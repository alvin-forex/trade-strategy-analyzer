#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_v163.py — v1.63 acceptance gates (1915/1925/2010/1850/2130), both platforms.
r2: + V19 spacer integrity (2130 §八), V20 0/empty () comments (2130 §九);
    param counts exclude spacers; MT5 sinput handled.
Gates:
  V1  version 1.63 strings (4 spots each) + no stale 1.60/1.62
  V2  input count 70 (spacers excluded) + 12 groups
  V3  input-comment hygiene: regex v[0-9]. / FIX-TD / Q# = ZERO (2010 §一 gate)
  V4  InpDefaultView default 0 (1850)
  V5  InpTelegramChatId default "" (1850/2010 §四)
  V6  InpTelegramBotToken default "" + override logic (2010 §三)
  V7  InpTelegramWhitelistUrl default URL (2010 §二)
  V8  five-button column right-aligned r3: bx0 = x+w-6s-185s (+65s); pager untouched
  V9  UNLOCK/LOCK dynamic label; no "ARM" label; ASCII-only button labels
  V10 [CLOSE ALL] in header (right of UNLOCK, bx0+68/90w); absent from tail
  V11 tail keeps LAST (BGL); allOn single; 30s cooldown semantics intact
  V12 BINGO_ArmToggle: both branches (arm 60s / manual disarm) preserved
  V13 three-state lexer: code-only brace/paren balance + L1 hygiene
  V14 MT5-only: CheckTabCmd ported (defined once, called x2, read-once delete)
  V15 MT5-only: v1.60 netting core intact (DealSeen dedup + persistence)
  V16 cross-platform parity 70/70 name+type+default (order-sensitive, spacers excluded)
  V17 .set baselines: 82 lines (70 params + 12 spacers), risk-10 = 0, chat/token
      empty, View=0, WhitelistUrl=default
  V18 fingerprint inputs untouched (InpDefaultView still read by fingerprint)
  V19 spacer integrity: 12 rows, Spacer01..12 order, uniform ─x32 + empty value,
      only at group boundaries; MT4 input / MT5 sinput keyword (2130 §八)
  V20 0/empty-default params: value-meaning "(...)" ending or 0=X enumeration (2130 §九)
