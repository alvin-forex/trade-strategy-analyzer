#!/usr/bin/env python3
"""build_phase1_home.py — Phase 1 新首頁建置（TSA 新首頁 v1.1 1.1）

把已驗收嘅 G8 簡化地圖 SVG（exchange/from_zcode/20261029_0935_…/assets/world_g8.svg，
15,500B，Menelabs VectorAtlas CC BY 4.0）inline 注入首頁 <!--WORLD_G8_SVG--> 位置。
注入後檢查：單一 <svg>、id=world-g8 保留、無外部引用。
"""
from pathlib import Path

REPO = Path("/home/z/my-project/exchange-repo")
HOME = REPO / "docs" / "index.html"
SVG = REPO / "exchange/from_zcode/20261029_0935_ZCODE_w_交付_開源地圖素材六項證據/assets/world_g8.svg"

html = HOME.read_text(encoding="utf-8")
svg = SVG.read_text(encoding="utf-8").strip()

assert html.count("<!--WORLD_G8_SVG-->") == 1, "首頁地圖佔位符數量異常"
assert svg.startswith("<svg") and 'id="world-g8"' in svg, "SVG 檔唔符預期"
assert "http" not in svg.replace("http://www.w3.org/2000/svg", "").replace(
    "https://creativecommons.org/licenses/by/4.0/", "").replace(
    "https://github.com/melenaos/Menelabs.VectorAtlas", ""), "SVG 內有預期外嘅外部引用"

out = html.replace("<!--WORLD_G8_SVG-->", svg)
HOME.write_text(out, encoding="utf-8")
size = len(out.encode("utf-8"))
print(f"homepage built: {HOME} ({size} bytes plaintext)")
print(f"map svg injected: {len(svg.encode('utf-8'))} bytes ({size/1024:.1f}KB total plaintext)")
