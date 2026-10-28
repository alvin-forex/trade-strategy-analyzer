#!/usr/bin/env python3
"""
Copy Trade Simulator - 逐單模擬 Copy on Profit / Copy on Lose

對每個 Cycle 嘅 L1 入場點，模擬延遲入場嘅效果：
  - Copy on Profit: 等價格向有利方向移動 N pips 先入場
  - Copy on Lose: 等價格向不利方向移動 N pips 先入場（更好價格）
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Default wait pips to simulate
DEFAULT_PROFIT_PIPS = [5, 10, 15, 20]
DEFAULT_LOSE_PIPS = [10, 15, 20, 25]


def simulate_copy_trade(
    cycle: Dict[str, Any],
    m5_data: pd.DataFrame,
    profit_pips: List[float] = None,
    lose_pips: List[float] = None,
) -> List[Dict[str, Any]]:
    """
    Simulate copy trade scenarios for a single cycle.

    For each cycle's L1 entry, simulate what would happen if we waited
    for price to move N pips before entering.

    Args:
        cycle: Position dict from position_builder
        m5_data: M5 OHLCV data with indicators (must cover entry period)
        profit_pips: list of positive pip values for Copy on Profit
        lose_pips: list of negative pip values for Copy on Lose (positive values, 
                   will be applied as negative movement)

    Returns:
        List of simulation result dicts
    """
    if profit_pips is None:
        profit_pips = DEFAULT_PROFIT_PIPS
    if lose_pips is None:
        lose_pips = DEFAULT_LOSE_PIPS

    # Get L1 trade info
    trades = cycle.get('trades', [])
    l1_trades = [t for t in trades if t.get('layer', 0) == 1]

    if not l1_trades:
        logger.warning(f"Cycle {cycle.get('position_key', '?')}: No L1 trade found")
        return []

    l1 = l1_trades[0]
    symbol = cycle.get('symbol', '')
    direction = cycle.get('direction', '')
    entry_price = l1.get('Open Price', 0)
    entry_time = l1.get('Open Time')
    close_price = cycle.get('close_time')  # Cycle close time
    cycle_close_price = None

    # Get the actual exit price from cycle
    if trades:
        # Last trade's close price
        cycle_close_price = trades[-1].get('Close Price', 0)

    if not entry_price or not entry_time or not cycle_close_price:
        return []

    # Determine pip size
    pip_size = _get_pip_size(symbol)

    # Get M5 bars around the entry time
    entry_ts = pd.Timestamp(entry_time, tz='UTC') if entry_time.tzinfo is None else pd.Timestamp(entry_time)
    if entry_ts.tz is None:
        entry_ts = entry_ts.tz_localize('UTC')

    # Look at M5 bars from entry to +24 hours
    end_ts = entry_ts + timedelta(hours=24)
    mask = (m5_data.index >= entry_ts) & (m5_data.index <= end_ts)
    m5_slice = m5_data[mask]

    if m5_slice.empty:
        logger.warning(f"No M5 data for {symbol} around {entry_time}")
        return []

    results = []

    # Actual cycle result (baseline)
    actual_result = {
        'cycle_key': cycle.get('position_key', ''),
        'symbol': symbol,
        'direction': direction,
        'entry_time': entry_time,
        'entry_price': entry_price,
        'sim_type': 'ACTUAL',
        'wait_pips': 0,
        'triggered': True,
        'trigger_time': entry_time,
        'sim_entry_price': entry_price,
        'sim_exit_price': cycle_close_price,
        'sim_profit_pips': _calc_pips(entry_price, cycle_close_price, direction, pip_size),
        'sim_profit': cycle.get('net_profit', 0),
        'actual_levels': cycle.get('layer_count', 1),
        'holding_hours': cycle.get('holding_time_hours', 0),
    }
    results.append(actual_result)

    # Simulate Copy on Profit
    for pips in profit_pips:
        sim = _simulate_delayed_entry(
            m5_slice, entry_price, entry_ts, cycle_close_price,
            direction, pip_size, pips, 'COPY_PROFIT', cycle
        )
        sim['cycle_key'] = cycle.get('position_key', '')
        sim['symbol'] = symbol
        sim['direction'] = direction
        sim['entry_time'] = entry_time
        sim['entry_price'] = entry_price
        results.append(sim)

    # Simulate Copy on Lose
    for pips in lose_pips:
        sim = _simulate_delayed_entry(
            m5_slice, entry_price, entry_ts, cycle_close_price,
            direction, pip_size, -pips, 'COPY_LOSE', cycle
        )
        sim['cycle_key'] = cycle.get('position_key', '')
        sim['symbol'] = symbol
        sim['direction'] = direction
        sim['entry_time'] = entry_time
        sim['entry_price'] = entry_price
        results.append(sim)

    return results


def _simulate_delayed_entry(
    m5_slice: pd.DataFrame,
    entry_price: float,
    entry_ts: pd.Timestamp,
    cycle_close_price: float,
    direction: str,
    pip_size: float,
    wait_pips: float,
    sim_type: str,
    cycle: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Simulate a delayed entry.

    wait_pips > 0: wait for price to move IN FAVOR (Copy on Profit)
    wait_pips < 0: wait for price to move AGAINST (Copy on Lose)
    """
    is_buy = direction.upper() == 'BUY'

    if is_buy:
        if wait_pips > 0:
            # Copy on Profit: wait for price to go UP by wait_pips
            target_price = entry_price + wait_pips * pip_size
        else:
            # Copy on Lose: wait for price to go DOWN by |wait_pips|
            target_price = entry_price + wait_pips * pip_size  # wait_pips is negative
    else:
        if wait_pips > 0:
            target_price = entry_price - wait_pips * pip_size
        else:
            target_price = entry_price - wait_pips * pip_size

    # Scan M5 bars to find trigger
    triggered = False
    trigger_time = None
    sim_entry_price = target_price

    for idx, row in m5_slice.iterrows():
        high = row.get('High', 0)
        low = row.get('Low', 0)

        if is_buy:
            if wait_pips > 0:
                # Wait for price to reach target (higher)
                if high >= target_price:
                    triggered = True
                    trigger_time = idx
                    break
            else:
                # Wait for price to drop to target (lower)
                if low <= target_price:
                    triggered = True
                    trigger_time = idx
                    break
        else:  # SELL
            if wait_pips > 0:
                # Wait for price to drop to target
                if low <= target_price:
                    triggered = True
                    trigger_time = idx
                    break
            else:
                # Wait for price to rise to target
                if high >= target_price:
                    triggered = True
                    trigger_time = idx
                    break

    if not triggered:
        return {
            'sim_type': sim_type,
            'wait_pips': wait_pips,
            'triggered': False,
            'trigger_time': None,
            'sim_entry_price': None,
            'sim_exit_price': None,
            'sim_profit_pips': None,
            'sim_profit': None,
            'actual_levels': cycle.get('layer_count', 1),
            'holding_hours': None,
        }

    # Calculate simulated P&L
    # Use the same exit as the original cycle (same TP/SL)
    # The copy trade only changes ENTRY, not EXIT
    sim_pips = _calc_pips(sim_entry_price, cycle_close_price, direction, pip_size)

    # Estimate profit using L1 lot size only (single layer, no grid)
    l1_lot = None
    for t in cycle.get('trades', []):
        if t.get('layer', 0) == 1:
            l1_lot = t.get('Lots', 0.01)
            break
    if l1_lot is None:
        l1_lot = 0.01

    # Approximate profit: pips * pip_value * lots
    # pip_value ≈ pip_size * lot_size * contract_size
    # For simplicity: profit = pips * lot * pip_value_per_lot
    # pip_value_per_lot ≈ 10 for standard lot on XXXUSD pairs, varies otherwise
    pip_value = _estimate_pip_value(cycle.get('symbol', ''), sim_entry_price)
    sim_profit = sim_pips * l1_lot * pip_value

    # Holding time from trigger to cycle close
    cycle_close_time = cycle.get('close_time')
    holding_hours = None
    if trigger_time and cycle_close_time:
        close_ts = pd.Timestamp(cycle_close_time)
        if close_ts.tz is None:
            close_ts = close_ts.tz_localize('UTC')
        holding_hours = (close_ts - trigger_time).total_seconds() / 3600

    return {
        'sim_type': sim_type,
        'wait_pips': wait_pips,
        'triggered': True,
        'trigger_time': trigger_time,
        'sim_entry_price': round(sim_entry_price, 6),
        'sim_exit_price': cycle_close_price,
        'sim_profit_pips': round(sim_pips, 2),
        'sim_profit': round(sim_profit, 2),
        'actual_levels': cycle.get('layer_count', 1),
        'holding_hours': round(holding_hours, 2) if holding_hours else None,
    }


