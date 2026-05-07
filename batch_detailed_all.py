#!/usr/bin/env python3
"""
Batch generate detailed comparison reports for all remaining signals.
Step 1: Download CSV from AlgoForest
Step 2: Generate detailed comparison HTML using generate_all_levels_from_csv logic
"""
import asyncio
import sys
import os
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

# 51 signals that need detailed reports
TODO_SIGNALS = [
    '10437','106','10864','11889','11984','12173','12962','13461','13790','13798',
    '13863','14158','14592','1470','14724','16538','16596','16698','17547','17823',
    '1980','19849','20805','20846','21698','22200','22278','23617','25260','25668',
    '25830','30359','31593','31781','32278','32541','32719','3291','33101','34259',
    '34574','36338','36397','5001','5275','537','5566','5636','7919','8325'
]

from algoforest_scraper import download_signal_csv
from generate_all_levels_from_csv import (
    analyze_trades_from_csv, analyze_by_levels, generate_html_report
)

SAMPLES_DIR = Path(__file__).parent / 'samples'
OUTPUT_DIR = Path(__file__).parent / 'output'

LEVEL_RANGES = {
    'L1': (0, 50),
    'L2': (50, 100),
    'L3': (100, 150),
    'L4+': (150, float('inf'))
}

async def download_all():
    """Download CSVs with rate limiting"""
    results = {'success': [], 'failed': []}
    
    for i, sid in enumerate(TODO_SIGNALS):
        csv_path = SAMPLES_DIR / f'forex-forest-signals-page-{sid}.csv'
        
        if csv_path.exists():
            print(f"[{i+1}/{len(TODO_SIGNALS)}] ✅ CSV exists for {sid}")
            results['success'].append(sid)
            continue
        
        print(f"[{i+1}/{len(TODO_SIGNALS)}] 📥 Downloading CSV for signal {sid}...")
        try:
            result = await download_signal_csv(str(sid), str(csv_path))
            if result:
                results['success'].append(sid)
                print(f"  ✅ Downloaded {sid}")
            else:
                results['failed'].append(sid)
                print(f"  ❌ Failed {sid}")
        except Exception as e:
            results['failed'].append(sid)
            print(f"  ❌ Error for {sid}: {e}")
        
        # Rate limit between downloads
        if i < len(TODO_SIGNALS) - 1:
            await asyncio.sleep(3)
    
    return results

def process_signal(csv_path):
    """Process a single CSV file and return (all_currency_data, level_ranges)"""
    trades = analyze_trades_from_csv(str(csv_path))
    if not trades:
        return None
    
    # Group by currency
    currency_data = defaultdict(list)
    for trade in trades:
        symbol = trade.get('symbol', '')
        if symbol:
            currency_data[symbol].append(trade)
    
    all_currency_data = {}
    for currency, currency_trades in currency_data.items():
        total_trades = len(currency_trades)
        win_trades = sum(1 for t in currency_trades if t.get('net_profit', 0) > 0)
        win_rate = win_trades / total_trades if total_trades > 0 else 0
        total_profit = sum(t.get('net_profit', 0) for t in currency_trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        avg_tp = sum(t.get('tp', 0) for t in currency_trades) / total_trades if total_trades > 0 else 0
        avg_sl = sum(t.get('sl', 0) for t in currency_trades) / total_trades if total_trades > 0 else 0
        
        stats = {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'avg_tp': avg_tp,
            'avg_sl': avg_sl
        }
        
        levels = analyze_by_levels(currency_trades, LEVEL_RANGES)
        
        all_currency_data[currency] = {
            'stats': stats,
            'levels': levels
        }
    
    return all_currency_data

def generate_reports(signal_ids):
    """Generate detailed comparison HTML for each signal"""
    results = {'success': [], 'failed': []}
    
    for i, sid in enumerate(signal_ids):
        csv_path = SAMPLES_DIR / f'forex-forest-signals-page-{sid}.csv'
        output_path = OUTPUT_DIR / f'detailed_comparison_all_levels_forex-forest-signals-page-{sid}.html'
        
        if not csv_path.exists():
            print(f"[{i+1}/{len(signal_ids)}] ⚠️ No CSV for {sid}, skipping")
            results['failed'].append(sid)
            continue
        
        if output_path.exists() and output_path.stat().st_size > 10000:
            print(f"[{i+1}/{len(signal_ids)}] ✅ Report exists for {sid}")
            results['success'].append(sid)
            continue
        
        print(f"[{i+1}/{len(signal_ids)}] 📊 Generating report for {sid}...")
        try:
            all_currency_data = process_signal(csv_path)
            if not all_currency_data:
                print(f"  ⚠️ No trades in CSV for {sid}")
                results['failed'].append(sid)
                continue
            
            html = generate_html_report(csv_path, all_currency_data, LEVEL_RANGES)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            
            size_kb = len(html) / 1024
            n_pairs = len(all_currency_data)
            print(f"  ✅ {sid}: {n_pairs} pairs, {size_kb:.0f}KB → {output_path.name}")
            results['success'].append(sid)
        except Exception as e:
            print(f"  ❌ Error for {sid}: {e}")
            import traceback
            traceback.print_exc()
            results['failed'].append(sid)
    
    return results

async def main():
    print("=" * 60)
    print("🦀 Batch Detailed Report Generator")
    print(f"   Total signals to process: {len(TODO_SIGNALS)}")
    print("=" * 60)
    
    # Step 1: Download CSVs
    print("\n📥 Step 1: Downloading CSV files...")
    dl_results = await download_all()
    print(f"\n   Downloaded: {len(dl_results['success'])}, Failed: {len(dl_results['failed'])}")
    
    if dl_results['failed']:
        print(f"   Failed: {dl_results['failed']}")
    
    # Step 2: Generate reports
    print("\n📊 Step 2: Generating detailed comparison reports...")
    gen_results = generate_reports(dl_results['success'])
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 FINAL SUMMARY")
    print("=" * 60)
    print(f"  ✅ Reports generated: {len(gen_results['success'])}")
    print(f"  ❌ Failed: {len(gen_results['failed'])}")
    if gen_results['failed']:
        print(f"  Failed IDs: {gen_results['failed']}")
    
    # Total count
    total_detailed = len(list(OUTPUT_DIR.glob('detailed_comparison_all_levels_*.html')))
    print(f"\n  📂 Total detailed reports in output/: {total_detailed}")
    print()

if __name__ == '__main__':
    asyncio.run(main())
