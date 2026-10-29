# -*- coding: utf-8 -*-
"""COPYTRADE v1.3 D3 沙盒驗證——§11.6 指標集補完（唔使 L0 六指標）。

D2 沙盒（sandbox_timing_test.py）覆蓋 Copy 時機線；本檔覆蓋 matrix 補欄：
  D0  _max_concurrent 層級區間重疊掃描（同刻 close 先 open）
  D1  _recovery_days 月度曲線（多段 DD 取最長；尾部未恢復 censor）
  D2  _monthly_pnl_str compact 串
  D3  schema 遷移：新 DB 四欄＋舊 DB ALTER 補欄（冪等重跑）
  D4  E2E run_matrix（合成 5 cycles）新欄手算對照：avg_win/avg_loss、
      monthly_pnl、max_concurrent、layers_filtered、max_float_loss、recovery_days
  D5  ratio 縮放：M2 config ratio 0.5 → max_float_loss ×2
  D6  blocked 行（M1 無 L0）新欄 None＋est_sl/start_eq 無 regression
"""
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from schema import init_db, DDL                       # noqa: E402
from matrix import (_max_concurrent, _recovery_days, _monthly_pnl_str,  # noqa: E402
                    run_matrix, write_rows, _load_cycles)

PASS = 0
FAIL = 0


def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}")


# ============ D0 _max_concurrent ============
print("D0 _max_concurrent（層級區間重疊掃描）")


def cyc(layers):
    """layers=[(ot, ct, close_known)]——close_known=False 逼 fallback cycle.close_time。"""
    ls = [{"layer_no": i + 1, "open_time": ot, "close_time": ct if ck else None,
           "lots": 0.01 * (i + 1), "net_profit": 10.0}
          for i, (ot, ct, ck) in enumerate(layers)]
    return {"symbol": "EURUSD", "direction": "BUY", "layers": ls,
            "close_time": max((ct for _, ct, ck in layers if ck), default="2026-10-05 12:00")}


c_stack = cyc([("5/10/2026 10:00", "2026-10-05 12:00", True),
               ("5/10/2026 10:30", "2026-10-05 12:00", True),
               ("5/10/2026 11:00", "2026-10-05 12:00", True)])
ok(_max_concurrent([c_stack]) == 3, "三層完全重疊 → 3")

c_seq = cyc([("5/10/2026 09:00", "2026-10-05 10:00", True)])
c_seq2 = cyc([("5/10/2026 10:00", "2026-10-05 11:00", True)])
ok(_max_concurrent([c_seq, c_seq2]) == 1, "同刻 close→open（close 先行）→ 1 無假重疊")

c_fb = cyc([("5/10/2026 14:00", "2026-10-05 15:00", False),
            ("5/10/2026 14:30", "2026-10-05 15:00", False)])
c_fb["close_time"] = "2026-10-05 15:00"
ok(_max_concurrent([c_fb]) == 2, "層 close_time 缺 → fallback cycle.close_time → 2")

c_bad = cyc([("垃圾時間", "2026-10-05 12:00", True)])
ok(_max_concurrent([c_bad]) is None, "時間解析唔到 → 無事件 → None")

# ============ D1 _recovery_days ============
print("D1 _recovery_days（月度曲線；月首對月首日曆日）")
ok(_recovery_days({"2026-01": 100.0, "2026-02": -50.0, "2026-03": 60.0}) == 59,
   "單段 DD：peak 1月→3月恢復 = 59 日")
ok(_recovery_days({"2026-01": 100.0, "2026-02": -50.0}) is None,
   "尾部 DD 未恢復 → censor → None")
ok(_recovery_days({"2026-01": 10.0, "2026-02": 20.0}) is None,
   "全程上升無 DD → None")
two_dd = {"2026-01": 100.0, "2026-02": -50.0, "2026-03": 60.0,
          "2026-04": -80.0, "2026-05": 10.0, "2026-06": 100.0}
ok(_recovery_days(two_dd) == 92, "兩段 DD 取最長：3月 peak→6月恢復 = 92 日")

# ============ D2 _monthly_pnl_str ============
print("D2 _monthly_pnl_str")
ok(_monthly_pnl_str({"2026-01": 10.556, "2026-02": -3.0}) == "2026-01:10.56|2026-02:-3.0",
   "排序＋round 2 位 compact 串（10.556→10.56 明確進位）")
ok(_monthly_pnl_str({}) is None, "空 dict → None")

# ============ D3 schema 遷移 ============
print("D3 schema 四欄遷移（新 DB／舊 DB ALTER）")
conn = sqlite3.connect(":memory:")
init_db(conn)
have = {r[1] for r in conn.execute("PRAGMA table_info(copy_sims)")}
ok({"layers_filtered", "avg_win", "avg_loss", "monthly_pnl"} <= have,
   "新 DB init_db → 四欄齊")
