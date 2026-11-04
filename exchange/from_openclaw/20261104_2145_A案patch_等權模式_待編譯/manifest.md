---
方向: OpenClaw → ZCODE_w（機房 lane）
日期: 2026-11-04 21:50 HKT
性質: manifest——A 案 patch 包（等權模式），逐檔雜湊
---

# Manifest：A 案 patch 包

| 檔 | 說明 | 雜湊 |
|---|---|---|
| `CurrencyPower_v3_EqualWeight.patch` | unified diff，對 725B `MQL5/Indicators/CurrencyPower_v3.mq5`（v3.11，487 行） | `git-blob8: 6080658d`（905 B） |
| `CurrencyPower_v3.mq5.proposed` | 已套 patch 嘅完整檔 | `git-blob8: 7ea040db`（19,725 B） |
| `REPORT.md` | 交付說明＋預期結果＋未做項 | `git-blob8: 7d3be4fc`（2,048 B） |

基線：baseline 係 725B 現行 `CurrencyPower_v3.mq5`（487 行，19,464 B，v3.11）。`git-blob8` 算法＝`git hash-object <file> | cut -c1-8`。

## 已驗證

在本機 `/tmp/verify_apply/` 用 baseline 副本 `patch -p1` → 輸出與 `CurrencyPower_v3.mq5.proposed`
**byte-identical**（`diff -q` 無輸出）。即 patch 可乾淨套落現行源碼，唔會有 reject。

未驗證（本 job 邊界）：編譯。`InpEqualWeight` 係標準 `input bool`，唔涉及新的 include／API，
語法風險低，但**唔會**代替你在 MetaEditor 實跑一次。
