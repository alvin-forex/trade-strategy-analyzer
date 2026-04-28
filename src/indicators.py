#!/usr/bin/env python3
"""
Indicator Engine - 計算技術指標並生成市況標籤

使用 pandas-ta 計算:
  EMA(20,50,200), ATR(14), ADX(14), RSI(14), BB(20,2), MACD(12,26,9)

衍生標籤:
  trend_direction, atr_percentile, adx_regime, range_duration,
  position_in_range, momentum, volatility_regime, market_phase
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pandas_ta as ta

logger = logging.getLogger(__name__)


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """
    為 OHLCV DataFrame 計算所有技術指標
    
    Args:
        df: DataFrame with Open, High, Low, Close, Volume columns
        
    Returns:
        DataFrame with added indicator columns
    """
    if df is None or df.empty:
        return df

    df = df.copy()

    # Ensure we have the right column types
    for col in ['Open', 'High', 'Low', 'Close']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')

    close = df['Close']
    high = df['High']
    low = df['Low']

    # EMA
    for period in [20, 50, 200]:
        df[f'EMA_{period}'] = ta.ema(close, length=period)

    # ATR
    df['ATR_14'] = ta.atr(high, low, close, length=14)

    # ADX
    adx = ta.adx(high, low, close, length=14)
    if adx is not None:
        df['ADX_14'] = adx['ADX_14']
        df['DMP_14'] = adx['DMP_14']   # +DI
        df['DMN_14'] = adx['DMN_14']   # -DI
    else:
        df['ADX_14'] = np.nan
        df['DMP_14'] = np.nan
        df['DMN_14'] = np.nan

    # RSI
    df['RSI_14'] = ta.rsi(close, length=14)

    # Bollinger Bands
    bb = ta.bbands(close, length=20, std=2)
    if bb is not None:
        # Column names vary by pandas_ta version — find by prefix
        bb_upper_col = next((c for c in bb.columns if c.startswith('BBU_')), None)
        bb_mid_col = next((c for c in bb.columns if c.startswith('BBM_')), None)
        bb_lower_col = next((c for c in bb.columns if c.startswith('BBL_')), None)
        if bb_upper_col and bb_mid_col and bb_lower_col:
            df['BB_Upper'] = bb[bb_upper_col]
            df['BB_Middle'] = bb[bb_mid_col]
            df['BB_Lower'] = bb[bb_lower_col]
            df['BB_Width'] = (df['BB_Upper'] - df['BB_Lower']) / df['BB_Middle']
        else:
            df['BB_Upper'] = np.nan
            df['BB_Middle'] = np.nan
            df['BB_Lower'] = np.nan
            df['BB_Width'] = np.nan
    else:
        df['BB_Upper'] = np.nan
        df['BB_Middle'] = np.nan
        df['BB_Lower'] = np.nan
        df['BB_Width'] = np.nan

    # MACD
    macd = ta.macd(close, fast=12, slow=26, signal=9)
    if macd is not None:
        macd_col = next((c for c in macd.columns if c.startswith('MACD_12_26_9') and 's' not in c.lower().replace('macd_12_26_9', '')), None)
        macd_s_col = next((c for c in macd.columns if c.startswith('MACDs_')), None)
        macd_h_col = next((c for c in macd.columns if c.startswith('MACDh_')), None)
        # Fallback: use positional
        cols = macd.columns.tolist()
        df['MACD'] = macd[macd_col] if macd_col else macd.iloc[:, 0]
        df['MACD_Signal'] = macd[macd_s_col] if macd_s_col else macd.iloc[:, 1]
        df['MACD_Hist'] = macd[macd_h_col] if macd_h_col else macd.iloc[:, 2]
    else:
        df['MACD'] = np.nan
        df['MACD_Signal'] = np.nan
        df['MACD_Hist'] = np.nan

    return df


def compute_atr_percentile(df: pd.DataFrame, window: int = 252) -> pd.Series:
    """Compute rolling percentile rank of ATR."""
    if 'ATR_14' not in df.columns:
        return pd.Series(np.nan, index=df.index)
    return df['ATR_14'].rolling(window).apply(
        lambda x: pd.Series(x).rank(pct=True).iloc[-1] * 100, raw=False
    )


def label_trend_direction(df: pd.DataFrame) -> pd.Series:
    """
    Label trend direction based on EMA alignment.
    
    UP: EMA20 > EMA50 > EMA200
    DOWN: EMA20 < EMA50 < EMA200
    FLAT: otherwise
    """
    ema20 = df.get('EMA_20')
    ema50 = df.get('EMA_50')
    ema200 = df.get('EMA_200')

    if any(x is None for x in [ema20, ema50, ema200]):
        return pd.Series('UNKNOWN', index=df.index)

    labels = []
    for e20, e50, e200 in zip(ema20, ema50, ema200):
        if pd.isna(e200):
            labels.append('UNKNOWN')
        elif e20 > e50 > e200:
            labels.append('UP')
        elif e20 < e50 < e200:
            labels.append('DOWN')
        elif e20 > e200:
            labels.append('UP_MIXED')
        elif e20 < e200:
            labels.append('DOWN_MIXED')
        else:
            labels.append('FLAT')

    return pd.Series(labels, index=df.index)


def label_adx_regime(df: pd.DataFrame, trending_threshold: float = 25,
                     strong_threshold: float = 40) -> pd.Series:
    """Label market regime based on ADX."""
    adx = df.get('ADX_14', pd.Series(np.nan, index=df.index))

    labels = []
    for val in adx:
        if pd.isna(val):
            labels.append('UNKNOWN')
        elif val >= strong_threshold:
            labels.append('STRONG_TREND')
        elif val >= trending_threshold:
            labels.append('TRENDING')
        else:
            labels.append('RANGING')

    return pd.Series(labels, index=df.index)


def label_range_duration(df: pd.DataFrame, trending_threshold: float = 25) -> pd.Series:
    """
    Count consecutive bars where ADX < threshold (ranging).
    Returns the count of consecutive ranging bars.
    """
    adx = df.get('ADX_14', pd.Series(np.nan, index=df.index))

    counts = []
    current_count = 0
    for val in adx:
        if pd.isna(val):
            counts.append(0)
            current_count = 0
        elif val < trending_threshold:
            current_count += 1
            counts.append(current_count)
        else:
            counts.append(0)
            current_count = 0

    return pd.Series(counts, index=df.index)


def label_position_in_range(df: pd.DataFrame, window: int = 20) -> pd.Series:
    """
    Position of close within the high-low range (0-100).
    0 = at low, 100 = at high, 50 = middle.
    """
    rolling_high = df['High'].rolling(window).max()
    rolling_low = df['Low'].rolling(window).min()
    range_width = rolling_high - rolling_low

    position = ((df['Close'] - rolling_low) / range_width * 100)
    position = position.clip(0, 100)
    return position


def label_momentum(df: pd.DataFrame, n_bars: int = 3) -> pd.Series:
    """
    Simple momentum label based on last N bars direction.
    STRONG_UP, UP, FLAT, DOWN, STRONG_DOWN
    """
    close = df['Close']
    change = close - close.shift(n_bars)
    atr = df.get('ATR_14', close * 0.001)  # fallback

    labels = []
    for chg, a in zip(change, atr):
        if pd.isna(chg) or pd.isna(a) or a == 0:
            labels.append('UNKNOWN')
            continue
        ratio = chg / a
        if ratio > 1.0:
            labels.append('STRONG_UP')
        elif ratio > 0.3:
            labels.append('UP')
        elif ratio > -0.3:
            labels.append('FLAT')
        elif ratio > -1.0:
            labels.append('DOWN')
        else:
            labels.append('STRONG_DOWN')

    return pd.Series(labels, index=df.index)


def label_all(df: pd.DataFrame, tf: str) -> pd.DataFrame:
    """
    Compute all indicators and labels for a DataFrame.
    
    Args:
        df: OHLCV DataFrame
        tf: timeframe string (W1, D1, H4, M5)
        
    Returns:
        DataFrame with all indicators and labels
    """
    if df is None or df.empty:
        return df

    # Compute indicators
    df = compute_indicators(df)

    # Compute labels
    df['trend_direction'] = label_trend_direction(df)
    df['atr_percentile'] = compute_atr_percentile(df)
    df['adx_regime'] = label_adx_regime(df)
    df['range_duration'] = label_range_duration(df)
    df['position_in_range'] = label_position_in_range(df)

    if tf in ('M5', 'M15'):
        df['momentum'] = label_momentum(df, n_bars=3)
    elif tf == 'H4':
        df['momentum'] = label_momentum(df, n_bars=2)
    else:
        df['momentum'] = label_momentum(df, n_bars=1)

    return df


def get_context_at_time(df: pd.DataFrame, timestamp: datetime,
                        tf: str) -> Dict[str, object]:
    """
    Get market context at a specific point in time.
    
    Returns a dict of indicator values and labels.
    """
    if df is None or df.empty:
        return {}

    ts = pd.Timestamp(timestamp, tz='UTC') if timestamp.tzinfo is None else pd.Timestamp(timestamp)
    if ts.tz is None:
        ts = ts.tz_localize('UTC')

    # Find the bar at or before timestamp
    mask = df.index <= ts
    if not mask.any():
        return {}

    row = df[mask].iloc[-1]

    context = {
        f'{tf}_close': safe_float(row.get('Close')),
        f'{tf}_ema20': safe_float(row.get('EMA_20')),
        f'{tf}_ema50': safe_float(row.get('EMA_50')),
        f'{tf}_ema200': safe_float(row.get('EMA_200')),
        f'{tf}_atr': safe_float(row.get('ATR_14')),
        f'{tf}_atr_pct': safe_float(row.get('atr_percentile')),
        f'{tf}_adx': safe_float(row.get('ADX_14')),
        f'{tf}_rsi': safe_float(row.get('RSI_14')),
        f'{tf}_bb_width': safe_float(row.get('BB_Width')),
        f'{tf}_macd_hist': safe_float(row.get('MACD_Hist')),
        f'{tf}_trend': safe_str(row.get('trend_direction')),
        f'{tf}_adx_regime': safe_str(row.get('adx_regime')),
        f'{tf}_range_dur': safe_int(row.get('range_duration')),
        f'{tf}_position': safe_float(row.get('position_in_range')),
        f'{tf}_momentum': safe_str(row.get('momentum')),
    }

    return context


def safe_float(val) -> Optional[float]:
    """Safely convert to float."""
    try:
        v = float(val)
        return round(v, 5) if not np.isnan(v) else None
    except (TypeError, ValueError):
        return None


def safe_int(val) -> Optional[int]:
    """Safely convert to int."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def safe_str(val) -> Optional[str]:
    """Safely convert to string."""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    return str(val)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Quick test with sample data
    dates = pd.date_range('2026-01-01', periods=200, freq='D', tz='UTC')
    np.random.seed(42)
    close = 0.68 + np.cumsum(np.random.randn(200) * 0.002)
    high = close + abs(np.random.randn(200) * 0.001)
    low = close - abs(np.random.randn(200) * 0.001)
    open_ = close + np.random.randn(200) * 0.0005

    test_df = pd.DataFrame({
        'Open': open_, 'High': high, 'Low': low, 'Close': close, 'Volume': 1000
    }, index=dates)

    labeled = label_all(test_df, 'D1')
    print(f"Columns: {labeled.columns.tolist()}")
    print(f"\nLast 5 rows:")
    print(labeled[['Close', 'EMA_20', 'trend_direction', 'adx_regime', 'ATR_14']].tail())

    # Test context
    ctx = get_context_at_time(labeled, dates[-1], 'D1')
    print(f"\nContext at last bar:")
    for k, v in ctx.items():
        print(f"  {k}: {v}")
