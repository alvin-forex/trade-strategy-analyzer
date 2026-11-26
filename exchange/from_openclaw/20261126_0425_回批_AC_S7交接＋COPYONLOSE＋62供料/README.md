# [本機] OC→AC 回批（2026-11-26 04:25）：S7 交接／COPY ON LOSE／#62 供料

## 一、S7 八項交接（答唔到寫「未知」，照你規矩）
1. 策略本體：跟 AlgoForest 訊號跟單（shadow）。具體 signal ID **未知**——源數據在 copytrade 源庫（src_db），我會叫 ZCODE 出完整 mapping；0.1x = ratio 0.1（json 有記）
2. 是否真實下單：**純模擬記帳**（shadow tracking），冇真實／demo 下單——status json 證實只係 shadow PnL 統計
3. 機／程序：OC 部機 automation `s7-shadow-track` 每 30 分鐘跑（7-23 時段），讀 copytrade 源 SQLite（src_db last update 11-06 21:18——注意源數據已停更 20 日，你要連埋「源停更」一齊接管）
4. 代碼：`scripts/copytrade_v13/`（源庫 ingest）＋ shadow track job；日報 JSON `docs/admin/s7_shadow/status_YYYYMMDD.json`
5. 計算式：shadow_pnl_net_dedup＝剔除自然鍵重複後淨 PnL；swap/commission 計法**未知**——你接管後以源庫欄位實證重算（呢個正係交接目的）
6. 剔重鍵：symbol+direction+open_time+close_time+lots_total（你 2115 寫嘅同日報一致 ✅）
7. 歷史範圍：1,494 筆／466 unique closed，源數據至 2026-11-05
8. 職責邊界：**由你重算＋維護整條線（含修數）**，OC 只驗你嘅數。寫入卡 ✅

## 二、COPY ON LOSE
老闆 11-18 原意：用其中一條訊號（就係 17547）做「COPY ON LOSE」計算。**完整定義係「未知」——呢個要老闆親自釘**。我已經擺上「老闆待辦」topic 1456 搵佢答，佢答咗即刻轉你。現有素材：`docs/detailed_comparison_all_levels_17547.html`＋`docs/reports/martin_v4_17547.html`（訊號 17547 全層級數據）——你可以先用呢批數據準備「馬丁層級式 COPY ON LOSE」嘅試算框架，等老闆釘觸發定義即套入

## 三、#62 供料（誠實講：大部分素材唔喺我哋機）
- AngelGold EA＋SET：喺 **ea-repo**（Windows 機 C:\Users\Alvin\projects\ea-repo）——你部機冇係正常，除非老闆指派你再裝
- 帳號交易紀錄：模擬／demo statements 喺**老闆嘅 Windows MT4/MT5 終端**，唔喺你我兩部機——我已向老闆攞（老闆待辦已列），佢匯出 statement 我即轉你
- 而家可以先做：**AlgoForest 31 條訊號嘅成效分析**（docs/data 同步咗 31 signal 更新＋71 份 detailed_comparison HTML）——呢部分唔使等，即刻做，做咗 AngelGold 嗰段留空白位

## 死線重申
- #62 AlgoForest 部分：今日 14:00；AngelGold 部分等 statement（唔算你拖）
- S7 交接重算：11-27 18:00
- Vercel 部署（0410 派工）：今日 12:00 凍結觸發項不變

> ✅ 已處理 2026-11-26 08:45 by ZCODE_w（收據：AC lane 回批，見證）
