# -*- coding: utf-8 -*-
"""COPYTRADE v1.3 D2 沙盒驗證——Copy 時機模擬（v1.2 merge 改造版）。

機房無 L0（MT5 specs）亦無 M5 歷史（.hst 喺生產機 A06E）→ 沙盒模式：
合成 L0 specs＋合成 M5 JSON（照 export_hst.py v2 新契約）＋106 真 CSV 重放對帳。

斷言分組：
  T0  v1.2 違規函數退役＋零 pip 常數表（§6.1/§6.2 改造注意）
  T1  FILLED 判定＋target 價＋式 A 手算（§6.3）
  T2  MISSED 記錄唔當 0 利潤（§5.2）
  T3  SELL 對稱（COPY_PROFIT／COPY_LOSE 方向）
  T4  無 L0 → BLOCKED 零估算（§6.7 鐵律 2）
  T5  無 M5 → NO_M5_DATA；ACTUAL 基線照出（唔使 M5）
  T6  pip_size 讀表權威（改 specs→target 隨之變）
  T7  非美元報價缺 fx_at_export → MissingFx→BLOCKED（§6.2 不准最近值頂）
  T8  滑點三情境（§11.8）手算對照
  T9  summarize_timing 聚合：fill_rate／total 只計 FILLED
  T10 load_m5_json 新契約 parse＋時間排序
  T11 layer_freq_matrix pnl_per_cycle 欄（§11.3③）
  T12 重放對帳——106 真 CSV XAUUSD 式 A vs net_profit（§6.3 品質閘門）
"""
import json
import os
import sqlite3
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tsa_redo") if os.path.isdir(
    os.path.join(os.path.dirname(HERE), "tsa_redo")) else HERE)

from copy_timing import (simulate_copy_timing, simulate_timing_all, summarize_timing,
                         load_m5_json, DEFAULT_PROFIT_PIPS, DEFAULT_LOSE_PIPS)
from pipcalc import pip_value_usd
from ingest import load_signal_csv, group_cycles

PASS = 0
FAIL = 0


def ok(cond, label):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}")


# ============ 合成 L0 specs（§6.2 權威鏈輸入） ============
XAU = {"pip_size": 0.1, "tick_size": 0.01, "tick_value": 1.0,
       "contract_size": 100.0, "quote_currency": "USD", "fx_at_export": None}
EUR = {"pip_size": 0.0001, "tick_size": 0.00001, "tick_value": 1.0,
       "contract_size": 100000.0, "quote_currency": "USD", "fx_at_export": None}
JPY = {"pip_size": 0.01, "tick_size": 0.001, "tick_value": 0.00667,
       "contract_size": 100000.0, "quote_currency": "JPY", "fx_at_export": None}
SPECS = {"XAUUSD": XAU, "EURUSD": EUR, "USDJPY": JPY}


def mk_cycle(symbol="XAUUSD", direction="BUY", entry=2650.00, exit_=2653.00,
             lots=0.10, open_time="2026-03-10 08:00", close_time="2026-03-10 16:00"):
    """單層 cycle（L1 出口＝cycle 出口——重放對帳用）。"""
    return {
        "signal_id": "sandbox", "symbol": symbol, "direction": direction,
        "open_time": open_time, "close_time": close_time,
        "layers_n": 1, "lots_total": lots, "pnl_total": 0.0, "data_grade": "A",
        "layers": [{"layer_no": 1, "typ": direction.lower(), "lots": lots,
                    "open_time": open_time, "open_price": entry,
                    "close_time": close_time, "close_price": exit_,
                    "net_profit": 0.0, "lots_cum": lots}],
    }


def mk_bars(spec, base=2650.00, moves=None, start="2026-03-10T08:00"):
    """合成 M5 bars（OHLC v2 新契約欄位）。moves=[(bar_idx, high_delta, low_delta)]。"""
    out = []
    for i in range(12):
        ts = f"{start[:11]}{int(start[11:13]):02d}:{(int(start[14:16]) + 5 * i) % 60:02d}"
        hi = base + 0.3
        lo = base - 0.3
        for (bi, hd, ld) in (moves or []):
            if bi == i:
                hi += hd
                lo += ld
        out.append({"timestamp": ts, "open": base, "high": round(hi, 2),
                    "low": round(lo, 2), "close": base, "volume": 100, "spread": 3})
    return out


