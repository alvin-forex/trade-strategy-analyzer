Keychain initialization encountered an error: Cannot find module '../build/Release/keytar.node'
Require stack:
- /home/linuxbrew/.linuxbrew/Cellar/gemini-cli/0.35.2/libexec/lib/node_modules/@google/gemini-cli/node_modules/keytar/lib/keytar.js
Using FileKeychain fallback for secure storage.
Loaded cached credentials.
好的，這是從您提供的五個頁面中提取的完整文字內容。

### **Page 1**

```
Forex Forest
Algorithmic Trading

MKD
操作指南 MANUAL
EXPERT ADVISOR
自動交易程序
```

### **Page 2**

```
CONTENT內容

MKD基本介紹.................................................................................................. 2
Flow Chart流程圖.......................................................................................... 3
BASIC SETTING基本設置................................................................................. 4
ENTRY SYSTEM 入市設置.................................................................................. 6
ENTRY SYSTEM – Main主要入市設置.................................................................. 6
Entry System – Direction 入市方向控制設置....................................................... 8
Entry System – Filter 輔助入市設置................................................................... 13
Entry System – Order Management 入市訂單管理.............................................. 17
Martingale System – Geometric Martingale 馬丁格爾策略系統設置....................... 18
Exit System – Exit STC Setting 隨機指標出市設置.............................................. 23
News Filter 新聞過濾......................................................................................... 25
Display & Misc 其他........................................................................................... 26
```

### **Page 3**

```
MKD基本介紹

MKD 是一款自家出品,以多重時間框架為策略的交易程式,以 STC 為基礎入市觸發點,配合方向性指標捕捉大市走向,於走勢作回調時捕捉有利入市點,以達至長線的利潤。
基礎入市原理為 STC 指標,方向性指標為輔助。
Direction indicators (方向性指標)會首先分析大市趨勢走向,當捕捉到有利趨勢後,基礎指標 STC 會接續捕捉有利的入市點,於最有優勢的價格點進行入市。
加入靈活的多重時間框架(MTF),能於趨勢得到判定,並判斷貨幣力量達至高水平後,以轉換 STC 的時間框架,以 special order 迅速入市,以捕捉整個高貨幣力量的趨勢,靈活地達至最佳利潤。

MKD的特點

*   除特別註明外,MKD主要輸入的數值都以Pips作基礎。
*   當MT4連接斷開或重新啟動時,不會丟失任何已設定的入市或平倉位置。
*   用了最新CODING技術,令PC或VPS不會負載過重。
*   使用API技術,可以促進MKD策略方案有效率進行。
*   可以與其他EA和腳本(Scripts)合作。
*   可以使用具有不同時間框架的過濾器。
*   具有價差(Spread)和滑點(Slippage)過濾器,當價差處於過大時,可以限制它們的交易。

MKD使用注意要點

入市機制
先由Direction Control Indicator判斷
入市方向,才交由STC Indicator捕捉入
市位置。
```

### **Page 4**

```
Flow Chart 流程圖

General Setting, Time Mgt, News Mgt
↓
Directional Indicator
(1) AI
(2) MACD
(3a) CCY Power
--- Indicator triggered with --->
Directional Indicator
(3b) CCY Power (high Power)
↓
Trigger Indicator
STC (Normal Order (NO))
↓
Order Placed (NO family)
↓
Trigger Indicator
STC (Special Order (SO))
(Shorter Time Frame)
↓
Order Placed (SO Family)
↓
Exit System & Martingale
↓
If directional indicator "MACD" used,
then Order close with:
(A) MACD exit;
(B) MACD diff exit
↓
If Profit Making
↓
Order Close with TP by
(1) Fix TP in pips
(2) BE
(3) Trailing
(4) STC Exit
If Loss Suffering
↓
If Profit Making
<---
Martingle orders
Follow NO/SO system;
with multi-TF provided
↓
Stop Loss / Stop Out
```

### **Page 5**

