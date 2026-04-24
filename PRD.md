# PRD：交易策略分析系統（Trade Strategy Analyzer）

> **版本：** v0.3（四方 Review 整合版：GLM-5 + GLM-4.7 + ChatGPT + Deepseek）
> **日期：** 2026-04-24
> **作者：** 丁蟹 + Alvin
> **狀態：** 待多模型 Review

---

## 1. 背景與目標

### 1.1 問題
Alvin 在 Forex Forest 平台管理多個信號頁（如 #14581），每個信號頁跑不同的 EA 策略。目前：
- 只能從平台下載 `.csv` 交易數據和 `.set` 策略設定檔
- 缺乏系統化方法分析策略的**入市準確性**和**性價比**
- 無法從歷史交易中提煉出哪些策略適合 Copy Trade
- 策略知識散落各處，沒有統一記錄

### 1.2 目標
建立一個 **交易策略分析系統**，實現：

**目標一：策略準確性分析**
- 評估每筆交易的入市質量（入得啱唔啱、入得快唔快）
- 記錄策略的入市條件、濾鏡、參數等完整設定
- 長期建立策略知識庫，協助設計應對不同市況的策略

**目標二：Copy Trade 策略篩選**
- 從交易數據中識別高勝率、高性價比的策略
- 分析單層 vs 多層（馬丁）交易的表現
- 建議最優 TP/SL/TSL 設定
- 評估 Copy on Profit vs Copy on Lose 的適用性

---

## 2. 輸入數據規格

### 2.1 交易數據（.csv）

來源：Forex Forest 信號頁下載

| 欄位 | 類型 | 說明 | 分析用途 |
|------|------|------|---------|
| Open Time | datetime | 開倉時間 | 時段分析、入市時機 |
| Type | string | buy / sell | 方向 |
| Lots | float | 手數 | 判斷第幾層（0.02=L1, 0.04=L2, 0.06=L3, 0.12=L4, 0.21=L5, 0.38=L6） |
| Symbol | string | 貨幣對 | 分組 |
| Open Price | float | 開倉價 | 計算實際點差 |
| Close Time | datetime | 平倉時間 | 倉位重構分組鍵 |
| Close Price | float | 平倉價 | 計算實際點差 |
| Commission | float | 手續費 | 真實成本 |
| Swap | float | 隔夜利息 | 長期持倉成本 |
| Net Pips | float | 淨賺點數 | 方向對唔對、盈虧大小 |
| Net Profit | float | 淨盈虧（$） | 真實收益 |
| Max Profit | float | 最大浮盈（$） | 出場效率 |
| Max Pips | float | 最大浮盈（pips） | 入市時機好唔好 |
| Max Loss | float | 最大浮虧（$） | 風險承受 |
| Max Loss Pips | float | 最大浮虧（pips） | 入市後最大逆境 |
| Magic Number | int | 88=BUY, 77=SELL | 方向、策略識別 |
| Comment | string | SMA BUY / SMA SELL | 策略名稱 |
| Holding Time (Hours) | float | 持倉小時 | 效率分析 |
| Holding Time | string | 可讀格式 | 顯示用 |

**已知特徵：**
- 一個 .csv 包含一個信號頁所有貨幣對的交易
- 同一貨幣對可能有多筆交易（馬丁多層）
- Magic Number 區分方向（88=BUY, 77=SELL）
- Close Time 相同 + Symbol 相同的多筆交易 = 同一倉位被整體平倉
- Lots 遞增模式：0.02 → 0.04 → 0.06 → 0.12 → 0.21 → 0.38（lotExp=1.8）

### 2.2 策略設定檔（.set）

來源：Forex Forest 信號頁下載，key=value 格式。

#### 基本設定
```
EA_NAME=SMA v3.00
EA_VERSION=20250805
EA_SYMBOL=USDJPY          # 此設定對應的貨幣對
EA_PERIOD=240             # 圖表時間框架（分鐘），240=H4
OpenType=2                # 開倉類型
TradeType=2               # 交易類型
Trading_Mode=2            # 交易模式
```

