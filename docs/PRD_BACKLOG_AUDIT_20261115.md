# PRD 待辦清單倉庫真實狀態審計（2026-11-15）

**審計範圍**：`PRD.md`（v0.9，2026-06-19）Section 10（待確認/待開發）、Section 14.6（實施路線圖）、Section 15（按日期覆盤，日期 2026-06-21）。
**審計對象**：本倉庫 `C:\Users\alvin\tsa-work` 當前代碼＋git 記錄（唯讀審計，本檔為唯一新增檔案）。
**方法**：git log --since=2026-06-01（5,689 個 commit）＋精確檢索（set_parser / info-card / jinja / sqlite / pickle / correlation / walk-forward / regime / cron / telegram）＋抽讀腳本實現同實際輸出 HTML。
**整體置信等級：高**（全部結論立足一手代碼、實際輸出檔案或 git commit；僅 ③⑧ 各有一個倉外待證點，已標注）。

---

## 0. 結論摘要

8 項中 **4 項 ✅ 已做、3 項 🔶 部分、1 項 ❌ 未做**。PRD Section 10／14.6 嘅狀態標記**已經過時**：① Info Card 同 ② .set 差異其實喺 PRD v0.9 發布（2026-06-19）**之前**就做咗（Info Card ≤2026-05-21、SQLite 2026-06-07）；⑤⑥ 喺 PRD 發布後兩日至兩週內完成（2026-06-21／07-04）。**所有 TSA 功能提交集中喺 ≤2026-07-04**，之後四個月倉庫活動只剩 health.json 自動刷新、exchange 信件、tasks_board、ranking 每日重生成——同派工前提「PRD 待辦＝真實缺口」有實質出入：真正嘅缺口係 ③ SKILL 端到端（倉內半鏈）、④ Jinja2 全面化（得一頁）、⑦ 訊號級 Walk-Forward＋ML、⑧ 覆盤自動化。

| # | 項目 | PRD 標記 | 倉庫實況 | 派工建議 |
|---|------|----------|----------|----------|
| ① | Signal Info Card | 🔜 待開發 | ✅ 已做（57/71 份報告有渲染） | 唔使派工 |
| ② | .set 版本差異比較 | 🔜 待開發 | ✅ 已做（CLI＋Info Card＋API 三層） | 唔使派工 |
| ③ | SKILL 自動化分析流程 | 🔜 待開發 | 🔶 部分（倉內只有 API＋通知檔半鏈） | 派細工核實＋補 |
| ④ | Phase 2 模組化＋Jinja2 | 待定 | 🔶 部分（模組化只覆蓋 archive 管線；Jinja2 得一頁） | 暫緩，先裁方向 |
| ⑤ | SQLite 取代 pickle | 待定 | ✅ 已做（主路徑全 SQLite，pickle 零殘留檔） | 唔使派工（可選清尾） |
| ⑥ | 投資組合相關性分析 | 待定 | ✅ 已做（相關性矩陣＋10 組合報告） | 唔使派工 |
| ⑦ | Phase 3 Walk-Forward／市場狀態偵測 | 待定 | 🔶 部分（regime 已建；WF 只有組合級；ML 全無） | 派工（真缺口） |
| ⑧ | 覆盤每日/每週自動化 | 15.6 明言「未來」 | ❌ 未做（工具在，零排程，輸出停喺 2026-05-31） | 派工（低成本高價值） |

---

## 1. 逐項發現

### ① Signal Info Card（PRD 6.3／Section 10 #1）——✅ 已做

**事實**：功能完整實現並已渲染喺現有 detailed report 頂部（title 下面）。PRD 6.3 三項內容齊全：Signal 基本資料（ID、EA 名＋版本、EA 家族標籤、Martin LV、.set 數量）、.set 版本差異（跨日期、同貨幣對、淨列差異參數）、核心參數摘要（加倉／風控／TP-SL 鍵值）。

