#!/usr/bin/env python3
"""
Trade Strategy Analyzer — Local API Server

Provides:
1. POST /api/save — Save analysis from frontend
2. GET  /api/list — List analyses (optional ?signal=&limit=)
3. GET  /api/summary/{id} — Get analysis detail
4. GET  /api/compare/{signal_id}/{v1}/{v2} — Compare versions
5. GET  /api/trend/{signal_id} — Get trend data

Runs on localhost:8787 alongside OpenClaw.
"""

import sys
import os
import threading

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from history_manager import (
    save_analysis, list_analyses, get_summary,
    compare_versions, get_trend, get_db
)
from v2_snapshot import (
    save_snapshot as v2_save_snapshot,
    list_snapshots as v2_list_snapshots,
    get_snapshot as v2_get_snapshot,
    get_latest as v2_get_latest,
)
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json
import urllib.request
import urllib.parse

# Telegram notification — write to notification log
# OpenClaw agent picks up via heartbeat/polling
def notify_telegram(message: str):
    """Write notification to shared file for OpenClaw to pick up."""
    try:
        with open('/tmp/trade-analyzer-notify.json', 'a') as f:
            import time
            f.write(json.dumps({"ts": time.time(), "msg": message}) + '\n')
    except Exception:
        pass

app = FastAPI(title="Trade Strategy Analyzer API")

# CORS — allow GitHub Pages and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tunnel URL changes each session; restrict later with named tunnel
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/save")
async def api_save(data: dict):
    """Save analysis data from frontend."""
    try:
        aid = save_analysis(data)
        # Notify via Telegram (fire-and-forget in background thread)
        sig = data.get('signal_id', '?')
        ea = data.get('ea_name', '?')
        wr = data.get('win_rate', 0)
        pf = data.get('profit_factor', 0)
        profit = data.get('total_profit', 0)
        positions = data.get('total_positions', 0)
        emoji = '🟢' if profit >= 0 else '🔴'
        msg = f"✅ 新分析已存檔\n{emoji} Signal {sig} | {ea} | {positions} 倉位\nWR {wr:.1f}% | PF {pf:.2f} | {emoji} ${profit:+.2f}"
        threading.Thread(target=notify_telegram, args=(msg,), daemon=True).start()
        return {"ok": True, "id": aid}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/list")
async def api_list(limit: int = Query(20, ge=1, le=100), signal: str = Query(None)):
    """List recent analyses."""
    text = list_analyses(limit, signal)
    # Also return raw data for frontend rendering
    conn = get_db()
    c = conn.cursor()
    if signal:
        c.execute('''SELECT a.*, v.version
                     FROM analyses a LEFT JOIN versions v ON v.analysis_id = a.id
                     WHERE a.signal_id = ? ORDER BY a.created_at DESC LIMIT ?''', (signal, limit))
    else:
        c.execute('''SELECT a.*, v.version
                     FROM analyses a LEFT JOIN versions v ON v.analysis_id = a.id
                     ORDER BY a.created_at DESC LIMIT ?''', (limit,))
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return {"text": text, "data": rows}


@app.get("/api/summary/{analysis_id}")
async def api_summary(analysis_id: int):
    """Get detailed summary."""
    return {"text": get_summary(analysis_id)}


@app.get("/api/compare/{signal_id}/{v1}/{v2}")
async def api_compare(signal_id: str, v1: int, v2: int):
    """Compare two versions."""
    return {"text": compare_versions(signal_id, v1, v2)}


@app.get("/api/trend/{signal_id}")
async def api_trend(signal_id: str):
    """Get trend for a signal."""
    return {"text": get_trend(signal_id)}


@app.get("/api/health")
async def api_health():
    """Health check."""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT COUNT(*) as cnt FROM analyses')
    count = c.fetchone()['cnt']
    conn.close()
    return {"ok": True, "analyses": count}


# ==============================
# V2 Snapshot Endpoints
# ==============================

@app.post("/api/v2/snapshot")
async def api_v2_save_snapshot(data: dict):
    """Save V2 technical analysis snapshot."""
    try:
        snapshot_time = data.get('snapshot_time')
        snapshot_type = data.get('snapshot_type')
        csv_data = data.get('csv_data', '')
        if not snapshot_time or not snapshot_type:
            return JSONResponse({"ok": False, "error": "snapshot_time and snapshot_type required"}, status_code=400)

        aid = v2_save_snapshot(
            snapshot_time=snapshot_time,
            snapshot_type=snapshot_type,
            csv_data=csv_data,
            ccy_power=data.get('ccy_power'),
            pair_scores=data.get('pair_scores'),
            report_path=data.get('report_path'),
            market_glance=data.get('market_glance'),
            events=data.get('events'),
            news=data.get('news'),
        )
        return {"ok": True, "id": aid}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/v2/snapshots")
async def api_v2_list_snapshots(limit: int = Query(10, ge=1, le=100)):
    """List recent V2 snapshots."""
    try:
        snapshots = v2_list_snapshots(limit)
        return {"ok": True, "snapshots": snapshots}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@app.get("/api/v2/snapshot/{snapshot_id}")
async def api_v2_get_snapshot(snapshot_id: int):
    """Get specific V2 snapshot."""
    s = v2_get_snapshot(snapshot_id)
    if not s:
        return JSONResponse({"ok": False, "error": "Not found"}, status_code=404)
    return {"ok": True, **s}


@app.get("/api/v2/latest")
async def api_v2_get_latest():
    """Get latest V2 snapshot with full data."""
    s = v2_get_latest()
    if not s:
        return JSONResponse({"ok": False, "error": "No snapshots available"}, status_code=404)
    return {"ok": True, **s}


if __name__ == '__main__':
    import uvicorn
    print("🚀 Trade Strategy Analyzer API starting on http://localhost:8787")
    uvicorn.run(app, host="0.0.0.0", port=8787)
