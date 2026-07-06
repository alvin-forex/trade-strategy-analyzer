#!/usr/bin/env python3
"""
CDP Helper: Use Windows curl.exe to bridge WSL → Chrome CDP on [::1]:9222
"""
import json, subprocess, asyncio, websockets, os

CURL = "/mnt/c/Windows/System32/curl.exe"

def cdp_http(path):
    """Make HTTP request to Chrome CDP via Windows curl"""
    result = subprocess.run(
        [CURL, "-s", f"http://[::1]:9222{path}"],
        capture_output=True, text=True, timeout=10
    )
    return json.loads(result.stdout) if result.stdout.strip() else None

def get_ws_url():
    """Get WebSocket URL for the first page tab"""
    targets = cdp_http("/json/list")
    if not targets:
        return None
    for t in targets:
        if t['type'] == 'page' and 'algoforest' in t.get('url', ''):
            return t["webSocketDebuggerUrl"]
    for t in targets:
        if t['type'] == 'page':
            return t["webSocketDebuggerUrl"]
    return None

def cdp_ws_forward():
    """Start a TCP relay from WSL 127.0.0.1:9222 → Windows [::1]:9222"""
    # Use socat-like relay via Python
    import socket, threading, select
    
    relay_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    relay_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        relay_sock.bind(('127.0.0.1', 9222))
    except OSError:
        return None  # Already bound
    relay_sock.listen(5)
    
    def handle(client):
        # Use Windows curl to tunnel websocket... actually just use subprocess netcat
        # Simpler: relay TCP to Windows [::1]:9222 via a Windows python one-liner
        pass
    
    return None

# The simplest approach: patch websockets to connect via Windows
class WindowsWebSocket:
    """WebSocket that connects through Windows using curl"""
    pass

# ACTUAL SOLUTION: Use ws://[::1]:9222 directly from Python websockets
# Python's websockets library supports IPv6

async def connect_cdp():
    """Connect to Chrome CDP via IPv6 localhost"""
    ws_url = get_ws_url()
    if not ws_url:
        print("ERROR: No CDP target found")
        return None
    
    # Replace localhost with [::1] for WSL compatibility
    # ws://localhost:9222 → ws://[::1]:9222
    ws_url_v6 = ws_url.replace("ws://localhost:", "ws://[::1]:").replace("ws://127.0.0.1:", "ws://[::1]:")
    
    print(f"Connecting to: {ws_url_v6}")
    ws = await websockets.connect(ws_url_v6, max_size=50*1024*1024, open_timeout=10, ping_interval=None)
    return ws

async def cdp_eval(ws, expr, mid=1, timeout=15):
    """Evaluate JS in browser via CDP"""
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

if __name__ == "__main__":
    # Test connection
    async def test():
        url = get_ws_url()
        print(f"WS URL: {url}")
        ws = await connect_cdp()
        if ws:
            val = await cdp_eval(ws, "window.location.href")
            print(f"Current page: {val}")
            await ws.close()
    
    asyncio.run(test())
