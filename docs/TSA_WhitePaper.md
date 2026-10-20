# Trade Strategy Analyzer (TSA) 技術白皮書

> **文件性質：** 審核級技術白皮書（供外部技術審核 / Audit）
> **版本：** v1.0（2026-10-20）
> **適用系統版本：** TSA v4.x（前端 v3.0 分析引擎 + DDE v3/v4/v5 評分引擎 + Martin Autopsy V3/V4 + MT4 Monitor Daemon）
> **語言：** 繁體中文 + 英文技術名詞
> **維護者：** 丁蟹 🦀（系統架構）、Coder Agent（代碼實作）

---

## 目錄

1. 系統概覽（System Overview）
2. 系統架構（Architecture）
3. 核心公式（Core Formulas）
4. 資料流（Data Flow）
5. 參數／配置表（Parameters & Configuration）
6. 已知缺陷與限制（Known Defects & Limitations）＋修復優先序
7. 版本歷史（Version History）

---

## 1. 系統概覽（System Overview）

### 1.1 TSA 係乜

**Trade Strategy Analyzer（TSA）** 係一套用於**外匯馬丁格爾（Martingale）策略**嘅**交易歷史分析與評級系統**。系統針對第三方信號平台（AlgoForest / Forex Forest）上嘅多個信號頁面，提供以下核心能力：

| 能力 | 說明 |
|------|------|
| **純瀏覽器分析** | 上傳交易 CSV + 策略設定 SET，全部計算喺瀏覽器本地完成，無需伺服器運算 |
| **倉位重構** | 將馬丁策略嘅多層交易重構成「倉位」（Position），正確反映一次完整加倉週期 |
| **DDE 評分排名** | 統一評分標準，跨 EA、跨信號比較「跟單（Copy Trade）」可行性 |
| **Martin Autopsy** | 深入剖析馬丁格爾策略嘅層數、回撤、恢復力、黑名單風險 |
| **MT4 帳戶監控** | 即時監控多個 MT4 帳戶狀態，偵測開倉／平倉／保證金風險事件 |
| **CCY Power 儀錶板** | 每小時更新貨幣強弱指數（跨 D1/H4/H1/M30 時框） |

### 1.2 設計哲學

1. **離線優先** — 分析引擎零外部 API 依賴，所有統計在本地（瀏覽器／Python）完成
2. **單文件架構** — 前端分析器以單一 `index.html` 部署（GitHub Pages 靜態托管）
3. **Lot-Based 層級偵測** — 馬丁層級一律以「手數（Lot Size）」判定，與 EA 實際設定一致（已徹底取代舊式 pip-based 分層，見 §6.1）
4. **排名制評分** — DDE v5 用「跨信號百分位排名」取代絕對分數，消除量綱差異

### 1.3 支援嘅 EA 家族

| EA 家族 | 縮寫 | 加倉方式 | 典型層數 |
|---------|------|----------|----------|
| Dragon Wave | DW | LotMul 倍投（×2.5） | 8 層 |
| SMA Pro | SMA | lotExp 指數遞增 + pipstep | 7–15 層 |
| MKD Pro | MKD | PipStep 網格加倉 | 6–10 層 |
| S10 | S10 | 平注碼（固定 lotSize） | 0 / 10 平注 |
| Flash | Flash | CheckLevels | 11 層 |
| GEM | GEM | 無馬丁 | 0 層 |

---

## 2. 系統架構（Architecture）

### 2.1 組件圖（文字版）

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        TSA 系統總覽                                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  【A. 前端分析器 — 純瀏覽器】                                             │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  GitHub Pages（靜態托管）                                      │       │
│  │  ┌────────────┐   ┌──────────────────────────────────────┐  │       │
│  │  │ index.html  │   │  分析引擎（內嵌 JS，~6,100 行）        │  │       │
│  │  │ (分析器主頁) │   │  parseCSV → buildPositions →          │  │       │
│  │  └────────────┘   │  calcStats → 報告渲染（HTML/SVG）      │  │       │
│  │  上傳 CSV + SET    └──────────────────────────────────────┘  │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  【B. 後端評分引擎 — Python】                                             │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  dde_v5_scorer.py     — DDE v5 排名制評分核心（4 維度）       │       │
│  │  dde_v4_scorer.py     — DDE v4 加權評分（舊版）              │       │
│  │  generate_signal_ranking_v5.py — 信號排名總表生成器          │       │
│  │  martin_autopsy_v3.py — Martin Autopsy V3 剖析引擎          │       │
│  │  martin_v4_engine.js  — Martin Autopsy V4 互動版引擎        │       │
│  │  config.py            — EA 對照表唯一真相來源                │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  【C. MT4 帳戶監控 — 即時】                                               │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  AccountMonitor.mq4 (MT4 EA) → HTTP POST →                  │       │
│  │  mt4_monitor/ (FastAPI，埠由環境變數配置)                    │       │
│  │    ├─ EventDetector（開倉/平倉/保證金/大額浮動/餘額變動）       │       │
│  │    ├─ TelegramNotifier（優先級隊列 + 靜默時段 + 限流）        │       │
│  │    ├─ Database（SQLite 狀態/歷史/事件）                       │       │
│  │    └─ Watchdog（掃描 MT4 事件 CSV，觸發通知）                 │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
│  【D. 本地資料服務】                                                      │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │  api_server.py（FastAPI，埠由環境變數配置）— 存檔/比較/趨勢  │       │
│  │  scripts/update_ccy_power.py — 讀 MT4 輸出 CSV →             │       │
│  │      data.json / timeline.json / pairs.json + SQLite        │       │
│  └─────────────────────────────────────────────────────────────┘       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 前端分析器內部模組

