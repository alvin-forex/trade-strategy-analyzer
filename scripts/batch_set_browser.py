#!/usr/bin/env python3
"""
Batch SET file downloader using OpenClaw browser evaluate.
Processes signals one by one, saves .set files to disk.
"""
import json, os, subprocess, time

OUTPUT_DIR = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/downloads/set_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SIGNALS = [
    30503, 31732, 31739, 36377, 36379, 36510, 36511, 36512, 36513, 36519,
    36520, 36655, 36656, 36657, 36658, 37850, 37851, 38641, 38663, 38667,
    38678, 38683, 38693, 38698, 38699, 38761, 38762, 38897, 38900, 43024,
    44452, 44453, 44459, 44465
]

DIR_MAP = {1: "Buy", 2: "Sell", 3: "Both", None: "Unknown"}

JS_TEMPLATE = """
async () => {
    const signalId = {SID};
    
    if (window.next && window.next.router) {
        await window.next.router.push('/signals/' + signalId);
    }
    
    let found = false;
    for (let i = 0; i < 10; i++) {
        await new Promise(r => setTimeout(r, 1000));
        const btn = [...document.querySelectorAll('button')].find(b => b.innerText?.trim() === 'Settings');
        if (btn) { found = true; break; }
    }
    if (!found) return JSON.stringify({signalId, error: 'No Settings button'});
    
    [...document.querySelectorAll('button')].find(b => b.innerText?.trim() === 'Settings').click();
    await new Promise(r => setTimeout(r, 2000));
    
    [...document.querySelectorAll('button[data-state="closed"]')].filter(b => 
        b.textContent?.includes('Total files')
    ).forEach(b => b.click());
    await new Promise(r => setTimeout(r, 2000));
    
    const btns = [...document.querySelectorAll('button')].filter(b => b.innerText.trim() === 'Download');
    const seen = new Set();
    const files = [];
    
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
                    files.push({
                        id: sf.id,
                        ea: sf.expertAdvisorName || 'Unknown',
                        symbol: sf.symbol || 'Unknown',
                        tf: String(sf.timeframe || ''),
                        dir: sf.tradeType,
                        content: sf.content || '',
                        logDt: sf.updateLog?.dateTime || ''
                    });
                }
                break;
            }
            p = p?.return;
            d++;
        }
    }
    
    return JSON.stringify({signalId, files});
}
"""

def format_filename(signal_id, f):
    direction = DIR_MAP.get(f.get('dir'), f"Type{f.get('dir')}")
    dt = f.get('logDt', '').replace('.000Z','').replace('T','_').replace(':','-')
    ea = (f.get('ea') or 'Unknown').replace(' ', '').replace('/', '_')
    symbol = f.get('symbol') or 'Unknown'
    tf = f.get('tf') or ''
    filename = f"({signal_id}){ea}{symbol}_{tf}_{direction}_{dt}.set"
    return filename.replace('\\\\', '_').replace('/', '_')

def run_browser_eval(js_code, target_id="E21489CB6A01459B37198776DD672FF6"):
    """Use openclaw browser tool via subprocess"""
    # Write JS to temp file and use browser tool
    result = subprocess.run(
        ["openclaw", "browser", "act", "--kind", "evaluate", "--fn", js_code, 
         "--target-id", target_id],
        capture_output=True, text=True, timeout=120
    )
    return result.stdout

# Since we can't easily call browser from subprocess, we'll output the JS for each signal
# and process manually
success = 0
no_files = 0
errors = 0
total_files = 0

print(f"Processing {len(SIGNALS)} signals...")
print(f"Output: {OUTPUT_DIR}")
print()

for sid in SIGNALS:
    print(f"Signal {sid}: ", end="", flush=True)
    # We need to use the browser tool directly - output the JS for copy-paste
    js = JS_TEMPLATE.replace("{SID}", str(sid))
    
    # Check if we already have files for this signal
    existing = [f for f in os.listdir(OUTPUT_DIR) if f.startswith(f"({sid})")]
    if existing:
        print(f"SKIP ({len(existing)} files exist)")
        continue
    
    # Write JS to file for the agent to process
    with open(f"/tmp/set_eval_{sid}.js", "w") as f:
        f.write(js)
    
    print(f"JS written to /tmp/set_eval_{sid}.js")
    # The actual browser eval will be done by the agent

print(f"\nDone generating JS files")
