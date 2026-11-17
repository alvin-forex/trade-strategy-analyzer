"""Parameter sweep used to settle the undocumented algorithm semantics.

The original indicator manual documents only parameter *names* and defaults; it
never defines Deviation units, Depth direction, Backstep meaning, or what the
Merge Percentage is measured against. This tool enumerates the plausible
readings and scores each one against the two known ground-truth sets:

  * original indicator panel (Alpari, EURUSD H1, Date Range window):
        49 swings -> 39 / 7 / 3, Total bars 630 / 211 / 162,
        Average bars 16.2 / 30.1 / 54.0
  * manual example : 53 swings -> 42 / 8 / 3

The panel numbers are the authoritative target; see ASSUMPTIONS.md.

Run::

    python -m engine.sweep --bars engine/evidence/a1/mt4_EURUSD_H1_bars.csv

Nothing here is used by ``engine.extract``; it exists so the chosen semantics
are evidence-backed rather than asserted.
"""

from __future__ import annotations

import argparse
import itertools
from dataclasses import dataclass
from typing import Iterable, List, Optional, Sequence, Tuple

from .bar import Bar, load_bars_csv, pip_size, slice_window
from .buckets import percentile_inc, percentile_nearest_rank, split_counts
from .merge import build_waves
from .zigzag import Pivot, zigzag

# --- ground truth -----------------------------------------------------------
PARITY_N = 49
PARITY_COUNTS = (39, 7, 3)
PARITY_TOTAL_BARS = (630, 211, 162)
PARITY_AVG_BARS = (16.2, 30.1, 54.0)

MANUAL_N = 53
MANUAL_COUNTS = (42, 8, 3)


@dataclass
class Candidate:
    dev_unit: str  # "points" | "pips"
    merge_mode: str  # "pre" | "post" | "wave"
    bar_mode: str  # "exclusive" | "inclusive"
    bucket_boundary: str  # "rank" | "inc"
    depth: int
    deviation: int
    backstep: int
    merge_pct: float

    def label(self) -> str:
        return (
            f"dev={self.deviation}{self.dev_unit[0]} d={self.depth} b={self.backstep} "
            f"merge={self.merge_pct:g}%/{self.merge_mode} bars={self.bar_mode[0]} "
            f"bkt={self.bucket_boundary}"
        )


def merge_wave_mode(pivots: Sequence[Pivot], pct: float) -> List[Pivot]:
    """Merge operating on the *wave* sequence instead of the pivot sequence.

    A wave is dropped (its endpoints absorbed) when its own amplitude is under
    ``pct``% of the previous wave's amplitude. Equivalent to the pivot test for
    the simple case but handles runs of small waves differently.
    """
    if len(pivots) < 3:
        return list(pivots)
    ratio = pct / 100.0
    amps = [abs(pivots[i + 1].price - pivots[i].price) for i in range(len(pivots) - 1)]
    keep = [True] * len(pivots)
    prev_kept_amp: Optional[float] = amps[0] if amps else None
    for w in range(1, len(amps)):
        if prev_kept_amp and amps[w] < ratio * prev_kept_amp:
            # drop both endpoints of this small wave: keep chain alternating by
            # removing the pivot that ends it
            keep[w + 1] = False
        else:
            prev_kept_amp = amps[w]
    return [p for i, p in enumerate(pivots) if keep[i]]


def apply_merge(pivots: Sequence[Pivot], pct: float, mode: str) -> List[Pivot]:
    from .merge import merge_pivots

    if mode == "wave":
        return merge_wave_mode(pivots, pct)
    return merge_pivots(pivots, pct, mode)  # drop_next / pre / post


def bucket_bars(
    waves_amp: Sequence[float], waves_bars: Sequence[int], boundary: str
) -> Tuple[List[int], List[int], List[float]]:
    """Assign waves to the three classes and return (counts, total_bars, avg_bars)."""
    n = len(waves_amp)
    if n == 0:
        return [0, 0, 0], [0, 0, 0], [0.0, 0.0, 0.0]
    counts = split_counts(n)
    if boundary == "inc":
        p80 = percentile_inc(sorted(waves_amp), 80)
        p95 = percentile_inc(sorted(waves_amp), 95)
        edges = [p80, p95]
    else:  # rank: cut on the sorted sample at the class counts
        s = sorted(waves_amp)
        c0, c1 = counts[0], counts[0] + counts[1]
        edges = [s[min(c0, n) - 1], s[min(c1, n) - 1]]

    groups: List[List[int]] = [[], [], []]
    for i, a in enumerate(waves_amp):
        if a <= edges[0]:
            groups[0].append(i)
        elif a <= edges[1]:
            groups[1].append(i)
        else:
            groups[2].append(i)

    tot = [sum(waves_bars[i] for i in g) for g in groups]
    cnt = [len(g) for g in groups]
    avg = [round(t / c, 1) if c else 0.0 for t, c in zip(tot, cnt)]
    return cnt, tot, avg


