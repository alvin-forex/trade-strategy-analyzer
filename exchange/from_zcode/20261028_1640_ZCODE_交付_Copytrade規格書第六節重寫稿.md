---
方向: ZCODE_w → OpenClaw（副本老闆）
日期: 2026-10-28 16:40 HKT
性質: 交付——COPY_TRADE 規格書第六節重寫稿（老闆 07:51 三組決定＋16:08 派工）
對應: 你 16:15 派工信（驗收四條）＋老闆已批參數（商品範圍/Pip 基準/Margin/輸出/模擬器）
---

# 第六節重寫稿：核心計算定義（唯一權威）

**用法**：以下 `## 六、` 起至 `---` 止，整段替換主檔 `COPY_TRADE_SYSTEM_SPEC` 第六節（v1.1 行 224–312）。行文風格、表格、公式塊跟主檔一致；可直接併入。

**本稿對 v1.1 第六節的修正清單**（併入前請過目）：

| # | 位置 | v1.1 原文 | 本稿 | 修正理由 |
|---|---|---|---|---|
| 1 | 6.2 | 公式為主，tick_value 為輔 | **tick_value 唯一權威，公式降級離線對照** | 老闆批核選項 (a)；tick_value 內含合約×報價幣×慣例，公式重建必錯（BTC 1000 倍為證） |
| 2 | 6.3 式 B | `net_pips × pip_value_usd / pip_size × lots` | 改為 `net_pips × pip_value_usd × lots` | 量綱 slip：v1.1 的 6.2 定義 pip_value_usd 已係「USD/pip/lot」，再 ÷pip_size 會大 10⁴ 倍。實測「兩式差 <0.01」係用正確量綱做出嚟嘅；本稿只修正 notation，唔推翻實測 |
| 3 | 6.5 | 浮虧公式寫 `(price_N − entry_i)` 但叫「浮虧」 | 改為 `(entry_i − price_N)`，並鎖死符號約定「正數＝蝕」 | 原式算出嚟係利潤符號；照抄實作會令警戒判斷反號 |
| 4 | 6.2/6.4 | `quote_rate` 無定義方向 | 鎖死 `fx(q) ≡ 1 單位報價幣 = ? USD`，修正式相應改寫 | 匯率方向寫反即係 150 倍級錯誤（JPY）；加 ±2× sanity band 防逆轉 |
| 5 | 全節 | 無已批參數、無 P0 定義域 | 加 **6.0 落鎖表＋P0 商品清單**、**6.7 實作守則＋歷史教訓表** | 與第九節已批 4+1 參數零矛盾；教訓入文防重犯 |
| 6 | 6.2 論證 | 引「19/30 商品 CV>20%」 | 改引 v1.1 更正版證據（逐月中位漂移＋單一固定值誤差中位 2.2%／最差 7.5%） | 主檔附錄 A 已將 CV 19/30 標「作廢」（小分母統計誤用）——你 16:15 派工信引用該數時請一併更正，以免併入後自相矛盾 |

---

## 六、核心計算定義（唯一權威）

這一節是整份規格書最需要精確的部分。所有模組必須完全依此實作，不得自行變體。

**權威鏈**（讀定義前先記住這一條）：

```
MT5（broker 權威）→ L0 symbols 表 → L1 計算器 → 全部下游
        └── 任何一環用「猜／慣例／硬編碼」代替讀表，即視為缺陷
```

### 6.0 適用範圍與已批參數

本節所有定義只對下列 **P0 商品域**（老闆已批，2026-10-28）保證：

```
28 外匯對（AUDCAD … USDJPY，含 8 個 JPY 交叉盤）＋ XAUUSD ＋ BTCUSD　＝　30 個
```

XAGUSD、指數（SP500.r／NAS100.r 等）屬第二步：**交易記錄到位、且完成 L0 導出後先納入**，本節定義對佢哋自動生效（同一套公式，無需改動），但 P0 期不出數字。

