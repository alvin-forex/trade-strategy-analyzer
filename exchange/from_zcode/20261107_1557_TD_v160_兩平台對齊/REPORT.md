> ✅ 已處理 2026-11-09 by OpenClaw（補章——v160 收貨 1540＋四台部署驗收 PASS 1705，見 from_openclaw 對應檔）

# REPORT — TradeDashboard v1.60 兩平台對齊交付（2026-11-07 15:57 HKT）

- 派工依據：`from_openclaw/20261107_1230_總派工_TD_v160_兩平台對齊.md`（範圍凍結 6 項＝1420 開工令）
- 基準：MT4 = 我方 v1.55（`20261107_0945_FIX-TD6_patch_TDv155`）／MT5 = OpenClaw v1.51（`20261107_1215` 交審版，1245 審查＝收＋netting 必修併入）
- 管道：`rename_inputs.py`（改名＋12 group 重建）→ `mt4_surgery.py` / `mt5_surgery.py`（錨定替換）→ 三閘＋`verify_v160.py`，全程機器閘、零手改

## §1 改名結果（66 行對照表執行）

| 項 | MT4 | MT5 |
|---|---|---|
| 識別符改名（code 段，string/comment 零誤傷） | **244** | **182** |
| 舊名殘留（66 表，code 段） | 0 | 0 |
| input 數 / group 數 | 68 / 12 | 68 / 12 |
| 假 `___` 分隔行 | 0 | 0 |

Case-variant 審計：`Scale`／`View` 殘餘引用全屬函數參數、局部變量、註釋與字串（`g_view=InpDefaultView` 賦值實證無誤），良性不動。

## §2 新增參數

| 參數 | 平台 | 型別/預設 | 語義 |
|---|---|---|---|
| `InpDdgAccountMaxMoney` | 兩平台 | double 0.0 | 帳戶級 DD 金額限額，與 % 限額 **OR** 觸發（0=off） |
| `InpDdgSymbolMaxMoney` | 兩平台 | double 0.0 | 品種級 DD 金額限額，OR 觸發（0=off） |
| MT5 補 8 參數（Backup/Reconnect/SnapshotBackfill） | MT5 | 照 MT4 v1.55 預設 | **有實作**：`CalcInputFingerprint`／`ReadActiveProfile`／`TriggerTerminalSaveProfile`／`DoProfileBackup`／`CheckAndBackupProfile`／`MarketShouldBeOpenLocal`／`TriggerTerminalRestart`／`GetEnvVarEA` 八函數全落地，非空宣告 |

觸發文案標明觸發源（% 或 $ 哪條中招）；TG 帳戶級訊息帶雙限額 `(limits X% / $Y)`。

## §3 12 group 參數分佈（兩平台逐組一致）

General 4｜Display 21｜Refresh & Recording 3｜Data Filter 3｜Trade Snapshot 3｜DD Guard - Account 10｜DD Guard - Per Symbol 5｜Symbol Guard 2｜News Guard 6｜Telegram 4｜Backup & Recovery 7｜Diagnostics 0（保留空組）＝ **68**。

## §4 編譯

沙盒無 MQL 編譯器——靜態前閘全過（三態 lexer 乾淨／code 段大括號平衡 mq4 436=436、mq5 322=322／MT4 `#property strict` 在場）。**0 err/0 warn 實證待 OpenClaw 側終端編譯**（驗收項 1/2）。本輪捉獲並已修三类真编译杀手，见 §9。

## §5 .set 影響申報（驗收項 13）

- **失效範圍**：terminal .set 按參數名載入——所有用舊名（≤v1.55 命名）保存嘅 preset 喺 v1.60 下會令 66 個參數跌返預設值。repo 內無追蹤任何 .set，受影響名單＝各終端本地 preset（6DB4/A06E/725B72F2 等）。部署 v1.60 後請以新 baseline .set 為起點重設。
- **新 baseline（本交付隨附）**：`TradeDashboard_v1.60_baseline_riskOFF.set`／`TradeDashboard5_v1.60_baseline_riskOFF.set`，各 68 行全參數。
  - 風險全關（10 項）：`InpNewsGuardMode=0`、DDG Enable/AccountEnable/SymbolEnable/CloseOnHit/StopAutoTrade/AccountStopAutotrade/SymbolStopAutotrade 全 0、`InpSymbolGuardEnable=0`、`InpAutoReconnect=0`（baseline 不做無人值守重啟；AutoBackup 照 default true，純檔案複製無交易風險）。
  - **憑證衛生**：`InpTelegramChatId=` 空（源碼 default 帶真實 chat ID，已清洗；token 檔名非秘密保留）。符合「永不 commit 憑證」鐵律。

## §6 兩平台 Gain 定義差異（驗收項附帶申報）

| 平台 | Gain 定義 | 面板註解 |
|---|---|---|
| MT4 | 公式重算：由持倉價格計 profit+swap+commission | `Gain = formula-recomputed from prices`（TAM2 行） |
| MT5 | 券商真實值：`DEAL_PROFIT + DEAL_SWAP + DEAL_COMMISSION` | `Gain = broker-true P/L (profit+swap+comm)`（TAM2 行） |

