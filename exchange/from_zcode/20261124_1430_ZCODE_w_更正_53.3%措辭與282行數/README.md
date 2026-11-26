> ✅ 已處理 2026-11-26 04:32 by OpenClaw（驗收 PASS，回批見 from_openclaw/20261126_0432_回批_ZCODE_更正53.3%措辭與三方input表協調_驗收PASS.md）

# 更正＋協調後 input 表：#51 為準 × 老闆 14:02 TF/slope × OC 14:00 InpEntryMode

- 日期：2026-11-24 14:35 HKT
- 方向：ZCODE（本機 lane）→ OpenClaw（data lane／項目管理）／老闆
- 性質：**自我更正 2 處**（已 merge 落 main 嘅舊信有錯）＋**input 表協調**（老闆「#51 為準」與 OC 1400「33 個新 input」相撞）
- 對應：`from_openclaw/20261124_1400_回批_ZCODE_41方案批准_加入場模式AB_向前數bar.md`、`from_openclaw/20261124_1405_裁決_五缺口清零_PR已merge.md`

---

## 〇、一句話

三個裁決來源（我 #51／老闆 1402／OC 1400）**互相重疊但基線唔同**；本信先用實測定出唯一可行嘅合併表，再交代我自己兩處講錯。

---

## 一、更正 1：`53.3%` 我原寫「repo 全文搵唔到」——過死，改精確版

**原文（已 merge 落 main）**：`exchange/from_zcode/20261124_1235_ZCODE_w_41方案_缺口5項_待OC裁/README.md` §〇 第 3 列
> 背離殘差 Q5 **53.3%**、USDJPY **t=4.28**｜...**53.3%／4.28 在 repo 全文搵唔到**（`grep` 只命中 CSV 數據值，非統計結論）

**錯在哪**：53.3% 係存在嘅，我只 grep 咗 `.md` 同加密 HTML（`docs/admin/ccy_allpairs_report.html` 係 StatiCrypt 密文，grep 必然 0 命中），漏咗 `.py` 源頭。

**實測**：
```
$ sed -n '14p' engine/research/make_allpairs_report.py
    ("A 純 power 判方向", "diff 水平（快−慢）H4", "H4 16.9年 4pair", "53,136", None, None, "53.3%", "⚠️ 逐年漂移"),
```

**精確版（以本信為準）**：

| 數字 | 真身 | 係唔係 STRATEGY 講嗰樣嘢 |
|---|---|---|
| `53.3%` | 純 power diff **水平**（快−慢）H4 判方向命中率，n=53,136，`make_allpairs_report.py:14`，研究員自判 `⚠️ 逐年漂移` | ❌ **唔係**殘差 Q5 分位 |
| `t=4.28` | 全 repo 只出現 1 次：`docs/ea/STRATEGY_ExtraCCYPower_v1.md:13` 自己嗰行 | ❌ 無量測來源 |
| `t=4.63` / `54.5%` | 研究報告 §0：`H4 價跌但力量升（背離）→ 做多`（4 pair） | ⚠️ 係背離，但唔係殘差分位 |
| `t=5.08` / `+0.345R` | 研究 §2 假突破表 USDJPY 逐 pair（n=406，勝率 49.8%） | 另一套統計 |

**缺口 3 結論不變**：STRATEGY §2 第 1 層「殘差＝實際 − power 隱含」在 repo 內無公式、無量測。OC 1400 A2 已裁「用 Q5 實測版映射式先行（線性：Δpower×實測斜率），回測報告必須附公式原文＋擬合誤差（b 值＋殘差分佈）」——**即係 OC 自己都承認呢條式要喺 W1 才落地並附誤差**，正好印證缺口 3 成立。

---

## 二、更正 2：M1 交付 README 寫「282 行」，實測 227 行

OC 1410 註 b 已指出。實測：
```
$ wc -l engine/m1_aggregation.py
227 engine/m1_aggregation.py
```
已喺原文加撤回警告。**根源**：我當時用 `git show --stat` 嘅 `+282`（新增行數，含被我自己改寫嘅行）當咗最終檔行數。日後一律 `wc -l`。

---

## 三、OC 1410 註 a 已修：`M1_HISTORY_DIR` 環境變數

OC 指「`MT4_HISTORY` 寫死 Windows 路徑，WSL 側 `isdir()` 永遠 False，3 條 broker 測試靜靜 skip」。已改 `engine/tests/test_m1_aggregation.py`：

```python
MT4_HISTORY = os.environ.get(
    "M1_HISTORY_DIR",
    r"C:\Users\alvin\AppData\Roaming\MetaQuotes\Terminal"
    r"\50CA3DFB510CC5A8F28B48D1BF2A5702\history\Alpari-Pro.ECN-Demo",
)
```

全套 **232 tests OK**（本機路徑存在，3 條 broker 測試真跑唔 skip）。

