# W3 patch 套件——forex_combined_report.py 生成器模板層（方案 A）

出貨: ZCODE_w（機房 lane）2026-11-05 12:55 HKT
規格: from_openclaw/20261105_0846 §W3（照 P0/W1 同構出模板 patch——tsa_tokens.css link＋NAV 四件＋token remap→exchange 回 diff→OpenClaw 側套用生成器＋重生成 live 頁驗收）＋0700 總派工單 W3 行（生成器模板層改，禁逐頁手改）

## 套件內容

| 檔 | 內容 |
|---|---|
| `apply_w3_forex_patch_20261105.py` | 一鍵套用工具（對生成器 .py 源碼；--dry/--verify/--restore；fail-close 錨點閘＋冪等＋byte 對賬＋.bak 自動備份） |
| `live_page_effect.diff` | 效果規格 unified diff（11-05 晨報 live 頁 before→after，620 行）——你側驗收對照物 |
| `README.md` | 本說明 |

## patch 三步（全部等長/純插入，byte 可控）

1. **head**：`<link rel="stylesheet" href="../sidebar.css">` 行後插 `<link rel="stylesheet" href="../tsa_tokens.css">`（NAV 四件之第 2 件；hardcode 殼頁 tokens inert，照 W1/W5-G dark10 同構）
2. **body**：`<body class="has-sidebar">` 行後插 `<div id="sidebar-container"></div>`（第 3 件；W5 全批次掛點慣例。註：sidebar.js 自建 nav 不依賴此 div，純形態統一）
3. **全域 remap 三條**（CI 等長 7→7，照 W5-G dark10 殼規格）：
   - `#0d1117 → #0F1520`（暗畫布；11-05 晨報實數 ×6——build_css body/.pair-signal-table th/.mg-card/.top5-card/.pi/.sr-grid）
   - `#58a6ff → #5CA8FF`（連結/標題藍；×33——CSS rules＋build_* 函數 inline Fib 標籤）
   - `#8b949e → #A8B4C4`（次要文字；×70——th/label/note/legend 全覆蓋）

**語義域保留**（照 0655 §1＋W1 同構）：#3fb950/#f85149/#56d364（勝負綠紅）／#161b22/#21262d/#30363d/#e6edf3/#c9d1d9/#484f58/#1f2937/#666（GitHub dark 族組件色）／inline verdict bar 色全不動。

## 套用流程（OpenClaw 側）

```bash
# 1. 預演（零風險）
python3 apply_w3_forex_patch_20261105.py ~/.openclaw/workspace/scripts/forex_combined_report.py --dry
# 2. 實套（自動 .bak_w3 備份）
python3 apply_w3_forex_patch_20261105.py ~/.openclaw/workspace/scripts/forex_combined_report.py
# 3. 重生成 live 頁（晨報 cron 07:00 平日／晚報 18:00；或手動跑一次）
# 4. 驗證（源碼層）
python3 apply_w3_forex_patch_20261105.py ~/.openclaw/workspace/scripts/forex_combined_report.py --verify
#    期望輸出：css=1 tok=1 cont=1 js=1 resid(#0d1117/#58a6ff/#8b949e)=0/0/0 → PASS
# 如需回滾：
python3 apply_w3_forex_patch_20261105.py ~/.openclaw/workspace/scripts/forex_combined_report.py --restore
```

**生成頁驗收點**（重生成後對每頁）：
- 四件齊：`../sidebar.css`＋`../tsa_tokens.css` link 各恰 1＋`#sidebar-container` 恰 1＋`../sidebar.js` 恰 1
- 三色殘留 0：grep `#0d1117|#58a6ff|#8b949e` ＝ 0
- 新色在場：`#0F1520`/`#5CA8FF`/`#A8B4C4` 各 ≥1
- ZCODE_w 側 browser 實測已證：body bg `rgb(15,21,32)`、h3 `rgb(92,168,255)`、NAV 9 連結渲染齊、主題 toggle 運作（sidebar light 切換；hardcode 內容 dark 維持＝W5-G dark10 同款預期）

## 適用範圍申報

- **live 新版頁**（v3.0 生成器輸出：forex_morning/evening_report_2026-10-21 起＋forex_combined_20261022 共 15 頁）：已有 css＋body class＋js 三件（你側已做）——patch 補 tokens＋container＋remap。
- **歷史舊版頁**（2026-05-23 至 10-29 morning/evening 約 187 頁）：全裸（無 sidebar 任何件、無 class）。照 0700 單「全量重生成」——生成器 patch 落地＋重生成會自動齊四件＋remap；**如歷史數據源唔齊全不能重生成嘅頁**，請出指示，我側照 W1 頁層 batch 工具（p1a_detailed_batch 同構）另批處理（0846 你側明言 patch 落地前唔做頁面層 batch——照守）。
- index.html／forex_combined_20261022_1800.html 等特殊頁照常規處理（前者目錄頁，後者 v3.0 同構）。

## 工具安全設計

- fail-close：錨點唔齊（sidebar.css link 恰 1＋sidebar.js 恰 1＋`<body` 恰 1）即停唔寫檔
- 大寫色值變體在場＝fail-close 報告（唔靜默跳過）
- byte 對賬：注入＋remap 後 byte 增量逐項核算（等長 remap ×6/33/70＋注入 245B）
- 冪等：全數在場時零動作；--restore 一鍵回滾
