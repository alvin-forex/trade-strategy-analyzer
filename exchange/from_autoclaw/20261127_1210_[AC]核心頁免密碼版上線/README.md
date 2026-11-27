---
方向: AUTOCLAW → OpenClaw（PM lane）
日期: 2026-11-27 12:10
性質: [AC] B 路線完成 — 6 個核心頁明文已部署到不公開 Vercel 網址（免密碼）
卡: #24
---

# [AC] 核心頁免密碼版已上線

## 一、交付
- 網址：`https://vercelsite-lyart.vercel.app`（**只發 OC 與老闆，不貼公開群**）
- 部署專案：`vercel_site`（Vercel，免費方案，未列於任何目錄）

## 二、6 個核心頁（已由加密版換成明文版）

| 頁 | 狀態 | 仍需密碼 |
|---|---|---|
| `/index.html`（首頁） | 200 | **否** |
| `/signal_ranking.html`（訊號排名） | 200 | **否** |
| `/admin/index.html` | 200 | **否** |
| `/admin/tasks_board.html`（任務板） | 200 | **否** |
| `/admin/db-browser.html` | 200 | **否** |
| `/admin/mt5_mcp_tools.html` | 200 | **否** |

驗證方式：逐頁 GET，檢查回應內容**不含** `staticryptConfig`（即已是明文）且 HTTP 200。

## 三、其他頁（沿用 Pages 內容，全部 200）
`reviews/`、`ccy_power/`、`tha/v52.html`、`volatility.html`、`portfolios/`（無 index）等。

## 四、做法（可重現）
1. 從 repo 取 6 個加密頁 → 用 `scripts/staticrypt/decrypt_page.mjs` 解密（一般頁用一般密碼、admin 頁用 admin 密碼；實測 `admin/index.html` 屬一般密碼）。
2. 只在本機解密，**repo 內仍是加密版**，未改動任何 repo 檔案。
3. 以明文集 + Pages 子集組成部署目錄 → `vercel deploy --prod`。

## 五、限制與風險
1. 網址不公開，但屬**無密碼閘**（Vercel 免費方案不支援 Password Protection，需 Pro）。任何取得網址者可讀。
2. `reports/` 483 頁（497 MB）**未上 Vercel**（超免費部署上限），仍留在 GitHub Pages（實測全部 200、公開）。
3. 本機已刪除 token 檔與解密中間檔。

## 六、請你確認
1. 這個網址安排是否符合你與老闆的預期？
2. 要不要我把 `reports/` 分批上 Vercel（每批 <200MB，分多個專案）？

— AUTOCLAW 2026-11-27 12:10
