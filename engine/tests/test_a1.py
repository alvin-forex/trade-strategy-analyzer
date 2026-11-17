"""A1 engine tests: determinism, ZigZag/MT4 parity, bucket rounding.

Run: python -m unittest discover -s engine/tests -t .
"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.bar import Bar, load_bars_csv, pip_size, slice_window
from engine.buckets import compute_buckets, percentile_inc, percentile_nearest_rank, split_counts
from engine.merge import build_waves, merge_pivots, merge_pivots_drop_next
from engine.zigzag import zigzag

EVID = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidence", "a1")
BARS = os.path.join(EVID, "mt4_EURUSD_H1_bars.csv")
ZZ = os.path.join(EVID, "mt4_zigzag_dump.csv")


def _synthetic(prices):
    """Bars from a list of highs/lows so swings are unambiguous."""
    return [
        Bar(time_label=f"2026-01-01T{i:02d}:00", open=p, high=p, low=p, close=p)
        for i, p in enumerate(prices)
    ]


class TestPip(unittest.TestCase):
    def test_fractional_pip(self):
        self.assertAlmostEqual(pip_size(1e-5, 5), 1e-4)
        self.assertAlmostEqual(pip_size(1e-3, 3), 1e-2)

    def test_whole_pip(self):
        self.assertAlmostEqual(pip_size(0.01, 2), 0.01)
        self.assertAlmostEqual(pip_size(1e-4, 4), 1e-4)


class TestBucketRounding(unittest.TestCase):
    """Both ground-truth sets must agree; only round-half-up satisfies both."""

    def test_parity_49(self):
        self.assertEqual(split_counts(49), [39, 7, 3])

    def test_manual_53(self):
        self.assertEqual(split_counts(53), [42, 8, 3])

    def test_floor_would_fail_manual(self):
        self.assertEqual(int(0.8 * 53), 42)
        self.assertEqual(int(0.15 * 53), 7)  # floor gives 7, truth is 8
        self.assertNotEqual([int(0.8 * 53), int(0.15 * 53), 53 - int(0.8 * 53) - int(0.15 * 53)], [42, 8, 3])

    def test_percentiles(self):
        data = [10.0, 20.0, 30.0, 40.0]
        self.assertAlmostEqual(percentile_inc(data, 50), 25.0)
        self.assertAlmostEqual(percentile_nearest_rank(data, 50), 20.0)


class TestZigZagSynthetic(unittest.TestCase):
    def test_alternation(self):
        prices = [10, 12, 14, 16, 14, 12, 10, 12, 14, 16, 18, 16, 14, 12, 10, 12, 14, 16]
        piv = zigzag(_synthetic(prices), depth=3, deviation_points=1, backstep=1, point=0.01)
        kinds = [p.kind for p in piv]
        for a, b in zip(kinds, kinds[1:]):
            self.assertNotEqual(a, b, "pivots must alternate H/L")

    def test_backstep_ge_depth_rejected(self):
        with self.assertRaises(ValueError):
            zigzag(_synthetic([1, 2, 3, 4]), depth=3, deviation_points=1, backstep=3, point=0.01)

    def test_too_few_bars(self):
        self.assertEqual(zigzag(_synthetic([1, 2, 3]), depth=12, deviation_points=1, backstep=3, point=0.01), [])


@unittest.skipUnless(os.path.exists(BARS) and os.path.exists(ZZ), "MT4 evidence not present")
class TestParityAgainstMT4(unittest.TestCase):
    """The port must reproduce MT4's own ZigZag output pivot-for-pivot."""

    def test_full_history_matches_mt4(self):
        import csv

        bars = load_bars_csv(BARS)
        piv = zigzag(bars, 12, 5, 3, 1e-5)

        with open(ZZ, "r", encoding="utf-8-sig", newline="") as fh:
            dump = list(csv.DictReader(fh))
        mt4 = {
            r["time"].replace(".", "-").replace(" ", "T"): float(r["zz"])
            for r in dump
            if abs(float(r["zz"])) > 0
        }

        py = {p.time_label: p.price for p in piv}
        common = set(mt4) & set(py)
        self.assertGreaterEqual(len(common), 100, "expected ~121 shared pivots")
        mismatches = [k for k in common if abs(mt4[k] - py[k]) > 1e-9]
        self.assertEqual(mismatches, [], f"price mismatches: {mismatches[:5]}")

        # the only divergence allowed is the still-forming newest bar
        self.assertLessEqual(len(set(mt4) - set(py)), 1)
        self.assertLessEqual(len(set(py) - set(mt4)), 1)

    def test_determinism(self):
        bars = load_bars_csv(BARS)
        a = zigzag(bars, 12, 5, 3, 1e-5)
        b = zigzag(bars, 12, 5, 3, 1e-5)
        self.assertEqual([(p.idx, p.price, p.kind) for p in a], [(p.idx, p.price, p.kind) for p in b])


