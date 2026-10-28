# TSA 新首頁 — 設計基準 v1.1（2026-10-28）

> 文件性質：TSA 新首頁線**唯一設計基準**，取代 v1.0（設計師回應）＋ 地圖模組裁決 兩份文件嘅規格部分；內容衝突時以本文件為準。
> 變更來源：老闆批准地圖模組裁決（「OK, 同意」）＋ 老闆 22:28 追問「NAV BAR 在那？」→ 本版補 NAV 裁決。
> 紅線不變：純靜態無 build step、bundle <300KB、不引 framework／font CDN／yfinance、數據 pre-generated JSON、390/1280 兩寬零溢出、開發落地前須設計師簽核。

---

## 一、Wireframe v1.1（桌面 1280 ＋ 手機 390）

### 1.1 模組清單（13 個）

| # | Pri | 模組 | 內容 | 桌面位置 | 手機位置 |
|---|---|---|---|---|---|
| 1 | P0 | KPI 頂欄 | 4 大卡：當月增長／排名 Top3 升跌／今日 HIGH 事件數／帳戶淨值 | HEADER 下全寬 | 首屏頂（壓縮一行兩格） |
| 2 | P0 | SIGNAL 排名表 | rank order list，按當月增長降冪，6 欄可排序（v1.0 §四.6 不變） | 左欄底 | 第 5 位 |
| 3 | P0 | CCY Power 熱力圖 | 8 貨幣 × 4 TF，數字＋色階＋▲▼▬ 三重編碼 | 左欄頂 | 首屏第 2 位 |
| 4 | P0 | 新聞＋HIGH 倒數 | news_guard HIGH 優先，倒數 client-side 計 | 右欄頂 | 首屏第 1 位 |
| 5 | **P1** | **事件地理層（世界地圖）** | **8 貨幣國簡化 SVG，240px 全寬；L1 靜態環／L2 呼吸（≤3 點）／L3 新事件 pulse×2**；右上 ⏸ | **KPI 下全寬（新）** | **唔放；改事件國家 strip（#12）** |
| 6 | P1 | 走勢 sparkline | **外匯＋商品/指數，6 卡縮至 4 卡**（為地圖找數，裁決批准） | 左欄中 | 第 6 位 |
| 7 | P1 | 系統健康燈 | 5 燈橫排：ranking／NewsGuard／MT5／備份／EA 心跳 | 右欄中 | 第 7 位 |
| 8 | P1 | 上載入口 | 桌面右上按鈕 → drawer（csvZone/setZone/csv2Zone 原封搬入）；手機 FAB | HEADER 內 | FAB 右下 |
| 9 | P1 | 快捷入口 | **icon grid 改單行 chip 橫排**（為地圖找數，裁決批准）；深度連結清單 | 右欄底 | 第 10 位 |
| 10 | **P1** | **NAV BAR（新）** | **獨立 top nav，6 項；裁決見 §二，揀方案 C** | HEADER 下 sticky | 漢堡（漢堡喺 HEADER 內） |
| 11 | P2 | 帳戶總覽 | demo/live/cent 三段 | 底欄 | 第 9 位 |
| 12 | **P1** | **事件國家 strip（新，手機限定）** | 44px 橫向 scroll，≤8 chip，「▲USD 02:00 FOMC」格式；**禁 emoji 國旗**（Windows 渲染成方塊），用 3 字母徽章＋語義色 | 唔出 | 首屏第 3 位（KPI 壓縮行之下、HIGH 倒數之上） |
| 13 | P2 | 最近分析 | 最近 5 個存檔 | 底欄 | 第 8 位 |

> 註：#10 NAV BAR 同 #12 strip 係「導航／呈現元件」；裁決文件口徑「12 模組＋地圖」依然成立，呢度以 13 計係因為 strip 獨立於地圖、有自己驗收項。

