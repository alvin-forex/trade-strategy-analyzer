#!/usr/bin/env python3
"""w5g_portfolio_nav_20261105.py — W5-G（portfolios 11 頁）：NAV 注入＋dark 族殼 remap＋padding 衝突剝除

人口：docs/portfolios/＝portfolio_P1..P10（10 頁）＋portfolio_master_report_v2.html（1 頁）＝11。

普查（2026-11-05，11/11 覆蓋，錨點全一）：
  - P1–P10＝hardcode dark GitHub 殼族：body{background:#0d1117;color:#c9d1d9}＋
    body.has-sidebar{padding-left:240px}＋class="has-sidebar"；#58a6ff×140（h1/h2/
    signal-link/footer/ea-badge inline）＋#8b949e×70（meta/stat-label/th/footer）；
    卡 #161b22×10／邊 #21262d×60／語義 #3fb950/#f85149/#d29922 保持不動。無 :root、無 var()。
  - master_v2＝雙主題 var 驅動頁：:root dark（--bg:#0d1117/--accent:#58a6ff/--muted:#8b949e）
    ＋[data-theme="light"] override（--bg:#f5f7fa/--accent:#0f3460 navy）＋自帶 tsa-theme
    script（同 sidebar.js 機制）。tsa_tokens.css 定義 --bg/--accent/--card/--border——
    注入會接管其 var 設計（同 W5-C v3.9 翻黑理據）→ 三件＋tokens 豁免＋變量零改動。

⚠️ 站點 NAV 衝突剝除（P1–P10 專屬）：sidebar.css 用 body.has-sidebar{margin-left:
  var(--sidebar-w)=200px !important}＋fixed 側欄；頁自有 body.has-sidebar{padding-left:
  240px} 疊加＝440px 雙重偏移破版。注入時剝頁內該行（每頁恰 1 處，外科式），
  保留 class（站點 margin 接手）——「基本殼」協調工序，出貨信申報。

做法：
  dark10（P1–P10）：三 remap（CI 等長：#0d1117→#0F1520／#58a6ff→#5CA8FF／
    #8b949e→#A8B4C4）＋剝 padding 行＋四件注入（sidebar.css＋tsa_tokens.css
    ＋#sidebar-container＋sidebar.js——hardcode 頁 tokens inert）。
  dualvar（master_v2）：三件注入＋tokens 豁免＋內容/變量零改動。
分類 fail-close：非呢兩族唔動。
用法：python3 w5g_portfolio_nav_20261105.py [--dry|--verify]
"""
import re
import sys
from pathlib import Path

BASE = Path('/home/z/my-project/exchange-repo')
PAGES = sorted((BASE / 'docs/portfolios').glob('*.html'))

HEAD_DARK = ('<!-- W5-G（2026-11-05）：NAV 四件 1+2——sidebar.css＋tsa_tokens.css'
             '（hardcode 殼已 remap canonical，tokens inert） -->\n'
             '<link rel="stylesheet" href="../sidebar.css">\n'
             '<link rel="stylesheet" href="../tsa_tokens.css">\n')
HEAD_DUAL = ('<!-- W5-G（2026-11-05）：NAV 三件 1+2——sidebar.css；tokens 豁免'
             '（var 驅動雙主題設計＋tokens :root 會接管 var，照 W5-C v3.9 裁定） -->\n'
             '<link rel="stylesheet" href="../sidebar.css">\n')
BODY_INJ = ('<!-- W5-G：NAV 之 #sidebar-container -->\n<div id="sidebar-container"></div>\n')
TAIL_INJ = '<script src="../sidebar.js"></script>\n'

# --- dark10 殼 remap（CI 等長，照 W5-C v3/W1 規格：畫布/標題/次要文字三條） ---
HEX_CI = {
    '0d1117': '0F1520',   # 暗畫布 body bg
    '58a6ff': '5CA8FF',   # h1/h2/link/badge accent
    '8b949e': 'A8B4C4',   # meta/th/stat-label 次要文字
}
LEGACY_KEYS = list(HEX_CI.keys())

# --- 站點 NAV padding 衝突行（外科式剝除，每頁恰 1） ---
PAD_RULE_RE = re.compile(r'body\.has-sidebar\{padding-left:240px\}')


def classify(t: str) -> str:
    """前態分類（未注入頁）。dualvar 先判（避免誤入 dark10）"""
    low = t.lower()
    if '[data-theme="light"]' in low and ':root' in low:
        return 'dualvar'
    if '#0d1117' in low and '[data-theme="light"]' not in low:
        return 'dark10'
    return '?'


