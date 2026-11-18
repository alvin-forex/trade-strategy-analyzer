"""Bucketing into 80 / 15 / 5 amplitude classes, plus the Range display bounds.

Two separate concepts live here and must not be confused:

**Class counts** (how many swings fall in each class)
    Three derivations are available via ``method``:

    ``count``  round-half-up on the shares, remainder to the last class.
               This is the only one that reproduces both ground-truth sets:
               49 -> 39/7/3 (panel) and 53 -> 42/8/3 (manual). Default.
    ``rank``   boundaries at nearest-rank percentiles 80 / 95.
    ``inc``    boundaries at PERCENTILE.INC (linear interpolation) 80 / 95.

    Requirement v0.2 §2 mandates that both percentile methods be available and
    switchable; ``count`` is the default because it is the only one with
    evidence behind it.

**Range display bounds** (the ``12-110 / 110-128 / 128-249`` numbers on the panel)
    Empirically recovered 2026-11-18 from the real panel screenshot. Four cut
    points, all truncated with ``floor`` (NOT rounded):

    ``b0 = floor(min amplitude over the RAW pivot chain, before merge)``
    ``b1 = floor(merged amplitudes sorted, index c0)``      first of Medium
    ``b2 = floor(merged amplitudes sorted, index c0+c1-1)``  last of Medium
    ``b3 = floor(merged amplitudes sorted, last)``

    Verified: 12 / 110 / 128 all match the panel exactly. ``b3`` lands at 253
    against the panel's 249, which is the same 4-pip tail artefact that makes
    our longest wave 103 bars instead of the panel's 99 — not a separate bug.

    The bounds are "next class's start", so adjacent bands share their edge
    (110, 128) exactly as the panel prints them. They are therefore NOT the
    per-class min/max, which is also why the manual's own example shows
    Normal 17-73 while its Longest is only 61.0 pips.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Sequence, Tuple

BUCKET_LABELS = ("Normal", "Medium", "Crazy")  # 80% / 15% / 5%
SHARES = (80, 15, 5)

#: band labels that must be printed verbatim on outputs and web pages
BAND_LABELS = ("80% Range", "15% Range", "5% Range")

BUCKET_METHODS = ("count", "rank", "inc")

#: Below this many swings the 80/15/5 split cannot produce three non-empty
#: classes, so the caller must handle it rather than receive silent zeros.
MIN_SWINGS = 3


class InsufficientSampleError(ValueError):
    """Raised when there are too few swings to form three classes."""

    def __init__(self, found: int, required: int = MIN_SWINGS) -> None:
        self.found = found
        self.required = required
        super().__init__(
            f"need at least {required} swings to split into 80/15/5, found {found}"
        )


def _round_half_up(x: float) -> int:
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def split_counts(total: int, shares=SHARES) -> List[int]:
    """Class counts from swing count, remainder to the last class.

    ``round`` first two shares, last takes the remainder. Verified against
    49 -> 39/7/3 (indicator panel) and 53 -> 42/8/3 (manual example).
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


def cut_points(
    amplitudes: Sequence[float], method: str = "count", shares=SHARES
) -> Tuple[List[float], List[int]]:
    """Return (bounds, counts) for the chosen ``method``.

    ``bounds`` has two entries: the upper edge of Normal and the upper edge of
    Medium. Boundaries are inclusive on the lower class.
    """
    if method not in BUCKET_METHODS:
        raise ValueError(f"method must be one of {BUCKET_METHODS}")
    n = len(amplitudes)
    if n == 0:
        return ([], [0, 0, 0])
    s = sorted(amplitudes)

    if method == "count":
        counts = split_counts(n, shares)
        c0, c1 = counts[0], counts[1]
        bounds = [
            s[min(c0, n) - 1] if c0 > 0 else float("-inf"),
            s[min(c0 + c1, n) - 1] if c0 + c1 > 0 else float("inf"),
        ]
        return (bounds, counts)

    if method == "rank":
        b1 = percentile_nearest_rank(s, float(shares[0]))
        b2 = percentile_nearest_rank(s, float(shares[0] + shares[1]))
    else:  # inc
        b1 = percentile_inc(s, float(shares[0]))
        b2 = percentile_inc(s, float(shares[0] + shares[1]))

    counts = [
        sum(1 for a in s if a <= b1),
        sum(1 for a in s if b1 < a <= b2),
        sum(1 for a in s if a > b2),
    ]
    return ([b1, b2], counts)


