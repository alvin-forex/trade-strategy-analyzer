#!/usr/bin/env python3
"""
Statistics - 統計計算
整體、貨幣對、層數、時段、方向統計
"""

from typing import Dict, List, Any
import numpy as np
from scipy import stats
from collections import defaultdict


def calculate_overall_stats(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    計算整體統計

    Args:
        positions: 倉位列表

    Returns:
        Dict: 整體統計
    """
    if not positions:
        return {}

    # 基本統計
    total_positions = len(positions)
    total_trades = sum(len(p.get('trades', [])) for p in positions)

    # 盈虧
    net_profits = [p['net_profit'] for p in positions]
    total_profit = sum(net_profits)
    avg_profit = np.mean(net_profits)

    # 勝率
    wins = [p for p in positions if p['net_profit'] > 0]
    losses = [p for p in positions if p['net_profit'] <= 0]
    win_rate = len(wins) / total_positions * 100 if total_positions > 0 else 0

    # 平均盈利和平均虧損
    avg_win = np.mean([p['net_profit'] for p in wins]) if wins else 0
    avg_loss = np.mean([p['net_profit'] for p in losses]) if losses else 0

    # 賠率
    avg_win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0

    # Profit Factor
    total_gross_profit = sum([p['net_profit'] for p in wins])
    total_gross_loss = abs(sum([p['net_profit'] for p in losses]))
    profit_factor = total_gross_profit / total_gross_loss if total_gross_loss > 0 else float('inf')

    # 最大回撤
    max_dd, max_dd_percent = calculate_max_drawdown(net_profits)

    # 平均層數和持倉時間
    avg_layers = np.mean([p['max_layer'] for p in positions])
    avg_holding_time = np.mean([p['holding_time_hours'] for p in positions])

    # Swap 和 Commission
    total_swap = sum([p['total_swap'] for p in positions])
    total_commission = sum([p['total_commission'] for p in positions])

    # Trading period
    try:
        total_period_days = (positions[-1]['close_time'] - positions[0]['open_time']).total_seconds() / 86400
    except:
        total_period_days = 1
    trading_days = max(total_period_days, 1)

    # Sharpe Ratio (年化)
    annual_factor = (252 / trading_days) ** 0.5
    sharpe_ratio = calculate_sharpe_ratio(net_profits, annual_factor=annual_factor)
    
    # Calmar Ratio (年化)
    annual_return = total_profit * (252 / trading_days)
    calmar_ratio = annual_return / abs(max_dd) if max_dd != 0 else float('inf')
    
    sortino_ratio = calculate_sortino_ratio(net_profits)

    # 盈虧偏度
    skewness = stats.skew(net_profits) if len(net_profits) > 2 else 0

    # CVaR (Conditional Value at Risk) at 95%
    cvar_95 = calculate_cvar(net_profits, 0.95)

    # Gain-to-Pain Ratio
    gain_pain_ratio = calculate_gain_pain_ratio(net_profits)

    # Exposure Time %
    try:
        total_period_days = (positions[-1]['close_time'] - positions[0]['open_time']).total_seconds() / 86400
        # Calculate overlapping exposure
        total_holding_hours = sum([p['holding_time_hours'] for p in positions])
        exposure_time_percent = min((total_holding_hours / (total_period_days * 24)) * 100, 100.0) if total_period_days > 0 else 0
    except:
        total_period_days = 1
        exposure_time_percent = 0

    # 連續虧損分析
    max_consecutive_losses, max_consecutive_loss_amount = analyze_consecutive_losses(positions)

    # 回撤恢復時間
    recovery_time = calculate_drawdown_recovery(net_profits)

    # 盈虧中位數 vs 平均數
    median_profit = np.median(net_profits)
    mean_profit = np.mean(net_profits)

    return {
        'total_positions': total_positions,
        'total_trades': total_trades,
        'win_rate': round(win_rate, 2),
        'avg_win': round(avg_win, 2),
        'avg_loss': round(avg_loss, 2),
        'avg_win_loss_ratio': round(avg_win_loss_ratio, 2),
        'profit_factor': round(profit_factor, 2),
        'total_profit': round(total_profit, 2),
        'avg_profit': round(avg_profit, 2),
        'max_dd': round(max_dd, 2),
        'max_dd_percent': round(max_dd_percent, 2),
        'avg_layers': round(avg_layers, 2),
        'avg_holding_time_hours': round(avg_holding_time, 2),
        'total_swap': round(total_swap, 2),
        'total_commission': round(total_commission, 2),
        'sharpe_ratio': round(sharpe_ratio, 2),
        'calmar_ratio': round(calmar_ratio, 2),
        'sortino_ratio': round(sortino_ratio, 2),
        'skewness': round(skewness, 2),
        'cvar_95': round(cvar_95, 2),
        'gain_pain_ratio': round(gain_pain_ratio, 2),
        'exposure_time_percent': round(exposure_time_percent, 2),
        'max_consecutive_losses': max_consecutive_losses,
        'max_consecutive_loss_amount': round(max_consecutive_loss_amount, 2),
        'recovery_time_days': round(recovery_time, 2),
        'median_profit': round(median_profit, 2),
        'mean_profit': round(mean_profit, 2)
    }


def calculate_symbol_stats(positions: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    計算按貨幣對統計

    Args:
        positions: 倉位列表

    Returns:
        Dict: 貨幣對統計
    """
    symbol_stats = defaultdict(list)

    # 按貨幣對分組
    for position in positions:
        symbol_stats[position['symbol']].append(position)

    # 計算每個貨幣對的統計
    results = {}
    for symbol, symbol_positions in symbol_stats.items():
        stats_data = calculate_overall_stats(symbol_positions)
        stats_data['count'] = len(symbol_positions)
        results[symbol] = stats_data

    return results


def calculate_layer_stats(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    計算按層數統計

    Args:
        positions: 倉位列表

    Returns:
        Dict: 層數統計
    """
    total = len(positions)

    # 分類
    l1_only = [p for p in positions if p['max_layer'] == 1]
    l1_l2 = [p for p in positions if p['max_layer'] == 2]
    l1_l3 = [p for p in positions if p['max_layer'] == 3]
    l4_plus = [p for p in positions if p['max_layer'] >= 4]

    def calc_stats(pos_list, name):
        if not pos_list:
            return {
                'name': name,
                'count': 0,
                'percentage': 0,
                'avg_profit': 0,
                'win_rate': 0
            }
        return {
            'name': name,
            'count': len(pos_list),
            'percentage': round(len(pos_list) / total * 100, 2),
            'avg_profit': round(np.mean([p['net_profit'] for p in pos_list]), 2),
            'win_rate': round(len([p for p in pos_list if p['net_profit'] > 0]) / len(pos_list) * 100, 2)
        }

    return {
        'L1 only': calc_stats(l1_only, 'L1 only'),
        'L1-L2': calc_stats(l1_l2, 'L1-L2'),
        'L1-L3': calc_stats(l1_l3, 'L1-L3'),
        'L4+': calc_stats(l4_plus, 'L4+'),
        'martin_health': {
            'l1_only_ratio': round(len(l1_only) / total * 100, 2) if total > 0 else 0,
            'l4_plus_ratio': round(len(l4_plus) / total * 100, 2) if total > 0 else 0
        }
    }


def calculate_time_stats(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    計算按時段統計
    亞洲盤(00-08 HKT) / 歐洲盤(14-22 HKT) / 美洲盤(21-05 HKT)

    Args:
        positions: 倉位列表

    Returns:
        Dict: 時段統計
    """
    def get_session(hour):
        if 0 <= hour < 8:
            return 'Asia'
        elif 14 <= hour < 22:
            return 'Europe'
        elif hour >= 21 or hour < 5:
            return 'America'
        else:
            return 'Other'

    session_stats = defaultdict(list)

    for position in positions:
        hour = position['open_time'].hour
        session = get_session(hour)
        session_stats[session].append(position)

    def calc_session_stats(session_positions):
        if not session_positions:
            return {
                'count': 0,
                'avg_profit': 0,
                'win_rate': 0
            }
        return {
            'count': len(session_positions),
            'avg_profit': round(np.mean([p['net_profit'] for p in session_positions]), 2),
            'win_rate': round(len([p for p in session_positions if p['net_profit'] > 0]) / len(session_positions) * 100, 2)
        }

    return {
        'Asia': calc_session_stats(session_stats.get('Asia', [])),
        'Europe': calc_session_stats(session_stats.get('Europe', [])),
        'America': calc_session_stats(session_stats.get('America', [])),
        'Other': calc_session_stats(session_stats.get('Other', []))
    }


def calculate_direction_stats(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    計算按方向統計

    Args:
        positions: 倉位列表

    Returns:
        Dict: 方向統計
    """
    buy_positions = [p for p in positions if p['direction'] == 'BUY']
    sell_positions = [p for p in positions if p['direction'] == 'SELL']

    def calc_dir_stats(dir_positions):
        if not dir_positions:
            return {
                'count': 0,
                'avg_profit': 0,
                'win_rate': 0
            }
        return {
            'count': len(dir_positions),
            'avg_profit': round(np.mean([p['net_profit'] for p in dir_positions]), 2),
            'win_rate': round(len([p for p in dir_positions if p['net_profit'] > 0]) / len(dir_positions) * 100, 2)
        }

    return {
        'BUY': calc_dir_stats(buy_positions),
        'SELL': calc_dir_stats(sell_positions)
    }


def calculate_max_drawdown(profits: List[float]) -> tuple:
    """
    計算最大回撤

    Args:
        profits: 盈虧列表

    Returns:
        tuple: (最大回撤, 最大回撤百分比)
    """
    if not profits:
        return 0, 0

    cumulative = np.cumsum(profits)
    peak = np.maximum.accumulate(cumulative)
    drawdown = cumulative - peak
    max_dd = np.min(drawdown)
    max_dd_percent = (max_dd / np.max(peak)) * 100 if np.max(peak) > 0 else 0

    return max_dd, max_dd_percent


def calculate_sharpe_ratio(profits: List[float], risk_free_rate: float = 0.0, annual_factor: float = 1.0) -> float:
    """
    計算 Sharpe Ratio

    Args:
        profits: 盈虧列表
        risk_free_rate: 無風險利率（每筆交易）
        annual_factor: 年化調整系數

    Returns:
        float: Sharpe Ratio
    """
    if len(profits) < 2:
        return 0

    excess_returns = np.array(profits) - risk_free_rate
    if np.std(excess_returns) == 0:
        return 0

    return (np.mean(excess_returns) / np.std(excess_returns)) * annual_factor


def calculate_sortino_ratio(profits: List[float], risk_free_rate: float = 0.02) -> float:
    """
    計算 Sortino Ratio

    Args:
        profits: 盈虧列表
        risk_free_rate: 無風險利率

    Returns:
        float: Sortino Ratio
    """
    if len(profits) < 2:
        return 0

    excess_returns = np.array(profits) - risk_free_rate
    downside_returns = excess_returns[excess_returns < 0]

    if len(downside_returns) == 0:
        return float('inf')

    downside_std = np.std(downside_returns)
    if downside_std == 0:
        return float('inf')

    return np.mean(excess_returns) / downside_std


def calculate_cvar(profits: List[float], confidence: float = 0.95) -> float:
    """
    計算 CVaR (Conditional Value at Risk)

    Args:
        profits: 盈虧列表
        confidence: 置信水平

    Returns:
        float: CVaR
    """
    if not profits:
        return 0

    sorted_profits = np.array(sorted(profits))
    index = int((1 - confidence) * len(sorted_profits))
    var = sorted_profits[index] if index < len(sorted_profits) else sorted_profits[-1]

    # CVaR 是低於 VaR 的平均值
    tail_losses = sorted_profits[:index+1]
    cvar = np.mean(tail_losses)

    return cvar


def calculate_gain_pain_ratio(profits: List[float]) -> float:
    """
    計算 Gain-to-Pain Ratio

    Args:
        profits: 盈虧列表

    Returns:
        float: Gain-to-Pain Ratio
    """
    gains = sum([p for p in profits if p > 0])
    losses = abs(sum([p for p in profits if p < 0]))

    if losses == 0:
        return float('inf')

    return gains / losses


def analyze_consecutive_losses(positions: List[Dict[str, Any]]) -> tuple:
    """
    分析連續虧損

    Args:
        positions: 倉位列表

    Returns:
        tuple: (最大連續虧損倉位數, 最大連續虧損金額)
    """
    if not positions:
        return 0, 0

    max_consecutive = 0
    max_consecutive_amount = 0
    current_consecutive = 0
    current_amount = 0

    for position in positions:
        if position['net_profit'] <= 0:
            current_consecutive += 1
            current_amount += position['net_profit']
        else:
            if current_consecutive > max_consecutive:
                max_consecutive = current_consecutive
                max_consecutive_amount = current_amount
            current_consecutive = 0
            current_amount = 0

    # 檢查最後一段
    if current_consecutive > max_consecutive:
        max_consecutive = current_consecutive
        max_consecutive_amount = current_amount

    return max_consecutive, abs(max_consecutive_amount)


def calculate_drawdown_recovery(profits: List[float]) -> float:
    """
    計算回撤恢復時間（天）

    Args:
        profits: 盈虧列表

    Returns:
        float: 恢復時間
    """
    if not profits:
        return 0

    cumulative = np.cumsum(profits)
    peak = np.maximum.accumulate(cumulative)
    drawdown = cumulative - peak

    # 找到最大回撤點
    max_dd_idx = np.argmin(drawdown)
    max_dd_peak_idx = np.argmax(cumulative[:max_dd_idx+1])

    # 找到恢復到新高的點
    for i in range(max_dd_idx + 1, len(cumulative)):
        if cumulative[i] >= peak[max_dd_idx]:
            return i - max_dd_idx

    # 如果沒有恢復，返回 0
    return 0
