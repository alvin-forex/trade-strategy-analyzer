#!/usr/bin/env python3
"""w5a_martin_v4_20261105.py — W5-A：martin_v4 族 165 頁 NAV 四件補齊＋主題 canonical（0700 總派工單 W5）

範圍：docs/reports/martin_v4_*.html（165 頁）＋ martin_v4_template.html（生成器模板）
背景：0805 缺陷信同款缺陷——頁有 sidebar.css/js 但缺 tsa_tokens＋#sidebar-container（四件掃描計 0）；
      主題塊舊色（#0a0e17 畫布/#FFD700 primary/#777 次文字）待 canonical。
結構現實（勘察 08:40）：
  - 161 頁＝新版格式（:root 直挂＋[data-theme=light]＋<body><div class="layout">）
  - 4 頁（14581/36338/36512/36655）＝舊版格式＝martin_v4_template.html 同構（[data-theme] 塊）
  - 9e93c62（11-01）重跑只改 tooltip；模板格式≠新版頁格式（可復現性疑）——頁層批次為主，
    模板同步修（將來若重生成，四件＋canonical 唔會走樣）
語義色保留：.r-sp 金（S+ 徽記）、rgba(255,215,0) 數據金、EA 色、勝負語義色全不動。
用法：python3 w5a_martin_v4_20261105.py [--dry|--verify]
"""
import re
import sys
from pathlib import Path

BASE = Path('/home/z/my-project/exchange-repo')
PAGES = sorted((BASE / 'docs/reports').glob('martin_v4_*.html'))
TMPL = BASE / 'martin_v4_template.html'

# ---------- 新版 161 頁編輯集 ----------
N1_OLD = ''':root{--bg:#0a0e17;--card:#111520;--card2:#1a1f2e;--zebra:#151b28;--brd:#1e2433;--th:#111520;
--text:#d0d0d0;--text2:#777;--pri:#FFD700;--acc:#64b5f6;--grn:#4CAF50;--red:#FF5722;--yel:#FFC107;
--radius:12px}'''
N1_NEW = ''':root{--bg:#0F1520;--card:#161E2E;--card2:#1C2638;--zebra:#131C2E;--brd:#2A3650;--th:#161E2E;
--text:#E6EDF5;--text2:#A8B4C4;--pri:#5CA8FF;--acc:#38BDF8;--grn:#22C55E;--red:#EF4444;--yel:#EAB308;
--radius:12px}'''
N2_OLD = '''[data-theme="light"]{--bg:#f5f7fa;--card:#fff;--card2:#eef2f7;--zebra:#f0f4fa;--brd:#ddd;--th:#eef2f7;
--text:#333;--text2:#666;--pri:#0f3460;--acc:#e94560;--grn:#28a745;--red:#dc3545;--yel:#ffc107}'''
N2_NEW = '''[data-theme="light"]{--bg:#F1F5F9;--card:#fff;--card2:#E2E8F0;--zebra:#F8FAFC;--brd:#CBD5E1;--th:#E2E8F0;
--text:#1E293B;--text2:#64748B;--pri:#2563EB;--acc:#0EA5E9;--grn:#16A34A;--red:#DC2626;--yel:#CA8A04}'''
TOKENS_OLD = '<link rel="stylesheet" href="../sidebar.css">'
TOKENS_NEW = '<link rel="stylesheet" href="../sidebar.css">\n<!-- W5-A（2026-11-05）：P0 四件套第 4 件 tsa_tokens.css——單一色源 -->\n<link rel="stylesheet" href="../tsa_tokens.css">'
N4_OLD = '<body>\n<div class="layout">'
N4_NEW = '<body>\n<!-- W5-A：NAV 四件之 #sidebar-container -->\n<div id="sidebar-container"></div>\n<div class="layout">'

# ---------- 舊版 4 頁＋模板編輯集 ----------
O1_OLD = '[data-theme="dark"]{--bg:#0a0e17;--card:#111520;--hover:#1a1f2e;--text:#d0d0d0;--text2:#777;--pri:#FFD700;--acc:#64b5f6;--grn:#4CAF50;--red:#FF5722;--yel:#FFC107;--brd:#1e2433;--th:#111520;--zebra:#151b28}'
O1_NEW = '[data-theme="dark"]{--bg:#0F1520;--card:#161E2E;--hover:#1C2638;--text:#E6EDF5;--text2:#A8B4C4;--pri:#5CA8FF;--acc:#38BDF8;--grn:#22C55E;--red:#EF4444;--yel:#EAB308;--brd:#2A3650;--th:#161E2E;--zebra:#131C2E}'
# 模板格式 light 塊（--card/--hover/--pri/--acc/--grn/--red/--yel/--brd/--th/--zebra 變數名）
O_LIGHT_RE = re.compile(r'\[data-theme="light"\]\{[^}]*\}')
O_LIGHT_NEW = '[data-theme="light"]{--bg:#F1F5F9;--card:#ffffff;--hover:#E2E8F0;--text:#1E293B;--text2:#64748B;--pri:#2563EB;--acc:#0EA5E9;--grn:#16A34A;--red:#DC2626;--yel:#CA8A04;--brd:#CBD5E1;--th:#E2E8F0;--zebra:#F8FAFC}'
BODY_OLD = '<body>\n'
BODY_NEW = '<body>\n<div id="sidebar-container"></div>\n'
JS_FB_OLD = "||'#0a0e17'"
JS_FB_NEW = "||'#0F1520'"


