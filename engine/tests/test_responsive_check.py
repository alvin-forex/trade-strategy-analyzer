"""響應式檢查工具測試（TDD）

背景（2026-11-27 深夜）：卡 #39 (c) 技術要求寫「響應式：375px 單欄、無橫向滾動」，
但全站從來冇量過。我用一次性腳本實測 707 頁，**146 頁（20.7%）375px 有橫向溢出**，
其中 144 頁係元素真跑出容器外（唔止表格可橫掃）。呢個工具把量測固定落嚟。

設計教訓（我實測踩到，唔係假設）：
  1. **空輸出 ≠ 零問題**：60 個 probe chunk 有一個（`_pb_13`）整份 DOM 冇 marker，
     而我第一次聚合時只印總數（707/719）冇察覺，差啲當成「全站都測過」。
     ⇒ `parse_result` 必須分開「冇 marker」同「有 marker 但結果係空 list」。
  2. **溢出要分「容器內」同「容器外」**：`ccy/EURUSD.html` 的 811px 表係塞喺
     `overflow-x:auto` 的 div 內（視覺正常可橫掃），但同頁 `div.tab` 跑到 412px
     係真溢出。只睇 `documentElement.scrollWidth` 會分唔開兩種。
  3. **頁族要用檔名歸一化**：`detailed_comparison_all_levels_10344.html` 同
     `..._10437.html` 係同一模板，逐頁列出來冇用。
"""
import json
import unittest

from engine.responsive_check import (
    build_probe_html,
    parse_result,
    split_chunks,
    summarise,
)


class TestBuildProbe(unittest.TestCase):
    def test_embeds_pages_and_width(self):
        html = build_probe_html(["a.html", "sub/b.html"], width=375)
        self.assertIn("a.html", html)
        self.assertIn("sub/b.html", html)
        self.assertIn("375", html)

    def test_pages_are_json_escaped(self):
        """檔名可能有引號／反斜線，唔可以直接拼入 JS 字串。"""
        html = build_probe_html(['we"ird.html', "back\\slash.html"], width=375)
        self.assertIn('we\\"ird.html', html)
        self.assertIn("back\\\\slash.html", html)

    def test_probe_reports_outside_scroller_count(self):
        """探針本身要計「唔喺 scroll 容器內」的元素數，否則分唔開兩種溢出。"""
        html = build_probe_html(["a.html"], width=375)
        self.assertIn("overflowX", html)
        self.assertIn("outsideScroller", html)

    def test_page_prefix_is_applied(self):
        """`--dir docs/ccy` 要用 `/ccy/` 前綴；默認 `/` 會令所有頁 404。

        實測：忘了傳前綴時 35 頁全部報「零溢出」，其實全部係 404 空殼。
        """
        html = build_probe_html(["EURUSD.html"], width=375, prefix="/ccy/")
        self.assertIn('"/ccy/"', html)
        self.assertIn("f.src=PRE+p", html)

    def test_default_prefix_is_root(self):
        html = build_probe_html(["a.html"], width=375)
        self.assertIn('"/"', html)

    def test_probe_reports_body_text_length(self):
        """要回報 txt／title，否則分唔開「真量到」同「載入 404 空殼」。"""
        html = build_probe_html(["a.html"], width=375)
        self.assertIn("txt:", html)
        self.assertIn("title:", html)


class TestSuspiciousPages(unittest.TestCase):
    """`summarise` 要把「載入空殼」的頁剔出 measured，唔可以當零溢出。"""

    def test_short_text_page_is_suspicious_not_measured(self):
        rows = [
            {"p": "real.html", "sw": 500, "cw": 360, "outsideScroller": 5, "txt": 5000},
            {"p": "ghost.html", "sw": 300, "cw": 360, "outsideScroller": 0, "txt": 40},
        ]
        s = summarise(rows)
        self.assertEqual(s["measured"], 1)
        self.assertEqual(s["suspicious"], ["ghost.html"])

    def test_error_row_is_suspicious(self):
        rows = [{"p": "err.html", "err": "load-fail"}]
        s = summarise(rows)
        self.assertEqual(s["measured"], 0)
        self.assertEqual(s["suspicious"], ["err.html"])

    def test_rows_without_txt_are_counted(self):
        """舊格式 rows（無 txt）要保持可算，唔可以全部變 suspicious。"""
        rows = [{"p": "a.html", "sw": 500, "cw": 360, "outsideScroller": 3}]
        s = summarise(rows)
        self.assertEqual(s["measured"], 1)
        self.assertEqual(s["real"], 1)


