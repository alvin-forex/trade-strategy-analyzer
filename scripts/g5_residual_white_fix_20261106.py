#!/usr/bin/env python3
# G5 殘白尾清除 2026-11-06 (ZCODE_w) — 0926 掃尾派工 G5
# 三頁範圍外舊殼頁（index_36512/36655/5117）各 2 個 A_css_bg 真兇：
#   :280 .archive-item .ai-actions button  background: #fff -> var(--card)
#   :295 .archive-dup-dialog .add-inner    background: #fff -> var(--card)
# 三頁自帶 light/dark 雙 :root（--card: #fff / #111520），var(--card) 雙主題自動跟。
# 驗證：替換後 (1) 每頁純 #fff css bg = 0 (2) w8_darkbg_scan2 v2 reports A_css_bg = 0
import sys, re

FILES = [
    "docs/reports/index_36512.html",
    "docs/reports/index_36655.html",
    "docs/reports/index_5117.html",
]
HEX = r"\#fff(?:fff)?(?![0-9a-fA-F])"
PAT = re.compile(r"(background(?:-color)?\s*:\s*)" + HEX, re.I)
DRY = "--dry" in sys.argv

total = 0
for f in FILES:
    s = open(f, encoding="utf-8").read()
    hits = PAT.findall(s)
    if DRY:
        for m in PAT.finditer(s):
            ln = s.count("\n", 0, m.start()) + 1
            print(f"  [dry] {f}:{ln}  {m.group(0)}")
    else:
        s2 = PAT.sub(lambda m: m.group(1) + "var(--card)", s)
        open(f, "w", encoding="utf-8").write(s2)
        remain = len(PAT.findall(open(f, encoding="utf-8").read()))
        print(f"  [fix] {f}: replaced {len(hits)}, remaining #fff css-bg {remain}")
        total += len(hits)
    if not DRY:
        total += 0

if not DRY:
    print(f"TOTAL replaced: {total}")
