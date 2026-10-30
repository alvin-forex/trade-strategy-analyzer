#!/usr/bin/env python3
"""verify_phase1_encrypted.py — Phase 1 加密態驗收（老闆流程）

1.4 staticrypt 深色密碼頁：閘面配色跟 tokens（非白屏）、無白底閃跳；
    remember checkbox 在位（30 日）。
1.1 加密後首頁功能完整：密碼 → 解密 → NAV/地圖/健康燈/chips 全渲染。
"""
import asyncio, subprocess, sys, time, os, signal
from playwright.async_api import async_playwright

PW_GENERAL = open("/home/z/my-project/.keys/tsa_pw_general.txt").read().strip()
PORT = 8794
BASE = f"http://127.0.0.1:{PORT}/trade-strategy-analyzer/"

RESULTS = []
def check(name, ok, extra=""):
    RESULTS.append((name, bool(ok)))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  ' + extra if extra else ''}")

async def main():
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1",
         "--directory", "/tmp/pages_root"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1280, "height": 800})
            await page.goto(BASE + "index.html", wait_until="domcontentloaded")
            await page.wait_for_selector("#staticrypt-password", timeout=8000)

            # --- 1.4 深色閘面 ---
            gate_bg = await page.eval_on_selector(
                ".staticrypt-content", "e => getComputedStyle(e).backgroundColor")
            check("gate_dark_bg", gate_bg == "rgb(15, 21, 32)", gate_bg)  # #0F1520
            form_bg = await page.eval_on_selector(
                ".staticrypt-form", "e => getComputedStyle(e).backgroundColor")
            check("gate_form_dark", form_bg == "rgb(22, 30, 46)", form_bg)  # #161E2E
            title_color = await page.eval_on_selector(
                ".staticrypt-title", "e => getComputedStyle(e).color")
            check("gate_title_light", title_color == "rgb(230, 237, 245)", title_color)
            btn_bg = await page.eval_on_selector(
                ".staticrypt-decrypt-button", "e => getComputedStyle(e).backgroundColor")
            check("gate_button_info", btn_bg == "rgb(92, 168, 255)", btn_bg)
            await page.screenshot(path="/home/z/my-project/download/新首頁Phase1_深色密碼頁.png")

            # remember checkbox（隱藏直至 gate 顯示；gate 已示）
            cb = await page.query_selector("#staticrypt-remember")
            cb_visible = await cb.is_visible() if cb else False
            check("gate_remember_checkbox", cb_visible)
            # 閘面唔係白屏：body 背景唔係 white
            body_bg = await page.evaluate("() => getComputedStyle(document.body).backgroundColor")
            check("gate_no_white_flash", body_bg != "rgb(255, 255, 255)", body_bg)

            # --- 解密 → 首頁 ---
            await page.fill("#staticrypt-password", PW_GENERAL)
            await page.click(".staticrypt-decrypt-button")
            await page.wait_for_selector(".nav", timeout=10000)
            await page.wait_for_timeout(1000)

            nav_n = await page.eval_on_selector_all(".nav > a", "els => els.length")
            check("decrypted_nav_6", nav_n == 6)
            labels = await page.eval_on_selector_all("#world-g8 text.map-lbl", "els => els.map(e => e.textContent)")
            check("decrypted_map_labels", sorted(labels) == sorted(["USD","EUR","JPY","GBP","CHF","AUD","CAD","NZD"]))
            await page.wait_for_timeout(800)
            pills = await page.eval_on_selector_all("#pills .pill", "els => els.length")
            check("decrypted_health_5", pills == 5)
            chips = await page.eval_on_selector_all(".chips-row .chip", "els => els.length")
            check("decrypted_chips_9", chips == 9)

            # 加密態 drawer＋分析器交接
            await page.click("#uploadBtn")
            await page.wait_for_timeout(350)
            await page.set_input_files("#csvInput", "/tmp/phase1_files/trades_test.csv")
            await page.set_input_files("#setInput", "/tmp/phase1_files/ea_test.set")
            await page.wait_for_timeout(250)
            st = await page.locator("#drawerStatus").inner_text()
            check("encrypted_drawer_status", "1 份 CSV" in st and "1 份 SET" in st, st)
            await page.click("#analyzeBtn")
            await page.wait_for_timeout(2500)
            frame = None
            for f in page.frames:
                if f.url.endswith("analyzer.html"):
                    frame = f
            az = 0
            if frame:
                az = await frame.eval_on_selector_all("#fileChips .chip", "els => els.length")
            check("encrypted_analyzer_handoff", az >= 2, f"{az} chips")

            # 390 溢出抽查（加密態）
            await page.set_viewport_size({"width": 390, "height": 844})
            await page.wait_for_timeout(300)
            sw, cw = await page.evaluate(
                "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
            check("encrypted_390_no_overflow", sw <= cw, f"sw={sw} cw={cw}")

            # 加密態截圖（解密後首頁）
            await page.set_viewport_size({"width": 1280, "height": 800})
            await page.wait_for_timeout(300)
            await page.screenshot(path="/home/z/my-project/download/新首頁Phase1_加密態解密後1280.png")
            await browser.close()
    finally:
        server.send_signal(signal.SIGTERM)
        server.wait(timeout=5)

    n_ok = sum(1 for _, ok in RESULTS if ok)
    print(f"\n=== PHASE 1 加密態驗收 {n_ok}/{len(RESULTS)} ===")
    sys.exit(0 if n_ok == len(RESULTS) else 1)

asyncio.run(main())
