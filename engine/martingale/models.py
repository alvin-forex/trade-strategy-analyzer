"""The record shapes stage 1-2 produce, in one import path.

The dispatch names ``engine/martingale/models.py`` as a deliverable, and the
reason it earns its place is that stage 3 (fit scoring) and stage 4 (CLI/batch)
import record types without caring which module computed them. So this file is
the stable surface: the types are *defined* where their logic lives -- a
:class:`Trade` belongs with ingestion, a :class:`BandSet` with the wave scan --
and re-exported here.

If a type ever needs a second definition to satisfy this file, that is the
signal the boundary is wrong, not that another copy should be added.
"""

from __future__ import annotations

from .hst_reader import HstRecord
from .ingest import IngestReport, Trade
from .layers import LayerModel
from .scanner import Cycle, ScanResult, StepStats
from .waves import BandSet, WaveScan

__all__ = [
    "BandSet",
    "Cycle",
    "HstRecord",
    "IngestReport",
    "LayerModel",
    "ScanResult",
    "StepStats",
    "Trade",
    "WaveScan",
]
