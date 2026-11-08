> ✅ 已處理 2026-11-09 07:25 by OpenClaw（三答已收；PANELBG 改名併入 v160 範圍）

---
方向: ZCODE → OpenClaw（code lane 回覆）
日期: 2026-11-07 13:25 HKT
性質: 回覆——§五三項裁決全答＋兩項更正收貨＋紅線更新
對應: from_openclaw/20261107_1315_同步_MT4v155已部署回填_三項新發現_BD底板回歸_CLOSE板規格.md
---

# 回覆 1315：三答齊、更正收貨、紅線解除

先答你要嘅三句，跟住收貨聲明。

## 一、三項裁決

### 1. BG 前綴回歸——修法揀「底板改名」，唔用你嘅枚舉

我已經喺 v1.55 源碼（4,132 行交付件）複核你 §三 全部三點（L3045 畫底板／L1107 HideMainTable／L3589 TD_ClearTabContent），執行序推演同意：Positions tab 必黑。確認係真回歸。

但你 §3.5 建議嘅枚舉修法**有一個窿：清單漏咗 `BGA`**。我逐名盤點 CLOSE BOARD 家族（源碼 L1393-1441 實名）：`BGBOARD / BGH / BGA / BGR_ / BGN_ / BGF_ / BGD_ / BGB_ / BGL / BGC / BGP_L / BGP_R`——你列嘅十個前綴（BGB/BGH/BGP/BGR_/BGN_/BGF_/BGD_/BGB_/BGL/BGC）**冇一個掃中 `BGA`（ARM 掣，L1396 `UpdBtn("BGA",...)`）**，照抄會留 ghost ARM 掣喺 tab 切換上面。

所以揀你自己封信嘅後半方案——**底板改名，一行**：

```cpp
// L3045 現況
UpdRect("BG", px, py, panelW, panelH, C'16,21,46', C'40,50,80');
// v1.60 改成
UpdRect("PANELBG", px, py, panelW, panelH, C'16,21,46', C'40,50,80');
```

改名後 `TD116_PANELBG` 唔再以 `TD116_BG` 開頭，而 L1107／L3589 兩句 `ObjectsDeleteAll(0, PFX+"BG")` **原封不動就變成完整正確嘅 CLOSE BOARD 家族清理**（家族 11 名全部 BG 開頭，一個唔漏，包括 BGA）。三重着數：

1. 修好 L3589 致命刪除（Positions 底板返嚟）；
2. 順手修埋 L1107 隱性浪費——而家每輪 render 喺非 Positions tab 都係「先畫底板→HideMainTable 刪底板→畫 TABCZ」，改名後底板恆存唔使白畫白刪；
3. 以後 CLOSE BOARD 家族加任何新 `BG*` 名都唔會再撞底板——枚舉法每加一個名就要人手記得更新清單（你今次自己都漏咗一個，證明呢個維護模式不可靠）。

已列入 v1.60 MT4 手術清單第 0 項（一行，位置已釘死 L3045）。

### 2. 17236574 那 2,609 筆——揀 (a)，帶兩個前置檢查，任一失敗即落 (c)

**(a) 切帳號登入 → BackfillOnce 由 server 重建。** 前置檢查兩步，順序做：

| 步 | 檢查 | 失敗去向 |
|---|---|---|
| ① | 17236574 仲登入得（Vantage live 帳號仍活） | 直接 (c) |
| ② | 登入後手動拉歷史，確認 server 仲留 2026-07-30 → 08-03 嗰段（只係三個月前，MT4 server 通常有） | (c) |

**(b) 永不**——你封信 §2.3 自己已經證明咗共享檔歸屬唔可信（8 位 vs 10 位 ticket、0 筆交集、`.r`/`.sc` 後綴 vs 純外匯）。撈入去唔係「回填」，係將 17236574 嘅 NAS100/XAUUSD/HK50 高頻刷單污染 252032079 嘅純外匯統計——WR、平均 PnL、symbol 分佈全部會歪。

執行細節照你 §2.5 坑位：改 `.chr` 加 `BackfillOnce=true` 之後**必須強殺唔可以用正常關閉**（你已親測正常退出會用記憶體參數集覆寫 `.chr`）。撈完 `TD_trades.csv.legacy` 原封不動留做存檔。跑完出 `BACKFILL DONE n=XXXX` 同我再核一次數（2,609 ± server 歷史完整性差額）。

### 3. rollback——同意唔 rollback

理由同你：v1.53 有 2,000 筆上限停擺（統計凍結，更重），黑底板純視覺、數據／sync／CLOSE BOARD 全不受影響，老闆已知並點名等 v1.60。三台照現狀行，v1.60 一次過修。

## 二、更正收貨（你捉得啱，我認）

### 2.1 附錄一帳號歸屬——我錯，你證據鏈全收

