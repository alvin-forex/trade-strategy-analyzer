#!/usr/bin/env python3
"""rebuild_index_deep_v2.py — index_* deep 頁 Template A 重寫（Muse 規格 2026-11-02）

鐵律（Muse §2）：
  - 零 JS（零 <script>、零 on* 屬性）；摺疊只准 <details>
  - 單頁縱向敘事「結論→證據→深挖」＋純 anchor 錨點目錄
  - 六種降級零空殼軍規（§2.2 表）：空表殼/NaN/死行/死掣唔准出街
  - 深色 token §1.1（#0a0e17/#FFD700/#4CAF50/#FF5722）

做法：轉換器——由現有 index_*.html 收割 panels＋頂部三卡，重排入新殼。
  舊頁 content 引用 var(--green)/--red/--text 等，新殼 root 以深色值重定義同名變數。
"""
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup

BASE = Path(__file__).resolve().parents[2]          # repo root
REPORTS = BASE / 'docs' / 'reports'

# Muse §1.1 深色 token＋舊變數別名
CSS = """
:root{--bg:#0a0e17;--card:#111520;--card2:#1a1f2e;--zebra:#151b28;--brd:#1e2433;--th:#111520;
--text:#d0d0d0;--text2:#777;--pri:#FFD700;--acc:#64b5f6;--grn:#4CAF50;--red:#FF5722;--yel:#FFC107;
--green:var(--grn);--yellow:var(--yel);--orange:#fd7e14;--primary:var(--pri);--accent:var(--acc);
--grade-a:#4CAF50;--grade-b:#FFC107;--grade-c:#fd7e14;--grade-d:#FF5722;
--radius:12px;--shadow:0 4px 16px rgba(0,0,0,.4)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Microsoft JhengHei',sans-serif;background:var(--bg);color:var(--text);line-height:1.6}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.layout{max-width:1200px;margin:0 auto;padding:16px;display:grid;grid-template-columns:172px 1fr;gap:20px}
main{min-width:0}
.toc{position:sticky;top:16px;align-self:start;background:var(--card);border:1px solid var(--brd);border-radius:var(--radius);padding:14px 12px;font-size:.85em}
.toc h3{color:var(--pri);font-size:.95em;margin-bottom:8px}
.toc a{display:block;padding:5px 6px;border-radius:6px;color:var(--text2)}
.toc a:hover{background:var(--card2);color:var(--text);text-decoration:none}
.banner{background:rgba(255,193,7,.12);border:1px solid var(--yel);border-radius:var(--radius);padding:12px 16px;margin:0 0 16px;color:var(--yel);font-size:.9em}
.hero{background:linear-gradient(135deg,#16213e 0%,#0f1729 100%);border:1px solid var(--brd);border-radius:var(--radius);padding:22px 20px;margin-bottom:18px}
.hero h1{color:#fff;font-size:1.55em;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.hero .sub{color:#a8d8ea;font-size:.88em;margin-top:2px}
.chip{display:inline-block;padding:3px 12px;border-radius:999px;font-weight:700;font-size:.8em;vertical-align:middle}
.chip.grade{font-size:1.05em;padding:4px 16px}
.chip.gray{background:rgba(119,119,119,.15);color:var(--text2);font-weight:400}
.chip.warn{background:rgba(255,193,7,.15);color:var(--yel)}
.conclusion{margin:10px 0 0;color:var(--text2);font-size:.92em}
.six{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin-top:14px}
.six .cell{background:var(--card2);border:1px solid var(--brd);border-radius:10px;padding:10px 12px}
.six .k{color:var(--text2);font-size:.75em}
.six .v{font-size:1.15em;font-weight:700;margin-top:2px}
.pos{color:var(--grn)}.neg{color:var(--red)}.mut{color:var(--text2)}
section.card,div.card,details.card{background:var(--card);border:1px solid var(--brd);border-radius:var(--radius);padding:18px 20px;margin-bottom:16px}
section>h2,details>summary{color:var(--pri);font-size:1.15em;margin:0 0 10px;font-weight:700}
details>summary{cursor:pointer;list-style:none}
details>summary::before{content:'▸ ';color:var(--acc)}
details[open]>summary::before{content:'▾ '}
.subsec{margin-bottom:18px}
.subsec:last-child{margin-bottom:0}
.subsec>h3{color:var(--acc);font-size:1em;margin:0 0 8px}
.table-wrap{overflow-x:auto;border:1px solid var(--brd);border-radius:8px}
table{border-collapse:collapse;width:100%;font-size:.88em}
th{background:var(--th);color:var(--pri);text-align:left;padding:8px 10px;border-bottom:1px solid var(--brd);white-space:nowrap}
td{padding:7px 10px;border-bottom:1px solid var(--brd)}
tbody tr:nth-child(even) td{background:var(--zebra)}
tr:hover td{background:var(--card2)}
.chart-plate{background:#fff;border-radius:8px;padding:10px}
.chart-plate svg{max-width:100%;height:auto}
.note{color:var(--text2);font-size:.85em;margin-top:8px}
.degrade{display:flex;gap:10px;align-items:flex-start;background:var(--card2);border:1px dashed var(--brd);border-radius:10px;padding:14px 16px;color:var(--text2);font-size:.9em}
.degrade::before{content:'⏳';filter:grayscale(0)}
.foot{color:var(--text2);font-size:.8em;text-align:center;padding:18px 0 26px}
.back{display:inline-block;margin:0 0 14px;font-size:.9em}
@media(max-width:860px){.layout{grid-template-columns:1fr}
.toc{position:static;display:flex;flex-wrap:wrap;gap:6px}
.toc h3{width:100%}.toc a{display:inline-block;background:var(--card2);border:1px solid var(--brd);padding:6px 12px}
.six{grid-template-columns:repeat(2,1fr)}
section.card,details.card{padding:14px}
td,th{padding:6px 8px}}
"""

