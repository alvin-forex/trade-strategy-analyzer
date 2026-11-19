"""Data-quality gate for trade-history CSVs.

Why this exists
---------------
Every downstream number -- layer counts, win rate, net profit, fit ratios --
inherits whatever is wrong with the input. Two kinds of wrongness were found in
``downloads/`` and neither announces itself:

**Junk rows that look like trades.** ``Type=buy, Symbol=profit,
Comment='Summary trade result MM.YYYY'`` passes a naive ``Type in (buy, sell)``
filter. Across the 275 files these add 89 rows and, because they carry a whole
month's P&L, a material share of total net profit -- 10.9% in aggregate and
44.3% in one file. ``ingest`` already drops them; this module reports them so the
drop is visible rather than silent.

**Rows that are real but cannot support the analysis.** A trade with no open
time cannot be placed in a date segment. A trade with zero lots cannot be
tiered. These are kept by ``ingest`` (they are genuine trades) and quarantined
here, because dropping them at read time would hide them from the counts that
matter.

Severity is deliberately coarse -- ``error`` blocks an analysis, ``warn``
changes a number, ``info`` is context. Anything that would make a report
misleading has to reach ``error`` or ``warn``; ``info`` is never load-bearing.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence

from .ingest import Trade

#: A gap this long between consecutive trades inside one signal is normal
#: (weekends, holidays, EA pause). Longer than this and the file is either
#: two different test runs concatenated or has a hole worth looking at.
DEFAULT_GAP_DAYS = 45

#: Duplicate detection rounds lots to this many decimals before comparing the
#: whole row. Two trades can legitimately share a second, so the timestamp is
#: compared at minute resolution rather than exactly.
DUP_TIME_RESOLUTION = "minute"


@dataclass(frozen=True)
class Issue:
    """One thing wrong with one file, stated as what it breaks."""

    code: str  # stable identifier, safe for tests to assert on
    severity: str  # "error" | "warn" | "info"
    message: str


@dataclass
class QualityReport:
    """Everything the gate found, plus the numbers it needs to justify itself."""

    path: str = ""
    total_rows: int = 0
    trades: int = 0
    issues: List[Issue] = field(default_factory=list)

    #: counted separately from issues so the magnitude is always available
    fake_rows: int = 0
    fake_profit: float = 0.0
    real_profit: float = 0.0
    zero_lot_trades: int = 0
    no_time_trades: int = 0
    duplicate_trades: int = 0
    span: Optional[tuple] = None
    biggest_gap_days: float = 0.0

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == "warn"]

    @property
    def ok(self) -> bool:
        """True when nothing found would make a report misleading."""
        return not any(i.severity in ("error", "warn") for i in self.issues)

    @property
    def fake_share(self) -> float:
        """Share of gross profit contributed by the junk rows, in [0, 1].

        Uses the sum of positive net profit as the denominator so a file with
        large losses cannot make the share exceed 100%.
        """
        gross = self.real_profit + self.fake_profit
        return self.fake_profit / gross if gross > 0 else 0.0

    def add(self, code: str, severity: str, message: str) -> None:
        self.issues.append(Issue(code, severity, message))


def _dup_key(t: Trade) -> tuple:
    """Identity for duplicate detection.

    A trade is the same trade only if symbol, direction, lots, open time and
    open price all match. Comparing net profit too would let two genuinely
    identical fills that closed differently slip through, so it is excluded --
    erring toward flagging a pair that might be legitimate is the safer
    direction for a quality gate.
    """
    ts = t.open_time
    if ts is not None and DUP_TIME_RESOLUTION == "minute":
        ts = ts.replace(second=0, microsecond=0)
    return (t.symbol, t.direction, round(t.lots, 2), ts, round(t.open_price, 5))


def _gaps(times: Sequence[datetime]) -> List[float]:
    """Day gaps between consecutive timestamps, in ascending time order."""
    ordered = sorted(times)
    return [
        (b - a).total_seconds() / 86400.0 for a, b in zip(ordered, ordered[1:])
    ]


def check(
    trades: Iterable[Trade],
    path: str = "",
    total_rows: Optional[int] = None,
    fake_rows: int = 0,
    fake_profit: float = 0.0,
    gap_days: int = DEFAULT_GAP_DAYS,
    min_trades: int = 30,
) -> QualityReport:
    """Run every check on one file's trades.

    ``fake_rows``/``fake_profit`` come from the caller because ``ingest``
    discards those rows before returning trades -- the gate cannot see them
    itself but must report them.
    """
    trades = list(trades)
    rep = QualityReport(path=path, trades=len(trades))
    rep.total_rows = total_rows if total_rows is not None else len(trades)
    rep.fake_rows = fake_rows
    rep.fake_profit = fake_profit
    rep.real_profit = sum(t.net_profit for t in trades if t.net_profit > 0)

    if rep.fake_rows:
        rep.add(
            "FAKE_TRADES",
            "error",
            f"{rep.fake_rows} row(s) tagged Symbol='profit' / Comment='Summary trade "
            f"result' carry {rep.fake_profit:,.2f} of profit; they are monthly "
            f"roll-ups, not trades",
        )

    if not trades:
        rep.add("NO_TRADES", "error", "no usable trade rows")
        return rep

    rep.zero_lot_trades = sum(1 for t in trades if t.lots <= 0)
    if rep.zero_lot_trades:
        rep.add(
            "ZERO_LOTS",
            "warn",
            f"{rep.zero_lot_trades} trade(s) have Lots <= 0 and cannot be tiered",
        )

    rep.no_time_trades = sum(1 for t in trades if t.open_time is None)
    if rep.no_time_trades:
        rep.add(
            "NO_OPEN_TIME",
            "warn",
            f"{rep.no_time_trades} trade(s) have no parsable Open Time and cannot "
            f"be placed in a date segment",
        )

    seen: Counter = Counter()
    for t in trades:
        seen[_dup_key(t)] += 1
    rep.duplicate_trades = sum(c - 1 for c in seen.values() if c > 1)
    if rep.duplicate_trades:
        rep.add(
            "DUPLICATES",
            "warn",
            f"{rep.duplicate_trades} row(s) repeat an earlier trade exactly "
            f"(symbol, direction, lots, open time, open price)",
        )

    times = [t.open_time for t in trades if t.open_time is not None]
    if times:
        rep.span = (min(times), max(times))
        gaps = _gaps(times)
        rep.biggest_gap_days = max(gaps) if gaps else 0.0
        if rep.biggest_gap_days > gap_days:
            rep.add(
                "DATE_GAP",
                "info",
                f"largest gap between trades is {rep.biggest_gap_days:.0f} days "
                f"(threshold {gap_days}); could be an EA pause or two runs joined",
            )

    if len(trades) < min_trades:
        rep.add(
            "SMALL_SAMPLE",
            "warn",
            f"only {len(trades)} trades (threshold {min_trades}); ratios are unstable",
        )

    if rep.span is not None and rep.span[0] == rep.span[1]:
        rep.add("SINGLE_DAY", "info", "every trade opened on the same day")

    return rep


def check_file(
    path: str, gap_days: int = DEFAULT_GAP_DAYS, min_trades: int = 30
) -> QualityReport:
    """Read one CSV and gate it, keeping the junk-row counts from ingestion."""
    from .ingest import IngestReport, read_trades

    ing = IngestReport()
    trades = read_trades(path, ing)

    # ``ingest`` counts summary rows but not their money, so recover the amount
    # here by re-reading only the rows it rejected as summary. Without this the
    # reported share would always be zero.
    fake_profit = 0.0
    fake_rows = 0
    if ing.dropped_summary:
        import csv as _csv

        from .ingest import is_summary_row

        with open(path, encoding="utf-8-sig", newline="") as fh:
            for row in _csv.DictReader(fh):
                sym = (row.get("Symbol") or "").strip()
                cmt = (row.get("Comment") or "").strip()
                if (row.get("Type") or "").strip().lower() not in ("buy", "sell"):
                    continue
                if not is_summary_row(sym, cmt):
                    continue
                fake_rows += 1
                try:
                    fake_profit += float((row.get("Net Profit") or "0").strip() or 0)
                except ValueError:
                    pass

    return check(
        trades,
        path=path,
        total_rows=ing.total_rows,
        fake_rows=fake_rows,
        fake_profit=fake_profit,
        gap_days=gap_days,
        min_trades=min_trades,
    )


def summarise(reports: Sequence[QualityReport]) -> Dict[str, object]:
    """Aggregate for a batch header: how bad is the whole corpus."""
    return {
        "files": len(reports),
        "files_with_errors": sum(1 for r in reports if r.errors),
        "files_with_warnings": sum(1 for r in reports if r.warnings),
        "files_clean": sum(1 for r in reports if r.ok),
        "trades": sum(r.trades for r in reports),
        "fake_rows": sum(r.fake_rows for r in reports),
        "fake_profit": round(sum(r.fake_profit for r in reports), 2),
        "real_profit": round(sum(r.real_profit for r in reports), 2),
        "no_time_trades": sum(r.no_time_trades for r in reports),
        "zero_lot_trades": sum(r.zero_lot_trades for r in reports),
        "duplicate_trades": sum(r.duplicate_trades for r in reports),
    }


def gap_days_between(start: datetime, end: datetime) -> float:
    """Small helper kept public so callers do not re-derive the unit."""
    return (end - start) / timedelta(days=1)
