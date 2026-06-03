#!/usr/bin/env python3
"""
MT4 .set file parser for strategy version tracking.

Supports:
- Parse .set key=value format
- Extract key strategy parameters
- Diff two .set files to find parameter changes
- Correlate parameter changes with score changes
"""
import re
import os
import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional


# Key parameters that affect strategy behavior (categorized)
KEY_PARAMS = {
    'entry': [
        'OpenType', 'TradeType', 'EnterFreqMode', 'HftMode',
        'EnterFreqBarMode', 'Enter_Mode', 'Trading_Mode',
        'effStcK', 'effStcD', 'effStcS', 'effStcShift',
        'effStcH', 'effStcL', 'effStcRetDist',
        'BasicMaTimeframes', 'BasicMaLine1_Period', 'BasicMaLine2_Period',
        'BasicMaLine345_Period', 'BasicMaLine6_Period', 'BasicMaMethod',
        'BasicMaPrice', 'BasicMaShift', 'FollowMADirection',
        'UseEntrySTC', 'entryStc_K', 'entryStc_D',
        'UseEntryBB', 'entryBB_period', 'entryBB_deviation',
        'UseEffectiveMACD', 'effMACD_fast', 'effMACD_slow', 'effMACD_signal',
        'UseAISignal', 'AIsrc', 'UseCCY',
        'VolatilityApplied', 'UseVlt', 'VltFrom', 'VltUntil',
        'UseCorrelation', 'MaxCorr', 'MinCorr',
    ],
    'exit': [
        'TradeCloseOnlyOnDD', 'TradeModeResetOnDD',
        'ExiMACD', 'ExiMacdDiff',
        'ExitMaxSpread', 'MaxSpread', 'MaxSlippage',
    ],
    'risk': [
        'slDistS1', 'beDistS1', 'tpDistS1',
        'trailStartS1', 'trailDistS1',
        'slDist1', 'beDist1', 'tpDist1',
        'trailStart1', 'trailDist1',
        'lot1', 'lotS1', 'lotS2',
        'PipStepS2', 'PipStep1',
    ],
    'meta': [
        'EA_NAME', 'EA_VERSION', 'EA_SYMBOL', 'EA_PERIOD',
        'magic_number_B', 'magic_number_S',
        'comment_B', 'comment_S',
    ],
}

# All key params flattened
ALL_KEY_PARAMS = set()
for group in KEY_PARAMS.values():
    ALL_KEY_PARAMS.update(group)


@dataclass
class SetFileData:
    """Parsed .set file data."""
    filepath: str
    filename: str
    ea_name: str = ''
    ea_version: str = ''
    ea_symbol: str = ''
    ea_period: str = ''
    all_params: dict = field(default_factory=dict)
    key_params: dict = field(default_factory=dict)
    parsed_at: str = ''

    def __post_init__(self):
        if not self.parsed_at:
            self.parsed_at = datetime.now().isoformat()


@dataclass
class ParamDiff:
    """Difference between two parameter values."""
    param: str
    old_value: str
    new_value: str
    category: str = 'other'


@dataclass
class SetDiff:
    """Diff result between two .set files."""
    old_file: str
    new_file: str
    old_version: str = ''
    new_version: str = ''
    diffs: list = field(default_factory=list)  # List[ParamDiff]
    added_params: list = field(default_factory=list)
    removed_params: list = field(default_factory=list)
    summary: str = ''

    @property
    def has_changes(self) -> bool:
        return bool(self.diffs or self.added_params or self.removed_params)


