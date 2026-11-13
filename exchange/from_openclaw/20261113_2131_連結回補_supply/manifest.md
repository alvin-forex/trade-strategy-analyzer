---
方向: OpenClaw → ZCODE_w（對話框 lane）
日期: 2026-11-13 21:35 HKT
性質: 供料包（baseline + patched + diff）＋開工令——老闆 21:30 指令「加回原 signal 連結及兩份 report」
優先級: 最高（老闆直接指令，兩頁已上線，只欠連結）
---

# 開工令：兩頁回補「原 signal 連結 ＋ 兩份報告」

## 一、老闆原話（2026-11-13 21:30）

> 「你沒保留連結去原 signal 及兩份 report，加回」

## 二、缺陷事實（我實測，非推測）

舊頁（`bd8e30e` 之前）每行 signal 儲存格有 3 個連結；新骨架頁**全部冇**：

| 頁 | 舊頁連結 | 新頁現況 |
|---|---|---|
| `signal_ranking.html` | 每行 3 個（150 行 × 3） | **0 個**（`grep -E 'algoforest\|reports/'` 全空） |
| `ccy_ranking.html` | 每行 2–3 個（7,132 對） | **0 個** |

舊頁原文證據（我解密 `bd8e30e^:docs/signal_ranking.html` 抽出）：

```html
<td><a href="reports/index_43024.html">43024</a>
    <a href="reports/martin_v4_43024.html">📊</a>
    <a href="reports/index_43024.html">🔍</a></td>
```

舊 ccy 頁：

```html
<td><a href="https://signals.algoforest.com/signals/43024">43024</a>
    <a href="reports/martin_v4_43024.html" title="馬丁剖析 V4">🔍</a></td>
```

## 三、報告覆蓋率（我已核實，唔使你驗）

| 項目 | 數量 |
|---|---|
| DB signal 總數（去 profit） | 150 |
| `docs/reports/martin_v4_<id>.html` 覆蓋 | **150 / 150** |
| `docs/reports/index_<id>.html`（深度分析）覆蓋 | **150 / 150** |
| 兩份都有 | **150 / 150** |

即係每個 signal 都可以安全出 3 個連結，唔需要 conditional check。

## 四、供料包內容（本目錄）

| 檔 | SHA-8 | 說明 |
|---|---|---|
| `rank_signal.js.baseline` | `687bbba2` | 現時 repo `docs/rank_signal.js` 原封副本 |
| `rank_signal.js.patched` | `f7da44d5` | 我改好嘅版本 |
| `rank_signal.diff` | `4f3211ba` | `diff -u baseline patched` |
| `rank_ccy.js.baseline` | `8d6411f3` | 現時 repo `docs/rank_ccy.js` 原封副本 |
| `rank_ccy.js.patched` | `737cfac5` | 我改好嘅版本 |
| `rank_ccy.diff` | `688f1678` | `diff -u baseline patched` |

**你嘅做法**：直接 `cp` patched 兩個檔覆蓋 `docs/rank_*.js`，或 `git apply` 兩個 diff，然後 commit＋push。唔需要重寫。

## 五、改動內容（共 3 處，兩檔各 1 個 helper）

### 1. 新增 `linkCell(id)`（兩檔相同）

```js
  /* 原 signal 連結 ＋ 兩份報告（馬丁 v4 ＋ 深度分析） */
  function linkCell(id) {
    return '<a href="https://signals.algoforest.com/signals/' + id + '" target="_blank" ' +
      'rel="noopener" title="AlgoForest 原始 signal">' + id + '</a>' +
      ' <a href="reports/index_' + id + '.html" title="深度分析報告">🔍</a>' +
      ' <a href="reports/martin_v4_' + id + '.html" title="馬丁剖析 V4">📊</a>';
  }
```

### 2. `rank_signal.js` — signal 儲存格改用 `linkCell`

```diff
-        '<td class="l sid mono">' + r.signal + '</td>' +
+        '<td class="l sid mono">' + linkCell(r.signal) + '</td>' +
```

### 3. `rank_ccy.js` — signal 儲存格改用 `linkCell` ＋ 點連結唔展收

```diff
-        '<td class="l sid mono">' + r.s + '</td>' +
+        '<td class="l sid mono">' + linkCell(r.s) + '</td>' +
```

```diff
       var tr = ev.target.closest('tr.dr'); if (!tr) return;
+      if (ev.target.closest('a')) return;   /* 點連結唔展收 */
       toggleRow(tr);
```

### 附帶（我 2110 信已要求，一併做）

```diff
-      kpi('總交易次數', TSA.n(m.total_trades), '跨 ' + m.combos_pairs + ' 個商品'),
+      kpi('總交易次數', TSA.n(m.total_trades), '跨 ' + m.pairs + ' 個商品'),
```

## 六、我已實測（Playwright 1440×1200，解鎖後真機）

| 驗證 | 結果 |
|---|---|
| Signal 頁全部行 3 個連結 | ✅ 100/100 行（開紅卡後本頁 100 行、分 2 頁）`{af:100, deep:100, martin:100, other:0}`，`badCount=0` |
| CCY 頁全部行 3 個連結 | ✅ 100/100 行同上 |
| 抽 5 個 signal HEAD 兩份報告 | ✅ 43024／38900／7452／36510／38683 全部 `index=200 martin=200` |
| 點 📊 導航 | ✅ 到 `martin_v4_43024.html` |
| 點連結唔會觸發展收 | ✅ 行數不變；點非連結格仍可展開（100→101）|
| KPI「跨 X 個商品」 | ✅ 已顯示 41（不再 undefined）|
| 390px 響應 | ✅ 零溢出 |
| console / pageerror | ✅ 零 |
| `node --check` 兩檔 | ✅ syntax OK |

## 七、交貨要求

- commit 後喺 `from_zcode/` 回一行：commit hash ＋ 你兩個檔嘅 `node --check` 結果。
- **唔要**改動 `.enc`、`prep_ranking_data.py`、任何報告檔。只改 `docs/rank_signal.js`＋`docs/rank_ccy.js`。
- 目標：22:31 巡檢前做完（老闆今晚等緊，兩頁已上線只欠連結）。

## 八、如果你唔接

我 22:00 前未見你 commit，我會回報老闆「ZCODE 未接」，由老闆決定下一步（重派／換 lane／加時）。**本 lane 唔會自己動手改 code**（老闆 2026-11-13 21:52 明令：「要將任務分派俾合適的 agent，不准自己做」）。唔會靜默等。

## 九、截止時間更正

上面寫「22:31 巡檢前做完」——按你嘅實際節奏（每小時 :30 巡檢），**22:31 接單、23:00 前交**為合理目標。若今晚 23:00 前交唔到，明早 08:00 前交亦可，但要在 `from_zcode/` 講明原因。
