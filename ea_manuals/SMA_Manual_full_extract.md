好的，這就為您提取前 5 頁的內容。

**Page 01**

Forex Forest®
Algorithmic Trading

SMA
操作指南

EXPERT ADVISOR
自動交易程序

---
**Page 02**

**CONTENT 內容**

| 主題 | 頁碼 |
| --- | --- |
| SMA 基本介紹 | 2 |
| Flow Chart 流程圖 | 3 |
| Basic Setting 基本設置 | 4 |
| Entry System 入市設置 | 5 |
| Entry System – Main 主要入市設置 | 6 |
| Entry System – 1ST ORDER 首單輔助入市設置 | 8 |
| Volatility Filter | 8 |
| Correlation Filter | 10 |
| Entry System-MARTINGALE 馬丁格爾策略系統入市過濾 | 12 |
| Exit System 出市設置 | 18 |
| News Filter 新聞過濾 | 24 |
| Display & Misc 其他 | 25 |

---
**Page 03**

**SMA基本介紹**

SMA是一個自家出品,以捕捉中長線利潤為策略的交易程式,內置智能加單系統。

基礎入市原理為維加斯通道,當多個通道同時向上或向下運行,並且表示方向趨勢一致,則表示中期趨勢已經確立並相對穩定發展,程式就會進行交易,直至趨勢完結賺取豐厚利潤。

出市原理亦能以MA線構成的通道作為標準,確保策略可以完整賺取大市趨勢帶來的利潤。

**SMA的特點**

*   除特別註明外,SMA主要輸入的數值都以Pips作基礎。
*   當MT4連接斷開或重新啟動時,不會丟失任何已設定的入市或平倉位置。
*   用了最新CODING 技術,令PC或VPS不會負載過重。
*   使用API技術,可以促進SMA策略方案有效率推行。
*   可以與其他EA和腳本(Scripts)合作。
*   可以從檢測多個振盪指標,選擇開單位置。
*   可以啟用具有不同周期的2個移動平均值作為趨勢過濾器,例如MA 200和MA 34。
*   具有價差(Spread)和滑點(Slippage)過濾器,當價差處於過大時,可以限制它們的交易。

**SMA使用注意要點**

**入市機制**
首張單入市後,馬丁類數訂單需要符合馬丁 Filter條件才會進行入市

---
**Page 04**

**Flow Chart 流程圖**

1.  **General Setting, Time Mgt, News Mgt, Volatility Filter, Correlation Filter**
2.  **Direction Signal by MA Indicators Line Up (6 nos.)**
    *   **Buy Signal:** Enter MA > Killer MA > Wave MAs (3 nos.) > Lower / Upper MA
    *   **Sell Signal:** Lower/Upper MA > Wave Mas (3 nos.) > Killer MA > Enter MA
3.  **Order Placement Triggered by Entry MA**
    *   **Buy Order Place:** Enter MA > all other MAs
    *   **Sell Order Place:** Enter MA < all other MAs
    *   **Assistant Control:** AI Direction Control
4.  **Exit System & Martingale**
5.  **If Profit Making**
    *   **Order Close with TP by**
        *   (1) Fix TP in dollars
        *   (2) Breakeven in dollars
        *   (3) Trailing in dollars (w. or w/o Dyn TP)
        *   (4) Dyn TP (w. or w/o Trailing)
    *   **Assistant Control**
        *   if Profit Making Contact
        *   (1) Pip Step
        *   (2a) RSI Filter
        *   (2b) Band Filter
6.  **If Loss Suffering**
7.  **Stop Loss / Stop Out**

---
**Page 05**

**Basic Setting 基本設置**

| 參數 | 值 |
| --- | --- |
| Direction of Trades to Open | Open Both direction |
| Trade Mode | Open and Close Trades |
| Close Only Mode when above DD% (0=not used) | 15.0 |
| Reset Trade Mode when below DD% (-1=not used) | 0.0 |
| Enter Mode | Per Bar |
| HFT Mode (10x speed up) | Off |

**Close Only Mode when above DD% 當損益比率超過某個百分比時進入僅平倉模式**

*   當圖表Drawdown大過指定數值,只可將現有持倉交易平倉,或繼續以馬丁入市直至平倉
*   0 代表不用此功能

