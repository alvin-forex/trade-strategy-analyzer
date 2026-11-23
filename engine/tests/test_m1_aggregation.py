"""Tests for M1 single-source aggregation (``engine/m1_aggregation.py``).

Two layers:
  * synthetic bars -- exact expectations, so a wrong fold rule fails loudly;
  * live MT4 ``.hst`` files -- M1 folded to H1 compared against the broker's
    own H1 series. That comparison is the whole point of the architecture
    decision, so it is asserted rather than eyeballed (skipped when the terminal
    history is not present on this machine).
"""

from __future__ import annotations

import os
import unittest

from engine.bar import Bar
from engine.m1_aggregation import (
    Aggregation,
    aggregate,
    aggregate_hst,
    bucket_epoch,
    bucket_label,
    cross_check,
    timeframe_minutes,
    usable_buckets,
)

MT4_HISTORY = (
    r"C:\Users\alvin\AppData\Roaming\MetaQuotes\Terminal"
    r"\50CA3DFB510CC5A8F28B48D1BF2A5702\history\Alpari-Pro.ECN-Demo"
)
HAVE_HISTORY = os.path.isdir(MT4_HISTORY)


def _m1(labels, ohlc):
    return [
        Bar(time_label=t, open=o, high=h, low=l, close=c, tick_volume=1)
        for t, (o, h, l, c) in zip(labels, ohlc)
    ]


class TestTimeframeMinutes(unittest.TestCase):
    def test_known_timeframes(self):
        self.assertEqual(timeframe_minutes("M1"), 1)
        self.assertEqual(timeframe_minutes("M5"), 5)
        self.assertEqual(timeframe_minutes("H1"), 60)
        self.assertEqual(timeframe_minutes("D1"), 1440)

    def test_lowercase_is_accepted(self):
        self.assertEqual(timeframe_minutes("h4"), 240)

    def test_unknown_timeframe_raises(self):
        with self.assertRaises(ValueError) as ctx:
            timeframe_minutes("W1")
        self.assertIn("W1", str(ctx.exception))


class TestBucketBoundary(unittest.TestCase):
    def test_floor_is_exact_multiple(self):
        # 2026-11-17T18:34 server time
        epoch = 1794940440
        self.assertEqual(bucket_epoch(epoch, 60) % 3600, 0)
        self.assertEqual(bucket_epoch(epoch, 1440) % 86400, 0)

    def test_floor_never_moves_forward(self):
        epoch = 1794940440
        for minutes in (5, 15, 30, 60, 240, 1440):
            self.assertLessEqual(bucket_epoch(epoch, minutes), epoch)

    def test_zero_minutes_rejected(self):
        with self.assertRaises(ValueError):
            bucket_epoch(1794940440, 0)

    def test_label_round_trip(self):
        label = bucket_label(1794940440 - 1794940440 % 3600)
        self.assertEqual(label, "2026-11-17T18:00")


