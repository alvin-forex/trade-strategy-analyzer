#!/usr/bin/env python3
"""CLEAN consolidated evidence pass (correct rev flags).

Source: ccy_power_reader.csv on MT4-2 (A06E / Alpari-Pro.ECN-Demo) written by
CCYPowerReader.mq4 reading the ORIGINAL indicator's __table_edit_* objects,
every 5 min. Bars: the same terminal's .hst files. => same machine & feed.

Outputs (one table per TF, identical sample subset for obs and model):
  per-currency sd/mean in U units (U = Power x N), cross-section correlation,
  acf1, sum over the 8 non-gold currencies, and the model's counterpart.
Plus an intrabar-update test that bears directly on "includes forming bar?".
"""
import csv
import datetime as dt
import os

import numpy as np

TERM = '/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549'
HST = os.path.join(TERM, 'history/Alpari-Pro.ECN-Demo')
PANEL = os.path.join(TERM, 'MQL4/Files/ccy_power_reader.csv')

PAIRS = ['AUDCAD','AUDCHF','AUDJPY','AUDNZD','AUDUSD','CADCHF','CADJPY','CHFJPY',
         'EURAUD','EURCAD','EURCHF','EURGBP','EURJPY','EURNZD','EURUSD',
         'GBPAUD','GBPCAD','GBPCHF','GBPJPY','GBPNZD','GBPUSD',
         'NZDCAD','NZDCHF','NZDJPY','NZDUSD','USDCAD','USDCHF','USDJPY']
GOLD = ['XAUAUD','XAUEUR','XAUGBP','XAUJPY','XAUUSD']
CCY = ['EUR','GBP','AUD','NZD','CHF','JPY','XAU','CAD','USD']
GOLD_OF = {'AUD':'XAUAUD','EUR':'XAUEUR','GBP':'XAUGBP','JPY':'XAUJPY','USD':'XAUUSD'}


def n_of(c):
    if c == 'XAU':
        return len(GOLD)
    return sum(1 for p in PAIRS if p[:3] == c or p[3:] == c) + (1 if c in GOLD_OF else 0)


def read_hst(path):
    d = open(path, 'rb').read()
    n = (len(d)-148)//60
    raw = np.frombuffer(d, dtype=np.uint8, count=n*60, offset=148).reshape(n, 60)
    return (raw[:, 0:4].copy().view('<i4').ravel().astype(np.int64),
            raw[:, 32:40].copy().view('<f8').ravel())


def r9(u):
    c = np.concatenate(([0.0], np.cumsum(u)))
    i = np.arange(1, len(u)+1)
    return c[i]-c[np.clip(i-9, 0, len(u))]


def offdiag(C):
    n = C.shape[0]
    return (C.sum()-n)/(n*n-n)


def acf1(v):
    m = v.mean()
    num = ((v[:-1]-m)*(v[1:]-m)).sum()
    den = ((v-m)**2).sum()
    return num/den if den else 0.0


def pairs_for(c):
    """(symbol, rev) where rev=True means 'c is the QUOTE currency'."""
    if c == 'XAU':
        return [(g, False) for g in GOLD]
    out = [(p, False) for p in PAIRS if p[:3] == c]      # c is base
    out += [(p, True) for p in PAIRS if p[3:] == c]      # c is quote
    if c in GOLD_OF:
        out.append((GOLD_OF[c], False))                  # XAU<c> : XAU base, c quote
    return out


