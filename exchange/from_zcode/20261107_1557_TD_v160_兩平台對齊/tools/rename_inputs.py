#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TD10 #1 rename_inputs.py — v1.60 two-platform input alignment (rebuild 2026-11-07 14:25 HKT)
Spec source: exchange/from_openclaw/20261107_1230_總派工_TD_v160_兩平台對齊.md §三 (66-row table)
ALL-PASS criteria (from 1325 §五): MT4 66+2=68 / MT5 58+8+2=68 inputs, 12 groups,
0 old-name residue, 0 fake separators, all inputs commented, brace balance.
Deterministic: input = source file + embedded mapping. No human judgement.

Three-state lexer: rename applies to CODE segments only (strings/comments untouched).
"""
import re, sys, argparse

# ---------------- 66-row mapping (1230 §三, MT4 v1.55 file order) ----------------
# (old, new, group)
MAP66 = [
    ("Title1","InpTitleLine1","General"),
    ("Title2","InpTitleLine2","General"),
    ("Scale","InpPanelScale","General"),
    ("View","InpDefaultView","General"),
    ("RefreshSec","InpRefreshSeconds","Refresh & Recording"),
    ("RecordSec","InpRecordSeconds","Refresh & Recording"),
    ("MaxRecords","InpMaxRecords","Refresh & Recording"),
    ("SnapEnable","InpSnapshotEnable","Trade Snapshot"),
    ("SnapHours","InpSnapshotHours","Trade Snapshot"),
    ("BackfillOnce","InpSnapshotBackfillOnce","Trade Snapshot"),
    ("ReportStart","InpReportStart","Data Filter"),
    ("FilterSymbol","InpFilterSymbol","Data Filter"),
    ("FilterComment","InpFilterComment","Data Filter"),
    ("ShowDay","InpShowDay","Display"),
    ("ShowTrades","InpShowTrades","Display"),
    ("ShowBuySell","InpShowBuySell","Display"),
    ("ShowWR","InpShowWinRate","Display"),
    ("ShowGain","InpShowGainMoney","Display"),
    ("ShowGainPct","InpShowGainPercent","Display"),
    ("ShowWPips","InpShowPips","Display"),
    ("ShowLot","InpShowLots","Display"),
    ("ShowTotalLot","InpShowTotalLots","Display"),
    ("ShowBalance","InpShowBalance","Display"),
    ("ShowMargin","InpShowMargin","Display"),
    ("ShowFreeMarg","InpShowFreeMargin","Display"),
    ("ShowFMaxPos","InpShowFloatPeakProfit","Display"),
    ("ShowFMaxNeg","InpShowFloatPeakLoss","Display"),
    ("ShowPF","InpShowProfitFactor","Display"),
    ("ShowAvgP","InpShowAvgPnl","Display"),
    ("ShowBest","InpShowBestTrade","Display"),
    ("ShowWorst","InpShowWorstTrade","Display"),
    ("ShowMaxDD","InpShowMaxDdMoney","Display"),
    ("ShowMaxDDPct","InpShowMaxDdPercent","Display"),
    ("ChartEnable","InpShowPnlChart","Display"),
    ("AutoBackup","InpAutoBackup","Backup & Recovery"),
    ("AutoReconnect","InpAutoReconnect","Backup & Recovery"),
    ("ReconnectAfterMin","InpReconnectAfterMinutes","Backup & Recovery"),
    ("RestartCooldownHrs","InpRestartCooldownHours","Backup & Recovery"),
    ("MaxRestartAttempts","InpMaxRestartAttempts","Backup & Recovery"),
    ("BackupTime","InpBackupTime","Backup & Recovery"),
    ("BackupFolder","InpBackupFolder","Backup & Recovery"),
    ("NG_Mode","InpNewsGuardMode","News Guard"),
    ("NG_BeforeMin","InpNewsBeforeMinutes","News Guard"),
    ("NG_AfterMin","InpNewsAfterMinutes","News Guard"),
    ("NG_HighOnly","InpNewsHighImpactOnly","News Guard"),
    ("NG_NewsFile","InpNewsFile","News Guard"),
    ("NG_ServerOffsetHours","InpNewsServerOffsetHours","News Guard"),
    ("DDG_Enable","InpDdgEnable","DD Guard - Account"),
    ("DDG_MaxDDPct","InpDdgAccountMaxPercent","DD Guard - Account"),
    ("DDG_AccOn","InpDdgAccountEnable","DD Guard - Account"),
    ("DDG_SymOn","InpDdgSymbolEnable","DD Guard - Per Symbol"),
    ("DDG_Symbols","InpDdgSymbolList","DD Guard - Per Symbol"),
    ("DDG_SymMaxDDPct","InpDdgSymbolMaxPercent","DD Guard - Per Symbol"),
    ("DDG_CloseOnHit","InpDdgCloseOnHit","DD Guard - Account"),
    ("DDG_LockMinutes","InpDdgLockMinutes","DD Guard - Account"),
    ("DDG_StopAutoTrade","InpDdgStopAutoTrade","DD Guard - Account"),
    ("DDG_Popup","InpDdgAlertPopup","DD Guard - Account"),
    ("DDG_AccStopAT","InpDdgAccountStopAutotrade","DD Guard - Account"),
    ("DDG_SymStopAT","InpDdgSymbolStopAutotrade","DD Guard - Per Symbol"),
    ("DDG_CloseRetry","InpDdgCloseRetry","DD Guard - Account"),
    ("TG_ChatID","InpTelegramChatId","Telegram"),
    ("TG_TokenFile","InpTelegramTokenFile","Telegram"),
    ("TG_Enable","InpTelegramEnable","Telegram"),
    ("TG_MinGapMin","InpTelegramMinGapMinutes","Telegram"),
    ("SG_Enable","InpSymbolGuardEnable","Symbol Guard"),
    ("SG_DefaultMode","InpSymbolGuardMode","Symbol Guard"),
]

GROUPS12 = ["General","Display","Refresh & Recording","Data Filter","Trade Snapshot",
            "DD Guard - Account","DD Guard - Per Symbol","Symbol Guard","News Guard",
            "Telegram","Backup & Recovery","Diagnostics"]

# 2 new params (1230 §3.3) — inserted after their % sibling in group order
NEW2 = {
    "InpDdgAccountMaxMoney": ("double","0.0","Account max drawdown in money (0 = off)","DD Guard - Account","InpDdgAccountMaxPercent"),
    "InpDdgSymbolMaxMoney":  ("double","0.0","Per-symbol max drawdown in money (0 = off)","DD Guard - Per Symbol","InpDdgSymbolMaxPercent"),
}

# 8 MT5-only additions (1230 §3.2) — defaults copied from MT4 v1.55, comments adapted
MT5_ADD8 = {
    "InpAutoBackup":           ("bool","true","Enable daily auto backup on change","Backup & Recovery","InpBackupTime"),
    "InpAutoReconnect":        ("bool","true","Auto-restart terminal on stuck disconnect","Backup & Recovery","InpAutoBackup"),
    "InpReconnectAfterMinutes":("int","10","Sustained disconnect minutes before restart","Backup & Recovery","InpAutoReconnect"),
    "InpRestartCooldownHours": ("int","2","Min hours between restarts","Backup & Recovery","InpReconnectAfterMinutes"),
    "InpMaxRestartAttempts":   ("int","3","Give up after N consecutive failed restarts","Backup & Recovery","InpRestartCooldownHours"),
    "InpBackupTime":           ("string","\"05:30\"","Daily check time, server time HH:MM","Backup & Recovery","InpMaxRestartAttempts"),
    "InpBackupFolder":         ("string","\"\"","Custom backup root (empty=auto data path)","Backup & Recovery","InpBackupTime"),
    "InpSnapshotBackfillOnce": ("bool","false","One-shot full-history backfill, flip back after run","Trade Snapshot","InpSnapshotHours"),
}

# comments for inputs that lack one in source (English, <=55 chars)
MISSING_COMMENT = {
    "InpPanelScale":"Panel size multiplier (1, 2 or 3)",
    "InpRefreshSeconds":"Panel refresh interval in seconds",
    "InpShowDay":"Show Day column in stats table",
    "InpShowTrades":"Show trade count column",
    "InpShowWinRate":"Show win rate column",
    "InpShowGainMoney":"Show gain in money column",
    "InpShowGainPercent":"Show gain in percent column",
    "InpShowPips":"Show net pips column",
    "InpShowLots":"Show lots column",
    "InpShowTotalLots":"Show total lots row",
    "InpShowBalance":"Show balance row",
    "InpShowMargin":"Show margin row",
    "InpShowFreeMargin":"Show free margin row",
    "InpShowProfitFactor":"Show profit factor row",
    "InpShowAvgPnl":"Show average P/L row",
    "InpShowBestTrade":"Show best trade row",
    "InpShowWorstTrade":"Show worst trade row",
    "InpNewsBeforeMinutes":"Minutes before news event to guard",
    "InpNewsAfterMinutes":"Minutes after news event to guard",
    "InpNewsHighImpactOnly":"Guard high-impact news only",
    "InpNewsFile":"News calendar CSV file name",
    "InpDdgSymbolList":"Guarded symbols, comma-separated (empty=all)",
    "InpDdgAlertPopup":"Show alert popup on trigger",
    "InpTelegramChatId":"Telegram chat ID",
    "InpTelegramTokenFile":"File name holding the bot token",
    "InpTelegramEnable":"Enable Telegram notifications",
}

# ---------------- three-state lexer ----------------
def lex(text):
    """Yield (state, text) segments. state in {'code','str','chr','ccmt','bcmt'}."""
    out=[]; i=0; n=len(text); buf=[]; st='code'
    while i < n:
        c = text[i]; nxt = text[i+1] if i+1 < n else ''
        if st == 'code':
            if c == '"': out.append(('code',''.join(buf))); buf=['"']; st='str'; i+=1; continue
            if c == "'": out.append(('code',''.join(buf))); buf=["'"]; st='chr'; i+=1; continue
            if c == '/' and nxt == '/': out.append(('code',''.join(buf))); buf=['//']; st='ccmt'; i+=2; continue
            if c == '/' and nxt == '*': out.append(('code',''.join(buf))); buf=['/*']; st='bcmt'; i+=2; continue
            buf.append(c); i+=1
        elif st == 'str':
            buf.append(c)
            if c == '\\':
                if i+1 < n: buf.append(nxt)
                i+=2; continue
            if c == '"': out.append(('str',''.join(buf))); buf=[]; st='code'
            i+=1
        elif st == 'chr':
            buf.append(c)
            if c == '\\':
                if i+1 < n: buf.append(nxt)
                i+=2; continue
            if c == "'": out.append(('chr',''.join(buf))); buf=[]; st='code'
            i+=1
        elif st == 'ccmt':
            buf.append(c)
            if c == '\n': out.append(('ccmt',''.join(buf))); buf=[]; st='code'
            i+=1
        elif st == 'bcmt':
            if c == '*' and nxt == '/':
                buf.append('*/'); out.append(('bcmt',''.join(buf))); buf=[]; st='code'; i+=2; continue
            buf.append(c); i+=1
    if buf: out.append((st if st!='code' else 'code',''.join(buf)))
    return out

def code_mask(text):
    """Boolean list: True if char is in a code segment (not string/char/comment)."""
    segs = lex(text); mask=[]
    for st, seg in segs:
        mask.extend([st=='code']*len(seg))
    assert len(mask)==len(text), f"mask len {len(mask)} != text {len(text)}"
    return mask

INPUT_RE = re.compile(r'^(\s*)input\s+([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)(//.*)?\s*$')  # g5 = comment
FAKE_RE  = re.compile(r'^\s*input\s+string\s+___')

def parse_inputs(lines):
    """Return list of (line_index, decl_or_None_for_fake)."""
    decls=[]
    for idx, ln in enumerate(lines):
        if FAKE_RE.match(ln): decls.append((idx, None)); continue
        if ln.lstrip().startswith('//'): continue
        m = INPUT_RE.match(ln)
        if m:
            cmt = m.group(5) or ''
            # normalize default: source lines carry the trailing ';' inside the
            # match; strip it here and ALWAYS re-emit it in the rebuilt block
            # (v1.60 bugfix: additions were written without ';' -> compile error)
            dflt = m.group(4).strip()
            if dflt.endswith(';'):            # strip ONE trailing terminator only —
                dflt = dflt[:-1].rstrip()     # never touches ';' inside "string" defaults
            decls.append((idx, {'indent':m.group(1),'type':m.group(2),'name':m.group(3),
                                'default':dflt,'comment':cmt.strip()}))
    return decls

def transform(path, out_path, platform):
    raw = open(path, 'rb').read()
    text = raw.decode('utf-8', errors='replace')
    nl = '\r\n' if '\r\n' in text else '\n'
    lines = text.split(nl)

    if platform=='mt4' and '#property strict' not in text:
        return ("FAIL", "MT4 source lacks #property strict — input group would not compile")

    decls = parse_inputs(lines)
    real = [(i,d) for i,d in decls if d]
    if not real: return ("FAIL","no input declarations found")
    first = decls[0][0]; last = decls[-1][0]
    for i in range(first, last+1):
        s = lines[i].strip()
        if s and not (s.startswith('input') or s.startswith('//')):
            return ("FAIL", f"non-input line inside input block at line {i+1}: {s[:60]}")

    declared = {d['name']: d for _, d in real}
    oldnames = [o for o,_,_ in MAP66]
    missing_on_this = [o for o in oldnames if o not in declared]
    if platform=='mt5':
        expect_missing = ["BackfillOnce","AutoBackup","BackupTime","BackupFolder","AutoReconnect",
                          "ReconnectAfterMin","RestartCooldownHrs","MaxRestartAttempts"]
        if sorted(missing_on_this) != sorted(expect_missing):
            return ("FAIL", f"MT5 missing set mismatch: {missing_on_this}")
    else:
        if missing_on_this: return ("FAIL", f"MT4 missing inputs: {missing_on_this}")
    extra = [n for n in declared if n not in oldnames]
    if extra: return ("FAIL", f"unknown inputs not in 66-table: {extra}")

    # rename identifiers, code segments only, exact-case whole-word
    # single combined pass: match positions stay relative to the ORIGINAL text,
    # so the code mask (computed on the original) stays aligned.
    mask = code_mask(text)
    renames_done = 0
    alt = re.compile(r'(?<![A-Za-z0-9_])(?:' + '|'.join(re.escape(o) for o,_n,_g in
                 sorted(MAP66, key=lambda r: -len(r[0]))) + r')(?![A-Za-z0-9_])')
    old2new = {o: n for o, n, _g in MAP66}
    def rep(m):
        nonlocal renames_done
        a,b = m.start(), m.end()
        if all(mask[a:b]):
            renames_done += 1
            return old2new[m.group(0)]
        return m.group(0)
    newtext = alt.sub(rep, text)
    # re-split AFTER renaming so the rebuilt block keeps body renames
    lines = newtext.split(nl)

    # rebuild the input block in fixed 12-group order
    per_group = {g: [] for g in GROUPS12}
    for old, new, grp in MAP66:
        if old not in declared:      # MT5 lacks the 8 backup/reconnect/backfill params
            continue                 # (they come back via MT5_ADD8 below)
        d = declared[old]
        cmt = d['comment']
        if not cmt: cmt = MISSING_COMMENT.get(new, "")
        if cmt:
            cmt = cmt if cmt.startswith('//') else '// '+cmt
        per_group[grp].append((new, d['type'], d['default'], cmt))
    additions = dict(MT5_ADD8) if platform=='mt5' else {}
    additions.update(NEW2)
    for name,(typ,dflt,cmt,grp,anchor) in additions.items():
        entry = (name, typ, dflt, '// '+cmt)
        lst = per_group[grp]
        pos = next((i for i,(n,_t,_d,_c) in enumerate(lst) if n==anchor), len(lst))
        lst.insert(pos+1, entry)
    maxlen = max(len(n) for g in GROUPS12 for (n,_t,_d,_c) in per_group[g])
    block=[]
    block.append("//=== INPUTS (v1.60: 12 groups / 68 params, two-platform aligned) ===")
    block.append("//--- v1.44: NewsGuard/DDGuard default OFF (enable when needed)")
    block.append("//--- v1.60 FIX-TD10: rename per 1230 letter 66-row table; 2 new DD-money params")
    for g in GROUPS12:
        lst = per_group[g]
        block.append("")
        block.append(f'input group "{g}"')
        if not lst and g=="Diagnostics":
            block.append("//--- (reserved: no diagnostics inputs yet)")
        for (name,typ,dflt,cmt) in lst:
            head = f"input {typ:<6} {name:<{maxlen}} = {dflt};"
            block.append(f"{head:<{58 + maxlen}} {cmt}")
    outtext = nl.join(lines[:first] + block + lines[last+1:])

    # ---------------- verification ----------------
    checks=[]; ok=True
    def chk(label, cond, detail=""):
        nonlocal ok
        checks.append((("PASS" if cond else "FAIL"), label, detail))
        if not cond: ok=False
    vlines = outtext.split(nl)
    vdecls = [l for l in vlines if re.match(r'\s*input\s', l)]
    vgroups = [l for l in vdecls if l.lstrip().startswith('input group')]
    vinputs = [l for l in vdecls if not l.lstrip().startswith('input group')]
    chk(f"[{platform}] input count == 68", len(vinputs)==68, f"got {len(vinputs)}")
    chk(f"[{platform}] input group count == 12", len(vgroups)==12, f"got {len(vgroups)}")
    chk(f"[{platform}] group order == fixed-12",
        [re.search(r'input group "(.*?)"',l).group(1) for l in vgroups]==GROUPS12)
    fake = [l for l in vlines if FAKE_RE.match(l)]
    chk(f"[{platform}] 0 fake ___ separators", not fake, f"got {len(fake)}")
    nocmt = [l for l in vinputs if '//' not in l]
    chk(f"[{platform}] all inputs commented", not nocmt, f"{len(nocmt)} missing comment")
    # every input line must terminate with ';' before its comment
    # (v1.60 regression gate: block builder once emitted '= false // cmt' — no ';')
    nosemi = [l.split()[2] if len(l.split())>2 else l[:40] for l in vinputs
              if not re.match(r'\s*input\s+\w+\s+\w+\s*=.*;\s*(//.*)?$', l)]
    chk(f"[{platform}] every input line ends with ';'", not nosemi, str(nosemi[:5]))
    omask = code_mask(outtext)
    residue=[]
    for old,_,_g in MAP66:
        for m in re.finditer(r'(?<![A-Za-z0-9_])'+re.escape(old)+r'(?![A-Za-z0-9_])', outtext):
            if all(omask[m.start():m.end()]): residue.append((old, m.start()))
    chk(f"[{platform}] 0 old-name residue (code segs)", not residue, str(residue[:5]))
    b_o, b_c = outtext.count('{'), outtext.count('}')
    chk(f"[{platform}] brace balance", b_o==b_c, f"{{={b_o} }}={b_c}")
    vnames = [INPUT_RE.match(l).group(3) for l in vinputs if INPUT_RE.match(l)]
    chk(f"[{platform}] 68 unique names", len(set(vnames))==68 and len(vnames)==68,
        f"dups: {[n for n in set(vnames) if vnames.count(n)>1]}")
    audit={}
    for old,_,_g in MAP66:
        hits=[]
        for m in re.finditer(r'(?<![A-Za-z0-9_])'+re.escape(old)+r'(?![A-Za-z0-9_])', outtext, re.IGNORECASE):
            if all(omask[m.start():m.end()]):
                seg=outtext[m.start():m.end()]
                if seg != old: hits.append(seg)
        if hits: audit[old]=sorted(set(hits))
    open(out_path,'w',encoding='utf-8',newline='').write(outtext)
    return ("OK" if ok else "FAIL", {"checks":checks,"audit":audit,"vnames":vnames,"renames":renames_done})

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--platform', required=True, choices=['mt4','mt5'])
    ap.add_argument('--peer', help='peer platform output file, for cross-platform parity check')
    a = ap.parse_args()
    res = transform(a.src, a.out, a.platform)
    if res[0] != "OK":
        print(f"== {a.platform}: {res[0]}")
        if isinstance(res[1], str): print("  "+res[1])
        else:
            for s,l,d in res[1]['checks']:
                if s=='FAIL': print(f"  {s}  {l}  {d}")
        sys.exit(1)
    info=res[1]
    print(f"== {a.platform}: ALL {len(info['checks'])} checks PASS ({info['renames']} identifier renames)")
    for s,l,d in info['checks']: print(f"  {s}  {l}" + (f"  [{d}]" if d else ""))
    if info['audit']:
        print(f"  AUDIT case-variant refs left in code (expected benign: fn params like 'scale'):")
        for k,v in info['audit'].items(): print(f"    - {k} -> {v}")
    if a.peer:
        pt = open(a.peer, encoding='utf-8', errors='replace').read()
        peer_names = set(INPUT_RE.match(l).group(3) for l in re.split(r'\r?\n', pt) if INPUT_RE.match(l))
        my = set(info['vnames'])
        same = my==peer_names
        print(f"== cross-platform parity: {'PASS' if same else 'FAIL'} (mine {len(my)} vs peer {len(peer_names)})")
        if not same:
            print("   only-mine:", sorted(my-peer_names)[:10])
            print("   only-peer:", sorted(peer_names-my)[:10])
        sys.exit(0 if same else 1)

if __name__ == '__main__':
    main()