#### MA 系統（方向判定 + 入市觸發）
```
BasicMaTimeframes=60      # 主MA時間框架（H1）
BasicMaLine1_Period=80    # 長線MA1 — 大方向
BasicMaLine2_Period=120   # 長線MA2 — 大方向
BasicMaLine345_Period=20  # 中線MA
BasicMaLine6_Period=5     # 短線MA
BasicMaShift=1            # 用前一支bar

FollowMADirection=0       # 否跟隨MA方向
CloseByMADirection=0      # 否按MA方向平倉

EnterMaTimeframes=30      # 入市MA時間框架（M30）
EnterMaLine_Period=3      # 入市觸發MA — 短期穿越
EnterMaShift=1            # 用前一支bar
```

**推斷邏輯：**
- MA Line1(80) > MA Line2(120) = 上升趨勢 → 只做 BUY
- MA Line1(80) < MA Line2(120) = 下降趨勢 → 只做 SELL
- EnterMA(3) 在 M30 穿越觸發具體入市時機

#### 濾鏡系統（全部要通過先入市）
```
UseAISignal=1             # ⚠️ AI信號（邏輯未知，待確認）

UseVlt=1                  # 波幅濾鏡
  VolatilityApplied=0
  VltTf=30                # M30
  VltPeriod=48            # ATR(48)
  VltFrom=8               # 波幅下限
  VltUntil=20             # 波幅上限

UseRSI=1                  # RSI濾鏡
  effRsi_TF=60            # H1
  effRsi_period=8         # RSI(8)
  effRsi_price=0          # Close price
  effRsi_shift=1          # 用前一支bar
  effRsi_high=70.0        # RSI>70 唔買（超買）
  effRsi_low=30.0         # RSI<30 唔賣（超賣）

UseBB=1                   # 布林帶濾鏡
  effBB_TF=60             # H1
  effBB_period=20         # BB(20)
  effBB_deviation=2.0     # 2倍標準差
  effBB_shift=0           # 當前bar
  effBB_price=0           # Close price

UseCorrelation=0          # 相關性濾鏡（此例關閉）
  CorrTf=240, CorrPeriod=20, MaxCorr=70, MinCorr=0
```

#### 馬丁加倉系統
```
EntryLot=0.02             # 第1層手數
lotExp=1.8                # 每層倍率（1.8x）
pipstep2=50               # 第2層距離（pips）
pipstep3=60               # 第3層
pipstep4=70               # 第4層
pipstep5=80               # 第5層
pipstep6=90               # 第6層
pipstep7=100              # 第7層
pipstep8=110              # 第8層
slInLevel=9               # 第9層止損（到第9層就止損）
```

**層數計算：**
| 層數 | Lots | 倍率 | pipstep | 累計 pips |
|------|------|------|---------|-----------|
| L1 | 0.02 | 1.0 | — | 0 |
| L2 | 0.04 | 2.0 | 50 | 50 |
| L3 | 0.06 | 3.0 | 60 | 110 |
| L4 | 0.12 | 6.0 | 70 | 180 |
| L5 | 0.21 | 10.5 | 80 | 260 |
| L6 | 0.38 | 19.0 | 90 | 350 |
| L7+ | ... | ... | 100-110 | 450+ |

#### TP/SL 系統（出市條件）

**動態 TP（DynamicTP=1）：**
```
MA_TopReturnTF=5          # M5 MA回折偵測
MA_TopReturnPeriod1=5     # MA(5)
MA_TopReturnPeriod2=10    # MA(10)
MA_TopReturnShift=1       # 前一支bar
MA_TopReturnStart=30.0    # 跑咗30 pips後啟動
MA_TopReturnDist=5.0      # MA回折5 pips觸發TP
DynTP_DollarTrail=0.5     # $0.5追蹤
```

