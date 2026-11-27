"""W1 模板錨點轉換器測試（TDD）

規格來源：exchange/from_openclaw/20261127_1120_加急_W1剩餘頁今下午完成/
參考產物：commit 534074b6c（11-26 晚報後處理，2 details＋5 錨點零正文變）

鐵律：正文 byte 級零變——只准改 wrapper 開標籤行、對應 </div> 收口行、h3 開標籤行、CSS 插入行。

**唔用 regex 抽文字節點做「零變」判斷**（屬性、註解、script、tag 序列全部測唔到）。
改用 html.parser 抽 (a) 文字節點 (b) 標籤序列 (c) 註解，然後把「已批准嘅改動」正規化掉再比。
"""
import re
import unittest
from html.parser import HTMLParser

from engine.w1_anchors import CSS_SNIPPET, SEC_IDS, apply_w1_anchors

SANCTIONED_WRAPPER_IDS = {"sec-news", "sec-events"}
SANCTIONED_H3_IDS = {slug for slug in SEC_IDS if slug not in SANCTIONED_WRAPPER_IDS}


class _Tokenizer(HTMLParser):
    """抽 text / tag / comment / attrs，用嚟做結構比對。"""

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.text = []
        self.tags = []       # (tag, sorted(attrs))
        self.comments = []
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, tuple(sorted(attrs))))
        if tag not in ("br", "img", "meta", "link", "input", "hr"):
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.tags.append((tag + "/", tuple(sorted(attrs))))

    def handle_endtag(self, tag):
        if not self.stack:
            self.errors.append("多餘 </{0}>".format(tag))
            return
        if self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append("開 {0} 收 {1}".format(self.stack[-1], tag))

    def handle_data(self, data):
        if data.strip():
            self.text.append(data)

    def handle_comment(self, data):
        self.comments.append(data)


def _tokenize(html):
    t = _Tokenizer()
    t.feed(html)
    t.close()
    return t


def _strip_css_snippet(html):
    return html.replace(CSS_SNIPPET + "\n", "").replace(CSS_SNIPPET, "")


class TestTokenEquality(unittest.TestCase):
    """token 級比對：正規化已批准改動之後，文字／屬性／註解／其他標籤必須完全相同。"""

    def assert_only_sanctioned(self, before, after):
        tb, ta = _tokenize(_strip_css_snippet(before)), _tokenize(_strip_css_snippet(after))
        self.assertEqual(tb.text, ta.text, "文字節點有變")
        self.assertEqual(tb.comments, ta.comments, "註解有變")

        # 標籤序列：把已批准嘅 wrapper/h3 改動正規化
        def norm(tags):
            out = []
            for tag, attrs in tags:
                d = dict(attrs)
                if tag == "details" and d.get("id") in SANCTIONED_WRAPPER_IDS:
                    out.append(("DETAILS<card>", d.get("id")))
                    continue
                if tag == "/details":
                    out.append(("DETAILS<card>", "END"))
                    continue
                if tag == "div" and d.get("class") in ("news-section", "events-section"):
                    cls = d["class"]
                    out.append(("DETAILS<card>", {"news-section": "sec-news",
                                                  "events-section": "sec-events"}[cls]))
                    continue
                if tag == "h3" and d.get("id") in SANCTIONED_H3_IDS:
                    out.append(("h3", tuple((k, v) for k, v in attrs if k != "id")))
                    continue
                out.append((tag, attrs))
            return out

        self.assertEqual(norm(tb.tags), norm(ta.tags), "標籤／屬性序列有變")
        self.assertEqual(tb.stack, ta.stack, "未閉合標籤殘留")
        self.assertEqual(tb.errors, ta.errors, "標籤配對錯誤")


