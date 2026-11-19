"""Stage 1-2 tests: CSV ingestion, lot tiers, cycle splitting, .hst, wave bands.

Every fixture is written to a temp dir inside the test, so the suite needs no
``downloads/`` tree and no MT4 terminal.

Run: python -m unittest discover -s engine/tests -t .
"""

from __future__ import annotations

import os
import struct
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from engine.bar import Bar
from engine.martingale.hst_reader import (
    HEADER_BYTES,
    RECORD_BYTES,
    load_hst_bars,
    read_hst,
    sanity_check,
    to_bars,
)
from engine.martingale.ingest import IngestReport, filter_by_date, is_summary_row, read_trades
from engine.martingale.layers import (
    _excel_round2,
    compare_methods,
    detect,
    detect_excel,
    detect_linear,
)
from engine.martingale.scanner import Cycle, ScanResult, split_cycles, scan_symbol, step_stats
from engine.martingale.waves import (
    merge_amplitudes,
    pip_size_from_digits,
    quantile,
    scan_waves,
)

HEADER_A = (
    "Open Time,Type,Lots,Symbol,Open Price,Close Time,Close Price,Commission,Swap,"
    "Net Pips,Net Profit,Max Profit,Max Pips,Max Loss,Max Loss Pips,Magic Number,"
    "Comment,Holding Time (Hours),Holding Time"
)
HEADER_B = (
    "Open Time,Type,Lots,Symbol,Open Price,Close Time,Close Price,Commission,Swap,"
    "Net Pips,Net Profit,Max Profit,Max Pips,Max Loss,Max Loss Pips,Magic Number,"
    "Comment,Holding Time (Hours)"
)
HEADER_C = (
    "Open Time,Type,Lots,Symbol,Open Price,Close Time,Close Price,Commission,Swap,"
    "Net Profit,Holding Time (Hours),Max Profit,Max Pips,Max Loss,Max Loss Pips,"
    "Magic Number,Comment,Net Pips"
)

ROW = "{t},buy,{lots},{sym},1.10000,{ct},1.10100,0.00,0.00,10.00,{profit},20.00,20.0,{loss},5.00,1,Wayne Class,1.00,1.00hrs"

#: Variant C puts ``Net Profit`` and ``Holding Time`` before ``Max Profit``, so a
#: positional row built for A would silently land values in the wrong columns.
ROW_C = "{t},buy,{lots},{sym},1.10000,{ct},1.10100,0.00,0.00,{profit},1.00,20.00,20.0,{loss},5.00,1,Wayne Class,10.00"


def _row(day: int, lots: float = 0.10, profit: float = 10.0, loss: float = -3.0, sym: str = "EURUSD") -> str:
    t = f"{day:02d}/07/2026 03:42:23"
    ct = f"{day:02d}/07/2026 05:42:23"
    return ROW.format(t=t, lots=lots, sym=sym, ct=ct, profit=profit, loss=loss)


def _row_c(day: int, lots: float = 0.10, profit: float = 10.0, loss: float = -3.0, sym: str = "EURUSD") -> str:
    t = f"{day:02d}/07/2026 03:42:23"
    ct = f"{day:02d}/07/2026 05:42:23"
    return ROW_C.format(t=t, lots=lots, sym=sym, ct=ct, profit=profit, loss=loss)


class TempDirCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = self._tmp.name

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def write(self, name: str, lines, encoding: str = "utf-8") -> str:
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding=encoding, newline="") as fh:
            fh.write("\n".join(lines) + "\n")
        return path


