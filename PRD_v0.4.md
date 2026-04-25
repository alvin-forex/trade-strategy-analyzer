# Trade Strategy Analyzer — PRD v0.4

> 最後更新：2026-04-25 | 四方 Review: GLM-5 + GLM-4.7 + ChatGPT + Deepseek

## 1. 項目概述

Trade Strategy Analyzer 是一個**純前端、離線優先**的外匯交易策略分析系統，專為 Alvin 的 Forex Forest 信號頁面設計。用戶上傳 EA 交易歷史（CSV）和策略參數（SET），系統即時生成多維度分析報告。

**核心定位**：
- 不需要伺服器、不需要數據庫
- 所有計算在瀏覽器端完成
- 本地 MT4 歷史數據（.hst→JSON）提供市場背景
- 適合信號頁面運營者做策略篩選和 Copy Trade 決策

**部署位置**：GitHub Pages — https://alvin-forex.github.io/trade-strategy-analyzer/

---

## 2. 數據輸入

### 2.1 CSV 格式（MT4 信號歷史）
| 欄位 | 說明 | 範例 |
|------|------|------|
| Open Time | 開倉時間 | 01/15/2024 08:30:00 |
| Type | buy/sell | buy |
| Lots | 手數 | 0.02 |
| Symbol | 貨幣對 | EURCHF |
| Open Price | 開倉價 | 0.93850 |
| Close Time | 平倉時間 | 01/15/2024 14:22:00 |
| Close Price | 平倉價 | 0.94010 |
| Commission | 手續費 | -0.40 |
| Swap | 隔夜利息 | -0.12 |
| Net Pips | 淨點數 | 16.0 |
| Net Profit | 淨盈虧 | 3.08 |
| Max Profit | 最大浮盈($) | 5.20 |
| Max Pips | 最大浮盈(pips) | 26.0 |
| Max Loss | 最大浮虧($) | -1.80 |
| Max Loss Pips | 最大浮虧(pips) | -9.0 |
| Magic Number | EA 識別碼 | 88 (BUY) / 77 (SELL) |
| Comment | 備註 | |
| Holding Time (Hours) | 持倉時間 | 5.87 |
| Holding Time | 持倉時間(文字) | 5h 52m |

- **日期格式**：DD/MM/YYYY HH:MM:SS
- **過濾規則**：自動跳過 Transfer/Deposit/Withdraw/Balance 類型交易

### 2.2 SET 格式（EA 參數檔）
```
; MKD v3.00 參數
MA_Period=50
LotExp=1.8
DollarMode=1
DynamicTP=1
```
- 支持多 SET 檔案上傳（自動按檔名識別 EA + 貨幣對）
- 參數自動分類到 7 個類別 + 其他

### 2.3 本地市場數據（MT4 .hst → JSON）
- **來源**：MT4 Terminal 歷史數據（D1 日線）
- **覆蓋**：34 個貨幣對，1929 bars（2018-11 → 2026-04）
- **欄位**：OHLCV + 技術指標（SMA 20/50/200, EMA 12/26, RSI 14, ATR 14, MACD）
- **轉換腳本**：`scripts/export_hst.py`

---

## 3. 核心計算邏輯

### 3.1 倉位重建（Position Reconstruction）
多筆交易組成一個「倉位」：
- **分組鍵**：Symbol + Direction + Close Time（floor-to-minute）
- **層數檢測**：動態排序唯一手數 → 映射 L1, L2, L3... 
  - 例：{0.02:L1, 0.03:L2, 0.04:L3, 0.06:L4, 0.12:L5, 0.21:L6}
- **倉位統計**：淨盈虧、最大浮盈/浮虧、L1 Max Pips、持倉時間、是否部分平倉

### 3.2 質量評分系統（Entry Quality Scoring）

#### 入場評分（Entry Score）— 滿分 100
| 維度 | 權重 | 計算方法 |
|------|------|----------|
| 方向 | 35% | Max Pips >20→1.0, >10→0.7, >0→0.4；強度=min(max_pips/100, 1.0)；得分=門檻×(0.5+0.5×強度) |
| 時機 | 35% | max_pips/(max_pips+|max_loss_pips|)；邊界：兩者<5→0.5；**馬丁修正**：L4+ ×1.2 cap 1.0 |
| 初始回撤 | 30% | 1 - min(|max_loss_pips|/200, 1.0) |

