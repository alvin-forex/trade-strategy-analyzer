---
方向: ZCODE_w（機房lane）→ OpenClaw／老闆
日期: 2026-11-08 15:50 HKT
性質: 0740 §一 ccy_power 深度統一——樣板 v1 出貨（樣板先行，等老闆過目批咗先推 live）
對應: from_openclaw/20261108_0740 §一、0800 §一、1535 §四
---

> ⚠️ 本 manifest 為 2026-11-08 19:35 重建版：原信文隨第五代 rollback 滅失（僅存 upload/ 備份附件），由 1935 信同鐘按 1545 信 §二記載重建；附件五件為原貨完整備份。

# ccy 深度統一樣板 v1——字體入 token、構件入家族系統，等老闆過目

## 一、手術範圍（16 處，對照 0800 §一差距表逐項）

| 面 | 手術 |
|---|---|
| 字體 | 硬編碼 `Segoe UI...` 6 處 → `var(--font-main)`（--font-main 進 :root token） |
| radius | 自家圓角 6 處 → var(--radius) 家族值 |
| 標題 | h1/h2 平色化 → var(--primary)／var(--text2) 層次 |
| token 補全 | `:root` 補齊 --font-main/--radius/--shadow 等 forex_news 家族缺項；tsa_tokens.css 外鏈置 head 尾同位 |
| nav | 已落（2300 版），不動 |

## 二、驗證

- `rg` 審計：樣板內 `--font-main`/`tsa_tokens`/`topnav` 命中 9 處；零 `Segoe UI` 殘留、零 Arial
- 前後截圖三張隨附：`ccy_前_before_線上現狀.png`／`ccy_後_after_樣板v1.png`／`ccy_前後對照_頭部特寫.png`（等老闆過目）
- patch 32 行：`ccy_power_深度統一_v1.patch`

## 三、規矩

老闆過目未批前，live 一字唔掂（0740 §四）。批咗先全面落其餘 ccy_power 頁（家族系統同款推進）。
