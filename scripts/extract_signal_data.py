#!/usr/bin/env python3
"""
Extract trade data from SQLite database and save as CSV for a specific signal.
"""
import csv
import sqlite3
import json
from pathlib import Path
from datetime import datetime

# Database path
DB_PATH = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/data/analysis_history.db"
CSV_DIR = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer/samples")
CSV_DIR.mkdir(exist_ok=True)

def extract_signal_to_csv(signal_id):
    """Extract trades for a signal to CSV"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get the analysis data
    cursor.execute("""
        SELECT raw_stats 
        FROM analyses 
        WHERE signal_id = ?
        ORDER BY created_at DESC
        LIMIT 1
    """, (signal_id,))
    
    row = cursor.fetchone()
    
    if not row:
        print(f"❌ No data found for signal {signal_id}")
        conn.close()
        return None
    
    raw_stats_json = row[0]
    
    if not raw_stats_json:
        print(f"❌ No raw_stats found for signal {signal_id}")
        conn.close()
        return None
    
    raw_stats = json.loads(raw_stats_json)
    
    conn.close()
    
    # Check if raw_stats exists
    if not raw_stats:
        print(f"❌ No raw_stats found for signal {signal_id}")
        return None
    
    # Get currency pairs
    currency_data = raw_stats.get('currency_data', {})
    
    if not currency_data:
        print(f"❌ No currency data found for signal {signal_id}")
        return None
    
    # Collect all trades
    all_trades = []
    
    for currency, data in currency_data.items():
        trades = data.get('trades', [])
        
        for trade in trades:
            trade_row = {
                'Open Time': trade.get('open_time', ''),
                'Type': trade.get('type', ''),
                'Lots': trade.get('volume', 0),
                'Symbol': currency,
                'Open Price': trade.get('open_price', 0),
                'Close Time': trade.get('close_time', ''),
                'Close Price': trade.get('close_price', 0),
                'Commission': trade.get('commission', 0),
                'Swap': trade.get('swap', 0),
                'Net Pips': trade.get('net_pips', 0),
                'Net Profit': trade.get('net_profit', 0),
                'Max Profit': trade.get('max_profit', 0),
                'Max Pips': trade.get('max_pips', 0),
                'Max Loss': trade.get('max_loss', 0),
                'Max Loss Pips': trade.get('max_loss_pips', 0),
                'Magic Number': trade.get('magic_number', ''),
                'Comment': trade.get('comment', ''),
                'Holding Time (Hours)': trade.get('holding_hours', 0),
                'Holding Time': trade.get('holding_time', '')
            }
            all_trades.append(trade_row)
    
    # Sort by open time
    all_trades.sort(key=lambda x: x['Open Time'])
    
    # Write to CSV
    output_file = CSV_DIR / f"signal_{signal_id}_trades.csv"
    
    fieldnames = [
        'Open Time', 'Type', 'Lots', 'Symbol', 'Open Price', 'Close Time', 
        'Close Price', 'Commission', 'Swap', 'Net Pips', 'Net Profit', 
        'Max Profit', 'Max Pips', 'Max Loss', 'Max Loss Pips', 
        'Magic Number', 'Comment', 'Holding Time (Hours)', 'Holding Time'
    ]
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_trades)
    
    print(f"✅ Exported {len(all_trades)} trades to {output_file}")
    return output_file

def main():
    import sys
    
    if len(sys.argv) > 1:
        signal_id = sys.argv[1]
    else:
        signal_id = input("Enter signal ID: ")
    
    extract_signal_to_csv(signal_id)

if __name__ == "__main__":
    main()
