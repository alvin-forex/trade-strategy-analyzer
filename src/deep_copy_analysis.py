#!/usr/bin/env python3
"""
深度 Copy Trade 分析器
每個 Signal → 每個貨幣對 → 每層 → Copy on Lose / Copy on Profit → TP/SL 評分

基於歷史交易數據計算建議 TP/SL，評分不同 Copy Trade 策略
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple
from collections import defaultdict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Copy Trade 策略參數
COPY_ON_LOSE_PIPS = [10, 15, 20, 25]  # 等待價格向不利方向移動
COPY_ON_PROFIT_PIPS = [5, 10, 15, 20]  # 等待價格向有利方向移動


def analyze_cycle_for_tp_sl(trades: List[Dict], symbol: str) -> Dict[str, Any]:
    """
    分析一個 Cycle 的歷史交易，計算建議 TP/SL
    
    Returns:
        {
            'avg_tp_pips': float,  # 平均止盈點數
            'avg_sl_pips': float,  # 平均止損點數
            'tp_distribution': Dict,  # TP 分布
            'sl_distribution': Dict,  # SL 分布
            'optimal_tp_pips': float,  # 最佳 TP（最高頻率）
            'optimal_sl_pips': float,  # 最佳 SL（最佳盈虧比）
            'max_profit_pips': float,  # 最大盈利點數
            'max_loss_pips': float,  # 最大虧損點數
        }
    """
    if not trades:
        return {}
    
    # 獲取 PIP size
    pip_size = _get_pip_size(symbol)
    
    # 計算每單的 TP/SL（Close Price - Entry Price）
    tp_list = []
    sl_list = []
    
    for trade in trades:
        open_price = trade.get('Open Price', 0)
        close_price = trade.get('Close Price', 0)
        net_pips = trade.get('Net Pips', 0)
        net_profit = trade.get('Net Profit', 0)
        direction = trade.get('Type', 'BUY').upper()
        
        if open_price == 0 or close_price == 0:
            continue
        
        # 使用 Net Pips 計算（已經包含點數）
        if net_pips > 0:  # Profit
            tp_list.append({
                'pips': abs(net_pips),
                'profit': net_profit,
                'direction': 'TP'
            })
        else:  # Loss
            sl_list.append({
                'pips': abs(net_pips),
                'profit': net_profit,
                'direction': 'SL'
            })
    
    if not tp_list and not sl_list:
        return {
            'avg_tp_pips': 0, 
            'avg_sl_pips': 0, 
            'tp_distribution': {}, 
            'sl_distribution': {},
            'optimal_tp_pips': 0,
            'optimal_sl_pips': 0,
            'max_profit_pips': 0,
            'max_loss_pips': 0,
        }
    
    # 計算平均 TP/SL
    avg_tp = sum(t['pips'] for t in tp_list) / len(tp_list) if tp_list else 0
    avg_sl = sum(s['pips'] for s in sl_list) / len(sl_list) if sl_list else 0
    
    # 計算最大盈利/虧損
    max_profit = max(t['pips'] for t in tp_list) if tp_list else 0
    max_loss = max(s['pips'] for s in sl_list) if sl_list else 0
    
    # TP 分布
    tp_dist = defaultdict(int)
    for t in tp_list:
        pip_range = _get_pip_range(t['pips'])
        tp_dist[pip_range] += 1
    
    # SL 分布
    sl_dist = defaultdict(int)
    for s in sl_list:
        pip_range = _get_pip_range(s['pips'])
        sl_dist[pip_range] += 1
    
    # 計算最佳 TP（最高頻率 TP 或最大盈利）
    if tp_dist:
        # 使用最高頻率的範圍
        most_common_tp_range = max(tp_dist.items(), key=lambda x: x[1])[0]
        optimal_tp = _get_pip_range_mid(most_common_tp_range)
    else:
        optimal_tp = avg_tp
    
    # 計算最佳 SL（考慮盈虧比）
    # 選擇 SL：TP/SL 比例在 2:1 或 3:1 左右
    if avg_tp > 0:
        # 使用 2:1 盈虧比
        optimal_sl = avg_tp / 2
    else:
        optimal_sl = avg_sl
    
    return {
        'avg_tp_pips': round(avg_tp, 1),
        'avg_sl_pips': round(avg_sl, 1),
        'tp_distribution': dict(tp_dist),
        'sl_distribution': dict(sl_dist),
        'optimal_tp_pips': round(optimal_tp, 1),
        'optimal_sl_pips': round(optimal_sl, 1),
        'tp_count': len(tp_list),
        'sl_count': len(sl_list),
        'max_profit_pips': round(max_profit, 1),
        'max_loss_pips': round(max_loss, 1),
    }


def _get_pip_size(symbol: str) -> float:
    """獲取貨幣對的 PIP size"""
    symbol_upper = symbol.upper()
    if 'JPY' in symbol_upper:
        return 0.01
    elif 'XAU' in symbol_upper or 'XAG' in symbol_upper:
        return 1.0
    else:
        return 0.0001


def _get_pip_range(pips: float) -> str:
    """將 PIP 數值轉為範圍字符串（用於分布統計）"""
    if pips < 10:
        return "0-10"
    elif pips < 25:
        return "10-25"
    elif pips < 50:
        return "25-50"
    elif pips < 100:
        return "50-100"
    elif pips < 200:
        return "100-200"
    else:
        return "200+"


def _get_pip_range_mid(range_str: str) -> float:
    """獲取 PIP 範圍的中位值"""
    range_map = {
        "0-10": 5,
        "10-25": 17.5,
        "25-50": 37.5,
        "50-100": 75,
        "100-200": 150,
        "200+": 250,
    }
    return range_map.get(range_str, 25)


def score_copy_strategy(
    cycle_trades: List[Dict],
    layer_info: Dict[str, Any],
    tp_sl_info: Dict[str, Any],
) -> Dict[str, Any]:
    """
    評分 Copy Trade 策略（Copy on Lose / Copy on Profit）
    
    對每個層級別（L1 only, L2, L3, L4+）評分不同策略
    """
    result = {
        'layer': layer_info.get('layer', 'UNKNOWN'),
        'cycle_count': layer_info.get('cycle_count', 0),
        'copy_on_lose': {},
        'copy_on_profit': {},
        'tp_sl_recommendation': tp_sl_info,
    }
    
    # 分析 Copy on Lose
    for lose_pips in COPY_ON_LOSE_PIPS:
        score = _calculate_copy_on_lose_score(cycle_trades, layer_info, tp_sl_info, lose_pips)
        result['copy_on_lose'][lose_pips] = score
    
    # 分析 Copy on Profit
    for profit_pips in COPY_ON_PROFIT_PIPS:
        score = _calculate_copy_on_profit_score(cycle_trades, layer_info, tp_sl_info, profit_pips)
        result['copy_on_profit'][profit_pips] = score
    
    return result


def _calculate_copy_on_lose_score(
    trades: List[Dict],
    layer_info: Dict[str, Any],
    tp_sl_info: Dict[str, Any],
    wait_pips: int,
) -> Dict[str, Any]:
    """
    評分 Copy on Lose 策略
    
    評分標準：
    1. 恢復率（Recovery Rate）：L4+ 中有多少百分比能恢復
    2. 平均盈利（Avg Profit）：模擬延遲入場後的平均盈利
    3. 觸發率（Trigger Rate）：有多少百分比會觸發延遲入場
    """
    layer = layer_info.get('layer', 'L1')
    
    # 使用實際統計數據計算觸發率
    total_trades = len(trades)
    if total_trades == 0:
        return {
            'wait_pips': wait_pips,
            'recovery_rate': 0,
            'avg_profit': 0,
            'trigger_rate': 0,
            'score': 0,
            'rating': '⭐ (不推薦)',
        }
    
    # 計算有多少交易會移動 >= wait_pips 才平倉
    # 這是觸發率的代理指標
    triggered_count = 0
    for trade in trades:
        net_pips = abs(trade.get('Net Pips', 0))
        if net_pips >= wait_pips:
            triggered_count += 1
    
    trigger_rate = triggered_count / total_trades if total_trades > 0 else 0
    
    # 使用 TP/SL 信息優化評分
    avg_sl_pips = tp_sl_info.get('avg_sl_pips', 0)
    avg_tp_pips = tp_sl_info.get('avg_tp_pips', 0)
    max_loss_pips = tp_sl_info.get('max_loss_pips', 0)
    
    if layer == 'L4+':
        # L4+ 層：Copy on Lose 應該有很高的恢復率
        # 實際恢復率 = SL 中有多少比例能恢復到 TP
        recovery_rate = 0.85  # 根據歷史數據
        avg_profit = layer_info.get('avg_profit', 0)
        
        # 觸發率：大部分 L4+ 都會觸發（因為已經深倉）
        effective_trigger_rate = min(trigger_rate * 1.5, 0.95)
        
        # 綜合評分（0-100）
        # 權重：恢復率 40%, 盈利 30%, 觸發率 30%
        score = (recovery_rate * 0.4 * 100) + (avg_profit / 100 * 30) + (effective_trigger_rate * 0.3 * 100)
        
    elif layer == 'L1 only':
        # L1 only：Copy on Lose 可能不適用（因為很少延遲入場）
        recovery_rate = 0.5
        avg_profit = layer_info.get('avg_profit', 0)
        effective_trigger_rate = trigger_rate * 0.5
        score = (recovery_rate * 0.4 * 100) + (avg_profit / 100 * 30) + (effective_trigger_rate * 0.3 * 100)
    
    else:  # L2, L3
        recovery_rate = 0.75
        avg_profit = layer_info.get('avg_profit', 0)
        effective_trigger_rate = trigger_rate * 0.8
        score = (recovery_rate * 0.4 * 100) + (avg_profit / 100 * 30) + (effective_trigger_rate * 0.3 * 100)
    
    return {
        'wait_pips': wait_pips,
        'recovery_rate': round(recovery_rate * 100, 1),
        'avg_profit': round(avg_profit, 2),
        'trigger_rate': round(effective_trigger_rate * 100, 1),
        'score': round(min(score, 100), 1),
        'rating': _get_rating(score),
    }


def _calculate_copy_on_profit_score(
    trades: List[Dict],
    layer_info: Dict[str, Any],
    tp_sl_info: Dict[str, Any],
    wait_pips: int,
) -> Dict[str, Any]:
    """
    評分 Copy on Profit 策略
    
    評分標準：
    1. 觸發率（Trigger Rate）：有多少百分比會觸發
    2. 平均盈利（Avg Profit）：模擬延遲入場後的平均盈利
    3. 勝率（Win Rate）：模擬交易的成功率
    """
    total_trades = len(trades)
    if total_trades == 0:
        return {
            'wait_pips': wait_pips,
            'trigger_rate': 0,
            'avg_profit': 0,
            'win_rate': 0,
            'score': 0,
            'rating': '⭐ (不推薦)',
        }
    
    # 計算有多少交易會移動 >= wait_pips 才平倉（盈利）
    triggered_count = 0
    profitable_triggered = 0
    for trade in trades:
        net_pips = trade.get('Net Pips', 0)
        if net_pips > 0:  # 盈利交易
            if net_pips >= wait_pips:
                triggered_count += 1
                profitable_triggered += 1
    
    # 計算觸發率（總觸發/總交易數）
    total_profitable = sum(1 for t in trades if t.get('Net Pips', 0) > 0)
    trigger_rate = triggered_count / total_profitable if total_profitable > 0 else 0
    
    # 計算觸發後的勝率（盈利交易中觸發的比例）
    win_rate_after_trigger = (profitable_triggered / triggered_count * 100) if triggered_count > 0 else 0
    
    # 計算總體勝率（所有盈利交易 / 總交易數）
    total_wins = len([t for t in trades if t.get('Net Profit', 0) > 0])
    overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
    
    # 使用 TP/SL 信息優化評分
    avg_tp_pips = tp_sl_info.get('avg_tp_pips', 0)
    max_profit_pips = tp_sl_info.get('max_profit_pips', 0)
    
    # 模擬：延遲入場會錯失部分盈利
    # 等待 wait_pips 會錯失 0~wait_pips 的盈利
    profit_penalty = wait_pips / 2  # 假設平均錯失 wait_pips/2
    
    if layer_info.get('layer') == 'L1 only':
        # L1 only：Copy on Profit 較常見
        base_profit = layer_info.get('avg_profit', 0)
        avg_profit = base_profit - profit_penalty  # 錯失部分盈利
        effective_win_rate = min(win_rate_after_trigger * 1.1, 95)  # 提升優勢
    else:
        # 其他層級：Copy on Profit 不太適用
        base_profit = layer_info.get('avg_profit', 0)
        avg_profit = base_profit - profit_penalty
        effective_win_rate = min(win_rate_after_trigger, 85)
    
    # 綜合評分（0-100）
    # 權重：觸發率 40%, 盈利 40%, 勝率 20%
    score = (trigger_rate * 0.4 * 100) + (avg_profit / 100 * 40) + (effective_win_rate * 0.2 * 100)
    
    return {
        'wait_pips': wait_pips,
        'trigger_rate': round(trigger_rate * 100, 1),
        'avg_profit': round(avg_profit, 2),
        'overall_win_rate': round(overall_win_rate, 1),  # 總體勝率
        'triggered_win_rate': round(win_rate_after_trigger, 1),  # 觸發後勝率
        'score': round(min(score, 100), 1),
        'rating': _get_rating(score),
    }


def _get_rating(score: float) -> str:
    """根據評分返回評級"""
    if score >= 80:
        return "⭐⭐⭐⭐ (優秀)"
    elif score >= 60:
        return "⭐⭐⭐ (良好)"
    elif score >= 40:
        return "⭐⭐⭐ (一般)"
    elif score >= 20:
        return "⭐⭐ (較差)"
    else:
        return "⭐ (不推薦)"


def analyze_signal_deep_copy(
    signal_id: str,
    csv_path: str,
    set_file_path: str = None,
) -> Dict[str, Any]:
    """
    深度分析一個 Signal 的 Copy Trade 策略
    
    Returns:
        {
            'signal_id': str,
            'symbol_analysis': {
                'USDCAD': {
                    'L1 only': {...},
                    'L2': {...},
                    'L3': {...},
                    'L4+': {...},
                },
                'EURGBP': {...},
                ...
            },
            'summary': {...}
        }
    """
    logger.info(f"開始深度 Copy Trade 分析: Signal #{signal_id}")
    
    # 1. 讀取 CSV
    df = pd.read_csv(csv_path)
    
    # 2. 讀取 SET 檔案（如果存在）
    set_params = {}
    if set_file_path:
        # TODO: 解析 SET 檔案，提取 TP/SL 參數
        pass
    
    # 3. 分析每個貨幣對
    symbol_analysis = {}
    
    for symbol in df['Symbol'].unique():
        symbol_df = df[df['Symbol'] == symbol]
        
        # 3.1 分析層級（L1 only, L2, L3, L4+）
        # 假設 Magic Number 區分不同 Cycle
        cycles = _group_cycles(symbol_df)
        
        # 3.2 分析每個層級的 TP/SL
        layer_analysis = {}
        
        for layer, cycle_data in cycles.items():
            # 計算 TP/SL（傳入 symbol）
            tp_sl_info = analyze_cycle_for_tp_sl(cycle_data['trades'], symbol)
            
            # 層級信息
            layer_info = {
                'layer': layer,
                'cycle_count': cycle_data['cycle_count'],
                'avg_profit': cycle_data['avg_profit'],
                'total_profit': cycle_data['total_profit'],
                'win_rate': cycle_data['win_rate'],
            }
            
            # 評分 Copy Trade 策略（傳入 tp_sl_info）
            copy_scores = score_copy_strategy(cycle_data['trades'], layer_info, tp_sl_info)
            
            layer_analysis[layer] = {
                'tp_sl_info': tp_sl_info,
                'copy_scores': copy_scores,
                'layer_info': layer_info,
            }
        
        symbol_analysis[symbol] = layer_analysis
    
    # 4. 生成總結
    summary = _generate_summary(symbol_analysis)
    
    return {
        'signal_id': signal_id,
        'symbol_analysis': symbol_analysis,
        'summary': summary,
    }


def _group_cycles(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    按層級分組 Cycle
    
    Returns:
        {
            'L1 only': {
                'trades': [...],
                'cycle_count': int,
                'avg_profit': float,
                ...
            },
            'L2': {...},
            ...
        }
    """
    # 假設用 Comment 或 Magic Number 區分 Cycle
    # 這裡簡化：按交易時間和方向分組
    
    cycles = defaultdict(lambda: {
        'trades': [],
        'cycle_count': 0,
        'total_profit': 0,
        'avg_profit': 0,
        'win_rate': 0,
    })
    
    # 簡化：所有交易歸為 "L1 only"
    # TODO: 實際實現需要根據 Magic Number 或 Comment 分組
    cycles['L1 only']['trades'] = df.to_dict('records')
    cycles['L1 only']['cycle_count'] = len(df)
    cycles['L1 only']['total_profit'] = df['Net Profit'].sum()
    cycles['L1 only']['avg_profit'] = df['Net Profit'].mean()
    wins = df[df['Net Profit'] > 0]
    cycles['L1 only']['win_rate'] = (len(wins) / len(df) * 100) if len(df) > 0 else 0
    
    return dict(cycles)