| 模組 | 函數 | 職責 |
|------|------|------|
| CSV 解析 | `parseCSV()` | 解析交易 CSV，過濾非 buy/sell 記錄 |
| SET 解析 | `parseSET()` | 解析 `.set` 參數並分類 |
| 層級映射 | `buildLayerMapping()` | 唯一手數排序 → L1, L2, L3... |
| 倉位重構 | `buildPositions()` | Symbol+Direction+CloseTime 分組 |
| 入場評分 | `calcEntryScore()` | 方向/時機/初始回撤三維評分 |
| 策略評分 | `calcStrategyScore()` | 回歸/出場效率/風控/利潤品質/成本 |
| 統計 | `calcStats()` | 勝率/PF/MaxDD/Sharpe/Sortino/CVaR 等 |
| 分組統計 | `calcSymbolStats()` / `calcLayerStats()` | 按貨幣對／層數切片 |
| 報告渲染 | `renderReport()` | 生成完整 HTML 報告 |

### 2.3 部署說明（不涉及具體位址）

- 前端：GitHub Pages 靜態托管，`main` 分支 root 為文件根（`index.html`、`admin/`、`reports/`）
- 後端：本地常駐服務（systemd 單元管理），Python + FastAPI
- MT4 端：EA 以 HTTP POST 推送帳戶狀態，CSV 導出作為 fallback 通道
- 資料庫：SQLite（分析歷史、版本快照、監控事件、CCY Power 歷史）

---

## 3. 核心公式（Core Formulas）

> 本章所有公式均由源碼直接提取（`index.html`、`dde_v5_scorer.py`、`dde_v4_scorer.py`、`martin_autopsy_v3.py`、`martin_v4_engine.js`、`mt4_monitor/__init__.py`），並註明出處位置。

### 3.1 倉位重構分組邏輯（Position Rebuild）

**出處：** `index.html` — `buildPositions()` / `buildLayerMapping()` / `sameMinute()`

**Step 1 — 層級映射（Lot-Based）：**
```
uniqueLots = sort(unique(trades.lots), ascending)
mapping[lot] = index + 1          // 最小手數 = L1，次小 = L2，...
```

**Step 2 — 分組鍵：** `Symbol + Direction + CloseTime`

**Step 3 — 時間容差（floor-to-minute）：**
```
sameMinute(d1, d2):
  floor1 = floor(d1.epoch / 60000) * 60000
  floor2 = floor(d2.epoch / 60000) * 60000
  return floor1 == floor2
```
> 設計決定：與後端 `pandas.dt.floor('T')` 對齊。舊 60 秒 tolerance 版本會產生不一致倉位數（測試中差 9 個），v3.0 已統一改為 floor-to-minute。

**Step 4 — 倉位聚合：**
```
group = {t ∈ trades | same Symbol, Direction, CloseTime(floor-minute)}
netProfit     = Σ netProfit
maxProfit     = Σ maxProfit（MFE 美元）
maxLoss       = Σ maxLoss（MAE 美元）
totalLots     = Σ lots
maxLayer      = max(layer) in group
holdingHours  = (max CloseTime − min OpenTime) / 3600000
                // 若為負值（MT4 數據異常）→ 用 CSV 自帶 Holding Time 平均
                // 再 clamp 到 ≥ 0
```

### 3.2 入場評分（Entry Score）— v3.0 前端

**出處：** `index.html` — `calcEntryScore()`

```
Direction Score（35%）：
  mp = L1 Max Pips（MFE pips）
  mp > 20 → 1.0；mp > 10 → 0.7；mp > 0 → 0.4；否則 0.0
  dirScore = dirScore × (0.5 + 0.5 × min(mp/100, 1.0))   // 強度加權

Timing Score（35%）：
  mp < 5 且 ml < 5 → 0.5                    // 兩邊都細 = 中性
  mp + ml > 0 → mp / (mp + ml)              // 浮盈佔比
  馬丁修正：maxLayer ≥ 4 → min(timing × 1.2, 1.0)

Initial DD Score（30%）：
  ddScore = 1 − min(ml / 200, 1.0)          // ml = |L1 Max Loss Pips|

Entry Score = (dir×0.35 + timing×0.35 + dd×0.30) × 100
```

### 3.3 策略評分（Strategy Score）— v3.0 前端

**出處：** `index.html` — `calcStrategyScore()`

```
Regression（30%）：深層加倉後能否自救
  maxLayer ≥ 4 → np>0 ? 1.0 : (np>−20 ? 0.7 : 0.3)
  maxLayer < 4 → np>0 ? 0.8 : 0.4

Exit Efficiency（25%）：
  np>0 → np / maxProfit
  np≤0 → min(|np| / maxLoss, 1.0)

Risk Control（20%）：
  layerScore = maxLayer≤2 ? 1.0 : (≤4 ? 0.7 : 0.4)
  ddRatio    = max(0, 1 − (maxLoss / |np|) / 5)
  risk       = (layerScore + ddRatio) / 2

Profit Quality（15%）：np>0 ? 0.7 : 0.3
Cost & Holding（10%）：
  cph = (|commission| + |swap|) / holdingHours
  cph<0.5 → 1.0；<1.0 → 0.7；否則 0.4

Strategy Score = (reg×0.30 + exit×0.25 + risk×0.20 + quality×0.15 + cost×0.10) × 100
```