def _get_pip_size(symbol: str) -> float:
    """Get pip size for a symbol."""
    # JPY pairs: 0.01 (pip = 0.01)
    if 'JPY' in symbol:
        return 0.01
    # XAUUSD: 0.1 (pip = 0.1)
    elif 'XAU' in symbol:
        return 0.1
    # XAGUSD: 0.001
    elif 'XAG' in symbol:
        return 0.001
    # Indices: varies
    elif 'IDX' in symbol:
        return 1.0
    # Standard forex: 0.0001
    else:
        return 0.0001


def _calc_pips(entry: float, exit_: float, direction: str, pip_size: float) -> float:
    """Calculate pips for a trade."""
    if direction.upper() == 'BUY':
        return (exit_ - entry) / pip_size
    else:
        return (entry - exit_) / pip_size


def _estimate_pip_value(symbol: str, price: float) -> float:
    """
    Estimate pip value per standard lot.
    
    For USD-quote pairs: $10/pip/lot
    For non-USD pairs: varies, approximate
    """
    if symbol.endswith('USD'):
        return 10.0  # Standard
    elif symbol.endswith('EUR'):
        return 10.0 / price if price else 10.0
    elif symbol.endswith('GBP'):
        return 10.0 * price if price else 10.0
    elif symbol.endswith('CHF'):
        return 10.0 / price if price else 10.0
    elif symbol.endswith('JPY'):
        return 1000.0 / price if price else 10.0
    elif symbol.endswith('CAD'):
        return 10.0 / price if price else 10.0
    elif symbol.endswith('AUD'):
        return 10.0 * price if price else 10.0
    elif symbol.endswith('NZD'):
        return 10.0 * price if price else 10.0
    else:
        return 10.0  # Default


