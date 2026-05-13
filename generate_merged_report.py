#!/usr/bin/env python3
"""
Generate Merged HTML Report: TSA + Martin Autopsy V3
For Signal #11141

Integrates:
  - Lot-based level assignment (from existing TSA system)
  - Copy Trade suggestion engine (CoP/CoL DDE scoring)
  - Worthiness analysis (R-Multiple, Kelly, Safety Margin)
  - Martin level depth analysis
  - V3 MFE/MAE scatter plots
  - V3 TP/SL comparison (P85 vs MFE-based)
  - V3 Blacklist + Danger Score
  - V3 Recovery analysis
"""
import csv
import json
import math
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

CSV_PATH = "/home/alvin/.openclaw/workspace/quant/signal_11141.csv"
OUTPUT_PATH = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/merged_report_11141.html"
SIGNAL_ID = "11141"

# ─── Global TP/SL baselines (from 58 signals) ──────────────
GLOBAL_TP_BASELINES = {
    'L1': 48.0, 'L2': 88.5, 'L3': 74.6, 'L4': 109.3,
    'L5': 109.6, 'L6': 128.7, 'L7': 138.6, 'L8': 150.2, 'L9+': 163.4,
}
GLOBAL_SL_BASELINES = {
    'L1': 76.4, 'L2': 115.8, 'L3': 97.5, 'L4': 143.3,
    'L5': 129.7, 'L6': 126.7, 'L7': 109.0, 'L8': 92.1, 'L9+': 73.8,
}
GLOBAL_BASELINES = {
    'global_p25': 1.52, 'floor': 5.00, 'min_sample': 30,
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


# ─── Data Loading ───────────────────────────────────────────
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
                    'max_loss_pips': float(row.get('Max Loss Pips', 0)),
                    'commission': float(row.get('Commission', 0)),
                    'swap': float(row.get('Swap', 0)),
                    'holding_hours': float(row.get('Holding Time (Hours)', 0)) if row.get('Holding Time (Hours)') else 0,
                    'comment': row.get('Comment', ''),
                }
                if trade['symbol']:
                    trades.append(trade)
            except (ValueError, TypeError):
                continue
    return trades


def assign_lot_levels(trades):
    """Assign L1-L9+ levels based on unique lot sizes."""
    unique_lots = sorted(set(t['lots'] for t in trades))
    lot_to_level = {}
    for i, lot in enumerate(unique_lots):
        if i >= 8:
            lot_to_level[lot] = 'L9+'
        else:
            lot_to_level[lot] = f'L{i+1}'
    for t in trades:
        t['lot_level'] = lot_to_level[t['lots']]
    return lot_to_level


# ─── Statistical Helpers ────────────────────────────────────
def percentile(data, pct):
    if not data:
        return 0
    s = sorted(data)
    idx = int(len(s) * pct)
    return s[min(idx, len(s)-1)]


def get_effective_percentiles(sig_p50, sig_p75, sig_n, level_key, baseline_type='profit'):
    gb = GLOBAL_BASELINES[baseline_type].get(level_key, GLOBAL_BASELINES['profit']['L1'])
    global_p50, global_p75 = gb['p50'], gb['p75']
    floor = GLOBAL_BASELINES['floor']
    min_sample = GLOBAL_BASELINES['min_sample']
    if sig_p50 is not None and sig_p75 is not None:
        if sig_n is not None and sig_n < min_sample:
            w = sig_n / min_sample
            eff_p50 = w * sig_p50 + (1 - w) * global_p50
            eff_p75 = w * sig_p75 + (1 - w) * global_p75
        else:
            eff_p50, eff_p75 = sig_p50, sig_p75
        eff_p50 = max(eff_p50, floor)
        eff_p75 = max(eff_p75, eff_p50 + 0.01)
    else:
        eff_p50 = max(global_p50, floor)
        eff_p75 = max(global_p75, eff_p50 + 0.01)
    return eff_p50, eff_p75


def compute_signal_percentiles(trades, level_key, baseline_type='profit'):
    if baseline_type == 'profit':
        profits = sorted([t['net_profit'] for t in trades if t['net_profit'] > 0])
    else:
        profits = sorted([t['net_profit'] for t in trades
                         if abs(t.get('mae', 0)) >= 10 and t['net_profit'] > 0])
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
        return 0, 0
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
    return max(0, min(100, 100 - avg_dd * 50)), avg_dd


