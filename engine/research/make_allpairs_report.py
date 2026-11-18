#!/usr/bin/env python3
"""Render docs/admin/ccy_allpairs_report.html from /tmp/allpairs2.json.

Self-contained HTML: test ledger table + per-symbol BUY/SELL performance table.
"""
import json, math, os, sys, datetime

SRC = '/tmp/allpairs2.json'
OUT = '/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/ccy_allpairs_report.html'

TESTS = [
    # (組別, 訊號, 數據, 樣本, 平均R, t值, 勝率, 判定)
    ("A 純 power 判方向", "diff 水平（快−慢）D1", "D1 8年 12pair", "22,678", None, None, "50.5%", "❌ 掟毫子"),
    ("A 純 power 判方向", "diff 水平（快−慢）H4", "H4 16.9年 4pair", "53,136", None, None, "53.3%", "⚠️ 逐年漂移"),
    ("A 純 power 判方向", "diff 斜率 5/10/20 日", "D1 8年", "22,639–22,759", None, None, "50.1–50.3%", "❌"),
    ("A 純 power 判方向", "斜率加門檻", "D1", "174–1,896", None, None, "47.1–49.6%", "❌ 越大越差"),
    ("A 純 power 判方向", "diff 穿零 cross", "D1 8年", "4,443", None, None, "49.9%", "❌"),
    ("A 純 power 判方向", "diff 穿零 cross", "H1 16月", "10,634", None, None, "49.6%", "❌"),
    ("A 純 power 判方向", "diff 穿零 cross", "H4 16月", "2,787", None, None, "49.5%", "❌"),
    ("A 純 power 判方向", "diff 穿 5/10/20 MA", "D1", "970–2,086", None, None, "49.5–50.2%", "❌"),
    ("A 純 power 判方向", "Z-score 距 60 日均", "D1 12pair", "3,812", None, None, "50.2%", "❌"),
    ("A 純 power 判方向", "排行輪動（多3空3）", "D1 8年", "—", None, None, "47.0%", "❌ 負期望"),
    ("A 純 power 判方向", "|diff| 門檻 0 / ≥2.5 / ≥3.0", "D1", "—", None, None, "50.2 / 48.7 / 46.0%", "❌ 越大越差"),
    ("B 技術指標", "MACD 同號", "D1", "—", None, None, "51.5%", "⚠️ 邊緣"),
    ("B 技術指標", "STC 同號", "D1", "—", None, None, "51.6%", "⚠️ 邊緣"),
    ("B 技術指標", "MACD 單獨", "D1", "—", None, None, "48.9%", "❌ 負期望"),
    ("B 技術指標", "STC 單獨", "D1", "—", None, None, "48.9%", "❌ 負期望"),
    ("B 技術指標", "diff + MACD 反號", "D1", "—", None, None, "58.5%（t=19.99）", "❌ 2024–25 跌回 49–50%"),
    ("B 技術指標", "三者同向 / 三者＋均線排列", "D1", "—", None, None, "51.2% / 51.5%", "❌"),
    ("C 拔河／削頭皮", "正拔河不加倉", "—", "54,176", "+0.093R", None, "—", "❌ 靠加倉攤平"),
    ("C 拔河／削頭皮", "逆勢加 1 次 / 加 2 次", "—", "—", "+0.158R / +0.191R", None, "—", "❌ 尾部風險"),
    ("C 拔河／削頭皮", "反拔河逆加 2 次", "—", "13,985", "+0.315R", None, "—", "❌ 非 alpha"),
    ("D Fib 支持阻力", "全部 Fib 觸及（原始版）", "H4 4pair", "3,004", "−0.542R", "−30.99", "18.2%", "❌ 已撤回：選擇偏差"),
    ("D Fib 支持阻力", "全部 Fib 觸及（修正無偏差）", "H4 4pair", "17,355", "+0.012R", "+1.18", "38.3%", "❌ 零 edge"),
    ("D Fib 支持阻力", "修正版 ＋ 快慢 power 同向", "H4 4pair", "5,061", "+0.188R", "+9.98", "44.7%", "⚠️ 係 power 帶嚟，唔關 Fib"),
    ("D Fib 支持阻力", "對照：同形態但唔喺 Fib 位", "H4 4pair", "9,456", "+0.006R", "—", "—", "❌ Fib 位無額外作用"),
    ("E 假突破 fade（有效方向）", "無 power 過濾", "H4 4pair 16.9年", "9,287", "+0.029R", "+2.15", "39.7%", "❌ 等於冇 edge"),
    ("E 假突破 fade（有效方向）", "只快 power 同向", "H4 4pair", "3,377", "+0.204R", "+8.86", "45.9%", "⚠️ 有 edge"),
    ("E 假突破 fade（有效方向）", "只慢 power 同向", "H4 4pair", "3,511", "+0.112R", "+5.07", "42.1%", "⚠️ 弱"),
    ("E 假突破 fade（有效方向）", "快＋慢都同向", "H4 4pair", "1,698", "+0.272R", "+8.27", "47.3%", "✅ 最強"),
    ("E 假突破 fade（有效方向）", "power 反向（反證）", "H4 4pair", "—", "−0.086R", "−4.48", "35.7%", "✅ 反向確認 edge"),
]


