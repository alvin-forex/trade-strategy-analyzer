import csv, datetime as dt, os
import numpy as np

T = '/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549'
HST = T + '/history/Alpari-Pro.ECN-Demo'
PAIRS = ['AUDCAD','AUDCHF','AUDJPY','AUDNZD','AUDUSD','CADCHF','CADJPY','CHFJPY',
         'EURAUD','EURCAD','EURCHF','EURGBP','EURJPY','EURNZD','EURUSD',
         'GBPAUD','GBPCAD','GBPCHF','GBPJPY','GBPNZD','GBPUSD',
         'NZDCAD','NZDCHF','NZDJPY','NZDUSD','USDCAD','USDCHF','USDJPY']
GOLD = ['XAUAUD','XAUEUR','XAUGBP','XAUJPY','XAUUSD']
CCY = ['EUR','GBP','AUD','NZD','CHF','JPY','XAU','CAD','USD']
GM = {'AUD':'XAUAUD','EUR':'XAUEUR','GBP':'XAUGBP','JPY':'XAUJPY','USD':'XAUUSD'}

def N(c):
    return len(GOLD) if c == 'XAU' else sum(1 for p in PAIRS if p[:3] == c or p[3:] == c) + (1 if c in GM else 0)

def hst(p):
    d = open(p, 'rb').read()
    n = (len(d)-148)//60
    raw = np.frombuffer(d, dtype=np.uint8, count=n*60, offset=148).reshape(n, 60)
    return raw[:, 0:4].copy().view('<i4').ravel().astype(np.int64), raw[:, 32:40].copy().view('<f8').ravel()

def offdiag(C):
    n = C.shape[0]
    return (C.sum()-n)/(n*n-n)

def pairs_for(c):
    if c == 'XAU':
        return [(g, False) for g in GOLD]
    o = [(p, False) for p in PAIRS if p[:3] == c] + [(p, True) for p in PAIRS if p[3:] == c]
    if c in GM:
        o.append((GM[c], False))
    return o

seen = set(); panel = {}
for a in csv.reader(open(T+'/MQL4/Files/ccy_power_reader.csv', newline='')):
    if len(a) < 20 or a[0] == 'timestamp' or a[1] not in ('H1', 'H4'):
        continue
    k = (a[1], a[0])
    if k in seen: continue
    seen.add(k); v = {}
    for i in range(9):
        try: v[a[2+i*2].strip()] = float(a[3+i*2])
        except ValueError: pass
    if len(v) != 9: continue
    panel.setdefault(a[1], []).append((int((dt.datetime.strptime(a[0], '%Y.%m.%d %H:%M')-dt.datetime(1970,1,1)).total_seconds()), v))
for k in panel: panel[k].sort()
Ns = np.array([N(c) for c in CCY], float)

for tf, suf in (('H1', '60'), ('H4', '240')):
    sers = {s: hst(os.path.join(HST, s+suf+'.hst')) for s in PAIRS+GOLD if os.path.exists(os.path.join(HST, s+suf+'.hst'))}
    tsec = np.array([r[0] for r in panel[tf]])
    obs = np.array([[r[1][c] for c in CCY] for r in panel[tf]])
    Uobs = obs*Ns
    for span in (9,):
        U = np.zeros((len(tsec), 9)); ok = np.ones(len(tsec), bool)
        for ci, c in enumerate(CCY):
            acc = np.zeros(len(tsec))
            for sym, rev in pairs_for(c):
                ts, cl = sers[sym]
                idx = np.searchsorted(ts, tsec, side='right')-1
                v = (idx >= span+1) & (idx < len(ts))
                ok &= v
                safe = np.clip(idx, 0, len(ts)-1)
                cnt = np.zeros(len(tsec))
                for kk in range(1, span+1):
                    cnt += (cl[safe] > cl[np.clip(safe-kk, 0, len(ts)-1)]).astype(float)
                acc += np.where(v, (span-cnt) if rev else cnt, 0)
            U[:, ci] = acc
        m = ok; O = Uobs[m]; P = U[m]
        print(f'\n===== {tf} FAN model (up_k = close[t] > close[t-k], k=1..9)  n={m.sum()}')
        print(f'{"ccy":4s} {"N":>2s} {"obsMean":>7s} {"obsSD":>6s} {"modMean":>7s} {"modSD":>6s} {"SDratio":>7s} {"corr":>6s} {"exact%":>6s}')
        for j, c in enumerate(CCY):
            o, pp = O[:, j], P[:, j]
            print(f'{c:4s} {int(Ns[j]):2d} {o.mean():7.2f} {o.std():6.2f} {pp.mean():7.2f} {pp.std():6.2f} {o.std()/pp.std():7.2f} {np.corrcoef(o, pp)[0, 1]:+6.3f} {(np.abs(o-pp) < 0.25).mean()*100:6.1f}')
        print('xsec obs %+.3f  model %+.3f' % (offdiag(np.corrcoef(O[:, :8].T)), offdiag(np.corrcoef(P[:, :8].T))))
        print('sum8 obs %.1f+-%.2f  model %.1f+-%.2f' % (O[:, :8].sum(1).mean(), O[:, :8].sum(1).std(), P[:, :8].sum(1).mean(), P[:, :8].sum(1).std()))
