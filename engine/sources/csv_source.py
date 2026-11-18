"""Offline CSV bar source (used for parity work and multi-broker comparisons).

Brokers are never mixed: every export carries its own ``broker``/``server``
label and is written to its own ``waves.csv`` (requirement v0.2 §5).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..bar import Bar, load_bars_csv, pip_size


@dataclass(frozen=True)
class CsvMeta:
    symbol: str
    digits: int
    point: float
    server: str
    account: int
    broker_company: str

    @property
    def pip(self) -> float:
        return pip_size(self.point, self.digits)


def load_meta_sidecar(path: str) -> Dict[str, str]:
    """Read a ``key,value`` sidecar (as written by the MQL dumper)."""
    out: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8-sig", newline="") as fh:
            for line in fh:
                parts = line.rstrip("\r\n").split(",")
                if len(parts) >= 2:
                    out[parts[0].strip().lower()] = parts[1].strip()
    except FileNotFoundError:
        pass
    return out


def fetch_bars(
    csv_path: str,
    start_label: Optional[str] = None,
    end_label: Optional[str] = None,
    meta_path: Optional[str] = None,
    digits: int = 5,
    point: float = 1e-5,
) -> Tuple[List[Bar], CsvMeta]:
    bars = load_bars_csv(csv_path)
    if start_label:
        bars = [b for b in bars if b.time_label >= start_label]
    if end_label:
        bars = [b for b in bars if b.time_label <= end_label]
    meta: Dict[str, str] = load_meta_sidecar(meta_path) if meta_path else {}
    d = int(meta.get("digits", digits))
    p = float(meta.get("point", point))
    return bars, CsvMeta(
        symbol=meta.get("symbol", ""),
        digits=d,
        point=p,
        server=meta.get("server", ""),
        account=int(meta.get("account", "0") or 0),
        broker_company=meta.get("company", ""),
    )
