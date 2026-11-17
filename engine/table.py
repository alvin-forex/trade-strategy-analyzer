"""Volatility table export (stage A2).

Produces the normalised table that the website consumes, in the shape required
by requirement v0.2 §13::

    symbol, year, timeframe, band, lowerPips, upperPips,
    scannerVersion, sourceFileHash, datasetVersion

The band names are printed **verbatim** as ``80% Range`` / ``15% Range`` /
``5% Range`` and must never be relabelled as P80 / P95 / Pmax (§13), because the
exact statistical meaning of the bands is still not documented by the vendor.

Two output formats, both deterministic:

``csv``   one row per band, the header being exactly the nine columns above
``json``  a single object with provenance + a ``bands`` array; this is what the
          website / MCP layer reads

The pip values written are the **display bounds** (the ``12-110`` style numbers
the original panel prints), not the per-class min/max. See
``engine/buckets.py`` for why those are different.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import os
from typing import Dict, List, Optional, Sequence

from .buckets import BAND_LABELS, BucketStat

RECORD_FIELDS = (
    "symbol",
    "year",
    "timeframe",
    "band",
    "lowerPips",
    "upperPips",
    "scannerVersion",
    "sourceFileHash",
    "datasetVersion",
)


def build_records(
    stats: Sequence[BucketStat],
    *,
    symbol: str,
    year: int,
    timeframe: str,
    scanner_version: str,
    source_file_hash: str,
    dataset_version: str,
) -> List[Dict[str, object]]:
    """One record per band, in Normal -> Medium -> Crazy order."""
    records: List[Dict[str, object]] = []
    for i, band in enumerate(BAND_LABELS):
        st = stats[i] if i < len(stats) else None
        records.append(
            {
                "symbol": symbol,
                "year": year,
                "timeframe": timeframe,
                "band": band,
                "lowerPips": st.lower_display if st else 0,
                "upperPips": st.upper_display if st else 0,
                "scannerVersion": scanner_version,
                "sourceFileHash": source_file_hash,
                "datasetVersion": dataset_version,
            }
        )
    return records


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_csv(path: str, records: Sequence[Dict[str, object]]) -> str:
    """Write the nine-column table and return its sha256."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=list(RECORD_FIELDS), lineterminator="\n")
    writer.writeheader()
    for r in records:
        writer.writerow({k: r[k] for k in RECORD_FIELDS})
    body = buf.getvalue()
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def write_json(
    path: str,
    records: Sequence[Dict[str, object]],
    *,
    meta: Optional[Dict[str, object]] = None,
    stats: Optional[Sequence[BucketStat]] = None,
) -> str:
    """Write a JSON document with provenance, bands and (optionally) full stats."""
    doc: Dict[str, object] = {}
    if meta:
        doc["provenance"] = meta
    doc["bands"] = list(records)
    if stats:
        doc["detail"] = [
            {
                "band": BAND_LABELS[i] if i < len(BAND_LABELS) else s.label,
                "count": s.count,
                "totalBars": s.total_bars,
                "averageBars": s.average_bars,
                "totalPips": s.total_pips,
                "averagePips": s.average_pips,
                "longestBars": s.longest_bars,
                "longestPips": s.longest_pips,
                "shortestBars": s.shortest_bars,
                "shortestPips": s.shortest_pips,
            }
            for i, s in enumerate(stats)
        ]
    body = json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(body)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def format_panel(stats: Sequence[BucketStat], *, title: str = "") -> str:
    """Render the Scan Summary the way the original panel lays it out.

    Used by the CLI so a run can be eyeballed against a screenshot line by line.
    """
    out: List[str] = []
    if title:
        out.append(title)
    out.append(f"{'Scan Summary':<40}")
    out.append("")
    for i, s in enumerate(stats):
        band = BAND_LABELS[i] if i < len(BAND_LABELS) else s.label
        freq = (80, 15, 5)[i] if i < 3 else 0
        out.append(f"{s.label} Wave Frequency ({freq}%): {s.lower_display} pips - {s.upper_display} pips")
        out.append(f"   Total:    {s.total_bars} bars with {s.total_pips} pips")
        out.append(f"   Average:  {s.average_bars} bars with {s.average_pips} pips")
        out.append(f"   Longest:  {s.longest_bars} bars with {s.longest_pips} pips")
        out.append(f"   Shortest: {s.shortest_bars} bars with {s.shortest_pips} pips")
        out.append("")
    return "\n".join(out)


def default_table_path(prefix: str, fmt: str) -> str:
    root, _ = os.path.splitext(prefix)
    return f"{root}.table.{fmt}"
