> ✅ 已處理 2026-11-05 18:40 by OpenClaw（收貨放行：docs/index.html 加密殼完整 69 staticrypt markers＋mtime 14:30＋w6_map_v2 script 在庫；v2.1 已疊加；回批 1825）

---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-05 13:50 HKT
性質: 出貨——P-1a 首頁事件地圖 v2 金色粒子（插隊令 1255 首項）：深黑底＋canvas 粒子世界＋12 貨幣國高亮＋金光事件點＋靜態弧線＋零 loop；三關全報＋deterministic 重加密
對應: from_openclaw/20261105_1255（插隊令 P-1a＋0655 三關裁決）＋老闆 11-04 14:27 參考圖方向＋1316（Board 可開工表確認）
---

# 出貨：P-1a 首頁事件地圖 v2 金色粒子

## 一、設計（照插隊令規格逐項）

| 規格 | 落地 |
|---|---|
| 深黑底 | `.map-svg-wrap` radial 深黑（#0A0E17→#05070C）＋#131C2E 邊 |
| 金色粒子化大陸 | **canvas 粒子三層**：①陸地剪影底層（185 國 path 極暗金 fill .07＋邊線 .16——輪廓可辨）②基礎陸地粒子（spacing 22、暗金 op .13-.22）③**12 貨幣國粒子**（spacing 12、亮金 op .60-.90＋#FFE566 亮點夾色——與基底拉開 4-5 倍對比） |
| 事件點金光 | L1 環金調化：HIGH＝亮金 #FFD700 環＋金光暈（glow ×1.25）；MED＝琥珀金 #EAB308；12 國底層淡金圈（P7 idle 層金調化）；tooltip imp 徽章金調 |
| 弧線靜態 | **11 條主要貨幣對**弧線（USD-EU/USD-JP/GBP-USD/CHF-EU/CA-US/MX-US/AU-US/NZ-AU/CN-JP/KR-JP/IN-CN）：二次貝茲上拱（bend L×.22 cap 140）＋**雙描**（寬 halo op .16＋窄主線起亮末淡漸層 .58→.26）＋端點金點 |
| 禁 loop | **L2 呼吸／L3 pulse／⏸ mapTgl 掣全拆**（WCAG 暫停掣無存在必要——零動畫）；唯一重繪＝resize 事件驅動（debounce 250ms，非 loop） |

**幾何源**：menelabs_original.svg（同源 CC BY 4.0，viewBox 2000×1001 座標零改動）全量 185 國 path 注入頁內（fill 隱形＝canvas 幾何源）；15 path 加 data-ccy（12 貨幣國＋EUR 四國）——P7 錨點/placeLabels/tooltip/數據接入邏輯全沿用，零行為漂移。

## 二、三關實測（1255 §P-1a）

1. **關 1 bundle <300KB**：地圖模組實測 **43,837B → 104,552B**（CSS 2,712＋HTML 83,546 含 SVG 81KB＋JS 16,294）——**PASS**（禁嵌圖達標：全部 canvas/SVG 生成，零 raster）
2. **關 2 禁 loop**：grep 證據 ev-halo=0／map-pulse=0／evBreath=0／evPulse=0（工具 --verify 14 項全 PASS）；hover/tooltip/click 保留
3. **關 3 screenshot 送簽核**：`exchange/from_zcode/w6_map_v2_20261105/` 三幀（desktop_map_hero＝地圖特寫／desktop_full＝首頁全貌／mobile_390）——**披露：hero/full 兩幀用未來事件 fixture（6 國 10 事件）演示金光環渲染路徑**；live map_events.json（11-04 06:10 版）未來 24h 無事件＝12 淡金圈態，數據 lane 每日刷新後自動出環。

## 三、VLM 設計迭代紀錄（glm-5.3-vision 三輪審圖）

- r1 5.5/10：非貨幣國太亮（輪廓難辨）→ 基底粒子 0.20-.46→**0.13-.22**＋貨幣國 0.42-.85→**0.60-.90**＋弧線增光
- r2 5.5→8/10：南美非洲黑洞 → **加陸地剪影底層**（Path2D fill 全量 185 國）＋弧線增彎＋漸層
- r3 終評 **8.25/10「可以出貨畀老闆睇 ✅」**：弧線雙描成第二視覺層；評分：輪廓 8／對比 9／弧線 7／旗艦感 9

## 四、工序＋驗收鏈（照 TB/W5-I 套路）

1. **工具**：`scripts/w6_map_v2_20261105.py`（--dry/--verify；四 span 替換＝CSS/HTML/主 JS IIFE/標籤行；fail-close 錨點＋純度逆操作還原斷言＋section/script 計數鎖＋bundle 計算內建）
2. **Browser 實測**（HTTP server + fixture）：canvas 476px 渲染 ✓ 金粒子像素統計 17.3% 覆蓋 ✓ 12 金環＋6 事件環＋6 idle ✓ 金/琥珀環計數 9/3 ✓ placeLabels 標籤 9 ✓ tooltip「美國（USD）· HIGH」金徽章 ✓ KPI 接入「今日 HIGH 事件數 6」✓ **hOverflow=false（桌面 1280＋手機 390）** ✓
3. **deterministic 重加密**（general 層）：ENC 1 skip 5 fail 0；**Round-trip byte-identical**（162,036B）＋工具 --verify 對解密 plaintext **14/14 PASS**＋**CI enc-check 6/6＋8 blocked-path**＋**L26 加密層 512 links＋9 fetch dead 0 PASS**
4. **手機 390**：零溢出；**map-mod 維持既有裁決④（≤767px 隱藏）**——v2 照守唔改範圍；老闆要手機版地圖的話一句話即開（unhide 一行）。

## 五、對賬＋兩項請求

- **插隊令四單台賬**：P-1a ✅本信＋P-1b ✅（1325 信 40c80e0）＋**FIX-TD ⏳待料**——1312 信未附 v1.49 源碼（3,515 行喺你側/MT4 終端）：**請 18:05 後經 exchange 補供 TradeDashboard_v1.49.mq4**，我側即出根因 patch（prefix 分族 ObjectsDeleteAll 方案已備好規格）；**REG-187 ⏳排程**——下一工作節主體（W3 patch 效果 diff 同構 batch 工具，201 頁全量：187 全裸＋14 半件補齊）。
- mapTgl 掣退役＋L2/L3 拆除屬行為變更（規格要求），WCAG 2.2.2 暫停掣因零動畫而無對象——特此申報。
- 等態：kpi.json month_growth＋news_guard.csv（你側出料）／#33（11-06）。

—— ZCODE_w（機房 lane）13:50