**證據**（一手代碼＋實際輸出）：
- `archive/generate_all_levels_from_csv.py:1201` `def build_signal_info_card(signal_id)`；`:1645` 嵌入報告體（位於標題區之後）。
- 實際輸出 `docs/detailed_comparison_all_levels_10437.html`：title 喺第 257 行，`<div class="info-card">` 喺第 264 行——即 PRD 要求嘅「最頂部（title 下面）」。
- 覆蓋率：docs/ 71 份 detailed report 中 **57 份含 info-card**；**14 份冇卡嘅全部對應 `set_files\{signal_id}\` 目錄不存在**（生成器對冇 .set 數據嘅訊號回傳空字串，屬預期行為，唔係漏做）。
- 引入時間：≤2026-05-21（commit `a59c7f12` 2026-05-21「chore: archive 8 obsolete scripts」將生成器連功能一齊移入 archive/）。報告內容生成日期全部係 2026-05-09（頁面內嵌「Generated: 2026-05-09 13:41:31」），之後只被 NAV 注入修改（`a6bd5849` 2026-11-04）。
- PRD 過時實證：`PRD.md:372`（6.3「計劃中」）、`PRD.md:560`（「🔜 待開發」）——功能喺 PRD v0.9 發布（2026-06-19）前已上線。

**注意**：生成器而家位於 `archive/`（已歸檔路徑）。如果要為新訊號重新生成 detailed report，需要行歸檔生成器——維護風險，但唔構成派新工理由。

**建議**：唔使派工。可以只開一張「PRD Section 10 狀態欄更新」文檔工。

---

### ② .set 版本差異比較（Section 10 #2）——✅ 已做

**事實**：三層實現齊備——獨立 CLI、Info Card 內嵌渲染、API 端點。符合「淨列出有差異嘅參數，只比較相同貨幣對」。

**證據**（一手代碼＋實際輸出）：
- `scripts/set_parser.py:82-104` `ParamDiff`／`SetDiff` 資料結構；`:149` `def diff_set_files(old, new)`；`:500-502` CLI 用法（`set_parser.py diff <old.set> <new.set>`）。
- Info Card 內嵌：`archive/generate_all_levels_from_csv.py:1275-1318`——按日期欄列比較**同一貨幣對**嘅 .set，skip `EA_NAME/EA_VERSION/EA_SYMBOL/EA_PERIOD`，只列值有差異嘅參數（上限 15 行＋「還有 N 個差異參數」提示）。
- 實際渲染：**7 份** docs 報告含「📋 .set 版本差異」區塊（`docs/detailed_comparison_all_levels_11984.html`、`_16706.html`、`_17962.html`、`_22278.html`、`_2351.html` 等）。
- API：`scripts/api_server.py:143-144` `GET /api/compare/{signal_id}/{v1}/{v2}`（經 `scripts/history_manager.py` `compare_versions`，比較分析版本）。

**缺口（不影響結論）**：`src/set_parser.py`（深入分析管線 `archive/main.py:14` 引用嗰份）只有 `parse_set`／`categorize_parameters`／`parse_multiple_sets`（`:10`／`:52`／`:167`），**冇** diff——即深入分析報告唔會自帶 .set 差異，要靠 levels 生成器或 CLI。

**建議**：唔使派工。若日後統一管線，順手把 `diff_set_files` 移入 `src/set_parser.py`。

---

### ③ SKILL 自動化分析流程（Section 10 #3：「分析 signal {ID}」→scraper→分析→Telegram）——🔶 部分

**事實**：倉庫內存在**後端半條鏈**（本地 API server＋Telegram 通知檔機制＋全套 scraper 腳本），但**觸發端 SKILL（「分析 signal {ID}」語音／文字指令接線）喺本倉庫零證據**——佢應該住喺 WSL 側 OpenClaw 工作區，倉內查證唔到。

**證據**（一手代碼；等級：代碼為一手，端到端運作為待證）：
- 有：
  - `scripts/api_server.py:39-45` `notify_telegram()`——寫入 `/tmp/trade-analyzer-notify.json`，註解明言「OpenClaw agent picks up via heartbeat/polling」；`:101-110` `POST /api/save` 完成分析後 fire-and-forget 觸發通知（含 Signal ID／EA／WR／PF／盈虧）。
  - `scripts/trade-analyzer-api.service`（systemd 單元，常駐 localhost:8787）；`scripts/api_server.py:11`「Runs on localhost:8787 alongside OpenClaw」。
  - Scraper 全套：`scripts/algoforest_scraper.py`、`scripts/algoforest_downloader.py`、`scripts/batch_csv_downloader.py`、`scripts/batch_set_downloader.py`。
  - `agents/tsa/AGENTS.md`——TSA agent 指引（工作區路徑 `/home/alvin/.openclaw/workspace/trade_strategy_analyzer`）。
- 冇：
  - 全倉**冇 skill 定義檔**（冇 skills/ 目錄；`.openclaw/` 只有 `workspace-state.json`，內容僅 setup 時間戳）。
  - 「分析 signal」四字喺倉內只出現喺 `generate_manual_pptx.py:967/1176/1203`——係**簡報文字**（「跟丁蟹講：分析 signal {ID}」），唔係實現。
  - TSA 代碼零 `sendMessage`／`api.telegram`（呢啲字眼只喺 `exchange/from_zcode/...TD_v163...TG直輸/` 嘅 MT4/MT5 工具，屬另一項目）。

**待證**：WSL 側 `/home/alvin/.openclaw/workspace/trade_strategy_analyzer` 有冇丁蟹 SKILL 定義同 Telegram 接線（查法：上 WLS 列 `.openclaw` skills，或問 TSA agent）。

**建議**：派一張細工——上 WSL 核實 SKILL 端；若存在，把 skill 定義／觸發文檔入倉；若唔存在，呢項先算真正「待開發」。

---

### ④ Phase 2 模組化＋Jinja2 重構（Section 14.6 Phase 2，P1）——🔶 部分

**事實**：兩個半成品。模組化：`src/` 有 15 個模組，但**只有 archive 深入分析管線行緊**；主力排名／評分生成器仍係根目錄單檔大腳本。Jinja2：**全倉只有一個生成器用**（CCY 排名頁）；另一個模板檔零引用。

**證據**（一手代碼）：
- `src/` 15 模組：`statistics.py`、`report_generator.py`、`set_parser.py`、`martin_detector.py`、`market_data.py`、`indicators.py`、`context_enricher.py`、`param_comparison.py`、`csv_parser.py`、`position_builder.py`、`copy_trade_sim.py`、`deep_copy_analysis.py`、`entry_quality.py`、`equity_curve.py`、`compare_reports.py`。
- 但 `git grep "from src."` 只命中 `archive/main.py:14`、`archive/run_analysis.py:22`、`archive/run_analysis_lite.py`、`archive/batch_analyze.py`——**src/ 嘅消費者全部喺 archive/**。
- 根目錄生成器仍單檔：`dde_v5_scorer.py`（~620 行）、`generate_signal_ranking_v5.py`、`generate_ranking_ccy.py`、`generate_martin_v4.py` 等（PRD 7.3 亦如此描述）。
- Jinja2：全倉唯一命中 `generate_ranking_ccy_v5.py:7`（"Uses Jinja2 template"）、`:14`（`import jinja2`）＋`templates/ccy_ranking.html`（Jinja2 語法 `{{ }}`）。`templates/forex_combined_v3_template.html` **零引用**（git grep 全倉無路徑引用）。
- 方向性事實：2026 年 10-11 月嘅新頁面走嘅係「JS 動態渲染」路線而唔係 Jinja2——commit `9c11496c`（signal_ranking.html 連結由 `rank_signal.js` 動態生成）；`.github/workflows/regression.yml` 測 `docs/martin_v4_engine.js`。

**建議**：暫緩派工。先由老闆裁決架構方向（Jinja2 服務器渲染 vs 而家行緊嘅 static JSON＋JS 渲染），再決定係重構定正式放棄呢張 Phase 2 卡。

---

### ⑤ SQLite 取代 pickle（Section 14.6 Phase 2，P1）——✅ 已做

**事實**：核心評分管線主路徑已全 SQLite；倉內零 .pkl 殘留；只剩一處 legacy pickle 旁寫（try/except 包住，失敗即略過）。

**證據**（一手代碼＋檔案系統）：
- `db_manager.py:4-13` docstring 明言「Replaces pickle-based data transfer with SQLite storage」，`DB_PATH = data/tsa.db`，建 `dde_scores` 表（取代 `/tmp/dde_v*_data.pkl`）。
- 使用方（git grep `db_manager`）：`dde_v4_scorer.py`、`dde_v5_scorer.py`、`generate_ranking_ccy.py`、`generate_ranking_ccy_v5.py`、`scripts/prep_ranking_data.py`、`scripts/migrate_to_sqlite.py`。
- `dde_v5_scorer.py:615-618` 主存檔 `from db_manager import save_scores`；`:619-624` 旁寫 `/tmp/dde_v5_data.pkl`（legacy 相容，`except Exception: pass`）。
- `scripts/migrate_to_sqlite.py`（pickle→SQLite 遷移工具）；全倉 **25+ 腳本** `import sqlite3`（含 `scripts/copytrade_v13/` 全套、`scripts/history_manager.py`、`scripts/version_tracker.py`、`scripts/ccy_power_history_api.py`）。
- 檔案系統：全倉 `*.pkl`／`*.pickle` **零檔案**。
- 時間：`db_manager.py` 首見 commit `9c885051`／`d0fb7059`（2026-06-07）。

**建議**：唔使派工。可選一張 5 分鐘細單：刪 `dde_v5_scorer.py:619-624` legacy 旁寫（WSL 路徑，Windows 上永遠靜默失敗，純死碼）。

---

### ⑥ 投資組合相關性分析（Section 14.6 Phase 2，P1）——✅ 已做

**事實**：組合內信號兩兩相關性矩陣（按月度盈利）＋高相關對預警已實現，並有 10 個組合（P1-P10）實際輸出報告。

**證據**（一手代碼＋實際輸出）：
- `scripts/portfolio_v2_analyzer.py:296-352` `def portfolio_correlation(monthly_results)`——計相關性矩陣＋`high_correlation_pairs`；docstring `:6-9` 明列「D → 組合內信號相關性分析」「Output: …組合相關性矩陣、機會評分」。
- 實際輸出：`docs/portfolios/portfolio_master_report_v2.html:21` 頁頭「10 個 Portfolio 橫向比較｜方案 B 月度順序回測 + 方案 D 相關性分析｜Generated: 2026-06-21 20:27 HKT」；另有 `portfolio_P1.html`～`P10.html`＋JSON 全套。
- 配套腳本成體系：`scripts/generate_portfolios.py`、`generate_enhanced_portfolios.py`、`generate_portfolio_reports.py`、`generate_portfolio_v2_reports.py`、`portfolio_builder.py`、`portfolio_generator.py`、`portfolio_unified.py`；另有 `docs/ccy_power/copy_trade_portfolio.html`、`portfolio_recommendation.html`。
- Commits：`965d9982`（2026-06-21 Portfolio V2 DD% fix）、`1281ab15`（2026-07-04 P1-P10 統一版）；`data/portfolio_v2_results.json` 等運行數據 2026-11-14 有刷新（時戳）。

**建議**：唔使派工。要新數據時重跑生成器即可。

---

### ⑦ Phase 3 Walk-Forward／市場狀態偵測（Section 14.6 Phase 3，P2；定義喺 14.5）——🔶 部分

**事實**：三個子項兩個半落地。市場狀態偵測（14.5.2 前半）：**指標層已建並入深度分析維度**。Walk-Forward（14.5.1）：**只有組合級**月度順序回測，訊號級 12 期 train/test 冇。ML 預測（14.5.3）：**完全未做**。

**證據**（一手代碼）：
- 市場狀態偵測 ✅（指標層）：
  - `src/indicators.py:9-10` 輸出清單含 `adx_regime`、`volatility_regime`、`market_phase`；`:153` `def label_adx_regime(df, trending_threshold=25,...)`——正正係 PRD 14.5.2「用 ADX 分 Trending/Ranging」。
  - `src/context_enricher.py:101-111` 波動率分級（HIGH/NORMAL/LOW）；`:114-132` `D1_adx_regime`（含 RANGING 分支）；`:154-158` 輸出「D1 市況」「波動」欄位。
  - 已入管線：`archive/run_analysis.py:176` 分析維度 `['D1_adx_regime', 'D1_trend', 'D1_atr_pct_bucket', 'D1_rsi_bucket']`。
- Walk-Forward 🔶（只有組合級）：
  - `scripts/portfolio_v2_analyzer.py:185`「# 3. 順序保留回測 (Walk-Forward)」＋`:6`「B → 順序保留回測 (Walk-Forward Sequential Simulation)」——月度順序保留，屬**組合層**。
  - PRD 14.5.1 要求嘅「歷史分 12 時期、Period N 訓練 / N+1 測試」**訊號級**流程：全倉檢索（walk-forward／walkforward）無其他命中。
- ML 預測 ❌：全倉零 `sklearn`／`LightGBM`／`xgboost`／`tensorflow` 引用。
- 14.5.2 後半「推薦組合按當前市況加權」：portfolio 生成腳本（`portfolio_*.py`）喺 regime 檢索中零命中——未做（此點置信：中高，基於關鍵詞檢索無命中，未逐行讀全部組合腳本）。

**建議**：派工——呢項係 8 項中真正嘅功能缺口：①訊號級 12 期 Walk-Forward；②ML 訊號品質預測（14.5.3，長期目標）。市場狀態偵測可以收貨（已入深度分析維度），補嘅係「組合按市況加權」。

---

### ⑧ 覆盤每日／每週自動化（PRD 15.6，明言「未來」）——❌ 未做

**事實**：手動工具在、輸出零更新、排程零存在。docs/reviews/ 全部覆盤檔案停喺 2026-05-31 數據，冇 daily 目錄，2026-06-01 後零新檔。

**證據**（實際輸出＋配置）：
- 工具在：`scripts/date_range_review.py`（commit `015285f3` 2026-06-21「feat: Add date range review feature (按日期覆盤）」）——係手動跑嘅腳本。
- 輸出停滯：`docs/reviews/` 只有 `monthly/`（3 組日期：2026-04、2026-04~05、2026-05）＋`weekly/`（5 檔，2026-04-01～05-31）＋`index.html`。**冇 `daily/` 目錄**。頁尾「Generated by TSA | 2026-06-21」（`scripts/w4_reviews_20261105.py` docstring 普查引述：8 頁全靜態、生成器已不存喺重生成風險評估內）。最近一次接觸係 2026-11-05 W4 NAV 注入（`scripts/w4_reviews_20261105.py`），**唔係重新生成數據**。
- 無排程：`.github/workflows/regression.yml` 只有 `on: push / pull_request / workflow_dispatch`（無 `schedule`）；倉內 cron 字眼全部屬 ops 腳本（`scripts/backup_dbs.sh`、`scripts/tsa_db_snapshot.sh`、`scripts/watchdog_retry.sh`）。
- 反向印證（cron 機制本身存在、但冇覆盤份）：runtime host 有 cron 行緊——health.json 每 30 分鐘刷新（`a86dc4e3` 等 data commits）、ranking 每日重生成（`123ce7b1`「data: ranking 每日重生成」；`9c11496c` 提 05:30 cron）——**加覆盤 cron 嘅基建已經喺度**。
- PRD 15.6 亦列明「每日 00:05 昨日覆盤／每週一 00:10 上週覆盤／保留策略（日報 30 日、週報 12 週、月報 12 個月）」——保留策略同樣零實現。

**待證**：runtime host（WSL/VPS）實際 crontab 內容（倉內查唔到；查法：WSL `crontab -l`）。但即使有，五年冇產出（2026-06-01 起零新覆盤檔）都證明自動化冇運行或產出冇落地。

**建議**：派工——低成本高價值：喺現有 cron 機制加兩個 job（日／週）行 `scripts/date_range_review.py`＋產出提交，順手做保留策略。

---

## 2. 時間線（git 實錄）

| 時間 | 事件 | 證據 |
|------|------|------|
| ≤2026-05-09 | 71 份 detailed report 內容生成（含 Info Card） | 頁面內嵌 Generated 時間戳 |
| 2026-05-21 | levels 生成器（含 Info Card）移入 archive/ | `a59c7f12` |
| 2026-06-07 | db_manager（SQLite 取代 pickle）落地 | `9c885051`／`d0fb7059` |
| 2026-06-19 | PRD v0.9 發布（①②仲標「待開發」——已過時） | `PRD.md` 檔頭 |
| 2026-06-21 | 按日期覆盤功能＋Portfolio V2（WF 方案 B＋相關性方案 D）＋API 安全加固 | `015285f3`／`965d9982`／`42d304fa` |
| 2026-07-04 | P1-P10 組合統一版——**最後一個 TSA 功能提交** | `1281ab15`／`a023ae42` |
| 2026-07-05 → 11-15 | 倉庫活動只剩 health.json／exchange／tasks_board／ranking 重生成／NAV-UI 修整 | git log --since=2026-06-01 人工覆核 |

CHANGELOG 最後更新 2026-04-25（任務簡報已查證，本次不重查）——比 PRD 仲舊，文檔面全面滯後於代碼。

## 3. 待證項

1. **③ SKILL 觸發端**：WSL `/home/alvin/.openclaw/workspace/trade_strategy_analyzer` 內有冇丁蟹 SKILL 定義、Telegram 接線係咪運作中。查法：上 WSL 列 skills 目錄／睇 `/tmp/trade-analyzer-notify.json` 有冇被消費紀錄。
2. **⑧ runtime crontab**：實際 cron 表有冇（曾經有）覆盤 job。查法：WSL `crontab -l`；輸出側已可斷定自動化冇交付。
3. **① 新訊號報告重生成路徑**：生成器喺 archive/，若有新訊號 CSV 要出 detailed report，確認重行 `archive/generate_all_levels_from_csv.py` 仲行唔行（本次唯讀審計唔執行，未驗）。

## 4. 建議派工優先序（基於上述實況）

1. **⑧ 覆盤自動化**——工具齊、cron 基建齊，淨係駁線；即刻有日常價值。
2. **⑦ 訊號級 Walk-Forward＋ML 預測**——真正未做嘅分析深度缺口（組合級 WF／regime 標籵可復用）。
3. **③ SKILL 端核實＋補文檔**——細工；核實後先知係「文檔工」定「開發工」。
4. **④ 架構方向裁決**——唔係代碼工，係決策工：Jinja2 定 JS 渲染路線，裁完先至知張卡仲有冇意義。
5. ①②⑤⑥ **收貨歸檔**——更新 PRD Section 10／14.6 狀態欄，防止下次再誤派。
