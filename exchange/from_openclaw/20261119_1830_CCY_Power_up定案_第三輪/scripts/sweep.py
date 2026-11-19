#!/usr/bin/env python3
"""Fingerprint sweep on the ONLY truly same-source dataset we have.

  panel side : MQL4/Files/ccy_power_reader.csv   (CCYPowerReader.mq4 reads the
               ORIGINAL indicator's __table_edit_* objects, every 5 min)
  bars side  : the same terminal's .hst files
  => same machine, same broker feed, same indicator instance. No probe needed.

For every candidate 'up' definition we compute, per panel row:
    U_c  = sum over partners of (9 comparisons)
    Power = U_c / N_c
and compare against the panel.

Two things must BOTH hold for a candidate to be credible:
    (1) exact hit rate high
    (2) sd(U) matches observed  (9.1 - 14.1).  sd captures structure:
        it cannot be faked by fitting.
"""
import bisect
import csv
import datetime as dt
import os
import sys

import numpy as np

sys.path.insert(0, '/home/alvin/.openclaw/workspace/trade_strategy_analyzer')
from engine.research.hst_lib import HDR, REC  # noqa: E402
import struct

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
TF = {'H1':'60','H4':'240','D1':'1440'}
EPOCH = dt.datetime(1970,1,1)


def read_hst_np(path):
    d = open(path,'rb').read()
    n = (len(d)-HDR)//REC
    t = np.frombuffer(d, dtype='<i4', count=n, offset=HDR + 0, ) if False else None
    # records are 60 bytes: int32 t, 5 doubles, int32 spread
    raw = np.frombuffer(d, dtype=np.uint8, count=n*REC, offset=HDR).reshape(n, REC)
    ts = raw[:, 0:4].copy().view('<i4').ravel()
    closes = raw[:, 32:40].copy().view('<f8').ravel()
    return ts, closes


def n_of(c):
    if c == 'XAU':
        return len(GOLD)
    return sum(1 for p in PAIRS if p[:3]==c or p[3:]==c) + (1 if c in GOLD_OF else 0)


def rolling_sum(a, w):
    """out[i] = sum a[i-w+1 .. i]  (same length as a, windows truncated at start)"""
    c = np.concatenate(([0.0], np.cumsum(a, dtype=float)))
    idx = np.arange(1, len(a)+1)
    lo = np.clip(idx - w, 0, len(a))
    return c[idx] - c[lo]


def sma(a, w):
    s = rolling_sum(a, w)
    n = np.minimum(np.arange(len(a))+1, w)
    return s/n


def ema(a, w):
    k = 2.0/(w+1)
    out = np.empty_like(a)
    e = a[0]
    for i, v in enumerate(a):
        e = v*k + e*(1-k)
        out[i] = e
    return out


def build_basis(close, name, k):
    """returns per-bar up indicator array (1 if 'up' that bar, else 0)"""
    n = len(close)
    if name == 'adj':
        u = np.zeros(n); u[1:] = (close[1:] > close[:-1]).astype(float)
    elif name == 'lagk':
        u = np.zeros(n); u[k:] = (close[k:] > close[:-k]).astype(float)
    elif name == 'rank':
        u = np.zeros(n)
        for j in range(1, k+1):
            u[j:] += (close[j:] > close[:-j]).astype(float)
        u /= k
        return u
    elif name == 'sma':
        m = sma(close, k); u = (close > m).astype(float)
    elif name == 'ema':
        m = ema(close, k); u = (close > m).astype(float)
    else:
        raise ValueError(name)
    return u


