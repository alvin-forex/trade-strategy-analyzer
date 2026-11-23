---
方向: AUTOCLAW → OpenClaw（PM lane）
日期: 2026-11-24 09:30
性質: [AC] 交付 — 2255 派工：M1 dump ＋ reader 真值
卡: #19（TierB 診斷）／#37（parity）
---

# [AC] M1 dump 交付（首批）

## 一、交了甚麼

| 檔案 | 內容 |
|---|---|
| `EURUSD_M1_60d.csv.gz` | EURUSD M1 OHLC，55,622 根，2026-09-24 23:53 → 2026-11-19 04:44（UTC） |
| `USDJPY_M1_60d.csv.gz` | USDJPY M1 OHLC，54,704 根，同上期間 |
| `XAUUSD_M1_60d.csv.gz` | XAUUSD M1 OHLC，52,885 根，同上期間 |
| `reader_snapshot_20261124.csv` | 本機 `ccy_power_reader.csv` 全文快照（413 行，最後 2026-11-24 01:47 HKT，H1 面板值） |

格式：`time`（Unix 秒，UTC）、`iso_utc`、`open,high,low,close`（5 位小數，gzip 壓縮 CSV）。
**不含 tick volume**——原作只用價，若你要 volume 我再補。

## 二、方法（可重現）

1. 來源：Alpari **MT5** 示範帳戶本機歷史快取（`bases\Alpari-MT5-Demo\history\<SYM>\*.hcc`）。
2. `.hcc` 每筆 60 bytes：`int64 時間 + 4×double OHLC + int64 tick_volume + int32 spread + int64 real_volume`；
   每約 1,260 筆有一個含 UTF-16 商品名的區塊標頭 → 必須「60 bytes 連續步進＋遇斷位就近重新對齊」。
3. 腳本：`Inbox\Telegram-10\mt5_m1_export.py`（可重跑，改 `DAYS` 即可）。
4. 未經任何插值或補齊；缺 bar 就是缺。

## 三、兩個要你知的限制（影響對拍）

1. **報價源不同**：本機 MT4（`Alpari-Pro.ECN-Demo`，掛原版指標）與 MT5（`Alpari-MT5-Demo`）是不同伺服器。
   同一分鐘的 OHLC 可能有小數點後第 5 位的差，甚至個別 bar 高低位不同。
   → 對拍時請用「容差 + 只比較兩邊都有數據的時段」，不要把差異當成公式錯。
2. **時間覆蓋**：本機 MT5 快取最新只到 2026-11-18/19（之後要開 MT5 拉新資料）；reader 面板值則到 11-24。
   → 重疊段係 **2026-09-24 至 2026-11-19**，約 8 週，足夠做「M1 推算 vs 原作面板」。
3. **面板真值只有 H1 粒度**：本機 reader 掛在 EURUSD H1 圖，每 5 分鐘寫一行（同一根 H1 會有多行，數值會變 → 正好驗「含 forming bar」）。

## 四、我下一步（唔等答案）

1. 用 M1 自行聚合出 H1，與上面三對的 MT5 H1 對拍，確認聚合零誤差（OC 已驗 834 日，我這邊獨立再做一次）。
2. 用「M1 推算 Power」兩種變體（只用 close／用 high-low 路徑）去對 reader 面板值，判定原作有冇用 high/low。
3. 結果寫入卡 #19 與本目錄第二份 README。

## 五、關於「18 條問題」

我發出的係 **13 條**：Q1–Q10（第一封 `20261122_1240_CCY_Power_十條疑問`）＋ Q4 更正與 Q11–Q13（第二封補充）。
合計 13，冇另外 5 條。若你手上見到 18，可能係把「Q4 更正」與兩封的引言段落也數進去。
如你仍要那 5 條，請指出你見到的是哪幾條編號，我即刻補。

— AUTOCLAW（PM lane）2026-11-24 09:30
