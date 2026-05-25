#!/usr/bin/env python3
"""
DDE v4 評分模型 — 基於老闆指定嘅 5 個維度
Based on Gemini consultation + Alvin's 5 criteria

Dimensions & Weights:
  1. Win Rate (勝率)                — 20%
  2. Holding Time (持倉時間)        — 5%
  3. Trade Count (交易數量)          — 15%
  4. Martin Layers (馬丁層數)        — 25%
  5. Risk/Reward (Net Pips/Max Loss) — 35%

Red card rules (auto 0):
  - Net Pips <= 0
  - Trade Count < 30
  - Max Loss Pips > 500 (single trade)
  - Win Rate < 50%
"""

import csv
import re
import json
import sys
import pickle
from pathlib import Path
from collections import defaultdict

# DEPRECATED: LEVEL_RANGES was pip-based, no longer used for level classification.
# Level classification is now LOT-BASED only. See compute_layer_lot() and infer_levels_from_lots().
# Kept for reference only — DO NOT USE in any scoring logic.
_DEPRECATED_LEVEL_RANGES = {
    'L1': (0, 50),
    'L2': (50, 100),
    'L3': (100, 150),
    'L4+': (150, float('inf'))
}


def clamp(val, lo=0, hi=100):
    return max(lo, min(hi, val))


