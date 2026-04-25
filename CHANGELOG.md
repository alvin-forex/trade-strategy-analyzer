# 📋 Trade Strategy Analyzer — 版本更新日誌

版本規則：**Major.Minor**（如 v3.2）
- **Major**：新功能模組 / 架構改動
- **Minor**：bug fix / 小優化 / UI 調整

---

## [v3.4] — 2026-04-25
### 📏 新增：波幅適配分析
- 新增「📏 波幅分析」Tab
- 各層波幅統計：平均/最小/最大波幅 + 勝率 + 平均盈虧
- ATR 市況交叉分析：低/中/高波幅環境下勝率對比
- 自動結論：策略喺咩 ATR 環境下表現最佳
- 波幅敏感度警告（勝率差 > 20%）
- Pip size 自動換算（JPY×100, 標準×10000, XAU/XAG×0.1）

---

## [v3.3] — 2026-04-25
### 🏆 新增：Copy Trade 推薦矩陣
- 新增「🏆 Copy 推薦」Tab
- 貨幣對 × 層數交叉分析（L1/L2/L3/L4+）
- 每個格子顯示 Grade + 勝率 + PF + 平均盈虧
- 自動推薦每個貨幣對最佳層數
- 🥇🥈🥉 Top 3 總結
- 評級標準：A=WR≥60%+PF≥1.5, B=WR≥50%+PF≥1.2, C=WR≥40%+PF≥1.0, D=其餘
- L4+ 最高評級 B（風險考量）

---

## [v3.2] — 2026-04-25
### 🌐 新增：本地市場數據整合
- 替代 Yahoo Finance，改用本地 MT4 .hst 歷史數據
- 34 個貨幣對 D1 數據導出至 JSON（2018-2026，~1929 bars/pair）
- 新增 `scripts/export_hst.py`：.hst → JSON 轉換工具
- JSON 包含技術指標：SMA 20/50/200, EMA 12/26, RSI 14, ATR 14, MACD
- `docs/data/manifest.json` 記錄數據元資訊
- 完全離線運行，無需外部 API

---

## [v3.1] — 2026-04-25
### 🌐 新增：市場語境分析（方案 A）
- 新增「🌐 市場語境」Tab（初版使用 Yahoo Finance，後被本地數據取代）
- 自動載入 CSV 時間範圍內嘅價格走勢
- Top 5 貨幣對趨勢分析 + 交易方向匹配
- SVG 價格走勢圖（BUY/SELL 標記）
- 趨勢判定：range(<1%), up, down
- Verdict：ok（順勢）/ warn（逆勢）/ neutral

---

## [v3.0] — 2026-04-25
### 🔧 Bug Fix 大修正 + 功能完善
**6 項 Bug Fix：**
1. **層數偵測**：從比率硬編碼改為動態排序唯一手數映射（配合後端）
2. **倉位分組**：從 60s tolerance 改為 floor-to-minute（配合後端）
3. **美洲盤時段**：修復 0-5 HKT 缺失問題
4. **Sortino Ratio**：加入 risk_free_rate=0.02 扣減
5. **下載按鈕**：新增 UI 按鈕觸發報告下載
6. **代碼清理**：移除不必要嘅 monkey-patch 包裝

**前端完整功能（Phase 1 + Phase 2）：**
- ✅ CSV 解析（過濾非交易、BOM 處理）
- ✅ SET 參數解析 + 分類
- ✅ 倉位重建（Symbol+Direction+CloseTime±60s）
- ✅ Entry Score（方向 35% + 時機 35% + 初始 DD 30%）
- ✅ Strategy Score（回歸 30% + 出場效率 25% + 風控 20% + 利潤品質 15% + 持倉成本 10%）
- ✅ Final Score = Entry×0.4 + Strategy×0.6
- ✅ 評級 A/B/C/D（可Copy/需評估/需調整/不建議）
- ✅ 完整統計（Sharpe/Calmar/Sortino/CVaR/Gain-Pain/Skewness/ Exposure Time）
- ✅ 收益曲線 SVG
- ✅ 貨幣對排名表
- ✅ 層數分析（L1/L2/L3/L4+ + Martin Health）
- ✅ 時段分析（亞洲/歐洲/美洲/其他）
- ✅ 方向分析（BUY/SELL）
- ✅ 倉位明細（排序 + 展開）
- ✅ SET 參數展示

---

## [v2.0] — 2026-04-24
### 🎨 前端 UI 升級
- 單一 HTML 檔案，純瀏覽器運算
- 拖放上傳 CSV + SET 檔案
- 基礎統計（總覽 + 按貨幣對）
- 收益曲線 SVG
- 貨幣對排名（PF 排序 + 顏色標記）
- 倉位明細（前 50 筆）
- 響應式設計（mobile RWD）
- 香港繁體中文介面

---

## [v1.0] — 2026-04-24
### 🚀 初始版本
- GitHub Pages 部署
- 基礎上傳 + 解析 UI
- 後端 Python 模組（CSV parser, SET parser, position builder, entry quality, statistics, equity curve, report generator）

---

*最後更新：2026-04-25 | 維護者：丁蟹 🦀*
