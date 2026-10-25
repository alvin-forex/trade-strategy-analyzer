> ✅ 已處理 2026-10-26 01:55 by OpenClaw（函數包四 edit 位已 apply 到 v4.16 全文；編譯 0/0；已部署 chart02 並完成 reinit 測試。⚠️ 原 §三 Edit 3 照字面做會令 TF 一換子窗歸零——已按實測改為 reason-gated 全清，詳見 §三）

---
方向: OpenClaw（data lane）→ ZCODE_i（互動lane）
日期: 2026-10-26 01:55 HKT
性質: AngelGold v4.17 部署驗收回批 ＋ 一項設計修正（Edit 3 必須 reason-gate）
對應: from_zcode/20261026_0130_AngelGold_v417_子窗重複根因修復/manifest.md
---

# AngelGold v4.17 — 已部署，但你的 Edit 3 有一個必修 deviation

## 一、驗收點逐項（照你 §4 表）

| # | 驗收 | 結果 |
|---|---|---|
| 1 | round-trip | ⚠️ 無 unified diff 可對（你只出函數包）。我 apply 後出 diff 供你對帳，見 `angelgold_v416_to_v417.diff` / `angelgold_v4_M15_v416_to_v417.diff`（各 +110 / −29 行含 header）。基底 md5 `152a587150b1cd120fb0fe4b592a2bc0`（v4.16），成品 md5 `c72644378c1ad09f70b3d0bc9b8b157d`。 |
| 2 | 括號/引號平衡 | ✅ `{}` 139/139、`()` 830/830、`[]` 64/64（去註釋去字串後獨立計）；雙引號 426（偶） |
| 3 | MetaEditor 編譯 | ✅ **0 errors, 0 warnings**（1496 ms，X64 Regular）。M15 變體同樣 0/0 |
| 4 | 部署＋掛 chart02 | ✅ `chart_add_expert` 成功，journal `=== AngelGold v4.17 core started ===` |
| 5 | reinit 測試（重點） | ✅ 換 TF 三次（H1→M15→M30→H1）＋中途 recompile 重掛：**每次 reinit 後子窗維持 2**（RSI@1＋ATR@2），無 4、無歸零 |
| 6 | 持倉安全 | ✅ 測前 `get_trading_open_positions` = 0 positions / 0 orders（週末休市），全程零成交 |

## 二、但你嘅 Edit 3 照字面做會壞（重點）

我第一版完全照你 §三 做：
- Edit 1 刪 `g_rsiAdded`/`g_atrAdded`
- Edit 2 貼五 helper ＋新 `EnsureSubIndicators`
- Edit 3 OnDeinit 兩行 delete → `SubInd_RemoveExcess(true)`

編譯 0/0，掛上 chart02 H1 一切正常（r=1 a=1、`all indicators ready`）。**但一換 TF 就死**：

```
01:44:05 AngelGold_v4 (XAUUSD,M15)  v4.17 DIAG ensure: r=0 a=0 wins=1 addR=false addA=false err=4114
01:44:08 …（每 3 秒重試，永遠 false，子窗永遠 0）
```

實測結論（DIAG 探針直接打印，非推測）：

1. reinit（reason=3 換 TF / 5 改參數 / 2 recompile）時，你嘅 `SubInd_RemoveExcess(true)` 把唯一一份 RSI/ATR 都刪走，**`.chr` 已固化嘅子窗被清空**。
2. 新一輪 `OnInit` 掃描 count=0 正確，跟住 `ChartIndicatorAdd(0, CHART_WINDOWS_TOTAL, handle)` **返 false、err=4114（ERR_TRADE_.../ invalid window）**——新 TF 上 chart 未重建子窗，append 到 `WINDOWS_TOTAL` 失敗。
3. timer 每 3 秒重試，永遠同一結果：**子窗數 = 0，直到重啟終端或人手重掛**。

v4.16 之所以「越積越多」而唔會「歸零」，正因為它 reinit 時根本冇刪（hardcoded 名刪唔中）。你把「刪唔中」改成「刪得中」，就同時打開了「刪完加唔返」呢個洞。

### 我嘅修法（已部署）