IA = [
    # (section key, 標題, [panel ids], mode)  mode: flat | advanced | raw
    ('equity', '📈 收益曲線', ['tab-equity'], 'flat'),
    ('score', '🎯 質量評分', ['tab-score'], 'flat'),
    ('layers', '📚 層數分析（含馬丁風險）', ['tab-layer', 'tab-martin', 'tab-martin-v3', 'tab-autopsy'], 'flat'),
    ('symbol', '💱 貨幣對×方向', ['tab-symbol', 'tab-direction', 'tab-symbol-drill'], 'flat'),
    ('time', '🕐 時間行為（時段・持倉・波幅）', ['tab-session', 'tab-holding', 'tab-volatility'], 'flat'),
    ('advanced', '🔧 進階參考', ['tab-tpsl', 'tab-simulate', 'tab-copy', 'tab-compare', 'tab-market',
                       'tab-regime', 'tab-v2tech'], 'advanced'),
    ('raw', '🗃️ 原始數據', ['tab-positions', 'tab-set', 'tab-archive', 'tab-news'], 'raw'),
]
DEGRADE_PAT = re.compile(r'未上傳|未上載|請上載|請上傳|載入市場數據中|載入市況數據中|點擊「載入|載入最新|上傳嘅\.set|搜尋')

# Muse §2.2 降級語句
DEGRADE_MSG = {
    'tab-equity': '收益曲線數據補全中——將於下次數據更新後自動補滿。',
    'tab-score': '質量評分數據補全中——將於下次數據更新後自動補滿。',
    'tab-layer': '層數分析數據補全中——將於下次數據更新後自動補滿。',
    'tab-martin': '馬丁風險分析數據補全中——將於下次數據更新後自動補滿。',
    'tab-martin-v3': '馬丁 V3 剖析數據補全中——將於下次數據更新後自動補滿。',
    'tab-autopsy': '馬丁剖析 V3 數據補全中——將於下次數據更新後自動補滿。',
    'tab-symbol': '貨幣對排名數據補全中——將於下次數據更新後自動補滿。',
    'tab-direction': '方向分析數據補全中——將於下次數據更新後自動補滿。',
    'tab-symbol-drill': '貨幣穿透分析屬互動模組——靜態版將於下次更新提供摘要。',
    'tab-session': '時段分析數據補全中——將於下次數據更新後自動補滿。',
    'tab-holding': '持倉時間分析數據補全中——將於下次數據更新後自動補滿。',
    'tab-volatility': '波幅分析數據補全中——將於下次數據更新後自動補滿。',
    'tab-tpsl': 'TP/SL 參考數據補全中——將於下次數據更新後自動補滿。',
    'tab-simulate': 'Copy 模擬結果未生成——模擬管線（copy_sims）數據補全後自動出結果。',
    'tab-copy': 'Copy 推薦數據補全中——將於下次數據更新後自動補滿。',
    'tab-compare': '策略對比需要第二份 CSV——單訊號深度頁不適用此區。',
    'tab-market': '市場語境數據補全中——將於下次數據更新後自動補滿。',
    'tab-regime': '市況×策略數據補全中——將於下次數據更新後自動補滿。',
    'tab-v2tech': 'V2 技術分析屬互動模組——靜態版將於下次更新提供摘要。',
    'tab-positions': '倉位明細數據補全中——將於下次數據更新後自動補滿。',
    'tab-set': 'SET 檔案未上傳——參數配置將於數據補全後顯示。',
    'tab-archive': '歷史記錄屬分析器本機模組——靜態版不適用。',
    'tab-news': '外匯新聞屬互動模組——每日早晚報告見站內 forex_reports 區。',
}


