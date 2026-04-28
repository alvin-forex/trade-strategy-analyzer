#!/usr/bin/env python3
"""
Report Generator - HTML 報告生成
"""

import os
from typing import Dict, List, Any
from datetime import datetime


def generate_html_report(
    stats: Dict[str, Any],
    positions: List[Dict[str, Any]],
    set_params: Dict[str, Any],
    output_path: str,
    csv_name: str = ""
):
    """生成 HTML 報告"""
    overall = stats.get('overall', {})
    symbol_stats = stats.get('by_symbol', {})
    layer_stats = stats.get('by_layer', {})
    time_stats = stats.get('by_time', {})
    direction_stats = stats.get('by_direction', {})
    
    # Get equity curve data
    equity_data = []
    cum_pnl = 0
    for p in positions:
        pnl = p.get('net_profit', 0) or 0
        cum_pnl += pnl
        equity_data.append({
            'date': p.get('close_time', '').strftime('%Y-%m-%d %H:%M') if hasattr(p.get('close_time', ''), 'strftime') else str(p.get('close_time', '')),
            'pnl': pnl,
            'cum_pnl': round(cum_pnl, 2)
        })
    
    # Symbol table rows
    symbol_rows = ""
    for sym, s in sorted(symbol_stats.items(), key=lambda x: x[1].get('profit_factor', 0) or 0, reverse=True):
        pf = s.get('profit_factor', 0) or 0
        wr = s.get('win_rate', 0) or 0
        color = '#d4edda' if pf > 2 else ('#fff3cd' if pf > 1 else '#f8d7da')
        symbol_rows += f"""
        <tr style="background:{color}">
            <td>{sym}</td>
            <td>{s.get('total_positions', 0)}</td>
            <td>{wr:.1f}%</td>
            <td>{pf:.2f}</td>
            <td>{s.get('avg_profit', 0):.2f}</td>
            <td>{s.get('max_dd', 0):.2f}</td>
            <td>{s.get('avg_layers', 0):.1f}</td>
        </tr>"""
    
    # Layer stats
    layer_rows = ""
    for layer_key, s in sorted(layer_stats.items()):
        layer_rows += f"""
        <tr>
            <td>{layer_key}</td>
            <td>{s.get('count', 0)}</td>
            <td>{s.get('percentage', 0):.1f}%</td>
            <td>${s.get('avg_profit', 0):.2f}</td>
            <td>{s.get('win_rate', 0):.1f}%</td>
            <td>{s.get('profit_factor', 0):.2f}</td>
        </tr>"""
    
    # Time stats
    time_rows = ""
    for period, s in time_stats.items():
        time_rows += f"""
        <tr>
            <td>{period}</td>
            <td>{s.get('count', 0)}</td>
            <td>{s.get('win_rate', 0):.1f}%</td>
            <td>{s.get('avg_profit', 0):.2f}</td>
            <td>{s.get('profit_factor', 0):.2f}</td>
        </tr>"""
    
    # Direction stats
    dir_rows = ""
    for d, s in direction_stats.items():
        dir_rows += f"""
        <tr>
            <td>{d}</td>
            <td>{s.get('count', 0)}</td>
            <td>{s.get('win_rate', 0):.1f}%</td>
            <td>${s.get('avg_profit', 0):.2f}</td>
            <td>{s.get('profit_factor', 0):.2f}</td>
        </tr>"""
    
    # Top 50 positions detail
    pos_rows = ""
    for i, p in enumerate(positions[:50]):
        net = p.get('net_profit', 0) or 0
        color = '#d4edda' if net > 0 else '#f8d7da'
        sym = p.get('symbol', 'N/A')
        direction = p.get('direction', 'N/A')
        layers = p.get('max_layer', 0)
        ht = p.get('holding_time_hours', 0) or 0
        entry_s = p.get('entry_score', 0)
        strat_s = p.get('strategy_score', 0)
        final_s = p.get('final_score', 0)
        grade_color = '#28a745' if final_s >= 80 else ('#ffc107' if final_s >= 60 else ('#fd7e14' if final_s >= 40 else '#dc3545'))
        
        pos_rows += f"""
        <tr style="background:{color}">
            <td>{i+1}</td>
            <td>{sym}</td>
            <td>{direction}</td>
            <td>{layers}</td>
            <td>{p.get('total_lots', 0):.2f}</td>
            <td>{net:.2f}</td>
            <td>{ht:.1f}h</td>
            <td style="color:{grade_color};font-weight:bold">{final_s:.0f}</td>
        </tr>"""
    
    # SET params summary
    set_summary = ""
    for category, params in set_params.items():
        items = ""
        for k, v in params.items():
            items += f"<tr><td><code>{k}</code></td><td>{v}</td></tr>\n"
        set_summary += f"<h4>{category}</h4><table class='set-table'>{items}</table>"
    
    # Grade distribution
    graded = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    for p in positions:
        s = p.get('final_score', 0)
        if s >= 80: graded['A'] += 1
        elif s >= 60: graded['B'] += 1
        elif s >= 40: graded['C'] += 1
        else: graded['D'] += 1
    
    grade_html = f"""
    <h2>🏅 質量評分分佈</h2>
    <div class="summary-grid">
        <div class="card" style="border-left:4px solid #28a745"><div class="value" style="color:#28a745">{graded['A']}</div><div class="label">A 優質 (≥80)</div></div>
        <div class="card" style="border-left:4px solid #ffc107"><div class="value" style="color:#ffc107">{graded['B']}</div><div class="label">B 一般 (60-79)</div></div>
        <div class="card" style="border-left:4px solid #fd7e14"><div class="value" style="color:#fd7e14">{graded['C']}</div><div class="label">C 偏弱 (40-59)</div></div>
        <div class="card" style="border-left:4px solid #dc3545"><div class="value" style="color:#dc3545">{graded['D']}</div><div class="label">D 差 (<40)</div></div>
    </div>
    """
    
    # Equity curve SVG
    equity_svg = generate_equity_svg(equity_data)
    
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>交易策略分析報告</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; color: #333; padding: 16px; }}
.container {{ max-width: 1000px; margin: 0 auto; }}
h1 {{ font-size: 1.5em; margin-bottom: 8px; color: #1a1a2e; }}
h2 {{ font-size: 1.2em; margin: 24px 0 12px; color: #16213e; border-bottom: 2px solid #0f3460; padding-bottom: 4px; }}
h3 {{ font-size: 1em; margin: 16px 0 8px; color: #1a1a2e; }}
.subtitle {{ color: #666; margin-bottom: 16px; font-size: 0.9em; }}
.summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }}
.card {{ background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }}
.card .value {{ font-size: 1.4em; font-weight: bold; color: #0f3460; }}
.card .label {{ font-size: 0.75em; color: #888; margin-top: 4px; }}
.card.good .value {{ color: #28a745; }}
.card.bad .value {{ color: #dc3545; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
th {{ background: #0f3460; color: white; padding: 10px 8px; text-align: left; font-size: 0.8em; }}
td {{ padding: 8px; border-bottom: 1px solid #eee; font-size: 0.85em; }}
tr:hover {{ opacity: 0.9; }}
.set-table {{ font-size: 0.8em; }}
.set-table td {{ padding: 4px 8px; }}
.chart-container {{ background: white; border-radius: 8px; padding: 16px; margin-bottom: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow-x: auto; }}
.legend {{ display: flex; gap: 16px; margin-top: 8px; font-size: 0.8em; }}
.legend span {{ display: flex; align-items: center; gap: 4px; }}
.legend .dot {{ width: 12px; height: 12px; border-radius: 3px; }}
@media (max-width: 600px) {{ .summary-grid {{ grid-template-columns: repeat(2, 1fr); }} th, td {{ padding: 6px 4px; font-size: 0.75em; }} }}
</style>
</head>
<body>
<div class="container">
<h1>🦀 交易策略分析報告</h1>
<p class="subtitle">{csv_name} | 生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

<div class="summary-grid">
    <div class="card"><div class="value">{overall.get('total_positions', 0)}</div><div class="label">倉位數</div></div>
    <div class="card {'good' if overall.get('win_rate', 0) > 60 else 'bad'}"><div class="value">{overall.get('win_rate', 0):.1f}%</div><div class="label">勝率</div></div>
    <div class="card {'good' if overall.get('profit_factor', 0) > 1.5 else 'bad'}"><div class="value">{overall.get('profit_factor', 0):.2f}</div><div class="label">Profit Factor</div></div>
    <div class="card {'good' if overall.get('total_profit', 0) > 0 else 'bad'}"><div class="value">${overall.get('total_profit', 0):.2f}</div><div class="label">總盈虧</div></div>
    <div class="card bad"><div class="value">${overall.get('max_dd', 0):.2f}</div><div class="label">Max DD</div></div>
    <div class="card"><div class="value">{overall.get('max_dd_percent', 0):.1f}%</div><div class="label">Max DD%</div></div>
    <div class="card"><div class="value">{overall.get('avg_layers', 0):.1f}</div><div class="label">平均層數</div></div>
    <div class="card"><div class="value">{overall.get('avg_holding_time_hours', 0):.0f}h</div><div class="label">平均持倉</div></div>
    <div class="card"><div class="value">{overall.get('sharpe_ratio', 0):.2f}</div><div class="label">Sharpe</div></div>
    <div class="card"><div class="value">{overall.get('calmar_ratio', 0):.2f}</div><div class="label">Calmar</div></div>
    <div class="card"><div class="value">{overall.get('cvar_95', 0):.1f}</div><div class="label">CVaR 95%</div></div>
    <div class="card"><div class="value">{overall.get('max_consecutive_losses', 0)}</div><div class="label">最大連虧</div></div>
    <div class="card"><div class="value">${overall.get('total_swap', 0):.2f}</div><div class="label">總 Swap</div></div>
    <div class="card"><div class="value">{overall.get('skewness', 0):.1f}</div><div class="label">偏度</div></div>
</div>

<h2>📈 收益曲線</h2>
<div class="chart-container">{equity_svg}</div>

{grade_html}

<h2>🏆 貨幣對排名</h2>
<table>
<tr><th>貨幣對</th><th>倉位數</th><th>勝率</th><th>PF</th><th>平均盈虧</th><th>Max DD</th><th>平均層數</th></tr>
{symbol_rows}
</table>

<h2>📊 層數分析</h2>
<table>
<tr><th>層數範圍</th><th>倉位數</th><th>佔比</th><th>平均盈虧</th><th>勝率</th><th>PF</th></tr>
{layer_rows}
</table>

<h2>🕐 時段分析</h2>
<table>
<tr><th>時段</th><th>倉位數</th><th>勝率</th><th>平均盈虧</th><th>PF</th></tr>
{time_rows}
</table>

<h2>📐 方向分析</h2>
<table>
<tr><th>方向</th><th>倉位數</th><th>勝率</th><th>平均盈虧</th><th>PF</th></tr>
{dir_rows}
</table>

<h2>📋 倉位明細（前 50）</h2>
<table>
<tr><th>#</th><th>貨幣對</th><th>方向</th><th>層數</th><th>總手數</th><th>盈虧</th><th>持倉時間</th><th>評分</th></tr>
{pos_rows}
</table>

<h2>⚙️ 策略參數</h2>
{set_summary}

</div>
</body>
</html>"""
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"報告已生成：{output_path}")


def generate_equity_svg(equity_data: list) -> str:
    """生成收益曲線 SVG"""
    if not equity_data:
        return "<p>無數據</p>"
    
    width = 900
    height = 300
    margin = 40
    chart_w = width - 2 * margin
    chart_h = height - 2 * margin
    
    values = [d['cum_pnl'] for d in equity_data]
    min_v = min(values)
    max_v = max(values)
    range_v = max_v - min_v if max_v != min_v else 1
    
    points = []
    for i, d in enumerate(equity_data):
        x = margin + (i / max(len(equity_data) - 1, 1)) * chart_w
        y = margin + chart_h - ((d['cum_pnl'] - min_v) / range_v) * chart_h
        points.append(f"{x:.1f},{y:.1f}")
    
    # Zero line
    zero_y = margin + chart_h - ((0 - min_v) / range_v) * chart_h
    
    polyline = " ".join(points)
    
    # Fill area
    fill_points = f"{margin},{margin + chart_h} " + polyline + f" {margin + chart_w},{margin + chart_h}"
    
    return f"""
    <svg viewBox="0 0 {width} {height}" style="width:100%;height:auto;">
        <line x1="{margin}" y1="{zero_y:.1f}" x2="{margin+chart_w}" y2="{zero_y:.1f}" stroke="#ccc" stroke-dasharray="4"/>
        <text x="{margin-5}" y="{zero_y:.1f}" text-anchor="end" font-size="10" fill="#999">$0</text>
        <text x="{margin-5}" y="{margin}" text-anchor="end" font-size="10" fill="#999">${max_v:.0f}</text>
        <text x="{margin-5}" y="{margin+chart_h}" text-anchor="end" font-size="10" fill="#999">${min_v:.0f}</text>
        <polygon points="{fill_points}" fill="rgba(15,52,96,0.1)" stroke="none"/>
        <polyline points="{polyline}" fill="none" stroke="#0f3460" stroke-width="2"/>
    </svg>
    """
