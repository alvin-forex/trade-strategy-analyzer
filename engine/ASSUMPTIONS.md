# ASSUMPTIONS — 波幅指標重建（A1）

本檔記錄**已證實**與**未證實**嘅算法語義。凡未證實者一律列明，唔會當成事實寫入實作。

來源限制：原廠手冊只有參數名、預設值同面板欄位，**完全無**算法定義（經客服 AI 逐條確認，B/C/D/E 組全部「手冊沒有記載」）。因此所有語義只能靠 (a) MT4 隨機附帶嘅 `ZigZag.mq4` 源碼、(b) 兩組 ground truth 數字反推。

---

## ✅ 已證實（有硬證據）

### 1. ZigZag 三參數語義 — 來自 MetaQuotes `ZigZag.mq4` 源碼

參考副本：`engine/evidence/a1/mt4_zigzag_reference.mq4`（MT4 build 1492 隨附）

| 參數 | 真正語義 | 證據 |
|---|---|---|
| `Depth = 12` | 窗口大小，掃 `shift i .. i+11`。**向前（未來）方向**，唔係向後 | 源碼 `iLowest(NULL,0,MODE_LOW,InpDepth,i)` |
| `Deviation = 5` | **points**，永遠以 `InpDeviation * Point` 使用 | 源碼 `low[i]-extremum > InpDeviation*Point` |
| `Backstep = 3` | 確認新極值時，**向前清除 3 支已標記極值**。**唔係**最小間距 | 源碼 `for(back=1; back<=InpBackstep; back++){ pos=i+back; ...=0 }` |

推論（重要）：因為 Depth 向前掃，**最新 `Depth-1` 支永遠唔會確認 pivot**，最舊 `Depth-1` 支唔會被掃。呢個就係「窗口 bars 少過實際 bars」嘅來源。

### 2. Python 移植 = MT4 原生輸出（逐 pivot 對齊）

用 MT4 原生 `ZigZag(12,5,3)` 全歷史 2049 支 H1 匯出 122 個 pivot；
Python 移植同一輸入 → 122 個 pivot。

```
common timestamps = 121
value mismatches  = 0
mt4_only = 1  (2026-11-17T19:00 — 匯出時仍在形成嘅最新一支)
py_only  = 1  (2026-11-17T18:00 — 同一支，時間標籤差一個 bar)
```

除咗正在形成嘅最後一支，**價格完全一致、時間完全一致**。移植可信。
證據檔：`engine/evidence/a1/mt4_zigzag_dump.csv`

### 3. Backstep ≠ 最小間距（用 ground truth 反證）

手冊例子 Normal 檔 **Shortest = 2 bars**。若 Backstep 係「兩極點最少相隔 3 支」，最短波段唔可能只有 2 支。→ 推翻「最小間距」假說。（此點同時被源碼證實）

### 4. 分檔取整 = round-half-up

| 規則 | 手冊 53 段 | AC 49 段 | 判定 |
|---|---|---|---|
| `floor(0.8N)/floor(0.15N)/餘數` | 42 / **7** / 4 ❌ | 39 / 7 / 3 ✅ | 排除 |
| `round(0.8N)/round(0.15N)/餘數` | 42 / **8** / 3 ✅ | 39 / 7 / 3 ✅ | **採用** |

只有 round-half-up 同時符合兩組。已寫入 `engine/buckets.py::split_counts`。

### 5. 波段數 = pivot 數 − 1

原始 ZigZag chain 有 N 個 pivot → N−1 段。窗口 1023 支 → 60 pivot → 59 段（未 merge）。
手冊例子 1024 支 → 62 pivot → 61 段（未 merge，目標 53）。

### 6. 窗口裁切量級正確

| | 窗口 bars | 首尾 pivot span | 差 |
|---|---|---|---|
| 手冊例子 | 1024 | 1010 | 14 |
| AC 窗口 | 1023 | 1007 | 16 |
| 目標 | 1024 | 1009 | 15 |
| 目標 | 1023 | 1003 | 20 |

同一量級（~1.5%），同「Depth 向前 look-ahead 食掉首尾」一致。

### 7. MT4 ZigZag 唔受 Deviation 影響（實測）

dev 由 1 points 掃到 2000 points，pivot 數**完全不變**（122）。因為 buffer 只會在 `bar[i]` 本身就係窗口極值時才寫入，Deviation 只係過濾「當前 bar 離極值幾遠」，而 H1 歐元嘅波動令此條件幾乎恆真。**唔係 bug**——Python 移植同樣行為，且與 MT4 逐點對齊。