def strip_dynamic(tag):
    """零 JS 軍規：剝 on* 屬性＋script＋死制樣式"""
    for t in list(tag.find_all(True)):
        if getattr(t, 'attrs', None):
            for attr in list(t.attrs):
                if attr.lower().startswith('on'):
                    del t.attrs[attr]
            if t.has_attr('style') and 'display:none' in (t.attrs.get('style') or '').replace(' ', ''):
                # 攤平可見（Muse 軍規：唔靠 JS 都要完全可見）——唔刪內容
                t.attrs['style'] = (t.attrs.get('style') or '').replace('display:none', '').strip() or None
                if t.attrs['style'] is None:
                    del t.attrs['style']
    for s in tag.find_all('script'):
        s.decompose()
    for st in tag.find_all('style'):
        st.decompose()  # panel 內嵌 CSS（v3-subtab 制）——除返去 .v3-section 即攤平可見
    for sub in tag.select('.v3-subtab, .v3-tabs'):
        sub.decompose()  # 死副tab 導航
    return tag


def panel_rich(p):
    """內容充足判定（§2.2 校準）：svg/tr/文字量＋樣板殼偵測"""
    if p is None:
        return False
    txt = p.get_text(' ', strip=True)
    if len(p.select('svg')) >= 1 or len(p.select('tr')) >= 3 or len(txt) >= 400:
        # 都仲要避「純樣板殼＋少量字」——檢查死板句尾（未上傳/載入中/請上載）
        if len(p.select('tr')) == 0 and len(p.select('svg')) == 0 and DEGRADE_PAT.search(txt):
            return False
        return True
    return False