init_db(conn)  # 冪等重跑
have2 = {r[1] for r in conn.execute("PRAGMA table_info(copy_sims)")}
ok(have == have2, "init_db 重跑冪等（唔重複 ALTER）")
conn.close()

conn_old = sqlite3.connect(":memory:")
for ddl in DDL[:-6]:  # 舊版起表（跳過 copy_sims 之後嘅表都照起——淨 copy_sims 用舊 DDL）
    if "copy_sims" in ddl:
        conn_old.execute("""CREATE TABLE copy_sims (
            sim_id INTEGER PRIMARY KEY AUTOINCREMENT,
            signal_id TEXT NOT NULL, symbol TEXT NOT NULL,
            layer_policy TEXT NOT NULL, copy_method TEXT NOT NULL,
            account_type TEXT NOT NULL, cost_scenario TEXT NOT NULL,
            cycles_n INTEGER NOT NULL, trades_filled INTEGER NOT NULL,
            trades_missed INTEGER NOT NULL, gross_pnl REAL NOT NULL,
            net_pnl REAL NOT NULL, win_rate REAL NOT NULL, data_grade TEXT NOT NULL)""")
    else:
        conn_old.execute(ddl)
old_before = {r[1] for r in conn_old.execute("PRAGMA table_info(copy_sims)")}
init_db(conn_old)
old_after = {r[1] for r in conn_old.execute("PRAGMA table_info(copy_sims)")}
ok("layers_filtered" not in old_before and {"layers_filtered", "avg_win", "avg_loss", "monthly_pnl"} <= old_after,
   "舊 DB（舊 DDL）→ init_db ALTER 補四欄")
conn_old.close()

# ============ D4 E2E run_matrix（合成 5 cycles） ============
print("D4 E2E：合成 DB 5 cycles → M2×USD×Ideal 新欄手算對照")
conn = sqlite3.connect(":memory:")
init_db(conn)
# c1 BUY 3層（10月，三層疊住）；c2 BUY 2層（10月）；c3 SELL 1層（同 c2 重疊）；
# c4 BUY 1層（11月）；c5 BUY 1層（12月）
# 層 lots 全 0.01（trades 鍵 open_time 唯一，唔會撞）
LAYERS = {
    "c1": [("5/10/2026 10:00", "2026-10-05 12:00", 0.01, 30.0, -100.0),
           ("5/10/2026 10:30", "2026-10-05 12:00", 0.02, 20.0, -200.0),
           ("5/10/2026 11:00", "2026-10-05 12:00", 0.04, 60.0, -50.0)],
    "c2": [("5/10/2026 14:00", "2026-10-05 15:00", 0.01, -40.0, -80.0),
           ("5/10/2026 14:30", "2026-10-05 15:00", 0.02, 70.0, -30.0)],
    "c3": [("5/10/2026 14:15", "2026-10-05 15:30", 0.01, -25.0, -20.0)],
    "c4": [("5/11/2026 14:00", "2026-11-05 15:00", 0.01, 200.0, -10.0)],
    "c5": [("5/12/2026 14:00", "2026-12-05 15:00", 0.01, 5.0, -5.0)],
}
CYC = {"c1": ("BUY", "5/10/2026 10:00", "2026-10-05 12:00", 3),
       "c2": ("BUY", "5/10/2026 14:00", "2026-10-05 15:00", 2),
       "c3": ("SELL", "5/10/2026 14:15", "2026-10-05 15:30", 1),
       "c4": ("BUY", "5/11/2026 14:00", "2026-11-05 15:00", 1),
       "c5": ("BUY", "5/12/2026 14:00", "2026-12-05 15:00", 1)}
for key, (dr, ot, ct, n) in CYC.items():
    lots_t = round(sum(l[2] for l in LAYERS[key]), 2)
    pnl_t = round(sum(l[3] for l in LAYERS[key]), 2)
    cur = conn.execute(
        "INSERT INTO cycles(signal_id,symbol,direction,open_time,close_time,layers_n,"
        "lots_total,pnl_total,data_grade) VALUES('sb1','EURUSD',?,?,?,?,?,?,'A')",
        (dr, ot, ct, n, lots_t, pnl_t))
    cid = cur.lastrowid
    cum = 0.0
    for i, (lot_, lct, lots, pnl, ml) in enumerate(LAYERS[key], 1):
        cum = round(cum + lots, 2)
        conn.execute("INSERT INTO layers(cycle_id,layer_no,lots,open_time,open_price,pnl,"
                     "lots_cum) VALUES(?,?,?,?,?,?,?)", (cid, i, lots, lot_, 1.0, pnl, cum))
        conn.execute(
            "INSERT INTO trades(signal_id,symbol,typ,lots,open_time,close_time,open_price,"
            "close_price,net_pips,net_profit,max_profit,max_loss,magic,comment,source_file,"
            "source_row,qc_flag) VALUES('sb1','EURUSD',?,?,?,?,?,?,?,?,?,?,NULL,'','sb.csv',?,NULL)",
            (dr.lower(), lots, lot_, lct, 1.0, 2.0, 0.0, pnl, 0.0, ml, i))
