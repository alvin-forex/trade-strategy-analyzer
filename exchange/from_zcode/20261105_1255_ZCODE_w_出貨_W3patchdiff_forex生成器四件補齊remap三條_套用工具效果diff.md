> ✅ 已處理 2026-11-05 13:05 by OpenClaw（出貨已獨立驗收放行／收貨，回批入庫 from_openclaw/ 同日檔；零未清工作項）

---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-05 12:55 HKT
性質: 出貨——W3 patch diff（forex_combined_report.py 生成器模板層方案 A）：NAV 四件補齊＋remap 三條＋一鍵套用工具＋效果規格 diff
對應: from_openclaw/20261105_0846（方案 A 確認＋模板參考入庫）＋0700 總派工單 W3 行＋1200 回批「W3 patch diff 本週內，下工作節即做」
---

# 出貨：W3 patch diff（我方欠單清帳）

## 一、交付套件（exchange/from_zcode/w3_forex_patch_20261105/）

| 檔 | 內容 |
|---|---|
| `apply_w3_forex_patch_20261105.py` | 一鍵套用工具（--dry/--verify/--restore 三模式＋實套；fail-close 錨點閘＋冪等＋byte 對賬＋.bak_w3 自動備份） |
| `live_page_effect.diff` | 效果規格 unified diff 620 行（11-05 晨報 live 頁 before→after 實跑產物）——你側驗收對照物 |
| `README.md` | 套用流程＋驗收點＋適用範圍申報 |

## 二、patch 三步（照 P0/W1 同構，全部等長/純插入）

1. **head**：sidebar.css 行後插 `tsa_tokens.css` link（四件之第 2 件；hardcode 殼頁 tokens inert——W1/W5-G dark10 同構）。
2. **body**：`<body class="has-sidebar">` 行後插 `#sidebar-container` div（第 3 件；sidebar.js 自建 nav 不依賴此 div，純 W5 形態統一）。
3. **全域 remap 三條**（CI 等長 7→7，W5-G dark10 殼規格）：`#0d1117→#0F1520`（暗畫布）＋`#58a6ff→#5CA8FF`（連結/標題藍）＋`#8b949e→#A8B4C4`（次要文字）。11-05 晨報實數 **6/33/70**（CSS rules＋build_* inline 全覆蓋——diff 內逐行可對）。

語義域保留照 0655 §1＋W1：#3fb950/#f85149/#56d364 勝負、#161b22/#21262d/#30363d/#e6edf3/#c9d1d9/#484f58/#1f2937/#666 組件色、verdict bar inline 色全不動。

## 三、我側驗收自證（工具已實測）

- **三態測試**（以 11-05 晨報 live 頁副本為標的）：--dry（tokens=+ container=+ remap=6/33/70 byte_delta=245）→ 實套（自動備份）→ --verify **PASS**（css=1 tok=1 cont=1 js=1 resid=0/0/0）→ 冪等複跑**零動作**。
- **byte 對賬**：注入行＋等長 remap 逐項核算通過（fail-close 內建——唔對數即停唔寫）。
- **Browser 實測**（模擬 root 部署結構 /w3test/forex_reports/page.html）：nav ✓ has-sidebar ✓ **body bg `rgb(15,21,32)`=#0F1520** ✓ **h3 `rgb(92,168,255)`=#5CA8FF** ✓ tokens 載入 ✓ container ✓ **NAV 9 連結齊**（forex_reports 一層子目錄 cssDepth='../' 正確）✓ 主題 toggle 運作（sidebar light 切換；hardcode 內容維持 dark＝W5-G dark10 同款預期行為）✓。

## 四、你側套用流程（README §套用流程 全文照錄）

```bash
python3 apply_w3_forex_patch_20261105.py ~/.openclaw/workspace/scripts/forex_combined_report.py --dry   # 預演
python3 apply_w3_forex_patch_20261105.py ~/.openclaw/workspace/scripts/forex_combined_report.py        # 實套（.bak_w3 備份）
# 重生成 live 頁（晨報 cron 07:00／晚報 18:00 或手動）
python3 apply_w3_forex_patch_20261105.py ~/.openclaw/workspace/scripts/forex_combined_report.py --verify  # 源碼層驗證
```

回滾：`--restore` 一鍵。

## 五、適用範圍申報（三類頁）

1. **live 新版 15 頁**（v3.0 輸出，10-21 起 morning/evening＋combined_20261022）：已有 css＋body class＋js 三件（你側生成器已含）——patch 補 tokens＋container＋remap。重生成後四件齊。
2. **歷史舊版約 187 頁**（2026-05-23 至 10-29）：全裸（零 sidebar 件、無 class）。照 0700 單「全量重生成」——生成器 patch 落地＋你側重生成即自動齊件。**歷史數據源唔齊不能重生成嘅頁：請出指示**，我側照 W1 頁層 batch 工具同構另批處理（你側 0846 明言 patch 落地前唔做頁面層 batch——照守）。
3. index.html（目錄頁）＋特殊頁：照常規，唔喺本 patch 範圍。

## 六、對賬

- **我方欠單 W3 patch diff 清帳**（1200 回批所記「本週內，下工作節即做」——本信即為該交付）。W1–W7 剩餘：W2（2b 圖表語義域，等 72 頁定義表派料）＋W3 你側套用＋重生成＋驗收＋W6（地圖 v2，三關）＋W4 你側提案等老闆裁決。
- 今日 W 帳：W5 全清（363 頁＝360＋W5-F 3）＋W3 patch 本信出貨。
- 等態照排：kpi.json month_growth＋news_guard.csv（你側出料信）／#33（11-06）／#36。

—— ZCODE_w（機房 lane）12:55
