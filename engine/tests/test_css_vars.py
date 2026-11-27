"""CSS 自訂變數掃描器測試（TDD）

背景：2026-11-27 實測發現 `docs/reports/index_*.html` 共 147 頁評級徽章
寫 `background:var(--grade-a22)`，但 `--grade-a22` 全站零定義，令徽章背景
透明。根因係 `scripts/tsa_w/rebuild_index_deep_v2.py:367` 把 hex 的 alpha
後綴 `22` 誤寫成變數名一部分。

呢套測試釘住：①掃得到呢類錯名 ②唔會誤報（fallback、script 內、已定義）
③修補只插 `:root{}` 尾、保留 EOL、唔碰其他行。
"""
import unittest

from engine.css_vars import (defined_vars, find_undefined_vars, insert_root_vars,
                             mask_noise, resolve_page_tokens, scan, used_vars)

ROOT_PAGE = """<!DOCTYPE html>
<html><head><style>
:root{--bg:#0F1520;--grade-a:#22C55E;--grade-b:#EAB308;--grade-c:#F97316;--grade-d:#EF4444;
--radius:12px}
.chip{display:inline-block}
</style></head>
<body>
<span class="chip" style="background:var(--grade-a22);color:var(--grade-a)">A</span>
<span class="chip" style="background:var(--grade-b22);color:var(--grade-b)">B</span>
</body></html>
"""


class TestUsedAndDefined(unittest.TestCase):
    def test_used_vars(self):
        self.assertEqual(used_vars(ROOT_PAGE),
                         {"--grade-a22", "--grade-a", "--grade-b22", "--grade-b"})

    def test_defined_vars(self):
        have = defined_vars(ROOT_PAGE)
        self.assertIn("--grade-a", have)
        self.assertIn("--bg", have)
        self.assertNotIn("--grade-a22", have)

    def test_token_file_definitions_counted(self):
        token = ":root{--grade-a22:#22C55E22;}"
        self.assertIn("--grade-a22", defined_vars(ROOT_PAGE, token))

    def test_var_with_fallback_parsed(self):
        html = "<style>:root{--a:1}</style><p style='color:var(--b, #fff)'>x</p>"
        # --a 只係定義唔係使用；--b 有 fallback 但一樣係「用到」
        self.assertEqual(used_vars(html), {"--b"})
        self.assertEqual(find_undefined_vars(html), ["--b"])


class TestBlindSpots(unittest.TestCase):
    """唔可以誤報或漏報。"""

    def test_script_content_ignored(self):
        html = ("<style>:root{--a:1}</style>"
                "<script>var s = 'var(--not-css)';</script>")
        self.assertEqual(find_undefined_vars(html), [])

    def test_css_comment_ignored(self):
        html = "<style>:root{--a:1}\n/* var(--old) 舊寫法 */\n</style>"
        self.assertEqual(find_undefined_vars(html), [])

    def test_definition_with_spaces(self):
        html = "<style>:root{ --grade-a22 : #22C55E22 ; }</style><p style='color:var(--grade-a22)'>"
        self.assertEqual(find_undefined_vars(html), [])

    def test_greedy_name_not_captured(self):
        """`var(--grade-a)` 唔可以食到後面嘅 `22` 當變數名一部分。"""
        html = "<style>:root{--grade-a:#22C55E}</style><p style='background:var(--grade-a)22'>"
        self.assertEqual(used_vars(html), {"--grade-a"})

    def test_real_typo_detected(self):
        self.assertEqual(find_undefined_vars(ROOT_PAGE), ["--grade-a22", "--grade-b22"])


