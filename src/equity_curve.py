#!/usr/bin/env python3
"""
Equity Curve - 淨值曲線計算
"""

from typing import Dict, List, Any
import numpy as np


def calculate_equity_curve(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    計算淨值曲線

    Args:
        positions: 倉位列表（按時間排序）

    Returns:
        Dict: 淨值曲線數據
    """
    if not positions:
        return {
            'dates': [],
            'equity': [],
            'peak': [],
            'drawdown': [],
            'major_drawdowns': []
        }

    # 按平倉時間排序
    sorted_positions = sorted(positions, key=lambda x: x['close_time'])

    # 計算累計盈虧
    dates = [p['close_time'] for p in sorted_positions]
    profits = [p['net_profit'] for p in sorted_positions]

    # 淨值曲線
    equity = np.cumsum(profits).tolist()

    # 最高點曲線
    peak = np.maximum.accumulate(equity).tolist()

    # 回撤曲線
    drawdown = [(e - p) for e, p in zip(equity, peak)]

    # 標記重大回撤（回撤 > 前高點的 5%）
    major_drawdowns = []
    in_drawdown = False
    drawdown_start = None
    drawdown_bottom = None
    drawdown_bottom_equity = None

    for i, (e, p, dd) in enumerate(zip(equity, peak, drawdown)):
        if p > 0 and dd / p < -0.05:  # 回撤超過 5%
            if not in_drawdown:
                # 回撤開始
                in_drawdown = True
                drawdown_start = dates[i]
            # 更新底部
            if dd < drawdown_bottom_equity:
                drawdown_bottom = dates[i]
                drawdown_bottom_equity = dd
        else:
            if in_drawdown:
                # 回撤結束
                major_drawdowns.append({
                    'start': drawdown_start,
                    'bottom': drawdown_bottom,
                    'end': dates[i],
                    'depth': abs(drawdown_bottom_equity),
                    'depth_percent': abs(drawdown_bottom_equity / peak[dates.index(drawdown_bottom)] * 100) if peak[dates.index(drawdown_bottom)] > 0 else 0
                })
                in_drawdown = False
                drawdown_start = None
                drawdown_bottom = None
                drawdown_bottom_equity = None

    return {
        'dates': dates,
        'equity': equity,
        'peak': peak,
        'drawdown': drawdown,
        'major_drawdowns': major_drawdowns
    }


def calculate_cumulative_returns(positions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    計算累計收益率

    Args:
        positions: 倉位列表（按時間排序）

    Returns:
        Dict: 累計收益率數據
    """
    if not positions:
        return {
            'dates': [],
            'returns': [],
            'cagr': 0
        }

    # 按平倉時間排序
    sorted_positions = sorted(positions, key=lambda x: x['close_time'])

    # 計算每筆倉位的收益率（假設初始資金）
    initial_capital = 10000  # 假設初始資金 $10,000
    current_capital = initial_capital

    dates = [p['close_time'] for p in sorted_positions]
    returns = []

    for position in sorted_positions:
        # 假設投入資金為風險暴露
        risk_exposure = abs(position['max_loss']) if position['max_loss'] > 0 else 100
        position_return = position['net_profit'] / risk_exposure if risk_exposure > 0 else 0

        current_capital *= (1 + position_return)
        returns.append((current_capital / initial_capital - 1) * 100)

    # 計算年化收益率 (CAGR)
    if len(dates) > 1:
        days = (dates[-1] - dates[0]).total_seconds() / 86400
        final_return = returns[-1]
        cagr = (1 + final_return / 100) ** (365 / days) - 1
        cagr *= 100
    else:
        cagr = 0

    return {
        'dates': dates,
        'returns': returns,
        'cagr': round(cagr, 2)
    }