def apply(t, edits, log):
    for name, old, new in edits:
        n = t.count(old)
        if n != 1:
            return None, f'錨點「{name}」出現 {n} 次'
        t = t.replace(old, new)
        log.append(name)
    return t, None


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    dry, verify = mode == '--dry', mode == '--verify'
    done = skip = fail = 0
    fails = []
    for p in PAGES:
        t = p.read_text(encoding='utf-8', errors='replace')
        if 'tsa_tokens.css' in t and JS_FB_OLD not in t:
            skip += 1
            continue
        log = []
        # 幂等補修：已套四件但 JS fallback 舊色仍在（舊版 4 頁首輪漏 T5）
        if 'tsa_tokens.css' in t and JS_FB_OLD in t:
            fb = t.count(JS_FB_OLD)
            nt = t.replace(JS_FB_OLD, JS_FB_NEW)
            if not dry and not verify:
                p.write_text(nt, encoding='utf-8')
            done += 1
            print(f'  [{"DRY" if dry else "OK"}] {p.name} (補修: JS fallback ×{fb})')
            continue
        if N1_OLD in t:
            nt, err = apply(t, [('N1 root暗', N1_OLD, N1_NEW), ('N2 light', N2_OLD, N2_NEW),
                                ('N3 tokens', TOKENS_OLD, TOKENS_NEW), ('N4 container', N4_OLD, N4_NEW)], log)
            kind = 'new'
        elif O1_OLD in t:
            m = O_LIGHT_RE.search(t)
            if not m:
                fail += 1; fails.append(f'{p.name}: 無 light 塊'); continue
            nt, err = apply(t, [('O1 dark', O1_OLD, O1_NEW), ('O3 tokens', TOKENS_OLD, TOKENS_NEW),
                                ('O4 container', BODY_OLD, BODY_NEW)], log)
            if err is None:
                m = O_LIGHT_RE.search(nt)
                if m:
                    nt = nt.replace(m.group(0), O_LIGHT_NEW, 1)
                    log.append('O2 light')
                fb = nt.count(JS_FB_OLD)
                if fb:
                    nt = nt.replace(JS_FB_OLD, JS_FB_NEW)
                    log.append(f'O5 JS fallback ×{fb}')
            kind = 'old'
        else:
            fail += 1; fails.append(f'{p.name}: 唔識別格式'); continue
        if err:
            fail += 1; fails.append(f'{p.name}: {err}'); continue
        if not dry and not verify:
            p.write_text(nt, encoding='utf-8')
        done += 1
        if done <= 3 or dry:
            print(f'  [{"DRY" if dry else "OK"}] {p.name} ({kind}: {log})')

    # 模板同步修（T1 dark＋T2 light＋T3 tokens＋T4 container＋T5 JS fallback×2）
    t = TMPL.read_text(encoding='utf-8')
    if 'tsa_tokens.css' not in t:
        log = []
        nt, err = apply(t, [('T1 dark', O1_OLD, O1_NEW)], log)
        if err:
            print(f'  模板 FAIL: {err}')
        else:
            m = O_LIGHT_RE.search(nt)
            if m:
                nt = nt.replace(m.group(0), O_LIGHT_NEW, 1); log.append('T2 light')
            for name, old, new in [('T3 tokens', TOKENS_OLD, TOKENS_NEW), ('T4 container', BODY_OLD, BODY_NEW)]:
                if nt.count(old) == 1:
                    nt = nt.replace(old, new); log.append(name)
                else:
                    log.append(f'{name}×{nt.count(old)}!')
            fb = nt.count(JS_FB_OLD)
            if fb:
                nt = nt.replace(JS_FB_OLD, JS_FB_NEW); log.append(f'T5 JS fallback ×{fb}')
            if not dry and not verify:
                TMPL.write_text(nt, encoding='utf-8')
        print(f'  模板 martin_v4_template.html: {log}')
    else:
        print('  模板：已套用跳過')

    print(f'\n=== {mode or "run"}：頁 改{done} 跳{skip} 敗{fail}（共{len(PAGES)}） ===')
    for f in fails[:10]:
        print('  FAIL:', f)

    if verify:
        bad = 0
        for p in PAGES:
            t = p.read_text(encoding='utf-8', errors='replace')
            four = ('sidebar.css' in t, 'tsa_tokens.css' in t, 'sidebar-container' in t, 'sidebar.js' in t)
            legacy = ('#0a0e17' in t) or ('--pri:#FFD700' in t)
            if not all(four) or legacy:
                bad += 1
                print(f'  [VERIFY-FAIL] {p.name} 四件={four} 舊色={legacy}')
        tt = TMPL.read_text(encoding='utf-8')
        tfour = ('sidebar.css' in tt, 'tsa_tokens.css' in tt, 'sidebar-container' in tt, 'sidebar.js' in tt)
        print(f'  模板四件={tfour} 舊色={"#0a0e17" in tt or "--pri:#FFD700" in tt}')
        ok = bad == 0 and len(PAGES) == 165 and all(tfour)
        print(f'=== verify：{"PASS 165/165＋模板" if ok else f"FAIL {bad}"} ===')
        return 0 if ok else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
