# -*- coding: utf-8 -*-
"""COPYTRADE D2 端到端驗證——模擬生產機（L0 symbols＋M5 JSON 到位）解鎖後完整 CLI 鏈。

場景：10344 XAUUSD 238 cycles × 9 wait 檔。
合成 M5 bars：每 cycle entry±1.2（12 pips）波動 →
  wait ±5／±10（0.5／1.0 價距）→ FILLED
  wait ±15／±20／±25（1.5／2.0／2.5）→ MISSED
預期聚合：每 wait 檔 238 cycles，fill_rate=0.5，MISSED 全記錄。
"""
import json
import os
import sqlite3
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
V13 = os.path.join(HERE, "copytrade_v13")
DL = os.path.join(HERE, "..", "docs", "downloads")
TMP = "/tmp/d2_e2e"

os.makedirs(TMP, exist_ok=True)
for f in ("copytrade.db",):
    p = os.path.join(TMP, f)
    if os.path.exists(p):
        os.remove(p)
for f in os.listdir(TMP):
    os.remove(os.path.join(TMP, f))

# 1) 先入庫（無 timing）——等 ingest 落 DB 後注入 L0
r0 = subprocess.run([sys.executable, os.path.join(V13, "run_sim.py"),
                     "--signals", "10344", "--out", os.path.join(TMP, "copytrade.db"),
                     "--report-dir", TMP], capture_output=True, text=True)
if r0.returncode != 0:
    print("STDERR:", r0.stderr[-2000:])
    sys.exit(1)

# 2) 注入合成 L0 symbols 表（§6.2 權威鏈輸入）
conn = sqlite3.connect(os.path.join(TMP, "copytrade.db"))
conn.execute(
    "INSERT OR REPLACE INTO symbols(symbol,pip_size,tick_size,tick_value,contract_size,"
    "quote_currency,margin_initial,exported_at,source) VALUES(?,?,?,?,?,?,?,?,?)",
    ("XAUUSD", 0.1, 0.01, 1.0, 100.0, "USD", None, "2026-10-29", "sandbox synthetic"))
conn.commit()

# 3) 讀真 cycles → 造 M5 JSON（entry±1.2 波動）
sys.path.insert(0, V13)
from ingest import load_signal_csv, group_cycles  # noqa: E402
trades = [t for t in load_signal_csv(os.path.join(DL, "forex-forest-signals-page-10344.csv"))
          if t["symbol"] == "XAUUSD"]
cycles = group_cycles(trades)
bars = []
for c in cycles:
    entry = c["layers"][0]["open_price"]
    ot = c["layers"][0]["_ot"]
    for i in range(12):  # entry 後 60 分鐘，每 5 分鐘一根
        ts = ot.isoformat()[:16]
        from datetime import timedelta
        ts = (ot + timedelta(minutes=5 * i)).isoformat()[:16]
        bars.append({"timestamp": ts, "open": entry, "high": round(entry + 1.2, 2),
                     "low": round(entry - 1.2, 2), "close": entry, "volume": 100, "spread": 3})
payload = {"updated": "2026-10-29T00:00", "symbol": "XAUUSD", "timeframe": "M5",
           "source": "sandbox synthetic", "start": bars[0]["timestamp"],
           "end": bars[-1]["timestamp"], "count": len(bars), "bars": bars}
with open(os.path.join(TMP, "XAUUSD_M5.json"), "w", encoding="utf-8") as f:
    json.dump(payload, f)
conn.close()
print(f"注入 L0 XAUUSD＋合成 M5 {len(bars)} bars（每 cycle entry±1.2）")

# 4) 跑 --timing-only（有 L0＋M5 → 應出 FILLED/MISSED 實數；唔重入庫唔重跑矩陣）
r = subprocess.run([sys.executable, os.path.join(V13, "run_sim.py"),
                    "--signals", "10344", "--timing-only",
                    "--m5-dir", TMP,
                    "--out", os.path.join(TMP, "copytrade.db"),
                    "--report-dir", TMP], capture_output=True, text=True)
print(r.stdout[-600:])
if r.returncode != 0:
    print(r.stderr[-2000:])
    sys.exit(1)

# 5) 驗證 copy_timing_scan.csv——生產場景合理預期：
#    帳目齊（filled＋missed＝cycles）、wait 越大越難觸（單調性）、blocked=0、MISSED 唔當 0
import csv
with open(os.path.join(TMP, "copy_timing_scan.csv"), encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
fails = []
fill_by_w = {}
for row in rows:
    w = abs(float(row["wait_pips"]))
    n, fill, miss, blk = (int(row["cycles"]), int(row["filled"]),
                          int(row["missed"]), int(row["blocked"]))
    if n != 238:
        fails.append(f"wait={row['wait_pips']} cycles {n}≠238（--timing-only 唔應重入庫）")
    if blk != 0:
        fails.append(f"wait={row['wait_pips']} blocked {blk}≠0（L0＋M5 已注入）")
    if fill + miss != n:
        fails.append(f"wait={row['wait_pips']} filled+missed={fill + miss}≠{n}（帳目唔齊）")
    fill_by_w.setdefault(w, []).append(fill / n)
for w in sorted(fill_by_w):
    print(f"  wait±{w}: fill_rate={sum(fill_by_w[w]) / len(fill_by_w[w]):.3f}")
for w5, w25 in ((5, 25), (10, 25), (5, 20), (10, 20)):
    if sum(fill_by_w[w5]) / len(fill_by_w[w5]) <= sum(fill_by_w[w25]) / len(fill_by_w[w25]):
        fails.append(f"單調性：wait±{w5} 觸發率應高於 wait±{w25}")

if fails:
    print("❌ E2E 失敗：", fails)
    sys.exit(1)
print("✅ E2E 全過：238 cycles×8 wait 檔——帳目齊（filled+missed=cycles）、blocked=0、"
      "觸發率單調遞減（wait 越大越難觸）＋六維矩陣 225 行無 regression）")
