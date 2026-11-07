#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TD10 #2 check_input_standard_r2.py — r2 of the input standard gate (2026-11-07 21:50 HKT)
r2 revision (from_openclaw/20261107_2130 §八 — spec revision, supersedes the v1.60 F1):
  - Spacer rows are now PART OF THE STANDARD: 12 standardized rows at group
    boundaries, uniform format, excluded from the param count.
  - F1 keeps banning the v1.55 'input string ___' fake separators; new gates
    SP1/SP2/SP3 enforce the standardized spacer contract instead.
  - G2 counts only non-spacer inputs (a spacer before group 1 is legal).
Checks:
  L1  lexer sanity | L2 strict(mt4) | N1 naming (params only) | N2 old-name residue
  C1  comments | F1 fake ___ = 0 | SP1 spacer count == group count
  SP2 spacers only at group boundaries | SP3 uniform format
  G1  group count/unique | G2 no param before first group | P1 block purity
  U1  unique names | T1 type whitelist | B1 brace balance
Usage: python3 check_input_standard_r2.py --src FILE [--platform mt4|mt5]
"""
import re, sys, argparse

sys.path.insert(0, __file__.rsplit('/', 1)[0])
try:
    from rename_inputs import MAP66, GROUPS12, lex, INPUT_RE, FAKE_RE
except Exception:
    MAP66 = []; GROUPS12 = []; lex = None
    INPUT_RE = re.compile(r'^(\s*)input\s+([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)(//.*)?\s*$')
    FAKE_RE  = re.compile(r'^\s*input\s+string\s+___')

NAME_RE = re.compile(r'^Inp[A-Z][A-Za-z0-9]*$')
SPACER_RE   = re.compile(r'^\s*(s?input)\s+string\s+(Spacer\d{2})\s*=\s*(""|)\s*;\s*(//.*)?$')
SPACER_LINE = re.compile(r'^\s*s?input\s+string\s+Spacer\d{2}')
SPACER_DASH = "─" * 32
TYPES_OK = {'bool', 'int', 'double', 'string', 'datetime', 'color', 'long', 'ulong'}

def code_mask(text):
    if lex is None:
        raise RuntimeError("rename_inputs.py not co-located: lexer unavailable")
    mask = []
    for st, seg in lex(text):
        mask.extend([st == 'code'] * len(seg))
    assert len(mask) == len(text)
    return mask

def check(path, platform=None):
    text = open(path, encoding='utf-8', errors='replace').read()
    nl = '\r\n' if '\r\n' in text else '\n'
    lines = text.split(nl)
    checks = []
    def chk(tag, label, cond, detail=""):
        checks.append((tag, label, "PASS" if cond else "FAIL", detail))
        return cond

    # ---- L1 lexer sanity ----
    lex_ok, lex_detail = True, ""
    if lex is not None:
        segs = lex(text)
        end_state = segs[-1][0]
        backslash = next((s for st, s in segs if st == 'code' and '\\' in s), None)
        rawnl     = next((s for st, s in segs if st in ('str', 'chr') and '\n' in s), None)
        lex_ok = (end_state not in ('str', 'chr')) and backslash is None and rawnl is None
        if end_state in ('str', 'chr'): lex_detail = f"lexer ends inside {end_state} literal"
        elif backslash is not None:  lex_detail = "backslash in code segment"
        elif rawnl is not None:      lex_detail = "raw newline inside string literal"
    else:
        lex_ok, lex_detail = False, "lexer unavailable"
    chk("L1", "lexer sanity (code-state clean)", lex_ok, lex_detail)

    if platform == 'mt4':
        chk("L2", "#property strict present", '#property strict' in text)

    # ---- parse inputs (r2: spacer rows tracked separately, excluded from params) ----
    decls, spacers = [], []
    for ln in lines:
        if SPACER_LINE.match(ln):
            spacers.append(ln)
            continue
        if FAKE_RE.match(ln):
            continue
        m = INPUT_RE.match(ln)
        if m and not ln.lstrip().startswith('//'):
            decls.append({'line': ln, 'name': m.group(3), 'type': m.group(2),
                          'default': m.group(4).strip(), 'comment': (m.group(5) or '').strip()})
    names = [d['name'] for d in decls]

    bad_names = [n for n in names if not NAME_RE.match(n)]
    chk("N1", f"naming standard InpPascalCase ({len(names)} params, spacers excluded)", not bad_names, str(bad_names[:5]))

    if MAP66:
        mask = code_mask(text)
        residue = []
        for old, _n, _g in MAP66:
            for m in re.finditer(r'(?<![A-Za-z0-9_])' + re.escape(old) + r'(?![A-Za-z0-9_])', text):
                if all(mask[m.start():m.end()]):
                    residue.append(old)
        chk("N2", "0 old-name identifiers in code", not residue, str(sorted(set(residue))[:5]))

    no_cmt = [d['name'] for d in decls if not d['comment']]
    chk("C1", "every input commented (params)", not no_cmt, str(no_cmt[:5]))

    # ---- F1: v1.55 ___ fakes stay banned ----
    fakes = [ln for ln in lines if FAKE_RE.match(ln)]
    chk("F1", "0 fake ___ separators", not fakes, f"got {len(fakes)}")

    # ---- SP1/SP2/SP3: standardized spacer contract (2130 §八) ----
    glines = [ln for ln in lines if re.match(r'\s*input\s+group\s+"', ln)]
    chk("SP1", f"spacer count == group count ({len(glines)})", len(spacers) == len(glines),
        f"spacers={len(spacers)} groups={len(glines)}")
    def nextidx(i):
        j = i + 1
        while j < len(lines) and not lines[j].strip():
            j += 1
        return j
    boundary_ok = all(nextidx(lines.index(l)) < len(lines)
                      and re.match(r'\s*input\s+group\s+"', lines[nextidx(lines.index(l))])
                      for l in spacers)
    chk("SP2", "spacers only at group boundaries (next non-blank = group)", boundary_ok)
    fmt_ok = all(SPACE_RE_OK(l) for l in spacers) if spacers else False
    chk("SP3", f"spacer format uniform (empty value + comment '{SPACER_DASH[:4]}…'x32)", fmt_ok)

    # ---- S1 statement terminator ----
    nosemi = [d['name'] for d in decls
              if not re.match(r'\s*input\s+\w+\s+\w+\s*=.*;\s*(//.*)?$', d['line'])]
    chk("S1", "every input line ends with ';'", not nosemi, str(nosemi[:5]))

    # ---- G1/G2 groups ----
    gnames = [re.search(r'input\s+group\s+"(.*?)"', ln).group(1) for ln in glines]
    if GROUPS12:
        chk("G1", f"input group count == {len(GROUPS12)} (fixed order)", gnames == GROUPS12,
            f"got {len(gnames)}: {gnames[:14]}")
    else:
        chk("G1", "group names unique", len(gnames) == len(set(gnames)))
    first_g = next((i for i, ln in enumerate(lines) if re.match(r'\s*input\s+group\s+"', ln)), None)
    first_i = next((i for i, ln in enumerate(lines)
                    if INPUT_RE.match(ln) and not SPACER_LINE.match(ln)
                    and not ln.lstrip().startswith('//')), None)
    chk("G2", "no param input before first group (spacers exempt)", first_g is not None and first_i is not None and first_g < first_i,
        f"first group line {first_g}, first param line {first_i}")

    # ---- P1 block purity ----
    pur = "PASS"; pur_d = ""
    if first_g is not None and first_i is not None:
        last_i = max(i for i, ln in enumerate(lines)
                     if INPUT_RE.match(ln) and not ln.lstrip().startswith('//'))
        for i in range(first_g, last_i + 1):
            s = lines[i].strip()
            if s and not (s.startswith('input') or s.startswith('sinput') or s.startswith('//')):
                pur, pur_d = "FAIL", f"line {i+1}: {s[:60]}"
                break
        chk("P1", "input block purity", pur == "PASS", pur_d)
    else:
        chk("P1", "input block purity", False, "no input block found")

    dups = sorted({n for n in names if names.count(n) > 1})
    chk("U1", "input names unique", not dups, str(dups))
    bad_t = sorted({d['type'] for d in decls if d['type'] not in TYPES_OK})
    chk("T1", "input types in whitelist", not bad_t, str(bad_t))

    if lex is not None:
        mask = code_mask(text)
        ob = sum(1 for i, c in enumerate(text) if c == '{' and mask[i])
        cb = sum(1 for i, c in enumerate(text) if c == '}' and mask[i])
        chk("B1", "brace balance (code-seg)", ob == cb, f"{{={ob} }}={cb}")

    return checks

SPACER_FULL = re.compile(r'^\s*s?input\s+string\s+Spacer\d{2}\s*=\s*""\s*;\s*//\s*' + SPACER_DASH + r'\s*$')
def SPACE_RE_OK(l):
    return bool(SPACER_FULL.match(l))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--platform', choices=['mt4', 'mt5'])
    a = ap.parse_args()
    checks = check(a.src, a.platform)
    n_fail = sum(1 for _t, _l, s, _d in checks if s == 'FAIL')
    for tag, label, status, detail in checks:
        print(f"  {status}  [{tag}] {label}" + (f"  — {detail}" if detail and status == 'FAIL' else ""))
    print(f"== {a.src.rsplit('/', 1)[-1]}: " + (f"ALL {len(checks)} checks PASS (r2)" if n_fail == 0 else f"{n_fail}/{len(checks)} FAIL"))
    sys.exit(0 if n_fail == 0 else 1)

if __name__ == '__main__':
    main()
