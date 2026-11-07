#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MT4 v1.60 -> v1.63 surgery — 9 items (1915/1925/2010/1850 + 2130 §八/§九)
  S1  version 1.60 -> 1.63 (x3 code spots + INPUTS banner comment)
  S2  input comment version-prefix strip x6 + InpDefaultView default 1->0
  S3  InpTelegramChatId source default -> "" (1850 ruling)
  S4  + InpTelegramWhitelistUrl + InpTelegramBotToken (Telegram group tail)
  S5  DDGuard table: five-button column right-aligned (bx0 = x+w-6s-250s),
      ARM -> UNLOCK/LOCK dynamic label, [CLOSE ALL] header move (right of
      UNLOCK, ASCII), tail keeps LAST only
  S6  BINGO_ArmToggle log text UNLOCK/LOCK
  S7  NGDDG_Init: InpTelegramBotToken overrides token file
  S8  (2130 §八) 12 standardized spacer rows at group boundaries —
      input string SpacerNN = ""; // ─×32 (MQL4 has no sinput; strings are
      never optimized so plain input is equivalent; excluded from the 70)
  S9  (2130 §九) 0/empty-default () comments: InpReportStart reworded,
      InpTelegramChatId empty-meaning, empty-family normalized "empty = X"
"""
import sys, re

BASE = "/home/z/my-project/scripts/v163/base_mt4_v160.mq4"
OUT  = "/home/z/my-project/scripts/v163/TradeDashboard_v1.63_final.mq4"

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

# ---------- S1: version ----------
rep('#property version   "1.60"', '#property version   "1.63"', 1, "S1a version")
rep('#property description "TradeDashboard v1.60 (two-platform aligned)"',
    '#property description "TradeDashboard v1.63 (two-platform aligned)"', 1, "S1b description")
rep('Print("=== TradeDashboard v1.60 STARTED ===',
    'Print("=== TradeDashboard v1.63 STARTED ===', 1, "S1c started print")
rep('//=== INPUTS (v1.60: 12 groups / 68 params, two-platform aligned) ===',
    '//=== INPUTS (v1.63: 12 groups / 70 params, two-platform aligned) ===', 1, "S1d inputs banner")

# ---------- S2: input comment strips + InpDefaultView default ----------
rep('input int    InpDefaultView             = 1;                                         // 0=Hour, 1=Day (v1.52 default, FIX-TD3), 2=Week, 3=Month',
    'input int    InpDefaultView             = 0;                                         // 0=Hour (default), 1=Day, 2=Week, 3=Month', 1, "S2a DefaultView=0+strip")
rep('// v1.55 FIX-TD6 addendum 608dbe5: one-shot full-history backfill, ignores SnapHours; flip back to false after the run',
    '// one-shot full-history backfill, ignores SnapHours; flip back to false after the run', 1, "S2b BackfillOnce strip")
rep('// v1.46 Q5: account-level DD guard (independent switch)',
    '// account-level DD guard (independent switch)', 1, "S2c DdgAccount strip")
rep('// v1.46 Q5: per-symbol DD guard (independent switch)',
    '// per-symbol DD guard (independent switch)', 1, "S2d DdgSymbol strip")
rep('// v1.47 Q7: new symbol default 0=ON 1=ALERT 2=BLOCK 3=CLOSE',
    '// new symbol default 0=ON 1=ALERT 2=BLOCK 3=CLOSE', 1, "S2e SymbolGuard strip")
rep('// v1.47 Q8: 0=OFF(default) 1=ALERT 2=BLOCK(new only) 3=CLOSE(new+old)',
    '// 0=OFF(default) 1=ALERT 2=BLOCK(new only) 3=CLOSE(new+old)', 1, "S2f NewsGuard strip")

# ---------- S3: TG chat ID default clear ----------
rep('input string InpTelegramChatId          = "920593269";                               // Telegram chat ID',
    'input string InpTelegramChatId          = "";                                        // Telegram chat ID (set via input/.set, never hardcoded)', 1, "S3 chatId clear")

# ---------- S4: two new inputs (Telegram group tail) ----------
rep('''input int    InpTelegramMinGapMinutes   = 10;                                        // min minutes between notifications per key

input group "Backup & Recovery"''',
    '''input int    InpTelegramMinGapMinutes   = 10;                                        // min minutes between notifications per key
input string InpTelegramWhitelistUrl    = "https://api.telegram.org";               // Whitelist this URL in firewall/proxy (copy)
input string InpTelegramBotToken        = "";                                        // Bot token direct (overrides token file; empty=use file)

input group "Backup & Recovery"''', 1, "S4 +2 inputs")

# ---------- S5: DDGuard table geometry + labels ----------
rep('''   //--- v1.60 (1400 §三, boss 13:29): CLOSE buttons INLINE — five buttons per
   //--- row right of MaxDD$; the independent CLOSE BOARD block is gone (its
   //--- 3 columns duplicated this table); ARM + pager live in the table
   //--- header, LAST + [CLOSE 全倉] in the tail. BGB_ semantics unchanged.''',
    '''   //--- v1.60 (1400 §三, boss 13:29): CLOSE buttons INLINE — five buttons per
   //--- row right of MaxDD$; the independent CLOSE BOARD block is gone (its
   //--- 3 columns duplicated this table); ARM + pager live in the table
   //--- header, LAST in the tail. BGB_ semantics unchanged.
   //--- v1.63 (1915 §一/§二, boss 19:04): five-button column RIGHT-ALIGNED to
   //---   the panel edge; ARM renamed UNLOCK/LOCK (1925); [CLOSE ALL] moved to
   //---   the header beside UNLOCK, pure-ASCII label (MQL button font mangles CJK).''', 1, "S5a block comment")

rep('   int bx0 = x + 340*scale;       // v1.60: inline button column origin',
    '   int bx0 = x + w - 6*scale - 185*scale;   // v1.63r3 (2305): five-button column +65s flush-right (boss 6DB4 pixel: gap 71px -> ~6px; was -250s)', 1, "S5b bx0 right-align")

rep('''   // v1.60: ARM + pager in the table header row (from the old board header)
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
   }''', 1, "S5c UNLOCK/LOCK + BGC header")

rep('''   // v1.60 (1400 §三): table tail — LAST + [CLOSE 全倉] (was the board footer)
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
   UpdTxt("BGL", (g_bingoLast == "" ? "LAST: -" : g_bingoLast), x, ly, clrKhaki, 9*scale);''', 1, "S5d tail LAST only")

rep('''   // v1.60 (1400 §三): independent CLOSE BOARD removed — buttons inline above,
   //   ARM/pager in the table header, LAST/[CLOSE 全倉] at the tail.''',
    '''   // v1.60 (1400 §三): independent CLOSE BOARD removed — buttons inline above.
   // v1.63 (1915 §二): UNLOCK/LOCK + [CLOSE ALL] + pager in the header, LAST at the tail.''', 1, "S5e tail comment")

# ---------- S6: BINGO_ArmToggle log text ----------
rep('      LogEvent("BINGO: ARM on (60s window)");',
    '      LogEvent("BINGO: UNLOCK on (60s window)");', 1, "S6a unlock log")
rep('      LogEvent("BINGO: ARM off (manual)");',
    '      LogEvent("BINGO: LOCK (manual)");', 1, "S6b lock log")

# ---------- S7: token override ----------
rep('''   int th = FileOpen(InpTelegramTokenFile, FILE_READ|FILE_TXT|FILE_ANSI);
   if(th != INVALID_HANDLE){ g_tgToken = FileReadString(th); StringTrimLeft(g_tgToken); StringTrimRight(g_tgToken); FileClose(th); }''',
    '''   // v1.63 (2010 §三): InpTelegramBotToken non-empty overrides the token file
   if(InpTelegramBotToken != "")
   {
      g_tgToken = InpTelegramBotToken;
      StringTrimLeft(g_tgToken); StringTrimRight(g_tgToken);
   }
   else
   {
      int th = FileOpen(InpTelegramTokenFile, FILE_READ|FILE_TXT|FILE_ANSI);
      if(th != INVALID_HANDLE){ g_tgToken = FileReadString(th); StringTrimLeft(g_tgToken); StringTrimRight(g_tgToken); FileClose(th); }
   }''', 1, "S7 token override")

# ---------- S8: group-boundary spacer rows (2130 §八) ----------
SPACER_DASH = "─" * 32
grp_lines = [l for l in src.split("\n") if l.startswith('input group "')]
assert len(grp_lines) == 12, f"expected 12 groups, got {len(grp_lines)}"
probe = next(l for l in src.split("\n") if l.startswith("input int    InpDefaultView"))
EQ_COL  = probe.index("=")
CMT_COL = probe.index("//")
for i, gl in enumerate(grp_lines, 1):
    head = f"input string Spacer{i:02d}"
    line = head.ljust(EQ_COL) + '= "";'.ljust(CMT_COL - EQ_COL) + "// " + SPACER_DASH
    old = "\n" + gl
    assert src.count(old) == 1, f"group line not unique: {gl}"
    src = src.replace(old, "\n" + line + "\n" + gl)
n_applied += 1
print(f"[ok] S8 spacer rows x12 at group boundaries (uniform ─x32, excluded from 70)")

# ---------- S9: 0/empty-default () comments (2130 §九) ----------
rep('// Report start date YYYY.MM.DD (empty=no filter)',
    '// Report start date YYYY.MM.DD (empty = from beginning)', 1, "S9a ReportStart")
rep('// Telegram chat ID (set via input/.set, never hardcoded)',
    '// Telegram chat ID (empty = no Telegram target; set via input/.set)', 1, "S9b ChatId empty-meaning")
rep('// Filter by symbol (empty=all)', '// Filter by symbol (empty = all)', 1, "S9c FilterSymbol")
rep('// Filter by comment (empty=all)', '// Filter by comment (empty = all)', 1, "S9d FilterComment")
rep('// Guarded symbols, comma-separated (empty=all)',
    '// Guarded symbols, comma-separated (empty = all)', 1, "S9e DdgSymbolList")
rep('// Custom backup root (empty=auto: UserProfile\\Downloads\\MT4\\Profiles)',
    '// Custom backup root (empty = auto: UserProfile\\Downloads\\MT4\\Profiles)', 1, "S9f BackupFolder")

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
base_lines = open(BASE, encoding="utf-8").read().count("\n")
out_lines  = out.count("\n")
chk(f"line count sane (base {base_lines} -> out {out_lines}, delta {out_lines-base_lines})",
    15 <= out_lines - base_lines <= 30)

# version (4 code spots bumped; v1.63 in new comments is expected)
chk("version 1.63 in the 4 code spots",
    '#property version   "1.63"' in out
    and 'TradeDashboard v1.63 (two-platform aligned)' in out
    and 'Print("=== TradeDashboard v1.63 STARTED ===' in out
    and '//=== INPUTS (v1.63: 12 groups / 70 params, two-platform aligned) ===' in out)
# no stale 1.60 in code strings
chk('no stale "1.60" string', '"1.60"' not in out)

# inputs (spacers excluded from the 70-param count per 2130 §八 spec revision)
m = re.findall(r'^input\s+\w+\s+(\w+)\s*=\s*([^;]*);', out, re.M)
spacers = [x[0] for x in m if re.match(r'^Spacer\d{2}$', x[0])]
params  = [(x[0], x[1]) for x in m if not re.match(r'^Spacer\d{2}$', x[0])]
names = [x[0] for x in params]
chk("70 params + 12 spacers (raw input lines 82)", len(params) == 70 and len(spacers) == 12 and len(m) == 82)
chk("spacer names Spacer01..12 in order", spacers == [f"Spacer{i:02d}" for i in range(1, 13)])
sp_lines = [l for l in out.split("\n") if re.match(r'^input string Spacer\d{2}', l)]
chk("spacer format uniform (value empty + ─x32 comment)",
    len(sp_lines) == 12 and all(l.split("//", 1)[1].strip() == SPACER_DASH and '= "";' in l for l in sp_lines))
nextline_ok = all(out.split("\n")[out.split("\n").index(l) + 1].startswith('input group "') for l in sp_lines)
chk("spacers only at group boundaries (next line = group)", nextline_ok)
chk("InpTelegramWhitelistUrl present", "InpTelegramWhitelistUrl" in names)
chk("InpTelegramBotToken present", "InpTelegramBotToken" in names)
chk("new inputs at Telegram tail order",
    names.index("InpTelegramMinGapMinutes") < names.index("InpTelegramWhitelistUrl") < names.index("InpTelegramBotToken")
    and names.index("InpTelegramBotToken") < names.index("InpAutoBackup"))
dv = dict(params)
chk("InpDefaultView default 0", dv.get("InpDefaultView", "?").strip() == "0")
chk("InpTelegramChatId default empty", dv.get("InpTelegramChatId", "?").strip() == '""')
chk("InpTelegramBotToken default empty", dv.get("InpTelegramBotToken", "?").strip() == '""')
chk("InpTelegramWhitelistUrl default URL", dv.get("InpTelegramWhitelistUrl", "?").strip() == '"https://api.telegram.org"')

# input comments: no version prefixes (v1.xx / FIX-TD / Q# tags)
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
    c = next(l.split("//", 1)[1] for l in out.split("\n") if re.match(r'^input\s+\w+\s+' + nm + r'\s*=', l))
    ending = re.search(r'\(([^()]*\b(?:0|empty)\s*=[^()]*)\)\s*$', c)
    enum   = re.search(r'\b0\s*=\s*[A-Za-z]', c)
    if not (ending or enum):
        paren_bad.append(nm)
chk(f"0/empty-default () comments complete (offenders={len(paren_bad)})", not paren_bad)
for b in paren_bad: print("   ", b)

# S5 geometry & labels
chk("bx0 right-aligned formula r3 (+65s)", "int bx0 = x + w - 6*scale - 185*scale;" in out)
chk("no old bx0 x+340", "int bx0 = x + 340*scale;" not in out)
chk("UNLOCK/LOCK armTxt", '"LOCK %ds"' in out and ': "UNLOCK"' in out and '"ARM %ds"' not in out)
chk("BGC header position (bx0+68, 90 wide)", 'UpdBtn("BGC", "[ CLOSE ALL ]", bx0 + 68*scale, ty - 2*scale, 90*scale, 13*scale, allOn);' in out)
chk("no CJK button label", "[ CLOSE 全倉 ]" not in out)
chk("BGC not at tail anymore", "x + w - 122*scale" not in out)
chk("allOn computed once", out.count("bool allOn =") == 1)
chk("tail keeps BGL LAST", 'UpdTxt("BGL"' in out)
chk("pager unchanged (BGP x+w-96/-64/-32)", out.count("x + w - 96*scale") == 1 and out.count("x + w - 64*scale") == 1 and out.count("x + w - 32*scale") == 1)

# S6 logs
chk("ArmToggle logs renamed", 'BINGO: UNLOCK on (60s window)' in out and 'BINGO: LOCK (manual)' in out and 'ARM on (60s window)' not in out)

# S7 token override
chk("token override block", "if(InpTelegramBotToken != \"\")" in out and out.count('FileOpen(InpTelegramTokenFile') == 1)

# brace / paren balance (delta vs base must be equal)
def bal(s):
    return s.count("{") - s.count("}"), s.count("(") - s.count(")")
chk(f"brace/paren delta consistent (base {bal(src0) if False else ''}".strip() + ")",
    bal(out) == bal(open(BASE, encoding='utf-8').read()))

# non-ASCII check on UpdBtn labels (ASCII rule, 1915 §二)
badbtn = [l for l in out.split("\n") if "UpdBtn(" in l and re.search(r'[^\x00-\x7f]', l)]
chk(f"UpdBtn labels all-ASCII (offenders={len(badbtn)})", not badbtn)
for b in badbtn: print("   ", b[:100])

# input block frozen except intended edits: compare against base input block
def inblock(s):
    m2 = re.search(r'//=== INPUTS.*?input group "Backup & Recovery"', s, re.S)
    return m2.group(0)
bi, oi = inblock(open(BASE, encoding='utf-8').read()), inblock(out)
import difflib
d = [l for l in difflib.unified_diff(bi.split("\n"), oi.split("\n"), n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
chk(f"input block diff lines = 37 (8 changed pairs*2 + 2 new + 11 in-block spacers + 4 S9 pairs*2)", len(d) == 37)
print("   input-block diff:")
for l in d: print("    " + l[:130])

print("\n" + ("ALL SELF-CHECKS PASS" if fails == 0 else f"{fails} FAILURES"))
sys.exit(0 if fails == 0 else 1)