---

## ❌ 未證實（已寫入實作但標記為 provisional）

### U1. Merge Percentage 嘅比較基準 — **核心未解**

手冊只有一句：「一個走勢回調多少才算是結束」，預設 35%。**冇講**：
- 35% 相對咩（前段波幅？價位？ATR？）
- 合併前定合併後嘅基準
- 掃一次定迭代至收斂
- 統計用邊份清單

已測試 ≥10 種讀法，**冇一種能同時命中 AC 六個目標數字**：

| 讀法 | 49段? | 三檔 | Total bars | 評估 |
|---|---|---|---|---|
| prev / 35% | ✗ 55 | 44/8/3 | 658/254/95 | 目標基準值 |
| prev / 42% | ✅ 49 | ✅ 39/7/3 | 616/241/150 | 段數同三檔全中，bars 差 |
| both / 41% | ✅ 49 | ✅ 39/7/3 | 618/241/148 | 同上 |
| prev / 41% + 丟首段 | ✅ 49 | ✅ 39/7/3 | **631**/206/148 | 第一檔 exactly 中 |
| post（迭代） 35% | ✗ 55 | 44/8/3 | 658/254/95 | |

**現時實作預設**：`base_mode="post"`（相對前一段波幅、合併後迭代至收斂），`merge_pct=35`。
理由見 `engine/merge.py` 模組 docstring（尺度不變 + 避免雙重標準）。
**但呢個組合出 55 段，唔係 49 段。**

### U2. 為何 49 段對唔到 — 三個未排除的可能

1. **券商數據唔同**：AC 原截圖券商未確認（AC 講「EURCHF 那張是 Alpari」）。本機 Alpari-Pro.ECN-Demo 對原截圖可能係另一間 → 「跨券商總段數 ±2」容差內，但 bars 差異會更大。
2. **Merge 讀法完全唔同**：例如「回調 < 35% 就唔算新波段」可能係以 **bar 數**或**時間**度量，唔係價幅。
3. **統計清單唔同**：可能只統計「已完成」波段（排除最後一段），或排除首段未成形者。

### U3. 面板「Range」欄語義

手冊例子 17-73 / 73-119 / 119-166（三檔首尾相連）。可能係「該檔 min-max」或「分界點」或「含相鄰檔」。AC 已明示**不可作驗收標準**。`engine/buckets.py` 只輸出 min/max，唔宣稱語義。

### U4. Longest / Shortest 定義

手冊有欄位（bars 同 pips 各一組），但未確認係邊個波段。`engine/buckets.py` 用 max/min。

### U5. 時間基準

MT5 Python API 實測：bar epoch 用 `datetime.fromtimestamp(t, UTC)` 解 → 出嘅時間標籤 = 你喺 MT5 圖表見到嘅 server time。已寫入 `engine/sources/mt5_source.py`，並自動量度 `server_utc_offset`（Alpari 現時 +2）。

⚠️ **naive datetime 陷阱**：`copy_rates_range` 收 naive datetime 會當**本機時間**（HKT, UTC+8）解釋，靜靜雞偏 −8h。實作一律傳 tz-aware。

---

## 未有機會驗證

**原廠指標 panel 數字未取得。** Martingale Scanner v1.00 係 GEMS 版權保護（需 `LoadLibraryW`），
即使勾選 Allow DLL imports 後載入成功並通過線上認證，其面板文字以 chart-global
object 形式存在，而 MT4 嘅 `ObjectsTotal(-1)` / `ObjectName(o,-1)` 對呢批 object
讀到 0（`win_0_objects=0` 但 `objects_all=434`）。

人手截圖可補此缺口（面板 Scan Summary 有 Longest/Shortest，係對錯誤極敏感嘅極值）。

---

## 結論

| 項目 | 狀態 |
|---|---|
| ZigZag 移植 | ✅ 與 MT4 原生逐點一致 |
| 分檔取整 | ✅ round-half-up，兩組 ground truth 同時符合 |
| 波段數 = pivot−1 | ✅ |
| 裁切量級 | ✅ |
| **Merge 基準** | ❌ 未解，≥10 種讀法全部對唔到 49 段 |
| 面板數字 | ❌ 受 GEMS DLL 保護，未取得 |

**A1 交付嘅係一個語義可切換、可重跑、與 MT4 ZigZag 逐點對齊嘅引擎；
49 段 parity 未達成，且唔會為湊數字改算法。**
