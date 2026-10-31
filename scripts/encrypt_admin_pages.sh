#!/usr/bin/env bash
# L22 StatiCrypt anti-resurrection — re-encrypt the 15 core pages in place.
#
# Why: generators (generate_signal_ranking_v5.py 等) write PLAINTEXT to some
# of these paths. After any regeneration, run this script BEFORE commit+push;
# CI runs tests/encryption_check.py and goes red on plaintext (anti-resurrection).
# 任務G (2026-10-25): switched CLI→deterministic wrapper. Same content + same
# password + same salt → byte-identical ciphertext → zero git-diff noise.
#
# 兩層制 (老闆裁決 2026-10-28「兩層密碼，都係防君子」):
#   general 層 — 12 頁，密碼檔 TSA_PW_FILE（一般報告/分析頁）
#   owner   層 —  db-browser / tasks_board / mt5_mcp_tools 三頁，
#                 密碼檔 TSA_OWNER_PW_FILE（主人專屬頁）
#   密碼本身 NEVER commit；只有路徑被引用。轉換注意：本腳本只會加密
#   plaintext 頁（already-encrypted 會 SKIP）——已用舊單層密碼鎖住的頁要
#   轉新層密碼，需在有舊密碼的機器上一次性 decrypt→re-encrypt（旋轉流程）
#   或由 generator 重出 plaintext 後再行本腳本。
# A pre-push hook (scripts/hooks/pre-push) also blocks plaintext from leaving
# the machine — install it per clone (not version-controlled) with:
#   cp scripts/hooks/pre-push .git/hooks/pre-push && chmod +x .git/hooks/pre-push
#
# Usage:
#   bash scripts/encrypt_admin_pages.sh
# Env:
#   TSA_PW_FILE        general 層 password file (default /home/alvin/tsa_pw.txt)
#   TSA_OWNER_PW_FILE  owner   層 password file (default /home/alvin/tsa_pw_owner.txt)
#                      — NEVER commit the passwords themselves; only paths here.
#   TSA_ST_SALT  optional override of the fixed salt (32 hex chars)
#   TSA_ST_REMEMBER  remember-me days. 老闆裁決 2026-10-30「開」→ 預設改 **30**
#                    （2026-10-30 12:5x ZCODE_w 定案：每日 05:30 重生成 4 頁
#                    false/0 回歸嘅根因＝生成器行本腳本時漏傳 env；預設直接
#                    對齊老闆裁決，OpenClaw 排程側零改動。傳 0 可顯式關閉。）
# Requirements: node (>=18) + scripts/staticrypt/ (StatiCrypt 3.5.4 unpacked,
#               source: exchange/from_openclaw/20261025_0719_staticrypt_supply/) —
#               no network, no npx, zero npm install.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PW_FILE="${TSA_PW_FILE:-/home/alvin/tsa_pw.txt}"
OWNER_PW_FILE="${TSA_OWNER_PW_FILE:-/home/alvin/tsa_pw_owner.txt}"
# Phase 1 1.4（TSA 新首頁 v1.1）：密碼頁模板可用 env 換——
#   TSA_ST_TEMPLATE=scripts/staticrypt/password_template_dark.html （深色 tokens 版，新首頁用）
# 預設 zh 白底版唔變（其他 14 頁照舊）。
ST_TEMPLATE="${TSA_ST_TEMPLATE:-scripts/staticrypt/password_template_zh.html}"

# 任務G deterministic salt — 32 hex, NOT a secret (embedded in each page's
# staticrypt_config, same as StatiCrypt CLI does). Fixed so that re-encrypting
# unchanged content yields identical bytes. Changing it re-encrypts everything
# and invalidates remember-me sessions.
ST_SALT="${TSA_ST_SALT:-2f5a7c9e1b3d4f6a8c0e2b4d6f8a1c3e}"
ST_REMEMBER="${TSA_ST_REMEMBER:-30}"

WRAPPER="scripts/staticrypt/encrypt_pages_deterministic.mjs"

PAGES=(
  "docs/admin/ccy_ranking.html"
  "docs/admin/forex_news.html"
  "docs/admin/index.html"
  "docs/admin/mfe_mae.html"
  "docs/admin/period_stats.html"
  "docs/admin/pivot_table.html"
  "docs/admin/signal_ranking.html"
  "docs/admin/symbol_ranking.html"
  "docs/admin/volatility.html"
  "docs/index.html"
  "docs/signal_ranking.html"
  # L22b (老闆裁決 2026-10-21「統一其他就好」): the 98-signal DDE v5 page.
  # Encrypted copy committed at d0e58013; CI gate (tests/encryption_check.py)
  # flipped 14→15 alongside the --output→-d fix in this script.
  "docs/signal_ranking_dde_v5.html"
)

# 兩層制 owner 頁（老闆裁決 2026-10-28）：只有主人看，獨立密碼。
OWNER_PAGES=(
  "docs/admin/db-browser.html"
  "docs/admin/tasks_board.html"
  "docs/admin/mt5_mcp_tools.html"
)

TMP_DIR="$REPO_ROOT/.staticrypt-tmp"
trap 'rm -rf "$TMP_DIR"' EXIT

changed=0
skipped=0
failed=0
todo_general=()
todo_owner=()

