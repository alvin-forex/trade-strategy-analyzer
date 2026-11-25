# -*- coding: utf-8 -*-
"""COPYTRADE v1.3 §5.1——SQLite 九張表 DDL（唯一 schema 來源）。

照 SPEC §5.1 九張表落鎖；copy_sims 擴 v1.3 §11 六維欄（不增表，照 SPEC）。
trades.source_file＋source_row 溯源必填（§5.2）。
"""

DDL = [
    # 1. symbols——L0 唯一真相來源（MT5 SymbolInfoDouble 導出）
    """CREATE TABLE IF NOT EXISTS symbols (
        symbol TEXT PRIMARY KEY,
        pip_size REAL NOT NULL,
        tick_size REAL NOT NULL,
        tick_value REAL NOT NULL,
        contract_size REAL NOT NULL,
        quote_currency TEXT NOT NULL,
        margin_initial REAL,
        fx_at_export REAL,
        exported_at TEXT NOT NULL,
        source TEXT NOT NULL DEFAULT 'MT5 SymbolInfoDouble'
    )""",
    # 2. prices_daily——按日換算用（收市價）
    """CREATE TABLE IF NOT EXISTS prices_daily (
        symbol TEXT NOT NULL,
        date TEXT NOT NULL,
        price REAL NOT NULL,
        PRIMARY KEY (symbol, date)
    )""",
    # 3. trades——原始逐單（溯源：source_file＋source_row §5.2）
    """CREATE TABLE IF NOT EXISTS trades (
        trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        typ TEXT NOT NULL,
        lots REAL NOT NULL,
        open_time TEXT NOT NULL,
        close_time TEXT NOT NULL,
        open_price REAL NOT NULL,
        close_price REAL NOT NULL,
        net_pips REAL NOT NULL,
        net_profit REAL NOT NULL,
        max_profit REAL,
        max_loss REAL,
        magic TEXT,
        comment TEXT,
        source_file TEXT NOT NULL,
        source_row INTEGER NOT NULL,
        qc_flag TEXT
    )""",
    # 4. cycles——一次完整馬丁週期
    """CREATE TABLE IF NOT EXISTS cycles (
        cycle_id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        direction TEXT NOT NULL,
        open_time TEXT NOT NULL,
        close_time TEXT NOT NULL,
        layers_n INTEGER NOT NULL,
        lots_total REAL NOT NULL,
        pnl_total REAL NOT NULL,
        data_grade TEXT NOT NULL
    )""",
    # 5. layers——馬丁層
    """CREATE TABLE IF NOT EXISTS layers (
        cycle_id INTEGER NOT NULL,
        layer_no INTEGER NOT NULL,
        lots REAL NOT NULL,
        open_time TEXT NOT NULL,
        open_price REAL NOT NULL,
        pnl REAL NOT NULL,
        lots_cum REAL NOT NULL,
        PRIMARY KEY (cycle_id, layer_no),
        FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
    )""",
    # 6. copy_sims——v1.3 六維模擬矩陣（§11.1）
    """CREATE TABLE IF NOT EXISTS copy_sims (
        sim_id INTEGER PRIMARY KEY AUTOINCREMENT,
        signal_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        layer_policy TEXT NOT NULL,
        copy_method TEXT NOT NULL,
        account_type TEXT NOT NULL,
        cost_scenario TEXT NOT NULL,
        cycles_n INTEGER NOT NULL,
        trades_filled INTEGER NOT NULL,
        trades_missed INTEGER NOT NULL,
        layers_filtered INTEGER,  -- §11.6 執行品質：被層檔截走嘅層數
        gross_pnl REAL NOT NULL,
        net_pnl REAL NOT NULL,
        win_rate REAL NOT NULL,
        profit_factor REAL,
        expectancy REAL,
        avg_win REAL,            -- §11.6 回報組：平均盈利單
        avg_loss REAL,           -- §11.6 回報組：平均虧損單（負值）
        monthly_growth REAL,
        monthly_pnl TEXT,        -- §11.6 回報組：每月 P/L（"YYYY-MM:val|..."）
        max_dd REAL,
        max_dd_pct REAL,
        margin_peak REAL,
        margin_ratio REAL,
        max_concurrent INTEGER,
        max_layer INTEGER,
        max_float_loss REAL,
        margin_stop_hit INTEGER NOT NULL DEFAULT 0,
        breach_layer_no INTEGER,
        stable_month_ratio REAL,
        worst_month REAL,
        max_consec_losses INTEGER,
        recovery_days INTEGER,
        concentration TEXT,
        est_sl_cost_usd REAL,
        est_margin_peak_usd REAL,
        suggested_start_equity_usd REAL,
        risk_adj_score REAL,
        data_grade TEXT NOT NULL,
        outcome_note TEXT
    )""",
    # 7. margin_req——逐層累積保證金（§5.2 lots_cum 可計爆倉層級）
    """CREATE TABLE IF NOT EXISTS margin_req (
        cycle_id INTEGER NOT NULL,
        layer_no INTEGER NOT NULL,
        lots_cum REAL NOT NULL,
        margin_cum_usd REAL,
        PRIMARY KEY (cycle_id, layer_no),
        FOREIGN KEY (cycle_id) REFERENCES cycles(cycle_id)
    )""",
    # 8. tpsl_grid——止盈止損掃描（P1 掃描表，P0 先建結構）
    """CREATE TABLE IF NOT EXISTS tpsl_grid (
        grid_id INTEGER PRIMARY KEY AUTOINCREMENT,
        cycle_id INTEGER NOT NULL,
        tp_pips REAL,
        sl_pips REAL,
        outcome TEXT,
        pnl_usd REAL
    )""",
    # 9. perf_periods——分期匯總（§6.6 保證金回報率）
    """CREATE TABLE IF NOT EXISTS perf_periods (
        period_type TEXT NOT NULL,
        period_key TEXT NOT NULL,
        strategy_id TEXT NOT NULL,
        symbol TEXT NOT NULL,
        net_pnl REAL NOT NULL,
        margin_peak REAL,
        margin_return REAL,
        win_rate REAL,
        PRIMARY KEY (period_type, period_key, strategy_id, symbol)
    )""",
]

