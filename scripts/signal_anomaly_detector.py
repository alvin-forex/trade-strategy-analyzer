#!/usr/bin/env python3
"""
Signal Data Quality Anomaly Detector
掃描所有 CSV 交易記錄，偵測 6 種數據品質異常。

異常類型：
1. 幽靈持倉（Ghost Position）— Holding Time > 30 天
2. 手數突變（Lot Anomaly）— 同 Symbol+Direction 相鄰交易手數差 >10x
3. Comment 斷層（Comment Break）— 同 Symbol Comment 前綴永久改變
4. 時間斷層（Time Gap）— 同 Symbol 超過 7 天無交易
5. SET 與實際手數不符（SET Mismatch）— 實際 Lots 與 SET 定義差 >50%
6. 異常盈虧（Outlier P&L）— 單筆 P&L 超過該 Symbol 10σ

用法：
  python3 signal_anomaly_detector.py                  # 掃描全部
  python3 signal_anomaly_detector.py 10437 106        # 指定 Signal
  python3 signal_anomaly_detector.py --test            # 測試前 5 個
"""

import csv, codecs, sys, os, json, re, math, glob
from collections import defaultdict
from datetime import datetime, timedelta, date
from pathlib import Path

# ─── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
CSV_DIR = BASE_DIR / 'downloads'
SET_DIR = CSV_DIR / 'set_files'
OUTPUT_DIR = BASE_DIR / 'docs' / 'reports'

# ─── Constants ──────────────────────────────────────────────────────────
IGNORE_PATTERNS = ['transfer', 'withdrawal', 'credit', 'so:', 'deposit']
GHOST_DAYS = 30
LOT_MULTIPLIER_THRESHOLD = 10
TIME_GAP_DAYS = 7
SET_MISMATCH_PCT = 0.50
OUTLIER_SIGMA = 10

# ─── Helpers ────────────────────────────────────────────────────────────

def should_skip(comment: str) -> bool:
    """Skip non-trade records (transfers, withdrawals, etc.)"""
    if not comment:
        return False
    cl = comment.lower()
    return any(p in cl for p in IGNORE_PATTERNS)


def parse_datetime(s: str):
    """Parse DD/MM/YYYY HH:MM:SS"""
    try:
        return datetime.strptime(s.strip()[:19], '%d/%m/%Y %H:%M:%S')
    except (ValueError, TypeError):
        return None


def parse_date_only(s: str):
    """Parse DD/MM/YYYY"""
    try:
        return datetime.strptime(s.strip()[:10], '%d/%m/%Y').date()
    except (ValueError, TypeError):
        return None


def comment_prefix(comment: str) -> str:
    """Extract EA name prefix from comment (e.g. 'Dragon Wave' from 'Dragon Wave_BZ2')"""
    if not comment:
        return ''
    # Split on first underscore to get EA name (keep spaces in EA name)
    parts = comment.split('_', 1)
    return parts[0].strip() if parts else comment.strip()


def load_csv_trades(csv_path: str, signal_id: str) -> list:
    """Load and parse trades from a single CSV file."""
    trades = []
    try:
        with codecs.open(csv_path, 'r', 'utf-8-sig') as f:
            reader = csv.DictReader(f)
            for r in reader:
                open_time_str = r.get('Open Time', '').strip()
                close_time_str = r.get('Close Time', '').strip()
                typ = r.get('Type', '').strip().lower()
                lots_str = r.get('Lots', '0').strip()
                symbol = r.get('Symbol', '').strip()
                pnl_str = r.get('Net Profit', '0').strip()
                comment = r.get('Comment', '').strip()
                holding_str = r.get('Holding Time (Hours)', '0').strip()
                pips_str = r.get('Net Pips', '0').strip()

                if not open_time_str or not typ:
                    continue

                comment_check = comment if comment else ''
                if should_skip(comment_check):
                    continue

                open_dt = parse_datetime(open_time_str)
                close_dt = parse_datetime(close_time_str) if close_time_str else None
                if not open_dt:
                    continue

                try:
                    lots = float(lots_str)
                    pnl = float(pnl_str)
                    holding_hours = float(holding_str)
                except (ValueError, TypeError):
                    lots = 0.0
                    pnl = 0.0
                    holding_hours = 0.0

                # Normalize direction
                direction = 'buy' if 'buy' in typ else 'sell' if 'sell' in typ else typ

                trades.append({
                    'signal_id': signal_id,
                    'open_dt': open_dt,
                    'close_dt': close_dt,
                    'open_date': open_dt.date(),
                    'type': typ,
                    'direction': direction,
                    'lots': lots,
                    'symbol': symbol,
                    'pnl': pnl,
                    'comment': comment,
                    'comment_prefix': comment_prefix(comment),
                    'holding_hours': holding_hours,
                    'holding_days': holding_hours / 24.0,
                })
    except Exception as e:
        print(f"  ⚠ Error reading {csv_path}: {e}")
        return []

    trades.sort(key=lambda t: t['open_dt'])
    return trades


