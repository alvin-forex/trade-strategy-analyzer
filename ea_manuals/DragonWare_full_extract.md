### 第 1 頁

- Forex Forest ® Algorithmic Trading
- Algo Forest ®
- DRAGON WAVE
- 操作指南
- MANUAL

### 第 2 頁

操作指南手冊所提及的參數設定僅供說明用途，並非建議設定或任何投資建議。用戶使用自動程式EA之前有需要明白投資涉及風險，用戶請自行評估參數是否合適使用，並可因應自己的風險承受能力自行設定有關參數值。所有參數設定都涉及風險，請用謹慎評估、使用模擬交易或進行BT回測參考結果數據，再作使用。

**Dragon Wave**

Dragon Wave EA 的設計靈感，源自日本浮世繪大師葛飾北齋的傳世名作 —《神奈川沖浪裏》。在波瀾壯闊的畫作中，平靜海面被突如其來的巨浪翻騰，正如市場，往往在最安靜的時刻，孕育最大幅度的變化。

Dragon Wave EA 正是為此而生 — 一套能於平靜市況中讀出波動序曲，在反轉的剎那儲力而起，更快、更準確地捕捉關鍵入市時機的智能交易系統，潛伏於海底，洞察暗流，在浪起之時，率先出擊。

策略核心透過 15 組不同的保力加通道，對市場的波動進行層層掃描，逐層過濾雜訊，最終只留下最佳的入市訊號。策略設計重視本金安全與穩定獲利，以打造穩定可持續的長期收益為目標。

**核心功能 (Core Features)**

*   **智能馬丁格爾系統**
    內建智能化馬丁格爾交易策略，能自動調整開單位置，在行情順勢時放大獲利潛能，在反向盤整時收斂風險，達致風險與收益的最佳平衡。
*   **穩定盈利的最佳化**
    結合超過 70,000 份歷史交易與回測數據驗證，擁有大量真實同學交易數據供參考。
*   **策略性止損**
    採用有紀律的止損邏輯，根據實時行情判斷離場時機，有效限制每筆交易的最大虧損，守護資本安全。

### 第 3 頁

*   **可定制入市參數**
    內建 15 組不同設置的保力加通道入市策略，可根據不同個人交易風險偏好，靈活調整入市條件，提升策略靈敏度與精準度。

**基本設定 (Basic Setting)**

| 參數 | 值 |
| :--- | :--- |
| Direction of Trades to Open | Open Both directions |

*   **Direction of Trades to open**
    設定交易方向以決定系統在何種市場情況下開倉。以下為可選擇的交易方向：
    1.  **No Entry**
        系統將暫停所有交易，不會執行任何買入或賣出操作。此選項適用於需要暫停交易或觀望市場時使用。
    2.  **Buy Only**
        系統僅執行買入操作，適用於看漲市場或對未來價格上升有信心的情況。
    3.  **Sell Only**
        系統僅執行賣出操作，適用於看跌市場或對未來價格下降有信心的情況。
    4.  **Open Both Directions**
        系統同時執行買入與賣出操作，適用於震盪市場或需要雙向交易策略的情況。

### 第 4 頁

**主要入市策略 - 保力加通道判斷 (Main Entry System - Band Signals)**

| 參數 | 值 |
| :--- | :--- |
| Set 1-1 Band Signal MA Period (0-not used) | 200 |
| Set 1-2 Band Signal MA Period (0-not used) | 400 |
| Set 1-3 Band Signal MA Period (0-not used) | 800 |
| Set 1-4 Band Signal MA Period (0-not used) | 0 |
| Set 1-5 Band Signal MA Period (0-not used) | 0 |
| Set 2-1 Band Signal MA Period (0-not used) | 0 |
| Set 2-2 Band Signal MA Period (0-not used) | 0 |
| Set 2-3 Band Signal MA Period (0-not used) | 0 |
| Set 2-4 Band Signal MA Period (0-not used) | 0 |
| Set 2-5 Band Signal MA Period (0-not used) | 0 |
| Set 3-1 Band Signal MA Period (0-not used) | 0 |
| Set 3-2 Band Signal MA Period (0-not used) | 0 |
| Set 3-3 Band Signal MA Period (0-not used) | 0 |
| Set 3-4 Band Signal MA Period (0-not used) | 0 |
| Set 3-5 Band Signal MA Period (0-not used) | 0 |

