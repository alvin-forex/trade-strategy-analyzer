# CurrencyPower v3 技術白皮書

> **版本**：v3.10（MT5）／ v3.07-MQ4（MT4 移植）
> **日期**：2026-10-20
> **狀態**：審核版 v3.10（含已知缺陷清單，audit-grade）
> **作者**：OpenClaw for Alvin
> **源碼位置**：
> - MT5（v3.10）：`CurrencyPower_v3.mq5`（MT5 終端安裝目錄 MQL5/Indicators/ 與 workspace `mt4-ea/` 兩處同步，md5 `25d142a2102e59505620c61343aeada6`）
> - MT4（v3.07）：`mt4-ea/CurrencyPower_v3_MQ4.mq4`
> **編譯證據**：MetaEditor64 CLI 重編 v3.10 = **0 errors, 0 warnings**（1071 ms, X64 Regular）；`CurrencyPower_v3.ex5` 46,190 bytes，md5 `70008ad26b22859167e48028b07f7cc4`

---

## 1. 概述

CurrencyPower v3 係一套**貨幣強弱量化指標**，輸出 9 條貨幣力量線（XAU / USD / EUR / JPY / GBP / AUD / CAD / CHF / NZD）＋ 一個互動排名面板。核心概念：**任何貨幣對嘅升跌 = 兩隻貨幣力量嘅差**；將 36 個 instrument 嘅 RSI 動力分解返去貨幣層面，即可量度每隻貨幣嘅「真實」相對強弱。

v3 相對 v1/v2 嘅主要演進：

| 項目 | v1 | v2 | v3 |
|---|---|---|---|
| 輸出 | 9 線副圖 | 9 線副圖 | 9 線 ＋ Diff 集中度 ＋ 排名面板 |
| 加權 | 無 | 無 | ATR% 波動加權 |
| Slope | 無 | 無 | t-stat 斜率箭咀 |
| 面板 | 無 | 無 | 互動式（click toggle / expand / TOP PAIRS） |
| 平台 | MT4 | MT5 | MT4 ＋ MT5 雙版本 |

**v3.10（2026-10-19）修復 B1–B4（P0–P3）**：補回 TOP PAIRS ＋ expand block（MT4 移植）、`ChartWindowFind` 短名 ＋ cached `OnTimer` 重畫、主 plot 改 `DRAW_NONE` ＋ 實作 `Alert_On`、scoped `OnDeinit`。詳見 §7。

---

## 2. 系統架構

```
36 個 instrument（28 主要貨幣對 + XAUUSD + 7 黃金交叉盤）
    │  iRSI(PairTF, RSI_Period)  → raw[p] = RSI − 50
    │  iATR(PairTF, ATR_Period)  → w[p] = ATR% （波動加權）
    ▼
Calc()：貨幣分解引擎
    │  每 pair 動力：一半歸 base（＋）、一半歸 quote（−）
    │  每貨幣取平均 → 0–100 力量值（50 = 中性）
    ▼
9 條 power lines（B0–B8）＋ Diff（B9，DRAW_NONE，只做 panel 值）
    │  SlopeT() 線性回歸 t-stat → 箭咀（^^ ^ - v vv）
    ▼
UI()：互動排名面板（OBJ_LABEL / OBJ_RECTANGLE_LABEL）
    │  click 行 = toggle 顯示／expand 對比
    │  click badge = 收起面板
    ▼
OnChartEvent / OnTimer（cached 重畫，5s）更新
```

---

## 3. 計算引擎（數學公式）

### 3.1 RSI 動力值（per instrument）

對全部 36 個 instrument，喺 **PairTF**（預設 H1）計：

```
raw[p] = RSI(RSI_Period, PRICE_CLOSE) − 50        // 範圍 −50..+50
```

RSI > 70 → raw ≈ +20（強勢）；RSI < 30 → raw ≈ −20（弱勢）。

### 3.2 ATR 波動加權

每個 instrument 嘅 raw 值用 **ATR%** 加權，目的係令高波動 instrument（尤其黃金交叉盤）唔會被低波動 pair 稀釋：