# ─── Anomaly Detectors ──────────────────────────────────────────────────

def detect_ghost_positions(trades: list) -> list:
    """1. 幽靈持倉：Holding Time > 30 days"""
    results = []
    for t in trades:
        if t['holding_days'] > GHOST_DAYS:
            results.append({
                'type': 'ghost_position',
                'signal_id': t['signal_id'],
                'symbol': t['symbol'],
                'direction': t['direction'],
                'open_date': str(t['open_date']),
                'holding_days': round(t['holding_days'], 1),
                'comment': t['comment'],
                'pnl': round(t['pnl'], 2),
            })
    return results


def detect_lot_anomalies(trades: list) -> list:
    """2. 手數突變：同 Symbol+Direction 相鄰兩筆手數差 >10x"""
    results = []
    # Group by signal_id + symbol + direction
    groups = defaultdict(list)
    for t in trades:
        key = (t['signal_id'], t['symbol'], t['direction'])
        groups[key].append(t)

    for (sid, sym, d), group in groups.items():
        if len(group) < 2:
            continue
        # Already sorted by open_dt
        for i in range(1, len(group)):
            prev_lot = group[i-1]['lots']
            curr_lot = group[i]['lots']
            if prev_lot <= 0 or curr_lot <= 0:
                continue
            ratio = max(prev_lot, curr_lot) / min(prev_lot, curr_lot)
            if ratio > LOT_MULTIPLIER_THRESHOLD:
                results.append({
                    'type': 'lot_anomaly',
                    'signal_id': sid,
                    'symbol': sym,
                    'date': str(group[i]['open_date']),
                    'expected_lot': prev_lot,
                    'actual_lot': curr_lot,
                    'ratio': round(ratio, 1),
                    'comment': group[i]['comment'],
                })
    return results


def detect_comment_breaks(trades: list) -> list:
    """3. Comment 斷層：同 Symbol Comment 前綴永久改變"""
    results = []
    # Group by signal_id + symbol
    groups = defaultdict(list)
    for t in trades:
        key = (t['signal_id'], t['symbol'])
        groups[key].append(t)

    for (sid, sym), group in groups.items():
        if len(group) < 3:
            continue
        # Track prefix changes
        prefixes = [t['comment_prefix'] for t in group]
        unique_prefixes = []
        seen = set()
        for p in prefixes:
            if p and p not in seen:
                unique_prefixes.append(p)
                seen.add(p)

        if len(unique_prefixes) < 2:
            continue

        # Find transitions where old prefix never reappears
        for i in range(len(unique_prefixes) - 1):
            old_prefix = unique_prefixes[i]
            new_prefix = unique_prefixes[i + 1]

            # Check if old prefix ever reappears after the transition
            # Find first occurrence of new_prefix
            first_new_idx = None
            for j, t in enumerate(group):
                if t['comment_prefix'] == new_prefix:
                    first_new_idx = j
                    break

            if first_new_idx is None:
                continue

            # Check if old_prefix appears after first_new_idx
            old_reappears = False
            for j in range(first_new_idx, len(group)):
                if group[j]['comment_prefix'] == old_prefix:
                    old_reappears = True
                    break

            if not old_reappears:
                results.append({
                    'type': 'comment_break',
                    'signal_id': sid,
                    'symbol': sym,
                    'date': str(group[first_new_idx]['open_date']),
                    'old_comment': old_prefix,
                    'new_comment': new_prefix,
                })

    return results