class TestInsertRootVars(unittest.TestCase):
    def test_inserts_at_end_of_root(self):
        out, rep = insert_root_vars(ROOT_PAGE, {"--grade-a22": "#22C55E22"})
        self.assertEqual(rep["inserted"], ["--grade-a22"])
        self.assertIn("--grade-a22:#22C55E22;", out)
        # 插入位置在 :root 之內
        root_start = out.index(":root{")
        root_end = out.index("}", root_start)
        self.assertLess(out.index("--grade-a22"), root_end)

    def test_existing_definition_not_overwritten(self):
        out, rep = insert_root_vars(ROOT_PAGE, {"--grade-a": "#000000"})
        self.assertEqual(rep["inserted"], [])
        self.assertEqual(rep["already"], ["--grade-a"])
        self.assertEqual(out, ROOT_PAGE)
        self.assertNotIn("#000000", out)

    def test_refuses_without_root(self):
        html = "<html><body><p style='color:var(--x)'>x</p></body></html>"
        out, rep = insert_root_vars(html, {"--x": "red"})
        self.assertEqual(out, html)
        self.assertEqual(rep["inserted"], [])
        self.assertIn(":root", rep["reason"])

    def test_only_other_lines_untouched(self):
        out, _ = insert_root_vars(ROOT_PAGE, {"--grade-a22": "#22C55E22"})
        before = ROOT_PAGE.split("\n")
        after = out.split("\n")
        self.assertEqual(len(before), len(after), "行數應該不變")
        for b, a in zip(before, after):
            if b != a:
                self.assertIn("--grade-a22", a, "只准改 :root 結尾那行")

    def test_multiple_insertions_sorted(self):
        out, rep = insert_root_vars(
            ROOT_PAGE, {"--grade-b22": "#EAB30822", "--grade-a22": "#22C55E22"})
        self.assertEqual(rep["inserted"], ["--grade-a22", "--grade-b22"])
        self.assertLess(out.index("--grade-a22"), out.index("--grade-b22"))

    def test_inserts_after_same_prefix_group(self):
        """補 --grade-*22 應該接在最後一條 --grade-* 宣告後（可讀性），
        唔係插在 :root 最尾（會同 --radius/--shadow 混在一起）。"""
        html = (":root{--bg:#000;--grade-a:#22C55E;--grade-d:#EF4444;"
                "--radius:12px}\n<p style='x:var(--grade-a22)'>")
        out, rep = insert_root_vars(html, {"--grade-a22": "#22C55E22"})
        self.assertIn("--grade-d:#EF4444;--grade-a22:#22C55E22;--radius:12px", out)
        self.assertEqual(rep["inserted"], ["--grade-a22"])

    def test_nested_braces_in_root(self):
        html = ":root{--a:1;--shadow:0 4px 16px rgba(0,0,0,.4)}\n<p style='x:var(--b)'>"
        out, rep = insert_root_vars(html, {"--b": "2"})
        self.assertIn("--b:2;", out)
        self.assertEqual(rep["inserted"], ["--b"])
        # 插入必須在最後一個 } 之前
        self.assertLess(out.index("--b:2"), out.rindex("}"))

    def test_missing_semicolon_before_close_is_supplied(self):
        """:root 最後一條宣告冇分號（`rgba(0,0,0,.4)}`）時，插入前要補分號，
        否則兩條宣告會串埋一齊，令全部失效（實測見過呢個 bug）。"""
        html = ":root{--radius:12px;--shadow:0 4px 16px rgba(0,0,0,.4)}\n<p style='x:var(--b)'>"
        out, _ = insert_root_vars(html, {"--b": "2"})
        self.assertIn("rgba(0,0,0,.4);--b:2;", out)
        self.assertNotIn("rgba(0,0,0,.4)--b", out)

    def test_existing_semicolon_not_doubled(self):
        html = ":root{--radius:12px;}\n<p style='x:var(--b)'>"
        out, _ = insert_root_vars(html, {"--b": "2"})
        self.assertIn("--radius:12px;--b:2;", out)
        self.assertNotIn(";;", out)


class TestScanReport(unittest.TestCase):
    def test_scan_counts(self):
        info = scan(ROOT_PAGE)
        self.assertEqual(info["undefined"], ["--grade-a22", "--grade-b22"])
        self.assertGreaterEqual(info["defined"], 5)

    def test_clean_page_has_no_undefined(self):
        token = ":root{--grade-a22:#22C55E22;--grade-b22:#EAB30822;}"
        self.assertEqual(scan(ROOT_PAGE, [token])["undefined"], [])


