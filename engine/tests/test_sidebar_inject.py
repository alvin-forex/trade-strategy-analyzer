"""Sidebar 注入工具測試（TDD）

背景：#39 W4「全站 sidebar 零缺」。實測 7 頁缺 `sidebar.js`，其中 1 頁係
StatiCrypt 加密頁（唔可以插）。
"""
import os
import unittest

from engine.sidebar_inject import inject_sidebar, is_encrypted, relative_sidebar_path


class TestRelativePath(unittest.TestCase):
    def test_root_page(self):
        self.assertEqual(relative_sidebar_path("docs/x.html", "docs"), "sidebar.js")

    def test_one_level(self):
        self.assertEqual(relative_sidebar_path("docs/tha/v52.html", "docs"),
                         "../sidebar.js")

    def test_two_levels(self):
        self.assertEqual(relative_sidebar_path("docs/admin/tha/index.html", "docs"),
                         "../../sidebar.js")

    def test_uses_forward_slash_on_windows(self):
        p = relative_sidebar_path(os.path.join("docs", "admin", "bt", "index.html"), "docs")
        self.assertNotIn("\\", p)
        self.assertEqual(p, "../../sidebar.js")


class TestInject(unittest.TestCase):
    PAGE = "<html><body>\n<p>內容</p>\n</body>\n</html>\n"

    def test_inserts_before_body_close(self):
        out, rep = inject_sidebar(self.PAGE, "docs/tha/v52.html", "docs")
        self.assertEqual(rep["status"], "INSERTED")
        self.assertIn('<script src="../sidebar.js"></script>', out)
        self.assertLess(out.index("sidebar.js"), out.index("</body>"))

    def test_idempotent(self):
        once, _ = inject_sidebar(self.PAGE, "docs/tha/v52.html", "docs")
        twice, rep = inject_sidebar(once, "docs/tha/v52.html", "docs")
        self.assertEqual(once, twice)
        self.assertEqual(rep["status"], "ALREADY")

    def test_existing_sidebar_not_duplicated(self):
        src = self.PAGE.replace("</body>", '<script src="sidebar.js"></script>\n</body>')
        out, rep = inject_sidebar(src, "docs/x.html", "docs")
        self.assertEqual(out, src)
        self.assertEqual(rep["status"], "ALREADY")

    def test_text_mention_is_not_a_script_tag(self):
        """實測 docs/shell.html 有 4 處文字提到 sidebar.js 但冇 script 標籤，
        而佢本身就係 sidebar 實體持有人——文字提及唔算「已注入」。"""
        page = ("<html><body>\n<!-- 本頁唔載 sidebar.js -->\n"
                "<p>sidebar.js 係導航</p>\n</body></html>")
        out, rep = inject_sidebar(page, "docs/shell.html", "docs")
        self.assertEqual(rep["status"], "INSERTED")
        self.assertIn('<script src="sidebar.js"></script>', out)

    def test_encrypted_with_existing_sidebar_reports_already(self):
        """加密頁多數明文側已注入（實測 9/10）；唔應該報 REFUSED 令人以為缺。"""
        page = ('<html><head><script src="staticrypt/x.js"></script></head><body>'
                '<script src="sidebar.js"></script></body></html>')
        out, rep = inject_sidebar(page, "docs/index.html", "docs")
        self.assertEqual(out, page)
        self.assertEqual(rep["status"], "ALREADY")

    def test_sidebar_host_page_not_injected(self):
        """實測 docs/shell.html 自己就係 sidebar 實體持有人（<nav id="tsa-sidebar">），
        明寫「本頁唔載 sidebar.js」——唔可以幫佢加。"""
        page = ('<html><body>\n<nav class="shell-sidebar" id="tsa-sidebar">'
                '<div class="sidebar-links"></div></nav>\n</body></html>')
        out, rep = inject_sidebar(page, "docs/shell.html", "docs")
        self.assertEqual(out, page)
        self.assertEqual(rep["status"], "ALREADY")
        self.assertIn("實體持有人", rep["reason"])

    def test_other_lines_untouched(self):
        out, _ = inject_sidebar(self.PAGE, "docs/tha/v52.html", "docs")
        # 插入一行之後，把嗰行剷走應該逐 byte 等於原文
        stripped = "\n".join(
            line for line in out.split("\n") if "sidebar.js" not in line)
        self.assertEqual(stripped, self.PAGE)

    def test_no_body_close_appends_at_end(self):
        page = "<html><p>內容</p></html>"
        out, rep = inject_sidebar(page, "docs/x.html", "docs")
        self.assertEqual(rep["status"], "INSERTED")
        self.assertTrue(out.startswith(page))
        self.assertIn("sidebar.js", out)

    def test_encrypted_page_refused(self):
        page = ('<html><head><title>x</title></head><body>'
                '<script src="staticrypt/decrypt.js"></script></body></html>')
        self.assertTrue(is_encrypted(page))
        out, rep = inject_sidebar(page, "docs/index.html", "docs")
        self.assertEqual(out, page)
        self.assertEqual(rep["status"], "REFUSED")
        self.assertIn("加密", rep["reason"])

    def test_empty_refused(self):
        out, rep = inject_sidebar("", "docs/x.html", "docs")
        self.assertEqual(out, "")
        self.assertEqual(rep["status"], "REFUSED")

    def test_indentation_follows_body_close(self):
        page = "<html>\n<body>\n  <p>x</p>\n  </body>\n</html>"
        out, _ = inject_sidebar(page, "docs/x.html", "docs")
        self.assertIn('  <script src="sidebar.js"></script>\n  </body>', out)

    def test_body_close_sharing_line_still_inserted_inside_body(self):
        """實測 `docs/admin/bt/index.html` 係 `</body></html>` 同一行；
        舊寫法（要求 </body> 獨立一行）會改插檔尾，令 script 喺 <html> 之外。"""
        page = "<html><body><p>x</p></body></html>"
        out, rep = inject_sidebar(page, "docs/admin/bt/index.html", "docs")
        self.assertEqual(rep["status"], "INSERTED")
        self.assertIn('<script src="../../sidebar.js"></script>\n</body></html>', out)
        self.assertLess(out.index("sidebar.js"), out.index("</body>"))


