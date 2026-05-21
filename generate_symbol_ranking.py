#!/usr/bin/env python3
"""
Generate Symbol-based Signal Ranking HTML (DDE v3 Copy Strategy)
- Symbol-centric: user selects a currency pair, sees all signals ranked by performance ON THAT PAIR
- Each row = 1 Signal × 1 Symbol
- Stores results in SQLite via version_tracker for historical comparison
"""
import sys
import os
import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent))

from generate_all_levels_from_csv import analyze_trades_from_csv, analyze_by_levels
from version_tracker import (get_connection, init_tables, upsert_ranking,
                              get_symbols, get_rankings_for_symbol,
                              get_version_summary)

BASE_DIR = Path(__file__).parent
SAMPLES_DIR = BASE_DIR / 'samples'
OUTPUT_DIR = BASE_DIR / 'output'
OUTPUT_DIR.mkdir(exist_ok=True)

LEVEL_RANGES = {
    'L1': (0, 50),
    'L2': (50, 100),
    'L3': (100, 150),
    'L4': (150, 200), 'L5': (200, 250), 'L6': (250, 300), 'L7': (300, 350), 'L8': (350, 400), 'L9+': (400, float('inf'))
}

# EA type mapping (from generate_signal_ranking.py)
EA_MAP = {
    'DW': ['10437','11984','13790','17547','21698','22200','22278','25830','30359','31781','32719','3291','33101','31593','34574','36338','36397','36511','34259','20846','16538'],
    'SMA': ['106','1980','2351','32278','32541','5001','5275','537','5566','11889','13863','14724','16596','16698','16706','17611','17823','10864','14158'],
    'MKD': ['12962','13461','14341','14592','1470','17962','20805','23617','25668','25260','8325','7919'],
    'S10': ['13798','16596'],
    'Flash': ['19849'],
    'GEM': ['14581'],
}

EA_FULL_NAMES = {
    'DW': 'DragonWare',
    'SMA': 'SMA_EA',
    'MKD': 'MKD_Scalper',
    'S10': 'S10_Strategy',
    'Flash': 'Flash_Scalper',
    'GEM': 'GEM_Trader',
    'UNK': 'Unknown',
}

def get_ea_type(signal_id):
    for ea_type, signals in EA_MAP.items():
        if signal_id in signals:
            return ea_type
    return 'UNK'

def get_ea_full_name(ea_type):
    return EA_FULL_NAMES.get(ea_type, ea_type)

def get_layer_info(avg_layers):
    if avg_layers == 0:
        return '0LV'
    return f'{int(round(avg_layers))}LV'

def get_dd_class(dd_value):
    """Pip-based DD thresholds: 500 / 2000 pips"""
    abs_dd = abs(dd_value)
    if abs_dd < 500:
        return 'dd-g'
    elif abs_dd < 2000:
        return 'dd-y'
    else:
        return 'dd-r'

def get_score_class(score):
    if score >= 90:
        return 's90'
    elif score >= 80:
        return 's80'
    elif score >= 70:
        return 's70'
    elif score >= 60:
        return 's60'
    else:
        return 's0'

def compute_symbol_score(signal_id, symbol_trades):
    """
    Compute DDE v3 score for a specific signal × symbol combination.
    Per-level analysis using CoP + CoL.
    Returns avg of all non-zero weighted_scores.
    """
    lr = analyze_by_levels(symbol_trades, LEVEL_RANGES)

    all_scores = []
    star4 = 0
    breakdown = {'trigger': [], 'alpha': [], 'dde': []}

    for level_name, ld in lr.items():
        if ld.get('stats', {}).get('count', 0) == 0:
            continue
        for strategy in ['copy_on_profit', 'copy_on_lose']:
            sdata = ld.get(strategy, {})
            for wp, wp_data in sdata.items():
                score = wp_data.get('weighted_score', 0)
                rating = wp_data.get('rating', '')
                if score > 0:
                    all_scores.append(score)
                    if '⭐⭐⭐⭐' in rating:
                        star4 += 1
                    # Collect breakdown
                    sd = wp_data.get('score_details', {})
                    if isinstance(sd, dict):
                        breakdown['trigger'].append(sd.get('trigger_rate', ''))
                        breakdown['alpha'].append(sd.get('alpha_profit', ''))
                        breakdown['dde'].append(sd.get('dde', ''))

    if not all_scores:
        return None

    avg_score = round(sum(all_scores) / len(all_scores), 1)

    return {
        'avg_score': avg_score,
        'star4_count': star4,
        'cmp_total': len(all_scores),
        'star4_pct': round(star4 / len(all_scores) * 100),
        'breakdown': breakdown,
    }


