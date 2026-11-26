"""Tests for the #37 clone-panel generator (RED-first, TDD).

Review-driven cases: server/UTC offset, forming bar cut at the truth minute,
minute-level anti-fabrication guard, partial labelling, precision, and the
series/parity loader contract. Synthetic M1 only -- no terminal, no network.
Run: python -m unittest discover -s engine/tests -t . -p test_clone_panel.py
"""

from __future__ import annotations

import datetime as dt
import gzip
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ccy_backtest import series as bt_series

from engine.clone_panel import (
    load_m1_dir, targets_from_truth, build_h1_data, compute_clone_panels,
    write_clone_csv, display_scale, clone_meta, MissingM1Error,
    TargetOutsideM1Error, DEFAULT_SERVER_OFFSET_HOURS,
)

UTC = dt.timezone.utc
EPOCH = 1764153600  # 2025-11-26 10:40 UTC (verified) => server 12:40 at +2h
OFFSET = DEFAULT_SERVER_OFFSET_HOURS


def utc(e: int) -> dt.datetime:
    return dt.datetime.fromtimestamp(e, UTC)


def truth_stamp(e_utc: int) -> str:
    """UTC epoch -> MT4 server-time truth string."""
    return (utc(e_utc) + dt.timedelta(hours=OFFSET)).strftime("%Y.%m.%d %H:%M")


def write_m1_gz(path: str, symbol: str, n: int = 3000, start: int = EPOCH) -> None:
    rows = ["time,iso_utc,open,high,low,close"]
    for i in range(n):
        e = start + i * 60
        base = 1.10 + 0.0002 * (i % 40)
        rows.append(f"{e},{utc(e):%Y-%m-%d %H:%M},{base:.5f},{base + 0.0003:.5f},"
                    f"{base - 0.0003:.5f},{base + 0.0001:.5f}")
    with gzip.open(path, "wt", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(rows) + "\n")


class DisplayScaleTests(unittest.TestCase):
    def test_oc_candidate_endpoints_and_precision(self):
        self.assertAlmostEqual(display_scale(-50), 0.0, places=9)
        self.assertAlmostEqual(display_scale(0), 4.5, places=9)
        self.assertAlmostEqual(display_scale(50), 9.0, places=9)
        # No premature 2dp rounding: a 0.001 change must survive the 1e-4 gate.
        self.assertAlmostEqual(display_scale(1.011), display_scale(1.010) + 0.00009,
                               places=9)

    def test_none_propagates(self):
        self.assertIsNone(display_scale(None))


class LoadM1Tests(unittest.TestCase):
    def test_loads_gz_dump(self):
        with tempfile.TemporaryDirectory() as d:
            write_m1_gz(os.path.join(d, "EURUSD_M1_60d.csv.gz"), "EURUSD", n=120)
            data = load_m1_dir(d)
            self.assertIn("EURUSD", data)
            self.assertEqual(len(data["EURUSD"]), 120)
            self.assertEqual(data["EURUSD"][0][0], EPOCH)

    def test_missing_dir_is_error(self):
        with self.assertRaises(FileNotFoundError):
            load_m1_dir(os.path.join(tempfile.gettempdir(), "no_such_m1_dir_xyz"))


class OffsetTests(unittest.TestCase):
    def test_truth_server_time_maps_to_utc(self):
        from engine.clone_panel import _truth_epoch
        e_utc = EPOCH + 150 * 60  # 13:10 UTC
        self.assertEqual(_truth_epoch(truth_stamp(e_utc)), e_utc)
        self.assertEqual(_truth_epoch(truth_stamp(e_utc), 3), e_utc - 3600)


class TargetTests(unittest.TestCase):
    def test_targets_from_truth(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "truth.csv")
            with open(p, "w", encoding="utf-8") as fh:
                fh.write("time,tf,EUR,USD\n")
                fh.write("2026.11.26 15:36,H1,7.13,5.50\n")
                fh.write("2026.11.26 15:41,H1,7.00,5.50\n")
            self.assertEqual(targets_from_truth(p),
                             [("2026.11.26 15:36", "H1"),
                              ("2026.11.26 15:41", "H1")])