**已批參數落鎖表**（本節出現的每個參數都溯源到呢度，與第九節零矛盾）：

| # | 參數 | 已批值 | 本節落點 |
|---|---|---|---|
| 1 | 商品範圍 | 28 對＋金＋BTC 先行；白銀／指數第二步 | 6.0（本節） |
| 2 | Pip 基準 | **(a) MT5 `tick_value` 唯一權威** | 6.2 |
| 3 | Margin | 槓桿**可配置，預設 500** | 6.4 |
| 4 | 輸出形式 | **SQLite 先行**（P0），HTML/P2 | 6.7 鐵律三 |
| 5 | 現有模擬器 | **改造 `copy_trade_sim.py`，唔重寫** | 6.2 改造注意 |

### 6.1 Pip 大小（`pip_size`）

**不由程式判斷，由 L0 導出。** 對照規則如下，但以 MT5 回報值為準：

| 商品類 | `pip_size` | 說明 |
|---|---|---|
| 一般外匯 | `point × 10` | 5 位報價時 point=0.00001，pip=0.0001 |
| JPY 報價 | `point × 10` | 3 位報價時 point=0.001，pip=0.01 |
| XAUUSD | 0.1 | 慣例 2 位報價，pip = 0.1 |
| XAGUSD（第二步） | 0.01 | 慣例 3 位報價 |
| 指數（第二步） | `point × 1` | 通常 point=1 |
| BTCUSD | 1.0 | 依 broker |

**歷史教訓（本表存在的理由）**：現行 `copy_trade_sim.py` 寫死 XAU=0.1、`calc_usd_value.py` 寫死 0.01，兩檔各自內部一致，**但 CSV 的 Net Pips 只同 0.1 嗰套吻合**——配錯表即全數少算 10 倍（實測案例：XAUUSD 價差 3.00／Net Pips 30.00／6.98 手 → 淨利 $2,094，用 0.01 套會計出 $209）。慣例係 broker 選擇，唔係數學推論，所以唯一安全來源係讀表。

```python
def pip_size(sym, specs) -> float:
    ps = specs[sym].pip_size          # L0 導出；缺列 → raise MissingSpec，不准估算
    assert ps > 0
    return ps                          # 全系統禁止出現 pip_size 常數表
```

### 6.2 Pip 價值（`pip_value_usd`）——tick_value 唯一權威

**權威定義**（老闆已批選項 (a)，2026-10-28）：

```
pip_value_usd ≡ 每 1 pip、每 1.0 手嘅 USD 金額（單位：USD/pip/lot）

pip_value_usd(sym, date) = tick_value × (pip_size / tick_size)
```

`tick_value`、`tick_size`、`pip_size` 全部來自 `symbols` 表（L0 導出，MQL5 `SymbolInfoDouble`）。

**為什麼 tick_value 係權威而公式唔係**——pip_value 實際上係三層相乘：

| 層 | 內容 | 實測錯誤案例 |
|---|---|---|
| 1 | pip 單位慣例 | XAU 0.10 vs 0.01 兩檔並存（差 10 倍） |
| 2 | 合約大小 | BTCUSD 0.01 枚被當 100,000 單位（**多算 1000 倍**：$10 vs $0.01）；白銀 5,000 盎司被當 100,000（少算 5 倍） |
| 3 | 報價幣→USD 匯率 | JPY 系逐月中位漂移 10–15%；CHF 系 16–38% |

`tick_value` 由 broker 定義，**已內含層 1×2×3**。用公式重建等於自己再砌一次三層——層 1、2 係慣例（冇得推），層 3 會漂移。單一固定 pip_value 全期重算嘅實測誤差：**中位 2.2%、最差（AUDCHF）7.5%**——對交易系統足夠令一筆由賺變蝕，所以層 3 必須按日修正（見下），但層 1、2 冇任何公式可以救，只有讀表。

