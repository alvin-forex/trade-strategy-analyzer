# 任務脫敏快照（PM lane 用）v1

> 來源：TASKS.md（私有原檔，含明文憑證，永不入庫）· OpenClaw 抽取 2026-11-14 22:05 HKT
> 規則：只含編號／任務／狀態摘要／ETA；狀態欄含敏感詞（密碼／key／token）即遮蔽
> 同步節奏：每次板面更新後重推。已排程／待做／等老闆動作段落 v2 按需求加。

## 🔄 進行中
| # | 任務｜執行 | 狀態（摘要） | ETA |
|---|---|---|---|
| 2 | 排名雙頁 KPI（#2）｜OpenClaw＋ZCODE | 🟡 首頁 KPI 已指雙頁；projection.html 已退役 | 11-16 |
| 6 | MT4 終端起機 F83D（#6）｜老闆＋OpenClaw | 🔴 F83D Logs 自 5-28 全空＝從未開機；其餘 3 終端在跑 | 等你開機 |
| 14 | S7 影子跟單 17547（#14）｜OpenClaw | 🔴 無實作痕跡（無 shadow 腳本、無 demo 落單記錄）；原 ETA 已到 | 11-17 |
| 16 | XAU timing 重跑（#16）｜OpenClaw | 🔴 根因確診（11-14 22:00）：全終端掃描無新於 7 月嘅 XAU M5 hst＝M5 圖未開；等老闆開一張 XAUUSD M5 圖即解鎖 | 11-15 06:00 |
| 18 | N/A reports 補 strategy（#18）｜OpenClaw | 🟠 根因已明（trades 級 strategy 缺），等 D2 全量重生 | 11-16 |
| 27 | 全站新 UI（#27）｜ZCODE＋OpenClaw | 🟡 889/906 有 sidebar.js；17 頁無（5 個新 signal 頁係真缺口） | 11-16 |
| 28 | 首頁空殼補齊（#28）｜OpenClaw＋ZCODE | 🟠 數據側未開（D1 JSON 停 2026-04-17） | 11-18 |
| 30 | AlgoForest set 檔（#30）｜OpenClaw | 🟠 CSV 側閉環（updated=29）；set 邊需 CDP 9222 | 等你開 CDP |
| 31 | remember 分層（#31）｜ZCODE | 🟢 靜態＋live PASS（詳情見私有原檔，敏感詞已略） | 11-15 |
| 33 | CCY v3 D1 flat 50（#33）｜ZCODE | 🔴 patch 未落地：v3.mq5 仍 3.11／0 命中 | 11-17 |
| 34 | CCY Reader 多 TF（#34）｜ZCODE | 🟠 D1/M30/M5/M1 全停；H1 H4 仍活 | 等你開圖表 |
| 35 | MT5 MCP 不通（#35）｜OpenClaw | 🔴 11-14 重測仍 000（NAT loopback 雙死） | 11-15 12:00 |
| 36 | CCY v3 等權開關（#36）｜OpenClaw | 🔴 未開工：InpEqualWeight 0 命中 | 11-18 |

## 📌 全域事項
| 事項 | 狀態 |
|---|---|
| CI regression 紅燈（golden baseline＋L23） | 已交 ZCODE（16:20 B 包＋issue #3）；首報期限 11-15 12:00 |
| gemini lane | 老闆 2026-11-14 裁決：暫停唔做；目錄封存 |