**Reset Trade Mode when below DD% 當損益比率低過某個百分比時進入重置交易模式**

*   當帳戶Drawdown小過指定數值,會重置原來的交易模式
*   -1代表不用此功能

**Trade Mode 交易模式**

*   **Open New Trades Only**: 只可進行新單交易
*   **Close Existing Trades Only**: 只可將現有持倉交易平倉或繼續以馬丁入市直至平倉
*   **Open and Close Trades**: 可推行新單交易、加開馬丁單或將現有持倉交易平倉

**Enter Mode 入市模式**

*   **Per Bar**: 以每支bar收市價格運算,如符合入市條件會在下一支bar進行入市,因此每支bar只會出現一次入市機會。
*   **Per Tick**: 每一次價格跳動都進行運算,當符合入市條件便會即時進行入市,因此有機會每支bar都會出現多次入市機會。

### page_06.png

**HFT Mode 高頻交易模式**

1.  **On:** EA每秒不斷運算,即使所選擇交易的貨幣對沒有報價跳動,仍然會不斷運算
2.  **Off:** 只會在所選擇交易的貨幣對有報價跳動時才作運算

高頻交易模式因較為耗費電腦資源,通常只用於極高速入市的策略上,例如炒新聞或利用低時間框架的CCY Power突破入市,以免出現出入市延誤的情況。

**Entry System 入市設置**

| | |
| :--- | :--- |
| === ENTRY SYSTEM === | ##### Entry Setting ##### |
| Trading Mode | Type C |

**Trading Mode**

1.  **Type A:** 同一時間只允許單一方向的訂單 (包括馬丁),不允許同時進行buy Order及Sell Order。
2.  **Type B:** 同一時間只允許單一方向的訂單 (包括馬丁),不允許同時進行buy Order及Sell Order; 平倉後下次入市單的方向必定為反方向。
3.  **Type C:** 允許同時進行buy Order及Sell Order。
### page_07.png

**Entry System - Main 主要入市設置**

| | |
| :--- | :--- |
| === ENTRY SYSTEM - MAIN === | === Entry MA Signals === |
| Basic MA Timeframe | H1 |
| Lower MA Trend | 144 |
| Upper MA Trend | 169 |
| Wave MA | 34 |
| Killer MA | 12 |
| Basic MA Shift | 1 |
| Follow Lower-Upper MA Direction | Off |
| Close by Lower-Upper MA Direction | Off |
| ... | Open order if Enter Ma Line(H1=60) touch th |
| Enter MA Timeframe | H1 |
| Enter Ma Line Period | 3 |
| Enter Ma Shift | 1 |

*   主要入市以「維加斯通道Vegas Tunnel」作中長期趨勢底氣
*   「維加斯通道」所採用移動平均線的指標為EMA,以EMA144和EMA169作為“通道區”

**Basic MA / Enter MA Timeframe 時間框架計算**

1.  M30
2.  H1
3.  H4
4.  D1

**Basic MA / Enter MA Shift**

*   必須是正整數 (0~無限)
*   例: Shift=0,代表取用以現價bar的數據作為計算基礎
*   例: Shift=1,代表取用以現價bar向左第1支bar的數據作為計算基礎;如此類推

**Follow Lower-Upper MA Direction**

1.  **On:**
    *   必須根據Lower / Upper MA線排列才觸發入市
    *   MA144 > MA169 = Buy; MA144 < MA169 = Sell
2.  **Off:**
    *   不必根據Lower / Upper MA線排列都可以觸發入市
### page_08.png

**入市訊號例子**

**Buy Order**

1.  Killer MA > Wave MA > Lower & Upper MA
2.  (ChartTF) Prev Close > Killer MA
3.  (ChartTF) Prev Low < Enter MA

**Sell Order**

1.  Killer MA < Wave MA < Lower & Upper MA
2.  (ChartTF) Prev Close < Killer MA
3.  (ChartTF) Prev High > Enter MA

**Close by Lower-Upper MA Direction**

1.  **On:**
    *   當Lower / Upper MA線排列與入市單方向不一致便進行平倉
2.  **Off:**
    *   不使用此功能作出市
### page_09.png

**Entry System - 1ST ORDER 首單輔助入市設置**

