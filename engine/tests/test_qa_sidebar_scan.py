"""驗 `scripts/tsa_qa_check.py` 的 sidebar 檢查真係掃全站（TDD）

背景（2026-11-27）：卡 #39 第二件之前，全站實際有 **7 頁**缺 `sidebar.js`，
但 `tsa_qa_check.py` 的 `check_sidebar_consistency()` 只查 `EXPECTED_PAGES`
（5 個 root 頁）＋`SUBDIR_PAGES`（1 頁）＝**6 頁硬編碼清單**，其餘 710 頁
一頁都冇驗。所以「全站 sidebar 零缺」呢個講法一直冇機器證據，靠人手 grep。

本檔鎖住三件事：
  1. 全站每頁都要被判（有 `sidebar.js` / 加密 / 設計上 standalone / sidebar 實體持有人 / 真缺）
  2. 真缺要出 `❌`（blocker，唔係 warning）
  3. `docs/shell.html` 呢類 sidebar 實體持有人唔可以報缺
"""
import importlib.util
import os
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_HERE))
_QA_PATH = os.path.join(_ROOT, "scripts", "tsa_qa_check.py")


def _load_qa():
    spec = importlib.util.spec_from_file_location("tsa_qa_check_under_test", _QA_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


GOOD = ('<html><head><link rel="stylesheet" href="sidebar.css"></head>'
        '<body><p>x</p><script src="sidebar.js"></script></body></html>')


def _page(js=True, css=True, extra=""):
    head = '<link rel="stylesheet" href="sidebar.css">' if css else ""
    tail = '<script src="sidebar.js"></script>' if js else ""
    return ("<html><head>" + head + "</head><body>" + extra +
            "<p>x</p>" + tail + "</body></html>")


class TestFullSiteSidebarScan(unittest.TestCase):
    def setUp(self):
        self.qa = _load_qa()
        self.tmp = tempfile.mkdtemp()

    def _write(self, rel, body):
        p = os.path.join(self.tmp, rel)
        parent = os.path.dirname(p)
        if parent and not os.path.isdir(parent):
            os.makedirs(parent)
        with open(p, "w", encoding="utf-8", newline="") as fh:
            fh.write(body)
        return p

    def _scan(self):
        self.qa.TSA_DIR = self.tmp
        return self.qa.check_sidebar_consistency()

    def test_deep_nested_page_without_sidebar_is_blocker(self):
        """舊版只查 6 頁硬編碼 ⇒ `tha/v52.html` 這種深層頁一頁都冇驗。"""
        self._write("tha/v52.html", _page(js=False, css=False))
        issues = self._scan()
        joined = "\n".join(issues)
        self.assertIn("tha/v52.html", joined)
        self.assertTrue(any(i.startswith("❌") and "tha/v52.html" in i for i in issues),
                        "深層頁缺 sidebar 要係 ❌ blocker，實際：%s" % issues)

    def test_page_with_sidebar_passes(self):
        self._write("tha/v53.html", _page())
        issues = self._scan()
        self.assertFalse([i for i in issues if "tha/v53.html" in i], issues)

    def test_encrypted_page_skipped(self):
        self._write("secret.html",
                    '<html><head><script src="staticrypt/x.js"></script></head>'
                    '<body>y</body></html>')
        issues = self._scan()
        self.assertFalse([i for i in issues if i.startswith("❌") and "secret.html" in i],
                         issues)

    def test_sidebar_host_page_not_reported_missing(self):
        """`docs/shell.html` 自己就係 sidebar 實體持有人（<nav id="tsa-sidebar">）。"""
        self._write("shell.html",
                    '<html><body><nav id="tsa-sidebar"><div></div></nav></body></html>')
        issues = self._scan()
        self.assertFalse([i for i in issues if "shell.html" in i and i.startswith("❌")],
                         issues)

    def test_designated_standalone_is_warning_not_blocker(self):
        """`forex_news.html`／`ccy_power/index.html` 設計上唔載 sidebar ⇒ ⚠️ 唔係 ❌。"""
        self._write("forex_news.html", _page(js=False, css=False))
        issues = self._scan()
        hits = [i for i in issues if "forex_news.html" in i]
        self.assertTrue(hits, issues)
        self.assertTrue(all(not i.startswith("❌") for i in hits), hits)

    def test_missing_css_with_js_is_blocker(self):
        """有 script 冇 CSS ⇒ 慢網 FOUC（review I-3），要報。"""
        self._write("tha/v54.html", _page(js=True, css=False))
        issues = self._scan()
        self.assertTrue([i for i in issues if i.startswith("❌") and "tha/v54.html" in i],
                        issues)

    def test_real_repo_has_no_sidebar_gap(self):
        """對真 repo 跑：除加密白名單外應該零 ❌。"""
        self.qa.TSA_DIR = os.path.join(_ROOT, "docs")
        issues = self.qa.check_sidebar_consistency()
        blockers = [i for i in issues if i.startswith("❌")]
        self.assertEqual(blockers, [], blockers)


if __name__ == "__main__":
    unittest.main()
