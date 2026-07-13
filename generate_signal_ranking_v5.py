#!/usr/bin/env python3
"""Generate Signal Ranking HTML (DDE v5 — 4 dimensions, ranking-based).

WR 15% + PF 20% + DD 25% + Martin 40%

Changes from v4:
  - Ranking-based scoring (percentile within all Signal×CCY)
  - 4 dimensions instead of 5
  - Profit Factor replaces Risk/Reward
  - Real data, no normalization distortion
"""
import sys
import os
import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent))

from dde_v5_scorer import run_v5_scoring, get_ea

BASE_DIR: Path = Path(__file__).parent
SAMPLES_DIR: Path = BASE_DIR / 'samples'
OUTPUT_DIR: Path = BASE_DIR / 'output'
DOCS_DIR: Path = BASE_DIR / 'docs'

EA_COLORS: Dict[str, tuple] = {
    'DW':      ('#4a148c', '#ce93d8'),
    'SMA':     ('#1b5e20', '#a5d6a7'),
    'SMAPro':  ('#1b5e20', '#c8e6c9'),
    'MKD':     ('#e65100', '#ffcc80'),
    'MKDPro':  ('#bf360c', '#ffab91'),
    'Flash':   ('#0d47a1', '#90caf9'),
    'S10':     ('#004d40', '#80cbc4'),
    'GC':      ('#0d47a1', '#90caf9'),
    'GS':      ('#1a237e', '#9fa8da'),
    'MAN':     ('#4527a0', '#b39ddb'),
    'UNK':     ('#333', 'var(--text2)'),
}

EA_OVERRIDES: Dict[str, str] = {
    '10344': 'Flash',
    '12173': 'SMA',
    '7999': 'MKD',
    '38678': 'DW',
}

from config import EA_MAP


def get_ea_style(ea_tag: str) -> str:
    """Return inline CSS style for EA tag badge."""
    first = ea_tag.split('/')[0]
    bg, fg = EA_COLORS.get(first, EA_COLORS['UNK'])
    return f'background:{bg};color:{fg}'


def get_score_class(score: float) -> str:
    """Return CSS class for DDE score."""
    if score >= 90: return 's90'
    elif score >= 80: return 's80'
    elif score >= 70: return 's70'
    elif score >= 60: return 's60'
    else: return 's0'


def get_dd_class(dd_value: float) -> str:
    """Return CSS class for drawdown value."""
    abs_dd = abs(dd_value)
    if abs_dd < 500: return 'dd-g'
    elif abs_dd < 2000: return 'dd-y'
    else: return 'dd-r'


