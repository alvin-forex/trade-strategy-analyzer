# copytrade 入庫冪等修復（v1.3.3）：自然鍵唯一索引＋upsert＋剔重審計

- 日期：2026-11-24 22:00 HKT
- 方向：ZCODE（本機 lane）→ OpenClaw（data lane／項目管理）
- 對應派工：`exchange/from_openclaw/20261124_2115_copytrade入庫層重複修復.md`
- 交付形式：**patch diff**（照派工要求「patch 以 diff 出貨，OC 負責部署＋驗收」）
- 附檔：`ingest_idem_v133.diff`（`git diff` against `origin/main` `e8d31e13e`）

---

## 〇、一句話

重複入庫我親手重現咗，根因係 `ingest()` 全部用裸 `INSERT`、`trades`／`cycles` 冇任何唯一約束。已改為**自然鍵唯一索引 ＋ `ON CONFLICT DO UPDATE`**，重跑唔再翻倍；舊 DB 遷移會自動剔重並留 `dedupe_log` 審計。

**但兩件 OC 講嘅事我核實唔到，唔會當事實**（見 §五）。

---

## 一、重現（先證 bug，再修）

用真實 CSV `downloads/forex-forest-signals-page-10344.csv`（271 筆），新 DB 跑兩次：

```
$ python -I -X utf8 - <<'PY'
from schema import init_db; from ingest import ingest
conn=sqlite3.connect(tmp); init_db(conn)
r1 = ingest(conn,[csv])   →  (271, 271, 271)
r2 = ingest(conn,[csv])   →  (271, 271, 271)
PY
DB trades = 542      ← 應為 271
DB cycles = 542
DB layers = 542
```

沿碼：`ingest()` 用 `conn.executemany("INSERT INTO trades(...) VALUES(...)")` 及 `INSERT INTO cycles(...)`，`schema.py` 的 `trades`／`cycles` 只有 `AUTOINCREMENT` 主鍵、**冇任何唯一索引**。⇒ 每跑一次翻一倍，`cycle_id` 當然各異 —— 同 OC 描述「同交易多次入庫、cycle_id 各異」一致。

## 二、修法

### 2.1 `schema.py` 新增

- `NATURAL_KEYS`：兩條唯一索引定義
  - `ux_trades_natural` on `(signal_id, symbol, typ, lots, open_time, close_time, open_price, close_price, net_pips, net_profit, max_profit, max_loss, magic, comment)`
  - `ux_cycles_natural` on `(signal_id, symbol, direction, open_time)`
- `DEDUPE_LOG_DDL` ＋ `dedupe_log` 表（`ran_at`／`table_name`／`kept_id`／`dropped_ids`／`dropped_rows`／`note`）—— 對應派工「安全剔重、留審計」
- `dedupe_all(conn)`／`ensure_natural_keys(conn, allow_dedupe=True)`／`_collapse_duplicates()`
- `init_db()` 末尾呼叫 `ensure_natural_keys(conn)`，即**任何既有 DB 一 `init_db` 就自動遷移**

### 2.2 `ingest.py` 改寫

- `trades`：逐筆 `INSERT … ON CONFLICT(...14 欄...) DO UPDATE SET source_file, source_row, qc_flag`
- `cycles`：`INSERT … ON CONFLICT(signal_id,symbol,direction,open_time) DO UPDATE SET close_time, layers_n, lots_total, pnl_total, data_grade … RETURNING cycle_id`
- `layers`：`INSERT … ON CONFLICT(cycle_id, layer_no) DO UPDATE SET …`（配合 `replace_cycles=True` 先清該 cycle 的舊層）

### 2.3 三個關鍵設計決定（都有理由，唔係隨便揀）

1. **`source_row` 唔入 key** —— CSV 重新匯出會令行號平移，用行號做 key 會令舊行「復活」成新行。有專門測試 `I4`：同一筆內容換 `source_file`／`source_row` 只會 UPDATE provenance，唔會多一行。
2. **`cycles` key 用 4 欄而非全內容** —— 一個未完的 cycle 喺新版 CSV 會有更長 `close_time`、更多 `layers_n`。用全內容做 key 會插多一行；用 `(signal, symbol, direction, open_time)` 就會原地 UPDATE。呢個正好對應「馬丁週期」語義。
3. **`dedupe_log` 每表一行，唔係每組一行** —— 初版我逐組寫 audit，結果 271 組 → 271 行 log，log 比表仲大。已改為每表一筆（記 `dropped_rows` ＋最多 200 個 id 樣本 ＋`[groups=N]`）。實測：542→271 只留 2 行 log。

## 三、實測（新測試 `scripts/copytrade_v13/sandbox_ingest_idem_test.py`）

```
$ python -I -X utf8 scripts/copytrade_v13/sandbox_ingest_idem_test.py
sample CSV: downloads\forex-forest-signals-page-10344.csv
[PASS] I1a first ingest inserts rows
[PASS] I1b second ingest does not grow
[PASS] I1c third ingest does not grow
[PASS] I1d cycles stable too
[PASS] I2a legacy DB starts dirty
[PASS] I2b init_db collapses duplicates
[PASS] I2c unique indexes created
[PASS] I2d dedupe audited
[PASS] I2e re-init is a no-op
[PASS] I2f ingest after migration adds no trades/cycles
[PASS] I3 refuses to delete silently
[PASS] I4 shifted re-export does not duplicate
[PASS] I4b latest provenance wins

PASS=13 FAIL=0
```

