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
PAIRS_JSON = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/ccy_power/pairs.json"
DB_PATH = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/data/ccy_power_history.db"

def read_csv():
    """Read latest CCY Power data from ccy_power_v2 DB (Pipeline 2).
    Falls back to forex_data.csv if DB is empty.
    Pipeline 2 = CCY Power Indicator → ccy_power_history.csv → ccy_power_v2 DB
    This gives per-TF distinct values, unlike EA's forex_data.csv (same values all TFs).
    """
    import sqlite3 as sq3
    
    CCY_NAMES = ["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD", "XAU"]
    
    # Try ccy_power_v2 first (has real per-TF distinct values)
    if os.path.exists(DB_PATH):
        try:
            conn = sq3.connect(DB_PATH)
            c = conn.cursor()
            data = {}
            for tf in ['D1', 'H4', 'H1']:
                c.execute('''SELECT timestamp, AUD, CAD, CHF, EUR, GBP, JPY, NZD, USD, XAU
                             FROM ccy_power_v2 WHERE timeframe=? ORDER BY timestamp DESC LIMIT 1''', (tf,))
                row = c.fetchone()
                if row:
                    vals = {}
                    for i, name in enumerate(CCY_NAMES):
                        vals[name] = round(float(row[1+i]), 4) if row[1+i] else 0
                    data[tf] = vals
            conn.close()
            if len(data) >= 2:  # At least 2 TFs with distinct data
                print(f"[OK] Using ccy_power_v2 DB: {len(data)} TFs with distinct values")
                return data, []
        except Exception as e:
            print(f"[WARN] ccy_power_v2 read failed: {e}")
    
    # Fallback: forex_data.csv (EA output, may have same values across TFs)
    if not os.path.exists(CSV_PATH):
        print(f"ERROR: CSV not found: {CSV_PATH}")
        return None
    
    data = {}
    all_rows = []
    with open(CSV_PATH, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            all_rows.append(row)
            tf = row.get('timeframe', '')
            if tf not in data:
                ccy = {}
                for i in range(1, 10):
                    name = row.get(f'ccy_{i}_name', '').strip()
                    val = row.get(f'ccy_{i}_power', '0').strip()
                    if name:
                        ccy[name] = float(val)
                if ccy:
                    data[tf] = ccy
    print(f"[WARN] Fallback to forex_data.csv (values may be identical across TFs)")
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
    """Save CCY Power data to ccy_power_v3 for timeline history.
    Skip if data came from v2 DB (already has correct per-TF data).
    Only write if at least 2 TFs have different values.
    """
    import sqlite3
    
    # Check if values are identical across TFs (EA bug)
    tf_vals = list(ccy_data.values())
    if len(tf_vals) >= 2:
        first = tf_vals[0]
        all_same = all(v == first for v in tf_vals[1:])
        if all_same:
            print("[SKIP] ccy_power_v3: values identical across TFs (EA bug), skipping")
            return
    
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
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
    
    # Keep only last 30 days
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(days=30)).strftime("%Y.%m.%d %H:%M")
    c.execute("DELETE FROM ccy_power_v3 WHERE timestamp < ?", (cutoff,))
    conn.commit()
    
    conn.close()
    print(f"[OK] ccy_power_v3 updated: {count} TF entries")

