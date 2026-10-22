#!/usr/bin/env bash
# =============================================================================
# L16 資料備份體系（白皮書 v1.3 §8.3 用戶裁定參數，2026-10-22 實施）
#
#   備份方法 : 禁止直接 cp 運行中 db —— 一律 VACUUM INTO（經 python3 sqlite3）
#   RPO ≤24h : 每日定時全量備份（cron 04:00）；watchdog 異常時 --event 追加快照
#   三級輪替 : 日備份 ×7 ｜ 週備份 ×4 ｜ 月備份永久（grandfather-father-son）
#   存放     : 本機備份根目錄（repo 外）＋ 可選第二存放 TSA_BACKUP_SECOND；
#              明確唔入 git repo（二進制無 diff 價值，repo 會膨脹）
#   備份驗證 : 每份快照必跑 PRAGMA integrity_check ＋ 逐表行數比對——
#              無驗證嘅備份等於冇備份；驗證失敗 exit 非零並打 ALERT 行
#
# 用法:
#   bash scripts/backup_dbs.sh             # 例行備份（cron 每日 04:00）
#   bash scripts/backup_dbs.sh --event     # watchdog 異常時追加事件快照
#   bash scripts/backup_dbs.sh --dry-run   # 只列出會做咩，唔寫唔刪
#
# 環境變數:
#   TSA_BACKUP_ROOT   備份根目錄（預設 $HOME/tsa_backups，必須喺 repo 外）
#   TSA_BACKUP_SECOND 第二存放根目錄（可選；例如另一磁碟／NFS 掛載點）
#   TSA_FORCE_WEEKLY=1 / TSA_FORCE_MONTHLY=1   演練用：強制產生週/月快照
#
# L29（2026-10-23）：第二存放 weekly/monthly cp 失敗由「|| true 靜默」改為
#   alert——同 daily/event 語義對齊；9p/drvfs 偶發寫入失敗唔再無聲缺失。
# 排程建議（見 docs/BACKUP_RUNBOOK.md）:
#   0 4 * * *  cd <repo> && bash scripts/backup_dbs.sh >> "$HOME/tsa_backups/cron.log" 2>&1
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

BACKUP_ROOT="${TSA_BACKUP_ROOT:-$HOME/tsa_backups}"
SECOND_ROOT="${TSA_BACKUP_SECOND:-}"
EVENT_MODE=0
DRY_RUN=0
for arg in "$@"; do
  case "$arg" in
    --event)  EVENT_MODE=1 ;;
    --dry-run) DRY_RUN=1 ;;
    *) echo "[backup] 未知參數: $arg" >&2; exit 2 ;;
  esac
done

# 備份對象（§2.3：監控事件 / CCY 歷史 / 分析快照）。路徑相對 repo 根。
# 注意：data/ccy_power_history.db 係 cron 每小時重寫嘅派生快取，唔備份；
#       如需加 DB，喺呢度加一行相對路徑即可。
DBS=(
  "data/ccy_power_observations.db"
  "data/analysis_history.db"
)

# ---- 事件快照輪替：保留最近 20 份 ----
EVENT_KEEP=20

NOW="$(date +%Y%m%d_%H%M%S)"
DOW="$(date +%u)"          # 1=Mon ... 7=Sun
DOM="$(date +%d)"          # 01-31
TODAY="$(date +%Y%m%d)"
MONTH="$(date +%Y%m)"

DAILY_DIR="$BACKUP_ROOT/daily"
WEEKLY_DIR="$BACKUP_ROOT/weekly"
MONTHLY_DIR="$BACKUP_ROOT/monthly"
EVENT_DIR="$BACKUP_ROOT/event"
mkdir -p "$DAILY_DIR" "$WEEKLY_DIR" "$MONTHLY_DIR" "$EVENT_DIR" 2>/dev/null || true
if [ -n "$SECOND_ROOT" ]; then
  mkdir -p "$SECOND_ROOT/daily" "$SECOND_ROOT/weekly" "$SECOND_ROOT/monthly" "$SECOND_ROOT/event"
fi

log()  { echo "[$(date '+%F %T')] $*"; }
alert(){ echo "[$(date '+%F %T')] ALERT: $*" | tee -a "$BACKUP_ROOT/alerts.log" >&2; }

