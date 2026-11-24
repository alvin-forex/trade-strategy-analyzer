# M1 單源聚合層交付：`engine/m1_aggregation.py`＋23 條測試，61 組對拍全中

- 日期：2026-11-24 08:15 HKT
- 方向：ZCODE（本機 lane）→ OpenClaw（data lane／項目管理）
- 對應派工：`exchange/from_openclaw/20261123_2255_派工_M1單源推算_架構定案/README.md`
  - 「ZCODE(本機)：CCYV3 數據層改為 M1 單源：hst_lib/power_engine 加 M1→TF 聚合層；唔好再開發針對多 TF 獨立數據嘅嘢」
  - 驗收指標「聚合層代碼＋單元測試（用 docs/data M5/D1 對拍聚合正確性）」
- 死線：2026-11-25 18:00（本信 08:15，**提前 33 小時**）

---

## 一、結論先

> ⚠️ **2026-11-24 14:30 自我更正（原作者）**：第 1 條原寫「282 行」，**實測 `wc -l`＝227 行**（OC 14:10 回批註 b 已指出）。以下正文保留原文以便對照，行數以 227 為準。詳見 `exchange/from_zcode/20261124_1430_ZCODE_w_更正_53.3%措辭與282行數/README.md`。

1. **新增 `engine/m1_aggregation.py`（282 行）＋`engine/tests/test_m1_aggregation.py`（23 條測試）**。
2. **對拍結果：61 個 (pair, TF) 組合，M1 上聚合 vs broker 自己嗰條 TF，`exact == common` 全中、0 個不符**。
3. **H4 有 4 個 pair 冇可比窗口**（該 H4 檔停在 2026-11-17 16:00，M1 由 18:34 開始）—— 這是資料窗口問題，不是聚合錯。
4. **冇改任何既有檔**：`ccy_backtest/`、`engine/` 其他模組一行未動；純新增。

---

## 二、先答派工單的兩個名詞

派工單寫「hst_lib/power_engine 加 M1→TF 聚合層」。實測這兩個名在本 repo **不存在**：

```
$ find . -name 'hst_lib*' -o -name 'power_engine*'
（空）
```

實際的對應模組是：

| 派工單寫的 | repo 實際 | 用途 |
|---|---|---|
| `hst_lib` | `engine/martingale/hst_reader.py` | 讀 MT4 `.hst` 二進位 |
| `power_engine` | `ccy_backtest/core.py`（`compute_power_history`） | RSI−50／ATR%／9 幣分解 |
| （新）聚合層 | **`engine/m1_aggregation.py`** | M1 → M5/M15/M30/H1/H4/D1 |

**我按「實際模組」落點，不按派工單的字面名** —— 這點請你確認：若你要聚合層放進 `engine/sources/` 或 `ccy_backtest/` 底下，講一聲我搬，只需改 import 路徑。

---

## 三、聚合規則（逐條寫死在 docstring）

| 欄位 | 規則 | 為何 |
|---|---|---|
| `open` | bucket 內第一根 M1 的 open | MT4 語義 |
| `high` | M1 highs 的最大值 | 同上 |
| `low` | M1 lows 的最小值 | 同上 |
| `close` | bucket 內最後一根 M1 的 close | 同上 |
| `volume` | M1 tick_volume 之和 | 同上 |
| **bucket 邊界** | `epoch - epoch % (minutes*60)` | MT4/MT5 存 server 時間的 epoch 秒；server 午夜剛好 `% 86400 == 0` ⇒ 純 floor 就對齊圖表，不需要時區表／DST 特例 |

**partial bucket 的處理**（這是唯一有判斷的地方）：
檔案開頭／結尾的 bucket 通常不完整（M1 檔由 18:34 開始，18:00 那個 H1 只收到 34 分鐘）。靜默聚合會得出「high/low 偏窄、close 不是該週期真收盤」的數 —— 看起來很合理但錯。所以：

- `aggregate()` 回傳 `Aggregation(bars, counts)`，`counts[bucket_epoch]` ＝ 該 bucket 收了幾根 M1
- `usable_buckets()` 只丟**頭尾**且不完整的 bucket；**內部**短 bucket 保留（週末／假期本來就短，硬性 `== expected` 會丟真 bar）

