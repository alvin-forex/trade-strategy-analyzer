#!/usr/bin/env python3
"""
馬汀剖析法分析器 (Martin Strategy Anatomy Analyzer)
分析 Signal 的馬汀特徵：加倉模式、倍數關係、風險遞增、爆倉風險
"""

import csv
import sys
import os
from collections import defaultdict
from datetime import datetime
import re

def parse_csv(filepath):
    """Parse the trading CSV file"""
    trades = []
    with open(filepath, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                trade = {
                    'open_time': row.get('Open Time', ''),
                    'type': row.get('Type', ''),
                    'lots': float(row.get('Lots', 0)),
                    'symbol': row.get('Symbol', ''),
                    'open_price': float(row.get('Open Price', 0)),
                    'close_time': row.get('Close Time', ''),
                    'close_price': float(row.get('Close Price', 0)),
                    'commission': float(row.get('Commission', 0)),
                    'swap': float(row.get('Swap', 0)),
                    'net_pips': float(row.get('Net Pips', 0)),
                    'net_profit': float(row.get('Net Profit', 0)),
                    'max_profit': float(row.get('Max Profit', 0)),
                    'max_pips': float(row.get('Max Pips', 0)),
                    'max_loss': float(row.get('Max Loss', 0)),
                    'max_loss_pips': float(row.get('Max Loss Pips', 0)),
                    'magic': row.get('Magic Number', ''),
                    'comment': row.get('Comment', ''),
                    'hold_hours': float(row.get('Holding Time (Hours)', 0)),
                }
                trades.append(trade)
            except (ValueError, KeyError):
                continue
    return trades

def group_by_symbol(trades):
    """Group trades by currency pair"""
    groups = defaultdict(list)
    for t in trades:
        groups[t['symbol']].append(t)
    return groups

def detect_lot_levels(trades):
    """Detect lot-based levels (L1, L2, L3, ...)"""
    lots_set = sorted(set(t['lots'] for t in trades))
    return lots_set

def classify_martin_trade(trade):
    """Classify a trade as Martin, Reverse Martin, Normal, or Cost Killed"""
    profit = trade['net_profit']
    pips = trade['net_pips']
    cost = abs(trade['commission']) + abs(trade['swap'])
    
    # Classic Martin: profit > 0 but pips < 0 (方向錯但靠加倉/加碼獲利)
    if profit > 0 and pips < 0:
        return 'classic_martin'
    # Reverse Martin: profit < 0 but pips > 0 (方向對但被成本吃掉)
    elif profit < 0 and pips > 0:
        if cost > abs(profit):
            return 'cost_killed'
        return 'reverse_martin'
    # Normal win
    elif profit > 0 and pips > 0:
        return 'normal_win'
    # Normal loss
    elif profit < 0 and pips < 0:
        return 'normal_loss'
    return 'other'

def analyze_martin_depth(trades):
    """Analyze Martin characteristics in depth"""
    results = {
        'total': len(trades),
        'classic_martin': 0,
        'reverse_martin': 0,
        'cost_killed': 0,
        'normal_win': 0,
        'normal_loss': 0,
        'martin_profit_total': 0,
        'normal_profit_total': 0,
        'total_profit': 0,
        'total_loss': 0,
        'max_dd': 0,
        'max_dd_pips': 0,
        'avg_hold_hours': 0,
        'trades_by_type': defaultdict(list),
        'lot_distribution': defaultdict(int),
        'level_escalation': [],  # L1 -> L2 -> L3 transitions
    }
    
    total_hold = 0
    for t in trades:
        ttype = classify_martin_trade(t)
        results['trades_by_type'][ttype].append(t)
        results['lot_distribution'][t['lots']] += 1
        total_hold += t['hold_hours']
        
        if ttype == 'classic_martin':
            results['classic_martin'] += 1
            results['martin_profit_total'] += t['net_profit']
        elif ttype == 'reverse_martin':
            results['reverse_martin'] += 1
        elif ttype == 'cost_killed':
            results['cost_killed'] += 1
        elif ttype == 'normal_win':
            results['normal_win'] += 1
            results['normal_profit_total'] += t['net_profit']
        elif ttype == 'normal_loss':
            results['normal_loss'] += 1
        
        if t['net_profit'] > 0:
            results['total_profit'] += t['net_profit']
        else:
            results['total_loss'] += abs(t['net_profit'])
        
        if abs(t['max_loss']) > results['max_dd']:
            results['max_dd'] = abs(t['max_loss'])
        if abs(t['max_loss_pips']) > results['max_dd_pips']:
            results['max_dd_pips'] = abs(t['max_loss_pips'])
    
    results['avg_hold_hours'] = total_hold / max(len(trades), 1)
    results['win_rate'] = (results['normal_win'] + results['classic_martin']) / max(len(trades), 1) * 100
    
    # Martin dependency ratio
    total_positive = results['martin_profit_total'] + results['normal_profit_total']
    results['martin_dependency'] = (results['martin_profit_total'] / total_positive * 100) if total_positive > 0 else 0
    
    # Lot multiplier analysis
    lots_sorted = sorted(results['lot_distribution'].keys())
    results['lot_multipliers'] = []
    for i in range(1, len(lots_sorted)):
        if lots_sorted[i-1] > 0:
            mult = lots_sorted[i] / lots_sorted[i-1]
            results['lot_multipliers'].append({
                'from': lots_sorted[i-1],
                'to': lots_sorted[i],
                'multiplier': mult
            })
    
    return results

def analyze_level_distribution(trades):
    """Analyze how trades distribute across lot levels"""
    lots_sorted = sorted(set(t['lots'] for t in trades))
    level_stats = []
    
    for i, lot in enumerate(lots_sorted):
        level_trades = [t for t in trades if t['lots'] == lot]
        wins = [t for t in level_trades if t['net_profit'] > 0]
        losses = [t for t in level_trades if t['net_profit'] <= 0]
        
        total_profit = sum(t['net_profit'] for t in level_trades)
        avg_profit = total_profit / max(len(level_trades), 1)
        avg_dd = sum(abs(t['max_loss']) for t in level_trades) / max(len(level_trades), 1)
        avg_pips = sum(t['net_pips'] for t in level_trades) / max(len(level_trades), 1)
        win_rate = len(wins) / max(len(level_trades), 1) * 100
        
        # Martin detection at this level
        martin_count = sum(1 for t in level_trades if classify_martin_trade(t) == 'classic_martin')
        
        level_stats.append({
            'level': f'L{i+1}',
            'lot': lot,
            'count': len(level_trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'avg_dd': avg_dd,
            'avg_pips': avg_pips,
            'martin_count': martin_count,
            'martin_pct': martin_count / max(len(level_trades), 1) * 100,
        })
    
    return level_stats

def calculate_martin_risk_score(stats):
    """Calculate overall Martin risk score (0-100)"""
    score = 0
    
    # Factor 1: Martin dependency (higher = more risky)
    score += min(stats['martin_dependency'] * 0.5, 25)
    
    # Factor 2: Deep level penetration
    num_levels = len(stats.get('level_stats', []))
    if num_levels >= 8:
        score += 25
    elif num_levels >= 6:
        score += 20
    elif num_levels >= 4:
        score += 15
    elif num_levels >= 3:
        score += 10
    
    # Factor 3: Win rate at deep levels
    deep_levels = [ls for ls in stats.get('level_stats', []) if ls['level'] in ['L4', 'L5', 'L6', 'L7', 'L8', 'L9+']]
    if deep_levels:
        deep_wr = sum(ls['win_rate'] for ls in deep_levels) / len(deep_levels)
        if deep_wr < 50:
            score += 25
        elif deep_wr < 60:
            score += 20
        elif deep_wr < 70:
            score += 10
    
    # Factor 4: Lot multiplier aggressiveness
    max_mult = 1
    for m in stats.get('lot_multipliers', []):
        if m['multiplier'] > max_mult:
            max_mult = m['multiplier']
    if max_mult >= 2.5:
        score += 25
    elif max_mult >= 2.0:
        score += 20
    elif max_mult >= 1.8:
        score += 15
    elif max_mult >= 1.5:
        score += 10
    
    return min(score, 100)

def generate_html_report(signal_id, all_results, total_trades, output_path):
    """Generate Martin-focused HTML report"""
    
    # Sort symbols by risk score descending
    sorted_symbols = sorted(all_results.items(), key=lambda x: x[1]['risk_score'], reverse=True)
    
    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🎰 馬汀剖析報告 - Signal #{signal_id}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 11px; color: #333; background: #1a1a2e; padding: 10px; }}
.container {{ max-width: 100%; margin: 0 auto; }}
h1 {{ font-size: 18px; color: #e94560; margin-bottom: 5px; text-align: center; }}
.subtitle {{ font-size: 10px; color: #888; text-align: center; margin-bottom: 15px; }}

.overview {{ background: #16213e; border-radius: 8px; padding: 15px; margin-bottom: 15px; }}
.overview-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; }}
.overview-item {{ text-align: center; padding: 8px; background: #0f3460; border-radius: 6px; }}
.overview-label {{ font-size: 9px; color: #888; }}
.overview-value {{ font-size: 14px; font-weight: bold; color: #e94560; }}

.risk-bar {{ background: #16213e; border-radius: 8px; padding: 12px; margin-bottom: 15px; }}
.risk-bar-inner {{ height: 20px; background: #0f3460; border-radius: 10px; overflow: hidden; }}
.risk-fill {{ height: 100%; border-radius: 10px; transition: width 0.3s; }}

.symbol-card {{ background: #16213e; border-radius: 8px; margin-bottom: 12px; overflow: hidden; border-left: 4px solid #e94560; }}
.symbol-header {{ padding: 8px 12px; font-weight: bold; font-size: 13px; color: #fff; display: flex; justify-content: space-between; align-items: center; }}
.symbol-body {{ padding: 10px 12px; }}

.stats-row {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(70px, 1fr)); gap: 6px; margin-bottom: 8px; }}
.stat {{ text-align: center; padding: 4px; background: #0f3460; border-radius: 4px; }}
.stat-label {{ font-size: 8px; color: #888; }}
.stat-val {{ font-size: 11px; font-weight: bold; color: #eee; }}

table {{ width: 100%; border-collapse: collapse; font-size: 10px; }}
th {{ background: #0f3460; color: #eee; padding: 5px 6px; text-align: center; font-size: 9px; }}
td {{ padding: 4px 6px; text-align: center; border-bottom: 1px solid #1a1a3e; color: #ddd; }}

.green {{ color: #4caf50; font-weight: bold; }}
.red {{ color: #e94560; font-weight: bold; }}
.orange {{ color: #ff9800; font-weight: bold; }}
.yellow {{ color: #fdd835; font-weight: bold; }}

.risk-low {{ border-left-color: #4caf50; }}
.risk-med {{ border-left-color: #ff9800; }}
.risk-high {{ border-left-color: #e94560; }}

.badge {{ display: inline-block; padding: 2px 6px; border-radius: 3px; font-size: 9px; font-weight: bold; }}
.badge-green {{ background: #1b5e20; color: #4caf50; }}
.badge-orange {{ background: #e65100; color: #ff9800; }}
.badge-red {{ background: #b71c1c; color: #e94560; }}

.martin-detail {{ background: #0f3460; border-radius: 4px; padding: 8px; margin-top: 6px; }}
.martin-detail-title {{ font-size: 10px; color: #ff9800; font-weight: bold; margin-bottom: 4px; }}

.footer {{ text-align: center; padding: 10px; color: #555; font-size: 9px; }}
</style>
</head>
<body>
<div class="container">
<h1>🎰 馬汀剖析報告</h1>
<div class="subtitle">Signal #{signal_id} | {total_trades} 筆交易 | {len(all_results)} 貨幣對<br>
生成時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
"""
    
    # Calculate overall stats
    total_martin = sum(r['classic_martin'] for r in all_results.values())
    total_normal_win = sum(r['normal_win'] for r in all_results.values())
    total_martin_profit = sum(r['martin_profit_total'] for r in all_results.values())
    total_normal_profit = sum(r['normal_profit_total'] for r in all_results.values())
    total_profit_all = sum(r['total_profit'] for r in all_results.values())
    total_loss_all = sum(r['total_loss'] for r in all_results.values())
    total_martin_dep = (total_martin_profit / (total_martin_profit + total_normal_profit) * 100) if (total_martin_profit + total_normal_profit) > 0 else 0
    
    # Overall risk score
    avg_risk = sum(r['risk_score'] for r in all_results.values()) / max(len(all_results), 1)
    
    if avg_risk >= 70:
        risk_color = '#e94560'
        risk_label = '高風險'
    elif avg_risk >= 40:
        risk_color = '#ff9800'
        risk_label = '中風險'
    else:
        risk_color = '#4caf50'
        risk_label = '低風險'
    
    html += f"""
<div class="overview">
<div style="text-align:center; margin-bottom:10px; font-size:12px; color:#fff;">📊 整體馬汀風險評估</div>
<div class="overview-grid">
<div class="overview-item">
<div class="overview-label">總交易</div>
<div class="overview-value">{total_trades}</div>
</div>
<div class="overview-item">
<div class="overview-label">Classic Martin</div>
<div class="overview-value">{total_martin}</div>
</div>
<div class="overview-item">
<div class="overview-label">馬丁依賴度</div>
<div class="overview-value">{total_martin_dep:.1f}%</div>
</div>
<div class="overview-item">
<div class="overview-label">總盈利</div>
<div class="overview-value" style="color: {'#4caf50' if total_profit_all > total_loss_all else '#e94560'}">${total_profit_all - total_loss_all:,.2f}</div>
</div>
<div class="overview-item">
<div class="overview-label">風險評級</div>
<div class="overview-value" style="color: {risk_color}">{risk_label} ({avg_risk:.0f}/100)</div>
</div>
</div>
</div>
"""
    
    # Risk bar
    html += f"""
<div class="risk-bar">
<div style="display:flex; justify-content:space-between; margin-bottom:5px; color:#888; font-size:9px;">
<span>🟢 低風險</span><span>🟡 中風險</span><span>🔴 高風險</span>
</div>
<div class="risk-bar-inner">
<div class="risk-fill" style="width: {avg_risk}%; background: {risk_color};"></div>
</div>
<div style="text-align:right; font-size:9px; color:#888; margin-top:2px;">{avg_risk:.0f}/100</div>
</div>
"""
    
    # Summary table
    html += """
<div style="background: #16213e; border-radius: 8px; padding: 10px; margin-bottom: 15px; overflow-x: auto;">
<div style="font-size: 12px; color: #e94560; font-weight: bold; margin-bottom: 8px;">📋 馬汀風險排行（由高到低）</div>
<table>
<thead>
<tr>
<th>貨幣對</th><th>交易數</th><th>勝率</th><th>Martin數</th><th>馬丁%</th>
<th>馬丁依賴</th><th>層級數</th><th>最大倍數</th><th>最深DD</th><th>風險分</th><th>評級</th>
</tr>
</thead>
<tbody>
"""
    
    for symbol, r in sorted_symbols:
        num_levels = len(r.get('level_stats', []))
        max_mult = max((m['multiplier'] for m in r.get('lot_multipliers', [])), default=1)
        risk = r['risk_score']
        
        if risk >= 70:
            badge = '<span class="badge badge-red">🔴 高</span>'
        elif risk >= 40:
            badge = '<span class="badge badge-orange">🟡 中</span>'
        else:
            badge = '<span class="badge badge-green">🟢 低</span>'
        
        martin_pct = (r['classic_martin'] / max(r['total'], 1)) * 100
        
        html += f"""<tr>
<td><strong>{symbol}</strong></td>
<td>{r['total']}</td>
<td class="{'green' if r['win_rate'] >= 70 else 'red'}">{r['win_rate']:.1f}%</td>
<td>{r['classic_martin']}</td>
<td class="{'red' if martin_pct > 5 else 'green'}">{martin_pct:.1f}%</td>
<td class="{'red' if r['martin_dependency'] > 10 else 'green'}">{r['martin_dependency']:.1f}%</td>
<td>{num_levels}</td>
<td class="{'red' if max_mult >= 2 else 'green'}">{max_mult:.2f}x</td>
<td class="red">${r['max_dd']:.0f}</td>
<td class="{'red' if risk >= 70 else 'orange' if risk >= 40 else 'green'}">{risk:.0f}</td>
<td>{badge}</td>
</tr>"""
    
    html += """</tbody></table></div>"""
    
    # Individual currency details
    html += """<div style="font-size: 12px; color: #e94560; font-weight: bold; margin-bottom: 8px;">🔍 各貨幣對馬汀深度剖析</div>"""
    
    for symbol, r in sorted_symbols:
        risk_class = 'risk-high' if r['risk_score'] >= 70 else 'risk-med' if r['risk_score'] >= 40 else 'risk-low'
        
        html += f"""
<div class="symbol-card {risk_class}">
<div class="symbol-header">
<span>{symbol}</span>
<span style="font-size: 11px;">風險分：{r['risk_score']:.0f}/100</span>
</div>
<div class="symbol-body">
<div class="stats-row">
<div class="stat"><div class="stat-label">交易數</div><div class="stat-val">{r['total']}</div></div>
<div class="stat"><div class="stat-label">勝率</div><div class="stat-val {'green' if r['win_rate'] >= 70 else 'red'}">{r['win_rate']:.1f}%</div></div>
<div class="stat"><div class="stat-label">Classic Martin</div><div class="stat-val orange">{r['classic_martin']}</div></div>
<div class="stat"><div class="stat-label">Reverse Martin</div><div class="stat-val yellow">{r['reverse_martin']}</div></div>
<div class="stat"><div class="stat-label">Cost Killed</div><div class="stat-val red">{r['cost_killed']}</div></div>
<div class="stat"><div class="stat-label">馬丁依賴</div><div class="stat-val {'red' if r['martin_dependency'] > 10 else 'green'}">{r['martin_dependency']:.1f}%</div></div>
<div class="stat"><div class="stat-label">最深DD</div><div class="stat-val red">${r['max_dd']:.0f}</div></div>
<div class="stat"><div class="stat-label">均持倉</div><div class="stat-val">{r['avg_hold_hours']:.1f}h</div></div>
</div>
"""
        
        # Level breakdown table
        if r.get('level_stats'):
            html += """<table><thead><tr><th>層級</th><th>Lot</th><th>交易數</th><th>勝率</th><th>總盈利</th><th>均盈利</th><th>均DD</th><th>均Pips</th><th>Martin</th><th>Martin%</th></tr></thead><tbody>"""
            for ls in r['level_stats']:
                wr_class = 'green' if ls['win_rate'] >= 70 else 'red'
                mp_class = 'red' if ls['martin_pct'] > 5 else 'green'
                html += f"""<tr>
<td><strong>{ls['level']}</strong></td>
<td>{ls['lot']:.2f}</td>
<td>{ls['count']}</td>
<td class="{wr_class}">{ls['win_rate']:.1f}%</td>
<td class="{'green' if ls['total_profit'] > 0 else 'red'}">${ls['total_profit']:.2f}</td>
<td>${ls['avg_profit']:.2f}</td>
<td class="red">${ls['avg_dd']:.2f}</td>
<td class="{'green' if ls['avg_pips'] > 0 else 'red'}">{ls['avg_pips']:.1f}</td>
<td>{ls['martin_count']}</td>
<td class="{mp_class}">{ls['martin_pct']:.1f}%</td>
</tr>"""
            html += """</tbody></table>"""
        
        # Lot multiplier chain
        if r.get('lot_multipliers'):
            html += """<div class="martin-detail"><div class="martin-detail-title">🔗 加倉倍數鏈</div><div style="display:flex; flex-wrap:wrap; gap:4px; align-items:center;">"""
            lots_sorted = sorted(r['lot_distribution'].keys())
            for i, lot in enumerate(lots_sorted):
                count = r['lot_distribution'][lot]
                if i > 0:
                    prev = lots_sorted[i-1]
                    mult = lot / prev if prev > 0 else 0
                    mult_class = 'red' if mult >= 2.5 else 'orange' if mult >= 2.0 else 'green'
                    html += f"""<span class="{mult_class}" style="font-size:10px;">→ ×{mult:.2f} →</span>"""
                html += f"""<span style="background:#0a1931; padding:3px 8px; border-radius:3px; color:#eee;">{lot:.2f} ({count})</span>"""
            html += """</div></div>"""
        
        # Classic Martin trade details
        if r['classic_martin'] > 0:
            html += """<div class="martin-detail"><div class="martin-detail-title">⚠️ Classic Martin 交易明細</div>"""
            html += """<table><thead><tr><th>Type</th><th>Lots</th><th>Pips</th><th>Profit</th><th>Max DD</th><th>DD Pips</th><th>Hold</th></tr></thead><tbody>"""
            for t in r['trades_by_type'].get('classic_martin', []):
                html += f"""<tr>
<td>{t['type']}</td><td>{t['lots']:.2f}</td>
<td class="red">{t['net_pips']:.1f}</td>
<td class="green">${t['net_profit']:.2f}</td>
<td class="red">${abs(t['max_loss']):.2f}</td>
<td class="red">{t['max_loss_pips']:.1f}</td>
<td>{t['hold_hours']:.0f}h</td>
</tr>"""
            html += """</tbody></table></div>"""
        
        html += """</div></div>"""
    
    # Methodology explanation
    html += """
<div style="background: #16213e; border-radius: 8px; padding: 12px; margin-top: 15px;">
<div style="font-size: 11px; color: #e94560; font-weight: bold; margin-bottom: 8px;">📐 馬汀剖析法說明</div>
<div style="font-size: 9px; color: #999; line-height: 1.6;">
<b>Classic Martin（經典馬汀）：</b>方向錯（Pips < 0）但最終獲利（Profit > 0），代表靠加倉攤平成本取勝。<br>
<b>Reverse Martin（反向馬汀）：</b>方向對（Pips > 0）但最終虧損（Profit < 0），被 Swap/Commission 吃掉利潤。<br>
<b>Cost Killed（成本殺手）：</b>Gross Profit > 0 但 Net < 0，Commission + Swap 大於毛利。<br>
<b>馬丁依賴度：</b>Classic Martin 交易所貢獻的盈利佔總盈利的比例。越高代表越依賴加倉策略。<br>
<b>加倉倍數鏈：</b>Lot 從 L1 到 L9+ 的倍數遞增關係。≥2.0x 代表激進加倉。<br>
<b>風險分數：</b>綜合馬丁依賴度、層級深度、深層勝率、加倉倍數四個維度計算（0-100）。
</div>
</div>
"""
    
    html += """<div class="footer">🎰 馬汀剖析報告 | DDE v3 Martin Strategy Anatomy | Generated by 丁蟹 🦀</div></div></body></html>"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path

def main():
    if len(sys.argv) < 2:
        print("Usage: python martin_analysis.py <csv_path> [signal_id]")
        sys.exit(1)
    
    csv_path = sys.argv[1]
    signal_id = sys.argv[2] if len(sys.argv) > 2 else 'unknown'
    
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        sys.exit(1)
    
    print(f"🎰 馬汀剖析法分析 - Signal #{signal_id}")
    print(f"📄 CSV: {csv_path}")
    
    trades = parse_csv(csv_path)
    print(f"📊 Total trades: {len(trades)}")
    
    groups = group_by_symbol(trades)
    print(f"📈 Currency pairs: {len(groups)}")
    
    all_results = {}
    for symbol, symbol_trades in groups.items():
        stats = analyze_martin_depth(symbol_trades)
        level_stats = analyze_level_distribution(symbol_trades)
        stats['level_stats'] = level_stats
        stats['risk_score'] = calculate_martin_risk_score(stats)
        all_results[symbol] = stats
    
    output_path = os.path.join(
        os.path.dirname(csv_path.replace('/mnt/c/', '')),
        f'martin_anatomy_{signal_id}.html'
    )
    # Actually output to trade_strategy_analyzer/output
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output')
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f'Martin_Anatomy_{signal_id}.html')
    
    generate_html_report(signal_id, all_results, len(trades), output_path)
    print(f"✅ Report saved to: {output_path}")

if __name__ == '__main__':
    main()
