# EA Skeleton — card #41 (S4), lane zcode-local

- 交付：ZCODE（本機 lane）
- 卡片：`#41 [S4] MT5 EA 骨架（等老闆 O1–O4 策略規格）`
- 落點：`ea_skeleton/`（OC 2026-11-23 14:45 裁決之過渡方案；`alvin-forex/ea-repo` 仍不可達）
- 產物：`ExtraCCYPower_EA.mq5`

## 一、編譯

```text
$ MetaEditor64 /compile:ea_skeleton/ExtraCCYPower_EA.mq5
Result: 0 errors, 0 warnings, 853 ms elapsed, cpu='X64 Regular'
```

- 495 行 / 17,890 bytes
- sha256 `b7ed0f160966359a6e49d3fc8b1a23cd8592e06dca2fd4f9b8d4b261331370b4`
- `#property version "1.00"`（初版寫 `0.10` 觸發 warning 68「incompatible with MQL5 Market」，改 `1.00` 後 0/0）

## 二、做了什麼（全部唔涉策略）

| 模組 | 內容 |
|---|---|
| input 框架 | 8 個 `input group`、21 個 `input`，全部 `Inp` 前綴＋PascalCase＋英文註解（實測 0 個超過 55 字元） |
| 手數骨架 | `CalcLayerLot(layer)`＝`base * mult^layer`，再經 `NormalizeLots()` 夾到 broker `VOLUME_MIN/MAX/STEP` |
| 風控 hook | DD Guard／Symbol Guard／News Guard 三組接口，**全部預設 OFF**（符合 REQUIREMENT 2.4＋驗收 A3） |
| 日誌 | `MQL5/Files/<base>_skeleton.csv`，10 欄固定表頭；`LogEvent()` 每個事件 flush |
| 回測入口 | `OnTester()` 寫 `<base>_tester_summary.csv`（11 個結構欄位） |
| 缺料申報 | `PrintMissingItems()` 逐項印 `MISSING:` |

## 三、驗收自檢（REQUIREMENT §2.5 A 組）

| # | 條件 | 實測 |
|---|---|---|
| 1 | 編譯 0 errors 0 warnings | ✅（見上） |
| 2a | 無 `___` 假分隔 | ✅ `grep -c '___'` = 0 |
| 2b | 無未註解 input | ✅ 21/21 有英文註解 |
| 2c | `grep -c '^input group'` 與 `grep -cE '^input '` 對得上 | ⚠️ **8 vs 29 — 見第五節缺口 1** |
| 3 | 風控預設全 OFF | ✅ `InpDdGuardEnable=false`、`InpSymGuardEnable=false`、`InpNewsGuardEnable=false` |
| 6 | `.set` 可載入 | 未能驗（無真 SET 對應此 input 集，見第五節缺口 2） |

## 四、出貨時請對照的「待填」清單

`OnInit()` 每次都印以下 `MISSING:` 行（原文）：

```text
MISSING: O1 - EA name is empty, filename and .set name are undecided   ← 僅當 InpEaName 為空
MISSING: O2 - strategy spec (entry/exit, grid or not, indicators, TF) not supplied
MISSING: O2 - no order-sending code exists in this build, by design
MISSING: O3 - parameter list must follow the real .set fields; not supplied yet
MISSING: O4 - acceptance thresholds (backtest numbers) not settled by owner
MISSING: G3 - ea-repo AGENTS.md section 1/3 is unreachable, input naming and
MISSING: G3 - group order below are a placeholder and must be re-ordered after spec lands
```

對應 O1–O4 的現狀（**本卡不自行填任何一項**）：

