# COPY TRADE 分析系統　核心 Workflow（按模組）

**版本** v1.0　·　**日期** 2026-10-26　·　**配套** `COPY_TRADE_SYSTEM_SPEC_v1.1.md`

---

## 0. 一句話總覽

```
MT5 規格 ─┐
          ├→ M0 規格 → M1 計算器 → ┐
歷史價 ───┘                          ├→ M4 Copy 時機 ─┐
                                     │                 ├→ M6 匯總 → M7 呈現
交易記錄 ──→ M2 正規化 → M3 分層 ────┴→ M5 TP/SL ──────┘
```

**資料只向一個方向流。** 下游不准回頭改上游，上游不准預測下游需要什麼。

---

## 1. 模組總表

| # | 模組 | 輸入 | 輸出 | 耗時 | 可重跑 |
|---|---|---|---|---|---|
| M0 | Symbol Spec Exporter | MT5 商品清單 | `symbol_specs.csv` | 秒級 | 每日 |
| M1 | Pip/Margin Calculator | M0 ＋ 價格 | `pip_margin.parquet` | 秒級 | 按需 |
| M2 | Trade Normalizer | AlgoForest CSV ×12 | `trades` 表 | 分鐘 | 冪等 |
| M3 | Martin Reconstructor | `trades` | `cycles`、`layers` | 分鐘 | 冪等 |
| M4 | Copy Timing Analyzer | M1＋M3＋M5 分鐘價 | `copy_sims` | 十分鐘 | 冪等 |
| M5 | TP/SL Optimizer | M1＋M3＋M1 分鐘價 | `tpsl_grid` | 十分鐘 | 冪等 |
| M6 | Performance Tracker | M3+M4+M5 | `perf_periods` | 秒級 | 冪等 |
| M7 | Presentation | M6＋M1 | HTML／PDF | 秒級 | 冪等 |

**冪等**＝同一輸入重跑結果完全一樣。除 M0 外全部必須冪等，否則無法除錯。

---

## 2. M0　Symbol Spec Exporter

**唯一職責**：向 MT5 要權威合約規格。不推算、不補值、不猜。

| 項目 | 內容 |
|---|---|
| 觸發 | 每日開盤前；或新增商品時 |
| 輸入 | MT5 已訂閱商品清單（實測 40 個） |
| 過程 | MQL5 Script 逐商品呼叫 `SymbolInfoDouble` / `SymbolInfoInteger` |
| 輸出 | `symbol_specs.csv`：symbol, digits, point, tick_size, tick_value, contract_size, margin_initial, leverage, swap_long, swap_short |
| 驗收 | ① 商品數 ≥ 40　② 抽 3 個商品與 MT5 介面手動核對一致　③ `tick_value > 0` 全部成立 |
| 失敗模式 | 商品未下載 → 該列缺席（**不准填預設值**） |
| 下游影響 | 缺 spec 的商品，M1 一律拒絕計算 |

**為什麼必須是第一個**：`tick_value` 已內含合約大小與報價幣換算。自己用公式推，在 JPY 交叉盤會偏 5–15%。這是唯一能一次性消滅量級錯誤的方法。

---

## 3. M1　Pip / Margin Calculator

**唯一職責**：把價格與手數轉成美元。**全系統只有這一層可以算錢。**

| 項目 | 內容 |
|---|---|
| 觸發 | M0 更新後；或查詢特定日期時 |
| 輸入 | `symbol_specs` ＋ `prices_daily`（或即時價） |
| 過程 | `pip_value = tick_value × (pip_size / tick_size)`；`margin = lots × contract_size × price / leverage` |
| 輸出 | `pip_margin`：以 (symbol, date) 為鍵的 pip_value、margin_per_lot |
| 驗收 | ① 用 14,013 真實成交反算，與實測中位數差異 < 2%　② USD 報價商品 pip_value 恆定（實測漂移 < 6%） |
| 失敗模式 | 缺 M0 規格 → 拋錯終止，**不估算** |
| 下游影響 | 全部依賴此層。此層錯，全錯 |

**三個必須分清的層次**（實測）：

| 層 | 內容 | 例 |
|---|---|---|
| 1 | pip 單位慣例 | EURUSD 0.0001／USDJPY 0.01／XAU 0.1 |
| 2 | 合約大小 | EURUSD 100,000／XAU 100 oz／BTC 0.01 枚 |
| 3 | 報價幣 → USD 匯率 | 非 USD 報價者會漂移（實測 5–20%/月） |

