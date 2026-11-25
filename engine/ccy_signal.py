"""CCY-power signal engine — pure functions, no I/O, no MT5 dependency.

Scope (OC ruling 2026-11-24 15:05 §二, five gaps cleared):

  * primary signal  = fake-breakout fade with fast/slow power agreement.
    Research verdict: +0.272R, t=8.27, n=1,698 (§2 of
    ``docs/admin/EXTRACcyPOWER_RESEARCH_20261118.md``). This is the only
    variant with positive expectancy, so it is the default.
  * alternative     = residual quantile (STRATEGY v1 §2 layer 1):
    ``residual = actual price change - power-implied change``.

Entry modes (OC 2026-11-24 14:00 §三, input ``InpEntryMode``):

  * ``MODE_CONFIRM`` — after the extreme quantile, wait ``revert_bars`` bars
    for the residual to start reverting, then enter once.
  * ``MODE_FORWARD`` — anchor at the extreme, ladder one layer every
    ``step_bars`` bars while the residual has NOT reverted; bounded by
    ``max_layers``. This is a counter-trend early entry, so the caller must
    keep the three risk guards armed (OC red line).

NO LOOKAHEAD: every rolling statistic (ATR, quantile band) is computed from
strictly earlier bars. ``test_ccy_signal`` asserts this directly rather than
trusting the code to stay honest.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

#: Fake-breakout tolerance as a multiple of ATR (research §2 uses 0.10).
DEFAULT_ATR_TOL = 0.10

#: Pivot half-width: a swing high/low must dominate ``k`` bars either side.
DEFAULT_PIVOT_K = 3

#: How far past a pivot to look for the reclaim (research uses 200 bars).
DEFAULT_LOOKBACK = 200


# --------------------------------------------------------------------------
# volatility
# --------------------------------------------------------------------------

def true_ranges(bars: Sequence) -> List[Optional[float]]:
    """True range per bar; the first bar has no previous close (``None``)."""
    out: List[Optional[float]] = []
    for i, b in enumerate(bars):
        if i == 0:
            out.append(None)
            continue
        prev_close = bars[i - 1].close
        out.append(max(b.high - b.low, abs(b.high - prev_close), abs(b.low - prev_close)))
    return out


def atr(bars: Sequence, period: int = 14) -> List[Optional[float]]:
    """Wilder ATR with ``period`` bars of warm-up (``None`` until then).

    The value at index ``i`` uses bars ``0..i`` inclusive, so it is safe to
    read at ``i`` when deciding an entry on bar ``i`` (the bar is closed).
    """
    if period < 1:
        raise ValueError("period must be >= 1")
    tr = true_ranges(bars)
    out: List[Optional[float]] = [None] * len(bars)
    # First ATR is the simple mean of the first `period` true ranges.
    seed_idx = period  # tr[0] is None, so bars 1..period give `period` values
    if len(bars) <= seed_idx:
        return out
    seed = [x for x in tr[1 : seed_idx + 1] if x is not None]
    if len(seed) < period:
        return out
    prev = sum(seed) / period
    out[seed_idx] = prev
    for i in range(seed_idx + 1, len(bars)):
        t = tr[i]
        if t is None:
            out[i] = prev
            continue
        prev = (prev * (period - 1) + t) / period
        out[i] = prev
    return out


# --------------------------------------------------------------------------
# pivots and fake breakouts
# --------------------------------------------------------------------------

def pivots(bars: Sequence, k: int = DEFAULT_PIVOT_K) -> List[tuple]:
    """Swing highs/lows as ``(index, level, 'R'|'S')``.

    A bar qualifies only if it dominates ``k`` neighbours on both sides, so the
    confirmation is inherently ``k`` bars late — the returned index is the
    pivot bar itself, and callers must only act from ``index + k`` onward.
    """
    if k < 1:
        raise ValueError("k must be >= 1")
    out = []
    for i in range(k, len(bars) - k):
        window = bars[i - k : i + k + 1]
        if bars[i].high == max(b.high for b in window):
            out.append((i, bars[i].high, "R"))
        elif bars[i].low == min(b.low for b in window):
            out.append((i, bars[i].low, "S"))
    return out


def fake_breaks(
    bars: Sequence,
    atr_series: Sequence[Optional[float]],
    k: int = DEFAULT_PIVOT_K,
    atr_tol: float = DEFAULT_ATR_TOL,
    lookback: int = DEFAULT_LOOKBACK,
) -> List[tuple]:
    """Fake breakouts: ``(entry_index, level, 'R'|'S')``.

    A level is *faked* when price trades beyond it by more than
    ``atr_tol * ATR`` and then closes back on the original side. The trade
    direction is the fade: a faked resistance ('R') means short, a faked
    support ('S') means long.

    ``entry_index`` is the bar on which the reclaim is observed, i.e. the
    signal is actionable at that bar's close (enter on the next open).
    """
    out = []
    for p, level, kind in pivots(bars, k):
        # Confirmation of the pivot is only available k bars later.
        for j in range(p + k, min(p + lookback, len(bars) - 1)):
            a = atr_series[j]
            if a is None:
                continue
            tol = atr_tol * a
            if kind == "R" and bars[j].high > level + tol and bars[j].close < level:
                out.append((j, level, "R"))
                break
            if kind == "S" and bars[j].low < level - tol and bars[j].close > level:
                out.append((j, level, "S"))
                break
    return out


def power_agrees(fast_diff: float, slow_diff: float, direction: int) -> bool:
    """True when both power spreads point the same way as ``direction``.

    ``direction`` is ``+1`` for long, ``-1`` for short. Mirrors
    ``exp_allpairs2.py``: the filter is only ever "same sign on both".
    """
    return (fast_diff > 0) == (direction > 0) and (slow_diff > 0) == (direction > 0)


# --------------------------------------------------------------------------
# residual / quantile band
# --------------------------------------------------------------------------

def residuals(
    bars: Sequence,
    power_by_time: dict,
    slope_b: float,
    base_ccy: str,
    quote_ccy: str,
) -> List[Optional[float]]:
    """Residual = actual price change − power-implied change.

    ``power_by_time`` maps ``bar.time_label`` to a mapping of currency to power
    value. ``slope_b`` is the fitted constant (OC 2026-11-24 18:15: a
    ``const double``, deliberately not an input, to keep the optimiser away
    from a single scale parameter).

    Returns ``None`` for any bar where the current or previous power spread is
    unavailable, so gaps never masquerade as zero residual.
    """
    out: List[Optional[float]] = []
    prev_price: Optional[float] = None
    prev_spread: Optional[float] = None
    for b in bars:
        p = power_by_time.get(b.time_label)
        spread = None
        if p and base_ccy in p and quote_ccy in p:
            spread = float(p[base_ccy]) - float(p[quote_ccy])
        if prev_price is None or prev_spread is None or spread is None:
            out.append(None)
        else:
            out.append((b.close - prev_price) - slope_b * (spread - prev_spread))
        prev_price = b.close
        prev_spread = spread
    return out


def rolling_quantile(
    values: Sequence[Optional[float]], q: float, window: int
) -> List[Optional[float]]:
    """Quantile of the ``window`` bars **before** each index (no lookahead).

    Index ``i`` reads ``values[i-window : i]`` — never ``values[i]`` — so the
    band at ``i`` is knowable at bar ``i``'s close. ``None`` entries inside the
    window are dropped; if fewer than two usable values remain, the result is
    ``None``.
    """
    if not 0.0 <= q <= 1.0:
        raise ValueError("q must be within [0, 1]")
    if window < 1:
        raise ValueError("window must be >= 1")
    out: List[Optional[float]] = []
    for i in range(len(values)):
        lo = max(0, i - window)
        usable = sorted(v for v in values[lo:i] if v is not None)
        out.append(_quantile_sorted(usable, q) if len(usable) >= 2 else None)
    return out


def _quantile_sorted(sorted_vals: List[float], q: float) -> float:
    """Linear-interpolation quantile on an already-sorted list."""
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1.0 - frac) + sorted_vals[hi] * frac


# --------------------------------------------------------------------------
# entry plans
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Layer:
    """One position to open."""

    index: int  # bar index whose close produced the decision
    direction: int  # +1 long, -1 short
    layer: int  # 1-based ladder position


def _direction_at(
    residual_series: Sequence[Optional[float]],
    low_band: Sequence[Optional[float]],
    high_band: Sequence[Optional[float]],
    i: int,
) -> int:
    """+1 when bar ``i`` sits in the bottom band, -1 in the top band, else 0."""
    r, hi, lo = residual_series[i], high_band[i], low_band[i]
    if r is None or hi is None or lo is None:
        return 0
    if r >= hi:
        return -1
    if r <= lo:
        return 1
    return 0


def plan_confirm(
    bars: Sequence,
    residual_series: Sequence[Optional[float]],
    low_band: Sequence[Optional[float]],
    high_band: Sequence[Optional[float]],
    revert_bars: int = 2,
    max_entries: int = 1000,
) -> List[Layer]:
    """``MODE_CONFIRM``: enter once, after the residual reverts off the extreme.

    A short setup is anchored when the residual sits in the *top* band
    (``>= high_band``) and armed for a long when it sits in the *bottom* band
    (``<= low_band``) — price overshot its power-implied path, so the fade is
    back toward the implied level. "Revert" means the residual has moved back
    inside the band on the bar ``revert_bars`` after the anchor.

    After an entry the engine re-arms only once the residual actually leaves
    the band, so one long excursion cannot emit the same trade twice.
    """
    if revert_bars < 0:
        raise ValueError("revert_bars must be >= 0")
    out: List[Layer] = []
    i = 0
    n = len(bars)
    while i < n:
        direction = _direction_at(residual_series, low_band, high_band, i)
        if direction == 0:
            i += 1
            continue
        j = i + revert_bars
        if j >= n:
            break
        rj = residual_series[j]
        if rj is None:
            i += 1
            continue
        hi, lo = high_band[i], low_band[i]
        reverted = rj < hi if direction == -1 else rj > lo
        if not reverted:
            i += 1
            continue
        out.append(Layer(index=j, direction=direction, layer=1))
        if len(out) >= max_entries:
            break
        # Re-arm only after the residual has left the band, so the next anchor
        # needs a fresh excursion rather than re-reading the same one.
        i = j + 1
        while i < n and _direction_at(residual_series, low_band, high_band, i) != 0:
            i += 1
    return out


def plan_forward(
    bars: Sequence,
    residual_series: Sequence[Optional[float]],
    low_band: Sequence[Optional[float]],
    high_band: Sequence[Optional[float]],
    step_bars: int = 1,
    max_layers: int = 1,
) -> List[Layer]:
    """``MODE_FORWARD``: anchor at the extreme, ladder while it has not reverted.

    A *ladder* is one maximal run of same-direction extreme bars. Inside it,
    layers are placed at the anchor and every ``step_bars`` bars after, stopping
    at ``max_layers`` or as soon as the residual returns inside the band —
    "殘差回返即停注" and "``InpMaxLayers`` 用盡即斷，唔准無限加" (OC
    2026-11-24 14:00 §三). The counters reset per ladder, so a later excursion
    is a fresh ladder rather than an extension of the previous one.
    """
    if step_bars < 1:
        raise ValueError("step_bars must be >= 1")
    if max_layers < 1:
        raise ValueError("max_layers must be >= 1")
    out: List[Layer] = []
    n = len(bars)
    i = 0
    while i < n:
        direction = _direction_at(residual_series, low_band, high_band, i)
        if direction == 0:
            i += 1
            continue
        anchor = i
        layer = 0
        j = anchor
        while j < n and layer < max_layers:
            if residual_series[j] is None:
                # A gap is not evidence of reversion; step over it.
                j += step_bars
                continue
            if _direction_at(residual_series, low_band, high_band, j) != direction:
                break  # back inside the band -> ladder ends
            layer += 1
            out.append(Layer(index=j, direction=direction, layer=layer))
            j += step_bars
        # Skip to the end of this extreme region so it is not re-read.
        i = max(anchor + 1, j)
        while i < n and _direction_at(residual_series, low_band, high_band, i) == direction:
            i += 1
    return out



# --------------------------------------------------------------------------
# guard check (OC red line)
# --------------------------------------------------------------------------

def forward_ladder_allowed(dd_guard: bool, sym_guard: bool, news_guard: bool) -> bool:
    """``MODE_FORWARD`` may only run with the three risk guards armed.

    OC 2026-11-24 14:00 §三 red line: the forward ladder is a counter-trend
    early entry, so it must be bound to the drawdown, per-symbol and news
    guards. The EA must refuse to start rather than rely on a backtest to
    reveal the omission.
    """
    return bool(dd_guard and sym_guard and news_guard)
