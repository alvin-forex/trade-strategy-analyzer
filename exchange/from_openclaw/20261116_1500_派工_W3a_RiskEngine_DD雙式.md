對象：ZCODE（code lane）
發出：OpenClaw（data lane，代 AC 落單）2026-11-16 15:00 HKT
性質：派工（規劃＝AutoClaw #1461 定稿；老闆 14:52 轉交）
quota：yuanyuai glm-5.3／Start Plan 免費額度先行（用盡先用收費）
基準變更（全項目生效）：老闆 11-16 確認冇修正版 Excel——對標基準改用 **Spec §5 公式手算值（provisional）**；現行 Excel §26 已知 bug 只作參考唔照抄

# 派工 — W3a Risk Engine 核心：DD 雙式＋回本（tsa-risk-analyzer）

依據：規格 §8–§9｜前置：W2b merge

## 任務
1. /src/engines/risk-dd.ts：
   - 直接式：每層浮虧＝累積距離(點)×lot×PV 逐層加總
   - 增量式：DD_k＝DD_(k-1)＋該層增量
   - **兩式結果完全相等——寫死斷言測試（§9）**
   - lossPerExtraPip＝PV×總手數
   - 回本距離＝Σ(lot×offset)÷Σlot（平均入市；入逐層明細，唔入 28 表）
2. 輸出雙軌：點數＋金額；金額軌規格唔齊即停用（BR-11）
3. 測試：0.05×1.2×16 層 fixture 手算對照＋XAU 缺 Contract Size 案例

## 驗收（OC 執行）
test 綠；兩式相等斷言過；手算表全對

## 唔好做
TF 覆蓋（W4）、任何 UI

## 收尾
完成 → exchange/notify/from_zcode/ 三行通知 → OC 自動驗收回批。

> ⏳ 進行中 2026-11-16 14:56 by ZCODE_w（W3a 屬 code lane 大交付——DD 雙式引擎＋相等斷言，轉介 i lane 認領；前置 W2b merge；基準變更 Spec §5 手算 provisional 隨轉介知悉。詳回執 1456）
