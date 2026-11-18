# engine — 波幅指標重建（A1 波浪 / A2 波幅表 / A3 MCP＋每日更新）

MartingaleScanner 波幅引擎嘅 Python 逆向實作。**唔使用任何 MT4/MT5 內建 ZigZag 指標**：
波動偵測係 MetaQuotes 公開 `ZigZag.mq4` 算法嘅逐語句 Python 移植
（參考副本：`evidence/a1/mt4_zigzag_reference.mq4`），可移植、確定性、可逐 pivot 對照。

## 快速開始

```bash
# 1) 環境自檢（MT5 連線／帳號／伺服器）
python -m engine.extract --doctor

# 2) 提取波浪（A1）＋波幅表（A2）
python -m engine.extract \
  --symbol EURUSD --tf H1 \
  --from 2026-09-17T02:00 --to 2026-11-16T17:00 \
  --out waves.csv \
  --table EURUSD_H1
#    -> waves.csv              A1 波浪清單（固定五欄）
#    -> waves.meta.json        溯源十欄 + 分檔統計
#    -> EURUSD_H1.table.csv    波幅表（§13 九欄）
#    -> EURUSD_H1.table.json   同上 + detail（給網站／MCP 讀）
#
#    A2 選項：
#      --bucket-method count|rank|inc   分檔推導法（預設 count，唯一有實證）
#      --table-format  csv|json|both    波幅表格式（預設 both）

# 3) 離線重跑（用已存嘅 MT4 bars，唔連 MT5）
python -m engine.extract --bars-csv engine/evidence/a1/mt4_EURUSD_H1_bars.csv \
  --from 2026-09-17T02:00 --to 2026-11-16T17:00 \
  --out waves_offline.csv --no-parity

# 4) 語義掃描 + 對真面板擬合（研究工具，唔參與出貨）
python -m engine.sweep --limit 20
python engine/fit_panel3.py

# 5) A3：MCP server（四個 tool，stdio 預設）
python -m engine.mcp_server                # 畀 MCP client 接
python -m engine.mcp_server --list         # 印 tool 清單
python -m engine.mcp_server --transport streamable-http --port 8765

# 6) A3：每日自動更新（排程交外部 cron / Task Scheduler）
python -m engine.daily --symbols EURUSD,GBPUSD,USDJPY --tf H1,H4
python -m engine.daily --dry-run           # 只出計劃
#    -> <out-dir>/<SYMBOL>_<TF>.table.{csv,json}
#    -> <out-dir>/<SYMBOL>_<TF>.waves.csv (+ .meta.json)
#    -> <out-dir>/manifest.json            （唯一帶時間戳嘅檔）
#    exit 0 全成功 / 1 有失敗 / 2 參數錯

# 7) 單元測試
python -m unittest discover -s engine/tests -t . -v
```

## MCP tools（A3）

| tool | 用途 |
|---|---|
| `get_rates` | OHLC bars + digits/point/pip + broker/server 溯源 |
| `extract_waves` | ZigZag＋Merge → 波浪清單（idx/startTime/endTime/bars/amplitudePips/direction）|
| `compute_buckets` | 80/15/5 統計 ＋ Range 四界；可直接餵 amplitudes 或跑全流程 |
| `export_table` | 跑流程並落檔，回每個 artefact 嘅 path + sha256 |

回傳永遠係 `{"ok": true, ...}` 或 `{"ok": false, "error": {"code", "message"}}`。
錯誤碼：`bad_argument` / `no_terminal` / `unknown_symbol` / `no_data` /
`insufficient_sample` / `io_error`。失敗係值唔係 exception，client 一定收到原因。

`mcp` 套件係**可選**依賴 —— 冇裝它，CLI、每日批次、引擎全部照跑。

## 輸出契約

`waves.csv` 固定五欄，順序固定，UTF-8 無 BOM、LF 行尾：

```
idx,startTime,endTime,bars,amplitudePips
1,2026-09-17T17:00,2026-09-18T15:00,22,43.40
```

- `idx` 1-based、由舊到新
- `startTime/endTime` = MT5 圖表見到嘅 **server time 標籤**（`YYYY-MM-DDTHH:MM`）
- `bars` = `end_idx − start_idx`（`--bar-mode inclusive` 則 +1）
- `amplitudePips` = `|Δprice| / pip_size`，2 位小數

十個溯源欄位（需求書 §4）**唔入 CSV**，另寫 `waves.meta.json`，並附 `csv_sha256`。
同一輸入同一參數 → CSV byte-identical。

## 模組