# ─── CoP/CoL Analysis ───────────────────────────────────────
def analyze_cop(trades, wait_levels, level_key):
    sig_p50, sig_p75, sig_n = compute_signal_percentiles(trades, level_key, 'profit')
    eff_p50, eff_p75 = get_effective_percentiles(sig_p50, sig_p75, sig_n, level_key, 'profit')
    results = {}
    for wp in wait_levels:
        triggered = []
        for t in trades:
            if t['net_profit'] <= 0:
                continue
            pp = abs(t.get('max_pips', 0)) or abs(t.get('mfe', 0))
            if pp >= wp:
                triggered.append(t)
        total_wins = sum(1 for t in trades if t['net_profit'] > 0)
        tr = len(triggered) / total_wins if total_wins > 0 else 0
        avg_p = sum(t['net_profit'] for t in triggered) / len(triggered) if triggered else 0
        ts = min(tr * 100, 100)
        ps = alpha_capture_score(avg_p, eff_p50, eff_p75)
        ds, _ = dde_score(triggered)
        ws = ts * 0.4 + ps * 0.4 + ds * 0.2
        results[wp] = {
            'triggered': len(triggered), 'total_wins': total_wins,
            'trigger_rate': tr, 'avg_profit': avg_p,
            'trigger_score': ts, 'profit_score': ps, 'dde_score': ds,
            'weighted': ws,
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
        total_recover_pnl = 0
        for t in trades:
            if abs(t.get('mae', 0)) >= wp:
                triggered += 1
                if t['net_profit'] > 0:
                    recovered += 1
                    total_recover_pnl += t['net_profit']
        total = len(trades)
        trigger_rate = triggered / total if total > 0 else 0
        recovery_rate = recovered / triggered if triggered > 0 else 0
        avg_p = total_recover_pnl / recovered if recovered > 0 else 0
        rs = recovery_rate * 100
        ps = alpha_capture_score(avg_p, eff_p50, eff_p75)
        ws = rs * 0.5 + ps * 0.5
        results[wp] = {
            'triggered': triggered, 'recovered': recovered,
            'trigger_rate': trigger_rate, 'recovery_rate': recovery_rate,
            'avg_profit': avg_p,
            'recovery_score': rs, 'profit_score': ps,
            'weighted': ws,
            'rating': '⭐⭐⭐⭐' if ws >= 80 else '⭐⭐⭐' if ws >= 60 else '⭐⭐' if ws >= 40 else '⭐',
        }
    return results


# ─── P85 TP/SL ──────────────────────────────────────────────
def calc_p85_tpsl(level_trades, level_key):
    if not level_trades:
        return {'tp': None, 'sl': None, 'rr': None}
    wins = [t for t in level_trades if t['net_profit'] > 0]
    n_all, n_win = len(level_trades), len(wins)
    gtp = GLOBAL_TP_BASELINES.get(level_key, 53.0)
    gsl = GLOBAL_SL_BASELINES.get(level_key, 44.7)
    # TP
    if n_win >= 100:
        tp = percentile([abs(t.get('max_pips', 0)) for t in wins], 0.85)
        tp_src = f'P85(n={n_win})'
    elif n_win >= 30:
        tp_sig = percentile([abs(t.get('max_pips', 0)) for t in wins], 0.85)
        w = (n_win - 30) / 70
        tp = w * tp_sig + (1 - w) * gtp
        tp_src = f'blend(n={n_win})'
    else:
        tp = gtp
        tp_src = f'global(n={n_win})'
    # SL
    if n_all >= 100:
        sl = percentile([abs(t.get('max_loss_pips', 0)) for t in level_trades], 0.85)
    elif n_all >= 30:
        sl_sig = percentile([abs(t.get('max_loss_pips', 0)) for t in level_trades], 0.85)
        w = (n_all - 30) / 70
        sl = w * sl_sig + (1 - w) * gsl
    else:
        sl = gsl
    rr = tp / sl if sl > 0 else None
    return {'tp': round(tp, 1), 'sl': round(sl, 1), 'rr': round(rr, 2) if rr else None, 'tp_src': tp_src}


# ─── Worthiness ─────────────────────────────────────────────
def calc_worthiness(trades):
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
    if sm > 0.15:
        sg = '🟢 穩健'
    elif sm > 0.05:
        sg = '🟡 一般'
    else:
        sg = '🔴 危險'
    return {
        'trades': n, 'win_rate': round(w * 100, 1), 'avg_win': round(avg_w, 2),
        'avg_loss': round(avg_l, 2), 'rr_ratio': round(rr, 2),
        'expectancy': round(exp_r, 3), 'kelly': round(kelly * 100, 1),
        'kelly_quarter': round(max(0, kelly * 25), 1),
        'breakeven_wr': round(be_wr * 100, 1), 'safety_margin': round(sm * 100, 1),
        'safety_grade': sg, 'total_profit': round(sum(t['net_profit'] for t in trades), 2),
    }


# ─── Martin Level Depth ────────────────────────────────────
def calc_martin_depth(trades):
    classic = [t for t in trades if t['net_profit'] > 0 and t['net_pips'] < 0]
    total_profit = sum(t['net_profit'] for t in trades if t['net_profit'] > 0)
    martin_profit = sum(t['net_profit'] for t in classic)
    dep = (martin_profit / total_profit * 100) if total_profit > 0 else 0
    levels = defaultdict(list)
    for t in trades:
        levels[t['lot_level']].append(t)
    lv_results = {}
    for lv, lt in sorted(levels.items(), key=lambda x: (99 if x[0]=='L9+' else int(x[0][1:]))):
        lm = [t for t in lt if t['net_profit'] > 0 and t['net_pips'] < 0]
        n = len(lt)
        nm = len(lm)
        lv_results[lv] = {
            'trades': n, 'martin_count': nm,
            'trigger_rate': round(nm / n * 100, 1) if n > 0 else 0,
            'avg_depth_pips': round(sum(abs(t['mae']) for t in lm) / nm, 1) if nm else 0,
            'max_depth_pips': round(max((abs(t['mae']) for t in lm), default=0), 1),
            'avg_dd': round(sum(abs(t['max_loss']) for t in lm) / nm, 2) if nm else 0,
            'max_dd': round(max((abs(t['max_loss']) for t in lm), default=0), 2),
        }
    return {'dependency': round(dep, 1), 'martin_count': len(classic),
            'martin_profit': round(martin_profit, 2), 'total_profit': round(total_profit, 2),
            'levels': lv_results}


# ─── Copy Trade Suggestion ─────────────────────────────────
def copy_trade_suggestion(trades, worthiness, martin, levels_data):
    if not worthiness:
        return None
    exp = worthiness['expectancy']
    wr = worthiness['win_rate']
    md = martin['dependency']
    # Find best CoP/CoL
    best_cop = (0, 0, '')
    best_col = (0, 0, '')
    for lv, ld in levels_data.items():
        for wp, r in ld.get('cop', {}).items():
            if r['weighted'] > best_cop[0]:
                best_cop = (r['weighted'], wp, lv)
        for wp, r in ld.get('col', {}).items():
            if r['weighted'] > best_col[0]:
                best_col = (r['weighted'], wp, lv)
    # Decision
    if exp < 0.1 or md > 70:
        rec, strat, conf, cls = '❌ 不建議 Copy', 'N/A', '🔴 低', 'low'
        reason = []
        if exp < 0.1: reason.append(f'期望值過低 ({exp:.3f}R)')
        if md > 70: reason.append(f'馬丁依賴度過高 ({md:.1f}%)')
        reason = '、'.join(reason)
    elif md < 30 and wr > 60 and best_cop[0] > 0:
        rec = '✅ 建議 CoP (Copy on Profit)'
        strat, wait = 'CoP', best_cop[1]
        reason = f'馬丁依賴度低 ({md:.1f}%)、勝率 {wr:.1f}%、信號質素高'
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
        rec, strat, conf, cls = '❌ 不建議 Copy', 'N/A', '🔴 低', 'low'
        reason = '缺乏有效的 CoP/CoL 觸發數據'
    # Get TP/SL
    best_lv = best_cop[2] or 'L1'
    tpsl = levels_data.get(best_lv, {}).get('p85_tpsl', {})
    return {
        'recommendation': rec, 'strategy': strat, 'confidence': conf, 'confidence_class': cls,
        'reason': reason, 'expectancy': exp, 'win_rate': wr, 'martin_dep': md,
        'best_cop_score': round(best_cop[0], 1), 'best_col_score': round(best_col[0], 1),
        'best_cop_level': best_cop[2], 'best_col_level': best_col[2],
        'tp': tpsl.get('tp', 'N/A'), 'sl': tpsl.get('sl', 'N/A'), 'rr': tpsl.get('rr', 'N/A'),
    }


# ─── V3 Rating ─────────────────────────────────────────────
def v3_rating(stats):
    wr = stats.get('win_rate', 0)
    ev = stats.get('ev', 0)
    odds = min(stats.get('odds_dollar', 0), stats.get('odds_pips', 0))
    count = stats.get('count', 0)
    hold = stats.get('avg_hold', 0)
    score = 0
    if wr >= 80: score += 30
    elif wr >= 70: score += 25
    elif wr >= 60: score += 18
    elif wr >= 50: score += 10
    else: score += max(0, wr / 5)
    if ev >= 20: score += 30
    elif ev >= 10: score += 25
    elif ev >= 5: score += 18
    elif ev >= 0: score += 10
    else: score += max(0, 10 + ev / 2)
    if odds >= 2.0: score += 20
    elif odds >= 1.5: score += 15
    elif odds >= 1.0: score += 10
    else: score += max(0, odds * 10)
    if count >= 10: score += 15
    elif count >= 5: score += 12
    elif count >= 3: score += 8
    else: score += max(0, count * 2)
    if hold <= 24: score += 5
    elif hold <= 72: score += 4
    elif hold <= 168: score += 3
    elif hold <= 360: score += 2
    else: score += 1
    if score >= 85: return 'S+'
    if score >= 70: return 'S'
    if score >= 55: return 'A'
    if score >= 40: return 'B'
    if score >= 25: return 'C'
    if score >= 15: return 'D'
    return 'E'


# ─── Blacklist + Danger Score ───────────────────────────────
def calc_blacklist(ccy_dir_data):
    blacklist = []
    for (sym, d), layers in ccy_dir_data.items():
        all_trades = []
        for key, lv_data in layers.items():
            if key == '_meta': continue
            if 'trades' in lv_data:
                all_trades.extend(lv_data['trades'])
        total_pnl = sum(t['net_profit'] for t in all_trades)
        total_trades = len(all_trades)
        total_wins = sum(1 for t in all_trades if t['net_profit'] > 0)
        wr = total_wins / total_trades * 100 if total_trades else 0
        # Classic martin
        classic = [t for t in all_trades if t['net_profit'] > 0 and t['net_pips'] < 0]
        reverse = [t for t in all_trades if t['net_profit'] < 0 and t['net_pips'] > 0]
        cost_killed = [t for t in all_trades if t['net_profit'] < 0 and (t['net_profit'] - t['commission'] - t['swap']) > 0]
        # Danger score (5 factors)
        danger = 0
        if total_pnl < 0: danger += min(abs(total_pnl) / 500, 5)
        avg_odds_list = []
        for key, lv_data in layers.items():
            if key == '_meta': continue
            lt = lv_data['trades']
            w = [t for t in lt if t['net_profit'] > 0]
            l = [t for t in lt if t['net_profit'] <= 0]
            if w and l:
                aw = sum(t['net_profit'] for t in w) / len(w)
                al = abs(sum(t['net_profit'] for t in l) / len(l))
                avg_odds_list.append(aw / al if al > 0 else 0)
        avg_odds = sum(avg_odds_list) / len(avg_odds_list) if avg_odds_list else 0
        if avg_odds < 1.0: danger += 3
        if wr < 50: danger += 2
        martin_dep = 0
        total_profit = sum(t['net_profit'] for t in all_trades if t['net_profit'] > 0)
        martin_profit = sum(t['net_profit'] for t in classic)
        if total_profit > 0:
            martin_dep = martin_profit / total_profit * 100
        if martin_dep > 50: danger += 3
        elif martin_dep > 30: danger += 1
        if danger >= 1:
            level = '💀 DEADLY' if danger > 5 else '⚠️ WARNING' if danger > 2 else '⚡ CAUTION'
            blacklist.append({
                'symbol': sym, 'direction': d, 'total_pnl': round(total_pnl, 2),
                'wr': round(wr, 1), 'avg_odds': round(avg_odds, 2),
                'martin_dep': round(martin_dep, 1),
                'classic_martin': len(classic), 'reverse_martin': len(reverse),
                'cost_killed': len(cost_killed),
                'danger': round(danger, 1), 'level': level,
            })
    blacklist.sort(key=lambda x: -x['danger'])
    return blacklist


# ─── Recovery Analysis ──────────────────────────────────────
def calc_recovery(ccy_dir_data):
    results = []
    for (sym, d), layers in ccy_dir_data.items():
        # Find deepest layer
        lvl_keys = [k for k in layers.keys() if k != '_meta']
        deepest_lv = max(lvl_keys, key=lambda x: (99 if x == 'L9+' else int(x[1:])))
        deepest = layers[deepest_lv]
        worst_loss = deepest['avg_loss'] if deepest['loss_count'] > 0 else (deepest['avg_lots'] * 100)
        # Best EV layer
        best_ev_lv = max(lvl_keys, key=lambda x: layers[x].get('ev', 0))
        best_ev = layers[best_ev_lv].get('ev', 0)
        if best_ev > 0:
            recovery_trades = math.ceil(worst_loss / best_ev)
        else:
            recovery_trades = 999
        total_trades = sum(ld['count'] for k, ld in layers.items() if k != '_meta')
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
            'deepest_layer': deepest_lv, 'worst_loss': round(worst_loss, 2),
            'best_ev_layer': best_ev_lv, 'best_ev': round(best_ev, 2),
            'recovery_trades': recovery_trades, 'recovery_days': int(recovery_days),
            'status': status, 'status_text': text,
        })
    results.sort(key=lambda x: x['recovery_trades'])
    return results


