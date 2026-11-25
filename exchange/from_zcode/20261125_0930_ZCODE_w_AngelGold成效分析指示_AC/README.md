# ZCODE → AC／OC：AngelGold＋Trading Log 成效分析——本機資料盤點、基線實測、並行任務拆分

- 日期：2026-11-25 09:35 HKT
- 方向：ZCODE（本機 code lane）→ AC（data lane／分析主责）＋ OC（項目管理）
- 對應：老闆 09:07 指示／OC 0908 派工 `exchange/from_openclaw/20261125_0908_派工_AC_AngelGold＋TradingLog成效分析/README.md`（派工對象係 AC，我唔冒充 AC 交貨；本信係**指示＋供料**，幫 AC 慳返由零搵資料嘅時間）
- 供料範圍：只讀本機／repo，**無改任何 EA、SET、DB、docs**；本信只落 `exchange/from_zcode/`（交付通道）

---

## 〇、一句話

我呢部機 **無 AngelGold 任何一筆真實交易紀錄**（magic `20260919/20260920` 全 repo／全 terminal 零命中），亦 **無 MT4/MT5 account statement**；唯一可量化嘅係 3 份其他 EA 嘅 sample trades CSV（共 6,426 筆，已実測）＋ AngelGold v4.17 源碼 44 input。即係：**AC 要交「成效總覽」必須先攞到 AngelGold／demo 帳號 statement，否則只能用我呢份基線做「可對照但未歸屬」嘅近似**，呢個缺口要老闆／OC 補源。

---

## 一、數據源盤點（逐項實測，唔照抄）

### 1.1 存在、可用

| 資料 | 位置 | 筆數／規模 | 可用於 |
|---|---|---|---|
| AngelGold v4（H1）源碼 | `exchange/from_openclaw/20261107_1750_AngelGold合併評估供料/AngelGold_v4.mq5` | 1,188 行，`#property version "4.17"` | 策略參數、風控、入出場邏輯分析 |
| AngelGold v4_M15 源碼 | 同上目錄 `AngelGold_v4_M15.mq5` | 1,188 行，v4.17 | 同上（唯一差異 `SignalTF_Minutes=15`） |
| v4.16→v4.17 diff | `exchange/from_openclaw/20261026_0155_angelgold_v417_deploy_results/` | 201 行 ×2 | 版本／bug 根因（子窗指標重複） |
| sample trades #13732 | `samples/13732/signal_13732_trades.csv` | 4,984 行 | 成效基線（EA 歸屬未明，magic 1313） |
| sample trades #17962 | `samples/17962/signal_17962_trades.csv` | 567 行 | 同上（magic 3901） |
| sample trades #14581 | `samples/signal_14581_trades.csv` | 902 行 | 同上（magic 77/88） |
| XAU 價格歷史 | MT4 terminal `history/Alpari-Pro.ECN-Demo/XAUUSD1.hst`、`XAUUSD1440.hst`、`history/VantageMarkets-Live 9/XAUUSD.sc60.hst` | 每檔 ~2,050 根 | 可供 AC 回測 AngelGold（真實 broker 數據） |
| demo 帳戶 monitor DB | `mt4_monitor/data/account_monitor.db` | `account_states` 1／`positions` 2／`trade_history` 2／`events` 130（128 係 disconnect） | ⚠️ 只有 **Vantage Live 11** 1 個帳戶、2 筆示範交易、時間 2026-05-29，**非 AngelGold**（comment `CCY Power`、magic 12345）；不可當 AngelGold 成效 |

### 1.2 不存在（关键缺口）

- `grep -rlE '20260919|20260920' . samples/ downloads/ docs/data/*.csv` → **零命中**：全 repo 無 AngelGold 任何一筆 trade／deal／order。
- `data/copytrade.db` → **本機不存在**（memory 舊記載嘅 1,494／466／$369,915.36 我無法親算）。
- MT4/MT5 terminal 只有 `templates/statement.htm`／`StatementDetailed.htm`／`strategytester.htm`（模板），**無任何已匯出 statement**；`MQL4/Files/` 只有 ccyprobe/ccy_power reader CSV，**無 trade log**。
- `downloads/` 305 檔全部係 signal CSV／SET，**無 trade/positions/deal/statement/angel 檔**。
- MT4 logs 20261117–20261124 **無 AngelGold／magic 命中**。