def parse_set_file(filepath: str) -> SetFileData:
    """Parse a MT4 .set file into structured data."""
    filepath = str(filepath)
    path = Path(filepath)

    if not path.exists():
        raise FileNotFoundError(f".set file not found: {filepath}")

    params = {}
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            line = line.strip()
            if '=' in line and not line.startswith(';') and not line.startswith('///'):
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip()
                # Skip complex MT4 internal lines
                if key and not key.startswith('///') and not value.startswith('|||'):
                    params[key] = value

    key_params = {k: v for k, v in params.items() if k in ALL_KEY_PARAMS}

    return SetFileData(
        filepath=filepath,
        filename=path.name,
        ea_name=params.get('EA_NAME', ''),
        ea_version=params.get('EA_VERSION', ''),
        ea_symbol=params.get('EA_SYMBOL', ''),
        ea_period=params.get('EA_PERIOD', ''),
        all_params=params,
        key_params=key_params,
    )


def get_param_category(param: str) -> str:
    """Get the category of a parameter."""
    for cat, params in KEY_PARAMS.items():
        if param in params:
            return cat
    return 'other'


def diff_set_files(old: SetFileData, new: SetFileData) -> SetDiff:
    """Compare two .set files and find differences."""
    result = SetDiff(
        old_file=old.filename,
        new_file=new.filename,
        old_version=old.ea_version,
        new_version=new.ea_version,
    )

    old_keys = set(old.all_params.keys())
    new_keys = set(new.all_params.keys())

    # Added params
    for key in sorted(new_keys - old_keys):
        result.added_params.append({'param': key, 'value': new.all_params[key]})

    # Removed params
    for key in sorted(old_keys - new_keys):
        result.removed_params.append({'param': key, 'value': old.all_params[key]})

    # Changed params
    for key in sorted(old_keys & new_keys):
        if old.all_params[key] != new.all_params[key]:
            result.diffs.append(ParamDiff(
                param=key,
                old_value=old.all_params[key],
                new_value=new.all_params[key],
                category=get_param_category(key),
            ))

    # Generate summary
    entry_changes = [d for d in result.diffs if d.category == 'entry']
    exit_changes = [d for d in result.diffs if d.category == 'exit']
    risk_changes = [d for d in result.diffs if d.category == 'risk']
    other_changes = [d for d in result.diffs if d.category == 'other']

    parts = []
    if entry_changes:
        parts.append(f"Entry: {len(entry_changes)} params")
    if exit_changes:
        parts.append(f"Exit: {len(exit_changes)} params")
    if risk_changes:
        parts.append(f"Risk: {len(risk_changes)} params")
    if other_changes:
        parts.append(f"Other: {len(other_changes)} params")
    if result.added_params:
        parts.append(f"Added: {len(result.added_params)}")
    if result.removed_params:
        parts.append(f"Removed: {len(result.removed_params)}")

    result.summary = ' | '.join(parts) if parts else 'No changes'

    return result


def extract_signal_from_set_filename(filename: str) -> Optional[str]:
    """Try to extract signal ID from .set filename."""
    # Pattern: (12345)EA_NAME...
    m = re.match(r'\((\d+)\)', filename)
    if m:
        return m.group(1)
    # Pattern: ..._signal12345...
    m = re.search(r'signal[_\-]?(\d+)', filename, re.I)
    if m:
        return m.group(1)
    return None


def set_to_dict(data: SetFileData) -> dict:
    """Convert SetFileData to dict for JSON storage."""
    return {
        'filepath': data.filepath,
        'filename': data.filename,
        'ea_name': data.ea_name,
        'ea_version': data.ea_version,
        'ea_symbol': data.ea_symbol,
        'ea_period': data.ea_period,
        'key_params': data.key_params,
        'parsed_at': data.parsed_at,
    }


def diff_to_dict(diff: SetDiff) -> dict:
    """Convert SetDiff to dict for JSON storage."""
    return {
        'old_file': diff.old_file,
        'new_file': diff.new_file,
        'old_version': diff.old_version,
        'new_version': diff.new_version,
        'diffs': [
            {'param': d.param, 'old': d.old_value, 'new': d.new_value, 'cat': d.category}
            for d in diff.diffs
        ],
        'added': diff.added_params,
        'removed': diff.removed_params,
        'summary': diff.summary,
        'has_changes': diff.has_changes,
    }


