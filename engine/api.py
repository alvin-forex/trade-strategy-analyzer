"""Programmatic API — the four operations the MCP server exposes.

Everything here is a plain function over plain data so it can be tested
without an MCP transport, an MT5 terminal, or a running server:

``get_rates``        bars for one symbol/timeframe/window
``extract_waves``    ZigZag + Merge -> swing list
``compute_buckets``  80/15/5 statistics
``export_table``     volatility table written to disk

Each returns a JSON-serialisable ``dict`` and never raises for expected
problems (bad symbol, no terminal, thin sample). Failures come back as
``{"ok": False, "error": {"code": ..., "message": ...}}`` so an MCP client sees
a readable payload instead of a transport-level exception.

The HTTP/stdio layer lives in ``engine/mcp_server.py``; the batch entry point
lives in ``engine/daily.py``.
"""

from __future__ import annotations

import datetime as dt
import os
from typing import Any, Dict, List, Optional, Sequence

from .bar import Bar, pip_size, slice_window
from .buckets import (
    BAND_LABELS,
    BUCKET_METHODS,
    InsufficientSampleError,
    range_bounds,
)
from .buckets import compute_buckets as _compute_buckets
from .merge import build_waves, merge_pivots
from .table import build_records, default_table_path, write_csv, write_json
from .version import CALC_METHOD_WAVES, ENGINE_VERSION
from .waves import build_meta, default_meta_path, write_meta, write_waves_csv
from .zigzag import zigzag

# Error codes are stable strings so clients can branch on them.
E_BAD_ARG = "bad_argument"
E_NO_TERMINAL = "no_terminal"
E_SYMBOL = "unknown_symbol"
E_NO_DATA = "no_data"
E_SAMPLE = "insufficient_sample"
E_IO = "io_error"


def _err(code: str, message: str, **extra: Any) -> Dict[str, Any]:
    payload = {"ok": False, "error": {"code": code, "message": message}}
    if extra:
        payload["error"].update(extra)
    return payload


def _ok(**fields: Any) -> Dict[str, Any]:
    return {"ok": True, **fields}


def _resolve_label(value: Optional[str], default: Optional[str] = None) -> Optional[str]:
    """Accept ``YYYY-MM-DDTHH:MM``, ``YYYY.MM.DD HH:MM`` or plain dates."""
    if value is None:
        return default
    s = str(value).strip().replace(".", "-")
    if "T" in s:
        date, _, clock = s.partition("T")
    elif " " in s:
        date, _, clock = s.partition(" ")
    else:
        date, clock = s, "00:00"
    clock = clock.strip()
    if len(clock) == 5:
        return f"{date}T{clock}"
    if len(clock) >= 5:
        return f"{date}T{clock[:5]}"
    return f"{date}T00:00"


def _bars_payload(bars: Sequence[Bar]) -> List[Dict[str, Any]]:
    return [
        {
            "time": b.time_label,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "tickVolume": b.tick_volume,
        }
        for b in bars
    ]


def _load(
    symbol: str,
    tf: str,
    start: Optional[str],
    end: Optional[str],
    bars_csv: Optional[str] = None,
    meta_in: Optional[str] = None,
):
    """Fetch bars from MT5 (default) or an offline CSV. Returns (bars, symmeta)."""
    if bars_csv:
        from .sources import csv_source

        return csv_source.fetch_bars(bars_csv, start, end, meta_path=meta_in)

    from .sources import mt5_source

    mt5_source.connect()
    sym = mt5_source.symbol_meta(symbol)
    bars, sym = mt5_source.fetch_bars(symbol, tf, start, end, sym)
    return bars, sym