| # | 項目 | OC 14:45 宣告 | 實測 |
|---|---|---|---|
| O1 | EA 名 | 「CCY POWER 重製版叫 ExtraCCY Power」 | ✅ 已用 `ExtraCCYPower_EA` 作檔名與 `InpEaName` 預設 |
| O2 | 策略規格 | 「SPEC 由 OC 起草，初版隨骨架交付」 | ❌ **未見**：`grep -icE "STRATEGY_|specs/"` 只命中 2 個 `ea_strategy_masterplan.html`（掃過內容：`ExtraCCY`／`POWER DIFF`／`entry`／`假突破`／`SPEC` 全部 0 命中，唔係 O2 spec）；`tsa-risk-analyzer/` = 0 檔 |
| O3 | 參數清單 | 「照 SET 檔實際欄位」 | ⚠️ 2,861 個 `.set` 在 repo，但**冇一份對應 ExtraCCY Power**；骨架 input 為通用風控框架，非 SET 對映 |
| O4 | 達標線 | 「第一期＝工程底線；第二期＝8 年回測 MDD < 100%」 | ⚠️ 第一期可判（0/0＋空策略平坦 equity）；第二期需 O2 策略 |
| G2 | ea-repo | 「骨架落 `trade-strategy-analyzer/ea_skeleton/`」 | ✅ 已落 |
| G3 | ea-repo `AGENTS.md` §1/§3（命名硬規則＋group 次序） | 未提供 | ❌ `gh repo view alvin-forex/ea-repo` → `Could not resolve`；本機全碟無此檔；repo 內 `grep -ci ea-repo` 只命中 REQUIREMENT 自身 |

## 五、缺口（需 OC 裁決，我沒有自行補）

### 缺口 1：驗收 A2 的 `input group` 對數規則本身矛盾

REQUIREMENT §2.5 A2 寫：「`grep -c '^input group'` 與 `grep -cE '^input '` 對得上」。

但 `^input ` 會**同時**匹配 `input group "..."` 那 8 行，所以照字面永遠對不上（8 vs 29）。
我按「每個 input 都屬於某個 group」的理解做到 21 個 input 分屬 8 個 group。
**請裁決：A2 改為「無孤兒 input」（即每個 input 前必有 group），定係要求 `group` 數＝`input` 數？**

### 缺口 2：O3 參數對映

骨架的 21 個 input 是**通用 EA 框架**（身份／符號／手數／三組風控／日誌／回測），
**唔係** ExtraCCY Power 的 SET 欄位。真 SET 欄位要等 OC 提供對應 `.set` 或 REQUIREMENT 參數清單。
現階段若強行對映，等於自創參數——按 O3「缺欄報 MISSING」的規矩，我報 MISSING 而唔自填。

### 缺口 3：News Guard 無資料源

`InpNewsGuardEnable` 已實作接口，但骨架內**冇綁任何財經日曆**（`CalendarValueHistory` 之類一律冇寫）。
開啟時 `RiskGuardAllow()` 唔會真的擋單，只會在 log 註明。**要不要一期先綁 `CalendarValueHistory`？**

### 缺口 4：OC 引用的裁決存檔不在 repo

OC 寫「原答已導出存檔（workspace memory/exports/2026-11-18_General_topic_裁決對話.md）」。

```
$ git ls-tree -r --name-only origin/main | grep -c "2026-11-18_General_topic"
0
```

該檔在 OC 自己的 workspace，不在 `trade-strategy-analyzer`。**我讀唔到，故此只按 issue #41 留言的摘要落地。** 若原答有更細條款（特別是 O4 二期門檻細節），請把該檔貼出來或貼進 repo。

## 六、紅線自查

| 紅線 | 狀態 |
|---|---|
| 唔准寫 entry/exit／格網／指標邏輯 | ✅ 全檔 0 個 `OrderSend`／`CTrade`／`iRSI`／`iATR`／`iCustom`／`OnTrade` |
| 風控預設全 OFF | ✅ |
| 唔准將帳號／token／密碼寫入源碼 | ✅ 只有 `InpMagicNumber`（用戶自填） |
| 未能編譯通過＝唔算交付 | ✅ 已 0/0 |
| 只准改 `ea-repo/MQL5/`… | ⚠️ 本卡按 OC 過渡方案落 `ea_skeleton/`，與 REQUIREMENT §4「只准改 ea-repo」字面有衝突，以 OC 14:45 裁決為準 |

## 七、未驗（我交唔到）

- **`.set` 載入測試（A6）**：冇對應 SET 檔，無法驗「改名後值無丟失」。
- **回測矩陣（A4）**：`ea-test-kit/scripts/run_matrix.py` 不在此 repo、本機亦無；且空策略矩陣無意義（要 O2）。
- **八年回測（A5）**：同上，需 O2 策略與 8 年 tick/bar 數據源。
- **人眼閘（B7/B8）**：需在 MT5 終端掛載後人工看參數視窗 group 次序；我本機有 MT5（Alpari `D0E8209F…`）但**未掛載執行**過。

— ZCODE（本機 lane）2026-11-23
