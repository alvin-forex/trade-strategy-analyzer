"""Grid-versus-volatility fit scoring.

The question: given a martingale grid that adds a layer every *n* pips, how
often does the market actually travel *n* pips against an open basket?

The measurement is deliberately simple and refuses to become a backtest. For a
symbol we take the wave bands (see :mod:`waves`) over a **5-year** window and
compare the grid's step distance against them:

    ratio = step_pips / p80_band_pips

* ``ratio < 0.5``  -- **tight**: a single ordinary swing crosses several layers.
* ``0.5 .. 1.5``  -- **plausible**: the grid needs a real move to deepen.
* ``> 1.5``       -- **wide**: the grid rarely reaches layer 2 at all.

The inverse of the ratio is reported too, as ``implied_layers``: how many steps
one typical swing spans. On real H4 data a 15-pip step against a 210-pip P80
band spans 14 steps, which is the plainest way to say "this grid will be deep".

Why 5 years and not 8: the owner ruled on 2026-11-19 that 5 years is enough for
a backtest. The window is a parameter so the choice is visible in the output
rather than buried here.

Why P80 and not the max: the max is one observation and moves with whichever
crisis is inside the window. P80 is the band the website already displays.

**This is not a recommendation engine.** It does not say a grid is good or bad,
only how its spacing compares to the observed swing distribution. Whether a
tight grid is acceptable is a risk decision that belongs to the owner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Sequence

from ..bar import Bar
from .waves import DEFAULT_MERGE_RATIO, BandSet, WaveScan, scan_waves

#: The owner's ruling: 5 years of history is enough for a backtest.
DEFAULT_YEARS = 5

#: Thresholds for the ratio bands. Named rather than inline so a report can
#: print the rule it applied instead of an adjective with no definition.
TIGHT_BELOW = 0.5
WIDE_ABOVE = 1.5

GRADE_TIGHT = "tight"
GRADE_PLAUSIBLE = "plausible"
GRADE_WIDE = "wide"
GRADE_UNKNOWN = "unknown"


@dataclass(frozen=True)
class FitScore:
    """One symbol's grid against one band set."""

    symbol: str
    step_pips: Optional[float]
    band_pips: Optional[float]
    ratio: Optional[float]
    grade: str
    band_label: str = ""
    segments: int = 0

    @property
    def implied_layers(self) -> Optional[float]:
        """How many grid steps a typical swing spans.

        This is the number a reader can act on, and the inverse of ``ratio``:
        a P80 swing of 210 pips against a 15-pip step spans 14 steps, so a
        deep basket is the normal case rather than the exception. Reported
        alongside the ratio rather than instead of it, because the ratio is the
        quantity the thresholds are defined on.
        """
        if not self.band_pips or not self.step_pips or self.step_pips <= 0:
            return None
        return self.band_pips / self.step_pips

    @property
    def explained(self) -> str:
        """One line a non-technical reader can act on."""
        if self.grade == GRADE_UNKNOWN:
            return "no step distance or no wave bands -- cannot score"
        layers = self.implied_layers
        span = f"{layers:.0f} steps" if layers is not None else "an unknown span"
        return (
            f"grid adds a layer every {self.step_pips:.1f} pips; "
            f"{self.band_label} swing is {self.band_pips:.1f} pips = {span} "
            f"(ratio {self.ratio:.2f} -> {self.grade})"
        )


@dataclass
class FitReport:
    """Every symbol's score plus the inputs, so the numbers can be re-checked."""

    years: int = DEFAULT_YEARS
    p_quantile: float = 0.80
    scores: List[FitScore] = field(default_factory=list)

    def by_grade(self) -> Dict[str, List[FitScore]]:
        out: Dict[str, List[FitScore]] = {}
        for s in self.scores:
            out.setdefault(s.grade, []).append(s)
        return out

    @property
    def worst(self) -> Optional[FitScore]:
        """Lowest ratio among scored symbols -- the most over-tight grid."""
        scored = [s for s in self.scores if s.ratio is not None]
        return min(scored, key=lambda s: s.ratio) if scored else None


