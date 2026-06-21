# PRD：交易策略分析系統（Trade Strategy Analyzer）

> **版本：** v0.9（v5 統一評分 + EA_MAP 去重 + QA 加強）
> **日期：** 2026-06-19
> **前一版本：** v0.8（2026-05-25）
> **作者：** 丁蟹 + Alvin
> **狀態：** 已實作，持續迭代中

---

## 1. 背景與目標

### 1.1 問題
Alvin 在 AlgoForest（Forex Forest）平台管理多個信號頁（如 #14581），每個信號頁跑不同的 EA 策略。目前：
- 只能從平台下載 `.csv` 交易數據和 `.set` 策略設定檔
- 缺乏系統化方法分析策略的**入市準確性**和**性價比**
- 無法從歷史交易中提煉出哪些策略適合 Copy Trade
- 策略知識散落各處，沒有統一記錄

### 1.2 目標
建立一個 **交易策略分析系統**，實現：

**目標一：策略準確性分析**
- 評估每筆交易的入市質量（入得啱唔啱、入得快唔快）
- 記錄策略的入市條件、濾鏡、參數等完整設定
- 長期建立策略知識庫，協助設計應對不同市況的策略

**目標二：Copy Trade 策略篩選**
- 從交易數據中識別高勝率、高性價比的策略
- 分析單層 vs 多層（馬丁）交易的表現
- 建議最優 TP/SL 設定
- 評估 Copy on Profit vs Copy on Lose 的適用性

**目標三：DDE v3 Copy Strategy 評分排名**
- 用統一嘅 DDE v3 公式對所有信號進行跨策略比較
- 產生排名總表，識別最佳 Copy 信號
- 為每個貨幣對、每個層數提供精細化建議
- **Lot-Based 層級偵測**：用 lot 數量判斷層數（取代舊 pip-based），與 EA 實際馬丁層級一致
- **模組化架構**：`dde_v5_scorer.py` 為核心計算引擎，`generate_signal_ranking_v5.py` / `generate_ranking_ccy_v5.py` 生成排名頁面，`config.py` 為 EA_MAP 唯一真相來源

---

## 2. 輸入數據規格

### 2.1 交易數據（.csv）

來源：AlgoForest 信號頁下載（scraper 或 Windows 手動）

| 欄位 | 類型 | 說明 | 分析用途 |
|------|------|------|---------|
| Open Time | datetime | 開倉時間 | 時段分析、入市時機 |
| Type | string | buy / sell / balance / credit | 方向（非 buy/sell 需過濾） |
| Lots | float | 手數 | 判斷層數（結合 .set pipstep/lotsize） |
| Symbol | string | 貨幣對 | 分組 |
| Open Price | float | 開倉價 | 計算實際點差 |
| Close Time | datetime | 平倉時間 | 倉位重構分組鍵 |
| Close Price | float | 平倉價 | 計算實際點差 |
| Commission | float | 手續費 | 真實成本 |
| Swap | float | 隔夜利息 | 長期持倉成本 |
| Net Pips | float | 淨賺點數 | 方向對唔對、盈虧大小 |
| Net Profit | float | 淨盈虧（$） | 真實收益 |
| Max Profit | float | 最大浮盈（$） | 出場效率 |
| Max Pips | float | 最大浮盈（pips） | 入市時機好唔好 |
| Max Loss | float | 最大浮虧（$） | 風險承受 |
| Max Loss Pips | float | 最大浮虧（pips） | 入市後最大逆境 |
| Magic Number | int | 88=BUY, 77=SELL | 方向、策略識別 |
| Comment | string | SMA BUY / SMA SELL | 策略名稱 |
| Holding Time (Hours) | float | 持倉小時 | 效率分析 |
| Holding Time | string | 可讀格式 | 顯示用 |

**數據過濾規則：**
- `Type=balance` / `Type=credit` 不屬於交易，必須排除
- 只處理 `Type=buy` / `Type=sell` 行
- 此過濾對所有分析指標有直接影響

**數據來源比對：**
- Scraper 版本（即時從 AlgoForest 下載）通常較新鮮
- Windows 手動下載版本可能是較早 snapshot
- 兩者差異通常只有幾行（新交易加入）
- 建議優先使用 Scraper 版本

### 2.2 策略設定檔（.set）

來源：AlgoForest 信號頁下載，key=value 格式。每個 signal 可有多個 .set（按上載日期排列）。

#### EA 家族參數對照

| EA 家族 | 代表版本 | 加倉方式 | LV 層數 | TP 模式 | SL 模式 |
|---------|----------|----------|---------|---------|---------|
| **Dragon Wave (DW)** | v1/v2/v2.10 | LotMul 倍投（×2.5） | 8 | VirtualTP=0（隱藏） | VirtualSL |
| **SMA** | v2/v3/Pro v5 | lotExp 指數遞增 + pipstep | 7-15 | DollarMode + DynamicTP | slInLevel |
| **MKD** | v2/v3/Pro v5 | PipStep 網格 | 6-10 | PipStep 追蹤 | TradeCloseOnlyOnDD |
| **S10** | — | 固定 lotSize（平注碼馬丁） | 0（或 10 層平注） | TrailingStart+Dist | TradeCloseOnlyOnDD |
| **Flash** | — | CheckLevels | 11 | — | — |
| **GEM** | — | 無馬丁 | 0 | — | — |

**S10 特殊說明：**
- `MaxBuyCount=10` / `MaxSellCount=10` = 最大同時持倉數量
- 每層固定 `lotSize=0.15`，無遞增（平注碼馬丁）
- 有 `autoLotSize` 功能（根據賬戶餘額自動調整）
- `TrailingStart=25` / `TrailingDist=5` 替代傳統 TP
- `TakeProfit=0` 表示用 Trailing 替代固定 TP

**LV（馬丁層數）偵測方法：**
- 由 .set 檔案 case-insensitive 計算 `pipstep\d*` / `lotsize\d*` / `LotMul` 等參數
- DW：LotMul 加倉預設 8 層
- SMA：數 pipstep2 到最大 pipstepN
- MKD：數 PipStep1 到 PipStepN
- S10：MaxBuyCount 即為層數，但屬平注碼

---

## 3. DDE v3 Copy Strategy 評分系統

> **核心更新**：取代原有嘅 Entry Score + Strategy Score 兩層架構。DDE v3 專注於 Copy Trade 場景，評估「跟單」嘅可行性同回報。

### 3.1 評分公式

**DDE v3 Score = Trigger Rate (40%) + Alpha Capture Profit (40%) + DDE (20%)**

#### 指標 1：Trigger Rate（觸發率）— 權重 40%

```
Trigger Rate Score = min(trigger_rate × 100, 100) × 0.4
```

