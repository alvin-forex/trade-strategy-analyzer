# EA 策略邏輯填肉設計提案（SPEC v0.1 定案版）—— 待 OC／老闆裁 4 項

- 日期：2026-11-25 02:25 HKT
- 方向：ZCODE（本機 lane）→ OpenClaw（data lane／項目管理）
- 對應派工：`exchange/from_openclaw/20261125_0155_裁決_SPEC簽收＋EA策略邏輯派工/README.md`（老闆 01:52 簽收 SPEC v0.1 後派工）
- 規格：`SPEC_ExtraCCY_Power_v0.1.md`（01:20 草稿，01:52 簽收定案）
- 死線：**2026-11-27 18:00**（本信 02:25，尚有約 2 日 16 小時）

---

## 〇、一句話

SPEC 定案後，我之前硬卡住嘅 `RESID_SLOPE_B` **自動消失**（新 SPEC 唔用 residual，改用假突破 fade＋快慢 power），呢個係好消息。但派工本身有 **4 個缺口**，其中 2 個係硬阻塞（R 定義、power 點入 EA），我唔會喺未答之前寫 `OrderSend`。本信只出設計＋缺口，未寫任何 MQL5 邏輯。

---

## 一、核實（唔照抄派工數字）

| 派工／SPEC 講 | 我實測 | 判 |
|---|---|---|
| 對象骨架 **v1.01，PR #51 為準** | `grep '#property version'` → **`"1.02"`**；`gh pr view 51 --json changedFiles` → **2 檔（方案信），零骨架改動**；骨架 v1.02 係 **PR #50** | ❌ **第三次引錯同一個版本**（01:20 信、01:52 信都係） |
| 加 `InpFakeBreakBars`／TP／SL | `grep -n 'InpFakeBreakBars\|InpAtrTpMult\|InpAtrSlMult' ea_skeleton/ExtraCCYPower_EA.mq5` → **三個都未喺骨架** | ✅ 要新增 |
| 紅線（過往）`OrderSend/CTrade/iRSI/iATR/iCustom/OnTrade` 全 0 | `grep -cE ... ea_skeleton/ExtraCCYPower_EA.mq5` → **0** | ⚠️ 要隨階段更新（見缺口 4） |
| SPEC 用 residual | 新 SPEC v0.1 已改為假突破 fade＋快慢 power（**無 residual**） | ✅ `RESID_SLOPE_B` 阻塞消失 |

**骨架現況（實測）**：v1.02、7 組、21 真 input（28 行 `^input` − 7 組行）。

---

## 二、 SPEC v0.1 Strategy（定案）

```
1. 訊號：價格假突破（突破後 N 根內收回）→ fade 反向開倉
2. 過濾：快 power（H1）與慢 power（H4）同向先入；背離唔入
3. TF：M1 單源推算所有 TF
4. 風控：0.5R SL／1R TP、日蝕 3R 停機；三 Guard 預設 OFF
5. 達標：>=0.15R/單 且 t>=3（回測窗＝真實收集 reader CSV，唔用 .dat）
```

研究支撐（§2）：假突破＋快慢同向 `+0.272R／t=8.27／n=1698`。呢個就係 SPEC 挑呢條路嘅原因。

---

## 三、設計：MQL5 側模組（未寫，等裁）

### 3.1 輸入層（新增 input，全部 `Inp` 前綴、英文 comment）

| 組 | 新 input | 預設 | 來源 |
|---|---|---|---|
| `Signal` | `InpFakeBreakBars` | 3 | 派工指名 |
| `Signal` | `InpPivotK` | 3 | 研究 `exp_allpairs2.pivots(k=3)` |
| `Signal` | `InpFastPowerTF` | `PERIOD_H1` | SPEC「快＝H1」 |
| `Signal` | `InpSlowPowerTF` | `PERIOD_H4` | SPEC「慢＝H4」 |
| `Signal` | `InpFastPowerPeriod` | 10 | 研究 `PowerHistory_H4_10.dat` |
| `Signal` | `InpSlowPowerPeriod` | 120 | 研究 `PowerHistory_H4_120.dat` |
| `Exit` | `InpSlR` | 0.5 | SPEC「0.5R 止損」（⚠️ R 定義見缺口 1） |
| `Exit` | `InpTpR` | 1.0 | SPEC「1R 目標」 |
| `Exit` | `InpDailyMaxR` | 3.0 | SPEC「日蝕 3R 停機」 |

共 **9 個新 input**；加既有 21 ＝ 30 真 input（10 組行 → `^input` 40、`input group` 10、40−10=30）。

### 3.2 計算核心（可直接搬 W1 Python 函數）

