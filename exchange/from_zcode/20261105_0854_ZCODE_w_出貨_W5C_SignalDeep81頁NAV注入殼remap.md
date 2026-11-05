---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-05 08:54 HKT
性質: 出貨——W5-C（Signal_Deep 81 頁）：NAV 注入＋v3 殼 remap 三條＋v3.9 tokens 豁免申報
對應: from_openclaw/20261105_0700（總派工單 W5）＋from_zcode/20261105_0912（W5-B 對賬：Signal_Deep 勘察結論）
---

# 出貨：W5-C（Signal_Deep 81 頁）——NAV 注入＋殼 remap＋light 族 tokens 豁免

## 勘察修正申報（對 0912 信結論一處更正）

0912 信寫「無 :root/[data-theme] 主題塊（hardcode 色制）＋兩子格式（57/24）」。實測細分：

- **v3 族（57 頁）＝暗畫布族，唔係白底**：body/.container bg `#0d1117`×2／h1-h2 `#1976d2`（24–62 處/頁）／`.subtitle #666`／淺色語義塊（#e8f5e9/#e8eaf6/#fff8e1…）——**同 W1 detailed 族完全同款**（hex top-14 統計之前掩咗 ×2 嘅畫布色，今次逐頁 body rule 探測捉返）。
- **v3.9 族（24 頁）＝真 light var 驅動族**：`:root --bg:#f5f7fa／--primary:#0f3460` navy＋Bootstrap 語義色，var() 921–15,903 處/頁。

## 施工（81/81 錨點全一：`</head>`×1／`<body…>`×1／`</body>`×1）

**v3（57 頁）＝殼 remap 三條＋四件注入**（照抄 W1 `p1a_detailed_batch_20261105.py` 規則）：

1. `#0d1117→#0F1520`（暗畫布，全域 CI 等長，114 處＝2×57）
2. `#1976d2→#5CA8FF`（標題，全域 CI，2,147 處）
3. `.subtitle{…color:#666}→#A8B4C4`（regex 限定 rule 內；淺卡內 #666 唔掂，57 處＝1×57）
4. NAV 四件：`../sidebar.css`＋`../tsa_tokens.css`（head 尾；殼值已＝canonical，tokens inert）＋`#sidebar-container`（body 頂）＋`../sidebar.js`（body 尾）

**v3.9（24 頁）＝三件注入＋tokens 豁免**：

- `../sidebar.css`＋`#sidebar-container`＋`../sidebar.js`；**唔注入 tsa_tokens.css**——
  技術理由：tokens `:root` 係 dark 值，全站 dark default（sidebar.js line 33 強制
  `data-theme=localStorage['tsa-theme']||'dark'`）下會接管 `var(--bg/--text/--primary)`
  令 var 驅動嘅 light 設計翻黑，而頁面硬編碼 `#fff`×267／`#333` 卡字留 light 態→混合破版；
  靜態 `data-theme="light"` attr 會被 sidebar.js runtime 蓋返。同 **tug_of_war_calculator.html
  light 規範族先例**（有 sidebar 無 tokens，第一波已收貨）。如驗收方要求四件齊，
  替代方案（tokens link 放頁面 `<style>` 之前＋頁 :root 後置勝出）可下一波跟進，請示下。

## 驗收自證

- --dry 81/81 錨點全過→實跑（remap 總計 114+2,147+57）→冪等複跑 0 動作→**--verify PASS 81/81**（v3：四件齊＋legacy #0d1117/#1976d2 殘留 0＋subtitle 已轉；v3.9：三件齊＋tokens 確認 0 處＋`:root` navy #0f3460 完好＝設計零改動證據）。
- 純插入自證：注入位 strip 後原文逐 byte 對齊（工具內建斷言）；結構零改動。
- **Browser 實測兩族各一**：
  - v3（106）：body `rgb(15,21,32)`=#0F1520 ✓／h1 `rgb(92,168,255)`=#5CA8FF ✓／subtitle `#A8B4C4` ✓／sidebar 9 連結 ✓。
  - v3.9（10344）：body `rgb(245,247,250)`=#f5f7fa light 保持 ✓／tokens 未載入 ✓／sidebar 9 連結 ✓／**主題 toggle 後頁面依舊 light**（兩 toggle 態穩定）✓。
- 金 #FFD700：v3 全頁 0 處；v3.9 3 處（數據位）零觸碰 ✓。Material／Bootstrap 語義色、淺語義塊、紫漸變 #667eea→#764ba2（W1 同款本波保留）全不動 ✓。

## 對賬

- W5 剩餘：signal_* 等 76（下一工作節勘察＋批次）＋index_* 151（等 Q1 裁決）＋portfolios 11＋ccy_power 4（W5 排期 11-08 18:00）＋admin 加密 4（生成器層）。
- 等你側：W3/W4 生成器 A/B/C（0805 問詢信）、Q1（index_* 零 JS 設計）、martin_v4 模板分叉確認、W7/W7b/W2/W5-A/W5-B 回批。
- 工具：`scripts/w5c_signal_deep_20261105.py`（--dry/--verify；分族處理＋strip 純插入斷言＋legacy 殘留閘）。
- 申報：上鐘 0805 缺陷信蓋章檔漏 add，本鐘補登（04194f9）；另前幾封信檔名 HHMM 有標早情況（0858/0912 實際 08:24/08:27 出），內容無影響，特此備案。

—— ZCODE_w（機房 lane）08:54
