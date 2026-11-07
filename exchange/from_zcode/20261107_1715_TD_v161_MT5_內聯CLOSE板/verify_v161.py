#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify_v161.py — static acceptance gate for TradeDashboard5 v1.61 (MT5 inline CLOSE board).

Checks (machine rows only; 0-err compile evidence is OpenClaw-side):
  V1  version 1.61 marks
  V2  BINGO engine: 7 functions, each defined exactly once
  V3  globals block: 9 state vars, cooldown array [12][5]
  V4  0745 semantics: ARM 60s auto-expiry, per-button 30s cooldown, live rescan
      (PositionsTotal in CountMatch/CloseMatch, no t_ arrays in close path),
      residual shown in LAST, cold start OnInit + account switch
  V5  render: 5 inline buttons/row (bx0=340), ARM+pager header, LAST+CLOSE全倉 tail,
      hide stale rows, 12 rows/page, cap 32
  V6  handlers: BGB_/BGA/BGC/BGP_L/BGP_R wired in OnChartEvent
  V7  OnTimer BINGO_Tick call present
  V8  executor: DDG_CloseMatch trade.PositionClose + trade.OrderDelete +
      retry loop (InpDdgCloseRetry) + residual rescan
  V9  panelW >= 620*scale on guard tab; tabNeedH covers fixed 12-row pages + tail
  V10 SCOPE FREEZE: input block byte-identical to v1.60 (68 params / 12 groups,
      InpDefaultView=0 untouched, TG chat-id default untouched — rulings pending)
  V11 brace balance in CODE-ONLY segments (strings+comments stripped)
  V12 L1 three-state lexer hygiene: code-segment bare backslash, string-segment
      raw newline, terminal state not str/chr  (the v1.60 S6c killer class)
"""
import re, sys, pathlib

V160 = pathlib.Path("/home/z/my-project/exchange-repo/exchange/from_zcode/20261107_1557_TD_v160_兩平台對齊/TradeDashboard5_v1.60_full_preview.mq5")
V161 = pathlib.Path("/home/z/my-project/scripts/v161/TradeDashboard5_v1.61_final.mq5")
a = V160.read_text(encoding="utf-8")   # baseline v1.60
b = V161.read_text(encoding="utf-8")   # candidate v1.61
res = []

def chk(name, ok, note=""):
    res.append((name, ok, note))

def g(p, t=None):
    return len(re.findall(p, b if t is None else t))

def d(p):
    """delta: count in v1.61 minus count in v1.60 baseline (same-shape source loops)."""
    return len(re.findall(p, b)) - len(re.findall(p, a))

# ---------------- three-state lexer (shared) ----------------
def lex_states(src):
    """Yield (state, char) with states: code/str/chr/comment/linecomment.
    MQL dialect: "..." strings with \\ escapes, '...' char literals,
    // line comments, /* */ block comments."""
    i, n = 0, len(src)
    st = "code"
    out = []
    while i < n:
        c = src[i]
        if st == "code":
            if c == '"': st = "str"
            elif c == "'": st = "chr"
            elif c == '/' and i+1 < n and src[i+1] == '/': st = "lcom"; i += 1
            elif c == '/' and i+1 < n and src[i+1] == '*': st = "bcom"; i += 1
        elif st == "str":
            if c == '\\': i += 2; out.append((st, c)); continue
            if c == '"': st = "code"
        elif st == "chr":
            if c == '\\': i += 2; out.append((st, c)); continue
            if c == "'": st = "code"
        elif st == "lcom":
            if c == '\n': st = "code"
        elif st == "bcom":
            if c == '*' and i+1 < n and src[i+1] == '/': st = "code"; i += 1
        out.append((st, c))
        i += 1
    return out, st

def strip_noncode(src):
    toks, _ = lex_states(src)
    return "".join(c for s, c in toks if s == "code")

# ---------------- V1 version ----------------
chk("V1 version 1.61 x3", g(r'#property version\s+"1\.61"')==1 and g(r'v1\.61 \(MT5 build, inline CLOSE board port\)')==1 and g(r'TD5 v1\.61: account switch')==1)