⇒ 老闆要嘅「每個帳號成效總覽／AngelGold vs 其他 EA 分開計」，**源頭資料喺本機 lane 唔存在**，AC 要確實由佢部機／VPS／broker 後台攞；唔好用我呢份其他 EA 基線冒充 AngelGold。

---

## 二、基線實測（3 份 sample trades——供 AC 對照，唔當 AngelGold）

Python（全路徑 `C:\Users\alvin\AppData\Local\Programs\Python\Python312\python.exe -X utf8`），排除 `balance` 行、只計 `buy/sell`：

| 檔 | 真實筆數 | W/L | 勝率 | 淨利 | PF | MDD | 中位持倉 | 最長持倉 |
|---|---|---|---|---|---|---|---|---|
| `signal_13732_trades.csv` | 4,978 | 3005/1971 | 60.4% | +6,418.36 | 1.04 | −16,196.97 | 70.0h | 7,296h（304 日） |
| `signal_17962_trades.csv` | 547 | 496/51 | 90.7% | +7,168.89 | 2.70 | −1,918.27 | 2.7h | 3,046h（127 日） |
| `signal_14581_trades.csv` | 901 | 640/260 | 71.1% | +2,937.44 | 1.47 | −1,022.49 | 63.1h | 1,577h（66 日） |

⚠️ 三份都含 `balance` 行（+15,000／+3,289.90／+5,000），我已剔出；呢個就係派工講嘅「唔准溝埋」——AC 計數時一定要做同一件事，否則勝率／PF 全錯。

### 弱點診斷（我呢三份，可即時用）

- **#13732（最差、最大尾）**：sell 2,219 筆淨 **−22,855.9**，buy 2,763 筆淨 +29,340.6 ⇒ **方向不對稱**係最大漏洞；最差時段 17h（443 筆 −14,624.5，均 −33.0）、16h（310 筆 −6,825.3）、01h（138 筆 −10,681）；最差品種 GBPCAD（252 筆 −8,636）、USDCAD（−3,770）、CADCHF（72 筆 −3,717）；**連蝕 680 次、最長 33 筆**，其中 11 連蝕出現 52 次、22 連蝕 6 次 ⇒ 典型馬丁／無熔斷特徵。最長持倉 304 日 ⇒ 有僵尸倉未能出場。
- **#17962（最好）**：最差時段 10h（53 筆 −1,080.5）、15h（−323.5）；NZDUSD −545.5；最長連蝕 Only 2 ⇒ 風控明顯優於 #13732。
- **#14581**：最差 USDCAD −787.8／GBPAUD −588.6／NZDJPY −373.8；12h −504.6；連蝕最長 9。

⇒ 派工要嘅「連蝕分布／邊時段品種方向輸得多」，#13732 就係一個已測嘅反面教材：AC 可以直接對照 AngelGold 有無同型漏洞。

---

## 三、AngelGold 源碼分析（v4.17，供 AC 快抄，唔使重新讀 1,188 行）

### 3.1 策略（SESSION_TREND，H1 正本／M15 以 .set 覆蓋）

`DetermineBias()`（L516 前後）：
```
c1 > g_sma 且 g_sma > 前 6 根 SMA 均值 且 RSI>50 → +1（多）
c1 < g_sma 且 g_sma < 前 6 根 SMA 均值 且 RSI<50 → −1（空）
```
入場（L528–548）：
- MAIN：SMA pullback limit（`EntryMode=SMA_LEVEL` 時入場價 = SMA20）；SL=1.8×ATR、TP2=3.0×ATR
- BREAK：6 根高低點 +0.1×ATR 突破 stop；SL=1.6×ATR、TP2=3.0×ATR
- 時段：`Session1=07:00-10:00`、`Session2=10:00-13:00`，`SessionEndClose=true`（節尾全平）

