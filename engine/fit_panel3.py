"""Fit against the real panel using the VERIFIED zigzag port.

Uses engine.zigzag (validated 122/122 against MT4's own ZigZag buffer).
The earlier fit_panel.py had a shift/chronology index bug and its results are
void; this module supersedes it.

Panel ground truth (Alpari-Pro.ECN-Demo, EURUSD H1, 2026.09.17 02:00 .. 11.16 17:00):
    Normal  12 - 110 pips : 630 bars / 2283.6 pips, avg 16.2, longest 48, shortest 3
    Medium 110 - 129 pips : 211 bars /  831.1 pips, avg 30.1, longest 56, shortest 11
    Crazy  129 - 250 pips : 162 bars /  553.0 pips, avg 54.0, longest 99, shortest 29
    => 49 swings, 1003 bars, 3667.7 pips
"""
from __future__ import annotations
import itertools, sys
sys.path.insert(0, "C:/Users/alvin/tsa-work")
from engine.bar import load_bars_csv
from engine.zigzag import zigzag
from decimal import ROUND_HALF_UP, Decimal


def rhu(x: float) -> int:
    return int(Decimal(str(x)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

PIP = 1e-4
T = dict(n=49, cnt=[39, 7, 3], bars=[630, 211, 162], avg=[16.2, 30.1, 54.0],
         pips=[2283.6, 831.1, 553.0], lng=[48, 56, 99], sht=[3, 11, 29],
         amin=12.0, amax=249.7)


def load():
    b = load_bars_csv("C:/Users/alvin/tsa-work/engine/evidence/a1/mt4_EURUSD_H1_bars.csv")
    lb = [x.time_label for x in b]
    lo = lb.index("2026-09-17T02:00")
    hi = lb.index("2026-11-16T17:00")
    return b, lb, lo, hi


def merge(piv, pct, mode, iters=60):
    if mode == "none" or len(piv) < 3:
        return list(piv)
    r = pct / 100.0
    if mode == "pre":
        out = [piv[0]]
        for k in range(1, len(piv) - 1):
            base = abs(piv[k][1] - piv[k - 1][1])
            nxt = abs(piv[k + 1][1] - piv[k][1])
            if base > 0 and nxt < r * base:
                continue
            out.append(piv[k])
        out.append(piv[-1])
        return out
    if mode == "post":
        cur = list(piv)
        for _ in range(iters):
            out = [cur[0]]
            dropped = False
            for k in range(1, len(cur) - 1):
                base = abs(cur[k][1] - out[-1][1])
                nxt = abs(cur[k + 1][1] - cur[k][1])
                if base > 0 and nxt < r * base:
                    dropped = True
                    continue
                out.append(cur[k])
            out.append(cur[-1])
            cur = out
            if not dropped:
                break
        return cur
    if mode == "drop_next":
        cur = list(piv)
        for _ in range(iters):
            if len(cur) < 3:
                break
            out = [cur[0]]
            k = 1
            dropped = False
            while k < len(cur) - 1:
                leg = abs(cur[k][1] - out[-1][1])
                ret = abs(cur[k + 1][1] - cur[k][1])
                if leg > 0 and ret < r * leg:
                    k += 2
                    dropped = True
                    continue
                out.append(cur[k])
                k += 1
            out.extend(cur[k:])
            cur = out
            if not dropped:
                break
        return cur
    raise ValueError(mode)


def stat(piv, lo, hi, bm, amp_mode, H, L):
    ws = []
    for k in range(len(piv) - 1):
        a, c = piv[k], piv[k + 1]
        if not (lo <= a[0] and c[0] <= hi):
            continue
        span = c[0] - a[0]
        if span <= 0:
            continue
        bars = span + 1 if bm == "incl" else span
        if amp_mode == "pivot":
            A = abs(c[1] - a[1]) / PIP
        else:
            A = (max(H[a[0]:c[0] + 1]) - min(L[a[0]:c[0] + 1])) / PIP
        ws.append((bars, round(A, 1)))
    if len(ws) < 5:
        return None
    n = len(ws)
    c0 = rhu(n * 0.8)
    c1 = rhu(n * 0.15)
    cnt = [c0, c1, n - c0 - c1]
    order = sorted(range(n), key=lambda i: ws[i][1])
    g = [[], [], []]
    for pos, i in enumerate(order):
        (g[0] if pos < c0 else g[1] if pos < c0 + c1 else g[2]).append(i)
    bars = [sum(ws[i][0] for i in grp) for grp in g]
    pips = [round(sum(ws[i][1] for i in grp), 1) for grp in g]
    return dict(n=n, cnt=cnt, bars=bars, pips=pips,
                avg=[round(x / c, 1) if c else 0 for x, c in zip(bars, cnt)],
                lng=[max((ws[i][0] for i in grp), default=0) for grp in g],
                sht=[min((ws[i][0] for i in grp), default=0) for grp in g],
                amin=min(w[1] for w in ws), amax=max(w[1] for w in ws), tot=sum(bars))


def score(s):
    if s is None:
        return 1e9
    z = 150 * abs(s["n"] - T["n"])
    z += 200 * sum(abs(a - c) for a, c in zip(s["cnt"], T["cnt"]))
    z += 8 * sum(abs(a - c) for a, c in zip(s["bars"], T["bars"]))
    z += 60 * sum(abs(a - c) for a, c in zip(s["avg"], T["avg"]))
    z += 0.5 * sum(abs(a - c) for a, c in zip(s["pips"], T["pips"]))
    z += 4 * sum(abs(a - c) for a, c in zip(s["lng"], T["lng"]))
    z += 4 * sum(abs(a - c) for a, c in zip(s["sht"], T["sht"]))
    z += 10 * (abs(s["amin"] - T["amin"]) + abs(s["amax"] - T["amax"]))
    return z


def main():
    b, lb, lo, hi = load()
    H = [x.high for x in b]
    L = [x.low for x in b]
    base = [(p.idx + lo, p.price, p.kind) for p in zigzag(b[lo:hi + 1], 12, 5, 3, 1e-5)]
    print(f"verified raw zigzag: pivots={len(base)} waves={len(base) - 1}")
    print(f"window bars={hi - lo + 1}")

    res = []
    for pct in range(0, 81):
        for mm in ("none", "pre", "post", "drop_next"):
            for amp in ("pivot", "range"):
                for bm in ("incl", "excl"):
                    s = stat(merge(base, float(pct), mm), lo, hi, bm, amp, H, L)
                    if s is None:
                        continue
                    res.append((score(s), f"{mm}/{pct}% amp={amp} {bm}", s))
    res.sort(key=lambda r: r[0])
    print("\nTARGET n=49 cnt=[39,7,3] bars=[630,211,162] avg=[16.2,30.1,54.0] tot=1003")
    print("       pips=[2283.6,831.1,553.0] lng=[48,56,99] sht=[3,11,29] amp=12.0-249.7")
    print()
    for z, name, s in res[:10]:
        print(f"{z:8.1f} | {name}")
        print(f"          n={s['n']} cnt={s['cnt']} bars={s['bars']} avg={s['avg']} tot={s['tot']}")
        print(f"          pips={s['pips']} lng={s['lng']} sht={s['sht']} amp={s['amin']}-{s['amax']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