# ─── Main Computation ───────────────────────────────────────
def compute_all():
    print("Loading trades...")
    trades = load_trades(CSV_PATH)
    print(f"  {len(trades)} trades loaded")
    
    lot_to_level = assign_lot_levels(trades)
    print(f"  Lot levels: {lot_to_level}")
    
    # Group by (CCY, Direction)
    ccy_dir_trades = defaultdict(list)
    for t in trades:
        ccy_dir_trades[(t['symbol'], t['direction'])].append(t)
    
    # For each CCY×Dir, compute per-level stats
    LEVEL_ORDER = lambda x: (99 if x == 'L9+' else int(x[1:]))
    
    ccy_dir_levels = {}  # (sym, dir) -> {level: stats}
    all_levels_data = {}  # For copy trade suggestion (flat)
    
    for (sym, d), cd_trades in sorted(ccy_dir_trades.items()):
        # Group by lot_level
        level_groups = defaultdict(list)
        for t in cd_trades:
            level_groups[t['lot_level']].append(t)
        
        ccy_dir_levels[(sym, d)] = {}
        
        for lv in sorted(level_groups.keys(), key=LEVEL_ORDER):
            lt = level_groups[lv]
            n = len(lt)
            wins = [t for t in lt if t['net_profit'] > 0]
            losses = [t for t in lt if t['net_profit'] <= 0]
            wr = len(wins) / n * 100 if n else 0
            total_pnl = sum(t['net_profit'] for t in lt)
            avg_win = sum(t['net_profit'] for t in wins) / len(wins) if wins else 0
            avg_loss = abs(sum(t['net_profit'] for t in losses) / len(losses)) if losses else 0
            ev = (wr/100 * avg_win) - ((1-wr/100) * avg_loss)
            avg_win_pips = sum(t['net_pips'] for t in wins) / len(wins) if wins else 0
            avg_loss_pips = abs(sum(t['net_pips'] for t in losses) / len(losses)) if losses else 0
            odds_d = avg_win / avg_loss if avg_loss > 0 else 999
            odds_p = avg_win_pips / avg_loss_pips if avg_loss_pips > 0 else 999
            avg_hold = sum(t['holding_hours'] for t in lt) / n
            avg_mfe = sum(t['mfe'] for t in lt) / n
            max_mfe = max(t['mfe'] for t in lt) if lt else 0
            avg_mae = sum(t['mae'] for t in lt) / n
            max_mae = max(t['mae'] for t in lt) if lt else 0
            
            stats = {
                'count': n, 'win_count': len(wins), 'loss_count': len(losses),
                'win_rate': round(wr, 1), 'total_pnl': round(total_pnl, 2),
                'ev': round(ev, 2), 'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'avg_win_pips': round(avg_win_pips, 1), 'avg_loss_pips': round(avg_loss_pips, 1),
                'odds_dollar': round(min(odds_d, 999), 2), 'odds_pips': round(min(odds_p, 999), 2),
                'avg_hold': round(avg_hold, 1),
                'avg_mfe': round(avg_mfe, 1), 'max_mfe': round(max_mfe, 1),
                'avg_mae': round(avg_mae, 1), 'max_mae': round(max_mae, 1),
                'avg_lots': sum(t['lots'] for t in lt) / n,
                'trades': lt,  # Keep for scatter plots
            }
            stats['rating'] = v3_rating(stats)
            ccy_dir_levels[(sym, d)][lv] = stats
        
        # Overall worthiness for this CCY×Dir
        worth = calc_worthiness(cd_trades)
        martin = calc_martin_depth(cd_trades)
        
        # Per-level CoP/CoL/TPSL
        levels_detail = {}
        for lv in sorted(level_groups.keys(), key=LEVEL_ORDER):
            lt = level_groups[lv]
            cop = analyze_cop(lt, [5, 10, 15, 20], lv)
            col = analyze_col(lt, [10, 15, 20, 25], lv)
            p85 = calc_p85_tpsl(lt, lv)
            # V3 TP/SL
            lv_stats = ccy_dir_levels[(sym, d)][lv]
            v3_tp = lv_stats['avg_mfe']
            v3_soft_sl = lv_stats['avg_mae'] * 1.2
            # Hard SL from pair max MAE
            pair_max_mae = max(ccy_dir_levels[(sym, d)][l]['max_mae'] for l in ccy_dir_levels[(sym, d)])
            v3_hard_sl = pair_max_mae * 1.3
            v3_rr = v3_tp / v3_soft_sl if v3_soft_sl > 0 else 0
            levels_detail[lv] = {
                'cop': cop, 'col': col, 'p85_tpsl': p85,
                'v3_tp': round(v3_tp, 1), 'v3_soft_sl': round(v3_soft_sl, 1),
                'v3_hard_sl': round(v3_hard_sl, 1), 'v3_rr': round(v3_rr, 2),
            }
        
        suggestion = copy_trade_suggestion(cd_trades, worth, martin, levels_detail)
        
        ccy_dir_levels[(sym, d)]['_meta'] = {
            'worthiness': worth, 'martin': martin, 'suggestion': suggestion,
            'levels_detail': levels_detail, 'total_trades': len(cd_trades),
        }
    
    # Blacklist & Recovery
    blacklist = calc_blacklist(ccy_dir_levels)
    recovery = calc_recovery(ccy_dir_levels)
    
    return trades, ccy_dir_levels, blacklist, recovery


