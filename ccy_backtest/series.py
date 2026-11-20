#!/usr/bin/env python3
"""cp_power_history 序列檔 writer（派工信規格：每 bar 一行 × 9 貨幣＋AVG，帶 timestamp/TF）。"""

from __future__ import annotations

import csv
import os
from typing import List, Optional

from . import universe

HEADER = ["timestamp", "tf"] + [c.lower() for c in universe.CURRENCIES_9] + ["avg"]
HEADER_CSV = ",".join(HEADER)


def write_cp_power_history(rows: List[dict], out_path: str) -> str:
    """rows（core.compute_power_history 輸出）→ CSV。

    欄序：timestamp, tf, eur, usd, jpy, gbp, chf, aud, cad, nzd, xau, avg
    None 值寫空字串（前段 warmup 期／缺料期）。回傳 out_path。
    """
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(HEADER)
        for r in rows:
            line = [r["ts"], r["tf"]]
            for c in universe.CURRENCIES_9:
                v = r["power"][c]
                line.append("" if v is None else f"{v:.6f}")
            a = r["avg"]
            line.append("" if a is None else f"{a:.6f}")
            w.writerow(line)
    return out_path


def read_cp_power_history(path: str) -> List[dict]:
    """回讀（parity 用），欄名照 HEADER。"""
    import csv as _csv
    out = []
    with open(path, encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            rec = {"ts": row["timestamp"], "tf": row["tf"], "power": {}, "avg": None}
            for c in universe.CURRENCIES_9:
                raw = row.get(c.lower(), "")
                rec["power"][c] = float(raw) if raw not in ("", None) else None
            raw = row.get("avg", "")
            rec["avg"] = float(raw) if raw not in ("", None) else None
            out.append(rec)
    return out