def _window(
    symbol: str,
    tf: str,
    start: Optional[str],
    end: Optional[str],
    bars_csv: Optional[str],
    meta_in: Optional[str],
    past_bars: Optional[int],
):
    """Load bars and, if ``past_bars`` is given, trim to the last N of them."""
    from .sources import mt5_source

    # Validate the timeframe up front, in both the MT5 and offline paths, so a
    # typo is a bad_argument rather than a silently different dataset.
    if tf not in mt5_source.TIMEFRAMES:
        return None, None, _err(E_BAD_ARG, f"unsupported timeframe {tf!r}; "
                                 f"expected one of {sorted(mt5_source.TIMEFRAMES)}")
    s = _resolve_label(start)
    e = _resolve_label(end)
    if past_bars is not None and (s or e):
        return None, None, _err(
            E_BAD_ARG, "give either start/end or past_bars, not both"
        )
    if past_bars is not None:
        # MT5 needs concrete bounds; fetch wide then trim.
        if bars_csv:
            from .sources import csv_source

            bars, sym = csv_source.fetch_bars(bars_csv, None, None, meta_path=meta_in)
            bars = bars[-int(past_bars) :]
        else:
            from .sources import mt5_source

            mt5_source.connect()
            sym = mt5_source.symbol_meta(symbol)
            tf_const = mt5_source.TIMEFRAMES.get(tf)
            if tf_const is None:
                return None, None, _err(E_BAD_ARG, f"unsupported timeframe {tf}")
            mt5 = mt5_source._mt5()  # noqa: SLF001 - intentional thin reuse
            rates = mt5.copy_rates_from_pos(symbol, getattr(mt5, f"TIMEFRAME_{tf}"), 0, int(past_bars))
            if rates is None:
                return None, sym, _err(E_NO_DATA, f"copy_rates_from_pos returned None: {mt5.last_error()}")
            bars = []
            for row in rates:
                label = dt.datetime.fromtimestamp(int(row["time"]), dt.timezone.utc)
                bars.append(
                    Bar(
                        time_label=label.strftime("%Y-%m-%dT%H:%M"),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        tick_volume=int(row["tick_volume"]),
                    )
                )
        if not bars:
            return None, sym, _err(E_NO_DATA, "no bars returned")
        return bars, sym, None

    if not s or not e:
        return None, None, _err(E_BAD_ARG, "start and end are both required (or use past_bars)")
    try:
        bars, sym = _load(symbol, tf, s, e, bars_csv, meta_in)
    except Exception as exc:  # MT5Error, FileNotFoundError, ValueError
        code = E_NO_TERMINAL if "initialize" in str(exc) or "MetaTrader5" in str(exc) else E_NO_DATA
        return None, None, _err(code, str(exc))
    if not bars:
        return None, sym, _err(E_NO_DATA, f"no bars between {s} and {e}")
    return bars, sym, None