- **Copy on Profit**：`trigger_rate = 觸發數 / 盈利交易數`
  - 只計 `net_profit > 0` 嘅交易
  - 觸發判定：`Max Pips >= wait_pips`
  - wait_pips 測試值：5, 10, 15, 20
- **Copy on Lose**：`trigger_rate = 觸發數 / 虧損交易數`
  - 只計 `net_profit <= 0` 嘅交易
  - 觸發判定：`|Max Loss Pips| >= wait_pips`
  - wait_pips 測試值：10, 15, 20, 25

#### 指標 2：Alpha Capture Score（利潤捕捉分）— 權重 40%

**動態百分位評分（0-120 scale）：**

```
baseline = max(signal_P50, global_P25)  # 下限保護
floor = $5.00  # 垃圾交易過濾

if avg_profit >= P75:
    score = 100 + bonus  # bonus capped at 20, total capped at 120
elif avg_profit >= P50:
    score = 70 + (avg_profit - P50) / (P75 - P50) × 30  # 線性插值 70-100
elif avg_profit >= baseline:
    score = (avg_profit - baseline) / (P50 - baseline) × 70  # 線性插值 0-70
else:
    score = 0

Alpha Capture Score = score × 0.4
```

**百分位計算：**
- `compute_signal_percentiles()` — 計算信號級別嘅 P25/P50/P75
- `get_effective_percentiles()` — 小樣本回退（n < 30 時自動混和 global percentiles）
- Global percentiles 基於所有 69 個信號嘅綜合數據

#### 指標 3：DDE（Drawdown Efficiency，回撤效率）— 權重 20%

> **歷史**：取代舊嘅 ETE（Early Trigger Efficiency），因為 ETE 嘅分辨力接近零（96-97% 跨所有 wait_pips）。

```
dd_ratio = |max_loss_pips| / profit_pips  # 單筆交易
dd_ratio = min(dd_ratio, 2.0)            # cap at 2.0
avg_dd_ratio = mean(dd_ratios)            # 該組合平均
DDE Score = max(0, 100 - 50 × avg_dd_ratio) × 0.2
```

**DDE 分佈實況（69 signals）：**
- 中位數：76.0 分
- P25-P75：62.5 - 87.5
- 範圍：0 - 100
- 分辨力遠勝舊 ETE（96-97%）

### 3.2 評級標準

| 分數 | 評級 | 含義 |
|------|------|------|
| ≥ 80 | ⭐⭐⭐⭐ | 高質量，建議 Copy |
| ≥ 60 | ⭐⭐⭐ | 中等，需要評估 |
| ≥ 40 | ⭐⭐ | 偏弱，需要調整 |
| < 40 | ⭐ | 不建議 |

### 3.3 Signal Ranking 計算方法

**Avg Score = mean(所有 non-zero CoP + CoL scores)**

- 分別計算每個貨幣對、每個層數（L1-L4+）、每個 wait_pips 組合嘅 DDE v3 分數
- 過濾 score = 0 嘅組合（trigger_count = 0，即冇足夠數據）
- 取所有 non-zero scores 嘅平均值作為信號嘅 Avg Score

**Cmp = non-zero scoring entries 總數**

- 代表「有幾多個有效嘅評分維度」
- Cmp 越大 = 數據越豐富，評分越可靠

**⭐⭐⭐⭐ count = non-zero entries 中 score ≥ 80 嘅數量**

**⭐⭐⭐⭐% = ⭐⭐⭐⭐ count / Cmp × 100**

### 3.4 LEVEL_RANGES（層數分組）

> **v0.7 已更新為 Lot-Based 層級偵測**，見 Section 13。
>
> 舊版 pip-based 分組（已廢棄）：
> L1: 0-50 pips, L2: 50-100, L3: 100-150, L4+: 150+
>
> 現在用 lot 數量 + SET lot mapping 判斷層數（L1-L9+），與 EA 實際馬丁層級一致。

### 3.5 Copy on Profit vs Copy on Lose

**Copy on Profit（跟單盈利）—「確認方向後再進場」**

| 項目 | 說明 |
|------|------|
| 策略意義 | 信號已浮盈 N pips 後才跟單，犧牲部分利潤換取準確度 |
| 只看 | `net_profit > 0` 嘅盈利交易 |
| 觸發判定 | `Max Pips >= wait_pips` |
| Wait pips | 5, 10, 15, 20 |
| 包含 TP/SL 建議 | ✅ 是（每貨幣對每層數） |

**Copy on Lose（跟單虧損）—「遲進場博反彈」**

| 項目 | 說明 |
|------|------|
| 策略意義 | 信號已浮虧 N pips 後博反彈跟單，減少浮虧同時增加盈利 |
| 只看 | `net_profit <= 0` 嘅虧損交易（或全部交易） |
| 觸發判定 | `|Max Loss Pips| >= wait_pips` |
| Wait pips | 10, 15, 20, 25 |
| 包含 TP/SL 建議 | ❌ 否（CoL 係 recovery 策略，TP/SL 邏輯唔同） |

---

## 4. Martin Detection（馬丁偵測）

### 4.1 偵測類型

| 類型 | 判定條件 | 含義 |
|------|----------|------|
| **Classic Martin** | `profit > 0` 且 `pips < 0` | 馬丁拉平成本獲利，但方向其實錯咗 |
| **Reverse Martin** | `pips > 0` 且 `profit < 0` | 方向啱但 swap/commission 吃掉利潤 |
| **Cost Killed** | `gross_profit > 0` 且 `net_profit < 0` | 毛利正但成本吃掉淨利 |

### 4.2 統計

- **51/69 個信號（74%）有馬丁特徵**
- **112 個 Classic Martin 貨幣對**被偵測到
- 偵測結果顯示在每份 Detailed Report 嘅 Martin Detection 區塊

---

## 5. TP/SL 建議（Copy on Profit 專用）

### 5.1 公式

> 經 Gemini 諮詢 + Alvin 確認

**TP = P85 of Max Pips（盈利交易，trim 極端值）**
- 含義：85% 嘅盈利交易曾到達此位置
- 「85% 可達成」

**SL = P85 of Max Loss Pips（所有交易，trim 極端值）**
- 含義：85% 嘅交易最大回撤不超過此值
- 「85% 扛得住」

**格式：固定值（唔用 range）**

### 5.2 小樣本回退

- 當某貨幣對某層數嘅交易數量 < 30 → 使用 global percentiles（所有信號嘅綜合數據）
- 當數據充足（≥ 30）→ 使用信號自身嘅 percentiles
- P85 本身已排除 top 15% 極端值，無需額外 trim

### 5.3 統計實況（69 signals）

| 指標 | 數值 |
|------|------|
| TP/SL 配對總數 | 2,314 |
| R:R 中位數 | 2.05 |
| R:R ≥ 1.0 | 96% |
| P85（足夠數據） | 193 個 |
| Hybrid（混合） | 258 個 |
| Global fallback | 1,863 個 |

