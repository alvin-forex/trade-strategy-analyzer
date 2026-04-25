#!/usr/bin/env python3
"""
Trade Strategy Analyzer — Analysis History Manager

CLI for querying analysis history from SQLite database.
Used by OpenClaw agent for /history and /compare Telegram commands.

Usage:
  python3 history_manager.py list [--limit N] [--signal ID]
  python3 history_manager.py summary <analysis_id>
  python3 history_manager.py compare <signal_id> <v1> <v2>
  python3 history_manager.py save --json <stats_json>
  python3 history_manager.py trend <signal_id>
"""

import sqlite3
import json
import os
import sys
import argparse
import hashlib
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'analysis_history.db')


def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def save_analysis(data: dict) -> int:
    """Save an analysis result to the database. Returns the analysis ID."""
    conn = get_db()
    c = conn.cursor()

    # Extract signal_id from csv_filename
    csv_fn = data.get('csv_filename', '')
    signal_id = data.get('signal_id', '')
    if not signal_id and csv_fn:
        # Try to extract from filename like signal_14581_trades.csv
        import re
        m = re.search(r'(\d+)', csv_fn)
        if m:
            signal_id = m.group(1)

    # Calculate CSV hash for dedup
    csv_hash = data.get('csv_hash', '')
    if not csv_hash and data.get('csv_content'):
        csv_hash = hashlib.md5(data['csv_content'].encode()).hexdigest()[:12]

    # Check for duplicate
    if csv_hash:
        c.execute('SELECT id FROM analyses WHERE csv_hash = ? ORDER BY created_at DESC LIMIT 1', (csv_hash,))
        existing = c.fetchone()
        if existing:
            conn.close()
            return existing['id']  # Return existing ID

    # Insert analysis
    raw_stats = json.dumps(data.get('raw_stats', {}), ensure_ascii=False)
    symbols_summary = json.dumps(data.get('symbols_summary', {}), ensure_ascii=False)

    avg_holding = data.get('avg_holding_hours', 0)
    if avg_holding:
        avg_holding_minutes = avg_holding * 60
    else:
        avg_holding_minutes = data.get('avg_holding_minutes', 0)

    c.execute('''INSERT INTO analyses (
        signal_id, ea_name, pair, csv_filename, set_filename, csv_hash,
        analysis_date, total_positions, total_trades, win_rate, profit_factor,
        total_profit, max_dd, max_dd_percent, avg_layers, avg_holding_minutes,
        sharpe, l1_only_ratio, l4_plus_ratio, l4_recovery_rate,
        entry_score_avg, strategy_score_avg, final_score_avg,
        grade_a_count, grade_b_count, grade_c_count, grade_d_count,
        symbols_summary, report_path, raw_stats
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', (
        signal_id,
        data.get('ea_name', ''),
        data.get('pair', ''),
        csv_fn,
        data.get('set_filename', ''),
        csv_hash,
        data.get('analysis_date', datetime.now().strftime('%Y-%m-%d')),
        data.get('total_positions', 0),
        data.get('total_trades', 0),
        data.get('win_rate', 0),
        data.get('profit_factor', 0),
        data.get('total_profit', 0),
        data.get('max_dd', 0),
        data.get('max_dd_percent', 0),
        data.get('avg_layers', 0),
        avg_holding_minutes,
        data.get('sharpe', 0),
        data.get('l1_only_ratio', 0),
        data.get('l4_plus_ratio', 0),
        data.get('l4_recovery_rate', 0),
        data.get('entry_score_avg', 0),
        data.get('strategy_score_avg', 0),
        data.get('final_score_avg', 0),
        data.get('grade_a_count', 0),
        data.get('grade_b_count', 0),
        data.get('grade_c_count', 0),
        data.get('grade_d_count', 0),
        symbols_summary,
        data.get('report_path', ''),
        raw_stats,
    ))

    analysis_id = c.lastrowid

    # Save symbol-level stats
    for sym_stat in data.get('symbol_stats', []):
        c.execute('''INSERT INTO symbol_stats (analysis_id, symbol, positions, win_rate, avg_profit, profit_factor, max_dd)
        VALUES (?,?,?,?,?,?,?)''', (
            analysis_id,
            sym_stat.get('symbol', ''),
            sym_stat.get('positions', 0),
            sym_stat.get('win_rate', 0),
            sym_stat.get('avg_profit', 0),
            sym_stat.get('profit_factor', 0),
            sym_stat.get('max_dd', 0),
        ))

    # Auto-version
    if signal_id:
        c.execute('SELECT MAX(version) as mv FROM versions WHERE signal_id = ?', (signal_id,))
        row = c.fetchone()
        next_ver = (row['mv'] or 0) + 1
        c.execute('INSERT OR IGNORE INTO versions (signal_id, version, analysis_id) VALUES (?,?,?)',
                  (signal_id, next_ver, analysis_id))

    conn.commit()
    conn.close()
    return analysis_id


def list_analyses(limit=10, signal_id=None):
    """List recent analyses."""
    conn = get_db()
    c = conn.cursor()

    if signal_id:
        c.execute('''SELECT a.*, v.version
                     FROM analyses a
                     LEFT JOIN versions v ON v.analysis_id = a.id AND v.signal_id = a.signal_id
                     WHERE a.signal_id = ?
                     ORDER BY a.created_at DESC LIMIT ?''', (signal_id, limit))
    else:
        c.execute('''SELECT a.*, v.version
                     FROM analyses a
                     LEFT JOIN versions v ON v.analysis_id = a.id
                     ORDER BY a.created_at DESC LIMIT ?''', (limit,))

    rows = c.fetchall()
    conn.close()

    if not rows:
        return "📭 暫無分析記錄"

    lines = ["📊 **分析歷史記錄**\n"]
    for r in rows:
        ver = f"v{r['version']}" if r['version'] else '—'
        profit_emoji = '🟢' if r['total_profit'] > 0 else '🔴'
        lines.append(
            f"**#{r['id']}** {ver} | Signal `{r['signal_id'] or '—'}` "
            f"| {r['ea_name'] or '—'} {r['pair'] or ''}\n"
            f"  {profit_emoji} ${r['total_profit']:.2f} | "
            f"WR {r['win_rate']:.1f}% | PF {r['profit_factor']:.2f} | "
            f"{r['total_positions']} 倉位\n"
            f"  📅 {r['created_at']}"
        )
    return '\n\n'.join(lines)


def get_summary(analysis_id):
    """Get detailed summary of a specific analysis."""
    conn = get_db()
    c = conn.cursor()

    c.execute('SELECT * FROM analyses WHERE id = ?', (analysis_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return f"❌ 找不到分析 #{analysis_id}"

    c.execute('SELECT * FROM symbol_stats WHERE analysis_id = ?', (analysis_id,))
    symbols = c.fetchall()
    conn.close()

    r = row
    profit_emoji = '🟢' if r['total_profit'] > 0 else '🔴'

    # Grade distribution
    total = r['grade_a_count'] + r['grade_b_count'] + r['grade_c_count'] + r['grade_d_count']
    grade_dist = ''
    if total > 0:
        grade_dist = f"   A:{r['grade_a_count']} B:{r['grade_b_count']} C:{r['grade_c_count']} D:{r['grade_d_count']}"

    lines = [
        f"📋 **分析詳情 #{r['id']}**\n",
        f"Signal: `{r['signal_id'] or '—'}` | EA: {r['ea_name'] or '—'} | 貨幣對: {r['pair'] or '—'}",
        f"CSV: `{r['csv_filename']}`",
        f"📅 分析日期: {r['analysis_date']} | 存檔: {r['created_at']}\n",
        f"**核心指標**",
        f"{profit_emoji} 總盈虧: ${r['total_profit']:.2f}",
        f"📈 倉位: {r['total_positions']} | 交易: {r['total_trades']}",
        f"🎯 勝率: {r['win_rate']:.1f}% | PF: {r['profit_factor']:.2f}",
        f"📉 Max DD: ${r['max_dd']:.2f} ({r['max_dd_percent']:.1f}%)",
        f"📊 Sharpe: {r['sharpe']:.2f}",
        f"📚 平均層數: {r['avg_layers']:.2f} | L1-only: {r['l1_only_ratio']:.1f}% | L4+: {r['l4_plus_ratio']:.1f}%",
        f"🔄 L4+ 回歸率: {r['l4_recovery_rate']:.1f}%",
        f"⏱️ 平均持倉: {r['avg_holding_minutes']:.0f} 分鐘",
    ]

    # Scores
    if r['entry_score_avg']:
        lines.append(f"\n**評分**")
        lines.append(f"  入場: {r['entry_score_avg']:.1f} | 策略: {r['strategy_score_avg']:.1f} | 最終: {r['final_score_avg']:.1f}")
        lines.append(grade_dist)

    # Top symbols
    if symbols:
        lines.append(f"\n**貨幣對 Top 5**")
        sorted_syms = sorted(symbols, key=lambda x: x['profit_factor'] or 0, reverse=True)
        for s in sorted_syms[:5]:
            p_emoji = '🟢' if s['avg_profit'] > 0 else '🔴'
            lines.append(f"  {p_emoji} {s['symbol']}: WR {s['win_rate']:.1f}% | PF {s['profit_factor']:.2f} | Avg ${s['avg_profit']:.2f}")

    return '\n'.join(lines)


def compare_versions(signal_id, v1, v2):
    """Compare two versions of the same signal."""
    conn = get_db()
    c = conn.cursor()

    c.execute('''SELECT a.* FROM analyses a
                 JOIN versions v ON v.analysis_id = a.id
                 WHERE v.signal_id = ? AND v.version IN (?,?)
                 ORDER BY v.version''', (signal_id, v1, v2))
    rows = c.fetchall()
    conn.close()

    if len(rows) < 2:
        return f"❌ 找不到 Signal {signal_id} 的 v{v1} 或 v{v2}"

    a, b = rows[0], rows[1]

    def diff(val1, val2, higher_better=True):
        d = val2 - val1
        if abs(d) < 0.01:
            return '➡️ 持平'
        emoji = '🟢' if (d > 0) == higher_better else '🔴'
        return f"{emoji} {'↑' if d > 0 else '↓'} {abs(d):.2f}"

    lines = [
        f"📊 **對比 Signal {signal_id}: v{v1} vs v{v2}**\n",
        f"| 指標 | v{v1} | v{v2} | 變化 |",
        f"|------|------|------|------|",
        f"| 總盈虧 | ${a['total_profit']:.2f} | ${b['total_profit']:.2f} | {diff(a['total_profit'], b['total_profit'])} |",
        f"| 勝率 | {a['win_rate']:.1f}% | {b['win_rate']:.1f}% | {diff(a['win_rate'], b['win_rate'])} |",
        f"| PF | {a['profit_factor']:.2f} | {b['profit_factor']:.2f} | {diff(a['profit_factor'], b['profit_factor'])} |",
        f"| Max DD | ${a['max_dd']:.2f} | ${b['max_dd']:.2f} | {diff(abs(a['max_dd']), abs(b['max_dd']), False)} |",
        f"| Sharpe | {a['sharpe']:.2f} | {b['sharpe']:.2f} | {diff(a['sharpe'], b['sharpe'])} |",
        f"| 倉位 | {a['total_positions']} | {b['total_positions']} | {diff(a['total_positions'], b['total_positions'])} |",
        f"| L1-only% | {a['l1_only_ratio']:.1f}% | {b['l1_only_ratio']:.1f}% | {diff(a['l1_only_ratio'], b['l1_only_ratio'])} |",
        f"| L4+% | {a['l4_plus_ratio']:.1f}% | {b['l4_plus_ratio']:.1f}% | {diff(a['l4_plus_ratio'], b['l4_plus_ratio'], False)} |",
    ]

    return '\n'.join(lines)


def get_trend(signal_id):
    """Get trend data for a signal across all versions."""
    conn = get_db()
    c = conn.cursor()

    c.execute('''SELECT a.*, v.version
                 FROM analyses a
                 JOIN versions v ON v.analysis_id = a.id
                 WHERE v.signal_id = ?
                 ORDER BY v.version''', (signal_id,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        return f"❌ 找不到 Signal {signal_id} 的任何分析"

    lines = [f"📈 **Signal {signal_id} 趨勢** ({len(rows)} 個版本)\n"]

    for r in rows:
        profit_emoji = '🟢' if r['total_profit'] > 0 else '🔴'
        lines.append(
            f"v{r['version']} ({r['analysis_date']}) "
            f"{profit_emoji} ${r['total_profit']:.2f} | "
            f"WR {r['win_rate']:.1f}% | PF {r['profit_factor']:.2f} | "
            f"L1:{r['l1_only_ratio']:.0f}% L4+:{r['l4_plus_ratio']:.0f}%"
        )

    # Trend summary
    if len(rows) >= 2:
        first, last = rows[0], rows[-1]
        wr_trend = '📈 上升' if last['win_rate'] > first['win_rate'] else '📉 下降' if last['win_rate'] < first['win_rate'] else '➡️ 持平'
        pf_trend = '📈 上升' if last['profit_factor'] > first['profit_factor'] else ('📉 下降' if last['profit_factor'] < first['profit_factor'] else '➡️ 持平')

        lines.append(f"\n**趨勢摘要** (v1→v{last['version']}):")
        lines.append(f"  勝率: {first['win_rate']:.1f}% → {last['win_rate']:.1f}% {wr_trend}")
        lines.append(f"  PF: {first['profit_factor']:.2f} → {last['profit_factor']:.2f} {pf_trend}")
        lines.append(f"  總盈虧: ${first['total_profit']:.2f} → ${last['total_profit']:.2f}")

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Trade Strategy Analysis History Manager')
    sub = parser.add_subparsers(dest='command')

    # list
    p_list = sub.add_parser('list', help='List recent analyses')
    p_list.add_argument('--limit', type=int, default=10)
    p_list.add_argument('--signal', type=str, default=None)

    # summary
    p_summary = sub.add_parser('summary', help='Get analysis summary')
    p_summary.add_argument('id', type=int)

    # compare
    p_compare = sub.add_parser('compare', help='Compare two versions')
    p_compare.add_argument('signal_id', type=str)
    p_compare.add_argument('v1', type=int)
    p_compare.add_argument('v2', type=int)

    # trend
    p_trend = sub.add_parser('trend', help='Get trend for a signal')
    p_trend.add_argument('signal_id', type=str)

    # save
    p_save = sub.add_parser('save', help='Save analysis from JSON')
    p_save.add_argument('--json', type=str, required=True, help='JSON file or stdin (-)')

    args = parser.parse_args()

    if args.command == 'list':
        print(list_analyses(args.limit, args.signal))
    elif args.command == 'summary':
        print(get_summary(args.id))
    elif args.command == 'compare':
        print(compare_versions(args.signal_id, args.v1, args.v2))
    elif args.command == 'trend':
        print(get_trend(args.signal_id))
    elif args.command == 'save':
        if args.json == '-':
            data = json.load(sys.stdin)
        else:
            with open(args.json) as f:
                data = json.load(f)
        aid = save_analysis(data)
        print(f"✅ Saved as analysis #{aid}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
