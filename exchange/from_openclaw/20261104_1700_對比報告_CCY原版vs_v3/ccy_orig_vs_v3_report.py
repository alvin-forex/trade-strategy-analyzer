#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""產生 CCY 原版 vs v3 對比 artifacts：逐 bar CSV ＋ summary JSON ＋ Markdown 報告。"""
import csv
import importlib.util
import json
import os
import statistics
from collections import defaultdict
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("cmp", os.path.join(HERE, "ccy_orig_vs_v3.py"))
cmp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cmp)

OUT = os.path.join(HERE, "..", "deliverables", "ccy_orig_vs_v3_20261104")
os.makedirs(OUT, exist_ok=True)
MAJORS = ["USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "NZD"]


def pearson(x, y):
    n = len(x)
    mx, my = sum(x) / n, sum(y) / n
    num = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = sum((a - mx) ** 2 for a in x) ** 0.5
    dy = sum((b - my) ** 2 for b in y) ** 0.5
    return num / (dx * dy) if dx and dy else None


summary = {}
rows_out = []

for tf in ("H1", "H4", "D1"):
    orig = cmp.load_reader(tf)
    ours = cmp.load_mt5(tf)
    common = sorted(set(orig) & set(ours))

    per_ccy, rhos8, rhos9, top1, top3, dirs8, total8 = (defaultdict(list), [], [], 0, 0, 0, 0)
    for bar in common:
        o, m = orig[bar], ours[bar]
        ks = [k for k in cmp.NAME.values() if k in o and k in m]
        if len(ks) < 5:
            continue
        rec = {"bar": bar.strftime("%Y-%m-%d %H:%M"), "tf": tf}
        for k in ks:
            ov = o[k] * cmp.ORIG_SCALE
            rec["orig_" + k] = round(ov, 2)
            rec["ours_" + k] = round(m[k], 2)
            rec["diff_" + k] = round(m[k] - ov, 2)
            per_ccy[k].append(abs(m[k] - ov))
        rows_out.append(rec)

        maj = [k for k in MAJORS if k in o and k in m]
        if len(maj) >= 5:
            r8 = cmp.spearman([o[k] * cmp.ORIG_SCALE for k in maj], [m[k] for k in maj])
            if r8 is not None:
                rhos8.append(r8)
            dirs8 += sum(1 for k in maj
                         if (o[k] * cmp.ORIG_SCALE - 50.0) * (m[k] - 50.0) > 0)
            total8 += len(maj)
            if max(maj, key=lambda k: o[k]) == max(maj, key=lambda k: m[k]):
                top1 += 1
            if set(sorted(maj, key=lambda k: -o[k])[:3]) == set(sorted(maj, key=lambda k: -m[k])[:3]):
                top3 += 1
        r9 = cmp.spearman([o[k] * cmp.ORIG_SCALE for k in ks], [m[k] for k in ks])
        if r9 is not None:
            rhos9.append(r9)

    per_cur = {}
    for k, v in per_ccy.items():
        xs = [(orig[b][k] * cmp.ORIG_SCALE) for b in common if k in orig[b] and k in ours[b]]
        ys = [(ours[b][k]) for b in common if k in orig[b] and k in ours[b]]
        per_cur[k] = {
            "abs_diff_mean": round(statistics.mean(v), 2) if v else None,
            "pearson_r": round(pearson(xs, ys), 3) if len(xs) > 10 else None,
            "bias": round(statistics.mean([b - a for a, b in zip(xs, ys)]), 2) if xs else None,
            "orig_mean": round(statistics.mean(xs), 1) if xs else None,
            "ours_mean": round(statistics.mean(ys), 1) if ys else None,
        }

    summary[tf] = {
        "orig_bars": len(orig),
        "ours_bars_valid": len(ours),
        "bars_matched": len(common),
        "window": [common[0].strftime("%Y-%m-%d %H:%M"),
                   common[-1].strftime("%Y-%m-%d %H:%M")] if common else None,
        "spearman_9ccy_mean": round(statistics.mean(rhos9), 3) if rhos9 else None,
        "spearman_8maj_mean": round(statistics.mean(rhos8), 3) if rhos8 else None,
        "spearman_8maj_min": round(min(rhos8), 3) if rhos8 else None,
        "top1_agree_pct": round(100.0 * top1 / len(rhos8), 1) if rhos8 else None,
        "top3_exact_pct": round(100.0 * top3 / len(rhos8), 1) if rhos8 else None,
        "direction_pct": round(100.0 * dirs8 / total8, 1) if total8 else None,
        "per_currency": per_cur,
    }

with open(os.path.join(OUT, "summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

if rows_out:
    keys = list(rows_out[0].keys())
    with open(os.path.join(OUT, "bars_compare.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore",
                           lineterminator="\n")
        w.writeheader()
        for r in rows_out:
            w.writerow(r)

print(json.dumps(summary, ensure_ascii=False, indent=2))
print("\nartifacts ->", OUT, "rows:", len(rows_out))
