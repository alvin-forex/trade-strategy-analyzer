#!/usr/bin/env bash
# verify_unify_gate.sh — signal_ranking 統一件防復活四閘（2026-11-08 ZCODE_w 出貨）
# 用法: bash verify_unify_gate.sh [加密頁路徑] [general 密碼檔]
#   預設: docs/signal_ranking.html ＋ /home/z/my-project/.keys/tsa_pw_general.txt
# 四閘: topnav≥1 / tsa_tokens≥1 / font-family 含 var(--font-main) / 零 Arial 硬編碼
# 出處: from_zcode/20261108_1645_ZCODE_w_signal_ranking驗屍報告_生成器鏈/manifest.md
set -uo pipefail
PAGE="${1:-docs/signal_ranking.html}"
PWFILE="${2:-/home/z/my-project/.keys/tsa_pw_general.txt}"
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$REPO" || exit 1
TMP="$(mktemp /tmp/unify_gate_XXXX.html)"
trap 'rm -f "$TMP"' EXIT

# ① 解密（頁已明文則直接用）
if grep -q "staticryptConfig" "$PAGE" 2>/dev/null; then
  PW="$(tr -d ' \r\n' < "$PWFILE")"
  node scripts/staticrypt/decrypt_page.mjs "$PAGE" -p "$PW" -o "$TMP" >/dev/null 2>&1 || {
    echo "GATE-ERROR: 解密失敗（$PAGE）"; exit 2; }
else
  cp "$PAGE" "$TMP" || { echo "GATE-ERROR: 頁唔存在（$PAGE）"; exit 2; }
fi

fail=0
# ② 四閘
c_nav=$(grep -c "topnav" "$TMP" || true)
c_tok=$(grep -c "tsa_tokens\.css" "$TMP" || true)
c_fm=$(grep -cE "font-family:[^;}]*var\(--font-main\)" "$TMP" || true)
c_arial=$(grep -ciE "font-family:[^;}]*[\"']?Arial" "$TMP" || true)
echo "閘1 topnav=$c_nav（需≥1）"
echo "閘2 tsa_tokens=$c_tok（需≥1）"
echo "閘3 var(--font-main)=$c_fm（需≥1）"
echo "閘4 Arial 硬編碼=$c_arial（需=0）"
[ "$c_nav" -ge 1 ] && [ "$c_tok" -ge 1 ] && [ "$c_fm" -ge 1 ] && [ "$c_arial" -eq 0 ] || fail=1
[ "$fail" -eq 0 ] && echo "GATE-GREEN: 統一件四閘全綠" || echo "GATE-RED: 統一件受損——生成器 patch 需要落刀"
exit "$fail"
