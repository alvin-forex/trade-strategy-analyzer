#!/usr/bin/env python3
"""
EA Strategy Comparison - 對比唔同 EA 嘅表現
"""

import os
from typing import Dict, List, Any
from datetime import datetime


def generate_comparison_report(
    reports: List[Dict[str, Any]],
    output_path: str
):
    """
    生成 EA 對比報告
    
    Args:
        reports: [{name, stats, positions}, ...]
        output_path: 輸出路徑
    """
    
    # Comparison table
    comp_rows = ""
    metrics = [
        ('倉位數', 'total_positions', 'int'),
        ('勝率', 'win_rate', 'pct'),
        ('Profit Factor', 'profit_factor', 'f2'),
        ('總盈虧', 'total_profit', 'money'),
        ('Max DD', 'max_dd', 'money'),
        ('Max DD%', 'max_dd_percent', 'pct'),
        ('平均層數', 'avg_layers', 'f1'),
        ('平均持倉', 'avg_holding_time_hours', 'hours'),
        ('Sharpe', 'sharpe_ratio', 'f2'),
        ('Calmar', 'calmar_ratio', 'f2'),
        ('CVaR 95%', 'cvar_95', 'f1'),
        ('最大連虧', 'max_consecutive_losses', 'int'),
        ('總 Swap', 'total_swap', 'money'),
    ]
    
    for label, key, fmt in metrics:
        values = []
        for r in reports:
            v = r['stats']['overall'].get(key, 0)
            if fmt == 'int':
                values.append(f'{int(v)}')
            elif fmt == 'pct':
                values.append(f'{v:.1f}%')
            elif fmt == 'f2':
                values.append(f'{v:.2f}')
            elif fmt == 'f1':
                values.append(f'{v:.1f}')
            elif fmt == 'money':
                values.append(f'${v:.2f}')
            elif fmt == 'hours':
                values.append(f'{v:.0f}h')
        
        # Find best value
        cells = ""
        for i, v in enumerate(values):
            best = False
            if key in ('win_rate', 'profit_factor', 'sharpe_ratio', 'calmar_ratio', 'avg_win_loss_ratio'):
                best = v == max(values)
            elif key in ('max_dd', 'max_dd_percent', 'cvar_95', 'max_consecutive_losses'):
                best = v == min(values)  # lower is better for risk metrics
            elif key == 'total_profit':
                best = v == max(values)
            
            style = 'font-weight:bold;color:#28a745;' if best else ''
            cells += f'<td style="{style}">{v}</td>'
        
        comp_rows += f'<tr><td><strong>{label}</strong></td>{cells}</tr>'
    
    # EA name header
    header_cells = "".join(f'<th>{r["name"]}</th>' for r in reports)
    
    # Equity curves side by side
    equity_svgs = ""
    colors = ['#0f3460', '#e94560', '#28a745', '#fd7e14', '#6f42c1']
    for idx, r in enumerate(reports):
        positions = r['positions']
        equity_data = []
        cum = 0
        for p in positions:
            cum += p.get('net_profit', 0) or 0
            equity_data.append({'cum_pnl': round(cum, 2)})
        
        svg = _mini_equity_svg(equity_data, colors[idx % len(colors)], 400, 200)
        equity_svgs += f'<div style="flex:1;min-width:300px;"><h3>{r["name"]}</h3>{svg}</div>'
    
    # Symbol comparison
    sym_section = ""
    all_symbols = set()
    for r in reports:
        all_symbols.update(r['stats']['by_symbol'].keys())
    
    if all_symbols:
        sym_header = "".join(f'<th>{r["name"]} PF</th><th>{r["name"]} WR</th>' for r in reports)
        sym_rows = ""
        for sym in sorted(all_symbols):
            cells = ""
            for r in reports:
                s = r['stats']['by_symbol'].get(sym, {})
                pf = s.get('profit_factor', 0) or 0
                wr = s.get('win_rate', 0) or 0
                color = '#d4edda' if pf > 2 else ('#fff3cd' if pf > 1 else '#f8d7da')
                cells += f'<td style="background:{color}">{pf:.2f}</td><td>{wr:.1f}%</td>'
            sym_rows += f'<tr><td><strong>{sym}</strong></td>{cells}</tr>'
        
        sym_section = f'''
        <h2>📊 貨幣對對比</h2>
        <table>
        <tr><th>貨幣對</th>{sym_header}</tr>
        {sym_rows}
        </table>
        '''
    
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>EA 策略對比報告</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; color: #333; padding: 16px; }}
.container {{ max-width: 1200px; margin: 0 auto; }}
h1 {{ font-size: 1.5em; margin-bottom: 8px; color: #1a1a2e; }}
h2 {{ font-size: 1.2em; margin: 24px 0 12px; color: #16213e; border-bottom: 2px solid #0f3460; padding-bottom: 4px; }}
.subtitle {{ color: #666; margin-bottom: 16px; font-size: 0.9em; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 16px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
th {{ background: #0f3460; color: white; padding: 10px 8px; text-align: center; font-size: 0.8em; }}
td {{ padding: 8px; border-bottom: 1px solid #eee; font-size: 0.85em; text-align: center; }}
tr:nth-child(even) {{ background: #f8f9fa; }}
.equity-grid {{ display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 16px; }}
@media (max-width: 600px) {{ .equity-grid {{ flex-direction: column; }} th, td {{ padding: 6px 4px; font-size: 0.75em; }} }}
</style>
</head>
<body>
<div class="container">
<h1>🦀 EA 策略對比報告</h1>
<p class="subtitle">生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

<h2>📈 核心指標對比</h2>
<table>
<tr><th>指標</th>{header_cells}</tr>
{comp_rows}
</table>

<h2>📉 收益曲線對比</h2>
<div class="equity-grid">
{equity_svgs}
</div>

{sym_section}

</div>
</body>
</html>"""
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"對比報告已生成：{output_path}")


def _mini_equity_svg(equity_data: list, color: str, width: int, height: int) -> str:
    if not equity_data:
        return "<p>無數據</p>"
    
    margin = 30
    chart_w = width - 2 * margin
    chart_h = height - 2 * margin
    
    values = [d['cum_pnl'] for d in equity_data]
    min_v, max_v = min(values), max(values)
    range_v = max_v - min_v if max_v != min_v else 1
    
    points = []
    for i, v in enumerate(values):
        x = margin + (i / max(len(values) - 1, 1)) * chart_w
        y = margin + chart_h - ((v - min_v) / range_v) * chart_h
        points.append(f"{x:.1f},{y:.1f}")
    
    zero_y = margin + chart_h - ((0 - min_v) / range_v) * chart_h
    polyline = " ".join(points)
    fill = f"{margin},{margin+chart_h} " + polyline + f" {margin+chart_w},{margin+chart_h}"
    
    return f"""
    <svg viewBox="0 0 {width} {height}" style="width:100%;height:auto;">
        <line x1="{margin}" y1="{zero_y:.1f}" x2="{margin+chart_w}" y2="{zero_y:.1f}" stroke="#ccc" stroke-dasharray="4"/>
        <text x="{margin-5}" y="{zero_y:.1f}" text-anchor="end" font-size="9" fill="#999">$0</text>
        <text x="{margin-5}" y="{margin}" text-anchor="end" font-size="9" fill="#999">${max_v:.0f}</text>
        <text x="{margin-5}" y="{margin+chart_h}" text-anchor="end" font-size="9" fill="#999">${min_v:.0f}</text>
        <polygon points="{fill}" fill="{color}22" stroke="none"/>
        <polyline points="{polyline}" fill="none" stroke="{color}" stroke-width="2"/>
    </svg>
    """
