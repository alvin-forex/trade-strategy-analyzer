#!/usr/bin/env python3
"""build_fx.py — D2 解鎖最後一里（2026-11-01 老闆「現在做」）
由 M5 json close 計：
  1) symbols.fx_at_export（quote_cccy→USD 基準匯率，M5 最後一個 close）
  2) prices_daily 每日 close（fx_table 數據源）
  3) run_sim patch：run_matrix(...) 傳入由 prices_daily build 嘅 fx_table
零估算：M5 冇嘅 pair 照跳（周一開市重導 L0 補齊）
"""
import json, glob, os, sqlite3
from collections import defaultdict
from pathlib import Path

REPO = Path("/file".replace("/file","")).joinpath() if False else Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer")
M5DIR = REPO / "docs/data"
DB = REPO / "data/copytrade.db"

# majors→USD 匯率（1 QUOTE = x USD）：USD quote 直接 1.0
def load_m5_daily(sym):
    f = M5DIR / f"{sym}_M5.json"
    if not f.exists(): return None
    d = json.load(open(f, encoding="utf-8-sig"))
    daily = {}
    for b in d.get("bars", []):
        daily[b["timestamp"][:10]] = b["close"]   # 每日最後一個 bar close（覆蓋=取最後）
    return dict(sorted(daily.items()))

MAJORS = {}   # ccy -> {date: rate_to_usd}
for pair, ccy, inv in [("EURUSD","EUR",False),("GBPUSD","GBP",False),("AUDUSD","AUD",False),
                        ("NZDUSD","NZD",False),("USDCAD","CAD",True),("USDCHF","CHF",True),
                        ("USDJPY","JPY",True),("XAUUSD","XAU",False)]:
    daily = load_m5_daily(pair)
    if daily:
        MAJORS[ccy] = {d: (1.0/v if inv else v) for d, v in daily.items()}
        print(f"{pair} -> {ccy}: {len(daily)} 日, 最新 {list(daily.values())[-1]:.5f}")

db = sqlite3.connect(DB)
# 1) symbols.fx_at_export 注入（quote_currency→最新匯率）
rows = db.execute("SELECT symbol, quote_currency FROM symbols").fetchall()
n_fx = 0
for sym, qc in rows:
    if qc == "USD":
        rate = 1.0
    elif qc in MAJORS:
        rate = list(MAJORS[qc].values())[-1]
    else:
        continue
    db.execute("UPDATE symbols SET fx_at_export=? WHERE symbol=?", (rate, sym))
    n_fx += 1
db.commit()
print(f"symbols.fx_at_export 注入 {n_fx}/{len(rows)}")

# 2) prices_daily：majors pair 每日 close
db.execute("DELETE FROM prices_daily")
n_pd = 0
for pair, ccy, inv in [("EURUSD","EUR",False),("GBPUSD","GBP",False),("AUDUSD","AUD",False),
                        ("NZDUSD","NZD",False),("USDCAD","CAD",True),("USDCHF","CHF",True),
                        ("USDJPY","JPY",True)]:
    daily = load_m5_daily(pair)
    if not daily: continue
    for d, v in sorted(daily.items()):
        db.execute("INSERT INTO prices_daily(symbol,date,price) VALUES(?,?,?)", (pair, d, v))
        n_pd += 1
db.commit()
print(f"prices_daily {n_pd} 行")
db.close()
print("OK")
