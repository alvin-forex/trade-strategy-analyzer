# ASSUMPTIONS — 波幅指標重建（A1）

本檔記錄**已證實**與**仍未證實**嘅算法語義。凡未證實者一律列明，唔會當成事實。

來源限制：原廠手冊只有參數名、預設值同面板欄位，**完全無**算法定義（經客服 AI 逐條確認，B/C/D/E 組全部「手冊沒有記載」）。因此所有語義只能靠三類硬證據反推：
（a）MT4 隨附 `ZigZag.mq4` 源碼、（b）MT4 原生 ZigZag 輸出、（c）原廠面板真實數字截圖。

---

## ✅ 已證實（有硬證據）

### 1. ZigZag 三參數語義 — 來自 MetaQuotes `ZigZag.mq4` 源碼

參考副本：`evidence/a1/mt4_zigzag_reference.mq4`（MT4 build 1492 隨附）

| 參數 | 真正語義 | 證據 |
|---|---|---|
| `Depth = 12` | 窗口大小，掃 shift `i .. i+11`。**向未來方向** | 源碼 `iLowest(NULL,0,MODE_LOW,InpDepth,i)` |
| `Deviation = 5` | **points**，永遠以 `InpDeviation * Point` 使用 | 源碼 `low[i]-extremum > InpDeviation*Point` |
| `Backstep = 3` | 確認新極值時**向前清除 3 支已標記極值**。**唔係**最小間距 | 源碼 `for(back=1; back<=InpBackstep; back++){ pos=i+back; ...=0 }` |

推論：Depth 向未來掃 → 最新 `Depth-1` 支永遠唔會確認 pivot，最舊 `Depth-1` 支唔會被掃。呢個就係「Total bars 少過窗口 bars」嘅來源。

### 2. Python 移植 = MT4 原生輸出（逐 pivot 對齊）

MT4 原生 `ZigZag(12,5,3)` 全歷史 2049 支 H1 匯出 **122** 個 pivot；
Python 移植同一輸入 → **122** 個 pivot。

```
common timestamps = 121
value mismatches  = 0
mt4_only = 1  (匯出時仍在形成嘅最新一支)
py_only  = 1  (同一支，時間標籤差一個 bar)
```

除咗正在形成嘅最後一支，**價格零差異、時間完全一致**。
證據檔：`evidence/a1/mt4_zigzag_dump.csv`

### 3. Merge 基準 = `drop_next` 讀法（用真面板數字反推）

原廠面板（Alpari demo，EURUSD H1，Date Range `2026.09.17 02:00 → 11.16 17:00`）實測：

| 類別 | 面板 n | 面板 bars | 面板 pips | 面板 avgB | 面板 longest | 面板 shortest |
|---|---|---|---|---|---|---|
| Normal | 39 | 630 | 2283.6 | 16.2 | 48 | 3 |
| Medium | 7 | **211** | **831.1** | **30.1** | **56** | **11** |
| Crazy | 3 | 162 | 553.0 | 54.0 | 99 | 29 |
| **合計** | **49** | **1003** | **3667.7** | | | |

由 Total ÷ Average 反推段數：`2283.6/58.6=39`、`831.1/118.7=7`、`553.0/184.3=3` → **49**。

**`drop_next` 讀法（刪除「結束淺回調嘅 pivot」，迭代至收斂）** 一跑即中：

| 指標 | 面板 | drop_next 35% | |
|---|---|---|---|
| 總段數 | 49 | **49** | ✅ |
| 三檔段數 | 39/7/3 | **39/7/3** | ✅ |
| Normal longest | 48 | **48** | ✅ |
| Normal avgB | 16.2 | 15.7 | ~ |
| Normal bars | 630 | 611 | −19 |
| **Medium 全部六項** | 211/831.1/30.1/56/11 | **211/831.1/30.1/56/11** | ✅ **六項全中** |
| Crazy bars | 162 | 185 | +23 |
| Crazy longest | 99 | 103 | +4 |
| 幅度上限 | 249.7 | 253.9 | +4.2 |

