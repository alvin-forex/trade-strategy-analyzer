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


class TestStaticCssLink(unittest.TestCase):
    """review I-3：全站 710 頁有靜態 `<link sidebar.css>`，6 頁冇 ⇒ 慢網 FOUC。

    實測慢網（CSS 延遲 1.5s）時 `<nav class="sidebar">` 係 position:static、
    寬 1264px、透明底，壓在正文上，CSS 到才縮成 200px 側欄。
    """

    PAGE = ('<html>\n<head>\n<meta charset="utf-8">\n<title>x</title>\n</head>\n'
            '<body>\n<p>內容</p>\n</body>\n</html>\n')

    def test_static_link_added_before_head_close(self):
        out, rep = inject_sidebar(self.PAGE, "docs/tha/v52.html", "docs")
        self.assertIn('<link rel="stylesheet" href="../sidebar.css">', out)
        self.assertLess(out.index("sidebar.css"), out.index("</head>"))
        self.assertEqual(rep["style"], "../sidebar.css")

    def test_static_link_depth_matches_script(self):
        out, _ = inject_sidebar(self.PAGE, "docs/admin/tha/index.html", "docs")
        self.assertIn('<link rel="stylesheet" href="../../sidebar.css">', out)

    def test_existing_style_link_not_duplicated(self):
        """已有 CSS 但冇 script → 只補 script，CSS 唔可以插第二次。"""
        page = self.PAGE.replace(
            "</head>", '<link rel="stylesheet" href="../sidebar.css">\n</head>')
        out, rep = inject_sidebar(page, "docs/tha/v52.html", "docs")
        self.assertEqual(out.count("sidebar.css"), page.count("sidebar.css"))
        self.assertIn('<script src="../sidebar.js"></script>', out)
        self.assertLess(out.index("sidebar.js"), out.index("</body>"))

    def test_script_without_style_gets_style_added(self):
        """有 script 冇 CSS → 補 CSS（實測 6 頁正是如此）。"""
        page = self.PAGE.replace(
            "</body>", '<script src="../sidebar.js"></script>\n</body>')
        out, rep = inject_sidebar(page, "docs/tha/v52.html", "docs")
        self.assertIn('<link rel="stylesheet" href="../sidebar.css">', out)
        self.assertEqual(rep["status"], "INSERTED")
        self.assertIn("補靜態", rep["reason"])

    def test_no_head_does_not_inject_into_body(self):
        page = "<html><body><p>x</p><script src=\"sidebar.js\"></script></body></html>"
        out, rep = inject_sidebar(page, "docs/x.html", "docs")
        self.assertNotIn("sidebar.css\"", out.split("<body>")[1])

    def test_can_disable_static_css(self):
        out, rep = inject_sidebar(self.PAGE, "docs/tha/v52.html", "docs",
                                  add_static_css=False)
        self.assertNotIn("sidebar.css", out)


class TestCliExitCode(unittest.TestCase):
    """CLI 離開碼（review 2026-11-27 I-4）。

    舊版 `--apply` 用**注入前**的 report 計 `unexplained`，INSERTED 全部落入
    「仲有缺」⇒ 成功注入兩頁都 exit 1。實測臨時目錄兩頁 `applied=2` 但
    `unexplained` 兩頁齊、rc=1；再跑 `--check` 就 rc=0。離開碼必須反映
    **動作之後**的狀態，否則 pre-push 閘永遠紅，人就會開始無視佢。
    """

    PAGE = "<html>\n<head>\n<title>a</title>\n</head>\n<body>\n<p>x</p>\n</body>\n</html>\n"

    def _run(self, argv):
        import io
        import sys
        from engine.sidebar_inject import main
        buf, old = io.StringIO(), sys.stdout
        sys.stdout = buf
        try:
            rc = main(argv)
        finally:
            sys.stdout = old
        import json
        return rc, json.loads(buf.getvalue())

    def _tmp(self, files):
        import tempfile
        d = tempfile.mkdtemp()
        for name, body in files.items():
            p = os.path.join(d, name)
            parent = os.path.dirname(p)
            if parent != d and not os.path.isdir(parent):
                os.makedirs(parent)
            with open(p, "w", encoding="utf-8", newline="") as fh:
                fh.write(body)
        return d

    def test_apply_success_exits_zero(self):
        d = self._tmp({"a.html": self.PAGE, "sub/b.html": self.PAGE})
        rc, rep = self._run(["--apply", "--dir", d])
        self.assertEqual(rep["applied"], 2)
        self.assertEqual(rep["unexplained"], [])
        self.assertEqual(rc, 0)

    def test_apply_then_check_agrees(self):
        d = self._tmp({"a.html": self.PAGE})
        rc_apply, _ = self._run(["--apply", "--dir", d])
        rc_check, rep = self._run(["--check", "--dir", d])
        self.assertEqual((rc_apply, rc_check), (0, 0), rep)

    def test_check_on_missing_page_exits_one(self):
        d = self._tmp({"a.html": self.PAGE})
        rc, rep = self._run(["--check", "--dir", d])
        self.assertEqual(rc, 1)
        self.assertEqual(len(rep["unexplained"]), 1)

    def test_refused_not_in_whitelist_exits_one(self):
        """加密頁唔在白名單 ⇒ 真缺，要令閘紅。"""
        page = ('<html><head><script src="staticrypt/x.js"></script></head>'
                '<body>y</body></html>')
        d = self._tmp({"secret.html": page})
        rc, rep = self._run(["--check", "--dir", d])
        self.assertEqual(rc, 1)
        self.assertEqual(rep["refused"], 1)

    def test_known_refused_whitelist_exits_zero(self):
        """白名單係用 `endswith` 比對 repo 相對路徑；用真 docs 路徑名建檔驗一次。"""
        page = ('<html><head><script src="staticrypt/x.js"></script></head>'
                '<body>y</body></html>')
        d = self._tmp({"docs/admin/tasks_board.html": page})
        rc, rep = self._run(["--check", "--dir", os.path.join(d, "docs")])
        self.assertEqual(rep["refused"], 1)
        self.assertEqual(rep["unexplained"], [])
        self.assertEqual(rc, 0)


class TestRealRepoPages(unittest.TestCase):
    """對真 docs/ 掃描：全站冪等＋INSERTED 後必有真 script 標籤。"""

    def test_inject_is_idempotent_on_every_repo_page(self):
        """對全站每頁跑一次：兩次結果必須相同（冪等）。

        注意：唔可以用「sidebar.js 出現次數 +1」做斷言——補靜態 CSS 時只加
        `sidebar.css` 唔加 `sidebar.js`，而且 `sidebar.js` 呢個字串本來就可能
        出現喺註解／文字。用「兩次結果相同」＋「INSERTED 後仍有 script tag」驗。
        """
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
                self.assertRegex(once, r'<script[^>]*src="[^"]*sidebar\.js"', p)


if __name__ == "__main__":
    unittest.main()
