#!/usr/bin/env python3
"""Task H v2.00 — unify existing report pages' head CSS + add back links.

One-off fixer for docs/reports/index_*.html (154 pages at time of writing).
Idempotent: pages already carrying the back link are skipped.

What it does per page (by kind):
  real  (>=1000 bytes): insert back-link <p> right after <body ...>;
                        ensure <html lang="zh-Hant">;
                        title "Trade Strategy Analysis Report" ->
                        "Signal {ID} — Trade Strategy Analysis Report"
  stub  (<1000 bytes): rebuild with official head (lang + tool CSS + signal
                        title) + back link + .card wrap; original sentence
                        "No trading data available (deposit only, no trades
                        executed)." preserved verbatim.

CSS source of truth: repo root index.html first <style> block (same source
the batch generators use). Run from repo root:

    python3 unify_report_heads.py [--dry-run] [--check]

--check: run tests/link_check.py afterwards (exit 1 on dead links).
"""
import re
import sys
from pathlib import Path

BACK_LINK = ('<p style="margin-bottom:16px">'
             '<a href="../index.html" style="color:#0f3460;text-decoration:none;'
             'font-weight:600">← 返回主頁</a></p>')
GENERIC_TITLE = "<title>Trade Strategy Analysis Report</title>"
STUB_BODY_RE = re.compile(r"<h2>.*?</h2>\s*<p>.*?</p>", re.S)


def find_repo_root() -> Path:
    p = Path(__file__).resolve().parent
    for cand in [p, *p.parents]:
        if (cand / "index.html").is_file() and (cand / "docs").is_dir():
            return cand
    sys.exit("ERROR: run from repo root (needs index.html + docs/)")


def tool_css(root: Path) -> str:
    html = (root / "index.html").read_text(encoding="utf-8")
    i = html.find("<style>")
    j = html.find("</style>", i)
    if i < 0 or j <= i:
        sys.exit("ERROR: no <style> block in index.html")
    return html[i + 7:j]


def fix_real(page: Path, sig: str, css: str) -> str:
    s = page.read_text(encoding="utf-8")
    if 'href="../index.html"' in s:
        return "skip-backlink-exists"
    # lang
    if "<html lang=" not in s:
        s = s.replace("<html>", '<html lang="zh-Hant">', 1)
    # title
    if GENERIC_TITLE in s:
        s = s.replace(GENERIC_TITLE,
                      f"<title>Signal {sig} — Trade Strategy Analysis Report</title>", 1)
    # back link after <body ...>
    b = s.find("<body")
    if b < 0:
        return "skip-no-body"
    e = s.find(">", b)
    if e < 0:
        return "skip-broken-body"
    s = s[:e + 1] + "\n" + BACK_LINK + s[e + 1:]
    page.write_text(s, encoding="utf-8")
    return "fixed"


def fix_stub(page: Path, sig: str, css: str) -> str:
    s = page.read_text(encoding="utf-8")
    if 'href="../index.html"' in s:
        return "skip-backlink-exists"
    m = STUB_BODY_RE.search(s)
    if not m:
        # not a recognised stub; fall back to real-page treatment
        return fix_real(page, sig, css)
    # original h2+p sentence block kept verbatim (covers both stub variants:
    # "No trading data available..." and "Analysis timeout.")
    orig = m.group(0)
    html = f"""<!DOCTYPE html>
<html lang="zh-Hant"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Signal {sig} — Trade Strategy Analysis Report</title><style>
{css}
</style></head><body style="max-width:900px;margin:0 auto;padding:20px;font-family:-apple-system,BlinkMacSystemFont,sans-serif">
{BACK_LINK}
<div class="card">{orig}</div>
</body></html>
"""
    page.write_text(html, encoding="utf-8")
    return "fixed-stub"


def main() -> int:
    dry = "--dry-run" in sys.argv
    root = find_repo_root()
    reports = sorted((root / "docs" / "reports").glob("index_*.html"))
    if not reports:
        sys.exit("ERROR: docs/reports/index_*.html not found")
    css = tool_css(root)

    stats = {"fixed": 0, "fixed-stub": 0, "skip-backlink-exists": 0, "skip-no-body": 0,
             "skip-broken-body": 0}
    for page in reports:
        sig = page.stem.replace("index_", "")
        size = page.stat().st_size
        kind = fix_stub if size < 1000 else fix_real
        if dry:
            s = page.read_text(encoding="utf-8")
            res = "skip-backlink-exists" if 'href="../index.html"' in s else (
                "would-fix-stub" if size < 1000 else "would-fix")
            print(f"[dry] {page.name}: {res}")
            continue
        res = kind(page, sig, css)
        stats[res] = stats.get(res, 0) + 1
        print(f"{page.name}: {res}")

    print("\n=== SUMMARY ===")
    for k, v in stats.items():
        if v:
            print(f"{k}: {v}")
    print(f"total pages scanned: {len(reports)}")

    if "--check" in sys.argv and not dry:
        import subprocess
        r = subprocess.run([sys.executable, str(root / "tests" / "link_check.py")])
        if r.returncode != 0:
            print("link_check FAILED")
            return 1
        print("link_check PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
