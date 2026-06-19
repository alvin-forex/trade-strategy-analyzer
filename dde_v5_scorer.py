#!/usr/bin/env python3
"""
DDE v5 評分模型 — 排名制 + 4 維度加權（老闆確認版 2026-05-26）

設計原則：
  - 用最真實嘅交易數據，唔做歸一化扭曲
  - 排名制：每個維度喺所有 Signal×CCY 之間排名，轉為百分位分數
  - 加權求和得出最終 DDE v5 分數

4 個維度 + 權重（老闆拍板）：
  1. Win Rate（勝率）      — 15%  | 真實勝率 × 100，唔加工
  2. Profit Factor         — 20%  | 平均盈利 pips / 平均 MAX LOSE pips（剔除 3σ 極端值）
  3. $1K DD%（真實 DD%）    — 25%  | 直接用真實 DD%，唔調整起始資金
  4. Martin Discipline      — 40%  | 維持 v4 現有計法（WAL + 層數分析）

Red card 規則（沿用 v4）：
  - Net Pips <= 0
  - Trade Count < 20
  - Max Loss Pips > 500（單筆）
  - Win Rate < 50%

排名制邏輯：
  1. 所有 Signal×CCY 計算 4 個維度嘅真實數值
  2. 每個維度內排名（越高越好，DD 越低越好）
  3. 排名轉為百分位分數：percentile = (rank - 1) / (N - 1) × 100
  4. 加權求和：WR_pct×15% + PF_pct×20% + DD_pct×25% + Martin_pct×40%
  5. 最終分數 = 加權百分位（0-100）
"""

import csv
import re
import json
import sys
import math
from pathlib import Path
from collections import defaultdict
from datetime import datetime


# ─── Utilities ───

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
                    continue

                lots = float(row.get('Lots', 0))
                net_pips = float(row.get('Net Pips', 0))
                net_profit = float(row.get('Net Profit', 0))
                max_loss_pips = abs(float(row.get('Max Loss Pips', 0)))
                holding_hours = float(row.get('Holding Time (Hours)', 0))
                symbol = row.get('Symbol', '').strip()

                max_profit = float(row.get('Max Profit', 0))
                max_loss = abs(float(row.get('Max Loss', 0)))
                max_pips = float(row.get('Max Pips', 0))

                # Parse Open Time for time insights
                _open_time = None
                try:
                    _open_time = datetime.strptime(row.get('Open Time', '').strip(), '%d/%m/%Y %H:%M:%S')
                except:
                    pass

                trades.append({
                    'type': trade_type,
                    'lots': lots,
                    'symbol': symbol,
                    'net_pips': net_pips,
                    'net_profit': net_profit,
                    'max_loss_pips': max_loss_pips,
                    'holding_hours': holding_hours,
                    'max_profit': max_profit,       # MFE $
                    'max_loss': max_loss,             # MAE $
                    'max_pips': max_pips,             # MFE pips
                    '_open_time': _open_time,         # For time analysis
                })
            except (ValueError, TypeError):
                continue
    return trades


# ─── Lot → Level mapping (from v4) ───

def infer_levels_from_lots(trades_for_group):
    """Fallback: infer levels from unique lot values."""
    unique_lots = sorted(set(
        round(t['lots'], 6)
        for t in trades_for_group
        if t.get('lots', 0) > 0
    ))
    if not unique_lots:
        return {'_default': 'L1'}
    if len(unique_lots) == 1:
        return {unique_lots[0]: 'L1'}
    mapping = {}
    for i, lot in enumerate(unique_lots):
        mapping[lot] = f'L{min(i + 1, 9)}' if i < 8 else 'L9+'
    return mapping


def compute_layer_from_lot_fallback(trade_lot, lot_to_level):
    if not lot_to_level or trade_lot <= 0:
        return 'L1'
    best_lot = min(lot_to_level.keys(), key=lambda x: abs(x - trade_lot))
    return lot_to_level[best_lot]


