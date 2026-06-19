#!/usr/bin/env python3
"""
Generate MFE/MAE Analysis HTML for TSA.
MFE = Maximum Favorable Excursion (Max Profit)
MAE = Maximum Adverse Excursion (Max Loss)
"""
import csv
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / 'downloads'
OUTPUT_DIR = BASE_DIR / 'output'
DOCS_DIR = BASE_DIR / 'docs'
REPORTS_DIR = BASE_DIR / 'reports'
for d in [OUTPUT_DIR, DOCS_DIR, REPORTS_DIR, DOCS_DIR / 'admin']:
    d.mkdir(parents=True, exist_ok=True)

from config import EA_MAP

EA_COLORS = {
    'DW': ('#4a148c', '#ce93d8'), 'SMA': ('#1b5e20', '#a5d6a7'),
    'MKD': ('#e65100', '#ffcc80'), 'Flash': ('#0d47a1', '#90caf9'),
    'S10': ('#004d40', '#80cbc4'), 'GEM': ('#880e4f', '#f48fb1'),
    'MAN': ('#4527a0', '#b39ddb'), 'UNK': ('#333', 'var(--text2)'),
}

def get_ea_tag(sid):
    s = str(sid)
    for ea, ids in EA_MAP.items():
        if s in ids: return ea
    return 'UNK'

def get_ea_style(ea):
    bg, fg = EA_COLORS.get(ea, EA_COLORS['UNK'])
    return f'background:{bg};color:{fg}'

def lots_to_layer(lots):
    lots = float(lots)
    if lots <= 0: return 0
    if lots == 0.01: return 1
    layer = 1
    while (0.01 * (2 ** (layer - 1))) < lots - 0.0001 and layer < 20:
        layer += 1
    return layer

def load_all_trades():
    all_trades = []
    for f in sorted(DOWNLOADS_DIR.glob('*.csv')):
        fname = f.stem
        sid = fname.replace('forex-forest-signals-page-', '').replace('signal_', '')
        try: int(sid)
        except ValueError: continue
        ea = get_ea_tag(sid)
        try:
            with open(f, 'r', encoding='utf-8-sig') as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    row['signal_id'] = sid
                    row['ea'] = ea
                    row['_mfe'] = float(row.get('Max Profit', '0').replace(',', '') or '0')
                    row['_mae'] = float(row.get('Max Loss', '0').replace(',', '') or '0')
                    row['_mfe_pips'] = float(row.get('Max Pips', '0').replace(',', '') or '0')
                    row['_mae_pips'] = float(row.get('Max Loss Pips', '0').replace(',', '') or '0')
                    row['_net_pips'] = float(row.get('Net Pips', '0').replace(',', '') or '0')
                    row['_net_profit'] = float(row.get('Net Profit', '0').replace(',', '') or '0')
                    row['_hold_hrs'] = float(row.get('Holding Time (Hours)', '0') or '0')
                    row['_lots'] = float(row.get('Lots', '0') or '0')
                    row['_layer'] = lots_to_layer(row.get('Lots', '0.01'))
                    row['symbol'] = row.get('Symbol', '').strip()
                    row['type'] = row.get('Type', '').strip().lower()
                    all_trades.append(row)
        except Exception as e:
            print(f"  ⚠️ Error reading {f.name}: {e}")
    return all_trades

def fmt(v):
    if v >= 0: return f'+{v:,.1f}'
    return f'{v:,.1f}'

def pnl_cls(v):
    if v > 0: return 'dd-g'
    if v < 0: return 'dd-r'
    return ''

def win_cls(pct):
    if pct >= 70: return 'dd-g'
    if pct >= 50: return 'dd-y'
    return 'dd-r'

