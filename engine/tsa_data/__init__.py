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

SCHEMA_VERSION = 3

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

#: Derived timeframes this layer materialises. M1 is the only price source.
DERIVED_TFS: Tuple[str, ...] = ("H1", "H4", "D1")
_TF_MINUTES = {"H1": 60, "H4": 240, "D1": 1440}

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
    # Derived timeframes: rebuildable materialised cache, never a source.
    # A bucket whose m1_cnt is short is still stored (weekends legitimately are)
    # but flagged, so a consumer can choose to skip it.
    """CREATE TABLE IF NOT EXISTS bar_tf (
           symbol TEXT NOT NULL REFERENCES symbol(code),
           tf TEXT NOT NULL,
           ts INTEGER NOT NULL,
           open_px INTEGER NOT NULL,
           high_px INTEGER NOT NULL,
           low_px INTEGER NOT NULL,
           close_px INTEGER NOT NULL,
           tick_vol INTEGER NOT NULL,
           m1_cnt INTEGER NOT NULL,
           is_partial INTEGER NOT NULL,
           PRIMARY KEY (symbol, tf, ts)
       ) WITHOUT ROWID""",
    """CREATE TABLE IF NOT EXISTS qc_result (
           tf TEXT NOT NULL,
           symbol TEXT NOT NULL,
           compared INTEGER NOT NULL,
           compared_complete INTEGER NOT NULL,
           mismatch INTEGER NOT NULL,
           mismatch_complete INTEGER NOT NULL,
           max_abs_diff REAL NOT NULL,
           max_abs_vol_diff REAL NOT NULL,
           digits INTEGER NOT NULL,
           ok INTEGER NOT NULL,
           PRIMARY KEY (tf, symbol)
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
    """Create the schema (idempotent) and validate/stamp the schema version.

    The version is checked *before* any DDL: sqlite3's legacy isolation mode
    autocommits DDL, so creating tables and then raising would leave a stale db
    owning tables from a newer schema (and a later slice adding a column would
    silently no-op on the pre-created table).
    """
    parent = os.path.dirname(os.path.abspath(db_path))
    if parent:
        os.makedirs(parent, exist_ok=True)
    with closing(_connect(db_path)) as cx, cx:
        has_meta = cx.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='meta'"
        ).fetchone()
        if has_meta:
            row = cx.execute(
                "SELECT value FROM meta WHERE key='schema_version'").fetchone()
            if row is not None and int(row[0]) != SCHEMA_VERSION:
                raise RuntimeError(
                    f"tsa.db schema_version={row[0]} but module expects "
                    f"{SCHEMA_VERSION}; migrate explicitly, do not mix versions")
        for stmt in _DDL:
            cx.execute(stmt)
        if not has_meta or cx.execute(
                "SELECT 1 FROM meta WHERE key='schema_version'").fetchone() is None:
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
        has_bar_tf = cx.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='bar_tf'"
        ).fetchone()
        tf_rows = ({tf: cx.execute(
            "SELECT count(*) FROM bar_tf WHERE tf=?", (tf,)).fetchone()[0]
            for tf in DERIVED_TFS} if has_bar_tf
            else {tf: 0 for tf in DERIVED_TFS})
    return {
        "schema_version": int(ver[0]) if ver else 0,
        "m1_bar_rows": m1,
        "symbol_rows": syms,
        "bar_tf_rows": tf_rows,
        "min_ts": span[0],
        "max_ts": span[1],
        "symbols_covered": span[2],
        "last_run": ({"status": last[0], "rows_in": last[1],
                      "rows_new": last[2], "rows_updated": last[3]}
                     if last else None),
    }


def materialize_tf(db_path: str, tf: str,
                   symbols: Optional[Sequence[str]] = None) -> Dict[str, object]:
    """Rebuild ``bar_tf`` for one timeframe from ``m1_bar``.

    M1 is the only source: open = first M1 open of the bucket, high/low = extents,
    close = last M1 close, tick volume summed. ``m1_cnt`` records how many M1
    bars folded into the bucket.

    ``is_partial`` follows ``engine.m1_aggregation.usable_buckets``: short is only
    meaningful at the **edges** of the symbol's own M1 span. This broker's M1
    session is 00:15–23:54 (1,420 minutes), so a complete D1 day never reaches
    1,440 — an absolute threshold would flag every D1 row as partial forever and
    hide correct data. Interior short buckets are real (weekend/holiday) and are
    kept unflagged, matching the aggregation module.
    """
    tf = tf.strip().upper()
    if tf not in DERIVED_TFS:
        raise ValueError(f"unsupported timeframe {tf!r}; known: {list(DERIVED_TFS)}")
    minutes = _TF_MINUTES[tf]
    step = minutes * 60
    wanted = [s.strip().upper() for s in (symbols if symbols is not None else SYMBOLS)]
    init_db(db_path)
    total = 0
    done: List[str] = []
    with closing(_connect(db_path)) as cx, cx:
        for sym in wanted:
            if cx.execute("SELECT 1 FROM symbol WHERE code=?", (sym,)).fetchone() is None:
                continue
            cx.execute("DELETE FROM bar_tf WHERE symbol=? AND tf=?", (sym, tf))
            buckets: Dict[int, list] = {}
            cursor = cx.execute(
                "SELECT ts,open_px,high_px,low_px,close_px,tick_vol "
                "FROM m1_bar WHERE symbol=? ORDER BY ts", (sym,))
            for ts, o, h, l, c, v in cursor:
                key = ts - ts % step
                b = buckets.get(key)
                if b is None:
                    # first bar of the bucket defines open/close and count=1
                    buckets[key] = [o, h, l, c, v, 1]
                    continue
                if h > b[1]:
                    b[1] = h
                if l < b[2]:
                    b[2] = l
                b[3] = c
                b[4] += v
                b[5] += 1
            order = sorted(buckets)
            if not order:
                continue
            last = len(order) - 1
            payload = []
            for i, k in enumerate(order):
                b = buckets[k]
                edge_and_short = b[5] < minutes and i in (0, last)
                payload.append((sym, tf, k, b[0], b[1], b[2], b[3], b[4], b[5],
                                1 if edge_and_short else 0))
            for start in range(0, len(payload), _CHUNK):
                cx.executemany(
                    "INSERT INTO bar_tf(symbol,tf,ts,open_px,high_px,low_px,"
                    "close_px,tick_vol,m1_cnt,is_partial) VALUES (?,?,?,?,?,?,?,?,?,?)",
                    payload[start:start + _CHUNK])
            total += len(payload)
            done.append(sym)
    return {"tf": tf, "bars": total, "symbols": len(done)}


def qc_against_hst(db_path: str, tf: str, hst_dir: str,
                   symbols: Optional[Sequence[str]] = None) -> Dict[str, object]:
    """Compare ``bar_tf`` against the broker's own ``.hst`` for that timeframe.

    Self-consistency proves nothing; the broker file is the independent check.

    Gate semantics (``ok``):
      * judged on **complete** buckets -- head/tail buckets are cut by the hst
        window, so their differences are reported but never gate;
      * a bucket the broker has inside our own M1 span but we failed to produce
        is a **missing** bucket and fails the gate (otherwise a fold that silently
        drops data would be certified clean);
      * symbols with no broker file are reported as ``no_evidence`` and fail the
        gate too -- no evidence is not green.
    """
    from ..martingale.hst_reader import read_hst, read_hst_header

    tf = tf.strip().upper()
    if tf not in DERIVED_TFS:
        raise ValueError(f"unsupported timeframe {tf!r}; known: {list(DERIVED_TFS)}")
    wanted = [s.strip().upper() for s in (symbols if symbols is not None else SYMBOLS)]
    init_db(db_path)
    per_symbol: Dict[str, dict] = {}
    compared_total = complete_total = 0
    mismatch_total = mismatch_complete_total = 0
    missing_total = only_mine_total = 0
    vol_mismatch_total = 0
    vol_mismatch_complete_total = 0
    worst = worst_complete = 0.0
    worst_vol = worst_vol_complete = 0.0
    no_evidence: List[str] = []
    with closing(_connect(db_path)) as cx, cx:
        cx.execute("DELETE FROM qc_result WHERE tf=?", (tf,))
        for sym in wanted:
            path = os.path.join(hst_dir, f"{sym}{_TF_MINUTES[tf]}.hst")
            if not os.path.exists(path):
                per_symbol[sym] = {"error": "hst missing"}
                no_evidence.append(sym)
                continue
            header = read_hst_header(path)
            if header is None or header.period != _TF_MINUTES[tf]:
                per_symbol[sym] = {"error": f"period mismatch ({header and header.period})"}
                no_evidence.append(sym)
                continue
            row = cx.execute("SELECT digits FROM symbol WHERE code=?", (sym,)).fetchone()
            if row is not None and int(row[0]) != header.digits:
                # A scale disagreement would show up as a uniform 10x error on
                # every bucket -- a false red with no diagnosis. Say so instead.
                per_symbol[sym] = {
                    "error": f"digits mismatch m1={row[0]} hst={header.digits}"}
                no_evidence.append(sym)
                continue
            digits = header.digits
            scale = 10 ** digits
            ref = {r.epoch: (r.open, r.high, r.low, r.close, r.tick_volume)
                   for r in read_hst(path)}
            mine = {ts: (o, h, l, c, v, part) for ts, o, h, l, c, v, part in cx.execute(
                "SELECT ts,open_px,high_px,low_px,close_px,tick_vol,is_partial "
                "FROM bar_tf WHERE symbol=? AND tf=?", (sym, tf)).fetchall()}
            compared = complete = 0
            mismatch = mismatch_complete = vol_mismatch = vol_mismatch_complete = 0
            max_diff = max_diff_complete = max_vol_diff = max_vol_diff_complete = 0.0
            for ts, (o, h, l, c, v, part) in mine.items():
                r = ref.get(ts)
                if r is None:
                    continue
                compared += 1
                diffs = [abs(a - _fixed(b, digits)) for a, b in
                         zip((o, h, l, c), r[:4])]
                worst_here = max(diffs) / scale
                if worst_here > 0:
                    mismatch += 1
                    max_diff = max(max_diff, worst_here)
                vol_here = float(abs(v - r[4]))
                if vol_here:
                    vol_mismatch += 1
                    max_vol_diff = max(max_vol_diff, vol_here)
                if not part:
                    complete += 1
                    if worst_here > 0:
                        mismatch_complete += 1
                        max_diff_complete = max(max_diff_complete, worst_here)
                    if vol_here:
                        vol_mismatch_complete += 1
                        max_vol_diff_complete = max(max_vol_diff_complete, vol_here)
            lo, hi = (min(mine), max(mine)) if mine else (0, 0)
            missing = [t for t in ref if mine and lo <= t <= hi and t not in mine]
            only_mine = [t for t in mine if t not in ref]
            per_symbol[sym] = {
                "compared": compared, "mismatch": mismatch,
                "max_abs_diff": round(max_diff, 12),
                "compared_complete": complete,
                "mismatch_complete": mismatch_complete,
                "max_abs_diff_complete": round(max_diff_complete, 12),
                "missing": len(missing), "only_mine": len(only_mine),
                "vol_mismatch": vol_mismatch,
                "max_abs_vol_diff": round(max_vol_diff, 6),
                "vol_mismatch_complete": vol_mismatch_complete,
                "max_abs_vol_diff_complete": round(max_vol_diff_complete, 6),
            }
            cx.execute(
                "INSERT INTO qc_result(tf,symbol,compared,compared_complete,"
                "mismatch,mismatch_complete,max_abs_diff,max_abs_vol_diff,digits,ok) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (tf, sym, compared, complete, mismatch, mismatch_complete,
                 max_diff_complete, max_vol_diff, digits,
                 1 if complete > 0 and mismatch_complete == 0 and not missing else 0))
            compared_total += compared
            mismatch_total += mismatch
            complete_total += complete
            mismatch_complete_total += mismatch_complete
            missing_total += len(missing)
            only_mine_total += len(only_mine)
            vol_mismatch_total += vol_mismatch
            vol_mismatch_complete_total += vol_mismatch_complete
            worst = max(worst, max_diff)
            worst_complete = max(worst_complete, max_diff_complete)
            worst_vol = max(worst_vol, max_vol_diff)
            worst_vol_complete = max(worst_vol_complete, max_vol_diff_complete)
    ok = (complete_total > 0 and mismatch_complete_total == 0
          and missing_total == 0 and not no_evidence)
    return {
        "tf": tf,
        "compared": compared_total,
        "mismatch": mismatch_total,
        "max_abs_diff": round(worst, 12),
        "compared_complete": complete_total,
        "mismatch_complete": mismatch_complete_total,
        "max_abs_diff_complete": round(worst_complete, 12),
        # Broker buckets inside our own span that we failed to produce.
        "missing": missing_total,
        "only_mine": only_mine_total,
        # MT4 boundary ticks make an exact volume match impossible; reported,
        # not gated (7 of 839 complete buckets differ by exactly +-1).
        "vol_mismatch": vol_mismatch_total,
        "max_abs_vol_diff": round(worst_vol, 6),
        "vol_mismatch_complete": vol_mismatch_complete_total,
        "max_abs_vol_diff_complete": round(worst_vol_complete, 6),
        "symbols_compared": len(wanted) - len(no_evidence),
        "no_evidence": no_evidence,
        "ok": ok,
        "per_symbol": per_symbol,
    }
