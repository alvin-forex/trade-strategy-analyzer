#!/usr/bin/env python3
"""
Generate standalone Signal Report V2 with Martin V3 analysis + Quant charts.
Usage: python generate_signal_report_v2.py <signal_id> <csv_path> <output_path>
"""
import csv
import json
import math
import os
import sys
from datetime import datetime
from collections import defaultdict

# ─── Global Baselines ──────────────────────────────────────
GLOBAL_TP_BASELINES = {
    'L1': 48.0, 'L2': 88.5, 'L3': 74.6, 'L4': 109.3,
    'L5': 109.6, 'L6': 128.7, 'L7': 138.6, 'L8': 150.2, 'L9+': 163.4,
}
GLOBAL_SL_BASELINES = {
    'L1': 76.4, 'L2': 115.8, 'L3': 97.5, 'L4': 143.3,
    'L5': 129.7, 'L6': 126.7, 'L7': 109.0, 'L8': 92.1, 'L9+': 73.8,
}
GLOBAL_BASELINES = {
    'floor': 5.00, 'min_sample': 30,
    'profit': {
        'L1': {'p50': 3.12, 'p75': 6.5}, 'L2': {'p50': 14.56, 'p75': 36.4},
        'L3': {'p50': 6.32, 'p75': 18.22}, 'L4': {'p50': 19.79, 'p75': 52.01},
        'L5': {'p50': 41.09, 'p75': 83.15}, 'L6': {'p50': 61.74, 'p75': 118.22},
        'L7': {'p50': 118.1, 'p75': 196.84}, 'L8': {'p50': 187.64, 'p75': 310.81},
        'L9+': {'p50': 334.19, 'p75': 600.37},
    },
    'lose': {
        'L1': {'p50': 2.96, 'p75': 6.17}, 'L2': {'p50': 13.83, 'p75': 34.58},
        'L3': {'p50': 6.00, 'p75': 17.31}, 'L4': {'p50': 18.80, 'p75': 49.41},
        'L5': {'p50': 39.04, 'p75': 78.99}, 'L6': {'p50': 58.65, 'p75': 112.31},
        'L7': {'p50': 112.19, 'p75': 187.00}, 'L8': {'p50': 178.26, 'p75': 295.27},
        'L9+': {'p50': 317.48, 'p75': 570.35},
    }
}

LEVEL_ORDER = lambda x: (99 if x == 'L9+' else int(x[1:]))


def load_trades(csv_path):
    trades = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            t = row.get('Type', '').strip().lower()
            if t not in ('buy', 'sell'):
                continue
            try:
                trade = {
                    'symbol': row.get('Symbol', '').strip(),
                    'direction': t,
                    'lots': abs(float(row.get('Lots', 0))),
                    'net_profit': float(row.get('Net Profit', 0)),
                    'net_pips': float(row.get('Net Pips', 0)),
                    'max_profit': float(row.get('Max Profit', 0)),
                    'max_loss': float(row.get('Max Loss', 0)),
                    'mfe': float(row.get('Max Pips', 0)),
                    'mae': abs(float(row.get('Max Loss Pips', 0))),
                    'max_pips': float(row.get('Max Pips', 0)),
                    'max_loss_pips': abs(float(row.get('Max Loss Pips', 0))),
                    'commission': float(row.get('Commission', 0)),
                    'swap': float(row.get('Swap', 0)),
                    'holding_hours': float(row.get('Holding Time (Hours)', '0').strip() or '0'),
                }
                if trade['symbol']:
                    trades.append(trade)
            except (ValueError, TypeError):
                continue
    return trades


def assign_lot_levels(trades):
    unique_lots = sorted(set(round(t['lots'], 4) for t in trades))
    lot_to_level = {}
    for i, lot in enumerate(unique_lots):
        lot_to_level[lot] = 'L9+' if i >= 8 else f'L{i+1}'
    for t in trades:
        t['lot_level'] = lot_to_level.get(round(t['lots'], 4), 'L1')
    return lot_to_level


def percentile(data, pct):
    if not data:
        return 0
    s = sorted(data)
    return s[min(int(len(s) * pct), len(s) - 1)]


def v3_rating(stats):
    wr = stats.get('win_rate', 0)
    ev = stats.get('ev', 0)
    odds = min(stats.get('odds_dollar', 0), stats.get('odds_pips', 0))
    count = stats.get('count', 0)
    score = 0
    if wr >= 80: score += 30
    elif wr >= 70: score += 25
    elif wr >= 60: score += 18
    elif wr >= 50: score += 10
    else: score += max(0, wr / 5)
    if ev >= 20: score += 30
    elif ev >= 10: score += 25
    elif ev >= 5: score += 18
    elif ev >= 0: score += 8
    else: score += max(0, 8 + ev / 2)
    if odds >= 3: score += 20
    elif odds >= 2: score += 15
    elif odds >= 1.5: score += 10
    elif odds >= 1: score += 5
    else: score += max(0, odds * 5)
    if count >= 100: score += 15
    elif count >= 50: score += 12
    elif count >= 20: score += 8
    elif count >= 10: score += 5
    else: score += max(0, count)
    if score >= 85: return 'S+'
    if score >= 70: return 'S'
    if score >= 55: return 'A'
    if score >= 40: return 'B'
    if score >= 25: return 'C'
    return 'D'


def compute_level_stats(trades_list):
    """Compute stats for a group of trades (one level)."""
    n = len(trades_list)
    if n == 0:
        return None
    wins = [t for t in trades_list if t['net_profit'] > 0]
    losses = [t for t in trades_list if t['net_profit'] <= 0]
    wr = len(wins) / n * 100
    total_pnl = sum(t['net_profit'] for t in trades_list)
    avg_win = sum(t['net_profit'] for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t['net_profit'] for t in losses) / len(losses)) if losses else 0
    ev = (wr / 100 * avg_win) - ((1 - wr / 100) * avg_loss)
    avg_win_pips = sum(t['net_pips'] for t in wins) / len(wins) if wins else 0
    avg_loss_pips = abs(sum(t['net_pips'] for t in losses) / len(losses)) if losses else 0
    odds_d = avg_win / avg_loss if avg_loss > 0 else 999
    odds_p = avg_win_pips / avg_loss_pips if avg_loss_pips > 0 else 999
    avg_hold = sum(t['holding_hours'] for t in trades_list) / n
    avg_mfe = sum(t['mfe'] for t in trades_list) / n
    max_mfe = max(t['mfe'] for t in trades_list) if trades_list else 0
    avg_mae = sum(t['mae'] for t in trades_list) / n
    max_mae = max(t['mae'] for t in trades_list) if trades_list else 0
    stats = {
        'count': n, 'win_count': len(wins), 'loss_count': len(losses),
        'win_rate': round(wr, 1), 'total_pnl': round(total_pnl, 2),
        'ev': round(ev, 2), 'avg_win': round(avg_win, 2), 'avg_loss': round(avg_loss, 2),
        'avg_win_pips': round(avg_win_pips, 1), 'avg_loss_pips': round(avg_loss_pips, 1),
        'odds_dollar': round(min(odds_d, 999), 2), 'odds_pips': round(min(odds_p, 999), 2),
        'avg_hold': round(avg_hold, 1),
        'avg_mfe': round(avg_mfe, 1), 'max_mfe': round(max_mfe, 1),
        'avg_mae': round(avg_mae, 1), 'max_mae': round(max_mae, 1),
        'trades': trades_list,
    }
    stats['rating'] = v3_rating(stats)
    return stats


def compute_martin_depth(trades):
    classic = [t for t in trades if t['net_profit'] > 0 and t['net_pips'] < 0]
    total_profit = sum(t['net_profit'] for t in trades if t['net_profit'] > 0)
    martin_profit = sum(t['net_profit'] for t in classic)
    dep = (martin_profit / total_profit * 100) if total_profit > 0 else 0

    levels = defaultdict(list)
    for t in trades:
        levels[t['lot_level']].append(t)
    lv_results = {}
    for lv in sorted(levels.keys(), key=LEVEL_ORDER):
        lt = levels[lv]
        lm = [t for t in lt if t['net_profit'] > 0 and t['net_pips'] < 0]
        n, nm = len(lt), len(lm)
        lv_results[lv] = {
            'trades': n, 'martin_count': nm,
            'trigger_rate': round(nm / n * 100, 1) if n else 0,
            'avg_depth_pips': round(sum(t['mae'] for t in lm) / nm, 1) if nm else 0,
            'max_depth_pips': round(max((t['mae'] for t in lm), default=0), 1),
        }
    return {'dependency': round(dep, 1), 'martin_count': len(classic), 'levels': lv_results}