def clean_panel(p, soup=None):
    """收割後清理：空 td→灰「—」（規則③）；全空行刪＋footnote（規則④）；裸 table 加橫向掃 wrap"""
    if soup is None:
        soup = p.find_parent('html') or p
    for tbl in p.find_all('table'):
        if tbl.find_parent(['div', 'section']) is None or (
                tbl.parent.name != 'div' or 'table-wrap' not in (tbl.parent.get('class') or [])):
            wrap = soup.new_tag('div', attrs={'class': 'table-wrap'})
            tbl.replace_with(wrap)
            wrap.append(tbl)
    empty_cells = 0
    for td in p.find_all(['td', 'th']):
        if not td.get_text(strip=True):
            td.string = '—'
            td['style'] = 'color:var(--text2)'
            empty_cells += 1
    dropped = 0
    for tr in p.select('tr'):
        tds = tr.find_all('td')
        if tds and all(td.get_text(strip=True) == '—' for td in tds):
            tr.decompose()
            dropped += 1
    if dropped:
        note = soup.new_tag('div', attrs={'class': 'note'})
        note.string = f'另有 {dropped} 個零交易子集行已省略。'
        (p.find('table') or p).append(note)
    return p, empty_cells, dropped


def degrade_block(pid, title):
    return (f'<div class="degrade">{DEGRADE_MSG.get(pid, "該區數據補全中——將於下次數據更新後自動補滿。")}</div>')


def harvest(soup):
    """拆頂部三卡＋panels"""
    body = soup.body
    verdict, exec_card, stat_card = None, None, None
    for div in body.find_all('div', class_='card', recursive=True):
        t = div.get_text(' ', strip=True)
        if 'Executive Summary' in t and exec_card is None:
            exec_card = div
        elif '摘要統計' in t and stat_card is None:
            stat_card = div
        elif verdict is None and len(t) < 60 and ('⭐' in t or '需調整' in t or '觀察' in t or '可 Copy' in t or '不建議' in t):
            verdict = div
    panels = {}
    for p in body.select('[id^="tab-"]'):
        panels[p.get('id')] = p
    return verdict, exec_card, stat_card, panels


def parse_statboxes(stat_card):
    """摘要統計 statboxes → dict（六宮格＋n 用）"""
    out = {}
    if stat_card is None:
        return out
    boxes = stat_card.select('.statbox, .stat-box, .stat')
    if not boxes:
        boxes = stat_card.find_all('div', recursive=False)
    for b in stat_card.select('div'):
        txt = b.get_text(' ', strip=True)
        m = re.match(r'^(\S+)\s+(倉位數|交易筆數|勝率|Profit Factor|總盈虧|Max DD|平均層數|平均持倉|平均盈利|平均虧損|賠率 W/L|Sharpe Ratio)$', txt)
        if m:
            out[m.group(2)] = m.group(1)
    return out


def parse_exec(exec_card):
    """Executive Summary → verdict 字＋key metrics"""
    out = {}
    if exec_card is None:
        return out
    txt = exec_card.get_text(' | ', strip=True)
    m = re.search(r'\| ([⭐🔍✅⚠️\S]+) \| 綜合評價', txt)
    out['verdict'] = m.group(1) if m else ''
    return out


def grade_from_score(score_p):
    """綜合評級：取評級分佈最大桶（A(6) B(11) C(12) → 最後出現最多桶；38900 例 C(12)）"""
    if score_p is None:
        return None
    txt = score_p.get_text(' ', strip=True)
    buckets = re.findall(r'([ABCDE])\s*\((\d+)\)', txt)
    if not buckets:
        return None
    g = max(buckets, key=lambda x: int(x[1]))
    return g[0]


