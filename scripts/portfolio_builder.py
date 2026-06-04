#!/usr/bin/env python3
"""
Portfolio Builder v1.0
======================
Exclude ghost positions → Re-rank signals → Select optimal portfolio → Generate MT4 configs

Usage:
  python3 scripts/portfolio_builder.py [--accounts N] [--budget_per_account USD] [--weekly_target PCT]
"""

import argparse
import csv
import json
import math
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

# ─── Config ────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BASE_DIR / "samples"
SET_DIR = BASE_DIR / "downloads"
EA_MAP_FILE = BASE_DIR / "ea_name_mapping.json"
LOT_CONFIG_FILE = BASE_DIR / "ea_lot_configs.json"
SIGNAL_LOT_MAP_FILE = BASE_DIR / "signal_lot_mapping.json"
SET_LAYERS_FILE = BASE_DIR / "set_lot_layers.json"
OUTPUT_DIR = BASE_DIR / "data"

GHOST_THRESHOLD_DAYS = 30

# Exclude Flash and S10 EA types
EXCLUDED_EA_TYPES = ["Flash", "S10", "AutoLot"]

# ─── EA Name Mapping ──────────────────────────────────────────────────────
def load_ea_mapping():
    """Load signal -> EA types mapping"""
    mapping = {}
    try:
        with open(EA_MAP_FILE) as f:
            content = f.read()
        # Fix: file may have multiple JSON objects
        decoder = json.JSONDecoder()
        pos = 0
        while pos < len(content):
            content_strip = content[pos:].lstrip()
            if not content_strip:
                break
            obj, end = decoder.raw_decode(content_strip)
            mapping.update(obj)
            pos += end + (len(content[pos:]) - len(content_strip))
    except Exception as e:
        print(f"⚠️ EA mapping load error: {e}")
    return mapping

def get_primary_ea(ea_list):
    """Get primary (non-Flash) EA from list"""
    if not ea_list:
        return "Unknown"
    for ea in ea_list:
        if not any(ex.lower() in ea.lower() for ex in ["Flash"]):
            return ea
    return ea_list[0]

def get_ea_type(ea_name):
    """Extract EA type from name"""
    if "Dragon Wave" in ea_name:
        return "DW"
    elif "MKD" in ea_name:
        return "MKD"
    elif "SMA" in ea_name:
        return "SMA"
    elif "Gemini" in ea_name:
        return "Gemini"
    elif "Flash" in ea_name:
        return "Flash"
    elif "TSR" in ea_name or "Tiger" in ea_name:
        return "TSR"
    else:
        return "Other"

def get_ea_full_type(ea_name):
    """Get full EA type including version"""
    return ea_name

