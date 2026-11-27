"""Tests for #36 data layer slice 2: derived-TF materialisation + QC.

Slice 1 built m1_bar. This slice adds ``bar_tf`` (H1/H4/D1 rebuilt from M1) and
a QC that compares the rebuild against the broker's own ``.hst`` files, which is
the only way to prove the fold is right rather than merely self-consistent.

TDD: these tests are written before the implementation.
Run: python -m unittest discover -s engine/tests -t . -p test_tsa_data_tf.py
"""

from __future__ import annotations

import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import closing

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.tsa_data import (
    ingest_hst_dir, init_db, materialize_tf, qc_against_hst, summary,
    SCHEMA_VERSION, DERIVED_TFS,
)
from engine.tests.test_tsa_data import write_hst, BASE

# BASE is minute-aligned but not hour-aligned; derived-TF tests need an exact
# hour boundary so N M1 bars fold into exactly N/60 complete buckets.
BASE_H = BASE - (BASE % 3600)
# Day-aligned variant for D1 buckets (BASE is neither hour- nor day-aligned).
BASE_D = BASE - (BASE % 86400)


def seed(db: str, hst_dir: str, symbol: str = "EURUSD") -> None:
    os.makedirs(hst_dir, exist_ok=True)
    # 3 complete H1 buckets of 60 M1 bars, deterministic ramp.
    rows = []
    for i in range(180):
        base = 1.1000 + 0.0001 * i
        rows.append((BASE_H + i * 60, base, base + 0.0002, base - 0.0002,
                     base + 0.0001, 100 + i))
    write_hst(os.path.join(hst_dir, f"{symbol}1.hst"), rows, digits=5, symbol=symbol)
    ingest_hst_dir(hst_dir, db, symbols=(symbol,))


