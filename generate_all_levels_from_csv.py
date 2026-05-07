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

# Global TP/SL percentile baselines (pre-computed from 58 signals)
# P85 of winning trades' Max Pips per level
GLOBAL_TP_BASELINES = {
    'L1': 53.0, 'L2': 129.8, 'L3': 137.3, 'L4+': 195.5
}
# P85 of all trades' Max Loss Pips per level
GLOBAL_SL_BASELINES = {
    'L1': 44.7, 'L2': 63.3, 'L3': 58.4, 'L4+': 70.9
}

# Global percentile baselines (pre-computed from 58 signals, 89,158 winning trades)
GLOBAL_BASELINES = {
    'global_p25': 1.52,
    'floor': 5.00,
    'min_sample': 30,
    'profit': {  # From winning trades per level
        'L1': {'p50': 3.82, 'p75': 8.89},
        'L2': {'p50': 66.41, 'p75': 80.28},
        'L3': {'p50': 120.07, 'p75': 132.90},
        'L4+': {'p50': 321.63, 'p75': 587.03},
    },
    'lose': {  # From recovered trades per level
        'L1': {'p50': 4.40, 'p75': 10.65},
        'L2': {'p50': 66.74, 'p75': 80.73},
        'L3': {'p50': 119.78, 'p75': 132.15},
        'L4+': {'p50': 306.84, 'p75': 546.51},
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


def generate_html_report(csv_file, all_currency_data, level_ranges):
    """Generate HTML report for all currencies and levels"""
    
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
            <table class="comparison-table">
                <thead>
                    <tr>
                        <th>Currency</th>
                        <th>L1 Trades</th>
                        <th>L2 Trades</th>
                        <th>L3 Trades</th>
                        <th>L4+ Trades</th>
                        <th>Total Trades</th>
                        <th>Overall Win Rate</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    # Build summary
    for currency in currency_pairs:
        data = all_currency_data[currency]
        
        total_trades = sum([
            data['levels']['L1']['stats']['count'],
            data['levels']['L2']['stats']['count'],
            data['levels']['L3']['stats']['count'],
            data['levels']['L4+']['stats']['count']
        ])
        
        if total_trades == 0:
            continue
        
        win_rate = data['stats']['win_rate']
        win_rate_class = 'rating-excellent' if win_rate >= 60 else 'rating-good' if win_rate >= 50 else 'rating-average' if win_rate >= 40 else 'rating-poor'
        
        html += f"""
                    <tr>
                        <td><strong>{currency}</strong></td>
                        <td>{data['levels']['L1']['stats']['count']}</td>
                        <td>{data['levels']['L2']['stats']['count']}</td>
                        <td>{data['levels']['L3']['stats']['count']}</td>
                        <td>{data['levels']['L4+']['stats']['count']}</td>
                        <td>{total_trades}</td>
                        <td class="score-cell {win_rate_class}">{win_rate:.2%}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
"""
    
    # Build detailed sections for each currency
    for currency in currency_pairs:
        data = all_currency_data[currency]
        stats = data['stats']
        levels = data['levels']
        
        total_trades = sum([
            levels['L1']['stats']['count'],
            levels['L2']['stats']['count'],
            levels['L3']['stats']['count'],
            levels['L4+']['stats']['count']
        ])
        
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
        
        # Build each level
        for level_name in ['L1', 'L2', 'L3', 'L4+']:
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
                    <table class="comparison-table">
                        <thead>
                            <tr>
                                <th>Wait</th>
                                <th>Trigger Rate</th>
                                <th>Avg After</th>
                                <th>DDE</th>
                                <th>Score</th>
                                <th>Rating</th>
                                <th>Score Details</th>
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
                            <td class="score-details">{result['score_details']['trigger_rate']}<br>{result['score_details']['alpha_profit']}<br>{result['score_details']['dde']}<br><strong>{result['score_details']['total']}</strong></td>
                        </tr>
"""
            
            html += """
                        </tbody>
                    </table>
                </div>
"""
            
            # Copy on Lose table
            lose_results = level_data['copy_on_lose']
            html += """
                <div class="strategy-section">
                    <div class="strategy-header">🛡️ Copy on Lose (Recovery Rate 50% + Alpha Capture Profit 50% | Trigger Rate: display only)</div>
                    <table class="comparison-table">
                        <thead>
                            <tr>
                                <th>Wait</th>
                                <th>Trigger Rate*</th>
                                <th>Recovery Rate</th>
                                <th>Avg After</th>
                                <th>Score</th>
                                <th>Rating</th>
                                <th>Score Details</th>
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
                            <td class="score-details">{result['score_details']['recovery_rate']}<br>{result['score_details']['alpha_profit']}<br>{result['score_details']['trigger_rate_info']}<br><strong>{result['score_details']['total']}</strong></td>
                        </tr>
"""
            
            html += """
                        </tbody>
                    </table>
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
</body>
</html>
"""
    
    return html

def main():
    import sys
    
    print("🚀 Starting all-levels comparison analysis from CSV...")
    
    # Level ranges (L1, L2, L3, L4+)
    level_ranges = {
        'L1': (0, 50),
        'L2': (50, 100),
        'L3': (100, 150),
        'L4+': (150, float('inf'))
    }
    
    # Get CSV file path from command line or find automatically
    if len(sys.argv) > 1:
        csv_file = Path(sys.argv[1])
    else:
        # Find CSV files
        csv_files = list(CSV_DIR.glob("signal_*.csv"))
        
        if not csv_files:
            print(f"❌ No CSV files found in {CSV_DIR}")
            return
        
        # Process the first CSV file found
        csv_file = csv_files[0]
    
    print(f"📄 Processing CSV file: {csv_file}")
    
    # Analyze trades from CSV
    trades = analyze_trades_from_csv(csv_file)
    print(f"📊 Total trades: {len(trades)}")
    
    # Group trades by currency
    currency_data = defaultdict(list)
    for trade in trades:
        symbol = trade.get('symbol', '')
        if symbol:
            currency_data[symbol].append(trade)
    
    print(f"📈 Found {len(currency_data)} currency pairs")
    
    # Analyze each currency by levels
    all_currency_data = {}
    
    for currency, currency_trades in currency_data.items():
        print(f"  🔄 Processing {currency}...")
        
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
        
        # Analyze by levels
        levels = analyze_by_levels(currency_trades, level_ranges)
        
        all_currency_data[currency] = {
            'stats': stats,
            'levels': levels
        }
    
    print(f"✅ Processed {len(all_currency_data)} currency pairs")
    
    # Generate HTML report
    print("📝 Generating HTML report...")
    html = generate_html_report(csv_file, all_currency_data, level_ranges)
    
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
