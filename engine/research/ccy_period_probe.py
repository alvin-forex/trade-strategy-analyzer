"""CCY Power `Period` semantics probe — H4_1..H4_9 family.

All nine files share ONE time window (2025-01-21 → 2026-05-21), ONE timeframe
(H4), and differ ONLY in the `Period` suffix, so the difference between them is
a pure function of Period. This isolates the smoothing operator from feed/broker
noise (which already defeated every earlier fit attempt).

Read-only. Never writes into exchange/ or docs/.
"""
from __future__ import annotations

import datetime as _dt
import struct
from dataclasses import dataclass

HEADER_INT = "<i"
RECORD = struct.Struct("<q9d")
RECORD_BYTES = RECORD.size  # 80


@dataclass(frozen=True)
class DatFile:
    path: str
    codes: tuple[str, ...]
    stamps: tuple[int, ...]
    # rows[i] is a 9-tuple in `codes` order
    rows: tuple[tuple[float, ...], ...]

    def column(self, ccy: str) -> list[float]:
        j = self.codes.index(ccy)
        return [r[j] for r in self.rows]


def read_dat(path: str) -> DatFile:
    with open(path, "rb") as fh:
        blob = fh.read()
    n = struct.unpack_from(HEADER_INT, blob, 0)[0]
    if not 1 <= n <= 32:
        raise ValueError(f"{path}: implausible header count {n}")
    codes = tuple(
        blob[4 + 4 * i : 8 + 4 * i].decode("latin1").rstrip("\x00") for i in range(n)
    )
    off = 4 + 4 * n
    stamps: list[int] = []
    rows: list[tuple[float, ...]] = []
    while off + RECORD_BYTES <= len(blob):
        t, *vals = RECORD.unpack_from(blob, off)
        stamps.append(t)
        rows.append(tuple(vals))
        off += RECORD_BYTES
    if off != len(blob):
        raise ValueError(f"{path}: {len(blob) - off} trailing bytes")
    return DatFile(path, codes, tuple(stamps), tuple(rows))


def utc(ts: int) -> _dt.datetime:
    return _dt.datetime.fromtimestamp(ts, _dt.timezone.utc)


def mean_abs_step(v: list[float]) -> float:
    d = [abs(v[i] - v[i - 1]) for i in range(1, len(v))]
    return sum(d) / len(d)


def stdev(v: list[float]) -> float:
    mu = sum(v) / len(v)
    return (sum((x - mu) ** 2 for x in v) / len(v)) ** 0.5


# --------------------------------------------------------------------------- #
# Lattice analysis
# --------------------------------------------------------------------------- #
def lattice_denominator(values: list[float], cap: int = 400) -> int | None:
    """Smallest D such that every value is an exact multiple of 1/D."""
    for d in range(1, cap + 1):
        if all(abs(v * d - round(v * d)) < 1e-9 for v in values):
            return d
    return None


def reduced_denominator_counts(values: list[float]) -> dict[int, int]:
    """Histogram of each value's *reduced* denominator (after gcd cancellation)."""
    from collections import Counter
    from math import gcd

    d = lattice_denominator(values)
    if d is None:
        return {}
    counts: Counter[int] = Counter()
    for v in values:
        n = round(v * d)
        counts[d // (gcd(n, d) or 1)] += 1
    return dict(counts)


def acf1(values: list[float]) -> float:
    n = len(values)
    mu = sum(values) / n
    den = sum((x - mu) ** 2 for x in values)
    if den == 0:
        return 0.0
    return sum((values[i] - mu) * (values[i - 1] - mu) for i in range(1, n)) / den