### 3.4 總分（Final Score）

```
Final Score = Entry × 0.4 + Strategy × 0.6
```
> 權重設計：策略管理（0.6）比入場時機（0.4）更重要 — 因為馬丁策略嘅成敗取決於「加倉後能否自救」。

### 3.5 統計指標（Statistics）— 前端

**出處：** `index.html` — `calcStats()`

| 指標 | 公式 |
|------|------|
| 勝率 WinRate | `wins / positions × 100%`（netProfit > 0 為贏） |
| Profit Factor | `Σ(wins) / |Σ(losses)|`（grossLoss=0 時 ÷1 防除零） |
| Max Drawdown | `max(peak − cumPnl)`，`maxDDpct = maxDD / peak × 100` |
| Sharpe | `(mean / std) × sqrt(252 / tradingDays)` |
| Calmar | `(totalProfit × 252/tradingDays) / maxDD` |
| Sortino | `(mean − riskFree) / downsideStd`，`riskFree = 0.02/252`（日），只計超額負回報 |
| CVaR 95% | 取排序後最差 5% 尾部之平均 |
| Gain-Pain | `grossWin / grossLoss` |
| Skewness | `m3 / (m2)^1.5`（三階／二階矩） |
| Exposure | `min(ΣholdingHours / (tradingDays×24) × 100, 100)` |

### 3.6 DDE v3 評分（Copy Strategy，已被 v5 取代，保留作歷史對照）

**出處：** `PRD.md` §3

```
DDE v3 Score = Trigger Rate × 0.40 + Alpha Capture × 0.40 + DDE × 0.20
```
- **Trigger Rate：** CoP 用 `netProfit>0` 交易中 `Max Pips ≥ wait_pips` 佔比；CoL 用 `netProfit≤0` 交易中 `|Max Loss Pips| ≥ wait_pips` 佔比。wait_pips 測試值：CoP = {5,10,15,20}，CoL = {10,15,20,25}
- **Alpha Capture：** 動態百分位 0–120 分。`baseline = max(signal P50, global P25)`，`floor = $5.00`；P75 以上 → 100+bonus（cap 120），P50–P75 → 70–100 線性，baseline–P50 → 0–70 線性，低於 baseline → 0
- **DDE（Drawdown Efficiency）：** `dd_ratio = |max_loss_pips| / profit_pips`（單筆，cap 2.0）→ `DDE = max(0, 100 − 50 × avg_dd_ratio) × 0.2`
- 小樣本回退：n < 30 → 混和 global percentiles

### 3.7 DDE v4 評分（加權制）

**出處：** `dde_v4_scorer.py` — `score_v4()`

```
DDE v4 = RR×0.35 + ML×0.25 + WR×0.20 + TC×0.15 + HT×0.05

RR（Risk/Reward）：   pips_ratio = ΣnetPips / maxLossPip
                      score = clamp((pips_ratio − 1) / 14 × 100)
ML（Martin Layers）： WAL = Σ(cnt × level) / n   // 手數層級加權平均
                      score = clamp(100 × (1 − (WAL − 1) / 1.5))
WR（Win Rate）：      clamp((WR − 55) / 30 × 100)
TC（Trade Count）：   clamp((n − 20) / 280 × 100)
HT（Holding Time）：  avgHold ≥ 4 ? clamp(100 × (1 − (avgHold−4)/68)) : 100

Red Card（任一本案即 0 分）：ΣnetPips ≤ 0 ｜ n < 20 ｜ WR < 50%
```

### 3.8 DDE v5 評分（排名制 — 現行版本）

**出處：** `dde_v5_scorer.py`

**4 維度真實值（raw metrics，per Signal×CCY×Direction）：**

| 維度 | 權重 | 計算方式 |
|------|------|----------|
| Win Rate | 15% | `真實勝率 × 100`，唔加工 |
| Profit Factor | 20% | `avg(盈利 netPips) / avg(|Max Loss Pips|)`，剔除 3σ 極端值 |
| $1K DD% | 25% | 累積 netPips 之 Max Drawdown（pips），越細越好 |
| Martin Discipline | 40% | WAL（手數層級加權平均），越細越好 |

**排名制轉換：**
```
percentile = (rank − 1) / (N − 1) × 100      // N = 該維度有效實體數
// 高者佳維度（WR/PF）降序排名；低者佳維度（DD/WAL）升序排名

DDE v5 = WR_pct×0.15 + PF_pct×0.20 + DD_pct×0.25 + Martin_pct×0.40
```

**Red Card 規則（v5）：**
- Tier 1（必紅）：n < 10
- Tier 2（10 ≤ n < 20）：ΣnetPips ≤ 0 或 WR < 60% 或 單筆 Max Loss > 500 pips → 紅；否則黃牌（照計分）
- Tier 3（n ≥ 20）：ΣnetPips ≤ 0 或 WR < 50% 或 單筆 Max Loss > 500 pips → 紅