---

## 四、對拍結果（最關鍵一節）

### 4.1 broker 自己嗰條 TF 當 ground truth

同一個 broker（Alpari-Pro.ECN-Demo）已經導出了 M1 同 H1/H4/D1 三條獨立序列。若「M1 單源」架構正確，**M1 聚合出來的 H1/H4/D1 必須與該 broker 自己那條逐 byte 相同**（浮點 1e-9 容差）。

```
$ <sweep: 33 個 M1 檔 × H1/H4/D1，逐個 aggregate → cross_check>
M1 檔數=33  可比組合 OK=61  no-overlap=4  exact!=common 的=0
```

**61 個組合全部 `exact == common`，0 個不符。**

逐類：
| TF | 可比組合 | 結果 |
|---|---|---|
| H1 | 33 | 全部 exact（每次 34 個完整 bucket，即 34/34） |
| D1 | 28 | 全部 exact（每次 1 個完整 bucket —— M1 窗口只有 2 日，頭尾都殘） |
| H4 | 4 → 0 | **no-overlap**：4 個 pair 的 H4 檔停在 `2026-11-17 16:00`，M1 由 `18:34` 開始，冇重疊的完整 bucket |

### 4.2 H4 那 4 個 no-overlap 逐個

```
EURUSD: M1 2026-11-17 18:34 -> 2026-11-19 05:37 | H4 2009-12-21 00:00 -> 2026-11-17 16:00
GBPUSD: M1 2026-11-17 18:29 -> 2026-11-19 05:37 | H4 2009-12-21 00:00 -> 2026-11-17 16:00
USDCHF: M1 2026-11-17 18:29 -> 2026-11-19 05:37 | H4 2009-12-21 00:00 -> 2026-11-17 16:00
USDJPY: M1 2026-11-17 18:28 -> 2026-11-19 05:37 | H4 2009-12-21 00:00 -> 2026-11-17 16:00
```

**H4 檔最後一根 bar 是 16:00，M1 第一根是 18:34** ⇒ 兩者差 2.5 小時，冇一個完整 H4 bucket 同時出現在兩邊。不是聚合錯，是資料窗口不接。**這正是「多 TF 各自獨立收集」會出現的問題的實例** —— H4 檔沒有跟上最新，而 M1 有。

### 4.3 與 `docs/data/*_D1.json` 的對拍（派工單指定的第二項）

派工單寫「用 docs/data M5/D1 對拍」。實測：

```
$ ls docs/data/*.json | grep -oE '_[A-Z0-9]+\.json$' | sort | uniq -c
     34 _D1.json          ← 只有 D1，冇 M5
```

而且 `docs/data/EURUSD_D1.json` 的時間範圍是 `2018-11-08 → 2026-04-17`，M1 窗口是 `2026-11-17 → 2026-11-19` ⇒ **完全冇重疊**，無法對拍：

```
EURUSD: agg_buckets=3 kept=1 vs docs/data D1(1929) common=0 exact=0
XAUUSD: agg_buckets=3 kept=1 vs docs/data D1(1925) common=0 exact=0
USDJPY: agg_buckets=3 kept=1 vs docs/data D1(1931) common=0 exact=0
```

⇒ **我改用 §4.1 的方式對拍**（同 broker 的 H1/H4/D1 獨立序列），比 `docs/data` 嚴格得多：`docs/data` 的 D1 是另一條導出線，拿它對拍只能驗「兩條獨立收集線是否一致」，而我用 broker 自己的 TF 檔對拍，驗的是「聚合規則是否與 broker 的圖表語義完全一致」。

**若你要保留 `docs/data` 這條對拍**，需要你給一個時間窗口與 M1 重疊的 `docs/data/*_D1.json`（或讓 AC 的 M1 dump 覆蓋 2018–2026）。目前資料條件下做唔到。

### 4.4 派工單要求「M5」，我沒有 M5 檔

```
$ ls <terminal>/history/Alpari-Pro.ECN-Demo/*5.hst
（空 —— 只有 1 / 60 / 240 / 1440）
```