def make_histogram_svg(data, bins=20, width=600, height=200, color='#FFD700', xlabel='', neg_color='#FF5722'):
    """Generate SVG histogram. data can include negative values."""
    if not data:
        return '<svg></svg>'
    
    min_v = min(data)
    max_v = max(data)
    if min_v == max_v:
        return '<svg></svg>'
    
    # Create bins
    bin_width = (max_v - min_v) / bins
    counts = [0] * bins
    for v in data:
        idx = min(int((v - min_v) / bin_width), bins - 1)
        counts[idx] += 1
    
    max_count = max(counts) if counts else 1
    bar_w = width / bins
    padding = 30
    
    svg_parts = [f'<svg viewBox="0 0 {width+60} {height+40}" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:{width+60}px">']
    
    # Draw bars
    for i, c in enumerate(counts):
        x = i * bar_w + padding
        bar_h = (c / max_count) * (height - 20) if max_count else 0
        y = height - bar_h - 10
        bin_val = min_v + (i + 0.5) * bin_width
        fill = neg_color if bin_val < 0 else color
        svg_parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_w-1:.1f}" height="{bar_h:.1f}" fill="{fill}" opacity="0.8" rx="1"/>')
    
    # Zero line
    if min_v < 0 < max_v:
        zero_x = (-min_v / (max_v - min_v)) * width + padding
        svg_parts.append(f'<line x1="{zero_x:.1f}" y1="5" x2="{zero_x:.1f}" y2="{height-5}" stroke="var(--text2)" stroke-width="1" stroke-dasharray="4"/>')
    
    # Axis labels
    svg_parts.append(f'<text x="{padding}" y="{height+5}" fill="var(--text2)" font-size="10">{min_v:.1f}</text>')
    svg_parts.append(f'<text x="{width+padding-30}" y="{height+5}" fill="var(--text2)" font-size="10">{max_v:.1f}</text>')
    if xlabel:
        svg_parts.append(f'<text x="{width/2+padding}" y="{height+18}" fill="var(--text2)" font-size="10" text-anchor="middle">{xlabel}</text>')
    
    svg_parts.append('</svg>')
    return '\n'.join(svg_parts)


