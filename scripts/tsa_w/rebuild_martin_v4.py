#!/usr/bin/env python3
"""rebuild_martin_v4.py — martin_v4 頁 Template B 重建（照老闆 Excel v8.5 ＋ Muse 規格 2026-11-02）

藍本：TradingHistory_Analyzer_v8.5 十 sheet → 八區動線（Muse §3.1）：
  ① 整倉總覽 hero（判定章＋六宮格＋MAE/MFE 窄帶＋分層摘要）
  ② 馬丁偵測（LotTiers：基準 lot 校準＋層級分佈＋bar）
  ③ 商品分析器（揀選器＋BUY/SELL 對照＋止賺止蝕 box＋61 級 slider 效益曲線）
  ④ 商品方向總表　⑤ 月度樞紐（單月降級 bar）　⑥ MAE/MFE 散點（SVG）
  ⑦ 時間維度＋明細（7×24 heatmap＋累計線＋明細表）　⑧ 使用說明（<details>）

軍規（Muse §3.3）：
  - 每個互動必有預設渲染，fetch 甩線都有嘢睇（全數據預渲染入 HTML）
  - URL hash 同步（#sym=..&th=..）；heatmap hover 用 title（零 JS）
  - BUY 綠左 / SELL 紅右全站統一；「冇數·」與 $0 分清；PF 無虧損單顯「無虧損」
  - pips 為主 $ 為輔；深色 token §1.1
用法：
  python3 rebuild_martin_v4.py --signal 43024 [--force]
"""
import argparse
import csv
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HKT = timezone(timedelta(hours=8))
BASE = Path(__file__).resolve().parents[2]
REPORTS = BASE / 'docs' / 'reports'
DOWNLOADS = BASE / 'docs' / 'downloads'

# ── Muse §1.1 token＋八區版面 ─────────────────────────────────────────
CSS = """
:root{--bg:#0a0e17;--card:#111520;--card2:#1a1f2e;--zebra:#151b28;--brd:#1e2433;--th:#111520;
--text:#d0d0d0;--text2:#777;--pri:#FFD700;--acc:#64b5f6;--grn:#4CAF50;--red:#FF5722;--yel:#FFC107;
--radius:12px}
[data-theme="light"]{--bg:#f5f7fa;--card:#fff;--card2:#eef2f7;--zebra:#f0f4fa;--brd:#ddd;--th:#eef2f7;
--text:#333;--text2:#666;--pri:#0f3460;--acc:#e94560;--grn:#28a745;--red:#dc3545;--yel:#ffc107}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Microsoft JhengHei',sans-serif;background:var(--bg);color:var(--text);line-height:1.6;font-size:15px}
a{color:var(--acc);text-decoration:none}
.layout{max-width:1200px;margin:0 auto;padding:16px;display:grid;grid-template-columns:168px 1fr;gap:20px}
main{min-width:0}
.toc{position:sticky;top:16px;align-self:start;background:var(--card);border:1px solid var(--brd);border-radius:var(--radius);padding:14px 12px;font-size:.85em}
.toc h3{color:var(--pri);font-size:.95em;margin-bottom:8px}
.toc a{display:block;padding:5px 6px;border-radius:6px;color:var(--text2)}
.toc a:hover{background:var(--card2);color:var(--text)}
header.top{background:var(--card);border:1px solid var(--brd);border-radius:var(--radius);padding:14px 18px;margin-bottom:14px;display:flex;justify-content:space-between;align-items:center;gap:10px;flex-wrap:wrap}
header.top h1{font-size:1.2em;color:#fff}
header.top .sub{color:var(--text2);font-size:.85em}
#themeToggle{background:var(--card2);border:1px solid var(--brd);color:var(--text);border-radius:8px;padding:6px 12px;cursor:pointer;font-size:1em}
section{background:var(--card);border:1px solid var(--brd);border-radius:var(--radius);padding:18px 20px;margin-bottom:16px;overflow-x:auto}
section table{min-width:max-content}
@media(max-width:520px){.sel-bar select{max-width:44vw}}
section>h2{color:var(--pri);font-size:1.15em;margin-bottom:4px}
section>.legend{color:var(--text2);font-size:.8em;margin-bottom:12px}
.banner{background:rgba(255,193,7,.12);border:1px solid var(--yel);border-radius:var(--radius);padding:10px 14px;margin-bottom:14px;color:var(--yel);font-size:.88em}
.hero-grid{display:grid;grid-template-columns:2fr 3fr;gap:16px}
.hero-left .badge{display:inline-block;border:2px solid var(--grn);color:var(--grn);border-radius:10px;padding:8px 18px;font-weight:800;font-size:1.25em;background:rgba(76,175,80,.08)}
.hero-left .badge.martin{border-color:var(--pri);color:var(--pri);background:rgba(255,215,0,.08);box-shadow:0 0 18px rgba(255,215,0,.15)}
.hero-left .badge.none{border-color:#8B95A5;color:#8B95A5;background:rgba(139,149,165,.08)}
.hero-left .meta{color:var(--text2);font-size:.85em;margin-top:10px}
.hero-left .meta b{color:var(--text)}
.six{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
.six .cell{background:var(--card2);border:1px solid var(--brd);border-radius:10px;padding:10px 12px}
.six .k{color:var(--text2);font-size:.75em}
.six .v{font-size:1.18em;font-weight:700;margin-top:2px}
.v.pos{color:var(--grn)}.v.neg{color:var(--red)}
.narrow{margin-top:14px;background:var(--card2);border:1px solid var(--brd);border-radius:10px;padding:8px 14px;display:flex;gap:18px;flex-wrap:wrap;font-size:.82em;color:var(--text2)}
.narrow b{color:var(--text)}
.pills{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:14px}
.pill{background:var(--card2);border:1px solid var(--brd);border-radius:999px;padding:8px 14px;text-align:center}
.pill .k{color:var(--text2);font-size:.72em}
.pill .v{font-weight:700;font-size:1.02em}
table{width:100%;border-collapse:collapse;font-size:.88em}
th{background:var(--th);color:var(--text2);font-weight:600;padding:7px 9px;text-align:right;border-bottom:1px solid var(--brd);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
td{padding:6px 9px;border-bottom:1px solid var(--brd);text-align:right;white-space:nowrap}
tbody tr:nth-child(even){background:var(--zebra)}
.pos{color:var(--grn)}.neg{color:var(--red)}.muted{color:var(--text2)}
.dim{opacity:.45}
.buysell th:nth-child(2),.buysell td:nth-child(2){border-left:3px solid var(--grn)}
.buysell th:last-child,.buysell td:last-child{border-left:3px solid var(--red)}
.buy-h,.sell-h{display:inline-block;width:8px;height:8px;border-radius:2px;margin-right:5px}
.buy-h{background:var(--grn)}.sell-h{background:var(--red)}
.bar-cell{background:linear-gradient(90deg,rgba(100,181,246,.55),rgba(100,181,246,.15));border-radius:3px;min-height:12px}
.heat{display:grid;gap:2px;font-size:.72em}
.heat .lab{color:var(--text2);display:flex;align-items:center;justify-content:flex-end;padding-right:4px}
.heat .c{border-radius:3px;min-height:22px;display:flex;align-items:center;justify-content:center;color:var(--text)}
.heat .c.na{background:var(--card2);color:var(--text2)}
.hm-wrap{overflow-x:auto}
details{border:1px solid var(--brd);border-radius:10px;padding:10px 14px;margin-top:12px;background:var(--card2)}
details>summary{cursor:pointer;color:var(--acc);font-weight:600}
select,input[type=range]{accent-color:var(--acc)}
.sel-bar{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:14px}
.sel-bar label{color:var(--text2);font-size:.85em}
.sel-bar select{background:var(--card2);color:var(--text);border:1px solid var(--brd);border-radius:8px;padding:6px 10px;font-size:.95em}
.slider-row{display:flex;gap:12px;align-items:center;margin:10px 0 4px;flex-wrap:wrap}
.slider-row input[type=range]{flex:1;min-width:200px}
.slider-val{font-weight:700;color:var(--pri);min-width:64px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.svgbox{background:var(--card2);border:1px solid var(--brd);border-radius:10px;padding:10px;overflow-x:auto}
.svgbox svg{display:block;margin:0 auto}
.svgbox .cap{color:var(--text2);font-size:.78em;text-align:center;margin-top:4px}
.gline{stroke:#666;stroke-dasharray:4 4;stroke-width:1}
.footnote{color:var(--text2);font-size:.8em;margin-top:8px}
/* 自製 tooltip（老闆 0619：說明收 mouseover）——共享 bubble＋JS 定位，hover/tap/focus 出、離開/Esc/外點收 */
.tt{position:relative;display:inline-flex;align-items:center;cursor:help;color:var(--acc);font-size:.88em;line-height:1;vertical-align:baseline}
.tt.tt-w{color:var(--yel)}
.tt.tt-pill{border:1px solid var(--brd);background:var(--card2);border-radius:999px;padding:3px 10px;font-size:.78em}
.tt:focus-visible{outline:2px solid var(--acc);outline-offset:2px;border-radius:4px}
#tt-global{position:fixed;z-index:999;display:none;max-width:min(480px,84vw);background:var(--card);color:var(--text);border:1px solid var(--brd);border-radius:8px;padding:9px 12px;font-size:.85em;line-height:1.55;box-shadow:0 6px 20px rgba(0,0,0,.3);white-space:pre-line;pointer-events:none;font-weight:400}
.heat .c.tt{color:var(--text2)}
.guide{display:grid;grid-template-columns:1fr 1fr;gap:4px 22px;font-size:.85em}
.guide dt{color:var(--pri);font-weight:600}
.guide dd{color:var(--text2);margin-bottom:6px}
@media(max-width:860px){.layout{grid-template-columns:1fr}.toc{position:static;display:flex;flex-wrap:wrap;gap:2px}
.toc a{padding:4px 10px;background:var(--card2);border-radius:999px}
.hero-grid{grid-template-columns:1fr}.six{grid-template-columns:repeat(2,1fr)}.pills{grid-template-columns:repeat(2,1fr)}
.two{grid-template-columns:1fr}.guide{grid-template-columns:1fr}
.hm-wrap{max-height:280px}}
"""