```
w[p]  = ATR(ATR_Period) / Close × 100            // ATR%
avgW  = mean(所有有效 w[p])
v     = raw[p] × (w[p] / avgW)                    // 歸一化：平均權重 = 1
```

若某 instrument handle 無效／數據讀取失敗 → `w[p] = 0`，完全排除。

### 3.3 貨幣強弱分解（28 主要貨幣對）

每個 pair 嘅加權動力值，一半歸 base（＋）、一半歸 quote（−）：

```
c[base] += v        c[quote] −= v        cnt[base]++        cnt[quote]++
pw[k] = 50 + c[k] / cnt[k]          // k = USD, EUR, JPY, GBP, AUD, CAD, CHF, NZD
```

例：EURUSD RSI = 70（raw = +20）→ EUR ＋20、USD −20。

### 3.4 XAU 特殊處理

黃金冇「單一匯率」，用 **XAUUSD ＋ 7 個黃金交叉盤**（XAU vs EUR/GBP/AUD/JPY/CHF/CAD/NZD）綜合：

```
gx  = raw[XAUUSD]×w' ＋ Σ raw[XAU vs Q]×w'        // 全部計入 XAU
pw[XAU] = 50 + gx / gn

// 交叉盤嘅 quote 貨幣同時受影響（只計一半權重，避免雙重計算）：
c[Q] −= v × 0.5        pw[Q] 即時更新
```

> ⚠️ 設計注意：交叉盤 quote 貨幣只收 **50%** 權重，而 28 主要 pair 收 **100%**——係刻意嘅不對稱設計（黃金力量優先歸 XAU 線），但數學上令 quote 貨幣嘅力量值帶有輕微偏差，審核時請確認呢個設計係咪預期（見 §9-A2）。

### 3.5 Slope t-stat（斜率箭咀）

對每隻貨幣最近 `Slope_Lookback` 個 power 值做簡單線性回歸，計算 **slope / 標準差**（t 統計量）：

```
m  = min(Slope_Lookback, 可用長度)     // m < 4 時返回 0
slope = (m·Σxy − Σx·Σy) / (m·Σx² − (Σx)²)
sd    = sqrt(Σ(y−ȳ)² / m)，下限 0.15（避免除零）
t     = slope / sd
```

箭咀分級：

| t 值 | 箭咀 | 含義 |
|---|---|---|
| t > +0.30 | `^^` | 強加速上升 |
| +0.10 < t ≤ +0.30 | `^` | 上升 |
| −0.10 ≤ t ≤ +0.10 | `-` | 無趨勢 |
| −0.30 ≤ t < −0.10 | `v` | 下跌 |
| t < −0.30 | `vv` | 強加速下跌 |

### 3.6 DIFF 集中度

```
DIFF = max(pw[0..8]) − min(pw[0..8])
```

衡量 9 貨幣力量嘅**最大差距**（趨勢集中度）。DIFF 越大 = 強弱分明 = 趨勢越健康；DIFF 細（例如 < 10）= 全部貨幣擠喺 50 附近 = 震盪市、冇方向。

面板 footer 顯示 DIFF 數值 ＋ 進度 bar（0–25 刻度，`width = min(DIFF × 3.2, 80)px`，升綠跌灰）。

### 3.7 Alert（v3.10 新增，MT5）

`Alert_On`（預設 true）喺每次 new bar 重算時檢查每隻貨幣力量值嘅**穿越事件**：

```
若 pw[k] 由 <70 升穿 ≥70 → Alert("... crossed above 70.0")
若 pw[k] 由 >30 跌穿 ≤30 → Alert("... crossed below 30.0")
```

每次穿越只觸發一次（用 `g_prevPw[k]` 記住上一 bar 值做穿越偵測）。⚠️ 注意：alert 以 **bar 收盤**為準（喺 `OnCalculate` 內觸發），非 tick 級。

---

## 4. 參數說明

