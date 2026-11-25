# [本機] SPEC v0.1 老闆簽收 OK（2026-11-25 01:52）＋ EA 策略邏輯派工

## 裁決
ExtraCCY Power 策略 SPEC v0.1（假突破 fade＋快慢 power 雙過濾，H1/H4 同向，0.5R 止損，日蝕 3R 停機，達標線 >=0.15R/單，M1 單源數據）——**老闆 OK 簽收，正式定案**。存 exchange/from_openclaw/20261125_0120_回批_AC_五缺口語意＋REA批准＋SPEC草稿/SPEC_ExtraCCY_Power_v0.1.md

## 派工：ZCODE(本機) EA 策略邏輯填肉
- 對象：ea_skeleton/ExtraCCYPower_EA.mq5（骨架 v1.01，PR #51 為準）
- 任務：按 SPEC 實作 entry/exit——假突破偵測（N 根收回確認，InpFakeBreakBars）、快慢 power 雙過濾、0.5R 止損／1R 目標、日蝕 3R 停機閘
- 規矩：input 全 Inp 前綴、新 input 入對應 group、唔改風控三閘預設（OFF）
- 交付：PR＋完整 compile log（0 err 0 warn）＋sha256＋886 @OC；死線 2026-11-27 18:00
> ✅ 已處理 2026-11-25 09:02 by ZCODE_w（本機 lane 對象（EA 策略填肉）——設計 PR #56 0820 驗收 PASS 11/11，實作死線 11-27 18:00；平台唔代辦）
