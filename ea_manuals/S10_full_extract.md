好的，這就為您提取頁面中的文字。

### Page 1

- Forex Forest
- S10
- Professional Version
- Expert Advisor
- S10 PRO
- V4.00
- V5.00

### Page 2

EFFECTIVE STC FILTER

### Page 3

S10 COURSE

#### Effective STC Filter (原理)

**Stochastic Oscillator(隨機指標/KDJ指標)**

*   通過一個特定的周期內出現過的
*   最高價、最低價及最後一個計算周期的收盤價及
*   這三者之間的比例關係，
*   來計算最後一個計算周期的未成熟隨機值 RSV，
*   然後根據平滑移動平均線的方法來計算 K值、D值與J值 (Slowing Value)，並繪成曲線圖

`RSV = (Cn - Ln) / (Hn - Ln) x 100`

> Cn 為第 n日收盤價; Ln 為 n日內的最低價; Hn 為 n日內的最高價。

`Kt = 2/3 * Kt-1 + 1/3 * RSVt`

> Kt 和 RSVt 分別表示某一天的K值和 RSV值;
> Kt-1 表示前一天的 K值, 若無前一天的 K值, 則用 50來代替。

`Dt = 2/3 * Dt-1 + 1/3 * Kt`

> Dt 和 Kt分別表示當天的D值和K值;
> Dt-1 表示前一天的 D值, 若無前一天的 D值, 則用 50來代替。

`Jt = 3Kt - 2Dt`

Equation Source: https://baike.baidu.com/item/KDJ%E6%8C%87%E6%A0%87/6328421?fromtitle=kdj&fromid=3423560

### Page 4

S10 COURSE

#### Effective STC Filter (原理)

**Stochastic Oscillator(隨機指標/KDJ指標)**

**KDJ指標、RSI指標有什麼不同呢?**

*   **KDJ指標(隨機指標):** 呈現「最新股價的相對高低位置」，估股價目前處於相對高點或低點。
*   **RSI指標(相對強弱指標):** 呈現「一段時間內股價買盤與賣盤力量強弱比例」，評估力量是相對平衡還是懸殊。

**KDJ數值越高**
代表 收盤價 接近最近幾天的最高價;

**KDJ數值越低**
代表 收盤價 接近最近幾天的最低價。

*   STC > 80 超買
*   STC < 20 超賣

| 參數 | 數值 |
| :--- | :--- |
| Effective STC Sell Below | 100.0 |
| Effective STC Sell Above | 80.0 |
| Effective STC Buy Below | 20.0 |
| Effective STC Buy Above | 0.0 |

Info Source: https://mql01.com/what-is-kd-indicator/

### Page 5

S10 COURSE

#### Effective STC Filter-Parameter List

| 參數 | 預設值 | 可選值 |
| :--- | :--- | :--- |
| **=== ENTRY SYSTEM - ADDITION ===** | | |
| **=== Effective STC Filter ===** | | |
| Use Effective Stochastic | On | On, Off |
| Effective STC Timeframe | 1 Hour | current, 1 Minute, 5 Minutes, 15 Minutes, 30 Minutes, 1 Hour, 4 Hours, 1 Day, 1 Week, 1 Month |
| Effective STC K-line Period | 5 | |
| Effective STC D-line Period | 3 | |
| Effective STC Slowing Value | 3 | |
| Effective STC MA Method | Simple | Simple, Exponential, Smoothed, Linear weighted |
| Effective STC Price Field | Low/High | Low/High, Close/Close |
| Effective STC Sell Below | 100.0 | |
| Effective STC Sell Above | 80.0 | |
| Effective STC Buy Below | 20.0 | |
| Effective STC Buy Above | 0.0 |
好的，這就為您提取 S10 EA 說明書 `page_06.png` 至 `page_10.png` 的所有可見文字。

### **Page_06.png**

#### **Effective STC Filter-MA Method**

[各種MA的優點與缺點]

| 移動平均線的類型 | 優點 (Open) | 缺點 (High) |
| :--- | :--- | :--- |
| **SMA (簡單移動平均線)** | 計算方法的重點不擺在價格上, 因此簡單明瞭, 容易實現原本的平滑的目的。 | 對價格變動的跟隨速度較鈍。到了隔天, 最早的資料已經不見了, 因此若該數據很大, 影響就很大。 |
| **EMA (指數平滑移動平均線)** | 對價格變動的跟隨性比SMA好。計算時, 舊數據不會失去。因此計算結果可視為涵蓋到所有數據。累積極加權平均的重點放在最近的數據上。 | 在跟隨性、反應度良好的另一面, 也較容易發生假訊號(Fakesouts)。關於計算的起點若不同, 算出的結果也不一樣。 |
| **SMMA (平滑移動平均線)** | 與EMA相同 | 與EMA相同 |
| **LWMA (線性加權移動平均線)** | 比重放在最近的數據較大, 資料越舊比重依序越小。因此對價格變動的漲跌效果更為敏銳。 | 因過度敏感高, 因此發生假訊號的機率較高。與移動平均的本質(平均化)有若干落差。須能善用該性質。 |

*   **MA** = Moving Average
*   **Simple** – SMA
*   **Exponential** – EMA
*   **Smoothed** – SMMA
*   **Linear Weighted** – LWMA

MA Line explanation Source:
https://www.oanda.com/bvi-ft/lab-education/technical_analysis/moving_average_comparison/

---

### **Page_07.png**

#### **Effective STC filter - Entry MACD off + STC on**

**參數設定:**
*   **Use Effective Stochastic:** On
*   **Effective STC Timeframe:** 1 Hour
*   **Effective STC K-line Period:** 5
*   **Effective STC D-line Period:** 3
*   **Effective STC Slowing Value:** 3
*   **Effective STC MA Method:** Simple
*   **Effective STC Price Field:** Low/High
*   **Effective STC Sell Below:** 100.0
*   **Effective STC Sell Above:** 80.0
*   **Effective STC Buy Below:** 20.0
*   **Effective STC Buy Above:** 0.0

**圖表標示:**
*   **80-100 Sell Zone**
*   **0-20 Buy Zone**

---

### **Page_08.png**

#### **Effective STC Filter - Entry MACD off + STC on(Buy)**

*   ***MACD apply on ALL orders while**
*   ***STC apply on 1st order only**

**圖表標示:**
*   **MACD buy signal**
*   **STC buy zone**
*   **銀影線 高過 紅線** Buy Zone
*   **紅線 高過 銀影線** Sell Zone
*   **80-100 Sell Zone**
*   **0-20 Buy Zone**

---

### **Page_09.png**

#### **Effective STC Filter - Entry MACD off + STC on(Sell)**

*   ***MACD apply on ALL orders while**
*   ***STC apply on 1st order only**

**圖表標示:**
*   **MACD sell signal**
*   **STC sell zone**
*   **銀影線 高過 紅線** Buy Zone
*   **紅線 高過 銀影線** Sell Zone
*   **80-100 Sell Zone**
*   **0-20 Buy Zone**

---

### **Page_10.png**

#### **Effective STC Filter-Case Study 疑問**

**疑問:**
點解 STC 睇圖未到20都開 buy 單?
S10 EA Manual Pages Text Extraction:

好的，這是從你指定的頁面中提取的文字。

### page_11.png

**Effective STC Filter-Case Study 答案**

開 visual mode 睇！
Effective STC 右邊set shift
即使張圖個close price計出黎未到20
只要曾經低過20
都會觸發STC開buy單

跌低過20

**Journal Log**
| Time | Message |
| --- | --- |
| 2022.03.16 16:47:28.... | 2022.02.01 04:00:00 S10 v3.00 AUDUSD,H1: Entry 1 MACD (MAIN): -0.00208, Entry 1 MACD (SIGNAL): -0.00353, **Effective STC: 19.49** |
| 2022.03.16 16:47:28.... | 2022.02.01 04:00:00 S10 v3.00 AUDUSD,H1: open #1 buy 0.10 AUDUSD at 0.70625 ok |
| 2022.03.16 16:45:24.... | 2022.02.01 02:00:00 Custom indicator MTF Stochastic v1.00 AUDUSD,H1: loaded successfully |

