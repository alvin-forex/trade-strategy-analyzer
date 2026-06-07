#!/usr/bin/env python3
"""
Generate Time Period Statistics HTML for TSA.
Analyzes trading data by Day/Week/Month/Quarter/Year/Hour/Magic/Comment.
"""
import csv
import os
import sys
import math
from pathlib import Path
from datetime import datetime
from collections import defaultdict, Counter

BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / 'downloads'
OUTPUT_DIR = BASE_DIR / 'output'
DOCS_DIR = BASE_DIR / 'docs'
REPORTS_DIR = BASE_DIR / 'reports'
for d in [OUTPUT_DIR, DOCS_DIR, REPORTS_DIR, DOCS_DIR / 'admin']:
    d.mkdir(parents=True, exist_ok=True)

# Import EA configuration from centralized config
from config import EA_MAP, EA_COLORS, get_ea_type

def get_ea_tag(signal_id):
    """Alias for get_ea_type for backward compatibility."""
    return get_ea_type(signal_id)

def get_ea_style(ea):
    bg, fg = EA_COLORS.get(ea, EA_COLORS['UNK'])
    return f'background:{bg};color:{fg}'

def parse_date(s):
    try:
        return datetime.strptime(s.strip(), '%d/%m/%Y %H:%M:%S')
    except:
        return None

def load_all_trades():
    all_trades = []
    signal_ids = set()
    symbols = set()
    
    for f in sorted(DOWNLOADS_DIR.glob('*.csv')):
        fname = f.stem
        # Extract signal_id from filename
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
                    row['_open_dt'] = parse_date(row.get('Open Time', ''))
                    row['_close_dt'] = parse_date(row.get('Close Time', ''))
                    row['_net_pips'] = float(row.get('Net Pips', '0').replace(',', '') or '0')
                    row['_net_profit'] = float(row.get('Net Profit', '0').replace(',', '') or '0')
                    row['_hold_hrs'] = float(row.get('Holding Time (Hours)', '0') or '0')
                    sym = row.get('Symbol', '').strip()
                    row['symbol'] = sym
                    if sym:
                        symbols.add(sym)
                    all_trades.append(row)
        except Exception as e:
            print(f"  ⚠️ Error reading {f.name}: {e}")
    
    return all_trades, sorted(signal_ids), sorted(symbols)

def calc_stats(trades):
    if not trades:
        return {'trades': 0, 'wins': 0, 'win_pct': 0, 'total_pips': 0, 'avg_pips': 0,
                'total_pnl': 0, 'avg_hold': 0}
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

def bar_html(value, max_val, color='#FFD700', height=18):
    w = abs(value) / max_val * 100 if max_val else 0
    return f'<div style="background:{color};height:{height}px;width:{w:.1f}%;border-radius:3px;min-width:2px"></div>'

def make_period_table(rows, headers, extra_cols=''):
    thead = '<thead><tr>' + ''.join(
        f'<th data-col="{i}" data-type="{"num" if i > 0 else "str"}">{h}<span class="arrow"></span></th>'
        for i, h in enumerate(headers)
    ) + '</tr></thead>'
    tbody = '<tbody>' + ''.join(rows) + '</tbody>'
    return f'<table>{thead}{tbody}</table>'

