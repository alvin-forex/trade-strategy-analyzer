"""29-pair x 6-timeframe orchestration for the martingale Scanner.

This module is deliberately thin. The two expensive pieces already exist and
are tested elsewhere:

* :mod:`fit` scores a grid's step distance against observed swing bands;
* :mod:`scanner` splits trade history into martingale cycles.

What was missing is the outer loop -- 29 symbols x 6 timeframes, one cell
failing without killing the batch -- and an output contract that says what a
"signal" actually is. This file supplies only those two things. It rewrites
neither ``scanner.py`` nor ``fit.py``.

A *signal* is a cell whose fit ratio crossed either of ``fit.py``'s own
thresholds (``tight`` below ``TIGHT_BELOW``, ``wide`` above ``WIDE_ABOVE``).
The thresholds are read from :mod:`fit`, never duplicated here, so a change to
the grading rule automatically changes what the signal list means. Every cell
is still emitted in the full matrix; the signal list is a filtered view of it.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from ..bar import Bar, load_bars_csv
from ..version import ENGINE_VERSION
from . import fit
from .ingest import Trade
from .scanner import scan_symbol

#: The 29 symbols used by the research experiment (``exp_allpairs2.SYMS``).
#: Duplicated as a plain tuple so importing this module never imports the
#: research package; the source of truth is named here for auditability.
DEFAULT_PAIRS: Tuple[str, ...] = (
    "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD",
    "CADCHF", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD",
    "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD",
    "USDCAD", "USDCHF", "USDJPY", "XAUUSD",
)

#: OC's 2026-11-25 ruling: M5/M15/M30/H1/H4/D1, explicitly excluding M1/W1.
DEFAULT_TFS: Tuple[str, ...] = ("M5", "M15", "M30", "H1", "H4", "D1")

VERDICT_OK = "OK"
VERDICT_NO_DATA = "NO_DATA"
VERDICT_NO_STEP = "NO_STEP"
VERDICT_UNUSABLE = "UNUSABLE"

# Grades that count as a signal, taken from fit.py's own constants.
SIGNAL_GRADES = frozenset({fit.GRADE_TIGHT, fit.GRADE_WIDE})

BarsLoader = Callable[[str, str], Sequence[Bar]]
TradeLoader = Callable[[str], Sequence[Trade]]


@dataclass(frozen=True)
class MatrixRow:
    """One (symbol, timeframe) cell. All inputs are carried for re-checking."""

    symbol: str
    timeframe: str
    step_pips: Optional[float]
    band_pips: Optional[float]
    ratio: Optional[float]
    grade: str
    bars: int
    trades: int
    cycles: int
    verdict: str

    @property
    def is_signal(self) -> bool:
        return self.verdict == VERDICT_OK and self.grade in SIGNAL_GRADES


@dataclass
class MatrixResult:
    """Full matrix, filtered signal list, per-cell errors and run metadata."""

    rows: List[MatrixRow] = field(default_factory=list)
    errors: List[Dict[str, str]] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def signals(self) -> List[MatrixRow]:
        return [r for r in self.rows if r.is_signal]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "rows": [asdict(r) for r in self.rows],
            "signals": [asdict(r) for r in self.signals],
            "errors": list(self.errors),
            "meta": dict(self.meta),
        }


def _step_for(
    symbol: str,
    step_pips_by_symbol: Optional[Mapping[str, float]],
    default_step_pips: Optional[float],
) -> Optional[float]:
    if step_pips_by_symbol and symbol in step_pips_by_symbol:
        return step_pips_by_symbol[symbol]
    return default_step_pips


def _cycles_for(
    symbol: str, trades: Sequence[Trade]
) -> int:
    """Reuse ``scanner.scan_symbol``; do not re-implement cycle splitting."""
    return sum(len(result.cycles) for result in scan_symbol(trades, symbol))


def scan_matrix(
    pairs: Sequence[str] = DEFAULT_PAIRS,
    timeframes: Sequence[str] = DEFAULT_TFS,
    *,
    years: int = fit.DEFAULT_YEARS,
    p_quantile: float = 0.80,
    pip_size_by_symbol: Optional[Mapping[str, float]] = None,
    default_pip_size: float = 0.0001,
    step_pips_by_symbol: Optional[Mapping[str, float]] = None,
    default_step_pips: Optional[float] = None,
    bars_loader: Optional[BarsLoader] = None,
    trade_loader: Optional[TradeLoader] = None,
) -> MatrixResult:
    """Score every pair/timeframe cell, isolating failures per cell.

    ``bars_loader(symbol, tf)`` is injected so the whole matrix is testable
    with synthetic bars and without an MT5 terminal. When omitted, a CSV
    loader is used that expects ``<symbol>_<tf>.csv`` files; pass a loader that
    calls ``mt5_source.fetch_bars`` for live data.

    ``trade_loader`` is optional: when supplied, cycle counts come from the
    existing :mod:`scanner` logic. Fit scoring never depends on trades.
    """
    if bars_loader is None:
        raise ValueError("bars_loader is required (see module docstring)")
    if years <= 0:
        raise ValueError("years must be positive")
    if not 0.0 <= p_quantile <= 1.0:
        raise ValueError("p_quantile must be in [0, 1]")

    out = MatrixResult(
        meta={
            "engine_version": ENGINE_VERSION,
            "pairs": list(pairs),
            "timeframes": list(timeframes),
            "years": years,
            "p_quantile": p_quantile,
            "signal_grades": sorted(SIGNAL_GRADES),
            "tight_below": fit.TIGHT_BELOW,
            "wide_above": fit.WIDE_ABOVE,
        }
    )
    trade_cache: Dict[str, Sequence[Trade]] = {}

    for symbol in pairs:
        if symbol not in trade_cache:
            if trade_loader is None:
                trade_cache[symbol] = []
            else:
                try:
                    trade_cache[symbol] = trade_loader(symbol) or []
                except Exception as exc:  # per-symbol isolation
                    out.errors.append(
                        {"symbol": symbol, "timeframe": "", "reason": f"trades: {exc}"}
                    )
                    trade_cache[symbol] = []
        trades = trade_cache[symbol]

        for tf in timeframes:
            step = _step_for(symbol, step_pips_by_symbol, default_step_pips)
            try:
                bars = bars_loader(symbol, tf) or []
                if not bars:
                    out.rows.append(
                        MatrixRow(symbol, tf, step, None, None, fit.GRADE_UNKNOWN,
                                  0, len(trades), 0, VERDICT_NO_DATA)
                    )
                    out.errors.append(
                        {"symbol": symbol, "timeframe": tf, "reason": "no bars"}
                    )
                    continue
                if step is None or step <= 0:
                    out.rows.append(
                        MatrixRow(symbol, tf, step, None, None, fit.GRADE_UNKNOWN,
                                  len(bars), len(trades), 0, VERDICT_NO_STEP)
                    )
                    out.errors.append(
                        {"symbol": symbol, "timeframe": tf, "reason": "no step distance"}
                    )
                    continue

                pip = (pip_size_by_symbol or {}).get(symbol, default_pip_size)
                score = fit.score_grid(
                    symbol, step, bars, pip, years=years, p_quantile=p_quantile
                )
                out.rows.append(
                    MatrixRow(
                        symbol=symbol,
                        timeframe=tf,
                        step_pips=step,
                        band_pips=score.band_pips,
                        ratio=score.ratio,
                        grade=score.grade,
                        bars=len(bars),
                        trades=len(trades),
                        cycles=_cycles_for(symbol, trades) if trades else 0,
                        verdict=VERDICT_OK,
                    )
                )
            except Exception as exc:  # one bad cell must not kill the matrix
                out.rows.append(
                    MatrixRow(symbol, tf, step, None, None, fit.GRADE_UNKNOWN,
                              0, len(trades), 0, VERDICT_UNUSABLE)
                )
                out.errors.append(
                    {"symbol": symbol, "timeframe": tf, "reason": str(exc)}
                )
    return out


def write_outputs(result: MatrixResult, out_dir: str) -> Dict[str, str]:
    """Write ``matrix.csv``, ``signals.csv`` and ``meta.json`` into ``out_dir``."""
    os.makedirs(out_dir, exist_ok=True)
    paths = {
        "matrix": os.path.join(out_dir, "matrix.csv"),
        "signals": os.path.join(out_dir, "signals.csv"),
        "errors": os.path.join(out_dir, "errors.txt"),
        "meta": os.path.join(out_dir, "meta.json"),
    }
    fields = [f.name for f in MatrixRow.__dataclass_fields__.values()]
    for key in ("matrix", "signals"):
        rows = result.rows if key == "matrix" else result.signals
        with open(paths[key], "w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            for row in rows:
                writer.writerow(asdict(row))
    with open(paths["errors"], "w", encoding="utf-8") as fh:
        for err in result.errors:
            fh.write(f"{err['symbol']}|{err['timeframe']}|{err['reason']}\n")
    with open(paths["meta"], "w", encoding="utf-8") as fh:
        json.dump(result.meta, fh, indent=2, sort_keys=True, ensure_ascii=False)
    return paths


def pip_size_for_symbol(symbol: str) -> float:
    """Conventional pip size by quote, for the 29-symbol default universe.

    OC's 2026-11-25 18:15 supply note requires per-symbol pip size: JPY-quoted
    pairs and XAUUSD use 0.01, all others 0.0001. A single global ``--pip-size``
    must never be applied to all 29 symbols -- it silently mis-scales the JPY
    and gold step distances against the wave bands.
    """
    s = symbol.upper()
    if s.endswith("JPY") or s.startswith("XAU"):
        return 0.01
    return 0.0001


def load_step_pips(path: str) -> Dict[str, float]:
    """Load OC's step-pips supply: a JSON mapping or a CSV with symbol + step.

    JSON is the direct shape for ``scan_matrix(step_pips_by_symbol=...)``. CSV
    accepts either ``step_pips_median`` or ``suggest_rounded`` so both columns
    of OC's supply file can be used without preprocessing.
    """
    if path.lower().endswith(".json"):
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return {str(k): float(v) for k, v in raw.items()}
    out: Dict[str, float] = {}
    with open(path, "r", encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            sym = (row.get("symbol") or "").strip()
            if not sym:
                continue
            val = row.get("step_pips_median") or row.get("suggest_rounded") or row.get("step_pips")
            if val not in (None, ""):
                out[sym] = float(val)
    return out


def load_pip_sizes(path: Optional[str], symbols: Sequence[str]) -> Dict[str, float]:
    """Per-symbol pip sizes: explicit JSON when given, else the quote rule."""
    if path:
        with open(path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return {s: float(raw[s]) for s in symbols if s in raw}
    return {s: pip_size_for_symbol(s) for s in symbols}


def hst_bars_loader(
    history_dir: str,
    tf_suffix: Optional[Mapping[str, str]] = None,
) -> BarsLoader:
    """Build a loader over MT4 ``<SYMBOL><suffix>.hst`` files.

    ``tf_suffix`` maps a canonical TF (``M5``) to the HST filename suffix
    (``5``). When a symbol/timeframe file is absent the loader returns no bars
    and the matrix records ``NO_DATA`` for that cell rather than crashing.
    """
    from .hst_reader import load_hst_bars

    suffixes = dict(tf_suffix or {
        "M1": "1", "M5": "5", "M15": "15", "M30": "30",
        "H1": "60", "H4": "240", "D1": "1440",
    })

    def load(symbol: str, tf: str) -> Sequence[Bar]:
        suffix = suffixes.get(tf)
        if suffix is None:
            return []
        path = os.path.join(history_dir, f"{symbol}{suffix}.hst")
        if not os.path.exists(path):
            return []
        return load_hst_bars(path)

    return load


def csv_bars_loader(directory: str) -> BarsLoader:
    """Build a loader over ``<symbol>_<tf>.csv`` files in ``directory``."""
    def load(symbol: str, tf: str) -> Sequence[Bar]:
        return load_bars_csv(os.path.join(directory, f"{symbol}_{tf}.csv"))

    return load


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Scan the pair x timeframe fit matrix")
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--bars-dir", help="directory of <SYMBOL>_<TF>.csv bars")
    src.add_argument("--history-dir", help="MT4 directory of <SYMBOL><suffix>.hst files")
    parser.add_argument("--out", required=True, help="output directory")
    parser.add_argument("--pairs", default=",".join(DEFAULT_PAIRS))
    parser.add_argument("--tfs", default=",".join(DEFAULT_TFS))
    parser.add_argument("--years", type=int, default=fit.DEFAULT_YEARS)
    parser.add_argument("--pip-size", type=float, default=None,
                        help="legacy global pip size (overrides per-symbol rule for all)")
    parser.add_argument("--pip-sizes", default=None,
                        help="optional JSON {symbol: pip_size}; else inferred by quote")
    parser.add_argument("--step-pips", type=float, default=None,
                        help="legacy global step pips (overrides the per-symbol file)")
    parser.add_argument("--step-pips-file", default=None,
                        help="OC supply: step_pips_by_symbol.json or .csv")
    args = parser.parse_args(argv)

    pairs = [p.strip() for p in args.pairs.split(",") if p.strip()]
    tfs = [t.strip() for t in args.tfs.split(",") if t.strip()]
    steps = load_step_pips(args.step_pips_file) if args.step_pips_file else {}
    if args.step_pips is not None:
        steps = {s: args.step_pips for s in pairs}
    pips = load_pip_sizes(args.pip_sizes, pairs)
    if args.pip_size is not None:
        pips = {s: args.pip_size for s in pairs}

    if args.bars_dir:
        loader = csv_bars_loader(args.bars_dir)
    else:
        loader = hst_bars_loader(args.history_dir)

    result = scan_matrix(
        pairs, tfs,
        years=args.years,
        pip_size_by_symbol=pips,
        step_pips_by_symbol=steps,
        bars_loader=loader,
    )
    paths = write_outputs(result, args.out)
    print(f"rows={len(result.rows)} signals={len(result.signals)} errors={len(result.errors)}")
    for path in paths.values():
        print(path)
    return 0
    print(f"rows={len(result.rows)} signals={len(result.signals)} errors={len(result.errors)}")
    for path in paths.values():
        print(path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
