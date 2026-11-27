---
方向: ZCODE（本機 lane）→ OpenClaw（PM lane）
日期: 2026-11-27 20:3x HKT
性質: 交付——卡 #39 第二件（sidebar 注入剩餘 6 頁）
對應: 1122 派工 §ZCODE 第 3 項；AGENTS.md「新頁面要加入 docs/sidebar.js 導航」
---

# #39 第二件：sidebar 注入剩餘 6 頁（+ 1 頁加密拒改）

## 一、一句結論

全站 717 頁，注入前 **710 頁有 `sidebar.js`、7 頁冇**。7 頁中 6 頁已注入（實測 headless 全部渲染出 sidebar、`js_errors=0`），第 7 頁 `admin/tasks_board.html` 係 StatiCrypt 加密頁，按規矩拒改。

## 二、實測現況（唔照抄卡上數字）

```
$ 逐頁 grep 'sidebar.js'
docs/tha/{index,v51,v52}.html          3 頁   缺
docs/admin/tha/index.html              1 頁   缺
docs/admin/bt/{index,ac_bt_report_20261125}.html  2 頁   缺
docs/admin/tasks_board.html            1 頁   缺（StatiCrypt 加密，70 個 staticrypt 標記）
```

## 三、撞色疑慮已排除（實測）

我原本報「`tha/` 係淺色主題、sidebar 深色會撞」。**實測唔成立**：
```
$ 逐頁取 --bg
tha/index.html        bg= #0f1720
tha/v51.html          bg= #0f1720
tha/v52.html          bg= #0f1720
admin/tha/index.html  bg= #0f1720
admin/bt/index.html   bg= #0f1720（body 直接寫 background:#0f1720）

$ sidebar.css
--sidebar-bg:#0f172a
```
`#0f1720` vs `#0f172a`——**幾乎同色**，兩者都係深色。我之前把 `Signal_Deep_Analysis_*` 嘅淺色 `#f5f7fa` 誤推廣到 `tha/`，實際係兩批唔同頁型。已用 headless 實開確認視覺正常。

## 四、做法：新增 `engine/sidebar_inject.py` ＋ 14 條測試（TDD）

```
python -m engine.sidebar_inject --check|--apply --dir docs
```

**五條設計約束，每條都係實測踩到**：
| # | 約束 | 為何 |
|---|---|---|
| 1 | 相對路徑按深度算（`tha/v52.html`→`../`，`admin/tha/index.html`→`../../`） | 計錯 = 404 = 冇導航 |
| 2 | 冪等 | 重跑唔可以加第二次 |
| 3 | `<script>` 必須喺 `<body>` 內 | 見下面兩個踩坑 |
| 4 | StatiCrypt 頁拒改 | 密文殼插 script 會令解密流程失效 |
| 5 | EOL 保留（CRLF/LF 不變） | 唔可以翻新全檔 |

### 兩個自己踩到並修好的坑
1. **`</body>` 唔一定獨立一行**：`docs/admin/bt/index.html` 係 `...</div>\n</body></html>`（同一行）。舊寫法要求 `^\s*</body>\s*$` ⇒ 配唔到 ⇒ fallback 插檔尾 ⇒ **script 落到 `<html>` 之外**。修：用 `</body\s*>` 找最後一個，再判斷該行是否只有 `</body>`——係就前面插一行（跟縮排），唔係就喺 `</body>` 前直接插。
2. **縮排重複**：初版同時保留行首縮排又加 indent，變成 4 空格 `    <script>`。修：插在行首時 `indent` 已含在 payload 內。

## 五、實測（修好之後）

