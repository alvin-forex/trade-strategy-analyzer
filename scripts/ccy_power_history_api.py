#!/usr/bin/env python3
"""
CCY Power History API v2
Reads MT4 CCY Power history CSV (10 buffers × 3 TFs) and serves API
"""

import os
import csv
import json
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)

# Config
MT4_TERMINAL_PATH = "/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/MQL4/Files/"
HISTORY_CSV = os.path.join(MT4_TERMINAL_PATH, "ccy_power_history.csv")
BACKFILL_CSV = os.path.join(MT4_TERMINAL_PATH, "ccy_power_backfill.csv")
DB_PATH = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/data/ccy_power_history.db"

# Buffer-to-currency mapping (10 buffers, confirmed from v4.16/v4.17)
# 0=EUR, 1=GBP, 2=AUD, 3=NZD, 4=CAD, 5=CHF, 6=XAU, 7=JPY, 8=USD, 9=AVG
CCY_COLUMNS = ["EUR", "GBP", "AUD", "NZD", "CAD", "CHF", "XAU", "JPY", "USD", "AVG"]
CCY_COUNT = 10

def init_db():
    """Initialize SQLite with v2 schema (10 CCY columns)"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create v2 table
    columns = ", ".join([f"{ccy} REAL DEFAULT 0" for ccy in CCY_COLUMNS])
    c.execute(f'''CREATE TABLE IF NOT EXISTS ccy_power_v2
                 (timestamp TEXT, timeframe TEXT, {columns},
                  UNIQUE(timestamp, timeframe))''')
    
    # Check if we need to migrate from old schema
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='ccy_power_history'")
    if c.fetchone():
        c.execute("PRAGMA table_info(ccy_power_history)")
        old_cols = [row[1] for row in c.fetchall()]
        if old_cols and len(old_cols) == 6:  # Old 4-buffer format
            print("[Migrate] Old format detected, data will be reimported")
            # Don't migrate old data — just start fresh with v2
            c.execute("DROP TABLE IF EXISTS ccy_power_history")
    
    conn.commit()
    conn.close()

def csv_to_db(csv_path=None):
    """Import CSV data into SQLite"""
    if csv_path is None:
        csv_path = HISTORY_CSV
    
    if not os.path.exists(csv_path):
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    count = 0
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                conn.close()
                return 0
            
            # Detect format by header
            col_count = len(header)
            
            for row in reader:
                if len(row) < 12:  # timestamp + tf + 10 CCY
                    continue
                try:
                    timestamp = row[0]
                    tf = row[1]
                    values = [float(v) if v else 0.0 for v in row[2:12]]
                    
                    placeholders = ", ".join(["?"] * (2 + CCY_COUNT))
                    c.execute(f'''INSERT OR REPLACE INTO ccy_power_v2 
                                 VALUES ({placeholders})''', 
                             [timestamp, tf] + values)
                    count += 1
                except (ValueError, IndexError) as e:
                    pass
        
        conn.commit()
    except Exception as e:
        print(f"Error reading CSV: {e}")
    
    conn.close()
    return count

def get_history_from_db(hours=24, timeframe=None, ccy=None):
    """Read history from SQLite"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    now = datetime.now()
    start_time = now - timedelta(hours=hours)
    start_str = start_time.strftime("%Y.%m.%d %H:%M")
    
    query = f'''SELECT * FROM ccy_power_v2 WHERE timestamp >= ?'''
    params = [start_str]
    
    if timeframe:
        query += ' AND timeframe = ?'
        params.append(timeframe)
    
    query += ' ORDER BY timestamp'
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    return rows

def rows_to_json(rows):
    """Convert DB rows to JSON-friendly format"""
    data = []
    for row in rows:
        entry = {
            "timestamp": row[0],
            "timeframe": row[1],
            "currencies": {}
        }
        for i, ccy in enumerate(CCY_COLUMNS):
            val = row[2 + i] if (2 + i) < len(row) else 0
            entry["currencies"][ccy] = round(float(val), 4) if val else 0.0
        data.append(entry)
    return data

# === API Routes ===

