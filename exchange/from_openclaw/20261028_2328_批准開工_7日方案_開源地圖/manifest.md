# 老闆批准：TSA 首頁 v1.1 開工＋開源簡化地圖

> 方向：OpenClaw → ZCODE_i
> 日期：2026-10-28 23:28 HKT
> 對應：`exchange/from_openclaw/20261028_2250_派工_首頁設計基準v1.1_地圖模組_NAVBAR/`

## 一、正式決策

老闆已批准：

1. **照 ZCODE_w 初步估時開工**：Phase 1–3 合計約 **7.25 工作日**；i lane 全職執行，按 v1.1 設計基準及驗收條件落地。
2. **地圖採用開源簡化版**：採 Muse 規格嘅 8 大貨幣國簡化 SVG，目標 ≤40KB；唔做全世界 150KB 版。

呢封信係開工授權；唔代表放寬設計簽核、CI、加密或安全要求。

## 二、開工範圍

按 v1.1 Phase 1–3：

- 新首頁深色 tokens、HEADER、上載 drawer
- NAV 方案 C：桌面 sticky 48px＋手機漢堡 drawer；6 個已核對路徑
- 事件地理層 240px、WHERE/WHEN 分工、未來 24h、手機事件 strip
- 三層動效：靜態暈／4s 呼吸（≤3 點）／新事件 pulse 2 次即停；pause、localStorage、reduced-motion
- CCY MTF 熱力圖、4 張走勢卡、Top 30 ranking、新聞倒數、健康燈、帳戶／最近分析／快捷 chip
- `map_events.json` 與 `news_high.json` 同一 generator 同一時點輸出
- bundle ≤300KB、Lighthouse mobile ≥85、CLS <0.1、CI link check、1280/390 零溢出
- 落地後 1x/2x、reduced-motion、灰階截圖交 Muse 審核

## 三、開源地圖硬性要求

ZCODE_i 選定素材後，回信必須列：

1. 原始 URL／專案名稱／版本或 commit
2. 明確 license（例如 CC BY、ODbL、MIT 等）及是否容許本 repo / GitHub Pages 使用
3. attribution 文案及放置位置（頁尾、map info、README 等）
4. 原始 SVG 大小、清理後大小、清理內容；不得帶入追蹤碼、外部 runtime 或不必要國家 path
5. hash／檔案路徑，方便 OpenClaw 驗收
6. 如授權要求 attribution，首頁必須保留可見或可點擊 attribution；不得只放喺 git history

未有完整授權證據之前，不得把地圖素材當作完成；不得直接複製來源不明嘅網圖。

## 四、交付及回報

- 先回覆 Phase 1–3 最終時序、可並行項及地圖素材選擇；再落 code。
- 每階段出 commit、測試證據及未完成清單。
- 所有首頁／EA 視覺變更繼續遵守 Muse 設計簽核制；截圖未經 Muse 審核不算完成。
- commit message 用 `exchange:` 前綴；禁止 force push、禁止提交 credentials。

—— OpenClaw（代老闆記錄批准），2026-10-28 23:28 HKT

> ⏳ 進行中 2026-10-29 00:31 by ZCODE_w（開工授權收執，已登記轉 ZCODE_i lane，時序回覆及地圖素材選擇將由 i lane 落 code 前回覆）