class IngestHeaderVariants(TempDirCase):
    """The three header shapes in ``downloads/`` must all parse."""

    def test_header_variant_a(self) -> None:
        path = self.write("a.csv", [HEADER_A, _row(1)])
        rep = IngestReport()
        trades = read_trades(path, rep)
        self.assertEqual(rep.kept, 1)
        self.assertEqual(trades[0].symbol, "EURUSD")
        self.assertAlmostEqual(trades[0].lots, 0.10)

    def test_header_variant_b_without_last_column(self) -> None:
        path = self.write("b.csv", [HEADER_B, _row(2)])
        rep = IngestReport()
        trades = read_trades(path, rep)
        self.assertEqual(rep.kept, 1)
        self.assertEqual(trades[0].direction, "buy")

    def test_header_variant_c_reordered(self) -> None:
        path = self.write("c.csv", [HEADER_C, _row_c(3, profit=12.5)])
        trades = read_trades(path)
        self.assertEqual(len(trades), 1)
        self.assertAlmostEqual(trades[0].net_profit, 12.5)

    def test_bom_is_tolerated(self) -> None:
        path = self.write("bom.csv", [HEADER_A, _row(4)], encoding="utf-8-sig")
        self.assertEqual(len(read_trades(path)), 1)


class IngestRowFiltering(TempDirCase):
    """Junk rows are counted, not silently kept or silently dropped."""

    def test_summary_row_is_dropped_and_counted(self) -> None:
        summary = (
            "01/08/2026 00:00:00,buy,0.00,profit,0.00000,,0.00000,0.00,0.00,0.00,"
            "1234.56,0.00,0.00,0.00,0.00,0,Summary trade result 07.2026,0.00,0.00hrs"
        )
        path = self.write("s.csv", [HEADER_A, _row(1), summary])
        rep = IngestReport()
        trades = read_trades(path, rep)
        self.assertEqual(rep.kept, 1)
        self.assertEqual(rep.dropped_summary, 1)
        self.assertEqual(len(trades), 1)

    def test_balance_and_dividend_rows_are_dropped(self) -> None:
        bal = "01/07/2026 00:00:00,balance,0.00,,0.00000,,0.00000,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0.00,0,,0.00,0.00hrs"
        div = "01/07/2026 00:00:00,credit,0.01,,0.00000,,0.00000,0.00,0.00,0.00,0.07,0.07,0.00,0.00,0.00,0,Dividend #1,0.00,0.00hrs"
        path = self.write("bal.csv", [HEADER_A, bal, div, _row(5)])
        rep = IngestReport()
        read_trades(path, rep)
        self.assertEqual(rep.dropped_non_trade, 2)
        self.assertEqual(rep.kept, 1)

    def test_index_cfd_symbols_are_kept(self) -> None:
        """``HK50``/``FRA40``/``SP500`` are real instruments, not junk."""
        path = self.write("idx.csv", [HEADER_A, _row(6, sym="HK50"), _row(7, sym="FRA40")])
        trades = read_trades(path)
        self.assertEqual([t.symbol for t in trades], ["HK50", "FRA40"])

    def test_empty_file_yields_no_trades_and_does_not_raise(self) -> None:
        path = self.write("empty.csv", [])
        rep = IngestReport()
        self.assertEqual(read_trades(path, rep), [])
        self.assertEqual(rep.total_rows, 0)

    def test_header_only_file(self) -> None:
        path = self.write("honly.csv", [HEADER_A])
        self.assertEqual(len(read_trades(path)), 0)

    def test_is_summary_row_helper(self) -> None:
        self.assertTrue(is_summary_row("profit", ""))
        self.assertTrue(is_summary_row("EURUSD", "Summary trade result 06.2026"))
        self.assertFalse(is_summary_row("EURUSD", "Wayne Class"))

    def test_open_price_is_read_from_the_row(self) -> None:
        """Regression: ``open_price`` was left unset and every row failed."""
        path = self.write("op.csv", [HEADER_A, _row(8)])
        trades = read_trades(path)
        self.assertAlmostEqual(trades[0].open_price, 1.10000)

    def test_date_filter_keeps_window_only(self) -> None:
        path = self.write("d.csv", [HEADER_A, _row(1), _row(10), _row(20)])
        trades = read_trades(path)
        from datetime import datetime

        kept = filter_by_date(trades, start=datetime(2026, 7, 5), end=datetime(2026, 7, 15))
        self.assertEqual(len(kept), 1)


