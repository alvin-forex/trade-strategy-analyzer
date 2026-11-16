對象：ZCODE（code lane）
發出：OpenClaw（data lane，代 AC 落單）2026-11-16 15:00 HKT
性質：派工（規劃＝AutoClaw #1461 定稿；老闆 14:52 轉交）
quota：yuanyuai glm-5.3／Start Plan 免費額度先行（用盡先用收費）
基準變更（全項目生效）：老闆 11-16 確認冇修正版 Excel——對標基準改用 **Spec §5 公式手算值（provisional）**；現行 Excel §26 已知 bug 只作參考唔照抄

# 派工 — W3b Pip Value＋Margin＋XAU＋Policy（tsa-risk-analyzer）

依據：規格 §10–§12＋§17｜前置：W3a merge

## 任務
1. /src/engines/pip-value.ts：pipValueInQuote＝pipSize×contractSize；quote→account 方向規則照 §10（直接／反向兩條）
2. /src/engines/margin.ts：marginBase＝lot×contractSize÷leverage，base→account 轉換**只做一次**；不變式測試：Σ逐層 margin＝＝margin(總手數)；**Excel Deposit Load 重複乘 bug 唔准遷移**
3. XAU 三檔規格表（齊／半／缺）：缺 Contract Size → 全部金額欄停用
4. /src/engines/policy.ts：capitalLoad＝(DD＋margin)÷initialDeposit raw ratio；門檻未設定 → 只出數值無 pass/fail（BR-12）；**唔准聲稱 50% 係官方標準**
5. 測試：EURUSD／USDJPY／XAUUSD 三案例手算對照

## 驗收（OC 執行）
test 綠；不變式過；三案例手算全對

## 唔好做
28 表 UI（W4.2）

## 收尾
完成 → exchange/notify/from_zcode/ 三行通知 → OC 自動驗收回批。
