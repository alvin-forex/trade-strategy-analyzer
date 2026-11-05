# FIX-TD patch：TradeDashboard v1.49 → v1.50（切 TAB 重影修復）

- 日期: 2026-11-05 19:50 HKT
- 對應: from_openclaw/20261105_1312（派工）＋ 20261105_1825 FIX-TD源碼入庫（base＝sha8 **5cbf792c**，3,515 行）＋ from_zcode/20261105_1342（源碼入庫請求）
- 出貨物: `TradeDashboard_v1.49_to_v1.50.diff`（55 行 diff，-p1）；`TradeDashboard_v1.50_full_preview.mq4`（補丁後全文預覽 3,529 行，編譯用呢個或 patch 後者等價）

## 一、根因（源碼實證）

DDG tab 建立嘅物件 family 有七個，**兩個清理清單都收漏**：

| family | 物件 | HideMainTable（:976 exact delete） | TD_ClearTabContent（:2999 prefix） |
|---|---|---|---|
| DD 行列 Float $ | `DDF0-11` | ✅（固定枚舉 0-13） | ❌ **漏** |
| DD 行列 DD now % | `DDP0-11` | ❌ **從未列出** | ❌ **漏** |
| DD 行列 MaxDD % | `DDM0-11` | ❌ **從未列出** | ❌ **漏** |
| DD 行列 MaxDD $ | `DDC$0-11` | ❌ exact `DDC0` 配唔中 `DDC$0` | ✅（prefix DDC 誤打誤撞中） |
| 欄頭 | `TPC2-5` | ❌（只刪 TPH） | ❌ **漏** |
| 按鈕 | `DDGT_ON/ACC/SYM` | ❌ | ❌ **漏** |
| 重置 | `DDRESET(+LBL)` | ❌ | ❌ **漏** |

老闆重現路徑 POS→DDG→POS：返回 Positions 走 `g_tab==0` 路徑（:2546）**只行 `TD_ClearTabContent()`**（HideMainTable 唔行）——上表 ❌ 全部殘留，疊喺 Position 表上＝截圖鬼影：DD 表頭（DD now／**Acc: ON**＝DDGT_ACC／MaxDD %／MaxDD $）＋DD 列值（DDF/DDP/DDM）。1312 診斷三點全中；另案修埋 `HISTW`（「HIST truncated!」提字喺 POS 以外 tab 殘留，同類漏網）。

## 二、修改函數名單（照 1312 單出）

1. **`HideMainTable()`**（v1.49 :976-995）
   - `ids[]` 加 `"HISTW"`；
   - DD 固定枚舉 loop（`g6` 0-13 exact delete）→ **10 條 prefix `ObjectsDeleteAll`**：`DDC／DDN／DDB／DDF／DDP／DDM／TPH／TPC／DDGT／DDRESET`（動態行數免疫，`DDC$` prefix 自然命中）。
2. **`TD_ClearTabContent()`**（v1.49 :2999-3009）
   - 加 6 條 prefix sweep：`DDF／DDP／DDM／TPC／DDGT／DDRESET`——切任何 TAB 前清晒 DDG 全族。
3. 版本行：`#property version`／`description` 1.49→**1.50**（2 行，方便部署後 log 對版）。

其餘 3,500+ 行零改動；TAB 按鈕（TAB0-3）／BG 底板／DDGT 按鈕 handler（:1367）等功能物件全部唔掂。

## 三、驗證（我側四態）

- 五錨點各恰 1（E1a/E1b/E2/E3/E4）＋十項 grep 斷言全 PASS（新版號 ×1、DDGT/DDRESET sweep 在位、舊固定枚舉 loop 歸零等）；
- **獨立重放**：pristine 5cbf792c 副本 `patch -p1 --dry-run` → **0 fuzz 0 reject**；實套後與出貨 preview **byte-identical**（cmp PASS）；反向 `-R` dry-run 乾淨；
- 3515→3529 行（+14）；兩版 brace balance delta=0；
- 你側照 #33 慣例獨立重放＋編譯即可。

## 四、驗收路徑（照 1312 原單）

- 四 TAB 兩兩互切循環（POS→DDG→POS→Alerts→POS→Set→POS 及全部反向組合）零重影；
- DDG 按鈕 ON/ALERT/BLOCK/CLOSE 功能不變；DDRESET 確認／重置照常；
- position 行數多寡切換唔残留（動態行數免疫＝prefix sweep 本意）；
- 編譯 0 err 後 .ex4 部署全部行緊 TD terminal（6DB4／A06E／F1BB），log 應見 **v1.50 STARTED**，老闆實測終審。
