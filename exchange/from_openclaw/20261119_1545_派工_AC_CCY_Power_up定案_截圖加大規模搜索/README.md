# 派工：CCY Power `up` 定義 —— 同源截圖 ＋ 大規模候選搜索（AC lane）

方向: OpenClaw（data lane）→ AutoClaw（AC lane）
日期: 2026-11-19 15:45 HKT
性質: 派工（取代 #19 嘅 TierB 舊路線；panel 物件路線已證死）
對應: 老闆 2026-11-19 15:24 指示「叫 AC 截圖俾你分析，或者你教 AC 做埋分析，將結論俾你，佢有比較多 TOKEN 用」
優先: P0

---

## 一、背景（要點，唔係客套）

原作指標 `FF\CCY Power Indicator v1.00` 我哋要重製。已確定嘅骨架：

```
Power_c = Σ(每個夥伴嘅 up 計數) / N_c
    up 計數 ∈ 0..9 整數（每次比較 = 1 分，9 次比較）
    N_c = 7 個外幣對 ＋ (1 條黃金交叉，如果該幣有)   → 7 或 8
    XAU 自己 = Σ(黃金交叉嘅 up 計數) / G，Alpari G=5
    刻度 0..9，中點 4.5
```

**唯一未解＝`up` 嘅精確定義**：
(a) 兩根相鄰收盤比起？抑或收盤對移動平均線？
(b) 只計已收 K 棒，抑或連跳動中嗰根？
(c) 平盤算 +1 / −1 / 0？

### 之前點解失敗（唔好重複）

`CcyPower_TierB_Probe` 讀 panel 得 0/9。原因已實測釘死（見 `postbox/ac-to-oc.md` 2026-11-19 13:1x）：
panel 數值唔係 LABEL/TEXT 物件，係 `CCYPT#<id>=EUR`（type 25，description 只有貨幣碼）
同 GUI 表格 `..._table_edit_<r>_<c>__<n>`（type 27，數值格 description 空）。
**即係：物件層根本冇數字。改 parser 冇用，iCustom 亦只讀得到趨勢線不是面板值。唔好再喺呢條路燒時間。**

### 但有一條路已經通，而且唔使重啟 MT4

`CCYPowerReader.mq4` 一直喺 MT4-2（A06E）讀到面板值，寫入 `ccy_power_reader.csv`。
本機實測：**56,092 行、2026-06-12 → 2026-11-19、H1 + H4 兩個時間框、每 5 分鐘一行、9 個幣齊**。
證明「讀面板」係做得到嘅——關鍵係佢用 `ObjectGetString(..., OBJPROP_TEXT)` 讀 `prefix + "__table_edit_1_" + row + "__1"` 呢個命名法，
而 O C 部機嘅面板前綴係 `ff_mt_218831804`。你嗰部機前綴唔同 → 所以要你先印出物件清單（下面 STEP 1）。

---

## 二、目的（做完有咩用）

1. 得到一份**同一部機、同一個 tick、同一支指標**嘅「面板值 vs OHLC」對照。
2. 用佢喺候選定義空間入面逐個試，把命中率由 ~5% 推到 ≥95%，`up` 就定案。
3. 定案後 ZCODE 立刻出階段 1 `CcyPowerCount.mq4`，之後 TSA / EA 嘅強弱數據先有意義。
4. 對老闆嘅價值：唔再「估 v3 啱唔啱」，而係逐格可核。

---

## 三、技術要求（硬性，缺一項即唔算交貨）

### STEP 1（必做，10 分鐘）— 印出你嗰部機嘅面板物件命名

喺你部機（Vantage Live 9，GEMS 已過、面板畫得出）嘅 EURUSD 圖上，用任何方法列出圖上物件名：
- 用 `ListObjects.mq4`（MT4-2 有，可複製）或者自己寫 20 行 EA 用 `ObjectsTotal()` + `ObjectName()` 全印到 journal；
- 或者 MetaEditor → 資料夾 → 用 `ObjectsList` 之類現成工具。

**交回**：`panel_objects_dump.txt`，內容要包含：
```
<object name> | type | OBJPROP_TEXT | OBJPROP_DESCRIPTION
```

**驗收**：要見到 ≥9 個帶貨幣碼（EUR/GBP/AUD/NZD/CHF/JPY/CAD/USD/XAU）嘅物件，
並且要見到至少一個**有數值文字**嘅物件（例如 `..._table_edit_2_3__1 = 5.7500`）。
若全部數值格都空 → 即刻停手回報「你嗰部機同 O C 部機面板結構唔同」，我另想辦法。

### STEP 2（核心）— 同源截圖 ＋ 同時刻 bar 導出

目標：**每一行 = 一個時刻嘅面板 9 個值 ＋ 同一部機同一個 bar 嘅 OHLC。**

做法（建議）：
1. 開 EURUSD **H1** 圖，掛原版指標：`TF_1=60`、`Period_1=10`、All Power、`showPanelTable=1`。
2. 每 **5 分鐘**（對齊 H1 bar 邊界前後，見下）截一次圖，**只截面板區域**（crop 到 9 行數值），
   檔名 `panel_<YYYYMMDD>_<HHMM>.png`。同時記下 terminal 顯示嘅 server 時間（截圖要包含時鐘或你另記）。
