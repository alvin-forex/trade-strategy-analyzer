#!/usr/bin/env python3
"""
Download SET files for all signals via browser evaluate.
Outputs the saved files to downloads/set_files/
"""
import json, os

OUTPUT_DIR = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/downloads/set_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

DIR_MAP = {1: "Buy", 2: "Sell", 3: "Both", None: "Unknown"}

def format_filename(signal_id, f):
    direction = DIR_MAP.get(f.get('dir'), f"Type{f.get('dir')}")
    dt = (f.get('logDt') or '').replace('.000Z','').replace('T','_').replace(':','-')
    ea = (f.get('ea') or 'Unknown').replace(' ', '').replace('/', '_')
    symbol = f.get('symbol') or 'Unknown'
    tf = f.get('tf') or ''
    filename = f"({signal_id}){ea}{symbol}_{tf}_{direction}_{dt}.set"
    return filename.replace('\\', '_').replace('/', '_')

def save_signal_files(signal_id, files_json):
    """Save files from JSON result"""
    data = json.loads(files_json) if isinstance(files_json, str) else files_json
    if 'files' not in data:
        return 0
    saved = 0
    for f in data['files']:
        content = f.get('content', '')
        if not content:
            continue
        filename = format_filename(signal_id, f)
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'w', newline='') as fh:
            fh.write(content)
        saved += 1
    return saved

# Already processed: 30503
# Remaining signals with content
SIGNALS_WITH_CONTENT = [
    36377, 36510, 36511, 36512, 36513, 36519, 36520,
    36655, 36656, 36657, 36658, 37850, 37851, 38641,
    38663, 38667, 38678, 38683, 38693, 38698, 38699,
    38761, 38762, 38897, 38900, 43024,
    44452, 44453, 44459, 44465
]

print(f"Signals to process: {len(SIGNALS_WITH_CONTENT)}")
print(f"Output dir: {OUTPUT_DIR}")
print("Run browser evaluate for each batch of 5 signals to extract full content")
