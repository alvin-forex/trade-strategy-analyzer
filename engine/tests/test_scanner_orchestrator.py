"""Tests for the 29x6 Scanner orchestrator and the api.py range fetch fix.

All bars are synthetic, so the suite needs no MT5 terminal and no downloads
tree. Run: python -m unittest discover -s engine/tests -t .
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine import api
from engine.bar import Bar
from engine.martingale import fit
from engine.martingale.ingest import Trade
from engine.martingale import scanner_orchestrator as so


def series(n: int = 1600, base: float = 1.2000, swing: float = 0.0200) -> list[Bar]:
    """A deterministic zig-zag-ish series with confirmed pivots every 25 bars."""
    bars = []
    for i in range(n):
        v = base + swing * ((i % 50) / 50.0) + 0.00002 * (i % 7)
        bars.append(
            Bar(
                time_label=f"2024-01-{1 + i // 1440:02d}T{(i // 60) % 24:02d}:{i % 60:02d}",
                open=v,
                high=v + 0.0003,
                low=v - 0.0003,
                close=v,
                tick_volume=100,
            )
        )
    return bars


def trade(symbol: str, direction: str = "buy") -> Trade:
    return Trade(
        symbol=symbol,
        direction=direction,
        lots=0.01,
        open_price=1.2,
        open_time=None,
        close_time=None,
        net_profit=1.0,
        net_pips=10.0,
        max_profit=1.0,
        max_pips=10.0,
        max_loss=-1.0,
        max_loss_pips=-10.0,
        magic="0",
        comment="",
    )


class TestDefaults(unittest.TestCase):
    def test_29_pairs_and_6_tfs(self):
        self.assertEqual(len(so.DEFAULT_PAIRS), 29)
        self.assertEqual(len(set(so.DEFAULT_PAIRS)), 29)
        self.assertIn("XAUUSD", so.DEFAULT_PAIRS)
        self.assertEqual(
            so.DEFAULT_TFS, ("M5", "M15", "M30", "H1", "H4", "D1")
        )
        self.assertNotIn("M1", so.DEFAULT_TFS)
        self.assertNotIn("W1", so.DEFAULT_TFS)

    def test_signal_grades_come_from_fit(self):
        self.assertEqual(
            so.SIGNAL_GRADES, {fit.GRADE_TIGHT, fit.GRADE_WIDE}
        )


class TestScanMatrix(unittest.TestCase):
    def test_rows_are_cartesian_and_isolated(self):
        bars = series()
        calls = []

        def loader(symbol, tf):
            calls.append((symbol, tf))
            if symbol == "BAD" and tf == "H4":
                raise RuntimeError("boom")
            if tf == "M5":
                return []
            return bars

        result = so.scan_matrix(
            ["EURUSD", "BAD"], ("M5", "H4"),
            default_step_pips=15.0,
            bars_loader=loader,
        )
        self.assertEqual(len(result.rows), 4)
        self.assertEqual(len(calls), 4)
        # Row order is pair-outer, tf-inner:
        #   0 EURUSD/M5 -> empty; 1 EURUSD/H4 -> OK;
        #   2 BAD/M5 -> empty;     3 BAD/H4 -> raises -> UNUSABLE.
        self.assertEqual([r.verdict for r in result.rows],
                         [so.VERDICT_NO_DATA, so.VERDICT_OK,
                          so.VERDICT_NO_DATA, so.VERDICT_UNUSABLE])
        self.assertIn("boom", result.errors[-1]["reason"])

    def test_no_step_marks_no_step_not_unusable(self):
        result = so.scan_matrix(
            ["EURUSD"], ["H1"],
            default_step_pips=None,
            bars_loader=lambda s, t: series(200),
        )
        self.assertEqual(result.rows[0].verdict, so.VERDICT_NO_STEP)
        self.assertIsNone(result.rows[0].ratio)

    def test_signal_list_is_filtered_view(self):
        # A very tight step should grade 'tight' and become a signal.
        result = so.scan_matrix(
            ["EURUSD"], ["H1"],
            default_step_pips=0.5,
            bars_loader=lambda s, t: series(),
        )
        row = result.rows[0]
        self.assertEqual(row.verdict, so.VERDICT_OK)
        self.assertEqual(row.grade, fit.GRADE_TIGHT)
        self.assertTrue(row.is_signal)
        self.assertEqual(result.signals, [row])

    def test_cycles_reuse_existing_scanner(self):
        trades = [trade("EURUSD"), trade("EURUSD", "sell")]
        result = so.scan_matrix(
            ["EURUSD"], ["H1"],
            default_step_pips=15.0,
            bars_loader=lambda s, t: series(),
            trade_loader=lambda s: trades,
        )
        # scan_symbol splits by direction: 2 cycles (one per direction).
        self.assertEqual(result.rows[0].cycles, 2)
        self.assertEqual(result.rows[0].trades, 2)

    def test_trade_loader_failure_isolated(self):
        def bad_loader(s):
            raise RuntimeError("no trades")

        result = so.scan_matrix(
            ["EURUSD"], ["H1"],
            default_step_pips=15.0,
            bars_loader=lambda s, t: series(),
            trade_loader=bad_loader,
        )
        self.assertEqual(result.rows[0].verdict, so.VERDICT_OK)
        self.assertTrue(any("no trades" in e["reason"] for e in result.errors))

    def test_invalid_args(self):
        with self.assertRaises(ValueError):
            so.scan_matrix(["EURUSD"], ["H1"], years=0, bars_loader=lambda s, t: [])
        with self.assertRaises(ValueError):
            so.scan_matrix(["EURUSD"], ["H1"], p_quantile=2,
                           bars_loader=lambda s, t: [])
        with self.assertRaises(ValueError):
            so.scan_matrix(["EURUSD"], ["H1"], bars_loader=None)


class TestOutputs(unittest.TestCase):
    def test_write_outputs_round_trip(self):
        result = so.scan_matrix(
            ["EURUSD"], ["H1"],
            default_step_pips=0.5,
            bars_loader=lambda s, t: series(),
        )
        with tempfile.TemporaryDirectory() as d:
            paths = so.write_outputs(result, d)
            self.assertTrue(all(os.path.exists(p) for p in paths.values()))
            with open(paths["matrix"], encoding="utf-8") as fh:
                rows = list(__import__("csv").DictReader(fh))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["symbol"], "EURUSD")
            with open(paths["signals"], encoding="utf-8") as fh:
                sigs = list(__import__("csv").DictReader(fh))
            self.assertEqual(len(sigs), 1)
            with open(paths["meta"], encoding="utf-8") as fh:
                meta = json.load(fh)
            self.assertEqual(meta["timeframes"], ["H1"])
            self.assertIn("engine_version", meta)

    def test_csv_bars_loader(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "EURUSD_H1.csv")
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("time,open,high,low,close\n")
                for i in range(50):
                    fh.write(f"2024-01-01T{i:02d}:00,1.2,1.21,1.19,1.2\n")
            bars = so.csv_bars_loader(d)("EURUSD", "H1")
            self.assertEqual(len(bars), 50)


class TestApiRangeFix(unittest.TestCase):
    def test_no_copy_rates_from_pos_in_api(self):
        path = os.path.join(os.path.dirname(api.__file__), "api.py")
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        self.assertNotIn("mt5.copy_rates_from_pos(", src)
        self.assertNotIn("getattr(mt5, f\"TIMEFRAME_", src)

    def test_dedupe_sorted(self):
        bars = [
            Bar("2024-01-01T02:00", 3, 3, 3, 3),
            Bar("2024-01-01T01:00", 1, 1, 1, 1),
            Bar("2024-01-01T01:00", 2, 2, 2, 2),  # later duplicate wins
        ]
        out = api._dedupe_sorted(bars)
        self.assertEqual([b.time_label for b in out],
                         ["2024-01-01T01:00", "2024-01-01T02:00"])
        self.assertEqual(out[0].open, 2.0)


if __name__ == "__main__":
    unittest.main()
