"""Tests for the CCY-power signal engine (``engine/ccy_signal.py``).

The point of these tests is not coverage theatre: the module decides trade
direction, so the two things that must never silently break are

  * **no lookahead** — a band or ATR at bar ``i`` may only use bars ``< i``;
  * **bounded ladders** — ``MODE_FORWARD`` must stop at ``max_layers`` and on
    revert, never run away.

Both are asserted directly against synthetic bars whose expected answers can be
worked out by hand.
"""

from __future__ import annotations

import unittest

from engine.bar import Bar
from engine.ccy_signal import (
    Layer,
    atr,
    fake_breaks,
    forward_ladder_allowed,
    pivots,
    plan_confirm,
    plan_forward,
    power_agrees,
    residuals,
    rolling_quantile,
    true_ranges,
)


def _bar(t, o, h, l, c):
    return Bar(time_label=t, open=o, high=h, low=l, close=c, tick_volume=1)


def _flat(n, price=1.0, prefix="2026-01-01T"):
    """``n`` identical bars, distinct labels."""
    return [
        _bar("%s%02d:00" % (prefix, i), price, price, price, price) for i in range(n)
    ]


class TestTrueRangeAndAtr(unittest.TestCase):
    def test_first_bar_has_no_true_range(self):
        bars = [_bar("t0", 1.0, 1.1, 0.9, 1.0), _bar("t1", 1.0, 1.2, 1.0, 1.1)]
        tr = true_ranges(bars)
        self.assertIsNone(tr[0])
        self.assertAlmostEqual(tr[1], max(0.2, abs(1.2 - 1.0), abs(1.0 - 1.0)))

    def test_atr_warmup_is_none(self):
        bars = _flat(20)
        series = atr(bars, period=14)
        self.assertTrue(all(x is None for x in series[:14]))
        self.assertIsNotNone(series[14])

    def test_atr_flat_market_is_zero(self):
        bars = _flat(30, price=1.0)
        series = atr(bars, period=14)
        self.assertAlmostEqual(series[14], 0.0)
        self.assertAlmostEqual(series[-1], 0.0)

    def test_atr_tracks_wilder_recursion(self):
        bars = [_bar("t%d" % i, 1.0, 1.1, 0.9, 1.0) for i in range(20)]
        series = atr(bars, period=14)
        # Every true range after the first is 0.2, so ATR settles at 0.2.
        self.assertAlmostEqual(series[14], 0.2)
        self.assertAlmostEqual(series[-1], 0.2)


class TestPivots(unittest.TestCase):
    def test_single_swing_high_and_low(self):
        bars = [
            _bar("t0", 1.0, 1.0, 0.95, 1.0),
            _bar("t1", 1.0, 1.01, 0.99, 1.0),
            _bar("t2", 1.0, 1.05, 1.0, 1.02),  # swing high
            _bar("t3", 1.0, 1.01, 0.99, 1.0),
            _bar("t4", 1.0, 1.0, 0.90, 1.0),  # swing low
            _bar("t5", 1.0, 1.01, 0.99, 1.0),
            _bar("t6", 1.0, 1.01, 0.99, 1.0),
        ]
        got = pivots(bars, k=1)
        self.assertIn((2, 1.05, "R"), got)
        self.assertIn((4, 0.90, "S"), got)

    def test_flat_market_yields_nothing_misleading(self):
        # Constant bars: every bar ties for both extremes, so a pivot list may
        # contain them, but no fake break may be produced from ties.
        bars = _flat(10)
        for _i, _lv, _kind in pivots(bars, k=1):
            pass  # existence is fine; the break test below is what matters
        self.assertEqual(fake_breaks(bars, atr(bars, 14), k=1), [])

    def test_k_validation(self):
        with self.assertRaises(ValueError):
            pivots(_flat(5), k=0)


