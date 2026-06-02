# TSA Martin Autopsy V4 — Interactive Web App PRD

**Date:** 2026-06-03
**Status:** In Progress
**Reference:** Derrick Martingale Analyzer v1.68

---

## 1. Goal

將馬丁剖析法由 static HTML 升級做 **client-side interactive web app**，支援：
1. 動態 Date Range Filter（快速選擇 + 自訂日期 + 拖拉 bar）
2. 所有分析即時重新計算
3. Set File Change Detection（Phase 2）

## 2. Architecture

```
Static HTML (GitHub Pages)
├── martin_v4.html          ← 單一 HTML 檔案（所有 JS + CSS inline）
├── data/
│   └── signal_{id}.csv     ← CSV 數據（fetch 載入）
└── docs/reports/
    └── martin_v4_{id}.html  ← 每個 Signal 嘅入口頁面
```

**關鍵決策：**
- CSV 數據用 `fetch()` 載入，唔 embed 喺 HTML（保持檔案大小合理）
- 所有計算用純 JavaScript，唔加公式，只用 CSV 真實數據
- 單一 HTML 模板，URL 參數決定載入邊個 Signal 嘅 CSV

## 3. Phase 1 — Date Range Filter

### 3.1 Date Range Controls

**快速選擇按鈕：**
| 按鈕 | 功能 |
|---|---|
| 全部 | 顯示所有交易 |
| 1D | 只睇過去 1 日 |
| 1W | 只睇過去 1 週 |
| 1M | 只睇過去 1 個月 |
| 3M | 只睇過去 3 個月 |
| 6M | 只睇過去 6 個月 |
| 1Y | 只睇過去 1 年 |

**自訂日期：**
- From / To 日期輸入框（type="date"）
- 清除按鈕

**拖拉 Bar：**
- 雙手柄 range slider
- 左手柄 = From，右手柄 = To
- 顯示日期範圍文字
- 拖動時即時更新分析

### 3.2 動態重新計算

當 Date Range 改變時，以下全部重新計算：

1. **交易篩選** — 根據 Open Time 篩選
2. **Per-CCY×Direction 逐層統計** — WR%, EV$, MFE, MAE, MaxMAE, Hold time
3. **Rating + Score** — A/B/C/D/F 評級
4. **TP/SL 建議** — 基於篩選後嘅數據
5. **Blacklist** — 危險層數
6. **Recovery Plan** — 恢復計劃
7. **CCY Layer Profitability**
8. **Summary Stats** — 總 P&L、Win%、Trades 等

### 3.3 計算邏輯（純 JavaScript）

**層數推斷（from Lots）：**
```javascript
function inferLayer(lots) {
    // 根據 lots 判斷馬丁層數
    // 0.01=L1, 0.02=L2, 0.04=L3, 0.08=L4...
    // 但可能有非標準 lots（0.03, 0.07 等）
    // 使用現有 V3 嘅 assign_layer_index 邏輯
}
```

**統計計算：**
```javascript
function computeLayerStats(trades) {
    // 同 V3 一樣嘅計算邏輯
    // WR%, EV$, MFE, MAE, MaxMAE, Hold time
    // 唔加公式，只用 CSV 欄位：
    //   Net Pips, Net Profit, Max Profit, Max Loss, Max Loss Pips, Holding Time (Hours)
}
```

**Rating 計算：**
```javascript
function computeRating(stats) {
    // 同 V3 一樣嘅 rating 邏輯
    // A: WR>=80% && profit>0
    // B: WR>=70% && profit>0
    // C: WR>=60% || (profit>0 && WR>=50%)
    // D: WR>=40% && profit>-100
    // F: 其他
}
```

### 3.4 UI 結構

```
┌─────────────────────────────────────────┐
│ 🔄 馬丁剖析法 V4 — Signal 10437 (DW)   │
│ Date Range: [1D][1W][1M][3M][6M][1Y][全部]│
│ From: [2024-01-01] To: [2026-06-03]     │
│ ──────拖拉 Bar──────                    │
│ 📊 1,851 筆交易 | Win% 74.1% | P&L +136K │
├─────────────────────────────────────────┤
│ CCY×Direction Sections (expandable)      │
│ ▶ XAUUSD BUY (L1-L8)                    │
│ ▶ XAUUSD SELL (L1-L6)                   │
│ ▶ EURUSD BUY (L1-L3)                    │
│ ...                                      │
├─────────────────────────────────────────┤
│ TP/SL 建議 | Blacklist | Recovery Plan  │
└─────────────────────────────────────────┘
```