層 1×2×3 = pip_value。三者任一錯，金額按倍數錯。

---

## 4. M2　Trade Normalizer

**唯一職責**：把 12 個格式不一的 CSV 變成乾淨、可溯源的表。

| 項目 | 內容 |
|---|---|
| 輸入 | `data/forex-forest-signals-page-*.csv`（12 檔、14,041 單） |
| 過程 | ① 日期強制 `%d/%m/%Y` ＋ 與檔案時序交叉驗證　② 空商品／1970 時間標記 REJECT　③ 欄位對齊　④ 寫入並保留 `source_file`+`source_row` |
| 輸出 | `trades` 表（含 `qc_flag`：OK／SUSPECT／REJECT） |
| 驗收 | 入庫數 ＋ 拒收數 = 14,041；隨機抽 10 筆與原始 CSV 逐字對得上 |
| 失敗模式 | 日期解析失敗率 > 1% → 終止並報告（代表格式假設錯） |

**最危險的陷阱**：`DD/MM` 若誤讀成 `MM/DD`，2026-04-01 會變 2026-01-04。所有按星期、按月份的分析會全部錯位，**而畫面完全正常**。所以必須交叉驗證，不能只信 `strptime` 沒拋錯。

---

## 5. M3　Martin Reconstructor

**唯一職責**：由手數序列還原馬丁層級，切出 cycle。

| 項目 | 內容 |
|---|---|
| 輸入 | `trades`（已正規化） |
| 過程 | ① 按 `magic + symbol + direction` 分組　② 時間窗內遞增收單歸為同一 cycle　③ 手數排序配層　④ 驗證倍數 |
| 輸出 | `cycles`（約 1,200）、`layers`（約 6,000） |
| 驗收 | 層級倍數偏離 ×1.5 ≤ ±5%（實測 1.478–1.667，即有充裕餘裕） |
| 失敗模式 | 倍數偏差 > 5% → 該 cycle 標 `REJECT`，不進下游 |

**實測可還原 15 層**：0.02 → 0.03 → 0.05 → … → 5.84，倍數 1.478–1.667。

---

## 6. M4　Copy Timing Analyzer

**唯一職責**：模擬「遲 N pips 才跟單」的結果。

| 項目 | 內容 |
|---|---|
| 輸入 | `cycles` L1 入場點 ＋ M1 分鐘價 ＋ M1 pip_value |
| 過程 | 對每個 cycle，分別掃 Copy on Profit（5/10/15/20 pips）與 Copy on Lose（10/15/20/25 pips），逐 tick 判定有否觸及門檻 |
| 輸出 | `copy_sims`：mode, wait_pips, entry_time, entry_price, profit_usd, margin_usd, **outcome（FILLED／MISSED）** |
| 驗收 | ① 每個 cycle 都有對應 sim　② `MISSED` 有記錄且佔比合理　③ 不延遲（0 pips）情境的 simulated 盈虧 = `trades` 實際盈虧 |
| 失敗模式 | 分鐘價缺該時段 → 標 `NO_DATA`，不可用最近價代替 |

**`MISSED` 為什麼必須記**：若只統計成功等到價格的 cycle，成交率會虛高至 100%，「等 30 pips 更好」可能只是因為等不到的那些被忽略了——結論會完全反向。

**驗收第 ③ 項是全系統最重要的一條對帳測試**：0 pips 情境必須完全重現真實盈虧。這條過了，代表 M1 的 pip_value 正確。

---

## 7. M5　TP/SL Optimizer

**唯一職責**：掃描止盈止損組合。

| 項目 | 內容 |
|---|---|
| 輸入 | `cycles`／`layers` ＋ M1 分鐘價 ＋ M1 pip_value |
| 過程 | TP ∈ {20,25,30,40}、SL ∈ {15,20,25,30} 網格；以 **M1 逐筆**判定先後次序 |
| 輸出 | `tpsl_grid`：tp_pips, sl_pips, hit_tp, hit_sl, profit_usd, max_dd_usd |
| 驗收 | ① 同時觸及 TP/SL 的 bar 用 M1 細分判定，抽 20 筆核對　② 網格完整（4×4） |
| 失敗模式 | M1 缺資料 → 標 `AMBIGUOUS`，不猜 |

**為什麼要 M1 而不能用 H1 收盤**：同一根 H1 內可能先觸 SL 後觸 TP，或反之。用收盤判斷等於隨機選一個答案。

---

## 8. M6　Performance Tracker

