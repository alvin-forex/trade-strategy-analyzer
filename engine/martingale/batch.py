"""Batch runner over a directory of trade-history CSVs.

The contract the dispatch sets is that 275 files must finish with **zero
crashes** and at most five failures recorded. That shapes the design:

**Per-file isolation.** Each file is scanned inside its own try/except and its
result or failure is written before the next file starts. One malformed CSV
therefore costs one row, not the run.

**Failures are a product, not noise.** ``failed.txt`` lists the files that could
not be read and why. A batch that silently skipped them would report a clean
summary over an unknown subset.

**Output is resumable.** ``summary.csv`` is rewritten after every file, so
killing the run mid-way still leaves a valid partial result rather than nothing.

Two runs over the same inputs must produce byte-identical output; anything that
would break that (dict ordering, timestamps, float formatting) is pinned.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Sequence

from .scan import DEFAULT_MIN_TRADES, DEFAULT_SEGMENT_MODE, SignalRecord, scan_csv

SUMMARY_FIELDS = [
    "signal_id",
    "file",
    "ok",
    "error",
    "trades",
    "total_rows",
    "first_trade",
    "last_trade",
    "symbols",
    "net_profit",
    "net_pips",
    "win_rate",
    "cycles",
    "deepest_layers",
    "excel_base",
    "excel_step",
    "excel_max_layer",
    "excel_classification",
    "linear_max_layer",
    "methods_disagree",
    "quality_ok",
    "fake_rows",
    "fake_profit",
    "no_time_trades",
    "zero_lot_trades",
    "duplicate_trades",
    "segments",
]


@dataclass
class BatchResult:
    records: List[SignalRecord]
    failed: List[Dict[str, str]]

    @property
    def ok_count(self) -> int:
        return sum(1 for r in self.records if r.ok)

    @property
    def failed_count(self) -> int:
        return len(self.failed)

    @property
    def trades(self) -> int:
        return sum(r.trades for r in self.records)

    @property
    def fake_rows(self) -> int:
        return sum((r.quality or {}).get("fake_rows", 0) for r in self.records)

    @property
    def fake_profit(self) -> float:
        return round(sum((r.quality or {}).get("fake_profit", 0.0) for r in self.records), 2)

    def summary_line(self) -> str:
        return (
            f"files={len(self.records)} ok={self.ok_count} failed={self.failed_count} "
            f"trades={self.trades:,} fake_rows={self.fake_rows} "
            f"fake_profit={self.fake_profit:,.2f}"
        )


def find_csvs(directory: str, recursive: bool = False) -> List[str]:
    """CSV paths in ``directory``, sorted for reproducible runs.

    ``recursive`` includes subdirectories. The sort is by full path so the same
    tree always yields the same order regardless of filesystem enumeration.
    """
    out: List[str] = []
    if recursive:
        for root, _dirs, files in os.walk(directory):
            for name in files:
                if name.lower().endswith(".csv"):
                    out.append(os.path.join(root, name))
    else:
        for name in os.listdir(directory):
            full = os.path.join(directory, name)
            if os.path.isfile(full) and name.lower().endswith(".csv"):
                out.append(full)
    return sorted(out)


def _row(rec: SignalRecord) -> Dict[str, object]:
    q = rec.quality or {}
    ex = rec.layers_excel or {}
    li = rec.layers_linear or {}
    return {
        "signal_id": rec.signal_id,
        "file": os.path.basename(rec.path),
        "ok": "1" if rec.ok else "0",
        "error": rec.error,
        "trades": rec.trades,
        "total_rows": rec.total_rows,
        "first_trade": rec.first_trade or "",
        "last_trade": rec.last_trade or "",
        "symbols": len(rec.symbols),
        "net_profit": f"{rec.net_profit:.2f}",
        "net_pips": f"{rec.net_pips:.2f}",
        "win_rate": f"{rec.win_rate:.4f}",
        "cycles": rec.cycles,
        "deepest_layers": rec.deepest_layers,
        "excel_base": ex.get("base", ""),
        "excel_step": "" if ex.get("step") is None else ex.get("step"),
        "excel_max_layer": ex.get("max_layer", 0),
        "excel_classification": ex.get("classification_rate", 0),
        "linear_max_layer": li.get("max_layer", 0),
        "methods_disagree": "1" if rec.methods_disagree else "0",
        "quality_ok": "1" if rec.quality_ok else "0",
        "fake_rows": q.get("fake_rows", 0),
        "fake_profit": f"{q.get('fake_profit', 0.0):.2f}",
        "no_time_trades": q.get("no_time_trades", 0),
        "zero_lot_trades": q.get("zero_lot_trades", 0),
        "duplicate_trades": q.get("duplicate_trades", 0),
        "segments": len(rec.segments),
    }


def write_summary(records: Sequence[SignalRecord], path: str) -> str:
    """Write ``summary.csv`` with LF endings and a fixed column order."""
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=SUMMARY_FIELDS, lineterminator="\n")
        writer.writeheader()
        for rec in records:
            writer.writerow(_row(rec))
    return path


def write_failed(failed: Sequence[Dict[str, str]], path: str) -> str:
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write("file\treason\n")
        for f in failed:
            fh.write(f"{f['file']}\t{f['reason']}\n")
    return path


def run(
    directory: str,
    out_dir: Optional[str] = None,
    recursive: bool = False,
    segment_mode: str = DEFAULT_SEGMENT_MODE,
    min_trades: int = DEFAULT_MIN_TRADES,
    limit: Optional[int] = None,
    progress: bool = False,
) -> BatchResult:
    """Scan every CSV under ``directory``.

    ``out_dir`` defaults to ``directory``. Two files are written there:
    ``summary.csv`` (one row per input) and ``failed.txt`` (only failures).
    """
    paths = find_csvs(directory, recursive=recursive)
    if limit is not None:
        paths = paths[:limit]

    records: List[SignalRecord] = []
    failed: List[Dict[str, str]] = []
    for i, path in enumerate(paths, 1):
        try:
            rec = scan_csv(path, segment_mode=segment_mode, min_trades=min_trades)
        except Exception as exc:  # noqa: BLE001 - isolation is the point
            failed.append(
                {"file": os.path.basename(path), "reason": f"{type(exc).__name__}: {exc}"}
            )
            continue
        records.append(rec)
        if not rec.ok:
            failed.append(
                {"file": os.path.basename(path), "reason": rec.error or "not ok"}
            )
        if progress and (i % 25 == 0 or i == len(paths)):
            print(f"  {i}/{len(paths)}", flush=True)

    dest = out_dir or directory
    os.makedirs(dest, exist_ok=True)
    write_summary(records, os.path.join(dest, "summary.csv"))
    write_failed(failed, os.path.join(dest, "failed.txt"))
    return BatchResult(records=records, failed=failed)


def load_summary(path: str) -> List[Dict[str, str]]:
    """Read back ``summary.csv`` as plain dicts, for the report renderer."""
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main(argv: Optional[Sequence[str]] = None) -> int:
    """``python -m engine.martingale.batch --dir downloads/``

    Exit code is 0 when every file scanned and failures stay within
    ``--max-failed`` (default 5, the dispatch's ceiling), else 1. A non-zero
    exit is the only signal CI can act on, so the threshold is explicit.
    """
    import argparse

    ap = argparse.ArgumentParser(prog="engine.martingale.batch", description=__doc__)
    ap.add_argument("--dir", required=True, help="directory of trade-history CSVs")
    ap.add_argument("--out", default=None, help="output directory (default: same as --dir)")
    ap.add_argument("--recursive", action="store_true", help="include subdirectories")
    ap.add_argument(
        "--segment",
        default=DEFAULT_SEGMENT_MODE,
        choices=["month", "quarter", "none"],
        help="date segmentation for the per-segment rows",
    )
    ap.add_argument("--min-trades", type=int, default=DEFAULT_MIN_TRADES)
    ap.add_argument("--limit", type=int, default=None, help="stop after N files (debugging)")
    ap.add_argument("--max-failed", type=int, default=5)
    ap.add_argument("--progress", action="store_true")
    args = ap.parse_args(argv)

    result = run(
        args.dir,
        out_dir=args.out,
        recursive=args.recursive,
        segment_mode=args.segment,
        min_trades=args.min_trades,
        limit=args.limit,
        progress=args.progress,
    )
    print(result.summary_line())
    dest = args.out or args.dir
    print(f"summary: {os.path.join(dest, 'summary.csv')}")
    print(f"failed:  {os.path.join(dest, 'failed.txt')}")

    if result.failed_count > args.max_failed:
        print(
            f"FAIL: {result.failed_count} failed files exceeds --max-failed "
            f"{args.max_failed}",
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess
    raise SystemExit(main())