def generate_html(all_trades):
    today = datetime.now().strftime('%Y-%m-%d')
    n = len(all_trades)
    
    # Global stats
    avg_mfe = sum(t['_mfe'] for t in all_trades) / n if n else 0
    avg_mae = sum(t['_mae'] for t in all_trades) / n if n else 0
    avg_mfe_pips = sum(t['_mfe_pips'] for t in all_trades) / n if n else 0
    avg_mae_pips = sum(t['_mae_pips'] for t in all_trades) / n if n else 0
    mfe_mae_ratio = abs(avg_mfe / avg_mae) if avg_mae != 0 else 0
    
    wins = [t for t in all_trades if t['_net_pips'] > 0]
    losses = [t for t in all_trades if t['_net_pips'] <= 0]
    
    # MFE of winners vs MFE of losers
    avg_mfe_win = sum(t['_mfe'] for t in wins) / len(wins) if wins else 0
    avg_mfe_loss = sum(t['_mfe'] for t in losses) / len(losses) if losses else 0
    avg_mae_win = sum(t['_mae'] for t in wins) / len(wins) if wins else 0
    avg_mae_loss = sum(t['_mae'] for t in losses) / len(losses) if losses else 0
    
    # ===== SECTION 1: Global Distribution =====
    mfe_data = [t['_mfe'] for t in all_trades]
    mae_data = [t['_mae'] for t in all_trades]
    mfe_pips_data = [t['_mfe_pips'] for t in all_trades]
    mae_pips_data = [t['_mae_pips'] for t in all_trades]
    
    svg_mfe = make_histogram_svg(mfe_data, bins=25, color='#4CAF50', xlabel='MFE ($)')
    svg_mae = make_histogram_svg(mae_data, bins=25, color='#FF5722', xlabel='MAE ($)')
    svg_mfe_pips = make_histogram_svg(mfe_pips_data, bins=25, color='#4CAF50', xlabel='MFE (pips)')
    svg_mae_pips = make_histogram_svg(mae_pips_data, bins=25, color='#FF5722', xlabel='MAE (pips)')
    
    # ===== SECTION 2: Per Signal×CCY =====
    by_pair = defaultdict(list)
    for t in all_trades:
        key = (t['signal_id'], t['symbol'])
        by_pair[key].append(t)
    
    pair_list = []
    for (sid, sym), trades in by_pair.items():
        n_t = len(trades)
        wins_t = [t for t in trades if t['_net_pips'] > 0]
        avg_mfe_t = sum(t['_mfe'] for t in trades) / n_t
        avg_mae_t = sum(t['_mae'] for t in trades) / n_t
        avg_mfe_pips_t = sum(t['_mfe_pips'] for t in trades) / n_t
        avg_mae_pips_t = sum(t['_mae_pips'] for t in trades) / n_t
        ratio_t = abs(avg_mfe_t / avg_mae_t) if avg_mae_t != 0 else 999
        total_pnl = sum(t['_net_profit'] for t in trades)
        win_pct = len(wins_t) / n_t * 100 if n_t else 0
        ea = get_ea_tag(sid)
        
        # TP/SL suggestion
        tp_suggestion = avg_mfe_pips_t * 0.8
        sl_suggestion = abs(avg_mae_pips_t) * 1.2
        
        pair_list.append({
            'signal_id': sid, 'symbol': sym, 'ea': ea,
            'trades': n_t, 'win_pct': win_pct,
            'avg_mfe': avg_mfe_t, 'avg_mae': avg_mae_t,
            'avg_mfe_pips': avg_mfe_pips_t, 'avg_mae_pips': avg_mae_pips_t,
            'ratio': ratio_t, 'total_pnl': total_pnl,
            'tp': tp_suggestion, 'sl': sl_suggestion,
        })
    
    pair_list.sort(key=lambda x: -x['ratio'])
    
    pair_rows = ''
    for p in pair_list[:100]:
        ea_style = get_ea_style(p['ea'])
        ratio_color = 'var(--green)' if p['ratio'] > 1.5 else ('var(--yellow)' if p['ratio'] > 1 else 'var(--red)')
        pair_rows += f'''<tr>
<td><a href="https://signals.algoforest.com/signals/{p['signal_id']}">{p['signal_id']}</a></td>
<td><span style="{ea_style};padding:1px 6px;border-radius:3px;font-size:0.8em;font-weight:bold">{p['ea']}</span></td>
<td style="font-weight:bold;color:var(--primary)">{p['symbol']}</td>
<td>{p['trades']}</td>
<td class="{win_cls(p['win_pct'])}">{p['win_pct']:.1f}%</td>
<td data-val="{p['avg_mfe']}" class="dd-g">{p['avg_mfe']:.1f}</td>
<td data-val="{p['avg_mae']}" class="dd-r">{p['avg_mae']:.1f}</td>
<td data-val="{p['avg_mfe_pips']}" class="dd-g">{p['avg_mfe_pips']:.1f}</td>
<td data-val="{p['avg_mae_pips']}" class="dd-r">{p['avg_mae_pips']:.1f}</td>
<td style="color:{ratio_color};font-weight:bold" data-val="{p['ratio']}">{p['ratio']:.2f}</td>
<td class="{pnl_cls(p['total_pnl'])}" data-val="{p['total_pnl']}">{fmt(p['total_pnl'])}</td>
<td style="color:var(--green)">{p['tp']:.1f}</td>
<td style="color:var(--red)">{p['sl']:.1f}</td>
</tr>'''
    
    # ===== SECTION 3: By Layer =====
    by_layer = defaultdict(list)
    for t in all_trades:
        by_layer[t['_layer']].append(t)
    
    layer_rows = ''
    for layer in sorted(by_layer.keys()):
        trades = by_layer[layer]
        n_t = len(trades)
        wins_t = [t for t in trades if t['_net_pips'] > 0]
        avg_mfe_t = sum(t['_mfe'] for t in trades) / n_t
        avg_mae_t = sum(t['_mae'] for t in trades) / n_t
        avg_mfe_pips_t = sum(t['_mfe_pips'] for t in trades) / n_t
        avg_mae_pips_t = sum(t['_mae_pips'] for t in trades) / n_t
        ratio_t = abs(avg_mfe_t / avg_mae_t) if avg_mae_t != 0 else 999
        total_pnl = sum(t['_net_profit'] for t in trades)
        win_pct = len(wins_t) / n_t * 100
        lots_val = 0.01 * (2 ** (layer - 1))
        avg_hold = sum(t['_hold_hrs'] for t in trades) / n_t
        
        layer_rows += f'''<tr>
<td>L{layer}</td>
<td>{lots_val:.2f}</td>
<td>{n_t}</td>
<td class="{win_cls(win_pct)}">{win_pct:.1f}%</td>
<td class="dd-g" data-val="{avg_mfe_t}">{avg_mfe_t:.1f}</td>
<td class="dd-r" data-val="{avg_mae_t}">{avg_mae_t:.1f}</td>
<td class="dd-g" data-val="{avg_mfe_pips_t}">{avg_mfe_pips_t:.1f}</td>
<td class="dd-r" data-val="{avg_mae_pips_t}">{avg_mae_pips_t:.1f}</td>
<td style="font-weight:bold" data-val="{ratio_t}">{ratio_t:.2f}</td>
<td class="{pnl_cls(total_pnl)}" data-val="{total_pnl}">{fmt(total_pnl)}</td>
<td>{avg_hold:.1f}h</td>
</tr>'''
    
    # ===== SECTION 4: Winner vs Loser MFE/MAE =====
    svg_mfe_win = make_histogram_svg([t['_mfe'] for t in wins], bins=20, color='#4CAF50', xlabel='MFE of Winners ($)')
    svg_mfe_loss = make_histogram_svg([t['_mfe'] for t in losses], bins=20, color='#FF9800', xlabel='MFE of Losers ($)')
    svg_mae_win = make_histogram_svg([t['_mae'] for t in wins], bins=20, color='#2196F3', xlabel='MAE of Winners ($)')
    svg_mae_loss = make_histogram_svg([t['_mae'] for t in losses], bins=20, color='#FF5722', xlabel='MAE of Losers ($)')
    
    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📊 MFE/MAE 分析</title>
