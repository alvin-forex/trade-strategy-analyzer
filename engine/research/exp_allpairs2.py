#!/usr/bin/env python3
"""ExtraCCY Power — v2 sweep: pick the LONGEST-overlap .hst per symbol across all terminals.

Fixes v1 flaw: v1 used a single terminal (Alpari-Pro.ECN-Demo) where 25 cross pairs
only had 0.9y overlap with power data -> useless sample.
"""
import sys, os, math, statistics as st, collections, json, glob
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hst_lib import read_hst, to_dt
from ccypower_lab import load_power, atr_series

ROOTS = glob.glob('/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/*/history/*')
PWR = '/tmp/phx'
TP, SL, MAXB = 2.0, 1.0, 8

SYMS = ['AUDCAD','AUDCHF','AUDJPY','AUDNZD','AUDUSD','CADCHF','CADJPY','CHFJPY',
        'EURAUD','EURCAD','EURCHF','EURGBP','EURJPY','EURNZD','EURUSD',
        'GBPAUD','GBPCAD','GBPCHF','GBPJPY','GBPNZD','GBPUSD',
        'NZDCAD','NZDCHF','NZDJPY','NZDUSD','USDCAD','USDCHF','USDJPY','XAUUSD']


def agg(rs):
    if not rs:
        return None
    n = len(rs); m = st.mean(rs); sd = st.pstdev(rs)
    return dict(n=n, avg=m, t=(m / (sd / math.sqrt(n)) if sd and n > 1 else 0.0),
                wr=sum(1 for x in rs if x > 0) / n * 100)


def best_hst(sym, ptimes):
    best = None
    for d in ROOTS:
        p = os.path.join(d, sym + '240.hst')
        if not os.path.exists(p):
            continue
        try:
            r = read_hst(p)
        except Exception:
            continue
        n = sum(1 for x in r if to_dt(x[0]) in ptimes)
        if best is None or n > best[0]:
            best = (n, p)
    return best


def pivots(B, k=3, lookback=200):
    sig = []
    for i in range(k, len(B) - k):
        if B[i]['h'] == max(B[j]['h'] for j in range(i - k, i + k + 1)):
            sig.append((i, B[i]['h'], 'R'))
        elif B[i]['l'] == min(B[j]['l'] for j in range(i - k, i + k + 1)):
            sig.append((i, B[i]['l'], 'S'))
    out = []
    for p, lv, kind in sig:
        for j in range(p + k, min(p + lookback, len(B) - 2)):
            if B[j]['atr'] is None:
                continue
            tol = 0.10 * B[j]['atr']
            if kind == 'R' and B[j]['h'] > lv + tol and B[j]['c'] < lv:
                out.append((j, lv, 'R')); break
            if kind == 'S' and B[j]['l'] < lv - tol and B[j]['c'] > lv:
                out.append((j, lv, 'S')); break
    return out


def trade(B, i, d):
    if i + 1 >= len(B) or B[i]['atr'] is None:
        return None
    atr = B[i]['atr']; ent = B[i + 1]['o']
    if not atr or not ent:
        return None
    tp, sl = ent + d * TP * atr, ent - d * SL * atr
    for j in range(i + 1, min(i + 1 + MAXB, len(B))):
        bx = B[j]
        if d > 0:
            if bx['l'] <= sl: return (-1.0, 'SL', j - i)
            if bx['h'] >= tp: return (TP, 'TP', j - i)
        else:
            if bx['h'] >= sl: return (-1.0, 'SL', j - i)
            if bx['l'] <= tp: return (TP, 'TP', j - i)
    j = min(i + MAXB, len(B) - 1)
    return ((B[j]['c'] - ent) * d / atr, 'TIME', j - i)


def d1_lookup(Pf, Ps, sym):
    b, q = sym[:3], sym[3:]
    out = {}
    for dt in Pf:
        pf, ps = Pf[dt], Ps.get(dt)
        if not ps:
            continue
        if not pf.get(b) or not pf.get(q) or not ps.get(b) or not ps.get(q):
            continue
        out[dt.date()] = (pf[b] - pf[q], ps[b] - ps[q])
    return out


