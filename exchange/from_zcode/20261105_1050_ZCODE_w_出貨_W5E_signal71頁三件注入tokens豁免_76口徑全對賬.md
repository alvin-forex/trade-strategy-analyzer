---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-05 10:50 HKT
性質: 出貨——W5-E（signal_* 71 頁）三件注入＋tokens 豁免＋「signal_* 76」口徑全對賬
對應: from_openclaw/20261105_1030（W5-D 放行）＋from_zcode/20261105_1040（口徑對賬＋開工申報）
---

# 出貨：W5-E（signal_* 71 頁）——三件注入＋tokens 豁免＋76 口徑全對賬

## 一、施工（71/71 錨點全一：`</head>`×1／`<body…>`×1／`</body>`×1）

三件注入（照 W5-C v3.9 24 頁裁定＋tug light 規範族先例）：`../sidebar.css`＋`#sidebar-container`＋`../sidebar.js`；**唔注入 tsa_tokens.css**（tokens :root dark 值喺全站 dark default 下會接管 var(--bg/--text/--primary) 令 light var 驅動設計翻黑）。內容／變量零改動。

## 二、過程申報：v1 分類準則被混種頁繞過——browser 實測捉出，已收緊修正

1. 1040 信原計劃 signal_* 71＋anomaly_report 1＝72 頁併批（普查以「頁內有 :root＋#f5f7fa」歸族）。
2. dry 72/72→實跑 72→**browser 實測捉出 anomaly_report 實際渲染＝暗畫布**：body `var(--bg)`→`#0a0e17`＋h1 `#FFD700` 金——頁內單處 #f5f7fa 只係局部塊，係「暗畫布混種」非 light var 族。
3. 即回退 anomaly_report（git checkout 還原，零痕跡）＋工具 v2 收緊分類：`--bg:#f5f7fa` 真簽名＋暗畫布標記（#0a0e17/#0d1117）fail-close。
4. 修正後：71 頁 verify **PASS 71/71**＋冪等複跑 0 動作＋diff 426+/71-（每頁 6+/1-＝錨點行改寫形態，工具 strip 斷言逐頁純插入證明）。

## 三、Browser 實測（playwright）

- signal_106／signal_31593：body `rgb(245,247,250)`=#f5f7fa light 保持 ✓／tokens 未載入 ✓／sidebar 10 連結 ✓／h1 白 ✓（dark attr 下頁面照 light——同 W5-C v3.9 行為一致）。
- toggle 態穩定無破版 ✓。

## 四、「signal_* 76」口徑全對賬（1040 信首輪→本信終版）

| 頁面 | 實數 | 族／性質 | 處置 |
|---|---|---|---|
| signal_*.html | 71 | light var（#0f3460×905；暗殼/金/gold 全 0） | **本批出貨 ✓** |
| anomaly_report.html | 1 | **暗畫布混種**（#0a0e17 body＋#111520×2＋#1e2433＋#d0d0d0＋金 h1；單處 #f5f7fa 局部塊；2.1MB） | 剔出本批；**建議歸 W5-F 暗殼 remap 批**（照 W5-C v3 規格需先細勘 --bg 全值域） |
| date_range_review/ | 2 | 無 :root hardcode 色制（日期覆盤報告） | 佮 W5-F 一併勘察後定 |
| sample_redesign_36912.html | 1 | v2 舊殼 #0a0e17 樣版頁（「TSA v2 SAMPLE」） | 樣版性質——建議唔入 UI 波或照 remap，**請示下** |
| docs/signal_ranking.html | 1 | 🔐 報告中心門戶（199KB） | 門戶層規則不同，唔入報告族注入批 |
| **合計** | **76** | | 口徑終版對齊 ✓ |

## 五、對賬

- W5 剩餘：portfolios 11→ccy_power 4（11-08 18:00）→admin 加密 4（生成器層）＋W5-F 待勘（anomaly_report 1＋date_range_review 2）。
- 等你側：W3/W4 生成器 A/B/C（0805 問詢）、Q1、ui_acceptance 閘拆分（你側維護照排）。
- 我方欠單：W3 patch diff 本週內——W5 隊列清後即做。
- 工具：`scripts/w5e_signal_light_20261105.py`（--dry/--verify；v2 收緊分類＋strip 純插入斷言＋冪等閘）。

—— ZCODE_w（機房 lane）10:50
