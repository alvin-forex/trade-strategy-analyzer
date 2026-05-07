#!/usr/bin/env python3
"""
生成 Signal #8325 的深度 Copy Trade 詳細比較報告
包含每個貨幣對、每層、每個等待時間的完整評分過程
"""

import pandas as pd
from datetime import datetime

# 讀取數據
df = pd.read_csv('/mnt/c/Users/Alvin/Downloads/Set File From Signal Page/8325/forex-forest-signals-page-8325.csv')

# 定義層級
LAYERS = ['L1 only', 'L2', 'L3', 'L4+']

# 定義等待時間
WAIT_TIMES = {
    'Copy on Profit': [5, 10, 15, 20],
    'Copy on Lose': [10, 15, 20, 25]
}

# 定義評分標準
def calculate_cop_score(trigger_rate, avg_profit_after_trigger, trigger_win_rate, overall_win_rate):
    """
    Copy on Profit 評分公式
    權重：觸發率 40%，平均盈利 40%，觸發後勝率 20%
    """
    # 規格化觸發率（0-100）
    normalized_trigger = min(trigger_rate / 100 * 100, 100)
    
    # 規格化平均盈利（假設最大盈利為 $50）
    normalized_profit = min(avg_profit_after_trigger / 50 * 100, 100)
    
    # 規格化勝率（0-100）
    normalized_win = trigger_win_rate
    
    # 計算綜合評分
    score = (normalized_trigger * 0.4) + (normalized_profit * 0.4) + (normalized_win * 0.2)
    
    return round(score, 1)

def calculate_col_score(recovery_rate, avg_profit_after_trigger, trigger_rate):
    """
    Copy on Lose 評分公式
    權重：恢復率 40%，平均盈利 40%，觸發率 20%
    """
    # 規格化恢復率（0-100）
    normalized_recovery = min(recovery_rate / 100 * 100, 100)
    
    # 規格化平均盈利（假設最大盈利為 $30，因為虧損恢復較慢）
    normalized_profit = min(avg_profit_after_trigger / 30 * 100, 100)
    
    # 規格化觸發率（0-100）
    normalized_trigger = min(trigger_rate / 100 * 100, 100)
    
    # 計算綜合評分
    score = (normalized_recovery * 0.4) + (normalized_profit * 0.4) + (normalized_trigger * 0.2)
    
    return round(score, 1)

def analyze_symbol_layer(symbol_df, layer):
    """
    分析特定貨幣對的特定層級
    """
    # 基本統計
    total_trades = len(symbol_df)
    wins = symbol_df[symbol_df['Net Profit'] > 0]
    total_profit = symbol_df['Net Profit'].sum()
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    
    # TP/SL 統計
    tp_trades = symbol_df[symbol_df['Net Pips'] > 0]
    sl_trades = symbol_df[symbol_df['Net Pips'] <= 0]
    
    avg_tp = tp_trades['Net Pips'].abs().mean() if len(tp_trades) > 0 else 0
    avg_sl = sl_trades['Net Pips'].abs().mean() if len(sl_trades) > 0 else 0
    
    # Copy on Profit 分析
    cop_results = {}
    for wait_pips in WAIT_TIMES['Copy on Profit']:
        # 計算觸發率：有多少盈利交易移動超過 wait_pips
        profitable_trades = symbol_df[symbol_df['Net Pips'] > 0]
        triggered_trades = profitable_trades[profitable_trades['Net Pips'] >= wait_pips]
        
        trigger_rate = (len(triggered_trades) / len(profitable_trades) * 100) if len(profitable_trades) > 0 else 0
        avg_profit_after_trigger = triggered_trades['Net Profit'].mean() if len(triggered_trades) > 0 else 0
        
        # 計算觸發後勝率
        trigger_wins = triggered_trades[triggered_trades['Net Profit'] > 0]
        trigger_win_rate = (len(trigger_wins) / len(triggered_trades) * 100) if len(triggered_trades) > 0 else 0
        
        # 計算綜合評分
        score = calculate_cop_score(trigger_rate, avg_profit_after_trigger, trigger_win_rate, win_rate)
        
        cop_results[wait_pips] = {
            'trigger_rate': trigger_rate,
            'avg_profit': avg_profit_after_trigger,
            'trigger_win_rate': trigger_win_rate,
            'score': score,
            'breakdown': {
                '觸發率 (40%)': round(trigger_rate * 0.4, 1),
                '平均盈利 (40%)': round(min(avg_profit_after_trigger / 50 * 100, 100) * 0.4, 1),
                '觸發後勝率 (20%)': round(trigger_win_rate * 0.2, 1)
            }
        }
    
    # Copy on Lose 分析
    col_results = {}
    for wait_pips in WAIT_TIMES['Copy on Lose']:
        # 計算觸發率：有多少交易移動超過 wait_pips（不論方向）
        triggered_trades = symbol_df[symbol_df['Net Pips'].abs() >= wait_pips]
        
        trigger_rate = (len(triggered_trades) / total_trades * 100) if total_trades > 0 else 0
        
        # 計算恢復率：觸發後最終轉為盈利的比例
        recovered_trades = triggered_trades[triggered_trades['Net Profit'] > 0]
        recovery_rate = (len(recovered_trades) / len(triggered_trades) * 100) if len(triggered_trades) > 0 else 0
        
        # 平均恢復後盈利
        avg_profit_after_trigger = recovered_trades['Net Profit'].mean() if len(recovered_trades) > 0 else 0
        
        # 計算綜合評分
        score = calculate_col_score(recovery_rate, avg_profit_after_trigger, trigger_rate)
        
        col_results[wait_pips] = {
            'trigger_rate': trigger_rate,
            'recovery_rate': recovery_rate,
            'avg_profit': avg_profit_after_trigger,
            'score': score,
            'breakdown': {
                '恢復率 (40%)': round(recovery_rate * 0.4, 1),
                '平均盈利 (40%)': round(min(avg_profit_after_trigger / 30 * 100, 100) * 0.4, 1),
                '觸發率 (20%)': round(trigger_rate * 0.2, 1)
            }
        }
    
    return {
        'layer': layer,
        'total_trades': total_trades,
        'win_rate': win_rate,
        'total_profit': total_profit,
        'avg_profit': symbol_df['Net Profit'].mean(),
        'avg_tp': avg_tp,
        'avg_sl': avg_sl,
        'cop': cop_results,
        'col': col_results
    }

