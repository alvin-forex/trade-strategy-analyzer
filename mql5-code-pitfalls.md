# MQL5 Code Pitfalls — ZCODE patch 出貨前必查清單

> 呢個檔記 MQL5/MT5 平台級陷阱，全部有實證（唔收推測）。ZCODE 每次出 EA patch 前掃一次；
> OpenClaw 部署遇到新坑請回批信提出，實證後由 ZCODE 編入。

---

## P1：reinit 語境下「OnDeinit 全清＋OnInit append 到 CHART_WINDOWS_TOTAL」係死亡組合

**實證**：AngelGold v4.17 首版（2026-10-26 01:44，chart02，journal DIAG 探針）
**症狀**：換 TF 後子窗歸零，`ChartIndicatorAdd` 永遠返 false，`err=4114`，timer 每 3 秒重試無效，直到人手重掛。

**根因鏈**：
1. reinit（reason 2/3/5/6）時 OnDeinit 清走唯一一份子窗指標；
2. 新 symbol/TF 嘅 chart 係**新建**——子窗結構未重建好；
3. `ChartIndicatorAdd(0, CHART_WINDOWS_TOTAL, handle)` append 到「當前總數」呢條路喺呢個時點**唔可靠**（MT5 內部子窗還原競態），返 false＋err 4114。

**正確模式（reason-gated 保留＋掃描收斂）**：
```mql5
// OnDeinit 只在「EA 真正被移除／圖表關閉」先全清；
// reinit 一律保留子窗，交由 OnInit 嘅 chart 實態掃描收斂（count==0 先加、>1 清多餘）。
if(reason == REASON_REMOVE || reason == REASON_CHARTCLOSE)
   SubInd_RemoveExcess(true);
```

**延伸**：`ChartIndicatorAdd(0, CHART_WINDOWS_TOTAL, ...)` 呢個 append 模式本身喺任何 chart 剛重建後都唔好信，加完要驗返
`ChartIndicatorsTotal(0, 該窗) == 1`，失敗就交俾 timer 下輪重試（唔好假設一次成功）。

**反模式**：v4.16「hardcoded 名刪唔中」冇爆呢個坑純屬運氣（刪唔中＝冇刪）——唔好學。

---

## 附：ZCODE 函數級交付 checklist（2026-10-26 Edit 3 事故後補強）

1. 出 patch 前對**舊符號做全套 grep**（唔只睇 edit 位）——任何被刪全局變數／函數嘅**全部調用位**都要交代；
   AngelGold 事故：Edit 1 刪 `g_rsiAdded`/`g_atrAdded`，但 OnTimer `EventKillTimer()` 條件仲用緊兩個旗標，
   照字面 apply 編譯都過唔到（OpenClaw 實測後加 `SubInd_Ready()` 補位）。
2. 「刪得中」同「加得返」要一齊驗證——把 delete 修好嘅同時，諗埋 delete 之後 init 路徑喺新 chart 實態上是否可靠（P1）。
3. 函數級交付（冇全文）＝ round-trip 責任轉移到部署方——交付信要明示，並要求 apply 後報 md5＋diff stat 對帳。
