"""Stage 3-4 tests: quality gate, SET diffing, segmentation, fit, scan, batch.

All offline. Fixtures are written into a temp dir; nothing reads ``downloads/``
or a terminal.

Run: python -m unittest discover -s engine/tests -t .
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.bar import Bar
from engine.martingale import batch as batch_mod
from engine.martingale import report as report_mod
from engine.martingale.fit import (
    GRADE_PLAUSIBLE,
    GRADE_TIGHT,
    GRADE_UNKNOWN,
    GRADE_WIDE,
    grade_ratio,
    score_symbol,
    trim_years,
)
from engine.martingale.ingest import Trade
from engine.martingale.quality import check, check_file, summarise
from engine.martingale.scan import scan_csv
from engine.martingale.segments import boundaries, compare, segment
from engine.martingale.setfile import (
    diff_sets,
    group_by_signal,
    parse_filename,
    parse_set_text,
    read_grid,
    read_set,
    timeline,
    version_changes,
)

HEADER = (
    "Open Time,Type,Lots,Symbol,Open Price,Close Time,Close Price,Commission,Swap,"
    "Net Pips,Net Profit,Max Profit,Max Pips,Max Loss,Max Loss Pips,Magic Number,"
    "Comment,Holding Time (Hours),Holding Time"
)


def _trade(
    day: int = 1,
    month: int = 7,
    year: int = 2026,
    lots: float = 0.02,
    symbol: str = "EURUSD",
    direction: str = "buy",
    profit: float = 10.0,
    pips: float = 10.0,
    open_price: float = 1.1,
    mae_pips: float = 5.0,
):
    """One trade at ``year-month-day 03:00``.

    ``day`` may exceed the month length: it is treated as an offset from the
    1st, so callers can write ``day=34`` without hand-rolling month arithmetic.
    """
    opened = datetime(year, month, 1, 3, 0, 0) + timedelta(days=day - 1)
    return Trade(
        symbol=symbol,
        direction=direction,
        lots=lots,
        open_time=opened,
        close_time=opened + timedelta(hours=2),
        open_price=open_price,
        net_pips=pips,
        net_profit=profit,
        max_profit=profit * 2,
        max_pips=pips * 2,
        max_loss=mae_pips,
        max_loss_pips=mae_pips,
        magic="1",
        comment="Test",
    )


class TempDirCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, name: str, text: str) -> str:
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8", newline="") as fh:
            fh.write(text)
        return path


def _csv_row(day: int, month: int = 7, lots: float = 0.02, symbol: str = "EURUSD",
             profit: float = 10.0, typ: str = "buy", comment: str = "Wayne Class") -> str:
    t = f"{day:02d}/{month:02d}/2026 03:00:00"
    ct = f"{day:02d}/{month:02d}/2026 05:00:00"
    return (f"{t},{typ},{lots},{symbol},1.10000,{ct},1.10100,0.00,0.00,10.00,"
            f"{profit},20.00,20.0,-3.00,5.00,1,{comment},1.00,1.00hrs")


class QualityGate(unittest.TestCase):
    def test_clean_file_produces_no_warnings(self) -> None:
        trades = [_trade(day=d) for d in range(1, 28)] + [
            _trade(day=d, month=8) for d in range(1, 15)
        ]
        rep = check(trades, path="x.csv")
        self.assertTrue(rep.ok)
        self.assertEqual(rep.errors, [])

    def test_fake_rows_are_an_error_with_a_dollar_figure(self) -> None:
        trades = [_trade(day=d) for d in range(1, 35)]
        rep = check(trades, fake_rows=14, fake_profit=8516.94)
        self.assertFalse(rep.ok)
        self.assertTrue(any(i.code == "FAKE_TRADES" for i in rep.errors))
        msg = next(i.message for i in rep.errors if i.code == "FAKE_TRADES")
        self.assertIn("8,516.94", msg)

    def test_fake_share_uses_gross_profit_as_denominator(self) -> None:
        """A file with big losses must never report a share above 1."""
        trades = [_trade(day=d, profit=-100.0) for d in range(1, 35)]
        rep = check(trades, fake_rows=5, fake_profit=1000.0)
        self.assertLessEqual(rep.fake_share, 1.0)

    def test_zero_lots_is_a_warning(self) -> None:
        trades = [_trade(day=d) for d in range(1, 35)] + [_trade(day=10, lots=0.0)]
        rep = check(trades)
        self.assertTrue(any(i.code == "ZERO_LOTS" for i in rep.warnings))

    def test_missing_open_time_is_a_warning(self) -> None:
        bad = Trade(
            symbol="EURUSD", direction="buy", lots=0.02, open_time=None,
            close_time=None, open_price=1.1, net_pips=0.0, net_profit=1.0,
            max_profit=1.0, max_pips=1.0, max_loss=0.0, max_loss_pips=0.0,
            magic="1", comment="",
        )
        trades = [_trade(day=d) for d in range(1, 35)] + [bad]
        rep = check(trades)
        self.assertEqual(rep.no_time_trades, 1)
        self.assertTrue(any(i.code == "NO_OPEN_TIME" for i in rep.warnings))

    def test_duplicates_are_detected(self) -> None:
        t = _trade(day=5)
        trades = [_trade(day=d) for d in range(1, 35)] + [t, t]
        rep = check(trades)
        self.assertGreaterEqual(rep.duplicate_trades, 2)
        self.assertTrue(any(i.code == "DUPLICATES" for i in rep.warnings))

    def test_small_sample_is_a_warning(self) -> None:
        rep = check([_trade(day=1)], min_trades=30)
        self.assertTrue(any(i.code == "SMALL_SAMPLE" for i in rep.warnings))

    def test_empty_input_is_an_error(self) -> None:
        rep = check([], path="empty.csv")
        self.assertTrue(any(i.code == "NO_TRADES" for i in rep.errors))

    def test_date_gap_is_only_informational(self) -> None:
        trades = [_trade(day=d, month=1) for d in range(1, 6)]
        trades += [_trade(day=d, month=8) for d in range(1, 6)]
        trades += [_trade(day=d, month=8) for d in range(6, 26)]
        rep = check(trades, gap_days=45)
        self.assertTrue(any(i.code == "DATE_GAP" for i in rep.issues))
        self.assertTrue(rep.ok)  # info must not block

    def test_summarise_aggregates(self) -> None:
        a = check([_trade(day=d) for d in range(1, 35)], fake_rows=2, fake_profit=100.0)
        b = check([], path="e.csv")
        s = summarise([a, b])
        self.assertEqual(s["files"], 2)
        self.assertEqual(s["fake_rows"], 2)
        self.assertGreaterEqual(s["files_with_errors"], 1)


class QualityFromCsv(TempDirCase):
    def test_check_file_reports_fake_rows_with_amount(self) -> None:
        summary_row = (
            "01/08/2026 00:00:00,buy,0.00,profit,0.00000,,0.00000,0.00,0.00,0.00,"
            "1234.56,0.00,0.00,0.00,0.00,0,Summary trade result 07.2026,0.00,0.00hrs"
        )
        rows = [_csv_row(d) for d in range(1, 35)] + [summary_row]
        path = self.write("s.csv", "\n".join([HEADER] + rows) + "\n")
        rep = check_file(path)
        self.assertEqual(rep.fake_rows, 1)
        self.assertAlmostEqual(rep.fake_profit, 1234.56)
        self.assertTrue(any(i.code == "FAKE_TRADES" for i in rep.errors))


class SetParsing(TempDirCase):
    def test_parse_splits_on_first_equals_only(self) -> None:
        params = parse_set_text("commentB=buy=ok\nLots=0.02\n; skip\n\nMaxSpread=40")
        self.assertEqual(params["commentB"], "buy=ok")
        self.assertEqual(params["Lots"], "0.02")
        self.assertEqual(params["MaxSpread"], "40")
        self.assertNotIn("; skip", params)

    def test_filename_signal_and_date(self) -> None:
        sig, d = parse_filename("(10437)Dragon Wave v2.10AUDCAD_H1_Both_2026-04-09_02-45-30.set")
        self.assertEqual(sig, "10437")
        self.assertEqual(d, date(2026, 4, 9))

    def test_filename_signal_without_date(self) -> None:
        sig, d = parse_filename("(16538)Dragon Wave v2.10AUDCAD_M5_Both_.set")
        self.assertEqual(sig, "16538")
        self.assertIsNone(d)

    def test_multiplier_family_is_recognised(self) -> None:
        g = read_grid({"Lots": "0.02", "LotMul": "2.5", "PipStepMul": "1.25"})
        self.assertEqual(g.family, "multiplicative")
        self.assertAlmostEqual(g.base_lot, 0.02)
        self.assertAlmostEqual(g.lot_multiplier, 2.5)
        self.assertAlmostEqual(g.step_multiplier, 1.25)
        lots = g.effective_lots(3)
        self.assertAlmostEqual(lots[0], 0.02)
        self.assertAlmostEqual(lots[1], 0.05)
        self.assertAlmostEqual(lots[2], 0.13)  # 0.125 rounded to cents

    def test_ladder_family_is_recognised(self) -> None:
        params = {"lot1": "0.02", "lot2": "0.05", "lot3": "0.07",
                  "PipStep1": "10", "PipStep2": "40", "PipStep3": "100"}
        g = read_grid(params)
        self.assertEqual(g.family, "ladder")
        self.assertEqual(g.effective_lots(5), [0.02, 0.05, 0.07])
        self.assertEqual(g.effective_steps(5), [10.0, 40.0, 100.0])
        self.assertAlmostEqual(g.first_step(), 10.0)

    def test_ladder_stops_at_a_gap(self) -> None:
        """lot1, lot2, lot4 must not collapse into a 3-rung ladder."""
        g = read_grid({"lot1": "0.01", "lot2": "0.02", "lot4": "0.08"})
        self.assertEqual(g.lot_ladder, [0.01, 0.02])

    def test_unknown_family_is_reported_not_guessed(self) -> None:
        g = read_grid({"MaxSpread": "40"})
        self.assertEqual(g.family, "unknown")
        self.assertEqual(g.effective_lots(), [])

    def test_multiplicative_without_first_step_has_no_ladder(self) -> None:
        g = read_grid({"Lots": "0.02", "LotMul": "2"})
        self.assertEqual(g.effective_steps(), [])


class SetDiff(TempDirCase):
    def _write_set(self, name: str, body: str) -> str:
        return self.write(name, body)

    def test_diff_reports_changed_added_and_removed(self) -> None:
        a = read_set(self._write_set("(1)A_2025-01-01.set", "Lots=0.01\nOld=1\nSame=5\n"))
        b = read_set(self._write_set("(1)A_2026-01-01.set", "Lots=0.02\nNew=2\nSame=5\n"))
        changes = {c.key: c for c in diff_sets(a, b)}
        self.assertEqual(changes["Lots"].old, "0.01")
        self.assertEqual(changes["Lots"].new, "0.02")
        self.assertTrue(changes["Lots"].is_grid)
        self.assertIsNone(changes["Old"].new)
        self.assertIsNone(changes["New"].old)
        self.assertNotIn("Same", changes)

    def test_ea_identity_change_is_flagged(self) -> None:
        a = read_set(self._write_set("(1)A_2025-01-01.set", "EA_NAME=S10 v2.00\n"))
        b = read_set(self._write_set("(1)A_2026-01-01.set", "EA_NAME=MKD v2.00\n"))
        ch = diff_sets(a, b)[0]
        self.assertTrue(ch.is_ea_identity)
        self.assertFalse(ch.is_grid)

    def test_timeline_orders_by_date_and_drops_undated(self) -> None:
        files = [
            read_set(self._write_set("(1)A_2026-05-04_x.set", "Lots=0.03\n")),
            read_set(self._write_set("(1)A_2025-05-20_x.set", "Lots=0.02\n")),
            read_set(self._write_set("(1)A_nodate.set", "Lots=0.99\n")),
        ]
        ordered = timeline(files)
        self.assertEqual([f.version_date for f in ordered], [date(2025, 5, 20), date(2026, 5, 4)])

    def test_version_changes_pairs_consecutive_versions(self) -> None:
        files = [
            read_set(self._write_set("(1)A_2025-01-01_x.set", "Lots=0.01\n")),
            read_set(self._write_set("(1)A_2025-06-01_x.set", "Lots=0.02\n")),
            read_set(self._write_set("(1)A_2026-01-01_x.set", "Lots=0.03\n")),
        ]
        pairs = version_changes(files)
        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0][2][0].new, "0.02")
        self.assertEqual(pairs[1][2][0].new, "0.03")

    def test_group_by_signal_skips_unnamed(self) -> None:
        files = [
            read_set(self._write_set("(7)A_x.set", "Lots=0.01\n")),
            read_set(self._write_set("plain.set", "Lots=0.01\n")),
        ]
        groups = group_by_signal(files)
        self.assertEqual(list(groups), ["7"])
        self.assertEqual(len(groups["7"]), 1)


class Segmentation(unittest.TestCase):
    def test_month_boundaries_cover_the_span(self) -> None:
        trades = [_trade(day=5, month=1), _trade(day=5, month=3)]
        cuts = boundaries(trades, "month")
        labels = [c[0] for c in cuts]
        self.assertEqual(labels, ["2026-01", "2026-02", "2026-03"])

    def test_quarter_boundaries(self) -> None:
        trades = [_trade(day=5, month=2), _trade(day=5, month=11)]
        labels = [c[0] for c in boundaries(trades, "quarter")]
        self.assertEqual(labels, ["2026-Q1", "2026-Q2", "2026-Q3", "2026-Q4"])

    def test_none_mode_is_one_window(self) -> None:
        trades = [_trade(day=5, month=2), _trade(day=5, month=11)]
        cuts = boundaries(trades, "none")
        self.assertEqual(len(cuts), 1)
        self.assertEqual(cuts[0][0], "all")

    def test_unknown_mode_raises(self) -> None:
        with self.assertRaises(ValueError):
            boundaries([_trade()], "week")

    def test_boundary_is_half_open_so_nothing_double_counts(self) -> None:
        """A trade at exactly midnight belongs to the window starting there."""
        midnight = _trade(day=1, month=3)
        midnight = Trade(
            symbol=midnight.symbol, direction=midnight.direction, lots=midnight.lots,
            open_time=datetime(2026, 3, 1, 0, 0, 0), close_time=midnight.close_time,
            open_price=midnight.open_price, net_pips=midnight.net_pips,
            net_profit=midnight.net_profit, max_profit=midnight.max_profit,
            max_pips=midnight.max_pips, max_loss=midnight.max_loss,
            max_loss_pips=midnight.max_loss_pips, magic=midnight.magic,
            comment=midnight.comment,
        )
        trades = [_trade(day=5, month=2), midnight]
        rep = segment(trades, mode="month")
        counts = {s.label: s.count for s in rep.segments}
        self.assertEqual(counts["2026-02"], 1)
        self.assertEqual(counts["2026-03"], 1)
        self.assertEqual(rep.total_trades, 2)

    def test_segment_stats(self) -> None:
        trades = [
            _trade(day=1, month=1, profit=100.0, pips=50.0, mae_pips=20.0),
            _trade(day=2, month=1, profit=-50.0, pips=-25.0, mae_pips=40.0),
        ]
        rep = segment(trades, mode="month")
        jan = rep.segments[0]
        self.assertEqual(jan.count, 2)
        self.assertAlmostEqual(jan.win_rate, 0.5)
        self.assertAlmostEqual(jan.net_profit, 50.0)
        self.assertAlmostEqual(jan.net_pips, 25.0)
        self.assertAlmostEqual(jan.worst_mae_pips, 40.0)

    def test_thin_segments_are_marked(self) -> None:
        rep = segment([_trade(day=1), _trade(day=2)], mode="month", min_trades=30)
        self.assertEqual(len(rep.thin()), len(rep.segments))

    def test_drift_needs_two_solid_segments(self) -> None:
        few = segment([_trade(day=1)], mode="month", min_trades=1)
        self.assertIsNone(few.drift())

    def test_drift_reports_direction(self) -> None:
        good = [_trade(day=d, month=1, profit=100.0) for d in range(1, 6)]
        bad = [_trade(day=d, month=2, profit=-100.0) for d in range(1, 6)]
        rep = segment(good + bad, mode="month", min_trades=3)
        d = rep.drift()
        assert d is not None
        self.assertLess(d["win_rate_delta"], 0)
        self.assertLess(d["profit_per_trade_delta"], 0)

    def test_explicit_ranges_override_mode(self) -> None:
        trades = [_trade(day=15, month=1), _trade(day=15, month=6)]
        cuts = [("H1", datetime(2026, 1, 1), datetime(2026, 4, 1)),
                ("H2", datetime(2026, 4, 1), datetime(2026, 12, 1))]
        rep = segment(trades, explicit=cuts)
        self.assertEqual([s.count for s in rep.segments], [1, 1])

    def test_compare_returns_both_sides(self) -> None:
        rep = segment(
            [_trade(day=d, month=1) for d in range(1, 6)]
            + [_trade(day=d, month=2, profit=-5.0) for d in range(1, 6)],
            mode="month", min_trades=3,
        )
        c = compare(rep.segments[0], rep.segments[1])
        self.assertEqual(c["win_rate"]["a"], 1.0)
        self.assertEqual(c["win_rate"]["b"], 0.0)


class FitScoring(unittest.TestCase):
    def test_grades(self) -> None:
        self.assertEqual(grade_ratio(None), GRADE_UNKNOWN)
        self.assertEqual(grade_ratio(0.2), GRADE_TIGHT)
        self.assertEqual(grade_ratio(1.0), GRADE_PLAUSIBLE)
        self.assertEqual(grade_ratio(3.0), GRADE_WIDE)
        self.assertEqual(grade_ratio(0.5), GRADE_PLAUSIBLE)
        self.assertEqual(grade_ratio(1.5), GRADE_PLAUSIBLE)

    def test_score_uses_p80_by_default(self) -> None:
        class FakeScan:
            def median_bands(self):
                from engine.martingale.waves import BandSet
                return BandSet(0, 10, 9, 5, 10.0, 100.0, 200.0, 300.0)

        s = score_symbol("EURUSD", 50.0, FakeScan())
        self.assertAlmostEqual(s.band_pips, 100.0)
        self.assertAlmostEqual(s.ratio, 0.5)
        self.assertEqual(s.grade, GRADE_PLAUSIBLE)

    def test_missing_step_is_unknown_not_zero(self) -> None:
        class FakeScan:
            def median_bands(self):
                return None

        s = score_symbol("EURUSD", None, FakeScan())
        self.assertEqual(s.grade, GRADE_UNKNOWN)
        self.assertIsNone(s.ratio)

    def test_implied_layers_is_the_inverse_of_the_ratio(self) -> None:
        """210-pip swing against a 15-pip step spans 14 steps."""
        class FakeScan:
            def median_bands(self):
                from engine.martingale.waves import BandSet
                return BandSet(0, 10, 9, 5, 10.0, 210.0, 200.0, 300.0)

        s = score_symbol("EURUSD", 15.0, FakeScan())
        self.assertAlmostEqual(s.implied_layers, 14.0)
        self.assertIn("14 steps", s.explained)

    def test_implied_layers_is_none_without_a_band(self) -> None:
        class FakeScan:
            def median_bands(self):
                return None

        self.assertIsNone(score_symbol("EURUSD", 15.0, FakeScan()).implied_layers)

    def test_trim_years_counts_back_from_last_bar(self) -> None:
        bars = [Bar(f"{y}-01-01T00:00", 1, 1, 1, 1) for y in range(2010, 2021)]
        kept = trim_years(bars, years=5)
        self.assertEqual(kept[0].time_label[:4], "2015")
        self.assertEqual(kept[-1].time_label[:4], "2020")

    def test_trim_years_on_empty(self) -> None:
        self.assertEqual(trim_years([], years=5), [])


class ScanRecord(TempDirCase):
    def _write(self, rows, name="s.csv"):
        return self.write(name, "\n".join([HEADER] + rows) + "\n")

    def test_record_fields(self) -> None:
        rows = [_csv_row(d, lots=0.01 if d < 3 else 0.02) for d in range(1, 20)]
        rec = scan_csv(self._write(rows))
        self.assertTrue(rec.ok)
        self.assertEqual(rec.trades, 19)
        self.assertAlmostEqual(rec.win_rate, 1.0)
        self.assertGreater(rec.cycles, 0)
        self.assertIn("EURUSD", rec.symbols)

    def test_empty_file_is_not_an_exception(self) -> None:
        rec = scan_csv(self._write([]))
        self.assertFalse(rec.ok)
        self.assertIn("no trades", rec.error)

    def test_missing_file_is_recorded_not_raised(self) -> None:
        rec = scan_csv(os.path.join(self.dir, "nope.csv"))
        self.assertFalse(rec.ok)
        self.assertTrue(rec.error)

    def test_methods_disagree_flag_matches_the_two_models(self) -> None:
        rows = [_csv_row(d, lots=0.01 * d) for d in range(1, 10)]
        rec = scan_csv(self._write(rows), quality_gate=False)
        self.assertEqual(
            rec.methods_disagree,
            rec.layers_excel["max_layer"] != rec.layers_linear["max_layer"],
        )

    def test_segments_are_present_and_labelled(self) -> None:
        rows = [_csv_row(d, month=m) for m in (1, 2) for d in range(1, 5)]
        rec = scan_csv(self._write(rows), quality_gate=False)
        self.assertEqual([s["label"] for s in rec.segments][:2], ["2026-01", "2026-02"])

    def test_as_dict_is_json_serialisable(self) -> None:
        rows = [_csv_row(d) for d in range(1, 12)]
        rec = scan_csv(self._write(rows), quality_gate=False)
        json.dumps(rec.as_dict())  # must not raise


class Batch(TempDirCase):
    def _make(self, name: str, n: int = 35) -> str:
        rows = [_csv_row(d if d <= 28 else d - 28, month=7 if d <= 28 else 8) for d in range(1, n + 1)]
        return self.write(name, "\n".join([HEADER] + rows) + "\n")

    def test_batch_writes_summary_and_failed(self) -> None:
        self._make("1.csv")
        self.write("2.csv", HEADER + "\n")  # header only -> failure recorded
        out = os.path.join(self.dir, "out")
        res = batch_mod.run(self.dir, out_dir=out)
        self.assertEqual(len(res.records), 2)
        self.assertEqual(res.failed_count, 1)
        self.assertTrue(os.path.exists(os.path.join(out, "summary.csv")))
        self.assertTrue(os.path.exists(os.path.join(out, "failed.txt")))

    def test_summary_has_a_fixed_header_order(self) -> None:
        self._make("a.csv")
        out = os.path.join(self.dir, "out")
        batch_mod.run(self.dir, out_dir=out)
        with open(os.path.join(out, "summary.csv"), encoding="utf-8", newline="") as fh:
            header = next(csv.reader(fh))
        self.assertEqual(header, batch_mod.SUMMARY_FIELDS)

    def test_two_runs_are_byte_identical(self) -> None:
        self._make("a.csv")
        self._make("b.csv")
        o1 = os.path.join(self.dir, "o1")
        o2 = os.path.join(self.dir, "o2")
        batch_mod.run(self.dir, out_dir=o1)
        batch_mod.run(self.dir, out_dir=o2)
        with open(os.path.join(o1, "summary.csv"), "rb") as fh:
            a = fh.read()
        with open(os.path.join(o2, "summary.csv"), "rb") as fh:
            b = fh.read()
        self.assertEqual(a, b)

    def test_summary_uses_lf_only(self) -> None:
        self._make("a.csv")
        out = os.path.join(self.dir, "out")
        batch_mod.run(self.dir, out_dir=out)
        with open(os.path.join(out, "summary.csv"), "rb") as fh:
            self.assertNotIn(b"\r\n", fh.read())

    def test_limit_stops_early(self) -> None:
        self._make("a.csv")
        self._make("b.csv")
        self._make("c.csv")
        res = batch_mod.run(self.dir, out_dir=os.path.join(self.dir, "o"), limit=2)
        self.assertEqual(len(res.records), 2)

    def test_cli_exit_code_respects_max_failed(self) -> None:
        self._make("a.csv")
        self.write("b.csv", HEADER + "\n")
        out = os.path.join(self.dir, "out")
        proc = subprocess.run(
            [sys.executable, "-m", "engine.martingale.batch",
             "--dir", self.dir, "--out", out, "--max-failed", "0"],
            cwd=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            capture_output=True, text=True,
        )
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)


class HtmlReport(TempDirCase):
    def _record(self):
        rows = [_csv_row(d, month=m) for m in (1, 2, 3) for d in range(1, 13)]
        return scan_csv(self.write("s.csv", "\n".join([HEADER] + rows) + "\n"))

    def test_report_is_standalone_and_has_no_external_assets(self) -> None:
        doc = report_mod.render(self._record())
        self.assertNotIn("http://", doc)
        self.assertNotIn("https://", doc)
        self.assertNotIn("<script src", doc)
        self.assertNotIn("<link rel=\"stylesheet\"", doc)

    def test_report_contains_zh_hant_and_no_simplified_forms(self) -> None:
        doc = report_mod.render(self._record())
        for word in ("淨利", "勝率", "資料質量"):
            self.assertIn(word, doc)
        # simplified-only characters that must never appear
        for bad in ("净", "胜率", "数据", "质量", "报表"):
            self.assertNotIn(bad, doc)

    def test_segment_rows_carry_data_month_for_filtering(self) -> None:
        doc = report_mod.render(self._record())
        self.assertIn('data-month="2026-01"', doc)
        self.assertIn('data-month="2026-03"', doc)

    def test_write_uses_lf(self) -> None:
        path = os.path.join(self.dir, "r.html")
        report_mod.write(self._record(), path)
        with open(path, "rb") as fh:
            self.assertNotIn(b"\r\n", fh.read())

    def test_index_lists_every_record(self) -> None:
        rec = self._record()
        doc = report_mod.render_index([rec])
        self.assertIn("馬丁掃描總覽", doc)
        self.assertIn(rec.signal_id, doc)

    def test_thin_segments_are_visually_marked(self) -> None:
        rows = [_csv_row(1, month=1)] + [_csv_row(d, month=2) for d in range(1, 30)]
        rec = scan_csv(self.write("t.csv", "\n".join([HEADER] + rows) + "\n"))
        doc = report_mod.render(rec)
        self.assertIn('class="thin"', doc)


if __name__ == "__main__":
    unittest.main()
