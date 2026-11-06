#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""FIX-TD5 v1.53 靜態驗證（照 FIX-TD3 先例六項＋帳號隔離專項）"""
import re, subprocess, sys

REPO = "/home/z/my-project/exchange-repo"
V52 = f"{REPO}/exchange/from_zcode/20261107_0240_FIX-TD3_patch_TDv152/TradeDashboard_v1.52_full_preview.mq4"
V53 = f"{REPO}/exchange/from_zcode/20261107_0635_FIX-TD5_patch_TDv153/TradeDashboard_v1.53_full_preview.mq4"

src52 = open(V52, encoding="utf-8", errors="replace").read()
src53 = open(V53, encoding="utf-8", errors="replace").read()
lines53 = src53.splitlines()
fails = []

def check(name, ok, detail=""):
    print(f"{'PASS' if ok else 'FAIL'} | {name}" + (f" | {detail}" if detail else ""))
    if not ok:
        fails.append(name)

# 1) 版本號
check("1. property version=1.53", '#property version   "1.53"' in src53)
check("1b. description=v1.53", '#property description "TradeDashboard v1.53"' in src53)

# 2) FileOpen 帳號化：不應再有寫死 TD 檔 FileOpen（除 legacy 名供遷移）
bad_open = [l for l in lines53 if re.search(r'FileOpen\((TRADES_FILE|SNAP_BIN|REC_FILE|"TD_summary\.csv")\b', l)]
check("2. FileOpen 無寫死 TD 檔殘留", len(bad_open) == 0, "; ".join(bad_open[:3]) if bad_open else "0 處殘留")

# 3) helper 呼叫計數
for fn, want in [("TD_F_trades()", 2), ("TD_F_snap()", 2), ("TD_F_records()", 2), ("TD_F_summary()", 1)]:
    n = len(re.findall(re.escape(fn), src53)) - 1  # 定義行含函數名一次
    check(f"3. {fn} 呼叫={want}", n == want, f"實際 {n}（另定義 1）")

# 4) Account 欄讀寫對稱
sv = src53[src53.index("void SaveTrades()"):src53.index("void LoadTrades()")]
hdr_ok = 'FileWrite(fh, "Ticket", "Account", "Symbol"' in sv
row_ok = "IntegerToString(AccountNumber())" in sv
ld = src53[src53.index("void LoadTrades()"):]
check("4a. SaveTrades 表頭含 Account", hdr_ok)
check("4b. SaveTrades 行含帳號", row_ok)
check("4c. LoadTrades 表頭讀 14 欄", "for(int h = 0; h < 14; h++) FileReadString(fh);" in ld)
check("4d. LoadTrades 比對 skip", "if(sAcct != \"\" && sAcct != IntegerToString(AccountNumber())) continue;" in ld)

# 5) 帳號變更偵測三件套
check("5a. g_acct 定義", "int g_acct = 0;" in src53)
check("5b. OnInit 記錄+遷移", "g_acct = AccountNumber();\n   MigrateLegacyTDFiles();" in src53)
check("5c. OnTimer 偵測重載", "if(AccountNumber() != g_acct && AccountNumber() > 0)" in src53)
check("5d. 重載四件套", all(s in src53 for s in ["LoadRecordsBin();                 //", "LoadTrades();                     //", "DDG_LoadState();                  //"]))
check("5e. MigrateLegacyTDFiles 定義+呼叫", len(re.findall(r"MigrateLegacyTDFiles", src53)) == 2)

# 6) 括號平衡（paren 以 diff-in-diff 判定：v1.52 註解內半開區間記法致基線差 -1，屬既有註解字符）
for ch, op, cl in [("brace", "{", "}"), ("paren", "(", ")")]:
    if ch == "brace":
        check(f"6. {ch} 平衡", src53.count(op) == src53.count(cl), f"{src53.count(op)} vs {src53.count(cl)}")
    else:
        d52, d53 = src52.count(op) - src52.count(cl), src53.count(op) - src53.count(cl)
        check(f"6. {ch} 差值與基線一致（diff-in-diff=0）", d52 == d53, f"v1.52差{d52} v1.53差{d53}（失衡字符經定位全屬註解：L2214 bnd[i+1]) 等）")
print(f"INFO | 行數 v1.52={len(src52.splitlines())} v1.53={len(lines53)} (+{len(lines53)-len(src52.splitlines())})")

# 7) 五項 spec 落點齊
check("7. spec1 四檔前綴 helper", all(s in src53 for s in ['"trades.csv"', '"snap.bin"', '"records.csv"', '"summary.csv"']))
check("7b. spec4 legacy 三檔", all(s in src53 for s in ["TD_trades.csv.legacy", "TD_records.csv.legacy", "td4_snap.bin.legacy"]))
check("7c. summary.csv 下游無寫死殘留", '"TD_summary.csv"' not in src53)

print("=" * 50)
print("RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL: {fails}")
sys.exit(1 if fails else 0)
