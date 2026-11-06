#!/usr/bin/env python3
"""tbnav_a_20261106.py — TBNAV A 案頁層施工（ZCODE_w，0922 老闆拍板「除 sidebar 留頂部 NAV」）

照 P-1b 慣例（20261105_1325 出貨信三步法）：
  1. plaintext 底（解密 live board，caller 先跑 decrypt_page.mjs -o /tmp/board_now.html）
  2. 三處精準替換（對應 generator v3.3 模板位——W5-I sidebar 三件除，方案 C 頂部 NAV 保留）
  3. 純度斷言（除三處外 byte 一致＋cards/kpi/rows 計數不變＋NAV 三件保留）
  寫回 docs/admin/tasks_board.html（plaintext）→ caller 跑 encrypt_admin_pages.sh 重加密。

用法：python3 scripts/tbnav_a_20261106.py          # 實跑
      python3 scripts/tbnav_a_20261106.py --dry   # 只報告唔寫檔
      python3 scripts/tbnav_a_20261106.py --verify # 獨立驗收（重掃殘留）
"""
import sys, re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
PLAIN = Path('/tmp/board_now.html')
OUT = BASE / 'docs' / 'admin' / 'tasks_board.html'
DRY = '--dry' in sys.argv
VERIFY = '--verify' in sys.argv

# 三處替換（與 generator v3.3 輸出位一一對應）
R1_OLD = ('<!-- W5-I（2026-11-05）：NAV 三件 1+2——sidebar.css；tokens 豁免'
          '（自帶 --l0 canonical 族照 W5-H 先例；本檔模板層同步，TASKS.md 重生成唔沖走） -->\n'
          '<link rel="stylesheet" href="../sidebar.css">\n')
R1_NEW = ('<!-- TBNAV A 案（2026-11-06 老闆拍板）：W5-I sidebar.css 三件已除，'
          '方案 C 頂部 NAV 唯一導航 -->\n')
R2_OLD = ('</head><body><!-- W5-I：NAV 之 #sidebar-container -->\n'
          '<div id="sidebar-container"></div>\n\n')
R2_NEW = '</head><body>\n\n'
R3_OLD = '<script src="../sidebar.js"></script>\n</body></html>'
R3_NEW = '</body></html>'

def counters(s):
    return {
        'cards_h2': len(re.findall(r'<h2', s)),
        'rows': len(re.findall(r'class="row[ "]', s)),
        'kpis': len(re.findall(r'class="kpi[ "]', s)),
        'nav_links': len(re.findall(r'<nav class="nav"', s)),
        'drawer': len(re.findall(r'id="navDrawer"', s)),
    }

def verify():
    src = OUT.read_text(encoding='utf-8') if OUT.exists() else ''
    checks = [
        ('sidebar.css 已除', '../sidebar.css' not in src),
        ('sidebar.js 已除', '../sidebar.js' not in src),
        ('sidebar-container 已除', 'sidebar-container' not in src),
        ('舊 W5-I 注入 comment 已除', 'NAV 三件 1+2' not in src),
        ('TBNAV A 記錄在位', 'TBNAV A 案' in src),
        ('方案 C NAV HTML 保留', '<nav class="nav"' in src),
        ('NAV drawer 保留', 'id="navDrawer"' in src),
        ('KPI 區保留', 'class="kpis"' in src),
        ('v3.3 GEN 串', 'tasks_board_gen v3.3' in src),
    ]
    ok = all(r for _, r in checks)
    for n, r in checks:
        print(f'  [{"PASS" if r else "FAIL"}] {n}')
    print('VERIFY', 'PASS' if ok else 'FAIL')
    return ok

if VERIFY:
    sys.exit(0 if verify() else 1)

src = PLAIN.read_text(encoding='utf-8')
before = counters(src)
n1 = src.count(R1_OLD); n2 = src.count(R2_OLD); n3 = src.count(R3_OLD)
print(f'命中：R1 sidebar.css={n1}｜R2 container={n2}｜R3 sidebar.js={n3}')
if (n1, n2, n3) != (1, 1, 1):
    print('❌ 命中數唔係各 1——板面結構與預期唔符，停低唔寫')
    sys.exit(1)
out = src.replace(R1_OLD, R1_NEW).replace(R2_OLD, R2_NEW).replace(R3_OLD, R3_NEW)
after = counters(out)
for k in before:
    flag = 'PASS' if before[k] == after[k] else 'FAIL'
    print(f'  [{flag}] 計數 {k}: {before[k]} -> {after[k]}')
if before != after:
    print('❌ 計數變化——停低唔寫')
    sys.exit(1)
delta = len(out) - len(src)
print(f'byte_delta {delta:+d}（預期 ≈ -400：三件除＋TBNAV 記錄加）')
if not DRY:
    OUT.write_text(out, encoding='utf-8')
    print(f'✅ 已寫 {OUT}（{len(out):,}B）——下一步：encrypt_admin_pages.sh 重加密')
else:
    print(f'[dry] 未寫檔')
