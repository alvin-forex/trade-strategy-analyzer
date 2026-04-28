#!/usr/bin/env python3
"""
Trade Strategy Analyzer - Main Entry Point

Modes:
  fast  — 基礎分析（CSV + SET → 倉位 → 評分 → 統計 → 報告）
  full  — 完整分析（+ 市場數據下載 + 環境分析 + 策略偵測 + Copy Trade 模擬）

Usage:
  python3 main.py --csv data.csv --set config.set
  python3 main.py --csv data.csv --set config.set --mode full
  python3 main.py --csv data.csv --set config.set --mode full --download
"""

import argparse
import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

# Add project dir to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.csv_parser import parse_csv
from src.set_parser import parse_set
from src.position_builder import build_positions
from src.entry_quality import calculate_entry_score, calculate_strategy_score, evaluate_positions
from src.trade_statistics import (
    calculate_overall_stats, calculate_symbol_stats,
    calculate_layer_stats, calculate_time_stats,
    calculate_direction_stats
)
from src.equity_curve import calculate_equity_curve
from src.report_generator import generate_html_report

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def _parse_args():
    parser = argparse.ArgumentParser(description='Trade Strategy Analyzer')
    parser.add_argument('--csv', required=True, help='Path to CSV file')
    parser.add_argument('--set', action='append', required=True, help='Path to SET file(s)')
    parser.add_argument('--output', default=None, help='Output HTML path (default: auto)')
    parser.add_argument('--mode', choices=['fast', 'full'], default='fast',
                        help='Analysis mode: fast (basic) or full (with market data)')
    parser.add_argument('--download', action='store_true',
                        help='Force re-download market data (full mode only)')
    return parser.parse_args()


def _parse_csv_and_set(csv_path, set_paths):
    """Step 1-2: Parse CSV and SET files."""
    logger.info("\n[1] 解析 CSV...")
    df = parse_csv(csv_path)
    logger.info(f"  ✓ {len(df)} 筆交易")

    logger.info("\n[2] 解析 SET...")
    set_params = {}
    for set_file in set_paths:
        params = parse_set(set_file)
        symbol = params.get('basic', {}).get('EA_SYMBOL', 'unknown')
        set_params[symbol] = params
        logger.info(f"  ✓ {set_file} → {symbol}")

    # Merge all SET params for display
    all_params = {}
    for symbol, params in set_params.items():
        all_params.update(params)

    return df, all_params


def _build_and_score(trades):
    """Step 3-4: Build positions and calculate scores."""
    logger.info("\n[3] 倉位重構...")
    positions = build_positions(trades)
    logger.info(f"  ✓ {len(positions)} 個倉位")

    logger.info("\n[4] 計算評分...")
    for pos in positions:
        trades_in_pos = pos.get('trades', [])
        l1 = [t for t in trades_in_pos if t.get('layer', 0) == 1]
        if l1:
            entry_result = calculate_entry_score(pos)
            pos['entry_score'] = entry_result['score']
            strategy_result = calculate_strategy_score(pos)
            pos['strategy_score'] = strategy_result['score']
            pos['final_score'] = pos['entry_score'] * 0.4 + pos['strategy_score'] * 0.6
        else:
            pos['entry_score'] = 0
            pos['strategy_score'] = 0
            pos['final_score'] = 0

    graded = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    for p in positions:
        s = p.get('final_score', 0)
        if s >= 80: graded['A'] += 1
        elif s >= 60: graded['B'] += 1
        elif s >= 40: graded['C'] += 1
        else: graded['D'] += 1
    logger.info(f'  ✓ A:{graded["A"]} B:{graded["B"]} C:{graded["C"]} D:{graded["D"]}')

    return positions


