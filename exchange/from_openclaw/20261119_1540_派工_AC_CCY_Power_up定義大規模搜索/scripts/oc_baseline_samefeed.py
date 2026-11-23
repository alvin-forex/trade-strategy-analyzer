#!/usr/bin/env python3
"""Precision + correlation check on the live panel CSV (same-machine Tier-B)."""
import sys, os, csv, datetime, statistics
from collections import Counter, defaultdict
sys.path.insert(0, '/home/alvin/.openclaw/workspace/trade_strategy_analyzer')
from engine.research.hst_lib import read_hst, to_dt

TERM='/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549'
HST=TERM+'/history/Alpari-Pro.ECN-Demo'
CSVF=TERM+'/MQL4/Files/ccy_power_reader.csv'
PAIRS=['AUDCAD','AUDCHF','AUDJPY','AUDNZD','AUDUSD','CADCHF','CADJPY','CHFJPY','EURAUD','EURCAD','EURCHF','EURGBP','EURJPY','EURNZD','EURUSD','GBPAUD','GBPCAD','GBPCHF','GBPJPY','GBPNZD','GBPUSD','NZDCAD','NZDCHF','NZDJPY','NZDUSD','USDCAD','USDCHF','USDJPY']
GOLD=['XAUAUD','XAUEUR','XAUGBP','XAUJPY','XAUUSD']
GMAP={'AUD':'XAUAUD','EUR':'XAUEUR','GBP':'XAUGBP','JPY':'XAUJPY','USD':'XAUUSD'}
TFMAP={'H1':'60','H4':'240'}
CCY=['EUR','GBP','AUD','NZD','CHF','JPY','XAU','CAD','USD']

rows=[];seen=set()
with open(CSVF,newline='') as f:
    r=csv.reader(f); next(r)
    for a in r:
        if len(a)<20 or a[1] not in TFMAP: continue
        try: t=datetime.datetime.strptime(a[0],'%Y.%m.%d %H:%M')
        except ValueError: continue
        v={}
        for i in range(9):
            nm=a[2+i*2].strip()
            try: v[nm]=float(a[3+i*2])
            except ValueError: pass
        if len(v)!=9: continue
        k=(a[1],t)
        if k in seen: continue
        seen.add(k); rows.append((t,a[1],v))

print('=== precision: are panel texts exact lattice values? ===')
for c in ('EUR','GBP','AUD','XAU'):
    cnt=Counter()
    for t,tf,v in rows[:4000]:
        x=v[c]
        for N in (7,8,5):
            if abs(x*N-round(x*N))<1e-4: cnt[N]+=1
    print(f'{c:4s} exactInt@N5/7/8 ->', dict(cnt))

print('\n=== decimal places observed (unique fractions) ===')
fr=Counter()
for t,tf,v in rows[:2000]:
    for c in CCY:
        s=f'{v[c]:.4f}'
        fr[s.split('.')[1]]+=1
print('top 8:', fr.most_common(8))

def n_of(c):
    if c=='XAU': return len(GOLD)
    return sum(1 for p in PAIRS if p[:3]==c or p[3:]==c)+(1 if c in GMAP else 0)

BARS={}
for tf,suf in TFMAP.items():
    BARS[tf]={}
    for s in PAIRS+GOLD:
        p=os.path.join(HST,s+suf+'.hst')
        if os.path.exists(p):
            BARS[tf][s]={to_dt(b[0]):b[4] for b in read_hst(p)}

def pred(c,tf,end):
    bars=BARS[tf]; tot=0
    if c=='XAU':
        for g in GOLD:
            s=bars.get(g)
            if not s or end not in s: return None
            d=sorted(s); i=d.index(end)
            if i<9: return None
            for k in range(9):
                a,b=d[i-k],d[i-k-1]
                diff=s[a]-s[b]
                if diff>0: tot+=1
        return tot
    for p in PAIRS:
        rev=p[3:]==c
        if p[:3]!=c and not rev: continue
        s=bars.get(p)
        if not s or end not in s: return None
        d=sorted(s); i=d.index(end)
        if i<9: return None
        for k in range(9):
            a,b=d[i-k],d[i-k-1]
            diff=s[a]-s[b]
            if diff>0: u=1
            elif diff<0: u=0
            else: continue
            tot += u if not rev else 1-u
    return tot

print('\n=== corr / sd ratio on LIVE panel (same machine) ===')
step={'H1':3600,'H4':14400}
for tf in ('H1','H4'):
    for c in ('EUR','GBP','USD','XAU'):
        N=n_of(c); X=[];Y=[]
        for t,tf2,v in rows:
            if tf2!=tf: continue
            end=t - datetime.timedelta(seconds=step[tf])
            pr=pred(c,tf,end)
            if pr is None: continue
            X.append(pr); Y.append(v[c])
        if len(X)<60: continue
        mx,my=statistics.mean(X),statistics.mean(Y)
        num=sum((a-mx)*(b-my) for a,b in zip(X,Y))
        den=(sum((a-mx)**2 for a in X)*sum((b-my)**2 for b in Y))**0.5
        corr=num/den if den else 0
        print(f'{tf} {c:4s} n={len(X):5d} corr={corr:6.3f} sdObs={statistics.pstdev(Y):5.2f} sdMod={statistics.pstdev(X):5.2f} ratio={statistics.pstdev(Y)/statistics.pstdev(X):4.2f}')
