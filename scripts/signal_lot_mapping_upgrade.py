#!/usr/bin/env python3
"""
Signal Lot Mapping Upgrade Script - Phase 2

升級 signal_lot_mapping.json 為多 EA、多版本結構

新結構：
{
  "10437": {
    "eas": [
      {
        "ea_id": "dragon_wave",
        "comment_prefix": "Dragon Wave",
        "magic": 1,
        "set_versions": [
          {
            "date": "2026-04-09",
            "set_file": "(10437)Dragon Wave v2.10AUDCAD_H1_Both_2026-04-09_02-45-30.set",
            "lot_layers": [[1, 0.1], [2, 0.25], ...]
          }
        ]
      },
      {
        "ea_id": "s10",
        "comment_prefix": "S10",
        "magic": 88,
        "set_versions": []
      }
    ]
  }
}

作者: Quant Agent
日期: 2026-06-20
"""

import json
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional
from collections import defaultdict

# ============ 配置 ============
WORKSPACE_DIR = Path(__file__).parent.parent
DOWNLOADS_DIR = WORKSPACE_DIR / "downloads"
OUTPUT_DIR = WORKSPACE_DIR / "output"

# Comment 參數名稱（SET 檔案中的）
COMMENT_PARAMS = ['Comment', 'CommentBuy', 'CommentSell', 'TradeComment']

# EA type mapping
EA_TYPE_MAP = {
    'Dragon Wave': 'DW',
    'Dragon': 'DW',
    'S10': 'S10',
    'Tiger': 'TIGER',
    'MKD': 'MKD',
    'Flash': 'FLASH',
    'SMA': 'SMA',
    'MOON': 'MOON',
}


def parse_set_file(filepath: Path) -> Dict[str, Any]:
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


def extract_lot_layers(params: Dict[str, str]) -> List[List[float]]:
    """
    從 SET 參數中提取 lot layers
    
    常見格式：
    - LotLayer1, LotLayer2, ... 或
    - Lot1, Lot2, ... 或
    - LotSize1, LotSize2, ...
    - Lots + LotMul (幾何倍數, Dragon Wave 格式)
    """
    layers = []
    
    # 嘗試 LotLayer 格式
    for i in range(1, 20):
        key = f'LotLayer{i}'
        if key in params:
            try:
                lot = float(params[key])
                layers.append([i, lot])
            except ValueError:
                pass
    
    if layers:
        return layers
    
    # 嘗試 Lot 格式
    for i in range(1, 20):
        key = f'Lot{i}'
        if key in params:
            try:
                lot = float(params[key])
                layers.append([i, lot])
            except ValueError:
                pass
    
    if layers:
        return layers
    
    # 嘗試 LotSize 格式
    for i in range(1, 20):
        key = f'LotSize{i}'
        if key in params:
            try:
                lot = float(params[key])
                layers.append([i, lot])
            except ValueError:
                pass
    
    if layers:
        return layers
    
    # 嘗試 Lots + LotMul (幾何倍數, Dragon Wave 風格)
    if 'Lots' in params and 'LotMul' in params:
        try:
            base_lot = float(params['Lots'])
            multiplier = float(params['LotMul'])
            # 生成最多 20 層
            for i in range(1, 21):
                lot = round(base_lot * (multiplier ** (i - 1)), 6)
                layers.append([i, lot])
        except ValueError:
            pass
    
    return layers
    
    # 嘗試固定 Lot 值（只有一個 Lot 參數）
    if 'Lot' in params and not layers:
        try:
            lot = float(params['Lot'])
            if lot > 0:
                layers = [[1, lot]]
        except ValueError:
            pass
    
    return layers


def extract_magic_from_set(params: Dict[str, str]) -> Optional[int]:
    """從 SET 參數中提取 Magic Number"""
    magic_keys = ['MagicNumber', 'Magic', 'MN', 'magic_number', 'magic']
    for key in magic_keys:
        if key in params:
            try:
                return int(params[key])
            except ValueError:
                pass
    return None


def extract_comments_from_set(params: Dict[str, str]) -> List[str]:
    """從 SET 參數中提取 Comment 值"""
    comments = []
    for param in COMMENT_PARAMS:
        if param in params and params[param]:
            comments.append(params[param])
    return comments


