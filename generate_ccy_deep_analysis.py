#!/usr/bin/env python3
"""
Generate per-CCY deep analysis pages (cross-signal aggregated).
Reads all CSV samples, groups by CCY, computes V3 metrics, outputs HTML.

Usage: python generate_ccy_deep_analysis.py
Output: docs/admin/ccy/{CCY}.html
"""

import csv, os, json, math
from pathlib import Path
from collections import defaultdict
from datetime import datetime

SAMPLES_DIR = Path(__file__).parent / 'samples'
OUTPUT_DIR = Path(__file__).parent / 'docs' / 'admin' / 'ccy'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def load_all_trades():
    """Load all trades from all CSV files, grouped by CCY."""
    ccy_trades = defaultdict(list)
    ccy_signals = defaultdict(set)
    
    for f in sorted(SAMPLES_DIR.glob('*.csv')):
        sid = f.stem.replace('forex-forest-signals-page-', '')
        with open(f, encoding='utf-8-sig') as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                t = row.get('Type', '').strip().lower()
                if t not in ('buy', 'sell'):
                    continue
                sym = row.get('Symbol', '').strip()
                if not sym:
                    continue
                try:
                    trade = {
                        'signal': sid,
                        'symbol': sym,
                        'direction': t,
                        'lots': float(row.get('Lots', 0)),
                        'open_price': float(row.get('Open Price', 0)),
                        'close_price': float(row.get('Close Price', 0)),
                        'net_pips': float(row.get('Net Pips', 0)),
                        'net_profit': float(row.get('Net Profit', 0)),
                        'max_profit': float(row.get('Max Profit', 0)),
                        'max_pips': float(row.get('Max Pips', 0)),
                        'max_loss': float(row.get('Max Loss', 0)),
                        'max_loss_pips': abs(float(row.get('Max Loss Pips', 0))),
                        'commission': float(row.get('Commission', 0)),
                        'swap': float(row.get('Swap', 0)),
                        'holding_hours': float(row.get('Holding Time (Hours)', '0').strip() or '0'),
                        'comment': row.get('Comment', '').strip(),
                    }
                    ccy_trades[sym].append(trade)
                    ccy_signals[sym].add(sid)
                except (ValueError, TypeError):
                    continue
    
    return ccy_trades, ccy_signals


