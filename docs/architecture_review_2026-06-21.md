我已經有足夠資料撰寫報告。以下是 TSA 架構審查報告：

---

# TSA（Trade Strategy Analyzer）架構審查報告

> 審查日期：2026-06-21 ｜ 範圍：`trade_strategy_analyzer` main branch

## 1. 專案概覽

TSA 係一個外匯 EA（Expert Advisor）策略分析系統，從 AlgoForest 抓取交易訊號 CSV，分析後生成 HTML 報告，最終部署到 GitHub Pages 公開瀏覽。

| 指標 | 數值 |
|---|---|
| Git 追蹤檔案 | 4,015 個 |
| HTML 頁面 | 1,134 個 |
| `.git` 體積 | 347 MB |
| `docs/` 體積 | 642 MB（部署根目錄）|
| 頂層 Python 腳本 | 28 個 |
| `scripts/` 工具腳本 | 25 個 |

## 2. 核心架構分層

```
┌─ 數據來源 ─────────────────────────────────────┐
│ AlgoForest (analytics-api.gemsai.com)          │
│  └─ scripts/algoforest_downloader.py           │
│     scripts/batch_set_downloader.py (CDP 抓取) │
├─ 數據層 ────────────────────────────────────────┤
│ downloads/*.csv + *.set  →  market_data/       │
│ SQLite: db_manager.py                           │
│   ├ data/tsa.db (2 MB)                          │
│   ├ data/analysis_history.db (20 MB)            │
│   └ data/ccy_power_history.db (164 KB)          │
├─ 分析引擎 ──────────────────────────────────────┤
│ config.py          ← 單一真相來源 (EA_MAP 等)    │
│ martin_autopsy_v3.py  ← 馬丁報告核心 (CSV→HTML)  │
│ dde_v5_scorer.py      ← DDE v5 評分引擎          │
│ signal_lot_mapping.json ← 多 EA / 多版本手數     │
├─ 報告生成 ──────────────────────────────────────┤
│ generate_martin_autopsy_v3.py / generate_martin_v4.py │
│ generate_signal_ranking_v5.py / generate_ranking_ccy_v5.py │
│ batch_index_reports.py / portfolio_v2_analyzer.py      │
├─ 前端服務 ──────────────────────────────────────┤
│ docs/ (GitHub Pages) ← sidebar.js 全域導航       │
│ scripts/api_server.py (FastAPI, localhost:8787) │
└─ 部署 ──────────────────────────────────────────┘
   scripts/sync_gh_pages.sh  (main → gh-pages)
```

## 3. 數據流（CSV → 分析 → 報告 → 部署）

1. **抓取**：`algoforest_downloader.py` 透過 Chrome DevTools Protocol（CDP）websocket 驅動已登入瀏覽器，呼叫 `analytics-api.gemsai.com/.../export` 下載 CSV / SET 檔到 `downloads/`
2. **攝取**：`martin_autopsy_v3.py:30` 以 `encoding='utf-8-sig'` 讀取 CSV
3. **分析**：套用 `signal_lot_mapping.json` 手數分層 + `dde_v5_scorer.py` 評分
4. **生成**：輸出 HTML 到 `reports/`，再由 `generate_*_ranking_v5.py` 生成排名頁
5. **驗證**：`scripts/tsa_qa_check.py`（sidebar / 連結 / EA 類型檢查）
6. **部署**：`sync_gh_pages.sh` 從 git tree 重建 `docs/`、`reports/`、`output/` 並推送到 `gh-pages` 分支

## 4. 潛在瓶頸

| 瓶頸 | 位置 | 影響 |
|---|---|---|
| **Repo 嚴重膨脹** | 347 MB `.git` + 642 MB `docs/` | clone / push 緩慢，CI 拖慢 |
| **SQLite 提交到 git** | `data/analysis_history.db` (20 MB) 等 8 個 DB | 每次更新等於全 binary blob 進歷史，無法 diff、持續膨脹 |
| **無快取讀檔** | `config.py:231 load_lot_mapping_v2()` 每次呼叫都重新 `json.load` 整個檔案 | `get_lot_layers_for_trade()` 逐筆交易觸發，大 CSV 時為 O(n) 磁碟讀取 |
| **v4/v5 重複模組** | `dde_v4/dde_v5`、`generate_ranking_ccy` / `_v5`、`generate_signal_ranking` / `_v5` | 維護雙份邏輯，易分歧 |
| **臨時檔案入庫** | `tmp_flatten_report.py`、`tmp_generate_index_31823.py`、`tmp_save_report.py`、`tsa_qa_check.py.bak.*` | 雜訊汙染 repo |
| **QA 腳本備份殘留** | `tsa_qa_check.py.bak.20260619_120500` | 應清理 |

## 5. 安全與合規疑慮（⚠️ 重點）

1. **API Server 無認證**（`scripts/api_server.py`）
   - `localhost:8787` 開放，`POST /api/save` 無 token / 無 rate-limit / 無 input schema 驗證
   - 錯誤回應直接回傳 `str(e)`（`api_server.py:78`），**洩漏內部 SQL / 堆疊資訊**

2. **CORS 過寬**（`api_server.py:50`）
   - `allow_origins=["*"]` + `allow_credentials=True` —— 經典不安全組合（註解承認「restrict later」）

3. **JWT Token 暴露風險**（`scripts/batch_set_downloader.py:56`）
   - 透過 CDP `eval` 從 `localStorage` 讀取 `jwtToken`，若被 log / commit 將造成憑證外洩

4. **資料庫含歷史資料入庫**（git）
   - `data/analysis_history.db`、`agents/tsa/openclaw-agent.sqlite` 可能含交易紀錄；binary blob 永留 git history，即使刪除仍可被復原

5. **公開 GitHub Pages 暴露交易分析**
   - 全站報告（含盈虧、倉位、手數）公開可見。若含真實帳戶資料 → **合規風險**（尤其若涉及他人 copy-trade 資料）。需確認資料敏感性與公開意圖

6. **通知機制脆弱**
   - `notify_telegram` 寫 `/tmp` 檔並吞掉所有例外（`api_server.py:42`），失敗無感知

## 6. 建議優先順序

| 優先 | 行動 |
|---|---|
| 🔴 高 | API Server 加入 API key 驗證 + 收窄 CORS + 移除 `str(e)` 回傳 |
| 🔴 高 | 將 `data/*.db` / `agents/*.sqlite` 移出 git → 改 `.gitignore` + 備份機制（或 git-lfs） |
| 🟡 中 | `load_lot_mapping_v2()` 加 `@lru_cache` 或模組級快取 |
| 🟡 中 | 清理 `tmp_*.py`、`.bak` 檔；合併 v4/v5 重複模組 |
| 🟢 低 | 文件化 `sync_gh_pages.sh` 的部署時序與 rollback 流程 |

---

**總評**：架構分層清晰、`config.py` 單一真相來源與 QA gate 做法正確；但 **安全面（無認證 API + 公開 Pages + DB 入庫）** 與 **repo 膨脹** 是最迫切的兩個改善方向。
