# SKILL 自動化分析流程運行手冊（2026-11-15）

**對應**：PRD 待辦③「分析 signal {ID}」一條龍（落載→分析→發 TG）。
**審計依據**：[PRD_BACKLOG_AUDIT_20261115.md](PRD_BACKLOG_AUDIT_20261115.md) 第③節（倉內只有半鏈：api_server 通知檔機制＋scraper 全套；SKILL 觸發端零定義）。
**本文檔用途**：陌生人可以憑本手冊喺呢部 Windows 機重複成條鏈，並知道每一環嘅實況與斷點。

---

## 一、結論（一行）

**行到。** 原設計鏈（WSL OpenClaw＋localhost:8787 api_server＋`/tmp` 通知檔）喺呢部機**完全冇基礎**（見§二），但經本次新補嘅純標準庫入口腳本 `scripts/analyze_signal_entry.py`，一條龍「下載 CSV→倉位分析→存 DB→TG 通知」已實測跑通兩個信號（見§三）。

---

## 二、執行環境核實（2026-11-15 實測）

| 項目 | 實測結果 | 影響 |
|------|----------|------|
| Windows Python | `Python 3.13.15`，指向 `C:\Users\alvin\AppData\Local\Programs\AutoClaw2\resources\vendor\python\python.exe`（AutoClaw 自帶） | 唔使裝 Python；但注意新開 PowerShell 若 `python` 彈 Microsoft Store，改用上述完整路徑 |
| pandas / numpy | ❌ 冇裝（`ModuleNotFoundError`） | `archive/run_analysis.py` 完整管線同 dde 評分器行唔到；lite 鏈唔需要 |
| fastapi / requests | ❌ 冇裝 | `scripts/api_server.py` 起唔到；lite 鏈唔經 HTTP |
| WSL | ❌ `wsl -l -v`／`wsl --status` 只出說明文字＝**零發行版** | 審計③「WSL 側 OpenClaw 工作區」喺呢部機不存在，倉外待證項就此了結：**呢部機冇 OpenClaw** |
| api_server（8787 埠） | ❌ `netstat -ano | findstr :8787` 零 listener | `/api/save`→TG 通知檔嗰段半鏈而家冇行 |
| `C:\tmp` | ❌ 唔存在 | api_server 即使起咗，`notify_telegram()` 寫 `/tmp/trade-analyzer-notify.json` 喺 Windows 會 `FileNotFoundError`，被 `except: pass` **靜默吞掉** |
| pip | ✅ `pip 25.3` 可用 | 補裝依賴嘅途徑喺度（見§五建議） |

---

## 三、實測記錄（跟呢個重複就係驗收）

兩個信號、兩條數據路徑（現成檔／真下載），全部 2026-11-15 喺本機實跑：

| 信號 | 路徑 | 結果（一行） |
|------|------|--------------|
| **10437** | 真下載（analytics API，2,670 筆交易） | ✅ 1,083 倉位｜WR 78.0%｜PF 1.22｜總盈虧 +$142,459.94｜MaxDD −$87,296（−41.0%）｜存 analysis #1｜通知已寫 |
| **11984** | 現成 `downloads/11984.csv`（1,461 筆交易） | ✅ 967 倉位｜WR 75.7%｜PF 1.88｜總盈虧 +$107,413.19｜MaxDD −$17,313（−16.0%）｜存 analysis #2｜通知已寫 |

**交叉驗證**：兩個信號嘅交易筆數同淨盈虧總和，同獨立代碼路徑（PowerShell `Import-Csv` 重算）**逐分吻合**（10437：2670/$142,459.94；11984：1461/$107,413.19）。
**去重驗證**：同一信號重跑，`csv_hash` 去重生效，返回同一 analysis id，唔會塞重複記錄。
**已知口徑限制**：lite 分析器同 `src/statistics.py` 公式逐條對齊（倉位＝Symbol＋方向＋平倉分鐘分組；層數＝唯一手數排名），但 `docs/detailed_comparison_all_levels_*.html` 係分層 R 倍數口徑，兩者數字唔可以直接對數。