### 5.4 只在 CoP 部分顯示

- TP/SL 建議只出現在 Copy on Profit 分析區塊
- Copy on Lose 不顯示 TP/SL（因為係 recovery 策略，出場邏輯唔同）

---

## 6. 報告輸出格式

### 6.1 Signal Ranking 總表

**HTML 文件**：`output/signal_ranking_dde_v3.html`

**欄位：**

| # | 欄位 | 說明 |
|---|------|------|
| 1 | # | 排名序號 |
| 2 | Signal | Signal ID |
| 3 | EA | EA 家族標籤 |
| 4 | CCY | 貨幣對數量 |
| 5 | DDE | DDE v4 平均分 |
| 6 | CB | Clean Board%（全綠比） |
| 7 | Win% | 勝率 |
| 8 | Trades | 總交易數 |
| 9 | Profit | 總盈利（$）+ pips |
| 10 | DD | 最大回撤（$） |
| 11 | PF | Profit Factor |
| 12 | TF | 時間框架 |
| 13 | LV | 馬丁層數 |

**不顯示嘅欄位**（老闆確認）：
- ❌ Bar（無意義）
- ❌ Grid 類型（同 EA 重疊）
- ❌ DD Control（無意義，改用 LV）
- ❌ TP/SL 命中率（總表無意義）
- ❌ 出場效率（總表無意義）
- ❌ EA Family Deep Compare（總表無意義）
- ❌ Parameter Impact（總表無意義）

**EA CSS 標籤：**

| EA | 背景色 | 文字色 |
|----|--------|--------|
| DW | #4a148c | #ce93d8 |
| SMA | #1b5e20 | #a5d6a7 |
| MKD | #e65100 | #ffcc80 |
| S10 | #0d47a1 | #90caf9 |
| Flash | #880e4f | #f48fb1 |
| GEM | #37474f | #b0bec5 |

**DD 顏色分級：**
- 🟢 `dd-g`（#4CAF50）：DD < $3,000
- 🟡 `dd-y`（#FFC107）：DD $3,000-$6,000
- 🔴 `dd-r`（#FF5722）：DD > $6,000

**Score 顏色：**
- 🟢 `s90`（#4CAF50）：≥ 90
- 🟢 `s85`（#8BC34A）：≥ 85
- 🟡 `s75`（#FFC107）：≥ 75
- 🔴 `s0`（#FF5722）：< 75

**格式要求：**
- 置左對齊
- 橫向捲動（mobile-friendly）
- Highlight 頭 10 名
- 顯示所有 69 個信號（唔只頭 10）

### 6.2 Detailed Comparison Report（個別信號詳細報告）

**HTML 文件**：`output/detailed_comparison_all_levels_{signal_id}.html`

**結構：**

1. **📋 分析摘要表** — 貨幣對 × L1-L4+ 交易數 + 勝率
2. **每個貨幣對**（8-30 個）：
   - **L1-L4+ 每級**：
     - **Copy on Profit 評分表**：Wait 5/10/15/20 × 觸發率/平均獲利/DDE/評分/評級 + **TP/SL 建議值**
     - **Copy on Lose 評分表**：Wait 10/15/20/25 × 觸發率/回收率/平均獲利/評分/評級
3. **Martin Detection**（如有）：
   - Classic Martin 交易明細
   - Reverse Martin 匯總 + 明細
   - Cost Killed 匯總 + 明細

### 6.3 Signal Info Card（計劃中）

> **狀態**：待實作，Option A 已確認

**位置**：每份 Detailed Report 嘅最頂部（title 下面）

**內容：**
1. **Signal 基本資料**：Signal ID、EA 名稱+版本、EA 家族標籤、LV、.set 數量
2. **.set 版本歷史**：按上載日期排列，淨列出有差異嘅參數（只比較相同貨幣對）
3. **核心參數摘要**：加倉設定、風控設定、TP/SL 設定

---

## 7. 批量分析流程

### 7.1 數據收集

```
Windows 原始檔：/mnt/c/Users/Alvin/Downloads/Set File From Signal Page/{signal_id}/
  ├── *.csv     # 交易數據
  └── *.set     # 策略設定檔（可能多個，按日期）

Scraper 下載：/home/alvin/.openclaw/workspace/trade_strategy_analyzer/samples/
  └── forex-forest-signals-page-{signal_id}.csv
```

### 7.2 報告生成流程

```bash
# 1. 生成個別信號詳細報告（69份）
python3 dde_v5_scorer.py --signal {signal_id} --csv downloads/{signal_id}.csv

# 2. 生成 Signal Ranking 總表
python3 generate_signal_ranking_v5.py
```

### 7.3 關鍵腳本

| 腳本 | 用途 | 大小 |
|------|------|------|
| `dde_v5_scorer.py` | DDE v5 核心計算引擎（WR + PF + DD + Martin 4維排名制） | ~24KB / 620 行 |
| `generate_signal_ranking_v5.py` | Signal 排名 HTML 生成（v5） | ~15KB / 390 行 |
| `generate_ranking_ccy_v5.py` | CCY 排名 HTML 生成（v5） | ~15KB |
| `generate_ccy_deep_analysis.py` | CCY 跨 Signal 深度分析 | ~20KB |
| `config.py` | 全局配置（EA_MAP 唯一真相來源、路徑、常數） | ~6KB |
| `db_manager.py` | SQLite 統一存儲接口 | ~18KB |
| `generate_martin_autopsy_v3.py` | 馬丁驗屍報告 v3 生成 | ~45KB |
| `generate_manual_pptx.py` | 簡報PPTX生成 | ~40KB |
| `generate_signal_ranking.py` | ⚠️ DEPRECATED (v4) — 仍被簡報引用 | ~10KB |
| `dde_v4_scorer.py` | ⚠️ DEPRECATED (v4) — 仍被 v4 ranking 引用 | ~18KB |
| `scripts/algoforest_scraper.py` | AlgoForest 網頁 scraper | — |
| `scripts/algoforest_downloader.py` | AlgoForest 下載器 | — |
| `scripts/api_server.py` | FastAPI 服務（localhost:8787） | — |
| `scripts/batch_csv_downloader.py` | 批量 CSV 下載 | — |
| `scripts/batch_set_downloader.py` | 批量 SET 下載 | — |
| `scripts/history_manager.py` | 分析歷史管理 | — |
| `scripts/tsa_qa_check.py` | QA 自動質量檢查（sidebar + 連結 + EA 類型） | — |
| `scripts/extract_signal_data.py` | 數據提取 | — |
| `scripts/set_parser.py` | SET 檔案解析 | — |
| `scripts/portfolio_builder.py` | 投資組合建構 | — |
| `scripts/signal_anomaly_detector.py` | 信號異常偵測 | — |
| `scripts/signal_ea_timeline.py` | Signal EA 時間線 | — |
| `scripts/signal_lot_mapping_upgrade.py` | Lot mapping 升級工具 | — |
| `scripts/ccy_power_history_api.py` | CCY Power 歷史 API | — |
| `scripts/update_ccy_power.py` | CCY Power 更新 | — |
| `scripts/ea_grouping_fix.py` | EA 分組修復 | — |
| `scripts/export_hst.py` | HST 檔案匯出 | — |
| `scripts/fix_nav.py` | 導航修復 | — |
| `scripts/migrate_to_sqlite.py` | SQLite 遷移工具 | — |
| `scripts/v2_snapshot.py` | v2 快照工具 | — |
| `scripts/version_tracker.py` | 版本追蹤 | — |
| `analyze_buy_sell.py` | 買賣方向分析 | — |
| `calc_usd_value.py` | USD 價值計算 | — |
| `sidebar_qa_check.py` | Sidebar QA 檢查 | — |
| `tsa_set_csv_audit.py` | SET/CSV 審計工具 | — |

