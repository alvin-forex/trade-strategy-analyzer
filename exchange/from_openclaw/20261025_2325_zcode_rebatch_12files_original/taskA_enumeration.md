# 任務 A 步驟 1 — MT5 725B 7 項 symbol 枚舉結果（2026-10-23 23:35）

方法：MCP catalog 直接查（diagnose script 已部署+編譯，但 terminal program index
建於 18:27 啟動時，22:54 後編譯嘅 .ex5 未被索引 → 掛載需重啟 terminal，見下）。

## 枚舉結果表（全部已加 Market Watch，有實時報價）

| 項目 | ZCODE 候選 | 實際正確 symbol | bid | ask | tick time (terminal) |
|---|---|---|---|---|---|
| S&P 500 | SP500.r | ✅ SP500.r | 7658.98 | 7659.58 | 18:29:53 |
| Dow | DJ30.r | ✅ DJ30.r | 52422.37 | 52425.47 | 18:35:33 |
| Nasdaq | NAS100.r | ✅ NAS100.r | 29127.89 | 29129.69 | 18:35:33 |
| DXY | DXYZ | ❌ → **USDX.r** | 101.598 | 101.638 | 18:35:30 |
| VIX | vix.r | ❌ → **VIX.r** | 19.509 | 19.592 | 18:34:50 |
| Brent | UKOUSD | ✅ UKOUSD | 117.449 | 117.503 | 18:35:32 |
| HK50 | HK50.r | ✅ HK50.r | 23097 | 23101 | 18:35:30 |

tick time 係 terminal 本地（server = HKT-5），18:35 ≈ HKT 23:35 = 查詢當時，全部新鮮。

## 關鍵發現（要 ZCODE 修正）

1. **`DXYZ` 唔係美元指數** — 係 NYQ 上市美股「The Destiny Tech 100」
   （ISIN US25063F1075，sector Financial / Assets Management）。
   老闆之前確認「DXYZ」存在係真，但呢個 symbol 嘅**描述完全唔係 DXY**。
   呢個 broker 嘅美元指數正確 symbol = **`USDX.r`**（"US Dollar Index CFD (USD)"，
   id 2575，swap 0，volume_min 0.1）。
   → `MarketGlanceExporter.mq5` InpSymbols 要改 `DXYZ` → `USDX.r`
   （diagnose script 嘅候選清單照樣保留 DXYZ 做比對冇問題，但實際取值用 USDX.r）

2. **`vix.r` 細楷唔存在** — SymbolSelect 大小楷敏感。實際 symbol = **`VIX.r`**
   （"Volatility Index"，id 2576，XSNP）。`add_marketwatch_symbol("vix.r")` 回
   `symbol not found`；`("VIX.r")` 成功。
   → `MarketGlanceExporter.mq5` InpSymbols 要改 `vix.r` → `VIX.r`

3. 其餘 5 項 ZCODE 候選名全部正確（SP500.r / DJ30.r / NAS100.r / UKOUSD / HK50.r）。

## 掛載阻塞（需 Windows 側人手）

- .ex5 已部署+編譯（Experts/MarketGlanceExporter.ex5，22:54 產出，0 errors）
- MCP `chart_add_expert` / `chart_add_script` 均回 `not found in base` —
  同 mt5-mcp-verify skill step 22 記錄一致：program index 建於 terminal 啟動時
  （terminal 18:27 起），後補編譯嘅 .ex5 唔會自動入索引
- 現有 4 個 chart 全掛住交易 EA（GoldSupporter / AngelGold_v4 / PlanExecutor /
  TradeDashboard5），唔可以郁
- 已開新 chart（chart_id 81334745672410, XAUUSD H1）等掛 Exporter
- **解法：重啟 MT5 terminal（Windows 側人手）**；重啟後 Exporter 可掛上新 chart，
  每 5 分鐘寫 MQL5/Files/market_glance.csv

## 現階段狀態

- ✅ 驗收 1（枚舉表）完成 — 上表
- ⏸ 驗收 2（market_glance.csv）— 等重啟後掛 Exporter 先有
- ✅ 任務 AC patch 已就位：`fetch_market_glance_mt5` 讀 market_glance.csv，
  缺源時全部 7 項標「缺數」（設計行為，唔會 fallback）
