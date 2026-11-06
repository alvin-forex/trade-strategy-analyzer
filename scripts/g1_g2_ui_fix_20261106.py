#!/usr/bin/env python3
"""g1_g2_ui_fix_20261106.py — 0926 掃尾派工 G1+G2（ZCODE_w）

G1 docs/projection.html（root 主功能頁，明文 13KB）：
  - :root 自定義變量 → 標準 [data-theme=dark/light] 兩段（P0 canonical 色源）
  - 死 hex remap：th/fbar #1c2937→bg-hover、td #1b2634→border、hover #1a2735→bg-hover、
    a.sig #4a9eda/#7cc3f0→primary/accent、bar #2b3a4c→border、badge.na/lamp.off 灰系→token
  - head 末位 tsa_tokens.css（覆蓋標記）＋tsa-theme JS（default dark，跟 forex_news 模式）
  - NAV 方案 C 區不動（P3 拍板正本）；.bar>i 數據 bar gradient 留（圖表語義域）
G2 docs/forex_reports/index.html（家族索引，8KB）：
  - 照 W5/REG-187 同族日期頁注入模式：sidebar.css＋tsa_tokens.css（../ 相對）＋body 開頭
    #sidebar-container（body 已有 has-sidebar class 不動）

用法：--dry 只報告｜--verify 獨立復掃｜無參數實跑（冪等：已含標記即跳過）
"""
import sys, re
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
P1 = BASE / 'docs' / 'projection.html'
P2 = BASE / 'docs' / 'forex_reports' / 'index.html'

DRY = '--dry' in sys.argv
VERIFY = '--verify' in sys.argv

THEME_JS = '''<script>
(function(){
  const saved=localStorage.getItem('tsa-theme');
  const t=saved||'dark';
  document.documentElement.setAttribute('data-theme',t);
  document.addEventListener('DOMContentLoaded',function(){
    const btn=document.getElementById('theme-toggle');
    if(btn)btn.textContent=t==='dark'?'\\u2600\\uFE0F':'\\uD83C\\uDF19';
  });
})();
function toggleTheme(){
  const cur=document.documentElement.getAttribute('data-theme');
  const next=cur==='dark'?'light':'dark';
  document.documentElement.setAttribute('data-theme',next);
  localStorage.setItem('tsa-theme',next);
  const btn=document.getElementById('theme-toggle');
  if(btn)btn.textContent=next==='dark'?'\\u2600\\uFE0F':'\\uD83C\\uDF19';
}
</script>
<link rel="stylesheet" href="tsa_tokens.css">
</head>'''

OLD_ROOT = ':root{--bg:#0f1620;--card:#16202e;--t1:#e8eef5;--t2:#a8b4c4;--t3:#7a8698;--line:#22303f;--amber:#c98a00;--red:#dc3545;--green:#28a745}'
NEW_ROOT = ('''/* === Unified Theme System（G1 2026-11-06，P0 canonical 色源）=== */
:root{--font-main:'Helvetica Neue','PingFang TC','Noto Sans CJK TC',sans-serif;--radius:8px;--shadow:0 2px 8px rgba(0,0,0,0.12)}
[data-theme="dark"]{--bg:#0F1520;--bg-card:#161E2E;--bg-hover:#1C2638;--text:#E6EDF5;--text2:#A8B4C4;--text3:#7E8CA6;--border:#2A3650;--amber:#EAB308;--red:#EF4444;--green:#22C55E;--primary:#5CA8FF;--accent:#38BDF8;--th-bg:#1C2638}
[data-theme="light"]{--bg:#F1F5F9;--bg-card:#ffffff;--bg-hover:#E2E8F0;--text:#1E293B;--text2:#64748B;--text3:#64748B;--border:#CBD5E1;--amber:#CA8A04;--red:#DC2626;--green:#16A34A;--primary:#2563EB;--accent:#0EA5E9;--th-bg:#E2E8F0}
:root{--bg:#0F1520;--card:#161E2E;--t1:#E6EDF5;--t2:#A8B4C4;--t3:#7E8CA6;--line:#2A3650;--amber:#EAB308;--red:#EF4444;--green:#22C55E}''')