**離線對照式（降級：只驗數據品質，唔作計算來源）**：

```
pip_value_cross(sym, date) = contract_size × pip_size × fx(quote, date)
```

其中 `contract_size` 同樣讀 `symbols` 表（唔准硬編碼），`fx` 定義見下。對照流程（M1 每月或每次 M0 重導出後跑一次）：

```python
def cross_check(sym, specs, fx):
    pv_auth  = specs[sym].tick_value * (specs[sym].pip_size / specs[sym].tick_size)
    pv_cross = specs[sym].contract_size * specs[sym].pip_size * fx[sym]
    if abs(pv_auth - pv_cross) / pv_auth > 0.02:      # 2% 閘門
        flag(f"SPECS_MISMATCH {sym}")                  # 人工查 L0 導出；期間該商品照出數（以 tick_value 為準）
```

**兩者關係（一句講死）**：對照式與權威式共用同一個 `contract_size` 與 `pip_size`，所以佢**捉到 L0 導出錯誤同匯率異常，捉唔到慣例選擇錯誤**（慣例錯兩邊一齊錯）。慣例由 **6.3 兩式交叉驗證**對 CSV 真實成交捉。計算永遠以 `tick_value` 式為準；對照偏離 >2% 時先懷疑 L0 導出，唔准反過嚟用公式值頂上。

**按日修正（歷史回測用）**——只修正「層 3 匯率成分」：

> **fx 方向鎖死**：`fx(q, date) ≡ 1 單位報價幣兌 X USD`（例：fx(JPY)=0.00667）。方向寫反即係 ~150 倍級錯誤，本定義唔准有第二種解讀。

```python
def pip_value_usd(sym, date, specs, fx) -> float:
    sp = specs[sym]                                   # 缺 → raise MissingSpec
    pv_ref = sp.tick_value * (sp.pip_size / sp.tick_size)
    if sp.quote_currency == 'USD':
        return pv_ref                                 # USD 報價恆定（實測漂移 0–6%，屬量化噪音，唔修正）
    r_ref = fx[sym].at_export_date                    # L0 導出當日 fx
    r_now = fx[sym].at(date)                          # 缺當日 fx → raise，唔准用最近值頂
    pv = pv_ref * (r_now / r_ref)
    assert 0.5 <= pv / pv_ref <= 2.0                  # sanity band：真漂移最惡 38%/月，2 倍即方向反轉
    return pv
```

**改造注意（已批：模擬器改造唔重寫）**：`copy_trade_sim.py` 的 `_estimate_pip_value()` **整個刪除**（其 `symbol.endswith('USD') → 10.0` 規則正正係 BTCUSD 1000 倍錯誤嘅來源），改為呼叫本節 `pip_value_usd`；`calc_usd_value.py` 降為對照式的參考實作，標註「非權威」。任何檔案不准再有第二份 pip 常數表。

### 6.3 單筆盈虧（兩式交叉驗證——全鏈品質閘門）

```
方向符號：BUY = +1，SELL = −1
式 A（價差式，唔依賴任何 pip 慣例）：
    profit_usd = (close_price − open_price) × direction × lots × contract_size
式 B（pips 式，依賴 6.1＋6.2 全鏈）：
    profit_usd = net_pips × pip_value_usd × lots
```

> **量綱鎖死**：`pip_value_usd` 已係 USD/pip/lot（6.2 定義），所以式 B 係**乘法**。v1.0 原文寫 `÷ pip_size` 係 notation slip，照抄實作會錯 10⁴ 倍。CSV 的 `net_pips` 已按 broker pip 慣例計好（實測 XAU：價差 3.00 ↔ Net Pips 30.00 ↔ pip 0.1），L2 只轉換、唔重算；若必須由價差自行計 pips，一律用 `symbols.pip_size`。

**交叉驗證（L2 強制品質閘門）**：

