#!/usr/bin/env python3
"""L22 StatiCrypt anti-resurrection gate.

The 6 core pages are StatiCrypt-wrapped (AES-256, client-side). 2026-11-01
boss-ruled admin reorg (34b49ae0) moved 7 encrypted pages to root plaintext
and deleted admin/signal_ranking.html — list synced 14→6.
Generators (generate_signal_ranking_v5.py 等) write
PLAINTEXT to some of these paths — if a regenerated page is committed
unencrypted, its content is public again on Pages. This gate fails CI
whenever any core page is not StatiCrypt-wrapped, forcing re-encryption via
scripts/encrypt_admin_pages.sh before the push counts as green.

Reads blobs via `git show HEAD:<path>` so it works both in CI (full checkout)
and in sparse local clones, and always audits the committed state rather than
a possibly stale working tree. Exit 1 = at least one page plaintext/missing.
"""
import subprocess
import sys

CORE_PAGES = [
    "docs/admin/db-browser.html",
    "docs/admin/index.html",
    "docs/admin/mt5_mcp_tools.html",
    "docs/admin/projection.html",
    "docs/admin/tasks_board.html",
    "docs/index.html",
    "docs/signal_ranking.html",
]
# 2026-11-04 七頁：projection.html 補入（OpenClaw 0435 ③ 批准）——owner 加密頁
# （P1/P3 修復主場）原唔在名單＝正閘脫網，明文復活閘攔唔住。

# 2026-11-04 #26 派工（OpenClaw 0335 ③）：負向斷言——禁止復活清單。
# docs/admin/ccy_ranking.html 係 6.9MB 明文復活實錄（11-03 137d1ddc）：內容與
# root 公開頁同類（老闆裁定 CCY 分析頁公開）、secrets 0 命中，副本無存在價值；
# 生成器已停寫（generate_ranking_ccy_v5.py 11-04 起）。呢條路徑唔在 CORE_PAGES
# 六頁名單——正負兩閘都攔唔住先會復活，此斷言補上；存在即 FAIL（無論形態）。
BLOCKED_PAGES = [
    ("docs/admin/ccy_ranking.html",
     "CCY 排名已裁定公開於 root，admin 副本禁止復活"),
    ("docs/admin/ccy_power/index.html",
     "CCY Power 已統一 root 公開層（docs/ccy_power/），admin 層頁面禁止復活（P5）"),
    ("docs/admin/history.html",
     "閘外寫入路徑（P5 停寫）——root/reports 為唯一出口"),
    ("docs/admin/mfe_mae.html",
     "閘外寫入路徑（P5 停寫）——root 公開層為唯一出口"),
    ("docs/admin/period_stats.html",
     "閘外寫入路徑（P5 停寫）——root 公開層為唯一出口"),
    ("docs/admin/pivot_table.html",
     "閘外寫入路徑（P5 停寫）——root 公開層為唯一出口"),
    ("docs/admin/ccy",
     "閘外寫入目錄（generate_ccy_deep_analysis，P5 停寫）——root 層落點待排期"),
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

    # 負向斷言：禁止復活清單——存在即 FAIL（唔理加密定明文，副本本身唔應存在）
    resurrected = []
    for rel, msg in BLOCKED_PAGES:
        r = git(["cat-file", "-e", f"HEAD:{rel}"])
        if r.returncode == 0:
            resurrected.append((rel, msg))

    total = len(CORE_PAGES)
    if bad or resurrected:
        print(f"[enc-check] FAIL: {len(bad)}/{total} core pages not StatiCrypt-wrapped, "
              f"{len(resurrected)} blocked-path resurrected (HEAD={head}):")
        for rel, why in bad:
            print(f"[enc-check]   {why:9s} {rel}")
        for rel, msg in resurrected:
            print(f"[enc-check]   RESURRECTED {rel} — {msg}")
        print("[enc-check] fix: bash scripts/encrypt_admin_pages.sh   (password from $TSA_PW_FILE)")
        return 1
    print(f"[enc-check] PASS: {total}/{total} core pages StatiCrypt-wrapped + "
          f"{len(BLOCKED_PAGES)} blocked-path negative assert (HEAD={head})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
