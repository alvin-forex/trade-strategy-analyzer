"""MT5 data source: bars + symbol metadata via the official MetaTrader5 package.

Time-basis rule (verified empirically, 2026-11-18)
--------------------------------------------------
``copy_rates_range`` treats a **naive** datetime as *local* time and a
tz-aware one as an absolute instant. Passing a naive 02:00 on a machine at
UTC+8 silently shifts the window by -8h. Therefore every datetime handed to
the API is built tz-aware.

MT5 stores bar time as seconds since the epoch *in server time*. Rendering
those seconds with ``datetime.fromtimestamp(t, timezone.utc)`` therefore yields
the exact label the MT5 chart displays, which is the label that must appear in
``waves.csv``. ``server_utc_offset`` is measured, not assumed, by comparing the
tick time against the local clock.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..bar import Bar, pip_size

TIMEFRAMES = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
    "H4": 240,
    "D1": 1440,
    "W1": 10080,
}


class MT5Error(RuntimeError):
    """Raised when the terminal cannot satisfy the request."""


@dataclass(frozen=True)
class SymbolMeta:
    symbol: str
    digits: int
    point: float
    server: str
    account: int
    broker_company: str

    @property
    def pip(self) -> float:
        return pip_size(self.point, self.digits)


def _mt5():
    try:
        import MetaTrader5 as mt5  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise MT5Error("MetaTrader5 package not installed") from exc
    return mt5


def connect(path: Optional[str] = None) -> None:
    mt5 = _mt5()
    kwargs = {}
    if path:
        kwargs["path"] = path
    if not mt5.initialize(**kwargs):
        raise MT5Error(f"initialize failed: {mt5.last_error()}")
    ti = mt5.terminal_info()
    if ti is None or not ti.connected:
        raise MT5Error("terminal not connected to a trade server")


def shutdown() -> None:
    _mt5().shutdown()


def symbol_meta(symbol: str) -> SymbolMeta:
    mt5 = _mt5()
    if not mt5.symbol_select(symbol, True):
        raise MT5Error(f"symbol not available: {symbol}")
    si = mt5.symbol_info(symbol)
    if si is None:
        raise MT5Error(f"symbol_info returned None for {symbol}")
    ai = mt5.account_info()
    ti = mt5.terminal_info()
    return SymbolMeta(
        symbol=symbol,
        digits=si.digits,
        point=si.point,
        server=getattr(ai, "server", "") if ai else "",
        account=getattr(ai, "login", 0) if ai else 0,
        # The broker is the *account's* company, not terminal_info().company:
        # the latter names the platform vendor ("MetaQuotes Ltd.") and would
        # make every broker look identical in provenance output.
        broker_company=(getattr(ai, "company", "") if ai else "")
        or (getattr(ti, "company", "") if ti else ""),
    )


def server_utc_offset_hours(symbol: str) -> float:
    """Measured difference between the server clock and UTC, in hours."""
    mt5 = _mt5()
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return 0.0
    server_now = dt.datetime.fromtimestamp(tick.time, dt.timezone.utc)
    real_now = dt.datetime.now(dt.timezone.utc)
    delta = (server_now - real_now).total_seconds() / 3600.0
    # round to the nearest whole hour; server offsets are whole hours in practice
    return round(delta)


def _parse_label(value: str) -> dt.datetime:
    """'2026-09-17T02:00' -> aware datetime treated as an absolute instant."""
    return dt.datetime.strptime(value, "%Y-%m-%dT%H:%M").replace(tzinfo=dt.timezone.utc)


def fetch_bars(
    symbol: str,
    tf: str,
    start_label: str,
    end_label: str,
    meta: Optional[SymbolMeta] = None,
) -> Tuple[List[Bar], SymbolMeta]:
    """Load bars covering ``start_label .. end_label`` (server-time labels, inclusive)."""
    mt5 = _mt5()
    if tf not in TIMEFRAMES:
        raise MT5Error(f"unsupported timeframe {tf}")
    meta = meta or symbol_meta(symbol)
    tf_const = getattr(mt5, f"TIMEFRAME_{tf}")
    rates = mt5.copy_rates_range(
        symbol, tf_const, _parse_label(start_label), _parse_label(end_label)
    )
    if rates is None:
        raise MT5Error(f"copy_rates_range returned None: {mt5.last_error()}")
    bars: List[Bar] = []
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
    bars.sort(key=lambda b: b.time_label)
    return bars, meta


def probe() -> Dict[str, object]:
    """Small diagnostic used by the CLI's ``--doctor`` flag."""
    mt5 = _mt5()
    ok = mt5.initialize()
    info: Dict[str, object] = {"initialize": ok}
    if not ok:
        info["error"] = mt5.last_error()
        return info
    ti = mt5.terminal_info()
    ai = mt5.account_info()
    info.update(
        {
            "path": getattr(ti, "path", None),
            "connected": getattr(ti, "connected", None),
            "company": getattr(ti, "company", None),
            "login": getattr(ai, "login", None),
            "server": getattr(ai, "server", None),
            "trade_mode": getattr(ai, "trade_mode", None),
        }
    )
    mt5.shutdown()
    return info