```
Basic Setting 基本設置

| | | === Basic Setting === |
| :--- | :--- | :--- |
| H1 | Enter Mode | Per Bar |
| H2 | Enter Mode PerBar Option | Order Level TF |
| H3 | HFT Mode (10x speed up) | Off |
| H4 | Trade Mode | Open and Close Trades |
| H5 | Close Only Mode when above DD% (0=not used) | 15.0 |
| H6 | Reset Trade Mode when below DD% (-1=not used) | 0.0 |

Enter Mode 入市模式

| Per Bar |
| :--- |
| 以每支 bar 收市價格運算,如符合入市條件會在下一支 bar 進行入市,因此每支 bar 只會出現一次入市機會。 |

| Per Tick |
| :--- |
| 每一次價格跳動都進行運算,當符合入市條件便會即時進行入市,因此有機會每支 bar 都會出現多次入市機會。 |

Enter Mode Per Bar Option 每支柱入市模式選項

1.  **Order Level TF:**
    以每層馬丁STC入市時間框架(Core Timeframe)設定作為入市機會計算。
    例子:Order Level的Core Timeframe設定為H4,會以H4 STC尋找入市機會,每次入市時間最少相隔4小時。

2.  **Chart TF:**
    MKD固定時間框架為M5,每次入市時間最少相隔5分鐘。
    例子:Order Level的Core Timeframe設定為H4,同樣會以H4 STC尋找入市機會,但每次入市時間之間最少只相隔5分鐘。

HFT Mode 高頻交易模式

1.  **On:**
    EA每秒不斷運算,即使所選擇交易的貨幣對沒有報價跳動,仍然會不斷運算。

2.  **Off:**
    只會在你選擇交易的貨幣對有報價跳動時才作運算。

高頻交易模式因為較為耗費電腦資源,通常只用於極高​​速入市的策略上,例如抄新聞、又或者利用低時間框架的CCY Power突破入市,以免出現出入市延誤的情況。
```
好的，這就為您提取這些頁面的內容。

**Page 06**

### Trade Mode 交易模式

*   **Open New Trades Only**
    只可進行新單交易
*   **Close Existing Trades Only**
    只可將現有持倉交易平倉,或繼續以馬丁入市直至平倉
*   **Open and Close Trades**
    可進行新單交易或將現有持倉交易平倉

### Close Only Mode when above DD% 當損益比率超過某個百分比時 僅平倉模式

*   當帳戶Drawdown大過指定數值,只可將現有持倉交易平倉,或繼續以馬丁入市直至平倉
*   0 代表不用此功能

### Reset Trade Mode when below DD% 當損益比率低過某個百分比時 重置交易模式

*   當帳戶Drawdown小過指定數值,會重置原來的交易模式
*   -1 代表不用此功能

---

**Page 07**

### Entry System 入市設置

#### Entry STC Signals

| | |
| :--- | :--- |
| **=== ENTRY SYSTEM ===** | **##### Entry Setting #####** |
| Trading Mode | Type C |

1.  **Type A:**
    同一時間只允許單一方向的訂單(包括馬丁),不允許同時進行Buy Order及Sell Order。
2.  **Type C:**
    允許同時進行Buy Order及Sell Order。

### Entry System - Main 主要入市設置

#### Entry STC Signals

| | |
| :--- | :--- |
| **=== ENTRY SYSTEM - MAIN ===** | **=== Entry STC Signals ===** |
| **Stochastic K** | 5 |
| **Stochastic D** | 3 |
| **Stochastic Slowing** | 3 |
| **Stochastic Shift** | 0 |
| **Stochastic Sell Entry** | 70.0 |
| **Stochastic Buy Entry** | 30.0 |
| **Stochastic Top Return Distance (0-not used)** | 10.0 |

*   STC (Stochastic Oscillator)隨機指標,原名%K and %D,又稱 KD 指標,是技術分析中的一種動量分析方法
*   採用超買和超賣的概念,藉由比較收盤價格和價格的波動範圍,預測價格趨勢何時逆轉
*   「隨機」一詞是指價格在一段時間內相對於其波動範圍的位置

| Stochastic K | Stochastic D |
| :--- | :--- |
| - STC %K 線週期 (eg. 預設值 5, 代表計算近 5 支陰陽燭內 的波幅水平高度)<br>- 必須是正整數(1~無限) | - STC %D 線週期 (eg. 預設值 3, 代 表計算近 3 支%K的移動平均數)<br>- 必須是正整數(1~無限)<br>- D線數值不影響效能 |

---

**Page 08**

| Stochastic Slowing | Stochastic Shift |
| :--- | :--- |
| - 控制%D 的內部平滑。(eg. 預設值 3, 代表計算近 3 支%D 的移動平均數)<br>- 必須是正整數 (1~無限) | - %K線指標偏移值<br>- 必須是正整數 (0~無限) |

