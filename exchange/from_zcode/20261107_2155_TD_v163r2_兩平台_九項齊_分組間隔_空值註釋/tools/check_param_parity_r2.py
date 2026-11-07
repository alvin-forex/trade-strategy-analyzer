#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TD10 #3 check_param_parity_r2.py — r2 of the cross-platform parity gate (2026-11-07 21:50 HKT)
r2 revision (from_openclaw/20261107_2130 §八):
  - Spacer rows (MT4 'input string SpacerNN' / MT5 'sinput string SpacerNN')
    are EXCLUDED from param accounting — they are display-only rows,
    not parameters. Their own integrity is gated by check_input_standard_r2.
  - sinput declarations now parsed (MT5 spacers).
  - ALLOWED_DEFAULT_DIFFS emptied: InpDefaultView unified to 0 in v1.63 (1850).
Compares MT4 vs MT5:
  P1 name set equal (70) | P2 order identical | P3 group sequence + per-name
  P4 type per name | P5 default per name | I1 comment diffs (INFO)
Usage: python3 check_param_parity_r2.py --mt4 FILE.mq4 --mt5 FILE.mq5
"""
import re, sys, argparse

INPUT_RE = re.compile(r'^(\s*)(s?input)\s+([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)(//.*)?\s*$')
GROUP_RE = re.compile(r'^\s*input\s+group\s+"(.*?)"')
SPACER_NAME = re.compile(r'^Spacer\d{2}$')

# v1.63 (1850 ruling): InpDefaultView unified to 0 on both platforms — no
# documented default differences remain.
ALLOWED_DEFAULT_DIFFS = set()

def norm_default(v):
    return v.strip().rstrip(';').strip()

def parse(path):
    text = open(path, encoding='utf-8', errors='replace').read()
    lines = text.split('\r\n' if '\r\n' in text else '\n')
    items, groups, cur, n2g = [], [], None, {}
    n_spacers = 0
    for ln in lines:
        gm = GROUP_RE.match(ln)
        if gm:
            cur = gm.group(1)
            if cur not in groups:
                groups.append(cur)
            continue
        m = INPUT_RE.match(ln)
        if m and not ln.lstrip().startswith('//'):
            name = m.group(4)
            if SPACER_NAME.match(name):
                n_spacers += 1
                continue                      # r2: spacers are not parameters
            items.append((name, m.group(3), norm_default(m.group(5)), (m.group(6) or '').strip()))
            n2g[name] = cur
    return items, groups, n2g, n_spacers

def compare(mt4_path, mt5_path):
    it4, g4, n2g4, sp4 = parse(mt4_path)
    it5, g5, n2g5, sp5 = parse(mt5_path)
    names4 = [x[0] for x in it4]
    names5 = [x[0] for x in it5]
    d4 = {x[0]: x for x in it4}
    d5 = {x[0]: x for x in it5}
    checks = []
    def chk(tag, label, cond, detail=""):
        checks.append((tag, label, "PASS" if cond else "FAIL", detail))

    s4, s5 = set(names4), set(names5)
    chk("P1", f"name set equal ({len(names4)} vs {len(names5)}, spacers excluded)",
        s4 == s5 and len(names4) == len(names5),
        f"only-mt4={sorted(s4-s5)[:6]} only-mt5={sorted(s5-s4)[:6]}")
    chk("P2", "declaration order identical (spacers excluded)", names4 == names5,
        "first diff at " + str(next((i for i, (a, b) in enumerate(zip(names4, names5)) if a != b), 'n/a')))
    chk("P3", "group sequence identical", g4 == g5, f"mt4={len(g4)} mt5={len(g5)}")
    gmis = [n for n in names4 if n in n2g5 and n2g4[n] != n2g5[n]]
    chk("P3b", "per-name group match", not gmis, str(gmis[:6]))
    tmis = [n for n in names4 if n in d5 and d4[n][1] != d5[n][1]]
    chk("P4", "type per name identical", not tmis,
        str([(n, d4[n][1], d5[n][1]) for n in tmis[:6]]))
    dmis = [n for n in names4 if n in d5 and d4[n][2] != d5[n][2]]
    hard  = [n for n in dmis if n not in ALLOWED_DEFAULT_DIFFS]
    chk("P5", "default per name identical", not hard,
        str([(n, d4[n][2], d5[n][2]) for n in hard[:6]]))
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
    print(f"== parity r2: {'PASS' if n_fail == 0 else 'FAIL'} "
          f"(mt4 {len(m4[0])} params + {m4[3]} spacers / {len(m4[1])} groups vs "
          f"mt5 {len(m5[0])} + {m5[3]} / {len(m5[1])})")
    sys.exit(0 if n_fail == 0 else 1)

if __name__ == '__main__':
    main()
