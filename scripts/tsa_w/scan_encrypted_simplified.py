#!/usr/bin/env python3
"""解密全部 staticrypt 頁面 → 掃描明文簡體字（系統文字只可用英文或繁體中文）"""
import os, subprocess, sys
from opencc import OpenCC

REPO = '/home/z/my-project/exchange-repo'
TMP = '/tmp/simp_scan'
DECRYPT = os.path.join(REPO, 'scripts/staticrypt/decrypt_page.mjs')
PW_GENERAL = open('/home/z/my-project/.keys/tsa_pw_general.txt').read().strip()
PW_OWNER = open('/home/z/my-project/.keys/tsa_pw_owner.txt').read().strip()
cc = OpenCC('s2t')

GENERAL = ['docs/admin/ccy_ranking.html', 'docs/admin/forex_news.html', 'docs/admin/index.html',
           'docs/admin/mfe_mae.html', 'docs/admin/period_stats.html', 'docs/admin/pivot_table.html',
           'docs/admin/signal_ranking.html', 'docs/admin/symbol_ranking.html',
           'docs/admin/volatility.html', 'docs/index.html', 'docs/signal_ranking.html',
           'docs/signal_ranking_dde_v5.html']
OWNER = ['docs/admin/db-browser.html', 'docs/admin/tasks_board.html', 'docs/admin/mt5_mcp_tools.html']

# 已判定為合法繁體/粵語用法嘅字（唔當簡體處理）：台(平台) 晒(睇晒) 游(游標) 群(群組) 准(批准)
FALSE_POS = set('台晒游群准')

def scan_text(text):
    hits = {}
    for i, line in enumerate(text.split('\n'), 1):
        for ch in line:
            if '\u4e00' <= ch <= '\u9fff' and cc.convert(ch) != ch and ch not in FALSE_POS:
                hits.setdefault(ch, []).append(i)
    return hits

os.makedirs(TMP, exist_ok=True)
n_files = n_bad = 0
for rel, pw in [(p, PW_GENERAL) for p in GENERAL] + [(p, PW_OWNER) for p in OWNER]:
    n_files += 1
    src = os.path.join(REPO, rel)
    out = os.path.join(TMP, rel.replace('/', '_') + '.plain')
    r = subprocess.run(['node', DECRYPT, src, '-p', pw, '-o', out],
                       capture_output=True, text=True, cwd=REPO)
    if r.returncode != 0:
        print(f"DECRYPT_FAIL {rel}")
        continue
    text = open(out, encoding='utf-8', errors='replace').read()
    hits = scan_text(text)
    if hits:
        n_bad += 1
        print(f"\n[簡體] {rel} ({os.path.getsize(out)}B 明文):")
        for ch, lines in sorted(hits.items(), key=lambda x: -len(x[1])):
            samples = []
            all_lines = text.split('\n')
            for ln in sorted(set(lines))[:2]:
                seg = all_lines[ln - 1].strip()
                # 抽出含該字前後 ~40 字
                idx = seg.find(ch)
                samples.append(f"L{ln}: …{seg[max(0,idx-25):idx+30]}…")
            print(f"  {ch} x{len(lines)}  " + ' | '.join(samples))
print(f"\n=== 掃描 {n_files} 頁，含簡體 {n_bad} 頁 ===")
