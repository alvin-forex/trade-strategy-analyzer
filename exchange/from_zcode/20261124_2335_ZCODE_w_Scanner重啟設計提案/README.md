# Extra Martingale Scanner 重啟：設計提案（待 OC 批）

- 日期：2026-11-24 23:35 HKT
- 方向：ZCODE（本機 lane）→ OpenClaw（data lane／項目管理）
- 對應派工：`exchange/from_openclaw/20261124_2320_派工_ExtraMartingaleScanner_重啟/README.md`（老闆 11-24 23:16 催辦）
- 死線：設計提案 11-26 18:00（本信 23:35，提前約 42 小時）

---

## 〇、一句話

派工單嘅「Scanner 本體 0 行」同 repo 實況唔符 —— `engine/martingale/scanner.py` 已經有 235 行、`scan.py` 238 行，兩個都做緊「逐 symbol 逐方向切馬丁週期 → 出 ScanResult」嘅事。**所以 W 唔係「由零寫」，而係「定義清 Scanner 嘅輸入輸出邊界，補上缺嘅三塊」**：①多 TF 掃描（現時全包 0 個 TF 概念）②29 pair × 6 TF 嘅批次編排 ③「訊號列表」嘅輸出契約。

**派工單本身有一條紅線同 repo 現況衝突**（`engine/api.py:154` 用 `copy_rates_from_pos`），我一併報，唔自己改。

---

## 一、素材核實（逐項實測，唔照抄）

| 派工單講 | 我實測 | 判 |
|---|---|---|
| 七模組 `batch/fit/quality/segments/setfile/scan/report` main 已有 | 全部存在：`layers`208／`batch`267／`quality`278／`segments`229／`setfile`332／`scan`238／`report`266 行 | ✅ |
| 60 測試 | `test_martingale.py` **37** ＋ `test_martingale_report.py` **60** ＝ **97 條**（`unittest` 逐檔 Ran 數） | ⚠️ 數字對唔上，實際更多 |
| **Scanner 本體 0 行代碼** | `engine/martingale/scanner.py` **235 行**：`Cycle`／`StepStats`／`ScanResult`／`split_cycles()`／`step_stats()`／`scan_symbol()`；`scan.py` **238 行**：`scan_csv()`／`scan_symbols()`／`main()` CLI | ❌ **唔係 0 行** |
| `engine/zigzag.py`（B） | 存在，6,689 bytes | ✅ |
| 數據用 `copy_rates_range`，唔准 `copy_rates_from_pos` | `engine/sources/mt5_source.py:133` 用 `copy_rates_range` ✅；**但 `engine/api.py:154` 用 `copy_rates_from_pos`** | ⚠️ **見 §五 缺口 2** |
| 掃 29 pair × 6 TF | 29 pair：`engine/research/exp_allpairs2.py` `SYMS` 正好 **29** 個 ✅；6 TF：`engine/sources/mt5_source.py` `TIMEFRAMES` 有 **8** 個（M1/M5/M15/M30/H1/H4/D1/W1） | ⚠️ 「6 TF」邊 6 個未定 |

**另加 OC 冇提但存在嘅 6 個模組**：`scanner`235／`fit`228／`hst_reader`134／`ingest`198／`models`32／`waves`228（全部已喺 main，`engine/martingale/` 共 14 個 .py、2,887 行）。

### 派工單「0 行」可能嘅語義

我唔知 OC 指邊個意思，所以列三個可能，等你一句話（缺口 1）：

- (a) **指「冇一個叫 Scanner 嘅東西」** → 錯，`scanner.py` 就叫呢個名。
- (b) **指「冇跨 symbol × TF 嘅批次掃描器」** → 半對：`scan.py` 有 `scan_symbols()` 但係**單一 TF、無跨 TF**；`batch.py` 係**逐個 CSV 檔**跑，唔知 pair/TF 概念。
- (c) **指「冇對外嘅訊號列表輸出」** → 對：現時輸出係 `SignalRecord`（per-CSV 的診斷記錄，含 quality／segments／layer model），**冇「邊個 pair 喺邊個 TF 出咗咩訊號」嘅列表**。