def compute_all_rankings(strategy_version='v1'):
    """Compute symbol-based rankings for all signals."""
    batch_data_path = OUTPUT_DIR / 'batch_analysis_results.json'
    if not batch_data_path.exists():
        print("❌ batch_analysis_results.json not found")
        return {}

    with open(batch_data_path) as f:
        batch_data = json.load(f)

    batch_lookup = {str(r['signal_id']): r for r in batch_data}
    batch_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')

    # symbol -> [ranking_records]
    symbol_rankings = defaultdict(list)
    all_results = []

    seen_ids = set()
    total = len(batch_data)

    for i, rec in enumerate(batch_data):
        sid = str(rec['signal_id'])
        if sid in seen_ids:
            continue
        seen_ids.add(sid)

        print(f"[{i+1}/{total}] Signal {sid}...", end=' ', flush=True)

        # Find CSV
        csv_path = None
        for pattern in [f'forex-forest-signals-page-{sid}.csv', f'forex-forest-signals-page-{sid} (2).csv']:
            p = SAMPLES_DIR / pattern
            if p.exists():
                csv_path = p
                break

        if not csv_path:
            print("NO CSV")
            continue

        # Parse trades
        trades = analyze_trades_from_csv(str(csv_path))
        if not trades:
            print("NO TRADES")
            continue

        # Group by symbol
        by_symbol = defaultdict(list)
        for t in trades:
            sym = t.get('symbol', t.get('currency', 'UNKNOWN'))
            by_symbol[sym].append(t)

        ea_type = get_ea_type(sid)
        tf = rec.get('timeframe', '')
        layers = get_layer_info(rec.get('avg_layers', 0))
        sym_count = len(by_symbol)
        scored = 0

        for sym, sym_trades in by_symbol.items():
            score_data = compute_symbol_score(sid, sym_trades)
            if not score_data:
                continue

            scored += 1

            # Per-symbol stats
            sym_wins = sum(1 for t in sym_trades if t.get('net_pips', 0) > 0)
            sym_win_rate = (sym_wins / len(sym_trades) * 100) if sym_trades else 0
            sym_profit = sum(t.get('net_pips', 0) for t in sym_trades)
            sym_losses = [t.get('net_pips', 0) for t in sym_trades if t.get('net_pips', 0) < 0]
            sym_wins_list = [t.get('net_pips', 0) for t in sym_trades if t.get('net_pips', 0) > 0]
            total_wins = sum(sym_wins_list)
            total_losses = abs(sum(sym_losses))
            sym_pf = (total_wins / total_losses) if total_losses > 0 else (999.0 if total_wins > 0 else 0)

            # Max DD for this symbol's trades
            running = 0
            peak = 0
            sym_dd = 0
            for t in sorted(sym_trades, key=lambda x: x.get('close_time', '')):
                running += t.get('net_pips', 0)
                if running > peak:
                    peak = running
                dd = running - peak
                if dd < sym_dd:
                    sym_dd = dd

            record = {
                'signal_id': sid,
                'symbol': sym,
                'strategy_version': strategy_version,
                'analysis_date': datetime.now().strftime('%Y-%m-%d'),
                'avg_score': score_data['avg_score'],
                'star4_count': score_data['star4_count'],
                'star4_pct': score_data['star4_pct'],
                'total_comparisons': score_data['cmp_total'],
                'trades': len(sym_trades),
                'win_rate': round(sym_win_rate, 1),
                'profit_factor': round(sym_pf, 1),
                'total_profit': round(sym_profit, 0),
                'timeframe': tf,
                'ea_type': ea_type,
                'ea_full': get_ea_full_name(ea_type),
                'layers': layers,
                'eq_max_dd': round(sym_dd, 0),
                'score_breakdown': score_data['breakdown'],
                'batch_run_id': batch_run_id,
            }

            symbol_rankings[sym].append(record)
            all_results.append(record)

        print(f"{sym_count} symbols, {scored} scored")

    return symbol_rankings, all_results, batch_run_id


