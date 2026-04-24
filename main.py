#!/usr/bin/env python3
"""
Trade Strategy Analyzer - Main Entry Point
"""

import argparse
import os
import sys

# Add parent dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.csv_parser import parse_csv
from src.set_parser import parse_set
from src.position_builder import build_positions
from src.entry_quality import calculate_entry_score, calculate_strategy_score
from src.statistics import (
    calculate_overall_stats, calculate_symbol_stats,
    calculate_layer_stats, calculate_time_stats,
    calculate_direction_stats
)
from src.equity_curve import generate_equity_curve
from src.report_generator import generate_html_report


def main():
    parser = argparse.ArgumentParser(description='Trade Strategy Analyzer')
    parser.add_argument('--csv', required=True, help='Path to CSV file')
    parser.add_argument('--set', action='append', required=True, help='Path to SET file(s)')
    parser.add_argument('--output', default='output/report.html', help='Output HTML path')
    args = parser.parse_args()

    print(f"📊 Trade Strategy Analyzer")
    print(f"   CSV: {args.csv}")
    print(f"   SET: {args.set}")

    # 1. Parse CSV
    print("\n[1/7] 解析 CSV...")
    df = parse_csv(args.csv)
    print(f"   ✓ {len(df)} 筆交易")

    # 2. Parse SET files
    print("\n[2/7] 解析 SET...")
    set_params = {}
    for set_file in args.set:
        params = parse_set(set_file)
        symbol = params.get('basic', {}).get('EA_SYMBOL', 'unknown')
        set_params[symbol] = params
        print(f"   ✓ {set_file} → {symbol}")

    # 3. Build positions
    print("\n[3/7] 倉位重構...")
    positions = build_positions(df)
    print(f"   ✓ {len(positions)} 個倉位")

    # 4. Calculate scores
    print("\n[4/7] 計算評分...")
    for pos in positions:
        trades = pos.get('trades', [])
        l1 = [t for t in trades if t.get('layer', 0) == 1]
        if l1:
            pos['entry_score'] = calculate_entry_score(l1[0], pos)
            pos['strategy_score'] = calculate_strategy_score(pos)
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
    print(f"   ✓ A:{graded['A']} B:{graded['B']} C:{graded['C']} D:{graded['D']}")

    # 5. Calculate statistics
    print("\n[5/7] 計算統計...")
    stats = {
        'overall': calculate_overall_stats(positions),
        'by_symbol': calculate_symbol_stats(positions),
        'by_layer': calculate_layer_stats(positions),
        'by_time': calculate_time_stats(positions),
        'by_direction': calculate_direction_stats(positions),
    }
    print(f"   ✓ 勝率: {stats['overall'].get('win_rate', 0):.1f}%  PF: {stats['overall'].get('profit_factor', 0):.2f}")

    # 6. Equity curve
    print("\n[6/7] 收益曲線...")
    curve = generate_equity_curve(positions)
    print(f"   ✓ {len(curve)} 個數據點")

    # 7. Generate report
    print("\n[7/7] 生成報告...")
    
    # Merge all SET params for display
    all_params = {}
    for symbol, params in set_params.items():
        all_params.update(params)
    
    csv_name = os.path.basename(args.csv)
    generate_html_report(stats, positions, all_params, args.output, csv_name)

    print(f"\n✅ 完成！報告：{args.output}")
    
    # Print summary
    o = stats['overall']
    print(f"\n📊 摘要:")
    print(f"   倉位: {o.get('total_positions', 0)}  勝率: {o.get('win_rate', 0):.1f}%  PF: {o.get('profit_factor', 0):.2f}")
    print(f"   總盈虧: ${o.get('total_profit', 0):.2f}  Max DD: ${o.get('max_dd', 0):.2f}")
    print(f"   Sharpe: {o.get('sharpe_ratio', 0):.2f}  Calmar: {o.get('calmar_ratio', 0):.2f}")


if __name__ == '__main__':
    main()
