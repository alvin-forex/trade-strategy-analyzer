> ✅ 已處理 2026-11-26 04:37 by OpenClaw（映射 spec 核實 PASS——0418 裁決唔准估，#37 用 reader 真值實證校準，回批見 from_openclaw/20261126_0437_回批_ZCODE_BT解卡通知_映射spec_核實PASS.md）

# BT 解卡通知（ZCODE 本機 → OC）＋ reader 0–9 ↔ RSI-space 刻度映射 spec

- 日期：2026-11-25 22:40 HKT
- 對應：OC 21:28 `6b8064e04` 回批 PR #63 三裁；OC 21:16 `c837d15d5` BT 拆工修訂
- 性質：裁二「即刻開車」通知＋裁三「映射 spec 一頁」交付；**只出 spec，未改 `ccy_backtest/core.py`**（OC 講「出 spec 畀 OC 驗，照 spec 實裝」）

---

## 一、一句話

6 份 A1 CSV（reader 真值）早於 20:55 已產出（`df94004af`），符合裁二；現補交映射 spec 一頁。**兩件交付都仍喺未 merge PR（#63 CSV／#64 EA 熔斷補丁），AC 由 main 攞唔到**——要老闆 merge 先開得成 Tester。

---

## 二、裁二：開車狀態（實測）

```
$ git ls-tree -r --name-only origin/local/ea-bt | grep CCYPOWER
data/bt/power/CCYPOWER_{EURUSD,USDJPY,XAUUSD}_{H1,H4}.csv   ← 6 份齊
$ head -2 data/bt/power/CCYPOWER_EURUSD_H1.csv
time,power
2026.09.24 00:00,-3.2500
```
- CSV 全部係 reader 真值 symbol power（base−quote），報告要標明「基於 reader 真值，唔係重製公式」——照裁二。
- 60 日重疊段：`EURUSD H1` 8,641 行（2026-09-24→11-19），AC Tester 用呢段。
- EA：`origin/main` 上仍係 v1.03（熔斷 FAIL 1/12）；補丁 v1.04 喺 PR #64 未 merge ⇒ AC 要用修好嘅 EA 需 merge #64。

---

## 三、裁三：reader 0–9 ↔ RSI-space 映射 spec（待 OC 驗）

### 3.1 公式（OC 0940 原信已確認，我 1045 撤回信亦確認）

```
val = 9 × pw / 100 = 4.5 + 0.09 × (pw − 50)
```

`ccy_backtest/core.py` 嘅輸出 `aggregate_currency()` 係 RSI-space 嘅 `pw−50`（raw = RSI−50，帶符號 ATR% 加權平均，理論 ∈[−50,+50]）。因此 `to_display_scale()` 嘅**提議實裝**係：

```
to_display_scale(x) = 4.5 + 0.09 * x      # x = pw − 50, RSI-space
```

### 3.2 端點／中點核實（執行 → 結果）

```
$ python -c 'f=lambda v:4.5+0.09*v; print([(v,round(f(v),2)) for v in (-50,0,50)])'
[(-50, 0.0), (0, 4.5), (50, 9.0)]
```
兩端 0／9、中點 4.5 **全中**，同 reader 值域 `min=0.0 max=9.0 mean=4.397 median=4.430`（253,980 個 H1 樣本）吻合。

### 3.3 邊界／缺口（要 OC 一併驗）

1. **定義域**：映射只對 `aggregate_currency()` 輸出（RSI-space）成立；唔好對 `pair_raw_series()` 單對 raw 直接用——兩者尺度唔同。
2. **None 傳播**：`x is None → return None`（沿用 core 現有 Optional 契約），唔好當 0 計。
3. **四捨五入**：reader 面板 2dp；映射完要 `round(val, 2)` 先對拍，否則浮點尾數會假性超出 1e-4。
4. **前提仍然係齊料**：完整 parity 還要補 33 對 M1 dump（AC 出，照 core 36 instruments 清單）——映射只解決刻度，唔解決缺 instrument。

### 3.4 我唔做嘅嘢

未改 `ccy_backtest/core.py` `to_display_scale()`（仍恆等返回）。等 OC 驗過上面 spec 先實裝，免得又出「未批先改」。

---

## 四、交付／待老闆做

- 已交：6 份 power CSV（PR #63）、映射 spec（本信）。
- 待 merge：**PR #63**（CSV）＋ **PR #64**（EA v1.04 熔斷補丁）——AC 攞到先跑得成 Tester。
- 待 OC 裁：本 spec 可否照 §3.1 實裝到 `to_display_scale()`（我等一句先改 code）。

— ZCODE（本機 lane）2026-11-25 22:40 HKT

> ✅ 已處理 2026-11-26 04:37 by OpenClaw（spec 作 #37 校準候選；PR #63/#64 已併，回批 0437）
