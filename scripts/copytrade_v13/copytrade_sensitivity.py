#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""修復期門檻敏感性分析（OpenClaw 審閱 2.1(3)）＋§2.6 漏斗復現驗證。

門檻口徑照文章 §2.6：PF≥1.5、勝率≥60%、回撤修復期 ≤X 日（修復期無法計算的
組合保守剔除）、最大連虧 ≤8。復現目標：865→467→464→45→45（全層）、
17,300→400 行／131 對。
敏感性：X ∈ {60, 90, 120, 180}，出 全層 與 17,300 兩口徑通過率。

v1.1 修復（OpenClaw 1219 審計）：
  1. None 口徑與正文對齊：recovery_days 無法計算＝保守剔除（原版 None＝通過，
     條件寫反，已改）。docstring 與正文同一句話。
  2. 全層基準補齊 M2/USD 過濾（原版只過 layer_policy，把 3,460 行當 865 用）。
  3. CSV 路徑改 sys.argv（腳本相對），跨機可重現。
  4. 全樣本口徑補齊 account_type=USD：閘欄位（PF/wr/recovery/連虧）係訊號級
     指標，M2/M3×USD/demo 四口徑逐行相同（demo＝USD 鏡像）——四口徑全展開
     800 行＝底層 200 組合×4；文章正文取 USD 口徑 400 行（M2+M3），
     分母 17,300 出 2.3%。

用法：python3 copytrade_sensitivity.py [decision_ranking.csv]
"""
import csv
import sys

CSV = sys.argv[1] if len(sys.argv) > 1 else "decision_ranking.csv"


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
    """四閘：PF≥1.5、wr≥0.6、修復期≤rec_lim（None＝無法計算＝保守剔除）、連虧≤8。"""
    pf, wr = f(r["profit_factor"]), f(r["win_rate"])
    if pf is None or pf < 1.5:
        return False
    if wr is None or wr < 0.6:
        return False
    rec = f(r["recovery_days"])
    if rec is None or rec > rec_lim:
        return False          # None＝修復期無法計算＝保守剔除（同正文 §2.6）
    mcl = f(r["max_consec_losses"])
    if mcl is None or mcl > 8:
        return False
    return True


# ── 全層 M2/USD 基準 865 行（文章基數口徑）──
quanc = [r for r in rows if r["layer_policy"] == "全層"
         and r["copy_method"] == "M2" and r["account_type"] == "USD"]

# ── 復現 §2.6 漏斗（全層 M2/USD 口徑）──
g1 = [r for r in quanc if f(r["profit_factor"]) and f(r["profit_factor"]) >= 1.5]
g2 = [r for r in g1 if f(r["win_rate"]) and f(r["win_rate"]) >= 0.6]
g2_none = sum(1 for r in g2 if f(r["recovery_days"]) is None)
g3 = [r for r in g2 if f(r["recovery_days"]) is not None and f(r["recovery_days"]) <= 90]
g4 = [r for r in g3 if f(r["max_consec_losses"]) is not None and f(r["max_consec_losses"]) <= 8]
print("復現 全層漏斗: %d→%d→%d→%d→%d（文章 865/467/464/45/45）"
      % (len(quanc), len(g1), len(g2), len(g3), len(g4)))
print("  其中 g2 內 recovery=None（無法計算）保守剔除: %d" % g2_none)

# ── 全樣本 400/131 復現（USD 口徑：demo 為鏡像，四口徑全展開係 800 行）──
all4 = [r for r in rows if r["account_type"] == "USD" and gates(r, 90)]
pairs4 = set((r["signal_id"], r["symbol"]) for r in all4)
pairs_all = set((r["signal_id"], r["symbol"]) for r in rows)
print("復現 全樣本: %d 行 / %d 對 / 865 對中 %.1f%%（文章 400/131/15.1%%）"
      % (len(all4), len(pairs4), len(pairs4) / len(pairs_all) * 100))
print("  佔 17,300 行 %.1f%%（正文：括號掛 2.3%%）" % (len(all4) / len(rows) * 100))

# ── 敏感性 60/90/120/180 ──
print("\n== 修復期門檻敏感性（其餘三閘不變：PF≥1.5＋wr≥60%＋連虧≤8；None 剔除）==")
print("門檻 | 全層通過(/865) | 全層通過率 | 全樣本行(/17300) | 對數(/865) | 對覆蓋率")
for lim in (60, 90, 120, 180):
    a = [r for r in quanc if gates(r, lim)]
    b = [r for r in rows if r["account_type"] == "USD" and gates(r, lim)]
    bp = set((r["signal_id"], r["symbol"]) for r in b)
    print("%3d | %4d | %5.1f%% | %5d | %3d | %4.1f%%"
          % (lim, len(a), len(a) / 865 * 100, len(b), len(bp),
             len(bp) / len(pairs_all) * 100))

# 附：只砍修復期一閘的通過率（唔合併其他三閘；None 剔除口徑）——答「90 係咪最狠一刀」
print("\n== 單閘對照（只過該閘，其餘唔設；None＝剔除）==")
for lim in (60, 90, 120, 180):
    a = [r for r in quanc if f(r["recovery_days"]) is not None
         and f(r["recovery_days"]) <= lim]
    print("修復期≤%3d：全層 %d/865（%.1f%%）" % (lim, len(a), len(a) / 865 * 100))
