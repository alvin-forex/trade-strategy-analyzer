# FIX-TD9 D — MT5 側（725B72F2/MQL5/Experts）清理建議

實測 9 個 .mq5：

| 檔 | 大小 | 判定 |
|---|---|---|
| out.mq5 | 80,305B（10-15） | **TradeDashboard5 原型**：頭註「MT4 port of TradeDashboard1.39 (broken summary profile)」、version 1.01——已被正式 TradeDashboard5.mq5（108,558B/v1.51）完全取代。建議：備份後刪（我執行，備份入 ea-repo cold-storage 分支或 exchange 附件） |
| AngelGold_v4.mq5 ＋ AngelGold_v4_M15.mq5 | 50,446B／50,457B（差 11B） | 近全同（得一兩行 input/常數差）。建議 ZCODE 評估合併為一檔＋input 分 TF（code lane）；合併前兩檔照跑 |
| GoldSupporter／HelloEA／MarketGlanceExporter／PlanExecutor／Thor | 各一 | 無重複，不動 |

注：v1.60 到貨後 TradeDashboard5.mq5 會被換版，out.mq5 刪除時機建議同場（一次過清）。