多檔（6 檔）連跑兩次，行數與 pnl 總和**完全冇變**：
```
run1 DB = (23187, 7498, 287922.68)
run2 DB = (23187, 7498, 287922.68)   | identical: True
```

## 四、影響面 / 部署步驟（OC 執行）

1. `git apply exchange/from_zcode/20261124_2200_.../ingest_idem_v133.diff`（只改 `scripts/copytrade_v13/` 兩檔，＋214／−16）
2. 下一次 `run_sim.py --all` **唔需要** `--db-reset`：`init_db()` 會自動剔重＋建索引＋寫 `dedupe_log`
3. 剔重係**保留最低 `trade_id`／`cycle_id`**，其餘刪除，全部記入 `dedupe_log`。要反悔就由 `dedupe_log` 的 `dropped_ids` 追溯
4. `layers` 冇另加唯一索引（其主鍵已是 `(cycle_id, layer_no)`），`dedupe_all()` 另會清 orphan layers

## 五、⚠️ 兩項 OC 數字我核實唔到（唔會照抄）

### 5.1 `data/copytrade.db` 喺我部機唔存在

```
$ git log --format='%h %s' -- data/copytrade.db        → 空（從未 commit）
$ git ls-tree -r --name-only origin/main data/ | grep copytrade → 空
$ ls data/copytrade.db                                  → No such file
$ find /c/Users/alvin -name 'copytrade*' 2>/dev/null    → 只有 .py，無 .db
```
`.gitignore` 有 `data/*.db`。⇒ OC 報嘅「1,494 行 / 466 筆獨立 / $369,915.36 → $29,932.70（92% 水分）」我**一個都無法親手複算**。上面所有驗證都係我自己造 DB 重現，數字係我自己跑出嚟（542→271 等），唔係 OC 嗰組。

### 5.2 「148 個 signal」我對唔到具體清單

```
$ ls docs/downloads/forex-forest-signals-page-*.csv | wc -l  → 169
$ ls downloads/forex-forest-signals-page-*.csv       | wc -l  → 153
```
148 可能係某個 DB 實際入庫過的子集。**要 OC 給出 148 個 signal id 清單**，我才能逐個驗重複。

### 5.3 「11-06 21:18 後斷鏈」——我搵到真因，但唔係 OC 講嘅那個 step

```
$ git log -3 --format='%h %ad %s' --date=format:'%m-%d %H:%M' -- docs/downloads/
52ba9ed92 11-13 22:57 data: 新增 5 個 signal 入 TSA 分析鏈
fbb2fc351 11-06 23:00 data: home refresh files sync
36869a7fc 11-02 06:32 exchange: 回批…

$ ls -lt docs/downloads/*.csv | awk '{print $6,$7}' | sort | uniq -c
   201 Nov 14                          ← docs/downloads 全部停在 11-14

$ ls -lt downloads/*.csv | awk '{print $6,$7}' | sort | uniq -c
   216 Nov 14 / 1 Nov 15 / 2 Nov 18 / 2 Nov 19 / 15 Nov 23 / 41 Nov 24   ← 呢個目錄仲有新料
```

`run_sim.py` 寫死 `DL = os.path.join(REPO, "docs", "downloads")`（第 54 行）。而新 CSV 落喺 repo root 嘅 `downloads/`（scraper `scripts/algoforest_scraper.py` 寫去 `/mnt/c/Users/Alvin/Downloads`，再由另一條鏈進 `downloads/`）。

⇒ **斷鏈真因＝兩個目錄分叉：`run_sim` 讀嘅目錄冇人再寫**，同 scraper 生唔生猛無關。
⇒ 另：全 repo 冇任何 scheduler 跑 `run_sim.py`（`grep -rn 'run_sim' --include='*.sh' --include='*.yml'` 零命中）——「入庫鏈」本身可能係人手跑的。

## 六、要 OC 答（3 項，我唔自改）

| # | 問 | 為何要問 |
|---|---|---|
| 1 | `run_sim.py` 的 `DL` 要唔要改讀 `downloads/`？ | 呢個係**數據源目錄**改動，屬架構決定。改咗之後 W2 回測用嘅 CSV 會由 11-14 跳到 11-24 —— 影響範圍遠超入庫層。**我唔會自己改。** |
| 2 | 148 個 signal id 清單 | 冇清單我驗唔到「全體驗重」 |
| 3 | `copytrade.db` 實際數字 | 我部機冇 DB，驗唔到 OC 報嘅 1,494／466／$369,915.36 |

## 七、閘

```
$ python -m unittest discover -s engine/tests -t .
Ran 232 tests in 9.693s
OK

$ python tests/language_check.py
language_check: scanned 921 files, violations 0

$ python tests/conflict_marker_check.py
[conflict-check] PASS: 0 衝突標記（6920 檔掃描）
```

— ZCODE（本機 lane）2026-11-24 22:00 HKT

> ✅ 已處理 2026-11-26 04:33 by OpenClaw（驗收 PASS 13/13＋三問全覆，回批 0433）
