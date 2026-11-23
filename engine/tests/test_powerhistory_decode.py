"""Tests for engine.research.powerhistory_decode (issue #27, stage 0.5)."""

from __future__ import annotations

import csv
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

from engine.research.powerhistory_decode import (
    decode_one,
    load_manifest_hashes,
    main,
    sha256_of,
)
from engine.tests.test_research_period import CODES, write_dat


def run_cli(argv: list[str]) -> int:
    """Invoke main() with stdout captured so test logs stay readable."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        return main(argv)


class TestSha256(unittest.TestCase):
    def test_stable_and_matches_known_vector(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "x.bin")
            with open(p, "wb") as fh:
                fh.write(b"abc")
            # sha256("abc") is a published constant
            self.assertEqual(
                sha256_of(p),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
            )

    def test_identical_bytes_give_identical_hash(self):
        with tempfile.TemporaryDirectory() as td:
            a = os.path.join(td, "a.dat")
            b = os.path.join(td, "b.dat")
            write_dat(a, CODES, [(1.0,) * 9])
            write_dat(b, CODES, [(1.0,) * 9])
            self.assertEqual(sha256_of(a), sha256_of(b))


class TestDecodeOne(unittest.TestCase):
    def test_csv_has_header_and_reproducible_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "PowerHistory_H4_1.dat")
            write_dat(src, CODES, [(1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0)] * 3)
            out1 = os.path.join(td, "a.csv")
            out2 = os.path.join(td, "b.csv")

            info = decode_one(src, out1)
            decode_one(src, out2)

            self.assertEqual(info["rows"], 3)
            self.assertEqual(info["codes"], list(CODES))

            with open(out1, "rb") as fh:
                a = fh.read()
            with open(out2, "rb") as fh:
                b = fh.read()
            self.assertEqual(a, b, "decode must be byte-identical across runs")
            self.assertNotIn(b"\r\n", a, "must be LF-only so hashes are stable")

            rows = list(csv.reader(open(out1, encoding="utf-8")))
            self.assertEqual(rows[0][:2], ["timestamp_utc", "epoch"])
            self.assertEqual(rows[0][2:], list(CODES))
            self.assertEqual(len(rows), 4)  # header + 3 rows

    def test_column_order_follows_each_file_header(self):
        # family B stores a rotated order; the CSV must follow the file, not CODES
        rotated = ("GBP", "AUD", "NZD", "CAD", "CHF", "JPY", "XAU", "USD", "EUR")
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "PowerHistory_D1_10.dat")
            write_dat(src, rotated, [(float(i) for i in range(9))])
            out = os.path.join(td, "o.csv")
            decode_one(src, out)
            rows = list(csv.reader(open(out, encoding="utf-8")))
            self.assertEqual(rows[0][2:], list(rotated))


class TestManifest(unittest.TestCase):
    def test_load_manifest_maps_filename_to_entry(self):
        with tempfile.TemporaryDirectory() as td:
            mf = os.path.join(td, "PowerHistory_MANIFEST.json")
            with open(mf, "w", encoding="utf-8") as fh:
                json.dump({"files": [{"file": "A.dat", "sha256": "deadbeef"}]}, fh)
            got = load_manifest_hashes(td)
            self.assertEqual(got["A.dat"]["sha256"], "deadbeef")

    def test_missing_manifest_is_empty_not_error(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(load_manifest_hashes(td), {})

    def test_explicit_manifest_path_wins(self):
        with tempfile.TemporaryDirectory() as td:
            mf = os.path.join(td, "elsewhere.json")
            with open(mf, "w", encoding="utf-8") as fh:
                json.dump({"files": [{"file": "B.dat", "sha256": "cafe"}]}, fh)
            self.assertEqual(load_manifest_hashes(td, mf)["B.dat"]["sha256"], "cafe")


class TestCli(unittest.TestCase):
    def test_exit_zero_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            src_dir = os.path.join(td, "in")
            os.makedirs(src_dir)
            write_dat(os.path.join(src_dir, "PowerHistory_H4_1.dat"), CODES, [(0.5,) * 9] * 2)
            write_dat(os.path.join(src_dir, "PowerHistory_H4_2.dat"), CODES, [(0.25,) * 9] * 2)
            out_dir = os.path.join(td, "out")

            rc = run_cli(["--dir", src_dir, "--out", out_dir])
            self.assertEqual(rc, 0)
            self.assertTrue(os.path.exists(os.path.join(out_dir, "PowerHistory_H4_1.csv")))
            mf = json.load(open(os.path.join(out_dir, "decode_manifest.json"), encoding="utf-8"))
            self.assertEqual(mf["file_count"], 2)
            self.assertEqual(len(mf["files"]), 2)

    def test_empty_dir_returns_two(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(run_cli(["--dir", td]), 2)

    def test_sha_mismatch_returns_one(self):
        with tempfile.TemporaryDirectory() as td:
            src_dir = os.path.join(td, "in")
            os.makedirs(src_dir)
            write_dat(os.path.join(src_dir, "PowerHistory_H4_1.dat"), CODES, [(1.0,) * 9])
            mf = os.path.join(td, "mf.json")
            with open(mf, "w", encoding="utf-8") as fh:
                json.dump({"files": [{"file": "PowerHistory_H4_1.dat", "sha256": "0" * 64}]}, fh)
            rc = run_cli(["--dir", src_dir, "--out", os.path.join(td, "out"), "--manifest", mf])
            self.assertEqual(rc, 1, "a sha256 mismatch must fail the run")


if __name__ == "__main__":
    unittest.main()