def esc(s):
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def bar(v, lo=-0.3, hi=0.4):
    pct = max(0, min(100, (v - lo) / (hi - lo) * 100))
    cls = 'pos' if v > 0.05 else ('neg' if v < -0.05 else 'zero')
    return '<div class="bw"><div class="bar %s" style="width:%.1f%%"></div></div>' % (cls, pct)


def main():
    d = json.load(open(SRC))
    rows = d['rows']; meta = d['meta']
    for r in rows:
        r['n'] = int(r['n'])
        for k in ('avg', 't', 'wr'):
            r[k] = float(r[k])

    def get(sym, side, tag):
        for r in rows:
            if r['sym'] == sym and r['side'] == side and r['tag'] == tag:
                return r
        return None

    def tot(tag, syms, side=None):
        sub = [r for r in rows if r['tag'] == tag and r['sym'] in syms and (side is None or r['side'] == side)]
        n = sum(r['n'] for r in sub)
        if not n:
            return None
        m = sum(r['avg'] * r['n'] for r in sub) / n
        var = 0.0
        for r in sub:
            sd = abs(r['avg'] / (r['t'] / math.sqrt(r['n']))) if r['t'] else 0
            var += r['n'] * (sd ** 2 + (r['avg'] - m) ** 2)
        sd = math.sqrt(var / n)
        return dict(n=n, avg=m, t=(m / (sd / math.sqrt(n)) if sd else 0))

    long_syms = [s for s in meta if float(meta[s]['years']) >= 10]
    short_syms = [s for s in meta if float(meta[s]['years']) < 10]
    all_syms = list(meta)

    # ---- summary cards ----
    def card(label, x, note=''):
        if not x:
            return ''
        c = 'g' if x['avg'] > 0.05 else ('r' if x['avg'] < -0.05 else 'y')
        return ('<div class="kpi"><div class="lbl">%s</div><div class="val %s">%+.3f R</div>'
                '<div class="sub">n=%s ｜ t=%+.2f%s</div></div>'
                % (label, c, x['avg'], f"{x['n']:,}", x['t'], note))

    k_long_h4q = tot('h4q', set(long_syms))
    k_long_all = tot('all', set(long_syms))
    k_short_h4q = tot('h4q', set(short_syms))
    k_all_h4q = tot('h4q', set(all_syms))

    # ---- test ledger ----
    trows = []
    for grp, sig, data, n, avg, t, wr, verdict in TESTS:
        cls = 'v-bad' if verdict.startswith('❌') else ('v-mid' if verdict.startswith('⚠') else 'v-ok')
        trows.append('<tr><td class="dim">%s</td><td>%s</td><td class="dim">%s</td><td class="num">%s</td>'
                     '<td class="num">%s</td><td class="num">%s</td><td class="num">%s</td>'
                     '<td class="%s">%s</td></tr>'
                     % (esc(grp), esc(sig), esc(data), n, avg or '—', t or '—', wr,
                        cls, esc(verdict)))

    # ---- per-symbol table ----
    srows = []
    for s in sorted(meta, key=lambda x: -float(meta[x]['years'])):
        yrs = float(meta[s]['years'])
        depth = 'v-ok' if yrs >= 10 else ('v-mid' if yrs >= 3 else 'v-bad')
        for side in ('BUY', 'SELL'):
            a = get(s, side, 'all'); h = get(s, side, 'h4q'); b = get(s, side, 'both')
            def cell(r):
                if not r or r['n'] < 10:
                    return '<td class="num dim">樣本不足</td><td></td><td></td><td></td>'
                cls = 'good' if (r['avg'] > 0.10 and r['t'] > 2) else ('bad' if r['avg'] < 0 else '')
                return ('<td class="num %s">%d</td><td class="num %s">%+.3f</td>'
                        '<td class="num">%+.2f</td><td class="num">%.1f%%</td>'
                        % (cls, r['n'], cls, r['avg'], r['t'], r['wr']))
            srows.append('<tr><td><b>%s</b></td><td class="num %s">%.1f年</td><td>%s</td>'
                         '%s%s%s<td>%s</td></tr>'
                         % (s, depth, yrs, side, cell(a), cell(h), cell(b), bar(h['avg'] if h and h['n'] >= 10 else 0)))

    TPL = """<!DOCTYPE html><html lang="zh-HK"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>ExtraCCY Power — 全對測試賬 + 逐 Symbol 表現</title>
<style>
:root{--l0:#0B1220;--l1:#131C2E;--l2:#1A2438;--line:#2A3650;--t1:#E6EDF7;--t2:#A8B4C4;--t3:#6B7A90;
--g:#3DDC84;--r:#FF6B6B;--y:#FFB454;--b:#5CA8FF}
*{box-sizing:border-box}
body{margin:0;background:var(--l0);color:var(--t1);font:14px/1.6 -apple-system,"Segoe UI","PingFang HK","Microsoft JhengHei",sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:28px 18px 60px}
h1{font-size:22px;margin:0 0 6px}
h2{font-size:16px;margin:36px 0 10px;padding-bottom:8px;border-bottom:1px solid var(--line)}
.meta{color:var(--t3);font-size:12px;margin-bottom:22px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:18px 0}
.kpi{background:var(--l1);border:1px solid var(--line);border-radius:10px;padding:14px}
.kpi .lbl{font-size:11px;color:var(--t2);letter-spacing:.4px;margin-bottom:6px}
.kpi .val{font-size:24px;font-weight:700;font-variant-numeric:tabular-nums}
.kpi .sub{font-size:11px;color:var(--t3);margin-top:4px}
.g{color:var(--g)}.r{color:var(--r)}.y{color:var(--y)}
table{width:100%;border-collapse:collapse;font-size:12.5px;margin:10px 0}
th{background:var(--l2);color:var(--t2);font-weight:600;text-align:left;padding:8px 8px;border-bottom:1px solid var(--line);white-space:nowrap;font-size:11px}
td{padding:6px 8px;border-bottom:1px solid rgba(42,54,80,.55);vertical-align:middle}
tr:hover td{background:rgba(92,168,255,.05)}
.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.dim{color:var(--t3);font-size:11.5px}
.good{color:var(--g);font-weight:600}
.bad{color:var(--r)}
.v-bad{color:var(--r)}.v-mid{color:var(--y)}.v-ok{color:var(--g)}
.bw{width:52px;height:6px;background:var(--l2);border-radius:3px;overflow:hidden;display:inline-block}
.bar{height:100%;border-radius:3px}
.bar.pos{background:var(--g)}.bar.neg{background:var(--r)}.bar.zero{background:var(--t3)}
.note{background:var(--l1);border-left:3px solid var(--y);border-radius:6px;padding:12px 14px;margin:14px 0;font-size:13px;color:var(--t2)}
.note b{color:var(--t1)}
.pw{display:inline-block;padding:1px 7px;border-radius:4px;font-size:11px;font-weight:600}
.pw.ok{background:rgba(61,220,132,.15);color:var(--g)}
.pw.bad{background:rgba(255,107,107,.15);color:var(--r)}
</style></head><body><div class="wrap">
<h1>ExtraCCY Power — 全對測試賬 + 逐 Symbol 表現</h1>
<div class="meta">生成：{{NOW}} ｜ 資料源：MT4 .hst 最長歷史 + PowerHistory H4/D1 ｜ 出場：TP=2×ATR／SL=1×ATR／最多持 8 支</div>

<div class="note"><b>先睇數據深度。</b>29 個 symbol 之中只有 <b>{{NLONG}} 個</b>有 10 年以上同 power 數據重疊；
其餘 <b>{{NSHORT}} 個</b>只有約 1.5 年，<b>XAUUSD 只有 0.9 年</b>。短樣本嘅數字只能當「有冇異常」，唔可以當結論。</div>

<div class="kpis">
{{KPI}}
</div>

<h2>一、全部測試方向總賬（35 項）</h2>
<table><thead><tr><th>組別</th><th>訊號</th><th>數據</th><th>樣本</th><th>平均</th><th>t 值</th><th>勝率</th><th>判定</th></tr></thead>
<tbody>{{TESTS}}</tbody></table>

<h2>二、逐 Symbol × BUY/SELL 表現</h2>
<div class="meta">每組四欄：樣本數 ／ 平均 R ／ t 值 ／ 勝率。綠＝平均&gt;+0.10R 且 t&gt;2。<br>
ALL＝無過濾假突破（基準）；H4Q＝H4 快(10)+慢(120) power 同向；BOTH＝H4Q 再加前一交易日 D1 power 同向。</div>
<table><thead><tr><th>Symbol</th><th>深度</th><th>方向</th>
<th>ALL<br>n</th><th>ALL<br>R</th><th>ALL<br>t</th><th>ALL<br>勝率</th>
<th>H4Q<br>n</th><th>H4Q<br>R</th><th>H4Q<br>t</th><th>H4Q<br>勝率</th>
<th>BOTH<br>n</th><th>BOTH<br>R</th><th>BOTH<br>t</th><th>BOTH<br>勝率</th><th></th></tr></thead>
<tbody>{{SYMS}}</tbody></table>

<h2>三、點解「加 D1 確認」幫唔到</h2>
<p>長歷史 10 對：<b>H4Q +0.091R（t=7.97）</b>、BOTH +0.093R（t=5.24）——加 D1 之後樣本少 58%，平均 R 只升 0.002，
t 值反而跌。即係 D1 power 冇提供額外資訊，只係把同一個訊號再篩一次。</p>
<p>分邊睇：長歷史組 H4Q 嘅 BUY +0.081R（t=5.05）／SELL +0.102R（t=6.22），兩邊都正，冇單邊偏誤。</p>

<h2>四、結論</h2>
<p><span class="pw ok">成立</span> 唯一有 alpha 嘅結構：<b>H4 假突破 fade ＋ 快慢 power 同向</b>。
長歷史 10 對 +0.091R（t=7.97）；原本 4 對 16.9 年 +0.272R；兩者差距主要來自 NZDUSD（−0.077R）同 GBPCHF／GBPJPY（接近 0）。</p>
<p><span class="pw bad">不成立</span> 純 power 判方向、斜率、cross、MACD／STC、拔河、Fib —— 全部已否證，
詳見上表 35 項。</p>
<div class="note"><b>要留意：</b>呢份報告全部係 H4 收盤後下一支開盤入場，未計 spread／滑點；
實測扣 3 pips 只蝕 0.003R（H4 ATR 平均 103 pips），所以成本唔係主要風險。<b>主要風險係樣本深度</b>。</div>
<div class="meta" style="margin-top:32px">generator: engine/research/make_allpairs_report.py ｜ data: engine/research/exp_allpairs2.py</div>
</div></body></html>"""
    html = (TPL
        .replace('{{NOW}}', datetime.datetime.now().strftime('%Y-%m-%d %H:%M HKT'))
        .replace('{{NLONG}}', str(len(long_syms)))
        .replace('{{NSHORT}}', str(len(short_syms)))
        .replace('{{KPI}}', ''.join([
            card('長歷史 10 對 · H4Q 過濾', k_long_h4q, '（最可信）'),
            card('長歷史 10 對 · 無過濾', k_long_all),
            card('29 對合計 · H4Q 過濾', k_all_h4q, '（含短樣本）'),
            card('19 個短樣本 · H4Q 過濾', k_short_h4q, '（1.5 年，勿當結論）'),
        ]))
        .replace('{{TESTS}}', ''.join(trows))
        .replace('{{SYMS}}', ''.join(srows)))

    open(OUT, 'w', encoding='utf-8').write(html)
    print('written', OUT, os.path.getsize(OUT), 'bytes')


if __name__ == '__main__':
    main()
