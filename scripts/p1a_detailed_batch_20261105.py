#!/usr/bin/env python3
"""p1a_detailed_batch_20261105.py — #27 W1（P1a）：detailed_comparison 71 頁 NAV＋token 注入

基準（0655 定義表＋0700 總派工單 W1，同 P0 第三波做法）：
  NAV 方案 C 四件：sidebar.css＋#sidebar-container＋sidebar.js＋tsa_tokens.css
  殼 remap（勘察 2026-11-05，71/71 同構生成器族）：
    - #0d1117 → #0F1520（暗畫布 body/.container，142 處＝2×71）
    - #1976d2 → #5CA8FF（h1/h2 標題，710 處＝10×71）
    - .subtitle #666 → #A8B4C4（暗畫布次要文字，多行 rule，71 處）
  語義域保留（2b 裁決＋W2 後續）：
    - Material 語義色全留：#2e7d32/#c62828（勝負行）／#e8f5e9/#c8e6c9（勝底）
      ／#e8eaf6/#f0f4ff（表頭）／#fff8e1/#fff3e0/#f57c00/#ff9800/#e65100（警示域）
      ／#e3f2fd/#1976d2 之外 info 塊／#e91e63/#3f51b5/#fce4ec／#ffebee／#f9a825
      ／#4a148c/#1b5e20（熱力域）／#ff5722
    - 紫渐變 currency-header #667eea→#764ba2：裝飾漸變→W2 統一金調，本波保留
    - 淺卡內 #666/#333/#ddd/#e0e0e0/#f5f5f5/#f8f9fa/#fafafa：淺語義塊，保留
  tsa_tokens.css 純變量（:root＋data-theme），注入零視覺影響，確立單一色源。

用法：python3 p1a_detailed_batch_20261105.py          # 實跑
      python3 p1a_detailed_batch_20261105.py --dry    # 只報告唔寫檔
      python3 p1a_detailed_batch_20261105.py --verify # 獨立驗收
"""
import re
import sys
from pathlib import Path

BASE = Path('/home/z/my-project/exchange-repo')
DOCS = BASE / 'docs'

CSS = '<link rel="stylesheet" href="./sidebar.css">'
CONT = '<div id="sidebar-container"></div>'
JS = '<script src="./sidebar.js"></script>'
TK = '<link rel="stylesheet" href="tsa_tokens.css">'

# 殼 remap（case-insensitive，等長）
HEX_CI = {
    '0d1117': '0F1520',   # 暗畫布
    '1976d2': '5CA8FF',   # h1/h2 標題
}
# 暗畫布 subtitle 次要文字（多行 rule 內 #666；淺卡內 #666 唔掂）
SUBTITLE_RE = (re.compile(r'(\.subtitle\s*\{[^}]*?color:\s*)#666(?=[;,}])'),
               r'\1#A8B4C4')

LEGACY_KEYS = ['0d1117', '1976d2']   # 驗收殘留＝0
NAV_BYTES = (len(CSS) + 1) + (len(CONT) + 1) + (len(JS) + 1) + (len(TK) + 1)


def inject_nav(html):
    changed = []
    if 'staticrypt' in html[:2048].lower():
        return html, ['SKIP-加密殼']
    if 'sidebar.css' not in html:
        if '</head>' not in html:
            return html, ['ERR-無</head>']
        html = html.replace('</head>', CSS + '\n</head>', 1)
        changed.append('css')
    if 'sidebar-container' not in html:
        m = re.search(r'<body[^>]*>', html)
        if not m:
            return html, ['ERR-無<body>']
        html = html[:m.end()] + '\n' + CONT + html[m.end():]
        changed.append('container')
    if 'sidebar.js' not in html:
        idx = html.rfind('</body>')
        if idx < 0:
            return html, ['ERR-無</body>']
        html = html[:idx] + JS + '\n' + html[idx:]
        changed.append('js')
    if 'tsa_tokens.css' not in html:
        m = re.search(r'<link[^>]*sidebar\.css[^>]*>', html)
        if m:
            html = html.replace(m.group(0), m.group(0) + '\n' + TK, 1)
            changed.append('tokens')
    return html, changed


def apply_remaps(html):
    n = 0
    for old, new in HEX_CI.items():
        html, k = re.subn('#' + old, '#' + new, html, flags=re.IGNORECASE)
        n += k
    pat, repl = SUBTITLE_RE
    html, k = pat.subn(repl, html)
    n += k
    return html, n


def verify(orig, new, expected_delta):
    ok, msgs = True, []
    if '</html>' not in new:
        ok = False; msgs.append('缺 </html>')
    for tag in ('<style', '</style>', '<table'):
        if new.count(tag) != orig.count(tag):
            ok = False; msgs.append(f'{tag} {orig.count(tag)}→{new.count(tag)}')
    d = new.count('<script') - orig.count('<script')
    if d not in (0, 1):
        ok = False; msgs.append(f'<script +{d}')
    if abs((len(new) - len(orig)) - expected_delta) > 50:
        ok = False; msgs.append(
            f'delta {len(new)-len(orig)}≠{expected_delta}')
    resid = {k: len(re.findall('#' + k, new, re.IGNORECASE))
             for k in LEGACY_KEYS}
    resid = {k: v for k, v in resid.items() if v}
    if resid:
        ok = False; msgs.append(f'殘留 {resid}')
    # 語義保留抽檢：勝負 Material 色必須仍在
    for keep in ('#2e7d32', '#c62828', '#667eea'):
        if keep.lower() not in new.lower():
            ok = False; msgs.append(f'語義色 {keep} 失蹤')
    return ok, msgs


def main():
    dry = '--dry' in sys.argv
    vonly = '--verify' in sys.argv
    pages = sorted(DOCS.glob('detailed_comparison_all_levels_*.html'))
    if not pages:
        print('ERR：搵唔到 detailed_comparison 頁'); sys.exit(1)
    report = []
    for p in pages:
        orig = p.read_text(encoding='utf-8')
        if vonly:
            ok, msgs = verify(orig, orig, 0)
            if not all(s in orig for s in (CSS, CONT, JS, 'tsa_tokens.css')):
                ok = False; msgs.append('NAV 四件唔齊')
            report.append((p.name, 'verify-only', ok, msgs))
            continue
        html, n_nav = inject_nav(orig)
        nav_b = NAV_BYTES if 'css' in n_nav else 0
        html, n_rep = apply_remaps(html)
        # subtitle #666→#A8B4C4 每處 +4B；hex 等長
        n_sub = html.count('#A8B4C4') - orig.count('#A8B4C4')
        if n_sub < 0:
            n_sub = 0
        expected_delta = nav_b + n_sub * 4
        ok, msgs = verify(orig, html, expected_delta)
        if 'ERR' in ''.join(n_nav) or 'SKIP' in ''.join(n_nav):
            ok = False; msgs += n_nav
            html = orig
        changed = (html != orig)
        if changed and not dry:
            p.write_text(html, encoding='utf-8')
        report.append((p.name,
                       f'nav={"+".join(n_nav) or "—"} remap={n_rep} '
                       f'delta={len(html)-len(orig):+d}B', ok, msgs))
    print(f'{"頁":<44}{"動作":<40}{"驗收"}')
    for name, act, ok, msgs in report:
        flag = 'PASS' if ok else 'FAIL ' + '; '.join(msgs)
        print(f'{name:<44}{act:<40}{flag}')
    fails = [r for r in report if not r[2]]
    print(f'\n{len(report)} 頁處理，{len(fails)} 頁 FAIL')
    if dry:
        print('（dry-run——無寫檔）')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