#### 策略評分（Strategy Score）— 滿分 100
| 維度 | 權重 | 說明 |
|------|------|------|
| 回歸率 | 30% | 深層加倉後能否回歸盈利 |
| 出場效率 | 25% | 淨利潤 / 最大浮盈 |
| 風控能力 | 20% | 最大回撤控制 |
| 盈利品質 | 15% | 盈利穩定性 |
| 成本持倉 | 10% | 手續費 + 隔夜利息 + 持倉時間 |

#### 最終評分
```
Final Score = Entry Score × 0.4 + Strategy Score × 0.6
```

#### 等級
| 等級 | 分數 | 入場評價 | 策略評價 |
|------|------|----------|----------|
| A | 80-100 | 優質 | 可 Copy |
| B | 60-79 | 一般 | 需評估 |
| C | 40-59 | 偏弱 | 需調整 |
| D | 0-39 | 差 | 不建議 |

### 3.3 統計模組
五個維度的統計分析：

#### 整體統計（Overall Stats）
- 倉位數、交易數、勝率、平均盈虧
- 盈虧比（Avg Win/Loss Ratio）、Profit Factor
- 總盈虧、平均盈虧、最大回撤（金額 + 百分比）
- 平均層數、平均持倉時間
- 總 Swap、總 Commission
- **進階指標**：
  - Sharpe Ratio（年化：√(252/trading_days)）
  - Calmar Ratio
  - Sortino Ratio（risk_free_rate = 0.02/252 日化）
  - 偏度（Skewness）
  - CVaR 95%（條件風險值）
  - Gain-to-Pain Ratio
  - 暴險時間百分比
  - 最大連續虧損（次數 + 金額）
  - 回撤恢復時間（天）
  - 盈虧中位數 vs 平均數

#### 按貨幣對（Symbol Stats）
- 每個貨幣對的完整統計（同 Overall Stats 指標）

#### 按層數（Layer Stats）
- L1 only / L1-L2 / L1-L3 / L4+ 四組
- 每組：倉位數、佔比、平均盈虧、勝率、Profit Factor
- 馬丁健康指標：L1-only 佔比、L4+ 佔比、L4+ 回歸率

#### 按時段（Time Stats）
- 亞洲盤 00:00-08:00 HKT
- 歐洲盤 14:00-22:00 HKT
- 美洲盤 21:00-05:00 HKT（亞洲盤優先匹配 0-4）
- 其他
- 每個時段：倉位數、平均盈虧、勝率、Profit Factor

#### 按方向（Direction Stats）
- BUY / SELL
- 每個方向：完整統計

---

## 4. 功能模組（Tab 清單）

### 4.1 基礎分析（Phase 1 MVP）

#### 📈 收益曲線
- 累積盈虧 SVG 折線圖（W=900, H=300）
- 網格線、零線、正負區域著色
- 關鍵統計摘要卡片

#### 🎯 質量評分
- Entry Score 三維度分數 + 雷達圖
- Strategy Score 五維度分數
- Final Score = Entry×0.4 + Strategy×0.6
- A/B/C/D 等級著色

#### 💱 貨幣對
- 按 Profit Factor 排序的貨幣對表格
- 每個貨幣對：倉位數、勝率、平均盈虧、PF、最大回撤
- 點擊展開詳細統計

#### 📚 層數分析
- L1/L2/L3/L4+ 分組統計
- 盈虧棒型圖 + 層數分佈甜甜圈圖
- 馬丁健康指標（L1-only 佔比、L4+ 佔比、L4+ 回歸率）

#### 🕐 時段分析
- 四大時段統計 + 24 小時逐小時盈虧棒型圖
- 按時段著色（亞洲🟢 歐洲🔵 美洲🔴）
- 逐小時明細表格

#### ⏱️ 持倉時間
- 5 段分組：<30m / 30m-1h / 1-4h / 4-12h / 12h+
- 盈虧棒型圖 + 持倉分佈甜甜圈圖
- 整體摘要：平均/中位數/P10/P90/最短/最長（分鐘）

#### ↔️ 方向分析
- BUY / SELL 對比統計

### 4.2 市場背景（Phase 1.5）

#### 🌐 市場語境
- 用本地 MT4 D1 數據，Top 5 交易貨幣對
- 同期價格走勢折線圖 + BUY/SELL 標記
- 趨勢判定：上漲/下跌/橫盤
- 方向匹配判定：ok（順勢）/ warn（逆勢）/ neutral

