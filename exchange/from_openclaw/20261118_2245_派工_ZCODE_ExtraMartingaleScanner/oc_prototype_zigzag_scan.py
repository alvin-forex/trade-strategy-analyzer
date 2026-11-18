import struct
PATH = '/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/history/VantageInternational-Live 11/EURUSD60.hst'
PIP = 0.0001
d = open(PATH, 'rb').read()
n = (len(d)-148)//60
bars = []
for i in range(n):
    b = 148+i*60
    t = struct.unpack_from('<q', d, b)[0]
    o,h,l,c = struct.unpack_from('<dddd', d, b+8)
    bars.append((t,o,h,l,c))
def zigzag(bs, depth=12):
    piv, mode = [], None
    for i in range(depth, len(bs)-depth):
        win = bs[i-depth:i+depth+1]
        ish = bs[i][2] >= max(x[2] for x in win); isl = bs[i][3] <= min(x[3] for x in win)
        if ish and mode != 'down': piv.append((i,'H',bs[i][2])); mode='down'
        elif isl and mode != 'up': piv.append((i,'L',bs[i][3])); mode='up'
        elif ish and mode=='down' and piv and piv[-1][1]=='H' and bs[i][2]>piv[-1][2]: piv[-1]=(i,'H',bs[i][2])
        elif isl and mode=='up' and piv and piv[-1][1]=='L' and bs[i][3]<piv[-1][2]: piv[-1]=(i,'L',bs[i][3])
    return piv
def merge(piv, mp=0.35):
    segs=[]
    for k in range(1,len(piv)):
        a,b2=piv[k-1],piv[k]; amp=abs(b2[2]-a[2])
        if amp<=0: continue
        if segs and segs[-1]>0 and amp < mp*segs[-1]: continue
        segs.append(amp)
    return segs
def inc(s,p):
    nn=len(s); pos=(nn-1)*p; lo=int(pos); f=pos-lo
    return s[lo]+f*(s[lo+1]-s[lo]) if lo+1<nn else s[lo]
F = (17,73,119,166)
res=[]
for start in range(0, len(bars)-1024, 25):
    seg = bars[start:start+1024]
    a = sorted(x/PIP for x in merge(zigzag(seg)))
    if len(a)<15: continue
    v = (a[0], inc(a,.8), inc(a,.95), a[-1])
    err = sum(abs(v[i]-F[i]) for i in range(4))
    res.append((round(err,1), start, len(bars)-(start+1024), round(v[0],1), round(v[1],1), round(v[2],1), round(v[3],1), len(a)))
res.sort()
print('fixture:', F)
for r in res[:6]: print('err=%s | 窗尾距而家 %s 燭 | bands %s/%s/%s/%s | %s波' % (r[0], r[2], r[3], r[4], r[5], r[6], r[7]))