def generate_html(all_trades, signal_ids, symbols):
    today = datetime.now().strftime('%Y-%m-%d')
    
    # Global stats
    total_trades = len(all_trades)
    global_stats = calc_stats(all_trades)
    
    # Signal options
    sig_opts = '<option value="">All Signals</option>'
    for s in signal_ids:
        ea = get_ea_tag(s)
        sig_opts += f'<option value="{s}">{s} ({ea})</option>'
    
    sym_opts = '<option value="">All CCY</option>'
    for s in symbols:
        sym_opts += f'<option value="{s}">{s}</option>'
    
    # ===== DAY OF WEEK =====
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    day_data = defaultdict(list)
    for t in all_trades:
        if t['_open_dt']:
            day_data[t['_open_dt'].weekday()].append(t)
    
    max_day_win = max((calc_stats(day_data.get(i, [])).get('win_pct', 0) for i in range(7)), default=100) or 100
    
    day_rows = ''
    for i in range(7):
        s = calc_stats(day_data.get(i, []))
        best_ccy = ''
        worst_ccy = ''
        if day_data.get(i):
            by_sym = defaultdict(list)
            for t in day_data[i]:
                by_sym[t['symbol']].append(t)
            sym_stats = {sym: calc_stats(ts) for sym, ts in by_sym.items()}
            best_ccy = max(sym_stats, key=lambda x: sym_stats[x]['win_pct']) if sym_stats else ''
            worst_ccy = min(sym_stats, key=lambda x: sym_stats[x]['win_pct']) if sym_stats else ''
        bar = bar_html(s['win_pct'], max_day_win)
        day_rows += f'''<tr>
<td>{day_names[i]}</td>
<td>{s['trades']}</td>
<td class="{win_class(s['win_pct'])}" data-val="{s['win_pct']}">{s['win_pct']:.1f}%</td>
<td>{bar}</td>
<td data-val="{s['avg_pips']}">{s['avg_pips']:.1f}</td>
<td class="{pnl_class(s['total_pnl'])}" data-val="{s['total_pnl']}">{fmt_pnl(s['total_pnl'])}</td>
<td>{s['avg_hold']:.1f}h</td>
<td>{best_ccy}</td>
<td>{worst_ccy}</td>
</tr>'''
    
    # ===== WEEK =====
    week_data = defaultdict(list)
    for t in all_trades:
        if t['_open_dt']:
            wk = t['_open_dt'].isocalendar()
            week_data[f"{wk[0]}-W{wk[1]:02d}"].append(t)
    
    week_rows = ''
    for wk in sorted(week_data.keys())[-12:]:
        s = calc_stats(week_data[wk])
        week_rows += f'''<tr>
<td>{wk}</td>
<td>{s['trades']}</td>
<td class="{win_class(s['win_pct'])}" data-val="{s['win_pct']}">{s['win_pct']:.1f}%</td>
<td class="{pnl_class(s['total_pnl'])}" data-val="{s['total_pnl']}">{fmt_pnl(s['total_pnl'])}</td>
<td>{s['avg_hold']:.1f}h</td>
</tr>'''
    
    # ===== MONTH =====
    month_data = defaultdict(list)
    for t in all_trades:
        if t['_open_dt']:
            month_data[t['_open_dt'].strftime('%Y-%m')].append(t)
    
    month_rows = ''
    for m in sorted(month_data.keys())[-12:]:
        s = calc_stats(month_data[m])
        month_rows += f'''<tr>
<td>{m}</td>
<td>{s['trades']}</td>
<td class="{win_class(s['win_pct'])}" data-val="{s['win_pct']}">{s['win_pct']:.1f}%</td>
<td class="{pnl_class(s['total_pnl'])}" data-val="{s['total_pnl']}">{fmt_pnl(s['total_pnl'])}</td>
<td>{s['avg_hold']:.1f}h</td>
</tr>'''
    
    # ===== QUARTER =====
    quarter_data = defaultdict(list)
    for t in all_trades:
        if t['_open_dt']:
            q = (t['_open_dt'].month - 1) // 3 + 1
            quarter_data[f"{t['_open_dt'].year}-Q{q}"].append(t)
    
    quarter_rows = ''
    for q in sorted(quarter_data.keys()):
        s = calc_stats(quarter_data[q])
        quarter_rows += f'''<tr>
<td>{q}</td>
<td>{s['trades']}</td>
<td class="{win_class(s['win_pct'])}" data-val="{s['win_pct']}">{s['win_pct']:.1f}%</td>
<td class="{pnl_class(s['total_pnl'])}" data-val="{s['total_pnl']}">{fmt_pnl(s['total_pnl'])}</td>
<td>{s['avg_hold']:.1f}h</td>
</tr>'''
    
    # ===== YEAR =====
    year_data = defaultdict(list)
    for t in all_trades:
        if t['_open_dt']:
            year_data[str(t['_open_dt'].year)].append(t)
    
    year_rows = ''
    for y in sorted(year_data.keys()):
        s = calc_stats(year_data[y])
        year_rows += f'''<tr>
<td>{y}</td>
<td>{s['trades']}</td>
<td class="{win_class(s['win_pct'])}" data-val="{s['win_pct']}">{s['win_pct']:.1f}%</td>
<td class="{pnl_class(s['total_pnl'])}" data-val="{s['total_pnl']}">{fmt_pnl(s['total_pnl'])}</td>
<td>{s['avg_hold']:.1f}h</td>
</tr>'''
    
    # ===== HOUR =====
    hour_data = defaultdict(list)
    for t in all_trades:
        if t['_open_dt']:
            hour_data[t['_open_dt'].hour].append(t)
    
    max_hour_trades = max((len(hour_data.get(i, [])) for i in range(24)), default=1) or 1
    
    hour_rows = ''
    for h in range(24):
        s = calc_stats(hour_data.get(h, []))
        bar = bar_html(s['trades'], max_hour_trades, '#64b5f6')
        hour_rows += f'''<tr>
<td>{h:02d}:00</td>
<td>{s['trades']}</td>
<td>{bar}</td>
<td class="{win_class(s['win_pct'])}" data-val="{s['win_pct']}">{s['win_pct']:.1f}%</td>
<td data-val="{s['avg_pips']}">{s['avg_pips']:.1f}</td>
<td class="{pnl_class(s['total_pnl'])}" data-val="{s['total_pnl']}">{fmt_pnl(s['total_pnl'])}</td>
</tr>'''
    
    # ===== MAGIC NUMBER =====
    magic_data = defaultdict(list)
    for t in all_trades:
        mn = t.get('Magic Number', '').strip()
        if mn:
            magic_data[mn].append(t)
    
    magic_rows = ''
    for mn in sorted(magic_data.keys(), key=lambda x: -len(magic_data[x])):
        s = calc_stats(magic_data[mn])
        magic_rows += f'''<tr>
<td>{mn}</td>
<td>{s['trades']}</td>
<td class="{win_class(s['win_pct'])}" data-val="{s['win_pct']}">{s['win_pct']:.1f}%</td>
<td class="{pnl_class(s['total_pnl'])}" data-val="{s['total_pnl']}">{fmt_pnl(s['total_pnl'])}</td>
<td>{s['avg_hold']:.1f}h</td>
</tr>'''
    
    # ===== COMMENT =====
    comment_data = defaultdict(list)
    for t in all_trades:
        cm = t.get('Comment', '').strip()
        if cm:
            comment_data[cm].append(t)
    
    comment_rows = ''
    for cm in sorted(comment_data.keys(), key=lambda x: -len(comment_data[x]))[:50]:
        s = calc_stats(comment_data[cm])
        comment_rows += f'''<tr>
<td title="{cm}">{cm[:40]}{"..." if len(cm)>40 else ""}</td>
<td>{s['trades']}</td>
<td class="{win_class(s['win_pct'])}" data-val="{s['win_pct']}">{s['win_pct']:.1f}%</td>
<td class="{pnl_class(s['total_pnl'])}" data-val="{s['total_pnl']}">{fmt_pnl(s['total_pnl'])}</td>
<td>{s['avg_hold']:.1f}h</td>
</tr>'''
    
    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>⏰ 時間統計</title>
