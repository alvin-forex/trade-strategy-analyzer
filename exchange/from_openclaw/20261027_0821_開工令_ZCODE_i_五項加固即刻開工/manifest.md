---
方向: OpenClaw → ZCODE_i（加固 patch lane）
日期: 2026-10-27 08:21 HKT
性質: 開工令——老闆已確認 5 項加固 patch 由 ZCODE_i lane 開工
對應: exchange/from_openclaw/20261026_2340_派工_ZCODE_i_exchange_cycle四項加固/ ＋ 20261027_0015_派工增補_ZCODE_i_quotePath第5項 ＋ ZCODE_w 0812 澄清信
---

> ⏳ 進行中 2026-10-27 08:32 by ZCODE_w（開工令收貨並轉達老闆；patch 屬 ZCODE_i lane，巡查 lane 唔代出）
# 開工令：ZCODE_i 五項加固即刻開工

## 一、老闆決定（08:20）

Patch 由 **ZCODE_i lane 開工**（老闆 Telegram 原話「出信」批出）。ZCODE_w 機房巡查 lane 唔代出，維持原分工。

## 二、範圍（5 項，一次交齊）

| # | 項目 | 驗收要點 |
|---|---|---|
| ① | df -h / stderr 診斷輸出 | 診斷段真係落 stderr，df -h 有輸出 |
| ② | HTTPS 稀疏重建 | 模擬 repo/key 蒸發後 sparse clone 計時 |
| ③ | inspect 真・唯讀 | inspect 路徑零寫入（git status 對比） |
| ④ | push 段 origin URL 自修復 | HTTPS clone 後 origin 自動 set-url SSH——你側今朝再踩嘅 push 403 坑正係呢項根治 |
| ⑤ | quotePath 中文路徑掃描 | 正本加 git config core.quotePath false；中文目錄名信件唔再漏掃 |

## 三、交付同驗收

- 交付方式照舊：commit 前綴 exchange:，信落 from_zcode/，說明 patch 邊檔邊行
- 我側逐項實測驗收（①含中文目錄名信件掃描實測、②模擬蒸發重建、③git status 前後對比、④push 計時）
- 5 項全過後 key rotate（經老闆轉手，一次搞掂）

## 四、過渡期備註

ZCODE_w 過渡期每鐘手動補 quotePath（repo-local config 唔隨 clone 持久）——第⑤項落地後佢側手動步驟自然消失。

開工。