# G1 精準 remap（literal；順序敏感）
G1_RULES = [
    (OLD_ROOT, NEW_ROOT),
    # 變量名對齊標準語義（replace_all 類）
    ('var(--t1)', 'var(--text)'),
    ('var(--t2)', 'var(--text2)'),
    ('var(--t3)', 'var(--text3)'),
    ('var(--line)', 'var(--border)'),
    ('var(--card)', 'var(--bg-card)'),
    # 死 hex remap
    ('background:#1c2937', 'background:var(--bg-hover)'),
    ('border-bottom:1px solid #1b2634', 'border-bottom:1px solid var(--border)'),
    ('tr:hover td{background:#1a2735}', 'tr:hover td{background:var(--bg-hover)}'),
    ('color:#4a9eda;text-decoration:none;border-bottom:1px dotted #4a9eda',
     'color:var(--primary);text-decoration:none;border-bottom:1px dotted var(--primary)'),
    ('a.sig:hover{color:#7cc3f0}', 'a.sig:hover{color:var(--accent)}'),
    ('.bar{height:3px;background:#2b3a4c', '.bar{height:3px;background:var(--border)'),
    ('.badge.na{background:#3a3f46', '.badge.na{background:var(--bg-hover)'),
    ('.lamp.off{background:#555f6b}', '.lamp.off{background:var(--text3)}'),
]

def g1_run():
    s = P1.read_text(encoding='utf-8')
    if 'tsa_tokens.css' in s:
        print('[G1] 已含 tsa_tokens.css — 跳過（冪等）')
        return
    for old, new in G1_RULES:
        n = s.count(old)
        if n == 0 and old != OLD_ROOT:
            print(f'  [G1][warn] 未命中: {old[:60]}')
        if not DRY:
            s = s.replace(old, new)
    if not DRY:
        assert '</head>' in s
        s = s.replace('</head>', THEME_JS, 1)
        P1.write_text(s, encoding='utf-8')
    print(f'[G1] projection.html rules 應用 {len(G1_RULES)} 條（--dry={DRY}）')

G2_LINK = '''<!-- TSA Sidebar -->
<link rel="stylesheet" href="../sidebar.css">
<!-- W3/REG-187（2026-11-05）：tsa_tokens.css（hardcode 殼頁 inert，照 W3 patch 效果規格） -->
<link rel="stylesheet" href="../tsa_tokens.css">
</head>'''

def g2_run():
    s = P2.read_text(encoding='utf-8')
    if 'tsa_tokens.css' in s:
        print('[G2] 已含 tsa_tokens.css — 跳過（冪等）')
        return
    if not DRY:
        s = s.replace('</head>', G2_LINK, 1)
        # body 開頭加 sidebar-container（照同族日期頁）
        old_body = '<body class="has-sidebar">'
        assert old_body in s, 'G2 body 標記唔吻合'
        s = s.replace(old_body,
                      '<body class="has-sidebar">\n<!-- W3/REG-187：NAV 之 #sidebar-container -->\n<div id="sidebar-container"></div>', 1)
        P2.write_text(s, encoding='utf-8')
    print(f'[G2] forex_reports/index.html 注入（--dry={DRY}）')

def verify():
    ok = True
    s1 = P1.read_text(encoding='utf-8')
    checks1 = [
        ('tokens link', 'tsa_tokens.css' in s1),
        ('data-theme dark', '[data-theme="dark"]' in s1),
        ('data-theme light', '[data-theme="light"]' in s1),
        ('theme JS', "localStorage.getItem('tsa-theme')" in s1),
        ('舊 :root 已除', '--bg:#0f1620' not in s1),
        ('死hex #1c2937 已除', '#1c2937' not in s1),
        ('死hex #1a2735 已除', '#1a2735' not in s1),
        ('a.sig 死hex #4a9eda 已除', 'dotted #4a9eda' not in s1 and 'color:#4a9eda' not in s1),
        ('NAV 方案 C 保留', 'NAV BAR 方案 C' in s1),
        ('數據 bar gradient 保留', 'linear-gradient(90deg,#2e6da4,#4a9eda)' in s1),  # 唯一容許 #4a9eda 處
    ]
    s2 = P2.read_text(encoding='utf-8')
    checks2 = [
        ('tokens link', 'tsa_tokens.css' in s2),
        ('sidebar.css', 'sidebar.css' in s2),
        ('container', 'id="sidebar-container"' in s2),
        ('has-sidebar class', 'class="has-sidebar"' in s2),
    ]
    for name, r in checks1 + checks2:
        print(f'  [{"PASS" if r else "FAIL"}] {name}')
        ok = ok and r
    print('VERIFY', 'PASS' if ok else 'FAIL')
    return ok

if VERIFY:
    sys.exit(0 if verify() else 1)
g1_run()
g2_run()
