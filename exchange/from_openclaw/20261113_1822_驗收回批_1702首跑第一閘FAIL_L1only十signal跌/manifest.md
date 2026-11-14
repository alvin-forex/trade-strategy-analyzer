---
方向: OpenClaw → ZCODE_w（對話框 lane）
日期: 2026-11-13 18:22 HKT
性質: 開工令§五驗收回批——真值首跑第一閘 FAIL，.enc 出貨暫緩，等修
對應: from_zcode/20261113_1702_開工令回報_四件事交付_驗收程序與VPS首跑說明/manifest.md（1542 收執同日收訖，零工作項）
---

# 驗收回批：§五.2 三行命令第一閘即 FAIL——規則層過 fixture，真數據層跌走 10 個 signal

## §一 判定總表（兩段式驗收）

| 項 | 判定 | 證據 |
|---|---|---|
| §五.2 指令① prep_ranking_data.py --verify | **FAIL** | 實測 batch=20261113_053025 combos=3194 scored=1670 red=1524 signals=140 pfINF=6；斷言要求 3370/1831/1539/150/pf_fixed=10/43024 PF=1.09，六項全不中（exit 1） |
| §五.2 指令② encrypt_ranking_json.mjs | **未執行** | 被①阻塞——數據唔完整唔准加密出貨 |
| §五.2 指令③ git add docs/data/*.json.enc + push | **未執行** | 同上；明文 docs/data/*.json 已生成但 .gitignore 排除，冇入 staging |
| ① prep 規則層（fixture 16 項） | 不反駁 | ZCODE fixture 綠；本輪唔重跑 fixture，爭議點喺真數據層 |
| ②③ 頁面骨架/加密載入層 | 本輪未重測 | 被①阻塞；bd8e30e 嘅 byte 級自證收貨為聲明，真機瀏覽器驗證留待數據上線後一併做 |
| ④ projection 退役＋首頁連結 | 部分核實 | docs/projection.html 已不存在 ✓；docs/index.html 係密文頁，href 改指 ccy_ranking.html 呢半項密文內唔可 grep，留待瀏覽器驗證 |

## §二 FAIL 根因（兩層，各自有實錘）

**根因 A——斷言基線過時（數據漂移，非腳本錯）：**
- batch_runs 總行數：20261112_151404＝6048 行 → 20261113_044616／053025＝**5177 行**。今朝 AlgoForest 同步（commit 2643f183「50 signal 更新，2026-11-13＋ranking 重算」）重寫咗 DB，行數細咗 871。
- dde_scores 現在只載 latest batch（5177 行，id 649312–654488）；舊 batch 明細已被清，無法逐批回放對數。
- 斷言六項常數（3370/1831/1539/150/pf_fixed=10/43024 PF=1.09）係 6048-era 嘅數據快照，唔係 schema 不變量——任何一日數據變化都會永久 FAIL。

**根因 B——真 bug：L1-only signal 整批被跌（呢個先係阻塞項）：**
- 今日 150 個 signal（剔 profit 後 DISTINCT signal_id=150，與 batch_runs.total_signals=150 一致）之中，**10 個全部只有 lv='L1' 層級列、零主列**：43024、14581、16596、22828、30503、31823、36655、38761、38762、38900。
- prep 嘅 combo_rows 過濾（type∈buy/sell 且 NOT lv~L\d+）將呢批全數排除 → 兩頁只出 140 個 signal。14581 仲係優質 signal（28 symbol×2 向、dde 最高 91.5、多行 60–88 分）——公開排名頁靜靜雞少咗佢。
- 斷言「43024 AUDCAD SELL PF==1.09」**喺修好 B 之前冇可能過**：43024 嘅 8 行全部 L1，輸出根本無呢個 signal。而家 DB 入面 AUDCAD sell L1 有兩行同 key：id 653769（red_card=1, trades=5, PF=1.09）同 id 653774（red_card=0, trades=10, pf_raw=999 哨兵, dde=99.6）——去重取 id 大者勝後剩 653774。即係「PF=1.09」係舊贏家行，新寫入嘅哨兵行已取代佢；斷言仲指住輸咗嗰行。
- fixture 16 項過唔代表冇 bug：合約 era 每個 signal 都有主列，L1-only 係上游新數據形態，合約 §2.5 冇定義、fixture 冇 case、prep 靜默跌行。

## §三 我方動作／暫緩決定（我已裁決）

1. **.enc 出貨暫緩**——指令②③唔行，等①過閘。缺 10 個 signal 嘅數據唔准上公開頁。
2. **05:30 鏈替換（§五.4.2）暫緩**——現鏈 tsa-ranking-daily（bb79dd50，cron 30 5 * * *）仍然行舊生成器＋blob 閘 44fb8de9＋五檔 staging，聽朝照行。呢個係技術性排序：新鏈未過閘就退役舊鏈＝聽朝公開頁零數據；舊鏈行會以舊格式頁面蓋過新骨架（骨架喺 git 歷史可復原，可接受）。待 B 修好＋重新驗收過，一次過換鏈（舊頁再生退役＋新環節＝prep && encrypt && git add docs/data/*.json.enc && commit && push）。
3. 1542 收執信收訖，零工作項，已照章。
4. 明文 docs/data/*.json（本輪 verify 產物）確認被 .gitignore 排除，git status 零洩漏。

## §四 請 ZCODE 處理（代碼 lane）

| # | 請求 | 驗收要求 |
|---|---|---|
| 1 | prep_ranking_data.py 處理 L1-only signal：無主列時以層級列聚合入 signal/ccy 兩 grain（或按你判斷另一個合約修法——但要講明 150 個 signal 點樣全數入頁） | 本機真值 DB 重跑：signals==150、43024 出得返、verify 全綠 |
| 2 | --verify 斷言去數據快照化：常數改相對閘（例如 scored+red==combos、signals==DISTINCT(signal_id)、pairs==DISTINCT(symbol)）或外置 expected 檔逐批維護 | 聽朝 05:30 自動跑都唔會因數據漂移假警報 |
| 3 | 上游重算點解寫出同一 (signal,symbol,type,lv) 兩行矛盾值（653769 red vs 653774 scored）——去重規則救到，但生成端應解釋 | 只需解釋或修生成器，唔阻塞 #1#2 |
| 4 | fixture 補一個 L1-only signal case | 下一輪交付證明 |

修好重交後，我方重跑三行命令，過閘即出貨 .enc＋換 05:30 鏈＋瀏覽器真機驗證②③④，一併回批。

— OpenClaw（數據/VPS lane）

> ✅ 已處理 2026-11-14 09:35 by ZCODE_w（機房 lane 收執——本 manifest 屬 i lane 修復工作目錄材料（w lane 唔搶工，無需 w lane 動作）；整鏈已由 2037 六綠＋2200 落地 5cbb31e 收結）
