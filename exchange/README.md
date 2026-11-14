# Exchange 信箱 — OpenClaw ↔ ZCODE 直接交換機制

> 老闆（TG 920593269）裁決 2026-10-24：唔再做中間人傳檔。
> OpenClaw（data lane）同 ZCODE（code lane）都有 TSA repo 寫入權限，
> 直接用 git 交換任務指示、patch 包、回批、供料。Telegram 只做通知。

## 目錄結構

```
exchange/
├── from_zcode/        # ZCODE → OpenClaw：任務指示、patch 包、回批
├── from_openclaw/     # OpenClaw → ZCODE：部署結果、供料、回批
└── templates/         # 訊息模板（複製去用，唔好直接改）
```

## 點用（5 步）

1. **寫檔**：放入自己嘅目錄，檔名 `YYYYMMDD_HHMM_<主題>.md`
2. **精準 add**：`git add exchange/from_zcode/20261024_1408_任務Bpatch.md`（唔准 `-A`）
3. **commit**：message 前綴 `exchange:` ＋ 方向，例如
   `exchange: ZCODE→OpenClaw 任務B五合一patch`
4. **push**：`git push origin main`
5. **通知**：喺 Telegram 講聲「exchange/from_xxx/ 有新嘢」，內容以 repo 為準

## 規則（雙方都要守）

1. **只讀對方目錄**，唔准改對方嘅檔；有異議就喺自己目錄開新檔回批
2. **已處理嘅檔**：喺檔頂加一行 `> ✅ 已處理 <日期> by <OpenClaw|ZCODE>`，**唔刪檔**（留審計）
3. **拉取前確認工作區乾淨**：`git status --porcelain` 應該係 0 或者只有自己啲檔
4. **patch 以 diff 形式出貨**，唔直接 push code 改動；部署由 data lane 執行
5. **大檔案（zip／csv 樣本）直接入 repo**，GitHub 單檔上限 100MB
6. **永遠唔好 commit**：密碼（`tsa_pw.txt` 只可以引用路徑）、`martin_v4` modified files、任何 credentials
7. **唔 force push、唔刪分支**；衝突就 rebase/merge 處理
8. **職責分離不變**：code 全部 ZCODE 出；OpenClaw 只做部署／測試／RUNBOOK／驗收

## 狀態標記約定

- 檔頂 `> ✅ 已處理 <日期> by <名>` ＝ 對方已消化，唔使再跟
- 檔頂 `> ⏳ 進行中 <日期> by <名>` ＝ 對方處理緊
- 無標記 ＝ 未開封

## 2026-11-14 更新：notify/ 目錄與新 lane
- 通知目錄（三行、<1KB、與正式信同一 commit）：
  exchange/notify/{from_openclaw, from_zcode, from_gemini, from_gemini_fast, from_autoclaw}/
- lane 目錄：from_gemini／from_gemini_fast（gemini lane，2026-11-14 老闆叫停暫存）、from_autoclaw（PM lane，2026-11-14 啟用）
- 處理狀態以**收方回批**為準；收方唔改對方目錄檔案（審計留雙方原稿）
- 首行三欄：對象／環境／模型

## 派工路由（2026-11-14 記錄現狀）
- code 改動 → ZCODE：現時兩個來源並行——OpenClaw 直派（16:20 B 包）＋ AUTOCLAW 介面規格派（2200／issue #3）。統一入口未裁決；回報一律四欄（commit/run/changed/evidence）
- 數據／板面／報告／cron → OpenClaw（data lane）
- 任務真值：TASKS.md 私有；repo 鏡像＝exchange/tasks_snapshot.md（脫敏，板面更新時同步）
