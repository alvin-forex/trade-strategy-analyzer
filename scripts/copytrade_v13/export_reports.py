# -*- coding: utf-8 -*-
"""COPYTRADE v1.3 §11.9 產出導出——由 copy_sims DB 全量出（D4 分批入庫後用）。

分批入庫時 run_sim 每批覆蓋 CSV（rows 淨係該批）→ 最後用本檔由 DB 一次過
出齊四份產出（decision_ranking 嘅 rank／verdict 需全量重排，分批出唔到）。

用法：
  python3 export_reports.py                    # 默認 data/copytrade.db → data/copytrade/
  python3 export_reports.py --db … --report-dir …
"""
import argparse
import csv
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from run_sim import SIM_COLS, layer_freq_matrix  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=os.path.join(REPO, "data", "copytrade.db"))
    ap.add_argument("--report-dir", default=os.path.join(REPO, "data", "copytrade"))
    args = ap.parse_args()
    os.makedirs(args.report_dir, exist_ok=True)
    conn = sqlite3.connect(args.db)

    rows = [dict(zip(SIM_COLS, r)) for r in conn.execute(
        "SELECT " + ",".join(SIM_COLS) + " FROM copy_sims")]
    if not rows:
        print("❌ copy_sims 空")
        sys.exit(1)

    # 1. 詳細分析表
    with open(os.path.join(args.report_dir, "detailed_analysis.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=SIM_COLS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    # 2. 決策排名表（全量 rank＋verdict）
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

    # 3. 層數勝率×頻率矩陣（全 signals）
    sids = [r[0] for r in conn.execute("SELECT DISTINCT signal_id FROM cycles ORDER BY signal_id")]
    lfm = layer_freq_matrix(conn, sids)
    with open(os.path.join(args.report_dir, "layer_win_freq_matrix.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(lfm[0].keys()) if lfm
                           else ["signal_id", "symbol", "layer_policy", "cycles",
                                 "win_rate", "pnl_usd", "pnl_per_cycle"])
        w.writeheader()
        w.writerows(lfm)

    # 4. MFE 風險報告
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

    blocked = sum(1 for r in rows if r["outcome_note"] and str(r["outcome_note"]).startswith("BLOCKED"))
    gated = sum(1 for r in rows if r["outcome_note"] == "樣本不足")
    print(f"✅ 四份產出 → {args.report_dir}（由 DB {len(rows):,} 行全量導出）")
    print(f"   blocked（需 L0）{blocked:,}｜樣本不足 {gated:,}｜可排名 {len(rank):,}｜signals {len(sids)}")


if __name__ == "__main__":
    main()
