# TSA Engineering Standards

> 本檔案係 TSA（Trade Strategy Analyzer）系統嘅工程標準。
> 所有改動必須遵守以下規範，確保全系統一致性。

## 系統架構概覽

```
trade_strategy_analyzer/
├── config.py                 # ⚠️ 單一真相來源（EA 映射、配置）
├── generate_*.py             # 報告/排名生成腳本
├── martin_autopsy_v3.py      # 馬丁報告核心
├── dde_v5_scorer.py          # DDE v5 評分引擎
│
├── docs/                     # GitHub Pages 根目錄
│   ├── index.html            # 首頁
│   ├── sidebar.js            # ⚠️ 全域導航（所有頁面依賴）
│   ├── sidebar.css           # 全域樣式
│   ├── admin/                # 排名頁 + 管理頁
│   │   ├── signal_ranking.html
│   │   ├── ccy_ranking.html
│   │   ├── ccy_power/        # CCY Power Dashboard
│   │   └── forex_reports/
│   ├── reports/              # 深度分析報告
│   └── data/                 # 前端數據
│
├── scripts/                  # 工具腳本
│   ├── tsa_qa_check.py       # QA 質量檢查
│   ├── algoforest_*.py       # AlgoForest API 整合
│   └── update_ccy_power.py   # CCY Power 更新
│
├── downloads/                # CSV + SET 檔案
├── market_data/              # 各貨幣對歷史數據
├── reports/                  # 馬丁報告（v4）
└── agents/tsa/               # TSA Agent 配置
```

**規模**：~631 個 HTML 頁面、64 個 Signal、11 種 EA 類型、~713 個報告

---

## ⛔ 改動前必做（強制執行）

### 1. 全局影響分析
每次改動前，必須先完成以下清單：

- [ ] **搜索所有引用**：用 `grep -r "function_name\|class_name\|variable" docs/ scripts/ *.py` 搵出所有受影響嘅檔案
- [ ] **sidebar.js 影響評估**：如果改動涉及導航、頁面路徑、新頁面 → 必須同步更新 `docs/sidebar.js`
- [ ] **config.py 影響評估**：如果改動涉及 EA 映射、Signal ID → 必須更新 `config.py`（單一真相來源）
- [ ] **排名頁影響評估**：如果改動涉及 Signal 列表、EA 類型 → 檢查 `signal_ranking.html`、`ccy_ranking.html` 是否需要更新
- [ ] **列出具體受影響檔案清單**，俾老闆確認範圍後先動手

### 2. 禁止行為
- ❌ **禁止**改動已公開嘅 URL 路徑（GitHub Pages 已索引）
- ❌ **禁止**移除已有嘅報告連結（`reports/*.html`、`docs/reports/*.html`）
- ❌ **禁止**未跑 QA 就 commit/push
- ❌ **禁止**修改 `sidebar.js` 嘅 depth 計算邏輯（影響所有子頁面）
- ❌ **禁止**單獨修改一個排名頁而不更新其他排名頁
- ❌ **禁止**引入新嘅 CSS framework（保持現有樣式系統）
- ❌ **禁止**喺 HTML 報告入面用 absolute path（必須用 relative path）

### 3. 必須行為
- ✅ 每次改動後跑 `python3 scripts/tsa_qa_check.py`
- ✅ 新增頁面必須加入 `docs/sidebar.js` 嘅導航連結
- ✅ 新增 Signal 必須更新 `config.py` 嘅 `EA_MAP`
- ✅ 新增報告必須喺對應嘅 ranking page 加入連結
- ✅ Git commit message 用 emoji 前綴（📊 數據更新 / 🔧 修復 / ✨ 新功能 / 📝 文檔）

---

## 🔧 標準工作流程

### Phase 1：理解（理解代碼 + 確認範圍）
```
1. 讀取相關嘅 config.py / sidebar.js / ranking pages
2. grep 搜索所有受影響嘅檔案
3. 列出改動清單 + 風險評估
4. 等老闆確認範圍
```

### Phase 2：規劃（制定執行計劃）
```
1. 拆解改動為獨立步驟
2. 每步列出：改邊個檔案、點改、點驗證
3. 識別依賴順序（例如：config.py → ranking pages → sidebar）
```

