"""Trade-history CSV ingestion for the Extra Martingale Scanner.

Two things here are not obvious and are the reason this module exists rather
than a bare ``csv.DictReader`` loop:

1. **Four header variants.** The 275 files under ``downloads/`` are not one
   format. 260 carry a UTF-8 BOM, 12 do not, one has the columns in a
   different order and omits ``Holding Time``, and two are 0 bytes. Reading by
   column *name* handles all of them; reading by position does not.

2. **Junk rows that look like trades.** Some files carry monthly summary rows
   shaped like ``Type=buy, Symbol=profit, Comment='Summary trade result
   06.2024'``. They pass a naive ``Type in (buy, sell)`` filter and inflate
   net profit. Across the 275 files they add up to a material share of the
   total, so they are dropped explicitly and counted.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, List, Optional

#: Time labels in these exports are day-first: ``17/07/2026 03:42:23``.
OPEN_TIME_FORMATS = ("%d/%m/%Y %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y-%m-%d %H:%M:%S")

#: A pair symbol is alphanumeric with optional ``.x``-style suffix. There is no
#: length floor: index CFDs are legitimate and shorter than six characters --
#: ``HK50`` 1,396 trades, ``FRA40`` 1,899, ``SP500`` 1,464, ``US500`` 32 across
#: ``downloads/``. An earlier ``len >= 6`` rule silently discarded all 4,791 of
#: them, so the check is on shape, not length.
MIN_SYMBOL_LEN = 2


@dataclass(frozen=True)
class Trade:
    """One closed position, in the units the export uses."""

    symbol: str
    direction: str  # "buy" | "sell"
    lots: float
    open_time: Optional[datetime]
    close_time: Optional[datetime]
    open_price: float  # entry price, needed for break-even of a basket
    net_pips: float
    net_profit: float
    max_profit: float  # MFE in account currency
    max_pips: float  # MFE in pips
    max_loss: float  # MAE in account currency (positive magnitude)
    max_loss_pips: float  # MAE in pips (positive magnitude)
    magic: str
    comment: str

    @property
    def is_win(self) -> bool:
        return self.net_profit > 0


@dataclass
class IngestReport:
    """What was thrown away, so a caller can show it rather than hide it."""

    total_rows: int = 0
    kept: int = 0
    dropped_non_trade: int = 0  # Type not buy/sell (balance, credit, ...)
    dropped_summary: int = 0  # Symbol looks like a pair but Comment says Summary
    dropped_bad_symbol: int = 0
    dropped_unparsable: int = 0
    headers_seen: set[str] = field(default_factory=set)

    @property
    def dropped_total(self) -> int:
        return (
            self.dropped_non_trade
            + self.dropped_summary
            + self.dropped_bad_symbol
            + self.dropped_unparsable
        )


def _f(row: dict, key: str) -> float:
    raw = (row.get(key) or "").strip()
    if not raw:
        return 0.0
    return float(raw)


def _parse_time(raw: str) -> Optional[datetime]:
    s = (raw or "").strip()
    if not s:
        return None
    for fmt in OPEN_TIME_FORMATS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _looks_like_symbol(sym: str) -> bool:
    """Reject summary-row placeholders such as ``profit``.

    Shape, not length: index CFDs carry digits (``HK50``, ``FRA40``, ``SP500``),
    so alphanumerics with an optional ``.x``/``-`` suffix pass. ``profit`` is
    caught earlier by :func:`is_summary_row`; this only screens shapes that
    cannot be an instrument at all.
    """
    if len(sym) < MIN_SYMBOL_LEN:
        return False
    return all(ch.isalnum() or ch in "._-" for ch in sym)


def is_summary_row(symbol: str, comment: str) -> bool:
    """True for the monthly ``Summary trade result MM.YYYY`` roll-up rows."""
    if "summary" in (comment or "").lower():
        return True
    # belt and braces: the placeholder symbol on its own is disqualifying
    return symbol.strip().lower() == "profit"


def read_trades(path: str, report: Optional[IngestReport] = None) -> List[Trade]:
    """Parse one trade-history CSV into :class:`Trade` objects.

    Rows are kept only when they are a real buy/sell on a plausible symbol.
    Everything else is counted in ``report`` instead of being silently skipped.
    """
    rep = report if report is not None else IngestReport()
    trades: List[Trade] = []

    with open(path, encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        rep.headers_seen.add(tuple(reader.fieldnames or ()))
        for row in reader:
            rep.total_rows += 1

            direction = (row.get("Type") or "").strip().lower()
            if direction not in ("buy", "sell"):
                rep.dropped_non_trade += 1
                continue

            symbol = (row.get("Symbol") or "").strip()
            comment = (row.get("Comment") or "").strip()

            if is_summary_row(symbol, comment):
                rep.dropped_summary += 1
                continue
            if not _looks_like_symbol(symbol):
                rep.dropped_bad_symbol += 1
                continue

            try:
                trade = Trade(
                    symbol=symbol,
                    direction=direction,
                    lots=_f(row, "Lots"),
                    open_time=_parse_time(row.get("Open Time") or ""),
                    close_time=_parse_time(row.get("Close Time") or ""),
                    open_price=_f(row, "Open Price"),
                    net_pips=_f(row, "Net Pips"),
                    net_profit=_f(row, "Net Profit"),
                    max_profit=_f(row, "Max Profit"),
                    max_pips=_f(row, "Max Pips"),
                    max_loss=abs(_f(row, "Max Loss")),
                    max_loss_pips=abs(_f(row, "Max Loss Pips")),
                    magic=(row.get("Magic Number") or "").strip(),
                    comment=comment,
                )
            except (TypeError, ValueError):
                rep.dropped_unparsable += 1
                continue

            trades.append(trade)
            rep.kept += 1

    return trades


def filter_by_date(
    trades: Iterable[Trade], start: Optional[datetime] = None, end: Optional[datetime] = None
) -> List[Trade]:
    """Keep trades whose ``open_time`` falls inside ``[start, end]``.

    Trades with no parsable open time are dropped when a bound is given: an
    unknown date cannot be proven to be inside the window.
    """
    if start is None and end is None:
        return list(trades)
    out: List[Trade] = []
    for t in trades:
        if t.open_time is None:
            continue
        if start is not None and t.open_time < start:
            continue
        if end is not None and t.open_time > end:
            continue
        out.append(t)
    return out
