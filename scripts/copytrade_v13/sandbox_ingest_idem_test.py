# -*- coding: utf-8 -*-
"""COPYTRADE v1.3.3 入庫冪等驗證（OC 派工 2026-11-24 21:15）。

覆蓋三件 OC 明確要求、而之前完全冇測嘅事：

  I1  同一份 CSV 連跑兩次，trades／cycles／layers 行數**唔會翻倍**
  I2  舊（無索引）DB 遷移：`init_db()` 自動剔重、建唯一索引、留 dedupe_log
  I3  `ensure_natural_keys(allow_dedupe=False)` 遇到重複會**拒絕**而唔係靜靜刪

用真 CSV（`downloads/forex-forest-signals-page-*.csv`）而唔係合成數據：
強制 CSV 缺欄位嗰陣要 skip 而唔係報紅，因為呢個測試要跟 CI 環境一齊跑。

    python scripts/copytrade_v13/sandbox_ingest_idem_test.py
"""
import glob
import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from schema import DDL, ensure_natural_keys, init_db       # noqa: E402
from ingest import group_cycles, ingest, load_signal_csv    # noqa: E402

REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DL_CANDIDATES = [
    os.path.join(REPO, "downloads"),
    os.path.join(REPO, "docs", "downloads"),
]

PASS = 0
FAIL = 0


def _check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"[PASS] {name}")
    else:
        FAIL += 1
        print(f"[FAIL] {name}  {detail}")


def _sample_csv():
    for d in DL_CANDIDATES:
        files = sorted(glob.glob(os.path.join(d, "forex-forest-signals-page-*.csv")))
        if files:
            return files[0]
    return None


def _fresh_db():
    path = os.path.join(tempfile.mkdtemp(), "ct.db")
    conn = sqlite3.connect(path)
    init_db(conn)
    return conn


def _counts(conn):
    return (
        conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0],
        conn.execute("SELECT COUNT(*) FROM cycles").fetchone()[0],
        conn.execute("SELECT COUNT(*) FROM layers").fetchone()[0],
    )


def test_reingest_is_idempotent(csv_path):
    """I1 — the exact failure OC found: 271 rows became 542 on a second run."""
    conn = _fresh_db()
    n1 = _counts(conn)
    ingest(conn, [csv_path])
    n2 = _counts(conn)
    ingest(conn, [csv_path])
    n3 = _counts(conn)
    ingest(conn, [csv_path])
    n4 = _counts(conn)
    _check("I1a first ingest inserts rows", n2[0] > n1[0], f"{n1} -> {n2}")
    _check("I1b second ingest does not grow", n3 == n2, f"{n2} -> {n3}")
    _check("I1c third ingest does not grow", n4 == n2, f"{n2} -> {n4}")
    _check(
        "I1d cycles stable too",
        n3[1] == n2[1] and n4[1] == n2[1],
        f"cycles {n2[1]} -> {n3[1]} -> {n4[1]}",
    )
    conn.close()


def test_legacy_db_migration(csv_path):
    """I2 — a dirty legacy DB must be cleaned, indexed, and audited."""
    path = os.path.join(tempfile.mkdtemp(), "legacy.db")
    conn = sqlite3.connect(path)
    for ddl in DDL:
        conn.execute(ddl)

    trades = load_signal_csv(csv_path)
    cols = (
        "signal_id,symbol,typ,lots,open_time,close_time,open_price,close_price,"
        "net_pips,net_profit,max_profit,max_loss,magic,comment,source_file,"
        "source_row,qc_flag"
    )
    values = "?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?"
    rows = [
        (t["signal_id"], t["symbol"], t["typ"], t["lots"], t["open_time"],
         t["close_time"], t["open_price"], t["close_price"], t["net_pips"],
         t["net_profit"], t["max_profit"], t["max_loss"], t["magic"],
         t["comment"], t["source_file"], t["source_row"], None)
        for t in trades
    ]
    conn.executemany(f"INSERT INTO trades({cols}) VALUES({values})", rows * 2)
    cycles = group_cycles(trades)
    conn.executemany(
        "INSERT INTO cycles(signal_id,symbol,direction,open_time,close_time,"
        "layers_n,lots_total,pnl_total,data_grade) VALUES(?,?,?,?,?,?,?,?,?)",
        [(c["signal_id"], c["symbol"], c["direction"], c["open_time"],
          c["close_time"], c["layers_n"], c["lots_total"], c["pnl_total"],
          c["data_grade"]) for c in cycles] * 2,
    )
    conn.commit()
    dirty = _counts(conn)
    _check("I2a legacy DB starts dirty", dirty[0] == len(trades) * 2, str(dirty))

    init_db(conn)
    clean = _counts(conn)
    _check(
        "I2b init_db collapses duplicates",
        clean[0] == len(trades) and clean[1] == len(cycles),
        f"{dirty} -> {clean}",
    )
    idx = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name LIKE 'ux_%'")]
    _check("I2c unique indexes created", len(idx) == 2, str(idx))
    log = conn.execute("SELECT COUNT(*) FROM dedupe_log").fetchone()[0]
    _check("I2d dedupe audited", log >= 1, f"dedupe_log rows={log}")

    init_db(conn)
    log2 = conn.execute("SELECT COUNT(*) FROM dedupe_log").fetchone()[0]
    _check("I2e re-init is a no-op", log2 == log, f"{log} -> {log2}")

    ingest(conn, [csv_path])
    after = _counts(conn)
    # The legacy fixture never had layers rows, so layers legitimately fills in
    # here; trades and cycles must not move.
    _check(
        "I2f ingest after migration adds no trades/cycles",
        after[0] == clean[0] and after[1] == clean[1],
        f"clean={clean} after={after}",
    )
    conn.close()