| | |
| :--- | :--- |
| === ENTRY SYSTEM - FILTER === | === AI Direction Control === |
| AI Source | AI 1 |
| Use AI Direction Control | On |

**AI Direction Control**

*   以貨幣力學、技術指標、背馳以及國家新聞等資訊,預測貨幣未來40小時的走勢
*   每4小時更新一次
*   可用於Back Test (可Back Test時期請參考EA About內提示)

**AI Source 運算模式**

| | |
| :--- | :--- |
| **AI 1** | Identify Uptrend / Downtrend 預測升市 / 跌市 |
| **AI 2** | Identify Uptrend / Downtrend / No trend 預測升市 / 跌市 / 橫行市 |

*   Uptrend: 只會進行 Buy Order 入市
*   Downtrend: 只會進行 Sell Order 入市
*   No Trend: 不進行入市

**Use AI Direction Control 以AI作為入市方向控制**

1.  **On:** 啟用
2.  **Off:** 關閉

**Volatility Filter**

| | |
| :--- | :--- |
| === ENTRY SYSTEM - FILTER === | === Volatility Filter === |
| Use Volatility Ranking | On |
| Volatility Timeframe | M30 |
| Volatility Period | 5 |
| Trade From x Rank | 1 |
| Trade Until x Rank | 5 |

*   用以顯示28個貨幣對波動值及排名
*   用以篩選合適波幅的貨幣對進行入市
*   此項功能並不能進行BT
### page_10.png

**Use Volatility Ranking 以波動性排行作為入市輔助**

1.  **On:** 啟用
2.  **Off:** 關閉

**Volatility Timeframe 波動性時間框架**

| | | | | |
| :--- | :--- | :--- | :--- | :--- |
| 1. Current | 2. M1 | 3. M5 | 4. M15 | 5. M30 |
| 6. H1 | 7. H4 | 8. D1 | 9. W1 | 10. MN1 |

**Volatility Period 波動性計算周期**

*   陰陽燭計算數量
*   必須輸入正整數 (1~無限)

**Trade From x Rank / Trade Until x Rank 以此排名範圍內作入市**

*   可輸入的由1至28

**請留意**

可利用Indicator Volatility Table檢視28個貨幣對的數值與排名

*   Timeframe與Period的部份建議要與EA內Setting相同,才可獲得相對的數值
*   Market Watch需要顯示28個貨幣對

| Rank | Symbol | Volatility(pips) |
| :--- | :--- | :--- |
| 1 | EURNZD | 127.00 |
| 2 | EURAUD | 119.80 |
| 3 | CHFJPY | 119.20 |
| 4 | GBPNZD | 118.70 |
| 5 | GBPAUD | 114.00 |
| 6 | EURCAD | 96.10 |
| 7 | GBPCAD | 91.60 |
| ... | ... | ... |
| 12 | USDJPY | 79.80 |
| 13 | GBPCHF | 79.40 |
| 14 | GBPJPY | 75.40 |
| 15 | AUDJPY | 72.20 |
| 16 | NZDJPY | 68.80 |
| 17 | CADJPY | 61.80 |
| 18 | USDCHF | 47.20 |
| 19 | USDCAD | 40.80 |
| 20 | NZDUSD | 33.20 |
| 21 | AUDUSD | 32.80 |
| 22 | NZDCAD | 29.20 |
| 23 | AUDCAD | 27.80 |
| 24 | NZDCHF | 24.20 |
| 25 | AUDCHF | 23.80 |
| 26 | CADCHF | 22.00 |
| 27 | AUDNZD | 20.20 |
| 28 | EURGBP | 18.80 |

只有第 1 位至第 5 位貨幣對才會觸發交易

**Indicator Volatility Table**

| Variable | Value |
| :--- | :--- |
| **--- SETTING ---** | |
| Volatility Timeframe | 30 Minutes 建議要與 EA 內 Setting 相同 |
| Volatility Period | 5 |
| Volatility Shift | 0 |
| CCY(s) | AUD,CAD,CHF,EUR,GBP,JPY,NZD,USD |
| **--- DISPLAY ---** | |
| Corner on | Left upper chart corner |
| Offset X | 20 |
| Offset Y | 4 |
| Font Size (0-auto size) | 0 |
| Update Interval (ms) | 1000 |

