#!/usr/bin/env python3
"""
TSA QA Checker — Automated quality checks for Trade Strategy Analyzer.
Run after any change to verify integrity.
"""

import os, re, glob, csv, json, sys
from collections import defaultdict

TSA_DIR = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs"
ADMIN_DIR = os.path.join(TSA_DIR, "admin")
REPORTS_DIR = os.path.join(TSA_DIR, "reports")
SIGNALS_DIR = "/mnt/c/Users/Alvin/Downloads/Set File From Signal Page"
DISABLED_SIGNALS_FILE = os.path.join(TSA_DIR, "disabled_signals.json")

# Expected pages with sidebar
EXPECTED_PAGES = [
    "index.html",
    "signal_ranking.html",
    "ccy_ranking.html",
    "volatility.html",
    "forex_news.html",
]
SUBDIR_PAGES = [
    ("ccy_power/index.html", "ccy_power"),
]

def check_sidebar_consistency():
    """Check all pages have sidebar.css and sidebar.js"""
    issues = []
    
    for page in EXPECTED_PAGES:
        path = os.path.join(ADMIN_DIR, page)
        if not os.path.exists(path):
            issues.append(f"❌ MISSING PAGE: {page}")
            continue
        with open(path) as f:
            html = f.read()
        if 'sidebar.css' not in html:
            issues.append(f"❌ NO SIDEBAR CSS: {page}")
        if 'sidebar.js' not in html:
            issues.append(f"❌ NO SIDEBAR JS: {page}")
    
    for page, subdir in SUBDIR_PAGES:
        path = os.path.join(ADMIN_DIR, page)
        if not os.path.exists(path):
            issues.append(f"❌ MISSING PAGE: {page}")
            continue
        with open(path) as f:
            html = f.read()
        if 'sidebar.css' not in html:
            issues.append(f"❌ NO SIDEBAR CSS: {page}")
        if 'sidebar.js' not in html:
            issues.append(f"❌ NO SIDEBAR JS: {page}")
    
    return issues


def load_disabled_signals():
    """Load disabled signals list from file"""
    if os.path.exists(DISABLED_SIGNALS_FILE):
        with open(DISABLED_SIGNALS_FILE) as f:
            data = json.load(f)
            return data.get("disabled", []), data.get("broken_counts", {})
    return [], {}


def save_disabled_signals(disabled, broken_counts):
    """Save disabled signals list to file"""
    with open(DISABLED_SIGNALS_FILE, "w") as f:
        json.dump({"disabled": disabled, "broken_counts": broken_counts}, f, indent=2)


def record_broken_link(sig_id, link_type, disabled, broken_counts):
    """Record a broken link. If same signal breaks 3 times, mark as disabled."""
    key = f"{sig_id}:{link_type}"
    broken_counts[key] = broken_counts.get(key, 0) + 1
    
    if broken_counts[key] >= 3 and sig_id not in disabled:
        disabled.append(sig_id)
        print(f"  🔕 AUTO-DISABLED: Signal #{sig_id} (broken 3 times)")
    
    return disabled, broken_counts


def check_signal_links():
    """Check all signal links in signal_ranking.html are valid"""
    issues = []
    ranking_path = os.path.join(ADMIN_DIR, "signal_ranking.html")
    
    if not os.path.exists(ranking_path):
        return [f"❌ MISSING: signal_ranking.html"]
    
    # Load disabled signals
    disabled, broken_counts = load_disabled_signals()
    newly_disabled = []
    
    with open(ranking_path) as f:
        html = f.read()
    
    # Check AlgoForest links
    algo_links = re.findall(r'href="(https://signals\.algoforest\.com/signals/(\d+))"', html)
    for url, sig_id in algo_links:
        # Just verify format, can't check external links
        if not sig_id.isdigit():
            issues.append(f"❌ INVALID ALGOLINK: {url}")
    
    # Check internal report links (skip disabled)
    # Note: ranking page uses martin_v4_*.html (not martin_final_*.html)
    # Missing reports are WARNINGS, not blockers — they indicate signals without
    # generated analysis yet, which is expected for newer/smaller signals.
    index_links = re.findall(r'href="\.\./reports/index_(\d+)\.html"', html)
    martin_links = re.findall(r'href="\.\./reports/martin_v4_(\d+)\.html"', html)
    
    broken_index = []
    broken_martin = []
    
    for sig_id in index_links:
        if sig_id in disabled:
            continue  # Skip disabled signals
        report_path = os.path.join(REPORTS_DIR, f"index_{sig_id}.html")
        if not os.path.exists(report_path):
            broken_index.append(sig_id)
    
    for sig_id in martin_links:
        if sig_id in disabled:
            continue
        report_path = os.path.join(REPORTS_DIR, f"martin_v4_{sig_id}.html")
        if not os.path.exists(report_path):
            broken_martin.append(sig_id)
    
    if broken_index:
        issues.append(f"⚠️ BROKEN 📊 LINKS ({len(broken_index)}): index_*.html referenced but not found: {sorted(broken_index, key=int)}")
    if broken_martin:
        issues.append(f"⚠️ BROKEN 📊 LINKS ({len(broken_martin)}): martin_v4_*.html referenced but not found: {sorted(broken_martin, key=int)}")
    
    # Check for signal IDs without any report icons (missing reports)
    sig_ids_in_ranking = set(re.findall(r'signals\.algoforest\.com/signals/(\d+)', html))
    sig_ids_with_index = set(index_links)
    sig_ids_with_martin = set(martin_links)
    
    # Filter out disabled signals
    missing_index = sig_ids_in_ranking - sig_ids_with_index - set(disabled)
    missing_martin = sig_ids_in_ranking - sig_ids_with_martin - set(disabled)
    
    if missing_index:
        issues.append(f"⚠️ MISSING 🔍 DEEP REPORTS ({len(missing_index)}): signals without index_*.html: {sorted(missing_index, key=int)}")
    if missing_martin:
        issues.append(f"⚠️ MISSING 📊 MARTIN REPORTS ({len(missing_martin)}): signals without martin_v4_*.html: {sorted(missing_martin, key=int)}")
    
    # Save updated disabled list
    save_disabled_signals(disabled, broken_counts)
    
    return issues


