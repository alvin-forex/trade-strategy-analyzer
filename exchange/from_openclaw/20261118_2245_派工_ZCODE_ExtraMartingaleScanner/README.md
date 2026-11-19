# 派工：Extra Martingale Scanner 重製版

- 卡：#30（https://github.com/alvin-forex/trade-strategy-analyzer/issues/30）
- lane：zcode-local
- 派工時間：2026-11-18 22:45 HKT
- 死線：階段 1＋2 → 2026-11-20 18:00｜階段 3＋4 → 2026-11-22 18:00
- 老闆原話：「Martingale Scanner重製版叫 Extra Martingale Scanner」「或者你先派咗馬汀Scanner相關嘅工作出去先，我哋慢慢研究呢個extra CCypower」

---

## 一、數據資產（OC 已點清，你唔需要再搵）

```
downloads/*.csv        275 檔、593,230 筆交易、293 個 unique signal id
docs/downloads/*.csv   201 檔（與上者部分重複）
```

CSV 表頭 **三種變體**（解析器必須容錯）：

| 變體 | 檔數 | 差異 |
|---|---|---|
| A（主流） | 260 | `...,Max Profit,Max Pips,Max Loss,Max Loss Pips,Magic Number,Comment,Holding Time (Hours),Holding Time` |
| B | 12 | 同上但少了最後一個 `Holding Time` |
| C | 1 | `...,Net Profit,Holding Time (Hours),Max Profit,Max Pips,...` 次序不同，且**缺 `Max Pips` 前的 `Net Pips` 段落** |

其他數據事實：
- 最大檔 32,832 筆；中位 803 筆；**30 檔少於 100 筆**（跳過或標記）；**1 檔只有表頭零數據**（`wc -l` = 0）
- Magic Number 分佈：`1`(3713)、`1313`(1288)、`1212`(817)、`12345`(578)、`1234`(337)、`0`(330)
- Comment 有語義：`Wayne Class`、`SMA BUY/SELL`、`Dragon Wave_CZ0/BZ0`、`MKD BUY/SELL`
- 41 個 symbol，top：XAUUSD(1729)、EURUSD(1019)、AUDUSD(716)、USDCAD(655)、GBPCAD(643)
- `docs/data/tsa.db` → `dde_scores` 997 行，已有 `martin_pct`／`layers_json`／`ea`／`lv` 欄位可對照

## 二、現有程式碼（可重用，**唔准重寫**）

| 檔案 | 行數 | 用途 |
|---|---|---|
| `martin_autopsy_v3.py` | 883 | V3 剖析核心：層數推斷、MFE/MAE、Danger Score |
| `generate_martin_autopsy_v3.py` | 1551 | V3 報告生成器 |
| `docs/martin_v4_engine.js` | 349 | V4 前端引擎：parseCSV／computeLayerStats／computeRating／computeBlacklist |
| `martin_v4_template.html` | 589 | V4 模板 |
| `src/martin_detector.py` | — | 由 .set 參數偵測 GRID/MARTINGALE/DCA |
| `scripts/w5a_martin_v4_20261105.py` | — | martin_v4 族 165 頁 NAV 四件補齊 |
| `PRD_MARTIN_V4.md` | 223 | V4 PRD（Phase 2 = Set File Change Detection，未做） |

**開工前必讀 `martin_autopsy_v3.py`。你若重寫一份，等於製造第二個真相來源，我會打回。**

## 三、OC 原型（可重現，已驗證）

附件 `oc_prototype_zigzag_scan.py`（1,939 B）—— EURUSD H1、3,038 支、`depth=12` 樞紐、`0.35` merge、1024 窗滑動。

OC 2026-11-18 22:40 重跑輸出（你可複現）：
```
fixture: (17, 73, 119, 166)
err=77.7 | 窗尾距而家 14 燭 | bands 36.5/89.6/129.1/197.5 | 43波
err=81.4 | 窗尾距而家 39 燭 | bands 36.5/92.3/130.1/197.5 | 41波
```