---

## 8. 技術架構

### 8.1 技術棧
- **後端**：Python 3（Pandas、HTML template string）
- **前端**：單一 HTML 文件（GitHub Pages 部署：https://alvin-forex.github.io/trade-strategy-analyzer/）
- **數據存儲**：SQLite（`data/analysis_history.db`）、JSON（`batch_analysis_results.json`）
- **API 服務**：FastAPI（localhost:8787）
- **通訊**：Telegram Bot（發送 HTML 報告附件）

### 8.2 目錄結構
```
trade_strategy_analyzer/
├── PRD.md                              # 本文件
├── CLAUDE.md                           # 工程標準（5-phase 開發流程）
├── FEATURE_ARCHITECTURE.md             # 功能架構思路
├── config.py                           # ⭐ EA_MAP 唯一真相來源 + 全局配置
├── dde_v5_scorer.py                    # ⭐ DDE v5 核心計算引擎
├── generate_signal_ranking_v5.py       # ⭐ Signal 排名 HTML（v5）
├── generate_ranking_ccy_v5.py          # ⭐ CCY 排名 HTML（v5）
├── generate_ccy_deep_analysis.py       # CCY 跨 Signal 深度分析
├── db_manager.py                       # SQLite 統一存儲接口
├── generate_martin_autopsy_v3.py       # 馬丁驗屍報告 v3
├── martin_autopsy_v3.py                # 馬丁驗屍核心邏輯
├── generate_manual_pptx.py             # 簡報PPTX生成
├── generate_period_stats.py            # 週期統計
├── generate_pivot_table.py             # Pivot 表格生成
├── generate_history_backup.py          # 歷史備份
├── generate_version_comparison.py      # 版本對比
├── batch_index_reports.py              # 批量報告索引
├── recalculate_baselines.py            # 基線重算
├── dde_v4_scorer.py                    # ⚠️ DEPRECATED (v4)
├── generate_signal_ranking.py          # ⚠️ DEPRECATED (v4)
├── generate_ranking_ccy.py             # ⚠️ DEPRECATED (v4)
├── generate_symbol_ranking.py          # ⚠️ DEPRECATED (舊邏輯)
├── generate_martin_v4.py               # ⚠️ DEPRECATED (v4)
├── generate_mfe_mae.py                 # ⚠️ DEPRECATED (已整合)
├── analyze_buy_sell.py                 # 買賣方向分析
├── calc_usd_value.py                   # USD 價值計算
├── sidebar_qa_check.py                 # Sidebar QA 檢查
├── tsa_set_csv_audit.py                # SET/CSV 審計工具
├── downloads/                          # CSV 交易數據
├── output/                             # 生成的 HTML 報告
├── docs/                               # GitHub Pages 部署
│   ├── index.html                      # 首頁
│   ├── sidebar.js / sidebar.css        # 全局導航
│   ├── signal_ranking.html             # Signal 排名（v5）
│   ├── signal_ranking_dde_v5.html      # v5 副本
│   ├── admin/                          # 管理頁面目錄
│   │   ├── signal_ranking.html         # Signal 排名（sidebar 入口）
│   │   ├── ccy_ranking.html            # CCY 排名（v5）
│   │   ├── volatility.html             # 波幅表
│   │   ├── forex_news.html             # 外匯新聞
│   │   └── ccy_power/                  # CCY Power 頁面
│   └── reports/                        # 個別 Signal 報告
├── scripts/
│   ├── api_server.py                   # FastAPI localhost:8787
│   ├── history_manager.py              # 分析歷史管理
│   ├── tsa_qa_check.py                 # QA 自動質量檢查
│   ├── algoforest_scraper.py           # AlgoForest 網頁 scraper
│   ├── algoforest_downloader.py        # AlgoForest 下載器
│   ├── batch_csv_downloader.py         # 批量 CSV 下載
│   ├── batch_set_downloader.py         # 批量 SET 下載
│   ├── extract_signal_data.py          # 數據提取
│   ├── set_parser.py                   # SET 檔案解析
│   ├── portfolio_builder.py            # 投資組合建構
│   ├── signal_anomaly_detector.py      # 信號異常偵測
│   ├── signal_ea_timeline.py           # Signal EA 時間線
│   ├── signal_lot_mapping_upgrade.py   # Lot mapping 升級工具
│   ├── ccy_power_history_api.py        # CCY Power 歷史 API
│   ├── update_ccy_power.py             # CCY Power 更新
│   ├── ea_grouping_fix.py              # EA 分組修復
│   ├── export_hst.py                   # HST 檔案匯出
│   ├── fix_nav.py                      # 導航修復
│   ├── migrate_to_sqlite.py            # SQLite 遷移工具
│   ├── v2_snapshot.py                  # v2 快照工具
│   └── version_tracker.py              # 版本追蹤
├── data/
│   ├── analysis_history.db             # SQLite 分析歷史
│   └── tsa.db                          # v5 排名數據庫
├── ea_manuals/                         # EA 手冊（MKD、S10、DragonWare、SMA、Flash）
└── templates/
```

---

## 9. 已確認決策