| | |
| :--- | :--- |
| === ENTRY SYSTEM - FILTER === | === Volatility Filter === |
| Use Volatility Ranking | On |
| Volatility Timeframe | M30 |
| Volatility Period | 5 |
| Trade From x Rank | 1 |
| Trade Until x Rank | 5 |
**page_11.png**

**Correlation Filter**

| *** ENTRY SYSTEM - FILTER *** | *** Correlation Filter *** |
| :--- | :--- |
| Use Correlation Filter | Off |
| Correlation Timeframe | H1 |
| Correlation Period | 50 |
| Maximum Correlation | 70.0 |
| Minimum Correlation | 0.0 |

*   分析28個貨幣對的走勢相連性，即兩個貨幣對之間的同步性
*   正數值越高同步值越高；負數值越髙越向值越高
*   此項功能並不能推行BT

**Use Correlation Filter 以貨幣相關性過濾作為入市輔助**
1.  **On:** 啟用
2.  **Off:** 關閉

**Correlation Timeframe 時間框架計算**
| 1. Current | 2. M1 | 3. M5 | 4. M15 | 5. M30 |
| :--- | :--- | :--- | :--- | :--- |
| **6. H1** | **7. H4** | **8. D1** | **9. W1** | **10. MN1** |

**Correlation Period 相聯性計算周期**
*   陰陽燭計算數量
*   必須輸入正整數 (1~無限)

**Maximum Correlation / Minimum Correlation 相關性最高值及最低值**
*   可輸入數值由0至100
*   輸入之數值已包括正值及負值 (eg. 70已代表 +70 及 -70)
*   相關性於此數值以外的貨幣對不作交易

---
**page_12.png**

**請留意**

可利用Forex Correlation Smart Indicator檢視28個貨幣對的相聯性

*   Timeframe與Period的部份建議要與EA內Setting相同,才可獲得相對的數值
*   Market Watch需要顯示28個貨幣對

| Forex Correlation Smart Indicator | |
| :--- | :--- |
| **Variable** | **Value** |
| **=== SETTING ===** | |
| Correlation Timeframe | H1 | <font color="red">建議要與 EA 內 Setting 相同</font> |
| Correlation Period | 50 |
| Correlation Shift | 0 |
| Symbol(s) | AUDCAD,AUDCHF,AUDJPY,AUDNZD,AUDUSD... |
| Correlation Limit | 80.0 |

*   USDJPY與AUDJPY的貨幣相關性數值為+91.46
*   USDCAD與AUDJPY的貨幣相關性數值為-88.59

---
**page_13.png**

**Entry System-MARTINGALE 馬丁格爾策略系統入市過濾**

*   起源於賭場的賭博策略
*   主要原理為將每次虧損的賭注加倍,持續進行多次逆勢加注,直到出現回調時連本帶利離場

**(圖表顯示 "Buy Order" 和 "Sell Order" 的位置)**

**RSI Condition**

| *** ENTRY SYSTEM - MARTINGALE *** | === RSI Condition === |
| :--- | :--- |
| Use RSI Filter | On |
| RSI Timeframe | H4 |
| RSI Period | 6 |
| RSI Price | Close price |
| RSI Shift | 1 |
| RSI High | 70.0 |
| RSI Low | 30.0 |

*   RSI (Relative Strength Index) 相對強弱指標,常簡稱為RSI指數或RSI線,是技術分析中的動量分析方法
*   透過認定時間周期內的平均價格上漲幅度和平均價格下跌幅度的關系,來衡量買賣雙方的相對力量程度
*   只涉及到一個周期參數,周期越小,RSI指標對價格變化越敏感;周期越大,RSI指標則對價格變化反應越遲緩
*   RSI 值在70到100之間通常被認定為超買區,此時代表市場可能上演過快,會發出賣入訊號
*   RSI 值在0到30間通常被認定為超賣區,此時代表市場可能下跌過快,會發出買出訊號

---
**page_14.png**

**Use RSI Filter 以RSI作為馬丁入市輔助**
1.  **On:** 啟用
2.  **Off:** 關閉

**RSI Timeframe 時間框架計算**
| 1. Current | 2. M1 | 3. M5 | 4. M15 | 5. M30 |
| :--- | :--- | :--- | :--- | :--- |
| **6. H1** | **7. H4** | **8. D1** | **9. W1** | **10. MN1** |

