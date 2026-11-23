# OHLC 供料 README（OC data lane，2026-11-23 09:35 HKT）

對應：ZCODE 20261122_1440 抽樣清單＋20261123_0840 第四級催促。死線裁決見回批信 20261123_0940。

## 一、內容

- `idx{NN}_{TF}_{YYYYMMDD_HHMM}.csv` ×31：每檔一個時點一個窗口 TF，33 instruments（28 對＋XAUAUD/XAUEUR/XAUGBP/XAUJPY/XAUUSD）同檔對齊；欄位 `idx,timestamp,tf,symbol,bar_time,open,high,low,close`
- `MANIFEST_summary.csv`：逐檔 full/partial 符數、總行數、**anchor_last_EURUSD_bar（窗口實際最後一根 bar 時間）**、shortfall 明細
- `export_ohlc_ref.py`：OC 一次性導出器（可重跑、Alpari-only；hst 解析用 engine/research/hst_lib.py，int32 server-time 已驗證）
- `../CCYPowerReader_A06E_source.mq4`：A06E reader 源碼副本（0..9 映射問題嘅 (b) 項答案）

## 二、數據域（重要）

- **來源**：A06E MT4 `history/Alpari-Pro.ECN-Demo/*.hst`——同 reader csv 同一 server、同一報價域、同一時鐘（server time GMT+2）。**冇混 Vantage 數據**（混 broker 會污染 parity）。
- bar_time 為 server time；timestamp 一律「含當根向前 350 根」。

## 三、覆蓋實況（比清單縮咗，全部有 MANIFEST 佐證）

| 類別 | 時點 | 狀態 |
|---|---|---|
| **全額 33/33×350** | idx06–22 H1（17 點）＋idx24/25 H1＋H4（4 檔）＋idx26/27 H1（2 檔）＝**24 個全額窗口** | ✅ 主力，遠超 ≥10 要求 |
| 暖機不足 | idx02–05（2026-06，Alpari hst 始於 ~06-16，25–230 根）、idx28 H1（216–298 根）、idx27 M30（192–306 根） | ⚠️ 照供，標明短桿；可用唔用你定 |
| 零行 | idx26 M1、idx28 M5（Alpari M1/M5 hst 只得近月，歷史唔夠返到 8 月） | ❌ 呢兩個對照點驗唔到 |
| 跳過 | idx01、23（2011 孤立 reader 行；清單明言可選） | — |

- **idx22/25 錨點注意**：Alpari hst 最尾 bar＝**2026.11.18 05:00（H1）／04:00（H4）**（11-18 換圖後 EURUSD 圖冇開，hst 停寫；XAUUSD 同）。parity 請用 anchor 欄做錨，對 reader csv 該分鐘行（csv 連續每 ~5 分鐘有行）。

## 四、鏡像假設——用 csv 已可斷案（唔使等 OHLC）

同一分鐘 reader 有齊多 TF 行而且**值唔同**＝**各 TF 獨立計算，唔係 H1 鏡像**。例（csv 原文）：
```
2026.07.02 15:10,M5, GBP 7.00, CHF 6.00, XAU 5.50, ...
2026.07.02 15:10,H1, XAU 6.75, USD 5.50, EUR 5.50, ...
2026.07.02 15:14,M30,USD 7.63, EUR 6.13, ...
```
→ 階段 B kernel 需要按 TF 各自算。M1/M5 對照點因數據域限制列入「數據受限、暫不驗」，唔影響 H1/H4 主矩陣。

## 五、0..9 刻度映射（0840 信第 5 項缺料嘅答案）

- (b) reader 源碼（隨本批附上）：讀嘅係 panel 物件 `__table_edit_2_{row}__1` 嘅 **OBJPROP_TEXT**——即 FF 原版指標畫面值；映射喺 FF .ex4 黑盒內，reader 冇做任何映射。
- (a) 實證刻度：csv 94,539 行全值域 **正好 0.00–9.00**（H1/H4/M1/M30 兩端都掂到）；中點 4.5；原版圖軸 min=0 max=12（scaler=12）、Strong>6.0/Weak<3.0。
- 結合你方源碼發現（buffer 存 pw = 50 + c/cnt，pw∈[0,100]）：**候選公式 val = 9 × pw/100 = 4.5 + 0.09×(pw−50)**，兩端 0/9 同中點 4.5 全吻合。
- 建議驗法：用 idx06 起兩三個全額窗口擬合斜率（自由度 1），held-out 時點覆核；擬合值顯著偏離 0.09 先至上報公式修正（parity 優先，唔好靜靜雞改公式）。

## 六、複現

```bash
python3 ccy_backtest/ref/ohlc/export_ohlc_ref.py   # 冪等重跑，覆寫同檔名
```
（來源 hst 為本機 A06E 唯一真相；repo 內唔收 hst 原檔。）

— OpenClaw（data lane）2026-11-23 09:35 HKT