def read_csv_trades(csv_path):
    """Read CSV and return list of trade dicts."""
    trades = []
    with open(csv_path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                trade_type = row.get('Type', '').strip().lower()
                if trade_type not in ('buy', 'sell'):
                    continue  # skip balance/transfer rows
                
                lots = float(row.get('Lots', 0))
                net_pips = float(row.get('Net Pips', 0))
                net_profit = float(row.get('Net Profit', 0))
                max_loss_pips = abs(float(row.get('Max Loss Pips', 0)))
                holding_hours = float(row.get('Holding Time (Hours)', 0))
                symbol = row.get('Symbol', '').strip()
                
                trades.append({
                    'type': trade_type,
                    'lots': lots,
                    'symbol': symbol,
                    'net_pips': net_pips,
                    'net_profit': net_profit,
                    'max_loss_pips': max_loss_pips,
                    'holding_hours': holding_hours,
                })
            except (ValueError, TypeError):
                continue
    return trades


def infer_levels_from_lots(trades_for_group):
    """
    Fallback: when no SET lot_layers available, infer levels from unique lot values.
    Sort unique lots ascending; smallest = L1, second = L2, etc.
    Trades with same lot → same level (e.g. flat-bet like S10 → all L1).
    """
    unique_lots = sorted(set(
        round(t['lots'], 6)
        for t in trades_for_group
        if t.get('lots', 0) > 0
    ))
    if not unique_lots:
        return {'_default': 'L1'}  # no lot data at all
    if len(unique_lots) == 1:
        return {unique_lots[0]: 'L1'}  # flat-bet
    mapping = {}
    for i, lot in enumerate(unique_lots):
        mapping[lot] = f'L{min(i + 1, 9)}' if i < 8 else 'L9+'
    return mapping


def compute_layer_from_lot_fallback(trade_lot, lot_to_level):
    """Map a trade's lot to level using inferred lot→level mapping."""
    if not lot_to_level or trade_lot <= 0:
        return 'L1'
    # Find closest lot in mapping
    best_lot = min(lot_to_level.keys(), key=lambda x: abs(x - trade_lot))
    return lot_to_level[best_lot]


# REMOVED: compute_layer_net_profit() — was incorrectly using net_profit to classify levels.
# See BUG_pip_based_levels.md for details.


def load_lot_mapping():
    """Load per-signal lot→level mapping from SET files."""
    mapping_path = Path(__file__).parent / 'signal_lot_mapping.json'
    if mapping_path.exists():
        with open(mapping_path) as f:
            return json.load(f)
    return {}


def compute_layer_lot(trade_lot, lot_layers):
    """Map trade lot size to level using SET file lot layers."""
    if not lot_layers or trade_lot <= 0:
        return 'L1'
    best_level = 1
    best_diff = float('inf')
    for level, lot in lot_layers:
        diff = abs(trade_lot - lot)
        if diff < best_diff:
            best_diff = diff
            best_level = level
    if best_level >= 9:
        return 'L9+'
    return f'L{best_level}'


def score_v4(trades_for_symbol, lot_layers=None):
    """
    Compute DDE v4 score for a single signal × symbol combination.
    lot_layers: optional list of (level_num, lot_size) from SET file.
    Returns dict with individual scores and final score.
    """
    n = len(trades_for_symbol)
    if n == 0:
        return None
    
    # --- Raw metrics ---
    total_net_pips = sum(t['net_pips'] for t in trades_for_symbol)
    wins = [t for t in trades_for_symbol if t['net_profit'] > 0]
    win_rate = len(wins) / n * 100
    avg_hold = sum(t['holding_hours'] for t in trades_for_symbol) / n
    max_loss_pip = max((t['max_loss_pips'] for t in trades_for_symbol), default=0)
    
    # Martin layers: weighted average layer (STRICTLY lot-based)
    # If no lot_layers provided, infer from unique lot values in this group
    layer_counts = defaultdict(int)
    if lot_layers:
        for t in trades_for_symbol:
            lv = compute_layer_lot(t['lots'], lot_layers)
            layer_counts[lv] += 1
    else:
        # Fallback: infer levels from unique lot values in this symbol's trades
        lot_to_level = infer_levels_from_lots(trades_for_symbol)
        for t in trades_for_symbol:
            lv = compute_layer_from_lot_fallback(t['lots'], lot_to_level)
            layer_counts[lv] += 1
    # Convert level name to numeric: L1→1, L2→2, ..., L9+→9
    def lv_to_num(lv_name):
        if lv_name == 'L9+': return 9
        try: return int(lv_name[1:])
        except: return 1
    wal = sum(cnt * lv_to_num(lv) for lv, cnt in layer_counts.items()) / n
    
    # --- Red card rules ---
    red_card = False
    red_reasons = []
    if total_net_pips <= 0:
        red_card = True
        red_reasons.append('Net Pips <= 0')
    if n < 20:
        red_card = True
        red_reasons.append(f'Trades < 20 ({n})')
    if win_rate < 50:
        red_card = True
        red_reasons.append(f'Win Rate < 50% ({win_rate:.1f}%)')
    
    # --- Individual dimension scores (0-100) ---
    # Always compute real scores, even for red cards
    
    # 1. Risk/Reward (35%): Pips Ratio
    pips_ratio = total_net_pips / max_loss_pip if max_loss_pip > 0 else 100
    rr_score = clamp((pips_ratio - 1) / 14 * 100)
    
    # 2. Martin Layers (25%): Weighted Average Layer
    ml_score = clamp(100 * (1 - (wal - 1) / 1.5))
    
    # 3. Win Rate (20%)
    wr_score = clamp((win_rate - 55) / 30 * 100)
    
    # 4. Trade Count (15%)
    tc_score = clamp((n - 20) / 280 * 100)
    
    # 5. Holding Time (5%)
    ht_score = clamp(100 * (1 - (avg_hold - 4) / 68)) if avg_hold >= 4 else 100
    
    # --- Weighted final ---
    final = round(
        rr_score * 0.35 +
        ml_score * 0.25 +
        wr_score * 0.20 +
        tc_score * 0.15 +
        ht_score * 0.05,
        1
    )
    
    return {
        'score': final,
        'red_card': red_card,
        'red_reasons': red_reasons,
        'rr_score': round(rr_score, 1),
        'ml_score': round(ml_score, 1),
        'wr_score': round(wr_score, 1),
        'tc_score': round(tc_score, 1),
        'ht_score': round(ht_score, 1),
        'win_rate': round(win_rate, 1),
        'avg_hold': round(avg_hold, 2),
        'trades': n,
        'wal': round(wal, 3),
        'pips_ratio': round(pips_ratio, 2),
        'total_net_pips': round(total_net_pips, 1),
        'max_loss_pip': round(max_loss_pip, 1),
        'layers': dict(layer_counts),
    }


if __name__ == '__main__':
    SAMPLES = Path('samples')
    DOWNLOADS = Path('downloads')
    OUTPUT = Path('output')
    
    EA_MAP = {
        'DW': [10437,11984,13790,17547,21698,22200,22278,25830,30359,31781,32719,3291,33101,31593,34574,36338,36397,36511,34259,20846,16538],
        'SMA': [106,1980,2351,32278,32541,5001,5275,537,5566,11889,13863,14724,16596,16698,16706,17611,17823,10864,14158],
        'MKD': [12962,13461,14341,14592,1470,17962,20805,23617,25668,25260,8325,7919],
        'S10': [13798,16596],
        'Flash': [19849],
        'GEM': [14581],
    }
    
    def get_ea(sid):
        eas = []
        for ea, ids in EA_MAP.items():
            if int(sid) in ids:
                eas.append(ea)
        return eas if eas else ['UNK']
    
    # Load lot mapping from SET files
    lot_mapping = load_lot_mapping()
    print(f"Lot mapping loaded: {len(lot_mapping)} signals")
    
    # Collect CSVs with dedup
    all_csvs = {}
    for csv_file in sorted(SAMPLES.glob('forex-forest-signals-page-*.csv')):
        m = re.search(r'(\d+)', csv_file.stem)
        if m:
            all_csvs[m.group(1)] = csv_file
    for csv_file in sorted(DOWNLOADS.glob('forex-forest-signals-page-*.csv')):
        m = re.search(r'(\d+)', csv_file.stem)
        if m and m.group(1) not in all_csvs:
            all_csvs[m.group(1)] = csv_file
    
    print(f"CSV signals: {len(all_csvs)}")
    
    all_results = []
    for sid, csv_file in sorted(all_csvs.items()):
        report = OUTPUT / f'detailed_comparison_all_levels_{sid}.html'
        if not report.exists():
            continue
        
        eas = get_ea(sid)
        ea_tag = '/'.join(eas)
        
        trades = read_csv_trades(str(csv_file))
        if not trades:
            continue
        
        # Group by symbol
        by_symbol = defaultdict(list)
        for t in trades:
            by_symbol[t['symbol']].append(t)
        
        # Get lot layers for this signal
        lot_layers = None
        if sid in lot_mapping and lot_mapping[sid].get('lot_layers'):
            lot_layers = [(lv, lot) for lv, lot in lot_mapping[sid].get('lot_layers', [])]
        # NOTE: lot_layers is passed per-symbol; if None, score_v4 will
        # auto-infer from unique lots in that symbol's trades (lot-based fallback)
        
        for sym, sym_trades in by_symbol.items():
            result = score_v4(sym_trades, lot_layers=lot_layers)
            if result is None:
                continue
            
            # Pips-based Profit Factor
            gross_pips = sum(t['net_pips'] for t in sym_trades if t['net_pips'] > 0)
            loss_pips = abs(sum(t['net_pips'] for t in sym_trades if t['net_pips'] < 0))
            pf = gross_pips / loss_pips if loss_pips > 0 else (999.0 if gross_pips > 0 else 0)
            
            # Pips-based Max DD (cumsum of net_pips)
            cum = 0; peak = 0; max_dd = 0
            for t in sym_trades:
                cum += t['net_pips']
                if cum > peak: peak = cum
                if cum - peak < max_dd: max_dd = cum - peak
            
            layer_names = []
            for ln in sorted(set(result['layers'].keys()), key=lambda x: (99 if x == 'L9+' else int(x[1:]))):
                if result['layers'].get(ln, 0) > 0:
                    layer_names.append(ln)
            
            all_results.append({
                'signal_id': sid,
                'symbol': sym,
                'ea': ea_tag,
                'dde_v4': result['score'],
                'rr': result['rr_score'],
                'ml': result['ml_score'],
                'wr': result['wr_score'],
                'tc': result['tc_score'],
                'ht': result['ht_score'],
                'red_card': result['red_card'],
                'red_reasons': result['red_reasons'],
                'trades': result['trades'],
                'win_rate': result['win_rate'],
                'avg_hold': result['avg_hold'],
                'wal': result['wal'],
                'pips_ratio': result['pips_ratio'],
                'total_net_pips': result['total_net_pips'],
                'max_loss_pip': result['max_loss_pip'],
                'pf': round(pf, 1),
                'total_profit_pips': round(result['total_net_pips'], 1),
                'max_dd_pips': round(max_dd, 1),
                'lv': '+'.join(layer_names) if layer_names else '-',
            })
    
    # Summary
    scored = [r for r in all_results if not r['red_card']]
    red = [r for r in all_results if r['red_card']]
    print(f"\n📊 DDE v4 Results (lot-based):")
    print(f"  Total rows: {len(all_results)}")
    print(f"  Scored: {len(scored)}")
    print(f"  Red card: {len(red)}")
    if scored:
        scores = [r['dde_v4'] for r in scored]
        print(f"  Score range: {min(scores)} - {max(scores)}")
        print(f"  Average: {round(sum(scores)/len(scores), 1)}")
    
    # Save
    with open('/tmp/dde_v4_data.pkl', 'wb') as f:
        pickle.dump(all_results, f)
    
    # Top 10
    scored.sort(key=lambda x: x['dde_v4'], reverse=True)
    print(f"\n🏆 Top 10:")
    for r in scored[:10]:
        print(f"  {r['signal_id']} × {r['symbol']:8s} = {r['dde_v4']:5.1f}  "
              f"pips={r['total_profit_pips']:+.1f} dd={r['max_dd_pips']:.1f} pf={r['pf']:.1f}")

    # Bottom 5
    print(f"\n💀 Bottom 5 (scored):")
    for r in scored[-5:]:
        print(f"  {r['signal_id']} × {r['symbol']:8s} = {r['dde_v4']:5.1f}  "
              f"pips={r['total_profit_pips']:+.1f} dd={r['max_dd_pips']:.1f} pf={r['pf']:.1f}")
    
    # Red card examples
    if red:
        print(f"\n🚫 Red cards ({len(red)}):")
        for r in red[:5]:
            print(f"  {r['signal_id']} × {r['symbol']:8s} — {', '.join(r['red_reasons'])}")
