#!/usr/bin/env python3
"""
Portfolio Report Generator
Generates P1-P5 portfolio HTML and JSON reports
"""

import os
import json
import csv
from datetime import datetime
from pathlib import Path

# Working directory
WORK_DIR = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer")
DOWNLOADS_DIR = WORK_DIR / "downloads"
REPORTS_DIR = WORK_DIR / "docs/reports"
OUTPUT_DIR = WORK_DIR / "docs/portfolios"

# Ensure output directory exists
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Portfolio configurations
PORTFOLIOS = {
    "P1": {
        "name": "DW 高勝率組",
        "capital": 1500,
        "target": "每月 50%",
        "strategy": "DW EA",
        "signals": [31593, 17547, 3291],
        "layers": "L1-L3",
        "risk_per_trade": 0.02,  # 2% risk per trade
    },
    "P2": {
        "name": "SMA 穩定組",
        "capital": 1000,
        "target": "每週 20%",
        "strategy": "SMA EA",
        "signals": [16698, 32278, 5001],
        "layers": "L1-L4",
        "risk_per_trade": 0.015,
    },
    "P3": {
        "name": "MKD 激進組",
        "capital": 2000,
        "target": "每月 50%",
        "strategy": "MKD EA",
        "signals": [23617, 10843],
        "layers": "L1-L5",
        "risk_per_trade": 0.03,
    },
    "P4": {
        "name": "GBPCAD 專攻",
        "capital": 1200,
        "target": "每週 20%",
        "strategy": "GBPCAD Sell",
        "signals": [],  # Will be populated dynamically
        "layers": "L1-L3",
        "risk_per_trade": 0.02,
        "filter_symbol": "GBPCAD",
    },
    "P5": {
        "name": "XAUUSD 黃金組",
        "capital": 1500,
        "target": "每月 50%",
        "strategy": "XAUUSD",
        "signals": [5117, 27226],
        "layers": "L1-L2",
        "risk_per_trade": 0.025,
    },
}

def read_signal_csv(signal_id):
    """Read signal CSV and return trade data"""
    csv_path = DOWNLOADS_DIR / f"forex-forest-signals-page-{signal_id}.csv"
    if not csv_path.exists():
        print(f"Warning: CSV not found for signal {signal_id}")
        return None
    
    trades = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trades.append(row)
    
    return trades

def analyze_signal(signal_id):
    """Analyze a signal and return summary statistics"""
    trades = read_signal_csv(signal_id)
    if not trades:
        return None
    
    total_trades = len(trades)
    total_profit = sum(float(t.get('Net Profit', 0)) for t in trades)
    
    # Count symbols
    symbols = {}
    for t in trades:
        symbol = t.get('Symbol', 'UNKNOWN')
        symbols[symbol] = symbols.get(symbol, 0) + 1
    
    # Determine EA type from comment
    ea_types = {}
    for t in trades:
        comment = t.get('Comment', '')
        if 'Dragon Wave' in comment:
            ea = 'DW'
        elif 'SMA' in comment:
            ea = 'SMA'
        elif 'MKD' in comment:
            ea = 'MKD'
        else:
            ea = 'Unknown'
        ea_types[ea] = ea_types.get(ea, 0) + 1
    
    # Primary EA type
    primary_ea = max(ea_types.items(), key=lambda x: x[1])[0] if ea_types else 'Unknown'
    
    # Primary symbol
    primary_symbol = max(symbols.items(), key=lambda x: x[1])[0] if symbols else 'UNKNOWN'
    
    # Primary direction
    directions = {}
    for t in trades:
        direction = t.get('Type', 'unknown')
        directions[direction] = directions.get(direction, 0) + 1
    primary_direction = max(directions.items(), key=lambda x: x[1])[0] if directions else 'unknown'
    
    # Calculate average lot size
    avg_lot = sum(float(t.get('Lots', 0)) for t in trades) / total_trades if total_trades > 0 else 0
    
    # Calculate win rate
    winning_trades = sum(1 for t in trades if float(t.get('Net Profit', 0)) > 0)
    win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Average profit per trade
    avg_profit = total_profit / total_trades if total_trades > 0 else 0
    
    # Calculate average SL (Max Loss Pips)
    avg_sl = sum(abs(float(t.get('Max Loss Pips', 0))) for t in trades) / total_trades if total_trades > 0 else 50
    
    return {
        'signal_id': signal_id,
        'total_trades': total_trades,
        'total_profit': total_profit,
        'primary_symbol': primary_symbol,
        'primary_direction': primary_direction,
        'ea_type': primary_ea,
        'avg_lot': avg_lot,
        'win_rate': win_rate,
        'avg_profit': avg_profit,
        'avg_sl_pips': avg_sl,
        'symbols': symbols,
    }

def calculate_lot_size(account_balance, risk_percent, sl_pips, pip_value=10):
    """
    Calculate recommended lot size
    Formula: Lot Size = (Account Balance × Risk %) / (SL Pips × Pip Value)
    """
    risk_amount = account_balance * risk_percent
    lot_size = risk_amount / (sl_pips * pip_value)
    return round(lot_size, 2)

