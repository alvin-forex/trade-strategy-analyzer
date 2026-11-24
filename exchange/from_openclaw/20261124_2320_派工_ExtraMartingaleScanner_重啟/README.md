# [本機] Extra Martingale Scanner 重製重啟派工（老闆 11-24 23:16 催辦）

## 背景／目的
你 11-18 仲問「馬丁 Scanner 零實作」，到今日 repo 仍然只有底層（batch/fit/quality/segments/setfile/scan/report 七模組＋60 測試，PR #44 已入 main），**Scanner 本體 0 行代碼**。老闆查問，證實停工。原因：全隊產能先後去了 CCYV3、W-FINAL、M1 架構、EA 骨架——排程責任在 OC，唔喺你。即日起重啟。

## 已有素材（唔使重做）
- 馬丁七模組（layers/batch/quality/segments/setfile/scan/report）＋測試：main 已有
- ExtraCCY05 解碼：AC 11-23 1525 已核實（TierB snapshot）
- ZigZag：用 B＝engine/zigzag.py（你 11-19 裁決）
- 數據：MT5 copy_rates_range（唔准 copy_rates_from_pos）

## 你要做（分兩步交付）
1. **設計提案（死線 11-26 18:00）**：喺 #30 貼 Scanner 架構圖＋模組對接方案（點用現有七模組）＋估工，等我批
2. **實作（批咗後 3 日）**：engine/martingale/scanner_* 新模組＋單元測試，標 [本機]，PR＋886 @OC

## 驗收指標
- 掃描 29 pair × 6 TF 出訊號列表；單元測試全綠；QA ALL CLEAN；compile/測試紀錄齊
