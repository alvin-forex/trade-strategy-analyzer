#!/usr/bin/env python3
"""verify_phase1_home.py — TSA 新首頁 Phase 1 驗收（明文態）

設計基準 v1.1 Phase 1 驗收項：
  1.1  1280/390 零橫向溢出（另加 A1 式九寬度）＋ 對比 ≥4.5:1 抽查
  1.2  drawer 開合（200ms transition 屬性在位）；csvZone/setZone/csv2Zone 三區
       ids 在位；上載狀態喺 drawer 內顯示；analyze → 分析器 overlay＋檔案交接
  1.3  NAV 6 項（桌面 bar＋漢堡 drawer 兩形態同清單）；aria-current="page"；
       6 連結逐一 HTTP 200；手機漢堡開 drawer
  1.4  （加密後另驗）深色密碼頁
  附带：健康燈 5 pills、地圖 SVG＋標籤、快捷 chips 200、reduced-motion CSS
"""
import asyncio, subprocess, sys, time, os, signal, json
from playwright.async_api import async_playwright

REPO_DOCS = "/home/z/my-project/exchange-repo/docs"
PORT = 8793
BASE = f"http://127.0.0.1:{PORT}/trade-strategy-analyzer/"

os.makedirs("/tmp/pages_root", exist_ok=True)
link = "/tmp/pages_root/trade-strategy-analyzer"
if os.path.islink(link):
    os.remove(link)
os.symlink(REPO_DOCS, link)

# 測試檔（交接驗證用：只驗 File 物件送達分析器，唔跑全分析）
os.makedirs("/tmp/phase1_files", exist_ok=True)
with open("/tmp/phase1_files/trades_test.csv", "w") as f:
    f.write("Time,Type,Price,Lots,Symbol\n2026-01-02 10:00,buy,1.2345,0.01,EURUSD\n")
with open("/tmp/phase1_files/ea_test.set", "w") as f:
    f.write("; test set\nLots=0.01\n")

RESULTS = []
def check(name, ok, extra=""):
    RESULTS.append((name, bool(ok)))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}{'  ' + extra if extra else ''}")

async def overflow_audit(page):
    """A1 式九寬度零溢出審計"""
    widths = [320, 390, 480, 600, 768, 1024, 1280, 1440, 1920]
    bad = []
    for w in widths:
        await page.set_viewport_size({"width": w, "height": 900})
        await page.wait_for_timeout(120)
        sw, cw = await page.evaluate(
            "() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]")
        if sw > cw:
            bad.append((w, sw, cw))
    return bad