class TestAggregateSynthetic(unittest.TestCase):
    def test_h1_folds_open_high_low_close_volume(self):
        labels = [f"2026-11-17T18:{m:02d}" for m in range(60)]
        ohlc = [(1.10000 + i * 1e-5, 1.10100 + i * 1e-5, 1.09900 + i * 1e-5, 1.10050 + i * 1e-5)
                for i in range(60)]
        agg = aggregate(_m1(labels, ohlc), "H1")
        self.assertEqual(len(agg.bars), 1)
        bar = agg.bars[0]
        self.assertEqual(bar.time_label, "2026-11-17T18:00")
        self.assertAlmostEqual(bar.open, ohlc[0][0])
        self.assertAlmostEqual(bar.high, max(x[1] for x in ohlc))
        self.assertAlmostEqual(bar.low, min(x[2] for x in ohlc))
        self.assertAlmostEqual(bar.close, ohlc[-1][3])
        self.assertEqual(bar.tick_volume, 60)
        self.assertEqual(agg.counts[1794940440 - 1794940440 % 3600], 60)

    def test_split_across_two_buckets(self):
        labels = ([f"2026-11-17T18:{m:02d}" for m in range(60)]
                  + [f"2026-11-17T19:{m:02d}" for m in range(60)])
        ohlc = [(1.1 + i * 1e-5,) * 4 for i in range(120)]
        agg = aggregate(_m1(labels, ohlc), "H1")
        self.assertEqual(len(agg.bars), 2)
        self.assertEqual(agg.bars[0].close, ohlc[59][0])
        self.assertEqual(agg.bars[1].open, ohlc[60][0])
        self.assertEqual([agg.counts[b] for b in sorted(agg.counts)], [60, 60])

    def test_unordered_input_still_uses_label_order(self):
        labels = ["2026-11-17T18:10", "2026-11-17T18:00", "2026-11-17T18:05"]
        ohlc = [(1.1005,) * 4, (1.1000,) * 4, (1.1002,) * 4]
        agg = aggregate(_m1(labels, ohlc), "H1")
        self.assertEqual(len(agg.bars), 1)
        self.assertAlmostEqual(agg.bars[0].open, 1.1000)   # 18:00 wins
        self.assertAlmostEqual(agg.bars[0].close, 1.1005)  # 18:10 wins
        self.assertEqual(agg.counts[list(agg.counts)[0]], 3)

    def test_m1_is_passthrough_and_sorted(self):
        labels = ["2026-11-17T18:05", "2026-11-17T18:00"]
        ohlc = [(1.1,) * 4, (1.2,) * 4]
        agg = aggregate(_m1(labels, ohlc), "M1")
        self.assertEqual([b.time_label for b in agg.bars], ["2026-11-17T18:00", "2026-11-17T18:05"])

    def test_d1_bucket_is_server_midnight(self):
        labels = [f"2026-11-17T{h:02d}:{m:02d}" for h in range(24) for m in range(60)]
        ohlc = [(1.1 + i * 1e-6,) * 4 for i in range(len(labels))]
        agg = aggregate(_m1(labels, ohlc), "D1")
        self.assertEqual(len(agg.bars), 1)
        self.assertEqual(agg.bars[0].time_label, "2026-11-17T00:00")
        self.assertEqual(agg.counts[list(agg.counts)[0]], 1440)

    def test_empty_input(self):
        agg = aggregate([], "H1")
        self.assertEqual(agg.bars, [])
        self.assertEqual(agg.counts, {})

    def test_expected_is_bucket_minutes(self):
        self.assertEqual(aggregate([], "H4").expected, 240)


class TestUsableBuckets(unittest.TestCase):
    def test_edge_partial_buckets_dropped(self):
        labels = ([f"2026-11-17T18:{m:02d}" for m in range(10)]  # partial: 10/60
                  + [f"2026-11-17T19:{m:02d}" for m in range(60)]
                  + [f"2026-11-17T20:{m:02d}" for m in range(5)])   # partial: 5/60
        ohlc = [(1.1,) * 4] * 75
        agg = aggregate(_m1(labels, ohlc), "H1")
        kept = usable_buckets(agg)
        self.assertEqual([b.time_label for b in kept], ["2026-11-17T19:00"])

    def test_interior_short_bucket_is_kept(self):
        labels = ([f"2026-11-17T18:{m:02d}" for m in range(60)]
                  + [f"2026-11-17T19:{m:02d}" for m in range(10)]   # interior, weekend-like
                  + [f"2026-11-17T20:{m:02d}" for m in range(60)])
        ohlc = [(1.1,) * 4] * 130
        agg = aggregate(_m1(labels, ohlc), "H1")
        self.assertEqual(len(usable_buckets(agg)), 3)

    def test_empty_aggregation(self):
        self.assertEqual(usable_buckets(aggregate([], "H1")), [])


class TestCrossCheck(unittest.TestCase):
    def test_identical_series_all_exact(self):
        bars = [Bar(f"2026-11-17T{h:02d}:00", 1.1, 1.2, 1.0, 1.15) for h in range(3)]
        agg = Aggregation(tf="H1", bars=bars, counts={})
        common, exact, mism = cross_check(agg, bars)
        self.assertEqual((common, exact, mism), (3, 3, []))

    def test_missing_reference_buckets_are_not_errors(self):
        bars = [Bar(f"2026-11-17T{h:02d}:00", 1.1, 1.2, 1.0, 1.15) for h in range(5)]
        ref = bars[:2]
        agg = Aggregation(tf="H1", bars=bars, counts={})
        common, exact, mism = cross_check(agg, ref)
        self.assertEqual((common, exact, mism), (2, 2, []))

    def test_high_mismatch_is_reported_with_field(self):
        b = Bar("2026-11-17T18:00", 1.1, 1.2, 1.0, 1.15)
        ref = Bar("2026-11-17T18:00", 1.1, 1.25, 1.0, 1.15)
        agg = Aggregation(tf="H1", bars=[b], counts={})
        common, exact, mism = cross_check(agg, [ref])
        self.assertEqual(common, 1)
        self.assertEqual(exact, 0)
        self.assertEqual(mism, [("2026-11-17T18:00", "high")])


