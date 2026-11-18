"""Daily batch updater: run the engine over a symbol/timeframe matrix.

Requirement v0.2 §7 A3 acceptance is just「每日自動更新跑通」 — there is no
schedule, timezone, retry or symbol-list spec in the document.  So this module
deliberately does one thing well and leaves scheduling to the caller (Windows
Task Scheduler / cron / OpenClaw): it runs the matrix, writes the artefacts,
and exits non-zero if anything failed.

Default window
--------------
``--past-bars 1024`` — the indicator's own *Past X Bars* default.  Using the
vendor's own default keeps a daily run comparable to what the panel shows,
instead of drifting with whatever date range someone typed last time.  Pass
``--from/--to`` for a fixed backfill instead.

Determinism
-----------
The data artefacts are byte-identical for identical input: file names carry no
date, contents carry no timestamp, and the sha256 of each file is reported in
the manifest so a daily run can be diffed against yesterday's.  Only the
manifest itself carries ``startedAt``/``finishedAt`` — it is a log, not data.

Usage
-----
    python -m engine.daily                                   # EURUSD H1, 1024 bars
    python -m engine.daily --symbols EURUSD,GBPUSD,USDJPY --tf H1,H4
    python -m engine.daily --symbols-file symbols.txt --out-dir out/vol
    python -m engine.daily --from 2026-09-17T02:00 --to 2026-11-16T17:00
    python -m engine.daily --dry-run                         # plan only, no MT5 call

Exit codes
----------
0  every symbol/timeframe succeeded
1  at least one failed (details in the manifest)
2  bad arguments
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import sys
from typing import Any, Dict, List, Optional, Sequence

from . import api
from .version import ENGINE_VERSION

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_ARGS = 2

#: the vendor indicator's own *Past X Bars* default
DEFAULT_PAST_BARS = 1024
DEFAULT_SYMBOLS = ("EURUSD",)
DEFAULT_TFS = ("H1",)

MANIFEST_NAME = "manifest.json"


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [p.strip() for p in value.replace(";", ",").split(",") if p.strip()]


def _read_symbols_file(path: str) -> List[str]:
    out: List[str] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if line:
                out.append(line.upper())
    return out


def run_matrix(
    symbols: Sequence[str],
    timeframes: Sequence[str],
    out_dir: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    past_bars: Optional[int] = DEFAULT_PAST_BARS,
    method: str = "count",
    merge_pct: float = 35.0,
    depth: int = 12,
    deviation: int = 5,
    backstep: int = 3,
    dry_run: bool = False,
    bars_csv: Optional[str] = None,
    meta_in: Optional[str] = None,
) -> Dict[str, Any]:
    """Run every symbol x timeframe pair and return a manifest dict.

    One failing pair never aborts the rest — a single delisted symbol must not
    cost you the whole day's table.
    """
    started = dt.datetime.now(dt.timezone.utc)
    results: List[Dict[str, Any]] = []

    for sym in symbols:
        for tf in timeframes:
            key = f"{sym}_{tf}"
            if dry_run:
                results.append(
                    {
                        "symbol": sym,
                        "timeframe": tf,
                        "ok": True,
                        "dryRun": True,
                        "outDir": out_dir,
                    }
                )
                continue
            try:
                res = api.export_table(
                    out_dir=out_dir,
                    symbol=sym,
                    tf=tf,
                    start=start,
                    end=end,
                    past_bars=past_bars,
                    method=method,
                    depth=depth,
                    deviation=deviation,
                    backstep=backstep,
                    merge_pct=merge_pct,
                    bars_csv=bars_csv,
                    meta_in=meta_in,
                )
            except Exception as exc:  # last-resort guard: report, keep going
                results.append(
                    {
                        "symbol": sym,
                        "timeframe": tf,
                        "ok": False,
                        "error": {"code": "exception", "message": f"{type(exc).__name__}: {exc}"},
                    }
                )
                continue
            entry: Dict[str, Any] = {"symbol": sym, "timeframe": tf}
            entry.update(res)
            entry["key"] = key
            results.append(entry)

    finished = dt.datetime.now(dt.timezone.utc)
    ok_count = sum(1 for r in results if r.get("ok"))
    return {
        "engineVersion": ENGINE_VERSION,
        "startedAt": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "finishedAt": finished.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "durationSeconds": round((finished - started).total_seconds(), 3),
        "outDir": os.path.abspath(out_dir),
        "window": {
            "from": start,
            "to": end,
            "pastBars": past_bars,
        },
        "params": {
            "method": method,
            "depth": depth,
            "deviationPoints": deviation,
            "backstep": backstep,
            "mergePct": merge_pct,
        },
        "dryRun": dry_run,
        "totals": {
            "requested": len(results),
            "succeeded": ok_count,
            "failed": len(results) - ok_count,
        },
        "results": results,
    }


def write_manifest(path: str, manifest: Dict[str, Any]) -> str:
    """Write the manifest as UTF-8 / LF JSON. Returns the path written."""
    parent = os.path.dirname(os.path.abspath(path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=2, sort_keys=False)
        fh.write("\n")
    return path


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m engine.daily",
        description="Daily volatility-table batch updater (A3)",
    )
    p.add_argument(
        "--symbols",
        default=None,
        help=f"comma separated, e.g. EURUSD,GBPUSD (default {','.join(DEFAULT_SYMBOLS)})",
    )
    p.add_argument("--symbols-file", default=None, help="one symbol per line, # comments ok")
    p.add_argument(
        "--tf",
        default=",".join(DEFAULT_TFS),
        help=f"comma separated timeframes (default {','.join(DEFAULT_TFS)})",
    )
    p.add_argument("--out-dir", default="out/volatility", help="artefact output directory")
    p.add_argument("--from", dest="start", default=None, help="fixed window start (server time)")
    p.add_argument("--to", dest="end", default=None, help="fixed window end (server time)")
    p.add_argument(
        "--past-bars",
        type=int,
        default=DEFAULT_PAST_BARS,
        help=f"most recent N bars (default {DEFAULT_PAST_BARS} = the indicator's own "
        f"*Past X Bars* setting); ignored when --from/--to are given",
    )
    p.add_argument(
        "--bucket-method", choices=("count", "rank", "inc"), default="count",
        help="class derivation (default count = evidence-backed)",
    )
    p.add_argument("--merge-pct", type=float, default=35.0)
    p.add_argument("--depth", type=int, default=12)
    p.add_argument("--deviation", type=int, default=5)
    p.add_argument("--backstep", type=int, default=3)
    p.add_argument("--manifest", default=None, help=f"manifest path (default <out-dir>/{MANIFEST_NAME})")
    p.add_argument("--bars-csv", default=None, help="offline bars CSV instead of a live MT5 call")
    p.add_argument("--meta-in", default=None, help="sidecar for --bars-csv")
    p.add_argument("--dry-run", action="store_true", help="plan only; no MT5 call, no files")
    p.add_argument("--quiet", action="store_true")
    return p


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    symbols: List[str] = []
    if args.symbols_file:
        try:
            symbols.extend(_read_symbols_file(args.symbols_file))
        except OSError as exc:
            print(f"error: cannot read symbols file: {exc}", file=sys.stderr)
            return EXIT_ARGS
    symbols.extend(_split_csv(args.symbols))
    if not symbols:
        symbols = list(DEFAULT_SYMBOLS)
    # Stable order so a run is reproducible regardless of how the list was typed.
    symbols = sorted({s.upper() for s in symbols})

    tfs = sorted({t.upper() for t in _split_csv(args.tf)}) or list(DEFAULT_TFS)

    if (args.start is None) != (args.end is None):
        print("error: --from and --to must be given together", file=sys.stderr)
        return EXIT_ARGS
    if args.backstep >= args.depth:
        print("error: --backstep must be smaller than --depth", file=sys.stderr)
        return EXIT_ARGS

    past_bars: Optional[int] = None if args.start else args.past_bars
    if past_bars is not None and past_bars < 64:
        print("error: --past-bars below 64 cannot form a usable sample", file=sys.stderr)
        return EXIT_ARGS

    manifest = run_matrix(
        symbols=symbols,
        timeframes=tfs,
        out_dir=args.out_dir,
        start=args.start,
        end=args.end,
        past_bars=past_bars,
        method=args.bucket_method,
        merge_pct=args.merge_pct,
        depth=args.depth,
        deviation=args.deviation,
        backstep=args.backstep,
        dry_run=args.dry_run,
        bars_csv=args.bars_csv,
        meta_in=args.meta_in,
    )

    if not args.dry_run:
        path = args.manifest or os.path.join(args.out_dir, MANIFEST_NAME)
        write_manifest(path, manifest)
        if not args.quiet:
            print(f"manifest   : {path}")

    if not args.quiet:
        t = manifest["totals"]
        print(
            f"engine     : {ENGINE_VERSION}\n"
            f"matrix     : {len(symbols)} symbol(s) x {len(tfs)} tf = {t['requested']} run(s)\n"
            f"window     : "
            + (
                f"{args.start} .. {args.end}"
                if args.start
                else f"last {past_bars} bars"
            )
            + f"\nout-dir    : {manifest['outDir']}"
        )
        print()
        for r in manifest["results"]:
            if r.get("ok"):
                arts = r.get("artifacts") or {}
                names = ", ".join(sorted(arts)) or "(dry run)"
                print(f"  OK   {r['symbol']:8s} {r['timeframe']:4s}  {names}")
            else:
                err = r.get("error") or {}
                print(f"  FAIL {r['symbol']:8s} {r['timeframe']:4s}  "
                      f"{err.get('code')}: {err.get('message')}")
        print()
        print(f"result     : {t['succeeded']}/{t['requested']} succeeded"
              + (f", {t['failed']} failed" if t["failed"] else ""))

    return EXIT_OK if manifest["totals"]["failed"] == 0 else EXIT_FAILED


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
