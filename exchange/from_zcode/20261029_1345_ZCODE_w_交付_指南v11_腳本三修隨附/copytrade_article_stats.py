#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Copy trade 文章實證數據計算——由 D4 全量 decision_ranking.csv 抽取統計

v1.1 修復（OpenClaw 1219 審計）：
  1. PF 統計改中位數＋四分位（原 avg 被 avg_loss=0 的巨型 PF 綁架，
     全庫最大 PF 5.946e18，均值毫無意義；正文本就用中位 1.12）。
  2. max_dd 過濾改 <0／abs（本庫 max_dd ≤0，負值＝回撤；原 >0 永遠空集）。
  3. CSV 路徑改 sys.argv（腳本相對），跨機可重現。
  4. 新增 PF 四桶分解（<1／1–1.5／≥1.5／未定義），支撐正文 §2.2 分母修正
     ——「≥1.5」唔可以靜靜併入 avg_loss=0 的 1,228 行。

用法：python3 copytrade_article_stats.py [decision_ranking.csv]
"""
import csv
import sys
from collections import Counter, defaultdict

CSV = sys.argv[1] if len(sys.argv) > 1 else "decision_ranking.csv"

rows = []
with open(CSV, newline="", encoding="utf-8") as fp:
    rows = list(csv.DictReader(fp))

print(f"total rankable rows: {len(rows)}")

# ── 基本結構 ──
signals = set(r["signal_id"] for r in rows)
pairs = set((r["signal_id"], r["symbol"]) for r in rows)
symbols = Counter(r["symbol"] for r in rows)
print(f"signal×symbol 對數: {len(pairs)}")
verdicts = Counter(r["verdict"] for r in rows)
grades = Counter(r["data_grade"] for r in rows)
methods = Counter(r["copy_method"] for r in rows)
scenarios = Counter(r["cost_scenario"] for r in rows)
accts = Counter(r["account_type"] for r in rows)

print(f"signals with rankable rows: {len(signals)}")
print(f"symbols top10: {symbols.most_common(10)}")
print(f"verdicts: {dict(verdicts)}")
print(f"grades: {dict(grades)}")
print(f"copy_methods: {dict(methods)}")
print(f"scenarios: {dict(scenarios)}")
print(f"account_types: {dict(accts)}")


def f(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None


def median(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return None
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2


def quartiles(vals):
    s = sorted(vals)
    n = len(s)
    if n == 0:
        return (None, None)
    return (s[int(round(0.25 * (n - 1)))], s[int(round(0.75 * (n - 1)))])


# ── signal 級：取每 signal 最佳（USD/Ideal/全層）行做代表性樣本？改用全部可排名行統計分布 ──
def dist(vals, bins):
    c = Counter()
    for v in vals:
        if v is None:
            continue
        for i in range(len(bins) - 1):
            if bins[i] <= v < bins[i + 1]:
                c[f"{bins[i]:g}-{bins[i+1]:g}"] += 1
                break
        else:
            if v == bins[-1]:
                c[f"{bins[-1]:g}"] += 1
    return dict(sorted(c.items(), key=lambda kv: float(kv[0].split('-')[0])))


wr_vals = [f(r["win_rate"]) for r in rows]
pf_vals = [f(r["profit_factor"]) for r in rows]
# v1.1 修復②：max_dd ≤0（負值＝回撤）；取 abs 量深度
dd_vals = [abs(f(r["max_dd"])) for r in rows if f(r["max_dd"]) is not None and f(r["max_dd"]) < 0]
mfl_vals = [abs(f(r["max_float_loss"])) for r in rows if f(r["max_float_loss"]) is not None and f(r["max_float_loss"]) < 0]
eq_vals = [f(r["suggested_start_equity_usd"]) for r in rows if f(r["suggested_start_equity_usd"]) is not None and f(r["suggested_start_equity_usd"]) > 0]
net_vals = [f(r["net_pnl"]) for r in rows if f(r["net_pnl"]) is not None]
rec_vals = [f(r["recovery_days"]) for r in rows if f(r["recovery_days"]) is not None]
mcl_vals = [f(r["max_consec_losses"]) for r in rows if f(r["max_consec_losses"]) is not None]

print("\n== win_rate 分布 ==")
print(dist(wr_vals, [0, 0.5, 0.6, 0.7, 0.8, 0.9, 1.001]))
print("\n== profit_factor 分布 ==")
print(dist(pf_vals, [0, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0, 100.1]))
print("\n== net_pnl 正負 ==")
pos = sum(1 for v in net_vals if v > 0)
neg = sum(1 for v in net_vals if v <= 0)
print(f"positive: {pos} ({pos/len(net_vals)*100:.1f}%)  non-positive: {neg} ({neg/len(net_vals)*100:.1f}%)")
print("\n== max_dd 分布(USD, 深度=abs, 負值口徑) ==")
print(dist(dd_vals, [0, 100, 500, 1000, 3000, 5000, 10000, 50000, 1e9]))
print("\n== max_float_loss 分布(USD, 絕對值) ==")
print(dist(mfl_vals, [0, 100, 500, 1000, 3000, 5000, 10000, 50000, 1e9]))
print("\n== suggested_start_equity 分布(USD) ==")
print(dist(eq_vals, [0, 100, 300, 1000, 3000, 10000, 30000, 1e9]))
print("\n== recovery_days 分布 ==")
print(dist(rec_vals, [0, 1, 7, 30, 90, 180, 365, 730, 4000]))
print("\n== max_consec_losses 分布 ==")
print(dist(mcl_vals, [0, 2, 4, 6, 8, 10, 15, 20, 30, 1000]))

# ── v1.1 修復①：PF 用中位數／四分位，唔好用均值（巨型 PF 綁架）──
pf_num = [v for v in pf_vals if v is not None]
pf_med = median(pf_num)
pf_q1, pf_q3 = quartiles(pf_num)
pf_undef = len(rows) - len(pf_num)
print("\n== profit_factor 統計（中位數口徑，正文 §2.2 同源）==")
print(f"PF 可計算: {len(pf_num)} 行｜未定義(avg_loss=0): {pf_undef} 行")
print(f"全庫 PF 中位: {pf_med:.3f}｜四分位: {pf_q1:.3f}–{pf_q3:.3f}")
print(f"全庫最大 PF: {max(pf_num):.3e}（若印均值會被此類極值綁架——v1.0 版教訓）")

# ── v1.1 新增④：PF 四桶分解（支撐正文 §2.2 分母修正，唔准併桶）──
b_lt1 = sum(1 for v in pf_num if v < 1)
b_mid = sum(1 for v in pf_num if 1 <= v < 1.5)
b_ge15 = sum(1 for v in pf_num if v >= 1.5)
n = len(rows)
print("\n== PF 四桶（分母 17,300，殘項另計——正文 §2.2 v1.1 口徑）==")
print(f"PF<1          : {b_lt1:5d} 行 ({b_lt1/n*100:.2f}%)")
print(f"1≤PF<1.5      : {b_mid:5d} 行 ({b_mid/n*100:.2f}%)")
print(f"PF≥1.5        : {b_ge15:5d} 行 ({b_ge15/n*100:.2f}%)")
print(f"PF 未定義     : {pf_undef:5d} 行 ({pf_undef/n*100:.2f}%)（avg_loss=0，零虧損週期，另計唔併入 ≥1.5）")
print(f"合計          : {b_lt1+b_mid+b_ge15+pf_undef} 行")

# ── Win-rate 陷阱實證：高勝率但虧損 vs 低勝率但賺錢 ──
trap = [r for r in rows if f(r["win_rate"]) and f(r["win_rate"]) >= 0.8 and f(r["net_pnl"]) is not None and f(r["net_pnl"]) < 0]
contrarian = [r for r in rows if f(r["win_rate"]) is not None and f(r["win_rate"]) < 0.5 and f(r["net_pnl"]) is not None and f(r["net_pnl"]) > 0]
print(f"\n== win-rate trap ==\n高勝率(≥80%)但淨虧損: {len(trap)} 行 ({len(trap)/len(rows)*100:.1f}%)")
print(f"低勝率(<50%)但淨盈利: {len(contrarian)} 行 ({len(contrarian)/len(rows)*100:.1f}%)")
if trap:
    t = max(trap, key=lambda r: f(r["win_rate"]))
    print(f"例: signal {t['signal_id']} {t['symbol']} {t['layer_policy']} wr={t['win_rate']} pf={t['profit_factor']} net={t['net_pnl']} avg_win={t['avg_win']} avg_loss={t['avg_loss']}")
if contrarian:
    cc = max(contrarian, key=lambda r: f(r["net_pnl"]))
    print(f"例: signal {cc['signal_id']} {cc['symbol']} {cc['layer_policy']} wr={cc['win_rate']} pf={cc['profit_factor']} net={cc['net_pnl']}")

# 註：Realistic/Stress 情境需 L0 symbols（現 blocked），故成本衝擊實證留待 L0 解鎖；文章中按 §11.8 定性說明
print("\n== 成本情境 Realistic/Stress: BLOCKED（需 L0）——文章以定性論述 ==")

# ── 帳戶類型：USD vs demo 差異（同 signal/layer/method/scenario）──
pairs2 = defaultdict(dict)
for r in rows:
    key = (r["signal_id"], r["layer_policy"], r["copy_method"], r["cost_scenario"])
    pairs2[key][r["account_type"]] = r
diff_ct = 0
for v in pairs2.values():
    if "USD" in v and "demo" in v:
        nu, nd = f(v["USD"]["net_pnl"]), f(v["demo"]["net_pnl"])
        if nu is not None and nd is not None and abs(nu - nd) > 0.01:
            diff_ct += 1
print(f"\n== USD vs demo 有差異對數: {diff_ct} / {sum(1 for v in pairs2.values() if 'USD' in v and 'demo' in v)}")

# ── 跟單方式 M2/M3 對比（USD/Ideal）── PF 用中位數（v1.1 修復①）
m_stats = defaultdict(lambda: {"n": 0, "wr": [], "pf": [], "net": [], "filled": 0, "missed": 0, "cycles": 0})
for r in rows:
    if r["account_type"] != "USD" or r["cost_scenario"] != "Ideal":
        continue
    m = r["copy_method"]
    s = m_stats[m]
    s["n"] += 1
    if f(r["win_rate"]) is not None:
        s["wr"].append(f(r["win_rate"]))
    if f(r["profit_factor"]) is not None:
        s["pf"].append(f(r["profit_factor"]))
    if f(r["net_pnl"]) is not None:
        s["net"].append(f(r["net_pnl"]))
    s["filled"] += int(float(r["trades_filled"] or 0))
    s["missed"] += int(float(r["trades_missed"] or 0))
    s["cycles"] += int(float(r["cycles_n"] or 0))
print("\n== copy_method 對比 (USD/Ideal) ==")
for m, s in sorted(m_stats.items()):
    fr = s["filled"] / (s["filled"] + s["missed"]) if (s["filled"] + s["missed"]) else 0
    med = median(s["pf"]) if s["pf"] else 0
    print(f"{m}: n={s['n']} fill_rate={fr*100:.1f}% avg_wr={sum(s['wr'])/len(s['wr']) if s['wr'] else 0:.4f} median_pf={med:.2f} sum_net={sum(s['net']):.0f}")

# ── 層級政策對比（USD/Ideal/M2）── max_dd 用 <0 口徑（v1.1 修復②）
l_stats = defaultdict(lambda: {"n": 0, "net": [], "dd": [], "mcl": []})
for r in rows:
    if r["account_type"] != "USD" or r["cost_scenario"] != "Ideal":
        continue
    if r["copy_method"] != "M2":
        continue
    lp = r["layer_policy"]
    s = l_stats[lp]
    s["n"] += 1
    if f(r["net_pnl"]) is not None:
        s["net"].append(f(r["net_pnl"]))
    if f(r["max_dd"]) is not None and f(r["max_dd"]) < 0:
        s["dd"].append(abs(f(r["max_dd"])))
    if f(r["max_consec_losses"]) is not None:
        s["mcl"].append(f(r["max_consec_losses"]))
print("\n== layer_policy 對比 (USD/Ideal/M2) ==")
for lp, s in sorted(l_stats.items(), key=lambda kv: -kv[1]["n"]):
    print(f"{lp}: n={s['n']} avg_net={sum(s['net'])/len(s['net']) if s['net'] else 0:.0f} avg_maxDD(深度)={sum(s['dd'])/len(s['dd']) if s['dd'] else 0:.0f} avg_maxConsecLoss={sum(s['mcl'])/len(s['mcl']) if s['mcl'] else 0:.1f}")

# ── Top 10 risk_adj_score（USD/Ideal 貼近現有解鎖面）──
top = [r for r in rows if r["account_type"] == "USD" and r["cost_scenario"] == "Ideal" and f(r["risk_adj_score"]) is not None]
top.sort(key=lambda r: f(r["risk_adj_score"]), reverse=True)
print("\n== Top10 risk_adj_score (USD/Ideal, 每對 signal×symbol 取首名) ==")
seen = set()
cnt = 0
for t in top:
    sig = (t["signal_id"], t["symbol"])
    if sig in seen:
        continue
    seen.add(sig)
    print(f"{t['rank']:>4} {sig} {t['symbol']} {t['layer_policy']} {t['copy_method']} wr={t['win_rate']} pf={t['profit_factor']} net={t['net_pnl']} dd={t['max_dd']} rec={t['recovery_days']} score={t['risk_adj_score']}")
    cnt += 1
    if cnt >= 10:
        break

# ── 極值記錄 ──（max_dd 取深度最大＝abs 最大；原始值為負）
mx_dd = max((r for r in rows if f(r["max_dd"]) is not None), key=lambda r: abs(f(r["max_dd"])))
mx_rec = max((r for r in rows if f(r["recovery_days"]) is not None), key=lambda r: f(r["recovery_days"]))
mx_mcl = max((r for r in rows if f(r["max_consec_losses"]) is not None), key=lambda r: f(r["max_consec_losses"]))
mx_conc = max((r for r in rows if f(r["max_concurrent"]) is not None), key=lambda r: f(r["max_concurrent"]))
mx_layer = max((r for r in rows if f(r["max_layer"]) is not None), key=lambda r: f(r["max_layer"]))
print("\n== 極值 ==")
print(f"最大回撤深度 max_dd: {mx_dd['max_dd']} (signal {mx_dd['signal_id']} {mx_dd['symbol']} {mx_dd['layer_policy']} {mx_dd['copy_method']} {mx_dd['cost_scenario']})")
print(f"最長 recovery_days: {mx_rec['recovery_days']} (signal {mx_rec['signal_id']} {mx_rec['symbol']} {mx_rec['layer_policy']})")
print(f"最多連虧: {mx_mcl['max_consec_losses']} (signal {mx_mcl['signal_id']} {mx_mcl['symbol']} {mx_mcl['layer_policy']})")
print(f"最高同時持倉 max_concurrent: {mx_conc['max_concurrent']} (signal {mx_conc['signal_id']} {mx_conc['symbol']} {mx_conc['layer_policy']})")
print(f"最深層深 max_layer: {mx_layer['max_layer']} (signal {mx_layer['signal_id']} {mx_layer['symbol']} {mx_layer['layer_policy']})——正文 §4.1 口徑=max_concurrent，非 max_layer")

# PF≥1.5 且 wr≥0.6 且 recovery≤90（None 剔除）且連虧≤8 嘅「三好」組合數（篩選器示範）
triple = [r for r in rows if r["account_type"] == "USD" and r["cost_scenario"] == "Ideal"
          and f(r["profit_factor"]) and f(r["profit_factor"]) >= 1.5
          and f(r["win_rate"]) and f(r["win_rate"]) >= 0.6
          and f(r["recovery_days"]) is not None and f(r["recovery_days"]) <= 90
          and f(r["max_consec_losses"]) is not None and f(r["max_consec_losses"]) <= 8]
triple_pairs = set((r["signal_id"], r["symbol"]) for r in triple)
print(f"\n== 三重篩選器示範 (PF≥1.5＋wr≥60%＋recovery≤90日 None剔除＋連虧≤8) ==")
print(f"通過組合: {len(triple)} 行 / {len(triple_pairs)} 對 signal×symbol ({len(triple_pairs)/len(pairs)*100:.1f}% 嘅對)")

# verdict 樣本數：優先/觀察/迴避
print(f"\nverdict 分布: {dict(verdicts)}")
