"""Tests for the #37 Scanner parity suite (original truth vs rebuilt panel).

Synthetic CSVs only: no MT4/MT5 or original-indicator license needed.
Run: python -m unittest discover -s engine/tests -t .
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.martingale import scanner_parity as sp


def write(path: str, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


class LoadTruthTests(unittest.TestCase):
    def test_wide_layout_with_gold_alias_and_tf(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "truth.csv")
            write(p, "timestamp,timeframe,EUR,USD,GOLD\n"
                     "2026-01-01 00:00,H1,4.5,5.0,2.25\n")
            got = sp.load_truth(p)
            self.assertEqual(got[("2026-01-01 00:00", "H1", "EUR")], 4.5)
            self.assertEqual(got[("2026-01-01 00:00", "H1", "XAU")], 2.25)

    def test_long_reader_layout(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "truth.csv")
            write(p, "timestamp,timeframe,ccy1_name,ccy1_power,ccy2_name,ccy2_power\n"
                     "2026-01-01 00:00,H4,USD,8.13,EUR,4.5\n")
            got = sp.load_truth(p)
            self.assertEqual(got[("2026-01-01 00:00", "H4", "USD")], 8.13)
            self.assertEqual(got[("2026-01-01 00:00", "H4", "EUR")], 4.5)

    def test_missing_file_and_too_few_rows_raise(self):
        with self.assertRaises(sp.ParityPendingError):
            sp.load_truth(os.path.join(tempfile.gettempdir(), "no_such_truth.csv"))
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "truth.csv")
            write(p, "timestamp,EUR\n2026-01-01 00:00,4.5\n")
            with self.assertRaises(sp.ParityPendingError):
                sp.load_truth(p, min_rows=2)


class CompareTests(unittest.TestCase):
    def test_exact_and_within_tolerance_pass(self):
        truth = {("t1", "H1", "EUR"): 4.5, ("t1", "H1", "USD"): 5.0}
        clone = {("t1", "H1", "EUR"): 4.50005, ("t1", "H1", "USD"): 5.0}
        rep = sp.compare(truth, clone)
        self.assertTrue(rep.all_pass)
        self.assertEqual(len(rep.passed), 2)
        self.assertLessEqual(rep.max_diff, 1e-4)

    def test_over_tolerance_fails_and_top10_sorted(self):
        truth = {("t1", "H1", c): 4.0 for c in sp.CURRENCIES_9}
        clone = dict(truth)
        clone[("t1", "H1", "EUR")] = 4.02
        clone[("t1", "H1", "USD")] = 4.01
        rep = sp.compare(truth, clone)
        self.assertFalse(rep.all_pass)
        self.assertEqual(len(rep.failed), 2)
        self.assertEqual([c.ccy for c in rep.top10()[:2]], ["EUR", "USD"])

    def test_missing_side_is_not_a_pass(self):
        truth = {("t1", "H1", "EUR"): 4.5, ("t1", "H1", "USD"): 5.0}
        clone = {("t1", "H1", "EUR"): 4.5, ("t1", "H1", "JPY"): 3.0}
        rep = sp.compare(truth, clone)
        self.assertFalse(rep.all_pass)
        self.assertEqual(rep.truth_only, [("t1", "H1", "USD")])
        self.assertEqual(rep.clone_only, [("t1", "H1", "JPY")])
        self.assertEqual(len(rep.compared), 1)

    def test_empty_inputs_raise(self):
        with self.assertRaises(sp.ParityPendingError):
            sp.compare({}, {("t1", "H1", "EUR"): 4.5})
        with self.assertRaises(sp.ParityPendingError):
            sp.compare({("t1", "H1", "EUR"): 4.5}, {})


class ReportTests(unittest.TestCase):
    def test_csv_has_every_cell_and_top10_section(self):
        truth = {("t1", "H1", c): 4.0 for c in sp.CURRENCIES_9}
        clone = dict(truth)
        clone[("t1", "H1", "EUR")] = 4.5
        rep = sp.compare(truth, clone)
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "nested", "parity_report.csv")
            sp.write_report(rep, p)
            with open(p, encoding="utf-8") as fh:
                text = fh.read()
            self.assertIn("pass/fail", text)
            self.assertNotIn("MISSING", text)  # no missing cells here
            self.assertIn("FAIL", text)
            self.assertIn("TOP10_MAX_DIFF", text)

    def test_summary_shape(self):
        truth = {("t1", "H1", "EUR"): 4.5}
        rep = sp.compare(truth, dict(truth))
        s = sp.summary(rep)
        self.assertEqual(s["tolerance"], 1e-4)
        self.assertEqual(s["compared"], 1)
        self.assertTrue(s["all_pass"])


class CliTests(unittest.TestCase):
    def test_cli_exit_zero_on_pass_one_on_fail(self):
        with tempfile.TemporaryDirectory() as d:
            truth_p = os.path.join(d, "truth.csv")
            clone_p = os.path.join(d, "clone.csv")
            out_p = os.path.join(d, "parity_report.csv")
            header = "timestamp,timeframe,EUR,USD\n"
            write(truth_p, header + "2026-01-01 00:00,H1,4.5,5.0\n")
            write(clone_p, header + "2026-01-01 00:00,H1,4.5,5.0\n")
            cmd = [sys.executable, "-m", "engine.martingale.scanner_parity",
                   "--truth", truth_p, "--clone", clone_p, "--out", out_p]
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn('"all_pass": true', r.stdout)
            write(clone_p, header + "2026-01-01 00:00,H1,4.5,5.5\n")
            r = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
            self.assertEqual(r.returncode, 1, r.stderr)


if __name__ == "__main__":
    unittest.main()