**金額 TP（DollarMode=1）：**
```
DollarStart=2.0           # 賺$2開始追蹤
DollarTrail=1.0           # 回落$1就TP
DollarBreakStart=2.0      # 賺$2後啟動保本
DollarBreakEven=1.0       # 保本$1
DollarLoss=0.0            # 無硬止損金額
```

**第0層（首層）TP：**
```
DollarMode0=1             # 第0層獨立金額TP
DollarStart0=2.0
DollarTrail0=1.0
DollarBreakStart0=2.0
DollarBreakEven0=1.0
```

**硬性止損：**
```
slInLevel=9               # 第9層止損
TradeCloseOnlyOnDD=15.0   # DD 15%全部平倉
TradeModeResetOnDD=15.0   # DD 15%重設
```

#### Cooldown（冷卻期）
```
CooldownAfterClose=1      # 平倉後冷卻
CooldownMA_TF=60          # H1 MA
CooldownMA_Period=25      # MA(25)
CooldownMA_Shift=1        
UseCooldownAfterClose=0   # 未啟用按分鐘冷卻
CooldownMinute=60         # 60分鐘
```

#### 新聞過濾
```
HighNews=1                # 高影響新聞
  HighIndentBefore=1440   # 前24小時
  HighIndentAfter=720     # 後12小時
NFPNews=1                 # 非農
  NFPIndentBefore=1440    # 前24小時
  NFPIndentAfter=720      # 後12小時
SpeaksNews=1              # 央行官員講話
  SpeaksIndentBefore=1440
  SpeaksIndentAfter=720
```

#### 其他
```
MaxSpread=3.0             # 最大點差
MaxSlippage=3.0           # 最大滑點
ExportSummaryReport=1     # 導出報告
SendBEDSignal=1           # 發送信號
```

---

## 3. 數據處理邏輯

### 3.1 倉位重構

CSV 中每一行是一筆獨立交易，但實際上多筆交易組成一個「倉位」。重構規則：

**分組鍵：Symbol + Direction + Close Time（容差 ±60 秒）**

> **改進說明**：加入 Direction 防止 BUY/SELL 被錯誤合併；加入時間容差處理批量平倉嘅 1-2 秒差異。

**部分平倉檢測：**
- 如果同 Symbol 嘅交易 Close Time 差距 > 5 分鐘 → 可能係部分平倉
- 標記為特殊倉位，分開統計

```
範例：
Open Time          | Symbol | Lots | Close Time         | Magic
2026-02-05 11:00   | GBPCHF | 0.02 | 2026-03-02 15:12   | 88    ← L1
2026-02-09 11:00   | GBPCHF | 0.04 | 2026-03-02 15:12   | 88    ← L2
2026-02-27 17:00   | GBPCHF | 0.21 | 2026-03-02 15:12   | 88    ← L5
2026-02-26 20:00   | GBPCHF | 0.12 | 2026-03-02 15:12   | 88    ← L4
```

同一 Symbol + 同一 Close Time = 一個倉位，包含 L1 到 L5。

**倉位級別統計：**
- 倉位總手數 = sum(Lots)
- 倉位總盈虧 = sum(Net Profit)
- 倉位最大層數 = max(layer)
- 倉位總持倉時間 = max(Close Time) - min(Open Time)

**層數判定：** 根據 Lots 推算（基於 lotExp）
- 0.02 = L1
- 0.04 = L2（0.02 × 1.8 ≈ 0.036，四捨五入到 0.04）
- 0.06 = L3
- 0.12 = L4
- 0.21 = L5
- 0.38 = L6

### 3.2 .set 解析

解析 key=value 格式，自動分類參數：

| 分類 | 前綴/關鍵字 |
|------|------------|
| 基本 | EA_NAME, EA_SYMBOL, EA_PERIOD, Trading_Mode |
| MA系統 | BasicMa*, EnterMa* |
| 濾鏡 | Use*, eff*, Vlt*, Corr* |
| 馬丁 | EntryLot, lotExp, pipstep* |
| TP/SL | Dollar*, DynamicTP, MA_TopReturn*, slInLevel |
| 新聞 | HighNews*, NFPNews*, SpeaksNews* |
| 冷卻 | Cooldown* |

