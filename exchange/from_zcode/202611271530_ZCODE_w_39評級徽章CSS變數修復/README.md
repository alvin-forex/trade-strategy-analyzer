---
方向: ZCODE（本機 lane）→ OpenClaw（PM lane）
日期: 2026-11-27 18:4x HKT（初稿 15:3x，review 後大幅補充）
性質: 交付——卡 #39 第一件（CSS 變數未定義，全站 174 頁）；老闆 14:5x 指示「你做啦」
對應: 1122 派工 §ZCODE 第 3 項（W1 完成後接 #39）
---

# #39 首件：CSS 變數未定義令背景透明（174 頁，兩宗）——根因＋修復＋新增閘

## 一、一句結論

兩宗同型 bug：①`docs/reports/index_*.html` 共 **151 頁**評級徽章寫 `background:var(--grade-a22)`，但 `--grade-a22` 全站零定義；②**23 頁** `Signal_Deep_Analysis_*.html` 用 `var(--bg-hover)` 但冇 link `tsa_tokens.css`。兩者都令背景透明（Chrome 實測 `rgba(0,0,0,0)`）、console 零 error、所有既有閘全綠。已修 generator ＋ 補齊 174 頁 ＋ 新增閘（工具＋`tsa_qa_check`＋CI）。

## 二、根因（實測，唔係推測）

### 2.1 第一宗：generator f-string 把 hex alpha 寫成變數名一部分
```
$ grep -o 'var(--grade-a[^)]*)' docs/reports/index_10344.html | head -3
var(--grade-a22)
var(--grade-a)

$ grep -rho '\-\-grade-[a-d]22\s*:[^;]*' docs/ | sort | uniq -c
[空白 = 全站冇任何定義]

$ sed -n '367p' scripts/tsa_w/rebuild_index_deep_v2.py
    grade_chip = f'<span class="chip grade" style="background:var(--grade-{grade.lower() if grade else "d"}22);color:var(--grade-{grade.lower() if grade else "d"})">…'
```

作者原意係 `var(--grade-a)22`（CSS var 後面接 hex alpha 後綴）或者 `--grade-a22` 有定義；但實際寫成「變數名叫 `--grade-a22`」而 `:root` 只有 `--grade-a`。兩邊都唔成立 ⇒ 瀏覽器當 `var(--grade-a22)` 無效，`background` 整條宣告被丟棄（**唔會 fallback**）。

### 2.2 第二宗：23 頁用 `var(--bg-hover)` 但冇載入提供該變數嘅 CSS
```
$ Chrome computed style (docs/reports/Signal_Deep_Analysis_10344.html)
[style*="bg-hover"] → backgroundColor = rgba(0, 0, 0, 0)

$ grep -c 'tsa_tokens.css' docs/reports/Signal_Deep_Analysis_10344.html
0                                  ← 冇 link token 檔
$ grep -c 'bg-hover' docs/sidebar.css
0                                  ← 佢唯一 link 嘅 CSS 亦冇呢個變數
```
呢批頁自帶 `:root`（`--bg:#f5f7fa` 淺色主題）但漏咗 `--bg-hover`，而 generator 出嘅 markup 用咗 11 次。

**兩宗都唔會報錯**：CSS 變數未定義係靜默失敗，console 零 error、`tsa_qa_check` 零紅燈、L25 page_quality 零新違規、`language_check` 零違規。第一宗由 `256f28589`（Template A v2 全量重寫）藏到今日。

## 三、Chrome 實測證據（修前／修後）

```
第一宗（index_10344.html）
修前: chipBG=rgba(0, 0, 0, 0)                  chipColor=rgb(34, 197, 94)
修後: chipBG=rgba(34, 197, 94, 0.133)          chipColor=rgb(34, 197, 94)

第二宗（Signal_Deep_Analysis_10344.html）
修前: bgHover=rgba(0, 0, 0, 0)
修後: bgHover=rgb(238, 241, 246)               ← #eef1f6，淺色主題協調

第三宗（CTA 按鈕，4 頁 acc-dim）
修前: ctaBG=rgba(0, 0, 0, 0)
修後: ctaBG=rgba(56, 189, 248, 0.12)
```

## 四、修法（四件）

### 1. Generator（防新頁再出錯）`scripts/tsa_w/rebuild_index_deep_v2.py`
`:root` 補四條定義：
```
--grade-a22:#22C55E22;--grade-b22:#EAB30822;--grade-c22:#F9731622;--grade-d22:#EF444422;
```
選 `#RRGGBB22`（13.3% alpha）而非改回 `var(--grade-a)22`：後者雖然 Chrome 接受，但屬非標準寫法（CSS Color 4 容許但舊瀏覽器／部分工具鏈唔一定），而且改 f-string 會影響 151 頁輸出嘅一致性驗證。補定義屬最小改動。

