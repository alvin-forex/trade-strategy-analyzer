#!/usr/bin/env python3
"""
Entry Quality - 入市質量評估
兩層評分架構：Entry Score + Strategy Score
"""

from typing import Dict, List, Any
import numpy as np
from scipy import stats


def calculate_entry_score(position: Dict[str, Any]) -> Dict[str, Any]:
    """
    計算入市質量評分（Layer 1：Entry Signal Quality）
    只評估 L1，純粹量度入市信號好壞

    Args:
        position: 倉位字典

    Returns:
        Dict: 評分結果
    """
    # 獲取 L1 數據
    max_pips = position.get('l1_max_pips', 0)
    max_loss_pips = position.get('l1_max_loss_pips', 0)

    # 維度 1：方向準確性（35%）
    # 使用 Max Pips 而非 Net Pips 判斷方向
    if max_pips > 20:
        direction_score = 1.0
    elif max_pips > 10:
        direction_score = 0.7
    elif max_pips > 0:
        direction_score = 0.4
    else:
        direction_score = 0.0

    # 方向強度
    direction_intensity = min(max_pips / 100, 1.0)
    direction_score = direction_score * (0.5 + 0.5 * direction_intensity)

    # 維度 2：入市時機（35%）
    # 時機分數 = Max Pips / (Max Pips + |Max Loss Pips|)
    if max_pips < 5 and abs(max_loss_pips) < 5:
        timing_score = 0.5  # 邊界處理
    else:
        timing_score = max_pips / (max_pips + abs(max_loss_pips)) if (max_pips + abs(max_loss_pips)) > 0 else 0.5

    # 馬丁修正：多層倉位的 L1 本來就會承受較大浮虧
    max_layer = position.get('max_layer', 1)
    if max_layer >= 4:
        # 減輕對 L1 時機的懲罰
        timing_score = min(timing_score * 1.2, 1.0)

    # 維度 3：初始回撤（30%）
    # 回撤分數 = 1 - min(|Max Loss Pips| / 200, 1.0)
    initial_dd_score = 1 - min(abs(max_loss_pips) / 200, 1.0)

    # 加權計算
    entry_score = (
        direction_score * 0.35 +
        timing_score * 0.35 +
        initial_dd_score * 0.30
    ) * 100

    # 評級
    if entry_score >= 80:
        grade = 'A'
        grade_text = '優質'
    elif entry_score >= 60:
        grade = 'B'
        grade_text = '一般'
    elif entry_score >= 40:
        grade = 'C'
        grade_text = '偏弱'
    else:
        grade = 'D'
        grade_text = '差'

    return {
        'score': round(entry_score, 2),
        'grade': grade,
        'grade_text': grade_text,
        'breakdown': {
            'direction': round(direction_score * 35, 2),
            'timing': round(timing_score * 35, 2),
            'initial_dd': round(initial_dd_score * 30, 2)
        },
        'components': {
            'direction_raw': round(direction_score, 3),
            'timing_raw': round(timing_score, 3),
            'initial_dd_raw': round(initial_dd_score, 3),
            'max_pips': max_pips,
            'max_loss_pips': max_loss_pips
        }
    }