class TestParseResult(unittest.TestCase):
    def test_parses_marker(self):
        dom = ('<html><body><div id="o">RESULT [{"p":"a.html","sw":456,"cw":360,'
               '"outsideScroller":3}]</div></body></html>')
        self.assertEqual(parse_result(dom),
                         [{"p": "a.html", "sw": 456, "cw": 360, "outsideScroller": 3}])

    def test_missing_marker_returns_none_not_empty_list(self):
        """實測 `_pb_13` 整份 DOM 冇 marker。回 [] 會令「冇測到」扮成「零問題」。"""
        self.assertIsNone(parse_result("<html><body>pending</body></html>"))

    def test_marker_with_empty_list_is_empty_list(self):
        self.assertEqual(parse_result('<div>RESULT []</div>'), [])

    def test_broken_json_returns_none(self):
        self.assertIsNone(parse_result('<div>RESULT [{"p":</div>'))


class TestSplitChunks(unittest.TestCase):
    def test_covers_every_item_exactly_once(self):
        items = ["p%d" % i for i in range(25)]
        chunks = split_chunks(items, 7)
        flat = [x for c in chunks for x in c]
        self.assertEqual(sorted(flat), sorted(items))
        self.assertEqual(len(flat), 25)
        self.assertTrue(all(len(c) <= 7 for c in chunks))

    def test_empty_input(self):
        self.assertEqual(split_chunks([], 5), [])


class TestSummarise(unittest.TestCase):
    def _row(self, page, sw, cw, out):
        return {"p": page, "sw": sw, "cw": cw, "outsideScroller": out}

    def test_counts_overflow_and_contained(self):
        rows = [
            self._row("ok.html", 360, 360, 0),
            self._row("wide_table_in_scroller.html", 800, 360, 0),   # 溢出但全在容器內
            self._row("real.html", 500, 360, 12),                   # 真溢出
        ]
        s = summarise(rows)
        self.assertEqual(s["measured"], 3)
        self.assertEqual(s["overflow"], 2)
        self.assertEqual(s["contained"], 1)
        self.assertEqual(s["real"], 1)
        self.assertEqual(s["real_pages"], ["real.html"])

    def test_family_aggregation_merges_numbered_pages(self):
        rows = [
            self._row("detailed_comparison_all_levels_10344.html", 648, 360, 13),
            self._row("detailed_comparison_all_levels_10437.html", 712, 360, 177),
            self._row("detailed_comparison_all_levels_10581.html", 360, 360, 0),
        ]
        s = summarise(rows)
        self.assertEqual(s["families"]["detailed_comparison_all_levels"],
                         {"measured": 3, "overflow": 2})

    def test_family_keeps_directory_for_nested(self):
        rows = [
            self._row("reports/Signal_Deep_Analysis_10344.html", 456, 360, 46),
            self._row("reports/Signal_Deep_Analysis_10843.html", 456, 360, 46),
        ]
        s = summarise(rows)
        self.assertEqual(s["families"]["reports/Signal_Deep_Analysis"],
                         {"measured": 2, "overflow": 2})

    def test_overflow_ratio(self):
        rows = [self._row("a.html", 400, 360, 1)] + [
            self._row("ok%d.html" % i, 360, 360, 0) for i in range(3)]
        s = summarise(rows)
        self.assertAlmostEqual(s["overflow_ratio"], 0.25)

    def test_empty_rows(self):
        s = summarise([])
        self.assertEqual(s["measured"], 0)
        self.assertEqual(s["overflow_ratio"], 0.0)


if __name__ == "__main__":
    unittest.main()


