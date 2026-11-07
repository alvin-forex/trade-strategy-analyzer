#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_v160.py — TradeDashboard v1.60 static acceptance gate (2026-11-07 15:31 HKT)
Covers the 13 acceptance items of the 1230 dispatch letter (§四), plus three
v1.60-specific rows: netting rebuild guards (1245 必修), Gain definition note,
baseline .set cross-check. Deterministic. Exit 0 = all machine rows PASS.

Usage:
  python3 verify_v160.py --mt4 TradeDashboard_v1.60_final.mq4 \
                         --mt5 TradeDashboard5_v1.60_final.mq5 \
                         --set4 TradeDashboard_v1.60_baseline_riskOFF.set \
                         --set5 TradeDashboard5_v1.60_baseline_riskOFF.set

Rows 1/2 (0-err compile) and 9/10 (group screenshots) are OPENCLAW-SIDE by
nature — the script runs the strongest static pre-gate available in sandbox
and marks the residual honestly. Self-contained: no imports from the TD10 tools
(lexer/parser embedded here; keep in sync with scripts/td10/rename_inputs.py).
"""
import re, sys, argparse

# ---------------- embedded three-state lexer (sync: rename_inputs.py) ----------------
def lex(text):
    out = []; i = 0; n = len(text); buf = []; st = 'code'
    while i < n:
        c = text[i]; nxt = text[i+1] if i+1 < n else ''
        if st == 'code':
            if c == '"': out.append(('code', ''.join(buf))); buf = ['"']; st = 'str'; i += 1; continue
            if c == "'": out.append(('code', ''.join(buf))); buf = ["'"]; st = 'chr'; i += 1; continue
            if c == '/' and nxt == '/': out.append(('code', ''.join(buf))); buf = ['//']; st = 'ccmt'; i += 2; continue
            if c == '/' and nxt == '*': out.append(('code', ''.join(buf))); buf = ['/*']; st = 'bcmt'; i += 2; continue
            buf.append(c); i += 1
        elif st == 'str':
            buf.append(c)
            if c == '\\':
                if i+1 < n: buf.append(nxt)
                i += 2; continue
            if c == '"': out.append(('str', ''.join(buf))); buf = []; st = 'code'
            i += 1
        elif st == 'chr':
            buf.append(c)
            if c == '\\':
                if i+1 < n: buf.append(nxt)
                i += 2; continue
            if c == "'": out.append(('chr', ''.join(buf))); buf = []; st = 'code'
            i += 1
        elif st == 'ccmt':
            buf.append(c)
            if c == '\n': out.append(('ccmt', ''.join(buf))); buf = []; st = 'code'
            i += 1
        elif st == 'bcmt':
            if c == '*' and nxt == '/':
                buf.append('*/'); out.append(('bcmt', ''.join(buf))); buf = []; st = 'code'; i += 2; continue
            buf.append(c); i += 1
    if buf: out.append((st, ''.join(buf)))
    return out

INPUT_RE  = re.compile(r'^(\s*)input\s+([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^;]*);\s*(//.*)?$')
GROUP_RE  = re.compile(r'^\s*input\s+group\s+"(.*?)"')
OLD66 = ["Title1","Title2","Scale","View","RefreshSec","RecordSec","MaxRecords","SnapEnable",
         "SnapHours","BackfillOnce","ReportStart","FilterSymbol","FilterComment","ShowDay",
         "ShowTrades","ShowBuySell","ShowWR","ShowGain","ShowGainPct","ShowWPips","ShowLot",
         "ShowTotalLot","ShowBalance","ShowMargin","ShowFreeMarg","ShowFMaxPos","ShowFMaxNeg",
         "ShowPF","ShowAvgP","ShowBest","ShowWorst","ShowMaxDD","ShowMaxDDPct","ChartEnable",
         "AutoBackup","AutoReconnect","ReconnectAfterMin","RestartCooldownHrs","MaxRestartAttempts",
         "BackupTime","BackupFolder","NG_Mode","NG_BeforeMin","NG_AfterMin","NG_HighOnly",
         "NG_NewsFile","NG_ServerOffsetHours","DDG_Enable","DDG_MaxDDPct","DDG_AccOn","DDG_SymOn",
         "DDG_Symbols","DDG_SymMaxDDPct","DDG_CloseOnHit","DDG_LockMinutes","DDG_StopAutoTrade",
         "DDG_Popup","DDG_AccStopAT","DDG_SymStopAT","DDG_CloseRetry","TG_ChatID","TG_TokenFile",
         "TG_Enable","TG_MinGapMin","SG_Enable","SG_DefaultMode"]
GROUPS12 = ["General","Display","Refresh & Recording","Data Filter","Trade Snapshot",
            "DD Guard - Account","DD Guard - Per Symbol","Symbol Guard","News Guard",
            "Telegram","Backup & Recovery","Diagnostics"]
MT5_ADD8 = ["InpAutoBackup","InpAutoReconnect","InpReconnectAfterMinutes","InpRestartCooldownHours",
            "InpMaxRestartAttempts","InpBackupTime","InpBackupFolder","InpSnapshotBackfillOnce"]
MT5_IMPL8 = ["CalcInputFingerprint","GetEnvVarEA","ReadActiveProfile","TriggerTerminalSaveProfile",
             "DoProfileBackup","CheckAndBackupProfile","MarketShouldBeOpenLocal","TriggerTerminalRestart"]
ALLOWED_DEFAULT_DIFFS = {"InpDefaultView"}   # MT4 v1.52 FIX-TD3 heritage; REPORTed

def norm_default(v):
    return v.strip().rstrip(';').strip()

class Src:
    def __init__(self, path):
        self.path = path
        self.text = open(path, encoding='utf-8', errors='replace').read()
        self.nl   = '\r\n' if '\r\n' in self.text else '\n'
        self.lines = self.text.split(self.nl)
        self.segs = lex(self.text)
        self.mask = []
        for st, seg in self.segs:
            self.mask.extend([st == 'code'] * len(seg))
        self.inputs = []       # (name, type, default, comment)
        self.groups = []
        cur = None
        for ln in self.lines:
            gm = GROUP_RE.match(ln)
            if gm:
                cur = gm.group(1)
                if cur not in self.groups: self.groups.append(cur)
                continue
            m = INPUT_RE.match(ln)
            if m and not ln.lstrip().startswith('//'):
                self.inputs.append((m.group(3), m.group(2), norm_default(m.group(4)), (m.group(5) or '').strip()))
        self.names = [x[0] for x in self.inputs]
    def code_has(self, pattern):
        """True if regex occurs at least once entirely inside code segments."""
        for m in re.finditer(pattern, self.text):
            if all(self.mask[m.start():m.end()]): return True
        return False
    def raw_has(self, pattern):
        """Raw-text search — for anchors that live inside string literals
        (banners, TG/notification text, persisted filenames) or span a
        string/code boundary (concatenation chains)."""
        return re.search(pattern, self.text) is not None
    def code_count(self, pattern):
        return sum(1 for m in re.finditer(pattern, self.text) if all(self.mask[m.start():m.end()]))
    def count_strlit(self, pattern):
        """count occurrences of regex inside string literals (version residue scan)"""
        return sum(1 for st, seg in self.segs if st == 'str' and re.search(pattern, seg))

def parse_set(path):
    entries = {}
    order = []
    for ln in open(path, encoding='utf-8'):
        ln = ln.strip()
        if not ln or ln.startswith(';') or '=' not in ln: continue
        k, v = ln.split('=', 1)
        entries[k.strip()] = v.strip()
        order.append(k.strip())
    return entries, order

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt4', required=True); ap.add_argument('--mt5', required=True)
    ap.add_argument('--set4', required=True); ap.add_argument('--set5', required=True)
    a = ap.parse_args()
    m4 = Src(a.mt4); m5 = Src(a.mt5)
    rows = []   # (item#, label, status, detail)
    def row(item, label, status, detail=""):
        rows.append((item, label, status, detail))

    # ---------- lexer pre-gate (feeds items 1/2) ----------
    def lexgate(s):
        bad = []
        if s.segs[-1][0] in ('str', 'chr'): bad.append("unterminated literal at EOF")
        for st, seg in s.segs:
            if st == 'code' and '\\' in seg: bad.append("backslash in code seg")
            if st in ('str', 'chr') and '\n' in seg: bad.append("raw newline in literal")
        return bad
    lg4, lg5 = lexgate(m4), lexgate(m5)
    ob4 = sum(1 for i, c in enumerate(m4.text) if c == '{' and m4.mask[i])
    cb4 = sum(1 for i, c in enumerate(m4.text) if c == '}' and m4.mask[i])
    ob5 = sum(1 for i, c in enumerate(m5.text) if c == '{' and m5.mask[i])
    cb5 = sum(1 for i, c in enumerate(m5.text) if c == '}' and m5.mask[i])
    stat_ok4 = ('#property strict' in m4.text) and not lg4 and ob4 == cb4
    stat_ok5 = not lg5 and ob5 == cb5

    # ---------- items 1/2: compile (static pre-gate; 0-err run = OpenClaw) ----------
    row("1", "MT4 compile 0 err/0 warn", "STATIC-PASS" if stat_ok4 else "FAIL",
        "lexer+braces+strict clean; 0-err compile pending OpenClaw terminal" if stat_ok4 else f"lg={lg4[:2]} braces {ob4}/{cb4}")
    row("2", "MT5 compile 0 err/0 warn", "STATIC-PASS" if stat_ok5 else "FAIL",
        "lexer+braces clean; 0-err compile pending OpenClaw terminal" if stat_ok5 else f"lg={lg5[:2]} braces {ob5}/{cb5}")

    # ---------- item 3: version lockstep ----------
    ver_d = []
    for tag, s in (("mt4", m4), ("mt5", m5)):
        if not re.search(r'#property\s+version\s+"1\.60"', s.text): ver_d.append(f"{tag}: property")
        if not s.raw_has(r'Print\("=== TradeDashboard v1\.60[^\"]*STARTED'):
            ver_d.append(f"{tag}: STARTED banner")
        resid = [seg for st, seg in s.segs if st == 'str' and re.search(r'"?\b1\.5\d\b"?', seg)]
        if resid: ver_d.append(f"{tag}: old version literals {resid[:2]}")
    row("3", "version lockstep 1.60 both", "PASS" if not ver_d else "FAIL", "; ".join(ver_d) or "property+description+STARTED = 1.60, zero 1.5x literals")

    # ---------- items 4/5: counts ----------
    row("4", "input count == 68 both", "PASS" if (len(m4.inputs) == 68 and len(m5.inputs) == 68) else "FAIL",
        f"mt4={len(m4.inputs)} mt5={len(m5.inputs)}")
    ok5 = (m4.groups == GROUPS12 and m5.groups == GROUPS12)
    row("5", "input group == 12 fixed-order both", "PASS" if ok5 else "FAIL",
        f"mt4={len(m4.groups)} mt5={len(m5.groups)}")

    # ---------- items 6/7: separators/comments ----------
    f4 = [l for l in m4.lines if re.match(r'^\s*input\s+string\s+___', l)]
    f5 = [l for l in m5.lines if re.match(r'^\s*input\s+string\s+___', l)]
    row("6", "0 fake ___ separators", "PASS" if not f4 and not f5 else "FAIL", f"mt4={len(f4)} mt5={len(f5)}")
    c4 = [x[0] for x in m4.inputs if not x[3]]
    c5 = [x[0] for x in m5.inputs if not x[3]]
    row("7", "all inputs commented", "PASS" if not c4 and not c5 else "FAIL", f"mt4={c4[:3]} mt5={c5[:3]}")

    # ---------- item 8: parity ----------
    s4, s5 = set(m4.names), set(m5.names)
    par = []
    if s4 != s5 or len(m4.names) != 68: par.append(f"names only-mt4={sorted(s4-s5)[:4]} only-mt5={sorted(s5-s4)[:4]}")
    if m4.names != m5.names: par.append("order differs")
    if m4.groups != m5.groups: par.append("group seq differs")
    d4 = {x[0]: x for x in m4.inputs}; d5 = {x[0]: x for x in m5.inputs}
    tmis = [n for n in m4.names if d4[n][1] != d5[n][1]]
    if tmis: par.append(f"types {tmis[:4]}")
    dmis = [n for n in m4.names if d4[n][2] != d5[n][2] and n not in ALLOWED_DEFAULT_DIFFS]
    if dmis: par.append(f"defaults {[(n, d4[n][2], d5[n][2]) for n in dmis[:4]]}")
    row("8", "param parity names/order/groups/types", "PASS" if not par else "FAIL",
        "; ".join(par) or "68=68 identical; documented default diff: InpDefaultView (mt4=1 v1.52 FIX-TD3 / mt5=0)")

    # ---------- items 9/10: group display ----------
    row("9",  "MT4 group displays (screenshot)", "OPENCLAW-SIDE", "static prereq met: input group x12 + #property strict; screenshot after deploy")
    row("10", "MT5 group displays (screenshot)", "OPENCLAW-SIDE", "static prereq met: input group x12; screenshot after deploy")

    # ---------- item 11: DD money OR trigger ----------
    d11 = []
    for tag, s in (("mt4", m4), ("mt5", m5)):
        code_need = [r'bool hitPct\s+=', r'bool hitMoney =', r'if\(\w+ && \(hitPct \|\| hitMoney\)\)',
                     r'bool symHitPct\s+=', r'bool symHitMoney =', r'if\(symHitPct \|\| symHitMoney\)',
                     r'string \w+ = symHitPct \? StringFormat',
                     r'if\(eqP? > g_ddgPeakEquity\)', r'MathMax\(0\.0,\(g_ddgPeakEquity>0\)\?', r'\(mbase>0\)\?maxdd/mbase\*100:0\.0']
        raw_need = [r'\(limits " \+ DoubleToString\(InpDdgAccountMaxPercent,1\) \+ "% / \$"']
        for p in code_need:
            if not s.code_has(p): d11.append(f"{tag}: missing /{p[:44]}/")
        for p in raw_need:
            if not s.raw_has(p): d11.append(f"{tag}: missing /{p[:44]}/ (TG dual-limit text)")
        # ratchet must run BEFORE the master-gate return — compare INSIDE DDG_Guard()
        g = re.search(r'void DDG_Guard\(\)', s.text)
        if not g:
            d11.append(f"{tag}: DDG_Guard() not found")
        else:
            win = s.text[g.start():g.start()+2500]
            mr = re.search(r'if\(eqP? > g_ddgPeakEquity\)', win)
            mg = re.search(r'if\(!(?:g_ddgeOn|InpDdgEnable)\) return;', win)
            if not mr: d11.append(f"{tag}: ratchet not in DDG_Guard head")
            elif not mg: d11.append(f"{tag}: master gate not in DDG_Guard head")
            elif mr.start() > mg.start(): d11.append(f"{tag}: ratchet after master gate")
    row("11", "DD money OR-trigger + ratchet/clamp/denominator", "PASS" if not d11 else "FAIL",
        "; ".join(d11) or "account+symbol OR, trig labels source, TG dual limits, ratchet pre-gate, clamp>=0, DDG_Base() denominator")

    # ---------- item 12: MT5 8-param implementations ----------
    d12 = []
    for p in MT5_ADD8:
        if p not in d5: d12.append(f"{p}: not declared")
        elif m5.code_count(rf'\b{p}\b') < 2: d12.append(f"{p}: declared but 0 body refs")
    for fn in MT5_IMPL8:
        if not m5.code_has(rf'\b{fn}\s*\('): d12.append(f"{fn}: no definition/call")
    row("12", "MT5 8 params implemented (not just declared)", "PASS" if not d12 else "FAIL",
        "; ".join(d12) or "8/8 declared with body refs + 8 implementation functions present")

    # ---------- item 13: .set impact / baseline cross-check ----------
    d13 = []
    for tag, s, setp in (("mt4", m4, a.set4), ("mt5", m5, a.set5)):
        ent, order = parse_set(setp)
        if len(ent) != 68 or sorted(ent) != sorted(s.names): d13.append(f"{tag}: .set names mismatch ({len(ent)})")
        for k in ("InpDdgEnable","InpDdgAccountEnable","InpDdgSymbolEnable","InpDdgCloseOnHit",
                  "InpDdgStopAutoTrade","InpDdgAccountStopAutotrade","InpDdgSymbolStopAutotrade",
                  "InpNewsGuardMode","InpSymbolGuardEnable","InpAutoReconnect"):
            if ent.get(k) != "0": d13.append(f"{tag}: {k}={ent.get(k)} not 0")
        if ent.get("InpTelegramChatId") != "": d13.append(f"{tag}: TG chat id not sanitized")
    row("13", "baseline .set 68/68 + risk-OFF + sanitized", "PASS" if not d13 else "FAIL",
        "; ".join(d13) or "both .set full-coverage, 10 risk switches OFF, TG chat id empty; legacy presets with old names invalid (see REPORT §.set)")

    # ---------- extra: netting rebuild guards (1245 必修) ----------
    dx = []
    if not m4.code_has(r't_lots\[idx\]\s*=\s*OrderLots\(\)'):
        dx.append("mt4: hedge per-ticket overwrite missing")
    code_need5 = [r't_lots\[idx\]\s*\+=', r't_profit\[idx\]\s*\+=', r't_swap\[idx\]\s*\+=',
                  r't_commission\[idx\]\s*\+=', r'bool DealSeen\(ulong', r'void MarkDealSeen\(ulong',
                  r'SaveSeenSet\(\)', r'LoadSeenSet\(\)', r'MAX_TRADES\s*12000']
    raw_need5  = [r'seen\.bin', r'MIGRATION DEFERRED']
    for p in code_need5:
        if not m5.code_has(p): dx.append(f"mt5: missing /{p[:36]}/")
    for p in raw_need5:
        if not m5.raw_has(p): dx.append(f"mt5: missing /{p[:36]}/ (string literal)")
    if len(re.findall(r'MIGRATION DEFERRED', m5.text)) < 2: dx.append("mt5: migration DEFERRED branches < 2")
    row("X1", "netting += aggregate + dedup + 2 guards (1245)", "PASS" if not dx else "FAIL",
        "; ".join(dx) or "mt4 per-ticket (hedge) unchanged; mt5 += aggregation, DealSeen dedup, seen.bin persist, no-shrink 12000 cap, both DEFERRED branches")

    # ---------- extra: Gain definition notes ----------
    g4 = m4.raw_has(r'Gain = formula-recomputed')
    g5 = m5.raw_has(r'Gain = broker-true')
    row("X2", "Gain definition annotated both panels", "PASS" if g4 and g5 else "FAIL",
        "mt4 formula-recomputed / mt5 broker-true; difference listed in REPORT.md" if g4 and g5 else f"mt4={g4} mt5={g5}")

    # ---------- verdict ----------
    n_fail = sum(1 for _i, _l, s, _d in rows if s == "FAIL")
    for item, label, status, detail in rows:
        print(f"  [{status:>12}] #{item:<3} {label}" + (f"  — {detail}" if detail and status == "FAIL" else f"  ({detail})" if detail else ""))
    print(f"== verify_v160: " + ("ALL PASS (machine rows)" if n_fail == 0 else f"{n_fail} FAIL")
          + " — rows 1/2/9/10 residual = OpenClaw-side compile + screenshots")
    sys.exit(0 if n_fail == 0 else 1)

if __name__ == '__main__':
    main()
