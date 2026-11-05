#!/usr/bin/env python3
"""w5b_ccy_20261105.py — W5-B（ccy 部分）：docs/ccy/ 36 頁 NAV 四件注入＋主題 canonical（0700 總派工單 W5）

背景：ccy 36 頁（generate_ccy_deep_analysis 產物，P5 停寫＝靜態）全裸（零 sidebar 引用）＋舊主題
（#0a0e17 畫布/#FFD700 primary/#888 次文字）＋JS shell 色（#111520 圖表面板/#888 軸標）。
做法：頁層批次（同構 36/36，錨點全一）；四件＝sidebar.css＋tsa_tokens.css＋#sidebar-container＋sidebar.js。
語義色保留：.rating-sp 金徽記、ctx.strokeStyle #FFD700（圖表零軸語義金）、rgba(255,215,0) 數據金、
勝負 #4CAF50/#FF5722、EA 色全不動。
用法：python3 w5b_ccy_20261105.py [--dry|--verify]
"""
import sys
from pathlib import Path

BASE = Path('/home/z/my-project/exchange-repo')
PAGES = sorted((BASE / 'docs/ccy').glob('*.html'))

ROOT_OLD = ":root{--font:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC',sans-serif;--bg:#0a0e17;--card:#111520;--text:#d0d0d0;--text2:#888;--primary:#FFD700;--accent:#64b5f6;--green:#4CAF50;--red:#FF5722;--yellow:#FFC107;--orange:#fd7e14;--border:#1e2433;--radius:8px}"
ROOT_NEW = ":root{--font:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC',sans-serif;--bg:#0F1520;--card:#161E2E;--text:#E6EDF5;--text2:#A8B4C4;--primary:#5CA8FF;--accent:#38BDF8;--green:#22C55E;--red:#EF4444;--yellow:#EAB308;--orange:#F97316;--border:#2A3650;--radius:8px}"

HEAD_OLD = '</style>\n</head>'
HEAD_NEW = '</style>\n<!-- W5-B（2026-11-05）：NAV 四件 1+4——sidebar.css＋tsa_tokens.css -->\n<link rel="stylesheet" href="../sidebar.css">\n<link rel="stylesheet" href="../tsa_tokens.css">\n</head>'
BODY_OLD = '<body>\n'
BODY_NEW = '<body>\n<!-- W5-B：NAV 四件之 #sidebar-container -->\n<div id="sidebar-container"></div>\n'
TAIL_OLD = '</script>\n</body>'
TAIL_NEW = '</script>\n<script src="../sidebar.js"></script>\n</body>'

# JS／style 區 shell 色（root 塊先行處理後，全域替換淨低嘅 shell 位）
SHELL_REPLACES = [
    ('#111520→#161E2E（圖表面板 fill ×4）', '#111520', '#161E2E'),
    ('#888→#A8B4C4（軸標 ×3）', "#888'", "#A8B4C4'"),
    ('#1a1f2e→#1C2638（th hover）', 'background:#1a1f2e', 'background:#1C2638'),
]


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    dry, verify = mode == '--dry', mode == '--verify'
    done = skip = fail = 0
    fails = []
    for p in PAGES:
        t = p.read_text(encoding='utf-8', errors='replace')
        if 'tsa_tokens.css' in t:
            skip += 1
            continue
        log = []
        for name, old, new in [('root', ROOT_OLD, ROOT_NEW), ('head', HEAD_OLD, HEAD_NEW),
                               ('body', BODY_OLD, BODY_NEW), ('tail', TAIL_OLD, TAIL_NEW)]:
            n = t.count(old)
            if n != 1:
                fail += 1; fails.append(f'{p.name}: 錨點「{name}」×{n}'); t = None
                break
            t = t.replace(old, new)
            log.append(name)
        if t is None:
            continue
        for name, old, new in SHELL_REPLACES:
            c = t.count(old)
            if c:
                t = t.replace(old, new)
                log.append(f'{name}×{c}')
        if not dry and not verify:
            p.write_text(t, encoding='utf-8')
        done += 1
        if done <= 2 or dry:
            print(f'  [{"DRY" if dry else "OK"}] {p.name} {log}')
    print(f'\n=== {mode or "run"}：改{done} 跳{skip} 敗{fail}（共{len(PAGES)}） ===')
    for f in fails[:8]:
        print('  FAIL:', f)

    if verify:
        bad = 0
        for p in PAGES:
            t = p.read_text(encoding='utf-8', errors='replace')
            four = ('sidebar.css' in t, 'tsa_tokens.css' in t, 'sidebar-container' in t, 'sidebar.js' in t)
            legacy = ('#0a0e17' in t) or ('--primary:#FFD700' in t) or ('#111520' in t)
            if not all(four) or legacy:
                bad += 1
                print(f'  [VERIFY-FAIL] {p.name} 四件={four} 舊色={legacy}')
        print(f'=== verify：{"PASS 36/36" if bad == 0 and len(PAGES) == 36 else f"FAIL {bad}"} ===')
        return 0 if bad == 0 and len(PAGES) == 36 else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