# ---------------- V2 engine functions ----------------
fns = ["BINGO_BtnName","BINGO_CountMatch","BINGO_ArmToggle","BINGO_Press","BINGO_CloseAll","BINGO_Tick","DDG_CloseMatch"]
bad = [f for f in fns if g(r'\b(?:int|void|string)\s+'+f+r'\s*\(')!=1]
chk("V2 engine fns defined exactly once x7", not bad, "dup/missing: "+",".join(bad))

# ---------------- V3 globals ----------------
gv = ["g_bingoPage","g_bingoCool[12][5]","g_bingoCoolAll","g_bingoArmed","g_bingoArmT","g_bingoLast","g_bingoResidSym","g_bingoResidN","g_bingoResidT"]
chk("V3 globals x9 + [12][5] cooldown", all(v in b for v in gv))

# ---------------- V4 0745 semantics ----------------
v4 = [
    g(r'g_bingoArmT \+ 60') >= 3,                      # ARM auto-expiry (Press/CloseAll/Tick)
    g(r'g_bingoCool\[row\]\[b\] < 30')==1 and g(r'g_bingoCool\[i2\]\[b\] < 30')==1,  # 30s per-button
    g(r'g_bingoCoolAll < 30')==2,                     # 30s close-all gate + Tick busy probe
    g(r'g_bingoCoolAll >= 30')==1,                    # tail button gate
    g(r'⚠RESID %d!')==2,                              # residual in LAST x2 (Press+CloseAll)
    d(r'for\(int p = PositionsTotal\(\)-1; p >= 0; p--\)')==1 and d(r'for\(int p2 = PositionsTotal\(\)-1; p2 >= 0; p2--\)')==1,
    not re.search(r'BINGO(?:_Press|_CloseAll|_CountMatch|_Tick)[\s\S]{0,400}?t_tradeCount|t_lots\[', b.split("void BINGO_Press")[1].split("//+--")[0] if "void BINGO_Press" in b else ""),
    g(r'g_bingoArmed = false;\s*\n\s*g_bingoPage\s*=\s*0;')>=2,   # cold start OnInit + acct switch
    g(r'row < 0 \|\| row >= 12')==1 and g(r'idx >= g_ddSymN \|\| idx >= 32')==1,  # bounds
]
chk("V4 0745 semantics (ARM60/cool30/live-rescan/RESID/cold/bounds)", all(v4), "; ".join(f"{i}" for i,ok in enumerate(v4) if not ok))

# ---------------- V5 render ----------------
v5 = [
    g(r'int bx0 = x \+ 340\*scale')==1,
    g(r'"BGB_"\+IntegerToString\(i2\)\+"_"\+IntegerToString\(b\)')==2,   # UpdBtn name + onm
    g(r'for\(int b = 0; b < 5; b\+\+\)')==2,          # render loop + BINGO_Tick cooldown scan
    g(r'UpdBtn\("BGA", armTxt')==1 and g(r'OBJPROP_BGCOLOR, clrOrange\)')==1,
    g(r'UpdTxt\("BGP", StringFormat\("%d/%d", g_bingoPage \+ 1, pages\)')==1,
    g(r'UpdBtn\("BGP_L"')==1 and g(r'UpdBtn\("BGP_R"')==1,
    g(r'UpdTxt\("BGL"')==1 and g(r'UpdBtn\("BGC", "\[ CLOSE 全倉 \]"')==1,
    g(r'clrOrangeRed\)')==2,                            # BGB armed + BGC armed colour pairs
    g(r'for\(int i3=0; i3<rows; i3\+\+\)')==1,          # hide stale rows
    g(r'int rows = 12;')==1 and g(r'int pages = \(g_ddSymN \+ rows - 1\) / rows;')==1,
    g(r'HideObj\("BGB_"\+IntegerToString\(i3\)\+"_"\+IntegerToString\(b3\)\)')==1,
]
chk("V5 render (buttons/header/pager/tail/hide-stale/12-per-page)", all(v5), "; ".join(f"{i}" for i,ok in enumerate(v5) if not ok))