class TestFakeBreaks(unittest.TestCase):
    def _series(self):
        # Build: swing high at 1.05, then a bar that pokes above it and closes
        # back below => faked resistance.
        bars = [
            _bar("t0", 1.00, 1.00, 0.99, 1.00),
            _bar("t1", 1.00, 1.05, 1.00, 1.04),  # pivot high
            _bar("t2", 1.02, 1.04, 1.01, 1.03),
            _bar("t3", 1.03, 1.20, 1.02, 1.02),  # poke to 1.20, close 1.02 < 1.05
            _bar("t4", 1.02, 1.03, 1.00, 1.01),
        ]
        return bars

    def test_faked_resistance_is_detected(self):
        bars = self._series()
        atr_s = atr(bars, period=2)
        got = fake_breaks(bars, atr_s, k=1, atr_tol=0.10, lookback=10)
        self.assertTrue(any(kind == "R" and idx == 3 for idx, _lv, kind in got), got)

    def test_break_requires_close_back(self):
        # Same poke but the bar *closes* above the level: not a fake break.
        bars = [
            _bar("t0", 1.00, 1.00, 0.99, 1.00),
            _bar("t1", 1.00, 1.05, 1.00, 1.04),
            _bar("t2", 1.02, 1.04, 1.01, 1.03),
            _bar("t3", 1.03, 1.20, 1.02, 1.15),  # closes well above 1.05
            _bar("t4", 1.15, 1.16, 1.14, 1.15),
        ]
        got = fake_breaks(bars, atr(bars, 2), k=1, atr_tol=0.10, lookback=10)
        self.assertEqual([g for g in got if g[0] == 3], [])

    def test_pivot_never_acts_before_confirmation(self):
        """A pivot at index p can only produce a signal at index >= p + k."""
        bars = self._series()
        k = 1
        for idx, _lv, _kind in fake_breaks(bars, atr(bars, 2), k=k, lookback=10):
            self.assertGreaterEqual(idx, 1 + k)


class TestPowerAgrees(unittest.TestCase):
    def test_long_needs_both_positive(self):
        self.assertTrue(power_agrees(0.5, 0.1, 1))
        self.assertFalse(power_agrees(0.5, -0.1, 1))
        self.assertFalse(power_agrees(-0.5, 0.1, 1))

    def test_short_needs_both_negative(self):
        self.assertTrue(power_agrees(-0.5, -0.1, -1))
        self.assertFalse(power_agrees(-0.5, 0.1, -1))


class TestResiduals(unittest.TestCase):
    def test_missing_power_yields_none_not_zero(self):
        bars = [
            _bar("t0", 1.0, 1.0, 1.0, 1.0),
            _bar("t1", 1.0, 1.0, 1.0, 1.1),
            _bar("t2", 1.0, 1.0, 1.0, 1.2),
        ]
        power = {"t0": {"USD": 8.0, "JPY": 3.0}, "t2": {"USD": 8.5, "JPY": 3.0}}
        got = residuals(bars, power, slope_b=0.1, base_ccy="USD", quote_ccy="JPY")
        self.assertIsNone(got[0])  # no previous spread
        self.assertIsNone(got[1])  # current bar has no power -> must not be 0
        # t2 has power, t1 does not, so prev_spread is None -> still None.
        self.assertIsNone(got[2])

    def test_residual_formula(self):
        bars = [
            _bar("t0", 1.0, 1.0, 1.0, 1.00),
            _bar("t1", 1.0, 1.0, 1.0, 1.10),
        ]
        power = {
            "t0": {"USD": 8.0, "JPY": 3.0},  # spread 5.0
            "t1": {"USD": 8.2, "JPY": 3.0},  # spread 5.2, d_spread = 0.2
        }
        got = residuals(bars, power, slope_b=0.5, base_ccy="USD", quote_ccy="JPY")
        # price change 0.10 - 0.5 * 0.2 = 0.0
        self.assertAlmostEqual(got[1], 0.0)

    def test_currency_absent_yields_none(self):
        bars = [_bar("t0", 1, 1, 1, 1), _bar("t1", 1, 1, 1, 1.1)]
        power = {"t0": {"USD": 8.0}, "t1": {"USD": 8.2}}
        got = residuals(bars, power, slope_b=0.5, base_ccy="USD", quote_ccy="JPY")
        self.assertIsNone(got[1])


