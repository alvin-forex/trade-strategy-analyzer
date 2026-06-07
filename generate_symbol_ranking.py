#!/usr/bin/env python3
"""
Generate Symbol-based Signal Ranking HTML (DDE v5 — ranking-based, 4 dimensions)
WR 15% + PF 20% + DD 25% + Martin 40%

Symbol-centric: user selects a currency pair, sees all signals ranked by performance ON THAT PAIR
Each row = 1 Signal × 1 Symbol

Uses dde_v5_scorer for scoring, config.py for EA classification.
"""
import sys
import os
import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from dde_v5_scorer import (
    read_csv_trades, compute_raw_metrics, score_v5_batch,
    load_lot_mapping
)
from config import EA_MAP, EA_FULL_NAMES, get_ea_type, get_ea_full_name

# Directories
OUTPUT_DIR = BASE_DIR / 'output'
SAMPLES_DIR = BASE_DIR / 'samples'
DOWNLOADS_DIR = BASE_DIR / 'downloads'
OUTPUT_DIR.mkdir(exist_ok=True)


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


def compute_all_rankings(strategy_version='v5'):
    """
    Compute symbol-based rankings for all signals using DDE v5 scoring.

    v5 uses ranking-based scoring across 4 dimensions:
    - Win Rate (15%): real win rate from ALL trades (not just profitable ones)
    - Profit Factor (20%): avg profit pips / avg max lose pips
    - $1K DD% (25%): real drawdown
    - Martin Discipline (40%): WAL + layer analysis

    Returns (symbol_rankings, all_results, batch_run_id)
    """
    lot_mapping = load_lot_mapping()
    print(f"📦 Lot mapping loaded: {len(lot_mapping)} signals")

    # Collect CSVs with dedup
    all_csvs = {}
    for csv_file in sorted(SAMPLES_DIR.glob('forex-forest-signals-page-*.csv')):
        m = re.search(r'(\d+)', csv_file.stem)
        if m:
            all_csvs[m.group(1)] = csv_file
    if DOWNLOADS_DIR.exists():
        for csv_file in sorted(DOWNLOADS_DIR.glob('forex-forest-signals-page-*.csv')):
            m = re.search(r'(\d+)', csv_file.stem)
            if m and m.group(1) not in all_csvs:
                all_csvs[m.group(1)] = csv_file

    print(f"📄 CSV signals: {len(all_csvs)}")

    # Load batch_analysis_results.json for additional metadata if available
    batch_data_path = OUTPUT_DIR / 'batch_analysis_results.json'
    batch_lookup = {}
    if batch_data_path.exists():
        with open(batch_data_path) as f:
            batch_data = json.load(f)
        batch_lookup = {str(r['signal_id']): r for r in batch_data}

    batch_run_id = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Step 1: Compute raw metrics for all Signal×CCY pairs
    all_metrics = []
    seen_ids = set()
    total = len(all_csvs)

    for i, (sid, csv_file) in enumerate(sorted(all_csvs.items())):
        if sid in seen_ids:
            continue
        seen_ids.add(sid)

        print(f"[{i+1}/{total}] Signal {sid}...", end=' ', flush=True)

        ea_type = get_ea_type(sid)
        trades = read_csv_trades(str(csv_file))
        if not trades:
            print("NO TRADES")
            continue

        # Group by symbol
        by_symbol = defaultdict(list)
        for t in trades:
            by_symbol[t['symbol']].append(t)

        # Get lot layers for this signal
        lot_layers = None
        if sid in lot_mapping and lot_mapping[sid].get('lot_layers'):
            lot_layers = [(lv, lot) for lv, lot in lot_mapping[sid].get('lot_layers', [])]

        sym_count = len(by_symbol)
        scored = 0

        for sym, sym_trades in by_symbol.items():
            metrics = compute_raw_metrics(sym_trades, lot_layers=lot_layers)
            if metrics is None:
                continue

            metrics['signal_id'] = sid
            metrics['symbol'] = sym
            metrics['ea_type'] = ea_type
            metrics['ea_full'] = get_ea_full_name(ea_type)

            # Layer display
            layer_names = []
            for ln in sorted(set(metrics['layers'].keys()),
                            key=lambda x: (99 if x == 'L9+' else int(x[1:]))):
                if metrics['layers'].get(ln, 0) > 0:
                    layer_names.append(ln)
            metrics['lv'] = '+'.join(layer_names) if layer_names else '-'

            # Timeframe from batch data if available
            rec = batch_lookup.get(sid, {})
            metrics['timeframe'] = rec.get('timeframe', '')
            metrics['avg_layers'] = rec.get('avg_layers', 0)

            all_metrics.append(metrics)
            scored += 1

        print(f"{sym_count} symbols, {scored} scored")

    if not all_metrics:
        print("❌ No metrics computed")
        return None

    # Step 2: Batch score using v5 ranking system
    print(f"\n📊 Computing v5 scores for {len(all_metrics)} Signal×CCY pairs...")
    scored_results = score_v5_batch(all_metrics)

    # Step 3: Organize by symbol
    symbol_rankings = defaultdict(list)
    all_results = []

    for r in scored_results:
        record = {
            'signal_id': r['signal_id'],
            'symbol': r['symbol'],
            'strategy_version': strategy_version,
            'analysis_date': datetime.now().strftime('%Y-%m-%d'),
            'avg_score': r['dde_v5'],
            'dde_v5': r['dde_v5'],
            'red_card': r['red_card'],
            'red_reasons': r.get('red_reasons', []),
            # v5 dimension scores
            'wr_pct': r['wr_pct'],
            'pf_pct': r['pf_pct'],
            'dd_pct': r['dd_pct'],
            'martin_pct': r['martin_pct'],
            # Raw metrics
            'win_rate': r['win_rate'],
            'profit_factor': round(r['pf'], 1),
            'total_profit': r['total_net_pips'],
            'trades': r['trades'],
            'wal': r['wal'],
            'max_dd_pips': r['max_dd_pips'],
            # Metadata
            'timeframe': r.get('timeframe', ''),
            'ea_type': r.get('ea_type', 'UNK'),
            'ea_full': r.get('ea_full', 'UNK'),
            'layers': get_layer_info(r.get('avg_layers', 0)),
            'lv': r.get('lv', '-'),
            'eq_max_dd': round(-r['max_dd_pips'], 0),
            'batch_run_id': batch_run_id,
            # Backward compat
            'star4_count': 0,
            'star4_pct': 0,
            'total_comparisons': r['trades'],
            'score_breakdown': {
                'trigger': f"WR {r['win_rate']:.0f}%",
                'alpha': f"PF {r['pf']:.2f}",
                'dde': f"DD {r['max_dd_pips']:.0f}",
            },
        }

        symbol_rankings[r['symbol']].append(record)
        all_results.append(record)

    return symbol_rankings, all_results, batch_run_id