**RSI Period 計算時期**
*   陰陽燭計算數量
*   必須輸入正整數(1~無限)

**RSI Price 應用價位**
1.  **Close price** 收盤價
2.  **Open price** 開盤價
3.  **High price** 最高價
4.  **Low price** 最低價
5.  **Median price** 最高價與最低價的中間值
6.  **Typical price** 最高價+最低價+收盤價的1/3
7.  **Weighted price** 最高價+最低價+開盤價+收盤價的1/4

**RSI Shift**
*   必須是正整數 (0~無限)
*   例: Shift=0,代表取用以現價bar的數據作為計算基礎
*   例: Shift=1,代表取用以現價bar向左第1支bar的數據作為計算基礎;如此類推

---
**page_15.png**

**RSI High / Low 超買超賣區**

*   RSI值高於RSI High代表進入超買區,會觸發Sell入市
*   RSI值低於RSI Low代表進入超賣區,會觸發Buy入市
*   可輸入數值0-100

**例子**
RSI High = 70, RSI Low = 30

**(圖表顯示在70超買區線觸發 "Sell Signal" 和在30超賣區線觸發 "Buy Signal")**

**Band Condition**

| *** ENTRY SYSTEM - MARTINGALE *** | === Band Condition === |
| :--- | :--- |
| Use Band Filter | On |
| Band Timeframe | H1 |
| Band Period | 20 |
| Band Deviation | 2.0 |
| Band Shift | 0 |
| Band Applied Price | Close price |

*   Band (Bollinger Band) 保力加通道,又簡稱為BB,一種用作判斷超買及超賣情況的參考指標
*   基本的型態是由三條軌道線組成的通道,分別為上軌、中軌及下軌,傳統參數會用
*   中軌是量度價格的簡單移動平均線(SMA)
*   上軌是以標準差數值(Deviation) 加平均線,通常被認為是阻力位置
*   下軌是以平均線減去兩個標準差數值(Deviation),通常被認為是支持位置
*   現價於通道之下,會發出買入訊號
*   現價於通道之上,會發出賣出訊號

**Use Band Filter 以Band作為馬丁入市輔助**
1.  **On:** 啟用
2.  **Off:** 關閉
### page_16.png

**Band Timeframe 時間框架計算**

| | | | | |
| :--- | :--- | :--- | :--- | :--- |
| 1. Current | 2. M1 | 3. M5 | 4. M15 | 5. M30 |
| 6. H1 | 7. H4 | 8. D1 | 9. W1 | 10. MN1 |

**Band Period 計算時期**
*   除陽燭計算數量
*   必須輸入正整數(1~無限)

**Band Deviation 標準差**
*   必須為正整數 (0~無限)

**Band Shift**
*   必須是正整數 (0~無限)
*   例: Shift=0,代表取用以現價bar的數據作為計算基礎
*   例: Shift=1,代表取用以現價bar向左第1支bar的數據作為計算基礎;如此類推

**Band Applied Price 應用價位**
1.  Close price 收盤價
2.  Open price 開盤價
3.  High price 最高價
4.  Low price 最低價
5.  Median price 最高價與最低價的中間值
6.  Typical price 最高價+最低價+收盤價的1/3
7.  Weighted price 最高價+最低價+開盤價+收盤價的1/4

**例子**
(圖表顯示買入和賣出信號)
*   Buy Signal
*   Sell Signal

***

### page_17.png

**Entry System – Money Management 資金管理**

| === ENTRY SYSTEM - MONEY MANAGEMENT === | === Lot Size & Dynamic Pipstep Setting === |
| :--- | :--- |
| **First Entry Lots Size** | 0.05 |
| **Lot Exponent** | 1.2 |
| **Level 1 Pips Step** | 30.0 |
| **Level 2 Pips Step** | 60.0 |
| **Level 3 Pips Step** | 120.0 |
| **Level 4 Pips Step** | 200.0 |
| **Level 5 Pips Step** | 360.0 |
| **Level 6 Pips Step** | 500.0 |
| **Level 7+ Pips Step** | 750.0 |
| **SL in Level (0=not used)** | 9 |

**First Entry Lots Size**
*   首單入市手數
*   必須為正數 (0~無限)