JS = """
let SYM_DATA=%(sym_data)s, TH_MIN=0, TH_MAX=60;
function loadTheme(){const t=localStorage.getItem('tsa-theme')||'dark';document.documentElement.setAttribute('data-theme',t);document.getElementById('themeToggle').textContent=t==='dark'?'☀️':'🌙';}
function toggleTheme(){const c=document.documentElement.getAttribute('data-theme')||'dark',n=c==='dark'?'light':'dark';document.documentElement.setAttribute('data-theme',n);localStorage.setItem('tsa-theme',n);document.getElementById('themeToggle').textContent=n==='dark'?'☀️':'🌙';}
function fmt$(x){return (x<0?'-$':'$')+Math.abs(x).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});}
function hashState(){const h=new URLSearchParams(location.hash.slice(1));return {sym:h.get('sym')||null,th:Math.max(TH_MIN,Math.min(TH_MAX,parseInt(h.get('th')||'%(th_default)s')))};}
function setHash(st){const p=new URLSearchParams();if(st.sym)p.set('sym',st.sym);p.set('th',st.th);history.replaceState(null,'','#'+p.toString());}
let state=hashState();
function renderSymbol(){
  const d=SYM_DATA[state.sym];if(!d)return;
  document.getElementById('an-name').textContent=state.sym;
  document.getElementById('an-table').innerHTML=d.table_html;
  document.getElementById('an-box').innerHTML=d.box_html;
  document.getElementById('an-note').textContent=d.note||'';
  const thOut=document.getElementById('th-out');thOut.textContent=state.th+' pips';
  document.getElementById('th-avoid').textContent=d.curve[state.th]!==undefined?d.curve[state.th][0]+'%%':'—';
  document.getElementById('th-catch').textContent=d.curve[state.th]!==undefined?d.curve[state.th][1]+'%%':'—';
  const pts=d.curve_pts.map(p=>p[0]+','+p[1]).join(' ');
  let svg='<svg viewBox="0 0 620 190" width="100%%" height="190" preserveAspectRatio="xMidYMid meet">';
  svg+='<line x1="40" y1="160" x2="600" y2="160" stroke="#333"/>';svg+='<line x1="40" y1="20" x2="40" y2="160" stroke="#333"/>';
  for(const g of [0,50,100]){const y=160-g*1.4;svg+='<line x1="40" y1="'+y+'" x2="600" y2="'+y+'" stroke="#222"/><text x="34" y="'+(y+4)+'" fill="#777" font-size="10" text-anchor="end">'+g+'</text>';}
  if(pts){const av=d.curve_pts.map(p=>40+p[0]*(560/60)).join(' ');const ca=d.curve_pts.map(p=>(40+p[0]*(560/60))+','+(160-p[1]*1.4)).join(' ');
    svg+='<polyline points="'+ca+'" fill="none" stroke="#4CAF50" stroke-width="2"/>';}
  svg+='<text x="320" y="182" fill="#777" font-size="10" text-anchor="middle">入場門檻（pips，0–60）</text>';
  svg+='<text x="12" y="90" fill="#777" font-size="10" transform="rotate(-90 12 90)">%%</text></svg>';
  document.getElementById('an-curve').innerHTML=svg;
}
const TTB=document.createElement('div');TTB.id='tt-global';TTB.setAttribute('role','tooltip');document.body.appendChild(TTB);let TTCUR=null,ttByFocus=false;
function ttShow(el){TTB.textContent=el.dataset.tip||'';TTB.style.display='block';TTB.style.left='0px';TTB.style.top='0px';const r=el.getBoundingClientRect(),bw=TTB.offsetWidth,bh=TTB.offsetHeight;let x=Math.max(8,Math.min(r.left,innerWidth-bw-8));let y=r.bottom+8;if(y+bh>innerHeight-8)y=r.top-bh-8;TTB.style.left=x+'px';TTB.style.top=y+'px';}
function ttHide(){TTB.style.display='none';TTCUR=null;}
if(matchMedia('(hover:hover)').matches){document.addEventListener('mouseover',e=>{const t=e.target.closest('.tt');if(t){TTCUR=t;ttShow(t)}else if(TTCUR){ttHide()}});}
document.addEventListener('focusin',e=>{const t=e.target.closest('.tt');if(t){TTCUR=t;ttByFocus=true;ttShow(t)}});
document.addEventListener('focusout',()=>ttHide());
document.addEventListener('click',e=>{const t=e.target.closest('.tt');if(t){if(TTCUR===t&&TTB.style.display==='block'&&!ttByFocus){ttHide()}else{TTCUR=t;ttShow(t)}ttByFocus=false;}else if(TTCUR){ttHide()}});
document.addEventListener('keydown',e=>{if(e.key==='Escape')ttHide()});
addEventListener('scroll',()=>ttHide(),true);addEventListener('resize',()=>ttHide());
window.addEventListener('DOMContentLoaded',()=>{
  loadTheme();
  const sel=document.getElementById('sym-select');
  if(sel){
    if(state.sym&&SYM_DATA[state.sym])sel.value=state.sym;else state.sym=sel.value;
    sel.addEventListener('change',()=>{state.sym=sel.value;setHash(state);renderSymbol();});
    const rg=document.getElementById('th-slider');
    rg.value=state.th;
    rg.addEventListener('input',()=>{state.th=parseInt(rg.value);document.getElementById('th-out').textContent=state.th+' pips';});
    rg.addEventListener('change',()=>{state.th=parseInt(rg.value);setHash(state);renderSymbol();});
    renderSymbol();
  }
});
"""

