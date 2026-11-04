#!/usr/bin/env python3
"""p0_tokens_batch_20261104.py — #27 P0 第二波：設計 token 統一（冪等批量工具）

基準（2205 派工＋唔好另起爐灶）：
  ① #23 新首頁（設計師簽核）深色 token：bg/L0 #0F1520 / L1 #161E2E / L2 #1C2638 /
     hairline #2A3650 / txt #E6EDF5·#A8B4C4 / sem info #5CA8FF
     （來源同 staticrypt 深色模板 scripts/staticrypt/password_template_dark.html）
  ② 狀態色照 ccy_power/index.html 模式（dark #22C55E/#EF4444/#EAB308/#F97316）
  ③ 金 #FFD700 降級 --gold（品牌/數據強調）；標題/表頭/交互統一 #5CA8FF

範圍：root 主功能頁 11 頁。唔郁：analyzer.html（原版 app byte 一致鐵律）、
  tug_of_war_calculator.html（已屬 Tailwind light 規範族）。
保留：熱力圖 ramp（#1b5e20/#a5d6a7/#b71c1c/#ef9a9a）、多序列紫
  （#4a148c/#ce93d8）、數據 bar 金（#FFD700）、hero 裝飾漸變——圖表語義域，
  等 72 頁定義表後第二波 b 再統一。

用法：python3 p0_tokens_batch_20261104.py          # 實跑
      python3 p0_tokens_batch_20261104.py --dry    # 只報告唔寫檔
      python3 p0_tokens_batch_20261104.py --verify # 獨立驗收（重掃殘留）
"""
import re
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]   # repo root
DOCS = BASE / 'docs'

# ---- 施工頁清單（11 頁） ----
TOKENS_INJECT = [  # 有 data-theme 系統 → 注入 tsa_tokens.css（P0 四件套第 4 件）
    'period_stats.html', 'volatility.html', 'forex_news.html',
    'pivot_table.html', 'mfe_mae.html', 'ccy_ranking.html',
    'sample_period_stats.html', 'ea_strategy_masterplan.html',
]
HEX_ONLY = [  # 無 data-theme 系統（硬編碼）→ 只做精準 remap，唔注入
    'symbol_ranking.html', 'ff54_report.html', 'merged_report_11141.html',
]
SKIP = ['analyzer.html', 'tug_of_war_calculator.html']  # 理由見 docstring

# ---- 全域 hex remap（case-insensitive；unambiguous 殼/狀態色） ----
GLOBAL_HEX_CI = {
    # 背景／卡／殼
    '0a0e17': '0F1520', '0a0a1a': '0F1520',
    '111520': '161E2E', '111827': '161E2E',
    '1a1f2e': '1C2638', '1a2332': '1C2638',
    '1e2433': '2A3650', '2a3040': '2A3650', '2a3450': '2A3650', '1e2a3f': '2A3650',
    '151b28': '131C2E',
    # 藍 accent（連結/互動）
    '64b5f6': '38BDF8', '90caf9': '38BDF8', '64ffda': '5CA8FF',
    # 狀態色（語義保留，色值統一）
    '4caf50': '22C55E', 'ff5722': 'EF4444', 'ff5252': 'EF4444',
    '2ecc71': '22C55E', 'f39c12': 'F97316', 'e74c3c': 'EF4444', 'fd7e14': 'F97316',
    # 文字
    'd0d0d0': 'E6EDF5', 'e0e0e0': 'E6EDF5', 'e0e6ed': 'E6EDF5',
    'b0bec5': 'A8B4C4', '8892b0': 'A8B4C4', '5c6780': '7E8CA6',
    # light 態（族頁 light block 值）
    'f5f7fa': 'F1F5F9', 'eef2f7': 'E2E8F0', '0f3460': '2563EB', 'e94560': '0EA5E9',
    '16213e': '1E3A8A', '28a745': '16A34A', 'dc3545': 'DC2626',
}
# case-sensitive 一對（dark #FFC700→#EAB308；light #ffc107→#CA8A04）
CASE_SENSITIVE = [('#FFC107', '#EAB308'), ('#ffc107', '#CA8A04')]

# ---- 變數宣告 literal（globally 安全） ----
VAR_LITERALS = [
    ('--primary:#FFD700', '--primary:#5CA8FF'),
    ('--pri:#FFD700', '--pri:#5CA8FF'),
    ('--text2:#888', '--text2:#A8B4C4'),
    ('--text2:#777', '--text2:#A8B4C4'),
    ('--text2:#666', '--text2:#64748B'),
    ('--text:#333', '--text:#1E293B'),
    ('--border:#ddd', '--border:#CBD5E1'),
]

