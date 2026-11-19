"""SET-file reading and change detection.

Two questions the owner asked that this answers:

**"Has the EA's configuration changed?"** -- 2,867 ``.set`` files sit in the
tree, covering 106 signals. Only 26 signals have any file whose name carries a
date, and only 6 of those carry more than one date. For those 6 the versions can
be diffed parameter by parameter, so "it changed" becomes "``PipStep2`` went
10.0 -> 40.0 on 2026-05-04".

**"Which parameters govern the grid?"** -- the martingale shape depends on the
lot ladder and the step ladder, and EA families spell those differently:
``Lots`` + ``LotMul`` + ``PipStepMul`` (multiplicative) versus ``lot1..lot9`` +
``PipStep1..PipStep9`` (explicit per-level ladder). Both are recognised, and a
file that matches neither is reported as unknown rather than guessed at.

A ``.set`` file is flat ``key=value`` text. Two details bite:

* MT4 writes ``key=value`` with no quoting, but values may contain ``=``
  (a comment field), so only the **first** ``=`` splits.
* Older exports carry no ``EA_VERSION``, so version order cannot be taken from
  the file contents -- only the date embedded in the filename orders them.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .layers import excel_round2 as _excel_round2

#: ``(10437)Dragon Wave v2.10AUDCAD_H1_Both_2026-04-09_02-45-30.set``
#: The signal id is in parentheses, the date is the last ``YYYY-MM-DD`` group.
FILENAME_RE = re.compile(
    r"^\((?P<signal>\d+)\)(?P<rest>.*?)(?P<date>\d{4}-\d{2}-\d{2})(?:[_\s].*)?\.set$",
    re.IGNORECASE,
)

#: Multiplicative families (Dragon Wave, Flash, ...).
KEY_BASE_LOT = "Lots"
KEY_LOT_MUL = "LotMul"
KEY_STEP_MUL = "PipStepMul"

#: Explicit-ladder families (MKD, ...).
KEY_LOT_LADDER = "lot"
KEY_STEP_LADDER = "PipStep"


@dataclass(frozen=True)
class SetFile:
    """One ``.set`` file, parsed."""

    path: str
    params: Dict[str, str]
    signal: Optional[str] = None
    version_date: Optional[date] = None

    @property
    def name(self) -> str:
        return os.path.basename(self.path)

    @property
    def ea_name(self) -> str:
        return self.params.get("EA_NAME", "")

    @property
    def symbol(self) -> str:
        return self.params.get("EA_SYMBOL", "")

    @property
    def period(self) -> str:
        return self.params.get("EA_PERIOD", "")

    def f(self, key: str) -> Optional[float]:
        raw = self.params.get(key)
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    def grid(self) -> "GridSpec":
        return read_grid(self.params)


@dataclass(frozen=True)
class GridSpec:
    """The grid parameters, normalised across EA families.

    ``lots`` is always the ladder from the first level upward, so a caller does
    not have to know whether the file spelled it as a multiplier or explicitly.
    ``None`` in ``lots`` means "this family expresses it multiplicatively".
    """

    base_lot: Optional[float]
    lot_multiplier: Optional[float]
    step_multiplier: Optional[float]
    lot_ladder: List[float] = field(default_factory=list)
    step_ladder: List[float] = field(default_factory=list)
    family: str = "unknown"  # "multiplicative" | "ladder" | "unknown"

    def effective_lots(self, levels: int = 9) -> List[float]:
        """The lot ladder this grid produces, whichever way it was expressed.

        A multiplicative family is expanded to ``base * mul**i``; a ladder
        family returns what it declared, truncated or (if needed) extended by
        the last ratio. Returns ``[]`` when there is not enough information,
        rather than inventing a base lot.

        Rounding uses Excel's half-away-from-zero rule, not Python's banker's
        rounding: ``0.02 * 2.5**2 = 0.125`` becomes 0.13, which is the lot the
        terminal would actually place. ``round()`` would give 0.12 and disagree
        with every other tier calculation in this package.
        """
        if self.family == "ladder" and self.lot_ladder:
            return list(self.lot_ladder[:levels])
        if self.base_lot is None:
            return []
        mul = self.lot_multiplier or 1.0
        return [_excel_round2(self.base_lot * (mul**i)) for i in range(levels)]

    def effective_steps(self, levels: int = 9) -> List[float]:
        """The step ladder, similarly normalised.

        Multiplicative families only give a step *multiplier* and a first step;
        the first step is ``PipStep`` when present, otherwise the ladder is
        unavailable and ``[]`` is returned.
        """
        if self.family == "ladder" and self.step_ladder:
            return list(self.step_ladder[:levels])
        first = self.first_step()
        if first is None:
            return []
        mul = self.step_multiplier or 1.0
        return [round(first * (mul**i), 2) for i in range(levels)]

    def first_step(self) -> Optional[float]:
        if self.step_ladder:
            return self.step_ladder[0]
        return None


def parse_set_text(text: str) -> Dict[str, str]:
    """Parse flat ``key=value`` lines.

    Splits on the first ``=`` only: MT4 does not escape values, so a comment
    like ``commentB=buy=ok`` would otherwise lose its tail. Blank lines,
    ``;``/``#`` comments, and lines with no ``=`` are skipped.
    """
    params: Dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in ";#":
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        params[key.strip()] = value.strip()
    return params


def parse_filename(path: str) -> Tuple[Optional[str], Optional[date]]:
    """Pull ``(signal_id, version_date)`` out of a ``.set`` filename.

    Both parts are optional and independent: ``(10437)X.set`` yields a signal
    with no date, ``X_2026-04-09.set`` yields a date with no signal.
    """
    name = os.path.basename(path)
    m = FILENAME_RE.match(name)
    if m:
        try:
            d = date.fromisoformat(m.group("date"))
        except ValueError:
            d = None
        return m.group("signal"), d

    sig = re.match(r"^\((\d+)\)", name)
    loose = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    try:
        d = date.fromisoformat(loose.group(1)) if loose else None
    except ValueError:
        d = None
    return (sig.group(1) if sig else None), d


def read_set(path: str) -> SetFile:
    """Read one ``.set`` file. Encoding is ``utf-8-sig`` because some exports
    carry a BOM and the first key would otherwise become ``\\ufeffEA_NAME``."""
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        params = parse_set_text(fh.read())
    signal, vdate = parse_filename(path)
    return SetFile(path=path, params=params, signal=signal, version_date=vdate)


def read_grid(params: Dict[str, str]) -> GridSpec:
    """Normalise a parameter dict into a :class:`GridSpec`.

    Order matters: a file that has *both* ``Lots``/``LotMul`` and ``lot1..9``
    is treated as a ladder, because explicit per-level values are what the EA
    actually trades; the multiplier fields would then be leftovers.
    """
    lot_ladder = _numeric_ladder(params, KEY_LOT_LADDER, 1, 9)
    step_ladder = _numeric_ladder(params, KEY_STEP_LADDER, 1, 9)

    def num(key: str) -> Optional[float]:
        raw = params.get(key)
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            return None

    if lot_ladder or step_ladder:
        return GridSpec(
            base_lot=lot_ladder[0] if lot_ladder else num(KEY_BASE_LOT),
            lot_multiplier=num(KEY_LOT_MUL),
            step_multiplier=num(KEY_STEP_MUL),
            lot_ladder=lot_ladder,
            step_ladder=step_ladder,
            family="ladder",
        )

    base = num(KEY_BASE_LOT)
    lot_mul = num(KEY_LOT_MUL)
    if base is not None or lot_mul is not None:
        return GridSpec(
            base_lot=base,
            lot_multiplier=lot_mul,
            step_multiplier=num(KEY_STEP_MUL),
            family="multiplicative",
        )

    return GridSpec(base_lot=None, lot_multiplier=None, step_multiplier=None)


def _numeric_ladder(
    params: Dict[str, str], prefix: str, first: int, last: int
) -> List[float]:
    """Collect ``prefix<1..9>`` values in level order, stopping at the first gap.

    Stopping at a gap rather than skipping it keeps level indices honest: a
    ladder ``1,2,4,_,6`` must not silently become ``1,2,4,6``.
    """
    out: List[float] = []
    for i in range(first, last + 1):
        raw = params.get(f"{prefix}{i}")
        if raw is None:
            break
        try:
            out.append(float(raw))
        except ValueError:
            break
    return out


@dataclass(frozen=True)
class ParamChange:
    """One parameter that differs between two versions."""

    key: str
    old: Optional[str]
    new: Optional[str]

    @property
    def is_grid(self) -> bool:
        """True when the change touches lot size or step distance."""
        k = self.key.lower()
        return (
            k.startswith("pipstep")
            or k.startswith("lot")
            or k.startswith("lots")
            or k in ("lotmul", "pipstepmul", "entrylot")
        )

    @property
    def is_ea_identity(self) -> bool:
        """True for the keys that say *which EA* this file configures.

        ``EA_NAME`` / ``EA_VERSION`` changing is not a tuning change, it is a
        different product. Diffing the rest of the parameters across that
        boundary compares two unrelated strategies and would report dozens of
        meaningless "changes", so callers should gate on this.
        """
        return self.key in ("EA_NAME", "EA_VERSION")


def diff_sets(old: SetFile, new: SetFile) -> List[ParamChange]:
    """Every parameter whose value differs, including added and removed keys.

    A key present in only one version is reported with ``None`` on the missing
    side: an EA upgrade that renamed ``PipStep`` to ``PipStep1`` is a change
    even though neither file disagrees with itself.
    """
    changes: List[ParamChange] = []
    for key in sorted(set(old.params) | set(new.params)):
        a = old.params.get(key)
        b = new.params.get(key)
        if a != b:
            changes.append(ParamChange(key, a, b))
    return changes


def timeline(files: Iterable[SetFile]) -> List[SetFile]:
    """Dated versions of one signal, oldest first.

    Undated files are excluded: they cannot be ordered, and pretending they are
    "before everything" would invent a change history.
    """
    dated = [f for f in files if f.version_date is not None]
    return sorted(dated, key=lambda f: f.version_date)  # type: ignore[arg-type,return-value]


def version_changes(files: Iterable[SetFile]) -> List[Tuple[SetFile, SetFile, List[ParamChange]]]:
    """Consecutive-pair diffs across a signal's dated versions."""
    ordered = timeline(files)
    return [
        (a, b, diff_sets(a, b)) for a, b in zip(ordered, ordered[1:])
    ]


def group_by_signal(files: Sequence[SetFile]) -> Dict[str, List[SetFile]]:
    """Bucket files by signal id; files with no id are skipped."""
    out: Dict[str, List[SetFile]] = {}
    for f in files:
        if f.signal:
            out.setdefault(f.signal, []).append(f)
    return out