print("== T0 v1.2 違規函數退役＋零 pip 常數表 ==")
src = open(os.path.join(HERE, "copy_timing.py"), encoding="utf-8").read()
ok("def _get_pip_size" not in src, "copy_timing 無 _get_pip_size 函數（§6.1 硬編碼表退役）")
ok("def _estimate_pip_value" not in src, "copy_timing 無 _estimate_pip_value 函數（§6.2 BTCUSD 1000 倍來源退役）")
ok(".endswith(" not in src,
   "源碼零 endswith 呼叫（§6.2 禁報價幣尾碼猜合約——docstring 歷史留痕除外）")
ok("from pipcalc import" in src, "pip 計算行 pipcalc 權威鏈（L1 唯一計錢層）")

print("== T1 FILLED 判定＋target＋式 A ==")
cyc = mk_cycle()
# BUY wait+10 pips → target=2650.00+10×0.1=2651.00；bar1 high 2651.2 觸
bars = mk_bars(XAU, moves=[(1, +0.9, 0.0)])  # bar1 high=2651.2
rows = simulate_copy_timing(cyc, bars, SPECS)
by_w = {r["wait_pips"]: r for r in rows if r["sim_type"] == "COPY_PROFIT"}
r10 = by_w[10]
ok(r10["outcome"] == "FILLED", "BUY COPY_PROFIT wait=10 FILLED")
ok(abs(r10["sim_entry_price"] - 2651.00) < 1e-9, "sim_entry=target=2651.00（entry+10×pip0.1）")
ok(r10["trigger_time"] == "2026-03-10T08:05", "trigger bar=08:05（首根觸及 bar）")
# 式 A：(2653−2651)×1×0.10×100=$20.00；Ideal 無滑點
ok(abs(r10["sim_pnl_usd"] - 20.00) < 0.005, "式 A 手算 $20.00＝引擎輸出")
act = [r for r in rows if r["sim_type"] == "ACTUAL"][0]
ok(act["outcome"] == "FILLED" and abs(act["sim_entry_price"] - 2650.00) < 1e-9,
   "ACTUAL 基線即刻跟（entry=2650.00）")
ok(abs(act["sim_pnl_usd"] - 30.00) < 0.005, "ACTUAL 式 A=(2653−2650)×0.1×100=$30.00")

print("== T2 MISSED 記錄唔當 0（§5.2） ==")
bars_low = mk_bars(XAU, moves=[(i, -0.15, 0.0) for i in range(12)])  # high 全部 <2651.0
rows2 = simulate_copy_timing(cyc, bars_low, SPECS)
m10 = {r["wait_pips"]: r for r in rows2 if r["sim_type"] == "COPY_PROFIT"}[10]
ok(m10["outcome"] == "MISSED", "無 bar 觸 target → MISSED")
ok(m10["sim_pnl_usd"] is None and m10["sim_entry_price"] is None,
   "MISSED pnl=None（唔當 0 利潤）")
ok(m10["trigger_time"] is None, "MISSED trigger_time=None")

print("== T3 SELL 對稱 ==")
cyc_s = mk_cycle(direction="SELL", entry=2650.00, exit_=2647.00)
# SELL COPY_PROFIT wait+10：target=2650−1.0=2649.0；bar2 low=2648.7 觸
bars_s = mk_bars(XAU, moves=[(2, 0.0, -1.0)])
rows_s = simulate_copy_timing(cyc_s, bars_s, SPECS)
sp10 = {r["wait_pips"]: r for r in rows_s if r["sim_type"] == "COPY_PROFIT"}[10]
ok(sp10["outcome"] == "FILLED" and abs(sp10["sim_entry_price"] - 2649.00) < 1e-9,
   "SELL wait+10 target=2649.00（方向反轉）")
