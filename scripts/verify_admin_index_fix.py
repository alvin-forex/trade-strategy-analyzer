#!/usr/bin/env python3
"""verify_admin_index_fix.py — 1e7f7d9 regression fix e2e verification.

Boss flow: /trade-strategy-analyzer/ root gate → shell → iframe admin gate
→ transitional homepage. Asserts: zero 404, zero /admin/admin/ requests,
5 health lights, 8 quick cards, remember checkbox present.
"""
import asyncio, subprocess, sys, time, json, os, signal
from playwright.async_api import async_playwright

REPO = "/home/z/my-project/exchange-repo/docs"
PW_GENERAL = open("/home/z/my-project/.keys/tsa_pw_general.txt").read().strip()
PORT = 8791
BASE = f"http://127.0.0.1:{PORT}/trade-strategy-analyzer/"

import os
os.makedirs("/tmp/pages_root", exist_ok=True)
if os.path.islink("/tmp/pages_root/trade-strategy-analyzer"):
    os.remove("/tmp/pages_root/trade-strategy-analyzer")
os.symlink(REPO, "/tmp/pages_root/trade-strategy-analyzer")

async def main():
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1", "--directory", "/tmp/pages_root"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)
    results, req_log = [], []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()
            page = await browser.new_page(viewport={"width": 1280, "height": 800})
            page.on("response", lambda r: req_log.append((r.url, r.status)))
            # 1. root gate
            await page.goto(BASE + "index.html", wait_until="domcontentloaded")
            await page.wait_for_selector("#staticrypt-password", timeout=8000)
            # 2. enter password at root gate
            await page.fill("#staticrypt-password", PW_GENERAL)
            await page.click(".staticrypt-decrypt-button")
            await page.wait_for_timeout(1500)
            shell_ok = "contentFrame" in (await page.content())
            results.append(("root_gate_decrypt_shell", shell_ok))
            # 3. iframe loads admin/index.html → gate inside iframe
            frame = None
            for _ in range(20):
                for f in page.frames:
                    if f.url.endswith("admin/index.html"):
                        frame = f
                        break
                if frame:
                    break
                await page.wait_for_timeout(300)
            results.append(("iframe_admin_loaded", frame is not None))
            if frame is None:
                raise SystemExit("FAIL: iframe admin/index.html never loaded")
            await frame.wait_for_selector("#staticrypt-password", timeout=8000)
            # remember checkbox present
            cb = await frame.query_selector("#staticrypt-remember")
            results.append(("remember_checkbox_in_admin_gate", cb is not None))
            # 4. enter password in iframe gate
            await frame.fill("#staticrypt-password", PW_GENERAL)
            await frame.click(".staticrypt-decrypt-button")
            await frame.wait_for_timeout(1500)
            # 5. transitional homepage markers (pills render after health.json fetch)
            await frame.wait_for_timeout(1200)
            pill_count = await frame.locator(".pill").count()
            st_when = await frame.locator("#stWhen").inner_text()
            results.append(("health_pills_5", pill_count >= 5))
            results.append(("checked_at_rendered", "讀取中" not in st_when and len(st_when.strip()) > 0))
            card_count = await frame.locator(".grid .card").count()
            results.append(("quick_cards_8", card_count >= 8))
            content = await frame.content()
            results.append(("no_admin_admin_url", "admin/admin/" not in content))
            # 6. request log: zero 404, zero admin/admin/
            statuses404 = [u for u, s in req_log if s == 404]
            results.append(("zero_http_404", len(statuses404) == 0))
            results.append(("zero_admin_admin_requests", all("admin/admin/" not in u for u, _ in req_log)))
            # 7. screenshot for the boss
            await page.screenshot(path="/home/z/my-project/download/驗證_首頁修復_1280.png", full_page=False)
            if statuses404:
                results.append(("debug_404_list", False))
            await browser.close()
    finally:
        server.send_signal(signal.SIGTERM)
        server.wait(timeout=5)
    print("=== REQUEST LOG (non-200) ===")
    for u, s in req_log:
        if s != 200:
            print(f"  {s} {u}")
    n_ok = sum(1 for _, ok in results if ok)
    print(f"=== RESULTS {n_ok}/{len(results)} ===")
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
    sys.exit(0 if n_ok == len(results) else 1)

asyncio.run(main())