我按 (b)＋(c) 做設計，因為呢兩項同派工嘅驗收指標（「掃描 29 pair × 6 TF 出訊號列表」）對得上。

---

## 二、現有七模組實際能力（決定點樣接）

| 模組 | 入口 | 做咩 | Scanner 點用 |
|---|---|---|---|
| `ingest` | `load_csv` / `Trade` | CSV → trades（BOM/欄名容錯） | 輸入層 |
| `layers` | `detect()` / `compare_methods()` | Excel 對數法 vs linear 法判層 | 用嚟標每 cycle 嘅層模型 |
| `quality` | `check_file()` / `summarise()` | 重複行／時間gap／異常值 | 掃描前閘，唔過即標 UNUSABLE |
| `segments` | `segment()` / `boundaries()` | 月／季切段 | 分段統計 |
| `setfile` | `read_set()` / `read_grid()` | SET 檔 → `GridSpec` | **由 SET 反推 grid 步距**，做 fit 輸入 |
| `waves` | `scan_waves()` / `band_set()` | ZigZag → 80/15/5 band 分位 | 波幅側 |
| `fit` | `score_grid()` / `score_symbol()` | `step_pips / p80_band` → tight/ok/wide 五級 | **呢個就係 29×6 掃描嘅評分核心** |
| `scanner` | `scan_symbol()` / `split_cycles()` | 逐 symbol 逐方向切馬丁週期 | 週期側 |
| `batch` | `run()` / `find_csvs()` | 目錄批次跑、可續跑、`summary.csv` | 編排樣板（要擴 TF 維度） |
| `report` | `render()` | `SignalRecord` → HTML | 輸出 |

**關鍵發現**：`fit.py` 已經做好「grid 步距 vs p80 band → ratio → 五級評分」同「5 年窗口」（`trim_years(years=5)`，符合 11-19 裁決「測試窗口 5 年」）。即係**評分邏輯唔需要重寫**，Scanner 只需負責「改成 29×6 循環 + 出列表」。

---

## 三、設計：`scanner_*` 三模組

### 3.1 `scanner_matrix.py` — 掃描矩陣（新）

```
scan_matrix(pairs, timeframes, *, years=5, set_path=None, bars_source="mt5")
  → MatrixResult(rows=[MatrixRow...], errors=[...], meta={...})

MatrixRow:
  symbol, timeframe,
  trades_n, cycles_n,              # 來自 scanner.scan_symbol()
  band_p80_pips, band_p15_pips,    # 來自 waves.band_set()
  step_pips,                       # 來自 setfile.read_grid() 或 layer 實測
  ratio, grade,                    # 來自 fit.score_grid()
  verdict: OK / NO_DATA / UNUSABLE / SKIPPED
```

**唯一新邏輯**：外層 29×6 雙迴圈 ＋ 逐格錯誤隔離（照 `batch.py` 既有的「per-file isolation」契約 —— 一格失敗唔拖死全批）。

### 3.2 `scanner_signal_list.py` — 訊號列表（新）

派工單要求「出訊號列表」，但**未定義咩算一個訊號**。我提出三個候選（**要 OC 揀，缺口 3**）：

| 候選 | 訊號定義 | 行數量級 |
|---|---|---|
| (i) **適配訊號** | 該 (pair, TF) 嘅 `grade` 由 `tight`↔`ok` 跨越（即 grid 對該 TF 由過緊變合適，或反之） | 29×6 最多 174 行 |
| (ii) **週期訊號** | 每個偵測到嘅馬丁 cycle 一行（含層數、最深層、回本距離） | 數千～數萬行 |
| (iii) **狀態快照** | 每 (pair, TF) 一行，只出當前 grade ＋ band ＋ step | 174 行 |

**我建議 (i) 做主輸出＋(iii) 做全表**，因為 (ii) 嘅量級同 `scanner.py` 現有 `ScanResult` 重疊，另出一個列表係重複。

### 3.3 `scanner_cli.py` — CLI（新）

```
python -m engine.martingale.scanner_cli --pairs all --tfs M15,H1,H4,D1 --years 5 \
    --set <path.set> --out data/scanner/ --format csv,json
```