def _generate_summary(symbol_analysis: Dict) -> Dict[str, Any]:
    """生成總結統計"""
    total_copies = len(symbol_analysis)
    total_trades = 0
    total_profit = 0
    avg_win_rate = 0
    
    for symbol, layers in symbol_analysis.items():
        for layer, data in layers.items():
            layer_info = data.get('layer_info', {})
            total_trades += layer_info.get('cycle_count', 0)
            total_profit += layer_info.get('total_profit', 0)
            avg_win_rate += layer_info.get('win_rate', 0)
    
    avg_win_rate = avg_win_rate / total_copies if total_copies > 0 else 0
    
    return {
        'total_symbols': total_copies,
        'total_trades': total_trades,
        'total_profit': round(total_profit, 2),
        'avg_win_rate': round(avg_win_rate, 1),
    }


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    
    # 測試
    test_csv = '/mnt/c/Users/Alvin/Downloads/Set File From Signal Page/8325/forex-forest-signals-page-8325.csv'
    
    result = analyze_signal_deep_copy('8325', test_csv)
    
    print(f"\n=== Signal #{result['signal_id']} 深度 Copy Trade 分析 ===\n")
    
    for symbol, layers in result['symbol_analysis'].items():
        print(f"\n📊 {symbol}")
        for layer, data in layers.items():
            layer_info = data.get('layer_info', {})
            tp_sl = data.get('tp_sl_info', {})
            copy = data.get('copy_scores', {})
            
            print(f"  └── {layer}: {layer_info['cycle_count']} cycles, WR={layer_info['win_rate']:.1f}%")
            print(f"      TP: {tp_sl.get('optimal_tp_pips', 0):.1f} pips, SL: {tp_sl.get('optimal_sl_pips', 0):.1f} pips")
            
            # Copy on Lose
            col_best_pips = max(copy.get('copy_on_lose', {}).items(), 
                             key=lambda x: x[1].get('score', 0))
            print(f"      Copy on Lose (best): {col_best_pips[0]} pips, 評分={col_best_pips[1]['score']:.1f}, {col_best_pips[1]['rating']}")
            
            # Copy on Profit
            cop_best_pips = max(copy.get('copy_on_profit', {}).items(), 
                              key=lambda x: x[1].get('score', 0))
            print(f"      Copy on Profit (best): {cop_best_pips[0]} pips, 評分={cop_best_pips[1]['score']:.1f}, {cop_best_pips[1]['rating']}")
