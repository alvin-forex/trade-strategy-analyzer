#!/usr/bin/env python3
"""CP-BT1 階段 B parity runner：OHLC 窗口 → mt4_ref 重算 → reader 對齊 → 誤差矩陣。

用法：
  python3 -m ccy_backtest.runner [--ref-root ccy_backtest/ref] [--out out/]
料源：ref/ohlc/ 內台方供料（格式照 ohlc_sampling_list.md 第三節，load_ohlc_csv 寬容匹配）。
抽樣：ref/ohlc_sampling_list.csv（28 時點；2011 兩點自動跳過——資料端無 2011 OHLC）。
對齊：reader key＝"timestamp|TF"（timestamp 格式 "YYYY.MM.DD HH:MM" 同 MT4 原生一致）。
刻度：reader 0..9 vs kernel 50±——映射公式等 OC 供 A06E 資訊後鎖定；目前
      output 同時列 raw kernel 值與 (pw−50)+4.5 試映射（X=1 假設版）供誤差走向判讀，
      唔作最終判定（最終刻度以 OC 答覆為準，唔静默假設）。
"""
from __future__ import annotations

import csv
import glob
import os
import sys
from typing import Dict, List, Optional

from . import dataio, indicators, mt4_ref, parity, universe

N_BARS = 350
REF_ROOT_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ref")


def load_sampling_list(path: str) -> List[dict]:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append({"idx": int(r["idx"]), "ts": r["timestamp"].strip(),
                         "tf": r["timeframe"].strip().upper(), "reason": r["reason"]})
    return rows


def load_ohlc_dir(ohlc_dir: str) -> Dict[str, dict]:
    """掃 ref/ohlc/ 內全部檔案 → {INSTRUMENT: {TF: series}}（兩種佈局兼容）。

    佈局 A（每 instrument 一檔）：*EURUSD_H1_350bars.csv* → {EURUSD: {H1: series}}
    佈局 B（每時點一檔）：檔名含 timestamp → 合併為 per-instrument 全序列再切窗。
    檔名規則寬鬆：以底線分節，從中識別 INSTRUMENT（28+XAUUSD 詞表）與 TF 詞。
    """
    insts = set(universe.INSTRUMENTS_36) | {"XAUUSD"}
    tfs = {"D1", "H4", "H1", "M30", "M5", "M1"}
    out: Dict[str, Dict[str, dict]] = {}
    for path in sorted(glob.glob(os.path.join(ohlc_dir, "**", "*.csv"), recursive=True)):
        base = os.path.basename(path)
        inst = next((i for i in sorted(insts, key=len, reverse=True)
                     if i.upper() in base.upper()), None)
        tf = next((t for t in sorted(tfs, key=len, reverse=True)
                   if f"_{t}_" in base.upper() or base.upper().endswith(f"_{t}.csv")
                   or f"_{t}-" in base.upper()), None)
        if inst is None or tf is None:
            print(f"  [skip] 檔名無法識別 instrument/TF: {base}")
            continue
        try:
            series = dataio.load_ohlc_csv(path)
        except Exception as e:
            print(f"  [skip] 載入失敗 {base}: {e}")
            continue
        out.setdefault(inst, {})
        if tf in out[inst]:
            # 同 instrument 同 TF 多檔（每時點一檔佈局）→ 按 d 值合併去重排序
            m = out[inst][tf]
            seen = {d: i for i, d in enumerate(m["d"])}
            for j, d in enumerate(series["d"]):
                if d not in seen:
                    m["d"].append(d)
                    for k in ("o", "h", "l", "c"):
                        m[k].append(series[k][j])
                else:
                    i2 = seen[d]
                    for k in ("o", "h", "l", "c"):
                        m[k][i2] = series[k][j]
            order = sorted(range(len(m["d"])), key=lambda i: m["d"][i])
            for k in ("d", "o", "h", "l", "c"):
                m[k] = [m[k][i] for i in order]
        else:
            out[inst][tf] = series
    return out