def update_timeline_json():
    """Generate timeline.json from both ccy_power_v2 and ccy_power_v3 DBs.
    Prefer ccy_power_v2 (Pipeline 2, real per-TF data) over v3 (may be identical).
    """
    import sqlite3
    
    if not os.path.exists(DB_PATH):
        print("[WARN] No DB for timeline")
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Try v2 first for real per-TF timeline
    v2_count = 0
    timeline = {}
    for tf in ['D1', 'H4', 'H1']:
        try:
            c.execute('''SELECT timestamp, AUD, CAD, CHF, EUR, GBP, JPY, NZD, USD, XAU 
                         FROM ccy_power_v2 
                         WHERE timeframe = ? 
                         ORDER BY timestamp DESC LIMIT 720''', (tf,))
            rows = c.fetchall()
            v2_count += len(rows)
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
        except Exception:
            pass
    
    # Fill missing TFs from v3
    for tf in ['D1', 'H4', 'H1']:
        if tf in timeline and len(timeline[tf]) > 0:
            continue
        try:
            c.execute('''SELECT timestamp, AUD, CAD, CHF, EUR, GBP, JPY, NZD, USD, XAU 
                         FROM ccy_power_v3 
                         WHERE timeframe = ? 
                         ORDER BY timestamp DESC LIMIT 720''', (tf,))
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
            if entries:
                timeline[tf] = entries
        except Exception:
            pass
    
    conn.close()
    
    out = {
        "success": True,
        "hours": 720,
        "timeline": timeline
    }
    
    with open(TIMELINE_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    
    total = sum(len(v) for v in timeline.values())
    print(f"[OK] timeline.json: {total} entries across {len(timeline)} TFs (v2={v2_count} rows)")

def update_pairs_json(all_rows):
    """Generate pairs.json with technical analysis from forex_data.csv"""
    if not all_rows:
        print("[WARN] No rows for pairs.json")
        return
    
    pairs = {}
    for row in all_rows:
        sym = row.get('symbol','').rstrip('.')
        tf = row.get('timeframe','')
        try:
            price = float(row.get('close','0'))
            o = float(row.get('open','0'))
            bb_u = float(row.get('bb_upper','0'))
            bb_m = float(row.get('bb_middle','0'))
            bb_l = float(row.get('bb_lower','0'))
            ema20 = float(row.get('ema20','0'))
            ema50 = float(row.get('ema50','0'))
            ema200 = float(row.get('ema200','0'))
            atr = float(row.get('atr14','0'))
            rsi = float(row.get('rsi14','0'))
            macd_h = float(row.get('macd_hist','0'))
        except:
            continue
        
        if sym not in pairs: pairs[sym] = {}
        
        # Signal calculation
        signals = []
        if rsi > 70: signals.append(-2)
        elif rsi > 60: signals.append(1)
        elif rsi > 40: signals.append(0)
        elif rsi > 30: signals.append(-1)
        else: signals.append(2)
        
        if macd_h > 0: signals.append(1)
        elif macd_h < 0: signals.append(-1)
        else: signals.append(0)
        
        if ema20 > ema50 > ema200: signals.append(2)
        elif ema20 > ema50: signals.append(1)
        elif ema20 < ema50 < ema200: signals.append(-2)
        elif ema20 < ema50: signals.append(-1)
        else: signals.append(0)
        
        if price > bb_u: signals.append(1)
        elif price < bb_l: signals.append(-1)
        else: signals.append(0)
        
        total = sum(signals)
        if total >= 3: bias = "Strong Buy"
        elif total >= 1: bias = "Buy"
        elif total <= -3: bias = "Strong Sell"
        elif total <= -1: bias = "Sell"
        else: bias = "Neutral"
        
        change = round((price - o) / o * 10000, 1) if o > 0 else 0
        
        pairs[sym][tf] = {
            "o": o, "h": float(row.get('high','0')), "l": float(row.get('low','0')), "c": price,
            "bb_u": bb_u, "bb_m": bb_m, "bb_l": bb_l,
            "ema20": ema20, "ema50": ema50, "ema200": ema200,
            "atr": atr, "rsi": rsi,
            "macd_h": macd_h,
            "signal": total, "bias": bias, "change": change
        }
    
    # Sort by D1 signal
    sorted_pairs = dict(sorted(pairs.items(), key=lambda x: -(x[1].get('D1',{}).get('signal',0))))
    
    out = {"success": True, "pairs": sorted_pairs}
    with open(PAIRS_JSON, 'w') as f:
        json.dump(out, f)
    print(f"[OK] pairs.json: {len(sorted_pairs)} pairs")

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
    
    # Generate pairs.json from forex_data.csv (EA data has all 29 pairs)
    csv_path = "/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/MQL4/Files/forex_data.csv"
    if os.path.exists(csv_path):
        pair_rows = []
        with open(csv_path) as f:
            reader = csv.DictReader(f)
            for row in reader: pair_rows.append(row)
        update_pairs_json(pair_rows)
    
    print("[DONE] CCY Power update complete")
