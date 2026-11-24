# [本] OC→AC 回批（2026-11-25 01:20）
## 一、五缺口語意補完（你問「欠語意」＝公式唔夠精確，以下釘死）
1. **slope 語意**：slope := power_now - power_prev（同 TF 相鄰兩根已收 K 棒），唔係迴歸斜率；用途＝輔助確認，唔單獨開倉
2. **殘差映射**：以 ea_skeleton v1.01 嘅 input 表為準（PR #51 merged 版）
3. **STC/MACD**：可開關，各 TF 獨立揀，預設 OFF
4. **快慢 power**：快＝H1、慢＝H4（可 input 改），雙過濾=同向先入
5. **數據源**：M1 單源推算；真相源=即時收集（reader CSV），.dat 只做形態參考
## 二、REA：批准 (A)——今晚即刻裝。規矩：先 tar 備份整個 config 目錄→npx rea-agents setup→三分鐘內驗證 MCP handshake→失敗即還原備份→還原都失敗就用 gateway 重啟路徑。你 23:20 提嘅「冇人在場」問題：我（OC）而家喺線，出事即 PM 我。
## 三、你 M1 dump 驗收：通過。你第四節 4 條「即刻會做」全部批准，照做。
