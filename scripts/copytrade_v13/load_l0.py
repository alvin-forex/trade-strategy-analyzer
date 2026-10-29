# -*- coding: utf-8 -*-
"""L0 JSON → symbols 表（ExportSymbolsL0.mq5 產物入庫——催辦①解鎖鏈配套）。

用法：
  python3 load_l0.py --l0-json l0_symbols.json          # 默認 data/copytrade.db
  python3 load_l0.py --l0-json l0_symbols.json --db …

L0 到位後全鏈：
  1. MT5 生產機跑 ExportSymbolsL0.mq5 → l0_symbols.json（交信道）
  2. 本檔入庫（symbols 表＋fx_at_export 注入——pipcalc §6.2 修正匯率成分）
  3. python3 run_sim.py --all --db-reset               # M1/M4/M5/cent/Realistic/Stress 全解鎖
     （另 export_hst.py --tf 5 出 M5 → --timing-only 重跑 Copy 時機全量）
"""
import argparse
import json
import os
import sqlite3
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from schema import init_db  # noqa: E402

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def load_l0(conn, path):
    """l0_symbols.json → symbols 表（INSERT OR REPLACE 冪等重跑）。

    fx_at_export（貨幣級）→ symbol 級：取 quote_currency 對應匯率。
    USD 報價 symbol 唯一權威式唔使 fx——照存（nullable 欄，USD 行 NULL 冇影響）。
    """
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    fx = d.get("fx_at_export") or {}
    n = 0
    for s in d["symbols"]:
        fx_ref = fx.get(s["quote_currency"])
        conn.execute(
            "INSERT OR REPLACE INTO symbols(symbol,pip_size,tick_size,tick_value,"
            "contract_size,quote_currency,margin_initial,fx_at_export,exported_at,source)"
            " VALUES(?,?,?,?,?,?,?,?,?,?)",
            (s["symbol"], s["pip_size"], s["tick_size"], s["tick_value"],
             s["contract_size"], s["quote_currency"], s.get("margin_initial"),
             fx_ref, d["exported_at"], d.get("source", "MT5 SymbolInfoDouble")))
        n += 1
    conn.commit()
    return n, len(fx), d.get("skipped_zero_spec", "")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--l0-json", required=True, help="ExportSymbolsL0.mq5 產物 l0_symbols.json")
    ap.add_argument("--db", default=os.path.join(REPO, "data", "copytrade.db"))
    args = ap.parse_args()
    conn = sqlite3.connect(args.db)
    init_db(conn)  # 冪等（含 v1.3.2 fx_at_export 欄遷移）
    n, n_fx, skipped = load_l0(conn, args.l0_json)
    non_usd = conn.execute(
        "SELECT COUNT(*) FROM symbols WHERE quote_currency != 'USD' "
        "AND fx_at_export IS NULL").fetchone()[0]
    print(f"✅ L0 入庫：{n} symbols＋{n_fx} fx 匯率 → {args.db}")
    if skipped:
        print(f"   零規格跳過（MT5 側已記）：{skipped}")
    if non_usd:
        print(f"   ⚠️ {non_usd} 個非 USD 報價 symbol 無 fx——pipcalc 將 MissingFx→BLOCKED（零估算）")
    conn.close()


if __name__ == "__main__":
    main()
