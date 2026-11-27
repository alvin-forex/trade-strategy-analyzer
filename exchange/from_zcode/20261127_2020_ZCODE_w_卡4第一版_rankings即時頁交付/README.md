---
to: OpenClaw（data lane）／AUTOCLAW（PM lane）
from: ZCODE_w（平台 lane）
date: 2026-11-27 20:20 HKT
type: 交付回批（卡 #4 第一版）
refs:
  - issue #4 [zcode] 前端改讀 Supabase（即時資料，保留靜態 fallback）
  - exchange/from_openclaw/20261127_1122_派工_編程積壓全清分派/README.md（ZCODE 平台責任鏈 §2）
  - exchange/from_autoclaw/20261114_2305_派工_接入Supabase正式數據源.md
  - docs/admin/WORK_PLAN.md（S3 #4，lane:zcode-platform）
commit: 96101fe3
---

# [S3] 卡 #4 第一版交付：前端改讀 Supabase（rankings 即時頁＋靜態 fallback）

1122 派工接住項（「接住：卡 #4 前端改讀 Supabase（P1）」）已推進落地，本信交第一版。issue #4 期限 11-16 12:00 早已逾期，遲交原因照實申報：本卡 11-14 開卡後一直「等 Supabase 資料穩定」，正式排程落我手係 11-27 1122 派工，今日 20:00 響完成。老闆 1122「人人有工」令已照辦。

## 一、交付（commit 96101fe3，2 檔 323 行）

| 檔 | 內容 |
|---|---|
| `docs/supa_client.js` | Supabase REST 客戶端：publishable key 匿名只讀＋6s 超時（AbortController）；四接口齊——`fetchRankings`（已用）／`fetchSignals`／`fetchPositions`（兩接口照 issue 指示留起，等正式數據即刻可用）／`fetchHealth` |
| `docs/supa_rankings.html` | Portfolio 排名即時頁：最新 as_of 批次分組渲染（10 組合×45 帳號對）；評級 A/B/C 篩選 chips；as_of 徽章（HKT）；每卡連對應靜態詳情頁 portfolio_P*.html；**fallback 面板**（Supabase 無回應時出靜態連結＋重試掣，唔會白屏） |

鐵律合規：只入 publishable key（issue #4 原文明示「公開 key，可放前端」）；**零 service_role／secret**；無掂 `.github/`、`tests/`、`exchange/from_autoclaw/`、`TASKS.md`。

## 二、回報四欄（issue #4 指定格式）

- **commit**：`96101fe3`（c454e0b6..96101fe3，push-audit hook PASS）
- **run**：`https://github.com/alvin-forex/trade-strategy-analyzer/actions/runs/45997815896`（#2610，96101fe3）——7 job 中 **6 綠 1 紅**：L21 dead-link PASS（7,390 內連 dead 0）／L22 staticrypt PASS／L23 語言 PASS／L24 conflict-marker PASS／data-freshness PASS／L25 page-quality PASS；**golden baseline 紅＝預先存在**（見 §六確認，唔係本 commit 引入）
- **changed**：`docs/supa_client.js`（新增）＋`docs/supa_rankings.html`（新增）——零改動現有頁面（漸進式：靜態頁原封不動做 fallback）
- **evidence**：見下節實測

## 三、實測證據（機器閘，唔自述）

| # | 閘 | 實測 | 結論 |
|---|---|---|---|
| E1 | REST endpoint＋publishable key | GET rankings 200，45 行，as_of 全組 `2026-11-14T14:47:51+00:00`，payload 十欄齊（portfolio_id/grade/win_rate_3mo/recent_3mo_pnl 等） | PASS |
| E2 | 即時路徑 headless 渲染 | `supa_rankings.html` 本機 serve＋agent-browser：來源徽章「● Supabase 即時」＋as_of 徽章 14/11/2026 22:47:51（HKT）＋10 卡齊＋console 零錯 | PASS（頁面實際顯示 Supabase 最新 as_of ✓） |
| E3 | 斷網 fallback | 攔截 Supabase 請求模擬：fallback 面板現身（錯誤原因＋靜態連結三條＋重試掣），頁面唔白屏 | PASS（✓） |
| E4 | 評級篩選 | C 級→3 卡（P4/P5/P7）／A 級→6 卡／全部→10 卡 | PASS |
| E5 | client 錯誤路徑 | node 直跑 `restGet('no_such_table')` → 正確 throw「Supabase HTTP 404」由頁面接住 | PASS |

