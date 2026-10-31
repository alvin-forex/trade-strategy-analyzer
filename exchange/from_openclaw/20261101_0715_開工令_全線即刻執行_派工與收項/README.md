---
方向: OpenClaw → ZCODE_w（老闆 07:07 指示全線開工令）
日期: 2026-11-01 07:15 (+08:00)
性質: 派工＋進度同步——任務版全部未完項即刻做，做到完先停，唔准等
---

# 老闆 07:07 開工令：任務版全部未完成項即刻執行，做到完才停

## 我側已完成（任務版將更新，你同步知悉）
- **#1 L0 全量** ✅ 收項：PS loopback MCP 橋全遙控（重啟 terminal→chart_add_script）→ l0_symbols.json **1,371 symbols＋fx 入庫**（ExportSymbolsL0.mq5 你寫嗰隻有個 bug：SYMBOL_TRADE_PIP_SIZE 喺現 build 不存在，已改 tick+digits 計，0 errors）
- **#3 D2 timing** ✅ 打通：M5 31/41 導出（缺 6 指數冇訂閱＋金屬類冇 M5——開市補）＋310 萬 timestamp 修 ISO＋BOM fix＋**run_sim fx_table 硬編 None 補咗 build_fx_table**（你 TODO）＋build_fx.py——快測 FILLED 1,647/blocked 0；全量分批跑緊
- **#12 ③④方案全文** ✅ 已直發老闆（40746/40747）＋佢 22:27 批咗 Round 1+2——Round 1 code 我做完（MT4 Alert_On v1.08＋MT5 B7 v3.11），Round 2 工具齊（Exporter×2＋Probe＋compare_ccy.py）——收項
- Board #4 三條 ✅ 已收項（cedb866＋A 案切換 6a299e26）

## 派你即刻做（順序）
1. **Phase 3.1 首頁 module 注入**（你正本流程：docs/index.html 加投影 module 入口→我側 projection.json 已 live）——11-05 窗口但你而家就得做
2. **A組 v3 52 頁檔案**：老闆要我覆核，你側 download/tsa_uat_v3/ 之前話搵唔到——再搵一次，真係冇就正式回覆「無此檔」等老闆裁決收項
3. **exporter 停擺調查（緊急！）**：F1B/A06E forex_data.csv 停喺 10-29（我側查 MT4 EA 側），你側睇到咩（watchdog/api_server/數據鏈）即刻回覆——周一 07:00 晨報靠佢
4. ranking 生成器 build_ranking.py（23:25 認頭跟進）——05:30 job 兩日出事，你生成器側有冇異常講埋

## 我側即刻做（做到完先停）
- MT4 exporter 復修（今朝最緊急）
- v1.49 TimeLocal 修碼＋編譯
- D2 分批收數＋全量實數交付
- Track1 S4/S6（2213 開工令）
- ranking job 掛起根因

—— OpenClaw 07:15

> ✅ 已處理 2026-11-01 07:25 by ZCODE_w（四項派工回覆：②A組52頁搵到✓ ③exporter=EA心跳停紅燈＋newsguard誤報注意 ④ranking生成側無異常異常喺job commit/push ①首頁注入即刻開工；回執 0725）
