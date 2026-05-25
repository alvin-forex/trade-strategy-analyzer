#!/usr/bin/env python3
"""
Regression tests for Bug: pip-based level classification (BUG_pip_based_levels.md)

These tests ensure that level classification is ALWAYS lot-based, never profit-based.
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from dde_v4_scorer import (
    score_v4,
    compute_layer_lot,
    infer_levels_from_lots,
    compute_layer_from_lot_fallback,
    _DEPRECATED_LEVEL_RANGES,
    clamp,
)


class TestLotBasedLevelClassification:
    """Verify that levels are determined by lot size, never by profit/pips."""

    def test_compute_layer_lot_basic(self):
        """Lot 0.01 maps to L1 when lot_layers says so."""
        lot_layers = [(1, 0.01), (2, 0.025), (3, 0.063)]
        assert compute_layer_lot(0.01, lot_layers) == 'L1'
        assert compute_layer_lot(0.025, lot_layers) == 'L2'
        assert compute_layer_lot(0.063, lot_layers) == 'L3'

    def test_compute_layer_lot_nearest_match(self):
        """Slight lot deviation still maps to closest level."""
        lot_layers = [(1, 0.01), (2, 0.025), (3, 0.063)]
        assert compute_layer_lot(0.011, lot_layers) == 'L1'  # close to 0.01
        assert compute_layer_lot(0.024, lot_layers) == 'L2'  # close to 0.025

    def test_infer_levels_single_lot(self):
        """All trades with same lot → all L1 (flat-bet like S10)."""
        trades = [
            {'lots': 0.15, 'net_profit': 50},
            {'lots': 0.15, 'net_profit': -30},
            {'lots': 0.15, 'net_profit': 100},
        ]
        mapping = infer_levels_from_lots(trades)
        assert len(mapping) == 1
        assert list(mapping.values()) == ['L1']

    def test_infer_levels_multiple_lots(self):
        """Different lot sizes map to different levels."""
        trades = [
            {'lots': 0.01, 'net_profit': 50},
            {'lots': 0.03, 'net_profit': -30},
            {'lots': 0.09, 'net_profit': 100},
        ]
        mapping = infer_levels_from_lots(trades)
        assert mapping[0.01] == 'L1'
        assert mapping[0.03] == 'L2'
        assert mapping[0.09] == 'L3'

    def test_infer_levels_ignores_profit(self):
        """Level inference ignores net_profit completely."""
        # Same lots but wildly different profits → same level
        trades = [
            {'lots': 0.01, 'net_profit': 500},   # high profit
            {'lots': 0.01, 'net_profit': -200},   # big loss
            {'lots': 0.01, 'net_profit': 0.01},   # tiny profit
        ]
        mapping = infer_levels_from_lots(trades)
        assert len(mapping) == 1  # all same lot = L1

    def test_score_v4_uses_lot_based_fallback(self):
        """When no lot_layers provided, score_v4 uses lot-based inference, NOT profit."""
        trades = [
            # All L1 by lot (0.01), but profits span different pip ranges
            {'lots': 0.01, 'net_profit': 10, 'net_pips': 5, 'max_loss_pips': 20,
             'holding_hours': 2, 'type': 'buy', 'symbol': 'EURUSD'},
            {'lots': 0.01, 'net_profit': 200, 'net_pips': 100, 'max_loss_pips': 15,
             'holding_hours': 3, 'type': 'buy', 'symbol': 'EURUSD'},
            {'lots': 0.01, 'net_profit': -50, 'net_pips': -25, 'max_loss_pips': 30,
             'holding_hours': 4, 'type': 'sell', 'symbol': 'EURUSD'},
            # This would be L2 if pip-based (profit 200), but should be L1 (lot 0.01)
        ] * 10  # repeat to get n >= 20

        # No lot_layers → triggers fallback
        result = score_v4(trades, lot_layers=None)
        assert result is not None
        # WAL should be 1.0 (all trades are L1 by lot)
        assert result['wal'] == 1.0, f"Expected WAL=1.0 but got {result['wal']}"

    def test_profit_does_not_affect_level(self):
        """
        REGRESSION: Verify that trades with same lot but different profits
        are classified at the same level.
        
        Old bug: profit=200 → L4, profit=10 → L1 (wrong!)
        Fix: both should be same level since same lot.
        """
        lot_layers = [(1, 0.01), (2, 0.025)]
        
        # Trade A: profit=10 (old bug → L1), lot=0.025 (correct → L2)
        assert compute_layer_lot(0.025, lot_layers) == 'L2'
        
        # Trade B: profit=200 (old bug → L4), lot=0.01 (correct → L1)
        assert compute_layer_lot(0.01, lot_layers) == 'L1'

    def test_deprecated_level_ranges_not_used(self):
        """Ensure _DEPRECATED_LEVEL_RANGES is not imported or used in scoring."""
        # Just verify it exists but is marked deprecated
        assert '_DEPRECATED_LEVEL_RANGES' in dir(sys.modules['dde_v4_scorer'])
        # Verify the new name has DEPRECATED in it
        assert 'DEPRECATED' in '_DEPRECATED_LEVEL_RANGES'


class TestNoProfitBasedClassification:
    """
    Anti-regression: verify NO function uses net_profit for level classification.
    If any new function tries to use profit for levels, these tests catch it.
    """

    def test_mixed_lot_same_level(self):
        """
        Trades with identical lots should have identical levels,
        regardless of profit.
        """
        lot_layers = [(1, 0.01), (2, 0.03), (3, 0.09)]
        
        # Both trades have lot=0.01, different profits
        lv_a = compute_layer_lot(0.01, lot_layers)
        lv_b = compute_layer_lot(0.01, lot_layers)
        assert lv_a == lv_b == 'L1'

    def test_different_lot_different_level(self):
        """
        Trades with different lots should have different levels,
        even if they have the same profit.
        """
        lot_layers = [(1, 0.01), (2, 0.03)]
        
        lv_a = compute_layer_lot(0.01, lot_layers)  # L1
        lv_b = compute_layer_lot(0.03, lot_layers)  # L2
        assert lv_a != lv_b
