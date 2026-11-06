#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W-FINAL 批 0：root 族特徵分析分類（讀 batch0_root_raw.txt）"""
import urllib.parse, sys
from collections import Counter

RAW = "/home/z/my-project/exchange-repo/exchange/from_zcode/wfinal_batch0_shots_20261107/batch0_root_raw.txt"
OUT = "/home/z/my-project/exchange-repo/exchange/from_zcode/wfinal_batch0_shots_20261107/batch0_root_classified.csv"

rows = []
for line in open(RAW, encoding="utf-8").read().strip().splitlines():
    parts = line.split("|")
    page = parts[0].strip()
    vals = [urllib.parse.unquote(v) for v in parts[1:]]
    d = dict(zip(["htmlBg", "bodyBg", "card2", "accent", "accent2", "bodyClass", "hasNav", "hasSidebar", "h1"], (vals + [""] * 9)[:9]))
    d["page"] = page
    rows.append(d)

print(f"總數: {len(rows)}")
print("bodyBg top8:", Counter(r["bodyBg"] for r in rows).most_common(8))
print("card2  top8:", Counter(r["card2"] for r in rows).most_common(8))
print()

def is_new(r):
    return "rgb(15, 21, 32)" in {r["htmlBg"], r["bodyBg"]} and r["card2"] == "#1C2638"

new_rows = [r for r in rows if is_new(r)]
old_rows = [r for r in rows if not is_new(r)]
print(f"★ 跟新設計特徵: {len(new_rows)} 頁 | ★ 唔跟: {len(old_rows)} 頁")
print()
print("【唔跟新設計·root 族】:")
for r in old_rows:
    print(f'  {r["page"][:44]:<44} body={r["bodyBg"][:20]:<20} card2={r["card2"][:9]!r:<11} accent={r["accent"][:9]!r}')
print()
print("【跟新設計特徵·root 族】:")
for r in new_rows:
    print(f'  {r["page"][:60]}')

with open(OUT, "w", encoding="utf-8") as f:
    f.write("page,htmlBg,bodyBg,card2,accent,accent2,bodyClass,hasNav,hasSidebar,h1,classified\n")
    for r in rows:
        cls = "NEW_DESIGN" if is_new(r) else "OLD_DESIGN"
        f.write(",".join([r["page"], r["htmlBg"].replace(",", " "), r["bodyBg"].replace(",", " "), r["card2"], r["accent"], r["accent2"], r["bodyClass"].replace(",", ";"), r["hasNav"], r["hasSidebar"], r["h1"].replace(",", ";"), cls]) + "\n")
print(f"\nCSV 已寫: {OUT}")
