#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CCY Power 對比器 v1（R12 Round 2 工具包核心）— ZCODE_w 2026-11-06 14:3x
用途（照 1358 方案原文）：
  - #3 MT4 vs MT5 數值一致性：兩份 exporter CSV 對齊 diff（跨 broker feed 容差 default 0.5）
  - #4 原版 vs 我哋：同 terminal 雙版對比（容差可收緊，--tol 自配）
  - 產出：逐 pair 差異報告（max/mean 差、不一致 bar、PASS/FAIL）markdown＋CSV
輸入 CSV 格式（Exporter EA 輸出，欄 header 必須一致）：
  time,pair,idx0,idx1,...,idx8
  time=YYYY-MM-DD HH:MM:SS（黑 bar 開盤時間）；pair=符號名（對齊鍵之一）；idx0-8=9 幣 power 值
用法：
  python3 ccy_comparator.py --a mt4.csv --b mt5.csv --tol 0.5 --label-a MT4 --label-b MT5 --out report.md
  python3 ccy_comparator.py --a mine.csv --b orig.csv --tol 0.01 --report-csv diff.csv
  python3 ccy_comparator.py --self-test        # 合成數據自證
"""
import csv, sys, os, argparse, datetime as dt

CCY = ["AUD","CAD","CHF","EUR","GBP","JPY","NZD","USD","XAU"]  # 9 幣序（照 v3 常量序）

def parse_time(s):
    return dt.datetime.strptime(s.strip(), "%Y-%m-%d %H:%M:%S")

def load_csv(path):
    rows = {}
    bad = 0
    with open(path, encoding="utf-8-sig") as f:
        rd = csv.DictReader(f)
        need = {"time","pair"} | {f"idx{i}" for i in range(9)}
        missing = need - set(rd.fieldnames or [])
        if missing:
            raise SystemExit(f"[FAIL] {path} 缺欄：{sorted(missing)}（需 time,pair,idx0..idx8）")
        for r in rd:
            try:
                t = parse_time(r["time"])
                key = (r["pair"].strip(), t)
                rows[key] = [float(r[f"idx{i}"]) for i in range(9)]
            except (ValueError, KeyError):
                bad += 1
    return rows, bad

def compare(rows_a, rows_b, tol, label_a="A", label_b="B"):
    keys_a, keys_b = set(rows_a), set(rows_b)
    common = sorted(keys_a & keys_b)
    out = {
        "only_a": sorted(keys_a - keys_b),
        "only_b": sorted(keys_b - keys_a),
        "common": common,
        "pairs": [],           # 每 (pair, ccy) 統計
        "bad_bars": [],        # 超容差 bar 明細
        "tol": tol, "label_a": label_a, "label_b": label_b,
    }
    stat = {}
    for key in common:
        pair, t = key
        va, vb = rows_a[key], rows_b[key]
        for i in range(9):
            d = va[i] - vb[i]
            st = stat.setdefault((pair, CCY[i]), {"n":0,"max":0.0,"sum":0.0,"bad":0})
            st["n"] += 1
            st["sum"] += d
            if abs(d) > st["max"]: st["max"] = abs(d)
            if abs(d) > tol:
                st["bad"] += 1
                out["bad_bars"].append((pair, t, CCY[i], va[i], vb[i], d))
    for (pair, ccy), st in sorted(stat.items()):
        out["pairs"].append({
            "pair": pair, "ccy": ccy, "n": st["n"],
            "max_diff": st["max"], "mean_diff": st["sum"]/st["n"],
            "bad_bars": st["bad"],
            "pass": st["bad"] == 0,
        })
    return out

def report_md(out, path):
    la, lb, tol = out["label_a"], out["label_b"], out["tol"]
    npass = sum(1 for p in out["pairs"] if p["pass"])
    total = len(out["pairs"])
    verdict = "PASS" if npass == total and total > 0 and not out["only_a"] and not out["only_b"] else "FAIL"
    L = []
    L.append(f"# CCY Power 對比報告：{la} vs {lb}")
    L.append("")
    L.append(f"- 判定：**{verdict}**（容差 {tol}；全 {total} 組（pair×幣）中 {npass} 組 PASS）")
    L.append(f"- 共同 bar：{len(out['common'])}／僅 {la}：{len(out['only_a'])}／僅 {lb}：{len(out['only_b'])}")
    L.append(f"- 超容差 bar 總數：{len(out['bad_bars'])}")
    L.append("")
    L.append("| pair | 幣 | n | max差 | mean差 | 超容差bar | 判定 |")
    L.append("|---|---|---|---|---|---|---|")
    for p in out["pairs"]:
        L.append(f"| {p['pair']} | {p['ccy']} | {p['n']} | {p['max_diff']:.4f} | {p['mean_diff']:+.4f} | {p['bad_bars']} | {'✅' if p['pass'] else '❌'} |")
    if out["bad_bars"]:
        L.append("")
        L.append("## 超容差明細（首 20 筆）")
        L.append("")
        L.append("| pair | bar時間 | 幣 | "+la+" | "+lb+" | 差 |")
        L.append("|---|---|---|---|---|---|")
        for pair, t, ccy, va, vb, d in out["bad_bars"][:20]:
            L.append(f"| {pair} | {t} | {ccy} | {va:.2f} | {vb:.2f} | {d:+.4f} |")
        if len(out["bad_bars"]) > 20:
            L.append(f"\n（其餘 {len(out['bad_bars'])-20} 筆見 CSV）")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    return verdict

def report_csv(out, path):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["pair","time","ccy",f"{out['label_a']}_val",f"{out['label_b']}_val","diff"])
        for pair, t, ccy, va, vb, d in out["bad_bars"]:
            w.writerow([pair, t, ccy, f"{va:.4f}", f"{vb:.4f}", f"{d:+.4f}"])

def self_test():
    """合成數據三案自證：全一致 PASS／單點超容差 FAIL／時間戳錯位零對齊"""
    base = (50.0, 55.2, 48.1, 62.3, 40.9, 58.7, 44.4, 51.5, 38.8)
    mk = lambda i: {("EURUSD", dt.datetime(2026,11,6,10,i,0)): list(base)}
    rows_a, rows_b = {}, {}
    for i in range(5):
        rows_a.update(mk(i)); rows_b.update(mk(i))
    # 案1：全一致
    o1 = compare(rows_a, rows_b, 0.5, "MT4", "MT5")
    assert o1["pairs"] and all(p["pass"] for p in o1["pairs"]) and not o1["bad_bars"], "案1 應全 PASS"
    # 案2：單點超容差（B 頭 2 bar 全行 +1.2）
    rows_b2 = {k: ([v+1.2 for v in vals] if i < 2 else vals) for i, (k, vals) in enumerate(rows_b.items())}
    o2 = compare(rows_a, rows_b2, 0.5, "MT4", "MT5")
    assert any(not p["pass"] for p in o2["pairs"]) and o2["bad_bars"], "案2 應有 FAIL"
    # 案3：時間戳錯位（B 整體偏 10 分鐘 → 零重疊 common=0）
    rows_b3 = {("EURUSD", t + dt.timedelta(minutes=10)): vals for (p, t), vals in rows_b.items()}
    o3 = compare(rows_a, rows_b3, 0.5, "MT4", "MT5")
    assert not o3["common"] and o3["only_a"] and o3["only_b"], "案3 應全部 only_a/only_b"
    npass2 = len([p for p in o2["pairs"] if not p["pass"]])
    print(f"[self-test] 案1 全一致 PASS ✓／案2 單點超容差捉出（{npass2}/{len(o2['pairs'])} 組 FAIL、{len(o2['bad_bars'])} bar）✓／案3 時間戳錯位零對齊捉出 ✓ — 3/3 PASS")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", help="CSV A（如 MT4 exporter 輸出）")
    ap.add_argument("--b", help="CSV B（如 MT5 exporter 輸出）")
    ap.add_argument("--tol", type=float, default=0.5, help="容差（default 0.5，跨 broker feed；同 terminal 可 0.01）")
    ap.add_argument("--label-a", default="A"); ap.add_argument("--label-b", default="B")
    ap.add_argument("--out", default="ccy_compare_report.md", help="markdown 報告輸出")
    ap.add_argument("--report-csv", default=None, help="超容差明細 CSV（可選）")
    ap.add_argument("--self-test", action="store_true", help="合成數據自證")
    args = ap.parse_args()
    if args.self_test:
        self_test(); return 0
    if not (args.a and args.b):
        ap.print_help(); return 1
    ra, bada = load_csv(args.a); rb, badb = load_csv(args.b)
    print(f"[load] {args.a}: {len(ra)} bars（壞行 {bada}）／{args.b}: {len(rb)} bars（壞行 {badb}）")
    out = compare(ra, rb, args.tol, args.label_a, args.label_b)
    verdict = report_md(out, args.out)
    if args.report_csv:
        report_csv(out, args.report_csv)
    print(f"[compare] 共同 {len(out['common'])} bars／組（pair×幣）{len(out['pairs'])}／超容差 {len(out['bad_bars'])} 筆")
    print(f"[verdict] {verdict} → {args.out}")
    return 0 if verdict == "PASS" else 2

if __name__ == "__main__":
    sys.exit(main())