def _trading_days_between(d1: date, d2: date) -> int:
    """Count calendar days between two dates excluding full weekends (Sat+Sun)."""
    if d1 >= d2:
        return 0
    total = (d2 - d1).days
    # Count weekends in range
    weekends = 0
    current = d1
    while current < d2:
        if current.weekday() >= 5:  # Sat=5, Sun=6
            weekends += 1
        current += timedelta(days=1)
    return total - weekends


def detect_time_gaps(trades: list) -> list:
    """4. 時間斷層：同 Symbol 超過 7 天無交易（排除週末）"""
    results = []
    # Group by signal_id + symbol
    groups = defaultdict(list)
    for t in trades:
        key = (t['signal_id'], t['symbol'])
        groups[key].append(t)

    for (sid, sym), group in groups.items():
        if len(group) < 2:
            continue
        # Already sorted
        for i in range(1, len(group)):
            prev_date = group[i-1]['open_date']
            curr_date = group[i]['open_date']
            gap_days = (curr_date - prev_date).days
            trading_gap = _trading_days_between(prev_date, curr_date)
            if trading_gap > TIME_GAP_DAYS:
                results.append({
                    'type': 'time_gap',
                    'signal_id': sid,
                    'symbol': sym,
                    'gap_start': str(prev_date),
                    'gap_end': str(curr_date),
                    'gap_days': gap_days,
                    'trading_days': trading_gap,
                })
    return results


def detect_set_mismatches(trades: list, set_dir: Path) -> list:
    """5. SET Mismatch：實際 Lots 與 SET 定義差 >50%"""
    results = []

    # Import set_parser
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from set_parser import get_set_configs_for_signal, extract_layer_config

    # Group trades by signal_id
    signal_groups = defaultdict(list)
    for t in trades:
        signal_groups[t['signal_id']].append(t)

    for sid, sig_trades in signal_groups.items():
        try:
            configs = get_set_configs_for_signal(sid, str(set_dir))
        except Exception:
            continue

        set_files = configs.get('set_files', [])
        if not set_files:
            continue

        # Build lookup: (symbol, direction) -> set lots info
        set_lots_map = {}
        for sf in set_files:
            if 'error' in sf:
                continue
            sym = sf.get('symbol', '')
            direction = sf.get('direction', 'both')
            lots_list = sf.get('lots', [])
            filename = sf.get('filename', '')
            ea_type = sf.get('ea_type', '')
            if not sym:
                continue

            key = (sym, direction)
            all_lots = lots_list  # All possible lot sizes from SET
            if key not in set_lots_map:
                set_lots_map[key] = {
                    'lots': all_lots,
                    'filename': filename,
                    'ea_type': ea_type,
                }
            # Also store for 'both' direction
            if direction == 'both':
                for d2 in ['buy', 'sell']:
                    k2 = (sym, d2)
                    if k2 not in set_lots_map:
                        set_lots_map[k2] = {
                            'lots': all_lots,
                            'filename': filename,
                            'ea_type': ea_type,
                        }

        # Check each trade
        for t in sig_trades:
            if t['lots'] <= 0:
                continue
            sym = t['symbol']
            direction = t['direction']

            # Try specific direction first, then 'both'
            set_info = set_lots_map.get((sym, direction)) or set_lots_map.get((sym, 'both'))
            if not set_info or not set_info['lots']:
                continue

            set_lots = set_info['lots']
            actual_lot = t['lots']

            # Check if actual lot is close to any SET-defined lot
            matched = False
            best_expected = min(set_lots, key=lambda x: abs(x - actual_lot))
            if best_expected > 0:
                diff_pct = abs(actual_lot - best_expected) / best_expected
                if diff_pct > SET_MISMATCH_PCT:
                    results.append({
                        'type': 'set_mismatch',
                        'signal_id': sid,
                        'symbol': sym,
                        'date': str(t['open_date']),
                        'actual_lot': actual_lot,
                        'set_expected_lot': best_expected,
                        'diff_pct': round(diff_pct * 100, 1),
                        'set_file': set_info['filename'],
                    })
    return results