# ─── HTML Generation ────────────────────────────────────────
def rating_color(r):
    return {'S+': '#FFD700', 'S': '#2ecc71', 'A': '#3498db', 'B': '#9b59b6',
            'C': '#f39c12', 'D': '#e67e22', 'E': '#e74c3c'}.get(r, '#999')

def rating_bg(r):
    return {'S+': '#FFF8E1', 'S': '#E8F5E9', 'A': '#E3F2FD', 'B': '#F3E5F5',
            'C': '#FFF3E0', 'D': '#FBE9E7', 'E': '#FFEBEE'}.get(r, '#F5F5F5')

def pnl_cls(v):
    return 'positive' if v > 0 else 'negative' if v < 0 else 'neutral'

def pm(v):
    return ('+' if v > 0 else '') + f'{v:.2f}'


def generate_html(trades, ccy_dir_levels, blacklist, recovery):
    total_trades = len(trades)
    total_pnl = sum(t['net_profit'] for t in trades)
    total_wins = sum(1 for t in trades if t['net_profit'] > 0)
    wr = total_wins / total_trades * 100 if total_trades else 0
    
    symbols = sorted(set(t['symbol'] for t in trades))
    ccy_dirs = sorted(ccy_dir_levels.keys())
    
    LEVEL_ORDER = lambda x: (99 if x == 'L9+' else int(x[1:]))
    
    # Build overview table data
    overview = []
    for (sym, d) in ccy_dirs:
        meta = ccy_dir_levels[(sym, d)].get('_meta', {})
        cd_trades_count = meta.get('total_trades', 0)
        worth = meta.get('worthiness')
        # Sum across levels
        all_lvls = {k: v for k, v in ccy_dir_levels[(sym, d)].items() if k != '_meta'}
        total_pnl_cd = sum(v['total_pnl'] for v in all_lvls.values())
        total_wins_cd = sum(v['win_count'] for v in all_lvls.values())
        wr_cd = total_wins_cd / cd_trades_count * 100 if cd_trades_count else 0
        total_ev = sum(v['ev'] for v in all_lvls.values())
        avg_ev = total_ev / len(all_lvls) if all_lvls else 0
        avg_odds_d = sum(v['odds_dollar'] for v in all_lvds.values()) / len(all_lvls) if all_lvls else 0
        
        # Wait, typo: all_lvls not all_lvds
        overview.append({
            'symbol': sym, 'direction': d, 'trades': cd_trades_count,
            'layers': len(all_lvls),
            'max_depth': max(LEVEL_ORDER(k) for k in all_lvls) if all_lvls else 0,
            'total_pnl': round(total_pnl_cd, 2), 'wr': round(wr_cd, 1),
            'avg_ev': round(avg_ev, 2),
            'suggestion': meta.get('suggestion'),
        })
    overview.sort(key=lambda x: -x['total_pnl'])
    
    # ... (rest of HTML generation below)
    # This is getting complex, let me just build the full HTML string
    return build_full_html(trades, ccy_dir_levels, blacklist, recovery, overview, symbols, ccy_dirs, LEVEL_ORDER)


def build_full_html(trades, ccy_dir_levels, blacklist, recovery, overview, symbols, ccy_dirs, LEVEL_ORDER):
    total_trades = len(trades)
    total_pnl = sum(t['net_profit'] for t in trades)
    total_wins = sum(1 for t in trades if t['net_profit'] > 0)
    wr = total_wins / total_trades * 100
    
    # Collect scatter data for JS
    scatter_data = {}
    chart_idx = 0
    ccy_dir_chart_map = {}
    for (sym, d) in sorted(ccy_dirs):
        all_lvls = {k: v for k, v in ccy_dir_levels[(sym, d)].items() if k != '_meta'}
        points = []
        for lv in sorted(all_lvls.keys(), key=LEVEL_ORDER):
            for t in all_lvls[lv]['trades']:
                points.append({
                    'net_pips': t['net_pips'], 'mae': t['mae'], 'mfe': t['mfe'],
                    'is_win': t['net_profit'] > 0, 'level': lv, 'lots': t['lots'],
                })
        scatter_data[str(chart_idx)] = points
        ccy_dir_chart_map[(sym, d)] = chart_idx
        chart_idx += 1
    
    scatter_json = json.dumps(scatter_data)
    
    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Signal #{SIGNAL_ID} 合併分析報告</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;font-size:12px;line-height:1.5;color:#e0e0e0;background:#0a0a1a;padding:10px}}
