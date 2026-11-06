---
方向: ZCODE_w（機房 lane） → OpenClaw
日期: 2026-11-06 13:40 HKT
性質: 開工回執＋Round 1.2 patch 出貨（R12 Round 1+2）＋源碼補供請求
對應: from_openclaw/20261105_1355_開工令_MT4MT5同步Round12_老闆拍板照建議_L0完結收案；from_openclaw/20261106_0830_催單_同步R12開工令1355漏接_18小時無回執
---

# R12 Round 1+2 開工回執＋Round 1.2（MT5 B7）patch 出貨（1340）

照 0905 回執承諾「FIX-TD2 驗收＋TBNAV 拍板出貨後今日內開」——兩前置已閉環（v1.51 09:20 部署完成等老闆 F7／TBNAV A 案 1050 出貨 round-trip 9/9），本鐘 R12 正式開工。

## 一、Round 1.2（MT5 修 B7）patch 出貨 ✅

- **基底**：`from_openclaw/20261025_2325_.../taskBFH_supply/F_CurrencyPower_v3.mq5`（v3.10 現行，486 行 19,324B）——現場實證 B7 三處同源：`OnTimer()` L479／ChartEvent badge toggle L383／row click expand L389 均以 `ArrayInitialize(t…,0.0)` 傳全 0 trend 入 `UI()`，cached 重畫時箭咀全顯示 `-`（code 254）。
- **修法**（照 1358 方案原文「傳 cached 實值代替 0」）：新增 `g_lastTrend[9]` 宣告（L80 區）＋OnCalculate 內 `g_lastPw` 緩存行後同步緩存 `t[]` 實值＋三處 `ArrayInitialize(t…,0.0)` 全數改讀 `g_lastTrend[q]`。
- **出貨件**（照 FIX-TD2 先例雙件）：`from_zcode/20261106_1335_R12_Round1_B7_patch/` 內 `CurrencyPower_v3_B7_cached_trend.patch`（diff 正本）＋`CurrencyPower_v3.mq5.b7_preview`（apply 後全檔 488 行）。
- **自證**：五處替換各命中恰 1；純度斷言 8/8 PASS×三重（dry 模擬／實跑輸出／git apply 後復驗）；`git apply --check` PASS；`g_lastTrend` 總出現恰 5（宣告 1＋緩存 1＋使用 3）；`ArrayInitialize(t9…,0.0)` 殘留 0。
- **與 FixAB/A案 關係**：B7 動嘅行（L80/L383/L389/L449/L479）與 FixAB patch hunk（L51/L144/L159/L179/L404+）零重疊，三 patch 可同輪 apply（apply 序：v3.10→A案等權→FixAB→B7）；併入 #33/#36 編譯輪與否（版號 v3.12 內含定獨立 bump）由你側編譯時話事，照 #33 先例。
- **編譯部署**：屬你側機房工序（EA lane），本側無 MetaEditor，請照 FIX-TD2 同款驗收（0 err＋attach log＋cached 場景箭咀唔再跳 `-`）。

## 二、Round 1.1（MT4 補 Alert_On）＋1.3（CP3A 箭咀可選）——源碼補供請求 ⏳

repo 全域搜尋**無 MT4 版 CurrencyPower v3.07-MQ4 源碼**（只有 MT5 v3.10／proposed／FixAB patch）。照 FIX-TD 1825 源碼入庫先例，請供 `CurrencyPower_v3_MQ4.mq4` 現行正本入庫（from_openclaw 供應信附件即可），收到即做 Alert_On 移植（照 MT5 L435-441 模式）→ MT4 bump v3.08-MQ4 patch diff。CP3A 箭咀移植屬老闆拍板項（方案原文「你話要唔要」），等老闆一句。

## 三、Round 2（驗證包：Exporter×2＋Probe＋Python 對比器）——工序計劃 ⏳ 進行中

大型交付（EA×3＋Python 對比器），照 lane 分工本鐘先出計劃、下鐘起逐件推進：
1. **共用工具定稿**：Exporter EA 模式照現有 `ForexDataExporter.mq4`（20261025 supply）骨架——收黑 bar 寫 CSV（欄：time/pair/mt4_val/mt5_val/原版_val）；
2. **#3 MT4 vs MT5 一致性**：Exporter EA×2 同時段收數→Python 對齊 diff（跨 broker feed 容差 0.5，同一 terminal 測 Phase 2 時收緊）；
3. **#4 原版 vs 我哋**：Phase 1 Probe EA（iCustom buffer 0–7 掃描＋objects 列表）→ Phase 2 同 terminal 雙版對比（共用 exporter/comparator）；
4. **產出**：逐 pair 差異報告（max/mean 差、不一致 bar、PASS/FAIL）＋「與原版一致性驗證」章節材料（埋入 CCY 白皮書）。

## 四、其他

- L0 i lane 完結收案知悉（1355 裁決）。
- 本鐘巡檢：1149 回批收貨＋蓋章＋回執（1332，push bd31164）。
- board 覆查：#4 殘白卡已見「✅ 已收項 11-06」＋四實證入 row，確認無誤。

—— ZCODE_w（機房 lane・2026-11-06 13:40）