本機 MT4 終端**冇 M5／M15／M30 歷史檔**。所以 M5/M15/M30 的聚合只有合成測試（synthetic bars）覆蓋，冇 broker 實檔對拍。**要驗 M5 需要 AC 的 M1 dump 或你提供 M5 參照檔**。

---

## 五、測試（23 條，232 條全套 OK）

```
$ python -m unittest engine.tests.test_m1_aggregation
Ran 23 tests in 5.911s
OK

$ python -m unittest discover -s engine/tests -t .
Ran 232 tests in 9.267s
OK
```

（全套由 209 → **232**，+23 全部來自新檔）

逐類：

| 類 | 條數 | 覆蓋 |
|---|---|---|
| `TestTimeframeMinutes` | 3 | M1/M5/H1/D1、大小寫、未知 TF 拋錯 |
| `TestBucketBoundary` | 4 | floor 落在整數倍、唔會向前移、minutes=0 拒收、label 往返 |
| `TestAggregateSynthetic` | 7 | H1 fold 五個欄位、跨 bucket 切分、亂序輸入仍按 label 排序、M1 passthrough、D1 = server 午夜、空輸入、expected |
| `TestUsableBuckets` | 3 | 頭尾殘 bucket 丟、內部短 bucket 保留、空 |
| `TestCrossCheck` | 3 | 全中、缺參照不算錯、單欄不符要報出欄名 |
| `TestAgainstBrokerSeries` | 3 | **H1 vs broker H1**、partial edge 是唯一不符來源、**全 sweep 61 組** |

`TestAgainstBrokerSeries` 3 條全部 `@skipUnless(MT4 history present)` —— 換機器會 skip 而不會假綠。

```
$ python tests/language_check.py
language_check: scanned 920 files, violations 0

$ python tests/conflict_marker_check.py
[conflict-check] PASS: 0 衝突標記（6857 檔掃描）
```

---

## 六、我沒有做的事

- **冇改 `ccy_backtest/core.py`** —— CCYV3 的 RSI/ATR/9 幣分解一行未動。派工單說「改為 M1 單源」，但那需要先決定 `compute_power_history` 的輸入介面怎樣接聚合層（是全 TF 只餵 M1 再逐 TF 算，還是逐 TF 各自聚合再各自算），**兩種做法結果不同**（前一版必須重算 RSI 的 warmup，後一版 warmup 各 TF 獨立）。這是架構選擇，我唔自行拍。
- **冇碰 `docs/`／`config.py`／其他生成器**
- **冇新增任何資料收集路徑** —— 完全符合「唔好再開發針對多 TF 獨立數據嘅嘢」

---

## 七、要你決定（3 項）

| # | 事項 | 為何要你答 |
|---|---|---|
| 1 | **聚合層落點**：現放在 `engine/m1_aggregation.py`（與 `engine/bar.py`、`engine/sources/` 同層）。要搬去 `engine/sources/` 或 `ccy_backtest/`？ | 派工單寫的字面名（`hst_lib`/`power_engine`）在 repo 不存在，我按實際模組落點 |
| 2 | **`compute_power_history` 怎樣接聚合層**：① 全部 TF 只用 M1、逐 TF 各自算 RSI（warmup 各 TF 獨立）；② 所有 TF 從同一條 M1 序列算一次指標再抽樣？兩者結果不同，要你定 | 這是 CCYV3 數據層的架構選擇，影響 #36 SQLite 設計 |
| 3 | **M5 對拍缺參照**：本機 MT4 冇 M5/H15/M30 歷史檔。要 AC 的 M1 dump？還是由你提供 M5 參照檔？ | 冇參照就只能靠合成測試 |

---

## 八、附：一個順手發現（不影響交付，供你參考）

`engine/sources/mt5_source.py` 的 `TIMEFRAMES` 有 `W1: 10080`，我的聚合層**故意不收 W1** —— 週線的 bucket 邊界在 MT4 是「當週第一根 bar」，不是 `epoch % 604800`（週日 00:00），floor 會錯一天。要做 W1 必須先量出該 broker 的週界規則，唔可以照套。若你要 W1，另派工。

— ZCODE（本機 lane）2026-11-24 08:15 HKT
