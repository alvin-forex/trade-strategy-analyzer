> ✅ 已處理 2026-11-09 by OpenClaw（補章——v163 三追加 1915／1925／2010＋2130，r2 驗收 2305，見 from_openclaw 對應檔）

# TD v1.63 兩平台交付 REPORT — 2026-11-07 21:35 HKT

**範圍**：1915（五鈕右移＋CLOSE ALL＋ASCII）＋1925（UNLOCK/LOCK 動態標籤）＋2010（註解清零＋WhitelistUrl＋BotToken 直輸）＋1850（兩候裁落地）——七項一鑊熟，MT4 v1.60→1.63、MT5 v1.62→1.63 兩平台同步。
**基準**：MT4 = v1.60 final（89d8305a…）｜MT5 = v1.62 final（53eebc1a…，warning hotfix 後）。

## 一、七項落地對照

| # | 項（來源） | MT4 | MT5 | 實現 |
|---|---|---|---|---|
| 1 | 五鈕右對齊（1915 §一） | ✅ | ✅ | `bx0 = x + w − 6·scale − 250·scale`——五鈕欄（46 闊×5、50 pitch，總闊 246·scale）右貼面板邊，同 pager 對齊，~6·scale 右邊距；表行唔加闊 |
| 2 | [CLOSE ALL] 搬表頭＋ASCII（1915 §二） | ✅ | ✅ | 由表尾搬到表頭 UNLOCK 掣右邊（`bx0+68·scale`，90·scale 闊），標籤 `[ CLOSE ALL ]` 純 ASCII（舊 `[ CLOSE 全倉 ]` 喺 MQL OBJ_BUTTON 字型渲染失敗變 ??——根治）；LAST 行留表尾；雙按確認＋30s 冷卻語義原封不動 |
| 3 | ARM→UNLOCK/LOCK 動態標籤（1925） | ✅ | ✅ | 未解鎖顯示 `UNLOCK`（撳=開 60s 窗口）；倒數中顯示 `LOCK 45s`（撳=即刻手動重鎖，唔使等 60s——BINGO_ArmToggle 原有 toggle 語義直接對應）；對象名 BGA 沿用，60s／切 TAB 解除／雙按確認不變 |
| 4a | InpDefaultView 統一 default 0（1850） | ✅ 1→0 | ✅ 已係 0 | baseline .set 兩平台同時 0 |
| 4b | TG chat ID 源碼 default 清空（1850/2010 §四） | ✅ | ✅ | `"920593269"`→`""`；真值只經 input/.set |
| 5 | input 註解版本號清零（2010 §一） | ✅ 6 處 | ✅ 4 號 | MT4：DefaultView/SnapshotBackfillOnce/DdgAccount/DdgSymbol/SymbolGuard/NewsGuard；MT5：DdgAccount/DdgSymbol/SymbolGuard/NewsGuard（見下「發現②」） |
| 6 | InpTelegramWhitelistUrl（2010 §二） | ✅ | ✅ | `"https://api.telegram.org"`，純顯示畀用家複製入防火牆白名單，EA 唔讀佢做嘢；Telegram group 尾 |
| 7 | InpTelegramBotToken（2010 §三） | ✅ | ✅ | default `""`；非空→直接用（優先於檔案）；空→照舊讀 InpTelegramTokenFile。兩平台 token 載入點（MT4 NGDDG_Init／MT5 TG_LoadToken）同一規則 |

輸入數：68→**70**（12 groups 不變），兩平台逐名逐序逐型別逐 default 對齊（TD10 parity PASS）。

## 二、表頭新幾何（兩平台一致）

```
SYMBOL  Float $  DD now %  MaxDD %  MaxDD $   [UNLOCK ][][ CLOSE ALL ]   1/3 [<][>]
 x+8     x+100    x+175     x+250    x+320     ^bx0 = x+w−256·scale      ^x+w−96 −64 −32
                                          （64 闊）（90 闊，右緣 x+w−98·scale，唔疊 pager）
```
- 五鈕數據行同樣由 bx0 起，排尾 x+w−10·scale——右對齊錨點＝pager。
- guard tab 最小闊 620·scale（MT4 :3001／MT5 :2649）不變；最窄情況下 UNLOCK 與 MaxDD$ 欄標籤之間嘅緊度與 v1.60/v1.61 現狀相同（老闆實機 chart 闊，正常顯示全闊）。

## 三、發現與根治（4 條）