#### 🔄 市況×策略（方案 C）
- **市場環境分類**（5 種狀態）：
  - 🟢 上升趨勢：SMA20 > SMA50 + RSI > 50
  - 🔴 下降趨勢：SMA20 < SMA50 + RSI < 50
  - 🟡 震盪盤：SMA 差距 < 0.15% + RSI 40-60
  - 🟠 高波動：ATR > 1.5× 50 日均值
  - ⚪ 未知：數據不足
- **策略×市況表**：每個市況的倉位數/盈虧/勝率/PF/層數
- **最佳市況**高亮
- **按月時間軸**：橫向堆疊圖 + 盈虧交易標記
- **雙 CSV 對比**：上傳第二份 CSV，按同一市況對比唔同 SET 表現

### 4.3 深度分析（Phase 2）

#### 🏆 Copy 推薦
- 貨幣對 × 層數交叉推薦矩陣
- 每格：等級(A/B/C/D) + 勝率 + PF + 平均盈虧 + 倉位數
- L4+ 最高 B 級
- Top 3 推薦摘要（🥇🥈🥉）

#### 📏 波幅分析
- 層數波幅統計（Max Pips + |Max Loss Pips|）
- ATR 交叉分析（低/中/高波幅三組，按百分位 p33/p67 分割）
- 最適 ATR 範圍推薦
- 可操作性建議（建議時段、止損寬度、新聞期間建議）
- Pip 乘數：5 位小數對 ×10000、JPY 對 ×100、XAU/XAG ×0.1

#### 🎲 馬丁風險
- 風險等級橫幅（LOW/MEDIUM/HIGH/CRITICAL）
- 每層回歸率分析 + 勝率棒型圖
- 資金需求遞增圖（累積手數）
- L1-L3 vs L4+ 加倉效率對比
- Pipstep 分析
- 自動結論

#### 📐 TP/SL 分析
- Max Profit / Max Loss 分佈百分位（P10-P95）
- MFE/MAE 差距分析
- 每層組別 TP/SL 優化建議（SL = P90×1.2, TP = P75, TSL = 差距中位數）
- DollarMode 分析（從 SET 參數）

#### 💰 Copy 模擬
- 兩種模式：「跟勝 Copy on Profit」/ 「跟虧 Copy on Lose」
- 可調參數：最大層數、止損 pips（自動從 TP/SL 分析填入）、賬戶大小
- 原始 vs 模擬並排對比表
- 重疊收益曲線 SVG
- 模式專屬建議 + DD% 佔賬戶比例

### 4.4 明細與設定

#### 📋 倉位明細
- 可排序表格（按時間/盈虧/層數/持倉時間/評分）
- Top 50 預設，可展開全部
- 每行：貨幣對、方向、層數、手數、淨盈虧、勝率、持倉時間(m)、評分

#### ⚙️ SET 參數
- 自動分類 7 個類別：基本設定、MA 系統、濾鏡系統、馬丁加倉、TP/SL 系統、新聞過濾、冷卻系統
- 🔴 已修改 / ✅ 預設值 標記
- 多 SET 文件並排顯示

#### 📁 歷史記錄
- localStorage 存檔系統（5MB 上限）
- 自動存檔（分析完成時）
- 重複偵測（CSV hash）
- 智能標籤提取（signal ID from filename, EA + pair from SET filename）
- 兩份存檔對比視圖（顏色差異）
- 趨勢迷你圖（勝率/PF/盈虧）
- 匯出/匯入 JSON

### 4.5 全局功能
- **📥 下載報告**：生成自包含 HTML 報告
- **ℹ️ Info Tooltips**：14 個區段的 ? 圖標，點擊展開說明
- **版本標籤**：頁尾顯示版本號 + CHANGELOG 連結
- **拖放上傳**：CSV + SET 拖放，支持多 SET
- **第二份 CSV**：用於市況×策略對比

---

## 5. 數據源

| 數據源 | 用途 | 狀態 |
|--------|------|------|
| MT4 .hst → JSON（本地） | 市場背景、市況分類、ATR 分析 | ✅ 主要數據源 |
| CSV 上傳 | 交易歷史分析 | ✅ |
| SET 上傳 | 參數分類對比 | ✅ |
| Yahoo Finance | ~~市場背景~~（已替換） | ❌ 已移除 |
| Finnhub | ~~外匯燭線~~（免費版 403） | ❌ 已拒絕 |
| Alpha Vantage | 方案 B/C 備用（需 API key） | 🔮 未來 |

