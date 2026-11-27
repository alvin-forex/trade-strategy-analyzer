"""W1 模板錨點轉換器測試（TDD）

規格來源：exchange/from_openclaw/20261127_1120_加急_W1剩餘頁今下午完成/
基準實作：exchange/from_zcode/20261127_0840_ZCODE_w_generator_patch_v1.1_indent修正/apply_generator_w1_patch.py
參考產物：commit 534074b6c（11-26 晚報後處理，2 details＋5 錨點零正文變）

鐵律：正文 byte 級零變——只准改 wrapper div 行、對應 </div> 行、h3 開標籤行、CSS 插入行。
"""
import unittest

from engine.w1_anchors import CSS_SNIPPET, SEC_IDS, apply_w1_anchors


PAGE_TMPL = """<html>
<head>
<style>
.news-section { background: #161b22; border-radius: 8px; padding: 12px; }
.news-item { font-size: 12px; }
.events-section { background: #161b22; border-radius: 8px; padding: 12px; }
.event-row { display: flex; }
</style>
</head>
<body>
<h1>報告</h1>
<div class="news-section">
<h3>📰 新聞摘要</h3>
<div class="news-item"><div>新聞一</div><div><span>美元利多</span></div></div>
<div class="news-item"><div>新聞二</div><div><span>黃金利空</span></div></div>
</div>
<div class="events-section">
<h3>📅 重要事件日程</h3>
<div class="event-row"><div class="event-time">20:30 ET</div></div>
</div>
<h3>📊 Charts</h3>
<div class="chart">圖表</div>
<h3>🔍 個別貨幣對分析</h3>
<div class="pair">貨幣對</div>
<h3>🔍 新聞 vs 技術 對比結論</h3>
<div class="concl">結論</div>
</body>
</html>
"""


class TestWrapperConversion(unittest.TestCase):
    def setUp(self):
        self.out, self.report = apply_w1_anchors(PAGE_TMPL)

    def test_news_wrapper_becomes_details(self):
        self.assertIn('<details class="card" id="sec-news" open>', self.out)
        self.assertNotIn('<div class="news-section">', self.out)

    def test_events_wrapper_becomes_details(self):
        self.assertIn('<details class="card" id="sec-events" open>', self.out)
        self.assertNotIn('<div class="events-section">', self.out)

    def test_css_rules_not_touched_by_wrapper_conversion(self):
        # CSS 選擇器係 .news-section {...}，唔係 <div class="news-section">，唔准被改
        self.assertIn('.news-section { background: #161b22', self.out)
        self.assertIn('.events-section { background: #161b22', self.out)

    def test_closing_div_matches_wrapper_depth(self):
        # news-section 有兩個 nested news-item div，收口必須取最外層
        news_start = self.out.index('id="sec-news"')
        news_end = self.out.index('</details>', news_start)
        seg = self.out[news_start:news_end]
        self.assertIn("新聞一", seg)
        self.assertIn("新聞二", seg)
        # events 段唔可以被吞入 news 段
        self.assertNotIn("重要事件日程", seg)

    def test_details_count_equals_wrappers(self):
        self.assertEqual(self.out.count("<details class=\"card\""), 2)
        self.assertEqual(self.out.count("</details>"), 2)


class TestHeadingAnchors(unittest.TestCase):
    def setUp(self):
        self.out, self.report = apply_w1_anchors(PAGE_TMPL)

    def test_charts_anchor(self):
        self.assertIn('<h3 id="sec-charts">📊 Charts</h3>', self.out)

    def test_pair_anchor(self):
        self.assertIn('<h3 id="sec-pair">🔍 個別貨幣對分析</h3>', self.out)

    def test_conclusion_anchor(self):
        self.assertIn('<h3 id="sec-conclusion">🔍 新聞 vs 技術 對比結論</h3>', self.out)

    def test_all_sec_ids_unique(self):
        for slug in SEC_IDS:
            self.assertLessEqual(self.out.count('id="{0}"'.format(slug)), 1,
                                 "{0} 重複".format(slug))

    def test_unknown_heading_untouched(self):
        self.assertIn("<h3>📰 新聞摘要</h3>", self.out)


class TestCssInsertion(unittest.TestCase):
    def test_css_inserted_after_news_section_rule(self):
        out, _ = apply_w1_anchors(PAGE_TMPL)
        self.assertIn(CSS_SNIPPET, out)
        # 插在 .news-section 規則之後
        self.assertLess(out.index('.news-section {'), out.index('details.card {'))

    def test_css_not_duplicated_when_already_present(self):
        once, _ = apply_w1_anchors(PAGE_TMPL)
        twice, rep = apply_w1_anchors(once)
        self.assertEqual(twice.count('details.card {'), 1)
        self.assertEqual(rep["css"], "ALREADY")

    def test_anchors_done_but_css_missing_is_reported_as_css_only(self):
        # 11-26 晚報：錨點由 generator 落齊，但 details.card 樣式冇落地
        once, _ = apply_w1_anchors(PAGE_TMPL)
        stripped = once.replace(CSS_SNIPPET + "\n", "")
        self.assertNotIn("details.card {", stripped)
        out, rep = apply_w1_anchors(stripped)
        self.assertEqual(rep["status"], "CSS_ONLY")
        self.assertIn("details.card {", out)
        self.assertEqual(rep["wrappers"], [])
        self.assertEqual(rep["headings"], [])


