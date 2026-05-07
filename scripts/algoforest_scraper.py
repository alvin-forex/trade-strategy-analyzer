#!/usr/bin/env python3
"""
AlgoForest Signal Scraper - Downloads CSV from AlgoForest signals page
Usage:
    python3 algoforest_scraper.py download <signal_id> [--output PATH]
    python3 algoforest_scraper.py download_batch <signal_id1> <signal_id2> ...
    python3 algoforest_scraper.py analyze <signal_id>  # Download + run analysis
"""

import asyncio
import argparse
import os
import sys
import re
import hashlib
import sqlite3
from pathlib import Path

# Project paths
PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
DOWNLOAD_DIR = Path("/mnt/c/Users/Alvin/Downloads")
DB_PATH = DATA_DIR / "analysis_history.db"


async def download_signal_csv(signal_id: str, output_path: str = None) -> str:
    """Download CSV from AlgoForest for a given signal ID."""
    from playwright.async_api import async_playwright
    
    if output_path is None:
        output_path = str(DOWNLOAD_DIR / f"forex-forest-signals-page-{signal_id}.csv")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        await context.add_init_script('Object.defineProperty(navigator, "webdriver", {get: () => undefined});')
        
        page = await context.new_page()
        
        download_result = []
        async def handle_download(download):
            await download.save_as(output_path)
            download_result.append(output_path)
        
        page.on('download', handle_download)
        
        url = f'https://signals.algoforest.com/signals/{signal_id}'
        resp = await page.goto(url, wait_until='domcontentloaded', timeout=30000)
        
        if resp.status == 403:
            print(f"  ❌ Cloudflare blocked (403) for signal {signal_id}")
            await browser.close()
            return None
        
        await page.wait_for_timeout(8000)
        
        # Dismiss any dialog
        await page.keyboard.press('Escape')
        await page.wait_for_timeout(2000)
        
        # Click Trading Order Histories
        hist_btn = await page.query_selector('button:has-text("Trading Order Histories")')
        if hist_btn:
            await hist_btn.click(force=True)
            await page.wait_for_timeout(5000)
        
        # Dismiss dialog again
        await page.keyboard.press('Escape')
        await page.wait_for_timeout(2000)
        
        # Click Export
        export_btn = await page.query_selector('button:has-text("Export")')
        if export_btn:
            await export_btn.evaluate('el => el.click()')
            await page.wait_for_timeout(5000)
        
        await browser.close()
    
    if download_result:
        # Verify file
        with open(output_path, 'r') as f:
            lines = f.readlines()
        if len(lines) > 1:
            print(f"  ✅ Downloaded signal {signal_id}: {len(lines)} rows → {output_path}")
            return output_path
        else:
            print(f"  ⚠️ Downloaded file for signal {signal_id} has only {len(lines)} rows")
            return output_path
    else:
        print(f"  ❌ No download triggered for signal {signal_id}")
        return None


def get_csv_hash(path: str) -> str:
    """Calculate MD5 hash of CSV file."""
    h = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def get_next_version(signal_id: str) -> int:
    """Get the next version number for a signal_id."""
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute('SELECT MAX(version) FROM analyses WHERE signal_id = ?', (signal_id,))
    row = cur.fetchone()
    conn.close()
    return (row[0] or 0) + 1


async def download_and_analyze(signal_id: str):
    """Download CSV and run analysis pipeline."""
    print(f"\n{'='*60}")
    print(f"📥 Signal {signal_id}: Downloading from AlgoForest...")
    print(f"{'='*60}")
    
    csv_path = await download_signal_csv(signal_id)
    if not csv_path:
        print(f"  ❌ Failed to download CSV for signal {signal_id}")
        return None
    
    # Check if this CSV was already analyzed (by hash)
    csv_hash = get_csv_hash(csv_path)
    conn = sqlite3.connect(str(DB_PATH))
    cur = conn.cursor()
    cur.execute('SELECT id, version FROM analyses WHERE signal_id = ? AND csv_hash = ? ORDER BY id DESC LIMIT 1', 
                (signal_id, csv_hash))
    existing = cur.fetchone()
    conn.close()
    
    if existing:
        print(f"  ℹ️ This exact CSV was already analyzed as #{existing[0]} (v{existing[1]})")
        return existing[0]
    
    # Run the analysis
    version = get_next_version(signal_id)
    print(f"  🔄 Running analysis v{version}...")
    
    # Run the analysis pipeline
    sys.path.insert(0, str(PROJECT_DIR))
    os.chdir(str(PROJECT_DIR))
    from run_analysis import run as run_analysis
    
    try:
        report_path = run_analysis(csv_path, download=True)
        print(f"  ✅ Analysis complete, report: {report_path}")
        
        # Save to database
        import sqlite3
        conn = sqlite3.connect(str(DB_PATH))
        cur = conn.cursor()
        
        # Get basic stats from the CSV for DB record
        import pandas as pd
        df = pd.read_csv(csv_path)
        total_trades = len(df)
        profitable = df[df['Net Profit'].astype(float) > 0]
        win_rate = round(len(profitable) / total_trades * 100, 1) if total_trades > 0 else 0
        total_profit = round(df['Net Profit'].astype(float).sum(), 2)
        
        csv_name = os.path.basename(csv_path)
        symbols = ', '.join(sorted(df['Symbol'].unique())) if 'Symbol' in df.columns else ''
        
        cur.execute('''
            INSERT INTO analyses (signal_id, csv_filename, csv_hash, analysis_date, 
                                  total_trades, win_rate, total_profit, symbols_summary, report_path)
            VALUES (?, ?, ?, datetime('now'), ?, ?, ?, ?, ?)
        ''', (signal_id, csv_name, csv_hash, total_trades, win_rate, total_profit, 
              symbols, str(report_path) if report_path else ''))
        
        analysis_id = cur.lastrowid
        conn.commit()
        conn.close()
        
        print(f"  📊 Saved as analysis #{analysis_id}")
        return analysis_id
    except Exception as e:
        print(f"  ❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    parser = argparse.ArgumentParser(description='AlgoForest Signal Scraper')
    parser.add_argument('action', choices=['download', 'download_batch', 'analyze'],
                       help='Action to perform')
    parser.add_argument('signal_ids', nargs='+', help='Signal ID(s)')
    parser.add_argument('--output', '-o', help='Output file path (for single download)')
    
    args = parser.parse_args()
    
    if args.action == 'download':
        path = await download_signal_csv(args.signal_ids[0], args.output)
        if path:
            print(f"\nCSV saved to: {path}")
        else:
            sys.exit(1)
    
    elif args.action == 'download_batch':
        for sid in args.signal_ids:
            await download_signal_csv(sid)
            await asyncio.sleep(2)  # Rate limit
    
    elif args.action == 'analyze':
        for sid in args.signal_ids:
            result = await download_and_analyze(sid)
            await asyncio.sleep(2)


if __name__ == '__main__':
    asyncio.run(main())