def _trade(direction: str = "buy", lots: float = 0.02, day: int = 1, symbol: str = "EURUSD", open_price: float = 1.1):
    from engine.martingale.ingest import Trade
    from datetime import datetime

    return Trade(
        symbol=symbol,
        direction=direction,
        lots=lots,
        open_time=datetime(2026, 7, day, 3, 0, 0),
        close_time=datetime(2026, 7, day, 5, 0, 0),
        open_price=open_price,
        net_pips=10.0,
        net_profit=10.0,
        max_profit=20.0,
        max_pips=20.0,
        max_loss=5.0,
        max_loss_pips=5.0,
        magic="1",
        comment="Wayne Class",
    )


class LotTiers(unittest.TestCase):
    def test_excel_round_matches_excel_half_away_from_zero(self) -> None:
        """Python's banker's rounding would give 0.04 here; Excel gives 0.05."""
        self.assertAlmostEqual(_excel_round2(0.045), 0.05)
        self.assertAlmostEqual(_excel_round2(0.035), 0.04)
        self.assertAlmostEqual(_excel_round2(-0.045), -0.05)

    def test_excel_layers_on_a_1_5_chain(self) -> None:
        lots = [0.02] * 8 + [0.03] * 5 + [0.05] * 3 + [0.07] * 2
        model = detect_excel([_trade(lots=x) for x in lots])
        self.assertAlmostEqual(model.base, 0.02)
        self.assertAlmostEqual(model.step, 1.5)
        self.assertGreaterEqual(model.max_layer, 3)
        self.assertEqual(model.counts.get(1), 8)

    def test_excel_and_linear_disagree_on_the_same_input(self) -> None:
        """Different methods, different answers -- that is why both exist."""
        lots = [0.01] * 6 + [0.02] * 4 + [0.04] * 3 + [0.08] * 2
        trades = [_trade(lots=x) for x in lots]
        both = compare_methods(trades)
        self.assertEqual(both["excel"].base, 0.01)
        self.assertAlmostEqual(both["excel"].step, 2.0)
        self.assertEqual(both["excel"].max_layer, 4)
        self.assertEqual(both["linear"].base, 0.01)
        self.assertEqual(both["linear"].max_layer, 8)

    def test_single_lot_series_lands_entirely_on_layer_one(self) -> None:
        model = detect([_trade(lots=0.10) for _ in range(5)])
        self.assertEqual(model.counts, {1: 5})
        self.assertIsNone(model.step)

    def test_unknown_method_raises(self) -> None:
        with self.assertRaises(ValueError):
            detect([_trade()], method="nope")

    def test_empty_trade_list_is_not_an_error(self) -> None:
        model = detect_excel([])
        self.assertEqual(model.base, 0.0)
        self.assertEqual(model.counts, {})