def find_gbpcad_signals():
    """Find all signals with GBPCAD trades"""
    gbpcad_signals = []
    
    for csv_file in DOWNLOADS_DIR.glob("forex-forest-signals-page-*.csv"):
        signal_id = csv_file.stem.split('-')[-1]
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('Symbol') == 'GBPCAD':
                    gbpcad_signals.append(int(signal_id))
                    break
    
    return gbpcad_signals

def generate_portfolio_report(portfolio_id, config):
    """Generate HTML and JSON report for a portfolio"""
    print(f"Generating {portfolio_id}: {config['name']}")
    
    # Handle P4 special case (GBPCAD signals)
    if portfolio_id == "P4" and 'filter_symbol' in config:
        config['signals'] = find_gbpcad_signals()
        print(f"  Found {len(config['signals'])} GBPCAD signals")
    
    # Analyze each signal
    signal_analyses = []
    for signal_id in config['signals']:
        analysis = analyze_signal(signal_id)
        if analysis:
            signal_analyses.append(analysis)
    
    # Calculate portfolio metrics
    total_profit = sum(s['total_profit'] for s in signal_analyses)
    total_trades = sum(s['total_trades'] for s in signal_analyses)
    weighted_win_rate = sum(s['win_rate'] * s['total_trades'] for s in signal_analyses) / total_trades if total_trades > 0 else 0
    
    # Calculate recommended lot sizes
    risk_per_trade = config['risk_per_trade']
    capital = config['capital']
    
    for signal in signal_analyses:
        signal['recommended_lot'] = calculate_lot_size(
            capital / len(signal_analyses),
            risk_per_trade,
            signal['avg_sl_pips']
        )
    
    # Prepare JSON data
    json_data = {
        'portfolio_id': portfolio_id,
        'name': config['name'],
        'capital': config['capital'],
        'target': config['target'],
        'strategy': config['strategy'],
        'layers': config['layers'],
        'risk_per_trade': risk_per_trade,
        'total_profit': total_profit,
        'total_trades': total_trades,
        'weighted_win_rate': round(weighted_win_rate, 2),
        'signals': signal_analyses,
        'generated_at': datetime.now().isoformat(),
    }
    
    # Generate HTML
    html = generate_html_report(portfolio_id, config, signal_analyses, total_profit, total_trades, weighted_win_rate)
    
    # Write files
    json_path = OUTPUT_DIR / f"portfolio_{portfolio_id}.json"
    html_path = OUTPUT_DIR / f"portfolio_{portfolio_id}.html"
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, indent=2, ensure_ascii=False)
    
    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"  ✓ Generated {html_path.name}")
    print(f"  ✓ Generated {json_path.name}")
    
    return json_data

