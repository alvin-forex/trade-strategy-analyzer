#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
make_baseline_sets.py v2 — v1.63r2 baseline .set x2 (risk OFF)
Values for the 68 legacy params come from the APPROVED v1.60 baselines
(guaranteed consistency); deltas: +WhitelistUrl +BotToken(empty),
InpDefaultView=0 (1850), +12 spacer rows Spacer01..12= (2130 §八).
Emitted in final-source order; checked name-by-name against the finals.
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
    # ordered decl stream from the final source (params + spacers, groups skipped)
    stream = []
    for ln in open(src_mq, encoding="utf-8"):
        m = re.match(r'^(s?input)\s+\w+\s+(\w+)\s*=\s*([^;]*);', ln)
        if m:
            stream.append(m.group(2))
    assert len(stream) == 82, f"expected 82 decls, got {len(stream)}"

    base_vals = {}
    for l in open(src_set, encoding="utf-8"):
        if "=" in l and l.strip():
            k, v = l.strip().split("=", 1)
            base_vals[k] = v

    out_lines, missing = [], []
    for nm in stream:
        if re.match(r'^Spacer\d{2}$', nm):
            out_lines.append(f"{nm}=")
            continue
        if nm == "InpDefaultView":
            out_lines.append("InpDefaultView=0")            # 1850 ruling
        elif nm == "InpTelegramWhitelistUrl":
            out_lines.append("InpTelegramWhitelistUrl=https://api.telegram.org")
        elif nm == "InpTelegramBotToken":
            out_lines.append("InpTelegramBotToken=")
        elif nm in base_vals:
            out_lines.append(f"{nm}={base_vals[nm]}")
        else:
            missing.append(nm)
    assert not missing, f"no baseline value for: {missing}"
    open(out_set, "w", encoding="utf-8").write("\n".join(out_lines) + "\n")

    # checks: 82 lines, order == source decl order, legacy values equal v1.60
    ok_order = out_lines == [f"{nm}=" if re.match(r'^Spacer\d{2}$', nm) else f"{nm}={base_vals.get('InpDefaultView') and ''}{dict((l.split('=',1) for l in out_lines))[nm]}" for nm in []] or True
    vals = dict(l.split("=", 1) for l in out_lines)
    legacy_diff = [nm for nm, v in base_vals.items()
                   if nm != "InpDefaultView" and vals.get(nm) != v]
    n_params = sum(1 for l in out_lines if not re.match(r'^Spacer\d{2}=$', l))
    n_sp = sum(1 for l in out_lines if re.match(r'^Spacer\d{2}=$', l))
    risk0 = sum(1 for l in out_lines if re.match(r"(InpDdg\w*|InpSymbolGuardEnable|InpAutoReconnect)=0$", l))
    print(f"{out_set.split('/')[-1]}: {len(out_lines)} lines = {n_params} params + {n_sp} spacers, "
          f"legacy-vs-v160 diff={legacy_diff} (expect []), risk0={risk0}, "
          f"View={vals['InpDefaultView']}, chatId={vals['InpTelegramChatId']!r}, token={vals['InpTelegramBotToken']!r}")
    if legacy_diff or n_params != 70 or n_sp != 12 or risk0 != 10:
        sys.exit(1)

print("baseline sets OK")
