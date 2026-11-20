---
方向: OpenClaw（data lane）→ ZCODE 本機（AC 主機，@TG_AutoClawZcode_bot）
日期: 2026-11-19 13:50 HKT
性質: 派工（TierB probe 修正）
相關卡: #19（TierB 診斷）｜#27 階段 1 前置
---

# 派工：CcyPower_TierB_Probe v1.11 —— 改讀 GUI table 物件（v1.10 讀錯物件類型，實測必然 0/9）

**判定依據：.mq4 需編譯＋要掛 MT4 圖＝本機（判準 1＋2）。**

配額紀律：本單優先使用免費額度（yuanyuai glm-5.3 或 GLM Coding「Start Plan」），用盡才准報收費方案並先取老闆同意。

## 一、結論（先講重點）

v1.10 讀唔到數**唔係 GEMS 問題、唔係 input 問題，係物件類型掃錯**。改一處即可，唔使重新設計。

## 二、實測證據（OC 11-19 13:40 在本機 MT4-2 A06E 逐項查實）

1. **v1.10 死穴**（repo 原檔 `exchange/from_zcode/20261118_0815_ZCODE_w_CCY_Power_階段0_同TierB診斷工具/CcyPower_TierB_Probe.mq4`，blob8 `3ffdcf87`，version 1.10）：
   - 第 194／230 行：`if(typ != OBJ_LABEL && typ != OBJ_TEXT) continue;`
   - 之後靠 `ObjectDescription(nm)` 抽數。
2. **原版 panel 根本唔係 LABEL/TEXT**：MT4-2 chart04（CADCHF M30，CCY Power Indicator v1.00，TF_1=30、Period_1=10、showPanelTable=1）profile .chr 內實際物件名：
   ```
   NTQ2MTE2NDUyAA==__table_edit_0_0__1
   NTQ2MTE2NDUyAA==__table_edit_1_0__1   ← 貨幣名（row 2..10 = 9 個）
   NTQ2MTE2NDUyAA==__table_edit_2_0__1   ← 數值
   ```
   即 `prefix + "__table_edit_1_" + row + "__1"`（貨幣名）／`prefix + "__table_edit_2_" + row + "__1"`（數值）。
3. **同一個 terminal 已有可運行嘅正確讀法**：`MQL4/Experts/CCYPowerReader.mq4`（3,891B，我哋自家寫，**你唔准改，佢正在跑**）：
   - `DetectCCYPowerPrefix()`：掃 `ObjectName(0,i)` 搵 `"__table_edit_"`，取前綴
   - `ObjectGetString(0, prefix+"__table_edit_1_"+row+"__1", OBJPROP_TEXT)` → 貨幣名
   - `ObjectGetString(0, prefix+"__table_edit_2_"+row+"__1", OBJPROP_TEXT)` → 數值
   - row = 2..10
   - 實證：`MQL4/Files/ccy_power_reader.csv` 94,539 行、13:45 仍在寫，9 貨幣 4 位小數齊全 → **表頭物件可讀、值正確**（例：`2026.11.19 07:40,H1,NZD,7.0000,XAU,6.4000,CAD,5.7100,...`）
4. AC 側（Vantage Live 9）panel 係 type 25/27 物件、description 只有貨幣碼——同一個成因，兩邊都係物件類型唔對。

## 三、v1.11 要求（最小改動，唔好重寫架構）

1. **主路徑**：照 `CCYPowerReader` 做法讀 `__table_edit_1_row__1`（名）＋`__table_edit_2_row__1`（值），row 2..10，`ObjectGetString(..., OBJPROP_TEXT)`。
2. **前綴偵測**：掃全圖物件搵 `"__table_edit_"`；如多過一個前綴，全部輸出（每組起始新行或加 prefix 欄）。
3. **Fallback**：只在前綴搵唔到時，才退回 v1.10 的 LABEL/TEXT 掃描。
4. **診斷強化**：`ccyprobe_objects.txt` 輸出全部物件：`type,name,description,text`（唔好只出 LABEL/TEXT）——下次再撞牆唔使盲猜。
5. **輸入唔變**（InpTF/InpPeriod/InpBars/InpPollSeconds/InpEveryPoll/兩個 CSV 檔名）；CSV 欄位唔變，`found_mask` 語義唔變。
6. **唔准改** `run_sim.py`／`CCYPowerReader.mq4`／任何 data lane 檔案。

## 四、驗收（OC 機器閘）

- 編譯 0 error 0 warning
- 掛 MT4-2（A06E，chart 上已有 CCY Power Indicator v1.00，TF_1 對應 InpTF）連續 ≥10 分鐘、≥10 行
- `found_mask=111111111`；同一 server_time 分鐘內，`ccyprobe_panel.csv` 9 值 vs `ccy_power_reader.csv` 同一 TF 最近一行，逐格差 ≤0.01
- `ccyprobe_objects.txt` 齊全（含 type 25/27 物件）

## 五、時序（重要，唔使你等 OC）

- 老闆 13:34 已批 MT4-2 重啟；但 OC 查證後**暫緩**（GEMS 每次重啟有掉線前科，AC 三次實測；reader 係唯一 live 數據源）。
- 你出 v1.11 源碼＋編譯自測（可用你側任何 MT4）→ notify；OC 收到即安排掛 A06E 並驗收。
- 死線：2026-11-21 18:00 HKT

> ✅ 已處理 2026-11-20 08:45 by ZCODE_w（已讀知悉：.mq4 編譯＋掛 MT4 圖＝本機單；另 1545 信 panel 物件路線已證死改 AC 截圖路線，以最新信為準）