def _load_market_data(positions, force_download=False):
    """Step 5 (full mode): Download market data and enrich positions."""
    from src.market_data import MarketDataProvider
    from src.indicators import compute_indicators, label_all
    from src.context_enricher import enrich_all_cycles
    from src.martin_detector import detect_strategy_type

    logger.info("\n[5] 市場數據 & 環境分析...")

    symbols = list(set(p.get('symbol') for p in positions if p.get('symbol')))
    logger.info(f"  Symbols: {symbols}")

    provider = MarketDataProvider()

    # Date range from trades
    all_dates = []
    for p in positions:
        if p.get('open_time'):
            all_dates.append(p['open_time'])
        if p.get('close_time'):
            all_dates.append(p['close_time'])

    if all_dates:
        trade_start = min(all_dates)
        trade_end = max(all_dates)
    else:
        trade_start = datetime(2026, 2, 19)
        trade_end = datetime(2026, 4, 16)

    timeframes = {
        'W1': {'lookback': 1460, 'label': 'W1'},
        'D1': {'lookback': 300, 'label': 'D1'},
        'H4': {'lookback': 150, 'label': 'H4'},
        'M5': {'lookback': 14, 'label': 'M5'},
    }

    market_data = {}
    for sym in symbols:
        market_data[sym] = {}
        for tf_name, tf_cfg in timeframes.items():
            start = trade_start - timedelta(days=tf_cfg['lookback'])
            end = trade_end + timedelta(days=7)
            try:
                df = provider.download(sym, tf_name, start, end, force=force_download)
                if df is not None and not df.empty:
                    df = compute_indicators(df)
                    df = label_all(df, tf_name)
                    market_data[sym][tf_name] = df
                    logger.info(f"  {sym}/{tf_name}: {len(df)} bars ✓")
                else:
                    logger.warning(f"  {sym}/{tf_name}: no data")
            except Exception as e:
                logger.error(f"  {sym}/{tf_name}: {e}")

    # Enrich positions with market context
    positions = enrich_all_cycles(positions, market_data)

    return positions, market_data


def _run_copy_trade_sim(positions, market_data):
    """Step 7 (full mode): Copy trade simulation."""
    from src.copy_trade_sim import simulate_all_cycles, generate_copy_trade_summary

    logger.info("\n[7] Copy Trade 模擬...")
    results = []
    summary = {}
    try:
        results = simulate_all_cycles(positions, market_data)
        if results:
            summary = generate_copy_trade_summary(results)
            triggered = sum(1 for r in results if r.get('triggered'))
            logger.info(f"  ✓ {len(results)} simulations, {triggered} triggered")
        else:
            logger.warning("  No results (M5 data may be missing)")
    except Exception as e:
        logger.warning(f"  Copy trade sim skipped: {e}")

    return results, summary


def _compute_market_context_stats(positions):
    """Compute win rate / P&L by market context dimensions."""
    dims = ['D1_adx_regime', 'D1_trend', 'D1_atr_pct_bucket', 'D1_rsi_bucket']
    results = {}

    for dim in dims:
        buckets = {}
        for p in positions:
            ctx = p.get('market_context', {})
            val = ctx.get(dim, 'UNKNOWN')
            if val is None:
                val = 'UNKNOWN'
            if val not in buckets:
                buckets[val] = {'wins': 0, 'losses': 0, 'pl': [], 'layers': [], 'hold': []}

            net = p.get('net_profit', 0) or 0
            if net > 0:
                buckets[val]['wins'] += 1
            else:
                buckets[val]['losses'] += 1
            buckets[val]['pl'].append(net)
            buckets[val]['layers'].append(p.get('layer_count', 0))
            buckets[val]['hold'].append(p.get('holding_time_hours', 0) or 0)

        dim_results = []
        for val, b in sorted(buckets.items()):
            total = b['wins'] + b['losses']
            dim_results.append({
                'label': val,
                'count': total,
                'win_rate': b['wins'] / total * 100 if total else 0,
                'avg_pl': np.mean(b['pl']) if b['pl'] else 0,
                'avg_layers': np.mean(b['layers']) if b['layers'] else 0,
                'avg_hold': np.mean(b['hold']) if b['hold'] else 0,
            })
        results[dim] = dim_results

    # RSI bucket
    rsi_buckets = {'<30': [], '30-50': [], '50-70': [], '>70': []}
    for p in positions:
        ctx = p.get('market_context', {})
        rsi = ctx.get('D1_rsi', None)
        if rsi is None:
            continue
        if rsi < 30: bucket = '<30'
        elif rsi < 50: bucket = '30-50'
        elif rsi < 70: bucket = '50-70'
        else: bucket = '>70'
        rsi_buckets[bucket].append(p)

    rsi_results = []
    for bucket, items in rsi_buckets.items():
        if not items:
            continue
        total = len(items)
        wins = sum(1 for p in items if (p.get('net_profit', 0) or 0) > 0)
        rsi_results.append({
            'label': f'RSI {bucket}',
            'count': total,
            'win_rate': wins / total * 100,
            'avg_pl': np.mean([p.get('net_profit', 0) or 0 for p in items]),
            'avg_layers': np.mean([p.get('layer_count', 0) for p in items]),
            'avg_hold': np.mean([p.get('holding_time_hours', 0) or 0 for p in items]),
        })
    results['D1_rsi_bucket'] = rsi_results

    # ATR bucket
    atr_buckets = {'Low(<25)': [], 'Med(25-75)': [], 'High(>75)': []}
    for p in positions:
        ctx = p.get('market_context', {})
        atr_pct = ctx.get('D1_atr_pct', None)
        if atr_pct is None:
            continue
        if atr_pct < 25: bucket = 'Low(<25)'
        elif atr_pct < 75: bucket = 'Med(25-75)'
        else: bucket = 'High(>75)'
        atr_buckets[bucket].append(p)

    atr_results = []
    for bucket, items in atr_buckets.items():
        if not items:
            continue
        total = len(items)
        wins = sum(1 for p in items if (p.get('net_profit', 0) or 0) > 0)
        atr_results.append({
            'label': f'ATR {bucket}',
            'count': total,
            'win_rate': wins / total * 100,
            'avg_pl': np.mean([p.get('net_profit', 0) or 0 for p in items]),
            'avg_layers': np.mean([p.get('layer_count', 0) for p in items]),
            'avg_hold': np.mean([p.get('holding_time_hours', 0) or 0 for p in items]),
        })
    results['D1_atr_pct_bucket'] = atr_results

    return results


