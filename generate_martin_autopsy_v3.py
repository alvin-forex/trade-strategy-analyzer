#!/usr/bin/env python3
"""
馬丁剖析法 V3 - Martin Autopsy V3

對單一 Signal 的 CSV 交易數據進行完整馬丁剖析分析,生成 HTML 報告。

分析模塊:
  Part 1: CCY × Direction 總覽表
  Part 2: MFE/MAE 散點分析(含圖表)
  Part 3: A 級以上 TP/SL 建議(混合方案)
  Part 4: A 級以上排行榜
  Part 5: 黑名單(Danger Score)
  Part 6: 恢復力分析

用法:
  python generate_martin_autopsy_v3.py <signal_csv> [--output OUTPUT_PATH]
"""

import csv
import json
import math
import sys
import os
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Tuple, Optional

# ─── 常量 ───────────────────────────────────────────────────

MARTIN_LAYERS = [0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.10, 0.12, 0.15, 0.21, 0.23, 0.34, 0.38, 0.51, 0.68, 0.77, 1.15, 2.59, 3.89, 5.84, 8.76]

# 評分權重(V3 評級系統)
RATING_WEIGHTS = {
    'wr': 0.25,      # Win Rate
    'ev': 0.30,      # Expected Value
    'odds': 0.20,    # Odds (Pip-based)
    'count': 0.15,   # Sample size
    'hold': 0.10,    # Holding time efficiency
}

# ─── 數據載入 ───────────────────────────────────────────────

def load_trades(csv_path: str) -> List[dict]:
    """從 CSV 載入交易數據"""
    trades = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            trade_type = row.get('Type', '').strip().lower()
            if trade_type not in ('buy', 'sell'):
                continue
            try:
                trade = {
                    'symbol': row.get('Symbol', '').strip(),
                    'direction': trade_type,
                    'lots': abs(float(row.get('Lots', 0))),
                    'net_profit': float(row.get('Net Profit', 0)),
                    'net_pips': float(row.get('Net Pips', 0)),
                    'max_profit': float(row.get('Max Profit', 0)),
                    'max_loss': float(row.get('Max Loss', 0)),
                    'mfe': float(row.get('Max Pips', 0)),         # MFE = Max Favorable Excursion
                    'mae': abs(float(row.get('Max Loss Pips', 0))),  # MAE = Max Adverse Excursion
                    'holding_hours': float(row.get('Holding Time (Hours)', 0)) if row.get('Holding Time (Hours)') else 0,
                    'commission': float(row.get('Commission', 0)),
                    'swap': float(row.get('Swap', 0)),
                    'comment': row.get('Comment', ''),
                    'open_time': row.get('Open Time', ''),
                }
                if trade['symbol']:
                    trades.append(trade)
            except (ValueError, TypeError):
                continue
    return trades


def infer_layer(lots: float) -> float:
    """從 Lots 值推斷馬丁層級"""
    # 精確匹配
    for layer in MARTIN_LAYERS:
        if abs(lots - layer) < 0.005:
            return layer
    # 最近匹配
    closest = min(MARTIN_LAYERS, key=lambda x: abs(x - lots))
    if abs(closest - lots) / max(lots, 0.001) < 0.15:
        return closest
    return lots  # 回退:返回原始值


def assign_layer_index(lots_list: List[float]) -> Dict[float, int]:
    """對 Lots 排序,生成 layer_idx (1-based)"""
    unique_lots = sorted(set(lots_list))
    return {lot: idx + 1 for idx, lot in enumerate(unique_lots)}


# ─── 核心計算 ───────────────────────────────────────────────

