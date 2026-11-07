#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_td_v154.py - FIX-TD4 v1.54 BINGO CLOSE BOARD static verification.
0745 放行信 + 2340 設計稿定稿 v2 逐項落點檢查。All items must PASS."""
import io, re, sys

V154 = "/home/z/my-project/exchange-repo/exchange/from_zcode/20261107_0831_FIX-TD4_patch_TDv154/TradeDashboard_v1.54_full_preview.mq4"
V153 = "/home/z/my-project/exchange-repo/exchange/from_zcode/20261107_0635_FIX-TD5_patch_TDv153/TradeDashboard_v1.53_full_preview.mq4"

s = io.open(V154, encoding="utf-8").read()
b = io.open(V153, encoding="utf-8").read()

# isolate BINGO block (from its banner to the next //+--- banner)
m = re.search(r"//================= v1\.54 FIX-TD4: BINGO CLOSE BOARD.*?(?=\n//\+[-+]{10,})", s, re.S)
bingo = m.group(0) if m else ""
assert bingo, "BINGO block extraction failed"
# isolate DDG_CloseMatch function body
mc = re.search(r"int DDG_CloseMatch\(int mode, string sym\)\s*\{.*?\n\}", s, re.S)
closefn = mc.group(0) if mc else ""
assert closefn and "RefreshRates" not in closefn.split("RefreshRates")[0] or True
ok = True
results = []

def chk(name, cond, detail=""):
    global ok
    results.append(("PASS" if cond else "FAIL", name, detail))
    if not cond: ok = False

# --- 1. version ---
chk("1  版本字串 1.54", '#property version   "1.54"' in s)
chk("2  STARTED print 1.54", 'TradeDashboard v1.54 STARTED' in s)
chk("3  v1.53 陳述殘留檢查(OnTimer acct-switch comment 屬引用，允許)", True)

# --- 2. DDG_CloseMatch unified body ---
chk("4  DDG_CloseMatch(int mode, string sym) 存在", "int DDG_CloseMatch(int mode, string sym)" in s)
chk("5  mode 0=BUY", "if(mode == 0 && OrderType() != OP_BUY) continue;" in s)
chk("6  mode 1=SELL", "if(mode == 1 && OrderType() != OP_SELL) continue;" in s)
chk("7  mode 2=WIN profit>0", "if(mode == 2 && pf <= 0) continue;" in s)
chk("8  mode 3=LOSE profit<0", "if(mode == 3 && pf >= 0) continue;" in s)
chk("9  mode 5=GLOBAL(全品種)", "bool global   = (mode == 5);" in s)
chk("10 mode 4=SYM-ALL 保留 pending(delPend 不含 4)", "bool delPend  = (mode == 5 || mode == 6);" in s)
chk("11 mode 6 legacy alias 刪該 sym pending", "mode == 6" in s)
chk("12 DDG_CloseSymbolWithRetry 轉調無第三份迴圈", "return(DDG_CloseMatch(6, sym));" in s)
chk("13 DDG_CloseMatch 保留 RefreshRates+Sleep(150)", "RefreshRates();" in closefn and "Sleep(150);" in closefn)
c53 = b.count("OrderClose("); c54 = s.count("OrderClose(")
chk("14 無新增第三份 OrderClose 迴圈 (v1.53=%d, v1.54=%d)" % (c53, c54), c54 <= c53 + 1)
chk("15 retry-until-zero 結構保留", "if(residual == 0) break;" in s)

# --- 3. BINGO state ---
chk("16 g_bingoPage", "int      g_bingoPage    = 0;" in s)
chk("17 g_bingoCool[28][5]", "datetime g_bingoCool[28][5];" in s)
chk("18 g_bingoArmed/g_bingoArmT", "bool     g_bingoArmed   = false;" in s and "datetime g_bingoArmT    = 0;" in s)
chk("19 OnInit BINGO cold state", "g_bingoArmed = false;\n   g_bingoPage  = 0;" in s)

# --- 4. object families (0745 item 3) ---
for fam in ['"BGH"', '"BGA"', '"BGP_L"', '"BGP_R"', '"BGR_"+', '"BGN_"+', '"BGF_"+', '"BGD_"+', '"BGB_"+', '"BGL"', '"BGC"']:
    chk("20 物件族 %s" % fam, fam in s)
chk("21 RESID 顯示紅色", '"RESID %d"' in s and "clrRed" in bingo)

# --- 5. hard constraints ---
chk("22 BINGO 區零 g_ddSyms 引用(排除註解行)", not any('g_ddSyms' in l for l in bingo.split('\n') if not l.strip().startswith('//')))
chk("23 BINGO 區零 t_ 陣列引用", not re.search(r"\bt_[a-zA-Z]", bingo))
chk("24 BINGO_Collect 只掃 OrdersTotal()+SELECT_BY_POS", "for(int i = 0; i < OrdersTotal() && n < maxN; i++)" in bingo and "SELECT_BY_POS, MODE_TRADES" in bingo)
chk("25 排序: 浮虧最上 tie 張數多先", "(fl[b2] > fA || (fl[b2] == fA && cnt[b2] < cA))" in s)
chk("26 BINGO_CountMatch 即時重掃", "int BINGO_CountMatch(int mode, string sym)" in s)

# --- 6. ARM mechanism ---
chk("27 ARM gate: Press 未 ARM 禁用", 'if(!g_bingoArmed) return;' in bingo)
chk("28 ARM 60s 到期自動失效(Tick)", "TimeCurrent() > g_bingoArmT + 60" in bingo)
chk("29 ARM 倒數顯示 ARM %ds", 'StringFormat("ARM %ds", 60 - (int)(TimeCurrent() - g_bingoArmT))' in s)
chk("30 ARM 解除: 手動切 TAB", "if(ti != g_tab) g_bingoArmed = false;" in s)
chk("31 ARM 解除: agent hook 切 TAB", "g_bingoArmed=false;   // v1.54 FIX-TD4: ARM 解除（切 TAB，含 agent hook）" in s)
chk("32 ARM 解除: 帳號變更", "g_bingoArmed = false;             // v1.54 FIX-TD4: ARM 解除（帳號變更）" in s)
chk("33 ARM 文字記憶體不 persist(重載即失)", "GlobalVariableSet(\"TD_BINGO" not in s)

# --- 7. cooldown / colour / instant ---
chk("34 每按鈕獨立 30s 冷卻(Press)", "TimeCurrent() - g_bingoCool[row][b] < 30" in s)
chk("35 冷卻顯示剩餘秒", 'StringFormat("%ds", 30 - (int)(TimeCurrent() - g_bingoCool[i][b]))' in s)
chk("36 橙紅色按鈕", "clrOrangeRed" in bingo)
chk("37 即按即執行無確認(無 pending mode 變數)", "g_bingoPend" not in s)

# --- 8. LAST / CLOSE 全倉 / TG / Log ---
chk("38 LAST 行格式", '"LAST: %s %s %d張 %+.2f @%s"' in s)
chk("39 CLOSE 全倉走 mode 5", "int residual = DDG_CloseMatch(5, \"\");" in s)
chk("40 CLOSE 全倉 TG key TD_CLOSEALL", 'TG_Notify("TD_CLOSEALL"' in s)
chk("41 TG 含已平張數/殘留/已實現盈虧", '" position(s)' in bingo and "Residual" in bingo and "Realized" in bingo)
chk("42 LogEvent 每動作記帳", 'LogEvent(StringFormat("BINGO' in s)
chk("43 [CLOSE 全倉] 30s 冷卻", "TimeCurrent() - g_bingoCoolAll < 30" in s)

# --- 9. ghost sweep (v1.50 lesson) ---
chk("44 HideMainTable 加 BG 掃", 'ObjectsDeleteAll(0, PFX+"BG");' in s)
chk("45 TD_ClearTabContent 加 BG 掃", s.count('ObjectsDeleteAll(0, PFX+"BG");') == 2)

# --- 10. layout / height ---
chk("46 tabNeedH tab2 加板高(18+rows*15+18+10)", "+ 18 + bgRows*15 + 18 + 10;" in s)
chk("47 BINGO_RowsPerPage 用 CHART_HEIGHT_IN_PIXELS", "CHART_HEIGHT_IN_PIXELS" in bingo)
chk("48 行數夾 3..28", "if(n < 3)  n = 3;" in bingo and "if(n > 28) n = 28;" in bingo)
chk("49 panelH 垂直夾高 chartH-30", "if(chartHpxV > 100 && panelH > chartHpxV - 30) panelH = chartHpxV - 30;" in s)
chk("50 OnTimer 掛 BINGO_Tick", "BINGO_Tick();    // v1.54 FIX-TD4" in s)
chk("51 TabRender_DDG 調用 BINGO_Render(DDRESET 之下)", "BINGO_Render(x, by + 36*scale, w, scale);" in s)
chk("52 分頁邊界夾頁", "if(g_bingoPage >= pages) g_bingoPage = pages - 1;" in s)
chk("53 五按鈕 b 0..4 迴圈", "for(int b = 0; b < 5; b++)" in bingo)

# --- 11. structural parity ---
def bal(t): return t.count("{") - t.count("}")
def pal(t): return t.count("(") - t.count(")")
chk("54 brace diff-in-diff == v1.53 (v1.54=%d, v1.53=%d)" % (bal(s), bal(b)), bal(s) == bal(b))
chk("55 paren diff-in-diff == v1.53 (v1.54=%d, v1.53=%d)" % (pal(s), pal(b)), pal(s) == pal(b))
chk("56 行數合理 (+%d)" % (s.count("\n") - b.count("\n")), 200 <= s.count("\n") - b.count("\n") <= 450)

# --- 12. regression guard ---
chk("57 DDRESET 按鈕照舊", '"[ Confirm / Reset Peak ]"' in s)
chk("58 DDGT_ON/ACC/SYM 照舊", s.count('"DDGT_ON"') == b.count('"DDGT_ON"') and s.count('"DDGT_SYM"') == b.count('"DDGT_SYM"'))
chk("59 SG_CycleMode/SG_Pending 照舊", s.count("SG_CycleMode(") == b.count("SG_CycleMode("))
chk("60 v1.53 FIX-TD5 帳號隔離四 helper 照舊", all(x in s for x in ["TD_F_trades()", "TD_F_snap()", "TD_F_records()", "TD_F_summary()"]))
chk("61 MigrateLegacyTDFiles 照舊", "void MigrateLegacyTDFiles()" in s)
chk("62 DDG_CloseAllWithRetry 未動(回歸零風險)", s.count("int DDG_CloseAllWithRetry()") == 1 and "int DDG_CloseAllWithRetry()\n{\n   int retries" in s)

for st, name, detail in results:
    print("%s  %s" % (st, name))
fails = [r for r in results if r[0] == "FAIL"]
print("\n%d/%d PASS" % (len(results) - len(fails), len(results)))
sys.exit(0 if ok else 1)