def test_refuses_silent_delete(csv_path):
    """I3 — allow_dedupe=False must refuse rather than quietly delete."""
    path = os.path.join(tempfile.mkdtemp(), "refuse.db")
    conn = sqlite3.connect(path)
    for ddl in DDL:
        conn.execute(ddl)
    cols = (
        "signal_id,symbol,typ,lots,open_time,close_time,open_price,close_price,"
        "net_pips,net_profit,max_profit,max_loss,magic,comment,source_file,"
        "source_row,qc_flag"
    )
    values = "?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?"
    dup = ("s", "X", "buy", 0.1, "o", "c", 1, 1, 1, 1, 1, 1, "", "", "f", 0, None)
    conn.execute(f"INSERT INTO trades({cols}) VALUES({values})", dup)
    conn.execute(f"INSERT INTO trades({cols}) VALUES({values})", dup)
    conn.commit()
    raised = False
    try:
        ensure_natural_keys(conn, allow_dedupe=False)
    except RuntimeError:
        raised = True
    _check("I3 refuses to delete silently", raised)
    conn.close()


def test_natural_key_excludes_source_row(csv_path):
    """Keying on source_row would treat a shifted re-export as brand-new rows."""
    cols = (
        "signal_id,symbol,typ,lots,open_time,close_time,open_price,close_price,"
        "net_pips,net_profit,max_profit,max_loss,magic,comment,source_file,"
        "source_row,qc_flag"
    )
    values = "?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?"
    conn = _fresh_db()
    t = load_signal_csv(csv_path)[0]
    base = (t["signal_id"], t["symbol"], t["typ"], t["lots"], t["open_time"],
            t["close_time"], t["open_price"], t["close_price"], t["net_pips"],
            t["net_profit"], t["max_profit"], t["max_loss"], t["magic"],
            t["comment"], "old.csv", t["source_row"], None)
    shifted = base[:-3] + ("new.csv", t["source_row"] + 100, None)
    conn.execute(f"INSERT INTO trades({cols}) VALUES({values})", base)
    # A shifted re-export must UPDATE, not raise and not insert. Using the
    # upsert form (same statement ingest() uses) is the thing being tested.
    conn.execute(
        f"INSERT INTO trades({cols}) VALUES({values}) "
        "ON CONFLICT(signal_id,symbol,typ,lots,open_time,close_time,open_price,"
        "close_price,net_pips,net_profit,max_profit,max_loss,magic,comment) "
        "DO UPDATE SET source_file=excluded.source_file, source_row=excluded.source_row,"
        " qc_flag=excluded.qc_flag",
        shifted,
    )
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM trades").fetchone()[0]
    _check("I4 shifted re-export does not duplicate", n == 1, f"rows={n}")
    sf = conn.execute("SELECT source_file, source_row FROM trades").fetchone()
    _check("I4b latest provenance wins", sf == ("new.csv", t["source_row"] + 100), str(sf))
    conn.close()


def main():
    csv_path = _sample_csv()
    if not csv_path:
        print("[SKIP] no forex-forest-signals CSV present (CI without downloads/)")
        return 0
    print(f"sample CSV: {os.path.relpath(csv_path, REPO)}")
    test_reingest_is_idempotent(csv_path)
    test_legacy_db_migration(csv_path)
    test_refuses_silent_delete(csv_path)
    test_natural_key_excludes_source_row(csv_path)
    print(f"\nPASS={PASS} FAIL={FAIL}")
    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
