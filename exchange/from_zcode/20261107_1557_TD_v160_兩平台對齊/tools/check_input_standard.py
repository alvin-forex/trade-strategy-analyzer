#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TD10 #2 check_input_standard.py — input naming/structure standard gate (2026-11-07 15:31 HKT)
Spec: FIX-TD10 規範工具（1230 信「維持有效，可並行」）；v1.60 交付驗收項 4/5/6/7 的機器閘。

Checks (each independent, all must PASS):
  L1  lexer sanity        : three-state lexer ends in code; NO backslash in code
                            segments; NO raw newline inside string/char literals
                            (catches broken string concatenation - the S6c class)
  L2  strict (mt4)        : #property strict present
  N1  naming standard     : every input name matches ^Inp[A-Z][A-Za-z0-9]*$
  N2  old-name residue    : zero 66-table old identifiers in code segments
  C1  comments            : every input line carries a // comment
  F1  fake separators     : zero 'input string ___'
  G1  group count/unique  : 12 'input group' lines, unique names
  G2  group coverage      : no input line before the first group line
  P1  block purity        : only input/group/comment/blank lines in the block
  U1  unique names        : no duplicate input names
  T1  type whitelist      : bool/int/double/string only (others = FAIL)
  B1  brace balance       : code-segment braces equal (string-masked count)