| Stochastic Sell Entry / Buy Entry | Stochastic Top Return Distance |
| :--- | :--- |
| - 超買 / 超賣指標<br>- 高於超買數值進行 Sell / 低於超賣 數值進行 Buy<br>- 可輸入數值0-100<br>- 可與Stochastic Top Return配合 | - 觸發後回調入市數值<br>- 於高位回調差距達至設定數值才進行入市<br>- 必須是正整數 (0~無限) |

### 例子: Stochastic Sell Entry = 70 , Stochastic Top Return Distance = 10

1.  啟動Stochastic Sell Entry
2.  上到最高位80
3.  高位回調10後入市

---

**Page 09**

### Entry System - Direction 入市方向控制設置

#### Direction Control Setting

| | |
| :--- | :--- |
| **=== ENTRY SYSTEM - DIRECTION ===** | **=== Direction Control Setting ===** |
| Direction of Trades to Open | Open Both directions |
| Direction Holding Minutes | 60 |
| Apply on | Apply on All Orders |

#### Direction of Trades to Open 入市方向開放模式:

1.  Buy Only單買方向模式
2.  Sell Only單賣方向模式
3.  Open Both direction買賣雙向模式

#### Direction Holding Minutes 入市方向持續時間

*   保持入市方向持續時間 (以分鐘計算)
*   要MACD·Power及AI都相同方向才開始計算holding minutes
*   Holding minutes期間如其中一個filter有改變,入市方向仍然不變
*   直至3個filter都轉為反方向,入市方向才改變
*   必須為正整數(0~無限)

#### 例子:

Holding Minutes = 60 , MACD = ON , AI = ON , CCY Power = ON

| | Time | MACD | AI | Power | Entry Direction Holding |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **First 60 mins Start** | 11:00 | No | No | Up | Holding Minutes not start |
| | 11:15 | Up | Up | Up | Up trend |
| | 11:30 | Up | Up | Down | Still Up trend |
| | 11:45 | Down | Down | Up | Still Up trend |
| **Another 60 mins Start** | 11:50 | Down | Down | Down | Change to Down trend |

#### Apply On 入市方向應用於:

1.  Apply on 1st Order: 只用於第一張Order
2.  Apply on All Orders: 應用於所有Order

---

**Page 10**

### AI Direction Control

| | |
| :--- | :--- |
| **=== ENTRY SYSTEM - FILTER ===** | **=== AI Direction Control ===** |
| AI Source | AI 1 |
| Use AI Direction Control | On |

*   以貨幣力學、技術指標、背馳以及國家新聞等資訊,預測貨幣未來40小時的走勢
*   每4小時更新一次
*   可以進行Back Test(可Back Test時段請參考EA About內提示,非指定BT時期內,均顯示No Trend, 即期間不允許進行任何交易)

#### AI Source 運算模式

| AI | |
| :--- | :--- |
| **AI 1** | Identify Uptrend / Downtrend 預測升市/ 跌市 |
| **AI 2** | Identify Uptrend / Downtrend / No trend 預測升市/ 跌市/ 橫行市 |

*   Uptrend: 只會進行Buy Order入市
*   Downtrend:只會進行Sell Order入市
*   No trend: 不進行入市

#### Use AI Direction Control 以AI作為入市方向控制

1.  **On:** 啟用
2.  **Off:** 關閉

### Power Direction Control

| | |
| :--- | :--- |
| **---** | **--- Power Direction Control ---** |
| Use Power Direction Control | On |
| Power Timeframe | D1 |
| Power Period | 10 |
| Trade If Buy Power Over | 0.0 |
| Trade If Sell Power Over | 0.0 |
| Special Order If Buy Power Over | 4.0 |
| Special Order If Sell Power Over | 4.0 |

*   運用貨幣力學分析各貨幣之間的強弱走勢, 如Chart非28對貨幣對, Power Filter會如常運行, 但要注意非 常用8隻貨幣, Power只會顯示0, 無法正確分析走勢, 在此情況下請關掉Power Filter
*   此項功能並不能進行BT

#### Use Power Direction Control 以貨幣力學指標作為入市方向控制:

1.  **On:** 啟用
2.  **Off:** 關閉
好的，這就為您提取這些頁面的內容。

### page_11.png

**Power Timeframe 時間框架計算**