async def main():
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(PORT), "--bind", "127.0.0.1",
         "--directory", "/tmp/pages_root"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)
    req_log = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch()

            # ========== 桌面 1280 ==========
            page = await browser.new_page(viewport={"width": 1280, "height": 800})
            page.on("response", lambda r: req_log.append((r.url, r.status)))
            await page.goto(BASE + "index.html", wait_until="networkidle")

            # --- 1.3 NAV ---
            bar_links = await page.eval_on_selector_all(".nav > a", "els => els.map(e => e.getAttribute('href'))")
            check("nav_bar_6_items", len(bar_links) == 6, str(bar_links))
            drawer_links = await page.eval_on_selector_all(".navdrawer nav > a", "els => els.map(e => e.getAttribute('href'))")
            check("nav_drawer_6_items_same", bar_links == drawer_links)
            ac = await page.eval_on_selector_all('.nav a[aria-current="page"]', "els => els.length")
            check("nav_aria_current_home", ac == 1)
            # 6 連結 HTTP 200
            codes = []
            for href in bar_links:
                r = await page.request.get(BASE + href)
                codes.append((href, r.status))
            check("nav_6_links_http200", all(s == 200 for _, s in codes), str(codes))
            # sticky 桌面 nav
            sticky = await page.eval_on_selector(".nav", "e => getComputedStyle(e).position")
            check("nav_sticky_desktop", sticky == "sticky", sticky)
            # 手機 nav 隱藏（<768）
            await page.set_viewport_size({"width": 390, "height": 844})
            nav_disp = await page.eval_on_selector(".nav", "e => getComputedStyle(e).display")
            check("nav_hidden_on_mobile", nav_disp == "none", nav_disp)
            burger_vis = await page.eval_on_selector("#burgerBtn", "e => getComputedStyle(e).display")
            check("burger_visible_on_mobile", burger_vis != "none", burger_vis)

            # --- 1.1 溢出審計（九寬度） ---
            bad = await overflow_audit(page)
            check("a1_nine_widths_zero_overflow", not bad, str(bad))

            # --- 1.1 對比抽查（正文/標籤/按鈕 ≥4.5:1 或大字 3:1） ---
            contrast = await page.evaluate("""() => {
                function lum(c){const m=c.match(/\\d+(\\.\\d+)?/g).map(Number);
                  const [r,g,b]=m;const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)};
                  return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)}
                function ratio(fg,bg){const l1=lum(fg),l2=lum(bg);
                  return (Math.max(l1,l2)+0.05)/(Math.min(l1,l2)+0.05)}
                const samples=[];
                const bg=getComputedStyle(document.body).backgroundColor;
                samples.push(['body_text',ratio(getComputedStyle(document.body).color,bg)]);
                const t=document.querySelector('.ph-title');
                const card=t.closest('.mod');
                const cbg=getComputedStyle(card).backgroundColor;
                samples.push(['module_title',ratio(getComputedStyle(t).color,cbg)]);
                const chip=document.querySelector('.chip');
                const chbg=getComputedStyle(chip).backgroundColor;
                samples.push(['chip_text',ratio(getComputedStyle(chip).color,chbg)]);
                const kpit=document.querySelector('.kpi-t');
                const kbg=getComputedStyle(kpit.closest('.kpi')).backgroundColor;
                samples.push(['kpi_label',ratio(getComputedStyle(kpit).color,kbg)]);
                const pill=document.querySelector('.pill');
                const pbg=getComputedStyle(pill).backgroundColor;
                samples.push(['pill_text',ratio(getComputedStyle(pill).color,pbg)]);
                return samples;
            }""")
            print("    contrast samples:", [(n, round(r, 2)) for n, r in contrast])
            check("contrast_4_5_body_samples", all(r >= 4.5 for _, r in contrast))

            # --- 地圖 ---
            await page.set_viewport_size({"width": 1280, "height": 800})
            await page.wait_for_timeout(300)
            svg_n = await page.eval_on_selector_all("#world-g8 path", "els => els.length")
            check("map_svg_11_paths", svg_n == 11, f"{svg_n} paths")
            labels = await page.eval_on_selector_all("#world-g8 text.map-lbl", "els => els.map(e => e.textContent)")
            check("map_labels_8_ccy", sorted(labels) == sorted(["USD","EUR","JPY","GBP","CHF","CAD","AUD","NZD"]), str(labels))
            map_mod_h = await page.eval_on_selector(".map-mod", "e => Math.round(e.getBoundingClientRect().height)")
            check("map_module_le_260", map_mod_h <= 260, f"{map_mod_h}px")
            map_hidden_390 = await page.evaluate("""async () => {
                await new Promise(r => setTimeout(r, 100));
                return true;
            }""")
            await page.set_viewport_size({"width": 390, "height": 844})
            map_disp = await page.eval_on_selector(".map-mod", "e => getComputedStyle(e).display")
            check("map_hidden_on_390", map_disp == "none", map_disp)
            strip_disp = await page.eval_on_selector(".strip-ph", "e => getComputedStyle(e).display")
            check("strip_visible_on_390", strip_disp != "none", strip_disp)

            # --- 健康燈 ---
            await page.set_viewport_size({"width": 1280, "height": 800})
            await page.goto(BASE + "index.html", wait_until="networkidle")
            await page.wait_for_timeout(800)
            pills = await page.eval_on_selector_all("#pills .pill", "els => els.length")
            check("health_pills_5", pills == 5, f"{pills} pills")
            st_when = await page.locator("#stWhen").inner_text()
            check("health_checked_at", "讀取中" not in st_when and len(st_when) > 5, st_when)
            r200 = [u for u, s in req_log if s != 200 and "favicon" not in u]
            check("zero_non200_requests", not r200, str(r200[:3]))

            # --- 1.2 上載 drawer（1280 桌面） ---
            await page.click("#uploadBtn")
            await page.wait_for_timeout(350)
            drawer_visible = await page.evaluate(
                "() => { const e = document.getElementById('uploadDrawer');"
                " return !e.hidden && e.getBoundingClientRect().x < window.innerWidth - 100; }")
            check("drawer_opens_200ms", drawer_visible)
            trans = await page.eval_on_selector("#uploadDrawer", "e => getComputedStyle(e).transitionDuration")
            check("drawer_transition_present", trans.startswith("0.2"), trans)
            zones = await page.evaluate("() => ['csvZone','setZone','csv2Zone','csvInput','setInput','csv2Input','fileChips'].every(id => !!document.getElementById(id))")
            check("upload_three_zones_ids", zones)
            status_in_drawer = await page.locator("#drawerStatus").inner_text()
            check("status_inside_drawer", status_in_drawer == "未選檔案", status_in_drawer)

            # 揀檔案（真 File 交接鏈）
            await page.set_input_files("#csvInput", "/tmp/phase1_files/trades_test.csv")
            await page.set_input_files("#setInput", "/tmp/phase1_files/ea_test.set")
            await page.wait_for_timeout(250)
            status2 = await page.locator("#drawerStatus").inner_text()
            check("status_updates_in_drawer", "1 份 CSV" in status2 and "1 份 SET" in status2, status2)
            chips = await page.eval_on_selector_all("#fileChips .fchip", "els => els.length")
            check("file_chips_2", chips == 2, f"{chips} chips")
            csv2_visible = await page.eval_on_selector("#csv2Zone", "e => !e.hidden")
            check("csv2zone_appears_after_csv", csv2_visible)
            # 揀第二份 CSV
            await page.set_input_files("#csv2Input", "/tmp/phase1_files/trades_test.csv")
            await page.wait_for_timeout(200)
            status3 = await page.locator("#drawerStatus").inner_text()
            check("status_csv2_added", "對比 CSV" in status3, status3)

            # analyze → overlay + iframe + postMessage 交接
            await page.click("#analyzeBtn")
            await page.wait_for_timeout(2500)
            overlay_shown = await page.eval_on_selector("#analyzerOverlay", "e => !e.hidden")
            check("analyzer_overlay_opens", overlay_shown)
            frame = None
            for f in page.frames:
                if f.url.endswith("analyzer.html"):
                    frame = f
            check("analyzer_iframe_loaded", frame is not None, str([f.url for f in page.frames]))
            if frame:
                az_chips = await frame.eval_on_selector_all("#fileChips .chip", "els => els.length")
                check("analyzer_received_files", az_chips >= 3, f"{az_chips} chips in analyzer")
                az_csv_label = await frame.locator("#csvZone .label").inner_text()
                check("analyzer_csv_zone_hasfile", az_csv_label == "trades_test.csv", az_csv_label)
            await page.click("#analyzerClose")
            await page.wait_for_timeout(200)

            # drawer 關閉
            await page.click("#drawerClose")
            await page.wait_for_timeout(300)
            drawer_closed = await page.eval_on_selector("#uploadDrawer", "e => e.hidden")
            check("drawer_closes", drawer_closed)

            # --- 手機：FAB 開 drawer ---
            await page.set_viewport_size({"width": 390, "height": 844})
            await page.wait_for_timeout(200)
            fab_vis = await page.eval_on_selector("#fab", "e => getComputedStyle(e).display")
            check("fab_visible_on_mobile", fab_vis != "none", fab_vis)
            await page.click("#fab")
            await page.wait_for_timeout(300)
            fab_drawer = await page.eval_on_selector("#uploadDrawer", "e => !e.hidden")
            check("fab_opens_drawer", fab_drawer)
            await page.click("#drawerClose")
            # 漢堡開導航
            await page.click("#burgerBtn")
            await page.wait_for_timeout(200)
            navdrawer_open = await page.eval_on_selector("#navDrawer", "e => !e.hidden")
            check("burger_opens_navdrawer", navdrawer_open)
            mlinks = await page.eval_on_selector_all(".navdrawer nav > a", "els => els.length")
            check("navdrawer_6_links_mobile", mlinks == 6)

            # --- chips 200 ---
            chip_hrefs = await page.eval_on_selector_all(".chips-row .chip", "els => els.map(e => e.getAttribute('href'))")
            check("chips_9_deep_links", len(chip_hrefs) == 9, str(chip_hrefs))
            chip_codes = []
            for href in chip_hrefs:
                r = await page.request.get(BASE + href)
                chip_codes.append((href, r.status))
            check("chips_all_http200", all(s == 200 for _, s in chip_codes), str(chip_codes))

            # --- reduced-motion CSS 在位 ---
            rm = await page.evaluate("""() => {
                let found=false;
                for(const sheet of document.styleSheets){
                    for(const rule of sheet.cssRules){
                        if(rule.media && /prefers-reduced-motion:\\s*reduce/.test(rule.media.mediaText)){found=true}
                    }
                }
                return found;
            }""")
            check("reduced_motion_css_present", rm)

            # --- bundle（明文） ---
            size = os.path.getsize("/home/z/my-project/exchange-repo/docs/index.html")
            check("plaintext_bundle_lt_90k", size < 90 * 1024, f"{size}B")

            # --- 截圖（1280 全頁＋首屏、390 全頁＋首屏） ---
            await page.set_viewport_size({"width": 1280, "height": 800})
            await page.goto(BASE + "index.html", wait_until="networkidle")
            await page.wait_for_timeout(500)
            await page.screenshot(path="/home/z/my-project/download/新首頁Phase1_1280全頁.png", full_page=True)
            await page.screenshot(path="/home/z/my-project/download/新首頁Phase1_1280首屏.png")
            await page.set_viewport_size({"width": 390, "height": 844})
            await page.wait_for_timeout(300)
            await page.screenshot(path="/home/z/my-project/download/新首頁Phase1_390全頁.png", full_page=True)
            await page.screenshot(path="/home/z/my-project/download/新首頁Phase1_390首屏.png")
            await browser.close()
    finally:
        server.send_signal(signal.SIGTERM)
        server.wait(timeout=5)

    n_ok = sum(1 for _, ok in RESULTS if ok)
    print(f"\n=== PHASE 1 明文態驗收 {n_ok}/{len(RESULTS)} ===")
    for name, ok in RESULTS:
        if not ok:
            print(f"  FAILED: {name}")
    sys.exit(0 if n_ok == len(RESULTS) else 1)

asyncio.run(main())