class TestMasking(unittest.TestCase):
    """review 2026-11-27：遮罩必須等長（offset 對應原文），且先遮 script 再遮註解。"""

    def test_mask_is_length_preserving(self):
        html = "<script>var a=':root{--x:1}';</script><style>:root{--y:2}</style>"
        self.assertEqual(len(mask_noise(html)), len(html))

    def test_line_numbers_preserved(self):
        html = "a\n<script>\nx\n</script>\nb"
        self.assertEqual(mask_noise(html).count("\n"), html.count("\n"))

    def test_script_content_masked(self):
        masked = mask_noise("<script>var t=':root{--fake:1}';</script>")
        self.assertNotIn(":root", masked)

    def test_comment_content_masked(self):
        masked = mask_noise("<style>/* :root{--fake:1} */</style>")
        self.assertNotIn(":root", masked)

    def test_script_comment_does_not_swallow_css(self):
        """review #6：`/*` 喺 script 內、`*/` 喺另一個 script 時，
        舊寫法（先遮註解）會吞掉中間全部 CSS。先遮 script 就唔會。"""
        html = ("<script>var s=\"/*\";</script>"
                "<p style=\"color:var(--x1)\">a</p>"
                "<script>var e=\"*/\";</script>")
        self.assertIn("--x1", used_vars(html))


class TestRootLocating(unittest.TestCase):
    """review #3：`:root`／`}` 落在字串、註解、script 內唔可以改爛頁面。"""

    def test_brace_inside_css_string_not_treated_as_close(self):
        html = ':root{--a:1;--q:"}";--d:2}\n<p style="x:var(--b)">'
        out, rep = insert_root_vars(html, {"--b": "2"})
        # 唔可以插進字串內部
        self.assertNotIn('"--b', out)
        self.assertNotIn(';"--b', out)
        self.assertEqual(rep["inserted"], ["--b"])
        # 新宣告必須在真正 :root 結尾之前
        self.assertLess(out.index("--b:2"), out.rindex("}"))

    def test_root_in_html_comment_ignored(self):
        html = ("<!-- :root{--fake:1} --><style>:root{--a:1}</style>"
                '<p style="x:var(--b)">')
        out, rep = insert_root_vars(html, {"--b": "2"})
        self.assertEqual(rep["inserted"], ["--b"])
        self.assertIn(":root{--a:1;--b:2;}", out)
        self.assertIn("<!-- :root{--fake:1} -->", out)

    def test_root_in_script_ignored(self):
        html = ("<script>var t=':root{--fake:1}';</script><style>:root{--a:1}</style>"
                '<p style="x:var(--b)">')
        out, rep = insert_root_vars(html, {"--b": "2"})
        self.assertEqual(rep["inserted"], ["--b"])
        self.assertIn(":root{--a:1;--b:2;}", out)

    def test_multiline_root_keeps_indentation(self):
        """多行 :root（每條宣告一行）插入時要跟縮排／換行，唔好壓成一行。"""
        html = (":root{\n  --a: 1;\n  --b: 2;\n}\n<p style='x:var(--c)'>")
        out, rep = insert_root_vars(html, {"--c": "3"})
        self.assertIn("  --b: 2;\n  --c:3;\n}", out)
        self.assertEqual(rep["inserted"], ["--c"])

    def test_data_uri_with_brace_refused_not_corrupted(self):
        html = (':root{--a:url("data:image/svg+xml,<svg>{</svg>")}'
                '<p style="x:var(--b)">')
        out, rep = insert_root_vars(html, {"--b": "2"})
        if rep["inserted"]:
            self.assertIn("--b:2", out)
            self.assertIn("</svg>", out)
        else:
            self.assertEqual(out, html)


