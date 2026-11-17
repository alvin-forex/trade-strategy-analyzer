# engine — 波幅指標重建（A1：波浪提取）

MartingaleScanner 波幅引擎嘅 Python 逆向實作。**唔使用任何 MT4/MT5 內建 ZigZag 指標**：
波動偵測係 MetaQuotes 公開 `ZigZag.mq4` 算法嘅逐語句 Python 移植
（參考副本：`evidence/a1/mt4_zigzag_reference.mq4`），可移植、確定性、可逐 pivot 對照。

## 快速開始

```bash
# 1) 環境自檢（MT5 連線／帳號／伺服器）
python -m engine.extract --doctor

# 2) 提取波浪（主命令，需求書 §7 A1 CLI 契約）
python -m engine.extract \
  --symbol EURUSD --tf H1 \
  --from 2026-09-17T02:00 --to 2026-11-16T17:00 \
  --out waves.csv

# 3) 離線重跑（用已存嘅 MT4 bars，唔連 MT5）
python -m engine.extract --bars-csv engine/evidence/a1/mt4_EURUSD_H1_bars.csv \
  --from 2026-09-17T02:00 --to 2026-11-16T17:00 \
  --out waves_offline.csv --no-parity

# 4) 語義掃描（擬合未確認嘅 Merge 讀法）
python -m engine.sweep --limit 20

# 5) 單元測試
python -m unittest discover -s engine/tests -t . -v
```

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
| `merge.py` | Merge Percentage 過濾（`pre` / `post` 兩種基準）→ `Wave[]` |
| `buckets.py` | 80/15/5 分檔（按條數，round-half-up）、兩種 percentile 法 |
| `waves.py` | `waves.csv` 寫出／讀回、meta sidecar |
| `extract.py` | CLI 入口 |
| `sweep.py` | 語義參數掃描（擬合工具，唔參與出貨路徑） |
| `sources/mt5_source.py` | MT5 官方 API：bars、symbol 元數據、時區量測 |
| `sources/csv_source.py` | 離線 CSV（parity／跨券商比較用） |

## 已證實 vs 未證實

**詳見 `ASSUMPTIONS.md`。** 摘要：

✅ **ZigZag 移植與 MT4 原生逐 pivot 一致**（全歷史 122/122，價格零差異）
✅ **Deviation 單位 = points**（源碼 `InpDeviation*Point`）
✅ **Backstep = 清除回看支數，唔係最小間距**（源碼 + 手冊 Shortest=2 bars 反證）
✅ **分檔取整 = round-half-up**（手冊 53→42/8/3 與 AC 49→39/7/3 同時符合）
❌ **Merge Percentage 基準未解**：≥10 種讀法全部對唔到 49 段
❌ **原廠面板數字未取得**（GEMS DLL 保護 + chart-global object 讀唔到）

## 現時 parity 狀態（截至 A1）

| 項目 | 目標 | 實測（Alpari demo） | 差 |
|---|---|---|---|
| 總段數 | 49 | 55 | +6 |
| 三檔 | 39/7/3 | 44/8/3 | — |
| Total bars | 631/210/162 | 658/254/95 | — |
| Total bars 合計 | 1003 | 1007 | +4 |
| 窗口 bars | 1023 | 1023 | ✅ |
| 原始 pivot 數 | ? | 60 | — |

**未達成 parity。** 唔會為湊 49 段改算法；差異已記錄，等券商確認同 Merge 語義釐清。

## 硬性約束遵循

1. ✅ 唔用 MT4/MT5 內建 ZigZag —— 自家移植
2. ✅ 唔自創算法 —— 全部源碼有據，未證實者入 `ASSUMPTIONS.md`
3. ✅ 只改 `engine/` —— 未動 `docs/`、`exchange/`、`src/`、`mt4/`、`mt5/`
4. ✅ 每階段一次 commit，前綴 `[A1]`