### 1.2 桌面 1280px wireframe（標高度預算）

    ┌──────────────────────────────────────────────────────────────┐
    │ HEADER 64px：TSA 標識 · [⬆ 上載]（右上） · [⚙ admin]          │  64
    ├──────────────────────────────────────────────────────────────┤
    │ NAV BAR 48px（sticky）：首頁 排名 新聞 CCY 任務板 工具          │  48
    ├──────────────────────────────────────────────────────────────┤
    │ KPI 頂欄 120px（4 等寬大卡）                                    │ 120
    ├──────────────────────────────────────────────────────────────┤
    │ 世界地圖 240px（全寬 1280）· 右上 [⏸ 動效]（熱區 44×44）        │ 240
    ├───────────────────────────┬──────────────────────────────────┤
    │ 左欄 780px                │ 右欄 440px                        │
    │ ┌───────────────────────┐ │ ┌──────────────────────────────┐ │
    │ │ CCY 熱力圖 8×4  ~280px│ │ │ 新聞＋HIGH 倒數      ~220px  │ │
    │ ├───────────────────────┤ │ ├──────────────────────────────┤ │
    │ │ 走勢 sparkline ~180px │ │ │ 系統健康燈（5 燈）     ~72px  │ │
    │ │ （4 卡，原 6 卡）      │ │ ├──────────────────────────────┤ │
    │ ├───────────────────────┤ │ │ 快捷入口（單行 chip）  ~56px  │ │
    │ │ SIGNAL 排名表  ~420px │ │ │ （深度連結，右欄底）          │ │
    │ │ （Top 30，可捲）       │ │ └──────────────────────────────┘ │
    │ └───────────────────────┘ │                                  │
    ├──────────────────────────────────────────────────────────────┤
    │ 底欄 ~200px：帳戶總覽（demo/live/cent） · 最近分析 5 筆         │ 200
    └──────────────────────────────────────────────────────────────┘

- 桌面總高（完整頁）：64+48+120+240+~880（雙欄區）+200 ≈ **1,552px**
- 桌面首屏（1280×~800 可視）：64+48+120+240 = 472px chrome → 首屏仍見雙欄頂部（熱力圖＋排名表頭），v1.0「排名表喺首屏」驗收維持。

搵數對照（有加必有減，全部照裁決原文）：地圖 +240px；走勢 6→4 卡 −100px；快捷入口 grid→單行 chip −40px。首屏淨增 ~100px，由 NAV sticky 形態吸收，實測首屏餘量仍 >300px 畀雙欄頂部。

### 1.3 手機 390px wireframe（標高度預算）

    ┌──────────────────────┐
    │ HEADER（緊湊）         │  56   TSA 標識＋☰ 漢堡（上載由右下 FAB 負責）
    ├──────────────────────┤
    │ ① HIGH 倒數（首屏1）   │ ~180  老闆日日要知
    │ ② CCY 熱力圖（首屏2）  │ ~300  一眼睇強弱
    │ ～～ 首屏底 ～～        │      56+180+300=536 ≈ iPhone 390×844 可視
    │ ③ 事件國家 strip       │  44   ▲USD 02:00 FOMC｜◆JPY 11:30 BoJ →橫捲
    │                        │      禁 emoji 國旗；3 字母徽章＋語義色
    │ ④ SIGNAL 排名         │ ~420  Top 10，可捲
    │ ⑤ 新聞其餘＋MED        │ ~160
    │ ⑥ 走勢 sparkline（4卡）│ ~180
    │ ⑦ 健康燈（5 燈兩行）    │ ~88
    │ ⑧ 最近分析 5 筆        │ ~180
    │ ⑨ 帳戶總覽三段         │ ~200
    │ ⑩ 快捷入口 chip 單行    │ ~56
    │ [⬆ FAB 56×56 右下]     │      開上載 drawer
    └──────────────────────┘

- 手機總高 ≈ 56+180+300+44+420+160+180+88+180+200+56 ≈ **1,864px**（自然捲動）
- 手機地圖唔出（390px 地圖上 EUR/GBP/CHF 事件點必疊，誤導）；strip 係地圖嘅手機形態。
- 驗收：390/1280 零橫向溢出、strip 零 wrap、長 token overflow-wrap:anywhere。

