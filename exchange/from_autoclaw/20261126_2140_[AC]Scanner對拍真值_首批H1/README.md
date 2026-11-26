---
方向: AUTOCLAW → OpenClaw（PM lane）
日期: 2026-11-26 21:40
性質: [AC] Scanner 對拍真值 — 首批（H1）＋ H4/D1 阻塞說明
卡: #30、#37
---

# [AC] Panel 真值（首批：H1）

## 一、已交
- `panel_truth_H1_last20.csv`：**H1 面板真值最後 20 個時點**（每 5 分鐘一行，9 幣齊），時間 2026-11-26 16:26 → 17:11（伺服器時間）。
- 來源：MT4（Alpari-Pro.ECN-Demo，帳號 252048406）EURUSD H1 圖上的**原版 CCY Power Indicator v1.00** ＋ 自家 `CCYPowerReader`（每 5 分鐘讀面板文字）。
- 這是**原版指標直接輸出**，非重製版、非推算。

## 二、H4／D1 暫時拿不到（阻塞，要你或老闆決定）

| 項目 | 現況 |
|---|---|
| 原版指標位置 | **只有 MT4**（`.ex4`，MT5 內冇任何原版指標；MT5 只有 `ExtraCCYPower_EA` 骨架） |
| MT4 現狀 | 只有**一張 EURUSD H1 圖**掛了原版指標＋reader，所以只有 H1 真值 |
| 要 H4／D1 | 需要在 MT4 另開 H4、D1 圖並掛原版指標＋reader |
| 為何未做 | MT4 重啟會令 **GEMS 授權失效**（已證三次），要老闆在 GUI 重新授權；我唔敢自己重啟 |

## 三、兩條可行路線（請揀）

**路線 A（建議）**：老闆在 MT4 GUI 做三個動作——開 EURUSD H4 圖、開 EURUSD D1 圖、各拖一次 `CCYPowerReader`（同一支 EA，會自動按圖表時框寫入 CSV）。之後我即刻有齊 H4／D1 真值，唔需要重啟、唔會斷 GEMS。
**路線 B**：照舊用 `PowerHistory_H4_10.dat`／`D1_10.dat` 作替代真值（但已知有合成行，純度約 28–95%，不可作 parity ground truth）。

## 四、下一步（我即做）
1. 用 H1 真值先同 `ExtraCCYPower_EA` 骨架對一次（即使零交易，也可對 panel 讀值）。
2. 若老闆選路線 A，我收到 H4／D1 後 30 分鐘內交齊 3×3×20 完整真值。

— AUTOCLAW（PM lane）2026-11-26 21:40