def extract_date_from_set_filename(filename: str) -> Optional[str]:
    """從 SET 檔名提取日期 (YYYY-MM-DD)"""
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    if match:
        return match.group(1)
    return None


def extract_signal_id_from_filename(filename: str) -> Optional[str]:
    """從檔名提取 signal ID"""
    match = re.search(r'\((\d+)\)', filename)
    if match:
        return match.group(1)
    
    match = re.search(r'signal_(\d+)', filename, re.IGNORECASE)
    if match:
        return match.group(1)
    
    return None


def identify_ea_from_set_filename(filename: str) -> Optional[str]:
    """
    從 SET 檔名識別 EA 類型
    
    Examples:
        "(10437)Dragon Wave v2.10AUDCAD..." → "dragon_wave"
        "(10437)S10 v3.00GBPJPY..." → "s10"
    """
    # 移除 signal ID 部分
    name = re.sub(r'^\(\d+\)', '', filename)
    
    # 常見 EA 名稱
    ea_patterns = [
        (r'Dragon Wave', 'dragon_wave'),
        (r'DragonWave', 'dragon_wave'),
        (r'S10', 's10'),
        (r'Tiger', 'tiger'),
        (r'MKD', 'mkd'),
        (r'Flash', 'flash'),
        (r'SMA', 'sma'),
        (r'MOON', 'moon'),
        (r'Gemini', 'gemini'),
    ]
    
    for pattern, ea_id in ea_patterns:
        if re.search(pattern, name, re.IGNORECASE):
            return ea_id
    
    return None


def extract_comment_prefix(comment: str) -> str:
    """提取 Comment 前綴"""
    if not comment:
        return ""
    
    # 特殊處理
    if comment.upper().startswith("S10 "):
        return "S10"
    if comment.startswith("Dragon Wave_") or comment.startswith("Dragon Wave["):
        return "Dragon Wave"
    
    # 尋找分隔符
    for i, char in enumerate(comment):
        if char in ['_', '[']:
            prefix = comment[:i].strip()
            return prefix if prefix else comment
    
    return comment.strip()