**Medium 類六個指標全部精確命中**（連小數位都一樣），證明切分同分檔邏輯正確。

之前試過 `pre`（相對前段、單次掃）同 `post`（相對前段、合併後迭代）——兩者最多只到 55 段，**永遠對唔到 49**。

### 4. Backstep ≠ 最小間距（雙重反證）

- 源碼直接證明（見上表）
- 手冊例子 Normal 檔 **Shortest = 2 bars**：若 Backstep 係「最少相隔 3 支」，最短波段唔可能 2 支

### 5. 分檔取整 = round-half-up

| 規則 | 手冊 53 段 | 面板 49 段 |
|---|---|---|
| `floor(0.8N)/floor(0.15N)/餘數` | 42/**7**/4 ❌ | 39/7/3 ✅ |
| `round(0.8N)/round(0.15N)/餘數` | 42/**8**/3 ✅ | 39/7/3 ✅ |

兩組同時符合者只有 round-half-up。已寫入 `buckets.py::split_counts`。

### 6. 波段數 = pivot 數 − 1

原始 ZigZag chain N 個 pivot → N−1 段。窗口 1023 支 → 60 pivot → 59 段（未 merge）；merge 後 50 pivot → **49 段**。

### 7. 幅度 = 兩 pivot 之間嘅價差（pivot delta），唔係段內 high-low range

面板 Crazy 最長段 249.7 pips 對應 `2026-11-10T10:00 H → 2026-11-16T13:00 L`，即兩極點價差。若改用段內 range，數值會偏離（同段 range 版本算出 248.2，亦接近但不是最優）。用 pivot delta 時 Medium 六項全中，故採用。

### 8. 時間基準（MT5 Python API）

- bar epoch 用 `datetime.fromtimestamp(t, UTC)` 解 → 出嘅標籤 = MT5 圖表見到嘅 server time
- ⚠️ `copy_rates_range` 收 **naive** datetime 會當**本機時間**（HKT, UTC+8）解釋，靜靜雞偏 −8h。實作一律傳 tz-aware
- `server_utc_offset` 自動量度（Alpari 現時 **+2**）

### 9. 券商標識要讀 account_info().company

`terminal_info().company` 係平台供應商（"MetaQuotes Ltd."），唔係券商；正確來源係 `account_info().company`（"Alpari"）。用錯會令所有券商喺溯源欄位睇落一樣。

---

## ⚠️ 仍未完全對齊（數字差異，非算法錯誤）

三檔合計同面板差 4 支（1007 vs 1003），差異集中喺兩個位：

1. **Normal −19 bars / Crazy +23 bars**：即一至兩段被歸入相鄰檔。邊界值我算出 101.2 / 128.5，面板印 110 / 129。第二個邊界幾乎一樣（128.5 vs 129），第一個差 8.8 pips —— 意味住 Normal/Medium 邊界附近有一段（約 103 pips）本應屬 Medium 但被我歸入 Normal。
2. **Crazy 最長段 103 bars vs 面板 99**：我嘅尾段由 `2026-11-10T10:00` 伸到 `2026-11-16T17:00`（窗口尾），面板停喺 `11-16T13:00`。即面板嘅最後一段喺 13:00 已完結，而我嘅仲延伸 4 支。可能係面板「分析期間」用「最後已成完 pivot」而唔係「窗口最後一支」，亦可能係最後一支未完成 K 線處理唔同。

**已定位到具體嗰一個分歧點**（最有價值嘅線索）：

面板 Crazy 最短段 = 29 bars / 165.7 pips，對應 `2026-09-30T15:00 H(1.13805) → 2026-10-01T20:00 L(1.12148)`。
我嘅規則砍咗佢，因為：

