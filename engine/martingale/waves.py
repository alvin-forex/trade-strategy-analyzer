"""Swing-amplitude bands over a rolling window.

What the bands are, and what they are not
-----------------------------------------
The website shows three numbers per symbol, labelled 80% / 15% / 5% Range. Per
``docs/martingale/TSA_Martingale_Technical_Docs_v1.0.md`` §13 their statistical
meaning is *not* documented, so this module does not claim to reproduce them.
It computes the one interpretation that has been written down anywhere -- the
OpenClaw prototype -- and names its output for what it actually is: quantiles of
merged swing amplitude inside a fixed bar window.

The prototype's rule, kept verbatim because it is the only written spec:

    pivots  = ZigZag(depth=12)
    segs    = |price[i] - price[i-1]| over consecutive pivots, where a new
              amplitude is dropped when  amp < 0.35 * previous kept amplitude
    bands   = (min, P80, P95, max) of the kept amplitudes

``merge`` is therefore not a filter on price but a filter on amplitude: it
removes swings that are small *relative to the swing before them*, which is why
a flat market yields few segments rather than many small ones.

Window semantics
----------------
The window is ``window_bars`` long and advances by ``step_bars``. Each window is
scored on its own; nothing is carried across window boundaries. That means the
last ``depth-1`` bars of a window can never confirm a pivot (the ZigZag port
needs ``depth`` bars of look-back), so the newest window is always slightly
stale -- the number of unusable trailing bars is reported rather than hidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Sequence

from ..bar import Bar
from ..zigzag import Pivot, zigzag

#: Prototype defaults. Depth 12 and merge 0.35 come from the OC prototype;
#: window 1024 and step 25 come from the same script. None of the four is
#: derived from theory, so all are parameters rather than constants.
DEFAULT_DEPTH = 12
DEFAULT_DEVIATION_POINTS = 5
DEFAULT_BACKSTEP = 3
DEFAULT_MERGE_RATIO = 0.35
DEFAULT_WINDOW_BARS = 1024
DEFAULT_STEP_BARS = 25


@dataclass(frozen=True)
class BandSet:
    """Quantiles of merged swing amplitude for one window, in pips."""

    window_start: int  # index into the caller's bar list, inclusive
    window_end: int  # exclusive
    usable_bars: int  # bars that could contribute a confirmed pivot
    segments: int  # kept amplitudes
    low: float  # min amplitude
    p80: float
    p95: float
    high: float  # max amplitude


@dataclass
class WaveScan:
    """All windows for one series, plus the tuning used to make them."""

    symbol: str
    pip_size: float
    depth: int
    merge_ratio: float
    window_bars: int
    step_bars: int
    bands: List[BandSet] = field(default_factory=list)

    @property
    def windows(self) -> int:
        return len(self.bands)

    def median_bands(self) -> Optional[BandSet]:
        """The window whose P80 sits at the median of all windows' P80.

        Reporting one window avoids implying the distribution is stable across
        time; returning the middle one is at least reproducible and is stated
        as such in the output rather than summarised as a mean.
        """
        if not self.bands:
            return None
        ordered = sorted(self.bands, key=lambda b: b.p80)
        return ordered[len(ordered) // 2]


def pip_size_from_digits(digits: int) -> float:
    """The conventional pip size for a quote carrying ``digits`` decimals.

    A market convention, not a property of the data: brokers quote FX to 3 or 5
    decimals (``point`` = one more digit than the pip), while 2- and 4-digit
    quotes are already at pip resolution. Metals and indices do not necessarily
    follow it, which is why :func:`scan_waves` takes an explicit override.
    """
    point = 10.0**-digits
    return point * 10.0 if digits in (3, 5) else point


def merge_amplitudes(pivots: Sequence[Pivot], merge_ratio: float = DEFAULT_MERGE_RATIO) -> List[float]:
    """Swing amplitudes in price units, after the relative-size filter.

    A candidate amplitude is dropped when it is smaller than
    ``merge_ratio`` times the most recently *kept* amplitude. Non-positive
    amplitudes are skipped because a zero-height swing carries no information.
    """
    kept: List[float] = []
    for prev, cur in zip(pivots, pivots[1:]):
        amp = abs(cur.price - prev.price)
        if amp <= 0:
            continue
        if kept and amp < merge_ratio * kept[-1]:
            continue
        kept.append(amp)
    return kept


def quantile(sorted_values: Sequence[float], p: float) -> float:
    """Linear-interpolated quantile, matching the prototype's ``inc``.

    ``p`` is in ``[0, 1]``. Position is ``(n-1)*p``; the result interpolates
    between the two neighbouring order statistics. With ``n == 1`` the single
    value is returned for every ``p``.
    """
    n = len(sorted_values)
    if n == 0:
        raise ValueError("quantile of empty sequence")
    if not 0.0 <= p <= 1.0:
        raise ValueError(f"quantile p out of range: {p}")
    pos = (n - 1) * p
    lo = int(pos)
    if lo + 1 >= n:
        return float(sorted_values[-1])
    frac = pos - lo
    return float(sorted_values[lo] + frac * (sorted_values[lo + 1] - sorted_values[lo]))


def band_set(
    bars: Sequence[Bar],
    window_start: int,
    window_end: int,
    pip_size: float,
    depth: int = DEFAULT_DEPTH,
    deviation_points: int = DEFAULT_DEVIATION_POINTS,
    backstep: int = DEFAULT_BACKSTEP,
    merge_ratio: float = DEFAULT_MERGE_RATIO,
    point: float = 1e-5,
    min_segments: int = 4,
) -> Optional[BandSet]:
    """Compute one window's bands, or ``None`` when it holds too few swings.

    ``min_segments`` guards the quantiles: with three amplitudes, P95 and max
    are the same number and the window says nothing about the tail.
    """
    window = bars[window_start:window_end]
    pivots = zigzag(window, depth=depth, deviation_points=deviation_points, backstep=backstep, point=point)
    amps = sorted(a / pip_size for a in merge_amplitudes(pivots, merge_ratio))
    if len(amps) < min_segments:
        return None
    return BandSet(
        window_start=window_start,
        window_end=window_end,
        usable_bars=max(0, len(window) - (depth - 1)),
        segments=len(amps),
        low=amps[0],
        p80=quantile(amps, 0.80),
        p95=quantile(amps, 0.95),
        high=amps[-1],
    )


def scan_waves(
    bars: Sequence[Bar],
    symbol: str = "",
    pip_size: Optional[float] = None,
    depth: int = DEFAULT_DEPTH,
    deviation_points: int = DEFAULT_DEVIATION_POINTS,
    backstep: int = DEFAULT_BACKSTEP,
    merge_ratio: float = DEFAULT_MERGE_RATIO,
    window_bars: int = DEFAULT_WINDOW_BARS,
    step_bars: int = DEFAULT_STEP_BARS,
    point: float = 1e-5,
    min_segments: int = 4,
) -> WaveScan:
    """Slide a fixed window over ``bars`` and collect one :class:`BandSet` each.

    ``pip_size`` is required in practice; when omitted the caller gets
    ``1.0`` and the bands come back in price units, which is honest but not
    comparable across symbols. The caller should pass
    :func:`pip_size_from_digits` or a known override.
    """
    pip = 1.0 if pip_size is None else pip_size
    out = WaveScan(
        symbol=symbol,
        pip_size=pip,
        depth=depth,
        merge_ratio=merge_ratio,
        window_bars=window_bars,
        step_bars=step_bars,
    )
    n = len(bars)
    if n < window_bars or step_bars <= 0:
        return out

    start = 0
    while start + window_bars <= n:
        bs = band_set(
            bars,
            start,
            start + window_bars,
            pip_size=pip,
            depth=depth,
            deviation_points=deviation_points,
            backstep=backstep,
            merge_ratio=merge_ratio,
            point=point,
            min_segments=min_segments,
        )
        if bs is not None:
            out.bands.append(bs)
        start += step_bars
    return out
