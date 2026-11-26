"""Clone-panel generator for #37 parity (route A, OC/老闆 11-26 裁定).

Given a directory of AC M1 dumps (``<SYM>_M1_60d.csv.gz``) and a list of
original-indicator truth timestamps, rebuild the *clone* 9-currency panel at
those exact timestamps from M1 via the existing, tested primitives:

* :mod:`engine.m1_aggregation` -- M1 -> H1 fold (single source, no rewrite)
* :mod:`ccy_backtest.core` -- RSI-50 x ATR%-weighted 9-currency decomposition
* :func:`display_scale` -- OC 0940 candidate ``val = 4.5 + 0.09*pw``

Three correctness rules learned from review (all covered by tests):

1. **Frame**: truth stamps are MT4 *server* time (Alpari GMT+2 in winter),
   the dumps' ``time`` is UTC. Convert with an explicit, configurable offset
   before looking up M1 bars; never compare the two frames directly.
2. **Forming bar**: truth is sampled every 5 minutes inside one H1 bucket and
   *changes* within that bucket. Slice M1 at the target minute before folding,
   so the forming H1 bar's close is the close at that minute (no look-ahead).
3. **No fabrication**: refuse a target outside the actual first/last M1 epoch
   at minute granularity -- including same-bucket-but-past-last-bar and
   before-first-bar cases. Renaming an old bar to a new stamp is fake data.

Only 3 of the 36 instruments are available, so every output is a PARTIAL clone
and is labelled as such in a sidecar. No network, no terminal, no data
invention: a missing dump or an out-of-window timestamp is a hard error.
"""

from __future__ import annotations

import csv
import datetime as dt
import gzip
import json
import os
from typing import Dict, List, Optional, Sequence, Tuple

from ccy_backtest import core as bt_core
from ccy_backtest import series as bt_series

from .m1_aggregation import aggregate, timeframe_minutes, usable_buckets

DEFAULT_TF = "H1"
DEFAULT_SYMBOLS: Tuple[str, ...] = ("EURUSD", "USDJPY", "XAUUSD")
# Alpari MT4 server time is GMT+2 in winter (README_ohlc_supply.md:14).
# GMT+3 during EU summer time -- pass --server-offset-hours 3 for those dates.
DEFAULT_SERVER_OFFSET_HOURS = 2
FULL_UNIVERSE_SIZE = 36


class MissingM1Error(FileNotFoundError):
    """A requested instrument's M1 dump is absent."""


class TargetOutsideM1Error(ValueError):
    """The M1 dump does not cover a requested truth timestamp (minute level)."""


def display_scale(power: Optional[float]) -> Optional[float]:
    """Provisional RSI-space -> 0..9 panel mapping (OC 0940 candidate).

    ``val = 4.5 + 0.09*pw``: -50->0, 0->4.5, +50->9, all confirmed by OC
    0437/0438. Full precision is kept so the 1e-4 gate is not weakened by
    premature rounding. ``ccy_backtest.core.to_display_scale`` stays identity.
    """
    if power is None:
        return None
    return 4.5 + 0.09 * power


def load_m1_dir(m1_dir: str,
                symbols: Sequence[str] = DEFAULT_SYMBOLS) -> Dict[str, List[tuple]]:
    """Read gzipped AC M1 dumps -> ``{symbol: [(epoch_utc, o,h,l,c), ...]}``."""
    if not os.path.isdir(m1_dir):
        raise FileNotFoundError(f"M1 dump directory missing: {m1_dir}")
    out: Dict[str, List[tuple]] = {}
    for sym in symbols:
        path = os.path.join(m1_dir, f"{sym}_M1_60d.csv.gz")
        if not os.path.exists(path):
            continue  # caller decides which symbols are mandatory
        rows: List[tuple] = []
        with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as fh:
            for r in csv.DictReader(fh):
                rows.append((int(r["time"]), float(r["open"]), float(r["high"]),
                             float(r["low"]), float(r["close"])))
        rows.sort(key=lambda x: x[0])
        out[sym] = rows
    return out


