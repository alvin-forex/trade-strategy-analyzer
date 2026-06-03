#!/usr/bin/env python3
"""
TSA QA 自動質量檢查腳本
用法：
  python3 scripts/tsa_qa_check.py --quick   # 快速模式：sidebar + 連結
  python3 scripts/tsa_qa_check.py --full    # 完整模式：全部檢查
"""

import argparse
import os
import re
import sys
import time
from pathlib import Path

# === 設定 ===
BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "docs"
REPORTS_DIR = BASE_DIR / "reports"
DOWNLOADS_DIR = BASE_DIR / "downloads"

# 必要頁面清單
REQUIRED_PAGES = [
    "index.html",
    "signal_ranking.html",
    "signal_ranking_dde_v5.html",
    "ranking_ccy.html",
]

# 導航組件 (sidebar 或 topnav 二擇一即可)
NAV_PATTERNS = ["sidebar.css", "sidebar.js", "topnav"]


class QAResult:
    def __init__(self):
        self.passes = []
        self.warns = []
        self.fails = []

    def ok(self, msg):
        self.passes.append(msg)

    def warn(self, msg):
        self.warns.append(msg)

    def fail(self, msg):
        self.fails.append(msg)

    def summary(self):
        total = len(self.passes) + len(self.warns) + len(self.fails)
        print(f"\n{'='*60}")
        print(f"📋 QA 總結：{total} 項檢查")
        print(f"  ✅ 通過：{len(self.passes)}")
        print(f"  ⚠️  警告：{len(self.warns)}")
        print(f"  ❌ 失敗：{len(self.fails)}")
        print(f"{'='*60}")
        if self.fails:
            print("\n❌ 需要修復的問題：")
            for f in self.fails:
                print(f"   • {f}")
        if self.warns:
            print("\n⚠️  警告事項：")
            for w in self.warns:
                print(f"   • {w}")
        if not self.fails and not self.warns:
            print("\n🎉 所有檢查通過！系統狀態良好。")
        return 1 if self.fails else 0


def check_sidebar_consistency(result: QAResult):
    """檢查 1：docs/ 下 HTML 頁面應有導航組件"""
    print("\n🔍 檢查 1：導航組件一致性")
    html_files = sorted(DOCS_DIR.glob("*.html"))

    for html_file in html_files:
        name = html_file.name
        content = html_file.read_text(encoding="utf-8", errors="ignore")
        has_nav = any(p in content for p in NAV_PATTERNS)

        # 排除 index.html（主頁可能有獨立導航）
        if name == "index.html":
            if has_nav:
                result.ok(f"index.html 有導航組件")
            else:
                result.warn(f"index.html 沒有 sidebar/topnav 導航（可能使用獨立導航）")
            continue

        if has_nav:
            result.ok(f"{name} ✓ 導航組件")
        else:
            result.fail(f"{name} 缺少 sidebar.css / sidebar.js 或 topnav 導航")


def check_signal_links(result: QAResult):
    """檢查 2：排名頁 signal 連結應指向新版報告"""
    print("\n🔍 檢查 2：Signal 連結有效性")
    ranking_files = sorted(DOCS_DIR.glob("signal_ranking*.html"))

    valid_prefixes = ("../reports/martin_v4_", "../reports/index_")
    bad_pattern = "../reports/detailed_comparison_"

    for rf in ranking_files:
        name = rf.name
        content = rf.read_text(encoding="utf-8", errors="ignore")
        links = re.findall(r'href="([^"]*)"', content)

        bad_links = [l for l in links if "detailed_comparison" in l]
        signal_links = [l for l in links if l.startswith("../reports/")]

        # Check for broken links (file doesn't exist)
        broken = []
        for sl in signal_links:
            target = BASE_DIR / sl.lstrip("./")
            if not target.exists():
                broken.append(sl)

        if bad_links:
            result.fail(f"{name} 有 {len(bad_links)} 個舊版 detailed_comparison 連結")
            for bl in bad_links[:5]:
                print(f"     ❌ {bl}")
        else:
            result.ok(f"{name} 沒有舊版連結")

        if broken:
            result.fail(f"{name} 有 {len(broken)} 個斷裂連結")
            for b in broken[:5]:
                print(f"     ❌ 斷裂: {b}")
        else:
            result.ok(f"{name} 所有報告連結有效 ({len(signal_links)} 個)")


def check_ea_types(result: QAResult):
    """檢查 3：排名頁不應有 Unknown EA 類型"""
    print("\n🔍 檢查 3：EA 類型檢查")
    ranking_files = sorted(DOCS_DIR.glob("signal_ranking*.html"))

    for rf in ranking_files:
        name = rf.name
        content = rf.read_text(encoding="utf-8", errors="ignore")
        # Look for "Unknown" in EA type context
        unknown_count = len(re.findall(r'>Unknown<', content))
        unknown_count += len(re.findall(r'class="[^"]*">Unknown<', content))

        if unknown_count > 0:
            result.fail(f"{name} 有 {unknown_count} 個 Unknown EA 類型")
        else:
            result.ok(f"{name} 沒有 Unknown EA 類型")


def check_csv_freshness(result: QAResult):
    """檢查 4：CSV 不應超過 48 小時"""
    print("\n🔍 檢查 4：CSV 時效性")
    csv_files = sorted(DOWNLOADS_DIR.glob("*.csv"))
    now = time.time()
    threshold_h = 48
    stale = []

    for csv in csv_files:
        age_h = (now - csv.stat().st_mtime) / 3600
        if age_h > threshold_h:
            stale.append((csv.name, age_h))

    if stale:
        result.warn(f"有 {len(stale)} 個 CSV 檔案超過 {threshold_h}h")
        for name, age in stale:
            print(f"     ⚠️  {name} ({age:.1f}h)")
    else:
        result.ok(f"所有 {len(csv_files)} 個 CSV 都在 {threshold_h}h 內")


def check_page_completeness(result: QAResult):
    """檢查 5：必要頁面存在"""
    print("\n🔍 檢查 5：頁面完整性")

    for page in REQUIRED_PAGES:
        path = DOCS_DIR / page
        if path.exists():
            size = path.stat().st_size
            if size > 1000:
                result.ok(f"{page} 存在 ({size:,} bytes)")
            else:
                result.fail(f"{page} 存在但太小 ({size} bytes)，可能不完整")
        else:
            result.fail(f"{page} 不存在")


def main():
    parser = argparse.ArgumentParser(description="TSA 系統 QA 檢查")
    parser.add_argument("--quick", action="store_true", help="快速模式：只檢查 sidebar + 連結")
    parser.add_argument("--full", action="store_true", help="完整模式：全部檢查")
    args = parser.parse_args()

    if not args.quick and not args.full:
        args.full = True  # 預設完整模式

    print("🦀 TSA QA 自動質量檢查")
    print(f"📁 工作目錄：{BASE_DIR}")
    mode = "快速" if args.quick else "完整"
    print(f"🔧 模式：{mode}")

    result = QAResult()

    # 所有模式都跑的檢查
    check_sidebar_consistency(result)
    check_signal_links(result)

    if args.full:
        check_ea_types(result)
        check_csv_freshness(result)
        check_page_completeness(result)

    sys.exit(result.summary())


if __name__ == "__main__":
    main()
