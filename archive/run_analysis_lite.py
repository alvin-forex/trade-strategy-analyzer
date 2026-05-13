#!/usr/bin/env python3
"""
Lite version: skip M5 data / copy trade sim to avoid OOM on large signal sets.
"""
import os
import sys
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.csv_parser import parse_csv
from src.position_builder import build_positions
from src.entry_quality import evaluate_positions
from src.statistics import (
    calculate_overall_stats, calculate_symbol_stats,
    calculate_layer_stats, calculate_time_stats,
    calculate_direction_stats
)
from src.report_generator import generate_html_report
from src.market_data import MarketDataProvider
from src.indicators import compute_indicators, label_all
from src.context_enricher import enrich_all_cycles
from src.martin_detector import detect_strategy_type

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

OUTPUT_DIR = BASE_DIR / 'output'


def run_lite(csv_path: str, set_path: str = None):
    logger.info("=" * 60)
    logger.info("🦀 Trade Strategy Analyzer — LITE (no M5/copy-trade)")
    logger.info("=" * 60)

    # 1. Parse CSV
    logger.info("\n[1/6] Parsing trade data...")
    trades = parse_csv(csv_path)
    logger.info(f"  {len(trades)} trades loaded")

    # 2. Parse SET (optional)
    set_params = {}
    strategy_info = {}
    if set_path and os.path.exists(set_path):
        logger.info("\n[2/6] Parsing SET file...")
        set_params = parse_set(set_path)
        strategy_info = detect_strategy_type(set_params)
    else:
        logger.info("\n[2/6] No SET file, skipping")

    # 3. Build Positions
    logger.info("\n[3/6] Building position cycles...")
    positions = build_positions(trades)
    logger.info(f"  {len(positions)} cycles")

    # 4. Market Data — W1, D1, H4 only (skip M5)
    logger.info("\n[4/6] Loading market data (W1/D1/H4)...")
    symbols = list(set(p.get('symbol') for p in positions if p.get('symbol')))
    logger.info(f"  Symbols: {symbols}")

    provider = MarketDataProvider()
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
        'W1': {'lookback': 1460},
        'D1': {'lookback': 300},
        'H4': {'lookback': 150},
    }

    market_data = {}
    for i, sym in enumerate(symbols):
        market_data[sym] = {}
        for tf_name, tf_cfg in timeframes.items():
            start = trade_start - timedelta(days=tf_cfg['lookback'])
            end = trade_end + timedelta(days=7)
            try:
                df = provider.download(sym, tf_name, start, end, force=False)
                if df is not None and not df.empty:
                    df = compute_indicators(df)
                    df = label_all(df, tf_name)
                    market_data[sym][tf_name] = df
                    logger.info(f"  [{i+1}/{len(symbols)}] {sym}/{tf_name}: {len(df)} bars ✓")
                else:
                    logger.warning(f"  {sym}/{tf_name}: no data")
            except Exception as e:
                logger.error(f"  {sym}/{tf_name}: {e}")

    # Free the provider / download cache
    del provider

    # 5. Enrich + Score
    logger.info("\n[5/6] Enriching + scoring...")
    positions = enrich_all_cycles(positions, market_data)
    positions = evaluate_positions(positions)

    # 6. Statistics
    logger.info("\n[6/6] Computing statistics...")
    stats = {
        'overall': calculate_overall_stats(positions),
        'by_symbol': calculate_symbol_stats(positions),
        'by_layer': calculate_layer_stats(positions),
        'by_time': calculate_time_stats(positions),
        'by_direction': calculate_direction_stats(positions),
    }

    # Market context stats
    stats['market_context'] = _compute_market_context_stats(positions)
    stats['copy_trade'] = {}
    stats['copy_trade_raw'] = []
    stats['strategy_info'] = strategy_info

    # Generate Report
    csv_name = os.path.basename(csv_path)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = OUTPUT_DIR / f'report_{timestamp}.html'

    generate_html_report(stats, positions, set_params, str(report_path), csv_name)
    logger.info(f"\n✅ Report: {report_path}")

    _print_summary(positions, stats, strategy_info)
    return report_path


def _compute_market_context_stats(positions):
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
    return results


def _print_summary(positions, stats, strategy_info):
    overall = stats.get('overall', {})
    print(f"\n{'='*50}")
    print(f"🦀 分析總結 (Signal #8325)")
    print(f"{'='*50}")
    print(f"  Cycles: {len(positions)}")
    print(f"  Win Rate: {overall.get('win_rate', 0):.1f}%")
    print(f"  Total P/L: ${overall.get('total_profit', 0):.2f}")
    print(f"  Profit Factor: {overall.get('profit_factor', 0):.2f}")
    print(f"  Avg Layers: {overall.get('avg_layers', 0):.1f}")
    print(f"  Avg Hold: {overall.get('avg_holding_time_hours', 0):.0f}h")
    print(f"  Max DD: ${overall.get('max_dd', 0):.2f}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--csv', required=True)
    parser.add_argument('--set', default=None)
    args = parser.parse_args()
    report = run_lite(args.csv, args.set)
    print(f"\n📄 Report: {report}")
