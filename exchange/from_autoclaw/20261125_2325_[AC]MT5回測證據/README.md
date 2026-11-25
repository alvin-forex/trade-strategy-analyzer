# [AC] MT5 回測證據（2026-11-25）

老闆質疑「唔見你做」，所以把原始證據公開，可自行核對。

## 一、這次跑了甚麼

| 項 | 值 |
|---|---|
| 終端 | MetaTrader 5 build 6323（本機，Alpari-MT5-Demo） |
| 品種／時框 | EURUSD / H1 |
| 期間 | 2025-01-01 → 2026-11-01 |
| 程式 | `Experts\Examples\MACD\MACD Sample.ex5`（MT5 內建示範 EA，用來驗證流水線會真交易） |
| 起始資金 | 10,000 USD，槓桿 1:100 |
| **結束結餘** | **8,490.87 USD** |
| Tick 數 | 2,686,350 |
| K 棒數 | 11,389 |
| 執行時間 | 1.695 秒（含 tick 前處理） |
| 執行方式 | 無 GUI：`terminal64.exe /config:<ini>`，跑完自動關閉 |

## 二、同一晚的另一次跑（骨架程式，證明會跑但零交易）

| 項 | 值 |
|---|---|
| 程式 | `Experts\ExtraCCYPower_EA.ex5`（ZCODE 交的骨架 v1.04） |
| 期間 | 2026-10-01 → 2026-11-09 |
| 結果 | 跑完，結餘 10,000.00 不變、零交易 |
| 原因 | 骨架只寫 tester summary，未實作下單（log 明寫 `SKELETON: tester summary written`） |

## 三、原始檔案（本目錄）

- `tester_log.txt` — 3,001 行原始 log，含兩次跑的完整記錄
- `tester_config.ini` — 第二次跑的設定檔（可照用重跑）

關鍵原文（可直接搜）：
```
EURUSD,H1 (Alpari-MT5-Demo): testing of Experts\Examples\MACD\MACD Sample.ex5 from 2025.01.01 00:00 to 2026.11.01 00:00
final balance 8490.87 USD
EURUSD,H1: 2686350 ticks, 11389 bars generated. ... Test passed in 0:00:01.695
```

## 四、重跑方法（任何人可驗）

1. 把 `tester_config.ini` 放在 MT5 資料夾的 `config\` 下
2. 關閉 MT5，執行：`terminal64.exe /config:"<資料夾>\config\tester_config.ini"`
3. 約 2 秒後自動關閉，`Tester\logs\` 會出新 log

## 五、限制（要講清楚）

1. 這是**流水線驗證**，不是策略評估——示範 EA 的盈虧無意義（蝕 1,509 是正常，它只是教科書範例）。
2. 要評 AngelGold 或 COPY ON LOSE，必須先有可跑的 MT5 版本程式；AngelGold 現時只有 MT4 執行檔，MT5 跑唔到。
3. 期間覆蓋：MT5 本機 H1 由 2025-01 起（M1 由 1990／2015 起，可自行聚合）。

— AUTOCLAW 2026-11-25 23:25
