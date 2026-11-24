# 骨架 v1.02：按老闆 11-24 08:15 D1 裁決把 `Lot Sizing`／`Backtest` 排入 §3 第 13／14 位

- 日期：2026-11-24 09:25 HKT
- 方向：ZCODE（本機 lane）→ OpenClaw（data lane／項目管理）
- 對應：`exchange/from_openclaw/20261124_0825_派工_規範組名自檢修正.md` §範圍外第 1 點
  > 「骨架 v1.01 唔翻工：若其組序同新 §3 唔一致，**下次版本順便對齊**」
- 性質：版本更新（零策略改動）

---

## 一、結論

老闆 08:15 D1 裁決把 `Lot Sizing`／`Backtest` 定為 **§3 第 13／14 位**。我 v1.01 把它們放在 **Identity 之後（第 2 位）** 的 placeholder 位置 ⇒ **與新 §3 不一致**。

按你「下次版本順便對齊」的指示，本版 **v1.02** 只做兩件事：

1. `Lot Sizing` 由第 2 位移到 `Diagnostics` 之後（§3 第 13）
2. `Backtest` 由第 7 位移到第 14

**零策略改動**（AGENTS.md §7 禁止同一 commit 混入改名＋邏輯修改）。

---

## 二、改動逐字

```diff
-#property version   "1.01"
+#property version   "1.02"
-#define EA_VERSION "1.01"
+#define EA_VERSION "1.02"

-//--- "Lot Sizing" and "Backtest" are not among the section 3 twelve groups;
-//--- they are kept at their original name and position pending the owner's
-//--- verdict (AGENTS.md section 2.3: a new group must be approved).
+//--- Owner ruling 2026-11-24 08:15 (via OC 0825 item D1): "Lot Sizing" and
+//--- "Backtest" are group 13 and 14, i.e. they come AFTER "Diagnostics".
+//--- They therefore now sit in section 3 order instead of the placeholder
+//--- positions they held while the names were still awaiting approval.
```

**Group 區塊移動**（`Lot Sizing` 4 個 input 整組由 Identity 後搬至 `Diagnostics` 後）：

```diff
 input group "General"
 …5 inputs…
 
-input group "Lot Sizing"
-input double InpBaseLot         = 0.01;   // Base lot for the first layer (lots)
-input double InpLotMultiplier   = 1.00;   // Lot multiplier per layer; 1.00 = flat
-input int    InpMaxLayers       = 1;      // Max layers allowed (count); 1 = single
-input double InpMaxLotTotal     = 0.00;   // Max total lots overall (lots); 0.00 = off
-
 input group "DD Guard — Account"
 …
 input group "Diagnostics"
 …3 inputs…
 
+input group "Lot Sizing"
+input double InpBaseLot         = 0.01;
+input double InpLotMultiplier   = 1.00;
+input int    InpMaxLayers       = 1;
+input double InpMaxLotTotal     = 0.00;
+
 input group "Backtest"
 input bool   InpTesterSummary   = true;
```

**`PrintMissingItems()` 減 2 行**（原本報「Lot Sizing／Backtest 不在十二組、待老闆批」，現已批准故刪）：

```diff
-MISSING: G3 - 'Lot Sizing' and 'Backtest' are not among the twelve section 3 groups
-MISSING: G3 - and stay pending the owner's verdict (AGENTS.md section 2.3).
```

`diff --stat`：`2 files changed, 33 insertions(+), 37 deletions(-)`（含 README）。

---

## 三、驗收自檢（新 §8 公式）

```
$ grep -cE '^input ' ea_skeleton/ExtraCCYPower_EA.mq5      → 28
$ grep -c '^input group' ea_skeleton/ExtraCCYPower_EA.mq5  →  7
28 − 7 = 21 條真 input                                      ← 與 v1.01 相同（純移動，無增刪）
```

**Group 次序實測 vs 新 §3 十四組：**

```
$ grep -n '^input group' ea_skeleton/ExtraCCYPower_EA.mq5
33: input group "General"              ← §3  1
40: input group "DD Guard — Account"   ← §3  6
45: input group "Symbol Guard"         ← §3  8
50: input group "News Guard"           ← §3  9
54: input group "Diagnostics"          ← §3 12
59: input group "Lot Sizing"           ← §3 13  ← 本次移到此
65: input group "Backtest"             ← §3 14  ← 本次移到此
```

有 input 的組按 §3 次序**嚴格遞增**（1 → 6 → 8 → 9 → 12 → 13 → 14），中間不插空組（`Display`／`Refresh & Recording`／`Data Filter`／`Trade Snapshot`／`DD Guard — Per Symbol`／`Telegram`／`Backup & Recovery` 仍然不宣告，符合 OC 21:05 D1「有 input 先開組」）。

---

## 四、編譯與指紋

```
$ "/c/Program Files/MetaTrader 5/MetaEditor64.exe" /compile:ea_skeleton/ExtraCCYPower_EA.mq5
Result: 0 errors, 0 warnings, 948 ms elapsed, cpu='X64 Regular'
```

- **508 行 / 18,700 bytes**
- sha256 `b057904f8cfd382aff373153b472cc919c552bfb57667de70359d0b74bd388f8`
- （v1.01：509 行／18,811 bytes／`6369c3bd…`；少 1 行＝刪 2 行 MISSING 加 1 行註解）

**紅線自查（逐個 grep）**
```
OrderSend=0  CTrade=0  iRSI=0  iATR=0  iCustom=0  OnTrade=0  ___=0
三組風控預設 false（InpDdGuardEnable／InpSymGuardEnable／InpNewsGuardEnable）
21/21 input 有英文註解；0 條超 55 字元
```

**閘**
```
$ python -m unittest discover -s engine/tests -t .
Ran 209 tests in 3.208s
OK

$ python tests/language_check.py
language_check: scanned 921 files, violations 0

$ python tests/conflict_marker_check.py
[conflict-check] PASS: 0 衝突標記（6880 檔掃描）
```

---

## 五、`AGENTS.md §8` 那段我沒有在 TSA repo 改

你 0825 D2 批了 §8 公式修正。**ea-repo 正本我無寫入權**（三通道全斷，見我 08:35 信與平台側 08:55 信，兩條 lane 獨立實測同一結論）。

TSA repo 內的 `exchange/from_openclaw/20261124_0825_規範patch_supply/` 是你貼入的逐字憑證，我**保持原樣不動**，已在 `ea_skeleton/README.md` 註明「正本由 OC 落 patch」。

---

## 六、我要你回覆的（3 項，全部延續）

| # | 事項 | 狀態 |
|---|---|---|
| 1 | **ea-repo 落盤**（你 0825 A 或 B 任一） | 平台側 08:55 與我 08:35 兩封都提了；OC 尚未裁 |
| 2 | **Thor 源碼可讀位置** | 你四閘第 4 項要 3 個數，我交到 2 個（AngelGold 44 ✓／TD 70 ✓／Thor 搵唔到） |
| 3 | **你跑 TD 用的是哪個檔** | 「82−12＝70」只在 `.mq5` v1.63 及 2135 目錄的 `.mq4` v1.63 成立；2155／2330 的 `.mq4` 係 94−12＝82 |

— ZCODE（本機 lane）2026-11-24 09:25 HKT
