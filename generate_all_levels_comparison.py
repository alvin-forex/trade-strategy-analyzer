#!/usr/bin/env python3
"""
Generate detailed comparison report for ALL LEVELS (L1, L2, L3, L4+) with compact layout
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Database path
DB_PATH = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/data/analysis_history.db"

# Output directory
OUTPUT_DIR = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer/output")
OUTPUT_DIR.mkdir(exist_ok=True)

def get_latest_signal():
    """Get the latest signal from the database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, signal_id, created_at, raw_stats
        FROM analyses
        ORDER BY created_at DESC
        LIMIT 1
    """)
    row = cursor.fetchone()
    conn.close()
    return row

def analyze_copy_on_profit(trades, wait_pips_levels, level_name, level_range):
    """
    Analyze Copy on Profit strategy for a specific level
    
    Args:
        trades: List of trades for this level
        wait_pips_levels: List of wait pips to test [5, 10, 15, 20]
        level_name: Level name (L1, L2, L3, L4+)
        level_range: (min_profit, max_profit) for this level
    """
    results = {}
    
    min_profit, max_profit = level_range
    level_trades = [t for t in trades if min_profit <= t.get('net_profit', 0) < max_profit]
    
    for wait_pips in wait_pips_levels:
        triggered_count = 0
        total_profit_after_trigger = 0
        win_after_trigger = 0
        
        for trade in level_trades:
            net_profit = trade.get('net_profit', 0)
            
            # Assume pip movement = net_profit / 10 (simplified)
            profit_pips = net_profit / 10
            
            if profit_pips >= wait_pips:
                triggered_count += 1
                total_profit_after_trigger += net_profit
                win_after_trigger += 1
        
        if triggered_count > 0:
            trigger_rate = triggered_count / len(level_trades) if len(level_trades) > 0 else 0
            avg_profit_after = total_profit_after_trigger / triggered_count
            win_rate_after = win_after_trigger / triggered_count if triggered_count > 0 else 0
        else:
            trigger_rate = 0
            avg_profit_after = 0
            win_rate_after = 0
        
        # Calculate score
        trigger_score = min(trigger_rate * 100, 100)
        profit_score = min(avg_profit_after / 50 * 100, 100)
        win_score = win_rate_after * 100
        
        # Weighted score: trigger 40%, profit 40%, win 20%
        weighted_score = (trigger_score * 0.4) + (profit_score * 0.4) + (win_score * 0.2)
        
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
            'total_trades': len(level_trades),
            'triggered_count': triggered_count,
            'trigger_rate': trigger_rate,
            'avg_profit_after': avg_profit_after,
            'win_rate_after': win_rate_after,
            'weighted_score': weighted_score,
            'rating': rating,
            'rating_class': rating_class,
            'score_details': {
                'trigger_rate': f"{trigger_rate:.2%} × 40% = {trigger_score:.1f}",
                'avg_profit': f"${avg_profit_after:.2f} / $50 × 40% = {profit_score:.1f}",
                'win_rate': f"{win_rate_after:.2%} × 20% = {win_score:.1f}",
                'total': f"{weighted_score:.1f}"
            }
        }
    
    return results

def analyze_copy_on_lose(trades, wait_pips_levels, level_name, level_range):
    """
    Analyze Copy on Lose strategy for a specific level
    
    Args:
        trades: List of trades for this level
        wait_pips_levels: List of wait pips to test [10, 15, 20, 25]
        level_name: Level name (L1, L2, L3, L4+)
        level_range: (min_profit, max_profit) for this level
    """
    results = {}
    
    min_profit, max_profit = level_range
    level_trades = [t for t in trades if min_profit <= t.get('net_profit', 0) < max_profit]
    
    for wait_pips in wait_pips_levels:
        triggered_count = 0
        recovered_count = 0
        total_profit_after_recover = 0
        
        for trade in level_trades:
            net_profit = trade.get('net_profit', 0)
            
            # For lose strategy, check if price moved against then recovered
            # Assume initial movement = -wait_pips (negative)
            # If net_profit > 0, it recovered
            
            # Simplified: check if any trade recovered from negative
            if net_profit > 0:
                triggered_count += 1
                recovered_count += 1
                total_profit_after_recover += net_profit
        
        if triggered_count > 0:
            trigger_rate = triggered_count / len(level_trades) if len(level_trades) > 0 else 0
            recovery_rate = recovered_count / triggered_count if triggered_count > 0 else 0
            avg_profit_after = total_profit_after_recover / recovered_count if recovered_count > 0 else 0
        else:
            trigger_rate = 0
            recovery_rate = 0
            avg_profit_after = 0
        
        # Calculate score
        recovery_score = recovery_rate * 100
        profit_score = min(avg_profit_after / 30 * 100, 100)
        trigger_score = min(trigger_rate * 100, 100)
        
        # Weighted score: recovery 40%, profit 40%, trigger 20%
        weighted_score = (recovery_score * 0.4) + (profit_score * 0.4) + (trigger_score * 0.2)
        
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
            'total_trades': len(level_trades),
            'triggered_count': triggered_count,
            'trigger_rate': trigger_rate,
            'recovered_count': recovered_count,
            'recovery_rate': recovery_rate,
            'avg_profit_after': avg_profit_after,
            'weighted_score': weighted_score,
            'rating': rating,
            'rating_class': rating_class,
            'score_details': {
                'recovery_rate': f"{recovery_rate:.2%} × 40% = {recovery_score:.1f}",
                'avg_profit': f"${avg_profit_after:.2f} / $30 × 40% = {profit_score:.1f}",
                'trigger_rate': f"{trigger_rate:.2%} × 20% = {trigger_score:.1f}",
                'total': f"{weighted_score:.1f}"
            }
        }
    
    return results

def generate_html_report(signal_id, all_level_results):
    """Generate HTML report for all levels"""
    
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Build currency list
    currency_pairs = list(all_level_results.keys())
    
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
            font-size: 12px;
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
            font-size: 18px;
            margin-bottom: 5px;
            color: #1976d2;
        }}
        
        .subtitle {{
            font-size: 11px;
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
            padding: 10px 15px;
            font-weight: bold;
            font-size: 14px;
        }}
        
        .currency-stats {{
            padding: 10px 15px;
            background: #f8f9fa;
            border-bottom: 1px solid #ddd;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
            gap: 10px;
            font-size: 11px;
        }}
        
        .stat-item {{
            display: flex;
            flex-direction: column;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 10px;
        }}
        
        .stat-value {{
            font-weight: bold;
            font-size: 13px;
            color: #333;
        }}
        
        .level-section {{
            margin: 10px;
            border: 1px solid #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .level-header {{
            background: #e3f2fd;
            padding: 8px 12px;
            font-weight: bold;
            font-size: 12px;
            color: #1976d2;
            border-bottom: 1px solid #e0e0e0;
        }}
        
        .strategy-section {{
            margin: 8px;
        }}
        
        .strategy-header {{
            background: #f5f5f5;
            padding: 6px 10px;
            font-weight: bold;
            font-size: 11px;
            color: #333;
            border-left: 3px solid #1976d2;
            margin-bottom: 5px;
        }}
        
        .comparison-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            background: white;
            border: 1px solid #e0e0e0;
        }}
        
        .comparison-table th {{
            background: #e8eaf6;
            padding: 5px 8px;
            text-align: left;
            font-weight: bold;
            border-bottom: 1px solid #e0e0e0;
            white-space: nowrap;
        }}
        
        .comparison-table td {{
            padding: 4px 8px;
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
            font-size: 9px;
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
            font-size: 10px;
            color: #666;
            text-align: center;
        }}
        
        @media print {{
            body {{
                font-size: 10px;
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
        
        <div class="summary-section" style="margin-bottom: 20px;">
            <h2 style="font-size: 14px; margin-bottom: 10px; color: #1976d2;">📋 Analysis Summary</h2>
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
    for currency in sorted(currency_pairs):
        data = all_level_results[currency]
        stats = data['stats']
        
        total_trades = sum([
            data['levels']['L1']['stats']['count'],
            data['levels']['L2']['stats']['count'],
            data['levels']['L3']['stats']['count'],
            data['levels']['L4+']['stats']['count']
        ])
        
        win_rate = stats['win_rate']
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
    for currency in sorted(currency_pairs):
        data = all_level_results[currency]
        stats = data['stats']
        levels = data['levels']
        
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
                </div>
"""
            
            # Copy on Profit table
            profit_results = level_data['copy_on_profit']
            html += """
                <div class="strategy-section">
                    <div class="strategy-header">🚀 Copy on Profit (Waiting for profit to reach threshold)</div>
                    <table class="comparison-table">
                        <thead>
                            <tr>
                                <th>Wait</th>
                                <th>Trigger Rate</th>
                                <th>Avg After</th>
                                <th>Win After</th>
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
                
                html += f"""
                        <tr class="{row_class}">
                            <td>{wait_pips} pips</td>
                            <td>{result['trigger_rate']:.2%}</td>
                            <td>${result['avg_profit_after']:.2f}</td>
                            <td>{result['win_rate_after']:.2%}</td>
                            <td class="score-cell {result['rating_class']}">{result['weighted_score']:.1f}</td>
                            <td class="score-cell {result['rating_class']}">{result['rating']}</td>
                            <td class="score-details">{result['score_details']['trigger_rate']}<br>{result['score_details']['avg_profit']}<br>{result['score_details']['win_rate']}<br><strong>{result['score_details']['total']}</strong></td>
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
                    <div class="strategy-header">🛡️ Copy on Lose (Waiting for recovery from adverse movement)</div>
                    <table class="comparison-table">
                        <thead>
                            <tr>
                                <th>Wait</th>
                                <th>Trigger Rate</th>
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
                            <td>{result['trigger_rate']:.2%}</td>
                            <td>{result['recovery_rate']:.2%}</td>
                            <td>${result['avg_profit_after']:.2f}</td>
                            <td class="score-cell {result['rating_class']}">{result['weighted_score']:.1f}</td>
                            <td class="score-cell {result['rating_class']}">{result['rating']}</td>
                            <td class="score-details">{result['score_details']['recovery_rate']}<br>{result['score_details']['avg_profit']}<br>{result['score_details']['trigger_rate']}<br><strong>{result['score_details']['total']}</strong></td>
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
            Generated by Trade Strategy Analyzer
        </div>
    </div>