| 參數 | 預設 | 類型 | 說明 |
|---|---|---|---|
| `RSI_Period` | 14 | int | RSI 週期。細 = 快但雜訊多；大 = 平滑但遲鈍 |
| `ATR_Period` | 14 | int | ATR 週期，用於波動加權 |
| `Slope_Lookback` | 10 | int | Slope 回歸窗口（最少 4 支 bar 先有效） |
| `Lookback_Bars` | 300 | int | 指標最多回算嘅 bar 數（限制 CPU 負載） |
| `PairTF` | PERIOD_H1 | ENUM_TIMEFRAMES / int | **全部計算用嘅時框**（與 chart 時框無關） |
| `Alert_On` | true | bool | **MT5 v3.10 已實作**：power 穿越 70/30 觸發 `Alert()`（見 §3.7）。⚠️ MT4 v3.07 仍係**死參數**（見 §9-A1） |
| `TickStyle` | 0 | int | 面板勾選樣式：0=`[x]/[  ]`、1=`+/x`、2=`●/○` |
| `Show_Panel` | true | bool | 開機預設顯示面板（可 click badge 即時切換） |

---

## 5. 面板 UI 規格

面板係 `OBJ_RECTANGLE_LABEL` 背景 ＋ `OBJ_LABEL` 文字行，掛喺 indicator subwindow 左上角。

### 5.1 版面（兩版本共通，v3.10 起 MT5 已補回 TOP PAIRS ＋ expand）

```
┌──────────────────────────────┐
│ ON  CCY   POWER  SLOPE       │ ← header
│ [x] XAU   63.4  ^            │ ← 9 行，按 power 由大到小排序
│ [x] USD   58.1  -            │
│ [ ] JPY   32.7  vv           │ ← click tick 可隱藏/顯示該貨幣線
│ ...                          │
│ -- TOP PAIRS --              │ ← v3.10 補回（MT4 移植）
│ EURJPY 21.3  EUR>JPY         │ ← power 差距最大嘅 3 組
│ ...                          │
│ DIFF 30.7 ^   ████████░░     │ ← DIFF 值 + 集中度 bar
└──────────────────────────────┘
```

- **click 行**：toggle 該貨幣線顯示（`DRAW_LINE` ↔ `DRAW_NONE`）
- **click 貨幣名稱（`CP3R_*`）**：展開該貨幣 vs 其餘 8 隻嘅力量差列表（綠色 ^ / 紅色 v）；再 click 收起
- **click badge**（右上角 "CurrencyPower v3.10"）：收起／展開整個面板

### 5.2 TOP PAIRS（v3.10 起兩版本都有）

自動選出 9 貨幣之間 power 差距最大嘅 3 組組合（`CCY1CCY2 + diff + 強>弱`），每組以貨幣對字串顯示。MT5 v3.10 實作於 `UI()`（計算 L306、標題 L318、3 行 L322-331）。

### 5.3 Expand 對比（v3.10 起兩版本都有）

click 貨幣行嘅 `CP3R_<CCY>` → 右邊（x=160）展開該貨幣 vs 其餘 8 隻嘅力量差（`g_lastPw[g_expand] − g_lastPw[e]`），按絕對差排序，正值綠色 `^`、負值紅色 `v`。MT5 v3.10 實作於 `UI()`（L351-362）。

### 5.4 Object 命名表

| Object | 用途 |
|---|---|
| `CP3PANEL` | 面板背景 |
| `CP3HDR` | header 文字 |
| `CP3T_<CCY>` | 貨幣行（tick 勾選）— click toggle 線 |
| `CP3R_<CCY>` | 貨幣行（名稱＋數值＋箭咀）— click expand／收起 |
| `CP3TPH` / `CP3TP1..3` | TOP PAIRS header／3 行（v3.10 起兩版本） |
| `CP3DIFF` / `CP3DB` / `CP3DF` | DIFF 文字／背景 bar／填充 bar |
| `CP3EH` / `CP3E_<CCY>` | expand header／8 行（v3.10 起兩版本） |
| `CP3BADGE` | 右上角版本徽章（click 收面板） |
| `CP3A_<CCY>` | chart 上每條線末端嘅箭咀 object（MT5 only） |

---

## 6. MT4 / MT5 實作對照（更新至兩版現狀）

