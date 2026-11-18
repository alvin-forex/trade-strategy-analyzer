> ⏳ 進行中 2026-11-18 08:15 by ZCODE_w（等 OpenClaw 部署／跑 Tier B＋回批）

---
方向: ZCODE_w（機窗 lane）→ OpenClaw（data lane）／老闆
日期: 2026-11-18 08:15 HKT
性質: 派工（CCY Power 逆向第二輪：階段 0 防禦版＋Tier B 同源診斷工具）
對應: 老闆 2026-11-18 指示「再做階段0 + TierB」＋已交 `PowerHistory_D1_8.dat` 樣本
---

# 0815 派工：CCY Power 階段 0 ＋ Tier B 診斷工具（請 OpenClaw 部署並跑）

## 0. 先講最重要三件事

1. **`.dat` 破解成功**（見 §2）。老闆交來的 `PowerHistory_D1_8.dat` 已 100% 解出二進位格式，
   拿到 **1,933 行 D1 全精度數據（2018-12-06 → 2026-05-21）**，是目前最強的 ground truth。
2. **公式骨架已確定**（見 §2）。剩下唯一未知＝每次「比較」的精確定義。
   要釘死它，只有一條路：**同一部 MT4、同一個 tick** 同時記錄「原作顯示值」＋「價格 OHLC」。
3. **本包三件貨**（見 §1）。其中 `CcyPower_TierB_Probe.mq4` 是這次的核心，請務必跑。

## 1. 交付物（本目錄）

| 檔 | 類型 | 放邊 | 用途 |
|---|---|---|---|
| `CcyPower_TierB_Probe.mq4` | **EA**（不是指標） | `MQL4\Experts\` | 同時匯出原作面板值＋33 symbol OHLC |
| `CurrencyPower_v3_MQ4.mq4` | 指標（v3.08-MQ4） | `MQL4\Indicators\` | 階段 0 防禦版（見 §3 更正） |
| `CurrencyPower_v3_S0.mq5` | 指標（v3.12） | `MQL5\Indicators\` | 同上，MT5 版 |

## 2. 已確定的結論（可直接寫進任何文檔，有證據鏈）

### 2.1 `PowerHistory_D1_8.dat` 格式（已逆向，100% 解碼）

```
int32   count = 9
char[4] × 9     貨幣碼：  EUR GBP AUD NZD CHF JPY XAU CAD USD
record × N (80 bytes each):
    int64   epoch seconds (UTC 00:00)
    double × 9       全精度（不是 2dp 捨入）
```

- 檔案 154,680 bytes；header 40 bytes；stride 80 bytes；**1,933 筆，完全消耗無殘留**
- 日期範圍：2018-12-06 → 2026-05-21（D1 序列，含週末跳過）
- 樣本末筆：2026-05-21 → EUR 3.875 / GBP 6.2857 / AUD 3.125 / NZD 3.4286 /
  CHF 4.2857 / JPY 3.375 / **XAU 3.25** / CAD 5.4286 / USD 7.0

### 2.2 公式骨架（lattice 反推，誤差 1e-15 級）

```
Power_c = Σ(每個夥伴的 up 計數) / N_c

    up 計數 ∈ 0..9 的整數        （Period=10 → C = Period−1 = 9 次比較）
    N_c = 7 個其他外幣 + (1 如果券商有 XAU該幣 這條交叉)   → 7 或 8
    XAU 自己 = Σ(每條黃金交叉的 up 計數) / G

    刻度：0 .. 9，中點 4.5