<link rel="stylesheet" href="../sidebar.css">
<style>
:root{{--font-main:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Microsoft JhengHei',sans-serif;--radius:8px;--shadow:0 2px 8px rgba(0,0,0,0.12)}}
[data-theme="dark"]{{--bg:#0a0e17;--bg-card:#111520;--bg-hover:#1a1f2e;--text:#d0d0d0;--text2:#888;--primary:#FFD700;--accent:#64b5f6;--green:#4CAF50;--red:#FF5722;--yellow:#FFC107;--orange:#fd7e14;--border:#1e2433;--th-bg:#111520}}
[data-theme="light"]{{--bg:#f5f7fa;--bg-card:#ffffff;--bg-hover:#eef2f7;--text:#333;--text2:#666;--primary:#0f3460;--accent:#e94560;--green:#28a745;--red:#dc3545;--yellow:#ffc107;--orange:#fd7e14;--border:#ddd;--th-bg:#eef2f7}}
*{{transition:background-color .25s ease,color .25s ease,border-color .25s ease;margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--font-main);background:var(--bg);color:var(--text);padding:16px;max-width:1400px;margin:0 auto}}
h1{{font-size:1.3em;margin-bottom:4px;color:var(--primary)}}
.sub{{color:var(--text2);font-size:0.85em;margin-bottom:16px}}
.stats{{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:12px 18px;margin-bottom:16px;display:flex;gap:30px;flex-wrap:wrap}}
.stats .v{{font-size:1.5em;font-weight:bold;color:var(--primary)}}
.stats .l{{font-size:0.75em;color:var(--text2)}}
.filters{{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:12px 18px;margin-bottom:16px;display:flex;gap:12px;flex-wrap:wrap;align-items:center}}
select,input[type=date]{{background:var(--bg-card);border:1px solid var(--border);color:var(--text);padding:6px 10px;border-radius:6px;font-size:13px}}
table{{width:100%;border-collapse:collapse}}
th{{background:var(--th-bg);padding:8px 10px;text-align:left;border-bottom:2px solid var(--primary);color:var(--primary);font-size:0.8em;white-space:nowrap;cursor:pointer;user-select:none}}
th:hover{{background:var(--bg-hover)}}
th .arrow{{font-size:0.65em;margin-left:3px;opacity:0.3}}
th.asc .arrow{{opacity:1}}
th.desc .arrow{{opacity:1}}
td{{padding:6px 10px;border-bottom:1px solid var(--border);font-size:0.9em}}
tr:hover{{background:var(--bg-card)}}
.container{{overflow-x:auto}}
.dd-g{{color:var(--green);font-weight:bold}}.dd-y{{color:var(--yellow);font-weight:bold}}.dd-r{{color:var(--red);font-weight:bold}}
.tabs{{display:flex;gap:0;margin-bottom:0;flex-wrap:wrap}}
.tab{{padding:8px 14px;background:var(--bg-card);border:1px solid var(--border);color:var(--text2);cursor:pointer;border-radius:8px 8px 0 0;font-size:0.88em}}
.tab.active{{background:var(--bg);color:var(--primary);border-bottom-color:var(--bg);font-weight:bold}}
.tab:hover{{color:var(--text)}}
.panel{{background:var(--bg);border:1px solid var(--border);border-top:none;border-radius:0 0 8px 8px;padding:16px}}
.panel.hidden{{display:none}}
.bar-cell{{min-width:80px}}
@media(max-width:768px){{body{{padding:8px;font-size:12px}}.tab{{padding:6px 10px;font-size:0.8em}}.filters{{flex-direction:column}}}}
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

<div style="display:flex;align-items:center;gap:10px"><h1>⏰ 時間統計</h1><button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()" title="切換亮/暗模式" style="width:36px;height:36px;border:1px solid var(--border);border-radius:50%;background:var(--bg-card);color:var(--text);font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0"></button></div>
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:0.82em;color:var(--text2)">
<span>{today} · {total_trades} 筆交易</span>
<span style="margin-left:4px">HKT (UTC+8)</span>
</div>

<div class="stats">
<div><div class="v">{total_trades}</div><div class="l">Total Trades</div></div>
<div><div class="v">{global_stats['win_pct']:.1f}%</div><div class="l">Win Rate</div></div>
<div><div class="v">{fmt_pnl(global_stats['total_pnl'])}</div><div class="l">Total P&L</div></div>
<div><div class="v">{global_stats['avg_hold']:.1f}h</div><div class="l">Avg Hold</div></div>
</div>

<div class="filters">
<span style="color:var(--text2);font-size:0.85em">Signal:</span>
<select id="sigSel" onchange="applyFilters()">{sig_opts}</select>
<span style="color:var(--text2);font-size:0.85em">CCY:</span>
<select id="symSel" onchange="applyFilters()">{sym_opts}</select>
</div>

<div class="tabs">
<div class="tab active" onclick="showPanel('day',this)">📅 Day</div>
<div class="tab" onclick="showPanel('week',this)">📆 Week</div>
<div class="tab" onclick="showPanel('month',this)">🗓 Month</div>
<div class="tab" onclick="showPanel('quarter',this)">📊 Quarter</div>
<div class="tab" onclick="showPanel('year',this)">📈 Year</div>
<div class="tab" onclick="showPanel('hour',this)">🕐 Hour</div>
<div class="tab" onclick="showPanel('magic',this)">🔮 Magic</div>
<div class="tab" onclick="showPanel('comment',this)">💬 Comment</div>
</div>

<!-- DAY -->
<div id="panel-day" class="panel">
<h2 style="color:var(--primary);font-size:1em;margin:0 0 12px">📅 按星期統計</h2>
<div class="container"><table id="tbl-day"><thead><tr>
<th data-col="0" data-type="str">Day<span class="arrow"></span></th>
<th data-col="1" data-type="num">Trades<span class="arrow"></span></th>
<th data-col="2" data-type="num">Win%<span class="arrow"></span></th>
<th data-col="3" data-type="num">Win% Bar<span class="arrow"></span></th>
<th data-col="4" data-type="num">Avg Pips<span class="arrow"></span></th>
<th data-col="5" data-type="num">Total P&L<span class="arrow"></span></th>
<th data-col="6" data-type="num">Avg Hold<span class="arrow"></span></th>
<th data-col="7" data-type="str">Best CCY<span class="arrow"></span></th>
<th data-col="8" data-type="str">Worst CCY<span class="arrow"></span></th>
</tr></thead><tbody>{day_rows}</tbody></table></div></div>

<!-- WEEK -->
<div id="panel-week" class="panel hidden">
<h2 style="color:var(--primary);font-size:1em;margin:0 0 12px">📆 按週統計（最近 12 週）</h2>
<div class="container"><table id="tbl-week"><thead><tr>
<th data-col="0" data-type="str">Week<span class="arrow"></span></th>
<th data-col="1" data-type="num">Trades<span class="arrow"></span></th>
<th data-col="2" data-type="num">Win%<span class="arrow"></span></th>
<th data-col="3" data-type="num">Total P&L<span class="arrow"></span></th>
<th data-col="4" data-type="num">Avg Hold<span class="arrow"></span></th>
</tr></thead><tbody>{week_rows}</tbody></table></div></div>

<!-- MONTH -->
<div id="panel-month" class="panel hidden">
<h2 style="color:var(--primary);font-size:1em;margin:0 0 12px">🗓 按月統計（最近 12 個月）</h2>
<div class="container"><table id="tbl-month"><thead><tr>
<th data-col="0" data-type="str">Month<span class="arrow"></span></th>
<th data-col="1" data-type="num">Trades<span class="arrow"></span></th>
<th data-col="2" data-type="num">Win%<span class="arrow"></span></th>
<th data-col="3" data-type="num">Total P&L<span class="arrow"></span></th>
<th data-col="4" data-type="num">Avg Hold<span class="arrow"></span></th>
</tr></thead><tbody>{month_rows}</tbody></table></div></div>

<!-- QUARTER -->
<div id="panel-quarter" class="panel hidden">
<h2 style="color:var(--primary);font-size:1em;margin:0 0 12px">📊 按季統計</h2>
<div class="container"><table id="tbl-quarter"><thead><tr>
<th data-col="0" data-type="str">Quarter<span class="arrow"></span></th>
<th data-col="1" data-type="num">Trades<span class="arrow"></span></th>
<th data-col="2" data-type="num">Win%<span class="arrow"></span></th>
<th data-col="3" data-type="num">Total P&L<span class="arrow"></span></th>
<th data-col="4" data-type="num">Avg Hold<span class="arrow"></span></th>
</tr></thead><tbody>{quarter_rows}</tbody></table></div></div>

<!-- YEAR -->
<div id="panel-year" class="panel hidden">
<h2 style="color:var(--primary);font-size:1em;margin:0 0 12px">📈 按年統計</h2>
<div class="container"><table id="tbl-year"><thead><tr>
<th data-col="0" data-type="str">Year<span class="arrow"></span></th>
<th data-col="1" data-type="num">Trades<span class="arrow"></span></th>
<th data-col="2" data-type="num">Win%<span class="arrow"></span></th>
<th data-col="3" data-type="num">Total P&L<span class="arrow"></span></th>
<th data-col="4" data-type="num">Avg Hold<span class="arrow"></span></th>
</tr></thead><tbody>{year_rows}</tbody></table></div></div>

<!-- HOUR -->
<div id="panel-hour" class="panel hidden">
<h2 style="color:var(--primary);font-size:1em;margin:0 0 12px">🕐 按小時統計（HKT）</h2>
<div class="container"><table id="tbl-hour"><thead><tr>
<th data-col="0" data-type="str">Hour<span class="arrow"></span></th>
<th data-col="1" data-type="num">Trades<span class="arrow"></span></th>
<th data-col="2" data-type="num">Count Bar<span class="arrow"></span></th>
<th data-col="3" data-type="num">Win%<span class="arrow"></span></th>
<th data-col="4" data-type="num">Avg Pips<span class="arrow"></span></th>
<th data-col="5" data-type="num">Total P&L<span class="arrow"></span></th>
</tr></thead><tbody>{hour_rows}</tbody></table></div></div>

<!-- MAGIC -->
<div id="panel-magic" class="panel hidden">
<h2 style="color:var(--primary);font-size:1em;margin:0 0 12px">🔮 Magic Number 統計</h2>
<div class="container"><table id="tbl-magic"><thead><tr>
<th data-col="0" data-type="str">Magic<span class="arrow"></span></th>
<th data-col="1" data-type="num">Trades<span class="arrow"></span></th>
<th data-col="2" data-type="num">Win%<span class="arrow"></span></th>
<th data-col="3" data-type="num">Total P&L<span class="arrow"></span></th>
<th data-col="4" data-type="num">Avg Hold<span class="arrow"></span></th>
</tr></thead><tbody>{magic_rows}</tbody></table></div></div>

<!-- COMMENT -->
<div id="panel-comment" class="panel hidden">
<h2 style="color:var(--primary);font-size:1em;margin:0 0 12px">💬 Comment 統計（Top 50）</h2>
<div class="container"><table id="tbl-comment"><thead><tr>
<th data-col="0" data-type="str">Comment<span class="arrow"></span></th>
<th data-col="1" data-type="num">Trades<span class="arrow"></span></th>
<th data-col="2" data-type="num">Win%<span class="arrow"></span></th>
<th data-col="3" data-type="num">Total P&L<span class="arrow"></span></th>
<th data-col="4" data-type="num">Avg Hold<span class="arrow"></span></th>
</tr></thead><tbody>{comment_rows}</tbody></table></div></div>

<script>
function applyFilters(){{
  /* Placeholder for client-side filtering - tables are static for now */
  var sig=document.getElementById('sigSel').value;
  var sym=document.getElementById('symSel').value;
  console.log('Filter:', sig, sym);
}}
</script>
</body></html>'''
    return html


def main():
    print("⏰ Generating Period Statistics...")
    all_trades, signal_ids, symbols = load_all_trades()
    print(f"  📊 Loaded {len(all_trades)} trades from {len(signal_ids)} signals")
    
    html = generate_html(all_trades, signal_ids, symbols)
    
    for out_dir in [OUTPUT_DIR, REPORTS_DIR, DOCS_DIR / 'admin']:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / 'period_stats.html'
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        size_kb = len(html.encode('utf-8')) / 1024
        print(f"  ✅ Written: {out_path} ({size_kb:.0f} KB)")


if __name__ == '__main__':
    main()