def load_lot_mapping():
    mapping_path = Path(__file__).parent / 'signal_lot_mapping.json'
    if mapping_path.exists():
        with open(mapping_path) as f:
            return json.load(f)
    return {}


def compute_layer_lot(trade_lot, lot_layers):
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


# ─── v5 Raw Metrics (per Signal×CCY) ───

def compute_raw_metrics(trades_for_symbol, lot_layers=None):
    """
    Compute the 4 raw metrics for v5 scoring.
    Returns dict with raw values (NOT scores — scoring happens via ranking).
    """
    n = len(trades_for_symbol)
    if n == 0:
        return None

    # --- 1. Win Rate (真實勝率，唔加工) ---
    wins = [t for t in trades_for_symbol if t['net_profit'] > 0]
    win_rate = len(wins) / n * 100  # e.g. 67.3

    # --- 2. Profit Factor (剔除 3σ 極端值後) ---
    # 計法：平均盈利 pips / 平均 MAX LOSE pips
    profit_pips_list = [t['net_pips'] for t in trades_for_symbol if t['net_pips'] > 0]
    max_loss_list = [t['max_loss_pips'] for t in trades_for_symbol if t['max_loss_pips'] > 0]

    # 剔除 3σ 極端值
    def remove_outliers(values):
        if len(values) < 4:
            return values
        mean = sum(values) / len(values)
        std = (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5
        if std == 0:
            return values
        return [x for x in values if abs(x - mean) <= 3 * std]

    clean_profits = remove_outliers(profit_pips_list)
    clean_losses = remove_outliers(max_loss_list)

    avg_profit = sum(clean_profits) / len(clean_profits) if clean_profits else 0
    avg_max_loss = sum(clean_losses) / len(clean_losses) if clean_losses else 0
    pf_raw = avg_profit / avg_max_loss if avg_max_loss > 0 else (999.0 if avg_profit > 0 else 0)

    # --- 3. $1K DD% (真實 DD%) ---
    # 計算 cumulative DD in pips，然後轉為 DD%
    # 簡化：用 max drawdown pips 作為 DD 指標
    # 真實 DD% = max DD pips / (starting capital in pips equivalent)
    # 但老闆話直接用真實 DD%，唔調整起始資金
    # 所以我用 max DD pips 作為原始值（越細越好）
    cum = 0
    peak = 0
    max_dd = 0
    for t in trades_for_symbol:
        cum += t['net_pips']
        if cum > peak:
            peak = cum
        if cum - peak < max_dd:
            max_dd = cum - peak

    # --- 4. Martin Discipline (沿用 v4) ---
    layer_counts = defaultdict(int)
    if lot_layers:
        for t in trades_for_symbol:
            lv = compute_layer_lot(t['lots'], lot_layers)
            layer_counts[lv] += 1
    else:
        lot_to_level = infer_levels_from_lots(trades_for_symbol)
        for t in trades_for_symbol:
            lv = compute_layer_from_lot_fallback(t['lots'], lot_to_level)
            layer_counts[lv] += 1

    def lv_to_num(lv_name):
        if lv_name == 'L9+':
            return 9
        try:
            return int(lv_name[1:])
        except:
            return 1

    wal = sum(cnt * lv_to_num(lv) for lv, cnt in layer_counts.items()) / n

    # Martin score: 沿用 v4 計法
    # WAL=1 (全L1) → 100分，WAL越高越差
    # v4: ml_score = clamp(100 * (1 - (wal - 1) / 1.5))
    # v5 用 raw WAL，排名時 WAL 越細越好
    martin_raw = wal  # raw WAL value, lower = better

    # --- Other useful metrics ---
    total_net_pips = sum(t['net_pips'] for t in trades_for_symbol)
    max_loss_pip = max((t['max_loss_pips'] for t in trades_for_symbol), default=0)
    avg_hold = sum(t['holding_hours'] for t in trades_for_symbol) / n

    # --- BUY/SELL bias ---
    buy_count = sum(1 for t in trades_for_symbol if t.get('type') == 'buy')
    sell_count = sum(1 for t in trades_for_symbol if t.get('type') == 'sell')
    buy_pct = buy_count / n * 100 if n else 0
    sell_pct = sell_count / n * 100 if n else 0
    bias = 'BUY' if buy_pct > 65 else ('SELL' if sell_pct > 65 else 'MIX')

    # --- MFE/MAE ---
    avg_mfe = sum(t.get('max_profit', 0) for t in trades_for_symbol) / n
    avg_mae = sum(t.get('max_loss', 0) for t in trades_for_symbol) / n
    avg_mfe_pips = sum(t.get('max_pips', 0) for t in trades_for_symbol) / n
    avg_mae_pips = sum(t.get('max_loss_pips', 0) for t in trades_for_symbol) / n
    mfe_mae_ratio = abs(avg_mfe / avg_mae) if avg_mae != 0 else 999.0
    suggest_tp = round(avg_mfe_pips * 0.8, 1) if avg_mfe_pips > 0 else 0
    suggest_sl = round(abs(avg_mae_pips) * 1.2, 1) if avg_mae_pips != 0 else 0

    # --- Time insights ---
    day_counts = defaultdict(int)
    day_wins = defaultdict(int)
    hour_counts = defaultdict(int)
    hour_wins = defaultdict(int)
    for t in trades_for_symbol:
        try:
            # Parse Open Time if available in raw trade
            ot = t.get('_open_time')
            if ot:
                day_counts[ot.strftime('%a')] += 1
                if t['net_pips'] > 0:
                    day_wins[ot.strftime('%a')] += 1
                hour_counts[ot.hour] += 1
                if t['net_pips'] > 0:
                    hour_wins[ot.hour] += 1
        except:
            pass
    best_day = max(day_wins, key=lambda d: day_wins[d]/day_counts[d]*100 if day_counts.get(d, 0) > 0 else 0) if day_wins else '-'
    worst_day = min(day_wins, key=lambda d: day_wins[d]/day_counts[d]*100 if day_counts.get(d, 0) > 0 else 0) if day_wins else '-'

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
    # 單筆 max loss > 500 pips → red card
    if max_loss_pip > 500:
        red_card = True
        red_reasons.append(f'Single Max Loss > 500 pips ({max_loss_pip:.0f})')

    return {
        # v5 raw metrics (for ranking)
        'wr_raw': round(win_rate, 2),           # 越高越好
        'pf_raw': round(pf_raw, 3),             # 越高越好
        'dd_raw': round(abs(max_dd), 1),        # 越細越好（排名時 reverse）
        'martin_raw': round(wal, 4),            # 越細越好（排名時 reverse）

        # Other info
        'red_card': red_card,
        'red_reasons': red_reasons,
        'win_rate': round(win_rate, 1),
        'pf': round(pf_raw, 2),
        'trades': n,
        'wal': round(wal, 3),
        'total_net_pips': round(total_net_pips, 1),
        'max_dd_pips': round(abs(max_dd), 1),
        'max_loss_pip': round(max_loss_pip, 1),
        'avg_hold': round(avg_hold, 2),
        'avg_profit_clean': round(avg_profit, 1),
        'avg_max_loss_clean': round(avg_max_loss, 1),
        'layers': dict(layer_counts),

        # BUY/SELL bias
        'buy_pct': round(buy_pct, 1),
        'sell_pct': round(sell_pct, 1),
        'bias': bias,

        # MFE/MAE
        'avg_mfe': round(avg_mfe, 1),
        'avg_mae': round(avg_mae, 1),
        'avg_mfe_pips': round(avg_mfe_pips, 1),
        'avg_mae_pips': round(avg_mae_pips, 1),
        'mfe_mae_ratio': round(mfe_mae_ratio, 2),
        'suggest_tp': suggest_tp,
        'suggest_sl': suggest_sl,

        # Time insights
        'best_day': best_day,
        'worst_day': worst_day,
    }


# ─── Ranking Engine ───

def compute_percentile_ranks_v2(all_metrics, dimension_key, reverse=False):
    """
    Compute percentile rank for a dimension across all Signal×CCY×Type.

    Args:
        all_metrics: list of dicts with raw metric values
        dimension_key: key to rank on (e.g. 'wr_raw', 'pf_raw')
        reverse: if True, lower values rank higher (for DD, Martin)

    Returns:
        dict mapping (signal_id, symbol, type) → percentile score (0-100)
    """
    # Filter out red cards for ranking
    valid = [(m['signal_id'], m['symbol'], m['type'], m[dimension_key])
             for m in all_metrics if not m['red_card']]

    if len(valid) <= 1:
        result = {}
        for sid, sym, typ, val in valid:
            result[(sid, sym, typ)] = 50.0
        return result

    # Sort by dimension value
    valid.sort(key=lambda x: x[3], reverse=not reverse)
    n = len(valid)

    # Compute percentile: (rank - 1) / (N - 1) × 100
    result = {}
    for i, (sid, sym, typ, val) in enumerate(valid):
        pct = i / (n - 1) * 100
        result[(sid, sym, typ)] = round(pct, 2)

    return result


def score_v5_batch(all_metrics):
    """
    Score ALL Signal×CCY pairs together using ranking system.

    Args:
        all_metrics: list of dicts from compute_raw_metrics(),
                     each must also have 'signal_id' and 'symbol'

    Returns:
        list of dicts with v5 scores added
    """
    # Compute percentile ranks for each dimension
    # Key 改为 (signal_id, symbol, type) 三维度
    wr_pcts = compute_percentile_ranks_v2(all_metrics, 'wr_raw', reverse=True)
    pf_pcts = compute_percentile_ranks_v2(all_metrics, 'pf_raw', reverse=True)
    dd_pcts = compute_percentile_ranks_v2(all_metrics, 'dd_raw', reverse=False)
    martin_pcts = compute_percentile_ranks_v2(all_metrics, 'martin_raw', reverse=False)

    # Weights (老闆拍板)
    W_WR = 0.15
    W_PF = 0.20
    W_DD = 0.25
    W_MARTIN = 0.40

    results = []
    for m in all_metrics:
        key = (m['signal_id'], m['symbol'], m['type'])

        wr_pct = wr_pcts.get(key, 0)
        pf_pct = pf_pcts.get(key, 0)
        dd_pct = dd_pcts.get(key, 0)
        martin_pct = martin_pcts.get(key, 0)

        if m['red_card']:
            # Red card: still compute but mark
            dde_v5 = 0.0
        else:
            dde_v5 = round(
                wr_pct * W_WR +
                pf_pct * W_PF +
                dd_pct * W_DD +
                martin_pct * W_MARTIN,
                1
            )

        results.append({
            **m,
            'dde_v5': dde_v5,
            'wr_pct': round(wr_pct, 1),
            'pf_pct': round(pf_pct, 1),
            'dd_pct': round(dd_pct, 1),
            'martin_pct': round(martin_pct, 1),
        })

    return results


# ─── Main: Process all signals ───

from config import EA_MAP as EA_MAP_STR
# Convert to int for internal use (scorer uses int signal IDs)
EA_MAP = {ea: [int(s) for s in signals] for ea, signals in EA_MAP_STR.items()}

def get_ea(sid):
    eas = []
    for ea, ids in EA_MAP.items():
        if int(sid) in ids:
            eas.append(ea)
    return eas if eas else ['UNK']


def run_v5_scoring():
    """Main entry: load all CSVs, compute raw metrics, batch score."""
    SAMPLES = Path(__file__).parent / 'samples'
    DOWNLOADS = Path(__file__).parent / 'downloads'
    OUTPUT = Path(__file__).parent / 'output'

    lot_mapping = load_lot_mapping()
    print(f"📦 Lot mapping loaded: {len(lot_mapping)} signals")

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

    print(f"📄 CSV signals: {len(all_csvs)}")

    # Step 1: Compute raw metrics for all Signal×CCY
    all_metrics = []
    for sid, csv_file in sorted(all_csvs.items()):
        eas = get_ea(sid)
        ea_tag = '/'.join(eas)

        trades = read_csv_trades(str(csv_file))
        if not trades:
            continue

        # 按 (symbol, type) 双维度分组 - BUY/SELL分开评分
        by_sym_type = defaultdict(list)
        for t in trades:
            key = (t['symbol'], t['type'])  # (symbol, 'buy'/'sell')
            by_sym_type[key].append(t)

        lot_layers = None
        if sid in lot_mapping and lot_mapping[sid].get('lot_layers'):
            lot_layers = [(lv, lot) for lv, lot in lot_mapping[sid].get('lot_layers', [])]

        for (sym, trade_type), sym_type_trades in by_sym_type.items():
            metrics = compute_raw_metrics(sym_type_trades, lot_layers=lot_layers)
            if metrics is None:
                continue

            metrics['signal_id'] = sid
            metrics['symbol'] = sym
            metrics['type'] = trade_type  # 新增: buy/sell 标识
            metrics['ea'] = ea_tag

            # Layer display string
            layer_names = []
            for ln in sorted(set(metrics['layers'].keys()),
                            key=lambda x: (99 if x == 'L9+' else int(x[1:]))):
                if metrics['layers'].get(ln, 0) > 0:
                    layer_names.append(ln)
            metrics['lv'] = '+'.join(layer_names) if layer_names else '-'

            all_metrics.append(metrics)

    print(f"📊 Raw metrics computed: {len(all_metrics)} Signal×CCY pairs")

    # Step 2: Batch score using ranking
    scored_results = score_v5_batch(all_metrics)

    # Summary
    valid = [r for r in scored_results if not r['red_card']]
    red = [r for r in scored_results if r['red_card']]

    print(f"\n📊 DDE v5 Results (ranking-based):")
    print(f"  Total rows: {len(scored_results)}")
    print(f"  Scored: {len(valid)}")
    print(f"  Red card: {len(red)}")

    if valid:
        scores = [r['dde_v5'] for r in valid]
        print(f"  Score range: {min(scores)} - {max(scores)}")
        print(f"  Average: {round(sum(scores)/len(scores), 1)}")

    # Save to SQLite via db_manager
    from db_manager import save_scores
    batch_id = save_scores(scored_results, version='v5')
    print(f"   Batch ID: {batch_id}")
    # Legacy: also save pickle for backward compat
    try:
        import pickle
        with open('/tmp/dde_v5_data.pkl', 'wb') as f:
            pickle.dump(scored_results, f)
        print(f"   (Legacy pickle also saved)")
    except Exception:
        pass

    # Top 10
    valid.sort(key=lambda x: x['dde_v5'], reverse=True)
    print(f"\n🏆 Top 10 (v5):")
    for r in valid[:10]:
        print(f"  {r['signal_id']} × {r['symbol']:8s} = {r['dde_v5']:5.1f}  "
              f"WR={r['win_rate']:.0f}% PF={r['pf']:.2f} DD={r['max_dd_pips']:.0f} WAL={r['wal']:.2f}  "
              f"[WR%={r['wr_pct']:.0f} PF%={r['pf_pct']:.0f} DD%={r['dd_pct']:.0f} M%={r['martin_pct']:.0f}]")

    print(f"\n💀 Bottom 5 (scored):")
    for r in valid[-5:]:
        print(f"  {r['signal_id']} × {r['symbol']:8s} = {r['dde_v5']:5.1f}  "
              f"WR={r['win_rate']:.0f}% PF={r['pf']:.2f} DD={r['max_dd_pips']:.0f} WAL={r['wal']:.2f}")

    if red:
        print(f"\n🚫 Red cards ({len(red)}):")
        for r in red[:5]:
            print(f"  {r['signal_id']} × {r['symbol']:8s} — {', '.join(r['red_reasons'])}")

    return scored_results


if __name__ == '__main__':
    run_v5_scoring()
