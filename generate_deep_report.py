#!/usr/bin/env python3
"""Generate Signal Deep Analysis report via Playwright - simple approach."""
import sys, os, time, glob

SIGNAL_ID = sys.argv[1] if len(sys.argv) > 1 else '16596'
BASE = '/home/alvin/.openclaw/workspace/trade_strategy_analyzer'
OUT = f'{BASE}/docs/reports/Signal_Deep_Analysis_{SIGNAL_ID}.html'

from playwright.sync_api import sync_playwright

def find(sid):
    csv = None; sfs = []
    for d in ['downloads','samples']:
        m = glob.glob(f'{BASE}/{d}/*{sid}*.csv')
        if m: csv = m[0]; break
    for d in ['downloads','samples']:
        sfs += glob.glob(f'{BASE}/{d}/*{sid}*.set')
    return csv, sfs

csv, sfs = find(SIGNAL_ID)
assert csv, f'No CSV for {SIGNAL_ID}'
print(f'{SIGNAL_ID}: csv={os.path.basename(csv)} sets={len(sfs)}')

with sync_playwright() as p:
    br = p.chromium.launch(headless=True)
    pg = br.new_page()
    errors = []
    pg.on('console', lambda m: errors.append(m.text) if m.type=='error' else None)
    
    # HTML is already modified with var + bridge functions
    
    # Read the already-modified index.html
    with open(f'{BASE}/index.html') as f:
        html = f.read()
    
    pg.route('http://localhost:8765/index.html', lambda r: r.fulfill(body=html, content_type='text/html'))
    pg.goto('http://localhost:8765/index.html')
    pg.wait_for_load_state('networkidle')
    print('Page loaded')
    
    # Use set_input_files for CSV (triggers the change listener)
    pg.locator('#csvInput').set_input_files(csv)
    time.sleep(0.5)
    
    # Check if csvFile got set
    cf = pg.evaluate('()=>window._getCsvFile()')
    print(f'csvFile via bridge: {cf is not None}')
    
    if cf is None:
        # Manually read and set via FileReader approach
        print('Manual CSV injection needed...')
        with open(csv, 'r') as f:
            csv_text = f.read()
        # Use page's own $ function to grab the file from input
        pg.evaluate("""() => {
            const input = document.getElementById('csvInput');
            if(input.files && input.files[0]) {
                csvFile = input.files[0];
            }
            if(!csvFile) {
                // Create from text
                csvFile = new File([`""" + csv_text.replace('`','\\`').replace('\\','\\\\') + """`], '""" + os.path.basename(csv) + """', {type:'text/csv'});
            }
            document.getElementById('analyzeBtn').disabled = false;
            refreshUploadUI();
        }""")
    
    # SET files
    if sfs:
        pg.locator('#setInput').set_input_files(sfs)
        time.sleep(0.5)
        sf_check = pg.evaluate('()=>window._getSetFiles().length')
        print(f'setFiles count: {sf_check}')
    
    print('Clicking analyze...')
    pg.evaluate('()=>document.getElementById("analyzeBtn").click()')
    
    # Poll
    for i in range(72):  # 6 min
        time.sleep(5)
        done = pg.evaluate('()=>document.getElementById("results").innerHTML.trim()!==""')
        if done:
            print('Done!')
            break
        if i%12==0: print(f'  waiting... {(i+1)*5}s errs={len(errors)}')
    else:
        print(f'Errors: {errors[-5:]}')
        pg.screenshot(path=f'/tmp/tsa_{SIGNAL_ID}.png')
        raise TimeoutError('Timeout')
    
    time.sleep(3)
    r = pg.evaluate("""() => {
        const s=document.querySelector('style').textContent;
        const r=document.getElementById('results');
        return '<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Signal Deep Analysis</title><style>'+s+'</style></head><body style="max-width:900px;margin:0 auto;padding:20px;font-family:sans-serif">'+r.innerHTML+'</body></html>';
    }""")
    
    with open(OUT,'w') as f: f.write(r)
    print(f'Saved: {OUT}')
    br.close()
print('Done!')
