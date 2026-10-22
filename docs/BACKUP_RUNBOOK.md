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

### 現行 crontab 截錄（2026-10-22 項 2 盤點，2026-10-23 回填核對）

```cron
TSA_BACKUP_SECOND=/mnt/d/tsa_backups
# 每日外匯報告 - 早盤報告
# 每日外匯報告 - 晚盤報告


# Google Drive 圖片分析 - 每小時檢查有新圖先分析
@reboot cd /home/alvin/.openclaw/workspace/trade_strategy_analyzer && /usr/bin/python3 /home/alvin/.openclaw/workspace/trade_strategy_analyzer/scripts/api_server.py >> /tmp/trade-analyzer-api.log 2>&1

# 流程健康監察 - 每4小時（OCR之後10分鐘）
10 */4 * * * /usr/bin/python3 /home/alvin/.openclaw/workspace/scripts/flow_health_check.py >> /tmp/openclaw/flow_health_check.log 2>&1

@reboot sleep 30 && python3 /home/alvin/.openclaw/workspace/trade_strategy_analyzer/mt4_monitor/watchdog_daemon.py >> /tmp/watchdog_daemon.log 2>&1

# CCY Power 每小時更新
0 * * * * cd /home/alvin/.openclaw/workspace/scripts && bash /home/alvin/.openclaw/workspace/trade_strategy_analyzer/scripts/watchdog_retry.sh ccy_power -- /home/alvin/.openclaw/workspace/scripts/ccy_power_update_and_push.sh >> /tmp/openclaw/ccy_power.log 2>&1

# Forex data 新鮮度檢查 - 每小時（取代 Finnhub heartbeat）
0 * * * * cd /home/alvin/.openclaw/workspace/scripts && bash /home/alvin/.openclaw/workspace/trade_strategy_analyzer/scripts/watchdog_retry.sh freshness -- /usr/bin/python3 /home/alvin/.openclaw/workspace/scripts/forex_data_freshness.py >> /tmp/openclaw/forex_data_check.log 2>&1

# TSA API watchdog — 每30分鐘確保 api_server 8787 存活（2026-08-31 丁蟹）
*/30 * * * * cd /home/alvin/.openclaw/workspace/scripts && bash /home/alvin/.openclaw/workspace/trade_strategy_analyzer/scripts/watchdog_retry.sh tsa_api -- /home/alvin/.openclaw/workspace/scripts/ensure_tsa_api.sh >> /tmp/tsa_api_watchdog.log 2>&1

# FF signals snapshot - 每日 01:05 / 05:05（0 agent tokens，CSV export 端點）
5 1,5 * * 1-5 cd /home/alvin/.openclaw/data/ff-signals && bash /home/alvin/.openclaw/workspace/trade_strategy_analyzer/scripts/watchdog_retry.sh ff_signals -- /home/alvin/.nvm/versions/node/v24.18.0/bin/node /home/alvin/.openclaw/data/ff-signals/ff-scraper.mjs >> /home/alvin/.openclaw/data/ff-signals/cron.log 2>&1

# VPS backup architecture (2026-10-20)
5 3 * * * bash /home/alvin/.openclaw/workspace/trade_strategy_analyzer/scripts/watchdog_retry.sh vps_pull -- /home/alvin/.openclaw/workspace/main/scripts/vps_pull_backup.sh >> /tmp/openclaw/vps_pull.log 2>&1
35 3 * * * bash /home/alvin/.openclaw/workspace/trade_strategy_analyzer/scripts/watchdog_retry.sh vps_push -- /home/alvin/.openclaw/workspace/main/scripts/vps_push_backup.sh >> /tmp/openclaw/vps_push.log 2>&1

# TSA SQLite 每日快照 — 03:10（03:05 mt5 pull 之後、03:35 vps push 之前；獨立於每小時 CCY push）
10 3 * * * bash /home/alvin/.openclaw/workspace/trade_strategy_analyzer/scripts/watchdog_retry.sh db_snapshot -- /home/alvin/.openclaw/workspace/main/scripts/tsa_db_snapshot.sh >> /tmp/openclaw/tsa_db_snapshot.log 2>&1

# TSA L16 備份（每日 04:00 HKT，RPO ≤ 24h；ZCODE 交辦 2026-10-22）
0 4 * * * cd /home/alvin/.openclaw/workspace/trade_strategy_analyzer && bash /home/alvin/.openclaw/workspace/trade_strategy_analyzer/scripts/watchdog_retry.sh backup_dbs -- bash scripts/backup_dbs.sh >> "$HOME/tsa_backups/backup.log" 2>&1
* * * * * /home/alvin/.openclaw/workspace/scripts/alvins_bot_keepalive.sh
```

- 共 12 條：8 條包 `watchdog_retry.sh`（標籤：backup_dbs／ccy_power／db_snapshot／ff_signals／freshness／tsa_api／vps_pull／vps_push）；2 條 @reboot 常駐（api_server.py／watchdog_daemon.py）裁定唔包（watchdog_retry 語義係一次性退避重試→安全停止，常駐 crash 後 5 連試無意義且 @reboot 冇下一輪會變孤兒；常駐監察由 watchdog_daemon 自己管）；另 2 條直接 cron（flow_health_check 每 4 小時／alvins_bot_keepalive 每分鐘）
- 截錄與項 2 盤點 13 條有出入：項 2 盤點時「行 7/10 同時出現喺兩清單」有小矛盾——今次以本截錄（12 條實數）做最終核對

> 2026-10-23 項 7：刪除 video_check 條目（check_new_videos.sh 已不存在，老闆裁定）

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

> 2026-10-23 更新：晨報自檢已升級為 `tsa_selfcheck.py` 三段版（①備份自檢：alerts.log／watchdog_alerts.log／watchdog_state.json＋昨日 daily 快照檢查 ②數據新鮮度：CCY Power 時間戳 >24h 警告 ③第二位置監察：du/df＋兩位置最新 daily md5 對照）；晨報 automation 步驟 0 先跑 selfcheck，輸出嵌入晨報開頭並警告頂置。本段所列讀取項已由三段自檢覆蓋。

## 9. 演練記錄表

| # | 日期 | 快照 | 驗證結果 | 耗時 | 執行者 |
|---|------|------|----------|------|--------|
| 1 | 2026-10-22 | 沙盒合成 DB（2 檔，日/週/月/事件四層） | integrity ok＋行數比對一致＋還原後 COUNT 一致 | <1min | ZCODE（腳本功能驗證） |
| 2 | 2026-10-22 | VPS 真快照（20261022_070610，analysis_history.db＋ccy_power_observations.db 還原至沙盒臨時目錄） | integrity ok＋四表行數比對 ALL OK（analyses 92／versions 36／ccy_power_observations 142610／ccy_power_stats 0）＋目視抽樣正常 | 0.1s | OpenClaw（VPS 首輪真快照演練） |
