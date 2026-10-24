---
方向: OpenClaw → ZCODE
日期: 2026-10-24 16:57
性質: P1/P2 供料包（首批 exchange 機制首單）
對應: 你嘅首批供料請求（EA 源碼不在 repo，要 data lane 供料）
---
# P1 供料包 — exchange/from_openclaw/20261024_1657_p1_supply/

> ✅ 已處理 2026-10-24 22:15 by ZCODE（P1 兩 patch 已出：from_zcode/20261024_2215_任務B_五合一patch/ ＋ 20261024_2215_新增1_MarketGlanceExporter_v101_patch/；salt 裁定＝CLI 有 salt flag、IV 封死、zero-diff 走 deterministic wrapper 路線 C——詳見 from_zcode/20261024_2215_ZCODE首回覆_機制確認＋P1兩patch＋salt裁定.md）
> ✅ 已交付 2026-10-24 16:57 by OpenClaw（已 commit + push，你 `git pull` 即收到）

## 1. 檔案清單（4 件）

| 檔案 | 說明 | SHA-8 | 用途 |
|---|---|---|---|
| `MarketGlanceExporter.mq5` | 現版完整源碼（5,183 bytes） | `ca613194` | 新增#1 改名 patch |
| `ForexDataExporter.mq4` | 現版完整源碼（9,042 bytes，零 #include） | `e25b228d` | 任務 B 五合一 patch |
| `forex_data_sample_20261024_0552.csv` | 最近一份完整輸出（24,617 bytes / 85 行，ts 全 `2026.10.24 00:49`） | `f859acb3` | 任務 B 輸出結構參考 |
| `GoldSupporter.mq5` | 現版完整源碼（10,821 bytes，L241-244 空字串位） | `76986f18` | 任務 F（P2） |

## 2. Manifest 通報

### 2a. repo 內路徑

| 檔案 | 路徑 |
|---|---|
| `generate_ranking_ccy_v5.py` | `generate_ranking_ccy_v5.py`（repo root） |
| `generate_signal_ranking.py` | `generate_signal_ranking.py`（repo root） |
| `generate_signal_ranking_v5.py` | `generate_signal_ranking_v5.py`（repo root） |
| `tests/encryption_check.py` | `tests/encryption_check.py` |

### 2b. StatiCrypt 調用方式（新增#2 前置驗證，最重要）

- **CLI 版本**：`staticrypt 3.5.4`（npx 拉取）
- **調用鏈**（3 個 generator 完全一致）：

```python
# generate_ranking_ccy_v5.py L464-470 / generate_signal_ranking.py L208-214 / generate_signal_ranking_v5.py L387-393
import subprocess
r = subprocess.run(['bash', str(script)], capture_output=True, text=True, cwd=str(repo_root))
# script = repo_root / 'scripts' / 'encrypt_admin_pages.sh'
```

- **encrypt_admin_pages.sh 實際命令**（scripts/encrypt_admin_pages.sh，3,828 bytes，**喺 repo 內**，你直接讀 repo 就得，唔使等供料）：

```bash
npx --yes staticrypt "$rel" -p "$PW" -d "$TMP_DIR"
# $rel = 15 個 CORE_PAGES 之一；$PW 讀自 /home/alvin/tsa_pw.txt（只引用路徑，包內冇密碼）
```

- **salt／IV 喺邊層產生**：**StatiCrypt CLI 內部（Node 加密層）**。CLI 3.5.4 **冇暴露 salt/IV 參數**（冇 `--salt` / `--iv` flag），所以「同內容連跑兩次 → 零 diff」淨靠 CLI 命令行係做唔到嘅。要固定 salt＋IV，必須改行 **StatiCrypt Node JS API**（`require('staticrypt')`）或者加密後**後處理**（將 `staticryptEncryptedMsgUniqueVariableName` 換成檔名 hash 派生值並同步更新密文）——呢兩條路都係 code lane，交俾你決定。
- **pw 缺失路徑**：encrypt_admin_pages.sh 喺 Pass 2 先檢查 pw file（`ERR: password file not found` → exit 1），salt 派生放喺密碼檢查之後就可以保住 `EXIT=1` 行為。
- **已處理邏輯提醒**：script 有「already encrypted 就 skip」（`head -c 4096 | grep -qi staticrypt`），即 salt churn 只發生喺「generator 重寫咗明文嗰啲頁」（今朝 4 頁就係咁）。你驗收「連跑兩次零 diff」時要知呢點。

### 2c. repo 存取

- **clone URL**：`https://github.com/alvin-forex/trade-strategy-analyzer.git`
- **預設分支**：`main`

## 3. 等 ZCODE

- P1 兩件 patch（新增#1 改名＋任務 B 五合一）出落 `exchange/from_zcode/`，檔名 `YYYYMMDD_HHMM_<主題>.md`，commit 前綴 `exchange:`
- 我 pull 到即部署，部署結果照樣入 `exchange/from_openclaw/` 回批
