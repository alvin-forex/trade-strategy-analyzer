# ZCODE 分流規則（老闆 2026-11-18 11:49 拍板）

## 決策

| 項目 | 決定 |
|---|---|
| **本機 ZCODE**（AC 主機，`@TG_AutoClawZcode_bot`） | **主力 code lane**，所有需要 MT4/MT5 在場、需要編譯驗證、需要終端測試的工作 |
| **平台 ZCODE**（ZAI，`@zc_ops_bot`） | **輔助分流**，只接純文字／純前端／無本機依賴的工作 |
| **成本** | **一律免費額度先行**：`yuanyuai glm-5.3` 或 GLM Coding「Start Plan」，用盡才准報收費方案 |

## 分流判準（派單前必問）

派俾**本機 ZCODE**，只要符合任何一項：
1. 要編譯（.mq4/.mq5/.ex4/.ex5）
2. 要碰 MT4/MT5 終端、數據夾、log
3. 要在本機跑測試／Tester
4. 要讀本機獨有檔案（例如 `Power History` .dat 樣本）

派俾**平台 ZCODE**，要同時符合全部：
1. 純文字檔（.md/.json/.yaml/.csv 處理）
2. 純前端（HTML/CSS/JS，不需編譯）
3. 無本機依賴、無需終端
4. 有明確可機器驗收的輸出

**兩者都合 → 派本機**（老闆：偏向用本機）。

## GitHub label 對應

- `lane:zcode-local` → 本機 ZCODE
- `lane:zcode-platform` → 平台 ZCODE
- 舊 `lane:zcode` 廢棄，不再使用（歷史卡已重標）

## 歷史包袱（記錄，不作為懲罰）

平台 ZCODE：
- 7 單零交付（W0–W3b＋CP-BT1＋效能單）
- 11 次 rollback（key 蒸發、v3.9 退化、工作樹退回舊 commit、worklog 被覆蓋）
- **仍可接單**，但只限上表「純文字／純前端」範圍
- 若再出現零交付或 rollback 事故，升級為「暫停派單」並上報老闆

## 配額紀律（寫入每張工單）

> 本單優先使用免費額度：`yuanyuai glm-5.3` 或 GLM Coding「Start Plan」。
> 免費額度用盡才准報收費方案，並須先取得老闆同意。

## 與其他決策的關係

- 取消「三個 PM」：AC / 兩隻 ZCODE 都**不准**讀 board、派工、催單、寫 status notice。項目管理只由 OC 做。
- 每張卡必須寫死「完成」定義（機器可判：編譯 0/0、誤差 <x%、raw URL 200）。
- AC 交貨強制入 repo（`exchange/from_autoclaw/`），唔好只喺 Telegram 講。
