"""Wave construction + Merge Percentage filtering.

Merge semantics
---------------
The manual states only: "Merge Percentage = how much pullback counts as the end
of a move" (default 35%). It does not say what the 35% is measured against.

`merge_pct` here is always measured as::

    retrace_k = |P[k+1] - P[k]|      # the pullback that would end wave k
    base      = |P[k]   - P[m]|      # amplitude of the swing arriving at P[k]
    merge     = retrace_k < pct/100 * base

Why "amplitude of the arriving swing" is the defensible base
-----------------------------------------------------------
* Scale invariance: a 20-pip and a 300-pip swing get judged by the same ruler.
  Any absolute base (price level, ATR, fixed pips) needs a second tuning knob
  the manual never mentions.
* "Relative to the last extremum" reduces to the same formula: both the
  pullback and the arriving amplitude are anchored on P[k], the extremum whose
  validity is being tested. The genuinely ambiguous part is therefore not
  *which point* but *pre- vs post-merge* base -- see ``base_mode``.

Two base modes are provided so the question can be settled empirically:

``pre``
    The base is always read off the **original** ZigZag chain. One left-to-right
    pass; a pivot is deleted when the pullback away from it is under 35% of the
    swing that led into it, as measured before any merging happened.

``post``
    The base is read off the chain **as merged so far**, iterated to a fixpoint
    ("merge until the chain stops changing"). This treats the merged swing as
    the real swing, so a shallow pullback after a big merged wave is still
    correctly rejected.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from .zigzag import Pivot

#: safety cap for the ``post`` fixpoint loop; normally settles in 1-3 rounds
MAX_ITER = 50


@dataclass(frozen=True)
class Wave:
    idx: int  # 1-based, oldest first
    start_idx: int  # bar index of the starting pivot
    end_idx: int  # bar index of the ending pivot
    start_time: str
    end_time: str
    bars: int
    amplitude_pips: float
    direction: str  # "up" | "down"


def merge_pivots_pre(pivots: Sequence[Pivot], pct: float) -> List[Pivot]:
    """Single pass; base amplitudes always come from the original chain."""
    if len(pivots) < 3:
        return list(pivots)
    ratio = pct / 100.0
    survivors: List[Pivot] = [pivots[0]]
    for k in range(1, len(pivots) - 1):
        base = abs(pivots[k].price - pivots[k - 1].price)
        retrace = abs(pivots[k + 1].price - pivots[k].price)
        if base > 0 and retrace < ratio * base:
            continue  # P[k] is not a real turning point
        survivors.append(pivots[k])
    survivors.append(pivots[-1])
    return survivors


def merge_pivots_post(
    pivots: Sequence[Pivot], pct: float, max_iter: int = MAX_ITER
) -> List[Pivot]:
    """Iterate on the merged chain until no pivot is dropped."""
    if len(pivots) < 3:
        return list(pivots)
    ratio = pct / 100.0
    chain = list(pivots)
    for _ in range(max_iter):
        out: List[Pivot] = [chain[0]]
        dropped = False
        for k in range(1, len(chain) - 1):
            base = abs(chain[k].price - out[-1].price)  # merged-so-far base
            retrace = abs(chain[k + 1].price - chain[k].price)
            if base > 0 and retrace < ratio * base:
                dropped = True
                continue
            out.append(chain[k])
        out.append(chain[-1])
        chain = out
        if not dropped:
            break
    return chain


def merge_pivots_drop_next(
    pivots: Sequence[Pivot], pct: float, max_iter: int = MAX_ITER
) -> List[Pivot]:
    """Iterate, deleting the pivot that *ends* a too-shallow retracement.

    Recovered empirically against the real panel (2026-11-18): this reading
    reproduces 49 swings / 39-7-3 and the whole Medium class exactly
    (211 bars, 831.1 pips, 30.1 avg, longest 56, shortest 11). Neither ``pre``
    nor ``post`` can do that — they only reach 55 swings.
    """
    if len(pivots) < 3:
        return list(pivots)
    ratio = pct / 100.0
    chain = list(pivots)
    for _ in range(max_iter):
        out: List[Pivot] = [chain[0]]
        k = 1
        dropped = False
        while k < len(chain) - 1:
            leg = abs(chain[k].price - out[-1].price)
            retrace = abs(chain[k + 1].price - chain[k].price)
            if leg > 0 and retrace < ratio * leg:
                k += 2  # absorb: skip the pivot that ended the shallow pullback
                dropped = True
                continue
            out.append(chain[k])
            k += 1
        out.extend(chain[k:])
        chain = out
        if not dropped:
            break
    return chain


def merge_pivots(
    pivots: Sequence[Pivot], pct: float = 35.0, base_mode: str = "drop_next"
) -> List[Pivot]:
    """Dispatch on ``base_mode``: ``"drop_next"`` (default), ``"pre"`` or ``"post"``."""
    if base_mode == "drop_next":
        return merge_pivots_drop_next(pivots, pct)
    if base_mode == "pre":
        return merge_pivots_pre(pivots, pct)
    if base_mode == "post":
        return merge_pivots_post(pivots, pct)
    raise ValueError("base_mode must be 'drop_next', 'pre' or 'post'")


def build_waves(
    pivots: Sequence[Pivot],
    pip: float,
    bar_mode: str = "exclusive",
) -> List[Wave]:
    """Turn an alternating pivot chain into waves (one wave per pivot pair)."""
    waves: List[Wave] = []
    for k in range(len(pivots) - 1):
        a, b = pivots[k], pivots[k + 1]
        span = b.idx - a.idx
        bars = span + 1 if bar_mode == "inclusive" else span
        waves.append(
            Wave(
                idx=k + 1,
                start_idx=a.idx,
                end_idx=b.idx,
                start_time=a.time_label,
                end_time=b.time_label,
                bars=bars,
                amplitude_pips=round(abs(b.price - a.price) / pip, 2),
                direction="up" if b.price > a.price else "down",
            )
        )
    return waves