| | | | | |
| :--- | :--- | :--- | :--- | :--- |
| 1. Current | 2. M1 | 3. M5 | 4. M15 | 5. M30 |
| 6. H1 | 7. H4 | 8. D1 | 9. W1 | 10. MN1 |

**Power Period 貨幣強弱計算時期**
*   **陰陽燭計算數量**
*   必須輸入正整數 (1~無限)

**Trade if Buy / Sell Power Over**
*   應用於Normal Order
*   兩貨幣強弱相差達至此數值才觸發入市
*   可輸入數值由0至9

**Special Order if Buy / Sell Power Over**
*   應用於Special Order
*   兩貨幣強弱相差達至此數值才觸發入市
*   可輸入數值由0至9

**請留意**
*   利用CCY Power Indicator檢視貨幣對的強弱指數
*   Timeframe與Period的部份建議要與EA內Setting相同,才可獲得相對的數值
*   Market Watch需要顯示28個貨幣對

**CCY Power Indicator**
| Variable | Value |
| :--- | :--- |
| **=== Basic Setting ===** | |
| **Display Mode** | Chart CCY Power |
| **Chart Symbol (close price)** | 1 Day |
| **Period** | 5 |
| **=== Display ===** | |
| **Show Chart Symbol only** | Off |
| **Show Vertical Line** | On |
| **Strong Line** | 8.0 |
| **Weak Line** | 2.0 |
| **Show Power Ranking Panel** | No |

*   強勢貨幣NZD的數值是5.86；弱勢貨幣JPY的數值是1.14，兩者之間的差距是4.71(四捨五入後)；符合設定範圍；此情況可觸發入市

---
### page_12.png

**MACD Direction Control**
| 參數 | 設定 |
| :--- | :--- |
| Use MACD Direction Control | On |
| MACD Timeframe | H4 |
| MACD Fast Period | 12 |
| MACD Slow Period | 26 |
| MACD Signal Period | 9 |
| Minimum Fast/Slow Difference in Pips | 2.0 |
| Use MACD Diff Exit | Off |
| MACD Diff Strat in Pips | 5.0 |
| MACD Diff Distance in Pips | 0.5 |
| Use MACD Signal Close | Off |

*   MACD中文名是「平滑異同移動平均線」(Moving Average Convergence & Divergence)
*   透過計算「收盤時股價或指數變化的指數移動平均值(EMA)」之間的離差程度(DIF)而來,用來確定波段漲幅並找到買賣點
*   一般MACD以兩線及柱作顯示,但在Forex Forest自家研發的EA下,只顯示一線及柱

**Use MACD 以 MACD 作為入市輔助**
*   **1. On:** 啟用
*   **2. Off:** 關閉

**MACD Timeframe 時間框架計算**
| | | |
| :--- | :--- | :--- |
| 1. H4 | 2. D1 | 3. W1 |

*   **Fast MACD Period** 快線平均線
*   **Slow MACD Period** 慢線平均線
*   **Signal MACD Period** 訊號線
*   **陰陽燭計算數量**
*   必須輸入正整數(1~無限)

---
### page_13.png

**MACD 入市應用例子:**
*   藍柱高於紅線 = Buy Signal
*   紅線高於藍柱 = Sell Signal

**Minimum Fast / Slow Difference in Pips 差價差距**
*   線與柱之間的差距需要達至設定數值才進行入市
*   必須是正整數(0~無限)

**Use MACD Diff Exit 以差價差距出市**
1.  **On:** 啟用 (必須要啟用MACD Direction Control才能運作)
2.  **Off:** 關閉

**MACD Diff Strat in Pips 啟動差價差距出市的起步距離**
*   線與柱之間的差距達至設定數值便觸發
*   必須是正整數(0~無限)

**MACD Diff Distance in Pips 差價差距收窄範圍**
*   當線與柱之間的差距收窄至設定數值便會進行出市
*   必須是正整數(0~無限)

---
### page_14.png

**Use MACD Signal Close 以 MACD 訊號出市**
*   不論於盈利或虧損下都會進行出市
*   MACD轉向反方向便進行出市
1.  **On:** 啟用
2.  **Off:** 關閉

**Entry System - Filter 輔助入市設置**

**Volatility Filter**
| 參數 | 設定 |
| :--- | :--- |
| **=== ENTRY SYSTEM - FILTER ===** | **=== Volatility Filter ===** |
| Use Volatility Ranking | On |
| Volatility Timeframe | M30 |
| Volatility Period | 5 |
| Trade From x Rank | 1 |
| Trade Until x Rank | 5 |

