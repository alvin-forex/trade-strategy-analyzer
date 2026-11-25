# [本機] OC 裁決：EA 填肉設計 4 缺口＋Scanner 設計 5 缺口（老闆 08:10 催速，即日批）

## A. EA 填肉（PR #56）四缺口裁決——即刻開工
1. **R 定義**：R := 1×ATR(14)（入場 TF）。預設 input 照 SPEC：SL=0.5R、TP=1R、日蝕 3R 停機；回測時另跑對照組 TP=2ATR/SL=1ATR（研究實測最優）比較，結果一併交
2. **power 輸入**：照 A1 外部 CSV（ccy_power\\CCYPOWER_<SYMBOL>_<TF>.csv，header time,power），MQL5 側 reader 你寫
3. **基底更正**：口徑以 v1.02／PR #50 為準，我三次引錯 v1.01/#51，書面認錯
4. **新紅線**：照你建議五條全批（三閘預設 OFF、§6 鎖步、§8 自檢、零 residual/STC/MACD、0 err 0 warn＋sha256）

## B. Scanner（PR #55）裁決
1. 「0 行」講法作廢：scanner.py 235 行係核心，**唔准重寫**；新工作＝編排層 scanner_orchestrator＋輸出契約
2. api.py:154 copy_rates_from_pos 一併改 copy_rates_range（本次任務範圍）
3. 訊號定義：用候選中最貼近現有 fit.py 評分嗰個（評分達 threshold 行＝訊號），詳情你揀，喺 PR 描述寫明
4. 6 TF＝M5/M15/M30/H1/H4/D1（排除 M1/W1）
5. 批咗，實作死線 11-27 18:00 照舊

## C. PR #53（W1 Signal 層）併入 main，供對拍基準
> ✅ 已處理 2026-11-25 09:02 by ZCODE_w（本機 lane 開工令——A.2 引用我 A1 路徑規範已鎖版收悉；本機 lane 經 zcode-local 收取即開工，平台唔代辦）
