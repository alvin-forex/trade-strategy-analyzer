# EA Skeleton — card #41 (S4), lane zcode-local

- 交付：ZCODE（本機 lane）
- 卡片：`#41 [S4] MT5 EA 骨架（等老闆 O1–O4 策略規格）`
- 落點：TSA repo `ea_skeleton/`（OC 2026-11-23 21:05 裁決：`ea_skeleton/` 即本機工作位，ea-repo git 通道唔急開）
- 產物：`ExtraCCYPower_EA.mq5`
- 版本：**v1.01**（v1.00 為 PR #43 首版；v1.01 按 OC 21:05 丁節三項裁決改 group／banner／縮寫／單位）

## 一、編譯（v1.01）

```text
$ "/c/Program Files/MetaTrader 5/MetaEditor64.exe" /compile:ea_skeleton/ExtraCCYPower_EA.mq5
Result: 0 errors, 0 warnings, 848 ms elapsed, cpu='X64 Regular'
```

- 509 行 / 18,811 bytes
- sha256 `6369c3bdc6a106c4b29f1339ae4785b969b820e3288e46c3a2b1b3e6b11061e4`
- 版本四處鎖步（AGENTS.md §6）：`#property version "1.01"`｜`#define EA_VERSION "1.01"`（banner 用）｜`#property description`｜本 README

## 二、v1.01 改了什麼（全部按 OC 2026-11-23 21:05 丁節裁決，零策略改動）

| # | 項目 | v1.00 | v1.01 |
|---|---|---|---|
| 1 | Group 名對齊 AGENTS.md §3 | `Identity`／`Symbol and Timeframe`／`Risk - Drawdown Guard`／`Risk - Symbol Guard`／`Risk - News Guard`／`Logging`（6 個名全不在 §3） | `General`（Identity＋Symbol and Timeframe 併入）／`DD Guard — Account`／`Symbol Guard`／`News Guard`／`Diagnostics`（原 Logging）—— 全部按 §3 標準名 |
| 2 | 空組 | — | **唔宣告**（OC D1「有 input 先開組」）：Display／Refresh & Recording／Data Filter／Trade Snapshot／Telegram／Backup & Recovery 一律不開；`DD Guard — Per Symbol` 亦不開（本骨架 DD 只讀 `ACCOUNT_BALANCE`／`ACCOUNT_EQUITY`，屬帳戶層，無逐 symbol DD input） |
| 3 | `Lot Sizing`／`Backtest` | 原位 | **維持原名原位**（OC D1：兩組不在 §3 十二組，屬「新 group」，§2.3 要老闆批；未批前唔准自行刪改） |
| 4 | STARTED banner | `SKELETON: v0.10 attached, symbol=... tf=...`（版本字串與 `#property` 不一致） | `PrintFormat("%s STARTED v%s on %s %s", InpEaName, EA_VERSION, symbol, tf)`，只在 `OnInit` 印一次（OC D2）；另加一行 `SKELETON: orders=DISABLED (no O2 spec)` |
| 5 | 縮寫還原（§1.1） | `InpWorkTF`／`InpHeartbeatSec`／`InpNewsBlockMins` | `InpWorkTimeframe`／`InpHeartbeatSeconds`／`InpNewsBlockMinutes`（引用點一併改，共 6 處） |
| 6 | 單位記號（§2.6） | 29 行 input 只有 1 行帶單位 | 7 行補 `(lots)`／`(%)`／`($)`／`(count)`／`(min)`／`(sec)`；`InpDdMaxPercent` 的 `percent` 字面改 `(%)` |

**無改動**：手數骨架 `CalcLayerLot`、三組風控 hook 邏輯、CSV 日誌 10 欄、`OnTester` 11 欄、`PrintMissingItems`（除 G3 措辭更新）、`ValidateInputs` 的檢查條件（只改錯誤訊息中的變數名以配合縮寫還原）。

## 三、現時 group 次序與 §3 對照

```
實測：grep -n '^input group' ea_skeleton/ExtraCCYPower_EA.mq5
32: input group "General"              ← §3 第 1
39: input group "Lot Sizing"           ← 不在 §3（§2.3 新 group，待老闆批）
45: input group "DD Guard — Account"   ← §3 第 6
50: input group "Symbol Guard"         ← §3 第 8
55: input group "News Guard"           ← §3 第 9
59: input group "Diagnostics"          ← §3 第 12
64: input group "Backtest"             ← 不在 §3（§2.3 新 group，待老闆批）
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

**⚠️ AGENTS.md §8 原文自檢式仍有矛盾**（`grep -c '^input group'` 與 `grep -cE '^input '` 「對得上」→ 實測 7 vs 28 永遠對不上，因為 `^input ` 會匹配 group 行）。OC 21:05 戊節同意並已列老闆待辦改原文；本 README 用減法口徑。

## 五、出貨時請對照的「待填」清單

`OnInit()` 每次都印以下 `MISSING:` 行（v1.01 原文）：

```text
MISSING: O1 - EA name is empty, filename and .set name are undecided   ← 僅當 InpEaName 為空
MISSING: O2 - strategy spec (entry/exit, grid or not, indicators, TF) not supplied
MISSING: O2 - no order-sending code exists in this build, by design
MISSING: O3 - parameter list must follow the real .set fields; not supplied yet
MISSING: O4 - acceptance thresholds (backtest numbers) not settled by owner
MISSING: G3 - group names now follow ea-repo AGENTS.md section 3 for the groups
MISSING: G3 - that carry inputs; groups without inputs are not declared (OC 21:05 D1).
MISSING: G3 - 'Lot Sizing' and 'Backtest' are not among the twelve section 3 groups
MISSING: G3 - and stay pending the owner's verdict (AGENTS.md section 2.3).
```

| # | 項目 | 現狀 |
|---|---|---|
| O1 | EA 名 | ✅ `ExtraCCYPower_EA` |
| O2 | 策略規格 | ❌ **未見**（`ea_strategy_masterplan.html` 掃 `ExtraCCY`／`POWER DIFF`／`entry`／`假突破`／`SPEC` 全 0 命中；`tsa-risk-analyzer/` 0 檔） |
| O3 | 參數清單 | ⚠️ 2,861 個 `.set` 無一份對應 ExtraCCY Power；現 21 個 input 為通用框架 |
| O4 | 達標線 | ⚠️ 一期可判（0/0＋空策略平坦 equity）；二期需 O2 |
| G3 | AGENTS.md §1/§3 | ✅ 已到手並已按 §3 改名＋§1.1 縮寫還原；餘 `Lot Sizing`／`Backtest` 待老闆批組名 |

## 六、缺口（需 OC／老闆裁決，我沒有自行補）

### 缺口 1：`Lot Sizing`／`Backtest` 兩個新 group 的組名

OC 21:05 D1 只裁「維持原名原位，未批前唔准自行刪改」，並列老闆待辦。
**若老闆批准，請給正式組名（例如 `Lot Sizing` 是否改 `Trade Sizing` 之類）**；未批前我不動。

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
