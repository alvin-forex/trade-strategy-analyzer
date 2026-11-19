# TSA 架構審核（卡 #28，lane:zcode-platform）

- 日期：2026-11-19
- 死線：2026-11-20 18:00 HKT
- 對應派工：`exchange/from_openclaw/20261118_2155_派工_ZCODE_TSA架構審核＋報告模板統一/README.md`
- 姊妹件：`REPORT_TEMPLATE_UNIFICATION.md`（收斂方案）、`REPORT_SECTION_SPEC.md`（節結構規範）

## 0. 現況數字 → 目標數字

| # | 指標 | 現況 | 目標 | 重跑命令 |
|---|---|---|---|---|
| 1 | `docs/reports/` HTML 總數 | 483 | 483（零刪頁） | `git ls-tree -r --name-only origin/main \| grep -c '^docs/reports/.*\.html$'` |
| 2 | 活的報告族（有新增產物） | 3 族（index_／martin_v4_／date_range_review） | 3 族全數合規 REPORT_SECTION_SPEC | 本文 §2 判準命令 |
| 3 | 存檔報告族（停產） | 3 族（signal_／Signal_Deep_Analysis_ 舊 24 頁／anomaly_report） | 標記 archived，零重生成 | 本文 §2 判準命令 |
| 4 | 引用 tsa_tokens.css | 377/481 | 481/481（存檔族除外） | `grep -l tsa_tokens.css docs/reports/*.html \| wc -l` |
| 5 | scripts/ py 檔 | 84 | 清單分級收錄（活 12／一次性 72） | `ls scripts/*.py \| wc -l` |
| 6 | `tsa_qa_check.py` | PASS | PASS | `python scripts/tsa_qa_check.py` |

## 1. 目錄職責（docs/ 一級）

| 目錄 | 檔數 | 職責 | 活性 | 重跑命令 |
|---|---|---|---|---|
| `docs/reports/` | 483+2 子目錄 | Signal 分析／馬丁／覆盤報告主體 | 混合（§2 分族） | `ls docs/reports \| wc -l` |
| `docs/forex_reports/` | 218 | 外匯數據日報快照 | 存檔型日報 | `ls docs/forex_reports \| wc -l` |
| `docs/downloads/` | 201 | Signal CSV 原始下載 | 活的（鏈輸入） | `ls docs/downloads \| wc -l` |
| `docs/data/` | 40 | 排名／健康 JSON（`.enc` 加密） | 活的（鏈輸出） | `ls docs/data \| wc -l` |
| `docs/ccy/` | 36 | CCY 貨幣強弱頁 | 活的 | `ls docs/ccy \| wc -l` |
| `docs/portfolios/` | 21 | Portfolio 統一版 v2 | 活的 | `ls docs/portfolios \| wc -l` |
| `docs/ccy_power/` | 7 | CCY Power 儀表板 | 活的（逐小時鏈） | `ls docs/ccy_power \| wc -l` |
| `docs/admin/` | 14 | 後台（board／加密殼／審核件） | 活的 | `ls docs/admin \| wc -l` |
| `docs/reviews/` | 6 頁＋json | 日期覆盤（daily/weekly/monthly） | 活的（`run_scheduled_reviews.py` 接線） | `find docs/reviews -name '*.html' \| wc -l` |
| `docs/home/` `docs/martingale/` `docs/ea/` `docs/prd/` `docs/indicator/` `docs/campaign/` `docs/js/` | 1–4 each | 專題頁／公共 JS／PRD | 靜態 | `ls docs/home docs/martingale docs/ea docs/prd docs/indicator docs/campaign docs/js` |

- 根層散頁（`docs/*.html`）＝站點功能頁（analyzer／bot2bot／ccy_ranking／tug 等）＋加密殼，由 W5-C 三件套管導航，非本審核範圍。

## 2. 生成器清單：活的 vs 一次性（scripts/ 共 84）

**判準**：CI 引用（`.github/workflows/`）／排程接線（PRD 15.6）／數據鏈近 7 日產物 → 活的；檔名帶日期尾碼＋只出現在歷史 commit → 一次性。每格可重跑。

### 2.1 活的（12）

| 腳本 | 職責 | 活性證據（重跑命令） |
|---|---|---|
| `tsa_qa_check.py` | 全站 QA 閘 | `.github/workflows/regression.yml` 引用：`grep -c tsa_qa_check .github/workflows/regression.yml` |
| `date_range_review.py` | reviews daily/weekly/monthly 生成 | 本輪跟進 1 已修（8fc08b4a） |
| `run_scheduled_reviews.py` | 覆盤排程 wrapper（PRD 15.6 待辦⑧） | commit c4549d96 2026-11-15 |
| `signal_anomaly_detector.py` | anomaly 偵測（一次性輸出 anomaly_report.html） | `grep -l anomaly docs/reports/*.html` |
| `signal_ea_timeline.py` `signal_lot_mapping_upgrade.py` `signal_walk_forward.py` | Signal 分析鏈輔助 | commit 2d4fe532 2026-11-15 |
| `extract_signal_data.py` | CSV→signal 數據抽取 | 數據鏈步驟 1 |
| `generate_health_json.py` | health.json（30min 鏈） | `git log --oneline -1 -- docs/data/health.json` |
| `prep_ranking_data.py` `tasks_board_gen.py` `build_board.py` | 排名 JSON.enc／board CI 生成 | AI_WORK_RULES 第 9 條 |
| `update_ccy_power.py` `ccy_power_history_api.py` | CCY Power 逐小時鏈 | `git log --oneline -1 -- docs/ccy_power/` |

