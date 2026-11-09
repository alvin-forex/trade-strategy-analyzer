> ✅ 已處理 2026-11-09 by OpenClaw（補章——r2 驗收 8.5/9 過＋r3 一項 2305，見 from_openclaw 對應檔）

# TD v1.63r2 兩平台交付 REPORT — 2026-11-07 21:55 HKT

**範圍**：1915（五鈕右移＋CLOSE ALL＋ASCII）＋1925（UNLOCK/LOCK 動態標籤）＋2010（註解清零＋WhitelistUrl＋BotToken 直輸）＋1850（兩候裁落地）＋**2130 §八（分組間隔）＋§九（0/空值 () 註釋）**——九項一鑊熟。
**本版取代 2135 交付**（七項版；該版保留作審計軌跡）。基準不變：MT4 = v1.60 final（89d8305a…）｜MT5 = v1.62 final（53eebc1a…）。

## 一、九項落地對照

| # | 項（來源） | MT4 | MT5 | 實現 |
|---|---|---|---|---|
| 1 | 五鈕右對齊（1915 §一） | ✅ | ✅ | `bx0 = x + w − 6·scale − 250·scale`——五鈕欄右貼面板邊，同 pager 對齊 |
| 2 | [CLOSE ALL] 搬表頭＋ASCII（1915 §二） | ✅ | ✅ | 表頭 UNLOCK 右邊（`bx0+68·scale`／90 闊）；`[ CLOSE ALL ]` 純 ASCII；LAST 留表尾；雙按＋30s 冷卻不變 |
| 3 | ARM→UNLOCK/LOCK（1925） | ✅ | ✅ | 未解鎖=`UNLOCK`（開 60s）；倒數=`LOCK 45s`（撳=即刻重鎖）；BGA 沿用 |
| 4 | 兩候裁（1850） | ✅ | ✅ | InpDefaultView 統一 0＋TG chat ID 源碼 default 清空 |
| 5 | input 註解版本號清零（2010 §一） | ✅ 6 處 | ✅ 4 處 | 兩平台掃描清零；R2 企立規閘 |
| 6 | InpTelegramWhitelistUrl（2010 §二） | ✅ | ✅ | 顯示用，Telegram group 尾 |
| 7 | InpTelegramBotToken（2010 §三） | ✅ | ✅ | 空=用檔案；非空=直用；baseline 永遠空 |
| **8** | **分組間隔 spacer（2130 §八）** | ✅ 12 行 | ✅ 12 行 | 每個 group 邊界一行標準化 spacer：**MT4 `input string SpacerNN`／MT5 `sinput string SpacerNN`**（MQL4 無 sinput——string 參數本來就唔會被優化器掃，效果等價；**兩平台都加**，觀感一致），值空、註釋 `─`×32 統一字符；**唔計入 70 參數總數**（parity 對账排除）；假分隔 `___`（v1.55 樣式）照舊封禁 |
| **9** | **0/空值 () 註釋（2130 §九）** | ✅ 12 參數全覆蓋 | ✅ 12 參數全覆蓋 | 兩平台各 12 個 0/0.0/空預設參數，註釋全部帶「(...)」值意義結尾或 0=X 模式列舉；修正 6 處（InpReportStart→「empty = from beginning」照信、InpTelegramChatId 補 empty 意義、FilterSymbol/FilterComment/DdgSymbolList/BackupFolder 格式統一「empty = X」） |

## 二、v1.63 輸入結構（2130 §八規範修訂後）

- **70 參數＋12 spacer**（MT4 82 行 input 宣告／MT5 70 input＋12 sinput），12 groups 不變。
- spacer 完整格式：`input string Spacer01 = ""; // ────────────────────────────────`（F7 對話框左欄顯示註釋=分隔線，右欄空值）。
- **F1 閘改版**（check_input_standard_r2）：`___` 假分隔繼續封禁＋新增 SP1（數目=組數）/SP2（只出現喺組邊界，下一行必係 group）/SP3（格式統一）；G2「首 group 前無參數」改為 spacer 豁免。
- **parity r2**：Spacer* 排除對账（P1-P5 淨比 70 參數）。

## 三、表頭新幾何（兩平台一致，同 2135 版）