def _truth_epoch(ts: str, server_offset_hours: int = DEFAULT_SERVER_OFFSET_HOURS) -> int:
    """Truth 'YYYY.MM.DD HH:MM' (MT4 server time) -> UTC epoch seconds."""
    s = ts.strip().replace(".", "-")
    parsed = dt.datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=dt.timezone.utc)
    return int(parsed.timestamp()) - int(server_offset_hours) * 3600


def _norm_label(ts: str) -> str:
    return ts.strip().replace(".", "-").replace(" ", "T")


def _bar_epoch(bar) -> int:
    parsed = dt.datetime.strptime(bar.time_label, "%Y-%m-%dT%H:%M")
    return int(parsed.replace(tzinfo=dt.timezone.utc).timestamp())


def targets_from_truth(truth_csv: str) -> List[Tuple[str, str]]:
    """Extract ordered ``(timestamp, tf)`` targets from a truth CSV."""
    out: List[Tuple[str, str]] = []
    with open(truth_csv, "r", encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            ts = (r.get("time") or r.get("timestamp") or "").strip()
            tf = (r.get("tf") or r.get("timeframe") or DEFAULT_TF).strip().upper()
            if ts:
                out.append((ts, tf))
    return out


def build_h1_data(series: Sequence[tuple], target_ts: str,
                  server_offset_hours: int = DEFAULT_SERVER_OFFSET_HOURS) -> dict:
    """Fold M1 into H1 up to the target minute, keeping the forming bar.

    The returned ``d`` values are unique keys; completed warm-up bars use UTC
    labels, the final forming bar uses the (server-frame) truth timestamp.
    """
    minutes = timeframe_minutes(DEFAULT_TF)
    bucket_width = minutes * 60
    if not series:
        raise TargetOutsideM1Error(f"empty M1 series for target {target_ts}")
    first_epoch, last_epoch = series[0][0], series[-1][0]
    target_utc = _truth_epoch(target_ts, server_offset_hours)
    if target_utc < first_epoch or target_utc > last_epoch:
        raise TargetOutsideM1Error(
            f"target {target_ts} (UTC {target_utc}) outside M1 coverage "
            f"[{first_epoch}, {last_epoch}]; refusing to fabricate a clone")

    target_bucket = target_utc - target_utc % bucket_width
    cut = [r for r in series if r[0] <= target_utc]
    seg = [r for r in cut if r[0] >= target_bucket]
    if not seg:
        raise TargetOutsideM1Error(
            f"no M1 bar in target bucket of {target_ts} (UTC bucket {target_bucket})")

    from engine.bar import Bar
    bars = [Bar(
        time_label=dt.datetime.fromtimestamp(e, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M"),
        open=o, high=h, low=l, close=c,
    ) for e, o, h, l, c in cut]
    agg = aggregate(bars, DEFAULT_TF)
    # Completed, trustworthy warm-up buckets only; the short forming bucket is
    # rebuilt explicitly below from M1 up to the exact truth minute.
    warm = [b for b in usable_buckets(agg) if _bar_epoch(b) < target_bucket]
    forming = Bar(
        time_label=_norm_label(target_ts),
        open=seg[0][1],
        high=max(r[2] for r in seg),
        low=min(r[3] for r in seg),
        close=seg[-1][4],
    )
    all_bars = warm + [forming]
    return {
        "d": [b.time_label for b in all_bars],
        "o": [b.open for b in all_bars],
        "h": [b.high for b in all_bars],
        "l": [b.low for b in all_bars],
        "c": [b.close for b in all_bars],
    }


def compute_clone_panels(m1_dir: str,
                         targets: Sequence[Tuple[str, str]],
                         symbols: Sequence[str] = DEFAULT_SYMBOLS,
                         server_offset_hours: int = DEFAULT_SERVER_OFFSET_HOURS
                         ) -> Dict[str, Dict[str, float]]:
    """Rebuild a clone panel per target timestamp (PARTIAL: 3 of 36)."""
    data = load_m1_dir(m1_dir, symbols)
    missing = [s for s in symbols if s not in data]
    if missing:
        raise MissingM1Error(f"missing M1 dumps: {', '.join(missing)}")
    instruments = list(symbols)
    out: Dict[str, Dict[str, float]] = {}
    for ts, tf in targets:
        if tf.upper() != DEFAULT_TF:
            raise ValueError(f"unsupported clone timeframe {tf!r}; only {DEFAULT_TF} for now")
        panel_data = {sym: build_h1_data(data[sym], ts, server_offset_hours)
                      for sym in instruments}
        rows = bt_core.compute_power_history(panel_data, DEFAULT_TF,
                                             instruments=instruments)
        if not rows:
            raise ValueError(f"clone produced no row for {ts}")
        row = rows[-1]
        out[ts] = {c: display_scale(row["power"].get(c))
                   for c in bt_core.universe.CURRENCIES_9
                   if row["power"].get(c) is not None}
    return out


def clone_meta(panels: Dict[str, Dict[str, float]],
               symbols: Sequence[str] = DEFAULT_SYMBOLS) -> dict:
    """Describe coverage so a partial clone can never pass as a full rebuild."""
    return {
        "coverage": (f"partial {len(symbols)}/{FULL_UNIVERSE_SIZE}"
                     if len(symbols) < FULL_UNIVERSE_SIZE
                     else f"full {FULL_UNIVERSE_SIZE}/{FULL_UNIVERSE_SIZE}"),
        "symbols": list(symbols),
        "missing_instruments": [i for i in bt_core.universe.INSTRUMENTS_36
                                if i not in set(symbols)],
        "targets": sorted(panels),
        "scale": "provisional OC candidate val=4.5+0.09*pw; core.to_display_scale untouched",
        "note": "PARTIAL reconstruction -- not a valid #37 full-universe parity clone",
    }


def write_clone_csv(panels: Dict[str, Dict[str, float]], out_path: str,
                    symbols: Sequence[str] = DEFAULT_SYMBOLS) -> str:
    """Write ``series.HEADER``-compatible CSV + a ``.meta.json`` sidecar.

    Header ``timestamp,tf,<lowercase 9 currencies>,avg`` is accepted by both
    ``ccy_backtest.series.read_cp_power_history`` and the #68 parity loader.
    """
    parent = os.path.dirname(os.path.abspath(out_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    currencies = list(bt_core.universe.CURRENCIES_9)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(bt_series.HEADER)
        for ts in sorted(panels):
            p = panels[ts]
            vals = [p.get(c) for c in currencies if p.get(c) is not None]
            avg = sum(vals) / len(vals) if vals else None
            w.writerow([ts, DEFAULT_TF] +
                       ["" if p.get(c) is None else f"{p[c]:.6f}" for c in currencies] +
                       ["" if avg is None else f"{avg:.6f}"])
    with open(out_path + ".meta.json", "w", encoding="utf-8") as fh:
        json.dump(clone_meta(panels, symbols), fh, indent=2, sort_keys=True,
                  ensure_ascii=False)
    return out_path


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI: M1 dump + truth CSV -> clone panel CSV (ready for the parity tool)."""
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--m1-dir", required=True, help="directory of <SYM>_M1_60d.csv.gz")
    ap.add_argument("--truth", required=True, help="original truth CSV (target timestamps)")
    ap.add_argument("--out", required=True, help="clone panel CSV path")
    ap.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS))
    ap.add_argument("--server-offset-hours", type=int, default=DEFAULT_SERVER_OFFSET_HOURS)
    args = ap.parse_args(argv)
    symbols = tuple(s.strip() for s in args.symbols.split(",") if s.strip())
    targets = targets_from_truth(args.truth)
    panels = compute_clone_panels(args.m1_dir, targets, symbols, args.server_offset_hours)
    path = write_clone_csv(panels, args.out, symbols)
    print(json.dumps({"targets": len(targets), "symbols": list(symbols),
                      "coverage": clone_meta(panels, symbols)["coverage"],
                      "out": path}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
