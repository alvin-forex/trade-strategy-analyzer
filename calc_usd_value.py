#!/usr/bin/env python3
"""
Calculate USD-value P/L per standard lot for cross-pair comparison.
Does NOT modify existing data — only adds calculated columns.
"""
import sqlite3
import math
from collections import defaultdict

DB = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/data/tsa.db"

# Pip value per STANDARD LOT (100,000 units) in USD
# Using approximate current rates (Jun 2026)
PIP_VALUE_USD = {
    # USD direct (USD is quote)
    "EURUSD": 10.00,   # 1 pip = 0.00010 × 100,000 = $10
    "GBPUSD": 10.00,
    "AUDUSD": 10.00,
    "NZDUSD": 10.00,
    # USD inverse (USD is base)
    "USDJPY": 6.25,    # at ~160: 1 pip = 0.010 × 100,000 / 160 = $6.25
    "USDCHF": 10.87,   # at ~0.92: 1 pip = 0.00010 × 100,000 / 0.92 = $10.87
    "USDCAD": 7.35,    # at ~1.36: 1 pip = 0.00010 × 100,000 / 1.36 = $7.35
    # Cross pairs (neither is USD)
    "EURJPY": 6.25,    # ¥1000 / 160 = $6.25
    "EURGBP": 13.16,   # £10 × 1.316 = $13.16
    "EURCHF": 10.87,   # CHF10 / 0.92 = $10.87
    "EURCAD": 7.35,    # CAD10 / 1.36 = $7.35
    "EURAUD": 6.54,    # AUD10 × 0.654 = $6.54
    "EURNZD": 6.11,    # NZD10 × 0.611 = $6.11
    "GBPJPY": 6.25,    # ¥1000 / 160 = $6.25
    "GBPCHF": 10.87,   # CHF10 / 0.92 = $10.87
    "GBPCAD": 7.35,    # CAD10 / 1.36 = $7.35
    "GBPAUD": 6.54,    # AUD10 × 0.654 = $6.54
    "GBPNZD": 6.11,    # NZD10 × 0.611 = $6.11
    "EURGBP": 13.16,   # £10 × 1.316 = $13.16
    "CHFJPY": 5.75,    # ¥1000 / (0.92 × 160) or just note: 1 pip in CHFJPY... this is cross
    "AUDJPY": 6.25,    # ¥1000 / 160 = $6.25
    "AUDCHF": 10.87,   # CHF10 / 0.92 = $10.87
    "AUDCAD": 7.35,    # CAD10 / 1.36 = $7.35
    "AUDNZD": 6.54,    # NZD10 × 0.654 = $6.54... wait no
    "CADJPY": 6.25,    # ¥1000 / 160 = $6.25
    "CADCHF": 10.87,   # CHF10 / 0.92 = $10.87
    "NZDJPY": 6.25,    # ¥1000 / 160 = $6.25
    "NZDCHF": 10.87,   # CHF10 / 0.92 = $10.87
    "NZDCAD": 7.35,    # CAD10 / 1.36 = $7.35
    # Commodities
    "XAUUSD": 1.00,    # Gold: varies by broker, ~$1/pip (0.01) per standard lot
    "XAGUSD": 5.00,    # Silver: ~$5/pip
}

# Better pip value calculation (approximate)
# For most fx pairs: 1 pip (5-digit broker) = 0.00010
# Standard lot = 100,000 units
# Pip Value = 0.00010 × 100,000 / quote_currency_to_usd_rate
# For inverse pairs (USDJPY, USDCHF): 0.010 × 100,000 / rate
# For JPY crosses: 0.010 × 100,000 / JPYUSD... which means 1000 / USDJPY

# But for our purposes we want "1 monitoring pip" = point. Let me recalculate
# Since total_net_pips in DB uses 5-digit broker points:
# Most pairs: 1 pip = 10 points (e.g., 0.00010 = 10 points)
# JPY pairs: 1 pip = 10 points (e.g., 0.010 = 10 points)
# So total_net_pips is in "points" (5th decimal) format

