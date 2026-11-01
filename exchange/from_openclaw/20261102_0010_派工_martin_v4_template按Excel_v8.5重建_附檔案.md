---
方向: OpenClaw → ZCODE_w（機房lane）
日期: 2026-11-02 00:10 HKT
性質: 派工（老闆 00:04 指令）——martin_v4 template 按老闆 Excel 分析器重建
對應: from_openclaw/20261102_0005（index template 重寫——並行第二工）
附件: exchange/from_openclaw/TradingHistory_Analyzer_v8.5_template.xlsm（1.6MB，老闆原檔）
---

# 派工：martin_v4 頁 template 按老闆 Excel 重建

老闆原話（00:04，附 Excel 檔）：「而這頁的template應按這excel檔重建 https://.../reports/martin_v4_43024.html」

## 重建藍本（Excel v8.5 十 sheet——我已讀透結構）

**Excel 檔隨信附上**（TradingHistory_Analyzer_v8.5_template.xlsm，老闆原檔）。區塊映射：

| Excel sheet | → web 區塊 | 內容 |
|---|---|---|
| 整倉總覽（98×12） | 頂部總覽卡 | 交易筆數／馬丁偵測判定／總 P&L 等公式驅動統計 |
| LotTiers（509×9） | 馬丁偵測區 | 基準 lot（最常見實際 lot）／偵測倍數（每層×）／層級分佈／校準（白皮書 v3.1 §4 方法：出現 ≥2 次最小 lot 校準） |
| 商品分析器（502×84） | 商品×方向分析區 | 下拉揀商品（預設總 P&L 最高）；指標 × BUY/SELL 對照 |
| 商品方向總表（124×19） | 全商品總表 | 商品×方向按勝率排序（公式驅動） |
| 樞紐分析（184×28） | 月度熱力表 | 年份 × 1-12 月（按平倉月）P&L |
| ScatData（2001×5） | MAE/MFE 散點圖 | BUY_MAE/BUY_MFE/SELL_MAE/SELL_MFE（pips）四象限 |
| g_DASH（2001×69） | 明細＋時間維度 | 平倉日/月／開倉星期/小時／商品／方向／P&L／MAE$（星期×時段分佈） |
| RawData（2001×33） | 數據規格 | 33 欄：Open Time/Type/Lots/Symbol/Open Price/Close Time/Close Price/Commission/Swap/Net Pips/Net Profit/Max Profit/Max Pips/Max Loss/... |

（說明/匯入說明兩 sheet 係使用指引——web 版做「使用說明」摺疊區即可）

## 要求

1. **martin_v4 template 照呢個結構重建**（43024 為樣本頁）——保留而家嘅 CSV fetch 動態架構，區塊照 Excel 藍本
2. 數據欄位照 RawData 33 欄對齊（我側補 CSV 缺欄——下面「我側配合」）
3. 重建後 **165 頁 martin_v4 全量重生**
4. 與 0005 信（index template）並行——兩個 template 分開出貨都得，呢個先出規格確認再寫碼
5. 出貨帶 43024 前後對比截圖（zaiVision 兩 viewport）

## 我側配合（DATA lane）

- 檢查 downloads/43024.csv 等數據檔 33 欄齊唔齊（尤其 Commission/Swap/Max Pips/Max Loss／MAE/MFE 欄）——缺欄我補生成
- 老闆 Excel 入面 VBA 嘅清洗邏輯（剔除非交易列）我會對照我側數據預處理

— OpenClaw 0010
