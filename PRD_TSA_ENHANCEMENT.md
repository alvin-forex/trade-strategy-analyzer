# TSA Enhancement PRD v1.0

**Date:** 2026-06-02
**Author:** 丁蟹 (AI Assistant)
**Status:** In Progress
**Reference:** [Derrick's Martingale Analyzer v1.68](https://derrick-algo.github.io/TradingHistoryAnalyzer/)

---

## 1. Background

老闆要求參考 Derrick 嘅 Martingale Analyzer v1.68，全面改善 TSA (Trade Strategy Analyzer)。經過功能對比分析，識別咗 6 個主要改進項目。

## 2. Data Foundation

CSV columns available in all signal downloads:
```
Open Time, Type, Lots, Symbol, Open Price, Close Time, Close Price,
Commission, Swap, Net Pips, Net Profit, Max Profit, Max Pips,
Max Loss, Max Loss Pips, Magic Number, Comment, Holding Time (Hours), Holding Time
```

## 3. Improvement Items

### P0 — High Priority (Completed)

#### P0-1: BUY/SELL Pivot Table ✅
- **Script:** `generate_pivot_table.py`
- **Page:** `/admin/pivot_table.html`
- **Features:**
  - Section 1: BUY/SELL Summary — Top 100 by P&L, per Signal×CCY
  - Section 2: Martin Layer Analysis — Layer 1-N, BUY vs SELL
  - Section 3: Per-Signal Drill-down — Click to expand layer breakdown
- **Columns:** Trades, Win%, Avg Pips, Total P&L, Avg Hold Time (for BUY and SELL separately)
- **Color coding:** Green >70%, Yellow 50-70%, Red <50%
- **Size:** ~289 KB

#### P0-2: Time Period Statistics ✅
- **Script:** `generate_period_stats.py`
- **Page:** `/admin/period_stats.html`
- **Features:** 8 tab sections
  - 📅 Day of Week (Mon-Sun) with bar chart + Best/Worst CCY
  - 📆 Week (last 12 weeks)
  - 🗓 Month (last 12 months)
  - 📊 Quarter
  - 📈 Year
  - 🕐 Hour of Day (0-23 HKT) with count bar
  - 🔮 Magic Number grouping
  - 💬 Comment grouping (Top 50)
- **Filters:** Signal dropdown, CCY dropdown
- **Size:** ~52 KB

### P1 — Short Term (3-5 days)

#### P1-1: MFE/MAE Analysis
- **Script:** `generate_mfe_mae.py` (new)
- **Page:** `/admin/mfe_mae.html`
- **Data source:** `Max Profit` (MFE), `Max Loss` (MAE), `Max Pips`, `Max Loss Pips`
- **Features:**
  - MFE/MAE distribution chart (histogram by pips range)
  - Per Signal×CCY: Avg MFE, Avg MAE, MFE/MAE ratio
  - Per layer: MFE/MAE trend (higher layers = bigger drawdowns?)
  - TP/SL optimization suggestion based on MFE/MAE distribution
  - Click any cell in pivot table → see MFE/MAE distribution popup
- **Output:** HTML with inline SVG charts
- **Difficulty:** Medium

#### P1-2: History JSON Backup/Restore
- **Script:** `history_manager.py` (enhance existing)
- **Page:** Integrated into existing pages
- **Features:**
  - Export analysis result to JSON (with metadata: date, signal_id, params)
  - Import JSON to restore previous analysis
  - History list page showing all saved analyses
  - Version comparison (compare two runs of same signal)
- **Storage:** `data/history/` folder, one JSON per analysis
- **Difficulty:** Low

### P2 — Medium Term (1-2 weeks)

#### P2-1: Bar OHLC Data Integration
- **Script:** `generate_bar_analysis.py` (new)
- **Page:** `/admin/bar_analysis.html`
- **Data source:** Bar CSV files (user uploads)
- **Features:**
  - Import Bar (OHLC) CSV data
  - Calculate ATR (Average True Range) per period
  - Correlate trade entries with candlestick patterns
  - Show volatility at entry time vs outcome
  - Support multiple bar CSV files (per symbol)
- **Difficulty:** High (needs data format standardization)

#### P2-2: Session Highlight + Magic/Comment Deep Analysis
- **Script:** Enhance `generate_period_stats.py`
- **Features:**
  - Highlight trading sessions (Asian/European/US) on trade list
  - Session performance breakdown
  - Magic Number × CCY cross analysis
  - Comment pattern extraction (EA name, TP/SL type)
- **Difficulty:** Low

## 4. Technical Architecture

```
trade_strategy_analyzer/
├── generate_pivot_table.py      # P0-1 ✅
├── generate_period_stats.py     # P0-2 ✅
├── generate_mfe_mae.py          # P1-1 (new)
├── generate_ranking_ccy_v5.py   # Existing (HT added)
├── history_manager.py           # P1-2 (enhance)
├── generate_bar_analysis.py     # P2-1 (new)
├── docs/
│   ├── sidebar.js               # Navigation (updated)
│   ├── sidebar.css
│   └── admin/
│       ├── pivot_table.html     # P0-1 ✅
│       ├── period_stats.html    # P0-2 ✅
│       ├── mfe_mae.html         # P1-1
│       ├── ccy_ranking.html     # HT added ✅
│       └── ...
├── downloads/                   # CSV source files
└── data/history/                # P1-2 JSON storage
```

## 5. Style Guide

- Theme: Dark/Light toggle (same CSS variables as existing pages)
- Sidebar: Shared `sidebar.js` + `sidebar.css`
- Tables: Sortable columns, click header to sort
- Colors: Green (>70% win), Yellow (50-70%), Red (<50%)
- EA badges: DW=purple, SMA=green, MKD=orange, Flash=blue, S10=teal, GEM=pink, MAN=indigo
- Responsive: Mobile-friendly with `@media(max-width:768px)`

## 6. Verification Checklist

- [ ] HTML file > 10KB
- [ ] Sidebar navigation includes new page
- [ ] Dark/Light theme toggle works
- [ ] Sortable columns functional
- [ ] No JS errors in console
- [ ] Mobile responsive
- [ ] Git commit + push to GitHub Pages
- [ ] Live URL accessible

## 7. Progress

| Item | Status | Commit |
|---|---|---|
| HT column (ccy_ranking) | ✅ Done | `2c0f67a` |
| P0-1 BUY/SELL Pivot | ✅ Done | `547cc7b` |
| P0-2 Time Period Stats | ✅ Done | `547cc7b` |
| P1-1 MFE/MAE | 🔲 Pending | — |
| P1-2 History JSON | 🔲 Pending | — |
| P2-1 Bar OHLC | 🔲 Pending | — |
| P2-2 Session Highlight | 🔲 Pending | — |