class TestRollingQuantile(unittest.TestCase):
    def test_no_lookahead(self):
        """The band at index i must ignore values[i] entirely."""
        vals = [1.0, 2.0, 3.0, 1000.0]
        band = rolling_quantile(vals, 0.5, window=3)
        # index 3 uses [1,2,3] -> median 2.0, unaffected by the 1000.0 at index 3
        self.assertAlmostEqual(band[3], 2.0)

    def test_insufficient_history_is_none(self):
        band = rolling_quantile([1.0], 0.5, window=5)
        self.assertEqual(band, [None])

    def test_none_values_are_skipped(self):
        band = rolling_quantile([None, 1.0, 2.0, 3.0], 0.5, window=4)
        # index 3 sees [None, 1.0, 2.0] -> usable [1.0, 2.0] -> median 1.5
        self.assertAlmostEqual(band[3], 1.5)

    def test_single_usable_value_is_none(self):
        band = rolling_quantile([None, None, 5.0, 6.0], 0.5, window=4)
        # index 3 sees only [5.0] (6.0 is at index 3, excluded) -> None
        self.assertIsNone(band[3])

    def test_argument_validation(self):
        with self.assertRaises(ValueError):
            rolling_quantile([1.0, 2.0], 1.5, window=2)
        with self.assertRaises(ValueError):
            rolling_quantile([1.0, 2.0], 0.5, window=0)

    def test_quantile_interpolates(self):
        band = rolling_quantile([0.0, 10.0, 0.0, 0.0], 0.5, window=3)
        # index 2 sees [0.0, 10.0] -> median 5.0
        self.assertAlmostEqual(band[2], 5.0)


class TestPlanConfirm(unittest.TestCase):
    def test_enters_only_after_revert(self):
        bars = _flat(6)
        resid = [0.0, 5.0, 3.0, 0.0, 0.0, 0.0]
        hi = [10.0] * 6
        lo = [-10.0] * 6
        # index 1 sits in band (5.0 < hi=10) so no anchor at all.
        self.assertEqual(plan_confirm(bars, resid, lo, hi, revert_bars=1), [])

    def test_short_anchor_then_revert_enters(self):
        bars = _flat(6)
        hi = [1.0] * 6
        lo = [-1.0] * 6
        resid = [0.0, 2.0, 2.0, 0.5, 0.0, 0.0]  # anchor idx1, revert idx3
        got = plan_confirm(bars, resid, lo, hi, revert_bars=2)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].index, 3)
        self.assertEqual(got[0].direction, -1)
        self.assertEqual(got[0].layer, 1)

    def test_long_anchor_then_revert_enters(self):
        bars = _flat(6)
        hi = [1.0] * 6
        lo = [-1.0] * 6
        resid = [0.0, -2.0, -2.0, -0.5, 0.0, 0.0]
        got = plan_confirm(bars, resid, lo, hi, revert_bars=2)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0].direction, 1)

    def test_no_revert_no_entry(self):
        bars = _flat(6)
        hi = [1.0] * 6
        lo = [-1.0] * 6
        resid = [0.0, 2.0, 2.5, 3.0, 3.5, 4.0]  # stays extreme
        self.assertEqual(plan_confirm(bars, resid, lo, hi, revert_bars=2), [])


