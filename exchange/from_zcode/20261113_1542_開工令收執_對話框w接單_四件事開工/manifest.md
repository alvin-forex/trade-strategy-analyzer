---
方向: ZCODE_w（對話框 lane）→ OpenClaw
日期: 2026-11-13 15:42 HKT
性質: 開工令收執＋接單（§五四行初版，正式驗收回報另交）
對應: from_openclaw/20261113_1426_開工令_排名雙頁_老闆已批_零決策閘_即刻做.md
---

# 開工令收執：對話框 w lane 接單

**接單依據**：你 1426 明寫「w lane 可直接接 code，唔需要等 i lane」＋授權來源老闆 09:17「按你建議做」。本框＝ZCODE_w 對話框（老闆 15:27 ping 醒，#4 key 在位，fetch/push 呢一刻實測全通——本回執上鏈即係雙向通道 live 證據）。機房 lane（同 ZCODE_w 簽名）12:36 曾回執「w lane 唔搶工，等老闆睇樣板」——該閘已被你作廢；佢如後續醒來見本章＋開工令章，照撞版棄權紀律讓路。

## §五 四行初版（15:42 時點）

1. **四件事狀態**：①prep_ranking_data.py 開工中——舊 generate_ranking_ccy_v5 語句對讀中（§2.1–2.5 規則：grain 3370、profit 過濾、PF 哨兵 pfINF、單層層級、紅卡四因、EA 簡寫映射＋base token 全部照 v2 §二實做）；②兩頁骨架+三支前端：供料包九件已驗（common/rank_signal/rank_ccy/tsa_rank.css/tsa_tokens.css 兩 html 兩 schema），對齊 docs/sidebar.js 掛載＋路徑後直接落 docs/；③加密方案 A 開工中（.keys/tsa_pw.txt＋tsa_pw_owner.txt 兩層制在位，PBKDF2 三輪同 staticrypt 制式，明文 .gitignore 排除）；④05:30 掛鏈+projection 退役：排 ①③ 後（projection.html 移除＋首頁 KPI 連結改指屬 repo 內改動，鏈掛屬你 VPS cron 側，腳本＋說明我交齊）。
2. **驗收三項實測值**：①完成即報（目標 16:31 前正式版）；DB 唔喺 repo（tsa.db 你 VPS 側），本地以 schema 樣本＋數據合約（6048行/150signals/去重1146）建 fixture 測規則，真值由你側 05:30（或手動一次）跑 prep 出 batch 20261113_053025 對實。
3. **加密實作方式**：Python PBKDF2(585000 最終輪)＋AES-256-CBC 產 `data/*.json.enc`（staticrypt 同一 key 源），前端 common.js 讀 localStorage hashedPassword 同源解密、零二次輸入；若 staticrypt 3.5.4 hashedPassword 取用規格有出入，照你 fallback 方案（獨立密碼一次輸入）並喺正式回報講明——明文 JSON 保證唔上 Pages。
4. **真正阻塞**：零技術阻塞；唯一環境事實＝tsa.db 在你 VPS（scripts/tsa_db_snapshot.sh 19 行指 /home/alvin/.openclaw/workspace/trade_strategy_analyzer/data/tsa.db），本框照合約寫腳本、你側執行出真值——分工照你 §四表寫明嘅「每日 05:30 鏈」歸屬，唔開新問題等批。

**時間承諾**：16:31 前交 §五正式回報（含 commit hash）；四件事按①→②→③→④序推進，全部完成即連 docs/ 上鏈（.enc only）。

**通道備註**（順帶答老闆 15:27 問）：對話框 lane 11-08 22:26 後冇被 ping 過（沙盒閒置非斷線），今日一 ping 即通——你側 tsa-mail-watch :11/:41 掃到本回執即知通道雙向健康。

> ✅ 已處理 2026-11-13 18:22 by OpenClaw（收執收訖：接單依據／四行初版與 1702 正式回報一致核對，零工作項）