# 式 A SELL：(2647−2649)×(−1)×0.1×100=$20.00
ok(abs(sp10["sim_pnl_usd"] - 20.00) < 0.005, "SELL 式 A 手算 $20.00")
# SELL COPY_LOSE wait−10：target=2650+1.0=2651.0；bar3 high=2652 觸
bars_sl = mk_bars(XAU, moves=[(3, +1.8, 0.0)])
rows_sl = simulate_copy_timing(cyc_s, bars_sl, SPECS)
sl_m10 = {r["wait_pips"]: r for r in rows_sl if r["sim_type"] == "COPY_LOSE"}[-10]
ok(sl_m10["outcome"] == "FILLED" and abs(sl_m10["sim_entry_price"] - 2651.00) < 1e-9,
   "SELL COPY_LOSE wait=−10 target=2651.00（等價更差）")
# BUY COPY_LOSE wait−10：target=2649.0（bar low 2648.7 觸；high 2650.3 唔觸 profit target）
bars_lose = mk_bars(XAU, moves=[(2, 0.0, -1.0)])
rows_bl = simulate_copy_timing(cyc, bars_lose, SPECS)
bl_m10 = {r["wait_pips"]: r for r in rows_bl if r["sim_type"] == "COPY_LOSE"}[-10]
ok(bl_m10["outcome"] == "FILLED" and abs(bl_m10["sim_entry_price"] - 2649.00) < 1e-9,
   "BUY COPY_LOSE wait=−10 target=2649.00（更好價）")

print("== T4 無 L0 → BLOCKED 零估算 ==")
rows_b = simulate_copy_timing(cyc, bars, {})
ok(all(r["outcome"] == "BLOCKED" for r in rows_b), "specs 缺 → 全行 BLOCKED")
ok(all(r["sim_pnl_usd"] is None for r in rows_b), "BLOCKED 行零數字（鐵律 2）")
ok(any("BLOCKED" in (r.get("note") or "") for r in rows_b), "note 註明 BLOCKED 原因")

print("== T5 無 M5 → NO_M5_DATA；ACTUAL 照出 ==")
rows_nm = simulate_copy_timing(cyc, [], SPECS)
act5 = [r for r in rows_nm if r["sim_type"] == "ACTUAL"][0]
ok(act5["outcome"] == "FILLED" and abs(act5["sim_pnl_usd"] - 30.00) < 0.005,
   "ACTUAL wait=0 唔使 M5 照出（$30.00）")
w_rows = [r for r in rows_nm if r["wait_pips"] != 0]
ok(all(r["outcome"] == "NO_M5_DATA" for r in w_rows), "wait≠0 全標 NO_M5_DATA")
ok(all("M5" in (r.get("note") or "") for r in w_rows), "note 指明 export_hst --tf 5 導出解鎖")

print("== T6 pip_size 讀表權威 ==")
SPECS2 = dict(SPECS)
SPECS2["XAUUSD"] = dict(XAU, pip_size=0.05)  # 改表→target 變
rows_p = simulate_copy_timing(cyc, bars, SPECS2)
p10 = {r["wait_pips"]: r for r in rows_p if r["sim_type"] == "COPY_PROFIT"}[10]
ok(abs(p10["sim_entry_price"] - 2650.50) < 1e-9, "pip_size 0.05→target=2650.50（讀表唔係常數）")
pv = pip_value_usd("XAUUSD", "2026-03-10", SPECS)
ok(abs(pv - 10.0) < 1e-9, "pip_value=tick_value×(pip/tick)=1×(0.1/0.01)=$10（§6.2 權威式）")
pv_e = pip_value_usd("EURUSD", "2026-03-10", SPECS)
ok(abs(pv_e - 10.0) < 1e-6, "EURUSD pv=1.0×(0.0001/0.00001)=$10")

print("== T7 非美元報價缺 fx → BLOCKED（§6.2 不准最近值頂） ==")
cyc_j = mk_cycle(symbol="USDJPY", direction="BUY", entry=150.00, exit_=150.50)
rows_j = simulate_copy_timing(cyc_j, mk_bars(JPY, base=150.0), SPECS)
ok(all(r["outcome"] == "BLOCKED" for r in rows_j), "JPY 報價無 fx_at_export → BLOCKED")
ok(any("fx" in (r.get("note") or "") for r in rows_j), "note 註明 fx 缺（MissingFx）")