def compute_worthiness(trades):
    if len(trades) < 5:
        return None
    wins = [t for t in trades if t['net_profit'] > 0]
    losses = [t for t in trades if t['net_profit'] <= 0]
    n = len(trades)
    w = len(wins) / n
    avg_w = sum(t['net_profit'] for t in wins) / len(wins) if wins else 0
    avg_l = abs(sum(t['net_profit'] for t in losses) / len(losses)) if losses else 0
    rr = avg_w / avg_l if avg_l > 0 else 999
    exp_r = (w * rr) - (1 - w)
    kelly = (w - (1 - w) / rr) if rr > 0 else 0
    be_wr = 1 / (1 + rr) if rr > 0 else 1.0
    sm = w - be_wr
    sg = '🟢 穩健' if sm > 0.15 else '🟡 一般' if sm > 0.05 else '🔴 危險'
    return {
        'trades': n, 'win_rate': round(w * 100, 1), 'avg_win': round(avg_w, 2),
        'avg_loss': round(avg_l, 2), 'rr_ratio': round(rr, 2),
        'expectancy': round(exp_r, 3), 'kelly': round(kelly * 100, 1),
        'safety_grade': sg,
        'total_profit': round(sum(t['net_profit'] for t in trades), 2),
    }


def compute_danger_score(all_trades, ccy_dir_levels):
    """Compute blacklist with 5-factor danger score."""
    results = []
    for (sym, d), lvls in ccy_dir_levels.items():
        all_t = []
        for k, v in lvls.items():
            if k == '_meta':
                continue
            all_t.extend(v['trades'])
        if not all_t:
            continue
        total_pnl = sum(t['net_profit'] for t in all_t)
        total_wins = sum(1 for t in all_t if t['net_profit'] > 0)
        wr = total_wins / len(all_t) * 100

        danger = 0
        # Factor 1: Net loss
        if total_pnl < 0:
            danger += min(abs(total_pnl) / 500, 5)
        # Factor 2: Low odds
        odds_list = []
        for k, v in lvls.items():
            if k == '_meta':
                continue
            if v['avg_loss'] > 0:
                odds_list.append(v['avg_win'] / v['avg_loss'])
        avg_odds = sum(odds_list) / len(odds_list) if odds_list else 0
        if avg_odds < 1.0:
            danger += 3
        # Factor 3: Low WR
        if wr < 50:
            danger += 2
        # Factor 4: Negative avg EV
        avg_ev = sum(v['ev'] for k, v in lvls.items() if k != '_meta') / max(1, len([k for k in lvls if k != '_meta']))
        if avg_ev < 0:
            danger += abs(avg_ev) / 10
        # Factor 5: Worst layer EV
        worst_ev = min(v['ev'] for k, v in lvls.items() if k != '_meta') if any(k != '_meta' for k in lvls) else 0
        if worst_ev < -50:
            danger += 2

        if danger >= 1:
            level = '💀 DEADLY' if danger > 5 else '⚠️ WARNING' if danger > 2 else '⚡ CAUTION'
            results.append({
                'symbol': sym, 'direction': d,
                'total_pnl': round(total_pnl, 2), 'wr': round(wr, 1),
                'avg_odds': round(avg_odds, 2), 'danger': round(danger, 1),
                'level': level,
            })
    results.sort(key=lambda x: -x['danger'])
    return results


def compute_recovery(ccy_dir_levels):
    results = []
    for (sym, d), lvls in ccy_dir_levels.items():
        lv_keys = [k for k in lvls if k != '_meta']
        if not lv_keys:
            continue
        deepest = max(lv_keys, key=LEVEL_ORDER)
        worst_loss = lvls[deepest]['avg_loss'] if lvls[deepest]['loss_count'] > 0 else (lvls[deepest]['count'] * 10)
        best_ev_lv = max(lv_keys, key=lambda x: lvls[x].get('ev', 0))
        best_ev = lvls[best_ev_lv]['ev']
        recovery_trades = math.ceil(worst_loss / best_ev) if best_ev > 0 else 999
        total_trades = sum(lvls[k]['count'] for k in lv_keys)
        freq_month = total_trades / 3
        recovery_days = round(recovery_trades / freq_month * 30) if freq_month > 0 else 999
        if recovery_trades > 20 or best_ev <= 0:
            status, text = '🔴', '無法恢復'
        elif recovery_trades >= 5:
            status, text = '🟡', f'需時 ({recovery_trades}次)'
        else:
            status, text = '🟢', f'安全 ({recovery_trades}次)'
        results.append({
            'symbol': sym, 'direction': d,
            'deepest_layer': deepest, 'worst_loss': round(worst_loss, 2),
            'best_ev_layer': best_ev_lv, 'best_ev': round(best_ev, 2),
            'recovery_trades': recovery_trades, 'recovery_days': int(recovery_days),
            'status': status, 'status_text': text,
        })
    results.sort(key=lambda x: x['recovery_trades'])
    return results


def get_effective_percentiles(sig_p50, sig_p75, sig_n, level_key, baseline_type='profit'):
    gb = GLOBAL_BASELINES[baseline_type].get(level_key, GLOBAL_BASELINES['profit']['L1'])
    g_p50, g_p75 = gb['p50'], gb['p75']
    floor = GLOBAL_BASELINES['floor']
    min_sample = GLOBAL_BASELINES['min_sample']
    if sig_p50 is not None and sig_p75 is not None:
        if sig_n is not None and sig_n < min_sample:
            w = sig_n / min_sample
            eff_p50 = w * sig_p50 + (1 - w) * g_p50
            eff_p75 = w * sig_p75 + (1 - w) * g_p75
        else:
            eff_p50, eff_p75 = sig_p50, sig_p75
        eff_p50 = max(eff_p50, floor)
        eff_p75 = max(eff_p75, eff_p50 + 0.01)
    else:
        eff_p50 = max(g_p50, floor)
        eff_p75 = max(g_p75, eff_p50 + 0.01)
    return eff_p50, eff_p75