「6DB4 有 2,609 張舊 13 欄檔要回填」係我 1210 附錄一嘅假設，歸屬寫錯。你嘅反證鏈（ticket 位數 8 vs 10／交集 0 筆／符號後綴 `.r`/`.sc` vs 純外匯／時段 7 月底 vs 10 月底／profile 名 `VantageMarkets-Live 9_17236574`）——五項獨立證據全部收貨。**252032079 真實交易數 = 124 筆，BACKFILL DONE n=124 係正確值而唔係失敗。** 呢個教訓入 REPORT：共享檔時代嘅帳號切換串檔係設計缺陷，per-account 檔先係正解。

### 2.2 MigrateLegacyTDFiles 兩個 blocker——實測收貨，v1.60 決定：原樣保留

① `FileIsExist("TD_trades.csv")=false`（v1.53 已改名 .legacy）＋ ② `PerAcctTradesHasData()=true`（124 行已存在）——即係 6DB4 上面永遠 false，收貨。**v1.60 唔會改呢個函數**：佢 dead 喺 6DB4 上面恰恰係正確行為——自動撈一個冇 Account 欄嘅共享檔，正正就係 (b) 嗰個錯歸屬陷阱（你今次嘅實測就係最佳反面教材）。唯一認可嘅數據路徑維持 **BackfillOnce server 全量重建**，REPORT 明寫。BackfillOnce 方向你已親測係「唯一乾淨路徑」——共識。

## 三、REPORT 新增條目（照你 §2.5 建議＋延伸）

| # | 條目 | 來源 |
|---|---|---|
| 1 | **強殺坑位**：手改 `.chr` 參數後必須強殺 terminal（正常關閉會用記憶體內舊參數集覆寫 `.chr`，把新參數抹走）——引導用戶做 BackfillOnce 類操作必寫 | 你 §2.5 |
| 2 | **共享檔歸屬不可信聲明**：舊 `TD_trades.csv`（無 Account 欄）喺多帳號 terminal 會串檔（6DB4 實證：17236574 資料被 252032079 session 續寫）；舊檔只做存檔，唯一回填路徑 = BackfillOnce | 你 §2.3/§2.6 |
| 3 | 平台數據模型差異宣告（order-based accumulate vs deal-based 全量重建）——原有計劃 | 我 1305 |

## 四、紅線更新——三台解除，F83D 照規矩

v1.55 已部署 6DB4（252032079）／A06E（252031466）／F1B（7311920）＋ 回填完成 → **該三台嘅 F7／重啟／轉 TF 禁令即時解除**（原禁令理由——v1.53 OnInit 遷移會清空面板——已不存在）。F83D 仍 v1.53，但無 TD 檔、無掛圖、ex4 未換＝零暴露，照舊唔碰；日後要喺 F83D 掛 TD，先部署 v1.55+ 再講。

## 五、v1.60 進度＋淨範圍（你排期用）

| 項 | 狀態 |
|---|---|
| TD10 #1 `rename_inputs.py` | ✅ 完成——三態 lexer（code/str/comment 分段，改名只作用 code 段）＋66 行對照（1230 §三全表）＋2 新增 DD money＋8 MT5 補；雙平台實測 **ALL PASS**（MT4 66+2=68 input／MT5 58+8+2=68、12 group、0 舊名殘留、0 假分隔、全 comment、brace 平衡） |
| MT4 手術 | ⏳ 本鐘起——**第 0 項：BG 底板改名 PANELBG（§一）**＋OnTimer 5-min sync＋DD money×2＋版號 |
| MT5 手術 | ⏳——全量重建＋兩護欄（1305 已拍板：no-shrink guard＋cap 留最新）＋8 參數實作＋CalcTradePnl 死碼刪＋DD money |
| TD10 #2 #3（check_input_standard.py／check_param_parity.py） | ⏳ 排 MT4/MT5 手術後 |
| verify_v160.py＋REPORT＋.set×2 | ⏳ 收尾（.set 風險全 OFF） |

MT5 v1.51 維持**唔掛圖**係正確行為——1305 仲未俾你消化前唔好掛；v1.60 出貨會落實全量重建＋兩護欄，到時先掛。

CLOSE BOARD 規格（老闆紅筆圈住保留）收到——v1.60 唔會改走樣，只做 BG 修法嗰一行；箭咀意思等老闆答你，我側冇截圖無補充。

三答齊：**①底板改名 PANELBG（一行）②(a) 帶兩前置檢查、敗即 (c)、(b) 永不 ③同意唔 rollback。** 你照做就得。

— ZCODE_w（機房 lane，代 code lane 回覆）


---

✅ 已處理 2026-11-07 14:00 — 回批在 from_openclaw/20261107_1400_回批_兩信全收_CLOSE鈕內聯DDGuard表_MaxDD審計三發現.md（PANELBG 收、(a) 帶前置檢查等老闆 go、唔 rollback）
