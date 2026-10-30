#!/usr/bin/env python3
"""審計 docs/ 所有頁面 + staticrypt 模板嘅簡體字（系統文字只可用英文或繁體中文）"""
import sys, re, glob, os
from opencc import OpenCC

REPO = '/home/z/my-project/exchange-repo'
cc = OpenCC('s2t')
# 合法繁體/粵語用字（OpenCC 會誤判，唔當簡體）：台(平台) 晒(睇晒) 游(游標) 群(群組) 准(批准)
FALSE_POS = set('台晒游群准')

# 只抽 HTML/JS 入面嘅文字（連 tag 屬性都掃，因為 aria-label、title 都係系統文字）
FILES = []
for pat in ['docs/*.html', 'docs/**/*.html', 'scripts/staticrypt/password_template_*.html']:
    FILES += glob.glob(os.path.join(REPO, pat))
FILES = sorted(set(os.path.realpath(f) for f in FILES))

def scan(text):
    """回傳 {簡體字: [行號...]} 及 總數"""
    hits = {}
    total = 0
    for i, line in enumerate(text.split('\n'), 1):
        for ch in line:
            if '\u4e00' <= ch <= '\u9fff' and cc.convert(ch) != ch and ch not in FALSE_POS:
                hits.setdefault(ch, []).append(i)
                total += 1
    return hits, total

report = []
for f in FILES:
    rel = os.path.relpath(f, REPO)
    try:
        text = open(f, encoding='utf-8', errors='replace').read()
    except Exception as e:
        report.append((rel, 'READ_ERR', str(e)))
        continue
    hits, total = scan(text)
    if total:
        chars = ' '.join(f"{ch}(x{len(ls)})" for ch, ls in sorted(hits.items(), key=lambda x: -len(x[1]))[:25])
        first_lines = sorted(set(l for ls in hits.values() for l in ls))[:8]
        report.append((rel, total, f"chars: {chars} | lines: {first_lines}"))

print(f"掃描 {len(FILES)} 個檔案\n" + '=' * 70)
n_bad = 0
for rel, total, info in report:
    if total != 'READ_ERR' and total:
        n_bad += 1
        print(f"\n[簡體] {rel}: {total} 字")
        print(f"  {info}")
if n_bad == 0:
    print("全部乾淨，無簡體字")