# ---- 逐頁 curated（標題/表頭/交互→藍；數據值/徽記→留金） ----
PAGE_RULES = {
    'volatility.html': [
        ('border-bottom:1px solid #FFD700', 'border-bottom:1px solid #5CA8FF'),  # .tf-group
    ],
    'symbol_ranking.html': [
        ('h1{font-size:1.2em;margin-bottom:2px;color:#FFD700}',
         'h1{font-size:1.2em;margin-bottom:2px;color:#5CA8FF}'),                       # h1 標題
        ('color:#FFD700;margin:16px 0 8px', 'color:#5CA8FF;margin:16px 0 8px'),      # .sym-header
        ('border-left:3px solid #FFD700', 'border-left:3px solid #5CA8FF'),
        ('border-bottom:2px solid #FFD700;color:#FFD700', 'border-bottom:2px solid #5CA8FF;color:#5CA8FF'),  # th
        ('border-color:#FFD700}', 'border-color:#5CA8FF}'),                            # select:focus
        ('color:#666', 'color:#A8B4C4'),
        ('color:#999', 'color:#A8B4C4'),
        # .sum .v 留金（數據強調）
    ],
    'ff54_report.html': [
        ('h1{color:#ffd700', 'h1{color:#5CA8FF'),
        ('h3{color:#ffd700', 'h3{color:#5CA8FF'),
        # .sc .v 留金；hero 漸變（#1a1f3a/#2d1b4e）留裝飾
    ],
    'merged_report_11141.html': [
        ('h1{font-size:20px;color:#FFD700', 'h1{font-size:20px;color:#5CA8FF'),
        ('.tab.active{color:#FFD700;border-bottom-color:#FFD700}',
         '.tab.active{color:#5CA8FF;border-bottom-color:#5CA8FF}'),
        ('table th:hover{color:#FFD700}', 'table th:hover{color:#5CA8FF}'),
        ('.sub-tab.active{color:#FFD700;border-color:#FFD700;background:rgba(255,215,0,.1)}',
         '.sub-tab.active{color:#5CA8FF;border-color:#5CA8FF;background:rgba(92,168,255,.1)}'),
        # .kpi .val.gold／.sec-h .badge 留金
    ],
    'ea_strategy_masterplan.html': [
        # :root 補 --primary（idempotent：--gold:#FFD700;--accent → 插中間）
        ('--gold:#FFD700;--accent', '--gold:#FFD700;--primary:#5CA8FF;--accent'),
        # h1/h2/th/phase-title：var(--gold)→var(--primary)；徽記/phase-num/.b-gold/.highlight 留金
        ('color:var(--gold);margin-bottom:4px;border-bottom:2px solid var(--gold)',
         'color:var(--primary);margin-bottom:4px;border-bottom:2px solid var(--primary)'),
        ('color:var(--gold);margin:30px 0 12px;padding-left:12px;border-left:4px solid var(--gold)',
         'color:var(--primary);margin:30px 0 12px;padding-left:12px;border-left:4px solid var(--primary)'),
        ('border-bottom:2px solid var(--gold);color:var(--gold)',
         'border-bottom:2px solid var(--primary);color:var(--primary)'),
        ('font-weight:bold;color:var(--gold)}', 'font-weight:bold;color:var(--primary)}'),
    ],
}

# ---- 驗收：殘留 legacy 殼色應為 0 ----
LEGACY_KEYS = ['0a0e17', '111520', '1a1f2e', '1e2433', '64b5f6', '90caf9',
               'd0d0d0', '4CAF50', 'FF5722', '2ecc71', 'f39c12', 'e74c3c']


def apply_global_hex(html):
    """全域 hex remap（case-insensitive），回 (新html, 替換總數)"""
    n = 0
    for old, new in GLOBAL_HEX_CI.items():
        pat = re.compile('#' + old, re.IGNORECASE)
        html, k = pat.subn('#' + new, html)
        n += k
    for old, new in CASE_SENSITIVE:
        html, k = re.subn(re.escape(old), new, html)
        n += k
    return html, n


def apply_literals(html, page):
    n = 0
    for old, new in VAR_LITERALS + PAGE_RULES.get(page, []):
        html, k = re.subn(re.escape(old), new, html)
        n += k
    return html, n


def inject_tokens_link(html):
    """喺 sidebar.css link 之後插 tsa_tokens.css（有 guard＝冪等）"""
    if 'tsa_tokens.css' in html:
        return html, 0
    m = re.search(r'<link[^>]*sidebar\.css[^>]*>', html)
    if not m:
        return html, 0
    tag = m.group(0)
    ins = tag + '\n<link rel="stylesheet" href="tsa_tokens.css">'
    return html.replace(tag, ins, 1), 1


def verify(page, orig, new):
    ok = True
    msgs = []
    if '</html>' not in new:
        ok = False; msgs.append('缺 </html>')
    for tag in ('<style', '</style>', '<table', '<script'):
        if new.count(tag) != orig.count(tag):
            ok = False; msgs.append(f'{tag} 數量變咗 {orig.count(tag)}→{new.count(tag)}')
    if abs(len(new) - len(orig)) > len(orig) * 0.03:
        ok = False; msgs.append(f'體積異動 {len(orig)}→{len(new)}')
    resid = {k: len(re.findall('#' + k, new, re.IGNORECASE)) for k in LEGACY_KEYS}
    resid = {k: v for k, v in resid.items() if v}
    if resid:
        ok = False; msgs.append(f'殘留 legacy: {resid}')
    return ok, msgs


def main():
    dry = '--dry' in sys.argv
    vonly = '--verify' in sys.argv
    pages = TOKENS_INJECT + HEX_ONLY
    report = []
    for page in pages:
        p = DOCS / page
        orig = p.read_text(encoding='utf-8')
        if vonly:
            ok, msgs = verify(page, orig, orig)
            report.append((page, 'verify-only', ok, msgs))
            continue
        html = orig
        html, n_hex = apply_global_hex(html)
        html, n_lit = apply_literals(html, page)
        n_inj = 0
        if page in TOKENS_INJECT:
            html, n_inj = inject_tokens_link(html)
        ok, msgs = verify(page, orig, html)
        changed = (html != orig)
        if changed and not dry:
            p.write_text(html, encoding='utf-8')
        report.append((page, f'hex={n_hex} lit={n_lit} inj={n_inj} '
                        f'delta={len(html)-len(orig):+d}B', ok, msgs))
    print(f'{"頁":<28}{"動作":<34}{"驗收"}')
    for page, act, ok, msgs in report:
        flag = 'PASS' if ok else 'FAIL ' + '; '.join(msgs)
        print(f'{page:<28}{act:<34}{flag}')
    fails = [r for r in report if not r[2]]
    print(f'\n{len(report)} 頁處理，{len(fails)} 頁 FAIL')
    if dry:
        print('（dry-run——無寫檔）')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
