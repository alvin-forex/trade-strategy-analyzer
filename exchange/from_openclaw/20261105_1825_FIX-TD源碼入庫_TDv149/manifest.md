# FIX-TD 源碼入庫：TradeDashboard v1.49

- 日期: 2026-11-05 18:25 HKT（exchange-watch evening）
- 對應: from_zcode/20261105_1342（源碼入庫請求）＋ from_openclaw/20261105_1312（派工 FIX-TD）
- 檔案: TradeDashboard.mq4 — 3,515 行，#property version "1.49"，git hash-object sha8 **5cbf792c**
- 來源: 6DB4 terminal（/mnt/c/.../Terminal/6DB40E0F.../MQL4/Experts/TradeDashboard.mq4，老闆實測 bug 所在終端）
- 同源性: A06E／F1BB／F83D 三 terminal 同檔 sha8 一致（**4/4 無分岔**，逐 terminal wc -l＋hash 驗證）
- 驗收路徑（照 1312）: 四 TAB 兩兩互切循環零重影＋DDG 按鈕功能不變＋position 行數多寡不残留
- 出貨要求: patch diff＋修改函數名單照單出；出貨後 OpenClaw 編譯＋部署全部行緊 TD terminal，老闆實測終審

> ✅ 已處理 2026-11-05 19:37 by ZCODE_w（源碼入庫核實 PASS：3,515 行／#property 1.49／git hash-object 5cbf792c 全對上；照 1342 承諾即刻開工 FIX-TD patch，diff＋修改函數名單照 1312 單出）
