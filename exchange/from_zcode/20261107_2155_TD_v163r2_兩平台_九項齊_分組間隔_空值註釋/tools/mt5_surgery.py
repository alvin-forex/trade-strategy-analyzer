#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT5 v1.62 -> v1.63 surgery — 9 items (1915/1925/2010/1850 + 2130 §八/§九)
  T1  version 1.62 -> 1.63 (property/description/STARTED print [stale v1.60
      fixed] + INPUTS banner)
  T2  input comment version-prefix strip x4 (2010 said MT5 clean — actually 4)
  T3  InpTelegramChatId source default -> "" (1850 ruling)
  T4  + InpTelegramWhitelistUrl + InpTelegramBotToken (Telegram group tail)
  T5  DDGuard table: right-aligned bx0, UNLOCK/LOCK, [CLOSE ALL] header move
  T6  BINGO_ArmToggle log text UNLOCK/LOCK
  T7  TG_LoadToken: InpTelegramBotToken overrides token file
  T8  CheckTabCmd port (1915 §五 — hook absent from every MT5 build = the
      "MT5 tabcmd no reaction" root cause); calls in OnTick + OnTimer
  T9  (2130 §八) 12 standardized sinput spacer rows at group boundaries —
      sinput string SpacerNN = ""; // ─×32 (excluded from the 70; the letter's
      keyword — MQL5 proper non-optimizable marker)
  T10 (2130 §九) 0/empty-default () comments (same set as MT4)