**唯一職責**：把逐筆結果匯總成週／月／季／年。

| 項目 | 內容 |
|---|---|
| 輸入 | `cycles`、`copy_sims`、`margin_req`、`tpsl_grid` |
| 過程 | 按 period_type（W/M/Q/Y）× strategy × symbol 聚合 |
| 輸出 | `perf_periods`：trades, net_profit, win_rate, profit_factor, max_dd, **margin_peak**, **return_on_margin** |
| 驗收 | 各期淨利總和 = 全期淨利（誤差 < 0.01 USD） |
| 失敗模式 | 加總不符 → 終止（代表有交易被重複或漏計） |

**兩個非標準指標**：

- `margin_peak`：該期峰值保證金佔用
- `return_on_margin` = 淨利 ÷ margin_peak

不用「本金回報率」，因為同一筆本金可並行跑多個策略。用峰值保證金作分母，才能比較資金效率。

---

## 9. M7　Presentation

**唯一職責**：顯示。**不准計算任何東西。**

| 項目 | 內容 |
|---|---|
| 輸入 | `perf_periods` 等已算好的表 |
| 過程 | 讀表 → 套版 → 出 HTML／PDF |
| 輸出 | Dashboard、策略明細頁、PDF 報告 |
| 驗收 | 頁面每個數字都能在 SQLite 直查到相同值（抽 10 個） |
| 失敗模式 | 缺資料 → 顯示「—」並標示原因，**不准用估算值填補** |

---

## 10. 三道閘門（跨模組）

| 閘門 | 位置 | 條件 | 動作 |
|---|---|---|---|
| G1 | M2 → M3 | 日期解析失敗率 ≤ 1% | 超標終止 |
| G2 | M3 → M4/M5 | 層級倍數偏離 ≤ ±5% | 超標拒收該 cycle |
| G3 | M1 → 全下游 | 商品有 M0 規格 | 缺則不出數字 |

**原則：寧可空白，不可估算。** 錯的數字比沒有數字危險得多——沒有數字你會去查，錯的數字你會直接拿去下單。

---

## 11. 執行順序與依賴

```
DAG（有向無環）
M0 ──→ M1 ──┬──→ M4 ──┐
             ├──→ M5 ──┤
M2 ──→ M3 ───┴─────────┴──→ M6 ──→ M7
```

**首次全量執行**（約 30 分鐘）：

```bash
./run_m0_specs.sh          # 秒級
./run_m1_calc.py --all     # 秒級
./run_m2_normalize.py      # 分鐘
./run_m3_layers.py         # 分鐘
./run_m4_copy.py           # 十分鐘
./run_m5_tpsl.py           # 十分鐘
./run_m6_periods.py        # 秒級
./run_m7_render.py         # 秒級
```

**日常增量**（新 CSV 進來後，約 5 分鐘）：

```bash
./run_m2_normalize.py --incremental
./run_m3_layers.py --incremental
./run_m4_copy.py --incremental
./run_m5_tpsl.py --incremental
./run_m6_periods.py && ./run_m7_render.py
```

M0／M1 每日跑一次即可（匯率與規格不會分鐘級變動）。

---

## 12. 階段驗收對照

| 交付階段 | 包含模組 | 驗收方式 | 估時 |
|---|---|---|---|
| P0 | M0 | 商品 ≥ 40，抽 3 個對 MT5 | 0.5 天 |
| P0 | M1 | 14,013 樣本反算差異 < 2% | 1 天 |
| P0 | M2 | 14,041 對帳 | 1 天 |
| P1 | M3 | 倍數偏離 ≤ ±5% | 1 天 |
| P1 | M4 | 0 pips 情境重現真實盈虧 | 1 天 |
| P1 | M5 | M1 先後判定抽 20 筆 | 1.5 天 |
| P2 | M6 | 分期加總對帳 | 1 天 |
| P2 | M7 | 頁面 vs SQLite 抽 10 個 | 2 天 |
| | | **合計** | **9 天** |

---

## 13. 最關鍵的一條對帳測試

整個系統的正確性，最終收斂到一個測試：

> **M4 在 `wait_pips = 0` 時，模擬出的每一筆盈虧，必須等於 `trades` 表的真實盈虧。**

這條過了，代表 M0 規格、M1 pip_value、M2 正規化、M3 分層、M4 模擬全部一致。

這條不過，任何下游數字都不可信——包括漂亮的回測曲線。

---

*OpenClaw · 2026-10-26*
