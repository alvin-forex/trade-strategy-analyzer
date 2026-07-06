#!/usr/bin/env python3
"""Batch generate deep analysis reports for multiple signals."""
import time, os, sys, subprocess

BASE = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer"
SIGNALS = [
    "30503", "36377", "36379", "36510", "36512", "36513", "36519", "36520",
    "36655", "36656", "36657", "36658", "37850", "37851", "38641", "38663",
    "38667", "38683", "38693", "38698", "38699", "38761", "38762", "38897",
    "38900", "43024", "44452", "44453", "44459", "44465"
]

# Python script template for each signal
SCRIPT_TEMPLATE = '''
import time, os
from playwright.sync_api import sync_playwright

SIGNAL_ID = "{sig}"
BASE = "{base}"
CSV_PATH = f"{{BASE}}/samples/forex-forest-signals-page-{{SIGNAL_ID}}.csv"
OUT = f"{{BASE}}/output/index_{{SIGNAL_ID}}.html"

if not os.path.exists(CSV_PATH):
    print(f"SKIP: {{SIGNAL_ID}} - no CSV")
    exit(0)

# Check if CSV has actual trades (more than just header + deposit)
with open(CSV_PATH, "r") as f:
    lines = f.readlines()
if len(lines) < 3:
    print(f"SKIP: {{SIGNAL_ID}} - only {{len(lines)}} lines (no trades)")
    # Create a minimal placeholder report
    html_content = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Signal {{SIGNAL_ID}}</title></head>
<body style="max-width:900px;margin:0 auto;padding:20px;font-family:sans-serif">
<h2>Signal {{SIGNAL_ID}}</h2>
<p>No trading data available (deposit only, no trades executed).</p>
</body></html>"""
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(html_content)
    print(f"PLACEHOLDER: {{OUT}}")
    exit(0)

with open(f"{{BASE}}/index.html", "r") as f:
    html = f.read()

with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    pg = br.new_page()
    pg.route("http://localhost:8765/**", lambda route: route.fulfill(body=html, content_type="text/html"))
    pg.goto("http://localhost:8765/index.html")
    pg.wait_for_load_state("networkidle")
    pg.locator("#csvInput").set_input_files(CSV_PATH)
    time.sleep(1)
    pg.evaluate("""() => {{
        const input = document.getElementById("csvInput");
        if (input.files && input.files[0]) {{
            csvFile = input.files[0];
            document.getElementById("csvZone").classList.add("has-file");
            document.getElementById("csvZone").querySelector(".label").textContent = csvFile.name;
        }}
        document.getElementById("analyzeBtn").disabled = false;
    }}""")
    pg.locator("#analyzeBtn").click()
    for i in range(120):
        time.sleep(5)
        if pg.evaluate("""() => document.getElementById("results").innerHTML.trim() !== """""):
            break
    time.sleep(3)
    r = pg.evaluate("""() => {{
        const s = document.querySelector("style").textContent;
        const r = document.getElementById("results");
        return "<!DOCTYPE html><html><head><meta charset=\\"UTF-8\\"><meta name=\\"viewport\\" content=\\"width=device-width,initial-scale=1\\"><title>Trade Strategy Analysis Report</title><style>"+s+"</style></head><body style=\\"max-width:900px;margin:0 auto;padding:20px;font-family:sans-serif\\">"+r.innerHTML+"</body></html>";
    }}""")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        f.write(r)
    br.close()
print(f"DONE: {{OUT}}")
'''

success = []
failed = []
skipped = []

for sig in SIGNALS:
    csv_path = f"{BASE}/samples/forex-forest-signals-page-{sig}.csv"
    out_path = f"{BASE}/output/index_{sig}.html"
    
    if not os.path.exists(csv_path):
        print(f"❌ {sig}: No CSV")
        failed.append(sig)
        continue
    
    if os.path.exists(out_path):
        print(f"⏭️  {sig}: Already exists")
        skipped.append(sig)
        continue
    
    script = SCRIPT_TEMPLATE.format(sig=sig, base=BASE)
    
    print(f"🔄 Processing {sig}...", flush=True)
    try:
        result = subprocess.run(
            ["python3", "-c", script],
            capture_output=True, text=True, timeout=600,
            cwd=BASE
        )
        output = result.stdout.strip() + result.stderr.strip()
        print(f"   → {output[-200:]}", flush=True)
        
        if os.path.exists(out_path):
            success.append(sig)
        else:
            failed.append(sig)
            print(f"❌ {sig}: Report not generated", flush=True)
    except subprocess.TimeoutExpired:
        failed.append(sig)
        print(f"❌ {sig}: Timeout", flush=True)
    except Exception as e:
        failed.append(sig)
        print(f"❌ {sig}: {e}", flush=True)
    
    time.sleep(2)

print(f"\n=== SUMMARY ===")
print(f"✅ Success: {len(success)} — {success}")
print(f"⏭️  Skipped: {len(skipped)} — {skipped}")
print(f"❌ Failed: {len(failed)} — {failed}")