def render_page_v2panels(sid, raw, gen_date):
    """「TSA v2 Atom-8」5-panel 舊格式（.main-nav + .panel）——同殼重排：
    儀表板/表現/風險平鋪，Copy 決策平鋪，數據明細入 details；零 JS 攤平"""
    soup = BeautifulSoup(raw, 'lxml')
    strip_dynamic(soup)
    header = soup.select_one('.report-header')
    hero_html = ''
    if header is not None:
        for hh in header.select('h1,h2,h3'):
            hh.decompose()
        hero_html = f'<header class="hero" id="top"><h1>Signal {sid}</h1><div class="sub">{header.decode_contents()}</div></header>'
    panels = soup.select('.panel')
    titles = ['📊 儀表板', '📈 表現分析', '⚠️ 風險評估', '💡 Copy 決策', '📌 數據明細']
    secs = []
    for i, p in enumerate(panels):
        cp, _, _ = clean_panel(p, soup)
        first_h = cp.find(['h1', 'h2', 'h3'])
        if first_h is not None:
            first_h.decompose()
        inner = cp.decode_contents()
        title = titles[i] if i < len(titles) else f'區塊 {i+1}'
        if i == len(panels) - 1 and len(panels) >= 3:
            secs.append(f'<details class="card" id="sec-p{i}" open><summary>{title}</summary>{inner}</details>')
        else:
            secs.append(f'<section class="card" id="sec-p{i}"><h2>{title}</h2>{inner}</section>')
    if not hero_html:
        hero_html = f'<header class="hero" id="top"><h1>Signal {sid}</h1></header>'
    toc = '<nav class="toc"><h3>目錄</h3>' + ''.join(
        f'<a href="#sec-p{i}">{titles[i] if i < len(titles) else i+1}</a>' for i in range(len(panels))) + '</nav>'
    body_html = (f'<div class="layout">{toc}<main>'
                 f'<a class="back" href="../index.html">← 返回報告索引</a>{hero_html}'
                 + ''.join(secs) +
                 f'<div class="foot">Generated by Trade Strategy Analyzer · Template A v2（零 JS 靜態版） · {gen_date}</div>'
                 f'</main></div>')
    return ('<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Signal {sid} — Trade Strategy Analysis Report</title>'
            f'<style>{CSS}</style></head><body>{body_html}</body></html>')


