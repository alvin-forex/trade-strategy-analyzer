# TradeDashboard 功能規格書（v1.43 統一版 · MT4 + MT5）
> FF48 Alvin · 2026-10-17 · 白皮書 + 完整功能列表
> **v1.43 統一制（2026-10-17）**：MT4 同 MT5 共用同一版本號 `1.43`，唔再分開 1.43/1.14。兩個平台功能對等（同一份 8 tasks + 分桶修復 + POSITION 欄位修正）。

## 一、產品定位
MT4/MT5 圖表面板 EA：本地時序快照 + 四視圖統計 + 三層風控（NewsGuard / DDGuard / SymbolGuard），一個 panel 睇晒實倉狀態與歷史表現。

## 二、功能列表

### 2.1 介面結構
| 區塊 | 內容 |
|---|---|
| TAB bar（右上） | Positions / Alerts / DDGuard / Set 四頁切換 |
| Header | Title 兩行、AC/Balance/Equity、Free Margin、Float P/L($+%)、H/D/W/M 視圖掣、‹›翻頁 |
| 過濾器 | Symbol / Comment 輸入框（淨睇某商品/某 EA） |
| 累計 P&L 曲線 | 可開關（ChartEnable），時段內累積損益視覺化 |
| 主統計表 | 最多 10 行 × 21 欄，欄位獨立開關（ShowXxx inputs） |

### 2.2 主表 21 欄
Day(時段) | Trades | B/S | WR% | Gain$ | Gain% | WPips | Lot | TotalLot | Balance | Margin | FreeMarg | **MaxP**(時段最高浮盈) | **MaxDD**(時段最深浮虧，ring buffer 盤中) | PF | AvgP&L | Best | Worst | **MaxDD$**(歷史已實現回撤$) | **MaxDD%**(歷史已實現回撤%) | Events

> **欄位語義（v1.43 修正）**
> - `MaxDD`（第 13 欄）= 盤中浮動最深虧損（ring buffer 實時觀察，短窗真相源）
> - `MaxDD$ / MaxDD%`（第 18/19 欄）= **歷史已實現回撤**（由平倉 PnL 逐筆累計 balance 曲線 peak-to-trough），與 MaxDD 概念分家，唔再重複
> - CSV 輸出 header 順序：`MaxP → MaxDD$ → MaxDD% → PF → AvgP&L → Best → Worst`（v1.43 刪走重複欄位名）

### 2.3 四視圖分桶
H=逐小時、D=日曆日、W=ISO週、M=月份；ReportStart 起算日過濾；翻頁睇舊桶。

**v1.43 分桶修復（cross-day merge guard）**：MT5 以 posId 合併 partial close 時，若同一 posId 相隔 > 48 小時，視為獨立交易（改用 deal ticket 做 key）— 根治「9月到10月全部交易堆埋最新一日」嘅歷史堆疊 bug。

### 2.4 NewsGuard（新聞守門）
- 讀 news_guard.csv（每日 06:10 job 自動抓＋push GitHub）
- **雙來源（v1.43.1）**：主 FF（ForexFactory 週曆 JSON）＋副 TradingView 經濟日曆 API
  - **Fallback**：任一源死（429/403/timeout）另一源單獨出檔，唔會空白
  - **交叉驗證**：按「時間 ±20 分鐘 + 貨幣」配對；impact 唔一致會寫入 audit log，唔會靜靜地合併
  - 兩源都在：FF 為權威（EA 校準基礎），TV-only 只補 HIGH 事件（避免 TV 分級唔同導致過度封鎖）
  - Audit：`docs/admin/news_guard_audit.log`（matched / impact mismatch / only-in-FF / only-in-TV 清單）
- 模式：OFF / ALERT（提示）/ GUARD（熱窗內擋新倉）
- 熱窗 = 事件前 NG_BeforeMin(30) 至後 NG_AfterMin(15)
- **時區（v1.43 T7 根治 DST）**：CSV 原時間即 **HKT（+8）**；熱窗判斷全部用 `TimeGMT()+8h`（`NG_NowHKT()`），不再依賴 `NG_ServerOffsetHours`（該參數只保留做顯示/fallback）。DST 切換自動正確，唔使再人手改 offset。
- HIGH 影響事件過濾（NG_HighOnly）

### 2.5 DDGuard（回撤保護，v1.43 大改）
- **帳戶級**：DD% = (Peak−Equity)/Peak，≥20%（`DDG_MaxDDPct`）全平 + 停 AutoTrading（`DDG_AccStopAT=true` 先停全局 AT）
- **Symbol 級**：單一商品浮虧 ÷ 結餘 ≥12%（`DDG_SymMaxDDPct`）平該 symbol；`DDG_SymStopAT=false` 預設**唔鎖全局 AT**（只鎖該 symbol）
- **T2 平倉重試歸零**：`DDG_CloseRetry=4` — 先刪 pending 再平倉，重試直至零殘留；殘留數 TG 緊急警告
- **T3 手動確認恢復**：停 AT 之後**永遠唔自動重開** — 面板 DDGuard tab 出現橙色「確認恢復 / Reset Peak」掣，人手撳先解除鎖定（`g_ddgAccountArmed` 所有權喺人度）
- **T8 出入金自動校正**：每分鐘掃描 OP_BALANCE / DEAL_TYPE_BALANCE，淨額 shift `g_ddgPeakEquity` 並寫回 GV — 出入金唔會製造假回撤
- **防棘輪**：觸發後 60 分鐘鎖盤（DDG_LockMinutes），peak 永不下調
- **帳號隔離**：GV key `TD_{AccountNumber}_DDG_PEAK`（MT5 用 `TD5_`），切帳戶唔會污染
- DDGuard tab 對齊表格：Float $ / DD now % / MaxDD % / MaxDD $（紅黃白三色預警）