*   提供最多15條獨立且可自定義的 Bollinger Bands 入市參數，讓您能針對不同的交易風格、貨幣對及市場條件，對 Dragon Wave 的進場策略進行精細微調。
*   每組參數均配備獨立的智能馬丁格爾開單系統，能根據市場波動自動調整開單位置，最大化交易效率。
*   保力加通道 (Bollinger Bands) 預設使用 Shift 1、收盤價 (Close Price) 及線性加權平均 (Linear Weighted Averaging) 進行計算，以確保對市場變動的精確性與靈敏度。
*   所有入市條件皆以每根陰陽燭 (Per Bar) 為單位進行判斷。
*   可配合 Band Signal v1.00 指標使用。
    (*同學請於 GemsAI 自行下載 Band Signal v1.00 技術指標)

### 第 5 頁

*   **首張單入市條件**
    1.  **計算條件**
        *   **Sell 條件:** 當前陰陽燭的收市價高於保力加通道 (標準差 × 2) 的上軌線。
        *   **Buy 條件:** 當前陰陽燭的收市價低於保力加通道 (標準差 × 2) 的下軌線。
    2.  **入市時機**
        *   **Sell 入市時機:** 若滿足賣出條件，則在下一根陰陽燭的開盤時執行開倉操作。
        *   **Buy 入市時機:** 若滿足買入條件，在下一根陰陽燭的開盤時進行買入。
    3.  **跳空保護機制**
        *   **Sell 開倉價格:** 取收市價和下一根陰陽燭的開盤價中的最大值。
        *   **Buy 開倉價格:** 取收市價和下一根陰陽燭的開盤價中的最小值。
好的，這就為您提取 page_06.png 到 page_10.png 的可見文字。

### page_06.png

#### 馬丁策略的開單位置

[圖片顯示兩張圖表，說明馬丁策略的開單位置。第一張圖顯示在上升趨勢中，當前一個賣出訂單的開單價位被突破後，下一個買入訂單會在比該價位高 42 pips 的地方開立。第二張圖顯示在下降趨勢中，當前一個買入訂單的開單價位被跌破後，下一個賣出訂單會在比該價位低 52 pips 的地方開立。]

在使用馬丁策略時，下一筆訂單的開單位置按照以下規則確定：

1.  **基準價位**
    以上一筆訂單的開單價位作為基準價位。

2.  **保力加通道的參考**
    根據當前市場條件，計算上一筆訂單的保力加通道 (Bollinger Bands) 中標準差的2倍距離。

3.  **下一單馬丁開單位置**
    下一筆訂單將於上一筆開單價位加上保力加通道 (Bollinger Bands) 標準差的兩倍距離位置開出。

4.  **公式表達**
    *   買入 (Buy) 情況: 下一單開單位置 = 上一單開單價位 - (標準差 × 2)
    *   賣出 (Sell) 情況: 下一單開單位置 = 上一單開單價位 + (標準差 × 2)

---

### page_07.png

#### 主要入市策略 - 保力加通道判斷
**Main Entry System - Band Signals**

| | === ENTRY SYSTEM - FILTER === | === Price ATR Filter === |
| :--- | :--- | :--- |
| **ab** | **Use Price ATR Filter** | **On** |
| **123** | **ATR Timeframe** | **1 Day** |
| **123** | **ATR Period** | **14** |
| **123** | **ATR Shift** | **1** |
| **½** | **Minimum Price/ATR Ratio** | **70.0** |

