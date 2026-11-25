# EA Skeleton — card #41 (S4), lane zcode-local

- 交付：ZCODE（本機 lane）
- 卡片：`#41 [S4] MT5 EA 骨架（等老闆 O1–O4 策略規格）`
- 落點：TSA repo `ea_skeleton/`（OC 2026-11-23 21:05 裁決：`ea_skeleton/` 即本機工作位，ea-repo git 通道唔急開）
- 產物：`ExtraCCYPower_EA.mq5`
- **版本（目前）：v1.03**（策略填肉，SPEC v0.1／OC 2026-11-25 0815 裁決）——v1.00 PR #43 首版；v1.01 OC 21:05 丁節三裁決；v1.02 老闆 11-24 08:15 `Lot Sizing`／`Backtest` 排 §3 第 13／14 位；**v1.03＝按 SPEC v0.1 填 entry/exit：假突破 fade＋快慢 power 雙過濾、R=1×ATR(14)、SL=0.5R／TP=1R、日蝕 3R、CTrade 落單、外部 power CSV reader（A1）；三 Guard 仍預設 OFF**

## 一、編譯（v1.03）

```text
$ MetaEditor64.exe /compile:...\MQL5\Experts\ExtraCCYPower_EA.mq5 /log
Result: 0 errors, 0 warnings, 1327 ms elapsed, cpu='X64 Regular'
```

- 817 行 / 29,862 bytes
- sha256 `f730413cb9cb07e3aa5c37a8d7bc80eb25df3374d8c74b2b1377d3a3e5d11187`
- 版本四處鎖步（AGENTS.md §6）：`#property version "1.03"`｜`#define EA_VERSION "1.03"`（banner 用）｜`#property description`（含 SPEC v0.1）｜本 README
- §8 自檢：`^input ` 42 − `input group` 9 ＝ **33 真 input**（v1.02 既有 21 ＋ 新增 12：Signal 8＋Exit 4；OC 0815 明列 9 個必備 input 全數在內）；`___` 零命中

### v1.03 新增 input（照 OC 0815 裁決）

| group | input | 預設 | 來源 |
|---|---|---|---|
| Signal | `InpFakeBreakBars` | 3 | 假突破 N 根收回 |
| Signal | `InpPivotK` | 3 | W1 `pivots(k=3)` |
| Signal | `InpAtrTol` | 0.10 | W1 `DEFAULT_ATR_TOL` |
| Signal | `InpFastPowerTF` | `PERIOD_H1` | SPEC 快=H1 |
| Signal | `InpSlowPowerTF` | `PERIOD_H4` | SPEC 慢=H4 |
| Signal | `InpFastPowerPeriod` | 10 | 研究 H4_10 |
| Signal | `InpSlowPowerPeriod` | 120 | 研究 H4_120 |
| Signal | `InpPowerDir` | `ccy_power` | A1 路徑 `CCYPOWER_<SYM>_<TF>.csv` |
| Exit | `InpSlR` | 0.5 | R=1ATR，SL=0.5R |
| Exit | `InpTpR` | 1.0 | TP=1R |
| Exit | `InpDailyMaxR` | 3.0 | 日蝕 3R |
| Exit | `InpCompareTp2Sl1` | false | 回測對照組 TP=2ATR/SL=1ATR |

### 與 W1 Python 對拍（一對一移植，零新邏輯）

- `atr()` → `iATR(14)` + `CopyBuffer`（暖期未就緒回 false，唔回 0，對應 W1 `None`）
- `pivots(k)`／`fake_breaks()` → `DetectFakeBreak()`（k 根 neighbours、收回確認、`atr_tol`）
- `power_agrees()` → `PowerAgrees()`（同號才入，背離唔入）
- slope = `power_now − power_prev`（OC 0120 逐字：唔係迴歸）→ `ReadPowerDiff()` 讀 A1 CSV 最近兩行

## 二、版本沿革（v1.00→v1.02 零策略改動；v1.03 首次填策略，分開 commit 原則照舊）