def slice_window(series: dict, ts: str, n: int = N_BARS) -> Optional[dict]:
    """由 series 切「timestamp（含）向前 n 根」窗口；d 值字串前綴匹配（日期含時分）。"""
    d = series["d"]
    # 精確匹配 → 前綴匹配（reader "2026.11.20 23:53" vs bar "2026.11.20 23:53"）
    cand = [i for i, x in enumerate(d) if x.strip() == ts]
    if not cand:
        cand = [i for i, x in enumerate(d) if str(x).strip().startswith(ts[:16])]
    if not cand:
        return None
    i = max(cand)
    lo = max(0, i - n + 1)
    return {k: v[lo:i + 1] for k, v in series.items()}


def run_parity(ref_root: str = REF_ROOT_DEFAULT, out_dir: str = None,
               ohlc_dir: str = None) -> str:
    ohlc_dir = ohlc_dir or os.path.join(ref_root, "ohlc")
    out_dir = out_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    if not os.path.isdir(ohlc_dir):
        raise parity.ParityPendingError(
            f"ref/ohlc/ 未出現（{ohlc_dir}）——OHLC 供料未到，唔静默扮成功")
    samples = load_sampling_list(os.path.join(ref_root, "ohlc_sampling_list.csv"))
    reader = parity.load_reader_csv(os.path.join(ref_root, "ccy_power_reader.csv"))
    # 2011 兩點資料端無源（OC 1445 確認 MT4 端無料即跳過）
    active = [s for s in samples if not s["ts"].startswith("2011")]

    all_data = load_ohlc_dir(ohlc_dir)
    if not all_data:
        raise parity.ParityPendingError("ohlc/ 有檔但零載入——檔名佈局唔合規，補 runner 相容")

    fake_rows: List[dict] = []
    skipped: List[str] = []
    for s in active:
        key = f"{s['ts']}|{s['tf']}"
        if key not in reader:
            print(f"  [warn] reader 無此 key: {key}")
            continue
        tf = s["tf"]
        # 該 TF 可用 instrument
        usable = {i: v for i, v in all_data.items() if tf in v}
        if not usable:
            print(f"  [warn] {key}：無 {tf} OHLC，跳過")
            continue
        # 每 instrument 該時點窗口的 RSI/ATR% 尾值 → mt4_ref 單 bar 計算
        rsi_by, atr_by = {}, {}
        for inst, tfs in usable.items():
            win = slice_window(tfs[tf], s["ts"])
            if win is None or len(win["c"]) < 15:
                continue  # RSI 暖機最少需求
            r = indicators.rsi_wilder(win["c"], 14)
            atr = indicators.atr_wilder(win["h"], win["l"], win["c"], 14)
            i_last = len(win["c"]) - 1
            rv = r[i_last] if i_last < len(r) else None
            av = atr[i_last] if i_last < len(atr) else None
            px = win["c"][i_last]
            if rv is not None and av is not None and av > 0 and px > 0:
                rsi_by[inst] = rv
                atr_by[inst] = av / px * 100.0
        if len(rsi_by) < 20:
            print(f"  [warn] {key}：有效 instrument 只 {len(rsi_by)}/29——coverage 低，行為異常")
        pw = mt4_ref.calc_pw_row(rsi_by, atr_by, list(universe.INSTRUMENTS_36))
        # 0..9 刻度：X 未知（等 OC）——輸出 (pw−50)+4.5 假設版＋raw，誤差走向判讀用
        scale_guess = {k: (v - 50.0) + 4.5 for k, v in pw.items()}
        fake_rows.append({"ts": key, "power": scale_guess, "avg": None})
        # 詳細 log
        r_row = reader[key]
        diffs = {k: round(scale_guess[k] - r_row[k], 4)
                 for k in universe.CURRENCIES_9 if k in r_row and k in scale_guess}
        print(f"  {key}: instruments={len(rsi_by)} | guess-scale 誤差 = {diffs}")

    if not fake_rows:
        raise parity.ParityPendingError("零對齊行——檢查 reader key 格式／時戳精確匹配")
    report_rows = parity.error_matrix(fake_rows, reader, scale_fn=None)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "parity_report.csv")
    parity.write_report(report_rows, out_path)
    print(f"parity 報告（guess-scale 版，{len(report_rows)} 行）→ {out_path}")
    return out_path


if __name__ == "__main__":
    argv = sys.argv[1:]
    ref_root = argv[0] if argv else REF_ROOT_DEFAULT
    try:
        run_parity(ref_root)
    except parity.ParityPendingError as e:
        print(f"PENDING: {e}")
        sys.exit(2)
