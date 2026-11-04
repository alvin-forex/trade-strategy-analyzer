#!/usr/bin/env python3
"""p2_w2_semantic_20261105.py — #27 W2（2b 圖表語義域）：P0 76 頁內裝飾漸變統一金調

裁決（0655 定義表 §1，老闆金色粒子風方向）：
  - 語義色保留：熱力 ramp／多序列紫／period_stats bar 金（已對齊 #FFD700，免改）／淺語義塊
  - 裝飾漸變統一金調：#FFD700 α 值 → 透明，token 黑底（#0F1520/#161E2E）

施工（勘察 2026-11-05）：
  merged_report_11141.html  hero：#1a1a3e→#2d1b69→#1a1a3e 3停 → #0F1520→rgba(金,.13)→#0F1520
  ff54_report.html          2 條：90deg 紫對 + 135deg 紫三停 → 金調同構
  martin_autopsy_v3_*（61）  3 條/頁：header 135deg＋90deg×2 → 金調同構（淺色 #e8eaf6 系不動）

用法：python3 p2_w2_semantic_20261105.py          # 實跑
      python3 p2_w2_semantic_20261105.py --dry    # 只報告
      python3 p2_w2_semantic_20261105.py --verify # 獨立驗收（紫殘留掃描）
"""
import re
import sys
from pathlib import Path

BASE = Path('/home/z/my-project/exchange-repo')
DOCS = BASE / 'docs'

# (頁 pattern, 舊漸變, 新漸調, 預期次數/頁)
RULES = [
    ('merged_report_11141.html',
     'linear-gradient(135deg,#1a1a3e 0%,#2d1b69 50%,#1a1a3e 100%)',
     'linear-gradient(135deg,#0F1520 0%,rgba(255,215,0,.13) 50%,#0F1520 100%)',
     1),
    ('merged_report_11141.html',
     'linear-gradient(90deg,#1a1a3e,#2d1b69)',
     'linear-gradient(90deg,#0F1520,rgba(255,215,0,.11))',
     1),
    ('ff54_report.html',
     'linear-gradient(135deg,#1a1f3a,#2d1b4e,#1a1f3a)',
     'linear-gradient(135deg,#0F1520,rgba(255,215,0,.13),#0F1520)',
     1),
    ('martin_autopsy_v3_*.html',
     'linear-gradient(135deg,#161E2E 0%,#2d1b69 50%,#161E2E 100%)',
     'linear-gradient(135deg,#161E2E 0%,rgba(255,215,0,.13) 50%,#161E2E 100%)',
     1),
    ('martin_autopsy_v3_*.html',
     'linear-gradient(90deg,#161E2E,#2d1b69)',
     'linear-gradient(90deg,#161E2E,rgba(255,215,0,.11))',
     2),
]

# 驗收：紫裝飾殘留應為 0（含舊紫族）；淺語義塊 #e8eaf6/#c5cae9 必須仍在
PURPLE_KEYS = ['2d1b69', '2d1b4e', '1a1f3a']
KEEP_LIGHT = ['#e8eaf6', '#c5cae9']


def verify(path, orig, new, expected):
    ok, msgs = True, []
    if len(new) != len(orig) + expected[1]:
        ok = False; msgs.append(f'delta {len(new)-len(orig)}≠{expected[1]}')
    resid = {k: len(re.findall('#' + k, new, re.IGNORECASE))
             for k in PURPLE_KEYS}
    resid = {k: v for k, v in resid.items() if v}
    if resid:
        ok = False; msgs.append(f'紫殘留 {resid}')
    if 'martin' in str(path):
        for k in KEEP_LIGHT:
            if k not in new:
                ok = False; msgs.append(f'淺語義 {k} 失蹤')
    for tag in ('<style', '</style>', '<table', '<script'):
        if new.count(tag) != orig.count(tag):
            ok = False; msgs.append(f'{tag} 數變')
    return ok, msgs


def main():
    dry = '--dry' in sys.argv
    vonly = '--verify' in sys.argv
    report = []
    pages = {}
    for pat, *_ in RULES:
        for p in sorted(DOCS.glob(pat)):
            pages[str(p.relative_to(DOCS))] = p
    for name, p in sorted(pages.items()):
        orig = p.read_text(encoding='utf-8')
        if vonly:
            ok, msgs = True, []
            resid = {k: len(re.findall('#' + k, orig, re.IGNORECASE))
                     for k in PURPLE_KEYS}
            resid = {k: v for k, v in resid.items() if v}
            if resid:
                ok = False; msgs.append(f'紫殘留 {resid}')
            if 'martin' in name:
                for k in KEEP_LIGHT:
                    if k not in orig:
                        ok = False; msgs.append(f'淺語義 {k} 失蹤')
            report.append((name, 'verify-only', ok, msgs))
            continue
        html = orig
        nrep, delta = 0, 0
        for pat, old, new, want in RULES:
            if not p.match(DOCS / pat) and pat != p.name:
                # glob 對照
                import fnmatch
                if not fnmatch.fnmatch(p.name, pat):
                    continue
            elif pat != p.name and not fnmatch.fnmatch(p.name, pat):
                continue
            n = html.count(old)
            if n == 0:
                if new in html:
                    continue  # 已套用（冪等複跑）——跳過
                ok = False
                report.append((name, f'[{old[:40]}…] 命中 0 且新值缺席', False,
                               ['錨點失蹤']))
                nrep = -1
                break
            if n != want:
                ok = False
                report.append((name, f'[{old[:40]}…] 命中 {n}≠{want}', False,
                               ['錨點數不符']))
                nrep = -1
                break
            html = html.replace(old, new)
            nrep += n
            delta += n * (len(new) - len(old))
        if nrep < 0:
            continue
        ok, msgs = verify(p.name, orig, html, (nrep, delta))
        changed = (html != orig)
        if changed and not dry:
            p.write_text(html, encoding='utf-8')
        report.append((name, f'漸變換金={nrep} delta={len(html)-len(orig):+d}B',
                       ok, msgs))
    print(f'{"頁":<38}{"動作":<40}{"驗收"}')
    for name, act, ok, msgs in report:
        flag = 'PASS' if ok else 'FAIL ' + '; '.join(msgs)
        print(f'{name:<38}{act:<40}{flag}')
    fails = [r for r in report if not r[2]]
    print(f'\n{len(report)} 頁處理，{len(fails)} 頁 FAIL')
    if dry:
        print('（dry-run——無寫檔）')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