@unittest.skipUnless(HAVE_HISTORY, "MT4 terminal history not present on this machine")
class TestAgainstBrokerSeries(unittest.TestCase):
    """The architecture claim itself: M1 folded up must equal the broker's own TF."""

    def test_m1_to_h1_matches_reference_h1(self):
        from engine.martingale.hst_reader import read_hst
        from datetime import datetime, timezone

        agg = aggregate_hst(os.path.join(MT4_HISTORY, "EURUSD1.hst"), "H1")
        ref = [
            Bar(datetime.fromtimestamp(r.epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M"),
                r.open, r.high, r.low, r.close, r.tick_volume)
            for r in read_hst(os.path.join(MT4_HISTORY, "EURUSD60.hst"))
        ]
        # Only the buckets whose M1 fold is complete can be expected to match:
        # the M1 file starts and ends mid-bucket.
        kept = usable_buckets(agg)
        self.assertGreater(len(kept), 20, "M1 window too short to assert anything")
        common, exact, mism = cross_check(Aggregation("H1", kept, agg.counts), ref)
        self.assertEqual(common, len(kept))
        self.assertEqual(exact, common, f"mismatches: {mism[:5]}")
        self.assertEqual(mism, [])

    def test_partial_edge_buckets_are_the_only_mismatches(self):
        from engine.martingale.hst_reader import read_hst
        from datetime import datetime, timezone

        agg = aggregate_hst(os.path.join(MT4_HISTORY, "EURUSD1.hst"), "H1")
        ref = [
            Bar(datetime.fromtimestamp(r.epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M"),
                r.open, r.high, r.low, r.close, r.tick_volume)
            for r in read_hst(os.path.join(MT4_HISTORY, "EURUSD60.hst"))
        ]
        common, exact, mism = cross_check(agg, ref)
        self.assertGreater(common, 20)
        self.assertEqual(len(mism), common - exact)
        # Every mismatch must be an edge bucket; a mismatch in the middle would
        # mean the fold rule itself is wrong.
        labels = [m[0] for m in mism]
        allowed = {agg.bars[0].time_label, agg.bars[-1].time_label}
        self.assertEqual(set(labels) - allowed, set(), f"interior mismatch: {set(labels) - allowed}")

    def test_every_pair_with_a_reference_tf_matches(self):
        """Sweep the whole terminal history, not one hand-picked symbol.

        For every pair that has both an M1 file and a higher-TF file, the M1
        fold must reproduce the broker's own bars exactly. H4 is the one
        timeframe whose file is stale (ends 2026-11-17 16:00 while M1 starts
        18:34), so H4 legitimately has no overlapping complete bucket; that case
        is asserted rather than hidden.
        """
        import glob

        from datetime import datetime, timezone

        from engine.martingale.hst_reader import read_hst

        codes = {"H1": "60", "H4": "240", "D1": "1440"}
        pairs = sorted(
            os.path.basename(p)[:-5] for p in glob.glob(os.path.join(MT4_HISTORY, "*1.hst"))
        )
        self.assertGreater(len(pairs), 20, "terminal history looks empty")

        checked = 0
        no_overlap = []
        for sym in pairs:
            for tf, code in codes.items():
                ref_path = os.path.join(MT4_HISTORY, sym + code + ".hst")
                if not os.path.exists(ref_path):
                    continue
                agg = aggregate_hst(os.path.join(MT4_HISTORY, sym + "1.hst"), tf)
                kept = usable_buckets(agg)
                ref = [
                    Bar(datetime.fromtimestamp(r.epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M"),
                        r.open, r.high, r.low, r.close, r.tick_volume)
                    for r in read_hst(ref_path)
                ]
                common, exact, mism = cross_check(Aggregation(tf, kept, agg.counts), ref)
                if common == 0:
                    no_overlap.append((sym, tf))
                    continue
                self.assertEqual(exact, common, f"{sym} {tf}: {mism[:3]}")
                checked += 1

        self.assertGreater(checked, 40, f"only {checked} (pair,TF) combinations verified")
        # The stale H4 files are the only expected no-overlap case.
        self.assertEqual({tf for _s, tf in no_overlap} - {"H4"}, set(),
                         f"unexpected no-overlap: {no_overlap}")


if __name__ == "__main__":
    unittest.main()
