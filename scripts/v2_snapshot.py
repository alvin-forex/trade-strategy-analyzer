#!/usr/bin/env python3
"""
V2 Technical Analysis Snapshot Manager

Provides functions to save/list/get V2 technical analysis snapshots
into the forex_v2_snapshots table in analysis_history.db.
"""

import sqlite3
import json
import os

DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'data', 'analysis_history.db'
)


def get_db():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _ensure_table(conn):
    """Ensure forex_v2_snapshots table exists."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS forex_v2_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_time TEXT NOT NULL,
            snapshot_type TEXT NOT NULL,
            report_path TEXT,
            csv_data TEXT NOT NULL,
            ccy_power_json TEXT,
            pair_scores_json TEXT,
            market_glance_json TEXT,
            events_json TEXT,
            news_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()


def save_snapshot(snapshot_time, snapshot_type, csv_data,
                  ccy_power=None, pair_scores=None,
                  report_path=None, market_glance=None,
                  events=None, news=None):
    """
    Save a V2 technical analysis snapshot.

    Args:
        snapshot_time: ISO timestamp, e.g. "2026-05-28T18:00:00+08:00"
        snapshot_type: "morning" or "evening"
        csv_data: Full CSV content as text
        ccy_power: dict like {"AUD":3.8, "CAD":2.3, ...}
        pair_scores: dict like {"AUDUSD":-13, "EURCHF":16, ...}
        report_path: path to HTML report (optional)
        market_glance: market snapshot data dict (optional)
        events: economic calendar events list/dict (optional)
        news: news items list/dict (optional)

    Returns:
        int: The id of the newly inserted snapshot
    """
    conn = get_db()
    try:
        _ensure_table(conn)
        conn.execute('''
            INSERT INTO forex_v2_snapshots
                (snapshot_time, snapshot_type, report_path, csv_data,
                 ccy_power_json, pair_scores_json, market_glance_json,
                 events_json, news_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            snapshot_time,
            snapshot_type,
            report_path,
            csv_data,
            json.dumps(ccy_power) if ccy_power else None,
            json.dumps(pair_scores) if pair_scores else None,
            json.dumps(market_glance) if market_glance else None,
            json.dumps(events) if events else None,
            json.dumps(news) if news else None,
        ))
        conn.commit()
        row_id = conn.execute('SELECT last_insert_rowid()').fetchone()[0]
        return row_id
    finally:
        conn.close()


def list_snapshots(limit=10):
    """
    List recent V2 snapshots (without full csv_data to save memory).

    Returns:
        list of dict with: id, snapshot_time, snapshot_type, report_path,
                           ccy_power_json, pair_scores_json, created_at, pair_count
    """
    conn = get_db()
    try:
        _ensure_table(conn)
        rows = conn.execute('''
            SELECT id, snapshot_time, snapshot_type, report_path,
                   ccy_power_json, pair_scores_json, created_at
            FROM forex_v2_snapshots
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,)).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            # Count pairs
            try:
                ps = json.loads(d.get('pair_scores_json') or '{}')
                d['pair_count'] = len(ps)
            except Exception:
                d['pair_count'] = 0
            result.append(d)
        return result
    finally:
        conn.close()


def get_snapshot(snapshot_id):
    """
    Get a specific V2 snapshot by id, including full data.

    Returns:
        dict or None
    """
    conn = get_db()
    try:
        _ensure_table(conn)
        row = conn.execute(
            'SELECT * FROM forex_v2_snapshots WHERE id = ?',
            (snapshot_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_latest():
    """
    Get the latest V2 snapshot with full data.

    Returns:
        dict or None
    """
    conn = get_db()
    try:
        _ensure_table(conn)
        row = conn.execute(
            'SELECT * FROM forex_v2_snapshots ORDER BY id DESC LIMIT 1'
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("Usage: v2_snapshot.py [list|latest|get <id>]")
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd == 'list':
        snapshots = list_snapshots(10)
        for s in snapshots:
            print(f"  #{s['id']}  {s['snapshot_time']}  {s['snapshot_type']}  pairs={s.get('pair_count', '?')}")
    elif cmd == 'latest':
        s = get_latest()
        if s:
            print(json.dumps(s, indent=2, ensure_ascii=False))
        else:
            print("No snapshots found")
    elif cmd == 'get' and len(sys.argv) > 2:
        s = get_snapshot(int(sys.argv[2]))
        if s:
            print(json.dumps(s, indent=2, ensure_ascii=False))
        else:
            print(f"Snapshot #{sys.argv[2]} not found")
    else:
        print(f"Unknown command: {cmd}")