def classify_post(t: str) -> str:
    """後態分類（已 remap 已注入頁，供冪等/verify 用）：
    dualvar＝:root＋[data-theme=light]（雙主題塊完好）；
    dark10＝#5CA8FF 已在而無 light 塊（前態 #0d1117 已 remap 清零）"""
    low = t.lower()
    if '[data-theme="light"]' in low and ':root' in low:
        return 'dualvar'
    if '#5ca8ff' in low and '[data-theme="light"]' not in low:
        return 'dark10'
    return '?'


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    dry, verify = mode == '--dry', mode == '--verify'
    done = skip = fail = 0
    fails = []
    fmts = {'dark10': 0, 'dualvar': 0, '?': 0}
    remap_tot = {k: 0 for k in HEX_CI}
    strip_tot = 0
    for p in PAGES:
        t = p.read_text(encoding='utf-8', errors='replace')
        # --- 冪等閘先行（已注入頁直接跳，唔再行前態分類） ---
        already_nav = 'sidebar-container' in t or 'sidebar.js' in t
        if already_nav:
            fmt = classify_post(t)
            fmts[fmt] += 1
            skip += 1
            continue
        fmt = classify(t)
        fmts[fmt] += 1
        if fmt == '?':
            fail += 1; fails.append(f'{p.name}: 族不明（fail-close）'); continue
        # --- dark10：remap ＋ padding 衝突行剝除（注入前） ---
        n_rule = 0
        if fmt == 'dark10':
            for old, new in HEX_CI.items():
                t, k = re.subn('#' + old, '#' + new, t, flags=re.IGNORECASE)
                remap_tot[old] += k
            t, n_rule = PAD_RULE_RE.subn('', t)
            strip_tot += n_rule
            if n_rule != 1:
                fail += 1
                fails.append(f'{p.name}: padding 衝突行 ×{n_rule}（預期恰 1）'); continue
        # --- 三錨點（全一先至動） ---
        if t.count('</head>') != 1:
            fail += 1; fails.append(f'{p.name}: </head> ×{t.count("</head>")}'); continue
        mb = re.findall(r'<body[^>]*>', t)
        if len(mb) != 1:
            fail += 1; fails.append(f'{p.name}: <body> ×{len(mb)}'); continue
        if t.count('</body>') != 1:
            fail += 1; fails.append(f'{p.name}: </body> ×{t.count("</body>")}'); continue
        head_inj = HEAD_DARK if fmt == 'dark10' else HEAD_DUAL
        t2 = t.replace('</head>', head_inj + '</head>')
        t2 = re.sub(r'(<body[^>]*>)', r'\1' + BODY_INJ, t2, count=1)
        i = t2.find('</body>')
        t2 = t2[:i] + TAIL_INJ + t2[i:]
        # --- 純插入自證：除注入位外零改動（對 remap＋剝行後嘅基底對齊） ---
        strip = lambda s: s.replace(head_inj, '').replace(BODY_INJ, '').replace(TAIL_INJ, '')
        if strip(t2) != t:
            fail += 1; fails.append(f'{p.name}: 插入後基底不對齊（唔應該發生）'); continue
        log = []
        if fmt == 'dark10':
            log.append('remap:' + ','.join(f'{k}×{v}' for k, v in HEX_CI.items()))
            log.append('strip-pad×1')
        log.append(f'{fmt}:nav')
        if not dry and not verify:
            p.write_text(t2, encoding='utf-8')
        done += 1
        if done <= 3 or dry:
            print(f'  [{"DRY" if dry else "OK"}] {p.name} {" ".join(log)}')
    print(f'\n=== {mode or "run"}：改{done} 跳{skip} 敗{fail}（共{len(PAGES)}；族計 {fmts}） ===')
    if fmts['dark10']:
        print(f'  remap 總計: {remap_tot}＋剝 padding 行 {strip_tot}')
    for f in fails[:10]:
        print('  FAIL:', f)

    if verify:
        bad = 0
        for p in PAGES:
            t = p.read_text(encoding='utf-8', errors='replace')
            fmt = classify_post(t)
            css = t.count('<link rel="stylesheet" href="../sidebar.css">')
            js = t.count('<script src="../sidebar.js"></script>')
            cont = t.count('<div id="sidebar-container"></div>')
            tok = t.count('<link rel="stylesheet" href="../tsa_tokens.css">')
            if fmt == 'dark10':
                legacy = sum(t.lower().count('#' + k) for k in LEGACY_KEYS)
                pad = len(PAD_RULE_RE.findall(t))
                ok = (css == 1 and js == 1 and cont >= 1 and tok == 1
                      and legacy == 0 and pad == 0 and '#5CA8FF' in t)
            elif fmt == 'dualvar':
                # 三件＋tokens 豁免＋自身 :root/雙主題塊完好（設計零改動證據）
                ok = (css == 1 and js == 1 and cont >= 1 and tok == 0
                      and '--bg:#0d1117' in t.replace(' ', '').lower()
                      and '[data-theme="light"]' in t.lower()
                      and '#f5f7fa' in t.lower())
            else:
                ok = False
            if not ok:
                bad += 1
                print(f'  [VERIFY-FAIL] {p.name} fmt={fmt} css={css} js={js} cont={cont} tok={tok}')
        n = len(PAGES)
        print(f'=== verify：{"PASS %d/%d" % (n, n) if bad == 0 else f"FAIL {bad}"} ===')
        return 0 if bad == 0 else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
