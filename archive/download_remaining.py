#!/usr/bin/env python3
"""Download remaining CSVs for signals that don't have them yet."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from algoforest_scraper import download_signal_csv

SAMPLES_DIR = Path(__file__).parent / 'samples'

REMAINING = [
    '21698','22200','22278','23617','25260','25668','25830','30359','31593','31781',
    '32278','32541','32719','3291','33101','34259','34574','36338','36397','5001',
    '5275','537','5566','5636','7919','8325'
]

async def main():
    for i, sid in enumerate(REMAINING):
        csv_path = SAMPLES_DIR / f'forex-forest-signals-page-{sid}.csv'
        if csv_path.exists():
            print(f"[{i+1}/{len(REMAINING)}] ✅ exists {sid}")
            continue
        print(f"[{i+1}/{len(REMAINING)}] 📥 {sid}...", end=' ', flush=True)
        try:
            result = await download_signal_csv(str(sid), str(csv_path))
            if result:
                print(f"✅")
            else:
                print(f"❌")
        except Exception as e:
            print(f"❌ {e}")
        if i < len(REMAINING) - 1:
            await asyncio.sleep(3)

    print("\nDone!")

asyncio.run(main())
