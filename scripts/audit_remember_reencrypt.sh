#!/usr/bin/env bash
# audit_remember_reencrypt.sh — 1e7f7d9 remember-me 批量重加密內容完整性審計
# 對比每頁喺 parent(33a417b) vs worktree(HEAD) 嘅解密明文是否一致。
# 發現 docs/admin/index.html 被-shell-副本覆蓋（404 炸彈翻發）後寫。
set -uo pipefail
REPO=/home/z/my-project/exchange-repo
cd "$REPO"
PARENT=$(git rev-parse 1e7f7d9^)
PW_GENERAL=$(cat /home/z/my-project/.keys/tsa_pw_general.txt)
PW_OWNER=$(cat /home/z/my-project/.keys/tsa_pw_owner.txt)
TMP=/tmp/audit_1e7f7d9
rm -rf "$TMP"; mkdir -p "$TMP/old" "$TMP/new"

GENERAL_PAGES=(
  docs/admin/ccy_ranking.html docs/admin/forex_news.html docs/admin/index.html
  docs/admin/mfe_mae.html docs/admin/period_stats.html docs/admin/pivot_table.html
  docs/admin/signal_ranking.html docs/admin/symbol_ranking.html
  docs/admin/volatility.html docs/index.html docs/signal_ranking.html
  docs/signal_ranking_dde_v5.html
)
OWNER_PAGES=(
  docs/admin/db-browser.html docs/admin/tasks_board.html docs/admin/mt5_mcp_tools.html
)

audit_one() {
  local rel="$1" tier="$2" pw="$3" base
  base=$(echo "$rel" | tr '/' '_')
  git show "$PARENT:$rel" > "$TMP/old/$base" 2>/dev/null || { echo "MISSING_OLD $rel"; return; }
  cp "$rel" "$TMP/new/$base"
  if ! node scripts/staticrypt/decrypt_page.mjs "$TMP/old/$base" -p "$pw" -o "$TMP/old/$base.plain" >/dev/null 2>&1; then
    echo "DECRYPT_FAIL_OLD [$tier] $rel"; return
  fi
  if ! node scripts/staticrypt/decrypt_page.mjs "$TMP/new/$base" -p "$pw" -o "$TMP/new/$base.plain" >/dev/null 2>&1; then
    echo "DECRYPT_FAIL_NEW [$tier] $rel"; return
  fi
  if cmp -s "$TMP/old/$base.plain" "$TMP/new/$base.plain"; then
    echo "MATCH   [$tier] $rel ($(wc -c < "$TMP/new/$base.plain")B)"
  else
    echo "DIFFER  [$tier] $rel  old=$(wc -c < "$TMP/old/$base.plain")B new=$(wc -c < "$TMP/new/$base.plain")B"
  fi
}

for p in "${GENERAL_PAGES[@]}"; do audit_one "$p" general "$PW_GENERAL"; done
for p in "${OWNER_PAGES[@]}";   do audit_one "$p" owner   "$PW_OWNER";   done
echo "=== audit done ==="