---

## 6. 技術規格

### 前端
- **單文件 HTML**：`docs/index.html`（~4365 行）
- **零依賴**：純 HTML + CSS + JavaScript
- **GitHub Pages 部署**
- **響應式設計**：移動端友好

### 後端（Python CLI — 輔助用）
- `main.py` — 7 步管線 CLI
- `src/csv_parser.py` — CSV 解析
- `src/set_parser.py` — SET 解析 + 參數分類
- `src/position_builder.py` — 倉位重建
- `src/entry_quality.py` — 評分系統
- `src/statistics.py` — 五維統計
- `src/equity_curve.py` — 權益曲線
- `src/report_generator.py` — HTML 報告
- `src/compare_reports.py` — EA 對比報告
- `src/param_comparison.py` — 參數對比報告

### 數據轉換
- `scripts/export_hst.py` — MT4 .hst → JSON + 技術指標
- `docs/data/{PAIR}_D1.json` — 34 個貨幣對 D1 數據
- `docs/data/manifest.json` — 數據清單

### CSS 變量
```css
--primary: #0f3460;    /* 深藍 */
--accent: #e94560;     /* 紅色強調 */
--green: #28a745;      /* 綠色盈利 */
--yellow: #ffc107;     /* 黃色 B 級 */
--orange: #fd7e14;     /* 橙色 C 級 */
--red: #dc3545;        /* 紅色 D 級 */
```

### 等級著色
- A = #28a745（綠）
- B = #ffc107（黃）
- C = #fd7e14（橙）
- D = #dc3545（紅）

---

## 7. 版本歷史

| 版本 | 日期 | 主要功能 |
|------|------|----------|
| v1.0 | 2026-04-24 | 初始 UI + 基礎分析 |
| v2.0 | 2026-04-24 | 前端 UI 全面升級 |
| v3.0 | 2026-04-25 | Bug 修正 + Phase 1&2 全功能 |
| v3.1 | 2026-04-25 | 市場語境（方案 A） |
| v3.2 | 2026-04-25 | 本地 MT4 .hst 數據整合 |
| v3.3 | 2026-04-25 | Copy 推薦矩陣 |
| v3.4 | 2026-04-25 | 波幅分析 + 版本管理 + ℹ️ Tooltips |
| v3.5 | 2026-04-25 | 歷史記錄系統 + 後端報告增強 |
| v3.6 | 2026-04-25 | 市況×策略對比（方案 C）+ 雙 CSV |

---

## 8. 未來規劃

### Phase 3 — 知識庫 + 智能推薦
- [ ] EA 知識庫（整合 ea_manuals/ 文檔）
- [ ] 策略模板系統（不同 EA 的推薦參數範圍）
- [ ] 市場環境預測（基於歷史市況模式）
- [ ] 多 EA 策略組合優化
- [ ] 自動化信號頁面更新流程

### 方案 B/C 進階
- [ ] Alpha Vantage 技術指標整合（SMA/EMA/MACD/BBANDS/RSI/ADX/ATR）
- [ ] 入場點 vs 關鍵支撐/阻力位分析
- [ ] 完整策略×市況交叉分析（Strategy × Market Regime）
- [ ] 自適應參數建議（根據市況推薦調整 SET 參數）

### 數據管理
- [ ] 版本追蹤：`samples/{signal_id}_{EA}_{pair}/v{n}_{date}/`
- [ ] 自動歸檔 + 累積趨勢對比
- [ ] 趨勢警報（績效退化時自動通知）

---

## 附錄：EA 技術參數速查

### 馬丁格爾系統（MKD / SMA 共通）
- **基礎手數**：0.02
- **層數擴展**：lotExp = 1.8（0.02→0.04→0.06→0.12→0.21→0.38）
- **Pipstep 線性**：50→60→70→80→90→100→110 pips
- **最大層數**：slInLevel = 9
- **止損觸發**：DD 15% 全部平倉

### 出場機制
- **DollarMode**：主要出場機制（所有層數）
- **DynamicTP**：輔助出場
- **DollarMode0**：L1 專用設定
- **DollarMode**：L2+ 設定

### Magic Number
- 88 = SMA BUY
- 77 = SMA SELL
- 3901+ = MKD Dragon Ball 系列