| # | 項目 | v1.00 | v1.01 |
|---|---|---|---|
| 1 | Group 名對齊 AGENTS.md §3 | `Identity`／`Symbol and Timeframe`／`Risk - Drawdown Guard`／`Risk - Symbol Guard`／`Risk - News Guard`／`Logging`（6 個名全不在 §3） | `General`（Identity＋Symbol and Timeframe 併入）／`DD Guard — Account`／`Symbol Guard`／`News Guard`／`Diagnostics`（原 Logging）—— 全部按 §3 標準名 |
| 2 | 空組 | — | **唔宣告**（OC D1「有 input 先開組」）：Display／Refresh & Recording／Data Filter／Trade Snapshot／Telegram／Backup & Recovery 一律不開；`DD Guard — Per Symbol` 亦不開（本骨架 DD 只讀 `ACCOUNT_BALANCE`／`ACCOUNT_EQUITY`，屬帳戶層，無逐 symbol DD input） |
| 3 | `Lot Sizing`／`Backtest` | 原位（Identity 之後） | v1.01：維持原名原位待批；**v1.02：老闆 11-24 08:15 批為 §3 第 13／14 位（`Diagnostics` 之後），已排入 §3 次序** |
| 4 | STARTED banner | `SKELETON: v0.10 attached, symbol=... tf=...`（版本字串與 `#property` 不一致） | `PrintFormat("%s STARTED v%s on %s %s", InpEaName, EA_VERSION, symbol, tf)`，只在 `OnInit` 印一次（OC D2）；另加一行 `SKELETON: orders=DISABLED (no O2 spec)` |
| 5 | 縮寫還原（§1.1） | `InpWorkTF`／`InpHeartbeatSec`／`InpNewsBlockMins` | `InpWorkTimeframe`／`InpHeartbeatSeconds`／`InpNewsBlockMinutes`（引用點一併改，共 6 處） |
| 6 | 單位記號（§2.6） | 29 行 input 只有 1 行帶單位 | 7 行補 `(lots)`／`(%)`／`($)`／`(count)`／`(min)`／`(sec)`；`InpDdMaxPercent` 的 `percent` 字面改 `(%)` |

**無改動**：手數骨架 `CalcLayerLot`、三組風控 hook 邏輯、CSV 日誌 10 欄、`OnTester` 11 欄、`PrintMissingItems`（除 G3 措辭更新）、`ValidateInputs` 的檢查條件（只改錯誤訊息中的變數名以配合縮寫還原）。

## 三、現時 group 次序與 §3 對照

```
實測：grep -n '^input group' ea_skeleton/ExtraCCYPower_EA.mq5（v1.02）
33: input group "General"              ← §3 第 1
40: input group "DD Guard — Account"   ← §3 第 6
45: input group "Symbol Guard"         ← §3 第 8
50: input group "News Guard"           ← §3 第 9
54: input group "Diagnostics"          ← §3 第 12
59: input group "Lot Sizing"           ← §3 第 13（老闆 11-24 08:15 批）
65: input group "Backtest"             ← §3 第 14（老闆 11-24 08:15 批）
```

有 input 的 §3 組按 §3 次序**遞增排列**（1 → 6 → 8 → 9 → 12），中間不插空組。

## 四、驗收自檢（REQUIREMENT §2.5 A 組＋AGENTS.md §8）

| # | 條件 | 實測 |
|---|---|---|
| 1 | 編譯 0 errors 0 warnings | ✅ `Result: 0 errors, 0 warnings, 848 ms` |
| 2a | 無 `___` 假分隔 | ✅ `grep -c '___'` = **0** |
| 2b | 無未註解 input | ✅ **21/21** 有英文註解 |
| 2c | input 對數 | ✅ `^input` **28** − `input group` **7** = **21** 條真 input（按 OC 21:05 戊節建議的減法口徑） |
| 2d | comment ≤ 55 字元 | ✅ 0 條超標 |
| 3 | 風控預設全 OFF | ✅ `InpDdGuardEnable=false`／`InpSymGuardEnable=false`／`InpNewsGuardEnable=false` |
| 6 | `.set` 可載入 | 未能驗（無真 SET 對應此 input 集，見第六節缺口 2） |

**✅ AGENTS.md §8 自檢式已修**：老闆 11-24 08:15 批准（OC 0825 D2）改為「`^input` 減 `input group` ＝ 真 input 數」。ea-repo 正本由 OC 落 patch（我對 ea-repo 無寫入權）；TSA 副本見 `exchange/from_openclaw/20261124_0825_規範patch_supply/`。本 README 一直用減法口徑。