---

## 4. 功能需求

### 4.1 Phase 1：MVP（核心分析）

#### F1：文件解析
- 讀取 .csv，自動識別欄位
- 讀取 .set，自動分類參數
- 支援一個 .csv 對應多個 .set（不同貨幣對不同設定）

#### F2：倉位重構
- 按 Symbol + Close Time 分組
- 自動識別層數（根據 Lots 推算）
- 計算倉位級別統計

#### F3：入市質量評估（兩層評分架構）

> **⚠️ 四方 Review 共識**：馬丁策略唔可以用「單筆 L1 表現」混合評估「多層策略」。ChatGPT 同 Deepseek 一致建議拆成兩層。

##### Layer 1：Entry Signal Quality（入市信號質量）

只評估每個倉位嘅**第 1 層（L1）**，純粹量度入市信號嘅好壞：

**維度 1：方向準確性（Direction，35%）**
- **⚠️ 關鍵修正**：用 `Max Pips` 而唔係 `Net Pips` 判斷方向
  - 原因：L1 可能 Max Pips=100 但最終 Net Pips=-10（因為加倉後才回歸）
  - 用 Net Pips 會誤判為「方向錯」，但其實入市方向係啱嘅
- Max Pips > 20 = 方向正確 ✅ / Max Pips ≤ 20 = 方向弱 ⚠️ / Max Pips ≈ 0 = 方向錯 ❌
- **方向強度**：min(Max Pips / 100, 1.0) 作為強度係數

**維度 2：入市時機（Timing，35%）**
- `Max Pips` = 入市後最大有利幅度
- `Max Loss Pips` = 入市後最大不利幅度
- **時機分數** = Max Pips / (Max Pips + |Max Loss Pips|)
  - 接近 1.0 = 即刻大賺 🟢 / 0.5 = 先虧再賺 🟡 / 接近 0.0 = 大幅浮虧 🔴
- **邊界處理**：Max Pips 同 |Max Loss Pips| 都 < 5 pips → 時機分數 = 0.5
- **馬丁修正**：多層倉位嘅 L1 本來就會承受較大浮虧（pipstep 設計），加入衰減因子減輕懲罰

**維度 3：初始回撤（Initial Drawdown，30%）**
- `Max Loss Pips` = L1 最大浮虧深度
- **回撤分數** = 1 - min(|Max Loss Pips| / 200, 1.0)
  - <50 pips = 小回撤 🟢 / 50-150 = 中等 🟡 / >150 = 大回撤 🔴

**Entry Score 評級：**
- 🟢 A（80-100）：入市信號優質
- 🟡 B（60-79）：入市信號一般
- 🟠 C（40-59）：入市信號偏弱
- 🔴 D（0-39）：入市信號差

---

##### Layer 2：Strategy Execution Quality（策略執行質量）

評估**整個倉位**（L1 到 LN）嘅策略執行效果：

**維度 1：回歸性（Regression，30%）**
- 高層數（L4+）倉位最終 Net Profit 正 vs 負嘅比例
- **分層回歸度**：每層嘅勝率（L1~55%, L4~75%, L6~95%）
  - L4+ 回歸度必須顯著高於 L1，否則馬丁無意義
- **Recovery Factor by Layer**：Net Profit / Max Floating Loss
  - 量化「賺得多但頂過好深 DD」嘅情況
- **Time-to-Recover**：L4+ 平均幾耐先回本
  - 成功但要 20 日 = 資金效率差

**維度 2：出場效率（Exit Efficiency，25%）**
- 贏倉：Net Profit / Max Profit（食咗幾多利潤）
- 輸倉：|Net Loss| / |Max Loss|（止損及唔及時）
- **TP 系統判定**：反推每個倉位係 DollarMode 定 DynamicTP 觸發出場
  - 如果 Net Pips < MA_TopReturnStart(30) 但接近 DollarStart/pip_value → DollarMode
  - 如果 Net Pips > 30 且 MA 回折明顯 → DynamicTP