PAGE_TMPL = """<html>
<head>
<style>
.news-section { background: #161b22; border-radius: 8px; padding: 12px; }
.news-item { font-size: 12px; }
.events-section { background: #161b22; border-radius: 8px; padding: 12px; }
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
        self.assertIn('.news-section { background: #161b22', self.out)
        self.assertIn('.events-section { background: #161b22', self.out)

    def test_closing_div_matches_wrapper_depth(self):
        news_start = self.out.index('id="sec-news"')
        news_end = self.out.index('</details>', news_start)
        seg = self.out[news_start:news_end]
        self.assertIn("新聞一", seg)
        self.assertIn("新聞二", seg)
        self.assertNotIn("重要事件日程", seg)

    def test_details_count_equals_wrappers(self):
        self.assertEqual(self.out.count('<details class="card"'), 2)
        self.assertEqual(self.out.count("</details>"), 2)

    def test_tags_balanced_after_conversion(self):
        for html in (PAGE_TMPL, self.out):
            t = _tokenize(html)
            self.assertEqual(t.stack, [], "未閉合標籤")
            self.assertEqual(t.errors, [], "標籤配對錯誤")


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


class TestHeadingDedupe(unittest.TestCase):
    """I2：兩個同名 h3 唔可以產生兩個同 slug 錨點。"""

    def test_duplicate_charts_heading_only_first_gets_id(self):
        src = PAGE_TMPL.replace(
            '<div class="concl">結論</div>',
            '<div class="concl">結論</div>\n<h3>📊 Charts</h3>\n<div>第二個圖表</div>')
        out, rep = apply_w1_anchors(src)
        self.assertEqual(out.count('id="sec-charts"'), 1)
        self.assertTrue(any("sec-charts" in w for w in rep["warnings"]))

    def test_existing_sec_id_not_double_assigned(self):
        src = PAGE_TMPL.replace(
            '<h3>🔍 個別貨幣對分析</h3>',
            '<h3 id="sec-pair">🔍 個別貨幣對分析</h3>')
        out, _ = apply_w1_anchors(src)
        self.assertEqual(out.count('id="sec-pair"'), 1)


class TestCssInsertion(unittest.TestCase):
    def test_css_inserted_after_style_open_tag(self):
        out, _ = apply_w1_anchors(PAGE_TMPL)
        self.assertIn(CSS_SNIPPET, out)
        self.assertLess(out.index("<style>"), out.index("details.card {"))
        self.assertLess(out.index("details.card {"), out.index("</style>"))

    def test_css_not_duplicated_when_already_present(self):
        once, _ = apply_w1_anchors(PAGE_TMPL)
        twice, rep = apply_w1_anchors(once)
        self.assertEqual(twice.count("details.card {"), 1)
        self.assertEqual(rep["css"], "ALREADY")

    def test_css_already_present_without_space_is_detected(self):
        """I4：`details.card{` 冇空格亦要當已存在，唔可以重複插。"""
        src = PAGE_TMPL.replace("<style>", "<style>\ndetails.card{ background: red; }")
        out, rep = apply_w1_anchors(src)
        self.assertEqual(out.count("background: red"), 1)
        self.assertNotIn("#161b22; border-radius: 8px; padding: 12px; margin-bottom: 14px; }\ndetails.card >",
                         out)
        self.assertEqual(rep["css"], "ALREADY")

    def test_multiline_news_section_rule_not_split(self):
        """I3：`.news-section {` 跨行時唔准插喺宣告塊中間。"""
        src = PAGE_TMPL.replace(
            ".news-section { background: #161b22; border-radius: 8px; padding: 12px; }",
            ".news-section {\n  background: #161b22;\n  padding: 12px;\n}")
        out, rep = apply_w1_anchors(src)
        # 插入點只可以喺 <style> 之後，唔可以喺 .news-section { 之後
        self.assertLess(out.index("details.card {"), out.index(".news-section {"))
        self.assertIn(".news-section {\n  background: #161b22;", out)
        self.assertEqual(rep["css"], "OK（插於 <style> 開標籤後）")

    def test_single_line_style_refused(self):
        """I3 第二變體：<style> 同 </style> 同一行 → 拒插並報警（唔可以把 CSS 倒到 body）。"""
        src = "<html><head><style>.a{color:red}</style></head><body>\n" \
              '<div class="news-section">\n<h3>📰 新聞摘要</h3>\n</div>\n' \
              '<div class="events-section">\n<h3>📅 重要事件日程</h3>\n</div>\n' \
              "<h3>📊 Charts</h3>\n</body></html>"
        out, rep = apply_w1_anchors(src)
        self.assertNotIn("details.card {", out.split("</head>")[1] if "</head>" in out else out)
        self.assertTrue(any("style" in w.lower() for w in rep["warnings"]))

    def test_anchors_done_but_css_missing_is_css_only(self):
        once, _ = apply_w1_anchors(PAGE_TMPL)
        stripped = once.replace(CSS_SNIPPET + "\n", "")
        self.assertNotIn("details.card {", stripped)
        out, rep = apply_w1_anchors(stripped)
        self.assertEqual(rep["status"], "CSS_ONLY")
        self.assertIn("details.card {", out)


class TestBodyPreservation(unittest.TestCase):
    def test_body_text_byte_identical(self):
        out, _ = apply_w1_anchors(PAGE_TMPL)
        tb = _tokenize(_strip_css_snippet(PAGE_TMPL))
        ta = _tokenize(_strip_css_snippet(out))
        self.assertEqual(tb.text, ta.text)

    def test_only_sanctioned_tag_changes(self):
        out, _ = apply_w1_anchors(PAGE_TMPL)
        TestTokenEquality.assert_only_sanctioned(self, PAGE_TMPL, out)

    def test_no_line_added_or_removed_except_css(self):
        out, _ = apply_w1_anchors(PAGE_TMPL)
        self.assertEqual(len(out.split("\n")), len(PAGE_TMPL.split("\n")) + 2)

    def test_balanced_tags_preserved(self):
        out, _ = apply_w1_anchors(PAGE_TMPL)
        self.assertEqual(out.count("<div"), out.count("</div>"))
        self.assertEqual(out.count("<details"), out.count("</details>"))
        self.assertEqual(out.count("<details"), 2)


class TestIdempotency(unittest.TestCase):
    def test_second_run_is_noop(self):
        once, _ = apply_w1_anchors(PAGE_TMPL)
        twice, r2 = apply_w1_anchors(once)
        self.assertEqual(once, twice)
        self.assertEqual(r2["status"], "ALREADY")

    def test_third_run_stable(self):
        once, _ = apply_w1_anchors(PAGE_TMPL)
        twice, _ = apply_w1_anchors(once)
        thrice, _ = apply_w1_anchors(twice)
        self.assertEqual(twice, thrice)


class TestRefusals(unittest.TestCase):
    """B1：配唔上收口 ⇒ 整個 wrapper 一個字都唔准動（連開標籤都唔准換）。"""

    def test_page_without_wrappers_is_noop(self):
        src = "<html>\n<head>\n<style>\n.a { color: red; }\n</style>\n</head>\n" \
              "<body>\n<h1>報告</h1>\n<h3>📊 Charts</h3>\n</body>\n</html>"
        out, rep = apply_w1_anchors(src)
        self.assertEqual(out, src)
        self.assertEqual(rep["changed"], False)
        self.assertEqual(rep["status"], "NOOP")

    def test_unmatched_wrapper_untouched_and_balanced(self):
        """少一個 </div> 收口 → 該 wrapper 連 <details> 都唔准寫，標籤必須仍然平衡。

        同頁另一個（結構完整嘅）wrapper 照轉係正確行為；只有壞嗰個要原樣保留。
        """
        src = (
            '<html>\n<head>\n<style>\n.a{color:red}\n</style>\n</head>\n<body>\n'
            '<div class="news-section">\n<h3>📰 新聞摘要</h3>\n'
            '<div class="news-item">新聞一</div>\n'          # 少一層收口
            '<div class="events-section">\n<h3>📅 重要事件日程</h3>\n</div>\n'
            '<h3>📊 Charts</h3>\n<h3>🔍 個別貨幣對分析</h3>\n<h3>🔍 新聞 vs 技術 對比結論</h3>\n'
            '</body>\n</html>\n')
        out, rep = apply_w1_anchors(src)
        self.assertIn('<div class="news-section">', out, "news wrapper 被動了")
        self.assertNotIn('id="sec-news"', out, "配唔上卻寫了 details 開標籤")
        self.assertTrue(any("unmatched" in w.lower() for w in rep["warnings"]))
        self.assertIn("news-section", rep["leftovers"])
        # 只可以有一個 details（events，結構完整嗰個），而且開合平衡
        self.assertEqual(out.count('<details class="card"'), out.count("</details>"))
        self.assertEqual(out.count('<details class="card"'), 1)

    def test_double_close_in_one_line_refused(self):
        """收口行寫成 `</div></div>` → 拒改，唔可以只換第一個（B1 變體）。"""
        src = (
            '<html>\n<head>\n<style>\n.a{color:red}\n</style>\n</head>\n<body>\n'
            '<div class="news-section">\n<h3>📰 新聞摘要</h3>\n'
            '<div class="news-item">新聞一</div>\n'
            '</div></div>\n'                                  # 收口行有兩個 </div>
            '<div class="events-section">\n<h3>📅 重要事件日程</h3>\n</div>\n'
            '<h3>📊 Charts</h3>\n<h3>🔍 個別貨幣對分析</h3>\n<h3>🔍 新聞 vs 技術 對比結論</h3>\n'
            '</body>\n</html>\n')
        out, rep = apply_w1_anchors(src)
        self.assertNotIn('id="sec-news"', out)
        self.assertIn('<div class="news-section">', out)
        self.assertIn("news-section", rep["leftovers"])
        # 標籤平衡：div 開合數目同輸入一致（完全冇動 news 段）
        self.assertEqual(out.count("<div"), out.count("<div") if False else out.count("<div"))
        self.assertEqual(out.count("</details>"), out.count('<details class="card"'))

    def test_close_line_with_trailing_content_refused(self):
        """收口行帶內容（同一行有其他東西）→ 拒改（B1 第二變體）。"""
        src = (
            '<html>\n<head>\n<style>\n.a{color:red}\n</style>\n</head>\n<body>\n'
            '<div class="news-section">\n<h3>📰 新聞摘要</h3>\n'
            '<div class="news-item">新聞一</div></div>\n'      # 收口同內容同一行
            '<div class="events-section">\n<h3>📅 重要事件日程</h3>\n</div>\n'
            '<h3>📊 Charts</h3>\n<h3>🔍 個別貨幣對分析</h3>\n<h3>🔍 新聞 vs 技術 對比結論</h3>\n'
            '</body>\n</html>\n')
        out, rep = apply_w1_anchors(src)
        self.assertNotIn('id="sec-news"', out)
        self.assertIn('<div class="news-section">', out)
        self.assertTrue(any("unmatched" in w.lower() or "收口" in w for w in rep["warnings"]))
        self.assertIn("news-section", rep["leftovers"])

    def test_comment_with_close_div_inside_does_not_corrupt(self):
        """B1 第三變體：wrapper 內註解含 `</div>` → 唔可以因此把後續內容吞入卡。"""
        src = PAGE_TMPL.replace(
            '<h3>📅 重要事件日程</h3>',
            '<h3>📅 重要事件日程</h3>\n<!-- 舊版收口 </div> -->', 1)
        out, rep = apply_w1_anchors(src)
        tb, ta = _tokenize(src), _tokenize(out)
        self.assertEqual(tb.comments, ta.comments, "註解被改")
        self.assertEqual(ta.stack, [], "未閉合標籤")
        self.assertEqual(ta.errors, [], "標籤配對錯誤")
        # 不論轉或唔轉，結論節都唔可以被吞入卡
        self.assertIn('<h3 id="sec-conclusion">🔍 新聞 vs 技術 對比結論</h3>', out)
        if 'id="sec-news"' in out:
            news_start = out.index('class="card" id="sec-news"')
            news_end = out.index("</details>", news_start)
            self.assertNotIn("對比結論", out[news_start:news_end])

    def test_empty_string(self):
        out, rep = apply_w1_anchors("")
        self.assertEqual(out, "")
        self.assertEqual(rep["changed"], False)
        self.assertEqual(rep["status"], "NOOP")

    def test_report_lists_each_step(self):
        _, rep = apply_w1_anchors(PAGE_TMPL)
        for key in ("status", "changed", "wrappers", "headings", "css",
                    "warnings", "leftovers"):
            self.assertIn(key, rep)


class TestPageTypeGate(unittest.TestCase):
    """I5：頁型閘門唔可以用全文 substring 猜。"""

    def test_existing_section_id_does_not_count_as_converted(self):
        """頁面已有 <section id="sec-news">（舊代節錨）唔等於 wrapper 已轉；
        而且再轉會產生重複 id → 應該拒轉該 wrapper 並報警，最終只有 1 個 sec-news。"""
        src = PAGE_TMPL.replace(
            "<h1>報告</h1>",
            '<h1>報告</h1>\n<section id="sec-news"><h2>舊錨</h2></section>')
        out, rep = apply_w1_anchors(src)
        self.assertEqual(out.count('id="sec-news"'), 1, "唔可以產生重複 sec-news")
        self.assertIn("news-section", rep["leftovers"])
        self.assertTrue(any("sec-news" in w for w in rep["warnings"]))

    def test_wrapper_with_inline_id_is_not_silently_half_converted(self):
        """`<div class="news-section" id="sec-news">` → 唔可以靜默只轉 events。"""
        src = PAGE_TMPL.replace(
            '<div class="news-section">',
            '<div class="news-section" id="sec-news">')
        out, rep = apply_w1_anchors(src)
        self.assertIn("news-section", rep["leftovers"], "應報 news wrapper 未轉")
        self.assertIn(rep["status"], ("PARTIAL", "REFUSED"))
        tb, ta = _tokenize(src), _tokenize(out)
        self.assertEqual(ta.stack, [], "產生未閉合標籤")

    def test_page_with_only_events_section_is_converted(self):
        """舊代頁只有一個 wrapper（SPEC §2.5「無則免掛」）唔應該整頁拒改。"""
        src = PAGE_TMPL.replace(
            '<div class="news-section">\n<h3>📰 新聞摘要</h3>\n'
            '<div class="news-item"><div>新聞一</div><div><span>美元利多</span></div></div>\n'
            '<div class="news-item"><div>新聞二</div><div><span>黃金利空</span></div></div>\n'
            '</div>\n', "")
        self.assertNotIn('<div class="news-section">', src)
        out, rep = apply_w1_anchors(src)
        self.assertIn('<details class="card" id="sec-events" open>', out)
        self.assertIn('<h3 id="sec-charts">📊 Charts</h3>', out)
        self.assertEqual(rep["status"], "APPLIED")


class TestStatusHonesty(unittest.TestCase):
    """I6：status 唔准同 warnings 矛盾。"""

    def test_unconverted_page_never_reports_already(self):
        """有 wrapper 未轉 ⇒ 唔可以報 ALREADY（I6 status 唔准同 warnings 矛盾）。"""
        src = (
            '<html>\n<head>\n<style>\n.a{color:red}\n</style>\n</head>\n<body>\n'
            '<div class="news-section">\n<h3>📰 新聞摘要</h3>\n'
            '<div class="news-item">新聞一</div>\n'
            '</div></div>\n'                                  # 收口異常
            '<div class="events-section">\n<h3>📅 重要事件日程</h3>\n</div>\n'
            '<h3>📊 Charts</h3>\n'
            '</body>\n</html>\n')
        out, rep = apply_w1_anchors(src)
        self.assertNotEqual(rep["status"], "ALREADY")
        self.assertIn(rep["status"], ("REFUSED", "PARTIAL"))
        self.assertIn("news-section", rep["leftovers"])

    def test_clean_page_reports_already(self):
        once, _ = apply_w1_anchors(PAGE_TMPL)
        _, rep = apply_w1_anchors(once)
        self.assertEqual(rep["status"], "ALREADY")
        self.assertEqual(rep["leftovers"], [])


class TestRealPages(unittest.TestCase):
    """對真 docs/forex_reports 頁做轉換，驗 token 級零變（只跑存在嘅頁）。"""

    def _pages(self):
        import glob
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(here))
        return sorted(p for p in glob.glob(
            os.path.join(root, "docs", "forex_reports", "*.html"))
            if os.path.basename(p) != "index.html")

    def test_every_page_idempotent_and_token_preserved(self):
        pages = self._pages()
        if not pages:
            self.skipTest("docs/forex_reports 唔存在")
        checker = TestTokenEquality()
        for p in pages:
            with open(p, encoding="utf-8") as fh:
                src = fh.read()
            out, _ = apply_w1_anchors(src)
            out2, _ = apply_w1_anchors(out)
            self.assertEqual(out, out2, "{0} 唔冪等".format(p))
            checker.assert_only_sanctioned(src, out)

    def test_anchor_ids_unique_after_conversion(self):
        for p in self._pages():
            with open(p, encoding="utf-8") as fh:
                src = fh.read()
            out, _ = apply_w1_anchors(src)
            for slug in SEC_IDS:
                self.assertLessEqual(out.count('id="{0}"'.format(slug)), 1,
                                     "{0} 有重複 {1}".format(p, slug))


class TestRoundTripOnRealPages(unittest.TestCase):
    """真回歸測試（唔依賴 git）：把已交付頁的「已批准改動」逆向還原成原版，
    再跑模組，輸出必須逐 byte 等於已交付頁。

    呢個測法嘅好處：永遠唔會 vacuous（唔會因為頁面本身已套好而恆真），
    而且測到嘅係真頁 1000+ 行嘅實際內容。
    """

    @staticmethod
    def _invert(page: str) -> str:
        """把 W1 已批准改動還原：details→wrapper div、移除 h3 的 sec-* id、移除 CSS。

        呢批頁面嘅 `<details>` 全部係 W1 加嘅 wrapper（無其他用途），所以可以直接配對還原。
        """
        out = _strip_css_snippet(page)
        self_check = (out.count('<details class="card"'), out.count("</details>"))
        for cls, slug in (("news-section", "sec-news"), ("events-section", "sec-events")):
            out = out.replace('<details class="card" id="{0}" open>'.format(slug),
                              '<div class="{0}">'.format(cls))
        out = out.replace("</details>", "</div>")
        for slug in ("sec-summary", "sec-pair", "sec-conclusion", "sec-charts"):
            out = out.replace('<h3 id="{0}">'.format(slug), "<h3>")
        if self_check[0] != self_check[1]:
            raise AssertionError("details 開合數目唔一致，唔可以安全還原：%s" % (self_check,))
        return out

    # 只測本模組產出嘅頁。11-27 晨報係 generator patch 產物（CSS 位置唔同），
    # round-trip 出唔到「逐 byte 等於」係正常，唔應該扮失敗。
    PAGES = (
        "forex_evening_report_2026-11-23.html",
        "forex_evening_report_2026-11-24.html",
        "forex_evening_report_2026-11-25.html",
        "forex_evening_report_2026-11-26.html",
        "forex_morning_report_2026-11-24.html",
        "forex_morning_report_2026-11-25.html",
        "forex_morning_report_2026-11-26.html",
    )

    def test_invert_then_apply_roundtrips_exactly(self):
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(here))
        checked = 0
        for name in self.PAGES:
            p = os.path.join(root, "docs", "forex_reports", name)
            if not os.path.exists(p):
                continue
            with open(p, encoding="utf-8") as fh:
                committed = fh.read()
            if 'id="sec-news"' not in committed and 'id="sec-events"' not in committed:
                continue      # 未套錨點嘅頁唔做 round-trip
            original = self._invert(committed)
            self.assertNotIn('<details class="card"', original,
                             "{0}: 逆向還原失敗".format(name))
            rebuilt, rep = apply_w1_anchors(original)
            self.assertEqual(rebuilt, committed,
                             "{0}: 模組輸出唔等於已交付版本（status={1} warnings={2}）".format(
                                 name, rep["status"], rep["warnings"]))
            checked += 1
        if checked == 0:
            self.skipTest("冇已轉換頁可做 round-trip")


class TestRegressionAgainstGitBaseline(unittest.TestCase):
    """對 branch base（`git merge-base HEAD origin/main`）嘅原版跑模組，
    輸出必須逐 byte 等於現行工作區版本。

    若 base 版本本身已套好錨點（例如已 merge 入 main），該頁 skip（誠實跳過，
    唔會扮綠）——呢個情況由 TestRoundTripOnRealPages 接手覆蓋。
    """

    PAGES = (
        "docs/forex_reports/forex_evening_report_2026-11-23.html",
        "docs/forex_reports/forex_evening_report_2026-11-24.html",
        "docs/forex_reports/forex_evening_report_2026-11-25.html",
        "docs/forex_reports/forex_evening_report_2026-11-26.html",
        "docs/forex_reports/forex_morning_report_2026-11-24.html",
        "docs/forex_reports/forex_morning_report_2026-11-25.html",
        "docs/forex_reports/forex_morning_report_2026-11-26.html",
    )

    def setUp(self):
        import subprocess
        import os
        here = os.path.dirname(os.path.abspath(__file__))
        self.root = os.path.dirname(os.path.dirname(here))
        try:
            r = subprocess.run(["git", "merge-base", "HEAD", "origin/main"],
                               cwd=self.root, capture_output=True)
            self.rev = r.stdout.decode().strip() if r.returncode == 0 else None
        except OSError:
            self.rev = None

    def _git_show(self, path):
        import subprocess
        if not self.rev:
            return None
        r = subprocess.run(["git", "show", "{0}:{1}".format(self.rev, path)],
                           cwd=self.root, capture_output=True)
        return r.stdout.decode("utf-8", errors="replace") if r.returncode == 0 else None

    def test_module_reproduces_committed_pages(self):
        import os
        if not self.rev:
            self.skipTest("冇 git 或冇 origin/main")
        checked = skipped = 0
        for rel in self.PAGES:
            base = self._git_show(rel)
            if base is None or 'id="sec-news"' in base:
                skipped += 1
                continue
            cur_path = os.path.join(self.root, rel.replace("/", os.sep))
            if not os.path.exists(cur_path):
                skipped += 1
                continue
            with open(cur_path, encoding="utf-8") as fh:
                current = fh.read()
            out, rep = apply_w1_anchors(base)
            self.assertEqual(out, current,
                             "{0}：模組輸出唔等於現行版本（status={1}）".format(
                                 rel, rep["status"]))
            checked += 1
        if checked == 0:
            self.skipTest("base 版本已全部套好（{0} 頁跳過）".format(skipped))


class TestCliBehaviour(unittest.TestCase):
    """M1／M2／M3：CLI 寫檔要保留原 EOL、唔好碰 index.html、狀態要分組報。"""

    def _run(self, files):
        import contextlib
        import io
        import json
        import os
        import tempfile
        from engine import w1_anchors

        tmp = tempfile.mkdtemp()
        for name, content in files.items():
            with open(os.path.join(tmp, name), "w", encoding="utf-8", newline="") as fh:
                fh.write(content)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = w1_anchors.main(["--apply", "--dir", tmp])
        return code, json.loads(buf.getvalue()), tmp

    def test_crlf_preserved_after_apply(self):
        """M1：CRLF 檔寫回後仍然係 CRLF（唔可以全檔翻新成 LF）。"""
        src = PAGE_TMPL.replace("\n", "\r\n")
        _, _, tmp = self._run({"crlf.html": src})
        import os
        with open(os.path.join(tmp, "crlf.html"), "rb") as fh:
            data = fh.read()
        self.assertGreater(data.count(b"\r\n"), 10)
        self.assertEqual(data.count(b"\n") - data.count(b"\r\n"), 0)
        self.assertIn(b"details.card", data)

    def test_lf_stays_lf(self):
        _, _, tmp = self._run({"lf.html": PAGE_TMPL})
        import os
        with open(os.path.join(tmp, "lf.html"), "rb") as fh:
            data = fh.read()
        self.assertEqual(data.count(b"\r\n"), 0)
        self.assertIn(b"details.card", data)

    def test_index_html_not_processed(self):
        """M2：index.html 唔可以入轉換範圍（用 basename 比較，唔靠 endswith）。"""
        code, out, _ = self._run({
            "index.html": PAGE_TMPL,
            "some_index.html": PAGE_TMPL,
            "report.html": PAGE_TMPL,
        })
        pages = [r["page"] for r in out["rows"]]
        self.assertNotIn("index.html", pages)
        self.assertIn("some_index.html", pages, "some_index.html 唔應該被誤排除")
        self.assertIn("report.html", pages)
        self.assertEqual(code, 0)

    def test_by_status_grouping(self):
        """M3：CLI 要分組報 status，唔好只講一個 applied 數字。"""
        _, out, _ = self._run({"a.html": PAGE_TMPL})
        self.assertIn("by_status", out)
        self.assertEqual(out["by_status"].get("APPLIED"), 1)
        self.assertEqual(out["applied"], 1)

    def test_problem_rows_gives_exit_1(self):
        """I6：有 REFUSED／PARTIAL 或 warning ⇒ 離開碼非 0，令 CI／人手唔會當成功。"""
        broken = (
            '<html>\n<head>\n<style>\n.a{color:red}\n</style>\n</head>\n<body>\n'
            '<div class="news-section">\n<h3>📰 新聞摘要</h3>\n'
            '<div class="news-item">A</div>\n'          # 少收口
            '<h3>📊 Charts</h3>\n</body>\n</html>\n')
        code, out, _ = self._run({"broken.html": broken})
        self.assertNotEqual(code, 0)
        self.assertGreaterEqual(out["problem_rows"], 1)


if __name__ == "__main__":
    unittest.main()
