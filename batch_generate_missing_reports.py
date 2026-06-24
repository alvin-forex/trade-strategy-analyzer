#!/usr/bin/env python3
"""
Batch generate missing Signal Deep Analysis and Martin Autopsy reports.

For each signal CSV in downloads/:
  1. If docs/reports/Signal_Deep_Analysis_{sid}.html is missing → generate via Playwright
  2. If docs/reports/martin_final_{sid}.html is missing → generate via martin_autopsy_v3

Usage: python3 batch_generate_missing_reports.py
"""

import os
import sys
import glob
import time
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / 'downloads'
REPORTS_DIR = BASE_DIR / 'docs' / 'reports'
DEEP_SCRIPT = BASE_DIR / 'archive' / 'generate_deep_report.py'
MARTIN_SCRIPT = BASE_DIR / 'generate_martin_autopsy_v3.py'

def get_all_signal_csvs():
    """Get all signal CSV files mapped by signal ID."""
    csvs = {}
    # Pattern: forex-forest-signals-page-{sid}.csv
    for f in DOWNLOADS_DIR.glob('forex-forest-signals-page-*.csv'):
        sid = f.stem.replace('forex-forest-signals-page-', '')
        try:
            int(sid)
            csvs[sid] = f
        except ValueError:
            continue
    # Also plain {sid}.csv
    for f in DOWNLOADS_DIR.glob('[0-9]*.csv'):
        sid = f.stem
        try:
            int(sid)
            if sid not in csvs:
                csvs[sid] = f
        except ValueError:
            continue
    return csvs

def get_existing_deep_ids():
    """Get set of signal IDs that already have deep analysis reports."""
    ids = set()
    for f in REPORTS_DIR.glob('Signal_Deep_Analysis_*.html'):
        sid = f.stem.replace('Signal_Deep_Analysis_', '')
        ids.add(sid)
    return ids

def get_existing_martin_ids():
    """Get set of signal IDs that already have martin_final reports."""
    ids = set()
    for f in REPORTS_DIR.glob('martin_final_*.html'):
        sid = f.stem.replace('martin_final_', '')
        ids.add(sid)
    # Also count martin_autopsy_v3_full_ as existing
    for f in REPORTS_DIR.glob('martin_autopsy_v3_full_*.html'):
        sid = f.stem.replace('martin_autopsy_v3_full_', '')
        ids.add(sid)
    return ids

def generate_martin_report(sid, csv_path):
    """Generate martin_final report for a signal."""
    output_path = REPORTS_DIR / f'martin_final_{sid}.html'
    try:
        result = subprocess.run(
            ['python3', str(MARTIN_SCRIPT), str(csv_path), '--output', str(output_path)],
            capture_output=True, text=True, timeout=60, cwd=str(BASE_DIR)
        )
        if result.returncode == 0 and output_path.exists():
            return True, result.stdout
        else:
            return False, f"RC={result.returncode}\nSTDERR={result.stderr[-500:]}"
    except subprocess.TimeoutExpired:
        return False, "Timeout"
    except Exception as e:
        return False, str(e)

def generate_deep_report(sid, csv_path):
    """Generate deep analysis report using Playwright script."""
    output_path = REPORTS_DIR / f'Signal_Deep_Analysis_{sid}.html'
    try:
        env = os.environ.copy()
        result = subprocess.run(
            ['python3', str(DEEP_SCRIPT), sid],
            capture_output=True, text=True, timeout=300, cwd=str(BASE_DIR), env=env
        )
        if result.returncode == 0 and output_path.exists():
            return True, result.stdout
        else:
            return False, f"RC={result.returncode}\nSTDERR={result.stderr[-500:]}"
    except subprocess.TimeoutExpired:
        return False, "Timeout (300s)"
    except Exception as e:
        return False, str(e)