# ── tooltip helper（老闆 0619：說明收 mouseover）─────────────────────
def tt(tip, label='ℹ️', cls=''):
    """自製 tooltip 觸發器：hover/tap/focus 出（共享 #tt-global bubble），唔用 title 屬性。"""
    import html as _htt
    return (f'<span class="tt {cls}" tabindex="0" role="button" aria-label="說明" '
            f'data-tip="{_htt.escape(tip, quote=True)}">{label}</span>')


# ── 數據層 ────────────────────────────────────────────────────────────
def parse_dt(s):
    s = (s or '').strip()
    if not s:
        return None
    for f in ('%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.strptime(s, f)
        except ValueError:
            pass
    return None


def load_trades(csv_path):
    """清洗照 Excel v8.5 說明 sheet：剔 balance/credit、剔未平倉、按 Close Time 排序。
    Magic=0 規則：copy-trade 數據源 Magic 全 0，照剔會清空——⑧區注明豁免。"""
    rows = list(csv.DictReader(open(csv_path, encoding='utf-8-sig')))
    trades = []
    for r in rows:
        typ = (r.get('Type') or '').strip().lower()
        if typ in ('balance', 'credit', 'deposit', 'withdrawal'):
            continue
        ct = parse_dt(r.get('Close Time'))
        if ct is None:          # 未平倉
            continue
        np_ = float(r.get('Net Profit') or 0)
        mp, mlp = float(r.get('Max Profit') or 0), abs(float(r.get('Max Loss Pips') or 0))
        # 缺數判定（OpenClaw 0235 P1-B）：MAE/MFE 全 0 而淨利為正＝數學上不可能＝源 CSV 缺欄非真 0
        mm = (mp == 0 and mlp == 0 and np_ > 0)
        trades.append({
            'open': parse_dt(r.get('Open Time')), 'close': ct, 'type': typ,
            'lots': float(r.get('Lots') or 0), 'sym': (r.get('Symbol') or '').strip(),
            'net_pips': float(r.get('Net Pips') or 0), 'np': np_,
            'mfe_$': mp, 'mfe_p': abs(float(r.get('Max Pips') or 0)),
            'mae_$': abs(float(r.get('Max Loss') or 0)), 'mae_p': mlp,
            'hours': float(r.get('Holding Time (Hours)') or 0), 'mm': mm,
        })
    trades.sort(key=lambda t: t['close'])
    return trades


def valid_mm(tr):
    """MAE/MFE 缺數筆剔除（OpenClaw 0235 P1-B：缺就係缺，唔好扮 0）。"""
    return [x for x in tr if not x['mm']]


def pct(n, d):
    return round(n / d * 100, 1) if d else None


def mart_detect(trades):
    """白皮書 v3.1 §4：基準 lot＝出現≥2次嘅最小實際 lot；每層×倍數；歸層比例。"""
    cnt = Counter(round(t['lots'], 2) for t in trades)
    base = min((l for l, c in cnt.items() if c >= 2), default=None)
    if base is None:
        base = min(cnt) if cnt else 0
    layers, uncls = defaultdict(lambda: {'n': 0, 'pl': 0.0}), 0
    for t in trades:
        ratio = t['lots'] / base if base else 0
        L = round(ratio)
        if L >= 1 and abs(ratio - L) < 0.02:
            layers[L]['n'] += 1
            layers[L]['pl'] += t['np']
        else:
            uncls += 1
    n_total = len(trades)
    ratio_ok = pct(n_total - uncls, n_total)
    maxL = max(layers) if layers else 0
    detected = maxL >= 2
    # 偵測倍數：相鄰層 lot 比值眾數（單層→None）
    step = None
    if maxL >= 2:
        lot_at = {}
        for t in trades:
            r_ = t['lots'] / base if base else 0
            L_ = round(r_)
            if L_ >= 1 and abs(r_ - L_) < 0.02 and L_ not in lot_at:
                lot_at[L_] = t['lots']
        steps = [round(lot_at[i + 1] / lot_at[i], 2) for i in range(1, maxL) if i in lot_at and i + 1 in lot_at and lot_at[i]]
        if steps:
            step = Counter(steps).most_common(1)[0][0]
    # 校準層差：實際 vs 理論（base×step^(L-1)）最大偏差
    calib = 0.0
    if step and maxL >= 2:
        for t in trades:
            r_ = t['lots'] / base if base else 0
            L_ = round(r_)
            if L_ >= 1 and abs(r_ - L_) < 0.02:
                try:
                    theo = base * (step ** (L_ - 1))
                except OverflowError:
                    continue  # step^(L-1) 超出 float 上限＝base 偵測失真，跳過該筆校準
                if theo:
                    calib = max(calib, abs(t['lots'] - theo) / theo * 100)
    return {'base': base, 'layers': dict(layers), 'uncls': uncls, 'ratio_ok': ratio_ok,
            'maxL': maxL, 'detected': detected, 'step': step, 'calib': round(calib, 1)}


def equity_maxdd(trades):
    eq = peak = dd = 0.0
    for t in trades:
        eq += t['np']
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    return dd


def pctile(vals, p):
    if not vals:
        return None
    s = sorted(vals)
    k = (len(s) - 1) * p / 100
    f, c = math.floor(k), math.ceil(k)
    return round(s[f] if f == c else s[f] + (s[c] - s[f]) * (k - f), 1)


def fmt_money(x):
    return ('-$' if x < 0 else '$') + f'{abs(x):,.2f}'


def fmt_cell(x, cls=None):
    if x is None:
        return '<td class="muted">—</td>'
    c = cls if cls else ('pos' if x > 0 else 'neg' if x < 0 else '')
    return f'<td class="{c}">{x:,.2f}</td>' if isinstance(x, float) else f'<td class="{c}">{x}</td>'


# ── 區塊生成 ──────────────────────────────────────────────────────────
def sec_hero(t, m, det):
    wins = [x for x in t if x['np'] > 0]
    losses = [x for x in t if x['np'] < 0]
    gross_w = sum(x['np'] for x in wins)
    gross_l = abs(sum(x['np'] for x in losses))
    pf = '無虧損' if gross_l == 0 and gross_w > 0 else (round(gross_w / gross_l, 2) if gross_l else '—')
    plr = round(statistics.mean([x['np'] for x in wins]) / abs(statistics.mean([x['np'] for x in losses])), 2) if wins and losses else None
    tot_pl = sum(x['np'] for x in t)
    dmin, dmax = t[0]['close'], t[-1]['close']
    badge = ('<span class="badge martin">偵測到馬丁 ×%s</span>' % det['step']) if det['detected'] else '<span class="badge none">未偵測到馬丁</span>'
    six = [('總 P&L', f'{fmt_money(tot_pl)}', 'pos' if tot_pl > 0 else 'neg'),
           ('勝率', f'{pct(len(wins), len(t))}%<span class="muted">（{len(wins)}/{len(t)}）</span>', ''),
           ('Profit Factor', f'{pf}', ''),
           ('盈虧比', f'{plr if plr else "—"}', ''),
           ('MaxDD $', f'{fmt_money(-equity_maxdd(t))}', 'neg' if equity_maxdd(t) else ''),
           ('最大 lot', f'{max(x["lots"] for x in t):.2f}', '')]
    six_html = ''.join(f'<div class="cell"><div class="k">{k}</div><div class="v {c}">{v}</div></div>' for k, v, c in six)
    vt = valid_mm(t)
    if vt:
        maep = [x['mae_p'] for x in vt]
        mfep = [x['mfe_p'] for x in vt]
        narrow = (f'<div>MAE pips 平均 <b>{round(statistics.mean(maep),1)}</b>·中位 <b>{round(statistics.median(maep),1)}</b>·P90 <b>{pctile(maep,90)}</b>'
                  f'（{fmt_money(statistics.mean([x["mae_$"] for x in vt]))}）</div>'
                  f'<div>MFE pips 平均 <b>{round(statistics.mean(mfep),1)}</b>·中位 <b>{round(statistics.median(mfep),1)}</b>·P90 <b>{pctile(mfep,90)}</b>'
                  f'（{fmt_money(statistics.mean([x["mfe_$"] for x in vt]))}）</div>')
        if len(vt) < len(t):
            narrow += (f'<div class="footnote">{tt(f"⚠ {len(t) - len(vt)} 筆 MAE/MFE 欄為 0 值（與淨利矛盾，判定缺欄）——窄帶統計剔除計算（冇數≠$0）。", "⚠", "tt-w")}</div>')
    else:
        narrow = '<div class="muted">MAE/MFE：·冇數（全數缺欄）</div>'
    # 分層摘要迷你表
    rows = ''
    lay = sorted(det['layers'].items())
    for L, d in lay:
        try:
            theo_l = det["base"] * (det["step"] or 1) ** (L - 1) if det["step"] else det["base"]
        except OverflowError:
            theo_l = None  # 理論 lot 超出 float 上限＝base/step 偵測失真，顯示—
        theo_cell = f'{theo_l:.2f}' if theo_l is not None else '<span class="muted">—</span>'
        rows += (f'<tr><td>L{L}</td><td>{theo_cell}</td>'
                 f'<td>{d["n"]}</td><td>{fmt_money(d["pl"])}</td><td>{pct(d["pl"], tot_pl) if tot_pl else "—"}%</td></tr>')
    if det['uncls']:
        rows += f'<tr><td>未分類</td><td class="muted">—</td><td>{det["uncls"]}</td><td class="muted">—</td><td class="muted">—</td></tr>'
    mini = (f'<details><summary>分層摘要（{len(lay)} 層）</summary><table><thead><tr><th>層</th><th>理論 lot</th><th>筆數</th>'
            f'<th>P&amp;L</th><th>佔 P&amp;L%</th></tr></thead><tbody>{rows}</tbody></table></details>')
    return f'''<section id="s1"><h2>① 整倉總覽 {tt('10 秒結論：賺唔賺、係唔係馬丁。圖例：P&L／勝率按平倉淨值（含 commission+swap）。')}</h2>
<div class="hero-grid"><div class="hero-left">{badge}<div class="meta"><b>{len(t)}</b> 筆交易　·　數據範圍 <b>{dmin:%Y-%m-%d} → {dmax:%Y-%m-%d}</b>（按平倉時間）</div></div>
<div class="six">{six_html}</div></div>
<div class="narrow">{narrow}</div>{mini}</section>'''


def sec_martin(det, t):
    if not det['layers']:
        return ('<section id="s2"><h2>② 馬丁偵測 '
                + tt('判定章可追溯：基準 lot 點嚟、倍數幾多。\n未有足夠數據分層——唔出膠囊與分佈表。')
                + '</h2></section>')
    bar_max = max(d['n'] for d in det['layers'].values()) or 1
    rows = ''
    for L in sorted(det['layers']):
        d = det['layers'][L]
        lots_seen = sorted({round(x['lots'], 2) for x in t if abs(x['lots'] / det['base'] - L) < 0.02}) if det['base'] else []
        lot_s = '/'.join(f'{x:.2f}' for x in lots_seen) or '—'
        w = round(d['n'] / bar_max * 100)
        rows += (f'<tr><td>L{L}</td><td>{lot_s}</td><td>{d["n"]}</td>'
                 f'<td><div class="bar-cell" style="width:{max(w,4)}%"></div></td><td>{fmt_money(d["pl"])}</td></tr>')
    uncls_row = f'<tr class="dim"><td>未分類</td><td class="muted">lot 不符倍數</td><td>{det["uncls"]}</td><td></td><td></td></tr>' if det['uncls'] else ''
    warn = '' if (det['ratio_ok'] or 0) >= 80 else f'<div class="footnote">{tt("⚠ 歸屬比例低於 80%，判定宜保守。", "⚠", "tt-w")}</div>'
    cap = f'基準 lot {det["base"]:.2f}（出現≥2次最小 lot）' + (f'，倍數 ×{det["step"]:g}' if det['step'] else '，單層無倍數')
    return f'''<section id="s2"><h2>② 馬丁偵測 {tt('判定方法：白皮書 v3.1 §4.3——校準用「出現≥2次嘅最小 lot」做基準。' + cap + '\n六步：① 剔除 balance／未平倉列 → ② 統計實際 lot 分佈 → ③ 基準 lot＝出現≥2次嘅最小 lot → ④ 每筆按 lot/基準 倍數歸層（容差 2%）→ ⑤ 相鄰層比值眾數＝偵測倍數 → ⑥ 最大層≥2 即判馬丁；未分類列於表尾。', 'ℹ️ 判定方法', 'tt-pill')}</h2>
<div class="pills">
<div class="pill"><div class="k">基準 lot</div><div class="v">{det["base"]:.2f}</div></div>
<div class="pill"><div class="k">偵測倍數</div><div class="v">{'×%g' % det["step"] if det["step"] else "—（單層）"}</div></div>
<div class="pill"><div class="k">歸層比例</div><div class="v">{det["ratio_ok"] if det["ratio_ok"] is not None else "—"}%</div></div>
<div class="pill"><div class="k">校準層差</div><div class="v">{det["calib"]}%</div></div>
</div>
<table><thead><tr><th>層</th><th>實際 lot</th><th>筆數</th><th>分佈</th><th>P&amp;L</th></tr></thead><tbody>{rows}{uncls_row}</tbody></table>{warn}</section>'''


def sym_group(trades):
    wins = [x for x in trades if x['np'] > 0]
    losses = [x for x in trades if x['np'] < 0]
    gw = sum(x['np'] for x in wins)
    gl = abs(sum(x['np'] for x in losses))
    pf = '無虧損' if gl == 0 and gw > 0 else (round(gw / gl, 2) if gl else None)
    vt = valid_mm(trades)
    return {'n': len(trades), 'wr': pct(len(wins), len(trades)) if trades else None,
            'pl': sum(x['np'] for x in trades), 'pf': pf,
            'avg_mae$': round(statistics.mean([x['mae_$'] for x in vt]), 2) if vt else None,
            'avg_mfe$': round(statistics.mean([x['mfe_$'] for x in vt]), 2) if vt else None,
            'avg_maep': round(statistics.mean([x['mae_p'] for x in vt]), 1) if vt else None,
            'avg_mfep': round(statistics.mean([x['mfe_p'] for x in vt]), 1) if vt else None,
            'max_lot': max((x['lots'] for x in trades), default=None),
            'avg_h': round(statistics.mean([x['hours'] for x in trades]), 1) if trades else None}


def sym_side_table(g, side):
    if g['n'] == 0:
        return None
    return g


def build_analyzer(t, det):
    """③ 商品分析器：預渲染全部商品，JS 切換＋61 級 slider＋hash 同步。"""
    by_sym = defaultdict(list)
    for x in t:
        by_sym[x['sym']].append(x)
    order = sorted(by_sym, key=lambda s: -sum(x['np'] for x in by_sym[s]))
    sym_data, default_sym = {}, order[0] if order else ''
    for s in order:
        tr = by_sym[s]
        buys = [x for x in tr if x['type'] == 'buy']
        sells = [x for x in tr if x['type'] == 'sell']
        gb, gs = sym_group(buys), sym_group(sells)
        # a) 指標×BUY/SELL 對照（BUY 左綠 SELL 右紅）
        metrics = [('筆數', lambda g: g['n']), ('勝率', lambda g: f'{g["wr"]}%' if g['wr'] is not None else '—'),
                   ('P&L', lambda g: fmt_money(g['pl'])), ('avg MAE $', lambda g: f'{g["avg_mae$"]:.2f}' if g['avg_mae$'] is not None else '—'),
                   ('avg MFE $', lambda g: f'{g["avg_mfe$"]:.2f}' if g['avg_mfe$'] is not None else '—'),
                   ('avg MAE pips', lambda g: f'{g["avg_maep"]:.1f}' if g['avg_maep'] is not None else '—'),
                   ('avg MFE pips', lambda g: f'{g["avg_mfep"]:.1f}' if g['avg_mfep'] is not None else '—'),
                   ('PF', lambda g: str(g['pf']) if g['pf'] is not None else '—'),
                   ('平均持倉 h', lambda g: f'{g["avg_h"]:.1f}' if g['avg_h'] is not None else '—'),
                   ('最大 lot', lambda g: f'{g["max_lot"]:.2f}' if g['max_lot'] is not None else '—')]
        rows = ''.join(f'<tr><td>{k}</td><td class="{"pos" if isinstance(vb := fn(gb), float) or isinstance(vb, int) and not isinstance(vb, bool) and k == "P&L" and vb > 0 else ""}">{vb if vb is not None else "—"}</td>'
                       f'<td>{vs if (vs := fn(gs)) is not None else "—"}</td></tr>' for k, fn in metrics)
        # 單方向提示
        note = ''
        if gb['n'] == 0:
            note = '此商品無 BUY 記錄'
        elif gs['n'] == 0:
            note = '此商品無 SELL 記錄'
        # c) 止賺止蝕參考（層×方向；n<5 灰化）
        crow = ''
        for side_name, side_tr in (('BUY', buys), ('SELL', sells)):
            if not side_tr:
                crow += f'<tr class="dim"><td>{side_name}</td><td class="muted">無記錄</td><td colspan="4" class="muted">—</td></tr>'
                continue
            vst = valid_mm(side_tr)
            dimc = ' class="dim"' if len(side_tr) < 5 else ''
            sm = ' title="樣本少 n=%d"' % len(side_tr) if len(side_tr) < 5 else ''
            if vst:
                maep = [x['mae_p'] for x in vst]
                mfep = [x['mfe_p'] for x in vst]
                sl_ref = f'<td class="neg">P90 {pctile(maep, 90)} / P95 {pctile(maep, 95)}</td>'
                tp_ref = f'<td class="pos">P50 {pctile(mfep, 50)} / P75 {pctile(mfep, 75)} / P90 {pctile(mfep, 90)}</td>'
            else:
                sl_ref = '<td class="muted">缺數</td>'
                tp_ref = '<td class="muted">缺數</td>'
            crow += (f'<tr{dimc}><td{sm}>{side_name}</td><td>{len(side_tr)}</td>'
                     f'{sl_ref}{tp_ref}'
                     f'<td>{round(statistics.mean([x["hours"] for x in side_tr]), 1):.1f}</td></tr>')
        # 61 級效益曲線（v8.4 延遲入場）；缺 MAE/MFE 筆剔除分母（P1-B）
        curve = {}
        vtr = valid_mm(tr)
        loss_tr = [x for x in vtr if x['np'] < 0]
        for th in range(0, 61):
            avoid = pct(sum(1 for x in loss_tr if x['mae_p'] >= th), len(loss_tr)) if loss_tr else None
            catch = pct(sum(1 for x in vtr if x['mfe_p'] >= th), len(vtr)) if vtr else None
            curve[th] = (avoid if avoid is not None else 0, catch if catch is not None else 0)
        curve_pts = [[th, curve[th][1]] for th in range(0, 61, 2)]
        box_html = (f'<table><thead><tr><th>方向</th><th>筆數</th><th>止蝕參考（MAE P90/P95 pips）</th>'
                    f'<th>止賺參考（MFE P50/75/90 pips）</th><th>平均持倉 h</th></tr></thead><tbody>{crow}</tbody></table>'
                    f'<div class="footnote">{tt("樣本 n&lt;5 嘅方向行已灰化，參考值僅供示意。")}</div>')
        table_html = (f'<table class="buysell"><thead><tr><th>指標</th>'
                      f'<th><span class="buy-h"></span>BUY</th><th><span class="sell-h"></span>SELL</th></tr></thead>'
                      f'<tbody>{rows}</tbody></table>'
                      + (f'<div class="footnote">{tt("⚠ " + note, "⚠", "tt-w")}</div>' if note else ''))
        sym_data[s] = {'table_html': table_html, 'box_html': box_html,
                       'note': f'清洗後 {len(tr)} 筆' if tr else '零交易',
                       'curve': {str(k): v for k, v in curve.items()}, 'curve_pts': curve_pts}
    options = ''.join(f'<option value="{s}">{s}</option>' for s in order)
    n_mm = sum(1 for x in t if x['mm'])
    mm_tip = (f'⚠ {n_mm} 筆 MAE/MFE 欄為 0 值（與淨利矛盾，判定缺欄）——相關商品 avg 值顯示「—」、統計分母剔除（冇數≠$0）。') if n_mm else ''
    return f'''<section id="s3"><h2>③ 商品分析器 {tt('單商品手術台：預設總 P&L 最高商品。BUY 綠左／SELL 紅右。門檻 slider＝v8.4 入場效益（61 級）web 升級位。')}{f' {tt(mm_tip, "⚠", "tt-w")}' if n_mm else ''}</h2>
<div class="sel-bar"><label>商品</label><select id="sym-select">{options}</select>
<label>入場門檻</label><div class="slider-row" style="margin:0;flex:1"><input type="range" id="th-slider" min="0" max="60" step="1" value="20"><span class="slider-val" id="th-out">20 pips</span></div></div>
<div id="an-note" class="footnote"></div>
<div class="two"><div><h3 style="color:var(--acc);font-size:.95em;margin-bottom:6px">指標 × BUY/SELL（<span id="an-name"></span>）</h3><div id="an-table"></div></div>
<div><h3 style="color:var(--acc);font-size:.95em;margin-bottom:6px">止賺止蝕參考（層×方向）</h3><div id="an-box"></div></div></div>
<h3 style="color:var(--acc);font-size:.95em;margin:14px 0 6px">61 級入場效益曲線 {tt('綠線＝可捕捉盈利%（MFE≥門檻佔比）；無虧損單時避開虧損% 不出線。門檻與商品選擇寫入 URL hash，可分享。')}</h3>
<div class="slider-row"><span class="muted" style="font-size:.82em">可避開虧損 <b id="th-avoid" style="color:var(--red)">—</b>　可捕捉盈利 <b id="th-catch" style="color:var(--grn)">—</b>（門檻命中佔比）</span></div>
<div class="svgbox" id="an-curve"></div></section>''', sym_data, default_sym


def sec_dir_table(t):
    """④ 商品方向總表：全商品×BUY/SELL 按勝率排；同商品兩行一組。"""
    by_sd = defaultdict(list)
    for x in t:
        by_sd[(x['sym'], x['type'])].append(x)
    syms = sorted({k[0] for k in by_sd})
    entries = []
    for s in syms:
        for side in ('buy', 'sell'):
            if (s, side) in by_sd:
                g = sym_group(by_sd[(s, side)])
                entries.append((s, side, g))
    entries.sort(key=lambda e: (-(e[2]['wr'] or 0), -e[2]['pl']))
    rows = ''
    for s, side, g in entries:
        deep = sum(1 for x in t if x['sym'] == s and x['type'] == side and x['lots'] > max({round(y['lots'], 2) for y in t}) * 0.999)
        l5 = ''
        rows += (f'<tr><td>{s}</td><td><span class="{"buy-h" if side == "buy" else "sell-h"}"></span>{side.upper()}</td>'
                 f'<td>{g["n"]}</td><td>{g["wr"] if g["wr"] is not None else "—"}%</td>'
                 f'<td class="{"pos" if g["pl"] > 0 else "neg"}">{fmt_money(g["pl"])}</td>'
                 f'<td>{format(g["avg_mae$"], ".2f") if g["avg_mae$"] is not None else "—"}</td>'
                 f'<td>{format(g["avg_mfe$"], ".2f") if g["avg_mfe$"] is not None else "—"}</td>'
                 f'<td>{format(g["avg_maep"], ".1f") if g["avg_maep"] is not None else "—"}</td>'
                 f'<td>{format(g["avg_mfep"], ".1f") if g["avg_mfep"] is not None else "—"}</td>'
                 f'<td>{g["max_lot"]:.2f}</td><td class="muted">—</td></tr>')
    return f'''<section id="s4"><h2>④ 商品方向總表 {tt('全場商品×方向成績表，按勝率排序；L5+ 深層馬丁暴露喺深層馬丁帳戶先會有數（本訊號見 ② 區）。零交易子集唔出行（軍規 A④）。')}</h2>
<table><thead><tr><th>商品</th><th>方向</th><th>筆數</th><th>勝率</th><th>P&amp;L</th><th>avg MAE $</th><th>avg MFE $</th><th>avg MAE p</th><th>avg MFE p</th><th>max lot</th><th>L5+ 筆數</th></tr></thead>
<tbody>{rows}</tbody></table></section>'''


def heat_color(v, vmax):
    if v is None or vmax == 0:
        return 'var(--card2)', 'var(--text2)'
    a = min(abs(v) / vmax, 1) * 0.72 + 0.08
    if v > 0:
        return f'rgba(76,175,80,{a:.2f})', 'var(--text)'
    return f'rgba(255,87,34,{a:.2f})', 'var(--text)'


def sec_pivot(t):
    """⑤ 月度樞紐：年×月熱力（按平倉月）；單月→bar 降級；「冇數·」≠ $0。"""
    by_ym = defaultdict(float)
    for x in t:
        by_ym[(x['close'].year, x['close'].month)] += x['np']
    years = sorted({k[0] for k in by_ym})
    months_covered = {m for (_, m) in by_ym}
    if len(years) == 1 and len(by_ym) == 1:
        (yy, mm), val = next(iter(by_ym.items()))
        vmax = abs(val) or 1
        bg, _ = heat_color(val, vmax)
        return f'''<section id="s5"><h2>⑤ 月度樞紐 {tt('年×月 P&L（按平倉月）。圖例：綠贏紅蝕，深淺按 |值| 歸一化。\n「·」＝未覆蓋月份（冇數），唔係 $0。')}</h2>
<div class="footnote">{tt('⚠ 數據只覆蓋單一月份——熱力表降級做單月 bar。', '⚠', 'tt-w')}</div>
<div style="display:flex;align-items:center;gap:14px;margin-top:10px"><b>{yy}-{mm:02d}</b>
<div style="flex:1;background:var(--card2);border-radius:6px;padding:4px"><div style="width:100%;background:{bg};border-radius:4px;padding:6px 10px;font-weight:700">{fmt_money(val)}</div></div></div></section>'''
    vmax = max((abs(v) for v in by_ym.values()), default=1)
    head = '<div class="heat" style="grid-template-columns:64px repeat(13,1fr)">'
    cells = ['<div class="lab"></div>'] + [f'<div class="lab" style="justify-content:center">{m}</div>' for m in range(1, 13)] + ['<div class="lab" style="justify-content:center">全年</div>']
    for y in years:
        cells.append(f'<div class="lab">{y}</div>')
        ytot = 0.0
        for m in range(1, 13):
            if (y, m) in by_ym:
                v = by_ym[(y, m)]
                ytot += v
                bg, _ = heat_color(v, vmax)
                cells.append(f'<div class="c" style="background:{bg}" title="{y}-{m:02d}: {fmt_money(v)}">{v / 1000:.1f}k</div>')
            else:
                cells.append(f'<div class="c na tt" tabindex="0" role="button" aria-label="說明" data-tip="未覆蓋月份——冇數，唔係 $0">·</div>')
        bg, _ = heat_color(ytot, vmax)
        cells.append(f'<div class="c" style="background:{bg}">{fmt_money(ytot)}</div>')
    grid = head + ''.join(cells) + '</div>'
    return f'''<section id="s5"><h2>⑤ 月度樞紐 {tt('年×月 P&L 熱力表（按平倉月）＋全年合計。圖例：綠贏紅蝕，深淺按該表 max|值| 歸一化。\n「·」＝未覆蓋（冇數≠$0），hover 格去睇。')}</h2>
{grid}</section>'''


def scatter_svg(tr, side, w=300, h=230):
    if not tr:
        return None
    pts = [(x['mae_p'], x['mfe_p'], x['np']) for x in tr]
    xmax = max(max(p[0] for p in pts), 10) * 1.08
    ymax = max(max(p[1] for p in pts), 10) * 1.08
    ml, mr, mt, mb = 40, 10, 10, 30
    pw, ph = w - ml - mr, h - mt - mb
    P = [(ml + p[0] / xmax * pw, mt + (1 - p[1] / ymax) * ph, p[2]) for p in pts]
    diag_y = lambda x_val: mt + (1 - (x_val / ymax if xmax else 0)) * ph
    diag = (ml, mt + ph, ml + pw, diag_y(xmax))
    s = f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}">'
    s += f'<rect x="{ml}" y="{mt}" width="{pw}" height="{ph}" fill="#0d1120" stroke="#222"/>'
    for gv in range(0, int(xmax) + 1, max(int(xmax // 4), 1)):
        gx = ml + gv / xmax * pw
        s += f'<line x1="{gx:.0f}" y1="{mt}" x2="{gx:.0f}" y2="{mt + ph}" stroke="#1c2333"/><text x="{gx:.0f}" y="{mt + ph + 14}" fill="#777" font-size="9" text-anchor="middle">{gv}</text>'
    for gv in range(0, int(ymax) + 1, max(int(ymax // 4), 1)):
        gy = mt + (1 - gv / ymax) * ph
        s += f'<line x1="{ml}" y1="{gy:.0f}" x2="{ml + pw}" y2="{gy:.0f}" stroke="#1c2333"/><text x="{ml - 5}" y="{gy + 3:.0f}" fill="#777" font-size="9" text-anchor="end">{gv}</text>'
    s += f'<line x1="{diag[0]}" y1="{diag[1]}" x2="{diag[2]}" y2="{diag[3]}" class="gline"/>'
    for (px, py, np_) in P:
        s += f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3.2" fill="{"#4CAF50" if np_ > 0 else "#FF5722"}" fill-opacity=".75"/>'
    s += f'<text x="{ml + pw / 2}" y="{h - 4}" fill="#777" font-size="10" text-anchor="middle">MAE（pips）</text>'
    s += f'<text x="12" y="{mt + ph / 2}" fill="#777" font-size="10" transform="rotate(-90 12 {mt + ph / 2})">MFE（pips）</text></svg>'
    return s


def sec_scatter(t):
    """⑥ MAE/MFE 散點：BUY/SELL 兩幅 SVG＋y=x 對角線；缺 MAE/MFE 筆唔入散點（P1-B）；點<10 改點表。"""
    import html as _h
    panels = []
    n_mm = sum(1 for x in t if x['mm'])
    for side, label in (('buy', 'BUY'), ('sell', 'SELL')):
        tr = [x for x in t if x['type'] == side]
        if not tr:
            panels.append(f'<div class="svgbox"><b style="color:var(--acc)">{label}</b><div class="footnote">無 {label} 記錄</div></div>')
            continue
        vtr = valid_mm(tr)
        if not vtr:
            panels.append(f'<div class="svgbox"><b style="color:var(--acc)">{label}</b><div class="footnote">{tt(f"⚠ {len(tr)} 筆全部缺 MAE/MFE 欄——無有效點可繪（冇數≠$0）。", "⚠", "tt-w")}</div></div>')
            continue
        if len(vtr) < 10:
            rows = ''.join(
                (f'<tr><td>{x["mae_p"]:.1f}</td><td>{x["mfe_p"]:.1f}</td><td class="{"pos" if x["np"] > 0 else "neg"}">{fmt_money(x["np"])}</td></tr>'
                 if not x['mm'] else
                 f'<tr><td class="muted" colspan="2">{tt("冇數——MAE/MFE 欄缺（0 值與淨利矛盾），唔係 $0。", "·冇數（缺欄）")}</td><td class="{"pos" if x["np"] > 0 else "neg"}">{fmt_money(x["np"])}</td></tr>')
                for x in tr)
            panels.append(f'<div class="svgbox"><b style="color:var(--acc)">{label}</b><div class="footnote">{tt(f"⚠ 有效 MAE/MFE {len(vtr)} 筆（<10）——散點改列點表。", "⚠", "tt-w")}</div><table><thead><tr><th>MAE p</th><th>MFE p</th><th>淨利</th></tr></thead><tbody>{rows}</tbody></table></div>')
            continue
        svg = scatter_svg(vtr, side)
        online = pct(sum(1 for x in vtr if x['mfe_p'] >= x['mae_p']), len(vtr))
        drop = f'（剔除 {len(tr) - len(vtr)} 筆缺數）' if len(tr) > len(vtr) else ''
        panels.append(f'<div class="svgbox"><b style="color:var(--acc)">{label}</b>{svg}<div class="cap">對角虛線＝MFE=MAE（線上＝入場後唔使挨逆風）；線上比例 {online}%{drop}；綠點贏紅點蝕</div></div>')
    quad = tt('入場質素四象限：MFE＝入場後最大有利偏移、MAE＝最大不利偏移（pips，由入場價起算）。y=x 對角線上＝好單（MFE≥MAE，入場後唔使挨逆風）。綠點贏紅點蝕。')
    mm_note = (f' {tt(f"⚠ {n_mm} 筆 MAE/MFE 欄為 0 值（與淨利矛盾，判定缺欄）——相關點位剔除散點（冇數≠$0）。", "⚠", "tt-w")}') if n_mm else ''
    return f'''<section id="s6"><h2>⑥ MAE/MFE 散點{mm_note}{quad}</h2>
<div class="two">{''.join(panels)}</div></section>'''


def sec_time(t):
    """⑦ 時間維度＋明細：7×24 heatmap（按平倉時間）＋累計線＋明細表。"""
    import html as _h
    hm = defaultdict(float)
    for x in t:
        hm[(x['close'].weekday(), x['close'].hour)] += x['np']
    vmax = max((abs(v) for v in hm.values()), default=1)
    days = ['一', '二', '三', '四', '五', '六', '日']
    # 行列合計色條
    col_tot = [sum(hm.get((d, h), 0.0) for d in range(7)) for h in range(24)]
    row_tot = [sum(hm.get((d, h), 0.0) for h in range(24)) for d in range(7)]
    g = ['<div class="heat hm-wrap" style="grid-template-columns:36px repeat(24,minmax(22px,1fr));min-width:720px">']
    g.append('<div class="lab"></div>' + ''.join(f'<div class="lab" style="justify-content:center">{h}</div>' for h in range(24)))
    for d in range(7):
        g.append(f'<div class="lab">{days[d]}</div>')
        for h in range(24):
            v = hm.get((d, h))
            if v is None:
                g.append(f'<div class="c na tt" tabindex="0" role="button" aria-label="說明" data-tip="冇數——該時段無平倉交易，唔係 $0">·</div>')
            else:
                bg, _ = heat_color(v, vmax)
                g.append(f'<div class="c" style="background:{bg}" title="週{days[d]} {h:02d}:00–{h + 1:02d}:00 {fmt_money(v)}">{"" if abs(v) < 0.005 else f"{v:,.0f}"}</div>')
    g.append('</div>')
    heatmap = ''.join(g)
    # 累計線（按平倉）
    cum, eq = [], 0.0
    for x in t:
        eq += x['np']
        cum.append(eq)
    lo, hi = min(cum + [0]), max(cum + [0])
    W, H, ml, mr, mt, mb = 620, 150, 46, 12, 8, 24
    pw, ph = W - ml - mr, H - mt - mb
    rng = (hi - lo) or 1
    P = [(ml + i / max(len(cum) - 1, 1) * pw, mt + (1 - (v - lo) / rng) * ph) for i, v in enumerate(cum)]
    s = f'<svg viewBox="0 0 {W} {H}" width="100%" height="{H}">'
    s += f'<line x1="{ml}" y1="{mt + (1 - (0 - lo) / rng) * ph:.0f}" x2="{ml + pw}" y2="{mt + (1 - (0 - lo) / rng) * ph:.0f}" stroke="#333" stroke-dasharray="3 3"/>'
    s += f'<polyline points="{" ".join(f"{px:.1f},{py:.1f}" for px, py in P)}" fill="none" stroke="#64b5f6" stroke-width="1.8"/>'
    s += f'<text x="{ml - 6}" y="{mt + 4}" fill="#777" font-size="9" text-anchor="end">{hi:,.0f}</text>'
    s += f'<text x="{ml - 6}" y="{mt + ph}" fill="#777" font-size="9" text-anchor="end">{lo:,.0f}</text>'
    s += f'<text x="{ml + pw / 2}" y="{H - 4}" fill="#777" font-size="10" text-anchor="middle">逐筆平倉（{t[0]["close"]:%m-%d} → {t[-1]["close"]:%m-%d}）</text></svg>'
    # 明細（最近 50 筆）
    rows = ''
    for x in t[-50:][::-1]:
        mae_cell = f'{x["mae_$"]:,.2f}' if not x['mm'] else tt("冇數——MAE/MFE 欄缺（0 值與淨利矛盾），唔係 $0。", "·冇數")
        rows += (f'<tr><td>{x["close"]:%m-%d %H:%M}</td><td>{_h.escape(x["sym"])}</td>'
                 f'<td><span class="{"buy-h" if x["type"] == "buy" else "sell-h"}"></span>{x["type"].upper()}</td>'
                 f'<td>{x["lots"]:.2f}</td><td class="{"pos" if x["np"] > 0 else "neg"}">{fmt_money(x["np"])}</td>'
                 f'<td class="neg">{mae_cell}</td></tr>')
    return f'''<section id="s7"><h2>⑦ 時間維度＋明細 {tt('星期×小時 P&L（格色雙向 heat，hover 格去睇精確值；「·」＝冇數，符號本身 hover 也有解釋）＋累計 P&L 走勢＋最近 50 筆明細。時間均按平倉時間。')}</h2>
<h3 style="color:var(--acc);font-size:.95em;margin:8px 0 6px">星期 × 小時 heatmap</h3>{''.join(g)}
<h3 style="color:var(--acc);font-size:.95em;margin:14px 0 6px">累計 P&amp;L（Growth）</h3><div class="svgbox">{s}</div>
<h3 style="color:var(--acc);font-size:.95em;margin:14px 0 6px">明細（最近 {min(len(t), 50)} 筆／共 {len(t)} 筆）</h3>
<table><thead><tr><th>平倉時間</th><th>商品</th><th>方向</th><th>lots</th><th>淨利</th><th>MAE $</th></tr></thead><tbody>{rows}</tbody></table>
<details><summary>完整欄位明細（RawData 33 欄版本）</summary><div class="footnote">CSV 源 19 欄（forex-forest 導出）；Excel RawData 33 欄其餘欄位由 OpenClaw 數據 lane 補齊後，重跑本生成器自動帶出。</div></details></section>'''


def sec_guide():
    return '''<section id="s8"><h2>⑧ 使用說明</h2><div class="legend">術語、清洗規則、顏色圖例——Excel「說明／匯入說明」兩 sheet 嘅 web 化。</div>
<details><summary>展開說明</summary><dl class="guide">
<dt>勝率</dt><dd>Net Profit &gt; 0 嘅交易佔比（含 commission＋swap 後淨值）。</dd>
<dt>盈虧比</dt><dd>平均贏利 ÷ |平均虧損|。</dd>
<dt>Profit Factor</dt><dd>總盈利 ÷ |總虧損|；無虧損單時顯示「無虧損」（唔係 ∞）。</dd>
<dt>MAE / MFE</dt><dd>入場後最大不利／有利偏移，由入場價起算，pips 為主、$ 為輔。</dd>
<dt>Growth／MaxDD</dt><dd>按平倉時間逐筆累計淨利；MaxDD＝峰值回撤最大深度（$）。</dd>
<dt>馬丁偵測</dt><dd>白皮書 v3.1 §4：基準 lot＝出現≥2次嘅最小實際 lot；每筆按倍數歸層；最大層≥2 判馬丁。</dd>
<dt>清洗規則</dt><dd>剔 balance/credit、剔未平倉、按 Close Time 排序。本數據源（forex-forest copy signal）Magic 全 0，「剔 Magic=0」規則豁免並在此注明。</dd>
<dt>顏色圖例</dt><dd>綠＝贏/BUY、紅＝蝕/SELL、金＝強調、藍＝互動；熱力深淺按 |值| 歸一化；「·」＝冇數（≠$0）。</dd>
<dt>數據上限</dt><dd>20,000 筆（Excel v8.5 同款上限）。</dd>
<dt>互動分享</dt><dd>③ 區商品／門檻選擇寫入 URL hash（#sym=…&amp;th=…），可分享可返後。</dd>
</dl></details></section>'''


TOC = '''<nav class="toc"><h3>目錄</h3>
<a href="#s1">① 整倉總覽</a><a href="#s2">② 馬丁偵測</a><a href="#s3">③ 商品分析器</a>
<a href="#s4">④ 商品方向總表</a><a href="#s5">⑤ 月度樞紐</a><a href="#s6">⑥ MAE/MFE 散點</a>
<a href="#s7">⑦ 時間維度＋明細</a><a href="#s8">⑧ 使用說明</a></nav>'''


def build_page(signal_id, csv_path, force=False):
    trades = load_trades(csv_path)
    if not trades:
        raise SystemExit('清洗後零交易——照規則①應出中央卡；樣本頁唔適用，退出')
    det = mart_detect(trades)
    s3, sym_data, default_sym = build_analyzer(trades, det)
    n_raw = len(list(csv.DictReader(open(csv_path, encoding='utf-8-sig'))))
    banner = (f'<div class="banner">⚠ 樣本頁：清洗後 {len(trades)} 筆（CSV 原始 {n_raw} 行）；'
              f'CSV 33 欄補齊前，部分指標按降級軍規處理（pips 主 $ 輔）。生成於 {datetime.now(HKT):%Y-%m-%d %H:%M} HKT。</div>')
    sym_json = json.dumps(sym_data, ensure_ascii=False).replace('</', '<\\/')
    js_block = (JS % {'sym_data': sym_json, 'th_default': '20'})
    html = f'''<!DOCTYPE html>
<html lang="zh-Hant" data-theme="dark">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Martin v4 · Signal {signal_id} · TSA</title>
<link rel="stylesheet" href="../sidebar.css">
<style>{CSS}</style>
</head>
<body>
<div class="layout">
{TOC}
<main>
<header class="top"><div><h1>Martin v4 分析 · Signal {signal_id} {tt('照老闆 Excel v8.5 八區動線重建（Template B）· CSV fetch 架構保留＋全數據預渲染底')}</h1></div>
<button id="themeToggle" onclick="toggleTheme()">☀️</button></header>
{banner}
{sec_hero(trades, None, det)}
{sec_martin(det, trades)}
{s3}
{sec_dir_table(trades)}
{sec_pivot(trades)}
{sec_scatter(trades)}
{sec_time(trades)}
{sec_guide()}
<div class="footnote" style="text-align:center">TSA · Template B v1（rebuild_martin_v4.py）· 數據源 docs/downloads/forex-forest-signals-page-{signal_id}.csv</div>
</main>
</div>
<script src="../sidebar.js"></script>
<script>{js_block}</script>
</body>
</html>'''
    out = REPORTS / f'martin_v4_{signal_id}.html'
    if out.exists() and not force:
        old = hashlib.md5(out.read_bytes()).hexdigest()
        new = hashlib.md5(html.encode()).hexdigest()
        if old == new:
            print(f'[skip] {out.name} 內容無變化')
            return out
    out.write_text(html, encoding='utf-8')
    print(f'[write] {out} ({len(html.encode("utf-8")):,} bytes / {len(html):,} chars, {len(trades)} trades, layers={sorted(det["layers"])}, detected={det["detected"]})')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--signal', required=True)
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    csv_path = DOWNLOADS / f'forex-forest-signals-page-{a.signal}.csv'
    if not csv_path.exists():
        raise SystemExit(f'CSV 缺：{csv_path}')
    build_page(a.signal, csv_path, a.force)


if __name__ == '__main__':
    main()