class TestBodyPreservation(unittest.TestCase):
    @staticmethod
    def _body_text(html):
        """</style> 之後的文字節點（CSS 全部排除；呢批頁面冇 <body> 標籤）。"""
        import re
        body = html.split("</style>", 1)[-1] if "</style>" in html else html
        return [t for t in re.findall(r">([^<>]+)<", body) if t.strip()]

    def test_body_text_byte_identical(self):
        out, _ = apply_w1_anchors(PAGE_TMPL)
        self.assertEqual(self._body_text(PAGE_TMPL), self._body_text(out))

    def test_no_line_added_or_removed_except_css(self):
        out, _ = apply_w1_anchors(PAGE_TMPL)
        before = PAGE_TMPL.split("\n")
        after = out.split("\n")
        # 容許 +2 行（CSS_SNIPPET 兩行），其餘行數一致
        self.assertEqual(len(after), len(before) + 2)

    def test_balanced_tags_preserved(self):
        out, _ = apply_w1_anchors(PAGE_TMPL)
        # 2 個 wrapper <div> 變 <details>，開合各自 -2 ⇒ div 仍然平衡
        self.assertEqual(out.count("<div"), out.count("</div>"))
        self.assertEqual(out.count("<details"), out.count("</details>"))
        self.assertEqual(out.count("<details"), 2)


class TestIdempotency(unittest.TestCase):
    def test_second_run_is_noop(self):
        once, r1 = apply_w1_anchors(PAGE_TMPL)
        twice, r2 = apply_w1_anchors(once)
        self.assertEqual(once, twice)
        self.assertEqual(r2["status"], "ALREADY")

    def test_already_converted_page_unchanged(self):
        once, _ = apply_w1_anchors(PAGE_TMPL)
        out, rep = apply_w1_anchors(once)
        self.assertEqual(out, once)
        self.assertEqual(rep["changed"], False)


class TestRefusals(unittest.TestCase):
    def test_no_news_wrapper_is_refused_not_silently_ok(self):
        src = PAGE_TMPL.replace('<div class="news-section">', '<div class="news-block">')
        out, rep = apply_w1_anchors(src)
        self.assertEqual(out, src)
        self.assertEqual(rep["changed"], False)
        self.assertIn("news", " ".join(rep["warnings"]))

    def test_unmatched_wrapper_kept_as_is(self):
        # 缺少 </div> 收口 → 唔准亂改，要照原樣留低並報警
        src = PAGE_TMPL.replace('</div>\n<div class="events-section">',
                                '\n<div class="events-section">', 1)
        out, rep = apply_w1_anchors(src)
        self.assertIn('<div class="news-section">', out)
        self.assertTrue(any("unmatched" in w.lower() for w in rep["warnings"]))

    def test_empty_string(self):
        out, rep = apply_w1_anchors("")
        self.assertEqual(out, "")
        self.assertEqual(rep["changed"], False)

    def test_report_lists_each_step(self):
        _, rep = apply_w1_anchors(PAGE_TMPL)
        for key in ("status", "changed", "wrappers", "headings", "css", "warnings"):
            self.assertIn(key, rep)


class TestRealPages(unittest.TestCase):
    """對真 docs/forex_reports 頁做轉換，驗正文零變（只跑存在嘅頁）。"""

    def _pages(self):
        import glob
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(here))
        return sorted(glob.glob(os.path.join(root, "docs", "forex_reports", "*.html")))

    def test_every_page_converges_and_is_idempotent(self):
        import re
        pages = self._pages()
        if not pages:
            self.skipTest("docs/forex_reports 唔存在")
        for p in pages:
            if p.endswith("index.html"):
                continue
            with open(p, encoding="utf-8") as fh:
                src = fh.read()
            out, rep = apply_w1_anchors(src)
            out2, rep2 = apply_w1_anchors(out)
            self.assertEqual(out, out2, "{0} 唔冪等".format(p))
            # 正文文字節點零變（</style> 之後，CSS 不在比較範圍）
            def body_text(h):
                tail = h.split("</style>", 1)[-1] if "</style>" in h else h
                return [t for t in re.findall(r">([^<>]+)<", tail) if t.strip()]
            self.assertEqual(body_text(src), body_text(out), "{0} 正文有變".format(p))

    def test_anchor_ids_unique_after_conversion(self):
        for p in self._pages():
            if p.endswith("index.html"):
                continue
            with open(p, encoding="utf-8") as fh:
                src = fh.read()
            out, _ = apply_w1_anchors(src)
            for slug in SEC_IDS + ("sec-news", "sec-events"):
                self.assertLessEqual(out.count('id="{0}"'.format(slug)), 1,
                                     "{0} 有重複 {1}".format(p, slug))


if __name__ == "__main__":
    unittest.main()
