"""Bucketing into 80 / 15 / 5 amplitude classes (stage A2 preview).

A1 does not emit buckets, but the split rule is pinned here because two
independent ground-truth sets constrain it: the manual's own EURUSD example
(53 swings -> 42 / 8 / 3) and the AC parity window (49 swings -> 39 / 7 / 3).

Only round-half-up on each cumulative share fits both; plain floor fails on
53 swings (gives 42 / 7 / 4).

Candidates for the *boundary values* (what pip number separates the classes)
are kept switchable: the manual shows the printed ranges as contiguous
(e.g. 17-73 / 73-119 / 119-166) but never states the formula, and the AC parity
table does not include ranges at all, so ranges are NOT used as an acceptance
criterion.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Sequence

BUCKET_LABELS = ("Normal", "Medium", "Crazy")  # 80% / 15% / 5%


def _round_half_up(x: float) -> int:
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def split_counts(total: int, shares=(80, 15, 5)) -> List[int]:
    """Class counts from swing count, remainder to the last class.

    ``round`` first two shares, last takes the remainder. Verified against
    49 -> 39/7/3 and 53 -> 42/8/3.
    """
    if total <= 0:
        return [0, 0, 0]
    a = _round_half_up(total * shares[0] / 100.0)
    b = _round_half_up(total * shares[1] / 100.0)
    return [a, b, total - a - b]


def percentile_nearest_rank(sorted_vals: Sequence[float], pct: float) -> float:
    """Excel PERCENTILE.EXC-style nearest-rank (rank = ceil(p/100 * N))."""
    n = len(sorted_vals)
    if n == 0:
        raise ValueError("empty sample")
    rank = max(1, min(n, int(-(-pct * n // 100))))  # ceil(pct*n/100)
    return sorted_vals[rank - 1]


def percentile_inc(sorted_vals: Sequence[float], pct: float) -> float:
    """Excel PERCENTILE.INC with linear interpolation."""
    n = len(sorted_vals)
    if n == 0:
        raise ValueError("empty sample")
    if n == 1:
        return sorted_vals[0]
    pos = (pct / 100.0) * (n - 1)  # 0-based
    lo = int(pos)
    hi = min(lo + 1, n - 1)
    frac = pos - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


@dataclass(frozen=True)
class BucketStat:
    label: str
    count: int
    total_bars: int
    average_bars: float
    total_pips: float
    average_pips: float
    longest_bars: int
    shortest_bars: int
    longest_pips: float
    shortest_pips: float
    lower_pips: float
    upper_pips: float


def compute_buckets(
    amplitudes: Sequence[float],
    bars: Sequence[int],
    method: str = "percentile-inc",
) -> List[BucketStat]:
    """Classify swings by amplitude into 80/15/5 classes, by swing count.

    ``method`` only decides how the class *boundaries* are printed
    (``nearest-rank`` or ``percentile-inc``); the counts always come from
    :func:`split_counts`, which is the rule the ground truth supports.
    """
    n = len(amplitudes)
    if n == 0:
        return []
    counts = split_counts(n)
    order = sorted(range(n), key=lambda i: amplitudes[i])
    bounds: List[float] = []
    cum = 0
    for c in counts[:-1]:
        cum += c
        if cum <= 0:
            bounds.append(float("-inf"))
        elif cum >= n:
            bounds.append(float("inf"))
        else:
            v = order[cum - 1]
            bounds.append(amplitudes[v])

    def bucket_of(amp: float) -> int:
        for i, b in enumerate(bounds):
            if amp <= b:
                return i
        return len(counts) - 1

    members: List[List[int]] = [[] for _ in counts]
    for i, amp in enumerate(amplitudes):
        members[bucket_of(amp)].append(i)

    stats: List[BucketStat] = []
    for bi, label in enumerate(BUCKET_LABELS):
        idxs = members[bi]
        if not idxs:
            stats.append(
                BucketStat(label, 0, 0, 0.0, 0.0, 0.0, 0, 0, 0.0, 0.0, 0.0, 0.0)
            )
            continue
        amps = [amplitudes[i] for i in idxs]
        brs = [bars[i] for i in idxs]
        # Longest / Shortest are the waves with the most / fewest *bars*; their
        # pips are that same wave's amplitude, NOT the class's max/min amplitude.
        # The panel makes this unambiguous: Medium shows Longest 56 bars / 119.4
        # pips and Shortest 11 bars / 128.5 pips — the "shortest" wave carries
        # MORE pips than the "longest" one, so pips are not sorted independently.
        i_long = max(range(len(idxs)), key=lambda j: brs[j])
        i_short = min(range(len(idxs)), key=lambda j: brs[j])
        stats.append(
            BucketStat(
                label=label,
                count=len(idxs),
                total_bars=sum(brs),
                average_bars=round(sum(brs) / len(brs), 1),
                total_pips=round(sum(amps), 1),
                average_pips=round(sum(amps) / len(amps), 1),
                longest_bars=brs[i_long],
                shortest_bars=brs[i_short],
                longest_pips=round(amps[i_long], 1),
                shortest_pips=round(amps[i_short], 1),
                lower_pips=round(min(amps), 1),
                upper_pips=round(max(amps), 1),
            )
        )
    return stats