class CycleSplitting(unittest.TestCase):
    def test_gap_splits_two_baskets(self) -> None:
        trades = [_trade(day=1, lots=0.01), _trade(day=2, lots=0.02), _trade(day=10, lots=0.01)]
        cycles = split_cycles(trades, gap_hours=24.0)
        self.assertEqual(len(cycles), 2)
        self.assertEqual(len(cycles[0].trades), 2)
        self.assertEqual(len(cycles[1].trades), 1)

    def test_directions_never_mix(self) -> None:
        trades = [_trade(direction="buy", lots=0.01), _trade(direction="sell", lots=0.01)]
        cycles = split_cycles(trades)
        self.assertEqual({c.direction for c in cycles}, {"buy", "sell"})

    def test_step_stats_multiplier_and_break_even(self) -> None:
        trades = [_trade(lots=0.01, open_price=1.1000), _trade(lots=0.02, open_price=1.0950)]
        cycle = Cycle("EURUSD", "buy", trades)
        stats = step_stats(cycle, open_prices=[1.1000, 1.0950])
        self.assertAlmostEqual(stats.first_lot, 0.01)
        self.assertAlmostEqual(stats.last_lot, 0.02)
        self.assertAlmostEqual(stats.multiplier, 2.0)
        # lot-weighted break-even: (0.01*1.1 + 0.02*1.095) / 0.03
        self.assertAlmostEqual(stats.break_even, (0.01 * 1.1 + 0.02 * 1.095) / 0.03)
        self.assertAlmostEqual(stats.cumulative_distance, 0.005)

    def test_step_stats_falls_back_to_the_trades_own_open_price(self) -> None:
        cycle = Cycle("EURUSD", "buy", [_trade(lots=0.01, open_price=1.1000), _trade(lots=0.02, open_price=1.0950)])
        stats = step_stats(cycle)
        self.assertAlmostEqual(stats.break_even, (0.01 * 1.1 + 0.02 * 1.095) / 0.03)
        self.assertAlmostEqual(stats.cumulative_distance, 0.005)

    def test_step_stats_with_a_blank_open_price_returns_none(self) -> None:
        """A single blank price disqualifies the basket rather than skewing it."""
        cycle = Cycle("EURUSD", "buy", [_trade(lots=0.01, open_price=1.1), _trade(lots=0.02, open_price=0.0)])
        stats = step_stats(cycle)
        self.assertIsNone(stats.break_even)
        self.assertIsNone(stats.cumulative_distance)

    def test_scan_symbol_reports_deepest_layers(self) -> None:
        trades = [_trade(day=1, lots=0.01), _trade(day=1, lots=0.02), _trade(day=1, lots=0.04)]
        results = scan_symbol(trades, "EURUSD")
        self.assertEqual(len(results), 1)
        self.assertIsInstance(results[0], ScanResult)
        self.assertEqual(results[0].deepest_layers, 3)


def write_hst(path: str, rows) -> None:
    """Write a synthetic ``.hst`` with the real 60-byte record shape.

    The record is ``int32 time``, ``int32 pad``, four doubles, ``int32 volume``,
    ``int32 pad``, ``int32 spread``, ``8 bytes pad``. The padding slots are the
    reason a naive ``<q`` for time and ``<d`` for volume "works" on the first
    field and fails on volume.
    """
    blob = bytearray(b"\x00" * HEADER_BYTES)
    for epoch, o, h, l, c, vol in rows:
        blob += struct.pack("<i", epoch)
        blob += struct.pack("<i", 0)
        blob += struct.pack("<4d", o, h, l, c)
        blob += struct.pack("<i", vol)
        blob += struct.pack("<i", 0)
        blob += struct.pack("<i", 0)
        blob += b"\x00" * 8
    assert len(blob) == HEADER_BYTES + len(rows) * RECORD_BYTES
    with open(path, "wb") as fh:
        fh.write(blob)


class HstReader(TempDirCase):
    def test_round_trip(self) -> None:
        path = os.path.join(self.dir, "EURUSD60.hst")
        write_hst(path, [(1_600_000_000, 1.10, 1.12, 1.09, 1.11, 1234)])
        recs = read_hst(path)
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0].tick_volume, 1234)
        self.assertAlmostEqual(recs[0].close, 1.11)
        with open(path, "rb") as fh:
            self.assertEqual(len(fh.read()), HEADER_BYTES + RECORD_BYTES)

    def test_volume_read_as_float64_would_be_a_denormal(self) -> None:
        """Documents the trap: the same four bytes as a double are ~1e-320."""
        path = os.path.join(self.dir, "v.hst")
        write_hst(path, [(1_600_000_000, 1.1, 1.1, 1.1, 1.1, 2365)])
        with open(path, "rb") as fh:
            raw = fh.read()[HEADER_BYTES:]
        as_double = struct.unpack_from("<d", raw, 40)[0]
        self.assertLess(as_double, 1e-300)
        self.assertEqual(read_hst(path)[0].tick_volume, 2365)

    def test_partial_trailing_record_is_dropped(self) -> None:
        path = os.path.join(self.dir, "p.hst")
        write_hst(path, [(1_600_000_000, 1.1, 1.1, 1.1, 1.1, 10)])
        with open(path, "ab") as fh:
            fh.write(b"\x00" * 17)  # half a record
        self.assertEqual(len(read_hst(path)), 1)

    def test_too_short_file_yields_nothing(self) -> None:
        path = os.path.join(self.dir, "tiny.hst")
        with open(path, "wb") as fh:
            fh.write(b"\x00" * 40)
        self.assertEqual(read_hst(path), [])

    def test_sanity_check_flags_bad_ohlc(self) -> None:
        path = os.path.join(self.dir, "bad.hst")
        write_hst(path, [(1_600_000_000, 1.1, 1.0, 1.2, 1.1, 10)])
        ok, reason = sanity_check(read_hst(path))
        self.assertFalse(ok)
        self.assertIn("low", reason)

    def test_bars_keep_chronological_labels(self) -> None:
        path = os.path.join(self.dir, "b.hst")
        write_hst(path, [(1_600_000_000, 1.1, 1.1, 1.1, 1.1, 1), (1_600_003_600, 1.1, 1.1, 1.1, 1.1, 1)])
        bars = load_hst_bars(path)
        self.assertEqual(len(bars), 2)
        self.assertLess(bars[0].time_label, bars[1].time_label)


