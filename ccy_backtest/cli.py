#!/usr/bin/env python3
"""CP-BT1 命令行入口。

用法（喺 repo 根目錄）：
  python3 -m ccy_backtest.cli run  [--tf D1] [--out ccy_backtest/out/cp_power_history.csv]
                                   [--rsi-period 14] [--atr-period 14]
      用 docs/data/ 內建 D1 JSON 算 cp_power_history（自測 run；parity 源以終端供料為準）
  python3 -m ccy_backtest.cli parity --series <csv> --reader <csv> --out <csv>
      階段 B：誤差矩陣（料未到 → ParityPendingError）
  python3 -m ccy_backtest.cli selftest
      合成數據煙霧測試（單調升市 → USD 段內強弱方向檢查）
"""

from __future__ import annotations

import argparse
import sys

from . import core, dataio, parity, series, universe


def cmd_run(args) -> int:
    universe.validate_universe()
    data = dataio.load_available_repo_instruments(universe.INSTRUMENTS_36, args.tf)
    if not data:
        print("docs/data/ 無可用 instrument 檔", file=sys.stderr)
        return 2
    rows = core.compute_power_history(data, args.tf,
                                      rsi_period=args.rsi_period,
                                      atr_period=args.atr_period)
    out = series.write_cp_power_history(rows, args.out)
    warm = sum(1 for r in rows if r["coverage"] == 0)
    print(f"run: tf={args.tf} instruments_loaded={len(data)} rows={len(rows)}"
          f"（warmup/零覆蓋 {warm} 行）-> {out}")
    tail = rows[-1]
    print("last row:", tail["ts"],
          {c: (None if v is None else round(v, 4)) for c, v in tail["power"].items()},
          "avg=", None if tail["avg"] is None else round(tail["avg"], 4))
    return 0


def cmd_parity(args) -> int:
    rows = series.read_cp_power_history(args.series)
    reader = parity.load_reader_csv(args.reader)
    errs = parity.error_matrix(rows, reader)
    out = parity.write_report(errs, args.out)
    mx = max(r["max_abs"] for r in errs if r["max_abs"] is not None)
    print(f"parity: {len(errs)} timestamps × {len(universe.CURRENCIES_9)}＋AVG"
          f"｜max_abs_err={mx:.6f} -> {out}")
    return 0


def cmd_selftest(_args) -> int:
    """合成數據煙霧測試：三對升市／跌市組合，檢查分解方向。"""
    n = 200
    # EURUSD 持續升（EUR 強 USD 弱）；USDJPY 持續升（USD 強 JPY 弱）
    up = [1.0 + 0.01 * i for i in range(n)]
    data = {
        "EURUSD": {"d": [f"d{i}" for i in range(n)], "o": up, "h": [x + 0.005 for x in up],
                   "l": [x - 0.005 for x in up], "c": up},
        "USDJPY": {"d": [f"d{i}" for i in range(n)], "o": up, "h": [x + 0.005 for x in up],
                   "l": [x - 0.005 for x in up], "c": up},
    }
    rows = core.compute_power_history(data, "D1")
    last = rows[-1]
    checks = [
        ("EUR 強（升市尾段 RSI>50 → raw>0）", (last["power"]["EUR"] or 0) > 0),
        ("USD 對 EURUSD 記負、對 USDJPY 記正，兩筆同 w 相加 → 0", abs(last["power"]["USD"]) < 1e-9),
        ("JPY 弱（raw<0）", (last["power"]["JPY"] or 0) < 0),
        ("只有兩對在場，EUR/JPY N=1、USD N=2", last["n_partners"]["EUR"] == 1
         and last["n_partners"]["USD"] == 2 and last["n_partners"]["JPY"] == 1),
    ]
    ok = True
    for name, passed in checks:
        print(("  PASS  " if passed else "  FAIL  ") + name)
        ok = ok and passed
    return 0 if ok else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="ccy_backtest")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_run = sub.add_parser("run")
    p_run.add_argument("--tf", default="D1")
    p_run.add_argument("--out", default="ccy_backtest/out/cp_power_history_sample.csv")
    p_run.add_argument("--rsi-period", type=int, default=14)
    p_run.add_argument("--atr-period", type=int, default=14)
    p_run.set_defaults(func=cmd_run)

    p_par = sub.add_parser("parity")
    p_par.add_argument("--series", required=True)
    p_par.add_argument("--reader", required=True)
    p_par.add_argument("--out", default="ccy_backtest/out/parity_report.csv")
    p_par.set_defaults(func=cmd_parity)

    p_st = sub.add_parser("selftest")
    p_st.set_defaults(func=cmd_selftest)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
