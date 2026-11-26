# [AC] 派工＋完整背景：Scanner 對拍真值（老闆 11-26 09:17 指示「畀齊料你先了解再開工」）

你而家得閒——呢單係你下一件主任務，材料全部列晒喺度，唔使再問「背景係乜」。

## 一、呢件事係乜（兩星期歷史一分鐘讀完）
- 11-18 老闆命名「Extra Martingale Scanner」（卡 #30），要求照原版指標重製＋加我哋要嘅功能
- 11-23 你核實咗原版 ExtraCCY05 參數解碼（TierB snapshot）
- 11-24 老闆催辦重啟（23:16）；ZCODE 出設計（PR #55）我批咗；編排層（PR #59）已入 main；今晨首跑出矩陣
- **老闆今朝裁決（順序寫死）**：①先照原版做到尾（含 parity 對拍）②然後網頁化 ③最後先加附加功能
- 你而家呢單＝①嘅第一塊：**做對拍基準（ground truth）**

## 二、你要做（今日 14:00 前，凍結觸發項）
1. 部機 MT5 掛**原版 ExtraCCY05 指標**（Martingale Scanner 那個）
2. 匯出 panel 真值：**至少 EURUSD／USDJPY／XAUUSD × H1/H4/D1 各最近 20 根**嘅指標輸出值（層級／區間／狀態，照指標 panel 顯示格式）
3. 入 `exchange/from_autoclaw/20261126_xxxx_[AC]Scanner對拍真值/`（CSV＋截圖）＋886 @OC

## 三、背景參考（全部喺 repo）
- 卡 #30（歷史＋裁決）／卡 #37（parity 規格）
- `docs/TSA_WhitePaper.md`（評分定義）
- ZCODE 首跑數據：`data/scanner/matrix.csv`（呢個係重製值，你匯嘅真值就係同佢對拍）
- 相關：你仲欠嘅 Vercel 部署（12:00）／AlgoForest 分析（14:00）——三單並行，助手分工

> ✅ 已處理 2026-11-26 09:45 by ZCODE_w（收據：AC對口派工，見證收悉）
