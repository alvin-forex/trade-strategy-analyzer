#!/usr/bin/env python3
"""
Generate BUY/SELL Pivot Table HTML for TSA.
Shows BUY vs SELL performance by Signal×CCY and Martin layer breakdown.
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

EA_MAP = {
    'DW': ['10437','11984','13790','17547','21698','22200','22278','25830','30359','31781','32719','3291','33101','31593','34574','36338','36397','36511','34259','20846','16538'],
    'SMA': ['106','1980','2351','32278','32541','5001','5275','537','5566','11889','13863','14724','16596','16698','16706','17611','17823','10864','14158','5636'],
    'MKD': ['12962','13461','14341','14592','1470','17962','20805','23617','25668','25260','8325','7919'],
    'S10': ['13798','16596'],
    'Flash': ['19849'],
    'GEM': ['14581'],
    'MAN': ['12173'],
}

EA_COLORS = {
    'DW': ('#4a148c', '#ce93d8'), 'SMA': ('#1b5e20', '#a5d6a7'),
    'MKD': ('#e65100', '#ffcc80'), 'Flash': ('#0d47a1', '#90caf9'),
    'S10': ('#004d40', '#80cbc4'), 'GEM': ('#880e4f', '#f48fb1'),
    'MAN': ('#4527a0', '#b39ddb'), 'UNK': ('#333', 'var(--text2)'),
}

def get_ea_tag(signal_id):
    s = str(signal_id)
    for ea, ids in EA_MAP.items():
        if s in ids:
            return ea
    return 'UNK'

def get_ea_style(ea):
    bg, fg = EA_COLORS.get(ea.split('/')[0], EA_COLORS['UNK'])
    return f'background:{bg};color:{fg}'

def lots_to_layer(lots):
    """Convert lot size to Martin layer number."""
    lots = float(lots)
    if lots <= 0:
        return 0
    # L1=0.01, L2=0.02, L3=0.04, L4=0.08, L5=0.16, L6=0.32, etc.
    if lots == 0.01:
        return 1
    layer = 1
    while (0.01 * (2 ** (layer - 1))) < lots - 0.0001 and layer < 20:
        layer += 1
    return layer

def calc_stats(trades):
    if not trades:
        return {'trades': 0, 'wins': 0, 'win_pct': 0, 'total_pips': 0,
                'avg_pips': 0, 'total_pnl': 0, 'avg_hold': 0}
    n = len(trades)
    wins = sum(1 for t in trades if t['_net_pips'] > 0)
    total_pips = sum(t['_net_pips'] for t in trades)
    total_pnl = sum(t['_net_profit'] for t in trades)
    hold_sum = sum(t['_hold_hrs'] for t in trades)
    return {
        'trades': n,
        'wins': wins,
        'win_pct': wins / n * 100 if n else 0,
        'total_pips': total_pips,
        'avg_pips': total_pips / n if n else 0,
        'total_pnl': total_pnl,
        'avg_hold': hold_sum / n if n else 0,
    }

def fmt_pnl(v):
    if v >= 0:
        return f'+{v:,.1f}'
    return f'{v:,.1f}'

def win_class(pct):
    if pct >= 70: return 'dd-g'
    if pct >= 50: return 'dd-y'
    return 'dd-r'

def pnl_class(v):
    if v > 0: return 'dd-g'
    if v < 0: return 'dd-r'
    return ''

def load_all_trades():
    all_trades = []
    signal_ids = set()
    symbols = set()
    
    for f in sorted(DOWNLOADS_DIR.glob('*.csv')):
        fname = f.stem
        sid = fname.replace('forex-forest-signals-page-', '').replace('signal_', '')
        try:
            int(sid)
        except ValueError:
            continue
        
        signal_ids.add(sid)
        ea = get_ea_tag(sid)
        
        try:
            with open(f, 'r', encoding='utf-8-sig') as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    row['signal_id'] = sid
                    row['ea'] = ea
                    row['_net_pips'] = float(row.get('Net Pips', '0').replace(',', '') or '0')
                    row['_net_profit'] = float(row.get('Net Profit', '0').replace(',', '') or '0')
                    row['_hold_hrs'] = float(row.get('Holding Time (Hours)', '0') or '0')
                    row['_lots'] = float(row.get('Lots', '0') or '0')
                    row['_layer'] = lots_to_layer(row.get('Lots', '0.01'))
                    sym = row.get('Symbol', '').strip()
                    row['symbol'] = sym
                    row['type'] = row.get('Type', '').strip().lower()
                    if sym:
                        symbols.add(sym)
                    all_trades.append(row)
        except Exception as e:
            print(f"  ⚠️ Error reading {f.name}: {e}")
    
    return all_trades, sorted(signal_ids), sorted(symbols)


def generate_html(all_trades, signal_ids, symbols):
    today = datetime.now().strftime('%Y-%m-%d')
    total_trades = len(all_trades)
    global_stats = calc_stats(all_trades)
    
    # Count unique Signal×CCY pairs
    pairs = set()
    for t in all_trades:
        pairs.add((t['signal_id'], t['symbol']))
    
    # ===== SECTION 1: BUY/SELL Summary =====
    # Group by Signal×CCY
    by_pair = defaultdict(lambda: {'buy': [], 'sell': []})
    for t in all_trades:
        key = (t['signal_id'], t['symbol'])
        tp = t['type']
        if tp in ('buy', 'sell'):
            by_pair[key][tp].append(t)
    
    # Sort by total P&L desc
    pair_list = []
    for (sid, sym), types in by_pair.items():
        buy_s = calc_stats(types['buy'])
        sell_s = calc_stats(types['sell'])
        combined = calc_stats(types['buy'] + types['sell'])
        ea = get_ea_tag(sid)
        pair_list.append({
            'signal_id': sid, 'symbol': sym, 'ea': ea,
            'buy': buy_s, 'sell': sell_s, 'combined': combined,
            'total_pnl': combined['total_pnl'],
        })
    pair_list.sort(key=lambda x: -x['total_pnl'])
    
    summary_rows = ''
    for i, p in enumerate(pair_list[:100], 1):
        ea_style = get_ea_style(p['ea'])
        b = p['buy']
        s = p['sell']
        c = p['combined']
        summary_rows += f'''<tr>
<td>{i}</td>
<td><a href="https://signals.algoforest.com/signals/{p['signal_id']}">{p['signal_id']}</a></td>
<td><span style="{ea_style};padding:1px 6px;border-radius:3px;font-size:0.8em;font-weight:bold">{p['ea']}</span></td>
<td style="font-weight:bold;color:var(--primary)">{p['symbol']}</td>
<td>{b['trades']}</td>
<td class="{win_class(b['win_pct'])}" data-val="{b['win_pct']}">{b['win_pct']:.1f}%</td>
<td data-val="{b['avg_pips']}">{b['avg_pips']:.1f}</td>
<td class="{pnl_class(b['total_pnl'])}" data-val="{b['total_pnl']}">{fmt_pnl(b['total_pnl'])}</td>
<td>{b['avg_hold']:.1f}h</td>
<td>{s['trades']}</td>
<td class="{win_class(s['win_pct'])}" data-val="{s['win_pct']}">{s['win_pct']:.1f}%</td>
<td data-val="{s['avg_pips']}">{s['avg_pips']:.1f}</td>
<td class="{pnl_class(s['total_pnl'])}" data-val="{s['total_pnl']}">{fmt_pnl(s['total_pnl'])}</td>
<td>{s['avg_hold']:.1f}h</td>
<td>{c['trades']}</td>
<td class="{win_class(c['win_pct'])}" data-val="{c['win_pct']}">{c['win_pct']:.1f}%</td>
<td class="{pnl_class(c['total_pnl'])}" data-val="{c['total_pnl']}">{fmt_pnl(c['total_pnl'])}</td>
</tr>'''
    
    # ===== SECTION 2: Martin Layer Analysis =====
    by_layer = defaultdict(lambda: {'buy': [], 'sell': []})
    for t in all_trades:
        layer = t['_layer']
        tp = t['type']
        if tp in ('buy', 'sell'):
            by_layer[layer][tp].append(t)
    
    max_layer = max(by_layer.keys()) if by_layer else 1
    layer_rows = ''
    for layer in range(1, max_layer + 1):
        if layer not in by_layer:
            continue
        types = by_layer[layer]
        b = calc_stats(types['buy'])
        s = calc_stats(types['sell'])
        total = calc_stats(types['buy'] + types['sell'])
        lots_val = 0.01 * (2 ** (layer - 1))
        layer_rows += f'''<tr>
<td>L{layer}</td>
<td>{lots_val:.2f}</td>
<td>{b['trades']}</td>
<td class="{win_class(b['win_pct'])}" data-val="{b['win_pct']}">{b['win_pct']:.1f}%</td>
<td class="{pnl_class(b['total_pnl'])}" data-val="{b['total_pnl']}">{fmt_pnl(b['total_pnl'])}</td>
<td>{b['avg_hold']:.1f}h</td>
<td>{s['trades']}</td>
<td class="{win_class(s['win_pct'])}" data-val="{s['win_pct']}">{s['win_pct']:.1f}%</td>
<td class="{pnl_class(s['total_pnl'])}" data-val="{s['total_pnl']}">{fmt_pnl(s['total_pnl'])}</td>
<td>{s['avg_hold']:.1f}h</td>
<td>{total['trades']}</td>
<td class="{win_class(total['win_pct'])}" data-val="{total['win_pct']}">{total['win_pct']:.1f}%</td>
<td class="{pnl_class(total['total_pnl'])}" data-val="{total['total_pnl']}">{fmt_pnl(total['total_pnl'])}</td>
<td>{total['avg_hold']:.1f}h</td>
</tr>'''
    
    # ===== SECTION 3: Per-Signal Drill-down =====
    by_signal = defaultdict(lambda: {'buy': [], 'sell': []})
    for t in all_trades:
        tp = t['type']
        if tp in ('buy', 'sell'):
            by_signal[t['signal_id']][tp].append(t)
    
    signal_rows = ''
    for sid in sorted(by_signal.keys(), key=lambda x: -calc_stats(by_signal[x]['buy'] + by_signal[x]['sell'])['total_pnl']):
        types = by_signal[sid]
        ea = get_ea_tag(sid)
        ea_style = get_ea_style(ea)
        b = calc_stats(types['buy'])
        s = calc_stats(types['sell'])
        c = calc_stats(types['buy'] + types['sell'])
        
        # Layer breakdown for this signal
        by_signal_layer = defaultdict(lambda: {'buy': [], 'sell': []})
        for t in types['buy'] + types['sell']:
            by_signal_layer[t['_layer']][t['type']].append(t)
        
        detail_rows = ''
        for layer in sorted(by_signal_layer.keys()):
            lt = by_signal_layer[layer]
            lb = calc_stats(lt['buy'])
            ls = calc_stats(lt['sell'])
            lc = calc_stats(lt['buy'] + lt['sell'])
            lots_val = 0.01 * (2 ** (layer - 1))
            detail_rows += f'''<tr style="background:var(--bg-hover)">
<td colspan="3" style="padding-left:30px">L{layer} ({lots_val:.2f} lots)</td>
<td>{lb['trades']}</td><td class="{win_class(lb['win_pct'])}">{lb['win_pct']:.1f}%</td><td class="{pnl_class(lb['total_pnl'])}">{fmt_pnl(lb['total_pnl'])}</td>
<td>{ls['trades']}</td><td class="{win_class(ls['win_pct'])}">{ls['win_pct']:.1f}%</td><td class="{pnl_class(ls['total_pnl'])}">{fmt_pnl(ls['total_pnl'])}</td>
<td>{lc['trades']}</td><td class="{win_class(lc['win_pct'])}">{lc['win_pct']:.1f}%</td><td class="{pnl_class(lc['total_pnl'])}">{fmt_pnl(lc['total_pnl'])}</td>
</tr>'''
        
        signal_rows += f'''<tr class="drill-toggle" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'':'none'">
<td><a href="https://signals.algoforest.com/signals/{sid}">{sid}</a></td>
<td><span style="{ea_style};padding:1px 6px;border-radius:3px;font-size:0.8em;font-weight:bold">{ea}</span></td>
<td style="color:var(--text2);cursor:pointer">▶ 點擊展開</td>
<td>{b['trades']}</td>
<td class="{win_class(b['win_pct'])}" data-val="{b['win_pct']}">{b['win_pct']:.1f}%</td>
<td class="{pnl_class(b['total_pnl'])}" data-val="{b['total_pnl']}">{fmt_pnl(b['total_pnl'])}</td>
<td>{s['trades']}</td>
<td class="{win_class(s['win_pct'])}" data-val="{s['win_pct']}">{s['win_pct']:.1f}%</td>
<td class="{pnl_class(s['total_pnl'])}" data-val="{s['total_pnl']}">{fmt_pnl(s['total_pnl'])}</td>
<td>{c['trades']}</td>
<td class="{win_class(c['win_pct'])}" data-val="{c['win_pct']}">{c['win_pct']:.1f}%</td>
<td class="{pnl_class(c['total_pnl'])}" data-val="{c['total_pnl']}">{fmt_pnl(c['total_pnl'])}</td>
</tr>
<tr class="drill-detail" style="display:none"><td colspan="12">
<div style="padding:8px 0">
<table style="width:100%;border-collapse:collapse">
<thead><tr>
<th>Layer</th><th></th><th></th>
<th>BUY Trades</th><th>BUY Win%</th><th>BUY P&L</th>
<th>SELL Trades</th><th>SELL Win%</th><th>SELL P&L</th>
<th>Total Trades</th><th>Total Win%</th><th>Total P&L</th>
</tr></thead>
<tbody>{detail_rows}</tbody>
</table>
</div>
</td></tr>'''
    
    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🔄 BUY/SELL 分析</title>
<link rel="stylesheet" href="../sidebar.css">
<style>
:root{{--font-main:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Microsoft JhengHei',sans-serif;--radius:8px;--shadow:0 2px 8px rgba(0,0,0,0.12)}}
[data-theme="dark"]{{--bg:#0a0e17;--bg-card:#111520;--bg-hover:#1a1f2e;--text:#d0d0d0;--text2:#888;--primary:#FFD700;--accent:#64b5f6;--green:#4CAF50;--red:#FF5722;--yellow:#FFC107;--orange:#fd7e14;--border:#1e2433;--th-bg:#111520}}
[data-theme="light"]{{--bg:#f5f7fa;--bg-card:#ffffff;--bg-hover:#eef2f7;--text:#333;--text2:#666;--primary:#0f3460;--accent:#e94560;--green:#28a745;--red:#dc3545;--yellow:#ffc107;--orange:#fd7e14;--border:#ddd;--th-bg:#eef2f7}}
*{{transition:background-color .25s ease,color .25s ease,border-color .25s ease;margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--font-main);background:var(--bg);color:var(--text);padding:16px;max-width:1400px;margin:0 auto}}
h1{{font-size:1.3em;margin-bottom:4px;color:var(--primary)}}
h2{{color:var(--primary);font-size:1em;margin:0 0 12px}}
.sub{{color:var(--text2);font-size:0.85em;margin-bottom:16px}}
.stats{{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:12px 18px;margin-bottom:16px;display:flex;gap:30px;flex-wrap:wrap}}
.stats .v{{font-size:1.5em;font-weight:bold;color:var(--primary)}}
.stats .l{{font-size:0.75em;color:var(--text2)}}
table{{width:100%;border-collapse:collapse}}
th{{background:var(--th-bg);padding:8px 10px;text-align:left;border-bottom:2px solid var(--primary);color:var(--primary);font-size:0.8em;white-space:nowrap;cursor:pointer;user-select:none}}
th:hover{{background:var(--bg-hover)}}
th .arrow{{font-size:0.65em;margin-left:3px;opacity:0.3}}
th.asc .arrow{{opacity:1}}
th.desc .arrow{{opacity:1}}
td{{padding:6px 10px;border-bottom:1px solid var(--border);font-size:0.9em}}
tr:hover{{background:var(--bg-card)}}
a{{color:var(--accent);text-decoration:none;font-weight:bold}}
a:hover{{text-decoration:underline}}
.container{{overflow-x:auto}}
.dd-g{{color:var(--green);font-weight:bold}}.dd-y{{color:var(--yellow);font-weight:bold}}.dd-r{{color:var(--red);font-weight:bold}}
.tabs{{display:flex;gap:0;margin-bottom:0}}
.tab{{padding:10px 20px;background:var(--bg-card);border:1px solid var(--border);color:var(--text2);cursor:pointer;border-radius:8px 8px 0 0;font-size:0.95em}}
.tab.active{{background:var(--bg);color:var(--primary);border-bottom-color:var(--bg);font-weight:bold}}
.tab:hover{{color:var(--text)}}
.panel{{background:var(--bg);border:1px solid var(--border);border-top:none;border-radius:0 0 8px 8px;padding:16px}}
.panel.hidden{{display:none}}
.drill-toggle{{cursor:pointer}}
.drill-toggle:hover{{background:var(--bg-hover)!important}}
.buy-header{{background:rgba(76,175,80,0.15);color:var(--green);border-bottom-color:var(--green)}}
.sell-header{{background:rgba(255,87,34,0.15);color:var(--red);border-bottom-color:var(--red)}}
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
  const btn=document.getElementById('theme-toggle');
  if(btn)btn.textContent=next==='dark'?'☀️':'🌙';
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
  var rows=Array.from(tbody.querySelectorAll('tr:not(.drill-detail)'));
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

<div style="display:flex;align-items:center;gap:10px"><h1>🔄 BUY/SELL 分析</h1><button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()" title="切換亮/暗模式" style="width:36px;height:36px;border:1px solid var(--border);border-radius:50%;background:var(--bg-card);color:var(--text);font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0"></button></div>
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:0.82em;color:var(--text2)">
<span>{today} · {total_trades} 筆交易 · {len(pairs)} 個 Signal×CCY 組合</span>
</div>

<div class="stats">
<div><div class="v">{global_stats['trades']}</div><div class="l">Total Trades</div></div>
<div><div class="v">{global_stats['win_pct']:.1f}%</div><div class="l">Win Rate</div></div>
<div><div class="v">{fmt_pnl(global_stats['total_pnl'])}</div><div class="l">Total P&L</div></div>
<div><div class="v">{len(pairs)}</div><div class="l">Signal×CCY</div></div>
</div>

<div class="tabs">
<div class="tab active" onclick="showPanel('summary',this)">📊 BUY/SELL 摘要</div>
<div class="tab" onclick="showPanel('layer',this)">🏗️ 馬丁層數</div>
<div class="tab" onclick="showPanel('drill',this)">🔍 逐層展開</div>
</div>

<!-- SUMMARY -->
<div id="panel-summary" class="panel">
<h2>📊 BUY/SELL 摘要（Top 100 by P&L）</h2>
<div class="container"><table id="tbl-summary"><thead><tr>
<th data-col="0" data-type="num">#</th>
<th data-col="1" data-type="num">Signal</th>
<th data-col="2" data-type="str">EA</th>
<th data-col="3" data-type="str">CCY</th>
<th class="buy-header" data-col="4" data-type="num">BUY Trades</th>
<th class="buy-header" data-col="5" data-type="num">BUY Win%</th>
<th class="buy-header" data-col="6" data-type="num">BUY Avg Pips</th>
<th class="buy-header" data-col="7" data-type="num">BUY P&L</th>
<th class="buy-header" data-col="8" data-type="num">BUY Hold</th>
<th class="sell-header" data-col="9" data-type="num">SELL Trades</th>
<th class="sell-header" data-col="10" data-type="num">SELL Win%</th>
<th class="sell-header" data-col="11" data-type="num">SELL Avg Pips</th>
<th class="sell-header" data-col="12" data-type="num">SELL P&L</th>
<th class="sell-header" data-col="13" data-type="num">SELL Hold</th>
<th data-col="14" data-type="num">Total Trades</th>
<th data-col="15" data-type="num">Total Win%</th>
<th data-col="16" data-type="num">Total P&L</th>
</tr></thead><tbody>{summary_rows}</tbody></table></div></div>

<!-- LAYER -->
<div id="panel-layer" class="panel hidden">
<h2>🏗️ 馬丁層數 BUY/SELL 對比</h2>
<div class="container"><table id="tbl-layer"><thead><tr>
<th data-col="0" data-type="str">Layer</th>
<th data-col="1" data-type="num">Lots</th>
<th class="buy-header" data-col="2" data-type="num">BUY Trades</th>
<th class="buy-header" data-col="3" data-type="num">BUY Win%</th>
<th class="buy-header" data-col="4" data-type="num">BUY P&L</th>
<th class="buy-header" data-col="5" data-type="num">BUY Hold</th>
<th class="sell-header" data-col="6" data-type="num">SELL Trades</th>
<th class="sell-header" data-col="7" data-type="num">SELL Win%</th>
<th class="sell-header" data-col="8" data-type="num">SELL P&L</th>
<th class="sell-header" data-col="9" data-type="num">SELL Hold</th>
<th data-col="10" data-type="num">Total Trades</th>
<th data-col="11" data-type="num">Total Win%</th>
<th data-col="12" data-type="num">Total P&L</th>
<th data-col="13" data-type="num">Total Hold</th>
</tr></thead><tbody>{layer_rows}</tbody></table></div></div>

<!-- DRILL DOWN -->
<div id="panel-drill" class="panel hidden">
<h2>🔍 逐 Signal 層數展開（點擊展開/收起）</h2>
<div class="container"><table id="tbl-drill" style="width:100%"><thead><tr>
<th data-col="0" data-type="num">Signal</th>
<th data-col="1" data-type="str">EA</th>
<th data-col="2" data-type="str">展開</th>
<th class="buy-header" data-col="3" data-type="num">BUY Trades</th>
<th class="buy-header" data-col="4" data-type="num">BUY Win%</th>
<th class="buy-header" data-col="5" data-type="num">BUY P&L</th>
<th class="sell-header" data-col="6" data-type="num">SELL Trades</th>
<th class="sell-header" data-col="7" data-type="num">SELL Win%</th>
<th class="sell-header" data-col="8" data-type="num">SELL P&L</th>
<th data-col="9" data-type="num">Total Trades</th>
<th data-col="10" data-type="num">Total Win%</th>
<th data-col="11" data-type="num">Total P&L</th>
</tr></thead><tbody>{signal_rows}</tbody></table></div></div>

</body></html>'''
    return html


def main():
    print("🔄 Generating BUY/SELL Pivot Table...")
    all_trades, signal_ids, symbols = load_all_trades()
    print(f"  📊 Loaded {len(all_trades)} trades from {len(signal_ids)} signals")
    
    html = generate_html(all_trades, signal_ids, symbols)
    
    for out_dir in [OUTPUT_DIR, REPORTS_DIR, DOCS_DIR / 'admin']:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / 'pivot_table.html'
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        size_kb = len(html.encode('utf-8')) / 1024
        print(f"  ✅ Written: {out_path} ({size_kb:.0f} KB)")


if __name__ == '__main__':
    main()