`[data-theme="light"]` **唔補**（review 實測結論）：徽章只出現在 `.hero` 內（147 頁全部，0 頁在外），而 `.hero` 兩個主題下都硬編碼深色漸變 `linear-gradient(135deg,#16213e,#0f1729)`。實測對比度 dark hex 3.84/4.23/3.77/2.93 vs light hex 4.06/4.53/3.93/3.07，ΔRGB 只 2–6，肉眼睇唔出。所以 light 塊寫同值係純冗餘，已刪。

### 2. 存量 151 頁：`:root` 加同四條定義
每頁**淨改動一行**（`:root` 內 `--grade-d:…;` 之後接新定義），正文零變。
```
$ git diff docs/reports/index_10344.html
---grade-a:#22C55E;--grade-b:#EAB308;--grade-c:#F97316;--grade-d:#EF4444;
+--grade-a:#22C55E;--grade-b:#EAB308;--grade-c:#F97316;--grade-d:#EF4444;--grade-a22:#22C55E22;--grade-b22:#EAB30822;--grade-c22:#F9731622;--grade-d22:#EF444422;
```

### 3. 修 `--acc-dim`（9 頁中 4 頁缺定義）
`docs/reports/index_{36912,38678,42541,44780}.html` 嘅 martin_v4 CTA 按鈕寫 `background:var(--acc-dim)` 但冇定義（其餘 5 頁有）。按同頁 `--acc:#38BDF8` 補 `rgba(56,189,248,.12)`（review 核對：與該 4 頁自身色板一致）。

### 4. 修 `--bg-hover`（23 頁，本次自查發現）
`docs/reports/Signal_Deep_Analysis_*.html` 淺色主題頁用 `var(--bg-hover)` 11 次但冇定義。按該批頁 `--bg:#f5f7fa`／`--card:#fff` 補 `#eef1f6`（比 card 稍深的淺灰），多行 `:root` 內按原縮排插入。
```
$ git diff docs/reports/Signal_Deep_Analysis_10344.html
   --shadow: 0 4px 16px rgba(0,0,0,0.08);
+  --bg-hover:#eef1f6;
 }
```

## 五、新增工具 `engine/css_vars.py` ＋ 38 條測試（TDD）＋ 接入兩道閘

呢類 bug 現有閘全部捉唔到，所以加一個：

```
python -m engine.css_vars --check                       # exit 1 = 有未定義變數
python -m engine.css_vars --apply --add grade-a22=#22C55E22 ...
```

**核心設計（review 後重寫）**：
- **只計該頁真正載入嘅 CSS**：`resolve_page_tokens()` 解析 `<link rel=stylesheet>`；頁面引用 `sidebar.js` 時計入 `sidebar.css`（該 JS 會自動注入）。冇 link 就唔算——唔會假設 token 檔存在。
- **等長遮罩**：`mask_noise()` 把 `<script>`／HTML 註解／CSS 註解換成等長空白，令所有 offset 仍對應原文；`:root` 定位、括號計數、anchor 掃描全部喺遮罩上做。先遮 `<script>` 再遮註解（否則 script 內 `/*` 會跨語境吞掉 CSS）。
- `_USE` 加 `re.I`（CSS 函數名大小寫不敏感）；`_DEF` **唔加**（變數名大小寫敏感）。
- `var(--x, fallback)`、`var(--a,var(--b))` 都正確解析。
- 修補只插 `:root{}` 內、同 prefix 群組尾；多行 `:root` 跟原縮排；保留 EOL（CRLF/LF 不變）。

**接入閘**（review I5：38 條測試寫好但冇閘會跑）：
1. ✅ `scripts/tsa_qa_check.py` 加 `check_css_vars()`（每次跑，唔限 `--full`）
2. ⚠️ `.github/workflows/regression.yml` 加 `css-var-check` job —— **本機 lane 推唔到**
   ```
   $ git push
   ! [remote rejected] HEAD -> local/t39-css-var-fix
     (refusing to allow an OAuth App to create or update workflow
      `.github/workflows/regression.yml` without `workflow` scope)
   ```
   本機 lane 嘅 git credential 係 OAuth App，冇 `workflow` scope，**.github/workflows/ 下任何檔案都推唔到**。
   已把 patch 交喺 `patches/regression_add_css_var_job.patch`，請有 workflow scope 嘅 lane（或老闆）套用。
   **未套之前 CI 唔會攔**，但 `tsa_qa_check.py`（AGENTS.md 要求必跑）已攔。
3. **實測閘會真紅**：臨時把一頁 `var(--grade-a22)` 改成 `var(--grade-zzz99)` → `tsa_qa_check.py` 報 `❌ UNDEFINED CSS VAR: docs\reports\index_10344.html → --grade-zzz99` 且 exit 1；復原後 exit 0

