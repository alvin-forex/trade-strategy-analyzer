#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批1 四頁 NAV 統一手術 — Job 505164 / 2100 批示（2026-11-07 晚）
===============================================================
老闆 2100：批1 四頁（forex_news / ccy_power / signal_ranking / projection）
全部打回——NAV 一律跟主站標準（docs/index.html 方案 C：48px sticky 六連結
＋漢堡 drawer），修完重交 8 截圖解鎖態。

本腳本錨定替換（計數斷言，一錨失手即 abort，唔寫半桶水檔）：
  P1 forex_news.html      拆 sidebar.css/js/container → 套標準 NAV（aria-current=新聞）
                          ＋.main 高度 60→108px 補償 nav 48px
  P2 ccy_power/index.html 拆 sidebar 三件 → 套標準 NAV（../ 前綴, aria-current=CCY）
                          ＋暗 palette 全套對齊 TSA tokens（#0f172a族→#0F1520族）
                          ＋ApexCharts 舊色字面值三點對齊
                          ＋body margin-left:260px 移除 ＋tsa_tokens.css 補鏈
  P3 projection.html      NAV 已係方案 C（11-04 P3）＋od 實證 navdrawer[hidden] selector
                          本正確（一度以為損壞＝讀檔顯示層食字假象）——一錨對齊：
                          body padding 補償令 nav 全出血＋padding 16→24px
  P4 signal_ranking.html  加密頁：解密（general 鎖）→拆 sidebar+topnav →套標準 NAV
                          （aria-current=排名）＋theme-toggle 右上重置
                          →deterministic 重加密（salt 2f5a…固定）→round-trip 驗證
