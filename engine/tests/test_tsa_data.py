"""Tests for the #36 M1 single-source data layer (RED-first, TDD).

Synthetic .hst files are generated here, so the suite needs no live terminal.
Run: python -m unittest discover -s engine/tests -t .
"""

from __future__ import annotations

import os
import sqlite3
import struct
import sys
import tempfile
import unittest
from contextlib import closing

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.martingale.hst_reader import HEADER_BYTES, RECORD_BYTES, read_hst_header
from engine.tsa_data import (
    infer_digits, init_db, ingest_hst_dir, summary, SCHEMA_VERSION, SYMBOLS,
    OBSERVED_EXTRAS,
)

BASE = 1699999980  # epoch aligned to a 60s minute boundary (BASE % 60 == 0)


def write_hst(path: str, rows: list[tuple[int, float, float, float, float, int]],
              digits: int = 4, period: int = 1, symbol: str = "") -> None:
    """Write a minimal MT4 .hst: 148-byte header + 60-byte records."""
    sym = (symbol or os.path.basename(path).split("1.hst")[0]).upper()
    header = bytearray(b"\x00" * HEADER_BYTES)
    header[68:68 + len(sym)] = sym.encode("ascii")
    struct.pack_into("<i", header, 80, period)
    struct.pack_into("<i", header, 84, digits)
    blob = bytearray(header)
    for epoch, o, h, l, c, vol in rows:
        rec = struct.pack("<i", epoch)
        rec += b"\x00" * 4                      # +4..+7 padding
        rec += struct.pack("<4d", o, h, l, c)  # +8..+39
        rec += struct.pack("<i", vol)          # +40..+43
        rec += struct.pack("<i", 0)            # +44..+47 padding
        rec += struct.pack("<i", 0)            # +48..+51 spread
        rec += b"\x00" * 8                     # +52..+59 reserved
        assert len(rec) == RECORD_BYTES
        blob += rec
    with open(path, "wb") as fh:
        fh.write(blob)


class InferDigitsTests(unittest.TestCase):
    def test_seed_range_is_exactly_32_with_xaujpy_as_extra(self):
        self.assertEqual(len(SYMBOLS), 32)
        self.assertEqual(len(set(SYMBOLS)), 32)
        self.assertEqual(OBSERVED_EXTRAS, ("XAUJPY",))
        self.assertNotIn("XAUJPY", SYMBOLS)
        self.assertEqual(sum(1 for s in SYMBOLS if s.startswith("XAU")), 4)

    def test_jpy_xau_and_default_fallback(self):
        self.assertEqual(infer_digits("USDJPY"), 3)
        self.assertEqual(infer_digits("XAUUSD"), 2)
        self.assertEqual(infer_digits("XAUEUR"), 2)
        self.assertEqual(infer_digits("EURUSD"), 4)
        self.assertEqual(infer_digits("AUDCAD"), 4)


class HeaderTests(unittest.TestCase):
    def test_header_symbol_period_digits_are_read(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "EURUSD1.hst")
            write_hst(p, [(BASE, 1.14238, 1.14240, 1.14230, 1.14235, 10)],
                      digits=5, symbol="EURUSD")
            h = read_hst_header(p)
            self.assertEqual((h.symbol, h.period, h.digits), ("EURUSD", 1, 5))
            self.assertEqual(h.scale, 100000)


class SchemaTests(unittest.TestCase):
    def test_init_creates_tables_and_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            init_db(db)
            init_db(db)  # must not fail on second run
            with closing(sqlite3.connect(db)) as cx, cx:
                tables = {r[0] for r in cx.execute(
                    "select name from sqlite_master where type='table'")}
            self.assertIn("symbol", tables)
            self.assertIn("m1_bar", tables)
            self.assertIn("ingest_run", tables)
            self.assertGreaterEqual(SCHEMA_VERSION, 2)

    def test_mismatched_schema_version_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            init_db(db)
            with closing(sqlite3.connect(db)) as cx, cx:
                cx.execute("UPDATE meta SET value='99' WHERE key='schema_version'")
            with self.assertRaises(RuntimeError):
                init_db(db)


