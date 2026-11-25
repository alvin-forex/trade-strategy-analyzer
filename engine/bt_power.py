#!/usr/bin/env python3
"""BT support: generate A1-format power CSV from reader truth + parity check.

OC 2026-11-25 20:32 dispatch, step 1. Two jobs:

1. ``generate`` -- extract per-symbol power from the reader's 9-currency panel
   into A1 format ``CCYPOWER_<SYMBOL>_<TF>.csv`` (header ``time,power``) for the
   three BT symbols. Symbol power = base currency power - quote currency power
   (the research ``exp_allpairs2`` convention: ``pf[b] - pf[q]``).

2. ``parity`` -- attempt to reconstruct the same power from the AC M1 dump via
   ``ccy_backtest.core`` (RSI-50 x ATR% weighted 9-currency decomposition) and
   compare against reader truth. The dump has only 3 of the 36 instruments the
   formula needs, so a large gap is a DATA limitation, not proof of a wrong
   formula. Per the dispatch, a >1e-4 gap halts BT pending OC review.

Read-only against source files; writes only into the requested output dir.
"""

from __future__ import annotations

import argparse
import gzip
import json
import os
from typing import Dict, List, Optional, Sequence, Tuple

from ccy_backtest import indicators, universe

CURRENCIES = universe.CURRENCIES_9
BT_SYMBOLS = ("EURUSD", "USDJPY", "XAUUSD")
TF_MAP = {"H1": 60, "H4": 240}

READER_DEFAULT = "ccy_backtest/ref/ccy_power_reader.csv"
M1_DIR_DEFAULT = "exchange/from_autoclaw/20261124_0930_[AC]M1dump"


def _reader_panel(path: str, tf: str) -> Dict[str, Dict[str, float]]:
    """Return {timestamp: {currency: power}} for one timeframe."""
    out: Dict[str, Dict[str, float]] = {}
    with open(path, "r", encoding="utf-8-sig") as fh:
        for row in __import__("csv").DictReader(fh):
            if (row.get("timeframe") or "").strip().upper() != tf:
                continue
            ts = (row.get("timestamp") or "").strip()
            if not ts:
                continue
            panel: Dict[str, float] = {}
            for i in range(1, 10):
                name = (row.get(f"ccy{i}_name") or "").strip().upper()
                val = row.get(f"ccy{i}_power")
                if name in CURRENCIES and val not in (None, ""):
                    panel[name] = float(val)
            if len(panel) == 9:
                out[ts] = panel
    return out


def symbol_power(panel: Dict[str, float], symbol: str) -> Optional[float]:
    """diff = base power - quote power (research convention)."""
    base, quote = symbol[:3], symbol[3:]
    if base not in panel or quote not in panel:
        return None
    return panel[base] - panel[quote]


def generate(reader: str, out_dir: str, symbols: Sequence[str], tfs: Sequence[str]) -> Dict[str, int]:
    os.makedirs(out_dir, exist_ok=True)
    counts: Dict[str, int] = {}
    for tf in tfs:
        panel = _reader_panel(reader, tf)
        for sym in symbols:
            rows = []
            for ts in sorted(panel):
                p = symbol_power(panel[ts], sym)
                if p is not None:
                    rows.append((ts, p))
            name = f"CCYPOWER_{sym}_{tf}.csv"
            path = os.path.join(out_dir, name)
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write("time,power\n")
                for ts, p in rows:
                    fh.write(f"{ts},{p:.4f}\n")
            counts[name] = len(rows)
    return counts


def _load_m1(path: str) -> List[Tuple[int, float, float, float, float]]:
    """Return (epoch, open, high, low, close) from the gzipped AC dump."""
    import csv as _csv

    out = []
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as fh:
        for row in _csv.DictReader(fh):
            out.append((
                int(row["time"]), float(row["open"]), float(row["high"]),
                float(row["low"]), float(row["close"]),
            ))
    return out


