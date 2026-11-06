# FIX-TD2 patch：TradeDashboard v1.50 → v1.51（0806 派工・Bug A＋Bug B）

出貨：ZCODE_w・2026-11-06 08:55・patch 以 diff 出貨（`patch -p1` 原地）

## Base 校正（重要）

- Base＝四 terminal 現場 v1.50（3,529 行＝v1.50 出貨 full_preview＋OpenClaw half-bump 補筆 `:700` banner v1.50）。
- 本套 `TradeDashboard_v1.50_to_v1.51.diff` 以該現場態為 base；3,529 → **3,550 行**。

## 改動內容（3,529→3,550，六處）

| # | 位置 | 改動 | 對應 |
|---|---|---|---|
| 1 | `#property version/description` | 1.50→**1.51** | 四點鎖定 |
| 2 | `:700` STARTED banner | v1.50→**v1.51** | 四點鎖定（OpenClaw 補筆版續 bump） |
| 3 | `CheckTabCmd()`（:731） | **Bug A 根治**：`FileClose` 後即刻 `FileDelete("TD_tabcmd.txt")`（read-once 語義）＋`tab=` 前綴驗證（`StringFind(cmd,"tab=")<0` 即 return） | 0806 Bug A |
| 4 | 全域 `g_histEmpty`（:146） | 新 bool | 0806 Bug B |
| 5 | `TD_CheckHistoryDepth()`（:2994） | **Bug B**：`OrdersHistoryTotal()==0` → `g_histEmpty=true`＋Print 明示 log | 0806 Bug B |
| 6 | POS 面板 HISTW render（:2567） | 三態：empty（`!! ACCOUNT HISTORY EMPTY - right-click History tab and choose All History !!`）／truncated／無 | 0806 Bug B |

## Bug A 診斷邏輯（真兇判斷）

- v1.50 diff 三處改動（version strings／HideMainTable／TD_ClearTabContent）**逐 prefix 家族核對**：TPH/DDM/DDP/DDGT/DDRESET/TPC 全部只涉 DD 頁物件，**無撞 TAB 按鈕（`TD116_TAB0-3`）或任何其他頁物件**；click handler／`g_tab` 賦值零改動。
- 「按任何 TAB 都跳去 DDGUARD、轉不到其他 tab」——全源碼 **`g_tab=2` 唯一寫入路徑＝click TAB2／`CheckTabCmd()` file hook**。`CheckTabCmd()` 由 **OnTick＋OnTimer 每 2 秒 throttle 重讀 `MQL4/Files/TD_tabcmd.txt` 且讀完唔刪＋無 `tab=` 格式驗證（v1.35 起兩個防呆漏洞）**——殘留 file（含 `tab=2`）＝每 2 秒彈返 DDG，與老闆症狀 100% 吻合。
- **請 OpenClaw 查證釘案**（6DB4）：①`MQL4/Files/TD_tabcmd.txt` 是否存在＋內容＋mtime；②`MQL4/Logs` 有冇 `TD: history truncated` Print（Bug B 釘案：earliest=0＝歷史空 vs filter 截斷）。
- **Fallback**：若 file 唔存在或 v1.51 仍跳 DDG → 下鐘出 v1.52 revert v1.50 重影修復（返 v1.49 清理邏輯），重影另法再修（照 0806 授權路徑）。

## Bug B 說明

- 症狀＝面板統計全 0 而 `TD_summary.csv` 有真數＝**面板讀 terminal「帳戶歷史」tab（MT4 無 API 改其 filter）**；`OrdersHistoryTotal()==0`（filter 空過期／切帳後未載）→ 統計全 0。MT4 側無法程式改 filter——v1.51 以**大警告行**取代靜默 0，老闆按提示右鍵→All History 即恢復實數。
- 若 log 顯示 earliest≠0（filter 截斷型）——同樣右鍵→All History；警告行文案照著指示。

## 驗證（本地全綠）

- `patch -p1 --dry-run`：0 fuzz 0 reject；實套 `cmp` **BYTE-IDENTICAL PASS**（vs full_preview）；反向 `-R` 乾淨＋byte-identical 回 base；
- brace balance 0（3,529→3,550）；paren delta 與 baseline 一致（字串內括號）；
- 錨點 grep：version 1.51×1／description 1.51×1／banner v1.51 STARTED×1／殘留 v1.49/v1.50 banner 0／`FileDelete("TD_tabcmd.txt")`×1／`tab=` guard×1／`g_histEmpty` decl×1／HISTW 文案×2（log＋panel）。

## 部署（OpenClaw）

1. 四 terminal 原地 apply（base＝現場 v1.50 3,529 行）；
2. 編譯 0 err＋md5 六點（四 terminal＋VPS 兩路，portable dated backup）；
3. **reload 後 log 應見 `=== TradeDashboard v1.51 STARTED ===`**；
4. 驗收照 0806：四 tab 互切零重影＋零跳錯＋統計欄實數（或見 HISTW 警告＝terminal 歷史 tab 需設 All）；
5. 自測注意：self-test hook（TD_tabcmd.txt）現為 read-once——**每次命令須重新寫 file**。

—— ZCODE_w（機房 lane・2026-11-06 08:55）
