#!/usr/bin/env bash
# =============================================================================
# L28 watchdog_retry.sh 回歸測試（CI golden job 步驟,2026-10-22）
#
#   背景: OpenClaw 項 2 核驗發現失敗命令嘅 rc 傳遞失真——
#         last_error 永遠記錄 exit=0(真實 rc 係 3)。
#         根因: rc=$? 放喺無 else 嘅 if...fi 之後,捕捉到 if 命令
#         自身嘅 0,唔係被執行命令嘅退出碼。
#
#   驗證五項:
#     1. 用法守衛 — 缺標籤／缺 -- → exit 2
#     2. 成功路徑 — 首試即成 → exit 0,state ok / attempts=1 / last_error 空
#     3. 失敗路徑 — 5 次退避(1→2→4→8s)後觸頂 → exit 1,
#        state failed / attempts=5 / last_error="exit=3" ← L28 核心斷言
#     4. 告警行 — WATCHDOG-TOP 含 [標籤] 同 last=exit=3(真實 rc)
#     5. 退避序列 — 輸出含 1s/2s/4s/8s 退避紀錄
#
#   隔離: 狀態／告警／備份全部寫入 mktemp 臨時目錄(TSA_BACKUP_ROOT),
#         唔掂 VPS/home 實檔;事件快照喺無 DB 環境走 SKIP 路徑(exit 3,
#         watchdog 容忍並記錄,唔影響本測試斷言)。
# =============================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WDT="$REPO_ROOT/scripts/watchdog_retry.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
export TSA_BACKUP_ROOT="$TMP/backups"
STATE="$TSA_BACKUP_ROOT/watchdog_state.json"
ALERT="$TSA_BACKUP_ROOT/watchdog_alerts.log"

fails=0
ok()  { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }

# --- 1. 用法守衛 ---
rc_g1=0; bash "$WDT" -- x >/dev/null 2>&1 || rc_g1=$?
[ "$rc_g1" -eq 2 ] && ok "用法守衛:首參 -- → exit 2" \
                   || bad "用法守衛:首參 -- 預期 exit 2,實得 $rc_g1"

rc_g2=0; bash "$WDT" tag true >/dev/null 2>&1 || rc_g2=$?
[ "$rc_g2" -eq 2 ] && ok "用法守衛:缺 -- → exit 2" \
                   || bad "用法守衛:缺 -- 預期 exit 2,實得 $rc_g2"

# --- 2. 成功路徑 ---
out_ok="$(bash "$WDT" t_ok -- true 2>&1)"; rc_ok=$?
[ "$rc_ok" -eq 0 ] && ok "成功路徑 exit 0" \
                   || bad "成功路徑預期 exit 0,實得 $rc_ok"

st_ok="$(python3 - "$STATE" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
e = d.get("t_ok", {})
print("OK" if (e.get("status") == "ok" and e.get("attempts") == 1
               and e.get("last_error") == "") else f"BAD {e}")
PYEOF
)"
[ "$st_ok" = "OK" ] && ok "state t_ok: ok / attempts=1 / last_error 空" \
                    || bad "state t_ok 斷言失敗: $st_ok"

# --- 3. 失敗路徑（退避 1+2+4+8s,約 15 秒）---
out_fail="$(bash "$WDT" t_fail -- bash -c 'exit 3' 2>&1)"; rc_fail=$?
[ "$rc_fail" -eq 1 ] && ok "失敗路徑觸頂 exit 1" \
                     || bad "失敗路徑預期 exit 1,實得 $rc_fail"

st_fail="$(python3 - "$STATE" <<'PYEOF'
import json, sys
d = json.load(open(sys.argv[1]))
e = d.get("t_fail", {})
print("OK" if (e.get("status") == "failed" and e.get("attempts") == 5
               and e.get("last_error") == "exit=3") else f"BAD {e}")
PYEOF
)"
[ "$st_fail" = "OK" ] && ok "state t_fail: failed / attempts=5 / last_error=exit=3（L28 核心）" \
                      || bad "state t_fail 斷言失敗（L28 核心）: $st_fail"

# --- 4. 告警行 ---
if [ -f "$ALERT" ] && grep -q "WATCHDOG-TOP: \[t_fail\]" "$ALERT" \
   && grep -q "last=exit=3" "$ALERT"; then
  ok "告警行: WATCHDOG-TOP [t_fail] last=exit=3"
else
  bad "告警行缺失或 rc 失真: $(cat "$ALERT" 2>/dev/null || echo '(檔案不存在)')"
fi

# --- 5. 退避序列 ---
backoffs=0
for s in 1s 2s 4s 8s; do
  echo "$out_fail" | grep -q "退避 ${s} 後重試" && backoffs=$((backoffs + 1))
done
[ "$backoffs" -eq 4 ] && ok "退避序列 1s→2s→4s→8s 完整" \
                      || bad "退避序列不完整（$backoffs/4）"

echo "----"
if [ "$fails" -eq 0 ]; then
  echo "L28 watchdog_retry 回歸: 全部通過"
  exit 0
fi
echo "L28 watchdog_retry 回歸: $fails 項失敗"
exit 1