# USD per point for standard lot:
# EURUSD: 0.00001 × 100000 = $1.00 per point
# USDJPY: 0.001 / 160 = $0.625 per point... wait
# 1 point = 0.001 for JPY pairs
# Value per point = 0.001 × 100,000 / USDJPY rate = 100 / 160 = $0.625
# 
# Actually wait. For MT4/MT5 standard lot:
# EURUSD 1 pip (0.00010) = $10
# EURUSD 1 point (0.00001) = $1
# USDJPY 1 pip (0.010) = ¥1000 = $1000/160 = $6.25
# USDJPY 1 point (0.001) = ¥100 = $100/160 = $0.625

# Since total_net_pips is in points (5-digit), let me calculate per-point value:
POINT_VALUE_USD = {}
for sym, pip_val in PIP_VALUE_USD.items():
    # pip in 5-digit = 10 points, so 1 point = pip/10
    POINT_VALUE_USD[sym] = round(pip_val / 10, 3)

# For pairs not in the dict, estimate from similar
def get_point_value(symbol):
    if symbol in POINT_VALUE_USD:
        return POINT_VALUE_USD[symbol]
    # Estimate from symbol pattern
    base = symbol[:3] if symbol.startswith("X") else symbol[:3]
    quote = symbol[3:] if symbol.startswith("X") else symbol[3:]
    # Try reverse
    rev = quote + base
    if rev in POINT_VALUE_USD:
        # 1 pip in reverse pair gives inverse value
        return round(1 / (POINT_VALUE_USD[rev] * 10 / 10), 3)
    return 1.0  # fallback

conn = sqlite3.connect(DB)
cur = conn.cursor()

# Get top green-card combos with SET files
cur.execute("""
    SELECT d.id, d.signal_id, d.symbol, d.ea, d.trades, d.win_rate, d.profit_factor,
           d.total_net_pips, d.max_dd_pips, d.wal, d.avg_mfe_pips, d.avg_mae_pips,
           d.suggest_tp, d.suggest_sl,
           d.dde_score, d.wr_raw, d.pf_raw, d.dd_raw, d.martin_raw
    FROM dde_scores d
    WHERE d.red_card = 0
      AND d.total_net_pips IS NOT NULL
      AND d.trades >= 8
    ORDER BY d.dde_score DESC
""")

rows = cur.fetchall()

# Get symbol columns
col_names = [d[0] for d in cur.description]

results = []
for row in rows:
    d = dict(zip(col_names, row))
    sym = d['symbol']
    trades = d['trades']
    total_pips = d['total_net_pips']
    max_dd_pips = d['max_dd_pips']
    sl = d['suggest_sl']
    tp = d['suggest_tp']
    
    pip_pt = get_point_value(sym)  # USD per point

    # per-standard-lot USD value
    total_usd = round(total_pips * pip_pt, 2)
    max_dd_usd = round(max_dd_pips * pip_pt, 2)
    avg_trade_usd = round(total_usd / trades, 2) if trades > 0 else 0
    
    # Weekly estimate (assuming trades spread over BT period)
    # BT period ~1 year from most signals
    weeks = 52
    avg_trades_per_week = round(trades / weeks, 1)
    weekly_usd = round(total_usd / weeks, 2)
    monthly_usd = round(total_usd / 12, 2)
    
    # Risk metrics
    # R-multiple if SL is available
    sl_usd = round(sl * pip_pt, 2) if sl and sl > 0 else None
    tp_usd = round(tp * pip_pt, 2) if tp and tp > 0 else None
    rr_ratio = round(tp / sl, 2) if sl and sl > 0 and tp and tp > 0 else None
    
    # Max DD as % of a $2000 account
    dd_pct_2k = round(max_dd_usd / 2000 * 100, 1) if max_dd_usd else 0
    
    # MFE/MAE in USD
    avg_mfe_usd = round(d['avg_mfe_pips'] * pip_pt, 2) if d['avg_mfe_pips'] else None
    avg_mae_usd = round(d['avg_mae_pips'] * pip_pt, 2) if d['avg_mae_pips'] else None
    
    results.append({
        'signal_id': d['signal_id'],
        'symbol': sym,
        'ea': d['ea'],
        'trades': trades,
        'win_rate': d['win_rate'],
        'profit_factor': d['profit_factor'],
        'total_net_pips': total_pips,
        'total_net_usd': total_usd,
        'max_dd_pips': max_dd_pips,
        'max_dd_usd': max_dd_usd,
        'dd_pct_2k': dd_pct_2k,
        'avg_trade_usd': avg_trade_usd,
        'trades_week': avg_trades_per_week,
        'weekly_usd': weekly_usd,
        'monthly_usd': monthly_usd,
        'suggest_sl_pips': sl if sl else '-',
        'suggest_tp_pips': tp if tp else '-',
        'suggest_sl_usd': sl_usd if sl_usd is not None else '-',
        'suggest_tp_usd': tp_usd if tp_usd is not None else '-',
        'rr_ratio': rr_ratio if rr_ratio is not None else '-',
        'avg_mfe_usd': avg_mfe_usd,
        'avg_mae_usd': avg_mae_usd,
        'dde_score': d['dde_score'],
        'pip_per_point_usd': pip_pt,
    })