@unittest.skipUnless(os.path.exists(BARS), "MT4 evidence not present")
class TestWaveBuild(unittest.TestCase):
    def test_waves_are_pivot_pairs(self):
        bars = load_bars_csv(BARS)
        w = slice_window(bars, "2026-09-17T02:00", "2026-11-16T17:00")
        self.assertEqual(len(w), 1023, "target window must contain 1023 H1 bars")
        piv = zigzag(w, 12, 5, 3, 1e-5)
        waves = build_waves(piv, pip_size(1e-5, 5), "exclusive")
        self.assertEqual(len(waves), len(piv) - 1)
        for wave, a, b in zip(waves, piv, piv[1:]):
            self.assertEqual(wave.bars, b.idx - a.idx)
            self.assertAlmostEqual(
                wave.amplitude_pips, round(abs(b.price - a.price) / 1e-4, 2), places=6
            )

    def test_bar_modes_differ_by_one(self):
        bars = load_bars_csv(BARS)
        w = slice_window(bars, "2026-09-17T02:00", "2026-11-16T17:00")
        piv = zigzag(w, 12, 5, 3, 1e-5)
        ex = build_waves(piv, 1e-4, "exclusive")
        inc = build_waves(piv, 1e-4, "inclusive")
        self.assertEqual(sum(x.bars for x in inc), sum(x.bars for x in ex) + len(ex))

    def test_merge_is_monotonic(self):
        bars = load_bars_csv(BARS)
        w = slice_window(bars, "2026-09-17T02:00", "2026-11-16T17:00")
        piv = zigzag(w, 12, 5, 3, 1e-5)
        prev = len(piv)
        for pct in (10, 20, 30, 40, 50, 60):
            cur = len(merge_pivots(piv, float(pct), "post"))
            self.assertLessEqual(cur, prev + 1)  # never grows by more than the seed
            prev = cur

    def test_buckets_sum_to_total(self):
        bars = load_bars_csv(BARS)
        w = slice_window(bars, "2026-09-17T02:00", "2026-11-16T17:00")
        piv = zigzag(w, 12, 5, 3, 1e-5)
        waves = build_waves(merge_pivots(piv, 35.0, "post"), 1e-4, "exclusive")
        stats = compute_buckets([x.amplitude_pips for x in waves], [x.bars for x in waves])
        self.assertEqual(sum(s.count for s in stats), len(waves))
        self.assertEqual(sum(s.total_bars for s in stats), sum(x.bars for x in waves))


@unittest.skipUnless(os.path.exists(BARS), "MT4 evidence not present")
class TestPanelParity(unittest.TestCase):
    """Reproduce the original indicator panel (Alpari, EURUSD H1)."""

    @classmethod
    def setUpClass(cls):
        bars = load_bars_csv(BARS)
        cls.window = slice_window(bars, "2026-09-17T02:00", "2026-11-16T17:00")
        cls.pivots = zigzag(cls.window, 12, 5, 3, 1e-5)
        cls.merged = merge_pivots_drop_next(cls.pivots, 35.0)
        cls.waves = build_waves(cls.merged, 1e-4, "exclusive")

    def test_window_bar_count(self):
        self.assertEqual(len(self.window), 1023)

    def test_total_swings_matches_panel(self):
        self.assertEqual(len(self.waves), 49, "panel reports 49 swings")

    def test_class_counts_match_panel(self):
        stats = compute_buckets(
            [w.amplitude_pips for w in self.waves], [w.bars for w in self.waves]
        )
        self.assertEqual([s.count for s in stats], [39, 7, 3])

    def test_medium_class_matches_panel_exactly(self):
        """The Medium class reproduces all six panel metrics."""
        stats = compute_buckets(
            [w.amplitude_pips for w in self.waves], [w.bars for w in self.waves]
        )
        medium = stats[1]
        self.assertEqual(medium.total_bars, 211)
        self.assertEqual(medium.total_pips, 831.1)
        self.assertEqual(medium.average_bars, 30.1)
        self.assertEqual(medium.longest_bars, 56)
        self.assertEqual(medium.shortest_bars, 11)

    def test_normal_longest_matches_panel(self):
        stats = compute_buckets(
            [w.amplitude_pips for w in self.waves], [w.bars for w in self.waves]
        )
        self.assertEqual(stats[0].longest_bars, 48)

    def test_determinism_of_merge(self):
        again = merge_pivots_drop_next(self.pivots, 35.0)
        self.assertEqual(
            [(p.idx, p.price, p.kind) for p in again],
            [(p.idx, p.price, p.kind) for p in self.merged],
        )


if __name__ == "__main__":
    unittest.main()
