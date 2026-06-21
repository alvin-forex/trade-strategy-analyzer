#!/usr/bin/env python3
"""
TSA SET↔CSV Mapping Audit Script - Phase 1
分析 CSV 和 SET 檔案的 Comment/Magic 對照關係
"""

import os
import re
import json
import csv
from datetime import datetime
from collections import defaultdict
from pathlib import Path

# 工作目錄
WORK_DIR = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer")
DOWNLOADS_DIR = WORK_DIR / "downloads"
OUTPUT_DIR = WORK_DIR / "output"

# 確保 output 目錄存在
OUTPUT_DIR.mkdir(exist_ok=True)

# 系統交易排除列表
SYSTEM_KEYWORDS = ['Transfer', 'Deposit', 'Credit', 'Summary', 'Withdrawal', 'Balance', 'Interest', 'Correction']

# SET 檔案中的 Comment 參數名稱
COMMENT_PARAMS = [
    'comment', 'commentB', 'commentS', 'comment_B', 'comment_S',
    'CommentsBuy', 'CommentsSell', 'CommentBuy', 'CommentSell',
    'CommentDealsBuy', 'CommentDealsSell', 'CommentList'
]

# SET 檔案中的 Magic 參數名稱
MAGIC_PARAMS = [
    'magic_number', 'magic_number_B', 'magic_number_S',
    'MagicNumberB', 'MagicNumberS', 'MagicBuy', 'MagicSell',
    'MagicNumber', 'magic'
]


def is_system_transaction(comment):
    """判斷是否為系統交易"""
    if not comment:
        return False
    comment_upper = str(comment).upper()
    return any(kw.upper() in comment_upper for kw in SYSTEM_KEYWORDS)


def parse_set_file(filepath):
    """解析 SET 檔案，返回參數字典"""
    params = {}
    try:
        with open(filepath, 'r', encoding='utf-8-sig', errors='ignore') as f:
            for line in f:
                line = line.strip()
                if '=' in line:
                    key, value = line.split('=', 1)
                    params[key.strip()] = value.strip()
    except Exception as e:
        print(f"  [WARN] 無法解析 SET: {filepath}: {e}")
    return params


