#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批1 截圖像素級驗證——nav 橫條顏色/全出血/aria-current 藍字/body bg"""
from PIL import Image
from pathlib import Path
import sys

SHOTS = Path("/home/z/my-project/scripts/scan_out/shots")
NAV_BG = (22, 30, 46)      # #161E2E
CUR_BLUE = (92, 168, 255)  # #5CA8FF
BODY_BG = (15, 21, 32)     # #0F1520

def close(a, b, tol=6):
    return all(abs(x - y) <= tol for x, y in zip(a, b))

fails = []
def chk(c, m):
    print(("  [PASS] " if c else "  [FAIL] ") + m)
    if not c: fails.append(m)

for name in ["P1_forex_news", "P2_ccy_power", "P3_projection", "P4_signal_ranking"]:
    img = Image.open(SHOTS / f"batch1r2_{name}_top.png").convert("RGB")
    w, h = img.size
    print(f"== {name} ({w}x{h}) ==")
    px = img.load()
    # 1) nav 橫條：y=24 掃 x=10..w-10，#161E2E 佔比 ≥85%（其餘係連結文字像素）
    nav_hits = sum(1 for x in range(10, w - 10, 4) if close(px[x, 24], NAV_BG))
    nav_total = len(range(10, w - 10, 4))
    chk(nav_hits / nav_total >= 0.85, f"nav 橫條 #161E2E 佔比 {nav_hits/nav_total:.0%}（y=24，餘為文字像素）")
    # 2) 全出血：x=2 與 x=w-3 都係 nav 色
    chk(close(px[2, 24], NAV_BG) and close(px[w - 3, 24], NAV_BG), "nav 全出血（左右邊緣無縫）")
    # 3) 頂行無白邊：y=1 掃描，非白
    top = [px[x, 1] for x in range(10, w - 10, 40)]
    chk(all(not (c[0] > 200 and c[1] > 200 and c[2] > 200) for c in top), "頂行無白邊（y=1）")
    # 4) aria-current 藍字存在於 nav 帶（y=8..40 掃全寬）；projection 無自連結→改驗灰色連結文字 #A8B4C4
    if name == "P3_projection":
        grey = any(close(px[x, y], (168, 180, 196), 26)
                   for y in range(8, 40, 2) for x in range(10, w - 10, 3))
        chk(grey, "nav 帶內灰色連結文字 #A8B4C4（projection 無自連結，預期無藍字）")
    else:
        blue = any(close(px[x, y], CUR_BLUE, 22)
                   for y in range(8, 40, 2) for x in range(10, w - 10, 3))
        chk(blue, "aria-current 藍字 #5CA8FF 喺 nav 帶內")
    # 5) nav 下 body 背景：y=70 掃描 #0F1520 為主（容許卡片色）
    body_hits = sum(1 for x in range(10, w - 10, 8)
                    if close(px[x, 70], BODY_BG) or close(px[x, 70], NAV_BG) or close(px[x, 70], (28, 38, 56)))
    chk(body_hits / len(range(10, w - 10, 8)) >= 0.5, f"nav 下深色背景基調（y=70 命中 {body_hits}）")

print()
if fails:
    print(f"PIXEL VERIFY FAILED：{len(fails)}"); sys.exit(1)
print("PIXEL VERIFY PASS — 4 頁截圖 nav 觀感全綠")
