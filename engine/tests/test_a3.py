"""A3 tests: the four API operations, the MCP surface, and the daily batch.

Everything here runs **offline** against the recorded MT4 evidence CSV, so the
suite never needs the MT5 terminal or a live broker connection.

Run: python -m unittest discover -s engine/tests -t .
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine import api, daily

EVID = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "evidence", "a1")
BARS = os.path.join(EVID, "mt4_EURUSD_H1_bars.csv")
PAIR = os.path.join(EVID, "mt4_EURUSD_H1_bars.meta.csv")
META = PAIR if os.path.exists(PAIR) else None

FROM = "2026-09-17T02:00"
TO = "2026-11-16T17:00"

HAVE_MCP = importlib.util.find_spec("mcp") is not None


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()

#: the four tools requirement v0.2 §7 names, in order
REQUIRED_TOOLS = ("get_rates", "extract_waves", "compute_buckets", "export_table")

#: every error code the API may return — a client branches on these strings
ERROR_CODES = {
    api.E_BAD_ARG,
    api.E_NO_TERMINAL,
    api.E_SYMBOL,
    api.E_NO_DATA,
    api.E_SAMPLE,
    api.E_IO,
}


@unittest.skipUnless(os.path.exists(BARS), "MT4 evidence not present")
class TestGetRates(unittest.TestCase):
    def test_returns_ohlc_and_provenance(self):
        r = api.get_rates("EURUSD", "H1", FROM, TO, bars_csv=BARS, meta_in=META)
        self.assertTrue(r["ok"])
        self.assertGreater(r["barCount"], 1000)
        self.assertEqual(r["returned"], r["barCount"])
        for key in ("digits", "point", "pip", "timeframe", "firstBar", "lastBar", "engineVersion"):
            self.assertIn(key, r)
        bar = r["bars"][0]
        self.assertEqual(
            set(bar), {"time", "open", "high", "low", "close", "tickVolume"}
        )

    def test_limit_truncates_payload_only(self):
        full = api.get_rates("EURUSD", "H1", FROM, TO, bars_csv=BARS, meta_in=META)
        cut = api.get_rates(
            "EURUSD", "H1", FROM, TO, bars_csv=BARS, meta_in=META, limit=5
        )
        self.assertEqual(cut["barCount"], full["barCount"])
        self.assertEqual(cut["returned"], 5)
        # newest bars are kept
        self.assertEqual(cut["bars"][-1], full["bars"][-1])

    def test_past_bars_instead_of_window(self):
        r = api.get_rates("EURUSD", "H1", past_bars=200, bars_csv=BARS, meta_in=META)
        self.assertTrue(r["ok"])
        self.assertEqual(r["barCount"], 200)

    def test_window_and_past_bars_are_mutually_exclusive(self):
        r = api.get_rates("EURUSD", "H1", FROM, TO, past_bars=200, bars_csv=BARS)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["code"], api.E_BAD_ARG)

    def test_accepts_dotted_and_spaced_labels(self):
        a = api.get_rates("EURUSD", "H1", "2026.09.17 02:00", "2026.11.16 17:00",
                          bars_csv=BARS, meta_in=META)
        b = api.get_rates("EURUSD", "H1", FROM, TO, bars_csv=BARS, meta_in=META)
        self.assertTrue(a["ok"])
        self.assertEqual(a["firstBar"], b["firstBar"])
        self.assertEqual(a["lastBar"], b["lastBar"])

    def test_unknown_timeframe_is_bad_argument(self):
        r = api.get_rates("EURUSD", "Z9", FROM, TO, bars_csv=BARS)
        self.assertFalse(r["ok"])
        self.assertEqual(r["error"]["code"], api.E_BAD_ARG)

    def test_missing_window_is_bad_argument(self):
        r = api.get_rates("EURUSD", "H1", bars_csv=BARS)
        self.assertEqual(r["error"]["code"], api.E_BAD_ARG)

    def test_missing_csv_is_no_data(self):
        r = api.get_rates("EURUSD", "H1", FROM, TO, bars_csv="does/not/exist.csv")
        self.assertFalse(r["ok"])
        self.assertIn(r["error"]["code"], {api.E_NO_DATA, api.E_BAD_ARG})


@unittest.skipUnless(os.path.exists(BARS), "MT4 evidence not present")
class TestExtractWavesApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r = api.extract_waves("EURUSD", "H1", FROM, TO, bars_csv=BARS, meta_in=META)

    def test_parity_wave_count(self):
        self.assertTrue(self.r["ok"])
        self.assertEqual(self.r["waveCount"], 49)

    def test_wave_fields_complete(self):
        w = self.r["waves"][0]
        self.assertEqual(
            set(w), {"idx", "startTime", "endTime", "bars", "amplitudePips", "direction"}
        )

    def test_params_are_echoed(self):
        p = self.r["params"]
        self.assertEqual(p["depth"], 12)
        self.assertEqual(p["deviationPoints"], 5)
        self.assertEqual(p["backstep"], 3)
        self.assertEqual(p["mergePct"], 35.0)
        self.assertEqual(p["mergeMode"], "drop_next")

    def test_backstep_ge_depth_is_bad_argument(self):
        r = api.extract_waves("EURUSD", "H1", FROM, TO, bars_csv=BARS, depth=3, backstep=3)
        self.assertEqual(r["error"]["code"], api.E_BAD_ARG)

    def test_bad_merge_mode_is_bad_argument(self):
        r = api.extract_waves("EURUSD", "H1", FROM, TO, bars_csv=BARS, merge_mode="nope")
        self.assertEqual(r["error"]["code"], api.E_BAD_ARG)


class TestComputeBucketsApi(unittest.TestCase):
    def test_direct_amplitudes(self):
        amps = [float(i) for i in range(1, 50)]
        r = api.compute_buckets(amplitudes=amps, bar_counts=[10] * 49)
        self.assertTrue(r["ok"])
        self.assertEqual([b["count"] for b in r["buckets"]], [39, 7, 3])
        self.assertEqual(r["source"], "supplied")

    def test_band_labels_verbatim(self):
        amps = [float(i) for i in range(1, 50)]
        r = api.compute_buckets(amplitudes=amps, bar_counts=[10] * 49)
        self.assertEqual(
            [b["band"] for b in r["buckets"]], ["80% Range", "15% Range", "5% Range"]
        )
        blob = json.dumps(r)
        for forbidden in ("P80", "P95", "Pmax"):
            self.assertNotIn(forbidden, blob)

    def test_bar_counts_length_mismatch(self):
        r = api.compute_buckets(amplitudes=[1.0, 2.0, 3.0], bar_counts=[1, 2])
        self.assertEqual(r["error"]["code"], api.E_BAD_ARG)

    def test_unknown_method(self):
        r = api.compute_buckets(amplitudes=[1.0, 2.0, 3.0], method="nope")
        self.assertEqual(r["error"]["code"], api.E_BAD_ARG)

    def test_thin_sample_is_insufficient(self):
        r = api.compute_buckets(amplitudes=[10.0, 20.0], bar_counts=[5, 5])
        self.assertEqual(r["error"]["code"], api.E_SAMPLE)
        self.assertEqual(r["error"]["found"], 2)
        self.assertEqual(r["error"]["required"], 3)

    def test_needs_amplitudes_or_symbol(self):
        self.assertEqual(api.compute_buckets()["error"]["code"], api.E_BAD_ARG)

    @unittest.skipUnless(os.path.exists(BARS), "MT4 evidence not present")
    def test_pipeline_matches_offline_evidence(self):
        r = api.compute_buckets("EURUSD", "H1", FROM, TO, bars_csv=BARS, meta_in=META)
        self.assertTrue(r["ok"])
        self.assertEqual(r["swingCount"], 49)
        self.assertEqual([b["count"] for b in r["buckets"]], [39, 7, 3])
        self.assertEqual(r["buckets"][1]["totalBars"], 211)
        self.assertAlmostEqual(r["buckets"][1]["totalPips"], 831.1, places=1)
        self.assertAlmostEqual(r["buckets"][2]["totalPips"], 551.3, places=1)
        self.assertEqual(r["rangeBounds"][:3], [12, 110, 128])


@unittest.skipUnless(os.path.exists(BARS), "MT4 evidence not present")
class TestExportTableApi(unittest.TestCase):
    def test_writes_all_artefacts_with_hashes(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = api.export_table(
                out_dir=tmp, symbol="EURUSD", tf="H1", start=FROM, end=TO,
                bars_csv=BARS, meta_in=META,
            )
            self.assertTrue(r["ok"])
            arts = r["artifacts"]
            self.assertEqual(
                set(arts), {"waves", "wavesMeta", "tableCsv", "tableJson"}
            )
            for key in ("waves", "tableCsv", "tableJson"):
                path = arts[key]["path"]
                self.assertTrue(os.path.exists(path), key)
                self.assertEqual(len(arts[key]["sha256"]), 64, key)

    def test_second_run_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            kwargs = dict(symbol="EURUSD", tf="H1", start=FROM, end=TO,
                          bars_csv=BARS, meta_in=META)
            ra = api.export_table(out_dir=a, **kwargs)
            rb = api.export_table(out_dir=b, **kwargs)
            for key in ("waves", "tableCsv", "tableJson"):
                self.assertEqual(
                    ra["artifacts"][key]["sha256"], rb["artifacts"][key]["sha256"],
                    f"{key} must be deterministic",
                )

    def test_artefact_paths_use_forward_slashes(self):
        """A Windows run and a WSL run must produce the same manifest JSON."""
        with tempfile.TemporaryDirectory() as tmp:
            r = api.export_table(
                out_dir=tmp, symbol="EURUSD", tf="H1", start=FROM, end=TO,
                bars_csv=BARS, meta_in=META,
            )
            for key, a in r["artifacts"].items():
                self.assertNotIn("\\", a["path"], key)

    def test_table_row_shape(self):
        with tempfile.TemporaryDirectory() as tmp:
            api.export_table(
                out_dir=tmp, symbol="EURUSD", tf="H1", start=FROM, end=TO,
                bars_csv=BARS, meta_in=META,
            )
            doc = json.loads(
                _read(os.path.join(tmp, "EURUSD_H1.table.json"))
            )
            self.assertEqual(len(doc["bands"]), 3)
            self.assertEqual(doc["detail"][1]["totalBars"], 211)

    def test_insufficient_sample_surfaces(self):
        with tempfile.TemporaryDirectory() as tmp:
            r = api.export_table(
                out_dir=tmp, symbol="EURUSD", tf="H1",
                start="2026-11-17T00:00", end="2026-11-17T06:00",
                bars_csv=BARS, meta_in=META,
            )
            self.assertFalse(r["ok"])
            self.assertIn(r["error"]["code"], {api.E_SAMPLE, api.E_NO_DATA})
            # nothing half-written
            self.assertEqual(
                [f for f in os.listdir(tmp) if f.endswith(".table.csv")], []
            )


class TestErrorCodeContract(unittest.TestCase):
    def test_codes_are_stable_strings(self):
        self.assertEqual(
            (api.E_BAD_ARG, api.E_NO_TERMINAL, api.E_SYMBOL, api.E_NO_DATA,
             api.E_SAMPLE, api.E_IO),
            ("bad_argument", "no_terminal", "unknown_symbol", "no_data",
             "insufficient_sample", "io_error"),
        )

    def test_every_failure_carries_code_and_message(self):
        failures = [
            api.get_rates("EURUSD", "H1"),
            api.extract_waves("EURUSD", "H1"),
            api.compute_buckets(),
        ]
        for r in failures:
            self.assertFalse(r["ok"])
            self.assertIn(r["error"]["code"], ERROR_CODES)
            self.assertTrue(r["error"]["message"])


@unittest.skipUnless(HAVE_MCP, "mcp package not installed")
class TestMcpSurface(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from engine.mcp_server import TOOL_NAMES, build_server

        cls.server = build_server()
        cls.tool_names = TOOL_NAMES

    def test_exactly_the_four_required_tools(self):
        self.assertEqual(tuple(self.tool_names), REQUIRED_TOOLS)

    def test_registration_matches_requirement(self):
        import asyncio

        tools = asyncio.run(self.server.list_tools())
        self.assertEqual([t.name for t in tools], list(REQUIRED_TOOLS))

    def test_each_tool_has_a_schema_and_description(self):
        import asyncio

        for t in asyncio.run(self.server.list_tools()):
            self.assertTrue(t.description, t.name)
            self.assertIn("properties", t.input_schema, t.name)

    def test_export_table_requires_out_dir(self):
        import asyncio

        tools = {t.name: t for t in asyncio.run(self.server.list_tools())}
        self.assertEqual(
            sorted(tools["export_table"].input_schema.get("required") or []),
            ["out_dir", "symbol"],
        )

    @unittest.skipUnless(os.path.exists(BARS), "MT4 evidence not present")
    def test_call_tool_returns_json_payload(self):
        import asyncio

        res = asyncio.run(
            self.server.call_tool(
                "compute_buckets",
                {"symbol": "EURUSD", "tf": "H1", "start": FROM, "end": TO,
                 "bars_csv": BARS},
            )
        )
        self.assertFalse(getattr(res, "isError", False))
        payload = json.loads(res.content[0].text)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["swingCount"], 49)

    def test_unknown_tool_does_not_crash_the_server(self):
        import asyncio

        with self.assertRaises(Exception):
            asyncio.run(self.server.call_tool("no_such_tool", {}))


class TestDaily(unittest.TestCase):
    def test_dry_run_plans_without_touching_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "vol")
            m = daily.run_matrix(
                ["EURUSD", "gbpusd"], ["h1"], target, past_bars=1024, dry_run=True
            )
            self.assertEqual(m["totals"], {"requested": 2, "succeeded": 2, "failed": 0})
            self.assertFalse(os.path.exists(target))
            self.assertTrue(all(r["dryRun"] for r in m["results"]))

    def test_manifest_is_written_and_reloadable(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", daily.MANIFEST_NAME)
            m = daily.run_matrix(["EURUSD"], ["H1"], tmp, past_bars=1024, dry_run=True)
            daily.write_manifest(path, m)
            self.assertTrue(os.path.exists(path))
            back = json.loads(_read(path))
            self.assertEqual(back["engineVersion"], m["engineVersion"])
            self.assertEqual(back["totals"]["requested"], 1)
            self.assertIn("startedAt", back)

    def test_manifest_starts_without_bom_and_uses_lf(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "m.json")
            daily.write_manifest(path, daily.run_matrix([], [], tmp, dry_run=True))
            with open(path, "rb") as fh:
                raw = fh.read()
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertNotIn(b"\r\n", raw)

    @unittest.skipUnless(os.path.exists(BARS), "MT4 evidence not present")
    def test_one_failing_pair_does_not_abort_the_rest(self):
        """A bad window on the first pair must not cost the second its result."""
        with tempfile.TemporaryDirectory() as tmp:
            good = api.export_table(
                out_dir=tmp, symbol="EURUSD", tf="H1", start=FROM, end=TO,
                bars_csv=BARS, meta_in=META,
            )
            self.assertTrue(good["ok"])
            bad = api.export_table(
                out_dir=tmp, symbol="EURUSD", tf="H1",
                start="2026-11-17T00:00", end="2026-11-17T06:00",
                bars_csv=BARS, meta_in=META,
            )
            self.assertFalse(bad["ok"])

    @unittest.skipUnless(os.path.exists(BARS), "MT4 evidence not present")
    def test_matrix_runs_end_to_end_offline(self):
        """The real acceptance run: artefacts land on disk with hashes, no MT5."""
        with tempfile.TemporaryDirectory() as tmp:
            m = daily.run_matrix(
                ["EURUSD"], ["H1"], tmp, start=FROM, end=TO,
                past_bars=None, bars_csv=BARS, meta_in=META,
            )
            self.assertEqual(m["totals"], {"requested": 1, "succeeded": 1, "failed": 0})
            arts = m["results"][0]["artifacts"]
            for key in ("waves", "tableCsv", "tableJson"):
                self.assertTrue(os.path.exists(arts[key]["path"]), key)
                self.assertEqual(len(arts[key]["sha256"]), 64, key)

    @unittest.skipUnless(os.path.exists(BARS), "MT4 evidence not present")
    def test_matrix_survives_an_all_failing_run(self):
        """Everything failing is a clean non-zero manifest, not a traceback."""
        with tempfile.TemporaryDirectory() as tmp:
            m = daily.run_matrix(
                ["EURUSD"], ["H1"], tmp,
                start="2026-11-17T00:00", end="2026-11-17T06:00",
                past_bars=None, bars_csv=BARS, meta_in=META,
            )
            self.assertEqual(m["totals"]["succeeded"], 0)
            self.assertEqual(m["totals"]["failed"], 1)
            err = m["results"][0]["error"]
            self.assertIn(err["code"], {api.E_SAMPLE, api.E_NO_DATA})

    def test_cli_rejects_half_a_window(self):
        self.assertEqual(daily.main(["--from", FROM, "--quiet"]), daily.EXIT_ARGS)

    def test_cli_rejects_backstep_ge_depth(self):
        self.assertEqual(
            daily.main(["--dry-run", "--depth", "3", "--backstep", "3", "--quiet"]),
            daily.EXIT_ARGS,
        )

    def test_cli_rejects_tiny_sample(self):
        self.assertEqual(
            daily.main(["--dry-run", "--past-bars", "10", "--quiet"]), daily.EXIT_ARGS
        )

    def test_cli_dry_run_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = daily.main(
                ["--dry-run", "--out-dir", tmp, "--symbols", "EURUSD", "--quiet"]
            )
            self.assertEqual(rc, daily.EXIT_OK)

    @unittest.skipUnless(os.path.exists(BARS), "MT4 evidence not present")
    def test_cli_offline_run_writes_manifest_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = daily.main(
                ["--out-dir", tmp, "--symbols", "EURUSD", "--tf", "H1",
                 "--from", FROM, "--to", TO, "--bars-csv", BARS, "--quiet"]
            )
            self.assertEqual(rc, daily.EXIT_OK)
            manifest = json.loads(_read(os.path.join(tmp, daily.MANIFEST_NAME)))
            self.assertEqual(manifest["totals"]["succeeded"], 1)

    @unittest.skipUnless(os.path.exists(BARS), "MT4 evidence not present")
    def test_cli_exits_one_when_every_pair_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            rc = daily.main(
                ["--out-dir", tmp, "--symbols", "EURUSD", "--tf", "H1",
                 "--from", "2026-11-17T00:00", "--to", "2026-11-17T06:00",
                 "--bars-csv", BARS, "--quiet"]
            )
            self.assertEqual(rc, daily.EXIT_FAILED)


if __name__ == "__main__":
    unittest.main()