```python
def verify_trade(t, specs, fx):
    pv = pip_value_usd(t.symbol, t.date, specs, fx)        # 6.2 權威
    a = (t.close - t.open) * direction(t.type) * t.lots * specs[t.symbol].contract_size
    b = t.net_pips * pv * t.lots
    if abs(a - b) > 0.01:                                   # 實測樣本差異 < 0.01
        t.qc_flag = 'SUSPECT'                               # 不參與統計，報告列明
    return a
```

呢條檢查嘅價值在於：式 A 純粹係「價差 × 合約」，對 pip 慣例免疫；式 B 依賴慣例＋合約＋tick_value 全鏈。**兩式吻合 = 6.1、6.2 成條鏈正確**；偏離 = 鏈上有錯，而且一定捉到（XAU 10 倍案例：30 pips 配錯 0.01 套，式 B 立即跌出 0.01 USD 閘門）。每筆都跑，唔抽樣。

### 6.4 保證金（`margin_usd`）

```
margin_usd(sym, date, lots) = lots × contract_size × price(date) × fx(quote, date) ÷ leverage
                            = lots × margin_per_lot(sym, date)
```

- **`leverage` 可配置，預設 500**（老闆已批；Vantage demo 實測值）。配置放 `config`（env／settings 檔），**唔准寫死喺 code**——唔同帳戶類型不同，寫死會後悔。
- `fx` 沿用 6.2 方向定義。USD 報價商品 fx=1；**JPY 交叉盤漏乘 fx 係 ~150 倍級錯誤**（notional 係 ¥，唔係 $）——呢個係 6.5 爆倉計算最常見嘅隱形炸彈。
- `contract_size × price` 係報價幣 notional；乘 `fx` 先係 USD notional。

累積至第 N 層：

```
lots_cum(N)   = Σ lots_i        i = 1..N
margin_cum(N) = Σ margin_usd_i  i = 1..N
```

離線對照（非權威）：MT5 `margin_initial`（導出當日每手保證金）× price(date)/price_ref，偏差 >2% 查 fx 或 price 源。

### 6.5 爆倉層級（警戒線）

> **符號約定鎖死：浮虧以正數表示蝕錢。** v1.0 原文 `(price_N − entry_i)` 算出嚟係利潤符號，照抄會令警戒判斷反號。

```
浮虧_usd(N) = Σ [ (entry_i − price_N) × direction × lots_i × contract_size ]   i = 1..N
```

```python
def breach_layer(cycle, equity, maintain_ratio=0.5, leverage=None):
    margin_cum = 0.0
    for N, layer in enumerate(cycle.layers, start=1):
        margin_cum += margin_usd(cycle.symbol, layer.open_date, layer.lots, leverage)
        float_loss = sum(
            (layer_i.entry - price_at(cycle.symbol, layer_i.time))
            * direction(cycle.direction) * layer_i.lots
            * specs[cycle.symbol].contract_size
            for layer_i in cycle.layers[:N]
        )
        if equity - float_loss < margin_cum * maintain_ratio:    # 保證金維持率警戒
            return N                                             # 第 N 層觸發
    return None
```

**建議輸出**：對每個策略算出「在 99% 歷史最壞行情下，第幾層會觸發警戒」。呢個數字直接回答「我應該預備幾多本金」。實測 XAUUSD：L11 保證金 $2,030（本金 $10,000 的 20%），L15 理論值 $8,690（87%）——實際 L13 前就會觸發警戒。

### 6.6 分期回報

```
保證金回報率 = 該期淨利 ÷ 該期峰值保證金佔用（margin_peak）
```

**不用「本金回報率」**——同一筆本金可以並行跑多個策略，用峰值保證金做分母先可以比較「邊個策略資金效率最高」，呢個先係 Copy Trade 決策需要嘅數字。`margin_peak` 取期內逐日 `margin_cum` 峰值（含浮盈加倉唔另計，P0 不做動態保證金）。

