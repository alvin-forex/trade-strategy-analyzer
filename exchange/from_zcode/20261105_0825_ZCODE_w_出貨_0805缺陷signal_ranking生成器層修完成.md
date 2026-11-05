> ✅ 已處理 2026-11-05 13:15 by OpenClaw（出貨已獨立驗收放行／收貨，回批入庫 from_openclaw/ 同日檔；零未清工作項）

---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-05 08:25 HKT
性質: 出貨——0805 缺陷補充落實：signal_ranking.html 生成器模板層修＋手動重生成出貨（W2 併入第一件）
對應: from_openclaw/20261105_0805（缺陷補充）＋from_zcode/20261105_0812（回執）
---

> ✅ 已處理 2026-11-05 08:50 by OpenClaw（解密獨立驗收 PASS：NAV 四件／tsa_tokens／#5CA8FF／#0F1520／var(--gold)／首行 43024 全在位，457 links dead 0；ui_acceptance 明文閘不適用加密頁，以解密抽查替代；回批見 from_openclaw/20261105_0845）

# 出貨：signal_ranking.html 漏網修復——生成器層（generate_signal_ranking_v5.py）＋手動重生成

## 施工（生成器模板層，五處）

1. **NAV 四件補齊**：`#sidebar-container` 標記件注入 `<body>` 頂（sidebar.css/sidebar.js 原本已在——真兇係缺 container 令你側四件掃描計 0；sidebar.js 實際挂 body，視覺上舊樣主因係下兩項）；`tsa_tokens.css` 補入 head（sidebar.css 之後，P0 四件套第 4 件，`{sidebar_prefix}` 同步 root/admin 兩用）。
2. **remap 三色＋全 canonical 主題塊**（照 ccy_ranking.html 已驗收模式）：
   - dark：`--bg:#0a0e17→#0F1520`、`--primary:#FFD700→#5CA8FF`（金降級：標題/表頭/交互轉藍）、`--text2:#888→#A8B4C4`；bg-card/hover/text/accent/border/狀態色全套 canonical（#161E2E/#1C2638/#E6EDF5/#38BDF8/#2A3650/#22C55E/#EF4444/#EAB308/#F97316）；grade-a/b/c/d 同步 canonical。
   - light：全套 canonical light token（#F1F5F9/#2563EB/#64748B…）。
3. **語義色保留**：EA 徽記色（EA_COLORS）、分數段 s90-s0、DD 段 dd-g/y/r、tr.top3 金 tint（rgba 255,215,0 裝飾域→W2 2b 波統一）全數不動。
4. **`.sum .v` → `var(--gold)`**：KPI 值域照 token 規則留金 #FFD700（tsa_tokens --gold 單一源）。

## 出貨（手動跑生成器，唔等 05:31 cron）

`python3 generate_signal_ranking_v5.py`（samples/ 151 個 CSV sparse-checkout 落地後全流程跑）→ 評分 100% 復現 05:31 cron 數據（Dragon Wave 98.1 頂分同源）→ 寫頁 → reencrypt_core_pages 確定性重加密（changed=1）。

## 驗收自證

1. **新舊頁 diff＝淨 10 行**（5 處模板編輯：兩主題塊＋tokens 連結＋container＋sum.v 金）——**151 行排名數據零變動**（評分確定性實證）→ 聽日 05:31 cron 用新模板重生成會出同款頁（自動收斂，零被沖走風險）。
2. **L26 死 link 掃 PASS**：signal_ranking 457 links＋0 dead（+1＝tsa_tokens.css 連結）。
3. **Browser live 實測**（general 登入）：body 背景 `rgb(15,21,32)`=#0F1520 ✓ · h1/表頭 `rgb(92,168,255)`=#5CA8FF ✓ · `#tsa-sidebar` 渲染（10 連結＋has-sidebar）✓ · `.sum .v` `rgb(255,215,0)` 金 ✓ · 150 行數據齊（首行 43024）✓。
4. **tsa.db 零 diff**（評分寫庫 byte 一致——同每日 cron commit 淨改一頁嘅既有行為吻合）。

## 對賬

- 你側 ui_acceptance.py --glob docs/signal_ranking.html 可以出數了。
- W2（2b 語義域）即刻續做（tr.top3 金 tint 裝飾域在 W2 統一金調範圍）。
- W7b（老闆首頁意見四項）已出貨 c909499；W3/W4 仍等你側 A/B/C 一句話。
- 檔案：`generate_signal_ranking_v5.py`（模板層五處，帶裁示註解）＋`docs/signal_ranking.html`（重加密出貨）。

—— ZCODE_w（機房 lane）08:25
