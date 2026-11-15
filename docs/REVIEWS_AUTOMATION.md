# 按日期覆盤自動化 — 排程接線紀錄（PRD 15.6／待辦⑧）

> 日期：2026-11-15｜來源：覆盤自動化派工（PRD 待辦⑧）
> 依據：`PRD.md` 15.6（自動化規劃）；機制參照 `tsa-ranking-daily`（05:30 ranking 重生成，commit `123ce7b1`）＋ L16 備份 cron（`docs/OPENCLAW_OPS_HANDOFF.md` 項 1）
> 狀態：**倉庫側已落地**（wrapper＋保留策略＋實跑產出）；VPS crontab 兩行待營運 lane 接線（見下）

---

## 1. 觸發點一覽（咩時間跑、點觸發、邊個檔負責）

| 任務 | 時間（HKT） | 觸發方式 | 負責檔案 |
|------|------------|----------|----------|
| 昨日日報 | 每日 06:05 | VPS crontab `5 6 * * *` | `scripts/run_scheduled_reviews.py daily` |
| 上週週報 | 每週一 06:10 | VPS crontab `10 6 * * 1` | `scripts/run_scheduled_reviews.py weekly` |

**完整調用鏈**（全部係既有輪，本工只加 wrapper 駁線）：

```
cron → scripts/run_scheduled_reviews.py {daily|weekly}
         ├─ 1. generate_history_backup.py::backup_all_signals()   # downloads/*.csv（AlgoForest 每日同步）→ data/history/signal_*.json
         ├─ 2. scripts/date_range_review.py --period daily|weekly # → docs/reviews/{daily,weekly}/review_*.{html,json}＋index.json
         ├─ 3. 保留策略剪枝（本 wrapper 內建）                     # 日報 30 日／週報 12 週，舊檔＋index.json 條目自動清
         └─ 4. git add docs/reviews/{daily,weekly}＋git commit     # 產物落地 repo（GitHub Pages 可見）；--push 旗標預設關
```

`docs/reviews/index.html` 本身動態 fetch `daily|weekly|monthly/index.json` 渲染（`index.html:361-368`），新報告入到 index.json 即自動現身，毋須改頁。

### VPS crontab 接線（營運 lane 動作，照 OPENCLAW_OPS_HANDOFF 項 1 模式）

```cron
# TSA 覆盤：昨日日報（排 AlgoForest 同步 ~04:40＋ranking 05:30 之後；見 §3 時間取捨）
5 6 * * *  cd /home/alvin/.openclaw/workspace/trade_strategy_analyzer && python3 scripts/run_scheduled_reviews.py daily >> "$HOME/tsa_backups/reviews.log" 2>&1
# TSA 覆盤：上週週報（週一至週日）
10 6 * * 1  cd /home/alvin/.openclaw/workspace/trade_strategy_analyzer && python3 scripts/run_scheduled_reviews.py weekly >> "$HOME/tsa_backups/reviews.log" 2>&1
```

步驟：`crontab -e` 加入兩行 → 手動各跑一次（daily／weekly）驗證 → 翌日檢查 `reviews.log` 與 `docs/reviews/daily/` 新檔。亦可併入 OpenClaw automations（`tsa-ranking-daily` 同款 job，payload 換成本 wrapper）。

## 2. 排程時間取捨（06:05 vs PRD 原文 00:05）

PRD 15.6 原文係「每日 00:05」。而家嘅數據鏈：AlgoForest 交易記錄同步喺朝早 ~04:40（例：commit `cb3ecd15` 2026-11-14 04:41），ranking 重生成 05:30（`123ce7b1`）。**00:05 跑會早過當日同步，昨日報告會成日缺失最新交易**，故實際接線排 06:05／06:10（同步＋ranking 完成後）。此為對 PRD 意圖（每日生成昨日覆盤）嘅忠實實現，時刻偏差原因記錄在此。

## 3. 保留策略（PRD 15.6）

| 週期 | 保留 | 實現 |
|------|------|------|
| 日報 | 30 日 | wrapper 剪枝：`review_YYYY-MM-DD_*` 檔名 start_date 早於今日−30 日即刪（含 signal 級變體），index.json 條目同步剪 |
| 週報 | 12 週 | 同上，cutoff＝今日−84 日 |
| 月報 | 12 個月 | PRD 有列但本月報 cron 未存在，暫未接（月報產物全部喺 12 個月內，現狀無需清） |

## 4. 落地驗收紀錄（2026-11-15，Windows 本機實跑）

| 項 | 結果 |
|----|------|
| 昨日日報實跑 | `docs/reviews/daily/review_2026-11-14_2026-11-14.{html,json}`（2026-11-14 係週六，外匯休市，0 交易屬正確輸出） |
| 上週週報實跑 | `docs/reviews/weekly/review_2026-11-09_2026-11-15.{html,json}`（2026-11-09～15，數據覆蓋至 2026-11-13；13/11 有 17 個 signal 檔含當週交易） |
| 保留清理 | 週報 12 週 cutoff=2026-08-23：刪 6 個 2026-04/05 舊週報檔，`weekly/index.json` 舊條目同步剪走 |
| 重跑驗證 | 刪產出後重跑 wrapper（--no-commit），檔案完整重生，JSON 數據段逐位一致（僅 `generated_at` 時間戳不同）——證明唔依賴 manual |

## 5. 邊界與未做

- wrapper 只 `git commit`，**唔 push**（`--push` 旗標留畀 job 層决定，同 `tsa-ranking-daily` 05:30 job 加 push 嘅先例一致）。
- 唔掂評分公式、排名腳本、`date_range_review.py` 本體（生成器零改動）。
- VPS crontab 實際兩行未接（本機無法觸達 VPS）——接線動作見 §1，屬營運 lane。