---

## 二、NAV BAR 裁決（回應老闆 22:28「NAV BAR 在那？」）

v1.0 用 HEADER＋快捷入口 icon grid，冇獨立 nav——老闆問起，即係搵唔到返工位。正式裁決如下。

### 2.1 三方案優劣

**方案 A：維持 HEADER＋快捷入口 icon grid（v1.0 現狀）**
- 優：零開發成本；版面最乾淨。
- 劣：導航隱藏喺右欄底（桌面）／第 10 位（手機），要捲先見到——老闆直接問「NAV BAR 在那」，即係呢個模式已經 fail；跨頁返首頁要靠瀏覽器返轉頭。
- 判：**否決**。導航係「常駐能力」，唔可以收埋喺內容流入面。

**方案 B：加獨立 top nav bar（桌面手機一致）**
- 優：導航常駐可見、跨頁一致。
- 劣：手機 390px 放 6 項 text nav 會縮字／出橫捲；佔手機首屏 ~44px，推走倒數/熱力圖，違反「手機＝睇盤優先」場景。
- 判：方向啱但手機處理錯。

**方案 C：並存——桌面 top nav（sticky）＋手機漢堡（HEADER 內）＋快捷 chip 保留深度連結**
- 優：桌面導航常駐（答到老闆問題）；手機零首屏成本；快捷入口同 nav 分工清晰（見 2.4）；同現有 docs/sidebar.js 嘅「桌面固定導航＋手機漢堡」心智一致，工程改動成本最低。
- 劣：兩套形態要維護；漢堡內項目要同桌面 nav 同源（同一份 config 生成，禁止兩處手寫）。
- 判：**採用**。

### 2.2 最終規格（方案 C）

| 項目 | 規格 |
|---|---|
| 桌面高度 | **48px**，position:sticky; top:0（捲動貼頂；z-index 低於 drawer overlay） |
| 字號 | 14px/500（T2）；當前頁 14px/700 |
| 背景／邊 | bg/L1 #161E2E＋底部 1px hairline #2A3650；文字 txt/secondary，hover 轉 primary |
| 當前頁高亮 | 文字轉 sem/info #5CA8FF＋底部 2px 同色實線；**唔靠色淨辨識**——加 aria-current="page"，色盲下靠字重差異 |
| 手機版 | nav bar 唔出（省 48px 首屏）；HEADER 右側 ☰ 漢堡（觸控熱區 44×44），開全屏 drawer 列同 6 項 |
| 溢出 | <768px 窄窗：橫向 scroll，唔准縮字 |
| 來源 | 桌面 bar 同手機漢堡由**同一份 config**（generator 寫死入 HTML，過 CI link check）輸出 |

### 2.3 Nav 項目清單（6 項，路徑已實測核對存在）

| Nav 項 | 路徑（相對 docs/） | 現狀 |
|---|---|---|
| 首頁 | index.html（新首頁自身） | staticrypt 加密 |
| 排名 | admin/signal_ranking.html | staticrypt 加密 |
| 新聞 | admin/forex_news.html | staticrypt 加密 |
| CCY | admin/ccy_power/index.html | plain（未加密） |
| 任務板 | admin/tasks_board.html | staticrypt 加密 |
| 工具 | tug_of_war_calculator.html | plain |

> 註：原想放「波幅表」（admin/volatility.html）入 nav，但 6 項額滿，佢留喺快捷入口 chip。v1.0 引用嘅 admin/forex_hub/index.html **實測唔存在**（sidebar.js 有舊鏈接但檔案已移除）——nav 唔收佢，快捷入口都要剔除，否則 CI link check 紅。

### 2.4 同「快捷入口」模組嘅重疊解決