def generate_html(symbol_rankings):
    """Generate the symbol-based ranking HTML with dropdown selector."""

    # Sort symbols by number of signals descending
    sorted_symbols = sorted(symbol_rankings.keys(),
                           key=lambda s: len(symbol_rankings[s]), reverse=True)

    # Global stats
    total_records = sum(len(v) for v in symbol_rankings.values())
    total_signals = len(set(r['signal_id'] for v in symbol_rankings.values() for r in v))

    valid_scores = [r['avg_score'] for v in symbol_rankings.values()
                    for r in v if not r.get('red_card')]
    global_avg = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0
    global_best = max(valid_scores) if valid_scores else 0

    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Symbol Ranking - DDE v5</title>
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
table{{width:100%;min-width:1000px;border-collapse:collapse;margin-bottom:8px}}
th{{background:#111520;padding:6px 8px;text-align:left;border-bottom:2px solid #FFD700;color:#FFD700;font-size:0.8em;white-space:nowrap}}
td{{padding:5px 8px;text-align:left;border-bottom:1px solid #1a1f2e}}
tr:hover{{background:#111520}}
tr.top3{{background:rgba(255,215,0,0.03)}}
tr.red-card{{opacity:0.5}}
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
.dim{{font-size:0.75em;color:#888}}
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
    <a href="./symbol_ranking.html" style="color:#FFD700;text-decoration:none;font-size:.88em;font-weight:600;padding:4px 10px;border-radius:6px;background:#1a1f2e">📊 Symbol</a>
  </div>
</div>
<h1>📊 Symbol Ranking - DDE v5</h1>
<div class="sub">WR 15% + PF 20% + DD 25% + Martin 40% | {total_signals} signals × {len(sorted_symbols)} symbols | {total_records} pairs | {now}</div>

<div class="controls">
<label for="symSelect">💱 貨幣對:</label>
<select id="symSelect" onchange="filterSymbol()">
<option value="__ALL__">- 所有貨幣對 (Top 10) -</option>
'''

    for sym in sorted_symbols:
        cnt = len(symbol_rankings[sym])
        html += f'<option value="{sym}">{sym} ({cnt} signals)</option>\n'

    html += '''</select>
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
    var csv = 'Rank,Signal,Symbol,Score,Win%,PF,P&L,Trades,WAL,DD,TF,EA,LV\\n';
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
                csv += cells[11].textContent.trim() + ',' + cells[12].textContent.trim() + '\\n';
            }
        });
    });
    var blob = new Blob([csv], {type: 'text/csv'});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = 'symbol_ranking_v5_' + (sym === '__ALL__' ? 'all' : sym) + '.csv';
    a.click(); URL.revokeObjectURL(url);
}
filterSymbol();
</script>
</body></html>'''

    return html


def generate_symbol_table(sym, rankings):
    """Generate an HTML table for one symbol."""
    cnt = len(rankings)
    valid_scores = [r['avg_score'] for r in rankings if not r.get('red_card')]
    avg_sc = round(sum(valid_scores) / len(valid_scores), 1) if valid_scores else 0

    html = f'''<div class="sym-section" data-symbol="{sym}">
<div class="sym-header">💱 {sym} <span class="sym-count">({cnt} signals | avg {avg_sc})</span></div>
<div style="overflow-x:auto;width:100%"><table><thead><tr>
<th>#</th><th>Signal</th><th>Symbol</th><th>Score</th>
<th>Win%</th><th>PF</th><th>P&L</th><th>#</th>
<th>WAL</th><th>DD</th><th>TF</th><th>EA</th><th>LV</th>
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

        if r.get('red_card'):
            row_class = ' class="red-card"'
            rank = '🚫'

        score_cls = get_score_class(r['avg_score'])
        ea_cls = f'ea-{r["ea_type"]}'
        dd_cls = get_dd_class(r['eq_max_dd'])
        ea_full = r.get('ea_full', get_ea_full_name(r['ea_type']))

        pf = r['profit_factor']
        pf_str = 'Inf' if pf > 999 else f'{pf:.1f}'

        profit_cls = 'g' if r['total_profit'] >= 0 else 'r'

        # Dimension breakdown tooltip
        dim_info = (f"WR%={r['wr_pct']:.0f} PF%={r['pf_pct']:.0f} "
                    f"DD%={r['dd_pct']:.0f} Martin%={r['martin_pct']:.0f}")

        html += f'''<tr{row_class}>
<td title="{dim_info}">{rank}</td>
<td class="sig"><a href="https://signals.algoforest.com/signals/{r['signal_id']}" style="color:#64b5f6;font-weight:bold;text-decoration:none">{r['signal_id']}</a> <a href="../reports/index_{r['signal_id']}.html" style="text-decoration:none;font-size:14px" title="深度分析">📊</a> <a href="../reports/Signal_Deep_Analysis_{r['signal_id']}.html" style="text-decoration:none;font-size:14px" title="馬丁剖析法">🔍</a></td>
<td>{r['symbol']}</td>
<td class="{score_cls}" title="{dim_info}">{r['avg_score']}</td>
<td>{r['win_rate']:.1f}%</td>
<td>{pf_str}</td>
<td class="{profit_cls}">{r['total_profit']:,.0f}p</td>
<td>{r['trades']:,}</td>
<td class="m">{r['wal']:.2f}</td>
<td class="m {dd_cls}">{r['eq_max_dd']:,.0f}</td>
<td><span class="tf">{r['timeframe']}</span></td>
<td><span class="ea-tag {ea_cls}">{ea_full}</span></td>
<td class="m">{r['layers']}</td>
</tr>
'''

    html += '</tbody></table></div></div>\n'
    return html


def main():
    import argparse
    parser = argparse.ArgumentParser(description='Symbol-based Signal Ranking Generator (DDE v5)')
    parser.add_argument('--version', default='v5', help='Strategy version label (default: v5)')
    parser.add_argument('--no-html', action='store_true', help='Skip generating HTML')
    args = parser.parse_args()

    print("=" * 60)
    print("🦀 Symbol Ranking Generator - DDE v5")
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

    valid = [r for r in all_results if not r.get('red_card')]
    red = [r for r in all_results if r.get('red_card')]
    print(f"   Valid: {len(valid)}, Red cards: {len(red)}")

    top_syms = []
    for sym in symbol_rankings.keys():
        valid_for_sym = [r for r in symbol_rankings[sym] if not r.get('red_card')]
        if valid_for_sym:
            best_score = max(r['avg_score'] for r in valid_for_sym)
            top_syms.append((sym, best_score))
    top_syms.sort(key=lambda x: x[1], reverse=True)
    top_syms = [sym for sym, _ in top_syms[:5]]
    for sym in top_syms:
        best = max((r for r in symbol_rankings[sym] if not r.get('red_card')),
                   key=lambda x: x['avg_score'], default=None)
        if best:
            print(f"   {sym}: best={best['avg_score']} (Signal {best['signal_id']}, WR={best['win_rate']:.0f}%)")

    # Generate HTML
    if not args.no_html:
        html = generate_html(symbol_rankings)
        output_path = OUTPUT_DIR / 'symbol_ranking_dde_v5.html'
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"\n✅ HTML: {output_path} ({len(html):,} bytes)")

    return symbol_rankings


if __name__ == '__main__':
    main()
