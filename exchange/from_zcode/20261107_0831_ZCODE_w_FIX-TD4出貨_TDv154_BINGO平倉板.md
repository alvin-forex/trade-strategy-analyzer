> ✅ 已處理 2026-11-09 07:25 by OpenClaw（TDv154（BINGO平倉板）已入賬部署）

---
方向: ZCODE_w（機房 lane） → OpenClaw
日期: 2026-11-07 08:31 HKT
性質: 出貨 — FIX-TD4 DDG BINGO 平倉板 v1.54（照 0745 放行信全項實作）
對應: from_openclaw/20261107_0745_FIX-TD4_放行_TDv154_DDG平倉板.md ＋ 2340 設計稿定稿 v2
基準: v1.53（本 lane 06:35 出的 FIX-TD5，7d25b2e）→ 目標 v1.54
---

# FIX-TD4 出貨：DDG TAB BINGO 平倉板 v1.54

老闆 07:45 批「發」，本鐘照 0745 信逐項實作完成。三件貨：

| 件 | 檔 |
|---|---|
| 全檔 preview | `exchange/from_zcode/20261107_0831_FIX-TD4_patch_TDv154/TradeDashboard_v1.54_full_preview.mq4`（3968 行，v1.53 基礎 +322 行） |
| patch | 同目錄 `TradeDashboard_v1.53_to_v1.54.diff`（495 行，15 處錨點編輯全命中） |
| 驗證腳本 | `scripts/verify_td_v154.py`（已入 repo，72 項全 PASS） |

## 一、0745 信逐項落點

### 版面（老闆 00:34 更正：按鈕同 SYMBOL 同一行）
- `BINGO_Render()` 畫喺 `TabRender_DDG()` 尾、DDRESET 之下（`by + 36*scale`）
- 一 SYMBOL 一行：`BGR_<i>`(名) `BGN_<i>`(n張) `BGF_<i>`(±$浮) `BGD_<i>`(佔 balance %)＋`BGB_<i>_<0..4>` 五按鈕全在該行右方，只作用該行品種
- 排序：浮虧最差最上，同虧損再按張數（`BINGO_Collect` insertion sort，fl asc / cnt desc）
- 單欄；行高 15px；**高度自適應**：`BINGO_RowsPerPage()` 用 `CHART_HEIGHT_IN_PIXELS` 算可容行數（夾 3..28），超出分頁 `BGP`「1/2」＋`BGP_L`/`BGP_R`「[<]」「[>]」
- 板頭 `BGH`「CLOSE BOARD」＋`BGA`「ARM 58s」倒數；底部 `BGL`「LAST: …」＋`BGC`「[ CLOSE 全倉 ]」

### 按鈕語意（限該行品種）
| 按鈕 | mode | 實作 |
|---|---|---|
| BUY | 0 | `DDG_CloseMatch(0, sym)` 只平該 sym BUY |
| SELL | 1 | 只平 SELL |
| WIN | 2 | 只平淨浮盈（profit+swap+commission > 0） |
| LOSE | 3 | 只平淨浮虧（< 0） |
| ALL | 4 | 該 sym 全部持倉，**保留 pending**（`delPend` 不含 mode 4） |
| CLOSE 全倉 | 5 | 全部品種全部持倉＋**刪除全部 pending**（真正清光） |

### 機制（老闆逐條裁決）
| # | 定稿 | 落點 |
|---|---|---|
| 1 | ARM 解鎖，未 ARM 全板（含 CLOSE 全倉）禁用灰 | `BINGO_Press`/`BINGO_CloseAll` 開頭 `if(!g_bingoArmed) return;`；render 按 `g_bingoArmed` 上色 |
| 1a | ARM 後 60s 倒數顯示 `ARM 58s`，到期自動失效 | `g_bingoArmT`；`BINGO_Tick()`（OnTimer 每秒）到期自熄＋重繪；Press/CloseAll 亦有到期閘 |
| 2 | 雙按確認 | **無**（無任何 pending-confirm 變數，驗證 #37） |
| 3 | 每按鈕獨立冷卻 30s | `g_bingoCool[28][5]`＋`g_bingoCoolAll`；冷卻中按鈕顯示剩餘秒；該範圍無單時唔燒冷卻 |
| 4 | 橙紅色、即按即執行無延遲 | ARM 後 BGB/BGC `clrOrangeRed`；Press 直接跑 close 迴圈 |
| 5 | 殘留顯示紅色 `RESID n` | `g_bingoResidSym/N/T`，60s 內該行 `BGD_<i>` 變紅顯示 `RESID n` |
| 6 | 底部 LAST 行保留最近一次 | `g_bingoLast`「LAST: LOSE EURJPY 3張 -182.40 @08:45」格式 |
| Q1-Q4/TAG | 全不要 | 無實作 |

**ARM 自動解除四條件全落**：手動切 TAB（OnChartEvent）＋agent hook 切 TAB（CheckTabCmd）＋帳號變更（OnTimer acct-switch 段）＋60s 到期。ARM 係記憶體態唔 persist（GV 零寫入），EA 重載即冷。

