# 缺陷補充：signal_ranking.html 漏網（對賬 888 之外的一頁）——併入 W2 一齊做

老闆 07:58 實測發現 signal_ranking.html 仲係舊 UI。我方覆核確認：呢頁唔喺 P0 76 名單、唔喺 W1 71 名單——**對賬漏咗**。

## 事實
- docs/signal_ranking.html（199KB，title 🔐 Alvin Forex 報告中心）：tsa_tokens=0、sidebar=0、remap 色 0——完全未觸
- 佢係 ranking 每日重生成 cron（05:31）嘅產物 → **一定要喺生成器模板層改**，逐頁 patch 會被次日 cron 蓋返舊樣
- 加密頁規則照舊：只准生成器／明文層改

## 指令（併入 W2，唔另開波）
1. 搵出 signal_ranking.html 嘅生成器模板，做 W1 同款處理：NAV 四件＋tsa_tokens＋remap 三色（#0F1520／#5CA8FF／#A8B4C4）＋語義色保留
2. 改完即刻手動跑一次生成器出貨（唔使等聽日 05:31 cron），加密閘照過
3. 驗收：我方 ui_acceptance.py 對呢頁單頁出數（--glob docs/signal_ranking.html）
4. W2（2b 語義域）其他範圍照 0700 單不變

## 另外兩頁老闆提及（已排期，唔使動作）
- ccy_power/index.html → W5（ccy_power 4 頁，11-08 18:00）
- reports/index_43024.html → W5（reports 475 頁，11-08 18:00）
- forex_news.html → 已有新 UI 底（NAV＋token＋#0F1520 全在位），淨裝飾統一屬 W2 2b 波

## 首頁 index.html 備註
root 層冇 sidebar 嘅只有兩頁：index.html（W7/#28 module 改建，故意的）＋signal_ranking.html（今次缺陷）。其餘 145/147 root 頁已有新 UI。

> ✅ 已處理 2026-11-05 08:35 by ZCODE_w（生成器層修已出貨：回執0812＋出貨0825＝push 48b4a82，151行數據零變動；本章為補登——上鐘出貨漏add蓋章檔）
