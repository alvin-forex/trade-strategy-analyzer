"""Lot-tier detection — two methods, both traceable to a written spec.

The same trade history can be grouped into "layers" two incompatible ways, and
the difference is not cosmetic: for signal 165's NZDCAD, one method yields L1-L6
and the other L1-L58. Both are implemented rather than one being chosen for the
caller, because until a golden fixture exists there is no evidence to prefer
either.

``excel``
    Mirrors ``TradingHistory_Analyzer_v8.5_template.xlsm`` → ``LotTiers`` I3-I7:

        base   = the most frequent lot                (I3)
        m0     = most frequent lot above base / base  (I4-I5, needs >=2 hits and >=1% of trades)
        cal    = largest lot appearing >= 2 times     (I5)
        span   = ROUND(LN(cal/base) / LN(m0))         (I7)
        step   = ROUND((cal/base) ** (1/span) * 20) / 20
        layer  = ROUND(LN(lot/base) / LN(step)) + 1
        (a lot whose actual value strays from base*step**(layer-1) by more than
        max(0.005, 3%) is "unclassified" = layer 0)

``linear``
    Mirrors ``docs/martin_v4_engine.js`` → ``computeLayerStats``: the label is
    just ``L<lots>``, so layer index = round(lot / base). No logarithm, no
    multiple derived from the data.

Both return the same :class:`LayerModel` shape so a caller can diff them.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .ingest import Trade

#: Tolerance for treating an actual lot as sitting on a computed tier.
#:
#: ``0.0051`` rather than ``0.005`` is not a typo: the Excel sheet uses
#: ``MAX(0.0051, 3%)`` precisely so that a lot exactly on the 0.005 boundary
#: (e.g. 0.05 against a 0.045 tier) is not lost to binary-float rounding.
#: ``TIER_EPSILON`` mirrors Excel's ``+0.000000001`` nudge for the same reason.
ABS_TOL = 0.0051
REL_TOL = 0.03
TIER_EPSILON = 1e-9


@dataclass
class LayerModel:
    """Everything needed to explain how a set of lots was indexed."""

    method: str
    base: float
    step: Optional[float]
    span: Optional[int]
    counts: Dict[int, int] = field(default_factory=dict)  # layer -> trade count
    unclassified: int = 0
    #: layer -> the distinct lots that landed in it
    lots_by_layer: Dict[int, List[float]] = field(default_factory=dict)

    @property
    def max_layer(self) -> int:
        return max(self.counts) if self.counts else 0

    @property
    def classified(self) -> int:
        return sum(self.counts.values())

    @property
    def classification_rate(self) -> float:
        total = self.classified + self.unclassified
        return self.classified / total if total else 0.0

    def theoretical_lot(self, layer: int) -> Optional[float]:
        """``base * step**(layer-1)`` — None when the model has no multiple."""
        if self.step is None or self.base == 0:
            return None
        try:
            return self.base * (self.step ** (layer - 1))
        except OverflowError:
            return None


def _lot_counter(trades: Sequence[Trade]) -> Counter:
    return Counter(round(t.lots, 2) for t in trades if t.lots > 0)


def detect_excel(trades: Sequence[Trade]) -> LayerModel:
    """Tier by the Excel v8.5 LotTiers rules (logarithmic)."""
    cnt = _lot_counter(trades)
    if not cnt:
        return LayerModel("excel", 0.0, None, None)

    base = cnt.most_common(1)[0][0]
    n_trades = sum(cnt.values())

    # m0: the most frequent lot strictly above base, provided it occurs at
    # least twice and at least 1% of the time (I4-I5).
    threshold = max(2, 0.01 * n_trades)
    above = {lot: c for lot, c in cnt.items() if lot > base and c >= threshold}
    m0 = (max(above, key=lambda lot: above[lot]) / base) if above else None

    if m0 is None or m0 <= 1.0:
        # Single-tier or no usable multiple: everything on tier 1.
        layers = {1: sum(cnt.values())}
        return LayerModel(
            "excel",
            base,
            None,
            None,
            counts=layers,
            unclassified=0,
            lots_by_layer={1: sorted(cnt)},
        )

    cal = max(lot for lot, c in cnt.items() if c >= 2)
    raw_span = math.log(cal / base) / math.log(m0)
    span = round(raw_span)
    if span < 1:
        step = m0
        span = 1
    else:
        step = round((cal / base) ** (1.0 / span) * 20) / 20

    counts: Dict[int, int] = {}
    lots_by_layer: Dict[int, List[float]] = {}
    unclassified = 0
    for lot, c in cnt.items():
        layer = _excel_layer(lot, base, step)
        if layer == 0:
            unclassified += c
            continue
        counts[layer] = counts.get(layer, 0) + c
        lots_by_layer.setdefault(layer, []).append(lot)

    for v in lots_by_layer.values():
        v.sort()
    return LayerModel("excel", base, step, span, counts, unclassified, lots_by_layer)


def _excel_round2(value: float) -> float:
    """``ROUND(value, 2)`` as Excel defines it: half away from zero.

    Python's built-in ``round`` is banker's rounding, so ``round(0.045, 2)``
    gives 0.04 where Excel gives 0.05. That single cent flips whether a lot
    sitting exactly between two tiers is classified or not, so the Excel
    behaviour is reproduced explicitly rather than inherited from ``round``.
    """
    scaled = value * 100.0
    if scaled >= 0:
        return math.floor(scaled + 0.5) / 100.0
    return math.ceil(scaled - 0.5) / 100.0


def _excel_layer(lot: float, base: float, step: float) -> int:
    """Layer index for one lot, or 0 when it does not sit on a tier."""
    if base <= 0 or step <= 1.0:
        return 1 if abs(lot - base) <= max(ABS_TOL, REL_TOL * base) else 0
    raw = math.log(lot / base) / math.log(step)
    idx = round(raw)
    if idx < 0 or idx > 19:
        return 0
    # Same order as the sheet: nudge, round to cents, then compare.
    theo = _excel_round2(base * (step ** idx) + TIER_EPSILON)
    if abs(lot - theo) <= max(ABS_TOL, REL_TOL * lot):
        return idx + 1
    return 0


def detect_linear(trades: Sequence[Trade]) -> LayerModel:
    """Tier the way ``martin_v4_engine.js`` does: label is the lot itself."""
    cnt = _lot_counter(trades)
    if not cnt:
        return LayerModel("linear", 0.0, None, None)

    base = min(cnt)
    counts: Dict[int, int] = {}
    lots_by_layer: Dict[int, List[float]] = {}
    for lot, c in cnt.items():
        layer = round(lot / base) if base else 1
        counts[layer] = counts.get(layer, 0) + c
        lots_by_layer.setdefault(layer, []).append(lot)
    for v in lots_by_layer.values():
        v.sort()
    return LayerModel("linear", base, None, None, counts, 0, lots_by_layer)


def detect(trades: Sequence[Trade], method: str = "excel") -> LayerModel:
    """Dispatch to a named method; ``excel`` is the default for reporting."""
    if method == "excel":
        return detect_excel(trades)
    if method == "linear":
        return detect_linear(trades)
    raise ValueError(f"unknown layering method {method!r}")


def compare_methods(trades: Sequence[Trade]) -> Dict[str, LayerModel]:
    """Both models side by side, for the disagreement report."""
    return {"excel": detect_excel(trades), "linear": detect_linear(trades)}
