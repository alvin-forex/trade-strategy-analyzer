#!/usr/bin/env python3
"""Batch generate V2 Signal reports for all CSV files in samples/."""
import os
import sys
import time
from pathlib import Path
from generate_signal_report_v2 import generate_report

SAMPLES_DIR = Path(__file__).parent / 'samples'
OUTPUT_DIR = Path(__file__).parent / 'docs' / 'reports'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Get all CSV files
csv_files = sorted(SAMPLES_DIR.glob('forex-forest-signals-page-*.csv'))
print(f"🚀 Batch Signal Report V2 Generator")
print(f"   Found {len(csv_files)} CSV files\n")

results = {'success': [], 'failed': [], 'skipped': []}

for i, csv_path in enumerate(csv_files, 1):
    signal_id = csv_path.stem.replace('forex-forest-signals-page-', '')
    output_path = OUTPUT_DIR / f'signal_{signal_id}.html'
    
    # Skip if already exists and recent
    if output_path.exists() and output_path.stat().st_size > 10000:
        print(f"[{i}/{len(csv_files)}] ⏭️ {signal_id}: already exists ({output_path.stat().st_size//1024}KB)")
        results['skipped'].append(signal_id)
        continue
    
    print(f"[{i}/{len(csv_files)}] 🔄 {signal_id}...", end=' ', flush=True)
    try:
        _, size = generate_report(signal_id, str(csv_path), str(output_path))
        print(f"✅ {size//1024}KB")
        results['success'].append(signal_id)
    except Exception as e:
        print(f"❌ {e}")
        results['failed'].append(signal_id)

print(f"\n{'='*50}")
print(f"📋 SUMMARY")
print(f"{'='*50}")
print(f"  ✅ Generated: {len(results['success'])}")
print(f"  ⏭️ Skipped: {len(results['skipped'])}")
print(f"  ❌ Failed: {len(results['failed'])}")
if results['failed']:
    print(f"  Failed IDs: {results['failed']}")
print(f"  📂 Total reports: {len(list(OUTPUT_DIR.glob('signal_*.html')))}")