"""
import sys, re

BASE = "/home/z/my-project/scripts/v163/base_mt5_v162.mq5"
OUT  = "/home/z/my-project/scripts/v163/TradeDashboard5_v1.63_final.mq5"

src = open(BASE, encoding="utf-8").read()
n_applied = 0

def rep(old, new, count=1, tag=""):
    global src, n_applied
    c = src.count(old)
    if c != count:
        print(f"[FAIL] {tag}: expected {count} occurrence(s), found {c}")
        sys.exit(1)
    src = src.replace(old, new)
    n_applied += 1
    print(f"[ok] {tag}")

# ---------- T1: version ----------
rep('#property version   "1.62"', '#property version   "1.63"', 1, "T1a version")
rep('#property description "TradeDashboard v1.62 (MT5 build, inline CLOSE board port)"',
    '#property description "TradeDashboard v1.63 (MT5 build, inline CLOSE board port)"', 1, "T1b description")
rep('Print("=== TradeDashboard v1.60 (MT5) STARTED ===',
    'Print("=== TradeDashboard v1.63 (MT5) STARTED ===', 1, "T1c started print (stale v1.60 fixed)")
rep('//=== INPUTS (v1.60: 12 groups / 68 params, two-platform aligned) ===',
    '//=== INPUTS (v1.63: 12 groups / 70 params, two-platform aligned) ===', 1, "T1d inputs banner")

# ---------- T2: input comment strips x4 ----------
rep('input bool   InpDdgAccountEnable        = true;                                      // v1.46 Q5: account-level DD guard (independent switch)',
    'input bool   InpDdgAccountEnable        = true;                                      // account-level DD guard (independent switch)', 1, "T2a DdgAccount strip")
rep('input bool   InpDdgSymbolEnable         = false;                                     // v1.46 Q5: per-symbol DD guard (independent switch)',
    'input bool   InpDdgSymbolEnable         = false;                                     // per-symbol DD guard (independent switch)', 1, "T2b DdgSymbol strip")
rep('input int    InpSymbolGuardMode         = 0;                                         // v1.47 Q7: new symbol default 0=ON 1=ALERT 2=BLOCK 3=CLOSE',
    'input int    InpSymbolGuardMode         = 0;                                         // new symbol default 0=ON 1=ALERT 2=BLOCK 3=CLOSE', 1, "T2c SymbolGuard strip")
rep('input int    InpNewsGuardMode           = 0;                                         // v1.47 Q8: 0=OFF(default) 1=ALERT 2=BLOCK(new only) 3=CLOSE(new+old)',
    'input int    InpNewsGuardMode           = 0;                                         // 0=OFF(default) 1=ALERT 2=BLOCK(new only) 3=CLOSE(new+old)', 1, "T2d NewsGuard strip")

# ---------- T3: TG chat ID default clear ----------
rep('input string InpTelegramChatId          = "920593269";                               // Telegram chat ID',
    'input string InpTelegramChatId          = "";                                        // Telegram chat ID (set via input/.set, never hardcoded)', 1, "T3 chatId clear")

# ---------- T4: two new inputs (Telegram group tail) ----------
rep('''input int    InpTelegramMinGapMinutes   = 10;                                        // min minutes between notifications per key

input group "Backup & Recovery"''',
    '''input int    InpTelegramMinGapMinutes   = 10;                                        // min minutes between notifications per key
input string InpTelegramWhitelistUrl    = "https://api.telegram.org";               // Whitelist this URL in firewall/proxy (copy)
input string InpTelegramBotToken        = "";                                        // Bot token direct (overrides token file; empty=use file)

input group "Backup & Recovery"''', 1, "T4 +2 inputs")

# ---------- T5: DDGuard table geometry + labels ----------
rep('''   //--- v1.61 (1400 §三 MT5 port): CLOSE buttons INLINE — five buttons per
   //--- row right of MaxDD$; ARM + pager live in the table header, LAST +
   //--- [CLOSE 全倉] in the tail (MT4 v1.60 parity, direct translation).''',
    '''   //--- v1.61 (1400 §三 MT5 port): CLOSE buttons INLINE — five buttons per
   //--- row right of MaxDD$; ARM + pager live in the table header, LAST in
   //--- the tail (MT4 v1.60 parity, direct translation).
   //--- v1.63 (1915 §一/§二, boss 19:04): five-button column RIGHT-ALIGNED to
   //---   the panel edge; ARM renamed UNLOCK/LOCK (1925); [CLOSE ALL] moved to
   //---   the header beside UNLOCK, pure-ASCII label (MQL button font mangles CJK).''', 1, "T5a block comment")

rep('   int bx0 = x + 340*scale;       // v1.61: inline button column origin',
    '   int bx0 = x + w - 6*scale - 250*scale;   // v1.63 (1915 §一): button column right-aligned to the panel edge', 1, "T5b bx0 right-align")

rep('''   // v1.61: ARM + pager in the table header row (MT4 v1.60 parity)
   string armTxt = g_bingoArmed ? StringFormat("ARM %ds", 60 - (int)(TimeCurrent() - g_bingoArmT)) : "ARM";
   UpdBtn("BGA", armTxt, bx0, ty - 2*scale, 64*scale, 13*scale, g_bingoArmed);
   if(g_bingoArmed) ObjectSetInteger(0, PFX+"BGA", OBJPROP_BGCOLOR, clrOrange);''',
    '''   // v1.63 (1925): ARM renamed — UNLOCK when locked (opens the 60s window);
   //   LOCK + countdown when armed (press = immediate manual re-lock).
   // v1.63 (1915 §二): [CLOSE ALL] moved from the tail into the header, right
   //   of the UNLOCK button (boss: "放在ARM鍵旁"); ASCII-only label.
   string armTxt = g_bingoArmed ? StringFormat("LOCK %ds", 60 - (int)(TimeCurrent() - g_bingoArmT)) : "UNLOCK";
   UpdBtn("BGA", armTxt, bx0, ty - 2*scale, 64*scale, 13*scale, g_bingoArmed);
   if(g_bingoArmed) ObjectSetInteger(0, PFX+"BGA", OBJPROP_BGCOLOR, clrOrange);
   bool allOn = (g_bingoArmed && TimeCurrent() - g_bingoCoolAll >= 30);   // v1.63: moved up from the tail (BGC now in the header)
   UpdBtn("BGC", "[ CLOSE ALL ]", bx0 + 68*scale, ty - 2*scale, 90*scale, 13*scale, allOn);
   if(allOn)
   {
      ObjectSetInteger(0, PFX+"BGC", OBJPROP_BGCOLOR, clrOrangeRed);
      ObjectSetInteger(0, PFX+"BGC", OBJPROP_COLOR, clrWhite);
   }''', 1, "T5c UNLOCK/LOCK + BGC header")

rep('''   // v1.61: table tail — LAST + [CLOSE 全倉] (MT4 v1.60 tail, ported)
   int ly = ty + 18*scale + shown*15*scale;
   UpdTxt("BGL", (g_bingoLast == "" ? "LAST: -" : g_bingoLast), x, ly, clrKhaki, 9*scale);
   bool allOn = (g_bingoArmed && TimeCurrent() - g_bingoCoolAll >= 30);
   UpdBtn("BGC", "[ CLOSE 全倉 ]", x + w - 122*scale, ly - 2*scale, 118*scale, 16*scale, allOn);
   if(allOn)
   {
      ObjectSetInteger(0, PFX+"BGC", OBJPROP_BGCOLOR, clrOrangeRed);
      ObjectSetInteger(0, PFX+"BGC", OBJPROP_COLOR, clrWhite);
   }''',
    '''   // v1.63 (1915 §二): table tail — LAST only ([CLOSE ALL] moved to the header)
   int ly = ty + 18*scale + shown*15*scale;
   UpdTxt("BGL", (g_bingoLast == "" ? "LAST: -" : g_bingoLast), x, ly, clrKhaki, 9*scale);''', 1, "T5d tail LAST only")

# ---------- T6: BINGO_ArmToggle log text ----------
rep('      LogEvent("BINGO: ARM on (60s window)");',
    '      LogEvent("BINGO: UNLOCK on (60s window)");', 1, "T6a unlock log")
rep('      LogEvent("BINGO: ARM off (manual)");',
    '      LogEvent("BINGO: LOCK (manual)");', 1, "T6b lock log")

# ---------- T7: TG_LoadToken override ----------
rep('''void TG_LoadToken()
{
   int th = FileOpen(InpTelegramTokenFile, FILE_READ|FILE_TXT|FILE_ANSI);''',
    '''void TG_LoadToken()
{
   // v1.63 (2010 §三): InpTelegramBotToken non-empty overrides the token file
   if(InpTelegramBotToken != "")
   {
      g_tgToken = InpTelegramBotToken;
      StringTrimLeft(g_tgToken); StringTrimRight(g_tgToken);
      return;
   }
   int th = FileOpen(InpTelegramTokenFile, FILE_READ|FILE_TXT|FILE_ANSI);''', 1, "T7 token override")

# ---------- T8: CheckTabCmd port (1915 §五) ----------
rep('''void OnTick()
{
   NGDDG_Init();''',
    '''//--- v1.63 (1915 §五): remote self-test hook ported from MT4 v1.35 — the
//---   agent writes MQL5/Files/TD_tabcmd.txt ("tab=N" and/or "snap=name");
//---   read-once semantics (MT4 v1.51 FIX-TD2): the hook file is ALWAYS
//---   deleted after read, only well-formed "tab=" acts. This hook was absent
//---   from every MT5 build — the root cause of the "MT5 tabcmd no reaction"
//---   ticket (1915 §五).
datetime g_tabCmdLast=0;
void CheckTabCmd()
{
   if(TimeLocal()-g_tabCmdLast < 2) return;   // v1.49: TimeLocal (weekend-safe)
   g_tabCmdLast=TimeCurrent();
   int h=FileOpen("TD_tabcmd.txt",FILE_READ|FILE_TXT|FILE_ANSI);
   if(h==INVALID_HANDLE) return;
   string cmd=FileReadString(h);
   FileClose(h);
   FileDelete("TD_tabcmd.txt");
   int tp=StringFind(cmd,"tab=");
   if(tp<0) return;               // v1.51 FIX-TD2: only well-formed commands act
   int ti=(int)StringToInteger(StringSubstr(cmd,tp+4));
   string snap="";
   int sp=StringFind(cmd,"snap=");
   if(sp>=0) snap=StringSubstr(cmd,sp+5);
   if(ti>=0 && ti<4 && ti!=g_tab)
   {
      g_tab=ti;
      g_bingoArmed=false;   // v1.54 FIX-TD4: ARM 解除（切 TAB，含 agent hook）
      RenderOnly();
   }
   if(snap!="")
   {
      string f="TD_tabcheck_"+snap+".png";
      ChartScreenShot(0,f,1600,900,ALIGN_LEFT);
      Print("[TD5] self-test snap ",f," tab=",g_tab);
   }
}
void OnTick()
{
   CheckTabCmd();   // v1.63 (1915 §五): agent self-test hook (MT4 v1.35 parity)
   NGDDG_Init();''', 1, "T8a CheckTabCmd + OnTick call")

rep('''   NG_WindowPush();
   BINGO_Tick();    // v1.61: ARM countdown / cooldown expiry refresh (g_tab==2 only)''',
    '''   NG_WindowPush();
   CheckTabCmd();   // v1.63 (1915 §五): agent self-test hook (also when no ticks)
   BINGO_Tick();    // v1.61: ARM countdown / cooldown expiry refresh (g_tab==2 only)''', 1, "T8b OnTimer call")

# ---------- T9: group-boundary spacer rows (2130 §八, sinput per letter) ----------
SPACER_DASH = "─" * 32
grp_lines = [l for l in src.split("\n") if l.startswith('input group "')]
assert len(grp_lines) == 12, f"expected 12 groups, got {len(grp_lines)}"
probe = next(l for l in src.split("\n") if l.startswith("input int    InpDefaultView"))
EQ_COL  = probe.index("=")
CMT_COL = probe.index("//")
for i, gl in enumerate(grp_lines, 1):
    head = f"sinput string Spacer{i:02d}"
    line = head.ljust(EQ_COL) + '= "";'.ljust(CMT_COL - EQ_COL) + "// " + SPACER_DASH
    old = "\n" + gl
    assert src.count(old) == 1, f"group line not unique: {gl}"
    src = src.replace(old, "\n" + line + "\n" + gl)
n_applied += 1
print(f"[ok] T9 spacer rows x12 at group boundaries (sinput, uniform ─×32, excluded from 70)")

# ---------- T10: 0/empty-default () comments (2130 §九) ----------
rep('// Report start date YYYY.MM.DD (empty=no filter)',
    '// Report start date YYYY.MM.DD (empty = from beginning)', 1, "T10a ReportStart")
rep('// Telegram chat ID (set via input/.set, never hardcoded)',
    '// Telegram chat ID (empty = no Telegram target; set via input/.set)', 1, "T10b ChatId empty-meaning")
rep('// Filter by symbol (empty=all)', '// Filter by symbol (empty = all)', 1, "T10c FilterSymbol")
rep('// Filter by comment (empty=all)', '// Filter by comment (empty = all)', 1, "T10d FilterComment")
rep('// Guarded symbols, comma-separated (empty=all)',
    '// Guarded symbols, comma-separated (empty = all)', 1, "T10e DdgSymbolList")
rep('// Custom backup root (empty=auto data path)',
    '// Custom backup root (empty = auto data path)', 1, "T10f BackupFolder")

open(OUT, "w", encoding="utf-8").write(src)
print(f"\n{n_applied} anchored replacements applied -> {OUT}")

# ================= SELF-CHECKS =================
print("\n--- self-checks ---")
fails = 0
def chk(name, cond):
    global fails
    print(("[ok] " if cond else "[FAIL] ") + name)
    if not cond: fails += 1

out = open(OUT, encoding="utf-8").read()
base = open(BASE, encoding="utf-8").read()
base_lines, out_lines = base.count("\n"), out.count("\n")
chk(f"line count sane (base {base_lines} -> out {out_lines}, delta {out_lines-base_lines})",
    50 <= out_lines - base_lines <= 65)

# version
chk("version 1.63 in the 4 code spots",
    '#property version   "1.63"' in out
    and 'TradeDashboard v1.63 (MT5 build, inline CLOSE board port)' in out
    and 'Print("=== TradeDashboard v1.63 (MT5) STARTED ===' in out
    and '//=== INPUTS (v1.63: 12 groups / 70 params, two-platform aligned) ===' in out)
chk('no stale "1.60"/"1.62" strings', '"1.60"' not in out and '"1.62"' not in out)

# inputs (spacers excluded from the 70-param count per 2130 §八 spec revision;
# sinput lines are not matched by ^input\s so only explicit counting is safe)
m = re.findall(r'^(?:s?input)\s+\w+\s+(\w+)\s*=\s*([^;]*);', out, re.M)
spacers = [x[0] for x in m if re.match(r'^Spacer\d{2}$', x[0])]
params  = [(x[0], x[1]) for x in m if not re.match(r'^Spacer\d{2}$', x[0])]
names = [x[0] for x in params]
chk("70 params + 12 spacers (raw decl lines 82)", len(params) == 70 and len(spacers) == 12 and len(m) == 82)
chk("spacer names Spacer01..12 in order", spacers == [f"Spacer{i:02d}" for i in range(1, 13)])
sp_lines = [l for l in out.split("\n") if re.match(r'^sinput string Spacer\d{2}', l)]
chk("spacer format uniform (sinput, value empty + ─×32 comment)",
    len(sp_lines) == 12 and all(l.split("//", 1)[1].strip() == SPACER_DASH and '= "";' in l for l in sp_lines))
nxt = out.split("\n")
chk("spacers only at group boundaries (next line = group)",
    all(nxt[nxt.index(l) + 1].startswith('input group "') for l in sp_lines))
chk("new inputs at Telegram tail order",
    names.index("InpTelegramMinGapMinutes") < names.index("InpTelegramWhitelistUrl") < names.index("InpTelegramBotToken")
    and names.index("InpTelegramBotToken") < names.index("InpAutoBackup"))
dv = dict(params)
chk("InpDefaultView default 0 (already 0 in v1.62)", dv.get("InpDefaultView", "?").strip() == "0")
chk("InpTelegramChatId default empty", dv.get("InpTelegramChatId", "?").strip() == '""')
chk("InpTelegramBotToken default empty", dv.get("InpTelegramBotToken", "?").strip() == '""')
chk("InpTelegramWhitelistUrl default URL", dv.get("InpTelegramWhitelistUrl", "?").strip() == '"https://api.telegram.org"')

# input comments: no version prefixes
bad = []
for i, line in enumerate(out.split("\n"), 1):
    if line.lstrip().startswith("input"):
        c = line.split("//", 1)[1] if "//" in line else ""
        if re.search(r'v[0-9]+\.[0-9]+|FIX-TD|Q[0-9]+\b', c):
            bad.append((i, line[:100]))
chk(f"input comments free of version/ticket prefixes (offenders={len(bad)})", not bad)
for b in bad: print("   ", b)

# (2130 §九) 0/empty-default params must carry a value-meaning parenthetical
# at the end, or a 0=X mode enumeration (OpenClaw audit convention)
paren_bad = []
for nm, val in params:
    if val.strip() not in ('0', '0.0', '""'):
        continue
    c = next(l.split("//", 1)[1] for l in out.split("\n") if re.match(r'^(?:s?input)\s+\w+\s+' + nm + r'\s*=', l))
    ending = re.search(r'\(([^()]*\b(?:0|empty)\s*=[^()]*)\)\s*$', c)
    enum   = re.search(r'\b0\s*=\s*[A-Za-z]', c)
    if not (ending or enum):
        paren_bad.append(nm)
chk(f"0/empty-default () comments complete (offenders={len(paren_bad)})", not paren_bad)
for b in paren_bad: print("   ", b)

# T5 geometry & labels
chk("bx0 right-aligned formula", "int bx0 = x + w - 6*scale - 250*scale;" in out)
chk("no old bx0 x+340", "int bx0 = x + 340*scale;" not in out)
chk("UNLOCK/LOCK armTxt", '"LOCK %ds"' in out and ': "UNLOCK"' in out and '"ARM %ds"' not in out)
chk("BGC header position (bx0+68, 90 wide)", 'UpdBtn("BGC", "[ CLOSE ALL ]", bx0 + 68*scale, ty - 2*scale, 90*scale, 13*scale, allOn);' in out)
chk("no CJK button label", "[ CLOSE 全倉 ]" not in out)
chk("BGC not at tail anymore", "x + w - 122*scale" not in out)
chk("allOn computed once", out.count("bool allOn =") == 1)
chk("tail keeps BGL LAST", 'UpdTxt("BGL"' in out)
chk("pager unchanged", out.count("x + w - 96*scale") == 1 and out.count("x + w - 64*scale") == 1 and out.count("x + w - 32*scale") == 1)

# T6 logs
chk("ArmToggle logs renamed", 'BINGO: UNLOCK on (60s window)' in out and 'BINGO: LOCK (manual)' in out and 'ARM on (60s window)' not in out)

# T7 token override
chk("token override in TG_LoadToken", "if(InpTelegramBotToken != \"\")" in out and out.count('FileOpen(InpTelegramTokenFile') == 1)

# T8 CheckTabCmd port
chk("CheckTabCmd defined once", out.count("void CheckTabCmd()") == 1)
chk("g_tabCmdLast declared once", out.count("datetime g_tabCmdLast=0;") == 1)
chk("hook calls x2 (OnTick + OnTimer)", out.count("CheckTabCmd();") == 2)
chk("read-once FileDelete present", 'FileDelete("TD_tabcmd.txt");' in out)
chk("snap ChartScreenShot present", 'ChartScreenShot(0,f,1600,900,ALIGN_LEFT);' in out)
chk("tab guard disarms ARM", "g_bingoArmed=false;   // v1.54 FIX-TD4" in out)

# brace / paren delta consistent
def bal(s):
    return s.count("{") - s.count("}"), s.count("(") - s.count(")")
chk("brace/paren delta consistent vs base", bal(out) == bal(base))

# netting core untouched (v1.60 X1 critical regions still intact)
chk("DealSeen dedup intact", "MarkDealSeen" in out and "DealSeen" in out)
chk("seen-set persistence intact", "SaveSeenSet" in out and "LoadSeenSet" in out)

# non-ASCII UpdBtn labels
badbtn = [l for l in out.split("\n") if "UpdBtn(" in l and re.search(r'[^\x00-\x7f]', l)]
chk(f"UpdBtn labels all-ASCII (offenders={len(badbtn)})", not badbtn)
for b in badbtn: print("   ", b[:100])

# input block diff vs base: 6 changed pairs (4 strips + chatId + banner) x2 + 2 added = 14
def inblock(s):
    m2 = re.search(r'//=== INPUTS.*?input group "Backup & Recovery"', s, re.S)
    return m2.group(0)
import difflib
d = [l for l in difflib.unified_diff(inblock(base).split("\n"), inblock(out).split("\n"), n=0)
     if l[:1] in "+-" and l[:3] not in ("+++", "---")]
chk(f"input block diff lines = 33 (6 changed pairs x2 + 2 new + 11 in-block spacers + 4 S9 pairs x2)", len(d) == 33)
print("   input-block diff:")
for l in d: print("    " + l[:130])

print("\n" + ("ALL SELF-CHECKS PASS" if fails == 0 else f"{fails} FAILURES"))
sys.exit(0 if fails == 0 else 1)