**Lot Exponent**
*   每層馬丁的手數倍數
*   必須為正整數 (0~無限)

**Level 1 - 7 Pips Step**
*   與上一層相距設定數值便觸發入市
*   第七層及之後層數都以第七層的設定值計算
*   必須為正整數 (0~無限)

**SL in Level**
*   於第幾層單進行出市止蝕 (包括首張單)
*   必須為正整數 (0~無限)

**Order General Setting**

| === ENTRY SYSTEM - ORDER MANAGEMENT === | === Order General Setting === |
| :--- | :--- |
| **Maximum Spread in Pips** | 3.0 |
| **Maximum Slippage in Pips** | 3.0 |
| **Exit Max Spread Filter** | Off |
| **Magic Number (Buy)** | 77 |
| **Order Comments (Buy)** | SMA BUY |
| **Magic Number (Sell)** | 77 |
| **Order Comments (Sell)** | SMA SELL |

**Max Spread in Pips 容許最大價差**
*   價差是指貨幣對的買入價和賣出價之間的差額
*   設定最大價差數值, 當價差大於設定數值, 不會進行入市
*   必須為正數 (0~無限)

**Max Slippage in Pips 容許最大滑價**
*   滑價是指交易的預期價格和交易執行價格之間的差異
*   設定最大滑價價值, 當滑價大於設定數值, 不會進行入市
*   必須為正數 (0~無限)

***

### page_18.png

**Exit Max Spread Filter 出市最大價差過濾器**
*   價差是指貨幣對的買入價和賣出價之間的差額
*   設定最大價差價值, 當價差超過設定的最大點差時, 不會進行出市
*   必須為正整數(0~無限)

**Magic Number (Buy / Sell)**
*   每次開單EA都會將Magic Number記錄, 平倉時會根據Magic Number來確認訂單
*   Buy / Sell 會分開獨立處理
*   不輸入數值, 會自動轉為0
*   必須為正數 (0~無限)

**Order Comment (Buy / Sell)**
*   每次開單EA都會將Comment記錄, 平倉時會根據Comment來確認訂單
*   Buy / Sell 會分開獨立處理
*   可任意輸入英文字及數值, 最多只能輸入28個字元
*   可不輸入任何資料

***

### page_19.png

**Exit System 出市設置**

| === EXIT SYSTEM === | ##### Exit Setting ##### |
| :--- | :--- |
| **Dollar Mode (1st)** | Dollar per 0.01 lot |
| **Take Profit in Dollars (0=not used)** | 0.0 |
| **Trailing Start in Dollars (0=not used)** | 5.0 |
| **Trailing Distance in Dollars (0=not used)** | 0.5 |
| **Breakeven Start in Dollars (0=not used)** | 0.0 |
| **Breakeven Distance in Dollars (0=not used)** | 0.0 |
| **Stop Loss in Fix Dollars (0=not used)** | 0.0 |
| **Dollar Mode (2nd +)** | Dollar per 0.01 lot |
| **Take Profit in Dollars (0=not used)** | 0.0 |
| **Trailing Start in Dollars (0=not used)** | 5.0 |
| **Trailing Distance in Dollars (0=not used)** | 0.5 |
| **Breakeven Start in Dollars (0=not used)** | 0.0 |
| **Breakeven Distance in Dollars (0=not used)** | 0.0 |
| **Stop Loss in Fix Dollars (0=not used)** | 0.0 |

*   **出市設置分為**
    *   Dollar Mode (1st)：只計算首張單
    *   Dollar Mode (2nd+)：第二張單及以上 (即整套馬丁)
    *   1. Dollars: 以整套交易的盈利總額作計算單位
    *   2. Dollar per 0.01 lot: 以每0.01 lot的盈利作計算單位

**Take Profit in Dollars 固定獲利設定**
*   固定獲利數值
*   必須為正數 (0~無限)

**Stoploss in Fix Dollars 固定止損設定**
*   固定止損數值
*   不論設定於Dollar 或者Dollar per 0.01 lot, 都是以固定數值止蝕出市
*   必須為正數 (0~無限)

**Trailing Start in Dollars 啟動移動止損的起步距離**
*   入市後如浮動超過此數值便觸發
*   必須為正數 (0~無限)