## 五、出貨時請對照的「待填」清單

`OnInit()` 每次都印以下 `MISSING:` 行（v1.02 原文）：

```text
MISSING: O1 - EA name is empty, filename and .set name are undecided   ← 僅當 InpEaName 為空
MISSING: O2 - strategy spec (entry/exit, grid or not, indicators, TF) not supplied
MISSING: O2 - no order-sending code exists in this build, by design
MISSING: O3 - parameter list must follow the real .set fields; not supplied yet
MISSING: O4 - acceptance thresholds (backtest numbers) not settled by owner
MISSING: G3 - group names now follow ea-repo AGENTS.md section 3 for the groups
MISSING: G3 - that carry inputs; groups without inputs are not declared (OC 21:05 D1).
```

| # | 項目 | 現狀 |
|---|---|---|
| O1 | EA 名 | ✅ `ExtraCCYPower_EA` |
| O2 | 策略規格 | ❌ **未見**（`ea_strategy_masterplan.html` 掃 `ExtraCCY`／`POWER DIFF`／`entry`／`假突破`／`SPEC` 全 0 命中；`tsa-risk-analyzer/` 0 檔） |
| O3 | 參數清單 | ⚠️ 2,861 個 `.set` 無一份對應 ExtraCCY Power；現 21 個 input 為通用框架 |
| O4 | 達標線 | ⚠️ 一期可判（0/0＋空策略平坦 equity）；二期需 O2 |
| G3 | AGENTS.md §1/§3 | ✅ 已到手；§3 組名＋次序全對齊（含第 13／14 位）；§1.1 縮寫已還原 |

## 六、缺口（需 OC／老闆裁決，我沒有自行補）

### 缺口 1（已解）

`Lot Sizing`／`Backtest` 組名與次序已由老闆 2026-11-24 08:15 裁決（OC 0825 D1）：兩名照用、列 §3 第 13／14 位。v1.02 已按此排入。

### 缺口 2：O3 參數對映

現 21 個 input 是**通用 EA 框架**（身份／符號／手數／三組風控／日誌／回測），**唔係** ExtraCCY Power 的 SET 欄位。
強行對映等於自創參數——按 O3 規矩報 MISSING 唔自填。

### 缺口 3：News Guard 無資料源

`InpNewsGuardEnable` 接口已實作，但**冇綁任何財經日曆**（`CalendarValueHistory` 一律冇寫）。
開啟時 `RiskGuardAllow()` 唔會真的擋單。**要不要一期先綁 `CalendarValueHistory`？**

### 缺口 4：`DD Guard — Per Symbol` 無 input

§3 有第 7 組 `DD Guard — Per Symbol`，但本骨架 DD guard 只讀帳戶層 `ACCOUNT_BALANCE`/`ACCOUNT_EQUITY`，**冇逐 symbol DD 的 input**，故按 OC D1「有 input 先開組」不宣告。
**若要真做逐 symbol DD，需 O2 或另行派工。**

## 七、紅線自查（v1.01 實測）

| 紅線 | 狀態 |
|---|---|
| 唔准寫 entry/exit／格網／指標邏輯 | ✅ `OrderSend`=0／`CTrade`=0／`iRSI`=0／`iATR`=0／`iCustom`=0／`OnTrade`=0 |
| 風控預設全 OFF | ✅ 三組全 `false` |
| 唔准將帳號／token／密碼寫入源碼 | ✅ 只有 `InpMagicNumber`（用戶自填） |
| 未能編譯通過＝唔算交付 | ✅ 已 0/0 |
| 不得同一 commit 混入「改名＋邏輯修改」（§7） | ✅ 本版只改名／改註解／加 banner，**零邏輯改動** |

## 八、未驗（我交唔到）

- **`.set` 載入測試（A6）**：冇對應 SET 檔，無法驗「改名後值無丟失」
- **回測矩陣（A4）**：`ea-test-kit/scripts/run_matrix.py` 不在此 repo、本機亦無；空策略矩陣無意義（要 O2）
- **八年回測（A5）**：需 O2 策略與 8 年 tick/bar 數據源
- **人眼閘（B7/B8）**：需在 MT5 終端掛載後人工看參數視窗 group 次序；本機只有 Alpari `D0E8209F…`，未掛載執行

— ZCODE（本機 lane）2026-11-24