def generate_html(all_results: List[Dict[str, Any]]) -> str:
    """Generate Signal Ranking HTML (v5).

    Aggregates per-Signal: average v5 score across all CCY pairs.

    Args:
        all_results: List of scoring result dicts from dde_v5_scorer.

    Returns:
        Complete HTML string.
    """

    # Separate scored vs red card
    scored: List[Dict[str, Any]] = [r for r in all_results if not r['red_card']]
    red: List[Dict[str, Any]] = [r for r in all_results if r['red_card']]

    # Aggregate per signal
    by_signal: Dict[str, List[Dict]] = defaultdict(list)
    for r in all_results:
        by_signal[r['signal_id']].append(r)

    signal_stats: List[Dict[str, Any]] = []
    for sid, rows in by_signal.items():
        valid_rows: List[Dict] = [r for r in rows if not r['red_card']]
        if not valid_rows:
            # All red cards
            signal_stats.append({
                'signal_id': sid,
                'ea': rows[0]['ea'],
                'avg_v5': 0,
                'total_symbols': len(rows),
                'clean_symbols': 0,
                'clean_pct': 0,
                'red_cards': len(rows),
                'total_trades': sum(r['trades'] for r in rows),
                'win_rate': round(sum(r['win_rate'] for r in rows) / len(rows), 1),
                'total_net_pips': round(sum(r['total_net_pips'] for r in rows), 1),
                'total_net_profit': round(sum(r['total_net_profit'] for r in rows), 1),
                'max_dd_pips': round(max(r['max_dd_pips'] for r in rows), 1),
                'pf': round(sum(r['pf'] for r in rows) / len(rows), 2),
                'wal': round(sum(r['wal'] for r in rows) / len(rows), 3),
            })
            continue

        avg_v5 = round(sum(r['dde_v5'] for r in valid_rows) / len(valid_rows), 1)
        total_trades = sum(r['trades'] for r in rows)
        avg_wr = round(sum(r['win_rate'] for r in rows) / len(rows), 1)
        total_pips = round(sum(r['total_net_pips'] for r in rows), 1)
        total_profit = round(sum(r['total_net_profit'] for r in rows), 1)
        max_dd = round(max(r['max_dd_pips'] for r in rows), 1)
        avg_pf = round(sum(r['pf'] for r in rows) / len(rows), 2)
        avg_wal = round(sum(r['wal'] for r in rows) / len(rows), 3)

        signal_stats.append({
            'signal_id': sid,
            'ea': rows[0]['ea'],
            'avg_v5': avg_v5,
            'total_symbols': len(rows),
            'clean_symbols': len(valid_rows),
            'clean_pct': round(len(valid_rows) / len(rows) * 100),
            'red_cards': len(rows) - len(valid_rows),
            'total_trades': total_trades,
            'win_rate': avg_wr,
            'total_net_pips': total_pips,
            'total_net_profit': total_profit,
            'max_dd_pips': max_dd,
            'pf': avg_pf,
            'wal': avg_wal,
        })

    signal_stats.sort(key=lambda x: x['avg_v5'], reverse=True)
    total_signals: int = len(signal_stats)

    scored_stats: List[Dict[str, Any]] = [s for s in signal_stats if s['clean_symbols'] > 0]
    avg_score: float = round(sum(s['avg_v5'] for s in scored_stats) / len(scored_stats), 1) if scored_stats else 0
    best_score: float = scored_stats[0]['avg_v5'] if scored_stats else 0
    worst_score: float = scored_stats[-1]['avg_v5'] if scored_stats else 0
    avg_clean_pct: float = round(sum(s['clean_pct'] for s in scored_stats) / len(scored_stats)) if scored_stats else 0
    today: str = datetime.now().strftime('%Y-%m-%d')

    # Build rows
    def make_rows(stats_list: List[Dict[str, Any]]) -> str:
        rows_html: str = ''
        for i, s in enumerate(stats_list, 1):
            rank: str = ''
            row_class: str = ''
            if i == 1: rank = '🥇'; row_class = ' class="top3"'
            elif i == 2: rank = '🥈'; row_class = ' class="top3"'
            elif i == 3: rank = '🥉'; row_class = ' class="top3"'
            else: rank = str(i)

            score_cls: str = get_score_class(s['avg_v5'])
            ea_style: str = get_ea_style(s['ea'])
            dd_cls: str = get_dd_class(s['max_dd_pips'])

            pf_str: str = 'Inf' if s['pf'] > 999 else f'{s["pf"]:.2f}'
            wr_str: str = f'{s["win_rate"]:.1f}%'
            pips_str: str = f'{s["total_net_pips"]:,.0f}p / ${s["total_net_profit"]:,.0f}'
            dd_str: str = f'{s["max_dd_pips"]:,.0f}p'
            wal_str: str = f'{s["wal"]:.2f}'

            clean_icon: str = '✅' if s['clean_pct'] >= 80 else ('⚠️' if s['clean_pct'] >= 50 else '🚫')

            # Use martin_v4 report (available for all signals)
            report_link: str = f"../reports/martin_v4_{s['signal_id']}.html"
            deep_link: str = f"../reports/index_{s['signal_id']}.html"
            deep_icon: str = '🔍' if (OUTPUT_DIR / f"index_{s['signal_id']}.html").exists() or (BASE_DIR / "docs" / "reports" / f"index_{s['signal_id']}.html").exists() else ''

            rows_html += f'''<tr{row_class}>
<td>{rank}</td>
<td><a href="https://signals.algoforest.com/signals/{s['signal_id']}">{s['signal_id']}</a> <a href="{report_link}">📊</a>{f' <a href="{deep_link}">🔍</a>' if deep_icon else ''}</td>
<td><span style="{ea_style};padding:1px 6px;border-radius:3px;font-size:0.8em;font-weight:bold">{s['ea']}</span></td>
<td>{s['total_symbols']}</td>
<td class="{score_cls}">{s['avg_v5']}</td>
<td>{clean_icon} {s['clean_pct']}%</td>
<td>{wr_str}</td>
<td>{s['total_trades']:,}</td>
<td>{pf_str}</td>
<td>{pips_str}</td>
<td class="{dd_cls}">{dd_str}</td>
<td>{wal_str}</td>
</tr>
'''
        return rows_html

    thead_html: str = '''<thead><tr>
<th data-col="idx" data-type="num">#<span class="arrow"></span></th>
<th data-col="signal" data-type="num">Signal<span class="arrow"></span></th>
<th data-col="ea" data-type="str">EA<span class="arrow"></span></th>
<th data-col="ccy" data-type="num">CCY<span class="arrow"></span></th>
<th data-col="dde" data-type="num"><span class="tooltip" data-tip="DDE v5 排名制分數 (WR 15% + PF 20% + DD 25% + Martin 40%)">DDE v5</span><span class="arrow"></span></th>
<th data-col="cb" data-type="num"><span class="tooltip" data-tip="Clean Board — 無 Red Card 嘅 CCY 佔比">CB</span><span class="arrow"></span></th>
<th data-col="wr" data-type="num">Win%<span class="arrow"></span></th>
<th data-col="trades" data-type="num">Trades<span class="arrow"></span></th>
<th data-col="pf" data-type="num">PF<span class="arrow"></span></th>
<th data-col="profit" data-type="num"><span class="tooltip" data-tip="總淨利潤（pips / USD）">Profit</span><span class="arrow"></span></th>
<th data-col="dd" data-type="num"><span class="tooltip" data-tip="最大回撤（pips）">Max DD</span><span class="arrow"></span></th>
<th data-col="wal" data-type="num">WAL<span class="arrow"></span></th>
</tr></thead>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🏆 Signal 排名 (v5)</title>
<style>
/* === Unified Theme System === */
:root{{--font-main:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Microsoft JhengHei',sans-serif;--radius:8px;--shadow:0 2px 8px rgba(0,0,0,0.12)}}
[data-theme="dark"]{{--bg:#0a0e17;--bg-card:#111520;--bg-hover:#1a1f2e;--text:#d0d0d0;--text2:#888;--primary:#FFD700;--accent:#64b5f6;--green:#4CAF50;--red:#FF5722;--yellow:#FFC107;--orange:#fd7e14;--border:#1e2433;--th-bg:#111520;--nav-bg:transparent;--grade-a:#4CAF50;--grade-b:#FFC107;--grade-c:#fd7e14;--grade-d:#FF5722;--header-from:#1a1f2e;--header-to:#0a0e17}}
[data-theme="light"]{{--bg:#f5f7fa;--bg-card:#ffffff;--bg-hover:#eef2f7;--text:#333;--text2:#666;--primary:#0f3460;--accent:#e94560;--green:#28a745;--red:#dc3545;--yellow:#ffc107;--orange:#fd7e14;--border:#ddd;--th-bg:#eef2f7;--nav-bg:rgba(0,0,0,0.03);--grade-a:#28a745;--grade-b:#ffc107;--grade-c:#fd7e14;--grade-d:#dc3545;--header-from:#0f3460;--header-to:#16213e}}
*{{transition:background-color .25s ease,color .25s ease,border-color .25s ease}}
.theme-toggle{{width:36px;height:36px;border:1px solid var(--border);border-radius:50%;background:var(--bg-card);color:var(--text);font-size:18px;cursor:pointer;display:flex;align-items:center;justify-content:center;box-shadow:var(--shadow);line-height:1;padding:0;flex-shrink:0}}.theme-toggle:hover{{background:var(--bg-hover);transform:scale(1.1)}}
.topnav{{display:flex;align-items:center;gap:12px;padding:10px 16px;background:var(--bg-card);border-bottom:1px solid var(--border);margin-bottom:16px;position:sticky;top:0;z-index:100}}
.topnav-logo{{font-weight:700;font-size:1em;color:var(--primary);text-decoration:none;margin-right:auto}}
.topnav-links{{display:flex;gap:10px;flex-wrap:wrap}}
.topnav-link{{color:var(--text2);text-decoration:none;font-size:.88em;font-weight:600;padding:4px 10px;border-radius:6px;transition:all .2s}}
.topnav-link:hover{{color:var(--primary);background:var(--bg-hover)}}
.topnav-link.active{{color:var(--primary);background:var(--bg-hover)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--font-main);background:var(--bg);color:var(--text);padding:16px;font-size:13px}}
h1{{font-size:1.3em;margin-bottom:4px;color:var(--primary)}}
.info-tip:hover .info-tip-text{{display:block}}
.sum{{background:var(--bg-card);border:1px solid var(--border);border-radius:var(--radius);padding:10px 14px;margin-bottom:12px;display:flex;flex-wrap:wrap;gap:20px}}
.sum .v{{font-size:1.3em;font-weight:bold;color:var(--primary)}}
.sum .l{{font-size:0.7em;color:var(--text2)}}
table{{width:100%;border-collapse:collapse;min-width:800px}}
th{{background:var(--th-bg);padding:8px 10px;text-align:left;border-bottom:2px solid var(--primary);color:var(--primary);font-size:0.8em;white-space:nowrap;cursor:pointer;user-select:none}}
th:hover{{background:var(--bg-hover)}}
th .arrow{{font-size:0.65em;margin-left:3px;opacity:0.3}}
th.asc .arrow{{opacity:1}}
th.desc .arrow{{opacity:1}}
td{{padding:6px 10px;border-bottom:1px solid var(--border);font-size:0.9em}}
tr:hover{{background:var(--bg-hover)}}
tr.top3{{background:rgba(255,215,0,0.03)}}
a{{color:var(--accent);text-decoration:none;font-weight:bold}}
a:hover{{text-decoration:underline}}
.container{{overflow-x:auto}}
.s90{{color:var(--green);font-weight:bold}}.s80{{color:#8BC34A;font-weight:bold}}.s70{{color:var(--yellow);font-weight:bold}}.s60{{color:var(--orange);font-weight:bold}}.s0{{color:var(--red);font-weight:bold}}
.dd-g{{color:var(--green)}}.dd-y{{color:var(--yellow)}}.dd-r{{color:var(--red)}}
.tooltip{{position:relative;cursor:help}}
.tooltip::after{{content:attr(data-tip);position:absolute;bottom:120%;left:50%;transform:translateX(-50%);background:var(--bg-hover);border:1px solid #333;color:#ddd;font-size:0.75em;padding:6px 10px;border-radius:6px;white-space:nowrap;opacity:0;pointer-events:none;transition:opacity 0.2s;z-index:99;font-weight:normal}}
.tooltip:hover::after{{opacity:1}}
select{{background:var(--bg-card);border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:6px;margin-bottom:12px;font-size:14px}}
input[type=text]{{background:var(--bg-card);border:1px solid var(--border);color:var(--text);padding:8px 12px;border-radius:6px;font-size:14px;width:160px}}
input[type=text]::placeholder{{color:#555}}
label{{color:var(--text2);font-size:0.9em;margin-left:12px}}
@media(max-width:768px){{body{{font-size:11px}}th,td{{padding:3px 5px}}}}
</style>
<link rel="stylesheet" href="../sidebar.css">
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
</script>
</head>
<body>
<div class="topnav">
<a href="./index.html" class="topnav-logo">🦀 TSA</a>
<div class="topnav-links">
<a href="./signal_ranking.html" class="topnav-link active">🏆 Signal 排名</a>
<a href="./admin/ccy_ranking.html" class="topnav-link">💱 CCY 排名</a>
<a href="./admin/symbol_ranking.html" class="topnav-link">📊 波幅波</a>
</div>
<button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()" title="切換亮/暗模式"></button>
</div>

<h1>🏆 Signal 排名</h1>
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:0.82em;color:var(--text2)">
<span>{today}</span>
<span class="info-tip" style="position:relative;display:inline-flex;cursor:pointer">
<span style="width:18px;height:18px;border-radius:50%;background:var(--bg-hover);border:1px solid var(--border);display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-style:italic;color:var(--text2)">i</span>
<span class="info-tip-text" style="display:none;position:absolute;top:24px;left:0;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:10px 14px;font-size:0.82em;line-height:1.6;z-index:50;white-space:nowrap;box-shadow:0 4px 16px rgba(0,0,0,0.3);color:var(--text)">
DDE v5 排名制評分（4維度）<br>
<b style="color:var(--primary)">WR</b> 15%（真實勝率）<br>
<b style="color:var(--primary)">PF</b> 20%（Profit Factor）<br>
<b style="color:var(--primary)">DD</b> 25%（真實 DD%）<br>
<b style="color:var(--primary)">Martin</b> 40%（WAL 層數）<br>
排名制：每個維度喺所有 Signal×CCY 排名後加權
</span>
</span>
</div>

<div class="sum">
<div><div class="v">{total_signals}</div><div class="l">Signals</div></div>
<div><div class="v">{avg_score}</div><div class="l">Avg DDE v5</div></div>
<div><div class="v">{best_score}</div><div class="l">Best</div></div>
<div><div class="v">{worst_score}</div><div class="l">Worst</div></div>
<div><div class="v">{avg_clean_pct}%</div><div class="l">Avg CB</div></div>
</div>

<div class="container"><table id="tbl">{thead_html}<tbody>
{make_rows(signal_stats)}
</tbody></table></div>

<script>
document.querySelectorAll('table[id^="tbl"]').forEach(function(table) {{
  table.querySelectorAll('thead th').forEach(function(th, i) {{
    th.addEventListener('click', function() {{
      var tbody = table.tBodies[0];
      var rows = Array.from(tbody.querySelectorAll('tr'));
      var dir = th.classList.contains('asc') ? 'desc' : 'asc';
      table.querySelectorAll('thead th').forEach(function(h) {{ h.classList.remove('asc', 'desc'); }});
      th.classList.add(dir);
      rows.sort(function(a, b) {{
        var va = a.cells[i].textContent.trim().replace(/[^0-9.\\-]/g, '');
        var vb = b.cells[i].textContent.trim().replace(/[^0-9.\\-]/g, '');
        var na = parseFloat(va) || 0;
        var nb = parseFloat(vb) || 0;
        if (!isNaN(na) && !isNaN(nb)) return dir === 'asc' ? na - nb : nb - na;
        return dir === 'asc' ? va.localeCompare(vb) : vb.localeCompare(va);
      }});
      rows.forEach(function(r) {{ tbody.appendChild(r); }});
    }});
  }});
}});
</script>
<script src="../sidebar.js"></script>
</body></html>'''

    return html


