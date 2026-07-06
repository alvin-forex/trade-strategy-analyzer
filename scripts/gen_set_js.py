#!/usr/bin/env python3
"""
Batch download SET files via OpenClaw browser (not CDP).
Outputs JS code to evaluate in browser, then saves results.
"""
import json, os, time

OUTPUT_DIR = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/downloads/set_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SIGNALS = [
    30503, 31732, 31739, 36377, 36379, 36510, 36511, 36512, 36513, 36519,
    36520, 36655, 36656, 36657, 36658, 37850, 37851, 38641, 38663, 38667,
    38678, 38683, 38693, 38698, 38699, 38761, 38762, 38897, 38900, 43024,
    44452, 44453, 44459, 44465
]

# Generate the JS snippet for batch extraction
JS_TEMPLATE = """
async () => {
    const signalId = {SID};
    
    // Navigate via Next.js router
    if (window.next && window.next.router) {
        await window.next.router.push('/signals/' + signalId);
    }
    
    // Wait for Settings button
    for (let i = 0; i < 10; i++) {
        await new Promise(r => setTimeout(r, 1000));
        const btn = [...document.querySelectorAll('button')].find(b => b.innerText?.trim() === 'Settings');
        if (btn) break;
    }
    
    // Click Settings
    const settingsBtn = [...document.querySelectorAll('button')].find(b => b.innerText?.trim() === 'Settings');
    if (!settingsBtn) return JSON.stringify({signalId, error: 'No Settings button'});
    settingsBtn.click();
    await new Promise(r => setTimeout(r, 2000));
    
    // Expand accordions
    [...document.querySelectorAll('button[data-state="closed"]')].filter(b => 
        b.textContent?.includes('Total files')
    ).forEach(b => b.click());
    await new Promise(r => setTimeout(r, 2000));
    
    // Extract SET files via React fiber
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
                        id: sf.id,
                        ea: sf.expertAdvisorName,
                        symbol: sf.symbol,
                        tf: sf.timeframe,
                        dir: sf.tradeType,
                        content: sf.content || null,
                        logDt: sf.updateLog?.dateTime || null
                    });
                }
                break;
            }
            p = p?.return;
            d++;
        }
    }
    
    return JSON.stringify({signalId, files: result});
}
"""

# Generate JS for each signal
for sid in SIGNALS:
    js = JS_TEMPLATE.replace("{SID}", str(sid))
    print(f"=== Signal {sid} ===")
    print(js)
    print("---END---")