**信號層級聚合（`generate_signal_ranking_v5.py`）：**
```
Signal Avg v5 = mean(所有 non-red 之 dde_v5 分數)
Signal PF / WR / WAL = 各 CCY 平均
Signal Max DD = 各 CCY 最大
```

### 3.9 Martin Autopsy V3 指標

**出處：** `martin_autopsy_v3.py`

**分組鍵：** `(Symbol, Direction, Lots)` — 直接按手數分層（不做時間重構）

**每層核心指標：**
```
WinRate      = wins / count × 100
EV$          = (WR/100 × avgWin$) − (1 − WR/100) × avgLoss$
Odds$        = avgWin$ / avgLoss$         // avgLoss 取絕對值
OddsPips     = avgWinPips / avgLossPips
MFE / MAE    = 各交易 Max Pips / |Max Loss Pips| 之 mean/max/median
```

**層級評級（Rating）：**
```
count < 2 → E
EV>50 且 Odds>2 且 WR>70 → S+
EV>20 且 Odds>1.5 且 WR>65 → S
EV>0  且 Odds>1 且 WR>55  → A
EV>−20 → B；EV>−50 → C；否則 D
```

**CCY×Direction 聚合：** 對各層取 `mean(ev_dollar)` 為 `EV per Layer`，`max(layer max_mae)` 為 pairMaxMAE。

**TP/SL 混合方案（僅 A 級以上）：**
```
TP     = avgMFE
SoftSL = avgMAE × 1.2
HardSL = pairMaxMAE × 1.3
RR     = TP / SoftSL
```

**黑名單 Danger Score（5 因子）：**
```
totalPnl < 0      → += |totalPnl| / 1000
avgOdds < 1.0     → += 3
WR < 50%          → += 2
avgEV < 0         → += |avgEV| / 10
worstEV < −50     → += 2
Danger > 5 → 💀 DEADLY；> 0 → ⚠️ WARNING
```

**恢復力（Recovery）：**
```
recoveryTrades = worstLoss / bestEV        // 最深虧損 ÷ 最佳層 EV
recoveryTrades > 20 或 bestEV ≤ 0 → 無法恢復（🔴）
recoveryTrades > 5 → ⚠️ 需長時間
否則 → ✅ 可恢復
```

### 3.10 Martin Autopsy V4（互動版）指標

**出處：** `martin_v4_engine.js`

**評分（0–100）：**
```
Score = WR分 + Odds分 + Count分 + Hold分
  WR:    ≥80→30 ｜ ≥70→25 ｜ ≥60→18 ｜ ≥50→10 ｜ else max(0, WR/5)
  Odds:  ≥2.0→20 ｜ ≥1.5→15 ｜ ≥1.0→10 ｜ else max(0, odds×10)
  Count: ≥10→15 ｜ ≥5→12 ｜ ≥3→8 ｜ else max(0, count×2)
  Hold:  ≤24h→5 ｜ ≤72h→4 ｜ ≤168h→3 ｜ ≤360h→2 ｜ else 1

Rating：≥85→S+ ｜ ≥70→S ｜ ≥55→A ｜ ≥40→B ｜ ≥25→C ｜ ≥15→D ｜ else E
```

**黑名單：** Rating ∈ {D, E} 且 count ≥ 2 → `danger = (100 − score) + |totalPnl|/10`（虧損時）。

### 3.11 馬丁偵測（Martin Detection）

**出處：** `PRD.md` §4 / `dde_v5_scorer.py`

| 類型 | 判定 | 含義 |
|------|------|------|
| Classic Martin | `netProfit > 0` 且 `netPips < 0` | 靠加倉拉平成本獲利，方向其實錯咗 |
| Reverse Martin | `netPips > 0` 且 `netProfit < 0` | 方向啱但成本（swap/commission）吃掉利潤 |
| Cost Killed | `grossProfit > 0` 且 `netProfit < 0` | 毛利正但淨利負 |

實測：51/57 個信號（89%）帶馬丁特徵 — 反映平台信號普遍依賴馬丁加倉，對跟單決策係關鍵風險提示。

---

## 4. 資料流（Data Flow）

### 4.1 前端分析（CSV → 報告）

```
用戶上傳 CSV ──► parseCSV() ──► trades[]（過濾 balance/credit，只留 buy/sell）
用戶上傳 SET ──► parseSET() ──► setParams{}（EA 名稱/版本/參數分類）
                          │
                          ▼
              buildLayerMapping(trades) ──► layerMap（手數→L1..L9+）
                          │
                          ▼
              buildPositions(trades, layerMap) ──► positions[]
                          │
        ┌─────────────────┼──────────────────┐
        ▼                 ▼                  ▼
   calcEntryScore    calcStats           calcSymbolStats
   calcStrategyScore  （整體統計）         calcLayerStats
        │                 │                  calcSessionStats
        ▼                 ▼                  calcDirectionStats
   calcFinalScore     收益曲線 SVG           分組報告
        │                 │
        └────────┬────────┘
                 ▼
           完整 HTML 報告（renderReport）
                 │
                 ├──► 下載 HTML
                 └──► 存檔到 localStorage（歷史記錄/比較/趨勢）
```

### 4.2 後端評分（CSV 批量 → 排名總表）

