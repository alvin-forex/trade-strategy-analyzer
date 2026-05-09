#!/usr/bin/env python3
"""
Generate cross-signal summary report from all-levels comparison HTML reports.
"""

from pathlib import Path
from bs4 import BeautifulSoup
from collections import defaultdict
import json

# Directory containing all-levels reports
OUTPUT_DIR = Path("output")

# Level ranges
LEVEL_RANGES = ['L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9+']

# Wait times for Copy on Profit
PROFIT_WAIT_TIMES = [5, 10, 15, 20]

# Wait times for Copy on Lose
LOSE_WAIT_TIMES = [10, 15, 20, 25]


def parse_report(report_path):
    """Parse an all-levels comparison report and extract key metrics."""
    print(f"  📖 Parsing: {report_path.name}")
    
    with open(report_path, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'html.parser')
    
    signal_data = {
        'signal_id': report_path.stem.replace('detailed_comparison_all_levels_', '').replace('forex-forest-signals-page-', ''),
        'currency_pairs': {},
        'total_comparisons': 0,
        'best_profit_combinations': [],
        'best_lose_combinations': []
    }
    
    # Find all currency pair sections
    pair_sections = soup.find_all('div', {'class': 'currency-section'})
    
    for section in pair_sections:
        header = section.find('div', {'class': 'currency-header'})
        if not header:
            continue
        symbol = header.text.strip()
        
        pair_data = {
            'symbol': symbol,
            'total_trades': 0,
            'levels': {}
        }
        
        # Find basic stats
        stats_div = section.find('div', {'class': 'currency-stats'})
        if stats_div:
            stat_items = stats_div.find_all('div', {'class': 'stat-item'})
            for item in stat_items:
                label = item.find('span', {'class': 'stat-label'})
                value = item.find('span', {'class': 'stat-value'})
                if label and value and 'Total Trades' in label.text:
                    total_trades = int(value.text.strip())
                    pair_data['total_trades'] = total_trades
        
        # Find all level sections within this currency pair
        # Level sections are inside the currency-section div
        all_level_sections = section.find_all('div', {'class': 'level-section'})
        
        for level_section in all_level_sections:
            # Extract level info from header
            level_header = level_section.find('div', {'class': 'level-header'})
            if not level_header:
                continue
            
            header_text = level_header.text.strip()
            # Determine level from header (e.g., "L1 ($0 - $50) - 28 trades")
            level = None
            for l in LEVEL_RANGES:
                if header_text.startswith(l):
                    level = l
                    break
            
            if not level:
                continue
            
            level_data = {
                'range': level,
                'profit': {},
                'lose': {}
            }
            
            # Find all strategy sections within this level
            strategy_sections = level_section.find_all('div', {'class': 'strategy-section'})
            
            for strategy_section in strategy_sections:
                strategy_header = strategy_section.find('div', {'class': 'strategy-header'})
                if not strategy_header:
                    continue
                
                strategy_text = strategy_header.text.strip()
                is_profit = 'Copy on Profit' in strategy_text
                is_lose = 'Copy on Lose' in strategy_text
                
                if not (is_profit or is_lose):
                    continue
                
                # Find the comparison table
                table = strategy_section.find('table', {'class': 'comparison-table'})
                if not table:
                    continue
                
                rows = table.find_all('tr')[1:]  # Skip header
                
                if is_profit:
                    wait_times = PROFIT_WAIT_TIMES
                else:
                    wait_times = LOSE_WAIT_TIMES
                
                for i, row in enumerate(rows):
                    if i >= len(wait_times):
                        break
                    
                    cells = row.find_all('td')
                    if len(cells) >= 6:
                        wait_time = wait_times[i]
                        score_cell = cells[4].text.strip()
                        
                        try:
                            score = float(score_cell)
                        except ValueError:
                            continue
                        
                        if is_profit:
                            trigger_rate = float(cells[1].text.strip().rstrip('%'))
                            avg_profit_str = cells[2].text.strip().replace('$', '')
                            avg_profit = float(avg_profit_str)
                            win_rate = float(cells[3].text.strip().rstrip('%'))
                            level_data['profit'][wait_time] = {
                                'trigger_rate': trigger_rate,
                                'avg_profit': avg_profit,
                                'win_rate': win_rate,
                                'score': score
                            }
                            
                            # Track best combinations
                            signal_data['best_profit_combinations'].append({
                                'signal': signal_data['signal_id'],
                                'symbol': symbol,
                                'level': level,
                                'wait_time': wait_time,
                                'score': score,
                                'trigger_rate': trigger_rate,
                                'avg_profit': avg_profit,
                                'win_rate': win_rate,
                                'total_trades': total_trades
                            })
                        else:
                            # Copy on Lose
                            # 欄位順序: Wait, Trigger Rate, Recovery Rate, Avg After, Score, Rating, Score Details
                            trigger_rate_str = cells[1].text.strip().rstrip('%')
                            recovery_rate_str = cells[2].text.strip().rstrip('%')
                            recovery_profit_str = cells[3].text.strip().replace('$', '')
                            
                            try:
                                trigger_rate = float(trigger_rate_str) if trigger_rate_str else 0.0
                                recovery_rate = float(recovery_rate_str) if recovery_rate_str else 0.0
                                recovery_profit = float(recovery_profit_str) if recovery_profit_str else 0.0
                            except ValueError:
                                continue
                            
                            level_data['lose'][wait_time] = {
                                'recovery_rate': recovery_rate,
                                'recovery_profit': recovery_profit,
                                'trigger_rate': trigger_rate,
                                'score': score
                            }
                            
                            # Track best combinations
                            signal_data['best_lose_combinations'].append({
                                'signal': signal_data['signal_id'],
                                'symbol': symbol,
                                'level': level,
                                'wait_time': wait_time,
                                'score': score,
                                'recovery_rate': recovery_rate,
                                'recovery_profit': recovery_profit,
                                'trigger_rate': trigger_rate,
                                'total_trades': total_trades
                            })
            
            pair_data['levels'][level] = level_data
        
        signal_data['currency_pairs'][symbol] = pair_data
    
    # Count total comparisons
    signal_data['total_comparisons'] = len(signal_data['best_profit_combinations']) + len(signal_data['best_lose_combinations'])
    
    return signal_data


