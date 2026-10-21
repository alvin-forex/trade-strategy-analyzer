#!/usr/bin/env bash
# L22 StatiCrypt anti-resurrection — re-encrypt the 14 core pages in place.
#
# Why: generators (generate_signal_ranking_v5.py 等) write PLAINTEXT to some
# of these paths. After any regeneration, run this script BEFORE commit+push;
# CI runs tests/encryption_check.py and goes red on plaintext (anti-resurrection).
#
# Usage:
#   bash scripts/encrypt_admin_pages.sh
# Env:
#   TSA_PW_FILE  password file (default /home/alvin/tsa_pw.txt) — NEVER commit
#                the password itself; only the path is referenced here.
# Requirements: npx (Node) — StatiCrypt CLI is fetched on demand.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PW_FILE="${TSA_PW_FILE:-/home/alvin/tsa_pw.txt}"

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
)

if [ ! -f "$PW_FILE" ]; then
  echo "ERR: password file not found: $PW_FILE (set TSA_PW_FILE to override)" >&2
  exit 1
fi
if ! command -v npx >/dev/null 2>&1; then
  echo "ERR: npx not found — install Node.js first" >&2
  exit 1
fi

PW="$(tr -d ' \r\n' < "$PW_FILE")"
if [ -z "$PW" ]; then
  echo "ERR: password file is empty: $PW_FILE" >&2
  exit 1
fi

TMP_DIR="$REPO_ROOT/.staticrypt-tmp"
trap 'rm -rf "$TMP_DIR"' EXIT

changed=0
skipped=0
failed=0

for rel in "${PAGES[@]}"; do
  f="$REPO_ROOT/$rel"
  if [ ! -f "$f" ]; then
    echo "SKIP (missing)  $rel"
    skipped=$((skipped + 1))
    continue
  fi
  # Idempotent: already-encrypted → leave untouched.
  if head -c 4096 "$f" | grep -qi "staticrypt"; then
    echo "OK   (already)  $rel"
    skipped=$((skipped + 1))
    continue
  fi

  rm -rf "$TMP_DIR"
  mkdir -p "$TMP_DIR"

  # Encrypt to a temp dir (output naming differs across staticrypt versions,
  # so we locate whatever *.html was produced and verify the marker).
  if ! (cd "$REPO_ROOT" && npx --yes staticrypt "$rel" -p "$PW" --output "$TMP_DIR" >/dev/null 2>&1); then
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

  mv "$produced" "$f"
  echo "ENC $rel"
  changed=$((changed + 1))
done

echo "-----------------------------"
echo "ENCRYPT_DONE changed=$changed skipped=$skipped failed=$failed"
[ "$failed" -eq 0 ] || exit 1
