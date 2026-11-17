"""CLI: python -m engine.extract --symbol EURUSD --tf H1 --from ... --to ... --out waves.csv"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional, Sequence

from .bar import Bar, pip_size
from .buckets import compute_buckets
from .merge import build_waves, merge_pivots
from .sources import csv_source, mt5_source
from .version import ENGINE_VERSION, CALC_METHOD_WAVES
from .waves import build_meta, default_meta_path, write_meta, write_waves_csv
from .zigzag import zigzag

EXIT_OK = 0
EXIT_ARGS = 2
EXIT_MT5 = 3
EXIT_SYMBOL = 4
EXIT_DATA = 5
EXIT_PARITY = 6

PARITY_N = 49


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m engine.extract",
        description="Extract ZigZag+Merge swing waves to waves.csv",
    )
    p.add_argument("--symbol", required=False, help="e.g. EURUSD")
    p.add_argument("--tf", default="H1", help="M1/M5/M15/M30/H1/H4/D1/W1")
    p.add_argument("--from", dest="start", help="YYYY-MM-DDTHH:MM (server time)")
    p.add_argument("--to", dest="end", help="YYYY-MM-DDTHH:MM (server time)")
    p.add_argument("--out", help="output CSV path")
    p.add_argument("--depth", type=int, default=12)
    p.add_argument("--deviation", type=int, default=5, help="in points")
    p.add_argument("--backstep", type=int, default=3)
    p.add_argument("--merge-pct", type=float, default=35.0)
    p.add_argument(
        "--merge-mode",
        choices=("drop_next", "pre", "post"),
        default="drop_next",
        help="merge reading; drop_next reproduces the original panel (default)",
    )
    p.add_argument("--bar-mode", choices=("exclusive", "inclusive"), default="exclusive")
    p.add_argument("--meta-out", default=None)
    p.add_argument("--bars-csv", default=None, help="offline bars instead of MT5")
    p.add_argument("--meta-in", default=None, help="sidecar for --bars-csv")
    p.add_argument("--no-parity", action="store_true", help="skip the 49-wave check")
    p.add_argument("--quiet", action="store_true")
    p.add_argument("--doctor", action="store_true", help="print MT5 diagnostics and exit")
    return p


def _load(args) -> tuple[List[Bar], object]:
    if args.bars_csv:
        return csv_source.fetch_bars(
            args.bars_csv, args.start, args.end, meta_path=args.meta_in
        )
    mt5_source.connect()
    meta = mt5_source.symbol_meta(args.symbol)
    bars, meta = mt5_source.fetch_bars(args.symbol, args.tf, args.start, args.end, meta)
    return bars, meta


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.doctor:
        from .sources.mt5_source import probe

        for k, v in probe().items():
            print(f"{k}: {v}")
        return EXIT_OK

    if not args.bars_csv and not (args.symbol and args.start and args.end and args.out):
        print("error: --symbol/--from/--to/--out are required (or use --bars-csv)", file=sys.stderr)
        return EXIT_ARGS
    if args.bars_csv and not args.out:
        print("error: --out is required", file=sys.stderr)
        return EXIT_ARGS

    try:
        bars, sym = _load(args)
    except mt5_source.MT5Error as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_MT5
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_DATA

    if not bars:
        print("error: no bars in the requested window", file=sys.stderr)
        return EXIT_DATA
    if args.backstep >= args.depth:
        print("error: --backstep must be < --depth", file=sys.stderr)
        return EXIT_ARGS

    pip = sym.pip  # type: ignore[attr-defined]
    pivots = zigzag(bars, args.depth, args.deviation, args.backstep, sym.point)  # type: ignore[attr-defined]
    merged = merge_pivots(pivots, args.merge_pct, args.merge_mode)
    waves = build_waves(merged, pip, args.bar_mode)

    sha = write_waves_csv(args.out, waves)
    total_bars = sum(w.bars for w in waves)
    stats = compute_buckets(
        [w.amplitude_pips for w in waves], [w.bars for w in waves]
    )

    offset = 0.0
    if not args.bars_csv:
        try:
            offset = mt5_source.server_utc_offset_hours(args.symbol)
        except Exception:  # pragma: no cover - diagnostic only
            offset = 0.0

    meta = build_meta(
        broker=getattr(sym, "broker_company", "") or "",
        server=getattr(sym, "server", "") or "",
        symbol=args.symbol or getattr(sym, "symbol", "") or "",
        symbol_digits=sym.digits,  # type: ignore[attr-defined]
        tf=args.tf,
        window_from=bars[0].time_label,
        window_to=bars[-1].time_label,
        params={
            "depth": args.depth,
            "deviation_points": args.deviation,
            "backstep": args.backstep,
            "merge_pct": args.merge_pct,
            "merge_mode": args.merge_mode,
            "bar_mode": args.bar_mode,
            "pip_size": pip,
        },
        engine_version=ENGINE_VERSION,
        calc_method=CALC_METHOD_WAVES,
        server_utc_offset=offset,
        time_basis="server",
        bar_count=len(bars),
        wave_count=len(waves),
        first_pivot_idx=merged[0].idx if merged else -1,
        last_pivot_idx=merged[-1].idx if merged else -1,
        covered_bars=(merged[-1].idx - merged[0].idx) if len(merged) > 1 else 0,
        csv_sha256=sha,
        total_bars=total_bars,
        extra={
            "pivot_count": len(pivots),
            "merged_pivot_count": len(merged),
            "buckets": [
                {
                    "label": s.label,
                    "count": s.count,
                    "total_bars": s.total_bars,
                    "average_bars": s.average_bars,
                    "average_pips": s.average_pips,
                    "lower_pips": s.lower_pips,
                    "upper_pips": s.upper_pips,
                }
                for s in stats
            ],
        },
    )
    meta_path = args.meta_out or default_meta_path(args.out)
    write_meta(meta_path, meta)

    if not args.quiet:
        print(f"engine     : {ENGINE_VERSION}  ({CALC_METHOD_WAVES})")
        print(f"symbol     : {args.symbol or sym.symbol} {args.tf}  digits={sym.digits}  pip={pip:g}")  # type: ignore[attr-defined]
        print(f"window     : {bars[0].time_label} .. {bars[-1].time_label}  ({len(bars)} bars)")
        print(f"pivots     : raw={len(pivots)}  merged={len(merged)}")
        print(f"waves      : {len(waves)}   total bars={total_bars}")
        for s in stats:
            print(
                f"  {s.label:7s} n={s.count:3d}  bars={s.total_bars:5d}  "
                f"avgB={s.average_bars:6.1f}  pips={s.lower_pips:7.1f}-{s.upper_pips:7.1f}"
            )
        print(f"csv        : {args.out}  sha256={sha[:16]}...")
        print(f"meta       : {meta_path}")

    if not args.no_parity and len(waves) != PARITY_N:
        print(
            f"note: wave count {len(waves)} != parity target {PARITY_N} "
            f"(broker data differs; algorithm left unchanged)",
            file=sys.stderr,
        )
        return EXIT_PARITY
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