def load_old_mapping() -> Dict:
    """載入舊的 signal_lot_mapping.json"""
    old_path = WORKSPACE_DIR / "signal_lot_mapping.json"
    if not old_path.exists():
        print(f"  [INFO] 舊檔案不存在: {old_path}")
        return {}
    
    with open(old_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_multi_ea_signals() -> Dict:
    """載入 multi_ea_signals_v2.json"""
    path = OUTPUT_DIR / "multi_ea_signals_v2.json"
    if not path.exists():
        print(f"  [WARN] 找不到 multi_ea_signals_v2.json")
        return {}
    
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def scan_set_files() -> Dict[str, List[Dict]]:
    """
    掃描所有 SET 檔案，按 signal ID 分組
    返回 {signal_id: [{set_file_info}, ...]}
    """
    print("\n[Phase 1] 掃描 SET 檔案...")
    
    set_files = list(DOWNLOADS_DIR.glob("**/*.set"))
    set_files += list(DOWNLOADS_DIR.glob("**/*.SET"))
    set_files = list(set(set_files))
    
    results = defaultdict(list)
    
    for set_path in set_files:
        signal_id = extract_signal_id_from_filename(set_path.name)
        if not signal_id:
            continue
        
        # 解析 SET 檔案
        params = parse_set_file(set_path)
        lot_layers = extract_lot_layers(params)
        magic = extract_magic_from_set(params)
        comments = extract_comments_from_set(params)
        date = extract_date_from_set_filename(set_path.name)
        ea_id = identify_ea_from_set_filename(set_path.name)
        
        results[signal_id].append({
            'path': str(set_path.relative_to(WORKSPACE_DIR)),
            'filename': set_path.name,
            'date': date,
            'ea_id': ea_id,
            'magic': magic,
            'comments': comments,
            'lot_layers': lot_layers
        })
    
    print(f"  完成: {len(results)} signals with SET files, {len(set_files)} total SET files")
    
    return dict(results)


def upgrade_signal_lot_mapping(old_mapping: Dict, multi_ea: Dict, set_data: Dict) -> Dict:
    """
    升級 signal_lot_mapping 結構
    """
    print("\n[Phase 2] 升級 signal_lot_mapping 結構...")
    
    results = {}
    
    # 合併所有 signal IDs
    all_signal_ids = set(old_mapping.keys())
    all_signal_ids.update(set_data.keys())
    all_signal_ids.update(multi_ea.get('signals', {}).keys())
    
    for signal_id in sorted(all_signal_ids, key=lambda x: int(x) if x.isdigit() else 0):
        # 舊結構資料
        old_data = old_mapping.get(signal_id, {})
        
        # Multi-EA 資料
        multi_ea_data = multi_ea.get('signals', {}).get(signal_id, {})
        
        # SET 檔案資料
        set_files = set_data.get(signal_id, [])
        
        # 建立 EA 分組
        ea_groups = {}
        
        # 從 multi_ea_signals_v2 取得 EA 分組
        if multi_ea_data.get('ea_details'):
            for ea in multi_ea_data['ea_details']:
                ea_key = f"{ea['comment_prefix']}_M{ea['magic']}"
                ea_groups[ea_key] = {
                    'ea_id': ea['ea_id'],
                    'comment_prefix': ea['comment_prefix'],
                    'magic': ea['magic'],
                    'set_versions': []
                }
        elif old_data:
            # 舊結構，只有一個 EA
            ea_type = old_data.get('ea_type', 'UNKNOWN')
            set_file = old_data.get('set_file', '')
            lot_layers = old_data.get('lot_layers', [])
            
            # 從 set_file 推斷 EA ID
            ea_id = identify_ea_from_set_filename(set_file) or ea_type.lower()
            
            ea_key = f"{ea_id}_unknown"
            ea_groups[ea_key] = {
                'ea_id': ea_id,
                'comment_prefix': ea_type,
                'magic': None,
                'set_versions': [{
                    'date': extract_date_from_set_filename(set_file),
                    'set_file': set_file,
                    'lot_layers': lot_layers
                }] if set_file and lot_layers else []
            }
        
        # 將 SET 檔案分配到對應的 EA
        for sf in set_files:
            sf_ea_id = sf.get('ea_id', '')
            sf_magic = sf.get('magic')
            sf_date = sf.get('date')
            sf_filename = sf.get('filename', '')
            sf_lot_layers = sf.get('lot_layers', [])
            
            # 尋找匹配的 EA group
            matched_key = None
            for key, group in ea_groups.items():
                # 1. 優先匹配 Magic Number（最精確）
                if sf_magic is not None and group['magic'] is not None:
                    if sf_magic == group['magic']:
                        # 雙重確認：prefix 或 ea_id 也要吻合
                        group_prefix_lower = group['comment_prefix'].lower().replace(' ', '_')
                        if sf_ea_id and (sf_ea_id == group_prefix_lower or sf_ea_id in group_prefix_lower or group_prefix_lower in sf_ea_id):
                            matched_key = key
                            break
                        # Magic 相同但 prefix 不同，可能是不同 EA
                        # 如果是 Dragon Wave，優先 magic match
                        if group['comment_prefix'] == 'Dragon Wave' and sf_ea_id == 'dragon_wave':
                            matched_key = key
                            break
                        if sf_ea_id == 'dragon_wave' and 'dragon' in group['comment_prefix'].lower():
                            matched_key = key
                            break
                
                # 2. 嘗試使用 comment_prefix 匹配 EA ID
                if sf_ea_id and not matched_key:
                    group_prefix_lower = group['comment_prefix'].lower().replace(' ', '_')
                    if sf_ea_id == group_prefix_lower:
                        if sf_magic is None or group['magic'] is None or sf_magic == group['magic']:
                            matched_key = key
                            break
            
            if matched_key:
                # 加入 set version
                if sf_lot_layers or sf_date:
                    # 檢查是否已經有相同的 set_file
                    existing_files = [sv['set_file'] for sv in ea_groups[matched_key]['set_versions']]
                    if sf_filename not in existing_files:
                        ea_groups[matched_key]['set_versions'].append({
                            'date': sf_date,
                            'set_file': sf_filename,
                            'lot_layers': sf_lot_layers
                        })
            else:
                # 沒有匹配，創建新 EA group
                if sf_lot_layers or sf_magic is not None:
                    comment_prefix = sf_ea_id.upper() if sf_ea_id else 'UNKNOWN'
                    new_key = f"{sf_ea_id or 'unknown'}_M{sf_magic or 'unknown'}"
                    if new_key not in ea_groups:
                        ea_groups[new_key] = {
                            'ea_id': sf_ea_id or 'unknown',
                            'comment_prefix': sf_ea_id.upper() if sf_ea_id else 'UNKNOWN',
                            'magic': sf_magic,
                            'set_versions': []
                        }
                    if sf_lot_layers or sf_date:
                        ea_groups[new_key]['set_versions'].append({
                            'date': sf_date,
                            'set_file': sf_filename,
                            'lot_layers': sf_lot_layers
                        })
        
        # 只保留有資料的 EA
        eas_list = [g for g in ea_groups.values() 
                    if g['set_versions'] or g['magic']]
        
        if eas_list:
            results[signal_id] = {
                'eas': eas_list
            }
    
    print(f"  完成: {len(results)} signals upgraded")
    
    return results


def generate_summary(new_mapping: Dict) -> Dict:
    """生成摘要統計"""
    stats = {
        'total_signals': len(new_mapping),
        'signals_with_eas': 0,
        'signals_with_set_files': 0,
        'total_eas': 0,
        'total_set_versions': 0,
        'ea_type_counts': defaultdict(int)
    }
    
    for signal_id, data in new_mapping.items():
        eas = data.get('eas', [])
        if eas:
            stats['signals_with_eas'] += 1
            stats['total_eas'] += len(eas)
            
            for ea in eas:
                # EA type 統計
                ea_id = ea.get('ea_id', 'unknown')
                stats['ea_type_counts'][ea_id] += 1
                
                # Set versions 統計
                set_versions = ea.get('set_versions', [])
                if set_versions:
                    stats['signals_with_set_files'] += 1
                    stats['total_set_versions'] += len(set_versions)
    
    stats['ea_type_counts'] = dict(stats['ea_type_counts'])
    
    return stats


def main():
    """主程式"""
    print("=" * 60)
    print("Signal Lot Mapping Upgrade - Phase 2")
    print("=" * 60)
    
    # 1. 載入舊資料
    old_mapping = load_old_mapping()
    print(f"  舊 mapping: {len(old_mapping)} signals")
    
    # 2. 載入 multi_ea_signals_v2
    multi_ea = load_multi_ea_signals()
    print(f"  Multi-EA signals: {multi_ea.get('summary', {}).get('multi_ea_signal_count', 0)}")
    
    # 3. 掃描 SET 檔案
    set_data = scan_set_files()
    
    # 4. 升級結構
    new_mapping = upgrade_signal_lot_mapping(old_mapping, multi_ea, set_data)
    
    # 5. 生成摘要
    stats = generate_summary(new_mapping)
    
    # 6. 加入 metadata
    output = {
        'generated_at': datetime.now().isoformat(),
        'version': '2.0',
        'summary': stats,
        'signals': new_mapping
    }
    
    # 7. 寫入輸出檔案
    output_path = OUTPUT_DIR / "signal_lot_mapping_v2.json"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n[Output] {output_path}")
    
    # 8. 顯示摘要
    print("\n" + "=" * 60)
    print("摘要")
    print("=" * 60)
    print(f"Total signals: {stats['total_signals']}")
    print(f"Signals with EAs: {stats['signals_with_eas']}")
    print(f"Signals with SET files: {stats['signals_with_set_files']}")
    print(f"Total EAs: {stats['total_eas']}")
    print(f"Total SET versions: {stats['total_set_versions']}")
    
    print("\nEA Types:")
    for ea_type, count in sorted(stats['ea_type_counts'].items(), 
                                  key=lambda x: -x[1])[:10]:
        print(f"  {ea_type}: {count}")
    
    # 9. 特別檢查 #10437
    if '10437' in new_mapping:
        print("\nSignal #10437 EAs:")
        for ea in new_mapping['10437']['eas']:
            set_count = len(ea.get('set_versions', []))
            print(f"  {ea['ea_id']}: magic={ea.get('magic')}, set_versions={set_count}")
    
    print("\n✅ Phase 2 signal_lot_mapping upgrade 完成")
    
    return new_mapping


if __name__ == "__main__":
    main()
