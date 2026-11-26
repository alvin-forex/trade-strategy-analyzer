"""MT4 ``.hst`` history reader.

The layout is fixed and was re-measured rather than assumed:

    header            148 bytes
    record             60 bytes
        +0   int32     Unix seconds  (int32, so 2038 is the ceiling)
        +8   float64   open
        +16  float64   high
        +24  float64   low
        +32  float64   close
        +40  int32     tick volume
        +48  int32     spread in points

Volume is the field that bites. Reading ``+40`` as float64 yields denormals
such as ``1.1685e-320`` -- numbers that look like broken data but are really
the two int32 halves of a plausible count reinterpreted as a double. On
``Alpari-Pro.ECN-Demo/EURUSD60.hst`` the int32 read gives 2365 where the
float64 read gives 1.1685e-320; 2365 is the answer.

Two consequences for callers: the oldest bar of a file is the first record
(the file is chronological ascending), and a truncated tail is possible while a
terminal is writing, so a partial trailing record is dropped rather than
raising.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from ..bar import Bar

HEADER_BYTES = 148
RECORD_BYTES = 60
TIME_FMT = "<i"
OHLC_FMT = "<4d"
VOL_FMT = "<i"
SPREAD_FMT = "<i"
# MT4 header fields, verified against the real Alpari-Pro.ECN-Demo files:
#   symbol char[16] @68, period int32 @80, digits int32 @84.
SYMBOL_OFFSET = 68
SYMBOL_BYTES = 16
PERIOD_OFFSET = 80
DIGITS_OFFSET = 84


@dataclass(frozen=True)
class HstHeader:
    """Static metadata from the 148-byte header (authoritative over filenames)."""

    symbol: str
    period: int       # minutes: 1 = M1, 60 = H1, 240 = H4, 1440 = D1
    digits: int       # decimal places of every price in this file

    @property
    def scale(self) -> int:
        return 10 ** self.digits


def read_hst_header(path: str) -> Optional[HstHeader]:
    """Read symbol/period/digits from ``path``; ``None`` if too short.

    The filename is not trustworthy: ``<SYM>1.hst`` can hold any timeframe, and
    broker digit counts differ from the obvious JPY/XAU heuristics (fiat is
    often 5 here, XAUJPY is 0). Always source the scale from this header.
    """
    with open(path, "rb") as fh:
        blob = fh.read(HEADER_BYTES)
    if len(blob) < HEADER_BYTES:
        return None
    raw = blob[SYMBOL_OFFSET:SYMBOL_OFFSET + SYMBOL_BYTES]
    symbol = raw.split(b"\x00", 1)[0].decode("ascii", errors="replace").strip()
    period = struct.unpack_from("<i", blob, PERIOD_OFFSET)[0]
    digits = struct.unpack_from("<i", blob, DIGITS_OFFSET)[0]
    return HstHeader(symbol=symbol, period=period, digits=digits)


@dataclass(frozen=True)
class HstRecord:
    """One bar as stored, before any label formatting."""

    epoch: int
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    spread_points: int


def read_hst(path: str) -> List[HstRecord]:
    """Read every complete record in ``path``.

    A trailing partial record is discarded, not an error: terminals append while
    writing and a half-written 60-byte slot is normal.
    """
    with open(path, "rb") as fh:
        blob = fh.read()
    if len(blob) < HEADER_BYTES:
        return []

    body = len(blob) - HEADER_BYTES
    n = body // RECORD_BYTES

    out: List[HstRecord] = []
    off = HEADER_BYTES
    for _ in range(n):
        epoch = struct.unpack_from(TIME_FMT, blob, off)[0]
        o, h, l, c = struct.unpack_from(OHLC_FMT, blob, off + 8)
        vol = struct.unpack_from(VOL_FMT, blob, off + 40)[0]
        spread = struct.unpack_from(SPREAD_FMT, blob, off + 48)[0]
        out.append(HstRecord(epoch, o, h, l, c, vol, spread))
        off += RECORD_BYTES
    return out


def _label(epoch: int) -> str:
    """Server-time label, no timezone shift applied.

    ``.hst`` stamps are already server time; converting through UTC would slide
    every bar by the broker offset and break the join against MT4's own display.
    """
    return datetime.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M")


def to_bars(records: List[HstRecord]) -> List[Bar]:
    """Convert to :class:`Bar` so the ZigZag port can consume it directly."""
    return [
        Bar(
            time_label=_label(r.epoch),
            open=r.open,
            high=r.high,
            low=r.low,
            close=r.close,
            tick_volume=r.tick_volume,
        )
        for r in records
    ]


def load_hst_bars(path: str) -> List[Bar]:
    """Convenience: file path straight to :class:`Bar` list."""
    return to_bars(read_hst(path))


def sanity_check(records: List[HstRecord]) -> Tuple[bool, str]:
    """Cheap structural check used by tests and by the CLI's pre-flight.

    Returns ``(ok, reason)``. Only invariants that must hold for any real file
    are tested -- ``low <= open/close <= high`` and non-negative volume -- so a
    legitimate gap or a weekend jump is not reported as corruption.
    """
    if not records:
        return False, "no records"
    prev = None
    for i, r in enumerate(records):
        if r.low > r.high:
            return False, f"record {i}: low {r.low} > high {r.high}"
        lo = min(r.open, r.close)
        hi = max(r.open, r.close)
        if lo < r.low - 1e-12 or hi > r.high + 1e-12:
            return False, f"record {i}: open/close outside low/high"
        if r.tick_volume < 0:
            return False, f"record {i}: negative volume {r.tick_volume}"
        if prev is not None and r.epoch < prev:
            return False, f"record {i}: time goes backwards ({r.epoch} < {prev})"
        prev = r.epoch
    return True, f"{len(records)} records ok"