*   **Price/ATR Filter** 是一種技術分析工具，結合了價格走勢 (Price Action) 和平均真實範圍 (Average True Range, ATR) 的指標。它通過將當前價格與該價位的 ATR 值進行比較，篩選出波動較大或符合特定條件的價格點。
*   **風險管理**：在市場波動加劇時，這個指標可以讓交易者識別風險較高的價位，從而調整倉位或減少操作。
*   **篩選信號**：當價格與ATR的比例超過設定的 Price/ATR 值時，Price/ATR Filter 可以配合保力加通道的設定進行入市。
*   可配合 MTF Price-ATR v1.00 技術指標使用。

##### Use Price/ATR Filter
- **On** 代表啟用；**Off** 代表關閉。

##### ATR Timeframe
- ATR 所使用的時間框架
- 選擇一個合適的時間週期，如日線圖、小時圖或分鐘圖，根據市場狀況和風險偏好調整。

##### ATR Period
- 基於指定的陰陽燭數量計算ATR值，必須是正整數 (可設定數值範圍 1 至 無限大)。

##### ATR Shift
- ATR指標偏移值，必須為正整數 (可設定數值範圍 0 至 無限大)。

---

### page_08.png

#### Minimum Price/ATR Ratio

[圖片顯示一張圖表，X軸為時間，Y軸為價格。圖表上方顯示蠟燭圖，下方顯示 ATR 指標。圖表說明了 ATR 與價格波動的關係：當 ATR 上升時，市場波動加劇，Price/ATR 數值會相對下降。]

- 設定一個 Price/ATR 值，當價格超過該 Price/ATR 值時，便會配合 Band Signals 的設定進行入市。
- 從下圖可以看出，ATR 與 Price/ATR 呈反比關係。因此當 ATR 上升，代表市場波動加劇，Price/ATR 數值會相對下降。此時並不適合啟動 Dragon Wave 的入市策略。

#### 訂單管理 - 基本參數
**Order Management - General Setting**

| | === ENTRY SYSTEM - ORDER MANAGEMENT === | === Order General Setting === |
| :--- | :--- | :--- |
| **123** | **Order ID (Magic Number)** | **1** |
| **123** | **Max Spread in Points (0-not used)** | **0** |
| **123** | **Max Slippage in Points (0-not used)** | **0** |

##### Order ID (Magic Number)
*   每次開單時，EA 都會將 Magic Number 記錄下來，並於平倉時根據此編號確認對應的訂單。
*   必須為正數範圍。

---

### page_09.png

##### Max Spread in Points
*   必須為正數範圍 (0代表不使用)。
*   價差是指貨幣對的買入價與賣出價之間的差額。
*   可設定最大價差值，當實際價差大於設定值時，將無法執行入市或出市操作。

##### Max Slippage in Points
*   必須為正數範圍 (0代表不使用)。
*   滑價是指交易的預期價格與實際執行價格之間的差異。
*   可設定最大滑價值，當實際滑價大於設定值時，將無法執行入市或出市操作。

#### 訂單管理 - 交易手數設定
**Order Management - Lot Size Setting**

| | === ENTRY SYSTEM - MONEY MANAGEMENT === | === Lot Size Setting === |
| :--- | :--- | :--- |
| **fx** | **Fixed Lot Size** | **0.01** |
| **fx** | **Virtual Trades** | **2** |
| **fx** | **Lot Multiplier** | **2.5** |
| **fx** | **Pipstep Multiplier** | **1.0** |

##### Fixed Lot Size
*   首張單的入市的手數
*   必須是正整數 (0~無限)

---

### page_10.png

##### Virtual Trades
目的是調整實際開單的順序和策略執行方式。當設定 Virtual Trade = 2 時，表示程式會跳過前兩筆開單，僅從第三筆開始執行實際開單操作。此時，原本應該是第三筆的開單，將成為第一筆實際下單的交易，而前兩筆開單僅作為模擬計算，不會真正執行。