---

## 四、逐步指令（陌生人版）

### 4.0 前置檢查（一分鐘）

```powershell
cd C:\Users\alvin\tsa-work
python --version        # 應見 3.13.x；若彈 Store 就用完整路徑：
# C:\Users\alvin\AppData\Local\Programs\AutoClaw2\resources\vendor\python\python.exe
```

### 4.1 一鍵鏈（呢個就係成條鏈）

```powershell
# A. 現成檔（downloads\{ID}.csv 已存在時）——離線都行到
python scripts\analyze_signal_entry.py 11984

# B. 真下載（本地冇檔，或要最新數據）
python scripts\analyze_signal_entry.py 10437 --refresh

# C. 完整管線（要 pandas，本機未裝，見§五）
python scripts\analyze_signal_entry.py 10437 --full
```

輸出四步：`[1/4]` 下載／用現成檔 → `[2/4]` 倉位重構分析 → `[3/4]` 存 `data/analysis_history.db` → `[4/4]` 寫通知檔 `logs/trade-analyzer-notify.jsonl`，最後印摘要。

### 4.2 查看結果（輸出側）

```powershell
python scripts\history_manager.py list --signal 11984     # 列記錄（含版本號）
python scripts\history_manager.py summary 2               # 睇指定 analysis 詳情
python scripts\history_manager.py trend 11984             # 同信號跨版本趨勢
Get-Content logs\trade-analyzer-notify.jsonl -Encoding UTF8   # TG 通知檔（一行一 JSON）
```

### 4.3 清零重跑（想由頭驗一次）

```powershell
Remove-Item data\analysis_history.db                      # 本地 gitignored，刪咗會自動重建（entry 腳本自帶建表）
python scripts\analyze_signal_entry.py 11984
```

---

## 五、依賴清單

**現有即用（零安裝）**：`scripts/analyze_signal_entry.py` 只用標準庫（urllib／csv／sqlite3／json／hashlib／datetime）＋ repo 既有 `scripts/history_manager.py`（同樣純標準庫）。

**建議安裝（唔裝唔影響 lite 鏈；裝咗解鎖完整管線）**：

| 套件 | 解鎖咩 | 安裝（vendor python） |
|------|--------|----------------------|
| `pandas`＋`numpy` | `archive/run_analysis.py` 深入分析＋HTML 報告（`--full`）；dde_v5 評分器 | `python -m pip install pandas numpy` |
| `fastapi`＋`uvicorn` | `scripts/api_server.py`（localhost:8787，前端 POST /api/save 用） | `python -m pip install fastapi "uvicorn[standard]"` |

> 邊界說明：本次任務按規定**冇即場安裝**任何大型依賴；上表留俾老闆裁決後執行。裝完 pandas 後記住補驗 `--full` 路徑（本次未驗）。

---

## 六、現時斷點（邊度仲未駁通）