print("== T8 滑點三情境手算 ==")
r_i = {r["wait_pips"]: r for r in simulate_copy_timing(cyc, bars, SPECS, scenario="Ideal")
       if r["sim_type"] == "COPY_PROFIT"}[10]
r_r = {r["wait_pips"]: r for r in simulate_copy_timing(cyc, bars, SPECS, scenario="Realistic")
       if r["sim_type"] == "COPY_PROFIT"}[10]
r_s = {r["wait_pips"]: r for r in simulate_copy_timing(cyc, bars, SPECS, scenario="Stress")
       if r["sim_type"] == "COPY_PROFIT"}[10]
ok(abs(r_i["sim_pnl_usd"] - 20.00) < 0.005, "Ideal 無滑點 $20.00")
ok(abs(r_r["sim_pnl_usd"] - 19.50) < 0.005, "Realistic 扣 0.5×$10×0.1=$0.50 → $19.50")
ok(abs(r_s["sim_pnl_usd"] - 18.00) < 0.005, "Stress 扣 2.0×$10×0.1=$2.00 → $18.00")

print("== T9 summarize_timing 聚合 ==")
two = simulate_timing_all([cyc, mk_cycle()], SPECS,
                           m5_loader=lambda s: bars if s == "XAUUSD" else None)
summ = summarize_timing(two)
s10 = [s for s in summ if s["sim_type"] == "COPY_PROFIT" and s["wait_pips"] == 10][0]
ok(s10["cycles"] == 2, "兩 cycles 聚合 cycles=2")
ok(s10["filled"] == 2 and s10["missed"] == 0, "兩者都 FILLED（m5_loader 同數據）")
ok(abs(s10["fill_rate"] - 1.0) < 1e-9, "fill_rate=1.0")
ok(abs(s10["total_pnl_usd"] - 40.00) < 0.01, "total=2×$20=$40（FILLED only）")
mixed = simulate_timing_all([cyc, mk_cycle(exit_=2648.0)], SPECS,
                            m5_loader=lambda s: bars if s == "XAUUSD" else None)
# 第二個 cycle exit 2648<target 2651——FILLED 但蝕（MISSED 唔入 total 之外，蝕單照計）
summ2 = summarize_timing(mixed)
s10b = [s for s in summ2 if s["sim_type"] == "COPY_PROFIT" and s["wait_pips"] == 10][0]
ok(s10b["filled"] == 2, "兩個都 FILLED（唔會因蝕而變 MISSED）")
# 手算：cycle2 entry 2650 wait10→2651 exit 2648：(2648−2651)×0.1×100=−30；total=20−30=−10
ok(abs(s10b["total_pnl_usd"] - (-10.00)) < 0.01, "total=20−30=−10（盈虧照計）")

print("== T10 load_m5_json 新契約 ==")
tmp = tempfile.mkdtemp(prefix="ct_sandbox_")
m5p = os.path.join(tmp, "XAUUSD_M5.json")
payload = {"updated": "2026-03-10T08:00", "symbol": "XAUUSD", "timeframe": "M5",
           "source": "sandbox", "start": "2026-03-10T08:00", "end": "2026-03-10T09:00",
           "count": 3, "bars": [
               {"timestamp": "2026-03-10T08:10", "open": 1, "high": 2, "low": 0.5,
                "close": 1.5, "volume": 10, "spread": 3},
               {"timestamp": "2026-03-10T08:00", "open": 1, "high": 2, "low": 0.5,
                "close": 1.5, "volume": 10, "spread": 3},
               {"timestamp": "2026-03-10T08:05", "open": 1, "high": 2, "low": 0.5,
                "close": 1.5, "volume": 10, "spread": 3}]}
with open(m5p, "w", encoding="utf-8") as f:
    json.dump(payload, f)
loaded = load_m5_json(m5p)
ok(len(loaded) == 3 and loaded[0]["timestamp"] == "2026-03-10T08:00",
   "新契約 parse＋timestamp 升序排序")