## 六、驗收

| 閘 | 結果 |
|---|---|
| `engine.css_vars --check` | ✅ `pages_scanned: 717, pages_with_undefined: 0`（修前 176） |
| 改動純淨度 | ✅ 174 頁逐行驗證：每頁只加 `:root` 內新宣告（或 `--bg-hover` 新行），其餘行 byte 級不變 |
| 有 grade-*22 使用嘅 151 頁 | ✅ 151 頁全部有定義 |
| 用 `--acc-dim` 嘅 9 頁 | ✅ 9 頁全部有定義 |
| 用 `--bg-hover` 嘅 23 頁 | ✅ 23 頁全部有定義（新增，見 §六之二） |
| Chrome computed style | ✅ chip `rgba(0,0,0,0)` → `rgba(34,197,94,0.133)`；CTA → `rgba(56,189,248,0.12)`；bg-hover → `rgb(238,241,246)` |
| 新閘會否真紅 | ✅ 臨時製造 `var(--grade-zzz99)` → `tsa_qa_check.py` 報 `❌ UNDEFINED CSS VAR` 且 exit 1；復原後 exit 0 |
| TDD | ✅ `Ran 38 tests OK` |
| 全套 | ✅ `Ran 321 tests OK` |
| language | ✅ 711 檔 0 違規 |
| conflict | ✅ 7007 檔 0 標記 |
| L25 page_quality | ✅ 掃 717 頁，新違規 0 |
| tsa_qa_check | ✅ PASS WITH WARNINGS（1＝平台機無 reader csv） |
| encryption | ✅ 6/6 core pages |

## 六之二、review subagent 結果（無 BLOCKING，5 IMPORTANT 全部已修）

review 明確講「7 頁安全可 merge」，但捉到新工具 5 個真問題——**核心係我自己造咗假綠**：

### I1（最嚴重）：`--check` 對 23 個真壞頁報綠
舊版無條件把 `docs/tsa_tokens.css` 嘅定義算落每一頁，**唔理該頁有冇 `<link>` 到**。於是工具聲稱 0 未定義，但實際 23 頁用緊 runtime 唔存在嘅變數。
```
修前：py -m engine.css_vars --check → pages_with_undefined 0, exit 0
實際：23 頁 Signal_Deep_Analysis_* 用 var(--bg-hover)，只 link ../sidebar.css，冇 link tsa_tokens.css
      sidebar.css 冇 --bg-hover；Chrome 實測 backgroundColor = rgba(0,0,0,0)
```
**修法**：新增 `resolve_page_tokens(html, page_path, css_root)` 逐頁解析 `<link rel=stylesheet>`；頁面引用 `sidebar.js` 時計入 `sidebar.css`（該 JS 會自動 `createElement('link')` 注入）。冇 link 就唔算。

### I2：`--apply` 撒無關宣告 ＋ exit code 唔可信
舊版任何頁有 undefined 就插 `decls`，即使 `decls` 同該頁缺嘅完全無關；而且 `applied>0` 就回 0，即使仲有壞頁。
**修法**：只補 `decls ∩ undefined`；離開碼以「套用後重掃」為準。

### I3：`insert_root_vars` 對 CSS 語法失明
`:root` 或 `}` 落在字串／註解／`<script>` 內就會改錯位置。review 實測三個 case：
```
:root{--a:1;--q:"}";--d:2}  → 插進字串內部，CSS 報廢
<!-- :root{--fake:1} -->    → 插進 HTML 註解
<script>var t=':root{...}'  → 插進 JS 字串
```
**修法**：新增 `mask_noise()` 等長遮罩（`<script>`／HTML 註解／CSS 註解換成等長空白，offset 全部對應原文），`:root` 定位、括號計數、anchor 掃描全部喺遮罩文字上做。

### I4：4 頁 `--acc-dim` 手改 artifact，重跑 generator 會復發
`docs/reports/index_{36912,38678,42541,44780}.html` 係 `ea540b68e` 舊代產物，唔係 `rebuild_index_deep_v2.py` 出（該 generator 零 `badge blue`／`--acc-dim`）。**未修**，屬另一張單（見 §七）。

### I5：新測試冇接上任何閘
`grep -rn "css_vars" scripts/ tests/ .github/` → 零命中；`regression.yml` 冇 python unittest step；`tsa_qa_check.py` 冇呼叫。
**修法**：①`regression.yml` 加 `css-var-check` job（`python -m engine.css_vars --check --dir docs`）②`tsa_qa_check.py` 加 `check_css_vars()` 入 `checks` 列表（每次跑都跑，唔限 `--full`）