class BuildDataTests(unittest.TestCase):
    def test_forming_bar_close_is_cut_at_truth_minute_not_hour_end(self):
        series = [(EPOCH + i * 60, 1.10, 1.11, 1.09, 1.10 + i * 0.00001)
                  for i in range(1200)]
        # Target near end of the series: enough H1 warm-up before it.
        e_target = EPOCH + 1190 * 60
        data = build_h1_data(series, truth_stamp(e_target))
        self.assertEqual(data["d"][-1], truth_stamp(e_target).replace(".", "-").replace(" ", "T"))
        expected_close = 1.10 + 1190 * 0.00001
        self.assertAlmostEqual(data["c"][-1], expected_close, places=9)
        self.assertGreater(len(data["d"]), 14)  # warm-up present

    def test_two_targets_in_same_hour_get_different_forming_values(self):
        series = [(EPOCH + i * 60, 1.10, 1.11, 1.09, 1.10 + i * 0.00001)
                  for i in range(1200)]
        e1, e2 = EPOCH + 150 * 60, EPOCH + 155 * 60  # same H1 bucket, 5 min apart
        d1 = build_h1_data(series, truth_stamp(e1))
        d2 = build_h1_data(series, truth_stamp(e2))
        self.assertNotAlmostEqual(d1["c"][-1], d2["c"][-1], places=9)


class AntiFabricationTests(unittest.TestCase):
    def test_target_past_last_m1_bar_same_bucket_refused(self):
        series = [(EPOCH + i * 60, 1.10, 1.11, 1.09, 1.105) for i in range(20)]
        # dump ends at EPOCH+19min, target 3 min later in the SAME H1 bucket
        with self.assertRaises(TargetOutsideM1Error):
            build_h1_data(series, truth_stamp(EPOCH + 22 * 60))

    def test_target_before_first_m1_bar_refused(self):
        series = [(EPOCH + i * 60, 1.10, 1.11, 1.09, 1.105) for i in range(20)]
        with self.assertRaises(TargetOutsideM1Error):
            build_h1_data(series, truth_stamp(EPOCH - 30 * 60))


class ClonePanelTests(unittest.TestCase):
    def test_compute_write_and_loader_contract(self):
        with tempfile.TemporaryDirectory() as d:
            for sym in ("EURUSD", "USDJPY", "XAUUSD"):
                write_m1_gz(os.path.join(d, f"{sym}_M1_60d.csv.gz"), sym, n=3000)
            e_target = EPOCH + 2900 * 60
            target = truth_stamp(e_target)
            panels = compute_clone_panels(d, [(target, "H1")])
            self.assertIn(target, panels)
            self.assertEqual(set(panels[target]), {"EUR", "USD", "JPY", "XAU"})
            self.assertTrue(all(0 <= v <= 9 for v in panels[target].values()))
            out = os.path.join(d, "clone.csv")
            write_clone_csv(panels, out)
            rows = bt_series.read_cp_power_history(out)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["ts"], target)
            self.assertEqual(rows[0]["tf"], "H1")
            self.assertIsNotNone(rows[0]["power"]["EUR"])
            with open(out + ".meta.json", encoding="utf-8") as fh:
                meta = json.load(fh)
            self.assertEqual(meta["coverage"], "partial 3/36")
            for have in ("EURUSD", "USDJPY", "XAUUSD"):
                self.assertNotIn(have, meta["missing_instruments"])
            self.assertIn("partial", meta["note"].lower())

    def test_missing_symbol_reported_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            target = truth_stamp(EPOCH + 2900 * 60)
            with self.assertRaises(MissingM1Error):
                compute_clone_panels(d, [(target, "H1")], symbols=("EURUSD",))

    def test_real_m1_dump_with_26nov_truth_is_refused_not_faked(self):
        truth = (r"C:\Users\alvin\tsa-work\exchange\from_autoclaw"
                 r"\20261126_2140_[AC]Scanner對拍真值_首批H1\panel_truth_H1_last20.csv")
        m1 = (r"C:\Users\alvin\tsa-work\exchange\from_autoclaw"
              r"\20261124_0930_[AC]M1dump")
        if not (os.path.exists(truth) and os.path.isdir(m1)):
            self.skipTest("real AC supply not present in this checkout")
        targets = targets_from_truth(truth)[:1]
        with self.assertRaises(TargetOutsideM1Error):
            compute_clone_panels(m1, targets)


if __name__ == "__main__":
    unittest.main()
