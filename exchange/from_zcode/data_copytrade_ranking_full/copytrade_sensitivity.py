#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修復期門檻敏感性分析（OpenClaw 審閱 2.1(3)）＋§2.6 漏斗復現驗證。

門檻口徑照文章 §2.6：PF≥1.5、勝率≥60%、回撤修復期 ≤X 日（或無未修復回撤）、
最大連虧 ≤8。復現目標：865→467→464→45→45（全層）、17,300→400 行／131 對。
敏感性：X ∈ {60, 90, 120, 180}，出 全層 與 17,300 兩口徑通過率。
"""
import csv

CSV = "/home/z/my-project/exchange-repo/data/copytrade/decision_ranking.csv"

def f(x):
    try:
        return float(x)
    except (ValueError, TypeError):
        return None

rows = []
with open(CSV, newline="", encoding="utf-8") as fp:
    rows = list(csv.DictReader(fp))

print("rankable rows:", len(rows))

def gates(r, rec_lim):
    pf, wr = f(r["profit_factor"]), f(r["win_rate"])
    if pf is None or pf < 1.5:
        return False
    if wr is None or wr < 0.6:
        return False
    rec = f(r["recovery_days"])
    if rec is not None and rec > rec_lim:
        return False          # None＝無未修復回撤，通過
    mcl = f(r["max_consec_losses"])
    if mcl is None or mcl > 8:
        return False
    return True

# ── 復現 §2.6 漏斗（全層口徑 865 行）──
quanc = [r for r in rows if r["layer_policy"] == "全層"]
g1 = [r for r in quanc if f(r["profit_factor"]) and f(r["profit_factor"]) >= 1.5]
g2 = [r for r in g1 if f(r["win_rate"]) and f(r["win_rate"]) >= 0.6]
g3 = [r for r in g2 if f(r["recovery_days"]) is None or f(r["recovery_days"]) <= 90]
g4 = [r for r in g3 if f(r["max_consec_losses"]) is not None and f(r["max_consec_losses"]) <= 8]
print("復現 全層漏斗: 865→%d→%d→%d→%d（文章 467/464/45/45）"
      % (len(g1), len(g2), len(g3), len(g4)))

# 復現第 3 重兩個分支拆解（回應 2.1(1) 第 4 重零邊際）
g3_keep = sum(1 for r in g2 if f(r["recovery_days"]) is None)
print("  其中 recovery=None（無未修復回撤）直接通過: %d" % g3_keep)

# ── 全樣本 400/131 復現 ──
all4 = [r for r in rows if gates(r, 90)]
pairs4 = set((r["signal_id"], r["symbol"]) for r in all4)
pairs_all = set((r["signal_id"], r["symbol"]) for r in rows)
print("復現 全樣本: %d 行 / %d 對 / 865 對中 %.1f%%（文章 400/131/15.1%%）"
      % (len(all4), len(pairs4), len(pairs4) / len(pairs_all) * 100))
print("  佔 17,300 行 %.1f%%（OpenClaw 指正：括號應掛 2.3%%）" % (len(all4) / len(rows) * 100))

# ── 敏感性 60/90/120/180 ──
print("\n== 修復期門檻敏感性（其餘三閘不變：PF≥1.5＋wr≥60%＋連虧≤8）==")
print("門檻 | 全層通過(/865) | 全層通過率 | 全樣本行(/17300) | 對數(/865) | 對覆蓋率")
for lim in (60, 90, 120, 180):
    a = [r for r in quanc if gates(r, lim)]
    b = [r for r in rows if gates(r, lim)]
    bp = set((r["signal_id"], r["symbol"]) for r in b)
    print("%3d | %4d | %5.1f%% | %5d | %3d | %4.1f%%"
          % (lim, len(a), len(a) / 865 * 100, len(b), len(bp),
             len(bp) / len(pairs_all) * 100))

# 附：只砍修復期一閘的通過率（唔合併其他三閘）——答「90 係咪最狠一刀」
print("\n== 單閘對照（只過該閘，其餘唔設）==")
for lim in (60, 90, 120, 180):
    a = [r for r in quanc if f(r["recovery_days"]) is None or f(r["recovery_days"]) <= lim]
    print("修復期≤%3d：全層 %d/865（%.1f%%）" % (lim, len(a), len(a) / 865 * 100))
