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
from matrix import run_matrix, write_rows, LAYER_POLICIES, N_GATE, _load_cycles  # noqa: E402
from copy_timing import (simulate_timing_all, summarize_timing,  # noqa: E402
                         load_m5_json)

SIM_COLS = ["signal_id", "symbol", "layer_policy", "copy_method", "account_type",
            "cost_scenario", "cycles_n", "trades_filled", "trades_missed",
            "layers_filtered",
            "gross_pnl", "net_pnl", "win_rate", "profit_factor", "expectancy",
            "avg_win", "avg_loss", "monthly_growth", "monthly_pnl",
            "max_dd", "max_dd_pct", "margin_peak", "margin_ratio",
            "max_concurrent", "max_layer", "max_float_loss", "margin_stop_hit",
            "breach_layer_no", "stable_month_ratio", "worst_month", "max_consec_losses",
            "recovery_days", "concentration", "est_sl_cost_usd", "est_margin_peak_usd",
            "suggested_start_equity_usd", "risk_adj_score", "data_grade", "outcome_note"]

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DL = os.path.join(REPO, "docs", "downloads")


def layer_freq_matrix(conn, signals):
    """§11.3 層數勝率×頻率矩陣（cycle 級，原始美元）＋單層回報（③先計單層回報）。"""
    out = []
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
                    "pnl_usd": round(v["pnl"], 2),
                    "pnl_per_cycle": round(v["pnl"] / v["n"], 2) if v["n"] else 0})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", help="逗號分隔 signal id；--all 用全部")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--out", default=os.path.join(REPO, "data", "copytrade.db"))
    ap.add_argument("--report-dir", default=os.path.join(REPO, "data", "copytrade"))
    ap.add_argument("--db-reset", action="store_true")
    ap.add_argument("--timing", action="store_true",
                    help="D2 Copy 時機掃描（v1.2 merge）：wait 網格 FILLED/MISSED（需 M5 JSON＋L0）")
    ap.add_argument("--timing-only", action="store_true",
                    help="只跑 timing 掃描出第五產出（唔入庫唔重跑矩陣——M5 導出後單獨重跑用）")
    ap.add_argument("--m5-dir", default=os.path.join(REPO, "docs", "data"),
                    help="M5 JSON 目錄（export_hst.py v2 --tf 5 出嘅 {PAIR}_M5.json）")
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

    if args.timing_only:
        # D2 增量場景：M5 導出後只重跑 timing 掃描（DB 已入庫，唔重複 ingest／矩陣）
        sids = [s.strip() for s in (args.signals or "").split(",") if s.strip()] \
            if not args.all else None
        if sids is None:
            sids = sorted({os.path.basename(p).split("-")[-1].replace(".csv", "")
                           for p in signal_csvs(DL, None)})
        _run_timing(conn, sids, args)
        conn.close()
        return

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
    conc = max((r.get("max_concurrent") or 0) for r in rows) if rows else 0
    rec = [r["recovery_days"] for r in rows if r.get("recovery_days") is not None]
    print(f"✅ 四份產出 → {args.report_dir}")
    print(f"   blocked（需 L0）{blocked}｜樣本不足（N<{N_GATE}）{gated}｜可排名 {len(rank)}")
    print(f"   D3 補欄：最大同時持倉 peak {conc}｜recovery_days 有值行 "
          f"{len(rec)}/{len(rows)}（最長 {max(rec) if rec else '—'} 日）")

    if args.timing:
        _run_timing(conn, sids, args)
    conn.close()


def _run_timing(conn, sids, args):
    """D2 第五份產出：Copy 時機掃描（v1.2 merge）——--timing／--timing-only 共用。"""
    m5_dir = args.m5_dir
    cache = {}

    def m5_loader(sym):
        if sym in cache:
            return cache[sym]
        p = os.path.join(m5_dir, f"{sym}_M5.json")
        bars = load_m5_json(p) if os.path.exists(p) else None
        cache[sym] = bars
        return bars

    # L0 唯一權威（§6.2）：有 symbols 表先行權威鏈；無 → specs=None 每行 BLOCKED（零估算）
    specs = None
    if conn.execute("SELECT COUNT(*) FROM symbols").fetchone()[0] > 0:
        specs = {r[0]: {"pip_size": r[1], "tick_size": r[2], "tick_value": r[3],
                        "contract_size": r[4], "quote_currency": r[5],
                        "margin_initial": r[6], "fx_at_export": r[7]}
                 for r in conn.execute(
                     "SELECT symbol, pip_size, tick_size, tick_value, contract_size, "
                     "quote_currency, margin_initial, fx_at_export FROM symbols")}
        # fx_at_export 由 load_l0.py 注入（ExportSymbolsL0.mq5 導出當日匯率）；
        # 缺——非 USD 報價將 raise MissingFx→BLOCKED（鐵律 2，正確行為）

    per_sid, all_rows = {}, []
    for sid in sids:
        rows_sid = simulate_timing_all(_load_cycles(conn, sid), specs=specs,
                                       fx_table=None, m5_loader=m5_loader)
        per_sid[sid] = rows_sid
        all_rows.extend(rows_sid)
    with open(os.path.join(args.report_dir, "copy_timing_scan.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["signal_id", "symbol", "sim_type",
                                          "wait_pips", "cycles", "filled", "missed",
                                          "blocked", "fill_rate", "total_pnl_usd",
                                          "avg_pnl_usd", "win_rate", "avg_pips"])
        w.writeheader()
        for sid in sids:
            for s in summarize_timing(per_sid[sid]):
                s["signal_id"] = sid
                w.writerow({k: s.get(k) for k in w.fieldnames})
    n_f = sum(1 for r in all_rows if r.get("outcome") == "FILLED")
    n_m = sum(1 for r in all_rows if r.get("outcome") == "MISSED")
    n_b = sum(1 for r in all_rows if r.get("outcome") in ("BLOCKED", "NO_M5_DATA"))
    print("✅ 第五份產出 copy_timing_scan.csv（D2 v1.2 merge）")
    print(f"   timing 行 {len(all_rows)}｜FILLED {n_f}｜MISSED {n_m}｜"
          f"blocked/no-M5 {n_b}（L0＋M5 導出後重跑即解鎖）")


if __name__ == "__main__":
    main()
