"""waves.csv contract: write, read, hash.

Field contract is fixed by requirement v0.2 §7 (A1):
``idx,startTime,endTime,bars,amplitudePips`` — five columns, that order, no more.
The ten provenance fields (§4) go into the sidecar ``*.meta.json`` instead so
the CSV stays byte-stable across runs.
"""

from __future__ import annotations

import hashlib
import json
import os
from typing import Iterable, List, Sequence

from .merge import Wave

HEADER = ("idx", "startTime", "endTime", "bars", "amplitudePips")


def write_waves_csv(path: str, waves: Sequence[Wave]) -> str:
    """Write the CSV and return its sha256. Deterministic: LF endings, no BOM."""
    lines = [",".join(HEADER)]
    for w in waves:
        lines.append(
            f"{w.idx},{w.start_time},{w.end_time},{w.bars},{w.amplitude_pips:.2f}"
        )
    body = "\n".join(lines) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def read_waves_csv(path: str) -> List[dict]:
    import csv

    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_meta(path: str, meta: dict) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False, sort_keys=True)
        fh.write("\n")


def default_meta_path(out_path: str) -> str:
    root, _ = os.path.splitext(out_path)
    return root + ".meta.json"


def build_meta(
    *,
    broker: str,
    server: str,
    symbol: str,
    symbol_digits: int,
    tf: str,
    window_from: str,
    window_to: str,
    params: dict,
    engine_version: str,
    calc_method: str,
    server_utc_offset: float,
    time_basis: str,
    bar_count: int,
    wave_count: int,
    first_pivot_idx: int,
    last_pivot_idx: int,
    covered_bars: int,
    csv_sha256: str,
    total_bars: int,
    extra: dict | None = None,
) -> dict:
    meta = {
        "broker": broker,
        "server": server,
        "symbol": symbol,
        "symbol_digits": symbol_digits,
        "tf": tf,
        "window_from": window_from,
        "window_to": window_to,
        "params": params,
        "engine_version": engine_version,
        "calc_method": calc_method,
        "server_utc_offset": server_utc_offset,
        "time_basis": time_basis,
        "bar_count": bar_count,
        "wave_count": wave_count,
        "first_pivot_idx": first_pivot_idx,
        "last_pivot_idx": last_pivot_idx,
        "covered_bars": covered_bars,
        "total_bars": total_bars,
        "csv_sha256": csv_sha256,
    }
    if extra:
        meta.update(extra)
    return meta
