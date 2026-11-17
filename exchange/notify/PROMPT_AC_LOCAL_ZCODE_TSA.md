# PROMPT — 教 AC 本機 ZCODE 接 REQUIREMENT（TSA Risk Analyzer）

> 用法：老闆將 **第 1 節「貼落 AC 本機 ZCODE 嘅完整指令」** 原封不動貼俾 AutoClaw／本機 ZCODE。
> 本檔係外部入口；真相全部喺 repo，唔靠口頭。

---

## 1. 貼落 AC 本機 ZCODE 嘅完整指令（copy-paste）

```
你係 ZCODE，負責實作 TSA Martingale Risk & Currency Fit Analyzer（下稱 TSA）。

【第一步：讀需求，唔准跳】
1. 去 https://github.com/alvin-forex/trade-strategy-analyzer
2. 讀 docs/martingale/REQUIREMENT_TSA_Risk_Analyzer_v1.1.md（需求書，老闆五條裁決）
3. 讀 docs/martingale/TSA_Martingale_Technical_Docs_v1.0.md（技術規格，唯一真相來源；§3 模組、§4 Canonical Model、§6 Adapter、§8-§12 引擎、§14-14.1 檢核、§23 可重現欄位、§28 結構）
4. 讀 exchange/from_openclaw/ 內 W0→W3b 七張派工單（逐張，唔好只讀頭尾）

【第二步：確認你嘅工作邊界】
- 你只可以改 tsa-risk-analyzer/ 呢個頂層目錄（未存在就係你建）
- 唔准郁 docs/、exchange/、scripts/、任何現有頁面
- 如果你用嘅 repo 係 local clone：你可以喺自己 branch 開工；交貨行 PR 或者 exchange/notify/from_zcode/ 三行通知

【第三步：開工次序（一單一 PR，唔准一次過做晒）】
W0 → W1 → W1.5 → W2a → W2b → W3a → W3b
W0 最先（骨架＋工具鏈＋CI）；W0 merge 後即刻做 W1；如此類推。
每單做完：npm test 全綠 → 寫 exchange/notify/from_zcode/ 三行（完成什麼／信件路徑／commit）→ 停，等下單放行。

【第四步：硬性規矩】
1. MT5 先行（老闆裁決 #1）：SET 解析、Adapter、PipValue/Margin 全部以 MT5 為第一公民；MT4 架構預留但唔實作。
2. 策略邏輯唔係你發明（裁決 #2）：你只做「讀入 + 建模 + 風險計算」。SET 檔有咩欄位就讀咩，冇就報 MISSING。
3. 參數照 Sett + Spec §4/§6 映射（裁決 #3）：唔准自創參數名或預設值。
4. 風險規則就係你嘅交付物（裁決 #4）：最大手數、逐層 DD、資本佔用、可生存性全部由你算出嚟。
5. 驗收標準（裁決 #5）：見 REQUIREMENT 第 4 節。最硬三條：
   - DD 雙式（直接式≡增量式）必須寫死斷言測試且通過
   - Margin 不變式 Σ逐層 ≡ 總手數 必須測試通過
   - 六類錯誤碼 fixtures（83103 / 32+152 / 395=632 / 286-546. / 1667--2258 / 5820-5223）必須全數紅燈攔截
6. 對標基準＝Spec §5 公式手算值（provisional）。現行 Excel §26 有已知 bug（包括 Deposit Load 重複乘），唔准照抄。
7. MQL 相關（如果日後要寫 .mq5）：先讀 ea-repo 嘅 AGENTS.md，input 命名 Inp+PascalCase、input group 固定次序、改名要先出對照表等老闆批。
8. 免費額度先行：yuanyuai glm-5.3 / GLM Coding Start Plan 先用，用盡先用收費 model。
9. 唔准 force push；唔准一次 commit 混「改名＋邏輯改動」。
10. 遇到規格歧義：停手寫信問，唔准自己判斷。

【第五步：回報格式（每次交付都用呢個格式）】
完成：<一句話講做完乜>
證據：npm test 輸出（X passed / 0 failed）、build 結果
路徑：<commit sha> + <改動檔案清單>
阻塞：<無 或 具體問題>
```

---

## 2. 內部備注（唔使貼）

- AC 本機 ZCODE 同平台 ZCODE_i 會撞車：**同一 repo 行 PR、由 OC 統一驗收**。兩邊唔好同時做同一張單。
- 平台 ZCODE 七單零交付（i lane 未認領）——若 AC 本機先開工，建議由 **W0＋W1** 起，搶通管線；W3a/W3b 留返平台隊或者之後再派。
- Scanner 逆向係另一條線（唔屬本 REQUIREMENT），唔好混入。
