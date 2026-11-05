#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""reg187_forex_batch_20261105.py — REG-187：歷史 forex_reports 頁全量 W3 treatment batch

規格：from_openclaw/20261105_1315（開工令 REG-187：老闆 13:14 拍板 A——歷史頁統一新 UI）
＋from_zcode/20261105_1255（W3 patch diff 效果規格）＋1312（1316 Board 可開工表）。

範圍：docs/forex_reports/*.html 除 index.html＝201 頁（勘察實況：96 全裸＋104 半件
〔有 body class＋css＋js，缺 tokens＋container〕＋1 全件〔OpenClaw 11-05 晨報重生成版〕）。

每頁處理（冪等——逐件檢查在場即跳過；fail-close 錨點：</head>/<body/</body> 各恰 1）：
  1. head：無 sidebar.css → 注入 <!-- TSA Sidebar -->＋css link＋tokens 註釋＋tokens link
          （</head> 前）；有 css 無 tokens → css 行後插 tokens 註釋＋link
  2. body：plain <body> → <body class="has-sidebar">（有 class 保留）
  3. container：<body...> 行後插 <!-- W3/REG-187 註釋 -->＋<div id="sidebar-container">
  4. js：</body> 前插 <!-- TSA Sidebar Nav -->＋<script src="../sidebar.js">
  5. remap 三條（CI 等長 7→7，照 W3 patch 效果規格）：
       #0d1117→#0F1520／#58a6ff→#5CA8FF／#8b949e→#A8B4C4
     語義域保留：#3fb950/#f85149/#56d364 勝負＋#161b22/#21262d/#30363d/#e6edf3/
     #c9d1d9/#484f58/#1f2937/#666 組件色全不動。

用法：python3 reg187_forex_batch_20261105.py [--dry|--verify] [--log <batchlog.txt>]
"""
import re
import sys
from pathlib import Path

BASE = Path('/home/z/my-project/exchange-repo/docs/forex_reports')

CSS_LINK = '<link rel="stylesheet" href="../sidebar.css">'
TOK_LINK = '<link rel="stylesheet" href="../tsa_tokens.css">'
JS_TAG = '<script src="../sidebar.js"></script>'
CONT_DIV = '<div id="sidebar-container"></div>'

HEAD_FULL = ('<!-- TSA Sidebar -->\n'
             '<link rel="stylesheet" href="../sidebar.css">\n'
             '<!-- W3/REG-187（2026-11-05）：tsa_tokens.css（hardcode 殼頁 inert，'
             '照 W3 patch 效果規格） -->\n'
             '<link rel="stylesheet" href="../tsa_tokens.css">\n')
HEAD_TOK = ('<!-- W3/REG-187（2026-11-05）：tsa_tokens.css（hardcode 殼頁 inert，'
            '照 W3 patch 效果規格） -->\n'
            '<link rel="stylesheet" href="../tsa_tokens.css">\n')
BODY_CMT = '<!-- W3/REG-187：NAV 之 #sidebar-container -->\n'
JS_BLOCK = '<!-- TSA Sidebar Nav -->\n<script src="../sidebar.js"></script>\n'

REMAP = [('#0d1117', '#0F1520'), ('#58a6ff', '#5CA8FF'), ('#8b949e', '#A8B4C4')]


def process(p: Path, dry: bool):
    t = p.read_text(encoding='utf-8', errors='replace')
    orig = t
    acts = []

    # ---- fail-close 錨點 ----
    if t.count('</head>') != 1 or len(re.findall(r'<body[^>]*>', t)) != 1 \
       or t.count('</body>') != 1:
        return ('FAIL', '錨點非各恰 1', 0, 0)

    # ---- 1. head links ----
    has_css = CSS_LINK in t
    has_tok = TOK_LINK in t
    if not has_css and not has_tok:
        t = t.replace('</head>', HEAD_FULL + '</head>', 1)
        acts.append('+css+tok')
    elif has_css and not has_tok:
        t = t.replace(CSS_LINK, CSS_LINK + '\n' + HEAD_TOK.rstrip('\n'), 1)
        acts.append('+tok')
    elif not has_css and has_tok:
        t = t.replace(TOK_LINK, CSS_LINK + '\n' + TOK_LINK, 1)
        acts.append('+css')

    # ---- 2. body class ----
    m = re.search(r'<body([^>]*)>', t)
    if m and 'has-sidebar' not in m.group(1):
        t = t.replace(m.group(0), '<body class="has-sidebar">', 1)
        acts.append('+class')

    # ---- 3. container ----
    if CONT_DIV not in t:
        m = re.search(r'<body[^>]*>', t)
        t = t[:m.end()] + '\n' + BODY_CMT + CONT_DIV + t[m.end():]
        acts.append('+cont')

    # ---- 4. js ----
    if JS_TAG not in t:
        i = t.find('</body>')
        t = t[:i] + JS_BLOCK + t[i:]
        acts.append('+js')

    # ---- 5. remap ----
    rep = []
    for old, new in REMAP:
        n = t.count(old)
        if n:
            t = t.replace(old, new)
            rep.append(f'{old[-6:]}×{n}')
    if rep:
        acts.append('remap(' + '/'.join(rep) + ')')

    if t == orig:
        return ('SKIP', '全件在場', 0, 0)
    if not dry:
        p.write_text(t, encoding='utf-8')
    return ('DONE' if not dry else 'DRY', ','.join(acts), len(orig), len(t))


def verify(p: Path):
    t = p.read_text(encoding='utf-8', errors='replace')
    return (t.count(CSS_LINK) == 1 and t.count(TOK_LINK) == 1
            and t.count(JS_TAG) == 1 and t.count(CONT_DIV) == 1
            and 'has-sidebar' in re.search(r'<body[^>]*>', t).group(0)
            and sum(t.count(o) for o, _ in REMAP) == 0)


def main():
    args = sys.argv[1:]
    mode = 'run'
    log_path = None
    i = 0
    while i < len(args):
        if args[i] in ('--dry', '--verify'):
            mode = args[i].lstrip('-')
        elif args[i] == '--log':
            i += 1
            log_path = args[i]
        i += 1

    pages = sorted(q for q in BASE.glob('*.html') if q.name != 'index.html')
    if mode == 'verify':
        bad = [p.name for p in pages if not verify(p)]
        n = len(pages)
        print(f'=== verify：{"PASS %d/%d" % (n, n) if not bad else "FAIL %d" % len(bad)} ===')
        for b in bad[:10]:
            print('  FAIL:', b)
        return 0 if not bad else 1

    stats = {'DONE': 0, 'DRY': 0, 'SKIP': 0, 'FAIL': 0}
    lines = [f'# REG-187 batch log（{mode}）— 2026-11-05 ZCODE_w']
    for p in pages:
        st, detail, olen, nlen = process(p, mode == 'dry')
        stats[st] = stats.get(st, 0) + 1
        lines.append(f'{st}\t{p.name}\t{detail}\t{olen}→{nlen}')
    summary = (f"=== REG-187 {mode or 'run'}："
               f"改{stats.get('DONE', 0)} 乾跑{stats.get('DRY', 0)} "
               f"跳{stats.get('SKIP', 0)} 敗{stats.get('FAIL', 0)}（共 {len(pages)}） ===")
    lines.append(summary)
    print('\n'.join(lines[-6:]))
    if log_path:
        Path(log_path).write_text('\n'.join(lines) + '\n', encoding='utf-8')
        print(f'batch log → {log_path}')
    return 1 if stats.get('FAIL', 0) else 0


if __name__ == '__main__':
    sys.exit(main())
