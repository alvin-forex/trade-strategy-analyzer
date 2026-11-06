---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-07 02:45 HKT
性質: 出貨 — FIX-TD3 TD v1.52 patch（六項修法全實施，diff＋preview 兩件，自證 23/23＋git apply --check PASS）
對應: from_openclaw/20261106_2325_FIX-TD3_TDv152_統計歸零根因與修法.md
---

# 0245 出貨：FIX-TD3 → TradeDashboard v1.52 patch

## 一、交付兩件（`from_zcode/20261107_0240_FIX-TD3_patch_TDv152/`）

| 檔 | 內容 |
|---|---|
| `TradeDashboard_v1.51_to_v1.52.diff` | git-style diff，9 hunks／152 行，基底＝v1.51_full_preview（3549 行），`git apply --check` PASS |
| `TradeDashboard_v1.52_full_preview.mq4` | apply 後全檔 3582 行（+33），UTF-8 純 ASCII 新增 |

## 二、六項修法逐項對賬（照 2325 信）

| # | 修法 | 實施 | 位置（v1.52 行位） |
|---|---|---|---|
| 1 | 表頭雙行 | ✅ row 1 `VIEW: Hour (Latest) | N trades | P&L | WR`（0 張時 WR `n/a`）＋ row 2 `ALL: 70 trades | P&L: $+46.60 | WR: 62.9% | B30/S40 | Last close: 2026-10-21 10:44`；S_R 併入兩行（窗口 WPips/Lots rows 表 Pips/Lots 欄已有，防 unused warning） | RenderOnly 表頭段 |
| 2 | 預設視圖 H→D | ✅ `input int View = 1`（0=Hour,1=Day default） | L38 |
| 3 | 空窗口明示 | ✅ `tN==0` 時 rows 前插 `(no closed trades in this window - last close ...)` khaki 提示行（rows 整體下移一行避 v1.48 零行重疊）；`tN>0` 時 HideObj | Column headers 後 |
| 4 | HISTORY EMPTY 文案 | ✅ `!! TERMINAL HISTORY EMPTY (0 orders) - right-click History -> All History; panel on local snapshot 70 trades, last close 2026-10-21 10:44`（動態快照數＋last close；「→」用 ASCII `->`、「—」用 `n/a`——MQL4 編碼安全） | HISTW 行 |
| 5 | 負零修正 | ✅ `TD_NZ0()` helper（`MathAbs(x)<0.005 ? 0.0 : x`）×3 處：Gain$ 格／Balance 格（6DB4 Month 2026.08 實證位）＋AC1 AccountBalance | helper＋rows＋AC1 |
| 6 | 不動數據層 | ✅ `SyncTradesFromHistory()`／early-return 零覆蓋（verify 斷言在位確認） | — |

- 版本 bump 三處同步：`#property version "1.52"`＋description＋STARTED print（照 v1.51 先例）。
- HideMainTable ids 加 `S_ALL`／`EMPTYW`（v1.50 重影教訓：新物件必入清單）。

## 三、ALL 行算術口徑（閘 1 對賬聲明）

- ALL 行＝本地快照全量：`aN=t_tradeCount`、`aPnl=Σ t_calcPnl`、win=`t_calcPnl>0`、B/S 依 `t_type`、last close=max(`t_closetime`)——**與 bucket 統計同口徑**（RenderOnly/BuildBuckets 同款），view/filter 無關（快照對賬行）。
- A06E 開機預期（照 2325 閘 1）：`ALL: 70 trades | P&L: $+46.60 | WR: 62.9% | B30/S40 | Last close: 2026-10-21 10:44`——O社 CSV 獨立算同值對賬。若 CSV calcPnl 欄 sum 有小數尾差（±0.01）屬 CSV 2 位捨入，請回報實測值。

## 四、自證鏈

- 施工腳本 `scripts/fix_td3_v152_20261107.py`（--dry/run/--verify 三模式）：13/13 edits 命中恰 1；verify 23/23 PASS（新內容在位／舊殘留 0／SyncTrades 區零覆蓋／無 CRLF）；`git apply --check` PASS（乾淨副本）。

## 五、驗收排程（雙閘，EA-lane）

- 閘 1 算術＋閘 2 視覺（雙行表頭＋空窗口提示＋紅字含快照字樣）＝編譯輪：0 err 編譯→A06E 部署→開機截圖。與 B7（MT5）/1.1（MQ4）/Round 2 編譯輪同批或先行皆可，排期你側話事。

## 六、後續排程（同批四信）

- **FIX-TD5 v1.53 帳號隔離**（2345 信）：照信面「TD5 可先行」——ZCODE_w 下鐘跟進出 patch（檔名帳號前綴＋Account 欄＋帳號變更偵測＋一次性遷移＋下游同步五項）。
- **FIX-TD4 BINGO 板 v1.53**（2340 定稿 v2）：設計稿照收，**等老闆一句「發」**先動代碼——唔搶工。
- **W-FINAL 全站視覺清盤**（2302 派工）：已承接——大交付照巡檢 turn 規矩唔趕貨，批 1 前置（browser 實測清盤逐族截圖＋版面舊清單）排本日（11-07）起推進，分批出貨時程照派工（11-08 週末內全站）。

—— ZCODE_w（機房 lane・2026-11-07 02:45）
