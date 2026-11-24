"""M1 single-source aggregation: every higher timeframe is derived from M1.

Architecture decision (owner 2026-11-23 22:32, OC dispatch 2026-11-23 22:55):
M1 is the only data source. M5/M15/M30/H1/H4/D1 are *computed* from M1 instead
of being collected independently, because independently collected timeframes
disagree at bar edges and every disagreement becomes an unexplainable parity
delta later.

Why the bucket boundary is a plain epoch floor
----------------------------------------------
MT4/MT5 store bar time as seconds since the epoch *in server time* (see
``engine/sources/mt5_source.py``). Server midnight is therefore exactly
``epoch % 86400 == 0``, so flooring an M1 epoch to a multiple of
``minutes * 60`` lands on the same boundary the chart uses -- no timezone
arithmetic, no DST special case, no broker-offset table. The one thing this
does *not* do is reproduce a broker whose day boundary is not 00:00 server
time; that broker is not in use here and would have to be handled explicitly
rather than guessed.

Partial buckets
---------------
The first and last bucket of any M1 file are usually incomplete because the
file starts or ends mid-bucket. A silently aggregated partial bucket produces a
low/high that is too narrow and a close that is not the period close, which is
exactly the kind of number that looks plausible and is wrong. ``aggregate()``
therefore records the M1 count of every bucket in ``counts`` and callers that
need only trustworthy bars should drop buckets whose count is below the expected
count (see :func:`usable_buckets`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Sequence, Tuple

from .bar import Bar

#: Minutes per timeframe. Only the set the owner asked for is listed; adding a
#: timeframe means adding a boundary rule here, not a new data collection path.
TIMEFRAME_MINUTES: Dict[str, int] = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
}


def timeframe_minutes(tf: str) -> int:
    """Minutes for ``tf`` (``M5``/``H1``/``D1``/...). Raises for anything else."""
    try:
        return TIMEFRAME_MINUTES[tf.upper()]
    except KeyError:
        raise ValueError(
            f"unsupported timeframe {tf!r}; known: {sorted(TIMEFRAME_MINUTES)}"
        ) from None


def bucket_epoch(epoch: int, minutes: int) -> int:
    """Floor ``epoch`` to the start of its ``minutes``-long bucket."""
    if minutes <= 0:
        raise ValueError("minutes must be positive")
    step = minutes * 60
    return epoch - (epoch % step)


def bucket_label(epoch: int) -> str:
    """Server-time label for a bucket start, matching ``Bar.time_label``."""
    return datetime.fromtimestamp(epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M")


@dataclass(frozen=True)
class Aggregation:
    """Aggregated bars plus the per-bucket M1 count used to detect partials."""

    tf: str
    bars: List[Bar]
    #: bucket epoch -> number of M1 records folded into it
    counts: Dict[int, int]

    @property
    def expected(self) -> int:
        """M1 records a complete bucket normally holds for this timeframe."""
        return timeframe_minutes(self.tf)


def aggregate(m1: Sequence[Bar], tf: str) -> Aggregation:
    """Fold M1 ``Bar`` records into ``tf`` bars.

    ``Bar.time_label`` carries the server-time label, and ``Bar`` has no epoch
    field, so the epoch is recovered by parsing the label. Parsing is safe here
    because every producer in this repo writes the same ``YYYY-MM-DDTHH:MM``
    label (``engine/bar.py`` documents the label as the identity).

    Rules, in the order MT4 applies them:
      * open   = open of the first M1 record in the bucket
      * high   = max of the M1 highs
      * low    = min of the M1 lows
      * close  = close of the last M1 record in the bucket
      * volume = sum of the M1 tick volumes
    Records are folded in label order, so a file that is not strictly ascending
    still produces the correct first-open/last-close.
    """
    minutes = timeframe_minutes(tf)
    if minutes == 1:
        order = sorted(m1, key=lambda b: b.time_label)
        counts = {_label_epoch(b.time_label): 1 for b in order}
        return Aggregation(tf="M1", bars=list(order), counts=counts)

    folded: Dict[int, List] = {}
    order = sorted(m1, key=lambda b: b.time_label)
    for b in order:
        key = bucket_epoch(_label_epoch(b.time_label), minutes)
        g = folded.get(key)
        if g is None:
            folded[key] = [b.open, b.high, b.low, b.close, b.tick_volume, 1]
        else:
            if b.high > g[1]:
                g[1] = b.high
            if b.low < g[2]:
                g[2] = b.low
            g[3] = b.close
            g[4] += b.tick_volume
            g[5] += 1

    bars: List[Bar] = []
    counts: Dict[int, int] = {}
    for key in sorted(folded):
        o, h, l, c, v, n = folded[key]
        bars.append(
            Bar(
                time_label=bucket_label(key),
                open=o,
                high=h,
                low=l,
                close=c,
                tick_volume=v,
            )
        )
        counts[key] = n
    return Aggregation(tf=tf.upper(), bars=bars, counts=counts)


def usable_buckets(agg: Aggregation) -> List[Bar]:
    """Bars whose bucket is complete enough to trust.

    A weekend or holiday bucket legitimately holds fewer M1 records, so a
    strict ``== expected`` test would throw away real bars. The rule used here
    is the one that matters for correctness: a bucket is dropped when it sits at
    the edge of the file (first or last bucket) *and* is short. Interior short
    buckets are kept and flagged by the caller through ``counts`` if wanted.
    """
    if not agg.bars:
        return []
    out: List[Bar] = []
    last = len(agg.bars) - 1
    for i, bar in enumerate(agg.bars):
        key = _label_epoch(bar.time_label)
        n = agg.counts.get(key, 0)
        if i in (0, last) and n < agg.expected:
            continue
        out.append(bar)
    return out


def _label_epoch(label: str) -> int:
    """Inverse of ``bucket_label``: ``YYYY-MM-DDTHH:MM`` -> server epoch seconds."""
    parsed = datetime.strptime(label, "%Y-%m-%dT%H:%M").replace(tzinfo=timezone.utc)
    return int(parsed.timestamp())


def aggregate_hst(path: str, tf: str) -> Aggregation:
    """Read an MT4 ``.hst`` M1 file and aggregate it to ``tf``.

    Kept as a thin wrapper so the offline path (``engine/martingale/hst_reader``)
    and the live path (``engine/sources/mt5_source``) share one aggregation
    implementation instead of each growing its own.
    """
    from .martingale.hst_reader import read_hst

    records = read_hst(path)
    bars = [
        Bar(
            time_label=datetime.fromtimestamp(r.epoch, timezone.utc).strftime("%Y-%m-%dT%H:%M"),
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            tick_volume=r.tick_volume,
        )
        for r in records
    ]
    return aggregate(bars, tf)


def cross_check(
    agg: Aggregation, reference: Iterable[Bar], tol: float = 1e-9
) -> Tuple[int, int, List[Tuple[str, str]]]:
    """Compare ``agg`` against independently collected ``reference`` bars.

    Returns ``(common, exact, mismatches)`` where ``mismatches`` lists
    ``(time_label, field)`` for the first differing field of each unmatched
    bucket. Only buckets present in both inputs are compared, so a shorter M1
    window does not masquerade as an aggregation error.
    """
    ref_by_label = {b.time_label: b for b in reference}
    exact = 0
    common = 0
    mism: List[Tuple[str, str]] = []
    for bar in agg.bars:
        ref = ref_by_label.get(bar.time_label)
        if ref is None:
            continue
        common += 1
        bad = None
        for field in ("open", "high", "low", "close"):
            if abs(getattr(bar, field) - getattr(ref, field)) > tol:
                bad = field
                break
        if bad is None:
            exact += 1
        else:
            mism.append((bar.time_label, bad))
    return common, exact, mism