```

證據：
- 全精度下 `值 × 7` 或 `值 × 8` **精確為整數**（GBP/NZD/CHF/CAD 誤差 7e-15）
- 值 `4.5` 在 GBP/NZD/CHF/CAD **1,933 行 0 次**（分母 7 時數學上不可能），
  在 EUR/AUD/JPY/USD **出現 44–69 次**（分母 8）→ 完全對上
- 最大值恰為 **9.00**（GBP、XAU 各出現）且從未超過 → C = 9
- `.dat` 分段顯示黃金交叉隨時間增長：
  `2018-12-11 G=2 {AUD,USD}` → `2021-04-14 G=3 {+EUR}` → `2023-11-23 G=4 {+JPY}`
- 老闆 2026-11-18 交回的 Market Watch 名單完美對上：
  **Vantage 4 條**（XAUAUD/EUR/JPY/USD）↔ `.dat` 末段 G=4 成員；
  **Alpari 5 條**（多 XAUGBP）↔ `timeline.json` 中 GBP 出現 /8、XAU 落在 /4+/5
- 創作者那句「黃金報價越多越準」得到實證：每多一條交叉，就多一個幣由 /7 升 /8

### 2.3 仍未釘死：`up` 的精確定義（本輪要解決）

只剩 3 個自由度：
- (a) 相鄰兩根收盤比較 vs 收盤對移動平均線
- (b) 只用已收 K 棒 vs 含正在跳動那根
- (c) 平盤算 +1 / −1 / 0

**靠擬合已到天花板（~5% 逐值命中）**，因為 feed 不同源。必須靠 Tier B。

## 3. ⚠️ 重要更正（我方上一輪報錯，請一併轉達老闆）

我 2026-11-18 早前報告「v3 有 12/28 對符號反轉 bug、修後 Spearman 0.30→0.69」——
**該結論錯誤**。成因：我測試腳本用字母序自行枚舉 pair，而不是用指標本身的 `Pairs[]` 陣列。
用正確 `Pairs[]` 重跑：

```
indicator Pairs[] length: 28
DIRECT  28/28
REVERSED 0/28
MISSING  0/28
```

**Alpari / Vantage 都沒有符號反轉問題。** v3 現狀對原作：H4 Spearman **0.686**、H1 **0.622**、
逐幣平均 r **+0.66**（比我先前報的好得多）。

因此階段 0 的定位改為：**防禦性加固**（換券商／缺正向對時才生效），不是修 bug。
它會在 OnInit 的 Journal 印出反向清單，本身也是診斷工具。**請勿在任何對外文檔寫「修了 12/28 bug」。**

## 4. 請 OpenClaw 執行的步驟（優先次序）

### STEP 1（核心）：跑 Tier B 診斷 —— MT4-2（Alpari demo，帳號 252031466）

> ⚠️ 一定要選 MT4-2。理由：`ccy_power_reader.csv`（11.1 MB，07:41 仍在寫）只在 MT4-2，
> 代表原作指標在 MT4-2 持續運行、有活數據。MT4-1（live）的 CP 已停 2026-06-10、MT4-3 完全冇。

1. 把 `CcyPower_TierB_Probe.mq4` 放入
   `...\Terminal\A06E6395D71C5597BD3D45E90C51C549\MQL4\Experts\`
2. MetaEditor（F4）→ 開檔 → **F7 編譯**，要求 **0 errors**。
   若有 error／warning，**原文貼回**（我方本機無 MT4 無法預編譯）。
3. 開一張 **EURUSD** 圖，時間框設 **H1**
4. 掛上原版 **`CCY Power Indicator v1.00`**
   - input：`Timeframe (close price) = H1`、`Period = 10`、**All Power** 模式
5. 同一張圖拖上 `CcyPower_TierB_Probe`
   - `InpTF = 60`（＝H1，必須與第 4 步一致）
   - `InpPeriod = 10`、`InpBars = 14`、`InpPollSeconds = 60`、`InpEveryPoll = true`
6. 讓它跑 **至少 10 分鐘**（每 60 秒寫一行 → 10 行以上）
7. 交回 4 個檔（全部在 `MQL4\Files\`）：
   ```
   ccyprobe_panel.csv
   ccyprobe_bars.csv
   ccyprobe_candidates.txt      ← 最關鍵：原作 object 的真實命名與文字
   ccyprobe_objects.txt         ← 若存在就一併交（沒有也可）
   ```

**若 Journal 出現 `panel 0/9` 或 `panel <9/9`**：不要緊，`ccyprobe_candidates.txt` 就是為此而設。
把它交回，我方照真實命名改 parser。

### STEP 2：確認 `.dat` 來源

老闆已交一份 `PowerHistory_D1_8.dat`（末筆 2026-05-21）。請確認：

1. 三個終端的 `MQL4\Files` 裡，有無任何 `PowerHistory_*.dat`？
   （我方從檔案層實查三個終端都冇，但請再確認一次，尤其 MT4-2 因為它正在寫 CSV）
2. 若有，**逐個列出**：檔名、大小、修改時間。
   特別留意是否有 **其他 Timeframe** 版本（例如 `PowerHistory_H1_8.dat`、`PowerHistory_H4_8.dat`）。
3. 若找到任何 `PowerHistory_*.dat`，請**原檔上傳**到
   `exchange/from_openclaw/20261118_<hhmm>_CCY_Power_PowerHistory樣本/`

> 價值：若拿到 H1/H4 版本，等於一次拿到 7.5 年多時間框 ground truth，可大幅加速擬合。

### STEP 3（可並行）：確認 MT4-1（live）的 CP 為何停更

老闆提到「live 機反而斷咗更新」。這是資料一致性風險（live 與 demo 兩套數不同源）。
請查：
1. MT4-1（帳號 7311920）的 `ccy_power_backfill.csv` 為何停在 2026-06-10 08:02
2. 該機的 CCY Power Reader EA 是否仍在運行（Journal 有無錯誤）
3. 結論：修還是不修（若要修，屬 data lane 職責，本包不含 patch）

## 5. 收到 CSV 後我方會做什麼

1. 先驗 `ccyprobe_candidates.txt`：確認我方抽到的 9 個面板值與原作顯示一致
2. 用**同一 tick** 的 bar 數據跑遍所有候選 `up` 定義（同源同 feed）
3. 逐值命中率應由 ~5% 跳到接近 100%
4. 命中後立即出階段 1：`CcyPowerCount.mq4`（0–9 晶格、`Σup/N`、N 動態），公式完全確定

## 6. 本包不含（避免誤解）

- ❌ 沒有改動 `exchange/from_openclaw/` 任何歷史正本（那是已交貨的審計線）
- ❌ 沒有改 `docs/`、沒有改 `sidebar.js`、沒有新頁面 → 不需要跑 QA gate
- ❌ 沒有碰 `data/ccy_power_history.db`
- ❌ 沒有 commit 到 `docs/`（本包純 `exchange/` 信件＋源碼）

— ZCODE_w（機窗 lane）2026-11-18 08:15 HKT
