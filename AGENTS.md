# AGENTS.md — TSA（Trade Strategy Analyzer）工程指引

> 本檔係 ZCode / Claude Code / Codex 等 coding agent 嘅**專案入口指引**。
> ZCode 每次開 task 都會讀本檔（workspace 根目錄）。**完整工程標準見 `CLAUDE.md`**，
> 本檔只列最關鍵、最易踩嘅規則，避免 agent 一開始就做錯。

## 這是什麼專案

TSA 分析 AlgoForest 交易信號（Signal），產生馬丁/深度分析報告同排名頁，
輸出到 `docs/` 由 GitHub Pages 發佈。

規模：~631 HTML 頁面、64 個 Signal、11 種 EA 類型、~713 份報告。

```
config.py                 ⚠️ 單一真相來源（EA 映射 EA_MAP、Signal 配置）
martin_autopsy_v3.py      馬丁報告核心
dde_v5_scorer.py          DDE v5 評分引擎
generate_*.py             排名 / 報告生成腳本
docs/                     GitHub Pages 根目錄（sidebar.js 係全域導航）
  admin/                  排名頁（signal_ranking / ccy_ranking / ccy_power）
  reports/                深度分析報告
  data/                   前端數據
scripts/                  tsa_qa_check.py 等工具
downloads/                CSV + SET 檔
reports/                  馬丁報告 v4
```

## ⛔ 改任何嘢之前（強制）

1. `grep -r "符號名" docs/ scripts/ *.py` — 搵出所有引用點，列出受影響檔案清單。
2. 涉及導航／新頁面 → 必須同步 `docs/sidebar.js`。
3. 涉及 EA 映射／Signal ID → 必須更新 `config.py` 嘅 `EA_MAP`。
4. 涉及 Signal 列表／EA 類型 → 檢查 `signal_ranking.html`、`ccy_ranking.html`。
5. **先列清單 + 風險，等老闆確認範圍，然後才動手。**

## ❌ 禁止

- 改已公開嘅 URL 路徑（Pages 已索引）
- 移除任何現有報告連結（`reports/*.html`、`docs/reports/*.html`）
- 未跑 QA 就 commit / push
- 改 `sidebar.js` 嘅 depth 計算邏輯（`/admin/ccy_power/` → `../../`）
- 只改一個排名頁而唔改其他
- 引入新 CSS framework
- HTML 用 absolute path（一律 relative）

## ✅ 必須

- 改完跑 `python3 scripts/tsa_qa_check.py`
- 新頁面要加入 `docs/sidebar.js` 導航
- 新 Signal 要更新 `config.py` 的 `EA_MAP`
- 新報告要在對應 ranking page 加連結
- Commit message：`emoji 描述`（📊 數據 / 🔧 修復 / ✨ 新功能 / 📝 文檔）

## 🧪 驗證指令

```bash
python3 scripts/tsa_qa_check.py            # 快速
python3 scripts/tsa_qa_check.py --full     # 完整
bash /home/alvin/.openclaw/workspace/scripts/tsa_pre_push_qa.sh   # pre-push gate，exit 1 = 唔好 push
```

## 📊 常用生成指令

```bash
python3 generate_signal_ranking_v5.py
python3 generate_ranking_ccy_v5.py
python3 batch_index_reports.py
python3 generate_martin_v4.py
python3 generate_martin_autopsy_v3.py "<csv>" --output "reports/martin_v4_<signal_id>.html"
```

## ⚠️ 已知陷阱

| 陷阱 | 預防 |
|---|---|
| 改 sidebar.js 搞壞全站導航 | 改前先在一個子頁面測 depth |
| 新 Signal 冇入 ranking | config.py → ranking → sidebar 三步都要做 |
| HTML 用 absolute path | 一律 relative |
| CSV encoding 錯 | 永遠 `encoding='utf-8'` |
| 報告連結指舊版 | 新報告即刻更新 ranking page |

## 🖥 環境注意

- **WSL 係生產環境**：`/home/alvin/.openclaw/workspace/trade_strategy_analyzer`，有 10 條 cron（含每小時 CCY Power 自動 commit+push）。
- **Windows clone**：`C:\Users\Alvin\projects\trade-strategy-analyzer`，只作開發用。
- 兩邊都會 push 同一個 `main` → **每次開工前先 `git pull --rebase`**，push 前再 pull 一次。
- Python 腳本喺 WSL 跑（Linux venv / python3）；Windows 側 Python 3.14 未必有齊依賴，唔好當成生產環境。
- 對外依賴：GitHub Pages（repo 已轉 private，Pages 目前停站）、AlgoForest API、Google Sheets、MT4 Terminal CSV。

## 檔案紀律

- `AGENTS.md`（本檔）= agent 入口；`CLAUDE.md` = 完整標準；`agents/tsa/AGENTS.md` = OpenClaw TSA agent 專用，唔好混用。
- `AGENTS.md.openclaw-template.bak` = 舊的通用模板備份，可刪。
