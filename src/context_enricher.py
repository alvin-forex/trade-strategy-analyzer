#!/usr/bin/env python3
"""
Context Enricher - 為每個 Cycle / Trade 打上市況標籤

讀取已標記嘅 OHLCV 數據，將市況資訊附加到倉位/交易上
"""

import logging
from datetime import datetime
from typing import Dict, List, Any, Optional

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def enrich_cycle(cycle: Dict[str, Any],
                 market_data: Dict[str, Dict[str, pd.DataFrame]]) -> Dict[str, Any]:
    """
    為一個 Cycle 附加多時間框架市況標籤

    Args:
        cycle: 倉位字典 (from position_builder)
        market_data: {symbol: {tf: DataFrame_with_labels}}

    Returns:
        附加咗市況標籤嘅 cycle
    """
    from .indicators import get_context_at_time

    symbol = cycle.get('symbol', '')
    open_time = cycle.get('open_time')

    if not symbol or open_time is None:
        cycle['market_context'] = {}
        return cycle

    # Get data for this symbol
    sym_data = market_data.get(symbol, {})

    context = {}

    for tf in ['W1', 'D1', 'H4', 'M5']:
        df = sym_data.get(tf)
        if df is not None and not df.empty:
            from .indicators import label_all
            # Only label if not already labeled
            if 'trend_direction' not in df.columns:
                df = label_all(df, tf)
                sym_data[tf] = df

            tf_ctx = get_context_at_time(df, open_time, tf)
            context.update(tf_ctx)

    # Derive composite labels
    context.update(_derive_composite(context))

    cycle['market_context'] = context
    return cycle


def enrich_all_cycles(cycles: List[Dict[str, Any]],
                      market_data: Dict[str, Dict[str, pd.DataFrame]]) -> List[Dict[str, Any]]:
    """Enrich all cycles with market context."""
    enriched = []
    for i, cycle in enumerate(cycles):
        try:
            enriched.append(enrich_cycle(cycle, market_data))
        except Exception as e:
            logger.warning(f"Failed to enrich cycle {i}: {e}")
            cycle['market_context'] = {}
            enriched.append(cycle)

    return enriched


def _derive_composite(ctx: Dict[str, object]) -> Dict[str, object]:
    """
    從各 TF 標籤衍生綜合標籤
    """
    composite = {}

    # Multi-TF alignment
    w1_trend = ctx.get('W1_trend', 'UNKNOWN')
    d1_trend = ctx.get('D1_trend', 'UNKNOWN')
    h4_momentum = ctx.get('H4_momentum', 'UNKNOWN')

    up_signals = sum(1 for t in [w1_trend, d1_trend]
                     if 'UP' in str(t))
    down_signals = sum(1 for t in [w1_trend, d1_trend]
                       if 'DOWN' in str(t))

    if up_signals >= 2:
        composite['multi_tf_alignment'] = 'ALL_UP'
    elif down_signals >= 2:
        composite['multi_tf_alignment'] = 'ALL_DOWN'
    else:
        composite['multi_tf_alignment'] = 'MIXED'

    # Volatility regime
    d1_atr_pct = ctx.get('D1_atr_pct')
    if d1_atr_pct is not None:
        if d1_atr_pct >= 75:
            composite['volatility_regime'] = 'HIGH'
        elif d1_atr_pct >= 35:
            composite['volatility_regime'] = 'NORMAL'
        else:
            composite['volatility_regime'] = 'LOW'
    else:
        composite['volatility_regime'] = 'UNKNOWN'

    # Market phase (composite)
    d1_regime = ctx.get('D1_adx_regime', 'UNKNOWN')
    d1_position = ctx.get('D1_position')
    w1_trend_str = str(w1_trend)

    if 'UP' in w1_trend_str and d1_position is not None:
        if d1_position >= 85:
            phase = 'TREND_TOP'
        elif d1_position <= 15:
            phase = 'TREND_BOTTOM'
        else:
            phase = 'TREND_CONTINUATION'
    elif 'DOWN' in w1_trend_str and d1_position is not None:
        if d1_position <= 15:
            phase = 'TREND_BOTTOM'
        elif d1_position >= 85:
            phase = 'TREND_TOP'
        else:
            phase = 'TREND_CONTINUATION'
    elif d1_regime == 'RANGING':
        range_dur = ctx.get('D1_range_dur', 0)
        if isinstance(range_dur, (int, float)) and range_dur > 10:
            phase = 'RANGE_EXTENDED'
        elif isinstance(range_dur, (int, float)) and range_dur > 5:
            phase = 'RANGE_MID'
        else:
            phase = 'RANGE_START'
    else:
        phase = 'UNKNOWN'

    composite['market_phase'] = phase

    return composite


def get_cycle_summary(cycle: Dict[str, Any]) -> Dict[str, str]:
    """Get human-readable summary of a cycle's market context."""
    ctx = cycle.get('market_context', {})

    return {
        'W1 趨勢': ctx.get('W1_trend', '?'),
        'D1 市況': ctx.get('D1_adx_regime', '?'),
        'D1 ATR%': f"{ctx.get('D1_atr_pct', '?')}%" if ctx.get('D1_atr_pct') else '?',
        'H4 動能': ctx.get('H4_momentum', '?'),
        '多 TF': ctx.get('multi_tf_alignment', '?'),
        '波動': ctx.get('volatility_regime', '?'),
        '市況階段': ctx.get('market_phase', '?'),
    }
