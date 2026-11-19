import csv, datetime as dt
from collections import Counter, defaultdict
T='/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/MQL4/Files/ccy_power_reader.csv'
CCY=['EUR','GBP','AUD','NZD','CHF','JPY','XAU','CAD','USD']
seen=set(); rows=defaultdict(list)
for a in csv.reader(open(T,newline='')):
    if len(a)<20 or a[0]=='timestamp' or a[1] not in ('H1','H4'): continue
    k=(a[1],a[0])
    if k in seen: continue
    seen.add(k); v={}
    for i in range(9):
        try: v[a[2+i*2].strip()]=float(a[3+i*2])
        except ValueError: pass
    if len(v)!=9: continue
    t=int((dt.datetime.strptime(a[0],'%Y.%m.%d %H:%M')-dt.datetime(1970,1,1)).total_seconds())
    rows[a[1]].append((t,tuple(v[c] for c in CCY)))
for tf,step in (('H1',3600),('H4',14400)):
    rs=sorted(rows[tf])
    buckets=defaultdict(list)
    for t,v in rs: buckets[t//step].append(v)
    full=[b for b in buckets if len(buckets[b])>=2]
    same=sum(1 for b in full if len(set(buckets[b]))==1)
    dist=Counter(len(set(buckets[b])) for b in full)
    print(f'{tf}: bars={len(buckets)} sampled>1x={len(full)}  identical={same} ({100*same/max(len(full),1):.1f}%)  distinct-value-count dist={dict(sorted(dist.items()))}')
    # per-currency change rate between consecutive samples in same bar
    chg=Counter()
    for b in full:
        vals=buckets[b]
        for i in range(1,len(vals)):
            for j in range(9):
                if vals[i][j]!=vals[i-1][j]: chg[CCY[j]]+=1
    tot=sum(len(buckets[b])-1 for b in full)
    print('   per-ccy changed-in-bar counts:', {c:chg[c] for c in CCY}, 'of', tot*9)
