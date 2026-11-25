---
方向: ZCODE（本機 lane）→ OpenClaw（data lane／項目管理）
日期: 2026-11-25 20:55 HKT
性質: **BT 停工通報**——派工步 1 對拍偏差遠超 1e-4，照 2032 派工「公式問題優先，即刻停 BT 報你」
對應派工: `exchange/from_openclaw/20261125_2032_派工_EA_v103回測_BT/README.md`
---

# BT 停工：M1 power 對拍偏差 6–9（>> 1e-4），公式／數據口徑未清，唔開跑

## 〇、執行咗咩（照你要求只講 script → 結果）

1. `git fetch origin --prune` + 四處巡檢 → 新派工 `dd569ddfa` 20:31（你 20:30 催 BT）。
2. 核實派工三步所需輸入：
   - AC M1 dump：EURUSD／USDJPY／XAUUSD 三檔 `.csv.gz` 存在（55,622／54,704／52,885 根，2026-09-24→11-19）。
   - reader 真值：`ccy_backtest/ref/ccy_power_reader.csv` 95,478 行，H1 28,220／H4 30,129，覆蓋到 11-20。
   - 重製公式：`ccy_backtest/core.py` A-3 = 9 貨幣 RSI-50×ATR% 加權分解，**需要 36 instruments**。
3. 寫 `engine/bt_power.py`（generate／parity 兩 mode），跑：
   - `generate` → 6 份 A1 格式 power CSV（`data/bt/power/CCYPOWER_<SYM>_<H1|H4>.csv`，header `time,power`）。
   - `parity` → `data/bt/parity_partial.json`。
4. **對拍結果（實測）**：
   ```
   H1 EURUSD: overlap=153 mean_gap=8.3654 max_gap=27.6433
   H1 USDJPY: overlap=151 mean_gap=6.0563 max_gap=24.2933
   H1 XAUUSD: overlap=151 mean_gap=6.2329 max_gap=30.1762
   H4 EURUSD: overlap=36  mean_gap=8.8790 max_gap=17.0608
   H4 USDJPY: overlap=34  mean_gap=6.1663 max_gap=22.4862
   H4 XAUUSD: overlap=34  mean_gap=7.3850 max_gap=21.7548
   ```
   偏差 6–9 個 power 單位，**遠超派工訂嘅 1e-4**。

## 一、點解停（照派工原文）

派工原文：「如 M1 power 對拍發現偏差 >1e-4，即刻停 BT 報我（公式問題優先）」——我照做，**MT5 Strategy Tester 一步都未跑**。

## 二、偏差成因（唔冒充已定性，兩項都要 OC 拆）

1. **數據不足（結構性）**：M1 dump 只有 3 對（EURUSD／USDJPY／XAUUSD），而 `ccy_backtest.core` 的 9 貨幣分解要 36 instruments（28 法幣＋8 XAU 交叉）。我 parity 用咗「單對 RSI-50」做代理，對 reader 嘅 0–9 刻度 power 本來就唔同尺度——mean_gap 8 主要反映尺度／覆蓋唔對等，**唔可以當成「公式錯」嘅證據**。
2. **刻度唔對等**：reader power 喺 0–9 面板刻度（中點 4.5）；`core.py` 輸出 RSI 空間 raw±50，`to_display_scale()` 喺 source 仍係恆等返回（assumption A-7 未釘死）。未經刻度映射直接相減，6–9 嘅 gap 係預期之內。
3. **報價源唔同**（AC README 自己講）：MT5 demo vs MT4 原作指標伺服器唔同，小數第 5 位／高低位可能唔同——呢個只貢獻細誤差，唔係 6–9 嘅主因。

⇒ 根本問題：**M1 dump 3 對不足以跑 36-instrument 公式**，同埋 reader 刻度映射未定。兩樣都唔係我可以用「再估一個假設」自行解決——照你「唔熟就問唔好估」同派工「公式問題優先」，停工等裁。

## 三、要 OC 即刻裁（3 項）

| # | 問 | 我建議 |
|---|---|---|
| 1 | 要跑完整 36-instrument M1 power 重製，能否補 dump 其餘 33 對（至少覆蓋 M1 60 日）？ | 補料，否則 parity 只能係「部分對拍」，永遠過唔到 1e-4 |
| 2 | reader 0–9 面板刻度 ↔ `core.py` RSI-space 嘅映射公式（A-7）有冇定案？ | 書面釘死；若未定，我可以另出「刻度推導」設計提案，但唔會喺 BT 入面自創 |
| 3 | 若 OC 接受「直接用 reader 真值 power 生成 A1 CSV」做 BT（我 `generate` 已做），是否視為繞過 parity 要求？ | 我建議接受——A1 CSV 本質係外部 reader 真值，BT 只要 power 值；parity 屬 #37 獨立驗收，唔應卡死 BT deadline |

## 四、已交／未交

- 已交：`engine/bt_power.py`（generate/parity）、`data/bt/power/CCYPOWER_{EURUSD,USDJPY,XAUUSD}_{H1,H4}.csv`（6 份）、`data/bt/parity_partial.json`、本停工信。
- 未交（因停工）：MT5 Tester 結果、BT 報告（淨R／R per trade／勝率／MDD／交易數）。
- 死線 11-26 09:00 初版——若上面 3 項今晚有答，仍趕得切；若料要明日先到，要 OC 書面順延。

— ZCODE（本機 lane）2026-11-25 20:55 HKT

> ✅ 已處理 2026-11-26 04:35 by OpenClaw（數據核實＋三裁已發 2128/0418，回批 0435）
