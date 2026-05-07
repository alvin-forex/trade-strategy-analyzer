#!/usr/bin/env python3
"""
Version Tracker Module for Symbol-based Signal Ranking
- Adds strategy_version to analysis runs
- Tracks per-symbol, per-signal analysis history
- Supports version comparison queries
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).parent.parent / 'data' / 'analysis_history.db'


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_tables(conn):
    """Ensure the symbol_rankings table exists with strategy_version support."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS symbol_rankings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL,
            symbol TEXT NOT NULL,
            strategy_version TEXT NOT NULL DEFAULT 'v1',
            analysis_date TEXT NOT NULL,
            avg_score REAL DEFAULT 0,
            star4_count INTEGER DEFAULT 0,
            star4_pct REAL DEFAULT 0,
            total_comparisons INTEGER DEFAULT 0,
            trades INTEGER DEFAULT 0,
            win_rate REAL DEFAULT 0,
            profit_factor REAL DEFAULT 0,
            total_profit REAL DEFAULT 0,
            timeframe TEXT DEFAULT '',
            ea_type TEXT DEFAULT '',
            layers TEXT DEFAULT '',
            eq_max_dd REAL DEFAULT 0,
            score_breakdown TEXT DEFAULT '{}',
            batch_run_id TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_sr_symbol ON symbol_rankings(symbol);
        CREATE INDEX IF NOT EXISTS idx_sr_signal ON symbol_rankings(signal_id);
        CREATE INDEX IF NOT EXISTS idx_sr_version ON symbol_rankings(strategy_version);
        CREATE INDEX IF NOT EXISTS idx_sr_sym_sig ON symbol_rankings(symbol, signal_id);
        CREATE INDEX IF NOT EXISTS idx_sr_batch ON symbol_rankings(batch_run_id);
    """)
    conn.commit()


def upsert_ranking(conn, signal_id, symbol, strategy_version, analysis_date,
                   avg_score, star4_count, star4_pct, total_comparisons,
                   trades, win_rate, profit_factor, total_profit,
                   timeframe, ea_type, layers, eq_max_dd,
                   score_breakdown, batch_run_id):
    """Insert a new ranking record."""
    conn.execute("""
        INSERT INTO symbol_rankings 
        (signal_id, symbol, strategy_version, analysis_date,
         avg_score, star4_count, star4_pct, total_comparisons,
         trades, win_rate, profit_factor, total_profit,
         timeframe, ea_type, layers, eq_max_dd,
         score_breakdown, batch_run_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        signal_id, symbol, strategy_version, analysis_date,
        avg_score, star4_count, star4_pct, total_comparisons,
        trades, win_rate, profit_factor, total_profit,
        timeframe, ea_type, layers, eq_max_dd,
        json.dumps(score_breakdown), batch_run_id
    ))
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def get_symbols(conn):
    """Get all unique symbols with their signal counts."""
    rows = conn.execute("""
        SELECT symbol, COUNT(DISTINCT signal_id) as signal_count,
               COUNT(*) as total_records
        FROM symbol_rankings
        GROUP BY symbol
        ORDER BY signal_count DESC, symbol
    """).fetchall()
    return [dict(r) for r in rows]


def get_rankings_for_symbol(conn, symbol, strategy_version=None):
    """Get all signal rankings for a specific symbol, sorted by score desc."""
    if strategy_version:
        rows = conn.execute("""
            SELECT * FROM symbol_rankings 
            WHERE symbol = ? AND strategy_version = ?
            ORDER BY avg_score DESC
        """, (symbol, strategy_version)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM symbol_rankings 
            WHERE symbol = ?
            ORDER BY avg_score DESC
        """, (symbol,)).fetchall()
    return [dict(r) for r in rows]


def get_versions_for_signal_symbol(conn, signal_id, symbol):
    """Get all versions for a specific signal × symbol combination."""
    rows = conn.execute("""
        SELECT * FROM symbol_rankings
        WHERE signal_id = ? AND symbol = ?
        ORDER BY strategy_version, analysis_date
    """, (signal_id, symbol)).fetchall()
    return [dict(r) for r in rows]


def get_version_comparison(conn, symbol=None, signal_id=None):
    """Get data suitable for version comparison view."""
    conditions = []
    params = []
    if symbol:
        conditions.append("symbol = ?")
        params.append(symbol)
    if signal_id:
        conditions.append("signal_id = ?")
        params.append(signal_id)
    
    where = " AND ".join(conditions) if conditions else "1=1"
    
    rows = conn.execute(f"""
        SELECT signal_id, symbol, strategy_version, analysis_date,
               avg_score, star4_pct, trades, win_rate, profit_factor,
               total_profit, eq_max_dd, score_breakdown
        FROM symbol_rankings
        WHERE {where}
        ORDER BY symbol, signal_id, strategy_version
    """, params).fetchall()
    return [dict(r) for r in rows]


def get_latest_batch(conn):
    """Get the most recent batch_run_id."""
    row = conn.execute("""
        SELECT batch_run_id, COUNT(*) as cnt, MAX(created_at) as latest
        FROM symbol_rankings
        WHERE batch_run_id != ''
        GROUP BY batch_run_id
        ORDER BY latest DESC
        LIMIT 1
    """).fetchone()
    return dict(row) if row else None


def get_version_summary(conn):
    """Summary of all versions in the DB."""
    rows = conn.execute("""
        SELECT strategy_version, COUNT(*) as records,
               COUNT(DISTINCT signal_id) as signals,
               COUNT(DISTINCT symbol) as symbols,
               ROUND(AVG(avg_score), 1) as avg_score
        FROM symbol_rankings
        GROUP BY strategy_version
        ORDER BY strategy_version
    """).fetchall()
    return [dict(r) for r in rows]


if __name__ == '__main__':
    conn = get_connection()
    init_tables(conn)
    print("✅ Tables initialized")
    
    symbols = get_symbols(conn)
    print(f"📊 Symbols in DB: {len(symbols)}")
    for s in symbols[:10]:
        print(f"  {s['symbol']}: {s['signal_count']} signals, {s['total_records']} records")
    
    versions = get_version_summary(conn)
    print(f"\n📋 Versions: {versions}")
    conn.close()