def save_to_db(all_results, strategy_version='v1'):
    """Save all ranking results to SQLite."""
    conn = get_connection()
    init_tables(conn)

    for r in all_results:
        upsert_ranking(
            conn=conn,
            signal_id=r['signal_id'],
            symbol=r['symbol'],
            strategy_version=r['strategy_version'],
            analysis_date=r['analysis_date'],
            avg_score=r['avg_score'],
            star4_count=r['star4_count'],
            star4_pct=r['star4_pct'],
            total_comparisons=r['total_comparisons'],
            trades=r['trades'],
            win_rate=r['win_rate'],
            profit_factor=r['profit_factor'],
            total_profit=r['total_profit'],
            timeframe=r['timeframe'],
            ea_type=r['ea_type'],
            layers=r['layers'],
            eq_max_dd=r['eq_max_dd'],
            score_breakdown=r['score_breakdown'],
            batch_run_id=r['batch_run_id'],
        )

    conn.close()
    print(f"✅ Saved {len(all_results)} records to DB (version={strategy_version})")


def generate_html(symbol_rankings):
    """Generate the symbol-based ranking HTML with dropdown selector."""

    # Sort symbols by number of signals descending
    sorted_symbols = sorted(symbol_rankings.keys(),
                           key=lambda s: len(symbol_rankings[s]), reverse=True)

    # Global stats
    total_records = sum(len(v) for v in symbol_rankings.values())
    total_signals = len(set(r['signal_id'] for v in symbol_rankings.values() for r in v))

    all_scores = [r['avg_score'] for v in symbol_rankings.values() for r in v]
    global_avg = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0
    global_best = max(all_scores) if all_scores else 0
    global_worst = min(all_scores) if all_scores else 0

    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Symbol Ranking - DDE v3 Copy Strategy</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#0a0e17;color:#d0d0d0;padding:12px;font-size:13px}}