*   用以顯示 28 個貨幣對波動值及排名, 如Trading Account不提供完整28對貨幣, 為免計算結果變為錯誤參考, Volatility Filter會自動關掉失效, 直至EA重啟
*   方便從中篩選適合波幅的貨幣對進行入市
*   此項功能並不能進行BT

**Use Volatility Ranking 以波動性排行作為入市輔助**
1.  **On:** 啟用
2.  **Off:** 關閉

**Volatility Timeframe 時間框架計算**
| | | | | |
| :--- | :--- | :--- | :--- | :--- |
| 1. Current | 2. M1 | 3. M5 | 4. M15 | 5. M30 |
| 6. H1 | 7. H4 | 8. D1 | 9. W1 | 10. MN1 |

**Volatility Period 波動性計算時期**
*   **陰陽燭計算數量**
*   必須輸入正整數(1~無限)

**Trade From x Rank / Trade Until x Rank 以此排名範圍內作入市**
*   可輸入數值由1至28

---
### page_15.png

**請留意**
*   利用Indicator Volatility Table檢視28個貨幣對的數值與排名
*   Timeframe與Period的部份建議要與EA內Setting相同,才可獲得相對的數值
*   Market Watch需要顯示 28 個貨幣對

**Indicator Volatility Table**
| Variable | Value |
| :--- | :--- |
| **=== SETTING ===** | |
| Volatility Timeframe | 30 Minutes |
| Volatility Period | 5 |
| Volatility Shift | 1 |
| CCY(s) | AUD,CAD,CHF,EUR,GBP,JPY,NZD,USD |
| Symbol Suffix (empty-auto detect) | |
| **=== DISPLAY ===** | |
| Corner-on | Left upper chart corner |
| Offset X | 00 |
| Offset Y | 0 |
| Font Size (0-auto size) | 0 |
| Update interval (ms) | 1000 |

**Correlation Filter**
| 參數 | 設定 |
| :--- | :--- |
| **=== ENTRY SYSTEM - FILTER ===** | **=== Correlation Filter ===** |
| Use Correlation Filter | Off |
| Correlation Timeframe | H1 |
| Correlation Period | 50 |
| Maximum Correlation | 70.0 |
| Minimum Correlation | 0.0 |

*   分析28個貨幣對的走勢相連性, 即兩個貨幣對之間的同步性
*   就算Chart跟交易中的訂單非28對貨幣對,Correlation Filter依然能有效分析走勢相連性
*   正數值越高同步值越高;負數值越高逆向值越高
### page_16.png

**Use Correlation Filter 以貨幣相關性過濾作為入市輔助**

*   **1. On:** 啟用
*   **2. Off:** 關閉

**Correlation Timeframe 時間框架計算**

*   1. Current
*   2. M1
*   3. M5
*   4. M15
*   5. M30
*   6. H1
*   7. H4
*   8. D1
*   9. W1
*   10. MN1

**Correlation Period 相聯性計算時期**

*   陰陽燭計算數量
*   必須輸入正整數 (1~無限)

**Maximum Correlation / Minimum Correlation 相關性最高值 / 相關性最低值**

*   可輸入數值由0至100
*   輸入之數值已包括正值及負值 (eg. 70已代表 +70 及 -70)
*   相關性於此數值以外的貨幣對不作交易
*   此項功能並不能進行BT

**請留意**
利用Forex Correlation Smart Indicator檢視28個貨幣對的相聯性

**Forex Correlation Smart Indicator**
*   Timeframe與Period的部份建議要與EA內Setting相同, 才可獲得相對的數值
*   Market Watch需要顯示28個貨幣對

| Variable | Value | *** SETTING *** |
| --- | --- | --- |
| **Correlation Timeframe** | **1 Hour** | 建議要與 EA 內 Setting 相同 |
| **Correlation Period** | **50** | |
| **Correlation Shift** | **0** | |
| **Symbol(s)** | **AUDCAD,AUDCHF,AUDJPY,AUDNZD,AUDSGD...** | |
| **Correlation Limit** | **70.0** | |

---
### page_17.png

**Forex Correlation Smart Indicator**
USDJPY 與 AUDJPY 的貨幣相關性數值為+91.46

**Forex Correlation Smart Indicator**
USDCAD 與 AUDJPY 的貨幣相關性數值為-88.59