**維度 3：風險控制（Risk Control，20%）**
- 最大層數、Max DD、DD 持續時間
- **Layer Escalation Probability**：P(L1→L2)、P(L2→L3)...
- **Margin Stress**：同時持倉嘅總手數（多貨幣對系統性風險）

**維度 4：收益質量（Profit Quality，15%）**
- Profit Factor、盈虧偏度（Skewness）
- 正偏度 = 偶爾大賺小虧（好）/ 負偏度 = 經常小賺偶爾大虧（馬丁失效特徵）

**維度 5：成本 + 持倉（Cost + Holding，10%）**
- Swap + Commission 佔比
- 持倉效率：每小時收益
- Exposure Time %：幾多時間有倉

---

##### 綜合評分

**Final Score = Entry Score × 0.4 + Strategy Score × 0.6**

> **為何 Strategy 佔 0.6？** 因為馬丁策略嘅核心價值在於多層後嘅回歸能力同出場效率，而非單純 L1 入市質量。L1 錯唔代表策略錯（係預期內），L1 好反而可能冇觸發盈利最大化。

**綜合評級：**
- 🟢 A（80-100）：策略優質，可 Copy
- 🟡 B（60-79）：策略一般，需評估
- 🟠 C（40-59）：策略偏弱，需調整
- 🔴 D（0-39）：策略差，不建議跟

#### F4：基礎統計

**整體統計：**
| 指標 | 計算方式 |
|------|---------|
| 總倉位數 | 重構後的倉位數量 |
| 總交易數 | CSV 行數 |
| 勝率 | Net Profit > 0 的倉位 / 總倉位 |
| 平均盈利 | 贏倉的平均 Net Profit |
| 平均虧損 | 輸倉的平均 Net Profit |
| 賠率（Avg W/L Ratio） | 平均盈利 / |平均虧損| |
| Profit Factor | 總盈利 / 總虧損 |
| Max DD（最大回撤） | 連續虧損最大值 |
| Max DD% | 最大回撤 / 最高淨值 |
| 平均層數 | 所有倉位的平均層數 |
| 平均持倉時間 | 所有倉位的平均持倉時間 |
| 總 Swap 成本 | 所有 Swap 的總和 |
| 總 Commission | 所有 Commission 的總和 |
| Sharpe Ratio | (平均收益 - 無風險利率) / 收益標準差 |
| Calmar Ratio | 總收益 / Max DD |
| Sortino Ratio | (平均收益 - 無風險利率) / 下行標準差 |
| 回撤恢復時間 | DD 底部到新高的天數 |
| 最大連虧倉位數 | 連續虧損的最大倉位數 |
| 最大連虧金額 | 連續虧損的最大金額 |
| 盈虧偏度（Skewness） | 正偏=偶爾大賺小虧（好），負偏=經常小賺偶爾大虧（差） |
| 盈虧中位數 vs 平均數 | median < mean = 正偏（好） |

**按貨幣對統計：**
- 每對貨幣獨立計算上述所有指標
- 排名：按 PF 或勝率排序
- 識別：最適合 / 最不適合該策略的貨幣對

**按層數統計：**
| 層數 | 出現次數 | 佔比 | 平均盈虧 | 勝率 |
|------|---------|------|---------|------|
| L1 only | — | — | — | — |
| L1-L2 | — | — | — | — |
| L1-L3 | — | — | — | — |
| L1-L4+ | — | — | — | — |

- **馬丁健康度**：L1 only 佔比越高越健康
- **風險回歸分析**：高層數倉位最終是否獲利回歸？

**按方向統計（BUY vs SELL）：**
- BUY（Magic=88）和 SELL（Magic=77）分別統計
- 識別策略是否偏向某個方向

