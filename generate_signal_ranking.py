#!/usr/bin/env python3
"""
Generate Signal Ranking HTML (DDE v4 — 5 dimensions)
Win Rate 20% + Holding Time 5% + Trade Count 15% + Martin Layers 25% + Risk/Reward 35%
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

from dde_v4_scorer import score_v4, read_csv_trades

BASE_DIR = Path(__file__).parent
SAMPLES_DIR = BASE_DIR / 'samples'
OUTPUT_DIR = BASE_DIR / 'output'

# Level ranges no longer used for lot-based detection (kept for reference)
# Lot-based levels are computed from signal_lot_mapping.json via dde_v4_scorer.py
LEVEL_RANGES = {
    'L1': (0, 50),
    'L2': (50, 100),
    'L3': (100, 150),
    'L4': (150, 200),
    'L5': (200, 250),
    'L6': (250, 300),
    'L7': (300, 350),
    'L8': (350, 400),
    'L9+': (400, float('inf'))
}

# EA type: manual overrides (boss-confirmed) take priority
EA_OVERRIDES = {
    '10344': 'Flash',   # Boss confirmed
    '12173': 'SMA',     # Boss confirmed (Wayne Class = SMA strategy)
    '7999': 'MKD',      # Boss confirmed (richman EA)
    '38678': 'DW',      # Dragon Wave v2.10
}

# Auto-detected EA mapping from SET file counts
EA_MAP = {
    'DW': ['10437','106','11984','12962','13790','16538','17547','20846','21698','22200','22278','25830','31593','32541','32719','34259','36338','36397','36511'],
    'SMA': ['537','1470','1980','2351','5001','5275','5566','10864','11984','14581','14724','16698','17611','17823','19849','23617','30359','33101','34574'],
    'MKD': ['8325','13461','14592','25260','25668','31781'],
    'S10': ['13798','16596'],
    'Flash': ['7919','11889','13863','14158','14341','16706','17962','20805','19849'],
    'GEM': ['3291'],
}

EA_NORMALIZE = {
    'DragonWave': 'DW', 'Dragon Wave': 'DW',
    'Flash': 'Flash',
    'SMA': 'SMA', 'SMAPro': 'SMA', 'SMA Pro': 'SMA',
    'MKD': 'MKD', 'MKDPro': 'MKD', 'MKD Pro': 'MKD',
    'S10': 'S10',
    'GeminiClient': 'GEM', 'Gemini Client': 'GEM',
    'GeminiServer': 'GEM', 'Gemini Server': 'GEM',
    'StableHelper': 'Helper', 'Stable Helper': 'Helper',
}

def auto_detect_ea_from_set(signal_id):
    """Auto-detect primary EA from SET files in downloads/"""
    import os, re
    from collections import Counter
    counts = Counter()
    for root, dirs, files in os.walk(str(SAMPLES_DIR).replace('samples', 'downloads')):
        for f in files:
            if not f.endswith('.set'):
                continue
            m = re.match(r'\((\d+)\)', f)
            if m and m.group(1) == str(signal_id):
                rest = f[len(m.group(0)):]
                ea_match = re.match(r'(.*?)(?:AUD|CAD|CHF|EUR|GBP|JPY|NZD|USD|XAU|XAG|GAS|BVSPX|Fra)', rest)
                if ea_match:
                    ea_raw = re.sub(r'[\s_]?v?[\d.]+$', '', ea_match.group(1).strip().rstrip('_ '))
                    ea = EA_NORMALIZE.get(ea_raw, ea_raw)
                    if ea != 'Helper':
                        counts[ea] += 1
    if counts:
        return counts.most_common(1)[0][0]
    return None

def get_all_eas(signal_id):
    """Get all EA types for a signal, sorted by SET file count (desc)."""
    sid = str(signal_id)
    import os, re
    from collections import Counter
    counts = Counter()
    for root, dirs, files in os.walk(str(SAMPLES_DIR).replace('samples', 'downloads')):
        for f in files:
            if not f.endswith('.set'):
                continue
            m = re.match(r'\((\d+)\)', f)
            if m and m.group(1) == sid:
                rest = f[len(m.group(0)):]
                ea_match = re.match(r'(.*?)(?:AUD|CAD|CHF|EUR|GBP|JPY|NZD|USD|XAU|XAG|GAS|BVSPX|Fra)', rest)
                if ea_match:
                    ea_raw = re.sub(r'[\s_]?v?[\d.]+$', '', ea_match.group(1).strip().rstrip('_ '))
                    ea = EA_NORMALIZE.get(ea_raw, ea_raw)
                    if ea != 'Helper':
                        counts[ea] += 1
    if counts:
        return [ea for ea, _ in counts.most_common()]
    # Fallback: single EA from get_ea_type
    single = get_ea_type(sid)
    return [single] if single and single != 'UNK' else []

def get_ea_type(signal_id):
    sid = str(signal_id)
    # 1. Manual override (boss-confirmed) takes priority
    if sid in EA_OVERRIDES:
        return EA_OVERRIDES[sid]
    # 2. EA_MAP lookup
    for ea_type, signals in EA_MAP.items():
        if sid in signals:
            return ea_type
    # 3. Auto-detect from SET files
    auto = auto_detect_ea_from_set(sid)
    if auto:
        return auto
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
    Compute DDE v4 score for a signal.
    Per-symbol analysis using 5 dimensions:
    Win Rate 20% + Holding Time 5% + Trade Count 15% + Martin Layers 25% + Risk/Reward 35%
    """
    csv_path = None
    for pattern in [f'forex-forest-signals-page-{signal_id}.csv', f'forex-forest-signals-page-{signal_id} (2).csv']:
        p = SAMPLES_DIR / pattern
        if p.exists():
            csv_path = p
            break
    
    if not csv_path:
        return None
    
    trades = read_csv_trades(str(csv_path))
    if not trades:
        return None
    
    by_symbol = defaultdict(list)
    for t in trades:
        sym = t.get('symbol', 'UNKNOWN')
        by_symbol[sym].append(t)
    
    all_scores = []
    red_cards = 0
    total_symbols = 0
    
    for sym, sym_trades in by_symbol.items():
        total_symbols += 1
        result = score_v4(sym_trades)
        if result:
            all_scores.append(result['score'])
            if result.get('red_card'):
                red_cards += 1
    
    if not all_scores:
        return None
    
    avg_score = round(sum(all_scores) / len(all_scores), 1)
    clean_symbols = len(all_scores) - red_cards
    
    return {
        'avg_score': avg_score,
        'clean_symbols': clean_symbols,
        'total_symbols': total_symbols,
        'clean_pct': round(clean_symbols / total_symbols * 100) if total_symbols else 0,
        'red_cards': red_cards,
    }


