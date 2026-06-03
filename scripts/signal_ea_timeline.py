#!/usr/bin/env python3
"""
Signal EA Timeline Analyzer
從 CSV Comment 欄提取 EA 資訊，按 EA 轉變時段拆開交易表現。

用法：
  python3 signal_ea_timeline.py [signal_id]         # 分析單個 Signal
  python3 signal_ea_timeline.py --all                # 分析全部
  python3 signal_ea_timeline.py --all --html         # 輸出 HTML 報告
"""

import csv, codecs, sys, os, json, re
from collections import defaultdict
from datetime import datetime, date
import glob

CSV_DIR = os.path.join(os.path.dirname(__file__), '..', 'downloads')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'docs', 'reports')

# 忽略嘅 Comment（轉帳、提款、Credit）
IGNORE_PATTERNS = ['Transfer', 'Withdrawal', 'Credit', 'so:', 'Deposit']


def extract_ea_name(comment):
    """從 Comment 欄提取 EA 名稱"""
    if not comment:
        return 'Unknown'
    
    # 去掉後綴 (_BZ2, _CZ2 等)
    parts = comment.split('_')
    if len(parts) > 1:
        ea = parts[0].strip()
    else:
        ea = comment.strip()
    
    # 標準化 EA 名稱
    ea_lower = ea.lower().replace(' ', '')
    
    if 'dragonwave' in ea_lower or 'dragon' in ea_lower:
        # 保留版本資訊
        if 'v2.10' in ea or 'v2.1' in ea:
            return 'DragonWave v2.10'
        elif 'v2.00' in ea or 'v2.0' in ea:
            return 'DragonWave v2.00'
        else:
            return 'DragonWave'
    elif 'tiger' in ea_lower:
        if '5016' in ea:
            return '5016 Tiger'
        return 'Tiger'
    elif 's10' in ea_lower and 's100' not in ea_lower:
        return 'S10'
    elif 'flash' in ea_lower and 'gold' not in ea_lower:
        return 'Flash'
    elif 'flash' in ea_lower and 'gold' in ea_lower:
        return 'Flash GOLD'
    elif 'mkd' in ea_lower and 'pro' in ea_lower:
        return 'MKD Pro'
    elif 'mkd' in ea_lower:
        return 'MKD'
    elif 'sma' in ea_lower and 'pro' in ea_lower:
        return 'SMA Pro'
    elif 'sma' in ea_lower:
        return 'SMA'
    elif 'geminiclient' in ea_lower or 'gemini client' in ea_lower:
        return 'Gemini Client'
    elif 'geminiserver' in ea_lower or 'gemini server' in ea_lower:
        return 'Gemini Server'
    elif 'stablehelper' in ea_lower or 'stable helper' in ea_lower:
        return 'StableHelper'
    elif ea_lower.startswith('s10'):
        return 'S10'
    
    return ea


def should_skip(comment):
    """判斷是否應該跳過（轉帳等非交易記錄）"""
    for pattern in IGNORE_PATTERNS:
        if pattern.lower() in comment.lower():
            return True
    return False


def parse_date(date_str):
    """解析 DD/MM/YYYY 格式日期"""
    try:
        return datetime.strptime(date_str[:10], '%d/%m/%Y').date()
    except:
        return None


