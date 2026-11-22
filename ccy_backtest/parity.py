#!/usr/bin/env python3
"""階段 B parity 骨架：重建序列 vs ccy_power_reader.csv（A06E 終端面板讀數）誤差表。

派工信驗收要求（20261116_1235／20261119_1325）：
  - parity 報告：≥10 個 timestamp × 9 貨幣誤差矩陣（＋AVG）
  - 目標貼近零；輸出格式固定、可重跑

等料（OC data lane 11-20 12:00 前 notify 通知）：
  1) D1／H4 歷史 OHLC 樣本（終端 history 匯出）
  2) A06E ccy_power_reader.csv 同 timestamp 抽樣
  3) 白皮書 PDF＋已知缺陷清單（假設 A-1..A-7 校準依據）

料未到時跑 parity → ParityPendingError（唔静默扮成功）。
"""

from __future__ import annotations

import csv
import os
from typing import Dict, List

from . import universe

COLUMNS = ["timestamp"] + [c for c in universe.CURRENCIES_9] + ["AVG"]


class ParityPendingError(RuntimeError):
    """parity 前置料未到。"""


def load_reader_csv(path: str) -> Dict[str, Dict[str, float]]:
    """讀 reader 抽樣 CSV → {key: {currency: value}}。

    支援兩種格式：
    - 寬格式（舊）：timestamp + 9 貨幣名欄（EUR USD JPY GBP CHF AUD CAD NZD XAU，
      大小寫不敏感；XAU 可寫 GOLD——自動歸一）；key＝timestamp。
    - 長格式（OC 實供 ccy_power_reader.csv）：
      timestamp,timeframe,ccy1_name,ccy1_power,...,ccy9_name,ccy9_power
      幣名喺資料值內（每行按 power 降序浮動）；key＝"timestamp|TF"
      （TF 空白→淨 timestamp；TF 歸一大寫，D1/H1）。
    """
    if not os.path.exists(path):
        raise ParityPendingError(
            f"reader 抽樣唔存在：{path}（等 OC 供料，notify 通知後再跑）")
    alias = {"GOLD": "XAU"}
    out: Dict[str, Dict[str, float]] = {}
    with open(path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = [fn.strip().lower() if fn else "" for fn in (reader.fieldnames or [])]
        long_fmt = any(fn.startswith("ccy") and fn.endswith("_name") for fn in fieldnames)
        for row in reader:
            ts = (row.get("timestamp") or row.get("date") or row.get("time") or "").strip()
            if not ts:
                continue
            rec = {}
            if long_fmt:
                tf = (row.get("timeframe") or row.get("tf") or "").strip().upper()
                key = f"{ts}|{tf}" if tf else ts
                for i in range(1, 10):
                    name = (row.get(f"ccy{i}_name") or "").strip().upper()
                    val = (row.get(f"ccy{i}_power") or "").strip()
                    cur = alias.get(name, name)
                    if cur in universe.CURRENCIES_9 and val:
                        rec[cur] = float(val)
            else:
                key = ts
                for k, v in row.items():
                    if k is None:
                        continue
                    key_u = k.strip().upper()
                    if key_u in ("TIMESTAMP", "DATE", "TIME", "TF", "AVG"):
                        continue
                    cur = alias.get(key_u, key_u)
                    if cur in universe.CURRENCIES_9 and str(v).strip():
                        rec[cur] = float(v)
            if rec:
                out[key] = rec
    if len(out) < 10:
        raise ParityPendingError(
            f"reader 抽樣得 {len(out)} 個 timestamp（<10），等 OC 全量供料")
    return out


def error_matrix(series_rows: List[dict], reader: Dict[str, Dict[str, float]],
                 scale_fn=None) -> List[dict]:
    """逐 timestamp 對齊算誤差：err = rebuilt − reader。

    scale_fn：None → 假設 rebuilt 已同 reader 同刻度（0..9 映射白皮書到料後接 core.to_display_scale）。
    回傳 rows：[{timestamp, eur, usd, ..., xau, avg, max_abs}]，只列兩邊都有數嘅 ts。
    """
    by_ts = {r["ts"]: r for r in series_rows}
    out = []
    for ts in sorted(reader.keys()):
        r = by_ts.get(ts)
        if r is None:
            continue
        errs = {}
        for cur, ref in reader[ts].items():
            mine = r["power"].get(cur)
            if mine is None:
                continue
            if scale_fn:
                mine = scale_fn(mine)
            errs[cur] = mine - ref
        if not errs:
            continue
        row = {"timestamp": ts}
        row.update({c: errs.get(c) for c in universe.CURRENCIES_9})
        row["avg"] = None if r["avg"] is None else r["avg"]
        absvals = [abs(v) for v in errs.values() if v is not None]
        row["max_abs"] = max(absvals) if absvals else None
        out.append(row)
    if len(out) < 10:
        raise ParityPendingError(
            f"對齊後只得 {len(out)} 個共同 timestamp（<10）——檢查時區／TF 對齊規則")
    return out


def write_report(rows: List[dict], out_path: str) -> str:
    """固定格式誤差表 CSV。"""
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    header = COLUMNS + ["max_abs"]
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for r in rows:
            line = [r["timestamp"]]
            for c in universe.CURRENCIES_9:
                v = r.get(c)
                line.append("" if v is None else f"{v:.6f}")
            line.append("" if r["avg"] is None else f"{r['avg']:.6f}")
            line.append("" if r["max_abs"] is None else f"{r['max_abs']:.6f}")
            w.writerow(line)
    return out_path