```
samples/*.csv + downloads/*.csv
        │
        ▼  (EA 分組：comment prefix + Magic Number)
dde_v5_scorer.read_csv_trades() ──► per Signal×EA×CCY×Direction 交易組
        │
        ▼
compute_raw_metrics() ──► {WR, PF, DD, WAL} raw values
        │
        ▼
score_v5_batch() ──► 跨全部實體排名 → 百分位 → 加權 = DDE v5
        │
        ▼
generate_signal_ranking_v5.py ──► 聚合 per Signal Avg v5
        │
        ▼
signal_ranking_dde_v5.html（GitHub Pages 排名總表）
```

### 4.3 MT4 帳戶監控（帳戶 → 通知）

```
MT4 Terminal
  └─ AccountMonitor.mq4（每 30s 導出，HTTP POST 主通道 / CSV fallback）
        │
        ▼
mt4_monitor FastAPI（埠由環境變數配置）
  ├─ POST /api/account/state  ──► StateCache + SQLite + EventDetector
  ├─ POST /api/account/history──► TradeHistory 存庫
  ├─ GET  /api/status /api/positions /api/events ──► Dashboard / 查詢
        │
        ▼
EventDetector.detect() ──► Notification（優先級 0/1/2）
        │
        ▼
TelegramNotifier（優先級隊列 → 靜默時段過濾 → 限流 → 發送）
```

**事件類型（EventDetector）：**

| 事件 | 觸發條件 | 優先級 |
|------|----------|--------|
| 新開倉 | ticket 未出現過（dedup 120s） | 2 |
| 平倉 | ticket 消失（dedup 120s） | 2 |
| 保證金危險 | margin_level < 120%（dedup 300s） | 0 |
| 保證金警告 | margin_level < 150%（dedup 300s） | 1 |
| 大額浮動 | \|position profit\| > $100（dedup 600s） | 1 |
| 餘額變動 | \|Δbalance\| > 1（dedup 60s） | 2 |

### 4.4 Watchdog（事件 CSV → 通知觸發）

```
MT4 Terminal 每寫入 monitor_events_*.csv（NEW_ORDER / CLOSE_ORDER 事件）
        │
        ▼  每 5 分鐘（watchdog 無 LLM、零 token）
掃描 32 字符 Terminal ID 目錄下所有事件 CSV
        │
        ▼  timestamp > last_processed
讀取新事件 ──► 寫入 pending_events.json
        │
        ▼
觸發 OpenClaw Agent（經本地 Gateway HTTP API）→ 格式化 → WhatsApp + Telegram 群組
        │
        ▼
成功 → 更新 watchdog_state.json（失敗唔更新 → 下次重試）
```

### 4.5 CCY Power（每小時更新）

```
MT4 CCYPowerReader EA ──► ccy_power_reader.csv（D1/H4/H1/M30 各時框）
        │  (優先)        └─► ccy_power_v2 DB（次優先）→ forex_data.csv（fallback）
        ▼
scripts/update_ccy_power.py
  ├─ 過濾損壞列（ccy 名稱白名單 AUD/CAD/CHF/EUR/GBP/JPY/NZD/USD/XAU）
  ├─ 每時框取最新有效列
  ▼
data.json + timeline.json + pairs.json + SQLite ──► GitHub Pages CCY Power 儀錶板
```

---

## 5. 參數／配置表（Parameters & Configuration）

### 5.1 MT4 帳戶監控（mt4_monitor）

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `MT4_MONITOR_API_PORT` | 環境變數配置 | FastAPI 監聽埠（本機） |
| `MT4_MONITOR_LARGE_PNL_THRESHOLD` | 100（美元） | 大額浮動觸發門檻 |
| `MT4_MONITOR_MARGIN_WARN` | 150（%） | 保證金警告門檻 |
| `MT4_MONITOR_MARGIN_CRIT` | 120（%） | 保證金危險門檻 |
| `MT4_MONITOR_QUIET_HOURS_START/END` | 00:00 / 07:00 | 靜默時段（只發優先級 0） |
| `MT4_MONITOR_HTTP_TIMEOUT` | 300（秒） | 帳戶數據過期判定 |
| 通知限流 | 1 msg/s、20 msg/min | Telegram 發送速率 |
| 事件去重窗口 | 60–600 秒（按事件） | 防重複通知 |

### 5.2 MT4 EA（AccountMonitor.mq4 input）

| 參數 | 預設 | 說明 |
|------|------|------|
| `ExportInterval` | 30 秒 | 導出頻率 |
| `EnableHTTP` / `EnableCSV` | true / true | HTTP 主通道 + CSV fallback |
| `HistoryDays` | 30 | 首次同步歷史天數 |
| `IncludeHistory` | true | 是否導出歷史交易 |

### 5.3 TSA 本地 API（scripts/api_server.py）

| 參數 | 預設 | 說明 |
|------|------|------|
| 監聽埠 | 環境變數配置 | 本地分析存檔 API |
| `TSA_API_TOKEN` | 未設（僅 localhost 可寫） | 寫入端點可選認證 |
| `TSA_API_CORS_ORIGINS` | 環境變數配置（預設僅本機） | CORS 白名單（env 覆寫） |

### 5.4 DDE 評分參數