def compute_layer_stats(trades: List[dict]) -> Dict[str, dict]:
    """
    計算每個 (CCY, Direction, Layer) 的完整統計

    返回: {(symbol, direction, layer_label): {stats}}
    """
    # 按 (CCY, Direction) 分組
    ccy_dir_trades = defaultdict(list)
    for t in trades:
        key = (t['symbol'], t['direction'])
        ccy_dir_trades[key].append(t)

    results = {}

    for (symbol, direction), ccy_trades in ccy_dir_trades.items():
        # 計算 layer index
        lots_in_group = sorted(set(t['lots'] for t in ccy_trades))
        lot_to_idx = {lot: i+1 for i, lot in enumerate(lots_in_group)}
        max_depth = len(lots_in_group)

        # 按層級分組
        layer_trades = defaultdict(list)
        for t in ccy_trades:
            layer_label = f"L{t['lots']}"
            layer_trades[layer_label].append(t)

        for layer_label, lt in layer_trades.items():
            count = len(lt)
            if count == 0:
                continue

            wins = [t for t in lt if t['net_profit'] > 0]
            losses = [t for t in lt if t['net_profit'] <= 0]
            win_count = len(wins)
            loss_count = len(losses)

            wr = (win_count / count * 100) if count > 0 else 0
            total_pnl = sum(t['net_profit'] for t in lt)
            avg_win = sum(t['net_profit'] for t in wins) / win_count if win_count else 0
            avg_loss = abs(sum(t['net_profit'] for t in losses) / loss_count) if loss_count else 0

            ev = (wr / 100 * avg_win) - ((1 - wr / 100) * avg_loss)

            avg_win_pips = sum(t['net_pips'] for t in wins) / win_count if win_count else 0
            avg_loss_pips = abs(sum(t['net_pips'] for t in losses) / loss_count) if loss_count else 0

            odds_dollar = avg_win / avg_loss if avg_loss > 0 else 999
            odds_pips = avg_win_pips / avg_loss_pips if avg_loss_pips > 0 else 999

            avg_hold = sum(t['holding_hours'] for t in lt) / count

            # MFE/MAE
            mfe_values = [t['mfe'] for t in lt]
            mae_values = [t['mae'] for t in lt]

            avg_mfe = sum(mfe_values) / len(mfe_values) if mfe_values else 0
            max_mfe = max(mfe_values) if mfe_values else 0
            med_mfe = sorted(mfe_values)[len(mfe_values)//2] if mfe_values else 0

            avg_mae = sum(mae_values) / len(mae_values) if mae_values else 0
            max_mae = max(mae_values) if mae_values else 0
            med_mae = sorted(mae_values)[len(mae_values)//2] if mae_values else 0

            # 該層 lots 的 layer_idx
            sample_lots = lt[0]['lots']
            layer_idx = lot_to_idx.get(sample_lots, 1)

            key = f"{symbol}_{direction}_{layer_label}"
            results[key] = {
                'symbol': symbol,
                'direction': direction,
                'layer_label': layer_label,
                'lots': sample_lots,
                'layer_idx': layer_idx,
                'max_depth': max_depth,
                'count': count,
                'win_count': win_count,
                'loss_count': loss_count,
                'wr': round(wr, 1),
                'total_pnl': round(total_pnl, 2),
                'ev': round(ev, 2),
                'avg_win': round(avg_win, 2),
                'avg_loss': round(avg_loss, 2),
                'avg_win_pips': round(avg_win_pips, 1),
                'avg_loss_pips': round(avg_loss_pips, 1),
                'odds_dollar': round(odds_dollar, 2) if odds_dollar < 100 else 999,
                'odds_pips': round(odds_pips, 2) if odds_pips < 100 else 999,
                'avg_hold': round(avg_hold, 1),
                'avg_mfe': round(avg_mfe, 1),
                'max_mfe': round(max_mfe, 1),
                'med_mfe': round(med_mfe, 1),
                'avg_mae': round(avg_mae, 1),
                'max_mae': round(max_mae, 1),
                'med_mae': round(med_mae, 1),
                # 原始交易數據(用於散點圖)
                'trade_details': [
                    {
                        'net_pips': t['net_pips'],
                        'mfe': t['mfe'],
                        'mae': t['mae'],
                        'net_profit': t['net_profit'],
                        'is_win': t['net_profit'] > 0,
                        'lots': t['lots'],
                        'holding_hours': t['holding_hours'],
                    }
                    for t in lt
                ],
            }

    return results


# ─── 評級系統 ───────────────────────────────────────────────

def compute_rating(stats: dict) -> str:
    """
    計算層級評級:S+, S, A, B, C, D, E
    基於 WR, EV, Odds, Count, Hold
    """
    wr = stats['wr']
    ev = stats['ev']
    odds = min(stats['odds_pips'], stats['odds_dollar'])  # 取較低的賠率
    count = stats['count']

    # 綜合評分 (0-100)
    score = 0

    # WR 評分 (0-30)
    if wr >= 80:
        score += 30
    elif wr >= 70:
        score += 25
    elif wr >= 60:
        score += 18
    elif wr >= 50:
        score += 10
    else:
        score += max(0, wr / 5)

    # EV 評分 (0-30)
    if ev >= 20:
        score += 30
    elif ev >= 10:
        score += 25
    elif ev >= 5:
        score += 18
    elif ev >= 0:
        score += 10
    else:
        score += max(0, 10 + ev / 2)

    # Odds 評分 (0-20)
    if odds >= 2.0:
        score += 20
    elif odds >= 1.5:
        score += 15
    elif odds >= 1.0:
        score += 10
    else:
        score += max(0, odds * 10)

    # Count 評分 (0-15)
    if count >= 10:
        score += 15
    elif count >= 5:
        score += 12
    elif count >= 3:
        score += 8
    else:
        score += max(0, count * 2)

    # Hold 評分 (0-5): 越短越好(效率)
    hold = stats['avg_hold']
    if hold <= 24:
        score += 5
    elif hold <= 72:
        score += 4
    elif hold <= 168:
        score += 3
    elif hold <= 360:
        score += 2
    else:
        score += 1

    # 評級映射
    if score >= 85:
        return 'S+'
    elif score >= 70:
        return 'S'
    elif score >= 55:
        return 'A'
    elif score >= 40:
        return 'B'
    elif score >= 25:
        return 'C'
    elif score >= 15:
        return 'D'
    else:
        return 'E'


def compute_score(stats: dict) -> float:
    """計算層級評分(0-100),與 compute_rating 相同邏輯"""
    wr = stats['wr']
    ev = stats['ev']
    odds = min(stats['odds_pips'], stats['odds_dollar'])
    count = stats['count']
    score = 0
    score += 30 if wr >= 80 else 25 if wr >= 70 else 18 if wr >= 60 else 10 if wr >= 50 else max(0, wr / 5)
    score += 30 if ev >= 20 else 25 if ev >= 10 else 18 if ev >= 5 else 10 if ev >= 0 else max(0, 10 + ev / 2)
    score += 20 if odds >= 2.0 else 15 if odds >= 1.5 else 10 if odds >= 1.0 else max(0, odds * 10)
    score += 15 if count >= 10 else 12 if count >= 5 else 8 if count >= 3 else max(0, count * 2)
    hold = stats['avg_hold']
    score += 5 if hold <= 24 else 4 if hold <= 72 else 3 if hold <= 168 else 2 if hold <= 360 else 1
    return round(score, 1)


# ─── Part 1: CCY × Direction 總覽 ──────────────────────────

def build_ccy_direction_summary(layer_stats: Dict) -> List[dict]:
    """Part 1: CCY × Direction 匯總"""
    ccy_dir_data = defaultdict(list)
    for key, stats in layer_stats.items():
        ccy_key = (stats['symbol'], stats['direction'])
        ccy_dir_data[ccy_key].append(stats)

    summary = []
    for (symbol, direction), layers in ccy_dir_data.items():
        total_trades = sum(l['count'] for l in layers)
        total_pnl = sum(l['total_pnl'] for l in layers)
        total_pips = sum(l['avg_win_pips'] * l['win_count'] + (-l['avg_loss_pips']) * l['loss_count'] for l in layers)
        total_wins = sum(l['win_count'] for l in layers)
        wr = total_wins / total_trades * 100 if total_trades > 0 else 0

        avg_ev = sum(l['ev'] for l in layers) / len(layers) if layers else 0
        avg_win_pips = sum(l['avg_win_pips'] for l in layers) / len(layers) if layers else 0
        avg_loss_pips = sum(l['avg_loss_pips'] for l in layers) / len(layers) if layers else 0
        avg_odds_d = sum(l['odds_dollar'] for l in layers) / len(layers) if layers else 0
        avg_odds_p = sum(l['odds_pips'] for l in layers) / len(layers) if layers else 0
        avg_mfe = sum(l['avg_mfe'] for l in layers) / len(layers) if layers else 0
        avg_mae = sum(l['avg_mae'] for l in layers) / len(layers) if layers else 0
        max_mae = max(l['max_mae'] for l in layers) if layers else 0

        summary.append({
            'symbol': symbol,
            'direction': direction,
            'trades': total_trades,
            'layers': len(layers),
            'max_depth': max(l['max_depth'] for l in layers),
            'total_pnl': round(total_pnl, 2),
            'total_pips': round(total_pips, 1),
            'wr': round(wr, 1),
            'avg_ev': round(avg_ev, 2),
            'avg_win_pips': round(avg_win_pips, 1),
            'avg_loss_pips': round(avg_loss_pips, 1),
            'avg_odds_dollar': round(avg_odds_d, 2),
            'avg_odds_pips': round(avg_odds_p, 2),
            'avg_mfe': round(avg_mfe, 1),
            'avg_mae': round(avg_mae, 1),
            'max_mae': round(max_mae, 1),
        })

    # 按 Total PnL 降序
    summary.sort(key=lambda x: x['total_pnl'], reverse=True)
    return summary


# ─── Part 3: TP/SL 計算 ─────────────────────────────────────

def compute_tp_sl(layer_stats: Dict, min_rating: str = 'A') -> List[dict]:
    """
    Part 3: A 級以上 TP/SL 建議
    TP = Avg MFE
    Soft SL = Avg MAE
    Hard SL = Pair Max MAE
    """
    rating_order = {'S+': 6, 'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1, 'E': 0}
    min_level = rating_order.get(min_rating, 4)

    # 計算每個 CCY×Dir 的 max_mae
    ccy_dir_max_mae = defaultdict(float)
    for key, stats in layer_stats.items():
        ccy_key = (stats['symbol'], stats['direction'])
        ccy_dir_max_mae[ccy_key] = max(ccy_dir_max_mae[ccy_key], stats['max_mae'])

    results = []
    for key, stats in layer_stats.items():
        if stats['count'] < 2:
            continue

        rating = compute_rating(stats)
        if rating_order.get(rating, 0) < min_level:
            continue

        tp = stats['avg_mfe']
        soft_sl = stats['avg_mae']
        hard_sl = stats['max_mae']  # 用該層自身的 Max MAE(不乘倍數)
        rr = tp / soft_sl if soft_sl > 0 else 0

        results.append({
            'rating': rating,
            'symbol': stats['symbol'],
            'direction': stats['direction'],
            'layer': stats['layer_label'],
            'count': stats['count'],
            'wr': stats['wr'],
            'ev': stats['ev'],
            'odds_dollar': stats['odds_dollar'],
            'odds_pips': stats['odds_pips'],
            'tp': round(tp, 1),
            'soft_sl': round(soft_sl, 1),
            'hard_sl': round(hard_sl, 1),
            'rr': round(rr, 2),
            'total_pnl': stats['total_pnl'],
            'avg_hold': stats['avg_hold'],
        })

    # 按 Rating 降序, EV 降序
    results.sort(key=lambda x: (-rating_order.get(x['rating'], 0), -x['ev']))
    return results


# ─── Part 5: 黑名單 ─────────────────────────────────────────

def compute_blacklist(layer_stats: Dict) -> List[dict]:
    """Part 5: 黑名單(Danger Score)"""
    ccy_dir_data = defaultdict(list)
    for key, stats in layer_stats.items():
        ccy_key = (stats['symbol'], stats['direction'])
        ccy_dir_data[ccy_key].append(stats)

    blacklist = []
    for (symbol, direction), layers in ccy_dir_data.items():
        total_pnl = sum(l['total_pnl'] for l in layers)
        total_trades = sum(l['count'] for l in layers)
        total_wins = sum(l['win_count'] for l in layers)
        wr = total_wins / total_trades * 100 if total_trades > 0 else 0

        avg_odds = sum(l['odds_pips'] for l in layers) / len(layers) if layers else 0
        avg_ev = sum(l['ev'] for l in layers) / len(layers) if layers else 0
        worst_ev = min(l['ev'] for l in layers) if layers else 0

        danger = 0.0
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

        if danger >= 1:
            # 找最深層級
            deepest = max(layers, key=lambda x: x['layer_idx'])
            avg_hold_all = sum(l['avg_hold'] * l['count'] for l in layers) / max(total_trades, 1)
            blacklist.append({
                'symbol': symbol,
                'direction': direction,
                'total_pnl': round(total_pnl, 2),
                'wr': round(wr, 1),
                'avg_odds': round(avg_odds, 2),
                'avg_ev': round(avg_ev, 2),
                'worst_ev': round(worst_ev, 2),
                'worst_layer': deepest['layer_label'],
                'danger': round(danger, 1),
                'level': '💀 DEADLY' if danger > 5 else '⚠️ WARNING',
                'avg_hold': round(avg_hold_all, 1),
            })

    blacklist.sort(key=lambda x: -x['danger'])
    return blacklist


# ─── Part 6: 恢復力分析 ─────────────────────────────────────

def compute_recovery(layer_stats: Dict) -> List[dict]:
    """Part 6: 恢復力分析"""
    ccy_dir_data = defaultdict(list)
    for key, stats in layer_stats.items():
        ccy_key = (stats['symbol'], stats['direction'])
        ccy_dir_data[ccy_key].append(stats)

    results = []
    for (symbol, direction), layers in ccy_dir_data.items():
        # 最深層級
        deepest = max(layers, key=lambda x: x['layer_idx'])
        worst_loss = deepest['avg_loss'] if deepest['loss_count'] > 0 else (deepest['lots'] * 100)

        # 最佳 EV 層級
        best_ev_layer = max(layers, key=lambda x: x['ev'])
        best_ev = best_ev_layer['ev']

        if best_ev > 0:
            recovery_trades = math.ceil(worst_loss / best_ev)
        else:
            recovery_trades = 999

        # 頻率估算(每月)
        total_trades = sum(l['count'] for l in layers)
        freq_month = total_trades / 3  # 假設數據覆蓋約3個月
        if freq_month > 0:
            recovery_days = round(recovery_trades / freq_month * 30, 0)
        else:
            recovery_days = 999

        if recovery_trades > 20 or best_ev <= 0:
            status = '🔴'
            status_text = '無法恢復'
        elif recovery_trades >= 5:
            status = '🟡'
            status_text = f'需時 ({recovery_trades}次)'
        else:
            status = '🟢'
            status_text = f'安全 ({recovery_trades}次)'

        results.append({
            'symbol': symbol,
            'direction': direction,
            'deepest_layer': deepest['layer_label'],
            'worst_loss': round(worst_loss, 2),
            'best_ev_layer': best_ev_layer['layer_label'],
            'best_ev': round(best_ev, 2),
            'recovery_trades': recovery_trades,
            'recovery_days': int(recovery_days),
            'status': status,
            'status_text': status_text,
            'avg_hold': round(sum(l['avg_hold'] * l['count'] for l in layers) / max(total_trades, 1), 1),
        })

    # 按恢復次數升序
    results.sort(key=lambda x: x['recovery_trades'])
    return results


# ─── Part 7: CCY 層級 TP/SL 盈利分析 ──────────────────────────

def compute_ccy_layer_profitability(layer_stats: Dict) -> Dict[str, List[dict]]:
    """
    Part 7: 按 CCY 分組,計算每層用 CCY 總覽 TP/SL 參數嘅盈利情況。

    邏輯:
    1. 計算每個 CCY×Direction 嘅總覽統計(整體 WR, avg MFE, avg MAE)
    2. 對每層,用該層嘅實際 TP/SL 數據,計算:
       - 實際盈虧 (Total P&L)
       - 盈利概率 = 該層勝率
       - 期望值 = WR × AvgWin - (1-WR) × AvgLoss
       - 與 CCY 平均嘅偏差
    3. 返回按 CCY 分組嘅結果
    """
    # 先按 CCY×Direction 分組
    ccy_dir_data = defaultdict(list)
    for key, stats in layer_stats.items():
        ccy_key = (stats['symbol'], stats['direction'])
        ccy_dir_data[ccy_key].append(stats)

    results = {}

    for (symbol, direction), layers in ccy_dir_data.items():
        # CCY 總覽統計
        total_trades = sum(l['count'] for l in layers)
        total_pnl = sum(l['total_pnl'] for l in layers)
        total_wins = sum(l['win_count'] for l in layers)
        total_losses = sum(l['loss_count'] for l in layers)
        ccy_wr = (total_wins / total_trades * 100) if total_trades > 0 else 0

        # CCY 加權平均 TP/SL
        total_win_amount = sum(l['avg_win'] * l['win_count'] for l in layers)
        total_loss_amount = sum(l['avg_loss'] * l['loss_count'] for l in layers)
        ccy_avg_win = total_win_amount / total_wins if total_wins > 0 else 0
        ccy_avg_loss = total_loss_amount / total_losses if total_losses > 0 else 0

        # CCY 加權平均 MFE/MAE
        ccy_avg_mfe = sum(l['avg_mfe'] * l['count'] for l in layers) / total_trades if total_trades > 0 else 0
        ccy_avg_mae = sum(l['avg_mae'] * l['count'] for l in layers) / total_trades if total_trades > 0 else 0
        ccy_max_mae = max(l['max_mae'] for l in layers) if layers else 0

        # CCY 整體 EV
        ccy_ev = (ccy_wr / 100 * ccy_avg_win) - ((1 - ccy_wr / 100) * ccy_avg_loss)

        layer_rows = []
        for ls in sorted(layers, key=lambda x: x['lots']):
            # 該層用 CCY TP/SL 參數嘅模擬結果
            # TP = CCY avg MFE, SL = CCY avg MAE
            layer_tp = ls['avg_mfe']  # 該層實際 TP 能力
            layer_sl = ls['avg_mae']  # 該層實際 SL 風險

            # 用 CCY 整體做基準
            tp_vs_ccy = ((layer_tp - ccy_avg_mfe) / ccy_avg_mfe * 100) if ccy_avg_mfe > 0 else 0
            sl_vs_ccy = ((layer_sl - ccy_avg_mae) / ccy_avg_mae * 100) if ccy_avg_mae > 0 else 0

            # 該層實際盈虧
            is_profitable = ls['total_pnl'] > 0
            profit_margin = ls['total_pnl'] / (ls['count'] * max(ls['avg_loss'], 1)) * 100 if ls['count'] > 0 else 0

            # TP/SL 盈利判定:用該層 WR + TP/SL 計算期望收益
            # 如果 TP > SL (MFE > MAE),且有正 WR,就有機會盈利
            tp_sl_ratio = layer_tp / layer_sl if layer_sl > 0 else 999

            # 用 Kelly Criterion 簡化版判定邊緣
            # Edge = WR × TP - (1-WR) × SL
            edge = (ls['wr'] / 100 * layer_tp) - ((1 - ls['wr'] / 100) * layer_sl)

            layer_rows.append({
                'layer_label': ls['layer_label'],
                'lots': ls['lots'],
                'layer_idx': ls['layer_idx'],
                'count': ls['count'],
                'win_count': ls['win_count'],
                'loss_count': ls['loss_count'],
                'wr': ls['wr'],
                'total_pnl': ls['total_pnl'],
                'ev': ls['ev'],
                # TP/SL 數據
                'tp_pips': layer_tp,
                'sl_pips': layer_sl,
                'hard_sl': ls['max_mae'],
                'tp_sl_ratio': round(tp_sl_ratio, 2) if tp_sl_ratio < 100 else 999,
                'edge': round(edge, 2),
                # vs CCY 偏差
                'tp_vs_ccy': round(tp_vs_ccy, 1),
                'sl_vs_ccy': round(sl_vs_ccy, 1),
                # 盈利判定
                'is_profitable': is_profitable,
                'profit_margin': round(profit_margin, 1),
                'rating': compute_rating(ls),
            })

        results[f"{symbol}_{direction}"] = {
            'symbol': symbol,
            'direction': direction,
            'ccy_wr': round(ccy_wr, 1),
            'ccy_total_pnl': round(total_pnl, 2),
            'ccy_avg_win': round(ccy_avg_win, 2),
            'ccy_avg_loss': round(ccy_avg_loss, 2),
            'ccy_ev': round(ccy_ev, 2),
            'ccy_avg_mfe': round(ccy_avg_mfe, 1),
            'ccy_avg_mae': round(ccy_avg_mae, 1),
            'ccy_max_mae': round(ccy_max_mae, 1),
            'total_trades': total_trades,
            'layers': layer_rows,
            'profitable_layers': sum(1 for l in layer_rows if l['is_profitable']),
            'total_layers': len(layer_rows),
        }

    return results


# ─── HTML 生成 ───────────────────────────────────────────────



def generate_html(signal_id: str, trades: List[dict], layer_stats: Dict,
                  ccy_summary: List[dict], tp_sl_data: List[dict],
                  blacklist: List[dict], recovery: List[dict],
                  ccy_profitability: Dict[str, dict] = None) -> str:
    """生成完整 HTML 報告 - 按 CCY×Direction 分組,每組包含 Part 1-7"""

    total_trades = len(trades)
    total_pnl = sum(t['net_profit'] for t in trades)
    total_wins = sum(1 for t in trades if t['net_profit'] > 0)
    wr = total_wins / total_trades * 100 if total_trades else 0
    avg_hold = sum(t['holding_hours'] for t in trades) / total_trades if total_trades else 0
    total_layers = len(layer_stats)
    num_ccy = len(ccy_summary)

    rating_order = {'S+': 6, 'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1, 'E': 0}

    def rc(r):
        return {'S+':'#FFD700','S':'#9b59b6','A':'#2ecc71','B':'#3498db',
                'C':'#f39c12','D':'#95a5a6','E':'#e74c3c'}.get(r,'#999')

    def rb(r):
        return {'S+':'#FFF8E1','S':'#F3E5F5','A':'#E8F5E9','B':'#E3F2FD',
                'C':'#FFF3E0','D':'#F5F5F5','E':'#FFEBEE'}.get(r,'#F5F5F5')

    def pp(v):
        return '+' if v > 0 else ''

    # ── Group by CCY×Direction, sort by Total P&L desc ──
    ccy_groups = defaultdict(dict)
    for key, stats in layer_stats.items():
        ccy_groups[(stats['symbol'], stats['direction'])][key] = stats

    # Sort: group same CCY together, BUY before SELL, CCY alphabetical
    sorted_ccy = sorted(ccy_groups.items(),
        key=lambda x: (x[0][0], 0 if x[0][1]=='buy' else 1))

    # ── Global bar chart data ──
    bar_groups = []
    # Build from sorted_ccy to keep same CCY adjacent (BUY/SELL together)
    for (symbol, direction), layers in sorted_ccy:
        agg_pnl = sum(s['total_pnl'] for s in layers.values())
        agg_pips = sum(s['net_pips'] for s in layers.values() if 'net_pips' in s)
        # find in ccy_summary
        match = [s for s in ccy_summary if s['symbol']==symbol and s['direction']==direction]
        if match:
            s = match[0]
            bar_groups.append({
                'label': f"{symbol} {direction}",
                'total_pnl': agg_pnl,
                'total_pips': agg_pips,
                'win_pip': s['avg_win_pips'],
                'loss_pip': s['avg_loss_pips'],
            })
        else:
            bar_groups.append({
                'label': f"{symbol} {direction}",
                'total_pnl': agg_pnl,
                'total_pips': agg_pips,
                'win_pip': 0,
                'loss_pip': 0,
            })
    max_abs_pnl = max((abs(s['total_pnl']) for s in ccy_summary), default=1) or 1
    max_abs_pip = max((max(abs(s['avg_win_pips']), abs(s['avg_loss_pips'])) for s in ccy_summary), default=1) or 1
    max_abs_total_pip = max((abs(g['total_pips']) for g in bar_groups), default=1) or 1

    # ── SVG builders ──
    def build_merged_bar_svg(groups, max_pnl, max_pip):
        """Combined $ + PIP bar chart - each row shows Total$ (thick) and Total PIP (thin)"""
        if not groups: return '<p style="color:#888;text-align:center;padding:20px">無數據</p>'
        n = len(groups); svg_h = max(200, n*42+70); gap = 42; lm = 70; rm = 70; cw = 780; pw = cw-lm-rm; zx = lm+pw//2
        svg = f'<svg viewBox="0 0 {cw} {svg_h}" style="width:100%;height:auto;font-family:sans-serif" xmlns="http://www.w3.org/2000/svg">'
        svg += f'<rect width="{cw}" height="{svg_h}" fill="#0a0a18" rx="6"/>'
        svg += f'<line x1="{zx}" y1="30" x2="{zx}" y2="{svg_h-35}" stroke="#333" stroke-width="1"/>'
        for frac in [0.25,0.5,0.75,1.0]:
            gx=lm+pw*frac; svg += f'<line x1="{gx:.1f}" y1="30" x2="{gx:.1f}" y2="{svg_h-35}" stroke="#1a1a2a" stroke-width="0.5"/>'
            gx2=lm+pw*(1-frac); svg += f'<line x1="{gx2:.1f}" y1="30" x2="{gx2:.1f}" y2="{svg_h-35}" stroke="#1a1a2a" stroke-width="0.5"/>'
        svg += f'<text x="{lm}" y="18" fill="#e74c3c" font-size="9" text-anchor="start">-$ / -PIP</text>'
        svg += f'<text x="{cw-rm}" y="18" fill="#2ecc71" font-size="9" text-anchor="end">+$ / +PIP</text>'
        for i,g in enumerate(groups):
            yb = 32+i*gap
            # Label
            svg += f'<text x="4" y="{yb+6}" fill="#ccc" font-size="9">{g["label"]}</text>'
            # Dollar bar (thick, 16px)
            dpw = abs(g['total_pnl'])/max(max_pnl,1)*(pw/2); dcol = '#2ecc71' if g['total_pnl']>=0 else '#e74c3c'
            dbx = zx if g['total_pnl']>=0 else zx-dpw
            svg += f'<rect x="{dbx:.1f}" y="{yb-4}" width="{max(dpw,1):.1f}" height="16" fill="{dcol}" rx="2" opacity="0.85"/>'
            # Dollar value
            dtx = dbx+dpw+3 if g['total_pnl']>=0 else dbx-3
            anch = "start" if g['total_pnl']>=0 else "end"
            svg += f'<text x="{dtx:.1f}" y="{yb+8}" fill="{dcol}" font-size="8" font-weight="bold" text-anchor="{anch}">${g["total_pnl"]:+,.0f}</text>'
            # PIP bar (thin, 8px)
            ppv = g.get('total_pips',0); ppw = abs(ppv)/max(max_pip,1)*(pw/2); pcol = '#5dade2' if ppv>=0 else '#e67e22'
            pbx = zx if ppv>=0 else zx-ppw
            svg += f'<rect x="{pbx:.1f}" y="{yb+14}" width="{max(ppw,1):.1f}" height="8" fill="{pcol}" rx="2" opacity="0.8"/>'
            # PIP value
            ptx = pbx+ppw+3 if ppv>=0 else pbx-3
            svg += f'<text x="{ptx:.1f}" y="{yb+22}" fill="{pcol}" font-size="7" text-anchor="{anch}">{ppv:+.1f} pip</text>'
        # Legend
        ly = svg_h-10
        svg += f'<rect x="{lm}" y="{ly-8}" width="10" height="8" fill="#2ecc71" rx="1"/><text x="{lm+14}" y="{ly}" fill="#aaa" font-size="8">盈利$</text>'
        svg += f'<rect x="{lm+55}" y="{ly-8}" width="10" height="8" fill="#e74c3c" rx="1"/><text x="{lm+69}" y="{ly}" fill="#aaa" font-size="8">虧損$</text>'
        svg += f'<rect x="{lm+120}" y="{ly-8}" width="10" height="4" fill="#5dade2" rx="1"/><text x="{lm+134}" y="{ly}" fill="#aaa" font-size="8">盈利PIP</text>'
        svg += f'<rect x="{lm+195}" y="{ly-8}" width="10" height="4" fill="#e67e22" rx="1"/><text x="{lm+209}" y="{ly}" fill="#aaa" font-size="8">虧損PIP</text>'
        svg += '</svg>'
        return svg

    merged_svg = build_merged_bar_svg(bar_groups, max_abs_pnl, max_abs_total_pip)

    def build_layer_scatter(trade_details, title=""):
        """Per-layer scatter SVG: X=MFE, Y=-MAE"""
        if not trade_details:
            return '<p style="color:#888;font-size:10px">無交易數據</p>'
        sw, sh = 340, 240; pad = {'top':20,'right':15,'bottom':30,'left':35}
        pw_ = sw-pad['left']-pad['right']; ph = sh-pad['top']-pad['bottom']
        mx_mfe = max((abs(d['mfe']) for d in trade_details), default=1) or 1; mx_mfe *= 1.1
        mx_mae = max((abs(d['mae']) for d in trade_details), default=1) or 1; mx_mae *= 1.1
        svg = f'<svg viewBox="0 0 {sw} {sh}" style="width:100%;height:auto;font-family:sans-serif" xmlns="http://www.w3.org/2000/svg">'
        svg += f'<rect width="{sw}" height="{sh}" fill="#0a0a18" rx="4"/>'
        for i in range(5):
            f_ = i/4; gx = pad['left']+pw_*f_; gy = pad['top']+ph*f_
            svg += f'<line x1="{gx:.1f}" y1="{pad["top"]}" x2="{gx:.1f}" y2="{pad["top"]+ph}" stroke="#1a1a2a" stroke-width="0.5"/>'
            svg += f'<line x1="{pad["left"]}" y1="{gy:.1f}" x2="{pad["left"]+pw_}" y2="{gy:.1f}" stroke="#1a1a2a" stroke-width="0.5"/>'
            svg += f'<text x="{gx:.1f}" y="{sh-8}" fill="#555" font-size="7" text-anchor="middle">{mx_mfe*f_:.0f}</text>'
            svg += f'<text x="{pad["left"]-4}" y="{gy+3:.1f}" fill="#555" font-size="7" text-anchor="end">{mx_mae*(1-f_):.0f}</text>'
        svg += f'<text x="{pad["left"]+pw_//2}" y="{sh-1}" fill="#777" font-size="8" text-anchor="middle">MFE →</text>'
        svg += f'<text x="8" y="{pad["top"]+ph//2}" fill="#777" font-size="8" text-anchor="middle" transform="rotate(-90,8,{pad["top"]+ph//2})">-MAE →</text>'
        svg += '<style>.dot{opacity:0.85;cursor:pointer} .dot:hover{opacity:1;r:5} .dot .tip{display:none} .dot:hover .tip{display:block}</style>'
        for idx,d in enumerate(trade_details):
            mfe = abs(d['mfe']); mae = abs(d['mae']); col = '#2ecc71' if d['is_win'] else '#e74c3c'
            cx = pad['left']+(mfe/mx_mfe)*pw_; cy = pad['top']+(1-mae/mx_mae)*ph
            cx = max(pad['left'], min(pad['left']+pw_, cx)); cy = max(pad['top'], min(pad['top']+ph, cy))
            svg += f'<g class="dot"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="{col}"/>'
            tx = cx+6; ty = cy-8
            if tx+90 > sw: tx = cx-96
            if ty < 10: ty = cy+10
            hh = d.get('holding_hours',0)
            tt = f"#{idx+1} MFE:{d['mfe']:.1f} MAE:{d['mae']:.1f} ${d['net_profit']:.2f} L{d['lots']} Hold:{hh:.1f}h"
            svg += f'<g class="tip"><rect x="{tx:.1f}" y="{ty-8:.1f}" width="{len(tt)*5.2+8:.0f}" height="14" fill="#1a1a3e" stroke="#4a3f8a" rx="3"/>'
            svg += f'<text x="{tx+4:.1f}" y="{ty+2:.1f}" fill="#eee" font-size="7">{tt}</text></g></g>\n'
        svg += '</svg>'
        return svg

    def build_tpsl_bar(layers_data):
        """TP/SL bar chart for layers in a CCY×Direction group"""
        if not layers_data: return ''
        items = [(ls, compute_rating(ls)) for ls in layers_data]
        n = len(items); sw = 700; bh = 14; gap = 4; lm = 100; rm = 20; tp_ = 30; bp_ = 30; pw_ = sw-lm-rm
        sh = tp_ + n*(bh*2+gap+12) + bp_
        mx = max(max(ls['avg_mae'], ls['max_mae'], ls['avg_mfe']) for ls,_ in items) or 1
        svg = f'<svg viewBox="0 0 {sw} {sh}" style="width:100%;height:auto;font-family:sans-serif" xmlns="http://www.w3.org/2000/svg">'
        svg += f'<rect width="{sw}" height="{sh}" fill="#0a0a18" rx="6"/>'
        for frac in [0.25,0.5,0.75,1.0]:
            gx=lm+pw_*frac; svg += f'<line x1="{gx:.1f}" y1="{tp_-10}" x2="{gx:.1f}" y2="{sh-bp_+10}" stroke="#1a1a2a" stroke-width="0.5"/>'
            svg += f'<text x="{gx:.1f}" y="{tp_-14}" fill="#555" font-size="7" text-anchor="middle">{mx*frac:.0f}</text>'
        for i,(ls,rat) in enumerate(items):
            yb = tp_ + i*(bh*2+gap+12)
            svg += f'<text x="4" y="{yb+6}" fill="#ccc" font-size="8">{ls["layer_label"]}</text>'
            svg += f'<text x="4" y="{yb+16}" fill="{rc(rat)}" font-size="8" font-weight="bold">{rat}</text>'
            sw_ = (ls['avg_mae']/mx)*pw_
            svg += f'<rect x="{lm:.1f}" y="{yb:.1f}" width="{max(sw_,1):.1f}" height="{bh}" fill="#f39c12" rx="2" opacity="0.85"/>'
            svg += f'<text x="{lm+sw_+3:.1f}" y="{yb+11}" fill="#ccc" font-size="7">SL {ls["avg_mae"]}</text>'
            hw = (ls['max_mae']/mx)*pw_
            svg += f'<rect x="{lm:.1f}" y="{yb+bh+1:.1f}" width="{max(hw,1):.1f}" height="{bh}" fill="#e74c3c" rx="2" opacity="0.85"/>'
            svg += f'<text x="{lm+hw+3:.1f}" y="{yb+bh+12}" fill="#ccc" font-size="7">Hard {ls["max_mae"]}</text>'
        ly = sh-10
        svg += f'<rect x="{lm}" y="{ly-8}" width="10" height="8" fill="#f39c12" rx="1"/><text x="{lm+14}" y="{ly}" fill="#aaa" font-size="8">Soft SL</text>'
        svg += f'<rect x="{lm+70}" y="{ly-8}" width="10" height="8" fill="#e74c3c" rx="1"/><text x="{lm+84}" y="{ly}" fill="#aaa" font-size="8">Hard SL</text>'
        svg += '</svg>'
        return svg

    def layer_danger(ls):
        d = 0.0
        if ls['total_pnl'] < 0: d += abs(ls['total_pnl']) / 500
        if ls['wr'] < 50: d += 2
        if ls['ev'] < 0: d += min(abs(ls['ev']) / 10, 5)
        if ls['odds_pips'] < 1.0: d += 2
        if ls['count'] < 3: d += 1
        if ls['layer_idx'] > 5: d += 1
        return round(d, 1)

    # merged_svg is built by build_merged_bar_svg above

    # ── Build navigation links ──
    nav_links = ' '.join(
        f'<a href="#ccy-{sym}-{dr}">{sym} {dr.upper()}</a>'
        for (sym, dr), _ in sorted_ccy
    )

    # ── Build CCY×Direction sections ──
    ccy_sections = []

    for idx_ccy, ((symbol, direction), layers) in enumerate(sorted_ccy):
        gs = next((s for s in ccy_summary if s['symbol']==symbol and s['direction']==direction), None)
        if not gs: continue

        sl = sorted(layers.values(), key=lambda x: x['lots'])  # shallow → deep
        best_ev = max((l['ev'] for l in sl), default=0)
        total_pnl_grp = gs['total_pnl']
        is_open = ' open' if idx_ccy == 0 else ''

        sec = f'''
    <details id="ccy-{symbol}-{direction}" class="ccy-section"{is_open}>
      <summary class="ccy-summary">
        <span style="font-size:16px">📌</span> <b>{symbol} {direction.upper()}</b>
        &nbsp;-&nbsp; <span class="{'positive' if total_pnl_grp>0 else 'negative'}">${pp(total_pnl_grp)}{total_pnl_grp:,.2f}</span>
        &nbsp;·&nbsp; {gs['trades']} trades
        &nbsp;·&nbsp; WR {gs['wr']}%
        &nbsp;·&nbsp; {len(sl)} layers
      </summary>
'''
        # ── Part 1: 組合概覽 ──
        sec += '''
      <div class="section">
        <div class="section-header">
          Part 1 · 組合概覽
          <span class="badge">''' + str(len(sl)) + ''' 層</span>
          <i class="info-icon" tabindex="0">i<span class="info-tip">
            <b>組合概覽說明</b><br>
            顯示此 CCY×Direction 下每一層嘅完整統計。<br>
            <span style="color:#2ecc71">綠色行</span> = A 級以上 &nbsp;|&nbsp;
            <span style="color:#e74c3c">紅色行</span> = D 級以下<br><br>
            <b>Rating</b>: S+(金) S(紫) A(綠) B(藍) C(橙) D(灰) E(紅)<br>
            <b>EV$</b>: 預期盈虧 | <b>Odds</b>: 盈虧比 | <b>MFE/MAE</b>: 最大有利/不利波幅
          </span></i>
        </div>
        <div class="section-body">
          <div class="table-wrap">
            <table>
              <thead><tr>
                <th>Layer</th><th>Rating</th><th>Score</th><th>Trades</th><th>W:L</th>
                <th>WR%</th><th>EV$</th><th>WinPip</th><th>LossPip</th>
                <th>Odds$</th><th>OddsPip</th><th>MFE</th><th>MAE</th><th>MaxMAE</th>
                <th>Hold(h)</th><th>Total$</th>
              </tr></thead>
              <tbody>
'''
        for ls in sl:
            rating = compute_rating(ls)
            score = compute_score(ls)
            row_cls = ' class="row-a"' if rating in ('S+','S','A') else ' class="row-d"' if rating in ('D','E') else ''
            ev_cls = 'positive' if ls['ev']>0 else 'negative'
            pnl_cls = 'positive' if ls['total_pnl']>0 else 'negative' if ls['total_pnl']<0 else 'neutral'
            sec += f'''<tr{row_cls}>
                <td><b>{ls["layer_label"]}</b></td>
                <td><span class="rating-badge" style="background:{rb(rating)};color:{rc(rating)}">{rating}</span></td>
                <td>{score}</td>
                <td>{ls["count"]}</td>
                <td>{ls["win_count"]}:{ls["loss_count"]}</td>
                <td>{ls["wr"]}%</td>
                <td class="{ev_cls}">{pp(ls["ev"])}{ls["ev"]}</td>
                <td>{ls["avg_win_pips"]}</td>
                <td>{ls["avg_loss_pips"]}</td>
                <td>{ls["odds_dollar"]}</td>
                <td>{ls["odds_pips"]}</td>
                <td>{ls["avg_mfe"]}</td>
                <td>{ls["avg_mae"]}</td>
                <td><b>{ls["max_mae"]}</b></td>
                <td>{ls["avg_hold"]}</td>
                <td class="{pnl_cls}"><b>${pp(ls["total_pnl"])}{ls["total_pnl"]:,.2f}</b></td>
              </tr>
'''
        sec += '''              </tbody>
            </table>
          </div>
        </div>
      </div>
'''
        # ── Part 2: MFE/MAE 散點圖 (per layer) ──
        sec += '''
      <div class="section">
        <div class="section-header">
          Part 2 · MFE/MAE 散點分析
          <span class="badge">每層一圖 · 綠=Win · 紅=Loss · Hover 查詳情</span>
          <i class="info-icon" tabindex="0">i<span class="info-tip">
            <b>MFE/MAE 散點分析</b><br>
            每層獨立嘅散點圖:X=MFE(最大有利波幅),Y=-MAE(最大不利波幅)。<br>
            綠色 = 盈利交易 | 紅色 = 虧損交易<br>
            Hover 可查看每筆交易詳情。
          </span></i>
        </div>
        <div class="section-body">
          <div class="scatter-grid">
'''
        for ls in sl:
            rating = compute_rating(ls)
            sec += f'''            <div class="scatter-card">
              <div class="title"><b>{ls["layer_label"]}</b> <span class="rating-badge" style="background:{rb(rating)};color:{rc(rating)}">{rating}</span> (n={ls["count"]}) &nbsp; WR:{ls["wr"]}% EV:{pp(ls["ev"])}{ls["ev"]}$</div>
              {build_layer_scatter(ls["trade_details"], ls["layer_label"])}
            </div>
'''
        sec += '''          </div>
        </div>
      </div>
'''
        # ── Part 3: TP/SL (all layers, no multiplier) ──
        sec += '''
      <div class="section">
        <div class="section-header">
          Part 3 · TP/SL 建議(原始值,不乘倍數)
          <i class="info-icon" tabindex="0">i<span class="info-tip">
            <b>TP/SL 說明</b><br>
            <b>TP</b> = 該層平均 MFE(不乘倍數)<br>
            <b>Soft SL</b> = 該層平均 MAE(不乘倍數)<br>
            <b>Hard SL</b> = 該層歷史最大 MAE(不乘倍數)<br>
            <b>R:R</b> = TP / Soft SL(≥1.5x 可接受,≥3.0x 優秀)
          </span></i>
        </div>
        <div class="section-body">
          <div style="font-size:10px;color:#888;margin-bottom:8px;">
            TP = Avg MFE &nbsp;|&nbsp; Soft SL = Avg MAE &nbsp;|&nbsp; Hard SL = Max MAE &nbsp;|&nbsp; 全部原始值,不乘倍數
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr>
                <th>Layer</th><th>Rating</th><th>n</th>
                <th>TP (AvgMFE)</th><th>Soft SL (AvgMAE)</th><th>Hard SL (MaxMAE)</th><th>R:R</th>
              </tr></thead>
              <tbody>
'''
        for ls in sl:
            rating = compute_rating(ls)
            tp = ls['avg_mfe']
            soft_sl = ls['avg_mae']   # 不乘倍數
            hard_sl = ls['max_mae']   # 不乘倍數,用層級自身 Max MAE
            rr = tp / soft_sl if soft_sl > 0 else 0
            rr_cls = 'positive' if rr >= 1.5 else 'negative'
            sec += f'''              <tr>
                <td><b>{ls["layer_label"]}</b></td>
                <td><span class="rating-badge" style="background:{rb(rating)};color:{rc(rating)}">{rating}</span></td>
                <td>{ls["count"]}</td>
                <td class="positive">{tp}</td>
                <td style="color:#f39c12">{soft_sl}</td>
                <td class="negative">{hard_sl}</td>
                <td class="{rr_cls}"><b>{rr:.2f}x</b></td>
              </tr>
'''
        sec += '''              </tbody>
            </table>
          </div>
          <div class="chart-container">
            <div class="chart-title">📊 Soft SL vs Hard SL 條形圖</div>
''' + build_tpsl_bar(sl) + '''
          </div>
        </div>
      </div>
'''
        # ── Part 4: 排行榜 (A+ only in this group) ──
        a_plus = [(ls, compute_rating(ls)) for ls in sl if rating_order.get(compute_rating(ls), 0) >= 4]
        a_plus.sort(key=lambda x: (-rating_order.get(x[1], 0), -x[0]['ev']))
        sec += f'''
      <div class="section">
        <div class="section-header">
          Part 4 · 排行榜(A 級以上)
          <span class="badge">{len(a_plus)} 層</span>
          <i class="info-icon" tabindex="0">i<span class="info-tip">
            <b>排行榜說明</b><br>
            此 CCY×Direction 內 A 級以上嘅層級,按評級同 EV 降序排列。<br>
            評級基於 WR(25%) + EV(30%) + Odds(20%) + Count(15%) + Hold(10%)。
          </span></i>
        </div>
        <div class="section-body">
'''
        if a_plus:
            sec += '''          <div class="table-wrap">
            <table>
              <thead><tr>
                <th>#</th><th>Rating</th><th>Layer</th><th>n</th>
                <th>WR%</th><th>EV$</th><th>Odds$</th><th>OddsPip</th>
                <th>MFE</th><th>MAE</th><th>Total$</th><th>Hold(h)</th>
              </tr></thead>
              <tbody>
'''
            for rank, (ls, rat) in enumerate(a_plus, 1):
                pnl_cls = 'positive' if ls['total_pnl']>0 else 'negative'
                ev_cls = 'positive' if ls['ev']>0 else 'negative'
                sec += f'''              <tr>
                <td>{rank}</td>
                <td><span class="rating-badge" style="background:{rb(rat)};color:{rc(rat)}">{rat}</span></td>
                <td><b>{ls["layer_label"]}</b></td>
                <td>{ls["count"]}</td>
                <td>{ls["wr"]}%</td>
                <td class="{ev_cls}"><b>{pp(ls["ev"])}{ls["ev"]}</b></td>
                <td>{ls["odds_dollar"]}</td>
                <td>{ls["odds_pips"]}</td>
                <td>{ls["avg_mfe"]}</td>
                <td>{ls["avg_mae"]}</td>
                <td class="{pnl_cls}">{pp(ls["total_pnl"])}{ls["total_pnl"]:,.2f}</td>
                <td>{ls["avg_hold"]:.0f}</td>
              </tr>
'''
            sec += '''              </tbody>
            </table>
          </div>
'''
        else:
            sec += '          <div style="text-align:center;padding:15px;color:#888;">此組合暫無 A 級以上層級</div>\n'
        sec += '''        </div>
      </div>
'''
        # ── Part 5: 黑名單 (dangerous layers in this group) ──
        dangerous = [(ls, layer_danger(ls)) for ls in sl if layer_danger(ls) >= 1]
        dangerous.sort(key=lambda x: -x[1])
        sec += f'''
      <div class="section">
        <div class="section-header">
          Part 5 · 黑名單(高危層級)
          <span class="badge">{len(dangerous)} 層</span>
          <i class="info-icon" tabindex="0">i<span class="info-tip">
            <b>黑名單說明</b><br>
            此 CCY×Direction 內 Danger Score ≥ 1 嘅層級。<br>
            危險因素:負 P&L、低 WR、負 EV、低 Odds、樣本少、深層級。<br>
            ⚠️ WARNING: 1-3 &nbsp;|&nbsp; 💀 DEADLY: &gt;3
          </span></i>
        </div>
        <div class="section-body">
'''
        if dangerous:
            sec += '''          <div class="table-wrap">
            <table>
              <thead><tr>
                <th>危險度</th><th>Danger</th><th>Layer</th><th>Rating</th>
                <th>n</th><th>WR%</th><th>EV$</th><th>OddsPip</th><th>Total$</th>
              </tr></thead>
              <tbody>
'''
            for ls, dg in dangerous:
                rat = compute_rating(ls)
                level = '💀 DEADLY' if dg > 3 else '⚠️ WARNING'
                pnl_cls = 'negative' if ls['total_pnl'] < 0 else 'positive'
                ev_cls = 'negative' if ls['ev'] < 0 else 'positive'
                sec += f'''              <tr>
                <td>{level}</td>
                <td><b>{dg}</b></td>
                <td><b>{ls["layer_label"]}</b></td>
                <td><span class="rating-badge" style="background:{rb(rat)};color:{rc(rat)}">{rat}</span></td>
                <td>{ls["count"]}</td>
                <td>{ls["wr"]}%</td>
                <td class="{ev_cls}">{pp(ls["ev"])}{ls["ev"]}</td>
                <td>{ls["odds_pips"]}</td>
                <td class="{pnl_cls}">${pp(ls["total_pnl"])}{ls["total_pnl"]:,.2f}</td>
              </tr>
'''
            sec += '''              </tbody>
            </table>
          </div>
'''
        else:
            sec += '          <div style="text-align:center;padding:15px;color:#2ecc71;">✅ 此組合無高危層級</div>\n'
        sec += '''        </div>
      </div>
'''
        # ── Part 6: 恢復力 (per layer) ──
        sec += '''
      <div class="section">
        <div class="section-header">
          Part 6 · 恢復力分析
          <span class="badge">每層恢復天數</span>
          <i class="info-icon" tabindex="0">i<span class="info-tip">
            <b>恢復力說明</b><br>
            如果該層被止損,需要幾多次最佳 EV 層交易先可以追回損失。<br>
            🟢 100%勝率或≤4次 &nbsp;|&nbsp; 🟡 5-20次 &nbsp;|&nbsp; 🔴 &gt;20次或EV≤0
          </span></i>
        </div>
        <div class="section-body">
          <div class="table-wrap">
            <table>
              <thead><tr>
                <th>狀態</th><th>Layer</th><th>Rating</th><th>損失$</th>
                <th>Best EV$</th><th>恢復次數</th><th>恢復天數</th><th>說明</th>
              </tr></thead>
              <tbody>
'''
        for ls in sl:
            rat = compute_rating(ls)
            avg_loss = ls['avg_loss'] if ls['loss_count'] > 0 else ls['lots'] * 100
            if best_ev > 0:
                rec_trades = math.ceil(avg_loss / best_ev)
            else:
                rec_trades = 999

            # Frequency estimate for this group
            total_grp_trades = sum(l['count'] for l in sl)
            freq_month = total_grp_trades / 3
            if freq_month > 0:
                rec_days = round(rec_trades / freq_month * 30)
            else:
                rec_days = 999

            if ls['wr'] == 100:
                status = '🟢'; status_text = '100% WR'
            elif rec_trades <= 4:
                status = '🟢'; status_text = f'安全 ({rec_trades}次)'
            elif rec_trades <= 20:
                status = '🟡'; status_text = f'需時 ({rec_trades}次)'
            else:
                status = '🔴'; status_text = '無法恢復'

            sec += f'''              <tr>
                <td>{status}</td>
                <td><b>{ls["layer_label"]}</b></td>
                <td><span class="rating-badge" style="background:{rb(rat)};color:{rc(rat)}">{rat}</span></td>
                <td class="negative">${avg_loss:,.2f}</td>
                <td class="{'positive' if best_ev>0 else 'negative'}">{pp(best_ev)}{best_ev}</td>
                <td><b>{rec_trades if rec_trades<999 else '∞'}</b></td>
                <td>{rec_days if rec_days<999 else '∞'}天</td>
                <td>{status_text}</td>
              </tr>
'''
        sec += '''              </tbody>
            </table>
          </div>
        </div>
      </div>
'''

        # ── Part 7: CCY 層級 TP/SL 盈利分析 ──
        if ccy_profitability:
            ccy_key = f"{symbol}_{direction}"
            cp = ccy_profitability.get(ccy_key)
            if cp:
                sec += f'''
      <div class="section">
        <div class="section-header">
          Part 7 · 層級 TP/SL 盈利分析
          <span class="badge">{cp['profitable_layers']}/{cp['total_layers']} 層盈利</span>
          <i class="info-icon" tabindex="0">i<span class="info-tip">
            <b>層級 TP/SL 盈利分析說明</b><br>
            基於 CCY 總覽統計,分析每層 TP/SL 是否有盈利邊緣。<br><br>
            <b>TP/SL</b>: 該層實際 MFE(最大有利波幅)= TP 能力,MAE(最大不利波幅)= SL 風險<br>
            <b>Edge</b>: WR × TP - (1-WR) × SL,正值 = 有盈利邊緣<br>
            <b>vs CCY</b>: 與 CCY 平均嘅偏差百分比<br>
            <span style="color:#2ecc71">綠色行</span> = 盈利層 &nbsp;|&nbsp;
            <span style="color:#e74c3c">紅色行</span> = 虧損層
          </span></i>
        </div>
        <div class="section-body">
          <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:6px;margin-bottom:8px">
            <div style="background:#1a1a2e;padding:6px 8px;border-radius:4px"><div style="color:#888;font-size:9px">CCY WR</div><div style="color:#FFD700;font-size:14px;font-weight:bold">{cp['ccy_wr']}%</div></div>
            <div style="background:#1a1a2e;padding:6px 8px;border-radius:4px"><div style="color:#888;font-size:9px">CCY EV$</div><div style="color:{'#2ecc71' if cp['ccy_ev']>0 else '#e74c3c'};font-size:14px;font-weight:bold">{pp(cp['ccy_ev'])}{cp['ccy_ev']}</div></div>
            <div style="background:#1a1a2e;padding:6px 8px;border-radius:4px"><div style="color:#888;font-size:9px">CCY TP (Avg MFE)</div><div style="color:#2ecc71;font-size:14px;font-weight:bold">{cp['ccy_avg_mfe']}</div></div>
            <div style="background:#1a1a2e;padding:6px 8px;border-radius:4px"><div style="color:#888;font-size:9px">CCY SL (Avg MAE)</div><div style="color:#e74c3c;font-size:14px;font-weight:bold">{cp['ccy_avg_mae']}</div></div>
            <div style="background:#1a1a2e;padding:6px 8px;border-radius:4px"><div style="color:#888;font-size:9px">盈利層數</div><div style="color:#2ecc71;font-size:14px;font-weight:bold">{cp['profitable_layers']}/{cp['total_layers']}</div></div>
            <div style="background:#1a1a2e;padding:6px 8px;border-radius:4px"><div style="color:#888;font-size:9px">CCY Total$</div><div style="color:{'#2ecc71' if cp['ccy_total_pnl']>0 else '#e74c3c'};font-size:14px;font-weight:bold">{pp(cp['ccy_total_pnl'])}{cp['ccy_total_pnl']:,.2f}</div></div>
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr>
                <th>Layer</th><th>Rating</th><th>狀態</th><th>Trades</th><th>WR%</th>
                <th>TP</th><th>SL</th><th>Hard SL</th><th>TP/SL比</th>
                <th>Edge</th><th>vs CCY TP</th><th>vs CCY SL</th>
                <th>EV$</th><th>Total$</th><th>盈利%</th>
              </tr></thead>
              <tbody>
'''
                for lr in cp['layers']:
                    row_cls = ' class="row-a"' if lr['is_profitable'] else ' class="row-d"'
                    status = '✅' if lr['is_profitable'] else '❌'
                    ev_cls = 'positive' if lr['ev'] > 0 else 'negative'
                    pnl_cls = 'positive' if lr['total_pnl'] > 0 else 'negative'
                    edge_cls = 'positive' if lr['edge'] > 0 else 'negative'
                    tp_vs = f"{pp(lr['tp_vs_ccy'])}{lr['tp_vs_ccy']}%"
                    sl_vs = f"{pp(lr['sl_vs_ccy'])}{lr['sl_vs_ccy']}%"
                    sec += f'''              <tr{row_cls}>
                <td><b>{lr['layer_label']}</b></td>
                <td><span class="rating-badge" style="background:{rb(lr['rating'])};color:{rc(lr['rating'])}">{lr['rating']}</span></td>
                <td>{status}</td>
                <td>{lr['count']}</td>
                <td>{lr['wr']}%</td>
                <td style="color:#2ecc71">{lr['tp_pips']}</td>
                <td style="color:#f39c12">{lr['sl_pips']}</td>
                <td style="color:#e74c3c">{lr['hard_sl']}</td>
                <td>{lr['tp_sl_ratio']}</td>
                <td class="{edge_cls}">{pp(lr['edge'])}{lr['edge']}</td>
                <td style="color:{'#2ecc71' if lr['tp_vs_ccy']>0 else '#e74c3c'}">{tp_vs}</td>
                <td style="color:{'#2ecc71' if lr['sl_vs_ccy']<0 else '#e74c3c'}">{sl_vs}</td>
                <td class="{ev_cls}">{pp(lr['ev'])}{lr['ev']}</td>
                <td class="{pnl_cls}"><b>{pp(lr['total_pnl'])}{lr['total_pnl']:,.2f}</b></td>
                <td>{lr['profit_margin']}%</td>
              </tr>
'''
                sec += '''              </tbody>
            </table>
          </div>
        </div>
      </div>
'''

        sec += '''    </details>
'''
        ccy_sections.append(sec)

    # ── Assemble full HTML ──
    all_sections = '\n'.join(ccy_sections)

    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>馬丁剖析法 V3 - Signal #{signal_id}</title>
    <style>
        :root {{--bg:#0a0a1a;--surface:#0f0f23;--border:#2a2a4a;--text:#e0e0e0;--muted:#888;--accent:#FFD700}}
        [data-theme="light"] {{--bg:#f5f5f5;--surface:#fff;--border:#ddd;--text:#222;--muted:#666;--accent:#d4a017}}
        * {{ margin:0; padding:0; box-sizing:border-box; }}
        body {{
            font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;
            font-size:12px; line-height:1.5; color:var(--text); background:var(--bg); padding:15px;
        }}
        .theme-toggle {{
            position:fixed;top:12px;right:16px;z-index:1001;
            background:var(--surface);color:var(--text);border:1px solid var(--border);
            border-radius:50%;width:36px;height:36px;font-size:16px;cursor:pointer;
            display:flex;align-items:center;justify-content:center;transition:background .2s;
        }}
        .theme-toggle:hover {{ background:var(--border); }}
        .container {{ max-width:1400px; margin:0 auto; }}
        .header {{
            background:linear-gradient(135deg,#1a1a3e 0%,#2d1b69 50%,#1a1a3e 100%);
            border:1px solid #4a3f8a; border-radius:12px; padding:20px; margin-bottom:20px;
        }}
        .header h1 {{ font-size:22px; color:#FFD700; margin-bottom:4px; }}
        .header .subtitle {{ font-size:12px; color:#999; }}
        .kpi-row {{
            display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr));
            gap:12px; margin-top:15px;
        }}
        .kpi-card {{
            background:rgba(255,255,255,0.05); border:1px solid rgba(255,255,255,0.1);
            border-radius:8px; padding:10px; text-align:center;
        }}
        .kpi-card .label {{ font-size:10px; color:#888; text-transform:uppercase; letter-spacing:0.5px; }}
        .kpi-card .value {{ font-size:18px; font-weight:bold; color:#fff; margin-top:4px; }}
        .kpi-card .value.green {{ color:#2ecc71; }}
        .kpi-card .value.red {{ color:#e74c3c; }}
        .kpi-card .value.gold {{ color:#FFD700; }}
        .section {{
            background:var(--surface); border:1px solid var(--border);
            border-radius:10px; margin-bottom:12px; overflow:hidden;
        }}
        .section-header {{
            background:linear-gradient(90deg,#1a1a3e,#2d1b69);
            padding:10px 14px; font-size:13px; font-weight:bold; color:#fff;
            border-bottom:1px solid #3a3a6a; display:flex; align-items:center; gap:8px;
        }}
        .section-header .badge {{
            display:inline-block; background:#FFD700; color:#000;
            font-size:10px; padding:2px 8px; border-radius:10px; font-weight:normal;
        }}
        .section-body {{ padding:12px; }}
        .info-icon {{
            position:relative; display:inline-flex; align-items:center; justify-content:center;
            width:18px; height:18px; border-radius:50%; background:rgba(255,255,255,0.15);
            color:#ccc; font-size:11px; cursor:help; font-style:normal; flex-shrink:0;
        }}
        .info-icon .info-tip {{
            display:none; position:absolute; top:100%; left:50%; transform:translateX(-50%);
            background:#1a1a3e; border:1px solid #4a3f8a; border-radius:6px;
            padding:8px 10px; font-size:10px; font-weight:normal; color:#ccc;
            white-space:normal; width:280px; z-index:100; line-height:1.6;
            box-shadow:0 4px 12px rgba(0,0,0,.5); pointer-events:none;
        }}
        .info-icon:hover .info-tip, .info-icon:focus .info-tip {{ display:block; }}
        .table-wrap {{ overflow-x:auto; -webkit-overflow-scrolling:touch; }}
        table {{ width:100%; border-collapse:collapse; font-size:11px; }}
        table th {{
            background:#1a1a3e; color:#bbb; padding:6px 8px; text-align:left;
            font-size:10px; text-transform:uppercase; letter-spacing:0.5px;
            border-bottom:1px solid #3a3a6a; white-space:nowrap; position:sticky; top:0;
        }}
        table td {{ padding:5px 8px; border-bottom:1px solid #1a1a2a; white-space:nowrap; }}
        table tr:hover {{ background:rgba(255,255,255,0.03); }}
        .positive {{ color:#2ecc71; }}
        .negative {{ color:#e74c3c; }}
        .neutral {{ color:#888; }}
        .rating-badge {{
            display:inline-block; padding:1px 6px; border-radius:3px;
            font-weight:700; font-size:11px; text-align:center; min-width:28px;
        }}
        .scatter-grid {{
            display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:12px;
        }}
        .scatter-card {{
            background:#0a0a18; border:1px solid #2a2a4a; border-radius:8px; padding:8px;
        }}
        .scatter-card .title {{ font-size:11px; color:#bbb; margin-bottom:4px; }}
        .chart-container {{
            margin-top:12px; padding:12px; background:#0a0a18;
            border:1px solid #2a2a4a; border-radius:8px;
        }}
        .chart-title {{ font-size:11px; color:#bbb; margin-bottom:8px; }}
        .section-nav {{
            display:flex; gap:2px; flex-wrap:wrap; background:#0a0a18;
            border-bottom:2px solid #2a2a4a; padding:0 12px;
            position:sticky; top:0; z-index:50;
        }}
        .section-nav a {{
            padding:8px 14px; font-size:11px; color:#888; text-decoration:none;
            border-bottom:2px solid transparent; transition:all 0.2s;
        }}
        .section-nav a:hover {{ color:#FFD700; border-bottom-color:#FFD700; }}
        /* CCY section styles */
        .ccy-section {{
            background:var(--surface); border:1px solid var(--border);
            border-radius:10px; margin-bottom:16px; padding:0;
        }}
        .ccy-summary {{
            display:block; padding:14px 18px; font-size:14px; cursor:pointer;
            background:linear-gradient(90deg,#1a1a3e,#2d1b69);
            border-radius:10px; color:#fff; list-style:none;
        }}
        .ccy-summary::-webkit-details-marker {{ display:none; }}
        .ccy-summary::before {{
            content:'▶'; display:inline-block; font-size:12px; color:#FFD700;
            margin-right:10px; transition:transform 0.15s;
        }}
        .ccy-section[open] .ccy-summary::before {{ transform:rotate(90deg); }}
        .ccy-section > .section {{ margin:8px 12px 12px 12px; }}
        .row-a {{ background:rgba(46,204,113,0.08); }}
        .row-d {{ background:rgba(231,76,60,0.08); }}
        .footer {{ text-align:center; padding:15px; color:#555; font-size:10px; }}
        /* Light theme */
        [data-theme="light"] .header {{
            background:linear-gradient(135deg,#e8eaf6 0%,#c5cae9 50%,#e8eaf6 100%);
            border-color:#9fa8da;
        }}
        [data-theme="light"] .header h1 {{ color:#1a237e; }}
        [data-theme="light"] .section-header {{
            background:linear-gradient(90deg,#e8eaf6,#c5cae9);
            color:#1a237e; border-bottom-color:#9fa8da;
        }}
        [data-theme="light"] table th {{ background:#e8eaf6; color:#555; border-bottom-color:#c5cae9; }}
        [data-theme="light"] table td {{ border-bottom-color:#e0e0e0; }}
        [data-theme="light"] .scatter-card,
        [data-theme="light"] .chart-container {{ background:#fff; border-color:#ddd; }}
        [data-theme="light"] .info-icon .info-tip {{ background:#fff; border-color:#ccc; color:#333; }}
        [data-theme="light"] .section-nav {{ background:#e0e0e0; border-bottom-color:#ccc; }}
        [data-theme="light"] .ccy-section {{ background:#fff; border-color:#ddd; }}
        [data-theme="light"] .ccy-summary {{
            background:linear-gradient(90deg,#e8eaf6,#c5cae9); color:#1a237e;
        }}
    </style>
    <script>
    function toggleTheme(){{
        var t=document.documentElement.getAttribute('data-theme');
        if(t==='light'){{document.documentElement.removeAttribute('data-theme');localStorage.setItem('theme','dark')}}
        else{{document.documentElement.setAttribute('data-theme','light');localStorage.setItem('theme','light')}}
    }}
    (function(){{
        var s=localStorage.getItem('theme');
        if(s==='light')document.documentElement.setAttribute('data-theme','light');
    }})();
    </script>
<link rel="stylesheet" href="../sidebar.css">
</head>
<body>
<button class="theme-toggle" onclick="toggleTheme()" title="切換亮/暗模式">🌓</button>
<div class="container">

    <!-- ═══ Executive Summary ═══ -->
    <div class="header">
        <h1>🔬 馬丁剖析法 V3 - Signal #{signal_id}</h1>
        <div class="subtitle">
            {num_ccy} 個 CCY×Direction 組合 · {total_layers} 個層級 · 生成時間 {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="label">總交易</div>
                <div class="value">{total_trades}</div>
            </div>
            <div class="kpi-card">
                <div class="label">總盈虧</div>
                <div class="value {'green' if total_pnl>0 else 'red'}">${pp(total_pnl)}{total_pnl:,.2f}</div>
            </div>
            <div class="kpi-card">
                <div class="label">勝率</div>
                <div class="value {'green' if wr>60 else 'red'}">{wr:.1f}%</div>
            </div>
            <div class="kpi-card">
                <div class="label">平均持倉</div>
                <div class="value">{avg_hold:.1f}h</div>
            </div>
            <div class="kpi-card">
                <div class="label">CCY 組合</div>
                <div class="value gold">{num_ccy}</div>
            </div>
            <div class="kpi-card">
                <div class="label">層級總數</div>
                <div class="value gold">{total_layers}</div>
            </div>
        </div>
    </div>

    <!-- Global Bar Chart (merged $ + PIP) -->
    <div class="section">
        <div class="section-header">📊 全局盈虧概覽(金額 + PIP)
            <i class="info-icon" tabindex="0">i<span class="info-tip">
                <b>盈虧概覽說明</b><br>
                每個 CCY×Direction 顯示兩組數據:<br><br>
                <b>金額條(粗)</b>:Total$ 盈虧金額<br>
                綠色 = 盈利 | 紅色 = 虧損<br><br>
                <b>PIP 條(細)</b>:Total PIP 盈虧<br>
                藍色 = 盈利 PIP | 橙色 = 虧損 PIP<br><br>
                每條 bar 旁邊顯示精確數值
            </span></i>
        </div>
        <div class="section-body">
            <div class="chart-container">
                {merged_svg}
            </div>
        </div>
    </div>

    <!-- Navigation -->
    <div class="section-nav">
        {nav_links}
    </div>

    <!-- ═══ CCY×Direction Sections ═══ -->
    {all_sections}

    <div class="footer">
        馬丁剖析法 V3 · 按 CCY×Direction 分組 · 數據說話,紀律至上 · Quant 📊
    </div>
</div>
<script src="../sidebar.js"></script>
</body>
</html>
"""

    return html



# ─── 主程序 ─────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法: python generate_martin_autopsy_v3.py <signal_csv> [--output OUTPUT_PATH]")
        print("範例: python generate_martin_autopsy_v3.py samples/forex-forest-signals-page-14581.csv")
        sys.exit(1)

    csv_path = sys.argv[1]

    # 解析 signal ID
    basename = Path(csv_path).stem
    signal_id = basename.replace('forex-forest-signals-page-', '').replace('signal_', '')

    # 輸出路徑
    output_path = None
    if '--output' in sys.argv:
        idx = sys.argv.index('--output')
        if idx + 1 < len(sys.argv):
            output_path = sys.argv[idx + 1]

    if not output_path:
        output_dir = Path(__file__).parent / 'docs'
        output_dir.mkdir(exist_ok=True)
        output_path = str(output_dir / f'martin_autopsy_v3_{signal_id}.html')

    print(f"📊 馬丁剖析法 V3 - Signal #{signal_id}")
    print(f"📁 載入: {csv_path}")

    # 載入數據
    trades = load_trades(csv_path)
    print(f"✅ 載入 {len(trades)} 筆交易")

    # 為每筆交易推斷層級
    for t in trades:
        t['layer'] = infer_layer(t['lots'])

    # 核心計算
    layer_stats = compute_layer_stats(trades)
    print(f"📊 計算 {len(layer_stats)} 個層級統計")

    # 各 Part
    ccy_summary = build_ccy_direction_summary(layer_stats)
    tp_sl_data = compute_tp_sl(layer_stats)
    blacklist = compute_blacklist(layer_stats)
    recovery = compute_recovery(layer_stats)
    ccy_profitability = compute_ccy_layer_profitability(layer_stats)
    
    print(f"✅ Part 1: {len(ccy_summary)} CCY×Dir 組合")
    print(f"✅ Part 3: {len(tp_sl_data)} A級以上層級")
    print(f"✅ Part 5: {len(blacklist)} 黑名單組合")
    print(f"✅ Part 6: {len(recovery)} 恢復力分析")
    print(f"✅ Part 7: {len(ccy_profitability)} CCY 層級盈利分析")

    # 生成 HTML
    html = generate_html(signal_id, trades, layer_stats, ccy_summary,
                         tp_sl_data, blacklist, recovery, ccy_profitability)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"\n✅ 報告已生成: {output_path}")
    print(f"📏 文件大小: {os.path.getsize(output_path):,} bytes")


if __name__ == '__main__':
    main()
