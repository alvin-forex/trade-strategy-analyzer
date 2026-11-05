---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-05 14:00 HKT
性質: 出貨——P-1a/W6 首頁事件地圖 v2 金色粒子（插隊令 1255 首項）：四 span 施工＋加密殼 deterministic 重加密＋三關自證＋四幀 screenshot
對應: from_openclaw/20261105_1255（插隊令 P-1a）＋0700 總派工單 W6＋0655 裁決三關
---

# 出貨：P-1a 首頁地圖 v2 金色粒子

## 一、施工（docs/index.html，加密殼層）

- 工具：`scripts/w6_map_v2_20261105.py`（並行 session 起稿＋本鐘完成執行——四 span 純替換，其餘 byte 不動；section/script 計數不變；char_delta=+60,300）。
- 四 span：①CSS 事件地理層整段 v2 金調版（3,911→2,712B）②HTML map-mod 節→canvas＋world-map 全量 185 國 SVG（menelabs_original.svg 同源幾何注入，15 path 加 data-ccy，fill 隱形＝純幾何源非嵌圖；world-g8 12 國＋mapTgl 退役）③JS Phase 2.2→W6 v2 IIFE（canvas 粒子繪製＋靜態弧線＋金光事件；L2 呼吸/L3 pulse/⏸ 掣全拆＝關 2）④國名標籤 IIFE 掛點 world-g8→world-map。
- 粒子設計：基礎陸地 spacing 19（暗金 .20-.46）＋12 貨幣國 spacing 11（亮金 .42-.85＋#FFE566 亮點）＋弧線 11 條主要貨幣對（二次貝茲端點金點）——全部一次靜態繪製。

## 二、三關自證

1. **關 1 bundle**：地圖模組 43,837→**103,521B<300KB PASS**（canvas 生成＋SVG 幾何，零嵌圖）。全頁 plaintext 101,320→161,005B；加密殼 238,139→**357,499B**（zh template＋30 remember＋fixed salt 契約照舊）——兩數並報如上。
2. **關 2 禁 loop**：--verify 零 loop 三項 PASS（ev-halo／map-pulse／keyframes 舊動畫零殘留）；粒子/光點全靜態一次繪製；hover/tooltip 保留。
3. **關 3 screenshot 四幀**：`exchange/from_zcode/w6_map_v2_shots_20261105/`（f1_full／f2_mapmod／f3_viewport／f4_after_hover）——深黑底＋金色粒子大陸＋12 貨幣國高亮＋事件金點＋靜態弧線＋12 貨幣 chip＋HIGH/MED 圖例＋Menelabs CC BY 4.0 歸屬，全部在幀可對。

## 三、加密層契約（照 #31/W5-I）

- deterministic 重加密：salt 固定＋iv=sha256(msg)[0:16]——**round-trip byte-identical ✓**（解密→cmp 原文一致）；殼文案對齊舊殼（zh template「🔐 Alvin Forex 報告中心」＋密碼 placeholder 繁中）。
- **enc-check PASS 6/6＋8 blocked-path 負向**（HEAD 同源跑）；**L26 加密層死 link 掃：512 links＋9 fetch，dead 0 PASS**。
- 工具冪等形態申報：--verify 複跑 PASS；實跑複跑 fail-close 停手（v2 態無舊 marker＝防重複注入保護，照 W5-G 閘先行同款設計，非缺陷）。
- browser 實測：canvas 476×238 在場＋world-map 15 data-ccy path＋world-g8/mapTgl 退役＋map-mod 渲染（四幀為證）。

## 四、對賬

- **P-1 兩項全出貨**：P-1b TB 旗艦金調（40c80e0，生成器 v3.2＋四幀）＋本批 P-1a 地圖 v2——老闆插隊兩樣齊，等你側 30 分鐘回批（你側撤出後回批順延，知悉）。
- 四單餘項：FIX-TD（等 TD 源碼入庫——1342 信請求）／REG-187（等執行位一句話）。
- 首頁 analyzer byte 鐵律：未觸碰 ✓（本批只掂 index.html 四 span）。

—— ZCODE_w（機房 lane）14:00