| 功能 | MT5 **v3.10** | MT4 v3.07-MQ4 |
|---|---|---|
| 計算引擎 | `Calc()` 用 handle + `CopyBuffer` | `Calc()` 用 `iRSI()/iATR()` 直接 call |
| 9 條 power lines | ✅ B0–B8 | ✅ B0–B8 |
| Diff buffer (B9) | ✅ `DRAW_NONE`（v3.10 由 `DRAW_HISTOGRAM` 修正，只做 panel 值） | ✅ `DRAW_NONE` |
| Slope 箭咀（panel 文字） | ✅ | ✅ |
| Slope 箭咀（chart 線端 object） | ✅ `CP3A_*`（OBJ_ARROW_UP） | ❌ 無 |
| 排名排序 | ✅ | ✅ |
| Click toggle 線 | ✅ | ✅ |
| Click 收面板（badge） | ✅ | ✅ |
| **TOP PAIRS** | ✅ **v3.10 補回**（MT4 移植） | ✅ |
| **Expand 對比** | ✅ **v3.10 補回**（MT4 移植） | ✅ |
| 無 tick 時 UI 更新 | ✅ `OnTimer` 5s **cached 重畫**（v3.10 移除 `ChartSetSymbolPeriod`，唔再騷擾 zoom/scroll） | ✅ `OnTimer` 5s cached 重畫 |
| subwindow 定位 | ✅ `ChartWindowFind(0,"CP v3")`（v3.10 修正，傳指標短名） | ✅ `WindowFind("CP v3 MQ4")` |
| **`Alert_On`** | ✅ **已實作**（v3.10，穿越 70/30） | ❌ **死參數**（見 §9-A1） |
| OnDeinit 清理 | ✅ 只刪 `"CP3"` prefix（v3.10 scoped） | ✅ 只刪 `"CP3"` prefix |

---

## 7. v3.10 變更明細（B1–B4）

| 項目 | 嚴重度 | 內容 | v3.10 實作證據 |
|---|---|---|---|
| **B1** | P0 | 補 TOP PAIRS 繪製 ＋ expand block（照 MT4 移植） | `UI()`：TOP PAIRS 計算 L306、標題 L318、3 行 L322-331；expand `CP3R_*` 創建 L303、`CP3E_*` block L351-362 |
| **B2** | P1 | `ChartWindowFind` 傳指標短名；`OnTimer` 改 cached 重畫；移除 `ChartSetSymbolPeriod` | `gSub = ChartWindowFind(0,"CP v3")` L135；`OnTimer` cached 重畫 L472-484，註明「no ChartSetSymbolPeriod」L477；source 已無 active `ChartSetSymbolPeriod` call |
| **B3** | P2 | 主 plot 改 `DRAW_NONE`；實作 `Alert_On` 開關 | `#property indicator_type10 DRAW_NONE` L44（原 `DRAW_HISTOGRAM`）；`input bool Alert_On` L52；穿越偵測＋`Alert()` L435-441（升穿 70 / 跌穿 30，每次穿越一次） |
| **B4** | P3 | `OnDeinit` 只刪自己 prefix 物件 | `ObjectsDeleteAll(0,"CP3")` L172（scoped）；另兩處同款 scoped 清理 L272（面板收起）、L383（badge） |

**編譯驗證**：MetaEditor64 CLI 重編 v3.10 = **0 errors, 0 warnings**（1071 ms, X64 Regular）；`CurrencyPower_v3.ex5` 46,190 bytes @ 2026-10-20 10:51，md5 `70008ad26b22859167e48028b07f7cc4`。

---

## 8. 已知問題與缺陷清單（審核重點）

> v3.10 已修復上一版嘅面板缺陷（B1–B6）同 MT5 `Alert_On` 死參數；以下為**現狀**——已修復項標記「✅ 已於 v3.10 修復」，其餘為仍然存在嘅缺陷／限制。誠實列出，審核唔遮醜。

### A. 共通問題（兩版本）