def calculate_strategy_score(position: Dict[str, Any]) -> Dict[str, Any]:
    """
    計算策略執行質量評分（Layer 2：Strategy Execution Quality）
    評估整個倉位的策略執行效果

    Args:
        position: 倉位字典

    Returns:
        Dict: 評分結果
    """
    net_profit = position.get('net_profit', 0)
    max_profit = position.get('max_profit', 0)
    max_loss = position.get('max_loss', 0)
    max_layer = position.get('max_layer', 1)
    holding_time = position.get('holding_time_hours', 0)

    # 維度 1：回歸性（30%）
    # 這裡用一個簡化的回歸性指標：高層數倉位的獲利能力
    if max_layer >= 4:
        if net_profit > 0:
            regression_score = 1.0
        elif net_profit > -20:
            regression_score = 0.7
        else:
            regression_score = 0.3
    else:
        # 低層數倉位，回歸性主要看盈虧
        if net_profit > 0:
            regression_score = 0.8
        else:
            regression_score = 0.4

    # 維度 2：出場效率（25%）
    if net_profit > 0:
        # 贏倉：Net Profit / Max Profit
        exit_efficiency = net_profit / max_profit if max_profit > 0 else 0.5
    else:
        # 輸倉：|Net Loss| / |Max Loss|
        exit_efficiency = abs(net_profit) / abs(max_loss) if abs(max_loss) > 0 else 0.5

    exit_score = min(exit_efficiency, 1.0)

    # 維度 3：風險控制（20%）
    # 考慮層數和最大回撤
    if max_layer <= 2:
        layer_score = 1.0
    elif max_layer <= 4:
        layer_score = 0.7
    else:
        layer_score = 0.4

    # 考慮最大回撤
    if max_loss > 0:
        dd_ratio = max_loss / abs(net_profit) if net_profit != 0 else 1.0
        dd_score = max(0, 1 - dd_ratio / 5)
    else:
        dd_score = 1.0

    risk_score = (layer_score + dd_score) / 2

    # 維度 4：收益質量（15%）
    # 這裡用簡化的質量指標：收益穩定性
    quality_score = 0.7 if net_profit > 0 else 0.3

    # 維度 5：成本 + 持倉（10%）
    # 考慮持倉時間效率
    total_commission = position.get('total_commission', 0)
    total_swap = position.get('total_swap', 0)
    total_cost = abs(total_commission) + abs(total_swap)

    if holding_time > 0:
        cost_per_hour = total_cost / holding_time
        if cost_per_hour < 0.5:
            cost_score = 1.0
        elif cost_per_hour < 1.0:
            cost_score = 0.7
        else:
            cost_score = 0.4
    else:
        cost_score = 1.0

    # 加權計算
    strategy_score = (
        regression_score * 0.30 +
        exit_score * 0.25 +
        risk_score * 0.20 +
        quality_score * 0.15 +
        cost_score * 0.10
    ) * 100

    # 評級
    if strategy_score >= 80:
        grade = 'A'
        grade_text = '優質'
    elif strategy_score >= 60:
        grade = 'B'
        grade_text = '一般'
    elif strategy_score >= 40:
        grade = 'C'
        grade_text = '偏弱'
    else:
        grade = 'D'
        grade_text = '差'

    return {
        'score': round(strategy_score, 2),
        'grade': grade,
        'grade_text': grade_text,
        'breakdown': {
            'regression': round(regression_score * 30, 2),
            'exit_efficiency': round(exit_score * 25, 2),
            'risk_control': round(risk_score * 20, 2),
            'profit_quality': round(quality_score * 15, 2),
            'cost_holding': round(cost_score * 10, 2)
        },
        'components': {
            'regression_raw': round(regression_score, 3),
            'exit_raw': round(exit_score, 3),
            'risk_raw': round(risk_score, 3),
            'quality_raw': round(quality_score, 3),
            'cost_raw': round(cost_score, 3)
        }
    }


def calculate_final_score(entry_score: float, strategy_score: float) -> Dict[str, Any]:
    """
    計算最終評分

    Final = Entry × 0.4 + Strategy × 0.6

    Args:
        entry_score: 入市質量評分
        strategy_score: 策略執行評分

    Returns:
        Dict: 最終評分
    """
    final_score = entry_score * 0.4 + strategy_score * 0.6

    if final_score >= 80:
        grade = 'A'
        grade_text = '可 Copy'
    elif final_score >= 60:
        grade = 'B'
        grade_text = '需評估'
    elif final_score >= 40:
        grade = 'C'
        grade_text = '需調整'
    else:
        grade = 'D'
        grade_text = '不建議'

    return {
        'score': round(final_score, 2),
        'grade': grade,
        'grade_text': grade_text
    }


def evaluate_positions(positions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    評估所有倉位的質量

    Args:
        positions: 倉位列表

    Returns:
        List[Dict]: 加入評分的倉位列表
    """
    evaluated_positions = []

    for position in positions:
        # 計算各項評分
        entry_result = calculate_entry_score(position)
        strategy_result = calculate_strategy_score(position)
        final_result = calculate_final_score(
            entry_result['score'],
            strategy_result['score']
        )

        # 加入評分到倉位
        position['entry_quality'] = entry_result
        position['strategy_quality'] = strategy_result
        position['final_quality'] = final_result

        evaluated_positions.append(position)

    return evaluated_positions
