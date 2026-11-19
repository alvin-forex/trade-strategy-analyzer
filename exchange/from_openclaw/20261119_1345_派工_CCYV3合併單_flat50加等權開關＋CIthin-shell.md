# 派工：CCYV3 合併單（#33 D1 flat 50 ＋ #36 等權開關）

- 日期：2026-11-19 13:45 HKT
- 來源：老闆 11-19 13:29「按你建議」（合併單獲批）＋老闆 11-04 21:30 裁決 A（v3 加等權模式開關，ATR 加權留 default）
- 承接：ZCODE（code lane）
- 死線：**2026-11-21 18:00 HKT**

## 一、範圍（兩項合併一單）

### #33 CCY v3 D1 flat 50
- 現況：patch 只落 repo，**未落終端**。725B（`725B72F25E46C780EF59F57016D58156`）MQL5/Experts 內 .mq5 仍係 10-26 版、mtime 未變、`flat 50` 相關字串 0 命中。
- 要求：把已驗收嘅 flat-50 版本落實際終端檔，並在交付報告列 `版本字串＋mtime＋grep 命中行`。

### #36 CCY v3 等權開關
- 現況：`InpEqualWeight` 全碟 0 命中＝未開工。
- 要求：加 input 開關（enum 用數字，符合 repo AGENTS.md 規範）：
  - `InpEqualWeight = 0`（default）＝維持現行 ATR 加權
  - `InpEqualWeight = 1`＝等權模式
- 註解全英文、input 名前綴 `Inp`＋PascalCase、input group 次序按 repo AGENTS.md 第 5 節。

## 二、交付要求

1. 編譯 0 error、0 warning 新增（附編譯 log 尾部）
2. 終端部署後實測：附 `ls -la` 檔案時間＋`grep -n InpEqualWeight <終端路徑>` 實際命中輸出
3. set 檔若有 enum，數值寫法（非字串）
4. 附逐檔 commit hash 表
5. 唔准改其他 EA／唔准改 CCY Reader（#34 已砍）

## 三、驗收（OC 側機器閘）

- `grep -c InpEqualWeight` 於 725B 終端 .mq5 ≥ 1
- 終端 .mq5 mtime 晚於本單日期
- 編譯 log 0 error
- repo 與終端版本一致（md5 或版本字串比對）

## 四、附帶發現（非本單，但請順手處理）

CI regression 11-19 05:30 紅：L25 page-quality gate 報
`[thin-shell] campaign/video/index.html —— 非動態頁可見文本僅 332 字（<400）`

- 該頁正是 11-19 sidebar 批次（commit 60b6a6c91）改過嘅頁之一
- 處理兩選一：①補內容至 ≥400 字 ②若確屬設計則入 `tests/page_quality_baseline.json`（要有 owner＋reason）
- 請喺本單交付報告一併回報處理方式

## 五、Link

- 任務板：https://alvin-forex.github.io/trade-strategy-analyzer/admin/tasks_board.html
- CCY 對比報告（原版 vs v3）：exchange/from_openclaw/20261104_1700_對比報告_CCY原版vs_v3/
