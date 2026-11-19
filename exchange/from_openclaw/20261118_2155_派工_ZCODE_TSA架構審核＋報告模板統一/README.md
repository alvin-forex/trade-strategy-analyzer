# 派工：TSA 架構審核 ＋ 報告模板統一建議

- 卡：#28（https://github.com/alvin-forex/trade-strategy-analyzer/issues/28）
- lane：zcode-local
- 派工時間：2026-11-18 21:55 HKT
- 死線：2026-11-20 18:00 HKT
- 老闆原話時間：2026-11-18 21:45

## 老闆原話
> 你指示ZCODE檢查一次TSA的架構及各版的統一性, 給我建議如何改善.
> 特別係兩個的REPORT的TEMPLATE, 完全無統一風格
> https://alvin-forex.github.io/trade-strategy-analyzer/reports/index_10344.html#sec-raw

## 交付物（三份 md，唔准改 code）

| 檔案 | 內容 |
|---|---|
| `docs/admin/TSA_ARCHITECTURE_AUDIT.md` | 目錄職責、生成器清單（邊隻仲用／邊隻死）、模板清單、資料鏈 |
| `docs/admin/REPORT_TEMPLATE_UNIFICATION.md` | **最緊要**：實際有幾多套視覺風格、各覆蓋幾多頁、差異清單、收斂方案（1 套定 2 套）、遷移路線、成本估算 |
| `docs/admin/REPORT_SECTION_SPEC.md` | section 結構規範（每類報告必須有邊幾節、固定 id、`#sec-raw` 錨點命名規則） |

## OC 已量化（你先核實，唔准照抄）

```
docs/reports/ 共 483 個 HTML
  martin_v*               169
  index_*                 159
  Signal_Deep_Analysis_*   81
  signal_*                 71
  date_range_review/*       2
  anomaly_report.html       1

引用 tsa_tokens.css（P0 統一 token）   377 / 481
完全冇引用（各自一套色）               104  ← signal_ 71、Signal_Deep_Analysis_ 24、index_ 8、anomaly 1
有 inline <style>                     481 / 481
```

重跑命令：
```
git ls-tree -r --name-only origin/main | grep -c '^docs/reports/.*\.html$'       # 483
grep -L tsa_tokens.css docs/reports/*.html | wc -l                               # 104
grep -l '<style' docs/reports/*.html | wc -l                                     # 481
```

## 驗收準則（機器可判）

- [ ] 三份 md 開頭有「現況數字 → 目標數字」對照表
- [ ] 每個數字附重跑命令
- [ ] 每項改動寫明「影響 N 頁 + 驗收命令」
- [ ] 零空話（唔准「建議考慮」「可以優化」）
- [ ] `python scripts/tsa_qa_check.py` PASS
- [ ] `python tests/language_check.py` → 0 violations

## 已知陷阱

1. 483 頁有大量係歷史快照，**唔一定全部統一**。要分辨「活的」vs「存檔」，判斷寫入報告，唔准一刀切。
2. `Signal_Deep_Analysis_5117.html` 32 MB、`index_17611.html` 18.8 MB — 重生成本高。
3. 只寫 md，**唔准改任何 .html 或生成器**。改動要老闆批准後另開卡。

## 通道（新規則，即刻生效）

1. 你個 clone 已失效（OC 今晚改寫咗歷史）。先做：
   ```
   git fetch --all --prune --force
   git reset --hard origin/local/alvin
   ```
   **嚴禁 `git pull --rebase`** — 會撞 240 個 commit 落差。
2. 完成後：push `local/alvin` → **自己即刻開 PR**（唔使等 OC）。
3. notify 檔照協議寫，同 commit 一齊 push：`exchange/notify/from_zcode/<時戳>_<事項>.md`
4. 唔准開 Issue（卡由 OC 開）。

> ✅ 已處理 2026-11-19 08:40 by ZCODE_w（收悉）
