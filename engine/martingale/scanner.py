"""Martingale structure per position cycle.

The question this answers is not "how did the trades do" (that is the V3
autopsy) but "what shape was the grid": how many layers fired, what multiple
each step multiplied by, how far price had to travel between fills, and how far
it must retrace for the basket to break even.

A *cycle* is a run of trades on one symbol and direction that belongs to one
basket. Without EA internals the only observable boundary is time: consecutive
same-symbol same-direction trades more than ``gap_hours`` apart start a new
cycle. That threshold is a parameter, not a fact, so the caller sets it and the
chosen value is recorded in the result.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from .ingest import Trade

DEFAULT_GAP_HOURS = 24.0


@dataclass
class Cycle:
    """One basket: same symbol, same direction, one continuous run."""

    symbol: str
    direction: str
    trades: List[Trade]

    @property
    def start(self) -> Optional[datetime]:
        times = [t.open_time for t in self.trades if t.open_time]
        return min(times) if times else None

    @property
    def end(self) -> Optional[datetime]:
        times = [t.close_time for t in self.trades if t.close_time]
        return max(times) if times else None

    @property
    def lots(self) -> List[float]:
        return [t.lots for t in self.trades]

    @property
    def max_layer(self) -> int:
        """How many rungs were visible, i.e. the count of distinct lots."""
        return len(set(round(x, 2) for x in self.lots))

    @property
    def total_lots(self) -> float:
        return sum(self.lots)

    @property
    def total_profit(self) -> float:
        return sum(t.net_profit for t in self.trades)

    @property
    def worst_mae_pips(self) -> float:
        return max((t.max_loss_pips for t in self.trades), default=0.0)

    @property
    def best_mfe_pips(self) -> float:
        return max((t.max_pips for t in self.trades), default=0.0)


@dataclass
class StepStats:
    """Multiplier and distance between the first and the last rung."""

    first_lot: float
    last_lot: float
    distinct_lots: int
    multiplier: Optional[float]
    #: cumulative lots over the whole basket
    total_lots: float
    #: lot-weighted average entry price, i.e. the break-even price
    break_even: Optional[float]
    #: max-min open price across fills, in the quote currency
    cumulative_distance: Optional[float]


@dataclass
class ScanResult:
    """Everything one symbol+direction produced, plus the tuning used."""

    symbol: str
    direction: str
    cycles: List[Cycle] = field(default_factory=list)
    gap_hours: float = DEFAULT_GAP_HOURS

    @property
    def trade_count(self) -> int:
        return sum(len(c.trades) for c in self.cycles)

    @property
    def deepest_layers(self) -> int:
        return max((c.max_layer for c in self.cycles), default=0)

    @property
    def step(self) -> Optional[StepStats]:
        """Step statistics for the deepest cycle, or None when there is none."""
        if not self.cycles:
            return None
        deepest = max(self.cycles, key=lambda c: (c.max_layer, len(c.trades)))
        return step_stats(deepest)

    def lots_histogram(self) -> Dict[float, int]:
        c: Counter = Counter()
        for cyc in self.cycles:
            for t in cyc.trades:
                c[round(t.lots, 2)] += 1
        return dict(sorted(c.items()))


def _prices_from_trades(trades: Sequence[Trade]) -> Optional[List[float]]:
    """The fills' entry prices, or ``None`` when any of them is missing.

    ``open_price`` comes from the CSV's ``Open Price`` column. A zero there means
    the export left it blank, which would silently pull the break-even toward
    zero, so a single missing value disqualifies the whole basket rather than
    being skipped.
    """
    prices = [t.open_price for t in trades]
    if not prices or any(p <= 0 for p in prices):
        return None
    return prices


def split_cycles(
    trades: Sequence[Trade], gap_hours: float = DEFAULT_GAP_HOURS
) -> List[Cycle]:
    """Group trades into baskets by symbol+direction and a time gap.

    Trades without a parsable open time are placed into the cycle of their
    symbol/direction key in input order, because there is no defensible way to
    time-split them; the count is visible via ``Cycle.trades``.
    """
    buckets: Dict[tuple, List[Trade]] = {}
    for t in trades:
        buckets.setdefault((t.symbol, t.direction), []).append(t)

    cycles: List[Cycle] = []
    gap_seconds = gap_hours * 3600.0

    for (symbol, direction), group in buckets.items():
        timed = [t for t in group if t.open_time is not None]
        untimed = [t for t in group if t.open_time is None]
        timed.sort(key=lambda t: t.open_time)

        current: List[Trade] = []
        previous: Optional[datetime] = None
        for t in timed:
            if previous is not None:
                delta = (t.open_time - previous).total_seconds()
                if delta > gap_seconds:
                    cycles.append(Cycle(symbol, direction, current))
                    current = []
            current.append(t)
            previous = t.open_time
        if current or untimed:
            cycles.append(Cycle(symbol, direction, current + list(untimed)))

    cycles.sort(key=lambda c: (c.symbol, c.direction, c.start or datetime.min))
    return cycles


def step_stats(
    cycle: Cycle, open_prices: Optional[Sequence[float]] = None
) -> StepStats:
    """Multiplier, cumulative distance and break-even for one basket.

    When ``open_prices`` is omitted the fills' own ``open_price`` values are
    used. If any of those is blank, break-even and distance come back as ``None``
    rather than being guessed from close prices or from a partial basket.
    """
    lots = cycle.lots
    first_lot = min(lots) if lots else 0.0
    last_lot = max(lots) if lots else 0.0
    distinct = len(set(round(x, 2) for x in lots))

    multiplier: Optional[float] = None
    if distinct > 1 and first_lot > 0:
        multiplier = (last_lot / first_lot) ** (1.0 / (distinct - 1))

    if open_prices is None:
        open_prices = _prices_from_trades(cycle.trades)

    break_even: Optional[float] = None
    distance: Optional[float] = None
    if open_prices and len(open_prices) == len(lots) and sum(lots) > 0:
        break_even = sum(p * q for p, q in zip(open_prices, lots)) / sum(lots)
        distance = max(open_prices) - min(open_prices)

    return StepStats(
        first_lot=first_lot,
        last_lot=last_lot,
        distinct_lots=distinct,
        multiplier=multiplier,
        total_lots=cycle.total_lots,
        break_even=break_even,
        cumulative_distance=distance,
    )


def scan_symbol(
    trades: Sequence[Trade],
    symbol: str,
    direction: Optional[str] = None,
    gap_hours: float = DEFAULT_GAP_HOURS,
) -> List[ScanResult]:
    """Scan one symbol (optionally one direction) into per-direction results."""
    subset = [t for t in trades if t.symbol == symbol]
    if direction:
        subset = [t for t in subset if t.direction == direction]

    by_dir: Dict[str, List[Trade]] = {}
    for t in subset:
        by_dir.setdefault(t.direction, []).append(t)

    out: List[ScanResult] = []
    for d, group in sorted(by_dir.items()):
        out.append(
            ScanResult(
                symbol=symbol,
                direction=d,
                cycles=split_cycles(group, gap_hours),
                gap_hours=gap_hours,
            )
        )
    return out