---
### page_18.png

**Entry System - Order Management 入市訂單管理**

**Order General Setting**

| *** ENTRY SYSTEM - ORDER MANAGEMENT *** | *** Order General Setting *** |
| :--- | :--- |
| **Buy Order ID (Magic Number)** | 88 |
| **Buy Order ID (Comment)** | MKD Buy |
| **Sell Order ID (Magic Number)** | 77 |
| **Sell Order ID (Comment)** | MKD Sell |
| **Maximum Spread in Pips** | 3.0 |
| **Maximum Slippage in Pips** | 3.0 |
| **Exit Max Spread Filter** | Off |

**Magic Number (Buy / Sell) 魔術編號**
*   每次開單EA都會將Magic Number記錄, 平倉時會根據Magic Number來確認訂單
*   必須為正整數 (0~無限)
*   如不輸入數值, 會自動轉為0

**Order Comment (Buy / Sell) 訂單備註**
*   每次開單EA都會將Comment記錄, 平倉時會根據Comment來確認訂單
*   最多只能輸入28個字元
*   可不輸入任何資料

**Max Spread in Pips 容許最大價差**
*   價差是指貨幣對的買入價和賣出價之間的差額
*   設定最大價差數值, 當價差大於設定數值, 不會進行入市
*   必須為正整數(0~無限)

**Max Slippage in Pips 容許最大滑價**
*   滑價是指交易的預期價格和交易執行價格之間的差額
*   設定最大滑價數值, 當滑價大於設定數值, 不會進行入市
*   必須為正整數(0~無限)

**Exit Max Spread Filter 出市最大價差過濾器**
*   價差是指貨幣對的買入價和賣出價之間的差額
*   設定最大價差數值, 當價差大於設定數值, 不會進行出市
*   必須為正整數(0~無限)

---
### page_19.png

**Martingale System - Geometric Martingale 馬丁格爾策略系統設置**

*   起源於賭場的交易策略
*   主要原理為將每次虧損的注碼加倍, 持續進行多次逆勢加注, 直到出現回調時連本帶利離場

**馬丁 Buy Order**
**馬丁 Sell Order**

**Special Order & Normal Order**

**Special 1st Order**

| --- | --- |
| --- | **(Special 1st Order)** --- |
| **Core Timeframe** | M5 |
| **Lot Size (0=not used)** | 0.01 |
| **Breakeven Distance in Pips (0=not used)** | 0.0 |
| **Fixed Take Profit in Pips (0=not used)** | 0.0 |
| **Fixed Stop Loss in Pips (0=not used)** | 0.0 |
| **Trailing Start in Pips (0=not used)** | 10.0 |
| **Trailing Distance in Pips (0=not used)** | 10.0 |

*   當貨幣對強弱指數(Power Diff)出現較大的差距時, 往往會出現上升或下跌的顯著波幅, 在較大Timeframe上的STC會較難進入超買/超賣範圍, 令開單條件未能達到而錯失入市機會
*   於顯著的上升或下跌趨勢中, 不同Timeframe下亦會有超買/超賣範圍
*   Special Order可用較小Timeframe STC(例如M1,M5等)於此時進行入市

---
### page_20.png

**Core Timeframe 時間框架計算**
*   M1
*   M5
*   M15

**Lot Size 入市手數**
*   每次入市的手數
*   必須為正整數(0~無限)
*   0代表不用此層數入市

**Special 2nd Order**

| --- | --- |
| --- | **(Special 2nd Order)** --- |
| **Core Timeframe** | M5 |
| **Lot Size (0=not used)** | 0.0 |
| **Effective Pipstep** | 5.0 |
| **Breakeven Distance in Pips (0=not used)**| 0.0 |
| **Fixed Take Profit in Pips (0=not used)** | 0.0 |
| **Fixed Stop Loss in Pips (0=not used)** | 0.0 |
| **Trailing Start in Pips (0=not used)** | 10.0 |
| **Trailing Distance in Pips (0=not used)** | 10.0 |
| **Next Effective Pipstep** | 10.0 |

**Effective Pipstep 有效點差距**
*   與Special 1st Order相距設定數值便觸發入市
*   必須為正整數(0~無限)

**Next Effective Pipstep 下一個有效點差距**
*   相距設定數值便觸發第一層Normal Order以馬丁層數入市
*   必須為正整數(0~無限)

