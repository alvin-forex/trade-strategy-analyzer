#!/usr/bin/env python3
"""p0_wave3_martin_20261105.py — #27 P0 第三波：martin_autopsy_v3 61 頁 NAV＋token 統一

基準（同第二波，2205 派工＋唔另起爐灶）：
  ① #23 簽核 token：bg #0F1520 / L1 #161E2E / L2 #1C2638 / hairline #2A3650 /
     txt #E6EDF5·#A8B4C4 / primary #5CA8FF
  ② 狀態色照 ccy_power（dark #22C55E/#EF4444/#F97316）
  ③ 金 #FFD700 降級 --gold：KPI WR 值／S+ 等級徽記／SVG 數據文字／金底 badge 留金；
     h1 標題／nav a:hover 交互轉藍 #5CA8FF

範圍：docs/martin_autopsy_v3_*.html 61 頁（root 一層，全部明文）。
第一波工具已明言排除 martin（P0 範圍當時未定義）；本波＝三件套＋token 一鍵齊。

martin 族勘察結論（2026-11-05 掃描）：
  - 61/61 同構生成器產出：:root --bg:#0a0a1a;--surface:#0f0f23;--border:#2a2a4a;
    --text:#e0e0e0;--muted:#888;--accent:#FFD700＋[data-theme="light"] 對應
  - var(--accent) 定義但 0 引用（死變量，正名 --accent:#5CA8FF 免將來引錯金）
  - 大量 SVG（levels 圖）：fill #1a1a3e／stroke #4a3f8a／網格 #1a1a2a／文字 #eee
  - 保留域：hero 漸變 #2d1b69、語義紫 badge #9b59b6+#f3e5f5、light 語義塊
    （#fff8e1/#e8f5e9/#e3f2fd/#ffebee/#fff3e0/#e8eaf6+#555+#c5cae9 表頭組）、
    light h1 #1a237e、白 #fff、#100~#103（數據字串唔係色）

用法：python3 p0_wave3_martin_20261105.py          # 實跑
      python3 p0_wave3_martin_20261105.py --dry    # 只報告唔寫檔
      python3 p0_wave3_martin_20261105.py --verify # 獨立驗收（重掃殘留＋四件齊）
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

# ---- 6 位 hex remap（case-insensitive；含第二波全域表全部項目） ----
GLOBAL_HEX_CI = {
    # 第二波全域表（原封繼承）
    '0a0e17': '0F1520', '0a0a1a': '0F1520',
    '111520': '161E2E', '111827': '161E2E',
    '1a1f2e': '1C2638', '1a2332': '1C2638',
    '1e2433': '2A3650', '2a3040': '2A3650', '2a3450': '2A3650', '1e2a3f': '2A3650',
    '151b28': '131C2E',
    '64b5f6': '38BDF8', '90caf9': '38BDF8', '64ffda': '5CA8FF',
    '4caf50': '22C55E', 'ff5722': 'EF4444', 'ff5252': 'EF4444',
    '2ecc71': '22C55E', 'f39c12': 'F97316', 'e74c3c': 'EF4444', 'fd7e14': 'F97316',
    'd0d0d0': 'E6EDF5', 'e0e0e0': 'E6EDF5', 'e0e6ed': 'E6EDF5',
    'b0bec5': 'A8B4C4', '8892b0': 'A8B4C4', '5c6780': '7E8CA6',
    'f5f7fa': 'F1F5F9', 'eef2f7': 'E2E8F0', '0f3460': '2563EB', 'e94560': '0EA5E9',
    '16213e': '1E3A8A', '28a745': '16A34A', 'dc3545': 'DC2626',
    # 第三波 martin 族擴充（勘察 2026-11-05）
    '0a0a18': '0F1520',   # 卡/SVG 底（--bg 近親）
    '0f0f23': '161E2E',   # --surface → L1
    '1a1a3e': '161E2E',   # level 卡底／SVG fill → L1
    '1a1a2e': '161E2E',   # inline 卡底 → L1
    '1a1a2a': '2A3650',   # table 邊／SVG 網格 stroke → hairline
    '2a2a4a': '2A3650',   # --border → hairline
    '4a3f8a': '2A3650',   # 卡邊／SVG stroke → hairline
    '3498db': '38BDF8',   # B badge info 藍 → accent
    '5dade2': '38BDF8',   # SVG bar/文字 info 藍 → accent
    'f5f5f5': 'F1F5F9',   # light --bg
    'd4a017': 'CA8A04',   # light --accent（金降級 light）
}
# 3 位 hex remap（word boundary guard：#xxx 後面唔准跟 hex 字符）
HEX3_CI = {
    'eee': 'E6EDF5',   # SVG 文字
    'ccc': 'A8B4C4',   # SVG 次要文字／light 邊
    'aaa': 'A8B4C4',   # SVG 更暗文字
    '888': 'A8B4C4',   # --muted／內文次要
    '999': 'A8B4C4',   # .subtitle 等次要文字
    '777': '7E8CA6',   # SVG 軸標籤
    # 保留：555（light 語義塊文字組）、fff（白）、666（light muted 走 literal）
}
CASE_SENSITIVE = [('#FFC107', '#EAB308'), ('#ffc107', '#CA8A04')]

# ---- 變數宣告 literal ----
VAR_LITERALS = [
    # 第二波原項
    ('--primary:#FFD700', '--primary:#5CA8FF'),
    ('--pri:#FFD700', '--pri:#5CA8FF'),
    ('--text2:#888', '--text2:#A8B4C4'),
    ('--text2:#777', '--text2:#A8B4C4'),
    ('--text2:#666', '--text2:#64748B'),
    ('--text:#333', '--text:#1E293B'),
    ('--border:#ddd', '--border:#CBD5E1'),
    # 第三波 martin 族
    ('--accent:#FFD700', '--accent:#5CA8FF'),   # 死變量正名（0 引用）
    ('--muted:#666', '--muted:#64748B'),        # light muted
    ('--text:#222', '--text:#1E293B'),          # light text
]

# ---- 逐頁 curated（61 頁同構 pattern，勘察 61/61 命中） ----
PAGE_RULES = [
    ('h1 { font-size:22px; color:#FFD700', 'h1 { font-size:22px; color:#5CA8FF'),
    ('a:hover { color:#FFD700', 'a:hover { color:#5CA8FF'),
    # 留金申報：WR KPI 值／S+ 徽記（#FFF8E1 底）／SVG 金字／金底黑字 badge
]

# ---- 驗收殘留（第二波 LEGACY＋martin 族舊值） ----
LEGACY_KEYS = ['0a0e17', '111520', '1a1f2e', '1e2433', '64b5f6', '90caf9',
               'd0d0d0', '4CAF50', 'FF5722', '2ecc71', 'f39c12', 'e74c3c',
               '0a0a18', '0f0f23', '1a1a3e', '1a1a2e', '1a1a2a', '2a2a4a',
               '4a3f8a', '3498db', '5dade2', 'd4a017']


def apply_hex(html):
    """返回 (html, 總次數, 預期字節 delta)——3位→6位每處 +3B，6→6 等長"""
    n, delta = 0, 0
    for old, new in GLOBAL_HEX_CI.items():
        html, k = re.subn('#' + old, '#' + new, html, flags=re.IGNORECASE)
        n += k
    for old, new in HEX3_CI.items():
        html, k = re.subn('#' + old + '(?![0-9a-fA-F])', '#' + new, html,
                          flags=re.IGNORECASE)
        n += k
        delta += k * (len(new) - len(old))
    for old, new in CASE_SENSITIVE:
        html, k = re.subn(re.escape(old), new, html)
        n += k
    return html, n, delta


def apply_literals(html):
    n, delta = 0, 0
    for old, new in VAR_LITERALS:
        html, k = re.subn(re.escape(old), new, html, flags=re.IGNORECASE)
        n += k
        delta += k * (len(new) - len(old))
    for old, new in PAGE_RULES:
        html, k = re.subn(re.escape(old), new, html)
        n += k
        delta += k * (len(new) - len(old))
    return html, n, delta


def inject_nav(html):
    """NAV 三件套＋tokens link（冪等；照第一波 patch 邏輯）"""
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


NAV_BYTES = (len(CSS) + 1) + (len(CONT) + 1) + (len(JS) + 1) + (len(TK) + 1)


def verify(page, orig, new, expected_delta):
    ok, msgs = True, []
    if '</html>' not in new:
        ok = False; msgs.append('缺 </html>')
    for tag in ('<style', '</style>', '<table'):
        if new.count(tag) != orig.count(tag):
            ok = False; msgs.append(f'{tag} {orig.count(tag)}→{new.count(tag)}')
    # <script>：NAV 注入允許 +1，其他唔准
    if not (new.count('<script') - orig.count('<script')) in (0, 1):
        ok = False; msgs.append(f'<script {orig.count("<script")}→{new.count("<script")}')
    if abs((len(new) - len(orig)) - expected_delta) > 50:
        ok = False; msgs.append(
            f'delta 對賬 {len(new)-len(orig)} ≠ 預期 {expected_delta}')
    resid = {k: len(re.findall('#' + k, new, re.IGNORECASE))
             for k in LEGACY_KEYS}
    resid = {k: v for k, v in resid.items() if v}
    if resid:
        ok = False; msgs.append(f'殘留 {resid}')
    return ok, msgs


def main():
    dry = '--dry' in sys.argv
    vonly = '--verify' in sys.argv
    pages = sorted(DOCS.glob('martin_autopsy_v3_*.html'))
    if not pages:
        print('ERR：搵唔到 martin_autopsy_v3_*.html'); sys.exit(1)
    report = []
    for p in pages:
        orig = p.read_text(encoding='utf-8')
        if vonly:
            ok, msgs = verify(p.name, orig, orig, 0)
            nav_ok = all(s in orig for s in (CSS, CONT, JS, 'tsa_tokens.css'))
            if not nav_ok:
                ok = False; msgs.append('NAV 四件唔齊')
            report.append((p.name, 'verify-only', ok, msgs))
            continue
        html = orig
        html, n_nav = inject_nav(html)
        nav_b = NAV_BYTES if n_nav and 'css' in n_nav else 0
        html, n_hex, d_hex = apply_hex(html)
        html, n_lit, d_lit = apply_literals(html)
        expected_delta = nav_b + d_hex + d_lit
        ok, msgs = verify(p.name, orig, html, expected_delta)
        if 'ERR' in ''.join(n_nav) or 'SKIP' in ''.join(n_nav):
            ok = False; msgs += n_nav
            html = orig
        changed = (html != orig)
        if changed and not dry:
            p.write_text(html, encoding='utf-8')
        report.append((p.name,
                       f'nav={"+".join(n_nav) or "—"} hex={n_hex} lit={n_lit} '
                       f'delta={len(html)-len(orig):+d}B', ok, msgs))
    print(f'{"頁":<36}{"動作":<46}{"驗收"}')
    for name, act, ok, msgs in report:
        flag = 'PASS' if ok else 'FAIL ' + '; '.join(msgs)
        print(f'{name:<36}{act:<46}{flag}')
    fails = [r for r in report if not r[2]]
    print(f'\n{len(report)} 頁處理，{len(fails)} 頁 FAIL')
    if dry:
        print('（dry-run——無寫檔）')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
