---
方向: OpenClaw → ZCODE_i（機房lane 派工）
日期: 2026-10-26 23:40 HKT
性質: 派工信——exchange_cycle.sh 四項加固（老闆 23:38 TG 批「批」）
對應: from_zcode/20261026_2256_ZCODE_w_key到位push首通＋origin_url弱點報告.md（第④項來源）；from_openclaw/20261026_1000_key_misdiagnosis_public_repo/（①②③來源）
---


> ⏳ 進行中 2026-10-26 23:45 by ZCODE_w（派工信收貨確認；patch 交付歸 ZCODE_i lane，另報一項新發現 quotePath 見回信）
# 派工：exchange_cycle.sh 四項加固（老闆已批）

## 範圍
exchange/tools/zcode/exchange_cycle.sh 及其呼叫嘅輔助腳本。

## 四項要求
1. **診斷可見**：巡查報告加 `df -h`（至少根目錄同 repo 所在掛載點）＋任何步驟失敗時 stderr 原文節錄（前後文各幾行，截斷防爆炸）。
2. **稀疏重建**：repo 蒸發後嘅 HTTPS fallback clone 改稀疏 clone（建議淨拉 exchange/＋巡查所需最小集；實際範圍你側定，目標＝重建快、慳帶寬）。
3. **inspect 真・唯讀**：巡查/inspect 路徑任何情況下不得寫入 repo 工作區（連 stamp 都要行 main flow，唔准 side-effect 落 repo）。
4. **push 段 origin 自修復**：push 前檢查——origin URL 係 https:// 而 ~/.ssh/zcode_exchange_key 在位 → 自動 `git remote set-url origin <SSH_URL>` 先至推；https:// 而 key 唔在位 → 照舊留本地＋如實報「無 key」，唔好再報「憑證/遠端分叉」。

## 驗收（OpenClaw 側）
- patch 經 exchange/from_zcode/ 交（照舊帶 manifest＋改動檔）
- 逐項實測：①報告採樣、②模擬蒸發＋計時重建、③巡查前後 git status 對比、④模擬 HTTPS clone 後 push
- 四項全過 → 回執 + 老闆安排 rotate key（今輪用完 rotate，慣例）

## 照舊約束
禁 force push・禁 git add -A・martin_v4 禁區・禁 commit 憑證。
