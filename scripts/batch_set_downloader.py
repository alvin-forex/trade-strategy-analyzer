#!/usr/bin/env python3
"""
Batch Settings Tab .set File Downloader for AlgoForest
Uses CDP to navigate via Next.js router, extract React fiber data from Settings tab.

Usage:
  python3 batch_set_downloader.py [--signals ID1 ID2 ...] [--all] [--dir DIR]
  
  --signals  Download .set files for specific signal IDs
  --all      Download .set files for all signals (default)
  --dir      Output directory (default: downloads/set_files)
"""

import json, asyncio, websockets, urllib.request, os, sys, time

TOKEN = None  # Will be fetched from browser localStorage
DOWNLOAD_DIR = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/downloads/set_files"

# All signal IDs from the ranking table
ALL_SIGNAL_IDS = [
    10437, 11984, 13790, 17547, 21698, 22200, 22278, 25830, 30359, 31781,
    32719, 3291, 33101, 31593, 34574, 36338, 36397, 36511, 34259, 20846, 16538,
    106, 1980, 2351, 32278, 32541, 5001, 5275, 537, 5566, 11889, 13863, 14724,
    16596, 16698, 16706, 17611, 17823, 10864, 14158,
    12962, 13461, 14341, 14592, 1470, 17962, 20805, 23617, 25668, 25260, 8325, 7919,
    13798, 16596,
    19849,
    14581
]

# Deduplicate
ALL_SIGNAL_IDS = sorted(set(ALL_SIGNAL_IDS))

def get_ws_url():
    req = urllib.request.Request("http://localhost:9222/json/list")
    with urllib.request.urlopen(req, timeout=5) as resp:
        targets = json.loads(resp.read())
    for t in targets:
        if t['type'] == 'page':
            return t["webSocketDebuggerUrl"].replace("ws://localhost:", "ws://127.0.0.1:")
    return None

async def cdp_eval(ws, expr, mid=1, timeout=10):
    await ws.send(json.dumps({"id":mid, "method":"Runtime.evaluate", 
        "params":{"expression":expr,"awaitPromise":True,"timeout":timeout*1000}}))
    deadline = asyncio.get_event_loop().time() + timeout + 5
    while asyncio.get_event_loop().time() < deadline:
        raw = await asyncio.wait_for(ws.recv(), timeout=min(5, deadline - asyncio.get_event_loop().time()))
        data = json.loads(raw)
        if data.get("id") == mid:
            return data.get("result",{}).get("result",{}).get("value")
    return None

async def get_token(ws):
    """Get JWT token from browser localStorage"""
    val = await cdp_eval(ws, "localStorage.getItem('jwtToken')", mid=1)
    if val:
        print(f"  Got JWT token ({len(val)} chars)", flush=True)
    return val

async def navigate_to_signal(ws, signal_id):
    """Navigate using Next.js router (SPA navigation, no page reload)"""
    val = await cdp_eval(ws, f"""(async () => {{
        if (window.next && window.next.router) {{
            await window.next.router.push('/signals/{signal_id}');
            return 'routed';
        }}
        return 'no-router';
    }})()""", mid=1)
    return val == 'routed'

async def wait_for_settings(ws, max_wait=8):
    """Wait for Settings button to appear"""
    for attempt in range(max_wait):
        await asyncio.sleep(1)
        val = await cdp_eval(ws, """(() => {
            const btn = [...document.querySelectorAll('button')].find(b => b.innerText?.trim() === 'Settings');
            return btn ? 'found' : 'waiting';
        })()""", mid=100+attempt)
        if val == 'found':
            return True
    return False

async def click_settings_and_expand(ws):
    """Click Settings tab and expand all accordions"""
    # Click Settings
    await cdp_eval(ws, """(() => {
        const btn = [...document.querySelectorAll('button')].find(b => b.innerText?.trim() === 'Settings');
        if (btn) btn.click();
    })()""", mid=200)
    await asyncio.sleep(2)
    
    # Expand all closed accordions
    await cdp_eval(ws, """(() => {
        [...document.querySelectorAll('button[data-state="closed"]')].filter(b => 
            b.textContent?.includes('Total files')
        ).forEach(b => b.click());
    })()""", mid=201)
    await asyncio.sleep(2)

async def extract_setfiles(ws):
    """Extract .set file data from React fiber"""
    val = await cdp_eval(ws, """(() => {
        const btns = [...document.querySelectorAll('button')].filter(b => b.innerText.trim() === 'Download');
        const seen = new Set();
        const result = [];
        for (const btn of btns) {
            const fk = Object.keys(btn).find(k => k.startsWith('__reactFiber'));
            if (!fk) continue;
            let p = btn[fk]?.return;
            let d = 0;
            while (p && d < 30) {
                const sf = p?.memoizedProps?.setFile;
                if (sf && sf.id) {
                    if (!seen.has(sf.id)) {
                        seen.add(sf.id);
                        result.push({
                            id: sf.id, ea: sf.expertAdvisorName, symbol: sf.symbol,
                            tf: sf.timeframe, dir: sf.tradeType, logId: sf.updateLog?.id,
                            logDt: sf.updateLog?.dateTime, content: sf.content || null,
                            checksum: sf.checksum
                        });
                    }
                    break;
                }
                p = p?.return;
                d++;
            }
        }
        return JSON.stringify(result);
    })()""", mid=300, timeout=15)
    
    if not val:
        return []
    return json.loads(val)

