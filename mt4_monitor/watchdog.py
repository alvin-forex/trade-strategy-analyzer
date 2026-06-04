#!/usr/bin/env python3
"""
MT4 Monitor Watchdog (Token-Free Pre-Filter)
=============================================
Runs every 5 minutes via cron (no LLM, 0 tokens).
Only when new trade events are detected, outputs a signal for the agent.

Exit codes:
  0 = no new events (agent should NO_REPLY)
  1 = new events found (agent should process and notify)
"""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

MT4_BASE = Path("/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal")
STATE_FILE = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer/mt4_monitor/watchdog_state.json")
EVENTS_BUFFER = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer/mt4_monitor/pending_events.json")


def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except:
            pass
    return {"processed": {}}  # {terminal_account: last_timestamp}


def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2))


def read_new_events(csv_path, last_ts_str=None):
    events = []
    if not csv_path.exists():
        return events

    try:
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                ts_str = row.get('timestamp', '').strip()
                if not ts_str:
                    continue
                for fmt in ['%Y.%m.%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                    try:
                        ts = datetime.strptime(ts_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    continue

                if last_ts_str:
                    try:
                        last_dt = datetime.strptime(last_ts_str, '%Y-%m-%d %H:%M:%S')
                        if ts <= last_dt:
                            continue
                    except:
                        pass

                evt_type = row.get('event_type', '')
                if evt_type not in ('NEW_ORDER', 'CLOSE_ORDER'):
                    continue

                events.append({
                    'timestamp': ts_str,
                    'account': row.get('account', ''),
                    'event_type': evt_type,
                    'symbol': row.get('symbol', ''),
                    'ticket': row.get('ticket', ''),
                    'order_type': row.get('order_type', ''),
                    'lots': row.get('lots', ''),
                    'price': row.get('price', ''),
                    'sl': row.get('sl', ''),
                    'tp': row.get('tp', ''),
                    'magic': row.get('magic', ''),
                    'balance': row.get('balance', ''),
                    'equity': row.get('equity', ''),
                    'comment': row.get('comment', ''),
                    'indicators': row.get('indicators', ''),
                    'extra': row.get('extra', ''),
                })
    except Exception as e:
        print(f"Error reading {csv_path}: {e}", file=sys.stderr)

    return events


def main():
    state = load_state()
    all_events = []

    # Scan all terminals
    if not MT4_BASE.exists():
        sys.exit(0)

    for term_dir in MT4_BASE.iterdir():
        if not term_dir.is_dir() or len(term_dir.name) != 32:
            continue
        files_dir = term_dir / "MQL4" / "Files"
        if not files_dir.exists():
            continue

        for csv_file in files_dir.glob("monitor_events_*.csv"):
            key = csv_file.name  # unique per terminal+account
            last_ts = state["processed"].get(key)
            events = read_new_events(csv_file, last_ts)
            all_events.extend(events)

            if events:
                latest = max(e['timestamp'] for e in events)
                state["processed"][key] = latest

    if not all_events:
        save_state(state)
        sys.exit(0)  # No events, agent NO_REPLY

    # Save pending events for agent
    EVENTS_BUFFER.parent.mkdir(parents=True, exist_ok=True)
    EVENTS_BUFFER.write_text(json.dumps(all_events, indent=2, ensure_ascii=False))

    # Save updated state
    save_state(state)

    # Print summary for agent
    new = sum(1 for e in all_events if e['event_type'] == 'NEW_ORDER')
    closed = sum(1 for e in all_events if e['event_type'] == 'CLOSE_ORDER')
    print(f"EVENTS_FOUND:{len(all_events)} new={new} closed={closed}")
    sys.exit(1)  # Signal: events found


if __name__ == '__main__':
    main()