***

### page_20.png

**Trailing Distance in Dollars 平倉位置與現價距離**
*   價格從高位回調多少便進行平倉
*   必須為正數 (0~無限)

**Trailing 例子**
*   Trailing Start in dollars = 10
*   Trailing Distance in dollars = 3

(圖表)
*   入市後浮盈達到10 dollars 便啟動Trailing 功能
*   觸發Trailing Start 後, 待反方向回調3 dollars 便會平倉
*   \*平倉位置會根據價格持續上升而改變
好的，這就為您提取 page_21.png 到 page_25.png 的內容。

### **Page 21**

#### **Breakeven Start in Dollars 盈虧平衡止損的起步距離**
*   入市後如浮盈超過此數值便啟動
*   必須為正數 (0~無限)

#### **Breakeven Distance in Dollars 平倉位置與現價距離**
*   價格回調到多少便進行平倉
*   必須為正數 (0~無限)

#### **Buy單例子**
*   **Breakeven Start in Dollars** = 5
*   **Breakeven Distance in Dollars** = 2

**圖表註解:**
*   入市後浮盈達到 5 dollars 便啟動 Breakeven 功能。
*   觸發 Breakeven 後，待反方向回調 2 dollars 便會平倉。
*   平倉位置不會根據價格持續上升而改變。

---

### **Page 22**

#### **Trailing VS Breakeven**
*   **Trailing**: Trailing 的平倉位置會根據現價不斷地調整。
*   **Breakeven**: Breakeven 的平倉位置是固定不變的。

#### **Dynamic TP 動態獲利模式進行平倉**

| === EXIT SYSTEM === | |
| :--- | :--- |
| **Use Dynamic TP** | On |
| **Top Return MA Timeframe** | H4 |
| **Top Return MA Period 1** | 12 |
| **Top Return MA Period 2** | 34 |
| **Top Return MA Shift** | 1 |
| **Top Return Start in Pips** (0-not used) | 30.0 |
| **Top Return Distance in Pips** (0-not used) | 10.0 |

*   以移動平均線(MA)來進行平倉
*   兩條MA線 (快線MA Period 1與慢線 MA Period 2) 之間的差距越大,代表趨勢越明顯
*   當兩線之間的差距開始收窄,代表趨勢強度開始減弱
*   如同時使用 Trailing, 出市會於 Dynamic TP 達成後, 再繼續進行 Trailing, 以達致最高利潤

#### **Use Dynamic TP 以動態獲利模式進行平倉**
*   **1. On**: 啟用
*   **2. Off**: 關閉

#### **Top Return MA Timeframe 時間框架計算**

| 1. Current | 2. M1 | 3. M5 | 4. M15 | 5. M30 |
| :--- | :--- | :--- | :--- | :--- |
| **6. H1** | **7. H4** | **8. D1** | **9. W1** | **10. MN1** |

---

### **Page 23**

#### **Top Return MA Period 1 / Period 2 高位回調的快線及慢線同期**
*   MA線的陰陽燭計算數量
*   必須為正整數 (1~無限)

#### **Top Return MA Shift**
*   MA線偏移值
*   必須為正整數 (0~無限)

#### **Top Return Start in Pips 高位回調的起步距離**
*   兩MA線差距超過此數值便啟動
*   必須為正數 (0~無限)

#### **Top Return Distance in Pips 高位回調的差距收窄距離**
*   兩條MA線的最大差距回調多少Pips便進行平倉
*   必須為正數 (0~無限)

#### **例子**
*   **Top Return Start in Pips** = 30
*   **Top Return Distance in Pips** = 10

**圖表註解:**
1.  兩條 MA 線差距達 30pips，啟動 Dynamic TP 功能。
2.  最高位的差距 = 50pips。
3.  兩條 MA 線的最大差距收窄達 10pips，會於此位置進行平倉。

#### **Trailing Distance after Dynmaic TP in Dollars 動態獲利模式後移動獲利的距離**
*   Dynamic TP 達成後
*   價格從高位回調多少便進行平倉
*   必須為正數(0~無限)

---

### **Page 24**

#### **Exit Cooldown**

| === EXIT SYSTEM === | |
| :--- | :--- |
| **Cooldown After Close** | Off |
| **Cooldown MA Timeframe** | H4 |
| **Cooldown MA Period** | 99 |
| **Cooldown MA Shift** | 1 |

