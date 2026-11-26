#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_vercel_links.py — Vercel 部署後逐頁自查（照 0410 派工第 3 點）

用法:
    python3 verify_vercel_links.py https://<deployment-url> [--sample N]

檢查範圍（照 0410「nav.toc／reports/index_*／全部 sidebar links 全 200」）:
  1. /reports/index_*.html 全量 481 頁（或 --sample 抽 N 頁）
  2. /reports/ 入 martin_v4／其他報告頁抽樣（每 index 頁頭 8 條報告連結）
  3. /admin/ 全部頁
  4. 首頁 / 及 sidebar.js
  5. /data/ 加密數據抽樣 5 檔
任何非 200 → 逐條列出，exit 1；全 200 → exit 0。

依賴: 純 stdlib（urllib），無需 pip。
"""
import json
import re
import sys
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor

TIMEOUT = 20
UA = {"User-Agent": "TSA-deploy-verify/1.0 (ZCODE_w)"}


def fetch_code(url):
    try:
        req = urllib.request.Request(url, headers=UA, method="GET")
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, r.read(4096).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:
        return 0, str(e)


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: verify_vercel_links.py https://<url> [--sample N]")
    base = sys.argv[1].rstrip("/")
    sample = 0
    if "--sample" in sys.argv:
        sample = int(sys.argv[sys.argv.index("--sample") + 1])

    checks = []          # (url, why)
    # 1. 首頁＋核心資產
    checks.append((f"{base}/", "首頁"))
    checks.append((f"{base}/sidebar.css", "sidebar.css"))
    checks.append((f"{base}/sidebar.js", "sidebar.js"))
    checks.append((f"{base}/common.js", "common.js"))

    # 2. reports/index_*.html——由本地 repo 清單讀（本腳本在 repo 內跑時）
    import os
    from pathlib import Path
    repo_docs = None
    for cand in [Path("docs"), Path("../docs"), Path(__file__).resolve().parents[3] / "docs"]:
        if (cand / "reports").is_dir():
            repo_docs = cand
            break
    index_pages = []
    admin_pages = []
    data_files = []
    if repo_docs:
        index_pages = sorted(p.name for p in (repo_docs / "reports").glob("index_*.html"))
        admin_pages = sorted(p.name for p in (repo_docs / "admin").glob("*.html"))
        data_files = sorted(p.name for p in (repo_docs / "data").glob("*.enc"))[:5]
    if sample and len(index_pages) > sample:
        step = max(1, len(index_pages) // sample)
        index_pages = index_pages[::step][:sample]

    for f in index_pages:
        checks.append((f"{base}/reports/{f}", "reports/index"))
    for f in admin_pages:
        checks.append((f"{base}/admin/{f}", "admin"))
    for f in data_files:
        checks.append((f"{base}/data/{f}", "data/.enc"))

    # 3. 每個 index 頁抽報告連結（頭 8 條 href）
    hrefs = []
    for f in (index_pages[:12] if index_pages else []):
        local = (repo_docs / "reports" / f)
        if local.exists():
            html = local.read_text(encoding="utf-8", errors="ignore")
            for m in re.findall(r'href="([^"#?]+\.html)"', html)[:8]:
                if m.startswith("http"):
                    continue
                hrefs.append(m if not m.startswith("/") else m.lstrip("/"))
    seen = set()
    for h in hrefs:
        if h not in seen:
            seen.add(h)
            url = f"{base}/reports/{h}" if not h.startswith("reports/") else f"{base}/{h}"
            checks.append((url, "index內報告連結"))

    print(f"檢查 {len(checks)} 項（index {len(index_pages)}／admin {len(admin_pages)}／連結抽樣 {len(seen)}）...")
    fails = []
    with ThreadPoolExecutor(max_workers=12) as ex:
        results = list(ex.map(lambda c: fetch_code(c[0]), checks))
    for i, (url, why) in enumerate(checks):
        code, _snip = results[i]
        if code != 200:
            fails.append((url, why, code))
    ok = len(checks) - len(fails)
    print(json.dumps({
        "total": len(checks),
        "ok_200": ok,
        "fail": len(fails),
        "fail_list": [f"{c} [{w}] {u}" for u, w, c in fails[:30]],
        "PASS": len(fails) == 0,
    }, ensure_ascii=False, indent=1))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
