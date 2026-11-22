# OHLC 抽樣清單說明（CP-BT1 階段 B——方案 A，照 OC 1345 批准）

清單檔：`ohlc_sampling_list.csv`（同目錄）｜產生：ZCODE_w 2026-11-22 14:40 HKT｜固定 seed=20261122 可重跑

## 一、抽樣概況

- **28 時點**：H1 22／H4 3／M30 1／M1 1／M5 1
- 覆蓋：csv 邊界（2011.04.14 孤立條＋2026.11.20 23:53 最尾）、主段（2026.06.12→11.20）每半月均勻 8 點、2026-06→11 每月中位 6 點、A2 缺陷觸發 2 點（XAU 排名 3→7 極端切換、1→8 最大位移）、H4 對照 3 點、多 TF 對照 3 點（M30/M1/M5，驗證 reader 多 TF 係獨立計算定 PairTF=H1 鏡像）
- 注：抽樣時發現 csv「2011.04.14 16:24」係**孤立 1 條**（2011→2026.06 之間 15 年無任何 key），判斷係 A06E 早期測試殘留——該條（idx 1／23）**屬可選**：若台方 MT4 端無 2011 年 OHLC，跳過唔影響驗收（其餘 26 點已遠超 ≥10 時點要求）。

## 二、窗口長度 N＝350 根（統一，每時點相同）

**計法（一句）**：N = `Lookback_Bars`(300，§4 全量重算深度，見 §8-A4) ＋ max(`RSI_Period`,`ATR_Period`)(14，指標暖機) ＋ `Slope_Lookback`(10，斜率回歸) ＋ 26 根緩衝 ＝ **350**。

- **時間框架**：照白皮書 §4 `PairTF = PERIOD_H1`（全部計算固定用 H1，與圖表時框無關）——**主窗口請供 H1 350 根**（每時點：該 timestamp（含）向前 350 根 H1 bar，欄位 OHLC＋bar 時間）。
- H4/M30/M1/M5 五個抽樣點（idx 23–28）：除 H1 主窗口外，請加供**該 TF 350 根**對照窗口（用於驗證 reader 多 TF 值來源；若 A06E 導出唔到該 TF 歷史，回報即可，我方改用備選方案）。
- 28 對＋XAUUSD 全 instrument 統一窗口（同一 timestamp 對齊導出，避免跨 instrument 時間錯位）。

## 三、供料格式建議（台方 1345 信承諾清單到後 2 小時內供齊）

- 路徑：`ccy_backtest/ref/ohlc/`（新建）
- 命名：`{INSTRUMENT}_{TF}_{N}bars.csv`（例：`EURUSD_H1_350bars.csv`）或每時點一檔 `{TF}_{timestamp}_{INSTRUMENT}.csv` 均可——**以台方導出方便為準**，我方 parser 遷就台方格式，唔使遷就我方。
- 欄位最低要求：`date/time,open,high,low,close`（MT4 history export 原生格式可直接用）。
- 供齊後 notify 通知＋commit 訊息申報，我方即刻開跑 parity 誤差矩陣。

## 四、驗收目標（不變）

誤差矩陣 ≥10 timestamp × 9 幣 ＋ AVG，目標貼近零；死線 11-23 18:00 維持。

— ZCODE_w（平台 lane）2026-11-22 14:40 HKT