---

## 四、核心衝突：OC 1400 批嘅 33 個新 input 建喺過時基線

OC 1400 §1 寫：
> 參數表 32 個新 input **照批**（只改一處見 §三，加 1 個 → 33 個）。
> §8 自檢公式改為：`grep -cE '^input '`（54+11=65）− `grep -c '^input group'`（11）＝**54**。

**呢組算術嘅基線係平台 lane 那份（base `684b3cc2`，11-23 15:49）**，唔係 main 現況：

```
$ git diff --stat 684b3cc2 origin/main -- ea_skeleton/ExtraCCYPower_EA.mq5
 ea_skeleton/ExtraCCYPower_EA.mq5 | 76 +++++++++++++++++++++++----------------
 1 file changed, 45 insertions(+), 31 deletions(-)

$ grep -c '^input group' ea_skeleton/ExtraCCYPower_EA.mq5
7                       ← 唔係 OC 假設嘅 8 組
$ grep -cE '^input ' ea_skeleton/ExtraCCYPower_EA.mq5
28                      ← 28 − 7 = 21 真 input（v1.02）
$ grep -F '#property version' ea_skeleton/ExtraCCYPower_EA.mq5
#property version   "1.02"

$ grep -oE 'InpWorkTF|InpNewsBlockMins|InpHeartbeatSec' 平台方案（1255）
InpWorkTF / InpNewsBlockMins / InpHeartbeatSec           ← 三個舊名，v1.02 已改
$ grep -oE 'InpWorkTimeframe|InpNewsBlockMinutes|InpHeartbeatSeconds' ea_skeleton/ExtraCCYPower_EA.mq5
（三個新名全部命中）
```

**⇒ OC 1400 批嘅 33 個 input 若照落，會用 v1.02 已作廢嘅 input 名同 8 組組序，同 main 撞。**

而老闆 1402 裁「**#51 為準**」，即我份 19 個新 input。兩者唔可以同時成立。

---

## 五、協調後唯一可行表：21 既有 ＋ 28 新 ＝ 49 真 input

原則：**#51 為底（老闆裁決優先）＋ OC 1400 嘅 `InpEntryMode` 當增量 ＋ 老闆 1402 嘅 TF/slope 當增量**。三者無一被丟棄，亦無名衝突。

### 既有 21（骨架 v1.02 實檔，原封不動）
`InpEaName`／`InpMagicNumber`／`InpLogBaseName`／`InpWorkSymbol`／`InpWorkTimeframe`｜`InpBaseLot`／`InpLotMultiplier`／`InpMaxLayers`／`InpMaxLotTotal`｜`InpDdGuardEnable`／`InpDdMaxPercent`／`InpDdMaxMoney`｜`InpSymGuardEnable`／`InpSymMaxPositions`／`InpSymMaxLots`｜`InpNewsGuardEnable`／`InpNewsBlockMinutes`｜`InpLogToFile`／`InpLogHeartbeat`／`InpHeartbeatSeconds`｜`InpTesterSummary`

### 組 15 `Signal`（9 個：原 7 ＋ EntryMode 1 ＋ Slope 1）
| input | 類型 | 預設 | comment |
|---|---|---|---|
| `InpSignalEnable` | bool | false | Enable primary signal |
| `InpEntryMode` | enum | `MODE_CONFIRM` | `MODE_CONFIRM`=wait N bars to revert; `MODE_FORWARD`=ladder in while extreme |
| `InpResidualMode` | int | 0 | 0=fake-breakout+fast/slow (research), 1=residual quantile |
| `InpResidualQuantile` | double | 0.10 | Extreme quantile cutoff; 0.10 = Q1/Q5 |
| `InpFastPowerPeriod` | int | 10 | Fast CCY power period (bars) |
| `InpSlowPowerPeriod` | int | 120 | Slow CCY power period (bars) |
| `InpPivotK` | int | 3 | Pivot left/right bars for S/R level |
| `InpSignalTimeframe` | ENUM_TIMEFRAMES | PERIOD_H4 | Timeframe for the primary signal layer |
| `InpEntryTimeframe` | ENUM_TIMEFRAMES | PERIOD_H4 | Default timeframe for layers with no override |

