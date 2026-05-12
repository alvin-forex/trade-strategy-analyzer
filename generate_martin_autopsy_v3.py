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
    Soft SL = Avg MAE × 1.2
    Hard SL = Pair Max MAE × 1.3
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
        soft_sl = stats['avg_mae'] * 1.2
        hard_sl = ccy_dir_max_mae[(stats['symbol'], stats['direction'])] * 1.3
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
        })
    
    # 按恢復次數升序
    results.sort(key=lambda x: x['recovery_trades'])
    return results


# ─── HTML 生成 ───────────────────────────────────────────────

def generate_html(signal_id: str, trades: List[dict], layer_stats: Dict,
                  ccy_summary: List[dict], tp_sl_data: List[dict],
                  blacklist: List[dict], recovery: List[dict]) -> str:
    """生成完整 HTML 報告"""
    
    total_trades = len(trades)
    total_pnl = sum(t['net_profit'] for t in trades)
    total_wins = sum(1 for t in trades if t['net_profit'] > 0)
    wr = total_wins / total_trades * 100 if total_trades else 0
    avg_hold = sum(t['holding_hours'] for t in trades) / total_trades if total_trades else 0
    
    rating_order = {'S+': 6, 'S': 5, 'A': 4, 'B': 3, 'C': 2, 'D': 1, 'E': 0}
    
    # 評級顏色
    def rating_color(r):
        return {'S+': '#FFD700', 'S': '#2ecc71', 'A': '#3498db', 'B': '#9b59b6',
                'C': '#f39c12', 'D': '#e67e22', 'E': '#e74c3c'}.get(r, '#999')
    
    def rating_bg(r):
        return {'S+': '#FFF8E1', 'S': '#E8F5E9', 'A': '#E3F2FD', 'B': '#F3E5F5',
                'C': '#FFF3E0', 'D': '#FBE9E7', 'E': '#FFEBEE'}.get(r, '#F5F5F5')
    
    def pnl_color(val):
        return '#2ecc71' if val > 0 else '#e74c3c' if val < 0 else '#999'
    
    def pnl_prefix(val):
        return '+' if val > 0 else ''
    
    # ─── Part 4 排行榜（從 tp_sl_data 已排序）───
    ranking = tp_sl_data
    
    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>馬丁剖析法 V3 — Signal #{signal_id}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 12px;
            line-height: 1.5;
            color: #e0e0e0;
            background: #0a0a1a;
            padding: 15px;
        }}
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
            background: #0f0f23;
            border: 1px solid #2a2a4a;
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
        }}
        .section-header .badge {{
            display: inline-block;
            background: #FFD700;
            color: #000;
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 10px;
            margin-left: 8px;
            font-weight: normal;
        }}
        .section-body {{
            padding: 12px;
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
        
        /* TP/SL bar chart */
        .bar-chart {{
            display: flex;
            align-items: center;
            gap: 4px;
            margin: 3px 0;
        }}
        .bar {{
            height: 16px;
            border-radius: 3px;
            min-width: 2px;
            position: relative;
            font-size: 9px;
            color: #fff;
            display: flex;
            align-items: center;
            padding: 0 4px;
        }}
        .bar.tp {{ background: #2ecc71; }}
        .bar.soft_sl {{ background: #f39c12; }}
        .bar.hard_sl {{ background: #e74c3c; }}
        
        /* Status indicator */
        .status {{ font-size: 14px; }}
        
        /* Scatter chart (canvas) */
        .scatter-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
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
        canvas.scatter {{ width: 100%; height: 180px; }}
        
        /* Tabs */
        .tabs {{
            display: flex;
            gap: 2px;
            background: #0a0a18;
            border-bottom: 2px solid #2a2a4a;
            padding: 0 12px;
        }}
        .tab {{
            padding: 8px 16px;
            cursor: pointer;
            font-size: 12px;
            color: #888;
            border-bottom: 2px solid transparent;
            transition: all 0.2s;
        }}
        .tab:hover {{ color: #ccc; }}
        .tab.active {{
            color: #FFD700;
            border-bottom-color: #FFD700;
        }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        
        /* Footer */
        .footer {{
            text-align: center;
            padding: 15px;
            color: #555;
            font-size: 10px;
        }}
    </style>
</head>
<body>
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
                <div class="value gold">{len([r for r in ranking])} 層</div>
            </div>
            <div class="kpi-card">
                <div class="label">黑名單</div>
                <div class="value {'red' if blacklist else 'green'}">{len(blacklist)} 個</div>
            </div>
        </div>
    </div>
    
    <!-- Tabs -->
    <div class="tabs">
        <div class="tab active" onclick="switchTab('part1')">Part 1 · CCY總覽</div>
        <div class="tab" onclick="switchTab('part2')">Part 2 · MFE/MAE</div>
        <div class="tab" onclick="switchTab('part3')">Part 3 · TP/SL</div>
        <div class="tab" onclick="switchTab('part4')">Part 4 · 排行榜</div>
        <div class="tab" onclick="switchTab('part5')">Part 5 · 黑名單</div>
        <div class="tab" onclick="switchTab('part6')">Part 6 · 恢復力</div>
    </div>
    
    <!-- Part 1: CCY × Direction 總覽 -->
    <div id="part1" class="tab-content active">
        <div class="section">
            <div class="section-header">
                Part 1 · CCY × Direction 總覽
                <span class="badge">{len(ccy_summary)} 組合</span>
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
        html += f"""                            <tr>
                                <td>{i}</td>
                                <td><b>{s['symbol']}</b></td>
                                <td>{s['direction']}</td>
                                <td>{s['trades']}</td>
                                <td>{s['layers']}</td>
                                <td>{s['max_depth']}</td>
                                <td class="{pnl_cls}"><b>${pnl_prefix(s['total_pnl'])}{s['total_pnl']:,.2f}</b></td>
                                <td>{s['wr']}%</td>
                                <td class="{'positive' if s['avg_ev'] > 0 else 'negative'}">{pnl_prefix(s['avg_ev'])}{s['avg_ev']}</td>
                                <td>{s['avg_win_pips']}</td>
                                <td>{s['avg_loss_pips']}</td>
                                <td>{s['avg_odds_dollar']}</td>
                                <td>{s['avg_odds_pips']}</td>
                                <td>{s['avg_mfe']}</td>
                                <td>{s['avg_mae']}</td>
                                <td><b>{s['max_mae']}</b></td>
                            </tr>
"""
    
    html += """                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
"""
    
    # ─── Part 2: MFE/MAE 散點圖 ───
    html += """    <!-- Part 2: MFE/MAE -->
    <div id="part2" class="tab-content">
        <div class="section">
            <div class="section-header">
                Part 2 · MFE/MAE 散點分析
                <span class="badge">每層一圖 · 綠=Win · 紅=Loss</span>
            </div>
            <div class="section-body">
                <div class="scatter-grid" id="scatter-grid">
"""
    
    # 為每個 CCY×Dir 生成散點圖卡片
    ccy_dir_groups = defaultdict(dict)
    for key, stats in layer_stats.items():
        ccy_key = (stats['symbol'], stats['direction'])
        ccy_dir_groups[ccy_key][key] = stats
    
    chart_idx = 0
    for (symbol, direction), layers in sorted(ccy_dir_groups.items()):
        html += f"""                    <div class="scatter-card">
                        <div class="title"><b>{symbol} {direction}</b> ({len(layers)} layers)</div>
                        <div class="stats-row">
"""
        # 顯示每層摘要
        for lkey, lstats in sorted(layers.items(), key=lambda x: x[1]['lots']):
            html += f"                            L{lstats['lots']} (n={lstats['count']}) WR:{lstats['wr']}% MFE:{lstats['avg_mfe']} MAE:{lstats['avg_mae']} MaxMAE:{lstats['max_mae']}<br>\n"
        
        html += f"""                        </div>
                        <canvas id="chart_{chart_idx}" class="scatter" width="280" height="180"></canvas>
                    </div>
"""
        chart_idx += 1
    
    html += """                </div>
            </div>
        </div>
    </div>
"""
    
    # ─── Part 3: TP/SL ───
    html += f"""    <!-- Part 3: TP/SL -->
    <div id="part3" class="tab-content">
        <div class="section">
            <div class="section-header">
                Part 3 · A 級以上 TP/SL 建議（混合方案）
                <span class="badge">{len(tp_sl_data)} 層</span>
            </div>
            <div class="section-body">
                <div style="font-size:10px; color:#888; margin-bottom:10px;">
                    TP = Avg MFE &nbsp;|&nbsp; Soft SL = Avg MAE × 1.2 &nbsp;|&nbsp; Hard SL = Pair Max MAE × 1.3 &nbsp;|&nbsp; R:R = TP / Soft SL（≥1.5x 可接受，≥3.0x 優秀）
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
    
    html += """                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
"""
    
    # ─── Part 4: 排行榜 ───
    html += f"""    <!-- Part 4: Ranking -->
    <div id="part4" class="tab-content">
        <div class="section">
            <div class="section-header">
                Part 4 · A 級以上排行榜
                <span class="badge">{len(ranking)} 層</span>
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
    <div id="part5" class="tab-content">
        <div class="section">
            <div class="section-header">
                Part 5 · 黑名單
                <span class="badge">{len(blacklist)} 個危險組合</span>
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
                            </tr>
                        </thead>
                        <tbody>
"""
        for b in blacklist:
            html += f"""                            <tr>
                                <td class="status">{b['level']}</td>
                                <td><b>{b['danger']}</b></td>
                                <td><b>{b['symbol']}</b></td>
                                <td>{b['direction']}</td>
                                <td class="negative">{b['total_pnl']:.2f}</td>
                                <td>{b['wr']}%</td>
                                <td>{b['avg_odds']}</td>
                                <td class="negative">{b['avg_ev']}</td>
                                <td class="negative">{b['worst_ev']}</td>
                                <td>{b['worst_layer']}</td>
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
    <div id="part6" class="tab-content">
        <div class="section">
            <div class="section-header">
                Part 6 · 恢復力分析
                <span class="badge">如果最深層被 Hard SL 止損，要用最佳 EV 層贏幾多次先追得返？</span>
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
                                <th>說明</th>
                            </tr>
                        </thead>
                        <tbody>
"""
    
    for r in recovery:
        html += f"""                            <tr>
                                <td class="status">{r['status']}</td>
                                <td><b>{r['symbol']}</b></td>
                                <td>{r['direction']}</td>
                                <td>{r['deepest_layer']}</td>
                                <td class="negative">${r['worst_loss']:.2f}</td>
                                <td>{r['best_ev_layer']}</td>
                                <td class="{'positive' if r['best_ev'] > 0 else 'negative'}">{pnl_prefix(r['best_ev'])}{r['best_ev']}</td>
                                <td><b>{r['recovery_trades'] if r['recovery_trades'] < 999 else '∞'}</b></td>
                                <td>{r['recovery_days'] if r['recovery_days'] < 999 else '∞'}天</td>
                                <td>{r['status_text']}</td>
                            </tr>
"""
    
    html += """                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
"""
    
    # ─── JavaScript: Tab switching + Scatter charts ───
    # 收集散點圖數據
    scatter_data = {}
    chart_idx = 0
    for (symbol, direction), layers in sorted(ccy_dir_groups.items()):
        chart_scatter = []
        for lkey, lstats in sorted(layers.items(), key=lambda x: x[1]['lots']):
            for td in lstats['trade_details']:
                chart_scatter.append({
                    'net_pips': td['net_pips'],
                    'mae': td['mae'],
                    'mfe': td['mfe'],
                    'is_win': td['is_win'],
                    'layer': lstats['layer_label'],
                })
        scatter_data[str(chart_idx)] = chart_scatter
        chart_idx += 1
    
    scatter_json = json.dumps(scatter_data)
    
    html += f"""
    <div class="footer">
        馬丁剖析法 V3 · 數據說話，紀律至上 · Quant 📊
    </div>
</div>

<script>
// Tab switching
function switchTab(tabId) {{
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    event.target.classList.add('active');
}}

// Scatter charts
const scatterData = {scatter_json};

function drawScatter(canvasId, data) {{
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const w = canvas.width = canvas.offsetWidth * 2;
    const h = canvas.height = canvas.offsetHeight * 2;
    ctx.scale(2, 2);
    const cw = canvas.offsetWidth;
    const ch = canvas.offsetHeight;
    
    // Clear
    ctx.fillStyle = '#0a0a18';
    ctx.fillRect(0, 0, cw, ch);
    
    // Compute bounds
    let allVals = data.map(d => Math.abs(d.net_pips)).concat(data.map(d => d.mae)).concat(data.map(d => d.mfe));
    let maxVal = Math.max(...allVals, 1);
    
    const pad = {{ top: 10, right: 10, bottom: 20, left: 35 }};
    const plotW = cw - pad.left - pad.right;
    const plotH = ch - pad.top - pad.bottom;
    
    // Grid
    ctx.strokeStyle = '#1a1a2a';
    ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {{
        let y = pad.top + plotH * i / 4;
        ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(pad.left + plotW, y); ctx.stroke();
        let val = Math.round(maxVal * (1 - i/4));
        ctx.fillStyle = '#555';
        ctx.font = '8px sans-serif';
        ctx.fillText(val, 2, y + 3);
    }}
    
    // Zero line
    let zeroY = pad.top + plotH * 0.5;
    ctx.strokeStyle = '#333';
    ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(pad.left, zeroY); ctx.lineTo(pad.left + plotW, zeroY); ctx.stroke();
    
    // Dots
    for (const d of data) {{
        let x = pad.left + (d.mae / maxVal) * plotW;
        let y_pos = d.is_win ? (pad.top + plotH * (1 - d.mfe / maxVal)) : (pad.top + plotH * (1 - d.net_pips / maxVal));
        y_pos = Math.max(pad.top, Math.min(pad.top + plotH, y_pos));
        x = Math.max(pad.left, Math.min(pad.left + plotW, x));
        
        ctx.beginPath();
        ctx.arc(x, y_pos, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = d.is_win ? '#2ecc71' : '#e74c3c';
        ctx.fill();
    }}
}}

// Draw all charts
for (const [id, data] of Object.entries(scatterData)) {{
    drawScatter('chart_' + id, data);
}}

// Redraw on resize
window.addEventListener('resize', () => {{
    for (const [id, data] of Object.entries(scatterData)) {{
        drawScatter('chart_' + id, data);
    }}
}});
</script>
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
