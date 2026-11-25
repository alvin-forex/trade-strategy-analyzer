# [本機] 派工：EA v1.03 回測（BT）即刻開工

老闆 20:30 問幾時做完 BT。目標：**今晚開跑，聽朝 09:00 前交初版結果**（避 14-18）。

## 步驟
1. **Power CSV 生成**：用 M1 單源（AC M1 dump 60 日）＋重製公式生成 CCYPOWER_EURUSD_H1/H4.csv、CCYPOWER_USDJPY_*.csv、CCYPOWER_XAUUSD_*.csv（A1 已鎖格式 time,power）。呢步同時係 #37 parity 嘅前身，跑出嚟嘅值先同 reader 真值對拍（順手釘死有冇用 high/low）
2. **MT5 Strategy Tester 跑 v1.03**（你本機 MT5）：EURUSD／USDJPY／XAUUSD 三條線，60 日 M1 窗，兩組設定：①SPEC 預設 SL0.5R/TP1R ②對照組 InpCompareTp2Sl1=true
3. **指標**：每組淨R總和／R per trade／勝率／max drawdown／交易數；達標線 >=0.15R/單

## 交付
- BT 報告入 exchange/from_zcode/＋PR（如涉及腳本）＋886 @OC
- 如 M1 power 對拍發現偏差 >1e-4，即刻停 BT 報我（公式問題優先）

死線：**11-26 09:00 初版報告**。
