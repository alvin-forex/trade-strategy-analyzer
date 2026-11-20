# 總計劃表（系統 × EA/指標 × 卡號）

> 版本：2026-11-20 10:0x｜維護：AUTOCLAW（AC lane）｜更新方式：每次巡檢／交貨後更新，並喺 postbox 講一聲
> 用法：所有工作先對「系統代號」，再對卡號；報告／commit 標題請加系統代號（例：`[S1] TierB …`）

## 一、系統清單

| 代號 | 系統 | 涉及 EA／指標 | 資料／產物 |
|---|---|---|---|
| **S1** | CCY Power（原版指標 ＋ 資料管道） | `CCY Power Indicator v1.00`、`CcyPower_TierB_Probe`、`CcyPowerExporter`、`CurrencyPower_v3` | 面板九貨幣值、PowerHistory .dat、ccy_power 網頁 data.json |
| **S2** | Martingale Scanner——**原版行為逆向工程（black-box）＋ 重製**：只複製「輸入→輸出」行為，做到同原版數值一致（parity）；**唔係**研究馬丁格爾理論原理、亦唔涉及策略設計（entry/exit／參數建議屬 LEGEND／老闆） | 原版 `Martingale Scanner v1.00`、重製版 `Extra Martingale Scanner` | TradingHistory v8.5 對照（golden fixture）、165 頁 martin_v4 報告 |
| **S3** | TSA 網站（報告頁／前端） | — | martin_v4／ccy／ranking 等 900+ 頁 |
| **S4** | EA（MT5 先行）＋ TSA Risk Analyzer | `REQUIREMENT_EA_v0.1`、`REQUIREMENT_TSA_Risk_Analyzer_v1.1` | MT5 .mq5 骨架、風險分析器 |
| **S5** | 工作板／CI 基建 | — | Taskboard、regression gate、exchange 通道 |
| **S6** | 協作協議／lane 管理 | — | 握手、規則文件、postbox |

## 二、主計劃表

| 系統 | 卡號 | 工作 | lane | 狀態 | 依賴（等乜） | 死線／下一步 |
|---|---|---|---|---|---|---|
| S1 | #19 | TierB 診斷（釘死 up 定義） | openclaw（AC 執行） | doing | ①ZCODE 交 exporter 或 OC 批截圖 parser ②老闆將面板 TF 由 D1(10) 改 H1(60) | **11-21 12:00 交 STEP3/4 候選搜索 Top 20** |
| S1 | #18 | CCY Power 管道修復（D1/M30 停更＋stale 閘） | openclaw | doing | 等 MT4 側數據源穩定 | P0，本週內 |
| S1 | #21 | 更正 Power History 派工前提 | openclaw | review | 等 AC 確認（本檔已引用其結論） | 待 OC 收貨 |
| S1 | #27 | Extra CCY Power 重製版 | zcode-local | todo | **卡喺 #19 定義未定案**（無定義無法重製） | 待 #19 |
| S2 | #30 | Extra Martingale Scanner 重製版 | zcode-local | todo | 分階段（#34／#35） | 分階段推 |
| S2 | #34 | 階段 1＋2（CSV ingest／層數／週期切分＋hst／波幅帶） | zcode-local | PR 待驗 | OC 驗收（PR） | 原死線 11-20 18:00（早一日交） |
| S2 | #35 | 階段 3＋4（質量閘／SET 診斷／日期段／適配評分／CLI） | zcode-local | PR 待驗 | 建基於 #34，需先 merge | 11-22 18:00 |
| S3 | （無卡） | martin_v4 報告頁邏輯修正（5 實錯＋3 顯示問題） | 待開卡 | 已審查 | 需 OC 指派 lane；AC 審查報告已交（cd8a6d36） | 待 OC 開卡 |
| S3 | #20 | W-FINAL sidebar 18 頁注入 | zcode-local | **逾期**（todo＋doing 兩個 label） | 老闆裁定順延或改期 | 已過 11-18 18:00 |
| S3 | #28 | 兩套報告模板統一性審核 | zcode-platform | todo | 依賴 #34／#35 模板定稿 | P1，本週 |
| S3 | #4 | 前端改讀 Supabase（保留 fallback） | zcode-platform | todo | 等 Supabase 資料穩定 | 未有死線 |
| S4 | #5 | EA 匯出持倉 forex_positions.csv | zcode-local | todo | 等老闆 O1–O4 裁決 | 待裁決 |
| S4 | （無卡） | MT5 EA 骨架 | — | 等指令 | 老闆五條裁決已入檔，策略邏輯未到 → 只准骨架 | 待老闆 O2（策略） |
| S5 | #17 | Taskboard v1（CI 5 分鐘重建 → Pages artifact） | autoclaw | doing | **等老闆兩個 admin 動作**：貼 board.yml＋Pages source 改 GitHub Actions | 今日可收 |
| S5 | #23 | 修 Golden baseline 紅燈 | openclaw | todo | 需先確認 main 既有失敗範圍 | P1 |
| S5 | #24 | 修 L25 page-quality 紅燈 | openclaw | todo | 同上 | P1 |
| S5 | #26 | ZCODE 通道定案（push local/* 即開 PR） | openclaw | doing | 等 ZCODE 確認 clone 已 reset | 11-19 12:00 已生效 |
| S6 | #1 | VERIFY lane 握手（無法觸達 GitHub） | gemini | **blocked** | 老闆決定：卡名 `[verify]` vs label `lane:gemini` 要否統一改名 | 待拍板 |
| S6 | #2 | AC handshake | autoclaw | review | 待 OC 收貨 | — |
| S6 | #16 | zcode 讀新規則並按規則開卡 | zcode-local | todo | AC 已提醒，未回覆 | 待回覆 |

## 三、依賴鏈（一眼睇）

```
S1: #18 管道 ─┐
              ├→ #19 定義定案 ─→ #27 CCY 重製
    #21 前提 ─┘        ↑
                      └── 需要：exporter（ZCODE）／TF 改 H1（老闆）

S2: #34 階段1+2 ─→ #35 階段3+4 ─→ #30 重製完成 ─→ S3 模板統一（#28）

S5: #17 Taskboard ─（待老闆 2 個 admin 動作）→ 之後所有卡可視化
S3: #20 逾期卡 → 待老闆裁定（順延／改期）
S4: 全部等老闆 O1–O4 裁決
```

## 四、每週節奏（建議）
- **AC 巡檢（每 30 分鐘）**：postbox／工作板／probe；有新指示即做。
- **AC 日報（09:00）**：卡數、交付、blocked、probe 狀態；每項附連結。
- **人手裁決點**：①#19 面板 TF（10 秒）②#17 兩個 admin 動作 ③#1 改名 ④#20 逾期卡 ⑤S4 O1–O4 策略規格。

— AUTOCLAW（AC lane）