# --------------------------------------------------------------------- tools
def get_rates(
    symbol: str,
    tf: str = "H1",
    start: Optional[str] = None,
    end: Optional[str] = None,
    past_bars: Optional[int] = None,
    bars_csv: Optional[str] = None,
    meta_in: Optional[str] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """Return OHLC bars for one symbol/timeframe/window.

    ``past_bars`` selects the most recent N bars instead of a date window.
    ``limit`` truncates the returned payload (the newest bars are kept) without
    changing anything else — useful when a client only needs a preview.
    """
    bars, sym, err = _window(symbol, tf, start, end, bars_csv, meta_in, past_bars)
    if err:
        return err
    total = len(bars)
    if limit is not None and int(limit) > 0 and int(limit) < total:
        bars = bars[-int(limit) :]
    return _ok(
        symbol=getattr(sym, "symbol", symbol),
        timeframe=tf,
        digits=sym.digits,  # type: ignore[attr-defined]
        point=sym.point,  # type: ignore[attr-defined]
        pip=pip_size(sym.point, sym.digits),  # type: ignore[attr-defined]
        server=getattr(sym, "server", ""),
        broker=getattr(sym, "broker_company", ""),
        barCount=total,
        returned=len(bars),
        firstBar=bars[0].time_label,
        lastBar=bars[-1].time_label,
        bars=_bars_payload(bars),
        engineVersion=ENGINE_VERSION,
    )


def extract_waves(
    symbol: str,
    tf: str = "H1",
    start: Optional[str] = None,
    end: Optional[str] = None,
    past_bars: Optional[int] = None,
    depth: int = 12,
    deviation: int = 5,
    backstep: int = 3,
    merge_pct: float = 35.0,
    merge_mode: str = "drop_next",
    bar_mode: str = "exclusive",
    bars_csv: Optional[str] = None,
    meta_in: Optional[str] = None,
) -> Dict[str, Any]:
    """Run ZigZag + Merge and return the swing list with provenance."""
    if backstep >= depth:
        return _err(E_BAD_ARG, "backstep must be smaller than depth")
    bars, sym, err = _window(symbol, tf, start, end, bars_csv, meta_in, past_bars)
    if err:
        return err

    pip = pip_size(sym.point, sym.digits)  # type: ignore[attr-defined]
    pivots = zigzag(bars, depth, deviation, backstep, sym.point)  # type: ignore[attr-defined]
    try:
        merged = merge_pivots(pivots, merge_pct, merge_mode)
    except ValueError as exc:
        return _err(E_BAD_ARG, str(exc))
    waves = build_waves(merged, pip, bar_mode)

    return _ok(
        symbol=getattr(sym, "symbol", symbol),
        timeframe=tf,
        digits=sym.digits,  # type: ignore[attr-defined]
        pip=pip,
        server=getattr(sym, "server", ""),
        broker=getattr(sym, "broker_company", ""),
        window={"from": bars[0].time_label, "to": bars[-1].time_label, "bars": len(bars)},
        params={
            "depth": depth,
            "deviationPoints": deviation,
            "backstep": backstep,
            "mergePct": merge_pct,
            "mergeMode": merge_mode,
            "barMode": bar_mode,
        },
        pivotCount=len(pivots),
        mergedPivotCount=len(merged),
        waveCount=len(waves),
        totalBars=sum(w.bars for w in waves),
        waves=[
            {
                "idx": w.idx,
                "startTime": w.start_time,
                "endTime": w.end_time,
                "bars": w.bars,
                "amplitudePips": w.amplitude_pips,
                "direction": w.direction,
            }
            for w in waves
        ],
        engineVersion=ENGINE_VERSION,
        calcMethod=CALC_METHOD_WAVES,
    )


def compute_buckets(
    symbol: Optional[str] = None,
    tf: str = "H1",
    start: Optional[str] = None,
    end: Optional[str] = None,
    past_bars: Optional[int] = None,
    method: str = "count",
    depth: int = 12,
    deviation: int = 5,
    backstep: int = 3,
    merge_pct: float = 35.0,
    merge_mode: str = "drop_next",
    bar_mode: str = "exclusive",
    bars_csv: Optional[str] = None,
    meta_in: Optional[str] = None,
    amplitudes: Optional[Sequence[float]] = None,
    bar_counts: Optional[Sequence[int]] = None,
) -> Dict[str, Any]:
    """Return 80/15/5 statistics.

    Either supply ``amplitudes`` (+ ``bar_counts``) directly, or give a symbol
    and window so the full pipeline runs first.
    """
    if method not in BUCKET_METHODS:
        return _err(E_BAD_ARG, f"method must be one of {list(BUCKET_METHODS)}")

    raw_amps: Optional[List[float]] = None
    sym = None
    bars = None

    if amplitudes is not None:
        amps = [float(a) for a in amplitudes]
        brs = [int(b) for b in bar_counts] if bar_counts is not None else [0] * len(amps)
        if len(brs) != len(amps):
            return _err(E_BAD_ARG, "bar_counts must match amplitudes in length")
        context: Dict[str, Any] = {"source": "supplied"}
    else:
        if not symbol:
            return _err(E_BAD_ARG, "give either amplitudes or a symbol")
        if backstep >= depth:
            return _err(E_BAD_ARG, "backstep must be smaller than depth")
        bars, sym, err = _window(symbol, tf, start, end, bars_csv, meta_in, past_bars)
        if err:
            return err
        pip = pip_size(sym.point, sym.digits)  # type: ignore[attr-defined]
        pivots = zigzag(bars, depth, deviation, backstep, sym.point)  # type: ignore[attr-defined]
        try:
            merged = merge_pivots(pivots, merge_pct, merge_mode)
        except ValueError as exc:
            return _err(E_BAD_ARG, str(exc))
        waves = build_waves(merged, pip, bar_mode)
        amps = [w.amplitude_pips for w in waves]
        brs = [w.bars for w in waves]
        raw_amps = [
            round(abs(pivots[i + 1].price - pivots[i].price) / pip, 1)
            for i in range(len(pivots) - 1)
        ]
        context = {
            "source": "pipeline",
            "symbol": getattr(sym, "symbol", symbol),
            "timeframe": tf,
            "window": {"from": bars[0].time_label, "to": bars[-1].time_label, "bars": len(bars)},
        }

    try:
        stats = _compute_buckets(
            amps, brs, method=method, raw_amplitudes=raw_amps, strict=True
        )
    except InsufficientSampleError as exc:
        return _err(E_SAMPLE, str(exc), found=exc.found, required=exc.required)

    if not stats:
        return _err(E_SAMPLE, "no swings to classify")

    rb = range_bounds(raw_amps, amps) if raw_amps else None
    return _ok(
        **context,
        method=method,
        swingCount=len(amps),
        totalBars=sum(brs),
        totalPips=round(sum(amps), 1),
        rangeBounds=list(rb) if rb else None,
        buckets=[
            {
                "label": s.label,
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
                "lowerPips": s.lower_display,
                "upperPips": s.upper_display,
            }
            for i, s in enumerate(stats)
        ],
        engineVersion=ENGINE_VERSION,
    )


def export_table(
    out_dir: str,
    symbol: str,
    tf: str = "H1",
    start: Optional[str] = None,
    end: Optional[str] = None,
    past_bars: Optional[int] = None,
    method: str = "count",
    depth: int = 12,
    deviation: int = 5,
    backstep: int = 3,
    merge_pct: float = 35.0,
    merge_mode: str = "drop_next",
    bar_mode: str = "exclusive",
    bars_csv: Optional[str] = None,
    meta_in: Optional[str] = None,
    formats: Sequence[str] = ("csv", "json"),
    write_waves: bool = True,
) -> Dict[str, Any]:
    """Run the pipeline and write waves + volatility table to ``out_dir``.

    Returns the paths and sha256 of every artefact so a caller can verify what
    landed on disk. File names are ``<SYMBOL>_<TF>.table.{csv,json}`` and
    ``<SYMBOL>_<TF>.waves.csv``.
    """
    res = compute_buckets(
        symbol=symbol,
        tf=tf,
        start=start,
        end=end,
        past_bars=past_bars,
        method=method,
        depth=depth,
        deviation=deviation,
        backstep=backstep,
        merge_pct=merge_pct,
        merge_mode=merge_mode,
        bar_mode=bar_mode,
        bars_csv=bars_csv,
        meta_in=meta_in,
    )
    if not res.get("ok"):
        return res

    # Re-run the pipeline here to get Wave objects for the CSV side-output.
    bars, sym, err = _window(symbol, tf, start, end, bars_csv, meta_in, past_bars)
    if err:
        return err
    pip = pip_size(sym.point, sym.digits)  # type: ignore[attr-defined]
    pivots = zigzag(bars, depth, deviation, backstep, sym.point)  # type: ignore[attr-defined]
    merged = merge_pivots(pivots, merge_pct, merge_mode)
    waves = build_waves(merged, pip, bar_mode)
    stats = _compute_buckets(
        [w.amplitude_pips for w in waves],
        [w.bars for w in waves],
        method=method,
        raw_amplitudes=[
            round(abs(pivots[i + 1].price - pivots[i].price) / pip, 1)
            for i in range(len(pivots) - 1)
        ],
        strict=True,
    )

    os.makedirs(out_dir, exist_ok=True)
    stem = os.path.join(out_dir, f"{symbol}_{tf}")
    year = int(bars[-1].time_label[:4])

    # Paths in the returned payload/manifest use forward slashes so a run on
    # Windows and a run on the WSL production box produce the same JSON.
    def _rel(p: str) -> str:
        return p.replace(os.sep, "/")

    offset = 0.0
    if not bars_csv:
        try:
            from .sources import mt5_source

            offset = mt5_source.server_utc_offset_hours(symbol)
        except Exception:  # pragma: no cover - diagnostic only
            offset = 0.0

    artifacts: Dict[str, Any] = {}
    try:
        if write_waves:
            waves_path = f"{stem}.waves.csv"
            waves_sha = write_waves_csv(waves_path, waves)
            meta_path = default_meta_path(waves_path)
            meta = build_meta(
                broker=getattr(sym, "broker_company", "") or "",
                server=getattr(sym, "server", "") or "",
                symbol=getattr(sym, "symbol", symbol),
                symbol_digits=sym.digits,  # type: ignore[attr-defined]
                tf=tf,
                window_from=bars[0].time_label,
                window_to=bars[-1].time_label,
                params={
                    "depth": depth,
                    "deviation_points": deviation,
                    "backstep": backstep,
                    "merge_pct": merge_pct,
                    "merge_mode": merge_mode,
                    "bar_mode": bar_mode,
                    "pip_size": pip,
                    "bucket_method": method,
                },
                engine_version=ENGINE_VERSION,
                calc_method=CALC_METHOD_WAVES,
                server_utc_offset=offset,
                time_basis="server",
                bar_count=len(bars),
                wave_count=len(waves),
                first_pivot_idx=merged[0].idx if merged else -1,
                last_pivot_idx=merged[-1].idx if merged else -1,
                covered_bars=(merged[-1].idx - merged[0].idx) if len(merged) > 1 else 0,
                csv_sha256=waves_sha,
                total_bars=sum(w.bars for w in waves),
            )
            write_meta(meta_path, meta)
            artifacts["waves"] = {"path": _rel(waves_path), "sha256": waves_sha}
            artifacts["wavesMeta"] = {"path": _rel(meta_path)}

        records = build_records(
            stats,
            symbol=symbol,
            year=year,
            timeframe=tf,
            scanner_version=ENGINE_VERSION,
            source_file_hash=artifacts.get("waves", {}).get("sha256", ""),
            dataset_version=f"{tf}-{bars[0].time_label}..{bars[-1].time_label}",
        )
        if "csv" in formats:
            p = default_table_path(stem, "csv")
            artifacts["tableCsv"] = {"path": _rel(p), "sha256": write_csv(p, records)}
        if "json" in formats:
            p = default_table_path(stem, "json")
            artifacts["tableJson"] = {
                "path": _rel(p),
                "sha256": write_json(
                    p,
                    records,
                    meta={"engineVersion": ENGINE_VERSION, "calcMethod": CALC_METHOD_WAVES},
                    stats=stats,
                ),
            }
    except OSError as exc:
        return _err(E_IO, str(exc))

    return _ok(
        symbol=getattr(sym, "symbol", symbol),
        timeframe=tf,
        year=year,
        window={"from": bars[0].time_label, "to": bars[-1].time_label, "bars": len(bars)},
        waveCount=len(waves),
        swingCount=sum(s.count for s in stats),
        artifacts=artifacts,
        engineVersion=ENGINE_VERSION,
    )