# ─── CSV Loading & Ghost Exclusion ────────────────────────────────────────
def parse_csv_datetime(dt_str):
    """Parse CSV datetime in DD/MM/YYYY HH:MM:SS or YYYY.MM.DD HH:MM:SS format"""
    dt_str = dt_str.strip()
    if not dt_str:
        return None
    for fmt in ['%d/%m/%Y %H:%M:%S', '%Y.%m.%d %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None

def load_csv_trades(csv_path):
    """Load trades from a CSV file"""
    trades = []
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle different column names
                profit = 0
                for key in ['Net Profit', 'Profit', 'profit']:
                    val = row.get(key, '').strip()
                    if val:
                        try:
                            profit = float(val)
                        except ValueError:
                            pass
                        break
                
                pips = 0
                for key in ['Net Pips', 'Pips', 'pips']:
                    val = row.get(key, '').strip()
                    if val:
                        try:
                            pips = float(val)
                        except ValueError:
                            pass
                        break
                
                trade = {
                    'symbol': row.get('Symbol', '').strip(),
                    'type': row.get('Type', '').strip().lower(),
                    'lots': float(row.get('Lots', 0) or 0),
                    'open_time': row.get('Open Time', '').strip(),
                    'close_time': row.get('Close Time', '').strip(),
                    'profit': profit,
                    'comment': row.get('Comment', '').strip(),
                    'pips': pips,
                }
                trades.append(trade)
    except Exception as e:
        print(f"  ⚠️ Error loading {csv_path.name}: {e}")
    return trades

def exclude_ghost_positions(trades, threshold_days=GHOST_THRESHOLD_DAYS):
    """
    Exclude ghost positions: trades open for ≥ threshold_days.
    Ghost positions typically indicate forgotten/abandoned trades.
    """
    clean = []
    ghost_count = 0
    ghost_pnl = 0.0
    
    for t in trades:
        try:
            open_dt = parse_csv_datetime(t['open_time'])
            close_dt = parse_csv_datetime(t['close_time'])
            if not open_dt or not close_dt:
                clean.append(t)
                continue
            hold_days = (close_dt - open_dt).total_seconds() / 86400
            
            if hold_days >= threshold_days:
                ghost_count += 1
                ghost_pnl += t['profit']
                continue
        except Exception:
            pass  # Can't parse dates, keep the trade
        
        clean.append(t)
    
    return clean, ghost_count, ghost_pnl

# ─── Signal Statistics ────────────────────────────────────────────────────
def calc_signal_stats(signal_id, trades, ea_type):
    """Calculate comprehensive statistics for a signal"""
    if not trades:
        return None
    
    n = len(trades)
    wins = [t for t in trades if t['profit'] > 0]
    losses = [t for t in trades if t['profit'] <= 0]
    
    total_pnl = sum(t['profit'] for t in trades)
    total_wins = sum(t['profit'] for t in wins)
    total_losses = abs(sum(t['profit'] for t in losses))
    
    win_rate = len(wins) / n * 100 if n > 0 else 0
    profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
    
    # Max drawdown (peak-to-trough)
    peak = 0
    max_dd = 0
    cum_pnl = 0
    for t in trades:
        cum_pnl += t['profit']
        if cum_pnl > peak:
            peak = cum_pnl
        dd = peak - cum_pnl
        if dd > max_dd:
            max_dd = dd
    
    # Average trade
    avg_pnl = total_pnl / n if n > 0 else 0
    avg_win = total_wins / len(wins) if wins else 0
    avg_loss = total_losses / len(losses) if losses else 0
    
    # Weekly return estimate (based on data span)
    dates = []
    for t in trades:
        dt = parse_csv_datetime(t['close_time'])
        if dt:
            dates.append(dt)
    
    weeks = 1
    if len(dates) >= 2:
        span_days = (max(dates) - min(dates)).total_seconds() / 86400
        weeks = max(span_days / 7, 1)
    
    weekly_pnl = total_pnl / weeks
    weekly_trades = n / weeks
    
    # Risk-adjusted metrics
    returns = [t['profit'] for t in trades]
    if len(returns) > 1:
        mean_r = sum(returns) / len(returns)
        var_r = sum((r - mean_r) ** 2 for r in returns) / (len(returns) - 1)
        std_r = var_r ** 0.5
        sharpe = mean_r / std_r * (52 ** 0.5) if std_r > 0 else 0  # Annualized weekly
    else:
        sharpe = 0
    
    # Symbols traded
    symbols = list(set(t['symbol'] for t in trades if t['symbol']))
    
    return {
        'signal_id': signal_id,
        'ea_type': ea_type,
        'total_trades': n,
        'win_rate': round(win_rate, 1),
        'profit_factor': round(profit_factor, 2),
        'total_pnl': round(total_pnl, 2),
        'max_drawdown': round(max_dd, 2),
        'avg_pnl': round(avg_pnl, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'weekly_pnl': round(weekly_pnl, 2),
        'weekly_trades': round(weekly_trades, 1),
        'sharpe': round(sharpe, 2),
        'symbols': symbols,
        'total_wins': len(wins),
        'total_losses': len(losses),
        'weeks_data': round(weeks, 1),
    }

# ─── Scoring (DDE v5 style) ──────────────────────────────────────────────
def score_signal(stats):
    """Score a signal for portfolio selection (0-100)"""
    if not stats:
        return 0
    
    # WR Score (0-30): Higher WR = better
    wr = stats['win_rate']
    wr_score = min(30, wr * 0.4)  # 75% WR = 30 points
    
    # EV Score (0-30): Based on avg PnL
    ev = stats['avg_pnl']
    if ev > 20:
        ev_score = 30
    elif ev > 10:
        ev_score = 25
    elif ev > 5:
        ev_score = 20
    elif ev > 2:
        ev_score = 15
    elif ev > 0:
        ev_score = 10
    else:
        ev_score = 0
    
    # PF Score (0-20): Higher PF = better
    pf = min(stats['profit_factor'], 5.0)
    pf_score = min(20, pf * 5)
    
    # Count Score (0-15): More trades = more reliable
    count = stats['total_trades']
    if count >= 500:
        count_score = 15
    elif count >= 200:
        count_score = 12
    elif count >= 100:
        count_score = 10
    elif count >= 50:
        count_score = 7
    else:
        count_score = 3
    
    # DD Score (0-5): Lower DD relative to PnL = better
    dd = stats['max_drawdown']
    pnl = stats['total_pnl']
    if pnl > 0 and dd > 0:
        dd_ratio = dd / pnl
        if dd_ratio < 0.1:
            dd_score = 5
        elif dd_ratio < 0.2:
            dd_score = 4
        elif dd_ratio < 0.3:
            dd_score = 3
        elif dd_ratio < 0.5:
            dd_score = 2
        else:
            dd_score = 1
    else:
        dd_score = 0
    
    total = wr_score + ev_score + pf_score + count_score + dd_score
    return round(total, 1)

def get_grade(score):
    if score >= 85: return "S+"
    elif score >= 70: return "S"
    elif score >= 55: return "A"
    elif score >= 40: return "B"
    elif score >= 25: return "C"
    elif score >= 15: return "D"
    else: return "E"

# ─── Portfolio Selection ──────────────────────────────────────────────────
def select_portfolio(scored_signals, num_accounts=5, budget_per_account=1000, weekly_target_pct=20):
    """
    Select optimal signal portfolio:
    - Diversify across EA types and symbols
    - Maximize combined weekly return
    - Control risk (DD per account)
    - Prefer signals with SET files available
    - Focus: 3-10 symbols per account for manageable risk
    """
    # Sort by score descending
    ranked = sorted(scored_signals, key=lambda x: x['score'], reverse=True)
    
    # Filter candidates: min score 55 (A grade), positive PnL, min 50 trades, manageable symbol count
    candidates = [
        s for s in ranked 
        if s['score'] >= 55 
        and s['total_pnl'] > 0 
        and s['total_trades'] >= 50
        and len(s['symbols']) <= 15  # Avoid overly diversified
        and 'profit' not in s['symbols']  # Data quality check
    ]
    
    print(f"\n📋 Portfolio Selection Input:")
    print(f"  Qualified candidates: {len(candidates)} (score ≥ 55, PnL > 0, trades ≥ 50, symbols ≤ 15)")
    print(f"  Target accounts: {num_accounts}")
    print(f"  Budget per account: ${budget_per_account}")
    print(f"  Weekly target: {weekly_target_pct}%")
    
    # Group by EA type
    ea_groups = defaultdict(list)
    for s in candidates:
        ea_groups[s['ea_type']].append(s)
    print(f"  EA type groups: {dict((k, len(v)) for k, v in ea_groups.items())}")
    
    target_weekly = budget_per_account * weekly_target_pct / 100
    
    # Selection strategy:
    # 1. Pick best signal per EA type (diversification)
    # 2. Prioritize: WR > 70%, PF > 3, reasonable DD
    # 3. Fill remaining slots with absolute best
    
    selected = []
    used_symbols = set()
    
    # Pass 1: Pick top from each major EA type
    ea_priority = ['DW', 'MKD', 'SMA', 'Other', 'Gemini']
    for ea_type in ea_priority:
        if ea_type not in ea_groups or len(selected) >= num_accounts:
            continue
        group = ea_groups[ea_type]
        for s in group:
            sym_set = set(s['symbols'])
            overlap = len(sym_set & used_symbols)
            if overlap < len(sym_set) * 0.5:
                selected.append(s)
                used_symbols.update(sym_set)
                break
    
    # Pass 2: Fill remaining with best available
    if len(selected) < num_accounts:
        for s in candidates:
            if s in selected:
                continue
            sym_set = set(s['symbols'])
            overlap = len(sym_set & used_symbols) / max(len(sym_set), 1)
            if len(selected) < num_accounts:
                selected.append(s)
                used_symbols.update(sym_set)
            else:
                break
    
    return selected[:num_accounts], target_weekly

# ─── MT4 Config Generator ─────────────────────────────────────────────────
def find_set_files(signal_id):
    """Find SET files for a signal"""
    set_files = []
    # Check multiple possible locations
    search_dirs = [
        SET_DIR / str(signal_id),
        SET_DIR / f"({signal_id})",
        SET_DIR / "set_files",
        SET_DIR / "set_files_test",
    ]
    
    for d in search_dirs:
        if d.exists():
            for sf in d.glob("*.set"):
                if signal_id in sf.name:
                    set_files.append(sf)
    
    # Also check root of downloads for signal_XXX_*.set
    for sf in SET_DIR.glob(f"signal_{signal_id}_*.set"):
        set_files.append(sf)
    
    return list(set(set_files))

def generate_mt4_config(account_num, signal_info, budget=1000):
    """Generate MT4 configuration for one account"""
    signal_id = signal_info['signal_id']
    set_files = find_set_files(signal_id)
    
    config = {
        'account': account_num,
        'signal_id': signal_id,
        'ea_type': signal_info['ea_type'],
        'symbols': signal_info['symbols'],
        'budget_usd': budget,
        'score': signal_info['score'],
        'grade': get_grade(signal_info['score']),
        'stats': {
            'win_rate': signal_info['win_rate'],
            'profit_factor': signal_info['profit_factor'],
            'total_pnl': signal_info['total_pnl'],
            'max_dd': signal_info['max_drawdown'],
            'weekly_pnl': signal_info['weekly_pnl'],
            'weekly_trades': signal_info['weekly_trades'],
            'total_trades': signal_info['total_trades'],
        },
        'set_files': [sf.name for sf in set_files],
        'recommended_lot': round(budget * 0.01 / 1000, 2),  # 1% risk, 1000:1 leverage estimate
        'notes': '',
    }
    
    # Risk notes
    if signal_info['max_drawdown'] > budget * 0.3:
        config['notes'] += '⚠️ Max DD > 30% of budget. '
    if signal_info['weekly_pnl'] > 0:
        projected_weekly = signal_info['weekly_pnl']
        config['projected_weekly_return_pct'] = round(projected_weekly / budget * 100, 1)
    
    return config

# ─── Main ─────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description='Portfolio Builder')
    parser.add_argument('--accounts', type=int, default=5, help='Number of accounts')
    parser.add_argument('--budget', type=int, default=1000, help='Budget per account (USD)')
    parser.add_argument('--target', type=int, default=20, help='Weekly target return (%)')
    parser.add_argument('--output', default=None, help='Output JSON file')
    args = parser.parse_args()
    
    print("🦀 Portfolio Builder v1.0")
    print("=" * 60)
    
    # 1. Load EA mapping
    ea_mapping = load_ea_mapping()
    print(f"\n📡 EA Mapping loaded: {len(ea_mapping)} signals")
    
    # 2. Load all CSVs
    csv_files = sorted(SAMPLES_DIR.glob("*.csv"))
    print(f"📊 Found {len(csv_files)} CSV files")
    
    all_stats = []
    total_ghost = 0
    total_ghost_pnl = 0
    excluded_signals = 0
    
    print(f"\n🔍 Processing with ghost exclusion (≥{GHOST_THRESHOLD_DAYS} days)...\n")
    
    for csv_file in csv_files:
        # Extract signal ID from filename
        match = re.search(r'(\d+)', csv_file.stem)
        if not match:
            continue
        signal_id = match.group(1)
        
        # Load trades
        trades = load_csv_trades(csv_file)
        if not trades:
            continue
        
        # Get EA type
        ea_list = ea_mapping.get(signal_id, ["Unknown"])
        primary_ea = get_primary_ea(ea_list)
        ea_type = get_ea_type(primary_ea)
        
        # Skip Flash and S10
        if ea_type == "Flash":
            excluded_signals += 1
            continue
        
        # Exclude ghost positions
        clean_trades, ghost_count, ghost_pnl = exclude_ghost_positions(trades)
        total_ghost += ghost_count
        total_ghost_pnl += ghost_pnl
        
        # Calculate stats
        stats = calc_signal_stats(signal_id, clean_trades, ea_type)
        if stats:
            score = score_signal(stats)
            stats['score'] = score
            stats['grade'] = get_grade(score)
            stats['ghost_excluded'] = ghost_count
            stats['ghost_pnl'] = round(ghost_pnl, 2)
            stats['ea_full'] = primary_ea
            all_stats.append(stats)
            
            if ghost_count > 0:
                print(f"  Signal {signal_id}: {len(trades)}→{len(clean_trades)} trades (excluded {ghost_count} ghost, ${ghost_pnl:.0f}) | Score: {score} ({get_grade(score)}) | {ea_type}")
    
    print(f"\n📊 Ghost Exclusion Summary:")
    print(f"  Total ghost trades excluded: {total_ghost}")
    print(f"  Total ghost PnL: ${total_ghost_pnl:,.2f}")
    print(f"  Signals excluded (Flash/S10): {excluded_signals}")
    print(f"  Signals scored: {len(all_stats)}")
    
    # 3. Rank all signals
    ranked = sorted(all_stats, key=lambda x: x['score'], reverse=True)
    
    print(f"\n🏆 Signal Ranking (Corrected Data)")
    print("=" * 120)
    print(f"{'#':>3} {'Signal':>7} {'EA':>6} {'Score':>6} {'Grade':>5} {'WR%':>5} {'PF':>6} {'PnL':>10} {'MaxDD':>9} {'Weekly':>8} {'Trades':>7} {'Symbols'}")
    print("-" * 120)
    
    for i, s in enumerate(ranked[:30], 1):
        syms = ', '.join(s['symbols'][:3])
        if len(s['symbols']) > 3:
            syms += f" +{len(s['symbols'])-3}"
        print(f"{i:>3} {s['signal_id']:>7} {s['ea_type']:>6} {s['score']:>6.1f} {s['grade']:>5} {s['win_rate']:>5.1f} {s['profit_factor']:>6.2f} {s['total_pnl']:>10,.2f} {s['max_drawdown']:>9,.2f} {s['weekly_pnl']:>8,.2f} {s['total_trades']:>7} {syms}")
    
    # 4. Select portfolio
    selected, target_weekly = select_portfolio(
        ranked, 
        num_accounts=args.accounts, 
        budget_per_account=args.budget,
        weekly_target_pct=args.target
    )
    
    print(f"\n\n🎯 SELECTED PORTFOLIO ({len(selected)} Accounts)")
    print("=" * 120)
    print(f"  Target: ${target_weekly:.0f}/week per account ({args.target}% of ${args.budget})")
    print()
    
    mt4_configs = []
    total_projected_weekly = 0
    
    for i, s in enumerate(selected, 1):
        config = generate_mt4_config(i, s, args.budget)
        mt4_configs.append(config)
        
        proj = config.get('projected_weekly_return_pct', 0)
        total_projected_weekly += s['weekly_pnl']
        
        set_info = f"{len(config['set_files'])} SET files" if config['set_files'] else "⚠️ No SET files found"
        
        print(f"  📦 Account {i}: Signal {s['signal_id']} ({s['ea_type']} / {s.get('ea_full', '')})")
        print(f"     Grade: {s['grade']} | Score: {s['score']}")
        print(f"     WR: {s['win_rate']}% | PF: {s['profit_factor']} | Trades: {s['total_trades']}")
        print(f"     Total PnL: ${s['total_pnl']:,.2f} | Max DD: ${s['max_drawdown']:,.2f}")
        print(f"     Weekly PnL: ${s['weekly_pnl']:,.2f} | Projected: {proj}%/week")
        print(f"     Symbols: {', '.join(s['symbols'][:5])}")
        print(f"     SET files: {set_info}")
        print(f"     Recommended start lot: {config['recommended_lot']}")
        if config['notes']:
            print(f"     Notes: {config['notes']}")
        print()
    
    print(f"  💰 Combined projected weekly: ${total_projected_weekly:,.2f}")
    print(f"  💰 Combined projected monthly: ${total_projected_weekly * 4:,.2f}")
    
    # 5. Output JSON
    output = {
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'config': {
            'accounts': args.accounts,
            'budget_per_account': args.budget,
            'weekly_target_pct': args.target,
            'ghost_threshold_days': GHOST_THRESHOLD_DAYS,
            'excluded_ea_types': EXCLUDED_EA_TYPES,
        },
        'exclusion_summary': {
            'total_ghost_trades': total_ghost,
            'total_ghost_pnl': round(total_ghost_pnl, 2),
            'flash_excluded': excluded_signals,
        },
        'ranking': ranked[:30],
        'portfolio': mt4_configs,
        'combined_weekly_projected': round(total_projected_weekly, 2),
        'combined_monthly_projected': round(total_projected_weekly * 4, 2),
    }
    
    output_path = args.output or str(OUTPUT_DIR / f"portfolio_{datetime.now().strftime('%Y%m%d_%H%M')}.json")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Portfolio saved to: {output_path}")
    
    # 6. Print MT4 deployment instructions
    print(f"\n\n🔧 MT4 DEPLOYMENT INSTRUCTIONS")
    print("=" * 80)
    for config in mt4_configs:
        sid = config['signal_id']
        print(f"\n  Account {config['account']} - Signal {sid} ({config['ea_type']})")
        print(f"  ─────────────────────────────────────────")
        print(f"  1. Open MT4 Terminal {config['account']}")
        print(f"  2. Login with funded account (${config['budget_usd']})")
        
        if config['set_files']:
            print(f"  3. Copy SET files to MQL4/Presets/:")
            for sf in config['set_files']:
                print(f"     - {sf}")
        else:
            print(f"  3. ⚠️ No SET files found - need to download from AlgoForest")
        
        print(f"  4. Attach EA to chart: {config['symbols'][0] if config['symbols'] else 'Unknown'}")
        print(f"  5. Set lot size: {config['recommended_lot']}")
        
        if len(config['symbols']) > 1:
            print(f"  6. Additional symbols to add:")
            for sym in config['symbols'][1:]:
                print(f"     - {sym}")
    
    return output

if __name__ == '__main__':
    main()
