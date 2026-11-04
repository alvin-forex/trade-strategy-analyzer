#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CCY 原版 vs 我們 v3 對比器（方案④ 落地）

原版側：A06E(MQL4) ccy_power_reader.csv —— CCYPowerReader EA 由原版 CCY Power
        Indicator v1.00 嘅圖表 table 物件抽值，0–9 刻度（4.5 = 中性）。
我們側：725B(MQL5) ccy_mt5_XAUUSD_<tf>.csv —— CurrencyPower_v3 (v3.11) 9 buffer，
        0–100 刻度（50 = 中性）。

刻度換算：原版 * 100/9 → 0–100（原版 4.5 → 50.0，中性對齊）。
對比內容：逐 bar 對齊後，計純量差值同「排序一致性」（Spearman / top1 / top3
          交集 / 中性上下方向一致率）——排序係唯一唔受刻度同實作細節影響嘅口徑。

用法：python3 ccy_orig_vs_v3.py [--tf H1,H4] [--days 30]
"""
import argparse
import csv
import json
import statistics
from collections import defaultdict
from datetime import datetime

READER = ("/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/"
          "A06E6395D71C5597BD3D45E90C51C549/MQL4/Files/ccy_power_reader.csv")
MT5_DIR = ("/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/"
           "725B72F25E46C780EF59F57016D58156/MQL5/Files")
TF_FILE = {"H1": "ccy_mt5_XAUUSD_16385.csv", "H4": "ccy_mt5_XAUUSD_16388.csv",
           "D1": "ccy_mt5_XAUUSD_16408.csv"}
COLS = ["bXAU", "bUSD", "bEUR", "bJPY", "bGBP", "bAUD", "bCAD", "bCHF", "bNZD"]
NAME = {c: c[1:] for c in COLS}
ORIG_SCALE = 100.0 / 9.0


def load_reader(tf):
    """{(bar_open_datetime): {ccy: value_0_9}} —— reader 係每 5 分鐘 snapshot，
    同一 bar 內取最後一個 snapshot。"""
    out = {}
    with open(READER, encoding="utf-8", errors="replace") as f:
        for r in csv.DictReader(f):
            if r.get("timeframe") != tf:
                continue
            try:
                ts = datetime.strptime(r["timestamp"], "%Y.%m.%d %H:%M")
            except (ValueError, KeyError):
                continue
            bar = ts.replace(minute=0, second=0)
            cells = {}
            for i in range(1, 10):
                n, p = r.get("ccy%d_name" % i), r.get("ccy%d_power" % i)
                if not n or not p:
                    continue
                n = n.strip().upper()
                if n not in NAME.values():
                    continue
                try:
                    cells[n] = float(p)
                except ValueError:
                    pass
            if cells:
                out[bar] = cells
    return out


def load_mt5(tf):
    path = "%s/%s" % (MT5_DIR, TF_FILE[tf])
    out = {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try:
                ts = datetime.strptime(r["bartime"].strip(), "%Y.%m.%d %H:%M")
            except (ValueError, KeyError):
                continue
            vals = {}
            zero = 0
            for c in COLS:
                raw = r.get(c)
                if raw in (None, "", "EMPTY"):
                    continue
                v = float(raw)
                if v == 0.0:
                    zero += 1
                    continue
                vals[NAME[c]] = v
            # 整行 0 = indicator 未計算（前段 warm-up），唔計
            if zero >= 5 or len(vals) < 5:
                continue
            out[ts.replace(minute=0, second=0)] = vals
    return out


def spearman(a, b):
    n = len(a)
    if n < 3:
        return None
    def ranks(v):
        order = sorted(range(n), key=lambda i: v[i])
        rk = [0.0] * n
        i = 0
        while i < n:
            j = i
            while j + 1 < n and v[order[j + 1]] == v[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                rk[order[k]] = avg
            i = j + 1
        return rk
    ra, rb = ranks(a), ranks(b)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((ra[i] - ma) * (rb[i] - mb) for i in range(n))
    da = sum((ra[i] - ma) ** 2 for i in range(n)) ** 0.5
    db = sum((rb[i] - mb) ** 2 for i in range(n)) ** 0.5
    return num / (da * db) if da and db else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tf", default="H1,H4,D1")
    ap.add_argument("--days", type=int, default=45, help="只計最近 N 日（0=全部）")
    ap.add_argument("--json-out")
    args = ap.parse_args()

    report = {}
    for tf in [t.strip() for t in args.tf.split(",") if t.strip()]:
        orig = load_reader(tf)
        ours = load_mt5(tf)
        common = sorted(set(orig) & set(ours))
        if args.days > 0 and common:
            cutoff = common[-1].toordinal() - args.days
            common = [d for d in common if d.toordinal() >= cutoff]

        per_ccy = defaultdict(list)
        rhos, top1, top3, dirs = [], 0, 0, 0
        for bar in common:
            o, m = orig[bar], ours[bar]
            keys = [k for k in NAME.values() if k in o and k in m]
            if len(keys) < 5:
                continue
            ov = [o[k] * ORIG_SCALE for k in keys]
            mv = [m[k] for k in keys]
            for i, k in enumerate(keys):
                per_ccy[k].append(abs(ov[i] - mv[i]))
            r = spearman(ov, mv)
            if r is not None:
                rhos.append(r)
            ob = max(keys, key=lambda k: o[k])
            mb = max(keys, key=lambda k: m[k])
            if ob == mb:
                top1 += 1
            ot3 = set(sorted(keys, key=lambda k: -o[k])[:3])
            mt3 = set(sorted(keys, key=lambda k: -m[k])[:3])
            if ot3 == mt3:
                top3 += 1
            dirs += sum(1 for i, k in enumerate(keys)
                        if (ov[i] - 50.0) * (mv[i] - 50.0) > 0)

        blocks = len(rhos) and len([b for b in common]) or 0
        total_pairs = sum(len(v) for v in per_ccy.values())
        report[tf] = {
            "bars_orig": len(orig),
            "bars_ours": len(ours),
            "bars_matched": len(common),
            "bars_scored": len(rhos),
            "spearman_mean": round(statistics.mean(rhos), 4) if rhos else None,
            "spearman_min": round(min(rhos), 4) if rhos else None,
            "top1_agree_pct": round(100.0 * top1 / len(rhos), 1) if rhos else None,
            "top3_exact_pct": round(100.0 * top3 / len(rhos), 1) if rhos else None,
            "direction_pct": round(100.0 * dirs / total_pairs, 1) if total_pairs else None,
            "abs_diff_mean": round(statistics.mean(
                [d for v in per_ccy.values() for d in v]), 3) if total_pairs else None,
            "abs_diff_by_ccy": {k: round(statistics.mean(v), 2)
                                for k, v in sorted(per_ccy.items()) if v},
            "window": [str(common[0]), str(common[-1])] if common else None,
        }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
