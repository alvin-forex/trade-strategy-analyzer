# 報告模板統一審核（卡 #28——最緊要份）

- 日期：2026-11-19
- 對應：卡 #28＋`TSA_ARCHITECTURE_AUDIT.md`（分族依據）＋`REPORT_SECTION_SPEC.md`（收斂目標）
- 老闆原話對準：「兩個的 REPORT 的 TEMPLATE 完全無統一風格」

## 0. 現況數字 → 目標數字

| # | 指標 | 現況 | 目標 | 重跑命令 |
|---|---|---|---|---|
| 1 | 實際視覺風格套數 | **6 套**（§1） | 2 套（暗色分析套＋存檔套＝凍結唔再投資） | 本文 §1 命令 |
| 2 | `tsa_tokens.css` 覆蓋 | 377/481 | 481/481 中「活頁 324/324」全覆蓋（存檔 157 頁凍結） | `grep -l tsa_tokens.css docs/reports/*.html \| wc -l` |
| 3 | 活頁缺 token | index_ 8＋SDA 57 覆蓋中 0 缺＋martin 0＋reviews 0 → **缺 8** | 0 | `grep -L tsa_tokens.css docs/reports/index_*.html \| wc -l` |
| 4 | sec-* 標準錨點覆蓋（index_） | 147/159 | 159/159 | 見 SECTION_SPEC §0 |
| 5 | inline `<style>` 頁 | 481/481 | 收斂後模板頁僅保留頁面專屬 rules（token 共用部分由 tsa_tokens.css 供給）；存檔頁不動 | `grep -l '<style' docs/reports/*.html \| wc -l` |
| 6 | 存檔族（唔投資） | signal_ 71＋SDA 24 舊頁＋anomaly 1＝96 頁 | 標記 archived，零改動 | `grep -L tsa_tokens.css docs/reports/signal_*.html docs/reports/Signal_Deep_Analysis_*.html docs/reports/anomaly_report.html \| wc -l` |

## 1. 實際有幾多套視覺風格（每套附指紋＋重跑命令）

| # | 風格套 | 覆蓋頁數 | 指紋（抽樣實測） | 重跑命令 |
|---|---|---|---|---|
| S1 | **index_ 現代暗色套**（token 化） | 151 | `tsa_tokens.css`＋暗底＋`-apple-system…`＋`<details class="card">` 摺疊卡＋sec-* 錨點 | `grep -l tsa_tokens.css docs/reports/index_*.html \| wc -l` |
| S2 | **index_ 舊暗色套**（無 token） | 8 | 同構但色值 hardcode（例：`background:#dc3545` 紅標直寫） | `grep -L tsa_tokens.css docs/reports/index_*.html` |
| S3 | **martin_v4 token 套** | 169 | token 100%＋①-⑥ 編號節＋圖表板塊 | `grep -L tsa_tokens.css docs/reports/martin_v*.html \| wc -l`（=0） |
| S4 | **SDA 舊淺色套** | 24 | **淺底 `#fef5f7`**（全站唯一淺色族）＋無 token＋無錨點 | `grep -L tsa_tokens.css docs/reports/Signal_Deep_Analysis_*.html \| wc -l` |
| S5 | **SDA token 化版** | 57 | 淺底但已掛 token | 同上反向 |
| S6 | **signal_ V3 海軍藍套** | 71＋1 | 暗海軍藍 `#0f3460`＋無 token＋無錨點＋V3 字樣標題 | `grep -c 'V3 分析報告' docs/reports/signal_10344.html` |

- 6 套裡 S5/S3 已向 S1 收斂（token 化完成）；真分裂＝S2（8）、S4（24）、S6（72）。
- 色值分裂實錘（重跑）：`grep -o 'background:#[0-9a-f]\{6\}' docs/reports/signal_10344.html | head -3` vs `grep -o 'background: #fef5f7' docs/reports/Signal_Deep_Analysis_10344.html`。

## 2. 差異清單（逐維度）