**按時段統計：**
- 將 Open Time 按交易時段分組：
  - 亞洲盤（00:00-08:00 HKT）
  - 歐洲盤（14:00-22:00 HKT）
  - 美洲盤（21:00-05:00 HKT）
- 識別策略在哪個時段表現最好

#### F5：HTML 報告生成

**單一 HTML 文件，移動端友好：**

結構：
1. **摘要卡片**：策略名稱、期間、總盈虧、勝率、PF
2. **入市質量分佈圖**：A/B/C/D 各佔多少
3. **貨幣對排名表**：按 PF 排序，顏色標記
4. **層數分析**：各層出現頻率、盈虧
5. **時段分析**：哪個時段最適合
6. **交易明細表**：可排序、可篩選
7. **倉位詳情**：每個倉位的層數展開

---

### 4.2 Phase 2：深度分析

#### F6：馬丁層數風險分析

**風險隨層數遞增：**
- 每層的累計資金需求：L1=0.02, L2=0.06, L3=0.12, ..., L6=0.83
- 每層的最大浮虧（Max Loss Pips × Lots）
- **絕對風險金額**（唔只列 pips，要計 $）：
  - 到 L9 止損時，累計約 630 pips，0.83 總手數 ≈ $5,229（以 USDJPY 計）
- **pipstep 遞增模式分析**：線性（每次+10）vs 幾何（每次×1.5）的影響
  - 此策略為線性遞增：50→60→70→80→90→100→110
  - 意味著越深層數，平均成本越接近，不利於快速回歸

**層數風險指標：**
| 指標 | 說明 |
|------|------|
| 平均層數 | 越低越好 |
| L4+ 出現頻率 | 越低越好 |
| 破產風險等級 | L9=CRITICAL, L7+=HIGH, L5+=MEDIUM |
| 階梯式倉位分佈 | L1-only / L1-L2 / L1-L3 / L4+ 各佔多少 |

**回歸性分析（核心）：**

1. **分層回歸度**：每層的勝率（L1: ~55%, L2: ~60%, ... L6: ~95%）
   - 關鍵：L4+ 回歸度必須顯著高於 L1，否則馬丁無意義

2. **加倉效率**：每加一層，平均獲利提升多少
   - L4+ 平均 Net Profit 應顯著高於 L1-L3
   - 如果 L4+ 平均虧損 = 馬丁失效

3. **資金效率**：
   - 資金利用率 = 總盈利 / 最大風險暴露
   - 風險暴露 = Max Layers × Avg Lot Size

4. **實際案例驗證**：
   - 用 CSV 中 GBPAUD 6層打穿案例（-$627.57）展示風險
   - 用成功回歸案例展示馬丁有效性

#### F7：TP/SL 系統深度分析

**DynamicTP vs DollarMode 交互邏輯（⚠️ Review 重點）：**

兩個 TP 系統同時啟用：
1. `DynamicTP=1`：MA 回折偵測（跑 30 pips 後啟動，MA 回折 5 pips 觸發）
2. `DollarMode=1`：金額追蹤（賺 $2 啟動，回落 $1 觸發）

**交互分析：**
- L1 (0.02手)：DollarStart=$2 只需 ~10 pips 就達到 → **DollarMode 大概率先觸發**
- L6 (0.38手)：DollarStart=$2 只需 ~5.3 pips → DollarMode 極快觸發
- **結論**：DollarMode 在各層數都是主要出場機制，DynamicTP 只在特殊情況觸發
- `DynTP_DollarTrail=0.5` 可能是 DynamicTP 觸發後的額外追蹤，比 DollarTrail=$1.0 更緊

**DollarMode0 vs DollarMode 的區別：**
- DollarMode0 = L1 專用設定（Start=2.0, Trail=1.0）
- DollarMode = L2+ 設定（同樣 Start=2.0, Trail=1.0）
- 金額固定但不同層數的 pip 敏感度差異巨大
- L1: $2 trail ≈ 100 pips 的 20%；L6: $2 trail ≈ 5.3 pips 的 38%