def compute_signal_percentiles(trades, level_key, baseline_type='profit'):
    if baseline_type == 'profit':
        profits = sorted([t['net_profit'] for t in trades if t['net_profit'] > 0])
    else:
        profits = sorted([t['net_profit'] for t in trades if abs(t.get('mae', 0)) >= 10 and t['net_profit'] > 0])
    n = len(profits)
    if n < 5:
        return None, None, n
    return profits[n // 2], profits[3 * n // 4], n


def alpha_capture_score(avg_profit, eff_p50, eff_p75):
    if avg_profit <= 0:
        return 0
    elif avg_profit < eff_p50:
        return (avg_profit / eff_p50) * 70
    elif avg_profit < eff_p75:
        return 70 + ((avg_profit - eff_p50) / (eff_p75 - eff_p50)) * 30
    else:
        bonus = ((avg_profit - eff_p75) / (eff_p75 - eff_p50)) * 10
        return 100 + min(bonus, 20)


def dde_score(triggered_trades):
    if not triggered_trades:
        return 0
    dd_ratios = []
    for t in triggered_trades:
        ml = abs(t.get('max_loss_pips', 0)) or abs(t.get('mae', 0))
        pp = abs(t.get('max_pips', 0)) or abs(t.get('mfe', 0))
        if t['net_profit'] > 0:
            pp = max(pp, abs(t.get('net_pips', 0)))
        if pp > 0:
            dd_ratios.append(min(2.0, ml / pp))
        else:
            dd_ratios.append(2.0)
    avg_dd = sum(dd_ratios) / len(dd_ratios)
    return max(0, min(100, 100 - avg_dd * 50))


def analyze_cop(trades, wait_levels, level_key):
    sig_p50, sig_p75, sig_n = compute_signal_percentiles(trades, level_key, 'profit')
    eff_p50, eff_p75 = get_effective_percentiles(sig_p50, sig_p75, sig_n, level_key, 'profit')
    results = {}
    for wp in wait_levels:
        triggered = [t for t in trades if t['net_profit'] > 0 and abs(t.get('max_pips', 0)) >= wp]
        total_wins = sum(1 for t in trades if t['net_profit'] > 0)
        tr = len(triggered) / total_wins if total_wins > 0 else 0
        avg_p = sum(t['net_profit'] for t in triggered) / len(triggered) if triggered else 0
        ts = min(tr * 100, 100)
        ps = alpha_capture_score(avg_p, eff_p50, eff_p75)
        ds = dde_score(triggered)
        ws = ts * 0.4 + ps * 0.4 + ds * 0.2
        results[wp] = {
            'triggered': len(triggered), 'total_wins': total_wins,
            'trigger_rate': tr, 'avg_profit': round(avg_p, 2),
            'weighted': round(ws, 1),
            'rating': '⭐⭐⭐⭐' if ws >= 80 else '⭐⭐⭐' if ws >= 60 else '⭐⭐' if ws >= 40 else '⭐',
        }
    return results


def analyze_col(trades, wait_levels, level_key):
    sig_p50, sig_p75, sig_n = compute_signal_percentiles(trades, level_key, 'lose')
    eff_p50, eff_p75 = get_effective_percentiles(sig_p50, sig_p75, sig_n, level_key, 'lose')
    results = {}
    for wp in wait_levels:
        triggered = 0
        recovered = 0
        total_pnl = 0
        for t in trades:
            if abs(t.get('mae', 0)) >= wp:
                triggered += 1
                if t['net_profit'] > 0:
                    recovered += 1
                    total_pnl += t['net_profit']
        rr = recovered / triggered if triggered > 0 else 0
        avg_p = total_pnl / recovered if recovered > 0 else 0
        rs = rr * 100
        ps = alpha_capture_score(avg_p, eff_p50, eff_p75)
        ws = rs * 0.5 + ps * 0.5
        results[wp] = {
            'triggered': triggered, 'recovered': recovered,
            'recovery_rate': rr, 'avg_profit': round(avg_p, 2),
            'weighted': round(ws, 1),
            'rating': '⭐⭐⭐⭐' if ws >= 80 else '⭐⭐⭐' if ws >= 60 else '⭐⭐' if ws >= 40 else '⭐',
        }
    return results


def compute_copy_trade_suggestion(worthiness, martin, levels_cop_col):
    if not worthiness:
        return None
    exp = worthiness['expectancy']
    wr = worthiness['win_rate']
    md = martin['dependency']

    best_cop = (0, 0, '')
    best_col = (0, 0, '')
    for lv, data in levels_cop_col.items():
        for wp, r in data.get('cop', {}).items():
            if r['weighted'] > best_cop[0]:
                best_cop = (r['weighted'], wp, lv)
        for wp, r in data.get('col', {}).items():
            if r['weighted'] > best_col[0]:
                best_col = (r['weighted'], wp, lv)

    if exp < 0.1 or md > 70:
        rec, strat, conf, cls, reason = '❌ 不建議 Copy', 'N/A', '🔴 低', 'low', ''
        rp = []
        if exp < 0.1: rp.append(f'期望值過低 ({exp:.3f}R)')
        if md > 70: rp.append(f'馬丁依賴度過高 ({md:.1f}%)')
        reason = '、'.join(rp)
    elif md < 30 and wr > 60 and best_cop[0] > 0:
        rec = '✅ 建議 CoP (Copy on Profit)'
        strat, wait = 'CoP', best_cop[1]
        reason = f'馬丁依賴度低 ({md:.1f}%)、勝率 {wr:.1f}%'
        conf = '🟢 高' if exp > 0.5 and md < 20 and wr > 80 else '🟡 中'
        cls = 'high' if '高' in conf else 'medium'
    elif md >= 30 and best_col[0] > 0:
        rec = '⚠️ 建議 CoL (Copy on Lose)'
        strat, wait = 'CoL', best_col[1]
        reason = f'馬丁依賴度 {md:.1f}%，適合等待回撤後跟單'
        conf = '🟡 中' if exp > 0.3 and md < 50 else '🔴 低'
        cls = 'medium' if '中' in conf else 'low'
    elif best_cop[0] > 0:
        rec = '⚠️ 可嘗試 CoP'
        strat, wait = 'CoP', best_cop[1]
        reason = f'期望值 {exp:.3f}R、勝率 {wr:.1f}%'
        conf, cls = '🟡 中', 'medium'
    else:
        rec, strat, conf, cls, reason = '❌ 不建議 Copy', 'N/A', '🔴 低', 'low', '缺乏有效的 CoP/CoL 觸發數據'

    return {
        'recommendation': rec, 'strategy': strat, 'confidence': conf, 'confidence_class': cls,
        'reason': reason, 'expectancy': exp, 'win_rate': wr, 'martin_dep': md,
        'best_cop_score': round(best_cop[0], 1), 'best_col_score': round(best_col[0], 1),
        'best_cop_level': best_cop[2], 'best_col_level': best_col[2],
        'wait_pips': best_cop[1] if 'CoP' in strat else best_col[1] if 'CoL' in strat else 0,
    }


def generate_report(signal_id, csv_path, output_path):
    print(f"Loading trades from {csv_path}...")
    trades = load_trades(csv_path)
    print(f"  {len(trades)} trades loaded")

    lot_to_level = assign_lot_levels(trades)
    print(f"  Lot levels: {lot_to_level}")

    # Group by (CCY, Direction)
    ccy_dir_trades = defaultdict(list)
    for t in trades:
        ccy_dir_trades[(t['symbol'], t['direction'])].append(t)

    ccy_dir_levels = {}
    for (sym, d) in sorted(ccy_dir_trades.keys()):
        cd_trades = ccy_dir_trades[(sym, d)]
        level_groups = defaultdict(list)
        for t in cd_trades:
            level_groups[t['lot_level']].append(t)

        ccy_dir_levels[(sym, d)] = {}
        for lv in sorted(level_groups.keys(), key=LEVEL_ORDER):
            stats = compute_level_stats(level_groups[lv])
            if stats:
                ccy_dir_levels[(sym, d)][lv] = stats

        # Meta: worthiness, martin, CoP/CoL, suggestion
        worth = compute_worthiness(cd_trades)
        martin = compute_martin_depth(cd_trades)

        levels_cop_col = {}
        for lv in sorted(level_groups.keys(), key=LEVEL_ORDER):
            lt = level_groups[lv]
            cop = analyze_cop(lt, [5, 10, 15, 20], lv)
            col = analyze_col(lt, [10, 15, 20, 25], lv)
            levels_cop_col[lv] = {'cop': cop, 'col': col}

        suggestion = compute_copy_trade_suggestion(worth, martin, levels_cop_col)
        ccy_dir_levels[(sym, d)]['_meta'] = {
            'worthiness': worth, 'martin': martin, 'suggestion': suggestion,
            'levels_cop_col': levels_cop_col, 'total_trades': len(cd_trades),
        }

    blacklist = compute_danger_score(trades, ccy_dir_levels)
    recovery = compute_recovery(ccy_dir_levels)

    # ─── Build HTML ─────────────────────────────
    total_trades = len(trades)
    total_pnl = sum(t['net_profit'] for t in trades)
    total_wins = sum(1 for t in trades if t['net_profit'] > 0)
    wr = total_wins / total_trades * 100 if total_trades else 0
    avg_hold = sum(t['holding_hours'] for t in trades) / total_trades if total_trades else 0
    # Profit Factor
    gross_profit = sum(t['net_profit'] for t in trades if t['net_profit'] > 0)
    gross_loss = abs(sum(t['net_profit'] for t in trades if t['net_profit'] <= 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999
    # Max DD (simplified)
    running = 0
    peak = 0
    max_dd = 0
    for t in sorted(trades, key=lambda x: x.get('holding_hours', 0)):
        running += t['net_profit']
        peak = max(peak, running)
        max_dd = min(max_dd, running - peak)

    ccy_dirs = sorted(ccy_dir_levels.keys())

    # Serialize data for JS
    chart_data = {}
    scatter_data = {}
    tpsl_chart_data = {}
    idx = 0
    for (sym, d) in ccy_dirs:
        all_lvls = {k: v for k, v in ccy_dir_levels[(sym, d)].items() if k != '_meta'}
        # TP/SL bar chart data
        tpsl_items = []
        for lv in sorted(all_lvls.keys(), key=LEVEL_ORDER):
            v = all_lvls[lv]
            # Max MAE across this CCY×Dir
            pair_max_mae = max(all_lvls[l]['max_mae'] for l in all_lvls)
            tpsl_items.append({
                'level': lv, 'count': v['count'], 'wr': v['win_rate'],
                'rating': v['rating'],
                'tp': v['avg_mfe'],
                'soft_sl': round(v['avg_mae'] * 1.2, 1),
                'hard_sl': round(pair_max_mae * 1.3, 1),
            })
        tpsl_chart_data[str(idx)] = tpsl_items

        # Scatter data per level
        scatter_items = {}
        for lv in sorted(all_lvls.keys(), key=LEVEL_ORDER):
            pts = []
            for t in all_lvls[lv]['trades']:
                pts.append({
                    'net_pips': round(t['net_pips'], 1),
                    'mfe': round(t['mfe'], 1),
                    'mae': round(t['mae'], 1),
                    'is_win': t['net_profit'] > 0,
                })
            scatter_items[lv] = {
                'points': pts,
                'count': all_lvls[lv]['count'],
                'wr': all_lvls[lv]['win_rate'],
            }
        scatter_data[str(idx)] = scatter_items
        chart_data[str(idx)] = {'sym': sym, 'dir': d}
        idx += 1

    scatter_json = json.dumps(scatter_data)
    tpsl_json = json.dumps(tpsl_chart_data)
    chart_map_json = json.dumps(chart_data)

    # Build CCY sections HTML
    ccy_sections = ''
    for ci, (sym, d) in enumerate(ccy_dirs):
        all_lvls = {k: v for k, v in ccy_dir_levels[(sym, d)].items() if k != '_meta'}
        meta = ccy_dir_levels[(sym, d)]['_meta']
        worth = meta['worthiness']
        martin = meta['martin']
        sug = meta['suggestion']
        cop_col = meta['levels_cop_col']

        total_pnl_cd = sum(v['total_pnl'] for v in all_lvls.values())
        total_trades_cd = sum(v['count'] for v in all_lvls.values())
        total_wins_cd = sum(v['win_count'] for v in all_lvls.values())
        wr_cd = total_wins_cd / total_trades_cd * 100 if total_trades_cd else 0
        avg_ev_cd = sum(v['ev'] for v in all_lvls.values()) / len(all_lvls) if all_lvls else 0
        avg_odds_cd = sum(v['odds_dollar'] for v in all_lvls.values()) / len(all_lvls) if all_lvls else 0

        # A. Summary Card
        section = f'''
        <div class="ccy-section">
          <div class="ccy-header" data-idx="{ci}" onclick="toggleCCY(this)">
            <span><b>{sym}</b> {d.upper()} — {total_trades_cd} trades · ${total_pnl_cd:+,.2f} · WR {wr_cd:.1f}% · EV ${avg_ev_cd:+.2f}</span>
            <span class="arrow">▶</span>
          </div>
          <div class="ccy-body">
            <div class="cards" style="margin-bottom:12px">
              <div class="card"><div class="v">{total_trades_cd}</div><div class="l">Trades</div></div>
              <div class="card"><div class="v {'pos' if wr_cd>50 else 'neg'}">{wr_cd:.1f}%</div><div class="l">WR%</div></div>
              <div class="card"><div class="v {'pos' if total_pnl_cd>=0 else 'neg'}">${total_pnl_cd:+,.0f}</div><div class="l">Total$</div></div>
              <div class="card"><div class="v">{len(all_lvls)}</div><div class="l">Layers</div></div>
              <div class="card"><div class="v {'pos' if avg_ev_cd>=0 else 'neg'}">${avg_ev_cd:+.2f}</div><div class="l">EV$/L</div></div>
              <div class="card"><div class="v">{avg_odds_cd:.2f}x</div><div class="l">Avg Odds$</div></div>
            </div>'''

        # Copy Trade Suggestion
        if sug:
            section += f'''
            <div class="sug-card {sug['confidence_class']}">
              <div class="sug-title">{sug['recommendation']}</div>
              <div class="sug-grid">
                <div><span class="lbl">策略</span><br>{sug['strategy']}</div>
                <div><span class="lbl">Wait Pips</span><br>{sug['wait_pips']}</div>
                <div><span class="lbl">信心度</span><br>{sug['confidence']}</div>
                <div><span class="lbl">期望值</span><br>{sug['expectancy']:.3f}R</div>
                <div><span class="lbl">勝率</span><br>{sug['win_rate']:.1f}%</div>
                <div><span class="lbl">馬丁依賴</span><br>{sug['martin_dep']:.1f}%</div>
                <div><span class="lbl">Best CoP</span><br>{sug['best_cop_score']} ({sug['best_cop_level']})</div>
                <div><span class="lbl">Best CoL</span><br>{sug['best_col_score']} ({sug['best_col_level']})</div>
              </div>
              <div class="sug-reason">{sug['reason']}</div>
            </div>'''

        # Worthiness
        if worth:
            section += f'''
            <div class="sec" style="margin-bottom:10px">
              <div class="sec-h">值博率分析 <span class="help-icon">?<span class="help-tip">評估呢個信號嘅值博率：勝率(WR%)、平均贏/輸金額、R:R 比率、Kelly 倉位比例。E(R) > 0 代表長期正期望值。安全邊際：🟢穩健 / 🟡一般 / 🔴危險。</span></span></div>
              <div class="sec-b"><div class="tw"><table>
                <thead><tr><th>Trades</th><th>WR%</th><th>AvgW$</th><th>AvgL$</th><th>R:R</th><th>E(R)</th><th>Kelly%</th><th>安全邊際</th><th>Total$</th></tr></thead>
                <tbody><tr>
                  <td>{worth['trades']}</td><td>{worth['win_rate']}%</td>
                  <td class="pos">${worth['avg_win']}</td><td class="neg">${worth['avg_loss']}</td>
                  <td>{worth['rr_ratio']}</td><td class="{'pos' if worth['expectancy']>=0 else 'neg'}">{worth['expectancy']}</td>
                  <td>{worth['kelly']}%</td><td>{worth['safety_grade']}</td>
                  <td class="{'pos' if worth['total_profit']>=0 else 'neg'}">${worth['total_profit']:+,.2f}</td>
                </tr></tbody></table></div></div>
            </div>'''

        # B. Level Data Table
        section += '''
            <div class="sec" style="margin-bottom:10px">
              <div class="sec-h">各層級數據 (L1-L9+) <span class="help-icon">?<span class="help-tip">按馬丁加倉層級拆分嘅詳細數據。L1=首倉，L2=第一次加倉，如此類推。重點睇：Count（樣本數夠唔夠）、WR%（越高越好）、EV$（每層期望值）、AvgMFE/AvgMAE（平均最大浮盈/浮虧）、Rating（S/A/B/C/D）。</span></span></div>
              <div class="sec-b"><div class="tw"><table>
                <thead><tr><th>Level</th><th>Count</th><th>WR%</th><th>Total$</th><th>EV$</th><th>Odds$</th><th>AvgWin Pip</th><th>AvgLoss Pip</th><th>AvgMFE</th><th>AvgMAE</th><th>MaxMAE</th><th>AvgHold</th><th>Rating</th></tr></thead>
                <tbody>'''
        for lv in sorted(all_lvls.keys(), key=LEVEL_ORDER):
            v = all_lvls[lv]
            rt_color = {'S+': '#0f3460', 'S': '#28a745', 'A': '#3498db', 'B': '#9b59b6', 'C': '#f39c12', 'D': '#dc3545'}.get(v['rating'], '#999')
            section += f'''<tr>
              <td><b>{lv}</b></td><td>{v['count']}</td><td>{v['win_rate']}%</td>
              <td class="{'pos' if v['total_pnl']>=0 else 'neg'}">${v['total_pnl']:+,.2f}</td>
              <td class="{'pos' if v['ev']>=0 else 'neg'}">${v['ev']:+.2f}</td>
              <td>{v['odds_dollar']}x</td>
              <td class="pos">{v['avg_win_pips']}</td><td class="neg">{v['avg_loss_pips']}</td>
              <td class="pos">{v['avg_mfe']}</td><td class="neg">{v['avg_mae']}</td><td class="neg">{v['max_mae']}</td>
              <td>{v['avg_hold']}h</td>
              <td><span class="rtg" style="background:{rt_color};color:#000">{v['rating']}</span></td>
            </tr>'''
        section += '</tbody></table></div></div></div>'

        # C. TP/SL Bar Chart
        section += f'''
            <div class="sec" style="margin-bottom:10px">
              <div class="sec-h">TP/SL 條形圖 <span class="help-icon">?<span class="help-tip">可視化各層級嘅建議 TP 同 SL。綠色=TP（Take Profit，基於 Avg MFE）、橙色=Soft SL（MAE×1.2，較寬鬆嘅止損）、紅色=Hard SL（MaxMAE×1.3，最嚴格嘅止損）。根據你嘅風險承受能力揀用邊個 SL。</span></span></div>
              <div class="sec-b">
                <canvas id="tpsl_{ci}" style="width:100%;height:{max(200, len(all_lvls)*40)}px"></canvas>
                <div class="legend">
                  <span class="l-green">TP (Avg MFE)</span>
                  <span class="l-orange">Soft SL (MAE×1.2)</span>
                  <span class="l-red">Hard SL (MaxMAE×1.3)</span>
                </div>
              </div>
            </div>'''

        # D. MFE/MAE Scatter Plots (per level)
        section += f'''
            <div class="sec" style="margin-bottom:10px">
              <div class="sec-h">MFE/MAE 散點圖 <span class="help-icon">?<span class="help-tip">每個圓點代表一筆交易。綠色=贏、紅色=輸。X軸=MAE（最大浮虧），Y軸=MFE（最大浮盈）。滑鼠移到圓點上可睇詳細數值。用呢個圖判斷 TP/SL 嘅合理位置。</span></span></div>
              <div class="sec-b">
                <div class="scatter-grid">'''
        for lv in sorted(all_lvls.keys(), key=LEVEL_ORDER):
            v = all_lvls[lv]
            section += f'''<div class="scatter-card">
                <div class="title">L{LEVEL_ORDER(lv) if lv != 'L9+' else '9+'} (n={v['count']}) WR:{v['win_rate']}%</div>
                <canvas id="sc_{ci}_{lv}" style="width:100%;height:160px"></canvas>
              </div>'''
        section += '</div></div></div>'

        # Martin Depth
        if martin:
            section += f'''
            <div class="sec" style="margin-bottom:10px">
              <div class="sec-h">馬丁層級深度 · 依賴度 {martin['dependency']:.1f}% <span class="help-icon">?<span class="help-tip">顯示馬丁（加倉）策略嘅實際觸發情況。Martin#=加倉次數、觸發率=幾常需要加倉、Avg深度/Max深度=加倉後嘅平均/最大浮虧。依賴度越低越好，0% 代表唔需要馬丁都贏。</span></span></div>
              <div class="sec-b"><div class="tw"><table>
                <thead><tr><th>Layer</th><th>Trades</th><th>Martin#</th><th>觸發率</th><th>Avg深度(pip)</th><th>Max深度(pip)</th></tr></thead>
                <tbody>'''
            for lv_name in sorted(martin['levels'].keys(), key=LEVEL_ORDER):
                lm = martin['levels'][lv_name]
                section += f'''<tr>
                  <td>{lv_name}</td><td>{lm['trades']}</td><td>{lm['martin_count']}</td>
                  <td>{lm['trigger_rate']}%</td>
                  <td>{lm['avg_depth_pips']}</td><td>{lm['max_depth_pips']}</td>
                </tr>'''
            section += '</tbody></table></div></div></div>'

        # DDE CoP/CoL Table
        section += '''
            <div class="sec" style="margin-bottom:10px">
              <div class="sec-h">DDE CoP/CoL 評分 <span class="help-icon">?<span class="help-tip">CoP=Copy on Profit（等行咗 N pip 先跟贏）、CoL=Copy on Lose（浮虧 N pip 時抄底跟入）。Triggered=歷史上有幾多筆符合條件。Score 綜合評分：≥80⭐⭐⭐⭐值得跟、60-80⭐⭐⭐可以考慮、<60⭐⭐風險高。揀最高分嘅 Wait Pip + Level 做跟單策略。</span></span></div>
              <div class="sec-b"><div class="tw"><table>
                <thead><tr><th>Level</th><th>Type</th><th>Wait</th><th>Triggered</th><th>Rate</th><th>Avg$</th><th>Score</th><th>Rating</th></tr></thead>
                <tbody>'''
        for lv in sorted(cop_col.keys(), key=LEVEL_ORDER):
            cd = cop_col[lv]
            for wp, r in sorted(cd.get('cop', {}).items()):
                section += f'''<tr><td>{lv}</td><td style="color:#28a745">CoP</td><td>{wp}pip</td>
                  <td>{r['triggered']}/{r['total_wins']}</td><td>{r['trigger_rate']:.0%}</td>
                  <td>${r['avg_profit']:.2f}</td><td><b>{r['weighted']}</b></td><td>{r['rating']}</td></tr>'''
            for wp, r in sorted(cd.get('col', {}).items()):
                section += f'''<tr><td>{lv}</td><td style="color:#f39c12">CoL</td><td>{wp}pip</td>
                  <td>{r['triggered']}</td><td>{r['recovery_rate']:.0%}</td>
                  <td>${r['avg_profit']:.2f}</td><td><b>{r['weighted']}</b></td><td>{r['rating']}</td></tr>'''
        section += '</tbody></table></div></div></div>'

        # Blacklist entry for this CCY
        bl_entry = next((b for b in blacklist if b['symbol'] == sym and b['direction'] == d), None)
        if bl_entry:
            section += f'''
            <div class="sec" style="margin-bottom:10px">
              <div class="sec-h" style="background:linear-gradient(135deg,#dc3545,#a71d2a)">⚠️ Danger Score <span class="help-icon">?<span class="help-tip">綜合風險評分（1-5分）。考慮因素：勝率、最大虧損、馬丁依賴度、恢復能力。分數越高風險越大，≥4 分要特別小心。</span></span></div>
              <div class="sec-b">
                <div style="font-size:14px;margin-bottom:6px">{bl_entry['level']}</div>
                <div>Danger: <b>{bl_entry['danger']}</b> | WR: {bl_entry['wr']}% | Odds: {bl_entry['avg_odds']}</div>
              </div>
            </div>'''

        # Recovery
        rec_entry = next((r for r in recovery if r['symbol'] == sym and r['direction'] == d), None)
        if rec_entry:
            section += f'''
            <div class="sec" style="margin-bottom:10px">
              <div class="sec-h">恢復力分析 <span class="help-icon">?<span class="help-tip">當交易去到最深層（如 L4/L5）時嘅恢復能力。狀態：🟢安全/🟡注意/🔴危險。恢復次數=從深層成功返回嘅次數。最佳EV層=邊層嘅期望值最高。</span></span></div>
              <div class="sec-b">
                <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:6px;font-size:11px">
                  <div><span class="lbl">狀態</span><br>{rec_entry['status']} {rec_entry['status_text']}</div>
                  <div><span class="lbl">最深層</span><br>{rec_entry['deepest_layer']}</div>
                  <div><span class="lbl">最差損失</span><br class="neg">${rec_entry['worst_loss']:.2f}</div>
                  <div><span class="lbl">最佳EV層</span><br>{rec_entry['best_ev_layer']} (${rec_entry['best_ev']:+.2f})</div>
                  <div><span class="lbl">恢復次數</span><br><b>{rec_entry['recovery_trades'] if rec_entry['recovery_trades']<999 else '∞'}</b></div>
                  <div><span class="lbl">恢復天數</span><br>{rec_entry['recovery_days'] if rec_entry['recovery_days']<999 else '∞'}天</div>
                </div>
              </div>
            </div>'''

        section += '</div></div>'  # ccy-body, ccy-section
        ccy_sections += section

    # Blacklist summary
    bl_html = ''
    if blacklist:
        bl_html = '<div class="tw"><table><thead><tr><th>危險度</th><th>Danger</th><th>CCY</th><th>Dir</th><th>Total$</th><th>WR%</th><th>Odds</th></tr></thead><tbody>'
        for b in blacklist:
            bl_html += f'''<tr><td>{b['level']}</td><td><b>{b['danger']}</b></td><td><b>{b['symbol']}</b></td><td>{b['direction']}</td>
              <td class="{'pos' if b['total_pnl']>=0 else 'neg'}">${b['total_pnl']:+,.2f}</td><td>{b['wr']}%</td><td>{b['avg_odds']}</td></tr>'''
        bl_html += '</tbody></table></div>'
    else:
        bl_html = '<div style="text-align:center;padding:20px;color:#28a745">✅ 沒有危險組合</div>'

    # Recovery summary
    rv_html = '<div class="tw"><table><thead><tr><th>狀態</th><th>CCY</th><th>Dir</th><th>最深層</th><th>最差損失</th><th>Best EV層</th><th>Best EV</th><th>恢復次數</th></tr></thead><tbody>'
    for r in recovery:
        rt = r['recovery_trades'] if r['recovery_trades'] < 999 else '∞'
        rv_html += f'''<tr><td>{r['status']}</td><td><b>{r['symbol']}</b></td><td>{r['direction']}</td>
          <td>{r['deepest_layer']}</td><td class="neg">${r['worst_loss']:.2f}</td>
          <td>{r['best_ev_layer']}</td><td class="{'pos' if r['best_ev']>=0 else 'neg'}">${r['best_ev']:+.2f}</td>
          <td><b>{rt}</b></td></tr>'''
    rv_html += '</tbody></table></div>'

    now_str = datetime.now().strftime('%Y-%m-%d %H:%M')

    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Signal #{signal_id} V3 分析報告</title>
<style>
:root{{--bg:#f5f7fa;--card:#fff;--text:#333;--text2:#666;--primary:#0f3460;--accent:#e94560;--green:#28a745;--red:#dc3545;--yellow:#FFC107;--orange:#fd7e14;--border:#e0e0e0;--radius:12px;--shadow:0 4px 16px rgba(0,0,0,0.08)}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC',sans-serif;background:var(--bg);color:var(--text);padding:12px;font-size:13px;line-height:1.5}}
.container{{max-width:1400px;margin:0 auto}}
.header{{background:linear-gradient(135deg,#0f3460 0%,#16213e 100%);border-radius:12px;padding:20px;margin-bottom:16px}}
.header h1{{font-size:22px;color:#fff;margin-bottom:4px}}
.header .sub{{font-size:11px;color:#a8d8ea}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin-bottom:16px;margin-top:12px}}
.card{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:10px;text-align:center;box-shadow:var(--shadow)}}
.card .v{{font-size:18px;font-weight:700;color:var(--primary)}}
.card .v.pos{{color:var(--green)}}.card .v.neg{{color:var(--red)}}
.card .l{{font-size:9px;color:var(--text2);margin-top:2px;text-transform:uppercase}}
.tabs{{display:flex;gap:0;margin-bottom:0;flex-wrap:wrap}}
.tab{{padding:10px 18px;background:var(--card);border:1px solid var(--border);color:var(--text2);cursor:pointer;border-radius:8px 8px 0 0;font-size:12px;white-space:nowrap}}
.tab.active{{background:var(--bg);color:var(--primary);border-bottom-color:var(--bg);font-weight:700}}
.tab:hover{{color:var(--primary)}}
.panel{{background:var(--bg);border:1px solid var(--border);border-top:none;border-radius:0 0 8px 8px;padding:16px;margin-bottom:20px}}
.panel.hidden{{display:none}}
.sec{{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);margin-bottom:12px;overflow:hidden}}
.sec-h{{position:relative;background:linear-gradient(135deg,#0f3460,#16213e);padding:10px 14px;font-size:12px;font-weight:bold;color:#fff;border-bottom:1px solid var(--border)}}
.help-icon{{display:inline-block;float:right;width:18px;height:18px;line-height:18px;text-align:center;border-radius:50%;background:rgba(255,255,255,0.25);color:#fff;font-size:12px;font-weight:bold;cursor:help;position:relative}}
.help-icon .help-tip{{display:none;position:absolute;left:auto;right:0;top:100%;width:320px;background:rgba(15,52,96,0.97);color:#fff;padding:10px 12px;border-radius:8px;font-size:11px;font-weight:normal;line-height:1.6;z-index:999;box-shadow:0 4px 12px rgba(0,0,0,0.3);white-space:normal;text-align:left;pointer-events:none}}
.help-icon:hover .help-tip{{display:block}}
.scatter-card .title{{display:none}}
h3 .help-icon{{background:rgba(15,52,96,0.2);color:var(--primary)}}
.sec-b{{padding:10px}}
.tw{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
table{{width:100%;border-collapse:collapse;font-size:11px;min-width:600px}}
th{{background:#0f3460;color:#eee;padding:6px;text-align:left;font-size:9px;text-transform:uppercase;border-bottom:2px solid var(--primary);white-space:nowrap;cursor:pointer}}
th:hover{{color:var(--accent)}}
td{{padding:5px 6px;border-bottom:1px solid var(--border);white-space:nowrap}}
tr:hover{{background:rgba(15,52,96,0.04)}}
.pos{{color:var(--green)}}.neg{{color:var(--red)}}
.rtg{{display:inline-block;padding:1px 8px;border-radius:4px;font-size:10px;font-weight:700;min-width:24px;text-align:center}}
.lbl{{font-size:9px;color:var(--text2);text-transform:uppercase}}
.legend{{display:flex;gap:16px;margin-top:8px;font-size:11px;color:var(--text2)}}
.legend span::before{{content:'';display:inline-block;width:12px;height:12px;border-radius:2px;margin-right:4px;vertical-align:middle}}
.l-green::before{{background:var(--green)}}.l-orange::before{{background:var(--orange)}}.l-red::before{{background:var(--red)}}
.ccy-section{{margin-bottom:8px;border:1px solid var(--border);border-radius:var(--radius);overflow:hidden}}
.ccy-header{{padding:12px 16px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;background:#f0f4f8;font-size:13px;color:var(--text)}}
.ccy-header:hover{{background:#e8edf2}}
.ccy-header .arrow{{transition:transform .2s;font-size:12px}}
.ccy-header.open .arrow{{transform:rotate(90deg)}}
.ccy-body{{display:none;padding:12px}}
.ccy-body.open{{display:block}}
.sug-card{{border:1px solid var(--border);border-radius:var(--radius);padding:12px;margin-bottom:12px;background:var(--card);box-shadow:var(--shadow)}}
.sug-card.high{{border-color:var(--green)}}.sug-card.medium{{border-color:var(--yellow)}}.sug-card.low{{border-color:var(--red)}}
.sug-title{{font-size:14px;font-weight:700;margin-bottom:8px}}
.sug-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:6px;font-size:11px}}
.sug-reason{{margin-top:8px;font-size:11px;color:var(--text2)}}
.scatter-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:10px}}
.scatter-card{{background:#f8f9fa;border:1px solid var(--border);border-radius:8px;padding:8px}}
.scatter-card .title{{font-size:11px;color:var(--primary);margin-bottom:4px}}
.footer{{text-align:center;padding:16px;color:var(--text2);font-size:10px}}
</style>
</head>
<body>
<div class="container">

<div class="header">
  <h1>🔬 Signal #{signal_id} V3 分析報告</h1>
  <div class="sub">Martin V3 + Quant 圖表 · {len(ccy_dirs)} CCY×Direction · {total_trades} trades · {now_str}</div>
  <div class="cards">
    <div class="card"><div class="v">{total_trades}</div><div class="l">總交易</div></div>
    <div class="card"><div class="v {'pos' if total_pnl>=0 else 'neg'}">${total_pnl:+,.0f}</div><div class="l">總盈虧</div></div>
    <div class="card"><div class="v {'pos' if wr>60 else 'neg'}">{wr:.1f}%</div><div class="l">勝率</div></div>
    <div class="card"><div class="v">{pf:.2f}</div><div class="l">Profit Factor</div></div>
    <div class="card"><div class="v neg">${abs(max_dd):,.0f}</div><div class="l">Max DD</div></div>
    <div class="card"><div class="v">{avg_hold:.1f}h</div><div class="l">Avg Hold</div></div>
    <div class="card"><div class="v" style="color:var(--accent)">{len(ccy_dirs)}</div><div class="l">CCY×Dir</div></div>
    <div class="card"><div class="v {'neg' if blacklist else 'pos'}">{len(blacklist)}</div><div class="l">黑名單</div></div>
  </div>
</div>

<div class="tabs">
  <div class="tab active" onclick="sw('p1')">📊 CCY 詳情</div>
  <div class="tab" onclick="sw('p2')">💀 黑名單</div>
  <div class="tab" onclick="sw('p3')">💪 恢復力</div>
</div>

<div class="panel" id="p1">
{ccy_sections}
</div>

<div class="panel hidden" id="p2">
  <h3 style="color:var(--primary);margin-bottom:12px">💀 黑名單 — 5因子 Danger Score</h3>
  <div style="font-size:10px;color:var(--text2);margin-bottom:8px">因子：虧損金額、賠率&lt;1、WR&lt;50%、EV&lt;0、最差層EV</div>
  {bl_html}
</div>

<div class="panel hidden" id="p3">
  <h3 style="color:var(--primary);margin-bottom:12px">💪 恢復力 — 最深層止損 vs 最佳EV恢復</h3>
  {rv_html}
</div>

<div class="footer">Signal #{signal_id} · Martin V3 + Quant · {now_str}</div>
</div>

<script>
// Tab switching
function sw(id){{
  document.querySelectorAll('.panel').forEach(p=>p.classList.add('hidden'));
  document.querySelectorAll('.tab').forEach(t=>t.classList.remove('active'));
  document.getElementById(id).classList.remove('hidden');
  event.target.classList.add('active');
  if(id==='p1') drawAllCharts();
}}

// CCY expand/collapse
var drawnCCY = {{}};
function toggleCCY(el){{
  el.classList.toggle('open');
  var body = el.nextElementSibling;
  body.classList.toggle('open');
  if(body.classList.contains('open') && !drawnCCY[el.dataset.idx]){{
    drawnCCY[el.dataset.idx] = true;
    drawCCYCharts(parseInt(el.dataset.idx));
  }}
}}

function drawCCYCharts(idx){{
  // Draw TP/SL chart for this CCY index
  var data = tpslData[idx];
  if(data && data.length){{
    var c = document.getElementById('tpsl_'+idx);
    if(c){{
      var ctx=c.getContext('2d');
      var dpr=window.devicePixelRatio||1;
      var p=c.parentElement;
      var w=p?(p.offsetWidth-24):600;
      w=Math.max(w,300);
      var h=Math.max(200,data.length*40);
      c.width=w*dpr;c.height=h*dpr;
      c.style.width=w+'px';c.style.height=h+'px';
      ctx.scale(dpr,dpr);
      var pad={{t:25,r:20,b:30,l:100}};
      var pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
      ctx.fillStyle='#f8f9fa';ctx.fillRect(0,0,w,h);
      var maxPip=1;
      data.forEach(function(d){{maxPip=Math.max(maxPip,d.tp,d.soft_sl,d.hard_sl)}});
      maxPip*=1.1;
      var barH=Math.max(4,ph/data.length*0.25);
      var rowH=ph/data.length;
      ctx.strokeStyle='#0f3460';ctx.lineWidth=1;
      ctx.beginPath();ctx.moveTo(pad.l+pw/2,pad.t);ctx.lineTo(pad.l+pw/2,pad.t+ph);ctx.stroke();
      var colors={{S:'#28a745',A:'#28a745',B:'#ffc107',C:'#fd7e14',D:'#dc3545'}};
      data.forEach(function(d,i){{
        var y=pad.t+rowH*i+rowH/2;
        var x0=pad.l+pw/2;
        var tpW=d.tp/maxPip*(pw/2);
        ctx.fillStyle=d.rating==='D'?'#dc3545':'#28a745';
        ctx.fillRect(x0,y-barH/2,tpW,barH);
        ctx.fillStyle='#fd7e14';
        ctx.fillRect(x0,y-barH/2-1,d.soft_sl/maxPip*(pw/2)*(-1),barH);
        ctx.fillStyle='rgba(220,53,69,0.3)';
        ctx.fillRect(x0,y-barH/2-1,d.hard_sl/maxPip*(pw/2)*(-1),barH+2);
        ctx.fillStyle='#333';ctx.font='bold 11px sans-serif';ctx.textAlign='right';
        ctx.fillText(d.level,pad.l-4,y+4);
        // === Numeric labels ===
        ctx.font='bold 11px sans-serif';
        // Hard SL - inside bar (white)
        ctx.textAlign='left';
        ctx.fillStyle='#fff';
        var hlW=d.hard_sl/maxPip*(pw/2);
        if(hlW>30) ctx.fillText(d.hard_sl.toFixed(1),x0-hlW+4,y+5);
        else{{ ctx.fillStyle='#a8001e'; ctx.textAlign='right'; ctx.fillText(d.hard_sl.toFixed(1),x0-hlW-4,y+5); }}
        // Soft SL - left of bar
        ctx.textAlign='right';
        ctx.fillStyle='#b35900';
        ctx.fillText(d.soft_sl.toFixed(1),x0-d.soft_sl/maxPip*(pw/2)-4,y+5);
        // TP - right of bar
        ctx.textAlign='left';
        ctx.fillStyle='#1a7a32';
        ctx.fillText(d.tp.toFixed(1),x0+tpW+4,y+5);
        // Rating - right of TP
        var rc=colors[d.rating]||'#666';
        ctx.fillStyle=rc;ctx.font='bold 12px sans-serif';
        ctx.fillText(d.rating,x0+tpW+45,y+5);
      }});
    }}
  }}
  // Draw scatter plots for this CCY index
  var sd = scatterData[idx];
  if(sd){{
    Object.keys(sd).forEach(function(lv){{
      var sc=document.getElementById('sc_'+idx+'_'+lv);
      if(!sc)return;
      var pts=sd[lv].points;if(!pts||!pts.length)return;
      var ctx=sc.getContext('2d');
      var dpr=window.devicePixelRatio||1;
      var p=sc.parentElement;
      var w=p?(p.offsetWidth-16):240;
      w=Math.max(w,200);
      var h=150;
      sc.width=w*dpr;sc.height=h*dpr;
      sc.style.width=w+'px';sc.style.height=h+'px';
      ctx.scale(dpr,dpr);
      ctx.fillStyle='#f8f9fa';ctx.fillRect(0,0,w,h);
      var pad={{t:18,r:8,b:18,l:28}};
      var pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
      ctx.strokeStyle='#ccc';ctx.lineWidth=0.5;
      ctx.beginPath();ctx.moveTo(pad.l,pad.t+ph/2);ctx.lineTo(pad.l+pw,pad.t+ph/2);ctx.stroke();
      var minX=0,maxX=0,minY=0,maxY=0;
      pts.forEach(function(p){{
        minX=Math.min(minX,p.net_pips);maxX=Math.max(maxX,p.net_pips);
        minY=Math.min(minY,p.mfe,p.mae);maxY=Math.max(maxY,p.mfe,p.mae);
      }});
      var rng=Math.max(Math.abs(minX),Math.abs(maxX),1);
      var rngY=Math.max(Math.abs(minY),Math.abs(maxY),1);
      pts.forEach(function(p){{
        var x=pad.l+(p.net_pips/rng*0.45+0.5)*pw;
        var yMfe=pad.t+(1-p.mfe/rngY*0.45-0.5)*ph;
        var yMae=pad.t+(1+p.mae/rngY*0.45-0.5)*ph;
        ctx.beginPath();ctx.arc(x,Math.min(pad.t+ph,Math.max(pad.t,yMfe)),2.0,0,Math.PI*2);
        ctx.fillStyle=p.is_win?'#28a745':'#dc3545';ctx.fill();
        ctx.beginPath();ctx.arc(x,Math.min(pad.t+ph,Math.max(pad.t,yMae)),2.0,0,Math.PI*2);
        ctx.fillStyle=p.is_win?'rgba(40,167,69,0.4)':'rgba(220,53,69,0.4)';ctx.fill();
      }});
      ctx.fillStyle='#0f3460';ctx.font='bold 10px sans-serif';ctx.textAlign='left';
      var lvName=lv.replace(/[^L\d+]/g,'')||lv;
      ctx.fillText(lvName+' (n='+pts.length+')',pad.l,12);
      // X axis labels
      ctx.fillStyle='#999';ctx.font='9px sans-serif';ctx.textAlign='center';
      ctx.fillText('-'+rng.toFixed(0),pad.l,pad.t+ph+12);
      ctx.fillText('0',pad.l+pw/2,pad.t+ph+12);
      ctx.fillText('+'+rng.toFixed(0),pad.l+pw,pad.t+ph+12);
      // Y axis labels  
      ctx.textAlign='right';
      ctx.fillText('+'+rngY.toFixed(0),pad.l-2,pad.t+8);
      ctx.fillText('-'+rngY.toFixed(0),pad.l-2,pad.t+ph);
      // Store points for tooltip
      var _pts=[];
      pts.forEach(function(p){{
        var x=pad.l+(p.net_pips/rng*0.45+0.5)*pw;
        var yMfe=pad.t+(1-p.mfe/rngY*0.45-0.5)*ph;
        _pts.push({{x:x,y:Math.min(pad.t+ph,Math.max(pad.t,yMfe)),mfe:p.mfe,mae:p.mae,net_pips:p.net_pips,is_win:p.is_win}});
      }});
      sc._scatterPoints=_pts;
      if(!sc._tooltipAdded){{
        sc._tooltipAdded=true;
        sc.addEventListener('mousemove',function(e){{
          var rect=sc.getBoundingClientRect();
          var dpr=window.devicePixelRatio||1;
          var mx=(e.clientX-rect.left);
          var my=(e.clientY-rect.top);
          var hit=null;
          if(sc._scatterPoints){{
            for(var i=0;i<sc._scatterPoints.length;i++){{
              var pt=sc._scatterPoints[i];
              if(Math.abs(mx-pt.x)<8 && Math.abs(my-pt.y)<8){{hit=pt;break;}}
            }}
          }}
          var tip=document.getElementById('scatterTip');
          if(hit){{
            if(!tip){{tip=document.createElement('div');tip.id='scatterTip';tip.style.cssText='position:fixed;background:rgba(15,52,96,0.95);color:#fff;padding:6px 10px;border-radius:6px;font-size:11px;pointer-events:none;z-index:9999;box-shadow:0 2px 8px rgba(0,0,0,0.3)';document.body.appendChild(tip);}}
            tip.style.display='block';
            tip.style.left=(e.clientX+12)+'px';
            tip.style.top=(e.clientY-30)+'px';
            tip.innerHTML='<b>'+(hit.is_win?'✅ Win':'❌ Lose')+'</b><br>Pips: '+hit.net_pips.toFixed(1)+'<br>MFE: '+hit.mfe.toFixed(1)+'<br>MAE: '+hit.mae.toFixed(1);
          }} else if(tip){{ tip.style.display='none'; }}
        }});
        sc.addEventListener('mouseleave',function(){{
          var tip=document.getElementById('scatterTip');
          if(tip) tip.style.display='none';
        }});
      }}
    }});
  }}
}}

// Data
var tpslData = {tpsl_json};
var scatterData = {scatter_json};
var chartMap = {chart_map_json};

// Sort tables
document.querySelectorAll('table').forEach(tbl=>{{
  var ths=tbl.querySelectorAll('thead th');
  ths.forEach((th,col)=>{{
    th.addEventListener('click',()=>{{
      var tbody=tbl.querySelector('tbody');
      if(!tbody)return;
      var rows=Array.from(tbody.querySelectorAll('tr'));
      var asc=th.dataset.sort!=='asc';
      ths.forEach(t=>{{t.classList.remove('sort-asc','sort-desc');delete t.dataset.sort}});
      th.dataset.sort=asc?'asc':'desc';
      th.classList.add(asc?'sort-asc':'sort-desc');
      rows.sort((a,b)=>{{
        var va=a.cells[col]?a.cells[col].textContent.trim():'';
        var vb=b.cells[col]?b.cells[col].textContent.trim():'';
        var na=parseFloat(va.replace(/[^0-9.-]/g,''));
        var nb=parseFloat(vb.replace(/[^0-9.-]/g,''));
        if(!isNaN(na)&&!isNaN(nb))return asc?na-nb:nb-na;
        return asc?va.localeCompare(vb):vb.localeCompare(va);
      }});
      rows.forEach(r=>tbody.appendChild(r));
    }});
  }});
}});

function drawAllCharts(){{
  // Charts drawn lazily on CCY expand
}}

function drawTpslCharts(){{
  for(var ci=0;ci<Object.keys(tpslData).length;ci++){{
    var data=tpslData[ci];
    if(!data||!data.length)continue;
    var c=document.getElementById('tpsl_'+ci);
    if(!c)continue;
    var ctx=c.getContext('2d');
    var dpr=window.devicePixelRatio||1;
    var w=c.offsetWidth||0;if(w<50){{var p=c.parentElement;w=p?(p.offsetWidth-24):600;}}
    var h=Math.max(200,data.length*40);
    c.width=w*dpr;c.height=h*dpr;
    c.style.height=h+'px';
    ctx.scale(dpr,dpr);
    var pad={{t:25,r:20,b:30,l:100}};
    var pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
    ctx.fillStyle='#f8f9fa';ctx.fillRect(0,0,w,h);

    var maxPip=1;
    data.forEach(function(d){{maxPip=Math.max(maxPip,d.tp,d.soft_sl,d.hard_sl)}});
    maxPip*=1.1;
    var barH=Math.max(4,ph/data.length*0.25);
    var rowH=ph/data.length;

    // Zero line
    ctx.strokeStyle='#0f3460';ctx.lineWidth=1;
    ctx.beginPath();ctx.moveTo(pad.l,pad.t);ctx.lineTo(pad.l,h-pad.b);ctx.stroke();

    data.forEach(function(d,i){{
      var y=pad.t+i*rowH;
      var label=d.level;
      ctx.fillStyle='#333';ctx.font='11px sans-serif';ctx.textAlign='right';
      ctx.fillText(label,pad.l-8,y+rowH/2+4);

      // TP (green, right)
      var tw=d.tp/maxPip*pw;
      ctx.fillStyle='#28a745';ctx.fillRect(pad.l,y+rowH/2-barH*1.5,Math.max(1,tw),barH);
      // Soft SL (orange, left)
      var sw=d.soft_sl/maxPip*pw;
      ctx.fillStyle='#fd7e14';ctx.fillRect(pad.l-sw,y+rowH/2-barH*0.5,Math.max(1,sw),barH);
      // Hard SL (red, left)
      var hw=d.hard_sl/maxPip*pw;
      ctx.fillStyle='#dc3545';ctx.fillRect(pad.l-hw,y+rowH/2+barH*0.5,Math.max(1,hw),barH);

      // Rating label
      ctx.fillStyle='#0f3460';ctx.font='bold 10px sans-serif';ctx.textAlign='left';
      ctx.fillText(d.rating+' '+d.tp+'/'+d.soft_sl,pad.l+tw+6,y+rowH/2+4);
    }});
  }}
}}

function drawScatterPlots(){{
  for(var ci=0;ci<Object.keys(scatterData).length;ci++){{
    var levels=scatterData[ci];
    if(!levels)continue;
    for(var lv in levels){{
      var c=document.getElementById('sc_'+ci+'_'+lv);
      if(!c)continue;
      var data=levels[lv].points;
      if(!data||!data.length)continue;
      var ctx=c.getContext('2d');
      var dpr=window.devicePixelRatio||1;
      var w=c.offsetWidth||0;if(w<50){{var p=c.parentElement;w=p?(p.offsetWidth-24):600;}}
      c.width=w*dpr;c.height=160*dpr;
      ctx.scale(dpr,dpr);
      var h=160;
      var pad={{t:12,r:6,b:20,l:30}};
      var pw=w-pad.l-pad.r,ph=h-pad.t-pad.b;
      ctx.fillStyle='#f8f9fa';ctx.fillRect(0,0,w,h);
      ctx.strokeStyle='#ccc';ctx.lineWidth=0.5;
      ctx.beginPath();ctx.moveTo(pad.l,pad.t);ctx.lineTo(pad.l,pad.t+ph);ctx.lineTo(pad.l+pw,pad.t+ph);ctx.stroke();

      var mx=1;
      data.forEach(function(d){{
        mx=Math.max(mx,Math.abs(d.mfe),Math.abs(d.mae));
      }});

      // Grid lines
      for(var g=0;g<=2;g++){{
        var gy=pad.t+ph*g/2;
        ctx.beginPath();ctx.moveTo(pad.l,gy);ctx.lineTo(pad.l+pw,gy);ctx.stroke();
        ctx.fillStyle='#666';ctx.font='8px sans-serif';ctx.textAlign='right';
        ctx.fillText((mx*(2-g)/2).toFixed(0),pad.l-4,gy+3);
      }}

      data.forEach(function(d){{
        var x=pad.l+(d.mae/mx)*pw;
        var y=pad.t+ph*(1-d.mfe/mx);
        x=Math.max(pad.l,Math.min(pad.l+pw,x));
        y=Math.max(pad.t,Math.min(pad.t+ph,y));
        ctx.beginPath();ctx.arc(x,y,2.0,0,Math.PI*2);
        ctx.fillStyle=d.is_win?'#28a745':'#dc3545';ctx.fill();
      }});
    }}
  }}
}}

// Initial draw
setTimeout(drawAllCharts, 100);
window.addEventListener('resize',function(){{setTimeout(drawAllCharts,50)}});
</script>
</body></html>'''

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    size = os.path.getsize(output_path)
    print(f"\n✅ Report generated: {output_path}")
    print(f"📏 File size: {size:,} bytes ({size/1024:.1f} KB)")
    return output_path, size


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python generate_signal_report_v2.py <signal_id> <csv_path> <output_path>")
        sys.exit(1)
    generate_report(sys.argv[1], sys.argv[2], sys.argv[3])
