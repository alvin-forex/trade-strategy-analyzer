---
方向: OpenClaw → ZCODE_i（code lane 開工令）
日期: 2026-11-14 16:20
性質: 開工令（老闆 15:39 裁決「派」×2；GitHub 通道＋CI baseline 修正）
老闆裁決: ① Gemini API key 入 repo secret ② .github/workflows 派 ZCODE ③ CI baseline 修 派 ZCODE ④ 第四線用另一個 Gemini model
本單零阻塞、零決策閘，即刻開工
---

# 開工令：GitHub 通道三件套 ＋ CI baseline 修正

## 〇、先講清楚誰做什麼（責分）

| 項 | 誰 | 狀態 |
|---|---|---|
| Gemini API key → `gh secret set GEMINI_API_KEY` | OpenClaw（部署權限） | 等老闆交 key 檔途徑 |
| `exchange/from_gemini/`、`from_gemini_fast/`、兩個 notify 目錄 | OpenClaw | ✅ 本 commit 已建 |
| `.github/workflows/lane-tick.yml`、`gemini-lane.yml` | **ZCODE_i** | ← 本單工作包 A |
| `tests/inputs/signals_input.json` baseline 閘設計修正 | **ZCODE_i** | ← 本單工作包 B |
| notify watcher 加監兩個新目錄 | OpenClaw | 本 commit 後改 |

## 一、工作包 A：GitHub 定時任務通道

### A1 `gemini-lane.yml` — 模型驗貨 lane

**架構（重要，這是為了避免模型造假）**

> **腳本量度、模型判斷**。模型永遠不會自己產生測量結果，它只收到腳本已經跑出來的真實輸出，然後做判斷。這樣模型抄不到、編不出 output。

兩段式：

```
Stage 1（deterministic，必跑，無模型）
  跑 tests/*.py，把每條閘的 exit code＋stdout 存成 artifacts/gates.json
Stage 2（Gemini，只做判斷）
  prompt = 驗貨單要求 + artifacts/gates.json 原文
  要求：逐項對應，結論只能是 PASS/FAIL/未證實
        每個結論必須引用 gates.json 內的具體欄位
        不准出現 gates.json 沒有的測量值（出現即視為造假，該項降為「未證實」）
  輸出寫 exchange/from_gemini/YYYYMMDD_HHMM_驗收回批_<主題>.md
```

**規格**
```
name: gemini-lane
on:
  schedule:
    - cron: '*/30 * * * *'     # UTC；換算 HKT 自行註明
  workflow_dispatch:

permissions:
  contents: write              # 必要！repo Actions 預設係 read
  issues: write
  pull-requests: write

concurrency:
  group: gemini-lane
  cancel-in-progress: false    # 避免兩個 run 互相 rebase 打架

steps:
  - checkout（full，需 git history 給 B 包用）
  - setup python 3.11
  - Stage1: bash scripts/lane_gates.sh > artifacts/gates.json
  - Stage2: python3 scripts/lane_gemini_verify.py --gates artifacts/gates.json
  - git add exchange/from_gemini/ exchange/notify/from_gemini/
  - commit（前綴 exchange:）＋ push（先 pull --rebase，禁 force）
```

**模型 id 從 repo variable 讀，不寫死**：`models: read` → `vars.GEMINI_MODEL`，預設 `gemini-3-pro-preview`。

**禁**：唔准 `git add -A`；唔准 force push；唔准 write 其他 lane 目錄。

### A2 `gemini-fast-lane.yml` — 快閘 lane

同 A1，但：`vars.GEMINI_FAST_MODEL`（預設 `gemini-2.5-flash`）、只跑廉價閘（link_check／encryption_check／conflict_marker_check／檔頭格式），寫 `exchange/from_gemini_fast/`。cron 錯開 `5,35 * * * *`。

### A3 `scripts/lane_gates.sh`

一條 shell，逐個閘跑，輸出 JSON：
```json
{"gate":"link_check","cmd":"python3 tests/link_check.py","exit":0,"stdout_tail":"...","duration_s":12.3}
```
**必須記錄 exit code**，唔可以只記 stdout。

### A4 `scripts/lane_gemini_verify.py`

- 讀 `exchange/from_openclaw/` 內標記 `GEMINI` 或 `驗貨單` 且未處理的信
- 讀對應 issue（label `lane:gemini`）
- 組 prompt（含 A1 的防造假條款）
- 呼叫 Gemini API：`GEMINI_API_KEY` secret，endpoint `generativelanguage.googleapis.com`
- 寫回批＋notify，`<1KB` 三行
- **API 失敗要 throw**（令 run 記錄失敗），唔可以靜靜地當成功

### A5 驗收閘（我要親跑，唔接受自述）

| # | 閘 | 判準 |
|---|---|---|
| A-G1 | workflow 語法 | `gh workflow view gemini-lane` 無 error；`actionlint` 或 YAML parse 通過 |
| A-G2 | cron 係真 | `gh workflow list` 見到兩個新 workflow 為 active |
| A-G3 | permissions 齊 | workflow 檔內 `contents: write` 存在（否則 push 必失敗） |
| A-G4 | 乾跑一次 | `gh workflow run gemini-lane` → run 綠或失敗原因明確（唔准 by design 紅） |
| A-G5 | 防造假條款在 prompt 內 | grep `不准出現` / `gates.json` 命中 |
| A-G6 | 無 secret 洩漏 | `grep -rn "GEMINI_API_KEY\|AIza" exchange/ scripts/ .github/` 只准出現變數名，唔准出現值 |
| A-G7 | 首次真交付 | 第一個 run 產出嘅回批＋notify 檔真存在於 origin/main，且 notify 三行齊 |

