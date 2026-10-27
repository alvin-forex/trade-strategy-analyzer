#!/usr/bin/env bash
# L22 StatiCrypt anti-resurrection — re-encrypt the 15 core pages in place.
#
# Why: generators (generate_signal_ranking_v5.py 等) write PLAINTEXT to some
# of these paths. After any regeneration, run this script BEFORE commit+push;
# CI runs tests/encryption_check.py and goes red on plaintext (anti-resurrection).
# 任務G (2026-10-25): switched CLI→deterministic wrapper. Same content + same
# password + same salt → byte-identical ciphertext → zero git-diff noise.
# A pre-push hook (scripts/hooks/pre-push) also blocks plaintext from leaving
# the machine — install it per clone (not version-controlled) with:
#   cp scripts/hooks/pre-push .git/hooks/pre-push && chmod +x .git/hooks/pre-push
#
# Usage:
#   bash scripts/encrypt_admin_pages.sh
# Env:
#   TSA_PW_FILE  password file (default /home/alvin/tsa_pw.txt) — NEVER commit
#                the password itself; only the path is referenced here.
#   TSA_ST_SALT  optional override of the fixed salt (32 hex chars)
# Requirements: node (>=18) + scripts/staticrypt/ (StatiCrypt 3.5.4 unpacked,
#               source: exchange/from_openclaw/20261025_0719_staticrypt_supply/) —
#               no network, no npx, zero npm install.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PW_FILE="${TSA_PW_FILE:-/home/alvin/tsa_pw.txt}"

# 任務G deterministic salt — 32 hex, NOT a secret (embedded in each page's
# staticrypt_config, same as StatiCrypt CLI does). Fixed so that re-encrypting
# unchanged content yields identical bytes. Changing it re-encrypts everything
# and invalidates remember-me sessions.
ST_SALT="${TSA_ST_SALT:-2f5a7c9e1b3d4f6a8c0e2b4d6f8a1c3e}"

WRAPPER="scripts/staticrypt/encrypt_pages_deterministic.mjs"

PAGES=(
  "docs/admin/ccy_ranking.html"
  "docs/admin/db-browser.html"
  "docs/admin/forex_news.html"
  "docs/admin/index.html"
  "docs/admin/mfe_mae.html"
  "docs/admin/mt5_mcp_tools.html"
  "docs/admin/period_stats.html"
  "docs/admin/pivot_table.html"
  "docs/admin/signal_ranking.html"
  "docs/admin/symbol_ranking.html"
  "docs/admin/tasks_board.html"
  "docs/admin/volatility.html"
  "docs/index.html"
  "docs/signal_ranking.html"
  # L22b (老闆裁決 2026-10-21「統一其他就好」): the 98-signal DDE v5 page.
  # Encrypted copy committed at d0e58013; CI gate (tests/encryption_check.py)
  # flipped 14→15 alongside the --output→-d fix in this script.
  "docs/signal_ranking_dde_v5.html"
)

TMP_DIR="$REPO_ROOT/.staticrypt-tmp"
trap 'rm -rf "$TMP_DIR"' EXIT

changed=0
skipped=0
failed=0
todo=()

# Pass 1 — classify (no password needed): missing / already encrypted / todo.
for rel in "${PAGES[@]}"; do
  f="$REPO_ROOT/$rel"
  if [ ! -f "$f" ]; then
    echo "SKIP (missing)  $rel"
    skipped=$((skipped + 1))
  elif head -c 4096 "$f" | grep -qi "staticrypt"; then
    echo "OK   (already)  $rel"
    skipped=$((skipped + 1))
  else
    todo+=("$rel")
  fi
done

# Pass 2 — encrypt only what needs it. Password + node are required lazily, so
# a nothing-to-do run (e.g. all pages already locked) succeeds without a
# password file; this keeps hook/cron/CI dry contexts safe.
if [ "${#todo[@]}" -gt 0 ]; then
  if [ ! -f "$PW_FILE" ]; then
    echo "ERR: password file not found: $PW_FILE (set TSA_PW_FILE to override)" >&2
    exit 1
  fi
  if ! command -v node >/dev/null 2>&1; then
    echo "ERR: node not found — install Node.js (>=18) first" >&2
    exit 1
  fi
  PW="$(tr -d ' \r\n' < "$PW_FILE")"
  if [ -z "$PW" ]; then
    echo "ERR: password file is empty: $PW_FILE" >&2
    exit 1
  fi
  if [ ! -f "$REPO_ROOT/$WRAPPER" ]; then
    echo "ERR: wrapper not found: $REPO_ROOT/$WRAPPER" >&2
    echo "     unpack staticrypt-3.5.4.tgz to scripts/staticrypt/ first (see 說明.md)" >&2
    exit 1
  fi

  for rel in "${todo[@]}"; do
    rm -rf "$TMP_DIR"
    mkdir -p "$TMP_DIR"
    # 任務G wrapper — same CLI interface (-p/-d), plus mandatory -s salt.
    # Deterministic: identical input → identical output file, so re-runs on
    # already-encrypted content produce zero git diff. Self-verifies via the
    # original codec.decode() before writing; exits non-zero on any failure.
    if ! (cd "$REPO_ROOT" && node "$WRAPPER" "$rel" -p "$PW" -d "$TMP_DIR" -s "$ST_SALT" --template "$REPO_ROOT/scripts/staticrypt/password_template_zh.html" >/dev/null 2>&1); then
      echo "FAIL (staticrypt)  $rel" >&2
      failed=$((failed + 1))
      continue
    fi

    produced="$(find "$TMP_DIR" -name '*.html' -type f | head -1)"
    if [ -z "$produced" ] || ! grep -qi "staticrypt" "$produced"; then
      echo "FAIL (no output)   $rel" >&2
      failed=$((failed + 1))
      continue
    fi

    mv "$produced" "$REPO_ROOT/$rel"
    echo "ENC $rel"
    changed=$((changed + 1))
  done
fi

echo "-----------------------------"
echo "ENCRYPT_DONE changed=$changed skipped=$skipped failed=$failed"
[ "$failed" -eq 0 ] || exit 1