def generate_summary(signals_data):
    """Generate cross-signal summary."""
    
    # 1. Best Copy on Profit combinations across all signals
    profit_combinations = []
    for signal in signals_data:
        profit_combinations.extend(signal['best_profit_combinations'])
    
    profit_combinations.sort(key=lambda x: (x['score'], x['avg_profit']), reverse=True)
    top_profit = profit_combinations[:20]
    
    # 2. Best Copy on Lose combinations across all signals
    lose_combinations = []
    for signal in signals_data:
        lose_combinations.extend(signal['best_lose_combinations'])
    
    lose_combinations.sort(key=lambda x: (x['score'], x['recovery_profit']), reverse=True)
    top_lose = lose_combinations[:20]
    
    # 3. Best signals by level
    best_signals_by_level = defaultdict(list)
    for signal in signals_data:
        signal_id = signal['signal_id']
        for level in LEVEL_RANGES:
            level_profit = [c for c in signal['best_profit_combinations'] if c['level'] == level]
            level_lose = [c for c in signal['best_lose_combinations'] if c['level'] == level]
            
            if level_profit:
                avg_score = sum(c['score'] for c in level_profit) / len(level_profit)
                best_signals_by_level[level].append({
                    'signal': signal_id,
                    'avg_profit_score': avg_score,
                    'comparisons': len(level_profit)
                })
    
    # Sort within each level and ensure all levels exist
    for level in LEVEL_RANGES:
        if level not in best_signals_by_level:
            best_signals_by_level[level] = []
        else:
            best_signals_by_level[level].sort(key=lambda x: x['avg_profit_score'], reverse=True)
    
    # 4. Best currency pairs across all signals
    pair_performance = defaultdict(lambda: {
        'profit_scores': [],
        'lose_scores': [],
        'signals': set(),
        'total_trades': 0
    })
    
    for signal in signals_data:
        signal_id = signal['signal_id']
        for symbol, pair_data in signal['currency_pairs'].items():
            pair_perf = pair_performance[symbol]
            pair_perf['signals'].add(signal_id)
            pair_perf['total_trades'] += pair_data['total_trades']
            
            for combo in signal['best_profit_combinations']:
                if combo['symbol'] == symbol:
                    pair_perf['profit_scores'].append(combo['score'])
            
            for combo in signal['best_lose_combinations']:
                if combo['symbol'] == symbol:
                    pair_perf['lose_scores'].append(combo['score'])
    
    # Calculate average scores for each pair
    pair_rankings = []
    for symbol, perf in pair_performance.items():
        avg_profit = sum(perf['profit_scores']) / len(perf['profit_scores']) if perf['profit_scores'] else 0
        avg_lose = sum(perf['lose_scores']) / len(perf['lose_scores']) if perf['lose_scores'] else 0
        overall_score = (avg_profit + avg_lose) / 2
        
        pair_rankings.append({
            'symbol': symbol,
            'avg_profit_score': avg_profit,
            'avg_lose_score': avg_lose,
            'overall_score': overall_score,
            'signals': len(perf['signals']),
            'total_trades': perf['total_trades']
        })
    
    pair_rankings.sort(key=lambda x: x['overall_score'], reverse=True)
    
    return {
        'top_profit': top_profit,
        'top_lose': top_lose,
        'best_signals_by_level': dict(best_signals_by_level),
        'pair_rankings': pair_rankings[:20]
    }