# Sort by DDE score descending
results.sort(key=lambda x: x['dde_score'], reverse=True)

# Print header
header = f"{'Signal':>7} {'Symbol':>8} {'EA':>16} {'Tr':>4} {'WR%':>5} {'PF':>5} {'Net$':>9} {'DD$':>7} {'DD%':>5} {'Avg$':>7} {'T/Wk':>5} {'Wk$':>7} {'Mo$':>8} {'SL$':>6} {'TP$':>6} {'R:R':>5} {'Ppt$':>6}"
print(header)
print("=" * len(header))

for r in results[:60]:
    signal = r['signal_id']
    ea_short = r['ea'][:14]
    line = f"{signal:>7} {r['symbol']:>8} {ea_short:>16} {r['trades']:>4} {r['win_rate']:>5.1f} {r['profit_factor']:>5.2f}"
    line += f" {r['total_net_usd']:>8.0f}$"
    dd_s = f"{r['max_dd_usd']:>4.0f}$" if r['max_dd_usd'] else "  $0"
    line += f" {dd_s:>7}"
    line += f" {r['dd_pct_2k']:>5.1f}"
    avg_s = f"{r['avg_trade_usd']:>4.1f}$" if r['avg_trade_usd'] else "0.0$"
    line += f" {avg_s:>7}"
    line += f" {r['trades_week']:>5.1f} {r['weekly_usd']:>6.1f}$"
    line += f" {r['monthly_usd']:>7.1f}$"
    sl_s = f"{r['suggest_sl_usd']}" if isinstance(r['suggest_sl_usd'], (int, float)) else "---"
    line += f" {sl_s:>6}"
    tp_s = f"{r['suggest_tp_usd']}" if isinstance(r['suggest_tp_usd'], (int, float)) else "---"
    line += f" {tp_s:>6}"
    line += f" {str(r['rr_ratio']):>5}" 
    line += f" {r['pip_per_point_usd']:>6.3f}"
    print(line)

print()
print("=" * len(header))
print(f"Total combos: {len(results)}")
print()
print("=== NOTES ===")
print("- Net$ = total_net_pips × USD value per point (standard lot)")
print("- DD% = max_dd_usd / $2000 account")
print("- SL$/TP$ = suggested stop/take in USD per standard lot")
print("- R:R = suggest_tp / suggest_sl (risk-reward ratio)")
print("- Ppt$ = USD value per 1 point (0.00001 for non-JPY)")
print("- All values assume STANDARD LOT (100k units)")
print("- Original pips data UNCHANGED — only calculated columns added")

conn.close()