def main():
    Pf4 = {t: v for t, v in load_power(os.path.join(PWR, 'PowerHistory_H4_10.dat'))}
    Ps4 = {t: v for t, v in load_power(os.path.join(PWR, 'PowerHistory_H4_120.dat'))}
    Pf1 = {t: v for t, v in load_power(os.path.join(PWR, 'PowerHistory_D1_10.dat'))}
    Ps1 = {t: v for t, v in load_power(os.path.join(PWR, 'PowerHistory_D1_120.dat'))}
    ptimes = set(Pf4)

    rows = []
    meta = {}
    for sym in SYMS:
        bi = best_hst(sym, ptimes)
        if not bi or bi[0] < 200:
            print('SKIP', sym, bi)
            continue
        n_ov, path = bi
        b, q = sym[:3], sym[3:]
        D1 = d1_lookup(Pf1, Ps1, sym)
        d1days = sorted(D1)
        bars = []
        for t, o, h, l, c, v, sp in read_hst(path):
            dt = to_dt(t)
            pf, ps = Pf4.get(dt), Ps4.get(dt)
            if not pf or not ps or not pf.get(b) or not pf.get(q) or not ps.get(b) or not ps.get(q):
                continue
            bars.append({'t': dt, 'o': o, 'h': h, 'l': l, 'c': c,
                         'df': pf[b] - pf[q], 'ds': ps[b] - ps[q]})
        at = atr_series(bars, 14)
        for i, x in enumerate(bars):
            x['atr'] = at[i]
        if len(bars) < 400:
            print('SHORT', sym, len(bars)); continue
        yrs = (bars[-1]['t'] - bars[0]['t']).days / 365.25
        meta[sym] = dict(bars=len(bars), years=round(yrs, 1), src=path.split('Terminal/')[1].split('/')[0][:8])

        for side, d in (('BUY', 1), ('SELL', -1)):
            bk = collections.defaultdict(list)
            for i, lv, kind in pivots(bars):
                kd = -1 if kind == 'R' else 1
                if kd != d:
                    continue
                tr = trade(bars, i, d)
                if not tr:
                    continue
                h4q = (bars[i]['df'] > 0) == (d > 0) and (bars[i]['ds'] > 0) == (d > 0)
                day = bars[i]['t'].date()
                prev = None
                for dd in reversed(d1days):
                    if dd < day:
                        prev = D1[dd]; break
                d1q = bool(prev) and (prev[0] > 0) == (d > 0) and (prev[1] > 0) == (d > 0)
                for tag, ok in (('all', True), ('h4q', h4q), ('d1q', d1q), ('both', h4q and d1q)):
                    if ok:
                        bk[tag].append(tr[0])
            for tag in ('all', 'h4q', 'd1q', 'both'):
                a = agg(bk[tag])
                if a:
                    a.update(sym=sym, side=side, tag=tag)
                    rows.append(a)
        print('done %-8s %5d bars %4.1fy' % (sym, len(bars), yrs), flush=True)

    json.dump({'rows': rows, 'meta': meta}, open('/tmp/allpairs2.json', 'w'), default=str)

    def tot(tag, syms):
        sub = [r for r in rows if r['tag'] == tag and r['sym'] in syms]
        n = sum(r['n'] for r in sub)
        if not n:
            return None
        m = sum(r['avg'] * r['n'] for r in sub) / n
        var = 0.0
        for r in sub:
            sd = abs(r['avg'] / (r['t'] / math.sqrt(r['n']))) if r['t'] else 0
            var += r['n'] * (sd ** 2 + (r['avg'] - m) ** 2)
        sd = math.sqrt(var / n)
        return dict(n=n, avg=m, t=(m / (sd / math.sqrt(n)) if sd else 0))

    ALL = set(meta)
    print('\n=== 合計（%d 個 symbol）===' % len(ALL))
    for tag in ('all', 'h4q', 'd1q', 'both'):
        x = tot(tag, ALL)
        print('  %-5s n=%6d %+.3fR t=%+.2f' % (tag, x['n'], x['avg'], x['t']))


if __name__ == '__main__':
    main()