---

### page_12.png

**CLOSE MODE**

---

### page_13.png

**Close Mode, Single Order Management (Pips / Money)**

| | === EXIT SYSTEM === | ##### Exit Setting |
| :--- | :--- | :--- |
| **ab** | | |
| **123** | Close Mode | Close Side |

*   **Close all**: close both side (buy + sell)
*   **Close side**: close one side (buy / sell)

---

### page_14.png

**Eg Close all side (buy + sell)**

**參數設定:**
*   **V Batch TP, SL, Trailing (Pips & Money)**
*   **Close Mode**: Close Side

**Journal Log**
| Time | Message |
| --- | --- |
| 3:45:12.550 | 2021.10.01 16:27:20 S10 v3.00 GBPUSD,H1: All Sell Order closed. |
| 3:45:12.550 | 2021.10.01 16:27:20 S10 v3.00 GBPUSD,H1: All Buy Order closed. |
| 3:45:12.550 | 2021.10.01 16:27:20 S10 v3.00 GBPUSD,H1: Sell Order closed: 1.35639 |

**訂單記錄**
| 日期 | 時間 | 操作 | 訂單號 | 手數 | 價格 | 利潤 |
| --- | --- | --- | --- | --- | --- | --- |
| 2021.10.01 | 16:27 | close | 3 | 0.10 | 1.35634 | 81.80 |
| 2021.10.01 | 16:27 | close | 2 | 0.10 | 1.35634 | 91.80 |
| 2021.10.01 | 16:27 | close | 1 | 0.10 | 1.35639 | -123.50 |

---

### page_15.png

**Eg Close one side only**

Side order P / lot size + trailing = trailing line

Although have buy & sell order on hand, only closed buy side !!!
**\*\* Not applicable to Batch TP SL**

**在倉訂單**
| 日期 | 時間 | 類型 | 訂單號 |
| --- | --- | --- | --- |
| 2021.09.30 | 07:17 | sell | 18 |
| 2021.09.30 | 07:19 | sell | 19 |
| 2021.09.30 | 08:53 | sell | 20 |
| 2021.10.01 | 00:00 | buy | 21 |
| 2021.10.01 | 00:11 | buy | 22 |
| 2021.10.01 | 00:12 | buy | 23 |
| 2021.10.01 | 00:12 | buy | 24 |
| 2021.10.01 | 00:12 | buy | 25 |
| 2021.10.01 | 01:00 | buy | 26 |

**平倉記錄**
| # | 日期 | 時間 | 操作 | 訂單號 | 手數 | 價格 | ... | 利潤 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 58 | 2021.10.01 | 15:35 | close | 23 | 0.01 | 1.35355 | ... | 5094.12 |
| 59 | 2021.10.01 | 15:35 | close | 22 | 0.01 | 1.35355 | ... | 5100.38 |
| 60 | 2021.10.01 | 15:35 | close | 21 | 0.01 | 1.35355 | ... | 5106.77 |

**Journal Log**
| Time | Message |
| --- | --- |
| 2022.03.18 23:29:08.439 | 2021.10.04 15:16:12 S10 v3.00 GBPUSD,H1: close #41 buy 0.01 GBPUSD at 1.35362 at price 1.35999 |
| 2022.03.18 23:29:08.439 | 2021.10.04 15:16:12 S10 v3.00 GBPUSD,H1: BUY Order Closing Now... (Batch TSL Side by Dollar) |
| 2022.03.18 23:29:08.439 | 2021.10.04 15:16:12 S10 v3.00 GBPUSD,H1: All Buy Order closed. |
### Page 16

SINGLE ORDER MANAGEMENT (PIPS / MONEY)
TP / SL / TRAILING CLOSE

---

### Page 17

#### Single Order Management (Pips / Money)

**EXIT SYSTEM (Pips)**
| 參數 | 值 |
| --- | --- |
| Stop Loss in Pips (0-not used) | 0.0 |
| Take Profit in Pips (0-not used) | 0.0 |
| Trailing Start in Pips (0-not used) | 0.0 |
| Trailing Distance in Pips (0-not used) | 0.0 |

**EXIT SYSTEM (Money)**
| 參數 | 值 |
| --- | --- |
| Stop Loss in Money (0-not used) | 0.0 |
| Take Profit in Money (0-not used) | 0.0 |
| Trailing Start in Money (0-not used) | 0.0 |
| Trailing Distance in Money (0-not used) | 0.0 |

**換算**
Pips: 0.000X0
Money → Pips = Money / lot size / 1000
(落一手, 行一步, 賺一蚊)

---

### Page 18

#### Single Order Management (Pips / Money)

*   **Stop Loss (SL):** 圖表顯示訂單（藍色箭咀）開立後，價格下跌至預設的 SL 水平（黃色箭咀），訂單被平倉。

*   **Take Profit (TP):** 圖表顯示訂單（藍色箭咀）開立後，價格上升至預設的 TP 水平（黃色箭咀），訂單被平倉。

*   **Trailing:**
    *   **情景一：** 價格上漲，觸發 Trailing Start (100)，移動止損線 (Trailing Line 1) 啟動。只要價格持續上漲，移動止損線會跟隨，與現價保持 Trailing Distance (20) 的距離。
    *   **說明文字：**
        *   After Trailing start, X entry order (移動止損啟動後，X 入場訂單)
        *   But if current p fall, trailing line will not follow to fall (如果現價下跌，移動止損線不會跟隨下跌)
        *   Trailing line will follow current P rise after trailing start (移動止損線將於移動止損啟動後跟隨現價上升)

---

### Page 19

#### Single Order SL Eg (Pips)

**交易日誌**
| 時間 | 類型 | 序號 | 手數 | 價格 |
| --- | --- | --- | --- | --- |
| 2021.09.30 04:00 | sell | 1 | 0.10 | 1.34408 |
| 2021.09.30 04:00 | sell | 2 | 0.10 | 1.34398 |
| 2021.09.30 04:22 | sell | 3 | 0.10 | 1.34386 |
| 2021.09.30 04:22 | sell | 4 | 0.10 | 1.34376 |
| 2021.09.30 04:22 | sell | 5 | 0.10 | 1.34364 |
| 2021.09.30 04:40 | sell | 6 | 0.10 | 1.34442 |
| 2021.09.30 04:41 | close | 5 | 0.10 | 1.34466 |
| 2021.09.30 04:43 | sell | 7 | 0.10 | 1.34432 |
| 2021.09.30 05:06 | close | 4 | 0.10 | 1.34476 |
| 2021.09.30 05:06 | close | 3 | 0.10 | 1.34486 |
| 2021.09.30 05:07 | close | 2 | 0.10 | 1.34500 |

**系統訊息**
*   USD,H1: Order #5 Closing Now... (Single SL by Pip)
*   USD,H1: close #5 sell 0.10 GBPUSD at 1.34364 at price 1.34466

**計算**
Single order P + SL (pips) = close P
1.34364 + 10 pips = 1.34464

**說明**
When each order reach SL in pips, single order would be closed.
(new order can enter after one order closed, unless max level of order reached)
當每張訂單達到以點數計算的止損時，該訂單將被平倉。
（一張訂單平倉後才能建立新訂單，除非已達到最大訂單數）

---

### Page 20

#### Single Order Trailing (Money)

