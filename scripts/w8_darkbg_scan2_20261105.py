#!/usr/bin/env python3
# 暗調殘白掃描 v2 2026-11-05 (ZCODE_w) — 1848 派工定量, tag 語境分類
# 真兇類: A=css background(-color):#fff  B=<rect fill="#fff"> 圖表底  C=bgcolor="#fff"
# 保留類: <text fill="#fff">(彩色底白字=合法) / <circle stroke="#fff">(halo) / css color:#fff
import re, glob, os, json

ROOTS = {
    "reports":       "/home/z/my-project/exchange-repo/docs/reports/index_*.html",
    "forex_reports": "/home/z/my-project/exchange-repo/docs/forex_reports/index_*.html",
    "reviews":       "/home/z/my-project/exchange-repo/docs/reviews/*.html",
}

HEX = r"\#fff(?:fff)?(?![0-9a-fA-F])"
PAT_CSS_BG   = re.compile(r"background(?:-color)?\s*:\s*" + HEX, re.I)
PAT_BGATTR   = re.compile(r"bgcolor\s*=\s*[\"']?" + HEX, re.I)
# fill="#fff" with 80-char lookbehind to find owning tag
PAT_FILL     = re.compile(r'(<[a-zA-Z]+[^<>]{0,120})fill\s*=\s*["\']' + HEX, re.I)
PAT_STROKE   = re.compile(r'(<[a-zA-Z]+[^<>]{0,120})stroke\s*=\s*["\']' + HEX, re.I)

def classify_fill(m):
    tag = m.group(1).rsplit("<", 1)[-1].split("/")[0].strip().lower()
    return tag

summary = {}
samples = {}
for fam, pat in ROOTS.items():
    files = sorted(glob.glob(pat))
    tot = {"A_css_bg": 0, "B_rect_fill": 0, "C_bgattr": 0, "kept_text_fill": 0,
           "kept_other_fill": 0, "kept_stroke": 0, "kept_color": 0, "offender_files": 0}
    worst = []
    tagset = {}
    for f in files:
        s = open(f, encoding="utf-8", errors="replace").read()
        a = len(PAT_CSS_BG.findall(s))
        rects = 0; texts = 0; others = 0
        for m in PAT_FILL.finditer(s):
            t = classify_fill(m)
            tagset[t] = tagset.get(t, 0) + 1
            if t == "rect": rects += 1
            elif t == "text": texts += 1
            else: others += 1
        c = len(PAT_BGATTR.findall(s))
        k_stroke = len(PAT_STROKE.findall(s))
        k_color = len(re.findall(r"(?<![-\w])color\s*:\s*" + HEX, s, re.I))
        off = a + rects + c
        tot["A_css_bg"] += a; tot["B_rect_fill"] += rects; tot["C_bgattr"] += c
        tot["kept_text_fill"] += texts; tot["kept_other_fill"] += others
        tot["kept_stroke"] += k_stroke; tot["kept_color"] += k_color
        if off: tot["offender_files"] += 1; worst.append((os.path.basename(f), off))
    summary[fam] = tot | {"files": len(files)}
    summary[fam]["fill_tags_seen"] = tagset
    worst.sort(key=lambda x: -x[1])
    samples[fam] = worst[:6]

print(json.dumps(summary, indent=2, ensure_ascii=False))
for fam, ex in samples.items():
    print(f"\n=== {fam} 最重災頁 (真兇數) ===")
    for n, c in ex: print(f"  {n}: {c}")
