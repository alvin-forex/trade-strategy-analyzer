# CCY Power 數據抓取 Pipeline

## 概覽

CCY Power（Currency Power）係衡量 9 個主要貨幣相對強度嘅指標。整個數據流從 MT4 指標計算，到 EA 抓取寫入 CSV，再經 Python 處理入 DB，最後前端 Dashboard 展示。

**9 個貨幣**：EUR, GBP, AUD, NZD, CAD, CHF, XAU, JPY, USD

**3 個時間框架**：D1, H4, H1

---

## 第一步：MT4 指標計算

### CCY Power Indicator v1.00（.ex4）

- 類型：MT4 自定義指標（只有 .ex4，無源碼）
- 開喺 MT4 chart 上，每個 chart 可設唔同嘅 `TF_1` 參數
- `TF_1` 參數：`60` = H1, `240` = H4, `1440` = D1
- 計算完成後，將 9 個貨幣嘅強度值顯示喺 chart panel 上
- Panel 使用 MT4 Object 系統（`ObjectCreate` + `ObjectSetString`）

### Panel Object 命名格式

```
{prefix}__table_edit_1_{row}__1  → 貨幣名稱（EUR, GBP...）
{prefix}__table_edit_2_{row}__1  → 強度值（float）
```

- `row` = 2~10（對應 9 個貨幣）
- `prefix` 係指標自動生成嘅隨機字串，每次載入可能唔同

---

## 第二步：EA 抓取數據

### ForexDataExporter EA v5.03

**運作頻率**：每 5 分鐘（`OnTimer()` 觸發 `DoExport()`）

### 2.1 偵測 CCY Power Panel

```cpp
string DetectCCYPowerPrefix()
```

- 掃描當前 chart window 所有 objects（`ObjectsTotal(0)`）
- 用 `ObjectName(0, i)` 逐個檢查
- 搵包含 `__table_edit_1_2__1` 嘅 object name
- 提取 prefix（即 `__table_edit_1_2__1` 前面嘅字串）
- 如果搵唔到，CCY Power 值全部填 0

### 2.2 讀取貨幣強度值

```cpp
for (int row = 2; row <= 10; row++) {
    nameObj = prefix + "__table_edit_1_" + row + "__1";
    valObj  = prefix + "__table_edit_2_" + row + "__1";
    ccyNames[row-2] = ObjectGetString(0, nameObj, OBJPROP_TEXT);
    ccyPower[row-2] = StringToDouble(ObjectGetString(0, valObj, OBJPROP_TEXT));
}
```

- 讀取 9 個貨幣嘅名同值
- 存入 `ccyNames[9]` 同 `ccyPower[9]` 陣列

### 2.3 寫入 CSV

`forex_data.csv` 路徑：`MQL4/Files/forex_data.csv`

**每個 pair 寫 3 行**（D1 / H4 / H1），共 29 pairs × 3 = 87 行 + 1 header = 88 行

**每行欄位**（37 columns）：

| 欄位 | 說明 |
|---|---|
| timestamp | 寫入時間（YYYY.MM.DD HH:MM） |
| symbol | 貨幣對（如 AUDUSD） |
| timeframe | D1 / H4 / H1 |
| open, high, low, close | OHLC |
| volume | 成交量 |
| ccy_1_name ~ ccy_9_name | 9 個貨幣名 |
| ccy_1_power ~ ccy_9_power | 9 個貨幣強度值 |
| bb_upper, bb_middle, bb_lower | 布林帶三軌 |
| ema20, ema50, ema200 | 指數移動平均線 |
| atr14 | 平均真實波幅 |
| rsi14 | 相對強弱指數 |
| macd_line, macd_signal, macd_hist | MACD 三線 |
| swing_high, swing_low | 搖擺高低點 |

### 2.4 技術指標讀取方式

EA 用 MT4 內建函數直接讀取：

```
iClose(symbol, tf, 0)       → close
iMA(symbol, tf, 20, ...)    → EMA20
iRSI(symbol, tf, 14, ...)   → RSI14
iMACD(symbol, tf, ...)      → MACD
iBands(symbol, tf, ...)     → Bollinger Bands
iATR(symbol, tf, 14, ...)   → ATR
```

技術指標係 per-TF 獨立計算嘅（每個 TF 傳入唔同嘅 timeframe 參數），所以 D1/H4/H1 嘅 RSI、MACD 等值係真正唔同嘅。

---

## 第三步：Python 處理

### update_ccy_power.py（每小時 crontab）

**CSV 路徑**：`/mnt/c/Users/Alvin/AppData/Roaming/.../MQL4/Files/forex_data.csv`

### 3.1 read_csv() — 讀取最新 CCY Power 值

- 優先讀 `ccy_power_v2` DB（由 CCY Power Indicator 直接寫嘅 history CSV 匯入，有 per-TF 分別）
- Fallback 讀 `forex_data.csv`（EA 寫嘅）
- 輸出：`{D1: {EUR: 5.25, ...}, H4: {...}, H1: {...}}`