```
到達段        |1.13805 − 1.12148| = 165.7 pips
隨後回調高點  1.12697（2026-10-02T11:00）
回調幅度      |1.12697 − 1.12148| = 54.9 pips
54.9 / 165.7 = 33.1%  <  35%   → 被 merge
```

即係**面板門檻實際低於 33.1%**（保留咗呢個 pivot）。但若把 merge_pct 降到 33%，段數會升到 >49，
同 49 段矛盾。所以剩餘差異唔係單純「門檻數值」，而係另一條未明規則
（可能係「深回調後嘅 pivot 有豁免」或「合併後重算 arrival 段」）。

已試過但**唔成功**嘅變體：視窗首尾各掃 ±40 支、`incl`/`excl` bar 模式、merge 分數 30–45%、
amp 用段內 range、minimum bar spacing 1–8、symmetric fractal window、`pre`/`post`/`drop_next` 三種刪除位置。
全部無法同時修正 Normal/Crazy。

**結論：核心算法（ZigZag + merge drop_next + round-half-up 分檔）已確定，Medium 類六項全中；殘差係邊界/尾段處理，唔會為湊數改算法。**

---

## ❌ 仍未證實（已寫入實作但標記 provisional）

### U1. 面板「Range」欄語義

面板印 `Normal 12-110 / Medium 110-129 / Crazy 129-250`（三檔首尾相連）。我算出 `16.9-101.2 / 110.8-128.5 / 137.6-253.9`。第二個邊界吻合（128.5≈129），第一個差 8.8。可能係「該檔 min-max」或「分界點」或「含相鄰檔重疊」。AC 已明示**不可作驗收標準**。`buckets.py` 只輸出 min/max，唔宣稱語義。

### U2. Longest / Shortest 定義

面板有 bars 同 pips 各一組。我用 max/min。Normal longest=48 命中、Medium 56/11 命中，但 Normal shortest 我 2 面板 3、Crazy 最長我 103 面板 99。

### U3. 最後一段（未完成）處理

面板 Crazy 最長段 99 bars 而我 103 bars，差 4 支正好係 `11-16T13:00 → 17:00`。未確定原廠係咪只計「已成完 pivot」。

### U4. 最小幅度 12.0 pips

面板 Normal 最短幅度 12.0，我 16.9。可能原廠允許更細嘅 pivot（Deviation 語義有別），亦可能係邊界效應。

---

## 未能取得嘅東西

**原廠面板數字只能靠人手截圖。** Martingale Scanner v1.00 係 GEMS 版權保護（`LoadLibraryW`），即使勾選 Allow DLL imports、載入成功並通過線上認證，其面板文字以 chart-global object 形式存在，而 MT4 `ObjectsTotal(-1)` / `ObjectName(o,-1)` 對呢批 object 讀到 0（`win_0_objects=0` 但 `objects_all=434`）。`iCustom` 取 buffer 全部 0（面板係 object 繪製，唔係 buffer）。`ChartIndicatorsTotal(0,0)` 只顯示 GEMS 包裝名 `ff_mt_309718014`。

---

## 結論

| 項目 | 狀態 |
|---|---|
| ZigZag 移植 | ✅ 與 MT4 原生逐點一致（122/122，價格零差異） |
| Deviation 單位 | ✅ points（源碼證實） |
| Backstep 語義 | ✅ 清除回看支數（源碼 + 面板 shortest 反證） |
| Merge 基準 | ✅ `drop_next`（面板 49 段 + Medium 六項全中） |
| 分檔取整 | ✅ round-half-up（兩組 ground truth 同時符合） |
| 幅度定義 | ✅ pivot delta |
| 總段數 | ✅ 49 = 面板 49 |
| 三檔段數 | ✅ 39/7/3 = 面板 39/7/3 |
| Medium 類全六項 | ✅ 精確命中 |
| Normal / Crazy bars | ⚠️ 差 4 支（邊界/尾段處理） |
| 面板「Range」語義 | ❌ 未證實 |
