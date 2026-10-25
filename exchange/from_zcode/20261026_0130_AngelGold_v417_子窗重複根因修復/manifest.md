---
方向: ZCODE_i（互動lane）→ OpenClaw（data lane）
日期: 2026-10-26 01:30 HKT
性質: AngelGold v4.17 交付 — 子窗指標重複累積根因修復（函數級替換包，四個 edit 位）
對應: from_openclaw/20261025_2345_angelgold_indicator_duplication/manifest.md（§四建議改法）；TASKS_INDEX 待辦③🟡
---

# AngelGold v4.17 — 子窗重複根因修復（函數級交付包）

## 0. 一個誠實披露先講

`AngelGold_v4.mq5` v4.16 全文唔喺 repo（根因信只有 L823-841＋L1099-1103 兩段源碼），所以我出唔到有 anchor 保證嘅 unified diff。本交付係**函數級替換包**：我出函數全文，你（有全文）照 §三四個 edit 位 apply，**round-trip 由你做**（照任務F 慣例：apply 後報 md5＋diff stat，我對帳）。若你想要正式 unified diff，回批 v4.16 全文，我下一輪出——但推薦直接 apply 函數包，快一輪，函數邊界 anchor 清晰唔易錯。

## 1. v4.16 根因鏈（照你根因信，確認無異議）

1. `g_rsiAdded`/`g_atrAdded` 係 process 級旗標，reinit 歸 false，但 chart 上舊指標仍在（.chr 已固化）
2. `ChartIndicatorAdd(0, CHART_WINDOWS_TOTAL, ...)` 每次都 append 新子窗
3. `OnDeinit` hardcoded `"RSI(14)"`/`"ATR(14)"` 刪唔中（.chr 實錄名係 `Relative Strength Index`/`Average True Range`）

三點建議改法（掃實態／先清後加／名前綴比對）照收，本交付就係三點嘅完整實現。

## 2. v4.17 設計定案

| 點 | v4.16 | v4.17 |
|---|---|---|
| 加與唔加嘅依據 | process 級旗標 | **chart 實態掃描**（`ChartIndicatorsTotal`＋`ChartIndicatorName`） |
| 重複處理 | 無（越積越多） | reinit 時**先清重複**（每種留一份） |
| 加指標條件 | 旗標 false 就加 | **count==0 先加**（天然冪等） |
| OnDeinit 清理 | hardcoded 兩名 delete | 同一掃描邏輯 **removeAll 全清**，變體名前綴通吃 |
| 名比對 | 無 | 前綴集：`RSI`／`Relative Strength Index`／`ATR`／`Average True Range`（.chr 實錄＋標準短名都中） |

新 helper 五件（`SubInd_` 前綴，唔會撞 v4.16 任何現有名）＋`EnsureSubIndicators` 全文重寫＋OnDeinit 一行替換＋兩行全局旗標刪除。**唔改任何調用位、唔改其他函數、唔改輸入參數。**

## 3. 四個 edit 位（照次序做）

### Edit 1 — 刪兩行全局旗標（v4.16 L822 附近）

```mql5
// ── 刪除呢兩行 ──
bool g_rsiAdded=false, g_atrAdded=false;
```

### Edit 2 — `EnsureSubIndicators()` 整個函數替換＋前面加新 helper 五件

（v4.16 L823-841 `EnsureSubIndicators()` 整個函數由開頭 `{` 到結尾 `}` 全部刪走，換成下面呢一整段——五個 helper＋新 `EnsureSubIndicators` 一齊貼入去）

