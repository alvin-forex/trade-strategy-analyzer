#!/usr/bin/env python3
"""
Market Data Provider - 從 Dukascopy 下載 OHLCV 數據並緩存為 Parquet

支援: M1, M5, M15, H1, H4, D1, W1
自動增量更新
"""

import os
import time
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)

# Interval mapping for dukascopy_python
INTERVAL_MAP = {
    'M1': '1MIN',
    'M5': '5MIN',
    'M15': '15MIN',
    'H1': '1HOUR',
    'H4': '4HOUR',
    'D1': '1DAY',
    'W1': '1WEEK',
}

# Symbol to Dukascopy instrument string
def _get_instrument(symbol: str) -> str:
    """Convert 'AUDCHF' to 'AUD/CHF'."""
    # Handle special cases
    if symbol.startswith('XAU'):
        return 'XAU/USD'
    elif symbol.startswith('XAG'):
        return 'XAG/USD'
    elif 'IDX' in symbol:
        # Indices: USA500IDXUSD -> USA500.IDX/USD
        # Dukascopy uses format like USA500.IDX/USD, USATECH.IDX/USD, HKG.IDX/HKD
        idx_map = {
            'USA500IDXUSD': 'USA500.IDX/USD',
            'USATECHIDXUSD': 'USATECH.IDX/USD',
            'HKGIDXHKD': 'HKG.IDX/HKD',
        }
        return idx_map.get(symbol, symbol)
    else:
        # Standard forex: AUDCHF -> AUD/CHF
        if '/' in symbol:
            return symbol
        return f'{symbol[:3]}/{symbol[3:]}'


# Time range extensions for indicator calculation
# How far back we need BEFORE the first trade date
LOOKBACK_DAYS = {
    'W1': 365 * 4,    # 200 EMA on weekly = ~4 years
    'D1': 300,         # 200 EMA on daily = ~300 days
    'H4': 150,         # 200 EMA on H4 = ~150 days
    'M5': 14,          # M5 indicators don't need much lookback
}


