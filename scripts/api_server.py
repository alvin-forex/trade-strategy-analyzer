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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from history_manager import (
    save_analysis, list_analyses, get_summary,
    compare_versions, get_trend, get_db
)
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json

app = FastAPI(title="Trade Strategy Analyzer API")

# CORS — allow GitHub Pages and localhost
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://alvin-forex.github.io",
        "http://localhost:*",
        "http://127.0.0.1:*",
        "null",  # local file://
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/save")
async def api_save(data: dict):
    """Save analysis data from frontend."""
    try:
        aid = save_analysis(data)
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


if __name__ == '__main__':
    import uvicorn
    print("🚀 Trade Strategy Analyzer API starting on http://localhost:8787")
    uvicorn.run(app, host="0.0.0.0", port=8787)