def format_filename(signal_id, f):
    """Format .set filename: ({signalId}){EA}{Symbol}_{TF}_{Direction}_{DateTime}.set"""
    dir_map = {1: "Buy", 2: "Sell", 3: "Both", None: "Unknown"}
    direction = dir_map.get(f.get('dir'), f"Type{f.get('dir')}")
    
    # Format datetime
    dt = f.get('logDt', '')
    if dt:
        # 2026-03-31T20:32:07.000Z → 2026-03-31_20-32-07
        dt = dt.replace('.000Z','').replace('T','_').replace(':','-')
    
    ea_name = (f.get('ea') or 'Unknown').replace(' ', '')
    symbol = f.get('symbol') or 'Unknown'
    tf = f.get('tf') or ''
    if tf and isinstance(tf, int):
        tf = f"M{tf}"
    
    filename = f"({signal_id}){ea_name}{symbol}_{tf}_{direction}_{dt}.set"
    # Clean invalid chars
    filename = filename.replace('/', '_').replace('\\', '_')
    return filename

def save_setfile(signal_id, f, output_dir):
    """Save .set file and return (filepath, size) or (None, 0)"""
    if not f.get('content'):
        return None, 0
    
    filename = format_filename(signal_id, f)
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w', newline='') as fh:
        fh.write(f['content'])
    return filepath, len(f['content'])

async def process_signal(ws, signal_id, output_dir):
    """Process a single signal: navigate → Settings → extract → save"""
    try:
        # Navigate
        ok = await navigate_to_signal(ws, signal_id)
        if not ok:
            return None, "Navigation failed"
        
        # Wait for page
        ok = await wait_for_settings(ws)
        if not ok:
            return None, "Settings button not found"
        
        # Click Settings and expand
        await click_settings_and_expand(ws)
        
        # Extract files
        files = await extract_setfiles(ws)
        
        if not files:
            return [], None
        
        # Save files
        saved = []
        for f in files:
            filepath, size = save_setfile(signal_id, f, output_dir)
            saved.append({
                'fileId': f['id'],
                'ea': f.get('ea'),
                'symbol': f.get('symbol'),
                'tf': f.get('tf'),
                'dir': f.get('dir'),
                'logDt': f.get('logDt'),
                'filepath': filepath,
                'size': size
            })
        
        return saved, None
        
    except Exception as e:
        return None, str(e)

async def main():
    global TOKEN
    
    # Parse args
    signal_ids = []
    output_dir = DOWNLOAD_DIR
    args = sys.argv[1:]
    
    i = 0
    while i < len(args):
        if args[i] == '--signals':
            i += 1
            while i < len(args) and not args[i].startswith('--'):
                signal_ids.append(int(args[i]))
                i += 1
        elif args[i] == '--all':
            signal_ids = ALL_SIGNAL_IDS
            i += 1
        elif args[i] == '--dir':
            i += 1
            output_dir = args[i]
            i += 1
        else:
            i += 1
    
    if not signal_ids:
        signal_ids = ALL_SIGNAL_IDS
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Connect to CDP
    ws_url = get_ws_url()
    if not ws_url:
        print("ERROR: No Chrome page target found!", flush=True)
        sys.exit(1)
    
    ws = await websockets.connect(ws_url, max_size=50*1024*1024, open_timeout=10, ping_interval=None)
    print(f"Connected to Chrome CDP", flush=True)
    
    # Get fresh token
    TOKEN = await get_token(ws)
    
    total = len(signal_ids)
    total_files = 0
    total_bytes = 0
    errors = 0
    
    print(f"\nScanning {total} signals for Settings Tab .set files...\n", flush=True)
    
    for idx, signal_id in enumerate(signal_ids):
        files, err = await process_signal(ws, signal_id, output_dir)
        
        if err:
            print(f"  ❌ {signal_id}: {err}", flush=True)
            errors += 1
            continue
        
        if files is None:
            print(f"  ⏭️ {signal_id}: no data", flush=True)
            continue
        
        if len(files) == 0:
            print(f"  ⏭️ {signal_id}: no .set files in Settings Tab", flush=True)
            continue
        
        signal_bytes = sum(f['size'] for f in files)
        total_files += len(files)
        total_bytes += signal_bytes
        
        for f in files:
            if f['filepath']:
                print(f"  ✅ {signal_id}: {os.path.basename(f['filepath'])} ({f['size']}B)", flush=True)
            else:
                print(f"  ⚠️ {signal_id}: fileId={f['fileId']} | {f['ea']} | no content", flush=True)
        
        if (idx + 1) % 10 == 0:
            print(f"\n  Progress: {idx+1}/{total} | ✅ {total_files} files ({total_bytes/1024:.0f}KB) | ❌ {errors}\n", flush=True)
        
        # Small delay between signals
        await asyncio.sleep(0.5)
    
    print(f"\n{'='*50}", flush=True)
    print(f"DONE! {total} signals scanned", flush=True)
    print(f"  Downloaded: {total_files} files ({total_bytes/1024:.0f}KB)", flush=True)
    print(f"  Errors: {errors}", flush=True)
    print(f"  Output: {output_dir}", flush=True)
    
    await ws.close()

if __name__ == '__main__':
    asyncio.run(main())