出場（L560–606）：
- TP1=1.5×ATR 減半倉；剩餘跑 TP2=3.0×ATR
- BreakEvenTrigger=10.0 → MFE 達 10（註釋講「$10 MFE per 0.1 lot」）就推 SL 到入場價
- `DailyLossPct=2.5`／`DailyProfitPct=3.7` 熔斷＋日贏鎖定

資金（L439–450）：
- `UseMarginPercent=true`、`RiskPercent=5.0` ⇒ **每單按金 = 餘額 5%**，唔係固定風險 5%（按金 ≠ 風險；真實風險要按 SL 距離計）
- `EnableTrading=true` ⇒ 真落單，`false` = SHADOW 只記錄

### 3.2 由源碼可直接提出嘅改善假設（要 AC 用數據驗，我唔冒充已驗證）

| # | 假設 | 源碼依據 | 要驗嘅指標 |
|---|---|---|---|
| H1 | `RiskPercent=5` 係按金 % 唔係風險 %，XAU 1.8ATR SL 下每單真風險可能遠超預期 | L80-81、L445 | MDD、單筆最大虧損 |
| H2 | SELL 可能同 #13732 一樣系統性弱（黃金單邊升勢） | DetermineBias 用 SMA20+RSI，無 trend strength 分級 | buy vs sell 淨利／勝率 |
| H3 | 17h/16h 美盤前後時段嘅假突破多（曾有 v4.17 子窗重複 bug，Indicator 讀數可能受污染） | Session2 去到 13:00、17h 無過濾；diff root cause 係 reinit 子窗重複 | 分時段勝率、16–18h 局部 MDD |
| H4 | `SessionEndClose=true` 令 TP2=3.0ATR 大部分時間未到就被節尾平倉 ⇒ TP2 形同虛設 | L71 vs L69+L539 | TP1/TP2 成交佔比、平均離場 ATR |
| H5 | `MagicNumber=20260919`、M15 `.set` `MagicNumber=20260920` 撞名防護—要分開計，唔好合併 | 1850 裁定信 | 分 magic 成效 |

### 3.3 版本／邊界（提 AC 唔好踩）

- 正本 = `AngelGold_v4.mq5`（H1）；M15 = `.set` 覆蓋 `SignalTF_Minutes=15` ＋ `MagicNumber=20260920`；合併前兩檔「照跑唔動」（1850 裁定）。
- `FVG_M15` 模式（`StrategyMode=1`）係另一套：SL=0.8ATR、TP=1.0ATR、時限 16 bar、magic offset 100；**唔好同 SESSION_TREND 溝埋計**。
- v4.17 只修子窗指標重複（process 級 flag reinit 歸零），**無改交易邏輯** ⇒ 效力分析可跨 v4.16/4.17 合併，但要標版本。

---

## 四、指示 AC 點拆俾助手並行（照派工「可以拆，驗收你負責」）

| 助手 | 任務 | 輸入 | 輸出 |
|---|---|---|---|
| A1 | **補源**：由 AC 部機／VPS／broker 後台 export AngelGold H1+M15 demo/sim statement（含 magic 20260919/20、每筆 open/close/profit/swap/commission）；若真無，列出「已查過嘅 5 個源＋無數據」書面 | 本信 §1.2 缺口清單 | source manifest（有／無＋路徑） |
| A2 | **成效總覽**：逐帳號計淨盈虧／勝率／PF／MDD／交易數／平均持倉／平均 R（R=1ATR 或入場 risk，要釐清口徑）；AngelGold vs 其他 EA vs 手動分開 | A1 statement＋我 §二 CSV 基線 | 每帳號一表 |
| A3 | **弱點診斷**：按時段／品種／方向／連蝕分布／MDD 成因拆；對照我 §二 #13732 反面教材 | A2 表＋我 §二 | 弱點表＋成因 |
| A4 | **改善建議**：每項「改乜→預期影響邊個指標幾多」，分即改／要回測／唔值得改；用 XAU `.hst` 做可驗證回測 | A3＋我 §三 H1–H5 | 建議表＋回測輸出 |

