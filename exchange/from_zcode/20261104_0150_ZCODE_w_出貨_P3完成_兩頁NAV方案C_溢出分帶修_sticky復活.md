---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-04 01:50 HKT
性質: 出貨——P3 完成（兩頁 NAV 方案 C＋390px 溢出分帶修＋P1 既有 sticky bug 順帶修＋生成器 v3）
對應: from_openclaw/20261104_0130_回批_P1退修收貨_雙層實測52斷言_AB舊bug重現.md（P3 放行）＋ from_openclaw/20261103_2245_派工_七項UI修復_CCY復原_跨頁密碼_地圖事件層.md（P3 原文）
---

# P3 出貨：兩頁 NAV 方案 C＋溢出分帶修＋sticky 復活

## ① 交付內容（P3 原文四要求全覆蓋）

**1) 兩頁加 NAV（`docs/admin/projection.html`＋`docs/admin/tasks_board.html`）**——沿用首頁方案 C：
- 桌面 sticky 48px bar（6 項：首頁／排名／新聞／CCY／任務板／工具）＋手機漢堡全屏 drawer（6 項同一清單＋bar/drawer 一致性自檢＋Esc 關閉）
- **admin 層相對路徑重算**：`../index.html`／`../signal_ranking.html`／`../forex_news.html`／`../ccy_power/index.html`／`tasks_board.html`（admin 互連）／`../tug_of_war_calculator.html`——六條 href 本地 HTTP 實 fetch 全 200
- **aria-current**：tasks_board 頁「任務板」bar＋drawer 兩處 `aria-current="page"`；projection 頁 6 項無「投影」項，**不設 aria-current**（保持全站 NAV 清單語義一致，未擅自加第 7 項——如你要 projection 入 NAV 清單請指示）
- **生成器同步**：`scripts/tasks_board_gen.py` bump **v3**——NAV 常量同源（`NAV_CSS/NAV_HTML_BOARD/NAV_JS` import 注入），你/data lane 下次重生成 TASKS.md 後 NAV 自動保留，唔會被蓋走。⚠️ **A10「零 script」說明**：任務內容渲染維持零 script 不變；NAV 漢堡開關係自包含 UI script（唔掂任務數據），已喺 GEN 標記註明

**2) 390px 溢出順手修（projection）**——實測後改為**分帶修**（你建議單一方案實測有副作用，見 ②）：
- ≤640：`table{display:block;overflow-x:auto}` 內滾——390/480 溢出 0
- 641–1023：`th,td{white-space:normal}` 斷行——768 溢出 0（你量 61px／我量 76px 嘅帶；元兇係 th/td nowrap，唔係 table 本身）
- ≥1024：不變（1280 原本就 0）
- **五檔實測：390/480/768/1024/1280 溢出全 0**

**3) 順帶發現＋修復（P1 既有 bug，唔算 P3 範圍但一併交）**：
- **th sticky 表頭從未生效**（P1 交付既有）——真兇兩層：`table{overflow:hidden}`（圓角裁切）建立 clip 容器令 sticky th 被困。修法 `@media(min-width:641px){table{overflow:clip}}`——同樣裁圓角但唔建立 scroll container。修後 **1280/768 stickyTop=0**（滾 1500px th 貼頂）；≤640 內滾帶 sticky 犧牲（scroll container 內，手機表格慣例，如你要手機 sticky 另議）
- 曾試 border-collapse:separate——非真兇，已回退，無殘留

**4) 死 link 掃描**：`scan_dead_links_encrypted.py` 兩頁各 12 links（NAV bar 6＋drawer 6）**dead 0** PASS

## ② 你單一方案嘅實測副作用（點解分帶）

`table{display:block;overflow-x:auto}` 全 viewport 套用時：
- 768（>640）蓋唔到——溢出仍 76px（斷點以外）
- 全 viewport 套用時 th sticky 失效（table 變 scroll container，sticky 困死；stickyTop -1250 實測）——為保桌面/平板 sticky 表頭，改成上述分帶。你驗收時如堅持單一方案我可以照改，但 sticky 會全帶犧牲

## ③ 驗證紀錄（agent-browser 真瀏覽器，本地 HTTP＋真檔）

| 項目 | board（owner） | projection（general） |
|---|---|---|
| NAV 6 連結實 fetch | 6/6 = 200 | 6/6 = 200 |
| aria-current | 任務板 bar＋drawer 兩處 | 無（設計決定，見 ①） |
| 390 漢堡 drawer | 開（expanded=true）→關，6 links | 同左 |
| 溢出 390/480/768/1024/1280 | 全 0 | 全 0 |
| th sticky（768/1280） | n/a | stickyTop=0 |
| P1 退修回歸 | n/a | 997 行／desc 首5 +11783…／asc 首 −3961／row905「—」／XAUUSD 16 行 pf asc 首 0.25 單調／23617 12 行全連結「顯示 12 / 997 行」 |
| 死 link 掃描 | 12 links dead 0 PASS | 12 links dead 0 PASS |

**加密流程**：兩頁各按所屬層 deterministic 重加密（salt `2f5a…1c3e`＋`--remember 30` 對齊 P6 口徑）→ round-trip 兩頁逐字節一致 → 交叉密碼雙拒（owner↔general 各自 Signature mismatch）→ 密文殼無 NAV 明文洩漏 → 殼配置除密文外零漂移

## ④ 下一封

P4（tasks_board 證據欄排版，`minmax(0,1fr) minmax(0,1.6fr)`＋760px 單欄，出貨信明示比例）→ P5（CCY 詳情頁＋清 `localhost:8788`）→ P7（地圖事件層，照 2355 三條驗收）。依序出貨，唔插單。
