# 派工：CI regression 紅燈 —— L25 thin-shell（campaign/video）

- 日期：2026-11-19 13:56 HKT
- 承接：ZCODE（tests/ 屬 code lane）
- 死線：2026-11-20 18:00 HKT
- 嚴重度：中（main 分支 CI 連紅，pages 部署本身成功，唔阻上線但遮蓋真問題）

## 一、事實

- `regression` workflow 由 11-18 起每次 push 都 failure（11-18 30 次、11-19 30 次，sample 全紅）。
- 失敗步驟：`L25 page-quality gate (placeholder / thin shell / data source)`
- 錯誤原文：
  ```
  ✗ 新違規（baseline 無記錄）——禁止 merge main：
    [thin-shell] campaign/video/index.html —— 非動態頁可見文本僅 332 字（<400）
  ```
- 該頁於 **2026-11-16 commit f09bc5fe3**（作者 alvn0808，"Add campaign product film page (Built with AutoClaw Round 3)"）加入；11-19 只係被 W-FINAL sidebar 批次（60b6a6c91）改過 head/body 引用，**內容本身冇改**。

## 二、判斷

呢頁係「15 秒產品影片」落地頁：主體係 `<video>`＋少量說明文字，332 字屬**設計本意**，唔應該硬湊 400 字廢話。

## 三、處理（二選一，建議 A）

**A（建議）入 baseline**：`tests/page_quality_baseline.json` 加一條，附 owner＋reason：
- path: `campaign/video/index.html`
- owner: ZCODE（頁面由 Round 3 產出）
- reason: 影片落地頁，主體為 `<video>`，可見文本 332 字屬設計；內容唔應灌水

**B** 若判定唔應存在：連同頁面一併下架（需老闆批，唔好自己刪）

## 四、驗收

- `gh run list --workflow=regression --limit 3` 連續 3 次 success
- L25 step 輸出 `0 violations`（或 baseline 命中 1 條）
- 附 run URL

## 五、唔准掂

- 唔准改 CCY EA／TD EA；本單只修 CI 閘與 baseline 記錄
- 唔准刪 `campaign/video/index.html`（除老闆明批）

> ✅ 已處理 2026-11-20 08:45 by ZCODE_w（平台接單：判準 1/3/4 純 json＋無本機依賴＋機器可驗收；A 案 baseline 條目已入＋本地 L25 綠燈 exit=0，詳交付信 0848；gh run list 驗證 OC 側執行）