分期匯總結果寫入 `perf_periods`（5.1 九張表之一，**SQLite 先行**，已批）；任何頁面只准讀表，唔准重算（見 6.7 鐵律三）。

### 6.7 實作守則（本節收口）

**三條鐵律**：

1. **L1（M1）係全系統唯一計錢嘅層**。任何下游模組重算 pip_value／margin 即視為缺陷——包括「順手」喺 SQL 入面乘個匯率。
2. **寧可空白，不可估算**。缺 `symbols` 列、缺當日 fx、缺價格——一律 raise／留空並標示原因，唔准用近似值、最近值、預設值頂上。錯嘅數字比冇數字危險。
3. **SQLite 先行**（已批）：本節所有產出落 5.1 九張表；L7 呈現只讀唔計；HTML/PDF 係 P1/P2。

**歷史教訓表（每條都係真實發生過嘅錯誤，實作前讀一次）**：

| # | 教訓 | 量級 | 守則 |
|---|---|---|---|
| 1 | XAU pip 0.10 vs 0.01 兩檔慣例並存 | 10 倍 | `pip_size` 讀表（6.1），程式內零常數表 |
| 2 | BTCUSD `endswith('USD')→$10`，真實 $0.01 | **1000 倍** | `pip_value` 讀 `tick_value`（6.2），禁用報價幣尾碼猜合約 |
| 3 | JPY／CHF 匯率漂移 10–38%/月；單一固定值全期誤差中位 2.2%、最差 7.5% | 2–8% | 非 USD 報價按日修正 fx（6.2），USD 報價恆定唔修正 |
| 4 | `quote_rate` 方向無定義（JPY 可反 150 倍） | 150 倍 | `fx ≡ 1 報價幣 = ? USD` 全系統唯一方向（6.2/6.4）＋ ±2× sanity band |

**一條收尾對帳（引用 CORE_WORKFLOW §13）**：M4 在 `wait_pips = 0` 時，模擬盈虧必須逐筆等於 `trades` 表真實盈虧。呢條過咗，本節全部定義（6.1–6.6）先算落地驗證。

---

## 交收與驗收自檢

- **併入**：以上 `## 六、` 至對應 `---`（不含本交收段）整段替換主檔 v1.1 第六節（行 224–312），節後直接接「## 七、介面設計」。OpenClaw 側併入＋交老闆。
- **驗收自檢（對照你 16:15 四條標準）**：

| 驗收標準 | 自檢結果 |
|---|---|
| 6.2 tick_value 權威、公式降級對照、兩者關係寫清楚 | ✅ 權威式／對照式分行＋「一句講死」關係段＋對照 2% 閘門 pseudo-code；並講明對照捉唔到慣例錯（由 6.3 捉） |
| 全節同九節已批 4 參數零矛盾 | ✅ 6.0 落鎖表逐項對應（商品域／tick_value／leverage 500 可配置／SQLite 先行／模擬器改造）；全節引用已批字眼而非另立說法 |
| 計算定義去到 pseudo-code 級精確 | ✅ 6.1–6.5 全部有 pseudo-code；順手修咗三處照抄即錯嘅 slip（式 B 量綱、浮虧符號、fx 方向）——見修正清單 #2/#3/#4 |
| 繁體中文、風格同主檔一致 | ✅ 表格＋公式塊＋教訓實例＋「寧可空白，不可估算」語彙全對齊主檔 |

- **一項請更正**：你 16:15 派工信引「19/30 商品 CV>20%」——主檔附錄 A 已標該數「作廢」（v1.1 小分母統計誤用）。本稿論證改用更正版證據（逐月漂移＋2.2%/7.5%），併入後全檔口徑一致。
- 本稿為**文件交付**，冇 code 變更；quota 時期分工下我側照出。

---
*ZCODE_w（機房lane）— 老闆 16:08 派工，16:40 交付*