| 參數 | v4 | v5 |
|------|----|----|
| 權重 | RR 35 / ML 25 / WR 20 / TC 15 / HT 5 | WR 15 / PF 20 / DD 25 / Martin 40 |
| 層級來源 | SET lot mapping（fallback：unique lots） | 同上（含 comment prefix + Magic 分組） |
| Red Card | netPips≤0 或 n<20 或 WR<50% | 分層級（n<10 / 10–19 / ≥20） |
| PF 計法 | pips_ratio = ΣnetPips/maxLossPip | avg 盈利 pips ÷ avg Max Loss pips（剔除 3σ） |

### 5.5 Martin Autopsy

| 參數 | V3 | V4 |
|------|----|----|
| 分組鍵 | (Symbol, Direction, Lots) | 同左 + 日期範圍過濾 |
| TP / SoftSL / HardSL | avgMFE / avgMAE×1.2 / pairMaxMAE×1.3 | —（互動，隨日期範圍重算） |
| 黑名單 | 5 因子 Danger Score | Rating D/E + count≥2 |
| 評級 | S+/S/A/B/C/D/E（EV$+Odds$+WR） | 0–100 分制（WR/Odds/Count/Hold） |

### 5.6 前端分析（v3.0）

| 參數 | 值 | 說明 |
|------|----|------|
| 時間容差 | floor-to-minute | 倉位分組鍵 |
| 層級 | 動態手數映射 | L1–L9+ 統一截斷 |
| Entry/Strategy 權重 | 0.4 / 0.6 | 總分 |
| L4+ timing 修正 | ×1.2（cap 1.0） | 深層加倉時機 bonus |
| 時段定義（HKT） | 亞洲 00–08 / 歐洲 14–22 / 美洲 21–05 | 重疊取亞洲優先 |
| 持倉分組 | <30m / 30m–1h / 1–4h / 4–12h / 12h+ | 五段 |
| localStorage 上限 | 5MB | 歷史存檔 |

---

## 6. 已知缺陷與限制（Known Defects & Limitations）＋修復優先序

> 本章係審核重點：誠實列出所有已知缺陷、對應源碼位置證據，並按風險排序。審核者可自行核實代碼位置。

### 6.1 已修復缺陷（記錄在案）

| # | 缺陷 | 嚴重度 | 證據位置 | 狀態 |
|---|------|--------|----------|------|
| 1 | **Pip-based 層級分類錯誤**：用淨利潤硬分層（L1<50, L2<100...），與 EA 手數層級完全無關，55/73 信號（75%）受影響，L1 平均誤差 32.6% | HIGH | `dde_v4_scorer.py:28-32,72-86`（`compute_layer_net_profit`），fallback 觸發點 `:140-142` | ✅ 2026-05-25 修復為 lot-based |
| 2 | **CoP 勝率永遠 100%**：CoP 只睇盈利交易，勝率分母變盈利交易本身 | HIGH（P0） | `PRD.md` §14.1；評分維度設計 | 🔶 已記錄，待改進（v5 已移除 CoP 勝率維度） |
| 3 | **v3/v4 評分唔統一**：Signal Ranking 與 CCY Ranking 用唔同公式，結果唔互通 | MEDIUM（P0） | `PRD.md` §14.1；v3/v4 scorer 並存 | ✅ v5 統一為排名制（但 v3/v4 仍在 repo） |
| 4 | **ETE 分辨力近零**：Early Trigger Efficiency 跨 wait_pips 全部 96–97% | MEDIUM | `PRD.md` §3.1；評分歷史 | ✅ v3 起以 DDE 取代 |
| 5 | **前端 60s tolerance 與後端 floor-to-minute 不一致**：倉位數差 9 個 | MEDIUM | `index.html` buildPositions（v3.0 修復）；`CHANGELOG.md` v3.0 | ✅ v3.0 統一 floor-to-minute |
| 6 | **Sortino 缺 risk-free 扣減** | LOW | `index.html` calcStats（v3.0 修復） | ✅ v3.0 加入 0.02/252 |
| 7 | **層數偵測硬編碼比率**（固定 0.02=L1 等） | MEDIUM | v3.0 changelog | ✅ v3.0 改動態唯一手數映射 |
| 8 | **美洲盤時段 0–5 HKT 缺失** | LOW | `CHANGELOG.md` v3.0 | ✅ v3.0 修復 |

### 6.2 現存缺陷與限制（審核時仍未修）

