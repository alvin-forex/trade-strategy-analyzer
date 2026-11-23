"""Single-signal scan: one CSV in, one JSON record out.

This is the unit the batch runner loops over, and it is also the shape the HTML
report consumes. Keeping it a pure function of ``(path, options) -> dict`` is
what makes the batch resumable and the tests cheap: nothing here touches the
clock, the network, or global state.

The record is deliberately wide rather than tidy. A caller filtering by date
range needs the per-segment rows; a caller checking "is this file trustworthy"
needs the quality block; a caller comparing strategies needs the layer model.
Emitting them in one object means the batch never has to re-read a CSV to
answer a follow-up question.
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from .ingest import IngestReport, Trade, filter_by_date, read_trades
from .layers import compare_methods
from .quality import QualityReport, check_file
from .scanner import ScanResult, scan_symbol, split_cycles
from .segments import SegmentReport, segment

DEFAULT_SEGMENT_MODE = "month"
DEFAULT_MIN_TRADES = 30
DEFAULT_GAP_HOURS = 24.0


def _iso(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat(sep=" ") if dt else None


@dataclass
class SignalRecord:
    """Everything one CSV yields, in one serialisable object."""

    path: str
    signal_id: str = ""
    ok: bool = True
    error: str = ""

    trades: int = 0
    total_rows: int = 0
    first_trade: Optional[str] = None
    last_trade: Optional[str] = None
    symbols: List[str] = field(default_factory=list)

    net_profit: float = 0.0
    net_pips: float = 0.0
    win_rate: float = 0.0

    cycles: int = 0
    deepest_layers: int = 0
    gap_hours: float = DEFAULT_GAP_HOURS

    layers_excel: Dict[str, Any] = field(default_factory=dict)
    layers_linear: Dict[str, Any] = field(default_factory=dict)
    methods_disagree: bool = False

    segments: List[Dict[str, Any]] = field(default_factory=list)
    segment_mode: str = DEFAULT_SEGMENT_MODE
    drift: Optional[Dict[str, Any]] = None

    quality: Dict[str, Any] = field(default_factory=dict)
    quality_ok: bool = True

    def as_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


def _signal_id(path: str) -> str:
    """The number in the filename, which is the signal id in this corpus."""
    stem = os.path.splitext(os.path.basename(path))[0]
    head = stem.split("-")[0]
    return head if head.isdigit() else stem


def scan_csv(
    path: str,
    segment_mode: str = DEFAULT_SEGMENT_MODE,
    min_trades: int = DEFAULT_MIN_TRADES,
    gap_hours: float = DEFAULT_GAP_HOURS,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None,
    quality_gate: bool = True,
) -> SignalRecord:
    """Scan one trade-history CSV into a :class:`SignalRecord`.

    A file that cannot be read is not an exception here: the batch must survive
    one bad file out of 275, so the failure is recorded in ``error`` and the
    record still carries its path. Callers check ``ok``.
    """
    rec = SignalRecord(path=path, signal_id=_signal_id(path), gap_hours=gap_hours)
    ing = IngestReport()

    try:
        trades = read_trades(path, ing)
    except Exception as exc:  # noqa: BLE001 - one bad file must not stop a batch
        rec.ok = False
        rec.error = f"{type(exc).__name__}: {exc}"
        return rec

    rec.total_rows = ing.total_rows
    trades = filter_by_date(trades, start=start, end=end)
    rec.trades = len(trades)

    if quality_gate:
        q: QualityReport = check_file(path, min_trades=min_trades)
        rec.quality = {
            "ok": q.ok,
            "issues": [asdict(i) for i in q.issues],
            "fake_rows": q.fake_rows,
            "fake_profit": round(q.fake_profit, 2),
            "fake_share": round(q.fake_share, 4),
            "zero_lot_trades": q.zero_lot_trades,
            "no_time_trades": q.no_time_trades,
            "duplicate_trades": q.duplicate_trades,
            "biggest_gap_days": round(q.biggest_gap_days, 1),
        }
        rec.quality_ok = q.ok

    if not trades:
        rec.ok = False
        rec.error = rec.error or "no trades"
        return rec

    times = [t.open_time for t in trades if t.open_time]
    rec.first_trade = _iso(min(times)) if times else None
    rec.last_trade = _iso(max(times)) if times else None
    rec.symbols = sorted({t.symbol for t in trades})

    rec.net_profit = round(sum(t.net_profit for t in trades), 2)
    rec.net_pips = round(sum(t.net_pips for t in trades), 2)
    rec.win_rate = round(sum(1 for t in trades if t.is_win) / len(trades), 4)

    cycles = split_cycles(trades, gap_hours)
    rec.cycles = len(cycles)
    rec.deepest_layers = max((c.max_layer for c in cycles), default=0)

    both = compare_methods(trades)
    rec.layers_excel = _model_dict(both["excel"])
    rec.layers_linear = _model_dict(both["linear"])
    rec.methods_disagree = both["excel"].max_layer != both["linear"].max_layer

    seg: SegmentReport = segment(trades, mode=segment_mode, min_trades=min_trades)
    rec.segment_mode = segment_mode
    rec.segments = [
        {
            "label": s.label,
            "trades": s.count,
            "win_rate": round(s.win_rate, 4),
            "net_profit": round(s.net_profit, 2),
            "net_pips": round(s.net_pips, 2),
            "worst_mae_pips": round(s.worst_mae_pips, 1),
            "symbols": len(s.symbols),
            "max_layer": s.layers().max_layer,
            "thin": s.count < min_trades,
        }
        for s in seg.segments
    ]
    rec.drift = seg.drift()

    return rec


def _model_dict(model) -> Dict[str, Any]:
    """Flatten a LayerModel, keeping the counts keyed by layer as strings.

    JSON object keys must be strings, so ``{1: 117}`` becomes ``{"1": 117}``
    here rather than at every consumer.
    """
    return {
        "method": model.method,
        "base": model.base,
        "step": model.step,
        "span": model.span,
        "max_layer": model.max_layer,
        "classified": model.classified,
        "unclassified": model.unclassified,
        "classification_rate": round(model.classification_rate, 4),
        "counts": {str(k): v for k, v in sorted(model.counts.items())},
    }


def scan_symbols(
    trades: List[Trade], gap_hours: float = DEFAULT_GAP_HOURS
) -> List[ScanResult]:
    """Per-symbol cycle breakdown, for callers that want more than the max."""
    by_symbol: Dict[str, List[Trade]] = {}
    for t in trades:
        by_symbol.setdefault(t.symbol, []).append(t)
    out: List[ScanResult] = []
    for sym, group in sorted(by_symbol.items()):
        out.extend(scan_symbol(group, sym, gap_hours=gap_hours))
    return out


def main(argv: Optional[Sequence[str]] = None) -> int:
    """``python -m engine.martingale.scan --csv <file>``

    Prints one JSON object. Exit 1 when the file could not be scanned, so a
    shell loop can detect it without parsing the output.
    """
    import argparse
    import json

    ap = argparse.ArgumentParser(prog="engine.martingale.scan", description=__doc__)
    ap.add_argument("--csv", required=True, help="one trade-history CSV")
    ap.add_argument(
        "--segment",
        default=DEFAULT_SEGMENT_MODE,
        choices=["month", "quarter", "none"],
        help="date segmentation mode",
    )
    ap.add_argument("--min-trades", type=int, default=DEFAULT_MIN_TRADES)
    ap.add_argument("--gap-hours", type=float, default=DEFAULT_GAP_HOURS)
    ap.add_argument("--no-quality", action="store_true", help="skip the quality gate")
    ap.add_argument("--indent", type=int, default=None)
    args = ap.parse_args(argv)

    rec = scan_csv(
        args.csv,
        segment_mode=args.segment,
        min_trades=args.min_trades,
        gap_hours=args.gap_hours,
        quality_gate=not args.no_quality,
    )
    print(json.dumps(rec.as_dict(), ensure_ascii=False, indent=args.indent, sort_keys=False))
    return 0 if rec.ok else 1


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess
    raise SystemExit(main())