class TestRealRepoPages(unittest.TestCase):
    """對真 docs/ 掃描：7 頁缺 sidebar，其中 1 頁加密。"""

    def _missing(self):
        import glob
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(here))
        docs = os.path.join(root, "docs")
        out = []
        for p in glob.glob(os.path.join(docs, "**", "*.html"), recursive=True):
            with open(p, encoding="utf-8", errors="replace") as fh:
                t = fh.read()
            if "sidebar.js" in t:
                continue
            out.append(os.path.relpath(p, root))
        return out

    def test_inject_is_idempotent_on_every_repo_page(self):
        """對全站每頁跑一次：已注入嘅要 ALREADY、未注入嘅要 INSERTED 且再跑 ALREADY。"""
        import glob
        here = os.path.dirname(os.path.abspath(__file__))
        root = os.path.dirname(os.path.dirname(here))
        docs = os.path.join(root, "docs")
        for p in glob.glob(os.path.join(docs, "**", "*.html"), recursive=True):
            with open(p, encoding="utf-8", errors="replace") as fh:
                t = fh.read()
            once, rep1 = inject_sidebar(t, p, docs)
            twice, rep2 = inject_sidebar(once, p, docs)
            self.assertEqual(once, twice, "{0} 唔冪等".format(p))
            if rep1["status"] == "INSERTED":
                self.assertEqual(rep2["status"], "ALREADY", p)
                self.assertEqual(once.count("sidebar.js"), t.count("sidebar.js") + 1, p)


if __name__ == "__main__":
    unittest.main()