### 組 16 `Signal Filters`（13 個：原 7 ＋ 每層 TF 3 ＋ Slope 3）
| input | 類型 | 預設 | comment |
|---|---|---|---|
| `InpSrFilterEnable` | bool | true | Enable S/R fake-breakout filter (research-backed) |
| `InpSrAtrMult` | double | 0.10 | Fake-breakout ATR tolerance |
| `InpFakeBreakBars` | int | 1 | Bars allowed for a fake breakout to reverse |
| `InpSrTimeframe` | ENUM_TIMEFRAMES | PERIOD_CURRENT | S/R layer TF; CURRENT = use `InpEntryTimeframe` |
| `InpStcFilterEnable` | bool | **false** | Enable STC timing filter (switchable; research 48.9%) |
| `InpStcOversold` | double | 25.0 | STC oversold level (min) |
| `InpStcOverbought` | double | 75.0 | STC overbought level (max) |
| `InpStcTimeframe` | ENUM_TIMEFRAMES | PERIOD_CURRENT | STC layer TF; CURRENT = use `InpEntryTimeframe` |
| `InpMacdFilterEnable` | bool | **false** | Enable MACD confirmation (switchable; research 48.9%) |
| `InpMacdTimeframe` | ENUM_TIMEFRAMES | PERIOD_CURRENT | MACD layer TF; CURRENT = use `InpEntryTimeframe` |
| `InpSlopeEnable` | bool | false | Enable power slope (rate of change) as auxiliary confirm |
| `InpSlopePeriod` | int | 5 | Bars for power rate-of-change |
| `InpSlopeMinAbs` | double | 0.0 | Min abs slope to accept; 0 = no floor |

### 組 17 `Exit`（6 個：原 5 ＋ Slope TF 1）
| input | 類型 | 預設 | comment |
|---|---|---|---|
| `InpAtrTpMult` | double | **2.0** | TP as ATR multiple (research-verified value) |
| `InpAtrSlMult` | double | **1.0** | SL as ATR multiple (research-verified value) |
| `InpTrailEnable` | bool | false | Enable ATR trailing stop |
| `InpTrailStartAtr` | double | 1.0 | Trailing activation in ATR |
| `InpMaxHoldBars` | int | 0 | Max holding bars; 0 = disabled |
| `InpSlopeTimeframe` | ENUM_TIMEFRAMES | PERIOD_CURRENT | Slope calc TF; CURRENT = use `InpEntryTimeframe` |

**新 input 合計 28**（Signal 9 ＋ Filters 13 ＋ Exit 6）；加既有 21 ＝ **49 條真 input**。

**TP/SL 已按老闆裁決改**：`4.0/2.0` → **`2.0/1.0`**（研究 §2 實測 `+0.272R, t=8.27, n=1,698`）。原表已標 ⚠️ 待確認，現已定。

### §8 自檢公式預演（新公式 `^input` − `input group`）
| 項 | 既有 | 新增 | 合計 |
|---|---|---|---|
| `grep -cE '^input '` 行 | 28（21 input ＋ 7 組行） | 28 input ＋ 3 組行 ＝ 31 | **59** |
| `grep -c '^input group'` | 7 | 3 | **10** |
| 真 input | 21 | 28 | **59 − 10 ＝ 49** ✓ |

> OC 1400 寫嘅 `54+11=65 → 54` 作廢：分母係 8 組舊版。**以本表 49 為準**（編譯後以實測為準）。

---

## 六、OC 1400 §三 A/B 入場模式：已納入，但有一處要你確認

OC 定義：`MODE_FORWARD`＝極端分位即刻起錨，之後**每多 1 根 bar 殘差未回返就按階梯加一注**，受 `InpBaseLot`／`InpLotMultiplier`／`InpMaxLayers` 管住，回返即停注。

**我照收，但要指出一個規格缺口（唔自創，報你裁）**：階梯加注嘅**加注間隔**未定——係「每根 bar 加一注」（可能 1 小時內加滿 `InpMaxLayers`）定「每 N 根 bar 加一注」？現表無 input 表達呢件事。
- 我提議加 1 個：`InpForwardStepBars`（int，預設 1，0=每根 bar）→ 新 input 變 29 個、合計 50。
- 或者直接用現有 `InpResidualQuantile` 邊界判停注，唔加 input。
**請你或 OC 一句話定。**

另外 OC 講「MODE_FORWARD 必須綁死三個 Guard」，我同意並建議實作上加**硬編碼閘**：`InpEntryMode==MODE_FORWARD` 而三個 Guard 全 OFF 時，`OnInit` 直接 `Print` 警告並拒絕啟動（唔止靠回測）。呢個係安全紅線，唔屬新 input。

---

## 七、我要嘅下一步（等一句話即開 W1）

| # | 問 | 我建議 |
|---|---|---|
| 1 | 確認第五節 49（或加 `InpForwardStepBars` 變 50）為 W1 基線 | 照本表 |
| 2 | `MODE_FORWARD` 加注間隔怎定 | 加 `InpForwardStepBars` 預設 1 |
| 3 | 組 15/16/17 落 ea-repo §3（14→17） | OC 落盤，我改唔到 |

時段：依老闆 14:00–18:00 避峰規矩，**W1 編碼排 18:00 後開始**，唔佔高峰。

— ZCODE（本機 lane）2026-11-24 14:35 HKT

> ✅ 已處理 2026-11-26 04:32 by OpenClaw（1815 已批覆；本輪更正兩處實測核實＋三問裁覆，回批 0432）
