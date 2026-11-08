---
方向: ZCODE_w（機房lane）→ OpenClaw／老闆
日期: 2026-11-08 18:05 HKT
性質: 0740 三項之③ tug_of_war_calculator 標準深頁重造樣板 v1 出貨（樣板先行——老闆過目批咗先推 live）
對應: from_openclaw/20261108_0740 §三、0800 §三、1535 §四；0740 之① ccy 樣板 v1（1550）已等批
---

# tug 重造樣板 v1——61 處手術，dark/light/手機三態達標，等老闆過目

## 一、手術範圍（style 層 61 處；計算邏輯／內容零改動）

| 面 | 手術 |
|---|---|
| token palette | `:root --font-main/--radius/--shadow`＋dark/light 全套 var（forex_news 家族規格逐值同款） |
| NAV | **舊側欄三件退役**（sidebar.css/container/sidebar.js）→ **方案 C 新 NAV 三件**（48px sticky＋drawer＋burger；「工具」aria-current）＋bar/drawer 清單一致性檢查 JS |
| 字體 | body→var(--font-main)；標題→var(--primary)；副題／灰字→var(--text2)；零 Arial |
| 表單 | select/input 邊框→var(--border)、底→var(--bg-card)、focus ring→var(--primary) |
| 語義區 | Margin 區／warn／ok／up/down card／dd-highlight／badges 全 rgba 化（dark 兩態可讀，硬色清零） |
| JS 注入色 | breakdown／tick 標籤／訂單列表 18 處→var(--green)/var(--red)/var(--yellow)/var(--text2) |
| tokens 接管 | `<link href="tsa_tokens.css">` 置 head 尾（forex_news 同位）＋theme JS（tsa-theme localStorage） |
| 標題 | `<title>` 加「 - TSA」標記 |

## 二、驗證（Playwright 活體，1440×900＋390×844）

- **pageerror／console error＝0**；計算按鈕在位（SMOKE btn=true）
- 五截圖隨附：前（線上現狀，舊側欄形態）／後 dark／後 light／頭部特寫 dark／手機 dark（burger 正常）
- 殘留硬色審計：僅語義色（tick 綠紅／thumb 紫／thumb ring #fff）＝家族慣例白名單

## 三、出貨形態

- 樣板正本 `tug_of_war_calculator_重造樣板_v1.html`（45KB）＋ `tug_of_war_重造_v1.patch`（412 行 diff，patch 以 diff 出貨照協議）
- **老闆過目未批前，live 一字唔掂**（0740 §四規矩，同 ccy 樣板）

## 四、通道狀態（重要）

push 仍封（rotate#6 待到，見 1742 回執 §一）——本貨與 1742 回執／1550 ccy 樣板／1645 驗屍報告全部本地 commit＋upload/ 後備層（zcode_backlog_backup_20261108_1805_tug），**key 到貨即五件一齊推**。
