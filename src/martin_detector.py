#!/usr/bin/env python3
"""
Martin Detector - 從 .set 參數偵測策略類型

分析 lotExp, pipstep, 分層參數等，判斷是否為:
  - GRID (網格)
  - MARTINGALE (馬丁)
  - DCA (均攤)
  - SIGNAL (信號策略)
"""

import re
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger(__name__)


def detect_strategy_type(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    從 .set 參數偵測策略類型同特徵

    Args:
        params: set_parser 返回嘅分類參數字典

    Returns:
        Dict with:
          strategy_type: GRID/MARTINGALE/DCA/SIGNAL/SCALPER/TREND
          is_martingale: bool
          lot_exp: float or None
          max_levels: int
          pipstep_values: list of floats
          details: dict of detected features
    """
    result = {
        'strategy_type': 'UNKNOWN',
        'is_martingale': False,
        'is_grid': False,
        'is_dca': False,
        'lot_exp': None,
        'max_levels': 0,
        'pipstep_values': [],
        'details': {},
    }

    martin_params = params.get('martingale', {})
    basic_params = params.get('basic', {})

    # 1. 偵測 lotExp (馬丁倍率)
    lot_exp_str = martin_params.get('lotExp')
    if lot_exp_str:
        try:
            lot_exp = float(lot_exp_str)
            result['lot_exp'] = lot_exp
            if lot_exp > 1.0:
                result['is_martingale'] = True
                result['details']['lot_exp'] = lot_exp
        except (ValueError, TypeError):
            pass

    # 2. 偵測分層系統 (MKD style: PipStep1-5, lot1-5 etc.)
    levels = _detect_mkd_levels(martin_params)
    if levels > 0:
        result['max_levels'] = levels
        result['details']['level_system'] = 'MKD'

    # 3. 偵測傳統 pipstep 系統 (pipstep2, pipstep3 etc.)
    pipstep_values = _detect_pipstep_values(martin_params)
    if pipstep_values:
        result['pipstep_values'] = pipstep_values
        result['details']['pipstep_pattern'] = _classify_pipstep_pattern(pipstep_values)

    # 4. 偵測 lot 序列
    lot_values = _detect_lot_values(martin_params)
    if lot_values:
        result['details']['lot_pattern'] = _classify_lot_pattern(lot_values)
        result['details']['lot_values'] = lot_values

    # 5. 分層止損偵測
    sl_in_level = martin_params.get('slInLevel')
    if sl_in_level:
        try:
            if int(sl_in_level) > 0:
                result['details']['has_level_sl'] = True
        except (ValueError, TypeError):
            pass

    # 6. 綜合判斷策略類型
    result['strategy_type'] = _classify_strategy(result)

    return result


def _detect_mkd_levels(martin_params: Dict[str, str]) -> int:
    """Detect number of MKD-style levels (PipStep1-5, lot1-5 etc.)"""
    max_level = 0

    # Check both PipStep1-5 and S1/S2 variants
    for i in range(1, 10):
        for prefix in [f'PipStep{i}', f'pipstep{i}', f'lot{i}', f'PipStepS{i}']:
            if prefix in martin_params:
                val = martin_params[prefix]
                try:
                    if float(val) > 0:
                        max_level = max(max_level, i)
                except (ValueError, TypeError):
                    pass

    return max_level


def _detect_pipstep_values(martin_params: Dict[str, str]) -> List[float]:
    """Detect pipstep values in order."""
    values = []

    # Traditional: pipstep2, pipstep3, ...
    for i in range(2, 9):
        key = f'pipstep{i}'
        if key in martin_params:
            try:
                val = float(martin_params[key])
                if val > 0:
                    values.append(val)
            except (ValueError, TypeError):
                pass

    # MKD: PipStep1, PipStep2, ...
    if not values:
        for i in range(1, 10):
            key = f'PipStep{i}'
            if key in martin_params:
                try:
                    val = float(martin_params[key])
                    if val > 0:
                        values.append(val)
                except (ValueError, TypeError):
                    pass

    return values


def _detect_lot_values(martin_params: Dict[str, str]) -> List[float]:
    """Detect lot values in order."""
    values = []

    # MKD: lot1, lot2, ...
    for i in range(1, 10):
        for prefix in [f'lot{i}', f'lotS{i}']:
            if prefix in martin_params:
                try:
                    val = float(martin_params[prefix])
                    if val > 0:
                        values.append(val)
                except (ValueError, TypeError):
                    pass

    # Traditional: EntryLot
    if not values:
        entry_lot = martin_params.get('EntryLot')
        if entry_lot:
            try:
                values.append(float(entry_lot))
            except (ValueError, TypeError):
                pass

    return values


def _classify_pipstep_pattern(values: List[float]) -> str:
    """Classify the pipstep pattern."""
    if len(values) <= 1:
        return 'SINGLE'

    # Check if increasing (wider spacing at deeper levels)
    increasing = all(values[i] < values[i + 1] for i in range(len(values) - 1))
    # Check if decreasing
    decreasing = all(values[i] > values[i + 1] for i in range(len(values) - 1))
    # Check if constant
    constant = all(abs(values[i] - values[0]) < 0.01 for i in range(len(values)))

    if constant:
        return 'CONSTANT'
    elif increasing:
        return 'WIDENING'
    elif decreasing:
        return 'NARROWING'
    else:
        return 'MIXED'


def _classify_lot_pattern(values: List[float]) -> str:
    """Classify the lot progression pattern."""
    if len(values) <= 1:
        return 'SINGLE'

    ratios = [values[i + 1] / values[i] for i in range(len(values) - 1)]
    avg_ratio = sum(ratios) / len(ratios)

    if all(abs(r - ratios[0]) < 0.1 for r in ratios):
        # Consistent multiplier
        if avg_ratio > 1.5:
            return f'MARTINGALE (x{avg_ratio:.1f})'
        elif avg_ratio > 1.05:
            return f'INCREASING (x{avg_ratio:.1f})'
        else:
            return 'CONSTANT'
    else:
        return 'VARIABLE'


def _classify_strategy(result: Dict[str, Any]) -> str:
    """Final strategy classification."""
    is_martingale = result.get('is_martingale', False)
    max_levels = result.get('max_levels', 0)
    pipstep_values = result.get('pipstep_values', [])
    details = result.get('details', {})

    has_levels = max_levels >= 2 or len(pipstep_values) >= 2

    if not has_levels:
        return 'SIGNAL'

    if is_martingale:
        return 'MARTINGALE'

    # Check lot pattern
    lot_pattern = details.get('lot_pattern', '')
    if 'MARTINGALE' in lot_pattern:
        return 'MARTINGALE'

    pipstep_pattern = details.get('pipstep_pattern', '')
    if pipstep_pattern == 'CONSTANT':
        return 'GRID'
    elif pipstep_pattern == 'WIDENING':
        return 'DCA'

    return 'GRID'


def generate_detection_report(detection: Dict[str, Any]) -> str:
    """Generate a human-readable detection report."""
    lines = []
    lines.append(f"策略類型: {detection['strategy_type']}")
    lines.append(f"馬丁偵測: {'✅ 是' if detection['is_martingale'] else '❌ 否'}")

    if detection.get('lot_exp'):
        lines.append(f"lotExp: {detection['lot_exp']}")

    if detection.get('max_levels'):
        lines.append(f"最大層數: {detection['max_levels']}")

    details = detection.get('details', {})
    if 'lot_pattern' in details:
        lines.append(f"手數模式: {details['lot_pattern']}")

    if 'pipstep_pattern' in details:
        lines.append(f"加倉距離模式: {details['pipstep_pattern']}")

    if 'pipstep_values' in details:
        vals = details['pipstep_values']
        lines.append(f"加倉距離: {', '.join(str(v) for v in vals)}")

    return '\n'.join(lines)


if __name__ == '__main__':
    # Test with sample parameters
    test_params = {
        'martingale': {
            'EntryLot': '0.01',
            'lotExp': '1.8',
            'pipstep2': '30',
            'pipstep3': '45',
            'pipstep4': '60',
            'pipstep5': '75',
            'PipStep1': '15',
            'lot1': '0.01',
            'lot2': '0.02',
            'lot3': '0.04',
            'lot4': '0.07',
            'lot5': '0.13',
            'slInLevel': '0',
        },
        'basic': {
            'EA_NAME': 'MKD',
        }
    }

    result = detect_strategy_type(test_params)
    print(generate_detection_report(result))