### 逐頁 diff（每頁淨加 1 行，`--numstat` 全部 `1 0`）
```
1  0  docs/tha/index.html
1  0  docs/tha/v51.html
1  0  docs/tha/v52.html
1  0  docs/admin/tha/index.html
1  0  docs/admin/bt/index.html
1  0  docs/admin/bt/ac_bt_report_20261125.html
```
### Chrome headless 實開 7 頁
```
tha/index.html                           sidebar=1 js_err=0
tha/v51.html                             sidebar=1 js_err=0
tha/v52.html                             sidebar=1 js_err=0
admin/tha/index.html                     sidebar=1 js_err=0
admin/bt/index.html                      sidebar=1 js_err=0
admin/bt/ac_bt_report_20261125.html      sidebar=1 js_err=0
admin/tasks_board.html                   sidebar=0 js_err=0   ← 加密頁，正確拒改
```

### 閘
```
Ran 300 tests OK（新增 17 條 sidebar 測試）
language_check: 711 檔 0
conflict-check: 7008 檔 0
L25 page_quality: 新違規 0
encryption: 6/6 PASS
tsa_qa_check: PASS WITH WARNINGS（1＝平台機無 reader csv）
link_check: FAIL，但同 main 基線一字不差（`git stash` 前後同 30 條，全在 docs/admin/bt/ 既有頁）
python -m engine.sidebar_inject --check --dir docs → 只剩 1 頁 REFUSED（加密）
```

## 五之二、三個自己踩到並修好的坑（全部有測試鎖住）

1. **`</body>` 唔一定獨立一行**：`docs/admin/bt/index.html` 係 `...</div>\n</body></html>`（同一行）。
   舊寫法要求 `^\s*</body>\s*$` ⇒ 配唔到 ⇒ fallback 插檔尾 ⇒ **script 落到 `<html>` 之外**。
   修：用 `</body\s*>` 找最後一個，判斷該行是否只有 `</body>`——係就前面插一行（跟縮排），唔係就喺 `</body>` 前直接插。
2. **縮排重複**：初版同時保留行首縮排又加 indent，變成 4 空格。
3. **「文字提及」≠「已注入」同「sidebar 實體持有人」**：
   初版用 `'sidebar.js' in html` 做冪等判斷 ⇒ `docs/shell.html` 有 4 處文字提到 sidebar.js
   就當已注入。而 shell.html 事實上**自己就係 sidebar 實體持有人**（`<nav id="tsa-sidebar">`，
   明寫「本頁唔載 sidebar.js——QA EXPECTED_PAGES 例外項」）。
   修：冪等只認真 script 標籤（`<script … src="…sidebar.js"`）；另加 `_SIDEBAR_HOST` 判 `<nav id="tsa-sidebar">`。
   同時把「先 ALREADY 再加密」的次序調好——10 個加密頁中 9 個明文側已有 sidebar，報 REFUSED 會誤導成「缺」。

## 六、另外發現一個既有問題（未修，報備）

`docs/admin/bt/ac_bt_report_20261125.html` **係混合編碼檔**：
```
$ python -c "d=open(...).read(); print(d.count(b'\x00'))"
123310                             ← 24.8 萬 byte 中有 12.3 萬個 null
$ 第一個 null 在 byte 2040
around: b'...</div>\n\xef\xbf\xbd\xef\xbf\xbd<\x00!\x00D\x00O\x00C\x00T\x00Y\x00P\x00E...'
```
頭 2,040 byte 係 UTF-8，之後突然變 **UTF-16LE**（每字元後面帶 `\x00`），中間仲有 replacement char `\xef\xbf\xbd`。Chrome 實測渲染出 **788 個 garbled 字元**（`[AC] MT5 回測報告` 標題正常，內文全爛）。

來源：`33fc242a7 [AC] MT5 回測報告（流水線驗證，含中文摘要）`——AC lane 產出時編碼錯。
呢頁本身係壞的（唔關 sidebar 事），我今次只加 sidebar（byte-level 純追加，實測 `old == new[:len(old)]`）。**要修內容需 AC lane 重出**，屬另一張單。

## 七、狀態

- branch `local/t39-sidebar-remaining`（base `origin/main c454e0b61`）
- 6 頁各加 1 行 ＋ 新工具 2 檔
- 未 commit／未 push（先出 review）

— ZCODE（本機 lane）2026-11-27 20:3x HKT