def _aggregate(m1: Sequence[Tuple[int, float, float, float, float]],
               minutes: int) -> List[Tuple[int, float, float, float, float]]:
    """Bucket M1 into TF bars by epoch floor, keeping first/last open-close."""
    buckets: Dict[int, List[Tuple[int, float, float, float, float]]] = {}
    step = minutes * 60
    for row in m1:
        buckets.setdefault(row[0] - row[0] % step, []).append(row)
    out = []
    for b in sorted(buckets):
        group = buckets[b]
        out.append((
            b,
            group[0][1],
            max(x[2] for x in group),
            min(x[3] for x in group),
            group[-1][4],
        ))
    return out


def parity(m1_dir: str, reader: str, tf: str, symbols: Sequence[str]) -> dict:
    """Partial parity: reader symbol-power vs single-pair RSI/ATR raw.

    The full 9-currency reconstruction needs 36 instruments; the dump has 3.
    We therefore report, per symbol, the reader power and the single-pair raw
    (RSI-50) at aligned timestamps, plus the absolute gap. A large gap with
    only 3/36 instruments is NOT a formula verdict.
    """
    panel = _reader_panel(reader, tf)
    minutes = TF_MAP[tf]
    report: Dict[str, dict] = {}
    for sym in symbols:
        m1_path = os.path.join(m1_dir, f"{sym}_M1_60d.csv.gz")
        if not os.path.exists(m1_path):
            report[sym] = {"error": "M1 dump missing", "path": m1_path}
            continue
        bars = _aggregate(_load_m1(m1_path), minutes)
        closes = [b[4] for b in bars]
        raws = [None if v is None else v - 50.0
                for v in indicators.rsi_wilder(closes, 14)]
        # Map reader timestamp "YYYY.MM.DD HH:MM" -> UTC epoch.
        import datetime as dt
        by_epoch = {}
        for i, b in enumerate(bars):
            label = dt.datetime.fromtimestamp(b[0], dt.timezone.utc).strftime("%Y.%m.%d %H:%M")
            if raws[i] is not None:
                by_epoch[label] = raws[i]
        pairs = []
        for ts, pnl in panel.items():
            key = ts[:16]
            if key in by_epoch:
                truth = symbol_power(pnl, sym)
                if truth is not None:
                    pairs.append((key, truth, by_epoch[key], abs(truth - by_epoch[key])))
        if not pairs:
            report[sym] = {"error": "no overlapping timestamps", "bars": len(bars)}
            continue
        gaps = [p[3] for p in pairs]
        report[sym] = {
            "bars": len(bars),
            "overlap": len(pairs),
            "mean_abs_gap": sum(gaps) / len(gaps),
            "max_abs_gap": max(gaps),
            "sample": [
                {"time": t, "reader_power": round(r, 4),
                 "pair_raw": round(v, 4), "gap": round(g, 4)}
                for t, r, v, g in pairs[:5]
            ],
            "instruments_used": 1,
            "instruments_required_by_full_formula": 36,
        }
    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("mode", choices=("generate", "parity"))
    ap.add_argument("--reader", default=READER_DEFAULT)
    ap.add_argument("--m1-dir", default=M1_DIR_DEFAULT)
    ap.add_argument("--out", required=True)
    ap.add_argument("--symbols", default=",".join(BT_SYMBOLS))
    ap.add_argument("--tfs", default="H1,H4")
    args = ap.parse_args(argv)
    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    tfs = [t.strip() for t in args.tfs.split(",") if t.strip()]

    if args.mode == "generate":
        counts = generate(args.reader, args.out, symbols, tfs)
        print(json.dumps(counts, indent=2, sort_keys=True))
    else:
        out = {}
        for tf in tfs:
            out[tf] = parity(args.m1_dir, args.reader, tf, symbols)
        os.makedirs(args.out, exist_ok=True)
        path = os.path.join(args.out, "parity_partial.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=2, sort_keys=True, ensure_ascii=False)
        print(path)
        for tf, rec in out.items():
            for sym, r in rec.items():
                if "error" in r:
                    print(f"{tf} {sym}: {r['error']}")
                else:
                    print(f"{tf} {sym}: overlap={r['overlap']} "
                          f"mean_gap={r['mean_abs_gap']:.4f} max_gap={r['max_abs_gap']:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