def analyze_signal(signal_id):
    """分析單個 Signal 的 EA 時間線"""
    csv_file = os.path.join(CSV_DIR, f'forex-forest-signals-page-{signal_id}.csv')
    if not os.path.exists(csv_file):
        return None
    
    trades = []
    with codecs.open(csv_file, 'r', 'utf-8-sig') as f:
        reader = csv.DictReader(f)
        for r in reader:
            open_time = r.get('Open Time', '').strip()
            pnl_str = r.get('Net Profit', '0').strip()
            sym = r.get('Symbol', '').strip()
            typ = r.get('Type', '').strip()
            comment = r.get('Comment', '').strip()
            lots_str = r.get('Lots', '0').strip()
            pips_str = r.get('Net Pips', '0').strip()
            
            if not open_time or not typ:
                continue
            
            d = parse_date(open_time)
            if not d:
                continue
            
            try:
                pnl = float(pnl_str)
                lots = float(lots_str)
                pips = float(pips_str)
            except:
                continue
            
            if should_skip(comment):
                continue
            
            ea = extract_ea_name(comment)
            
            trades.append({
                'date': d, 'pnl': pnl, 'symbol': sym, 'type': typ,
                'ea': ea, 'comment': comment, 'lots': lots, 'pips': pips
            })
    
    if not trades:
        return None
    
    trades.sort(key=lambda x: x['date'])
    
    # 1. EA Timeline — 每個 EA 首次出現日期
    ea_first = {}
    ea_last = {}
    ea_count = defaultdict(int)
    ea_pnl = defaultdict(float)
    for t in trades:
        ea = t['ea']
        if ea not in ea_first:
            ea_first[ea] = t['date']
        ea_last[ea] = t['date']
        ea_count[ea] += 1
        ea_pnl[ea] += t['pnl']
    
    # 2. 按 EA 轉變定義時段
    # 排序所有 EA 首次出現日期
    sorted_dates = sorted(set(ea_first.values()))
    
    # 建立時段：每個新 EA 出現 = 新時段開始
    periods = []
    for i, d in enumerate(sorted_dates):
        if i + 1 < len(sorted_dates):
            periods.append({
                'name': str(d),
                'start': d,
                'end': sorted_dates[i + 1],
                'ea_added': [ea for ea, first in ea_first.items() if first == d]
            })
        else:
            periods.append({
                'name': str(d),
                'start': d,
                'end': date(2030, 1, 1),
                'ea_added': [ea for ea, first in ea_first.items() if first == d]
            })
    
    # 3. 每個時段嘅交易表現
    period_stats = []
    for p in periods:
        ts = [t for t in trades if p['start'] <= t['date'] < p['end']]
        if not ts:
            continue
        
        total = len(ts)
        wins = sum(1 for t in ts if t['pnl'] > 0)
        total_pnl = sum(t['pnl'] for t in ts)
        wr = wins / total * 100 if total > 0 else 0
        avg_pnl = total_pnl / total if total > 0 else 0
        
        # Max DD
        equity, peak, max_dd = 0, 0, 0
        for t in ts:
            equity += t['pnl']
            if equity > peak:
                peak = equity
            dd = peak - equity
            if dd > max_dd:
                max_dd = dd
        
        # PF
        gross_w = sum(t['pnl'] for t in ts if t['pnl'] > 0)
        gross_l = abs(sum(t['pnl'] for t in ts if t['pnl'] <= 0))
        pf = gross_w / gross_l if gross_l > 0 else 999
        
        # EA breakdown
        ea_in_period = defaultdict(lambda: {'count': 0, 'pnl': 0, 'symbols': set()})
        for t in ts:
            ea_in_period[t['ea']]['count'] += 1
            ea_in_period[t['ea']]['pnl'] += t['pnl']
            ea_in_period[t['ea']]['symbols'].add(t['symbol'])
        
        # Symbol breakdown
        sym_in_period = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})
        for t in ts:
            sym_in_period[t['symbol']]['count'] += 1
            sym_in_period[t['symbol']]['pnl'] += t['pnl']
            if t['pnl'] > 0:
                sym_in_period[t['symbol']]['wins'] += 1
        
        period_stats.append({
            'period_name': p['name'],
            'start': p['start'],
            'end': p['end'],
            'ea_added': p['ea_added'],
            'total_trades': total,
            'wr': round(wr, 1),
            'total_pnl': round(total_pnl, 2),
            'avg_pnl': round(avg_pnl, 2),
            'max_dd': round(max_dd, 2),
            'pf': round(pf, 2),
            'ea_breakdown': {ea: {'count': v['count'], 'pnl': round(v['pnl'], 2),
                                   'symbols': sorted(v['symbols'])}
                            for ea, v in sorted(ea_in_period.items(), key=lambda x: -x[1]['count'])},
            'symbol_breakdown': {sym: {'count': v['count'], 'pnl': round(v['pnl'], 2),
                                        'wr': round(v['wins'] / v['count'] * 100, 1) if v['count'] > 0 else 0}
                                 for sym, v in sorted(sym_in_period.items(), key=lambda x: -x[1]['pnl'])}
        })
    
    # 4. 找出最佳時段（最高 PF + 最低 DD，至少 20 筆交易）
    best_period = None
    best_score = -999
    for ps in period_stats:
        if ps['total_trades'] < 10:
            continue
        # Score: PF * WR / (1 + MaxDD/TotalPnL)
        score = ps['pf'] * (ps['wr'] / 100)
        if ps['total_pnl'] > 0 and ps['max_dd'] > 0:
            score /= (1 + ps['max_dd'] / ps['total_pnl'])
        if score > best_score:
            best_score = score
            best_period = ps
    
    return {
        'signal_id': signal_id,
        'total_trades': len(trades),
        'date_range': f"{trades[0]['date']} → {trades[-1]['date']}",
        'ea_timeline': [
            {'ea': ea, 'first': str(ea_first[ea]), 'last': str(ea_last[ea]),
             'count': ea_count[ea], 'pnl': round(ea_pnl[ea], 2),
             'symbols': sorted(set(t['symbol'] for t in trades if t['ea'] == ea))}
            for ea in sorted(ea_first.keys(), key=lambda x: ea_first[x])
        ],
        'periods': period_stats,
        'best_period': best_period,
        'all_eas': sorted(set(t['ea'] for t in trades))
    }