| 模組 | 職責 |
|---|---|
| `bar.py` | `Bar` 容器、CSV 載入、窗口切片、`pip_size()` |
| `zigzag.py` | MT4 `ZigZag.mq4` 三遍算法嘅逐語句移植 → `Pivot[]` |
| `merge.py` | Merge Percentage 過濾（`drop_next` 預設；另有 `pre` / `post` 對照）→ `Wave[]` |
| `buckets.py` | 80/15/5 分檔（`count`/`rank`/`inc` 三法可切換）＋ Range 四界（floor） |
| `table.py` | 波幅表輸出（§13 九欄 CSV＋JSON、panel 文字排版） |
| `waves.py` | `waves.csv` 寫出／讀回、meta sidecar |
| `extract.py` | CLI 入口 |
| `api.py` | 四個操作嘅程式介面（回傳 `{ok, ...}` / `{ok:false, error}`）|
| `mcp_server.py` | MCP server：`api` 四個函數嘅薄包裝 |
| `daily.py` | 每日批次：跑 symbol×TF 矩陣、落檔、出 manifest |
| `sweep.py` / `fit_panel3.py` | 語義參數掃描（擬合工具，唔參與出貨路徑） |
| `sources/mt5_source.py` | MT5 官方 API：bars、symbol 元數據、時區量測 |
| `sources/csv_source.py` | 離線 CSV（parity／跨券商比較用） |

## 已證實 vs 未證實

**詳見 `ASSUMPTIONS.md`。** 摘要：

✅ **ZigZag 移植與 MT4 原生逐 pivot 一致**（全歷史 122/122，價格零差異）
✅ **Deviation 單位 = points**（源碼 `InpDeviation*Point`）
✅ **Backstep = 清除回看支數，唔係最小間距**（源碼 + 手冊 Shortest=2 bars 反證）
✅ **分檔取整 = round-half-up**（手冊 53→42/8/3 與 AC 49→39/7/3 同時符合）
✅ **Merge 基準 = `drop_next`**（真面板 49 段反推，Medium 七項全中）
✅ **Range 四界 = floor 截斷**（128 唔係 129）
✅ **Longest/Shortest 嘅 pips 跟 bars 揀出嘅同一段**（唔係 class max/min）
⚠️ **尾段單一殘差未解**（一段 pivot 面板保留、我方 35% merge 剔除）

## Parity 狀態（對原廠面板實測，Alpari demo）

面板真實數字（2026-11-18 老闆截圖確認）：`12-110 / 110-128 / 128-249`，
Crazy **162 bars / 551.3 pips**。

| 項目 | 面板 | 本引擎 | |
|---|---|---|---|
| 總段數 | 49 | **49** | ✅ |
| 三檔段數 | 39/7/3 | **39/7/3** | ✅ |
| Medium total bars | 211 | **211** | ✅ |
| Medium total pips | 831.1 | **831.1** | ✅ |
| Medium avgB | 30.1 | **30.1** | ✅ |
| Medium longest | 56b / 119.4p | **56b / 119.4p** | ✅ |
| Medium shortest | 11b / 128.5p | **11b / 128.5p** | ✅ |
| **Crazy total pips** | **551.3** | **551.3** | ✅ |
| Normal longest | 48b / 99.9p | **48b / 99.9p** | ✅ |
| Range b0 (Normal 下限) | 12 | **12** | ✅ |
| Range b1 (Normal 上限) | 110 | **110** | ✅ |
| Range b2 (Crazy 下限) | 128 | **128** | ✅ |
| Normal total bars | 630 | 611 | −19 |
| Crazy total bars | 162 | 185 | +23 |
| Range b3 (Crazy 上限) | 249 | 253 | +4 |

**核心算法已確定**（ZigZag 12/5/3 移植 + merge `drop_next` 35% + round-half-up 分檔
＋ Range floor 四界）：Medium 全七項、Crazy pips、Normal longest、Range 前三界**全部精確命中**。

殘差全部源自**單一尾段**（最長段 103 vs 99 bars），同 Range b3 嘅 4 pip 差係同一件事。
詳見 `ASSUMPTIONS.md`。唔會為湊數改算法。

## 硬性約束遵循

1. ✅ 唔用 MT4/MT5 內建 ZigZag —— 自家移植
2. ✅ 唔自創算法 —— 全部源碼／實測有據，未證實者入 `ASSUMPTIONS.md`
3. ✅ 只改 `engine/` —— 未動 `docs/`、`exchange/`、`src/`、`mt4/`、`mt5/`
4. ✅ 每階段一次 commit，前綴 `[A1]` / `[A2]` / `[A3]`

## 測試

```
python -m unittest discover -s engine/tests -t .
```

A1 22 條、A2 22 條、A3 44 條，共 **88 條全綠**。
A3 全部用 `evidence/a1/` 嘅 MT4 實錄 CSV 跑，**唔需要 MT5 終端**。
（另有 `engine/evidence/a3/` 存一次真 MT5 批次嘅產物＋manifest 作實證。）
