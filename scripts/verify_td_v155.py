#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_td_v155.py - FIX-TD6 v1.55 static verification.
0925 根因信 §四 修法表 1-7 ＋ 608dbe5 追加 BackfillOnce 逐項落點檢查。All items must PASS."""
import io, re, sys

V155 = "/home/z/my-project/exchange-repo/exchange/from_zcode/20261107_0945_FIX-TD6_patch_TDv155/TradeDashboard_v1.55_full_preview.mq4"
V154 = "/home/z/my-project/exchange-repo/exchange/from_zcode/20261107_0831_FIX-TD4_patch_TDv154/TradeDashboard_v1.54_full_preview.mq4"

s = io.open(V155, encoding="utf-8").read()
b = io.open(V154, encoding="utf-8").read()

ok = True
results = []

def chk(name, cond, detail=""):
    global ok
    results.append(("PASS" if cond else "FAIL", name, detail))
    if not cond: ok = False

def body(src, header):
    """extract a function body by its header line up to the closing brace column-0"""
    m = re.search(re.escape(header) + r"\s*\n\{.*?\n\}", src, re.S)
    return m.group(0) if m else ""

# --- 1. version lockstep (fix 7: description finally matches) ---
chk("1  版本字串 1.55", '#property version   "1.55"' in s)
chk("2  STARTED print 1.55", 'TradeDashboard v1.55 STARTED' in s)
chk("3  description 1.55（v1.54 漏 bump 修正）", '#property description "TradeDashboard v1.55"' in s)
chk("4  v1.53/v1.54 版本殘留歸零", '#property description "TradeDashboard v1.53"' not in s and 'v1.54 STARTED' not in s)

# --- 2. sync: newest-first, no cap, window break (fixes 1+2) ---
chk("5  掃描改最新往回 for(i=histTotal-1;i>=0;i--)", "for(int i = histTotal - 1; i >= 0; i--)" in s)
chk("6  舊最舊起掃迴圈已移除", "for(int i = 0; i < histTotal; i++)" not in s)
chk("7  2000 硬上限已移除", "if(histTotal > 2000) histTotal = 2000;" not in s and "histTotal = 2000;" not in s)
chk("8  窗口外成批 break（原 continue）", "if(OrderCloseTime() < since) break;" in s and "OrderCloseTime() < since) continue;" not in s)
chk("9  MAX_HISTORY_SCAN 20000 定義", "#define MAX_HISTORY_SCAN 20000" in s)
chk("10 cap 閘 { capHit=true; break; }", "if(scanned >= MAX_HISTORY_SCAN) { capHit = true; break; }" in s)
chk("11 scanned 計數遞增", "      scanned++;" in s)
chk("12 type>OP_SELL / 開倉中 過濾照舊", "if(OrderType() > OP_SELL) continue;" in s and "if(OrderCloseTime() == 0) continue;" in s)

# --- 3. heartbeat state + panel line (fix 6) ---
chk("13 heartbeat 四全域", all(x in s for x in ["datetime g_syncLastOk = 0;", "int      g_syncNew    = 0;", "int      g_syncHist   = 0;", "bool     g_syncCap    = false;"]))
tail = body(s, "void SyncTradesFromHistory()")
chk("14 sync 尾餵 heartbeat", all(x in tail for x in ["g_syncLastOk = TimeCurrent();", "g_syncNew    = newCount;", "g_syncHist   = histTotal;", "g_syncCap    = capHit;"]))
chk("15 cap hit 記帳 SYNC CAP HIT", 'LogEvent(StringFormat("SYNC CAP HIT | scanned %d of hist %d - raise MAX_HISTORY_SCAN", scanned, histTotal));' in tail)
chk("16 面板 SYNCLN 狀態行", 'UpdTxt("SYNCLN", StringFormat("SYNC: last ok %s / new %d / hist %d%s",' in s)
chk("17 cap hit 面板橙紅 / CAP HIT", '" / CAP HIT"' in s and "clrOrangeRed : clrSilver" in s)
chk("18 SYNCLN 佔 HISTW 槽位（歷史正常時）", 'ObjectDelete(0,PFX+"HISTW");' in body(s, "void RenderOnly()"))

# --- 4. SaveTrades silent-wipe guard (fix 5) ---
st = body(s, "void SaveTrades()")
chk("19 guard: 0 trades 且檔非空唔覆寫", "if(t_tradeCount == 0 && PerAcctTradesHasData())" in st)
chk("20 guard LogEvent 原文", 'LogEvent("SAVE SKIPPED: 0 trades in memory, file non-empty (v1.55 guard)");' in st)
chk("21 guard 在 FILE_WRITE 之前", st.find("PerAcctTradesHasData()") < st.find("FILE_WRITE|FILE_CSV"))
chk("22 guard 之後 return", st.find("SAVE SKIPPED") < st.find("return;") < st.find("FILE_WRITE|FILE_CSV"))

# --- 5. MAX_TRADES 12000 + 連動陣列（fix 4） ---
chk("23 MAX_TRADES 12000", "#define MAX_TRADES 12000" in s and "#define MAX_TRADES 5000" not in s)
chk("24 g_ddUsed 同步 MAX_TRADES", "bool g_ddUsed[MAX_TRADES];" in s and "g_ddUsed[5000]" not in s)
chk("25 GetRealizedMaxDD 陣列同步", "datetime ctArr[MAX_TRADES] = {0}; double pnlArr[MAX_TRADES] = {0};" in s)
chk("26 GetRealizedMaxDD 迴圈上限同步", "n < MAX_TRADES" in s and "n < 5000" not in s)
chk("27 全檔 5000 字面值清零（MAX_REC 20000 屬 records 域）", "[5000]" not in s and " 5000;" not in s and "> 5000" not in s)

# --- 6. load-then-migrate (fix 3) ---
mg = body(s, "void MigrateLegacyTDFiles()")
chk("28 遷移閘: 舊檔有數據且新檔空", "if(m == 0 && LegacyTradesHasData() && !PerAcctTradesHasData())" in mg)
chk("29 先載入 int nLoaded = LoadTradesLegacy();", "int nLoaded = LoadTradesLegacy();" in mg)
chk("30 後改名再 SaveTrades", mg.find("LoadTradesLegacy()") < mg.find("FileMove(src3[m], 0, dst3[m], 0)") < mg.find("SaveTrades();"))
chk("31 MIGRATE load-then-park 記帳", 'LogEvent(StringFormat("MIGRATE load-then-park | Legacy rows: %d -> %s", nLoaded, TD_F_trades()));' in mg)
lg = body(s, "int LoadTradesLegacy()")
chk("32 legacy loader 13 欄 header", "for(int h = 0; h < 13; h++) FileReadString(fh);" in lg)
chk("33 legacy loader 不讀 Account 欄", "sAcct" not in lg)
chk("34 legacy loader ReportStart 過濾同 LoadTrades", s.count("if(g_reportStart > 0 && ct < g_reportStart) continue;") == 2)
chk("35 LegacyTradesHasData helper", "bool LegacyTradesHasData()" in s and "for(int h = 0; h < 13; h++) FileReadString(fh);" in body(s, "bool LegacyTradesHasData()"))
chk("36 PerAcctTradesHasData helper 14 欄", "bool PerAcctTradesHasData()" in s and "for(int h = 0; h < 14; h++) FileReadString(fh);" in body(s, "bool PerAcctTradesHasData()"))
chk("37 migration 非 trades 檔行為不變（records/snap 仍 park）", mg.count("FileMove(src3[m], 0, dst3[m], 0)") == 2)

# --- 7. regression guards (v1.50-v1.54 lessons intact) ---
chk("38 TD_F_* 帳號隔離四 helper 照舊", all(x in s for x in ["TD_F_trades()", "TD_F_snap()", "TD_F_records()", "TD_F_summary()"]))
chk("39 legacy 檔名不變", '"TD_trades.csv.legacy"' in s and '"td4_snap.bin.legacy"' in s and '"TD_records.csv.legacy"' in s)
chk("40 BINGO 板全套照舊", all(x in s for x in ["g_bingoArmed = false;", 'TG_Notify("TD_CLOSEALL"', "BINGO_Render(x, by + 36*scale, w, scale);", "if(!g_bingoArmed) return;"]))
chk("41 DDG_CloseMatch 簽名照舊", "int DDG_CloseMatch(int mode, string sym)" in s)
chk("42 mode 6 alias 轉調照舊", "return(DDG_CloseMatch(6, sym));" in s)
chk("43 OrderClose 數不變（無新增平倉迴圈）", s.count("OrderClose(") == b.count("OrderClose("))
chk("44 BG 前綴雙掃照舊（v1.50 教訓）", s.count('ObjectsDeleteAll(0, PFX+"BG");') == 2)
chk("45 panelH 垂直夾高照舊（v1.54）", "if(chartHpxV > 100 && panelH > chartHpxV - 30) panelH = chartHpxV - 30;" in s)
chk("46 tabNeedH BINGO 高度算式照舊", "+ 18 + bgRows*15 + 18 + 10;" in s)
chk("47 v1.52 撈 history 兩函數本來就最新往回（不動）", s.count("for(int i = OrdersHistoryTotal()-1; i >= 0; i--)") == b.count("for(int i = OrdersHistoryTotal()-1; i >= 0; i--)") and s.count("for(int i = histTotal - 1; i >= 0; i--)") == 1)
chk("48 SaveTrades 欄序 14 欄照舊", 'FileWrite(fh, "Ticket", "Account", "Symbol", "Type", "OpenTime", "CloseTime",' in s)
chk("49 LoadTrades 主 loader 照舊（14 欄＋帳號過濾）", "if(sAcct != \"\" && sAcct != IntegerToString(AccountNumber())) continue;" in s)
chk("50 CSV 表頭無版本 token（無需 bump，出貨信聲明）", 'FileWrite(fh, "Ticket"' in s)

# --- 8. structural parity ---
def bal(t): return t.count("{") - t.count("}")
def pal(t): return t.count("(") - t.count(")")
chk("51 brace diff-in-diff == v1.54 (v1.55=%d, v1.54=%d)" % (bal(s), bal(b)), bal(s) == bal(b))
chk("52 paren diff-in-diff == v1.54 (v1.55=%d, v1.54=%d)" % (pal(s), pal(b)), pal(s) == pal(b))
dl = s.count("\n") - b.count("\n")
chk("53 行數合理 (+%d)" % dl, 80 <= dl <= 250)
added = "".join(l for l in open(V155.replace("TradeDashboard_v1.55_full_preview.mq4", "TradeDashboard_v1.54_to_v1.55.diff")) if l.startswith("+") and not l.startswith("+++"))
removed = "".join(l for l in open(V155.replace("TradeDashboard_v1.55_full_preview.mq4", "TradeDashboard_v1.54_to_v1.55.diff")) if l.startswith("-") and not l.startswith("---"))
chk("54 diff hunk brace 淨差 = 全檔淨差", (added.count("{") - added.count("}")) - (removed.count("{") - removed.count("}")) == 0)

# --- 9. addendum 608dbe5: BackfillOnce one-shot full-history backfill ---
chk("55 追加 input BackfillOnce default false", "input bool   BackfillOnce    = false;" in s)
chk("56 追加 since 覆寫分支", "if(BackfillOnce) since = 0;" in tail and "else since = TimeCurrent() - SnapHours * 3600;" in tail)
chk("57 追加 fingerprint 併入", "IntegerToString((int)BackfillOnce)" in s)
chk("58 追加 BACKFILL DONE n= 記帳", 'LogEvent(StringFormat("BACKFILL DONE n=%d", t_tradeCount));' in tail)

for st_, name, detail in results:
    print("%s  %s" % (st_, name))
fails = [r for r in results if r[0] == "FAIL"]
print("\n%d/%d PASS" % (len(results) - len(fails), len(results)))
sys.exit(0 if ok else 1)