### 3.2 save_to_db() — 寫入歷史 DB

- 將每個 TF 嘅 9 個 CCY Power 值寫入 `ccy_power_v3` 表
- 帶 timestamp + timeframe
- 自動清理 30 日前嘅舊數據

### 3.3 update_timeline_json() — 生成時間序列

- 從 `ccy_power_v3`（主要）+ `ccy_power_v2`（補充）讀取歷史
- 生成 `timeline.json`，每個 TF 一組時間序列

### 3.4 generate_pairs_json() — 生成貨幣對分析

- 從 `forex_data.csv` 讀取 29 pairs × 3 TFs 嘅技術指標
- 計算綜合 Signal Score：
  - RSI：>60 = +1, <40 = -1
  - MACD Histogram：>0 = +1, <0 = -1
  - EMA 對齊：EMA20 > EMA50 > EMA200 = +2, EMA20 > EMA50 = +1（反向同理）
  - BB 位置：(close - lower) / (upper - lower) > 0.7 = -1, < 0.3 = +1
- 輸出：`pairs.json`

---

## 第四步：DB Schema

### ccy_power_history.db

**ccy_power_v2** — 來自 CCY Power Indicator 直接寫嘅 history CSV

| Column | Type | 說明 |
|---|---|---|
| timestamp | TEXT | `YYYY.MM.DD HH:MM` |
| timeframe | TEXT | D1 / H4 / H1 |
| EUR, GBP, AUD, NZD, CAD, CHF, XAU, JPY, USD | REAL | 9 個貨幣強度值 |
| AVG | REAL | 平均值 |

**ccy_power_v3** — 來自 update_ccy_power.py 每小時寫入

| Column | Type | 說明 |
|---|---|---|
| timestamp | TEXT | `YYYY.MM.DD HH:MM` |
| timeframe | TEXT | D1 / H4 / H1 |
| AUD, CAD, CHF, EUR, GBP, JPY, NZD, USD, XAU | REAL | 9 個貨幣強度值 |

---

## 第五步：前端 Dashboard

### CCY Power Dashboard（index.html）

**三個 JSON 數據檔**：

| 檔案 | 用途 | 內容 |
|---|---|---|
| `data.json` | MTF Heatmap | D1/H4/H1 最新 9 貨幣強度值，用顏色深淺顯示強弱 |
| `timeline.json` | Timeline 歷史 | D1/H4/H1 時間序列，支援 24h/3D/7D/30D 四個範圍 |
| `pairs.json` | 29 Pairs 分析 | 每個 pair 嘅 RSI/MACD/EMA/BB/ATR × 3 TFs + 綜合 Signal |

### 前端展示邏輯

**MTF Heatmap**：
- 讀 `data.json` 嘅 D1/H4/H1 值
- 9 貨幣 × 3 TF 網格
- 顏色由綠（強）到紅（弱），按排名分 5 級

**Timeline**：
- 讀 `timeline.json`
- 24h 模式：24 格 × 9 貨幣，每格代表一小時
- 空格用 forward-fill + wrap-around 填補
- Session 底部色帶：Asia（黃）、Europe（藍）、US（綠）

**29 Pairs 分析表**：
- 讀 `pairs.json`
- 每行一個 pair，每格顯示 3 個箭咀（D1 / H4 / H1）
- ⬆ 強多 → ↑ 偏多 → — 中性 → ↓ 偏空 → ⬇ 強空
- Score = D1 + H4 + H1 signal 加總（-12 ~ +12）

---

## 數據流總結

```
MT4 CCY Power Indicator
    │（計算強度值，顯示喺 panel objects）
    ▼
ForexDataExporter EA
    │（ObjectGetString 讀 panel + iRSI/iMACD/... 讀指標）
    │（每 5 分鐘寫入 forex_data.csv）
    ▼
update_ccy_power.py（每小時 crontab）
    │（讀 CSV → 處理 → 寫 DB + JSON）
    ├── data.json      → Heatmap
    ├── timeline.json  → Timeline
    └── pairs.json     → Pairs Table
    ▼
GitHub Pages（前端 Dashboard）
```

---

## 29 個貨幣對清單

AUDCAD, AUDCHF, AUDJPY, AUDNZD, AUDUSD, BTCUSD, CADCHF, CADJPY, CHFJPY, EURAUD, EURCAD, EURCHF, EURGBP, EURJPY, EURNZD, EURUSD, GBPAUD, GBPCAD, GBPCHF, GBPJPY, GBPNZD, GBPUSD, NZDCAD, NZDCHF, NZDJPY, NZDUSD, USDCAD, USDCHF, USDJPY, XAUUSD, XAGUSD

---

*Last updated: 2026-06-10*