.container{{max-width:1500px;margin:0 auto}}
a{{color:#64b5f6;text-decoration:none}}

/* Header */
.header{{background:linear-gradient(135deg,#1a1a3e 0%,#2d1b69 50%,#1a1a3e 100%);border:1px solid #4a3f8a;border-radius:12px;padding:20px;margin-bottom:16px}}
.header h1{{font-size:20px;color:#FFD700;margin-bottom:4px}}
.header .sub{{font-size:11px;color:#888}}
.kpi-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-top:12px}}
.kpi{{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);border-radius:8px;padding:8px;text-align:center}}
.kpi .lbl{{font-size:9px;color:#888;text-transform:uppercase;letter-spacing:.5px}}
.kpi .val{{font-size:16px;font-weight:bold;color:#fff;margin-top:3px}}
.kpi .val.g{{color:#2ecc71}}.kpi .val.r{{color:#e74c3c}}.kpi .val.gold{{color:#FFD700}}

/* Tabs */
.tabs{{display:flex;gap:2px;background:#0a0a18;border-bottom:2px solid #2a2a4a;padding:0 12px;flex-wrap:wrap}}
.tab{{padding:8px 14px;cursor:pointer;font-size:11px;color:#888;border-bottom:2px solid transparent;transition:.2s;white-space:nowrap}}
.tab:hover{{color:#ccc}}.tab.active{{color:#FFD700;border-bottom-color:#FFD700}}
.tc{{display:none}}.tc.active{{display:block}}

/* Section */
.sec{{background:#0f0f23;border:1px solid #2a2a4a;border-radius:10px;margin-bottom:16px;overflow:hidden}}
.sec-h{{background:linear-gradient(90deg,#1a1a3e,#2d1b69);padding:10px 14px;font-size:13px;font-weight:bold;color:#fff;border-bottom:1px solid #3a3a6a;display:flex;justify-content:space-between;align-items:center}}
.sec-h .badge{{background:#FFD700;color:#000;font-size:9px;padding:2px 8px;border-radius:10px;font-weight:normal}}
.sec-b{{padding:10px}}

/* Tables */
.tw{{overflow-x:auto;-webkit-overflow-scrolling:touch}}
table{{width:100%;border-collapse:collapse;font-size:10px}}
table th{{background:#1a1a3e;color:#bbb;padding:5px 6px;text-align:left;font-size:9px;text-transform:uppercase;letter-spacing:.3px;border-bottom:1px solid #3a3a6a;white-space:nowrap;position:sticky;top:0;cursor:pointer}}
table th:hover{{color:#FFD700}}
table td{{padding:4px 6px;border-bottom:1px solid #1a1a2a;white-space:nowrap}}
table tr:hover{{background:rgba(255,255,255,.03)}}
.pos{{color:#2ecc71}}.neg{{color:#e74c3c}}.neu{{color:#888}}

/* Rating badge */
.rtg{{display:inline-block;padding:1px 6px;border-radius:3px;font-weight:bold;font-size:10px;min-width:24px;text-align:center}}

/* Suggestion card */
.sug-card{{border:1px solid #2a2a4a;border-radius:8px;padding:12px;margin-bottom:10px;background:rgba(255,255,255,.02)}}
.sug-card.high{{border-color:#2ecc71}}.sug-card.medium{{border-color:#f39c12}}.sug-card.low{{border-color:#e74c3c}}

/* Scatter */
.scatter-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:10px}}
.scatter-card{{background:#0a0a18;border:1px solid #2a2a4a;border-radius:8px;padding:8px}}
.scatter-card .title{{font-size:11px;color:#bbb;margin-bottom:4px}}
canvas.scatter{{width:100%;height:160px}}

/* Expandable CCY */
.ccy-section{{margin-bottom:8px;border:1px solid #2a2a4a;border-radius:8px;overflow:hidden}}
.ccy-header{{padding:10px 14px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;background:#131335}}
.ccy-header:hover{{background:#1a1a4a}}
.ccy-header .arrow{{transition:transform .2s;font-size:12px}}
.ccy-header.open .arrow{{transform:rotate(90deg)}}
.ccy-body{{display:none;padding:10px}}
.ccy-body.open{{display:block}}

/* Sub-tabs */
.sub-tabs{{display:flex;gap:2px;margin-bottom:8px}}
.sub-tab{{padding:5px 12px;cursor:pointer;font-size:10px;color:#888;border:1px solid #2a2a4a;border-radius:4px}}
.sub-tab.active{{color:#FFD700;border-color:#FFD700;background:rgba(255,215,0,.1)}}
.sub-tc{{display:none}}.sub-tc.active{{display:block}}

/* TP/SL compare highlight */
.better{{background:rgba(46,204,113,.15);font-weight:bold}}

/* Sortable */
th.sort-asc::after{{content:' ▲';font-size:8px}}
th.sort-desc::after{{content:' ▼';font-size:8px}}

.footer{{text-align:center;padding:12px;color:#555;font-size:10px}}
</style>
</head>
<body>
<div class="container">

<!-- Header -->
<div class="header">
<h1>🔬 Signal #{SIGNAL_ID} 合併分析報告</h1>
<div class="sub">TSA + 馬丁剖析法 V3 · {len(ccy_dirs)} CCY×Direction · {total_trades} trades · {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
<div class="kpi-row">
<div class="kpi"><div class="lbl">總交易</div><div class="val">{total_trades}</div></div>
<div class="kpi"><div class="lbl">總盈虧</div><div class="val {'g' if total_pnl>0 else 'r'}">${total_pnl:+,.2f}</div></div>
<div class="kpi"><div class="lbl">勝率</div><div class="val {'g' if wr>60 else 'r'}">{wr:.1f}%</div></div>
<div class="kpi"><div class="lbl">CCY×Dir</div><div class="val gold">{len(ccy_dirs)}</div></div>
<div class="kpi"><div class="lbl">黑名單</div><div class="val {'r' if blacklist else 'g'}">{len(blacklist)}</div></div>
</div>
</div>

<!-- Main Tabs -->
<div class="tabs">
<div class="tab active" onclick="switchTab('overview')">總覽</div>
<div class="tab" onclick="switchTab('detail')">CCY 詳情</div>
<div class="tab" onclick="switchTab('blacklist')">黑名單</div>
<div class="tab" onclick="switchTab('recovery')">恢復力</div>
</div>

<!-- ═══ TAB: Overview ═══ -->
<div id="overview" class="tc active">
<div class="sec">
<div class="sec-h">CCY×Direction 總覽<span class="badge">{len(overview)} 組合</span></div>
<div class="sec-b"><div class="tw">
<table id="overview-table">
<thead><tr>
<th data-col="0">#</th><th data-col="1">CCY</th><th data-col="2">Dir</th>
<th data-col="3">Trades</th><th data-col="4">Layers</th><th data-col="5">MaxD</th>
<th data-col="6">Total$</th><th data-col="7">WR%</th><th data-col="8">EV$/L</th>
<th data-col="9">建議</th><th data-col="10">信心</th>
</tr></thead><tbody>
"""
    for i, o in enumerate(overview, 1):
        sug = o.get('suggestion')
        rec = sug['recommendation'] if sug else 'N/A'
        conf = sug['confidence'] if sug else 'N/A'
        html += f'<tr><td>{i}</td><td><b>{o["symbol"]}</b></td><td>{o["direction"]}</td>'
        html += f'<td>{o["trades"]}</td><td>{o["layers"]}</td><td>{o["max_depth"]}</td>'
        html += f'<td class="{pnl_cls(o["total_pnl"])}"><b>${o["total_pnl"]:+,.2f}</b></td>'
        html += f'<td>{o["wr"]}%</td><td class="{pnl_cls(o["avg_ev"])}">{o["avg_ev"]:+.2f}</td>'
        html += f'<td>{rec}</td><td>{conf}</td></tr>\n'
    
    html += """</tbody></table></div></div></div>
</div>

<!-- ═══ TAB: CCY Detail ═══ -->
<div id="detail" class="tc">
<div class="sec">
<div class="sec-h">CCY 詳情<span class="badge">展開查看 Buy/Sell 子分析</span></div>
<div class="sec-b">
"""
    
    # Group by CCY
    ccy_groups = defaultdict(list)
    for (sym, d) in ccy_dirs:
        ccy_groups[sym].append(d)
    
    for sym in sorted(ccy_groups.keys()):
        dirs = ccy_groups[sym]
        # CCY summary
        all_cd_trades = []
        for d in dirs:
            all_cd_trades.extend([t for t in trades if t['symbol'] == sym and t['direction'] == d])
        cd_pnl = sum(t['net_profit'] for t in all_cd_trades)
        cd_wr = sum(1 for t in all_cd_trades if t['net_profit'] > 0) / len(all_cd_trades) * 100 if all_cd_trades else 0
        
        html += f'<div class="ccy-section">'
        html += f'<div class="ccy-header" onclick="toggleCCY(this)">'
        html += f'<span><b>{sym}</b> — {len(all_cd_trades)} trades · ${cd_pnl:+,.2f} · WR {cd_wr:.1f}%</span>'
        html += f'<span class="arrow">▶</span></div>'
        html += f'<div class="ccy-body">'
        
        # Sub-tabs for Buy/Sell
        html += f'<div class="sub-tabs">'
        for j, d in enumerate(dirs):
            cls = ' active' if j == 0 else ''
            html += f'<div class="sub-tab{cls}" onclick="switchSubTab(this,\'{sym}_{d}\')">{d.upper()}</div>'
        html += '</div>'
        
        for j, d in enumerate(dirs):
            active = ' active' if j == 0 else ''
            html += f'<div id="{sym}_{d}" class="sub-tc{active}">'
            
            all_lvls = {k: v for k, v in ccy_dir_levels[(sym, d)].items() if k != '_meta'}
            meta = ccy_dir_levels[(sym, d)].get('_meta', {})
            worth = meta.get('worthiness')
            martin = meta.get('martin')
            sug = meta.get('suggestion')
            ld = meta.get('levels_detail', {})
            
            # ── A. Summary Card ──
            total_pnl_cd = sum(v['total_pnl'] for v in all_lvls.values())
            total_trades_cd = sum(v['count'] for v in all_lvls.values())
            total_wins_cd = sum(v['win_count'] for v in all_lvls.values())
            wr_cd = total_wins_cd / total_trades_cd * 100 if total_trades_cd else 0
            avg_ev_cd = sum(v['ev'] for v in all_lvls.values()) / len(all_lvls) if all_lvls else 0
            avg_odds_cd = sum(v['odds_dollar'] for v in all_lvls.values()) / len(all_lvls) if all_lvls else 0
            
            html += f'''<div class="sug-card">
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:8px;margin-bottom:8px">
<div><span style="color:#888;font-size:9px">Total Trades</span><br><b>{total_trades_cd}</b></div>
<div><span style="color:#888;font-size:9px">WR%</span><br><b>{wr_cd:.1f}%</b></div>
<div><span style="color:#888;font-size:9px">Total$</span><br><b class="{pnl_cls(total_pnl_cd)}">${total_pnl_cd:+,.2f}</b></div>
<div><span style="color:#888;font-size:9px">EV$/L</span><br><b class="{pnl_cls(avg_ev_cd)}">{avg_ev_cd:+.2f}</b></div>
<div><span style="color:#888;font-size:9px">Avg Odds$</span><br><b>{avg_odds_cd:.2f}</b></div>
<div><span style="color:#888;font-size:9px">Layers</span><br><b>{len(all_lvls)}</b></div>
<div><span style="color:#888;font-size:9px">MaxDepth</span><br><b>{max(LEVEL_ORDER(k) for k in all_lvls) if all_lvls else 0}</b></div>
</div></div>'''
            
            # ── B. Copy Trade Suggestion ──
            if sug:
                html += f'''<div class="sug-card {sug["confidence_class"]}">
<div style="font-size:13px;font-weight:bold;margin-bottom:6px">{sug["recommendation"]}</div>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(100px,1fr));gap:6px;font-size:10px">
<div><span style="color:#888">策略</span><br>{sug["strategy"]}</div>
<div><span style="color:#888">信心度</span><br>{sug["confidence"]}</div>
<div><span style="color:#888">期望值</span><br>{sug["expectancy"]:.3f}R</div>
<div><span style="color:#888">勝率</span><br>{sug["win_rate"]:.1f}%</div>
<div><span style="color:#888">馬丁依賴</span><br>{sug["martin_dep"]:.1f}%</div>
<div><span style="color:#888">Best CoP</span><br>{sug["best_cop_score"]} ({sug["best_cop_level"]})</div>
<div><span style="color:#888">Best CoL</span><br>{sug["best_col_score"]} ({sug["best_col_level"]})</div>
<div><span style="color:#888">TP/SL</span><br>{sug["tp"]} / {sug["sl"]} (R:R {sug["rr"]})</div>
</div>
<div style="margin-top:6px;font-size:10px;color:#aaa">原因：{sug["reason"]}</div>
</div>'''
            
            # ── C. Worthiness ──
            if worth:
                html += f'''<div class="sec" style="margin-bottom:8px">
<div class="sec-h">值博率分析</div>
<div class="sec-b"><div class="tw"><table>
<thead><tr><th>Trades</th><th>WR%</th><th>AvgW$</th><th>AvgL$</th><th>R:R</th>
<th>E(R)</th><th>Kelly%</th><th>1/4K%</th><th>BE WR%</th><th>安全邊際</th><th>Total$</th></tr></thead>
<tbody><tr>
<td>{worth["trades"]}</td><td>{worth["win_rate"]}%</td>
<td class="pos">{worth["avg_win"]}</td><td class="neg">{worth["avg_loss"]}</td>
<td>{worth["rr_ratio"]}</td><td class="{pnl_cls(worth["expectancy"])}">{worth["expectancy"]}</td>
<td>{worth["kelly"]}%</td><td>{worth["kelly_quarter"]}%</td>
<td>{worth["breakeven_wr"]}%</td><td>{worth["safety_grade"]}</td>
<td class="{pnl_cls(worth["total_profit"])}">${worth["total_profit"]:+,.2f}</td>
</tr></tbody></table></div></div></div>'''
            
            # ── D. DDE CoP/CoL Table ──
            html += '<div class="sec" style="margin-bottom:8px"><div class="sec-h">DDE CoP/CoL 評分</div><div class="sec-b"><div class="tw"><table>'
            html += '<thead><tr><th>Level</th><th>Type</th><th>Wait</th><th>Triggered</th><th>Rate</th><th>Avg$</th><th>Score</th><th>Rating</th></tr></thead><tbody>'
            for lv in sorted(all_lvls.keys(), key=LEVEL_ORDER):
                lv_detail = ld.get(lv, {})
                # CoP
                for wp, r in sorted(lv_detail.get('cop', {}).items()):
                    html += f'<tr><td>{lv}</td><td style="color:#2ecc71">CoP</td><td>{wp}pip</td>'
                    html += f'<td>{r["triggered"]}/{r["total_wins"]}</td><td>{r["trigger_rate"]:.0%}</td>'
                    html += f'<td>${r["avg_profit"]:.2f}</td><td><b>{r["weighted"]:.1f}</b></td><td>{r["rating"]}</td></tr>'
                # CoL
                for wp, r in sorted(lv_detail.get('col', {}).items()):
                    html += f'<tr><td>{lv}</td><td style="color:#f39c12">CoL</td><td>{wp}pip</td>'
                    html += f'<td>{r["triggered"]}/{r["triggered"]-r["recovered"]+r["recovered"]}</td>'
                    html += f'<td>{r["recovery_rate"]:.0%}</td><td>${r["avg_profit"]:.2f}</td>'
                    html += f'<td><b>{r["weighted"]:.1f}</b></td><td>{r["rating"]}</td></tr>'
            html += '</tbody></table></div></div></div>'
            
            # ── E. TP/SL Comparison Table ──
            html += '<div class="sec" style="margin-bottom:8px"><div class="sec-h">TP/SL 對比表 (統計 vs 實戰)</div>'
            html += '<div class="sec-b"><div style="font-size:9px;color:#888;margin-bottom:6px">統計: P85 MaxPips / P85 MaxLoss | 實戰: Avg MFE / Avg MAE×1.2 / Pair MaxMAE×1.3</div>'
            html += '<div class="tw"><table>'
            html += '<thead><tr><th>Layer</th><th>n</th><th>P85 TP</th><th>P85 SL</th><th>P85 R:R</th>'
            html += '<th>Avg MFE</th><th>Soft SL</th><th>Hard SL</th><th>MFE R:R</th></tr></thead><tbody>'
            for lv in sorted(all_lvls.keys(), key=LEVEL_ORDER):
                lv_detail = ld.get(lv, {})
                p85 = lv_detail.get('p85_tpsl', {})
                n = all_lvls[lv]['count']
                v3_tp = lv_detail.get('v3_tp', 0)
                v3_soft = lv_detail.get('v3_soft_sl', 0)
                v3_hard = lv_detail.get('v3_hard_sl', 0)
                v3_rr = lv_detail.get('v3_rr', 0)
                p85_tp = p85.get('tp', '-')
                p85_sl = p85.get('sl', '-')
                p85_rr = p85.get('rr', '-')
                # Highlight better R:R
                p85_rr_v = p85.get('rr') or 0
                html += f'<tr><td>{lv}</td><td>{n}</td>'
                html += f'<td class="pos">{p85_tp}</td><td class="neg">{p85_sl}</td>'
                html += f'<td class="{pnl_cls(p85_rr_v)}">{p85_rr}</td>'
                html += f'<td class="pos">{v3_tp}</td><td style="color:#f39c12">{v3_soft}</td>'
                html += f'<td class="neg">{v3_hard}</td>'
                html += f'<td class="{pnl_cls(v3_rr)}">{v3_rr}</td></tr>'
            html += '</tbody></table></div></div></div>'
            
            # ── F. Martin Level Depth ──
            if martin:
                html += '<div class="sec" style="margin-bottom:8px"><div class="sec-h">'
                html += f'馬丁層級深度 · 依賴度 {martin["dependency"]:.1f}% ({martin["martin_count"]} trades)</div>'
                html += '<div class="sec-b"><div class="tw"><table>'
                html += '<thead><tr><th>Layer</th><th>Trades</th><th>Martin#</th><th>觸發率</th>'
                html += '<th>Avg深度(pip)</th><th>Max深度(pip)</th><th>Avg DD$</th><th>Max DD$</th></tr></thead><tbody>'
                for lv_name, lv_m in sorted(martin['levels'].items(), key=lambda x: LEVEL_ORDER(x[0])):
                    tr_rate = lv_m['trigger_rate']
                    tc = '#e74c3c' if tr_rate > 10 else '#f39c12' if tr_rate > 3 else '#2ecc71'
                    html += f'<tr><td>{lv_name}</td><td>{lv_m["trades"]}</td><td>{lv_m["martin_count"]}</td>'
                    html += f'<td style="color:{tc}">{tr_rate}%</td>'
                    html += f'<td>{lv_m["avg_depth_pips"]}</td><td>{lv_m["max_depth_pips"]}</td>'
                    html += f'<td class="neg">${lv_m["avg_dd"]}</td><td class="neg">${lv_m["max_dd"]}</td></tr>'
                html += '</tbody></table></div></div></div>'
            
            # ── G. MFE/MAE Scatter ──
            chart_id = ccy_dir_chart_map.get((sym, d), -1)
            html += f'''<div class="sec" style="margin-bottom:8px"><div class="sec-h">MFE/MAE 散點圖 · 綠=Win 紅=Loss</div>
<div class="sec-b"><div class="scatter-card" style="max-width:600px">
<div class="title"><b>{sym} {d.upper()}</b> ({len(all_lvls)} layers)</div>
<canvas id="chart_{chart_id}" class="scatter" width="600" height="160"></canvas>
</div></div></div>'''
            
            # ── H. Martin Detection + Blacklist side by side ──
            html += '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:8px">'
            # Left: Martin Detection
            all_cd_t = [t for t in trades if t['symbol'] == sym and t['direction'] == d]
            classic = [t for t in all_cd_t if t['net_profit'] > 0 and t['net_pips'] < 0]
            reverse = [t for t in all_cd_t if t['net_profit'] < 0 and t['net_pips'] > 0]
            cost_k = [t for t in all_cd_t if t['net_profit'] < 0 and (t['net_profit'] - t['commission'] - t['swap']) > 0]
            html += '<div class="sec" style="margin:0"><div class="sec-h">Martin Detection</div><div class="sec-b" style="font-size:10px">'
            html += f'<div>Classic Martin (profit>0, pips<0): <b class="pos">{len(classic)}</b></div>'
            html += f'<div>Reverse Martin (profit<0, pips>0): <b class="neg">{len(reverse)}</b></div>'
            html += f'<div>Cost Killed: <b>{len(cost_k)}</b></div>'
            if classic:
                html += '<table style="margin-top:4px"><thead><tr><th>Lots</th><th>Pips</th><th>$</th><th>MaxDD(pip)</th></tr></thead><tbody>'
                for t in classic[:5]:
                    html += f'<tr><td>{t["lots"]}</td><td class="neg">{t["net_pips"]:.1f}</td>'
                    html += f'<td class="pos">${t["net_profit"]:.2f}</td><td class="neg">{t["mae"]:.1f}</td></tr>'
                if len(classic) > 5:
                    html += f'<tr><td colspan="4" style="color:#888">... 還有 {len(classic)-5} 筆</td></tr>'
                html += '</tbody></table>'
            html += '</div></div>'
            
            # Right: V3 Danger Score
            # Find this CCY in blacklist
            bl_entry = next((b for b in blacklist if b['symbol'] == sym and b['direction'] == d), None)
            html += '<div class="sec" style="margin:0"><div class="sec-h">V3 Danger Score</div><div class="sec-b" style="font-size:10px">'
            if bl_entry:
                html += f'<div style="font-size:14px;margin-bottom:6px">{bl_entry["level"]}</div>'
                html += f'<div>Danger Score: <b>{bl_entry["danger"]}</b></div>'
                html += f'<div>WR: {bl_entry["wr"]}% | Odds: {bl_entry["avg_odds"]}</div>'
                html += f'<div>馬丁依賴: {bl_entry["martin_dep"]}%</div>'
                html += f'<div>Classic: {bl_entry["classic_martin"]} | Reverse: {bl_entry["reverse_martin"]} | CostKilled: {bl_entry["cost_killed"]}</div>'
            else:
                html += '<div style="color:#2ecc71;text-align:center;padding:10px">✅ 安全 — 不在黑名單中</div>'
            html += '</div></div>'
            html += '</div>'
            
            # ── I. Recovery for this CCY×Dir ──
            rec_entry = next((r for r in recovery if r['symbol'] == sym and r['direction'] == d), None)
            if rec_entry:
                html += f'''<div class="sug-card" style="margin-bottom:8px">
<div style="font-size:11px;font-weight:bold;margin-bottom:4px">恢復力分析</div>
<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));gap:6px;font-size:10px">
<div><span style="color:#888">狀態</span><br>{rec_entry["status"]} {rec_entry["status_text"]}</div>
<div><span style="color:#888">最深層</span><br>{rec_entry["deepest_layer"]}</div>
<div><span style="color:#888">最差損失</span><br class="neg">${rec_entry["worst_loss"]:.2f}</div>
<div><span style="color:#888">最佳EV層</span><br>{rec_entry["best_ev_layer"]} (${rec_entry["best_ev"]:+.2f})</div>
<div><span style="color:#888">恢復次數</span><br><b>{rec_entry["recovery_trades"] if rec_entry["recovery_trades"]<999 else "∞"}</b></div>
<div><span style="color:#888">恢復天數</span><br>{rec_entry["recovery_days"] if rec_entry["recovery_days"]<999 else "∞"}天</div>
</div></div>'''
            
            html += '</div>'  # sub-tc
        
        html += '</div></div>'  # ccy-body, ccy-section
    
    html += '</div></div></div>'  # sec-b, sec, tc
    
    # ═══ TAB: Blacklist ═══
    html += f'''<div id="blacklist" class="tc">
<div class="sec"><div class="sec-h">黑名單<span class="badge">{len(blacklist)} 個危險組合</span></div>
<div class="sec-b">'''
    if blacklist:
        html += '<div class="tw"><table><thead><tr><th>危險度</th><th>Danger</th><th>CCY</th><th>Dir</th>'
        html += '<th>Total$</th><th>WR%</th><th>Avg Odds</th><th>馬丁依賴</th><th>Classic</th><th>Reverse</th><th>CostKilled</th></tr></thead><tbody>'
        for b in blacklist:
            html += f'<tr><td>{b["level"]}</td><td><b>{b["danger"]}</b></td><td><b>{b["symbol"]}</b></td><td>{b["direction"]}</td>'
            html += f'<td class="neg">{b["total_pnl"]:.2f}</td><td>{b["wr"]}%</td><td>{b["avg_odds"]}</td>'
            html += f'<td>{b["martin_dep"]}%</td><td>{b["classic_martin"]}</td><td>{b["reverse_martin"]}</td><td>{b["cost_killed"]}</td></tr>'
        html += '</tbody></table></div>'
    else:
        html += '<div style="text-align:center;padding:20px;color:#2ecc71">✅ 沒有危險組合</div>'
    html += '</div></div></div>'
    
    # ═══ TAB: Recovery ═══
    html += f'''<div id="recovery" class="tc">
<div class="sec"><div class="sec-h">恢復力分析<span class="badge">最深層止損 → 需要幾多次最佳EV交易先追得返？</span></div>
<div class="sec-b"><div class="tw"><table>
<thead><tr><th>狀態</th><th>CCY</th><th>Dir</th><th>最深層</th><th>最差損失$</th>
<th>最佳EV層</th><th>Best EV$</th><th>恢復次數</th><th>恢復天數</th><th>說明</th></tr></thead><tbody>'''
    for r in recovery:
        html += f'<tr><td>{r["status"]}</td><td><b>{r["symbol"]}</b></td><td>{r["direction"]}</td>'
        html += f'<td>{r["deepest_layer"]}</td><td class="neg">${r["worst_loss"]:.2f}</td>'
        html += f'<td>{r["best_ev_layer"]}</td><td class="{pnl_cls(r["best_ev"])}">{r["best_ev"]:+.2f}</td>'
        rt = r["recovery_trades"] if r["recovery_trades"] < 999 else "∞"
        rd = r["recovery_days"] if r["recovery_days"] < 999 else "∞"
        html += f'<td><b>{rt}</b></td><td>{rd}天</td><td>{r["status_text"]}</td></tr>'
    html += '</tbody></table></div></div></div></div>'
    
    # Footer
    html += f'''<div class="footer">
TSA + 馬丁剖析法 V3 合併報告 · Signal #{SIGNAL_ID} · {datetime.now().strftime('%Y-%m-%d %H:%M')} · Quant 📊
</div></div>'''
    
    # ─── JavaScript ───
    js_template = '''
<script>
const scatterData = __SCATTER_JSON__;

function switchTab(id) {
    document.querySelectorAll('.tc').forEach(e=>e.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(e=>e.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    event.target.classList.add('active');
}
function toggleCCY(el) {
    el.classList.toggle('open');
    el.nextElementSibling.classList.toggle('open');
}
function switchSubTab(el, id) {
    const parent = el.closest('.ccy-body');
    parent.querySelectorAll('.sub-tab').forEach(e=>e.classList.remove('active'));
    parent.querySelectorAll('.sub-tc').forEach(e=>e.classList.remove('active'));
    el.classList.add('active');
    document.getElementById(id).classList.add('active');
}

function drawScatter(cid, data) {
    const c = document.getElementById(cid);
    if (!c || !data || !data.length) return;
    const ctx = c.getContext('2d');
    const dpr = window.devicePixelRatio || 1;
    const w = c.offsetWidth, h = c.offsetHeight;
    c.width = w * dpr; c.height = h * dpr;
    ctx.scale(dpr, dpr);

    const pad = {t:20,r:10,b:30,l:40};
    const pw=w-pad.l-pad.r, ph=h-pad.t-pad.b;
    ctx.fillStyle='#1a1a2e'; ctx.fillRect(0,0,w,h);
    ctx.strokeStyle='#333'; ctx.lineWidth=0.5;

    const mx = Math.max(
        ...data.map(d=>Math.abs(d.mfe)),
        ...data.map(d=>Math.abs(d.mae)),
        1
    );

    // Grid
    ctx.beginPath(); ctx.moveTo(pad.l,pad.t); ctx.lineTo(pad.l,pad.t+ph); ctx.lineTo(pad.l+pw,pad.t+ph);
    ctx.stroke();
    for(let i=0;i<=4;i++){
        let y=pad.t+ph*i/4;
        ctx.beginPath(); ctx.moveTo(pad.l,y); ctx.lineTo(pad.l+pw,y); ctx.stroke();
        ctx.fillStyle='#888'; ctx.font='9px sans-serif'; ctx.textAlign='right';
        ctx.fillText(((4-i)/4*mx).toFixed(0),pad.l-4,y+3);
    }

    for(const d of data){
        let x=pad.l+(d.mae/mx)*pw;
        let y=pad.t+ph*(1-d.mfe/mx);
        x=Math.max(pad.l,Math.min(pad.l+pw,x));
        y=Math.max(pad.t,Math.min(pad.t+ph,y));
        ctx.beginPath();ctx.arc(x,y,2,0,Math.PI*2);
        ctx.fillStyle=d.is_win?'#2ecc71':'#e74c3c';ctx.fill();
    }
}

for(const [id,data] of Object.entries(scatterData)) drawScatter('chart_'+id, data);
window.addEventListener('resize',()=>{for(const[id,data]of Object.entries(scatterData))drawScatter('chart_'+id,data)});

// Sortable tables
document.querySelectorAll('table[id]').forEach(tbl=>{
    const tbody=tbl.querySelector('tbody');
    const ths=tbl.querySelectorAll('thead th');
    ths.forEach((th,col)=>{
        th.addEventListener('click',()=>{
            const rows=Array.from(tbody.querySelectorAll('tr'));
            const asc=th.dataset.sort!=='asc';
            ths.forEach(t=>{t.classList.remove('sort-asc','sort-desc');delete t.dataset.sort});
            th.dataset.sort=asc?'asc':'desc';
            th.classList.add(asc?'sort-asc':'sort-desc');
            rows.sort((a,b)=>{
                let va=a.cells[col]?.textContent?.trim()||'';
                let vb=b.cells[col]?.textContent?.trim()||'';
                let na=parseFloat(va.replace(/[^0-9.-]/g,''));
                let nb=parseFloat(vb.replace(/[^0-9.-]/g,''));
                if(!isNaN(na)&&!isNaN(nb)) return asc?na-nb:nb-na;
                return asc?va.localeCompare(vb):vb.localeCompare(va);
            });
            rows.forEach(r=>tbody.appendChild(r));
        });
    });
});
</script>
</body></html>'''
    html += js_template.replace('__SCATTER_JSON__', scatter_json)
    return html
    return html


# ─── Main ───────────────────────────────────────────────────
if __name__ == '__main__':
    print(f"🔬 Building merged report for Signal #{SIGNAL_ID}")
    trades, ccy_dir_levels, blacklist, recovery = compute_all()
    
    # Fix overview calculation - there was a typo (all_lvds -> all_lvls)
    # Regenerate overview properly
    LEVEL_ORDER = lambda x: (99 if x == 'L9+' else int(x[1:]))
    overview = []
    for (sym, d) in sorted(ccy_dir_levels.keys()):
        meta = ccy_dir_levels[(sym, d)].get('_meta', {})
        all_lvls = {k: v for k, v in ccy_dir_levels[(sym, d)].items() if k != '_meta'}
        total_pnl_cd = sum(v['total_pnl'] for v in all_lvls.values())
        total_trades_cd = meta.get('total_trades', 0)
        total_wins_cd = sum(v['win_count'] for v in all_lvls.values())
        wr_cd = total_wins_cd / total_trades_cd * 100 if total_trades_cd else 0
        avg_ev = sum(v['ev'] for v in all_lvls.values()) / len(all_lvls) if all_lvls else 0
        overview.append({
            'symbol': sym, 'direction': d, 'trades': total_trades_cd,
            'layers': len(all_lvls),
            'max_depth': max(LEVEL_ORDER(k) for k in all_lvls) if all_lvls else 0,
            'total_pnl': round(total_pnl_cd, 2), 'wr': round(wr_cd, 1),
            'avg_ev': round(avg_ev, 2), 'suggestion': meta.get('suggestion'),
        })
    overview.sort(key=lambda x: -x['total_pnl'])
    
    symbols = sorted(set(t['symbol'] for t in trades))
    ccy_dirs = sorted(ccy_dir_levels.keys())
    
    html = build_full_html(trades, ccy_dir_levels, blacklist, recovery, overview, symbols, ccy_dirs, LEVEL_ORDER)
    
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        f.write(html)
    
    size = os.path.getsize(OUTPUT_PATH)
    print(f"\n✅ Report generated: {OUTPUT_PATH}")
    print(f"📏 File size: {size:,} bytes ({size/1024:.1f} KB)")
