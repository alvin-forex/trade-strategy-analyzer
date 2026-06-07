#!/usr/bin/env python3
"""Batch generate index-style reports using headless browser automation.

Uses Playwright to load index.html, inject CSV, trigger analysis, and save report.
"""
import os
import sys
import json
import time
import glob
import base64
from pathlib import Path
from typing import List, Set, Dict

# Config
BASE_DIR: Path = Path(__file__).parent
DOCS_DIR: Path = BASE_DIR / 'docs'
DOWNLOADS_DIR: Path = BASE_DIR / 'downloads'
REPORTS_DIR: Path = DOCS_DIR / 'reports'
SERVER_URL: str = 'http://localhost:8765'
UPLOAD_URL: str = 'http://localhost:8766/save-report'


def get_needed_reports() -> List[str]:
    """Get list of signal IDs that need index reports.

    Returns:
        Sorted list of signal IDs (as strings) that have CSVs but no reports.
    """
    # Get all CSVs
    csvs: List[str] = glob.glob(os.path.join(str(DOWNLOADS_DIR), 'forex-forest-signals-page-*.csv'))
    csv_ids: Set[str] = set()
    for c in csvs:
        sid: str = os.path.basename(c).replace('forex-forest-signals-page-', '').replace('.csv', '')
        csv_ids.add(sid)

    # Get existing reports
    existing: Set[str] = set()
    for f in glob.glob(os.path.join(str(REPORTS_DIR), 'index_*.html')):
        sid = os.path.basename(f).replace('index_', '').replace('.html', '')
        existing.add(sid)

    needed: List[str] = sorted(csv_ids - existing, key=int)
    return needed


def generate_report_js(csv_path: Path) -> str:
    """Generate JS code to inject CSV and trigger analysis.

    Args:
        csv_path: Path to the CSV file to inject.

    Returns:
        JavaScript code string for Playwright evaluate.
    """
    try:
        with open(csv_path, 'rb') as f:
            b64: str = base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        print(f"  ✗ CSV not found: {csv_path}")
        return ""
    except IOError as e:
        print(f"  ✗ Error reading {csv_path}: {e}")
        return ""

    csv_basename: str = os.path.basename(csv_path)
    return f"""
    async () => {{
        // Reset
        const input = document.getElementById('csvInput');
        input.value = '';
        input.files = new DataTransfer().files;

        // Fetch CSV
        const resp = await fetch('/downloads/{csv_basename}');
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
    needed: List[str] = get_needed_reports()
    print(f"Reports needed: {len(needed)}")
    print(f"IDs: {needed[:10]}{'...' if len(needed) > 10 else ''}")

    if not needed:
        print("All reports up to date!")
        sys.exit(0)

    print(f"\nRun: python3 batch_browser_reports.py {' '.join(needed)}")
    print("Or use the browser automation approach.")