| # | 缺陷／限制 | 嚴重度 | 證據位置 | 影響 |
|---|-----------|--------|----------|------|
| L1 | **無 Tick Data**：無法知實際觸發時序，TP/SL 觸發時間只係估算 | MEDIUM | `FEATURE_ARCHITECTURE.md` 已知限制 #1 | MFE/MAE 用 CSV 內 Max Pips/Max Loss Pips，非真實逐 tick |
| L2 | **D1 精度市況分類**：M5/H1 EA 用日線分類市況可能唔夠精細 | MEDIUM | `FEATURE_ARCHITECTURE.md` #2 | 市況×策略分析粒度有限 |
| L3 | **單文件維護困難**：前端 6,100+ 行、後端 generate_all_levels 1,356 行 | MEDIUM | `FEATURE_ARCHITECTURE.md` #3 | 改動易引入回歸；今日 2 個 JS bug 正屬此類 |
| L4 | **localStorage 單用戶 + 5MB 上限**：無跨設備同步 | LOW | `FEATURE_ARCHITECTURE.md` #4/#5 | 歷史存檔可能爆限 |
| L5 | **DDE v5 用「pips」作 DD 單位**：`max_dd_pips` 非美元回撤，與 $1K DD% 命名不完全一致 | LOW | `dde_v5_scorer.py` compute_raw_metrics | 跨貨幣對 DD 比較受 pip 值影響 |
| L6 | **v3/v4/v5 三套評分引擎並存**：repo 內三套邏輯，未來維護易混淆 | MEDIUM | `dde_v4_scorer.py` / `dde_v5_scorer.py` | 需統一或標記 deprecation |
| L7 | **HTML 報告用字符串拼接生成**（Python f-string 內嵌 HTML） | LOW | `generate_*_ranking_v5.py`、`martin_autopsy_v3.py` | 維護困難、易有轉義 bug（今日第 2 個 bug 根源） |
| L8 | **前端 JS 以 Python 內嵌字串注入 Playwright**（批次報告生成） | MEDIUM | `batch_generate_reports.py` | 引號轉義脆弱，今日 2 個 bug 直接成因 |
| L9 | **監控 EA 的 HTTP 通道無 TLS 加密** | HIGH | `AccountMonitor.mq4`（HTTP 明文 POST） | 帳戶數據在網絡層明文傳輸，僅靠 header API key 保護 |
| L10 | **監控 API key 寫死喺源碼**（非 env） | HIGH | `mt4_monitor/server.py:20` | 換 key 要改代碼；key 屬靜態共享密鑰 |
| L11 | **保證金門檻為單一全局值**（120%/150%），未按帳戶風險偏好區分 | LOW | `mt4_monitor/__init__.py:50-51` | 不同帳戶需要不同警報級別 |
| L12 | **批次報告生成無輸出完整性檢查**（成功/失敗/跳過僅統計，唔保證報告內容一致） | LOW | `batch_generate_reports.py` | 需人手核實生成結果 |
| L13 | **AutoLot 信號**：6 個信號 unique lots 數 >> SET 層數（如 10437/3291/1980/10864/1470/23617） | LOW | `PRD.md` §13.3 | 手數映射層級對 AutoLot 可能失真 |
| L14 | **前端依賴單一全局 `_layerMapping`**：多信號同時分析（compare）時共享映射，可能串數據 | MEDIUM | `index.html` buildLayerMapping（`_layerMapping` 全局變量） | 比較分析時若層級集不同，第二個 CSV 會覆寫映射 |

### 6.3 建議修復優先序（Fix Priority）

| 優先序 | 項目 | 理由 |
|--------|------|------|
| **P0** | L9 監控通道加密 + L10 key 改 env | 安全性最高，防帳戶數據洩露；審核必定關注 |
| **P1** | L6 統一評分引擎（刪除/標記 v3/v4 deprecation） | 消除多引擎混淆，減低未來錯誤使用舊邏輯風險 |
| **P1** | L8 批次生成腳本重構（改用 file-based JS 而非內嵌字符串） | 直接消除今日 2 個 bug 類型嘅轉義脆弱性 |
| **P2** | L14 全局 layerMapping 隔離 | 影響多信號比較分析正確性 |
| **P2** | L1 引入 tick 數據或至少標明 MFE/MAE 為 CSV 估算 | 提升分析可信度／透明性 |
| **P3** | L2/L4/L5/L11/L12/L13 | 功能完善類，按需排期 |
| **P3** | L3/L7 技術債（單文件/字符串拼接） | 長期維護健康，可配合重構一併處理 |

---

## 7. 版本歷史（Version History）

### 7.1 CHANGELOG 摘要

| 版本 | 日期 | 重點 |
|------|------|------|
| v1.0 | 2026-04-24 | 初始版本：GitHub Pages 部署、基礎上傳+解析、後端 Python 模組 |
| v2.0 | 2026-04-24 | 前端 UI 升級：單一 HTML、拖放上傳、基礎統計、貨幣對排名、SVG 收益曲線 |
| v3.0 | 2026-04-25 | **6 項 Bug Fix 大修正**：層數動態偵測、floor-to-minute 分組、美洲盤時段、Sortino risk-free、下載按鈕、monkey-patch 清理；完整 Phase1+2 功能 |
| v3.1 | 2026-04-25 | 市場語境分析（初版 Yahoo Finance → 本地數據取代） |
| v3.2 | 2026-04-25 | 本地 MT4 .hst 數據整合（34 對 D1，2018–2026），完全離線 |
| v3.3 | 2026-04-25 | Copy Trade 推薦矩陣（CCY×層數） |
| v3.4 | 2026-04-25 | 波幅適配分析（ATR 三分組） |
| v3.5 | 2026-04-25 | 歷史記錄／版本追蹤（localStorage 存檔 + 比較 + 趨勢） |
| v4.0 | 2026-05-02 | **DDE v3 Copy Strategy 評分系統**：Trigger/Alpha/DDE 三維、Scoring Audit（3 項修復）、Martin Detection、TP/SL 建議 |
| v0.7（評分） | 2026-05-09→10 | **Lot-Based 層級重構**：69 signals 全部 lot-based 重生成，AutoLot 偵測 |
| v0.8（評分） | 2026-05-25 | 四方 Agent 全面優化：修復 pip-based bug、DD 控制維度、CoP 勝率問題記錄 |
| v0.9（評分） | 2026-06-19 | **DDE v5 統一評分**：排名制 4 維度、EA_MAP 去重、QA 加強 |

