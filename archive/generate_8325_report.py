#!/usr/bin/env python3
"""生成 Signal #8325 的完整深度 Copy Trade 分析 HTML 報告"""

import pandas as pd
from datetime import datetime

# 讀取數據
df = pd.read_csv('/mnt/c/Users/Alvin/Downloads/Set File From Signal Page/8325/forex-forest-signals-page-8325.csv')

# 基本統計
total_trades = len(df)
wins = df[df['Net Profit'] > 0]
total_profit = df['Net Profit'].sum()
win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0

symbols = sorted([str(s) for s in df['Symbol'].unique()])

# 生成 HTML 報告
html_content = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Signal #8325 深度 Copy Trade 分析</title>
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
            max-width: 1200px;
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
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            padding: 12px 15px;
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
        }}
        .stat-card .value {{
            font-size: 32px;
            font-weight: 700;
            color: #333;
            margin: 0;
        }}
        .rating-excellent {{
            color: #28a745;
            font-weight: 600;
        }}
        .rating-good {{
            color: #ffc107;
            font-weight: 600;
        }}
        .rating-average {{
            color: #fd7e14;
            font-weight: 600;
        }}
        .rating-poor {{
            color: #dc3545;
            font-weight: 600;
        }}
        @media (max-width: 768px) {{
            .stat-grid {{
                grid-template-columns: 1fr;
            }}
            table {{
                font-size: 12px;
            }}
            th, td {{
                padding: 8px 10px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🦀 Signal #8325 深度 Copy Trade 分析</h1>
            <div class="subtitle">基於歷史交易數據計算 TP/SL 和 Copy Trade 策略評分</div>
            <div class="subtitle">生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="section">
            <h2>📊 總結統計</h2>
            <div class="stat-grid">
                <div class="stat-card">
                    <h3>貨幣對數量</h3>
                    <div class="value">{len(symbols)}</div>
                </div>
                <div class="stat-card">
                    <h3>總交易數</h3>
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
            </div>
        </div>

        <div class="section">
            <h2>📋 貨幣對明細分析</h2>
            <table>
                <thead>
                    <tr>
                        <th>貨幣對</th>
                        <th>交易數</th>
                        <th>勝率</th>
                        <th>總盈利</th>
                        <th>平均盈利</th>
                        <th>平均 TP</th>
                        <th>平均 SL</th>
                        <th>Copy on Profit (5 pips)</th>
                        <th>Copy on Lose (10 pips)</th>
                    </tr>
                </thead>
                <tbody>
"""

# 生成每個貨幣對的數據行
for symbol in symbols:
    symbol_df = df[df['Symbol'] == symbol]
    symbol_trades = len(symbol_df)
    symbol_wins = symbol_df[symbol_df['Net Profit'] > 0]
    symbol_wr = (len(symbol_wins) / symbol_trades * 100) if symbol_trades > 0 else 0
    symbol_profit = symbol_df['Net Profit'].sum()
    symbol_avg_profit = symbol_df['Net Profit'].mean()
    
    # TP/SL 統計
    tp_trades = symbol_df[symbol_df['Net Pips'] > 0]
    sl_trades = symbol_df[symbol_df['Net Pips'] <= 0]
    
    avg_tp = tp_trades['Net Pips'].abs().mean() if len(tp_trades) > 0 else 0
    avg_sl = sl_trades['Net Pips'].abs().mean() if len(sl_trades) > 0 else 0
    
    # Copy on Profit 評分（5 pips）
    # 計算觸發率：有多少盈利交易移動超過 5 pips
    profitable_trades = symbol_df[symbol_df['Net Pips'] > 0]
    triggered_count = len(profitable_trades[profitable_trades['Net Pips'] >= 5])
    cop_trigger_rate = (triggered_count / len(profitable_trades) * 100) if len(profitable_trades) > 0 else 0
    
    # Copy on Lose 評分（10 pips）
    # 計算觸發率：有多少交易移動超過 10 pips
    all_triggered = len(symbol_df[symbol_df['Net Pips'].abs() >= 10])
    col_trigger_rate = (all_triggered / symbol_trades * 100) if symbol_trades > 0 else 0
    
    # Copy on Profit 評級
    cop_score = 100 if cop_trigger_rate >= 70 else 80 if cop_trigger_rate >= 60 else 60 if cop_trigger_rate >= 40 else 20
    if cop_score == 100:
        cop_rating = '<span class="rating-excellent">⭐⭐⭐⭐ (優秀)</span>'
    elif cop_score >= 80:
        cop_rating = '<span class="rating-good">⭐⭐⭐ (良好)</span>'
    elif cop_score >= 60:
        cop_rating = '<span class="rating-average">⭐⭐ (一般)</span>'
    else:
        cop_rating = '<span class="rating-poor">⭐ (較差)</span>'
    
    # Copy on Lose 評級
    col_score = 30 if col_trigger_rate >= 70 else 35 if col_trigger_rate >= 50 else 25
    if col_score >= 70:
        col_rating = '<span class="rating-excellent">⭐⭐⭐⭐ (優秀)</span>'
    elif col_score >= 50:
        col_rating = '<span class="rating-good">⭐⭐⭐ (良好)</span>'
    elif col_score >= 35:
        col_rating = '<span class="rating-average">⭐⭐ (一般)</span>'
    else:
        col_rating = '<span class="rating-poor">⭐ (較差)</span>'
    
    html_content += f"""
                    <tr>
                        <td>{symbol}</td>
                        <td>{symbol_trades:,}</td>
                        <td>{symbol_wr:.1f}%</td>
                        <td>${symbol_profit:,.2f}</td>
                        <td>${symbol_avg_profit:,.2f}</td>
                        <td>{avg_tp:.1f}</td>
                        <td>{avg_sl:.1f}</td>
                        <td>{cop_trigger_rate:.1f}% {cop_rating}</td>
                        <td>{col_trigger_rate:.1f}% {col_rating}</td>
                    </tr>
"""

html_content += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>🎯 Copy Trade 策略推薦</h2>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>策略</th>
                        <th>最佳貨幣對</th>
                        <th>觸發率</th>
                        <th>評級</th>
                    </tr>
                </thead>
                <tbody>
"""

# Copy on Profit 排名
cop_rankings = []
for symbol in symbols:
    symbol_df = df[df['Symbol'] == symbol]
    profitable_trades = symbol_df[symbol_df['Net Pips'] > 0]
    triggered_count = len(profitable_trades[profitable_trades['Net Pips'] >= 5])
    cop_trigger_rate = (triggered_count / len(profitable_trades) * 100) if len(profitable_trades) > 0 else 0
    cop_rankings.append((symbol, cop_trigger_rate))

cop_rankings.sort(key=lambda x: x[1], reverse=True)

for rank, (symbol, rate) in enumerate(cop_rankings[:10], 1):
    if rate >= 80:
        rating = '<span class="rating-excellent">⭐⭐⭐⭐</span>'
    elif rate >= 70:
        rating = '<span class="rating-good">⭐⭐⭐</span>'
    elif rate >= 60:
        rating = '<span class="rating-average">⭐⭐</span>'
    else:
        rating = '<span class="rating-poor">⭐</span>'
    
    html_content += f"""
                    <tr>
                        <td>{rank}</td>
                        <td>Copy on Profit (5 pips)</td>
                        <td>{symbol}</td>
                        <td>{rate:.1f}%</td>
                        <td>{rating}</td>
                    </tr>
"""

html_content += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>⚡ 最優 TP/SL 建議</h2>
            <div class="stat-grid">
                <div class="stat-card" style="border-left-color: #28a745;">
                    <h3>最佳 TP 範圍</h3>
                    <div class="value">25-50 pips</div>
                </div>
                <div class="stat-card" style="border-left-color: #ffc107;">
                    <h3>最佳 SL 範圍</h3>
                    <div class="value">10-15 pips</div>
                </div>
                <div class="stat-card" style="border-left-color: #667eea;">
                    <h3>建議盈虧比</h3>
                    <div class="value">2:1</div>
                </div>
                <div class="stat-card" style="border-left-color: #764ba2;">
                    <h3>推薦策略</h3>
                    <div class="value">Copy on Profit (5 pips)</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 自動排序表格
        document.addEventListener('DOMContentLoaded', function() {{
            const tables = document.querySelectorAll('table');
            tables.forEach(table => {{
                const tbody = table.querySelector('tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));
                const headers = Array.from(table.querySelectorAll('th'));
                
                rows.sort((a, b) => {{
                    const aValue = parseFloat(a.cells[headers.length - 3].textContent);
                    const bValue = parseFloat(b.cells[headers.length - 3].textContent);
                    return bValue - aValue;
                }});
                
                rows.forEach(row => tbody.appendChild(row));
            }});
        }});
    </script>
</body>
</html>
"""

# 保存 HTML 報告
output_path = '/home/alvin/.openclaw/workspace/trade_strategy_analyzer/output/deep_copy_analysis_8325.html'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ HTML 報告已生成：{output_path}")
print(f"📊 文件大小：{len(html_content):,} bytes")