def main():
    print("=" * 70)
    print("🚀 TSA Batch Report Generator")
    print("=" * 70)

    all_csvs = get_all_signal_csvs()
    existing_deep = get_existing_deep_ids()
    existing_martin = get_existing_martin_ids()

    # Find what's missing
    all_sids = sorted(all_csvs.keys(), key=int)
    missing_deep = [s for s in all_sids if s not in existing_deep]
    missing_martin = [s for s in all_sids if s not in existing_martin]

    print(f"\n📊 Signal Inventory:")
    print(f"  Total CSV signals: {len(all_sids)}")
    print(f"  Existing Deep Analysis: {len(existing_deep & set(all_sids))}")
    print(f"  Existing Martin Reports: {len(existing_martin & set(all_sids))}")
    print(f"  ❌ Missing Deep Analysis: {len(missing_deep)}")
    print(f"  ❌ Missing Martin Reports: {len(missing_martin)}")

    if missing_deep:
        print(f"\n  Deep Analysis needed: {', '.join(missing_deep)}")
    if missing_martin:
        print(f"\n  Martin Reports needed: {', '.join(missing_martin)}")

    total_tasks = len(missing_deep) + len(missing_martin)
    if total_tasks == 0:
        print("\n✅ All reports are up to date! Nothing to do.")
        return

    # ─── Phase 1: Generate Martin Reports (fast, pure Python) ───
    martin_success = 0
    martin_fail = 0
    martin_errors = {}

    if missing_martin:
        print(f"\n{'─'*70}")
        print(f"📋 Phase 1: Generating {len(missing_martin)} Martin Reports")
        print(f"{'─'*70}")

        for i, sid in enumerate(missing_martin):
            csv_path = all_csvs[sid]
            print(f"  [{i+1}/{len(missing_martin)}] Signal #{sid}... ", end="", flush=True)
            ok, msg = generate_martin_report(sid, csv_path)
            if ok:
                size = (REPORTS_DIR / f'martin_final_{sid}.html').stat().st_size
                print(f"✅ ({size:,} bytes)")
                martin_success += 1
            else:
                print(f"❌ {msg[:100]}")
                martin_errors[sid] = msg
                martin_fail += 1

    # ─── Phase 2: Generate Deep Analysis Reports (Playwright, slower) ───
    deep_success = 0
    deep_fail = 0
    deep_errors = {}

    if missing_deep:
        print(f"\n{'─'*70}")
        print(f"📋 Phase 2: Generating {len(missing_deep)} Deep Analysis Reports")
        print(f"{'─'*70}")

        for i, sid in enumerate(missing_deep):
            csv_path = all_csvs[sid]
            print(f"  [{i+1}/{len(missing_deep)}] Signal #{sid}... ", end="", flush=True)
            ok, msg = generate_deep_report(sid, csv_path)
            if ok:
                size = (REPORTS_DIR / f'Signal_Deep_Analysis_{sid}.html').stat().st_size
                print(f"✅ ({size:,} bytes)")
                deep_success += 1
            else:
                print(f"❌ {msg[:100]}")
                deep_errors[sid] = msg
                deep_fail += 1

    # ─── Summary ───
    print(f"\n{'='*70}")
    print(f"📊 Batch Generation Summary")
    print(f"{'='*70}")
    print(f"  Martin Reports:    ✅ {martin_success} | ❌ {martin_fail} | Total {len(missing_martin)}")
    print(f"  Deep Analysis:     ✅ {deep_success} | ❌ {deep_fail} | Total {len(missing_deep)}")
    total_success = martin_success + deep_success
    total_fail = martin_fail + deep_fail
    print(f"  ────────────────────────────────────")
    print(f"  Total:             ✅ {total_success} | ❌ {total_fail} | Total {total_tasks}")

    if martin_errors:
        print(f"\n⚠️ Martin Errors:")
        for sid, err in martin_errors.items():
            print(f"    #{sid}: {err[:200]}")

    if deep_errors:
        print(f"\n⚠️ Deep Analysis Errors:")
        for sid, err in deep_errors.items():
            print(f"    #{sid}: {err[:200]}")

    print(f"\n✨ Done! {total_success} reports generated successfully.")

if __name__ == '__main__':
    main()