class TestPagePrefixGuard(unittest.TestCase):
    """實測陷阱：Git Bash 把 `/ccy/` 轉成 `C:/Program Files/Git/ccy/`。

    後果唔係報錯，而係 iframe 全部 404 ⇒ 量到 34 字元空殼 ⇒ 總結報「0 頁溢出」。
    呢個係最惡的假綠（工具本身「成功」但數值全錯），必須在 CLI 入口攔。
    """

    def test_accepts_root(self):
        from engine.responsive_check import is_plausible_page_prefix
        self.assertTrue(is_plausible_page_prefix("/"))

    def test_accepts_nested(self):
        from engine.responsive_check import is_plausible_page_prefix
        self.assertTrue(is_plausible_page_prefix("/ccy/"))

    def test_rejects_msys_mangled_drive_path(self):
        from engine.responsive_check import is_plausible_page_prefix
        self.assertFalse(
            is_plausible_page_prefix("C:/Program Files/Git/ccy/"))

    def test_rejects_empty(self):
        from engine.responsive_check import is_plausible_page_prefix
        self.assertFalse(is_plausible_page_prefix(""))

    def test_cli_exits_2_on_mangled_prefix(self):
        import io
        import sys
        from engine.responsive_check import main
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            rc = main(["--dir", "docs", "--outdir", "docs",
                       "--page-prefix", "C:/Program Files/Git/ccy/"])
        finally:
            sys.stdout = old
        self.assertEqual(rc, 2)
        self.assertIn("page-prefix", buf.getvalue())


class TestGhostDetection(unittest.TestCase):
    """薄頁 vs 404 空殼：唔可以一刀切用字元數（實測踩到）。"""

    def test_404_title_is_ghost(self):
        from engine.responsive_check import looks_like_ghost
        self.assertTrue(looks_like_ghost(
            {"p": "x.html", "sw": 300, "cw": 360, "txt": 34,
             "title": "404 Not Found"}))

    def test_thin_page_with_real_title_is_not_ghost(self):
        """`reports/index_5117.html` txt=96 但 title 正常 ⇒ 真薄頁，要計入。"""
        from engine.responsive_check import looks_like_ghost
        self.assertFalse(looks_like_ghost(
            {"p": "x.html", "sw": 375, "cw": 375, "txt": 96,
             "title": "Signal 5117 — Trade Strategy Analysis Report"}))

    def test_short_text_no_title_is_ghost(self):
        from engine.responsive_check import looks_like_ghost
        self.assertTrue(looks_like_ghost(
            {"p": "x.html", "sw": 300, "cw": 360, "txt": 40, "title": ""}))

    def test_err_is_ghost(self):
        from engine.responsive_check import looks_like_ghost
        self.assertTrue(looks_like_ghost({"p": "x.html", "err": "load-fail"}))


class TestPythonHttpServerGhost(unittest.TestCase):
    """Python `http.server` 的 404 頁 `title="Error response"`，冇「404」二字。

    實測：`--dir docs/ccy` 忘了傳 `--page-prefix` 時，iframe 全部載入
    `Error response` 頁（`txt≈180`、`title="Error response"`），工具報
    「36 頁、零溢出」——呢個係最迷惑的假綠，因為數字睇落完全正常。
    """

    def test_error_response_title_is_ghost(self):
        from engine.responsive_check import looks_like_ghost
        self.assertTrue(looks_like_ghost(
            {"p": "x.html", "sw": 360, "cw": 360, "txt": 180,
             "title": "Error response"}))

    def test_summarise_excludes_error_response_from_measured(self):
        from engine.responsive_check import summarise
        rows = [
            {"p": "ghost1.html", "sw": 360, "cw": 360, "txt": 180,
             "title": "Error response", "outsideScroller": 0},
            {"p": "ghost2.html", "sw": 300, "cw": 360, "txt": 34,
             "title": "404 Not Found", "outsideScroller": 0},
            {"p": "real.html", "sw": 480, "cw": 360, "txt": 4000,
             "title": "真頁", "outsideScroller": 7},
        ]
        s = summarise(rows)
        self.assertEqual(s["measured"], 1)
        self.assertEqual(s["real"], 1)
        self.assertEqual(sorted(s["suspicious"]), ["ghost1.html", "ghost2.html"])
