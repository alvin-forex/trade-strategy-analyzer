#!/usr/bin/env python3
"""v5: fingerprint test.

Recover the integer count U_c = round(Power_c * N_c) from ground truth, then
compare its *distributional fingerprint* against the adjacent-close model and
against theoretical bounds. Any candidate 'up' definition must reproduce:
  mean(U), sd(U), acf1(U)
"""
import sys, os, csv, datetime, statistics
sys.path.insert(0, '/home/alvin/.openclaw/workspace/trade_strategy_analyzer')
from engine.research.hst_lib import read_hst, to_dt

HST = '/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/history/Alpari-Pro.ECN-Demo'
FIX = '/home/alvin/.openclaw/workspace/trade_strategy_analyzer/exchange/from_autoclaw/20261118_1210_PowerHistory樣本與解碼報告/D1_8_decoded_fixture.csv'
PAIRS = ['AUDCAD','AUDCHF','AUDJPY','AUDNZD','AUDUSD','CADCHF','CADJPY','CHFJPY',
         'EURAUD','EURCAD','EURCHF','EURGBP','EURJPY','EURNZD','EURUSD',
         'GBPAUD','GBPCAD','GBPCHF','GBPJPY','GBPNZD','GBPUSD',
         'NZDCAD','NZDCHF','NZDJPY','NZDUSD','USDCAD','USDCHF','USDJPY']
CCY = ['EUR','GBP','AUD','NZD','CHF','JPY','CAD','USD']
GS = [(datetime.date(2018,12,11), ['AUD','USD']),
      (datetime.date(2021,4,14), ['AUD','USD','EUR']),
      (datetime.date(2023,11,23), ['AUD','USD','EUR','JPY'])]
def gs(d):
    cur = []
    for s,l in GS:
        if d>=s: cur=l
    return cur

gt=[(datetime.date.fromisoformat(r['date']),{c:float(r[c]) for c in CCY})
    for r in csv.DictReader(open(FIX))]
series={}
for p in PAIRS:
    f=os.path.join(HST,p+'1440.hst')
    if os.path.exists(f):
        series[p]={to_dt(b[0]).date():b[4] for b in read_hst(f)}

def n_of(c,d):
    return sum(1 for p in PAIRS if p[:3]==c or p[3:]==c) + (1 if c in gs(d) else 0)

def acf1(v):
    m=statistics.mean(v)
    num=sum((v[i]-m)*(v[i+1]-m) for i in range(len(v)-1))
    den=sum((x-m)**2 for x in v)
    return num/den if den else 0.0

def model_u(c,d,lag=0,tie_zero=True):
    dd=d+datetime.timedelta(days=lag)
    s=0
    for p in PAIRS:
        rev = p[3:]==c
        if p[:3]!=c and not rev:
            continue
        ser=series.get(p)
        if not ser or dd not in ser: return None
        dates=sorted(ser)
        i=dates.index(dd)
        if i<9: return None
        cnt=0
        for k in range(9):
            a,b=dates[i-k],dates[i-k-1]
            diff=ser[a]-ser[b]
            if diff>0: u=1
            elif diff==0: u=None if tie_zero else 0
            else: u=0
            if u is None: continue
            cnt += u if not rev else 1-u
        s+=cnt
    return s

print(f'{"ccy":4s} {"N":>2s} {"n":>5s} | {"Umean":>6s} {"Usd":>6s} {"Uacf1":>6s} {"Umin":>5s} {"Umax":>5s} | {"Mmean":>6s} {"Msd":>6s} {"Macf1":>7s} | {"sdRatio":>7s}')
for c in CCY:
    Uobs=[]; Umod=[]
    for d,obs in gt:
        N=n_of(c,d)
        u=obs[c]*N
        r=round(u)
        if abs(u-r)>1e-6: continue
        m=model_u(c,d)
        Uobs.append(r)
        if m is not None: Umod.append(m)
        else: Umod.append(None)
    pairs=[(a,b) for a,b in zip(Uobs,Umod) if b is not None]
    Uo=[a for a,_ in pairs]; Um=[b for _,b in pairs]
    if len(Uo)<50: continue
    N=n_of(c,gt[-1][0])
    print(f'{c:4s} {N:2d} {len(Uo):5d} | {statistics.mean(Uo):6.2f} {statistics.pstdev(Uo):6.2f} {acf1(Uo):6.3f} {min(Uo):5.0f} {max(Uo):5.0f} | {statistics.mean(Um):6.2f} {statistics.pstdev(Um):6.2f} {acf1(Um):7.3f} | {statistics.pstdev(Uo)/statistics.pstdev(Um):7.2f}')
