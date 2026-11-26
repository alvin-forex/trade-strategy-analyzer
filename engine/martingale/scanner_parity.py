#!/usr/bin/env python3
"""#37 parity suite: original ExtraCCY05 panel truth vs the rebuilt engine.

OC dispatch 2026-11-26 14:08 (AC + ZCODE same-machine collaboration) asks ZCODE
to read the original-indicator truth on this machine and run parity under the
#37 machine gate (tolerance 1e-4). This module is the reusable, testable core:

* :func:`load_truth` reads the AC truth CSV (wide 9-currency panel or the long
  ``ccyN_name/ccyN_power`` reader layout) keyed by ``(timestamp, tf, currency)``.
* :func:`load_clone` reads the rebuilt panel produced by the orchestrator/core
  in the same keyed shape.
* :func:`compare` emits a deterministic :class:`ParityReport` (one row per
  ts/tf/ccy with orig/clone/diff/pass, plus max-diff top 10). Missing truth is
  a hard error -- the gate never silently passes on absent data (OC 1525 rule:
  no fake success).

No MT4/MT5 dependency: everything is plain CSV, so it runs in CI. The caller
supplies both files; this module does not guess paths or manufacture values.
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

CURRENCIES_9 = ("EUR", "USD", "AUD", "GBP", "JPY", "CHF", "CAD", "NZD", "XAU")
DEFAULT_TOLERANCE = 1e-4
_ALIAS = {"GOLD": "XAU"}

Key = Tuple[str, str, str]  # (timestamp, timeframe, currency)


class ParityPendingError(RuntimeError):
    """Truth or clone data missing / below the minimum viable sample."""


def _norm_ccy(name: str) -> str:
    name = name.strip().upper()
    return _ALIAS.get(name, name)


def _norm_tf(tf: str) -> str:
    tf = tf.strip().upper()
    return {"30M": "M30", "1H": "H1", "4H": "H4", "1D": "D1"}.get(tf, tf)


def load_truth(path: str, min_rows: int = 1) -> Dict[Key, float]:
    """Read original-indicator truth into ``{(ts, tf, ccy): value}``.

    Two layouts are accepted:
      * wide: ``timestamp[,timeframe],EUR,USD,...,XAU``
      * long: ``timestamp,timeframe,ccy1_name,ccy1_power,...,ccy9_name,ccy9_power``

    XAU and GOLD are the same currency. Values are 0..9 panel readings.
    """
    if not os.path.exists(path):
        raise ParityPendingError(f"原版真值檔唔存在：{path}")
    out: Dict[Key, float] = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = [f.strip().lower() if f else "" for f in (reader.fieldnames or [])]
        long_fmt = any(f.startswith("ccy") and f.endswith("_name") for f in fields)
        for row in reader:
            ts = (row.get("timestamp") or row.get("time") or row.get("date") or "").strip()
            if not ts:
                continue
            tf = _norm_tf(row.get("timeframe") or row.get("tf") or "")
            if long_fmt:
                for i in range(1, 10):
                    ccy = _norm_ccy(row.get(f"ccy{i}_name") or "")
                    raw = (row.get(f"ccy{i}_power") or "").strip()
                    if ccy in CURRENCIES_9 and raw:
                        out[(ts, tf, ccy)] = float(raw)
            else:
                for name, raw in row.items():
                    if name is None:
                        continue
                    ccy = _norm_ccy(name)
                    if ccy in CURRENCIES_9 and str(raw).strip():
                        out[(ts, tf, ccy)] = float(raw)
    if len(out) < min_rows:
        raise ParityPendingError(
            f"原版真值只得 {len(out)} 格（< {min_rows}），唔夠對拍")
    return out


def load_clone(path: str) -> Dict[Key, float]:
    """Read rebuilt panel CSV into ``{(ts, tf, ccy): value}``.

    Expected header: ``timestamp/time, timeframe/tf, <currency columns>``.
    Values are 0..9 panel readings (caller must have applied the display-scale
    mapping first; this module never rescales silently).
    """
    if not os.path.exists(path):
        raise ParityPendingError(f"重製值檔唔存在：{path}")
    out: Dict[Key, float] = {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            ts = (row.get("timestamp") or row.get("time") or row.get("date") or "").strip()
            if not ts:
                continue
            tf = _norm_tf(row.get("timeframe") or row.get("tf") or "")
            for name, raw in row.items():
                if name is None:
                    continue
                ccy = _norm_ccy(name)
                if ccy in CURRENCIES_9 and str(raw).strip():
                    out[(ts, tf, ccy)] = float(raw)
    if not out:
        raise ParityPendingError(f"重製值檔無有效儲存格：{path}")
    return out


@dataclass(frozen=True)
class Cell:
    ts: str
    tf: str
    ccy: str
    orig: Optional[float]
    clone: Optional[float]
    diff: Optional[float]

    @property
    def passed(self) -> bool:
        return self.diff is not None and self.diff <= DEFAULT_TOLERANCE


@dataclass
class ParityReport:
    tolerance: float = DEFAULT_TOLERANCE
    cells: List[Cell] = field(default_factory=list)
    truth_only: List[Key] = field(default_factory=list)
    clone_only: List[Key] = field(default_factory=list)

    @property
    def compared(self) -> List[Cell]:
        return [c for c in self.cells if c.diff is not None]

    @property
    def passed(self) -> List[Cell]:
        return [c for c in self.cells if c.passed]

    @property
    def failed(self) -> List[Cell]:
        return [c for c in self.cells if c.diff is not None and not c.passed]

    @property
    def max_diff(self) -> float:
        return max((c.diff for c in self.compared), default=0.0)

    @property
    def pass_rate(self) -> float:
        return len(self.passed) / len(self.compared) if self.compared else 0.0

    @property
    def all_pass(self) -> bool:
        return bool(self.compared) and not self.failed and not self.truth_only and not self.clone_only

    def top10(self) -> List[Cell]:
        """Largest discrepancies first (top of the file for the gate report)."""
        return sorted(self.compared, key=lambda c: c.diff, reverse=True)[:10]


def compare(truth: Dict[Key, float], clone: Dict[Key, float],
            tolerance: float = DEFAULT_TOLERANCE) -> ParityReport:
    """Key-by-key compare; a missing side is recorded, never treated as a pass."""
    if not truth:
        raise ParityPendingError("原版真值為空")
    if not clone:
        raise ParityPendingError("重製值為空")
    keys = sorted(set(truth) | set(clone))
    rep = ParityReport(tolerance=tolerance)
    for ts, tf, ccy in keys:
        o, c = truth.get((ts, tf, ccy)), clone.get((ts, tf, ccy))
        if o is None:
            rep.clone_only.append((ts, tf, ccy))
            rep.cells.append(Cell(ts, tf, ccy, None, c, None))
        elif c is None:
            rep.truth_only.append((ts, tf, ccy))
            rep.cells.append(Cell(ts, tf, ccy, o, None, None))
        else:
            rep.cells.append(Cell(ts, tf, ccy, o, c, abs(o - c)))
    return rep


def write_report(rep: ParityReport, out_path: str) -> str:
    """Write ``parity_report.csv``: every cell, then a top-10 gap section."""
    parent = os.path.dirname(os.path.abspath(out_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["ts", "tf", "ccy", "orig", "clone", "diff", "pass/fail"])
        for c in rep.cells:
            w.writerow([c.ts, c.tf, c.ccy,
                        "" if c.orig is None else f"{c.orig:.6f}",
                        "" if c.clone is None else f"{c.clone:.6f}",
                        "" if c.diff is None else f"{c.diff:.6f}",
                        "PASS" if c.passed else (
                            "MISSING_TRUTH" if c.orig is None else
                            "MISSING_CLONE" if c.clone is None else "FAIL")])
        w.writerow([])
        w.writerow(["TOP10_MAX_DIFF"])
        w.writerow(["ts", "tf", "ccy", "orig", "clone", "diff"])
        for c in rep.top10():
            w.writerow([c.ts, c.tf, c.ccy, f"{c.orig:.6f}",
                        f"{c.clone:.6f}", f"{c.diff:.6f}"])
    return out_path


def summary(rep: ParityReport) -> dict:
    return {
        "tolerance": rep.tolerance,
        "compared": len(rep.compared),
        "passed": len(rep.passed),
        "failed": len(rep.failed),
        "truth_only": len(rep.truth_only),
        "clone_only": len(rep.clone_only),
        "max_diff": round(rep.max_diff, 6),
        "pass_rate": round(rep.pass_rate, 6),
        "all_pass": rep.all_pass,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    import argparse
    import json

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--truth", required=True, help="原版 ExtraCCY05 panel 真值 CSV")
    ap.add_argument("--clone", required=True, help="重製版 panel 值 CSV")
    ap.add_argument("--out", required=True, help="parity_report.csv 輸出路徑")
    ap.add_argument("--tolerance", type=float, default=DEFAULT_TOLERANCE)
    args = ap.parse_args(argv)

    rep = compare(load_truth(args.truth), load_clone(args.clone), args.tolerance)
    path = write_report(rep, args.out)
    print(json.dumps(summary(rep), indent=2, sort_keys=True))
    print(path)
    return 0 if rep.all_pass else 1


if __name__ == "__main__":
    raise SystemExit(main())