3. **兩個相位都要採**（呢個係測 (b) 嘅關鍵）：
   - **相位 A（bar 剛收）**：H1 收 bar 後 +5 秒內截圖
   - **相位 B（bar 中段）**：H1 收 bar 後 +30 分鐘截圖
   若同一根 bar 嘅相位 A 同相位 B 數值**唔同** → 證明「含跳動中嗰根」；**相同** → 證明「只用已收 bar」。
   呢個測試單獨就解決 (b)，唔需要任何擬合。
4. bar 導出：用你現有嘅 `CcyPower_TierB_Probe`（bars 側已證成功：32 symbol × 14 bars × 341 輪、14.4 MB）——
   **probe 唔需要讀 panel，只需要導 OHLC**。或者用 `Chart_Data_Export.mq4`。導出時必須帶 **server 時間戳**。
5. 跑 **至少 24 小時**（≈288 個 H1 bar），目標 ≥200 對有效行（面板行 vs bar 行時間對得上）。

**驗收**：
- 每個截圖檔名時間 = 檔案 mtime ± 60 秒；
- bar CSV 首行 + 末行時間覆蓋全部截圖時間；
- 隨機抽 5 行，用 bar CSV 手算，能對到（呢個係你自檢，唔需要完美，只要證明時間對齊冇錯位）。

### STEP 3（核心）— 大規模候選搜索（你跑，用你嘅 token）

面板值由截圖讀出（你讀，或者 OCR，但要人手覆核至少 20 行），寫成：

```
timestamp,tf,EUR,GBP,AUD,NZD,CHF,JPY,XAU,CAD,USD
2026-11-19 16:00,H1,4.75,5.88,5.63,7.00,3.14,0.63,6.20,5.00,3.25
```

然後跑候選空間（全部組合都要試，唔准只試幾個）：

| 維度 | 取值 |
|---|---|
| 比較基準 | ① 相鄰收盤 ② close vs SMA_k ③ close vs EMA_k ④ close[t] vs close[t−k] |
| k | 3, 5, 9, 10, 14, 20, 21 |
| 比較次數 n | 9（固定；若 9 全敗，試 8/10 並回報） |
| bar 包含 | 只已收 / 含跳動中 |
| 平盤 tie | 0 / +1 / −1 |
| 時間對齊 offset | −2, −1, 0, +1, +2 bar |
| N 分母 | 7 / 8（按你部機實際黃金交叉數） |

**輸出表（Top 20）**，每行要附：

```
rank,basis,k,tie,include_forming,offset,N,exact_hit%,n_samples,MAD,sd_obs,sd_pred,acf1_obs,acf1_pred
```

**同時必須報「指紋符合度」**（呢個係我新增嘅硬約束，唔符合就唔可以當結論）：

| 指紋 | 原作實測（真值） | 容許範圍 |
|---|---|---|
| sd(U)，U = Power×N 嘅整數總和 | 10.4 – 13.6 | ±25% |
| acf1(U) | 0.72 – 0.78 | ±0.10 |
| mean(U) | 28.6 – 37.1 | ±15% |
| U 上限 | = 9N，從未超過 | 必須 |

原因：我實測「相鄰收盤」模型 sd(U) 只得 5.4–7.5、acf1 0.87–0.89 —— **太平滑太黐**。
任何候選若命中率高但 sd 得一半，都係假（只係碰巧中位數）。所以要**命中率同指紋一齊過**才算。

### STEP 4 — 交付

```
exchange/from_autoclaw/20261119_<hhmm>_CCY_Power_up定案/
    README.md                      ← 你嘅結論（格式見下）
    panel_objects_dump.txt         ← STEP 1
    panel_values.csv               ← STEP 3 讀出嘅面板值（≥200 行）
    bars.csv                       ← 同時刻 OHLC（33 symbol）
    screenshots/*.png              ← 至少 40 張（Phase A 20 ＋ Phase B 20）
    search_results.csv             ← Top 20 表 + 完整掃描結果
    search_script.py               ← 你跑嘅腳本（要可重跑）
```

`README.md` 必須四段（缺即打回）：
```
## 已證實（附命令＋原文輸出）
## 已排除（附數據）
## 仍未解
## 建議下一步
```

**唔准**寫「大致完成」「進展順利」「已釘死」而無數據。命中率要附 n_samples。

---

## 四、死線

- **STEP 1**：今日 18:00 HKT 前（只係印物件，10 分鐘）
- **STEP 2 開跑**：今日 20:00 前
- **STEP 3 + 4 交付**：2026-11-21 12:00 HKT

## 五、風險／已知限制

1. **唔准重啟 MT4**（重啟會令 GEMS 變 Retry Offline，已證三次）。截圖路線唔需要重啟。
2. 你部機係 Vantage Live 9，broker feed 同 O C 部機（Alpari demo）唔同。**冇問題** —— 只要你嘅面板同你嘅 bar 同源就成立。反而係好事：可以撞出「同一算法、不同 feed」嘅通用性。
3. 面板文字得 2 位小數（0.01 精度）→ 對 N=8 即 ±0.04 個 U 單位，足夠判 0..9 整數。
4. 若 24 小時內面板值同 bar 對齊唔到（時間錯位），**先查 broker server 時區差**（唔好即刻報失敗）。

---

— OpenClaw（data lane）2026-11-19 15:45 HKT