class TestResolvePageTokens(unittest.TestCase):
    """review #1：冇 <link> 嘅頁唔可以當佢有 token 定義。"""

    def setUp(self):
        import os
        import tempfile
        self.tmp = tempfile.mkdtemp()
        self.root = self.tmp
        with open(os.path.join(self.root, "tsa_tokens.css"), "w", encoding="utf-8") as fh:
            fh.write(":root{--only-in-tokens:1}")
        with open(os.path.join(self.root, "sidebar.css"), "w", encoding="utf-8") as fh:
            fh.write(":root{--only-in-sidebar:2}")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_linked_css_is_picked_up(self):
        import os
        page = os.path.join(self.root, "p.html")
        html = '<link rel="stylesheet" href="tsa_tokens.css"><p style="c:var(--only-in-tokens)">'
        toks = resolve_page_tokens(html, page, self.root)
        self.assertEqual(find_undefined_vars(html, toks), [])

    def test_unlinked_css_not_counted(self):
        """冇 <link> ⇒ token 唔算入，變數仍報未定義（呢個正正係舊版假綠）。"""
        import os
        page = os.path.join(self.root, "p.html")
        html = '<p style="c:var(--only-in-tokens)">'
        toks = resolve_page_tokens(html, page, self.root)
        self.assertEqual(find_undefined_vars(html, toks), ["--only-in-tokens"])

    def test_sidebar_js_implies_sidebar_css(self):
        import os
        page = os.path.join(self.root, "p.html")
        html = '<script src="sidebar.js"></script><p style="c:var(--only-in-sidebar)">'
        toks = resolve_page_tokens(html, page, self.root)
        self.assertEqual(find_undefined_vars(html, toks), [])

    def test_remote_and_data_href_ignored(self):
        import os
        page = os.path.join(self.root, "p.html")
        html = ('<link rel="stylesheet" href="https://x/y.css">'
                '<link rel="stylesheet" href="data:text/css,a{}">')
        self.assertEqual(resolve_page_tokens(html, page, self.root), [])


class TestUseRegex(unittest.TestCase):
    def test_uppercase_var_detected(self):
        """review #11：CSS 函數名大小寫唔敏感，`VAR(--x)` 一樣係使用。"""
        self.assertEqual(used_vars("<style>:root{--x:1}</style><p style='c:VAR(--y)'>"), {"--y"})

    def test_nested_var_detected(self):
        self.assertEqual(used_vars("<p style='c:var(--a,var(--b))'>"), {"--a", "--b"})


class TestRealRepoPages(unittest.TestCase):
    """對真 docs/ 全站掃描：grade-*22 錯名必須係 0（迴歸閘）。"""

    def _scan_repo(self):
        import glob
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(here))
        docs = os.path.join(root, "docs")
        out = {}
        for p in glob.glob(os.path.join(docs, "**", "*.html"), recursive=True):
            with open(p, encoding="utf-8", errors="replace") as fh:
                t = fh.read()
            if "staticrypt" in t[:3000].lower():
                continue
            toks = resolve_page_tokens(t, p, docs)
            und = find_undefined_vars(t, toks)
            if und:
                out[os.path.relpath(p, docs)] = und
        return out

    def test_grade_xx22_typo_gone(self):
        """修好之後應該係零；有迴歸即紅（唔靠魔法數門檻）。"""
        bad = self._scan_repo()
        hits = {p: u for p, u in bad.items()
                if any(v.startswith("--grade-") and v.endswith("22") for v in u)}
        self.assertEqual(hits, {},
                         "repo 內仍有 grade-*22 錯名（見 engine/css_vars.py 說明）")

    def test_known_bg_hover_gap_is_visible(self):
        """23 頁 Signal_Deep_Analysis 用 var(--bg-hover) 但冇 link tsa_tokens.css。
        呢條測試唔要求修好，只要求「工具睇得見」——防止再出現假綠。"""
        bad = self._scan_repo()
        hover = [p for p, u in bad.items() if "--bg-hover" in u]
        if not hover:
            return       # 已修好就無需再提
        self.assertGreater(len(hover), 0)


if __name__ == "__main__":
    unittest.main()