"""
import subprocess, sys, shutil
from pathlib import Path

REPO = Path("/home/z/my-project/exchange-repo")
DOCS = REPO / "docs"
WORK = Path("/tmp/sr_work")
PW_FILE = Path("/home/z/my-project/.keys/tsa_pw.txt")
SALT = "2f5a7c9e1b3d4f6a8c0e2b4d6f8a1c3e"
TEMPLATE = REPO / "scripts/staticrypt/password_template_zh.html"
ENC = REPO / "scripts/staticrypt/encrypt_pages_deterministic.mjs"
DEC = REPO / "scripts/staticrypt/decrypt_page.mjs"

fails = []
def chk(cond, msg):
    print(("  [PASS] " if cond else "  [FAIL] ") + msg)
    if not cond: fails.append(msg)

def rep1(text, old, new, expect=1, tag=""):
    n = text.count(old)
    if n != expect:
        print(f"  [FAIL] 錨點計數 {tag}: 期望 {expect} 實得 {n}——中止該頁"); return None
    return text.replace(old, new)

# ---------------- 標準 NAV 三件套（主站 docs/index.html 方案 C）----------------
NAV_CSS = """/* ==== TSA 標準 NAV BAR 48px sticky（方案 C·主站 docs/index.html 同款；2026-11-07 批1 NAV 統一·2100 批示）==== */
.nav{position:sticky;top:0;z-index:50;display:flex;align-items:stretch;height:48px;background:#161E2E;border-bottom:1px solid #2A3650;padding:0 24px;overflow-x:auto;overflow-y:hidden}
.nav a{display:inline-flex;align-items:center;padding:0 12px;color:#A8B4C4;font-size:14px;font-weight:500;white-space:nowrap;text-decoration:none;border-bottom:2px solid transparent;transition:color .15s,border-color .15s}
.nav a:hover{color:#E6EDF5}
.nav a[aria-current="page"]{color:#5CA8FF;font-weight:700;border-bottom-color:#5CA8FF}
/* 漢堡全屏 drawer（手機；與桌面同一清單） */
.navdrawer{position:fixed;inset:0;z-index:220;background:rgba(10,14,22,.72);display:flex;flex-direction:column;align-items:stretch;justify-content:center;padding:32px}
.navdrawer[hidden]{display:none}
.navdrawer nav{display:flex;flex-direction:column;gap:8px;max-width:420px;margin:0 auto;width:100%}
.navdrawer a{display:flex;align-items:center;height:56px;padding:0 16px;background:#161E2E;border:1px solid #2A3650;border-radius:6px;color:#E6EDF5;font-size:16px;font-weight:500;text-decoration:none}
.navdrawer a[aria-current="page"]{color:#5CA8FF;font-weight:700;border-color:#5CA8FF}
.navdrawer-x{position:absolute;top:16px;right:16px;width:44px;height:44px;border:1px solid #2A3650;border-radius:6px;background:#161E2E;color:#E6EDF5;font-size:18px;cursor:pointer}
.burger{display:none}
@media (max-width:767px){
  .nav{display:none} /* 方案 C：手機 nav 唔出，漢堡負責 */
  .burger{display:block;position:fixed;top:8px;right:10px;z-index:60;width:40px;height:40px;border:1px solid #2A3650;border-radius:8px;background:#161E2E;color:#E6EDF5;font-size:18px;cursor:pointer}
}
"""

LINKS = [("index.html", "首頁"), ("signal_ranking.html", "排名"),
         ("forex_news.html", "新聞"), ("ccy_power/index.html", "CCY"),
         ("admin/tasks_board.html", "任務板"),
         ("tug_of_war_calculator.html", "工具")]

def nav_html(rel, current, self_href=None):
    """rel=前綴（root=''）ccy='../'；current=標準清單身份（self 頁嗰條嘅 canonical key）；
    self_href=自連結寫法（ccy_power 內頁自指 'index.html'，避免 ../ccy_power/index.html 繞圈）"""
    def a(h, l):
        if h == current and self_href:
            return f'<a href="{self_href}" aria-current="page">{l}</a>'
        c = ' aria-current="page"' if h == current else ""
        return f'<a href="{rel}{h}"{c}>{l}</a>'
    links = "".join(a(h, l) for h, l in LINKS)
    return ('<nav class="nav" aria-label="主導航">' + links + '</nav>\n'
            '<div id="navDrawer" class="navdrawer" hidden role="dialog" aria-modal="true" aria-label="導航選單">'
            '<button id="navDrawerClose" class="navdrawer-x" aria-label="關閉導航">✕</button>'
            '<nav aria-label="主導清單（手機）">' + links + '</nav></div>\n'
            '<button id="burgerBtn" class="burger" aria-label="開啟導航" aria-expanded="false">☰</button>')

DRAWER_JS = ("<script>(function(){var d=document.getElementById('navDrawer'),"
             "b=document.getElementById('burgerBtn'),x=document.getElementById('navDrawerClose');"
             "if(!d||!b||!x)return;var bar=[].map.call(document.querySelectorAll('.nav>a'),"
             "function(a){return a.getAttribute('href')});"
             "var dr=[].map.call(document.querySelectorAll('.navdrawer nav>a'),"
             "function(a){return a.getAttribute('href')});"
             "if(JSON.stringify(bar)!==JSON.stringify(dr))console.error('[nav] bar/drawer 清單唔一致',bar,dr);"
             "function open(){d.hidden=false;b.setAttribute('aria-expanded','true');x.focus()}"
             "function close(){d.hidden=true;b.setAttribute('aria-expanded','false');b.focus()}"
             "b.addEventListener('click',open);x.addEventListener('click',close);"
             "d.addEventListener('click',function(e){if(e.target===d)close()});"
             "document.addEventListener('keydown',function(e){if(e.key==='Escape'&&!d.hidden)close()});})();</script>")

# ================= P1 forex_news.html =================
print("== P1 forex_news.html ==")
p = DOCS / "forex_news.html"
t = p.read_text(encoding="utf-8")
t = rep1(t, '<link rel="stylesheet" href="sidebar.css">\n<link rel="stylesheet" href="tsa_tokens.css">',
         '<link rel="stylesheet" href="tsa_tokens.css">', 1, "S1 sidebar.css 拆除")
t = rep1(t, '<div id="sidebar-container"></div>', nav_html("", "forex_news.html"), 1, "S2 NAV 注入") if t else None
t = rep1(t, '<script src="sidebar.js"></script>', DRAWER_JS, 1, "S3 drawer JS") if t else None
t = rep1(t, '.main{display:flex;height:calc(100vh - 60px);overflow:hidden}',
         '.main{display:flex;height:calc(100vh - 108px);overflow:hidden}', 1, "S4 .main 高度補償") if t else None
t = rep1(t, '</style>', NAV_CSS + '</style>', 1, "S5 NAV CSS") if t else None
if t:
    p.write_text(t, encoding="utf-8")
    t2 = p.read_text(encoding="utf-8")
    chk(t2.count('<nav class="nav" aria-label="主導航">') == 1 and t2.count('主導清單（手機）') == 1, "P1 bar nav＋drawer nav 在位")
    chk(t2.count('<a href="forex_news.html" aria-current="page">') == 2,
        "P1 aria-current 落新聞×2（bar＋drawer）")
    chk('sidebar' not in t2, "P1 sidebar 引用全清")
    chk('href="tsa_tokens.css"' in t2, "P1 tsa_tokens.css 保留")
    chk('--bg:#0F1520' in t2, "P1 --bg:#0F1520 保留（過閘條件）")

# ================= P2 ccy_power/index.html =================
print("== P2 ccy_power/index.html ==")
p = DOCS / "ccy_power/index.html"
t = p.read_text(encoding="utf-8")
OLD_DARK = """        --bg: #0f172a; --bg-card: #1e293b; --bg-hover: #334155;
        --text: #f8fafc; --text2: #94a3b8;
        --primary: #60a5fa; --accent: #38bdf8;
        --green: #22c55e; --red: #ef4444; --yellow: #eab308; --orange: #f97316;
        --border: #334155; --shadow: rgba(0,0,0,0.3);"""
NEW_DARK = """        --bg: #0F1520; --bg-card: #161E2E; --bg-hover: #1C2638;
        --text: #E6EDF5; --text2: #A8B4C4;
        --primary: #5CA8FF; --accent: #38BDF8;
        --green: #22c55e; --red: #ef4444; --yellow: #eab308; --orange: #f97316;
        --border: #2A3650; --shadow: rgba(0,0,0,0.3);"""
t = rep1(t, OLD_DARK, NEW_DARK, 1, "S1 暗 palette 對齊")
t = rep1(t, '<link rel="stylesheet" href="../sidebar.css">',
         '<link rel="stylesheet" href="../tsa_tokens.css">', 1, "S2 sidebar.css→tsa_tokens.css") if t else None
t = rep1(t, '<div id="sidebar-container"></div>', nav_html("../", "ccy_power/index.html", self_href="index.html"), 1, "S3 NAV 注入(../)") if t else None
t = rep1(t, '<script src="../sidebar.js"></script>', DRAWER_JS, 1, "S4 drawer JS") if t else None
t = rep1(t, 'min-height: 100vh; margin-left: 260px; }', 'min-height: 100vh; }', 1, "S5 body margin-left 移除") if t else None
t = rep1(t, "    </style>", "    " + NAV_CSS.replace("\n", "\n    ").rstrip() + "\n    </style>", 1, "S6 NAV CSS") if t else None
# ApexCharts 舊色字面值三點（dark 分支）
t = rep1(t, "isDark?'#94a3b8':'#64748b'", "isDark?'#A8B4C4':'#64748b'", 3, "S7a 圖表 text2 ×3") if t else None
t = rep1(t, "axisBorder: {color: isDark?'#334155':'#e2e8f0'}", "axisBorder: {color: isDark?'#2A3650':'#e2e8f0'}", 1, "S7b 圖表 axisBorder") if t else None
t = rep1(t, "axisTicks: {color: isDark?'#334155':'#e2e8f0'}", "axisTicks: {color: isDark?'#2A3650':'#e2e8f0'}", 1, "S7c 圖表 axisTicks") if t else None
t = rep1(t, "grid: {borderColor:isDark?'#1e293b':'#f1f5f9'", "grid: {borderColor:isDark?'#161E2E':'#f1f5f9'", 1, "S7d 圖表 grid") if t else None
if t:
    p.write_text(t, encoding="utf-8")
    t2 = p.read_text(encoding="utf-8")
    chk(t2.count('<a href="index.html" aria-current="page">CCY</a>') == 2, "P2 aria-current 落 CCY×2")
    chk('../index.html">首頁' in t2 and '../signal_ranking.html">排名' in t2, "P2 ../ 前綴連結")
    chk('sidebar' not in t2, "P2 sidebar 引用全清")
    low = t2.lower()
    chk('#0f172a' not in low, "P2 舊 bg #0f172a 清零")
    chk('margin-left: 260px' not in t2, "P2 margin-left:260px 清零")
    chk(t2.count('<nav class="nav" aria-label="主導航">') == 1 and t2.count('主導清單（手機）') == 1, "P2 bar nav＋drawer nav 在位")
    chk('href="../tsa_tokens.css"' in t2, "P2 ../tsa_tokens.css 補鏈")

# ================= P3 projection.html（一錨對齊：body padding 補償令 nav 全出血，與主站/另三頁同一標準）=================
print("== P3 projection.html（nav 全出血對齊）==")
p = DOCS / "projection.html"
t = p.read_text(encoding="utf-8")
t = rep1(t, '.nav{position:sticky;top:0;z-index:50;display:flex;align-items:stretch;height:48px;background:#161E2E;border-bottom:1px solid #2A3650;padding:0 16px;overflow-x:auto;overflow-y:hidden}',
         '.nav{position:sticky;top:0;z-index:50;display:flex;align-items:stretch;height:48px;background:#161E2E;border-bottom:1px solid #2A3650;padding:0 24px;overflow-x:auto;overflow-y:hidden;margin:-24px -16px 24px}/* 批1標準對齊：body padding:24px 16px 補償→nav 全出血（主站同款）＋padding 16→24px */',
         1, "S1 nav 全出血＋24px padding")
if t:
    p.write_text(t, encoding="utf-8")
    t3 = p.read_text(encoding="utf-8")
    chk('.navdrawer[hidden]{display:none}' in t3, "P3 drawer selector 正確在位（先前「損壞」係讀檔顯示假象）")
    chk(t3.count('<nav class="nav"') == 1 and 'aria-label="主導航"' in t3, "P3 既有方案C nav 在位")
    chk('burgerBtn' in t3 and 'navDrawerClose' in t3, "P3 漢堡 drawer 三件在位")
    chk('margin:-24px -16px 24px' in t3 and 'padding:0 24px' in t3, "P3 全出血 margin＋24px padding 落地")

# ================= P4 signal_ranking.html（加密頁全流程）=================
print("== P4 signal_ranking.html（解密→手術→重加密→round-trip）==")
WORK.mkdir(parents=True, exist_ok=True)
pw = PW_FILE.read_text().strip()
plain = WORK / "signal_ranking.html"
r = subprocess.run(["node", str(DEC), str(DOCS / "signal_ranking.html"), "-p", pw,
                    "-o", str(plain)], capture_output=True, text=True, cwd=REPO)
chk(r.returncode == 0 and plain.exists(), "P4 解密（general 鎖）")
t = plain.read_text(encoding="utf-8")

# 錨點原文
TOPNAV_CSS = """.topnav{display:flex;align-items:center;gap:12px;padding:10px 16px;background:var(--bg-card);border-bottom:1px solid var(--border);margin-bottom:16px;position:sticky;top:0;z-index:100}
.topnav-logo{font-weight:700;font-size:1em;color:var(--primary);text-decoration:none;margin-right:auto}
.topnav-links{display:flex;gap:10px;flex-wrap:wrap}
.topnav-link{color:var(--text2);text-decoration:none;font-size:.88em;font-weight:600;padding:4px 10px;border-radius:6px;transition:all .2s}
.topnav-link:hover{color:var(--primary);background:var(--bg-hover)}
.topnav-link.active{color:var(--primary);background:var(--bg-hover)}
"""
TOPNAV_HTML = """<!-- 0805 缺陷補充（W2 併入）：NAV 四件之 #sidebar-container（sidebar.css/js 已在，此前缺 container 令 sidebar 永遠唔現） -->
<div id="sidebar-container"></div>
<div class="topnav">
<a href="./index.html" class="topnav-logo">🦀 TSA</a>
<div class="topnav-links">
<a href="./signal_ranking.html" class="topnav-link active">🏆 Signal 排名</a>
<a href="./ccy_ranking.html" class="topnav-link">💱 CCY 排名</a>
<a href="./symbol_ranking.html" class="topnav-link">📊 波幅波</a>
</div>
<button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()" title="切換亮/暗模式"></button>
</div>"""

SR_EXTRA_CSS = """/* signal_ranking 頁面適配：body padding:16px 補償（nav 全出血）＋主題切換掣右上重置（原頂欄內） */
.nav{margin:-16px -16px 16px}
.theme-toggle{position:fixed;top:8px;right:10px;z-index:60}
@media (max-width:767px){.theme-toggle{right:58px}}
"""

t = rep1(t, '<link rel="stylesheet" href="sidebar.css">\n', '', 1, "S1 sidebar.css 拆除")
t = rep1(t, TOPNAV_CSS, '', 1, "S2 topnav CSS 拆除") if t else None
t = rep1(t, TOPNAV_HTML,
         nav_html("", "signal_ranking.html") +
         '\n<button class="theme-toggle" id="theme-toggle" onclick="toggleTheme()" title="切換亮/暗模式"></button>',
         1, "S3 topnav→標準NAV＋toggle 重置") if t else None
t = rep1(t, '<script src="sidebar.js"></script>', DRAWER_JS, 1, "S4 drawer JS") if t else None
t = rep1(t, '</style>', NAV_CSS + SR_EXTRA_CSS + '</style>', 1, "S5 NAV CSS＋適配") if t else None
if t is None:
    print(f"SURGERY FAILED：P4 錨點失手"); sys.exit(1)
plain.write_text(t, encoding="utf-8")
t2 = plain.read_text(encoding="utf-8")
chk(t2.count('<nav class="nav" aria-label="主導航">') == 1 and t2.count('主導清單（手機）') == 1, "P4 bar nav＋drawer nav 在位")
chk(t2.count('<a href="signal_ranking.html" aria-current="page">') == 2,
    "P4 aria-current 落排名×2（bar＋drawer）")
chk('topnav' not in t2 and 'sidebar' not in t2, "P4 topnav/sidebar 全清")
chk('id="theme-toggle"' in t2 and 'href="tsa_tokens.css"' in t2, "P4 toggle 按鈕在位＋tokens 保留")
chk('--bg:#0F1520' in t2, "P4 --bg:#0F1520 保留")

# 重加密（deterministic：同明文+同密碼+同 salt）
enc_out = WORK / "newenc"
shutil.rmtree(enc_out, ignore_errors=True)
enc_out.mkdir()
r = subprocess.run(["node", str(ENC), str(plain), "-p", pw, "-d", str(enc_out),
                    "-s", SALT, "--remember", "30", "--template", str(TEMPLATE)],
                   capture_output=True, text=True, cwd=REPO)
enc_file = enc_out / "signal_ranking.html"
chk(r.returncode == 0 and enc_file.exists(), "P4 deterministic 重加密")
# round-trip：新密文解密 == 手術後明文
rt = WORK / "rt_plain.html"
r = subprocess.run(["node", str(DEC), str(enc_file), "-p", pw, "-o", str(rt)],
                   capture_output=True, text=True, cwd=REPO)
chk(r.returncode == 0 and rt.read_bytes() == plain.read_bytes(), "P4 round-trip byte-identical")
chk(enc_file.read_bytes() != (DOCS / "signal_ranking.html").read_bytes(), "P4 密文已變（內容有改）")
if not fails:
    shutil.copy(enc_file, DOCS / "signal_ranking.html")
    print("  [OK] docs/signal_ranking.html 已替換（密文）")
    head = (DOCS / "signal_ranking.html").read_text(errors="ignore")[:200]
    chk("staticrypt" in head.lower(), "P4 殼在位（staticrypt）")

print()
if fails:
    print(f"SURGERY FAILED：{len(fails)} 項"); [print("  -", f) for f in fails]; sys.exit(1)
print("ALL SURGERY PASS — 四頁手術完成")
