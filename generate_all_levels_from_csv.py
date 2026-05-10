#!/usr/bin/env python3
"""
Generate detailed comparison report for ALL LEVELS (L1, L2, L3, L4+) from CSV files
"""
import csv
import os
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Output directory
OUTPUT_DIR = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer/output")
OUTPUT_DIR.mkdir(exist_ok=True)

# CSV data directory
CSV_DIR = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer/samples")

# Global TP/SL percentile baselines (lot-based, pre-computed from 58 signals)
# P85 of winning trades' Max Pips per level
GLOBAL_TP_BASELINES = {
    'L1': 48.0, 'L2': 88.5, 'L3': 74.6, 'L4': 109.3,
    'L5': 109.6, 'L6': 128.7, 'L7': 138.6, 'L8': 150.2, 'L9+': 163.4,
}
# P85 of all trades' Max Loss Pips per level
GLOBAL_SL_BASELINES = {
    'L1': 76.4, 'L2': 115.8, 'L3': 97.5, 'L4': 143.3,
    'L5': 129.7, 'L6': 126.7, 'L7': 109.0, 'L8': 92.1, 'L9+': 73.8,
}

# Global percentile baselines (lot-based, pre-computed from 58 signals)
GLOBAL_BASELINES = {
    'global_p25': 1.52,
    'floor': 5.00,
    'min_sample': 30,
    'profit': {
        'L1': {'p50': 3.12, 'p75': 6.5}, 'L2': {'p50': 14.56, 'p75': 36.4},
        'L3': {'p50': 6.32, 'p75': 18.22}, 'L4': {'p50': 19.79, 'p75': 52.01},
        'L5': {'p50': 41.09, 'p75': 83.15}, 'L6': {'p50': 61.74, 'p75': 118.22},
        'L7': {'p50': 118.1, 'p75': 196.84}, 'L8': {'p50': 187.64, 'p75': 310.81},
        'L9+': {'p50': 334.19, 'p75': 600.37},
    },
    'lose': {
        'L1': {'p50': 2.96, 'p75': 6.17}, 'L2': {'p50': 13.83, 'p75': 34.58},
        'L3': {'p50': 6.00, 'p75': 17.31}, 'L4': {'p50': 18.80, 'p75': 49.41},
        'L5': {'p50': 39.04, 'p75': 78.99}, 'L6': {'p50': 58.65, 'p75': 112.31},
        'L7': {'p50': 112.19, 'p75': 187.00}, 'L8': {'p50': 178.26, 'p75': 295.27},
        'L9+': {'p50': 317.48, 'p75': 570.35},
    }
}


def get_effective_percentiles(signal_p50, signal_p75, sig_n, level_key, baseline_type='profit'):
    """
    Blend signal percentiles with global baselines for small samples.
    If n < min_sample (30): P_eff = (n/30)*P_signal + (1-n/30)*P_global
    If signal data unavailable: use global baselines directly.
    
    Returns:
        (effective_p50, effective_p75)
    """
    global_baselines = GLOBAL_BASELINES[baseline_type].get(level_key, GLOBAL_BASELINES['profit']['L1'])
    global_p50 = global_baselines['p50']
    global_p75 = global_baselines['p75']
    floor = GLOBAL_BASELINES['floor']
    min_sample = GLOBAL_BASELINES['min_sample']
    
    if signal_p50 is not None and signal_p75 is not None:
        if sig_n is not None and sig_n < min_sample:
            # Small sample: blend signal and global
            weight = sig_n / min_sample
            eff_p50 = weight * signal_p50 + (1 - weight) * global_p50
            eff_p75 = weight * signal_p75 + (1 - weight) * global_p75
        else:
            eff_p50 = signal_p50
            eff_p75 = signal_p75
        eff_p50 = max(eff_p50, floor)
        eff_p75 = max(eff_p75, eff_p50 + 0.01)
    else:
        # No signal data: use global
        eff_p50 = max(global_p50, floor)
        eff_p75 = max(global_p75, eff_p50 + 0.01)
    
    return eff_p50, eff_p75


def calculate_alpha_capture_score(avg_profit, eff_p50, eff_p75, level_key, baseline_type='profit'):
    """
    Alpha Capture dynamic scoring using pre-computed effective percentiles.
    
    Args:
        avg_profit: Average profit to score
        eff_p50: Effective P50 (already blended for small samples)
        eff_p75: Effective P75 (already blended for small samples)
        level_key: 'L1', 'L2', 'L3', 'L4+'
        baseline_type: 'profit' or 'lose'
    
    Returns:
        dict with score (0-120), effective_p50, effective_p75, details
    """
    
    # Alpha Capture scoring
    if avg_profit <= 0:
        score = 0
        tier = 'below_p50'
    elif avg_profit < eff_p50:
        score = (avg_profit / eff_p50) * 70
        tier = 'below_p50'
    elif avg_profit < eff_p75:
        score = 70 + ((avg_profit - eff_p50) / (eff_p75 - eff_p50)) * 30
        tier = 'p50_to_p75'
    else:
        # Bonus zone: up to 120
        bonus = ((avg_profit - eff_p75) / (eff_p75 - eff_p50)) * 10
        score = 100 + min(bonus, 20)
        tier = 'above_p75'
    
    return {
        'score': round(score, 2),
        'effective_p50': round(eff_p50, 2),
        'effective_p75': round(eff_p75, 2),
        'tier': tier,
        'details': f"P50=${eff_p50:.2f}, P75=${eff_p75:.2f}"
    }


def calculate_dde_score(triggered_trades):
    """
    Drawdown Efficiency (DDE): Measures how 'clean' the triggered entries are.
    
    For each triggered trade: dd_ratio = |max_loss_pips| / profit_pips
    Lower dd_ratio = less initial heat per pip of profit = better quality entry.
    
    DDE score = max(0, 100 - avg(dd_ratio) × 50)
    - dd_ratio=0.5 → 75 (very clean)
    - dd_ratio=1.0 → 50 (1:1 heat)
    - dd_ratio=2.0+ → 0 (excessive drawdown)
    
    Individual dd_ratio capped at 2.0 to prevent outliers.
    
    Args:
        triggered_trades: List of trades that were triggered (profit_pips >= wait_pips)
    
    Returns:
        dict with score (0-100), avg_dd_ratio, details
    """
    if not triggered_trades:
        return {'score': 0, 'avg_dd_ratio': 0, 'details': 'No triggered trades'}
    
    dd_ratios = []
    for trade in triggered_trades:
        max_loss_pips = abs(trade.get('max_loss_pips', 0))
        profit_pips = trade.get('profit_pips', 0)
        
        if profit_pips <= 0:
            profit_pips = abs(trade.get('max_pips', 0))
        
        if profit_pips > 0:
            dd_ratio = min(2.0, max_loss_pips / profit_pips)
        else:
            dd_ratio = 2.0  # No profit pips = worst
        
        dd_ratios.append(dd_ratio)
    
    avg_dd_ratio = sum(dd_ratios) / len(dd_ratios) if dd_ratios else 2.0
    score = max(0, min(100, 100 - avg_dd_ratio * 50))
    
    return {
        'score': round(score, 2),
        'avg_dd_ratio': round(avg_dd_ratio, 4),
        'details': f"Avg DD ratio: {avg_dd_ratio:.2f} (heat per pip)"
    }