**例子:**

**Virtual Trades = 0**
[圖表顯示在沒有虛擬交易的情況下，所有交易都會被實際執行。]

**Virtual Trades = 2**
[圖表顯示當虛擬交易設為2時，前兩筆交易（以綠色框標示）僅為模擬，從第三筆交易開始才會實際下單。]
好的，這就為您提取 `page_11.png` 到 `page_15.png` 的可見文字。

### Page 11

*   **Lot Multiplier**
    根據交易策略的需求，利用 Lot Multiplier 可以放大或縮小每筆交易的手數。
    例如，設置 Lot Multiplier = 2，則每筆交易的手數將是原手數的兩倍；設置 Lot Multiplier = 0.5，則每筆交易的手數將減半。

    **例子:**
    Lot Multiplier = 2

| # | Time | Type | Order | Size | Price |
| :-- | :--- | :--- | :-- | :--- | :--- |
| 1 | 2025.03.03 13:15 | sell | 1 | 1.00 | 1.50723 |
| 2 | 2025.03.03 14:45 | sell | 2 | 2.00 | 1.51162 |
| 3 | 2025.03.03 22:00 | sell | 3 | 4.00 | 1.51849 |
| 4 | 2025.03.04 18:00 | sell | 4 | 8.00 | 1.52600 |
| 5 | 2025.03.05 10:30 | sell | 5 | 16.00 | 1.53860 |
| 6 | 2025.03.05 18:15 | sell | 6 | 32.00 | 1.55381 |

*   **Pipstep Multiplier**
    在交易程式中設置 Pipstep Multiplier，用於調整加單距離的參考值。
    Pipstep Multiplier 的預設值為 1，表示加單距離直接參考保力加通道的原始標準差距離。
    當 Pipstep Multiplier = 2 時，程式會將原有保力加通道的標準差距離放大至 2 倍，並以此作為加單距離的參考值。因此，加單的觸發條件會延後，使開單間距更大，從而減少頻繁交易。

### Page 12

*   **訂單管理 — 出場設定**
    **Order Management - Exit Setting**

*   **=== EXIT SYSTEM ===**
    - **Use Virtual TP**: Off
    - **Use Virtual SL**: Off
    - **SL in Points (0-not used)**: 0
    - **Account StopLoss in Money (0-not used)**: 0.0
    - **Force Close on BE**: Off

*   **Virtual TP**
    啟用此功能後，止盈價位不會顯示在 MT4 的訂單記錄上，只有當價格達到設定的止盈點時，才會執行止盈操作。

*   **Virtual SL**
    啟用此功能後，止損價位不會顯示在 MT4 的訂單記錄上，只有當價格達到設定的止損點時，才會執行止損操作。

*   **SL in Points**
    以點數 (Points) 為單位設定止損 (Stop Loss)，用於計算價格波動範圍內的止損距離。
    *   SL 計算方法 = 平均價格 (Avg Price) ± SL 點數 (SL in Points)
    *   無論是止盈 (TP) 還是止損 (SL)，都會針對每個設置 (set) 進行獨立計算。

*   **Account Stop Loss in Money**
    以整個帳戶的浮虧金額 (Money) 為單位設定止損 (Stop Loss)，用於控制最大浮虧在可承受範圍之內。
    *   跟 SL in Points 不同，是以整個交易帳戶 (Account) 計算，並不是針對每張圖 (chart) 進行獨立計算。

*   **Force Close on BE**
    所有持倉在結單時的淨利潤 (包括手續費和隔夜利息) 等於 0 時強制平倉。

### Page 13

*   **交易時段設定**
    **Trading Session**

*   **=== TRADING SESSION ===**
    - **No Trade Days on Year Start**: 14 Days
    - **No Trade Days on Year End**: 14 Days
    - **Trading Session (Broker Time)**: 00:00-23:59

