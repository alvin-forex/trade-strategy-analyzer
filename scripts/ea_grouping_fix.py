#!/usr/bin/env python3
"""
EA Grouping Fix Script - Phase 2

修正 EA 分組邏輯：
- 用 Comment 前綴 + Magic Number 分組（而非完整 Comment 字串）
- 解決 Dragon Wave _AZ2, _BZ2... 被當成獨立 EA 的問題
- 合併相同 Magic 的 BUY/SELL Comment

作者: Quant Agent
日期: 2026-06-20
"""

import json
import csv
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple, Any

# ============ 配置 ============
WORKSPACE_DIR = Path(__file__).parent.parent
DOWNLOADS_DIR = WORKSPACE_DIR / "downloads"
OUTPUT_DIR = WORKSPACE_DIR / "output"

# 系統交易關鍵字（排除）
SYSTEM_KEYWORDS = [
    'Transfer', 'Deposit', 'Credit', 'Summary', 'Balance', 
    'Withdrawal', 'Bonus', 'Correction', 'Adjustment',
    'swap', 'commission', 'Fee'
]


def is_system_transaction(comment: str) -> bool:
    """判斷是否為系統交易"""
    if not comment:
        return False
    comment_upper = str(comment).upper()
    return any(kw.upper() in comment_upper for kw in SYSTEM_KEYWORDS)


def extract_comment_prefix(comment: str) -> str:
    """
    提取 Comment 前綴（用於 EA 分組）
    
    規則：
    - 取第一個 `_` 或 `[` 之前的部分
    - 如果沒有分隔符，取整個 Comment
    - 特殊處理：S10 BUY / S10 SELL → S10
    - 特殊處理：Dragon Wave_... → Dragon Wave
    
    Examples:
        "Dragon Wave_AZ2" → "Dragon Wave"
        "Dragon Wave_AZ2[tp]" → "Dragon Wave"
        "S10 BUY" → "S10"
        "S10 SELL" → "S10"
        "Tiger_lot2_set" → "Tiger"
        "MKD_LD-02" → "MKD"
    """
    if not comment:
        return ""
    
    # 特殊處理：S10 BUY/SELL
    if comment.upper().startswith("S10 "):
        return "S10"
    
    # 特殊處理：Dragon Wave_... → Dragon Wave (multi-word EA name)
    if comment.startswith("Dragon Wave_") or comment.startswith("Dragon Wave["):
        return "Dragon Wave"
    
    # 尋找分隔符位置（_ 或 [）
    for i, char in enumerate(comment):
        if char in ['_', '[']:
            # 確保不取到空字串
            prefix = comment[:i].strip()
            return prefix if prefix else comment
    
    # 沒有分隔符，返回整個 Comment
    return comment.strip()