```
SYMBOL  Float $  DD now %  MaxDD %  MaxDD $   [UNLOCK ][ CLOSE ALL ]   1/3 [<][>]
 x+8     x+100    x+175     x+250    x+320     ^bx0=x+w−256·scale       ^x+w−96/−64/−32
```
BGC 右緣 x+w−98·scale 唔疊 pager 文字（x+w−96·scale 起），全闊度成立。

## 四、發現與根治（4 條，同 2135 版）

1. **CheckTabCmd 根治（1915 §五）**：MT5 歷代完全冇呢個函數——v1.63 補移植（read-once 語義照 MT4 v1.51 修復版；OnTick+OnTimer 雙呼叫；snap 截圖）。
2. 2010 話「MT5 乾淨」實測有 4 個版本號註解——已清。
3. 1850 兩平台 default 寫反（實況 MT4=1、MT5=0）；統一 0 不變。
4. MT5 STARTED print 版號 v1.60 滯留兩版——已修 1.63。

## 五、企立規（verify 閘強制，累計 5 條）

| # | 規則 | 來源 | 強制點 |
|---|---|---|---|
| R1 | 按鈕文字一律純 ASCII | 1915 §二 | verify V9 |
| R2 | input 註解永遠唔帶版本號／工單號 | 2010 §一 | verify V3 |
| R3 | BotToken 直輸＝明文暴露面（同檔案）；baseline .set 永遠空 | 2010 §三 | verify V17 |
| **R4** | **spacer 只出現喺組邊界、格式統一、數目=組數、唔計入參數總數** | 2130 §八 | verify V19＋TD10-r2 SP1-3 |
| **R5** | **0/0.0/空預設參數（值=唔用/自動/全部）註釋必須以「(...)」寫明值意義** | 2130 §九 | verify V20 |

## 六、機器驗證（全綠）

- **verify_v163.py r2：38 閘全 PASS、exit 0**（V1-V20；輸出 `verify_v163_output.txt`）
- **TD10-r2 工具**：check_input_standard_r2 MT4 **16/16**（L1/L2/N1/N2/C1/F1/SP1/SP2/SP3/S1/G1/G2/P1/U1/T1/B1）＋MT5 **15/15**；check_param_parity_r2 **PASS**（70 vs 70＋兩側 12 spacers）
- 手術：MT4 21 錨定（20 rep＋1 程式化 spacer 批次）＋34 自檢；MT5 26 錨定＋36 自檢；期望值修正 3 輪全係檢查器 bug（產品碼零回退）
- diff：MT4 v1.60→v1.63r2 共 245 行；MT5 v1.62→v1.63r2 共 280 行
- md5：MT4 final `3b5920b5cf5abd6fef5401bd2cd81db8`｜MT5 final `62867f683939f84ba5c7c6dd7a24f989`

## 七、baseline .set ×2（risk OFF）

82 行＝**70 參數＋12 spacer**。68 個 legacy 參數值與 v1.60 已批基準**逐名比對零差異**（機器對账）；delta＝View=0（1850）＋2 新參數（WhitelistUrl 帶 URL／BotToken 空）＋12 行 spacer。風險 10 開關全 0、chat ID 空、token 空。

## 八、OpenClaw 側驗收（等態）

1. 兩平台真機編譯 0/0（v1.62 已 0/0；r2 淨增 spacer 行＋註釋改動，預期全綠——**MT5 sinput 係標準 MQL5 關鍵字，MT4 `input group`/plain input 均為既有已編譯構造**）。
2. F7 觀感截圖：分組間隔（12 條 ──── 分隔線）＋DDGuard 表頭（UNLOCK/[CLOSE ALL]/pager 右對齊）＋LOCK 倒數。
3. .set 沿用：70 參數冇改名（68+2 新增），舊 .set 可直接載入；新 .set（82 行）已隨信。

## 九、範圍外備註

- 批 1 四頁 NAV 重做＋8 截圖解鎖態：下一工作鐘（2100 批示排期）。
- AngelGold .set（MagicNumber=20260920）11-09 同場。
- D 族 98 頁統一深色：隨批 2/4 時段，經中介制呈批。