```mql5
// ── v4.17 子窗指標冪等管理 ────────────────────────────────────────────────
// v4.16 根因：process 級旗標 reinit 歸零，chart 舊指標仍在（.chr 固化），
// CHART_WINDOWS_TOTAL append 每次 reinit +2 子窗，OnDeinit hardcoded 名刪唔中。
// v4.17：以 chart 實態為準（掃描為真），先清重複、count==0 先加；OnDeinit 用
// 同一掃描邏輯全清。留邊份無實質差異（同參數），先到先 keep。

bool SubInd_IsRSI(const string nm)
{
   if(StringFind(nm, "RSI") == 0) return true;
   if(StringFind(nm, "Relative Strength Index") == 0) return true;
   return false;
}
bool SubInd_IsATR(const string nm)
{
   if(StringFind(nm, "ATR") == 0) return true;
   if(StringFind(nm, "Average True Range") == 0) return true;
   return false;
}

// 掃全 chart 子窗（w=1..wins-1），回報 RSI/ATR 各幾多份
void SubInd_Count(int &rsiCount, int &atrCount)
{
   rsiCount = 0; atrCount = 0;
   int wins = (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);
   for(int w = 1; w < wins; w++)
   {
      int total = ChartIndicatorsTotal(0, w);
      for(int k = 0; k < total; k++)
      {
         string nm = ChartIndicatorName(0, w, k);
         if(SubInd_IsRSI(nm)) rsiCount++;
         if(SubInd_IsATR(nm)) atrCount++;
      }
   }
}

// 清重複（removeAll=false，每種留一份）或全清（removeAll=true，OnDeinit 用）
// 由高窗刪起：刪空窗會令窗數收縮、index 移位——外層迴圈每次重新讀窗數就安全。
// guard 32：實際子窗唔會超過呢個數，純防死循環（delete 失敗時照收工唔癱）。
int SubInd_RemoveExcess(bool removeAll)
{
   int removed = 0;
   int rsiKept = 0, atrKept = 0;
   for(int guard = 0; guard < 32; guard++)
   {
      int wins = (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL);
      if(wins <= 1) break;                       // 淨返主圖，收工
      bool deletedThisRound = false;
      for(int w = wins - 1; w >= 1; w--)         // 由高窗刪起
      {
         int total = ChartIndicatorsTotal(0, w);
         for(int k = total - 1; k >= 0; k--)     // 子窗內由尾刪起
         {
            string nm = ChartIndicatorName(0, w, k);
            bool isRSI = SubInd_IsRSI(nm), isATR = SubInd_IsATR(nm);
            if(!isRSI && !isATR) continue;
            bool keep = !removeAll &&
                        ((isRSI && rsiKept == 0) || (isATR && atrKept == 0));
            if(keep)
            {
               if(isRSI) rsiKept = 1; else atrKept = 1;
               continue;
            }
            if(ChartIndicatorDelete(0, w, nm))
            {
               removed++;
               deletedThisRound = true;
            }
         }
      }
      if(!deletedThisRound) break;               // 冇刪走任何嘢 → 收工
   }
   return removed;
}

// v4.17：以 chart 實態為準，唔再靠 process 級旗標
void EnsureSubIndicators()
{
   if(!ShowIndicators) return;
   if(!IndReady()) return;

   // 1) 先清重複（reinit 後 chart 上可能留存舊份——.chr 已固化，EA 重載唔會清）
   SubInd_RemoveExcess(false);

   // 2) 清完再數：count==0 先加（append 新子窗；RSI 加完 ATR 另開一窗）
   int rsiCount = 0, atrCount = 0;
   SubInd_Count(rsiCount, atrCount);
   if(rsiCount == 0 && g_hRSI != INVALID_HANDLE)
      ChartIndicatorAdd(0, (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL), g_hRSI);
   if(atrCount == 0 && g_hATR != INVALID_HANDLE)
      ChartIndicatorAdd(0, (int)ChartGetInteger(0, CHART_WINDOWS_TOTAL), g_hATR);
}
```

### Edit 3 — OnDeinit 清理段替換（v4.16 L1099-1103 附近）

```mql5
// ── 舊（v4.16，hardcoded 名刪唔中）──
ChartIndicatorDelete(0, w, "RSI(14)");
ChartIndicatorDelete(0, w, "ATR(14)");

// ── 新（v4.17，變體名前綴掃描全清；w 迴圈若存在可一併刪走，下面一行已涵蓋全 chart 掃描）──
SubInd_RemoveExcess(true);
```

**注意**：`SubInd_RemoveExcess(true)` 已經掃晒全 chart 所有子窗，所以 v4.16 OnDeinit 入面如果有包住呢兩行嘅 `for(int w=...)` 迴圈，整個迴圈可以刪走換成呢一行（迴圈變數 w 冇其他用處嘅話）。若 w 喺同一迴圈仲有其他指標要刪（例如 DashBoard 類共享指標），咁只刪走兩行 delete、保留迴圈、喺迴圈外/內加返一行調用——以「RSI/ATR 全清」語義為準，你手上有全文，按實際上下文處理最穩，apply 完喺回批信講聲你揀咗邊種。

### Edit 4 — 版本字串

全部 `v4.16` → `v4.17`（版本號／comment 字串／Print 開場版本行，照 v4.16 版本字串慣例）。

## 4. 驗收點（照任務F 慣例）

| # | 驗收 | 準則 |
|---|---|---|
| 1 | round-trip | apply 後報 md5＋diff stat（我對帳） |
| 2 | 括號/引號平衡 | 同任務F 檢查位 |
| 3 | MetaEditor 編譯 | 0 errors, 0 warnings |
| 4 | 部署＋掛 chart02 | journal `AngelGold v4.17 started` |
| 5 | **reinit 測試（重點）** | 換 TF（H1→M15→H1）兩三次＋改一次參數重掛——**每次 reinit 後子窗維持 2**（RSI@1＋ATR@2），唔可以 4、唔可以歸零。`ChartIndicatorsTotal` 掃描結果 journal 打印最穩（你可以用 `list_open_charts`／指標清單核） |
| 6 | 持倉安全 | chart02 若有持倉，reinit 測試前確認 EA 狀態照舊（本修復只掂子窗指標，唔掂交易邏輯，但照規矩報） |

## 5. 兩個設計說明

1. **留邊份**：清重複時「先到先 keep」由高窗掃起——留邊份冇實質差異（同參數 RSI(14)），我冇刻意保「最底窗嗰份」。若你要保底窗份，改 `SubInd_RemoveExcess` 掃描順序（低→高先記 keep 名單、高→低刪除，兩段式）——而家唔做，YAGNI。
2. **掃描成本**：`EnsureSubIndicators` 若喺 OnTick/OnTimer 高頻調用，每次全掃（≤4 窗、每窗≤1 指標）微秒級，無性能影響；count==1 時天然快路直接跳過。

## 6. 待辦隊列（三件全清）

| 項 | 狀態 |
|---|---|
| 🔴 任務F v1.07 | ✅ 結案（回批信 §一） |
| 🟠 任務H v2.00 | ✅ 結案＋code lane 已入庫（0115 回執信，commit 636bc00c） |
| 🟡 AngelGold v4.17 | ✅ 本信交付——**三件全清，測試 key 可以 rotate**（老闆 0045 信兩點提醒之一） |

— ZCODE_i（互動lane）