def check_ea_types():
    """Check no signals have Unknown EA type"""
    issues = []
    
    sys.path.insert(0, '/home/alvin/.openclaw/workspace/scripts')
    from signal_analyzer import analyze_signal
    
    for d in sorted(os.listdir(SIGNALS_DIR)):
        full = os.path.join(SIGNALS_DIR, d)
        if not os.path.isdir(full) or not d.isdigit():
            continue
        result = analyze_signal(d)
        if result and result['ea_type'] == 'Unknown':
            issues.append(f"❌ UNKNOWN EA: Signal #{d}")
    
    return issues


def check_data_freshness():
    """Check data sources are recent (primary source + weekend-market aware)"""
    import time
    from datetime import datetime, timedelta
    issues = []

    base = "/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/MQL4/Files"
    # Primary source first (feeds the CCY Power pipeline), then EA fallback export
    sources = ["ccy_power_reader.csv", "forex_data.csv"]
    existing = [f for f in sources if os.path.exists(os.path.join(base, f))]
    if not existing:
        issues.append(f"❌ MISSING: ccy_power_reader.csv and forex_data.csv")
        return issues

    # Weekend closure window: Sat 05:00 HKT → Mon 08:00 HKT (same rule as update_ccy_power.py)
    now = datetime.now()
    wd, hr = now.weekday(), now.hour
    closure_started = None
    if wd == 5 and hr >= 5:
        closure_started = now.replace(hour=5, minute=0, second=0, microsecond=0)
    elif wd == 6:
        closure_started = (now - timedelta(days=1)).replace(hour=5, minute=0, second=0, microsecond=0)
    elif wd == 0 and hr < 8:
        closure_started = (now - timedelta(days=2)).replace(hour=5, minute=0, second=0, microsecond=0)

    grace = 0.0
    if closure_started:
        # During weekend closure the EA legitimately stops writing — allow closure duration + 3h slack
        grace = (now - closure_started).total_seconds() / 3600 + 3

    for name in existing:
        mtime = os.path.getmtime(os.path.join(base, name))
        age_hours = (time.time() - mtime) / 3600
        threshold = 48 + grace
        if age_hours > threshold:
            issues.append(
                f"⚠️ STALE DATA: {name} is {age_hours:.0f} hours old "
                f"(threshold {threshold:.0f}h incl. weekend allowance) — MT4/EA export likely stopped"
            )

    return issues


def check_nav_consistency():
    """Check sidebar.js has all expected nav links"""
    issues = []
    sidebar_js = os.path.join(TSA_DIR, "sidebar.js")
    
    if not os.path.exists(sidebar_js):
        return [f"❌ MISSING: sidebar.js"]
    
    with open(sidebar_js) as f:
        js = f.read()
    
    expected_links = [
        ("index.html", "首頁"),
        ("signal_ranking.html", "Signal 排名"),
        ("ccy_ranking.html", "CCY 排名"),
        ("ccy_power/index.html", "CCY Power"),
        ("volatility.html", "波幅表"),
        ("forex_news.html", "外匯新聞"),
    ]
    
    for href, label in expected_links:
        if href not in js:
            issues.append(f"❌ NAV MISSING: {label} ({href})")
    
    return issues


def run_all_checks():
    """Run all QA checks and print report"""
    all_issues = []
    
    print("=" * 60)
    print("🔍 TSA QA CHECK")
    print("=" * 60)
    
    checks = [
        ("Navigation Consistency", check_nav_consistency),
        ("Sidebar on All Pages", check_sidebar_consistency),
        ("Signal Links", check_signal_links),
        ("Data Freshness", check_data_freshness),
    ]
    
    for name, check_fn in checks:
        print(f"\n📋 {name}...")
        issues = check_fn()
        if issues:
            for issue in issues:
                print(f"  {issue}")
                all_issues.append((name, issue))
        else:
            print(f"  ✅ PASS")
    
    # EA type check is slow, make it optional
    if "--full" in sys.argv:
        print(f"\n📋 EA Type Check (full)...")
        issues = check_ea_types()
        if issues:
            for issue in issues:
                print(f"  {issue}")
                all_issues.append(("EA Types", issue))
        else:
            print(f"  ✅ PASS")
    
    print(f"\n{'=' * 60}")
    blockers = [i for i in all_issues if i[1].startswith("❌")]
    warnings = [i for i in all_issues if i[1].startswith("⚠️")]
    
    if blockers:
        print(f"❌ FAIL — {len(blockers)} blocker(s), {len(warnings)} warning(s)")
    elif warnings:
        print(f"⚠️ PASS WITH WARNINGS — {len(warnings)} warning(s)")
    else:
        print(f"✅ ALL CLEAR")
    
    return len(blockers) == 0


if __name__ == "__main__":
    ok = run_all_checks()
    sys.exit(0 if ok else 1)
