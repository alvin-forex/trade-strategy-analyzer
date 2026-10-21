# OpenClaw 運維交辦 — L16 備份體系接線（六項）

> 日期：2026-10-22｜來源：ZCODE（代碼 lane）→ OpenClaw（營運 lane）
> 依據：白皮書 v1.4 §8.3／§8.6（結案版）＋ `docs/BACKUP_RUNBOOK.md`
> 狀態：本批已合併入 main — `scripts/backup_dbs.sh`、`scripts/watchdog_retry.sh`、`docs/BACKUP_RUNBOOK.md`
> （merge 72b56120）；`generate_forex_hub.py` 數據新鮮度三級警示（merge 59d9f8da）
> 治理：本檔為一次性交辦清單；完成一項請喺「完成紀錄」表回填日期與結果，全部完成後本檔可歸檔

---

## 背景

2026-10-22 收尾批次已將 L16 備份體系與 L22 數據新鮮度修復合併入 main（CI 7/7 綠）。
代碼 lane 嘅部分已齊：備份腳本（熱安全＋三級輪替＋驗證）、watchdog 退避包裝、運維手冊。
以下六項屬 **VPS 環境接線與營運動作**，屬 OpenClaw 營運 lane 職責，請按優先序執行。
每項都有明確驗收標準；完成後喺文末「完成紀錄」表回填。

---

## 交辦清單（按優先序）

### 項 1｜每日備份 cron 接線（RPO ≤ 24h 主線）— P0

```cron
# TSA L16 備份（每日 04:00 HKT，避開 23:00 報告峰同每小時 cron）
0 4 * * *  cd /home/alvin/.openclaw/workspace/trade_strategy_analyzer && bash scripts/backup_dbs.sh >> "$HOME/tsa_backups/backup.log" 2>&1
```

- **步驟**：crontab -e 加入上行 → 手動跑一次 `bash scripts/backup_dbs.sh` 驗證 → 翌日檢查自動執行結果。
- **驗收**：`$HOME/tsa_backups/daily/` 出現當日快照；`backup.log` 無 ALERT 行；
  `PRAGMA integrity_check` 回 ok（腳本自動執行，日誌可查）。

### 項 2｜watchdog 改用 watchdog_retry.sh 包裝 — P1

- **步驟**：盤點現有裸跑 cron 命令（HST 導出、報告生成等），逐個按 RUNBOOK §4 改為
  `bash scripts/watchdog_retry.sh <標籤> -- <原命令>`；標籤用任務名（如 `export_hst`）。
- **驗收**：`$HOME/tsa_backups/watchdog_state.json` 出現各標籤嘅 attempts/status 紀錄；
  模擬失敗一次（錯命令），確認退避 1s→2s→4s→8s→16s、5 次觸頂後寫 `watchdog_alerts.log`
  ＋自動追加事件快照＋安全停止。

### 項 3｜備份雙存放第二位置 — P1

- **步驟**：決定第二存放位置（第二磁碟／NFS／rclone 掛載，雲端建議 rclone 免費額度）→
  設環境變數 `TSA_BACKUP_SECOND=<掛載點>/tsa_backups`（寫入 crontab 行或腳本 env）→
  手動跑一次備份確認同步。
- **驗收**：每份新快照同時出現喺 `$HOME/tsa_backups/` 同第二位置；第二位置磁碟用量監察納入晨報。

### 項 4｜VPS 還原演練（季度演練首輪）— P1

- **步驟**：按 RUNBOOK §6 還原程序 — 揀最新 daily 快照 → 還原至**臨時目錄**（唔好覆蓋線上 db）→
  對還原檔跑 `PRAGMA integrity_check` + 行數比對 → 記錄全程耗時與結果。
- **驗收**：演練紀錄（日期／快照檔名／耗時／行數比對結果）回報並回寫 RUNBOOK §7 演練日誌；
  如發現程序問題，開 branch 修 RUNBOOK（走代碼 lane 受控流程）。

### 項 5｜工作區 template.bak 殘留清理 — P2

- **步驟**：喺 VPS 工作區搜尋 template 類 `.bak` 殘留並刪除：
  `find /home/alvin/.openclaw/workspace -maxdepth 3 -name "*.bak" -o -name "template*.bak*"`
  先列清單人工確認，再刪。呢類檔案唔喺 git 內（屬本機殘留），刪除唔影響 repo。
- **驗收**：find 再跑一次無 `.bak` 殘留；如發現唔確定用途嘅檔案，先回報唔好刪。

### 項 6｜晨報自檢擴充（備份狀態＋數據新鮮度）— P2

- **步驟**：晨報生成流程加入兩個自檢段：
  ①讀 `$HOME/tsa_backups/alerts.log`、`watchdog_alerts.log`、`watchdog_state.json` —
  有 ALERT／觸頂紀錄即喺晨報頂部加警告；無紀錄但 `daily/` 冇昨日快照亦要報。
  ②讀 CCY Power 最新時間戳 — 距現在 >24 小時即加「數據停滯」警告
  （頁面端三級警示已上線：🟢 ≤24h／⚠️ >24h／🚨 >7 天＋落單核實提示）。
- **驗收**：晨報出現「備份自檢」與「數據新鮮度」兩段；人工製造一次失敗（例如改名 daily 目錄）
  確認晨報有警告。

---

## 執行注意

- 六項全部屬 VPS 本機動作，**唔使改 repo 代碼**；只有發現腳本／手冊本身有錯先開 branch 走受控流程。
- 備份與快照一律**唔入 git**（白皮書 §8.3 裁定）。
- 完成回報：喺 TG 群回報＋回填下表即可，唔使開 PR。

## 完成紀錄（OpenClaw 回填）

| # | 項目 | 完成日期 | 驗收結果 | 備註 |
|---|------|----------|----------|------|
| 1 | cron 04:00 接線 | — | — | — |
| 2 | watchdog 包裝 | — | — | — |
| 3 | 雙存放第二位置 | — | — | — |
| 4 | VPS 還原演練 | — | — | — |
| 5 | template.bak 清理 | — | — | — |
| 6 | 晨報自檢擴充 | — | — | — |
