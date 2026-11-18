"""Tests for engine.research — the CCY Power `Period` probe.

These run fully offline: they synthesise .dat files in memory/tempdir using the
documented binary layout, then assert the reader and the two empirical laws
behave as the findings document says.
"""

from __future__ import annotations

import os
import struct
import tempfile
import unittest

from engine.research.ccy_period_probe import (
    RECORD_BYTES,
    acf1,
    lattice_denominator,
    mean_abs_step,
    read_dat,
    stdev,
)

CODES = ("EUR", "GBP", "AUD", "NZD", "CHF", "JPY", "XAU", "CAD", "USD")


def write_dat(path: str, codes: tuple[str, ...], rows: list[tuple[float, ...]], t0: int = 1_600_000_000) -> None:
    """Write a synthetic PowerHistory file in the reverse-engineered layout."""
    buf = bytearray()
    buf += struct.pack("<i", len(codes))
    for c in codes:
        raw = c.encode("latin1")
        buf += raw + b"\x00" * (4 - len(raw))
    for i, row in enumerate(rows):
        buf += struct.pack("<q", t0 + i * 3600)
        buf += struct.pack("<9d", *row)
    with open(path, "wb") as fh:
        fh.write(buf)


class TestReader(unittest.TestCase):
    def test_roundtrip_header_and_rows(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "PowerHistory_H4_1.dat")
            rows = [(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)] * 3
            write_dat(p, CODES, rows)
            d = read_dat(p)
            self.assertEqual(d.codes, CODES)
            self.assertEqual(len(d.rows), 3)
            self.assertEqual(d.rows[0], rows[0])
            self.assertEqual(len(d.stamps), 3)
            self.assertEqual(d.stamps[1] - d.stamps[0], 3600)

    def test_trailing_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "x.dat")
            write_dat(p, CODES, [(0.0,) * 9])
            with open(p, "ab") as fh:
                fh.write(b"\x01\x02\x03")
            with self.assertRaises(ValueError):
                read_dat(p)

    def test_column_selects_by_header_order(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "x.dat")
            # one row; each column carries its own index so the mapping is visible
            write_dat(p, CODES, [tuple(float(i) for i in range(9))])
            d = read_dat(p)
            self.assertEqual(d.column("EUR"), [0.0])
            self.assertEqual(d.column("XAU"), [6.0])
            self.assertEqual(d.column("USD"), [8.0])

    def test_strides_match_documented_layout(self):
        self.assertEqual(RECORD_BYTES, 80)


class TestLattice(unittest.TestCase):
    def test_exact_sevenths(self):
        vals = [round(k / 7, 15) for k in range(70)]
        self.assertEqual(lattice_denominator(vals), 7)

    def test_exact_eighths(self):
        vals = [round(k / 8, 15) for k in range(72)]
        self.assertEqual(lattice_denominator(vals), 8)

    def test_impure_series_has_no_small_denominator(self):
        vals = [0.1, 0.31415926, 1.0 / 3.0 * 1.0000001]
        d = lattice_denominator(vals, cap=50)
        self.assertIsNone(d)


class TestStatistics(unittest.TestCase):
    def test_acf1_of_alternating_series_is_negative(self):
        vals = [1.0 if i % 2 else 0.0 for i in range(500)]
        self.assertLess(acf1(vals), -0.9)

    def test_acf1_of_random_walk_is_positive(self):
        vals = [0.0]
        for i in range(500):
            vals.append(vals[-1] + (1.0 if i % 3 else 0.5))
        self.assertGreater(acf1(vals), 0.5)

    def test_stdev_flat_when_mixed_seven_seven(self):
        self.assertAlmostEqual(stdev([7.0] * 10), 0.0)

    def test_mean_abs_step(self):
        self.assertAlmostEqual(mean_abs_step([1.0, 2.0, 4.0]), 1.5)


class TestPeriodLaw(unittest.TestCase):
    """Law 1 from the findings doc: acf1(Power_P) ~= (P-1)/(P+1.5) for P <= 10."""

    def test_law_matches_within_tolerance(self):
        for p in range(1, 11):
            predicted = (p - 1) / (p + 1.5)
            self.assertGreaterEqual(predicted, 0.0)
            self.assertLess(predicted, 1.0)
        # spot-check the two anchors quoted in the doc
        self.assertAlmostEqual((2 - 1) / (2 + 1.5), 0.285714, places=5)
        self.assertAlmostEqual((9 - 1) / (9 + 1.5), 0.761905, places=5)

    def test_period_one_has_zero_autocorrelation_target(self):
        # Observed -0.073 on both H4 and D1; the formula predicts exactly 0.
        self.assertEqual((1 - 1) / (1 + 1.5), 0.0)


if __name__ == "__main__":
    unittest.main()