def main():
    print("=" * 60)
    print("🦀 Signal Ranking Generator — DDE v4 (5 Dimensions)")
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
        
        print(f"Score={score_data['avg_score']} Clean={score_data['clean_symbols']}/{score_data['total_symbols']} ({score_data['clean_pct']}%)")
        
        results.append({
            'signal_id': sid,
            'avg_score': score_data['avg_score'],
            'clean_symbols': score_data['clean_symbols'],
            'total_symbols': score_data['total_symbols'],
            'clean_pct': score_data['clean_pct'],
            'total_trades': rec.get('total_trades', 0),
            'win_rate': rec.get('win_rate', 0),
            'profit_factor': round(abs(rec.get('total_profit', 0) / abs(rec.get('max_loss', 1))), 1) if rec.get('max_loss', 0) != 0 else 999,
            'total_profit': rec.get('total_profit', 0),
            'total_pips': rec.get('total_pips', 0),
            'max_dd': rec.get('max_loss', 0),
            'timeframe': rec.get('timeframe', ''),
            'ea_type': get_ea_type(sid),
            'layer_info': get_layer_info(rec),
            'dd_class': get_dd_class(rec.get('max_loss', 0)),
        })
    
    results.sort(key=lambda x: x['avg_score'], reverse=True)
    
    total_signals = len(results)
    avg_score = sum(r['avg_score'] for r in results) / total_signals if total_signals else 0
    best_score = results[0]['avg_score'] if results else 0
    worst_score = results[-1]['avg_score'] if results else 0
    avg_clean_pct = sum(r['clean_pct'] for r in results) / total_signals if total_signals else 0
    
    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🏆 Signal 排名</title>
