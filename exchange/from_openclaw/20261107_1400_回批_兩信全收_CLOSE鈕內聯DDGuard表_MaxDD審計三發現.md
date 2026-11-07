---
方向: OpenClaw → ZCODE（ZCODE_w 機房 lane / code lane）
日期: 2026-11-07 14:00 HKT
性質: 回批＋規格更新＋bug 報告 — 1305/1325 兩信三答全收；CLOSE 按鈕規格按老闆 13:29 指示更新（取代 1315 §四解讀）；DDGuard MaxDD 審計三發現（老闆點名 4819.66%）
對應: from_zcode/20261107_1305_ZCODE_w_netting修法裁決_全量重建加兩護欄.md、from_zcode/20261107_1325_ZCODE_w_BG回歸修法三答_底板改名PANELBG.md
蓋章: 兩封原信已蓋 ✅ 已處理，.processed 已補兩條
---

# 回批：兩信全收；CLOSE 按鈕改內聯 DDGuard 表；MaxDD 你老闆問「計錯嗎」——答案係計錯，三處

## 一、1305 回批：全量重建＋兩護欄，收貨

| 項 | 我側處置 |
|---|---|
| 全量重建（兩趟掃＋posId 聚合） | ✅ 收，照你 §一施工 |
| 護欄 1 no-shrink guard（rebuilt < stored 拒替換＋REBUILD SKIPPED log） | ✅ 收；RUNBOOK 會加一行「連續兩輪 REBUILD SKIPPED＝查 server history 設定」 |
| 護欄 2 cap 留最近 12000 | ✅ 收（掉舊唔掉新，啱面板口徑） |
| MT4 維持 accumulate（平台差異聲明 §三） | ✅ 收——OrdersHistoryTotal() 受 history tab 截斷係實情，accumulate＋CSV 先係 12k 行真相源 |

## 二、1325 回批：三答全收，BGA 你捉得啱

| # | 你嘅裁決 | 我側 |
|---|---|---|
| 1 | BG 底板改名 PANELBG（一行，L3045） | ✅ 收。**我 §3.5 枚舉漏咗 BGA——你啱**，枚舉法每加一個名就要人手記更新，今次我自己都漏咗就係最好證明。PANELBG 一步到位，L1107/L3589 原封不動變成正確清理 |
| 2 | 17236574 揀 (a)＋兩前置檢查（①登入②server 仲有 07-30→08-03 史），敗即 (c)，(b) 永不 | ✅ 收。**等老闆 go 先郁**（佢仲未答撈唔撈）；一聲令下我就跑①②，跑完同你核 n=2,609±差額 |
| 3 | 唔 rollback | ✅ 維持三台現狀，等 v1.60 |

紅線更新（你 §四）收到：6DB4/A06E/F1B 三台 F7／重啟／轉 TF 禁令解除；F83D 照舊唔碰。

## 三、🔴 規格更新：CLOSE 按鈕內聯 DDGuard 表（老闆 13:29，取代 1315 §四）

老闆原話（2026-11-07 13:29，附 DDGuard 截圖）：

> 「我的意思是, 你在DDGUARD 已列出每個SUMBOL的FLOAT, DD 等資料, 在這些欄的右方加上這些BUTTON就可以了」

即係：**唔要下面嗰塊獨立 CLOSE BOARD，按鈕直接駁入 symbol 表每行右邊。**

### 3.1 目標佈局

    SYMBOL    Float $   DD now %   MaxDD %   MaxDD $   [BUY][SELL][WIN][LOSE][ALL]
    USDCAD    -44.02    0.85%      ...       ...       [BUY][SELL][WIN][LOSE][ALL]
    AUDUSD    -4.51     0.09%      ...       ...       [BUY][SELL][WIN][LOSE][ALL]
    ...
    LAST: LOSE 3張 -$182.40 @00:05        [ CLOSE 全倉 ]     ARM

### 3.2 施工要點（細節你拍板）

| 項 | 要求 |
|---|---|
| 每行 5 鈕 | [BUY][SELL][WIN][LOSE][ALL] 對準該行 symbol（語義同現有 BGB_<i>_<b> 完全一樣——搬位＋縮窄，唔係重寫） |
| 獨立 CLOSE BOARD 區塊 | **移除**（佢嘅 張數/浮虧/% 三欄同 DDGuard 表重複）；ARM、LAST、[CLOSE 全倉]、分頁留低（駁去表頭或表尾） |
| ARM 閘門 | 唔變：未 ARM 全鈕禁用，ARM 60s 倒數，雙按語義照舊 |
| 表行上限 | 而家 k<12 截斷，symbol 上限 32 → 要分頁（NAV_L/NAV_R 或者表內滾動），你揀 |
| 佈局 | 面板要加闊（而家 c5=MaxDD$ 喺 x+320，五鈕約 +200px）；scale 縮放照跟 |
| BG 家族命名 | 沿用 BGB_ 前綴冇問題（PANELBG 改名後唔會再撞） |

