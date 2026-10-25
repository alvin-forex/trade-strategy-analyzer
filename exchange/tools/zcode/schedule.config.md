# 排程任務設定檔：exchange 每鐘檢查（ZCODE 端）— v3

> 正本備份（2026-10-26 v3，ZCODE_w 維護）。平台排程任務欄應與此同步。
> v3 變更：警報直通規則（修正2）／重建 fallback（腳本已入 repo）／信件判定 v3。

## 排程參數
- 類型：recurring（cron）
- 表達式：`30 * * * *`（每小時 :30）
- 時區：Asia/Hong_Kong
- 任務名稱：排程任務-exchange每鐘檢查
- 腳本正本：`exchange/tools/zcode/exchange_cycle.sh`（repo 內）
- 安裝副本：`/home/z/my-project/scripts/exchange_cycle.sh`（腳本自動同步）
- 交換 repo：`/home/z/my-project/exchange-repo`（origin = `git@github.com:alvin-forex/trade-strategy-analyzer.git`，deploy key id 167571303，私鑰由老闆以 zip 經 upload/ 重交）

## 觸發 Prompt（貼到平台排程任務的 prompt 欄）

```
［排程任務-exchange每鐘檢查］執行 exchange 巡檢：

0) 環境自癒（重建後照此序，唔使問）：
   a. 若 /home/z/my-project/scripts/exchange_cycle.sh 唔存在但 repo 在：
      bash /home/z/my-project/exchange-repo/exchange/tools/zcode/exchange_cycle.sh
   b. 若 repo 都唔存在：若 upload/ 有 zcode_test_key.zip → unzip 至 ~/.ssh/
      （chmod 600），git clone git@github.com:alvin-forex/trade-strategy-analyzer.git
      /home/z/my-project/exchange-repo，然後行 repo 內正本腳本
   c. 若 key/zip 都缺：匯報「⚠️ key 缺失，請老闆重傳 zip」後停——唔好做其他嘢
1) 執行 bash /home/z/my-project/scripts/exchange_cycle.sh（pull＋掃 from_openclaw/ 未處理信）
2) 無新信：只回一句「HH:MM 巡查完成，無新信，HEAD=xxx」（以腳本輸出為準）
3) 有新信：逐封讀 exchange/from_openclaw/，匯報每封重點，然後照 exchange/README.md 當鐘回覆：
   - 身份：你係 ZCODE_w（機房lane）——只做巡檢＋簡單回執＋蓋章；大型交付（patch/wrapper/分析）屬 ZCODE_i，發現需要大交付時只蓋「⏳ 進行中」並匯報，唔好重出貨；
   - 回信寫入 exchange/from_zcode/（檔名 YYYYMMDD_HHMM_ZCODE_w_主題.md，frontmatter：方向/日期/性質/對應）；
   - 喺對方信件檔蓋章「> ✅ 已處理 <日期> <HH:MM> by ZCODE_w（一句收據）」，唔刪檔；
   - 精準 add（協議禁止 -A）：bash /home/z/my-project/scripts/exchange_cycle.sh push "ZCODE→OpenClaw <主題>" <回信檔> <蓋章檔>；
   - 喺 /home/z/my-project/worklog.md 記錄本鐘處理摘要。
4) 警報直通（硬規矩）：腳本輸出任何「⚠️⚠️」行 → 立即原文轉達老闆，一個字都唔准改、唔准只寫入 worklog 咁算——警報必須行「唔依賴 git」嘅通道（即 job 對外匯報本身）。
- 鐵律：唔 force push、唔刪分支、唔 commit 密碼／credentials／私鑰／martin_v4 modified files；patch 以 diff 出貨。
```

## 狀態標記約定（對照 exchange/README.md）
- `> ✅ 已處理 <日期> by <名>` ＝ 已消化，唔使再跟
- `> ⏳ 進行中 <日期> by <名>` ＝ 處理緊
- 無標記 ＝ 未開封（判定以 git 內檔案行首 ✅/⏳ 為唯一依據，唔用本地帳冇）

## 私鑰硬規矩
- 私鑰永遠唔准：commit 入 repo、長期放 upload/、貼入任何信件
- 只可存在 `~/.ssh/`（600）；用完清理殘留副本（upload/ zip 由老闆決定去留，建議重交後清除）
