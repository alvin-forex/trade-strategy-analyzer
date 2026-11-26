"""#36 M1 single-source SQLite data layer (engine-only, no repo-root writes).

First slice of the planner's three-layer design: a trustworthy ``m1_bar``
price source with an auditable, idempotent ingest. No terminal/API call, no
``docs/`` or ``data/`` writes, so it is CI-safe.

Key correctness rule learned from review: the ``.hst`` **header** (symbol @68,
period @80, digits @84) is authoritative. Filenames and currency-name
heuristics are not -- this broker stores fiat at 5 decimals, not 4, and XAUJPY
at 0. Quantising 5-decimal prices at 1e4 destroys high/low ranges and makes
derived timeframes disagree with the broker's own H1 files.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import closing
from typing import Dict, List, Optional, Sequence, Tuple

from ..martingale.hst_reader import (
    read_hst, read_hst_header, sanity_check,
)

SCHEMA_VERSION = 2

# Seed range A approved 2026-11-26 14:02: 32 codes (28 fiat pairs + 4 XAU
# crosses). XAUJPY is present on this machine but is NOT in range A -- it is
# recorded as an observed extra only, never seeded or ingested into m1_bar.
SYMBOLS: Tuple[str, ...] = (
    "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD",
    "CADCHF", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD",
    "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD",
    "USDCAD", "USDCHF", "USDJPY",
    "XAUAUD", "XAUEUR", "XAUGBP", "XAUUSD",
)
OBSERVED_EXTRAS: Tuple[str, ...] = ("XAUJPY",)
_ALLOWED = frozenset(SYMBOLS)
_CHUNK = 5000

_DDL = (
    """CREATE TABLE IF NOT EXISTS symbol (
           code TEXT PRIMARY KEY,
           digits INTEGER NOT NULL,
           kind TEXT NOT NULL DEFAULT 'fiat'
       )""",
    """CREATE TABLE IF NOT EXISTS m1_bar (
           symbol TEXT NOT NULL REFERENCES symbol(code),
           ts INTEGER NOT NULL,
           open_px INTEGER NOT NULL,
           high_px INTEGER NOT NULL,
           low_px INTEGER NOT NULL,
           close_px INTEGER NOT NULL,
           tick_vol INTEGER NOT NULL,
           PRIMARY KEY (symbol, ts)
       ) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS ingest_run (
           run_id INTEGER PRIMARY KEY AUTOINCREMENT,
           kind TEXT NOT NULL,
           status TEXT NOT NULL,
           rows_in INTEGER NOT NULL,
           rows_new INTEGER NOT NULL,
           rows_updated INTEGER NOT NULL,
           symbols_requested INTEGER NOT NULL,
           symbols_ingested INTEGER NOT NULL,
           missing_json TEXT NOT NULL,
           src_dir TEXT NOT NULL
       )""",
    """CREATE TABLE IF NOT EXISTS meta (
           key TEXT PRIMARY KEY,
           value TEXT NOT NULL
       )""",
)

_UPSERT = """INSERT INTO m1_bar(symbol,ts,open_px,high_px,low_px,close_px,tick_vol)
             VALUES (?,?,?,?,?,?,?)
             ON CONFLICT(symbol,ts) DO UPDATE SET
               open_px=excluded.open_px, high_px=excluded.high_px,
               low_px=excluded.low_px, close_px=excluded.close_px,
               tick_vol=excluded.tick_vol
             WHERE excluded.open_px<>m1_bar.open_px
                OR excluded.high_px<>m1_bar.high_px
                OR excluded.low_px<>m1_bar.low_px
                OR excluded.close_px<>m1_bar.close_px
                OR excluded.tick_vol<>m1_bar.tick_vol"""


def infer_digits(symbol: str) -> int:
    """Fallback only -- real scale always comes from the ``.hst`` header.

    Kept for seeding a symbol row before any file is read and for synthetic
    tests. This broker stores fiat at 5 decimals, so the fallback is deliberately
    not used for price quantisation during real ingest.
    """
    s = symbol.upper()
    if s.startswith("XAU"):
        return 2
    if s.endswith("JPY"):
        return 3
    return 4


def _kind(symbol: str) -> str:
    return "metal-cross" if symbol.upper().startswith("XAU") else "fiat"


def _fixed(value: float, digits: int) -> int:
    return int(round(value * (10 ** digits)))


def _connect(db_path: str) -> sqlite3.Connection:
    cx = sqlite3.connect(db_path)
    cx.execute("PRAGMA foreign_keys=ON")
    cx.execute("PRAGMA journal_mode=WAL")
    cx.execute("PRAGMA busy_timeout=30000")
    return cx


def init_db(db_path: str) -> None:
    """Create the schema (idempotent) and validate/stamp the schema version."""
    parent = os.path.dirname(os.path.abspath(db_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with closing(_connect(db_path)) as cx, cx:
        for stmt in _DDL:
            cx.execute(stmt)
        row = cx.execute(
            "SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is not None:
            found = int(row[0])
            if found != SCHEMA_VERSION:
                raise RuntimeError(
                    f"tsa.db schema_version={found} but module expects "
                    f"{SCHEMA_VERSION}; migrate explicitly, do not mix versions")
        else:
            cx.execute(
                "INSERT INTO meta(key,value) VALUES ('schema_version',?)",
                (str(SCHEMA_VERSION),))
        for sym in SYMBOLS:
            cx.execute(
                "INSERT OR IGNORE INTO symbol(code,digits,kind) VALUES (?,?,?)",
                (sym, infer_digits(sym), _kind(sym)),
            )


def ingest_hst_dir(hst_dir: str, db_path: str,
                   symbols: Optional[Sequence[str]] = None) -> Dict[str, object]:
    """Ingest ``<SYMBOL>1.hst`` files into ``m1_bar``.

    Scale comes from each file's header, and a non-M1 or corrupt file is
    rejected. A rerun inserts zero new rows but *does* update a bar whose MT4
    values changed (the forming bar / a redownload). Missing and rejected
    symbols are reported and persisted in ``ingest_run``.
    """
    init_db(db_path)
    wanted: List[str] = []
    rejected: List[str] = []
    for raw in (symbols if symbols is not None else SYMBOLS):
        sym = raw.strip().upper()
        if sym not in _ALLOWED:
            rejected.append(sym)
        elif sym not in wanted:
            wanted.append(sym)  # de-duplicate without losing order

    missing: List[str] = []
    bad: List[str] = []
    rows_in = 0
    rows_new = 0
    rows_updated = 0
    ingested = 0

    with closing(_connect(db_path)) as cx, cx:
        for sym in wanted:
            path = os.path.join(hst_dir, f"{sym}1.hst")
            if not os.path.exists(path):
                missing.append(sym)
                continue
            header = read_hst_header(path)
            records = read_hst(path)
            if header is None or header.period != 1 or not records:
                bad.append(sym)
                continue
            ok, _ = sanity_check(records)
            # sanity_check validates each incoming bar against its OWN high/low
            # (low<=o,c<=high) and monotonic time -- an internally corrupt bar
            # never becomes truth. A revised forming bar is fine as long as its
            # new values are self-consistent; the upsert below rewrites it.
            if not ok or any(r.epoch % 60 or r.low <= 0 for r in records):
                bad.append(sym)
                continue

            # Header is authoritative; correct the seeded fallback value too.
            cx.execute("UPDATE symbol SET digits=? WHERE code=?",
                       (header.digits, sym))
            digits = header.digits
            payload = [
                (sym, r.epoch, _fixed(r.open, digits), _fixed(r.high, digits),
                 _fixed(r.low, digits), _fixed(r.close, digits), r.tick_volume)
                for r in records
            ]
            before = cx.execute(
                "SELECT count(*) FROM m1_bar WHERE symbol=?", (sym,)).fetchone()[0]
            changed = 0
            for start in range(0, len(payload), _CHUNK):
                cur = cx.executemany(_UPSERT, payload[start:start + _CHUNK])
                changed += max(cur.rowcount, 0)
            after = cx.execute(
                "SELECT count(*) FROM m1_bar WHERE symbol=?", (sym,)).fetchone()[0]
            new = after - before
            rows_in += len(payload)
            rows_new += new
            rows_updated += changed - new
            ingested += 1

        status = "ok" if not missing and not bad and not rejected else "partial"
        cx.execute(
            "INSERT INTO ingest_run(kind,status,rows_in,rows_new,rows_updated,"
            "symbols_requested,symbols_ingested,missing_json,src_dir) "
            "VALUES ('m1_hst',?,?,?,?,?,?,?,?)",
            (status, rows_in, rows_new, rows_updated, len(wanted), ingested,
             json.dumps({"missing": missing, "bad": bad, "rejected": rejected},
                        ensure_ascii=False),
             os.path.abspath(hst_dir)),
        )

    return {
        "symbols_ingested": ingested,
        "symbols_requested": len(wanted),
        "missing": missing,
        "bad": bad,
        "rejected": rejected,
        "bars_in": rows_in,
        "bars_new": rows_new,
        "bars_updated": rows_updated,
        "status": status,
    }


def summary(db_path: str) -> Dict[str, object]:
    """Counts, time span and last run for a data-layer report."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(db_path)
    with closing(_connect(db_path)) as cx, cx:
        m1 = cx.execute("SELECT count(*) FROM m1_bar").fetchone()[0]
        syms = cx.execute("SELECT count(*) FROM symbol").fetchone()[0]
        span = cx.execute(
            "SELECT min(ts), max(ts), count(DISTINCT symbol) FROM m1_bar"
        ).fetchone()
        ver = cx.execute(
            "SELECT value FROM meta WHERE key='schema_version'").fetchone()
        last = cx.execute(
            "SELECT status, rows_in, rows_new, rows_updated FROM ingest_run "
            "ORDER BY run_id DESC LIMIT 1").fetchone()
    return {
        "schema_version": int(ver[0]) if ver else 0,
        "m1_bar_rows": m1,
        "symbol_rows": syms,
        "min_ts": span[0],
        "max_ts": span[1],
        "symbols_covered": span[2],
        "last_run": ({"status": last[0], "rows_in": last[1],
                      "rows_new": last[2], "rows_updated": last[3]}
                     if last else None),
    }
