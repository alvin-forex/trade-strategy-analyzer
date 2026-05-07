#!/usr/bin/env python3
"""
AlgoForest Signal Data Downloader
Uses Chrome CDP to download CSV data from AlgoForest via user's authenticated browser session.
Requires Chrome running with --remote-debugging-port and logged into AlgoForest.
"""
import json, asyncio, websockets, urllib.request, os, sys, time, argparse
from datetime import datetime

# All signal IDs from EA_MAP + extra
ALL_SIGNALS = sorted(set([
    # DW
    10437,11984,13790,17547,21698,22200,22278,25830,30359,31781,32719,3291,33101,31593,34574,36338,36397,36511,34259,20846,16538,
    # SMA
    106,1980,2351,32278,32541,5001,5275,537,5566,11889,13863,14724,16596,16698,16706,17611,17823,10864,14158,
    # MKD
    12962,13461,14341,14592,1470,17962,20805,23617,25668,25260,8325,7919,
    # S10
    13798,
    # Flash
    19849,
    # GEM
    14581,
    # Extra
    27226, 10344, 10843, 12173, 12733
]))

DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "downloads")
CDP_PORT = 9223  # WSL proxy port


async def get_ws_url():
    """Get WebSocket URL for the first page target."""
    try:
        resp = urllib.request.urlopen(f"http://localhost:{CDP_PORT}/json/list")
        targets = json.loads(resp.read())
        page_targets = [t for t in targets if t["type"] == "page"]
        if not page_targets:
            raise Exception("No page targets found")
        return page_targets[0]["webSocketDebuggerUrl"].replace("ws://localhost:", "ws://127.0.0.1:")
    except Exception as e:
        raise Exception(f"Cannot connect to Chrome CDP on port {CDP_PORT}: {e}")


async def download_signal_csv(ws, signal_id):
    """Download CSV for a single signal via browser fetch()."""
    js_code = f"""
    (async () => {{
        try {{
            const r = await fetch('https://analytics-api.gemsai.com/signals/{signal_id}/trading-order-histories/export');
            if (r.status !== 200) return JSON.stringify({{error: true, status: r.status}});
            const text = await r.text();
            return JSON.stringify({{error: false, data: text}});
        }} catch(e) {{
            return JSON.stringify({{error: true, message: e.message}});
        }}
    }})()
    """
    await ws.send(json.dumps({"id": signal_id, "method": "Runtime.evaluate", "params": {
        "expression": js_code,
        "awaitPromise": True,
        "returnByValue": True
    }}))
    
    resp = json.loads(await ws.recv())
    result = resp.get("result", {}).get("result", {})
    value = result.get("value", "{}")
    data = json.loads(value)
    
    if data.get("error"):
        return None, f"HTTP {data.get('status', data.get('message', 'unknown'))}"
    
    return data.get("data"), "OK"


async def batch_download(signal_ids=None, delay=1.0):
    """Download CSV for multiple signals."""
    signals = signal_ids or ALL_SIGNALS
    ws_url = await get_ws_url()
    
    print(f"Connecting to Chrome CDP...")
    async with websockets.connect(ws_url, max_size=50*1024*1024) as ws:
        os.makedirs(DOWNLOAD_DIR, exist_ok=True)
        
        success = 0
        failed = []
        skipped = 0
        
        print(f"Downloading {len(signals)} signals...")
        
        for i, sig_id in enumerate(signals):
            outpath = os.path.join(DOWNLOAD_DIR, f"forex-forest-signals-page-{sig_id}.csv")
            
            # Skip if already downloaded today
            if os.path.exists(outpath):
                mtime = os.path.getmtime(outpath)
                if (time.time() - mtime) < 86400:  # Less than 24h old
                    skipped += 1
                    print(f"  [{i+1}/{len(signals)}] ⏭️  {sig_id}: already downloaded")
                    continue
            
            csv_data, status = await download_signal_csv(ws, sig_id)
            
            if csv_data and status == "OK":
                with open(outpath, "w", encoding="utf-8") as f:
                    f.write(csv_data)
                success += 1
                print(f"  [{i+1}/{len(signals)}] ✅ {sig_id}: {len(csv_data)} bytes")
            else:
                failed.append(sig_id)
                print(f"  [{i+1}/{len(signals)}] ❌ {sig_id}: {status}")
            
            if delay > 0 and i < len(signals) - 1:
                await asyncio.sleep(delay)
        
        print(f"\n{'='*50}")
        print(f"Done! Success: {success}, Skipped: {skipped}, Failed: {len(failed)}/{len(signals)}")
        if failed:
            print(f"Failed IDs: {failed}")
        
        return success, failed


def main():
    parser = argparse.ArgumentParser(description="Download AlgoForest signal CSV data via Chrome CDP")
    parser.add_argument("--signals", nargs="+", type=int, help="Specific signal IDs to download")
    parser.add_argument("--all", action="store_true", help="Download all known signals")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests (seconds)")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    args = parser.parse_args()
    
    signals = args.signals or (ALL_SIGNALS if args.all else None)
    if not signals:
        print("Specify --signals ID1 ID2... or --all")
        sys.exit(1)
    
    asyncio.run(batch_download(signals, args.delay))


if __name__ == "__main__":
    main()