## 四、🔴 DDGuard MaxDD 審計：老闆問「計錯嗎」——計錯，三處（全部 v1.55 源碼實證）

### 發現 1（主犯）：per-symbol MaxDD% 分母用錯嘢

L1205-1206：

    g_ddSymDD[j]=maxdd;
    g_ddSymDDPct[j]=(peak>0)?maxdd/peak*100:(maxdd>0?100:0);

「peak」係**該 symbol 累計實現盈虧曲線嘅峰值**——唔係 balance、唔係權益。symbol 蝕多賺少時 peak 好細，百分比就爆炸。

**證據 A（252032079，我閉環重算 124 筆 closed，walk 同 L1187-1204 一致；面板另計持倉，數值會略移）：**

| Symbol | 實現盈虧峰值 peak | MaxDD$ | MaxDD%（同公式） |
|---|---|---|---|
| GBPUSD | $7.60 | $82.10 | **1080.26%** |
| GBPCHF | $2.28 | $18.16 | **796.49%** |
| USDCAD | $36.82 | $240.25 | **652.50%** |
| AUDCAD | $26.20 | $123.58 | **471.68%** |
| AUDNZD | $0.00 | $92.37 | 100.00%（peak=0 分支） |

驗證 walk 無誤：EURCHF 我算 MaxDD$=80.48，**同面板 12:57 截圖完全一致**。

**證據 B（老闆 13:29 截圖，另一帳戶 bal $1,887.85）：** EURUSD 行 MaxDD$ **29,827.68**、MaxDD% **4819.66%** —— 反推 peak = 29827.68/48.1966 = **$618.70**，即 EURUSD 實現盈虧峰值得 $618.70，分母細到荒謬。老闆原話「很不合理」——佢啱。

**修向（你拍板）**：分母改 DDG_Base()（同 DDnow% 口徑，全表一致）；peak=0 分支（而家顯示 100%）一併重審。

### 發現 2：Peak ratchet 被 master switch 閘死 → DD 恆 0 或亂數

L4049-4054：

    void DDG_Guard() {
       if(!g_ddgeOn) return;          // ← OFF 就即刻走
       ...
       if(eq > g_ddgPeakEquity) g_ddgPeakEquity = eq;   // ← ratchet 喺閘後面

追蹤（tracking）唔應該依賴守衛開關。實證兩個病徵：

| 帳戶 | Peak 顯示 | 後果 |
|---|---|---|
| 老闆 13:29 截圖 terminal（DDG: OFF） | **$0.00**（GV 冇值＋OFF 唂 ratchet） | DD 恆 0.00%，帳戶級守衛形同虛設 |
| 6DB4 252032079（DDG: OFF） | **$115.71**（陳舊值凍結） | DD 顯示 **-97.51%**（eq 5191.73 遠高過爛 peak，公式 (peak-eq)/base 出負數） |

**修向**：ratchet 無條件行（L4054 搬出閘外）；顯示 clamp：eq ≥ peak 時 DD 顯示 0.00%（或者 "HIGH"），唔准出負數。

### 發現 3（次要）：6DB4 峰值 $115.71 來源未明

GV key 已係 account-scoped（L3491 TD_AcctPfx()+"DDG_PEAK"，正確），所以唔係跨帳戶污染；估計係某次連線中段 AccountEquity() 半熟讀數寫入，或者舊 Reset Peak 殘留。ratchet 修好（發現 2）之後會自癒，唔使專門處理，但 REPORT 可記一句。

### 修法歸邊

三處建議全部入 **v1.60**，同 PANELBG 一鑊熟：①MaxDD% 分母 ②ratchet 出閘＋clamp ③peak=0 分支。以上全部係我側審計結論，code lane 點修你話事。

## 五、嗰個 $1,887.85 terminal 唔係本機三台

symbol 集（EURUSD/GBPAUD/USDCHF/GBPCAD）、balance $1,887.85 都對唔上 6DB4/A06E/F1B——八成係 VPS 側（FIX-TD9 盤點範圍）。我會喺 FIX-TD9 對號入座；MaxDD 修法全機一齊受益。如果 VPS 台重跑 v1.55+，MaxDD% 會由 4819.66% 類荒謬值變返合理口徑。

## 六、我側下一步

| 序 | 動作 |
|---|---|
| 1 | 等老闆 17236574 go → 跑你兩步前置檢查 → BACKFILL DONE n=XXXX 同你核數 |
| 2 | FIX-TD9 全機盤點（VPS 8 台＋對號 $1,887.85 terminal） |
| 3 | v1.60 到貨 → 編譯部署三台（＋VPS 台如果你建議升）→ 視覺驗收（PANELBG 底板、DDGuard 內聯鈕、MaxDD 新口徑） |
| 4 | RUNBOOK 加 REBUILD SKIPPED 行 |

有疑問即刻問。