MT5 `CalcTradePnl()` 零呼叫死碼已刪（1230 §3.4）。兩數在 swap/commission 計法不同嘅券商下可以有細微差異——屬定義差異，唔係 bug。

## §7 netting 必修落地（1245 審查結論，MT5）

1. `t_lots/t_profit/t_swap/t_commission` 由 upsert `=` 覆寫改 **`+=` 聚合**；`t_calcPnl` 同步重算。
2. **posId×dealTicket 去重**：`DealSeen()`/`MarkDealSeen()` 排序 ulong 陣列二元搜尋集合。
3. **持久化**：`TD_<acct>_seen.bin`；sync 尾 `SaveSeenSet()`，重啟／帳號切換 `LoadSeenSet()`——斷電重試優先於永久漏計。
4. **v1.60 遷移**：無 seen 檔＋有舊 store → 置零重建；空掃描與帳號切換兩分支 `MIGRATION DEFERRED`（保舊檔重試，防雙計）。
5. **兩護欄**：no-shrink（現有行不刪）＋`MAX_TRADES 12000` cap 留最新。
6. MT4 hedging 語義不變：`t_lots[idx] = OrderLots()` 逐 ticket 一行，無聚合需求（對照註記於 verify X1）。

## §8 13 驗收項對照（詳細輸出＝`verify_v160_output.txt`）

| # | 項目 | 狀態 | 證據 |
|---|---|---|---|
| 1 | MT4 編譯 0 err | STATIC-PASS | lexer/braces/strict 乾淨；0-err 待 OpenClaw 終端 |
| 2 | MT5 編譯 0 err | STATIC-PASS | 同上 |
| 3 | 版本四處鎖步 1.60 | PASS | property/description/STARTED banner；code+string 段零 `1.5x` 殘留 |
| 4 | input 數 68 | PASS | 兩平台 68=68 |
| 5 | input group 12 | PASS | 固定序逐組一致 |
| 6 | 零假分隔 | PASS | `input string ___` ×0 |
| 7 | 全 input 有 comment | PASS | 68/68 |
| 8 | 參數名一致性 | PASS | 逐名逐序逐組逐型別一致；default 唯一差異＝§10 申報項 |
| 9 | MT4 group 顯示 | OPENCLAW-SIDE | 靜態前置已備（group 語法×12＋strict）；部署後截輸入參數視窗圖 |
| 10 | MT5 group 顯示 | OPENCLAW-SIDE | 同上 |
| 11 | DD Money 觸發 | PASS | 帳戶+品種 OR 條件、trig 文案標觸發源、TG 雙限額、peak ratchet 無條件先行且只升不降、顯示 clamp≥0、per-symbol 分母 `DDG_Base()`、peak=0 分支消失 |
| 12 | 補齊 8 參數有實作 | PASS | 8/8 宣告＋body 引用＋8 實作函數 |
| 13 | .set 影響申報 | PASS | §5；baseline 68/68 對名全中＋風險 10 開關全 0＋TG ID 已清 |

附加行：X1 netting 修法靜態全錨點 PASS；X2 Gain 註解兩平台在場 PASS。**verify_v160 exit 0。**

## §9 本輪捉獲並修復嘅三個真編譯殺手（機器閘進化記錄）

1. **S6c TG 字串斷裂（MT4）**：OR 限額三元改寫時食咗原字串開引號，`\n⚡ Action` 落入 code 段——brace balance 對 string cascade 唔敏感，21/21 自檢捉唔到。修復＝`+ "` 重接；**新閘**：TD10 #2 L1（lexer 終態、code 段禁 `\`、string 段禁裸換行）。
2. **新增參數缺分號（兩平台）**：block builder 對 10 個新增參數寫出 `= false // cmt`（MAP66 舊參數因源碼 default 帶 `;` 而僥倖合規）。修復＝default 規範化統一重發 `;`；**新閘**：TD10 #2 S1＋rename 自檢第 9 項。
3. **TAM2 Gain 註解回歸（MT4）**：該行係上輪手動補落 final、未入 surgery 源頭，重跑即失。修復＝入 `mt4_surgery.py` S8c＋自檢新增 "TAM2 Gain note" 行——教訓：**一切修改必須落管道源頭，唔准手改產物**。

## §10 已知差異申報（超出凍結範圍，唔自行改，請 OpenClaw 裁）

`InpDefaultView` 預設值：MT4=1（Day，v1.52 FIX-TD3 改）vs MT5=0（Hour，v1.50 基底）。屬兩平台唯一 default 分叉；已入 parity 工具 documented exception 名單。要對齊嘅話屬一行改動，建議併 v1.61。

## §11 FIX-TD10 規範工具三件（`tools/`）

| 工具 | 用途 | 本輪結果 |
|---|---|---|
| `rename_inputs.py` | 66 表改名＋12 group 重建＋自檢 9 項 | 雙平台 ALL PASS（244/182 renames） |
| `check_input_standard.py` | 命名/結構/註解/lexer 十三閘（L1/S1 為本輪新閘） | 兩平台 13/13、12/12 PASS |
| `check_param_parity.py` | 兩平台逐名逐序逐組逐型別（+default 例外名單） | PASS 68=68 |

三工具可獨立跑任何 TD 源碼（`--help` 見用法）；`rename_report.txt` 為 #1 輸出。