@app.route('/api/ccy_power/history')
def api_history():
    """Get historical CCY Power data"""
    hours = request.args.get('hours', 24, type=int)
    tf = request.args.get('tf', None)
    
    csv_to_db()
    rows = get_history_from_db(hours=hours, timeframe=tf)
    data = rows_to_json(rows)
    
    return jsonify({
        "success": True,
        "count": len(data),
        "hours": hours,
        "data": data
    })

@app.route('/api/ccy_power/timeline')
def api_timeline():
    """Get timeline data grouped by TF (for heatmap/charts)"""
    hours = request.args.get('hours', 168, type=int)
    
    csv_to_db()
    rows = get_history_from_db(hours=hours)
    
    timeline = {"D1": [], "H4": [], "H1": []}
    for row in rows:
        entry = {"timestamp": row[0], "currencies": {}}
        for i, ccy in enumerate(CCY_COLUMNS):
            val = row[2 + i] if (2 + i) < len(row) else 0
            entry["currencies"][ccy] = round(float(val), 4) if val else 0.0
        tf = row[1]
        if tf in timeline:
            timeline[tf].append(entry)
    
    return jsonify({
        "success": True,
        "hours": hours,
        "timeline": timeline
    })

@app.route('/api/ccy_power/current')
def api_current():
    """Get latest CCY Power data (from CSV)"""
    csv_to_db()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    result = {}
    for tf in ["D1", "H4", "H1"]:
        c.execute(f'''SELECT * FROM ccy_power_v2 
                      WHERE timeframe = ? ORDER BY timestamp DESC LIMIT 1''', (tf,))
        row = c.fetchone()
        if row:
            result[tf] = {}
            for i, ccy in enumerate(CCY_COLUMNS):
                val = row[2 + i] if (2 + i) < len(row) else 0
                result[tf][ccy] = round(float(val), 4) if val else 0.0
    
    conn.close()
    
    return jsonify({
        "success": True,
        "timestamp": datetime.now().strftime("%Y.%m.%d %H:%M"),
        "data": result
    })

@app.route('/api/ccy_power/ranking')
def api_ranking():
    """Get currency ranking (strongest to weakest) for each TF"""
    csv_to_db()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    result = {}
    for tf in ["D1", "H4", "H1"]:
        c.execute(f'''SELECT * FROM ccy_power_v2 
                      WHERE timeframe = ? ORDER BY timestamp DESC LIMIT 1''', (tf,))
        row = c.fetchone()
        if row:
            ranking = []
            for i, ccy in enumerate(CCY_COLUMNS[:-1]):  # Exclude AVG
                val = row[2 + i] if (2 + i) < len(row) else 0
                ranking.append({"ccy": ccy, "power": round(float(val), 4) if val else 0.0})
            ranking.sort(key=lambda x: x["power"], reverse=True)
            result[tf] = ranking
    
    conn.close()
    
    return jsonify({
        "success": True,
        "timestamp": datetime.now().strftime("%Y.%m.%d %H:%M"),
        "ranking": result
    })

@app.route('/api/ccy_power/import')
def api_import():
    """Manual trigger CSV import (including backfill)"""
    count1 = csv_to_db(HISTORY_CSV)
    count2 = csv_to_db(BACKFILL_CSV)
    return jsonify({
        "success": True,
        "history_imported": count1,
        "backfill_imported": count2,
        "message": f"Imported {count1} history + {count2} backfill records"
    })

@app.route('/api/ccy_power/health')
def api_health():
    """Health check"""
    csv_exists = os.path.exists(HISTORY_CSV)
    csv_size = os.path.getsize(HISTORY_CSV) if csv_exists else 0
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM ccy_power_v2")
    db_count = c.fetchone()[0]
    c.execute("SELECT MAX(timestamp) FROM ccy_power_v2")
    latest = c.fetchone()[0]
    conn.close()
    
    return jsonify({
        "status": "ok",
        "csv_exists": csv_exists,
        "csv_size": csv_size,
        "db_records": db_count,
        "latest_record": latest,
        "ccy_count": CCY_COUNT,
        "ccy_list": CCY_COLUMNS
    })

if __name__ == '__main__':
    init_db()
    print(f"=== CCY Power History API v2 ===")
    print(f"CSV: {HISTORY_CSV}")
    print(f"DB: {DB_PATH}")
    print(f"CCY: {CCY_COLUMNS}")
    app.run(host='0.0.0.0', port=8788, debug=True)