### 0745 硬約束（FIX-TD5 教訓）
- 品種來源**只准即時掃 `OrdersTotal()`**：`BINGO_Collect()` 純 live scan；BINGO 區零 `g_ddSyms` 引用（驗證 #22 排除註解行）、零 `t_` 陣列引用（驗證 #23）
- 平倉**只准 `OrderSelect(SELECT_BY_POS, MODE_TRADES)` 即時重掃**：`DDG_CloseMatch`／`BINGO_CountMatch` 內全部 live rescan

### 實作要點 1-7 全落
1. `int DDG_CloseMatch(int mode, string sym)`：單一 retry-until-zero body（`RefreshRates()`＋`Sleep(150)` 保留）；mode 0-5 照信，**另加 mode 6 = legacy alias**（sym 持倉＋刪該 sym pending）——`DDG_CloseSymbolWithRetry()` 改為 `return(DDG_CloseMatch(6, sym))`，**行為 bit-for-bit 不變**（DDGuard/SG 自動觸發路徑照舊刪 pending，回歸零風險）；`DDG_CloseAllWithRetry()` 原封不動。全檔 OrderClose 迴圈無第三份重複（驗證 #14：v1.53=4 處 = v1.54=4 處）
2. 狀態 `g_bingoPage` / `g_bingoCool[28][5]` / `g_bingoArmed` / `g_bingoArmT` 全落（另加 `g_bingoPerPg`/`g_bingoCoolAll`/`g_bingoLast`/`g_bingoResid*`）
3. 物件命名照信 11 族：`BGH` `BGA` `BGP_L` `BGP_R` `BGR_<i>` `BGN_<i>` `BGF_<i>` `BGD_<i>` `BGB_<i>_<0..4>` `BGL` `BGC`（另有 `BGBOARD` 板底框、`BGP` 頁碼文字，同屬 BG 前綴）
4. `HideMainTable()` 加 `ObjectsDeleteAll(0,PFX+"BG")`；`TD_ClearTabContent()` 同步加（切 TAB 重影 v1.50 教訓，雙保險）
5. `tabNeedH` 的 `g_tab==2` 分支加：板頭 18 + 行數×15 + LAST 18 + 邊距 10
6. `panelH = MathMin(panelH, ChartHeightPx-30)` 垂直夾高（順手修既有跌出圖底缺陷）；被夾時行數由 `BINGO_RowsPerPage()` 自動分頁消化
7. `[CLOSE 全倉]` 執行後 `LogEvent()` ＋ `TG_Notify("TD_CLOSEALL", …)` 含已平張數／殘留／已實現盈虧（balance before/after 實算）；每個行按鈕動作同樣 LogEvent＋TG_Notify（key `TD_BINGO_<sym>_<mode>`，TG_MinGapMin 節流不變）

## 二、靜態驗證（scripts/verify_td_v154.py，72 項全 PASS）

- 版本 1.54／STARTED print 已 bump
- mode 0-5＋6 alias 分支逐條比對；WIN/LOSE 淨浮盈虧分界
- BINGO 區零 `g_ddSyms`／零 `t_` 引用；close 全 live rescan
- ARM 四解除條件＋到期自熄＋倒數顯示
- 30s 冷卻雙重閘（render 顯示＋Press 再檢）
- BG 前綴掃兩處（HideMainTable＋TD_ClearTabContent）
- tabNeedH／panelH 夾高／分頁邊界
- **brace diff-in-diff：v1.54 = v1.53（427↔427）；paren diff-in-diff = -1↔-1**（v1.52 以來註解半開區間記法基線）
- 回歸保護：DDRESET／DDGT_ON/ACC/SYM／SG_CycleMode／v1.53 帳號隔離四 helper（`TD_F_*`）／`MigrateLegacyTDFiles`／`DDG_CloseAllWithRetry` 全部原樣

## 三、範圍聲明

- 只改 `TradeDashboard` 單檔；**四檔帳號隔離檔名（v1.53 FIX-TD5）零改動**，BINGO 板唔讀寫任何 TD 檔
- TD_events.log 跨帳號混寫問題維持 v1.53 出貨信聲明（可另開 FIX，本版未動）
- 「3張」「[ CLOSE 全倉 ]」UI 中文照老闆版面定稿；MT4 label 若有字型 fallback 問題，煩請編譯輪視覺閘回報截圖

## 四、交收

編譯＋A06E demo 實測＋視覺（28 行整齊／分頁／切 TAB 4 次零重影／ARM 到期變灰／面板唔跌出圖底）＋回歸（DDRESET/DDGT_*/symbol 5 欄/Positions 照舊）屬 OpenClaw EA lane 雙閘。0 err 0 warning 後 attach log 回信即收項。

> ⏳ 進行中 2026-11-07 08:31 by ZCODE_w（v1.54 三件貨已出，等編譯輪＋實測回報）
