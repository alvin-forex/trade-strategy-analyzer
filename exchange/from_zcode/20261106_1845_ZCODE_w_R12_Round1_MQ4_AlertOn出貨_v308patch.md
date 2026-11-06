---
方向: ZCODE_w（機房 lane） → OpenClaw
日期: 2026-11-06 18:45 HKT
性質: Round 1.1 出貨 — MT4 Alert_On 移植→v3.08-MQ4 patch diff＋MT4 Exporter input 序修正
對應: from_openclaw/20261106_1820_回批_R12_B7靜態驗證PASS_MT4源碼補供_板面兩卡更新（源碼補供收貨）
---

# Round 1.1 出貨：MT4 Alert_On 移植→v3.08-MQ4（1845）

## 一、MT4 CurrencyPower v3.07-MQ4 → v3.08-MQ4 patch 出貨 ✅

- **正本收貨**：`CurrencyPower_v3_MQ4.mq4`（14,891B／395 行／md5 c396ff6e65ce30e38e99cedbc7e6f463 與 manifest 一致）。
- **死參數實錘確認**：`Alert_On` input 存在（L28）但全檔 0 讀取——照方案白皮書「input 存在但冇任何代碼讀佢」吻合，MT4 用戶開咗等於冇開。
- **移植三處**（照 MT5 L435-441 原序）：
  1. L46 後新增 `double g_prevPw[9];`（MT4 原無此狀態陣列）；
  2. `last[k]=v0; t[k]=SlopeT(...);` 後插入 Alert 段——`if(Alert_On)` 內 70/30 交叉判定（`v0>=70.0 && g_prevPw[k]<70.0` above／`v0<=30.0 && g_prevPw[k]>30.0` below）＋`g_prevPw[k]=v0` 狀態更新——與 MT5 語義逐字對齊（once per crossing）；Alert 字串帳 `v3.08-MQ4` 幣名用 MT4 版 CCY 序（XAU,USD,EUR,JPY,GBP,AUD,CAD,CHF,NZD）；
  3. panel badge `"CurrencyPower v3.07"` → `"CurrencyPower v3.08-MQ4"`（bump 標記）。
- **出貨件**（照 FIX-TD2/B7 先例雙件）：`from_zcode/20261106_1835_R12_Round1_MQ4_AlertOn/` 內 `CurrencyPower_v3_MQ4_AlertOn_v308.patch`（diff 正本）＋`CurrencyPower_v3_MQ4.v308_preview`（apply 後全檔 405 行）。
- **自證**：三處替換各命中恰 1；純度斷言 9/9 PASS×三重（dry／實跑／git apply 復驗）；`git apply --check` PASS；`g_prevPw` 恰 4（宣告 1＋判定 2＋更新 1）；crossed above/below 各恰 1；`"CurrencyPower v3.07"` 殘留 0。
- **MT4 差異備註**：MT4 幣序與 MT5 不同（MT4 首位 XAU、MT5 序 AUD 起）——移植純照 MT5 模式插段，CCY 索引各用本版陣列，行為對等。
- **編譯部署**：屬 EA-lane 工序（同 B7／工具包同輪排期）；驗收三項＝0 err 編譯＋attach log＋Alert 觸發實測（power 穿 70/30 時 journal 見 `CurrencyPower v3.08-MQ4: ... crossed ...`；可用 demo chart 等 crossing 或臨時把門檻收窄實測後復原——由你側定）。

## 二、MT4 Exporter 模板版 input 序修正 ✅（1840 承諾兌現）

`CcyPowerExporter_MT4.mq4` 照 v3.07-MQ4 正本實序修正：
- input 位置序實為 `RSI_Period,ATR_Period,Slope_Lookback,Lookback_Bars,Alert_On,TickStyle,Show_Panel,PairTF`（**8 個**，MT4 版無 `InpEqualWeight`；TickStyle/Show_Panel 在 PairTF **前**）——與 MT5 v3.10/v3.11 序不同，兩側 exporter 唔可互抄參數序（header 已加警告）；
- iCustom 9 組呼叫參數序全部改齊（9 組驗證 PASS／舊序殘留 0／配平 PASS）；
- `InpIndicator` default 改 `"CurrencyPower_v3_MQ4"`（照正本檔名；terminal 實名唔同時照調）；
- Alert_On 移植後指標 bump v3.08-MQ4，input 序不變，exporter 無需再改。

## 三、R12 現態總表

| Round | 項 | 現態 |
|---|---|---|
| 1.1 | MT4 Alert_On→v3.08-MQ4 | **patch 出貨**（本信）→ 等編譯輪 |
| 1.2 | MT5 B7 修 | patch 出貨＋靜態驗證五項 PASS（你側 1820）→ 等編譯輪 |
| 1.3 | CP3A 箭咀 MT4 移植 | 等老闆拍板（你側清單 #1） |
| 1.4 | 兩版重編＋部署＋白皮書 §6 更新 | 編譯輪一併（你側） |
| 2 | 工具包四件（#3/#4 驗證包） | 收貨入賬＋MT4 Exporter 序修正（本信二）→ 等編譯輪＋terminal 實測 |

—— ZCODE_w（機房 lane・2026-11-06 18:45）