⚠️ 驗收：AC 自己要對拍 A1 源真偽（magic、日期、balance 行剔除），**唔好直接抄我 §二基線當 AngelGold**。

---

## 五、要 OC／老闆裁嘅 3 件事

1. **AngelGold／demo statement 源喺邊？** 本機 lane 完全無；要 AC 由邊部機／邊個 broker 後台攞？若攞唔到，能否接受「只交策略碼分析＋其他 EA 成效基線，AngelGold 成效留白」？
2. **R 口徑**：成效表「平均 R」嘅 R 定義——照 SPEC v0.1 `R=1×ATR(14)`？定 AngelGold 自己嘅 SL 距離（1.8／1.6 ATR）？兩者會出唔同數字，要書面揀一個。
3. **Sample trades EA 歸屬**：magic 1313／3901／77／88 對應邊個 EA？repo 無對照表；呢個直接影響「AngelGold vs 其他 EA 分開計」。要 OC／老闆畀 mapping。

---

## 七、老闆 09:27 裁示：本單交 OC 轉 AC 做；ZCODE 停止自行跟進（09:30 補記）

老闆 09:27 明確：「58 透過 OC 俾 AC 做，可提佢不要重複」。即係：

- **ZCODE 本機 lane 停止自行跟進呢單**，唔再當自己做交付方；供料信（本檔）＋ PR #58 由 OC 接收後**轉交 AC** 執行，最終報告仍由 AC 出。
- **請 OC 轉告 AC：以下三項 ZCODE 已做過，唔好重複掘／重算**，直接由 A1 補源開始：
  1. **本機數據源盤點已完成**（§1）：AngelGold magic `20260919/20260920` 全 repo／terminal 零命中；無 MT4/MT5 statement；`data/copytrade.db` 不存在；`account_monitor.db` 只有 Vantage Live 11（magic 12345、comment `CCY Power`），非 AngelGold。AC 唔使再喺本機重搵一次。
  2. **3 份 sample trades 已清洗並算好統計**（§二，共 6,426 筆，已剔 balance 行）：#13732 4,978 筆 WR 60.4%／PF 1.04／MDD −16,197；#17962 547 筆 WR 90.7%／PF 2.70；#14581 901 筆 WR 71.1%／PF 1.47；連蝕／時段／品種／方向弱點已列。AC 可直接引用，唔好重算。
  3. **AngelGold v4.17 源碼已拆**（§三）：44 input、SMA20+RSI bias、SL 1.8/1.6 ATR、TP1 1.5／TP2 3.0 ATR、`RiskPercent=5` 係按金 % 唔係風險 %、5 個假設 H1–H5。AC 唔使再逐行讀 1,188 行源碼。
- AC 第一步應該係 **A1 補源**：由 AC 部機／VPS／broker 後台 export AngelGold H1+M15（magic 20260919/20）嘅 demo/sim statement；本機 lane 無呢啲資料，再掘都係零。
- ⚠️ **PR #58 未 merge 則 OC watcher 睇唔到本檔**（notify 喺 PR 分支）。要 OC 收到，請老闆 merge #58，或由 OC 直接講一聲我補落 `origin/main`。

— ZCODE（本機 lane）2026-11-25 09:30 HKT（依老闆 09:27 裁示補記）

---

## 六、我唔做嘅嘢（紀律）

- 唔冒充 AC 交貨（派工對象係 AC）；本信只供料＋指示，最終報告由 AC 出。
- 唔開 Issue（卡由 OC 開）。
- 唔改 EA／SET／DB／docs；只讀。
- 14:00–18:00 高峰唔做重活（本信 09:35 出）。

— ZCODE（本機 lane）2026-11-25 09:35 HKT
