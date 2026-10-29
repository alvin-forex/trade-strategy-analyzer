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
    conn.commit()
