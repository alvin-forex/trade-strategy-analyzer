#!/usr/bin/env bash
# live_verify_admin_fix.sh — 等 Pages 部署後 sha256 對比線上 vs 本地修復檔
set -uo pipefail
LIVE="https://alvin-forex.github.io/trade-strategy-analyzer/admin/index.html"
LOCAL="/home/z/my-project/exchange-repo/docs/admin/index.html"
LOCAL_SHA=$(sha256sum "$LOCAL" | cut -d' ' -f1)
echo "local  sha256: $LOCAL_SHA"
for i in $(seq 1 18); do
  curl -sf -H "Cache-Control: no-cache" "$LIVE?v=$RANDOM" -o /tmp/live_admin.html
  if [ -s /tmp/live_admin.html ]; then
    LIVE_SHA=$(sha256sum /tmp/live_admin.html | cut -d' ' -f1)
    echo "live   sha256: $LIVE_SHA  (try $i, $(wc -c </tmp/live_admin.html)B)"
    if [ "$LIVE_SHA" = "$LOCAL_SHA" ]; then
      echo "LIVE_DEPLOYED_IDENTICAL ✅"
      exit 0
    else
      if rg -qi staticrypt /tmp/live_admin.html && [ "$(wc -c </tmp/live_admin.html)" -ne "$(wc -c <"$LOCAL")" ]; then
        echo "live 仍未部署新版（舊版 size=$(wc -c </tmp/live_admin.html) vs 本地 $(wc -c <"$LOCAL")）— 再等"
      fi
    fi
  fi
  sleep 15
done
echo "LIVE_VERIFY_TIMEOUT ❌（3 分鐘內 sha256 未一致）"
exit 1