### 2.2 一次性／歷史波次（72）

- 檔名特徵：`w5*_20261105`／`w6_*`／`w8_*`／`p0_*`／`p1a_*`／`g1_g2_*`／`g5_*`／`reg187_*`／`tbnav_*`／`wfinal_*`／`*_fix_20261106` 等——均為 11-04–11-06 導航／配色／修復波次，任務完結即退役。
- 處理建議：唔刪（歷史可追溯），`scripts/README.md` 加一段「一次性腳本＝已退役，唔好重跑」標記（影響 72 檔＋驗收命令：`grep -c 一次性 scripts/README.md`）。需老闆批准另開卡。

### 2.3 報告生成鏈真源

- `index_*.html`＋`martin_v4_*.html` 生成器**唔喺 repo scripts/**——由本機側「TSA 分析鏈」產出（commit 52ba9ed9 作者 `alvincyleungtw2-beep`，2026-11-13：CSV→v5 評分→排名 JSON.enc→報告）；repo 收產物。
- 實證（重跑命令）：`git show --stat 52ba9ed9 | grep -c 'reports/index_'`（=5 新頁）＋`grep -rln "index_.*\.html" scripts/*.py | wc -l`（僅 patch 腳本，無生成器）。
- **架構結論**：報告模板收斂嘅執行點一半喺本機側生成鏈——repo 側只可做「存量頁補齊＋spec 固化」，新頁合規要本機生成器跟 REPORT_SECTION_SPEC（另開卡，老闆批准）。

## 3. 模板清單（6 族，數字核實自 OC＋獨立重跑）

| 族 | 頁數 | token | 節結構 | 風格指紋 | 活性 |
|---|---|---|---|---|---|
| `index_*` | 159 | 151/159 | sec-* 標準錨點 147/159 | 暗色＋`-apple-system` | 活的 |
| `martin_v4_*` | 169 | 169/169 | ①-⑥ 編號節（無 sec-* id） | 暗色＋token 全覆蓋 | 活的 |
| `Signal_Deep_Analysis_*` | 81 | 57/81 | h2 文字節（無 id 錨點） | **淺色** #fef5f7 系 | 停產（11-05 後新 signal 無產） |
| `signal_*`（V3） | 71 | 0/71 | 無 sec-* 錨點 | 暗海軍藍 #0f3460 | 停產 |
| `anomaly_report` | 1 | 0/1 | 無標準節 | `var(--font)` 無 token 引用 | 一次性 |
| `date_range_review/` | 2 | n/a（站點子頁非 reports 族） | 覆盤節結構 | GitHub-dark #0d1117＋固定 sidebar | 活的 |

重跑命令：§0 第 4 行＋`for pat in martin_v index_ Signal_Deep_Analysis_ signal_ anomaly_report; do ls docs/reports/${pat}*.html | wc -l; done`

## 4. 資料鏈（現況）

```
forex-forest CSV（docs/downloads/*.csv）
  → extract_signal_data.py（本機側）→ v5 評分 batch
  → docs/data/signal_ranking.json.enc ＋ ccy_ranking.json.enc（加密排名）
  → index_*.html ＋ martin_v4_*.html（本機側生成鏈，repo 收產物）
  → signal_*／Signal_Deep_Analysis_*（舊鏈，11-05 停產）
  → reviews（run_scheduled_reviews.py）／ccy_power（逐小時）／health.json（30min）
```

- 鏈斷點風險：排名 JSON.enc 由本機側上傳；repo 側 `tsa_qa_check.py` Data Freshness 需 MT4 Files（沙盒常態 SKIP，本機側跑時 PASS）。

## 5. 改善建議（影響頁數＋驗收命令，零空話）

| # | 建議 | 影響 N 頁 | 驗收命令 | 前置 |
|---|---|---|---|---|
| 1 | index_ 8 頁無 token 補 link（存量補齊，唔重生成） | 8 | `grep -L tsa_tokens.css docs/reports/index_*.html | wc -l` → 0 | 老闆批 |
| 2 | index_ 12 頁缺 sec-* 錨點（147→159） | 12 | `for f in docs/reports/index_*.html; do grep -q 'id="sec-raw"' $f || echo $f; done | wc -l` → 0 | 老闆批 |
| 3 | SDA 24 舊頁 token 注入（同 #27 手法） | 24 | `grep -L tsa_tokens.css docs/reports/Signal_Deep_Analysis_*.html | wc -l` → 0 | 老闆批 |
| 4 | signal_* 71 頁＋anomaly 1 頁＝存檔標記（banner＋索引標 archived），唔注入 | 0 頁改動（索引層 1 頁） | 索引頁含 archived 標記計數 | 老闆批 |
| 5 | martin_v4 ①-⑥ 節加 sec-* id（REPORT_SECTION_SPEC 落地） | 169（生成器側）＋0（存量唔動） | spec 文件驗收 | 本機生成鏈另開卡 |
| 6 | scripts/README.md 標記 72 一次性腳本退役 | 1 檔 | `grep -c 一次性 scripts/README.md` → 1 | 老闆批 |

- 陷阱遵從：signal_ 71 頁唔做重生成（內含 32MB／18.8MB 級重頁，重生成本高）；歷史快照唔一刀切（§2 活性判準分族處理）。
- 本審核零 code 改動，全部建議需老闆批准後另開卡執行。
