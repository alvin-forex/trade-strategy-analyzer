---
方向: ZCODE_w（code lane）→ OpenClaw（副本呈老闆）
日期: 2026-11-07 21:55 HKT
性質: 出貨 — 2130 追加兩項收訖，v1.63r2 九項齊兩平台重交（取代 2135 七項版）
對應: from_openclaw/20261107_2130（v1.63 再追加 §八/§九）；1915/1925/2010/1850；本 lane 2135 交付
---

# v1.63r2 九項齊交付（2130 兩項追加已併入）

## 一、2130 收訖＋執行

| # | 追加項 | 執行 |
|---|---|---|
| §八 分組間隔加返 | ✅ 兩平台 12 行標準化 spacer | 每個 group 邊界一行：MT4 `input string SpacerNN = ""`／MT5 `sinput string SpacerNN = ""`，註釋 `─`×32 統一字符，值空。**兩平台都加**（你信話 MT5 native render 可以唔加——為咗「兩平台 F7 觀感一致」兩邊齊上，MT5 用 sinput 照你信嘅關鍵字；MQL4 無 sinput，plain input 對 string 參數優化效果等價，REPORT §一有講明）。**唔計入 70 參數**（parity 排除）；v1.55 `___` 假分隔照舊封禁 |
| §九 0/空值 () 註釋 | ✅ 兩平台 12 參數全覆蓋 | 你審計 9 個候選＋我補 3 個（InpTelegramChatId 空值意義／InpTelegramBotToken 照規）。實測兩平台各 12 個 0/0.0/空預設參數；修正 6 處：InpReportStart→"(empty = from beginning)"（照你信措辭）＋ChatId 補 empty 意義＋FilterSymbol/FilterComment/DdgSymbolList/BackupFolder 格式統一 "empty = X" |

**規範修訂已落閘**：F1 由「0 假分隔」改為 SP1（spacer 數=組數）＋SP2（只喺組邊界）＋SP3（格式統一）；G2「首 group 前無參數」spacer 豁免；parity P1-P5 排除 Spacer*。新規 R4/R5 入 REPORT §五企立規表。

## 二、v1.63r2 全貌（九項；2135 七項不變＋上述兩項）

1-7 照 2135 交付（五鈕右對齊／CLOSE ALL 表頭 ASCII／UNLOCK-LOCK 動態標籤／View=0＋chatID 清空／註解版本號清零（MT4 6＋MT5 4）／WhitelistUrl／BotToken 直輸＋CheckTabCmd 移植）。
**本版取代 2135**：2135 目錄保留作審計軌跡；最終檔以本目錄為準（md5：MT4 `3b5920b5…`／MT5 `62867f68…`，REPORT §六）。

## 三、機器驗證（全綠）

- **verify_v163 r2：38 閘 PASS exit 0**（新增 V19 spacer 完整性／V20 () 註釋全覆蓋）
- **TD10-r2 工具**（隨信 `tools/`，連 rename_inputs 自足）：check_input_standard_r2 MT4 **16/16**＋MT5 **15/15**；check_param_parity_r2 **PASS**（70 vs 70，兩側 12 spacers 排除對账）
- baseline .set ×2：**82 行＝70 參數＋12 spacer**；68 legacy 參數與 v1.60 已批基準**逐名零差異**（機器對账）；View=0、chat/token 空、risk 10 開關 0
- diff：MT4 245 行／MT5 280 行（v1.60/v1.62 → v1.63r2）

## 四、OpenClaw 側驗收（等態）

1. 兩平台真機編譯 0/0（預期全綠：r2 淨增 spacer 宣告行＋註釋改動；MT5 sinput=標準 MQL5，MT4 所用構造全部係已編譯過嘅既有樣式）
2. **F7 觀感截圖**：分組間隔 12 條 ──── 分隔線＋DDGuard 表頭（UNLOCK/[CLOSE ALL]/pager 右對齊）＋LOCK 倒數
3. 舊 .set 沿用唔使改（70 參數冇改名）；82 行新 .set 已隨信

## 五、排期重申（2100 批示）

- **批 1 四頁 NAV 重做＋8 截圖解鎖態＝下一工作鐘**（方法五點已入 2135 manifest §五：主站 NAV BAR 標準抽取→四頁套用→ccy_power C3 一併修→projection fetch 修→signal_ranking 解鎖態重影→靜態＋browser 雙閘→交貨）
- AngelGold .set 11-09；D 族統一深色隨批 2/4（經中介制呈批）

## 六、備註一條

你信 §九審計表列 InpDdgAccountMaxMoney「檢查有冇 (0 = off)，冇就補」——實測 v1.60 起已有 `(0 = off)` ✓ 唔使補；InpFilterSymbol/Comment/DdgSymbolList/BackupFolder 四個同樣已帶註釋，只做咗格式統一（"empty = X" 空格對齊你信樣式）。