<link rel="stylesheet" href="../sidebar.css">
<style>
:root{{--font-main:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Microsoft JhengHei',sans-serif}}
[data-theme="dark"]{{--bg:#0a0e17;--bg-card:#111520;--bg-hover:#1a1f2e;--text:#d0d0d0;--text2:#888;--primary:#FFD700;--accent:#64b5f6;--green:#4CAF50;--red:#FF5722;--yellow:#FFC107;--orange:#fd7e14;--border:#1e2433;--th-bg:#111520}}
[data-theme="light"]{{--bg:#f5f7fa;--bg-card:#ffffff;--bg-hover:#eef2f7;--text:#333;--text2:#666;--primary:#0f3460;--accent:#e94560;--green:#28a745;--red:#dc3545;--yellow:#ffc107;--orange:#fd7e14;--border:#ddd;--th-bg:#eef2f7}}
*{{transition:background-color .25s ease,color .25s ease,border-color .25s ease;margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--font-main);background:var(--bg);color:var(--text);padding:16px;max-width:1400px;margin:0 auto}}
h1{{font-size:1.3em;margin-bottom:4px;color:var(--primary)}}
h2{{color:var(--primary);font-size:1em;margin:0 0 12px}}
.sub{{color:var(--text2);font-size:0.85em;margin-bottom:16px}}
.stats{{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:12px 18px;margin-bottom:16px;display:flex;gap:24px;flex-wrap:wrap}}
.stats .v{{font-size:1.4em;font-weight:bold;color:var(--primary)}}
.stats .l{{font-size:0.75em;color:var(--text2)}}
table{{width:100%;border-collapse:collapse}}
th{{background:var(--th-bg);padding:8px 10px;text-align:left;border-bottom:2px solid var(--primary);color:var(--primary);font-size:0.8em;white-space:nowrap;cursor:pointer;user-select:none}}
th:hover{{background:var(--bg-hover)}}
td{{padding:6px 10px;border-bottom:1px solid var(--border);font-size:0.88em}}
tr:hover{{background:var(--bg-card)}}
a{{color:var(--accent);text-decoration:none;font-weight:bold}}
a:hover{{text-decoration:underline}}
.container{{overflow-x:auto}}
.dd-g{{color:var(--green);font-weight:bold}}.dd-y{{color:var(--yellow);font-weight:bold}}.dd-r{{color:var(--red);font-weight:bold}}
.tabs{{display:flex;gap:0;margin-bottom:0;flex-wrap:wrap}}
.tab{{padding:10px 18px;background:var(--bg-card);border:1px solid var(--border);color:var(--text2);cursor:pointer;border-radius:8px 8px 0 0;font-size:0.92em}}
.tab.active{{background:var(--bg);color:var(--primary);border-bottom-color:var(--bg);font-weight:bold}}
.tab:hover{{color:var(--text)}}
.panel{{background:var(--bg);border:1px solid var(--border);border-top:none;border-radius:0 0 8px 8px;padding:16px}}
.panel.hidden{{display:none}}
.chart-box{{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:12px}}
.chart-title{{color:var(--primary);font-size:0.9em;font-weight:bold;margin-bottom:8px}}
.suggest{{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:12px 16px;margin-top:12px;display:flex;gap:20px;flex-wrap:wrap}}
.suggest .item{{text-align:center}}
.suggest .val{{font-size:1.3em;font-weight:bold}}
.suggest .lab{{font-size:0.75em;color:var(--text2)}}
@media(max-width:768px){{body{{padding:8px;font-size:12px}}.tab{{padding:8px 12px;font-size:0.85em}}}}
</style>
<script>
(function(){{
  const saved=localStorage.getItem('tsa-theme');
  const t=saved||'dark';
  document.documentElement.setAttribute('data-theme',t);
  document.addEventListener('DOMContentLoaded',function(){{
    const btn=document.getElementById('theme-toggle');
    if(btn)btn.textContent=t==='dark'?'☀️':'🌙';
  }});
}})();
function toggleTheme(){{
  const cur=document.documentElement.getAttribute('data-theme');
  const next=cur==='dark'?'light':'dark';
  document.documentElement.setAttribute('data-theme',next);
  localStorage.setItem('tsa-theme',next);
  document.getElementById('theme-toggle').textContent=next==='dark'?'☀️':'🌙';
}}
function showPanel(id,el){{
  document.querySelectorAll('.panel').forEach(function(p){{p.classList.add('hidden')}});
  document.querySelectorAll('.tab').forEach(function(t){{t.classList.remove('active')}});
  document.getElementById('panel-'+id).classList.remove('hidden');
  el.classList.add('active');
}}
function getCellValue(row,colIdx,type){{
  var cell=row.cells[colIdx];if(!cell)return type==='num'?0:'';
  var dv=cell.getAttribute('data-val');
  if(dv!==null)return type==='num'?parseFloat(dv):dv;
  var text=cell.textContent.trim().replace(/[^0-9.\\-]/g,'');
  return type==='num'?(parseFloat(text)||0):cell.textContent.trim();
}}
function sortTable(table,colIdx,type){{
  var tbody=table.tBodies[0];
  var rows=Array.from(tbody.querySelectorAll('tr'));
  var ths=table.querySelectorAll('thead th');
  var dir=ths[colIdx].classList.contains('asc')?'desc':'asc';
  ths.forEach(function(h){{h.classList.remove('asc','desc')}});
  ths[colIdx].classList.add(dir);
  rows.sort(function(a,b){{
    var va=getCellValue(a,colIdx,type);
    var vb=getCellValue(b,colIdx,type);
    if(type==='num')return dir==='asc'?va-vb:vb-va;
    return dir==='asc'?String(va).localeCompare(String(vb)):String(vb).localeCompare(String(va));
  }});
  rows.forEach(function(r){{tbody.appendChild(r)}});
}}
document.addEventListener('DOMContentLoaded',function(){{
  document.querySelectorAll('table[id^="tbl"]').forEach(function(table){{
    table.querySelectorAll('thead th').forEach(function(th,i){{
      th.addEventListener('click',function(){{sortTable(table,i,th.getAttribute('data-type')||'str')}});
    }});
  }});
}});
</script>
</head>
<body>

<div style="display:flex;align-items:center;gap:10px"><h1>📊 MFE/MAE 分析</h1><button id="theme-toggle" onclick="toggleTheme()" title="切換亮/暗模式" style="width:36px;height:36px;border:1px solid var(--border);border-radius:50%;background:var(--bg-card);color:var(--text);font-size:18px;cursor:pointer;flex-shrink:0"></button></div>
<div class="sub">{today} · {n} 筆交易 · MFE=最大有利偏移 · MAE=最大不利偏移</div>

<div class="stats">
<div><div class="v">{avg_mfe:.1f}</div><div class="l">Avg MFE ($)</div></div>
<div><div class="v">{avg_mae:.1f}</div><div class="l">Avg MAE ($)</div></div>
<div><div class="v">{mfe_mae_ratio:.2f}</div><div class="l">MFE/MAE Ratio</div></div>
<div><div class="v">{avg_mfe_pips:.1f}</div><div class="l">Avg MFE (pips)</div></div>
<div><div class="v">{avg_mae_pips:.1f}</div><div class="l">Avg MAE (pips)</div></div>
</div>

<div class="tabs">
<div class="tab active" onclick="showPanel('dist',this)">📈 分佈圖</div>
<div class="tab" onclick="showPanel('pair',this)">💱 Signal×CCY</div>
<div class="tab" onclick="showPanel('layer',this)">🏗️ 層數分析</div>
<div class="tab" onclick="showPanel('winloss',this)">✅❌ 贏輸對比</div>
</div>

<!-- DISTRIBUTION -->
<div id="panel-dist" class="panel">
<h2>📈 MFE/MAE 全局分佈</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
<div class="chart-box"><div class="chart-title">MFE 分佈 ($)</div>{svg_mfe}</div>
<div class="chart-box"><div class="chart-title">MAE 分佈 ($)</div>{svg_mae}</div>
<div class="chart-box"><div class="chart-title">MFE 分佈 (pips)</div>{svg_mfe_pips}</div>
<div class="chart-box"><div class="chart-title">MAE 分佈 (pips)</div>{svg_mae_pips}</div>
</div>
<div class="suggest">
<div class="item"><div class="val" style="color:var(--green)">{avg_mfe_pips*0.8:.1f} pips</div><div class="lab">建議 TP（80% Avg MFE）</div></div>
<div class="item"><div class="val" style="color:var(--red)">{abs(avg_mae_pips)*1.2:.1f} pips</div><div class="lab">建議 SL（120% Avg MAE）</div></div>
<div class="item"><div class="val">{avg_mfe_pips*0.8/abs(avg_mae_pips)/1.2:.2f}</div><div class="lab">建議 Risk/Reward</div></div>
</div>
</div>

<!-- PAIR -->
<div id="panel-pair" class="panel hidden">
<h2>💱 按 Signal×CCY MFE/MAE（Top 100 by Ratio）</h2>
<div class="container"><table id="tbl-pair"><thead><tr>
<th data-col="0" data-type="num">Signal</th>
<th data-col="1" data-type="str">EA</th>
<th data-col="2" data-type="str">CCY</th>
<th data-col="3" data-type="num">Trades</th>
<th data-col="4" data-type="num">Win%</th>
<th data-col="5" data-type="num">Avg MFE $</th>
<th data-col="6" data-type="num">Avg MAE $</th>
<th data-col="7" data-type="num">Avg MFE pips</th>
<th data-col="8" data-type="num">Avg MAE pips</th>
<th data-col="9" data-type="num">MFE/MAE</th>
<th data-col="10" data-type="num">Total P&L</th>
<th data-col="11" data-type="num">建議 TP</th>
<th data-col="12" data-type="num">建議 SL</th>
</tr></thead><tbody>{pair_rows}</tbody></table></div></div>

<!-- LAYER -->
<div id="panel-layer" class="panel hidden">
<h2>🏗️ 按馬丁層數 MFE/MAE</h2>
<div class="container"><table id="tbl-layer"><thead><tr>
<th data-col="0" data-type="str">Layer</th>
<th data-col="1" data-type="num">Lots</th>
<th data-col="2" data-type="num">Trades</th>
<th data-col="3" data-type="num">Win%</th>
<th data-col="4" data-type="num">Avg MFE $</th>
<th data-col="5" data-type="num">Avg MAE $</th>
<th data-col="6" data-type="num">Avg MFE pips</th>
<th data-col="7" data-type="num">Avg MAE pips</th>
<th data-col="8" data-type="num">MFE/MAE</th>
<th data-col="9" data-type="num">Total P&L</th>
<th data-col="10" data-type="num">Avg Hold</th>
</tr></thead><tbody>{layer_rows}</tbody></table></div></div>

<!-- WIN VS LOSS -->
<div id="panel-winloss" class="panel hidden">
<h2>✅❌ 贏家 vs 輸家 MFE/MAE 對比</h2>
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
<div class="chart-box"><div class="chart-title">✅ 贏家 MFE（平均 {avg_mfe_win:.1f}）</div>{svg_mfe_win}</div>
<div class="chart-box"><div class="chart-title">❌ 輸家 MFE（平均 {avg_mfe_loss:.1f}）</div>{svg_mfe_loss}</div>
<div class="chart-box"><div class="chart-title">✅ 贏家 MAE（平均 {avg_mae_win:.1f}）</div>{svg_mae_win}</div>
<div class="chart-box"><div class="chart-title">❌ 輸家 MAE（平均 {avg_mae_loss:.1f}）</div>{svg_mae_loss}</div>
</div>
<div class="suggest">
<div class="item"><div class="val" style="color:var(--green)">{len(wins)}</div><div class="lab">贏家</div></div>
<div class="item"><div class="val" style="color:var(--red)">{len(losses)}</div><div class="lab">輸家</div></div>
<div class="item"><div class="val">{avg_mfe_win:.1f} / {avg_mfe_loss:.1f}</div><div class="lab">MFE 贏 vs 輸</div></div>
<div class="item"><div class="val">{avg_mae_win:.1f} / {avg_mae_loss:.1f}</div><div class="lab">MAE 贏 vs 輸</div></div>
</div>
</div>

</body></html>'''
    return html


def main():
    print("📊 Generating MFE/MAE Analysis...")
    all_trades = load_all_trades()
    print(f"  Loaded {len(all_trades)} trades")
    
    html = generate_html(all_trades)
    
    for out_dir in [OUTPUT_DIR, REPORTS_DIR, DOCS_DIR / 'admin']:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / 'mfe_mae.html'
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        size_kb = len(html.encode('utf-8')) / 1024
        print(f"  ✅ Written: {out_path} ({size_kb:.0f} KB)")


if __name__ == '__main__':
    main()