def generate_html_report(signals_data, summary, output_path):
    """Generate HTML summary report."""
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cross-Signal Copy Trade Strategy Summary</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            line-height: 1.6;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }}
        
        h1 {{
            text-align: center;
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }}
        
        .subtitle {{
            text-align: center;
            color: #666;
            margin-bottom: 40px;
            font-size: 1.1em;
        }}
        
        .section {{
            margin-bottom: 50px;
        }}
        
        h2 {{
            color: #764ba2;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
            font-size: 1.8em;
        }}
        
        h3 {{
            color: #555;
            margin-bottom: 15px;
            font-size: 1.3em;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            background: white;
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        
        th {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
        }}
        
        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}
        
        tr:hover {{
            background: #f8f9ff;
        }}
        
        .score {{
            font-weight: bold;
            color: #667eea;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            margin-right: 8px;
        }}
        
        .badge-excellent {{
            background: #10b981;
            color: white;
        }}
        
        .badge-good {{
            background: #f59e0b;
            color: white;
        }}
        
        .badge-average {{
            background: #f97316;
            color: white;
        }}
        
        .badge-poor {{
            background: #ef4444;
            color: white;
        }}
        
        .level-badge {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 4px;
            font-size: 0.8em;
            font-weight: bold;
            background: #e0e7ff;
            color: #4338ca;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        
        .stat-value {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            font-size: 0.9em;
            opacity: 0.9;
        }}
        
        .ranking {{
            margin-bottom: 30px;
        }}
        
        .level-section {{
            margin-bottom: 30px;
            padding: 20px;
            background: #f8f9ff;
            border-radius: 8px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Cross-Signal Copy Trade Strategy Summary</h1>
        <p class="subtitle">Analysis of {len(signals_data)} signals across {len(set(pair['symbol'] for signal in signals_data for pair in signal['currency_pairs'].values()))} currency pairs</p>
        
        <div class="section">
            <h2>📊 Overall Statistics</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-value">{len(signals_data)}</div>
                    <div class="stat-label">Signals Analyzed</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{sum(len(signal['currency_pairs']) for signal in signals_data)}</div>
                    <div class="stat-label">Total Pair-Signal Combinations</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value">{sum(signal['total_comparisons'] for signal in signals_data)}</div>
                    <div class="stat-label">Total Comparisons</div>
                </div>
            </div>
        </div>
        
        <div class="section">
            <h2>🚀 Top Copy on Profit Combinations</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Signal</th>
                        <th>Pair</th>
                        <th>Level</th>
                        <th>Wait</th>
                        <th>Score</th>
                        <th>Trigger Rate</th>
                        <th>Avg Profit</th>
                        <th>Win Rate</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for i, combo in enumerate(summary['top_profit'], 1):
        badge_class = 'badge-excellent' if combo['score'] >= 80 else 'badge-good' if combo['score'] >= 60 else 'badge-average' if combo['score'] >= 40 else 'badge-poor'
        
        html += f"""
                    <tr>
                        <td><strong>#{i}</strong></td>
                        <td><span class="badge badge-excellent">{combo['signal']}</span></td>
                        <td>{combo['symbol']}</td>
                        <td><span class="level-badge">{combo['level']}</span></td>
                        <td>{combo['wait_time']} pips</td>
                        <td class="score">{combo['score']:.1f}</td>
                        <td>{combo['trigger_rate']:.1f}%</td>
                        <td>${combo['avg_profit']:.2f}</td>
                        <td>{combo['win_rate']:.1f}%</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>🛡️ Top Copy on Lose Combinations</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Signal</th>
                        <th>Pair</th>
                        <th>Level</th>
                        <th>Wait</th>
                        <th>Score</th>
                        <th>Recovery Rate</th>
                        <th>Recovery Profit</th>
                        <th>Trigger Rate</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for i, combo in enumerate(summary['top_lose'], 1):
        badge_class = 'badge-excellent' if combo['score'] >= 80 else 'badge-good' if combo['score'] >= 60 else 'badge-average' if combo['score'] >= 40 else 'badge-poor'
        
        html += f"""
                    <tr>
                        <td><strong>#{i}</strong></td>
                        <td><span class="badge badge-excellent">{combo['signal']}</span></td>
                        <td>{combo['symbol']}</td>
                        <td><span class="level-badge">{combo['level']}</span></td>
                        <td>{combo['wait_time']} pips</td>
                        <td class="score">{combo['score']:.1f}</td>
                        <td>{combo['recovery_rate']:.1f}%</td>
                        <td>${combo['recovery_profit']:.2f}</td>
                        <td>{combo['trigger_rate']:.1f}%</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>🏆 Best Signals by Level</h2>
"""
    
    for level in LEVEL_RANGES:
        html += f"""
            <div class="level-section">
                <h3>{level} (${level.replace('L', '').replace('+', '$') if level == 'L9+' else level.replace('L', '$')})</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Rank</th>
                            <th>Signal</th>
                            <th>Avg Profit Score</th>
                            <th>Comparisons</th>
                        </tr>
                    </thead>
                    <tbody>
"""
        
        for i, signal in enumerate(summary['best_signals_by_level'][level][:5], 1):
            html += f"""
                        <tr>
                            <td><strong>#{i}</strong></td>
                            <td><span class="badge badge-excellent">{signal['signal']}</span></td>
                            <td class="score">{signal['avg_profit_score']:.1f}</td>
                            <td>{signal['comparisons']}</td>
                        </tr>
"""
        
        html += """
                    </tbody>
                </table>
            </div>
"""
    
    html += """
        </div>
        
        <div class="section">
            <h2>💱 Best Currency Pairs Across All Signals</h2>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Pair</th>
                        <th>Overall Score</th>
                        <th>Avg Profit Score</th>
                        <th>Avg Lose Score</th>
                        <th>Signals</th>
                        <th>Total Trades</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for i, pair in enumerate(summary['pair_rankings'], 1):
        html += f"""
                    <tr>
                        <td><strong>#{i}</strong></td>
                        <td><span class="badge badge-excellent">{pair['symbol']}</span></td>
                        <td class="score">{pair['overall_score']:.1f}</td>
                        <td>{pair['avg_profit_score']:.1f}</td>
                        <td>{pair['avg_lose_score']:.1f}</td>
                        <td>{pair['signals']}</td>
                        <td>{pair['total_trades']}</td>
                    </tr>
"""
    
    html += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>📋 Strategy Recommendations</h2>
            <div style="background: #f0f9ff; padding: 20px; border-radius: 8px; border-left: 4px solid #667eea;">
                <h3 style="margin-top: 0;">Based on the analysis above:</h3>
                <ul>
"""
    
    # Generate recommendations
    if summary['top_profit']:
        top_profit = summary['top_profit'][0]
        html += f"""
                    <li><strong>Best Copy on Profit Strategy:</strong> Use Signal <strong>{top_profit['signal']}</strong> with <strong>{top_profit['symbol']}</strong> at <strong>{top_profit['level']}</strong> level, wait <strong>{top_profit['wait_time']} pips</strong> before copying. Expected score: <strong>{top_profit['score']:.1f}</strong></li>
"""
    
    if summary['top_lose']:
        top_lose = summary['top_lose'][0]
        html += f"""
                    <li><strong>Best Copy on Lose Strategy:</strong> Use Signal <strong>{top_lose['signal']}</strong> with <strong>{top_lose['symbol']}</strong> at <strong>{top_lose['level']}</strong> level, wait <strong>{top_lose['wait_time']} pips</strong> before copying. Expected score: <strong>{top_lose['score']:.1f}</strong></li>
"""
    
    if summary['pair_rankings']:
        top_pair = summary['pair_rankings'][0]
        html += f"""
                    <li><strong>Most Reliable Pair:</strong> <strong>{top_pair['symbol']}</strong> performs best across all signals with an overall score of <strong>{top_pair['overall_score']:.1f}</strong></li>
"""
    
    html += """
                </ul>
            </div>
        </div>
        
        <div style="text-align: center; color: #999; margin-top: 50px; padding-top: 20px; border-top: 1px solid #eee;">
            <p>Generated by Trade Strategy Analyzer | {len(signals_data)} signals analyzed</p>
        </div>
    </div>
</body>
</html>
"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"  ✅ HTML report saved: {output_path}")


def main():
    print("🚀 Generating cross-signal summary report...")
    
    # Find all all-levels reports
    report_files = sorted(OUTPUT_DIR.glob("detailed_comparison_all_levels_*.html"))
    
    if not report_files:
        print(f"❌ No all-levels reports found in {OUTPUT_DIR}")
        return
    
    print(f"📄 Found {len(report_files)} all-levels reports")
    
    # Parse all reports
    signals_data = []
    for report_file in report_files:
        signal_data = parse_report(report_file)
        signals_data.append(signal_data)
    
    print(f"\n📊 Parsed {len(signals_data)} signals")
    
    # Generate summary
    print("\n🔍 Analyzing cross-signal patterns...")
    summary = generate_summary(signals_data)
    
    # Generate HTML report
    output_path = OUTPUT_DIR / "cross_signal_summary.html"
    generate_html_report(signals_data, summary, output_path)
    
    print(f"\n✅ Cross-signal summary report complete!")
    print(f"📄 Report saved to: {output_path}")


if __name__ == '__main__':
    main()