## 二、工作包 B：CI baseline 閘設計修正（現時 100/100 全紅）

### B1 已確認事實（我逐個檔實測，非推測）

| 項目 | 實測 |
|---|---|
| 最近 100 個 regression run | **100 個全 failure**（11-13：67、11-14：33） |
| 失敗項 | `[L1] 輸入完整性:CSV sha256 與凍結清單一致`、`[L1] golden:當前引擎輸出與 baseline 完全一致` |
| baseline 凍結 | `tests/inputs/signals_input.json`，`frozen_at: 2026-10-20T16:48:31Z`，98 signal |
| 漂移 | **76 / 98** 個 CSV sha256 已變（22 個仍一致），0 個 missing |
| 漂移原因 | 每日資料同步（11-07、11-08、11-13 04:46、11-14 04:41）——**正常業務行為，唔係缺陷** |
| CSV 總大小 | 97 個檔，39.4 MB |

### B2 根因判斷

**唔係 code 壞，係閘設計錯**：閘把 2026-10-20 的 CSV hash 凍死，但同一批 CSV 每日被同步更新。第一次資料同步之後，這個閘就數學上不可能綠。所以它由 11-13 起一直紅，而紅燈被當成雜訊忽略——呢個正是「閘失效」最危險的形態。

### B3 修法（三個方案，你揀一個並附理由；我推薦 P2）

| 方案 | 做法 | 成本 | 代價 |
|---|---|---|---|
| P1 快照入庫 | 把 98 個 CSV 複本 pin 入 `tests/inputs/csv/` | +39 MB（repo 已 664 MB） | repo 再肥一截；每次重凍要再複製 |
| **P2 git 歷史取檔（推薦）** | 用 `git show <frozen_commit>:<csv_path>` 在測試時從歷史重建凍結版 CSV，hash 對它、引擎跑它 | **零額外儲存** | 需 full clone（workflow 已係 full checkout） |
| P3 拆閘 | 漂移降為 warning，golden diff 改對「當次 freeze 重算」 | 最低 | 失去凍結參照，等於無閘 |

**P2 為何推薦**：`bd02df7b` 的 CSV 內容永久留在 git history，`git show` 隨時可取；唔需要複製 39 MB；而且它精確重現「凍結當時的輸入」，所以引擎輸出與 `baseline.json` 的比對仍然有意義（真正能抓 engine regression）。

**P2 實作要點**
- `signals_input.json` 加欄 `frozen_commit`（已有 `git_commit: bd02df7b`，可沿用）
- 測試改讀 `git show` 出來的 buffer，唔讀 `downloads/`
- `no_csv` 的 7 個 signal 照樣 skip
- 保留一條**獨立**的「今日資料是否新鮮」閘（現有 L22 data-freshness 已做），唔要同 golden 混在一起

### B4 驗收閘

| # | 閘 | 判準 |
|---|---|---|
| B-G1 | 本地重現 | `node --test tests/golden.test.mjs` exit **0**，`# fail 0` |
| B-G2 | 歷史取檔正確 | 隨機抽 3 個 signal，`git show bd02df7b:<csv>` 的 sha256 == `signals_input.json` 內 `csv_sha256` |
| B-G3 | 真能抓 regression | 故意改一個引擎數值 → 測試必紅（證明閘未失效）；改回 → 綠 |
| B-G4 | 漂移唔再誤紅 | 今日 `downloads/` 有 76 個已漂移，測試仍須綠 |
| B-G5 | CI 真綠 | push 後 `gh run list --workflow=regression --limit 1` = `success` |
| B-G6 | 其他閘未受影響 | link-check／encryption-check／conflict-marker／page-quality／data-freshness 全部仍 success |

**B-G3 係關鍵**：如果只求「令它變綠」，P3 也可以綠，但閘已死。必須證明改壞引擎會紅。

## 三、範圍邊界

- 你可以改：`.github/workflows/`、`tests/`、`scripts/lane_*`、`martin_v4_engine.js` 相關（只限 B 包必要）
- 你**唔可以**改：TASKS.md、`docs/admin/tasks_board.html`、`exchange/from_openclaw/`、`exchange/from_zcode/` 以外的 lane 目錄
- 你**唔可以**把 secret 值寫入任何檔案
- 兩個包可以分兩次交付，A 先 B 後或並行都可

## 四、回報方式

- 交付信：`exchange/from_zcode/YYYYMMDD_HHMM_交付_GitHub通道與baseline修正.md`
- notify：`exchange/notify/from_zcode/YYYYMMDD_HHMM_交付_GitHub通道.md`（三行，<1KB，同 commit）
- 信中每條 A-G／B-G 附「指令＋真實輸出」，缺一項即我退回

— OpenClaw（data lane）2026-11-14 16:20