def generate_html_report(portfolio_id, config, signal_analyses, total_profit, total_trades, win_rate):
    """Generate HTML report"""
    
    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio {portfolio_id}: {config['name']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            font-size: 32px;
            margin-bottom: 10px;
        }}
        .header .subtitle {{
            font-size: 18px;
            opacity: 0.9;
        }}
        .summary {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            padding: 30px;
            background: #f8f9fa;
        }}
        .summary-card {{
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }}
        .summary-card .label {{
            font-size: 14px;
            color: #666;
            margin-bottom: 8px;
        }}
        .summary-card .value {{
            font-size: 28px;
            font-weight: bold;
            color: #1e3c72;
        }}
        .summary-card .value.positive {{
            color: #10b981;
        }}
        .summary-card .value.negative {{
            color: #ef4444;
        }}
        .content {{
            padding: 30px;
        }}
        .section-title {{
            font-size: 24px;
            color: #1e3c72;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e5e7eb;
        }}
        th {{
            background: #1e3c72;
            color: white;
            font-weight: 600;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .signal-link {{
            color: #667eea;
            text-decoration: none;
            font-weight: 600;
        }}
        .signal-link:hover {{
            text-decoration: underline;
        }}
        .tag {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
        }}
        .tag.buy {{
            background: #d1fae5;
            color: #065f46;
        }}
        .tag.sell {{
            background: #fee2e2;
            color: #991b1b;
        }}
        .formula-box {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            margin: 20px 0;
            border-radius: 8px;
        }}
        .formula-box code {{
            display: block;
            background: #1e3c72;
            color: #10b981;
            padding: 15px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            margin-top: 10px;
            overflow-x: auto;
        }}
        .footer {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            color: #666;
            font-size: 14px;
        }}
        @media (max-width: 768px) {{
            .summary {{
                grid-template-columns: 1fr 1fr;
            }}
            table {{
                font-size: 14px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Portfolio {portfolio_id}</h1>
            <div class="subtitle">{config['name']}</div>
        </div>
        
        <div class="summary">
            <div class="summary-card">
                <div class="label">資金</div>
                <div class="value">${config['capital']:,.0f}</div>
            </div>
            <div class="summary-card">
                <div class="label">目標</div>
                <div class="value" style="font-size: 20px;">{config['target']}</div>
            </div>
            <div class="summary-card">
                <div class="label">策略</div>
                <div class="value" style="font-size: 20px;">{config['strategy']}</div>
            </div>
            <div class="summary-card">
                <div class="label">層數</div>
                <div class="value">{config['layers']}</div>
            </div>
            <div class="summary-card">
                <div class="label">總交易</div>
                <div class="value">{total_trades:,}</div>
            </div>
            <div class="summary-card">
                <div class="label">總盈利</div>
                <div class="value positive">${total_profit:,.0f}</div>
            </div>
            <div class="summary-card">
                <div class="label">勝率</div>
                <div class="value">{win_rate:.1f}%</div>
            </div>
            <div class="summary-card">
                <div class="label">風險/交易</div>
                <div class="value">{config['risk_per_trade']*100:.1f}%</div>
            </div>
        </div>
        
        <div class="content">
            <h2 class="section-title">📊 Signal 詳細資料</h2>
            <table>
                <thead>
                    <tr>
                        <th>Signal ID</th>
                        <th>貨幣對</th>
                        <th>方向</th>
                        <th>EA 類型</th>
                        <th>交易數</th>
                        <th>總盈利</th>
                        <th>勝率</th>
                        <th>建議手數</th>
                    </tr>
                </thead>
                <tbody>
"""
    
    for signal in signal_analyses:
        direction_class = 'buy' if signal['primary_direction'] == 'buy' else 'sell'
        html += f"""                    <tr>
                        <td><a href="../reports/Signal_Deep_Analysis_{signal['signal_id']}.html" class="signal-link">{signal['signal_id']}</a></td>
                        <td>{signal['primary_symbol']}</td>
                        <td><span class="tag {direction_class}">{signal['primary_direction'].upper()}</span></td>
                        <td>{signal['ea_type']}</td>
                        <td>{signal['total_trades']:,}</td>
                        <td>${signal['total_profit']:,.0f}</td>
                        <td>{signal['win_rate']:.1f}%</td>
                        <td>{signal['recommended_lot']:.2f}</td>
                    </tr>
"""
    
    html += """                </tbody>
            </table>
            
            <h2 class="section-title">📐 手數計算公式</h2>
            <div class="formula-box">
                <p><strong>建議手數計算公式：</strong></p>
                <code>建議手數 = (帳戶餘額 × 風險百分比) / (止損點數 × 點值)</code>
                <p style="margin-top: 15px; color: #666;">
                    <strong>示例計算：</strong><br>
                    假設帳戶餘額 = ${config['capital']:,}，風險百分比 = {config['risk_per_trade']*100}%，止損點數 = 50 pips，點值 = $10<br>
                    建議手數 = (${config['capital']:,} × {config['risk_per_trade']}) / (50 × $10) = {calculate_lot_size(config['capital'], config['risk_per_trade'], 50):.2f} 手
                </p>
            </div>
            
            <h2 class="section-title">⚠️ 風險評估</h2>
            <table>
                <thead>
                    <tr>
                        <th>風險指標</th>
                        <th>數值</th>
                        <th>評估</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>單筆風險</td>
                        <td>{0:.1f}%</td>
                        <td>{1}</td>
                    </tr>
                    <tr>
                        <td>總風險敞口</td>
                        <td>{2:.1f}%</td>
                        <td>{3} 個 Signals 同時交易</td>
                    </tr>
                    <tr>
                        <td>平均止損</td>
                        <td>{4:.1f} pips</td>
                        <td>基於歷史數據</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <div class="footer">
            Generated on {5} HKT | Trade Strategy Analyzer
        </div>
    </div>
</body>
</html>
"""
    
    # Format the risk assessment table
    risk_per_trade_pct = config['risk_per_trade'] * 100
    risk_level = '✅ 低風險' if config['risk_per_trade'] <= 0.02 else '⚠️ 中等風險' if config['risk_per_trade'] <= 0.03 else '🔴 高風險'
    total_risk = config['risk_per_trade'] * 100 * len(signal_analyses)
    avg_sl = sum(s['avg_sl_pips'] for s in signal_analyses) / len(signal_analyses) if signal_analyses else 50
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    html = html.format(
        risk_per_trade_pct,
        risk_level,
        total_risk,
        len(signal_analyses),
        avg_sl,
        timestamp
    )
    
    return html

def main():
    """Main function"""
    print("=" * 60)
    print("Portfolio Report Generator")
    print("=" * 60)
    print()
    
    results = {}
    for portfolio_id, config in PORTFOLIOS.items():
        result = generate_portfolio_report(portfolio_id, config)
        results[portfolio_id] = result
        print()
    
    print("=" * 60)
    print("✅ All portfolio reports generated successfully!")
    print(f"Output directory: {OUTPUT_DIR}")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    main()
