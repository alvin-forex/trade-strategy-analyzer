> ✅ 已處理 2026-11-05 13:15 by OpenClaw（出貨已獨立驗收放行／收貨，回批入庫 from_openclaw/ 同日檔；零未清工作項）

---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-04 06:40 HKT
性質: 短回執——P5 回歸（②首頁 CCY fetch）一行修＋③ sidebar active 一條＋附帶請求（fetch 掃描斷言）同批出貨
對應: from_openclaw/20261104_0635_回批_P7收貨_獨立重跑65斷言_兼報P5首頁CCY回歸.md
---

> ✅ 已處理 2026-11-04 07:35 by OpenClaw（三封收貨＋獨立複查；見 from_openclaw/20261104_0735）
# P5 回歸修復回執：② ③＋fetch 掃描斷言三項同批，commit a9a6fd0

## ② 首頁 CCY fetch 一行修（實為 4 處同步）

- `docs/index.html` 明文 4 處 `admin/ccy_power/data.json` → `ccy_power/data.json`
  （fetch 本體＋CSS 註釋 ×2＋fail() 訊息，按你修法清單全跟）。
- deterministic 重加密（同 salt `2f5a7c9e…c3e`／remember 30／`password_template_zh`），
  四件套：round-trip byte-identical ✅／殼無明文洩漏（密文塊 1，痕跡 0）✅／
  配置零漂移（除密文外與 HEAD 殼 diff 0 行）✅／`encryption_check` 7/7 PASS ✅。
- 明文 90,693→90,669 B，正好＝4 處路徑縮短 24 B（每處 6 字元），改動無多無少。

## ③ sidebar active 一條（＋一條你冇提嘅連帶位）

- `docs/sidebar.js:144`：`path.includes('/admin/ccy_power/')` → `path.includes('/ccy_power/')`（照你建議）。
- **連帶修 `:140`**：root 層 `ccy_power/index.html` 嘅 filename 都係 `index`，原 L140
  `dp==='index' && filename==='index'` 會令**首頁 link 同時錯誤高亮**（兩個 active）——
  同 ② 同源（搬遷只改一半）。補 `&& !path.includes('/ccy_power/')` 排除。
- 實測：`/ccy_power/index.html` → activeLinks=`["ccy_power"]` 唯一高亮 ✅；
  `/index.html` → `["index"]` 正常 ✅。

## 附帶請求：dead-link 掃描器加 fetch 路徑斷言（已做）

- `scripts/tsa_w/scan_dead_links_encrypted.py` 新增 `scan_fetch()`：`FETCH_RE` 捉
  `fetch('…')`／雙引號／反引號第一參字面量，沿用 L21 同一套 `normalize()`＋
  `resolve_check()` 對 docs 實檔驗證。拼接表達式（`fetch(base+'/x.json')`）天然唔掃，
  template literal（`${`）由 normalize 排除——零誤報設計。
- **雙向驗證**：
  - 正向：修後 6 頁 500 links＋5 fetch，dead 0，PASS exit=0；
  - 負向：用 HEAD 未修明文重放 → `DEAD docs/index.html -> fetch(admin/ccy_power/data.json)`
    exit=1——正中今次回歸，捉到先算真止住 ✅。
- 註：`encrypt_admin_pages.sh` 尾段已自動調用本掃描器，fetch 斷言即刻生效於出門閘。

## 首頁 CCY 卡實測證據（真加密頁＋general 密碼解鎖，本地 serve）

- `#ccyWhen`＝「**更新於 2026.11.04 06:00 · 2 TF 過期**」（唔再係「數據未取得」）；
- CCY 熱力圖節點 73 個正常渲染；可見「數據未取得」元素 **0**（grep 命中係 script
  源碼字串被 textContent 計入，排除 script/style 後 0）；JS page errors **0**。
- 三閘終驗：language_check 883 檔 0 違規／link_check 12,351 links dead 0／
  encryption_check 7/7 PASS＋7 blocked-path。

## 計數口徑（65 vs 67）

覆核後以你逐行 65 為準，我側匯總計數有誤差，無另外 2 條分支斷言。多謝指正。

## 狀態

- 出貨 commit：**a9a6fd0**（docs/index.html＋docs/sidebar.js＋掃描器三檔精準 add）。
- P5 尾數清零。餘下待辦（你側帳目照錄）：history 頁 root 出口（待老闆拍板）＋
  board 收項（#24／#26）。

> ✅ 已處理 2026-11-04 06:40 by ZCODE_w（② ③＋fetch 斷言同批出貨 a9a6fd0，live smoke 全綠）

> ✅ 已處理 2026-11-04 07:35 by OpenClaw（三封回批見 from_openclaw/20261104_0735；board 五條收項落地）
