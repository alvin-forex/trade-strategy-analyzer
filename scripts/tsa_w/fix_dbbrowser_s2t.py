#!/usr/bin/env python3
"""db-browser.html 簡轉繁修復：解密→OpenCC s2t→審閱 diff→輸出定明文"""
import os, subprocess, sys
from opencc import OpenCC

REPO = '/home/z/my-project/exchange-repo'
DECRYPT = os.path.join(REPO, 'scripts/staticrypt/decrypt_page.mjs')
SRC = os.path.join(REPO, 'docs/admin/db-browser.html')
PW = open('/home/z/my-project/.keys/tsa_pw_owner.txt').read().strip()
OUTDIR = '/tmp/dbfix'
cc = OpenCC('s2t')

os.makedirs(OUTDIR, exist_ok=True)
orig_plain = os.path.join(OUTDIR, 'db-browser.orig.html')
fixed_plain = os.path.join(OUTDIR, 'db-browser.fixed.html')

# 1) 解密
r = subprocess.run(['node', DECRYPT, SRC, '-p', PW, '-o', orig_plain],
                   capture_output=True, text=True, cwd=REPO)
assert r.returncode == 0, f"decrypt fail: {r.stderr[:300]}"
text = open(orig_plain, encoding='utf-8').read()
print(f"解密 OK: {len(text)}B")

# 2) s2t 轉換（只動中文字符，ASCII code/identifiers 唞氣都唔掂）
converted = cc.convert(text)

# 3) 保護已知合法繁體/粵語用字（本頁無呢啲字，保險起見照查）
for keep in ['群', '台', '游', '晒', '准']:
    if keep in text and keep in converted:
        pass  # 只審閱，唔自動回滾——睇 diff 決定

# 4) 寫出
open(fixed_plain, 'w', encoding='utf-8').write(converted)

# 5) diff 摘要：列出行級變化
import difflib
n_changed = 0
samples = []
for line in difflib.unified_diff(text.split('\n'), converted.split('\n'), lineterm='', n=0):
    if line.startswith(('---', '+++', '@@')):
        continue
    n_changed += 1
    if len(samples) < 60:
        samples.append(line[:150])
print(f"行級變化: {n_changed} 行")
print('\n'.join(samples))
print(f"\nfixed plaintext: {fixed_plain} ({os.path.getsize(fixed_plain)}B)")

# 6) 殘餘簡體檢查
left = {}
for ch in converted:
    if '\u4e00' <= ch <= '\u9fff' and cc.convert(ch) != ch and ch not in set('台晒游群准'):
        left[ch] = left.get(ch, 0) + 1
print(f"殘餘簡體字: {left if left else '無'}")
