#!/bin/bash
# fix_remember_4pages_20261031.sh — remember-me 4 頁修復（false/0 → true/30）
# 標準鏈（同 97f3238 修復）：殼檢查→解密入 /tmp staging→round-trip 原頁驗證→
# 明文入工作區→批量重加密（deterministic dark＋remember 30）→config/殼/round-trip/
# encryption_check 四驗→由調用者精準 add push
set -euo pipefail
cd /home/z/my-project/exchange-repo

PW=$(tr -d ' \r\n' < /home/z/my-project/.keys/tsa_pw_general.txt)
PAGES="docs/admin/ccy_ranking.html docs/admin/signal_ranking.html docs/signal_ranking.html docs/signal_ranking_dde_v5.html"
STAGE=/tmp/remember4_20261031
rm -rf "$STAGE"; mkdir -p "$STAGE/orig_plain"

echo "== 1) 加密殼檢查（修復前）=="
for f in $PAGES; do
  if ! head -c 200 "$f" | grep -qi staticrypt; then echo "❌ $f 唔係加密殼"; exit 1; fi
done
echo "OK 4/4 殼在場"

echo "== 2) 解密入 staging＋round-trip 原頁驗證 =="
for f in $PAGES; do
  node scripts/staticrypt/decrypt_page.mjs "$f" -p "$PW" -o "$STAGE/orig_plain/$(basename $f)"
  node scripts/staticrypt/decrypt_page.mjs "$f" -p "$PW" --print > /dev/null
done
echo "OK 4 頁解密成功（密碼正確）"

echo "== 3) 明文入工作區 =="
for f in $PAGES; do
  cp "$STAGE/orig_plain/$(basename $f)" "$f"
done
ls -la $PAGES | awk '{print $5, $9}'

echo "== 4) 批量重加密（deterministic dark＋remember 30）=="
TSA_PW_FILE=/home/z/my-project/.keys/tsa_pw_general.txt \
TSA_OWNER_PW_FILE=/home/z/my-project/.keys/tsa_pw_owner.txt \
TSA_ST_TEMPLATE=scripts/staticrypt/password_template_dark.html \
TSA_ST_REMEMBER=30 \
bash scripts/encrypt_admin_pages.sh

echo "== 5) config 驗證 true/30 ×4 ＋ 殼檢查 =="
for f in $PAGES; do
  r=$(grep -o 'isRememberEnabled":[a-z]*' "$f" | head -1)
  d=$(grep -o 'rememberDurationInDays":[0-9]*' "$f" | head -1)
  [ "$r" = 'isRememberEnabled":true' ] && [ "$d" = 'rememberDurationInDays":30' ] || { echo "❌ $f config=$r $d"; exit 1; }
  head -c 200 "$f" | grep -qi staticrypt || { echo "❌ $f 殼唔在場"; exit 1; }
  echo "OK $f true/30 殼在場 $(wc -c < $f)B"
done

echo "== 6) round-trip：解密新殼 vs 原明文 byte 一致 =="
for f in $PAGES; do
  node scripts/staticrypt/decrypt_page.mjs "$f" -p "$PW" -o "$STAGE/rt_$(basename $f)"
  cmp -s "$STAGE/rt_$(basename $f)" "$STAGE/orig_plain/$(basename $f)" || { echo "❌ $f round-trip 唔一致"; exit 1; }
  echo "OK $f round-trip byte 一致"
done

echo "== 7) encryption_check 15/15 =="
python3 tests/encryption_check.py

echo "ALL PASS — 可精準 add push"