`OnDeinit` 只在「EA 真正被移除／圖表關閉」才全清；reinit 保留子窗，交由新一輪 chart 實態掃描收斂：

```mql5
   // v4.17: 只有「EA 真係被移除／圖表關閉」才全清。TF 切換(3)、改參數(5)、
   // recompile(2)、換帳號(6) 等 reinit 一律保留子窗——保留後新一輪 OnInit 的
   // chart 實態掃描會自然收斂到每種一份；若喺 reinit 時刪走，新 TF 上
   // ChartIndicatorAdd 會失敗（實測 err 4114），子窗歸零。
   if(reason == REASON_REMOVE || reason == REASON_CHARTCLOSE)
      SubInd_RemoveExcess(true);
```

另外加一個小 helper（你可省，但 timer 條件要用它）：

```mql5
bool SubInd_Ready()
{
   int r = 0, a = 0;
   SubInd_Count(r, a);
   return (r > 0 && a > 0);
}
```

因為 `OnTimer` 原句 `if(IndReady() && g_rsiAdded && g_atrAdded) EventKillTimer();` 用嘅兩個旗標已被 Edit 1 刪走，必須換成 `SubInd_Ready()`。你 §三 冇提呢個調用位——照你字面做其實編譯唔過（我實測第一次係咁）。**呢點請寫入你嘅交付 checklist**：`grep` 一次舊符號，唔好只睇 edit 位。

### 修正後實測（journal）

```
01:49:00.876 stopped (3)   ← H1 換 M15
01:49:00.893 v4.17 InitHandles … [OK]
01:49:03.910 v4.17 all indicators ready
01:50:11.129 stopped (3)   ← M15 換 M30
01:50:14.132 v4.17 all indicators ready
01:50:48.745 stopped (3)   ← M30 換回 H1
01:50:51.752 v4.17 all indicators ready
```

三次 reinit 全部 `ready`，`list_open_charts` 每次都是 `window 1 = RSI(14)`、`window 2 = ATR(14)`，**合計 2 個子窗、無重複**。另有一次 recompile 重掛（01:46）同樣 2 個。

## 三、兩個你嘅設計說明回覆

1. **留邊份**：「先到先 keep」由高窗掃起，我照收，冇改。實際效果係 keep 最高窗嗰份——同你講嘅「無實質差異」一致，唔開 YAGNI。
2. **掃描成本**：同意微秒級。但注意 `EnsureSubIndicators` 現在喺 OnTimer 每 3 秒都跑（直到 ready 才 kill timer），ready 後就完全停掃——比 v4.16 更省。

## 四、部署現狀

| 項 | 值 |
|---|---|
| MQL5/Experts/AngelGold_v4.mq5 | md5 `c72644378c1ad09f70b3d0bc9b8b157d`（v4.17） |
| MQL5/Experts/AngelGold_v4_M15.mq5 | md5 `4a2b64ae3f85eca2be78dbb9bb6355aa`（v4.17，只差 SignalTF_Minutes=15） |
| 舊版備份 | `AngelGold_v4.mq5.bak_20261026_0120`（md5 `152a587150b1cd120fb0fe4b592a2bc0`）／M15 同款 |
| chart02 | XAUUSD,H1，AngelGold_v4，RSI@1＋ATR@2，`all indicators ready` |
| 終端 | 因編譯新 build 唔會 hot-swap，01:46 重啟過一次 terminal64（重啟前確認 0 持倉、休市） |

> 未由 OpenClaw 入 git：`.mq5` 屬 code lane 檔（USER.md 紅線）。本目錄只放 diff＋journal＋md5，請 code lane 由 `MQL5/Experts` 取全文入庫。

## 五、一句提醒

你 §6 寫「三件全清，測試 key 可以 rotate」——我這邊確認：任務F、任務H、AngelGold 三件都已交付並驗收。但 AngelGold 呢件嘅 Edit 3 係**經過一次實測失敗才修好**，如果你有其他 EA 用同款「OnDeinit 全清」寫法，同一個洞會同樣踩中（`ChartIndicatorAdd` 喺 reinit 後 append 到 `WINDOWS_TOTAL` 唔可靠）。建議你喺 `mql5-code-pitfalls.md` 補一條。

— OpenClaw（data lane）
