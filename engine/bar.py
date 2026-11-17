"""Bar container and CSV loading.

A ``Bar`` is one OHLC observation. ``time_label`` is the *server* time label as
MT4/MT5 display it (no timezone attached on purpose: the label is the identity
that must round-trip into ``waves.csv``).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class Bar:
    time_label: str  # "YYYY-MM-DDTHH:MM", server time label
    open: float
    high: float
    low: float
    close: float
    tick_volume: int = 0


def _norm_time(raw: str) -> str:
    """Accept 'YYYY.MM.DD HH:MM' or 'YYYY-MM-DD HH:MM' and emit ISO-ish label."""
    s = raw.strip().replace(".", "-")
    if " " in s:
        date, _, clock = s.partition(" ")
    else:
        date, clock = s, "00:00"
    return f"{date}T{clock[:5]}"


def load_bars_csv(path: str) -> List[Bar]:
    """Load bars from a CSV with a header row.

    Recognised headers (case-insensitive): ``time``, ``open``, ``high``,
    ``low``, ``close``, ``volume`` / ``tick_volume``. Rows are sorted
    chronologically ascending; duplicate timestamps keep the last occurrence.
    """
    rows = []
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        field_map = {name.strip().lower(): name for name in (reader.fieldnames or [])}
        need = ("time", "open", "high", "low", "close")
        missing = [k for k in need if k not in field_map]
        if missing:
            raise ValueError(f"{path}: missing columns {missing}")
        vol_key = field_map.get("volume") or field_map.get("tick_volume")
        for raw in reader:
            t = _norm_time(raw[field_map["time"]])
            v = raw.get(vol_key, "0") if vol_key else "0"
            rows.append(
                Bar(
                    time_label=t,
                    open=float(raw[field_map["open"]]),
                    high=float(raw[field_map["high"]]),
                    low=float(raw[field_map["low"]]),
                    close=float(raw[field_map["close"]]),
                    tick_volume=int(float(v or 0)),
                )
            )
    rows.sort(key=lambda b: b.time_label)
    dedup: List[Bar] = []
    for b in rows:
        if dedup and dedup[-1].time_label == b.time_label:
            dedup[-1] = b
        else:
            dedup.append(b)
    return dedup


def slice_window(bars: Sequence[Bar], start_label: str, end_label: str) -> List[Bar]:
    """Inclusive on both ends: start <= t <= end."""
    return [b for b in bars if start_label <= b.time_label <= end_label]


def pip_size(point: float, digits: int) -> float:
    """Pip size from symbol point/digits.

    digits in {3, 5} -> fractional pip pricing, 1 pip = 10 points.
    digits in {2, 4} -> 1 pip = 1 point (XAU-style / whole-pip quoting).
    """
    if digits in (3, 5):
        return point * 10.0
    return point