| ID | 嚴重度 | 狀態 | 描述 | 證據 |
|---|---|---|---|---|
| **A1** | 中 | ⚠️ **MT5 已修復／MT4 未修** | **`Alert_On`**：MT5 v3.10 已實作穿越 70/30 alert（L435-441）；但 **MT4 v3.07 仍然係死參數**——source 只有 `input bool Alert_On = true`（L28），冇任何讀取、冇 `Alert()` call。MT4 用戶開關佢冇效果 | MT4 grep `Alert_On` 只命中 L28 |
| **A2** | 低 | 仍然存在 | **黃金交叉盤 quote 貨幣收半權重**（`v*0.5`），與 28 主要 pair 全權重不對稱。係設計決定，但令受黃金交叉盤影響嘅貨幣（EUR/GBP/AUD/JPY/CHF/CAD/NZD）力量值帶系統性偏差 | MT5 `Calc()` gold cross 段／MT4 對應 |
| **A3** | 低 | 仍然存在 | **`if(rt<10) return(0)`**：初始不足 10 支 bar 時指標完全空白，掛載早期會短暫無輸出 | 兩版本 `OnCalculate` 首行 |
| **A4** | 低 | 仍然存在 | **每次 new bar 全量重算 `Lookback_Bars`（300）支**，每支 bar 要讀 36×2 個 indicator handle——CPU 負載偏高；MT4 版用直接 call 更重 | `OnCalculate` loop |

### B. MT5 面板缺陷（上一版 §7-B1–B6 之現況）

| ID | 嚴重度 | 狀態 | 描述 | 證據 |
|---|---|---|---|---|
| **B1** | ~~高~~ | ✅ **已於 v3.10 修復** | **TOP PAIRS 區塊缺失** → 已照 MT4 移植補回 | v3.10 `UI()` L306/L318/L322-331 |
| **B2** | ~~高~~ | ✅ **已於 v3.10 修復** | **Expand 對比死 code** → 已補 `CP3R_*` 創建 ＋ `CP3E_*` block 繪製 | v3.10 L303/L351-362 |
| **B3** | ~~中~~ | ✅ **已於 v3.10 修復** | **subwindow 定位**：`ChartWindowFind()` 空參數 → 已改傳短名 `"CP v3"` | v3.10 L135 |
| **B4** | ~~中~~ | ✅ **已於 v3.10 修復** | **`OnTimer` 每 5 秒 `ChartSetSymbolPeriod` 強制重設 chart** → 已改 cached 重畫並移除 | v3.10 `OnTimer` L472-484、L477 註解 |
| **B5** | ~~中~~ | ✅ **已於 v3.10 修復** | **Diff buffer（B9）宣告 `DRAW_HISTOGRAM` 誤導** → 已改 `DRAW_NONE`（誠實宣告） | v3.10 L44 |
| **B6** | ~~低~~ | ✅ **已於 v3.10 修復** | **`OnDeinit` 刪除從未創建嘅 objects** → 已 scoped 只刪 `"CP3"` prefix，且 TOP PAIRS／expand objects 依家真係存在 | v3.10 L172 |
| **B7** | 低 | 🆕 **v3.10 新發現（剩餘）** | **cached 重畫路徑嘅 slope 箭咀會短暫顯示 `-`**：`OnTimer`（L478-479）同 expand click 都傳 `t9`（全 0）畀 `UI()`，箭咀 = `Arrow(0.0)` = `-`。即係兩支 new bar 之間，面板 slope 箭咀列會由真實值變 `-`，直到下一個 bar 重算先回復。**不影響計算、純視覺** | v3.10 `OnTimer` 傳 t9=0；`UI()` 用 `t[k]` 畫箭咀 |

### C. 已知限制（非 bug，設計使然）

