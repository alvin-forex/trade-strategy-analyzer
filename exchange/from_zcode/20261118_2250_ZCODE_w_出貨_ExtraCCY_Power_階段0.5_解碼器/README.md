# 出貨：ExtraCCY Power 階段 0.5 —— PowerHistory 解碼器

> ✅ 已交付 2026-11-18 22:50 by 本機 ZCODE（`lane:zcode-local`）

方向：本機 ZCODE（code lane）→ OpenClaw（data lane）／老闆
對應卡：GitHub #27 `[zcode] ExtraCCY Power 重製版`
性質：交貨（階段 0.5）

---

## 1. 交付物

| 檔案 | 用途 |
|---|---|
| `engine/research/powerhistory_decode.py` | 解碼 CLI（本單主體） |
| `engine/tests/test_powerhistory_decode.py` | 10 條離線測試 |

**指令（照 #27 驗收準則原文）**

```bash
python -m engine.research.powerhistory_decode --dir "<dir>" [--out <out>] [--manifest <mf>]
```

---

## 2. #27 驗收準則逐項核對

| # | 準則 | 結果 |
|---|---|---|
| 1 | `python -m engine.research.powerhistory_decode --dir <dir>` 可重跑 | ✅ |
| 2 | 輸出 50 檔 CSV | ✅ 50/50 |
| 3 | 每檔附 sha256 對得上 manifest | ✅ **50/50 match** |

實跑原文：

```
decoded 50 file(s) -> C:/Users/alvin/AppData/Local/Temp/ph_decode
manifest -> C:/Users/alvin/AppData/Local/Temp/ph_decode\decode_manifest.json
sha256: 50/50 match manifest
```

（manifest 用 `exchange/from_autoclaw/20261118_1210_PowerHistory樣本與解碼報告/PowerHistory_MANIFEST.json`，
可用 `--manifest <path>` 指定，唔一定要放喺樣本目錄旁邊。）

---

## 3. 額外做到的兩件事（驗收準則冇要求，但影響可信度）

### 3.1 兩次跑 byte-identical

```
md5sum run1 50 個 CSV  vs  run2 50 個 CSV  →  diff 為空
```

理由：CSV 用 `lineterminator="\n"` 寫死 LF，兩平台雜湊一致。唔做呢步，Windows 出 CRLF、
Linux 出 LF，同一份資料兩個 hash，審計線會斷。

### 3.2 貨幣碼順序逐檔解析，唔硬碼

`.dat` header 內嘅 9 個貨幣碼，**兩族順序唔同**：

| 族 | 順序 |
|---|---|
| A（D1_2..9、H4_1..9、H1_10000、M30_51200） | `EUR GBP AUD NZD CHF JPY XAU CAD USD` |
| B（D1_10/20/…、H1_60/…、M30_60/…） | `GBP AUD NZD CAD CHF JPY XAU USD EUR` |

解碼器讀每個檔自己嘅 header，唔假設固定順序。測試 `test_column_order_follows_each_file_header`
專門守呢條 —— 若日後有人改成硬碼，B 族會靜默錯欄，測試會紅。

---

## 4. 輸出格式

```csv
timestamp_utc,epoch,EUR,GBP,AUD,NZD,CHF,JPY,XAU,CAD,USD
2025-01-21 00:00:00,1737417600,4.0,3.5,4.25,3.0,4.666666666666667,6.5,8.0,3.0,4.875
```

- `timestamp_utc`：人類可讀（UTC），由 epoch 轉出
- `epoch`：原始 int64，保留做精確對齊
- 9 個幣值：`repr()` 全精度（唔四捨五入）

另出 `decode_manifest.json`：每檔 `bytes` / `sha256` / `manifest_sha256` / `sha256_status` /
`rows` / `codes` / `first` / `last`。

---

## 5. 退出碼

| 碼 | 意思 |
|---|---|
| 0 | 全部成功（有 manifest 且全對，或冇 manifest 只解碼） |
| 1 | sha256 對唔上 manifest（審計失敗） |
| 2 | 目錄冇 `PowerHistory_*.dat` |

**sha256 對唔上就 return 1** —— 呢個係刻意設計：資料被改過就唔准靜默過關。

---

## 6. 測試

```
python -m unittest discover -s engine/tests -t .
→ Ran 112 tests, OK
```

原 102 條（A1/A2/A3 + Period 研究）＋ 本單 10 條 = **112 條全綠**。

本單 10 條覆蓋：
1. `sha256("abc")` 對公開常數
2. 同 bytes → 同 hash
3. CSV 有 header、固定欄序、兩次跑 byte-identical、無 CRLF
4. 欄序跟每個檔自己 header（B 族旋轉順序）
5. manifest 檔名→entry 映射
6. 冇 manifest 唔算錯
7. `--manifest` 顯式路徑優先
8. CLI exit 0 + 寫出 decode_manifest
9. 空目錄 exit 2
10. sha256 錯 → exit 1

---

## 7. 未做（階段 1 前置）

`CcyPowerCount.mq4`（階段 1，死線 2026-11-20 18:00）**未開工**。前置：

1. `up` 的精確定義仍未釘死（見 §8）
2. 需要 TierB 同源樣本 → 依賴 #19（panel 側）

---

## 8. 順帶報告：Period 語義研究（已 commit 上 main）

`engine/research/CCY_POWER_PERIOD_FINDINGS.md`（commit `eaf6df39f`，已隨 PR #22 上 main）
＋ `engine/research/period_probe_run.py`（一鍵重跑）。

三個結論（全部有 `.dat` 硬證據）：

1. **`C = Period − 1` 否證**。`H4_1..H4_9` 同一時窗、同一 TF、2,074 筆、時戳逐點相同，
   只改 Period：最小晶格分母 D 由 P=1 到 P=9 **完全不變**（EUR=8、GBP=14）。
   → 比較次數恆定 **9**。
2. **Period 唔係輸出平滑**。sd 由 1.3047→1.2164（只跌 6.8%，若低通應跌 67%）；
   `xcorr(H4_1,H4_P)` 由 0.829 跌到 0.467。
3. **7 種機制已排除**（lag-P、block、close-vs-SMA、價格 EMA、輸出 EMA、輸出 SMA、hold/decimate）。

兩條可直接用的定律（跨 H4／D1 兩族獨立命中，誤差 ≤0.033）：
`acf1(Power_P) ≈ (P−1)/(P+1.5)`、`sd(Power_P) ≈ 常數`。

⚠️ 對 #27 階段 1 的影響：**唔可以照 `C = Period−1` 寫 `CcyPowerCount.mq4`**，
否則 P 一改就錯。詳見 `engine/research/CCY_POWER_PERIOD_FINDINGS.md` §二、三。

---

## 9. 已知限制

1. 解碼器**只讀檔、不判斷族**。A/B 族要人手分（manifest 內 `families` 已註明）。
   B 族晶格純度僅 61–82%、首筆 `1971-01-05` 只有 USD=9.0（1971 年冇 EUR）→
   **疑似合成，唔准作 ground truth**。
2. 50 檔共 102 MB，解碼後 CSV 約 125 MB。**唔建議入 repo**，建議產出走 Release asset 或由 CI 快取。
3. 本機暫存路徑 `%TEMP%\ph_decode` 跑完即棄，冇 commit。

— 本機 ZCODE（`lane:zcode-local`）
