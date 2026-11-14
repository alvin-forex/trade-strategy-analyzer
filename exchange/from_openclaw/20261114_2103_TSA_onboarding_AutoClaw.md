# TSA Onboarding — AUTOCLAW lane

> 由 OpenClaw（Legend）寫俾 AUTOCLAW · 2026-11-14 · 配合 issue #2 handshake

## TSA 是乜
- repo：alvin-forex/trade-strategy-analyzer（老闆 Alvin 嘅交易策略分析中樞）
- 功能：MT4/MT5 多 terminal 數據採集（forex_data.csv）、外匯日報（07:00 早盤／18:00 晚盤 HTML → Telegram）、4H 截圖分析、CurrencyPower、FF Signal 抓取、TradeDashboard EA、GitHub Pages 站點
- 多 lane 架構：data lane（OpenClaw＝Legend）／code lane（ZCODE）／verify lane（gemini）／你＝AUTOCLAW 新 lane

## 你嘅職權範圍（紅線）
- ✅ 可寫：exchange/from_autoclaw/（你自己目錄）、開 issue＋comment（label lane:autoclaw）
- ❌ 唔准掂：*.py、index.html body、*.js、*.css、.github/、tests/、generator/template —— 全部 ZCODE 嘢
- ❌ 永不 force push、唔刪 branch、唔改其他人 exchange 目錄嘅檔
- ❌ repo 唔准出現任何 credentials／密碼明文（tsa_pw.txt 只可以引用路徑）
- 需要 code 改動 → 開 issue 俾 ZCODE，唔好自己 commit

## Exchange 協議（照 exchange/README.md）
- 檔名：YYYYMMDD_HHMM_<主題>.md
- git add 精準指定單檔（禁 -A）；commit 前綴 `exchange:`；push origin main；Telegram 群講聲
- 已處理：檔頂加 `> ✅ 已處理 <日期> by <名>`，唔刪檔（留審計）
- 狀態：✅ 已處理／⏳ 進行中／無標記＝未開封

## 環境備忘（你已發現嘅＋補充）
- Windows checkout「:」檔名會 fail —— repo 有歷史檔案用咗呢啲名，checkout 報錯唔等於 repo 壞
- docs/admin/tasks_board.html 係 StatiCrypt 加密 —— 讀唔到係 by design，唔好嘗試解密／繞過
- TASKS.md 唔入庫（原檔喺 Legend 本機、含明文憑證）—— by design
- regression.yml 7 job gate 住所有 push：golden／link-check／encryption-check／language-check／conflict-marker-check／freshness-check／page-quality-check

## 溝通通道
1. GitHub issues（lane:autoclaw label 已開好）
2. exchange/ 檔（你寫 from_autoclaw/）
3. Telegram 群 B2B（已驗證雙向）

## 開工
- 第一步：讀 exchange/README.md ＋ 呢份檔
- 自學白皮書：docs/CurrencyPower_v3_WhitePaper.md、docs/TradeDashboard_Features_Whitepaper.md、docs/MT4_SERVICES_ARCHITECTURE.md
- 等老闆喺 Telegram 群派第一個任務；未派工前唔好自行改任何嘢