### 2.6 SymbolGuard
逐 symbol ON / ALERT / CLOSE 三態掣（Alerts tab 內撳切換）；新 symbol 預設模式可設。`SG_ForceClose()` 連動 DDGuard per-symbol 鎖（`g_ddgSymLocked[64]` / `g_sgForcedClose[64]`）。

### 2.7 資料層
- tick 級 AccountEquity snapshot → ring buffer 20,000 筆（RecordSec 節流，30 秒 flush）
- 平倉歷史：MT4 OrderHistory / MT5 HistoryDeals（DEAL_ENTRY_OUT）
- **持久化（v1.43 T6 雙平台一致）**：`.bin` 二進位檔（MT4 `td4_snap.bin` / MT5 `td5_snap.bin`），格式 `[magic][count][count × (dt,bal,eq,marg,fmarg,float)]`；bin 水合優先、CSV fallback；OnDeinit 強制 flush — 重啟唔斷史
- 歷史截斷警示：分頁未開 All History 時 panel 頂部紅字提示

### 2.8 其他
SAVE profile 掣、input 指紋自動備份、週末/字體規範（內文 9pt、tab 標題 10pt 粗體、禁灰色）、panel 闊高度 clamp 圖表邊界、動態高度隨 symbol 行數增長。

### 2.9 DLL 擴充功能（v1.43 T1 前置攔截）
> 前提：Tools → Options → Expert Advisors → 勾「Allow DLL imports」

| 功能 | 觸發 | 行為 |
|---|---|---|
| **DLL 前置檢查** | OnInit / 每次呼叫 | `TERMINAL_DLLS_ALLOWED` 檢查，未授權時所有 Win32 操作只 Print 唔執行（DLL-01/06 攔截） |
| **DDG_StopAutoTrade**（default ON） | DDGuard 觸發 | WM_COMMAND(33020/32851) 撳停 terminal AutoTrading 掣 → 成個 terminal 所有 EA 即停；**唔會自動重開**（v1.43 T3：人手按 Reset Peak 先恢復） |
| **DDG_Popup**（default OFF） | DDGuard 觸發 | MessageBoxW 原生 Windows 彈窗（注意：彈窗會 block EA 直到撳OK，建議只喺人手睇盤時開） |

### 2.10 Telegram 直推通知（v1.43 T5 強化）> wininet.dll HTTP POST → api.telegram.org（免白名單、免 WebRequest）；token 由 MQL# Files tg_token.txt 讀入（唔入 source，v1.43 加 CR/LF strip）

| 事件 | 訊息內容 |
|---|---|
| 🚨 帳戶級 DD≥20% 觸發 | AC / DD% / Peak / Equity / 全平✅+AT停🛑 / 鎖盤至 |
| ⚠️ 單 symbol DD≥12% 觸發 | Symbol / 浮虧 / 平倉+AT停 / 鎖盤至 |
| 🛡 NewsGuard 熱窗開啟 | 事件 / 貨幣 / 窗口 / 模式 |
| ✅ 鎖盤結束 | AlgoTrading 已恢復 + 時間戳 |

參數：TG_ChatID、TG_TokenFile、TG_Enable、TG_MinGapMin=10（同 key 10 分鐘內唔重發）；DLL 未勾時 fallback SendNotification。T5 新增：wininet timeout 防 hang、JSON POST、token 去白空格。

### 2.11 統計公式規格（v1.43 逐欄對照修正）
| 欄 | 公式 | v1.43 狀態 |
|---|---|---|
| Trades / B/S | 開倉方向筆數（買入倉/賣出倉） | ✅ |
| WR% | 盈利筆數 ÷ 總筆數 × 100 | ✅ |
| Gain$ | 平倉 Profit + Swap + Commission | ✅ |
| Gain% | 對時段起始 Balance | ✅ |
| WPips | 按倉位方向加權點數 | ✅ |
| Lot / TotalLot | 時段手數 / 累計手數 | ✅ |
| Balance | 時段結束結餘 | ✅ |
| Margin / FreeMarg | ring buffer 時段內最大/最小 | ✅ |
| MaxP | ring buffer 時段內最大浮盈 | ✅ |
| MaxDD | ring buffer 時段內最深浮虧（盤中） | ✅ |
| MaxDD$ / MaxDD% | **已實現回撤**（平倉 PnL 曲線 peak-to-trough） | ✅ v1.43 新 |
| PF | Gain$ 正 ÷ Gain$ 負絕對值；**全勝時 = 99.99**（v1.43 修正，舊 99.0） | ✅ |
| AvgP&L | Gain$ ÷ Trades | ✅ |
| Best / Worst | 時段內最佳/最差單筆 | ✅ |

