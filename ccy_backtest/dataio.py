#!/usr/bin/env python3
"""資料載入：docs/data/*_TF.json（repo 內建）＋通用 OHLC CSV（OC 終端供料用）。"""

from __future__ import annotations

import csv
import json
import os
from typing import Dict, List

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(REPO_ROOT, "docs", "data")


def load_repo_json(symbol: str, tf: str = "D1",
                   data_dir: str = None) -> dict:
    """讀 docs/data/{SYM}_{TF}.json → {"d","o","h","l","c"} bars 結構。

    repo 格式：{"symbol","timeframe","start","end","count","bars":[{"d","o","h","l","c","v"}]}
    """
    dd = data_dir or DATA_DIR
    path = os.path.join(dd, f"{symbol.upper()}_{tf.upper()}.json")
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    bars = raw["bars"]
    return {
        "d": [b["d"] for b in bars],
        "o": [float(b["o"]) for b in bars],
        "h": [float(b["h"]) for b in bars],
        "l": [float(b["l"]) for b in bars],
        "c": [float(b["c"]) for b in bars],
    }


def load_available_repo_instruments(instruments: List[str], tf: str = "D1",
                                    data_dir: str = None) -> Dict[str, dict]:
    """盡載宇宙內喺 repo 有檔嘅 instrument；缺檔靜默略過（coverage 記錄靠 engine）。"""
    out = {}
    for inst in instruments:
        try:
            out[inst] = load_repo_json(inst, tf, data_dir)
        except FileNotFoundError:
            continue
    return out


def load_ohlc_csv(path: str) -> dict:
    """通用 OHLC CSV loader（OC 終端 history 供料，階段 B parity 用）。

    接受欄位名（大小寫不敏感，順序不限）：
      timestamp/date/time/datetime、open/o、high/h、low/l、close/c
    有 open 就用；冇 open（三欄 close 檔）就 open=close（引擎只用 h/l/c 時不受影響）。
    """
    with open(path, encoding="utf-8-sig") as f:
        sample = f.read(4096)
        f.seek(0)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t") if sample else csv.excel
        reader = csv.DictReader(f, dialect=dialect)
        cols = {c.strip().lower(): c for c in (reader.fieldnames or [])}

        def col(*names):
            for n in names:
                if n in cols:
                    return cols[n]
            return None

        c_ts = col("timestamp", "datetime")
        c_date = col("date")
        c_time = col("time")
        if c_ts is None and c_date is not None and c_time is not None:
            # MT4 原生導出：DATE＋TIME 兩欄分開 → 合併 "YYYY.MM.DD HH:MM"
            ts_mode = "split"
        elif c_ts is None and c_date is not None:
            ts_mode = "single"   # 淨 DATE 欄：當 timestamp 用（舊行為）
            c_ts = c_date
        elif c_ts is None and c_time is not None:
            ts_mode = "single"   # 淨 TIME 欄：當 timestamp 用
            c_ts = c_time
        elif c_ts is not None:
            ts_mode = "single"
        else:
            raise ValueError(f"{path} 缺必要欄位（timestamp/date+time）")
        c_o = col("open", "o")
        c_h = col("high", "h")
        c_l = col("low", "l")
        c_c = col("close", "c")
        if c_h is None or c_l is None or c_c is None:
            raise ValueError(f"{path} 缺必要欄位（high/low/close）")

        d, o, h, l, c = [], [], [], [], []
        for row in reader:
            if ts_mode == "split":
                d.append(f"{row[c_date].strip()} {row[c_time].strip()}")
            elif ts_mode == "time_only":
                d.append(row[c_time].strip())
            else:
                d.append(row[c_ts].strip())
            if c_o:
                o.append(float(row[c_o]))
            else:
                o.append(float(row[c_c]))
            h.append(float(row[c_h]))
            l.append(float(row[c_l]))
            c.append(float(row[c_c]))
    return {"d": d, "o": o, "h": h, "l": l, "c": c}
