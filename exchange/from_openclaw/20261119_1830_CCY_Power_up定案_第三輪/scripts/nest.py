"""Narrow the nesting depth: up-count from m nested lookbacks, rescaled to 0..9.

m=1  -> 9 copies of close[t] > close[t-1]          (adjacent; sd too LOW)
m=9  -> 9 distinct lookbacks close[t] > close[t-k] (fan; sd too HIGH)
Find the m whose sd(U) matches the panel.
"""
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

def pairs_for(c):
    if c == 'XAU':
        return [(g, False) for g in GOLD]
    o = [(p, False) for p in PAIRS if p[:3] == c] + [(p, True) for p in PAIRS if p[3:] == c]
    if c in GM: o.append((GM[c], False))
    return o

seen = set(); panel = {}
for a in csv.reader(open(T+'/MQL4/Files/ccy_power_reader.csv', newline='')):
    if len(a) < 20 or a[0] == 'timestamp' or a[1] != 'H4':
        continue
    if a[0] in seen: continue
    seen.add(a[0]); v = {}
    for i in range(9):
        try: v[a[2+i*2].strip()] = float(a[3+i*2])
        except ValueError: pass
    if len(v) != 9: continue
    panel.setdefault('H4', []).append((int((dt.datetime.strptime(a[0], '%Y.%m.%d %H:%M')-dt.datetime(1970,1,1)).total_seconds()), v))
panel['H4'].sort()
Ns = np.array([N(c) for c in CCY], float)

suf = '240'
sers = {s: hst(os.path.join(HST, s+suf+'.hst')) for s in PAIRS+GOLD if os.path.exists(os.path.join(HST, s+suf+'.hst'))}
tsec = np.array([r[0] for r in panel['H4']])
obs = np.array([[r[1][c] for c in CCY] for r in panel['H4']])
Uobs = obs*Ns

print(f'{"m":>2s} {"obsSD":>6s} {"modSD":>6s} {"ratio":>6s} {"corr":>6s} {"exact%":>6s}  per-ccy ratio')
for m in (1, 2, 3, 4, 5, 6, 9):
    U = np.zeros((len(tsec), 9)); ok = np.ones(len(tsec), bool)
    for ci, c in enumerate(CCY):
        acc = np.zeros(len(tsec))
        for sym, rev in pairs_for(c):
            ts, cl = sers[sym]
            idx = np.searchsorted(ts, tsec, side='right')-1
            v = (idx >= m+1) & (idx < len(ts)); ok &= v
            safe = np.clip(idx, 0, len(ts)-1)
            cnt = np.zeros(len(tsec))
            for kk in range(1, m+1):
                cnt += (cl[safe] > cl[np.clip(safe-kk, 0, len(ts)-1)]).astype(float)
            cnt = cnt/m*9.0          # rescale to 0..9 so the scale stays comparable
            acc += np.where(v, (9.0-cnt) if rev else cnt, 0)
        U[:, ci] = acc
    O = Uobs[ok]; P = U[ok]
    cors = [np.corrcoef(O[:, j], P[:, j])[0, 1] for j in range(8)]
    ex = (np.abs(O-P) < 0.25).mean()*100
    ratios = O[:, :8].std(0)/P[:, :8].std(0)
    print(f'{m:2d} {O[:, :8].std():6.2f} {P[:, :8].std():6.2f} {np.mean(ratios):6.2f} {np.mean(cors):+6.3f} {ex:6.1f}  ' + ' '.join(f'{r:.2f}' for r in ratios))
