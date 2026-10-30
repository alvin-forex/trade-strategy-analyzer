#!/usr/bin/env python3
"""live_verify_phase1.py — Phase 1 線上（GitHub Pages）老闆流程最終把關"""
import asyncio, sys
from playwright.async_api import async_playwright

PW_GENERAL = open("/home/z/my-project/.keys/tsa_pw_general.txt").read().strip()
LIVE = "https://alvin-forex.github.io/trade-strategy-analyzer/index.html"

async def main():
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.goto(LIVE, wait_until="domcontentloaded")
        await page.wait_for_selector("#staticrypt-password", timeout=15000)
        results.append(("live_gate_dark", await page.eval_on_selector(
            ".staticrypt-content", "e => getComputedStyle(e).backgroundColor") == "rgb(15, 21, 32)"))
        await page.fill("#staticrypt-password", PW_GENERAL)
        await page.click(".staticrypt-decrypt-button")
        await page.wait_for_selector(".nav", timeout=15000)
        await page.wait_for_timeout(1200)
        results.append(("live_nav_6", await page.eval_on_selector_all(".nav > a", "els => els.length") == 6))
        results.append(("live_map_labels", sorted(await page.eval_on_selector_all(
            "#world-g8 text.map-lbl", "els => els.map(e => e.textContent)")) ==
            sorted(["USD","EUR","JPY","GBP","CHF","CAD","AUD","NZD"])))
        results.append(("live_health_5", await page.eval_on_selector_all("#pills .pill", "els => els.length") == 5))
        results.append(("live_chips_9", await page.eval_on_selector_all(".chips-row .chip", "els => els.length") == 9))
        # 390 live overflow
        await page.set_viewport_size({"width": 390, "height": 844})
        await page.wait_for_timeout(300)
        sw, cw = await page.evaluate(
            "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        results.append(("live_390_no_overflow", sw <= cw))
        await page.screenshot(path="/home/z/my-project/download/新首頁Phase1_LIVE_390首屏.png")
        await browser.close()
    n = sum(1 for _, ok in results if ok)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    print(f"=== LIVE {n}/{len(results)} ===")
    sys.exit(0 if n == len(results) else 1)

asyncio.run(main())
