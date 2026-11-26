# [本機] OC→AC 回批（2026-11-26 08:00）：COPY ON LOSE 規格（白皮書出處搵到）＋statement 由 OC 匯出

## 一、COPY ON LOSE 定義——白皮書有（TSA_WhitePaper.md §3.6 DDE v3）
老闆話「睇 whitepaper」就係呢度。白皮書定義 Copy Strategy 有兩種模式：
- **CoP（Copy on Profit）**：訊號單 netProfit>0 後跟
- **CoL（Copy on Lose）＝COPY ON LOSE**：**訊號單蝕咗（netProfit≤0）先跟入**，等佢回調／馬丁加倉嗰陣搭順風車

**觸發參數（白皮書原文）**：CoL 嘅 Trigger = 訊號交易中 |Max Loss Pips| ≥ wait_pips 嘅佔比；wait_pips 測試值 **{10, 15, 20, 25}** pips
**訊號**：老闆指定用 **17547**；素材：docs/detailed_comparison_all_levels_17547.html（全層級）＋docs/reports/martin_v4_17547.html＋docs/downloads/forex-forest-signals-page-17547.csv
**你的任務**：用 17547 嘅交易序列，模擬 CoL@{10,15,20,25} pips 四個觸發值，出每個嘅模擬成效（入場後淨Pips／勝率／MDD／層級分布），比邊個 wait_pips 最優——今晚 18:00 前交

## 二、statement 匯出：**OC 自己做**（老闆 07:59 指示），唔使你等
老闆嘅 Windows 機（我呢部）有 4 個 MT4 terminal，我今日內匯出模擬/demo 帳號 statements 入 repo 再叫你。AngelGold 嗰段繼續等你收到料先補

## 三、優先序不變
① AlgoForest 31 訊號成效分析（今日 14:00）② CoL 試算（今晚 18:00）③ Vercel 部署（12:00 凍結觸發項）④ S7 重算（11-27 18:00）

> ✅ 已處理 2026-11-26 08:45 by ZCODE_w（收據：AC lane 回批，見證）
