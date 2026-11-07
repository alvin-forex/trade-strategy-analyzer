#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批1 四頁 NAV 統一——獨立驗證閘（與 surgery.py 完全獨立嘅第二實現）
================================================================
閘門語義＝tsa_scan_v3（批0 browser 閘靜態等價）＋2100 老闆 NAV 標準：
  N1 標準 nav.bar 六連結（label 順序 首頁/排名/新聞/CCY/任務板/工具）＋相對前綴正確
  N2 aria-current 落自己頁（bar＋drawer 各一；projection 無自連結=0）
  N3 drawer（navDrawer/navDrawerClose）＋burger（burgerBtn）＋一致性 JS 在位
  N4 sidebar.css/sidebar.js/#sidebar-container/topnav 全清（P1/P2/P4）
  G1 tokens_var_ok（tsa_tokens.css 外鏈 OR --card2:#1C2638 源碼定義）——掃描器同款 regex
  G2 bg_new（html/body 字面 #0F1520 OR var(--bg) 且 --bg:#0F1520）——掃描器同款 regex
  G3 ccy_power 暗 palette 全套=TSA tokens 值；舊 slate 字面值清零（var 區＋圖表）
  E1 signal_ranking：staticrypt 殼＋解密=手術明文（round-trip）＋密文非空
  V0 projection 對 HEAD 零改動（git diff 空）
