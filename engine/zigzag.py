"""Swing detection: from-scratch port of the MQL4 ZigZag algorithm.

Why a port instead of a re-invention
------------------------------------
The requirement forbids calling any MT4/MT5 built-in ZigZag, and also forbids
inventing an algorithm. The original scanner is documented only as
"ZigZag(Depth/Deviation/Backstep)", so the only defensible definition is the
published MetaQuotes ZigZag algorithm itself. That algorithm is fully visible
in the shipped ``ZigZag.mq4`` (reference copy:
``engine/evidence/a1/mt4_zigzag_reference.mq4``). This module is a literal
re-implementation of its three passes, so the output is deterministic and can
be diffed pivot-by-pivot against the MQL4 original.

Semantics confirmed from that source (not guessed):

* ``Depth``     -- window size in bars, scanned at shifts ``i .. i+Depth-1``.
                   Note this reaches *forward in time* from bar ``i``, which is
                   why the newest ``Depth-1`` bars can never confirm a pivot
                   and the oldest ``Depth-1`` bars are never scanned.
* ``Deviation`` -- always used as ``InpDeviation * Point``, i.e. **points**,
                   never pips.
* ``Backstep``  -- how many already-marked extrema behind the current bar are
                   cleared when a more extreme value is found. It is NOT a
                   minimum spacing between pivots.

Index convention
----------------
Internally every buffer is indexed by MQL4 **shift** (0 = newest bar), exactly
like the original, so the port can be compared statement by statement.
Callers get pivots in ascending chronological order.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from .bar import Bar

LOOK_HIGH = -1
LOOK_LOW = 1


@dataclass(frozen=True)
class Pivot:
    """A confirmed swing point.

    ``idx`` is the 0-based position inside the supplied chronological window.
    ``kind`` is ``"H"`` for a swing high, ``"L"`` for a swing low.
    """

    idx: int
    time_label: str
    price: float
    kind: str


def zigzag(
    bars: Sequence[Bar],
    depth: int = 12,
    deviation_points: int = 5,
    backstep: int = 3,
    point: float = 1e-5,
) -> List[Pivot]:
    """Return the confirmed ZigZag pivots, ascending in time.

    Mirrors ``ZigZag.mq4``: (1) mark raw extrema per bar with backstep
    clearing, (2) discard repeats via the ``lastlow``/``lasthigh`` carry,
    (3) thin to a strictly alternating high/low chain.
    """
    n = len(bars)
    if backstep >= depth:
        raise ValueError("Backstep cannot be greater or equal to Depth")
    if n < depth + 1:
        return []

    highs = [b.high for b in bars]  # chronological
    lows = [b.low for b in bars]

    def low_at(shift: int) -> float:
        return lows[n - 1 - shift]

    def high_at(shift: int) -> float:
        return highs[n - 1 - shift]

    ext_low = [0.0] * n  # indexed by shift
    ext_high = [0.0] * n
    zz = [0.0] * n

    lastlow = 0.0
    lasthigh = 0.0
    dev = deviation_points * point

    # ---- pass 1+2: raw extrema, oldest -> newest (shift descending) ----
    limit = n - depth
    for i in range(limit, -1, -1):
        # lowest low over shifts i .. i+depth-1  (bar i is the newest of them)
        window_lows = [low_at(i + k) for k in range(depth)]
        extremum = min(window_lows)
        if extremum == lastlow:
            extremum = 0.0
        else:
            lastlow = extremum
            if low_at(i) - extremum > dev:
                extremum = 0.0
            else:
                for back in range(1, backstep + 1):
                    pos = i + back
                    if pos < n and ext_low[pos] != 0 and ext_low[pos] > extremum:
                        ext_low[pos] = 0.0
        ext_low[i] = extremum if low_at(i) == extremum else 0.0

        window_highs = [high_at(i + k) for k in range(depth)]
        extremum = max(window_highs)
        if extremum == lasthigh:
            extremum = 0.0
        else:
            lasthigh = extremum
            if extremum - high_at(i) > dev:
                extremum = 0.0
            else:
                for back in range(1, backstep + 1):
                    pos = i + back
                    if pos < n and ext_high[pos] != 0 and ext_high[pos] < extremum:
                        ext_high[pos] = 0.0
        ext_high[i] = extremum if high_at(i) == extremum else 0.0

    # ---- pass 3: thin to alternating high/low chain ----
    whatlookfor = 0
    curlow = curhigh = 0.0
    lastlow = lasthigh = 0.0
    lastlowpos = lasthighpos = 0
    for i in range(limit, -1, -1):
        if whatlookfor == 0:
            if lastlow == 0.0 and lasthigh == 0.0:
                if ext_high[i] != 0.0:
                    lasthigh = high_at(i)
                    lasthighpos = i
                    whatlookfor = LOOK_HIGH
                    zz[i] = lasthigh
                if ext_low[i] != 0.0:
                    lastlow = low_at(i)
                    lastlowpos = i
                    whatlookfor = LOOK_LOW
                    zz[i] = lastlow
        elif whatlookfor == LOOK_LOW:  # last pivot was a low, seek a high
            if ext_low[i] != 0.0 and ext_low[i] < lastlow and ext_high[i] == 0.0:
                zz[lastlowpos] = 0.0
                lastlowpos = i
                lastlow = ext_low[i]
                zz[i] = lastlow
            if ext_high[i] != 0.0 and ext_low[i] == 0.0:
                lasthigh = ext_high[i]
                lasthighpos = i
                zz[i] = lasthigh
                whatlookfor = LOOK_HIGH
        else:  # last pivot was a high, seek a low
            if ext_high[i] != 0.0 and ext_high[i] > lasthigh and ext_low[i] == 0.0:
                zz[lasthighpos] = 0.0
                lasthighpos = i
                lasthigh = ext_high[i]
                zz[i] = lasthigh
            if ext_low[i] != 0.0 and ext_high[i] == 0.0:
                lastlow = ext_low[i]
                lastlowpos = i
                zz[i] = lastlow
                whatlookfor = LOOK_LOW

    # ---- emit oldest -> newest ----
    pivots: List[Pivot] = []
    for i in range(limit, -1, -1):
        if zz[i] == 0.0:
            continue
        chron = n - 1 - i
        kind = "L" if ext_low[i] != 0.0 and ext_low[i] == zz[i] else "H"
        if pivots and pivots[-1].kind == kind:
            # Alternation is enforced by pass 3; guard defensively.
            if (kind == "H" and zz[i] <= pivots[-1].price) or (
                kind == "L" and zz[i] >= pivots[-1].price
            ):
                continue
        pivots.append(Pivot(idx=chron, time_label=bars[chron].time_label, price=zz[i], kind=kind))
    return pivots