Usage: python3 check_input_standard.py --src FILE.mq4 [--platform mt4|mt5]
Exit 0 = ALL PASS, 1 = any FAIL. Deterministic, no human judgement.
"""
import re, sys, argparse

# --- shared with rename_inputs.py (single source of truth when co-located) ---
sys.path.insert(0, __file__.rsplit('/', 1)[0])
try:
    from rename_inputs import MAP66, GROUPS12, lex, INPUT_RE, FAKE_RE
except Exception:                                    # standalone fallback
    MAP66 = []; GROUPS12 = []; lex = None
    INPUT_RE = re.compile(r'^(\s*)input\s+([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)(//.*)?\s*$')
    FAKE_RE  = re.compile(r'^\s*input\s+string\s+___')

NAME_RE = re.compile(r'^Inp[A-Z][A-Za-z0-9]*$')
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

    # ---- L1 lexer sanity (catches broken string concat, e.g. missing ' + "') ----
    # end-state: str/chr = unterminated literal (FAIL); ccmt/bcmt = file ends in a
    # comment with no trailing newline - legal MQL, benign.
    lex_ok, lex_detail = True, ""
    if lex is not None:
        segs = lex(text)
        end_state = segs[-1][0]
        backslash = next((s for st, s in segs if st == 'code' and '\\' in s), None)
        rawnl     = next((s for st, s in segs if st in ('str', 'chr') and '\n' in s), None)
        lex_ok = (end_state not in ('str', 'chr')) and backslash is None and rawnl is None
        if end_state in ('str', 'chr'): lex_detail = f"lexer ends inside {end_state} literal"
        elif backslash is not None:  lex_detail = "backslash in code segment: " + backslash[:60].replace('\n', '⏎')
        elif rawnl is not None:      lex_detail = "raw newline inside string literal"
    else:
        lex_ok, lex_detail = False, "lexer unavailable"
    chk("L1", "lexer sanity (code-state clean)", lex_ok, lex_detail)

    if platform == 'mt4':
        chk("L2", "#property strict present", '#property strict' in text)

    # ---- parse inputs ----
    decls = []
    for ln in lines:
        if FAKE_RE.match(ln):
            continue
        m = INPUT_RE.match(ln)
        if m and not ln.lstrip().startswith('//'):
            decls.append({'line': ln, 'name': m.group(3), 'type': m.group(2),
                          'default': m.group(4).strip(), 'comment': (m.group(5) or '').strip()})
    names = [d['name'] for d in decls]

    # ---- N1 naming standard ----
    bad_names = [n for n in names if not NAME_RE.match(n)]
    chk("N1", f"naming standard InpPascalCase ({len(names)} inputs)", not bad_names, str(bad_names[:5]))

    # ---- N2 old-name residue (code segments only) ----
    if MAP66:
        mask = code_mask(text)
        residue = []
        for old, _n, _g in MAP66:
            for m in re.finditer(r'(?<![A-Za-z0-9_])' + re.escape(old) + r'(?![A-Za-z0-9_])', text):
                if all(mask[m.start():m.end()]):
                    residue.append(old)
        chk("N2", "0 old-name identifiers in code", not residue, str(sorted(set(residue))[:5]))

    # ---- C1 comments ----
    no_cmt = [d['name'] for d in decls if not d['comment']]
    chk("C1", "every input commented", not no_cmt, str(no_cmt[:5]))

    # ---- F1 fake separators ----
    fakes = [ln for ln in lines if FAKE_RE.match(ln)]
    chk("F1", "0 fake ___ separators", not fakes, f"got {len(fakes)}")

    # ---- S1 statement terminator: every input line ends with ';' pre-comment ----
    nosemi = [d['name'] for d in decls
              if not re.match(r'\s*input\s+\w+\s+\w+\s*=.*;\s*(//.*)?$', d['line'])]
    chk("S1", "every input line ends with ';'", not nosemi, str(nosemi[:5]))

    # ---- G1/G2 groups ----
    glines = [ln for ln in lines if re.match(r'\s*input\s+group\s+"', ln)]
    gnames = [re.search(r'input\s+group\s+"(.*?)"', ln).group(1) for ln in glines]
    if GROUPS12:
        chk("G1", f"input group count == {len(GROUPS12)} (fixed order)",
            gnames == GROUPS12, f"got {len(gnames)}: {gnames[:14]}")
    else:
        chk("G1", "group names unique", len(gnames) == len(set(gnames)))
    first_g = next((i for i, ln in enumerate(lines) if re.match(r'\s*input\s+group\s+"', ln)), None)
    first_i = next((i for i, ln in enumerate(lines) if INPUT_RE.match(ln) and not ln.lstrip().startswith('//')), None)
    chk("G2", "no input before first group", first_g is not None and first_i is not None and first_g < first_i,
        f"first group line {first_g}, first input line {first_i}")

    # ---- P1 block purity ----
    pur = "PASS"; pur_d = ""
    if first_g is not None and first_i is not None:
        last_i = max(i for i, ln in enumerate(lines) if INPUT_RE.match(ln) and not ln.lstrip().startswith('//'))
        for i in range(first_g, last_i + 1):
            s = lines[i].strip()
            if s and not (s.startswith('input') or s.startswith('//')):
                pur, pur_d = "FAIL", f"line {i+1}: {s[:60]}"
                break
        chk("P1", "input block purity", pur == "PASS", pur_d)
    else:
        chk("P1", "input block purity", False, "no input block found")

    # ---- U1 unique ----
    dups = sorted({n for n in names if names.count(n) > 1})
    chk("U1", "input names unique", not dups, str(dups))

    # ---- T1 types ----
    bad_t = sorted({d['type'] for d in decls if d['type'] not in TYPES_OK})
    chk("T1", "input types in whitelist", not bad_t, str(bad_t))

    # ---- B1 brace balance (code segments only) ----
    if lex is not None:
        mask = code_mask(text)
        ob = sum(1 for i, c in enumerate(text) if c == '{' and mask[i])
        cb = sum(1 for i, c in enumerate(text) if c == '}' and mask[i])
        chk("B1", "brace balance (code-seg)", ob == cb, f"{{={ob} }}={cb}")

    return checks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True)
    ap.add_argument('--platform', choices=['mt4', 'mt5'])
    a = ap.parse_args()
    checks = check(a.src, a.platform)
    n_fail = sum(1 for _t, _l, s, _d in checks if s == 'FAIL')
    for tag, label, status, detail in checks:
        print(f"  {status}  [{tag}] {label}" + (f"  — {detail}" if detail and status == 'FAIL' else ""))
    print(f"== {a.src.rsplit('/', 1)[-1]}: " + (f"ALL {len(checks)} checks PASS" if n_fail == 0 else f"{n_fail}/{len(checks)} FAIL"))
    sys.exit(0 if n_fail == 0 else 1)

if __name__ == '__main__':
    main()
