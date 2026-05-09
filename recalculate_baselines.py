#!/usr/bin/env python3
"""
Recalculate global baselines using LOT-BASED level detection.
Scans all signals with SET mapping, assigns levels by lot size,
then computes TP/SL/Profit percentiles per level.

Output: New baseline constants to paste into generate_all_levels_from_csv.py
"""
import csv
import json
import os
import re
from pathlib import Path
from collections import defaultdict
import statistics

BASE_DIR = Path(__file__).parent
SAMPLES_DIR = BASE_DIR / 'samples'
MAPPING_FILE = BASE_DIR / 'signal_lot_mapping.json'

def load_lot_mapping():
    with open(MAPPING_FILE) as f:
        return json.load(f)

def assign_lot_level(trade_lot, lot_layers):
    """
    Assign level based on closest lot size match.
    Returns (level_num, level_name, is_autolot)
    """
    if not lot_layers:
        return None
    
    # Find closest lot layer
    best = min(lot_layers, key=lambda x: abs(x[1] - trade_lot))
    best_level, best_lot = best
    
    # AutoLot detection: >20% deviation from closest SET lot
    tolerance = best_lot * 0.25
    is_autolot = abs(trade_lot - best_lot) > tolerance and best_lot > 0
    
    if best_level >= 9:
        return (best_level, 'L9+', is_autolot)
    return (best_level, f'L{best_level}', is_autolot)