def compute_layer_stats(trades):
    """Compute stats per (direction, layer) for a CCY's trades."""
    # Determine layers from unique lots
    all_lots = sorted(set(round(t['lots'], 4) for t in trades))
    lot_to_level = {}
    for i, lot in enumerate(all_lots):
        if i >= 8:
            lot_to_level[lot] = 'L9+'
        else:
            lot_to_level[lot] = f'L{i+1}'
    
    # Group by (direction, level)
    groups = defaultdict(list)
    for t in trades:
        lot_key = round(t['lots'], 4)
        level = lot_to_level.get(lot_key, 'L1')
        groups[(t['direction'], level)].append(t)
    
    results = {}
    for (direction, level), lt in groups.items():
        n = len(lt)
        if n == 0:
            continue
        wins = [t for t in lt if t['net_profit'] > 0]
        losses = [t for t in lt if t['net_profit'] <= 0]
        win_count = len(wins)
        loss_count = len(losses)
        wr = win_count / n * 100 if n > 0 else 0
        total_pnl = sum(t['net_profit'] for t in lt)
        avg_win = sum(t['net_profit'] for t in wins) / win_count if win_count else 0
        avg_loss = abs(sum(t['net_profit'] for t in losses) / loss_count) if loss_count else 0
        ev = (wr / 100 * avg_win) - ((1 - wr / 100) * avg_loss)
        avg_win_pips = sum(t['net_pips'] for t in wins) / win_count if win_count else 0
        avg_loss_pips = abs(sum(t['net_pips'] for t in losses) / loss_count) if loss_count else 0
        odds_dollar = avg_win / avg_loss if avg_loss > 0 else 999
        odds_pips = avg_win_pips / avg_loss_pips if avg_loss_pips > 0 else 999
        avg_hold = sum(t['holding_hours'] for t in lt) / n
        # MFE/MAE
        mfe_values = [t['max_pips'] for t in lt]
        mae_values = [t['max_loss_pips'] for t in lt]
        avg_mfe = sum(mfe_values) / len(mfe_values) if mfe_values else 0
        max_mfe = max(mfe_values) if mfe_values else 0
        avg_mae = sum(mae_values) / len(mae_values) if mae_values else 0
        max_mae = max(mae_values) if mae_values else 0
        # Signals
        signals = set(t['signal'] for t in lt)
        
        key = f"{direction}_{level}"
        results[key] = {
            'direction': direction,
            'level': level,
            'count': n,
            'win_count': win_count,
            'loss_count': loss_count,
            'wr': round(wr, 1),
            'total_pnl': round(total_pnl, 2),
            'ev': round(ev, 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'avg_win_pips': round(avg_win_pips, 1),
            'avg_loss_pips': round(avg_loss_pips, 1),
            'odds_dollar': round(odds_dollar, 2) if odds_dollar < 100 else 999,
            'odds_pips': round(odds_pips, 2) if odds_pips < 100 else 999,
            'avg_hold': round(avg_hold, 1),
            'avg_mfe': round(avg_mfe, 1),
            'max_mfe': round(max_mfe, 1),
            'avg_mae': round(avg_mae, 1),
            'max_mae': round(max_mae, 1),
            'signals': len(signals),
            'scatter_data': [
                {
                    'net_pips': t['net_pips'],
                    'mfe': t['max_pips'],
                    'mae': t['max_loss_pips'],
                    'is_win': t['net_profit'] > 0,
                }
                for t in lt[:200]  # cap for performance
            ],
        }
    
    return results, lot_to_level


def compute_rating(stats):
    """Compute rating S+/S/A/B/C/D/E."""
    wr = stats['wr']
    ev = stats['ev']
    odds = min(stats['odds_pips'], stats['odds_dollar'])
    count = stats['count']
    
    score = 0
    if wr >= 80: score += 30
    elif wr >= 70: score += 25
    elif wr >= 60: score += 18
    elif wr >= 50: score += 10
    else: score += max(0, wr / 5)
    
    if ev >= 20: score += 30
    elif ev >= 10: score += 25
    elif ev >= 5: score += 18
    elif ev >= 0: score += 8
    
    if odds >= 3: score += 25
    elif odds >= 2: score += 20
    elif odds >= 1.5: score += 15
    elif odds >= 1: score += 8
    
    if count >= 100: score += 15
    elif count >= 50: score += 12
    elif count >= 20: score += 8
    elif count >= 10: score += 4
    
    if score >= 85: return 'S+'
    if score >= 70: return 'S'
    if score >= 55: return 'A'
    if score >= 40: return 'B'
    if score >= 25: return 'C'
    if score >= 15: return 'D'
    return 'E'


def compute_tpsl(layer_stats):
    """Compute TP/SL for A-grade+ layers."""
    rating_order = {'S+': 6, 'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1, 'E': 0}
    
    # Max MAE per direction
    dir_max_mae = defaultdict(float)
    for key, s in layer_stats.items():
        dir_max_mae[s['direction']] = max(dir_max_mae[s['direction']], s['max_mae'])
    
    results = []
    for key, s in layer_stats.items():
        if s['count'] < 2:
            continue
        rating = compute_rating(s)
        if rating_order.get(rating, 0) < 4:
            continue
        tp = s['avg_mfe']
        soft_sl = s['avg_mae'] * 1.2
        hard_sl = dir_max_mae[s['direction']] * 1.3
        rr = tp / soft_sl if soft_sl > 0 else 0
        results.append({
            'rating': rating,
            'direction': s['direction'],
            'level': s['level'],
            'count': s['count'],
            'wr': s['wr'],
            'ev': s['ev'],
            'odds_dollar': s['odds_dollar'],
            'odds_pips': s['odds_pips'],
            'tp': round(tp, 1),
            'soft_sl': round(soft_sl, 1),
            'hard_sl': round(hard_sl, 1),
            'rr': round(rr, 2),
            'total_pnl': s['total_pnl'],
            'avg_hold': s['avg_hold'],
        })
    
    results.sort(key=lambda x: (-rating_order.get(x['rating'], 0), -x['ev']))
    return results


def compute_blacklist(layer_stats):
    """Compute blacklist by direction."""
    dir_data = defaultdict(list)
    for key, s in layer_stats.items():
        dir_data[s['direction']].append(s)
    
    blacklist = []
    for direction, layers in dir_data.items():
        total_pnl = sum(l['total_pnl'] for l in layers)
        total_trades = sum(l['count'] for l in layers)
        total_wins = sum(l['win_count'] for l in layers)
        wr = total_wins / total_trades * 100 if total_trades else 0
        avg_odds = sum(l['odds_pips'] for l in layers) / len(layers) if layers else 0
        avg_ev = sum(l['ev'] for l in layers) / len(layers) if layers else 0
        worst_ev = min(l['ev'] for l in layers) if layers else 0
        
        danger = 0
        if total_pnl < 0: danger += min(abs(total_pnl) / 500, 5)
        if avg_odds < 1.0: danger += 3
        if wr < 50: danger += 2
        if avg_ev < 0: danger += abs(avg_ev) / 10
        if worst_ev < -50: danger += 2
        
        if danger >= 1:
            deepest = max(layers, key=lambda x: x['count'])
            blacklist.append({
                'direction': direction,
                'total_pnl': round(total_pnl, 2),
                'wr': round(wr, 1),
                'avg_odds': round(avg_odds, 2),
                'avg_ev': round(avg_ev, 2),
                'worst_ev': round(worst_ev, 2),
                'danger': round(danger, 1),
                'level': '💀 DEADLY' if danger > 5 else '⚠️ WARNING',
            })
    
    blacklist.sort(key=lambda x: -x['danger'])
    return blacklist


def compute_recovery(layer_stats):
    """Compute recovery analysis by direction."""
    dir_data = defaultdict(list)
    for key, s in layer_stats.items():
        dir_data[s['direction']].append(s)
    
    results = []
    level_order = lambda x: (99 if x == 'L9+' else int(x[1:]))
    
    for direction, layers in dir_data.items():
        lvl_keys = [l['level'] for l in layers]
        if not lvl_keys:
            continue
        deepest = max(layers, key=lambda x: level_order(x['level']))
        worst_loss = deepest['avg_loss'] if deepest['loss_count'] > 0 else (deepest['count'] * 10)
        best_ev_layer = max(layers, key=lambda x: x['ev'])
        best_ev = best_ev_layer['ev']
        
        if best_ev > 0:
            recovery_trades = math.ceil(worst_loss / best_ev)
        else:
            recovery_trades = 999
        
        total_trades = sum(l['count'] for l in layers)
        freq_month = total_trades / 6  # assume ~6 months data
        recovery_days = round(recovery_trades / freq_month * 30, 0) if freq_month > 0 else 999
        
        if recovery_trades > 20 or best_ev <= 0:
            status = '🔴'
            status_text = f'無法恢復 ({recovery_trades}次)'
        elif recovery_trades >= 5:
            status = '🟡'
            status_text = f'需時 ({recovery_trades}次)'
        else:
            status = '🟢'
            status_text = f'安全 ({recovery_trades}次)'
        
        results.append({
            'direction': direction,
            'deepest_level': deepest['level'],
            'worst_loss': round(worst_loss, 2),
            'best_ev_level': best_ev_layer['level'],
            'best_ev': round(best_ev, 2),
            'recovery_trades': recovery_trades,
            'recovery_days': int(recovery_days),
            'status': status,
            'status_text': status_text,
        })
    
    results.sort(key=lambda x: x['recovery_trades'])
    return results


def generate_html(ccy, trades, layer_stats, tpsl_data, blacklist, recovery, num_signals):
    """Generate HTML for a single CCY deep analysis page."""
    
    total_trades = len(trades)
    total_pnl = sum(t['net_profit'] for t in trades)
    total_wins = sum(1 for t in trades if t['net_profit'] > 0)
    wr = total_wins / total_trades * 100 if total_trades else 0
    avg_hold = sum(t['holding_hours'] for t in trades) / total_trades if total_trades else 0
    
    # Direction summary
    buy_trades = [t for t in trades if t['direction'] == 'buy']
    sell_trades = [t for t in trades if t['direction'] == 'sell']
    buy_wr = sum(1 for t in buy_trades if t['net_profit'] > 0) / len(buy_trades) * 100 if buy_trades else 0
    sell_wr = sum(1 for t in sell_trades if t['net_profit'] > 0) / len(sell_trades) * 100 if sell_trades else 0
    buy_pnl = sum(t['net_profit'] for t in buy_trades)
    sell_pnl = sum(t['net_profit'] for t in sell_trades)
    
    # Serialize scatter data
    scatter_json = json.dumps({k: v['scatter_data'] for k, v in layer_stats.items() if v.get('scatter_data')})
    
    # Sort layer stats for table
    sorted_keys = sorted(layer_stats.keys(), key=lambda k: (
        0 if layer_stats[k]['direction'] == 'buy' else 1,
        99 if layer_stats[k]['level'] == 'L9+' else int(layer_stats[k]['level'][1:])
    ))
    
    html = f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>💱 {ccy} 深度分析 | TSA</title>
<style>
:root{{--font:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC',sans-serif;--bg:#0a0e17;--card:#111520;--text:#d0d0d0;--text2:#888;--primary:#FFD700;--accent:#64b5f6;--green:#4CAF50;--red:#FF5722;--yellow:#FFC107;--orange:#fd7e14;--border:#1e2433;--radius:8px}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--font);background:var(--bg);color:var(--text);padding:16px;font-size:13px}}
.topnav{{display:flex;align-items:center;gap:12px;padding:10px 16px;background:var(--card);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:16px}}
.topnav a{{color:var(--accent);text-decoration:none;font-weight:700;font-size:0.9em}}
.topnav .back{{margin-right:auto}}
h1{{font-size:1.4em;color:var(--primary);margin-bottom:4px}}
.sub{{color:var(--text2);font-size:0.85em;margin-bottom:16px}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:20px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:14px;text-align:center}}
.card .v{{font-size:1.4em;font-weight:700;color:var(--primary)}}
.card .v.pos{{color:var(--green)}}.card .v.neg{{color:var(--red)}}
.card .l{{font-size:0.72em;color:var(--text2);margin-top:2px}}
.tabs{{display:flex;gap:0;margin-bottom:0}}
.tab{{padding:10px 20px;background:var(--card);border:1px solid var(--border);color:var(--text2);cursor:pointer;border-radius:8px 8px 0 0;font-size:0.9em}}
.tab.active{{background:var(--bg);color:var(--primary);border-bottom-color:var(--bg);font-weight:700}}
.tab:hover{{color:var(--primary)}}
.panel{{background:var(--bg);border:1px solid var(--border);border-top:none;border-radius:0 0 8px 8px;padding:16px;margin-bottom:20px}}
.panel.hidden{{display:none}}
table{{width:100%;border-collapse:collapse;min-width:600px}}
th{{background:var(--card);padding:8px;text-align:left;border-bottom:2px solid var(--primary);color:var(--primary);font-size:0.8em;white-space:nowrap;cursor:pointer}}
th:hover{{background:#1a1f2e}}
td{{padding:6px 8px;border-bottom:1px solid var(--border);font-size:0.85em}}
tr:hover{{background:rgba(255,215,0,0.03)}}
.g{{color:var(--green)}}.r{{color:var(--red)}}.y{{color:var(--yellow)}}
.rating{{display:inline-block;padding:1px 8px;border-radius:4px;font-size:0.78em;font-weight:700}}
.rating-sp{{background:#FFD700;color:#000}}.rating-s{{background:var(--green);color:#fff}}.rating-a{{background:var(--accent);color:#000}}
.chart-wrap{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:16px;margin-bottom:16px}}
.chart-wrap h3{{color:var(--primary);font-size:0.95em;margin-bottom:12px}}
canvas{{width:100%;height:300px}}
.legend{{display:flex;gap:16px;margin-top:8px;font-size:0.82em;color:var(--text2)}}
.legend span::before{{content:'';display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:4px;vertical-align:middle}}
.legend .l-tp::before{{background:var(--green)}}
.legend .l-ssl::before{{background:var(--orange)}}
.legend .l-hsl::before{{background:var(--red)}}
.legend .l-green::before{{background:var(--green)}}
.legend .l-orange::before{{background:var(--orange)}}
.legend .l-red::before{{background:var(--red)}}
.bl-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}
@media(max-width:768px){{.bl-grid{{grid-template-columns:1fr}}}}
</style>
</head>
<body>

<div class="topnav">
  <a href="../ccy_ranking.html" class="back">← 返回 CCY 排名</a>
  <a href="../index.html">🏠 Dashboard</a>
</div>

<h1>💱 {ccy} 深度分析</h1>
<div class="sub">跨 Signal 聚合數據 | {num_signals} 個 Signal | {total_trades:,} 筆交易</div>

<div class="cards">
  <div class="card"><div class="v">{total_trades:,}</div><div class="l">總交易</div></div>
  <div class="card"><div class="v {'pos' if total_pnl >= 0 else 'neg'}">${total_pnl:,.0f}</div><div class="l">總盈虧</div></div>
  <div class="card"><div class="v">{wr:.1f}%</div><div class="l">勝率</div></div>
  <div class="card"><div class="v">{avg_hold:.1f}h</div><div class="l">平均持倉</div></div>
  <div class="card"><div class="v {'pos' if buy_pnl >= 0 else 'neg'}">${buy_pnl:,.0f}</div><div class="l">Buy PnL ({buy_wr:.0f}%)</div></div>
  <div class="card"><div class="v {'pos' if sell_pnl >= 0 else 'neg'}">${sell_pnl:,.0f}</div><div class="l">Sell PnL ({sell_wr:.0f}%)</div></div>
</div>

<div class="tabs">
  <div class="tab active" onclick="sw('p1')">📊 數據總表</div>
  <div class="tab" onclick="sw('p2')">📈 TP/SL 圖表</div>
  <div class="tab" onclick="sw('p3')">🏆 排行榜</div>
  <div class="tab" onclick="sw('p4')">💀 黑名單</div>
  <div class="tab" onclick="sw('p5')">💪 恢復力</div>
  <div class="tab" onclick="sw('p6')">🔬 MFE/MAE</div>
</div>

<!-- Part 1: Data Table -->
<div class="panel" id="p1">
<h3 style="color:var(--primary);margin-bottom:12px">📊 {ccy} × Direction × Layer 完整數據</h3>
<div style="overflow-x:auto">
<table id="t1">
<thead><tr>
<th>Dir</th><th>Layer</th><th>Trades</th><th>WR%</th><th>Total$</th><th>EV$</th><th>Odds$</th><th>OddsPip</th><th>AvgWin Pip</th><th>AvgLoss Pip</th><th>AvgMFE</th><th>AvgMAE</th><th>MaxMAE</th><th>AvgHold</th><th>Signals</th>
</tr></thead>
<tbody>
'''
    
    for key in sorted_keys:
        s = layer_stats[key]
        pnl_cls = 'g' if s['total_pnl'] >= 0 else 'r'
        html += f'''<tr>
<td>{s['direction'].upper()}</td>
<td>{s['level']}</td>
<td>{s['count']:,}</td>
<td>{s['wr']:.1f}%</td>
<td class="{pnl_cls}">${s['total_pnl']:,.0f}</td>
<td class="{'g' if s['ev'] >= 0 else 'r'}">${s['ev']:.2f}</td>
<td>{s['odds_dollar']:.1f}x</td>
<td>{s['odds_pips']:.1f}x</td>
<td>{s['avg_win_pips']:.1f}</td>
<td>{s['avg_loss_pips']:.1f}</td>
<td>{s['avg_mfe']:.1f}</td>
<td>{s['avg_mae']:.1f}</td>
<td class="r">{s['max_mae']:.1f}</td>
<td>{s['avg_hold']:.1f}h</td>
<td>{s['signals']}</td>
</tr>
'''
    
    html += '''</tbody></table></div>
</div>

<!-- Part 2: TP/SL Chart -->
<div class="panel hidden" id="p2">
<h3 style="color:var(--primary);margin-bottom:12px">📈 TP/SL 橫向條形圖</h3>
<div class="chart-wrap">
  <canvas id="chartTpsl"></canvas>
  <div class="legend">
    <span class="l-tp">TP (Avg MFE)</span>
    <span class="l-ssl">Soft SL (MAE×1.2)</span>
    <span class="l-hsl">Hard SL (MaxMAE×1.3)</span>
  </div>
</div>
<div style="overflow-x:auto">
<table id="tTpsl">
<thead><tr><th>Rating</th><th>Dir</th><th>Layer</th><th>Trades</th><th>WR%</th><th>EV$</th><th>TP(pip)</th><th>SoftSL</th><th>HardSL</th><th>R:R</th><th>Total$</th></tr></thead>
<tbody>
'''
    
    for t in tpsl_data:
        rt_cls = {'S+': 'rating-sp', 'S': 'rating-s', 'A': 'rating-a'}.get(t['rating'], '')
        html += f'''<tr>
<td><span class="rating {rt_cls}">{t['rating']}</span></td>
<td>{t['direction'].upper()}</td>
<td>{t['level']}</td>
<td>{t['count']}</td>
<td>{t['wr']:.1f}%</td>
<td class="{'g' if t['ev'] >= 0 else 'r'}">${t['ev']:.2f}</td>
<td class="g">{t['tp']:.1f}</td>
<td class="y">{t['soft_sl']:.1f}</td>
<td class="r">{t['hard_sl']:.1f}</td>
<td>{t['rr']:.2f}x</td>
<td class="{'g' if t['total_pnl'] >= 0 else 'r'}">${t['total_pnl']:,.0f}</td>
</tr>
'''
    
    html += '''</tbody></table></div>
</div>

<!-- Part 3: Ranking -->
<div class="panel hidden" id="p3">
<h3 style="color:var(--primary);margin-bottom:12px">🏆 A級以上排行榜</h3>
<div style="overflow-x:auto">
<table id="tRank">
<thead><tr><th>#</th><th>Rating</th><th>Dir</th><th>Layer</th><th>Trades</th><th>WR%</th><th>EV$</th><th>Odds$</th><th>OddsPip</th><th>TP</th><th>SoftSL</th><th>HardSL</th><th>Total$</th><th>AvgHold</th></tr></thead>
<tbody>
'''
    
    for i, t in enumerate(tpsl_data, 1):
        rt_cls = {'S+': 'rating-sp', 'S': 'rating-s', 'A': 'rating-a'}.get(t['rating'], '')
        html += f'''<tr>
<td>{i}</td>
<td><span class="rating {rt_cls}">{t['rating']}</span></td>
<td>{t['direction'].upper()}</td>
<td>{t['level']}</td>
<td>{t['count']}</td>
<td>{t['wr']:.1f}%</td>
<td class="g">${t['ev']:.2f}</td>
<td>{t['odds_dollar']:.1f}x</td>
<td>{t['odds_pips']:.1f}x</td>
<td class="g">{t['tp']:.1f}</td>
<td class="y">{t['soft_sl']:.1f}</td>
<td class="r">{t['hard_sl']:.1f}</td>
<td class="g">${t['total_pnl']:,.0f}</td>
<td>{t['avg_hold']:.1f}h</td>
</tr>
'''
    
    html += f'''</tbody></table></div>
</div>

<!-- Part 4: Blacklist -->
<div class="panel hidden" id="p4">
<h3 style="color:var(--primary);margin-bottom:12px">💀 黑名單</h3>
'''
    
    if blacklist:
        html += '''<div class="chart-wrap"><canvas id="chartBl"></canvas>
<div class="legend"><span class="l-orange">⚠️ WARNING</span><span class="l-red">💀 DEADLY</span></div></div>
<div style="overflow-x:auto"><table><thead><tr><th>Dir</th><th>PnL</th><th>WR%</th><th>Odds</th><th>Avg EV</th><th>Worst EV</th><th>Danger</th><th>Level</th></tr></thead><tbody>
'''
        for b in blacklist:
            cls = 'r' if b['total_pnl'] < 0 else 'g'
            html += f'''<tr><td>{b['direction'].upper()}</td><td class="{cls}">${b['total_pnl']:,.0f}</td><td>{b['wr']:.1f}%</td><td>{b['avg_odds']:.1f}x</td><td class="{'r' if b['avg_ev'] < 0 else 'g'}">${b['avg_ev']:.2f}</td><td class="r">${b['worst_ev']:.2f}</td><td><strong>{b['danger']:.1f}</strong></td><td>{b['level']}</td></tr>
'''
        html += '</tbody></table></div>'
    else:
        html += '<p style="color:var(--green)">✅ 無黑名單項目</p>'
    
    html += '''</div>

<!-- Part 5: Recovery -->
<div class="panel hidden" id="p5">
<h3 style="color:var(--primary);margin-bottom:12px">💪 恢復力分析</h3>
'''
    
    if recovery:
        html += '<div class="chart-wrap"><canvas id="chartRv"></canvas><div class="legend"><span class="l-green">🟢 &lt;5次</span><span class="l-orange">🟡 5-20次</span><span class="l-red">🔴 &gt;20次</span></div></div>'
        html += '<div style="overflow-x:auto"><table><thead><tr><th>Dir</th><th>Deepest</th><th>Worst Loss</th><th>Best EV Layer</th><th>Best EV</th><th>Recovery</th><th>Days</th><th>Status</th></tr></thead><tbody>'
        for r in recovery:
            html += f'''<tr><td>{r['direction'].upper()}</td><td>{r['deepest_level']}</td><td class="r">${r['worst_loss']:,.0f}</td><td>{r['best_ev_level']}</td><td class="g">${r['best_ev']:.2f}</td><td>{r['recovery_trades']}</td><td>{r['recovery_days']}</td><td>{r['status']} {r['status_text']}</td></tr>
'''
        html += '</tbody></table></div>'
    else:
        html += '<p style="color:var(--text2)">無數據</p>'
    
    html += '''</div>

<!-- Part 6: MFE/MAE Scatter -->
<div class="panel hidden" id="p6">
<h3 style="color:var(--primary);margin-bottom:12px">🔬 MFE/MAE 散點分析</h3>
<div id="scatterGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px"></div>
</div>

<script>
const scatterData = ''' + scatter_json + ''';

function sw(id){
  document.querySelectorAll('.panel').forEach(p=>p.classList.add('hidden'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(id).classList.remove('hidden');
  event.target.classList.add('active');
  if(id==='p2') drawTpsl();
  if(id==='p4') drawBl();
  if(id==='p5') drawRv();
  if(id==='p6') drawScatter();
}

// Sort tables
document.querySelectorAll('table[id]').forEach(tbl=>{
  const tbody=tbl.querySelector('tbody');
  const ths=tbl.querySelectorAll('thead th');
  ths.forEach((th,col)=>{
    th.addEventListener('click',()=>{
      const rows=Array.from(tbody.querySelectorAll('tr'));
      const asc=th.dataset.sort!=='asc';
      ths.forEach(t=>{t.classList.remove('asc','desc');delete t.dataset.sort});
      th.dataset.sort=asc?'asc':'desc';
      rows.sort((a,b)=>{
        let va=a.cells[col]?.textContent?.trim()||'';
        let vb=b.cells[col]?.textContent?.trim()||'';
        let na=parseFloat(va.replace(/[^0-9.-]/g,''));
        let nb=parseFloat(vb.replace(/[^0-9.-]/g,''));
        if(!isNaN(na)&&!isNaN(nb)) return asc?na-nb:nb-na;
        return asc?va.localeCompare(vb):vb.localeCompare(va);
      });
      rows.forEach(r=>tbody.appendChild(r));
    });
  });
});

function drawTpsl(){
  const c=document.getElementById('chartTpsl');
  const data=''' + json.dumps(tpsl_data[:30]) + ''';
  if(!data.length)return;
  const ctx=c.getContext('2d');
  const dpr=window.devicePixelRatio||1;
  c.width=c.offsetWidth*dpr;c.height=Math.max(300,data.length*28)*dpr;
  c.style.height=Math.max(300,data.length*28)+'px';
  ctx.scale(dpr,dpr);
  const w=c.offsetWidth,h=parseInt(c.style.height);
  const pad={t:20,r:20,b:30,l:100};
  const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
  ctx.fillStyle='#111520';ctx.fillRect(0,0,w,h);
  const maxPip=Math.max(...data.map(d=>d.tp),...data.map(d=>d.hard_sl),1);
  const barH=Math.max(4,ph/data.length*0.3);
  const rowH=ph/data.length;
  data.forEach((d,i)=>{
    const y=pad.t+i*rowH;
    const label=d.direction.toUpperCase()+' '+d.level;
    ctx.fillStyle='#888';ctx.font='10px sans-serif';ctx.textAlign='right';
    ctx.fillText(label,pad.l-6,y+rowH/2+3);
    // TP bar (green, right)
    const tw=d.tp/maxPip*pw;
    ctx.fillStyle='#4CAF50';ctx.fillRect(pad.l,y+rowH/2-barH*1.5,Math.max(1,tw),barH);
    // Soft SL (orange, left)
    const sw=d.soft_sl/maxPip*pw;
    ctx.fillStyle='#FFC107';ctx.fillRect(pad.l-sw,y+rowH/2-barH*0.5,Math.max(1,sw),barH);
    // Hard SL (red, left, thinner)
    const hw=d.hard_sl/maxPip*pw;
    ctx.fillStyle='#FF5722';ctx.fillRect(pad.l-hw,y+rowH/2+barH*0.5,Math.max(1,hw),barH);
  });
  // Zero line
  ctx.strokeStyle='#FFD700';ctx.lineWidth=1;
  ctx.beginPath();ctx.moveTo(pad.l,pad.t);ctx.lineTo(pad.l,h-pad.b);ctx.stroke();
}

function drawBl(){
  const data=''' + json.dumps(blacklist) + ''';
  if(!data.length)return;
  const c=document.getElementById('chartBl');
  const ctx=c.getContext('2d');
  const dpr=window.devicePixelRatio||1;
  c.width=c.offsetWidth*dpr;c.height=Math.max(200,data.length*30)*dpr;
  c.style.height=Math.max(200,data.length*30)+'px';
  ctx.scale(dpr,dpr);
  const w=c.offsetWidth,h=parseInt(c.style.height);
  const pad={t:20,r:20,b:30,l:100};
  const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
  ctx.fillStyle='#111520';ctx.fillRect(0,0,w,h);
  const maxAbs=Math.max(...data.map(d=>Math.abs(d.total_pnl)),100)*1.2;
  const rowH=ph/data.length;
  const barH=rowH*0.5;
  data.forEach((d,i)=>{
    const y=pad.t+i*rowH;
    ctx.fillStyle='#888';ctx.font='10px sans-serif';ctx.textAlign='right';
    ctx.fillText(d.direction.toUpperCase(),pad.l-6,y+rowH/2+3);
    const bw=Math.abs(d.total_pnl)/maxAbs*pw;
    const x=d.total_pnl>=0?pad.l:pad.l-bw;
    ctx.fillStyle=d.danger>5?'#FF5722':'#FFC107';
    ctx.fillRect(x,y+rowH/2-barH/2,Math.max(1,bw),barH);
    ctx.fillStyle='#ddd';ctx.font='9px sans-serif';ctx.textAlign=d.total_pnl>=0?'left':'right';
    ctx.fillText('$'+d.total_pnl.toLocaleString()+'|'+d.level,x+(d.total_pnl>=0?4:-4),y+rowH/2+3);
  });
  // Zero line
  ctx.strokeStyle='#FFD700';ctx.lineWidth=1;
  ctx.beginPath();ctx.moveTo(pad.l,pad.t);ctx.lineTo(pad.l,h-pad.b);ctx.stroke();
}

function drawRv(){
  const data=''' + json.dumps(recovery) + ''';
  if(!data.length)return;
  const c=document.getElementById('chartRv');
  const ctx=c.getContext('2d');
  const dpr=window.devicePixelRatio||1;
  c.width=c.offsetWidth*dpr;c.height=Math.max(200,data.length*30)*dpr;
  c.style.height=Math.max(200,data.length*30)+'px';
  ctx.scale(dpr,dpr);
  const w=c.offsetWidth,h=parseInt(c.style.height);
  const pad={t:20,r:20,b:30,l:120};
  const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
  ctx.fillStyle='#111520';ctx.fillRect(0,0,w,h);
  const cap=40;
  const rowH=ph/data.length;
  const barH=rowH*0.5;
  data.forEach((d,i)=>{
    const y=pad.t+i*rowH;
    const label=d.direction.toUpperCase()+' (depth '+d.deepest_level+')';
    ctx.fillStyle='#888';ctx.font='9px sans-serif';ctx.textAlign='right';
    ctx.fillText(label,pad.l-6,y+rowH/2+3);
    const val=Math.min(d.recovery_trades,cap);
    const bw=val/cap*pw;
    ctx.fillStyle=d.recovery_trades>20?'#FF5722':d.recovery_trades>=5?'#FFC107':'#4CAF50';
    ctx.fillRect(pad.l,y+rowH/2-barH/2,Math.max(1,bw),barH);
    ctx.fillStyle='#ddd';ctx.font='9px sans-serif';ctx.textAlign='left';
    ctx.fillText(d.recovery_trades+'次 ('+d.recovery_days+'天)',pad.l+bw+4,y+rowH/2+3);
  });
  // Reference lines
  [5,20].forEach(v=>{
    const x=pad.l+v/cap*pw;
    ctx.strokeStyle=v===5?'#FFC107':'#FF5722';ctx.lineWidth=0.5;ctx.setLineDash([4,4]);
    ctx.beginPath();ctx.moveTo(x,pad.t);ctx.lineTo(x,h-pad.b);ctx.stroke();
    ctx.setLineDash([]);
  });
}

function drawScatter(){
  const grid=document.getElementById('scatterGrid');
  grid.innerHTML='';
  for(const[key,data]of Object.entries(scatterData)){
    if(!data.length)continue;
    const card=document.createElement('div');
    card.style.cssText='background:var(--card);border:1px solid var(--border);border-radius:8px;padding:8px';
    const parts=key.split('_');
    card.innerHTML='<div style="font-size:0.8em;color:var(--primary);margin-bottom:4px">'+parts[0].toUpperCase()+' '+parts[1]+'</div><canvas id="sc_'+key+'" style="width:100%;height:160px"></canvas>';
    grid.appendChild(card);
    setTimeout(()=>{
      const cv=document.getElementById('sc_'+key);
      if(!cv)return;
      const ctx=cv.getContext('2d');
      const dpr=window.devicePixelRatio||1;
      cv.width=cv.offsetWidth*dpr;cv.height=160*dpr;
      ctx.scale(dpr,dpr);
      const w=cv.offsetWidth,h=160;
      const pad={t:12,r:6,b:20,l:30};
      const pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
      ctx.fillStyle='#111520';ctx.fillRect(0,0,w,h);
      const mx=Math.max(...data.map(d=>Math.abs(d.mfe)),...data.map(d=>Math.abs(d.mae)),1);
      // Axes
      ctx.strokeStyle='#333';ctx.lineWidth=0.5;
      ctx.beginPath();ctx.moveTo(pad.l,pad.t);ctx.lineTo(pad.l,pad.t+ph);ctx.lineTo(pad.l+pw,pad.t+ph);ctx.stroke();
      // Points
      data.forEach(d=>{
        const x=pad.l+(d.mae/mx)*pw;
        const y=pad.t+ph*(1-d.mfe/mx);
        ctx.beginPath();ctx.arc(Math.max(pad.l,Math.min(pad.l+pw,x)),Math.max(pad.t,Math.min(pad.t+ph,y)),2,0,Math.PI*2);
        ctx.fillStyle=d.is_win?'#4CAF50':'#FF5722';ctx.fill();
      });
    },50);
  }
}
</script>
</body></html>'''
    
    return html


def main():
    print("🔬 Loading all trades...")
    ccy_trades, ccy_signals = load_all_trades()
    print(f"  Loaded {sum(len(v) for v in ccy_trades.values()):,} trades across {len(ccy_trades)} CCY")
    
    print("📊 Generating CCY deep analysis pages...")
    
    for ccy, trades in sorted(ccy_trades.items()):
        if len(trades) < 20:
            print(f"  ⏭️ {ccy}: only {len(trades)} trades, skipping")
            continue
        
        num_signals = len(ccy_signals[ccy])
        layer_stats, lot_mapping = compute_layer_stats(trades)
        tpsl_data = compute_tpsl(layer_stats)
        blacklist = compute_blacklist(layer_stats)
        recovery = compute_recovery(layer_stats)
        
        html = generate_html(ccy, trades, layer_stats, tpsl_data, blacklist, recovery, num_signals)
        
        out_path = OUTPUT_DIR / f"{ccy}.html"
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        print(f"  ✅ {ccy}: {len(trades):,} trades, {num_signals} signals, {len(layer_stats)} layers → {out_path.name} ({len(html):,} bytes)")
    
    print(f"\n✅ Done! Generated {len(list(OUTPUT_DIR.glob('*.html')))} CCY analysis pages in {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
