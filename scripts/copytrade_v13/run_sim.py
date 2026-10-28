# -*- coding: utf-8 -*-
"""COPYTRADE v1.3 §11.9 CLI——跑六維矩陣＋落庫＋四份產出。

用法（機房無 L0 亦可跑 B 級重放主體）：
  python run_sim.py --signals 10344,5117
  python run_sim.py --all --out ../../data/copytrade.db
"""
import argparse
import csv
import os
import sqlite3
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from schema import init_db          # noqa: E402
from ingest import ingest, signal_csvs   # noqa: E402
from matrix import run_matrix, write_rows, LAYER_POLICIES, N_GATE  # noqa: E402

SIM_COLS = ["signal_id", "symbol", "layer_policy", "copy_method", "account_type",
            "cost_scenario", "cycles_n", "trades_filled", "trades_missed",
            "gross_pnl", "net_pnl", "win_rate", "profit_factor", "expectancy",
            "monthly_growth", "max_dd", "max_dd_pct", "margin_peak", "margin_ratio",
            "max_concurrent", "max_layer", "max_float_loss", "margin_stop_hit",
            "breach_layer_no", "stable_month_ratio", "worst_month", "max_consec_losses",
            "recovery_days", "concentration", "est_sl_cost_usd", "est_margin_peak_usd",
            "suggested_start_equity_usd", "risk_adj_score", "data_grade", "outcome_note"]

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DL = os.path.join(REPO, "docs", "downloads")


def layer_freq_matrix(conn, signals):
    """§11.3 層數勝率×頻率矩陣（cycle 級，原始美元）。"""
    out = []
    for sid in signals:
        for row in conn.execute(
                "SELECT symbol, cycle_id, direction, layers_n, pnl_total, close_time "
                "FROM cycles WHERE signal_id=?", (sid,)):
            pass  # cycles 逐層計——用 layers 表重聚合
    by = defaultdict(lambda: {"wins": 0, "n": 0, "pnl": 0.0})
    for row in conn.execute(
            "SELECT c.signal_id, c.symbol, c.layers_n, c.pnl_total FROM cycles c "
            "WHERE c.signal_id IN (%s)" % ",".join("?" * len(signals)), signals):
        for pol_name, pol_n in LAYER_POLICIES:
            if pol_n is None or row[2] <= pol_n:
                k = (row[0], row[1], pol_name)
                by[k]["n"] += 1
                by[k]["pnl"] += row[3]
                if row[3] > 0:
                    by[k]["wins"] += 1
    for (sid, sym, pol), v in sorted(by.items()):
        out.append({"signal_id": sid, "symbol": sym, "layer_policy": pol,
                    "cycles": v["n"], "win_rate": round(v["wins"] / v["n"], 4) if v["n"] else 0,
                    "pnl_usd": round(v["pnl"], 2)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", help="逗號分隔 signal id；--all 用全部")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default=os.path.join(REPO, "data", "copytrade.db"))
    ap.add_argument("--report-dir", default=os.path.join(REPO, "data", "copytrade"))
    ap.add_argument("--db-reset", action="store_true")
    args = ap.parse_args()

    signals = None
    if not args.all:
        if not args.signals:
            ap.error("要 --signals 或 --all")
        signals = [s.strip() for s in args.signals.split(",") if s.strip()]

    paths = signal_csvs(DL, signals)
    if not paths:
        print("❌ 無 CSV")
        sys.exit(1)

    if args.db_reset and os.path.exists(args.out):
        os.remove(args.out)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    os.makedirs(args.report_dir, exist_ok=True)
    conn = sqlite3.connect(args.out)
    init_db(conn)

    n_tr, n_cy, n_ly = ingest(conn, paths)  # 機房無 L0 specs → 未跑兩式交叉驗證
    print(f"✅ 入庫：trades {n_tr}／cycles {n_cy}／layers {n_ly}")

    sids = sorted({os.path.basename(p).split("-")[-1].replace(".csv", "") for p in paths})
    rows = run_matrix(conn, sids, specs=None, fx_table=None)  # L0 到位後解鎖 M1/M4/cent
    write_rows(conn, rows)
    print(f"✅ copy_sims {len(rows)} 行（六維矩陣）")

    # §11.9 四份產出
    with open(os.path.join(args.report_dir, "detailed_analysis.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SIM_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    rank = [r for r in rows if r["risk_adj_score"] is not None]
    rank.sort(key=lambda r: -r["risk_adj_score"])
    for i, r in enumerate(rank):
        r["rank"] = i + 1
        r["verdict"] = ("優先" if i < len(rank) * 0.15
                        else "可研究" if i < len(rank) * 0.5 else "不建議")
    with open(os.path.join(args.report_dir, "decision_ranking.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["rank", "verdict"] + SIM_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rank)

    lfm = layer_freq_matrix(conn, sids)
    with open(os.path.join(args.report_dir, "layer_win_freq_matrix.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lfm[0].keys()))
        w.writeheader()
        w.writerows(lfm)

    with open(os.path.join(args.report_dir, "mfe_risk_report.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["signal_id", "symbol", "layer_policy",
                                          "est_sl_cost_usd", "est_margin_peak_usd",
                                          "suggested_start_equity_usd"])
        w.writeheader()
        seen = set()
        for r in sorted(rows, key=lambda x: x.get("est_sl_cost_usd") is None):
            k = (r["signal_id"], r["symbol"], r["layer_policy"])
            if k not in seen and r.get("est_sl_cost_usd") is not None:
                seen.add(k)
                w.writerow({k2: r.get(k2) for k2 in w.fieldnames})

    blocked = sum(1 for r in rows if r["outcome_note"] and r["outcome_note"].startswith("BLOCKED"))
    gated = sum(1 for r in rows if r["outcome_note"] == "樣本不足")
    print(f"✅ 四份產出 → {args.report_dir}")
    print(f"   blocked（需 L0）{blocked}｜樣本不足（N<{N_GATE}）{gated}｜可排名 {len(rank)}")
    conn.close()


if __name__ == "__main__":
    main()