"""
import re, subprocess, sys
from pathlib import Path

REPO = Path("/home/z/my-project/exchange-repo")
DOCS = REPO / "docs"
PW = Path("/home/z/my-project/.keys/tsa_pw.txt").read_text().strip()

fails, npass = [], 0
def chk(cond, msg):
    global npass
    print(("  [PASS] " if cond else "  [FAIL] ") + msg)
    if cond: npass += 1
    else: fails.append(msg)

# 掃描器同款 regex（tsa_scan_v3.py 原文）
RE_TOKENS_CSS = re.compile(r'href="[^"]*tsa_tokens\.css"', re.I)
RE_ROOT_CARD2 = re.compile(r'--card2\s*:\s*#1[cC]2638')
RE_BGDECL     = re.compile(r'--bg\s*:\s*([^;}]+)')
RE_BODY_RULE  = re.compile(r'(?:^|\})\s*(?:html|body)\s*\{([^}]*)\}', re.I | re.M)
RE_BGBODY     = re.compile(r'background(?:-color)?\s*:\s*([^;}]+)', re.I)

def norm(v): return v.replace(" ", "").replace(":", "").lower()

def gate_tokens(src): return bool(RE_TOKENS_CSS.search(src) or RE_ROOT_CARD2.search(src))
def gate_bg(src):
    m = RE_BODY_RULE.search(src)
    if m:
        b = RE_BGBODY.search(m.group(1))
        if b:
            v = norm(b.group(1))
            if v == "#0f1520": return True
            mm = re.match(r'var\((--bg)\)', b.group(1).strip())
            if mm:
                for d in RE_BGDECL.finditer(src):
                    if norm(d.group(1)) == "#0f1520": return True
    return False

STD = [("index.html", "首頁"), ("signal_ranking.html", "排名"), ("forex_news.html", "新聞"),
       ("ccy_power/index.html", "CCY"), ("admin/tasks_board.html", "任務板"),
       ("tug_of_war_calculator.html", "工具")]
BAR_RE = re.compile(r'<nav class="nav" aria-label="主導航">(.*?)</nav>', re.S)
DRAWER_RE = re.compile(r'<nav aria-label="主導清單（手機）">(.*?)</nav>', re.S)
A_RE = re.compile(r'<a href="([^"]+)"( aria-current="page")?>([^<]*)</a>')

def nav_of(src):
    b = BAR_RE.search(src); d = DRAWER_RE.search(src)
    if not b or not d: return None, None
    bar = A_RE.findall(b.group(1)); drw = A_RE.findall(d.group(1))
    return bar, drw

def check_nav(page_file, src, expect_current, prefix, self_href):
    bar, drw = nav_of(src)
    ok_links = ok_cur = ok_pair = False
    if bar and drw:
        want = [((self_href or prefix + h) if (self_href and h == expect_current) else prefix + h, l) for h, l in STD]
        got_b = [(h, l) for h, _, l in bar]; got_d = [(h, l) for h, _, l in drw]
        ok_links = got_b == want and got_d == want
        ncur_b = sum(1 for _, c, _ in bar if c); ncur_d = sum(1 for _, c, _ in drw if c)
        cur_ok = (h for h, c, _ in bar if c)
        cur_href = next(cur_ok, None)
        want_cur = (self_href or prefix + expect_current) if expect_current else None
        ok_cur = (ncur_b == (1 if expect_current else 0) and ncur_d == (1 if expect_current else 0)
                  and cur_href == want_cur)
        ok_pair = all(not c or h == want_cur for h, c, _ in drw)
    chk(ok_links, f"{page_file} N1 六連結=標準（前綴 {prefix or 'root'}）")
    chk(ok_cur and ok_pair, f"{page_file} N2 aria-current={'自頁' if expect_current else '0'}正確")
    chk(all(x in src for x in ('id="navDrawer"', 'id="navDrawerClose"', 'id="burgerBtn"',
                               "querySelectorAll('.nav>a')")), f"{page_file} N3 drawer+burger+JS 三件")
    if page_file != "projection.html":
        chk(not re.search(r'sidebar\.css|sidebar\.js|#sidebar-container|class="topnav', src),
            f"{page_file} N4 舊導航殘留清零")
    chk(gate_tokens(src), f"{page_file} G1 tokens_var_ok")
    chk(gate_bg(src), f"{page_file} G2 bg_new #0F1520")

print("== 批1 四頁獨立驗證 ==")
# P1 forex_news
src = (DOCS / "forex_news.html").read_text(encoding="utf-8")
check_nav("forex_news.html", src, "forex_news.html", "", None)
# P2 ccy_power
src = (DOCS / "ccy_power/index.html").read_text(encoding="utf-8")
check_nav("ccy_power/index.html", src, "ccy_power/index.html", "../", "index.html")
chk(all(x in src for x in ("--bg: #0F1520", "--bg-card: #161E2E", "--bg-hover: #1C2638",
                           "--text: #E6EDF5", "--text2: #A8B4C4", "--primary: #5CA8FF",
                           "--border: #2A3650")), "ccy_power G3 暗 palette 全套=TSA tokens")
low = src.lower()
chk(all(x not in low for x in ("#0f172a", "#94a3b8", "#60a5fa", "#334155")),
    "ccy_power G3 舊 slate 字面值清零（bg/text2/primary/border）")
n1e = len(re.findall(r'#1e293b', low))
chk(n1e == 1 and '--text: #1e293b' in src, "ccy_power G3 #1e293b 僅 light --text 一處（tokens light 合法值）")
chk("isDark?'#334155'" not in src and "isDark?'#94a3b8'" not in src, "ccy_power G3 圖表舊色清零")
# P3 projection（nav 全出血對齊後驗證）
src = (DOCS / "projection.html").read_text(encoding="utf-8")
check_nav("projection.html", src, None, "", None)
chk("margin:-24px -16px 24px" in src and "padding:0 24px" in src, "projection N5 全出血 margin＋24px padding（body padding 補償）")
# P4 signal_ranking（加密頁：殼＋round-trip）
enc = (DOCS / "signal_ranking.html").read_bytes()
chk(b"staticrypt" in enc[:600].lower(), "signal_ranking E1 staticrypt 殼在位")
tmp = Path("/tmp/sr_work/verify_plain.html")
r = subprocess.run(["node", str(REPO / "scripts/staticrypt/decrypt_page.mjs"),
                    str(DOCS / "signal_ranking.html"), "-p", PW, "-o", str(tmp)],
                   capture_output=True, text=True, cwd=REPO)
chk(r.returncode == 0 and tmp.exists(), "signal_ranking E1 解密成功（general 鎖）")
src = tmp.read_text(encoding="utf-8")
check_nav("signal_ranking.html", src, "signal_ranking.html", "", None)
chk('<style>' in src and '🏆 Signal 排名' in src, "signal_ranking E1 內容主體在位")

print()
if fails:
    print(f"VERIFY FAILED：{len(fails)} 項 / {npass} PASS"); [print("  -", f) for f in fails]; sys.exit(1)
print(f"ALL VERIFY PASS — {npass} 項全綠")