| 維度 | index_（標準） | martin_v4 | SDA | signal_ V3 | anomaly |
|---|---|---|---|---|---|
| token | 151/159 | 169/169 | 57/81 | 0/71 | 0/1 |
| 節 id | sec-* 147/159 | 無（①-⑥ 文字節） | 無 | 無 | 無 |
| 底色 | 暗色（token var） | 暗色（token var） | **淺色 #fef5f7** | **海軍藍 #0f3460** | var 但無定義源 |
| 標題式樣 | `Signal NNNN`＋emoji h2 | `①-⑥` 編號 h2 | `📋 Executive Summary` 英文 h2 | `🔬 Signal #N V3` | 無 h2 標準 |
| 生成源 | 本機分析鏈（活的） | 本機分析鏈（活的） | 舊鏈停產 | 舊鏈停產 | 一次性 |
| 摺疊卡 | `<details class="card">` | 板塊 div | 平鋪 | 平鋪 | 平鋪 |

## 3. 收斂方案：1 套定 2 套

**裁決建議：1 套 token 系統＋2 佈局範本（唔係 2 套視覺風格）**：

1. **視覺 token＝1 套**：`tsa_tokens.css` 唯一色板／字體／間距。淺色 SDA 同暗色其他族用 token 的 `data-theme` 切換（token 檔本身支援，W5 波次已驗證），唔另立第二色板。
2. **佈局範本＝2 個**：
   - **範本 A「分析報告版」**＝index_ 現行結構（details 摺疊卡＋sec-* 錨點）——index_／SDA／未來新族歸併入此；
   - **範本 B「馬丁深挖版」**＝martin_v4 現行結構（①-⑥ 編號節＋圖表板）——保留編號導航，但節 id 補齊 spec（SEC_SPEC 落地）。
3. **存檔族（signal_ 71＋SDA 舊 24＋anomaly 1＝96 頁）唔收斂**：停產＋重生成 32MB/18.8MB 級成本高＋歷史快照價值。處理＝索引標 archived＋banner 一行，**零頁面改動**（比注入 token 更省更穩——老闆裁決邊套都要重生成先至可以真正統一，唔值得）。

## 4. 遷移路線（每步影響 N 頁＋驗收命令＋成本）

| Phase | 動作 | 影響 N 頁 | 驗收命令 | 成本 | 前置 |
|---|---|---|---|---|---|
| P1 | index_ 8 頁掛 token link（存量補齊） | 8 | `grep -L tsa_tokens.css docs/reports/index_*.html \| wc -l` → 0 | 0.5 工作日（逐頁 diff＋headless） | 老闆批 |
| P2 | index_ 12 頁補 sec-* 錨點（147→159） | 12 | 見 SECTION_SPEC §0 命令 → 159/159 | 0.5 工作日 | 老闆批 |
| P3 | SDA 57 活用頁驗 token＋24 舊頁 archive 標記 | 24 改＋57 驗 | `grep -L tsa_tokens.css docs/reports/Signal_Deep_Analysis_*.html \| wc -l` → 57（舊 24 走 archive） | 0.5 工作日 | 老闆批 |
| P4 | reports 索引頁標 活/存檔 兩區（s1 索引層） | 1 | 索引頁含 `archived` 標記數＝96 | 0.5 工作日 | 老闆批 |
| P5 | martin_v4 生成器補 sec-* id＋SECTION_SPEC 寫入本機分析鏈 | 0 存量（新頁自動合規） | 新頁出後跑 SECTION_SPEC §0 命令 | 本機側 1 工作日 | 老闆批＋另開卡 |
| P6 | scripts/README.md 標 72 一次性腳本退役 | 1 檔 | `grep -c 一次性 scripts/README.md` → 1 | 0.1 工作日 | 老闆批 |

- 總成本：repo 側約 2–2.5 工作日＋本機側 1 工作日；零重生成（96 存檔頁唔掂）。
- 風險控制：P1–P3 逐頁 diff（正文 byte 級零變，只動 head link／錨點）＋headless console 零 error＋tsa_qa_check PASS（同 #27／1115 跟進 1/2 手法）。

## 5. 老闆示範頁對照（`reports/index_10344.html#sec-raw`）

- 實測：`#sec-raw`＝「🗃️ 原始數據」摺疊卡（`<details class="card" id="sec-raw">`，3 小節倉位明細表）——呢個係 S1 標準結構嘅正確形態。
- 同頁族內 12 頁缺呢套錨點（S2 舊版），令老闆「完全無統一風格」觀感成立——統一後所有 index_ 頁 #sec-raw 直達同一節。
