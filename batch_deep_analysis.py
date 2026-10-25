#!/usr/bin/env python3
"""Batch generate deep analysis reports using Playwright.

Task H v2.00 (ZCODE 2026-10-26): unified official head CSS + back link for all
generated pages (real + placeholder). Tool page index.html <style> is the single
source of truth for placeholder CSS; real pages keep runtime extraction.
"""
import time, os, sys

def generate_one(signal_id, base):
    csv_path = f"{base}/samples/forex-forest-signals-page-{signal_id}.csv"
    out_path = f"{base}/output/index_{signal_id}.html"

    if not os.path.exists(csv_path):
        return ("skip", f"No CSV")

    # Check if CSV has enough data
    with open(csv_path, 'r') as f:
        lines = f.readlines()

    # Task H v2.00: 統一 head CSS＋返回連結——tool 頁 CSS 係唯一真相源（與真頁同一份）
    with open(f"{base}/index.html", 'r') as f:
        template_html = f.read()
    _css_s = template_html.find('<style>')
    _css_e = template_html.find('</style>', _css_s)
    tool_css = template_html[_css_s+7:_css_e] if _css_s >= 0 and _css_e > _css_s else ''

    if len(lines) < 3:
        # Create placeholder（Task H：官方 head＋CSS＋返回連結；原文句子保留）
        html = f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Signal {signal_id} — Trade Strategy Analysis Report</title><style>
{tool_css}
</style></head><body style="max-width:900px;margin:0 auto;padding:20px;font-family:-apple-system,BlinkMacSystemFont,sans-serif">
<p style="margin-bottom:16px"><a href="../index.html" style="color:#0f3460;text-decoration:none;font-weight:600">← 返回主頁</a></p>
<div class="card"><h2>Signal {signal_id}</h2><p>No trading data available (deposit only, no trades executed).</p></div>
</body></html>"""
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w') as f:
            f.write(html)
        return ("placeholder", f"Only {len(lines)} lines (official head + back link)")

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        pg = br.new_page()

        def handle_route(route):
            route.fulfill(body=template_html, content_type="text/html")

        pg.route("http://localhost:8765/**", handle_route)
        pg.goto("http://localhost:8765/index.html")
        pg.wait_for_load_state("networkidle")

        # Upload CSV file
        pg.locator("#csvInput").set_input_files(csv_path)
        time.sleep(1)

        # Enable analyze button
        pg.evaluate("""
            () => {
                const input = document.getElementById('csvInput');
                if (input.files && input.files[0]) {
                    csvFile = input.files[0];
                    document.getElementById('csvZone').classList.add('has-file');
                    document.getElementById('csvZone').querySelector('.label').textContent = csvFile.name;
                }
                document.getElementById('analyzeBtn').disabled = false;
            }
        """)

        # Click analyze
        pg.locator("#analyzeBtn").click()

        # Wait for results (up to 600 seconds)
        for i in range(120):
            time.sleep(5)
            has_results = pg.evaluate("""
                () => document.getElementById('results').innerHTML.trim() !== ''
            """)
            if has_results:
                break

        time.sleep(3)

        # Extract results HTML（Task H v2.00：lang＋signal title＋官方 body font＋返回連結）
        result_html = pg.evaluate("""
            () => {
                const s = document.querySelector('style').textContent;
                const r = document.getElementById('results');
                return '<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>__TITLE__</title><style>' + s + '</style></head><body style="max-width:900px;margin:0 auto;padding:20px;font-family:-apple-system,BlinkMacSystemFont,sans-serif"><p style="margin-bottom:16px"><a href="../index.html" style="color:#0f3460;text-decoration:none;font-weight:600">← 返回主頁</a></p>' + r.innerHTML + '</body></html>';
            }
        """)
        result_html = result_html.replace("__TITLE__", f"Signal {signal_id} — Trade Strategy Analysis Report", 1)

        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w') as f:
            f.write(result_html)

        br.close()

    return ("ok", f"Generated {len(result_html)} bytes")


if __name__ == "__main__":
    BASE = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer"
    SIGNALS = [
        "30503", "36377", "36379", "36510", "36512", "36513", "36519", "36520",
        "36655", "36656", "36657", "36658", "37850", "37851", "38641", "38663",
        "38667", "38683", "38693", "38698", "38699", "38761", "38762", "38897",
        "38900", "43024", "44452", "44453", "44459", "44465"
    ]

    success = []
    placeholders = []
    failed = []

    for sig in SIGNALS:
        out_path = f"{BASE}/output/index_{sig}.html"
        if os.path.exists(out_path):
            print(f"⏭️  {sig}: Already exists, skip", flush=True)
            continue

        print(f"🔄 {sig}...", flush=True, end=" ")
        try:
            status, msg = generate_one(sig, BASE)
            if status == "ok":
                print(f"✅ {msg}", flush=True)
                success.append(sig)
            elif status == "placeholder":
                print(f"⚠️  {msg}", flush=True)
                placeholders.append(sig)
            else:
                print(f"⏭️  {msg}", flush=True)
        except Exception as e:
            err = str(e)[:150]
            print(f"❌ {err}", flush=True)
            failed.append(sig)

        time.sleep(2)

    print(f"\n=== SUMMARY ===", flush=True)
    print(f"✅ Success: {len(success)} — {success}", flush=True)
    print(f"⚠️  Placeholder: {len(placeholders)} — {placeholders}", flush=True)
    print(f"❌ Failed: {len(failed)} — {failed}", flush=True)
