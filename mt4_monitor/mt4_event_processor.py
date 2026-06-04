#!/usr/bin/env python3
"""
MT4 Account Event Processor
=============================
Reads monitor_events CSV from MT4 Terminal, processes new trade events,
performs analysis (indicators + TSA context), and outputs notification payload.

Called by OpenClaw cron every 30 seconds.

Usage:
  python3 mt4_event_processor.py --terminal-dir <path> [--whatsapp] [--telegram]
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ─── Config ────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_DIR = SCRIPT_DIR.parent.parent  # ~/.openclaw/workspace/
TSA_DIR = WORKSPACE_DIR / "trade_strategy_analyzer"
PROCESSED_FILE = SCRIPT_DIR / "last_processed_event.json"

# MT4 Terminal directories (will be overridden by args)
MT4_BASE = Path("/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal")

def get_terminal_paths():
    """Get all active MT4 terminal paths"""
    terminals = {}
    if MT4_BASE.exists():
        for d in MT4_BASE.iterdir():
            if d.is_dir() and len(d.name) == 32:
                mq4 = d / "MQL4" / "Files"
                if mq4.exists():
                    # Try to get label from origin.txt
                    origin = ""
                    origin_file = d / "origin.txt"
                    if origin_file.exists():
                        try:
                            origin = origin_file.read_text(encoding='utf-16-le', errors='ignore').strip()
                        except:
                            pass
                    terminals[d.name] = {
                        'path': mq4,
                        'origin': origin,
                        'id': d.name[:8]
                    }
    return terminals

def load_last_processed():
    """Load last processed event timestamp per terminal"""
    if PROCESSED_FILE.exists():
        try:
            return json.loads(PROCESSED_FILE.read_text())
        except:
            return {}
    return {}

def save_last_processed(data):
    """Save last processed event timestamp"""
    PROCESSED_FILE.write_text(json.dumps(data, indent=2))

def read_new_events(csv_path, last_ts=None):
    """Read new events from monitor CSV since last_ts"""
    events = []
    if not csv_path.exists():
        return events
    
    try:
        with open(csv_path, 'r', encoding='utf-8', errors='replace') as f:
            reader = csv.DictReader(f, delimiter='\t')
            for row in reader:
                try:
                    ts_str = row.get('timestamp', '').strip()
                    if not ts_str:
                        continue
                    # Parse DD/MM/YYYY or YYYY.MM.DD
                    for fmt in ['%Y.%m.%d %H:%M:%S', '%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S']:
                        try:
                            ts = datetime.strptime(ts_str, fmt)
                            break
                        except ValueError:
                            continue
                    else:
                        continue
                    
                    if last_ts:
                        try:
                            last_dt = datetime.strptime(last_ts, '%Y-%m-%d %H:%M:%S')
                            if ts <= last_dt:
                                continue
                        except:
                            pass
                    
                    events.append({
                        'timestamp': ts_str,
                        'ts_parsed': ts,
                        'account': row.get('account', ''),
                        'event_type': row.get('event_type', ''),
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
                    continue
    except Exception as e:
        print(f"Error reading {csv_path}: {e}")
    
    return events

def parse_indicators(ind_str):
    """Parse indicator string from EA into structured data"""
    if not ind_str:
        return {}
    
    result = {}
    
    # Parse MA trend
    import re
    ma_match = re.search(r'Trend=(\w+)', ind_str)
    if ma_match:
        result['ma_trend'] = ma_match.group(1)
    
    # Parse RSI
    rsi_match = re.search(r'RSI\[([0-9.]+),(\w+)', ind_str)
    if rsi_match:
        result['rsi'] = float(rsi_match.group(1))
        result['rsi_zone'] = rsi_match.group(2)
    
    # Parse MACD
    macd_match = re.search(r'MACD\[.*?(\w+)\]', ind_str)
    if macd_match:
        result['macd_direction'] = macd_match.group(1)
    
    # Parse BB
    bb_match = re.search(r'BB\[.*?(ABOVE_UPPER|BELOW_LOWER|MID)', ind_str)
    if bb_match:
        result['bb_position'] = bb_match.group(1)
    
    # Parse ADX
    adx_match = re.search(r'ADX\[([0-9.]+).*?(UP_TREND|DOWN_TREND|NO_TREND)', ind_str)
    if adx_match:
        result['adx'] = float(adx_match.group(1))
        result['trend'] = adx_match.group(2)
    
    # Parse Stochastic
    stoch_match = re.search(r'STOCH\[.*?(\w+)\]', ind_str)
    if stoch_match:
        result['stoch_zone'] = stoch_match.group(1)
    
    return result

def analyze_trade_event(event):
    """Generate analysis summary for a trade event"""
    analysis = {
        'symbol': event['symbol'],
        'direction': event['order_type'],
        'lots': event['lots'],
        'price': event['price'],
        'comment': event['comment'],
        'account': event['account'],
        'balance': event['balance'],
        'equity': event['equity'],
    }
    
    # Parse indicators
    indicators = parse_indicators(event.get('indicators', ''))
    analysis['indicators'] = indicators
    
    # Generate reasoning based on indicators
    reasons = []
    
    if event['event_type'] == 'NEW_ORDER':
        direction = event['order_type']
        symbol = event['symbol']
        
        # MA trend
        ma_trend = indicators.get('ma_trend', '')
        if ma_trend == 'BULLISH' and direction == 'BUY':
            reasons.append(f"📈 EMA 均線多頭排列支持買入")
        elif ma_trend == 'BEARISH' and direction == 'SELL':
            reasons.append(f"📉 EMA 均線空頭排列支持賣出")
        elif ma_trend == 'BULLISH' and direction == 'SELL':
            reasons.append(f"⚠️ 逆均線趨勢做空（可能逆勢交易）")
        elif ma_trend == 'BEARISH' and direction == 'BUY':
            reasons.append(f"⚠️ 逆均線趨勢做多（可能逆勢交易）")
        
        # RSI
        rsi = indicators.get('rsi', 0)
        rsi_zone = indicators.get('rsi_zone', '')
        if rsi_zone == 'OVERSOLD' and direction == 'BUY':
            reasons.append(f"📊 RSI={rsi:.0f} 超賣區反彈買入")
        elif rsi_zone == 'OVERBOUGHT' and direction == 'SELL':
            reasons.append(f"📊 RSI={rsi:.0f} 超買區回落做空")
        elif rsi_zone == 'OVERBOUGHT' and direction == 'BUY':
            reasons.append(f"⚠️ RSI={rsi:.0f} 超買區仍追多")
        elif rsi_zone == 'OVERSOLD' and direction == 'SELL':
            reasons.append(f"⚠️ RSI={rsi:.0f} 超賣區仍追空")
        
        # MACD
        macd_dir = indicators.get('macd_direction', '')
        if macd_dir == 'BULL' and direction == 'BUY':
            reasons.append(f"✅ MACD 金叉/多頭確認")
        elif macd_dir == 'BEAR' and direction == 'SELL':
            reasons.append(f"✅ MACD 死叉/空頭確認")
        
        # ADX trend strength
        trend = indicators.get('trend', '')
        adx = indicators.get('adx', 0)
        if trend == 'UP_TREND' and direction == 'BUY':
            reasons.append(f"💪 ADX={adx:.0f} 強上升趨勢")
        elif trend == 'DOWN_TREND' and direction == 'SELL':
            reasons.append(f"💪 ADX={adx:.0f} 強下降趨勢")
        elif trend == 'NO_TREND':
            reasons.append(f"🔄 ADX={adx:.0f} 無明顯趨勢（可能震盪策略）")
        
        # BB
        bb_pos = indicators.get('bb_position', '')
        if bb_pos == 'BELOW_LOWER' and direction == 'BUY':
            reasons.append(f"📍 布林帶下軌反彈做多")
        elif bb_pos == 'ABOVE_UPPER' and direction == 'SELL':
            reasons.append(f"📍 布林帶上軌回落做空")
        
        # Stochastic
        stoch = indicators.get('stoch_zone', '')
        if stoch == 'OVERSOLD' and direction == 'BUY':
            reasons.append(f"🔷 隨機指標超賣反彈信號")
        elif stoch == 'OVERBOUGHT' and direction == 'SELL':
            reasons.append(f"🔷 隨機指標超買回落信號")
        
        # EA identification from comment
        comment = event.get('comment', '')
        if 'TSR' in comment or 'Tiger' in comment:
            reasons.append(f"🐯 EA: TSR/Tiger 策略")
        elif 'Dragon Wave' in comment or 'DW' in comment:
            reasons.append(f"🐉 EA: Dragon Wave 策略")
        elif 'MKD' in comment:
            reasons.append(f"🎯 EA: MKD 策略")
        elif 'SMA' in comment:
            reasons.append(f"📐 EA: SMA 策略")
        elif 'Flash' in comment:
            reasons.append(f"⚡ EA: Flash 策略")
        elif 'Gemini' in comment:
            reasons.append(f"♊ EA: Gemini 策略")
    
    elif event['event_type'] == 'CLOSE_ORDER':
        reasons.append(f"💰 平倉結果：{event.get('extra', '')}")
    
    analysis['reasons'] = reasons
    return analysis

def format_whatsapp_message(event, analysis):
    """Format WhatsApp notification message"""
    evt = event['event_type']
    symbol = event['symbol']
    direction = event['order_type']
    lots = event['lots']
    price = event['price']
    account = event['account']
    balance = event['balance']
    equity = event['equity']
    
    if evt == 'NEW_ORDER':
        emoji = "🟢" if direction == "BUY" else "🔴"
        header = f"{emoji} 新訂單偵測"
    elif evt == 'CLOSE_ORDER':
        extra = event.get('extra', '')
        is_profit = '+' in extra and not extra.startswith('-')
        emoji = "💰" if is_profit else "💔"
        header = f"{emoji} 平倉通知"
    elif evt == 'STARTUP':
        return f"🟡 MT4 帳戶監察已啟動\n📋 帳戶：{account}\n💰 餘額：${balance} | 淨值：${equity}"
    else:
        return None
    
    msg = f"{header}\n"
    msg += f"━━━━━━━━━━━━━━━━━\n"
    msg += f"📋 帳戶：{account}\n"
    msg += f"💱 貨幣對：{symbol}\n"
    msg += f"📊 方向：{direction} | 手數：{lots}\n"
    msg += f"💲 價格：{price}\n"
    
    if evt == 'NEW_ORDER':
        sl = event.get('sl', '0')
        tp = event.get('tp', '0')
        if sl and sl != '0.00000':
            msg += f"🛡️ SL：{sl}\n"
        if tp and tp != '0.00000':
            msg += f"🎯 TP：{tp}\n"
        msg += f"📝 Comment：{event.get('comment', '-')}\n"
    
    if evt == 'CLOSE_ORDER':
        msg += f"📋 {event.get('extra', '')}\n"
    
    msg += f"💰 餘額：${balance} | 淨值：${equity}\n"
    
    # Analysis
    reasons = analysis.get('reasons', [])
    if reasons:
        msg += f"\n🧠 分析：\n"
        for r in reasons:
            msg += f"  {r}\n"
    
    return msg

def main():
    parser = argparse.ArgumentParser(description='MT4 Event Processor')
    parser.add_argument('--terminal', default=None, help='Specific terminal ID to monitor')
    parser.add_argument('--whatsapp', action='store_true', help='Output WhatsApp format')
    parser.add_argument('--json', action='store_true', help='Output JSON format')
    parser.add_argument('--mark-processed', action='store_true', help='Mark events as processed')
    args = parser.parse_args()
    
    terminals = get_terminal_paths()
    if not terminals:
        print("No MT4 terminals found")
        return
    
    last_processed = load_last_processed()
    all_new_events = []
    
    for tid, tinfo in terminals.items():
        if args.terminal and tid != args.terminal and not tid.startswith(args.terminal):
            continue
        
        # Look for event CSV files
        files_path = tinfo['path']
        for csv_file in files_path.glob("monitor_events_*.csv"):
            # Extract account number from filename
            account_num = csv_file.stem.replace("monitor_events_", "")
            last_key = f"{tid}_{account_num}"
            last_ts = last_processed.get(last_key)
            
            events = read_new_events(csv_file, last_ts)
            
            for event in events:
                event['terminal_id'] = tid
                event['terminal_origin'] = tinfo['origin']
                all_new_events.append(event)
            
            # Update last processed
            if events:
                latest = max(e['ts_parsed'] for e in events)
                last_processed[last_key] = latest.strftime('%Y-%m-%d %H:%M:%S')
    
    if not all_new_events:
        if args.json:
            print(json.dumps({"new_events": 0, "events": []}))
        return
    
    # Filter: only process trade events (not STARTUP/SHUTDOWN)
    trade_events = [e for e in all_new_events if e['event_type'] in ('NEW_ORDER', 'CLOSE_ORDER')]
    system_events = [e for e in all_new_events if e['event_type'] in ('STARTUP', 'SHUTDOWN')]
    
    output = {
        'new_events': len(all_new_events),
        'trade_events': len(trade_events),
        'system_events': len(system_events),
        'events': [],
        'messages': []
    }
    
    # Process trade events
    for event in trade_events:
        analysis = analyze_trade_event(event)
        msg = format_whatsapp_message(event, analysis)
        output['events'].append({
            'event': {k: v for k, v in event.items() if k != 'ts_parsed'},
            'analysis': analysis,
        })
        if msg:
            output['messages'].append(msg)
    
    # Process system events
    for event in system_events:
        msg = format_whatsapp_message(event, {})
        if msg:
            output['messages'].append(msg)
    
    # Output
    if args.json:
        print(json.dumps(output, indent=2, ensure_ascii=False, default=str))
    else:
        for msg in output['messages']:
            print(msg)
            print("---")
    
    # Mark as processed
    if args.mark_processed:
        save_last_processed(last_processed)
    
    return output

if __name__ == '__main__':
    main()