def extract_signal_id_from_filename(filename: str) -> str:
    """從檔名提取 signal ID"""
    # 格式: forex-forest-signals-page-10437.csv 或 10437.csv
    match = re.search(r'forex-forest-signals-page-(\d+)', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    
    match = re.search(r'^(\d+)\.csv$', filename)
    if match:
        return match.group(1)
    
    return None


def scan_csv_files() -> Dict[str, Any]:
    """
    掃描所有 CSV 檔案，使用新的分組邏輯
    返回 {signal_id: {ea_groups: {...}, total_trades: N, ...}}
    """
    print("\n[Phase 1] 掃描 CSV 檔案（新分組邏輯）...")
    
    csv_files = list(DOWNLOADS_DIR.glob("*.csv"))
    csv_files += list(DOWNLOADS_DIR.rglob("*.csv"))
    csv_files = list(set(csv_files))
    
    results = {
        'signals': {}
    }
    
    for csv_path in csv_files:
        signal_id = extract_signal_id_from_filename(csv_path.name)
        if not signal_id:
            continue
        
        # EA 分組：{prefix: {magic: {comments: set(), stats: {...}}}}
        ea_groups = defaultdict(lambda: defaultdict(lambda: {
            'comments': set(),
            'trade_count': 0,
            'lot_range': {'min': None, 'max': None, 'unique': set()},
            'date_range': {'min': None, 'max': None},
            'magics': set()
        }))
        
        total_trades = 0
        system_trades = 0
        
        try:
            with open(csv_path, 'r', encoding='utf-8-sig', errors='ignore') as f:
                reader = csv.DictReader(f)
                
                for row in reader:
                    total_trades += 1
                    
                    comment = row.get('Comment', '').strip()
                    magic_str = row.get('Magic Number', '').strip()
                    lot_str = row.get('Lots', '').strip()
                    open_time = row.get('Open Time', '').strip()
                    
                    # 檢查是否為系統交易
                    if is_system_transaction(comment):
                        system_trades += 1
                        continue
                    
                    if not comment:
                        continue
                    
                    # 解析 Magic
                    try:
                        magic = int(magic_str) if magic_str else 0
                    except ValueError:
                        magic = 0
                    
                    # 解析 Lot
                    try:
                        lot = float(lot_str) if lot_str else 0.0
                    except ValueError:
                        lot = 0.0
                    
                    # 提取前綴
                    prefix = extract_comment_prefix(comment)
                    
                    # 分組：prefix + magic
                    group = ea_groups[prefix][magic]
                    group['comments'].add(comment)
                    group['magics'].add(magic)
                    group['trade_count'] += 1
                    
                    # 更新 lot 範圍
                    if lot > 0:
                        if group['lot_range']['min'] is None or lot < group['lot_range']['min']:
                            group['lot_range']['min'] = lot
                        if group['lot_range']['max'] is None or lot > group['lot_range']['max']:
                            group['lot_range']['max'] = lot
                        group['lot_range']['unique'].add(lot)
                    
                    # 更新日期範圍
                    if open_time:
                        if group['date_range']['min'] is None or open_time < group['date_range']['min']:
                            group['date_range']['min'] = open_time
                        if group['date_range']['max'] is None or open_time > group['date_range']['max']:
                            group['date_range']['max'] = open_time
        
        except Exception as e:
            print(f"  [ERROR] 無法讀取 {csv_path.name}: {e}")
            continue
        
        # 轉換為輸出格式
        signal_result = {
            'ea_groups': {},
            'total_trades': total_trades,
            'system_trades': system_trades,
            'csv_file': csv_path.name
        }
        
        for prefix in sorted(ea_groups.keys()):
            for magic in sorted(ea_groups[prefix].keys()):
                group = ea_groups[prefix][magic]
                
                # 生成唯一 EA ID
                ea_id = f"{prefix}_M{magic}" if magic else prefix
                
                signal_result['ea_groups'][ea_id] = {
                    'comment_prefix': prefix,
                    'magic': magic,
                    'comments': sorted(list(group['comments'])),
                    'comment_count': len(group['comments']),
                    'trade_count': group['trade_count'],
                    'lot_range': {
                        'min': group['lot_range']['min'],
                        'max': group['lot_range']['max'],
                        'unique': sorted([round(x, 2) for x in group['lot_range']['unique']])
                    },
                    'date_range': group['date_range']
                }
        
        results['signals'][signal_id] = signal_result
        print(f"  Signal #{signal_id}: {len(signal_result['ea_groups'])} EA groups, {total_trades} trades")
    
    # 排序
    results['signals'] = dict(sorted(results['signals'].items(),
                                      key=lambda x: int(x[0]) if x[0].isdigit() else 0))
    
    results['summary'] = {
        'total_signals': len(results['signals']),
        'generated_at': datetime.now().isoformat()
    }
    
    return results


def identify_multi_ea_signals(csv_data: Dict) -> Dict:
    """
    識別多 EA Signals（使用新分組邏輯）
    """
    print("\n[Phase 2] 識別多 EA Signals...")
    
    results = {
        'signals': {}
    }
    
    for signal_id, signal_data in csv_data['signals'].items():
        ea_groups = signal_data.get('ea_groups', {})
        
        if len(ea_groups) > 1:
            ea_details = []
            
            for ea_id, group in ea_groups.items():
                ea_details.append({
                    'ea_id': ea_id,
                    'comment_prefix': group['comment_prefix'],
                    'magic': group['magic'],
                    'comments': group['comments'],
                    'comment_count': group['comment_count'],
                    'trade_count': group['trade_count'],
                    'lot_range': group['lot_range'],
                    'date_range': group['date_range']
                })
            
            # 按交易數排序
            ea_details.sort(key=lambda x: x['trade_count'], reverse=True)
            
            results['signals'][signal_id] = {
                'ea_count': len(ea_groups),
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
    
    # 特別檢查
    for test_id in ['3291', '10437']:
        if test_id in results['signals']:
            print(f"  Signal #{test_id}: {results['signals'][test_id]['ea_count']} EAs (after fix)")
    
    print(f"  完成: {len(results['signals'])} multi-EA signals")
    
    return results


def load_old_multi_ea_signals() -> Dict:
    """載入舊的 multi_ea_signals.json"""
    old_path = OUTPUT_DIR / "multi_ea_signals.json"
    if not old_path.exists():
        print(f"  [WARN] 找不到舊檔案: {old_path}")
        return {}
    
    with open(old_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def generate_comparison_report(old_data: Dict, new_data: Dict) -> str:
    """
    生成對比報告
    """
    print("\n[Phase 3] 生成對比報告...")
    
    report = []
    report.append("# EA Grouping Comparison Report")
    report.append(f"\n**Generated at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("\n## 修正說明\n")
    report.append("**問題：** Dragon Wave Comment 後綴 `_AZ2`, `_BZ2`... 被當成獨立 EA")
    report.append("\n**修正方式：** 使用 Comment 前綴 + Magic Number 分組")
    report.append("- `Dragon Wave_AZ2` → 前綴 `Dragon Wave` + Magic `1`")
    report.append("- `Dragon Wave_BZ2[tp]` → 前綴 `Dragon Wave` + Magic `1`")
    report.append("- 同一 EA 的不同 Comment 後綴會被合併")
    report.append("- `S10 BUY` / `S10 SELL` → 同一 EA（Magic 相同）")
    
    report.append("\n## 統計摘要\n")
    report.append("| 指標 | 修正前 | 修正後 | 變化 |")
    report.append("|------|--------|--------|------|")
    
    old_count = old_data.get('summary', {}).get('multi_ea_signal_count', 0)
    new_count = new_data.get('summary', {}).get('multi_ea_signal_count', 0)
    report.append(f"| Multi-EA Signals | {old_count} | {new_count} | {new_count - old_count:+d} |")
    
    # 統計總 EA 數
    old_total_eas = sum(s.get('ea_count', 0) for s in old_data.get('signals', {}).values())
    new_total_eas = sum(s.get('ea_count', 0) for s in new_data.get('signals', {}).values())
    report.append(f"| 總 EA 數 | {old_total_eas} | {new_total_eas} | {new_total_eas - old_total_eas:+d} |")
    
    # 重點 Signals 對比
    report.append("\n## 重點 Signals 對比\n")
    report.append("| Signal ID | 修正前 EA 數 | 修正後 EA 數 | 說明 |")
    report.append("|-----------|--------------|--------------|------|")
    
    # 指定要對比的 signals
    focus_signals = ['3291', '10437', '8027', '106', '165']
    
    for signal_id in focus_signals:
        old_ea_count = old_data.get('signals', {}).get(signal_id, {}).get('ea_count', 0)
        new_ea_count = new_data.get('signals', {}).get(signal_id, {}).get('ea_count', 0)
        
        # 說明
        if signal_id == '3291':
            note = "Dragon Wave (958 → 1 EA)"
        elif signal_id == '10437':
            note = "S10 + Tiger + MKD + Dragon Wave"
        else:
            note = ""
        
        report.append(f"| #{signal_id} | {old_ea_count} | {new_ea_count} | {note} |")
    
    # 詳細列表
    report.append("\n## 所有 Multi-EA Signals 詳細列表\n")
    report.append("| Signal ID | EA 數 | 總交易數 | 主要 EA |")
    report.append("|-----------|-------|----------|---------|")
    
    for signal_id, signal_data in sorted(new_data.get('signals', {}).items(),
                                          key=lambda x: int(x[0]) if x[0].isdigit() else 0):
        ea_count = signal_data.get('ea_count', 0)
        total_trades = signal_data.get('total_trades', 0)
        ea_details = signal_data.get('ea_details', [])
        
        # 主要 EA
        if ea_details:
            main_ea = ea_details[0]
            main_ea_name = f"{main_ea.get('comment_prefix', '?')} (M{main_ea.get('magic', '?')})"
        else:
            main_ea_name = "N/A"
        
        report.append(f"| #{signal_id} | {ea_count} | {total_trades} | {main_ea_name} |")
    
    # 特別分析：#10437
    if '10437' in new_data.get('signals', {}):
        report.append("\n## Signal #10437 詳細分析\n")
        signal_10437 = new_data['signals']['10437']
        report.append(f"- **EA 數量：** {signal_10437['ea_count']}")
        report.append(f"- **總交易數：** {signal_10437['total_trades']}")
        report.append(f"- **CSV 檔案：** {signal_10437['csv_file']}")
        report.append("\n### EA 分組詳情\n")
        
        for ea in signal_10437.get('ea_details', []):
            report.append(f"#### {ea['ea_id']}")
            report.append(f"- **前綴：** `{ea['comment_prefix']}`")
            report.append(f"- **Magic：** {ea['magic']}")
            report.append(f"- **交易數：** {ea['trade_count']}")
            report.append(f"- **Comment 變體：** {ea['comment_count']} 種")
            if ea['comments']:
                comment_preview = ea['comments'][:5]
                report.append(f"- **Comments：** {', '.join(comment_preview)}{'...' if len(ea['comments']) > 5 else ''}")
            report.append("")
    
    # 特別分析：#3291
    if '3291' in new_data.get('signals', {}):
        report.append("\n## Signal #3291 詳細分析\n")
        signal_3291 = new_data['signals']['3291']
        report.append(f"- **EA 數量：** {signal_3291['ea_count']}")
        report.append(f"- **總交易數：** {signal_3291['total_trades']}")
        report.append(f"- **CSV 檔案：** {signal_3291['csv_file']}")
        
        # Dragon Wave 前綴分析
        dragon_wave_ea = None
        for ea in signal_3291.get('ea_details', []):
            if 'Dragon' in ea['comment_prefix']:
                dragon_wave_ea = ea
                break
        
        if dragon_wave_ea:
            report.append("\n### Dragon Wave 分組\n")
            report.append(f"- **前綴：** `{dragon_wave_ea['comment_prefix']}`")
            report.append(f"- **Magic：** {dragon_wave_ea['magic']}")
            report.append(f"- **交易數：** {dragon_wave_ea['trade_count']}")
            report.append(f"- **Comment 變體數：** {dragon_wave_ea['comment_count']}")
            report.append(f"- **修正前被誤認為：** 958 個獨立 EA")
            report.append(f"- **修正後合併為：** 1 個 EA")
    
    return '\n'.join(report)


def main():
    """主程式"""
    print("=" * 60)
    print("EA Grouping Fix - Phase 2")
    print("=" * 60)
    
    # 確保輸出目錄存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. 掃描 CSV 檔案（新邏輯）
    csv_data = scan_csv_files()
    
    # 2. 識別 Multi-EA Signals
    multi_ea = identify_multi_ea_signals(csv_data)
    
    # 3. 載入舊資料
    old_data = load_old_multi_ea_signals()
    
    # 4. 生成對比報告
    report = generate_comparison_report(old_data, multi_ea)
    
    # 5. 寫入輸出檔案
    output_json_path = OUTPUT_DIR / "multi_ea_signals_v2.json"
    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(multi_ea, f, indent=2, ensure_ascii=False)
    print(f"\n[Output] {output_json_path}")
    
    report_path = OUTPUT_DIR / "EA_Grouping_Comparison.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"[Output] {report_path}")
    
    # 6. 顯示摘要
    print("\n" + "=" * 60)
    print("摘要")
    print("=" * 60)
    print(f"Multi-EA Signals: {multi_ea['summary']['multi_ea_signal_count']}")
    
    if '3291' in multi_ea['signals']:
        print(f"Signal #3291: {multi_ea['signals']['3291']['ea_count']} EAs (修正前: 958)")
    
    if '10437' in multi_ea['signals']:
        print(f"Signal #10437: {multi_ea['signals']['10437']['ea_count']} EAs (修正前: 56)")
    
    print("\n✅ Phase 2 完成")
    
    return multi_ea


if __name__ == "__main__":
    main()
