#!/usr/bin/env python3
"""ExtraCCY Power — full sweep: 28 FX pairs + XAUUSD.

A) H4 false-break fade, per symbol, per side:
   - 'all'       : no power filter
   - 'h4q'       : H4 fast(10) + slow(120) power both agree with fade direction
   - 'd1q'       : D1 fast+slow power agree (lagged: previous calendar day, no look-ahead)
   - 'both'      : h4q AND d1q
B) Headline test table (all the directions tried so far).
Entry: next bar open. TP=2*ATR, SL=1*ATR, max hold 8 bars.
"""
import sys, os, math, statistics as st, collections, datetime, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hst_lib import read_hst, to_dt
from ccypower_lab import load_power, atr_series

ALPARI = '/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/history/Alpari-Pro.ECN-Demo'
PWR = '/tmp/phx'
TP, SL, MAXB = 2.0, 1.0, 8

SYMS = ['AUDCAD','AUDCHF','AUDJPY','AUDNZD','AUDUSD','CADCHF','CADJPY','CHFJPY',
        'EURAUD','EURCAD','EURCHF','EURGBP','EURJPY','EURNZD','EURUSD',
        'GBPAUD','GBPCAD','GBPCHF','GBPJPY','GBPNZD','GBPUSD',
        'NZDCAD','NZDCHF','NZDJPY','NZDUSD','USDCAD','USDCHF','USDJPY']


def agg(rs):
    if not rs:
        return None
    n = len(rs); m = st.mean(rs); sd = st.pstdev(rs)
    return dict(n=n, avg=m, t=(m / (sd / math.sqrt(n)) if sd and n > 1 else 0.0),
                wr=sum(1 for x in rs if x > 0) / n * 100)


def load_pw(tf, p):
    return {t: v for t, v in load_power(os.path.join(PWR, 'PowerHistory_%s_%d.dat' % (tf, p)))}


def d1_lookup(Pf, Ps, sym):
    """date -> (df, ds) for base/quote pair; only completed days."""
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


def main():
    Pf4 = load_pw('H4', 10); Ps4 = load_pw('H4', 120)
    Pf1 = load_pw('D1', 10); Ps1 = load_pw('D1', 120)

    rows = []
    for sym in SYMS + ['XAUUSD']:
        path = os.path.join(ALPARI, sym + '240.hst')
        if not os.path.exists(path):
            print('MISSING', sym); continue
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
        if len(bars) < 500:
            print('SHORT', sym, len(bars)); continue

        for side, d in (('BUY', 1), ('SELL', -1)):
            buckets = collections.defaultdict(list)
            for i, lv, kind in pivots(bars):
                kd = -1 if kind == 'R' else 1
                if kd != d:
                    continue
                tr = trade(bars, i, d)
                if not tr:
                    continue
                h4q = (bars[i]['df'] > 0) == (d > 0) and (bars[i]['ds'] > 0) == (d > 0)
                # previous D1 day (strictly before this H4 bar's date)
                prev = None
                day = bars[i]['t'].date()
                for dd in reversed(d1days):
                    if dd < day:
                        prev = D1[dd]; break
                d1q = False
                if prev:
                    d1q = (prev[0] > 0) == (d > 0) and (prev[1] > 0) == (d > 0)
                for tag, ok in (('all', True), ('h4q', h4q), ('d1q', d1q), ('both', h4q and d1q)):
                    if ok:
                        buckets[tag].append(tr[0])
            for tag in ('all', 'h4q', 'd1q', 'both'):
                a = agg(buckets[tag])
                if a:
                    a.update(sym=sym, side=side, tag=tag)
                    rows.append(a)
        print('done', sym, len(bars), flush=True)

    json.dump(rows, open('/tmp/allpairs.json', 'w'))

    # ---- summary prints ----
    print('\n=== 合計（29 個 symbol）===')
    for tag in ('all', 'h4q', 'd1q', 'both'):
        rs = []
        for sym in SYMS + ['XAUUSD']:
            pass
        print(' ', tag)

    def tot(tag, syms):
        # recompute weighted properly needs raw; approximate via pooled per-symbol means weight n
        sub = [r for r in rows if r['tag'] == tag and r['sym'] in syms]
        n = sum(r['n'] for r in sub)
        if not n: return None
        m = sum(r['avg'] * r['n'] for r in sub) / n
        return dict(n=n, avg=m)

    for tag in ('all', 'h4q', 'd1q', 'both'):
        t = tot(tag, set(SYMS))
        print('  28FX %-5s n=%5d avg=%+.3f' % (tag, t['n'], t['avg']) if t else '  28FX', tag, 'none')

    print('\n=== 逐 symbol（h4q）===')
    print('%-8s %-5s %6s %8s %7s %7s' % ('sym', 'side', 'n', 'avgR', 't', 'win%'))
    for r in rows:
        if r['tag'] != 'h4q':
            continue
        print('%-8s %-5s %6d %+8.3f %+7.2f %6.1f' % (r['sym'], r['side'], r['n'], r['avg'], r['t'], r['wr']))


if __name__ == '__main__':
    main()