**`DollarLoss=0.0` 風險：**
- 無硬止損金額，唯一止損是 slInLevel=9 + DD 15%
- 如果市場單邊快速移動，可能跳過 L9 導致更大虧損

**TP/SL 優化建議：**
- 分析 Max Profit / Max Pips 分佈百分位
- 建議 SL 設在 P75 或 P90 的 Max Loss Pips
- TSL 建議：Max Pips vs Net Pips 差距中位數

#### F8：Copy Trade 策略建議（基於原始數據）

**策略分級：**
- ⭐⭐⭐ **首選 Copy**：高勝率(>70%) + 高PF(>2.0) + 平均層數<2 + 回歸性好
- ⭐⭐ **可用 Copy**：中等勝率(50-70%) + PF>1.5 + 回歸性一般
- ⭐ **需調整**：勝率<50% 或 PF<1.0
- ❌ **不建議**：高層數依賴 + 回歸性差 + 大DD

**Copy 模式建議：**
- **Copy on Profit（跟勝）**：
  - 適合：高勝率、低層數
  - 建議：只跟 L1-L2，設定獨立硬止損
  - 倍數：按原始數據
- **Copy on Lose（跟虧加碼）**：
  - 適合：馬丁策略、回歸性好
  - 適合：馬丁策略、回歸性好
  - ⚠️ **唔好用固定 0.3x 倍數**，改用動態風險預算：
    - 最多承受 X% 賬戶 DD（如 10%）
    - Max layers cap（動態，基於當前賬戶餘額）
    - Equity stop（如 -10% 即停）
    - Symbol diversification limit（防止同方向貨幣對同時爆）
  - 獨立止損（唔等原倉位）

**資金管理建議：**
- 建議最低賬戶規模 = Max DD × 10
- 同時持倉分析：多貨幣對同時加層的系統性風險
- 歷史收益曲線：按時間排序的累計盈虧

**Copy Trade 模擬驗證：**
- 模擬 Copy on Profit / Copy on Lose 的歷史表現
- 輸出：勝率、PF、Max DD、年化收益
- 按不同止損層級模擬歷史收益曲線

---

### 4.3 Phase 3：知識庫 + 未來方向

#### F9：策略檔案
- 存入 Obsidian（Markdown + YAML frontmatter）
- 包含：策略名稱、版本、完整參數、歷史表現、評分

#### F10：策略比較
- 同一 EA 不同參數設定對比
- 不同 EA 同一貨幣對對比

#### F11：市況反推（未來方向）
- 不依賴外部數據
- 從策略參數和交易結果反推可能的市況特徵
- 例如：高層數 = 震盪市、快進快出 = 趨勢市

---

## 5. 輸出格式

### 5.1 HTML 分析報告
- 單一 HTML 文件，移動端友好
- 明亮主題
- 繁體中文
- 包含：摘要卡片、統計表格、貨幣對排名、交易明細

### 5.2 結構化數據（JSON）
```json
{
  "strategy_id": "14581_SMA_v3.00",
  "analysis_date": "2026-04-24",
  "date_range": {"from": "2025-11-01", "to": "2026-03-02"},
  "overall_stats": {
    "total_positions": 0,
    "win_rate": 0,
    "profit_factor": 0,
    "max_dd": 0,
    "avg_layers": 0
  },
  "symbol_stats": [...],
  "layer_stats": [...],
  "positions": [
    {
      "symbol": "USDJPY",
      "direction": "BUY",
      "layers": 3,
      "total_lots": 0.12,
      "net_profit": 10.5,
      "entry_quality_score": 85,
      "entry_quality_grade": "A",
      "trades": [...]
    }
  ],
  "recommendations": {
    "copy_grade": "⭐⭐⭐",
    "copy_mode": "Copy on Profit",
    "reason": "..."
  }
}
```