### 7.2 2026-10-20 修復紀錄：TSA Index 工具 2 個 JS Bug

> 今日（2026-10-20）修復 `batch_generate_reports.py`（批次生成 index 報告嘅 Playwright 自動化工具）入面 2 個 JS 轉義 bug。修復位於工作樹改動（`git diff batch_generate_reports.py`）。

**Bug 1 — 空字串比較轉義錯誤（`batch_generate_reports.py:66`）**

```python
# ❌ 修復前：Python 三重引號內嘅空字串被錯誤寫成 `"""""`，
#    實際產生嘅 JS 係 `!== """"`（四個引號），語法錯誤／永假
if pg.evaluate("""() => document.getElementById("results").innerHTML.trim() !== """"""):
    break

# ✅ 修復後：改用單引號空字串 `''`
if pg.evaluate("""() => document.getElementById("results").innerHTML.trim() !== ''"""):
    break
```

- **影響：** 判斷「分析結果已渲染」嘅條件失效，導致批次生成器可能誤判未完成而 timeout，或進入錯誤分支。
- **根源：** Python 三重引號字符串內嵌 JS，空字串引號與外層引號衝突（L8 技術債之實例）。

**Bug 2 — HTML 模板字符串轉義錯誤（`batch_generate_reports.py:71-72`）**

```python
# ❌ 修復前：JS 模板用 `\\"` 轉義雙引號，但放喺 Python 三重引號內會
#    產生字面 `\"`，令生成嘅 HTML 標籤屬性帶反斜線 → 報告樣式/結構損壞
return "<!DOCTYPE html>...<meta name=\\"viewport\\" ...>"+r.innerHTML;

# ✅ 修復後：改用單引號包住 JS 字符串，雙引號可原樣保留喺 HTML 內
return '<!DOCTYPE html>...<meta name="viewport" ...>'+r.innerHTML;
```

- **影響：** 生成嘅 index 報告 HTML `<meta>` 標籤屬性帶多餘反斜線，可能令 viewport/樣式失效，移動端顯示異常。
- **根源：** 雙層引號轉義（Python 外層 + JS 內層）造成嘅轉義疊加（L7/L8 技術債之實例）。

**修復影響範圍：** 只影響「批次生成報告」工具本身，唔影響分析引擎或已生成報告。改動未提交至 git（工作樹改動），待 main agent 確認後提交。

### 7.3 評分引擎演進

```
v3（2026-05-02）  加權絕對制：Trigger 40 + Alpha 40 + DDE 20（Copy 場景）
   │
   ├─ 問題：CoP 勝率 100%、ETE 分辨力近零、pip-based 層級錯誤
   ▼
v4（2026-05-25）  加權制：RR 35 + ML 25 + WR 20 + TC 15 + HT 5（lot-based）
   │
   ├─ 問題：與 v3 唔統一、$1K 帳戶 DD 控制維度弱
   ▼
v5（2026-06-19）  排名制：WR 15 + PF 20 + DD 25 + Martin 40（現行）
                 percentile = (rank−1)/(N−1)×100，跨 Signal×CCY 統一排名
```

---

## 附錄 A：源碼位置索引（審核對照用）

| 組件 | 檔案 |
|------|------|
| 前端分析器（倉位/評分/統計/渲染） | `index.html`（root，~6,100 行） |
| DDE v5 評分引擎 | `dde_v5_scorer.py` |
| DDE v4 評分引擎 | `dde_v4_scorer.py` |
| 信號排名生成器 | `generate_signal_ranking_v5.py` |
| Martin Autopsy V3 | `martin_autopsy_v3.py` / `generate_martin_autopsy_v3.py` |
| Martin Autopsy V4 | `martin_v4_engine.js` / `martin_v4_template.html` / `generate_martin_v4.py` |
| EA 對照／lot mapping | `config.py` / `signal_lot_mapping.json` |
| SET 解析 | `scripts/set_parser.py` |
| 批次報告生成 | `batch_generate_reports.py` |
| MT4 帳戶監控 | `mt4_monitor/__init__.py` / `server.py` / `AccountMonitor.mq4` |
| 監控 Watchdog | `mt4_monitor/watchdog.py` / `watchdog_daemon.py` / `forexdata_watchdog.py` |
| 本地分析 API | `scripts/api_server.py` / `history_manager.py` / `v2_snapshot.py` |
| CCY Power 更新 | `scripts/update_ccy_power.py` / `ccy_power_history_api.py` |

## 附錄 B：文件清潔度聲明（Security Cleanliness）

本白皮書僅描述系統邏輯與算法，**不含**以下內容：

- ✅ 無任何 API key / token / 密鑰
- ✅ 無電話號碼
- ✅ 無 VPS IP／主機名
- ✅ 無 broker 帳號實號（如有需要以「Acct-A/B/C」代替）
- ✅ 無個人檔案路徑（如 `/home/...`、Windows 本機路徑）
- ✅ 無部署位址／第三方服務憑證

審核者可基於 §附錄 A 之檔案索引，直接核對 §3 所有公式與 §6 所有缺陷證據。

---

*本白皮書由 Coder Agent 基於源碼審核撰寫，所有公式均可由附錄 A 對應檔案核實。*
*生成日期：2026-10-20*
