#!/usr/bin/env python3
"""
Generate Signal Ranking HTML (DDE v3 Copy Strategy format)
Avg Score = mean of all non-zero weighted_scores (CoP + CoL) across per-symbol per-level analysis
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

BASE_DIR = Path(__file__).parent
SAMPLES_DIR = BASE_DIR / 'samples'
OUTPUT_DIR = BASE_DIR / 'output'

LEVEL_RANGES = {
    'L1': (0, 50),
    'L2': (50, 100),
    'L3': (100, 150),
    'L4+': (150, float('inf'))
}

# EA type mapping
EA_MAP = {
    'DW': ['10437','11984','13790','17547','21698','22200','22278','25830','30359','31781','32719','3291','33101','31593','34574','36338','36397','36511','34259','20846','16538'],
    'SMA': ['106','1980','2351','32278','32541','5001','5275','537','5566','11889','13863','14724','16596','16698','16706','17611','17823','10864','14158'],
    'MKD': ['12962','13461','14341','14592','1470','17962','20805','23617','25668','25260','8325','7919'],
    'S10': ['13798','16596'],
    'Flash': ['19849'],
    'GEM': ['14581'],
}

def get_ea_type(signal_id):
    for ea_type, signals in EA_MAP.items():
        if signal_id in signals:
            return ea_type
    return 'UNK'

def get_layer_info(rec):
    layers = rec.get('avg_layers', 0)
    if layers == 0:
        return '0LV'
    return f'{int(round(layers))}LV'

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
    elif score >= 85:
        return 's85'
    elif score >= 75:
        return 's75'
    else:
        return 's0'

def compute_signal_score(signal_id):
    """
    Compute DDE v3 score for a signal.
    Per-symbol, per-level analysis.
    Avg Score = mean of all non-zero weighted_scores (CoP + CoL).
    """
    csv_path = None
    for pattern in [f'forex-forest-signals-page-{signal_id}.csv', f'forex-forest-signals-page-{signal_id} (2).csv']:
        p = SAMPLES_DIR / pattern
        if p.exists():
            csv_path = p
            break
    
    if not csv_path:
        return None
    
    trades = analyze_trades_from_csv(str(csv_path))
    if not trades:
        return None
    
    by_symbol = defaultdict(list)
    for t in trades:
        sym = t.get('symbol', t.get('currency', 'UNKNOWN'))
        by_symbol[sym].append(t)
    
    all_scores = []
    star4 = 0
    total = 0
    
    for sym, sym_trades in by_symbol.items():
        lr = analyze_by_levels(sym_trades, LEVEL_RANGES)
        for level_name, ld in lr.items():
            if ld.get('stats', {}).get('count', 0) == 0:
                continue
            for strategy in ['copy_on_profit', 'copy_on_lose']:
                sdata = ld.get(strategy, {})
                for wp, wp_data in sdata.items():
                    score = wp_data.get('weighted_score', 0)
                    rating = wp_data.get('rating', '')
                    total += 1
                    if score > 0:
                        all_scores.append(score)
                        if '⭐⭐⭐⭐' in rating:
                            star4 += 1
    
    if not all_scores:
        return None
    
    avg_score = round(sum(all_scores) / len(all_scores), 1)
    
    return {
        'avg_score': avg_score,
        'star4_count': star4,
        'cmp_total': len(all_scores),
        'star4_pct': round(star4 / len(all_scores) * 100),
    }


def main():
    print("=" * 60)
    print("🦀 Signal Ranking Generator — DDE v3 Copy Strategy")
    print("=" * 60)
    
    with open(OUTPUT_DIR / 'batch_analysis_results.json') as f:
        batch_data = json.load(f)
    
    batch_lookup = {r['signal_id']: r for r in batch_data}
    
    results = []
    
    seen_ids = set()
    for i, rec in enumerate(batch_data):
        sid = rec['signal_id']
        if sid in seen_ids:
            print(f"[{i+1}/{len(batch_data)}] Signal {sid}... SKIP (duplicate)")
            continue
        seen_ids.add(sid)
        print(f"[{i+1}/{len(batch_data)}] Signal {sid}...", end=' ', flush=True)
        
        score_data = compute_signal_score(sid)
        
        if not score_data:
            print("SKIP")
            continue
        
        print(f"Score={score_data['avg_score']} ⭐4={score_data['star4_count']}/{score_data['cmp_total']} ({score_data['star4_pct']}%)")
        
        results.append({
            'signal_id': sid,
            'avg_score': score_data['avg_score'],
            'star4_count': score_data['star4_count'],
            'cmp_total': score_data['cmp_total'],
            'star4_pct': score_data['star4_pct'],
            'total_trades': rec.get('total_trades', 0),
            'win_rate': rec.get('win_rate', 0),
            'profit_factor': rec.get('profit_factor', 0),
            'total_profit': rec.get('total_profit', 0),
            'max_dd': rec.get('max_dd', 0),
            'timeframe': rec.get('timeframe', ''),
            'ea_type': get_ea_type(sid),
            'layer_info': get_layer_info(rec),
            'dd_class': get_dd_class(rec.get('max_dd', 0)),
        })
    
    results.sort(key=lambda x: x['avg_score'], reverse=True)
    
    total_signals = len(results)
    avg_score = sum(r['avg_score'] for r in results) / total_signals if total_signals else 0
    best_score = results[0]['avg_score'] if results else 0
    worst_score = results[-1]['avg_score'] if results else 0
    avg_star4_pct = sum(r['star4_pct'] for r in results) / total_signals if total_signals else 0
    
    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Signal Ranking - DDE v3 Copy Strategy</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,sans-serif;background:#0a0e17;color:#d0d0d0;padding:12px;font-size:13px}}
h1{{font-size:1.2em;margin-bottom:2px;color:#FFD700}}
.sub{{color:#666;font-size:0.85em;margin-bottom:12px}}
.sum{{background:#111520;border:1px solid #1e2433;border-radius:6px;padding:10px 14px;margin-bottom:12px;display:flex;flex-wrap:wrap;gap:20px}}
.sum .v{{font-size:1.3em;font-weight:bold;color:#FFD700}}
.sum .l{{font-size:0.7em;color:#666}}
table{{width:100%;min-width:900px;border-collapse:collapse}}
th{{background:#111520;padding:6px 8px;text-align:left;border-bottom:2px solid #FFD700;color:#FFD700;font-size:0.8em;white-space:nowrap}}
td{{padding:5px 8px;text-align:left;border-bottom:1px solid #1a1f2e}}
tr:hover{{background:#111520}}
tr.top3{{background:rgba(255,215,0,0.03)}}
.sig{{color:#64b5f6;font-weight:bold}}
.s90{{color:#4CAF50;font-weight:bold}}.s85{{color:#8BC34A;font-weight:bold}}.s75{{color:#FFC107;font-weight:bold}}.s0{{color:#FF5722;font-weight:bold}}
.p4{{color:#4CAF50}}
.g{{color:#4CAF50}}.r{{color:#FF5722}}
.m{{font-family:'SF Mono',Consolas,monospace;font-size:0.9em}}
.tf{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:0.8em;background:#1a237e;color:#90caf9}}
.ea-tag{{display:inline-block;padding:1px 5px;border-radius:3px;font-size:0.72em;font-weight:bold}}
.ea-DW{{background:#4a148c;color:#ce93d8}}
.ea-SMA{{background:#1b5e20;color:#a5d6a7}}
.ea-MKD{{background:#e65100;color:#ffcc80}}
.ea-S10{{background:#0d47a1;color:#90caf9}}
.ea-Flash{{background:#880e4f;color:#f48fb1}}
.ea-GEM{{background:#37474f;color:#b0bec5}}
.ea-STB{{background:#37474f;color:#b0bec5}}
.ea-UNK{{background:#37474f;color:#b0bec5}}
.dd-g{{color:#4CAF50}}.dd-y{{color:#FFC107}}.dd-r{{color:#FF5722}}
@media(max-width:768px){{body{{font-size:11px}}th,td{{padding:3px 5px}}}}
</style>
</head>
<body>
<h1>📊 Signal Ranking — DDE v3 Copy Strategy</h1>
<div class="sub">Trigger 40% + Alpha Capture 40% + DDE 20% | {total_signals} signals | {datetime.now().strftime('%Y-%m-%d')}</div>
<div class="sum">
<div><div class="v">{total_signals}</div><div class="l">Signals</div></div>
<div><div class="v">{avg_score:.1f}</div><div class="l">Avg Score</div></div>
<div><div class="v">{best_score:.1f}</div><div class="l">Best</div></div>
<div><div class="v">{worst_score:.1f}</div><div class="l">Worst</div></div>
<div><div class="v">{avg_star4_pct:.0f}%</div><div class="l">Avg ⭐⭐⭐⭐</div></div>
</div>
<div style="overflow-x:auto;width:100%"><table><thead><tr>
<th>#</th><th>Signal</th><th>Avg Score</th><th>⭐⭐⭐⭐</th><th>⭐⭐⭐⭐%</th>
<th>Trades</th><th>Win%</th><th>PF</th><th>Total Profit</th><th>TF</th><th>Cmp</th>
<th>EA</th><th>LV</th><th>Eq Max DD</th>
</tr></thead><tbody>
'''
    
    for i, r in enumerate(results, 1):
        rank = ''
        row_class = ''
        if i == 1:
            rank = '🥇'
            row_class = ' class="top3"'
        elif i == 2:
            rank = '🥈'
            row_class = ' class="top3"'
        elif i == 3:
            rank = '🥉'
            row_class = ' class="top3"'
        else:
            rank = str(i)
        
        score_cls = get_score_class(r['avg_score'])
        ea_cls = f'ea-{r["ea_type"]}'
        dd_cls = r['dd_class']
        
        pf = r['profit_factor']
        pf_str = 'Inf' if pf > 999 else f'{pf:.1f}'
        
        html += f'''<tr{row_class}>
<td>{rank}</td>
<td class="sig">{r['signal_id']}</td>
<td class="{score_cls}">{r['avg_score']}</td>
<td class="p4">{r['star4_count']}</td>
<td class="p4">{r['star4_pct']}%</td>
<td>{r['total_trades']:,}</td>
<td>{r['win_rate']:.1f}%</td>
<td>{pf_str}</td>
<td class="g">{r['total_profit']:,.0f} pips</td>
<td><span class="tf">{r['timeframe']}</span></td>
<td>{r['cmp_total']}</td>
<td><span class="ea-tag {ea_cls}">{r['ea_type']}</span></td>
<td class="m">{r['layer_info']}</td>
<td class="m {dd_cls}">{r['max_dd']:,.0f} pips</td>
</tr>
'''
    
    html += '</tbody></table></div></body></html>'
    
    output_path = OUTPUT_DIR / 'signal_ranking_dde_v3.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ Generated: {output_path}")
    print(f"   Size: {len(html):,} bytes")
    print(f"   Signals: {total_signals}")
    print(f"   Avg Score: {avg_score:.1f}")
    print(f"   Best: {best_score:.1f} (Signal {results[0]['signal_id']})")
    print(f"   Worst: {worst_score:.1f} (Signal {results[-1]['signal_id']})")
    
    return str(output_path)

if __name__ == '__main__':
    main()