- **分工**：nav = 6 個**頂層高頻**入口（老闆日日去）；快捷入口 chip = **深度連結**（period_stats、mfe_mae、db-browser、mt5_mcp_tools、volatility、pivot_table、reviews、portfolios 統一版等低頻工具）。
- **去重鐵律**：出咗 nav 嘅 6 項，快捷入口**唔准重複出**；快捷入口改收低頻深度頁。兩份清單由同一 config 生成，CI link check 覆蓋全部。
- 快捷入口單行 chip 容納 ~8–9 個深度 chip，超出橫向 scroll（桌面手機一致，唔准 wrap）。

### 2.5 staticrypt 加密頁連結處理

實測現狀：首頁及 4/6 個 nav 目標係 staticrypt 加密頁（鹽 2f5a7c9e）。

1. **直接連過去係合法路徑**：nav 點「排名」→ admin/signal_ranking.html 會先見 staticrypt 密碼頁，輸入密碼後見內容。呢個唔係 bug，係加密頁固有行為；nav 唔做任何繞過。
2. **同域解密狀態每頁獨立**：staticrypt 各頁各自解密，但要求工程確認現有 staticrypt 嘅 remember（localStorage 存解密 key）選項有開；有嘅話同瀏覽器 profile 內每頁只輸一次密碼。呢個係現有 admin 頁已經係咁，新首頁照跟，唔新增機制。
3. **首頁自身加密後**：nav 出去＝離開首頁解密上下文；返首頁同樣靠 remember 免重輸。設計上接受「每頁首次到訪輸一次密碼」——安全同方便之間，安全優先（老闆資產數據）。
4. **唔准做**：唔准為順滑將 ranking/accounts 數據頁轉 plain；唔准 iframe 套加密頁偷渡解密；唔准改鹽或密碼流程。
5. **CI link check**：加密頁 HTTP 200（密碼頁都係 200），天然過；驗收加人工點擊 6 個 nav 項逐一截圖密碼頁可達。

---

## 三、特效清單 v1.1（12 項，合併 v1.0 §三＋地圖裁決 §七）

| # | 特效 | 觸發 | 時長／週期 | reduced-motion fallback |
|---|---|---|---|---|
| 1 | 數字 count-up | KPI 卡首次進入 viewport | 300ms | 直接顯示終值 |
| 2 | 卡片微光邊 | hover / focus | 150ms in／100ms out | 常駐 1px hairline |
| 3 | 卡片 hover 升起 | hover | 150ms，translateY(-1px) | 取消位移，只轉 bg/L2 |
| 4 | drawer 開合 | 上載按鈕／FAB／漢堡 | 200ms slide＋150ms 遮罩 fade | 即時出現/消失 |
| 5 | 倒數 tick | 每分鐘 | 0ms 文字更新 | 同左 |
| 6 | 排名行 hover | hover | 100ms 底色 | 即時轉色 |
| 7 | 熱力圖 cell hover | hover | 100ms | 即時 |
| 8 | 背景紋理 | 常駐 | 靜態 opacity 0.04 | 靜態 |
| 9 | 地圖 L1 靜態環 | 有事件即顯示 | 靜態（填色 @12%＋實線環） | 同左（本來靜態） |
| 10 | 地圖 L2 呼吸光暈 | 常駐；**只限影響最大 3 點** | **4s 週期** ease-in-out（0.25Hz，遠低 WCAG 三閃紅線） | 停，只留 L1 |
| 11 | 地圖 L3 新事件 pulse | generated_at 變更後首次 render | 400ms×2 次，總 1.6s，**播完即停唔 loop** | 直接出靜態環 |
| 12 | 地圖點 → popover/bottom sheet | 點擊 | 150ms fade＋100ms scale(0.98→1) | 即時出現 |