## 三、白皮書：設計決策與理由

### 3.1 點解用 ring buffer + history 混合
浮動 P/L 路徑（MaxP/MaxDD）只有實時觀察到，平倉後就冇 — 所以 tick 快照係唯一真相源；但 20,000 筆僅約 5.5 小時，長統計必須靠平倉歷史補。兩者口徑不同（短窗=真實浮動、長窗=已實現），文檔明示以免誤讀。

### 3.2 高水位（high-watermark）哲學
MaxDD 由歷史高位計，唔因反彈重置 — 專業風控標準。但觸發平倉後若 peak 直接落返當前 equity，會陷入「棘輪陷阱」（連環蝕 5%×N 次都當合規）。解法：觸發後時限鎖盤而 peak 不動 — 保防線不下移。

### 3.3 帳號隔離
MT4/MT5 Global Variables 係 terminal 級共享，切帳戶（demo→live）會撈亂 peak 引發假 DD 誤平倉。key 嵌入 AccountNumber() 係零成本防護。

### 3.4 時區校正（v1.43 T7 改進）
舊版靠 `NG_ServerOffsetHours=-5` 補償 broker server 時間差，但 DST 切換會變 −4h 要人手改。v1.43 改用**雙 HKT 函數**：`NG_EvTimeHKT()`（CSV 原時間即 HKT，零轉換）+ `NG_NowHKT()`（=`TimeGMT()+8h`）。GMT 唔受 DST 影響 → 熱窗全年正確，offset 參數只保留做顯示/fallback。

### 3.5 前綴物件清理
MT4 ObjectsDeleteAll(0, prefix) 批次刪取代硬編碼清單 — tab 切換疊字嘅根治法，加新欄位唔會再漏。

### 3.6 出入金校正（v1.43 T8）
裸 peak 會被出入金污染：入金推高 equity → peak 升 → 之後正常波動變「假回撤」；出金則製造「假高峰」。每分鐘掃描 balance op 淨額，`peak = max(eq, peak + delta)` 校正後寫回 GV，出入金前後 DD 計法不變。

### 3.7 已知限制
- ring 深度 ~5.5h（可調 20,000 筆）
- GV 4 週無存取會被 terminal 清（長假後 peak 或需重建）；bin 檔水合（T6）緩解
- NewsGuard CSV 依賴每日 06:10 job（雙源 + fallback，2026-10-17 起）；EA 讀本地檔仍要人手落檔或 WebRequest 拉（自動化為未來項）
- ShellExecuteW SAVE 掣需開 DLL 權限（VPS 合規環境或禁）

## 四、版本史
| 版本 | 重點 |
|---|---|
| v1.14→1.22 | 統計表 + 視圖 + 過濾器基礎 |
| v1.23 | NewsGuard + DDGuard 模組併入 |
| v1.25 | SymbolGuard |
| v1.27-1.29 | 四 tab 架構 + DDG symbol 表 |
| v1.33 | tabs 右上角 + clamp |
| v1.34 | 疊字修復（前綴清理） |
| v1.35 | 時區 / 帳號隔離 / 防棘輪 / 歷史警示 |
| v1.36 | 字體統一 + 禁灰 |
| v1.38 | DDGuard 對齊表格 + MaxP/MaxDD 改名 |
| v1.39 | 動態 panel 高度 |
| v1.40 | DLL：觸發時自動撳停 AutoTrading + 彈窗選項 |
| v1.41 | 老闆設定：全倉 20% / 單 symbol 12% 停 AT |
| v1.42 | TG 直推通知（wininet，4 事件 template + 防轟炸 + token 檔案化） |
| **v1.43** | **T1 DLL 前置攔截 + T2 平倉重試歸零 + T3 手動確認恢復（唔自動重開 AT）+ T4 帳戶/symbol 鎖拆分 + T5 TG timeout/JSON/token strip + T6 雙平台 .bin 持久化 + T7 NewsGuard HKT 根治 DST + T8 出入金 peak 校正；POSITION 欄位修正（已實現 MaxDD$/% 分家、PF 全勝 99.99、CSV 重複欄刪除）；分桶 cross-day merge guard** |
| TD5 v1.00 | MT5 骨架（核心保護 + 10 欄） |
| TD5 v1.10 | MT5 全功能移植（✅ 已完成：2,190 行、21 欄齊、0 errors） |
| TD5 v1.11 | DLL：AlgoTrading 自動撳停（cmd 32851）+ 彈窗 |
| TD5 v1.12 | 老闆設定 20%/12% |
| TD5 v1.13 | TG 直推通知（MT5 版 wininet） |
| **v1.43（MT5）** | **MT5 port of v1.43（8 tasks + 分桶修復 + POSITION 欄位修正，0 errors / 0 warnings）— 2026-10-17 起版本號同 MT4 統一為 1.43** |