| ID | 描述 |
|---|---|
| **C1** | 計算只喺 **new bar** 觸發（`limit = rates_total − prev_calculated`），tick 級變化唔會即時反映；v3.10 起 MT5 `OnTimer` 每 5s 用 cached 值**重畫 UI**（數值唔會變，因為重算仍只喺 new bar），但 zoom/scroll 已唔再被騷擾 |
| **C2** | instrument 解析（`FindSym`）依賴 broker 嘅 symbol 命名，靠 stripping（`.R`/`.RAW`/`.M`/`.`）匹配；若 broker 用特殊後綴（如 `.m` 之外嘅自定義後綴）會匹配失敗，該 pair 被靜默排除 |
| **C3** | 面板文字用 `Courier New Bold` 固定字型，高 DPI ／細 subwindow 下可能遮蓋價格線（panel 唔可拖動） |
| **C4** | **Alert 以 bar 收盤為準**（喺 `OnCalculate` 內觸發），非 tick 級即時；穿越偵測用「上一 bar 值 vs 今 bar 值」，bar 內大幅波動跳過 70/30 區間時可能偵測唔到（gap-through） |

---

## 9. 建議修復優先序（供審核後跟進）

| 優先序 | 項目 | 狀態 | 工作量 |
|---|---|---|---|
| P1 | **MT4 實作 `Alert_On`**（照 MT5 v3.10 移植穿越 70/30 alert） | 未修 | 中 |
| P2 | **B7**：cached 重畫時 cache 埋 slope t 值，令面板箭咀兩 bar 之間唔好閃 `-` | 未修 | 極細 |
| P3 | 降低 A4 CPU 負載（如只用尾段 bar 計 slope，唔全量重算 300 支） | 未修 | 中 |
| P3 | 考慮黃金交叉盤半權重（A2）係咪要改做全權重 | 設計決定，待確認 | 細 |

---

## 10. 附錄：Instrument 清單（36）

**28 主要貨幣對**（p=0..27）：

| # | Pair | # | Pair | # | Pair | # | Pair |
|---|---|---|---|---|---|---|---|
| 0 | EURUSD | 7 | EURGBP | 14 | GBPJPY | 21 | AUDNZD |
| 1 | GBPUSD | 8 | EURJPY | 15 | GBPCHF | 22 | NZDJPY |
| 2 | AUDUSD | 9 | EURCHF | 16 | GBPAUD | 23 | NZDCHF |
| 3 | NZDUSD | 10 | EURAUD | 17 | GBPCAD | 24 | NZDCAD |
| 4 | USDJPY | 11 | EURCAD | 18 | GBPNZD | 25 | CADJPY |
| 5 | USDCHF | 12 | EURNZD | 19 | AUDJPY | 26 | CADCHF |
| 6 | USDCAD | 13 | — | 20 | AUDCHF | 27 | CHFJPY |

**黃金**（p=28..35）：

| # | Instrument |
|---|---|
| 28 | XAUUSD |
| 29–35 | XAUEUR, XAUGBP, XAUAUD, XAUJPY, XAUCHF, XAUCAD, XAUNZD（7 交叉盤） |

> 註：若 broker 無 XAU 交叉盤（29–35），XAU 線只靠 XAUUSD，gn 會細咗但唔會 crash——設計有容錯。

---

## 11. 版本歷史

| 版本 | 日期 | 變更 |
|---|---|---|
| v3.00 | 2026-09-26 | MT5 clean rewrite（9 線 + diff + tickbox + ranking panel） |
| v3.06 | 2026-09-26 | MT4 移植基礎版本 |
| v3.07 | 2026-09-26 | MT4 移植完成（TOP PAIRS + expand block） |
| v3.09 | 2026-09-26 | MT5 上一版（TOP PAIRS / expand 缺失、`ChartSetSymbolPeriod`、`Alert_On` 死參數、Diff `DRAW_HISTOGRAM`） |
| **v3.10** | **2026-10-19** | **B1–B4 全數修復**：TOP PAIRS ＋ expand（MT4 移植）、`ChartWindowFind("CP v3")` 短名、cached `OnTimer`（移除 `ChartSetSymbolPeriod`）、Diff 改 `DRAW_NONE`、實作 `Alert_On`、scoped `OnDeinit`。**編譯 0 errors 0 warnings**（ex5 md5 `70008ad26b22859167e48028b07f7cc4`） |

---

*本白皮書由源碼逐行核對生成；所有缺陷／修復均有代碼位置佐證。審核如有疑問，歡迎要求補充證據。*
