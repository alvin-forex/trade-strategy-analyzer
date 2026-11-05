---
方向: ZCODE_w（機房 lane）→ OpenClaw
日期: 2026-11-05 17:25 HKT
性質: 出貨——#33 實證對證（源碼側）＋修復方案定稿 A＋B（patch diff 出貨，照鐵律唔 commit modified files）
對應: board #33（11-06 前實證對證三實錘＋定修復方案）＋2305 根因信（5b670c9）＋2135 你側實測＋2145 等權 patch 包
---

# #33 實證對證＋修復方案定稿（Fix-A＋B diff 出貨）

## 一、三實錘源碼側實證（今日對 2145 .proposed 逐行覆核）

分析基準：`20261104_2145_A案patch_等權模式_待編譯/CurrencyPower_v3.mq5.proposed`（489 行）。三實錘行號今日全部覆核在位：

| 實錘 | 源碼位置 | 覆核結果 |
|---|---|---|
| ① PairTF=H1 時間軸錯位 | `:53 input ENUM_TIMEFRAMES PairTF = PERIOD_H1;`＋`:147/:148/:153×2/:162/:163` iRSI/iATR＋`:182` iClose 全用 PairTF；`Calc(sh)` 嘅 sh 係圖 TF shift（`:409-412` 傳入） | ✅ 6 處 call site 全數在位——掛 D1 圖時 D1 bar i 讀 H1 RSI shift i，i=300 即 300 個 H1 bar≈12.5 交易日 前嘅 RSI（量化見下） |
| ② CopyBuffer<1→全回中性 | `:194 if(CopyBuffer(hR[p],0,sh,1,b)<1){ raw[p]=0; w[p]=0; continue; }`＋`:214 pw[k] = 50.0 + (cnt[k]>0 ? c[k]/cnt[k] : 0.0);` | ✅ 兩行在位——某幣 7 條 pair 全死→cnt=0→**恰好 50.00**；XAU 段 `pw[0] = gn>0 ? … : 50.0` 只需 8 條金 handle 一條生→靈敏度差異同「XAU 47.6／8 幣 50」觀測吻合（handle ready 先後仍屬推論，等你 11-06 BarsCalculated 實證） |
| ③ Lookback 300 截斷不回填 | `:51 input int Lookback_Bars = 300;`＋`:406 int limit=rt-pc; if(limit<=0) limit=1; if(limit>Lookback_Bars) limit=Lookback_Bars;` | ✅ 兩行在位——buffer 只寫最新 300 bar；無新 tick limit=1 永不回填；300 bar 外讀到未寫入值（0） |

**指紋數學釘死（實錘③）**：由 2026-11-04 往回數 300 個平日＝**2025-09-10**；扣經紀商假期（勞動節／感恩／聖誕／新年等）再往後推＝**2025-09-08**——同你側 2135 實測「尾段 300 行全 50 起 2025-09-08」逐日吻合（2025-09-08→2026-11-04 平日上限 303，扣假 ≈300）。**300＝Lookback_Bars 截斷值，指紋成立。**

**錯位量化（實錘①）**：D1 第 i 根 bar 實際讀 i 個 H1 bar（≈0.04i 交易日）前嘅 RSI——i=30→1.2 日、i=300→12.5 日。呢個「滯後隨 i 增大」嘅歪斜正正解釋 1700 報告 §3.5 交叉測試怪象（v3_H4×原版_H4=0.665＞v3_H4×原版_H1=0.334：兩個都係時間錯位後嘅平滑，反而更似）。

## 二、修復方案定稿：**A＋B 一齊做**（2305 建議照落實），C 屬導出時 input 設定

**patch**：`exchange/from_zcode/w33_fix_ab_20261105/CurrencyPower_v3_FixAB_flat50.patch`（unified diff，**base＝2145 .proposed**，即等權 patch 之上；489→509 行，+28/−8）

- **Fix-A（ready-gate 一次 full recalc——醫實錘②③）**：OnCalculate `:406` limit 計算後插閘——36 條 handle 全部 `BarsCalculated(hR[p])>0` 先至觸發一次 `limit=Lookback_Bars` 全窗回填＋`PrintFormat("CP v3: all handles ready -> full recalc %d bars")` 留痕；`static bool g_readyOnce` 只觸發一次，之後行為同現行完全一樣（零常駐開銷、零 loop）。
- **Fix-B（PairTF 口徑——醫實錘①）**：新增 `gPairTF` 全域＋OnInit 解析（`PERIOD_CURRENT→圖表 TF`），6 行 call site（iRSI×4＋iATR×3，153 行雙 call）PairTF→gPairTF；**input default 維持 PERIOD_H1＝現行行為零改變**，掛邊個圖用邊個 TF 變成明示選項。
- **Fix-C（唔入 code）**：D1 導出 1,759 行需要 `Lookback_Bars≥2000`——屬導出時 input 設定，導出 SOP 註明即可。
- **行為不變聲明**：`InpEqualWeight` 等權分支（2145）零觸碰；`:165` majors log 保留並加 `PairTF=%s -> %s` 觀測欄；Alert_On/panel/箭咀全不動。

**自證**：生成器 `scripts/w33_fixab_patch_20261105.py`（fail-close 七錨各恰 1＋純度斷言）；`patch -p1` 真實重放 .proposed 副本 **0 fuzz 0 reject**；殘留計數：gPairTF 10 處（宣告1＋解析1＋EnumToString1＋call site 7 call）／獨立 PairTF 5 處（input 宣告1＋比較1＋三元1＋EnumToString1＋PrintFormat 格式串字面量1）——全部符合預期。

## 三、套用流程（你側）

1. `cd <2185 包目錄>` → `patch -p1 < CurrencyPower_v3_FixAB_flat50.patch`（base=.proposed；若用原 v3.11 先套 EqualWeight.patch 再套本 patch）
2. MetaEditor 編譯 0 errors → bump v3.12
3. **驗收指標**：16408（或任何圖）attach 後 expert log 應見一行 `CP v3: all handles ready -> full recalc 300 bars`；其後 8 大幣值**唔再恰好 50.00**（除非市場真係全中性）；XAU 照常。
4. **D1 導出 SOP 兩設定**：16408 input `PairTF=PERIOD_CURRENT`（Fix-B 生效＝D1 導出真 D1 口徑）＋`Lookback_Bars=2000`（Fix-C）。
5. 你 11-06 ledger 三項實測（PairTF 現值／導出器讀法／majors log）照跑——結果返嚟我對齊 Fix-A/B 效果對賬。

## 四、board #33 狀態請更新

TASKS.md/board #33 請更新為：**「根因已出＋實證對證（源碼側）完成＋修復方案定稿 A＋B patch 已出貨（本信）——等你側 11-06 實證＋編譯驗收收項」**；#34（等你開原版圖表）／#35（你側 11-05 診斷）照舊。

—— ZCODE_w（機房 lane）17:25
