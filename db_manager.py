#!/usr/bin/env python3
"""
Database Manager for TSA (Trade Strategy Analyzer)

Replaces pickle-based data transfer with SQLite storage.
Provides unified API for DDE scoring data (v4 and v5).

Schema:
  - dde_scores: Signal×Symbol scoring results (取代 /tmp/dde_v*_data.pkl)
  - Backward compatible with existing analysis_history.db tables
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from contextlib import contextmanager

# Database path
DATA_DIR = Path(__file__).parent / 'data'
DB_PATH = DATA_DIR / 'tsa.db'

# Ensure data directory exists
DATA_DIR.mkdir(exist_ok=True)


@contextmanager
def get_connection():
    """Get database connection with automatic close."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_database():
    """Initialize database schema if not exists."""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Create dde_scores table (replaces pickle storage)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS dde_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                strategy_version TEXT NOT NULL DEFAULT 'v5',
                batch_run_id TEXT NOT NULL,
                
                -- DDE Score
                dde_score REAL DEFAULT 0,
                
                -- v5 Percentile scores (ranking-based)
                wr_pct REAL DEFAULT 0,
                pf_pct REAL DEFAULT 0,
                dd_pct REAL DEFAULT 0,
                martin_pct REAL DEFAULT 0,
                
                -- Raw metrics (v5)
                wr_raw REAL DEFAULT 0,
                pf_raw REAL DEFAULT 0,
                dd_raw REAL DEFAULT 0,
                martin_raw REAL DEFAULT 0,
                
                -- v4 individual scores (deprecated but kept for compat)
                rr_score REAL DEFAULT 0,
                ml_score REAL DEFAULT 0,
                wr_score REAL DEFAULT 0,
                tc_score REAL DEFAULT 0,
                ht_score REAL DEFAULT 0,
                
                -- Common metrics
                win_rate REAL DEFAULT 0,
                profit_factor REAL DEFAULT 0,
                trades INTEGER DEFAULT 0,
                total_net_pips REAL DEFAULT 0,
                max_dd_pips REAL DEFAULT 0,
                max_loss_pip REAL DEFAULT 0,
                wal REAL DEFAULT 0,
                avg_hold REAL DEFAULT 0,
                
                -- Red card status
                red_card INTEGER DEFAULT 0,
                red_reasons TEXT DEFAULT '',
                
                -- Metadata
                ea TEXT DEFAULT '',
                lv TEXT DEFAULT '',
                layers_json TEXT DEFAULT '{}',
                
                -- MFE/MAE (v5)
                avg_mfe REAL DEFAULT 0,
                avg_mae REAL DEFAULT 0,
                avg_mfe_pips REAL DEFAULT 0,
                avg_mae_pips REAL DEFAULT 0,
                mfe_mae_ratio REAL DEFAULT 0,
                suggest_tp REAL DEFAULT 0,
                suggest_sl REAL DEFAULT 0,
                
                -- BUY/SELL bias
                buy_pct REAL DEFAULT 0,
                sell_pct REAL DEFAULT 0,
                bias TEXT DEFAULT 'MIX',
                
                -- Time insights
                best_day TEXT DEFAULT '',
                worst_day TEXT DEFAULT '',
                
                -- Timestamps
                analysis_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for fast queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dde_version ON dde_scores(strategy_version)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dde_signal ON dde_scores(signal_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dde_symbol ON dde_scores(symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dde_batch ON dde_scores(batch_run_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dde_sig_sym ON dde_scores(signal_id, symbol)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dde_sig_ver ON dde_scores(signal_id, strategy_version)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_dde_sym_ver ON dde_scores(symbol, strategy_version)')
        
        # Create batch_runs metadata table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS batch_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_run_id TEXT NOT NULL UNIQUE,
                strategy_version TEXT NOT NULL,
                run_date TEXT NOT NULL,
                total_signals INTEGER DEFAULT 0,
                total_records INTEGER DEFAULT 0,
                scored_count INTEGER DEFAULT 0,
                red_card_count INTEGER DEFAULT 0,
                global_avg_score REAL DEFAULT 0,
                global_best_score REAL DEFAULT 0,
                status TEXT DEFAULT 'completed',
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        print(f"✅ Database initialized: {DB_PATH}")


# ─── Write Operations ───

def save_scores(results: List[Dict], version: str = 'v5', batch_run_id: Optional[str] = None) -> str:
    """
    Save DDE scoring results to SQLite.
    
    Args:
        results: List of scoring dicts from dde_v*_scorer
        version: 'v4' or 'v5'
        batch_run_id: Optional batch ID, auto-generated if None
    
    Returns:
        batch_run_id
    """
    if not results:
        print("⚠️ No results to save")
        return batch_run_id or ''
    
    init_database()
    
    # Generate batch_run_id if not provided
    if not batch_run_id:
        batch_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Normalize version: ensure 'v' prefix
    if not version.startswith('v'):
        version = 'v' + version
    
    analysis_date = datetime.now().strftime('%Y-%m-%d')
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Clear old data for this version (keep only latest batch)
        cursor.execute('DELETE FROM dde_scores WHERE strategy_version = ?', (version,))
        
        # Insert new records
        for r in results:
            # Convert red_reasons list to JSON string
            red_reasons_json = json.dumps(r.get('red_reasons', []))
            
            # Convert layers dict to JSON string
            layers_json = json.dumps(r.get('layers', {}))
            
            cursor.execute('''
                INSERT INTO dde_scores (
                    signal_id, symbol, strategy_version, batch_run_id,
                    dde_score, wr_pct, pf_pct, dd_pct, martin_pct,
                    wr_raw, pf_raw, dd_raw, martin_raw,
                    rr_score, ml_score, wr_score, tc_score, ht_score,
                    win_rate, profit_factor, trades, total_net_pips,
                    max_dd_pips, max_loss_pip, wal, avg_hold,
                    red_card, red_reasons, ea, lv, layers_json,
                    avg_mfe, avg_mae, avg_mfe_pips, avg_mae_pips,
                    mfe_mae_ratio, suggest_tp, suggest_sl,
                    buy_pct, sell_pct, bias, best_day, worst_day,
                    analysis_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                r['signal_id'], r['symbol'], version, batch_run_id,
                r.get('dde_v5', r.get('dde_v4', 0)),
                r.get('wr_pct', 0), r.get('pf_pct', 0), r.get('dd_pct', 0), r.get('martin_pct', 0),
                r.get('wr_raw', r.get('win_rate', 0)), r.get('pf_raw', r.get('pf', 0)), r.get('dd_raw', r.get('max_dd_pips', 0)), r.get('martin_raw', r.get('wal', 0)),
                r.get('rr', r.get('rr_score', 0)), r.get('ml', r.get('ml_score', 0)), r.get('wr', r.get('wr_score', 0)), r.get('tc', r.get('tc_score', 0)), r.get('ht', r.get('ht_score', 0)),
                r.get('win_rate', 0), r.get('pf', 0), r.get('trades', 0), r.get('total_net_pips', 0),
                r.get('max_dd_pips', 0), r.get('max_loss_pip', 0), r.get('wal', 0), r.get('avg_hold', 0),
                int(r.get('red_card', False)), red_reasons_json, r.get('ea', ''), r.get('lv', ''), layers_json,
                r.get('avg_mfe', 0), r.get('avg_mae', 0), r.get('avg_mfe_pips', 0), r.get('avg_mae_pips', 0),
                r.get('mfe_mae_ratio', 0), r.get('suggest_tp', 0), r.get('suggest_sl', 0),
                r.get('buy_pct', 0), r.get('sell_pct', 0), r.get('bias', 'MIX'), r.get('best_day', ''), r.get('worst_day', ''),
                analysis_date
            ))
        
        # Record batch metadata
        scored_count = len([r for r in results if not r.get('red_card')])
        red_card_count = len([r for r in results if r.get('red_card')])
        
        valid_scores = [r.get('dde_v5', r.get('dde_v4', 0)) for r in results if not r.get('red_card')]
        global_avg = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0
        global_best = max(valid_scores) if valid_scores else 0
        
        cursor.execute('''
            INSERT OR REPLACE INTO batch_runs (
                batch_run_id, strategy_version, run_date,
                total_signals, total_records, scored_count, red_card_count,
                global_avg_score, global_best_score, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'completed')
        ''', (
            batch_run_id, version, analysis_date,
            len(set(r['signal_id'] for r in results)), len(results), scored_count, red_card_count,
            global_avg, global_best
        ))
        
        conn.commit()
        
        print(f"✅ Saved {len(results)} records to SQLite (v{version}, batch={batch_run_id})")
        print(f"   Scored: {scored_count}, Red cards: {red_card_count}, Avg: {global_avg}, Best: {global_best}")
    
    return batch_run_id


# ─── Read Operations ───

def load_scores(version: str = 'v5', batch_run_id: Optional[str] = None) -> List[Dict]:
    """
    Load DDE scoring results from SQLite.
    
    Args:
        version: 'v4' or 'v5'
        batch_run_id: Optional specific batch, uses latest if None
    
    Returns:
        List of scoring dicts (same format as pickle output)
    """
    init_database()
    
    # Normalize version
    if not version.startswith('v'):
        version = 'v' + version
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get latest batch_run_id if not specified
        if not batch_run_id:
            cursor.execute('''
                SELECT batch_run_id FROM dde_scores
                WHERE strategy_version = ?
                ORDER BY created_at DESC LIMIT 1
            ''', (version,))
            row = cursor.fetchone()
            if not row:
                print(f"⚠️ No data found for version {version}")
                return []
            batch_run_id = row['batch_run_id']
        
        # Load all records for this batch
        cursor.execute('''
            SELECT * FROM dde_scores
            WHERE strategy_version = ? AND batch_run_id = ?
            ORDER BY dde_score DESC
        ''', (version, batch_run_id))
        
        rows = cursor.fetchall()
        results = []
        
        for row in rows:
            r = dict(row)
            
            # Convert JSON fields back to Python objects
            r['red_reasons'] = json.loads(r['red_reasons'] or '[]')
            r['layers'] = json.loads(r['layers_json'] or '{}')
            
            # Map SQLite columns back to scorer output format
            r['dde_v5'] = r['dde_score'] if version == 'v5' else 0
            r['dde_v4'] = r['dde_score'] if version == 'v4' else 0
            
            # v5 compatibility
            if version == 'v5':
                r['pf'] = r['profit_factor']
                r['avg_hold'] = r['avg_hold'] if 'avg_hold' in r else 0
            
            # v4 compatibility
            if version == 'v4':
                r['rr'] = r['rr_score']
                r['ml'] = r['ml_score']
                r['wr'] = r['wr_score']
                r['tc'] = r['tc_score']
                r['ht'] = r['ht_score']
                r['total_profit_pips'] = r['total_net_pips']
            
            # Red card as boolean
            r['red_card'] = bool(r['red_card'])
            
            results.append(r)
        
        print(f"📦 Loaded {len(results)} records from SQLite ({version}, batch={batch_run_id})")
        return results


def get_scores_by_signal(signal_id: str, version: str = 'v5') -> List[Dict]:
    """Get all scores for a specific signal."""
    init_database()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM dde_scores
            WHERE signal_id = ? AND strategy_version = ?
            ORDER BY symbol
        ''', (signal_id, version))
        
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        
        for r in results:
            r['red_reasons'] = json.loads(r['red_reasons'] or '[]')
            r['layers'] = json.loads(r['layers_json'] or '{}')
            r['dde_v5'] = r['dde_score'] if version == 'v5' else 0
            r['dde_v4'] = r['dde_score'] if version == 'v4' else 0
            r['red_card'] = bool(r['red_card'])
        
        return results


def get_scores_by_symbol(symbol: str, version: str = 'v5') -> List[Dict]:
    """Get all scores for a specific symbol."""
    init_database()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM dde_scores
            WHERE symbol = ? AND strategy_version = ?
            ORDER BY dde_score DESC
        ''', (symbol, version))
        
        rows = cursor.fetchall()
        results = [dict(row) for row in rows]
        
        for r in results:
            r['red_reasons'] = json.loads(r['red_reasons'] or '[]')
            r['layers'] = json.loads(r['layers_json'] or '{}')
            r['dde_v5'] = r['dde_score'] if version == 'v5' else 0
            r['dde_v4'] = r['dde_score'] if version == 'v4' else 0
            r['red_card'] = bool(r['red_card'])
        
        return results


def get_latest_batch(version: str = 'v5') -> Optional[Dict]:
    """Get metadata for latest batch run."""
    init_database()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM batch_runs
            WHERE strategy_version = ?
            ORDER BY created_at DESC LIMIT 1
        ''', (version,))
        
        row = cursor.fetchone()
        return dict(row) if row else None


def get_batch_list(version: str = 'v5', limit: int = 10) -> List[Dict]:
    """Get list of recent batch runs."""
    init_database()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM batch_runs
            WHERE strategy_version = ?
            ORDER BY created_at DESC LIMIT ?
        ''', (version, limit))
        
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


# ─── Migration Utility ───

def migrate_from_pickle(pkl_path: str, version: str = 'v5') -> str:
    """
    Migrate data from legacy pickle file to SQLite.
    
    Args:
        pkl_path: Path to .pkl file
        version: 'v4' or 'v5'
    
    Returns:
        batch_run_id
    """
    import pickle
    
    pkl_file = Path(pkl_path)
    if not pkl_file.exists():
        print(f"❌ Pickle file not found: {pkl_path}")
        return ''
    
    print(f"📦 Migrating from pickle: {pkl_path}")
    
    with open(pkl_file, 'rb') as f:
        data = pickle.load(f)
    
    if not isinstance(data, list):
        print(f"❌ Unexpected pickle format: {type(data)}")
        return ''
    
    # Use pickle filename as batch_run_id hint
    batch_run_id = pkl_file.stem.replace('dde_', '').replace('_data', '')
    
    return save_scores(data, version, batch_run_id)


# ─── Stats & Info ───

def get_database_stats() -> Dict:
    """Get database statistics."""
    init_database()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        stats = {'db_path': str(DB_PATH)}
        
        # dde_scores stats
        cursor.execute('SELECT COUNT(*) as total FROM dde_scores')
        stats['total_scores'] = cursor.fetchone()['total']
        
        cursor.execute('SELECT COUNT(DISTINCT signal_id) as cnt FROM dde_scores')
        stats['unique_signals'] = cursor.fetchone()['cnt']
        
        cursor.execute('SELECT COUNT(DISTINCT symbol) as cnt FROM dde_scores')
        stats['unique_symbols'] = cursor.fetchone()['cnt']
        
        cursor.execute('SELECT COUNT(DISTINCT batch_run_id) as cnt FROM dde_scores')
        stats['batch_runs'] = cursor.fetchone()['cnt']
        
        # By version
        cursor.execute('SELECT strategy_version, COUNT(*) as cnt FROM dde_scores GROUP BY strategy_version')
        stats['by_version'] = {row['strategy_version']: row['cnt'] for row in cursor.fetchall()}
        
        # batch_runs stats
        cursor.execute('SELECT COUNT(*) as total FROM batch_runs')
        stats['total_batches'] = cursor.fetchone()['total']
        
        return stats


def clear_old_batches(version: str = 'v5', keep_latest: int = 3):
    """Clear old batch runs, keep only latest N."""
    init_database()
    
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Get batch IDs to keep
        cursor.execute('''
            SELECT batch_run_id FROM batch_runs
            WHERE strategy_version = ?
            ORDER BY created_at DESC LIMIT ?
        ''', (version, keep_latest))
        
        keep_ids = [row['batch_run_id'] for row in cursor.fetchall()]
        
        if not keep_ids:
            return
        
        # Delete old scores
        cursor.execute('''
            DELETE FROM dde_scores
            WHERE strategy_version = ? AND batch_run_id NOT IN ({})
        '''.format(','.join(['?' for _ in keep_ids])), [version] + keep_ids)
        
        deleted_scores = cursor.rowcount
        
        # Delete old batch metadata
        cursor.execute('''
            DELETE FROM batch_runs
            WHERE strategy_version = ? AND batch_run_id NOT IN ({})
        '''.format(','.join(['?' for _ in keep_ids])), [version] + keep_ids)
        
        deleted_batches = cursor.rowcount
        
        conn.commit()
        
        print(f"🗑️ Cleared {deleted_scores} old scores and {deleted_batches} old batches (kept {keep_latest} latest)")


# ─── CLI Entry Point ───

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='TSA Database Manager')
    parser.add_argument('action', choices=['init', 'stats', 'migrate', 'clear'], help='Action to perform')
    parser.add_argument('--pkl', help='Pickle file path for migration')
    parser.add_argument('--version', default='v5', help='Strategy version')
    parser.add_argument('--keep', type=int, default=3, help='Keep latest N batches')
    
    args = parser.parse_args()
    
    if args.action == 'init':
        init_database()
        print(f"✅ Database ready: {DB_PATH}")
    
    elif args.action == 'stats':
        stats = get_database_stats()
        print("📊 Database Statistics:")
        for k, v in stats.items():
            print(f"   {k}: {v}")
    
    elif args.action == 'migrate':
        if not args.pkl:
            print("❌ --pkl required for migration")
        else:
            batch_id = migrate_from_pickle(args.pkl, args.version)
            print(f"✅ Migrated to batch: {batch_id}")
    
    elif args.action == 'clear':
        clear_old_batches(args.version, args.keep)