**注意:**
*   使用Power的情況下, Special 1st Order、Special 2nd Order或Normal 1st Order必須大於0
*   所有Order必須順序連接, 如只想開 1 層Special Order, 請跳過Special 1st Order並設定Special 2nd Order
Page 21
Normal Order

| --- (1st Order) --- | |
| :--- | :--- |
| Core Timeframe | H4 |
| Lot Size | 0.01 |
| Breakeven Distance in Pips (0-not used) | 0.0 |
| Fixed Take Profit in Pips (0-not used) | 0.0 |
| Fixed Stop Loss in Pips (0-not used) | 0.0 |
| Trailing Start in Pips (0-not used) | 5.0 |
| Trailing Distance in Pips (0-not used) | 2.0 |

* 以大Timeframe STC作為入市指標(例如H1,H4,D1等)
* 可配搭其他Direction Control及Filter來輔助入市,並以馬丁方式一層層逆勢開單

Core Timeframe 時間框架計算
M30, H1, H4, D1

Lot Size 固定入市手數
* 每次入市的手數
* 必須為正整數(0-無限)
* 在不使用Power的情況下,1st Normal Order必須大於 0,否則不能開單

| --- (6th+ Order) --- | |
| :--- | :--- |
| Core Timeframe | H1 |
| Lot Size | 0.12 |
| Effective Pipstep | 25.0 |
| Breakeven Distance in Pips (0-not used) | 0.0 |
| Fixed Take Profit in Pips (0-not used) | 0.0 |
| Fixed Stop Loss in Pips (0-not used) | 0.0 |
| Trailing Start in Pips (0-not used) | 40.0 |
| Trailing Distance in Pips (0-not used) | 0.0 |

Effective Pipstep
* 與上一層相距設定數值便觸發入市
* 必須為正整數 (0~無限)
* *Normal Order第六層及之後層數都以第六層的設定值計算

Page 22
Exit System in each Order Level

| | |
| :--- | :--- |
| Breakeven Distance in Pips (0~not used) | 0.0 |
| Fixed Take Profit in Pips (0~not used) | 0.0 |
| Fixed Stop Loss in Pips (0~not used) | 0.0 |
| Trailing Start in Pips (0~not used) | 5.0 |
| Trailing Distance in Pips (0~not used) | 2.0 |

Breakeven Distance in Pips 盈虧平衡止損
* 將止損位設定至與開單位價相近,以消除成本虧損的風險
* 必須為正整數 (0~無限)
* Breakeven觸發位價相等於設置數值的兩倍
* 觸發後回調數值等於設置數值便推行出市

Breakeven 例子:
Breakeven Distance in pips = 5
價格上升 10pips 時觸發 Breakeven 線出現
5 x2 = 10Pips
Breakeven
如價格回調至 Breakeven 線便進行出市
*平倉位置不合根據價格持續上升而改變

Fixed Take Profit in Pips 固定獲利設定
* 固定獲利數值
* 必須為正整數 (0~無限)

Page 23
Fixed Stop Loss in Pips 固定止損設定
* 固定止損數值
* 必須為正整數 (0~無限)

Trailing Start in Pips 啟動移動止損的起步距離
* 入市後如浮動達到此數值便觸發
* 必須為正整數 (0~無限)

Trailing Distance in Pips 平倉位置與現價距離
* 價格回調多少便進行平倉
* 必須為正整數 (0~無限)

Trailing 例子:
Trailing Start in pips = 10 | Trailing Distance in pips = 2
Trailing Start
Distance 2pips
10 pips
入市後浮動達到 10 pips 便啟動 Trailing 功能
Distance 2pips
觸發 Trailing Start 後, 持反方向回調 2 pips 便會平倉
*平倉位置會根據價格持續上升而改變

**注意:以上出市設置均以平均Pips數計算

Page 24
Trailing VS Breakeven
Trailing 的平倉位置會根據現價不斷地調整
Breakeven 的平倉位置是固定不變的

Exit System - Exit STC Setting 隨機指標出市設置

| --- EXIT SYSTEM --- | --- Exit STC Setting --- |
| :--- | :--- |
| Use Exit Stochastic | On |
| Stochastic K | 5 |
| Stochastic D | 3 |
| Stochastic Slowing | 3 |
| Stochastic Shift | 0 |
| Stochastic Sell Exit | 40.0 |
| Stochastic Buy Exit | 60.0 |
| Stochastic Top Return Distance | 10.0 |
| Trailing Distance after Exit Stochastic in Pips (0-not used) | 0.5 |