def compute_signal_percentiles(trades, level_key, baseline_type='profit'):
    """
    Compute P50 and P75 for a signal's trades in a given level.
    
    Args:
        trades: List of trade dicts
        level_key: 'L1', 'L2', 'L3', 'L4+'
        baseline_type: 'profit' (winning trades) or 'lose' (recovered trades)
    
    Returns:
        (p50, p75, count) or (None, None, 0) if insufficient data
    """
    if baseline_type == 'profit':
        profits = sorted([t['net_profit'] for t in trades if t['net_profit'] > 0])
    else:  # lose/recovered
        profits = sorted([t['net_profit'] for t in trades 
                         if abs(t.get('max_loss_pips', 0)) >= 10 and t['net_profit'] > 0])
    
    n = len(profits)
    if n < 5:  # Minimum 5 trades for meaningful percentiles
        return None, None, n
    
    p50 = profits[n // 2]
    p75 = profits[3 * n // 4]
    
    return p50, p75, n

def analyze_trades_from_csv(csv_file):
    """Analyze trades from a CSV file"""
    trades = []
    
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip rows with missing data
            if not row.get('Symbol') or not row.get('Net Profit'):
                continue
            
            try:
                # Filter non-trade rows (balance, credit, pending orders)
                trade_type = row.get('Type', '').strip().lower()
                if trade_type not in ('buy', 'sell'):
                    continue
                
                trade = {
                    'symbol': row.get('Symbol', '').strip(),
                    'net_profit': float(row.get('Net Profit', 0)),
                    'max_profit': float(row.get('Max Profit', 0)),
                    'max_loss': float(row.get('Max Loss', 0)),
                    'net_pips': float(row.get('Net Pips', 0)),
                    'tp': float(row.get('TP', 0)) if row.get('TP') else 0,
                    'sl': float(row.get('SL', 0)) if row.get('SL') else 0,
                    'volume': float(row.get('Lots', 0)),
                    'type': row.get('Type', ''),
                    'open_price': float(row.get('Open Price', 0)),
                    'close_price': float(row.get('Close Price', 0)),
                    'max_pips': float(row.get('Max Pips', 0)),
                    'max_loss_pips': float(row.get('Max Loss Pips', 0)),
                    'commission': float(row.get('Commission', 0)),
                    'swap': float(row.get('Swap', 0)),
                    'holding_hours': float(row.get('Holding Time (Hours)', 0)) if row.get('Holding Time (Hours)') else 0,
                }
                trades.append(trade)
            except (ValueError, TypeError) as e:
                # Skip malformed rows
                continue
    
    return trades

def load_signal_lot_mapping():
    """Load per-signal lot→level mapping from SET files."""
    mapping_path = Path(__file__).parent / 'signal_lot_mapping.json'
    if mapping_path.exists():
        with open(mapping_path) as f:
            return json.load(f)
    return {}

def assign_lot_level(trade_lot, lot_layers):
    """
    Assign level based on closest lot size match from SET file.
    Returns (level_name, is_autolot) or None if no mapping.
    """
    if not lot_layers:
        return None
    best = min(lot_layers, key=lambda x: abs(x[1] - trade_lot))
    best_level, best_lot = best[0], best[1]
    tolerance = best_lot * 0.25 if best_lot > 0 else 0.01
    is_autolot = abs(trade_lot - best_lot) > tolerance
    if best_level >= 9:
        return ('L9+', is_autolot)
    return (f'L{best_level}', is_autolot)

def infer_levels_from_csv_lots(trades):
    """
    Fallback: infer levels from unique lot values when no SET mapping.
    Smallest lot = L1, ascending.
    """
    unique_lots = sorted(set(round(t['volume'], 4) for t in trades))
    if len(unique_lots) == 1:
        return {unique_lots[0]: 'L1'}
    mapping = {}
    for i, lot in enumerate(unique_lots):
        if i >= 8:
            mapping[lot] = 'L9+'
        else:
            mapping[lot] = f'L{i+1}'
    return mapping

def detect_martin_trades(trades):
    """
    Detect Martin strategy characteristics in trades.
    
    Martin patterns:
    1. Classic Martin: net_profit > 0 but net_pips < 0 (win money, lose pips)
       → Position sizing compensated for direction, classic martingale recovery
    2. Reverse Martin: net_profit < 0 but net_pips > 0 (lose money, win pips)
       → Commission/swap killed the profit, or late-stage addition
    3. Cost Killed: gross profit positive but commission+swap dragged net negative
    
    Returns dict with martin analysis.
    """
    classic_martin = []  # profit > 0, pips < 0
    reverse_martin = []  # profit < 0, pips > 0
    cost_killed = []     # gross positive, net negative due to costs
    
    for trade in trades:
        net_profit = trade.get('net_profit', 0)
        net_pips = trade.get('net_pips', 0)
        commission = trade.get('commission', 0)
        swap = trade.get('swap', 0)
        lots = trade.get('volume', 0)
        
        # Classic Martin: won money but lost pips
        if net_profit > 0 and net_pips < 0:
            classic_martin.append({
                'symbol': trade.get('symbol', ''),
                'type': trade.get('type', ''),
                'lots': lots,
                'net_pips': net_pips,
                'net_profit': net_profit,
                'max_loss': trade.get('max_loss', 0),
                'max_loss_pips': trade.get('max_loss_pips', 0),
                'max_profit': trade.get('max_profit', 0),
                'max_pips': trade.get('max_pips', 0),
                'commission': commission,
                'swap': swap,
                'holding_hours': trade.get('holding_hours', 0),
            })
        
        # Reverse Martin: lost money but won pips
        elif net_profit < 0 and net_pips > 0:
            reverse_martin.append({
                'symbol': trade.get('symbol', ''),
                'type': trade.get('type', ''),
                'lots': lots,
                'net_pips': net_pips,
                'net_profit': net_profit,
                'commission': commission,
                'swap': swap,
                'holding_hours': trade.get('holding_hours', 0),
            })
        
        # Cost Killed: gross positive but costs made it negative
        if net_profit < 0:
            gross_profit = net_profit - commission - swap  # remove cost impact
            if gross_profit > 0:
                cost_killed.append({
                    'symbol': trade.get('symbol', ''),
                    'net_profit': net_profit,
                    'net_pips': net_pips,
                    'commission': commission,
                    'swap': swap,
                    'total_cost': abs(commission) + abs(swap),
                })
    
    total = len(trades)
    
    # Calculate aggregates
    classic_total_profit = sum(t['net_profit'] for t in classic_martin)
    classic_total_pips = sum(t['net_pips'] for t in classic_martin)
    classic_avg_dd = sum(abs(t['max_loss']) for t in classic_martin) / len(classic_martin) if classic_martin else 0
    classic_max_dd = max((abs(t['max_loss']) for t in classic_martin), default=0)
    
    reverse_total_loss = sum(t['net_pips'] for t in reverse_martin)  # pips won but money lost
    reverse_total_cost = sum(abs(t['commission']) + abs(t['swap']) for t in reverse_martin)
    
    cost_killed_total = sum(t['total_cost'] for t in cost_killed)
    
    return {
        'total_trades': total,
        'classic_martin': {
            'count': len(classic_martin),
            'pct': len(classic_martin) / total * 100 if total > 0 else 0,
            'total_profit': classic_total_profit,
            'total_pips_lost': classic_total_pips,
            'avg_max_drawdown': classic_avg_dd,
            'max_drawdown': classic_max_dd,
            'trades': classic_martin[:10],  # Top 10 for display
        },
        'reverse_martin': {
            'count': len(reverse_martin),
            'pct': len(reverse_martin) / total * 100 if total > 0 else 0,
            'total_pips_won': reverse_total_loss,
            'total_cost': reverse_total_cost,
            'trades': reverse_martin[:10],
        },
        'cost_killed': {
            'count': len(cost_killed),
            'pct': len(cost_killed) / total * 100 if total > 0 else 0,
            'total_cost': cost_killed_total,
            'trades': cost_killed[:10],
        },
        'has_martin': len(classic_martin) > 0 or len(reverse_martin) > 0,
        'martin_severity': 'HIGH' if len(classic_martin) / total > 0.02 else 'MEDIUM' if len(classic_martin) / total > 0.005 else 'LOW' if len(classic_martin) > 0 else 'NONE',
    }


def analyze_copy_on_profit(trades, wait_pips_levels, level_key='L1'):
    """
    Analyze Copy on Profit strategy with Alpha Capture dynamic scoring.
    
    New scoring:
    - Component 1 (40%): Trigger Rate
    - Component 2 (40%): Alpha Capture Profit Score (dynamic baseline)
    - Component 3 (20%): Drawdown Efficiency (DDE)
    
    Args:
        trades: List of trades
        wait_pips_levels: List of wait pips to test [5, 10, 15, 20]
        level_key: Level name for dynamic baseline lookup
    """
    results = {}
    
    # Compute signal's own percentiles for this level (with small-sample blending)
    sig_p50, sig_p75, sig_n = compute_signal_percentiles(trades, level_key, 'profit')
    eff_p50, eff_p75 = get_effective_percentiles(sig_p50, sig_p75, sig_n, level_key, 'profit')
    
    for wait_pips in wait_pips_levels:
        triggered_count = 0
        total_profit_after_trigger = 0
        triggered_trades_list = []
        
        for trade in trades:
            net_profit = trade.get('net_profit', 0)
            max_profit = trade.get('max_profit', 0)
            
            if net_profit <= 0:
                continue
            
            # Use Max Pips if available, otherwise estimate from Max Profit
            max_pips = trade.get('max_pips', 0)
            if max_pips > 0:
                profit_pips = abs(max_pips)
            elif max_profit > 0:
                # Estimate: Max Profit / (Volume * 10)
                volume = trade.get('volume', 0.01)
                profit_pips = max_profit / (volume * 10)
            else:
                profit_pips = 0
            
            if profit_pips >= wait_pips:
                triggered_count += 1
                total_profit_after_trigger += net_profit
                triggered_trades_list.append(trade)
        
        total_profit_trades = sum(1 for t in trades if t.get('net_profit', 0) > 0)
        
        if total_profit_trades > 0:
            trigger_rate = triggered_count / total_profit_trades
        else:
            trigger_rate = 0
            
        if triggered_count > 0:
            avg_profit_after = total_profit_after_trigger / triggered_count
        else:
            avg_profit_after = 0
        
        # Component 1: Trigger Rate Score (40%)
        trigger_score = min(trigger_rate * 100, 100)
        
        # Component 2: Alpha Capture Profit Score (40%)
        alpha = calculate_alpha_capture_score(avg_profit_after, eff_p50, eff_p75, level_key, 'profit')
        profit_score = alpha['score']
        
        # Component 3: Drawdown Efficiency Score (20%)
        dde = calculate_dde_score(triggered_trades_list)
        dde_score = dde['score']
        
        # Weighted score
        weighted_score = (trigger_score * 0.4) + (profit_score * 0.4) + (dde_score * 0.2)
        
        # Rating
        if weighted_score >= 80:
            rating = "⭐⭐⭐⭐"
            rating_class = "rating-excellent"
        elif weighted_score >= 60:
            rating = "⭐⭐⭐"
            rating_class = "rating-good"
        elif weighted_score >= 40:
            rating = "⭐⭐"
            rating_class = "rating-average"
        else:
            rating = "⭐"
            rating_class = "rating-poor"
        
        results[wait_pips] = {
            'total_trades': total_profit_trades,
            'triggered_count': triggered_count,
            'trigger_rate': trigger_rate,
            'avg_profit_after': avg_profit_after,
            'weighted_score': round(weighted_score, 2),
            'rating': rating,
            'rating_class': rating_class,
            'score_details': {
                'trigger_rate': f"{trigger_rate:.2%} → {trigger_score:.1f} × 40% = {trigger_score * 0.4:.1f}",
                'alpha_profit': f"${avg_profit_after:.2f} vs {alpha['details']} → {profit_score:.1f} × 40% = {profit_score * 0.4:.1f}",
                'dde': f"DD ratio: {dde['avg_dd_ratio']:.2f} → {dde_score:.1f} × 20% = {dde_score * 0.2:.1f}",
                'total': f"{weighted_score:.1f}"
            }
        }
    
    return results

def analyze_copy_on_lose(trades, wait_pips_levels, level_key='L1'):
    """
    Analyze Copy on Lose strategy with Alpha Capture dynamic scoring.
    
    New scoring:
    - Component 1 (50%): Recovery Rate = recovered / triggered
    - Component 2 (50%): Alpha Capture Profit Score (dynamic baseline from recovered trades)
    - trigger_rate: DISPLAY ONLY, not scored (independent metric)
    
    Args:
        trades: List of trades
        wait_pips_levels: List of wait pips to test [10, 15, 20, 25]
        level_key: Level name for dynamic baseline lookup
    """
    results = {}
    
    # Compute signal's own percentiles from recovered trades (with small-sample blending)
    sig_p50, sig_p75, sig_n = compute_signal_percentiles(trades, level_key, 'lose')
    eff_p50, eff_p75 = get_effective_percentiles(sig_p50, sig_p75, sig_n, level_key, 'lose')
    
    for wait_pips in wait_pips_levels:
        triggered_count = 0
        recovered_count = 0
        total_profit_after_recover = 0
        
        for trade in trades:
            net_profit = trade.get('net_profit', 0)
            max_loss_pips = trade.get('max_loss_pips', 0)
            
            if abs(max_loss_pips) >= wait_pips:
                triggered_count += 1
                
                if net_profit > 0:
                    recovered_count += 1
                    total_profit_after_recover += net_profit
        
        total_trades = len(trades)
        
        # Trigger rate (display only, not scored)
        if total_trades > 0:
            trigger_rate = triggered_count / total_trades
        else:
            trigger_rate = 0
        
        if triggered_count > 0:
            recovery_rate = recovered_count / triggered_count
            avg_profit_after = total_profit_after_recover / recovered_count if recovered_count > 0 else 0
        else:
            recovery_rate = 0
            avg_profit_after = 0
        
        # Component 1: Recovery Rate Score (50%)
        recovery_score = recovery_rate * 100
        
        # Component 2: Alpha Capture Profit Score (50%)
        alpha = calculate_alpha_capture_score(avg_profit_after, eff_p50, eff_p75, level_key, 'lose')
        profit_score = alpha['score']
        
        # Weighted score: recovery 50%, profit 50%
        weighted_score = (recovery_score * 0.5) + (profit_score * 0.5)
        
        # Rating
        if weighted_score >= 80:
            rating = "⭐⭐⭐⭐"
            rating_class = "rating-excellent"
        elif weighted_score >= 60:
            rating = "⭐⭐⭐"
            rating_class = "rating-good"
        elif weighted_score >= 40:
            rating = "⭐⭐"
            rating_class = "rating-average"
        else:
            rating = "⭐"
            rating_class = "rating-poor"
        
        results[wait_pips] = {
            'total_trades': total_trades,
            'triggered_count': triggered_count,
            'trigger_rate': trigger_rate,
            'recovered_count': recovered_count,
            'recovery_rate': recovery_rate,
            'avg_profit_after': avg_profit_after,
            'weighted_score': round(weighted_score, 2),
            'rating': rating,
            'rating_class': rating_class,
            'score_details': {
                'recovery_rate': f"{recovery_rate:.2%} → {recovery_score:.1f} × 50% = {recovery_score * 0.5:.1f}",
                'alpha_profit': f"${avg_profit_after:.2f} vs {alpha['details']} → {profit_score:.1f} × 50% = {profit_score * 0.5:.1f}",
                'trigger_rate_info': f"{trigger_rate:.2%} (display only, not scored)",
                'total': f"{weighted_score:.1f}"
            }
        }
    
    return results

def calculate_tpsl(level_trades, level_key):
    """
    Calculate TP/SL suggestions for a specific level using P85 percentile.
    
    TP = P85 of winning trades' Max Pips (85% of winners reached this level)
    SL = P85 of all trades' Max Loss Pips (85% of trades had drawdown ≤ this)
    
    Small sample fallback (n < 100): blend with global baselines.
    """
    if not level_trades:
        return {'tp': None, 'sl': None, 'tp_sample': 0, 'sl_sample': 0,
                'tp_source': 'none', 'sl_source': 'none', 'rr_ratio': None, 'rr_flag': ''}
    
    all_trades = level_trades
    winning_trades = [t for t in level_trades if t.get('net_profit', 0) > 0]
    
    n_all = len(all_trades)
    n_win = len(winning_trades)
    
    global_tp = GLOBAL_TP_BASELINES.get(level_key, 53.0)
    global_sl = GLOBAL_SL_BASELINES.get(level_key, 44.7)
    
    # TP calculation (from winning trades' Max Pips)
    if n_win >= 100:
        max_pips_sorted = sorted([abs(t.get('max_pips', 0)) for t in winning_trades])
        tp = max_pips_sorted[int(len(max_pips_sorted) * 0.85)]
        tp_source = f'P85(n={n_win})'
    elif n_win >= 30:
        max_pips_sorted = sorted([abs(t.get('max_pips', 0)) for t in winning_trades])
        tp_sig = max_pips_sorted[int(len(max_pips_sorted) * 0.85)]
        weight = (n_win - 30) / 70  # 0 at n=30, 1 at n=100
        tp = weight * tp_sig + (1 - weight) * global_tp
        tp_source = f'blend(n={n_win},w={weight:.2f})'
    else:
        tp = global_tp
        tp_source = f'global(n={n_win})'
    
    # SL calculation (from all trades' Max Loss Pips)
    if n_all >= 100:
        max_loss_sorted = sorted([abs(t.get('max_loss_pips', 0)) for t in all_trades])
        sl = max_loss_sorted[int(len(max_loss_sorted) * 0.85)]
        sl_source = f'P85(n={n_all})'
    elif n_all >= 30:
        max_loss_sorted = sorted([abs(t.get('max_loss_pips', 0)) for t in all_trades])
        sl_sig = max_loss_sorted[int(len(max_loss_sorted) * 0.85)]
        weight = (n_all - 30) / 70
        sl = weight * sl_sig + (1 - weight) * global_sl
        sl_source = f'blend(n={n_all},w={weight:.2f})'
    else:
        sl = global_sl
        sl_source = f'global(n={n_all})'
    
    # Risk-Reward ratio
    rr_ratio = tp / sl if sl > 0 else None
    if rr_ratio is not None:
        if rr_ratio >= 1.5:
            rr_flag = '🟢'
        elif rr_ratio >= 1.0:
            rr_flag = '✅'
        elif rr_ratio >= 0.7:
            rr_flag = '⚠️'
        else:
            rr_flag = '🚩'
    else:
        rr_flag = ''
    
    return {
        'tp': round(tp, 1),
        'sl': round(sl, 1),
        'tp_sample': n_win,
        'sl_sample': n_all,
        'tp_source': tp_source,
        'sl_source': sl_source,
        'rr_ratio': round(rr_ratio, 2) if rr_ratio else None,
        'rr_flag': rr_flag
    }


def analyze_by_levels(trades, level_ranges):
    """
    Analyze trades by profit levels
    
    Args:
        trades: List of trades
        level_ranges: Dict of level ranges
    """
    level_results = {}
    
    for level_name, (min_profit, max_profit) in level_ranges.items():
        level_trades = [t for t in trades if min_profit <= t.get('net_profit', 0) < max_profit]
        
        # Calculate basic stats
        total_trades = len(level_trades)
        if total_trades == 0:
            level_results[level_name] = {
                'stats': {
                    'count': 0,
                    'min_profit': min_profit,
                    'max_profit': max_profit
                },
                'copy_on_profit': {},
                'copy_on_lose': {}
            }
            continue
        
        win_trades = sum(1 for t in level_trades if t.get('net_profit', 0) > 0)
        win_rate = win_trades / total_trades if total_trades > 0 else 0
        total_profit = sum(t.get('net_profit', 0) for t in level_trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        avg_tp = sum(t.get('tp', 0) for t in level_trades) / total_trades if total_trades > 0 else 0
        avg_sl = sum(t.get('sl', 0) for t in level_trades) / total_trades if total_trades > 0 else 0
        
        stats = {
            'count': total_trades,
            'min_profit': min_profit,
            'max_profit': max_profit,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'avg_tp': avg_tp,
            'avg_sl': avg_sl
        }
        
        # Copy on Profit analysis
        profit_results = analyze_copy_on_profit(level_trades, [5, 10, 15, 20], level_name)
        
        # Copy on Lose analysis
        lose_results = analyze_copy_on_lose(level_trades, [10, 15, 20, 25], level_name)
        
        # TP/SL suggestion
        tpsl = calculate_tpsl(level_trades, level_name)
        
        level_results[level_name] = {
            'stats': stats,
            'copy_on_profit': profit_results,
            'copy_on_lose': lose_results,
            'tpsl': tpsl
        }
    
    return level_results

def analyze_by_levels_lotbased(trades, achieved_levels):
    """
    Analyze trades by lot-based levels.
    achieved_levels: list of level names that have trades (e.g. ['L1', 'L2', 'L3', 'L9+'])
    """
    level_results = {}

    for level_name in achieved_levels:
        level_trades = [t for t in trades if t.get('lot_level') == level_name]

        total_trades = len(level_trades)
        if total_trades == 0:
            level_results[level_name] = {
                'stats': {'count': 0, 'min_profit': 0, 'max_profit': 0},
                'copy_on_profit': {},
                'copy_on_lose': {}
            }
            continue

        win_trades = sum(1 for t in level_trades if t.get('net_profit', 0) > 0)
        win_rate = win_trades / total_trades if total_trades > 0 else 0
        total_profit = sum(t.get('net_profit', 0) for t in level_trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        avg_tp = sum(t.get('tp', 0) for t in level_trades) / total_trades if total_trades > 0 else 0
        avg_sl = sum(t.get('sl', 0) for t in level_trades) / total_trades if total_trades > 0 else 0

        stats = {
            'count': total_trades,
            'min_profit': min((t.get('net_profit', 0) for t in level_trades), default=0),
            'max_profit': max((t.get('net_profit', 0) for t in level_trades), default=0),
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'avg_tp': avg_tp,
            'avg_sl': avg_sl
        }

        # Copy on Profit analysis
        profit_results = analyze_copy_on_profit(level_trades, [5, 10, 15, 20], level_name)

        # Copy on Lose analysis
        lose_results = analyze_copy_on_lose(level_trades, [10, 15, 20, 25], level_name)

        # TP/SL suggestion
        tpsl = calculate_tpsl(level_trades, level_name)

        level_results[level_name] = {
            'stats': stats,
            'copy_on_profit': profit_results,
            'copy_on_lose': lose_results,
            'tpsl': tpsl
        }

    return level_results

# Windows .set files directory
SET_FILES_DIR = Path("/mnt/c/Users/Alvin/Downloads/Set File From Signal Page")

def parse_set_filename(filename):
    """Parse .set filename to extract EA name, version, symbol, timeframe, direction, date"""
    # Format: (signal_id)EA_NameVERSION_SYMBOL_TF_Dir_YYYY-MM-DD_HH-MM-SS.set
    # or: (signal_id)EA_NameVERSIONSYMBOL_TF_Dir_YYYY-MM-DD_HH-MM-SS.set
    name = filename.replace('.set', '')
    # Remove signal_id prefix like (22200)
    if name.startswith('('):
        closing = name.find(')')
        if closing > 0:
            name = name[closing+1:]
    
    # Extract date (last YYYY-MM-DD_HH-MM-SS)
    import re
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})_(\d{2}-\d{2}-\d{2})$', name)
    date_str = date_match.group(1) if date_match else ''
    if date_match:
        name = name[:date_match.start()].rstrip('_')
    
    # Parse remaining: EANameVersion_SYMBOL_TF_Direction
    parts = name.rsplit('_', 2)  # Split from right: [..., TF, Direction]
    direction = parts[-1] if len(parts) >= 3 else ''
    tf = parts[-2] if len(parts) >= 3 else ''
    
    # TF to human-readable
    tf_map = {'M5': 'M5', 'M15': 'M15', 'M30': 'M30', 'H1': 'H1', 'H4': 'H4', 
              'D1': 'D1', '60': 'H1', '30': 'M30', '5': 'M5', '240': 'H4', '1440': 'D1'}
    tf_display = tf_map.get(tf, tf)
    
    # Extract symbol and EA name from remaining
    remaining = parts[0] if len(parts) >= 3 else name
    # Symbol is typically 6 chars near the end (before TF)
    symbol_match = re.search(r'([A-Z]{6})$', remaining)
    symbol = symbol_match.group(1) if symbol_match else ''
    ea_full = remaining[:-6] if symbol else remaining
    
    return {
        'ea_full': ea_full,
        'symbol': symbol,
        'timeframe': tf_display,
        'direction': direction,
        'date': date_str
    }


def read_set_params(set_path):
    """Read .set file and return dict of key=value pairs"""
    params = {}
    try:
        with open(set_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, _, value = line.partition('=')
                    params[key.strip()] = value.strip()
    except Exception:
        pass
    return params


def get_ea_family(ea_name):
    """Determine EA family from name"""
    ea_lower = ea_name.lower()
    if 'dragon' in ea_lower or 'dw' in ea_lower:
        return 'DW'
    elif 'sma' in ea_lower:
        return 'SMA'
    elif 'mkd' in ea_lower:
        return 'MKD'
    elif 's10' in ea_lower:
        return 'S10'
    elif 'flash' in ea_lower:
        return 'Flash'
    elif 'gem' in ea_lower:
        return 'GEM'
    return 'UNK'


def detect_martin_lv(params):
    """Detect Martin levels from .set parameters"""
    ea_name = params.get('EA_NAME', '')
    ea_lower = ea_name.lower()
    
    # Dragon Wave: LotMul-based
    if 'dragon' in ea_lower:
        return 8  # DW default 8 layers
    
    # Count pipstep/lotsize params (SMA, MKD style)
    import re
    max_pipstep = 0
    max_lotsize = 0
    for key in params:
        m = re.match(r'pipstep(\d+)', key, re.IGNORECASE)
        if m and float(params[key]) > 0:
            max_pipstep = max(max_pipstep, int(m.group(1)))
        m = re.match(r'lotsize(\d+)', key, re.IGNORECASE)
        if m and float(params[key]) > 0:
            max_lotsize = max(max_lotsize, int(m.group(1)))
    
    if max_pipstep > 0 or max_lotsize > 0:
        return max(max_pipstep, max_lotsize)
    
    # S10: MaxBuyCount
    for key in ['MaxBuyCount', 'MaxSellCount']:
        if key in params:
            val = int(float(params.get(key, '0')))
            if val > 0:
                return val  # flat-bet, but still counts as levels
    
    return 0


def compute_worthiness(trades):
    """
    Compute worthiness metrics (R-Multiple, Kelly, Safety Margin) for a list of trades.
    Returns dict with per-level + overall metrics.
    Uses lot-based levels if available on trades.
    """
    if not trades:
        return None
    
    # Determine levels from trade data
    achieved = sorted(set(t.get('lot_level', 'L1') for t in trades),
                      key=lambda x: (99 if x == 'L9+' else int(x[1:])))
    
    results = {}
    
    for level_name in achieved + ['Overall']:
        if level_name == 'Overall':
            level_trades = trades
        else:
            level_trades = [t for t in trades if t.get('lot_level') == level_name]
        
        n = len(level_trades)
        if n < 5:
            results[level_name] = None
            continue
        
        wins = [t for t in level_trades if t.get('net_profit', 0) > 0]
        losses = [t for t in level_trades if t.get('net_profit', 0) <= 0]
        
        w = len(wins) / n  # win rate
        avg_win = sum(t['net_profit'] for t in wins) / len(wins) if wins else 0
        avg_loss = abs(sum(t['net_profit'] for t in losses) / len(losses)) if losses else 0
        
        r_ratio = avg_win / avg_loss if avg_loss > 0 else 999.0  # profit/loss ratio
        
        # Expectancy (R-Multiple): E = (W * R) - (1 - W)
        expectancy = (w * r_ratio) - (1 - w)
        
        # Kelly: K = W - ((1-W) / R)
        if r_ratio > 0:
            kelly = w - ((1 - w) / r_ratio)
        else:
            kelly = 0
        kelly_quarter = max(0, kelly * 0.25) * 100  # 1/4 Kelly as %
        
        # Breakeven win rate: 1 / (1 + R)
        be_wr = 1 / (1 + r_ratio) if r_ratio > 0 else 1.0
        safety_margin = w - be_wr  # actual WR minus breakeven WR
        
        # Safety margin grade
        if safety_margin > 0.15:
            safety_grade = '🟢'
            safety_label = '穩健'
        elif safety_margin > 0.05:
            safety_grade = '🟡'
            safety_label = '一般'
        else:
            safety_grade = '🔴'
            safety_label = '危險'
        
        # Total profit
        total_profit = sum(t['net_profit'] for t in level_trades)
        
        results[level_name] = {
            'trades': n,
            'wins': len(wins),
            'win_rate': round(w * 100, 1),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'rr_ratio': round(r_ratio, 2),
            'expectancy': round(expectancy, 3),
            'kelly': round(kelly * 100, 1),
            'kelly_quarter': round(kelly_quarter, 1),
            'breakeven_wr': round(be_wr * 100, 1),
            'safety_margin': round(safety_margin * 100, 1),
            'safety_grade': safety_grade,
            'safety_label': safety_label,
            'total_profit': round(total_profit, 2),
        }
    
    return results


def compute_martin_level_analysis(trades):
    """
    Compute per-level Martin depth analysis for a list of trades.
    Returns dict with per-level Martin metrics.
    Uses lot-based levels if available on trades.
    """
    if not trades:
        return None
    
    # Determine levels from trade data
    achieved = sorted(set(t.get('lot_level', 'L1') for t in trades),
                      key=lambda x: (99 if x == 'L9+' else int(x[1:])))
    
    total = len(trades)
    classic_martin_trades = [t for t in trades if t.get('net_profit', 0) > 0 and t.get('net_pips', 0) < 0]
    total_profit = sum(t.get('net_profit', 0) for t in trades if t.get('net_profit', 0) > 0)
    martin_profit = sum(t['net_profit'] for t in classic_martin_trades)
    
    # Martin profit dependency
    martin_dependency = (martin_profit / total_profit * 100) if total_profit > 0 else 0
    
    # Martin win rate (among martin trades)
    martin_wins = len([t for t in classic_martin_trades if t['net_profit'] > 0])
    martin_wr = martin_wins / len(classic_martin_trades) * 100 if classic_martin_trades else 0
    
    results = {
        'overall_dependency': round(martin_dependency, 1),
        'overall_martin_count': len(classic_martin_trades),
        'overall_martin_wr': round(martin_wr, 1),
        'overall_total_profit': round(total_profit, 2),
        'overall_martin_profit': round(martin_profit, 2),
        'levels': {}
    }
    
    for level_name in achieved:
        level_trades = [t for t in trades if t.get('lot_level') == level_name]
        level_martin = [t for t in level_trades if t.get('net_profit', 0) > 0 and t.get('net_pips', 0) < 0]
        
        n = len(level_trades)
        n_martin = len(level_martin)
        
        trigger_rate = n_martin / n * 100 if n > 0 else 0
        avg_depth = sum(abs(t.get('max_loss_pips', 0)) for t in level_martin) / n_martin if n_martin > 0 else 0
        max_depth = max((abs(t.get('max_loss_pips', 0)) for t in level_martin), default=0)
        avg_dd = sum(abs(t.get('max_loss', 0)) for t in level_martin) / n_martin if n_martin > 0 else 0
        max_dd = max((abs(t.get('max_loss', 0)) for t in level_martin), default=0)
        
        # Severity color
        if trigger_rate > 10:
            trigger_color = '#c62828'  # red
        elif trigger_rate > 3:
            trigger_color = '#f57c00'  # orange
        else:
            trigger_color = '#2e7d32'  # green
        
        results['levels'][level_name] = {
            'trades': n,
            'martin_count': n_martin,
            'trigger_rate': round(trigger_rate, 1),
            'avg_depth_pips': round(avg_depth, 1),
            'max_depth_pips': round(max_depth, 1),
            'avg_dd': round(avg_dd, 2),
            'max_dd': round(max_dd, 2),
            'trigger_color': trigger_color,
        }
    
    return results


def compute_copy_trade_suggestion(trades, worthiness, martin_analysis, levels_data):
    """
    Generate Copy Trade suggestion based on worthiness + martin analysis.
    Returns dict with recommendation details.
    """
    if not trades or not worthiness:
        return None
    
    overall = worthiness.get('Overall')
    if not overall:
        return None
    
    expectancy = overall['expectancy']
    win_rate = overall['win_rate']
    rr_ratio = overall['rr_ratio']
    
    # Martin dependency
    martin_dep = martin_analysis['overall_dependency'] if martin_analysis else 0
    martin_count = martin_analysis['overall_martin_count'] if martin_analysis else 0
    
    # Find best CoP score across all levels
    best_cop_score = 0
    best_cop_wait = 0
    best_cop_level = ''
    for lv in levels_data:
        lv_data = levels_data[lv]
        cop = lv_data.get('copy_on_profit', {})
        for wp, r in cop.items():
            if r.get('weighted_score', 0) > best_cop_score:
                best_cop_score = r['weighted_score']
                best_cop_wait = wp
                best_cop_level = lv
    
    # Find best CoL score
    best_col_score = 0
    best_col_wait = 0
    best_col_level = ''
    for lv in levels_data:
        lv_data = levels_data[lv]
        col = lv_data.get('copy_on_lose', {})
        for wp, r in col.items():
            if r.get('weighted_score', 0) > best_col_score:
                best_col_score = r['weighted_score']
                best_col_wait = wp
                best_col_level = lv
    
    # Get suggested TP/SL from best level
    best_tpsl = levels_data.get(best_cop_level or 'L1', {}).get('tpsl', {})
    tp_val = best_tpsl.get('tp', 'N/A')
    sl_val = best_tpsl.get('sl', 'N/A')
    rr_val = best_tpsl.get('rr_ratio', 'N/A')
    rr_flag = best_tpsl.get('rr_flag', '')
    
    # Decision logic
    recommendation = ''
    strategy = ''
    wait_pips = 0
    confidence = '🔴 低'
    confidence_class = 'low'
    reason = ''
    
    # Rule 1: Not recommended
    if expectancy < 0.1 or martin_dep > 70:
        recommendation = '❌ 不建議 Copy'
        strategy = 'N/A'
        reason_parts = []
        if expectancy < 0.1:
            reason_parts.append(f'期望值過低 ({expectancy:.3f}R)')
        if martin_dep > 70:
            reason_parts.append(f'馬丁盈利依賴度過高 ({martin_dep:.1f}%)')
        reason = '、'.join(reason_parts)
        confidence = '🔴 低'
        confidence_class = 'low'
    
    # Rule 2: CoP - signal-driven, low martin dependency
    elif martin_dep < 30 and win_rate > 60 and best_cop_score > 0:
        recommendation = '✅ 建議 CoP (Copy on Profit)'
        strategy = 'CoP'
        wait_pips = best_cop_wait
        reason = f'馬丁依賴度低 ({martin_dep:.1f}%)、勝率 {win_rate:.1f}%、信號質素高'
        
        # Confidence
        if expectancy > 0.5 and martin_dep < 20 and win_rate > 80:
            confidence = '🟢 高'
            confidence_class = 'high'
        else:
            confidence = '🟡 中'
            confidence_class = 'medium'
    
    # Rule 3: CoL - martin-reliant, use recovery strategy
    elif martin_dep >= 30 and best_col_score > 0:
        recommendation = '⚠️ 建議 CoL (Copy on Lose)'
        strategy = 'CoL'
        wait_pips = best_col_wait
        reason = f'馬丁依賴度 {martin_dep:.1f}%，適合等待回撤後跟單博反彈'
        
        if expectancy > 0.3 and martin_dep < 50:
            confidence = '🟡 中'
            confidence_class = 'medium'
        else:
            confidence = '🔴 低'
            confidence_class = 'low'
    
    # Rule 4: Default - try CoP if available
    elif best_cop_score > 0:
        recommendation = '⚠️ 可嘗試 CoP (Copy on Profit)'
        strategy = 'CoP'
        wait_pips = best_cop_wait
        reason = f'期望值 {expectancy:.3f}R、勝率 {win_rate:.1f}%，數據勉強支持 CoP'
        confidence = '🟡 中'
        confidence_class = 'medium'
    
    # Rule 5: No good option
    else:
        recommendation = '❌ 不建議 Copy'
        strategy = 'N/A'
        reason = f'缺乏有效嘅 CoP/CoL 觸發數據'
        confidence = '🔴 低'
        confidence_class = 'low'
    
    # Format TP/SL display
    tp_display = f'{tp_val:.1f} pips' if isinstance(tp_val, (int, float)) else str(tp_val)
    sl_display = f'{sl_val:.1f} pips' if isinstance(sl_val, (int, float)) else str(sl_val)
    rr_display = f'{rr_flag} {rr_val:.2f}' if isinstance(rr_val, (int, float)) else str(rr_val)
    
    return {
        'recommendation': recommendation,
        'strategy': strategy,
        'confidence': confidence,
        'confidence_class': confidence_class,
        'wait_pips': wait_pips,
        'tp': tp_display,
        'sl': sl_display,
        'rr_display': rr_display,
        'best_cop_score': round(best_cop_score, 1),
        'best_col_score': round(best_col_score, 1),
        'best_cop_level': best_cop_level,
        'best_col_level': best_col_level,
        'reason': reason,
        'expectancy': expectancy,
        'win_rate': win_rate,
        'rr_ratio': rr_ratio,
        'martin_dep': martin_dep,
    }


def build_signal_info_card(signal_id):
    """Build Signal Info Card HTML from .set files in Windows directory"""
    signal_dir = SET_FILES_DIR / str(signal_id)
    if not signal_dir.exists():
        return ''
    
    set_files = sorted(signal_dir.glob('*.set'))
    if not set_files:
        return ''
    
    # Parse all .set files
    all_sets = []
    for sf in set_files:
        meta = parse_set_filename(sf.name)
        params = read_set_params(sf)
        all_sets.append({**meta, 'params': params, 'path': sf})
    
    # Determine EA info from first set
    first = all_sets[0]
    ea_name = first['params'].get('EA_NAME', 'Unknown')
    ea_version = first['params'].get('EA_VERSION', '')
    ea_family = get_ea_family(ea_name)
    martin_lv = detect_martin_lv(first['params'])
    
    # Collect unique dates and symbols
    dates = sorted(set(s['date'] for s in all_sets if s['date']))
    symbols = sorted(set(s['symbol'] for s in all_sets if s['symbol']))
    
    # EA Family CSS
    family_css = {
        'DW': ('#4a148c', '#ce93d8'), 'SMA': ('#1b5e20', '#a5d6a7'),
        'MKD': ('#e65100', '#ffcc80'), 'S10': ('#0d47a1', '#90caf9'),
        'Flash': ('#880e4f', '#f48fb1'), 'GEM': ('#37474f', '#b0bec5'),
    }
    bg_color, text_color = family_css.get(ea_family, ('#555', '#fff'))
    
    # Build info card HTML
    html_parts = []
    html_parts.append(f'''
    <div class="info-card" style="margin-bottom: 20px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, {bg_color}, {bg_color}dd); color: {text_color}; padding: 10px 15px;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
                <div>
                    <span style="font-size: 14px; font-weight: bold;">📡 Signal #{signal_id}</span>
                    <span style="background: rgba(255,255,255,0.2); padding: 2px 8px; border-radius: 4px; font-size: 10px; margin-left: 8px;">{ea_family}</span>
                </div>
                <div style="font-size: 11px; text-align: right;">
                    <div>{ea_name}</div>
                    {f'<div style="font-size:10px;opacity:0.8">Version: {ea_version}</div>' if ea_version else ''}
                </div>
            </div>
        </div>
        <div style="padding: 10px 15px; background: #fafafa;">
            <table style="width: 100%; font-size: 11px; border-collapse: collapse;">
                <tr>
                    <td style="padding: 3px 8px; color: #666; width: 100px;">EA Family</td>
                    <td style="padding: 3px 8px; font-weight: bold;">{ea_family} ({ea_name})</td>
                    <td style="padding: 3px 8px; color: #666; width: 100px;">Martin LV</td>
                    <td style="padding: 3px 8px; font-weight: bold;">{martin_lv}</td>
                </tr>
                <tr>
                    <td style="padding: 3px 8px; color: #666;">貨幣對數量</td>
                    <td style="padding: 3px 8px;">{len(symbols)} 個 ({', '.join(symbols[:6])}{', ...' if len(symbols) > 6 else ''})</td>
                    <td style="padding: 3px 8px; color: #666;">.set 檔案</td>
                    <td style="padding: 3px 8px;">{len(set_files)} 個（{len(dates)} 個日期版本）</td>
                </tr>
            </table>
        </div>
    ''')
    
    # .set version diff (only if multiple dates)
    if len(dates) > 1:
        html_parts.append('''
        <div style="padding: 8px 15px; border-top: 1px solid #eee;">
            <div style="font-size: 11px; font-weight: bold; margin-bottom: 6px; color: #555;">📋 .set 版本差異（只顯示有改動嘅參數）</div>
            <table style="width: 100%; font-size: 10px; border-collapse: collapse;">
        ''')
        
        # Compare sets across dates (same symbol)
        # Pick a reference symbol (first symbol with sets across multiple dates)
        for ref_symbol in symbols[:3]:  # Check first 3 symbols
            symbol_sets = {}  # date -> params
            for s in all_sets:
                if s['symbol'] == ref_symbol and s['date']:
                    symbol_sets[s['date']] = s['params']
            
            if len(symbol_sets) < 2:
                continue
            
            # Find differing keys
            all_keys = set()
            for p in symbol_sets.values():
                all_keys.update(p.keys())
            
            # Skip boring keys
            skip_keys = {'EA_NAME', 'EA_VERSION', 'EA_SYMBOL', 'EA_PERIOD'}
            diff_keys = []
            for k in sorted(all_keys):
                if k in skip_keys:
                    continue
                values = set()
                for p in symbol_sets.values():
                    values.add(p.get(k, ''))
                if len(values) > 1:
                    diff_keys.append(k)
            
            if not diff_keys:
                continue
            
            html_parts.append(f'<tr><td colspan="{len(dates)+1}" style="padding: 4px 0 2px; font-weight: bold; color: #1976d2;">{ref_symbol}</td></tr>')
            html_parts.append(f'<tr style="background: #e3f2fd;"><th style="padding: 2px 6px; text-align: left;">參數</th>')
            for d in dates:
                html_parts.append(f'<th style="padding: 2px 6px;">{d}</th>')
            html_parts.append('</tr>')
            
            for k in diff_keys[:15]:  # Show max 15 diffs
                html_parts.append(f'<tr><td style="padding: 2px 6px; color: #666;">{k}</td>')
                for d in dates:
                    val = symbol_sets.get(d, {}).get(k, '—')
                    html_parts.append(f'<td style="padding: 2px 6px;">{val}</td>')
                html_parts.append('</tr>')
            
            if len(diff_keys) > 15:
                html_parts.append(f'<tr><td colspan="{len(dates)+1}" style="padding: 2px 6px; color: #999;">... 還有 {len(diff_keys)-15} 個差異參數</td></tr>')
            
            break  # Only show first symbol with diffs
        
        html_parts.append('</table></div>')
    
    # Core params summary
    core_params = first['params']
    core_keys_map = {
        'Lots': '初始手數', 'LotMul': '加倉倍數', 'lotExp': '加倉指數',
        'EntryLot': '入市手數', 'lotSize': '手數',
        'PipStepMul': '網格倍數', 'VirtualTP': '虛擬 TP', 'VirtualSL': '虛擬 SL',
        'UseVirtualTP': '使用虛擬TP', 'UseVirtualSL': '使用虛擬SL',
        'TradeCloseOnlyOnDD': 'DD 平倉', 'DailyStopLoss': '日止損',
        'MaxSpread': '最大點差', 'MaxSlippage': '最大滑點',
        'ForceBE': '強制保本', 'StopTrading': '停止交易',
        'TakeProfit': 'TP', 'TrailingStart': '追蹤啟動', 'TrailingDist': '追蹤距離',
        'MaxBuyCount': '最大買單', 'MaxSellCount': '最大賣單',
        'autoLotSize': '自動手數',
        'OpenType': '開倉類型', 'TradeType': '交易類型',
    }
    
    found_cores = [(core_keys_map.get(k, k), core_params.get(k, '')) 
                    for k in core_keys_map if k in core_params]
    
    if found_cores:
        html_parts.append('''
        <div style="padding: 8px 15px; border-top: 1px solid #eee;">
            <div style="font-size: 11px; font-weight: bold; margin-bottom: 6px; color: #555;">⚙️ 核心參數</div>
            <div style="display: flex; flex-wrap: wrap; gap: 4px;">
        ''')
        for label, val in found_cores:
            html_parts.append(f'<span style="background: #e8eaf6; padding: 2px 6px; border-radius: 3px; font-size: 10px;">{label}: <b>{val}</b></span>')
        html_parts.append('</div></div>')
    
    html_parts.append('</div>')
    return '\n'.join(html_parts)


def generate_html_report(csv_file, all_currency_data, level_ranges=None):
    """Generate HTML report for all currencies and levels"""
    
    # Determine all achieved levels across all currencies
    all_achieved_levels = set()
    for currency, data in all_currency_data.items():
        for lv_name in data['levels']:
            if data['levels'][lv_name]['stats']['count'] > 0:
                all_achieved_levels.add(lv_name)
    achieved_levels = sorted(all_achieved_levels, key=lambda x: (99 if x == 'L9+' else int(x[1:])))
    
    # Extract signal ID from various CSV naming patterns
    stem = Path(csv_file).stem
    if 'forex-forest-signals-page-' in stem:
        signal_id = stem.replace('forex-forest-signals-page-', '')
    elif stem.startswith('signal_') and stem.endswith('_trades'):
        signal_id = stem.replace('signal_', '').replace('_trades', '')
    else:
        signal_id = stem
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Build currency list
    currency_pairs = sorted(all_currency_data.keys())
    
    # Build HTML
    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Copy Trade Analysis - Signal #{signal_id} - All Levels</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 11px;
            line-height: 1.4;
            color: #333;
            background: #f5f5f5;
            padding: 10px;
        }}
        
        .container {{
            max-width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            padding: 15px;
        }}
        
        h1 {{
            font-size: 16px;
            margin-bottom: 5px;
            color: #1976d2;
        }}
        
        .subtitle {{
            font-size: 10px;
            color: #666;
            margin-bottom: 15px;
        }}
        
        .currency-section {{
            margin-bottom: 20px;
            border: 1px solid #ddd;
            border-radius: 6px;
            overflow: hidden;
        }}
        
        .currency-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 8px 12px;
            font-weight: bold;
            font-size: 12px;
        }}
        
        .currency-stats {{
            padding: 8px 12px;
            background: #f8f9fa;
            border-bottom: 1px solid #ddd;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
            gap: 8px;
            font-size: 10px;
        }}
        
        .stat-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 9px;
        }}
        
        .stat-value {{
            font-weight: bold;
            font-size: 11px;
            color: #333;
        }}
        
        .level-section {{
            margin: 8px;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .level-header {{
            background: #e3f2fd;
            padding: 6px 10px;
            font-weight: bold;
            font-size: 11px;
            color: #1976d2;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .strategy-section {{
            margin: 6px;
        }}
        
        .strategy-header {{
            background: #f5f5f5;
            padding: 5px 8px;
            font-weight: bold;
            font-size: 10px;
            color: #333;
            border-left: 3px solid #1976d2;
            margin-bottom: 4px;
        }}
        
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 10px;
            background: white;
            border: 1px solid #e0e0e0;
            table-layout: auto;
        }}
        
        .table-wrap {{
            width: 100%;
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }}
        
        .comparison-table th {{
            background: #e8eaf6;
            padding: 4px 6px;
            text-align: left;
            font-weight: bold;
            border-bottom: 1px solid #e0e0e0;
            white-space: nowrap;
        }}
        
        .comparison-table td {{
            padding: 3px 6px;
            border-bottom: 1px solid #f0f0f0;
            white-space: nowrap;
        }}
        
        .comparison-table tr:last-child td {{
            border-bottom: none;
        }}
        
        .score-cell {{
            font-weight: bold;
            text-align: center;
        }}
        
        .rating-excellent {{
            color: #2e7d32;
            background: #e8f5e9;
        }}
        
        .rating-good {{
            color: #f57c00;
            background: #fff3e0;
        }}
        
        .rating-average {{
            color: #f9a825;
            background: #fffde7;
        }}
        
        .rating-poor {{
            color: #c62828;
            background: #ffebee;
        }}
        
        .score-details {{
            font-size: 8px;
            color: #666;
            margin-top: 2px;
        }}
        
        /* Tooltip for score details */
        .info-icon {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 16px;
            height: 16px;
            border-radius: 50%;
            background: #e0e0e0;
            color: #666;
            font-size: 10px;
            font-style: italic;
            cursor: help;
            position: relative;
        }}
        .info-icon .tip {{
            display: none;
            position: absolute;
            left: 20px;
            top: -10px;
            background: #333;
            color: #fff;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 9px;
            white-space: nowrap;
            z-index: 100;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            line-height: 1.5;
        }}
        .info-icon:hover .tip {{ display: block; }}
        
        /* Sortable table headers */
        th.sortable {{ cursor: pointer; user-select: none; }}
        th.sortable:hover {{ background: #c5cae9; }}
        th.sortable::after {{ content: ' ⇕'; font-size: 9px; opacity: 0.5; }}
        th.sort-asc::after {{ content: ' ↑'; opacity: 1; color: #1976d2; }}
        th.sort-desc::after {{ content: ' ↓'; opacity: 1; color: #1976d2; }}
        
        /* Formula tooltip on table headers */
        th.formula-tip {{ cursor: help; position: relative; }}
        th.formula-tip .formula {{ display: none; position: absolute; left: 50%; top: 100%; transform: translateX(-50%); background: #263238; color: #e0f7fa; padding: 8px 12px; border-radius: 6px; font-size: 10px; font-weight: normal; white-space: nowrap; z-index: 200; box-shadow: 0 4px 12px rgba(0,0,0,0.3); line-height: 1.6; margin-top: 2px; }}
        th.formula-tip .formula::before {{ content: ''; position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%); border: 5px solid transparent; border-bottom-color: #263238; }}
        th.formula-tip:hover .formula {{ display: block; }}
        th.formula-tip:hover {{ background: #c5cae9; }}
        
        .best-score {{
            background: #e8f5e9;
            font-weight: bold;
        }}
        
        .footer {{
            margin-top: 20px;
            padding-top: 10px;
            border-top: 1px solid #ddd;
            font-size: 9px;
            color: #666;
            text-align: center;
        }}
        
        @media print {{
            body {{
                font-size: 9px;
            }}
            .currency-section {{
                page-break-inside: avoid;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>📊 Copy Trade Analysis - Signal #{signal_id}</h1>
        <div class="subtitle">
            Complete Analysis for ALL LEVELS (L1, L2, L3, L4+)<br>
            Generated: {current_time}
        </div>
        
        {build_signal_info_card(signal_id)}
        
        <div class="summary-section" style="margin-bottom: 20px;">
            <h2 style="font-size: 13px; margin-bottom: 10px; color: #1976d2;">📋 Analysis Summary</h2>
            <div class="table-wrap"><table class="comparison-table">
                <thead>
                    <tr>
                        <th>Currency</th>"""
    for lv in achieved_levels:
        html += f"""
                        <th>{lv}</th>"""
    html += """
                        <th>Total</th>
                        <th>Win%</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Build summary
    for currency in currency_pairs:
        data = all_currency_data[currency]
        
        total_trades = sum(data['levels'].get(lv, {}).get('stats', {}).get('count', 0) for lv in achieved_levels)
        
        if total_trades == 0:
            continue
        
        win_rate = data['stats']['win_rate']
        win_rate_class = 'rating-excellent' if win_rate >= 60 else 'rating-good' if win_rate >= 50 else 'rating-average' if win_rate >= 40 else 'rating-poor'
        
        html += f"""
                    <tr>
                        <td><strong>{currency}</strong></td>"""
        for lv in achieved_levels:
            count = data['levels'].get(lv, {}).get('stats', {}).get('count', 0)
            html += f"""
                        <td>{count}</td>"""
        html += f"""
                        <td>{total_trades}</td>
                        <td class="score-cell {win_rate_class}">{win_rate:.2%}</td>
                    </tr>"""
    
    html += """
                </tbody>
            </table>
            </div>
        </div>
"""
    
    # Build detailed sections for each currency
    for currency in currency_pairs:
        data = all_currency_data[currency]
        stats = data['stats']
        levels = data['levels']
        
        total_trades = sum(levels.get(lv, {}).get('stats', {}).get('count', 0) for lv in achieved_levels)
        
        if total_trades == 0:
            continue
        
        html += f"""
        <div class="currency-section">
            <div class="currency-header">{currency}</div>
            
            <div class="currency-stats">
                <div class="stat-item">
                    <span class="stat-label">Total Trades</span>
                    <span class="stat-value">{stats['total_trades']}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Win Rate</span>
                    <span class="stat-value">{stats['win_rate']:.2%}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Total Profit</span>
                    <span class="stat-value">${stats['total_profit']:.2f}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Avg Profit</span>
                    <span class="stat-value">${stats['avg_profit']:.2f}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Avg TP</span>
                    <span class="stat-value">${stats['avg_tp']:.2f}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Avg SL</span>
                    <span class="stat-value">${stats['avg_sl']:.2f}</span>
                </div>
            </div>
"""
        
        # === NEW: Compute worthiness, martin level analysis, copy trade suggestion ===
        raw_trades = data.get('raw_trades', [])
        worthiness = compute_worthiness(raw_trades) if raw_trades else None
        martin_lvl = compute_martin_level_analysis(raw_trades) if raw_trades else None
        copy_suggestion = compute_copy_trade_suggestion(raw_trades, worthiness, martin_lvl, levels) if raw_trades else None
        
        # === NEW MODULE 1: Copy Trade Suggestion ===
        if copy_suggestion:
            cs = copy_suggestion
            conf_bg = {'high': '#e8f5e9', 'medium': '#fff8e1', 'low': '#ffebee'}
            conf_border = {'high': '#4CAF50', 'medium': '#FFC107', 'low': '#FF5722'}
            html += f"""
            <div style="margin: 8px; border: 2px solid {conf_border[cs['confidence_class']]}; border-radius: 6px; overflow: hidden;">
                <div style="background: {conf_bg[cs['confidence_class']]}; padding: 8px 12px; font-weight: bold; font-size: 12px; border-bottom: 1px solid #e0e0e0;">
                    🎯 Copy Trade 建議
                </div>
                <div style="padding: 10px 12px; font-size: 11px; line-height: 1.8;">
                    <div><strong>建議：</strong>{cs['recommendation']}</div>
                    <div><strong>信心度：</strong>{cs['confidence']}</div>
"""
            if cs['strategy'] != 'N/A':
                html += f"""
                    <div><strong>策略：</strong>{cs['strategy']} · Wait <strong>{cs['wait_pips']} pips</strong></div>
                    <div><strong>建議 TP/SL：</strong>TP = {cs['tp']} / SL = {cs['sl']} (R:R = {cs['rr_display']})</div>
"""
            html += f"""
                    <div><strong>理由：</strong>{cs['reason']}</div>
                    <div style="margin-top: 4px; padding-top: 4px; border-top: 1px dashed #ddd; font-size: 9px; color: #666;"><strong>背景數據：</strong>期望值 {cs['expectancy']:.3f}R · 勝率 {cs['win_rate']:.1f}% · 盈虧比 {cs['rr_ratio']:.2f} · 馬丁依賴 {cs['martin_dep']:.1f}% · 最佳 CoP {cs['best_cop_score']:.1f} · 最佳 CoL {cs['best_col_score']:.1f}</div>
                </div>
            </div>
"""
        
        # === NEW MODULE 2: Worthiness Analysis ===
        if worthiness:
            html += """
            <div style="margin: 8px; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden;">
                <div style="background: #e3f2fd; padding: 6px 10px; font-weight: bold; font-size: 11px; color: #1976d2; border-bottom: 1px solid #e0e0e0;
                    border-left: 3px solid #1976d2;">
                    📈 值博率分析 (Expectancy + Kelly + Safety Margin)
                </div>
                <table class="comparison-table" style="font-size: 10px;">
                    <thead>
                        <tr style="background: #e8eaf6;">
                            <th>層級</th><th>#</th><th>勝率</th><th>R</th><th>E</th>
                            <th>Kelly</th><th>¼Kelly</th><th>BE</th><th>安全</th><th>等級</th>
                        </tr>
                    </thead>
                    <tbody>
"""
            for lv_name in ['L1', 'L2', 'L3', 'L4+', 'Overall']:
                lv = worthiness.get(lv_name)
                if not lv:
                    continue
                row_bg = 'background: #f0f4ff;' if lv_name == 'Overall' else ''
                # Color for expectancy
                e_color = '#2e7d32' if lv['expectancy'] > 0 else '#c62828'
                html += f"""
                        <tr style="{row_bg}">
                            <td><strong>{lv_name}</strong></td>
                            <td>{lv['trades']}</td>
                            <td>{lv['win_rate']:.1f}%</td>
                            <td>{lv['rr_ratio']:.2f}</td>
                            <td style="color: {e_color}; font-weight: bold;">{lv['expectancy']:.3f}R</td>
                            <td>{lv['kelly']:.1f}%</td>
                            <td>{lv['kelly_quarter']:.1f}%</td>
                            <td>{lv['breakeven_wr']:.1f}%</td>
                            <td>{lv['safety_grade']} {lv['safety_margin']:.1f}%</td>
                            <td style="font-size: 9px;">{lv['safety_label']}</td>
                        </tr>
"""
            html += """
                    </tbody>
                </table>
"""
            # Safety margin explanation
            ov = worthiness.get('Overall')
            if ov:
                html += f"""
                <div style="padding: 6px 10px; font-size: 9px; color: #666; border-top: 1px solid #e0e0e0;">
                    <strong>值博率解讀：</strong>期望值 {ov['expectancy']:.3f}R（每冒 1R 風險期望回報 {ov['expectancy']:.3f}R）。即使勝率跌至 {ov['breakeven_wr']:.1f}% 或盈虧比跌至 {(1-ov['win_rate']/100)/(ov['win_rate']/100):.2f} 仍可打和。安全邊際 {ov['safety_grade']} {ov['safety_margin']:.1f}%（{ov['safety_label']}）。
                </div>
"""
            html += "</div>\n"
        
        # === NEW MODULE 3: Martin Level Depth Analysis ===
        if martin_lvl:
            ml = martin_lvl
            html += f"""
            <div style="margin: 8px; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden;">
                <div style="background: #fff3e0; padding: 6px 10px; font-weight: bold; font-size: 11px; color: #e65100; border-bottom: 1px solid #e0e0e0;
                    border-left: 3px solid #ff9800;">
                    🎰 馬丁層級深度分析
                </div>
                <div style="padding: 6px 10px; font-size: 10px; border-bottom: 1px solid #eee;">
                    <strong>馬丁盈利依賴度：</strong><span style="color: {'#c62828' if ml['overall_dependency'] > 50 else '#f57c00' if ml['overall_dependency'] > 20 else '#2e7d32'}; font-weight: bold;">{ml['overall_dependency']:.1f}%</span>
                    &nbsp;|&nbsp; 馬丁交易數：{ml['overall_martin_count']} 筆
                    &nbsp;|&nbsp; 總盈利 ${ml['overall_total_profit']:.2f} 中 ${ml['overall_martin_profit']:.2f} 來自馬丁
                </div>
                <table class="comparison-table" style="font-size: 10px;">
                    <thead>
                        <tr style="background: #fff8e1;">
                            <th>層級</th><th>#</th><th>馬丁數</th><th>觸發</th><th>均深(pips)</th>
                            <th>最深(pips)</th><th>均DD($)</th><th>最DD($)</th>
                        </tr>
                    </thead>
                    <tbody>
"""
            for lv_name in ['L1', 'L2', 'L3', 'L4+']:
                lv_data = ml['levels'].get(lv_name)
                if not lv_data or lv_data['trades'] == 0:
                    continue
                html += f"""
                        <tr>
                            <td><strong>{lv_name}</strong></td>
                            <td>{lv_data['trades']}</td>
                            <td>{lv_data['martin_count']}</td>
                            <td style="color: {lv_data['trigger_color']}; font-weight: bold;">{lv_data['trigger_rate']:.1f}%</td>
                            <td>{lv_data['avg_depth_pips']:.1f}</td>
                            <td>{lv_data['max_depth_pips']:.1f}</td>
                            <td>${lv_data['avg_dd']:.2f}</td>
                            <td>${lv_data['max_dd']:.2f}</td>
                        </tr>
"""
            html += """
                    </tbody>
                </table>
                <div style="padding: 6px 10px; font-size: 9px; color: #666; border-top: 1px solid #e0e0e0;">
                    <strong>觸發率</strong> = Classic Martin 數 / 該層總交易數。紅色 >10%，橙色 >3%，綠色 ≤3%。<br>
                    <strong>平均深度</strong> = 馬丁交易的平均 Max Loss Pips，反映觸發後要扛幾深。
                </div>
            </div>
"""
        
        # Martin Detection Section
        martin = stats.get('martin', None)
        if martin and martin['has_martin']:
            severity = martin['martin_severity']
            severity_color = {'HIGH': '#c62828', 'MEDIUM': '#f57c00', 'LOW': '#2e7d32', 'NONE': '#666'}
            severity_bg = {'HIGH': '#ffebee', 'MEDIUM': '#fff3e0', 'LOW': '#e8f5e9', 'NONE': '#f5f5f5'}
            severity_label = {'HIGH': '🔴 HIGH', 'MEDIUM': '🟡 MEDIUM', 'LOW': '🟢 LOW', 'NONE': '⚪ NONE'}
            
            html += f"""
            <div class="martin-section" style="margin: 6px 8px; border: 1px solid #e0e0e0; border-radius: 4px; overflow: hidden;">
                <div style="background: {severity_bg[severity]}; padding: 6px 10px; font-weight: bold; font-size: 11px; color: {severity_color[severity]}; border-bottom: 1px solid #e0e0e0;">
                    🎰 Martin Strategy Detection — {severity_label[severity]}
                </div>
                <div style="padding: 8px 10px; font-size: 10px;">
"""
            
            # Classic Martin
            cm = martin['classic_martin']
            if cm['count'] > 0:
                html += f"""
                    <div style="margin-bottom: 8px; padding: 6px; background: #fff8e1; border-left: 3px solid #ff9800; border-radius: 2px;">
                        <strong>⚠️ Classic Martin (Profit > 0, Pips < 0): {cm['count']} trades ({cm['pct']:.1f}%)</strong><br>
                        <span style="color: #2e7d32;">💰 Total Profit: ${cm['total_profit']:,.2f}</span> | 
                        <span style="color: #c62828;">📉 Total Pips Lost: {cm['total_pips_lost']:,.1f}</span> | 
                        <span style="color: #c62828;">📊 Avg Max DD: ${cm['avg_max_drawdown']:,.2f}</span> | 
                        <span style="color: #c62828;">💥 Worst DD: ${cm['max_drawdown']:,.2f}</span>
"""
                if cm['trades']:
                    html += f"""
                        <table style="width: 100%; margin-top: 4px; font-size: 9px; border-collapse: collapse;">
                            <tr style="background: #f5f5f5;"><th style="padding: 2px 4px; text-align: left;">Symbol</th><th>Type</th><th>Lots</th><th>Pips</th><th>Profit</th><th>Max DD</th><th>Max DD Pips</th><th>Hold hrs</th></tr>
"""
                    for t in cm['trades'][:5]:
                        html += f"""
                            <tr><td style="padding: 2px 4px;">{t['symbol']}</td><td>{t['type']}</td><td>{t['lots']:.2f}</td><td style="color: #c62828;">{t['net_pips']:.1f}</td><td style="color: #2e7d32;">${t['net_profit']:.2f}</td><td style="color: #c62828;">${t['max_loss']:.2f}</td><td>{t['max_loss_pips']:.1f}</td><td>{t['holding_hours']:.0f}</td></tr>
"""
                    html += "</table>"
                html += "</div>"
            
            # Reverse Martin
            rm = martin['reverse_martin']
            if rm['count'] > 0:
                html += f"""
                    <div style="margin-bottom: 8px; padding: 6px; background: #fce4ec; border-left: 3px solid #e91e63; border-radius: 2px;">
                        <strong>🔄 Reverse Martin (Profit < 0, Pips > 0): {rm['count']} trades ({rm['pct']:.1f}%)</strong><br>
                        <span style="color: #2e7d32;">📈 Pips Won: {rm['total_pips_won']:,.1f}</span> | 
                        <span style="color: #c62828;">💸 Cost Eaten: ${rm['total_cost']:,.2f}</span>
                        <br><span style="font-size: 8px; color: #666;">Commission + Swap ate all profit. Direction was right, but holding costs killed it.</span>
"""
                if rm['trades']:
                    html += f"""
                        <table style="width: 100%; margin-top: 4px; font-size: 9px; border-collapse: collapse;">
                            <tr style="background: #f5f5f5;"><th style="padding: 2px 4px; text-align: left;">Symbol</th><th>Type</th><th>Lots</th><th>Pips</th><th>Profit</th><th>Cost</th></tr>
"""
                    for t in rm['trades'][:5]:
                        cost = abs(t['commission']) + abs(t['swap'])
                        html += f"""
                            <tr><td style="padding: 2px 4px;">{t['symbol']}</td><td>{t['type']}</td><td>{t['lots']:.2f}</td><td style="color: #2e7d32;">{t['net_pips']:.1f}</td><td style="color: #c62828;">${t['net_profit']:.2f}</td><td style="color: #c62828;">${cost:.2f}</td></tr>
"""
                    html += "</table>"
                html += "</div>"
            
            # Cost Killed
            ck = martin['cost_killed']
            if ck['count'] > 0:
                html += f"""
                    <div style="margin-bottom: 8px; padding: 6px; background: #e8eaf6; border-left: 3px solid #3f51b5; border-radius: 2px;">
                        <strong>💀 Cost Killed (Gross Profit > 0, Net < 0): {ck['count']} trades ({ck['pct']:.1f}%)</strong><br>
                        <span style="color: #c62828;">💸 Total Cost: ${ck['total_cost']:,.2f}</span>
                        <br><span style="font-size: 8px; color: #666;">Trade direction was correct, but commission + swap exceeded the gross profit.</span>
"""
                if ck['trades']:
                    html += f"""
                        <table style="width: 100%; margin-top: 4px; font-size: 9px; border-collapse: collapse;">
                            <tr style="background: #f5f5f5;"><th style="padding: 2px 4px; text-align: left;">Symbol</th><th>Pips</th><th>Net Profit</th><th>Commission</th><th>Swap</th><th>Total Cost</th></tr>
"""
                    for t in ck['trades'][:5]:
                        html += f"""
                            <tr><td style="padding: 2px 4px;">{t['symbol']}</td><td>{t['net_pips']:.1f}</td><td style="color: #c62828;">${t['net_profit']:.2f}</td><td>${t['commission']:.2f}</td><td>${t['swap']:.2f}</td><td style="color: #c62828;">${t['total_cost']:.2f}</td></tr>
"""
                    html += "</table>"
                html += "</div>"
            
            html += """
                </div>
            </div>
"""
        
        # Build each level (only levels that exist for this currency)
        for level_name in achieved_levels:
            if level_name not in levels:
                continue
            level_data = levels[level_name]
            level_stats = level_data['stats']
            
            if level_stats['count'] == 0:
                continue
            
            html += f"""
            <div class="level-section">
                <div class="level-header">
                    {level_name} (${level_stats['min_profit']:.0f} - ${level_stats['max_profit']:.0f}) - {level_stats['count']} trades
                </div>"""
            
            # TP/SL suggestion display
            tpsl = level_data.get('tpsl', {})
            if tpsl and tpsl.get('tp') is not None:
                tp_val = tpsl['tp']
                sl_val = tpsl['sl']
                rr_val = tpsl.get('rr_ratio', None)
                rr_flag = tpsl.get('rr_flag', '')
                tp_src = tpsl.get('tp_source', '')
                sl_src = tpsl.get('sl_source', '')
                rr_display = f"{rr_val:.2f}" if rr_val else 'N/A'
                html += f"""
                <div style="margin: 6px 8px; padding: 8px 10px; background: #e8f5e9; border: 1px solid #c8e6c9; border-radius: 4px; font-size: 10px;">
                    <strong>📍 Suggested TP/SL:</strong>
                    &nbsp; TP = <span style="color: #2e7d32; font-weight: bold;">{tp_val:.1f} pips</span> <span style="color: #888; font-size: 8px;">({tp_src})</span>
                    &nbsp;|&nbsp; SL = <span style="color: #c62828; font-weight: bold;">{sl_val:.1f} pips</span> <span style="color: #888; font-size: 8px;">({sl_src})</span>
                    &nbsp;|&nbsp; R:R = <span style="font-weight: bold;">{rr_flag} {rr_display}</span>
                </div>
"""
            
            # Copy on Profit table
            profit_results = level_data['copy_on_profit']
            html += """
                <div class="strategy-section">
                    <div class="strategy-header">🚀 Copy on Profit (Trigger Rate 40% + Alpha Capture Profit 40% + DDE 20%)</div>
                    <div class="table-wrap"><table class="comparison-table">
                        <thead>
                            <tr>
                                <th>Wait</th>
                                <th class="formula-tip">Trig%<span class="formula">公式：trigger_rate × 100 × 0.4</span></th>
                                <th>Avg</th>
                                <th class="formula-tip">DDE<span class="formula">公式：max(0, 100 - 50 × avg_dd_ratio) × 0.2</span></th>
                                <th class="formula-tip">Score<span class="formula">公式：Trigger Rate + Alpha Capture + DDE<br>＝ (trigger_rate × 100 × 0.4)<br>＋ (動態百分位評分 × 0.4)<br>＋ (max(0, 100 - 50 × avg_dd_ratio) × 0.2)</span></th>
                                <th>Rating</th>
                                <th>ℹ️</th>
                            </tr>
                        </thead>
                        <tbody>
"""
            
            for wait_pips in [5, 10, 15, 20]:
                result = profit_results[wait_pips]
                is_best = result['weighted_score'] == max(profit_results[wp]['weighted_score'] for wp in profit_results)
                row_class = 'best-score' if is_best else ''
                dde_info = result['score_details']['dde']
                
                html += f"""
                        <tr class="{row_class}">
                            <td>{wait_pips} pips</td>
                            <td>{result['trigger_rate']:.2%}</td>
                            <td>${result['avg_profit_after']:.2f}</td>
                            <td>{dde_info.split('→')[0].strip()}</td>
                            <td class="score-cell {result['rating_class']}">{result['weighted_score']:.1f}</td>
                            <td class="score-cell {result['rating_class']}">{result['rating']}</td>
                            <td class="score-details"><span class="info-icon">i<span class="tip">{result['score_details']['trigger_rate']}<br>{result['score_details']['alpha_profit']}<br>{result['score_details']['dde']}<br><strong>{result['score_details']['total']}</strong></span></span></td>
                        </tr>
"""
            
            html += """
                        </tbody>
                    </table>
                    </div>
                </div>
"""
            
            # Copy on Lose table
            lose_results = level_data['copy_on_lose']
            html += """
                <div class="strategy-section">
                    <div class="strategy-header">🛡️ Copy on Lose (Recovery Rate 50% + Alpha Capture Profit 50% | Trigger Rate: display only)</div>
                    <div class="table-wrap"><table class="comparison-table">
                        <thead>
                            <tr>
                                <th>Wait</th>
                                <th class="formula-tip">Trig%*<span class="formula">顯示用途，不計入評分<br>公式：trigger_rate × 100</span></th>
                                <th class="formula-tip">Recov%<span class="formula">公式：recovery_rate × 100 × 0.5</span></th>
                                <th>Avg</th>
                                <th class="formula-tip">Score<span class="formula">公式：Recovery Rate + Alpha Capture<br>＝ (recovery_rate × 100 × 0.5)<br>＋ (動態百分位評分 × 0.5)</span></th>
                                <th>Rating</th>
                                <th>ℹ️</th>
                            </tr>
                        </thead>
                        <tbody>
"""
            
            for wait_pips in [10, 15, 20, 25]:
                result = lose_results[wait_pips]
                is_best = result['weighted_score'] == max(lose_results[wp]['weighted_score'] for wp in lose_results)
                row_class = 'best-score' if is_best else ''
                
                html += f"""
                        <tr class="{row_class}">
                            <td>{wait_pips} pips</td>
                            <td>{result['trigger_rate']:.2%}*</td>
                            <td>{result['recovery_rate']:.2%}</td>
                            <td>${result['avg_profit_after']:.2f}</td>
                            <td class="score-cell {result['rating_class']}">{result['weighted_score']:.1f}</td>
                            <td class="score-cell {result['rating_class']}">{result['rating']}</td>
                            <td class="score-details"><span class="info-icon">i<span class="tip">{result['score_details']['recovery_rate']}<br>{result['score_details']['alpha_profit']}<br>{result['score_details']['trigger_rate_info']}<br><strong>{result['score_details']['total']}</strong></span></span></td>
                        </tr>
"""
            
            html += """
                        </tbody>
                    </table>
                    </div>
                </div>
"""
            
            html += """
            </div>
"""
        
        html += """
        </div>
"""
    
    html += f"""
        <div class="footer">
            Copy Trade Analysis - Signal #{signal_id}<br>
            Generated by Trade Strategy Analyzer v3 (DDE + TP/SL)<br>
            <span style="font-size: 8px;">
            Scoring: CoP Trigger 40% + Alpha Capture 40% + DDE 20% | CoL Recovery 50% + Alpha Capture 50%<br>
            TP = P85 of winning trades' Max Pips | SL = P85 of all trades' Max Loss Pips | R:R = TP/SL
            </span>
        </div>
    </div>
<script>
document.addEventListener('DOMContentLoaded', function() {{
    document.querySelectorAll('.comparison-table').forEach(function(table) {{
        var headers = table.querySelectorAll('thead th');
        headers.forEach(function(th, colIdx) {{
            if (th.textContent.trim() === '\u2139\uFE0F') return;
            th.classList.add('sortable');
            th.addEventListener('click', function() {{
                var tbody = table.querySelector('tbody');
                if (!tbody) return;
                var rows = Array.from(tbody.querySelectorAll('tr'));
                var asc = th.classList.contains('sort-asc');
                headers.forEach(function(h) {{ h.classList.remove('sort-asc','sort-desc'); }});
                if (asc) {{ th.classList.add('sort-desc'); }} else {{ th.classList.add('sort-asc'); }}
                rows.sort(function(a, b) {{
                    var aVal = a.children[colIdx] ? a.children[colIdx].textContent.trim() : '';
                    var bVal = b.children[colIdx] ? b.children[colIdx].textContent.trim() : '';
                    var aNum = parseFloat(aVal.replace(/[^0-9.-]/g, ''));
                    var bNum = parseFloat(bVal.replace(/[^0-9.-]/g, ''));
                    if (!isNaN(aNum) && !isNaN(bNum)) {{ return asc ? aNum - bNum : bNum - aNum; }}
                    return asc ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
                }});
                rows.forEach(function(r) {{ tbody.appendChild(r); }});
            }});
        }});
    }});
}});
</script>
</body>
</html>
"""
    
    return html

def main():
    import sys
    import re as _re
    
    print("🚀 Starting lot-based level analysis from CSV...")
    
    # Get CSV file path from command line or find automatically
    if len(sys.argv) > 1:
        csv_file = Path(sys.argv[1])
    else:
        csv_files = list(CSV_DIR.glob("signal_*.csv"))
        if not csv_files:
            print(f"❌ No CSV files found in {CSV_DIR}")
            return
        csv_file = csv_files[0]
    
    print(f"📄 Processing CSV file: {csv_file}")
    
    # Extract signal ID
    stem = csv_file.stem
    if 'forex-forest-signals-page-' in stem:
        signal_id = stem.replace('forex-forest-signals-page-', '')
    elif stem.startswith('signal_') and stem.endswith('_trades'):
        signal_id = stem.replace('signal_', '').replace('_trades', '')
    else:
        signal_id = stem
    
    # Analyze trades from CSV
    trades = analyze_trades_from_csv(csv_file)
    print(f"📊 Total trades: {len(trades)}")
    
    # === LOT-BASED LEVEL DETECTION ===
    global_lot_mapping = load_signal_lot_mapping()
    signal_lot_layers = None
    is_autolot_signal = False
    if signal_id in global_lot_mapping:
        signal_lot_layers = global_lot_mapping[signal_id].get('lot_layers', [])
        # Check AutoLot: unique lots >> SET layers
        unique_lots = len(set(round(t['volume'], 4) for t in trades))
        set_layers = len(signal_lot_layers)
        if unique_lots > set_layers * 2 and set_layers > 1:
            is_autolot_signal = True
    
    # Assign lot-based levels to each trade
    if signal_lot_layers:
        for t in trades:
            result = assign_lot_level(t['volume'], signal_lot_layers)
            if result:
                t['lot_level'] = result[0]
                t['is_autolot'] = result[1] or is_autolot_signal
            else:
                t['lot_level'] = 'L1'
                t['is_autolot'] = is_autolot_signal
        print(f"   Level detection: SET-based ({len(signal_lot_layers)} layers){' [AUTOLOT]' if is_autolot_signal else ''}")
    else:
        lot_to_level = infer_levels_from_csv_lots(trades)
        for t in trades:
            lot_key = round(t['volume'], 4)
            t['lot_level'] = lot_to_level.get(lot_key, 'L1')
            t['is_autolot'] = False
        print(f"   Level detection: CSV-inferred ({len(lot_to_level)} unique lots)")
    
    # Group trades by currency
    currency_data = defaultdict(list)
    for trade in trades:
        symbol = trade.get('symbol', '')
        if symbol:
            currency_data[symbol].append(trade)
    
    print(f"📈 Found {len(currency_data)} currency pairs")
    
    # Analyze each currency by lot-based levels
    all_currency_data = {}
    
    for currency, currency_trades in currency_data.items():
        # Get achieved levels for this currency
        ccy_achieved = sorted(set(t.get('lot_level', 'L1') for t in currency_trades),
                             key=lambda x: (99 if x == 'L9+' else int(x[1:])))
        print(f"  🔄 Processing {currency}... ({len(currency_trades)} trades, levels: {','.join(ccy_achieved)})")
        
        # Calculate basic stats
        total_trades = len(currency_trades)
        win_trades = sum(1 for t in currency_trades if t.get('net_profit', 0) > 0)
        win_rate = win_trades / total_trades if total_trades > 0 else 0
        total_profit = sum(t.get('net_profit', 0) for t in currency_trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        avg_tp = sum(t.get('tp', 0) for t in currency_trades) / total_trades if total_trades > 0 else 0
        avg_sl = sum(t.get('sl', 0) for t in currency_trades) / total_trades if total_trades > 0 else 0
        
        # Detect Martin patterns
        martin = detect_martin_trades(currency_trades)
        
        stats = {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'avg_tp': avg_tp,
            'avg_sl': avg_sl,
            'martin': martin,
        }
        
        # Analyze by lot-based levels
        levels = analyze_by_levels_lotbased(currency_trades, ccy_achieved)
        
        all_currency_data[currency] = {
            'stats': stats,
            'levels': levels,
            'raw_trades': currency_trades
        }
    
    print(f"✅ Processed {len(all_currency_data)} currency pairs")
    
    # Generate HTML report
    print("📝 Generating HTML report...")
    html = generate_html_report(csv_file, all_currency_data)
    
    # Save report
    stem = Path(csv_file).stem
    if 'forex-forest-signals-page-' in stem:
        signal_id = stem.replace('forex-forest-signals-page-', '')
    elif stem.startswith('signal_') and stem.endswith('_trades'):
        signal_id = stem.replace('signal_', '').replace('_trades', '')
    else:
        signal_id = stem
    output_file = OUTPUT_DIR / f"detailed_comparison_all_levels_{signal_id}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Report saved to: {output_file}")
    print(f"📊 File size: {len(html):,} bytes")
    print(f"📈 {len(all_currency_data)} currency pairs analyzed")
    print(f"📊 Each currency includes: L1, L2, L3, L4+ analysis")
    
    total_comparisons = 0
    for currency, data in all_currency_data.items():
        for level_name in data['levels']:
            if data['levels'][level_name]['stats']['count'] > 0:
                total_comparisons += 8  # 4 profit + 4 lose
    
    print(f"⚡ Total comparisons: {total_comparisons}")
    
    return output_file

if __name__ == "__main__":
    main()
