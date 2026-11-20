---
方向: OpenClaw（data lane）→ 平台 ZCODE（@zc_ops_bot）
日期: 2026-11-19 13:25 HKT
性質: 派工（重發）
相關: CP-BT1 CurrencyPower v3.10 Python 移植＋parity（原 20261116_1235）
---

# 派工：CP-BT1 CurrencyPower v3.10 Python 移植＋parity（平台 ZCODE 接）

**判定依據：純 Python 計算核心＋白皮書公式＋無編譯／無終端依賴＋機器可驗收（誤差表可重跑）＝平台（判準 1–4 全中）。**

配額紀律：本單優先使用免費額度（yuanyuai glm-5.3 或 GLM Coding「Start Plan」），用盡才准報收費方案並先取老闆同意。

## 〇、裁決承接（老闆 2026-11-19 13:14）

原話：「琴日咪同你講過重新定位啲身份，依家邊個叫zcode就叫佢接啦」
→ **「i lane」概念取消**，原單「待 i lane 認領」理由作廢，本單即刻開工。

## 一、原單（內容不變，路徑已驗存在）

原文：exchange/from_openclaw/20261116_1235_派工_CP-BT1_CurrencyPower移植_parity.md

- 移植 v3.10 計算核心：iRSI(PairTF, RSI_Period) → raw=RSI−50；iATR(PairTF) → w=ATR%（波動加權）；9 貨幣分解引擎（36 instruments）
- **已知缺陷照抄行為，唔好自作聰明修正**（parity 優先）
- 新目錄 ccy_backtest/（與 tsa-risk-analyzer/ 同級，唔混 TSA 現有 scripts/）
- 產出：cp_power_history 序列檔（每 bar 一行 × 9 貨幣＋AVG，帶 timestamp/TF）

## 二、前置數據（**OC data lane 11-20 12:00 前供，屆時 notify 通知**）

- D1／H4 歷史 OHLC 樣本（自終端 history 匯出）
- A06E ccy_power_reader.csv 同 timestamp 抽樣（parity 對照用）
- 你今日可先做：目錄骨架＋計算核心移植（公式唔使等數據到）

## 三、收貨（照 0930 已確認機制）

- push local/alvin → 自開 PR；commit 帶 exchange: 前綴；**嚴禁 git pull --rebase**
- 進度用 exchange/notify/from_zcode/ 時戳檔＋commit 訊息；唔使申請 gh token
- 交付附：移植核心＋9 貨幣＋AVG 誤差表＋重跑指令

## 四、驗收（OC 重跑）

- 誤差表可重跑，輸出格式固定
- 白皮書公式逐條對得上（OC 抽查 ≥5 條）
- 已知缺陷行為與原作一致（唔准修）

## 五、死線

- 階段 A（目錄＋計算核心＋自測）：2026-11-21 18:00 HKT
- 階段 B（parity 誤差表＋序列檔）：2026-11-23 18:00 HKT

> ⏳ 進行中 2026-11-20 08:45 by ZCODE_w（平台 ZCODE 接單：判準 1–4 全中成立；階段 A 目錄骨架＋計算核心移植＋自測本鐘開工，死線 11-21 18:00）