### 3.5 CSV 載入方式

每個 Signal 嘅入口頁面包含：
```html
<!-- martin_v4_10437.html -->
<script>
const SIGNAL_ID = '10437';
const CSV_URL = '../../downloads/forex-forest-signals-page-10437.csv';
</script>
<script src="martin_v4_app.js"></script>
```

或者用 URL 參數：
```
martin_v4.html?signal=10437
```

### 3.6 現有 V3 功能保留清單

| 功能 | V3 | V4 |
|---|---|---|
| Per-CCY×Direction 逐層分析 | ✅ | ✅ 保留 |
| WR%, EV$, MFE, MAE, MaxMAE, Hold time | ✅ | ✅ 保留 |
| Rating + Score (A/B/C/D/F) | ✅ | ✅ 保留 |
| TP/SL 建議 | ✅ | ✅ 保留 |
| Blacklist | ✅ | ✅ 保留 |
| Recovery Plan | ✅ | ✅ 保留 |
| CCY Layer Profitability | ✅ | ✅ 保留 |
| Per-CCY×Direction 詳細表格 | ✅ | ✅ 保留 |
| Dark/Light Theme | ✅ | ✅ 保留 |
| **Date Range Filter** | ❌ | ✅ **新增** |
| **拖拉 Bar** | ❌ | ✅ **新增** |
| **動態重新計算** | ❌ | ✅ **新增** |

## 4. Phase 2 — Set File Change Detection（待做）

### 4.1 數據來源

**方案 A（自動）：**
- 用 browser 自動登入 AlgoForest
- 下載 Signal page 嘅 .set 檔案
- 需要 CloudFlare bypass + 登入
- 老闆提供登入資料或 session

**方案 B（手動）：**
- 老闆不定期手動下載 .set 檔案到指定目錄
- 系統自動偵測新檔案並解析

### 4.2 Set 檔案解析

.set 檔案命名格式（待確認）：
```
{EA}_{Symbol}_{YYYYMMDD}.set
例如：DragonWave_XAUUSD_20240101.set
     DragonWave_XAUUSD_20240401.set
```

比對兩個 set 檔案：
- 提取 Lots 參數變化（LV1: 0.01→0.02）
- 提取 TP/SL 變化
- 其他參數變化

### 4.3 分析輸出

喺層數表標注：
```
L1  0.01→0.02 (2024-04-01)  Win%: 80%→72%  P&L: +500→+380
L2  0.02→0.04 (2024-04-01)  Win%: 70%→65%  P&L: +200→+150
```

## 5. Implementation Plan

| Step | 任務 | 預計時間 |
|---|---|---|
| 1 | 寫 PRD ✅ | Done |
| 2 | 研究現有 V3 計算邏輯，提取所有公式 | 30min |
| 3 | 用 JS 重寫核心計算（layer inference, stats, rating） | 2hr |
| 4 | 寫 Date Range UI（快速按鈕 + 自訂日期 + 拖拉 bar） | 1hr |
| 5 | 寫動態重新計算邏輯 | 1hr |
| 6 | 寫 Per-CCY×Direction 展開面板 | 1hr |
| 7 | 寫 TP/SL、Blacklist、Recovery Plan | 30min |
| 8 | CSS 樣式 + Dark/Light theme | 30min |
| 9 | 整合測試 + 生成入口頁面 | 30min |
| 10 | Git push + GitHub Pages 驗證 | 15min |

## 6. Files to Create/Modify

| 檔案 | 類型 | 說明 |
|---|---|---|
| `martin_v4_app.js` | New | 核心計算 + UI 邏輯 |
| `martin_v4_template.html` | New | HTML 模板 |
| `generate_martin_v4.py` | New | 生成入口頁面嘅 Python 腳本 |
| `generate_martin_autopsy_v3.py` | Keep | 保留舊版，唔刪 |

## 7. Constraints

- **唔加公式**：所有數據直接來自 CSV 欄位，唔做推算
- **GitHub Pages 相容**：純 static files，唔用 server
- **Mobile 友好**：響應式設計
- **保留 V3 所有功能**：唔減少現有分析內容