def main():
    seen = set(); panel = {}
    with open(PANEL, newline='') as f:
        r = csv.reader(f); next(r)
        for a in r:
            if len(a) < 20 or a[1] not in ('H1', 'H4'):
                continue
            k = (a[1], a[0])
            if k in seen: continue
            seen.add(k)
            v = {}
            for i in range(9):
                try: v[a[2+i*2].strip()] = float(a[3+i*2])
                except ValueError: pass
            if len(v) != 9: continue
            t = dt.datetime.strptime(a[0], '%Y.%m.%d %H:%M')
            panel.setdefault(a[1], []).append((int((t-dt.datetime(1970,1,1)).total_seconds()), v))
    for k in panel: panel[k].sort()

    Ns = np.array([n_of(c) for c in CCY], float)

    for tf, suf in (('H1', '60'), ('H4', '240')):
        sers = {s: read_hst(os.path.join(HST, s+suf+'.hst'))
                for s in PAIRS+GOLD if os.path.exists(os.path.join(HST, s+suf+'.hst'))}
        tsec = np.array([r[0] for r in panel[tf]])
        obsP = np.array([[r[1][c] for c in CCY] for r in panel[tf]])
        Uobs = obsP*Ns

        Umod = np.full((len(tsec), 9), np.nan)
        ok = np.ones(len(tsec), bool)
        arrs = {s: r9(np.concatenate(([0.0], (cl[1:] > cl[:-1]).astype(float))))
                for s, (ts, cl) in sers.items()}
        for ci, c in enumerate(CCY):
            acc = np.zeros(len(tsec))
            for sym, rev in pairs_for(c):
                ts, cl = sers[sym]
                idx = np.searchsorted(ts, tsec, side='right')-1
                v = (idx >= 9) & (idx < len(ts))
                ok &= v
                cnt = arrs[sym][np.clip(idx, 0, len(ts)-1)]
                acc += np.where(v, (9.0-cnt) if rev else cnt, 0)
            Umod[:, ci] = acc
        m = ok
        O = Uobs[m]; P = Umod[m]
        print(f'\n===== {tf}  n={m.sum()}  (same subset for obs & model)')
        print(f'{"ccy":4s} {"N":>2s} | {"obsMean":>7s} {"obsSD":>6s} {"modMean":>7s} {"modSD":>6s} {"SDratio":>7s} {"corr":>6s} {"acf1_obs":>8s} {"acf1_mod":>8s} {"exact%":>6s}')
        for j, c in enumerate(CCY):
            o, p_ = O[:, j], P[:, j]
            corr = np.corrcoef(o, p_)[0, 1] if p_.std() > 1e-9 else 0
            ex = (np.abs(o-p_) < 0.25).mean()*100
            print(f'{c:4s} {int(Ns[j]):2d} | {o.mean():7.2f} {o.std():6.2f} {p_.mean():7.2f} {p_.std():6.2f} '
                  f'{o.std()/p_.std():7.2f} {corr:+6.3f} {acf1(o):8.3f} {acf1(p_):8.3f} {ex:6.1f}')
        Co = np.corrcoef(O[:, :8].T); Cp = np.corrcoef(P[:, :8].T)
        print(f'xsec corr (8 ccy):  observed {offdiag(Co):+.3f}   model {offdiag(Cp):+.3f}')
        s8o = O[:, :8].sum(1); s8p = P[:, :8].sum(1)
        print(f'sum8(U):            observed {s8o.mean():.1f} +- {s8o.std():.2f}   model {s8p.mean():.1f} +- {s8p.std():.2f}')
        print(f'U max observed:     {" ".join(f"{c}={O[:, j].max():.0f}/{int(9*Ns[j])}" for j, c in enumerate(CCY))}')
        print('implied partner-rho from sd ratio: rho = (ratio^2-1)/(N-1)')
        print('  ' + '  '.join(f'{c}={( (O[:, j].std()/P[:, j].std())**2-1)/(Ns[j]-1):+.2f}'
                               for j, c in enumerate(CCY)))

        # ---- intrabar update test (b): does the panel change inside one bar?
        dtm = np.array([panel[tf][i][0] for i in range(len(tsec))])
        step = int(suf)*60
        bucket = (dtm//step)
        first = {}
        changes = np.zeros(9)
        nb = 0
        prev = {}
        for i, b in enumerate(bucket):
            if b not in prev:
                prev[b] = 0; nb += 1
                continue
            prev[b] += 1
            if np.any(np.abs(O[i]-O[i-1]) > 0.25) if False else np.any(obsP[i] != obsP[i-1]):
                changes += 1
        print(f'intrabar (b-test): {nb} bars, {int(changes.max())} bars where panel CHANGED inside the bar '
              f'({100*changes.max()/max(nb-1,1):.1f}% of consecutive sample pairs)')


if __name__ == '__main__':
    main()