**呢個係原型，唔係產品。** 你要把它變成可重跑、有測試、有 CLI 嘅模組。

## 四、`.hst` 格式（OC 已破解，**唔准再猜**）

```
標頭 148 bytes
每筆記錄 60 bytes：
  +0   int32   Unix 秒        ← 注意：int32，唔係 int64
  +8   float64 open
  +16  float64 high
  +24  float64 low
  +32  float64 close
  +40  float64 volume
  +48  int32   spread
```

驗證：`VantageMarkets-Live 11/EURUSD240.hst` → 15,712 筆，全部 O/H/L/C 合理（L≤O,C≤H），2009-12-21 → 2026-10-16，零異常。

**踩過嘅坑**：早前用 `<q` 讀 +0 同 `<dddd` 讀 +8，得出 `1.383797990166262e-168` 呢類垃圾數 —— 因為時間係 int32 令 offset 全錯。**直接抄上面張表，唔好自己推。**

可用 `.hst` 目錄（3 個 server，共 660 檔）：
```
/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/history/VantageMarkets-Live 11/     197 檔
.../VantageInternational-Live 11/   293 檔
.../Alpari-Pro.ECN-Demo/            170 檔
```

## 五、交付物（詳見 #30）

| 階段 | 內容 | 路徑 | 死線 |
|---|---|---|---|
| 1 | 掃描核心：層數／倍率／加倉距離／回本距離 | `engine/martingale/scanner.py`、`models.py` | 11-20 18:00 |
| 2 | 波幅帶：ZigZag 移植＋hst 讀取 | `engine/martingale/waves.py`、`hst_reader.py` | 11-20 18:00 |
| 3 | 適配評分：grid 間距 vs 8 年波幅 | `engine/martingale/fit.py` | 11-22 18:00 |
| 4 | CLI＋批量 | `scan`／`batch` + `engine/evidence/mart/summary.csv` | 11-22 18:00 |

## 六、驗收準則（機器可判，全部要貼真實輸出原文）

```
python -m unittest discover -s engine/tests -t .      → 全綠，條數 ≥ 102
python -m engine.martingale.batch --dir downloads/     → 275 檔零 crash，failed.txt ≤ 5 個
python -m engine.martingale.scan --csv <單檔>          → JSON 欄位齊
python scripts/tsa_qa_check.py                         → PASS
python tests/language_check.py                         → 0 violations
```

新增測試 ≥ 12 條：CSV 三變體各 1、空檔／負行數 1、層數偵測 3、倍率判定 3、hst 讀取 2、fit 分級 2。

`hst_reader` 抽驗必須與 OC 值一致：首筆 2009-12-21 00:00 O=1.43110 H=1.43470 L=1.43110 C=1.43420。

## 七、已知陷阱

1. **唔准自創策略邏輯。** 呢張卡只做「讀入 + 建模 + 計算」。entry/exit、EA 參數建議屬 LEGEND／老闆。
2. `.hst` offset 陷阱（見第四節）。
3. 293 個 signal id 但 275 個 CSV —— 缺失要報，唔准靜靜跳過。
4. 1 檔零數據、30 檔 <100 筆 —— 要當「空檔／樣本不足」處理，唔好 crash。
5. **只改 `engine/`**。`docs/`、`exchange/`、`config.py` 唔准碰。

## 八、通道（新規則，即刻生效）

1. 你個 clone 已失效（OC 今晚改寫咗歷史）。先做：
   ```
   git fetch --all --prune --force
   git reset --hard origin/local/alvin
   ```
   **嚴禁 `git pull --rebase`**
2. 完成後：push `local/alvin` → **自己即刻開 PR**
3. notify 檔同 commit 一齊 push：`exchange/notify/from_zcode/<時戳>_<事項>.md`
4. 唔准開 Issue（卡由 OC 開）

> ✅ 已處理 2026-11-19 08:40 by ZCODE_w（收悉）
