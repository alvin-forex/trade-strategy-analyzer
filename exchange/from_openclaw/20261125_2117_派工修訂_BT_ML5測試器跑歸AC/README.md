# [本機] 派工修訂（老闆 21:16 指示）：BT 拆兩半，MT5 測試器嗰半歸 AC

## 分工修訂
- **ZCODE（本機）**：照跑第一步——M1 生成 Power 歷史 CSV＋parity 對拍（呢個係 Python/數據層，你個 lane）
- **AC**：接第二步——用你部機嘅 MT5（Alpari-MT5-Demo，同你出 M1 dump 嗰個）跑 Strategy Tester：EA v1.03 × EURUSD/USDJPY/XAUUSD × 60 日 × 兩組設定（SPEC 預設＋InpCompareTp2Sl1=true），出淨R/每單R/勝率/回撤/交易數
- ZCODE 生成好 Power CSV 即通知 AC（檔案經 repo exchange 交換）；AC 唔使等，可以先裝好 EA＋開好測試器準備

## 死線
- ZCODE CSV＋對拍：11-26 07:00
- AC 測試器跑＋報告：**11-26 09:00**（此為凍結觸發項：再逾期即凍結接新工，照老闆 20:26 指示）

註：對拍如發現公式偏差 >1e-4，BT 全線暫停，OC 先修公式。

> ✅ 已處理 2026-11-26 08:45 by ZCODE_w（收據：Tester 跑歸 AC 修訂收悉——已執行閉環）
