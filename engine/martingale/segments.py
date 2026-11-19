"""Date-range segmentation for one signal.

The owner's requirement, in his words: the interface must let him **separate
information by date range** -- because a strategy that worked for eight months
and broke after a SET change is two different strategies, and averaging them
produces a number that describes neither.

So this module does one thing: cut a trade list into consecutive windows and
report the same statistics for each, plus whether the windows actually differ.
It deliberately does not decide which cut is "right"; that is a UI control.

Two design points that are not obvious:

**Boundaries are half-open ``[start, end)``.** A trade at exactly midnight
belongs to the window that starts there, not the one that ends there. Without
this a trade can be counted twice when windows are adjacent, and the totals
will not reconcile with the unsegmented figure.

**A segment can be too small to say anything.** Reporting "win rate 100%" off
four trades is worse than reporting nothing, so ``min_trades`` marks a segment
``thin`` and the caller is expected to show it as such rather than hide it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .ingest import Trade
from .layers import LayerModel, detect_excel


@dataclass(frozen=True)
class Segment:
    """One date window and what happened inside it."""

    label: str
    start: Optional[datetime]  # inclusive
    end: Optional[datetime]  # exclusive
    trades: List[Trade] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.trades)

    @property
    def wins(self) -> int:
        return sum(1 for t in self.trades if t.is_win)

    @property
    def win_rate(self) -> float:
        """Fraction of winners in ``[0, 1]``; 0.0 for an empty segment."""
        return self.wins / self.count if self.count else 0.0

    @property
    def net_profit(self) -> float:
        return sum(t.net_profit for t in self.trades)

    @property
    def net_pips(self) -> float:
        return sum(t.net_pips for t in self.trades)

    @property
    def worst_mae_pips(self) -> float:
        return max((t.max_loss_pips for t in self.trades), default=0.0)

    @property
    def symbols(self) -> List[str]:
        return sorted({t.symbol for t in self.trades})

    def layers(self) -> LayerModel:
        """Excel-method tiering for this window alone.

        Per-window rather than whole-file: if the lot ladder changed, the base
        lot differs by design and pooling would rank every segment against a
        base lot that only applied to part of the history.
        """
        return detect_excel(self.trades)


@dataclass
class SegmentReport:
    """All segments for one signal, plus the comparison between them."""

    segments: List[Segment] = field(default_factory=list)
    min_trades: int = 30

    @property
    def total_trades(self) -> int:
        return sum(s.count for s in self.segments)

    @property
    def total_profit(self) -> float:
        return sum(s.net_profit for s in self.segments)

    def thin(self) -> List[Segment]:
        return [s for s in self.segments if s.count < self.min_trades]

    def best(self) -> Optional[Segment]:
        """Highest net profit among segments large enough to trust."""
        solid = [s for s in self.segments if s.count >= self.min_trades]
        return max(solid, key=lambda s: s.net_profit) if solid else None

    def worst(self) -> Optional[Segment]:
        solid = [s for s in self.segments if s.count >= self.min_trades]
        return min(solid, key=lambda s: s.net_profit) if solid else None

    def drift(self) -> Optional[Dict[str, float]]:
        """How far the last solid segment moved from the first.

        This is the number that answers "did something change?" -- a swing in
        win rate or profit per trade between the ends of the history. Returns
        ``None`` when there are fewer than two solid segments, because one
        segment has nothing to drift from.
        """
        solid = [s for s in self.segments if s.count >= self.min_trades]
        if len(solid) < 2:
            return None
        a, b = solid[0], solid[-1]
        return {
            "from": a.label,
            "to": b.label,
            "win_rate_delta": b.win_rate - a.win_rate,
            "profit_per_trade_delta": (b.net_profit / b.count) - (a.net_profit / a.count),
            "trades_delta": b.count - a.count,
        }


def _month_start(d: date) -> date:
    return d.replace(day=1)


def _next_month(d: date) -> date:
    return date(d.year + (d.month == 12), (d.month % 12) + 1, 1)


def _quarter_start(d: date) -> date:
    m = ((d.month - 1) // 3) * 3 + 1
    return date(d.year, m, 1)


def _next_quarter(d: date) -> date:
    return _next_month(_next_month(_next_month(_month_start(d))))


def boundaries(
    trades: Sequence[Trade], mode: str = "month"
) -> List[Tuple[str, datetime, datetime]]:
    """Cut points covering the trades' span, as ``(label, start, end)``.

    ``month`` and ``quarter`` walk calendar boundaries rather than fixed
    30/90-day blocks, so a segment always means "September", not "days 30-59".
    ``none`` returns one window spanning everything, which is how a caller
    disables segmentation without special-casing.
    """
    times = [t.open_time for t in trades if t.open_time is not None]
    if not times:
        return []
    lo = min(times).date()
    hi = max(times).date()

    if mode == "none":
        return [("all", datetime.combine(lo, datetime.min.time()),
                 datetime.combine(hi + timedelta(days=1), datetime.min.time()))]

    if mode == "month":
        out: List[Tuple[str, datetime, datetime]] = []
        cur = _month_start(lo)
        while cur <= hi:
            nxt = _next_month(cur)
            out.append((f"{cur.year}-{cur.month:02d}",
                        datetime.combine(cur, datetime.min.time()),
                        datetime.combine(nxt, datetime.min.time())))
            cur = nxt
        return out

    if mode == "quarter":
        out = []
        cur = _quarter_start(lo)
        while cur <= hi:
            nxt = _next_quarter(cur)
            out.append((f"{cur.year}-Q{(cur.month - 1) // 3 + 1}",
                        datetime.combine(cur, datetime.min.time()),
                        datetime.combine(nxt, datetime.min.time())))
            cur = nxt
        return out

    raise ValueError(f"unknown segment mode {mode!r} (use 'month', 'quarter', 'none')")


def segment(
    trades: Iterable[Trade],
    mode: str = "month",
    min_trades: int = 30,
    explicit: Optional[Sequence[Tuple[str, datetime, datetime]]] = None,
) -> SegmentReport:
    """Split ``trades`` and return per-window statistics.

    ``explicit`` overrides ``mode`` when the caller wants hand-picked ranges;
    the ``(label, start, end)`` triples are used as given, still half-open.
    Trades with no open time are excluded because they cannot be placed --
    :mod:`quality` is where that count is reported, so it is not lost, only
    not attributed to a window it cannot belong to.
    """
    pool = [t for t in trades if t.open_time is not None]
    cuts = list(explicit) if explicit is not None else boundaries(pool, mode)

    report = SegmentReport(min_trades=min_trades)
    for label, start, end in cuts:
        bucket = [t for t in pool if start <= t.open_time < end]  # type: ignore[operator]
        report.segments.append(Segment(label, start, end, bucket))
    return report


def compare(a: Segment, b: Segment) -> Dict[str, object]:
    """Side-by-side of two windows, for the "what changed" table."""
    return {
        "a": a.label,
        "b": b.label,
        "trades": {"a": a.count, "b": b.count},
        "win_rate": {"a": round(a.win_rate, 4), "b": round(b.win_rate, 4)},
        "net_profit": {"a": round(a.net_profit, 2), "b": round(b.net_profit, 2)},
        "profit_per_trade": {
            "a": round(a.net_profit / a.count, 2) if a.count else 0.0,
            "b": round(b.net_profit / b.count, 2) if b.count else 0.0,
        },
        "max_layer": {"a": a.layers().max_layer, "b": b.layers().max_layer},
    }
