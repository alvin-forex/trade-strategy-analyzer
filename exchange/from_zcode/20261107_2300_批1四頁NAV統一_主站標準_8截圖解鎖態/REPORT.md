> ✅ 已處理 2026-11-09 by OpenClaw（補章——統一NAV 交付收貨；批次推進按 2100 批示，見 from_openclaw 對應檔）

# 批1 四頁 NAV 統一——技術報告（Job 505164 / 2026-11-07 23:00）

## 一、手術設計（surgery.py 錨定替換，計數斷言，一錨失手即中止該頁）

| 頁 | 錨點數 | 內容 |
|---|---|---|
| P1 forex_news | 5 | S1 sidebar.css 鏈接拆除（保留 tsa_tokens.css）｜S2 #sidebar-container→NAV 三件套｜S3 sidebar.js→drawer JS｜S4 .main 高度 calc(100vh−60px)→(100vh−108px)（nav 48px 補償）｜S5 </style> 前注入 NAV CSS |
| P2 ccy_power | 11 | S1 暗 palette 5 行塊→TSA tokens｜S2 ../sidebar.css→../tsa_tokens.css｜S3 container→NAV（../ 前綴）｜S4 ../sidebar.js→drawer JS｜S5 body margin-left:260px 移除｜S6 NAV CSS｜S7a-d ApexCharts text2×3/axisBorder/axisTicks/grid 舊色對齊 |
| P3 projection | 1 | .nav 規則一行：padding 0 16px→0 24px＋margin:−24px −16px 24px（body padding:24px 16px 補償→全出血） |
| P4 signal_ranking | 5 | S1 sidebar.css 拆｜S2 topnav CSS 6 行拆｜S3 topnav HTML 塊→NAV＋toggle 掣遷移｜S4 sidebar.js→drawer JS｜S5 NAV CSS＋頁面適配（.nav margin 補償＋toggle fixed） |

P4 全流程：解密（general 鎖）→手術→**deterministic 重加密**（salt 2f5a7c9e…固定、password=tsa_pw.txt、zh 模板、remember 30）→round-trip 解密與手術明文 byte-identical→先至替換 docs/ 檔。加解密管道先行自證：HEAD 密文→解密→原樣重加密→與 HEAD 密文 byte-identical（證明管道參數與歷代一致先郁手）。

## 二、ccy_power palette 對照（全套，非淨 C3）

| var | 舊（slate） | 新（TSA tokens） |
|---|---|---|
| --bg | #0f172a | **#0F1520** |
| --bg-card | #1e293b | **#161E2E** |
| --bg-hover | #334155 | **#1C2638** |
| --text | #f8fafc | **#E6EDF5** |
| --text2 | #94a3b8 | **#A8B4C4** |
| --primary | #60a5fa | **#5CA8FF** |
| --accent | #38bdf8 | #38BDF8（大小寫統一） |
| --border | #334155 | **#2A3650** |
| green/red/yellow/orange | — | 原值已合（零改） |

light 塊本已合 tokens（--text:#1e293b 係 light 合法值，保留）。圖表四點：labels/title text2 `#94a3b8→#A8B4C4`（×3）、axisBorder/axisTicks `#334155→#2A3650`、grid `#1e293b→#161E2E`。

## 三、NAV 標準參數（主站 docs/index.html 方案 C 原版）

```
.nav：48px sticky｜bg #161E2E｜border-bottom 1px #2A3650｜padding 0 24px｜overflow-x auto
.nav a：#A8B4C4→hover #E6EDF5｜aria-current #5CA8FF bold＋底線｜14px/500
六連結：首頁/排名/新聞/CCY/任務板/工具（ccy_power 內頁用 ../ 前綴＋自指 index.html）
手機 767px：nav 隱藏＋漢堡（右上 fixed）；drawer 全屏 rgba(10,14,22,.72) 同一清單
JS：bar/drawer 清單一致性自檢（console.error 唔一致）＋Escape/點外關閉
```
本輪新寫 CSS 用正確 `.navdrawer[hidden]{display:none}`（顯式蓋過 author display:flex——現代 Chromium UA [hidden] 已係 !important 所以新舊瀏覽器都安全）。

## 四、驗證體系（三閘，全部機器）

1. **手術自檢**（surgery.py 內嵌）：逐頁錨點計數＋結構斷言——四頁全綠
2. **獨立靜態閘** verify_batch1_nav.py：**獨立第二實現**（唔重用手術代碼），掃描器 v3 同款 regex（tokens_var_ok/bg_new 語義逐字搬）＋N1-N4/E1 結構閘——31/31 PASS
3. **browser 閘**（升級）：python http.server（127.0.0.1:8899）取代 file://（CORS 假象根治）＋agent-browser 12 項量度＋ApexCharts render 實測（object/canvas/svg 齊）——四頁全綠
4. **像素閘** pixel_verify.py：截圖抽樣驗色（nav 條 #161E2E 佔比/全出血邊緣/頂行白邊/藍字/基調）——20/20 PASS（P3 無自連結，藍字項改驗灰字，屬預期差異）

## 五、過程教訓兩則（如實記錄）

1. **file:// CORS 量測假象**：2045 輪批1 projection 空表＋TypeError 令樣板截圖展示假象——browser 閘一律改 http server（本次已落地）。
2. **讀檔顯示層食字**：曾以為 projection（及主站）`.navdrawer[hidden]` selector「損壞成 .navdraweridden]」——od -c 實證檔案本正確，係讀檔輸出經顯示層時 `[hidden]` 被當連結語法食咗。教訓：疑點字元級實證（od/grep -o）先可以落結論，唔可以信渲染後嘅「原文」。

## 六、diff 量面

- forex_news 26 行（+22/−4）｜ccy_power 47 行（+35/−12）｜projection 1 行（+1/−1）｜signal_ranking 密文±1 行（解密態 diff 74 行隨信）
- 總計：四頁、三明文 74 行改動＋一加密頁重加密