# === Layer Config Extraction ===

EA_NAME_PATTERNS = {
    'MKD': ['MKD', 'MKD Pro', 'MKDPro'],
    'DragonWave': ['DragonWave', 'Dragon Wave'],
    'SMA': ['SMA', 'SMA Pro', 'SMAPro'],
    'S10': ['S10'],
    'Flash': ['Flash'],
    'GeminiClient': ['GeminiClient', 'Gemini Client'],
    'GeminiServer': ['GeminiServer', 'Gemini Server'],
    'StableHelper': ['StableHelper', 'Stable Helper'],
}

EA_DISPLAY_ABBREV = {
    'DragonWave': 'DW',
    'MKD Pro': 'MKDPro',
    'MKD': 'MKD',
    'SMA Pro': 'SMAPro',
    'SMA': 'SMA',
    'Flash': 'Flash',
    'S10': 'S10',
    'Gemini Client': 'GC',
    'Gemini Server': 'GS',
    'StableHelper': None,  # 不顯示
}


def get_ea_display_name(ea_name: str) -> str:
    """Return abbreviated EA display name, or '' for hidden EAs (StableHelper)."""
    if not ea_name:
        return ''
    ea_lower = ea_name.lower()
    # Match longest first to avoid partial matches (e.g. 'MKD Pro' before 'MKD')
    for full_name, abbrev in sorted(EA_DISPLAY_ABBREV.items(), key=lambda x: -len(x[0])):
        if full_name.lower() in ea_lower:
            return abbrev if abbrev is not None else ''
    # Fallback: strip version number
    import re
    cleaned = re.sub(r'\s*v?[\d.]+$', '', ea_name).strip()
    return cleaned


def detect_ea_type(ea_name: str) -> str:
    """Detect EA type from EA_NAME field."""
    for ea_type, patterns in EA_NAME_PATTERNS.items():
        for p in patterns:
            if p.lower() in ea_name.lower():
                return ea_type
    return 'Unknown'


def extract_symbol_from_filename(filename: str) -> str:
    """Extract symbol from SET filename like (10437)DragonWavev2.10USDJPY_H1_TypeBoth_.set"""
    m = re.match(r'\(\d+\).*?([A-Z]{6,}|XAUUSD|XAGUSD|US30|NAS100|US500)\b', filename)
    if m:
        return m.group(1)
    return ''


def extract_direction_from_filename(filename: str) -> str:
    """Extract direction (Buy/Sell/Both) from SET filename."""
    fl = filename.lower()
    if 'typebuy' in fl or '_buy_' in fl:
        return 'buy'
    elif 'typesell' in fl or '_sell_' in fl:
        return 'sell'
    return 'both'


