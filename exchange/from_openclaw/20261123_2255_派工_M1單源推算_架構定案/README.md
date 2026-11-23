# 架構定案：M1 單源推算（老闆 2026-11-23 22:32 提出＋批准方向）

## 裁決內容
- **M1 係唯一數據源**：所有更大 TF（M5/M15/M30/H1/H4/D1）一律由 M1 聚合推算
- Power 公式亦以 M1 推算 TF 為輸入，唔再各自獨立計
- 實測基礎：OC 已驗證 M5→D1 聚合 834 交易日 100% 一致（僅 broker 第5位小數捨入差）
- 真相源＝OC 即時收集數據（老闆 22:46 前已拍板）；8 年 .dat 降級為參考

## 派工
- **AC**：喺 MT4-2 (A06E) 開 M1 dump——(1) 導出 EURUSD/USDJPY/XAUUSD 至少 30 日 M1 OHLC；(2) reader CSV 照跑（做面板真值）；(3) 兩樣放 exchange/from_autoclaw/ 推上 repo。目的：逐格對「M1 推算 Power」vs「原作面板值」，釘死原作有冇用 high/low
- **ZCODE(本機)**：CCYV3 數據層改為 M1 單源：hst_lib/power_engine 加 M1→TF 聚合層；唔好再開發針對多 TF 獨立數據嘅嘢。呢個改動會影響 #36 SQLite 數據層設計（M1 為主表）

## 驗收指標
- AC 交付：M1 CSV＋reader CSV，標 [AC]，886 @OC
- ZCODE 交付：聚合層代碼＋單元測試（用 docs/data M5/D1 對拍聚合正確性），標 [本機]
- 死線：2026-11-25 18:00（避開 14:00–18:00）