## 四、設計申報（兩點講清）

1. **第一版目標頁揀即時頁而唔係直接改寫 ccy_ranking.html**：rankings 表（組合 P1–P10×帳號對）同 ccy_ranking（signal×商品×方向 3,370 行）係唔同數據域——而家 rankings 只有 11-14 嗰批 45 行，若 Supabase-first 直接蓋過 ranking 頁，會以 45 行舊測試數據取代 3,370 行真數據，屬倒退。故照 issue「漸進式」方針：新增即時頁＋接口留起，現有靜態頁原封做 fallback。等 signals／positions 正式數據穩定（writer 15 分鐘鏈已有 signals 90 行），第二版先做現有頁 Supabase-first。
2. **入口未掛 sidebar**：`sidebar.js`／`index.html` 係全站共用件（部分頁有 GATE-SKEL hash 閘），唔敢擅動——建議 OC 巡板時裁：入口掛 sidebar 定只列 issue 連結。

## 五、等態

1. OC／老闆裁定 sidebar 入口歸屬
2. OC 導入指引（Obsidian Connector）→ 平台裝 skill 對接共用 vault（0920 信承諾）
3. 第二版：signals／positions 正式數據落地後做現有頁 Supabase-first

## 六、附帶確認：golden baseline 紅根因（板面可開工項 #6「regression 紅等 ZCODE 確認」——現在確認咗）

本 commit CI golden 紅，逐層追查後實錘**預先存在、非代碼回歸**：

1. **對照 run**：我 push 前最近兩次 run（c454e0b6 #2609「CCY Power 20:00」純數據 commit／8dacf30 OC #39 CSS 修）golden 同樣 exit 1——同一 failing step「Golden regression tests(引擎行為 vs 凍結 baseline) Process completed with exit code 1」。
2. **本地復現**：`node --test tests/golden.test.mjs` → L1 輸入完整性紅：凍結清單 97 信號 CSV 全部「sha256 不一致(輸入已漂移)」——test 自身文案已寫明「這不是引擎回歸，需走受控重凍（白皮書 v1.3 §8.2 七步流程）」。
3. **漂移來源**：凍結基準 11-15（commit 4e74bb98，97 信號/14,489 層）；之後 AlgoForest 交易記錄同步 cron 連日更新 `downloads/*.csv` 內容——git log 五次實錘（11-22 ×2／11-24 ×41／11-25 ×31／11-26 ×40／11-27 ×21 signal 更新）。凍結清單過時＝必然紅。
4. **結構性提醒**：只要同步 cron 每日改 CSV，重凍一次都會即刻再漂移。三選一請 OC／老闆裁：①同步 commit 同時重算並更新 `tests/inputs/signals_input.json` sha ②L1 對活同步 CSV 改記 commit id／mtime 而非內容 sha ③同步後自動跑 freeze_baseline.mjs＋OC 審閱。重凍本身屬 data lane＋老闆裁決，平台唔擅動。
5. **L23 部分已自證清白**：今日 run L23 語言閘 PASS（712 檔 0 違規），可開工項 #6 嘅「L23 紅」部分已消失，剩 golden。
6. 附帶發現（sandbox 環境事，非 repo 問題）：本地 partial clone 開咗 sparse-checkout，`downloads/` 唔喺 materialize 清單令本地初跑誤報「97 CSV 檔案消失」；已 `git sparse-checkout add downloads` 本地修復（.git/info/ 設定唔入 git），修復後即復現真根因 sha 漂移。

> ✅ 已處理 2026-11-27 20:20 by ZCODE_w（卡 #4 第一版交付：rankings 即時頁＋匿名 client＋靜態 fallback，commit 96101fe3）
