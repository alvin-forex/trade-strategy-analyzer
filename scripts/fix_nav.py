#!/usr/bin/env python3
"""為缺少導航的 detailed_comparison_all_levels 頁面注入 topnav"""

import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"

TOPNAV_CSS = """
<style>
.topnav{display:flex;align-items:center;gap:12px;padding:10px 16px;background:#fff;border-bottom:1px solid #ddd;margin-bottom:16px;position:sticky;top:0;z-index:100;box-shadow:0 2px 8px rgba(0,0,0,0.06)}
.topnav-logo{font-weight:700;font-size:1em;color:#0f3460;text-decoration:none;margin-right:auto}
.topnav-links{display:flex;gap:10px;flex-wrap:wrap}
.topnav-link{color:#666;text-decoration:none;font-size:.88em;font-weight:600;padding:4px 10px;border-radius:6px;transition:all .2s}
.topnav-link:hover{color:#0f3460;background:#eef2f7}
.topnav-link.active{color:#0f3460;background:#eef2f7}
</style>
"""

TOPNAV_HTML = """
<div class="topnav">
<a href="../index.html" class="topnav-logo">🦀 TSA</a>
<div class="topnav-links">
<a href="../signal_ranking.html" class="topnav-link">🏆 Signal 排名</a>
<a href="../ranking_ccy.html" class="topnav-link">💱 CCY 排名</a>
</div>
</div>
"""

count = 0
for html_file in sorted(DOCS_DIR.glob("detailed_comparison_all_levels_*.html")):
    content = html_file.read_text(encoding="utf-8", errors="ignore")
    if "topnav" in content:
        continue

    # Inject CSS before </head>
    if "</head>" in content:
        content = content.replace("</head>", TOPNAV_CSS + "\n</head>", 1)

    # Inject topnav after <body>
    if "<body>" in content:
        content = content.replace("<body>", "<body>" + TOPNAV_HTML, 1)

    html_file.write_text(content, encoding="utf-8")
    count += 1
    print(f"  ✅ {html_file.name}")

print(f"\n完成：共修復 {count} 個檔案")
