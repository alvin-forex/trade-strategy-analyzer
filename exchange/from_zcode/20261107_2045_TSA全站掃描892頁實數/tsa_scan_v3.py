#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TSA 全站頁面機器掃描 v3（終版）— Job 505164 / Task a
閘門語義＝批0 browser 閘（html/body bg=rgb(15,21,32) AND --card2=#1C2638）靜態等價：
  tokens_var_ok = tsa_tokens.css 外鏈 OR 源碼 --card2:#1C2638 定義
  bg_new       = html/body 背景字面 #0F1520 OR var(--bg) 且 --bg 定義=#0F1520
另解析 W5 注入註釋（tokens 豁免＝W5-C v3.9 裁定）同 browser 實測覆核結果。
分類桶：A過閘 B半程缺tokenvar C bg微差/舊/透明 D light豁免族 E自帶palette F舊工具 G admin內部 H待刪G4
"""
import os, re, csv, argparse, urllib.parse
from pathlib import Path
from collections import Counter, defaultdict

# v3.1（2026-11-08 應 OpenClaw 0740 信附註）：REPO/OUT 參數化，預設值不變——其他框可用 --repo/--out 指自己路徑
def _parse_args():
    ap = argparse.ArgumentParser(description="TSA 全站頁面機器掃描 v3.1")
    ap.add_argument("--repo", default="/home/z/my-project/exchange-repo/exchange",
                    help="repo exchange 子樹路徑（預設機房框路徑）")
    ap.add_argument("--out", default="/home/z/my-project/scripts/scan_out",
                    help="掃描輸出目錄（預設機房框路徑）")
    return ap.parse_args()

_ARGS = _parse_args()
REPO = Path(_ARGS.repo)
DOCS = REPO / "docs"
OUT = Path(_ARGS.out)
DEC = OUT / "decrypted"
OUT.mkdir(parents=True, exist_ok=True)   # v3.1：--out 指到新目錄都直接跑
DEC.mkdir(parents=True, exist_ok=True)

GENERAL_LOCK = {"index.html", "signal_ranking.html"}
OWNER_LOCK   = {"admin/tasks_board.html", "admin/index.html", "admin/db-browser.html", "admin/mt5_mcp_tools.html"}
DECRYPTED = {}
for rel in GENERAL_LOCK:
    d = DEC / rel.replace("/", "_")
    if d.exists(): DECRYPTED[rel] = d
for rel in OWNER_LOCK:
    d = DEC / rel.replace("/", "_")
    if d.exists(): DECRYPTED[rel] = d
d = DEC / "admin_index_try2.html"
if d.exists(): DECRYPTED["admin/index.html"] = d

RE_CANONICAL   = re.compile(r'<link\s+rel="canonical"', re.I)
RE_NAV_MARK    = re.compile(r'<nav[\s>]|topnav|#sidebar-container', re.I)
RE_SIDEBAR_CSS = re.compile(r'href="[^"]*sidebar\.css"', re.I)
RE_TOKENS_CSS  = re.compile(r'href="[^"]*tsa_tokens\.css"', re.I)
RE_ROOT_CARD2  = re.compile(r'--card2\s*:\s*#1[cC]2638')
RE_W5_COMMENT  = re.compile(r'W5-[A-Z]（[^）]*）：(NAV[^<]*?)</', re.I)
RE_EXEMPT      = re.compile(r'tokens\s*豁免')
RE_BGDECL      = re.compile(r'--bg\s*:\s*([^;}]+)')
RE_BODY_RULE   = re.compile(r'(?:^|\})\s*(?:html|body)\s*\{([^}]*)\}', re.I)
RE_BGBODY      = re.compile(r'background(?:-color)?\s*:\s*([^;}]+)', re.I)

def norm(v):
    return v.replace(" ", "").replace(":", "").lower()

def family_of(rel):
    top = rel.split("/")[0] if "/" in rel else "(root)"
    return {"(root)": "root"}.get(top, top)

SUBF = [
    ("SignalDeep", re.compile(r'^Signal_Deep_Analysis_\d+\.html$')),
    ("index_deep", re.compile(r'^index_\d+\.html$')),
    ("signal",     re.compile(r'^signal_\d+\.html$')),
    ("martin_v4",  re.compile(r'^martin_v4_\d+\.html$')),
    ("dca",        re.compile(r'^detailed_comparison_all_levels_\d+\.html$')),
    ("martin_auto",re.compile(r'^martin_autopsy_v3(_\d+)?\.html$')),
    ("date_range", re.compile(r'^date_range_review')),
    ("anomaly",    re.compile(r'^anomaly_report\.html$')),
    ("sample_red", re.compile(r'^sample_redesign_\d+\.html$')),
    ("forex_daily",re.compile(r'^2026-\d\d-\d\d_(morning|evening)\.html$')),
    ("monthly",    re.compile(r'^monthly/')),
    ("weekly",     re.compile(r'^weekly/')),
    ("admin_cat",  re.compile(r'^ccy_auto_trader/')),
]
def subfamily_of(name):
    for tag, rex in SUBF:
        if rex.search(name): return tag
    return "other"

def wfinal_batch(rel):
    if rel in ("signal_ranking.html", "forex_news.html", "ccy_power/index.html", "projection.html"):
        return "批1"
    fam = family_of(rel)
    if fam == "reports":          return "批2"
    if fam == "forex_reports":    return "批3"
    if fam in ("ccy", "reviews"): return "批4"
    if fam in ("portfolios", "admin", "ccy_power"): return "批5"
    if fam == "root":             return "批0已測root補漏"
    return "?"

def w5_scope(rel):
    fam, name = family_of(rel), Path(rel).name
    if fam == "ccy": return "W5B"
    sf = subfamily_of(name)
    if sf == "SignalDeep": return "W5C"
    if sf == "index_deep": return "W5D"
    if sf == "signal":     return "W5E"
    if sf == "date_range": return "W5F"
    if fam == "portfolios": return "W5G"
    if fam == "ccy_power" and name != "index.html": return "W5H"
    if fam == "admin" and "/" not in rel: return "W5I"
    return ""

def classify(rel, txt):
    tokens_css  = bool(RE_TOKENS_CSS.search(txt))
    card2_var   = bool(RE_ROOT_CARD2.search(txt))
    tokens_ok   = tokens_css or card2_var
    exempt      = bool(RE_EXEMPT.search(txt))

    # --bg 定義值
    bgdefs = [m.group(1).strip() for m in RE_BGDECL.finditer(txt)]
    bgdef_new   = any(norm(v) in ("#0f1520",) for v in bgdefs)
    bgdef_light = any(norm(v) in ("#f5f7fa", "#ffffff", "#f1f5f9") for v in bgdefs)
    bgdef_172a  = any(norm(v) == "#0f172a" for v in bgdefs)
    bgdef_olddk = any(norm(v) in ("#0a0e1a", "#0a0e17", "#0d1117") for v in bgdefs)

    # html/body 背景
    body_bg_new = body_bg_var = body_bg_172a = body_bg_olddk = body_bg_light = body_bg_none = False
    rules = RE_BODY_RULE.findall(txt)
    for rule in rules:
        for m in RE_BGBODY.finditer(rule):
            v = m.group(1).strip()
            n = norm(v)
            if "var(--bg)" in n:
                body_bg_var = True
            elif n.startswith("#0f1520") or n.startswith("rgb(15,21,32") or n.startswith("#0f1520"):
                body_bg_new = True
            elif n.startswith("#0f172a") or n.startswith("rgb(15,23,42"):
                body_bg_172a = True
            elif n.startswith("#0a0e") or n.startswith("#0d1117") or n.startswith("rgb(10,14"):
                body_bg_olddk = True
            elif n.startswith("#f5f7fa") or n.startswith("#f1f5f9") or n in ("#fff", "white", "#ffffff"):
                body_bg_light = True
    bg_new = body_bg_new or (body_bg_var and bgdef_new and tokens_ok) or (body_bg_var and bgdef_new)

    fam = family_of(rel)
    name = Path(rel).name

    if rel == "reports/sample_redesign_36912.html":
        return "H_待刪G4", tokens_ok, exempt
    if fam == "admin":
        return "G_admin內部工具加密", tokens_ok, exempt
    if bg_new and tokens_ok:
        return "A_過閘", tokens_ok, exempt
    if (body_bg_light or bgdef_light) and exempt:
        return "D_light豁免族", tokens_ok, exempt
    if bgdef_olddk or body_bg_olddk:
        return ("E_自帶palette深" if exempt else "C_bg舊深"), tokens_ok, exempt
    if bgdef_172a or body_bg_172a:
        return "C_bg172A微差", tokens_ok, exempt
    if bg_new and not tokens_ok:
        return "B_半程缺tokenvar", tokens_ok, exempt
    if body_bg_var and bgdef_light:
        return "D_light豁免族", tokens_ok, exempt
    if body_bg_light or bgdef_light:
        return ("F_舊工具light" if not exempt else "D_light豁免族"), tokens_ok, exempt
    if not rules or body_bg_var:
        return ("C_bg透明缺" if tokens_ok else ("D_light豁免族" if exempt else "F_舊工具light")), tokens_ok, exempt
    return ("B_半程缺tokenvar" if bg_new else "F_舊工具light"), tokens_ok, exempt

rows = []
allpages = []
for dirpath, dirnames, filenames in os.walk(DOCS):
    dirnames.sort()
    for fn in sorted(filenames):
        if fn.endswith(".html"):
            allpages.append(os.path.relpath(os.path.join(dirpath, fn), DOCS))
allpages.sort()

# browser 實測結果（本鐘 12 頁）
browser = {}
RAWF = OUT / "browser_verify_raw.txt"
if RAWF.exists():
    for line in RAWF.read_text().strip().splitlines():
        pg, rest = line.split("|", 1)
        vals = [urllib.parse.unquote(v) for v in rest.split("|")]
        browser[pg] = vals  # htmlBg, bodyBg, card2, accent, bodyClass, hasNav, hasSidebar, h1

for rel in allpages:
    src = DECRYPTED.get(rel, DOCS / rel)
    txt = src.read_text(encoding="utf-8", errors="replace") if src.exists() else ""
    cls, tokens_ok, exempt = classify(rel, txt)
    bt = browser.get(rel) or browser.get("_zscan_" + Path(rel).name)
    rows.append({
        "page": rel, "family": family_of(rel), "subfamily": subfamily_of(Path(rel).name),
        "wfinal_batch": wfinal_batch(rel), "w5": w5_scope(rel),
        "templateA_index族": "Y" if subfamily_of(Path(rel).name) == "index_deep" else "",
        "final_class": cls,
        "tokens_var_ok": "Y" if tokens_ok else "", "w5_exempt註釋": "Y" if exempt else "",
        "encrypted_shell": "Y" if rel in DECRYPTED else "",
        "tsa_tokens_css": "Y" if RE_TOKENS_CSS.search(txt) else "",
        "sidebar_css": "Y" if RE_SIDEBAR_CSS.search(txt) else "",
        "nav_markup": "Y" if RE_NAV_MARK.search(txt) else "",
        "canonical": "Y" if RE_CANONICAL.search(txt) else "",
        "browser_verified": "Y" if bt else "",
        "browser_bodyBg": bt[1] if bt else "", "browser_card2": bt[2] if bt else "",
        "bytes": ((src.stat().st_size if src.exists() else ((DOCS / rel).stat().st_size if (DOCS / rel).exists() else 0))),
    })

if not rows:
    print(f"[v3.1] DOCS 無 .html 頁（{DOCS}）——稀疏 clone 冇 docs/ 子樹？請用 --repo 指向有 docs/ 嘅完整 checkout 後再跑。")
    raise SystemExit(2)

with open(OUT / "tsa_census_final.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)

cls_cnt = Counter(r["final_class"] for r in rows)
batch_cls = defaultdict(Counter)
for r in rows:
    batch_cls[r["wfinal_batch"]][r["final_class"]] += 1
sf_cls = defaultdict(Counter)
for r in rows:
    sf_cls[r["subfamily"]][r["final_class"]] += 1

print(f"TOTAL {len(rows)}")
print("\n=== 終版分類 ===")
for k, v in sorted(cls_cnt.items()):
    print(f"  {k:<22} {v}")
print("\n=== 批次 × 分類 ===")
for b in ["批1", "批2", "批3", "批4", "批5", "批0已測root補漏"]:
    print(f"  {b:<14} total={sum(batch_cls[b].values()):<4} {dict(batch_cls[b])}")
print("\n=== subfamily × 分類 ===")
for sf, c in sorted(sf_cls.items()):
    print(f"  {sf:<14} total={sum(c.values()):<4} {dict(c)}")

# 未達標點名清單（B/C/D/E/F/G/H；A 除外）
BAD = ("B_半程缺tokenvar", "C_bg172A微差", "C_bg舊深", "C_bg透明缺",
       "D_light豁免族", "E_自帶palette深", "F_舊工具light", "G_admin內部工具加密", "H_待刪G4")
bad = [r for r in rows if r["final_class"] in BAD]
print(f"\n★ 未達 W-FINAL 深頁標準：{len(bad)} 頁")
with open(OUT / "not_fixed_final.txt", "w", encoding="utf-8") as f:
    for r in sorted(bad, key=lambda x: (x["wfinal_batch"], x["page"])):
        f.write(f"{r['wfinal_batch']}\t{r['final_class']}\t{r['w5'] or '-'}\t{r['page']}\n")
print("saved not_fixed_final.txt")