Exit 0 = all machine gates PASS.
"""
import re, sys

D = "/home/z/my-project/scripts/v163"
MT4 = open(f"{D}/TradeDashboard_v1.63_final.mq4", encoding="utf-8").read()
MT5 = open(f"{D}/TradeDashboard5_v1.63_final.mq5", encoding="utf-8").read()
S4  = open(f"{D}/TradeDashboard_v1.63_baseline_riskOFF.set", encoding="utf-8").read()
S5  = open(f"{D}/TradeDashboard5_v1.63_baseline_riskOFF.set", encoding="utf-8").read()
SPACER_DASH = "─" * 32

fails = 0
def gate(name, cond, detail=""):
    global fails
    tag = "PASS" if cond else "FAIL"
    print(f"[{tag}] {name}" + (f"  ({detail})" if detail and not cond else ""))
    if not cond: fails += 1

def decls_of(src):
    """All input decls incl. sinput; returns (params, spacers) as (type,name,default,comment) tuples."""
    all_d = re.findall(r'^(s?input)\s+(\w+)\s+(\w+)\s*=\s*([^;]*);\s*//\s*(.*)$', src, re.M)
    params  = [d[1:] for d in all_d if not re.match(r'^Spacer\d{2}$', d[2])]
    spacers = [d for d in all_d if re.match(r'^Spacer\d{2}$', d[2])]
    return params, spacers

def lexer_check(src, label):
    state, depth_b, depth_p, line = 0, 0, 0, 1
    i, n = 0, len(src)
    while i < n:
        c = src[i]
        if c == "\n": line += 1
        if state == 0:
            if c == '"': state = 1
            elif c == "'":
                j = src.find("'", i+1)
                if j == -1 or j - i > 12: return False, f"{label}:{line} unterminated char/color literal"
                i = j
            elif src.startswith("//", i): state = 2
            elif src.startswith("/*", i): state = 3
            elif c == "{": depth_b += 1
            elif c == "}": depth_b -= 1
            elif c == "(": depth_p += 1
            elif c == ")": depth_p -= 1
            if depth_b < 0: return False, f"{label}:{line} brace closes before open"
        elif state == 1:
            if c == "\\": i += 1
            elif c == '"': state = 0
            elif c == "\n": return False, f"{label}:{line} bare newline inside string literal"
        elif state == 2:
            if c == "\n": state = 0
        elif state == 3:
            if src.startswith("*/", i): state = 0; i += 1
        i += 1
    if state != 0: return False, f"{label} EOF in state {state}"
    if depth_b != 0: return False, f"{label} brace imbalance {depth_b}"
    if depth_p != 0: return False, f"{label} paren imbalance {depth_p}"
    return True, f"{label} lexer clean"

for label, src, spacer_kw in (("MT4", MT4, "input"), ("MT5", MT5, "sinput")):
    params, spacers = decls_of(src)
    names = [p[1] for p in params]
    dv = {p[1]: p[2].strip() for p in params}
    cm = {p[1]: p[3] for p in params}

    gate(f"V1 {label} version 1.63 x4 + no stale",
         '#property version   "1.63"' in src
         and re.search(r'#property description "TradeDashboard v1\.63', src)
         and 'TradeDashboard v1.63' in src and 'STARTED ===' in src
         and '//=== INPUTS (v1.63: 12 groups / 70 params, two-platform aligned) ===' in src
         and '"1.60"' not in src and '"1.62"' not in src)
    gate(f"V2 {label} 70 params (spacers excluded) / 12 groups",
         len(params) == 70 and len(spacers) == 12 and src.count('input group "') == 12,
         f"params={len(params)} spacers={len(spacers)} groups={src.count('input group \"')}")
    bad = [(nm, cm[nm]) for nm in names if re.search(r'v[0-9]+\.[0-9]+|FIX-TD|Q[0-9]+\b', cm[nm])]
    gate(f"V3 {label} input comments version/ticket-free", not bad, str(bad[:3]))
    gate(f"V4 {label} InpDefaultView default 0", dv.get("InpDefaultView") == "0", dv.get("InpDefaultView"))
    gate(f"V5 {label} InpTelegramChatId default empty", dv.get("InpTelegramChatId") == '""', dv.get("InpTelegramChatId"))
    gate(f"V6a {label} InpTelegramBotToken default empty", dv.get("InpTelegramBotToken") == '""', dv.get("InpTelegramBotToken"))
    gate(f"V6b {label} BotToken override logic present",
         'if(InpTelegramBotToken != "")' in src and src.count('FileOpen(InpTelegramTokenFile') == 1)
    gate(f"V7 {label} InpTelegramWhitelistUrl default URL",
         dv.get("InpTelegramWhitelistUrl") == '"https://api.telegram.org"', dv.get("InpTelegramWhitelistUrl"))
    gate(f"V8 {label} bx0 r3 +65s flush + pager untouched",
         "int bx0 = x + w - 6*scale - 185*scale;" in src
         and "int bx0 = x + w - 6*scale - 250*scale;" not in src
         and "int bx0 = x + 340*scale;" not in src
         and src.count("x + w - 96*scale") == 1 and src.count("x + w - 64*scale") == 1
         and src.count("x + w - 32*scale") == 1)
    gate(f"V9 {label} UNLOCK/LOCK + ASCII button labels",
         '"LOCK %ds"' in src and ': "UNLOCK"' in src and '"ARM %ds"' not in src and '"ARM"' not in src
         and not [l for l in src.split("\n") if "UpdBtn(" in l and re.search(r'[^\x00-\x7f]', l)])
    gate(f"V10 {label} [CLOSE ALL] header, right of UNLOCK, not at tail",
         'UpdBtn("BGC", "[ CLOSE ALL ]", bx0 + 68*scale, ty - 2*scale, 90*scale, 13*scale, allOn);' in src
         and "x + w - 122*scale" not in src and "[ CLOSE 全倉 ]" not in src)
    gate(f"V11 {label} tail LAST only, allOn single, 30s cooldown intact",
         'UpdTxt("BGL"' in src and src.count("bool allOn =") == 1
         and src.count("g_bingoCoolAll >= 30") == 1 and "g_bingoCoolAll = TimeCurrent();" in src)
    gate(f"V12 {label} ArmToggle both branches preserved",
         src.count("void BINGO_ArmToggle()") == 1
         and "g_bingoArmed = true;" in src and "g_bingoArmed = false;" in src
         and 'BINGO: UNLOCK on (60s window)' in src and 'BINGO: LOCK (manual)' in src)
    ok, msg = lexer_check(src, label)
    gate(f"V13 {label} three-state lexer clean", ok, msg)
    # V19 spacer integrity (2130 §八)
    sp_names = [s[2] for s in spacers]
    sp_lines = [l for l in src.split("\n") if re.match(r'^' + spacer_kw + r' string Spacer\d{2}', l)]
    nxt = src.split("\n")
    gate(f"V19 {label} spacers x12 uniform at group boundaries ({spacer_kw})",
         len(sp_lines) == 12 and sp_names == [f"Spacer{i:02d}" for i in range(1, 13)]
         and all(l.split("//", 1)[1].strip() == SPACER_DASH and '= "";' in l for l in sp_lines)
         and all(nxt[nxt.index(l) + 1].startswith('input group "') for l in sp_lines)
         and not [l for l in src.split("\n") if re.match(r'^\s*input\s+string\s+___', l)],
         f"lines={len(sp_lines)}")
    # V20 () comments (2130 §九)
    paren_bad = []
    for p in params:
        nm, val, c = p[1], p[2].strip(), p[3]
        if val not in ('0', '0.0', '""'):
            continue
        ending = re.search(r'\(([^()]*\b(?:0|empty)\s*=[^()]*)\)\s*$', c)
        enum   = re.search(r'\b0\s*=\s*[A-Za-z]', c)
        if not (ending or enum):
            paren_bad.append(nm)
    gate(f"V20 {label} 0/empty-default () comments complete", not paren_bad, str(paren_bad[:5]))

gate("V14 MT5 CheckTabCmd port (1915 §五)",
     MT5.count("void CheckTabCmd()") == 1
     and MT5.count("datetime g_tabCmdLast=0;") == 1
     and MT5.count("CheckTabCmd();") == 2
     and 'FileDelete("TD_tabcmd.txt");' in MT5
     and 'ChartScreenShot(0,f,1600,900,ALIGN_LEFT);' in MT5
     and "g_bingoArmed=false;   // v1.54 FIX-TD4" in MT5)
gate("V15 MT5 netting core intact (DealSeen dedup + persistence)",
     all(k in MT5 for k in ("MarkDealSeen", "SaveSeenSet", "LoadSeenSet")))

a, _ = decls_of(MT4)
b, _ = decls_of(MT5)
diffs = [f"#{i+1} {x[1]} vs {y[1]}" for i, (x, y) in enumerate(zip(a, b))
         if x[0] != y[0] or x[1] != y[1] or x[2].strip() != y[2].strip()]
gate("V16 cross-platform parity 70/70 name+type+default", len(a) == 70 and len(b) == 70 and not diffs, str(diffs[:3]))

def setcheck(txt, label):
    lines = [l for l in txt.split("\n") if l.strip()]
    vals = dict(l.split("=", 1) for l in lines if "=" in l)
    sp = [l.split("=")[0] for l in lines if re.match(r'^Spacer\d{2}=$', l)]
    par = [l.split("=")[0] for l in lines if not re.match(r'^Spacer\d{2}=$', l)]
    risk0 = sum(1 for nm in par if re.match(r"(InpDdg\w*|InpSymbolGuardEnable|InpAutoReconnect)$", nm) and vals.get(nm) == "0")
    return (len(lines) == 82 and len(par) == 70 and len(sp) == 12
            and sp == [f"Spacer{i:02d}" for i in range(1, 13)]
            and par == [x[1] for x in a]
            and vals.get("InpDefaultView") == "0" and vals.get("InpTelegramChatId") == ""
            and vals.get("InpTelegramBotToken") == "" and vals.get("InpTelegramWhitelistUrl") == "https://api.telegram.org"
            and risk0 == 10), f"{len(lines)} lines params={len(par)} sp={len(sp)} risk0={risk0}"
for txt, label in ((S4, "MT4"), (S5, "MT5")):
    ok, det = setcheck(txt, label)
    gate(f"V17 {label} baseline .set (82 lines = 70+12, risk-10=0, empties, URL)", ok, det)

gate("V18 both platforms read InpDefaultView (fingerprint path intact)",
     MT4.count("InpDefaultView") >= 3 and MT5.count("InpDefaultView") >= 3)

print("\n" + ("ALL v1.63r3 GATES PASS — exit 0" if fails == 0 else f"{fails} GATE FAILURES"))
sys.exit(0 if fails == 0 else 1)
