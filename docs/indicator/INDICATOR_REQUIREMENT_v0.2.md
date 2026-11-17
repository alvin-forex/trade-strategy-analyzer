# 波幅指標需求書 v0.2（MT5 引擎先行）

- 版本：v0.2（2026-11-17 22:20 HKT）｜**取代 v0.1（v0.1 從未 commit，作廢）**
- 作者：AutoClaw（AC，規劃）｜落地 commit：OpenClaw（中央派工）｜實作：ZCODE（@TG_AutoClawZcode_bot）
- 老闆拍板：2026-11-17 21:18「ok 就開工」；21:07「想用 MT5 做因為可以靈活運用 MCP 做每日更新」
- 前文：`docs/martingale/TSA_Martingale_Technical_Docs_v1.0.md`（TSA 分析器規格，另有線）

---

## 1. 兩條交付線

| 線 | 技術 | 用途 | 階段 |
|---|---|---|---|
| **A 引擎＋MCP** | Python + 官方 `MetaTrader5` 套件 + MCP server | 每日自動出波幅表、餵網站 | **P1（先行）** |
| **B 指標** | MQL5（MT5 圖表＋面板） | 對照原 Scanner、人手分析、比較模式 | P2 |
| C MT4 兼容 | MQL4 | 舊環境 | P3（如仍需要） |

**平台決策**：MT5 先行。理由：MT5 有官方 Python API（一級公民）；MCP 生態成熟（現成 server 至少四隻）；Vantage／Alpari 兩間都有 MT5 demo。
MCP 控制嘅係**數據同計算**，唔係圖表指標物件——呢點要講清楚，唔好混淆。

## 2. 核心算法（兩線共用同一份規格）

- **波段切分**：ZigZag(Depth 12 / Deviation 5 / Backstep 3) **自家實作**（唔准用內建）+ Merge Percentage 35%
- **分檔**：按波段**條數**切 80% / 15% / 5%
  （已用實機數據驗證：39 / 7 / 3 段 = 79.6% / 14.3% / 6.1%）
- **分界計法**：候選 A = percentile nearest-rank；候選 B = Excel `PERCENTILE.INC` 插值
  → **實作必須兩種都支援，可切換**，用 parity 決定邊個對
- **pip 換算**：主要貨幣對 10 points = 1 pip；非主要品種（XAU 等）以最後一位小數為 1 pip（自動讀 `symbol_digits`）

## 3. 容差標準（三層，取代「大致一樣」）

| 場景 | 標準 |
|---|---|
| 同券商同窗口重跑 | **零容差** |
| 跨券商（Vantage vs Alpari） | 總段數 ±2；每桶段數 ±1；Total bars ±3%；桶邊界 ±5% |
| 對原 Scanner（同券商同窗口） | 段數完全一致；bars ±1%；pips ±2% |

## 4. 溯源欄位（每次輸出必帶）

`broker`、`server`、`symbol`、`symbol_digits`、`tf`、`window_from`、`window_to`、`params`、`engine_version`、`calc_method`

## 5. 多券商

- 結果按 broker **分開儲存**，不混算
- **比較模式**：讀兩個 broker 各自匯出嘅 CSV，並排比較（同商品同窗口）——S4 階段功能

## 6. Parity 驗收基準（AC 提供，ground truth）

窗口：`2026.09.17 02:00 → 2026.11.16 17:00`，EURUSD H1，參數 (12)(5)(3)(35%)

| 項目 | 目標值 |
|---|---|
| 總段數 | 49 |
| 三檔段數 | 39 / 7 / 3 |
| Total bars | 631 / 210 / 162 |
| Average bars | 16.2 / 30.0 / 54.0 |

**判定次序**：先對 bars（切分正確性）→ 再對 pips（換算正確性）。
⚠️ 面板「Range」欄語義未確認（疑似同 Total/Average 用唔同度量）→ **不可作驗收標準**。

## 7. 交付階段

| 階段 | 內容 | 驗收 |
|---|---|---|
| **A1** | 波浪提取 → `waves.csv`（`idx,startTime,endTime,bars,amplitudePips`） | 可重跑一致；同窗口 49 段 |
| **A2** | 分檔統計（兩種 percentile 法可切換）→ 波幅表 | 39/7/3、631-210-162、16.2-30.0-54.0 |
| **A3** | MCP server（`get_rates` / `extract_waves` / `compute_buckets` / `export_table`） | 每日自動更新跑通 |
| **S4** | 多券商比較視圖 | Vantage vs Alpari 並排 |
| **P2** | MQL5 指標（圖表＋面板） | 對照原 Scanner 視覺 parity |

## 8. 硬性約束（派工時寫入工單）

1. **唔准用 MT4/MT5 內建 ZigZag 指標**（要自家實作，確保可移植＋確定性）
2. **唔准自創算法**；未確認嘅寫入 `ASSUMPTIONS.md`
3. 每階段 commit 一次，前綴 `[A1]` `[A2]` …
4. 唔准改動 `docs/`、`exchange/`、`src/`（TSA 分析器）、`mt5/` 以外任何目錄
5. 未獲批准前唔准寫 A1 實作碼（先出設計）
6. 免費額度先行：`yuanyuai glm-5.3` / GLM Coding Start Plan 用盡先用收費 model

## 9. 未決 / 待補

- **v0.2 原文有部分被截斷**：本檔由 AC 2026-11-17 21:18 群組訊息重構，若有遺漏段落，AC 補回即更新。
- 原 Scanner 截圖嗰張 EURUSD H1 49 段——券商未知（AC 講「EURCHF 那張是 Alpari」）。驗證時兩間各跑一次，邊間對得上用邊間做基準。
- 面板「Range」欄語義（同上，不作驗收）。

---

_來源：AC 群組訊息 2026-11-17 #1694（v0.1）、#1702（v0.2）；老闆 #1695／#1698／#1701 拍板。_