def main():
    args = _parse_args()
    mode = args.mode
    is_full = mode == 'full'

    logger.info("=" * 60)
    logger.info(f"🦀 Trade Strategy Analyzer — mode={mode}")
    logger.info("=" * 60)
    logger.info(f"  CSV: {args.csv}")
    logger.info(f"  SET: {args.set}")

    # ── Steps 1-2: Parse CSV + SET ──
    trades, all_params = _parse_csv_and_set(args.csv, args.set)

    # ── Steps 3-4: Build positions + Score ──
    positions = _build_and_score(trades)

    # ── Extra: Strategy detection (full mode) ──
    strategy_info = {}
    if is_full:
        from src.martin_detector import detect_strategy_type
        strategy_info = detect_strategy_type(all_params)
        logger.info(f"\n  Strategy: {strategy_info.get('strategy_type', 'UNKNOWN')}")
        logger.info(f"  Martingale: {strategy_info.get('is_martingale', False)}")

    # ── Steps 5-6 (full mode): Market data + Copy trade sim ──
    market_data = {}
    copy_trade_raw = []
    copy_trade_summary = {}

    if is_full:
        positions, market_data = _load_market_data(positions, force_download=args.download)

    # ── Compute statistics ──
    step_n = 6 if not is_full else 8
    logger.info(f"\n[{step_n}] 計算統計...")
    stats = {
        'overall': calculate_overall_stats(positions),
        'by_symbol': calculate_symbol_stats(positions),
        'by_layer': calculate_layer_stats(positions),
        'by_time': calculate_time_stats(positions),
        'by_direction': calculate_direction_stats(positions),
    }
    if is_full:
        stats['strategy_info'] = strategy_info

    if is_full and market_data:
        copy_trade_raw, copy_trade_summary = _run_copy_trade_sim(positions, market_data)
        stats['market_context'] = _compute_market_context_stats(positions)
        stats['copy_trade'] = copy_trade_summary
        stats['copy_trade_raw'] = copy_trade_raw

    # ── Equity curve ──
    curve = calculate_equity_curve(positions)
    logger.info(f"  ✓ {len(curve)} 數據點")

    # ── Generate report ──
    step_n += 1
    logger.info(f"\n[{step_n}] 生成報告...")

    csv_name = os.path.basename(args.csv)
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = str(BASE_DIR / 'output' / f'report_{timestamp}.html')

    generate_html_report(stats, positions, all_params, output_path, csv_name)

    # ── Print summary ──
    o = stats['overall']
    print(f"\n{'='*50}")
    print(f"🦀 分析總結 ({mode})")
    print(f"{'='*50}")
    print(f"  倉位: {o.get('total_positions', 0)}  勝率: {o.get('win_rate', 0):.1f}%  PF: {o.get('profit_factor', 0):.2f}")
    print(f"  總盈虧: ${o.get('total_profit', 0):.2f}  Max DD: ${o.get('max_dd', 0):.2f}")
    print(f"  Sharpe: {o.get('sharpe_ratio', 0):.2f}  Calmar: {o.get('calmar_ratio', 0):.2f}")

    if strategy_info:
        print(f"\n  Strategy: {strategy_info.get('strategy_type', '?')}")
        if strategy_info.get('is_martingale'):
            print(f"  ⚠️ Martingale: lotExp={strategy_info.get('lot_exp', '?')}")

    if copy_trade_raw:
        triggered = sum(1 for r in copy_trade_raw if r.get('triggered'))
        print(f"\n  📊 Copy Trade: {triggered}/{len(copy_trade_raw)} triggered")

    print(f"\n✅ 報告：{output_path}")


if __name__ == '__main__':
    main()
