# REQUIREMENT — TSA Martingale Risk & Currency Fit Analyzer（MT5 先行）

- 版本：v1.1（2026-11-17 20:20 HKT）
- 狀態：**provisional — 第 5 項驗收標準待老闆拍板**
- 業主：Alvin（老闆）｜需求落地：OpenClaw（中央派工）｜實作：ZCODE code lane
- 技術真相來源：`docs/martingale/TSA_Martingale_Technical_Docs_v1.0.md`（以下簡稱 Spec）
- 承接工單：`exchange/from_openclaw/` 內 W0／W1／W1.5／W2a／W2b／W3a／W3b

---

## 0. 老闆 2026-11-17 五條裁決（原文 + 解讀）

| # | 老闆原文 | 本文件落地解讀 |
|---|---|---|
| 1 | MT4 / MT5，先做好 MT5 的 | 平台支援次序：**MT5 先行**（SET 解析、Adapter、PipValue/Margin 全部以 MT5 為第一公民）；MT4 支援排後，架構預留但唔做首批實作 |
| 2 | Strategy logic（entry/exit、grid or not、indicators）由 LEGEND 俾你 | 策略邏輯**唔由開發方發明**。系統只做「讀入 + 建模 + 風險計算」；策略本體由 LEGEND 提供（SET 檔 + 規格 §6 Adapter） |
| 3 | Inputs & parameter ranges，參照 REQUIREMENT 的參數 | 參數以 SET 檔實際欄位為準，映射照 Spec §4 Canonical Strategy Model ＋ §6 EA Adapter Rules；**唔准自創參數**，缺欄位即報 MISSING |
| 4 | Risk rules（max lots、drawdown limits）就係唔知先要個系統 | **風險規則就係本系統嘅交付內容**——由系統計出最大手數、各層 DD、資本佔用、可生存性（Spec §8–§12、§17）；唔係由用戶預先提供 |
| 5 | Acceptance criteria（backtest numbers、compile clean 等）未有諗法 | 由 OpenClaw 提議具體驗收標準（見第 4 節），**待老闆確認即生效**；未確認前以「機器閘」為準 |

---

## 1. 目標（What）

一個可重現、可審計嘅靜態分析系統：輸入 **MT5 EA 嘅 SET 檔** + **波幅資料**，輸出：
1. 馬丁格爾網格模型（層數、累積距離、累積手數、加權入市、回本距離）
2. 風險模型（逐層 DD、金額＋點數雙軌、資本佔用、可生存性）
3. 波幅適配（TF Fit：主適配／壓力適配）
4. 可重現報告（Spec §23 reproducibility 13 欄位）

## 2. 非目標（Not in scope — Phase 1）

- 唔做自動下單、唔做 EA 執行、唔接 MT5 帳戶 API
- 唔做策略優化／參數尋優
- 唔做 MT4 首批（架構預留）
- 唔做任何公開頁面嘅「適合性建議」以外嘅投資建議字句（Spec §30 邊界聲明常駐）

## 3. 範圍與模組（照 Spec §3）

| 模組 | 內容 | 對應工單 |
|---|---|---|
| repo 骨架＋工具鏈＋CI | Vite＋Vitest＋TS strict，`tsa-risk-analyzer/` 頂層目錄 | W0 |
| SET 讀取＋Adapter Registry | MT5 SET 先行；六類錯誤碼 | W1／W2a |
| 波幅匯入管線＋檢核 | xlsx → VolData，六類錯誤碼＋凍結機制 | W1 |
| ADMIN／公開頁（佈局） | staticrypt 上載、雙版本比較、公開頁範圍＋狀態欄 | W1.5 |
| TF 五級解析＋GridSpec | 主 TF 解析次序 | W2b |
| Risk Engine（DD 雙式） | 直接式／增量式必須相等（斷言） | W3a |
| PipValue／Margin／XAU／Policy | 匯率方向規則、不變式、XAU 三檔、BR-12 | W3b |
| TF Fit／Report Composer | 主適配＋壓力適配、13 欄位可重現報告 | W4＋（待派） |

## 4. 驗收標準（提議，待老闆拍板）

**A. 機器閘（必過，唔靠人眼）**
1. `npm test` 全綠、`npm run lint` 零錯、CI 綠
2. DD 雙式相等斷言（直接式 ≡ 增量式）通過
3. Margin 不變式：Σ逐層 margin ≡ margin(總手數)；Excel Deposit Load 重複乘 bug 唔准遷移
4. PipValue 三案例（EURUSD／USDJPY／XAUUSD）手算全對
5. 六類檢核錯誤碼 fixtures 全紅燈攔截（83103／32+152／395=632／286-546.／1667--2258／5820-5223 等）
6. 對標基準＝Spec §5 公式手算值（provisional）——現行 Excel §26 有已知 bug，只作參考
7. 報告可重現：同輸入 → 同輸出（13 欄位含 ENGINE_VERSION）

**B. 人眼閘**
8. 公開頁未登入見唔到任何上載入口；狀態欄顏色＋文字並排
9. 錯誤未確認時 artifact 顯示「凍結中 — 唔准發佈」

**C. 明確唔適用**
- 「backtest numbers」：本系統唔係 EA、唔交易，Phase 1 不適用
- 「compile clean」：只適用於 MQL 部分（如日後做 EA 端整合）；本系統以 TS 編譯零錯替代

## 5. 紅線

- 改動只准喺 `tsa-risk-analyzer/` 之內；`docs/`、`exchange/`、`scripts/` 一律唔郁
- 唔准 force push；PR＋OC 統一驗收
- 免費額度先行（yuanyuai glm-5.3／GLM Coding Start Plan）
- 任何規格歧義 → 寫信問，唔准自創

## 6. 交付節奏

W0 → W1 → W1.5 → W2a → W2b → W3a → W3b，一單一 PR；每單完成寫 `exchange/notify/from_zcode/` 三行通知。