1. **api_server 冇行**：8787 零 listener（§二）。即係前端 GitHub Pages→`POST /api/save`→通知檔嗰段**而家唔存在**。lite 鏈已繞過（直接 call `history_manager.save_analysis()`，效果等同 /api/save 落庫＋通知）。
2. **api_server 通知路徑喺 Windows 斷**：`api_server.py:42` 寫 `/tmp/trade-analyzer-notify.json`，Windows 冇 `/tmp` 且 `except: pass` 靜默吞錯。要復用 api_server 嘅話，建議將路徑改為環境變數（例如 `TSA_NOTIFY_FILE`）預設 `logs/trade-analyzer-notify.jsonl`——本次未改（超出最細範圍，留俾老闆）。
3. **WSL／OpenClaw 不存在**：零發行版。審計③嘅倉外待證項（WSL 側 skill 定義）喺呢部機**證否**。TG 發送惟一現實路徑＝AutoClaw 端（§七）。
4. **AutoClaw 端 skill 定義仍未建立**：倉內＋agent 端都冇「分析 signal {ID}」skill 檔；本次補嘅係俾 skill call 嘅指令（§七），skill 檔本身屬 agent 端配置動作。
5. **`scripts/batch_csv_downloader.py` 硬編碼 WSL 路徑**（`OUTPUT_DIR = /home/alvin/.openclaw/...`）而且冇單信號參數——冇改佢，entry 腳本自帶同源下載邏輯（同 URL／UA／內容檢查），輸出採用 `downloads/` 現行 bare-id 命名。
6. **`analysis_history.db` schema 倉內零 CREATE TABLE**（原 schema 倉外手建）：entry 腳本已自帶 `CREATE TABLE IF NOT EXISTS`（欄位照 `history_manager.py` 實際 INSERT/SELECT），呢個斷點對新機已補。
7. **`--full` 未驗證**：缺 pandas。裝完後跑 `python scripts\analyze_signal_entry.py 10437 --full` 補驗。
8. **監看限制（實渐發現）**：AutoClaw `workspace.file_tail` 監看**只收 workspace 內相對路徑**，repo（`C:\Users\alvin\tsa-work`）喺 workspace 外，通知檔唔可以直接 monitor。所以 agent 接線走 stdout（§七），通知檔保留為 api_server 兼容落點。
9. **數據質量陷阱（實渐撞到）**：algoforest export 嘅 CSV 會喺**檔案中段**滲 BOM 字元（\ufeff）落個別 Open Time 欄，令日期解析失敗。entry 腳本已處理（逐 cell 剝 \ufeff）；若日後用 pandas 管線記住同樣處理。

---

## 七、AutoClaw 端 skill 應該 call 邊條指令

**主指令（一條）：**

```
python C:\Users\alvin\tsa-work\scripts\analyze_signal_entry.py {信號ID}
```

- 參數：`{ID}` 純數字；`--refresh` 強制重新下載；`--full` 行完整管線（需 pandas）。
- **結果讀法**：stdout 最後「===== 摘要 =====」四行就係可直接轉發 TG 嘅內容；agent 收到即轉發，**唔需要**通知檔／HTTP。
- 通知檔 `logs/trade-analyzer-notify.jsonl` 係 `api_server.notify_telegram` 同格式嘅兼容落點（`{"ts":…,"msg":…}` 一行一 JSON），將來若有常駐消費方可以直接接管。
- 建議 skill 觸發句式：`分析 signal {ID}`→執行上指令→摘要轉發。

**憑證與敏感資訊（只記位置與型態，唔記值）**：
- lite 鏈＋下載 API：**零 token**（公開 export endpoint）。
- 如日後啟用 api_server：寫入端 token 喺環境變數 `TSA_API_TOKEN`（型態：字串；經 `x-api-key` header 或 `api_key` query 傳；未設時僅限 localhost 寫入——見 `scripts/api_server.py` `require_api_token`）。
- Telegram 發送憑證：一律喺 agent（AutoClaw）端既有 TG 連線，repo 內零存放。

---

## 八、本次實測遺留物質

- `scripts/analyze_signal_entry.py`：新入口腳本（已 commit）。
- `downloads/10437.csv`：實測真下載嘅新數據檔（untracked→本次隨 commit 入庫，同 downloads/ 既有 2,969 個追蹤 CSV 同一慣例）。
- `data/analysis_history.db`：本地 runtime（gitignored），含實測 #1（10437）、#2（11984）。
- `logs/trade-analyzer-notify.jsonl`：本地 runtime（gitignored），含實測通知行。
- `ea_name_mapping.json`：修好一處令全檔 parse 唔到嘅殘留行（`Total signals: 80`）＋去 BOM；80 條映射完整保留。

*本文檔由任務③（SKILL 自動化鏈核實＋補駁通）產出；⑦ Walk-Forward、⑧覆盤自動化屬隊友範圍，本文檔不涉。*
