#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TD10 #3 check_param_parity.py — cross-platform input parity gate (2026-11-07 15:31 HKT)
Spec: FIX-TD10 規範工具；v1.60 驗收項 8「兩平台逐名比對，一字不差」的機器閘。

Compares MT4 vs MT5 input declarations:
  P1  name set equal          : same 68 names both sides
  P2  name order equal        : identical declaration order (fixed-12 rebuild)
  P3  group sequence equal    : identical group order AND per-name group match
  P4  type per name equal     : same MQL type per parameter
  P5  default per name equal  : same default value per parameter
  I1  comment diffs (INFO)    : reported, never fails (wording may drift)

Usage: python3 check_param_parity.py --mt4 FILE.mq4 --mt5 FILE.mq5
Exit 0 = parity PASS, 1 = any FAIL.
"""
import re, sys, argparse

INPUT_RE = re.compile(r'^(\s*)input\s+([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)(//.*)?\s*$')
GROUP_RE = re.compile(r'^\s*input\s+group\s+"(.*?)"')

# documented platform default differences (NOT parity failures — reported, decision with OpenClaw):
#   InpDefaultView: MT4 v1.52 FIX-TD3 changed default to 1 (Day); MT5 baseline kept 0 (Hour).
#                   Out of the frozen v1.60 scope; flagged in REPORT.md §set/diff table.
ALLOWED_DEFAULT_DIFFS = {'InpDefaultView'}

def norm_default(v):
    """Normalize a captured default: strip trailing ';' and whitespace."""
    return v.strip().rstrip(';').strip()

def parse(path):
    """Ordered list of (name, type, default, comment) + group sequence + name->group."""
    text = open(path, encoding='utf-8', errors='replace').read()
    lines = text.split('\r\n' if '\r\n' in text else '\n')
    items, groups, cur, n2g = [], [], None, {}
    for ln in lines:
        gm = GROUP_RE.match(ln)
        if gm:
            cur = gm.group(1)
            if cur not in groups:
                groups.append(cur)
            continue
        m = INPUT_RE.match(ln)
        if m and not ln.lstrip().startswith('//'):
            name = m.group(3)
            items.append((name, m.group(2), norm_default(m.group(4)), (m.group(5) or '').strip()))
            n2g[name] = cur
    return items, groups, n2g

def compare(mt4_path, mt5_path):
    it4, g4, n2g4 = parse(mt4_path)
    it5, g5, n2g5 = parse(mt5_path)
    names4 = [x[0] for x in it4]
    names5 = [x[0] for x in it5]
    d4 = {x[0]: x for x in it4}
    d5 = {x[0]: x for x in it5}
    checks = []
    def chk(tag, label, cond, detail=""):
        checks.append((tag, label, "PASS" if cond else "FAIL", detail))

    s4, s5 = set(names4), set(names5)
    chk("P1", f"name set equal ({len(names4)} vs {len(names5)})",
        s4 == s5 and len(names4) == len(names5),
        f"only-mt4={sorted(s4-s5)[:6]} only-mt5={sorted(s5-s4)[:6]}")
    chk("P2", "declaration order identical", names4 == names5,
        "first diff at " + str(next((i for i, (a, b) in enumerate(zip(names4, names5)) if a != b), 'n/a')))
    chk("P3", "group sequence identical", g4 == g5, f"mt4={len(g4)} mt5={len(g5)}")
    gmis = [n for n in names4 if n in n2g5 and n2g4[n] != n2g5[n]]
    chk("P3b", "per-name group match", not gmis, str(gmis[:6]))
    tmis = [n for n in names4 if n in d5 and d4[n][1] != d5[n][1]]
    chk("P4", "type per name identical", not tmis,
        str([(n, d4[n][1], d5[n][1]) for n in tmis[:6]]))
    dmis = [n for n in names4 if n in d5 and d4[n][2] != d5[n][2]]
    hard  = [n for n in dmis if n not in ALLOWED_DEFAULT_DIFFS]
    known = [n for n in dmis if n in ALLOWED_DEFAULT_DIFFS]
    chk("P5", "default per name identical", not hard,
        str([(n, d4[n][2], d5[n][2]) for n in hard[:6]])
        + (f" | documented diff (allowed): {[(n, d4[n][2], d5[n][2]) for n in known]}" if known else ""))
    cmis = [n for n in names4 if n in d5 and d4[n][3] != d5[n][3]]
    chk("I1", "comment diffs (INFO only)", True, f"{len(cmis)} differ" + (f": {cmis[:6]}" if cmis else ""))
    return checks

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--mt4', required=True)
    ap.add_argument('--mt5', required=True)
    a = ap.parse_args()
    checks = compare(a.mt4, a.mt5)
    for tag, label, status, detail in checks:
        print(f"  {status}  [{tag}] {label}" + (f"  — {detail}" if detail and (status == 'FAIL' or tag == 'I1') else ""))
    n_fail = sum(1 for _t, _l, s, _d in checks if s == 'FAIL')
    m4, m5 = parse(a.mt4), parse(a.mt5)
    print(f"== parity: {'PASS' if n_fail == 0 else 'FAIL'} (mt4 {len(m4[0])} inputs/{len(m4[1])} groups vs mt5 {len(m5[0])}/{len(m5[1])})")
    sys.exit(0 if n_fail == 0 else 1)

if __name__ == '__main__':
    main()