def extract_signal_id_from_filename(filename):
    """從檔名提取 signal ID"""
    # 格式: (10437)EA_Name...set 或 signal_10437_... 或 forex-forest-signals-page-10437.csv
    match = re.search(r'\((\d+)\)', filename)
    if match:
        return match.group(1)
    
    match = re.search(r'signal_(\d+)', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    
    match = re.search(r'forex-forest-signals-page-(\d+)', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    
    match = re.search(r'^(\d+)\.csv$', filename)
    if match:
        return match.group(1)
    
    return None


def extract_date_from_set_filename(filename):
    """從 SET 檔名提取日期 (格式: YYYY-MM-DD)"""
    # 格式: ..._YYYY-MM-DD_HH-MM-SS.set 或 ..._YYYY-MM-DD.set
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if match:
        return match.group(1)
    return None


def extract_comments_from_set(params):
    """從 SET 參數中提取所有 Comment 值"""
    comments = []
    for param in COMMENT_PARAMS:
        if param in params and params[param]:
            comments.append({
                'param': param,
                'value': params[param]
            })
    return comments


def extract_magics_from_set(params):
    """從 SET 參數中提取所有 Magic 值"""
    magics = []
    for param in MAGIC_PARAMS:
        if param in params and params[param]:
            try:
                magic_val = int(params[param])
                magics.append({
                    'param': param,
                    'value': magic_val
                })
            except ValueError:
                pass
    return magics


def normalize_comment_for_match(comment):
    """標準化 Comment 用於匹配（處理 Dragon Wave 後綴）"""
    if not comment:
        return ''
    
    # Dragon Wave 格式: Dragon Wave_XZ2 -> Dragon Wave
    match = re.match(r'(Dragon Wave)_?[A-Z]+Z\d+', comment)
    if match:
        return match.group(1)
    
    return comment.strip()


def prefix_match(comment1, comment2):
    """前綴匹配（用於 Dragon Wave 等動態 Comment）"""
    if not comment1 or not comment2:
        return False
    
    c1 = normalize_comment_for_match(comment1)
    c2 = normalize_comment_for_match(comment2)
    
    # 完全匹配
    if c1 == c2:
        return 'exact'
    
    # 前綴匹配
    if c1.startswith(c2) or c2.startswith(c1):
        return 'prefix'
    
    # Dragon Wave 特殊匹配
    if 'Dragon Wave' in c1 and 'Dragon Wave' in c2:
        return 'prefix'
    
    return None

def ea_name_match(csv_comment, set_ea_name):
    """EA 名稱匹配（當 SET 沒有 Comment 參數時）"""
    if not csv_comment or not set_ea_name:
        return None
    
    csv_norm = normalize_comment_for_match(csv_comment)
    
    # Dragon Wave: CSV comment "Dragon Wave_XZ2" matches EA name "Dragon Wave v2.10"
    if 'Dragon Wave' in csv_norm and 'Dragon Wave' in set_ea_name:
        return 'ea_name'
    
    # S10: CSV comment "S10 BUY/SELL" matches EA name "S10 v3.00"
    if 'S10' in csv_norm and 'S10' in set_ea_name:
        return 'ea_name'
    
    # SMA: CSV comment "SMA Buy/Sell" matches EA name "SMA v3.00"
    if csv_norm.upper().startswith('SMA') and 'SMA' in set_ea_name:
        return 'ea_name'
    
    # Tiger: CSV comment "Tiger_lot2_set" matches EA name containing Tiger
    if 'Tiger' in csv_norm and 'Tiger' in set_ea_name:
        return 'ea_name'
    
    # MKD: CSV comment "MKD_*" matches EA name containing MKD
    if 'MKD' in csv_norm and 'MKD' in set_ea_name:
        return 'ea_name'
    
    # Flash: CSV comment "Flash_*" matches EA name containing Flash
    if 'Flash' in csv_norm and 'Flash' in set_ea_name:
        return 'ea_name'
    
    return None


def scan_csv_files():
    """掃描所有 CSV 檔案，統計 Comment + Magic 分佈"""
    print("\n[Phase 1.1] 掃描 CSV 檔案...")
    
    csv_files = list(DOWNLOADS_DIR.glob("*.csv"))
    csv_files += list(DOWNLOADS_DIR.rglob("*.csv"))
    
    # 去重
    csv_files = list(set(csv_files))
    
    results = {
        'signals': {}
    }
    
    for csv_path in csv_files:
        signal_id = extract_signal_id_from_filename(csv_path.name)
        if not signal_id:
            continue
        
        print(f"  處理 CSV: {csv_path.name} (Signal: {signal_id})")
        
        signal_data = {
            'csv_file': csv_path.name,
            'comment_stats': defaultdict(lambda: {
                'count': 0,
                'lot_range': {'min': None, 'max': None, 'unique': []},
                'date_range': {'min': None, 'max': None},
                'magic_numbers': set()
            }),
            'total_trades': 0,
            'system_trades': 0
        }
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    signal_data['total_trades'] += 1
                    
                    comment = row.get('Comment', '').strip()
                    magic_str = row.get('Magic Number', '').strip()
                    lot_str = row.get('Lots', '').strip()
                    open_time = row.get('Open Time', '').strip()
                    
                    # 檢查是否為系統交易
                    if is_system_transaction(comment):
                        signal_data['system_trades'] += 1
                        continue
                    
                    if not comment:
                        continue
                    
                    # 解析 Magic
                    try:
                        magic = int(magic_str) if magic_str else None
                    except ValueError:
                        magic = None
                    
                    # 解析 Lot
                    try:
                        lot = float(lot_str) if lot_str else None
                    except ValueError:
                        lot = None
                    
                    # 統計
                    stats = signal_data['comment_stats'][comment]
                    stats['count'] += 1
                    
                    if magic is not None:
                        stats['magic_numbers'].add(magic)
                    
                    if lot is not None:
                        if stats['lot_range']['min'] is None or lot < stats['lot_range']['min']:
                            stats['lot_range']['min'] = lot
                        if stats['lot_range']['max'] is None or lot > stats['lot_range']['max']:
                            stats['lot_range']['max'] = lot
                        if lot not in stats['lot_range']['unique']:
                            stats['lot_range']['unique'].append(lot)
                    
                    # 日期範圍
                    if open_time:
                        try:
                            # 嘗試解析日期
                            dt_str = open_time.split(' ')[0] if ' ' in open_time else open_time
                            if stats['date_range']['min'] is None or dt_str < stats['date_range']['min']:
                                stats['date_range']['min'] = dt_str
                            if stats['date_range']['max'] is None or dt_str > stats['date_range']['max']:
                                stats['date_range']['max'] = dt_str
                        except:
                            pass
            
            # 轉換 set 為 list 以便 JSON 序列化
            for comment, stats in signal_data['comment_stats'].items():
                stats['magic_numbers'] = sorted(list(stats['magic_numbers']))
            
            results['signals'][signal_id] = signal_data
            
        except Exception as e:
            print(f"  [ERROR] 讀取 CSV 失敗: {csv_path}: {e}")
    
    # 統計摘要
    total_signals = len(results['signals'])
    multi_ea_count = 0
    no_comment_count = 0
    
    for signal_id, data in results['signals'].items():
        non_system_comments = [c for c in data['comment_stats'].keys() if not is_system_transaction(c)]
        if len(non_system_comments) > 1:
            multi_ea_count += 1
        if len(non_system_comments) == 0:
            no_comment_count += 1
    
    results['summary'] = {
        'total_signals': total_signals,
        'multi_ea_signals': multi_ea_count,
        'no_comment_signals': no_comment_count,
        'generated_at': datetime.now().isoformat()
    }
    
    print(f"  完成: {total_signals} signals, {multi_ea_count} 多 EA signals")
    
    return results


def scan_set_files():
    """掃描所有 SET 檔案，提取 Comment + Magic"""
    print("\n[Phase 1.2] 掃描 SET 檔案...")
    
    set_files = list(DOWNLOADS_DIR.glob("**/*.set"))
    set_files += list(DOWNLOADS_DIR.glob("**/*.SET"))
    
    # 去重
    set_files = list(set(set_files))
    
    results = {
        'signals': {}
    }
    
    for set_path in set_files:
        signal_id = extract_signal_id_from_filename(set_path.name)
        if not signal_id:
            continue
        
        print(f"  處理 SET: {set_path.name} (Signal: {signal_id})")
        
        params = parse_set_file(set_path)
        
        set_data = {
            'filename': set_path.name,
            'date': extract_date_from_set_filename(set_path.name),
            'ea_name': params.get('EA_NAME', ''),
            'ea_version': params.get('EA_VERSION', ''),
            'symbol': params.get('EA_SYMBOL', ''),
            'comments': extract_comments_from_set(params),
            'magics': extract_magics_from_set(params),
            'raw_params': {k: v for k, v in params.items() if any(x in k.lower() for x in ['comment', 'magic'])}
        }
        
        if signal_id not in results['signals']:
            results['signals'][signal_id] = {
                'set_versions': []
            }
        
        results['signals'][signal_id]['set_versions'].append(set_data)
    
    # 統計摘要
    total_signals = len(results['signals'])
    total_sets = sum(len(s['set_versions']) for s in results['signals'].values())
    signals_with_dates = sum(1 for s in results['signals'].values() 
                             if any(v['date'] for v in s['set_versions']))
    
    results['summary'] = {
        'total_signals': total_signals,
        'total_set_files': total_sets,
        'signals_with_dates': signals_with_dates,
        'generated_at': datetime.now().isoformat()
    }
    
    print(f"  完成: {total_signals} signals, {total_sets} SET files")
    
    return results


def cross_reference(csv_data, set_data):
    """交叉比對 CSV 和 SET 的 Comment/Magic"""
    print("\n[Phase 1.3] 交叉比對...")
    
    results = {
        'signals': {}
    }
    
    all_signal_ids = set(csv_data['signals'].keys()) | set(set_data['signals'].keys())
    
    matched_count = 0
    partial_count = 0
    no_match_count = 0
    multi_ea_count = 0
    no_set_count = 0
    
    for signal_id in sorted(all_signal_ids, key=lambda x: int(x) if x.isdigit() else 0):
        csv_signal = csv_data['signals'].get(signal_id, {})
        set_signal = set_data['signals'].get(signal_id, {})
        
        # 收集 CSV Comments (排除系統交易)
        csv_comments = {}
        for comment, stats in csv_signal.get('comment_stats', {}).items():
            if not is_system_transaction(comment):
                csv_comments[comment] = {
                    'count': stats['count'],
                    'magic_numbers': stats['magic_numbers'],
                    'lot_range': stats['lot_range'],
                    'date_range': stats['date_range']
                }
        
        # 收集 SET Comments
        set_comments = []
        set_magics = []
        set_dates = []
        
        for version in set_signal.get('set_versions', []):
            for c in version.get('comments', []):
                set_comments.append({
                    'value': c['value'],
                    'param': c['param'],
                    'date': version.get('date'),
                    'file': version.get('filename')
                })
            for m in version.get('magics', []):
                set_magics.append({
                    'value': m['value'],
                    'param': m['param'],
                    'date': version.get('date'),
                    'file': version.get('filename')
                })
            if version.get('date'):
                set_dates.append(version['date'])
        
        # 收集 SET EA Names
        set_ea_names = []
        for version in set_signal.get('set_versions', []):
            if version.get('ea_name'):
                set_ea_names.append({
                    'ea_name': version['ea_name'],
                    'date': version.get('date'),
                    'file': version.get('filename'),
                    'magic': version.get('magics', [])
                })
        
        # 判斷匹配狀態
        match_status = '❓'
        match_details = []
        
        if not csv_comments and not set_comments:
            match_status = '⚠️ 無資料'
        elif not set_comments and not set_magics and not set_ea_names:
            match_status = '❌ 無 SET'
            no_set_count += 1
        else:
            # 比對
            all_matched = True
            any_matched = False
            
            for csv_comment, csv_info in csv_comments.items():
                csv_norm = normalize_comment_for_match(csv_comment)
                csv_magics = csv_info['magic_numbers']
                
                best_match = None
                best_match_type = None
                best_match_source = None
                
                # 先嘗試 Comment 匹配
                for set_comment in set_comments:
                    match_type = prefix_match(csv_comment, set_comment['value'])
                    if match_type:
                        if not best_match or match_type == 'exact':
                            best_match = set_comment
                            best_match_type = match_type
                            best_match_source = 'comment'
                
                # 如果沒有 Comment 匹配，嘗試 EA Name 匹配
                if not best_match:
                    for ea_info in set_ea_names:
                        match_type = ea_name_match(csv_comment, ea_info['ea_name'])
                        if match_type:
                            # 檢查 Magic 是否匹配
                            set_magic_values = [m['value'] for m in ea_info.get('magic', [])]
                            magic_match = any(m in set_magic_values for m in csv_magics) if csv_magics else True
                            if magic_match or not csv_magics or not set_magic_values:
                                best_match = ea_info
                                best_match_type = match_type
                                best_match_source = 'ea_name'
                                break
                
                if best_match:
                    any_matched = True
                    match_label = '✅ 完全' if best_match_type == 'exact' else '⚠️ 前綴' if best_match_type == 'prefix' else '🔄 EA名'
                    match_details.append({
                        'csv_comment': csv_comment,
                        'set_comment': best_match.get('value') if best_match_source == 'comment' else None,
                        'set_ea_name': best_match.get('ea_name') if best_match_source == 'ea_name' else None,
                        'match_type': match_label,
                        'match_source': best_match_source,
                        'csv_magic': csv_info['magic_numbers'],
                        'csv_date_range': csv_info['date_range']
                    })
                else:
                    all_matched = False
                    match_details.append({
                        'csv_comment': csv_comment,
                        'set_comment': None,
                        'set_ea_name': None,
                        'match_type': '❌ 不匹配',
                        'match_source': None,
                        'csv_magic': csv_info['magic_numbers'],
                        'csv_date_range': csv_info['date_range']
                    })
            
            if all_matched and csv_comments:
                match_status = '✅ 完全匹配'
                matched_count += 1
            elif any_matched:
                match_status = '⚠️ 部分匹配'
                partial_count += 1
            else:
                match_status = '❌ 不匹配'
                no_match_count += 1
        
        # 判斷是否多 EA
        is_multi_ea = len(csv_comments) > 1
        if is_multi_ea:
            match_status = '🔀 多 EA ' + match_status
            multi_ea_count += 1
        
        # SET 日期覆蓋
        csv_date_range = None
        if csv_comments:
            all_dates = []
            for c_info in csv_comments.values():
                dr = c_info.get('date_range', {})
                if dr.get('min'):
                    all_dates.append(dr['min'])
                if dr.get('max'):
                    all_dates.append(dr['max'])
            if all_dates:
                csv_date_range = {'min': min(all_dates), 'max': max(all_dates)}
        
        set_date_coverage = []
        for sd in sorted(set(set_dates)):
            if csv_date_range:
                if csv_date_range['min'] <= sd <= csv_date_range['max']:
                    set_date_coverage.append({'date': sd, 'status': '✅ 區間內'})
                elif sd > csv_date_range['max']:
                    set_date_coverage.append({'date': sd, 'status': '⚠️ 晚於區間'})
                else:
                    set_date_coverage.append({'date': sd, 'status': '⚠️ 早於區間'})
            else:
                set_date_coverage.append({'date': sd, 'status': '❓ 無 CSV 日期'})
        
        results['signals'][signal_id] = {
            'match_status': match_status,
            'is_multi_ea': is_multi_ea,
            'csv_comments': csv_comments,
            'set_comments': set_comments,
            'set_magics': set_magics,
            'match_details': match_details,
            'csv_date_range': csv_date_range,
            'set_date_coverage': set_date_coverage
        }
    
    results['summary'] = {
        'total_signals': len(all_signal_ids),
        'matched': matched_count,
        'partial': partial_count,
        'no_match': no_match_count,
        'multi_ea': multi_ea_count,
        'no_set': no_set_count,
        'generated_at': datetime.now().isoformat()
    }
    
    print(f"  完成: {results['summary']}")
    
    return results


def identify_multi_ea_signals(csv_data, cross_ref):
    """識別多 EA Signals"""
    print("\n[Phase 1.4] 識別多 EA Signals...")
    
    results = {
        'signals': {}
    }
    
    for signal_id, signal_data in csv_data['signals'].items():
        # 過濾系統交易
        non_system_comments = {
            c: stats for c, stats in signal_data.get('comment_stats', {}).items()
            if not is_system_transaction(c)
        }
        
        if len(non_system_comments) > 1:
            ea_details = []
            
            for comment, stats in non_system_comments.items():
                ea_details.append({
                    'comment': comment,
                    'magic_numbers': stats['magic_numbers'],
                    'trade_count': stats['count'],
                    'lot_range': stats['lot_range'],
                    'date_range': stats['date_range']
                })
            
            # 按交易數排序
            ea_details.sort(key=lambda x: x['trade_count'], reverse=True)
            
            results['signals'][signal_id] = {
                'ea_count': len(non_system_comments),
                'total_trades': signal_data['total_trades'],
                'ea_details': ea_details,
                'csv_file': signal_data['csv_file']
            }
    
    # 排序
    results['signals'] = dict(sorted(results['signals'].items(), 
                                      key=lambda x: int(x[0]) if x[0].isdigit() else 0))
    
    results['summary'] = {
        'multi_ea_signal_count': len(results['signals']),
        'generated_at': datetime.now().isoformat()
    }
    
    # 特別檢查 #10437
    if '10437' in results['signals']:
        print(f"  Signal #10437: {results['signals']['10437']['ea_count']} EAs detected")
    
    print(f"  完成: {len(results['signals'])} multi-EA signals")
    
    return results


def generate_report(csv_data, set_data, cross_ref, multi_ea):
    """生成 Markdown 摘要報告"""
    print("\n[Phase 1.5] 生成報告...")
    
    report = []
    report.append("# TSA SET↔CSV Mapping Audit Report")
    report.append(f"\n**Generated at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 總體統計
    report.append("\n## 1. 總體統計\n")
    report.append(f"- **CSV Signals:** {csv_data['summary']['total_signals']}")
    report.append(f"- **SET Signals:** {set_data['summary']['total_signals']}")
    report.append(f"- **SET Files:** {set_data['summary']['total_set_files']}")
    report.append(f"- **Multi-EA Signals:** {multi_ea['summary']['multi_ea_signal_count']}")
    
    # 交叉比對統計
    report.append("\n## 2. 交叉比對結果\n")
    cr_summary = cross_ref['summary']
    report.append(f"| 狀態 | 數量 |")
    report.append(f"|------|------|")
    report.append(f"| ✅ 完全匹配 | {cr_summary['matched']} |")
    report.append(f"| ⚠️ 部分匹配 | {cr_summary['partial']} |")
    report.append(f"| ❌ 不匹配 | {cr_summary['no_match']} |")
    report.append(f"| ❌ 無 SET | {cr_summary['no_set']} |")
    report.append(f"| 🔀 多 EA | {cr_summary['multi_ea']} |")
    
    # 多 EA Signals 詳細表格
    report.append("\n## 3. 多 EA Signals 詳細列表\n")
    
    if multi_ea['signals']:
        for signal_id, data in multi_ea['signals'].items():
            report.append(f"\n### Signal #{signal_id}\n")
            report.append(f"- **EA Count:** {data['ea_count']}")
            report.append(f"- **Total Trades:** {data['total_trades']}")
            report.append(f"- **CSV File:** `{data['csv_file']}`")
            report.append("\n| EA Comment | Magic Numbers | Trades | Lot Range | Date Range |")
            report.append("|------------|---------------|--------|-----------|------------|")
            
            for ea in data['ea_details']:
                magics = ', '.join(map(str, ea['magic_numbers'])) if ea['magic_numbers'] else '-'
                lot_r = f"{ea['lot_range']['min']:.2f} - {ea['lot_range']['max']:.2f}" if ea['lot_range']['min'] else '-'
                date_r = f"{ea['date_range']['min']} ~ {ea['date_range']['max']}" if ea['date_range']['min'] else '-'
                report.append(f"| {ea['comment']} | {magics} | {ea['trade_count']} | {lot_r} | {date_r} |")
    else:
        report.append("無多 EA Signals")
    
    # SET 版本覆蓋缺口
    report.append("\n## 4. SET 版本覆蓋缺口清單\n")
    
    no_set_signals = []
    late_set_signals = []
    
    for signal_id, data in cross_ref['signals'].items():
        if '無 SET' in data['match_status']:
            no_set_signals.append(signal_id)
        elif data['set_date_coverage']:
            for cov in data['set_date_coverage']:
                if '晚於' in cov['status']:
                    late_set_signals.append((signal_id, cov['date']))
    
    if no_set_signals:
        report.append(f"\n### 無 SET 覆蓋 ({len(no_set_signals)} signals)\n")
        for sid in no_set_signals[:20]:  # 只顯示前 20 個
            report.append(f"- Signal #{sid}")
        if len(no_set_signals) > 20:
            report.append(f"- ... 還有 {len(no_set_signals) - 20} 個")
    
    if late_set_signals:
        report.append(f"\n### SET 晚於 CSV 區間\n")
        for sid, date in late_set_signals[:10]:
            report.append(f"- Signal #{sid}: SET date {date}")
    
    # 特別關注 #10437
    if '10437' in multi_ea['signals']:
        report.append("\n## 5. Signal #10437 詳細分析\n")
        data = multi_ea['signals']['10437']
        report.append(f"\n這個 Signal 有 **{data['ea_count']} 個 EA** 運行，共 **{data['total_trades']} 筆交易**。\n")
        
        for i, ea in enumerate(data['ea_details'], 1):
            report.append(f"\n**EA {i}: {ea['comment']}**")
            report.append(f"- Magic: {ea['magic_numbers']}")
            report.append(f"- Trades: {ea['trade_count']}")
            report.append(f"- Lot Range: {ea['lot_range']['min']:.2f} - {ea['lot_range']['max']:.2f}")
            report.append(f"- Date Range: {ea['date_range']['min']} ~ {ea['date_range']['max']}")
    
    report.append("\n---\n")
    report.append("*Report generated by TSA SET↔CSV Mapping Audit Script*")
    
    return '\n'.join(report)


def main():
    """主程式"""
    print("=" * 60)
    print("TSA SET↔CSV Mapping Audit - Phase 1")
    print("=" * 60)
    
    # Phase 1.1: 掃描 CSV
    csv_data = scan_csv_files()
    
    # Phase 1.2: 掃描 SET
    set_data = scan_set_files()
    
    # Phase 1.3: 交叉比對
    cross_ref = cross_reference(csv_data, set_data)
    
    # Phase 1.4: 識別多 EA
    multi_ea = identify_multi_ea_signals(csv_data, cross_ref)
    
    # 輸出 JSON
    print("\n[輸出 JSON 檔案]")
    
    output_files = {
        'csv_comment_magic_audit.json': csv_data,
        'set_comment_magic_audit.json': set_data,
        'set_csv_cross_reference.json': cross_ref,
        'multi_ea_signals.json': multi_ea
    }
    
    for filename, data in output_files.items():
        filepath = OUTPUT_DIR / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        print(f"  ✓ {filepath}")
    
    # 生成報告
    report = generate_report(csv_data, set_data, cross_ref, multi_ea)
    report_path = OUTPUT_DIR / "TSA_Set_Csv_Audit_Report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"  ✓ {report_path}")
    
    print("\n" + "=" * 60)
    print("Phase 1 完成!")
    print("=" * 60)


if __name__ == '__main__':
    main()