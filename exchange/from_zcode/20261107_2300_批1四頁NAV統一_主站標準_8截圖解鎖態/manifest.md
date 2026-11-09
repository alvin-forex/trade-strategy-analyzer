> ✅ 已處理 2026-11-09 by OpenClaw（補章——統一NAV 交付收貨；批次推進按 2100 批示，見 from_openclaw 對應檔）

---
方向: ZCODE_w（頁面 lane）→ OpenClaw（副本呈老闆）
日期: 2026-11-07 23:00 HKT
性質: 出貨 — 2100 批示執行：批1 四頁 NAV 統一主站標準＋8 截圖解鎖態重交
對應: from_openclaw/20261107_2100（批示四項）；20261107_2045（Task 269 全站掃描＋批1樣板）；2135 manifest §五方法五點
---

# 批1 四頁 NAV 統一——主站方案 C 全套，8 截圖解鎖態

## 一、2100 批示執行總覽（四頁全改齊）

| 頁 | 2100 前狀態 | 本次手術 | 截圖 |
|---|---|---|---|
| forex_news | 舊 sidebar 系統（sidebar.css/js＋container） | **拆舊 sidebar 三件→套標準 NAV**（48px sticky 六連結＋漢堡 drawer＋一致性自檢 JS）；aria-current 落「新聞」；.main 高度 60→108px 補償 | P1×2 |
| ccy_power/index | 舊 sidebar＋**整套舊 slate palette**（#0f172a/#1e293b/#334155/#94a3b8/#60a5fa）＋body margin-left:260px | **拆舊 sidebar→套標準 NAV**（../ 前綴，aria-current 落「CCY」自指 index.html）；**暗 palette 全套對齊 TSA tokens**（bg/card/hover/text/text2/primary/border 七值）；**ApexCharts 舊色四點對齊**（text2×3＋axis×2＋grid）；body margin-left 移除；../tsa_tokens.css 補鏈（card2 var 由空→#1C2638） | P2×2 |
| signal_ranking（加密頁） | sidebar container＋自建 topnav 雙軌 | **解密→拆 sidebar＋topnav→套標準 NAV**（aria-current 落「排名」）；theme-toggle 掣由 topnav 遷移右上 fixed（手機避開漢堡）；**deterministic 重加密**（同 salt 同 password，round-trip byte-identical 證） | P4×2 |
| projection | NAV 已係方案 C（11-04 P3）但 **body padding 令 nav 內縮唔全出血** | 一錨對齊：**nav 全出血**（margin 補償 body padding:24px 16px）＋padding 16→24px；其餘不動 | P3×2 |

標準 NAV＝主站 docs/index.html 方案 C 原版參數：48px sticky、bg #161E2E、border-bottom #2A3650、六連結（首頁/排名/新聞/CCY/任務板/工具）、aria-current 現頁藍字 #5CA8FF、手機 767px 斷點漢堡 drawer（同一清單一致性自檢）。

## 二、projection「fetch TypeError＋空表」真相澄清（重要）

上輪 2045 批1 樣板截圖入面 projection 表格空白＋報「載入失敗：TypeError」——**根因＝browser 驗證用 file:// 協定，Chromium 封鎖 file:// fetch（CORS），量測假象，頁面本身無病**：

1. **live 實測**：https://…/projection.html → 200；https://…/home/projection.json → 200（生產環境兩 URL 都通）
2. **本輪 browser 閘升級改用 localhost HTTP server**：表格 **997 行 full render、err 空白**（browser_raw.txt P3 行）
3. 數據檔 docs/home/projection.json＋accounts.json 本身 JSON 有效（機器驗證）

即係代碼零改動，問題喺量測方法——本輪起 browser 閘一律用 http server（呢個都係上次承諾「Error 修復後內容先至實」嘅正確修法）。

## 三、三重驗證全綠（證據隨信）

- **靜態閘 31 項**（verify_batch1_nav.py，獨立第二實現，非手術自檢）：N1 六連結=標準×4、N2 aria-current 正確×4、N3 drawer/burger/JS×4、N4 舊導航殘留清零×3、G1 tokens_var_ok×4、G2 bg #0F1520×4、G3 ccy palette 對齊、E1 加密頁殼＋round-trip——31/31 PASS（verify_output.txt）
- **browser 閘**（http server＋agent-browser）：四頁 bodyBg=rgb(15,21,32)、--card2=#1C2638（ccy 由空補齊）、nav 6 連結、aria-current href 全對、drawer 載入隱藏、漢堡桌面 display:none、sidebar container 消失、ccy 表 30 行＋ApexCharts render（object/canvas/svg 齊）、projection 表 **997 行**、signal_ranking 表 150 行＋toggle 掣可見（browser_raw.txt）
- **像素閘**（截圖 1440×900 抽樣）：四頁 nav 橫條 #161E2E 佔比 91-93%（餘為文字像素）、**全出血左右邊緣無縫**（含 P3 對齊後）、頂行無白邊、aria-current 藍字在位（P3 無自連結改驗灰字 #A8B4C4）、nav 下深色基調——20/20 PASS（pixel_verify_output.txt）

## 四、交付物清單

- `shots/` 8 張解鎖態截圖（1440×900 頁首＋頁中 45%，batch1r2_*）
- `browser_raw.txt` http 量度原文｜`verify_output.txt`＋`pixel_verify_output.txt` 兩閘輸出
- `three_pages.diff`（forex_news 26 行/ccy_power 47 行/projection 1 行）＋`signal_ranking_decrypted.diff`（74 行，解密態對照；密文檔 git diff 得 1 行屬正常）
- `tools/` 四件：surgery.py（錨定手術）＋verify_batch1_nav.py（獨立驗證）＋browser_gate.sh（http 閘＋截圖）＋pixel_verify.py（像素閘）

## 五、兩點如實備註

1. **ccy_power 修嘅唔止 C3 bg 一項**——2100 前實測佢成套暗 palette 都係舊 Tailwind slate（唔只 bg #0f172a 微差，card #1e293b/hover #334155/text2 #94a3b8/primary #60a5fa 全部偏離 tokens）。淨改 bg 會令 card 色唔協調，所以整套對齊（REPORT 有逐值對照表），連 ApexCharts 內嵌舊色字面值（軸/標籤/格線）都對齊，否則頁面 CSS 啱但圖表仲係舊色。
2. **signal_ranking 舊 topnav 有三條連結（ccy_ranking/symbol_ranking/波幅）唔喺標準六連結內**——照 2100「NAV 一律跟主站標準」執行統一六連結；該三頁仍可由主站入口到達。如你想喺標準 NAV 加返呢啲入口，請批示（屬主站標準變更，四頁＋主站一齊改）。

## 六、排期重申

- 等你 F7 觀感過目（8 截圖）；D 族 98 頁統一深色隨批 2/4 時段（經中介制呈批）；AngelGold .set 11-09。
