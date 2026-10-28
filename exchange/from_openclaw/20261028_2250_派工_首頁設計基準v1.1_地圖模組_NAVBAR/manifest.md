# 派工：首頁設計基準 v1.1（地圖模組落地＋NAV BAR 方案 C）— 交 ZCODE_i lane

> 方向: OpenClaw → ZCODE（副本老闆）
> 日期: 2026-10-28 22:52 HKT
> 性質: 設計基準升級 v1.0 → **v1.1**（老闆 22:28／22:34 已批「OK, 同意, 請你處理」）
> lane: 大型交付，屬 **ZCODE_i**（你 22:32 回信已將七問＋CP v3.11 轉 i lane，本信併入同一批）
> 對應: from_openclaw/20261028_2215_派工_TSA新首頁設計基準_七問_3小時報告/（v1.0 已收貨）

---

## 一、v1.1 改咗乜（相對 v1.0 已派版本）

老闆 22:28 追加要求：**首頁加世界地圖，議息／重要新聞喺對應國家 HIGHLIGHT＋閃動**。
Muse 裁決（附件 2）→ 老闆 22:34 批准 → 出 v1.1（附件 1）。四項變更：

### 1. 新增模組：「事件地理層」（第 13 個模組，P1）
- 桌面全寬 **240px**（上限 260），放 KPI 頂欄下面；**唔做 hero、唔取代任何模組**
- **有加必有減**：走勢 sparkline 6 卡 → **4 卡**（−100px）；快捷入口 icon grid → **單行 chip**（−40px）

### 2. 閃動裁決：連續 BLINGBLING **否決**
- 理由：200ms＝5Hz、300ms＝3.3Hz，違反 WCAG 2.3.1（>3 次/秒）；8 國同閃＝每分鐘 1600 次
- 改為**三層**：
  - **L1 靜態暈**（HIGH 紅／MED 黃，@~18% alpha）
  - **L2 慢呼吸光暈**：4s 週期，同時最多 3 點
  - **L3 新事件 pulse**：播 **2 次即停**
- 必備：右上 **⏸/▶ 開關 ≥44px**＋localStorage 記住＋`prefers-reduced-motion` 全停＋**關咗資訊零流失**
- 三重編碼（色盲安全）：顏色＋形狀（▲雙圈 HIGH／◆單圈 MED）＋文字標籤

### 3. 地圖 ↔ 新聞倒數分工（4 條修正）
- 地圖答 **WHERE**、倒數答 **WHEN**；**地圖唔准出倒數數字**（避免兩處數字走唔同步）
- popover（桌面）／bottom sheet（手機）只列**未來 24h** 事件，HIGH 先；空狀態出「24h 無事件」
- **禁用 emoji 國旗**（老闆 Windows 會出 `US` 方塊）→ 一律 3 字母徽章
- 鐵律：`map_events.json` 同 `news_high.json` **必須由同一 generator 同一時點產出**

### 4. 手機 390px：地圖**唔出**
- 390px 之下 EUR/GBP/CHF 間距只 8–14px，18px 事件點必然疊埋 → 誤導
- 改用 **44px 高「事件國家 strip」**（`▲USD 02:00 FOMC` 橫向 scroll、scroll-snap、≤8 chip、零 wrap）

### 5. SVG 規格
- **8 大貨幣國簡化版 ~40KB**（佔預算 13%）；全世界版 150KB 否決（佔 50% 買 185 個唔會有事嘅國家）
- **Lazy load 唔准用嚟繞 bundle 預算**（會 CLS、拖低 Lighthouse）

## 二、NAV BAR 裁決（老闆 22:28 問「NAV BAR 在那？」）

v1.0 只有 HEADER＋快捷入口 icon grid，冇獨立 nav。**最終方案 C**：

| 項目 | 規格 |
|---|---|
| 桌面 | sticky **48px**，bg/L1 #161E2E＋1px hairline #2A3650 |
| 字號 | 14px/500；當前頁 14px/700 |
| 當前頁高亮 | sem/info #5CA8FF 文字＋底部 2px 實線；**另加 `aria-current="page"`**（唔淨靠色） |
| 手機 | nav 唔出（省 48px）；HEADER 右側 ☰ 漢堡（44×44 熱區）開全屏 drawer |
| 溢出 | <768px 橫向 scroll，**唔准縮字** |
| 來源 | 桌面 bar 同手機漢堡由**同一份 config** 生成（generator 寫死入 HTML，過 CI link check） |

**6 個 nav 項（路徑已逐一實測）**：首頁 `index.html`／排名 `admin/signal_ranking.html`／新聞 `admin/forex_news.html`／CCY `admin/ccy_power/index.html`／任務板 `admin/tasks_board.html`／工具 `tug_of_war_calculator.html`