class IngestTests(unittest.TestCase):
    def test_single_symbol_ingest_and_rerun_is_idempotent(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst_dir = os.path.join(d, "history")
            os.makedirs(hst_dir)
            rows = [(BASE + i * 60, 1.1000 + i * 0.0001,
                     1.1005 + i * 0.0001, 1.0995 + i * 0.0001,
                     1.1002 + i * 0.0001, 100 + i) for i in range(20)]
            write_hst(os.path.join(hst_dir, "EURUSD1.hst"), rows)

            first = ingest_hst_dir(hst_dir, db, symbols=("EURUSD",))
            self.assertEqual(first["symbols_ingested"], 1)
            self.assertEqual(first["bars_in"], 20)
            self.assertEqual(first["bars_new"], 20)

            with closing(sqlite3.connect(db)) as cx, cx:
                n1 = cx.execute("select count(*) from m1_bar where symbol='EURUSD'").fetchone()[0]
                o1 = cx.execute("select open_px from m1_bar where symbol='EURUSD' order by ts limit 1").fetchone()[0]
            self.assertEqual(n1, 20)
            self.assertEqual(o1, 11000)  # 1.1000 × 10^4, fixed-point int

            second = ingest_hst_dir(hst_dir, db, symbols=("EURUSD",))
            self.assertEqual(second["bars_new"], 0)
            self.assertEqual(second["bars_updated"], 0)
            with closing(sqlite3.connect(db)) as cx, cx:
                n2 = cx.execute("select count(*) from m1_bar where symbol='EURUSD'").fetchone()[0]
            self.assertEqual(n2, 20)

    def test_five_decimal_fiat_uses_header_scale_not_heuristic(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst_dir = os.path.join(d, "history")
            os.makedirs(hst_dir)
            write_hst(os.path.join(hst_dir, "EURUSD1.hst"),
                      [(BASE, 1.14238, 1.14240, 1.14230, 1.14235, 10)],
                      digits=5, symbol="EURUSD")
            ingest_hst_dir(hst_dir, db, symbols=("EURUSD",))
            with closing(sqlite3.connect(db)) as cx, cx:
                o = cx.execute("select open_px from m1_bar where symbol='EURUSD'").fetchone()[0]
                d = cx.execute("select digits from symbol where code='EURUSD'").fetchone()[0]
            self.assertEqual(o, 114238)  # ×10^5 from header, NOT 11424
            self.assertEqual(d, 5)

    def test_revised_bar_is_updated_not_frozen(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst_dir = os.path.join(d, "history")
            os.makedirs(hst_dir)
            p = os.path.join(hst_dir, "EURUSD1.hst")
            write_hst(p, [(BASE, 1.1000, 1.1005, 1.0995, 1.1002, 100)])
            ingest_hst_dir(hst_dir, db, symbols=("EURUSD",))
            # MT4 finalises the forming bar: same ts, new close/volume/high.
            write_hst(p, [(BASE, 1.1000, 1.1012, 1.0994, 1.1010, 150)])
            second = ingest_hst_dir(hst_dir, db, symbols=("EURUSD",))
            self.assertEqual(second["bars_new"], 0)
            self.assertEqual(second["bars_updated"], 1)
            with closing(sqlite3.connect(db)) as cx, cx:
                c, v = cx.execute(
                    "select close_px,tick_vol from m1_bar where symbol='EURUSD'").fetchone()
            self.assertEqual((c, v), (11010, 150))

    def test_non_m1_header_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst_dir = os.path.join(d, "history")
            os.makedirs(hst_dir)
            write_hst(os.path.join(hst_dir, "EURUSD1.hst"),
                      [(BASE, 1.1, 1.2, 1.0, 1.15, 5)], period=60)
            res = ingest_hst_dir(hst_dir, db, symbols=("EURUSD",))
            self.assertEqual(res["symbols_ingested"], 0)
            self.assertEqual(res["bad"], ["EURUSD"])

    def test_case_and_unknown_symbol_normalisation(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst_dir = os.path.join(d, "history")
            os.makedirs(hst_dir)
            write_hst(os.path.join(hst_dir, "EURUSD1.hst"),
                      [(BASE, 1.1, 1.2, 1.0, 1.15, 5)], symbol="EURUSD")
            res = ingest_hst_dir(hst_dir, db, symbols=("eurusd", "eurusd", "XAUJPY"))
            self.assertEqual(res["rejected"], ["XAUJPY"])
            self.assertEqual(res["symbols_requested"], 1)  # de-duplicated
            with closing(sqlite3.connect(db)) as cx, cx:
                keys = [r[0] for r in cx.execute("select distinct symbol from m1_bar")]
            self.assertEqual(keys, ["EURUSD"])

    def test_missing_file_is_reported_and_persisted(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst_dir = os.path.join(d, "empty")
            os.makedirs(hst_dir)
            res = ingest_hst_dir(hst_dir, db, symbols=("EURUSD",))
            self.assertEqual(res["symbols_ingested"], 0)
            self.assertEqual(res["missing"], ["EURUSD"])
            self.assertEqual(res["status"], "partial")
            with closing(sqlite3.connect(db)) as cx, cx:
                status, miss = cx.execute(
                    "select status,missing_json from ingest_run order by run_id desc limit 1"
                ).fetchone()
            self.assertEqual(status, "partial")
            self.assertIn("EURUSD", miss)

    def test_jpy_symbol_uses_three_decimal_scale(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst_dir = os.path.join(d, "history")
            os.makedirs(hst_dir)
            write_hst(os.path.join(hst_dir, "USDJPY1.hst"),
                      [(BASE, 150.000, 150.100, 149.900, 150.050, 10)], digits=3)
            ingest_hst_dir(hst_dir, db, symbols=("USDJPY",))
            with closing(sqlite3.connect(db)) as cx, cx:
                c = cx.execute("select close_px from m1_bar where symbol='USDJPY'").fetchone()[0]
            self.assertEqual(c, 150050)  # 150.050 × 10^3


class SummaryTests(unittest.TestCase):
    def test_summary_reports_counts_span_and_last_run(self):
        with tempfile.TemporaryDirectory() as d:
            db = os.path.join(d, "tsa.db")
            hst_dir = os.path.join(d, "history")
            os.makedirs(hst_dir)
            rows = [(BASE + i * 60, 1.1, 1.2, 1.0, 1.15, 5) for i in range(3)]
            write_hst(os.path.join(hst_dir, "EURUSD1.hst"), rows)
            ingest_hst_dir(hst_dir, db, symbols=("EURUSD",))
            s = summary(db)
            self.assertEqual(s["m1_bar_rows"], 3)
            self.assertEqual(s["symbol_rows"], 32)  # seed range A
            self.assertEqual(s["symbols_covered"], 1)
            self.assertEqual(s["min_ts"], BASE)
            self.assertEqual(s["max_ts"], BASE + 120)
            self.assertEqual(s["last_run"]["status"], "ok")
            self.assertGreaterEqual(s["schema_version"], 2)


if __name__ == "__main__":
    unittest.main()
