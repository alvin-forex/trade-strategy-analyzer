#!/usr/bin/env python3
"""Generate missing index_{sig}.html reports for 33 signals."""
import os, sys, time, glob
from pathlib import Path

BASE = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer")
TEMPLATE = BASE / "index.html"
OUTPUT_DIR = BASE / "output"
REPORTS_DIR = BASE / "docs" / "reports"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Signal ID -> CSV path (relative to BASE)
SIGNALS = {
    "165": "samples/forex-forest-signals-page-16538.csv",
    "971": "downloads/forex-forest-signals-page-971.csv",
    "1165": "downloads/forex-forest-signals-page-1165.csv",
    "1491": "downloads/forex-forest-signals-page-1491.csv",
    "1584": "downloads/forex-forest-signals-page-1584.csv",
    "2260": "downloads/forex-forest-signals-page-2260.csv",
    "2377": "downloads/forex-forest-signals-page-2377.csv",
    "3736": "downloads/forex-forest-signals-page-3736.csv",
    "4022": "samples/forex-forest-signals-page-4022.csv",
    "4200": "downloads/4200.csv",
    "4666": "downloads/forex-forest-signals-page-4666.csv",
    "4734": "samples/forex-forest-signals-page-4734.csv",
    "5077": "downloads/forex-forest-signals-page-5077.csv",
    "5117": "samples/forex-forest-signals-page-5117.csv",
    "5120": "downloads/forex-forest-signals-page-5120.csv",
    "6797": "downloads/forex-forest-signals-page-6797.csv",
    "7452": "downloads/forex-forest-signals-page-7452.csv",
    "8027": "downloads/forex-forest-signals-page-8027.csv",
    "9085": "downloads/forex-forest-signals-page-9085.csv",
    "9966": "downloads/forex-forest-signals-page-9966.csv",
    "10581": "downloads/forex-forest-signals-page-10581.csv",
    "11103": "downloads/forex-forest-signals-page-11103.csv",
    "11623": "downloads/forex-forest-signals-page-11623.csv",
    "12023": "samples/forex-forest-signals-page-12023.csv",
    "12787": "downloads/forex-forest-signals-page-12787.csv",
    "12888": "downloads/forex-forest-signals-page-12888.csv",
    "13732": "downloads/forex-forest-signals-page-13732.csv",
    "21609": "downloads/forex-forest-signals-page-21609.csv",
    "22828": "downloads/forex-forest-signals-page-22828.csv",
    "26370": "downloads/forex-forest-signals-page-26370.csv",
    "26953": "downloads/forex-forest-signals-page-26953.csv",
    "34206": "downloads/forex-forest-signals-page-34206.csv",
    "38678": "samples/forex-forest-signals-page-38678.csv",
}

def make_placeholder(sig, reason):
    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Signal {sig}</title></head>
<body style="max-width:900px;margin:0 auto;padding:20px;font-family:sans-serif">
<h2>Signal {sig}</h2>
<p>{reason}</p>
</body></html>"""
    return html

def generate_one(sig, csv_path):
    """Generate one report using Playwright."""
    if not os.path.exists(csv_path):
        return ("placeholder", make_placeholder(sig, "No CSV data available."), "No CSV")

    with open(csv_path, 'r') as f:
        lines = f.readlines()
    if len(lines) < 3:
        return ("placeholder", make_placeholder(sig, f"Insufficient data ({len(lines)} lines). Deposit only, no trades executed."), f"{len(lines)} lines")

    # Read template
    with open(TEMPLATE, 'r') as f:
        template_html = f.read()

    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        br = p.chromium.launch(headless=True)
        pg = br.new_page()

        def handle_route(route):
            route.fulfill(body=template_html, content_type="text/html")

        pg.route("http://localhost:8765/**", handle_route)
        pg.goto("http://localhost:8765/index.html")
        pg.wait_for_load_state("networkidle")

        # Upload CSV
        pg.locator("#csvInput").set_input_files(csv_path)
        time.sleep(1)

        # Click analyze
        analyze_btn = pg.locator("#analyzeBtn")
        if analyze_btn.is_visible():
            analyze_btn.click()

        # Wait for results
        try:
            pg.wait_for_selector("#results", state="visible", timeout=30000)
        except:
            br.close()
            return ("placeholder", make_placeholder(sig, "Analysis timeout."), "timeout")

        time.sleep(2)  # Let charts render

        # Extract results
        result_html = pg.evaluate("""
            () => {
                const s = document.querySelector('style') ? document.querySelector('style').textContent : '';
                const r = document.getElementById('results');
                if (!r) return null;
                return '<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Trade Strategy Analysis - Signal %s</title><style>' + s + '</style></head><body style="max-width:900px;margin:0 auto;padding:20px;font-family:sans-serif">' + r.innerHTML + '</body></html>';
            }
        """ % sig)

        br.close()

        if not result_html:
            return ("placeholder", make_placeholder(sig, "No results generated."), "empty results")

        return ("ok", result_html, f"{len(result_html)} bytes")

def main():
    success = []
    placeholders = []
    failed = []

    with open(TEMPLATE, 'r') as f:
        template_html = f.read()

    for sig, csv_rel in SIGNALS.items():
        out_path = OUTPUT_DIR / f"index_{sig}.html"
        reports_path = REPORTS_DIR / f"index_{sig}.html"

        # Skip if already exists in docs/reports
        if reports_path.exists():
            print(f"⏭️  {sig}: Already exists in docs/reports, skip", flush=True)
            continue

        csv_path = str(BASE / csv_rel)
        print(f"🔄 {sig}...", flush=True, end=" ")

        try:
            status, html_content, msg = generate_one(sig, csv_path)
            # Write to both locations
            with open(out_path, 'w') as f:
                f.write(html_content)
            with open(reports_path, 'w') as f:
                f.write(html_content)

            if status == "ok":
                print(f"✅ {msg}", flush=True)
                success.append(sig)
            elif status == "placeholder":
                print(f"⚠️  {msg}", flush=True)
                placeholders.append(sig)
        except Exception as e:
            err = str(e)[:150]
            print(f"❌ {err}", flush=True)
            failed.append(sig)

        time.sleep(1)

    print(f"\n=== SUMMARY ===", flush=True)
    print(f"✅ Success: {len(success)} — {success}", flush=True)
    print(f"⚠️  Placeholder: {len(placeholders)} — {placeholders}", flush=True)
    print(f"❌ Failed: {len(failed)} — {failed}", flush=True)

if __name__ == "__main__":
    main()
