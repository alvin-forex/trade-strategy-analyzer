#!/usr/bin/env python3
"""Batch CSV Downloader for AlgoForest signals"""

import urllib.request
import os
import time

API_URL = "https://analytics-api.gemsai.com/signals/{}/trading-order-histories/export"
OUTPUT_DIR = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/downloads"

# Signal IDs from list (deduplicated)
SIGNAL_IDS = [
    537, 1470, 1980, 2351, 2739, 3291, 3894, 4022, 4200, 4734, 5001, 5117, 5275, 5566, 5636,
    7919, 8325, 10344, 10437, 10843, 10864, 11141, 11598, 11889, 11984, 12173, 12733,
    12962, 13461, 13790, 13798, 13863, 14158, 14341, 14581, 14592, 14724, 16266, 16538,
    16596, 16698, 16706, 16777, 17547, 17611, 17823, 17962, 19625, 19849, 20805, 20846,
    21698, 22200, 22278, 23617, 25260, 25668, 25830, 27226, 30359, 31593, 31781, 32278,
    32541, 32719, 33101, 34259, 34574, 35362, 35434, 35436, 36338, 36397, 36511, 38678
]

def download_csv(signal_id):
    url = API_URL.format(signal_id)
    filename = f"forex-forest-signals-page-{signal_id}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            content = resp.read().decode('utf-8')
            if 'Open Time' in content:
                with open(filepath, 'w', newline='') as f:
                    f.write(content)
                return len(content)
    except Exception as e:
        print(f"  ❌ {signal_id}: {e}")
        return 0
    
    return 0

if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    total = len(SIGNAL_IDS)
    success = 0
    total_bytes = 0
    
    print(f"Downloading {total} CSV files...")
    
    for i, sid in enumerate(SIGNAL_IDS):
        size = download_csv(sid)
        if size > 0:
            success += 1
            total_bytes += size
            print(f"  ✅ {sid}: {size//1024}KB ({i+1}/{total})")
        time.sleep(0.5)  # Rate limit
    
    print(f"\nDone! {success}/{total} files downloaded ({total_bytes//1024//1024}MB)")