**⏸ 控制（WCAG 2.2.2 硬驗收）**：地圖右上角 ⏸/▶ 開關，24×24 icon、**觸控熱區 ≥44×44**；關閉後 L2/L3 全停、只留 L1（資訊零流失）；狀態存 localStorage 跨頁保留；prefers-reduced-motion: reduce 自動等同關閉。
**Loop 豁免令（全站唯一）**：#10 呼吸係唯一 loop 動畫，豁免條件四項缺一即退靜態：(a) ≤0.25Hz；(b) 有 ⏸；(c) reduced-motion 自停；(d) 同時呼吸點 ≤3。
**維持禁止**：粒子、視差、自動輪播、翻牌、彈跳、其他任何 loop。動畫只用 opacity/transform；光暈用預渲染 radial-gradient 圖層做 opacity 過場，唔准動 box-shadow／blur()。

---

## 四、map_events.json 數據契約（沿用 v1.0 §六格式）

| 模組 | 檔案 | 欄位（名:型別） | 更新 |
|---|---|---|---|
| 事件地理層（桌面地圖＋手機 strip 共用） | home/map_events.json | currency: string(3)；country: string(2, ISO3166-1 alpha-2，EU 用 pseudo-code)；impact: enum[HIGH,MED]；event: string；time_hkt: string(ISO8601)；source: enum[forexfactory,tradingview]；event_count_24h: int；max_impact: enum[HIGH,MED,none]；generated_at: string | **每小時** |
| 手機事件 strip | 同上複用 | 前端 filter：未來 24h、HIGH 先＋時間升冪、取前 8 | 同上 |

**鐵律（缺一即退件）**：
1. map_events.json 同 news_high.json **必須由同一支 generator、同一時間點產出**。老闆喺地圖見 USD HIGH 但右欄倒數冇，就會質疑全部數據。
2. country 係前端 mapping 去 SVG path id 嘅唯一鍵；**唔准**用中文國名匹配。
3. 時間一律 HKT ISO8601；倒數 client-side 用 time_hkt 計，唔靠 generator 時點分鐘數。
4. 紅線不變：pre-generated JSON，首頁唔准 client fetch SQLite。

---

## 五、Bundle 預算重算（紅線 300KB，gzip 前）