def print_analysis(result):
    """打印分析結果"""
    if not result:
        print("  No data")
        return
    
    sid = result['signal_id']
    print(f"\n{'='*120}")
    print(f"Signal {sid} — EA Timeline Analysis")
    print(f"  Date range: {result['date_range']}")
    print(f"  Total trades: {result['total_trades']}")
    print(f"  EAs: {', '.join(result['all_eas'])}")
    
    # EA Timeline
    print(f"\n  📅 EA Timeline:")
    for e in result['ea_timeline']:
        syms = ', '.join(e['symbols'][:5])
        if len(e['symbols']) > 5:
            syms += f' +{len(e["symbols"])-5}'
        print(f"    {e['first']} → {e['last']} | {e['ea']:<20} | {e['count']:>4} trades | P&L: {e['pnl']:>10.2f} | {syms}")
    
    # Period Performance
    print(f"\n  📊 Period Performance:")
    print(f"    {'Period':<14} {'Start':<12} {'End':<12} {'#':>5} {'WR%':>6} {'P&L':>12} {'Avg':>8} {'MaxDD':>10} {'PF':>6} {'EA Added':<20}")
    print(f"    {'-'*110}")
    for ps in result['periods']:
        ea_added = ', '.join(ps['ea_added'])
        end_str = str(ps['end']) if ps['end'].year < 2030 else 'now'
        marker = ' ★' if result['best_period'] and ps['period_name'] == result['best_period']['period_name'] else ''
        print(f"    {ps['period_name']:<14} {str(ps['start']):<12} {end_str:<12} {ps['total_trades']:>5} {ps['wr']:>5.1f}% {ps['total_pnl']:>11.2f} {ps['avg_pnl']:>8.2f} {ps['max_dd']:>10.2f} {ps['pf']:>6.2f} {ea_added:<20}{marker}")
    
    # Best Period
    if result['best_period']:
        bp = result['best_period']
        print(f"\n  ⭐ Best Period: {bp['period_name']} (Score: PF={bp['pf']}, WR={bp['wr']}%, DD={bp['max_dd']})")
        print(f"    EA Breakdown:")
        for ea, info in bp['ea_breakdown'].items():
            print(f"      {ea:<20} {info['count']:>4} trades, P&L: {info['pnl']:>10.2f}, Symbols: {', '.join(info['symbols'][:5])}")
        print(f"    Top Symbols:")
        for sym, info in sorted(bp['symbol_breakdown'].items(), key=lambda x: -x[1]['pnl'])[:10]:
            print(f"      {sym:<10} {info['count']:>3} trades, WR={info['wr']:>5.1f}%, P&L={info['pnl']:>9.2f}")


def generate_html_report(all_results):
    """生成 HTML 總覽報告"""
    # This will be handled by TSA agent or main session
    pass


if __name__ == '__main__':
    if '--all' in sys.argv:
        # Find all CSV files
        csv_files = sorted(glob.glob(os.path.join(CSV_DIR, 'forex-forest-signals-page-*.csv')))
        all_results = []
        for cf in csv_files:
            sid = re.search(r'page-(\d+)\.csv', cf).group(1)
            result = analyze_signal(sid)
            if result:
                all_results.append(result)
                if '--html' not in sys.argv:
                    print_analysis(result)
        
        if '--html' in sys.argv:
            # Output JSON for HTML generation
            json.dump([r for r in all_results], sys.stdout, indent=2, default=str)
        
        # Summary
        print(f"\n{'='*120}")
        print(f"📊 Summary: {len(all_results)} signals analyzed")
        
        # Best period per signal
        print(f"\n{'Signal':>8} {'EAs':>30} {'Best Period':>14} {'WR%':>6} {'PF':>6} {'P&L':>10}")
        print("-" * 80)
        for r in sorted(all_results, key=lambda x: x['best_period']['pf'] if x['best_period'] else 0, reverse=True):
            if r['best_period']:
                bp = r['best_period']
                eas = ', '.join(r['all_eas'][:3])
                print(f"{r['signal_id']:>8} {eas:>30} {bp['period_name']:>14} {bp['wr']:>5.1f}% {bp['pf']:>6.2f} {bp['total_pnl']:>10.2f}")
    else:
        sid = sys.argv[1] if len(sys.argv) > 1 else '10437'
        result = analyze_signal(sid)
        if result:
            print_analysis(result)
            if '--json' in sys.argv:
                print("\n\nJSON:")
                print(json.dumps(result, indent=2, default=str))