def score(cnt, tot, avg) -> Tuple[int, str]:
    """Lower is better. Weighted so bars dominate, then counts."""
    if len(tot) != 3:
        return (10**9, "no buckets")
    d_bars = sum(abs(a - b) for a, b in zip(tot, PARITY_TOTAL_BARS))
    d_cnt = sum(abs(a - b) for a, b in zip(cnt, PARITY_COUNTS))
    d_avg = sum(abs(a - b) for a, b in zip(avg, PARITY_AVG_BARS))
    total = d_bars * 10 + d_cnt * 40 + d_avg * 5
    return (int(total), f"dCnt={d_cnt} dBars={d_bars} dAvg={d_avg:.1f}")


def evaluate(
    bars: Sequence[Bar], cand: Candidate
) -> Tuple[int, List[int], List[int], List[float], int, int]:
    point = 1e-5
    pip = pip_size(point, 5)
    dev_points = cand.deviation if cand.dev_unit == "points" else cand.deviation * 10
    pivots = zigzag(bars, cand.depth, dev_points, cand.backstep, point)
    merged = apply_merge(pivots, cand.merge_pct, cand.merge_mode)
    waves = build_waves(merged, pip, cand.bar_mode)
    amps = [w.amplitude_pips for w in waves]
    brs = [w.bars for w in waves]
    cnt, tot, avg = bucket_bars(amps, brs, cand.bucket_boundary)
    return len(waves), cnt, tot, avg, sum(brs), len(pivots)


def sweep(
    bars: Sequence[Bar],
    merge_pcts: Iterable[float] = (25, 30, 35, 40, 45, 50, 55, 60),
    depths: Iterable[int] = (12,),
    deviations: Iterable[int] = (5,),
    backsteps: Iterable[int] = (3,),
    limit: int = 20,
) -> List[Tuple[int, str, Candidate, tuple]]:
    out = []
    combos = itertools.product(
        ("points", "pips"),
        ("drop_next", "pre", "post", "wave"),
        ("exclusive", "inclusive"),
        ("rank", "inc"),
        depths,
        deviations,
        backsteps,
        merge_pcts,
    )
    for dev_unit, mmode, bmode, bkt, d, dv, bs, mp in combos:
        cand = Candidate(dev_unit, mmode, bmode, bkt, d, dv, bs, float(mp))
        n, cnt, tot, avg, total_bars, n_piv = evaluate(bars, cand)
        s, why = score(cnt, tot, avg)
        if n != PARITY_N:
            s += abs(n - PARITY_N) * 30
            why += f" [n={n}]"
        out.append((s, why, cand, (n, cnt, tot, avg, total_bars, n_piv)))
    out.sort(key=lambda r: r[0])
    return out[:limit]


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Semantics sweep for the wave engine")
    ap.add_argument("--bars", default="engine/evidence/a1/mt4_EURUSD_H1_bars.csv")
    ap.add_argument("--from", dest="start", default="2026-09-17T02:00")
    ap.add_argument("--to", dest="end", default="2026-11-16T17:00")
    ap.add_argument("--limit", type=int, default=20)
    args = ap.parse_args(argv)

    all_bars = load_bars_csv(args.bars)
    window = slice_window(all_bars, args.start, args.end)
    print(f"window bars = {len(window)}  ({window[0].time_label} .. {window[-1].time_label})")
    print(f"target: n={PARITY_N} counts={PARITY_COUNTS} bars={PARITY_TOTAL_BARS} avg={PARITY_AVG_BARS}")
    print()
    for s, why, cand, res in sweep(window, limit=args.limit):
        n, cnt, tot, avg, total_bars, n_piv = res
        print(f"score={s:6d}  n={n:3d} piv={n_piv:3d} cnt={cnt} bars={tot} avg={avg} total={total_bars}")
        print(f"          {cand.label()}  {why}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