class MarketDataProvider:
    """
    下載、緩存同提供 OHLCV 市場數據

    使用 Dukascopy API 下載，Parquet 本地緩存
    支持增量更新
    """

    def __init__(self, cache_dir: str = None):
        if cache_dir is None:
            base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            cache_dir = os.path.join(base, 'market_data')
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)

    def get_parquet_path(self, symbol: str, tf: str) -> str:
        d = os.path.join(self.cache_dir, symbol)
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, f'{tf}.parquet')

    def load_cached(self, symbol: str, tf: str) -> Optional[pd.DataFrame]:
        path = self.get_parquet_path(symbol, tf)
        if os.path.exists(path):
            df = pd.read_parquet(path)
            if not df.empty:
                df = df.sort_index()
                logger.info(f"Loaded {symbol}/{tf}: {len(df)} bars, "
                          f"{df.index[0]} → {df.index[-1]}")
                return df
        return None

    def save_cache(self, symbol: str, tf: str, df: pd.DataFrame):
        if df is None or df.empty:
            return
        path = self.get_parquet_path(symbol, tf)
        df = df.sort_index()
        df = df[~df.index.duplicated(keep='last')]
        df.to_parquet(path, index=True)
        logger.info(f"Saved {symbol}/{tf}: {len(df)} bars → {path}")

    def _download_chunk(self, symbol: str, tf: str,
                        start: datetime, end: datetime) -> Optional[pd.DataFrame]:
        """Download a chunk of data from Dukascopy."""
        try:
            import dukascopy_python as dc

            instrument = _get_instrument(symbol)
            interval = INTERVAL_MAP.get(tf)
            if interval is None:
                raise ValueError(f"Unknown timeframe: {tf}")

            logger.info(f"Downloading {symbol}/{tf} ({instrument}): "
                       f"{start.date()} → {end.date()}")

            df = dc.fetch(
                instrument=instrument,
                interval=interval,
                offer_side=dc.OFFER_SIDE_BID,
                start=start,
                end=end,
                max_retries=3,
            )

            if df is not None and not df.empty:
                df = self._standardize_columns(df, tf)
                return df
            return None

        except Exception as e:
            logger.error(f"Download failed {symbol}/{tf} {start}→{end}: {e}")
            return None

    def _standardize_columns(self, df: pd.DataFrame, tf: str) -> pd.DataFrame:
        """Standardize OHLCV column names."""
        rename_map = {}
        current_cols = df.columns.tolist()

        col_mappings = {
            'open': 'Open', 'high': 'High', 'low': 'Low',
            'close': 'Close', 'volume': 'Volume',
            'Open': 'Open', 'High': 'High', 'Low': 'Low',
            'Close': 'Close', 'Volume': 'Volume',
            'bidOpen': 'Open', 'bidHigh': 'High',
            'bidLow': 'Low', 'bidClose': 'Close',
            'askOpen': 'Open_ask', 'askHigh': 'High_ask',
            'askLow': 'Low_ask', 'askClose': 'Close_ask',
        }

        for col in current_cols:
            if col in col_mappings:
                rename_map[col] = col_mappings[col]

        if rename_map:
            df = df.rename(columns=rename_map)

        if df.index.name != 'timestamp':
            if 'timestamp' in df.columns:
                df = df.set_index('timestamp')
            elif df.index.name is None:
                df.index.name = 'timestamp'

        # Ensure UTC timezone
        if df.index.tz is None:
            df.index = df.index.tz_localize('UTC')

        return df

    def download(self, symbol: str, tf: str,
                 start: datetime, end: datetime,
                 force: bool = False) -> pd.DataFrame:
        """
        Download data for a symbol/timeframe, using cache if available.
        """
        cached = None if force else self.load_cached(symbol, tf)

        if cached is not None:
            cached_start = cached.index[0]
            cached_end = cached.index[-1]

            # Normalize to UTC-aware for comparison
            start_ts = pd.Timestamp(start, tz='UTC') if start.tzinfo is None else pd.Timestamp(start)
            end_ts = pd.Timestamp(end, tz='UTC') if end.tzinfo is None else pd.Timestamp(end)

            need_before = start_ts < cached_start
            need_after = end_ts > cached_end

            if not need_before and not need_after:
                return cached[cached.index >= start_ts]

            chunks = []
            if need_before:
                chunk = self._download_chunk(symbol, tf, start, cached_start)
                if chunk is not None:
                    chunks.append(chunk)
                time.sleep(0.5)

            if need_after:
                chunk = self._download_chunk(symbol, tf, cached_end, end)
                if chunk is not None:
                    chunks.append(chunk)
                time.sleep(0.5)

            chunks.append(cached)
            combined = pd.concat(chunks)
            combined = combined[~combined.index.duplicated(keep='last')]
            combined = combined.sort_index()
            self.save_cache(symbol, tf, combined)

            mask = combined.index >= pd.Timestamp(start, tz='UTC')
            return combined[mask].copy()

        else:
            all_chunks = []
            current = start
            chunk_delta = timedelta(days=30)

            while current < end:
                chunk_end = min(current + chunk_delta, end)
                chunk = self._download_chunk(symbol, tf, current, chunk_end)
                if chunk is not None:
                    all_chunks.append(chunk)
                current = chunk_end
                time.sleep(0.3)

            if not all_chunks:
                logger.warning(f"No data downloaded for {symbol}/{tf}")
                return pd.DataFrame()

            combined = pd.concat(all_chunks)
            combined = combined[~combined.index.duplicated(keep='last')]
            combined = combined.sort_index()
            self.save_cache(symbol, tf, combined)

            return combined

    def download_for_analysis(self, symbols: list,
                              trade_start: datetime, trade_end: datetime,
                              timeframes: list = None) -> Dict[str, Dict[str, pd.DataFrame]]:
        """
        Download all data needed for analysis.

        Automatically calculates lookback based on timeframe.
        """
        if timeframes is None:
            timeframes = ['W1', 'D1', 'H4', 'M5']

        end = trade_end + timedelta(days=7)

        result = {}
        for symbol in symbols:
            result[symbol] = {}
            for tf in timeframes:
                lookback = LOOKBACK_DAYS.get(tf, 30)
                start = trade_start - timedelta(days=lookback)

                logger.info(f"\n{'='*50}")
                logger.info(f"Fetching {symbol}/{tf}: "
                          f"{start.date()} → {end.date()} "
                          f"(lookback {lookback} days)")

                try:
                    df = self.download(symbol, tf, start, end)
                    result[symbol][tf] = df
                    logger.info(f"  ✓ {len(df)} bars")
                except Exception as e:
                    logger.error(f"  ✗ {symbol}/{tf} failed: {e}")
                    result[symbol][tf] = pd.DataFrame()

                time.sleep(0.5)  # Rate limit between symbols/TFs

        return result

    def get_data_at(self, symbol: str, tf: str,
                    timestamp: datetime) -> Optional[pd.Series]:
        df = self.load_cached(symbol, tf)
        if df is None or df.empty:
            return None

        ts = pd.Timestamp(timestamp, tz='UTC')
        mask = df.index <= ts
        if mask.any():
            return df[mask].iloc[-1]
        return None

    def get_data_range(self, symbol: str, tf: str,
                       start: datetime, end: datetime) -> pd.DataFrame:
        df = self.load_cached(symbol, tf)
        if df is None or df.empty:
            return pd.DataFrame()

        s = pd.Timestamp(start, tz='UTC')
        e = pd.Timestamp(end, tz='UTC')
        mask = (df.index >= s) & (df.index <= e)
        return df[mask]


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s [%(levelname)s] %(message)s')

    provider = MarketDataProvider()

    # Test: download AUDCHF D1 for last 30 days
    end = datetime(2026, 4, 27)
    start = end - timedelta(days=30)

    print("Testing MarketDataProvider...")
    df = provider.download('AUDCHF', 'D1', start, end)
    if df is not None and not df.empty:
        print(f"OK! {len(df)} bars")
        print(df.head())
        print(df.tail())
    else:
        print("No data returned")
