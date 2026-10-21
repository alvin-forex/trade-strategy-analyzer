# L16 資料備份與還原運維手冊（BACKUP RUNBOOK）

> 依據：白皮書 v1.3 §8.3 用戶裁定參數（RPO ≤ 24h）｜實施：2026-10-22（ZCODE）
> 適用環境：VPS／WSL 生產工作區（OpenClaw 營運 lane）
> 治理：本手冊隨季度演練同步更新；修改備份參數須走白皮書 §8.2 受控流程

---

## 1. 備份對象與範圍

| 資料檔 | 內容 | 備份策略 |
|--------|------|----------|
| `data/ccy_power_observations.db` | CCY Power 觀測（26MB 級） | 日×7＋週×4＋月永久＋事件快照 |
| `data/analysis_history.db` | 分析歷史快照 | 同上 |
| `data/ccy_power_history.db` | **唔備份**——cron 每小時重寫嘅派生快取，可由來源重算 | — |

唔入 git repo（§8.3 裁定：二進制無 diff 價值，repo 只做代碼真相源）。

## 2. 備份方法（熱安全）

- **禁止直接 `cp` 運行中 db**（熱備有損壞風險）——一律 SQLite `VACUUM INTO`
- 腳本以唯讀 URI（`file:...?mode=ro`）打開來源，唔阻礙並行寫入
- `VACUUM INTO` 輸出經壓實，體積通常細過原檔

## 3. 每日備份 cron（RPO ≤ 24h 主線）

```cron
# TSA L16 備份（每日 04:00 HKT，避開 23:00 報告峰同每小時 cron）
0 4 * * *  cd /home/alvin/.openclaw/workspace/trade_strategy_analyzer && bash scripts/backup_dbs.sh >> "$HOME/tsa_backups/backup.log" 2>&1
```

目錄結構（`$TSA_BACKUP_ROOT`，預設 `$HOME/tsa_backups`）：

```
tsa_backups/
├── daily/     ×7 自動輪替      ccy_power_observations.daily.20261022_040000.db
├── weekly/    ×4 自動輪替（週日產生）
├── monthly/   永久保留（每月 1 號產生）
├── event/     ×20 自動輪替（watchdog 異常快照）
├── backup.log / cron.log      執行日誌
├── alerts.log                  備份失敗告警（OpenClaw 晨報讀取）
├── watchdog_alerts.log         watchdog 觸頂告警（OpenClaw 晨報讀取）
└── watchdog_state.json         各命令最後執行狀態（attempts/status）
```

**雙存放（§8.3 裁定：本機＋雲端雙份）**：設 `TSA_BACKUP_SECOND=/mnt/backup2/tsa_backups`
（第二磁碟／NFS／rclone 掛載點均可），腳本每份快照自動同步一份過去。
雲端建議：rclone 掛 OneDrive／Google Drive 免費額度，或定時 `rclone copy $HOME/tsa_backups remote:tsa_backups`。

## 4. watchdog（指數退避，§4.4/§8.3 裁定）

```bash
# 將 cron 命令包入 watchdog（例：HST 導出任務）
*/30 * * * * cd <repo> && bash scripts/watchdog_retry.sh export_hst -- python3 scripts/export_hst.py --full >> ... 2>&1
```

行為：失敗按 1s→2s→4s→8s→16s 退避，最多 5 次；觸頂後
①寫 `watchdog_alerts.log`（OpenClaw 晨報轉發通道）→
②自動追加事件快照 `backup_dbs.sh --event` →
③ exit 1 進入安全停止，下一輪排程自然恢復。
`watchdog_state.json` 記錄每個標籤最後 attempts／status，供晨報自檢。

## 5. 備份驗證（每次自動執行）

每份快照產生後腳本自動跑：
1. `PRAGMA integrity_check` — 必須回 `ok`
2. 逐表行數比對 — 來源 vs 快照每張用戶表 `COUNT(*)` 必須一致

任何一項失敗：該快照視為無效、腳本 exit 非零、`alerts.log` 記 ALERT 行。
**無驗證嘅備份等於冇備份。**

## 6. 還原程序（事件應變）

```bash
# 1. 停止寫入源（停相關 cron：OpenClaw 工作區 crontab -e 暫停對應條目）
# 2. 選快照（愈新愈好，但必須 integrity ok——backup.log 有每次驗證記錄）
ls -lt ~/tsa_backups/daily/ | head
# 3. 驗證候選快照
python3 -c "import sqlite3;print(sqlite3.connect('~/tsa_backups/daily/<file>.db').execute('PRAGMA integrity_check').fetchone())"
# 4. 還原（VACUUM INTO 回正名，唔直接 mv 覆蓋運行中檔）
python3 -c "import sqlite3;sqlite3.connect('~/tsa_backups/daily/<file>.db').execute(\"VACUUM INTO 'data/ccy_power_observations.db'\")"
# 5. 行數比對覆核（snapshot vs 還原後 live 檔 COUNT(*) 一致）
# 6. 重啟相關 cron，backup.log 留還原記錄
```

## 7. 季度還原演練（§8.3 裁定：每季度一次）

每季第一週執行，結果記入本手冊第 9 節演練記錄表：

1. 揀一份 recent 快照（daily 最新）
2. 沙盒還原：`VACUUM INTO` 到臨時路徑（**唔好直接覆蓋 live 檔**）
3. 驗證：integrity_check ＋ 行數比對 ＋ 抽一張表前 5 行目視
4. 記錄：演練日期／快照檔名／驗證結果／耗時（RPO 實證）
5. 清理沙盒檔

首次實施記錄（2026-10-22，ZCODE 沙盒）：見第 9 節記錄表 #1。

## 8. 告警接線（OpenClaw 晨報自檢項）

晨報生成時讀取並轉發：
- `~/tsa_backups/watchdog_alerts.log` 最新未讀行（WATCHDOG-TOP）
- `~/tsa_backups/alerts.log` 最新未讀行（backup ALERT）
- `~/tsa_backups/watchdog_state.json` 中 `status != "ok"` 嘅標籤
- 昨日 `daily/` 有冇新快照（`ls daily/ | wc -l` 冇增長＝備份鏈斷，RPO 破功）

## 9. 演練記錄表

| # | 日期 | 快照 | 驗證結果 | 耗時 | 執行者 |
|---|------|------|----------|------|--------|
| 1 | 2026-10-22 | 沙盒合成 DB（2 檔，日/週/月/事件四層） | integrity ok＋行數比對一致＋還原後 COUNT 一致 | <1min | ZCODE（腳本功能驗證） |
