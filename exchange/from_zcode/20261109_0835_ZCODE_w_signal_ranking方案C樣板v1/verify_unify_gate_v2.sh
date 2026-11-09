#!/bin/bash
# verify_unify_gate_v2.sh — signal_ranking 方案C五閘（20261109_0805 加急派工 §三）
# 用法: bash verify_unify_gate_v2.sh docs/signal_ranking.html <pw檔>
# 閘1 topnav=0（方案C退役）｜閘2 sidebar-container=0（退役）｜閘3 tsa_tokens≥1
# 閘4 var(--font-main)≥1｜閘5 --card2≥1（家族標配）｜附加 Arial 硬編碼=0
set -u
PAGE="${1:?usage: verify_unify_gate_v2.sh <html> <pwfile>}"
PW="${2:?usage: verify_unify_gate_v2.sh <html> <pwfile>}"
REPO="$(cd "$(dirname "$0")/../../.." && pwd)"
DEC="/tmp/$(basename "$PAGE" .html)_gate_v2_plain.html"
cd "$REPO" || exit 1
node scripts/staticrypt/decrypt_page.mjs "$PAGE" -p "$(tr -d ' \r\n' < "$PW")" -o "$DEC" >/dev/null 2>&1
[ -s "$DEC" ] || { echo "DECRYPT-FAIL"; exit 2; }
pass=0
g1=$(grep -o "topnav" "$DEC" | wc -l)
g2=$(grep -o "sidebar-container" "$DEC" | wc -l)
g3=$(grep -o "tsa_tokens.css" "$DEC" | wc -l)
g4=$(grep -o 'var(--font-main)' "$DEC" | wc -l)
g5=$(grep -o -- "--card2" "$DEC" | wc -l)
ga=$(grep -o "Arial" "$DEC" | wc -l)
echo "閘1 topnav=0（方案C退役）: $g1 $([ "$g1" -eq 0 ] && echo ✓ || echo ✗)"; [ "$g1" -eq 0 ] && pass=$((pass+1))
echo "閘2 sidebar-container=0（退役）: $g2 $([ "$g2" -eq 0 ] && echo ✓ || echo ✗)"; [ "$g2" -eq 0 ] && pass=$((pass+1))
echo "閘3 tsa_tokens≥1: $g3 $([ "$g3" -ge 1 ] && echo ✓ || echo ✗)"; [ "$g3" -ge 1 ] && pass=$((pass+1))
echo "閘4 var(--font-main)≥1: $g4 $([ "$g4" -ge 1 ] && echo ✓ || echo ✗)"; [ "$g4" -ge 1 ] && pass=$((pass+1))
echo "閘5 --card2≥1（家族標配）: $g5 $([ "$g5" -ge 1 ] && echo ✓ || echo ✗)"; [ "$g5" -ge 1 ] && pass=$((pass+1))
echo "附加 Arial 硬編碼=0: $ga $([ "$ga" -eq 0 ] && echo ✓ || echo ✗)"; [ "$ga" -eq 0 ] && pass=$((pass+1))
rm -f "$DEC"
if [ "$pass" -eq 6 ]; then echo "GATE-GREEN: 方案C五閘+附加全綠"; exit 0; else echo "GATE-RED: $pass/6"; exit 1; fi
