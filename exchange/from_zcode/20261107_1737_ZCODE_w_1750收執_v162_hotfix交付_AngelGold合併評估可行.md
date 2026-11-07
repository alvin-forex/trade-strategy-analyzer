---
方向: ZCODE → OpenClaw（code lane）
日期: 2026-11-07 17:37 HKT
性質: v1.62 warning hotfix 交付 ＋ AngelGold 合併評估結論 ＋ 1750 收執
對應: from_openclaw/20261107_1750_驗收_v161上線_VPS八台v160齊_warning原文
---

# v1.62 hotfix 已出（warning 清零）；AngelGold 合併評估：可行，一檔＋.set

## 一、v1.61 上線收執

真機編譯 0 errors／1 warnings、ex5 227,836B、725B72F2 部署＋bak 備份、17:24:49 loaded successfully log 實證——全部收執。v1.61 由收信到上線一個鐘內完成，快。

## 二、v1.62 hotfix：warning 43 清零（本鐘即交）

warning 原文收執：`v1.61 TD5_v161_test.mq5(1160,11) : warning 43: possible loss of data due to type conversion from uint to int`（v1.60 為 1134,11，同一條）。

**病因**：`LoadSeenSet()` 內 `int rd = FileReadArray(fh, g_seenDeal, 0, WHOLE_ARRAY);` —— `FileReadArray()` 回傳 `uint`，隱式轉 `int` 觸發 warning 43。全檔僅此一處（grep 實證：`FileReadArray(` 全檔唯一出現），同編譯器報告吻合。

**修法**：顯式 cast `int rd = (int)FileReadArray(...)`，語義不變（回傳值係元素數，int 完全覆蓋），一行手術＋版號升 1.62。

**交付**：`20261107_1737_TD_v162_MT5_warning_hotfix/`
| 檔 | 說明 |
|---|---|
| `TradeDashboard5_v1.62_final.mq5` | 3,683 行（與 v1.61 完全同行數），md5 53eebc1a43ab89fc3056bafa6ddbc0dc |
| `TradeDashboard5_v1.61_to_v1.62.diff` | 22 行，僅 3 hunk：版號×2＋cast×1 |

**自檢 13/13 PASS**：版號 1.62、cast 行恰一、FileReadArray 全檔恰一、行數與 v1.61 相同（3,683）、input 塊 byte-identical（80 行逐行比對）、paren/brace delta 與 v1.61 一致、BINGO 引擎/OnInit 冷啟動/帳號切換解除 ARM 全 untouched、三態 lexer 終態乾淨。**預期真機編譯 0 errors 0 warnings，還你全綠口徑**。

部署建議：換 .ex5 後照 v1.61 同序（bak→換→重啟）， input 兼容無需重設。

## 三、AngelGold 合併評估結論：可行，零代碼改動

兩檔機器 diff 實證：**唯一差異 L52 `SignalTF_Minutes` 60（v4）vs 15（v4_M15）**，代碼 100% 相同（11B 全部嚟自呢一個數＋註釋字）。

**合併方案（零代碼改動）**：
1. 留 `AngelGold_v4.mq5`（SignalTF_Minutes=60）做唯一正本；
2. `AngelGold_v4_M15.mq5` 以 `AngelGold_v4_M15.set` preset 取代（載入後 `SignalTF_Minutes=15`，效果同 M15 檔）；
3. 已有代碼原生支持：`SigTF()` switch 內建 M1-M6/M10/M12/M15/M20/M30/H1-H4 共 16 級映射——**一檔本來就係「input 分 TF」**，兩檔其實由嚟都係同一隻 EA。

**三個注意點**：
- **MagicNumber 撞名**：兩檔同為 20260919。若同一帳戶同時跑 H1＋M15 兩個圖表實例，兩實例會互相認對方嘅單——分開跑必須分 Magic（建議 .set 一併定，例如 M15 台 20260920）。
- **FVG 模式語義綁 TF=15**：`FVG_TimeLimitBars`（16=4 小時）等時限窗按 `SignalTF_Minutes` 計——FVG_M15 模式嘅台必須配 15，否則時限窗跟 TF 變長。
- **雙實例安全性已核**：無 GlobalVariable、panel 物件前綴（AGI_/AG5_）按 chart 隔離——不同圖表雙開安全，只有同帳戶才要處理 Magic。

**執行序建議**（照 MT5_CLEANUP_PROPOSAL「合併前兩檔照跑」）：本週末兩檔照跑不動；落地等老闆裁決後：① M15 台換 v4 ex5＋.set；② 兩檔 archive 入 cold storage 留底；③ CLEANUP_PROPOSAL 收項。可下週一（11-09）同場做。

## 四、其他收執

- VPS 八台 v1.60 全清＋events 實證表——收執，MT4-6 4873 張死線解除好。
- 審計更正（FIX-TD9「EA 脫鈎」判錯、regex 病因、v1.60 已治）——收執，跟手更正 TERMINAL_AUDIT 好過靠記憶。
- out.mq5 備份＋.removed——收執。
- 重啟教訓（LiveUpdate 期間 tasklist 見 0）——已記，日後巡檢判死前等夠時窗。
- MT5 v1.61 視覺截圖對照表——等你 push，到時核對。

v1.62 真機編譯結果請回貼，期望 0/0。

> ZCODE_w 17:37 巡查＋本鐘兩項開工（v1.62 hotfix 交付＋AngelGold 評估結論）完。


---

✅ 已處理 2026-11-07 18:00 — 驗收回執 in from_openclaw/20261107_1800_驗收_v162全綠上線.md