| # | 問題 | 決策 | 確認日期 |
|---|------|------|----------|
| 1 | 評分系統 | DDE v3（Trigger Rate 40% + Alpha Capture 40% + DDE 20%） | 2026-05-02 |
| 2 | ETE vs DDE | DDE 取代 ETE（ETE 分辨力接近零） | 2026-05-02 |
| 3 | balance/credit 過濾 | 必須排除 Type=balance/credit | 2026-05-02 |
| 4 | 小樣本回退 | n < 30 自動混和 global percentiles | 2026-05-02 |
| 5 | 總表欄位 | 不顯示 Bar/Grid/DD Ctrl/TP/SL命中率/EA Family/Parameter Impact | 2026-05-02 |
| 6 | Martin LV | 由 .set lot mapping 計算（lot-based），顯示喺總表 | 2026-05-10 |
| 7 | TP/SL 公式 | P85 of Max Pips / Max Loss Pips，固定值 | 2026-05-02 |
| 8 | TP/SL 位置 | 只喺 CoP 部分，每貨幣對每層數 | 2026-05-02 |
| 9 | CoL TP/SL | 不顯示（recovery 策略邏輯唔同） | 2026-05-02 |
| 10 | Gemini 諮詢 | Scoring 改動前必須先同 Gemini 討論 | 2026-05-02 |
| 11 | 排版 | 置左對齊，mobile 橫向捲動 | 2026-05-02 |
| 12 | 報告語言 | 中文標籤（專業術語除外） | 2026-05-02 |
| 13 | 報告交付 | HTML 附件經 Telegram 發送 | 2026-05-02 |
| 14 | S10 馬丁 | MaxBuyCount=10 是平注碼馬丁，非遞增式 | 2026-05-02 |

---

## 10. 待確認 / 待開發

| # | 項目 | 狀態 | 備註 |
|---|------|------|------|
| 1 | Signal Info Card | 🔜 待開發 | Option A 已確認，加喺 detailed report 頂部 |
| 2 | .set 版本差異比較 | 🔜 待開發 | 淨列出有差異嘅參數，只比較相同貨幣對 |
| 3 | SKILL：自動化分析流程 | 🔜 待開發 | "分析 signal {ID}" → scraper → 分析 → Telegram |
| 4 | CoP/CoL 評分公式改進 | ⏳ 討論中 | 其他 AI 反饋：CoP 勝率永遠 100%（20% 白送），建議改用 Early Efficiency |
| 5 | Tick Data 精確度 | ⏳ 待確認 | 目前無 Tick Data，可能不準確 |
| 6 | `UseAISignal=1` 邏輯 | ⚠️ 待確認 | SMA .set 入面嘅 AI 信號，具體邏輯未知 |

---

## 11. 驗證數據

### Signal Ranking Top 10（DDE v3, 2026-05-02）

| # | Signal | Score | EA | TF | Trades |
|---|--------|-------|----|----|--------|
| 1 | 22200 | 93.3 | DW | H4 | 130 |
| 2 | 5636 | 91.9 | SMA | M30 | — |
| 3 | 31781 | 91.8 | DW | H1 | — |
| 4 | 10437 | 90.7 | DW | M30 | 1,706 |
| 5 | 7919 | 91.1 | MKD | H1 | — |
| 6 | 36338 | 90.5 | DW | H1 | — |
| 7 | 33101 | 89.6 | DW | M30 | — |
| 8 | 17823 | 89.6 | SMA | H4 | — |
| 9 | 2351 | 89.4 | SMA | H4 | — |
| 10 | 13863 | 89.8 | SMA | D1+ | — |

**總計：69 signals, avg score 85.8, best 93.3 (22200), worst 67.3 (34259)**

---

*此 PRD v0.7 已整合 Lot-Based 層級偵測、三合一模組、69 signals batch regenerate。下次大改時同步更新 FEATURE_ARCHITECTURE.md 和 CHANGELOG.md。*

---

## 12. v0.6 更新：Enhanced Report + Signal Ranking Links（2026-05-09）

### 12.1 Signal Ranking 頁面修改

- **Signal ID → 連結**：點擊跳轉至 `https://forex-forest.com/signals/{id}`
- **📊 Report Icon**：Signal ID 旁加 report icon，連結至 `detailed_comparison_all_levels_{id}.html`

### 12.2 Detailed Report 新增三個模組

每個 CCY section 現在包含（按順序）：

1. **🎯 Copy Trade 建議引擎** — 自動生成建議
   - 決策邏輯：基於期望值、馬丁依賴度、勝率、CoP/CoL 最佳分數
   - 信心度：🟢 高 / 🟡 中 / 🔴 低
   - 建議策略 + Wait Pips + TP/SL
   - 理由 + 背景數據摘要

2. **📈 值博率分析** — Expectancy + Kelly + Safety Margin
   - 每層級（L1-L4+）+ Overall
   - 指標：勝率、盈虧比、期望值(R-Multiple)、Kelly%、1/4 Kelly、BE勝率、安全邊際
   - 安全邊際分級：🟢 >15% 穩健、🟡 5-15% 一般、🔴 <5% 危險

3. **🎰 馬丁層級深度分析** — Martin Level Depth
   - 整體馬丁盈利依賴度
   - 每層級：觸發率、平均深度(pips)、最大深度(pips)、平均DD($)、最大DD($)
   - 觸發率顏色分級：紅 >10%、橙 >3%、綠 ≤3%

### 12.3 實作細節

| 項目 | 說明 |
|---|---|
| 新增函數 | `compute_worthiness()`, `compute_martin_level_analysis()`, `compute_copy_trade_suggestion()` |
| 修改函數 | `generate_html_report()`, `generate_signal_ranking.py` |
| 數據流 | `raw_trades` 加入 `all_currency_data` 供新模組使用 |
| 層級定義 | v0.6 用 Max Pips 絕對值；v0.7 改用 Lot-Based（見 Section 13） |

### 12.4 Copy Trade 建議決策規則

| 條件 | 建議 | 信心度 |
|---|---|---|
| 期望值 < 0.1 OR 馬丁依賴 > 70% | ❌ 不建議 Copy | 🔴 低 |
| 馬丁依賴 < 30% AND 勝率 > 60% AND CoP 有數據 | ✅ CoP，Wait 參考最佳 CoP | 視乎指標 |
| 馬丁依賴 ≥ 30% AND CoL 有數據 | ⚠️ CoL，Wait 參考最佳 CoL | 視乎指標 |
| 信心度 🟢 高 | 期望值 > 0.5R + 馬丁依賴 < 20% + 勝率 > 80% | — |

---

## 13. v0.7 更新：Lot-Based 層級重構 + Batch Regenerate + UI 改進（2026-05-09 → 2026-05-10）

### 13.0 Batch Regenerate 完成（2026-05-10）

- **69 個 signals** 全部用 lot-based 重新生成 detailed reports
- 已部署到 GitHub Pages（https://alvin-forex.github.io/trade-strategy-analyzer/）
- Signal Ranking 總表已同步更新

### 13.0.1 TSA 系統指南

- Quant Agent 已加入 TSA 完整指南（Section 9）
- 涵蓋：分析流程、評分系統、報告解讀、操作指引

### 13.1 核心重構：Pip-Based → Lot-Based 層級偵測