# Pass 1 — classify (no password needed): missing / already encrypted / todo.
# $1 = tier tag (general|owner), $2 = array name (nameref — bash 4.3+).
classify_tier() {
  local tier="$1"
  local -n pages="$2"
  local rel f
  for rel in "${pages[@]}"; do
    f="$REPO_ROOT/$rel"
    if [ ! -f "$f" ]; then
      echo "SKIP (missing)  $rel"
      skipped=$((skipped + 1))
    elif head -c 4096 "$f" | grep -qi "staticrypt"; then
      echo "OK   (already)  $rel"
      skipped=$((skipped + 1))
    elif [ "$tier" = "owner" ]; then
      todo_owner+=("$rel")
    else
      todo_general+=("$rel")
    fi
  done
}
classify_tier general PAGES
classify_tier owner OWNER_PAGES

# Pass 2 — encrypt only what needs it. Password + node are required lazily, so
# a nothing-to-do run (e.g. all pages already locked) succeeds without a
# password file; this keeps hook/cron/CI dry contexts safe.
encrypt_page() {
  # $1 = tier tag, $2 = rel path, $3 = password
  local tier="$1" rel="$2" pw="$3"
  rm -rf "$TMP_DIR"
  mkdir -p "$TMP_DIR"
  # 任務G wrapper — same CLI interface (-p/-d), plus mandatory -s salt.
  # Deterministic: identical input → identical output file, so re-runs on
  # already-encrypted content produce zero git diff. Self-verifies via the
  # original codec.decode() before writing; exits non-zero on any failure.
  if ! (cd "$REPO_ROOT" && node "$WRAPPER" "$rel" -p "$pw" -d "$TMP_DIR" -s "$ST_SALT" --remember "$ST_REMEMBER" --template "$REPO_ROOT/$ST_TEMPLATE" >/dev/null 2>&1); then
    echo "FAIL (staticrypt)  $rel" >&2
    failed=$((failed + 1))
    return
  fi

  local produced
  produced="$(find "$TMP_DIR" -name '*.html' -type f | head -1)"
  if [ -z "$produced" ] || ! grep -qi "staticrypt" "$produced"; then
    echo "FAIL (no output)   $rel" >&2
    failed=$((failed + 1))
    return
  fi

  # v3.7 後置閘（回應 OpenClaw 1130 信第二節建議，2026-10-31 落地）：
  # 加密輸出嘅 staticryptConfig 實值必須等於本次 --remember——唔等＝env 漏傳／
  # 靜默降級（10-30 05:30 tsa-ranking-daily 4 頁 true/30→false/0 事故同類），即 FAIL
  local want_en="false" want_days="0"
  [ "$ST_REMEMBER" -gt 0 ] && { want_en="true"; want_days="$ST_REMEMBER"; }
  if ! grep -q "\"isRememberEnabled\":${want_en}" "$produced" \
     || ! grep -q "\"rememberDurationInDays\":${want_days}" "$produced"; then
    echo "FAIL (remember cfg want $want_en/$want_days)  $rel" >&2
    failed=$((failed + 1))
    return
  fi

  mv "$produced" "$REPO_ROOT/$rel"
  echo "ENC ($tier)  $rel"
  changed=$((changed + 1))
}

if [ "${#todo_general[@]}" -gt 0 ] || [ "${#todo_owner[@]}" -gt 0 ]; then
  if ! command -v node >/dev/null 2>&1; then
    echo "ERR: node not found — install Node.js (>=18) first" >&2
    exit 1
  fi
  if [ ! -f "$REPO_ROOT/$WRAPPER" ]; then
    echo "ERR: wrapper not found: $REPO_ROOT/$WRAPPER" >&2
    echo "     unpack staticrypt-3.5.4.tgz to scripts/staticrypt/ first (see 說明.md)" >&2
    exit 1
  fi

  if [ "${#todo_general[@]}" -gt 0 ]; then
    if [ ! -f "$PW_FILE" ]; then
      echo "ERR: general password file not found: $PW_FILE (set TSA_PW_FILE to override)" >&2
      exit 1
    fi
    PW_GENERAL="$(tr -d ' \r\n' < "$PW_FILE")"
    if [ -z "$PW_GENERAL" ]; then
      echo "ERR: general password file is empty: $PW_FILE" >&2
      exit 1
    fi
    for rel in "${todo_general[@]}"; do
      encrypt_page general "$rel" "$PW_GENERAL"
    done
  fi

  if [ "${#todo_owner[@]}" -gt 0 ]; then
    if [ ! -f "$OWNER_PW_FILE" ]; then
      echo "ERR: owner password file not found: $OWNER_PW_FILE (set TSA_OWNER_PW_FILE to override)" >&2
      exit 1
    fi
    PW_OWNER="$(tr -d ' \r\n' < "$OWNER_PW_FILE")"
    if [ -z "$PW_OWNER" ]; then
      echo "ERR: owner password file is empty: $OWNER_PW_FILE" >&2
      exit 1
    fi
    for rel in "${todo_owner[@]}"; do
      encrypt_page owner "$rel" "$PW_OWNER"
    done
  fi
fi

echo "-----------------------------"
echo "ENCRYPT_DONE changed=$changed skipped=$skipped failed=$failed"
[ "$failed" -eq 0 ] || exit 1