h1{{font-size:1.2em;margin-bottom:2px;color:#FFD700}}
.sub{{color:#666;font-size:0.85em;margin-bottom:12px}}
.controls{{background:#111520;border:1px solid #1e2433;border-radius:6px;padding:10px 14px;margin-bottom:12px;display:flex;flex-wrap:wrap;gap:12px;align-items:center}}
.controls label{{color:#999;font-size:0.85em}}
.controls select{{background:#1a1f2e;color:#d0d0d0;border:1px solid #2a3040;border-radius:4px;padding:6px 10px;font-size:0.9em;min-width:150px}}
.controls select:focus{{outline:none;border-color:#FFD700}}
.controls .btn{{background:#1a237e;color:#90caf9;border:1px solid #283593;border-radius:4px;padding:6px 14px;cursor:pointer;font-size:0.85em}}
.controls .btn:hover{{background:#283593}}
.controls .info{{color:#666;font-size:0.8em;margin-left:auto}}
.sum{{background:#111520;border:1px solid #1e2433;border-radius:6px;padding:10px 14px;margin-bottom:12px;display:flex;flex-wrap:wrap;gap:20px}}
.sum .v{{font-size:1.3em;font-weight:bold;color:#FFD700}}
.sum .l{{font-size:0.7em;color:#666}}
.sym-header{{font-size:1.1em;color:#FFD700;margin:16px 0 8px;padding:6px 10px;background:#111520;border-left:3px solid #FFD700;border-radius:0 4px 4px 0}}
.sym-count{{color:#666;font-size:0.8em;margin-left:8px}}
table{{width:100%;min-width:900px;border-collapse:collapse;margin-bottom:8px}}
th{{background:#111520;padding:6px 8px;text-align:left;border-bottom:2px solid #FFD700;color:#FFD700;font-size:0.8em;white-space:nowrap}}
td{{padding:5px 8px;text-align:left;border-bottom:1px solid #1a1f2e}}
tr:hover{{background:#111520}}
tr.top3{{background:rgba(255,215,0,0.03)}}
.sig{{color:#64b5f6;font-weight:bold}}
.s90{{color:#4CAF50;font-weight:bold}}.s80{{color:#8BC34A;font-weight:bold}}.s70{{color:#FFC107;font-weight:bold}}.s60{{color:#FF9800;font-weight:bold}}.s0{{color:#FF5722;font-weight:bold}}
.p4{{color:#4CAF50}}
.g{{color:#4CAF50}}.r{{color:#FF5722}}
.m{{font-family:'SF Mono',Consolas,monospace;font-size:0.9em}}
.tf{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:0.8em;background:#1a237e;color:#90caf9}}
.ea-tag{{display:inline-block;padding:1px 5px;border-radius:3px;font-size:0.72em;font-weight:bold}}
.ea-DW{{background:#4a148c;color:#ce93d8}}.ea-SMA{{background:#1b5e20;color:#a5d6a7}}.ea-MKD{{background:#e65100;color:#ffcc80}}
.ea-S10{{background:#0d47a1;color:#90caf9}}.ea-Flash{{background:#880e4f;color:#f48fb1}}.ea-GEM{{background:#37474f;color:#b0bec5}}
.ea-UNK{{background:#37474f;color:#b0bec5}}
.dd-g{{color:#4CAF50}}.dd-y{{color:#FFC107}}.dd-r{{color:#FF5722}}
.no-data{{color:#555;font-style:italic;padding:20px;text-align:center}}
@media(max-width:768px){{body{{font-size:11px}}th,td{{padding:3px 5px}}}}
.hidden{{display:none}}
</style>
</head>
<body>
<div class="topnav" style="display:flex;align-items:center;gap:12px;padding:10px 16px;background:#111520;border-bottom:1px solid #1e2433;margin-bottom:16px;position:sticky;top:0;z-index:100">
  <a href="../index.html" style="font-weight:700;font-size:1em;color:#FFD700;text-decoration:none;margin-right:auto">🦀 TSA</a>
  <div style="display:flex;gap:10px;flex-wrap:wrap">
    <a href="../signal_ranking.html" style="color:#666;text-decoration:none;font-size:.88em;font-weight:600;padding:4px 10px;border-radius:6px">🏆 Signal 排名</a>
    <a href="./ccy_ranking.html" style="color:#666;text-decoration:none;font-size:.88em;font-weight:600;padding:4px 10px;border-radius:6px">💱 CCY 排名</a>
    <a href="./symbol_ranking.html" style="color:#FFD700;text-decoration:none;font-size:.88em;font-weight:600;padding:4px 10px;border-radius:6px;background:#1a1f2e">📊 波幅波</a>
  </div>
</div>
<h1>📊 Symbol Ranking - DDE v3 Copy Strategy</h1>
<div class="sub">Trigger 40% + Alpha Capture 40% + DDE 20% | {total_signals} signals × {len(sorted_symbols)} symbols | {total_records} pairs | {now}</div>

<div class="controls">
<label for="symSelect">💱 貨幣對:</label>
<select id="symSelect" onchange="filterSymbol()">
<option value="__ALL__">- 所有貨幣對 (Top 10) -</option>
'''

    for sym in sorted_symbols:
        cnt = len(symbol_rankings[sym])
        html += f'<option value="{sym}">{sym} ({cnt} signals)</option>\n'

    html += '''</select>
<label for="versionSelect">📋 版本:</label>
<select id="versionSelect" onchange="filterSymbol()">
<option value="v1">v1</option>
</select>
<button class="btn" onclick="exportCSV()">📥 Export</button>
<span class="info" id="filterInfo"></span>
</div>

<div class="sum">
<div><div class="v">''' + str(total_signals) + '''</div><div class="l">Signals</div></div>
<div><div class="v">''' + str(len(sorted_symbols)) + '''</div><div class="l">Symbols</div></div>
<div><div class="v">''' + str(total_records) + '''</div><div class="l">Signal×Symbol</div></div>
<div><div class="v">''' + f'{global_avg}' + '''</div><div class="l">Avg Score</div></div>
<div><div class="v">''' + f'{global_best}' + '''</div><div class="l">Best</div></div>
</div>

<div id="tableContainer">
'''

    # Generate tables for top 10 symbols initially visible
    top10 = sorted_symbols[:10]
    for sym in top10:
        rankings = sorted(symbol_rankings[sym], key=lambda x: x['avg_score'], reverse=True)
        html += generate_symbol_table(sym, rankings)

    # Hidden tables for remaining symbols
    for sym in sorted_symbols[10:]:
        rankings = sorted(symbol_rankings[sym], key=lambda x: x['avg_score'], reverse=True)
        html += f'<div class="sym-section hidden" data-symbol="{sym}">'
        html += generate_symbol_table(sym, rankings)
        html += '</div>\n'

    html += '''</div>

<script>
function filterSymbol() {
    var sym = document.getElementById('symSelect').value;
    var sections = document.querySelectorAll('.sym-section');
    var info = document.getElementById('filterInfo');

    sections.forEach(function(s) {
        if (sym === '__ALL__') {
            // Show only top 10
            var allSyms = sections;
            var shown = 0;
            allSyms.forEach(function(ss, idx) {
                if (idx < 10) {
                    ss.classList.remove('hidden');
                    shown++;
                } else {
                    ss.classList.add('hidden');
                }
            });
            info.textContent = '';
        } else {
            if (s.dataset.symbol === sym) {
                s.classList.remove('hidden');
                info.textContent = s.dataset.symbol + ' - ' + s.querySelectorAll('tbody tr').length + ' signals';
            } else {
                s.classList.add('hidden');
            }
        }
    });
}

function exportCSV() {
    var sym = document.getElementById('symSelect').value;
    var visible = document.querySelectorAll('.sym-section:not(.hidden)');
    var csv = 'Rank,Signal,Symbol,Avg Score,⭐⭐⭐⭐,⭐⭐⭐⭐%,Trades,Win%,PF,Profit,TF,EA,LV,Eq Max DD\\n';
    visible.forEach(function(s) {
        var rows = s.querySelectorAll('tbody tr');
        rows.forEach(function(row, idx) {
            var cells = row.querySelectorAll('td');
            if (cells.length > 3) {
                csv += (idx+1) + ',' + cells[1].textContent.trim() + ',' + cells[2].textContent.trim() + ',';
                csv += cells[3].textContent.trim() + ',' + cells[4].textContent.trim() + ',';
                csv += cells[5].textContent.trim() + ',' + cells[6].textContent.trim() + ',';
                csv += cells[7].textContent.trim() + ',' + cells[8].textContent.trim() + ',';
                csv += cells[9].textContent.trim() + ',' + cells[10].textContent.trim() + ',';
                csv += cells[11].textContent.trim() + ',' + cells[12].textContent.trim() + ',';
                csv += cells[13].textContent.trim() + '\\n';
            }
        });
    });
    var blob = new Blob([csv], {type: 'text/csv'});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = 'symbol_ranking_' + (sym === '__ALL__' ? 'all' : sym) + '.csv';
    a.click(); URL.revokeObjectURL(url);
}
filterSymbol();
</script>
</body></html>'''

    return html


def generate_symbol_table(sym, rankings):
    """Generate an HTML table for one symbol."""
    cnt = len(rankings)
    avg_sc = round(sum(r['avg_score'] for r in rankings) / cnt, 1) if cnt else 0

    html = f'''<div class="sym-section" data-symbol="{sym}">
<div class="sym-header">💱 {sym} <span class="sym-count">({cnt} signals | avg {avg_sc})</span></div>
<div style="overflow-x:auto;width:100%"><table><thead><tr>
<th>#</th><th>Signal</th><th>Symbol</th><th>Avg</th><th>⭐⭐⭐⭐</th><th>⭐⭐⭐⭐%</th>
<th>#</th><th>Win%</th><th>PF</th><th>P&L</th><th>TF</th>
<th>EA</th><th>LV</th><th>DD</th>
</tr></thead><tbody>
'''

    for i, r in enumerate(rankings, 1):
        rank = ''
        row_class = ''
        if i == 1:
            rank = '🥇'; row_class = ' class="top3"'
        elif i == 2:
            rank = '🥈'; row_class = ' class="top3"'
        elif i == 3:
            rank = '🥉'; row_class = ' class="top3"'
        else:
            rank = str(i)

        score_cls = get_score_class(r['avg_score'])
        ea_cls = f'ea-{r["ea_type"]}'
        dd_cls = get_dd_class(r['eq_max_dd'])
        ea_full = r.get('ea_full', get_ea_full_name(r['ea_type']))

        pf = r['profit_factor']
        pf_str = 'Inf' if pf > 999 else f'{pf:.1f}'

        profit_cls = 'g' if r['total_profit'] >= 0 else 'r'

        html += f'''<tr{row_class}>
<td>{rank}</td>
<td class="sig"><a href="https://signals.algoforest.com/signals/{r['signal_id']}" style="color:#64b5f6;font-weight:bold;text-decoration:none">{r['signal_id']}</a> <a href="../reports/index_{r['signal_id']}.html" style="text-decoration:none;font-size:14px" title="深度分析">📊</a> <a href="../reports/Signal_Deep_Analysis_{r['signal_id']}.html" style="text-decoration:none;font-size:14px" title="馬丁剖析法">🔍</a></td>
<td>{r['symbol']}</td>
<td class="{score_cls}">{r['avg_score']}</td>
<td class="p4">{r['star4_count']}</td>
<td class="p4">{r['star4_pct']}%</td>
<td>{r['trades']:,}</td>
<td>{r['win_rate']:.1f}%</td>
<td>{pf_str}</td>
<td class="{profit_cls}">{r['total_profit']:,.0f} pips</td>
<td><span class="tf">{r['timeframe']}</span></td>
<td><span class="ea-tag {ea_cls}">{ea_full}</span></td>
<td class="m">{r['layers']}</td>
<td class="m {dd_cls}">{r['eq_max_dd']:,.0f} pips</td>
</tr>
'''

    html += '</tbody></table></div></div>\n'
    return html


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Symbol-based Signal Ranking Generator')
    parser.add_argument('--version', default='v1', help='Strategy version label (default: v1)')
    parser.add_argument('--no-db', action='store_true', help='Skip saving to database')
    parser.add_argument('--no-html', action='store_true', help='Skip generating HTML')
    args = parser.parse_args()

    print("=" * 60)
    print("🦀 Symbol Ranking Generator - DDE v3 Copy Strategy")
    print("=" * 60)

    result = compute_all_rankings(strategy_version=args.version)
    if not result:
        print("❌ No results")
        return

    symbol_rankings, all_results, batch_run_id = result

    # Summary
    print(f"\n📊 Summary:")
    print(f"   Total symbols: {len(symbol_rankings)}")
    print(f"   Total Signal×Symbol records: {len(all_results)}")
    top_syms = sorted(symbol_rankings.keys(),
                      key=lambda s: max(r['avg_score'] for r in symbol_rankings[s]),
                      reverse=True)[:5]
    for sym in top_syms:
        best = max(symbol_rankings[sym], key=lambda x: x['avg_score'])
        print(f"   {sym}: best={best['avg_score']} (Signal {best['signal_id']})")

    # Save to DB
    if not args.no_db:
        save_to_db(all_results, strategy_version=args.version)

    # Generate HTML
    if not args.no_html:
        html = generate_html(symbol_rankings)
        output_path = OUTPUT_DIR / 'symbol_ranking_dde_v3.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n✅ HTML: {output_path} ({len(html):,} bytes)")

    return symbol_rankings


if __name__ == '__main__':
    main()
