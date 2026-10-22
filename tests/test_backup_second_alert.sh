#!/usr/bin/env bash
# =============================================================================
# L29 backup_dbs.sh 第二存放 weekly/monthly 靜默失敗回歸測試（CI golden job 步驟）
#
#   背景: 項 3 雙存放驗證裁定——event/daily 第二存放 cp 失敗有 alert,
#         weekly(原 L153)/monthly(原 L163) 係 || true 靜默失敗:
#         9p/drvfs(WSL /mnt/d) 偶發寫入失敗時,週月快照喺第二位置
#         悄悄缺失,告警零感知——第二存放等級降級無人知。
#
#   驗證五項:
#     1. 主位置快照生成正常 — daily/weekly/monthly 各 2 份(2 db),exit 0
#     2. L29 核心 .weekly.  — 第二存放 weekly 寫入失敗 → alerts.log 有 ALERT
#     3. L29 核心 .monthly. — 第二存放 monthly 寫入失敗 → alerts.log 有 ALERT
#     4. 對照組             — daily 第二存放正常寫入 → 零誤報＋確有同步
#     5. 失敗模擬生效       — 第二位置 weekly/ 確認空(cp 全部被拒)
#
#   隔離: mktemp 全程;測試 DB 即場建(python3 sqlite3);
#         第二位置 weekly/monthly 目錄預建後 chmod 555 模擬 9p 寫入拒絕
#         (script 內 mkdir -p 對已存在目錄 no-op,cp 得 EPERM)。
#         ⚠️ 唔好以 root 跑(root 繞過檔案權限,chmod 模擬會失效)。
# =============================================================================
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BKP="$REPO_ROOT/scripts/backup_dbs.sh"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- 測試環境:假 repo 結構(backup_dbs.sh 由自身位置推算 REPO_ROOT,
#     所以複製 script 入 $TMP/repo/scripts/,令 data 源指向 $TMP/repo/data) ---
mkdir -p "$TMP/repo/scripts" "$TMP/repo/data" "$TMP/main" "$TMP/second"
cp "$BKP" "$TMP/repo/scripts/backup_dbs.sh"
BKP="$TMP/repo/scripts/backup_dbs.sh"
python3 - "$TMP/repo/data" <<'PYEOF'
import sqlite3, sys, pathlib
d = pathlib.Path(sys.argv[1])
# 表名貼近真 db(行數比對邏輯對任意表成立)
c = sqlite3.connect(d / "ccy_power_observations.db")
c.execute("CREATE TABLE ccy_power_observations (id INTEGER, ts TEXT)")
c.executemany("INSERT INTO ccy_power_observations VALUES (?,?)",
              [(i, "2026-10-23T0%d:00" % i) for i in range(5)])
c.commit(); c.close()
a = sqlite3.connect(d / "analysis_history.db")
a.execute("CREATE TABLE analyses (id INTEGER, sig TEXT)")
a.executemany("INSERT INTO analyses VALUES (?,?)", [(i, "SIG%d" % i) for i in range(3)])
a.commit(); a.close()
PYEOF

# 第二位置:daily/event 正常;weekly/monthly 預建+只讀(模擬 9p 寫入失敗)
mkdir -p "$TMP/second/daily" "$TMP/second/event" "$TMP/second/weekly" "$TMP/second/monthly"
chmod 555 "$TMP/second/weekly" "$TMP/second/monthly"

# --- 跑備份(強制週月,唔睇 DOW/DOM) ---
export TSA_BACKUP_ROOT="$TMP/main" TSA_BACKUP_SECOND="$TMP/second"
out="$(TSA_FORCE_WEEKLY=1 TSA_FORCE_MONTHLY=1 bash "$BKP" 2>&1)"; rc=$?
ALERT="$TSA_BACKUP_ROOT/alerts.log"

fails=0
ok()  { echo "PASS: $1"; }
bad() { echo "FAIL: $1"; fails=$((fails + 1)); }

# --- 1. 主位置快照生成正常 ---
[ "$rc" -eq 0 ] && ok "backup_dbs 整體 exit 0(第二存放失敗唔拖垮主備份)" \
                || bad "預期 exit 0,實得 $rc;輸出: $out"
for d in daily weekly monthly; do
  n="$(ls -1 "$TSA_BACKUP_ROOT/$d" 2>/dev/null | wc -l)"
  [ "$n" -eq 2 ] && ok "主位置 $d/ 有 2 份快照(2 db)" \
                 || bad "主位置 $d/ 預期 2 份快照,實得 $n"
done

# --- 2/3. L29 核心:weekly/monthly 第二存放失敗有 ALERT ---
[ -f "$ALERT" ] || { bad "alerts.log 唔存在: $ALERT"; echo "輸出: $out"; exit 1; }
w_alerts="$(grep -c '第二存放寫入失敗.*\.weekly\.' "$ALERT" || true)"
m_alerts="$(grep -c '第二存放寫入失敗.*\.monthly\.' "$ALERT" || true)"
[ "$w_alerts" -eq 2 ] && ok "L29 核心:weekly 第二存放失敗 → 2 條 ALERT(2 db)" \
                      || bad "L29 核心:weekly ALERT 預期 2 條,實得 $w_alerts"
[ "$m_alerts" -eq 2 ] && ok "L29 核心:monthly 第二存放失敗 → 2 條 ALERT(2 db)" \
                      || bad "L29 核心:monthly ALERT 預期 2 條,實得 $m_alerts"

# --- 4. 對照組:daily 正常寫入,零誤報 ---
d_alerts="$(grep -c '第二存放寫入失敗.*\.daily\.' "$ALERT" || true)"
[ "$d_alerts" -eq 0 ] && ok "對照組:daily 第二存放正常 → 零誤報" \
                      || bad "對照組:daily 出現 $d_alerts 條誤報"
n="$(ls -1 "$TMP/second/daily" 2>/dev/null | wc -l)"
[ "$n" -eq 2 ] && ok "對照組:daily 快照確有同步到第二位置(2 份)" \
               || bad "對照組:第二位置 daily/ 預期 2 份,實得 $n"

# --- 5. 失敗模擬生效確認 ---
n="$(ls -1 "$TMP/second/weekly" 2>/dev/null | wc -l)"
[ "$n" -eq 0 ] && ok "失敗模擬生效:第二位置 weekly/ 空(cp 全部被拒)" \
               || bad "失敗模擬未生效:第二位置 weekly/ 有 $n 份"

echo "----"
if [ "$fails" -eq 0 ]; then
  echo "L29 backup 第二存放告警回歸: 全部通過"
  exit 0
fi
echo "L29 backup 第二存放告警回歸: $fails 項失敗"
exit 1