def extract_layer_config(filepath: str) -> dict:
    """
    Extract layer configuration from a SET file.
    Returns structured dict with lots sequence, pipstep sequence, and EA-specific params.
    """
    data = parse_set_file(filepath)
    params = data.all_params
    ea_name = data.ea_name
    ea_type = detect_ea_type(ea_name)
    symbol = data.ea_symbol or extract_symbol_from_filename(data.filename)
    direction = extract_direction_from_filename(data.filename)

    def pf(key, default=0.0):
        """Parse float from params."""
        try:
            return float(params.get(key, default))
        except (ValueError, TypeError):
            return default

    def pi(key, default=0):
        """Parse int from params."""
        try:
            return int(float(params.get(key, default)))
        except (ValueError, TypeError):
            return default

    result = {
        'filename': data.filename,
        'ea_name': ea_name,
        'ea_type': ea_type,
        'ea_version': data.ea_version,
        'symbol': symbol,
        'direction': direction,
        'lot_mode': 'unknown',
        'lots': [],
        'pipsteps': [],
        'params': {},
    }

    if ea_type == 'MKD':
        # MKD v3: explicit lot1-lot5 + lot, PipStep1-5 + PipStep, plus S1/S2 sells
        lots = []
        pipsteps = []
        # Buy levels (lot1-5, lot final)
        for i in range(1, 6):
            l = pf(f'lot{i}')
            if l > 0:
                lots.append(l)
                ps = pf(f'PipStep{i}') if i > 1 else 0
                pipsteps.append(ps)
        # Final level
        final_lot = pf('lot')
        if final_lot > 0:
            lots.append(final_lot)
            pipsteps.append(pf('PipStep'))
        result['lot_mode'] = 'explicit'
        result['lots'] = lots
        result['pipsteps'] = pipsteps
        # Also store sell-side lots if present
        sell_lots = []
        for i in range(1, 3):
            sl = pf(f'lotS{i}')
            if sl > 0:
                sell_lots.append(sl)
        if sell_lots:
            result['sell_lots'] = sell_lots
        result['params'] = {f'lot{i}': pf(f'lot{i}') for i in range(1, 6) if pf(f'lot{i}') > 0}
        result['params']['lot'] = pf('lot')
        result['params'].update({f'PipStep{i}': pf(f'PipStep{i}') for i in range(1, 6) if pf(f'PipStep{i}') > 0})

    elif ea_type == 'DragonWave':
        # DragonWave: Lots + LotMul multiplier, PipStepMul
        base_lot = pf('Lots')
        lot_mul = pf('LotMul')
        pip_step_mul = pf('PipStepMul')
        # Calculate up to 8 levels
        lots = [base_lot]
        pipsteps = [0]
        # PipStep default for DW: use the base PipStep if set, else typical is 50
        base_pipstep = pf('PipStep') if pf('PipStep') > 0 else 50
        for i in range(1, 8):
            lots.append(round(base_lot * (lot_mul ** i), 4))
            pipsteps.append(round(base_pipstep * (pip_step_mul ** (i - 1)) if pip_step_mul else base_pipstep, 1))
        result['lot_mode'] = 'multiplier'
        result['lots'] = lots
        result['pipsteps'] = pipsteps
        result['params'] = {'Lots': base_lot, 'LotMul': lot_mul, 'PipStepMul': pip_step_mul}

    elif ea_type == 'SMA':
        # SMA v3: EntryLot + lotExp, pipstep2-8, slInLevel
        base_lot = pf('EntryLot')
        lot_exp = pf('lotExp')
        sl_in_level = pi('slInLevel')
        # pipstep2-8
        pipsteps = [0]  # LV1 has no pipstep
        for i in range(2, 9):
            ps = pf(f'pipstep{i}')
            if ps > 0:
                pipsteps.append(ps)
        # Calculate lots: lot * lotExp^(i-1) up to slInLevel
        n_levels = max(sl_in_level, len(pipsteps))
        lots = [round(base_lot * (lot_exp ** i), 4) for i in range(n_levels)]
        result['lot_mode'] = 'multiplier'
        result['lots'] = lots
        result['pipsteps'] = pipsteps[:n_levels]
        result['params'] = {'EntryLot': base_lot, 'lotExp': lot_exp, 'slInLevel': sl_in_level}

    elif ea_type == 'S10':
        # S10 v3: fixed lotSize
        lot_size = pf('lotSize')
        result['lot_mode'] = 'fixed'
        result['lots'] = [lot_size]
        result['pipsteps'] = []
        result['params'] = {'lotSize': lot_size}

    elif ea_type == 'Flash':
        # Flash v3: fixed Lot + CheckLevels, CheckDist
        lot = pf('Lot')
        check_levels = pi('CheckLevels')
        check_dist = pf('CheckDist')
        result['lot_mode'] = 'fixed'
        result['lots'] = [lot] if lot > 0 else []
        result['pipsteps'] = []
        result['params'] = {'Lot': lot, 'CheckLevels': check_levels, 'CheckDist': check_dist}

    elif ea_type in ('GeminiClient', 'GeminiServer'):
        # Gemini: Copy trade with StartLv and EndLv
        start_lv = pi('StartLv')
        end_lv = pi('EndLv')
        fix_lot = pf('FixLot')
        lot_mul = pf('LotMul')
        result['lot_mode'] = 'copy_trade'
        result['lots'] = []
        result['pipsteps'] = []
        result['start_lv'] = start_lv
        result['end_lv'] = end_lv
        result['params'] = {'StartLv': start_lv, 'EndLv': end_lv, 'FixLot': fix_lot, 'LotMul': lot_mul}

    elif ea_type == 'StableHelper':
        result['lot_mode'] = 'helper'

    return result