class MaterializeTests(unittest.TestCase):
    def test_derived_tfs_declared(self):
        self.assertEqual(set(DERIVED_TFS), {"H1", "H4", "D1"})

    def test_h1_rebuild_matches_m1_fold(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            seed(db, os.path.join(d, "hist"))
            res = materialize_tf(db, "H1")
            self.assertEqual(res["tf"], "H1")
            self.assertEqual(res["bars"], 3)  # 180 M1 = 3 complete hours
            with closing(sqlite3.connect(db)) as cx, cx:
                rows = cx.execute(
                    "SELECT ts,open_px,high_px,low_px,close_px,m1_cnt,is_partial "
                    "FROM bar_tf WHERE tf='H1' AND symbol='EURUSD' ORDER BY ts"
                ).fetchall()
            self.assertEqual(len(rows), 3)
            ts0, o0, h0, l0, c0, cnt0, partial0 = rows[0]
            self.assertEqual(cnt0, 60)
            self.assertEqual(partial0, 0)
            self.assertEqual(o0, 110000)                  # first M1 open ×1e5
            self.assertEqual(c0, 110600)                  # close of M1 bar 59, ×1e5

    def test_partial_bucket_flagged_not_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst = os.path.join(d, "hist")
            os.makedirs(hst)
            # 60 + 25 M1 bars -> one complete hour and one short (forming) hour
            rows = []
            for i in range(85):
                base = 1.1000 + 0.0001 * i
                rows.append((BASE_H + i * 60, base, base + 0.0002, base - 0.0002,
                             base + 0.0001, 10))
            write_hst(os.path.join(hst, "EURUSD1.hst"), rows, digits=5, symbol="EURUSD")
            ingest_hst_dir(hst, db, symbols=("EURUSD",))
            materialize_tf(db, "H1")
            with closing(sqlite3.connect(db)) as cx, cx:
                got = cx.execute(
                    "SELECT m1_cnt,is_partial FROM bar_tf WHERE tf='H1' ORDER BY ts"
                ).fetchall()
            self.assertEqual(len(got), 2)
            self.assertEqual(got[0], (60, 0))
            self.assertEqual(got[1], (25, 1))   # flagged, still stored

    def test_rematerialise_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            seed(db, os.path.join(d, "hist"))
            materialize_tf(db, "H1")
            materialize_tf(db, "H1")
            with closing(sqlite3.connect(db)) as cx, cx:
                n = cx.execute("SELECT count(*) FROM bar_tf WHERE tf='H1'").fetchone()[0]
            self.assertEqual(n, 3)

    def test_d1_buckets_are_all_flagged_partial(self):
        """Only 180 M1 bars exist, so every D1 bucket is short -> flagged."""
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            seed(db, os.path.join(d, "hist"))
            materialize_tf(db, "D1")
            with closing(sqlite3.connect(db)) as cx, cx:
                got = cx.execute(
                    "SELECT m1_cnt,is_partial FROM bar_tf WHERE tf='D1'").fetchall()
            self.assertTrue(got)
            for cnt, partial in got:
                self.assertLess(cnt, 1440)
                self.assertEqual(partial, 1)

    def test_unknown_tf_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            init_db(db)
            with self.assertRaises(ValueError):
                materialize_tf(db, "M5")


class QcTests(unittest.TestCase):
    def test_qc_reports_zero_mismatch_against_broker_hst(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst = os.path.join(d, "hist")
            seed(db, hst)
            materialize_tf(db, "H1")
            # Broker-side H1 written from the same underlying values.
            h1rows = []
            for b in range(3):
                i0, i1 = b * 60, b * 60 + 59
                h1rows.append((
                    BASE_H + b * 3600,
                    1.1000 + 0.0001 * i0,
                    1.1000 + 0.0001 * i1 + 0.0002,
                    1.1000 + 0.0001 * i0 - 0.0002,
                    1.1000 + 0.0001 * i1 + 0.0001,
                    6000 + b,
                ))
            write_hst(os.path.join(hst, "EURUSD60.hst"), h1rows, digits=5,
                      period=60, symbol="EURUSD")
            qc = qc_against_hst(db, "H1", hst, symbols=("EURUSD",))
            self.assertEqual(qc["compared"], 3)
            self.assertEqual(qc["mismatch"], 0)
            self.assertTrue(qc["ok"])

    def test_qc_detects_mismatch(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst = os.path.join(d, "hist")
            seed(db, hst)
            materialize_tf(db, "H1")
            h1rows = [(BASE_H, 1.2000, 1.2001, 1.1999, 1.2000, 60)]  # wrong prices
            write_hst(os.path.join(hst, "EURUSD60.hst"), h1rows, digits=5,
                      period=60, symbol="EURUSD")
            qc = qc_against_hst(db, "H1", hst, symbols=("EURUSD",))
            self.assertEqual(qc["compared"], 1)
            self.assertGreater(qc["mismatch"], 0)
            self.assertFalse(qc["ok"])

    def test_partial_bucket_diff_does_not_fail_gate(self):
        """A short head/tail bucket is cut by the hst window: reported, not gating."""
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst = os.path.join(d, "hist")
            os.makedirs(hst)
            rows = [(BASE_H + i * 60, 1.1000 + 0.0001 * i,
                     1.1000 + 0.0001 * i + 0.0002, 1.1000 + 0.0001 * i - 0.0002,
                     1.1000 + 0.0001 * i + 0.0001, 10) for i in range(85)]
            write_hst(os.path.join(hst, "EURUSD1.hst"), rows, digits=5,
                      symbol="EURUSD")
            ingest_hst_dir(hst, db, symbols=("EURUSD",))
            materialize_tf(db, "H1")
            # Broker H1: correct for the complete hour, deliberately wrong for
            # the short (forming) hour.
            h1rows = [
                (BASE_H, 1.1000, 1.1059 + 0.0002, 1.1000 - 0.0002, 1.1059 + 0.0001, 600),
                (BASE_H + 3600, 9.9999, 9.9999, 9.9999, 9.9999, 25),
            ]
            write_hst(os.path.join(hst, "EURUSD60.hst"), h1rows, digits=5,
                      period=60, symbol="EURUSD")
            qc = qc_against_hst(db, "H1", hst, symbols=("EURUSD",))
            self.assertEqual(qc["compared"], 2)
            self.assertEqual(qc["mismatch"], 1)          # the partial one
            self.assertEqual(qc["compared_complete"], 1)
            self.assertEqual(qc["mismatch_complete"], 0)
            self.assertTrue(qc["ok"])                    # gate uses complete only

    def test_complete_bucket_mismatch_fails_gate(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst = os.path.join(d, "hist")
            seed(db, hst)
            materialize_tf(db, "H1")
            h1rows = [(BASE_H, 1.2000, 1.2001, 1.1999, 1.2000, 60)]
            write_hst(os.path.join(hst, "EURUSD60.hst"), h1rows, digits=5,
                      period=60, symbol="EURUSD")
            qc = qc_against_hst(db, "H1", hst, symbols=("EURUSD",))
            self.assertEqual(qc["compared_complete"], 1)
            self.assertEqual(qc["mismatch_complete"], 1)
            self.assertFalse(qc["ok"])

    def test_interior_short_bucket_is_not_flagged(self):
        """Broker session is 1,420 min/day: a complete D1 day is short of 1,440.

        An absolute threshold would flag every D1 row partial forever and hide
        correct data, so only edge buckets may be flagged.
        """
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst = os.path.join(d, "hist")
            os.makedirs(hst)
            # Two D1 days: full 1440 then a 20-bar tail (edge). Interior day 1 is
            # complete by the minute count; make day 2 interior-short instead by
            # appending a third day so day 2 is not the last bucket.
            rows = []
            for day in range(3):
                n = 1440 if day < 2 else 20
                for i in range(n):
                    e = BASE_D + day * 86400 + i * 60
                    rows.append((e, 1.1, 1.2, 1.0, 1.15, 5))
            write_hst(os.path.join(hst, "EURUSD1.hst"), rows, digits=5, symbol="EURUSD")
            ingest_hst_dir(hst, db, symbols=("EURUSD",))
            materialize_tf(db, "D1")
            with closing(sqlite3.connect(db)) as cx, cx:
                got = cx.execute(
                    "SELECT m1_cnt,is_partial FROM bar_tf WHERE tf='D1' ORDER BY ts"
                ).fetchall()
            self.assertEqual(len(got), 3)
            self.assertEqual(got[0], (1440, 0))   # interior complete
            self.assertEqual(got[1], (1440, 0))   # interior complete
            self.assertEqual(got[2], (20, 1))     # edge short -> flagged

    def test_absent_bucket_fails_gate(self):
        """A fold that silently drops a bucket must not be certified clean."""
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst = os.path.join(d, "hist")
            seed(db, hst)
            # Delete the middle hour's M1 rows, then re-materialise.
            with closing(sqlite3.connect(db)) as cx, cx:
                cx.execute("DELETE FROM m1_bar WHERE ts>=? AND ts<?",
                           (BASE_H + 3600, BASE_H + 7200))
            materialize_tf(db, "H1")
            h1rows = []
            for b in range(3):
                i0, i1 = b * 60, b * 60 + 59
                h1rows.append((BASE_H + b * 3600,
                               1.1000 + 0.0001 * i0,
                               1.1000 + 0.0001 * i1 + 0.0002,
                               1.1000 + 0.0001 * i0 - 0.0002,
                               1.1000 + 0.0001 * i1 + 0.0001, 6000 + b))
            write_hst(os.path.join(hst, "EURUSD60.hst"), h1rows, digits=5,
                      period=60, symbol="EURUSD")
            qc = qc_against_hst(db, "H1", hst, symbols=("EURUSD",))
            self.assertEqual(qc["missing"], 1)
            self.assertFalse(qc["ok"])

    def test_no_evidence_symbol_fails_gate(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst = os.path.join(d, "hist")
            seed(db, hst)
            materialize_tf(db, "H1")
            h1rows = [(BASE_H, 1.1000, 1.1059 + 0.0002, 1.1000 - 0.0002,
                       1.1059 + 0.0001, 6000)]
            write_hst(os.path.join(hst, "EURUSD60.hst"), h1rows, digits=5,
                      period=60, symbol="EURUSD")
            qc = qc_against_hst(db, "H1", hst, symbols=("EURUSD", "AUDCAD"))
            self.assertIn("AUDCAD", qc["no_evidence"])
            self.assertEqual(qc["symbols_compared"], 1)
            self.assertFalse(qc["ok"])

    def test_high_low_and_volume_are_folded(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst = os.path.join(d, "hist")
            os.makedirs(hst)
            rows = []
            for i in range(60):
                base = 1.1000 + 0.0001 * i
                close = base + 0.00005
                rows.append((BASE_H + i * 60, base, base + 0.0003,
                             base - 0.0005, close, 7))
            write_hst(os.path.join(hst, "EURUSD1.hst"), rows,
                      digits=5, symbol="EURUSD")
            ingest_hst_dir(hst, db, symbols=("EURUSD",))
            materialize_tf(db, "H1")
            with closing(sqlite3.connect(db)) as cx, cx:
                o, h, l, c, v = cx.execute(
                    "SELECT open_px,high_px,low_px,close_px,tick_vol FROM bar_tf "
                    "WHERE tf='H1'").fetchone()
            self.assertEqual(h, 110620)          # max high = last bar's high
            self.assertEqual(l, 109950)          # min low  = first bar's low
            self.assertEqual(v, 60 * 7)          # volume summed

    def test_qc_result_row_is_not_green_without_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst = os.path.join(d, "hist")
            seed(db, hst)
            materialize_tf(db, "H1")
            # Broker bars far outside our span -> zero overlap, zero evidence.
            write_hst(os.path.join(hst, "EURUSD60.hst"),
                      [(BASE_H + 86400 * 400, 1.1, 1.2, 1.0, 1.15, 60)],
                      digits=5, period=60, symbol="EURUSD")
            qc_against_hst(db, "H1", hst, symbols=("EURUSD",))
            with closing(sqlite3.connect(db)) as cx, cx:
                ok = cx.execute(
                    "SELECT ok FROM qc_result WHERE tf='H1' AND symbol='EURUSD'"
                ).fetchone()[0]
            self.assertEqual(ok, 0)

    def test_materialize_on_absent_db_creates_schema(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "fresh", "tsa.db")
            res = materialize_tf(db, "H1")
            self.assertEqual(res["bars"], 0)     # no M1 yet, but schema exists
            with closing(sqlite3.connect(db)) as cx, cx:
                tables = {r[0] for r in cx.execute(
                    "select name from sqlite_master where type='table'")}
            self.assertIn("bar_tf", tables)

    def test_summary_reports_derived_rows(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            seed(db, os.path.join(d, "hist"))
            materialize_tf(db, "H1")
            s = summary(db)
            self.assertEqual(s["bar_tf_rows"].get("H1"), 3)
            self.assertGreaterEqual(s["schema_version"], 3)


if __name__ == "__main__":
    unittest.main()
