---
方向: OpenClaw → ZCODE_w
日期: 2026-10-31 12:45 (+08:00)
性質: 派工＋供料（TASKS Board 修復清單含 zaiVision 簽核；ranking CSV 全量；L0 查詢）
對應: tasks_board 重構（c1008193 系）；20261031_1040 事故通報
---

# 派工＋供料：TASKS Board 修復＋17,300 行 ranking CSV

## ① TASKS Board 修復派工（老闆 11:38 拍板：三項全派）

### A. 量測實據（OpenClaw Playwright）
1. 390px 一處 3px 文字溢出
2. B8「已完成」卡 312px > 260px 上限（四卡 vs 原型三卡）
3. 出貨流程漏附量測 JSON——工序要求：以後出貨必附 measure JSON（老闆拍板寫入要求）

### B. zaiVision 視覺簽核（老闆拍板改用 zaiVision 代替 llava；截圖同目錄 m390_s / t768_s / d_top.jpg）
- d1440＝FAIL：「進行中」卡長文擠壓黏連（+2124行 / T+TAG 28,000 一段）；ETA 欄窄到逐字直排（「等老窗 Windows Excel 開機後(v6)」）；「已完成(10-27)」備註欄同樣直排；卡片高度失衡；詳情與代碼字級偏細
- m390＝PASS with notes：右緣貼邊風險；長 URL／版本號零碎換行（建議 word-break: break-all 或省略號）；「已 完成」空格不統一
- t768＝PASS with notes：右欄「已排程」與「已完成(10-26)」之間大片空白、左右欄失衡；內文標籤目測 10–11px 偏細（建議 +1–2px）

### C. 驗收標準
修完出貨請附：measure JSON＋三 viewport 截圖；OpenClaw 側 zaiVision 重簽＋Playwright 重測，雙軌過先收。

## ② ranking CSV 供料（老闆拍板 3a：指南附全量）

- decision_ranking.csv：17,300 行（+1 header），sha256 前綴 5b40306f67503562
- 產出：run_sim.py --all --db-reset 全量重跑（背景：停擺期 data/copytrade.db 被清空——已復原並重生成）
- 復原核對：copy_sims 386,775 行；blocked 352,395；N<18 17,080；可排名 17,300；peak 88；recovery 最長 608 日——同指南 v1.1 數字全線一致

## ③ L0 進度查詢

A06E symbol PNG 停喺 64 張（12:15 後冇新）——L0 導出（145 全量）係完結定中斷？請 ZCODE_i 回覆狀態；F1BB 側 symbol_specs.csv 有更新。

## 附註（我方 lane，知會）

TradeDashboard v1.35 自檢鈎（TD_tabcmd）周末失效——OnTimer 有行，但 throttle 用 TimeCurrent（周末凍結）→ CheckTabCmd 永遠 early-return。v1.49 我方改 TimeLocal。

—— OpenClaw 12:45

> ✅ 已處理 2026-10-31 12:10 by ZCODE_w（派工收件：CSV 供料驗收收貨＋Board 修復 ⏳ 下工作鐘開工＋L0 查詢回覆——見 from_zcode 1205）
