#!/usr/bin/env python3
"""
Batch generate index-style reports using headless browser automation.
Uses Playwright to load index.html, inject CSV, trigger analysis, and save report.
"""
import os, sys, json, time, glob

# Config
DOCS_DIR = os.path.join(os.path.dirname(__file__), 'docs')
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')
REPORTS_DIR = os.path.join(DOCS_DIR, 'reports')
SERVER_URL = 'http://localhost:8765'
UPLOAD_URL = 'http://localhost:8766/save-report'

def get_needed_reports():
    """Get list of signal IDs that need index reports."""
    # Get all CSVs
    csvs = glob.glob(os.path.join(DOWNLOADS_DIR, 'forex-forest-signals-page-*.csv'))
    csv_ids = set()
    for c in csvs:
        sid = os.path.basename(c).replace('forex-forest-signals-page-', '').replace('.csv', '')
        csv_ids.add(sid)
    
    # Get existing reports
    existing = set()
    for f in glob.glob(os.path.join(REPORTS_DIR, 'index_*.html')):
        sid = os.path.basename(f).replace('index_', '').replace('.html', '')
        existing.add(sid)
    
    needed = sorted(csv_ids - existing, key=int)
    return needed

def generate_report_js(csv_path):
    """Generate JS code to inject CSV and trigger analysis."""
    with open(csv_path, 'rb') as f:
        import base64
        b64 = base64.b64encode(f.read()).decode()
    
    return f"""
    async () => {{
        // Reset
        const input = document.getElementById('csvInput');
        input.value = '';
        input.files = new DataTransfer().files;
        
        // Fetch CSV
        const resp = await fetch('/downloads/{os.path.basename(csv_path)}');
        if (!resp.ok) return {{ error: 'fetch failed', status: resp.status }};
        const blob = await resp.blob();
        const file = new File([blob], 'signal.csv', {{type: 'text/csv'}});
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event('change', {{bubbles: true}}));
        
        // Click analyze
        document.getElementById('analyzeBtn')?.click();
        
        // Wait for results
        await new Promise(r => setTimeout(r, 5000));
        
        // Generate report
        if (typeof downloadReport === 'function') downloadReport();
        const html = window._reportHTML;
        if (!html) return {{ error: 'no report generated' }};
        
        // Save via upload server
        const saveResp = await fetch('{UPLOAD_URL}', {{method: 'POST', body: html}});
        const text = await saveResp.text();
        return {{ status: saveResp.status, size: html.length, text }};
    }}
    """

if __name__ == '__main__':
    needed = get_needed_reports()
    print(f"Reports needed: {len(needed)}")
    print(f"IDs: {needed[:10]}{'...' if len(needed) > 10 else ''}")
    
    if not needed:
        print("All reports up to date!")
        sys.exit(0)
    
    print(f"\nRun: python3 batch_browser_reports.py {' '.join(needed)}")
    print("Or use the browser automation approach.")