def detect_outlier_pnl(trades: list) -> list:
    """6. 異常盈虧：單筆 P&L 超過該 Symbol 10σ"""
    results = []

    # Group by signal_id + symbol
    groups = defaultdict(list)
    for t in trades:
        key = (t['signal_id'], t['symbol'])
        groups[key].append(t)

    for (sid, sym), group in groups.items():
        if len(group) < 5:  # Need enough data for meaningful stats
            continue

        pnls = [t['pnl'] for t in group]
        avg_pnl = sum(pnls) / len(pnls)
        variance = sum((p - avg_pnl) ** 2 for p in pnls) / len(pnls)
        std_pnl = math.sqrt(variance)

        if std_pnl <= 0:
            continue

        for t in group:
            z_score = abs(t['pnl'] - avg_pnl) / std_pnl
            if z_score > OUTLIER_SIGMA:
                results.append({
                    'type': 'outlier_pnl',
                    'signal_id': sid,
                    'symbol': sym,
                    'date': str(t['open_date']),
                    'pnl': round(t['pnl'], 2),
                    'avg_pnl': round(avg_pnl, 2),
                    'std_dev': round(std_pnl, 2),
                    'z_score': round(z_score, 1),
                    'comment': t['comment'],
                })
    return results


# ─── Report Generation ──────────────────────────────────────────────────

