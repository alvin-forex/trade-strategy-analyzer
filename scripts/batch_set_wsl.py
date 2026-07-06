#!/usr/bin/env python3
"""
Batch SET file downloader via Windows Python (bypasses WSL2 IPv6 issue)
"""
import json, subprocess, os, sys

OUTPUT_DIR = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/downloads/set_files"
WIN_OUTPUT_DIR = r"C:\Users\Alvin\Downloads\Set File From Signal Page"
WIN_SCRIPT_PATH = r"C:\Users\Alvin\ChromeDebug\batch_set_win.py"
WIN_PYTHON = "/mnt/c/Python314/python.exe"

SIGNALS = [
    30503, 31732, 31739, 36377, 36379, 36510, 36511, 36512, 36513, 36519,
    36520, 36655, 36656, 36657, 36658, 37850, 37851, 38641, 38663, 38667,
    38678, 38683, 38693, 38698, 38699, 38761, 38762, 38897, 38900, 43024,
    44452, 44453, 44459, 44465
]

WIN_SCRIPT = '''import json, asyncio, websockets, urllib.request, os

OUTPUT_DIR = r"C:\\Users\\Alvin\\Downloads\\Set File From Signal Page"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SIGNALS = ''' + str(SIGNALS) + '''

def get_ws_url():
    req = urllib.request.Request("http://[::1]:9222/json/list")
    with urllib.request.urlopen(req, timeout=5) as resp:
        targets = json.loads(resp.read())
    for t in targets:
        if t["type"] == "page" and "algoforest" in t.get("url", ""):
            return t["webSocketDebuggerUrl"]
    for t in targets:
        if t["type"] == "page":
            return t["webSocketDebuggerUrl"]
    return None

async def cdp_eval(ws, expr, mid=1, timeout=15):
    await ws.send(json.dumps({"id":mid, "method":"Runtime.evaluate",
        "params":{"expression":expr,"awaitPromise":True,"timeout":timeout*1000}}))
    deadline = asyncio.get_event_loop().time() + timeout + 10
    while asyncio.get_event_loop().time() < deadline:
        raw = await asyncio.wait_for(ws.recv(), timeout=min(5, deadline - asyncio.get_event_loop().time()))
        data = json.loads(raw)
        if data.get("id") == mid:
            result = data.get("result",{}).get("result",{})
            if result.get("type") == "undefined":
                return None
            return result.get("value")
    return None

async def main():
    ws_url = get_ws_url()
    if not ws_url:
        print("ERROR: No CDP target found")
        return
    ws = await websockets.connect(ws_url, max_size=50*1024*1024, open_timeout=10, ping_interval=None)
    print("Connected to Chrome CDP")

    total_files = 0
    errors = 0

    for idx, sid in enumerate(SIGNALS):
        try:
            routed = await cdp_eval(ws, "(async () => { if (window.next && window.next.router) { await window.next.router.push('/signals/" + str(sid) + "'); return 'ok'; } return 'fail'; })()")
            if routed != "ok":
                print(f"  X {sid}: nav failed")
                errors += 1
                continue

            found = False
            for _ in range(8):
                await asyncio.sleep(1)
                v = await cdp_eval(ws, "(() => { const b = [...document.querySelectorAll('button')].find(b => b.innerText?.trim() === 'Settings'); return b ? 'yes' : 'no'; })()")
                if v == "yes":
                    found = True
                    break
            if not found:
                print(f"  X {sid}: no Settings")
                errors += 1
                continue

            await cdp_eval(ws, "(() => { const b = [...document.querySelectorAll('button')].find(b => b.innerText?.trim() === 'Settings'); if (b) b.click(); })()")
            await asyncio.sleep(2)

            await cdp_eval(ws, "(() => { [...document.querySelectorAll('button[data-state=\\\"closed\\\"]')].filter(b => b.textContent?.includes('Total files')).forEach(b => b.click()); })()")
            await asyncio.sleep(2)

            data = await cdp_eval(ws, "(() => { const btns = [...document.querySelectorAll('button')].filter(b => b.innerText.trim() === 'Download'); const seen = new Set(); const result = []; const dirMap = {1:'Buy',2:'Sell',3:'Both',null:'Unknown'}; for (const btn of btns) { const fk = Object.keys(btn).find(k => k.startsWith('__reactFiber')); if (!fk) continue; let p = btn[fk]?.return; let d = 0; while (p && d < 30) { const sf = p?.memoizedProps?.setFile; if (sf && sf.id) { if (!seen.has(sf.id)) { seen.add(sf.id); const ea = (sf.expertAdvisorName||'Unknown').replace(/ /g,''); const sym = sf.symbol||'Unknown'; const tf = String(sf.timeframe||''); const dir = dirMap[sf.tradeType]||'Unknown'; result.push({fn: '(' + " + str(sid) + " + ')' + ea + sym + '_' + tf + '_' + dir + '.set', c: sf.content || ''}); } break; } p = p?.return; d++; } } return JSON.stringify(result); })()", timeout=15)

            if not data:
                print(f"  - {sid}: no files")
                continue

            files = json.loads(data)
            for f in files:
                if f["c"]:
                    fpath = os.path.join(OUTPUT_DIR, f["fn"])
                    with open(fpath, "w", newline="") as fh:
                        fh.write(f["c"])
                    total_files += 1
                    print(f"  OK {sid}: {f['fn'][:60]}")
                else:
                    print(f"  ! {sid}: {f['fn'][:40]} (no content)")

        except Exception as e:
            print(f"  X {sid}: {str(e)[:80]}")
            errors += 1

        await asyncio.sleep(0.5)

        if (idx + 1) % 10 == 0:
            print(f"  Progress: {idx+1}/{len(SIGNALS)} | Files: {total_files} | Errors: {errors}")

    print(f"\\nDONE! {total_files} files, {errors} errors")
    print(f"Output: {OUTPUT_DIR}")
    await ws.close()

asyncio.run(main())
'''

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Write script to Windows path
    wsl_script_path = WIN_SCRIPT_PATH.replace("\\", "/").replace("C:", "/mnt/c")
    with open(wsl_script_path, "w") as f:
        f.write(WIN_SCRIPT)

    print(f"Running batch SET downloader via Windows Python...")
    print(f"Signals: {len(SIGNALS)}")
    print()

    result = subprocess.run(
        [WIN_PYTHON, WIN_SCRIPT_PATH],
        cwd=wsl_script_path.rsplit("/", 1)[0],
        timeout=600
    )

    # Copy files from Windows to WSL
    win_set_dir = "/mnt/c/Users/Alvin/Downloads/Set File From Signal Page"
    if os.path.exists(win_set_dir):
        import shutil
        count = 0
        for f in os.listdir(win_set_dir):
            if f.endswith('.set'):
                src = os.path.join(win_set_dir, f)
                dst = os.path.join(OUTPUT_DIR, f)
                shutil.copy2(src, dst)
                count += 1
        print(f"\nCopied {count} files to WSL: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
