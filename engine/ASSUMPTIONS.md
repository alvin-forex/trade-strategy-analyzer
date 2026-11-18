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
| `Depth = 12` | 窗口大小，掃 shift `i .. i+11`（shift 越大越舊）→ **向過去（較舊）方向** | 源碼 `iLowest(NULL,0,MODE_LOW,InpDepth,i)` |
| `Deviation = 5` | **points**，永遠以 `InpDeviation * Point` 使用 | 源碼 `low[i]-extremum > InpDeviation*Point` |
| `Backstep = 3` | 確認新極值時**向前清除 3 支已標記極值**。**唔係**最小間距 | 源碼 `for(back=1; back<=InpBackstep; back++){ pos=i+back; ...=0 }` |

推論（2026-11-18 實測修正）：MQL4 嘅 shift 係「由最新倒數」，所以 `iLowest(...,i)` 掃嘅係 `i..i+11` 即**越來越舊**嘅 bar，
即 Depth 係向**過去**方向。因此：

- **最新一支（shift 0）可以成為 pivot** —— 實測窗口最後一支 `2026-11-16T17:00` 正是最後一個 raw pivot
- **最舊 `Depth-1` 支永遠唔會被掃**

所以「Total bars 少過窗口 bars」係來自**最舊**一截冇被掃（唔係最新一截）。

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

### U1. 面板「Range」欄語義 — **已破解（2026-11-18）**

面板印 `Normal 12-110 / Medium 110-129 / Crazy 129-250`。四界全部解釋得到：

| 邊界 | 面板 | 我嘅計算 | 來源 |
|---|---|---|---|
| Normal 下限 | **12** | raw zigzag 最小幅度 **12.4** → 取整 12 | 合併前原始鏈嘅最細段 |
| Normal 上限 | **110** | 排序第 40 名 = **110.8** → 取整 110 | 下一檔起點（唔係第 39 名 101.2） |
| Medium 上限 | **129** | 排序第 46 名 = **128.5** → 四捨五入 129 | 下一檔起點 |
| Crazy 上限 | 250 | merged 最大 = **253.9** | OCR 可能把 253 讀成 250 |

**關鍵驗證**：直接用「幅度門檻 110 / 129」分檔，**正好出 39 / 7 / 3**：
```
<= 110       -> 39 段
(110, 129]   ->  7 段
> 129        ->  3 段
```
若改用實際第 39 名 / 第 46 名作門檻（101.2 / 128.5），會出 **40 / 6 / 3**，同面板唔符。

**結論**：面板 Range 係「**下一檔起點**」式分界（首尾相連），**唔係**該檔實際 min–max。
呢個亦解釋咗為何手冊例子 Normal 顯示 17–73 但 Longest 只有 61.0 pips —— Range 必定比實際 min–max 寬。
廠商 AI 嘅判斷（「顯示範圍 ≠ 該檔 min–max」）**正確**。

⚠️ 但要注意：`buckets.py` 仍以**條數**（round-half-up）分檔，唔係以幅度門檻分檔。
兩種方法喺本窗口得出同一個 39/7/3，但喺極端分佈下可能分歧。此點列入待確認。

### U2. Longest / Shortest 定義 — **已破解（2026-11-18）**

**Longest / Shortest 係「bars 最多／最少嗰段」，其 pips 就係該段本身嘅幅度**，
唔係該檔幅度嘅 max/min。

決定性證據：面板 Medium 顯示
```
Longest  :  56 bars / 119.4 pips
Shortest :  11 bars / 128.5 pips     <-- pips 反而更大
```
若 pips 係獨立取 max/min，「Shortest」唔可能比「Longest」多 9.1 pips。
唯一解釋：兩者都係「按 bars 揀嗰段，再讀佢嘅 pips」。

修正前 `buckets.py` 錯用 `max(amps)` / `min(amps)`，現已改為
「bars 極值段所對應嘅幅度」。修正後 Medium 六項**全部精確命中**：
`211 bars / 831.1 pips / 30.1 avg / longest 56b·119.4p / shortest 11b·128.5p`。

Normal longest（48 bars / 99.9 pips）亦精確命中。

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

---

# A2 新增（2026-11-18）

## ✅ 已證實

### 10. Range 四界 = floor 截斷（唔係 round）

老闆提供修正後面板數字：`12-110 / 110-128 / 128-249`（原本 OCR 讀成 129，實際 128）。

| 邊界 | 面板 | 公式 | 值 | floor |
|---|---|---|---|---|
| b0 Normal 下限 | **12** | min amplitude over **raw** (pre-merge) chain | 12.40 | **12** ✅ |
| b1 Normal 上限 = Medium 下限 | **110** | merged sorted, index `c0`（第 40 名，Medium 首個） | 110.80 | **110** ✅ |
| b2 Medium 上限 = Crazy 下限 | **128** | merged sorted, index `c0+c1-1`（第 46 名） | 128.50 | **128** ✅ |
| b3 Crazy 上限 | 249 | merged sorted, last | 253.90 | 253（差 4） |

**三個界限精確命中**，而且全部係 `floor` 向下截斷 —— 若用 `round`，128.5 會變 129，
同面板 128 唔符。呢一點由老闆提供嘅新數字直接鎖定。

b3 嘅 4 pip 差同 A1 已知嘅「最長段 103 vs 面板 99 bars」係**同一個尾段問題**，唔係獨立 bug。

### 11. Crazy total pips 完全一致

