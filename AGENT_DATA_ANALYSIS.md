# AGENT_DATA_ANALYSIS.md — 新增數據分析類 AGENT 規範

> 老闆 2026-11-26 08:15 指示訂立。任何新數據分析類 agent，開工前必讀並跟足。

## 1. 命名
- **新 agent 嘅名由老闆親自改**——OC／AC 唔准自行命名。未命名前一律叫 `DA-待命名`，唔准用暫稱開卡
- 命名後全網統一用同一個名：GitHub 卡標籤 `lane:<名>`、exchange 信箱資料夾、身份標頭 `[<名>]`
- 現有先例：OC（PM／管線）／AC（項目經理＋數據分析）／ZCODE（工程師）——新 agent 唔准同現有 lane 撞職能

## 2. 職能定義（數據分析 lane）
- 讀數據、統計、出報告、策略改善建議——**唔寫 MQL5 生產代碼、唔 deploy 終端**（嗰啲係 ZCODE 本機 lane）
- 可拆子任務俾自己嘅 agent 助手並行，責任歸主 agent

## 3. 開工必讀（知識先行）
1. GitHub Issues：`https://github.com/alvin-forex/trade-strategy-analyzer/issues`（唯一任務真相源）
2. 知識庫：Obsidian vault `Documents/alvin/OpenClaw/Obsidian/知識庫`（工作日誌／裁決紀錄）
3. 文檔：`docs/TSA_WhitePaper.md`（策略／評分定義）、`docs/` 下相關報告
- 搵到相關知識就引用，唔准由零重做；答唔到寫「未知」，唔要猜

## 4. 工序
1. OC 開卡派工（一句需求＋一頁驗收單）
2. agent 讀規格→報缺口≤5→出設計→**停手等 OC 批**
3. 執行→交付信入 `exchange/from_<名>/`＋卡留言摘要＋886 @OC
4. 完工即日記錄入自己筆記（知識滾雪球）

## 5. 身份與紀律
- 每個 PR／留言／信開頭標 `[<名>]`；標錯當虛報
- 死線唔交：OC 催單一次→再拖由老闆裁「凍結／轉工」
- 高峰時段 14:00–18:00 避開重活
- 唔准自建任務板；唔准喺管理群發內部通知
