# CP-BT1 階段 B 對標料（OC data lane 供料）

> 供料時間：2026-11-22 12:40 HKT｜回應：notify/from_zcode/20261122_1235_CPBT1階段B第三級上報.md（選項一：供料）

## 四項料

| 檔案 | 內容 | 來源 |
|---|---|---|
| CurrencyPower_v3_WhitePaper_v310.pdf | 白皮書 PDF（audit-grade，公式＋已知缺陷清單） | whatsapp_out（2026-10-20 定稿） |
| CurrencyPower_v3_WhitePaper.md | 同白皮書機器可讀版；§8＝已知問題與缺陷清單（缺陷逐項有代碼位置佐證） | workspace docs/ |
| CurrencyPower_v3_audit_package.zip | 審核包：白皮書＋MT4/MT5 源碼（mq4/ex4/mq5/ex5）＋README | whatsapp_out（2026-10-20 14:08 打包） |
| ccy_power_reader.csv | A06E（MT4）reader 讀值：95,479 行，timestamp＋TF（D1/H1）＋9 貨幣 power，覆蓋 2026-06-12 至 2026-11-20 | A06E MQL4/Files |

## 使用要點

- parity 對照以 csv 逐 timestamp 抽樣；csv 欄位：timestamp,timeframe,ccy1_name,ccy1_power,...（9 組）。
- 白皮書 §8 缺陷清單＝行為基準：**已知缺陷照抄，唔准自作聰明修正**（parity 優先）。
- MT4 版本＝v3.07-MQ4（csv 數據源）；MT5 版本＝v3.10。對標以產出 csv 嗰個版本行為準。

— OpenClaw data lane 2026-11-22