# ---------------- V6 handlers ----------------
v6 = [g(re.escape('PFX+"'+o+'"'))>0 for o in ["BGB_","BGA","BGC","BGP_L","BGP_R"]]
chk("V6 chart-event handlers x5", all(v6))
chk("V6b BGB_ parse (row_btn split)", g(r'bgRest')==4 and g(r'StringFind\(bgRest, "_"\)')==1 and d(r'StringSubstr\(s, StringLen\(PFX\)\+4\)')==1)

# ---------------- V7 OnTimer ----------------
chk("V7 OnTimer BINGO_Tick call", g(r'BINGO_Tick\(\);')==1 and g(r'void BINGO_Tick\(\)')==1 and g(r'if\(g_tab != 2\) return;')==1)

# ---------------- V8 executor ----------------
v8 = [
    d(r'int retries = MathMax\(1, InpDdgCloseRetry\);')==1,
    d(r'if\(!trade\.PositionClose\(tk\)\)')==1,
    g(r'if\(!trade\.OrderDelete\(ot\)\)')==1,
    d(r'if\(residual == 0\) break;')==1,
    d(r'Sleep\(150\)')==1,
    g(r'ulong ot = OrderGetTicket\(p\)')==1,
]
chk("V8 DDG_CloseMatch executor (retry/close/delete/rescan)", all(v8), "; ".join(f"{i}" for i,ok in enumerate(v8) if not ok))

# ---------------- V9 panel geometry ----------------
chk("V9 panelW 620 + tabNeedH 12-row", g(r'g_tab==2 && panelW<620\*scale')==1 and g(r'\(\(g_ddSymN>0\)\?12:0\)\*15\*scale')==1)

# ---------------- V10 scope freeze: input block byte-identical ----------------
def input_lines(src):
    return [l.rstrip() for l in src.splitlines() if re.match(r'\s*input\s', l)]
la, lb = input_lines(a), input_lines(b)
chk("V10 input lines byte-identical to v1.60 (68 params + 12 groups frozen)", la == lb,
    f"v160={len(la)} lines, v161={len(lb)} lines, equal={la == lb}")
chk("V10b InpDefaultView default untouched", g(r'InpDefaultView\s*=\s*0')==1, "default must stay 0 (ruling pending)")
chk("V10c TG chat-id default untouched (ruling pending)",
    re.search(r'InpTelegramChatId\s*=\s*"[^"]*"', a).group(0) == re.search(r'InpTelegramChatId\s*=\s*"[^"]*"', b).group(0))
chk("V10d param count parity", g(r'(?m)^\s*input\s')==len(re.findall(r'(?m)^\s*input\s', a)) and g(r'(?m)^\s*input\s+group')==12)

# ---------------- V11 brace balance, code-only ----------------
code_b = strip_noncode(b)
code_a = strip_noncode(a)
chk("V11 brace balance (code-only)", code_b.count('{')==code_b.count('}'), f"{code_b.count('{')}/{code_b.count('}')}")
chk("V11b brace delta vs v1.60 = even", (code_b.count('{')-code_a.count('{'))==(code_b.count('}')-code_a.count('}')))

# ---------------- V12 L1 lexer hygiene ----------------
toks, final = lex_states(b)
bare_bs   = sum(1 for s,c in toks if s=="code" and c=="\\")
str_nl    = sum(1 for s,c in toks if s=="str" and c=="\n")
term_bad  = final in ("str","chr")
chk("V12 L1 lexer (code-\\ =0, str-newline =0, terminal ok)", bare_bs==0 and str_nl==0 and not term_bad,
    f"bare_backslash={bare_bs} str_newline={str_nl} terminal={final}")
# baseline v1.60 must also be clean (control)
toks_a, final_a = lex_states(a)
chk("V12b baseline v1.60 lexer control", sum(1 for s,c in toks_a if s=="code" and c=="\\")==0
    and sum(1 for s,c in toks_a if s=="str" and c=="\n")==0 and final_a not in ("str","chr"))

# ---------------- report ----------------
npass = sum(1 for _,ok,_ in res if ok)
print(f"verify_v161: {npass}/{len(res)} PASS  (file={V161.name}, {b.count(chr(10))+1} lines)")
for name, ok, note in res:
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}" + (f"  [{note}]" if note and not ok else ""))
    if note and ok and name.startswith("V10"):
        print(f"        {note}")
sys.exit(0 if npass==len(res) else 1)
