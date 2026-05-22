#!/usr/bin/env python3
"""
馬丁剖析法 V3 — Martin Autopsy V3

對單一 Signal 的 CSV 交易數據進行完整馬丁剖析分析，生成 HTML 報告。

分析模塊：
  Part 1: CCY × Direction 總覽表
  Part 2: MFE/MAE 散點分析（含圖表）
  Part 3: A 級以上 TP/SL 建議（混合方案）
  Part 4: A 級以上排行榜
  Part 5: 黑名單（Danger Score）
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

# 評分權重（V3 評級系統）
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
    return lots  # 回退：返回原始值


def assign_layer_index(lots_list: List[float]) -> Dict[float, int]:
    """對 Lots 排序，生成 layer_idx (1-based)"""
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
                # 原始交易數據（用於散點圖）
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
    計算層級評級：S+, S, A, B, C, D, E
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
    
    # Hold 評分 (0-5): 越短越好（效率）
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
        hard_sl = ccy_dir_max_mae[(stats['symbol'], stats['direction'])]
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
    """Part 5: 黑名單（Danger Score）"""
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
        
        # 頻率估算（每月）
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


# ─── HTML 生成 ───────────────────────────────────────────────



def generate_html(signal_id: str, trades: List[dict], layer_stats: Dict,
                  ccy_summary: List[dict], tp_sl_data: List[dict],
                  blacklist: List[dict], recovery: List[dict]) -> str:
    """生成完整 HTML 報告（含 sidebar、SVG 圖表、CSS tooltip）"""
    
    total_trades = len(trades)
    total_pnl = sum(t['net_profit'] for t in trades)
    total_wins = sum(1 for t in trades if t['net_profit'] > 0)
    wr = total_wins / total_trades * 100 if total_trades else 0
    avg_hold = sum(t['holding_hours'] for t in trades) / total_trades if total_trades else 0
    
    rating_order = {'S+': 6, 'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1, 'E': 0}
    
    def rating_color(r):
        return {'S+': '#FFD700', 'S': '#2ecc71', 'A': '#3498db', 'B': '#9b59b6',
                'C': '#f39c12', 'D': '#e67e22', 'E': '#e74c3c'}.get(r, '#999')
    
    def rating_bg(r):
        return {'S+': '#FFF8E1', 'S': '#E8F5E9', 'A': '#E3F2FD', 'B': '#F3E5F5',
                'C': '#FFF3E0', 'D': '#FBE9E7', 'E': '#FFEBEE'}.get(r, '#F5F5F5')
    
    def pnl_prefix(val):
        return '+' if val > 0 else ''
    
    # ─── Part 4 排行榜 ───
    ranking = tp_sl_data

    # ─── Part 1 條形圖數據 ───
    bar_chart_groups = []
    max_abs_pnl = max(abs(s['total_pnl']) for s in ccy_summary) if ccy_summary else 1
    max_abs_pip = max(max(abs(s['avg_win_pips']), abs(s['avg_loss_pips'])) for s in ccy_summary) if ccy_summary else 1
    for s in ccy_summary:
        bar_chart_groups.append({
            'label': f"{s['symbol']} {s['direction']}",
            'total_pnl': s['total_pnl'],
            'total_pips': s.get('total_pips', 0),
            'win_pip': s['avg_win_pips'],
            'loss_pip': s['avg_loss_pips'],
        })
    
    # Build SVG bar chart for Part 1
    def build_p1_bar_svg(groups, max_pnl, max_pip):
        if not groups:
            return '<p style="color:#888;text-align:center;padding:20px">無數據</p>'
        n = len(groups)
        svg_h = max(200, n * 38 + 60)
        bar_h = 14
        group_gap = 38
        left_margin = 60
        right_margin = 60
        chart_w = 700
        plot_w = chart_w - left_margin - right_margin
        
        # Scale: left axis ($), right axis (pip)
        def pnl_x(val):
            return left_margin + (val / max(max_pnl, 1)) * (plot_w / 2) + plot_w / 2
        def pip_x(val):
            return left_margin + (val / max(max_pip, 1)) * (plot_w / 2) + plot_w / 2
        
        svg = f'<svg viewBox="0 0 {chart_w} {svg_h}" style="width:100%;height:auto;font-family:sans-serif" xmlns="http://www.w3.org/2000/svg">'
        # Background
        svg += f'<rect width="{chart_w}" height="{svg_h}" fill="#0a0a18" rx="6"/>'
        # Zero line
        zero_x = left_margin + plot_w // 2
        svg += f'<line x1="{zero_x}" y1="30" x2="{zero_x}" y2="{svg_h-30}" stroke="#333" stroke-width="1"/>'
        # Grid lines
        for frac in [0.25, 0.5, 0.75, 1.0]:
            gx = left_margin + plot_w * frac
            svg += f'<line x1="{gx}" y1="30" x2="{gx}" y2="{svg_h-30}" stroke="#1a1a2a" stroke-width="0.5"/>'
            gx2 = left_margin + plot_w * (1 - frac)
            svg += f'<line x1="{gx2}" y1="30" x2="{gx2}" y2="{svg_h-30}" stroke="#1a1a2a" stroke-width="0.5"/>'
        
        # Axis labels
        svg += f'<text x="{left_margin}" y="18" fill="#2ecc71" font-size="9" text-anchor="start">-$</text>'
        svg += f'<text x="{chart_w - right_margin}" y="18" fill="#2ecc71" font-size="9" text-anchor="end">+$</text>'
        svg += f'<text x="{chart_w - right_margin + 5}" y="18" fill="#5dade2" font-size="9" text-anchor="start">PIP→</text>'
        
        for i, g in enumerate(groups):
            y_base = 30 + i * group_gap + 10
            # Label
            svg += f'<text x="4" y="{y_base + 5}" fill="#ccc" font-size="9">{g["label"]}</text>'
            # Total$ bar
            pnl_w = abs(g['total_pnl']) / max(max_pnl, 1) * (plot_w / 2)
            pnl_col = '#2ecc71' if g['total_pnl'] >= 0 else '#e74c3c'
            if g['total_pnl'] >= 0:
                bx = zero_x
            else:
                bx = zero_x - pnl_w
            svg += f'<rect x="{bx:.1f}" y="{y_base - 8}" width="{max(pnl_w, 1):.1f}" height="{bar_h}" fill="{pnl_col}" rx="2" opacity="0.85"/>'
            svg += f'<text x="{bx + pnl_w + 3:.1f}" y="{y_base + 3}" fill="#ccc" font-size="8">${g["total_pnl"]:,.0f}</text>'
            
            # WinPip bar (above pnl bar)
            pip_w = abs(g['win_pip']) / max(max_pip, 1) * (plot_w / 2)
            svg += f'<rect x="{zero_x:.1f}" y="{y_base - 8 - bar_h - 1}" width="{max(pip_w, 1):.1f}" height="{bar_h - 2}" fill="#5dade2" rx="2" opacity="0.6"/>'
            # LossPip bar (negative direction)
            loss_w = abs(g['loss_pip']) / max(max_pip, 1) * (plot_w / 2)
            svg += f'<rect x="{zero_x - loss_w:.1f}" y="{y_base - 8 - bar_h - 1}" width="{max(loss_w, 1):.1f}" height="{bar_h - 2}" fill="#e67e22" rx="2" opacity="0.6"/>'
        
        # Legend
        ly = svg_h - 12
        svg += f'<rect x="{left_margin}" y="{ly - 8}" width="10" height="8" fill="#2ecc71" rx="1"/>'
        svg += f'<text x="{left_margin + 14}" y="{ly}" fill="#aaa" font-size="8">Total$ (+)</text>'
        svg += f'<rect x="{left_margin + 70}" y="{ly - 8}" width="10" height="8" fill="#e74c3c" rx="1"/>'
        svg += f'<text x="{left_margin + 84}" y="{ly}" fill="#aaa" font-size="8">Total$ (-)</text>'
        svg += f'<rect x="{left_margin + 140}" y="{ly - 8}" width="10" height="8" fill="#5dade2" rx="1"/>'
        svg += f'<text x="{left_margin + 154}" y="{ly}" fill="#aaa" font-size="8">WinPip</text>'
        svg += f'<rect x="{left_margin + 200}" y="{ly - 8}" width="10" height="8" fill="#e67e22" rx="1"/>'
        svg += f'<text x="{left_margin + 214}" y="{ly}" fill="#aaa" font-size="8">LossPip</text>'
        
        svg += '</svg>'
        return svg
    
    p1_bar_svg = build_p1_bar_svg(bar_chart_groups, max_abs_pnl, max_abs_pip)
    
    # ─── PIP Bar Chart for Part 1 ───
    max_abs_total_pip = max(abs(g['total_pips']) for g in bar_chart_groups) if bar_chart_groups else 1
    
    def build_p1_pip_bar_svg(groups, max_pip):
        if not groups:
            return '<p style="color:#888;text-align:center;padding:20px">無數據</p>'
        n = len(groups)
        svg_h = max(180, n * 32 + 50)
        bar_h = 14
        group_gap = 32
        left_margin = 60
        right_margin = 40
        chart_w = 700
        plot_w = chart_w - left_margin - right_margin
        zero_x = left_margin + plot_w // 2
        
        svg = f'<svg viewBox="0 0 {chart_w} {svg_h}" style="width:100%;height:auto;font-family:sans-serif" xmlns="http://www.w3.org/2000/svg">'
        svg += f'<rect width="{chart_w}" height="{svg_h}" fill="#0a0a18" rx="6"/>'
        # Zero line
        svg += f'<line x1="{zero_x}" y1="25" x2="{zero_x}" y2="{svg_h-25}" stroke="#333" stroke-width="1"/>'
        # Grid
        for frac in [0.25, 0.5, 0.75, 1.0]:
            gx = left_margin + plot_w * frac
            svg += f'<line x1="{gx:.1f}" y1="25" x2="{gx:.1f}" y2="{svg_h-25}" stroke="#1a1a2a" stroke-width="0.5"/>'
            gx2 = left_margin + plot_w * (1 - frac)
            svg += f'<line x1="{gx2:.1f}" y1="25" x2="{gx2:.1f}" y2="{svg_h-25}" stroke="#1a1a2a" stroke-width="0.5"/>'
        
        for i, g in enumerate(groups):
            y_base = 25 + i * group_gap + 10
            svg += f'<text x="4" y="{y_base + 4}" fill="#ccc" font-size="9">{g["label"]}</text>'
            # PIP bar
            pip_val = g['total_pips']
            pip_w = abs(pip_val) / max(max_pip, 1) * (plot_w / 2)
            pip_col = '#2ecc71' if pip_val >= 0 else '#e74c3c'
            if pip_val >= 0:
                bx = zero_x
            else:
                bx = zero_x - pip_w
            svg += f'<rect x="{bx:.1f}" y="{y_base - 7}" width="{max(pip_w, 1):.1f}" height="{bar_h}" fill="{pip_col}" rx="2" opacity="0.85"/>'
            svg += f'<text x="{bx + pip_w + 3:.1f}" y="{y_base + 4}" fill="#ccc" font-size="8">{pip_val:+.1f} pip</text>'
        
        # Legend
        ly = svg_h - 8
        svg += f'<rect x="{left_margin}" y="{ly-8}" width="10" height="8" fill="#2ecc71" rx="1"/>'
        svg += f'<text x="{left_margin+14}" y="{ly}" fill="#aaa" font-size="8">賺 PIP</text>'
        svg += f'<rect x="{left_margin+60}" y="{ly-8}" width="10" height="8" fill="#e74c3c" rx="1"/>'
        svg += f'<text x="{left_margin+74}" y="{ly}" fill="#aaa" font-size="8">蝕 PIP</text>'
        
        svg += '</svg>'
        return svg
    
    p1_pip_bar_svg = build_p1_pip_bar_svg(bar_chart_groups, max_abs_total_pip)
    
    # ─── Part 2: MFE/MAE 散點圖 (inline SVG + CSS tooltip) ───
    ccy_dir_groups = defaultdict(dict)
    for key, stats in layer_stats.items():
        ccy_key = (stats['symbol'], stats['direction'])
        ccy_dir_groups[ccy_key][key] = stats
    
    def build_scatter_svg(symbol, direction, layers, trade_list):
        """Build inline SVG scatter chart: X=MFE, Y=-MAE, with CSS tooltip"""
        if not trade_list:
            return '<p style="color:#888;font-size:10px">無交易數據</p>'
        
        svg_w, svg_h = 340, 240
        pad = {'top': 20, 'right': 15, 'bottom': 30, 'left': 35}
        plot_w = svg_w - pad['left'] - pad['right']
        plot_h = svg_h - pad['top'] - pad['bottom']
        
        # Compute bounds
        max_mfe = max((abs(d['mfe']) for d in trade_list), default=1) or 1
        max_mae = max((abs(d['mae']) for d in trade_list), default=1) or 1
        # Add 10% padding
        max_mfe *= 1.1
        max_mae *= 1.1
        
        svg = f'<svg viewBox="0 0 {svg_w} {svg_h}" style="width:100%;height:auto;font-family:sans-serif" xmlns="http://www.w3.org/2000/svg">'
        svg += f'<rect width="{svg_w}" height="{svg_h}" fill="#0a0a18" rx="4"/>'
        
        # Grid
        for i in range(5):
            frac = i / 4
            gx = pad['left'] + plot_w * frac
            gy = pad['top'] + plot_h * frac
            svg += f'<line x1="{gx:.1f}" y1="{pad["top"]}" x2="{gx:.1f}" y2="{pad["top"]+plot_h}" stroke="#1a1a2a" stroke-width="0.5"/>'
            svg += f'<line x1="{pad["left"]}" y1="{gy:.1f}" x2="{pad["left"]+plot_w}" y2="{gy:.1f}" stroke="#1a1a2a" stroke-width="0.5"/>'
            # X axis labels (MFE)
            mfe_val = max_mfe * frac
            svg += f'<text x="{gx:.1f}" y="{svg_h - 8}" fill="#555" font-size="7" text-anchor="middle">{mfe_val:.0f}</text>'
            # Y axis labels (-MAE)
            mae_val = max_mae * (1 - frac)
            svg += f'<text x="{pad["left"]-4}" y="{gy+3:.1f}" fill="#555" font-size="7" text-anchor="end">{mae_val:.0f}</text>'
        
        # Axis titles
        svg += f'<text x="{pad["left"]+plot_w//2}" y="{svg_h-1}" fill="#777" font-size="8" text-anchor="middle">MFE →</text>'
        svg += f'<text x="8" y="{pad["top"]+plot_h//2}" fill="#777" font-size="8" text-anchor="middle" transform="rotate(-90,8,{pad["top"]+plot_h//2})">-MAE →</text>'
        
        # Scatter dots with CSS tooltip
        # We need a <style> block inside the SVG for tooltips
        svg += '<style>'
        svg += '.dot{opacity:0.85;cursor:pointer} .dot:hover{opacity:1;r:5} .dot .tip{display:none} .dot:hover .tip{display:block}'
        svg += '</style>'
        
        for idx, d in enumerate(trade_list):
            mfe = abs(d['mfe'])
            mae = abs(d['mae'])
            is_win = d['is_win']
            col = '#2ecc71' if is_win else '#e74c3c'
            
            cx = pad['left'] + (mfe / max_mfe) * plot_w
            cy = pad['top'] + (1 - mae / max_mae) * plot_h
            # Clamp
            cx = max(pad['left'], min(pad['left'] + plot_w, cx))
            cy = max(pad['top'], min(pad['top'] + plot_h, cy))
            
            svg += f'<g class="dot">'
            svg += f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="3" fill="{col}"/>'
            # Tooltip (shown on hover via CSS)
            tip_x = cx + 6
            tip_y = cy - 8
            # Keep tooltip within bounds
            if tip_x + 90 > svg_w:
                tip_x = cx - 96
            if tip_y < 10:
                tip_y = cy + 10
            hold_h = d.get('holding_hours', 0)
            tip_text = f"#{idx+1} MFE:{d['mfe']:.1f} MAE:{d['mae']:.1f} ${d['net_profit']:.2f} L{d['lots']} Hold:{hold_h:.1f}h"
            svg += f'<g class="tip">'
            svg += f'<rect x="{tip_x:.1f}" y="{tip_y-8:.1f}" width="{len(tip_text)*5.2+8:.0f}" height="14" fill="#1a1a3e" stroke="#4a3f8a" rx="3"/>'
            svg += f'<text x="{tip_x+4:.1f}" y="{tip_y+2:.1f}" fill="#eee" font-size="7">{tip_text}</text>'
            svg += '</g>'
            svg += '</g>\n'
        
        svg += '</svg>'
        return svg
    
    # Build scatter SVGs per CCY×Dir
    scatter_svgs = []
    for (symbol, direction), layers in sorted(ccy_dir_groups.items()):
        all_trades = []
        for lkey, lstats in sorted(layers.items(), key=lambda x: x[1]['lots']):
            for td in lstats['trade_details']:
                all_trades.append(td)
        scatter_svgs.append({
            'symbol': symbol,
            'direction': direction,
            'layer_count': len(layers),
            'svg': build_scatter_svg(symbol, direction, layers, all_trades),
            'layers_summary': layers,
        })
    
    # ─── Part 3: TP/SL 條形圖 SVG ───
    def build_tpsl_bar_svg(tp_sl_items):
        if not tp_sl_items:
            return '<p style="color:#888;text-align:center;padding:20px">無 A 級以上層級</p>'
        
        n = len(tp_sl_items)
        svg_w = 700
        bar_h = 16
        group_gap = 6
        left_margin = 100
        right_margin = 20
        top_pad = 30
        bot_pad = 30
        plot_w = svg_w - left_margin - right_margin
        svg_h = top_pad + n * (bar_h * 2 + group_gap + 10) + bot_pad
        
        max_sl = max(max(r['soft_sl'], r['hard_sl'], r['tp']) for r in tp_sl_items) or 1
        
        svg = f'<svg viewBox="0 0 {svg_w} {svg_h}" style="width:100%;height:auto;font-family:sans-serif" xmlns="http://www.w3.org/2000/svg">'
        svg += f'<rect width="{svg_w}" height="{svg_h}" fill="#0a0a18" rx="6"/>'
        
        # Grid
        for frac in [0.25, 0.5, 0.75, 1.0]:
            gx = left_margin + plot_w * frac
            svg += f'<line x1="{gx:.1f}" y1="{top_pad-10}" x2="{gx:.1f}" y2="{svg_h - bot_pad + 10}" stroke="#1a1a2a" stroke-width="0.5"/>'
            val = max_sl * frac
            svg += f'<text x="{gx:.1f}" y="{top_pad - 14}" fill="#555" font-size="7" text-anchor="middle">{val:.0f}</text>'
        
        for i, r in enumerate(tp_sl_items):
            y_base = top_pad + i * (bar_h * 2 + group_gap + 10)
            label = f"{r['symbol']} {r['direction']} {r['layer']}"
            rc = rating_color(r['rating'])
            svg += f'<text x="4" y="{y_base + 6}" fill="#ccc" font-size="8">{label}</text>'
            svg += f'<text x="4" y="{y_base + 16}" fill="{rc}" font-size="8" font-weight="bold">{r["rating"]}</text>'
            
            # Soft SL bar
            soft_w = (r['soft_sl'] / max_sl) * plot_w
            svg += f'<rect x="{left_margin:.1f}" y="{y_base:.1f}" width="{max(soft_w, 1):.1f}" height="{bar_h}" fill="#f39c12" rx="2" opacity="0.85"/>'
            svg += f'<text x="{left_margin + soft_w + 3:.1f}" y="{y_base + 11}" fill="#ccc" font-size="7">SL {r["soft_sl"]}</text>'
            
            # Hard SL bar
            hard_w = (r['hard_sl'] / max_sl) * plot_w
            svg += f'<rect x="{left_margin:.1f}" y="{y_base + bar_h + 1:.1f}" width="{max(hard_w, 1):.1f}" height="{bar_h}" fill="#e74c3c" rx="2" opacity="0.85"/>'
            svg += f'<text x="{left_margin + hard_w + 3:.1f}" y="{y_base + bar_h + 12}" fill="#ccc" font-size="7">Hard {r["hard_sl"]}</text>'
        
        # Legend
        ly = svg_h - 10
        svg += f'<rect x="{left_margin}" y="{ly-8}" width="10" height="8" fill="#f39c12" rx="1"/>'
        svg += f'<text x="{left_margin+14}" y="{ly}" fill="#aaa" font-size="8">Soft SL</text>'
        svg += f'<rect x="{left_margin+70}" y="{ly-8}" width="10" height="8" fill="#e74c3c" rx="1"/>'
        svg += f'<text x="{left_margin+84}" y="{ly}" fill="#aaa" font-size="8">Hard SL</text>'
        
        svg += '</svg>'
        return svg
    
    p3_bar_svg = build_tpsl_bar_svg(tp_sl_data)
    
    # ─── Build full HTML ───
    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>馬丁剖析法 V3 — Signal #{signal_id}</title>
    <link rel="stylesheet" href="../sidebar.css">
    <style>
        :root {{--bg:#0a0a1a;--surface:#0f0f23;--border:#2a2a4a;--text:#e0e0e0;--muted:#888;--accent:#FFD700}}
        [data-theme="light"] {{--bg:#f5f5f5;--surface:#fff;--border:#ddd;--text:#222;--muted:#666;--accent:#d4a017}}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 12px;
            line-height: 1.5;
            color: var(--text);
            background: var(--bg);
            padding: 15px;
        }}
        body.has-sidebar {{ margin-left: 200px; }}
        .theme-toggle {{
            position:fixed;top:12px;right:16px;z-index:1001;
            background:var(--surface);color:var(--text);border:1px solid var(--border);
            border-radius:50%;width:36px;height:36px;font-size:16px;cursor:pointer;
            display:flex;align-items:center;justify-content:center;
            transition:background .2s;
        }}
        .theme-toggle:hover {{ background:var(--border); }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        /* Header */
        .header {{
            background: linear-gradient(135deg, #1a1a3e 0%, #2d1b69 50%, #1a1a3e 100%);
            border: 1px solid #4a3f8a;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }}
        .header h1 {{
            font-size: 22px;
            color: #FFD700;
            margin-bottom: 4px;
        }}
        .header .subtitle {{
            font-size: 12px;
            color: #999;
        }}
        .kpi-row {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
            gap: 12px;
            margin-top: 15px;
        }}
        .kpi-card {{
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 10px;
            text-align: center;
        }}
        .kpi-card .label {{
            font-size: 10px;
            color: #888;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        .kpi-card .value {{
            font-size: 18px;
            font-weight: bold;
            color: #fff;
            margin-top: 4px;
        }}
        .kpi-card .value.green {{ color: #2ecc71; }}
        .kpi-card .value.red {{ color: #e74c3c; }}
        .kpi-card .value.gold {{ color: #FFD700; }}
        
        /* Section */
        .section {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: 10px;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        .section-header {{
            background: linear-gradient(90deg, #1a1a3e, #2d1b69);
            padding: 12px 16px;
            font-size: 14px;
            font-weight: bold;
            color: #fff;
            border-bottom: 1px solid #3a3a6a;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .section-header .badge {{
            display: inline-block;
            background: #FFD700;
            color: #000;
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 10px;
            font-weight: normal;
        }}
        .section-body {{
            padding: 12px;
        }}
        
        /* Info icon with tooltip */
        .info-icon {{
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 18px;
            height: 18px;
            border-radius: 50%;
            background: rgba(255,255,255,0.15);
            color: #ccc;
            font-size: 11px;
            cursor: help;
            font-style: normal;
            flex-shrink: 0;
        }}
        .info-icon .info-tip {{
            display: none;
            position: absolute;
            top: 100%;
            left: 50%;
            transform: translateX(-50%);
            background: #1a1a3e;
            border: 1px solid #4a3f8a;
            border-radius: 6px;
            padding: 8px 10px;
            font-size: 10px;
            font-weight: normal;
            color: #ccc;
            white-space: normal;
            width: 280px;
            z-index: 100;
            line-height: 1.6;
            box-shadow: 0 4px 12px rgba(0,0,0,.5);
            pointer-events: none;
        }}
        .info-icon:hover .info-tip,
        .info-icon:focus .info-tip {{
            display: block;
        }}
        
        /* Tables */
        .table-wrap {{
            overflow-x: auto;
            -webkit-overflow-scrolling: touch;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
        }}
        table th {{
            background: #1a1a3e;
            color: #bbb;
            padding: 6px 8px;
            text-align: left;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #3a3a6a;
            white-space: nowrap;
            position: sticky;
            top: 0;
        }}
        table td {{
            padding: 5px 8px;
            border-bottom: 1px solid #1a1a2a;
            white-space: nowrap;
        }}
        table tr:hover {{ background: rgba(255,255,255,0.03); }}
        
        .positive {{ color: #2ecc71; }}
        .negative {{ color: #e74c3c; }}
        .neutral {{ color: #888; }}
        
        /* Rating badge */
        .rating {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-weight: bold;
            font-size: 11px;
            text-align: center;
            min-width: 30px;
        }}
        
        /* Scatter grid */
        .scatter-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 12px;
        }}
        .scatter-card {{
            background: #0a0a18;
            border: 1px solid #2a2a4a;
            border-radius: 8px;
            padding: 8px;
        }}
        .scatter-card .title {{
            font-size: 11px;
            color: #bbb;
            margin-bottom: 4px;
        }}
        .scatter-card .stats-row {{
            font-size: 10px;
            color: #888;
            margin-bottom: 6px;
        }}
        
        /* Chart container */
        .chart-container {{
            margin-top: 16px;
            padding: 12px;
            background: #0a0a18;
            border: 1px solid #2a2a4a;
            border-radius: 8px;
        }}
        .chart-title {{
            font-size: 11px;
            color: #bbb;
            margin-bottom: 8px;
        }}
        
        /* Section nav — anchor-based, no JS tabs */
        .section-nav {{
            display: flex;
            gap: 2px;
            flex-wrap: wrap;
            background: #0a0a18;
            border-bottom: 2px solid #2a2a4a;
            padding: 0 12px;
            position: sticky;
            top: 0;
            z-index: 50;
        }}
        .section-nav a {{
            padding: 8px 16px;
            font-size: 12px;
            color: #888;
            text-decoration: none;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }}
        .section-nav a:hover {{ color: #FFD700; border-bottom-color: #FFD700; }}
        .tab-panel {{ padding-top: 0; }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 15px;
            color: #555;
            font-size: 10px;
        }}

        /* Light theme overrides */
        [data-theme="light"] .header {{
            background: linear-gradient(135deg, #e8eaf6 0%, #c5cae9 50%, #e8eaf6 100%);
            border-color: #9fa8da;
        }}
        [data-theme="light"] .header h1 {{ color: #1a237e; }}
        [data-theme="light"] .section-header {{
            background: linear-gradient(90deg, #e8eaf6, #c5cae9);
            color: #1a237e;
            border-bottom-color: #9fa8da;
        }}
        [data-theme="light"] table th {{
            background: #e8eaf6;
            color: #555;
            border-bottom-color: #c5cae9;
        }}
        [data-theme="light"] table td {{ border-bottom-color: #e0e0e0; }}
        [data-theme="light"] .scatter-card,
        [data-theme="light"] .chart-container {{
            background: #fff;
            border-color: #ddd;
        }}
        [data-theme="light"] .info-icon .info-tip {{
            background: #fff;
            border-color: #ccc;
            color: #333;
        }}
        [data-theme="light"] .section-nav {{
            background: #e0e0e0;
            border-bottom-color: #ccc;
        }}
    </style>
    <script>
    // Theme toggle (minimal JS, only for theme persistence)
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
</head>
<body class="has-sidebar">
<button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()" title="切換亮/暗模式" style="position:fixed;top:12px;right:16px;z-index:1001">🌓</button>
<div class="container">
    <!-- Header -->
    <div class="header">
        <h1>🔬 馬丁剖析法 V3 — Signal #{signal_id}</h1>
        <div class="subtitle">
            數據覆蓋 {len(ccy_summary)} 個 CCY×Direction 組合 · {len(layer_stats)} 個層級 · 生成時間 {datetime.now().strftime('%Y-%m-%d %H:%M')}
        </div>
        <div class="kpi-row">
            <div class="kpi-card">
                <div class="label">總交易</div>
                <div class="value">{total_trades}</div>
            </div>
            <div class="kpi-card">
                <div class="label">總盈虧</div>
                <div class="value {'green' if total_pnl > 0 else 'red'}">${pnl_prefix(total_pnl)}{total_pnl:,.2f}</div>
            </div>
            <div class="kpi-card">
                <div class="label">勝率</div>
                <div class="value {'green' if wr > 60 else 'red'}">{wr:.1f}%</div>
            </div>
            <div class="kpi-card">
                <div class="label">平均持倉</div>
                <div class="value">{avg_hold:.1f}h</div>
            </div>
            <div class="kpi-card">
                <div class="label">A 級以上</div>
                <div class="value gold">{len(ranking)} 層</div>
            </div>
            <div class="kpi-card">
                <div class="label">黑名單</div>
                <div class="value {'red' if blacklist else 'green'}">{len(blacklist)} 個</div>
            </div>
        </div>
    </div>
    
    <!-- Section Navigation (anchor-based) -->
    <div class="section-nav">
        <a href="#part1">Part 1 · CCY總覽</a>
        <a href="#part2">Part 2 · MFE/MAE</a>
        <a href="#part3">Part 3 · TP/SL</a>
        <a href="#part4">Part 4 · 排行榜</a>
        <a href="#part5">Part 5 · 黑名單</a>
        <a href="#part6">Part 6 · 恢復力</a>
    </div>
    
    <div class="tab-panels">
    
    <!-- Part 1: CCY × Direction 總覽 -->
    <div id="part1" class="tab-panel">
        <div class="section">
            <div class="section-header">
                Part 1 · CCY × Direction 總覽
                <span class="badge">{len(ccy_summary)} 組合</span>
                <i class="info-icon" tabindex="0">ℹ<span class="info-tip">
                    <b>欄位說明：</b><br>
                    <b>Trades</b>: 該 CCY×方向的總交易次數<br>
                    <b>Layers</b>: 觸發的馬丁層級數量<br>
                    <b>MaxD</b>: 最大回撤金額<br>
                    <b>Total$</b>: 總盈虧金額<br>
                    <b>WR%</b>: 勝率（盈利交易/總交易）<br>
                    <b>EV$/L</b>: 每層預期盈虧<br>
                    <b>WinPip</b>: 平均盈利 PIP<br>
                    <b>LossPip</b>: 平均虧損 PIP<br>
                    <b>Odds$</b>: 金額盈虧比<br>
                    <b>OddsPip</b>: PIP 盈虧比<br>
                    <b>MFE</b>: 最大有利波幅<br>
                    <b>MAE</b>: 最大不利波幅<br>
                    <b>MaxMAE</b>: 歷史最大 MAE
                </span></i>
            </div>
            <div class="section-body">
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>CCY</th>
                                <th>Dir</th>
                                <th>Trades</th>
                                <th>Layers</th>
                                <th>MaxD</th>
                                <th>Total$</th>
                                <th>WR%</th>
                                <th>EV$/L</th>
                                <th>AvgW Pip</th>
                                <th>AvgL Pip</th>
                                <th>Odds$</th>
                                <th>OddsPip</th>
                                <th>AvgMFE</th>
                                <th>AvgMAE</th>
                                <th>MaxMAE</th>
                            </tr>
                        </thead>
                        <tbody>
"""
    
    for i, s in enumerate(ccy_summary, 1):
        pnl_cls = 'positive' if s['total_pnl'] > 0 else 'negative' if s['total_pnl'] < 0 else 'neutral'
        anchor = f"ccy-{s['symbol']}-{s['direction']}"
        html += f"""                            <tr>
                                <td>{i}</td>
                                <td><b><a href=\"#part2-{anchor}\" style=\"color:var(--text);text-decoration:none\">{s['symbol']}</a></b></td>
                                <td><a href=\"#part2-{anchor}\" style=\"color:var(--text);text-decoration:none\">{s['direction']}</a></td>
                                <td>{s['trades']}</td>
                                <td>{s['layers']}</td>
                                <td>{s['max_depth']}</td>
                                <td class=\"{pnl_cls}\"><b>${pnl_prefix(s['total_pnl'])}{s['total_pnl']:,.2f}</b></td>
                                <td>{s['wr']}%</td>
                                <td class=\"{'positive' if s['avg_ev'] > 0 else 'negative'}\">{pnl_prefix(s['avg_ev'])}{s['avg_ev']}</td>
                                <td>{s['avg_win_pips']}</td>
                                <td>{s['avg_loss_pips']}</td>
                                <td>{s['avg_odds_dollar']}</td>
                                <td>{s['avg_odds_pips']}</td>
                                <td>{s['avg_mfe']}</td>
                                <td>{s['avg_mae']}</td>
                                <td><b>{s['max_mae']}</b></td>
                            </tr>
"""
    
    html += f"""                        </tbody>
                    </table>
                </div>
                <!-- Part 1 Dollar Bar Chart -->
                <div class="chart-container">
                    <div class="chart-title">📊 Total$ 金額條形圖</div>
                    {p1_bar_svg}
                </div>
                <!-- Part 1 PIP Bar Chart -->
                <div class="chart-container">
                    <div class="chart-title">📊 Total PIP 賺/蝕條形圖（綠=賺 · 紅=蝕）</div>
                    {p1_pip_bar_svg}
                </div>
            </div>
        </div>
    </div>
"""
    
    # ─── Part 2: MFE/MAE 散點圖 ───
    html += """    <!-- Part 2: MFE/MAE -->
    <div id="part2" class="tab-panel">
        <div class="section">
            <div class="section-header">
                Part 2 · MFE/MAE 散點分析
                <span class="badge">每組合一圖 · 綠=Win · 紅=Loss · Hover 查詳情</span>
                <i class="info-icon" tabindex="0">ℹ<span class="info-tip">
                    <b>MFE/MAE 散點分析</b><br>
                    顯示每筆交易嘅最大有利波幅（MFE）同最大不利波幅（MAE）嘅關係。<br><br>
                    <b>欄位說明：</b><br>
                    <b>MFE</b>: Maximum Favorable Excursion — 交易期間最大有利波幅（PIP）<br>
                    <b>MAE</b>: Maximum Adverse Excursion — 交易期間最大不利波幅（PIP）<br>
                    <b>Hold</b>: 持倉時間（小時）<br>
                    <b>L</b>: 馬丁層級（Lots 大小）<br><br>
                    綠色圓點 = 盈利交易 | 紅色圓點 = 虧損交易<br>
                    Hover 可看每筆交易詳情（MFE、MAE、金額、層級、持倉時間）
                </span></i>
            </div>
            <div class="section-body">
                <div class="scatter-grid">
"""
    
    for sc in scatter_svgs:
        layers_summary_lines = []
        for lkey, lstats in sorted(sc['layers_summary'].items(), key=lambda x: x[1]['lots']):
            layers_summary_lines.append(f"L{lstats['lots']} (n={lstats['count']}) WR:{lstats['wr']}% MFE:{lstats['avg_mfe']} MAE:{lstats['avg_mae']}")
        
        layers_text = '<br>\n'.join(layers_summary_lines)
        anchor_id = f"part2-ccy-{sc['symbol']}-{sc['direction']}"
        html += f"""                    <div class="scatter-card" id="{anchor_id}">
                        <div class="title"><b>{sc['symbol']} {sc['direction']}</b> ({sc['layer_count']} layers)</div>
                        <div class="stats-row">{layers_text}</div>
                        {sc['svg']}
                    </div>
"""
    
    html += """                </div>
            </div>
        </div>
    </div>
"""
    
    # ─── Part 3: TP/SL ───
    html += f"""    <!-- Part 3: TP/SL -->
    <div id="part3" class="tab-panel">
        <div class="section">
            <div class="section-header">
                Part 3 · A 級以上 TP/SL 建議（混合方案）
                <span class="badge">{len(tp_sl_data)} 層</span>
                <i class="info-icon" tabindex="0">ℹ<span class="info-tip">
                    <b>TP/SL 建議說明</b><br>
                    只顯示 A 級以上嘅層級，提供 Take Profit 同 Stop Loss 建議值。<br><br>
                    <b>計算方法：</b><br>
                    <b>TP</b>: 該層所有交易嘅平均 MFE（最大有利波幅）<br>
                    <b>Soft SL</b>: 該層所有交易嘅平均 MAE（最大不利波幅）<br>
                    <b>Hard SL</b>: 該 CCY×Direction 組合嘅歷史最大 MAE<br>
                    <b>R:R</b>: TP / Soft SL（≥1.5x 可接受，≥3.0x 優秀）<br><br>
                    <b>表格欄位：</b><br>
                    Rating | CCY | Dir | Layer | n | WR% | EV$ | TP | SoftSL | HardSL | R:R | Total$ | AvgHold
                </span></i>
            </div>
            <div class="section-body">
                <div style="font-size:10px; color:#888; margin-bottom:10px;">
                    TP = Avg MFE &nbsp;|&nbsp; Soft SL = Avg MAE &nbsp;|&nbsp; Hard SL = Pair Max MAE &nbsp;|&nbsp; R:R = TP / Soft SL（≥1.5x 可接受，≥3.0x 優秀）
                </div>
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>Rating</th>
                                <th>CCY</th>
                                <th>Dir</th>
                                <th>Layer</th>
                                <th>n</th>
                                <th>WR%</th>
                                <th>EV$</th>
                                <th>TP(pip)</th>
                                <th>SoftSL</th>
                                <th>HardSL</th>
                                <th>R:R</th>
                                <th>Total$</th>
                                <th>AvgHold</th>
                            </tr>
                        </thead>
                        <tbody>
"""
    
    for r in tp_sl_data:
        rc = rating_color(r['rating'])
        rbg = rating_bg(r['rating'])
        rr_cls = 'positive' if r['rr'] >= 1.5 else 'negative'
        html += f"""                            <tr>
                                <td><span class="rating" style="background:{rbg};color:{rc}">{r['rating']}</span></td>
                                <td><b>{r['symbol']}</b></td>
                                <td>{r['direction']}</td>
                                <td>{r['layer']}</td>
                                <td>{r['count']}</td>
                                <td>{r['wr']}%</td>
                                <td class="{'positive' if r['ev'] > 0 else 'negative'}">{pnl_prefix(r['ev'])}{r['ev']}</td>
                                <td class="positive">{r['tp']}</td>
                                <td style="color:#f39c12">{r['soft_sl']}</td>
                                <td class="negative">{r['hard_sl']}</td>
                                <td class="{rr_cls}"><b>{r['rr']}x</b></td>
                                <td class="{'positive' if r['total_pnl'] > 0 else 'negative'}">{pnl_prefix(r['total_pnl'])}{r['total_pnl']:.2f}</td>
                                <td>{r['avg_hold']:.0f}h</td>
                            </tr>
"""
    
    html += f"""                        </tbody>
                    </table>
                </div>
                <!-- Part 3 TP/SL Bar Chart -->
                <div class="chart-container">
                    <div class="chart-title">📊 TP/SL 條形圖 — 🟠 Soft SL / 🔴 Hard SL</div>
                    {p3_bar_svg}
                </div>
            </div>
        </div>
    </div>
"""
    
    # ─── Part 4: 排行榜 ───
    html += f"""    <!-- Part 4: Ranking -->
    <div id="part4" class="tab-panel">
        <div class="section">
            <div class="section-header">
                Part 4 · A 級以上排行榜
                <span class="badge">{len(ranking)} 層</span>
                <i class="info-icon" tabindex="0">ℹ<span class="info-tip">
                    <b>排行榜說明</b><br>
                    只顯示 A 級以上嘅層級，按評級同 EV 排序。<br><br>
                    <b>評級系統（S+ 到 E）：</b><br>
                    基於 5 個維度加權計算：<br>
                    <b>WR (25%)</b>: 勝率 — 越高越好<br>
                    <b>EV (30%)</b>: 預期盈虧 — 核心指標<br>
                    <b>Odds (20%)</b>: 盈虧比 — 越高越好<br>
                    <b>Count (15%)</b>: 樣本數 — 越多越可靠<br>
                    <b>Hold (10%)</b>: 持倉效率 — 越短越好<br><br>
                    <b>評級映射：</b>S+ ≥85 | S ≥70 | A ≥55 | B ≥40 | C ≥25 | D ≥15 | E &lt;15
                </span></i>
            </div>
            <div class="section-body">
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Rating</th>
                                <th>CCY</th>
                                <th>Dir</th>
                                <th>Layer</th>
                                <th>Trades</th>
                                <th>WR%</th>
                                <th>EV$</th>
                                <th>Odds$</th>
                                <th>OddsPip</th>
                                <th>TP(pip)</th>
                                <th>SoftSL</th>
                                <th>HardSL</th>
                                <th>Total$</th>
                                <th>AvgHold(h)</th>
                            </tr>
                        </thead>
                        <tbody>
"""
    
    for i, r in enumerate(ranking, 1):
        rc = rating_color(r['rating'])
        rbg = rating_bg(r['rating'])
        html += f"""                            <tr>
                                <td>{i}</td>
                                <td><span class="rating" style="background:{rbg};color:{rc}">{r['rating']}</span></td>
                                <td><b>{r['symbol']}</b></td>
                                <td>{r['direction']}</td>
                                <td>{r['layer']}</td>
                                <td>{r['count']}</td>
                                <td>{r['wr']}%</td>
                                <td class="{'positive' if r['ev'] > 0 else 'negative'}"><b>{pnl_prefix(r['ev'])}{r['ev']}</b></td>
                                <td>{r['odds_dollar']}</td>
                                <td>{r['odds_pips']}</td>
                                <td class="positive">{r['tp']}</td>
                                <td style="color:#f39c12">{r['soft_sl']}</td>
                                <td class="negative">{r['hard_sl']}</td>
                                <td class="{'positive' if r['total_pnl'] > 0 else 'negative'}">{pnl_prefix(r['total_pnl'])}{r['total_pnl']:.2f}</td>
                                <td>{r['avg_hold']:.0f}</td>
                            </tr>
"""
    
    html += """                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
"""
    
    # ─── Part 5: 黑名單 ───
    html += f"""    <!-- Part 5: Blacklist -->
    <div id="part5" class="tab-panel">
        <div class="section">
            <div class="section-header">
                Part 5 · 黑名單
                <span class="badge">{len(blacklist)} 個危險組合</span>
                <i class="info-icon" tabindex="0">ℹ<span class="info-tip">
                    <b>黑名單說明</b><br>
                    列出所有危險嘅 CCY×Direction 組合。<br><br>
                    <b>Danger Score 計算方法：</b><br>
                    基於以下因素加權計算：<br>
                    1. 總虧損金額（每 $1000 加 1 分）<br>
                    2. 平均賠率 &lt; 1.0（加 3 分）<br>
                    3. 勝率 &lt; 50%（加 2 分）<br>
                    4. 平均 EV 爲負（按比例加分）<br>
                    5. 最差層級 EV &lt; -50（加 2 分）<br><br>
                    <b>危險等級：</b><br>
                    ⚠️ WARNING: Danger ≥ 1<br>
                    💀 DEADLY: Danger > 5<br><br>
                    <b>表格欄位：</b>危險度 | Danger | CCY | Dir | Total$ | WR% | Avg Odds | Avg EV | Worst EV | 最差層 | Avg Hold
                </span></i>
            </div>
            <div class="section-body">
"""
    
    if blacklist:
        html += """                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>危險度</th>
                                <th>Danger</th>
                                <th>CCY</th>
                                <th>Dir</th>
                                <th>Total$</th>
                                <th>WR%</th>
                                <th>Avg Odds</th>
                                <th>Avg EV</th>
                                <th>Worst EV</th>
                                <th>最差層</th>
                                <th>Avg Hold</th>
                            </tr>
                        </thead>
                        <tbody>
"""
        for b in blacklist:
            html += f"""                            <tr>
                                <td>{b['level']}</td>
                                <td><b>{b['danger']}</b></td>
                                <td><b>{b['symbol']}</b></td>
                                <td>{b['direction']}</td>
                                <td class="negative">{b['total_pnl']:.2f}</td>
                                <td>{b['wr']}%</td>
                                <td>{b['avg_odds']}</td>
                                <td class="negative">{b['avg_ev']}</td>
                                <td class="negative">{b['worst_ev']}</td>
                                <td>{b['worst_layer']}</td>
                                <td>{b['avg_hold']:.1f}h</td>
                            </tr>
"""
        html += """                        </tbody>
                    </table>
                </div>
"""
    else:
        html += '                <div style="text-align:center;padding:20px;color:#2ecc71;">✅ 沒有危險組合，所有 CCY×Direction 表現良好</div>\n'
    
    html += """            </div>
        </div>
    </div>
"""
    
    # ─── Part 6: 恢復力 ───
    html += f"""    <!-- Part 6: Recovery -->
    <div id="part6" class="tab-panel">
        <div class="section">
            <div class="section-header">
                Part 6 · 恢復力分析
                <span class="badge">如果最深層被 Hard SL 止損，要用最佳 EV 層贏幾多次先追得返？</span>
                <i class="info-icon" tabindex="0">ℹ<span class="info-tip">
                    <b>恢復力分析說明</b><br>
                    假設最深層被 Hard SL 止損，需要幾多次最佳 EV 層交易先可以追回損失。<br><br>
                    <b>計算方式：</b><br>
                    <b>恢復次數</b> = ceil(最深層平均損失 / 最佳 EV)<br>
                    <b>恢復天數</b> = 恢復次數 / 每月交易頻率 × 30<br><br>
                    <b>狀態標記：</b><br>
                    🟢 安全: ≤4 次可恢復<br>
                    🟡 需時: 5-20 次可恢復<br>
                    🔴 無法恢復: >20 次或 EV ≤ 0<br><br>
                    <b>表格欄位：</b>狀態 | CCY | Dir | 最深層 | 最差損失 | 最佳 EV 層 | Best EV$ | 恢復次數 | 恢復天數 | Avg Hold | 說明
                </span></i>
            </div>
            <div class="section-body">
                <div class="table-wrap">
                    <table>
                        <thead>
                            <tr>
                                <th>狀態</th>
                                <th>CCY</th>
                                <th>Dir</th>
                                <th>最深層</th>
                                <th>最差損失</th>
                                <th>最佳 EV 層</th>
                                <th>Best EV$</th>
                                <th>恢復次數</th>
                                <th>恢復天數</th>
                                <th>Avg Hold</th>
                                <th>說明</th>
                            </tr>
                        </thead>
                        <tbody>
"""
    
    for r in recovery:
        html += f"""                            <tr>
                                <td>{r['status']}</td>
                                <td><b>{r['symbol']}</b></td>
                                <td>{r['direction']}</td>
                                <td>{r['deepest_layer']}</td>
                                <td class="negative">${r['worst_loss']:.2f}</td>
                                <td>{r['best_ev_layer']}</td>
                                <td class="{'positive' if r['best_ev'] > 0 else 'negative'}">{pnl_prefix(r['best_ev'])}{r['best_ev']}</td>
                                <td><b>{r['recovery_trades'] if r['recovery_trades'] < 999 else '∞'}</b></td>
                                <td>{r['recovery_days'] if r['recovery_days'] < 999 else '∞'}天</td>
                                <td>{r['avg_hold']:.1f}h</td>
                                <td>{r['status_text']}</td>
                            </tr>
"""
    
    html += f"""                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    
    </div><!-- end tab-panels -->
    
    <div class="footer">
        馬丁剖析法 V3 · 數據說話，紀律至上 · Quant 📊
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
    
    print(f"📊 馬丁剖析法 V3 — Signal #{signal_id}")
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
    
    print(f"✅ Part 1: {len(ccy_summary)} CCY×Dir 組合")
    print(f"✅ Part 3: {len(tp_sl_data)} A級以上層級")
    print(f"✅ Part 5: {len(blacklist)} 黑名單組合")
    print(f"✅ Part 6: {len(recovery)} 恢復力分析")
    
    # 生成 HTML
    html = generate_html(signal_id, trades, layer_stats, ccy_summary,
                         tp_sl_data, blacklist, recovery)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"\n✅ 報告已生成: {output_path}")
    print(f"📏 文件大小: {os.path.getsize(output_path):,} bytes")


if __name__ == '__main__':
    main()
