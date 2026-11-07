#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_baseline_sets.py — v1.63 baseline .set x2 (risk OFF), machine-generated
from the APPROVED v1.60 baselines (guaranteed consistency) + v1.63 deltas:
  + InpTelegramWhitelistUrl (default URL, not a credential)
  + InpTelegramBotToken = "" (empty — token stays out of the baseline)
  InpDefaultView = 0 (1850 ruling; MT4 side was 1)
"""
import re, sys

V160_DIR = "/home/z/my-project/exchange-repo/exchange/from_zcode/20261107_1557_TD_v160_兩平台對齊"
OUT_DIR  = "/home/z/my-project/scripts/v163"

JOBS = [
    (f"{V160_DIR}/TradeDashboard_v1.60_baseline_riskOFF.set",
     f"{OUT_DIR}/TradeDashboard_v1.63_baseline_riskOFF.set",
     f"{OUT_DIR}/TradeDashboard_v1.63_final.mq4"),
    (f"{V160_DIR}/TradeDashboard5_v1.60_baseline_riskOFF.set",
     f"{OUT_DIR}/TradeDashboard5_v1.63_baseline_riskOFF.set",
     f"{OUT_DIR}/TradeDashboard5_v1.63_final.mq5"),
]

for src_set, out_set, src_mq in JOBS:
    lines = [l.rstrip("\n") for l in open(src_set, encoding="utf-8") if l.strip()]
    out, inserted = [], False
    for l in lines:
        if l.startswith("InpDefaultView="):
            out.append("InpDefaultView=0")          # 1850 ruling: unify 0
            continue
        out.append(l)
        if l.startswith("InpTelegramMinGapMinutes=") and not inserted:
            out.append("InpTelegramWhitelistUrl=https://api.telegram.org")
            out.append("InpTelegramBotToken=")
            inserted = True
    assert inserted, "anchor InpTelegramMinGapMinutes not found"
    open(out_set, "w", encoding="utf-8").write("\n".join(out) + "\n")

    # consistency: .set names must equal the final source input names, in order
    src = open(src_mq, encoding="utf-8").read()
    mq_names = re.findall(r'^input\s+\w+\s+(\w+)\s*=', src, re.M)
    set_names = [l.split("=", 1)[0] for l in out]
    ok = mq_names == set_names
    n_risk0 = sum(1 for l in out if re.match(r"(InpDdg\w*|InpSymbolGuardEnable|InpAutoReconnect)=0$", l))
    chat = next((l for l in out if l.startswith("InpTelegramChatId=")), "?")
    tok  = next((l for l in out if l.startswith("InpTelegramBotToken=")), "?")
    dv   = next((l for l in out if l.startswith("InpDefaultView=")), "?")
    print(f"{out_set.split('/')[-1]}: {len(out)} params, order-vs-source "
          f"{'PASS' if ok else 'FAIL'}, risk-switch-0 count={n_risk0}, {dv}, {chat!r}, {tok!r}")
    if not ok:
        print("  set-only:", [n for n in set_names if n not in mq_names])
        print("  mq-only:", [n for n in mq_names if n not in set_names])
        sys.exit(1)

print("baseline sets OK")