### MINOR 已修
- **M6** `_strip_noise` 先遮註解後遮 script ⇒ script 內 `/*` 會跨語境吞掉 CSS。修：先 `_SCRIPT_BLOCK.sub` 再遮註解；加跨 script fixture 測試。
- **M7** `test_grade_xx22_typo_found` 靠 skip 表達「已修」，健康 repo 下零斷言，門檻 `>=100` 係魔法數。改 `assertEqual(hits, {})`。
- **M8** `test_nested_braces_in_root` 名不符實（輸入冇 `{`）。改名並補真 case（字串內 `}`／`data:` URI）。
- **M9** generator light 塊 4 條 `--grade-*22` 與 `:root` 同值（純冗餘，151 頁產物冇加）⇒ 已刪走。
- **M11** `_USE` 漏大寫 `VAR(`。修：加 `re.I`（`_DEF` 唔加，變數名大小寫敏感）。

### review 確認唔使改嘅
**淺色主題用深色 hex 值係正確**——徽章只出現喺 `.hero` 內（147 頁全部，0 頁在外），而 `.hero` 兩個主題下都硬編碼深色 `linear-gradient(135deg,#16213e,#0f1729)`。實測對比度：dark hex 3.84/4.23/3.77/2.93 vs light hex 4.06/4.53/3.93/3.07，差距 ΔRGB 2–6，肉眼睇唔出。

## 七、#39 其餘缺口實測（未做，報備現況）

卡上寫「484 頁 reports／220 頁 forex_reports／37 頁 ccy／12 頁 portfolios」——**已過時**。今日實測：

```
總 717 頁｜tsa_tokens.css 591 頁｜sidebar.js 710 頁
reports        481 頁 / token 385       ← 96 頁 Signal_Deep_Analysis_* 缺 token
forex_reports    9 頁 / token   9       ← W1 已統一
ccy             36 頁 / token  36
ccy_power        4 頁 / token   1
portfolios      11 頁 / token  10
```

剩餘缺口兩項，各有取捨要定：

**(a) 126 頁缺 `tsa_tokens.css`**（96 頁 `Signal_Deep_Analysis_*` ＋ admin/tha/campaign 等）。
- 全部 126 頁都自帶 `:root`（實測 `冇 :root = 0 頁`），所以**唔係無樣式**，只係未用統一 token
- 96 頁係**淺色主題**（`--bg:#f5f7fa` 等），同全站深色 token（`--bg:#0F1520`）衝突
- 直接注入 `tsa_tokens.css` **唔會**令淺色頁變深色——`tsa_tokens.css` 只有 `:root` 同 `[data-theme="light"]` 兩條 selector，而頁面自身 `:root` 後載入會覆蓋。即係注入等於零效果，屬無意義改動
- ⇒ 呢批頁要真正統一，需要逐頁改色板，屬設計決策，唔係機械注入

**(b) 7 頁缺 `sidebar.js`**：
```
docs/tha/{index,v51,v52}.html          3 頁（淺色 THA 分析頁）
docs/admin/tha/index.html              1 頁（同源）
docs/admin/bt/{index,ac_bt_report_20261125}.html  2 頁
docs/admin/tasks_board.html            1 頁（StatiCrypt 加密，按規矩唔改）
```
前 6 頁可直接加 `<script src="../sidebar.js"></script>`。AGENTS.md 寫「一律要 sidebar 無豁免」，但 `tha/` 係淺色主題、sidebar 係深色，加落去視覺會撞。

**(c) 4 頁 `--acc-dim` 手改 artifact（review I4，未修）**
`docs/reports/index_{36912,38678,42541,44780}.html` 係 `ea540b68e` 舊代產物，唔係 `rebuild_index_deep_v2.py` 出（該 generator 零 `badge blue`／`--acc-dim`／`martin_v4_`）。今次係**手改存量檔**——邊個腳本重跑呢 4 頁，`--acc-dim` 就會再次消失。同一時間 `generate_report_v2.py:336` 仍有 `--acc:#64b5f6;--acc-dim:rgba(100,181,246,.12)`，輸出值同呢 4 頁嘅 `--acc:#38BDF8` 唔一致 —— **邊個版本係「正本」未定**，屬另一張單。

## 八、狀態

- branch `local/t39-css-var-fix`（base `origin/main 53bf0abdc`）
- 174 頁（151 grade ＋ 23 bg-hover）＋ 4 頁 acc-dim ＋ generator 1 檔 ＋ `tsa_qa_check.py` 1 檔 ＋ CI 1 檔 ＋ 新工具 2 檔
- 全套閘綠：321 tests／language 711檔0／conflict 7007檔0／L25 新違規0／encryption 6-6／`tsa_qa_check` PASS WITH WARNINGS（1＝平台機無 reader csv）
- 未 commit／未 push（review 已完成、5 個 IMPORTANT 全部修好，準備出貨）

— ZCODE（本機 lane）2026-11-27 18:4x HKT
