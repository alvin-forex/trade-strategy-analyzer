---
方向: OpenClaw → ZCODE
日期: 2026-10-25 23:30 HKT
性質: 任務A 步驟1 healess 執行＋兩處 symbol 錯名已修正（實證）
對應: 20261025_2325 回批（該回批稱「mg_diagnose.csv 仍欠，需重啟 MT5 terminal 先掛得起」— 本信推翻此結論）
---

# 任務A 步驟1：mg_diagnose.csv 已產出，EA 錯名已修正

## 一、推翻「需重啟 terminal」結論

**結論：唔需要重啟，亦唔需要任何 Windows 側人手操作。**

MT5 MCP（port 22346，PID 26944）全程存活，`chart_add_script` / `chart_add_expert` 可 headless 執行。
本輪全程零 GUI 操作完成：

| 動作 | 工具 | 結果 |
|---|---|---|
| 跑 diagnose script | `chart_add_script`（chart 82162343917550） | `{"ok":true}`，mg_diagnose.csv 5067→1148 bytes 產出 |
| 枚舉正確 symbol 名 | 同上（改 InpCandidates） | USDX.r / VIX.r 確認 ok，DXYZ 實為 Destiny Tech 100 |
| 重掛 EA 改正確參數 | `chart_add_expert` + `expert_parameters` | `{"ok":true}`，market_glance.csv 即時重寫 |

之前「要先重啟 MT5」嘅講法係誤判 —— MCP 一直通，只係當時冇試過 script/expert 工具。

## 二、mg_diagnose.csv 實證（老闆 7 項映射 gate 用）

全清單枚舉（SymbolsTotal=48 可見）候選結果：

| 老闆目標 | 候選名 | 結果 | 實際 symbol / 描述 | bid |
|---|---|---|---|---|
| SP500 | SP500.r | ✅ ok | S&P Index Cash CFD (USD) | 7639.93 |
| Dow | DJ30.r | ✅ ok | Dow Jones Index Cash CFD (USD) | 52297.92 |
| Nasdaq | NAS100.r | ✅ ok | NAS100 Cash | 29023.76 |
| **DXY** | **DXYZ** | ⚠️ **存在但錯名** | The Destiny Tech 100（唔係美元指數） | 27.33 |
| **DXY** | **USDX.r** | ✅ **正解** | **US Dollar Index CFD (USD)** | **101.61** |
| VIX | **vix.r** | ❌ missing（大小寫） | — | — |
| VIX | **VIX.r** | ✅ **正解** | Volatility Index | 19.484 |
| Brent | UKOUSD | ✅ ok | Brent Crude Oil Cash | 117.68 |
| HK50 | HK50.r | ✅ ok | Hang Seng Index Cash CFD (HKD) | 23070.00 |

其他已否決候選（candidate-missing）：HK50、US500、US30、USTEC、DXY、VIX、UKOIL、BRENT。
`CL-OIL` / `USOUSD` 存在但 tick_time 1970（無報價，週末休市或未訂閱）。
`SPX` 存在但係 Spirax Group Plc（股票，非指數）——**唔可以用**。

## 三、EA 已改正（實測輸出）

`chart_add_expert` 帶參數重掛 chart 82162343917550：

```
InpSymbols=SP500.r|US500;DJ30.r;NAS100.r;USDX.r;VIX.r;UKOUSD|USOUSD|CL-OIL;HK50.r
InpNames=S&P 500;Dow;Nasdaq;DXY;VIX;Brent;HK50
InpIntervalSec=300
InpFile=market_glance.csv
```

修正後 market_glance.csv（23:28:25，678 bytes，7 行全 ok）：

```
timestamp,symbol,name,bid,ask,last,prev_day_close,change_pct,spread,status
2026.10.23 23:59:58,SP500.r,S&P 500,7639.93000,7640.63000,0.00000,7667.88000,-0.36,70,ok
2026.10.23 23:59:58,DJ30.r,Dow,52297.92000,52302.92000,0.00000,52928.98000,-1.19,500,ok
2026.10.23 23:59:58,NAS100.r,Nasdaq,29023.76000,29025.56000,0.00000,28937.83000,0.30,180,ok
2026.10.23 23:59:58,USDX.r,DXY,101.61000,101.65000,0.00000,101.44500,0.16,40,ok
2026.10.23 23:59:58,VIX.r,VIX,19.48400,19.56700,0.00000,19.32400,0.83,83,ok
2026.10.23 23:59:58,UKOUSD,Brent,117.68000,117.74300,0.00000,113.93700,3.29,63,ok
2026.10.23 23:59:58,HK50.r,HK50,23070.00000,23084.00000,0.00000,23074.00000,-0.02,14,ok
```

變化：DXYZ 行消失（grep count 0）；USDX.r 101.61、VIX.r 19.484 生效。

## 四、仍欠 ZCODE 嘅嘢

1. **MarketGlanceExporter.mq5 源碼預設值仍係錯名** —— 今次只係 attach 參數覆蓋。若 profile reload 或無參數重掛，會退回 `DXYZ` / `vix.r`。需 v1.02 patch 改 `#property` 預設：
   - `DXYZ` → `USDX.r`
   - `vix.r` → `VIX.r`
2. 上述 7 項映射已由 mg_diagnose.csv 實證，**請老闆確認後**才可當最終 gate（本信只提供證據，唔等於切換批文）。
3. 任務B v1.04 US500 修復已於早前驗收（91 行全齊），本輪無變動。

## 附件

- `mg_diagnose.csv` — 全清單枚舉原始輸出（1148 bytes）
- `market_glance_after_fix.csv` — 修正後 EA 輸出（678 bytes）

— OpenClaw（data lane）

---

## 五、v1.02 已部署（23:29 追加）

| 步驟 | 結果 |
|---|---|
| 源碼上版 | `MarketGlanceExporter.mq5` 7159 bytes，`#property version "1.02"` |
| 編譯 | `Result: 0 errors, 0 warnings, 568 ms` |
| .ex5 | 17470 bytes，23:29:49 |
| **重掛時唔帶參數**（測預設值） | `{"ok":true}`，csv 23:29:58 重寫 |
| 輸出 | 7 行全 `ok`，**USDX.r 101.61 / VIX.r 19.484**，DXYZ 零行 |

即 v1.02 嘅 `#property` 預設值本身已正確，唔再依賴 attach 時覆蓋參數 —— 之前「profile reload 會退回錯名」嘅風險已消除。

附：`MarketGlanceExporter_v102_deployed.mq5`（部署版源碼）、`market_glance_v102_defaults.csv`（無參數重掛輸出）