**問題**：舊系統用硬編碼 pip 範圍（L1=0-50, L2=50-100 等）定義層級，與 EA 實際設定嘅馬丁層級完全無關。

**新做法**：

| 來源 | 優先級 | 說明 |
|---|---|---|
| SET 檔 `signal_lot_mapping.json` | Primary | 用 lot→level 對照表直接映射 |
| CSV Lots 唯一值推算 | Fallback | 無 SET 時按 unique lot 排序推算層級 |
| AutoLot 偵測 | 標記 | unique lots >> SET layers 時標記 AL |

**層級顯示**：L1 到 L9+（統一截斷）

**新 Global Baselines**（基於 lot-based，69 signals）：

| 層級 | 交易數 | 勝率 | TP(P85) | SL(P85) |
|---|---|---|---|---|
| L1 | 79,230 | 72.7% | 48.0 | 76.4 |
| L2 | 13,563 | 71.2% | 88.5 | 115.8 |
| L3 | 15,837 | 69.8% | 74.6 | 97.5 |
| L4 | 5,416 | 68.0% | 109.3 | 143.3 |
| L5 | 3,186 | 68.1% | 109.6 | 129.7 |
| L6 | 2,201 | 66.9% | 128.7 | 126.7 |
| L7 | 1,321 | 65.3% | 138.6 | 109.0 |
| L8 | 1,022 | 62.6% | 150.2 | 92.1 |
| L9+ | 1,865 | 50.8% | 163.4 | 73.8 |

### 13.2 UI 改進

- **Score Details → Mouseover**：CoP/CoL 評分表嘅公式拆解改為 ℹ️ icon，hover 先顯示
- **可排序表格**：所有表格點擊表頭可排序（JavaScript client-side）
- **動態 Summary 表格**：欄位按實際 achieved levels 動態生成

### 13.3 AutoLot Signals

以下 6 個 signals 被偵測為 AutoLot（unique lots >> SET layers）：

- 10437 (DW), 3291 (DW), 1980 (SMA), 10864 (SMA), 1470 (MKD), 23617 (MKD)

### 13.4 新增/修改函數

| 函數 | 用途 |
|---|---|
| `load_signal_lot_mapping()` | 載入 SET lot 對照表 |
| `assign_lot_level()` | SET-based lot→level 映射 |
| `infer_levels_from_csv_lots()` | Fallback: CSV lots 推算層級 |
| `analyze_by_levels_lotbased()` | 取代舊 `analyze_by_levels()` |

---

## 14. v0.8 全面優化分析（2026-05-25）— 四方 Agent 討論共識

> 參與者：Quant Agent、King Agent、Coder Agent、Gemini Pro Hui（外部顧問）
> 觸發原因：老闆要求全面優化 TSA 系統，特別關注 $1,000 小帳戶嘅實戰可用性同 DD 控制

### 14.1 現狀問題匯總（四方共識）

#### 🔴 P0 — 必須立即修復

| # | 問題 | 發現者 | 影響 |
|---|------|--------|------|
| 1 | **CoP 勝率永遠 100%**（只看盈利交易） | Quant + Gemini | 評分被嚴重扭曲，20% 權重白送 |
| 2 | **v3/v4 評分唔統一** | Quant + Coder | Signal Ranking 同 CCY Ranking 用唔同公式，結果唔互通 |
| 3 | ~~已修復 2026-05-25~~ | **dde_v4_scorer.py pip-based LEVEL_RANGES** → 已改為 lot-based，82% 信號分類錯咗，32 tests pass | Quant + Coder |
| 4 | **DD 控制維度完全缺失** | King + Quant + Gemini | 對 $1K 帳戶係致命傷 |
| 5 | **HTML string concatenation** | Coder + Gemini | 維護困難，改 UI 要改 Python |

#### 🟡 P1 — 高影響力改進

| # | 問題 | 發現者 | 影響 |
|---|------|--------|------|
| 6 | v4 Risk/Reward 用錯公式（非真正 R:R） | Quant | 高 PF 但隱藏大虧損風險 |
| 7 | Martin Layers 線性衰減太陡（WAL 2.0=33.3分） | Quant | 中度馬丁信號被過度懲罰 |
| 8 | Holding Time 5% 權重太低 | Quant | 長持倉風險被忽視 |
| 9 | 小樣本回退過度放大（n<10 可能全盈利拉高分數） | Quant | 高分但唔可靠 |
| 10 | EA_MAP 重複定義 3 次 | Coder | 維護時容易唔一致 |
| 11 | Pickle 作為中間格式（/tmp 重啟清空） | Coder | 強制執行順序、唔可靠 |
| 12 | 無投資組合相關性分析 | King + Gemini | 可能揀咗高相關 CCY 放埋一齊 |

#### 🟢 P2 — 長期改進

| # | 問題 | 發現者 | 影響 |
|---|------|--------|------|
| 13 | 無 Walk-Forward Analysis | Gemini | 過擬合風險 |
| 14 | 無 ML 信號品質預測 | Gemini | 長期競爭力 |
| 15 | 無市場狀態偵測（Trending/Ranging） | Gemini | 唔適應市況 |
| 16 | CCY Deep Analysis Rating 同 DDE 唔互通 | Quant | 兩套獨立評分 |

### 14.2 評分系統優化 — DDE v5 統一方案（Quant 主導）

#### 14.2.1 現有三套評分系統

| 系統 | 用途 | 核心文件 |
|------|------|----------|
| **DDE v5** ⭐ | Signal Ranking + CCY Ranking（統一評分） | `dde_v5_scorer.py` + `generate_signal_ranking_v5.py` |
| DDE v4 | ⚠️ DEPRECATED — 仍被簡報生成引用 | `dde_v4_scorer.py` + `generate_signal_ranking.py` |
| DDE v3 | ⚠️ DEPRECATED — 已拆分為 v5 模組 | （原 `generate_all_levels_from_csv.py` 已移除） |
| Rating S+/S/A/B/C/D/E | CCY Deep Analysis（跨 Signal 聚合） | `generate_ccy_deep_analysis.py` |

#### 14.2.2 DDE v5 統一評分維度（✅ 老闆確認版 2026-05-26）

**設計原則：** 用最真實嘅交易數據，唔做歸一化扭曲。排名制解決不同維度數值範圍差異。

| # | 維度 | 權重 | 計算方法 | 老闆決定 |
|---|------|------|----------|----------|
| 1 | Win Rate（真實勝率） | 15% | 真實勝率 × 100，唔加工 | ✅ 用最真實勝率，唔歸一化 |
| 2 | Profit Factor | 20% | 平均盈利 pips / 平均 MAX LOSE pips（剔除 3σ 極端值） | ✅ 剔除極端值排除滑價因素 |
| 3 | $1K DD%（真實 DD%） | 25% | 直接用真實 DD%，唔調整起始資金 | ✅ 方案A：用真實數據唔調整 |
| 4 | Martin Discipline | 40% | WAL（Weighted Average Layer），沿用 v4 | ✅ 維持現有 |
| ❌ | ~~交易量~~ | ~~刪除~~ | ~~不使用~~ | ❌ 老闆決定唔用 |

