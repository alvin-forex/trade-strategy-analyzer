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
READER_CSV_PATH = "/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/MQL4/Files/ccy_power_reader.csv"
DATA_JSON = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/ccy_power/data.json"
TIMELINE_JSON = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/ccy_power/timeline.json"
PAIRS_JSON = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/ccy_power/pairs.json"
DB_PATH = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/data/ccy_power_history.db"

def is_market_closed():
    """檢查是否為週末休市時間（以 HKT 為準）
    週六05:00 HKT（紐約週五收市）→ 週一08:00 HKT（悉尼週一開市）
    """
    now = datetime.now()
    weekday = now.weekday()  # 0=Mon, 5=Sat, 6=Sun
    hour = now.hour

    if weekday == 5 and hour >= 5:  # 週六 05:00 後
        return True, f"週末休市（週六 {hour:02d}:00 HKT）"
    if weekday == 6:  # 週日全天
        return True, "週末休市（週日）"
    if weekday == 0 and hour < 8:  # 週一 08:00 前
        return True, f"週末休市（週一 {hour:02d}:00 HKT，未開市）"
    return False, None

def read_csv():
    """Read latest CCY Power data.
    Priority: ccy_power_reader.csv → ccy_power_v2 DB → forex_data.csv
    ccy_power_reader.csv = CCYPowerReader EA (reads chart objects from 3 TF charts)
    This gives REAL per-TF distinct values from CCY Power Indicator.
    """
    import sqlite3 as sq3
    
    CCY_NAMES = ["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD", "XAU"]
    
    # Priority 1: ccy_power_reader.csv (CCYPowerReader EA - reads chart objects)
    if os.path.exists(READER_CSV_PATH):
        try:
            data = {}
            with open(READER_CSV_PATH, 'r') as f:
                reader = csv.DictReader(f)
                # Collect all rows, get latest per TF
                tf_rows = {'D1': [], 'H4': [], 'H1': []}
                for row in reader:
                    tf = row.get('timeframe', '')
                    if tf in tf_rows:
                        tf_rows[tf].append(row)
                # Get latest row for each TF
                for tf, rows in tf_rows.items():
                    if rows:
                        latest = rows[-1]  # Last row is latest
                        ccy = {}
                        for i in range(1, 10):
                            name = latest.get(f'ccy{i}_name', '').strip()
                            val = latest.get(f'ccy{i}_power', '0').strip()
                            if name:
                                ccy[name] = float(val)
                        if ccy:
                            data[tf] = ccy
            if len(data) >= 2:  # At least 2 TFs with data
                print(f"[OK] Using ccy_power_reader.csv: {len(data)} TFs with distinct values")
                ts = tf_rows['D1'][-1]['timestamp'] if tf_rows['D1'] else datetime.now().strftime("%Y.%m.%d %H:%M")
                print(f"     Latest: {ts} | D1: {list(data.get('D1', {}).keys())[:3]} H4: {list(data.get('H4', {}).keys())[:3]} H1: {list(data.get('H1', {}).keys())[:3]}")
                return data, []
        except Exception as e:
            print(f"[WARN] ccy_power_reader.csv read failed: {e}")
    
    # Priority 2: ccy_power_v2 DB
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
    Always write - this is our primary timeline data source.
    """
    import sqlite3
    
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
    """Generate timeline.json from ccy_power_v3 (primary) and v2 (supplement).
    v3 = continuously updated by update_ccy_power.py (has 24h data).
    v2 = Pipeline 2 from CCY Power Indicator (may be stale but has per-TF distinct values).
    """
    import sqlite3
    
    if not os.path.exists(DB_PATH):
        print("[WARN] No DB for timeline")
        return
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    timeline = {}
    for tf in ['D1', 'H4', 'H1']:
        entries = []
        seen_ts = set()
        
        # Primary: v3 (continuously updated)
        try:
            c.execute('''SELECT timestamp, AUD, CAD, CHF, EUR, GBP, JPY, NZD, USD, XAU 
                         FROM ccy_power_v3 
                         WHERE timeframe = ? 
                         ORDER BY timestamp DESC LIMIT 720''', (tf,))
            rows = c.fetchall()
            for row in reversed(rows):
                if row[0] not in seen_ts:
                    seen_ts.add(row[0])
                    entries.append({
                        "timestamp": row[0],
                        "currencies": {
                            "AUD": row[1], "CAD": row[2], "CHF": row[3],
                            "EUR": row[4], "GBP": row[5], "JPY": row[6],
                            "NZD": row[7], "USD": row[8], "XAU": row[9]
                        }
                    })
        except Exception as e:
            print(f"[WARN] v3 read failed for {tf}: {e}")
        
        # Supplement: v2 (has per-TF distinct values, fill gaps)
        try:
            c.execute('''SELECT timestamp, AUD, CAD, CHF, EUR, GBP, JPY, NZD, USD, XAU 
                         FROM ccy_power_v2 
                         WHERE timeframe = ? 
                         AND timestamp NOT IN ({})
                         ORDER BY timestamp DESC LIMIT 720'''.format(','.join(['?']*len(seen_ts))),
                      (tf,) + tuple(seen_ts))
            rows = c.fetchall()
            for row in reversed(rows):
                entries.append({
                    "timestamp": row[0],
                    "currencies": {
                        "AUD": row[1], "CAD": row[2], "CHF": row[3],
                        "EUR": row[4], "GBP": row[5], "JPY": row[6],
                        "NZD": row[7], "USD": row[8], "XAU": row[9]
                    }
                })
            entries.sort(key=lambda x: x['timestamp'])
        except Exception:
            pass
        
        if entries:
            timeline[tf] = entries
    
    conn.close()
    
    out = {
        "success": True,
        "hours": 720,
        "timeline": timeline
    }
    
    with open(TIMELINE_JSON, 'w') as f:
        json.dump(out, f, indent=2)
    
    total = sum(len(v) for v in timeline.values())
    print(f"[OK] timeline.json: {total} entries across {len(timeline)} TFs")

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
    # 休市時間檢查
    closed, reason = is_market_closed()
    if closed:
        print(f"[SKIP] {reason}")
        sys.exit(0)  # 正常退出，不報錯
    
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
    
    # Inject inline data into HTML
    HTML_PATH = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/ccy_power/index.html"
    import re
    if os.path.exists(HTML_PATH):
        with open(HTML_PATH, 'r') as f: html = f.read()
        with open(DATA_JSON, 'r') as f: data_json = json.load(f)
        with open(TIMELINE_JSON, 'r') as f: timeline_json = json.load(f)
        # Fill H4/H1 from D1 if missing
        d1 = data_json.get('data', {}).get('D1', {})
        if d1:
            for tf in ['H4', 'H1']:
                if tf not in data_json.get('data', {}) or not data_json['data'][tf]:
                    data_json.setdefault('data', {})[tf] = dict(d1)
        # Remove existing inline script blocks
        html = re.sub(r'<script>window\.__CCY_POWER_DATA__\s*=\s*\{.*?\};</script>\n?', '', html, flags=re.DOTALL)
        html = re.sub(r'<script>window\.__CCY_TIMELINE_DATA__\s*=\s*\{.*?\};</script>\n?', '', html, flags=re.DOTALL)
        # Insert both before </head>
        inject = '<script>window.__CCY_POWER_DATA__ = ' + json.dumps(data_json) + ';</script>\n'
        inject += '<script>window.__CCY_TIMELINE_DATA__ = ' + json.dumps(timeline_json) + ';</script>\n'
        html = html.replace('</head>', inject + '</head>')
        with open(HTML_PATH, 'w') as f: f.write(html)
        print("[OK] HTML inline data injected (power + timeline)")
    
    print("[DONE] CCY Power update complete")
