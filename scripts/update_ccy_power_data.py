#!/usr/bin/env python3
"""Fetch CCY Power from API (or CSV fallback), update data.json, timeline.json, AND inject inline data into index.html"""
import json, sys, urllib.request, re, csv, os
from datetime import datetime

DST_JSON = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/ccy_power/data.json"
DST_TL_JSON = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/ccy_power/timeline.json"
DST_HTML = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/ccy_power/index.html"
CSV_PATH = "/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/MQL4/Files/forex_data.csv"

def _inject(html, marker, inline_js):
    """Replace or insert a window.__X__ = ... block in HTML."""
    if f"{marker} = " in html:
        html = re.sub(rf"{re.escape(marker)}\s*=\s*\{{.*?\}};", inline_js, html, flags=re.DOTALL)
    else:
        html = html.replace("</head>", f"<script>{inline_js}</script>\n</head>")
    return html

def _ensure_h4_h1(data):
    """If H4/H1 missing or empty, fill from D1. Returns modified data."""
    d1 = data.get("D1", {})
    if not d1:
        return data
    for tf in ["H4", "H1"]:
        if tf not in data or not data[tf]:
            data[tf] = dict(d1)
    return data

def read_ccy_from_csv():
    """Read latest CCY Power from forex_data.csv (fallback when API is down)."""
    if not os.path.exists(CSV_PATH):
        print(f"⚠️ CSV not found: {CSV_PATH}", file=sys.stderr)
        return None
    try:
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # CCY Power is in every row — take the first one we find
                ccy = {}
                for i in range(1, 10):
                    name = row.get(f"ccy_{i}_name", "").strip()
                    power = row.get(f"ccy_{i}_power", "").strip()
                    if name and power:
                        try:
                            ccy[name] = float(power)
                        except ValueError:
                            pass
                if ccy:
                    ts = row.get("timestamp", datetime.now().strftime("%Y.%m.%d %H:%M")).strip()
                    return {"success": True, "timestamp": ts, "data": {"D1": ccy}}
    except Exception as e:
        print(f"⚠️ CSV read failed: {e}", file=sys.stderr)
    return None

try:
    # --- Current CCY Power ---
    # Try API first, fallback to CSV
    api_data = None
    source = "API"
    try:
        req = urllib.request.Request("http://localhost:8788/api/ccy_power/current")
        with urllib.request.urlopen(req, timeout=5) as resp:
            api_data = json.loads(resp.read())
    except Exception:
        print("⚠️ API unavailable, falling back to CSV...", file=sys.stderr)
        api_data = read_ccy_from_csv()
        source = "CSV"
        if api_data is None:
            print("❌ No data from API or CSV", file=sys.stderr)
            sys.exit(1)

    if not api_data.get("success") or not api_data.get("data"):
        print("ERROR: No valid data", file=sys.stderr)
        sys.exit(1)

    # Remove AVG from all TFs
    for tf in ["D1", "H4", "H1"]:
        if tf in api_data["data"]:
            api_data["data"][tf].pop("AVG", None)

    # Fill missing H4/H1 from D1
    api_data["data"] = _ensure_h4_h1(api_data["data"])

    with open(DST_JSON, "w") as f:
        json.dump(api_data, f, indent=2)
    print(f"✅ data.json ({source}): {api_data['timestamp']}")

    # --- Timeline (24h) ---
    tl_data = {}
    try:
        req2 = urllib.request.Request("http://localhost:8788/api/ccy_power/timeline?hours=24")
        with urllib.request.urlopen(req2, timeout=5) as resp2:
            tl_data = json.loads(resp2.read())
        for tf in ["D1", "H4", "H1"]:
            for entry in tl_data.get("timeline", {}).get(tf, []):
                entry["currencies"].pop("AVG", None)
        with open(DST_TL_JSON, "w") as f:
            json.dump(tl_data, f, indent=2)
        d1_count = len(tl_data.get("timeline", {}).get("D1", []))
        print(f"✅ timeline.json: {d1_count} D1 entries")
    except Exception as e:
        print(f"⚠️ Timeline fetch failed: {e}", file=sys.stderr)

    # --- Inject into HTML ---
    with open(DST_HTML, "r") as f:
        html = f.read()

    html = _inject(html, "window.__CCY_POWER_DATA__", f"window.__CCY_POWER_DATA__ = {json.dumps(api_data)};")

    if tl_data.get("success"):
        html = _inject(html, "window.__CCY_TIMELINE_DATA__", f"window.__CCY_TIMELINE_DATA__ = {json.dumps(tl_data)};")

    with open(DST_HTML, "w") as f:
        f.write(html)
    print("✅ index.html inline data updated")

except Exception as e:
    print(f"❌ Failed: {e}", file=sys.stderr)
    sys.exit(1)