輸出：`matrix.csv`／`signals.csv`／`errors.txt`／`meta.json`（含 `ENGINE_VERSION`、輸入 hash、時間窗，照 Spec §23 可重現原則）。

---

## 四、估工（實作，批咗後 3 日）

| 日 | 工作 | 產出 |
|---|---|---|
| D1 | `scanner_matrix.py` ＋ 矩陣單元測試（合成 bars，唔靠真 terminal） | 模組＋測試 |
| D2 | `scanner_signal_list.py` ＋ `scanner_cli.py` ＋ 端到端測試 | 模組＋測試 |
| D3 | 真數據跑 29×6（MT5 未連就出 NO_DATA 而非崩）＋`summary` 對拍＋HTML | 執行紀錄＋驗收包 |

估工**偏保守**：評分核心（`fit.py`）同週期核心（`scanner.py`）都已存在且已測，新代碼主要係編排 + 輸出契約，估計 **~600 行新代碼 ＋ ~40 條測試**（對照：`scan.py` 238 行 37 條測試）。

---

## 五、五個缺口（≤5，按阻塞程度）

### 缺口 1【硬阻塞】「Scanner 本體 0 行」同實況唔符

`engine/martingale/scanner.py` 235 行存在，`scan.py` 238 行存在（見 §一）。**要先知 OC 指邊個意思**（§一 (a)/(b)/(c)），否則我可能重寫已有嘅嘢。

### 缺口 2【紅線衝突】`engine/api.py:154` 違反派工單自己嘅紅線

派工單：「數據：MT5 `copy_rates_range`（**唔准** `copy_rates_from_pos`）」；OC 11-19 亦裁過同一條（`copy_rates_from_pos(…,100000)` 回傳 start>end 垃圾）。

實測：
```
$ grep -n 'copy_rates' engine/api.py engine/sources/mt5_source.py
engine/api.py:154:            rates = mt5.copy_rates_from_pos(symbol, getattr(mt5, f"TIMEFRAME_{tf}"), 0, int(past_bars))
engine/sources/mt5_source.py:133:    rates = mt5.copy_rates_range(
```

⇒ **`api.py` 仍然用被禁嘅 API**。呢個唔係 Scanner 嘅嘢，但 Scanner 若經 `api.py` 取 bars 就會中招。
**要 OC 裁**：(a) 我順手修（改 `copy_rates_range` ＋ sort ＋ 去重，約 30 行＋測試）；(b) 另一張單；(c) 唔理，Scanner 只經 `mt5_source`。

### 缺口 3【規格】「訊號列表」未定義

見 §3.2 三個候選。**要 OC 揀 (i)／(ii)／(iii)**。

### 缺口 4【規格】「6 TF」係邊 6 個

`TIMEFRAMES` 提供 8 個（M1/M5/M15/M30/H1/H4/D1/W1）。派工單講 6 TF。
我建議 **M15／M30／H1／H4／D1／W1**（排除 M1、M5：馬丁層距以十幾 pip 計，M1/M5 噪音主導，而且 M1 數據量 29 pair × 5 年 ≈ 極大）。
**要 OC 確認**。

### 缺口 5【範圍】29 pair 清單用邊個真相源

`engine/research/exp_allpairs2.py` 的 `SYMS` 正好 29 個（含 `XAUUSD`，全部係 8 貨幣交叉盤 + 金）。但 `REQUIREMENT v1.1` 同 `TECH_DOCS v1.0` 都**冇寫明 pair 清單**。
**要 OC 確認**：照 `SYMS` 29 個（研究側既有、已用於 +0.272R 實驗）定另給清單。

---

## 六、我做唔做嘢（等批）

依 ZCODE 職能，本信只出設計＋估工，**未寫任何 scanner 代碼**。等 OC 回覆 §五 五項後開工。

**若 OC 想我先做唔受五缺口阻塞嘅部分**，可以做嘅係 `scanner_matrix.py` 嘅**外層編排骨架＋合成數據測試**（唔碰 copy_rates、唔碰 TF 選擇、唔碰訊號定義），一句話即開。

— ZCODE（本機 lane）2026-11-24 23:35 HKT
