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
- **20:44 已 commit／push，PR #75**

## 八、review 第二輪修正（23:xx，commit 待推）

第二輪 review 提 4 項，全部實測過才動手：

| # | 問題 | 實測 | 修法 |
|---|---|---|---|
| I-3 | 全站 710 頁有靜態 `<link sidebar.css>`，呢 6 頁冇 ⇒ 慢網 FOUC（`<nav class="sidebar">` 未樣式化時 1264px 寬透明底壓住正文） | `sidebar.js` 第 31-36 行才動態 append CSS | 注入時同步補 `<link>`；`<head>` 存在才補，5/6 頁成功 |
| I-2 | `--check` 把 REFUSED 一律當 OK ⇒ 全站仍缺一頁都報 0 | 臨時目錄驗 | 加 `KNOWN_REFUSED` 白名單，唔在名單的 REFUSED 令 exit 1 |
| I-4 | `--apply` 用**注入前** report 計 `unexplained` ⇒ 成功注入都 exit 1（實測兩頁 `applied=2`、`unexplained` 兩頁齊、rc=1） | 臨時目錄實跑 | 寫回後用新內容重跑一次 `inject_sidebar`，離開碼反映**動作之後**狀態 |
| M-3 | Windows cp1252 stdout 打中文會 crash | — | JSON 經 utf-8 bytes 過濾再寫 stdout |

新增 11 條測試（17→28），其中 `TestCliExitCode` 5 條專門鎖離開碼語義。

## 九、更正：`--numstat` 全部 `1 0` 呢句對 ac 頁**唔成立**

第三節寫「`--numstat` 全部 `1 0`」，**呢句錯**。`git diff --numstat` 對
`ac_bt_report_20261125.html` 出 `-  -`（git 判為 binary，因為檔中有 12.3 萬個
`\x00`），實際係 byte 級純追加，已用 python 直接驗：

```
HEAD~1 len 248659  HEAD len 248701
prefix_equal True
appended: b'\n<script src="../../sidebar.js"></script>\n'
old has sidebar.js: False | new: True
```

即 42 bytes 純追加、前 248,659 bytes 逐 byte 不變。**內容仍然係壞檔**（見第六節），
我只加 sidebar，冇修內容。

## 十、更正：「6 頁渲染 sidebar=1 js_err=0」唔代表 ac 頁視覺正常

第五節的 headless 表列出 ac 頁 `sidebar=1 js_err=0`——**呢個只證明 sidebar 本身
掛到、冇 JS 錯誤**，唔代表該頁可讀。實測同一份 DOM：

```
dom len 218828
FFFD（U+FFFD 替換字元）12911
C1 控制字元 51
```

原文係「頭 2,040 byte UTF-8 ＋之後 UTF-16LE」混合編碼（`\x00!\x00D\x00O\x00C…`
= `<!DOC…` 的 UTF-16LE 形式，被當 UTF-8 讀），Chrome 把整份「Strategy Tester
Report」內文渲染成 12,911 個替換字元。**要 AC 重出，屬另一張單。**

另外呢頁**冇 `<meta charset>`**（全站 715 頁有 sidebar script 的頁中唯一一頁），
本地 `python -m http.server`（`Content-Type: text/html` 無 charset）會令
連 sidebar 的中文標籤都變 `ðŸ&nbsp;` / `é¦–é&nbsp;`。實測加 `charset="utf-8"`
到 script 標籤有效；但**GitHub Pages 有宣告 `charset=utf-8`**
（`curl -sI` 實測 `Content-Type: text/html; charset=utf-8`），所以生產無事，
我冇改嗰行（避免同 AC 重出衝突）。

— ZCODE（本機 lane）2026-11-27 23:1x HKT
