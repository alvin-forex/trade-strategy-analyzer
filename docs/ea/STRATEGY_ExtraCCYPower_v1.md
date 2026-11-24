# STRATEGY — ExtraCCYPower v1（策略規格）

- 版本：v1（2026-11-24 12:20 HKT）
- 依據：老闆 11-17 裁決 2（策略由 OC 代建議）＋ 11-24 12:05 方向指示（配合支持阻力位、STC、MACD；沿用之前基本出市模組）＋ 11-24 12:07「批」（#2146）
- 狀態：**DESIGN** —— 呢係待回測驗證嘅假設；實測唔達標即迭代 v2，唔准為湊數 overfit
- 負責：起草 OC｜實作 ZCODE｜驗收 OC＋老闆

## 0. 一句話
貨幣強弱「背離殘差」做主訊號；支持阻力位定位置、STC 定時機、MACD 定方向；基本出市模組離場。

## 1. 實測根據（8 年 D1 數據，2026-11-18 測試）
- 純 POWER DIFF 判方向 50.5%；slope 更差（50.1–50.3%）——power 本體係後鏡（對過去 3 日回報 r=−0.476，對未來 0.07%）
- 唯一站得住：**背離殘差**（Q5 53.3%，USDJPY t=4.28）＋假突破＋數 bar＋多 TF 結構
- 原作者聲稱 power 預測未來 ~40 小時 → 入場 TF＝H4（H1 觀察），D1 做強弱背景

## 2. 訊號鏈（四層全部齊先入場）
1. **主訊號（背離殘差）**：殘差＝實際價格變動 − power 隱含變動；殘差處極端分位（Q1/Q5，Inp 極端分位參數）且開始回返
2. **位置（支持阻力）**：價格距關鍵位 ≤ InpSrAtrMult×ATR；做多近支持、做空近阻力；配合假突破結構——破位後 InpFakeBreakBars 內收回＝假突破，順殘差方向入
3. **時機（STC）**：STC <25 向上轉（多）／>75 向下轉（空）
4. **方向確認（MACD）**：histogram 方向一致，或價格–histogram 背離支持主訊號方向

## 3. 出市模組（基本款）
- TP/SL＝ATR 倍數（InpAtrTpMult 預設 4.0／InpAtrSlMult 預設 2.0）
- 移動止損可選（InpTrailEnable 預設 false；盈利 >InpTrailStartAtr×ATR 啟動）
- 時間出場：持倉 >InpMaxHoldBars 即平（預設 0＝off）
- 訊號反轉出場：主訊號反向極端即平
- 風控出場：DD Guard／Symbol Guard／News Guard（骨架已有，預設 OFF）

## 4. 參數（O3：跟現有做底）
- 底＝骨架 v1.02 現有 21 個 input（General／Lot Sizing／DD Guard—Account／Symbol Guard／News Guard／Diagnostics／Backtest）
- 新增策略組（隨本規格一併生效，老闆 11-24 已批起草授權）：**Signal**（殘差/分位/TF）、**Signal Filters**（S/R＋STC＋MACD 開關同參數）、**Exit**（出市模組）——組名照 ea-repo AGENTS.md §3 程序補入名單（14→17）
- 手數：單層 0.01 起步，InpLotMultiplier 1.00（flat）；多層格網唔啟用

## 5. 標的
- 交易：主要 FX 對（清單照 CCYV3 家族）
- 首階段回測主力 6 對：USDJPY（t 最強）先行，其餘 5 對樣本外覆核

## 6. 驗收（O4）
- **硬指標（老闆 11-24）**：≥1 年回測，月回報 20–30%
- **防背答案（老闆 11-24 批）**：walk-forward——參數只准用 2024-08～2025-08 段優化；2025-11～2026-11 做樣本外覆核。OC 提議樣本外參考線：月回報 ≥15% 且唔爆倉（提議值，同回測報告一齊評，唔係老闆已定線）
- **生存閘（v0.1 A5 照舊）**：8 年回測唔爆倉；編譯 0/0；input 閘照 §8 新公式
- 唔達標 → 出對比報告迭代 v2，唔准靜靜雞改參數湯數