1. **MT5 tabcmd hook 根因確診＋根治（1915 §五）**：`CheckTabCmd()` 喺 MT4 有（v1.35 hook，OnTick+OnTimer 雙呼叫、read-once、snap 截圖），**MT5 歷代版本完全冇**——「MT5 tabcmd 冇反應」唔係 bug 係整個函數從未移植。v1.63 已補移植（MQL5 語法對應，read-once 語義照 MT4 v1.51 FIX-TD2 修復版：hook 檔讀後必刪、只認 well-formed `tab=`、切 TAB 解除 ARM）。
2. **2010 信「MT5 v1.62 乾淨」唔準確**：MT5 實測有 4 個 input 註解帶 v1.46/v1.47 前綴（DdgAccount/DdgSymbol/SymbolGuard/NewsGuard）——已一併清零。規則以後由 verify 閘強制（見下），唔靠人手數。
3. **1850 信兩平台 default 寫反咗**：實測 MT4=1、MT5=0（信中寫 MT4 0 vs MT5 1）。裁決「統一 0」結果不變——改嘅係 MT4 側。
4. **MT5 STARTED print 版號由 v1.60 起滯留**：v1.61/v1.62 兩次手術都冇掂到 `Print("=== TradeDashboard v1.60 (MT5) STARTED…`——v1.63 已一併修正為 1.63。

## 四、新立規（入 standing rules，verify 閘強制）

| # | 規則 | 來源 | 強制點 |
|---|---|---|---|
| R1 | **按鈕文字一律純 ASCII**（MQL OBJ_BUTTON 字型渲染 CJK 會變 ??） | 1915 §二 | verify V9：全 UpdBtn 標籤 regex 掃非 ASCII＝0 |
| R2 | **input 註解永遠唔帶版本號／工單號**（歷史留 git log 同 REPORT） | 2010 §一 | verify V3：`v[0-9]\.`/`FIX-TD`/`Q#` 掃 input 註解＝0 |
| R3 | **BotToken 直輸安全說明**：input 值會存 .chr/.set 明文——同 token 檔一樣暴露面，個人終端可接受；**baseline .set 永遠空** | 2010 §三 | verify V17 |

## 五、機器驗證

- **verify_v163.py**：34 閘全 PASS、exit 0（版號×4/70 輸入/註解衛生/幾何/標籤/lexer 三態/CheckTabCmd/netting 核心/跨平台 parity/baseline）。輸出見 `verify_v163_output.txt`。
- **TD10 工具**（v1.60 交付版）：check_input_standard MT4 **13/13**、MT5 **12/12**；check_param_parity **PASS**（70 vs 70，逐名逐序逐組逐型別逐 default）。
- **手術紀律**：MT4 20 錨定替換＋28 自檢；MT5 17 錨定替換＋32 自檢；全部錨定單次命中，期望值修正 4 輪全係檢查器 bug（產品碼零回退）。
- diff：MT4 v1.60→v1.63 共 203 行（+46/−29）；MT5 v1.62→v1.63 共 224 行（+76/−24）。
- md5：MT4 final `3b464ee31cd903995fb2279c2d877956`｜MT5 final `b828c7401f4a9fdc18f77ec4571e5d74`。

## 六、baseline .set ×2（risk OFF）

`TradeDashboard_v1.63_baseline_riskOFF.set`／`TradeDashboard5_v1.63_baseline_riskOFF.set`：70 參數全列、風險 10 開關全 0（NG/DDG 全家/SG/AutoReconnect）、TG chat ID 空、BotToken 空、WhitelistUrl 帶預設 URL（非憑證）、InpDefaultView=0。由 v1.60 已批基準機器延伸生成，順序對 final 源碼逐名核對 PASS。

## 七、OpenClaw 側驗收（等態）

1. 兩平台真機編譯 0 errors/0 warnings（預期全綠——v1.62 已 0/0，v1.63 淨增 2 input＋純幾何/標籤改動＋一個獨立 void 函數）。
2. 部署截圖：DDGuard tab 表頭（UNLOCK/[CLOSE ALL]/pager 右對齊）＋解鎖態 LOCK 倒數＋五鈕右貼邊。
3. .set 沿用宣告：v1.63 輸入冇改名（70=68+2 新增），舊 .set 可直接載入，新增兩項自動取 default。

## 八、範圍外備註

- v1.63 未郁 MT5 內聯 CLOSE 板嘅 BGB_ 五鈕語義（1915 只改位置）；AngelGold .set（MagicNumber=20260920）照 1850 裁決排 11-09 同場交付。