def simulate_all_cycles(
    cycles: List[Dict[str, Any]],
    market_data: Dict[str, Dict[str, pd.DataFrame]],
) -> List[Dict[str, Any]]:
    """
    Run copy trade simulation for all cycles.

    Args:
        cycles: list of enriched cycles (with market_context)
        market_data: {symbol: {tf: DataFrame}}

    Returns:
        List of all simulation results
    """
    all_results = []

    for i, cycle in enumerate(cycles):
        symbol = cycle.get('symbol', '')

        # Get M5 data for this symbol
        sym_data = market_data.get(symbol, {})
        m5_df = sym_data.get('M5')

        if m5_df is None or m5_df.empty:
            logger.warning(f"Cycle {i}: No M5 data for {symbol}, skipping copy sim")
            continue

        try:
            results = simulate_copy_trade(cycle, m5_df)
            all_results.extend(results)
        except Exception as e:
            logger.error(f"Copy sim failed for cycle {i}: {e}")

    return all_results


def generate_copy_trade_summary(sim_results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Generate summary statistics from all copy trade simulations.
    
    Returns per-scenario aggregated stats.
    """
    summary = {}

    # Group by sim_type + wait_pips
    groups = {}
    for r in sim_results:
        key = f"{r['sim_type']}_{r['wait_pips']}"
        if key not in groups:
            groups[key] = []
        groups[key].append(r)

    for key, results in groups.items():
        triggered = [r for r in results if r.get('triggered')]
        not_triggered = [r for r in results if not r.get('triggered')]

        if not triggered:
            summary[key] = {
                'total': len(results),
                'triggered': 0,
                'trigger_rate': 0,
                'avg_profit': None,
                'win_rate': None,
            }
            continue

        profits = [r['sim_profit'] for r in triggered if r.get('sim_profit') is not None]
        wins = [p for p in profits if p > 0]

        summary[key] = {
            'total': len(results),
            'triggered': len(triggered),
            'trigger_rate': round(len(triggered) / len(results) * 100, 1),
            'avg_profit': round(sum(profits) / len(profits), 2) if profits else None,
            'total_profit': round(sum(profits), 2) if profits else None,
            'win_rate': round(len(wins) / len(profits) * 100, 1) if profits else None,
            'avg_pips': round(
                sum(r['sim_profit_pips'] for r in triggered if r.get('sim_profit_pips')) / len(triggered), 2
            ) if triggered else None,
        }

    return summary


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    # Quick test with synthetic data
    dates = pd.date_range('2026-03-15 14:00', periods=288, freq='5min', tz='UTC')
    np.random.seed(42)
    price = 0.68000
    closes = []
    highs = []
    lows = []
    for i in range(288):
        price += np.random.randn() * 0.0002
        closes.append(price)
        highs.append(price + abs(np.random.randn() * 0.0003))
        lows.append(price - abs(np.random.randn() * 0.0003))

    m5 = pd.DataFrame({
        'Open': closes, 'High': highs, 'Low': lows,
        'Close': closes, 'Volume': 100
    }, index=dates)

    test_cycle = {
        'position_key': 'AUDCHF_BUY_test',
        'symbol': 'AUDCHF',
        'direction': 'BUY',
        'open_time': dates[0],
        'close_time': dates[200],
        'holding_time_hours': 16.7,
        'net_profit': 45.20,
        'layer_count': 3,
        'trades': [
            {'layer': 1, 'Open Price': 0.68000, 'Open Time': dates[0], 'Lots': 0.01},
            {'layer': 2, 'Open Price': 0.67700, 'Open Time': dates[50], 'Lots': 0.02},
            {'layer': 3, 'Open Price': 0.67400, 'Open Time': dates[100], 'Lots': 0.04,
             'Close Price': 0.68200, 'Close Time': dates[200]},
        ]
    }

    results = simulate_copy_trade(test_cycle, m5)
    for r in results:
        print(f"{r['sim_type']:15s} | wait={r['wait_pips']:+5.0f} | "
              f"triggered={str(r['triggered']):5s} | "
              f"profit={r.get('sim_profit', 'N/A')}")