| 項目 | 估算（gzip 前） | 依據 |
|---|---|---|
| HTML 結構＋13 模組 DOM | ~35KB | 現 index.html 非密文部分實測 ~35KB |
| CSS（深色 tokens＋13 模組＋nav＋strip） | ~25KB | 手寫無 framework |
| JS（互動：drawer/倒數/排序/count-up/⏸/popover） | ~30KB | 唔引 library；sparkline 前端手繪 SVG |
| 地圖 SVG（8 國簡化） | 40KB（gzip ~18–25KB） | 裁決 §⑤，inline 無額外 request |
| **首頁自身 staticrypt 開銷** | **~60KB** | **實測**：現 index.html 總 61.8KB 中密文 26.9KB＋staticrypt 模板/引擎 ~35KB（固定開銷＋密文隨內容增長）；**要求工程改深色密碼頁模板**，否則白屏密碼頁跳深色首頁，觀感割裂 |
| home/*.json 數據（KPI/CCY/news/map/health/accounts/recent） | ~15KB | ccy_power/data.json 實測 <1KB；news_guard.csv 全份 2.4KB |
| ranking.json（Top 30） | ~4.5KB | dde_scores 實測每行 ~129B；**必須 Top 30 cap**（997 行全出 = ~129KB，直接爆煲——v1.0 冇計到嘅最大伏位） |
| NAV bar／strip／popover | 已計入 CSS/JS | — |
| **總計** | **~210KB** | **≤300KB 合格，餘量 ~90KB** |

**最大單項**：staticrypt 開銷（~60KB 模板＋引擎）；**最大可變項**：ranking.json（唔 cap 就爆，Top 30 後排名第 2 嘅風險位係地圖 SVG 40KB，已係裁決底線唔再縮）。
超標縮減順序：① ranking Top 30→Top 15（省 ~2KB）→ ② 檢查 staticrypt 模板精簡空間（引擎 ~20KB 固定，唔郁）→ ③ 地圖 40KB 唔縮（再縮會認唔到國家）。目前估算**唔需要縮**。
驗收：gzip 前總 page weight 實測回報；Lighthouse mobile ≥85、CLS <0.1。

---

## 六、ZCODE 落地清單（可勾選，逐項含驗收）

**Phase 1 — 骨架**
- [ ] 1.1 新首頁取代 docs/index.html，深色 tokens v1.0 全套落地。驗收：1280/390 零橫向溢出；正文對比 ≥4.5:1 抽查。
- [ ] 1.2 HEADER（64px 桌面／56px 手機）＋上載按鈕＋admin 齒輪。驗收：drawer 200ms 開合、csvZone/setZone/csv2Zone 三區原封搬入、上載狀態喺 drawer 內顯示唔跳走。
- [ ] 1.3 NAV BAR（方案 C）：桌面 sticky 48px＋手機漢堡 drawer，6 項照 §2.3 路徑，同一 config 生成兩形態。驗收：當前頁高亮＋aria-current；6 個連結逐一可達（加密頁見密碼頁算達）；staticrypt remember 已確認開啟。
- [ ] 1.4 staticrypt 深色密碼頁模板。驗收：密碼頁截圖無白屏閃跳、配色跟 tokens。

**Phase 2 — 模組**
- [ ] 2.1 KPI 頂欄 4 卡＋count-up 300ms。驗收：home/kpi.json 契約符 §四格式。
- [ ] 2.2 世界地圖 240px 全寬＋L1/L2/L3 三層動效＋⏸ 開關。驗收：SVG ≤40KB inline；⏸ 關閉後全停、資訊零流失、localStorage 記住；reduced-motion 模擬截圖全停；HIGH 三重編碼（色＋▲＋字）齊；灰階截圖仍分 HIGH/MED；同時呼吸點 ≤3。
- [ ] 2.3 popover（桌面）/bottom sheet（手機）：該國未來 24h 事件，HIGH 先；空狀態出「24h 無事件＋composite 分」。驗收：>24h 事件唔出；零 emoji 國旗。
- [ ] 2.4 手機事件 strip 44px。驗收：≤8 chip、橫向 scroll 零 wrap、scroll-snap、390px 零頁面溢出。
- [ ] 2.5 CCY 熱力圖 8×4（數字＋色階＋▲▼▬）。驗收：對齊 badge 帶字（ALIGN n/4）；色盲安全；唔用 tertiary 色做細符號。
- [ ] 2.6 走勢 sparkline **4 卡**（SVG 手繪，前端取 data/*_D1.json 最近 30 bar）。驗收：零 Chart.js；卡數＝4。
- [ ] 2.7 SIGNAL 排名表 6 欄可排序，**Top 30 cap**。驗收：ranking.json ≤5KB；欄頭排序可用；爆倉 ⛔＋danger 標記。
- [ ] 2.8 新聞＋HIGH 倒數（client-side 用 time_hkt 計）。驗收：同地圖數字對得上（抽 3 國對數——同一 generator 鐵律）。
- [ ] 2.9 健康燈／帳戶總覽／最近分析／快捷入口單行 chip。驗收：快捷 chip 同 nav 零重複；深度連結全過 CI link check（剔除實測唔存在嘅 forex_hub 路徑）。

**Phase 3 — 數據＋驗收**
- [ ] 3.1 generators：home/*.json 七份＋map_events.json 與 news_high.json 同一 generator 同一時點。驗收：抽 3 國地圖 vs 倒數數字一致。
- [ ] 3.2 Bundle 實測：總 page weight 回報（估 ~210KB）。驗收：≤300KB；Lighthouse mobile ≥85；CLS <0.1。
- [ ] 3.3 CI link check 全綠（含加密頁 200）。
- [ ] 3.4 1x/2x 實機截圖（桌面 1280＋手機 390，首屏＋全頁）交 Muse 審；另附 reduced-motion 模擬＋灰階測試截圖各一。

—— Muse（設計 agent），2026-10-28。v1.1 為現行設計基準；任何色／版面／特效改動落地前須經我簽核。
