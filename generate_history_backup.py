#!/usr/bin/env python3
"""
Generate History JSON Backup/Restore page for TSA.
Shows all saved analyses with export/import functionality.
"""
import json
import csv
import os
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
HISTORY_DIR = DATA_DIR / 'history'
DOWNLOADS_DIR = BASE_DIR / 'downloads'
OUTPUT_DIR = BASE_DIR / 'output'
DOCS_DIR = BASE_DIR / 'docs'
REPORTS_DIR = BASE_DIR / 'reports'

for d in [OUTPUT_DIR, DOCS_DIR, REPORTS_DIR, DOCS_DIR / 'admin', HISTORY_DIR]:
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

def get_ea_tag(sid):
    s = str(sid)
    for ea, ids in EA_MAP.items():
        if s in ids: return ea
    return 'UNK'

def get_ea_style(ea):
    bg, fg = EA_COLORS.get(ea, EA_COLORS['UNK'])
    return f'background:{bg};color:{fg}'


def backup_all_signals():
    """Export all CSV data as JSON backup files."""
    backups = []
    
    for f in sorted(DOWNLOADS_DIR.glob('*.csv')):
        fname = f.stem
        sid = fname.replace('forex-forest-signals-page-', '').replace('signal_', '')
        try: int(sid)
        except ValueError: continue
        
        ea = get_ea_tag(sid)
        trades = []
        
        try:
            with open(f, 'r', encoding='utf-8-sig') as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    trades.append(dict(row))
        except Exception as e:
            print(f"  ⚠️ Error reading {f.name}: {e}")
            continue
        
        if not trades:
            continue
        
        # Calculate summary stats
        total_pnl = sum(float(t.get('Net Profit', '0').replace(',', '') or '0') for t in trades)
        total_pips = sum(float(t.get('Net Pips', '0').replace(',', '') or '0') for t in trades)
        wins = sum(1 for t in trades if float(t.get('Net Pips', '0').replace(',', '') or '0') > 0)
        avg_hold = sum(float(t.get('Holding Time (Hours)', '0') or '0') for t in trades) / len(trades)
        
        symbols = list(set(t.get('Symbol', '') for t in trades if t.get('Symbol')))
        
        backup_data = {
            'signal_id': sid,
            'ea': ea,
            'backup_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'source_file': f.name,
            'trade_count': len(trades),
            'symbols': sorted(symbols),
            'summary': {
                'total_pnl': round(total_pnl, 2),
                'total_pips': round(total_pips, 1),
                'win_rate': round(wins / len(trades) * 100, 1) if trades else 0,
                'avg_hold_hours': round(avg_hold, 1),
            },
            'trades': trades,
        }
        
        # Write JSON backup
        json_path = HISTORY_DIR / f'signal_{sid}.json'
        with open(json_path, 'w', encoding='utf-8') as jf:
            json.dump(backup_data, jf, ensure_ascii=False, indent=2)
        
        backups.append({
            'signal_id': sid,
            'ea': ea,
            'trades': len(trades),
            'pnl': total_pnl,
            'pips': total_pips,
            'win_pct': wins / len(trades) * 100 if trades else 0,
            'avg_hold': avg_hold,
            'symbols': len(symbols),
            'file_size': json_path.stat().st_size,
            'backup_date': backup_data['backup_date'],
        })
    
    return backups


def generate_html(backups):
    today = datetime.now().strftime('%Y-%m-%d')
    n = len(backups)
    total_trades = sum(b['trades'] for b in backups)
    total_pnl = sum(b['pnl'] for b in backups)
    
    # Sort by P&L desc
    backups.sort(key=lambda x: -x['pnl'])
    
    rows = ''
    for i, b in enumerate(backups, 1):
        ea_style = get_ea_style(b['ea'])
        pnl_cls = 'dd-g' if b['pnl'] >= 0 else 'dd-r'
        fmt_pnl = f"+{b['pnl']:,.1f}" if b['pnl'] >= 0 else f"{b['pnl']:,.1f}"
        win_cls = 'dd-g' if b['win_pct'] >= 70 else ('dd-y' if b['win_pct'] >= 50 else 'dd-r')
        size_kb = b['file_size'] / 1024
        
        rows += f'''<tr>
<td>{i}</td>
<td><a href="https://signals.algoforest.com/signals/{b['signal_id']}">{b['signal_id']}</a></td>
<td><span style="{ea_style};padding:1px 6px;border-radius:3px;font-size:0.8em;font-weight:bold">{b['ea']}</span></td>
<td>{b['trades']}</td>
<td class="{win_cls}" data-val="{b['win_pct']}">{b['win_pct']:.1f}%</td>
<td class="{pnl_cls}" data-val="{b['pnl']}">{fmt_pnl}</td>
<td data-val="{b['pips']}">{b['pips']:.1f}</td>
<td>{b['avg_hold']:.1f}h</td>
<td>{b['symbols']}</td>
<td>{size_kb:.0f} KB</td>
<td>
<button onclick="downloadJSON('{b['signal_id']}')" style="padding:3px 8px;border:1px solid var(--border);border-radius:4px;background:var(--bg-card);color:var(--accent);cursor:pointer;font-size:0.8em">💾 下載</button>
</td>
</tr>'''
    
    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>💾 歷史備份</title>