*   **No Trade Days on Year Start**
    在新的一年開始時，市場往往處於低流動性狀態，參與者較少，價格波動可能異常劇烈或不穩定。啟用「No Trade Days on Year Start」功能，可於年初指定天數內暫停交易，避開潛在風險。
    此設定有助於降低因市場異常波動或交易量不足所造成的損失風險，為之後的交易表現建立更穩定的起點。

*   **No Trade Days on Year End**
    在年末的最後幾天，外匯市場通常會受到以下影響：
    1.  流動性降低： 很多機構投資者和交易者在年末休假，市場參與者減少，導致流動性下降，買賣差價 (Spread) 可能擴大。
    2.  價格異常波動： 因流動性不足，少量交易可能引發較大的價格波動，增加交易風險。
    3.  市場噪音增加： 年末通常伴隨資金結算、財務報表調整和其他非正常市場行為，可能產生更多市場噪音，干擾交易策略。
    設定 No Trade Days on Year End 的目的是避免在市場條件不穩定或高風險的年末進行交易，從而保護資金，減少不必要的損失，並為新年的交易做好準備。

### Page 14

*   **Trading Session (Broker Time)**
    設定交易活動的時間範圍，根據經紀商提供的伺服器時間 (Broker Time) 來限制交易的執行時間。這樣可以：
    1.  避免低流動性時段的風險： 某些時段 (如市場收盤或開盤前後) 流動性較低，價格波動可能異常，限制交易時間可以減少這種風險。
    2.  針對特定市場時段： 不同的交易時段 (如亞洲、歐洲或美洲市場) 具有不同的波動特性，設定交易時間可以專注於特定的市場活動。
    3.  提升策略效率： 配合策略需求，僅在最有利的時間段運行交易，避免在無效或低效率的時段浪費資源。
    此功能有助於更精確地控制交易行為，優化整體交易績效。

*   **顯示設定 — 其他項目**
    **Display – Misc**

*   **=== DISPLAY ===**
    - **Show Panel**: On
    - **Send BED Signal**: Off

*   **Show Panel**
    *   提供啟用面板的功能，可根據需求獨立選擇是否啟用。
    *   控制面板將顯示於交易圖表的左上角。

*   **Send BED Signal**
    *   發送 BED 訊號 (僅供回測使用)。
    *   提供啟用發送 BED 訊號的選項。
    *   BED Signal 指的是包含餘額 (Balance)、淨值 (Equity) 及回撤 (Drawdown) 資料的訊號。

### Page 15

*   **補充資訊**

| Band Signals | Comment 內的對應字母 |
| :--- | :--- |
| Set 1-1 | A |
| Set 1-2 | B |
| Set 1-3 | C |
| Set 1-4 | D |
| Set 1-5 | E |
| Set 2-1 | F |
| Set 2-2 | G |
| Set 2-3 | H |
| Set 2-4 | I |
| Set 2-5 | J |
| Set 3-1 | K |
| Set 3-2 | L |
| Set 3-3 | M |
| Set 3-4 | N |
| Set 3-5 | O |

*   每次開單時，Dragon Wave 都會將 Comment 記錄下來，並於平倉時根據對應字母確認對應的訂單，以便交易者能識別交易的訂單。

*   **顯示方式:**
    Order Comment = Dragon Wave _ Band Signals 對應字母 + Z + Order

| Set Used | Order (包括 Virtual Trade) | Comment |
| :--- | :--- | :--- |
| Set 1-1 | 1st Order | Dragon Wave_AZ0 |
| Set 1-1 | 2nd Order | Dragon Wave_AZ1 |
| Set 2-3 | 1st Order | Dragon Wave_HZ0 |
| Set 2-3 | 2nd Order | Dragon Wave_HZ1 |

*   在Comment中，「Z」用作分隔「Band Signals對應字母」及「Order」之用。
Here's the text from the image above:
**Page 16**

**參數**
- 49.2
- 57.8
- 46.1
- 52.3