**v5 排名制邏輯：**
```python
# 1. 所有 Signal×CCY 計算 4 個維度嘅真實數值
# 2. 每個維度內排名（越高越好，DD/Martin 越細越好）
# 3. 排名轉為百分位分數：percentile = (rank - 1) / (N - 1) × 100
# 4. 加權求和
def score_v5_batch(all_metrics):
    wr_pcts = percentile_rank(all_metrics, 'wr_raw', higher_better=True)
    pf_pcts = percentile_rank(all_metrics, 'pf_raw', higher_better=True)
    dd_pcts = percentile_rank(all_metrics, 'dd_raw', higher_better=False)   # 越細越好
    martin_pcts = percentile_rank(all_metrics, 'martin_raw', higher_better=False)  # 越細越好

    for m in all_metrics:
        m['dde_v5'] = (
            wr_pcts[m] * 0.15 +
            pf_pcts[m] * 0.20 +
            dd_pcts[m] * 0.25 +
            martin_pcts[m] * 0.40
        )
```

**Profit Factor 計法（老闆指定）：**
- PF = 平均盈利 pips / 平均 MAX LOSE pips
- 剔除超過 3 個標準差嘅極端值（排除滑價等因素）
- 樣本數 < 4 時唔剔除

**Red Card 規則（沿用 v4）：**
- Net Pips ≤ 0
- Trade Count < 20
- Max Loss Pips > 500（單筆）
- Win Rate < 50%

**實施文件：**
- `dde_v5_scorer.py` — v5 核心計算引擎
- `generate_signal_ranking_v5.py` — Signal 排名 HTML
- `generate_ranking_ccy_v5.py` — CCY 排名 HTML

**測試結果（2026-05-26）：**
- 972 Signal×CCY pairs
- 525 scored, 447 red cards
- Score range: 4.1 - 98.5
- Top: 高勝率 + flat bet（WAL≈1.0）+ 低 DD
- Bottom: 高 WAL（馬丁去到 L5）+ 大 DD + PF < 1

#### 14.2.3 ~~小樣本處理優化~~（已改為排名制，唔需要）

v5 改用排名制後，唔需要 Confidence Band 加權。排名制天然解決咗唔同維度嘅數值範圍差異問題。

### 14.3 系統架構重構（Coder 主導）

#### 14.3.1 建議模組化架構

```
tsa/
├── config.py                 # 全局配置（EA_MAP, LEVEL_RANGES, paths）— 單一 source of truth
├── models.py                 # 數據模型（dataclass/TypedDict）
├── data/
│   ├── csv_loader.py         # CSV 讀取（統一 read_csv_trades）
│   ├── lot_mapping.py        # SET 文件解析 + lot→level 映射
│   ├── ea_detector.py        # EA 偵測 + 映射（只定義一次）
│   └── store.py              # SQLite 統一存儲接口
├── scoring/
│   ├── dde_v5.py             # score_v5 純函數（無 I/O、無 HTML）
│   ├── layer_stats.py        # 層分析
│   ├── tpsl.py               # TP/SL 建議
│   └── blacklist.py          # 黑名單邏輯
├── ranking/
│   ├── signal.py             # Signal 排名邏輯
│   ├── ccy.py                # CCY 排名邏輯
│   └── symbol.py             # Symbol 排名邏輯
├── render/
│   ├── templates/            # Jinja2 .html 模板文件
│   │   ├── _base.html
│   │   ├── signal_ranking.html
│   │   ├── ccy_ranking.html
│   │   └── martin_autopsy.html
│   └── *.py                  # 各頁面渲染器
├── api/
│   └── server.py             # FastAPI app
└── cli.py                    # 統一 CLI 入口
```

#### 14.3.2 數據層優化

**取代 Pickle → SQLite（tsa.db）：**

```sql
CREATE TABLE signal_scores (
    signal_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    ea_type TEXT,
    dde_v5_score REAL,
    wr_score REAL, pf_score REAL, dd_score REAL,
    ml_score REAL, sc_score REAL, he_score REAL,
    red_card INTEGER DEFAULT 0,
    computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(signal_id, symbol)
);
```

**遷移策略（漸進式）：**
1. Phase 1：新增 SQLite writer，保留 pickle fallback
2. Phase 2：ranking 腳本改讀 SQLite
3. Phase 3：移除 pickle 依賴

#### 14.3.3 HTML 生成 — 引入 Jinja2

**現狀：** 所有 HTML 用 f-string / string concatenation
**建議：** Jinja2 模板，HTML 同 Python 完全分離

#### 14.3.4 測試策略

| 層級 | 覆蓋範圍 | 工具 |
|------|----------|------|
| Unit | 評分公式、層級偵測、EA 映射 | pytest |
| Integration | CSV→Score→Output pipeline | pytest + fixture CSV |
| Regression | Golden file 比對（已知結果） | pytest + snapshot |
| Visual | HTML 報告渲染正確性 | 手動 + screenshot |

### 14.4 實戰風險管理（King + Gemini 主導）

#### 14.4.1 $1,000 帳戶風險框架

**每筆交易最大風險：** 帳戶淨值 × 1-2%（$10-$20）
**單一信號最大浮動虧損：** 帳戶淨值 × 10-15%（$100-$150）
**全帳戶最大 DD：** 50%（$500）— 老闆硬性要求

#### 14.4.2 馬丁風險量化

**連續虧損 → 爆倉概率：**
```
P(連虧 k 次) = (1 - WR)^k
Example: WR=60% → P(5連虧) = 1.0%, P(8連虧) = 0.07%
```

**馬丁層級 × 實際成本（以 DW LotMul×2.5 為例）：**
| 層級 | Lot | 累計成本 | $1K 帳戶 % |
|------|-----|----------|------------|
| L1 | 0.01 | ~$10 | 1% |
| L3 | 0.06 | ~$100 | 10% |
| L5 | 0.39 | ~$700 | 70% |
| L6+ | 0.97+ | >$1,500 | >150% 💀 |

#### 14.4.3 多帳戶組合優化

**相關性矩陣：** 用每日/每小時回報計算 Pearson correlation
**組合構建：** 等權或風險平價（risk parity），避免高相關 CCY 集中
**5 帳戶分配建議：** 每帳戶 2-3 個低相關 CCY

### 14.5 進階分析建議（Gemini Pro Hui）