conn.commit()

rows = run_matrix(conn, ["sb1"], specs=None, fx_table=None)
write_rows(conn, rows)

target = [r for r in rows if r["copy_method"] == "M2" and r["account_type"] == "USD"
          and r["cost_scenario"] == "Ideal" and r["layer_policy"] == "全層"]
ok(len(target) == 1, "M2×USD×Ideal×全層 得一行")
t = target[0]
# 手算：pnl 序列 [27.5, 7.5, -6.25, 50.0, 1.25]（ratio 0.25、Ideal slip=0 純重放）
ok(t["avg_win"] == 21.56, f"avg_win=21.56（86.25/4 round2）實得 {t['avg_win']}")
ok(t["avg_loss"] == -6.25, f"avg_loss=-6.25 實得 {t['avg_loss']}")
ok(t["monthly_pnl"] == "2026-10:28.75|2026-11:50.0|2026-12:1.25",
   f"monthly_pnl 串實得 {t['monthly_pnl']}")
ok(t["max_concurrent"] == 3, f"max_concurrent=3（c1 三層疊；c2×2+c3 重疊）實得 {t['max_concurrent']}")
ok(t["max_float_loss"] == -87.5, f"max_float_loss=-87.5（c1 MAE 疊加×0.25）實得 {t['max_float_loss']}")
ok(t["recovery_days"] is None, "全程上升無 DD → recovery_days=None")
ok(t["gross_pnl"] == 80.0 and t["win_rate"] == 0.8, "既有欄無 regression（gross 80.0／wr 0.8）")
# §11.5 無 regression：mae p95 手算 41.25（8 層 sorted [1.25..50] k=6.65）
ok(t["est_sl_cost_usd"] == 123.75 and t["suggested_start_equity_usd"] == 371.25,
   f"est_sl/start_eq 無 regression（41.25×3／×3 buffer）實得 {t['est_sl_cost_usd']}/{t['suggested_start_equity_usd']}")

l1 = [r for r in rows if r["copy_method"] == "M2" and r["account_type"] == "USD"
      and r["cost_scenario"] == "Ideal" and r["layer_policy"] == "L1"][0]
ok(l1["layers_filtered"] == 3, f"L1 政策截走 3 層（8 total−5 kept）實得 {l1['layers_filtered']}")
ok(l1["max_concurrent"] == 2, "L1 淨剩每 cycle 頭層：c2×c3 跨向重疊 → 2")

# DB 落庫新欄
db_row = conn.execute(
    "SELECT avg_win, avg_loss, monthly_pnl, max_concurrent, max_float_loss, "
    "recovery_days, layers_filtered FROM copy_sims WHERE copy_method='M2' AND "
    "account_type='USD' AND cost_scenario='Ideal' AND layer_policy='全層'").fetchone()
ok(db_row == (21.56, -6.25, "2026-10:28.75|2026-11:50.0|2026-12:1.25", 3, -87.5, None, 0),
   f"SQLite 落庫新欄齊且值啱 實得 {db_row}")

# ============ D5 ratio 縮放 ============
print("D5 ratio 縮放（config ratio 0.5）")
rows_r = run_matrix(conn, ["sb1"], specs=None, fx_table=None,
                    config={"ratio": 0.5})
t5 = [r for r in rows_r if r["copy_method"] == "M2" and r["account_type"] == "USD"
      and r["cost_scenario"] == "Ideal" and r["layer_policy"] == "全層"][0]
ok(t5["max_float_loss"] == -175.0, f"ratio 0.5 → max_float_loss ×2 = -175.0 實得 {t5['max_float_loss']}")
ok(t5["avg_win"] == 43.12, f"avg_win ×2 = 43.12（86.25×0.5/4 round2）實得 {t5['avg_win']}")

# ============ D6 blocked 行 ============
print("D6 blocked 行（M1 無 L0 §6.7 鐵律 2）")
b = [r for r in rows if r["copy_method"] == "M1" and r["account_type"] == "USD"
     and r["cost_scenario"] == "Ideal" and r["layer_policy"] == "全層"][0]
ok(b["outcome_note"] and b["outcome_note"].startswith("BLOCKED"), "M1 無 L0 → BLOCKED")
ok(b.get("max_concurrent") is None and b.get("layers_filtered") is None
   and b.get("avg_win") is None and b.get("monthly_pnl") is None, "blocked 行新欄全 None（零估算）")

conn.close()

print(f"\n{'=' * 50}")
print(f"D3 沙盒：PASS {PASS}｜FAIL {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
