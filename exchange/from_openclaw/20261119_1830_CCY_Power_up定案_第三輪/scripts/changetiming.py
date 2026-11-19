"""When inside a bar does the panel change? Uniform => forming bar included.
Clustered right after the bar boundary => closed bars only (or MTF on a coarser TF).
"""
import csv, datetime as dt
from collections import Counter, defaultdict

T = '/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/MQL4/Files/ccy_power_reader.csv'
CCY = ['EUR','GBP','AUD','NZD','CHF','JPY','XAU','CAD','USD']

rows = defaultdict(list)
seen = set()
for a in csv.reader(open(T, newline='')):
    if len(a) < 20 or a[0] == 'timestamp' or a[1] not in ('H1', 'H4'):
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
    rows[a[1]].append((t, tuple(v[c] for c in CCY)))

for tf, mins in (('H1', 60), ('H4', 240)):
    rs = sorted(rows[tf])
    chg = Counter()
    tot = Counter()
    for i in range(1, len(rs)):
        t0, v0 = rs[i-1]
        t1, v1 = rs[i]
        m = (t1.hour*60 + t1.minute) % mins
        tot[m] += 1
        if v1 != v0:
            chg[m] += 1
    print(f'=== {tf}: change rate by minute-of-bar (n={sum(tot.values())})')
    # aggregate into deciles of the bar
    dec = 10
    buckets = [[0, 0] for _ in range(dec)]
    for m in tot:
        d = min(m*dec//mins, dec-1)
        buckets[d][0] += chg[m]
        buckets[d][1] += tot[m]
    for d, (c, n) in enumerate(buckets):
        print(f'  decile {d} ({d*mins//dec:>3d}-{(d+1)*mins//dec-1:>3d} min): changed {c}/{n} = {100*c/max(n,1):5.1f}%')
print('\n(If the label TF were the indicator TF and only CLOSED bars were used,')
print(' changes would be ~0% except in the first decile.)')
