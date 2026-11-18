# AC lane 交付：CCY Power TierB 樣本（部分完成＋阻塞報告）

- lane：autoclaw（AC）｜負責：AUTOCLAW｜日期：2026-11-18 20:1x HKT
- 對應卡：#19（openclaw lane）／派工：20261118_1107_派工_AC本機跑TierB＋PowerHistory解碼

## 已交付

| 檔案 | 內容 |
|---|---|
| `ccyprobe_bars.csv` | EURUSD H1 OHLC（14 根 bar＋tick_volume），持續追加中 |
| `ccyprobe_panel.csv` | 每 60 秒一行：server_time／tf_min／period／chart_symbol／bid／ask／spread_pt／九貨幣值（現全為 -1.0000＝NOT_FOUND）／found_mask |
| `ccyprobe_candidates.txt` | 每輪覆寫：objects_total ＋ LABEL/TEXT object 清單 |

（`ccyprobe_objects.txt` 未產生——probe 邏輯上僅在有 object 時寫。）

## 執行環境（如實申報，與派工單有一項偏差）

- 派工單指定 MT4-2（Alpari-Pro.ECN-Demo 252031466）。**MT4-2 唔喺 AC 本機**（全機搜查：無 A06E6395... 資料夾、無 Alpari 帳號、無 reader csv——該 terminal 應該喺 OC 側 WSL mount 嗰部機）。
- AC 實際用本機 VantageMarkets-Live 9（帳號 17231558）terminal：EURUSD H1 圖＋原版 `CCY Power Indicator v1.00`（displayMode=0、TF_1=60、Period_1=10、showPanelTable=1）＋ `CcyPower_TierB_Probe`（InpTF=60、InpPeriod=10、InpBars=14、InpPollSeconds=60、InpEveryPoll=true），compile 0 errors 0 warnings。
- panel vs bars 為同圖同源對比，診斷方法不受 broker 影響；但如需與 MT4-2/Alpari 歷史數值直接對照，則唔可混用。

## 掛載方法（供 ZCODE/OC 參考，已驗證可行）

- 原版指標：profile `default\chart01.chr` 內 `<indicator><name>Custom Indicator</name><expert><name>CCY Power Indicator v1.00</name>...` → journal 確認 `loaded successfully`。
- TierB probe（EA 型）：**唔可以**放 `<indicator>` block（MT4 會去 `MQL4\indicators\` 搵，並報 `Expert ... it is not a custom indicator and will be removed`）。正確做法：喺 `<chart>` 層級直接放 `<expert>name=CcyPower_TierB_Probe ... </expert>` → journal `Expert CcyPower_TierB_Probe EURUSD,H1: loaded successfully`＋inputs 全部生效。

## 阻塞（卡邊、等乜）

**panel 全部 NOT_FOUND／objects_total = 0**，且 MQL4 journal 出現：

- `CCY Power Indicator v1.00 EURUSD,H1: initialized` 後：
- `GEMS Initialization: Retry 1 Offline User[""]`（Retry 1 之後再無進展；Martingale Scanner 同樣報 GEMS Offline）

判定：原版指標被 **Forex Forest GEMS 授權系統**擋住（Offline User，未完成初始化），panel/objects 從未繪出。呢個唔係 input 錯、唔係數據缺（bars 正常、多 symbol chart 已開齊 27 張餵數據）。

**等乜**：
1. 老闆喺本機 terminal 對 CCY Power 指標做一次 GEMS 登入／授權（GUI 動作，AC 做唔到）；或者
2. OC 用 MT4-2（你哋嗰邊 GEMS 係過咗嘅）跑 panel 部分交 4 檔；或者
3. ZCODE 改用 `iCustom` buffer 路線（R12 toolkit 嘅 `CcyProbe_Original.mq4` 已證明 iCustom 可讀原版 buffer 0-7），繞過 object 依賴。

probe 喺本機繼續行緊（每 60 秒輪詢），GEMS 一過，panel 值會即刻出現，屆時補交。

— AUTOCLAW（AC lane）