def generate_json_report(all_anomalies: dict, output_path: Path):
    """Generate JSON anomaly report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_anomalies, f, indent=2, ensure_ascii=False, default=str)
    print(f"  ✅ JSON report → {output_path}")


def generate_html_report(all_anomalies: dict, output_path: Path):
    """Generate dark-themed HTML anomaly report."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    counts = {k: len(v) for k, v in all_anomalies['anomalies'].items()}
    total = sum(counts.values())

    # Build sections
    sections_html = ''

    # 1. Ghost Positions
    ghost = all_anomalies['anomalies'].get('ghost_position', [])
    sections_html += build_section('👻 幽靈持倉 (Ghost Position)',
        'Holding Time > 30 天 — 改 SET 後 Comment 變了，EA 不認舊單',
        ghost, ['Signal ID', 'Symbol', 'Direction', 'Open Date', 'Holding Days', 'Comment', 'P&L'],
        lambda r: [r['signal_id'], r['symbol'], r['direction'], r['open_date'],
                   r['holding_days'], r['comment'], fmt_pnl(r['pnl'])])

    # 2. Lot Anomalies
    lot = all_anomalies['anomalies'].get('lot_anomaly', [])
    sections_html += build_section('📊 手數突變 (Lot Anomaly)',
        '同 Symbol+Direction 相鄰交易手數差 >10x',
        lot, ['Signal ID', 'Symbol', 'Date', 'Expected Lot', 'Actual Lot', 'Ratio', 'Comment'],
        lambda r: [r['signal_id'], r['symbol'], r['date'], r['expected_lot'],
                   r['actual_lot'], f"{r['ratio']}x", r['comment']])

    # 3. Comment Breaks
    cb = all_anomalies['anomalies'].get('comment_break', [])
    sections_html += build_section('🔗 Comment 斷層 (Comment Break)',
        '同 Symbol Comment 前綴永久改變 — EA 更換或改 SET',
        cb, ['Signal ID', 'Symbol', 'Date', 'Old Comment', 'New Comment'],
        lambda r: [r['signal_id'], r['symbol'], r['date'], r['old_comment'], r['new_comment']])

    # 4. Time Gaps
    tg = all_anomalies['anomalies'].get('time_gap', [])
    sections_html += build_section('⏰ 時間斷層 (Time Gap)',
        '同 Symbol 超過 7 個交易日無交易 — 斷線或 EA 停止',
        tg, ['Signal ID', 'Symbol', 'Gap Start', 'Gap End', 'Days', 'Trading Days'],
        lambda r: [r['signal_id'], r['symbol'], r['gap_start'], r['gap_end'], r['gap_days'], r.get('trading_days', r['gap_days'])])

    # 5. SET Mismatches
    sm = all_anomalies['anomalies'].get('set_mismatch', [])
    sections_html += build_section('⚙️ SET 手數不符 (SET Mismatch)',
        '實際 Lots 與 SET 定義差 >50%',
        sm, ['Signal ID', 'Symbol', 'Date', 'Actual Lot', 'SET Expected', 'Diff%', 'SET File'],
        lambda r: [r['signal_id'], r['symbol'], r['date'], r['actual_lot'],
                   r['set_expected_lot'], f"{r['diff_pct']}%", r['set_file']])

    # 6. Outlier P&L
    ol = all_anomalies['anomalies'].get('outlier_pnl', [])
    sections_html += build_section('💰 異常盈虧 (Outlier P&L)',
        '單筆 P&L 超過該 Symbol 10σ — 可能是斷線清算',
        ol, ['Signal ID', 'Symbol', 'Date', 'P&L', 'Avg P&L', 'StdDev', 'Z-Score', 'Comment'],
        lambda r: [r['signal_id'], r['symbol'], r['date'], fmt_pnl(r['pnl']),
                   fmt_pnl(r['avg_pnl']), fmt_pnl(r['std_dev']), r['z_score'], r['comment']])

    # Stats summary
    stats_html = f'''
    <div class="stats-bar">
        <div><span class="v">{all_anomalies["meta"]["total_signals"]}</span><span class="l">Signals</span></div>
        <div><span class="v">{all_anomalies["meta"]["total_trades"]}</span><span class="l">Trades</span></div>
        <div><span class="v" style="color:var(--red)">{total}</span><span class="l">Total Anomalies</span></div>
        <div><span class="v" style="color:#FF5722">{counts.get("ghost_position",0)}</span><span class="l">👻 Ghost</span></div>
        <div><span class="v" style="color:#FFC107">{counts.get("lot_anomaly",0)}</span><span class="l">📊 Lot</span></div>
        <div><span class="v" style="color:#64b5f6">{counts.get("comment_break",0)}</span><span class="l">🔗 Comment</span></div>
        <div><span class="v" style="color:#AB47BC">{counts.get("time_gap",0)}</span><span class="l">⏰ Time Gap</span></div>
        <div><span class="v" style="color:#26C6DA">{counts.get("set_mismatch",0)}</span><span class="l">⚙️ SET</span></div>
        <div><span class="v" style="color:#66BB6A">{counts.get("outlier_pnl",0)}</span><span class="l">💰 Outlier</span></div>
    </div>'''

    # Affected signals summary
    affected_signals = set()
    for anom_list in all_anomalies['anomalies'].values():
        for a in anom_list:
            affected_signals.add(str(a['signal_id']))

    affected_html = ''
    if affected_signals:
        affected_html = f'''
    <div class="sec">
        <div class="sec-h open" onclick="toggleSec(this)">📋 受影響 Signals ({len(affected_signals)}) <span class="arrow">▶</span></div>
        <div class="sec-b open">
            <div style="display:flex;flex-wrap:wrap;gap:6px">
                {''.join(f'<span class="signal-tag">{s}</span>' for s in sorted(affected_signals, key=lambda x: int(x) if x.isdigit() else 0))}
            </div>
        </div>
    </div>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🔍 數據品質異常報告</title>
<style>
:root{{--font:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Microsoft JhengHei',sans-serif;--radius:8px}}
[data-theme="dark"]{{--bg:#0a0e17;--card:#111520;--hover:#1a1f2e;--text:#d0d0d0;--text2:#777;--pri:#FFD700;--acc:#64b5f6;--grn:#4CAF50;--red:#FF5722;--yel:#FFC107;--brd:#1e2433;--th:#111520;--zebra:#151b28}}
[data-theme="light"]{{--bg:#f5f7fa;--card:#fff;--hover:#eef2f7;--text:#333;--text2:#666;--pri:#0f3460;--acc:#e94560;--grn:#28a745;--red:#dc3545;--yel:#ffc107;--brd:#ddd;--th:#eef2f7;--zebra:#f0f4fa}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:var(--font);background:var(--bg);color:var(--text);padding:12px;max-width:1600px;margin:0 auto}}
h1{{font-size:1.4em;color:var(--pri);margin-bottom:4px}}
h2{{font-size:1.05em;color:var(--pri);margin:16px 0 8px}}
.theme-btn{{width:36px;height:36px;border:1px solid var(--brd);border-radius:50%;background:var(--card);color:var(--text);font-size:18px;cursor:pointer;position:fixed;top:12px;right:12px;z-index:100}}
.stats-bar{{background:var(--card);border:1px solid var(--brd);border-radius:8px;padding:12px 18px;margin-bottom:12px;display:flex;gap:20px;flex-wrap:wrap}}
.stats-bar .v{{font-size:1.3em;font-weight:bold}}.stats-bar .l{{font-size:0.75em;color:var(--text2)}}
.sec{{background:var(--card);border:1px solid var(--brd);border-radius:8px;margin-bottom:8px;overflow:hidden}}
.sec-h{{padding:10px 14px;cursor:pointer;display:flex;justify-content:space-between;align-items:center;font-weight:bold;font-size:0.95em}}
.sec-h:hover{{background:var(--hover)}}
.sec-h .arrow{{transition:transform 0.2s;font-size:0.8em;color:var(--text2)}}
.sec-h.open .arrow{{transform:rotate(90deg)}}
.sec-b{{display:none;padding:10px 14px;border-top:1px solid var(--brd)}}
.sec-b.open{{display:block}}
.sec-desc{{font-size:0.8em;color:var(--text2);margin-bottom:8px;font-style:italic}}
table{{width:100%;border-collapse:collapse;font-size:0.82em}}
th{{background:var(--th);padding:5px 8px;text-align:left;border-bottom:2px solid var(--pri);color:var(--pri);font-size:0.8em;white-space:nowrap}}
td{{padding:4px 8px;border-bottom:1px solid var(--brd)}}
tr:nth-child(even){{background:var(--zebra)}}
tr:hover{{background:var(--hover)}}
.pnl-pos{{color:var(--grn)}}.pnl-neg{{color:var(--red)}}
.signal-tag{{background:var(--bg);border:1px solid var(--brd);border-radius:4px;padding:2px 8px;font-size:0.8em;font-family:monospace}}
.empty{{color:var(--text2);font-style:italic;padding:10px;font-size:0.9em}}
.generated{{font-size:0.75em;color:var(--text2);margin-top:16px;text-align:right}}
</style>
</head>
<body data-theme="dark">
<button class="theme-btn" onclick="toggleTheme()" title="Toggle theme">🌓</button>
<h1>🔍 數據品質異常報告</h1>
<p style="color:var(--text2);font-size:0.85em;margin-bottom:8px">
    Generated: {all_anomalies['meta']['generated_at']} | 
    Signals scanned: {all_anomalies['meta']['total_signals']} | 
    Trades analyzed: {all_anomalies['meta']['total_trades']}
</p>

{stats_html}
{affected_html}
{sections_html}

<div class="generated">Generated by signal_anomaly_detector.py</div>

<script>
function toggleTheme(){{
    const b=document.body;
    b.setAttribute('data-theme',b.getAttribute('data-theme')==='dark'?'light':'dark');
}}
function toggleSec(el){{
    el.classList.toggle('open');
    el.nextElementSibling.classList.toggle('open');
}}
</script>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"  ✅ HTML report → {output_path}")


def fmt_pnl(v: float) -> str:
    if v > 0:
        return f'<span class="pnl-pos">+{v:.2f}</span>'
    elif v < 0:
        return f'<span class="pnl-neg">{v:.2f}</span>'
    return f'{v:.2f}'


def build_section(title: str, desc: str, rows: list, headers: list, row_fn) -> str:
    """Build an HTML section with a table."""
    count = len(rows)
    html = f'''
    <div class="sec">
        <div class="sec-h open" onclick="toggleSec(this)">{title} ({count}) <span class="arrow">▶</span></div>
        <div class="sec-b open">
            <div class="sec-desc">{desc}</div>'''

    if not rows:
        html += '<div class="empty">✅ 無異常</div>'
    else:
        html += '<table><tr>'
        for h in headers:
            html += f'<th>{h}</th>'
        html += '</tr>'
        for r in rows:
            html += '<tr>'
            for cell in row_fn(r):
                html += f'<td>{cell}</td>'
            html += '</tr>'
        html += '</table>'

    html += '</div></div>'
    return html


# ─── Main ───────────────────────────────────────────────────────────────

def scan_signals(signal_ids: list = None, test_mode: bool = False):
    """Scan signals for anomalies."""
    # Find CSV files
    csv_pattern = str(CSV_DIR / 'forex-forest-signals-page-*.csv')
    csv_files = sorted(glob.glob(csv_pattern))

    if test_mode:
        csv_files = csv_files[:5]

    if signal_ids:
        csv_files = [f for f in csv_files
                     if any(sid in os.path.basename(f) for sid in signal_ids)]

    print(f"🔍 Scanning {len(csv_files)} signals...")

    all_trades = []
    signal_count = 0

    for cf in csv_files:
        m = re.search(r'page-(\d+)\.csv', cf)
        if not m:
            continue
        sid = m.group(1)
        trades = load_csv_trades(cf, sid)
        if trades:
            all_trades.extend(trades)
            signal_count += 1
            print(f"  Signal {sid}: {len(trades)} trades")

    print(f"\n📊 Loaded {len(all_trades)} trades from {signal_count} signals\n")

    # Run detectors
    print("━" * 60)
    print("Running anomaly detectors...")

    anomalies = {
        'ghost_position': detect_ghost_positions(all_trades),
        'lot_anomaly': detect_lot_anomalies(all_trades),
        'comment_break': detect_comment_breaks(all_trades),
        'time_gap': detect_time_gaps(all_trades),
        'set_mismatch': detect_set_mismatches(all_trades, SET_DIR),
        'outlier_pnl': detect_outlier_pnl(all_trades),
    }

    # Print console report
    print_console_report(anomalies)

    # Build full report
    report = {
        'meta': {
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_signals': signal_count,
            'total_trades': len(all_trades),
            'csv_files_scanned': len(csv_files),
        },
        'anomalies': anomalies,
        'summary': {
            name: len(items) for name, items in anomalies.items()
        }
    }

    # Save reports
    json_path = OUTPUT_DIR / 'anomaly_report.json'
    html_path = OUTPUT_DIR / 'anomaly_report.html'
    generate_json_report(report, json_path)
    generate_html_report(report, html_path)

    return report


def print_console_report(anomalies: dict):
    """Print anomaly results to console."""
    print("\n" + "━" * 60)
    print("📋 ANOMALY DETECTION RESULTS")
    print("━" * 60)

    # 1. Ghost Positions
    ghost = anomalies['ghost_position']
    print(f"\n👻 幽靈持倉 (Ghost Position): {len(ghost)}")
    if ghost:
        print(f"  {'Signal':>8} {'Symbol':<10} {'Dir':<6} {'Open Date':<12} {'Days':>8} {'P&L':>10} Comment")
        for r in ghost[:20]:
            print(f"  {r['signal_id']:>8} {r['symbol']:<10} {r['direction']:<6} {r['open_date']:<12} {r['holding_days']:>8.1f} {r['pnl']:>10.2f} {r['comment']}")
        if len(ghost) > 20:
            print(f"  ... and {len(ghost)-20} more")

    # 2. Lot Anomalies
    lot = anomalies['lot_anomaly']
    print(f"\n📊 手數突變 (Lot Anomaly): {len(lot)}")
    if lot:
        print(f"  {'Signal':>8} {'Symbol':<10} {'Date':<12} {'Expected':>10} {'Actual':>10} {'Ratio':>8} Comment")
        for r in lot[:20]:
            print(f"  {r['signal_id']:>8} {r['symbol']:<10} {r['date']:<12} {r['expected_lot']:>10.2f} {r['actual_lot']:>10.2f} {r['ratio']:>7.1f}x {r['comment']}")
        if len(lot) > 20:
            print(f"  ... and {len(lot)-20} more")

    # 3. Comment Breaks
    cb = anomalies['comment_break']
    print(f"\n🔗 Comment 斷層 (Comment Break): {len(cb)}")
    if cb:
        print(f"  {'Signal':>8} {'Symbol':<10} {'Date':<12} {'Old Comment':<25} → {'New Comment'}")
        for r in cb[:20]:
            print(f"  {r['signal_id']:>8} {r['symbol']:<10} {r['date']:<12} {r['old_comment']:<25} → {r['new_comment']}")
        if len(cb) > 20:
            print(f"  ... and {len(cb)-20} more")

    # 4. Time Gaps
    tg = anomalies['time_gap']
    print(f"\n⏰ 時間斷層 (Time Gap): {len(tg)}")
    if tg:
        print(f"  {'Signal':>8} {'Symbol':<10} {'Gap Start':<12} {'Gap End':<12} {'Days':>6} {'Trade Days':>10}")
        for r in tg[:20]:
            print(f"  {r['signal_id']:>8} {r['symbol']:<10} {r['gap_start']:<12} {r['gap_end']:<12} {r['gap_days']:>6} {r.get('trading_days', r['gap_days']):>10}")
        if len(tg) > 20:
            print(f"  ... and {len(tg)-20} more")

    # 5. SET Mismatches
    sm = anomalies['set_mismatch']
    print(f"\n⚙️ SET 手數不符 (SET Mismatch): {len(sm)}")
    if sm:
        print(f"  {'Signal':>8} {'Symbol':<10} {'Date':<12} {'Actual':>8} {'Expected':>10} {'Diff%':>8} SET File")
        for r in sm[:20]:
            print(f"  {r['signal_id']:>8} {r['symbol']:<10} {r['date']:<12} {r['actual_lot']:>8.2f} {r['set_expected_lot']:>10.2f} {r['diff_pct']:>7.1f}% {r['set_file']}")
        if len(sm) > 20:
            print(f"  ... and {len(sm)-20} more")

    # 6. Outlier P&L
    ol = anomalies['outlier_pnl']
    print(f"\n💰 異常盈虧 (Outlier P&L): {len(ol)}")
    if ol:
        print(f"  {'Signal':>8} {'Symbol':<10} {'Date':<12} {'P&L':>10} {'Avg':>10} {'σ':>8} {'Z':>6} Comment")
        for r in ol[:20]:
            print(f"  {r['signal_id']:>8} {r['symbol']:<10} {r['date']:<12} {r['pnl']:>10.2f} {r['avg_pnl']:>10.2f} {r['std_dev']:>8.2f} {r['z_score']:>6.1f} {r['comment']}")
        if len(ol) > 20:
            print(f"  ... and {len(ol)-20} more")

    total = sum(len(v) for v in anomalies.values())
    print(f"\n{'━' * 60}")
    print(f"Total anomalies: {total}")
    for name, items in anomalies.items():
        if items:
            print(f"  {name}: {len(items)}")
    print()


if __name__ == '__main__':
    test_mode = '--test' in sys.argv
    signal_ids = [a for a in sys.argv[1:] if not a.startswith('--') and a.isdigit()]

    if test_mode:
        print("🧪 TEST MODE — scanning first 5 signals")
        scan_signals(test_mode=True)
    elif signal_ids:
        scan_signals(signal_ids=signal_ids)
    else:
        scan_signals()