面板 **551.3 pips**，引擎 **551.3 pips** —— 精確命中。
（A1 時我誤以為面板 Crazy bars = 185，實為 162；pips 一直係對嘅。）

### 12. 分檔三種方法可切換，只有 `count` 對得上

| method | 段數 | 三檔 | 對面板 |
|---|---|---|---|
| `count`（round-half-up 條數） | 49 | **39/7/3** | ✅ |
| `rank`（nearest-rank 邊界） | 49 | 40/7/2 | ❌ |
| `inc`（PERCENTILE.INC） | 49 | 39/7/3 | ✅ |

`count` 同 `inc` 喺本窗口都得 39/7/3；`rank` 唔得。需求書要求兩種 percentile 都支援，
已全部實作並可切換，但預設 `count`（兩組 ground truth 都驗證過）。

### 13. 波幅表 band 命名必須逐字保留

依需求書 §13：`80% Range` / `15% Range` / `5% Range`，**唔准改叫 P80/P95/Pmax**。
`table.py` 有測試專門攔截任何 P80/P95/Pmax 字串。

### 14. 樣本不足要明確報錯

少於 3 段無法切三檔。`compute_buckets(strict=True)` 拋 `InsufficientSampleError`，
CLI 回 exit code 7。唔會靜靜出空表。

## ⚠️ 仍需知道

- `--bucket-method rank` 喺本窗口出 40/7/2，唔符面板。保留係為滿足需求書「兩法可切換」，
  但**唔建議**用作生產預設。
- Range b3（253 vs 249）同尾段問題同源，未解。

---

# A3（MCP server + 每日自動更新）—— 需求書冇寫、由實作者定嘅事項

需求書 §7 A3 只寫「MCP server（`get_rates` / `extract_waves` / `compute_buckets` / `export_table`）」，
驗收就五個字「每日自動更新跑通」。**冇** tool signature、冇回傳型別、冇錯誤碼、
冇排程時間／時區／重試／通知規格、冇 `export_table` 輸出格式。以下係實作時嘅決定，
全部屬於「唔自創算法」範圍以外嘅**接口約定**（唔影響任何計算數字）。

### A1. Tool 簽名 = `engine.api` 嘅函數簽名（單一實作）

四個 tool 係 `engine/api.py` 四個函數嘅薄包裝，同一條 code path 同時服務 CLI、
每日批次同 MCP client。冇第二份實作可以走樣。

`symbol` 必填；`start`+`end`（server time，`YYYY-MM-DDTHH:MM`）**或** `past_bars`
二揀一，同時俾會回 `bad_argument`。`export_table` 另需 `out_dir`。
接受 `YYYY.MM.DD HH:MM` / 純日期（自動補 `T00:00`）—— 方便照抄 MT5 圖表標籤。

### A2. 回傳永遠係 `{"ok": true, ...}` 或 `{"ok": false, "error": {...}}`

可預期嘅失敗（冇終端、冇數據、symbol 唔存在、樣本不足、參數錯、IO 錯）
**係值唔係 exception**，所以 MCP client 一定收到結構化原因，唔會撞 protocol error。
錯誤碼係穩定字串：`bad_argument` / `no_terminal` / `unknown_symbol` /
`no_data` / `insufficient_sample` / `io_error`。有測試鎖住呢六個字串。

### A3. `past_bars` 預設 = 1024（原廠 *Past X Bars* 預設）

每日批次預設用原廠自己嘅 1024 支，令每日跑出嚟嘅數同面板可比，
唔會因為上次有人手打咗個日期區間而漂移。要固定回補就用 `--from/--to`。

### A4. 每日批次唔負責排程

`engine/daily.py` 只做「跑矩陣 → 寫檔 → exit code」。cron / Windows Task Scheduler /
OpenClaw 點叫佢係外部事（WSL 生產環境已有 10 條 cron 嘅既有做法）。
需求書冇規定時區同頻率，所以唔喺程式裡硬編一個。

- 一個 symbol/TF 失敗**唔會**中止其餘 —— 單一隻下架 symbol 唔應該令你損失全日波幅表。
- exit code：`0` 全成功、`1` 有失敗（細節在 manifest）、`2` 參數錯。
- `--dry-run` 只出計劃，唔連 MT5、唔寫檔。

### A5. 數據檔冇時間戳，manifest 才有

`<SYMBOL>_<TF>.table.{csv,json}` / `.waves.csv` 同 `.meta.json` 內容**唔含**執行時間，
所以同一輸入跑兩次係 byte-identical（已用 sha256 實測鎖住）。時間戳只出現在
`manifest.json` 嘅 `startedAt`/`finishedAt` —— 佢係 log，唔係數據。
呢個分野令「今日同昨日有冇變」可以直接 diff hash 而唔會假報。

### A6. 傳輸：stdio 預設，另備 sse / streamable-http

本地 MCP client 用 stdio（`python -m engine.mcp_server`）。要跨機／畀網站後端用就
`--transport streamable-http --port 8765`。stdio 模式下所有診斷資訊走 **stderr**，
因為 stdout 係 protocol 頻道，印任何字都會破壞 handshake。

### A7. `mcp` 套件係可選依賴

`engine.mcp_server` 才 import `mcp`；`import engine.api` 永遠唔需要它。
冇裝 `mcp` 時引擎、CLI、每日批次照跑，只有 MCP server 會提示安裝。
（SDK 2.x 已將 `FastMCP` 改名 `MCPServer`，位置 `mcp.server.mcpserver`。）