def grade_ratio(ratio: Optional[float]) -> str:
    """Map a step/band ratio onto one of the three named grades."""
    if ratio is None:
        return GRADE_UNKNOWN
    if ratio < TIGHT_BELOW:
        return GRADE_TIGHT
    if ratio > WIDE_ABOVE:
        return GRADE_WIDE
    return GRADE_PLAUSIBLE


def _band_value(band: BandSet, p: float) -> float:
    """Pick the requested quantile out of a band set.

    Only the three quantiles the wave scan already computed are available; any
    other ``p`` falls back to P80 with no pretence of interpolation, because
    interpolating between P80 and P95 would imply a precision the segment count
    does not support.
    """
    if abs(p - 0.95) < 1e-9:
        return band.p95
    if abs(p - 1.0) < 1e-9:
        return band.high
    if abs(p - 0.0) < 1e-9:
        return band.low
    return band.p80


def trim_years(bars: Sequence[Bar], years: int = DEFAULT_YEARS) -> List[Bar]:
    """Keep only the last ``years`` of bars.

    The cutoff is computed from the **last** bar rather than "today", so a
    stale history file gives a complete window instead of a short one, and a
    test fixture does not depend on the wall clock.

    The year is subtracted as a calendar year, not as ``365 * years`` days:
    a leap year inside the window would otherwise pull the cutoff one day
    later and drop a bar that belongs in it.
    """
    if not bars:
        return []
    last = bars[-1].time_label
    try:
        last_dt = datetime.strptime(last, "%Y-%m-%dT%H:%M")
    except ValueError:
        return list(bars)
    try:
        cutoff = last_dt.replace(year=last_dt.year - years)
    except ValueError:  # 29 February -> fall back one day
        cutoff = last_dt.replace(year=last_dt.year - years, day=28)
    cutoff_label = cutoff.strftime("%Y-%m-%dT%H:%M")
    return [b for b in bars if b.time_label >= cutoff_label]


def score_symbol(
    symbol: str,
    step_pips: Optional[float],
    scan: WaveScan,
    p_quantile: float = 0.80,
) -> FitScore:
    """Score one symbol from an already-computed :class:`WaveScan`.

    Taking the scan rather than the bars keeps the expensive part (ZigZag over
    every window) outside, so scoring many symbols against one scan is cheap.
    """
    band = scan.median_bands()
    if band is None or step_pips is None or step_pips <= 0:
        return FitScore(
            symbol=symbol,
            step_pips=step_pips,
            band_pips=None,
            ratio=None,
            grade=GRADE_UNKNOWN,
        )
    band_pips = _band_value(band, p_quantile)
    ratio = step_pips / band_pips if band_pips > 0 else None
    return FitScore(
        symbol=symbol,
        step_pips=step_pips,
        band_pips=band_pips,
        ratio=ratio,
        grade=grade_ratio(ratio),
        band_label=f"P{int(p_quantile * 100)}",
        segments=band.segments,
    )


def score_grid(
    symbol: str,
    step_pips: Optional[float],
    bars: Sequence[Bar],
    pip_size: float,
    years: int = DEFAULT_YEARS,
    p_quantile: float = 0.80,
    window_bars: int = 1024,
    step_bars: int = 25,
    merge_ratio: float = DEFAULT_MERGE_RATIO,
) -> FitScore:
    """Convenience path: trim to ``years``, scan the bands, score the grid."""
    trimmed = trim_years(bars, years)
    scan = scan_waves(
        trimmed,
        symbol=symbol,
        pip_size=pip_size,
        window_bars=window_bars,
        step_bars=step_bars,
        merge_ratio=merge_ratio,
    )
    return score_symbol(symbol, step_pips, scan, p_quantile=p_quantile)


def report(scores: Sequence[FitScore], years: int = DEFAULT_YEARS) -> FitReport:
    return FitReport(years=years, scores=list(scores))
