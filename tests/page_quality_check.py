#!/usr/bin/env python3
"""L25 page-quality gate — placeholder／空白殼／數據源三檢（老闆 2026-11-01 TG 批「同意」）.

三檢（任一**新**命中即紅燈＋出頁面清單）：
  1) placeholder 詞表命中可見文本（HTML 註釋／script／style 排除）
  2) 非動態頁可見文本 <400 字（空白殼；fetch/XHR/axios 頁屬動態渲染，明文字少屬設計）
  3) 動態頁 CSV 數據源 404（repo 內無此檔）或 0 字節（離線核對存在性＋大小；
     外部 http(s) CSV 唔單 CI 核，由 live audit 抽驗覆蓋）

加密頁（staticrypt）跳過掃描、單獨計數——密文不可掃屬設計，質素由
上板流程＋ZCODE_w 全站 audit（scripts/audit_site_quality.py，解密後掃）覆蓋。

Baseline：tests/page_quality_baseline.json（ratchet 制——只准縮唔准加；
每條帶 owner＋reason，收項後移除）。新增違規而 baseline 無記錄 → exit 1。

2026-11-01 首跑基線：899 頁（ tracked docs/*.html），已知違規 4 條
（martin_v4 CSV×4，OpenClaw D2 全量補 CSV 後收項）。
"""
import json
import os
import re
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(REPO_ROOT, 'tests', 'page_quality_baseline.json')
MIN_CHARS = 400

PLACEHOLDER_PAT = re.compile(
    r'(施工中|即將推出|即將上線|Coming [Ss]oon|COMING SOON|Under [Cc]onstruction|'
    r'敬請期待|待補充|待完善|佔位|占位符|placeholder content|尚未完成|未完成模板|'
    r'頁面建設中|內容準備中|示例數據|Sample [Dd]ata|TODO[:：]|FIXME|此處顯示|範本)', re.I)
DYNAMIC_PAT = re.compile(
    r'fetch\(|XMLHttpRequest|axios|document\.createElement|innerHTML|'
    r'document\.write|insertAdjacentHTML', re.I)   # 動態＝JS 渲染（fetch 或 DOM 建構）
# 前置快篩（C 速 in 運算）：零候選就唔使跑上面 regex——CI 提速約 5 倍（50MB→秒級）
_DYN_CAND = ('fetch(', 'xmlhttprequest', 'axios', 'createelement',
             'innerhtml', 'document.write', 'insertadjacenthtml')
_PLACE_CAND = ('施工中', '即將推出', '即將上線', 'coming', 'construction', '敬請期待',
               '待補充', '待完善', '佔位', '占位符', 'placeholder', '尚未完成',
               '未完成模板', '頁面建設中', '內容準備中', '示例數據', 'sample',
               'todo', 'fixme', '此處顯示', '範本')
STATICRYPT_PAT = re.compile(r'staticrypt|staticCrypt', re.I)
# CSV 引用三形態：const CSV_URL='...' / fetch('...') / url:'...'（martin_v4 模板實證）
CSV_REF_PAT = re.compile(
    r"""(?:CSV_URL\s*=\s*|fetch\(\s*|url\s*:\s*)['"`]([^'"`]*?\.csv(?:\?[^'"`]*)?)['"`]""",
    re.I)


def strip_text(src):
    s = re.sub(r'<!--.*?-->', ' ', src, flags=re.S)          # 註釋唔算可見文本
    s = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', s, flags=re.S | re.I)
    s = re.sub(r'<[^>]+>', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def resolve_csv(ref, page_rel):
    ref = ref.split('#')[0]
    if ref.startswith(('http://', 'https://', '//')):
        return None                                          # 外部源，CI 離線唔核
    page_dir = os.path.dirname(os.path.join('docs', page_rel))
    return os.path.normpath(os.path.join(page_dir, ref)).replace(os.sep, '/')


def scan_page(rel, raw):
    """回 (violations, encrypted_bool)；violation = (check, page, detail)。"""
    head = raw[:4000]
    if ('staticrypt' in head.lower() or 'staticcrypt' in head.lower()) \
            and '<canvas' not in head:
        return [], True                                      # 加密頁：跳過
    v = []
    raw_l = raw.lower()
    # placeholder：先快篩，有候選先 strip＋regex
    if any(w in raw for w in _PLACE_CAND) or any(w in raw_l for w in _PLACE_CAND):
        text = strip_text(raw)
        ph = PLACEHOLDER_PAT.findall(text)
        if ph:
            v.append(('placeholder', rel, '命中: ' + '/'.join(sorted(set(ph))[:3])))
    else:
        text = strip_text(raw)
    dynamic = bool(DYNAMIC_PAT.search(raw)) if any(w in raw_l for w in _DYN_CAND) else False
    if not dynamic and len(text) < MIN_CHARS:
        v.append(('thin-shell', rel, f'非動態頁可見文本僅 {len(text)} 字（<{MIN_CHARS}）'))
    if dynamic and '.csv' in raw_l:
        seen = set()
        for m in CSV_REF_PAT.finditer(raw):
            tgt = resolve_csv(m.group(1), rel)
            if tgt is None or tgt in seen:
                continue
            seen.add(tgt)
            ap = os.path.join(REPO_ROOT, tgt)
            if not os.path.exists(ap):
                v.append(('csv-missing', rel, f'數據源 404：{m.group(1)}'))
            elif os.path.getsize(ap) == 0:
                v.append(('csv-empty', rel, f'數據源空檔：{m.group(1)}（0 字節）'))
    return v, False


def load_baseline():
    try:
        with open(BASELINE, encoding='utf-8') as f:
            data = json.load(f)
        return {item['key']: item for item in data.get('violations', [])}
    except FileNotFoundError:
        return {}


def main():
    files = subprocess.run(['git', 'ls-files', 'docs'], cwd=REPO_ROOT,
                           capture_output=True, text=True).stdout.split()
    htmls = sorted(f[5:] for f in files
                   if f.startswith('docs/') and f.endswith('.html'))

    violations, encrypted = [], 0
    for rel in htmls:
        raw = open(os.path.join(REPO_ROOT, 'docs', rel),
                   encoding='utf-8', errors='ignore').read()
        v, enc = scan_page(rel, raw)
        if enc:
            encrypted += 1
        violations.extend(v)

    baseline = load_baseline()
    keyed = {f'{chk}:{page}': (chk, page, det) for chk, page, det in violations}
    new = [(k, *keyed[k]) for k in keyed if k not in baseline]
    covered = [k for k in keyed if k in baseline]

    print(f'L25 page-quality gate: 掃 {len(htmls)} 頁（加密跳過 {encrypted}）'
          f'｜命中 {len(keyed)}｜baseline 已記 {len(covered)}｜新違規 {len(new)}')
    if covered:
        for k in sorted(covered):
            print(f'  [baseline] {k} —— {baseline[k].get("owner", "?")}：'
                  f'{baseline[k].get("reason", "")}')
    if new:
        print('\n✗ 新違規（baseline 無記錄）——禁止 merge main：')
        for _, chk, page, det in sorted(new):
            print(f'  [{chk}] {page} —— {det}')
        print('\n處理：修頁面／補數據源；確屬已知歷史遺留先至入 baseline（'
              'tests/page_quality_baseline.json，要有 owner＋reason）。')
        return 1
    print('✓ 綠燈：三檢零新違規')
    return 0


if __name__ == '__main__':
    sys.exit(main())