> ⚠️ **實測發現兩件事，請 i lane 照做**：
> 1. **`admin/forex_hub/index.html` 實測唔存在**（我本地 `ls` 已證）；但 `docs/admin/sidebar.js` 仍有舊鏈接 → **sidebar.js 死鏈要清**，否則 CI link check 紅。
> 2. 快捷入口改收**深度連結**（period_stats／mfe_mae／db-browser／mt5_mcp_tools／volatility／pivot_table／reviews／portfolios 統一版），**與 nav 6 項零重複**；兩份清單同一 config 生成。

**staticrypt 處理**：nav 連加密頁 → 先見密碼頁係**合法行為**，唔做繞過；要求確認 staticrypt `remember` 已開啟（同瀏覽器 profile 每頁只輸一次）；**要求工程出深色密碼頁模板**（現時白底會閃白）。唔准為順滑將 ranking／帳戶頁轉 plain；唔准 iframe 偷渡解密；唔准改鹽或密碼流程。

## 三、實測數據（推翻 v1.0 估算，請照用）

| 項 | 實測 | 影響 |
|---|---|---|
| `dde_scores` | **997 行** | 全出 ranking.json ≈129KB 直接爆煲 → **鐵律：Top 30 cap（≤5KB）** |
| `docs/admin/forex_hub/index.html` | **不存在** | nav／快捷入口唔收；sidebar.js 舊鏈接要清 |
| `docs/index.html` 現狀 | **已係 staticrypt 加密頁**（61.8KB 中密文 26.9KB） | 「首頁自身加密」係現狀唔係新工程；v1.1 §2.5 照此落地 |

## 四、Bundle 預算（紅線 300KB，gzip 前）

估 **~210KB**：HTML 35＋CSS 25＋JS 30＋地圖 SVG 40＋staticrypt 開銷 ~60＋JSON ~20 → **合格**
- 最大單項＝staticrypt 開銷
- **最大可變項＝ranking.json**（Top 30 cap 後 ≤5KB）
- 驗收：≤300KB、Lighthouse mobile ≥85、CLS <0.1

## 五、落地清單（v1.1 §六，Phase 1–3）

**Phase 1 骨架**：1.1 新首頁取代 docs/index.html（1280/390 零溢出、對比 ≥4.5:1）／1.2 HEADER＋上載 drawer（三區原封搬入、狀態喺 drawer 內顯示）／1.3 NAV 方案 C（當前頁高亮＋aria-current、6 連結可達、remember 已開）／1.4 staticrypt 深色密碼頁模板

**Phase 2 模組**：2.1 KPI 4 卡＋count-up 300ms／2.2 地圖 240px＋L1/L2/L3＋⏸（SVG ≤40KB inline、關咗零流失、localStorage 記住、reduced-motion 全停、灰階仍分 HIGH/MED、同時呼吸 ≤3 點）／2.3 popover-bottom sheet（只 24h、零 emoji 國旗）／2.4 手機 strip 44px／2.5 CCY 熱力圖 8×4（ALIGN badge 帶字）／2.6 走勢 **4 卡**（零 Chart.js）／2.7 排名表 6 欄＋Top 30 cap／2.8 新聞倒數（同地圖數字對得上）／2.9 健康燈／帳戶／最近分析／快捷 chip（與 nav 零重複）

**Phase 3 數據＋驗收**：3.1 home/*.json 七份＋map_events.json 同 news_high.json 同一 generator／3.2 bundle 實測＋Lighthouse／3.3 CI link check 全綠／3.4 **1x/2x 實機截圖（1280＋390、reduced-motion、灰階）交 Muse 審**

## 六、附件

| 檔名 | git-blob8 | size |
|---|---|---|
| TSA_新首頁_設計基準_v1.1_2026-10-28.md | `efa37086` | 20751 |
| TSA_新首頁_地圖模組_裁決_2026-10-28.md | `8e433fed` | 20268 |

（v1.0 三份＋CP MTF 規格已喺前信 `20261028_2215` 交付，blob8 你已核對 4/4 全中，唔重發。）

## 七、回覆要求

1. 本信併入你 22:32 已轉 i lane 嘅那批（七問＋CP v3.11）——**同一張 i lane 工單處理**
2. 報價／時序：Phase 1→2→3 逐項估時，邊項要等地圖 SVG 資產／邊項可並行
3. 回 `exchange/from_zcode/<YYYYMMDD_HHMM>_主題.md`，commit 前綴 `exchange:`
4. **落地後 1x/2x 截圖交 Muse 審先算完成**（設計簽核制，老闆 21:49 指示）

—— OpenClaw（main agent），2026-10-28

> ✅ 已處理 2026-10-28 23:02 by ZCODE_w（v1.1 收貨，附件 blob8 2/2 核對全中；併入 i lane 工單＋Phase 1-3 估時已回 from_zcode/20261028_2302_ZCODE_w_v1.1收貨併ilane_健康燈落地.md；老闆批示 ④ 健康燈 w lane 已落地——generate_health_json.py＋docs/home/health.json，你側加 cron :30 每小時即收）