class TestPlanForward(unittest.TestCase):
    def test_ladder_stops_at_max_layers(self):
        bars = _flat(10)
        hi = [1.0] * 10
        lo = [-1.0] * 10
        resid = [2.0] * 10  # never reverts
        got = plan_forward(bars, resid, lo, hi, step_bars=1, max_layers=3)
        self.assertEqual(len(got), 3)
        self.assertEqual([g.layer for g in got], [1, 2, 3])
        self.assertTrue(all(g.direction == -1 for g in got))

    def test_ladder_stops_on_revert(self):
        """A reversion ends *that* ladder; the next excursion is a new one.

        OC 2026-11-24 14:00 §三: "殘差回返即停注" — stop adding on revert —
        and "InpMaxLayers 用盡即斷". The cap is per ladder, so the 5-layer
        budget is reused by the second excursion rather than shared globally.
        """
        bars = _flat(10)
        hi = [1.0] * 10
        lo = [-1.0] * 10
        resid = [2.0, 2.0, 2.0, 0.0, 2.0, 2.0, 2.0, 2.0, 2.0, 2.0]
        got = plan_forward(bars, resid, lo, hi, step_bars=1, max_layers=5)
        # Ladder 1 = idx 0,1,2 (revert at 3); ladder 2 = idx 4..8 (cap 5).
        self.assertEqual([g.index for g in got], [0, 1, 2, 4, 5, 6, 7, 8])
        # Layer numbering restarts inside each ladder.
        self.assertEqual([g.layer for g in got], [1, 2, 3, 1, 2, 3, 4, 5])

    def test_each_ladder_respects_max_layers(self):
        bars = _flat(20)
        hi = [1.0] * 20
        lo = [-1.0] * 20
        resid = [2.0] * 5 + [0.0] * 5 + [2.0] * 10
        got = plan_forward(bars, resid, lo, hi, step_bars=1, max_layers=2)
        self.assertEqual([g.index for g in got], [0, 1, 10, 11])

    def test_step_bars_spacing(self):
        bars = _flat(10)
        hi = [1.0] * 10
        lo = [-1.0] * 10
        resid = [2.0] * 10
        got = plan_forward(bars, resid, lo, hi, step_bars=3, max_layers=3)
        self.assertEqual([g.index for g in got], [0, 3, 6])

    def test_ladder_is_bounded_even_on_long_input(self):
        """A 10,000-bar runaway extreme must not produce 10,000 layers."""
        bars = _flat(10000)
        hi = [1.0] * 10000
        lo = [-1.0] * 10000
        resid = [2.0] * 10000
        got = plan_forward(bars, resid, lo, hi, step_bars=1, max_layers=4)
        self.assertEqual(len(got), 4)

    def test_argument_validation(self):
        bars = _flat(5)
        with self.assertRaises(ValueError):
            plan_forward(bars, [0.0] * 5, [0.0] * 5, [0.0] * 5, step_bars=0, max_layers=1)
        with self.assertRaises(ValueError):
            plan_forward(bars, [0.0] * 5, [0.0] * 5, [0.0] * 5, step_bars=1, max_layers=0)

    def test_index_never_exceeds_input(self):
        bars = _flat(5)
        hi = [1.0] * 5
        lo = [-1.0] * 5
        resid = [2.0] * 5
        for g in plan_forward(bars, resid, lo, hi, step_bars=2, max_layers=10):
            self.assertLess(g.index, len(bars))


class TestGuardRedLine(unittest.TestCase):
    def test_all_three_guards_required(self):
        self.assertTrue(forward_ladder_allowed(True, True, True))
        self.assertFalse(forward_ladder_allowed(True, True, False))
        self.assertFalse(forward_ladder_allowed(True, False, True))
        self.assertFalse(forward_ladder_allowed(False, True, True))
        self.assertFalse(forward_ladder_allowed(False, False, False))


class TestLayerContract(unittest.TestCase):
    def test_layer_is_frozen(self):
        lay = Layer(index=1, direction=1, layer=1)
        with self.assertRaises(Exception):
            lay.index = 2  # type: ignore[misc]


if __name__ == "__main__":
    unittest.main()