*   以移動平均線(MA)進行冷卻期
*   平倉後待現價再次觸及設定MA線才會再進行入市(Sell 必須高於MA線才能再次入市 / Buy必須低於MA線才能再次入市)

#### **Cooldown After Close 以移動平均線進行冷卻期**
*   **1. On**: 啟用
*   **2. Off**: 關閉

#### **Cooldown MA Timeframe 時間框架計算**

| 1. Current | 2. M1 | 3. M5 | 4. M15 | 5. M30 |
| :--- | :--- | :--- | :--- | :--- |
| **6. H1** | **7. H4** | **8. D1** | **9. W1** | **10. MN1** |

#### **Cooldown MA Period 計算時期**
*   陰陽燭計算數量
*   必須輸入正整數 (1~無限)

#### **Top Return MA Shift**
*   MA線偏移值
*   必須為正整數 (0~無限)

#### **例子**
*   **Cooldown MA Period** = 34
*   **圖表註解**: 此位置出市後便設冷卻期。價位再次觸及 MA(34)線，冷卻期結束，可以允許繼續開單。

---

### **Page 25**

#### **Time Cooldown**

| === EXIT SYSTEM === | |
| :--- | :--- |
| **Use Time Cooldown After Close** | On |
| **Cooldown in Minutes** | 60 |

#### **Cooldown After Close 以移動平均線進行冷卻期**
*   **1. On**: 啟用
*   **2. Off**: 關閉

#### **Cooldown in Minutes 冷卻時間**
*   平倉後的冷卻時間,以分鐘計算
好的，這是從您提供的圖片中提取的文字內容：

### Page 26

**News Filter 新聞過濾**

| 參數 | 值 |
| :--- | :--- |
| Related Currency (eg. EUR,USD) (Empty = Cu... | On |
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
*   News filter只限制首單入市, 不會限制馬丁加單以及平倉

**Related Currency 相關貨幣**

*   不輸入貨幣代表只應用於當前圖表貨幣 (eg. 當前圖表貨幣對的貨幣是GBPJPγ, 就只會使用 GBP 跟JPY的新聞)
*   如輸入貨幣 GBP, 代表只影響GBP相關貨幣對

**High Important (Red) 重要新聞 (紅色)**

*   禁止高度重要指標發佈前後下單

**Non-Farm Payout 非農就業數據**

*   禁止非農就業數據發佈前後下單

**Speaks (Orange) 演講 (橙色)**

*   禁止發佈重要演講前後下單

**Draw News Lines 繪畫新聞線**

*   於圖表上顯示新聞發佈時間

### Page 27

**Display & Misc 其他**

| 參數 | 值 |
| :--- | :--- |
| Show Panel | Off |
| Send BED Signal (Backtest Use) | On |
| Export Analytics Summary Report (Backtest Use) | On |
| Display Trade Mode | On Chart Comment |
| Display Remark | |

**Show Panel 面板:**

*   提供啟動面板功能, 可以獨立選擇做動與否
*   會於交易圖表左上角出現控制面板
*   會於交易圖表上劃出Buy stop / Sell stop / Breakeven / Trailing 等位置線
*   會於交易圖表左下角顯示MACD / Volatility / CCY Power / AI signal等資訊

**左下角資訊顏色顯示代表:**

*   黑色: Both Direction
*   綠色: Buy Only
*   紅色: Sell Only
*   灰色: No Trade

**Send BED Signal (Backtest Use) 發送BED訊號 (只供回測用):**

*   提供啟動發送BED訊號選項
*   BED Signal即顯示BalanceיEquity及Drawdown資料

**Export Analytics Summary Report (Backtest Use) 匯出交易記錄報表 (只供回測用):**

*   提供啟動匯出交易記錄報表選項

**Display Trade Mode 顯示交易模式:**

*   No Display: 交易模式不會顯示
*   On Chart Comment: 交易模式將顯示在圖表的左上角並在備註旁邊
*   On Chart Center: 交易模式將顯示在圖表的中央位置

**Display Remark 顯示備註:**

*   將輸入的備註顯示在圖表的左上角

### Page 28

這頁沒有可見的文字內容。