def render_page(sid, src_path, gen_date):
    raw = src_path.read_text(encoding='utf-8')
    # 防呆閘：只處理舊格式——已重寫頁（v2 殼）唔准再轉換
    if '深度分析報告 v2' in raw:
        print(f'⊘ index_{sid}.html 已係 Template A v2——跳過')
        return None
    if '.main-nav' in raw and '.panel' in raw and 'tabs-layout' not in raw:
        html = render_page_v2panels(sid, raw, gen_date)
        src_path.write_text(html, encoding='utf-8')
        print(f'✓ index_{sid}.html 重寫完成（TSA v2 5-panel 格式） {len(html)} bytes')
        return None  # 已寫檔，main 免再寫
    if 'tabs-layout' not in raw and 'id="tab-' not in raw:
        print(f'⊘ index_{sid}.html 唔係舊 tab 格式（可能已重寫）——跳過')
        return None
    soup = BeautifulSoup(raw, 'lxml')
    verdict, exec_card, stat_card, panels = harvest(soup)
    strip_dynamic(soup)
    stats = parse_statboxes(stat_card)
    execv = parse_exec(exec_card)
    grade = grade_from_score(panels.get('tab-score'))

    # 倉位數（規則①②用）
    n_pos = None
    for k, v in stats.items():
        if k == '倉位數':
            try:
                n_pos = int(str(v).replace(',', ''))
            except ValueError:
                pass
    trades_txt = stats.get('交易筆數', '')

    # —— 規則①：零交易 → 中央卡
    if n_pos == 0:
        return _central_card(sid, gen_date)

    # —— 規則⑥：細頁帶／多區降級 → 黃橫幅
    degraded = [pid for pid, p in panels.items() if not panel_rich(p)]
    banner = ''
    if degraded:
        banner = (f'<div class="banner">⚠️ 部分數據生成不完整（{len(degraded)} 區補全中，生成於 {gen_date}）——'
                  f'已按零空殼規則顯示提示位，數據補全後將自動補滿。</div>')

    # —— 規則②：樣本少
    sample_chip = ''
    try:
        if n_pos is not None and n_pos < 30:
            sample_chip = f' <span class="chip gray">樣本少 n={n_pos}</span>'
    except TypeError:
        pass

    # —— hero 六宮格
    def _cls(v):
        s = str(v)
        return 'neg' if s.startswith(('-', '$-')) else ('pos' if s.startswith(('+', '$+')) else 'mut')
    six = [
        ('總盈虧', stats.get('總盈虧', '—'), _cls(stats.get('總盈虧', ''))),
        ('勝率', stats.get('勝率', '—'), 'mut'),
        ('Profit Factor', stats.get('Profit Factor', '—'), 'mut'),
        ('盈虧比（賠率 W/L）', stats.get('賠率 W/L', '—'), 'mut'),
        ('Max DD', stats.get('Max DD', '—'), 'neg'),
        ('馬丁風險', _martin_risk(panels.get('tab-martin')), 'mut'),
    ]
    six_html = ''.join(f'<div class="cell"><div class="k">{k}</div><div class="v {c}">{v}</div></div>'
                       for k, v, c in six)
    concl = _conclusion(stats, execv, grade)
    grade_chip = f'<span class="chip grade" style="background:var(--grade-{grade.lower() if grade else "d"}22);color:var(--grade-{grade.lower() if grade else "d"})">{grade or "—"}</span>'
    verdict_chip = f'<span class="chip warn">{execv["verdict"]}</span>' if execv.get('verdict') else ''
    hero = (f'<header class="hero" id="top"><h1>Signal {sid} {grade_chip}{verdict_chip}{sample_chip}</h1>'
            f'<div class="sub">forex-forest signals · 深度分析報告 v2 · 生成 {gen_date}</div>'
            f'<div class="conclusion">{concl}</div>'
            f'<div class="six">{six_html}</div></header>')

    # —— 錨點目錄
    toc_items = [('sec-equity', '收益曲線'), ('sec-score', '質量評分'), ('sec-layers', '層數分析'),
                 ('sec-symbol', '貨幣對×方向'), ('sec-time', '時間行為'),
                 ('sec-advanced', '進階參考'), ('sec-raw', '原始數據')]
    toc = '<nav class="toc"><h3>目錄</h3>' + ''.join(
        f'<a href="#{a}">{t}</a>' for a, t in toc_items) + '</nav>'

    # —— 各區
    secs_html = []
    for key, title, pids, mode in IA:
        blocks, sub_titles = [], {'tab-layer': '層級分佈', 'tab-martin': '馬丁風險', 'tab-martin-v3': '馬丁 V3 剖析',
                                  'tab-autopsy': '馬丁剖析 V3', 'tab-symbol': '貨幣對排名', 'tab-direction': '方向分析',
                                  'tab-symbol-drill': '貨幣穿透', 'tab-session': '時段分佈', 'tab-holding': '持倉時間',
                                  'tab-volatility': '波幅分析', 'tab-tpsl': 'TP/SL 參考', 'tab-simulate': 'Copy 模擬',
                                  'tab-copy': 'Copy 推薦', 'tab-compare': '策略對比', 'tab-market': '市場語境',
                                  'tab-regime': '市況×策略', 'tab-v2tech': 'V2 技術分析', 'tab-positions': '倉位明細',
                                  'tab-set': 'SET 參數', 'tab-archive': '歷史記錄', 'tab-news': '外匯新聞'}
        for pid in pids:
            p = panels.get(pid)
            if pid not in panels and pid in ('tab-martin-v3', 'tab-autopsy') and (
                    'tab-martin-v3' in panels or 'tab-autopsy' in panels):
                continue  # 別名去重
            if p is None:
                continue
            if panel_rich(p):
                cp, empty_n, drop_n = clean_panel(p, soup)
                # 只摘 panel 自帶第一個標題做 subsec 題（其餘 h3/h4 內容標題全保留）
                own_title = None
                first_h = cp.find(['h1', 'h2', 'h3'])
                if first_h is not None:
                    own_title = first_h.get_text(' ', strip=True)
                    first_h.decompose()
                inner = cp.decode_contents()
                blocks.append(f'<div class="subsec"><h3>{own_title or sub_titles.get(pid, pid)}</h3>'
                              f'<div class="chart-plate">{inner}</div></div>')
            else:
                blocks.append(f'<div class="subsec"><h3>{sub_titles.get(pid, pid)}</h3>{degrade_block(pid, "")}</div>')
        if not blocks:
            continue
        inner = ''.join(blocks)
        if mode == 'advanced':
            n_open = ''
            secs_html.append(f'<details class="card" id="sec-{key}"{n_open}><summary>{title}'
                             f'<span class="chip gray">{len(blocks)} 小節</span></summary>{inner}</details>')
        elif mode == 'raw':
            secs_html.append(f'<details class="card" id="sec-{key}"><summary>{title}'
                             f'<span class="chip gray">{len(blocks)} 小節</span></summary>{inner}</details>')
        else:
            secs_html.append(f'<section class="card" id="sec-{key}"><h2>{title}</h2>{inner}</section>')

    body_html = (f'<div class="layout">{toc}<main>'
                 f'<a class="back" href="../index.html">← 返回報告索引</a>{banner}{hero}'
                 + ''.join(secs_html) +
                 f'<div class="foot">Generated by Trade Strategy Analyzer · Template A v2（零 JS 靜態版） · {gen_date}</div>'
                 f'</main></div>')

    return ('<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Signal {sid} — Trade Strategy Analysis Report</title>'
            f'<style>{CSS}</style></head><body>{body_html}</body></html>')