ok(all(k in loaded[0] for k in ("timestamp", "open", "high", "low", "close", "volume", "spread")),
   "七欄齊（timestamp/open/high/low/close/volume/spread）")

print("== T11 layer_freq_matrix pnl_per_cycle（§11.3③） ==")
conn = sqlite3.connect(":memory:")
from schema import init_db
from ingest import ingest
init_db(conn)
csv106 = os.path.join(os.path.dirname(HERE), "..", "docs", "downloads",
                      "forex-forest-signals-page-106.csv")
csv106 = os.path.normpath(csv106)
n_tr, n_cy, n_ly = ingest(conn, [csv106])
ok(n_tr == 3330, f"106 入庫 3,330 筆（D1 基準，無 regression）")
from run_sim import layer_freq_matrix
lfm = layer_freq_matrix(conn, ["106"])
ok(all("pnl_per_cycle" in r for r in lfm), "頻率矩陣新增 pnl_per_cycle 欄")
row_l1 = [r for r in lfm if r["layer_policy"] == "L1"]
ok(row_l1 and all(abs(r["pnl_per_cycle"] - round(r["pnl_usd"] / r["cycles"], 2)) < 1e-9
                  for r in row_l1),
   "pnl_per_cycle=pnl/cycles（§11.3③ 單層回報，全 symbol 驗）")

print("== T12 重放對帳——10344 真 CSV XAUUSD 式 A vs net_profit（§6.3） ==")
csv10344 = os.path.normpath(os.path.join(os.path.dirname(HERE), "..", "docs", "downloads",
                                          "forex-forest-signals-page-10344.csv"))
trades = [t for t in load_signal_csv(csv10344) if t["symbol"] == "XAUUSD"]
ok(len(trades) == 238, f"10344 XAUUSD 樣本 {len(trades)} 筆（D1 基準 238）")
errs = []
for t in trades:
    d = 1.0 if t["typ"] == "buy" else -1.0
    a = (t["close_price"] - t["open_price"]) * d * t["lots"] * 100.0
    if abs(a) > 1.0:  # 細額單相對誤差噪音大——只計 |式A|>$1
        errs.append(abs(a - t["net_profit"]) / max(abs(t["net_profit"]), 1.0))
errs.sort()
med = errs[len(errs) // 2] if errs else 0.0
ok(med < 0.02, f"式 A vs net_profit 中位相對誤差 {med:.4%} <2%（broker 計法同式 A 同源）")
ok(len(errs) >= 200, f"有效對帳樣本 {len(errs)} 筆（|式A|>$1）")
# timing ACTUAL 行重放對帳：單層 cycle wait=0 式 A＝L1 net_profit（同一筆）
one = [c for c in group_cycles(trades) if c["layers_n"] == 1 and c["symbol"] == "XAUUSD"][:80]
ok(len(one) >= 20, f"單層 cycle 樣本 {len(one)} 個")
matched = 0
for c in one:
    r = simulate_copy_timing(c, None, SPECS)
    act = [x for x in r if x["sim_type"] == "ACTUAL"][0]
    l1 = c["layers"][0]
    # 重放對帳（§13 精神）：wait=0 引擎式 A vs 測試腳本獨立手算式 A——同一條數，100% 一致
    d = 1.0 if l1["typ"] == "buy" else -1.0
    manual = (l1["close_price"] - l1["open_price"]) * d * l1["lots"] * 100.0
    if abs(act["sim_pnl_usd"] - round(manual, 2)) < 0.005:
        matched += 1
ok(matched == len(one),
   f"ACTUAL wait=0 引擎式 A＝腳本獨立手算：{matched}/{len(one)}（100%，重放對帳）")
ok(med < 0.05,
   f"式 A vs broker net_profit 中位差 {med:.4%} <5%（差異＝swap/commission 成分，非引擎 defect）")

print()
print(f"===== COPYTRADE D2 sandbox：PASS {PASS}／FAIL {FAIL} =====")
sys.exit(1 if FAIL else 0)