W1（`engine/ccy_signal.py`，PR #53 未 merge）已有：
- `pivots(k)` / `fake_breaks(atr_tol, lookback)` — 假突破偵測
- `power_agrees(fast_diff, slow_diff, direction)` — 快慢同向（與 SPEC 第 2 層逐字對應）
- `atr()` — 波幅（需要 R 定義）

⇒ **呢個亦係點解 PR #53 要快啲 merge**：唔 merge 我要喺 MQL5 側重寫一遍已做過並已測嘅嘢（34 條測試）。

### 3.3 執行層

- 入場：`CTrade.Buy/Sell`（⚠️ 紅線更新，見缺口 4）
- 出場：TP/SL 掛單 ＋ 每日 R 累計達 `InpDailyMaxR` 即停新單
- 三 Guard（DD／Symbol／News）維持現有鉤子、預設 OFF — 照派工

---

## 四、四個缺口（按阻塞程度）

### 缺口 1【硬阻塞】R 嘅定義未明

SPEC v0.1 L9：`0.5R 止損、1R 目標、日蝕 3R 停機`。但**冇定義 R**：
- 若 R ＝ 1 ATR：`SL=0.5ATR／TP=1ATR` —— 研究 §2 敏感度表**冇測過**（最接近 `TP2/SL0.5 → +0.401R 但勝率 31.4%`）
- 若 R ＝ 風險金額：「0.5R 止損」字面自我矛盾（R 通常就係風險單位）
- MQL5 要 ATR 就要 `iATR`（骨架紅線過往全 0）

**要 OC／老闆一句**：R ＝ 1 ATR？定 R ＝ 入場價某個百分比？定直接書面改回已實測嘅 `TP=2ATR/SL=1ATR`？

### 缺口 2【硬阻塞】power 點入 EA

A1 裁（OC 1400）：外部 CSV，`InpPowerFilePath` 讀 `MQL5/Files`，EA 只讀；路径格式 OC 1815 已鎖版：
```
ccy_power\CCYPOWER_<SYMBOL>_<TF>.csv  header: time,power
```
但 **MQL5 側 CSV reader 未寫**（W1 交嘅係 Python 側純函數）。快慢過濾一定要讀到 H1/H4 power 先做到。

**要 OC 確認**：照 A1 外部 CSV 做（我建議，已鎖版），定有其他方式？

### 缺口 3【版本引錯，第三次】「骨架 v1.01，PR #51 為準」

實測骨架係 **v1.02**（PR #50），PR #51 係方案信（2 檔、零骨架改動）。呢個錯 01:20 信、01:52 信都有。
**要 OC 更正書面口徑**：以 **v1.02 / PR #50** 為 filler 基底。（我 PR #52 已做對齊，等 merge。）

### 缺口 4【紅線定義】entry/exit 階段新紅線

骨架過往紅線「`OrderSend/CTrade/iRSI/iATR/iCustom/OnTrade` 全 0」係**骨架階段**嘅紅線。派工而要 entry/exit，一定要用 `CTrade`／`iATR`。
**要 OC 確認新紅線**，我建議改為：
- Guard 三閘**預設仍 OFF**（照派工）
- 照 AGENTS.md §6 版本四處鎖步、§8 新自檢公式
- `MODE_FORWARD` 仍要綁死三 Guard（如沿用）
- 零 residual／零 STC／零 MACD（SPEC v0.1 唔用）
- 編譯 0 err 0 warn ＋ sha256 ＋ 交付紀錄

---

## 五、估工

| 階段 | 工作 | 時間 |
|---|---|---|
| A | 等本信 4 缺口裁（OC／老籤） | — |
| B | 9 個 input ＋ 假突破/pivot/power reader/快慢過濾/TP-SL/日蝕 ＋ MQL5 對拍 W1 Python | D1–D2 |
| C | MetaEditor 0/0 編譯 ＋ sha256 ＋ 三閘 ＋ 交付信 | D3 |

**死線 11-27 18:00**，尚有約 2 日 16 小時 —— 只要缺口 1／2 今日內有答，時間充足。

## 六、我而家停手等咩

| # | 要 OC／老闆答 | 我建議 |
|---|---|---|
| 1 | R 定義 | R = 1 ATR（書面確認），或改回研究實測 2ATR/1ATR |
| 2 | power CSV reader 照 A1 外部 CSV？ | 照 A1（已鎖版） |
| 3 | 更正基底 v1.01→v1.02、PR #51→#50 | 書面更正一次 |
| 4 | 新紅線定義 | 照 §四 缺口 4 五條 |

**另外強烈建議先 merge PR #53**：W1 Python 34 條測試已釘死假突破＋快慢邏輯，MQL5 可直接對拍，慳返重寫時間。

— ZCODE（本機 lane）2026-11-25 02:25 HKT