# Natural keys for the three ingestion tables (OC dispatch 2026-11-24 21:15).
#
# Before this existed ``ingest()`` used plain ``INSERT``, so every ``--all`` run
# re-inserted the same rows: one file ingested twice produced 271 → 542 trades
# and 542 cycles in isolation. The key is content-based (never ``source_row``)
# because a refreshed CSV shifts row numbers, which would resurrect the old
# rows as "new" ones.
#
# ``cycles`` deliberately keys on ``(signal_id, symbol, direction, open_time)``
# rather than the full content: a CSV refresh can extend a still-open cycle, and
# that must UPDATE the existing row (layers_n / lots_total / pnl_total) instead
# of inserting a second copy.
NATURAL_KEYS = [
    (
        "ux_trades_natural",
        "trades",
        ("signal_id", "symbol", "typ", "lots", "open_time", "close_time",
         "open_price", "close_price", "net_pips", "net_profit",
         "max_profit", "max_loss", "magic", "comment"),
    ),
    (
        "ux_cycles_natural",
        "cycles",
        ("signal_id", "symbol", "direction", "open_time"),
    ),
]

#: Audit trail for collapsed duplicates — the dispatch asks for "安全剔重、留審計".
DEDUPE_LOG_DDL = """CREATE TABLE IF NOT EXISTS dedupe_log (
    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
    ran_at TEXT NOT NULL,
    table_name TEXT NOT NULL,
    kept_id INTEGER NOT NULL,
    dropped_ids TEXT NOT NULL,
    dropped_rows INTEGER NOT NULL,
    note TEXT
)"""


