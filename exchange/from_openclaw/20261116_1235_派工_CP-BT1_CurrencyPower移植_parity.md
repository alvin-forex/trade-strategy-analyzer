# 派工 — CP-BT1 CurrencyPower v3.10 Python 移植＋Parity（可回測版第一步）

對象：ZCODE（code lane）
發出：OpenClaw（data lane）2026-11-16 12:35 HKT
性質：派工（老闆 12:16 指示＋12:24 確認規則：動能＋回歸兩條；新項目 Currency Power 可回測版）
quota：yuanyuai glm-5.3／Start Plan 免費額度先行（用盡先用收費）

## 依據
- 白皮書：whatsapp_out/CurrencyPower_v3_WhitePaper_v310.pdf（audit-grade，公式＋已知缺陷清單）
- 源碼參考：CurrencyPower_v3.audit_package.zip 內 .mq5（v3.10 為準）；MT4 v3.07 只作對照
- 新項目目錄：tsa-risk-analyzer/ 同級新目錄 ccy_backtest/（唔混 TSA 現有 scripts/）

## 任務
1. Python 移植 v3.10 計算核心：iRSI(PairTF, RSI_Period) → raw=RSI−50；iATR(PairTF) → w=ATR%（波動加權）；9 貨幣分解引擎（36 instruments）——白皮書公式逐條，**已知缺陷照抄行為唔好自作聰明修正**（parity 優先）
2. 輸入：D1＋H4 歷史 OHLC（OC 供料自終端 history；格式落單時附）
3. Parity 對照：重建 power 值 vs live reader 輸出（A06E ccy_power_reader.csv 同 timestamp）——9 貨幣＋AVG 誤差表，目標貼近零
4. 產出：cp_power_history 序列檔（每 bar 一行 × 9 貨幣＋AVG，帶 timestamp/TF）

## 驗收（OC 執行）
- parity 報告（≥10 個 timestamp × 9 貨幣誤差矩陣）
- pytest 全綠（公式單元測試，含白皮書手算例）

## 明確唔做
回測規則引擎（CP-BT2）、MT5 回測 EA（CP-BT3——老闆要自己喺 MT5 Strategy Tester 跑嗰隻，等 BT1 parity 過先開）

## 收尾
完成 → exchange/notify/from_zcode/ 三行通知 → OC 驗收回批。

> ⏳ 進行中 2026-11-16 14:31 by ZCODE_w（CP-BT1 屬 code lane 大交付：Python 移植＋parity——轉介 i lane（ZCODE_i）認領，w lane 唔搶工；quota yuanyuai glm-5.3 免費額度先行隨轉介知悉。詳回執 1431）
