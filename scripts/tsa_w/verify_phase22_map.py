#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Phase 2.2 地圖動效驗證（Playwright）— 對照設計基準 v1.1 §2.2 驗收清單

- [2.2] SVG ≤40KB inline；⏸ 關閉後全停、資訊零流失（L1 留）、localStorage 記住
- reduced-motion 模擬全停；HIGH 三重編碼（色＋▲＋字）齊；灰階仍分 HIGH/MED；同時呼吸點 ≤3
- 口徑：地圖環＝未來 24h——countries[] 在場食 generator rollup；唔在場由 events[] 自行 filter
- 回歸：8 國標籤不變、1280/390 零溢出、零 JS 錯、無數據 fallback 靜態零錯
fixture 經 route 攔截注入（home/map_events.json），唔會推上 repo。
"""
import json, sys, datetime, pathlib, threading, functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright

PLAIN = '/tmp/p22/index_p22.html'
SRVROOT = '/tmp/p22'  # HTTP serve（file:// 下 fetch 被擋，唔行 route）

_handler = functools.partial(SimpleHTTPRequestHandler, directory=SRVROOT)
_srv = ThreadingHTTPServer(('127.0.0.1', 0), _handler)
PORT = _srv.server_address[1]
threading.Thread(target=_srv.serve_forever, daemon=True).start()
BASE = f'http://127.0.0.1:{PORT}'
SHOT = pathlib.Path('/tmp/p22/shots'); SHOT.mkdir(exist_ok=True)
FAILS = []

def check(name, cond, detail=''):
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f'  ({detail})' if detail and not cond else ''))
    if not cond: FAILS.append(f'{name}: {detail}')

def txts(page, sel):
    """SVG <text> 用 textContent（SVGElement 冇 innerText）"""
    return page.eval_on_selector_all(sel, "els=>els.map(e=>e.textContent.trim())")

HKT = datetime.timezone(datetime.timedelta(hours=8))
now = datetime.datetime.now(HKT)
today = now.strftime('%Y-%m-%d')
def hkt(dt): return dt.strftime('%Y-%m-%dT%H:%M:%S+08:00')
GEN = hkt(now.replace(microsecond=0)) + 'Z'  # 必同 localStorage 舊值唔同（context 乾淨其實必新）

def ev(ccy, country, impact, name, t, cnt):
    return {"currency": ccy, "country": country, "impact": impact, "event": name,
            "time_hkt": t, "source": "forexfactory", "event_count_24h": cnt,
            "max_impact": impact, "generated_at": GEN}

# ===== FIXTURE A：generator 口徑（countries[] 在場＝未來 24h rollup）=====
# countries[] 話 3 國活躍（USD/EUR HIGH＋JPY MED）；events[] 仲有 GBP/AUD 舊事件
# ＋1 件今日 HIGH（KPI=1）。環必須跟 countries[]（GBP/AUD 唔出環）。
FIX_A = {"generated_at": GEN, "window": {"past_hours": 24, "future_hours": 24},
 "countries": [
    {"currency": "USD", "country": "US", "event_count_24h": 3, "max_impact": "HIGH"},
    {"currency": "EUR", "country": "EU", "event_count_24h": 2, "max_impact": "HIGH"},
    {"currency": "JPY", "country": "JP", "event_count_24h": 1, "max_impact": "MED"},
 ],
 "events": [
    ev("USD", "US", "HIGH", "FOMC Statement", f"{today}T02:00:00+08:00", 3),
    ev("EUR", "EU", "HIGH", "Inflation Rate YoY Prel", "2026-10-30T21:00:00+08:00", 2),
    ev("JPY", "JP", "MED", "Consumer Confidence", "2026-10-29T13:00:00+08:00", 1),
    ev("GBP", "GB", "MED", "Autumn Forecast Statement", "2026-10-28T20:30:00+08:00", 2),
    ev("AUD", "AU", "MED", "CPI m/m", "2026-10-28T08:30:00+08:00", 1),
 ]}

# ===== FIXTURE B：舊契約（冇 countries[]）——events[] 自行 filter 未來 24h =====
# USD now+1h（HIGH）＋JPY now+2h（MED）係未來；GBP 10-28 係過去→唔出環
FUT1 = hkt(now + datetime.timedelta(hours=1))
FUT2 = hkt(now + datetime.timedelta(hours=2))
FIX_B = {"generated_at": GEN + "B", "events": [
    ev("USD", "US", "HIGH", "ISM Manufacturing PMI", FUT1, 2),
    ev("JPY", "JP", "MED", "BoJ Outlook", FUT2, 1),
    ev("GBP", "GB", "MED", "Autumn Forecast", "2026-10-28T20:30:00+08:00", 1),
 ]}

def route_fix(fixture):
    return lambda route: route.fulfill(status=200, content_type='application/json',
                                       body=json.dumps(fixture))

with sync_playwright() as pw:
    b = pw.chromium.launch()

    # ============ T1-T3：FIXTURE A（countries[] 口徑） ============
    ctx = b.new_context(viewport={'width': 1280, 'height': 900})
    page = ctx.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and not m.text.startswith('Failed to load resource') else None)
    page.route('**/home/map_events.json', route_fix(FIX_A))
    page.goto(f'{BASE}/index_p22.html')
    page.wait_for_timeout(400)

    print('T1 L1 靜態環＋三重編碼（countries[] 口徑＝未來 24h）')
    rings = page.locator('#evLayer .ev-ring')
    check('L1 環 3 國（USD/EUR/JPY）', rings.count() == 3, f'got {rings.count()}')
    hi_txt = page.locator('#evLayer .ev-high-txt')
    check('HIGH 字 2 個（USD/EUR）', hi_txt.count() == 2 and txts(page, '#evLayer .ev-high-txt') == ['HIGH', 'HIGH'], f'got {txts(page, "#evLayer .ev-high-txt")}')
    marks = page.locator('#evLayer .ev-marker')
    check('▲◆ 標記 3 個', marks.count() == 3, f'got {marks.count()}')
    mark_txt = txts(page, '#evLayer .ev-marker')
    check('▲ 2＋◆ 1', mark_txt.count('▲') == 2 and mark_txt.count('◆') == 1, str(mark_txt))
    hi_stroke = page.eval_on_selector_all('#evLayer .ev-ring', """els=>els.map(e=>({
        s:e.querySelector('circle[stroke]').getAttribute('stroke'),
        f:e.querySelector('circle[opacity]').getAttribute('fill')}))""")
    red = [x for x in hi_stroke if x['s'] == '#FF6B6B']; amb = [x for x in hi_stroke if x['s'] == '#FFB454']
    check('色編碼：紅 2 琥珀 1', len(red) == 2 and len(amb) == 1, str(hi_stroke))
    check('HIGH 環填色 @12%', all(x['f'] == '#FF6B6B' for x in red))
    # GBP/AUD 唔准有環（events[] 有舊事件但 countries[] 話佢哋唔活躍）
    check('GBP/AUD 舊事件唔出環（未來 24h 口徑）', rings.count() == 3)
    # 環錨點全部喺 viewBox 內
    vb = page.eval_on_selector('#evLayer', """el=>[...el.querySelectorAll('circle')].every(c=>{
        const r=+c.getAttribute('r'),x=+c.getAttribute('cx'),y=+c.getAttribute('cy');
        return x-r>=0&&y-r>=0&&x+r<=2000&&y+r<=1001})""")
    check('環／標記零出 viewBox', vb)
    # 錨點必須真係喺國土上（isPointInFill；防碎塊拉歪 union 中心）
    inland = page.evaluate("""()=>{
      const map={};document.querySelectorAll('#world-g8 path[data-ccy]').forEach(p=>{
        const c=p.getAttribute('data-ccy').split('-')[0];(map[c]=map[c]||[]).push(p)});
      return [...document.querySelectorAll('#evLayer .ev-ring')].every(g=>{
        const c=g.querySelector('circle[stroke]');
        const pt=new DOMPoint(+c.getAttribute('cx'),+c.getAttribute('cy'));
        return Object.values(map).some(ps=>ps.some(p=>{try{return p.isPointInFill(pt)}catch(e){return false}}));
      })}""")
    check('環錨點全部喺國土上', inland)
    # KPI 接線（events[] 今日 HIGH）
    kpi = page.eval_on_selector_all('.kpi', """els=>els.find(e=>/今日\\s*HIGH/.test(e.querySelector('.kpi-t').textContent))?.querySelector('.kpi-v').textContent""")
    check('KPI 今日 HIGH 事件數＝1', kpi == '1', f'got {kpi!r}')

    print('T2 L2 呼吸 ≤3＋L3 pulse×2')
    halos = page.locator('#evLayer .ev-halo')
    check('呼吸點 ≤3（=3）', halos.count() == 3, f'got {halos.count()}')
    halo_c = page.eval_on_selector_all('#evLayer .ev-halo', """els=>els.map(e=>e.getAttribute('fill'))""")
    check('呼吸點含 USD/EUR（HIGH 先）', halo_c.count('url(#evGlowH)') == 2 and halo_c.count('url(#evGlowM)') == 1, str(halo_c))
    dur = page.eval_on_selector('#evLayer .ev-halo', "el=>getComputedStyle(el).animationDuration+'|'+getComputedStyle(el).animationIterationCount")
    check('呼吸 4s infinite（0.25Hz）', '4s|infinite' in dur, dur)
    pulses = page.locator('#evLayer .map-pulse')
    check('L3 pulse 首渲染 3 環', pulses.count() == 3, f'got {pulses.count()}')
    pd = page.eval_on_selector('#evLayer .map-pulse', "el=>getComputedStyle(el).animationDuration+'|'+getComputedStyle(el).animationIterationCount")
    check('pulse 800ms×2（總 1.6s 唔 loop）', '0.8s|2' in pd, pd)
    page.wait_for_timeout(2000)
    check('pulse 播完自清', page.locator('#evLayer .map-pulse').count() == 0)
    gen_ls = page.evaluate("localStorage.getItem('tsa_map_gen')")
    check('generated_at 入 localStorage', gen_ls and gen_ls.startswith(today) and gen_ls.endswith('+08:00Z'), f'got {gen_ls!r}')

    print('T3 ⏸ 控制（WCAG 2.2.2）')
    btn = page.locator('#mapTgl')
    box = btn.bounding_box()
    check('熱區 44×44', box and box['width'] >= 44 and box['height'] >= 44, str(box))
    check('icon 24×24', abs(page.eval_on_selector('#mapTgl svg', "el=>el.getBoundingClientRect().width") - 24) < 0.5)
    check('aria-pressed 初始 false', btn.get_attribute('aria-pressed') == 'false')
    btn.click(); page.wait_for_timeout(120)
    check('⏸ 後 .map-paused', page.eval_on_selector('.map-mod', "el=>el.classList.contains('map-paused')"))
    check('⏸ 後 halo 全停（display none）', page.eval_on_selector('#evLayer .ev-halo', "el=>getComputedStyle(el).display") == 'none')
    check('L1 資訊零流失（環仍在 DOM）', page.locator('#evLayer .ev-ring').count() == 3)
    check('aria-pressed true＋aria-label 恢復', btn.get_attribute('aria-pressed') == 'true' and btn.get_attribute('aria-label') == '恢復地圖動效')
    check('localStorage motion=off', page.evaluate("localStorage.getItem('tsa_map_motion')") == 'off')
    page.screenshot(path=str(SHOT / 'map_paused_1280.png'), clip={'x': 0, 'y': 130, 'width': 1280, 'height': 300})
    # reload → 跨頁保留（context 唔重開，localStorage 同源保留）
    page.reload(); page.wait_for_timeout(300)
    check('reload 後暫停保留', page.eval_on_selector('.map-mod', "el=>el.classList.contains('map-paused')"))
    # ▶ 恢復
    btn.click(); page.wait_for_timeout(120)
    check('▶ 後 halo 可見＋motion 清除', page.eval_on_selector('#evLayer .ev-halo', "el=>getComputedStyle(el).display") != 'none'
          and page.evaluate("localStorage.getItem('tsa_map_motion')") != 'off')
    # 灰階截圖（HIGH/MED 仍辨——▲HIGH 字＋◆）
    page.evaluate("document.getElementById('mapWrap').style.filter='grayscale(1)'")
    page.screenshot(path=str(SHOT / 'map_grayscale_1280.png'), clip={'x': 0, 'y': 130, 'width': 1280, 'height': 300})
    check('灰階下 HIGH 字仍在', hi_txt.count() == 2)
    page.evaluate("document.getElementById('mapWrap').style.filter=''")
    # 溢出＋標籤回歸
    ovf = page.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
    check('1280 零溢出', ovf == 0, f'ovf={ovf}')
    check('8 國標籤不變（回歸）', page.locator('#world-g8 text.map-lbl').count() == 8)
    page.screenshot(path=str(SHOT / 'map_events_1280.png'), clip={'x': 0, 'y': 130, 'width': 1280, 'height': 300})
    check('零 JS 錯（fixture A 場景）', not errors, str(errors[:3]))
    ctx.close()

    # ============ T4 reduced-motion ============
    ctx2 = b.new_context(viewport={'width': 1280, 'height': 900}, reduced_motion='reduce')
    p2 = ctx2.new_page()
    e2 = []; p2.on('pageerror', lambda e: e2.append(str(e)))
    p2.route('**/home/map_events.json', route_fix(FIX_A))
    p2.goto(f'{BASE}/index_p22.html'); p2.wait_for_timeout(400)
    print('T4 reduced-motion 自停')
    check('halo display none', p2.eval_on_selector('#evLayer .ev-halo', "el=>getComputedStyle(el).display") == 'none')
    check('L3 唔播（0 pulse）', p2.locator('#evLayer .map-pulse').count() == 0)
    check('L1 環仍在（資訊零流失）', p2.locator('#evLayer .ev-ring').count() == 3)
    check('aria-pressed true（自動暫停態）', p2.locator('#mapTgl').get_attribute('aria-pressed') == 'true')
    p2.screenshot(path=str(SHOT / 'map_reduced_motion_1280.png'), clip={'x': 0, 'y': 130, 'width': 1280, 'height': 300})
    check('零 JS 錯（reduced 場景）', not e2, str(e2[:3]))
    ctx2.close()

    # ============ T5 FIXTURE B：冇 countries[] → events[] 自行 filter 未來 24h ============
    ctx5 = b.new_context(viewport={'width': 1280, 'height': 900})
    p5 = ctx5.new_page()
    e5 = []; p5.on('pageerror', lambda e: e5.append(str(e)))
    p5.route('**/home/map_events.json', route_fix(FIX_B))
    p5.goto(f'{BASE}/index_p22.html'); p5.wait_for_timeout(400)
    print('T5 舊契約 fallback（events[] 未來 24h 自聚合）')
    check('環 2 國（USD/JPY 未來；GBP 過去唔出）', p5.locator('#evLayer .ev-ring').count() == 2,
          f'got {p5.locator("#evLayer .ev-ring").count()}')
    halos5 = p5.locator('#evLayer .ev-halo')
    check('呼吸 ≤3（=2）', halos5.count() == 2, f'got {halos5.count()}')
    kpi5 = p5.eval_on_selector_all('.kpi', """els=>els.find(e=>/今日\\s*HIGH/.test(e.querySelector('.kpi-t').textContent))?.querySelector('.kpi-v').textContent""")
    check('KPI 今日 HIGH＝1（USD now+1h 係今日）', kpi5 == '1', f'got {kpi5!r}')
    check('零 JS 錯（fixture B 場景）', not e5, str(e5[:3]))
    ctx5.close()

    # ============ T6 無數據 fallback ＋ T7 390 ============
    ctx3 = b.new_context(viewport={'width': 1280, 'height': 900})
    p3 = ctx3.new_page()
    e3 = []; p3.on('pageerror', lambda e: e3.append(str(e)))
    p3.on('console', lambda m: e3.append(m.text) if m.type == 'error' and not m.text.startswith('Failed to load resource') else None)
    p3.route('**/home/map_events.json', lambda r: r.abort())
    p3.goto(f'{BASE}/index_p22.html'); p3.wait_for_timeout(500)
    print('T6 無數據 fallback（404）')
    check('0 環 0 halo', p3.locator('#evLayer .ev-ring').count() == 0 and p3.locator('#evLayer .ev-halo').count() == 0)
    kpi3 = p3.eval_on_selector_all('.kpi', """els=>els.find(e=>/今日\\s*HIGH/.test(e.querySelector('.kpi-t').textContent))?.querySelector('.kpi-v').textContent""")
    check('KPI 維持 —', kpi3 == '—', f'got {kpi3!r}')
    check('⏸ 在場（idle）', p3.locator('#mapTgl').count() == 1)
    check('零 JS 錯（fallback 場景）', not e3, str(e3[:3]))
    ctx3.close()

    ctx4 = b.new_context(viewport={'width': 390, 'height': 844})
    p4 = ctx4.new_page()
    p4.route('**/home/map_events.json', route_fix(FIX_A))
    p4.goto(f'{BASE}/index_p22.html'); p4.wait_for_timeout(400)
    print('T7 390 回歸')
    ovf4 = p4.evaluate("document.documentElement.scrollWidth-document.documentElement.clientWidth")
    check('390 零溢出', ovf4 == 0, f'ovf={ovf4}')
    check('390 地圖唔出（裁決④）', p4.eval_on_selector('.map-mod', "el=>getComputedStyle(el).display") == 'none')
    ctx4.close()
    b.close()

# ============ T9 SVG 預算 ============
html = pathlib.Path(PLAIN).read_text(encoding='utf-8')
i = html.find('id="world-g8"'); j = html.find('</svg>', i)
svg_len = j + 6 - html.rfind('<svg', 0, i)
print('T9 SVG 預算')
check('inline SVG ≤40KB', svg_len <= 40960, f'{svg_len}B')

print()
_srv.shutdown()
if FAILS:
    print(f'❌ {len(FAILS)} FAIL'); [print(' -', f) for f in FAILS]; sys.exit(1)
print('✅ Phase 2.2 全綠（T1-T9）')
