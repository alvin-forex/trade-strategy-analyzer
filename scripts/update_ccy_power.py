#!/usr/bin/env python3
"""
Read MT4 forex_data.csv and update TSA CCY Power data.json + timeline.json
"""
import csv
import json
import os
import sys
from datetime import datetime
from collections import defaultdict

CSV_PATH = "/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/MQL4/Files/forex_data.csv"
DATA_JSON = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/ccy_power/data.json"
TIMELINE_JSON = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/ccy_power/timeline.json"
DB_PATH = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/data/ccy_power_history.db"

def read_csv():
    """Read latest forex_data.csv and extract CCY Power + OHLC data"""
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: CSV not found: {CSV_PATH}")
        return None
    
    data = {}  # tf -> {ccy_name: value}
    all_rows = []
    
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_rows.append(row)
            tf = row.get('timeframe', '')
            if tf not in data:
                # Extract CCY Power from first row of each TF
                ccy = {}
                for i in range(1, 10):
                    name = row.get(f'ccy_{i}_name', '').strip()
                    val = row.get(f'ccy_{i}_power', '0').strip()
                    if name:
                        ccy[name] = float(val)
                if ccy:
                    data[tf] = ccy
    
    return data, all_rows

def update_data_json(ccy_data):
    """Update data.json with latest CCY Power values"""
    out = {
        "success": True,
        "timestamp": datetime.now().strftime("%Y.%m.%d %H:%M"),
        "data": ccy_data
    }
    
    with open(DATA_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    
    print(f"[OK] data.json updated: {len(ccy_data)} TFs")
    for tf, vals in ccy_data.items():
        top = sorted(vals.items(), key=lambda x: -x[1])[:3]
        print(f"  {tf}: {', '.join(f'{k}={v:.1f}' for k,v in top)}")

def save_to_db(ccy_data):
    """Save CCY Power data to SQLite for timeline history"""
    import sqlite3
    
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create table if not exists
    c.execute('''CREATE TABLE IF NOT EXISTS ccy_power_v3
                 (timestamp TEXT, timeframe TEXT,
                  AUD REAL, CAD REAL, CHF REAL, EUR REAL, GBP REAL,
                  JPY REAL, NZD REAL, USD REAL, XAU REAL,
                  UNIQUE(timestamp, timeframe))''')
    
    now = datetime.now().strftime("%Y.%m.%d %H:%M")
    count = 0
    
    for tf, vals in ccy_data.items():
        try:
            c.execute('''INSERT OR REPLACE INTO ccy_power_v3 
                        (timestamp, timeframe, AUD, CAD, CHF, EUR, GBP, JPY, NZD, USD, XAU)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                     (now, tf,
                      vals.get('AUD', 0), vals.get('CAD', 0), vals.get('CHF', 0),
                      vals.get('EUR', 0), vals.get('GBP', 0), vals.get('JPY', 0),
                      vals.get('NZD', 0), vals.get('USD', 0), vals.get('XAU', 0)))
            count += 1
        except Exception as e:
            print(f"[WARN] DB insert failed for {tf}: {e}")
    
    conn.commit()
    
    # Keep only last 7 days (168 hourly entries)
    c.execute("DELETE FROM ccy_power_v3 WHERE timestamp < ?", 
              (datetime.now().replace(hour=0, minute=0).strftime("%Y.%m.%d ") + "00:00",))
    conn.commit()
    
    # Keep only last 30 days for daily
    # Actually let's just keep 7 days of data
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=7)).strftime("%Y.%m.%d %H:%M")
    c.execute("DELETE FROM ccy_power_v3 WHERE timestamp < ?", (cutoff,))
    conn.commit()
    
    conn.close()
    print(f"[OK] DB updated: {count} TF entries")

def update_timeline_json():
    """Generate timeline.json from DB"""
    import sqlite3
    
    if not os.path.exists(DB_PATH):
        print("[WARN] No DB for timeline")
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    timeline = {}
    for tf in ['D1', 'H4', 'H1']:
        c.execute('''SELECT timestamp, AUD, CAD, CHF, EUR, GBP, JPY, NZD, USD, XAU 
                     FROM ccy_power_v3 
                     WHERE timeframe = ? 
                     ORDER BY timestamp DESC LIMIT 168''', (tf,))
        rows = c.fetchall()
        entries = []
        for row in reversed(rows):
            entries.append({
                "timestamp": row[0],
                "currencies": {
                    "AUD": row[1], "CAD": row[2], "CHF": row[3],
                    "EUR": row[4], "GBP": row[5], "JPY": row[6],
                    "NZD": row[7], "USD": row[8], "XAU": row[9]
                }
            })
        timeline[tf] = entries
    
    conn.close()
    
    out = {
        "success": True,
        "hours": 168,
        "timeline": timeline
    }
    
    with open(TIMELINE_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    
    total = sum(len(v) for v in timeline.values())
    print(f"[OK] timeline.json updated: {total} entries across {len(timeline)} TFs")

if __name__ == "__main__":
    result = read_csv()
    if result is None:
        sys.exit(1)
    
    ccy_data, all_rows = result
    
    if not ccy_data:
        print("ERROR: No CCY Power data in CSV")
        sys.exit(1)
    
    update_data_json(ccy_data)
    save_to_db(ccy_data)
    update_timeline_json()
    print("[DONE] CCY Power update complete")