Use Exit Stochastic 使用STC作為出市:
1. On: 啟用 2. Off: 關閉

Stochastic K / D / Slowing
* 必須為正整數(1~無限)

Stochastic Shift
* %K線指標偏移值
* 必須為正整數(0~無限)

Page 25
Stochastic Sell Exit / Buy Exit
* 超買/超賣指標
* 超買/超賣指標達至設定數值便觸發出市
* 必須為 0-100
* 可與Stochastic Top Return配合

Stochastic Top Return Distance
* 觸發Stochastic Sell Exit / Buy Exit後啟動
* 於高位回調差距(Stochastic)達至設定數值才進行出市
* 必須為正整數(0-無限)

請留意
* 採用 STC Exit,只會於有盈利情況下推行出市
* STC Exit的Timeframe,是根據Enter的Timeframe進行出市。
例如:現在已開到第 6 層馬丁 (H4),出市會同樣使用H4 作出Stochastic Exit 的計算

Trailing Distance after Exit Stochastic in Pips
* 觸發 Stochastic Exit 後啟動
* 於高位回調差距(Pips)達至設定數值才進行出市
* 必須為正整數(0-無限)
page_26.png
### News Filter 新聞過濾

| 參數 | 值 |
| :--- | :--- |
| Related Currency (eg. EUR,USD) (Empty=Cu... | |
| High Importance (Red) | On |
| High (Pause x mins before) | 60 |
| High (Pause x mins after) | 60 |
| Non-Farm Payroll | On |
| Non-Farm (Pause x mins before) | 180 |
| Non-Farm (Pause x mins after) | 180 |
| Speaks (Orange) | On |
| Speaks (Pause x mins before) | 180 |
| Speaks (Pause x mins after) | 180 |
| Draw News Lines | On |

*   根據經濟新聞的發佈設立非交易時段
*   News filter只限制直盤入市,不會限制馬丁加單以及平倉

#### Related Currency 相關貨幣
*   不輸入貨幣代表只應用於當前圖表貨幣 (eg. 當前圖表貨幣對的貨幣是GBPJPY, 就只會使用 GBP 跟JPY的新聞)
*   如輸入貨幣 GBP, 代表只影響GBP相關貨幣對

#### High Important (Red) 重要新聞 (紅色)
*   禁止高度重要指標發佈前後下單

#### Non-farm Payout 非農就業數據
*   禁止非農就業數據發佈前後下單

#### Speaks (Orange) 演講 (橙色)
*   禁止發佈重要演講前後下單

#### Draw News Lines 繪畫新聞線
*   於圖表上顯示新聞發佈時間

page_27.png
### Display & Misc 其他

| 參數 | 值 |
| :--- | :--- |
| Show Panel | Off |
| Send BED Signal | Off |
| Display Stochastic on Bar | Off |
| Export Summary Report | Off |
| Display Trade Mode | On Chart Comment |
| Display Remark | |

#### Show Panel 面板:
*   提供啟動面板功能, 可以獨立選擇啟動與否
*   會於交易圖表左上角出現控制面板
*   會於交易圖表左下角顯示Volatility / CCY Power / AI signal等資訊

#### 左上角控制面板顏色顯示代表:
*   藍色: Buy & Sell Mode (沒有啟動任何Direction Filter情況時)
*   黑色: No trend
*   綠色: Buy Only
*   紅色: Sell Only

#### 左下角資訊顏色顯示代表:
*   黑色: Both Direction
*   綠色: Buy Only
*   紅色: Sell Only
*   灰色: No Trade

page_28.png
### Send BED Signal 發送BED訊號:
*   提供啟動發送BED訊號選項
*   BED Signal即顯示Balance及Equity資料
*   只供回測用

### Display Stochastic on Bar 顯示STC於當前圖表上:
*   資料以白色文字顯示

### Export Summary Report 匯出交易記錄報表:
*   提供啟動匯出交易記錄報表選項
*   只供回測用

### Display Trade Mode 顯示交易模式:
*   No Display: 交易模式不會顯示
*   On Chart Comment: 交易模式將顯示在圖表的左上角並在備註旁邊
*   On Chart Center: 交易模式將顯示在圖表的中央位置

### Display Remark 顯示備註:
*   將輸入的備註顯示在圖表的左上角
