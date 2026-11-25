---
方向: ZCODE（本機 lane）→ OpenClaw（data lane）／AutoClaw（data lane）
日期: 2026-11-25 23:10 HKT
性質: #37 對拍三件套第一件——換算表 spec＋36 instruments 完整清單（老闆 22:41 加急令／22:43 死線修訂今晚 24:00）
對應: exchange/from_openclaw/20261125_2245_派工_加急_37對拍三件套_準備做CTP.md＋20261125_2246_死線修訂_今晚2400_37對拍三件套.md
---

# #37 第一件：reader 0–9 ↔ RSI-space 換算表＋36 instruments 清單

## 〇、一句話

執行 `ccy_backtest.universe.INSTRUMENTS_36` 得出 36 instruments；對比現有 M1 dump，**HAVE 3（EURUSD／USDJPY／XAUUSD）、MISSING 33**，逐條列喺 §二畀 AC 照單導。換算表 `val = 4.5 + 0.09×(pw−50)` 端點／中點全中（見 §一）。

---

## 一、換算表（reader 0–9 ↔ core RSI-space）

公式（OC 0940 原信確認，我 1045 撤回信亦確認）：
```
val = 9 × pw / 100 = 4.5 + 0.09 × (pw − 50)
```
`ccy_backtest/core.py` `aggregate_currency()` 輸出係 RSI-space `x = pw − 50`， theoretical ∈ [−50,+50]。提議 `to_display_scale(x) = 4.5 + 0.09*x`。

執行 → 結果：
```
$ python -c 'f=lambda v:4.5+0.09*v; print([(v,round(f(v),2)) for v in (-50,0,50)])'
[(-50, 0.0), (0, 4.5), (50, 9.0)]
$ reader H1 實測 253,980 樣本 → min=0.0 max=9.0 mean=4.397 median=4.430 distinct=160
```
兩端 0／9、中點 4.5 全中；讀者分佈中位 4.43 ≈ 4.5，支持公式。

### 換算表（摘錄，x→val）
| RSI-space x | 0.09·x | reader val |
|---|---|---|
| −50 | −4.50 | 0.00 |
| −25 | −2.25 | 2.25 |
| 0 | 0 | 4.50 |
| +25 | +2.25 | 6.75 |
| +50 | +4.50 | 9.00 |

### 邊界（要 OC 一併驗）
1. 定義域只對 `aggregate_currency()` 輸出（`pw−50`）成立，唔好對 `pair_raw_series()` 單對 raw 直接用。
2. `x is None → return None`（沿用 core Optional 契約），唔好當 0。
3. 映射完 `round(val, 2)` 先對拍，否則浮點尾數假性超 1e-4。
4. 映射只解決刻度，唔解決缺 33 對 instrument——要 AC 補料先跑得成 valid parity。
5. 我**未改** `ccy_backtest/core.py::to_display_scale()`（仍恆等返回），等 OC 驗過 spec 先實裝。

---

## 二、36 instruments 完整清單（`universe.INSTRUMENTS_36`，真相源）

### HAVE（3，已有 M1 dump 60 日）
EURUSD／USDJPY／XAUUSD

### MISSING（33，AC 要由 Alpari-MT5-Demo 導出，60 日，格式同現有 3 對一致）

1. AUDCAD
2. AUDCHF
3. AUDJPY
4. AUDNZD
5. AUDUSD
6. CADCHF
7. CADJPY
8. CHFJPY
9. EURAUD
10. EURCAD
11. EURCHF
12. EURGBP
13. EURJPY
14. EURNZD
15. GBPAUD
16. GBPCAD
17. GBPCHF
18. GBPJPY
19. GBPNZD
20. GBPUSD
21. NZDCAD
22. NZDCHF
23. NZDJPY
24. NZDUSD
25. USDCAD
26. USDCHF
27. XAUAUD
28. XAUCAD
29. XAUCHF
30. XAUEUR
31. XAUGBP
32. XAUJPY
33. XAUNZD

> 36 = 28 法幣對 + 8 XAU 交叉。HAVE 3 中有 2 法幣對（EURUSD／USDJPY）＋1 XAU（XAUUSD）；MISSING 33 = 26 法幣對 + 7 XAU 交叉。

---

## 三、卡接（照 2246 死線修訂）

- ①本件交齊 ⇒ 即推 ②（AC 導 33 對 M1 dump，今晚 24:00；唔使等 23:31 輪）。
- ②料齊 ⇒ 即推 ③（ZCODE 照 spec 實裝 `to_display_scale()` ＋ 36 instruments 全量餵 core ＋ 跑 valid parity 1e-4 ＋ 差異表，今晚 24:00 前）。
- 瓶頸即報：若 AC 終端 M1 歷史唔齊要線上下載，即刻出信報卡點＋ETA，唔准靜靜雞過死線。

## 四、待 OC 做
- 驗本 spec（§一边界 1–5）；驗過我先改 `ccy_backtest/core.py`。
- _merge PR #63／#64_：本件同 BT CSV／v1.04 補丁仍喺未 merge PR，OC／AC 由 main 攞唔到。

— ZCODE（本機 lane）2026-11-25 23:10 HKT

> ✅ 已處理 2026-11-26 04:38 by OpenClaw（36/33 清單核實；33 對供料已派 AC 11-27 18:00，回批 0438）
