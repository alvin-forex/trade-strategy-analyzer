#!/usr/bin/env python3
"""
CCY Power History API
读取 MT4 CCY Power 历史数据并提供 API 接口
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

# 配置
MT4_TERMINAL_PATH = "/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/MQL4/Files/"
HISTORY_CSV = os.path.join(MT4_TERMINAL_PATH, "ccy_power_history.csv")
DB_PATH = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/data/ccy_power_history.db"

# CCY 货币名称映射（根据 buffer index）
BUFFER_TO_CCY = {
    0: "NZD",
    2: "AUD",
    3: "CAD",
    4: "CHF"
}

def init_db():
    """初始化 SQLite 数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS ccy_power_history
                 (timestamp TEXT, timeframe TEXT, ccy_0 REAL, ccy_2 REAL, ccy_3 REAL, ccy_4 REAL)''')
    conn.commit()
    conn.close()

def csv_to_db():
    """从 CSV 导入数据到 SQLite"""
    if not os.path.exists(HISTORY_CSV):
        return 0
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    count = 0
    with open(HISTORY_CSV, 'r') as f:
        reader = csv.reader(f)
        header = next(reader, None)  # 跳过 header
        
        for row in reader:
            if len(row) >= 6:
                try:
                    c.execute('''INSERT OR IGNORE INTO ccy_power_history 
                                 VALUES (?, ?, ?, ?, ?, ?)''', row[:6])
                    count += 1
                except Exception as e:
                    print(f"Error inserting row: {e}")
    
    conn.commit()
    conn.close()
    return count

def get_history_from_db(hours=24, timeframe=None):
    """从 SQLite 读取历史数据"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 计算时间范围
    now = datetime.now()
    start_time = now - timedelta(hours=hours)
    start_str = start_time.strftime("%Y.%m.%d %H:%M")
    
    query = '''SELECT * FROM ccy_power_history 
               WHERE timestamp >= ?'''
    params = [start_str]
    
    if timeframe:
        query += ' AND timeframe = ?'
        params.append(timeframe)
    
    query += ' ORDER BY timestamp'
    
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()
    
    return rows

def format_history_data(rows):
    """格式化历史数据为 JSON"""
    data = []
    
    for row in rows:
        timestamp, tf, ccy_0, ccy_2, ccy_3, ccy_4 = row
        
        # 转换为货币名称
        currencies = {}
        for buf, name in BUFFER_TO_CCY.items():
            val = row[2 + buf // 2] if buf == 0 else row[2 + buf // 2 + 1]
            currencies[name] = float(val) if val else 0.0
        
        # 简化：直接使用 buffer 值
        currencies = {
            "NZD": float(ccy_0) if ccy_0 else 0.0,
            "AUD": float(ccy_2) if ccy_2 else 0.0,
            "CAD": float(ccy_3) if ccy_3 else 0.0,
            "CHF": float(ccy_4) if ccy_4 else 0.0
        }
        
        data.append({
            "timestamp": timestamp,
            "timeframe": tf,
            "currencies": currencies
        })
    
    return data

@app.route('/api/ccy_power/history')
def api_history():
    """API: 获取历史数据"""
    hours = request.args.get('hours', 24, type=int)
    timeframe = request.args.get('tf', None)
    
    # 先尝试从 CSV 导入新数据
    csv_to_db()
    
    # 从 DB 读取
    rows = get_history_from_db(hours=hours, timeframe=timeframe)
    data = format_history_data(rows)
    
    return jsonify({
        "success": True,
        "count": len(data),
        "hours": hours,
        "data": data
    })

@app.route('/api/ccy_power/timeline')
def api_timeline():
    """API: 获取时间轴数据（用于热力图）"""
    hours = request.args.get('hours', 168, type=int)  # 默认一周
    
    # 先尝试从 CSV 导入新数据
    csv_to_db()
    
    # 从 DB 读取
    rows = get_history_from_db(hours=hours)
    
    # 按 TF 分组
    timeline = {"D1": [], "H4": [], "H1": []}
    
    for row in rows:
        timestamp, tf, ccy_0, ccy_2, ccy_3, ccy_4 = row
        
        currencies = {
            "NZD": float(ccy_0) if ccy_0 else 0.0,
            "AUD": float(ccy_2) if ccy_2 else 0.0,
            "CAD": float(ccy_3) if ccy_3 else 0.0,
            "CHF": float(ccy_4) if ccy_4 else 0.0
        }
        
        if tf in timeline:
            timeline[tf].append({
                "timestamp": timestamp,
                "currencies": currencies
            })
    
    return jsonify({
        "success": True,
        "hours": hours,
        "timeline": timeline
    })

@app.route('/api/ccy_power/current')
def api_current():
    """API: 获取当前数据（实时）"""
    # 这里应该从 ZeroMQ 或最新 CSV 读取
    # 暂时返回 demo 数据
    return jsonify({
        "success": True,
        "timestamp": datetime.now().strftime("%Y.%m.%d %H:%M"),
        "D1": {"NZD": 2.25, "AUD": 6.25, "CAD": 8.50, "CHF": 4.35},
        "H4": {"NZD": 2.25, "AUD": 6.25, "CAD": 8.50, "CHF": 4.35},
        "H1": {"NZD": 2.25, "AUD": 6.25, "CAD": 8.50, "CHF": 4.35}
    })

@app.route('/api/ccy_power/import')
def api_import():
    """API: 手动触发 CSV 导入"""
    count = csv_to_db()
    return jsonify({
        "success": True,
        "imported": count,
        "message": f"Imported {count} records from CSV"
    })

if __name__ == '__main__':
    init_db()
    print(f"=== CCY Power History API ===")
    print(f"CSV: {HISTORY_CSV}")
    print(f"DB: {DB_PATH}")
    app.run(host='0.0.0.0', port=8788, debug=True)