#!/usr/bin/env python3
"""
Report Generator - HTML 報告生成（緊湊版）
"""

import os
import re
from typing import Dict, List, Any
from datetime import datetime


def _extract_signal_info(csv_name: str) -> dict:
    """Extract signal ID and URL from CSV filename."""
    m = re.search(r'page-(\d+)', csv_name or '')
    if m:
        sid = m.group(1)
        return {'id': sid, 'url': f'https://signals.algoforest.com/signals/{sid}', 'name': f'AlgoForest Signal #{sid}'}
    return {'id': '', 'url': '', 'name': csv_name}


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
    strategy_info = stats.get('strategy_info', {})
    
    signal = _extract_signal_info(csv_name)
    
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
    
    # ── Compact summary line ──
    wr = overall.get('win_rate', 0)
    total_pl = overall.get('total_profit', 0)
    pf = overall.get('profit_factor', 0)
    avg_layers = overall.get('avg_layers', 0)
    avg_hold = overall.get('avg_holding_time_hours', 0)
    sharpe = overall.get('sharpe_ratio', 0)
    max_dd = overall.get('max_dd', 0)
    
    wr_c = '#28a745' if wr >= 70 else ('#ffc107' if wr >= 50 else '#dc3545')
    pl_c = '#28a745' if total_pl > 0 else '#dc3545'
    pf_str = '∞' if pf != pf or pf > 999 else f'{pf:.2f}'
    pf_c = '#28a745' if (pf == pf and pf > 2) else ('#ffc107' if (pf == pf and pf > 1) else '#dc3545')
    
    summary_text = f"""
    <div class="compact-summary">
        <span class="si">Cycles <b>{len(positions)}</b></span>
        <span class="si">WR <b style="color:{wr_c}">{wr:.0f}%</b></span>
        <span class="si">P/L <b style="color:{pl_c}">${total_pl:,.2f}</b></span>
        <span class="si">PF <b style="color:{pf_c}">{pf_str}</b></span>
        <span class="si">DD <b style="color:#dc3545">${max_dd:,.2f}</b></span>
        <span class="si">Avg Lv <b>{avg_layers:.1f}</b></span>
        <span class="si">Hold <b>{avg_hold:.0f}h</b></span>
        <span class="si">Sharpe <b>{sharpe:.2f}</b></span>
    </div>
    """
    
    # Strategy info line
    strategy_line = ""
    if strategy_info:
        stype = strategy_info.get('strategy_type', '')
        is_martin = strategy_info.get('is_martingale', False)
        lot_exp = strategy_info.get('lot_exp', '')
        if is_martin:
            strategy_line = f'<div class="strategy-tag">⚠️ Martingale · lotExp={lot_exp}</div>'
        else:
            strategy_line = f'<div class="strategy-tag">Strategy: {stype}</div>'
    
    # Signal header
    signal_html = ""
    if signal.get('url'):
        signal_html = f'<div class="signal-link">🔗 <a href="{signal["url"]}" target="_blank">{signal["name"]}</a></div>'
    
    # Grade distribution — compact inline
    graded = {'A': 0, 'B': 0, 'C': 0, 'D': 0}
    for p in positions:
        s = p.get('final_score', 0)
        if s >= 80: graded['A'] += 1
        elif s >= 60: graded['B'] += 1
        elif s >= 40: graded['C'] += 1
        else: graded['D'] += 1
    
    grade_inline = f"""
    <div class="grade-bar">
        <span style="color:#28a745">A:{graded['A']}</span>
        <span style="color:#ffc107">B:{graded['B']}</span>
        <span style="color:#fd7e14">C:{graded['C']}</span>
        <span style="color:#dc3545">D:{graded['D']}</span>
    </div>
    """
    
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

    # Market context section
    market_context_html = _render_market_context(stats)
    
    # Symbol table rows
    symbol_rows = ""
    for sym, s in sorted(symbol_stats.items(), key=lambda x: x[1].get('profit_factor', 0) or 0, reverse=True):
        pf_val = s.get('profit_factor', 0) or 0
        wr_val = s.get('win_rate', 0) or 0
        avg_pl_val = s.get('avg_profit', 0) or 0
        pl_c2 = '#28a745' if avg_pl_val > 0 else '#dc3545'
        pf_str2 = '∞' if pf_val != pf_val or pf_val > 999 else f'{pf_val:.2f}'
        symbol_rows += f"""
        <tr>
            <td><b>{sym}</b></td>
            <td>{s.get('total_positions', 0)}</td>
            <td style="color:{'#28a745' if wr_val>=70 else '#dc3545'};font-weight:bold">{wr_val:.0f}%</td>
            <td style="font-weight:bold">{pf_str2}</td>
            <td style="color:{pl_c2};font-weight:bold">${avg_pl_val:,.2f}</td>
            <td>${s.get('max_dd', 0):.2f}</td>
            <td>{s.get('avg_layers', 0):.1f}</td>
        </tr>"""
    
    # Layer stats
    layer_rows = ""
    for layer_key, s in sorted(layer_stats.items()):
        avg_pl_val = s.get('avg_profit', 0) or 0
        pl_c2 = '#28a745' if avg_pl_val > 0 else '#dc3545'
        layer_rows += f"""
        <tr>
            <td>{layer_key}</td>
            <td>{s.get('count', 0)}</td>
            <td>{s.get('percentage', 0):.1f}%</td>
            <td style="color:{pl_c2};font-weight:bold">${avg_pl_val:,.2f}</td>
            <td>{s.get('win_rate', 0):.0f}%</td>
            <td>{s.get('profit_factor', 0):.2f}</td>
        </tr>"""
    
    # Time stats
    time_rows = ""
    for period, s in time_stats.items():
        avg_pl_val = s.get('avg_profit', 0) or 0
        pl_c2 = '#28a745' if avg_pl_val > 0 else '#dc3545'
        time_rows += f"""
        <tr>
            <td>{period}</td>
            <td>{s.get('count', 0)}</td>
            <td>{s.get('win_rate', 0):.0f}%</td>
            <td style="color:{pl_c2};font-weight:bold">${avg_pl_val:,.2f}</td>
            <td>{s.get('profit_factor', 0):.2f}</td>
        </tr>"""
    
    # Direction stats (only if mixed)
    dir_rows = ""
    for d, s in direction_stats.items():
        avg_pl_val = s.get('avg_profit', 0) or 0
        pl_c2 = '#28a745' if avg_pl_val > 0 else '#dc3545'
        dir_rows += f"""
        <tr>
            <td>{d}</td>
            <td>{s.get('count', 0)}</td>
            <td>{s.get('win_rate', 0):.0f}%</td>
            <td style="color:{pl_c2};font-weight:bold">${avg_pl_val:,.2f}</td>
            <td>{s.get('profit_factor', 0):.2f}</td>
        </tr>"""
    
    # Position detail rows
    pos_rows = ""
    for i, p in enumerate(positions[:50]):
        net = p.get('net_profit', 0) or 0
        sym = p.get('symbol', 'N/A')
        direction = p.get('direction', 'N/A')
        layers = p.get('max_layer', 0)
        ht = p.get('holding_time_hours', 0) or 0
        final_s = p.get('final_score', 0)
        gc = '#28a745' if final_s >= 80 else ('#ffc107' if final_s >= 60 else ('#fd7e14' if final_s >= 40 else '#dc3545'))
        nc = '#28a745' if net > 0 else '#dc3545'
        
        pos_rows += f"""
        <tr>
            <td>{i+1}</td>
            <td>{sym}</td>
            <td>{direction}</td>
            <td>{layers}</td>
            <td>{p.get('total_lots', 0):.2f}</td>
            <td style="color:{nc};font-weight:bold">${net:,.2f}</td>
            <td>{ht:.0f}h</td>
            <td style="color:{gc};font-weight:bold">{final_s:.0f}</td>
        </tr>"""
    
    # SET params — collapsible details
    set_summary = ""
    for category, params in set_params.items():
        if not params or category == '_meta':
            continue
        items = ""
        for k, v in params.items():
            items += f"<tr><td><code>{k}</code></td><td>{v}</td></tr>\n"
        if items:
            set_summary += f"<details><summary>{category} ({len(params)})</summary><table class='set-table'>{items}</table></details>"
    
    # Only show direction section if more than 1 direction
    direction_section = ""
    if len(direction_stats) > 1:
        direction_section = f"""
        <h2>📐 方向分析</h2>
        <table>
        <tr><th>方向</th><th>倉位</th><th>WR</th><th>均盈虧</th><th>PF</th></tr>
        {dir_rows}
        </table>"""
    
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>策略分析報告</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f5f7fa; color: #333; padding: 16px; }}
.container {{ max-width: 1000px; margin: 0 auto; }}
h1 {{ font-size: 1.3em; margin-bottom: 4px; color: #1a1a2e; }}
h2 {{ font-size: 1.05em; margin: 18px 0 6px; color: #16213e; border-bottom: 2px solid #0f3460; padding-bottom: 3px; }}
h3 {{ font-size: 0.9em; margin: 10px 0 4px; color: #1a1a2e; }}
.subtitle {{ color: #888; margin-bottom: 8px; font-size: 0.78em; }}
.signal-link {{ font-size: 0.9em; margin-bottom: 6px; }}
.signal-link a {{ color: #0f3460; text-decoration: none; font-weight: 600; }}
.signal-link a:hover {{ text-decoration: underline; }}
.compact-summary {{ display: flex; flex-wrap: wrap; gap: 4px 14px; padding: 10px 14px; background: white; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); margin-bottom: 10px; font-size: 0.88em; }}
.si {{ white-space: nowrap; }}
.strategy-tag {{ display: inline-block; padding: 3px 8px; background: #fff3cd; border-radius: 4px; font-size: 0.78em; margin-bottom: 8px; }}
.grade-bar {{ display: inline-flex; gap: 10px; padding: 4px 10px; background: white; border-radius: 5px; font-weight: bold; font-size: 0.82em; margin-left: 8px; }}
.summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 20px; }}
.card {{ background: white; border-radius: 8px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); text-align: center; }}
.card .value {{ font-size: 1.4em; font-weight: bold; color: #0f3460; }}
.card .label {{ font-size: 0.75em; color: #888; margin-top: 4px; }}
table {{ width: 100%; border-collapse: collapse; margin-bottom: 12px; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
th {{ background: #0f3460; color: white; padding: 7px 5px; text-align: left; font-size: 0.75em; }}
td {{ padding: 6px 5px; border-bottom: 1px solid #eee; font-size: 0.8em; }}
tr:hover {{ background: #f8f9fa; }}
.set-table {{ font-size: 0.75em; box-shadow: none; margin-bottom: 2px; }}
.set-table td {{ padding: 2px 5px; }}
.chart-container {{ background: white; border-radius: 8px; padding: 10px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); overflow-x: auto; }}
details {{ margin-bottom: 6px; }}
details summary {{ cursor: pointer; padding: 5px 8px; background: #e9ecef; border-radius: 4px; font-size: 0.82em; font-weight: 600; }}
details[open] summary {{ border-radius: 4px 4px 0 0; }}
@media (max-width: 600px) {{ .compact-summary {{ font-size: 0.78em; gap: 3px 8px; }} th, td {{ padding: 4px 2px; font-size: 0.7em; }} }}
</style>
</head>
<body>
<div class="container">
<h1>🦀 策略分析報告</h1>
{signal_html}
<p class="subtitle">生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}</p>

{summary_text}
{strategy_line}{grade_inline}

<h2>📈 收益曲線</h2>
<div class="chart-container">{equity_svg}</div>

{grade_html}
{market_context_html}

<h2>🏆 貨幣對</h2>
<table>
<tr><th>Pair</th><th>倉位</th><th>WR</th><th>PF</th><th>均盈虧</th><th>Max DD</th><th>均層</th></tr>
{symbol_rows}
</table>

<h2>📊 層數分析</h2>
<table>
<tr><th>層數</th><th>倉位</th><th>佔比</th><th>均盈虧</th><th>WR</th><th>PF</th></tr>
{layer_rows}
</table>

<h2>🕐 時段</h2>
<table>
<tr><th>時段</th><th>倉位</th><th>WR</th><th>均盈虧</th><th>PF</th></tr>
{time_rows}
</table>
{direction_section}

<h2>📋 倉位明細（前 50）</h2>
<table>
<tr><th>#</th><th>Pair</th><th>方向</th><th>層</th><th>手數</th><th>盈虧</th><th>持倉</th><th>分</th></tr>
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
    height = 260
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
    fill_points = f"{margin},{margin + chart_h} " + polyline + f" {margin + chart_w},{margin + chart_h}"
    
    return f"""
    <svg viewBox="0 0 {width} {height}" style="width:100%;height:auto;">
        <line x1="{margin}" y1="{zero_y:.1f}" x2="{margin+chart_w}" y2="{zero_y:.1f}" stroke="#ccc" stroke-dasharray="4"/>
        <text x="{margin-5}" y="{zero_y:.1f}" text-anchor="end" font-size="9" fill="#999">$0</text>
        <text x="{margin-5}" y="{margin}" text-anchor="end" font-size="9" fill="#999">${max_v:.0f}</text>
        <text x="{margin-5}" y="{margin+chart_h}" text-anchor="end" font-size="9" fill="#999">${min_v:.0f}</text>
        <polygon points="{fill_points}" fill="rgba(15,52,96,0.1)" stroke="none"/>
        <polyline points="{polyline}" fill="none" stroke="#0f3460" stroke-width="2"/>
    </svg>
    """


def _render_market_context(stats: dict) -> str:
    """Render market context analysis section."""
    ctx = stats.get('market_context', {})
    if not ctx:
        return ""
    
    dim_labels = {
        'D1_adx_regime': 'ADX 趨勢',
        'D1_trend': 'D1 方向',
        'D1_rsi_bucket': 'RSI 區間',
        'D1_atr_pct_bucket': 'ATR 波動',
    }
    
    sections = []
    for dim_key, label in dim_labels.items():
        items = ctx.get(dim_key, [])
        if not items:
            continue
        
        rows = ""
        for item in items:
            avg_pl = item.get('avg_pl', 0)
            nc = '#28a745' if avg_pl > 300 else ('#333' if avg_pl > 0 else '#dc3545')
            rows += f"""
            <tr>
                <td><b>{item['label']}</b></td>
                <td>{item['count']}</td>
                <td>{item.get('win_rate', 0):.0f}%</td>
                <td style="color:{nc};font-weight:bold">${avg_pl:,.2f}</td>
                <td>{item.get('avg_layers', 0):.1f}</td>
                <td>{item.get('avg_hold', 0):.0f}h</td>
            </tr>"""
        
        sections.append(f"""
        <h3>{label}</h3>
        <table>
        <tr><th>狀態</th><th>數量</th><th>WR</th><th>均盈虧</th><th>均層</th><th>均持倉</th></tr>
        {rows}
        </table>""")
    
    if not sections:
        return ""
    
    return f"""
    <h2>🌍 市場環境</h2>
    {''.join(sections)}
    """
