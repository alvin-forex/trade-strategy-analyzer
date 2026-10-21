#!/usr/bin/env bash
# =============================================================================
# L16 watchdog 重試包裝（白皮書 v1.3 §4.4/§8.3 用戶裁定，2026-10-22 實施）
#
#   裁定行為：指數退避 1s → 2s → 4s → 8s → 16s，上限 5 次；
#             觸頂經 OpenClaw 通道告警並進入安全停止，
#             重啟需人工確認或由下一輪排程自動恢復。
#
# 用法:
#   bash scripts/watchdog_retry.sh -- <command...>
#   例: bash scripts/watchdog_retry.sh -- python3 scripts/export_hst.py --full
#
# 行為:
#   1. 執行 command；成功（exit 0）即結束，記錄耗時
#   2. 失敗 → 指數退避重試（1/2/4/8/16s），最多 5 次
#   3. 觸頂（5 次全失敗）：
#      a) 告警寫入 $TSA_WATCHDOG_ALERT_LOG（預設 $HOME/tsa_backups/watchdog_alerts.log）
#         —— OpenClaw 晨報自檢／輪詢讀取此檔轉發通道
#      b) 追加一次事件快照 backup_dbs.sh --event（異常時保數據，§8.3 RPO 增量條款）
#      c) exit 1 —— cron 層面記錄失敗；下一輪排程自然恢復（安全停止語義）
#
# 狀態檔: $TSA_WATCHDOG_STATE（預設 $HOME/tsa_backups/watchdog_state.json）
#         記錄每個命令最後一次嘅 attempts／last_error／last_ok，
#         供晨報自檢同 cross-audit 讀取。
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MAX_ATTEMPTS=5
BACKUP_ROOT="${TSA_BACKUP_ROOT:-$HOME/tsa_backups}"
ALERT_LOG="${TSA_WATCHDOG_ALERT_LOG:-$BACKUP_ROOT/watchdog_alerts.log}"
STATE_FILE="${TSA_WATCHDOG_STATE:-$BACKUP_ROOT/watchdog_state.json}"

# -- 分隔後第一參數 = 命令標籤（state key 用）
if [ "${1:-}" = "--" ]; then
  echo "[watchdog] 用法: watchdog_retry.sh <標籤> -- <command...>" >&2
  exit 2
fi
LABEL="${1:?用法: watchdog_retry.sh <標籤> -- <command...>}"
[ "${2:-}" = "--" ] || { echo "[watchdog] 第二參數必須係 --" >&2; exit 2; }
shift 2
[ "$#" -gt 0 ] || { echo "[watchdog] 冇命令可執行" >&2; exit 2; }

mkdir -p "$BACKUP_ROOT" 2>/dev/null || true

attempt=0
delay=1
last_err=""
start_ts="$(date '+%F %T')"

while [ "$attempt" -lt "$MAX_ATTEMPTS" ]; do
  attempt=$((attempt + 1))
  echo "[watchdog] [$LABEL] 第 $attempt/$MAX_ATTEMPTS 次: $*"
  if "$@"; then
    echo "[watchdog] [$LABEL] OK（第 $attempt 次成功，耗時自 $start_ts）"
    python3 - "$STATE_FILE" "$LABEL" "$attempt" "ok" "" <<'PYEOF'
import json, sys, datetime, pathlib
state_p, label, attempts, status, err = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
p = pathlib.Path(state_p)
data = {}
if p.exists():
    try: data = json.loads(p.read_text())
    except Exception: data = {}
data[label] = {"attempts": attempts, "status": status, "last_error": err,
               "timestamp": datetime.datetime.now().isoformat(timespec="seconds")}
p.write_text(json.dumps(data, ensure_ascii=False, indent=1))
PYEOF
    exit 0
  fi
  rc=$?
  last_err="exit=$rc"
  echo "[watchdog] [$LABEL] 失敗 rc=$rc"
  if [ "$attempt" -lt "$MAX_ATTEMPTS" ]; then
    echo "[watchdog] [$LABEL] 退避 ${delay}s 後重試"
    sleep "$delay"
    delay=$((delay * 2))
  fi
done

# ---- 觸頂：告警 + 事件快照 + 安全停止 ----
echo "[watchdog] [$LABEL] 5 次全敗——觸發告警＋事件快照＋安全停止" >&2
{
  echo "[$(date '+%F %T')] WATCHDOG-TOP: [$LABEL] command=$* attempts=$MAX_ATTEMPTS last=$last_err"
} >> "$ALERT_LOG"

python3 - "$STATE_FILE" "$LABEL" "$MAX_ATTEMPTS" "failed" "$last_err" <<'PYEOF'
import json, sys, datetime, pathlib
state_p, label, attempts, status, err = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], sys.argv[5]
p = pathlib.Path(state_p)
data = {}
if p.exists():
    try: data = json.loads(p.read_text())
    except Exception: data = {}
data[label] = {"attempts": attempts, "status": status, "last_error": err,
               "timestamp": datetime.datetime.now().isoformat(timespec="seconds")}
p.write_text(json.dumps(data, ensure_ascii=False, indent=1))
PYEOF

# 事件快照（§8.3：watchdog 觸發異常事件時追加增量備份）
# 呢步唔阻住告警語義——快照失敗只追加記錄
if bash "$SCRIPT_DIR/backup_dbs.sh" --event >> "$BACKUP_ROOT/backup.log" 2>&1; then
  echo "[watchdog] [$LABEL] 事件快照完成"
else
  echo "[watchdog] [$LABEL] 事件快照失敗（已記錄 backup.log）" >&2
fi

exit 1