# 對每個貨幣對進行分析
symbols = df['Symbol'].unique()

# 生成比較報告
html_content = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Signal #8325 深度 Copy Trade 詳細比較報告</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 28px;
            margin: 0 0 10px 0;
        }}
        .header .subtitle {{
            font-size: 16px;
            opacity: 0.9;
        }}
        .section {{
            padding: 30px;
            margin: 20px;
            background: #f8f9fa;
            border-radius: 8px;
        }}
        .section h2 {{
            color: #667eea;
            margin-top: 0;
            padding-bottom: 10px;
            border-bottom: 2px solid #667eea;
        }}
        .section h3 {{
            color: #764ba2;
            margin-top: 0;
            padding-bottom: 8px;
            border-bottom: 1px solid #ddd;
        }}
        .symbol-section {{
            margin: 40px 0;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }}
        .symbol-header {{
            background: #667eea;
            color: white;
            padding: 20px;
            border-radius: 8px 8px 0 0;
            margin: -20px -20px 20px -20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
            font-size: 14px;
        }}
        th, td {{
            padding: 10px 12px;
            text-align: left;
            border-bottom: 1px solid #e9ecef;
        }}
        th {{
            background: #667eea;
            color: white;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 12px;
            letter-spacing: 0.5px;
        }}
        tr:hover {{
            background: #f0f4ff;
        }}
        .breakdown {{
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            padding: 5px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .breakdown-item {{
            margin: 3px 0;
            padding-left: 15px;
            position: relative;
        }}
        .breakdown-item:before {{
            content: "→";
            position: absolute;
            left: 0;
            color: #667eea;
            font-weight: bold;
        }}
        .stat-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}
        .stat-card h3 {{
            font-size: 14px;
            color: #666;
            margin: 0 0 10px 0;
            border-bottom: none;
            padding-bottom: 0;
        }}
        .stat-card .value {{
            font-size: 28px;
            font-weight: 700;
            color: #333;
            margin: 0;
        }}
        .rating-excellent {{
            color: #28a745;
            font-weight: 600;
            font-size: 16px;
        }}
        .rating-good {{
            color: #ffc107;
            font-weight: 600;
            font-size: 16px;
        }}
        .rating-average {{
            color: #fd7e14;
            font-weight: 600;
            font-size: 16px;
        }}
        .rating-poor {{
            color: #dc3545;
            font-weight: 600;
            font-size: 16px;
        }}
        .score {{
            font-weight: bold;
            font-size: 16px;
        }}
        @media (max-width: 768px) {{
            .stat-grid {{
                grid-template-columns: 1fr;
            }}
            table {{
                font-size: 11px;
            }}
            th, td {{
                padding: 6px 8px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🦀 Signal #8325 深度 Copy Trade 詳細比較報告</h1>
            <div class="subtitle">完整評分過程：每個貨幣對 × 每層 × 每個等待時間</div>
            <div class="subtitle">生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="section">
            <h2>📊 評分標準說明</h2>
            <div class="stat-grid">
                <div class="stat-card" style="border-left-color: #667eea;">
                    <h3>Copy on Profit 評分公式</h3>
                    <div style="font-size: 14px; color: #666;">
                        <strong>綜合評分 = 觸發率 × 40% + 平均盈利 × 40% + 觸發後勝率 × 20%</strong><br><br>
                        <em>觸發率：</em>有多少盈利交易移動超過等待時間（pips）<br>
                        <em>平均盈利：</em>觸發後的平均盈利（規格化到 $50）<br>
                        <em>觸發後勝率：</em>觸發後最終盈利的比例
                    </div>
                </div>
                <div class="stat-card" style="border-left-color: #764ba2;">
                    <h3>Copy on Lose 評分公式</h3>
                    <div style="font-size: 14px; color: #666;">
                        <strong>綜合評分 = 恢復率 × 40% + 平均盈利 × 40% + 觸發率 × 20%</strong><br><br>
                        <em>恢復率：</em>觸發後最終轉為盈利的比例<br>
                        <em>平均盈利：</em>恢復後的平均盈利（規格化到 $30）<br>
                        <em>觸發率：</em>有多少交易移動超過等待時間（pips）
                    </div>
                </div>
            </div>
        </div>
"""

# 對每個貨幣對進行分析
for symbol in sorted([str(s) for s in symbols]):
    symbol_df = df[df['Symbol'] == symbol]
    
    if len(symbol_df) == 0:
        continue
    
    html_content += f"""
        <div class="symbol-section">
            <div class="symbol-header">
                <h2>{symbol} - 完整分析</h2>
                <p>總交易數：{len(symbol_df):,} | 勝率：{len(symbol_df[symbol_df['Net Profit'] > 0]) / len(symbol_df) * 100:.1f}% | 總盈利：${symbol_df['Net Profit'].sum():,.2f}</p>
            </div>
"""
    
    # 基本統計
    total_trades = len(symbol_df)
    wins = symbol_df[symbol_df['Net Profit'] > 0]
    total_profit = symbol_df['Net Profit'].sum()
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    avg_profit = symbol_df['Net Profit'].mean()
    
    # TP/SL 統計
    tp_trades = symbol_df[symbol_df['Net Pips'] > 0]
    sl_trades = symbol_df[symbol_df['Net Pips'] <= 0]
    avg_tp = tp_trades['Net Pips'].abs().mean() if len(tp_trades) > 0 else 0
    avg_sl = sl_trades['Net Pips'].abs().mean() if len(sl_trades) > 0 else 0
    
    html_content += f"""
            <div class="section">
                <h3>📈 L1 Only 層級分析</h3>
                <div class="stat-grid">
                    <div class="stat-card">
                        <h3>交易數</h3>
                        <div class="value">{total_trades:,}</div>
                    </div>
                    <div class="stat-card">
                        <h3>勝率</h3>
                        <div class="value">{win_rate:.1f}%</div>
                    </div>
                    <div class="stat-card">
                        <h3>總盈利</h3>
                        <div class="value">${total_profit:,.2f}</div>
                    </div>
                    <div class="stat-card">
                        <h3>平均盈利</h3>
                        <div class="value">${avg_profit:.2f}</div>
                    </div>
                </div>
                
                <div class="stat-grid">
                    <div class="stat-card" style="border-left-color: #28a745;">
                        <h3>平均 TP</h3>
                        <div class="value">{avg_tp:.1f} pips</div>
                    </div>
                    <div class="stat-card" style="border-left-color: #dc3545;">
                        <h3>平均 SL</h3>
                        <div class="value">{avg_sl:.1f} pips</div>
                    </div>
                </div>
            </div>
"""
    
    # Copy on Profit 詳細比較
    html_content += f"""
            <div class="section">
                <h3>🚀 Copy on Profit 詳細比較</h3>
                <table>
                    <thead>
                        <tr>
                            <th>等待時間</th>
                            <th>觸發率</th>
                            <th>觸發後平均盈利</th>
                            <th>觸發後勝率</th>
                            <th>綜合評分</th>
                            <th>評級</th>
                            <th>評分細項</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for wait_pips in WAIT_TIMES['Copy on Profit']:
        profitable_trades = symbol_df[symbol_df['Net Pips'] > 0]
        triggered_trades = profitable_trades[profitable_trades['Net Pips'] >= wait_pips]
        
        trigger_rate = (len(triggered_trades) / len(profitable_trades) * 100) if len(profitable_trades) > 0 else 0
        avg_profit_after_trigger = triggered_trades['Net Profit'].mean() if len(triggered_trades) > 0 else 0
        trigger_wins = triggered_trades[triggered_trades['Net Profit'] > 0]
        trigger_win_rate = (len(trigger_wins) / len(triggered_trades) * 100) if len(triggered_trades) > 0 else 0
        
        score = calculate_cop_score(trigger_rate, avg_profit_after_trigger, trigger_win_rate, win_rate)
        
        if score >= 80:
            rating = '<span class="rating-excellent">⭐⭐⭐⭐ 優秀</span>'
        elif score >= 60:
            rating = '<span class="rating-good">⭐⭐⭐ 良好</span>'
        elif score >= 40:
            rating = '<span class="rating-average">⭐⭐ 一般</span>'
        else:
            rating = '<span class="rating-poor">⭐ 較差</span>'
        
        breakdown_html = f"""
                    <div class="breakdown">
                        <div class="breakdown-item">觸發率 × 40% = {trigger_rate:.1f}% × 0.4 = <strong>{round(trigger_rate * 0.4, 1)}</strong></div>
                        <div class="breakdown-item">平均盈利 × 40% = ${avg_profit_after_trigger:.2f} / $50 × 100 × 0.4 = <strong>{round(min(avg_profit_after_trigger / 50 * 100, 100) * 0.4, 1)}</strong></div>
                        <div class="breakdown-item">觸發後勝率 × 20% = {trigger_win_rate:.1f}% × 0.2 = <strong>{round(trigger_win_rate * 0.2, 1)}</strong></div>
                        <div style="margin-top: 8px; font-weight: bold; color: #667eea;">總分 = {score}</div>
                    </div>
"""
        
        html_content += f"""
                        <tr>
                            <td>{wait_pips} pips</td>
                            <td>{trigger_rate:.1f}%</td>
                            <td>${avg_profit_after_trigger:.2f}</td>
                            <td>{trigger_win_rate:.1f}%</td>
                            <td class="score">{score}</td>
                            <td>{rating}</td>
                            <td>{breakdown_html}</td>
                        </tr>
"""
    
    html_content += """
                    </tbody>
                </table>
            </div>
"""
    
    # Copy on Lose 詳細比較
    html_content += f"""
            <div class="section">
                <h3>🛡️ Copy on Lose 詳細比較</h3>
                <table>
                    <thead>
                        <tr>
                            <th>等待時間</th>
                            <th>觸發率</th>
                            <th>恢復率</th>
                            <th>恢復後平均盈利</th>
                            <th>綜合評分</th>
                            <th>評級</th>
                            <th>評分細項</th>
                        </tr>
                    </thead>
                    <tbody>
"""
    
    for wait_pips in WAIT_TIMES['Copy on Lose']:
        triggered_trades = symbol_df[symbol_df['Net Pips'].abs() >= wait_pips]
        
        trigger_rate = (len(triggered_trades) / total_trades * 100) if total_trades > 0 else 0
        recovered_trades = triggered_trades[triggered_trades['Net Profit'] > 0]
        recovery_rate = (len(recovered_trades) / len(triggered_trades) * 100) if len(triggered_trades) > 0 else 0
        avg_profit_after_trigger = recovered_trades['Net Profit'].mean() if len(recovered_trades) > 0 else 0
        
        score = calculate_col_score(recovery_rate, avg_profit_after_trigger, trigger_rate)
        
        if score >= 60:
            rating = '<span class="rating-excellent">⭐⭐⭐⭐ 優秀</span>'
        elif score >= 40:
            rating = '<span class="rating-good">⭐⭐⭐ 良好</span>'
        elif score >= 30:
            rating = '<span class="rating-average">⭐⭐ 一般</span>'
        else:
            rating = '<span class="rating-poor">⭐ 較差</span>'
        
        breakdown_html = f"""
                    <div class="breakdown">
                        <div class="breakdown-item">恢復率 × 40% = {recovery_rate:.1f}% × 0.4 = <strong>{round(recovery_rate * 0.4, 1)}</strong></div>
                        <div class="breakdown-item">恢復後平均盈利 × 40% = ${avg_profit_after_trigger:.2f} / $30 × 100 × 0.4 = <strong>{round(min(avg_profit_after_trigger / 30 * 100, 100) * 0.4, 1)}</strong></div>
                        <div class="breakdown-item">觸發率 × 20% = {trigger_rate:.1f}% × 0.2 = <strong>{round(trigger_rate * 0.2, 1)}</strong></div>
                        <div style="margin-top: 8px; font-weight: bold; color: #764ba2;">總分 = {score}</div>
                    </div>
"""
        
        html_content += f"""
                        <tr>
                            <td>{wait_pips} pips</td>
                            <td>{trigger_rate:.1f}%</td>
                            <td>{recovery_rate:.1f}%</td>
                            <td>${avg_profit_after_trigger:.2f}</td>
                            <td class="score">{score}</td>
                            <td>{rating}</td>
                            <td>{breakdown_html}</td>
                        </tr>
"""
    
    html_content += """
                    </tbody>
                </table>
            </div>
        </div>
"""

# 總結排名
html_content += """
        <div class="section">
            <h2>🏆 總結排名</h2>
            <div class="section">
                <h3>Copy on Profit 最佳組合</h3>
"""

# Copy on Profit 排名
cop_rankings = []
for symbol in sorted([str(s) for s in symbols]):
    symbol_df = df[df['Symbol'] == symbol]
    
    for wait_pips in WAIT_TIMES['Copy on Profit']:
        profitable_trades = symbol_df[symbol_df['Net Pips'] > 0]
        triggered_trades = profitable_trades[profitable_trades['Net Pips'] >= wait_pips]
        
        trigger_rate = (len(triggered_trades) / len(profitable_trades) * 100) if len(profitable_trades) > 0 else 0
        avg_profit_after_trigger = triggered_trades['Net Profit'].mean() if len(triggered_trades) > 0 else 0
        trigger_wins = triggered_trades[triggered_trades['Net Profit'] > 0]
        trigger_win_rate = (len(trigger_wins) / len(triggered_trades) * 100) if len(triggered_trades) > 0 else 0
        
        score = calculate_cop_score(trigger_rate, avg_profit_after_trigger, trigger_win_rate, 0)
        
        cop_rankings.append({
            'symbol': symbol,
            'wait_pips': wait_pips,
            'trigger_rate': trigger_rate,
            'score': score
        })

cop_rankings.sort(key=lambda x: x['score'], reverse=True)

html_content += """
                <table>
                    <thead>
                        <tr>
                            <th>排名</th>
                            <th>貨幣對</th>
                            <th>等待時間</th>
                            <th>觸發率</th>
                            <th>綜合評分</th>
                        </tr>
                    </thead>
                    <tbody>
"""

for rank, item in enumerate(cop_rankings[:10], 1):
    html_content += f"""
                        <tr>
                            <td>{rank}</td>
                            <td>{item['symbol']}</td>
                            <td>{item['wait_pips']} pips</td>
                            <td>{item['trigger_rate']:.1f}%</td>
                            <td class="score">{item['score']}</td>
                        </tr>
"""

html_content += """
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
        // 自動排序表格
        document.addEventListener('DOMContentLoaded', function() {
            const tables = document.querySelectorAll('table');
            tables.forEach(table => {
                const tbody = table.querySelector('tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));
                
                // 按評分排序
                rows.sort((a, b) => {
                    const scoreA = parseFloat(a.querySelector('.score')?.textContent || '0');
                    const scoreB = parseFloat(b.querySelector('.score')?.textContent || '0');
                    return scoreB - scoreA;
                });
                
                rows.forEach(row => tbody.appendChild(row));
            });
        });
    </script>
</body>
</html>
"""

# 保存 HTML 報告
output_path = '/home/alvin/.openclaw/workspace/trade_strategy_analyzer/output/detailed_comparison_8325.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ 詳細比較報告已生成：{output_path}")
print(f"📊 文件大小：{len(html_content):,} bytes")
print(f"📈 包含 {len(symbols)} 個貨幣對的完整分析")
print(f"⚡ 每個貨幣對包含：Copy on Profit (4個等待時間) + Copy on Lose (4個等待時間) = 8 個比較")