</body>
</html>
"""
    
    return html

def main():
    print("🚀 Starting all-levels comparison analysis...")
    
    # Get latest signal
    row = get_latest_signal()
    if not row:
        print("❌ No signals found in database")
        return
    
    analysis_id, signal_id, created_at, raw_stats = row
    print(f"📊 Latest signal: #{signal_id} (ID: {analysis_id})")
    
    # Parse analysis data
    data = json.loads(raw_stats)
    
    # Level ranges (L1, L2, L3, L4+)
    level_ranges = {
        'L1': (0, 50),
        'L2': (50, 100),
        'L3': (100, 150),
        'L4+': (150, float('inf'))
    }
    
    all_level_results = {}
    
    # Process each currency pair
    for currency, trades in data.items():
        print(f"  🔄 Processing {currency}...")
        
        # Calculate basic stats
        total_trades = len(trades)
        win_trades = sum(1 for t in trades if t.get('net_profit', 0) > 0)
        win_rate = win_trades / total_trades if total_trades > 0 else 0
        total_profit = sum(t.get('net_profit', 0) for t in trades)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        avg_tp = sum(t.get('tp', 0) for t in trades) / total_trades if total_trades > 0 else 0
        avg_sl = sum(t.get('sl', 0) for t in trades) / total_trades if total_trades > 0 else 0
        
        stats = {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'avg_tp': avg_tp,
            'avg_sl': avg_sl
        }
        
        levels = {}
        
        # Process each level
        for level_name, level_range in level_ranges.items():
            min_profit, max_profit = level_range
            level_trades = [t for t in trades if min_profit <= t.get('net_profit', 0) < max_profit]
            
            level_stats = {
                'count': len(level_trades),
                'min_profit': min_profit,
                'max_profit': max_profit
            }
            
            # Copy on Profit analysis
            profit_results = analyze_copy_on_profit(
                trades,
                [5, 10, 15, 20],
                level_name,
                level_range
            )
            
            # Copy on Lose analysis
            lose_results = analyze_copy_on_lose(
                trades,
                [10, 15, 20, 25],
                level_name,
                level_range
            )
            
            levels[level_name] = {
                'stats': level_stats,
                'copy_on_profit': profit_results,
                'copy_on_lose': lose_results
            }
        
        all_level_results[currency] = {
            'stats': stats,
            'levels': levels
        }
    
    print(f"✅ Processed {len(all_level_results)} currency pairs")
    
    # Generate HTML report
    print("📝 Generating HTML report...")
    html = generate_html_report(signal_id, all_level_results)
    
    # Save report
    output_file = OUTPUT_DIR / f"detailed_comparison_all_levels_{signal_id}.html"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Report saved to: {output_file}")
    print(f"📊 File size: {len(html):,} bytes")
    print(f"📈 {len(all_level_results)} currency pairs analyzed")
    print(f"📊 Each currency includes: L1, L2, L3, L4+ analysis")
    print(f"⚡ Total comparisons: {len(all_level_results) * 4 * 8}")
    
    return output_file

if __name__ == "__main__":
    main()
