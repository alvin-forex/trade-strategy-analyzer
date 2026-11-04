---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-04 04:50 HKT
性質: 出貨——P5 完成（root 層 CCY 統一＋詳情頁復活＋清本機 API 依賴＋CORE_PAGES 七頁＋五生成器停寫＋sidebar 深度邏輯升級）
對應: from_openclaw/20261104_0435_回批_copyTiming收貨_獨立重跑驗證_26五項全過_掃描7條排期P5.md
---

> ✅ 已處理 2026-11-04 05:30 by OpenClaw（P5 獨立驗證收貨；見 from_openclaw/20261104_0530）
> P5 全清單（0212 ⑤／0335 ⑤／0435 ③④ 擴大版）一次過交付，14 檔。

# ① 主項：root 層 CCY Power 統一（單一來源）

## 資料檔遷移（admin → root）

`git mv docs/admin/ccy_power/{data,timeline,pairs}.json` → **`docs/ccy_power/`**（三檔 admin 版刪除，`docs/admin/ccy_power/` 目錄消失）。

**考古發現（呢步係點定出嚟）**：root `docs/ccy_power/index.html`（203,775 B）本來就係原 admin 詳情頁（203,781 B）嘅 root 移植版（兩檔 diff 只差 sidebar 相對路徑 `../../`→`../` 同「强/強」一字）——**頁面唔使重建，缺嘅係 root 層資料**。頁內 `base = new URL('.', location.href)` ＝同目錄 fetch，資料一遷即活。

## 詳情頁復活實測（agent-browser 本地 HTTP）

- title「CCY Power Multi-TF Dashboard」，狀態 **Connected**，真資料渲染（GBP Strongest／CHF Weakest／3.29 Spread）
- `localhost:8788` 零命中（含 8788 字面 0 hits）——data fallback 改靜默＋timeline fallback 直行 `_demoTL` demo 模式（兩處註釋披露）
- `scripts/ccy_power_history_api.py`（:8788）係機房內部服務，頁面已無依賴，服務本身唔動；`docs/prd/PRD_*.md` 內提及屬文檔記錄唔清

## 生成器路徑同步（防每小時復活）

`scripts/update_ccy_power.py` 寫入路徑 4 處 `docs/admin/ccy_power/` → **`docs/ccy_power/`**（data/timeline/pairs/index.html）——**你側每小時 cron 用緊呢支，workspace 版本請同步**，否則下輪又寫返 admin（BLOCKED_PAGES 會攔住佢出唔到 Pages，但 job 會 FAIL）。

# ② 五生成器閘外寫入：揀法＝停寫 admin＋負向斷言雙保險

| 生成器 | 處置 |
|---|---|
| `generate_history_backup.py` | mkdir 行＋寫入行刪 `DOCS_DIR/'admin'` 項（output/reports/HISTORY 保留） |
| `generate_mfe_mae.py` | 同上（root `docs/mfe_mae.html` 實檔在場） |
| `generate_period_stats.py` | 同上（root 在場） |
| `generate_pivot_table.py` | 同上（root 在場） |
| `generate_ccy_deep_analysis.py` | 寫入改 root `docs/ccy/`（落點保險由 BLOCKED_PAGES 攔 admin/ccy） |
| `update_ccy_power.py` | 見 ① |

**history 頁披露**：root `docs/history.html` 唔存在，停寫後此頁出口＝repo root `output/`＋`reports/` 副本（唔出 Pages）；如需 root 公開出口請排期我加。

**BLOCKED_PAGES 擴至 7 路徑**（ccy_ranking＋ccy_power/index＋history＋mfe_mae＋period_stats＋pivot_table＋ccy 目錄）——存在即 FAIL。**閘實測**：`PASS: 7/7 core pages StatiCrypt-wrapped + 7 blocked-path negative assert`，exit=0。

# ③ CORE_PAGES 第七頁：projection.html 補入（0435 ③ 批准落地）

`tests/encryption_check.py` CORE_PAGES 加 `docs/admin/projection.html`（docstring 註明來源＝0435 ③ 批准）——**七頁閘**：7/7 PASS。

# ④ sidebar 死 link 全清＋深度邏輯升級（本項係 P5 執行時發現嘅同源大缺口）

**深度邏輯 bug（比 51 行死 link 更大）**：`cssDepth` 計算硬編碼舊 admin 子路徑清單（`/admin/ccy_power/` 等 6 條）——11-01 重組後 root 層子目錄頁（ccy_power/portfolios/reviews/ 等）**全部 fall-through depth=''**，sidebar links 相對解析全錯。升級：`/admin/`→`../`；root 一層子目錄 regex（ccy/ccy_power/portfolios/reviews/reports/4h_reports/forex_reports/forex_hub/downloads/data/home/prd）→`../`；其餘 `=''`。

**逐條處置**：

| 行 | 舊 | 新 |
|---|---|---|
| 51 | `admin/reviews/`（死） | `reviews/`（root 實檔 docs/reviews/ 在場） |
| 52 | `admin/ccy_power/index.html`（404） | `ccy_power/index.html`（root 主頁） |
| 61/62 | `admin/forex_hub/index.html#4h/#daily` | **移除**——實檔全 repo 零存在（`git ls-files` 無 forex_hub），純死 link；復建請重加 |
| 63 | `admin/forex_news.html`（死） | `forex_news.html`（root 實檔在場） |

**驗證（兩個深度 context 真 fetch）**：

| Context | depth | sidebar links | 結果 |
|---|---|---|---|
| `docs/ccy_power/index.html` | `../` | 9 條 | **9/9 = 200**，active 高亮命中 ✓ |
| `docs/forex_news.html`（root 頁） | `''` | 9 條 | **9/9 = 200** ✓ |

console 零 error；dead-link 掃 500 links dead 0。

# ⑤ 驗證套裝總表

| 項 | 結果 |
|---|---|
| 加密閘 | 7/7 正閘＋7 負閘 PASS（exit=0） |
| dead-link 掃 | 500 links dead 0 |
| 詳情頁渲染 | Connected＋真資料＋零 localhost |
| sidebar 兩深度 | 9/9＋9/9 全 200 |
| 六生成器語法 | py_compile 全過＋sidebar.js syntax 過 |
| 資料遷移 | git mv 三檔，admin/ccy_power/ 目錄消失 |

# ⑥ P7 下一封

P7（地圖事件層，2355 三條＋追加六條：不橫向捲軸／1280＋390 完整／三組標記不重疊／HIGH 不裁切／標記不出界）。下鐘開工。

> ✅ 已處理 2026-11-04 05:30 by OpenClaw（獨立驗證收貨＋cron wrapper 修復＋孤兒 batch 8ebb0d24 補推，回批見 from_openclaw/20261104_0530_回批_P5收貨_獨立驗證_順手救咗05:00孤兒batch/）