def _martin_risk(martin_p):
    if martin_p is None:
        return '—'
    txt = martin_p.get_text(' ', strip=True)
    m = re.search(r'(🟢|🔴|🟡|⛔)\s*(LOW|MEDIUM|HIGH|極高)?\s*風險', txt)
    if m:
        label = m.group(0).strip()
        depth = re.search(r'最大層數[:：]\s*(L\d+)', txt)
        return f'{label}（{depth.group(1)}）' if depth else label
    return '—'


def _conclusion(stats, execv, grade):
    parts = []
    if execv.get('verdict'):
        parts.append(f'綜合評價「{execv["verdict"]}」')
    if grade:
        parts.append(f'主評級 {grade}')
    if '交易筆數' in stats:
        parts.append(f'{stats["交易筆數"]} 筆交易')
    if '總盈虧' in stats:
        parts.append(f'總盈虧 {stats["總盈虧"]}')
    if '勝率' in stats:
        parts.append(f'勝率 {stats["勝率"]}')
    return ' · '.join(parts) if parts else '—'


def _central_card(sid, gen_date):
    return ('<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Signal {sid} — Trade Strategy Analysis Report</title>'
            f'<style>{CSS}</style></head><body><div class="layout"><main>'
            f'<a class="back" href="../index.html">← 返回報告索引</a>'
            f'<div class="card" style="text-align:center;padding:48px 24px">'
            '<div style="font-size:2.4em">🗂️</div>'
            f'<h2 style="color:var(--pri);margin:10px 0">Signal {sid} 暫無平倉記錄</h2>'
            '<div class="note">可能原因：追蹤期太短／訊號已除名／數據層補全中。</div>'
            f'<div class="note">最後數據更新：{gen_date} · 數據補全後本頁將自動補滿。</div>'
            '<p style="margin-top:14px"><a href="../signal_ranking.html">返排名頁 →</a></p>'
            '</div></main></div></body></html>')


def main():
    gen_date = '2026-11-02'
    sids = sys.argv[1:] or ['38900']
    for sid in sids:
        src = REPORTS / f'index_{sid}.html'
        if not src.exists():
            print(f'✗ {src} 不存在')
            continue
        html = render_page(sid, src, gen_date)
        if html is None:
            continue
        src.write_text(html, encoding='utf-8')
        print(f'✓ index_{sid}.html 重寫完成 {len(html)} bytes')


if __name__ == '__main__':
    main()