### Phase 3：實施（分步執行 + 逐步驗證）
```
1. 每改一個檔案，即刻驗證語法（python3 -c "import ..."）
2. 改完一組相關改動後，跑 QA check
3. 如果 QA FAIL → 即刻修復，唔好繼續下一步
```

### Phase 4：驗證（全局檢查）
```
1. 跑完整 QA：python3 scripts/tsa_qa_check.py --full
2. 檢查 sidebar 喺所有頁面存在
3. 檢查所有連結有效
4. 確認無 out-of-scope 改動
```

### Phase 5：發佈
```
1. git add -A && git commit -m "emoji + 描述"
2. git push
3. 確認 GitHub Pages 部署成功
```

---

## 📐 代碼規範

### Python
- 使用 type hints
- 函數必須有 docstring
- 配置統一放 `config.py`，唔好散落喺各處
- CSV 讀取必須有 encoding='utf-8' + error handling
- 外部 API 調用必須有 retry + timeout

### HTML
- 所有頁面必須引入 `sidebar.css` + `sidebar.js`
- 用 relative path（`./`、`../`），唔用 absolute path
- 深色主題：`--bg-primary: #1a1a2e`、`--bg-secondary: #16213e`
- 報告 class 命名：`signal-card`、`report-header`、`data-table`

### JavaScript
- sidebar.js 係全域組件，改動必須極度謹慎
- depth 計算邏輯：`/admin/ccy_power/` → `../../`，`/admin/` → `../`，`/reports/` → `../`
- 新增互動功能必須用 event listener，唔好 inline onclick

### Git
- Commit message 格式：`emoji 描述`（例：`📊 CCY Power 2026-06-19 10:00`）
- 一個 commit 只做一件事
- Push 前必須跑 QA

---

## 🧪 QA 檢查項目

### 快速模式（`--quick`）
- Sidebar 喺所有頁面存在
- Signal 連結有效
- 必要頁面存在（index, signal_ranking, ccy_ranking）

### 完整模式（`--full`）
- 以上全部 +
- EA 類型正確（無 Unknown）
- 數據時效（CSV < 48 小時）
- 新 Signal 是否已加入 ranking
- 報告連結指向正確版本

### Pre-Push Gate
```bash
bash /home/alvin/.openclaw/workspace/scripts/tsa_pre_push_qa.sh
```
Exit code 1 = ❌ 唔好 push，Exit code 0 = ✅ 可以 push

---

## 📊 報告生成規範

### 馬丁報告（Martin Autopsy V3）
```bash
python3 generate_martin_autopsy_v3.py "<csv_path>" \
  --output "reports/martin_v4_<signal_id>.html"
```
- 輸出到 `reports/` 目錄
- 命名格式：`martin_v4_<signal_id>.html`

### 深度分析報告
```bash
python3 scripts/generate_deep_analysis.py <signal_id>
```

### 排名頁更新
```bash
cd /home/alvin/.openclaw/workspace/trade_strategy_analyzer
python3 generate_signal_ranking_v5.py
python3 generate_ranking_ccy_v5.py
python3 batch_index_reports.py
python3 generate_martin_v4.py
```

---

## ⚠️ 常見陷阱

| 陷阱 | 原因 | 預防 |
|---|---|---|
| 改 sidebar.js 全站導航壞 | depth 計算錯 | 改前喺一個子頁面測試 |
| 新增 Signal 冇更新 ranking | 忘記更新 config.py | 新 Signal → config.py → ranking → sidebar |
| HTML 用 absolute path | GitHub Pages 子路徑錯 | 一律用 relative path |
| CSV encoding 錯 | AlgoForest 用特殊編碼 | 永遠 `encoding='utf-8'` |
| 報告連結指向舊版 | 忘記更新 ranking page 連結 | 新報告 → 即刻更新 ranking page |

---

## 🔗 外部依賴

- **GitHub Pages**: `https://alvinpoon.github.io/trade-strategy-analyzer/`
- **AlgoForest API**: Signal 數據來源
- **Google Sheets**: Signal 數據同步
- **MT4 Terminal**: Forex CSV 數據

---

_最後更新：2026-06-19_
_維護者：丁蟹 (TSA Agent)_
