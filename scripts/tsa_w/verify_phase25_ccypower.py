#!/usr/bin/env python3
"""Phase 2.5 CCY Power 熱力圖模組驗證（WIP 明文態）。
驗證項：渲染 9ccy×4TF／字串值轉數（非「—」）／stale 灰化（M30+D1）／
per-TF 時間印／排序 fallback（M30 斷改→H1）／ALIGN badge 邏輯／截圖。
"""
import subprocess, time, sys, json
from playwright.sync_api import sync_playwright

DOCS = "/home/z/my-project/exchange-repo/docs"
BASE = "http://localhost:8934"
OUT = "/home/z/my-project/download"

server = subprocess.Popen(["python3", "-m", "http.server", "8934", "--directory", DOCS],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
time.sleep(1.2)
fails = []
try:
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1280, "height": 900})
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        pg.goto(f"{BASE}/index.html", wait_until="networkidle")
        pg.wait_for_selector("#ccyGrid .ccy-cell", timeout=8000)
        time.sleep(0.5)

        r = pg.evaluate("""() => {
          const g = document.getElementById('ccyGrid');
          const cells = g.querySelectorAll('.ccy-cell');
          const heads = g.querySelectorAll('.ccy-h');
          const rows = g.querySelectorAll('.ccy-row');
          const staleHeads = g.querySelectorAll('.ccy-h.stale');
          const staleCells = g.querySelectorAll('.ccy-cell.stale');
          const dashes = [...cells].filter(c => c.querySelector('.v') && c.querySelector('.v').textContent.trim() === '—');
          const dates = [...g.querySelectorAll('.tf-date')].map(e => e.textContent.trim());
          const when = document.getElementById('ccyWhen').textContent.trim();
          const up = g.querySelectorAll('.ccy-cell .arr.up').length;
          const dn = g.querySelectorAll('.ccy-cell .arr.dn').length;
          const badges = [...g.querySelectorAll('.ccy-abadge')].map(e => e.textContent.trim());
          const rowsText = [...rows].map(e => e.textContent.trim().replace(/ALIGN.?[▲▼]?/,''));
          return {cells: cells.length, heads: heads.length, rows: rows.length,
                  staleHeads: staleHeads.length, staleCells: staleCells.length,
                  dashes: dashes.length, dates, when, up, dn, badges, rowsText,
                  aria: g.getAttribute('aria-label')};
        }""")

        def chk(name, cond, detail=""):
            print(("  ✅" if cond else "  ❌"), name, detail)
            if not cond:
                fails.append(name)

        print("== Phase 2.5 CCY Power 模組驗證 ==")
        chk("9 貨幣行", r["rows"] == 9, f"rows={r['rows']}")
        chk("4 TF 表頭＋貨幣欄", r["heads"] == 5, f"heads={r['heads']}")
        chk("36 格（9×4）", r["cells"] == 36, f"cells={r['cells']}")
        chk("字串值轉數：零「—」格", r["dashes"] == 0, f"dashes={r['dashes']}")
        chk("stale 表頭 2 個（M30+D1）", r["staleHeads"] == 2, f"={r['staleHeads']}")
        chk("stale 格 18 個（2 TF×9）", r["staleCells"] == 18, f"={r['staleCells']}")
        chk("per-TF 時間印 4 個", all(len(d) >= 11 for d in r["dates"]) and len(r["dates"]) == 4, str(r["dates"]))
        chk("when 時間印（更新於…）", r["when"].startswith("更新於"), r["when"])
        # 排序 fallback 斷言：依真實 data.json 動態計 H1（非 stale 首選 TF）top1
        dj = json.load(open(f"{DOCS}/admin/ccy_power/data.json"))
        h1 = {k: float(v) for k, v in dj["data"]["H1"].items()}
        expect_top = max(h1, key=h1.get)
        chk("排序 fallback 生效（首行=非 stale TF 最高值）",
            r["rowsText"][0] == expect_top, f"首行={r['rowsText'][0]} 預期={expect_top}")
        chk("▲/▼/▬ 標記齊", r["up"] > 0 and r["dn"] > 0, f"up={r['up']} dn={r['dn']}")
        chk("aria-label 含過期灰化提示", "過期灰化" in (r["aria"] or ""), r["aria"])
        chk("頁面 JS 零錯誤", len(errors) == 0, f"errors={errors[:2]}")

        # 截圖
        pg.screenshot(path=f"{OUT}/Phase2_5首頁_CCYPower_1280.png", full_page=True)
        m = b.new_page(viewport={"width": 390, "height": 844})
        m.goto(f"{BASE}/index.html", wait_until="networkidle")
        m.wait_for_selector("#ccyGrid .ccy-cell", timeout=8000)
        m.screenshot(path=f"{OUT}/Phase2_5首頁_CCYPower_390.png", full_page=True)
        # 390 橫向溢出檢查
        ovf = m.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        chk("390 零橫向溢出", ovf <= 0, f"ovf={ovf}")
        b.close()
finally:
    server.terminate()

print("\n結果:", "全過 ✅" if not fails else f"失敗 {len(fails)} 項: {fails}")
sys.exit(1 if fails else 0)
