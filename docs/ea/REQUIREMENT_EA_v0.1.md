# REQUIREMENT — EA 開發需求書 v0.1（MT5 先行）

- 版本：v0.1（2026-11-17 20:25 HKT）
- 狀態：**OPEN — 5 項中 3 項待補，見第 3 節「未決清單」**
- 業主：Alvin（老闆／LEGEND）｜需求整理＋驗收：OpenClaw｜實作：ZCODE code lane
- 本檔位置：`trade-strategy-analyzer/docs/ea/`（公開可讀）
- 代碼落點：`github.com/alvin-forex/ea-repo`（private；`MQL5/Experts/`、`MQL4/Experts/`）
- 開發規範：ea-repo 根目錄 `AGENTS.md`（**開工前必讀，逐條跟足**）

---

## 1. 老闆 2026-11-17 五條裁決（原文）

| # | 問題 | 老闆原文答覆 |
|---|---|---|
| 1 | MT4 / MT5？ | 「先做好 MT5 的」 |
| 2 | Strategy logic（entry/exit、grid or not、indicators used） | 「由 LEGENT 俾你」 |
| 3 | Inputs & parameter ranges | 「參照 REQUIREMENT 的參數」 |
| 4 | Risk rules（max lots、drawdown limits） | 「就係唔知先要個系統」 |
| 5 | Acceptance criteria（backtest numbers、compile clean 等） | 「未有諗法」 |

## 2. 五條裁決嘅工程落地

### 2.1 平台（裁決 1）
- **MT5 先行**：`.mq5` 為第一交付物；編譯目標 `0 errors, 0 warnings`。
- MT4 版本**架構預留但唔實作**：參數名、group、次序、預設值日後必須與 MT5 一致（ea-repo AGENTS.md §6）。
- 不得為咗遷就 MT4 而犧牲 MT5 功能。

### 2.2 策略邏輯（裁決 2）
- **策略本體唔由開發方發明**。入口／出場／是否格網／用邊啲指標，一律等 **LEGEND（老闆）** 書面提供。
- 收到策略書面規格前，開發方可做嘅只有：**骨架、輸入框架、風控接口、編譯管線**——唔准自創交易邏輯。
- 策略規格到齊後補入本檔第 2.2 節附件（`specs/STRATEGY_<EA名>_v1.md`）。

### 2.3 輸入參數（裁決 3）
- 參數**照 SET 檔實際欄位**（對標 TSA Canonical Strategy Model，Spec §4／§6 Adapter Rules）；冇嘅欄位報 MISSING，唔准自創。
- 命名硬規則（ea-repo AGENTS.md §1）：`Inp` 前綴 + PascalCase，每個 input 必有英文 comment（≤55 字元），`input group "..."` 分組，group 次序固定（§3），**數值上限 0 ＝ 關閉**，風控類預設 `false`／`0`。
- 參考現行資產：`ea-repo/specs/TradeDashboard5_inputs_before.md`（輸入清單範式）、`specs/presets/*.set`。

### 2.4 風險規則（裁決 4）——**呢個係項目核心**
老闆明言「就係唔知先要個系統」。所以：
- 風險規則**唔係由老闆預先提供**，而係由 **TSA Martingale Risk & Currency Fit Analyzer**（`trade-strategy-analyzer` repo，`tsa-risk-analyzer/`）計出嚟：最大手數上限、逐層 DD 金額＋點數、回本距離、資本佔用率、可生存性。
- 該分析器嘅需求書：`docs/martingale/REQUIREMENT_TSA_Risk_Analyzer_v1.1.md`；技術規格：`docs/martingale/TSA_Martingale_Technical_Docs_v1.0.md`。
- **依賴次序**：分析器先出風險數字 → EA 嘅風控參數才有基準值 → 先可以寫死 EA 嘅 max lots／DD 限制。
- EA 側風控模組（DD Guard / Symbol Guard / News Guard）照 ea-repo AGENTS.md group 次序實作，**預設全部 OFF**。

### 2.5 驗收標準（裁決 5）——由 OpenClaw 提議，**待老闆拍板**

**A. 機器閘（硬性）**
1. 編譯 `0 errors, 0 warnings`（`ea-test-kit/scripts/compile_all.py`）
2. `grep -c '^input group'` 與 `grep -cE '^input '` 對得上；無 `___` 假分隔；無未註解 input
3. 風控功能預設全 OFF（未設置時 EA 唔會發超出預設嘅單）
4. 回測矩陣跑得完（`ea-test-kit/scripts/run_matrix.py`）並產出報告
5. 八年回測（老闆既定鐵律，AGENTS.md §11 之 8 年門檻）通過基本生存條件：**最大回撤 < 100%（爆倉線）**、無異常連續虧損
6. `.set` 檔可正確載入（改名後值無丟失）

**B. 人眼閘**
7. 參數視窗 group 次序、comment 文案正確
8. 圖表面板（如有）顯示與實際倉位一致

**C. 唔適用（Phase 1）**
- 「backtest numbers」嘅具體達標線（如年化／盈利因子）：**待老闆定**，現階段只做「生存 + 可重現」

## 3. 未決清單（OPEN — 需老闆提供）

| # | 項目 | 負責 | 影響 |
|---|---|---|---|
| O1 | **EA 名稱**（`Inp` 前綴以外嘅程式名） | 老闆 | 決定檔名／目錄／set 檔 |
| O2 | **策略邏輯規格**：entry/exit 條件、是否格網、用邊啲指標、TF | 老闆（裁決 2） | 冇呢個＝只能做骨架，唔可以寫交易邏輯 |
| O3 | **參數清單**：邊個 SET／邊份 REQUIREMENT 參數為準 | 老闆（裁決 3） | 決定 input 框架 |
| O4 | **驗收達標線**：backtest numbers 具體門檻 | 老闆（裁決 5） | 決定「done」定義 |

> O1–O4 未清之前，ZCODE 只准做：repo 結構、編譯管線、input 框架、風控接口 skeleton。**唔准寫交易邏輯。**

## 4. 紅線

- 只准改 `ea-repo/MQL5/`、`MQL4/`、`specs/`；唔准改終端數據夾（AGENTS.md §4）
- 改名依賴 AGENTS.md §5 完整八步程序，未經老闆確認唔准動手
- 同一 commit 唔准混「改名 + 邏輯修改」
- 唔准將帳號／token／密碼寫入源碼
- 未能編譯通過＝唔算交付

## 5. 交付格式

每次交付附：`.mq5` 源碼 + 編譯 log（0 err/0 warn）+ 改動摘要（改名數／新增刪除／group 變動）+ 回測報告路徑。
