#!/usr/bin/env python3
"""
Generate individual HTML reports + summary from batch_analysis_results.json
"""
import json
import os
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / 'output'
RESULTS_FILE = OUTPUT_DIR / 'batch_analysis_results.json'

def load_results():
    with open(RESULTS_FILE) as f:
        return json.load(f)

def generate_signal_report(item):
    """Generate individual HTML report for one signal."""
    sid = item['signal_id']
    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🦀 Signal #{sid} 分析報告</title>
<style>
  :root {{
    --bg: #0a0e17;
    --card: #111827;
    --border: #1e2d3d;
    --text: #e2e8f0;
    --dim: #8899aa;
    --accent: #10b981;
    --warn: #f59e0b;
    --danger: #ef4444;
    --good: #22c55e;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; padding: 12px; }}
  .header {{ text-align: center; padding: 20px 0; border-bottom: 1px solid var(--border); margin-bottom: 16px; }}
  .header h1 {{ font-size: 1.4em; color: var(--accent); }}
  .header .sub {{ color: var(--dim); font-size: 0.85em; margin-top: 4px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 10px; margin-bottom: 16px; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px; }}
  .card .label {{ color: var(--dim); font-size: 0.75em; text-transform: uppercase; letter-spacing: 0.5px; }}
  .card .value {{ font-size: 1.3em; font-weight: 700; margin-top: 4px; }}
  .card .value.good {{ color: var(--good); }}
  .card .value.warn {{ color: var(--warn); }}
  .card .value.danger {{ color: var(--danger); }}
  .section {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 12px; }}
  .section h2 {{ font-size: 1em; color: var(--accent); margin-bottom: 10px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
  .row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid rgba(255,255,255,0.05); }}
  .row .key {{ color: var(--dim); }}
  .row .val {{ font-weight: 600; }}
  .bar {{ height: 6px; border-radius: 3px; background: var(--border); margin-top: 4px; }}
  .bar .fill {{ height: 100%; border-radius: 3px; }}
  .badge {{ display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75em; font-weight: 600; }}
  .badge.sma {{ background: #1e3a5f; color: #60a5fa; }}
  .badge.mkd {{ background: #1e3f30; color: #34d399; }}
  footer {{ text-align: center; padding: 20px 0; color: var(--dim); font-size: 0.75em; border-top: 1px solid var(--border); margin-top: 16px; }}
</style>
</head>
<body>
<div class="header">
  <h1>🦀 Signal #{sid} 分析報告</h1>
  <div class="sub">{item.get('timeframe', 'N/A')} · {item.get('trade_type', 'N/A')} · {item.get('csv_file', '')}</div>
  <div class="sub">{item.get('date_from', 'N/A')} → {item.get('date_to', 'N/A')}</div>
</div>
"""
    # Key metrics
    wr = item.get('win_rate', 0)
    pf = item.get('profit_factor', 0)
    tpl = item.get('total_profit', 0)
    wr_class = 'good' if wr >= 90 else ('warn' if wr >= 70 else 'danger')
    pf_str = '∞' if (pf == float('inf') or pf > 99999) else f'{pf:.2f}'
    tpl_class = 'good' if tpl > 0 else 'danger'

    html += f"""
<div class="grid">
  <div class="card">
    <div class="label">Win Rate</div>
    <div class="value {wr_class}">{wr:.1f}%</div>
    <div class="bar"><div class="fill" style="width:{min(wr,100)}%;background:{'var(--good)' if wr>=90 else ('var(--warn)' if wr>=70 else 'var(--danger)')}"></div></div>
  </div>
  <div class="card">
    <div class="label">Profit Factor</div>
    <div class="value {'good' if pf >= 2 else ('warn' if pf >= 1.5 else 'danger')}">{pf_str}</div>
  </div>
  <div class="card">
    <div class="label">Total P/L</div>
    <div class="value {tpl_class}">${tpl:,.2f}</div>
  </div>
  <div class="card">
    <div class="label">Cycles</div>
    <div class="value">{item.get('total_cycles', 0):,}</div>
  </div>
  <div class="card">
    <div class="label">Max DD</div>
    <div class="value danger">${item.get('max_dd', 0):,.2f}</div>
  </div>
  <div class="card">
    <div class="label">Avg Layers</div>
    <div class="value {'good' if item.get('avg_layers',0) <= 2 else 'warn'}">{item.get('avg_layers', 0):.1f}</div>
  </div>
</div>
"""
    # Detailed stats
    html += f"""
<div class="section">
  <h2>📊 詳細統計</h2>
  <div class="row"><span class="key">Total Trades</span><span class="val">{item.get('total_trades', 0):,}</span></div>
  <div class="row"><span class="key">Avg Win</span><span class="val good">${item.get('avg_win', 0):,.2f}</span></div>
  <div class="row"><span class="key">Avg Loss</span><span class="val danger">${item.get('avg_loss', 0):,.2f}</span></div>
  <div class="row"><span class="key">Win/Loss Ratio</span><span class="val">{item.get('win_loss_ratio', 0):.2f}</span></div>
  <div class="row"><span class="key">Avg Hold Time</span><span class="val">{item.get('avg_hold_hours', 0):.0f}h</span></div>
  <div class="row"><span class="key">Max Consecutive Losses</span><span class="val">{item.get('max_consec_loss', 0)}</span></div>
  <div class="row"><span class="key">L1 Only %</span><span class="val">{item.get('l1_only_pct', 0):.1f}%</span></div>
  <div class="row"><span class="key">L4+ Count</span><span class="val">{item.get('l4_plus_count', 0)}</span></div>
  <div class="row"><span class="key">L4 Recovery Rate</span><span class="val">{item.get('l4_recovery_rate', 0):.1f}%</span></div>
</div>
"""
    # Advanced metrics
    sharpe = item.get('sharpe', 0) or 0
    sortino = item.get('sortino', 0) or 0
    html += f"""
<div class="section">
  <h2>📈 進階指標</h2>
  <div class="row"><span class="key">Sharpe Ratio</span><span class="val {'good' if sharpe >= 1 else 'warn'}">{sharpe:.2f}</span></div>
  <div class="row"><span class="key">Sortino Ratio</span><span class="val {'good' if sortino >= 1 else 'warn'}">{sortino:.2f}</span></div>
  <div class="row"><span class="key">Exposure %</span><span class="val">{item.get('exposure_pct', 0):.1f}%</span></div>
  <div class="row"><span class="key">Total Swap</span><span class="val">${item.get('total_swap', 0):,.2f}</span></div>
  <div class="row"><span class="key">Total Commission</span><span class="val">${item.get('total_commission', 0):,.2f}</span></div>
  <div class="row"><span class="key">Entry Score</span><span class="val">{item.get('avg_entry_score', 0):.1f}</span></div>
  <div class="row"><span class="key">Strategy Score</span><span class="val">{item.get('avg_strategy_score', 0):.1f}</span></div>
  <div class="row"><span class="key">Composite Score</span><span class="val">{item.get('composite_score', 0):.1f}</span></div>
</div>
"""
    # Symbols & Layer Distribution
    symbols = item.get('symbols', [])
    if isinstance(symbols, list):
        sym_str = ', '.join(symbols[:20])
    else:
        sym_str = str(symbols)
    layer_dist = item.get('layer_dist', {})
    
    html += f"""
<div class="section">
  <h2>💱 交易品種</h2>
  <div class="row"><span class="key">Symbols</span><span class="val" style="font-size:0.85em">{sym_str}</span></div>
</div>
"""
    if layer_dist:
        html += """<div class="section"><h2>📊 Layer 分佈</h2>"""
        for layer, count in sorted(layer_dist.items()):
            total = item.get('total_cycles', 1) or 1
            pct = count / total * 100 if total else 0
            html += f"""<div class="row"><span class="key">Layer {layer}</span><span class="val">{count} ({pct:.1f}%)</span></div>"""
        html += "</div>"

    html += f"""
<footer>
  🦀 丁蟹 Trade Strategy Analyzer · LITE Mode · {datetime.now().strftime('%Y-%m-%d %H:%M')}
</footer>
</body></html>"""
    
    report_path = OUTPUT_DIR / f'report_signal_{sid}.html'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return str(report_path)


def generate_summary_report(results):
    """Generate comprehensive summary comparing all 58 signals."""
    # Sort by composite score (descending)
    sorted_results = sorted(results, key=lambda x: x.get('composite_score', 0) or 0, reverse=True)
    
    # Compute aggregate stats
    total_cycles = sum(r.get('total_cycles', 0) for r in results)
    total_pl = sum(r.get('total_profit', 0) for r in results)
    avg_wr = sum(r.get('win_rate', 0) for r in results) / len(results) if results else 0
    profitable = sum(1 for r in results if r.get('total_profit', 0) > 0)
    high_wr = sum(1 for r in results if r.get('win_rate', 0) >= 95)
    
    # Top/Bottom performers
    by_pl = sorted(results, key=lambda x: x.get('total_profit', 0), reverse=True)
    by_wr = sorted(results, key=lambda x: x.get('win_rate', 0), reverse=True)
    by_pf = sorted(results, key=lambda x: x.get('profit_factor', 0) if x.get('profit_factor', 0) != float('inf') else 999999, reverse=True)
    by_dd = sorted(results, key=lambda x: x.get('max_dd', 0))  # least DD first
    
    # Strategy breakdown
    sma_signals = [r for r in results if r.get('trade_type', '').upper() == 'SMA' or 'SMA' in str(r.get('csv_file', '')).upper()]
    mkd_signals = [r for r in results if r.get('trade_type', '').upper() == 'MKD' or 'MKD' in str(r.get('csv_file', '')).upper()]
    
    def avg_stat(signals, key):
        vals = [s.get(key, 0) or 0 for s in signals]
        return sum(vals) / len(vals) if vals else 0
    
    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🦀 58 Signals 總結報告</title>
<style>
  :root {{
    --bg: #0a0e17;
    --card: #111827;
    --card2: #1a2332;
    --border: #1e2d3d;
    --text: #e2e8f0;
    --dim: #8899aa;
    --accent: #10b981;
    --accent2: #06b6d4;
    --warn: #f59e0b;
    --danger: #ef4444;
    --good: #22c55e;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; padding: 12px; max-width: 100%; }}
  .header {{ text-align: center; padding: 20px 0; border-bottom: 1px solid var(--border); margin-bottom: 16px; }}
  .header h1 {{ font-size: 1.6em; color: var(--accent); }}
  .header .sub {{ color: var(--dim); font-size: 0.85em; margin-top: 4px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 10px; margin-bottom: 16px; }}
  .card {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 14px; text-align: center; }}
  .card .label {{ color: var(--dim); font-size: 0.7em; text-transform: uppercase; letter-spacing: 0.5px; }}
  .card .value {{ font-size: 1.4em; font-weight: 700; margin-top: 4px; }}
  .card .value.good {{ color: var(--good); }}
  .card .value.warn {{ color: var(--warn); }}
  .card .value.danger {{ color: var(--danger); }}
  .section {{ background: var(--card); border: 1px solid var(--border); border-radius: 8px; padding: 16px; margin-bottom: 12px; }}
  .section h2 {{ font-size: 1em; color: var(--accent); margin-bottom: 10px; border-bottom: 1px solid var(--border); padding-bottom: 6px; }}
  .section h3 {{ font-size: 0.9em; color: var(--accent2); margin: 10px 0 6px; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.8em; }}
  th {{ text-align: left; color: var(--dim); padding: 6px 8px; border-bottom: 1px solid var(--border); font-size: 0.85em; position: sticky; top: 0; background: var(--card); }}
  td {{ padding: 5px 8px; border-bottom: 1px solid rgba(255,255,255,0.03); }}
  tr:hover {{ background: rgba(255,255,255,0.02); }}
  .rank {{ color: var(--accent); font-weight: 700; }}
  .bar {{ height: 4px; border-radius: 2px; background: var(--border); margin-top: 2px; }}
  .bar .fill {{ height: 100%; border-radius: 2px; }}
  .badge {{ display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 0.7em; font-weight: 600; }}
  .badge.sma {{ background: #1e3a5f; color: #60a5fa; }}
  .badge.mkd {{ background: #1e3f30; color: #34d399; }}
  .badge.other {{ background: #3d2e1e; color: #f59e0b; }}
  .badge.top3 {{ background: #3d2e1e; color: #fbbf24; }}
  .badge.top10 {{ background: #1e3a5f; color: #60a5fa; }}
  footer {{ text-align: center; padding: 20px 0; color: var(--dim); font-size: 0.75em; border-top: 1px solid var(--border); margin-top: 16px; }}
  @media (max-width: 600px) {{ .grid {{ grid-template-columns: repeat(2, 1fr); }} table {{ font-size: 0.7em; }} th, td {{ padding: 3px 4px; }} }}
</style>
</head>
<body>
<div class="header">
  <h1>🦀 AlgoForest 58 Signals 總結報告</h1>
  <div class="sub">LITE Mode Analysis · {datetime.now().strftime('%Y-%m-%d %H:%M HKT')}</div>
  <div class="sub">Generated by 丁蟹 Trade Strategy Analyzer</div>
</div>
"""
    # === Overview Cards ===
    html += f"""
<div class="grid">
  <div class="card">
    <div class="label">Total Signals</div>
    <div class="value">{len(results)}</div>
  </div>
  <div class="card">
    <div class="label">Total Cycles</div>
    <div class="value">{total_cycles:,}</div>
  </div>
  <div class="card">
    <div class="label">Total P/L</div>
    <div class="value good">${total_pl:,.0f}</div>
  </div>
  <div class="card">
    <div class="label">Avg Win Rate</div>
    <div class="value {'good' if avg_wr >= 90 else 'warn'}">{avg_wr:.1f}%</div>
  </div>
  <div class="card">
    <div class="label">Profitable</div>
    <div class="value good">{profitable}/{len(results)}</div>
  </div>
  <div class="card">
    <div class="label">WR ≥ 95%</div>
    <div class="value good">{high_wr}</div>
  </div>
</div>
"""
    # === Strategy Comparison ===
    html += """
<div class="section">
  <h2>⚔️ SMA vs MKD 策略對比</h2>
  <table>
    <tr><th>Metric</th><th>SMA</th><th>MKD</th><th>All</th></tr>
"""
    for key, label in [('win_rate', 'Avg Win Rate'), ('total_profit', 'Total P/L'), ('profit_factor', 'Avg PF'), ('avg_layers', 'Avg Layers'), ('max_dd', 'Avg Max DD'), ('composite_score', 'Avg Composite')]:
        sma_v = avg_stat(sma_signals, key)
        mkd_v = avg_stat(mkd_signals, key)
        all_v = avg_stat(results, key)
        fmt = '.1f' if key in ('win_rate', 'avg_layers', 'composite_score') else '.2f'
        prefix = '$' if key in ('total_profit', 'max_dd') else ''
        pct = '%' if key == 'win_rate' else ''
        html += f"<tr><td>{label}</td><td>{prefix}{sma_v:{fmt}}{pct}</td><td>{prefix}{mkd_v:{fmt}}{pct}</td><td>{prefix}{all_v:{fmt}}{pct}</td></tr>\n"
    html += f"<tr><td>Count</td><td>{len(sma_signals)}</td><td>{len(mkd_signals)}</td><td>{len(results)}</td></tr>\n"
    html += "</table></div>\n"

    # === Top 10 by P/L ===
    html += """<div class="section"><h2>🏆 Top 10 — 總盈利 (P/L)</h2><table>
    <tr><th>#</th><th>Signal</th><th>Type</th><th>WR%</th><th>PF</th><th>P/L</th><th>Cycles</th><th>Avg Layers</th><th>Max DD</th><th>Composite</th></tr>\n"""
    for i, r in enumerate(by_pl[:10]):
        sid = r['signal_id']
        pf_str = '∞' if (r.get('profit_factor', 0) == float('inf') or r.get('profit_factor', 0) > 99999) else f"{r.get('profit_factor', 0):.2f}"
        tt = r.get('trade_type', '')
        badge = 'sma' if 'SMA' in tt.upper() else ('mkd' if 'MKD' in tt.upper() else 'other')
        wr = r.get('win_rate', 0)
        html += f"<tr><td class='rank'>{i+1}</td><td><strong>#{sid}</strong></td><td><span class='badge {badge}'>{tt}</span></td><td class='{'good' if wr>=95 else ''}'>{wr:.1f}%</td><td>{pf_str}</td><td class='good'>${r.get('total_profit',0):,.0f}</td><td>{r.get('total_cycles',0):,}</td><td>{r.get('avg_layers',0):.1f}</td><td class='danger'>${r.get('max_dd',0):,.0f}</td><td>{r.get('composite_score',0):.1f}</td></tr>\n"
    html += "</table></div>\n"

    # === Top 10 by Win Rate ===
    html += """<div class="section"><h2>🎯 Top 10 — 勝率 (Win Rate)</h2><table>
    <tr><th>#</th><th>Signal</th><th>Type</th><th>WR%</th><th>PF</th><th>P/L</th><th>Cycles</th><th>Avg Layers</th><th>Max DD</th></tr>\n"""
    for i, r in enumerate(by_wr[:10]):
        sid = r['signal_id']
        pf_str = '∞' if (r.get('profit_factor', 0) == float('inf') or r.get('profit_factor', 0) > 99999) else f"{r.get('profit_factor', 0):.2f}"
        tt = r.get('trade_type', '')
        badge = 'sma' if 'SMA' in tt.upper() else ('mkd' if 'MKD' in tt.upper() else 'other')
        html += f"<tr><td class='rank'>{i+1}</td><td><strong>#{sid}</strong></td><td><span class='badge {badge}'>{tt}</span></td><td class='good'>{r.get('win_rate',0):.1f}%</td><td>{pf_str}</td><td class='good'>${r.get('total_profit',0):,.0f}</td><td>{r.get('total_cycles',0):,}</td><td>{r.get('avg_layers',0):.1f}</td><td class='danger'>${r.get('max_dd',0):,.0f}</td></tr>\n"
    html += "</table></div>\n"

    # === Top 10 by Lowest Drawdown ===
    html += """<div class="section"><h2>🛡️ Top 10 — 最低回撤 (Lowest Max DD)</h2><table>
    <tr><th>#</th><th>Signal</th><th>Type</th><th>WR%</th><th>PF</th><th>P/L</th><th>Cycles</th><th>Max DD</th><th>DD/P/L Ratio</th></tr>\n"""
    for i, r in enumerate(by_dd[:10]):
        sid = r['signal_id']
        pf_str = '∞' if (r.get('profit_factor', 0) == float('inf') or r.get('profit_factor', 0) > 99999) else f"{r.get('profit_factor', 0):.2f}"
        tt = r.get('trade_type', '')
        badge = 'sma' if 'SMA' in tt.upper() else ('mkd' if 'MKD' in tt.upper() else 'other')
        dd = r.get('max_dd', 0)
        pl = r.get('total_profit', 0) or 1
        dd_pl = abs(dd) / pl if pl else 0
        html += f"<tr><td class='rank'>{i+1}</td><td><strong>#{sid}</strong></td><td><span class='badge {badge}'>{tt}</span></td><td>{r.get('win_rate',0):.1f}%</td><td>{pf_str}</td><td class='good'>${r.get('total_profit',0):,.0f}</td><td>{r.get('total_cycles',0):,}</td><td>${dd:,.0f}</td><td>{dd_pl:.2f}</td></tr>\n"
    html += "</table></div>\n"

    # === Bottom 5 (worst performers) ===
    html += """<div class="section"><h2>⚠️ Bottom 5 — 需要關注</h2><table>
    <tr><th>#</th><th>Signal</th><th>Type</th><th>WR%</th><th>PF</th><th>P/L</th><th>Cycles</th><th>Max DD</th><th>L4+ %</th></tr>\n"""
    for i, r in enumerate(by_pl[-5:]):
        sid = r['signal_id']
        pf_str = '∞' if (r.get('profit_factor', 0) == float('inf') or r.get('profit_factor', 0) > 99999) else f"{r.get('profit_factor', 0):.2f}"
        tt = r.get('trade_type', '')
        badge = 'sma' if 'SMA' in tt.upper() else ('mkd' if 'MKD' in tt.upper() else 'other')
        wr = r.get('win_rate', 0)
        l4_pct = (r.get('l4_plus_count', 0) / max(r.get('total_cycles', 1), 1)) * 100
        html += f"<tr><td>{len(by_pl)-4+i}</td><td><strong>#{sid}</strong></td><td><span class='badge {badge}'>{tt}</span></td><td class='{'danger' if wr<70 else 'warn'}'>{wr:.1f}%</td><td>{pf_str}</td><td class='{'danger' if r.get('total_profit',0)<0 else ''}'>${r.get('total_profit',0):,.0f}</td><td>{r.get('total_cycles',0):,}</td><td>${r.get('max_dd',0):,.0f}</td><td>{l4_pct:.1f}%</td></tr>\n"
    html += "</table></div>\n"

    # === Complete Rankings Table ===
    html += """<div class="section"><h2>📊 完整排名 — Composite Score</h2>
    <div style="overflow-x:auto;"><table>
    <tr><th>Rank</th><th>Signal</th><th>Type</th><th>TF</th><th>WR%</th><th>PF</th><th>P/L</th><th>Cycles</th><th>Layers</th><th>Max DD</th><th>Hold(h)</th><th>Composite</th><th>Report</th></tr>\n"""
    for i, r in enumerate(sorted_results):
        sid = r['signal_id']
        pf = r.get('profit_factor', 0)
        pf_str = '∞' if (pf == float('inf') or pf > 99999) else f"{pf:.2f}"
        tt = r.get('trade_type', '')
        badge = 'sma' if 'SMA' in tt.upper() else ('mkd' if 'MKD' in tt.upper() else 'other')
        wr = r.get('win_rate', 0)
        rank_badge = 'top3' if i < 3 else ('top10' if i < 10 else '')
        html += f"<tr><td><span class='badge {rank_badge}'>{i+1}</span></td><td><strong>#{sid}</strong></td><td><span class='badge {badge}'>{tt}</span></td><td>{r.get('timeframe','')}</td><td class='{'good' if wr>=95 else ('warn' if wr>=80 else 'danger')}'>{wr:.1f}%</td><td>{pf_str}</td><td class='{'good' if r.get('total_profit',0)>0 else 'danger'}'>${r.get('total_profit',0):,.0f}</td><td>{r.get('total_cycles',0):,}</td><td>{r.get('avg_layers',0):.1f}</td><td>${r.get('max_dd',0):,.0f}</td><td>{r.get('avg_hold_hours',0):.0f}</td><td>{r.get('composite_score',0):.1f}</td><td><a href='report_signal_{sid}.html' style='color:var(--accent2)'>🔗</a></td></tr>\n"
    html += "</table></div></div>\n"

    # === Risk Analysis ===
    html += """<div class="section"><h2>🔬 風險分析</h2><h3>高 L4+ 比例（深層馬丁）</h3><table>
    <tr><th>Signal</th><th>L4+ Count</th><th>L4+ %</th><th>L4 Recovery Rate</th><th>Max DD</th><th>WR%</th></tr>\n"""
    by_l4 = sorted(results, key=lambda x: x.get('l4_plus_count', 0), reverse=True)
    for r in by_l4[:10]:
        sid = r['signal_id']
        l4 = r.get('l4_plus_count', 0)
        tc = max(r.get('total_cycles', 1), 1)
        l4_pct = l4 / tc * 100
        l4r = r.get('l4_recovery_rate', 0)
        html += f"<tr><td>#{sid}</td><td>{l4}</td><td>{l4_pct:.1f}%</td><td class='{'good' if l4r>=80 else 'danger'}'>{l4r:.1f}%</td><td>${r.get('max_dd',0):,.0f}</td><td>{r.get('win_rate',0):.1f}%</td></tr>\n"
    html += "</table>\n"

    # Sharpe analysis
    html += """<h3>Sharpe Ratio 分佈</h3><table>
    <tr><th>Range</th><th>Count</th><th>Signals</th></tr>\n"""
    sharpe_ranges = [(3, 'inf', '≥ 3.0'), (2, 3, '2.0 - 2.99'), (1, 2, '1.0 - 1.99'), (0, 1, '0.0 - 0.99'), (-999, 0, '< 0')]
    for lo, hi, label in sharpe_ranges:
        group = [r for r in results if lo <= (r.get('sharpe', 0) or 0) < (hi if hi != 'inf' else 9999)]
        sigs = ', '.join(f"#{r['signal_id']}" for r in group[:8])
        if len(group) > 8:
            sigs += f" +{len(group)-8} more"
        html += f"<tr><td>{label}</td><td>{len(group)}</td><td style='font-size:0.8em'>{sigs}</td></tr>\n"
    html += "</table></div>\n"

    html += f"""
<footer>
  🦀 丁蟹 Trade Strategy Analyzer · LITE Mode · 58 Signals · {datetime.now().strftime('%Y-%m-%d %H:%M HKT')}
</footer>
</body></html>"""
    
    summary_path = OUTPUT_DIR / f'summary_all_signals_{datetime.now().strftime("%Y%m%d_%H%M%S")}.html'
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return str(summary_path)


def main():
    results = load_results()
    print(f"🦀 Generating individual reports for {len(results)} signals...")
    
    report_paths = {}
    for i, item in enumerate(results):
        sid = item['signal_id']
        path = generate_signal_report(item)
        report_paths[sid] = path
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{len(results)}] Done")
    
    print(f"\n✅ {len(report_paths)} individual reports generated")
    
    print("\n🦀 Generating summary report...")
    summary_path = generate_summary_report(results)
    print(f"✅ Summary: {summary_path}")
    
    # Print quick stats
    total_pl = sum(r.get('total_profit', 0) for r in results)
    avg_wr = sum(r.get('win_rate', 0) for r in results) / len(results)
    top3_pl = sorted(results, key=lambda x: x.get('total_profit', 0), reverse=True)[:3]
    
    print(f"\n{'='*60}")
    print(f"📊 總結統計")
    print(f"{'='*60}")
    print(f"  Signals: {len(results)}")
    print(f"  Total P/L: ${total_pl:,.2f}")
    print(f"  Avg Win Rate: {avg_wr:.1f}%")
    print(f"  Top 3 by P/L:")
    for r in top3_pl:
        print(f"    #{r['signal_id']}: ${r.get('total_profit',0):,.2f} (WR={r.get('win_rate',0):.1f}%)")
    print(f"\n📄 Summary Report: {summary_path}")


if __name__ == '__main__':
    main()