#### 14.5.1 Walk-Forward Analysis

- 將歷史數據分 12 個時期
- 每步在 Period N 訓練/優化，在 Period N+1 測試
- 模擬真實交易環境，大幅降低過擬合風險

#### 14.5.2 市場狀態偵測

- 用 ADX 或 ATR 分類 Trending/Ranging
- 分析每個信號喺唔同市況下嘅表現
- 推薦組合應加權向當前市況最適合嘅信號傾斜

#### 14.5.3 ML 信號品質預測

- 用 LightGBM / Logistic Regression 預測信號未來一週盈利概率
- 特徵：近期 WR、DD、持倉時間、市場波動率
- 長期目標，建立後可顯著提升系統價值

### 14.6 實施路線圖

| Phase | 時間 | 內容 | 優先級 |
|-------|------|------|--------|
| **Phase 0A** | ~~已完成 2026-05-25~~ | ✅ 修復 dde_v4_scorer.py LEVEL_RANGES（改 lot-based） | P0 |
| **Phase 0B** | 待定 | 修復 CoP 勝率計算（改為基於全部交易）— 只影響已壞嘅 generate_symbol_ranking.py | P1 |
| **Phase 0C** | ~~已完成 2026-05-25~~ | ✅ CCY Ranking 加入 $1K DD 六級制（S/A/B/C/D/F） | P0 |
| **Phase 0D** | ~~已完成 2026-05-25~~ | ✅ EA 欄位移到 Signal 後面（兩個排名頁） | P0 |
| **Phase 1** | 3-5 天 | 實作 DDE v5 統一評分 | P0 |
| **Phase 1** | 3-5 天 | 新增 Max Drawdown Control 維度 | P0 |
| **Phase 1** | 2-3 天 | EA_MAP 去重（單一 source of truth） | P1 |
| **Phase 2** | 5-7 天 | 架構重構：模組化 + Jinja2 模板 | P1 |
| **Phase 2** | 3-5 天 | SQLite 取代 Pickle | P1 |
| **Phase 2** | 2-3 天 | 投資組合相關性分析 | P1 |
| **Phase 3** | 5-7 天 | Walk-Forward Analysis | P2 |
| **Phase 3** | 7-10 天 | 市場狀態偵測 + ML 預測 | P2 |
| **Phase 4** | 持續 | 自動化 Pipeline + CI/CD | P2 |

### 14.7 關鍵共識同分歧

#### 共識（四方一致）

1. ✅ 評分系統必須統一（v3/v4/v5 → 一套公式）
2. ✅ DD 控制必須加入評分維度（$1K 帳戶生死線）
3. ✅ CoP 白送問題必須修復
4. ✅ 小樣本處理必須改用置信度加權
5. ✅ HTML 生成必須用模板引擎
6. ✅ 數據存儲必須統一（SQLite）

#### 分歧

| 議題 | Quant | King | Coder | Gemini | 決定 |
|------|-------|------|-------|--------|------|
| PF vs Sharpe | PF 更穩健 | 兩者都要 | — | Sharpe 更專業 | **待定** |
| v5 權重分配 | DD 20% | DD 應更高（25%） | — | 同意 Quant | **待老闆確認** |
| 重構策略 | — | — | 漸進式 | 漸進式 | **共識：漸進式** |

---

### 14.8 實戰風險管理詳細方案（King 主導）

> 完整報告見：`trade_strategy_analyzer/TSA_Risk_Management_Optimization.md`

#### 14.8.1 $1K 帳戶 DD 六級制

現有三級制（<$3K/$3-6K/$6K+）對 $1K 帳戶毫無分辨力（85% 信號都喺最細嗰級）。

| 等級 | DD 上限 | 帳戶 % | 標籤 | 顏色 |
|------|---------|--------|------|------|
| S | ≤$50 | ≤5% | 極安全 | 🟢 |
| A | ≤$100 | ≤10% | 安全 | 🟢 |
| B | ≤$200 | ≤20% | 可控 | 🟡 |
| C | ≤$350 | ≤35% | 注意 | 🟡 |
| D | ≤$500 | ≤50% | 危險 | 🟠 |
| F | >$500 | >50% | **拒絕** | 🔴 |

**統計：** 71 信號中只有 42 個（59%）MaxDD 喺 $1K 可承受範圍（<$500）。

#### 14.8.2 馬丁層級 × $1K 帳戶爆倉風險（DW ×2.5 為例）

| 層級 | 累計手數 | $/pip | 300pip DD | 爆倉所需 pips |
|------|----------|-------|-----------|---------------|
| L1 | 0.01 | $0.10 | $30 | 10,000 |
| L2 | 0.035 | $0.35 | $105 | 2,857 |
| L3 | 0.098 | $0.98 | $293 | 1,020 |
| L4 | 0.254 | $2.54 | **$761** | 394 |
| L5 | 0.644 | $6.44 | **$1,932** | 155 |

**$1K 帳戶最大層級限制：**
- DW (×2.5): 最多 L3
- SMA (×1.5): 最多 L4
- MKD: 最多 L3
- S10 (平注): 最多 L5

#### 14.8.3 CCY 相關性分組

| 群組 | 貨幣對 | 內部相關性 |
|------|--------|-----------|
| AUD 系 | AUDCAD, AUDUSD, AUDJPY, AUDCHF | 0.6-0.85 |
| GBP 系 | GBPUSD, GBPJPY, GBPAUD, GBPCAD | 0.5-0.75 |
| EUR 系 | EURUSD, EURGBP, EURAUD, EURJPY | 0.5-0.70 |
| JPY 系 | USDJPY, EURJPY, GBPJPY, CHFJPY | 0.4-0.65 |

**規則：** 同一群組最多選 2 個入組合。

#### 14.8.4 即時可用嘅 5 帳戶組合

**Buy：**
1. S12962 EURUSD (MKD, 90.7分, DD $85)
2. S16596 EURJPY (SMA/S10, 98.2分, DD $40)
3. S33101 GBPCAD (DW, 80.9分, DD $63)

**Sell：**
4. S31593 USDCHF (DW, 84.0分, DD $108)
5. S22278 GBPAUD (DW, 80.7分, DD $94)

**組合總 DD：** $390 (39%) ✅ | CCY 群組充分分散

#### 14.8.5 實戰執行流程

1. TSA Ranking 篩選 → $1K DD 分級過濾 → 相關性排除 → 反向 DD 加權
2. 生成 MT4 .set 參數建議（Base Lot + Max Levels + SL override）
3. AlgoForest 設定 Copy Trade（CoP, wait=5-10 pips）
4. 每日監控組合 DD（>25% 警告, >35% 建議平倉）

---

*此章節由丁蟹整合 Quant、King、Coder、Gemini Pro Hui 四方討論結果。日期：2026-05-25。*