### 5.3 Obsidian 策略檔案
```markdown
---
type: strategy_profile
ea: SMA v3.00
version: "20250805"
signal_page: "14581"
analysis_date: 2026-04-24
copy_grade: "⭐⭐⭐"
tags: [strategy, forex, sma, martin]
---

# SMA v3.00 - Signal #14581

## 策略概述
...

## 參數設定
...

## 歷史表現
...
```

---

## 6. 技術架構

### 6.1 技術棧
- **語言**：Python 3
- **數據處理**：Pandas
- **報告生成**：Jinja2 HTML 模板
- **交互方式**：CLI 腳本（初期）→ Telegram Bot 上傳（後期）

### 6.2 目錄結構
```
trade_strategy_analyzer/
├── PRD.md                    # 本文件
├── samples/                  # 範例數據
│   ├── signal_14581_trades.csv
│   ├── SMA_v3.00_USDJPY_H4.set
│   └── SMA_v3.00_USDCHF_H1.set
├── src/
│   ├── __init__.py
│   ├── csv_parser.py         # CSV 解析
│   ├── set_parser.py         # .set 解析
│   ├── position_builder.py   # 倉位重構
│   ├── entry_quality.py      # 入市質量評估
│   ├── statistics.py         # 統計計算
│   ├── report_generator.py   # HTML 報告
│   └── templates/
│       └── report.html       # HTML 模板
├── output/                   # 輸出目錄
└── requirements.txt
```

### 6.3 運行方式
```bash
# Phase 1 MVP
python3 -m src.main \
  --csv samples/signal_14581_trades.csv \
  --set samples/SMA_v3.00_USDJPY_H4.set \
  --set samples/SMA_v3.00_USDCHF_H1.set \
  --output output/report_14581.html
```

---

## 7. 已確認決策

| # | 問題 | 決策 |
|---|------|------|
| 1 | 入市質量評分 | 盡量利用 CSV 內所有相關欄位，6 個維度加權評估 |
| 2 | 馬丁層數分析 | 層數越大=風險越大，分析回歸性（高層數最終是否獲利） |
| 3 | Copy Trade 倍數 | 暫時按原始數據，不做複雜計算 |
| 4 | 市況分類 | 暫不做，將來從參數+產品特性反推（Phase 3） |
| 5 | 多策略組合 | 待定（Phase 3） |

---

## 8. 待確認事項

| # | 問題 | 影響 | 狀態 |
|---|------|------|------|
| 1 | `UseAISignal=1` 的具體邏輯是什麼？ | 入市條件可能不完整 | ⚠️ 待確認 |
| 2 | 一個信號頁是否只跑一個 EA？ | 策略歸類 | ⚠️ 待確認 |
| 3 | CSV 中同 Symbol 同 Close Time 但不同 Magic Number？ | 倉位重構邏輯 | ⚠️ 待確認 |
| 4 | `.set` 檔名規則是否固定？ | 自動識別 | ⚠️ 待確認 |

---

## 9. 開發計劃

### Phase 1：MVP
- [ ] csv_parser.py — CSV 讀取與解析
- [ ] set_parser.py — .set 讀取與參數分類
- [ ] position_builder.py — 倉位重構（Symbol + Direction + Close Time 分組，容差 ±60s）
- [ ] entry_quality.py — 6 維度入市質量評估（含回歸性維度）
- [ ] statistics.py — 整體/貨幣對/層數/時段統計（含 Sharpe/Calmar/Sortino）
- [ ] equity_curve.py — 歷史收益曲線
- [ ] report_generator.py — HTML 報告生成
- [ ] 整合測試（用 sample 數據）

### Phase 2：深度分析
- [ ] 馬丁層數風險分析（回歸性）
- [ ] TP/SL 優化建議
- [ ] Copy Trade 策略分級與建議
- [ ] JSON 輸出格式

### Phase 3：知識庫 + 未來
- [ ] Obsidian 策略檔案生成
- [ ] 策略比較功能
- [ ] 市況反推（從參數+結果反推市況）
- [ ] 多策略組合分析

---

*此 PRD v0.2 待多模型 Review 後定稿。*