# ---- 核心：VACUUM INTO 快照 + 驗證（integrity_check + 逐表行數比對）----
snapshot_db() {
  local src="$1" dest="$2"
  if [ "$DRY_RUN" = "1" ]; then log "DRY: $src -> $dest"; return 0; fi
  python3 - "$src" "$dest" <<'PYEOF'
import sqlite3, sys, pathlib
src, dest = sys.argv[1], sys.argv[2]
if not pathlib.Path(src).exists():
    print(f"[backup] SKIP（來源唔存在）: {src}"); sys.exit(3)
if pathlib.Path(dest).exists():
    print(f"[backup] FAIL（目標已存在）: {dest}"); sys.exit(4)
s = sqlite3.connect(f"file:{src}?mode=ro", uri=True)   # 唯讀打開，唔阻礙並行寫入
s.execute("VACUUM INTO ?", (dest,))                    # 熱安全快照（§8.3 裁定）
tables = [r[0] for r in s.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
src_rows = {t: s.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
s.close()
b = sqlite3.connect(dest)
ok = b.execute("PRAGMA integrity_check").fetchone()[0]
bts = [r[0] for r in b.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
bak_rows = {t: b.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in bts}
b.execute("PRAGMA optimize"); b.close()
if ok != "ok":
    print(f"[backup] FAIL integrity_check={ok}: {dest}"); sys.exit(5)
if src_rows != bak_rows:
    diff = {t: (src_rows.get(t), bak_rows.get(t)) for t in set(src_rows) | set(bak_rows)
            if src_rows.get(t) != bak_rows.get(t)}
    print(f"[backup] FAIL 行數比對唔一致: {diff}"); sys.exit(6)
print(f"[backup] OK {pathlib.Path(dest).name} tables={len(tables)} rows={sum(bak_rows.values())}")
PYEOF
}

# ---- 輪替：目錄入面按 mtime 降序，第 (keep+1) 份起刪除 ----
rotate() {
  local dir="$1" keep="$2"
  [ "$DRY_RUN" = "1" ] && return 0
  ls -1t "$dir" 2>/dev/null | tail -n +$((keep + 1)) | while IFS= read -r f; do
    rm -f -- "$dir/$f"; log "ROTATE 刪除過期快照: $dir/$f"
  done
}

# ---- 同秒重跑防撞：dest 已存在就加 _N 後綴（重試/手動重跑友好）----
resolve_dest() {
  local d="$1" i=0
  while [ -e "$d" ]; do i=$((i + 1)); d="${d%.db}_${i}.db"; done
  echo "$d"
}

rc=0
for rel in "${DBS[@]}"; do
  src="$REPO_ROOT/$rel"
  base="$(basename "$rel" .db)"

  if [ "$EVENT_MODE" = "1" ]; then
    dest="$(resolve_dest "$EVENT_DIR/${base}.event.${NOW}.db")"
    log "EVENT 快照: $rel"
    snapshot_db "$src" "$dest" || { alert "$rel 事件快照失敗"; rc=1; continue; }
    rotate "$EVENT_DIR" "$EVENT_KEEP"
    if [ -n "$SECOND_ROOT" ]; then
      cp -f "$dest" "$SECOND_ROOT/event/" 2>/dev/null || alert "第二存放寫入失敗: $dest"
    fi
    continue
  fi

  # 日備份（每日）
  dest="$(resolve_dest "$DAILY_DIR/${base}.daily.${TODAY}_${NOW##*_}.db")"
  log "DAILY 快照: $rel"
  snapshot_db "$src" "$dest" || { alert "$rel 日備份失敗"; rc=1; continue; }
  rotate "$DAILY_DIR" 7
  if [ -n "$SECOND_ROOT" ]; then
    cp -f "$dest" "$SECOND_ROOT/daily/" 2>/dev/null || alert "第二存放寫入失敗: $dest"
  fi

  # 週備份（週日或 TSA_FORCE_WEEKLY）
  if [ "$DOW" = "7" ] || [ "${TSA_FORCE_WEEKLY:-0}" = "1" ]; then
    wdest="$(resolve_dest "$WEEKLY_DIR/${base}.weekly.${TODAY}.db")"
    log "WEEKLY 快照: $rel"
    snapshot_db "$src" "$wdest" || { alert "$rel 週備份失敗"; rc=1; }
    rotate "$WEEKLY_DIR" 4
    if [ -n "$SECOND_ROOT" ]; then
      cp -f "$wdest" "$SECOND_ROOT/weekly/" 2>/dev/null || alert "第二存放寫入失敗: $wdest"
    fi
  fi

  # 月備份（每月 1 號或 TSA_FORCE_MONTHLY）——永久保留
  if [ "$DOM" = "01" ] || [ "${TSA_FORCE_MONTHLY:-0}" = "1" ]; then
    mdest="$(resolve_dest "$MONTHLY_DIR/${base}.monthly.${MONTH}.db")"
    log "MONTHLY 快照: $rel"
    snapshot_db "$src" "$mdest" || { alert "$rel 月備份失敗"; rc=1; }
    if [ -n "$SECOND_ROOT" ]; then
      cp -f "$mdest" "$SECOND_ROOT/monthly/" 2>/dev/null || alert "第二存放寫入失敗: $mdest"
    fi
  fi
done

if [ "$rc" = "0" ]; then log "備份完成（RPO ≤24h 維持）"; else alert "備份部分失敗 rc=$rc——檢查 $BACKUP_ROOT/alerts.log"; fi
exit $rc