def main():
    mapping = load_lot_mapping()
    print(f"Loaded mapping for {len(mapping)} signals")
    
    # Collect all trade data grouped by lot-based level
    level_trades = defaultdict(list)  # level_name -> list of trades
    
    processed = 0
    autolot_signals = []
    
    for sid, info in mapping.items():
        lot_layers = info.get('lot_layers', [])
        ea_type = info.get('ea_type', 'UNK')
        if not lot_layers:
            continue
        
        # Find CSV
        csv_path = None
        for pattern in [f'forex-forest-signals-page-{sid}.csv']:
            p = SAMPLES_DIR / pattern
            if p.exists():
                csv_path = p
                break
        if not csv_path:
            continue
        
        # Read trades
        trades = []
        with open(csv_path, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ttype = row.get('Type', '').strip().lower()
                if ttype not in ('buy', 'sell'):
                    continue
                try:
                    trades.append({
                        'lots': float(row.get('Lots', 0)),
                        'net_profit': float(row.get('Net Profit', 0)),
                        'net_pips': float(row.get('Net Pips', 0)),
                        'max_pips': float(row.get('Max Pips', 0)),
                        'max_loss_pips': float(row.get('Max Loss Pips', 0)),
                        'max_profit': float(row.get('Max Profit', 0)),
                        'max_loss': float(row.get('Max Loss', 0)),
                        'commission': float(row.get('Commission', 0)),
                        'swap': float(row.get('Swap', 0)),
                    })
                except (ValueError, TypeError):
                    continue
        
        if not trades:
            continue
        
        # Check AutoLot
        unique_lots = len(set(round(t['lots'], 4) for t in trades))
        set_layers = len(lot_layers)
        is_autolot = unique_lots > set_layers * 2 and set_layers > 1
        
        if is_autolot:
            autolot_signals.append(f"{sid} ({ea_type}): {unique_lots} unique vs {set_layers} SET")
        
        # Assign levels
        for t in trades:
            result = assign_lot_level(t['lots'], lot_layers)
            if result:
                level_num, level_name, al = result
                t['level_num'] = level_num
                t['level_name'] = level_name
                t['is_autolot'] = al or is_autolot
                t['ea_type'] = ea_type
                level_trades[level_name].append(t)
        
        processed += 1
    
    print(f"\nProcessed: {processed} signals")
    print(f"AutoLot signals: {len(autolot_signals)}")
    for s in autolot_signals:
        print(f"  {s}")
    
    # Calculate baselines per level
    print("\n" + "=" * 80)
    print("LOT-BASED GLOBAL BASELINES")
    print("=" * 80)
    
    level_names = ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9+']
    
    # TP baselines (P85 of winning trades' Max Pips)
    tp_baselines = {}
    sl_baselines = {}
    profit_baselines = {}  # p50, p75
    
    print(f"\n{'Level':<6} {'Trades':<8} {'Wins':<8} {'Win%':<8} {'TP(P85)':<10} {'SL(P85)':<10} {'Profit P50':<12} {'Profit P75':<12}")
    print("-" * 80)
    
    for lv in level_names:
        trades = level_trades.get(lv, [])
        if not trades:
            continue
        
        n = len(trades)
        wins = [t for t in trades if t['net_profit'] > 0]
        n_wins = len(wins)
        wr = n_wins / n * 100 if n > 0 else 0
        
        # TP: P85 of winning trades' |Max Pips|
        if n_wins >= 5:
            win_max_pips = sorted([abs(t['max_pips']) for t in wins])
            tp = win_max_pips[int(len(win_max_pips) * 0.85)]
            tp_baselines[lv] = round(tp, 1)
        else:
            tp_baselines[lv] = None
        
        # SL: P85 of all trades' |Max Loss Pips|
        if n >= 5:
            all_max_loss = sorted([abs(t['max_loss_pips']) for t in trades])
            sl = all_max_loss[int(len(all_max_loss) * 0.85)]
            sl_baselines[lv] = round(sl, 1)
        else:
            sl_baselines[lv] = None
        
        # Profit percentiles (from winning trades)
        if n_wins >= 5:
            profits = sorted([t['net_profit'] for t in wins])
            p50 = profits[len(profits) // 2]
            p75 = profits[3 * len(profits) // 4]
            profit_baselines[lv] = {'p50': round(p50, 2), 'p75': round(p75, 2)}
        else:
            profit_baselines[lv] = None
        
        tp_str = f"{tp_baselines[lv]:.1f}" if tp_baselines.get(lv) else "N/A"
        sl_str = f"{sl_baselines[lv]:.1f}" if sl_baselines.get(lv) else "N/A"
        p50_str = f"${profit_baselines[lv]['p50']:.2f}" if profit_baselines.get(lv) else "N/A"
        p75_str = f"${profit_baselines[lv]['p75']:.2f}" if profit_baselines.get(lv) else "N/A"
        
        print(f"{lv:<6} {n:<8} {n_wins:<8} {wr:<8.1f} {tp_str:<10} {sl_str:<10} {p50_str:<12} {p75_str:<12}")
    
    # Output Python code
    print("\n" + "=" * 80)
    print("COPY THIS INTO generate_all_levels_from_csv.py:")
    print("=" * 80)
    
    print("\nGLOBAL_TP_BASELINES = {")
    for lv in level_names:
        if tp_baselines.get(lv):
            print(f"    '{lv}': {tp_baselines[lv]},")
    print("}")
    
    print("\nGLOBAL_SL_BASELINES = {")
    for lv in level_names:
        if sl_baselines.get(lv):
            print(f"    '{lv}': {sl_baselines[lv]},")
    print("}")
    
    print("\nGLOBAL_BASELINES = {")
    print("    'global_p25': 1.52,")
    print("    'floor': 5.00,")
    print("    'min_sample': 30,")
    print("    'profit': {")
    for lv in level_names:
        if profit_baselines.get(lv):
            print(f"        '{lv}': {{'p50': {profit_baselines[lv]['p50']}, 'p75': {profit_baselines[lv]['p75']}}},")
    print("    },")
    print("    'lose': {")
    # For lose baselines, use same structure (will be computed from recovery trades)
    for lv in level_names:
        if profit_baselines.get(lv):
            print(f"        '{lv}': {{'p50': {profit_baselines[lv]['p50'] * 0.95:.2f}, 'p75': {profit_baselines[lv]['p75'] * 0.95:.2f}}},")
    print("    }")
    print("}")

if __name__ == '__main__':
    main()
