#!/usr/bin/env python3
"""L22 StatiCrypt anti-resurrection gate.

The 14 core pages were password-protected in 7ad97b7f (StatiCrypt AES-256,
client-side). Generators (generate_signal_ranking_v5.py 等) write PLAINTEXT
to some of these paths — if a regenerated page is committed unencrypted,
its content is public again on Pages. This gate fails CI whenever any core
page is not StatiCrypt-wrapped, forcing re-encryption via
scripts/encrypt_admin_pages.sh before the push counts as green.

Reads blobs via `git show HEAD:<path>` so it works both in CI (full checkout)
and in sparse local clones, and always audits the committed state rather than
a possibly stale working tree. Exit 1 = at least one page plaintext/missing.
"""
import subprocess
import sys

CORE_PAGES = [
    "docs/admin/ccy_ranking.html",
    "docs/admin/db-browser.html",
    "docs/admin/forex_news.html",
    "docs/admin/index.html",
    "docs/admin/mfe_mae.html",
    "docs/admin/mt5_mcp_tools.html",
    "docs/admin/period_stats.html",
    "docs/admin/pivot_table.html",
    "docs/admin/signal_ranking.html",
    "docs/admin/symbol_ranking.html",
    "docs/admin/tasks_board.html",
    "docs/admin/volatility.html",
    "docs/index.html",
    "docs/signal_ranking.html",
]


def git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False)


def head_blob(rel: str) -> bytes | None:
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], capture_output=True, check=False)
    return r.stdout if r.returncode == 0 else None


def main() -> int:
    head = git(["rev-parse", "--short", "HEAD"]).stdout.strip()
    bad = []
    for rel in CORE_PAGES:
        blob = head_blob(rel)
        if blob is None:
            bad.append((rel, "MISSING"))
        elif b"staticrypt" not in blob[:4096].lower():
            bad.append((rel, "PLAINTEXT"))

    total = len(CORE_PAGES)
    if bad:
        print(f"[enc-check] FAIL: {len(bad)}/{total} core pages not StatiCrypt-wrapped (HEAD={head}):")
        for rel, why in bad:
            print(f"[enc-check]   {why:9s} {rel}")
        print("[enc-check] fix: bash scripts/encrypt_admin_pages.sh   (password from $TSA_PW_FILE)")
        return 1
    print(f"[enc-check] PASS: {total}/{total} core pages StatiCrypt-wrapped (HEAD={head})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