<link rel="stylesheet" href="../sidebar.css">
<style>
:root{{--font-main:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Microsoft JhengHei',sans-serif}}
[data-theme="dark"]{{--bg:#0a0e17;--bg-card:#111520;--bg-hover:#1a1f2e;--text:#d0d0d0;--text2:#888;--primary:#FFD700;--accent:#64b5f6;--green:#4CAF50;--red:#FF5722;--yellow:#FFC107;--border:#1e2433;--th-bg:#111520}}
[data-theme="light"]{{--bg:#f5f7fa;--bg-card:#ffffff;--bg-hover:#eef2f7;--text:#333;--text2:#666;--primary:#0f3460;--accent:#e94560;--green:#28a745;--red:#dc3545;--yellow:#ffc107;--border:#ddd;--th-bg:#eef2f7}}
*{{transition:background-color .25s ease,color .25s ease,border-color .25s ease;margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--font-main);background:var(--bg);color:var(--text);padding:16px;max-width:1400px;margin:0 auto}}
h1{{font-size:1.3em;margin-bottom:4px;color:var(--primary)}}
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
.import-box{{background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:16px;margin-bottom:16px}}
.import-box h3{{color:var(--primary);font-size:0.95em;margin-bottom:8px}}
.import-box textarea{{width:100%;height:60px;background:var(--bg);border:1px solid var(--border);color:var(--text);border-radius:4px;padding:8px;font-family:monospace;font-size:0.85em}}
.import-box button{{margin-top:8px;padding:6px 14px;border:1px solid var(--primary);border-radius:4px;background:transparent;color:var(--primary);cursor:pointer;font-weight:bold}}
.import-box button:hover{{background:var(--primary);color:var(--bg)}}
@media(max-width:768px){{body{{padding:8px;font-size:12px}}}}
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
function downloadJSON(signalId){{
  /* For GitHub Pages, we can't serve dynamic JSON. Instead, open the raw file. */
  const url='https://raw.githubusercontent.com/alvin-forex/trade-strategy-analyzer/main/data/history/signal_'+signalId+'.json';
  window.open(url,'_blank');
}}
function importJSON(){{
  const ta=document.getElementById('importText');
  const status=document.getElementById('importStatus');
  try{{
    const data=JSON.parse(ta.value);
    if(!data.signal_id)throw new Error('Missing signal_id');
    status.textContent='✅ Valid JSON for signal '+data.signal_id+' ('+data.trade_count+' trades)';
    status.style.color='var(--green)';
    // Download as file
    const blob=new Blob([ta.value],{{type:'application/json'}});
    const url=URL.createObjectURL(blob);
    const a=document.createElement('a');
    a.href=url;a.download='signal_'+data.signal_id+'.json';
    a.click();
    URL.revokeObjectURL(url);
  }}catch(e){{
    status.textContent='❌ '+e.message;
    status.style.color='var(--red)';
  }}
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
    var va=getCellValue(a,colIdx,type);var vb=getCellValue(b,colIdx,type);
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

<div style="display:flex;align-items:center;gap:10px"><h1>💾 歷史備份</h1><button id="theme-toggle" onclick="toggleTheme()" title="切換亮/暗模式" style="width:36px;height:36px;border:1px solid var(--border);border-radius:50%;background:var(--bg-card);color:var(--text);font-size:18px;cursor:pointer;flex-shrink:0"></button></div>
<div class="sub">{today} · {n} 個 Signal 備份 · {total_trades} 筆交易</div>

<div class="stats">
<div><div class="v">{n}</div><div class="l">已備份 Signals</div></div>
<div><div class="v">{total_trades}</div><div class="l">總交易筆數</div></div>
<div><div class="v">{"+" if total_pnl>=0 else ""}{total_pnl:,.1f}</div><div class="l">總 P&L ($)</div></div>
</div>

<div class="import-box">
<h3>📥 還原備份</h3>
<p style="color:var(--text2);font-size:0.85em;margin-bottom:8px">貼上 JSON 內容以還原歷史分析數據</p>
<textarea id="importText" placeholder='貼上 signal JSON 內容...'></textarea>
<button onclick="importJSON()">📥 還原</button>
<span id="importStatus" style="margin-left:10px;font-size:0.85em"></span>
</div>

<div class="container"><table id="tbl-history"><thead><tr>
<th data-col="0" data-type="num">#</th>
<th data-col="1" data-type="num">Signal</th>
<th data-col="2" data-type="str">EA</th>
<th data-col="3" data-type="num">Trades</th>
<th data-col="4" data-type="num">Win%</th>
<th data-col="5" data-type="num">Total P&L</th>
<th data-col="6" data-type="num">Total Pips</th>
<th data-col="7" data-type="num">Avg Hold</th>
<th data-col="8" data-type="num">CCY</th>
<th data-col="9" data-type="num">Size</th>
<th data-col="10" data-type="str">Action</th>
</tr></thead><tbody>{rows}</tbody></table></div>

</body></html>'''
    return html


def main():
    print("💾 Generating History Backup...")
    
    # 1. Backup all signals to JSON
    backups = backup_all_signals()
    print(f"  📦 Backed up {len(backups)} signals to {HISTORY_DIR}")
    
    # 2. Generate HTML page
    html = generate_html(backups)
    
    for out_dir in [OUTPUT_DIR, REPORTS_DIR, DOCS_DIR / 'admin']:
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / 'history.html'
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(html)
        size_kb = len(html.encode('utf-8')) / 1024
        print(f"  ✅ Written: {out_path} ({size_kb:.0f} KB)")


if __name__ == '__main__':
    main()