def range_bounds(
    raw_amplitudes: Sequence[float], merged_amplitudes: Sequence[float], shares=SHARES
) -> Tuple[int, int, int, int]:
    """The four ``floor``-truncated numbers the panel prints as pip ranges.

    ``(b0, b1, b2, b3)`` -> bands ``b0-b1 / b1-b2 / b2-b3``.

    ``b0`` comes from the **raw** chain (before merge); the rest come from the
    merged, amplitude-sorted list. See the module docstring for the evidence.
    """
    if not merged_amplitudes:
        return (0, 0, 0, 0)
    n = len(merged_amplitudes)
    counts = split_counts(n, shares)
    c0, c1 = counts[0], counts[1]
    s = sorted(merged_amplitudes)
    raw_min = min(raw_amplitudes) if raw_amplitudes else s[0]

    b0 = int(math.floor(raw_min))
    b1 = int(math.floor(s[min(c0, n - 1)]))
    b2 = int(math.floor(s[min(c0 + c1 - 1, n - 1)]))
    b3 = int(math.floor(s[-1]))
    return (b0, b1, b2, b3)


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
    lower_display: int = 0
    upper_display: int = 0


def compute_buckets(
    amplitudes: Sequence[float],
    bars: Sequence[int],
    method: str = "count",
    raw_amplitudes: Optional[Sequence[float]] = None,
    shares=SHARES,
    strict: bool = False,
) -> List[BucketStat]:
    """Classify swings by amplitude into 80/15/5 classes.

    ``method`` selects how the class membership is derived (see
    :func:`cut_points`); ``count`` is the default and the only method that
    reproduces the ground truth.

    ``raw_amplitudes`` (pre-merge amplitudes) is only needed to fill the outer
    lower display bound; pass it when producing panel-parity tables.

    ``strict`` raises :class:`InsufficientSampleError` when the swing count is
    below :data:`MIN_SWINGS`. Non-strict returns zeroed rows, which is what a
    display layer wants; batch runs should pass ``strict=True`` so a thin
    sample never silently produces an empty volatility table.
    """
    n = len(amplitudes)
    if n == 0:
        if strict:
            raise InsufficientSampleError(0)
        return []
    if strict and n < MIN_SWINGS:
        raise InsufficientSampleError(n)
    bounds, counts = cut_points(amplitudes, method, shares)

    def bucket_of(amp: float) -> int:
        if amp <= bounds[0]:
            return 0
        if amp <= bounds[1]:
            return 1
        return 2

    members: List[List[int]] = [[], [], []]
    for i, amp in enumerate(amplitudes):
        members[bucket_of(amp)].append(i)

    # Display ranges: floor-truncated, panel style (adjacent bands share edges).
    if raw_amplitudes is not None:
        rb = range_bounds(raw_amplitudes, amplitudes, shares)
    else:
        rb = (0, 0, 0, 0)

    stats: List[BucketStat] = []
    for bi, label in enumerate(BUCKET_LABELS):
        idxs = members[bi]
        if not idxs:
            stats.append(
                BucketStat(label, 0, 0, 0.0, 0.0, 0.0, 0, 0, 0.0, 0.0, 0.0, 0.0, 0, 0)
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
                lower_display=rb[bi],
                upper_display=rb[bi + 1],
            )
        )
    return stats
