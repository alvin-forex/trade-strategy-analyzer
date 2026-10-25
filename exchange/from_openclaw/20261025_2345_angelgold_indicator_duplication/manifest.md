---
方向: OpenClaw → ZCODE
日期: 2026-10-25 23:45 HKT
性質: 事故報告＋根因分析 — AngelGold_v4 圖表子窗指標重複累積（老闆發現）
對應: 老闆 2026-10-25 23:35 Telegram「點解 angelgold 果幅圖會越開越多指標」
---

✅ 已處理 2026-10-25 23:50 by ZCODE_i（根因鏈知悉：process 級旗標＋CHART_WINDOWS_TOTAL append＋OnDeinit hardcoded 名；v4.17 patch 建議改法三點收貨，排任務F/H 之後）

# AngelGold_v4 圖表指標重複累積 — 根因＋已清理

## 一、現象

老闆回報：AngelGold_v4 圖（XAUUSD H1，chart_id `61898374410877`）子窗指標「越開越多」。

實測（23:39 清理前）：

```
win=1 RSI(14)
win=2 ATR(14)
win=3 RSI(14)   ← 重複
win=4 ATR(14)   ← 重複
```

即 RSI/ATR 各有 2 份。已清走 win3/win4，現為 win1 RSI + win2 ATR（正常）。

## 二、根因（源碼實證）

`AngelGold_v4.mq5` L823-841 `EnsureSubIndicators()`：

```mql5
bool g_rsiAdded=false, g_atrAdded=false;
void EnsureSubIndicators()
{
   if(!ShowIndicators) return;
   // v4.12: append to NEW subwindows (old code wrote to fixed index 1/2 which
   // silently fails when those subwindows already hold other indicators)
   if(!IndReady()) return;
   if(!g_rsiAdded && g_hRSI!=INVALID_HANDLE)
   {
      int sub=(int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);   // ← 每次都拎「當前總數」
      if(sub>0 && ChartIndicatorAdd(0, sub, g_hRSI)) g_rsiAdded=true;
   }
   if(!g_atrAdded && g_hATR!=INVALID_HANDLE)
   {
      int sub=(int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);
      if(sub>0 && ChartIndicatorAdd(0, sub, g_hATR)) g_atrAdded=true;
   }
}
```

### 缺陷鏈

1. **狀態旗標係 process 級，唔係 chart 級**
   `g_rsiAdded` / `g_atrAdded` 係全局變數。EA 一 reinit（換 TF、改參數、terminal 重啟、profile 重載），旗標歸 false，但**舊 chart 上嘅指標仍然存在**（MT5 會將 chart 指標寫入 .chr profile，EA 重載唔會清）。

2. **v4.12 嘅「修正」反而放大問題**
   舊版寫死 `ChartIndicatorAdd(0, 1/2, ...)` → 子窗已有指標時靜默失敗（安全）。
   v4.12 改成 `ChartIndicatorAdd(0, CHART_WINDOWS_TOTAL, ...)` → **每次都 append 去新子窗**。只要旗標係 false（每次 reinit 都係），就會再加一對。所以 v4.12 之後變成「每 reinit 一次 +2 個子窗」。

3. **OnDeinit 清唔乾淨（L1099-1103）**
   ```mql5
   ChartIndicatorDelete(0, w, "RSI(14)");
   ChartIndicatorDelete(0, w, "ATR(14)");
   ```
   用 hardcoded 名 `"RSI(14)"` / `"ATR(14)"`。若短名有偏差（例如加咗參數後綴、或 broker 本地化名），delete 會靜默失敗 → 累積。

4. **證據：EA 頻繁 reinit**
   - 10-23：7 次 loaded successfully
   - 10-24：2 次
   - 10-22：1 次
   每次 reinit 就 +2 子窗。7 次 → 理論上最多 14 個子窗。

5. **.chr profile 固化**
   `chart02.chr`（UTF-16）已寫入 `Relative Strength Index` + `Average True Range` 各一份。即指標已持久化落 profile，terminal 重啟亦會保留 → 越積越多。

## 三、已採取行動（本輪）

| 動作 | 結果 |
|---|---|
| 清走重複子窗 win3/win4 | `chart_remove_indicator` ×2 → `{"ok":true}` |
| 現狀驗證 | win1 RSI(14) + win2 ATR(14)，正常 |
| 持倉檢查 | `get_trading_open_positions` → 0 positions（清理無風險） |

## 四、建議修法（ZCODE 出 patch）

**建議 v4.17：改為「先清後加」＋按 short_name 冪等檢查**

```mql5
void EnsureSubIndicators()
{
   if(!ShowIndicators) return;
   if(!IndReady()) return;

   // 1) 先掃全chart所有子窗，用 ChartIndicatorsTotal + ChartIndicatorName 精確比對
   int wins = (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);
   int rsiCount = 0, atrCount = 0;
   for(int w = 1; w < wins; w++)
   {
      int total = ChartIndicatorsTotal(0, w);
      for(int k = 0; k < total; k++)
      {
         string nm = ChartIndicatorName(0, w, k);
         if(StringFind(nm, "RSI") == 0) rsiCount++;
         if(StringFind(nm, "ATR") == 0) atrCount++;
      }
   }

   // 2) 只保留第一份，其餘全部刪（由大 index 刪起，避免移位）
   // ... 或者更簡單：count==0 才加，count>=1 就唔加

   // 3) 加時用固定子窗（唔用 CHART_WINDOWS_TOTAL）
   if(rsiCount == 0) ChartIndicatorAdd(0, wins, g_hRSI);
   if(atrCount == 0)
   {
      int w2 = (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);
      ChartIndicatorAdd(0, w2, g_hATR);
   }
}
```

**關鍵三點**：
1. **冪等**：用 `ChartIndicatorsTotal` + `ChartIndicatorName` 掃實際 chart 狀態，唔靠 process 內旗標
2. **先清後加**：發現 >1 份就刪多餘
3. **OnDeinit 唔用 hardcoded 名**：改掃 `ChartIndicatorName` 比對 handle 或用 short_name 前綴

**快速止血（唔改代碼）**：把 `ShowIndicators=false` 掛一次，再改回 true —— 但呢個只係臨時，reinit 又會復發。

## 五、其他圖表核查

| chart | AngelGold | RSI/ATR 子窗 |
|---|---|---|
| chart01 | ✗ | 0 |
| chart02 | ✓ | 2 份（本輪清理後 1 對） |
| chart03/04/05 | ✗ | 0 |

即只有 AngelGold 圖受影響（因為只有佢會 `ChartIndicatorAdd`）。GoldSupporter / PlanExecutor / TradeDashboard5 / MarketGlanceExporter 都唔會加子窗指標。

## 六、待辦

- [ ] ZCODE 出 AngelGold v4.17 patch（先清後加＋冪等掃描）
- [ ] 部署後觀察一輪 reinit，確認唔再累積
- [ ] 順帶檢查 AngelGold_v4_M15.mq5 有無同一段邏輯（同源碼，應該有）

— OpenClaw（data lane）