**圖表說明**
圖表顯示一個買入訂單(#2)的移動止盈過程。

*   **Buy Down -- #2 Buy P < #1 Buy P**
    (#2 買入價低於 #1 買入價)
*   **After reaching 100 dollar above order #2, Single trailing triggered for #2 only, trailing line at 80 dollar**
    (當盈利超過 #2 訂單 100 美元後，只為 #2 訂單觸發移動止盈，移動止盈線設於盈利 80 美元)
*   **Trailing line then follow rise in current P to 86 dollar,**
    (移動止盈線跟隨現價上升至盈利 86 美元)
*   **After current P drop to trailing line 2, Trailing SL**
    (現價下跌至移動止盈線 2 後，觸發移動止損)

**交易日誌**
| 時間 | 類型 | 序號 | 手數 | 價格 |
| --- | --- | --- | --- | --- |
| 2021.10.01 04:00 | buy | 1 | 0.10 | 1.34541 |
| 2021.10.01 10:04 | buy | 2 | 0.10 | 1.34390 |
| 2021.10.01 15:41 | close | 2 | 0.10 | 1.35254 |

**系統訊息**
*   2022.03.19 21:01:08.081 S10 v3.00 GBPUSD,H1: Dollar Trail of #2 is updated: 86.60000
*   2022.03.19 20:57:22.409 S10 v3.00 GBPUSD,H1: Dollar Trail of #2 is updated: 80.00000
*   2022.03.19 20:57:06.120 S10 v3.00 GBPUSD,H1: open #2 buy 0.10 GBPUSD at 1.34390 ok
好的，這就為您提取 S10 EA 說明書 `page_21.png` 到 `page_25.png` 的所有可見文字。

### **Page_21.png**

BATCH ORDER MANAGEMENT (PIPS / MONEY)
TP / SL / TRAILING CLOSE

---

### **Page_22.png**

#### **Batch Order Management-Pips-Setting**

| 功能 | 參數 | 當前值 |
| :--- | :--- | :--- |
| **=== EXIT SYSTEM ===** | **=== Batch Order Management (Pips) ===** | |
| Stop Loss in Pips (0-not used) | 30.0 | 0.0 |
| Take Profit in Pips (0-not used) | 10.0 | 0.0 |
| Trailing Start in Pips (0-not used) | 5.0 | 0.0 |
| Trailing Distance in Pips (0-not used) | 2.0 | 0.0 |
| **=== EXIT SYSTEM ===** | **=== Batch Order Management (Money) ===**| |
| Stop Loss in Money (0-not used) | 0.0 | 300.0 |
| Take Profit in Money (0-not used) | 0.0 | 0.0 |
| Trailing Start in Money (0-not used) | 0.0 | 150.0 |
| Trailing Distance in Money (0-not u... | 0.0 | 20.0 |

---

### **Page_23.png**

#### **Batch Order Management-Pips-Take Profit-Chart**

圖表顯示了一筆交易的止盈（Take Profit）過程。

*   **入場點 (Entry):** 1 / 100 / 81.120
*   **參數設置:**
    *   Take Profit in Pips: 10.0

| 功能 | 參數 | 當前值 |
| :--- | :--- | :--- |
| **=== EXIT SYSTEM ===** | **=== Batch Order Management (Pips) ===** | |
| Stop Loss in Pips (0-not used) | 30.0 | 0.0 |
| Take Profit in Pips (0-not used) | 10.0 | 0.0 |
| Trailing Start in Pips (0-not used) | 5.0 | 0.0 |
| Trailing Distance in Pips (0-not used) | 2.0 | 0.0 |

*   **交易記錄:**
    *   `4` 2021.12.01 04:09 close 2 0.10 81.021 1.93 5003.44
    *   `5` 2021.12.01 04:09 buy 3 0.10 81.025
    *   `6` 2021.12.01 04:31 close 3 0.10 81.127 8.56 5012.00

---

### **Page_24.png**

#### **Batch Order Management-Pips-Take Profit -Journal**

*   **日誌詳情:**
    *   `2021.12.01 04:09:54 S10 v3.00 AUDJPY,H1: open #3 buy 0.10 AUDJPY at 81.025 ok`
    *   `2021.12.01 04:09:54 S10 v3.00 AUDJPY,H1: Entry 1 MACD (MAIN): -0.043, Entry 1 MACD (SIGNAL): -0.128, Effective MACD (MAIN): -49.264, Effective MA...`
    *   `2021.12.01 04:30:56 S10 v3.00 AUDJPY,H1: Batch Pips Trail is updated: 81.044`
    *   `2021.12.01 04:30:56 S10 v3.00 AUDJPY,H1: Side Pips Trail is updated: 81.044`
    *   `Skip Trailing Journal`
    *   `2021.12.01 04:31:11 S10 v3.00 AUDJPY,H1: Batch Pips Trail is updated: 81.093`
    *   `2021.12.01 04:31:11 S10 v3.00 AUDJPY,H1: Side Pips Trail is updated: 81.093`
    *   `2021.12.01 04:31:14 S10 v3.00 AUDJPY,H1: Order Closing Now... (Batch TP by Pip)`
    *   `2021.12.01 04:31:14 S10 v3.00 AUDJPY,H1: close #3 buy 0.10 AUDJPY at 81.025 at price 81.127`
    *   `2021.12.01 04:31:14 S10 v3.00 AUDJPY,H1: Buy Order closed: 81.127`
    *   `2021.12.01 04:31:14 S10 v3.00 AUDJPY,H1: All Sell Order closed.`
    *   `2021.12.01 04:31:14 S10 v3.00 AUDJPY,H1: All Buy Order closed.`

*   **計算說明:**
    *   `Batch order P + TP (pips) = close P`
    *   `81.025 + ~10 pips (JPY only) = 81.127`

*   **交易記錄:**
    *   `4` 2021.12.01 04:09 close 2 0.10 81.021 1.93 5003.44
    *   `5` 2021.12.01 04:09 buy 3 0.10 81.025
    *   `6` 2021.12.01 04:31 close 3 0.10 81.127 8.56 5012.00

---

### **Page_25.png**

#### **Batch Order Management-Pips-Trailing-Journal**

*   **交易記錄:**

| # | 時間 | 類型 | 訂單 | 手數 | 價格 | 止損 | 止盈 | 盈利 | 註釋 |
| :- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | 2021.12.01 04:00 | buy | 1 | 0.10 | 80.976 | | | | |
| 2 | 2021.12.01 04:05 | close | 1 | 0.10 | 80.994 | | | 1.51 | 5001.51 |
| 3 | 2021.12.01 04:05 | buy | 2 | 0.10 | 80.998 | | | | |
| 4 | 2021.12.01 04:09 | close | 2 | 0.10 | 81.021 | | | 1.93 | 5003.44 |

*   **日誌詳情:**
    *   `2021.12.01 04:00:00 S10 v3.00 AUDJPY,H1: open #1 buy 0.10 AUDJPY at 80.976 ok`
    *   ... (MACD 資訊) ...
    *   `2021.12.01 04:04:03 S10 v3.00 AUDJPY,H1: Batch Pips Trail is updated: 80.995`
    *   `2021.12.01 04:05:37 S10 v3.00 AUDJPY,H1: Order Closing Now... (Batch TSL Side by Pip)`
    *   `2021.12.01 04:05:37 S10 v3.00 AUDJPY,H1: close #1 buy 0.10 AUDJPY at 80.976 at price 80.994`
    *   `2021.12.01 04:05:37 S10 v3.00 AUDJPY,H1: Buy Order closed: 80.994`
    *   ... (後續日誌) ...

*   **計算說明:**
    *   `Batch order P + T SL (pips) = close P`
    *   `80.976 + ~2 pips (JPY only) = 80.994`

*   **參數設置:**

| 功能 | 參數 | 當前值 |
| :--- | :--- | :--- |
| **=== EXIT SYSTEM ===** | **=== Batch Order Management (Pips) ===** | |
| Stop Loss in Pips (0-not used) | 30.0 | 0.0 |
| Take Profit in Pips (0-not used) | 10.0 | 0.0 |
| Trailing Start in Pips (0-not used) | 5.0 | 0.0 |
| Trailing Distance in Pips (0-not used) | 2.0 | 0.0 |
好的，這就為您提取頁面中的文字。

### Page_26.png

**標題：** Batch Order Management-Pips-Stop Loss-Chart

**退出系統參數：**
| 參數 | 數值 |
|---|---|
| === EXIT SYSTEM === | === Batch Order Management (Pips) === |
| Stop Loss in Pips (0-not used) | 10.0 |
| Take Profit in Pips (0-not used) | 0.0 |
| Trailing Start in Pips (0-not used) | 5.0 |
| Trailing Distance in Pips (0-not used) | 2.0 |

**交易記錄：**
*   2022.03.19 12:21:31.582
*   2022.03.19 12:21:31.582
*   2022.03.19 12:21:31.937
*   2022.03.19 12:21:31.945
*   2022.03.19 12:21:31.945
*   2022.03.19 12:21:31.945
*   2022.03.19 12:21:31.945

---

### Page_27.png

**標題：** Batch Order Management-Money-Setting

**退出系統參數：**
| 參數 | 數值 1 | 數值 2 |
|---|---|---|
| === EXIT SYSTEM === | === Batch Order Management (Pips) === |
| Stop Loss in Pips (0-not used) | 0.0 | 0.0 |
| Take Profit in Pips (0-not used) | 0.0 | 0.0 |
| Trailing Start in Pips (0-not used) | 0.0 | 0.0 |
| Trailing Distance in Pips (0-not used) | 0.0 | 0.0 |
| === EXIT SYSTEM === | === Batch Order Management (Money) === |
| Stop Loss in Money (0-not used) | 300.0 | 300.0 |
| Take Profit in Money (0-not used) | 100.0 | 0.0 |
| Trailing Start in Money (0-not used) | 50.0 | 150.0 |
| Trailing Distance in Money (0-not used) | 20.0 | 20.0 |

---

### Page_28.png

**標題：** Batch Order Management-Money-Stop Loss-Chart

**圖表標記：**
*   #17 Sell
*   #18-#20 Sell
*   #17-#20 Stop Loss

---

### Page_29.png

**標題：** Batch Order Management-Money-Stop Loss-Journal

**退出系統參數：**
| 參數 | 數值 1 | 數值 2 |
|---|---|---|
| === EXIT SYSTEM === | === Batch Order Management (Pips) === |
| Stop Loss in Pips (0-not used) | 0.0 | 0.0 |
| Take Profit in Pips (0-not used) | 0.0 | 0.0 |
| Trailing Start in Pips (0-not used) | 0.0 | 0.0 |
| Trailing Distance in Pips (0-not used) | 0.0 | 0.0 |
| === EXIT SYSTEM === | === Batch Order Management (Money) === |
| Stop Loss in Money (0-not used) | 300.0 | 300.0 |
| Take Profit in Money (0-not used) | 0.0 | 0.0 |
| Trailing Start in Money (0-not used) | 50.0 | 150.0 |
| Trailing Distance in Money (0-not used) | 20.0 | 20.0 |

**交易日誌：**
| 時間 | 類型 | 訂單 | 大小 | 價格 | 止損/止盈 | 盈利 | 結餘 |
|---|---|---|---|---|---|---|---|
| 2021.12.14 05:37 | close | 14 | 0.10 | 80.544 | | 11.83 | 5198.65 |
| 2021.12.14 05:37 | close | 13 | 0.10 | 80.544 | | 18.41 | 5217.07 |
| 2021.12.14 05:37 | sell | 17 | 0.10 | 80.545 | | | |
| 2021.12.20 08:48 | sell | 18 | 0.10 | 80.464 | | | |
| 2021.12.20 09:16 | sell | 19 | 0.10 | 80.383 | | | |
| 2021.12.20 09:27 | sell | 20 | 0.10 | 80.303 | | | |
| 2021.12.21 17:15 | close | 20 | 0.10 | 81.315 | | -85.06 | 5132.01 |
| 2021.12.21 17:15 | close | 19 | 0.10 | 81.315 | | -78.34 | 5053.68 |
| 2021.12.21 17:15 | close | 18 | 0.10 | 81.315 | | -71.55 | 4982.13 |
| 2021.12.21 17:15 | close | 17 | 0.10 | 81.315 | | -65.50 | 4916.63 |

---

### Page_30.png

**標題：** Batch Order Management-Money-Take Profit-Chart

**圖表標記：**
*   #41-#44 Sell
*   #45 Sell & ALL TP

**退出系統參數：**
| 參數 | 數值 1 | 數值 2 |
|---|---|---|
| === EXIT SYSTEM === | === Batch Order Management (Pips) === |
| Stop Loss in Pips (0-not used) | 0.0 | 0.0 |
| Take Profit in Pips (0-not used) | 0.0 | 0.0 |
| Trailing Start in Pips (0-not used) | 0.0 | 0.0 |
| Trailing Distance in Pips (0-not used) | 0.0 | 0.0 |
| === EXIT SYSTEM === | === Batch Order Management (Money) === |
| Stop Loss in Money (0-not used) | 300.0 | 300.0 |
| Take Profit in Money (0-not used) | 100.0 | 0.0 |
| Trailing Start in Money (0-not used) | 50.0 | 150.0 |
| Trailing Distance in Money (0-not used) | 20.0 | 20.0 |

**交易日誌：**
| | 時間 | 類型 | 訂單 | 大小 | 價格 | 盈利 | 結餘 |
|---|---|---|---|---|---|---|---|
| 80 | 2022.01.03 03:14 | close | 37 | 0.10 | 83.822 | -65.21 | 4770.41 |
| 81 | 2022.01.03 04:00 | sell | 41 | 0.10 | 83.594 | | |
| 82 | 2022.01.03 04:08 | sell | 42 | 0.10 | 83.513 | | |
| 83 | 2022.01.03 12:57 | sell | 43 | 0.10 | 83.433 | | |
| 84 | 2022.01.03 13:09 | sell | 44 | 0.10 | 83.353 | | |
| 85 | 2022.01.03 15:15 | sell | 45 | 0.10 | 83.192 | | |
| 86 | 2022.01.03 15:15 | close | 45 | 0.10 | 83.178 | 1.18 | 4771.59 |
| 87 | 2022.01.03 15:15 | close | 44 | 0.10 | 83.178 | 14.69 | 4786.28 |
| 88 | 2022.01.03 15:15 | close | 43 | 0.10 | 83.178 | 21.40 | 4807.68 |
| 89 | 2022.01.03 15:15 | close | 42 | 0.10 | 83.178 | 28.11 | 4835.79 |
| 90 | 2022.01.03 15:15 | close | 41 | 0.10 | 83.178 | 34.91 | 4870.70 |
| | -85.06 | 5132.01 |
| 2021.12.21 17:15 | close | 19 | 0.10 | 81.315 | | | -78.34 | 5053.68 |
| 2021.12.21 17:15 | close | 18 | 0.10 | 81.315 | | | -71.55 | 4982.13 |
| 2021.12.21 17:15 | close | 17 | 0.10 | 81.315 | | | -65.50 | 4916.63 |

總虧損約為 300。

---
以下係 **page_30.png** 嘅內容：

S10 COURSE

### Batch Order Management-Money-Take Profit-Chart

圖表顯示以下標記：
*   #41-#44 Sell
*   #45 Sell & ALL TP

**參數設定：**

| 參數名稱 | 數值 |
| :--- | :--- |
| `=== EXIT SYSTEM ===` | `=== Batch Order Management (Pips) ===` |
| Stop Loss in Pips (0-not used) | 0.0 |
| Take Profit in Pips (0-not used) | 0.0 |
| Trailing Start in Pips (0-not used) | 0.0 |
| Trailing Distance in Pips (0-not used) | 0.0 |
| `=== EXIT SYSTEM ===` | `=== Batch Order Management (Money) ===` |
| Stop Loss in Money (0-not used) | 300.0 |
| Take Profit in Money (0-not used) | 100.0 |
| Trailing Start in Money (0-not used) | 50.0 |
| Trailing Distance in Money (0-not u... | 20.0 |

**交易日誌：**

| # | Time | Type | Order | Size | Price | Profit | Balance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 80 | 2022.01.03 03:14 | close | 37 | 0.10 | 83.822 | -65.21 | 4770.41 |
| 81 | 2022.01.03 04:00 | sell | 41 | 0.10 | 83.594 | | |
| 82 | 2022.01.03 04:08 | sell | 42 | 0.10 | 83.513 | | |
| 83 | 2022.01.03 12:57 | sell | 43 | 0.10 | 83.433 | | |
| 84 | 2022.01.03 13:09 | sell | 44 | 0.10 | 83.353 | | |
| 85 | 2022.01.03 15:15 | sell | 45 | 0.10 | 83.192 | | |
| 86 | 2022.01.03 15:15 | close | 45 | 0.10 | 83.178 | 1.18 | 4771.59 |
| 87 | 2022.01.03 15:15 | close | 44 | 0.10 | 83.178 | 14.69 | 4786.28 |
| 88 | 2022.01.03 15:15 | close | 43 | 0.10 | 83.178 | 21.40 | 4807.68 |
| 89 | 2022.01.03 15:15 | close | 42 | 0.10 | 83.178 | 28.11 | 4835.79 |
| 90 | 2022.01.03 15:15 | close | 41 | 0.10 | 83.178 | 34.91 | 4870.70 |

總利潤約為 100。
好的，這就為您提取頁面中的文字。

**page_31.png**

S10 COURSE

# Batch Order Management-Money-Take Profit -Journal

| 時間 | 內容 |
| --- | --- |
| 2022.01.03 15:15:21 | S10 v3.00 AUDJPY,H1: All Sell Order closed. |
| 2022.01.03 15:15:21 | S10 v3.00 AUDJPY,H1: close #41 sell 0.10 AUDJPY at 83.594 at price 83.178 |
| 2022.01.03 15:15:21 | S10 v3.00 AUDJPY,H1: close #42 sell 0.10 AUDJPY at 83.513 at price 83.178 |
| 2022.01.03 15:15:21 | S10 v3.00 AUDJPY,H1: close #43 sell 0.10 AUDJPY at 83.433 at price 83.178 |
| 2022.01.03 15:15:21 | S10 v3.00 AUDJPY,H1: close #44 sell 0.10 AUDJPY at 83.353 at price 83.178 |
| 2022.01.03 15:15:21 | S10 v3.00 AUDJPY,H1: Sell Order closed: 83.178 |
| 2022.01.03 15:15:21 | S10 v3.00 AUDJPY,H1: close #45 sell 0.10 AUDJPY at 83.192 at price 83.178 |
| 2022.01.03 15:15:21 | S10 v3.00 AUDJPY,H1: All Buy Order closed. |
| 2022.01.03 15:15:21 | S10 v3.00 AUDJPY,H1: Order Closing Now... (Batch TP by Dollar) |
| 2022.01.03 15:15:18 | S10 v3.00 AUDJPY,H1: Side Dollar Trail is updated: $79.04 |
| 2022.01.03 15:15:18 | S10 v3.00 AUDJPY,H1: Batch Dollar Trail is updated: $79.04 |

**Skip Trailing Journal**

| 時間 | 內容 |
| --- | --- |
| 2022.01.03 15:07:42 | S10 v3.00 AUDJPY,H1: Side Dollar Trail is updated: $30.11 |
| 2022.01.03 15:07:42 | S10 v3.00 AUDJPY,H1: Batch Dollar Trail is updated: $30.11 |
| 2022.01.03 13:09:43 | S10 v3.00 AUDJPY,H1: open #44 sell 0.10 AUDJPY at 83.353 ok |
| 2022.01.03 12:57:55 | S10 v3.00 AUDJPY,H1: open #43 sell 0.10 AUDJPY at 83.433 ok |
| 2022.01.03 04:08:53 | S10 v3.00 AUDJPY,H1: open #42 sell 0.10 AUDJPY at 83.513 ok |
| 2022.01.03 04:00:00 | S10 v3.00 AUDJPY,H1: Entry 1 MACD (MAIN): 0.043, Entry 1 MACD (SIGNAL): 0.049, Effective MACD (MAIN): 22.206, Effective MACD (SIGNAL): 24.389, Effective MACD (... |
| 2022.01.03 04:00:00 | S10 v3.00 AUDJPY,H1: open #41 sell 0.10 AUDJPY at 83.594 ok |
| 2022.01.03 03:14:02 | S10 v3.00 AUDJPY,H1: All Sell Order closed. |

---

**page_32.png**

S10 COURSE

# Batch Order Management-Money-Trailing-Result

| 參數 | Batch Order Management (Pips) | |
| :--- | :--- | :--- |
| Stop Loss in Pips (0-not used) | 0.0 | 0.0 |
| Take Profit in Pips (0-not used) | 0.0 | 0.0 |
| Trailing Start in Pips (0-not used) | 0.0 | 0.0 |
| Trailing Distance in Pips (0-not used)| 0.0 | 0.0 |

| 參數 | Batch Order Management (Money) | |
| :--- | :--- | :--- |
| Stop Loss in Money (0-not used) | 300.0 | 300.0 |
| Take Profit in Money (0-not used) | 100.0 | 0.0 |
| Trailing Start in Money (0-not used) | 50.0 | 150.0 |
| Trailing Distance in Money (0-not u...| 20.0 | 20.0 |

| Time | Type | Order | Size | Price | S/L | T/P | Profit | Balance |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| 2021.12.22 16:55 | close | 25 | 0.10 | 82.170 | | | 23.08 | 5006.68 |
| 2021.12.22 16:55 | buy | 29 | 0.10 | 82.178 | | | | |
| 2021.12.22 17:13 | buy | 30 | 0.10 | 82.258 | | | | |
| 2021.12.22 17:31 | buy | 31 | 0.10 | 82.339 | | | | |
| 2021.12.22 18:49 | buy | 32 | 0.10 | 82.419 | | | | |
| 2021.12.22 20:19 | close | 32 | 0.10 | 82.410 | | | -0.76 | 5005.92 |
| 2021.12.22 20:19 | close | 31 | 0.10 | 82.410 | | | 5.96 | 5011.88 |
| 2021.12.22 20:19 | close | 30 | 0.10 | 82.410 | | | 12.76 | 5024.64 |
| 2021.12.22 20:19 | close | 29 | 0.10 | 82.410 | | | 19.47 | 5044.11 |

~38

---

**page_33.png**

S10 COURSE

# Batch Order Management-Money-Trailing-Journal

| 時間 | 內容 |
| --- | --- |
| 2021.12.22 16:55:58 | S10 v3.00 AUDJPY,H1: All Buy Order closed. |
| 2021.12.22 16:55:59 | S10 v3.00 AUDJPY,H1: open #29 buy 0.10 AUDJPY at 82.178 ok |
| 2021.12.22 16:55:59 | S10 v3.00 AUDJPY,H1: Entry 1 MACD (MAIN): 0.184, Entry 1 MACD (SIGNAL): 0.130, Effective MACD (MAIN): 14.359, Effective MACD (SI... |
| 2021.12.22 17:13:19 | S10 v3.00 AUDJPY,H1: open #30 buy 0.10 AUDJPY at 82.258 ok |
| 2021.12.22 17:31:11 | S10 v3.00 AUDJPY,H1: open #31 buy 0.10 AUDJPY at 82.339 ok |
| 2021.12.22 18:49:20 | S10 v3.00 AUDJPY,H1: open #32 buy 0.10 AUDJPY at 82.419 ok |
| 2021.12.22 19:16:05 | S10 v3.00 AUDJPY,H1: Batch Dollar Trail is updated: $30.14 |
| 2021.12.22 19:16:05 | S10 v3.00 AUDJPY,H1: Side Dollar Trail is updated: $30.14 |
| 2021.12.22 19:16:05 | S10 v3.00 AUDJPY,H1: Batch Dollar Trail is updated: $32.18 |
| 2021.12.22 19:16:05 | S10 v3.00 AUDJPY,H1: Side Dollar Trail is updated: $32.18 |
| 2021.12.22 19:16:43 | S10 v3.00 AUDJPY,H1: Batch Dollar Trail is updated: $34.50 |
| 2021.12.22 19:16:43 | S10 v3.00 AUDJPY,H1: Side Dollar Trail is updated: $34.50 |
| 2021.12.22 19:19:19 | S10 v3.00 AUDJPY,H1: Batch Dollar Trail is updated: $36.54 |
| 2021.12.22 19:19:19 | S10 v3.00 AUDJPY,H1: Side Dollar Trail is updated: $36.54 |
| 2021.12.22 20:21:07 | S10 v3.00 AUDJPY,H1: Order Closing Now... (Batch TSL by Dollar) |
| 2021.12.22 20:21:07 | S10 v3.00 AUDJPY,H1: BUY Order Closing Now... (Batch TSL Side by Dollar) |
| 2021.12.22 20:21:07 | S10 v3.00 AUDJPY,H1: close #32 buy 0.10 AUDJPY at 82.419 at price 82.407 |
| 2021.12.22 20:21:07 | S10 v3.00 AUDJPY,H1: Buy Order closed: 82.407 |
| 2021.12.22 20:21:07 | S10 v3.00 AUDJPY,H1: close #31 buy 0.10 AUDJPY at 82.339 at price 82.407 |
| 2021.12.22 20:21:07 | S10 v3.00 AUDJPY,H1: close #30 buy 0.10 AUDJPY at 82.258 at price 82.407 |
| 2021.12.22 20:21:07 | S10 v3.00 AUDJPY,H1: close #29 buy 0.10 AUDJPY at 82.178 at price 82.407 |
| 2021.12.22 20:21:07 | S10 v3.00 AUDJPY,H1: All Sell Order closed. |

---

**page_34.png**

S10 COURSE

# Single & Batch Setting Tips

| 時間 | 內容 |
| --- | --- |
| 2021.10.01 10:38:02 | S10 v3.00 GBPUSD,H1: Batch Pips Trail is removed: Orders Net Gain is now -$0. |
| 2021.10.01 10:28:58 | S10 v3.00 GBPUSD,H1: Order #2 Closing Now... (Single TP by Pip) |
| 2021.10.01 10:28:58 | S10 v3.00 GBPUSD,H1: close #2 buy 0.10 GBPUSD at 1.34390 at price 1.34591 |
| 2021.10.01 10:28:49 | S10 v3.00 GBPUSD,H1: Batch Pips Trail is updated: 1.33886 |

Although Batch Trailing started, **Single TP/SL/Trailing will still close single order in batch**, batch trailing would then be cancelled and recalculated.

---

**page_35.png**

EXIT AI SIGNALS
好的，這就為您提取 page_36.png 到 page_40.png 的內容。

### Page 36

#### Exit AI Signal

**ENTRY SYSTEM - ADDITION**
*   **AI Source**: AI 1
*   **Use AI Direction Control**: On

**EXIT SYSTEM**
*   **Use AI Signal Change Exit**: Off

**Exit AI Signal Setting**
*   **選項**: Off / On (已選擇 "On")

**說明**
*   **Exit AI On**: 會根據市況預測判斷出市 (Up / Down / No trend)
*   **Exit AI Off**: 不會有任何動作

---

### Page 37

#### Exit AI Signal

*   **AI Direction Control**: On
*   **AI Signal Exit**: On

**日誌摘要**
*   `2022.04.14 15:58:33.541 S10 v3.00 EURGBP,M15: MA Cross Cooldown Now... (BUY)`
*   `2022.04.14 15:58:33.541 S10 v3.00 EURGBP,M15: Buy Order closed: 0.82605`
*   `2022.04.14 15:58:33.541 S10 v3.00 EURGBP,M15: close #2048751069 buy 0.10 EURGBP at 0.83110 at price 0.82605`
*   `2022.04.14 15:58:33.322 S10 v3.00 EURGBP,M15: Exit: AI Signal: Downtrend`
*   `2022.04.14 15:58:33.322 S10 v3.00 EURGBP,M15: BUY Order Closing Now... (AI Signal change)`
*   `2022.04.14 15:58:33.322 S10 v3.00 EURGBP,M15: File successfully downloaded, the file size in bytes =295.`
*   `2022.04.14 15:58:33.291 S10 v3.00 EURGBP,M15: investing.com News Loading...`
*   `2022.04.14 15:58:33.291 S10 v3.00 EURGBP,M15: initialized`

**說明**
*   Sense 到 AI Signal Change
*   有 Buy單 sense到 Downtrend 轉勢所以平倉出市

---

### Page 38

**EXIT SYSTEM**
*   **Use AI Signal Change Exit**: On

**說明**
當 AI Signal 由 Uptrend 改變為 Down Trend 時進行出市。
在這個圖例中，實例情況是在 Trend 尾時進行了入市，如果繼續持倉可能會損失更大，這次 AI signal 實際上是進行了 SL。

**圖表日誌摘要**
*   `2022.03.22 17:21:25... 2021.10.27 12:00:00 S10 v3.00 GBPJPY,H1: open #135 buy 0.10 GBPJPY at 157.167 at price 156.027`
*   `2022.03.22 17:21:25... 2021.10.27 12:00:00 S10 v3.00 GBPJPY,H1: Exit STC: 7.0% Exit: AI Signal: Downtrend`
*   `2022.03.22 17:21:25... 2021.10.28 10:45:00 S10 v3.00 GBPJPY,H1: open #135 buy 0.10 GBPJPY at 157.067 ok.`
*   `2022.03.22 17:21:18... 2021.10.28 11:15:00 S10 v3.00 GBPJPY,H1: open #136 buy 0.10 GBPJPY at 157.057 ok.`
*   `2022.03.22 17:21:18... 2021.10.28 11:20:00 S10 v3.00 GBPJPY,H1: open #137 buy 0.10 GBPJPY at 157.057 ok.`
*   `2022.03.22 17:21:18... 2021.10.28 11:25:00 S10 v3.00 GBPJPY,H1: open #138 buy 0.10 GBPJPY at 157.057 ok.`
*   `2022.03.22 17:21:18... 2021.10.28 15:20:00 S10 v3.00 GBPJPY,H1: open #139 buy 0.10 GBPJPY at 157.417 ok.`
*   `2022.03.22 17:21:18... 2021.10.28 15:25:00 S10 v3.00 GBPJPY,H1: Entry 1 MACD (MAIN) 77.497, Effective MACD (SIGNAL) 51.031, Effective MACD (DIFF) 24.214, AI Signal: Uptrend`

---

### Page 39

**說明**
*   只使用 AI Exit 而不使用 AI Entry 的 backtest，其他設定一律不改的情況
*   這次測試找不到任何 AI Close 的記錄，推測不用 AI Entry 的話，是不會觸發 AI Signal Change

**日誌**
```
Message
2021.10.27 20:45:00 S10 v3.00 GBPJPY,H1: STC Top Return. BUY Orders Net Gain is now $ -2587.18428
2021.10.27 20:45:00 S10 v3.00 GBPJPY,H1: STC Top Return Modified to 90.8 (SL/TP)
2021.10.27 20:45:00 S10 v3.00 GBPJPY,H1: STC Top Return Activated (STC TP)
2021.10.26 13:00:00 S10 v3.00 GBPJPY,H1: open #96 buy 0.17 GBPJPY at 156.861 ok.
2021.10.25 18:45:00 S10 v3.00 GBPJPY,H1: STC Top Return Modified to 90.8 (SL/TP)
2021.10.25 12:45:10 S10 v3.00 GBPJPY,H1: open #94 buy 0.17 GBPJPY at 156.219 ok.
2021.10.25 10:25:30 S10 v3.00 GBPJPY,H1: open #93 buy 0.20 GBPJPY at 156.781 ok.
2021.10.25 09:55:00 S10 v3.00 GBPJPY,H1: open #92 buy 0.18 GBPJPY at 156.881 ok.
2021.10.25 09:54:20 S10 v3.00 GBPJPY,H1: open #91 buy 0.19 GBPJPY at 156.871 ok.
2021.10.25 03:55:07 S10 v3.00 GBPJPY,H1: open #90 buy 0.18 GBPJPY at 156.531 ok.
2021.10.25 01:45:07 S10 v3.00 GBPJPY,H1: STC Top Return. BUY Orders Net Gain is now $ -3002.20685
2021.10.25 01:45:07 S10 v3.00 GBPJPY,H1: STC Top Return Modified to 90.8 (SL/TP)
2021.10.25 01:45:07 S10 v3.00 GBPJPY,H1: STC Top Return Activated (STC TP)
2021.10.22 14:52:12 S10 v3.00 GBPJPY,H1: open #88 buy 0.22 GBPJPY at 157.144 ok.
2021.10.22 04:11:12 S10 v3.00 GBPJPY,H1: open #87 buy 0.23 GBPJPY at 157.424 ok.
2021.10.22 04:10:22 S10 v3.00 GBPJPY,H1: open #86 buy 0.21 GBPJPY at 157.374 ok.
2021.10.22 03:57:12 S10 v3.00 GBPJPY,H1: open #85 buy 0.22 GBPJPY at 157.194 ok.
2021.10.22 03:02:45 S10 v3.00 GBPJPY,H1: open #84 buy 0.22 GBPJPY at 157.044 ok.
2021.10.22 02:52:00 S10 v3.00 GBPJPY,H1: open #83 buy 0.22 GBPJPY at 156.960 ok.
2021.10.21 07:12:00 S10 v3.00 GBPJPY,H1: open #82 buy 0.23 GBPJPY at 157.703 ok.
2021.10.21 07:11:10 S10 v3.00 GBPJPY,H1: open #81 buy 0.23 GBPJPY at 157.653 ok.
2021.10.20 21:30:02 S10 v3.00 GBPJPY,H1: STC Top Return is removed. BUY Orders Net Gain is now $ -29.17
2021.10.20 21:30:02 S10 v3.00 GBPJPY,H1: STC Top Return Modified to 90.8 (SL/TP)
2021.10.20 21:30:02 S10 v3.00 GBPJPY,H1: STC Top Return Activated (STC TP)
2021.10.20 21:02:10 S10 v3.00 GBPJPY,H1: open #80 buy 0.24 GBPJPY at 157.907 ok.
2021.10.20 20:29:20 S10 v3.00 GBPJPY,H1: open #79 buy 0.24 GBPJPY at 157.990 ok.
2021.10.20 18:45:00 S10 v3.00 GBPJPY,H1: Entry 1 MACD (MAIN): 147.457, Effective MACD (SIGNAL): 69.960, Effective MACD (DIFF): 77.497, AI Signal: No trend detected
2021.10.20 18:45:00 S10 v3.00 GBPJPY,H1: open #77 buy 0.24 GBPJPY at 158.008 ok.
2021.10.20 02:15:08 S10 v3.00 GBPJPY,H1: MA Cross Cooldown Now... (BUY)
2021.10.20 02:15:08 S10 v3.00 GBPJPY,H1: All Buy Order closed.
2021.10.20 02:15:08 S10 v3.00 GBPJPY,H1: Stochastic Cooldown Now... (BUY)
2021.10.20 02:15:07 S10 v3.00 GBPJPY,H1: close #74 buy 0.24 GBPJPY at 157.864 at price 157.866
2021.10.20 02:15:05 S10 v3.00 GBPJPY,H1: open #76 buy 0.24 GBPJPY at 157.892 at price 157.866
2021.10.20 02:15:05 S10 v3.00 GBPJPY,H1: Buy Order closed.
2021.10.20 02:15:01 S10 v3.00 GBPJPY,H1: close #76 buy 0.24 GBPJPY at 157.737 at price 157.866
```

---

### Page 40

EXIT STC
好的，這就為您提取 S10 EA 說明書 `page_41.png` 到 `page_45.png` 的所有可見文字。

### **Page 41**

# Exit STC

## STC setting Parameters

| === EXIT SYSTEM === | | === Exit STC Setting === | |
| :--- | :--- | :--- | :--- |
| **Use STC Close** | On/Off | On | 應用 STC 出市開/關 |
| **Apply On Profit** | On/Off | On | 應用 STC 獲利 |
| **Apply On Loss** | On/Off | Off | 應用 STC 止損 |
| **STC Timeframe** | current | | STC 時間框架 |
| **STC K-line Period**| 5 | | STC K線週期 |
| **STC D-line Period**| 3 | | STC D線週期 |
| **STC Slowing Value**| 3 | | STC 慢速值 |
| **STC MA Method** | Simple | | STC 移動平均 |
| **STC Price Field** | Low/High | | STC 應用價格 |
| **STC Shift** | 1 | | STC 偏移值 |
| **STC Close Above** | 80.0 | | STC 高位出市值 |
| **STC Close Below** | 20.0 | | STC 低位出市值 |
| **STC Top Return** | On/Off | Off | STC 均價回報 |
| **STC Top Return Start**| 10.0 | | STC 均價回報數值 |
| **STC Top Return Distance**| 10.0 | | STC 均價回報距離 |
| **STC Reset** | On/Off | On | STC 重新計算 |
| **STC Reset Buy Below**| 50.0 | | Buy 單數值以下重新計算 |
| **STC Reset Sell Above**| 50.0 | | Sell 單數值以上重新計算 |

---

### **可選參數值**

**STC Timeframe**
*   current
*   1 Minute
*   5 Minutes
*   15 Minutes
*   30 Minutes
*   1 Hour
*   4 Hours
*   1 Day
*   1 Week
*   1 Month

**STC MA Method**
*   Simple
*   Exponential
*   Smoothed
*   Linear weighted

**STC Price Field**
*   Low/High
*   Close/Close

---

### **Page 42**

# Exit STC Setting

| === EXIT SYSTEM === | |
| :--- | :--- |
| **Use STC Close** | On |
| **Apply On Profit** | On |
| **Apply On Loss** | Off |
| **STC Timeframe** | 15 Minutes |
| **STC K-line Period**| 5 |
| **STC D-line Period**| 3 |
| **STC Slowing Value**| 3 |
| **STC MA Method** | Simple |
| **STC Price Field** | Low/High |
| **STC Shift** | 1 |
| **STC Close Above** | 80.0 |
| **STC Close Below** | 20.0 |
| **STC Top Return** | On |
| **STC Top Return Start**| 10.0 |
| **STC Top Return Distance**| 7.0 |
| **STC Reset** | On |
| **STC Reset Buy Below**| 50.0 |
| **STC Reset Sell Above**| 50.0 |

*   **Use STC Close**: 設置為on時才會使用STC作為出市策略
*   **Apply On Profit**: 設置為on時, exit條件會變成當有營利並同時乎合STC參數
*   **Apply On Loss**: 設置為on時, exit條件會變成當有虧損並同時乎合STC參數
    *   用具體影像的說法是: 用Apply On Profit的STC做TP, 用Apply On Loss做SL, 兩者同時on時則無論TP或SL都以該STC設定出市
*   **STC Close Above & STC Close Below**: 從0-100調整Exit區或大小

---

### **Page 43**

# Exit STC

**(圖表顯示隨機指標(Stochastic Oscillator))**

**出場條件:**
STC的K線超過了 Close Above (80) 或 Close Below (20) 的值，就會平倉。

*   **STC Close Above**: 80.0
*   **STC Close Below**: 20.0

---

### **Page 44**

# Apply On Profit VS Apply On Loss

**(此頁為圖表比較，顯示了「Profit」(盈利) 及 「Loss」(虧損) 兩種情況下的市場圖表和指標圖表，用以說明「Apply On Profit」和「Apply On Loss」的應用情境。) **

---

### **Page 45**

# Exit STC

**(此頁顯示了兩個出場範例)**

**範例 1: Sell Order (賣單)**
*   **出場條件**: K線超過了Close Below (20)值，就出市平倉。
*   **圖中數值**: 18.98 (此為當時K線值)

**範例 2: Buy Order (買單)**
*   **出場條件**: K線超過了Close Above (80)值，就出市平倉。
*   **圖中數值**: 82.56 (此為當時K線值)
page_46.png
S10 COURSE

Exit STC

STC K 線 Close Below (20)

| STC Close Above | 80.0 |
| :--- | :--- |
| **STC Close Below** | **20.0** |

| | | |
| :--- | :--- | :--- |
| A 2022.04.20 20:26:58... | 2022.02.02 00:00:00 S10 v3.00 USD/JPY,M15: Stochastic Cooldown Now... (SELL) | |
| A 2022.04.20 20:26:58... | 2022.02.02 00:00:00 S10 v3.00 USD/JPY,M15: close #9 sell 0.10 USD/JPY at 114.631 at price 114.660 | |
| A 2022.04.20 20:26:58... | 2022.02.02 00:00:00 S10 v3.00 USD/JPY,M15: close #10 sell 0.10 USD/JPY at 114.751 at price 114.660 | |
| 2022.04.20 20:26:58... | 2022.02.02 00:00:00 S10 v3.00 USD/JPY,M15: Sell Order closed: 114.66 | |
| A 2022.04.20 20:26:58... | 2022.02.02 00:00:00 S10 v3.00 USD/JPY,M15: close #11 sell 0.10 USD/JPY at 114.671 at price 114.660 | |
| 2022.04.20 20:26:58... | 2022.02.02 00:00:00 S10 v3.00 USD/JPY,M15: Exit STC: 14.69 | |
| 2022.04.20 20:26:58... | 2022.02.02 00:00:00 S10 v3.00 USD/JPY,M15: SELL Order Closing Now... (Signal TP/STC) | |
| A 2022.04.20 20:26:58... | 2022.02.01 19:33:21 S10 v3.00 USD/JPY,M15: open #11 sell 0.10 USD/JPY at 114.671 ok | |
| A 2022.04.20 20:26:58... | 2022.02.01 17:50:21 S10 v3.00 USD/JPY,M15: open #10 sell 0.10 USD/JPY at 114.751 ok | |

Sell order :
K線超過了Close Below
(20)值,就出市平倉

14.69

---
page_47.png
S10 COURSE

Exit STC

STC Top Return

| | |
| :--- | :--- |
| STC Top Return | On |
| STC Top Return Start | 5.0 |
| STC Top Return Distance | 5.0 |

STC到達 15 以下or 85 以上
就會觸發
然後回升/回落5個distance
就出市

85.6013

| | | |
| :--- | :--- | :--- |
| A 2022.04.21 14:38:44... | 2022.04.14 12:30:00 S10 v3.00 GBP/JPY,M15: Buy Order closed: 164.689 | |
| A 2022.04.21 14:38:44... | 2022.04.14 12:30:00 S10 v3.00 GBP/JPY,M15: close #1667 buy 0.10 GBP/JPY at 164.774 at price 164.689 | |
| 2022.04.21 14:38:44... | 2022.04.14 12:30:00 S10 v3.00 GBP/JPY,M15: Exit STC: 78.75 | |
| 2022.04.21 14:38:44... | 2022.04.14 12:30:00 S10 v3.00 GBP/JPY,M15: BUY Order Closing Now... (Signal TP/STC) | |
| 2022.04.21 14:38:44... | 2022.04.14 11:45:00 S10 v3.00 GBP/JPY,M15: STC Top Return Modified to 83.2 (STC TP) | |
| 2022.04.21 14:38:44... | 2022.04.14 11:45:00 S10 v3.00 GBP/JPY,M15: STC Top Return Activated (STC TP) | |
| A 2022.04.21 14:38:43... | 2022.04.14 09:27:14 S10 v3.00 GBP/JPY,M15: open #1667 buy 0.10 GBP/JPY at 164.774 ok | |

觸發

---
page_48.png
S10 COURSE

Exit STC

STC Top Return

| | | |
| :--- | :--- | :--- |
| A 2022.04.21 14:38:44... | 2022.04.14 12:30:00 S10 v3.00 GBP/JPY,M15: Buy Order closed: 164.689 | |
| A 2022.04.21 14:38:44... | 2022.04.14 12:30:00 S10 v3.00 GBP/JPY,M15: close #1667 buy 0.10 GBP/JPY at 164.774 at price 164.689 | |
| 2022.04.21 14:38:44... | 2022.04.14 12:30:00 S10 v3.00 GBP/JPY,M15: Exit STC: 78.75 | |
| 2022.04.21 14:38:44... | 2022.04.14 12:30:00 S10 v3.00 GBP/JPY,M15: BUY Order Closing Now... (Signal TP/STC) | |
| 2022.04.21 14:38:44... | 2022.04.14 11:45:00 S10 v3.00 GBP/JPY,M15: STC Top Return Modified to 83.2 (STC TP) | |
| 2022.04.21 14:38:44... | 2022.04.14 11:45:00 S10 v3.00 GBP/JPY,M15: STC Top Return Activated (STC TP) | |
| A 2022.04.21 14:38:43... | 2022.04.14 09:27:14 S10 v3.00 GBP/JPY,M15: open #1667 buy 0.10 GBP/JPY at 164.774 ok | |

在 85.6013 觸發了 Top Return (到達85)
調整為 83.2
最後以 78.75 出市 ( 83 回落 5 Distance )

| | |
| :--- | :--- |
| STC Top Return | On |
| STC Top Return Start | 5.0 |
| STC Top Return Distance | 5.0 |

Set STC Top Return 是為了最大化利潤
另外是可以 confirm 真要轉勢先出市

觸發
出市

---
page_49.png
S10 COURSE

STC Top Return ON vs OFF

上圖中, Top Return = On
當STC到達目標區域, 便會
開始記錄最高位置, 並隨著
STC繼續升高而更新
當STC回落到STC Return
Distance設定的數值時出
市

可視作為STC版的trailing

下圖中, Top Return = Off, 當STC到達目標區域, 便會馬上出市, 可視作為STC版的TP或SL

S10 PRO

---
page_50.png
S10 COURSE

Exit STC

Cooldown started

Cooldown Ended

可以開始再入市

STC Reset ( Cooldown )

| | |
| :--- | :--- |
| STC Reset | On |
| STC Reset Buy Below | 50.0 |
| STC Reset Sell Above | 50.0 |

STC cooldown 會在出市
平倉之後就會觸發開始
cooldown

直到K線到達 setting 數
值(50) cooldown 完先可
以再開單

Sell單平倉之後 STC
到 setting 的數值
(50) 可以再入市

STC Reset Sell Above 50

S10 P

### page_51.png

**Exit STC**

**STC Reset (Cooldown)**

`Cooldown完先再開單` (Cooldown finishes before opening new orders)

| Timestamp | Message |
| :--- | :--- |
| 2022.02.04 04:00:04 | S10 v3.00 USDJPY,M15: open #12 buy 0.10 USDJPY at 114.857 ok |
| 2022.02.03 22:00:00 | S10 v3.00 USDJPY,M15: MA Cross Cooldown Ended (BUY) |
| 2022.02.02 01:15:00 | S10 v3.00 USDJPY,M15: Stochastic Cooldown Ended (SELL) |
| 2022.02.02 00:00:43 | S10 v3.00 USDJPY,M15: All Sell Order closed. |
| 2022.02.02 00:00:00 | S10 v3.00 USDJPY,M15: MA Cross Cooldown Now... (SELL) |
| 2022.02.02 00:00:00 | S10 v3.00 USDJPY,M15: Stochastic Cooldown Now... (SELL) |

`Sell完 STC Cooldown` (STC Cooldown after Sell)

`Cooldown完先再開單` (Cooldown finishes before opening new orders)

| Timestamp | Message |
| :--- | :--- |
| 2022.02.14 05:31:07 | S10 v3.00 USDJPY,M15: open #14 sell 0.10 USDJPY at 115.533 ok |
| 2022.02.14 03:00:00 | S10 v3.00 USDJPY,M15: MA Cross Cooldown Ended (SELL) |
| 2022.02.04 06:15:05 | S10 v3.00 USDJPY,M15: Stochastic Cooldown Ended (BUY) |
| 2022.02.04 05:15:05 | S10 v3.00 USDJPY,M15: All Buy Order closed. |
| 2022.02.04 05:15:05 | S10 v3.00 USDJPY,M15: MA Cross Cooldown Now... (BUY) |
| 2022.02.04 05:15:05 | S10 v3.00 USDJPY,M15: Stochastic Cooldown Now... (BUY) |

`Buy完 STC Cooldown` (STC Cooldown after Buy)

S10 COURSE
S10 PRO
### page_01.png

S10 PRO
v4.00
v5.00
Forex Forest
Algorithmic Trading
S10
Expert Advisor
Professional Version
PRO
S10
$0.45056
$0.4
