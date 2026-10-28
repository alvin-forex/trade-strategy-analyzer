#!/bin/bash
# TSA SQLite daily snapshot — hot-safe backup of operational DBs
# Created 2026-10-21. Runs 03:10 (before vps_pull 03:05 is MT5-only; separate from hourly ccy push)
# Uses sqlite3 .backup (consistent snapshot even with concurrent writers).
# 2026-10-23 (項 7 phase 2)：stderr 留底 + .backup 3 次 retry + FAIL exit 透傳 watchdog
set -o pipefail
# 2026-10-27: cron PATH fix - sqlite3 lives outside cron's default PATH;
# without this the 03:13 run fails 5x with 'sqlite3: command not found'
export PATH="/usr/local/bin:/usr/bin:/bin:/home/linuxbrew/.linuxbrew/bin:$PATH"

R=/home/alvin/.openclaw/workspace/trade_strategy_analyzer
DEST=/home/alvin/backups/tsa_db_snapshots
KEEP_DAYS=14
STAMP=$(date +%Y%m%d)
LOG="$DEST/snapshot.log"

DB_LIST=(
  "data/ccy_power_observations.db"
  "data/tsa.db"
  "data/analysis_history.db"
  "data/ccy_power_history.db"
)

mkdir -p "$DEST" || exit 1

{
  echo "=== $(date '+%F %T') snapshot start ==="
  FAIL=0
  for rel in "${DB_LIST[@]}"; do
    src="$R/$rel"
    [ -f "$src" ] || { echo "SKIP $rel (missing)"; continue; }
    base=$(basename "$rel" .db)
    out="$DEST/${base}_${STAMP}.db"

    # hot-safe copy via sqlite3 .backup (3 retries: transient lock tolerance)
    bak_ok=0
    for attempt in 1 2 3; do
      if sqlite3 "$src" ".backup '$out'" 2>>"$LOG"; then
        bak_ok=1
        break
      fi
      echo "RETRY $rel (.backup attempt $attempt/3 failed)" >&2
      if [ "$attempt" -lt 3 ]; then sleep 5; fi
    done
    if [ "$bak_ok" -eq 0 ]; then
      echo "FAIL $rel (sqlite3 .backup, 3 attempts)"
      rm -f "$out"
      FAIL=1
      continue
    fi

    # verify snapshot integrity
    chk=$(sqlite3 "$out" "PRAGMA integrity_check;" 2>>"$LOG" | head -1)
    if [ "$chk" != "ok" ]; then
      echo "FAIL $rel (integrity=$chk)"
      rm -f "$out"
      FAIL=1
      continue
    fi

    if ! gzip -9 -f "$out" 2>>"$LOG"; then
      echo "FAIL $rel (gzip)"
      rm -f "${out}.gz"
      FAIL=1
      continue
    fi
    printf 'OK %-42s %10s -> %s.gz\n' "$rel" "$(du -h "$src" | cut -f1)" "$(basename "$out")"
  done

  # rotation
  n=$(find "$DEST" -name '*_2*.db.gz' -mtime +$KEEP_DAYS 2>/dev/null | wc -l)
  if [ "$n" -gt 0 ]; then
    find "$DEST" -name '*_2*.db.gz' -mtime +$KEEP_DAYS -delete 2>/dev/null
    echo "ROTATED removed $n file(s) older than ${KEEP_DAYS}d"
  fi

  total=$(du -sh "$DEST" 2>/dev/null | cut -f1)
  echo "SNAPSHOT_DONE fail=$FAIL total=$total"
} >> "$LOG" 2>&1

exit "$FAIL"
