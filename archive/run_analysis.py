#!/usr/bin/env python3
"""
Comprehensive Trade Analysis — end-to-end pipeline
Usage: python3 run_analysis.py [--csv FILE] [--set FILE] [--download]
"""

import os
import sys
import argparse
import logging
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

# Add parent dir to path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.csv_parser import parse_csv
from src.set_parser import parse_set
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
from src.copy_trade_sim import simulate_copy_trade, simulate_all_cycles, generate_copy_trade_summary

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_CSV = '/mnt/c/Users/Alvin/Downloads/forex-forest-signals-page-32278.csv'
OUTPUT_DIR = BASE_DIR / 'output'


def run(csv_path: str, set_path: str = None, download: bool = False):
    logger.info("=" * 60)
    logger.info("🦀 Trade Strategy Analyzer — Comprehensive Analysis")
    logger.info("=" * 60)

    # ── 1. Parse CSV ──
    logger.info("\n[1/8] Parsing trade data...")
    trades = parse_csv(csv_path)
    logger.info(f"  {len(trades)} trades loaded")

    # ── 2. Parse SET (optional) ──
    set_params = {}
    strategy_info = {}
    if set_path and os.path.exists(set_path):
        logger.info("\n[2/8] Parsing SET file...")
        set_params = parse_set(set_path)
        strategy_info = detect_strategy_type(set_params)
        logger.info(f"  Strategy: {strategy_info.get('strategy_type', 'UNKNOWN')}")
        logger.info(f"  Martingale: {strategy_info.get('is_martingale', False)}")
    else:
        logger.info("\n[2/8] No SET file, skipping strategy detection")

    # ── 3. Build Positions ──
    logger.info("\n[3/8] Building position cycles...")
    positions = build_positions(trades)
    logger.info(f"  {len(positions)} cycles")

    # ── 4. Market Data ──
    logger.info("\n[4/8] Loading market data...")
    symbols = list(set(p.get('symbol') for p in positions if p.get('symbol')))
    logger.info(f"  Symbols: {symbols}")

    provider = MarketDataProvider()
    
    # Determine date range from trades
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

    # Download all timeframes: W1, D1, H4, M5
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
                df = provider.download(sym, tf_name, start, end, force=download)
                if df is not None and not df.empty:
                    df = compute_indicators(df)
                    df = label_all(df, tf_name)
                    market_data[sym][tf_name] = df
                    logger.info(f"  {sym}/{tf_name}: {len(df)} bars ✓")
                else:
                    logger.warning(f"  {sym}/{tf_name}: no data")
            except Exception as e:
                logger.error(f"  {sym}/{tf_name}: {e}")

    # ── 5. Enrich with Context ──
    logger.info("\n[5/8] Enriching with market context...")
    positions = enrich_all_cycles(positions, market_data)
    
    # ── 6. Score positions ──
    logger.info("\n[6/8] Scoring positions...")
    positions = evaluate_positions(positions)
    
    # ── 7. Statistics ──
    logger.info("\n[7/8] Computing statistics...")
    stats = {
        'overall': calculate_overall_stats(positions),
        'by_symbol': calculate_symbol_stats(positions),
        'by_layer': calculate_layer_stats(positions),
        'by_time': calculate_time_stats(positions),
        'by_direction': calculate_direction_stats(positions),
    }

    # ── 8. Copy Trade Simulation ──
    copy_sim_results = []
    copy_sim_summary = {}
    try:
        logger.info("\n[8/8] Running copy trade simulation...")
        # Use simulate_all_cycles which properly passes M5 data
        copy_sim_results = simulate_all_cycles(positions, market_data)
        if copy_sim_results:
            copy_sim_summary = generate_copy_trade_summary(copy_sim_results)
            triggered = sum(1 for r in copy_sim_results if r.get('triggered'))
            logger.info(f"  {len(copy_sim_results)} simulations, {triggered} triggered")
        else:
            logger.warning("  No copy trade results (M5 data may be missing)")
    except Exception as e:
        logger.warning(f"Copy trade sim skipped: {e}")

    # ── Generate Report ──
    csv_name = os.path.basename(csv_path)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_path = OUTPUT_DIR / f'report_{timestamp}.html'

    # Add market context section to stats
    stats['market_context'] = _compute_market_context_stats(positions)
    stats['copy_trade'] = copy_sim_summary
    stats['copy_trade_raw'] = copy_sim_results
    stats['strategy_info'] = strategy_info

    generate_html_report(stats, positions, set_params, str(report_path), csv_name)
    logger.info(f"\n✅ Report: {report_path}")

    # Print summary
    _print_summary(positions, stats, strategy_info, copy_sim_results)

    return report_path


def _compute_market_context_stats(positions: list) -> dict:
    """Analyze win rate / P&L by market context dimensions."""
    import numpy as np
    
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
    
    # Add RSI bucket
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


def _print_summary(positions, stats, strategy_info, copy_sim):
    overall = stats.get('overall', {})
    print(f"\n{'='*50}")
    print(f"🦀 分析總結")
    print(f"{'='*50}")
    print(f"  Cycles: {len(positions)}")
    print(f"  Win Rate: {overall.get('win_rate', 0):.1f}%")
    print(f"  Total P/L: ${overall.get('total_profit', 0):.2f}")
    print(f"  Profit Factor: {overall.get('profit_factor', 0):.2f}")
    print(f"  Avg Layers: {overall.get('avg_layers', 0):.1f}")
    print(f"  Avg Hold: {overall.get('avg_holding_time_hours', 0):.0f}h")
    print(f"  Max DD: ${overall.get('max_dd', 0):.2f}")
    
    if strategy_info:
        print(f"\n  Strategy: {strategy_info.get('strategy_type', '?')}")
        if strategy_info.get('is_martingale'):
            print(f"  ⚠️ Martingale detected: lotExp={strategy_info.get('lot_exp', '?')}")
    
    if copy_sim:
        print(f"\n  📊 Copy Trade Simulation: {len(copy_sim)} results")
        if isinstance(copy_sim, list):
            triggered = sum(1 for r in copy_sim if r.get('triggered'))
            print(f"    Triggered: {triggered}/{len(copy_sim)}")
        elif isinstance(copy_sim, dict):
            for delay, result in sorted(copy_sim.items()):
                if isinstance(result, dict) and 'avg_pl' in result:
                    print(f"    {delay}: Avg P/L=${result['avg_pl']:.2f}, "
                          f"Triggered={result.get('triggered', '?')}/{result.get('total', '?')}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Trade Strategy Analysis')
    parser.add_argument('--csv', default=DEFAULT_CSV, help='Path to CSV file')
    parser.add_argument('--set', default=None, help='Path to .set file')
    parser.add_argument('--download', action='store_true', help='Force re-download market data')
    args = parser.parse_args()

    report = run(args.csv, args.set, args.download)
    print(f"\n📄 Report: {report}")