class WaveBands(unittest.TestCase):
    def test_quantile_matches_linear_interpolation(self) -> None:
        vals = [10.0, 20.0, 30.0, 40.0, 50.0]
        self.assertAlmostEqual(quantile(vals, 0.0), 10.0)
        self.assertAlmostEqual(quantile(vals, 1.0), 50.0)
        self.assertAlmostEqual(quantile(vals, 0.5), 30.0)
        self.assertAlmostEqual(quantile(vals, 0.25), 20.0)

    def test_quantile_single_value(self) -> None:
        self.assertAlmostEqual(quantile([7.0], 0.9), 7.0)

    def test_quantile_empty_raises(self) -> None:
        with self.assertRaises(ValueError):
            quantile([], 0.5)

    def test_merge_drops_swings_small_relative_to_previous(self) -> None:
        from engine.zigzag import Pivot

        pivots = [
            Pivot(0, "t0", 1.1000, "L"),
            Pivot(1, "t1", 1.1100, "H"),  # +100, kept
            Pivot(2, "t2", 1.1090, "L"),  # 10 < 0.35*100 -> dropped
            Pivot(3, "t3", 1.1200, "H"),  # 110 >= 0.35*100 -> kept
        ]
        amps = merge_amplitudes(pivots, merge_ratio=0.35)
        self.assertEqual(len(amps), 2)
        self.assertAlmostEqual(amps[0], 0.0100, places=6)
        self.assertAlmostEqual(amps[1], 0.0110, places=6)

    def test_pip_size_from_digits(self) -> None:
        self.assertAlmostEqual(pip_size_from_digits(5), 0.0001)
        self.assertAlmostEqual(pip_size_from_digits(3), 0.01)
        self.assertAlmostEqual(pip_size_from_digits(2), 0.01)

    def test_scan_needs_a_full_window(self) -> None:
        bars = [Bar(f"d{i}", 1.0, 1.0, 1.0, 1.0) for i in range(100)]
        scan = scan_waves(bars, window_bars=1024, step_bars=25)
        self.assertEqual(scan.windows, 0)

    def test_scan_produces_bands_on_a_sawtooth(self) -> None:
        """A synthetic zig-zag of ±80 pips must produce non-zero P80 bands."""
        bars = []
        price = 1.1000
        for i in range(400):
            step = 0.0080 if (i // 10) % 2 == 0 else -0.0080
            price += step
            high = price + 0.0002
            low = price - 0.0002
            bars.append(Bar(f"d{i}", price, high, low, price))
        scan = scan_waves(bars, pip_size=0.0001, window_bars=200, step_bars=50, depth=5, backstep=2)
        self.assertGreater(scan.windows, 0)
        bands = scan.median_bands()
        self.assertIsNotNone(bands)
        assert bands is not None
        self.assertGreater(bands.p80, 0)
        self.assertGreaterEqual(bands.p95, bands.p80)
        self.assertGreaterEqual(bands.high, bands.p95)


if __name__ == "__main__":
    unittest.main()