def main() -> None:
    """Main entry point: run v5 scoring and generate ranking HTML."""
    print("=" * 60)
    print("🦀 Signal Ranking Generator — DDE v5 (4 Dimensions, Ranking-based)")
    print("=" * 60)

    # Run v5 scoring (which saves to SQLite)
    all_results: List[Dict[str, Any]] = run_v5_scoring()

    if not all_results:
        print("❌ No results")
        return

    # Generate HTML
    html: str = generate_html(all_results)

    # Write outputs
    output_path: Path = OUTPUT_DIR / 'signal_ranking_dde_v5.html'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    # Also write to docs/ for GitHub Pages
    DOCS_DIR.mkdir(exist_ok=True)
    docs_path: Path = DOCS_DIR / 'signal_ranking_dde_v5.html'
    with open(docs_path, 'w', encoding='utf-8') as f:
        f.write(html)

    # Also create signal_ranking.html (main alias)
    docs_alias: Path = DOCS_DIR / 'signal_ranking.html'
    with open(docs_alias, 'w', encoding='utf-8') as f:
        f.write(html)

    # Also write to docs/admin/ for sidebar navigation (primary page)
    admin_path: Path = DOCS_DIR / 'admin' / 'signal_ranking.html'
    admin_path.parent.mkdir(parents=True, exist_ok=True)
    with open(admin_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ Generated: {output_path}")
    print(f"   Size: {len(html):,} bytes")


if __name__ == '__main__':
    main()
