# -*- coding: utf-8 -*-
"""extract_g8_map.py——8 大貨幣國簡化 SVG 提取（首頁 v1.1 事件地理層素材）。

輸入：download/map_asset/menelabs_original.svg（Menelabs.VectorAtlas dist/world.svg，
      CC BY 4.0，Natural Earth public domain 衍生）
輸出：world_g8.svg（淨 8 貨幣國＋歐元區核心 4 國 path，零座標改動）
      ＋stdout 證據行（清理前後大小／sha256）——落六項證據表用。

8 大貨幣（v1.1 設計基準）：USD/CAD/JPY/GBP/CHF/AUD/NZD/EUR
EUR 素材備歐元區核心 4 國（DE/FR/IT/ES）——Phase 2.2 設計時揀聚合定代表點。
"""
import hashlib
import re
import sys

SRC = "/home/z/my-project/download/map_asset/menelabs_original.svg"
DST = "/home/z/my-project/download/map_asset/world_g8.svg"
KEEP = ["us", "ca", "jp", "gb", "ch", "au", "nz", "de", "fr", "it", "es"]
LABELS = {"us": "USD", "ca": "CAD", "jp": "JPY", "gb": "GBP", "ch": "CHF",
          "au": "AUD", "nz": "NZD", "de": "EUR-DE", "fr": "EUR-FR",
          "it": "EUR-IT", "es": "EUR-ES"}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    with open(SRC, encoding="utf-8") as f:
        src = f.read()
    vb = re.search(r'viewBox="([^"]+)"', src)
    if not vb:
        print("❌ viewBox 搵唔到")
        sys.exit(1)
    # 每國一個 <path id="xx" d="..."/>——d 屬性原文保留（零座標改動）
    paths = {}
    for m in re.finditer(r'<path id="([a-z]{2})" d="([^"]+)"/>', src):
        paths[m.group(1)] = m.group(2)
    missing = [k for k in KEEP if k not in paths]
    if missing:
        print(f"❌ 目標國 path 缺：{missing}")
        sys.exit(1)
    out = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="%s" id="world-g8">' % vb.group(1)]
    out.append("  <!-- Source: Menelabs.VectorAtlas dist/world.svg (Natural Earth public domain data)")
    out.append("       License: CC BY 4.0 - https://creativecommons.org/licenses/by/4.0/")
    out.append("       Attribution: Menelabs VectorAtlas https://github.com/melenaos/Menelabs.VectorAtlas -->")
    for k in KEEP:
        out.append('  <path id="%s" data-ccy="%s" d="%s"/>' % (k, LABELS[k], paths[k]))
    out.append("</svg>")
    with open(DST, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    pre_b = len(open(SRC, "rb").read())
    post_b = len(open(DST, "rb").read())
    print(f"清理前：{pre_b:,} bytes｜sha256={sha256(SRC)}")
    print(f"清理後：{post_b:,} bytes｜sha256={sha256(DST)}")
    print(f"國家數：{len(KEEP)}（8 貨幣國＋EUR 核心 4 國）｜壓縮 {(1 - post_b / pre_b) * 100:.0f}%")


if __name__ == "__main__":
    main()
