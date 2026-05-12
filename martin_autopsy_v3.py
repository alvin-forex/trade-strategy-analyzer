#!/usr/bin/env python3
"""
Martin Autopsy V3 — 馬丁剖析法 V3
Absolute data analysis for martingale trading signals.

Generates a standalone HTML report with:
  Part 1: CCY × Direction detailed analysis table
  Part 2: MFE/MAE scatter plots (inline SVG)
  Part 3: A-grade+ TP/SL hybrid scheme
  Part 4: A-grade+ ranking board
  Part 5: Blacklist (Danger Score)
  Part 6: Recovery analysis
"""

import csv
import json
import os
import sys
import statistics
from collections import defaultdict
from datetime import datetime

# ──────────────────────────────────────────────
# 1. CSV Parser
# ──────────────────────────────────────────────

def parse_signal_csv(path):
    """Parse signal CSV into list of trade dicts."""
    trades = []
    with open(path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                net_pips = float(row.get('Net Pips', 0))
                net_profit = float(row.get('Net Profit', 0))
                lots = float(row.get('Lots', 0))
                max_pips = float(row.get('Max Pips', 0))       # MFE
                max_loss_pips = float(row.get('Max Loss Pips', 0))  # MAE (negative)
                hold_hours = float(row.get('Holding Time (Hours)', 0))
            except (ValueError, TypeError):
                continue

            trades.append({
                'symbol': row.get('Symbol', '').strip(),
                'direction': row.get('Type', '').strip().lower(),
                'lots': lots,
                'net_pips': net_pips,
                'net_profit': net_profit,
                'max_pips': max_pips,         # MFE
                'max_loss_pips': max_loss_pips, # MAE (negative)
                'hold_hours': hold_hours,
                'comment': row.get('Comment', '').strip(),
                'open_time': row.get('Open Time', '').strip(),
                'close_time': row.get('Close Time', '').strip(),
            })
    return trades


# ──────────────────────────────────────────────
# 2. Core Analysis Engine
# ──────────────────────────────────────────────

def analyze_layers(trades):
    """
    Group trades by (Symbol, Direction, Lots) and compute V3 metrics.
    Returns dict keyed by (symbol, direction, lots) with stats.
    """
    groups = defaultdict(list)
    for t in trades:
        key = (t['symbol'], t['direction'], t['lots'])
        groups[key].append(t)

    layer_stats = {}
    for (sym, direction, lots), tlist in groups.items():
        wins = [t for t in tlist if t['net_profit'] > 0]
        losses = [t for t in tlist if t['net_profit'] <= 0]
        count = len(tlist)
        win_count = len(wins)
        loss_count = len(losses)
        wr = (win_count / count * 100) if count > 0 else 0
        total_pnl = sum(t['net_profit'] for t in tlist)

        avg_win_pnl = (sum(t['net_profit'] for t in wins) / win_count) if win_count > 0 else 0
        avg_loss_pnl = (abs(sum(t['net_profit'] for t in losses) / loss_count)) if loss_count > 0 else 0
        avg_win_pips = (sum(t['net_pips'] for t in wins) / win_count) if win_count > 0 else 0
        avg_loss_pips = (abs(sum(t['net_pips'] for t in losses) / loss_count)) if loss_count > 0 else 0

        # EV$
        ev_dollar = (wr / 100 * avg_win_pnl) - ((1 - wr / 100) * avg_loss_pnl)

        # Odds
        odds_dollar = (avg_win_pnl / avg_loss_pnl) if avg_loss_pnl > 0 else 999
        odds_pips = (avg_win_pips / avg_loss_pips) if avg_loss_pips > 0 else 999

        # Hold time
        avg_hold = sum(t['hold_hours'] for t in tlist) / count if count > 0 else 0

        # MFE/MAE
        mfe_values = [t['max_pips'] for t in tlist]
        mae_values = [abs(t['max_loss_pips']) for t in tlist]

        avg_mfe = statistics.mean(mfe_values) if mfe_values else 0
        max_mfe = max(mfe_values) if mfe_values else 0
        med_mfe = statistics.median(mfe_values) if mfe_values else 0
        avg_mae = statistics.mean(mae_values) if mae_values else 0
        max_mae = max(mae_values) if mae_values else 0
        med_mae = statistics.median(mae_values) if mae_values else 0

        layer_stats[(sym, direction, lots)] = {
            'symbol': sym,
            'direction': direction,
            'lots': lots,
            'count': count,
            'win_count': win_count,
            'loss_count': loss_count,
            'win_rate': wr,
            'total_pnl': total_pnl,
            'avg_win_pnl': avg_win_pnl,
            'avg_loss_pnl': avg_loss_pnl,
            'avg_win_pips': avg_win_pips,
            'avg_loss_pips': avg_loss_pips,
            'ev_dollar': ev_dollar,
            'odds_dollar': odds_dollar,
            'odds_pips': odds_pips,
            'avg_hold': avg_hold,
            'avg_mfe': avg_mfe,
            'max_mfe': max_mfe,
            'med_mfe': med_mfe,
            'avg_mae': avg_mae,
            'max_mae': max_mae,
            'med_mae': med_mae,
            'trades': tlist,  # keep for scatter plots
        }

    return layer_stats


def compute_ccy_direction_stats(layer_stats):
    """
    Aggregate layer_stats into CCY×Direction summary.
    Returns dict keyed by (symbol, direction).
    """
    ccy_dir = defaultdict(lambda: {
        'layers': [],
        'trades': 0,
        'wins': 0,
        'total_pnl': 0,
        'max_depth': 0,
        'lot_set': set(),
    })

    for (sym, d, lots), stats in layer_stats.items():
        key = (sym, d)
        cd = ccy_dir[key]
        cd['layers'].append(stats)
        cd['trades'] += stats['count']
        cd['wins'] += stats['win_count']
        cd['total_pnl'] += stats['total_pnl']
        cd['lot_set'].add(lots)

    results = {}
    for (sym, d), cd in ccy_dir.items():
        layers = sorted(cd['layers'], key=lambda x: x['lots'])
        max_depth = len(cd['lot_set'])
        wr = (cd['wins'] / cd['trades'] * 100) if cd['trades'] > 0 else 0
        ev_per_layer = statistics.mean([l['ev_dollar'] for l in layers]) if layers else 0
        avg_win_pip = statistics.mean([l['avg_win_pips'] for l in layers]) if layers else 0
        avg_loss_pip = statistics.mean([l['avg_loss_pips'] for l in layers]) if layers else 0
        odds_d = statistics.mean([l['odds_dollar'] for l in layers]) if layers else 0
        odds_p = statistics.mean([l['odds_pips'] for l in layers]) if layers else 0
        avg_mfe = statistics.mean([l['avg_mfe'] for l in layers]) if layers else 0
        avg_mae = statistics.mean([l['avg_mae'] for l in layers]) if layers else 0
        max_mae = max([l['max_mae'] for l in layers]) if layers else 0

        results[(sym, d)] = {
            'symbol': sym,
            'direction': d,
            'trades': cd['trades'],
            'num_layers': len(layers),
            'max_depth': max_depth,
            'total_pnl': cd['total_pnl'],
            'win_rate': wr,
            'ev_per_layer': ev_per_layer,
            'avg_win_pip': avg_win_pip,
            'avg_loss_pip': avg_loss_pip,
            'odds_dollar': odds_d,
            'odds_pips': odds_p,
            'avg_mfe': avg_mfe,
            'avg_mae': avg_mae,
            'max_mae': max_mae,
            'layers': layers,
        }

    return results


def compute_layer_index(layer_stats):
    """Compute layer index for each (symbol, direction, lots)."""
    ccy_lots = defaultdict(set)
    for (sym, d, lots) in layer_stats:
        ccy_lots[(sym, d)].add(lots)

    idx_map = {}
    for (sym, d), lot_set in ccy_lots.items():
        sorted_lots = sorted(lot_set)
        for i, lot in enumerate(sorted_lots, 1):
            idx_map[(sym, d, lot)] = {
                'layer_idx': i,
                'max_depth': len(sorted_lots),
            }
    return idx_map


def compute_blacklist(ccy_dir_stats):
    """Compute danger score for each CCY×Direction."""
    blacklist = []
    for (sym, d), cd in ccy_dir_stats.items():
        danger = 0
        total_pnl = cd['total_pnl']
        avg_odds = cd['odds_dollar']
        wr = cd['win_rate']
        layers = cd['layers']
        avg_ev = cd['ev_per_layer']
        worst_ev = min(l['ev_dollar'] for l in layers) if layers else 0

        if total_pnl < 0:
            danger += abs(total_pnl) / 1000
        if avg_odds < 1.0:
            danger += 3
        if wr < 50:
            danger += 2
        if avg_ev < 0:
            danger += abs(avg_ev) / 10
        if worst_ev < -50:
            danger += 2

        if danger > 0:
            level = '💀 DEADLY' if danger > 5 else '⚠️ WARNING'
            blacklist.append({
                'symbol': sym,
                'direction': d,
                'danger_score': danger,
                'level': level,
                'total_pnl': total_pnl,
                'win_rate': wr,
                'odds': avg_odds,
                'worst_ev': worst_ev,
                'worst_layer': max(layers, key=lambda l: abs(l['ev_dollar'])) if layers else None,
            })

    blacklist.sort(key=lambda x: x['danger_score'], reverse=True)
    return blacklist


def compute_recovery(ccy_dir_stats, layer_stats):
    """Compute recovery analysis for each CCY×Direction."""
    recovery = []
    for (sym, d), cd in ccy_dir_stats.items():
        layers = cd['layers']
        if not layers:
            continue

        # Deepest layer = highest lots
        deepest = max(layers, key=lambda l: l['lots'])
        worst_loss = deepest['avg_loss_pnl'] if deepest['loss_count'] > 0 else 0

        # Best EV layer
        best_layer = max(layers, key=lambda l: l['ev_dollar'])
        best_ev = best_layer['ev_dollar']

        if best_ev > 0 and worst_loss > 0:
            recovery_trades = worst_loss / best_ev
        else:
            recovery_trades = 999

        if recovery_trades > 20 or best_ev <= 0:
            status = '🔴 無法恢復'
        elif recovery_trades > 5:
            status = '🟡 需時'
        else:
            status = '🟢 安全'

        recovery.append({
            'symbol': sym,
            'direction': d,
            'worst_loss': worst_loss,
            'best_ev': best_ev,
            'best_layer_lots': best_layer['lots'],
            'recovery_trades': recovery_trades,
            'status': status,
        })

    recovery.sort(key=lambda x: x['recovery_trades'])
    return recovery


def compute_tp_sl(ccy_dir_stats, layer_stats):
    """
    Compute TP/SL hybrid scheme for A-grade+ layers.
    Since we don't have external rating, we derive rating from EV$ and Odds$.
    """
    # Rate each layer
    for (sym, d, lots), ls in layer_stats.items():
        ev = ls['ev_dollar']
        odds = ls['odds_dollar']
        wr = ls['win_rate']
        count = ls['count']

        # Simple rating: based on EV$, Odds$, WR, count
        if count < 2:
            ls['rating'] = 'E'
        elif ev > 50 and odds > 2 and wr > 70:
            ls['rating'] = 'S+'
        elif ev > 20 and odds > 1.5 and wr > 65:
            ls['rating'] = 'S'
        elif ev > 0 and odds > 1 and wr > 55:
            ls['rating'] = 'A'
        elif ev > -20:
            ls['rating'] = 'B'
        elif ev > -50:
            ls['rating'] = 'C'
        else:
            ls['rating'] = 'D'

    # Get pair max MAE
    pair_max_mae = {}
    for (sym, d, lots), ls in layer_stats.items():
        key = (sym, d)
        if key not in pair_max_mae or ls['max_mae'] > pair_max_mae[key]:
            pair_max_mae[key] = ls['max_mae']

    # Build TP/SL for A+ layers
    tp_sl_entries = []
    for (sym, d, lots), ls in layer_stats.items():
        if ls['rating'] not in ('S+', 'S', 'A'):
            continue
        if ls['count'] < 2:
            continue

        tp = ls['avg_mfe']
        soft_sl = ls['avg_mae'] * 1.2
        hard_sl = pair_max_mae.get((sym, d), ls['max_mae']) * 1.3
        rr = (tp / soft_sl) if soft_sl > 0 else 0

        tp_sl_entries.append({
            'symbol': sym,
            'direction': d,
            'lots': lots,
            'rating': ls['rating'],
            'count': ls['count'],
            'win_rate': ls['win_rate'],
            'ev_dollar': ls['ev_dollar'],
            'odds_dollar': ls['odds_dollar'],
            'odds_pips': ls['odds_pips'],
            'tp': tp,
            'soft_sl': soft_sl,
            'hard_sl': hard_sl,
            'rr': rr,
            'total_pnl': ls['total_pnl'],
            'avg_hold': ls['avg_hold'],
            'avg_mfe': ls['avg_mfe'],
            'avg_mae': ls['avg_mae'],
        })

    # Sort: Rating desc, then EV$ desc
    rating_order = {'S+': 0, 'S': 1, 'A': 2}
    tp_sl_entries.sort(key=lambda x: (rating_order.get(x['rating'], 9), -x['ev_dollar']))
    return tp_sl_entries


# ──────────────────────────────────────────────
# 3. HTML Report Generator
# ──────────────────────────────────────────────

def generate_v3_html_report(ccy_dir_stats, layer_stats, blacklist, recovery, tp_sl, signal_id, output_path):
    """Generate the Martin Autopsy V3 HTML report."""

    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    # ── Part 1: CCY × Direction Table ──
    sorted_ccy = sorted(ccy_dir_stats.values(), key=lambda x: x['total_pnl'], reverse=True)

    part1_rows = ""
    for i, cd in enumerate(sorted_ccy, 1):
        pnl = cd['total_pnl']
        wr = cd['win_rate']
        ev = cd['ev_per_layer']
        odds = cd['odds_dollar']

        bg = '#d4edda' if pnl > 500 else ('#fff3cd' if pnl > 0 else '#f8d7da')
        ev_color = '#28a745' if ev > 0 else '#dc3545'
        odds_color = '#28a745' if odds > 1 else ('#ffc107' if odds > 0.5 else '#dc3545')

        part1_rows += f"""
        <tr style="background:{bg}">
            <td><strong>{i}</strong></td>
            <td><strong>{cd['symbol']}</strong></td>
            <td>{cd['direction'].upper()}</td>
            <td>{cd['trades']}</td>
            <td>{cd['num_layers']}</td>
            <td>{cd['max_depth']}</td>
            <td class="pnl">${pnl:,.2f}</td>
            <td>{wr:.1f}%</td>
            <td style="color:{ev_color};font-weight:bold">${ev:.2f}</td>
            <td>{cd['avg_win_pip']:.1f}</td>
            <td>{cd['avg_loss_pip']:.1f}</td>
            <td style="color:{odds_color}">{odds:.2f}x</td>
            <td>{cd['odds_pips']:.2f}x</td>
            <td class="mfe">{cd['avg_mfe']:.1f}</td>
            <td class="mae">{cd['avg_mae']:.1f}</td>
            <td class="mae-max">{cd['max_mae']:.1f}</td>
        </tr>"""

    # ── Part 2: MFE/MAE Scatter SVG ──
    scatter_svgs = ""
    for (sym, d), cd in sorted(ccy_dir_stats.items()):
        layers = cd['layers']
        if not layers:
            continue

        n_layers = len(layers)
        cols = min(4, n_layers)
        rows_count = (n_layers + cols - 1) // cols

        subplot_w = 220
        subplot_h = 180
        gap = 12
        total_w = cols * subplot_w + (cols - 1) * gap + 40
        total_h = rows_count * subplot_h + (rows_count - 1) * gap + 40

        svg_content = ""
        for idx, layer in enumerate(layers):
            col = idx % cols
            row = idx // cols
            ox = 20 + col * (subplot_w + gap)
            oy = 20 + row * (subplot_h + gap)

            # Subplot background
            svg_content += f'<rect x="{ox}" y="{oy}" width="{subplot_w}" height="{subplot_h}" fill="#0a0a1a" rx="4" stroke="#2a2a4a" stroke-width="1"/>'

            # Title
            title_text = f"L{layer['lots']:.2f} (n={layer['count']}) WR:{layer['win_rate']:.0f}%"
            svg_content += f'<text x="{ox + subplot_w/2}" y="{oy + 14}" text-anchor="middle" fill="#aab" font-size="9">{title_text}</text>'

            # Plot area within subplot
            px = ox + 30
            py = oy + 22
            pw = subplot_w - 40
            ph = subplot_h - 34

            # Axes
            svg_content += f'<line x1="{px}" y1="{py}" x2="{px}" y2="{py + ph}" stroke="#444" stroke-width="0.5"/>'
            svg_content += f'<line x1="{px}" y1="{py + ph/2}" x2="{px + pw}" y2="{py + ph/2}" stroke="#333" stroke-width="0.5" stroke-dasharray="2"/>'

            # Scale trades
            trades = layer['trades']
            if not trades:
                continue

            all_x = [t['net_pips'] for t in trades]
            all_y_mfe = [t['max_pips'] for t in trades]
            all_y_mae = [abs(t['max_loss_pips']) for t in trades]

            x_min = min(all_x) if all_x else -1
            x_max = max(all_x) if all_x else 1
            y_max = max(max(all_y_mfe) if all_y_mfe else 1, max(all_y_mae) if all_y_mae else 1)

            x_range = x_max - x_min if x_max != x_min else 1
            y_range = y_max if y_max > 0 else 1

            for t in trades:
                is_win = t['net_profit'] > 0
                color = '#28a745' if is_win else '#dc3545'

                # MAE dot
                mae_val = abs(t['max_loss_pips'])
                cx = px + ((t['net_pips'] - x_min) / x_range) * pw
                cy = py + ph - (mae_val / y_range) * ph * 0.45

                svg_content += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="2.5" fill="{color}" opacity="0.7"/>'

                # MFE triangle
                mfe_val = t['max_pips']
                cy_mfe = py + ph - (mfe_val / y_range) * ph * 0.45

                svg_content += f'<polygon points="{cx:.1f},{cy_mfe-4:.1f} {cx-3:.1f},{cy_mfe+2:.1f} {cx+3:.1f},{cy_mfe+2:.1f}" fill="{color}" opacity="0.5"/>'

        scatter_svgs += f"""
        <div class="scatter-card">
            <h3>{sym} {d.upper()} — MFE/MAE 散點圖</h3>
            <div class="scatter-legend">
                <span>🟢 Win MAE</span> <span>🔴 Loss MAE</span> <span>▲ MFE</span>
            </div>
            <svg viewBox="0 0 {total_w} {total_h}" style="width:100%;max-width:{total_w}px;">
                <rect width="100%" height="100%" fill="#0a0a1a" rx="8"/>
                {svg_content}
            </svg>
        </div>"""

    # ── Part 3: TP/SL Table ──
    part3_rows = ""
    for i, entry in enumerate(tp_sl, 1):
        rating = entry['rating']
        rating_color = {'S+': '#FFD700', 'S': '#28a745', 'A': '#3498db'}.get(rating, '#666')
        rr = entry['rr']
        rr_color = '#28a745' if rr > 3 else ('#ffc107' if rr > 1.5 else '#dc3545')

        part3_rows += f"""
        <tr>
            <td><span class="rating-badge" style="background:{rating_color}">{rating}</span></td>
            <td><strong>{entry['symbol']}</strong></td>
            <td>{entry['direction'].upper()}</td>
            <td>L{entry['lots']:.2f}</td>
            <td>{entry['count']}</td>
            <td>{entry['win_rate']:.1f}%</td>
            <td class="ev">${entry['ev_dollar']:.2f}</td>
            <td>{entry['odds_dollar']:.2f}x</td>
            <td class="tp">{entry['tp']:.1f}</td>
            <td class="sl-soft">{entry['soft_sl']:.1f}</td>
            <td class="sl-hard">{entry['hard_sl']:.1f}</td>
            <td style="color:{rr_color};font-weight:bold">{rr:.1f}x</td>
        </tr>"""

    # ── Part 4: Ranking ──
    # Re-use tp_sl sorted data
    part4_rows = ""
    for i, entry in enumerate(tp_sl, 1):
        rating = entry['rating']
        rating_color = {'S+': '#FFD700', 'S': '#28a745', 'A': '#3498db'}.get(rating, '#666')
        pnl = entry['total_pnl']
        pnl_color = '#28a745' if pnl > 0 else '#dc3545'

        part4_rows += f"""
        <tr>
            <td><strong>#{i}</strong></td>
            <td><span class="rating-badge" style="background:{rating_color}">{rating}</span></td>
            <td>{entry['symbol']}</td>
            <td>{entry['direction'].upper()}</td>
            <td>L{entry['lots']:.2f}</td>
            <td>{entry['count']}</td>
            <td>{entry['win_rate']:.1f}%</td>
            <td class="ev">${entry['ev_dollar']:.2f}</td>
            <td>{entry['odds_dollar']:.2f}x</td>
            <td>{entry['odds_pips']:.2f}x</td>
            <td class="tp">{entry['tp']:.1f}</td>
            <td class="sl-soft">{entry['soft_sl']:.1f}</td>
            <td class="sl-hard">{entry['hard_sl']:.1f}</td>
            <td style="color:{pnl_color}">${pnl:.2f}</td>
            <td>{entry['avg_hold']:.1f}h</td>
        </tr>"""

    # ── Part 5: Blacklist ──
    part5_rows = ""
    for bl in blacklist:
        level = bl['level']
        pnl = bl['total_pnl']
        wl = bl.get('worst_layer')

        part5_rows += f"""
        <tr>
            <td>{level}</td>
            <td><strong>{bl['symbol']}</strong></td>
            <td>{bl['direction'].upper()}</td>
            <td class="danger-score">{bl['danger_score']:.1f}</td>
            <td class="pnl">${pnl:,.2f}</td>
            <td>{bl['win_rate']:.1f}%</td>
            <td>{bl['odds']:.2f}x</td>
            <td>{f"L{wl['lots']:.2f} ${wl['ev_dollar']:.0f}" if wl else 'N/A'}</td>
        </tr>"""

    # ── Part 6: Recovery ──
    part6_rows = ""
    for r in recovery:
        rt = r['recovery_trades']
        rt_display = f"{rt:.1f}" if rt < 999 else "∞"

        part6_rows += f"""
        <tr>
            <td>{r['status']}</td>
            <td><strong>{r['symbol']}</strong></td>
            <td>{r['direction'].upper()}</td>
            <td>${r['worst_loss']:.2f}</td>
            <td class="ev">${r['best_ev']:.2f}</td>
            <td>L{r['best_layer_lots']:.2f}</td>
            <td>{rt_display}</td>
        </tr>"""

    # ── Full HTML ──
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>👑 馬丁剖析法 V3 — Signal #{signal_id}</title>
<style>
:root {{
    --bg: #0d1117;
    --card: #161b22;
    --card2: #1c2333;
    --border: #30363d;
    --text: #e6edf3;
    --text2: #8b949e;
    --primary: #58a6ff;
    --accent: #f78166;
    --green: #3fb950;
    --yellow: #d29922;
    --orange: #db6d28;
    --red: #f85149;
    --gold: #FFD700;
    --radius: 10px;
}}
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang TC', sans-serif; background: var(--bg); color: var(--text); padding: 12px; font-size: 13px; }}
.container {{ max-width: 1100px; margin: 0 auto; }}

/* Header */
.header {{ text-align: center; padding: 28px 20px; background: linear-gradient(135deg, #0d1117 0%, #1a1f36 50%, #0d1117 100%); border-radius: var(--radius); margin-bottom: 20px; border: 1px solid var(--border); }}
.header h1 {{ font-size: 1.6em; color: var(--gold); margin-bottom: 4px; }}
.header .sub {{ color: var(--text2); font-size: 0.85em; }}
.header .signal-id {{ color: var(--primary); font-weight: 700; }}

/* Cards */
.card {{ background: var(--card); border-radius: var(--radius); padding: 20px; margin-bottom: 20px; border: 1px solid var(--border); }}
.card h2 {{ font-size: 1.15em; color: var(--primary); margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid var(--border); }}
.card h2 .emoji {{ margin-right: 6px; }}

/* Tables */
.table-wrap {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
table {{ width: 100%; border-collapse: collapse; font-size: 0.82em; }}
th {{ background: #21262d; color: var(--text); padding: 8px 6px; text-align: center; white-space: nowrap; border-bottom: 2px solid var(--primary); font-size: 0.9em; }}
td {{ padding: 6px; border-bottom: 1px solid var(--border); text-align: center; white-space: nowrap; }}
tr:hover td {{ background: rgba(88,166,255,0.06); }}

/* Specific column styles */
.pnl {{ font-weight: 700; }}
.ev {{ font-weight: 700; color: var(--green); }}
.mfe {{ color: var(--green); }}
.mae {{ color: var(--orange); }}
.mae-max {{ color: var(--red); font-weight: 700; }}
.tp {{ color: var(--green); font-weight: 600; }}
.sl-soft {{ color: var(--orange); }}
.sl-hard {{ color: var(--red); font-weight: 600; }}
.danger-score {{ color: var(--red); font-weight: 700; font-size: 1.1em; }}

/* Rating badge */
.rating-badge {{ display: inline-block; padding: 2px 8px; border-radius: 10px; font-weight: 700; font-size: 0.85em; color: #000; }}

/* Scatter */
.scatter-card {{ background: #0a0a1a; border-radius: var(--radius); padding: 16px; margin-bottom: 16px; border: 1px solid #2a2a4a; }}
.scatter-card h3 {{ color: var(--primary); margin-bottom: 8px; font-size: 1em; }}
.scatter-legend {{ display: flex; gap: 16px; margin-bottom: 10px; font-size: 0.8em; color: var(--text2); }}

/* Summary boxes */
.summary-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; margin-bottom: 16px; }}
.summary-box {{ background: var(--card2); border-radius: 8px; padding: 12px; text-align: center; border: 1px solid var(--border); }}
.summary-box .val {{ font-size: 1.3em; font-weight: 700; }}
.summary-box .lbl {{ font-size: 0.7em; color: var(--text2); margin-top: 2px; }}

/* Tabs */
.tabs {{ display: flex; gap: 0; border-bottom: 2px solid var(--border); margin-bottom: 16px; overflow-x: auto; }}
.tab {{ padding: 10px 16px; cursor: pointer; font-size: 0.9em; font-weight: 600; color: var(--text2); border-bottom: 3px solid transparent; transition: all 0.2s; white-space: nowrap; }}
.tab:hover {{ color: var(--primary); }}
.tab.active {{ color: var(--primary); border-bottom-color: var(--accent); }}
.tab-panel {{ display: none; }}
.tab-panel.active {{ display: block; }}

/* Footer */
.footer {{ text-align: center; color: var(--text2); font-size: 0.75em; margin-top: 24px; padding: 12px 0; border-top: 1px solid var(--border); }}

/* Responsive */
@media (max-width: 600px) {{
    th, td {{ padding: 4px 2px; font-size: 0.75em; }}
    .summary-grid {{ grid-template-columns: repeat(2, 1fr); }}
}}
</style>
</head>
<body>
<div class="container">

<!-- Header -->
<div class="header">
    <h1>👑 馬丁剖析法 V3</h1>
    <div class="sub">Martin Autopsy V3 — 絕對數據分析 | Signal <span class="signal-id">#{signal_id}</span> | {now}</div>
</div>

<!-- Overview Stats -->
<div class="summary-grid">
    <div class="summary-box"><div class="val" style="color:var(--primary)">{len(layer_stats)}</div><div class="lbl">層級組合</div></div>
    <div class="summary-box"><div class="val" style="color:var(--primary)">{len(ccy_dir_stats)}</div><div class="lbl">CCY×Dir 組合</div></div>
    <div class="summary-box"><div class="val" style="color:var(--green)">{sum(1 for l in layer_stats.values() if l['ev_dollar']>0)}</div><div class="lbl">正 EV 層</div></div>
    <div class="summary-box"><div class="val" style="color:var(--red)">{sum(1 for l in layer_stats.values() if l['ev_dollar']<=0)}</div><div class="lbl">負 EV 層</div></div>
    <div class="summary-box"><div class="val" style="color:var(--green)">{sum(cd['total_pnl'] for cd in ccy_dir_stats.values()):,.0f}</div><div class="lbl">總 P&L $</div></div>
    <div class="summary-box"><div class="val" style="color:var(--accent)">{len(blacklist)}</div><div class="lbl">黑名單</div></div>
    <div class="summary-box"><div class="val" style="color:var(--gold)">{len(tp_sl)}</div><div class="lbl">A級+ 層</div></div>
    <div class="summary-box"><div class="val" style="color:var(--red)">{sum(1 for r in recovery if '無法恢復' in r['status'])}</div><div class="lbl">無法恢復</div></div>
</div>

<!-- Tabs -->
<div class="tabs">
    <div class="tab active" onclick="switchTab('part1')">📊 Part 1: CCY×Dir</div>
    <div class="tab" onclick="switchTab('part2')">🔬 Part 2: MFE/MAE</div>
    <div class="tab" onclick="switchTab('part3')">🎯 Part 3: TP/SL</div>
    <div class="tab" onclick="switchTab('part4')">🏅 Part 4: 排行</div>
    <div class="tab" onclick="switchTab('part5')">💀 Part 5: 黑名單</div>
    <div class="tab" onclick="switchTab('part6')">🔄 Part 6: 恢復力</div>
</div>

<!-- Part 1 -->
<div class="tab-panel active" id="part1">
<div class="card">
    <h2><span class="emoji">📊</span>Part 1：CCY × Direction 詳細分析表</h2>
    <p style="color:var(--text2);font-size:0.82em;margin-bottom:12px;">按 Total$ 降序排列 | EV$ = (WR×AvgWin$) − ((1−WR)×AvgLoss$) | Odds$ = AvgWin$ / AvgLoss$</p>
    <div class="table-wrap">
    <table>
    <tr>
        <th>#</th><th>CCY</th><th>Dir</th><th>Trades</th><th>Layers</th><th>MaxD</th>
        <th>Total$</th><th>WR%</th><th>EV$/L</th><th>AvgWin Pip</th><th>AvgLoss Pip</th>
        <th>Odds$</th><th>OddsPip</th><th>AvgMFE</th><th>AvgMAE</th><th>MaxMAE</th>
    </tr>
    {part1_rows}
    </table>
    </div>
</div>
</div>

<!-- Part 2 -->
<div class="tab-panel" id="part2">
<div class="card">
    <h2><span class="emoji">🔬</span>Part 2：MFE/MAE 散點圖</h2>
    <p style="color:var(--text2);font-size:0.82em;margin-bottom:12px;">
        ● 圓點 = MAE（最大不利偏移）| ▲ 三角 = MFE（最大有利偏移）| 綠色 = Win | 紅色 = Loss
    </p>
    {scatter_svgs}
</div>
</div>

<!-- Part 3 -->
<div class="tab-panel" id="part3">
<div class="card">
    <h2><span class="emoji">🎯</span>Part 3：A級以上 TP/SL 匯總（混合方案）</h2>
    <div style="background:var(--card2);padding:12px;border-radius:8px;margin-bottom:12px;font-size:0.82em;color:var(--text2);border:1px solid var(--border);">
        <strong style="color:var(--text)">SL 設計原理：</strong><br>
        🟠 <strong>Soft SL</strong> = Avg MAE × 1.2（正常波動止損，避免加碼）<br>
        🔴 <strong>Hard SL</strong> = Pair Max MAE × 1.3（極端情況防爆倉）<br>
        🟢 <strong>TP</strong> = Avg MFE（平均最大有利偏移）<br>
        <strong>R:R</strong> = TP / Soft SL | &gt;1.5x 最低可接受 | &gt;3.0x 優秀
    </div>
    <div class="table-wrap">
    <table>
    <tr><th>Rating</th><th>CCY</th><th>Dir</th><th>Layer</th><th>Trades</th><th>WR%</th><th>EV$</th><th>Odds$</th><th>TP(pip)</th><th>Soft SL</th><th>Hard SL</th><th>R:R</th></tr>
    {part3_rows}
    </table>
    </div>
</div>
</div>

<!-- Part 4 -->
<div class="tab-panel" id="part4">
<div class="card">
    <h2><span class="emoji">🏅</span>Part 4：A級以上排行榜</h2>
    <p style="color:var(--text2);font-size:0.82em;margin-bottom:12px;">排序：Rating 降序 → EV$ 降序</p>
    <div class="table-wrap">
    <table>
    <tr><th>#</th><th>Rating</th><th>CCY</th><th>Dir</th><th>Layer</th><th>Trades</th><th>WR%</th><th>EV$</th><th>Odds$</th><th>OddsPip</th><th>TP</th><th>SoftSL</th><th>HardSL</th><th>Total$</th><th>AvgHold</th></tr>
    {part4_rows}
    </table>
    </div>
</div>
</div>

<!-- Part 5 -->
<div class="tab-panel" id="part5">
<div class="card">
    <h2><span class="emoji">💀</span>Part 5：黑名單（Danger Score）</h2>
    <div style="background:var(--card2);padding:12px;border-radius:8px;margin-bottom:12px;font-size:0.82em;color:var(--text2);border:1px solid var(--border);">
        <strong style="color:var(--text)">Danger Score 計算：</strong><br>
        ① 總虧損 / 1000 &nbsp; ② Odds$ &lt; 1.0 → +3 &nbsp; ③ WR &lt; 50% → +2 &nbsp; ④ Avg EV 為負 → |EV|/10 &nbsp; ⑤ 最差單層 EV &lt; -$50 → +2<br>
        💀 DEADLY &gt; 5 | ⚠️ WARNING 1-5
    </div>
    <div class="table-wrap">
    <table>
    <tr><th>級別</th><th>CCY</th><th>Dir</th><th>Danger</th><th>Total$</th><th>WR%</th><th>Odds$</th><th>最差層</th></tr>
    {part5_rows}
    </table>
    </div>
</div>
</div>

<!-- Part 6 -->
<div class="tab-panel" id="part6">
<div class="card">
    <h2><span class="emoji">🔄</span>Part 6：恢復力分析</h2>
    <p style="color:var(--text2);font-size:0.82em;margin-bottom:12px;">
        場景：如果最深層馬丁被 Hard SL 止損，要用最佳 EV 層級贏幾多次先追得返？
        <br>恢復次數 = 最深層平均虧損 / 最佳層 EV$
    </p>
    <div class="table-wrap">
    <table>
    <tr><th>狀態</th><th>CCY</th><th>Dir</th><th>最深層虧損</th><th>最佳 EV$</th><th>最佳層</th><th>恢復次數</th></tr>
    {part6_rows}
    </table>
    </div>
</div>
</div>

<!-- Footer -->
<div class="footer">
    👑 Martin Autopsy V3 | 絕對數據 · 無百分比評分 | Signal #{signal_id} | {now}
</div>

</div>

<script>
function switchTab(tabId) {{
    document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    event.target.classList.add('active');
}}
</script>
</body>
</html>"""

    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"✅ 馬丁剖析法 V3 報告已生成：{output_path}")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────

def main():
    csv_path = sys.argv[1] if len(sys.argv) > 1 else 'downloads/signal_11141.csv'

    # Extract signal ID from filename
    import re
    basename = os.path.basename(csv_path)
    m = re.search(r'(?:signal_|page-)(\d+)', basename)
    signal_id = m.group(1) if m else basename.replace('.csv', '')

    output_path = sys.argv[2] if len(sys.argv) > 2 else f'reports/martin_autopsy_v3_{signal_id}.html'

    print(f"👑 馬丁剖析法 V3")
    print(f"   CSV: {csv_path}")
    print(f"   Signal ID: {signal_id}")

    # 1. Parse
    print("\n[1/5] 解析 CSV...")
    trades = parse_signal_csv(csv_path)
    print(f"   ✓ {len(trades)} 筆交易")

    # Filter VPS02 trades if present
    vps_trades = [t for t in trades if 'VPS02' in t['comment']]
    if vps_trades:
        print(f"   ✓ 篩選 VPS02: {len(vps_trades)} 筆")
        trades = vps_trades

    # 2. Layer analysis
    print("\n[2/5] 層級分析...")
    layer_stats = analyze_layers(trades)
    print(f"   ✓ {len(layer_stats)} 個層級組合")

    # 3. CCY×Direction aggregation
    print("\n[3/5] CCY×Direction 匯總...")
    ccy_dir_stats = compute_ccy_direction_stats(layer_stats)
    print(f"   ✓ {len(ccy_dir_stats)} 個 CCY×Dir 組合")

    # 4. Derived analysis
    print("\n[4/5] 計算 TP/SL、黑名單、恢復力...")
    tp_sl = compute_tp_sl(ccy_dir_stats, layer_stats)
    blacklist = compute_blacklist(ccy_dir_stats)
    recovery = compute_recovery(ccy_dir_stats, layer_stats)
    print(f"   ✓ A級+: {len(tp_sl)} 層 | 黑名單: {len(blacklist)} | 恢復分析: {len(recovery)}")

    # 5. Generate report
    print("\n[5/5] 生成 HTML 報告...")
    generate_v3_html_report(ccy_dir_stats, layer_stats, blacklist, recovery, tp_sl, signal_id, output_path)


if __name__ == '__main__':
    main()
