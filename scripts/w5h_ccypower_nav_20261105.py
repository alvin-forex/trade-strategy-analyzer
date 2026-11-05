#!/usr/bin/env python3
"""w5h_ccypower_nav_20261105.py — W5-H（ccy_power 3 頁 copy_trade 系）：NAV 三件注入＋tokens 豁免

人口：docs/ccy_power/＝4 html——index.html（178KB，數據 lane 30min auto-refresh 頁，
已有三件 NAV（../sidebar.css＋container＋sidebar.js，tok=0）＝數據 lane 維護，**唔掂**）＋
copy_trade_portfolio.html／copy_trade_v2.html／portfolio_recommendation.html（3 裸頁）＝本批。

家族（3/3 同族）：var 驅動 dark 自帶 palette——:root multiline（--bg:#0a0e1a／
--card:#111827／--border:#1e293b／--text:#f1f5f9／--text2:#94a3b8／--accent:#3b82f6）。
tsa_tokens.css 定義 --bg/--accent/--card/--border——注入會接管 var 設計
（同 W5-C v3.9／W5-G master_v2 豁免理據）→ 三件＋豁免＋內容零改動。
「root 明文層」（0700 派工單）＝明文服務＋NAV——同 dir 數據 lane index.html
本身即用此形態（../ 三件、tok=0），照抄同款。

用法：python3 w5h_ccypower_nav_20261105.py [--dry|--verify]
"""
import re
import sys
from pathlib import Path

BASE = Path('/home/z/my-project/exchange-repo')
PAGES = sorted((BASE / 'docs/ccy_power').glob('copy_trade_portfolio.html'))
PAGES += sorted((BASE / 'docs/ccy_power').glob('copy_trade_v2.html'))
PAGES += sorted((BASE / 'docs/ccy_power').glob('portfolio_recommendation.html'))

HEAD_INJ = ('<!-- W5-H（2026-11-05）：NAV 三件 1+2——sidebar.css；tokens 豁免'
            '（var 驅動自帶 palette＋tokens :root 會接管 var，照同 dir index.html 及'
            ' W5-C v3.9 裁定） -->\n'
            '<link rel="stylesheet" href="../sidebar.css">\n')
BODY_INJ = ('<!-- W5-H：NAV 之 #sidebar-container -->\n<div id="sidebar-container"></div>\n')
TAIL_INJ = '<script src="../sidebar.js"></script>\n'


def family_ok(t: str) -> bool:
    low = t.lower()
    return ':root' in low and '#0a0e1a' in low and '[data-theme="light"]' not in low


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    dry, verify = mode == '--dry', mode == '--verify'
    done = skip = fail = 0
    fails = []
    for p in PAGES:
        t = p.read_text(encoding='utf-8', errors='replace')
        if 'sidebar-container' in t or 'sidebar.js' in t:
            skip += 1  # 已注入（冪等閘先行）
            continue
        if not family_ok(t):
            fail += 1; fails.append(f'{p.name}: 非 ccy_power var 族（fail-close）'); continue
        # --- 三錨點（全一先至動） ---
        if t.count('</head>') != 1:
            fail += 1; fails.append(f'{p.name}: </head> ×{t.count("</head>")}'); continue
        mb = re.findall(r'<body[^>]*>', t)
        if len(mb) != 1:
            fail += 1; fails.append(f'{p.name}: <body> ×{len(mb)}'); continue
        if t.count('</body>') != 1:
            fail += 1; fails.append(f'{p.name}: </body> ×{t.count("</body>")}'); continue
        t2 = t.replace('</head>', HEAD_INJ + '</head>')
        t2 = re.sub(r'(<body[^>]*>)', r'\1' + BODY_INJ, t2, count=1)
        i = t2.find('</body>')
        t2 = t2[:i] + TAIL_INJ + t2[i:]
        # --- 純插入自證 ---
        strip = lambda s: s.replace(HEAD_INJ, '').replace(BODY_INJ, '').replace(TAIL_INJ, '')
        if strip(t2) != t:
            fail += 1; fails.append(f'{p.name}: 插入後原文不對齊（唔應該發生）'); continue
        if not dry and not verify:
            p.write_text(t2, encoding='utf-8')
        done += 1
        print(f'  [{"DRY" if dry else "OK"}] {p.name} var-dark:nav3')
    print(f'\n=== {mode or "run"}：改{done} 跳{skip} 敗{fail}（共{len(PAGES)}） ===')
    for f in fails[:10]:
        print('  FAIL:', f)

    if verify:
        bad = 0
        for p in PAGES:
            t = p.read_text(encoding='utf-8', errors='replace')
            css = t.count('<link rel="stylesheet" href="../sidebar.css">')
            js = t.count('<script src="../sidebar.js"></script>')
            cont = t.count('<div id="sidebar-container"></div>')
            tok = t.count('<link rel="stylesheet" href="../tsa_tokens.css">')
            ok = css == 1 and js == 1 and cont >= 1 and tok == 0 and '#0a0e1a' in t
            if not ok:
                bad += 1
                print(f'  [VERIFY-FAIL] {p.name} css={css} js={js} cont={cont} tok={tok}')
        n = len(PAGES)
        print(f'=== verify：{"PASS %d/%d" % (n, n) if bad == 0 else f"FAIL {bad}"} ===')
        return 0 if bad == 0 else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
