#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w6_label_fix_shots_20261105.py — v2.1 撞色修復 browser 實測截圖

對 /tmp/home_plain.html（v2.1 修復後 plaintext）HTTP serve＋playwright 截圖：
  f1 全頁（desktop 1280）  f2 地圖模組特寫  f3 tooltip hover 幀
舊幀對照用 from_zcode/w6_map_v2_20261105/ 原四幀。
"""
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SRC = Path('/tmp/home_plain.html')
OUT = Path('/tmp/w6fix_shots')
OUT.mkdir(exist_ok=True)

srv = subprocess.Popen(
    ['python3', '-m', 'http.server', '8093', '--directory', '/tmp'],
    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)

try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={'width': 1280, 'height': 900})
        pg.goto('http://localhost:8093/home_plain.html', wait_until='networkidle')
        pg.wait_for_timeout(1500)

        # 斷言一：halo CSS 三條在場＋象牙白 fill
        n = pg.evaluate("document.documentElement.outerHTML.split('paint-order:stroke').length-1")
        print(f'paint-order:stroke 出現 {n} 處（應 3）')
        lbl = pg.evaluate(
            "getComputedStyle(document.querySelector('.map-lbl')||document.createElement('i')).fill"
        ) if pg.query_selector('.map-lbl') else '（標籤由 JS 遲生成）'
        print(f'.map-lbl fill（若有）: {lbl}')

        # 等標籤 JS 跑完（標籤 IIFE 同步，fetch 數據非必需）
        pg.wait_for_timeout(800)

        # f1 全頁
        pg.screenshot(path=str(OUT / 'f1_full.png'), full_page=False)
        # f2 地圖模組特寫
        mod = pg.query_selector('.map-mod')
        if mod:
            mod.screenshot(path=str(OUT / 'f2_mapmod.png'))
            box = mod.bounding_box()
            print(f'map-mod box: {box}')
        # f3 地圖 svg wrap 特寫（放大）
        wrap = pg.query_selector('.map-svg-wrap')
        if wrap:
            wrap.screenshot(path=str(OUT / 'f3_wrap.png'))

        # 斷言二：canvas 有繪製（非白屏）＋ world-map path 在場
        cnt = pg.evaluate("document.querySelectorAll('#world-map path').length")
        cc = pg.evaluate("!!document.getElementById('mapCanvas')")
        print(f'world-map path {cnt} 條／mapCanvas {cc}')
        b.close()
finally:
    srv.terminate()

print('shots ->', OUT)