def get_set_configs_for_signal(signal_id: str, set_dir: str = None) -> dict:
    """
    Get all SET file configs for a given signal ID.
    Returns dict with signal_id and list of SET configs.
    Skips StableHelper files.
    """
    if set_dir is None:
        set_dir = str(Path(__file__).parent.parent / 'downloads' / 'set_files')
    set_path = Path(set_dir)
    sid = str(signal_id)
    configs = []
    for f in sorted(set_path.glob('*.set')):
        m = re.match(r'\((\d+)\)', f.name)
        if not m or m.group(1) != sid:
            continue
        try:
            cfg = extract_layer_config(str(f))
            if cfg.get('ea_type') == 'StableHelper':
                continue
            configs.append(cfg)
        except Exception as e:
            configs.append({
                'filename': f.name, 'error': str(e),
                'ea_name': '', 'ea_type': 'Unknown', 'symbol': '',
                'direction': 'both', 'lot_mode': 'error', 'lots': [], 'pipsteps': [], 'params': {}
            })
    return {
        'signal_id': int(sid) if sid.isdigit() else sid,
        'set_files': configs
    }


# === CLI ===
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  set_parser.py parse <file.set>          - Parse a .set file")
        print("  set_parser.py diff <old.set> <new.set>  - Diff two .set files")
        print("  set_parser.py scan <dir>                - Scan dir for .set files")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == 'parse' and len(sys.argv) >= 3:
        data = parse_set_file(sys.argv[2])
        print(f"EA: {data.ea_name} v{data.ea_version}")
        print(f"Symbol: {data.ea_symbol} | Period: {data.ea_period}")
        print(f"Key params ({len(data.key_params)}):")
        for cat, params in KEY_PARAMS.items():
            cat_params = {k: v for k, v in data.key_params.items() if k in params}
            if cat_params:
                print(f"  [{cat}] {json.dumps(cat_params, indent=4)}")

    elif cmd == 'diff' and len(sys.argv) >= 4:
        old = parse_set_file(sys.argv[2])
        new = parse_set_file(sys.argv[3])
        diff = diff_set_files(old, new)
        print(f"Diff: {diff.old_file} → {diff.new_file}")
        print(f"Version: {diff.old_version} → {diff.new_version}")
        print(f"Summary: {diff.summary}")
        print()
        if diff.diffs:
            print("Changed parameters:")
            for d in diff.diffs:
                print(f"  [{d.category}] {d.param}: {d.old_value} → {d.new_value}")
        if diff.added_params:
            print("Added:")
            for p in diff.added_params:
                print(f"  + {p['param']} = {p['value']}")
        if diff.removed_params:
            print("Removed:")
            for p in diff.removed_params:
                print(f"  - {p['param']} = {p['value']}")

    elif cmd == 'scan' and len(sys.argv) >= 3:
        d = Path(sys.argv[2])
        for f in sorted(d.rglob('*.set')):
            try:
                data = parse_set_file(str(f))
                sig = extract_signal_from_set_filename(f.name)
                print(f"{f.name} → EA={data.ea_name} v{data.ea_version} Sym={data.ea_symbol} Sig={sig}")
            except Exception as e:
                print(f"{f.name} → ERROR: {e}")
    else:
        print(f"Unknown command or missing args: {cmd}")
        sys.exit(1)