def _table_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def index_exists(conn, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='index' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _collapse_duplicates(conn, table: str, cols, note: str = "") -> int:
    """Keep the lowest rowid per natural key, log one audit row per table.

    Returns the number of rows removed. Idempotent: a second call removes 0.

    The audit row records how many rows went and up to 200 of the dropped ids —
    enough to reconstruct what happened without making ``dedupe_log`` bigger
    than the tables it describes.
    """
    if not _table_exists(conn, table):
        return 0
    pk = "trade_id" if table == "trades" else "cycle_id"
    col_sql = ", ".join(cols)
    groups = conn.execute(
        f"SELECT {col_sql}, COUNT(*) AS n, MIN({pk}) AS keep_id, "
        f"GROUP_CONCAT({pk}) AS ids FROM {table} "
        f"GROUP BY {col_sql} HAVING n > 1"
    ).fetchall()
    if not groups:
        return 0
    from datetime import datetime, timezone

    ran_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    dropped = 0
    all_doomed: list = []
    kept_ids: list = []
    for g in groups:
        keep_id = g[len(cols) + 1]
        ids = [int(x) for x in str(g[len(cols) + 2]).split(",")]
        doomed = [i for i in ids if i != keep_id]
        if not doomed:
            continue
        placeholders = ",".join("?" * len(doomed))
        conn.execute(f"DELETE FROM {table} WHERE {pk} IN ({placeholders})", doomed)
        all_doomed.extend(doomed)
        kept_ids.append(keep_id)
        dropped += len(doomed)
    if dropped:
        sample = ",".join(str(i) for i in all_doomed[:200])
        if len(all_doomed) > 200:
            sample += f",...(+{len(all_doomed) - 200} more)"
        conn.execute(
            "INSERT INTO dedupe_log(ran_at, table_name, kept_id, dropped_ids,"
            " dropped_rows, note) VALUES(?,?,?,?,?,?)",
            (ran_at, table, kept_ids[0] if len(kept_ids) == 1 else -1, sample,
             dropped, (note + f" [groups={len(groups)}]").strip()),
        )
    return dropped


def dedupe_all(conn, note: str = "") -> dict:
    """Collapse duplicates in trades/cycles/layers, returning per-table counts.

    ``layers`` needs no natural-key index (its PK is already
    ``(cycle_id, layer_no)``), but orphan layers must go when a cycle row is
    dropped — that is handled here rather than by SQLite cascade, because the
    schema has no ``ON DELETE CASCADE`` and changing that would rewrite the
    table.
    """
    conn.execute(DEDUPE_LOG_DDL)
    removed = {
        "trades": _collapse_duplicates(conn, "trades", NATURAL_KEYS[0][2], note),
        "cycles": _collapse_duplicates(conn, "cycles", NATURAL_KEYS[1][2], note),
    }
    # Orphan layers (their cycle no longer exists).
    if _table_exists(conn, "layers"):
        cur = conn.execute(
            "DELETE FROM layers WHERE cycle_id NOT IN (SELECT cycle_id FROM cycles)"
        )
        removed["orphan_layers"] = cur.rowcount
    conn.commit()
    return removed


def ensure_natural_keys(conn, allow_dedupe: bool = True) -> dict:
    """Create the unique natural-key indexes, collapsing duplicates first.

    A unique index cannot be created over a table that still holds duplicates,
    so ``allow_dedupe=True`` (the default) clears them first and records every
    collapse in ``dedupe_log``. With ``allow_dedupe=False`` the function instead
    reports what *would* be collapsed and raises, letting an operator inspect
    before anything is deleted.
    """
    report = {}
    conn.execute(DEDUPE_LOG_DDL)
    for name, table, cols in NATURAL_KEYS:
        if index_exists(conn, name) or not _table_exists(conn, table):
            report[name] = "already"
            continue
        dupes = _collapse_duplicates(conn, table, cols, note="ensure_natural_keys")
        if dupes and not allow_dedupe:
            raise RuntimeError(
                f"{table}: {dupes} duplicate row(s) must be collapsed before the "
                f"unique index {name} can be created; re-run init_db() (which "
                f"dedupes and logs to dedupe_log) or call dedupe_all() first."
            )
        cols_sql = ", ".join(cols)
        conn.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS {name} ON {table}({cols_sql})")
        report[name] = "created" if not dupes else f"created_after_dropping_{dupes}"
    conn.commit()
    return report


def init_db(conn):
    """建九張表（冪等）＋ copy_sims v1.3.1 四欄遷移（D3 補完：§11.6 avg_win/avg_loss/layers_filtered/monthly_pnl）。"""
    for ddl in DDL:
        conn.execute(ddl)
    # 既有 DB 遷移：CREATE TABLE IF NOT EXISTS 唔會加欄——pragma 檢查後 ALTER（冪等）
    have = {r[1] for r in conn.execute("PRAGMA table_info(copy_sims)")}
    for col, typ in (("layers_filtered", "INTEGER"), ("avg_win", "REAL"),
                     ("avg_loss", "REAL"), ("monthly_pnl", "TEXT")):
        if col not in have:
            conn.execute(f"ALTER TABLE copy_sims ADD COLUMN {col} {typ}")
    # v1.3.2：symbols 加 fx_at_export（L0 導出當日匯率——pipcalc §6.2 修正用）
    have_sym = {r[1] for r in conn.execute("PRAGMA table_info(symbols)")}
    if "fx_at_export" not in have_sym:
        conn.execute("ALTER TABLE symbols ADD COLUMN fx_at_export REAL")
    # v1.3.3（OC 2026-11-24 21:15）：自然鍵唯一索引——冪等入庫的前提。
    ensure_natural_keys(conn)
    conn.commit()
