#!/usr/bin/env python3
"""w8_dark_fix_apply_20261105.py — 暗調殘白修復殼級批量 patch（1848／2012 定稿）

範圍：docs/reports/index_*.html 151 頁 Template A v2 殼（排除 3 頁舊格式殘頁
36512/36655/5117——另信匯報，唔塞入本單）。
動作（每頁恰 1+1）：
  1. .chart-plate{background:#fff;...} → var(--card2)＋svg line/text theme-aware 兩條
  2. foot gen_date 2026-11-02 → 2026-11-05
機器閘：除 3 舊殼頁外逐頁 A_css_bg=0；新規則每頁恰 1 組。
"""
import re
import sys
from pathlib import Path

BASE = Path('/home/z/my-project/exchange-repo/docs/reports')
SKIP = {'index_36512.html', 'index_36655.html', 'index_5117.html'}  # 舊殼殘頁，另報

OLD_CSS = '.chart-plate{background:#fff;border-radius:8px;padding:10px}'
NEW_CSS = ('.chart-plate{background:var(--card2);border-radius:8px;padding:10px}\n'
           '.chart-plate svg line[stroke="#e8e8e8"]{stroke:var(--brd)}\n'
           '.chart-plate svg text[fill="#999"]{fill:var(--text2)}')
OLD_FOOT = 'Template A v2（零 JS 靜態版） · 2026-11-02'
NEW_FOOT = 'Template A v2（零 JS 靜態版） · 2026-11-05'

ok, bad = 0, []
for f in sorted(BASE.glob('index_*.html')):
    if f.name in SKIP:
        continue
    s = f.read_text(encoding='utf-8')
    n_css = s.count(OLD_CSS)
    n_foot = s.count(OLD_FOOT)
    if n_css != 1 or n_foot != 1:
        bad.append((f.name, f'css={n_css} foot={n_foot}'))
        continue
    s2 = s.replace(OLD_CSS, NEW_CSS).replace(OLD_FOOT, NEW_FOOT)
    # 驗證新規則在位且無殘留
    assert '.chart-plate{background:var(--card2)' in s2
    assert 'line[stroke="#e8e8e8"]' in s2 and 'text[fill="#999"]' in s2
    assert not re.search(r'background(?:-color)?\s*:\s*#fff(?![0-9a-fA-F])', s2, re.I), f'{f.name} 仍有 A 類殘留'
    f.write_text(s2, encoding='utf-8')
    ok += 1

print(f'patched: {ok} / {ok + len(bad)}  (skip 舊殼 3 頁)')
for n, why in bad:
    print(f'  ✗ {n}: {why}')
sys.exit(1 if bad else 0)
