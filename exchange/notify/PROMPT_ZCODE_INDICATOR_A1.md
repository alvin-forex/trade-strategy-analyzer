# PROMPT — 波幅指標線（ZCODE 接單指令）v1.0

- 對象：`@TG_AutoClawZcode_bot`（新加入群組嘅寫 code agent）
- 派工：OpenClaw（中央派工）｜規劃：AutoClaw（AC）｜業主：Alvin
- 需求書：`docs/indicator/INDICATOR_REQUIREMENT_v0.2.md`（2026-11-17 21:18 老闆「ok 就開工」）

---

## 任務：波幅指標 A1（引擎線第一階段）

### 第一步：讀需求（順序唔准跳）
1. `docs/indicator/INDICATOR_REQUIREMENT_v0.2.md` — 需求書 v0.2（兩條交付線、核心算法、三層容差、溯源欄位）
2. `docs/martingale/TSA_Martingale_Technical_Docs_v1.0.md` §14／§14.1 — 數據管線同檢核範式（參考）
3. 群組 #1694／#1702 — AC 定稿全文（ZigZag 12/5/3 ＋ Merge 35%、80/15/5 分檔）

### 第二步：報環境（唔准寫碼）
- `python --version`
- `pip show MetaTrader5`（有無裝）
- MT5 終端有無裝（路徑＋版本）
- 回報格式：**需求摘要 ≤200 字 ＋ 缺口 ≤5 條 ＋ 環境狀態**

### 第三步：出設計（停手等批准）
設計必須講清：
- 模組切分：`zigzag.py` / `merge.py` / `buckets.py` / `mt5_source.py` / `mcp_server.py`
- ZigZag 判定邏輯：Depth／Deviation／Backstep 語義，confirmed pivot 條件寫死
- **Merge 35% 基準**：回調相對「上一段波幅」定「最近極點」——要有理由，唔准含混
- 分檔：nearest-rank 同 PERCENTILE.INC 兩法都要，可切換；樣本不足行為明確
- 資料契約：`waves.csv` 欄位（`idx,startTime,endTime,bars,amplitudePips`）、時間格式（server time vs UTC）、pips 換算（自動讀 `symbol_digits`）
- CLI 契約（見第四步）

### 第四步：批准後實作 A1
```
python -m engine.extract --symbol EURUSD --tf H1 \
  --from 2026-09-17T02:00 --to 2026-11-16T17:00 --out waves.csv
```
**驗收**：可重跑結果一致；同窗口目標 **49 段**（券商數據唔同就記錄差異，唔准為湊數改算法）

### 第五步：停手報告
完成／證據（段數、Total bars）／commit sha／阻塞

---

## 硬性約束（違反即退回）

1. **唔准用 MT4/MT5 內建 ZigZag 指標**——自家實作，確保可移植＋確定性
2. **唔准自創算法**；未確認嘅寫入 `ASSUMPTIONS.md`
3. 只准改動 `engine/`（新目錄）；唔准郁 `docs/`、`exchange/`、`src/`、`mt4/`、`mt5/`
4. 每階段 commit 一次，前綴 `[W6.1]` `[W6.2]` …；唔准 force push
5. 未獲批准前**唔准寫 A1 實作碼**（先環境 → 再設計 → 等 AC 批准）
6. 免費額度先行：`yuanyuai glm-5.3` / GLM Coding Start Plan 用盡先用收費 model

---

## Parity 驗收基準（ground truth）

窗口 `2026.09.17 02:00 → 2026.11.16 17:00`，EURUSD H1，參數 (12)(5)(3)(35%)

| 項目 | 目標值 |
|---|---|
| 總段數 | 49 |
| 三檔段數 | 39 / 7 / 3 |
| Total bars | 631 / 210 / 162 |
| Average bars | 16.2 / 30.0 / 54.0 |

判定次序：**先對 bars（切分正確性）→ 再對 pips（換算正確性）**
⚠️ 面板「Range」欄語義未確認 → **不可作驗收標準**

---

## 後續階段（唔准提早做）
| 階段 | 內容 |
|---|---|
| A2 | 分檔統計（兩法可切換）→ 波幅表 |
| A3 | MCP server（`get_rates` / `extract_waves` / `compute_buckets` / `export_table`） |
| S4 | 多券商比較（Vantage vs Alpari 並排） |
| P2 | MQL5 指標（圖表＋面板） |

_來源：AC #1694（v0.1）／#1702（v0.2）定稿；老闆 #1695／#1698／#1701 拍板；OC commit d8d5cc46。_
