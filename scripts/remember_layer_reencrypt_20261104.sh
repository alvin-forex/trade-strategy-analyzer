#!/bin/bash
# remember_layer_reencrypt_20261104.sh — #31 跨頁密碼 remember 分層：7 頁旋轉重加密
# 規格：exchange/from_openclaw/20261104_1215_派工_跨頁密碼remember分層修復/
#       TSA_remember分層規格.md（老闆 11-04 11:38 裁決落地）
# 鏈式（同 fix_remember_4pages_20261031 標準）：殼檢查→解密入 /tmp staging→
# round-trip 原頁驗證→明文入工作區→批量重加密（deterministic zh＋remember 30
# ＋分層模板閘）→config/分層/殼/round-trip/CI encryption_check 五驗→由調用者
# 精準 add push
#
# 現狀基準（11-01 重組 34b49ae 後實數）：加密頁 7 頁（非派工時 15——收項明細見信）；
#   general 4：docs/index.html docs/signal_ranking.html docs/admin/index.html
#              docs/admin/projection.html
#   owner   3：docs/admin/db-browser.html docs/admin/tasks_board.html
#              docs/admin/mt5_mcp_tools.html
# 紅線：唔統一密碼（兩層制保留）；唔改 remember 天數（30）；唔改加密演算法；
#       deterministic salt 不變→同明文同密碼重加密→密文不變、只有殼 JS 分層化。
set -euo pipefail
cd /home/z/my-project/exchange-repo

PW_GENERAL=$(tr -d ' \r\n' < /home/z/my-project/.keys/tsa_pw_general.txt)
PW_OWNER=$(tr -d ' \r\n' < /home/z/my-project/.keys/tsa_pw_owner.txt)
STAGE=/tmp/remember_layer_20261104
rm -rf "$STAGE"; mkdir -p "$STAGE/orig_plain"

GENERAL_PAGES="docs/index.html docs/signal_ranking.html docs/admin/index.html docs/admin/projection.html"
OWNER_PAGES="docs/admin/db-browser.html docs/admin/tasks_board.html docs/admin/mt5_mcp_tools.html"
ALL_PAGES="$GENERAL_PAGES $OWNER_PAGES"

echo "== 1) 加密殼檢查（旋轉前）=="
for f in $ALL_PAGES; do
  head -c 200 "$f" | grep -qi staticrypt || { echo "❌ $f 唔係加密殼"; exit 1; }
done
echo "OK 7/7 殼在場"

echo "== 2) 解密入 staging＋--print round-trip 驗證 =="
for f in $GENERAL_PAGES; do
  node scripts/staticrypt/decrypt_page.mjs "$f" -p "$PW_GENERAL" -o "$STAGE/orig_plain/$(echo "$f" | tr "/" "_")" >/dev/null
  node scripts/staticrypt/decrypt_page.mjs "$f" -p "$PW_GENERAL" --print > /dev/null
done
for f in $OWNER_PAGES; do
  node scripts/staticrypt/decrypt_page.mjs "$f" -p "$PW_OWNER" -o "$STAGE/orig_plain/$(echo "$f" | tr "/" "_")" >/dev/null
  node scripts/staticrypt/decrypt_page.mjs "$f" -p "$PW_OWNER" --print > /dev/null
done
echo "OK 7 頁解密成功（兩層密碼正確）"

echo "== 3) 明文入工作區 =="
for f in $ALL_PAGES; do
  cp "$STAGE/orig_plain/$(echo "$f" | tr "/" "_")" "$f"
done

echo "== 4) 批量重加密（deterministic zh＋remember 30＋分層閘）=="
TSA_PW_FILE=/home/z/my-project/.keys/tsa_pw_general.txt \
TSA_OWNER_PW_FILE=/home/z/my-project/.keys/tsa_pw_owner.txt \
TSA_ST_REMEMBER=30 \
bash scripts/encrypt_admin_pages.sh

echo "== 5) 逐頁驗證：殼＋true/30＋分層 key＋無裸 key =="
for f in $ALL_PAGES; do
  head -c 200 "$f" | grep -qi staticrypt || { echo "❌ $f 殼唔在場"; exit 1; }
  r=$(grep -o 'isRememberEnabled":[a-z]*' "$f" | head -1)
  d=$(grep -o 'rememberDurationInDays":[0-9]*' "$f" | head -1)
  [ "$r" = 'isRememberEnabled":true' ] && [ "$d" = 'rememberDurationInDays":30' ] \
    || { echo "❌ $f config=$r $d"; exit 1; }
  grep -q 'rememberLayerSuffix' "$f" || { echo "❌ $f 無 rememberLayerSuffix"; exit 1; }
  grep -q '"_owner" : "_general"' "$f" || { echo "❌ $f 無分層分支"; exit 1; }
  for key in staticrypt_passphrase staticrypt_expiration; do
    t=$(grep -o "\"${key}\"" "$f" | wc -l)
    l=$(grep -o "\"${key}\" *+ *rememberLayerSuffix" "$f" | wc -l)
    [ "$t" -gt 0 ] && [ "$t" -eq "$l" ] || { echo "❌ $f 裸key $key t=$t l=$l"; exit 1; }
  done
  echo "OK $f $(wc -c < "$f")B true/30 分層在位"
done

echo "== 6) round-trip：新殼解密 vs 原明文 byte 一致 =="
for f in $ALL_PAGES; do
  case "$f" in *admin/*) pw="$PW_OWNER";; *) pw="$PW_GENERAL";; esac
  node scripts/staticrypt/decrypt_page.mjs "$f" -p "$pw" -o "$STAGE/new_plain_$(echo "$f" | tr "/" "_")" >/dev/null
  cmp -s "$STAGE/orig_plain/$(echo "$f" | tr "/" "_")" "$STAGE/new_plain_$(echo "$f" | tr "/" "_")" \
    || { echo "❌ $f round-trip 內容唔一致"; exit 1; }
  echo "OK $f round-trip byte-identical"
done

echo "== 7) CI encryption_check =="
python3 tests/encryption_check.py

echo "REMEMBER_LAYER_REENCRYPT_DONE 7/7 全綠"
