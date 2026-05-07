#!/usr/bin/env python3
"""
Generate Version Comparison HTML
- Pick a symbol → pick a signal → see all versions side by side
- Compare scores, ratings, key metrics between versions
- Highlight improvements / regressions
"""
import sys
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent / 'scripts'))

from version_tracker import (get_connection, init_tables, get_symbols,
                              get_rankings_for_symbol, get_version_comparison,
                              get_version_summary)

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)


def get_ea_full(ea_type):
    names = {
        'DW': 'DragonWare', 'SMA': 'SMA_EA', 'MKD': 'MKD_Scalper',
        'S10': 'S10_Strategy', 'Flash': 'Flash_Scalper', 'GEM': 'GEM_Trader',
        'UNK': 'Unknown',
    }
    return names.get(ea_type, ea_type)


def delta_arrow(current, previous):
    """Return colored arrow indicator for comparison."""
    if current is None or previous is None:
        return ''
    diff = current - previous
    if diff > 2:
        return f'<span style="color:#4CAF50">▲ +{diff:.1f}</span>'
    elif diff < -2:
        return f'<span style="color:#FF5722">▼ {diff:.1f}</span>'
    else:
        return f'<span style="color:#666">● ±{diff:.1f}</span>'


def generate_comparison_html():
    """Generate version comparison HTML page."""
    conn = get_connection()
    init_tables(conn)
    
    symbols = get_symbols(conn)
    versions = get_version_summary(conn)
    
    if not symbols:
        print("⚠️ No data in symbol_rankings table. Run generate_symbol_ranking.py first.")
        conn.close()
        return None
    
    # Build JSON data for JS
    symbol_data = {}
    for s in symbols:
        sym = s['symbol']
        rankings = get_rankings_for_symbol(conn, sym)
        
        # Group by signal_id → versions
        by_signal = defaultdict(list)
        for r in rankings:
            by_signal[r['signal_id']].append(r)
        
        symbol_data[sym] = {
            'signal_count': s['signal_count'],
            'signals': {}
        }
        
        for sig_id, versions_list in by_signal.items():
            symbol_data[sym]['signals'][sig_id] = [
                {
                    'version': v['strategy_version'],
                    'date': v['analysis_date'],
                    'score': v['avg_score'],
                    'star4_pct': v['star4_pct'],
                    'trades': v['trades'],
                    'win_rate': v['win_rate'],
                    'pf': v['profit_factor'],
                    'profit': v['total_profit'],
                    'tf': v['timeframe'],
                    'ea': get_ea_full(v['ea_type']),
                    'ea_short': v['ea_type'],
                    'layers': v['layers'],
                    'dd': v['eq_max_dd'],
                }
                for v in versions_list
            ]
    
    conn.close()
    
    json_data = json.dumps(symbol_data, ensure_ascii=False)
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Version Comparison - DDE v3 Copy Strategy</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#0a0e17;color:#d0d0d0;padding:12px;font-size:13px}}
h1{{font-size:1.2em;margin-bottom:2px;color:#FFD700}}
.sub{{color:#666;font-size:0.85em;margin-bottom:12px}}
.controls{{background:#111520;border:1px solid #1e2433;border-radius:6px;padding:10px 14px;margin-bottom:12px;display:flex;flex-wrap:wrap;gap:12px;align-items:center}}
.controls label{{color:#999;font-size:0.85em}}
.controls select{{background:#1a1f2e;color:#d0d0d0;border:1px solid #2a3040;border-radius:4px;padding:6px 10px;font-size:0.9em;min-width:150px}}
.controls select:focus{{outline:none;border-color:#FFD700}}
.controls .info{{color:#666;font-size:0.8em;margin-left:auto}}
table{{width:100%;border-collapse:collapse;margin-bottom:16px}}
th{{background:#111520;padding:8px 10px;text-align:left;border-bottom:2px solid #FFD700;color:#FFD700;font-size:0.8em;white-space:nowrap}}
td{{padding:6px 10px;text-align:left;border-bottom:1px solid #1a1f2e}}
tr:hover{{background:#111520}}
tr.top1{{background:rgba(255,215,0,0.03)}}
.sig{{color:#64b5f6;font-weight:bold}}
.s90{{color:#4CAF50;font-weight:bold}}.s80{{color:#8BC34A;font-weight:bold}}.s70{{color:#FFC107;font-weight:bold}}.s0{{color:#FF5722;font-weight:bold}}
.g{{color:#4CAF50}}.r{{color:#FF5722}}
.m{{font-family:'SF Mono',Consolas,monospace;font-size:0.9em}}
.tf{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:0.8em;background:#1a237e;color:#90caf9}}
.ea-tag{{display:inline-block;padding:1px 5px;border-radius:3px;font-size:0.72em;font-weight:bold}}
.ea-DW{{background:#4a148c;color:#ce93d8}}.ea-SMA{{background:#1b5e20;color:#a5d6a7}}.ea-MKD{{background:#e65100;color:#ffcc80}}
.ea-S10{{background:#0d47a1;color:#90caf9}}.ea-Flash{{background:#880e4f;color:#f48fb1}}.ea-GEM{{background:#37474f;color:#b0bec5}}
.ea-UNK{{background:#37474f;color:#b0bec5}}
.dd-g{{color:#4CAF50}}.dd-y{{color:#FFC107}}.dd-r{{color:#FF5722}}
.improved{{background:rgba(76,175,80,0.08)}}.regressed{{background:rgba(255,87,34,0.08)}}
.ver-badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:0.75em;font-weight:bold;margin-right:4px}}
.ver-v1{{background:#1b5e20;color:#a5d6a7}}.ver-v2{{background:#e65100;color:#ffcc80}}.ver-v3{{background:#4a148c;color:#ce93d8}}
.delta{{font-size:0.8em;margin-left:6px}}
.card{{background:#111520;border:1px solid #1e2433;border-radius:6px;padding:12px 16px;margin-bottom:16px}}
.card h3{{color:#FFD700;font-size:1em;margin-bottom:8px}}
.empty{{color:#555;font-style:italic;text-align:center;padding:40px}}
@media(max-width:768px){{body{{font-size:11px}}th,td{{padding:3px 5px}}}}
</style>
</head>
<body>
<h1>📊 Version Comparison — DDE v3 Copy Strategy</h1>
<div class="sub">Compare signal performance across strategy versions | {now}</div>

<div class="controls">
<label>💱 貨幣對:</label>
<select id="symSelect" onchange="onSymbolChange()">
<option value="">— 選擇貨幣對 —</option>
</select>
<label>📡 Signal:</label>
<select id="sigSelect" onchange="onSignalChange()">
<option value="">— 選擇 Signal —</option>
</select>
<button onclick="showAllSignals()" style="background:#1a237e;color:#90caf9;border:1px solid #283593;border-radius:4px;padding:6px 14px;cursor:pointer;font-size:0.85em">📋 全部 Signals</button>
<span class="info" id="statusInfo"></span>
</div>

<div id="content">
<div class="empty">👆 選擇貨幣對開始分析</div>
</div>

<script>
var DATA = {json_data};

// Populate symbol selector
var symSel = document.getElementById('symSelect');
var syms = Object.keys(DATA).sort(function(a,b){{ return DATA[b].signal_count - DATA[a].signal_count; }});
syms.forEach(function(s) {{
    var o = document.createElement('option');
    o.value = s;
    o.textContent = s + ' (' + DATA[s].signal_count + ' signals)';
    symSel.appendChild(o);
}});

function onSymbolChange() {{
    var sym = symSel.value;
    var sigSel = document.getElementById('sigSelect');
    sigSel.innerHTML = '<option value="">— 選擇 Signal —</option>';
    
    if (!sym || !DATA[sym]) {{
        document.getElementById('content').innerHTML = '<div class="empty">👆 選擇貨幣對開始分析</div>';
        return;
    }}
    
    var signals = DATA[sym].signals;
    var sigIds = Object.keys(signals).sort(function(a,b) {{
        var bestA = signals[a].reduce(function(mx,v){{ return Math.max(mx,v.score); }}, 0);
        var bestB = signals[b].reduce(function(mx,v){{ return Math.max(mx,v.score); }}, 0);
        return bestB - bestA;
    }});
    
    sigIds.forEach(function(sid) {{
        var o = document.createElement('option');
        o.value = sid;
        var best = signals[sid].reduce(function(mx,v){{ return Math.max(mx,v.score); }}, 0);
        o.textContent = 'Signal ' + sid + ' (best: ' + best + ')';
        sigSel.appendChild(o);
    }});
    
    showAllSignals();
}}

function onSignalChange() {{
    var sym = symSel.value;
    var sig = document.getElementById('sigSelect').value;
    if (!sym || !sig) return;
    showSignalDetail(sym, sig);
}}

function scoreClass(s) {{
    if (s >= 90) return 's90';
    if (s >= 80) return 's80';
    if (s >= 70) return 's70';
    return 's0';
}}

function ddClass(d) {{
    var a = Math.abs(d);
    if (a < 5000) return 'dd-g';
    if (a < 20000) return 'dd-y';
    return 'dd-r';
}}

function eaClass(e) {{
    return 'ea-' + (e || 'UNK');
}}

function verClass(v) {{
    return 'ver-' + (v || 'v1');
}}

function showSignalDetail(sym, sig) {{
    var versions = DATA[sym].signals[sig];
    if (!versions || versions.length === 0) return;
    
    var html = '<div class="card"><h3>💱 ' + sym + ' × Signal ' + sig + ' — Version History</h3>';
    html += '<table><thead><tr><th>Version</th><th>Date</th><th>Score</th><th>Δ</th><th>⭐⭐⭐⭐%</th><th>Trades</th><th>Win%</th><th>PF</th><th>Profit</th><th>TF</th><th>EA</th><th>LV</th><th>Eq Max DD</th></tr></thead><tbody>';
    
    versions.sort(function(a,b){{ return a.version.localeCompare(b.version); }});
    
    for (var i = 0; i < versions.length; i++) {{
        var v = versions[i];
        var pf = v.pf > 999 ? 'Inf' : v.pf.toFixed(1);
        var profitCls = v.profit >= 0 ? 'g' : 'r';
        var ddC = ddClass(v.dd);
        var scC = scoreClass(v.score);
        var delta = '';
        if (i > 0) {{
            var diff = v.score - versions[i-1].score;
            if (diff > 2) delta = '<span class="delta" style="color:#4CAF50">▲+' + diff.toFixed(1) + '</span>';
            else if (diff < -2) delta = '<span class="delta" style="color:#FF5722">▼' + diff.toFixed(1) + '</span>';
            else delta = '<span class="delta" style="color:#666">●</span>';
        }}
        
        html += '<tr class="' + (i===0 ? '' : '') + '">';
        html += '<td><span class="ver-badge ' + verClass(v.version) + '">' + v.version + '</span></td>';
        html += '<td>' + v.date + '</td>';
        html += '<td class="' + scC + '">' + v.score + '</td>';
        html += '<td>' + delta + '</td>';
        html += '<td>' + v.star4_pct + '%</td>';
        html += '<td>' + v.trades.toLocaleString() + '</td>';
        html += '<td>' + v.win_rate.toFixed(1) + '%</td>';
        html += '<td>' + pf + '</td>';
        html += '<td class="' + profitCls + '">$' + v.profit.toLocaleString('en-US',{{maximumFractionDigits:0}}) + '</td>';
        html += '<td><span class="tf">' + v.tf + '</span></td>';
        html += '<td><span class="ea-tag ' + eaClass(v.ea_short) + '">' + v.ea + '</span></td>';
        html += '<td class="m">' + v.layers + '</td>';
        html += '<td class="m ' + ddC + '">$' + v.dd.toLocaleString('en-US',{{maximumFractionDigits:0}}) + '</td>';
        html += '</tr>';
    }}
    
    html += '</tbody></table></div>';
    
    document.getElementById('content').innerHTML = html;
    document.getElementById('statusInfo').textContent = sym + ' × Signal ' + sig + ' — ' + versions.length + ' version(s)';
}}

function showAllSignals() {{
    var sym = symSel.value;
    if (!sym || !DATA[sym]) {{
        document.getElementById('content').innerHTML = '<div class="empty">👆 選擇貨幣對開始分析</div>';
        return;
    }}
    
    var signals = DATA[sym].signals;
    var sigIds = Object.keys(signals).sort(function(a,b) {{
        var bestA = signals[a].reduce(function(mx,v){{ return Math.max(mx,v.score); }}, 0);
        var bestB = signals[b].reduce(function(mx,v){{ return Math.max(mx,v.score); }}, 0);
        return bestB - bestA;
    }});
    
    var html = '<div class="card"><h3>💱 ' + sym + ' — All Signals (Best Version)</h3>';
    html += '<table><thead><tr><th>#</th><th>Signal</th><th>Best Score</th><th>Versions</th><th>⭐⭐⭐⭐%</th><th>Trades</th><th>Win%</th><th>PF</th><th>Profit</th><th>TF</th><th>EA</th><th>LV</th><th>Eq Max DD</th></tr></thead><tbody>';
    
    for (var i = 0; i < sigIds.length; i++) {{
        var sid = sigIds[i];
        var vers = signals[sid];
        // Use best version
        var best = vers.reduce(function(b,v){{ return v.score > b.score ? v : b; }}, vers[0]);
        var pf = best.pf > 999 ? 'Inf' : best.pf.toFixed(1);
        var profitCls = best.profit >= 0 ? 'g' : 'r';
        var ddC = ddClass(best.dd);
        var scC = scoreClass(best.score);
        var rank = i < 3 ? ['🥇','🥈','🥉'][i] : (i+1);
        var rowCls = i < 3 ? ' class="top1"' : '';
        
        html += '<tr' + rowCls + '>';
        html += '<td>' + rank + '</td>';
        html += '<td class="sig">' + sid + '</td>';
        html += '<td class="' + scC + '">' + best.score + '</td>';
        html += '<td>' + vers.map(function(v){{ return '<span class="ver-badge ' + verClass(v.version) + '">' + v.version + '</span>'; }}).join(' ') + '</td>';
        html += '<td>' + best.star4_pct + '%</td>';
        html += '<td>' + best.trades.toLocaleString() + '</td>';
        html += '<td>' + best.win_rate.toFixed(1) + '%</td>';
        html += '<td>' + pf + '</td>';
        html += '<td class="' + profitCls + '">$' + best.profit.toLocaleString('en-US',{{maximumFractionDigits:0}}) + '</td>';
        html += '<td><span class="tf">' + best.tf + '</span></td>';
        html += '<td><span class="ea-tag ' + eaClass(best.ea_short) + '">' + best.ea + '</span></td>';
        html += '<td class="m">' + best.layers + '</td>';
        html += '<td class="m ' + ddC + '">$' + best.dd.toLocaleString('en-US',{{maximumFractionDigits:0}}) + '</td>';
        html += '</tr>';
    }}
    
    html += '</tbody></table></div>';
    
    document.getElementById('content').innerHTML = html;
    document.getElementById('statusInfo').textContent = sym + ' — ' + sigIds.length + ' signals';
}}

</script>
</body></html>'''
    
    output_path = OUTPUT_DIR / 'version_comparison.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✅ Version comparison: {output_path} ({len(html):,} bytes)")
    return str(output_path)


if __name__ == '__main__':
    path = generate_comparison_html()
    if path:
        print(f"📄 Open: file://{path}")