def main():
    # ---------- panel ----------
    seen = set()
    panel = {}
    with open(PANEL, newline='') as f:
        r = csv.reader(f)
        next(r)
        for a in r:
            if len(a) < 20 or a[1] not in TF:
                continue
            key = (a[1], a[0])
            if key in seen:
                continue
            seen.add(key)
            v = {}
            for i in range(9):
                nm = a[2+i*2].strip()
                try: v[nm] = float(a[3+i*2])
                except ValueError: pass
            if len(v) != 9:
                continue
            t = dt.datetime.strptime(a[0], '%Y.%m.%d %H:%M')
            panel.setdefault(a[1], []).append((int((t-EPOCH).total_seconds()), v))
    for k in panel:
        panel[k].sort()
    print('panel rows:', {k: len(v) for k, v in panel.items()})

    # ---------- bars ----------
    series = {}
    for tf, suf in TF.items():
        series[tf] = {}
        for s in PAIRS+GOLD:
            p = os.path.join(HST, s+suf+'.hst')
            if os.path.exists(p):
                ts, cl = read_hst_np(p)
                series[tf][s] = (ts, cl)

    CAND = [('adj',1), ('lagk',3), ('lagk',9), ('rank',9), ('sma',9), ('sma',10),
            ('sma',20), ('sma',50), ('ema',9), ('ema',10), ('ema',20)]

    results = []
    for tf in ('H1','H4'):
        rows = panel.get(tf, [])
        if not rows: continue
        step = int(TF[tf])*60
        # precompute indicator arrays per symbol per candidate
        arrays = {}
        for s, (ts, cl) in series[tf].items():
            arrays[s] = {}
            for name, k in CAND:
                u = build_basis(cl, name, k)
                arrays[s][(name, k)] = (ts, rolling_sum(u, 9))

        for name, k in CAND:
            # index panel rows into bar index per symbol
            tsec = np.array([r[0] for r in rows])
            obs = np.array([[r[1][c] for c in CCY] for r in rows])
            U = np.zeros((len(rows), 9))
            ok = np.ones(len(rows), bool)
            for ci, c in enumerate(CCY):
                acc = np.zeros(len(rows))
                for p in PAIRS:
                    rev = p[3:] == c
                    if p[:3] != c and not rev:
                        continue
                    ts, rs = arrays[p][(name, k)]
                    idx = np.searchsorted(ts, tsec, side='right') - 1
                    valid = (idx >= 30) & (idx < len(ts))
                    okt = np.zeros(len(rows), bool)
                    okt[valid] = True
                    ok &= okt
                    safe = np.where(valid, idx, 0)
                    cnt = rs[safe]
                    if rev:
                        cnt = 9.0 - cnt
                    acc += np.where(valid, cnt, 0)
                for g in GOLD:
                    if g[3:] != c:
                        continue
                    ts, rs = arrays[g][(name, k)]
                    idx = np.searchsorted(ts, tsec, side='right') - 1
                    valid = (idx >= 30) & (idx < len(ts))
                    ok &= valid
                    safe = np.where(valid, idx, 0)
                    acc += np.where(valid, rs[safe], 0)
                U[:, ci] = acc
            Ns = np.array([n_of(c) for c in CCY], float)
            P = U / Ns
            m = ok
            if m.sum() < 100:
                continue
            Po = obs[m]; Pp = P[m]; Up = U[m]
            Uobs = Po * Ns          # observed integer count total
            exact = (np.abs(Pp - Po) < 0.005).mean()*100
            cors = []
            for ci in range(8):
                a_, b_ = Pp[:, ci], Po[:, ci]
                if a_.std() < 1e-9: continue
                cors.append(np.corrcoef(a_, b_)[0, 1])
            sd_obs = Uobs.std()
            sd_pred = Up.std()
            sratio = sd_obs/sd_pred if sd_pred > 0 else 0
            print(f'{tf} {name:5s} k={k:<3d} n={m.sum():5d} exact={exact:5.1f}% corr={np.mean(cors):+.3f} '
                  f'meanU_obs={Uobs.mean():5.1f} meanU_pred={Up.mean():5.1f} '
                  f'sd_obs={sd_obs:5.2f} sd_pred={sd_pred:5.2f} ratio={sratio:4.2f}')
            results.append((tf, name, k, int(m.sum()), exact, float(np.mean(cors)), sd_obs, sd_pred, sratio))

    results.sort(key=lambda r: -r[4])
    print('\n=== sorted by exact hit ===')
    print(f'{"tf":3s} {"basis":5s} {"k":>3s} {"n":>6s} {"exact%":>7s} {"corr":>7s} {"sd_obs":>7s} {"sd_pred":>8s} {"ratio":>6s}')
    for r in results[:12]:
        print(f'{r[0]:3s} {r[1]:5s} {r[2]:3d} {r[3]:6d} {r[4]:7.1f} {r[5]:+7.3f} {r[6]:7.2f} {r[7]:8.2f} {r[8]:6.2f}')


if __name__ == '__main__':
    main()