<style>
/* === Unified Theme System === */
:root{{--font-main:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Microsoft JhengHei',sans-serif;--radius:8px;--shadow:0 2px 8px rgba(0,0,0,0.12)}}
[data-theme="dark"]{{--bg:#0a0e17;--bg-card:#111520;--bg-hover:#1a1f2e;--text:#d0d0d0;--text2:#888;--primary:#FFD700;--accent:#64b5f6;--green:#4CAF50;--red:#FF5722;--yellow:#FFC107;--orange:#fd7e14;--border:#1e2433;--th-bg:#111520;--nav-bg:transparent;--grade-a:#4CAF50;--grade-b:#FFC107;--grade-c:#fd7e14;--grade-d:#FF5722;--header-from:#1a1f2e;--header-to:#0a0e17}}
[data-theme="light"]{{--bg:#f5f7fa;--bg-card:#ffffff;--bg-hover:#eef2f7;--text:#333;--text2:#666;--primary:#0f3460;--accent:#e94560;--green:#28a745;--red:#dc3545;--yellow:#ffc107;--orange:#fd7e14;--border:#ddd;--th-bg:#eef2f7;--nav-bg:rgba(0,0,0,0.03);--grade-a:#28a745;--grade-b:#ffc107;--grade-c:#fd7e14;--grade-d:#dc3545;--header-from:#0f3460;--header-to:#16213e}}
*{{transition:background-color .25s ease,color .25s ease,border-color .25s ease}}
.theme-toggle{{width:36px;height:36px;border:1px solid var(--border);border-radius:50%;background:var(--bg-card);color:var(--text);font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:var(--shadow);line-height:1;padding:0;flex-shrink:0}}.theme-toggle:hover{{background:var(--bg-hover);transform:scale(1.1)}}
/* Topnav */
.topnav{{display:flex;align-items:center;gap:12px;padding:10px 16px;background:var(--bg-card);border-bottom:1px solid var(--border);margin-bottom:16px;position:sticky;top:0;z-index:100}}
.topnav-logo{{font-weight:700;font-size:1em;color:var(--primary);text-decoration:none;margin-right:auto}}
.topnav-links{{display:flex;gap:10px;flex-wrap:wrap}}
.topnav-link{{color:var(--text2);text-decoration:none;font-size:.88em;font-weight:600;padding:4px 10px;border-radius:6px;transition:all .2s}}
.topnav-link:hover{{color:var(--primary);background:var(--bg-hover)}}
.topnav-link.active{{color:var(--primary);background:var(--bg-hover)}}
/* Page styles */
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--font-main);background:var(--bg);color:var(--text);padding:16px;font-size:13px}}
h1{{font-size:1.3em;margin-bottom:4px;color:var(--primary)}}
.info-tip:hover .info-tip-text{{display:block}}
.sum{{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:10px 14px;margin-bottom:12px;display:flex;flex-wrap:wrap;gap:20px}}
.sum .v{{font-size:1.3em;font-weight:bold;color:var(--primary)}}
.sum .l{{font-size:0.7em;color:var(--text2)}}
table{{width:100%;min-width:900px;border-collapse:collapse}}
th{{background:var(--th-bg);padding:6px 8px;text-align:left;border-bottom:2px solid var(--primary);color:var(--primary);font-size:0.8em;white-space:nowrap}}
td{{padding:5px 8px;text-align:left;border-bottom:1px solid var(--border)}}
tr:hover{{background:var(--bg-hover)}}
tr.top3{{background:rgba(255,215,0,0.03)}}
.sig{{color:var(--accent);font-weight:bold}}
.s90{{color:var(--green);font-weight:bold}}.s85{{color:#8BC34A;font-weight:bold}}.s75{{color:var(--yellow);font-weight:bold}}.s0{{color:var(--red);font-weight:bold}}
.p4{{color:var(--green)}}
.g{{color:var(--green)}}.r{{color:var(--red)}}
.m{{font-family:'SF Mono',Consolas,monospace;font-size:0.9em}}
.tf{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:0.8em;background:var(--bg-hover);color:var(--accent)}}
.ea-tag{{display:inline-block;padding:1px 5px;border-radius:3px;font-size:0.72em;font-weight:bold}}
.ea-DW{{background:#4a148c;color:#ce93d8}}
.ea-SMA{{background:#1b5e20;color:#a5d6a7}}
.ea-MKD{{background:#e65100;color:#ffcc80}}
.ea-S10{{background:#0d47a1;color:#90caf9}}
.ea-Flash{{background:#880e4f;color:#f48fb1}}
.ea-GEM{{background:#37474f;color:#b0bec5}}
.ea-STB{{background:#37474f;color:#b0bec5}}
.ea-MAN{{background:#4527a0;color:#e8eaf6}}
.dd-g{{color:var(--green)}}.dd-y{{color:var(--yellow)}}.dd-r{{color:var(--red)}}
@media(max-width:768px){{body{{font-size:11px}}th,td{{padding:3px 5px}}}}
</style>
</head>
<body>
<div class="topnav">
  <a href="./index.html" class="topnav-logo">🦀 TSA</a>
  <div class="topnav-links">
    <a href="./signal_ranking.html" class="topnav-link active">🏆 Signal 排名</a>
    <a href="./admin/ccy_ranking.html" class="topnav-link">💱 CCY 排名</a>
    <a href="./admin/symbol_ranking.html" class="topnav-link">📊 波幅波</a>
  </div>
  <button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()">🌙</button>
</div>
<h1>🏆 Signal 排名</h1>
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:0.82em;color:var(--text2)"><span>{total_signals} signals · {datetime.now().strftime('%Y-%m-%d')}</span><span class="info-tip" style="position:relative;display:inline-flex;cursor:pointer"><span style="width:18px;height:18px;border-radius:50%;background:var(--bg-hover);border:1px solid var(--border);display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-style:italic;color:var(--text2)">i</span><span class="info-tip-text" style="display:none;position:absolute;top:24px;left:0;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:10px 14px;font-size:0.82em;line-height:1.6;z-index:50;white-space:nowrap;box-shadow:0 4px 16px rgba(0,0,0,0.3);color:var(--text)">DDE v4 五維評分權重：<b style="color:var(--primary)">WR</b> 20% · <b style="color:var(--primary)">HT</b> 5% · <b style="color:var(--primary)">TC</b> 15% · <b style="color:var(--primary)">ML</b> 25% · <b style="color:var(--primary)">RR</b> 35%</span></span></div>
<div class="sum">
<div><div class="v">{total_signals}</div><div class="l">Signals</div></div>
<div><div class="v">{avg_score:.1f}</div><div class="l">Avg Score</div></div>
<div><div class="v">{best_score:.1f}</div><div class="l">Best</div></div>
<div><div class="v">{worst_score:.1f}</div><div class="l">Worst</div></div>
<div><div class="v">{avg_clean_pct:.0f}%</div><div class="l">Avg CB</div></div>
</div>
<div style="overflow-x:auto;width:100%"><table><thead><tr>
<th>#</th><th>Signal</th><th>CCY</th><th>DDE</th><th>CB</th>
<th>Win%</th><th>Trades</th><th>Profit</th><th>DD</th><th>PF</th>
<th>TF</th><th>LV</th><th>EA</th>
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
        signal_id = r['signal_id']
        all_eas = get_all_eas(signal_id)
        ea_cls = f'ea-{r["ea_type"]}'
        ea_tags = ' '.join([f'<span class="ea-tag ea-{ea}">{ea}</span>' for ea in all_eas])
        dd_cls = r['dd_class']
        
        pf = r['profit_factor']
        pf_str = 'Inf' if pf > 999 else f'{pf:.1f}'

        report_url = f'../reports/index_{signal_id}.html'
        martin_url = f'../reports/Signal_Deep_Analysis_{signal_id}.html'
        signal_page_url = f'https://signals.algoforest.com/signals/{signal_id}'
        html += f'''<tr{row_class}>
<td>{rank}</td>
<td class="sig"><a href="{signal_page_url}" style="color:var(--accent);font-weight:bold;text-decoration:none">{signal_id}</a> <a href="{report_url}" title="Signal 深度分析" style="text-decoration:none;font-size:14px">📊</a> <a href="{martin_url}" title="馬丁剖析法" style="text-decoration:none;font-size:14px">🔍</a></td>
<td>{r['total_symbols']}</td>
<td class="{score_cls}">{r['avg_score']}</td>
<td class="p4">{r['clean_pct']}%</td>
<td>{r['win_rate']:.1f}%</td>
<td>{r['total_trades']:,}</td>
<td class="g">${r['total_profit']:,.0f}<br><span style="font-size:0.75em;color:#888">{r['total_pips']:,.0f} pips</span></td>
<td class="m {dd_cls}">${r['max_dd']:,.0f}</td>
<td>{pf_str}</td>
<td><span class="tf">{r['timeframe']}</span></td>
<td class="m">{r['layer_info']}</td>
<td>{ea_tags}</td>
</tr>
'''
    
    html += '</tbody></table></div>'
    html += '<script>function toggleTheme(){var t=document.documentElement.getAttribute("data-theme");var n=t==="light"?"dark":"light";document.documentElement.setAttribute("data-theme",n);localStorage.setItem("tsa-theme",n);var b=document.getElementById("theme-toggle");b.textContent=n==="dark"?"🌙":"☀️"}(function(){var s=localStorage.getItem("tsa-theme")||"dark";document.documentElement.setAttribute("data-theme",s);var b=document.getElementById("theme-toggle");if(b)b.textContent=s==="dark"?"🌙":"☀️"})();</script>'
    html += '</body></html>'
    
    output_path = OUTPUT_DIR / 'signal_ranking_dde_v4.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # Also write to docs/ for GitHub Pages
    docs_path = BASE_DIR / 'docs' / 'signal_ranking_dde_v4.html'
    with open(docs_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    # Also create signal_ranking.html (alias)
    docs_alias = BASE_DIR / 'docs' / 'signal_ranking.html'
    with open(docs_alias, 'w', encoding='utf-8') as f:
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
