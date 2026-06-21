#!/usr/bin/env python3
"""
Date Range Review - 按日期覆盤分析（TSA 整合版）

按日期範圍分析交易數據，支持：
- 按日期範圍篩選（例如 2026-03-01 至 2026-03-31）
- 按 Signal/CCY/Buy/Sell 分組
- 跨系統所有 signals 對比
- 市況數據 overlay（預留接口）

**TSA 整合**：
- 共用 dde_v5_scorer.py 的 CSV reader
- 共用 history_manager.py 的 DB connection
- 共用 TSA HTML template style
- 輸出到 docs/reviews/ → GitHub Pages 部署
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from typing import Optional, Dict, List, Any

# TSA 整合 imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dde_v5_scorer import read_csv_trades, get_ea
    USE_DDE_V5 = True
except ImportError:
    USE_DDE_V5 = False

try:
    from config import EA_MAP
except ImportError:
    EA_MAP = {}

# 項目路徑
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'history'
DEFAULT_OUTPUT = PROJECT_ROOT / 'docs' / 'reviews'

# EA Colors
EA_COLORS = {
    'DW': ('#4a148c', '#ce93d8'),
    'SMA': ('#1b5e20', '#a5d6a7'),
    'MKD': ('#e65100', '#ffcc80'),
    'Flash': ('#0d47a1', '#90caf9'),
    'S10': ('#004d40', '#80cbc4'),
    'GC': ('#0d47a1', '#90caf9'),
    'GS': ('#1a237e', '#9fa8da'),
    'MAN': ('#4527a0', '#b39ddb'),
    'UNK': ('#333', '#c9d1d9'),
}


def get_ea_from_signal(signal_id: str) -> str:
    """Get EA tag from signal ID."""
    if USE_DDE_V5:
        try:
            return get_ea(signal_id)
        except:
            pass
    return EA_MAP.get(signal_id, 'UNK')


def parse_trade_time(time_str: str) -> Optional[datetime]:
    """Parse trade time string."""
    if not time_str:
        return None
    formats = ['%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d/%m/%y %H:%M:%S']
    time_str = time_str.strip()
    for fmt in formats:
        try:
            return datetime.strptime(time_str, fmt)
        except ValueError:
            continue
    return None


def load_all_signal_data(data_dir: Path) -> Dict[str, dict]:
    """Load all signal JSON files."""
    signals = {}
    for json_file in sorted(data_dir.glob('signal_*.json')):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                signal_id = data.get('signal_id') or json_file.stem.replace('signal_', '')
                signals[str(signal_id)] = data
        except Exception as e:
            print(f"Warning: Failed to load {json_file}: {e}", file=sys.stderr)
    return signals


def filter_trades_by_date(trades: List[dict], start_date: datetime, end_date: datetime, use_close: bool = False) -> List[dict]:
    """Filter trades within date range."""
    filtered = []
    time_field = 'Close Time' if use_close else 'Open Time'
    for trade in trades:
        trade_time = parse_trade_time(trade.get(time_field, ''))
        if trade_time and start_date <= trade_time <= end_date:
            filtered.append(trade)
    return filtered


def analyze_trades(trades: List[dict]) -> dict:
    """Compute statistics for trades."""
    if not trades:
        return {'count': 0, 'win_count': 0, 'loss_count': 0, 'win_rate': 0, 'total_pnl': 0, 'total_pips': 0,
                'avg_pnl': 0, 'avg_pips': 0, 'avg_win': 0, 'avg_loss': 0, 'profit_factor': 0, 'avg_hold_hours': 0}
    
    wins = [t for t in trades if float(t.get('Net Profit', 0)) > 0]
    losses = [t for t in trades if float(t.get('Net Profit', 0)) <= 0]
    total_pnl = sum(float(t.get('Net Profit', 0)) for t in trades)
    total_pips = sum(float(t.get('Net Pips', 0)) for t in trades)
    total_wins = sum(float(t.get('Net Profit', 0)) for t in wins)
    total_losses = abs(sum(float(t.get('Net Profit', 0)) for t in losses))
    avg_hold = sum(float(t.get('Holding Time (Hours)', 0) or 0) for t in trades) / len(trades)
    pf = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
    
    return {
        'count': len(trades),
        'win_count': len(wins),
        'loss_count': len(losses),
        'win_rate': round(len(wins) / len(trades) * 100, 2) if trades else 0,
        'total_pnl': round(total_pnl, 2),
        'total_pips': round(total_pips, 1),
        'avg_pnl': round(total_pnl / len(trades), 2) if trades else 0,
        'avg_pips': round(total_pips / len(trades), 1) if trades else 0,
        'avg_win': round(total_wins / len(wins), 2) if wins else 0,
        'avg_loss': round(total_losses / len(losses), 2) if losses else 0,
        'profit_factor': round(pf, 2) if pf != float('inf') else 'inf',
        'avg_hold_hours': round(avg_hold, 1),
    }


def generate_report(signals_data: Dict[str, dict], start_date: datetime, end_date: datetime, signal_id: Optional[str] = None) -> dict:
    """Generate date range review report."""
    # Valid trade types only (exclude balance, credit, etc.)
    VALID_TRADE_TYPES = {'buy', 'sell'}
    
    all_trades = []
    for sid, data in signals_data.items():
        if signal_id and sid != signal_id:
            continue
        ea = data.get('ea', get_ea_from_signal(sid))
        for trade in data.get('trades', []):
            # Filter: only include buy/sell trades
            trade_type = trade.get('Type', '').lower()
            if trade_type not in VALID_TRADE_TYPES:
                continue
            trade_copy = trade.copy()
            trade_copy['_signal_id'] = sid
            trade_copy['_ea'] = ea
            all_trades.append(trade_copy)
    
    filtered = filter_trades_by_date(all_trades, start_date, end_date)
    overall = analyze_trades(filtered)
    
    # Group stats
    by_signal = {}
    by_ccy = {}
    by_direction = {}
    by_ccy_dir = {}
    by_ccy_signal = {}  # New: CCY -> Signal -> stats
    daily = {}
    
    groups = defaultdict(list)
    for t in filtered:
        groups[t['_signal_id']].append(t)
    for sid, trades in groups.items():
        stats = analyze_trades(trades)
        stats['ea'] = signals_data.get(sid, {}).get('ea', get_ea_from_signal(sid))
        by_signal[sid] = stats
    
    ccy_groups = defaultdict(list)
    for t in filtered:
        ccy_groups[t.get('Symbol', 'UNK')].append(t)
    for ccy, trades in sorted(ccy_groups.items(), key=lambda x: analyze_trades(x[1])['total_pnl'], reverse=True):
        by_ccy[ccy] = analyze_trades(trades)
        # Build by_ccy_signal for accordion
        ccy_signal_groups = defaultdict(list)
        for t in trades:
            ccy_signal_groups[t['_signal_id']].append(t)
        by_ccy_signal[ccy] = []
        for sid, s_trades in sorted(ccy_signal_groups.items(), key=lambda x: analyze_trades(x[1])['total_pnl'], reverse=True):
            s_stats = analyze_trades(s_trades)
            s_stats['signal_id'] = sid
            s_stats['ea'] = signals_data.get(sid, {}).get('ea', get_ea_from_signal(sid))
            # Also breakdown by direction within each signal
            dir_breakdown = {}
            for d, d_trades in defaultdict(list, {t.get('Type', '').lower(): [] for t in s_trades}).items():
                if d in ('buy', 'sell'):
                    dir_trades = [t for t in s_trades if t.get('Type', '').lower() == d]
                    if dir_trades:
                        dir_breakdown[d] = analyze_trades(dir_trades)
            s_stats['by_direction'] = dir_breakdown
            by_ccy_signal[ccy].append(s_stats)
    
    dir_groups = defaultdict(list)
    for t in filtered:
        dir_groups[t.get('Type', '').lower()].append(t)
    for dir, trades in dir_groups.items():
        by_direction[dir] = analyze_trades(trades)
    
    # Build by_direction_ccy for accordion (Direction -> CCY breakdown)
    by_direction_ccy = {}
    for dir, dir_trades in dir_groups.items():
        ccy_in_dir = defaultdict(list)
        for t in dir_trades:
            ccy_in_dir[t.get('Symbol', 'UNK')].append(t)
        by_direction_ccy[dir] = []
        for ccy, c_trades in sorted(ccy_in_dir.items(), key=lambda x: analyze_trades(x[1])['total_pnl'], reverse=True):
            c_stats = analyze_trades(c_trades)
            c_stats['ccy'] = ccy
            # Breakdown by signal within direction-ccy
            sig_in_ccy = defaultdict(list)
            for t in c_trades:
                sig_in_ccy[t['_signal_id']].append(t)
            c_stats['by_signal'] = []
            for sid, sig_trades in sorted(sig_in_ccy.items(), key=lambda x: analyze_trades(x[1])['total_pnl'], reverse=True):
                sig_stats = analyze_trades(sig_trades)
                sig_stats['signal_id'] = sid
                sig_stats['ea'] = signals_data.get(sid, {}).get('ea', get_ea_from_signal(sid))
                c_stats['by_signal'].append(sig_stats)
            by_direction_ccy[dir].append(c_stats)
    
    ccy_dir_groups = defaultdict(list)
    for t in filtered:
        key = f"{t.get('Symbol','UNK')}_{t.get('Type','').lower()}"
        ccy_dir_groups[key].append(t)
    for key, trades in sorted(ccy_dir_groups.items(), key=lambda x: analyze_trades(x[1])['total_pnl'], reverse=True):
        by_ccy_dir[key] = analyze_trades(trades)
        # Build by_ccy_direction_signal for accordion
        sig_in_ccydir = defaultdict(list)
        for t in trades:
            sig_in_ccydir[t['_signal_id']].append(t)
        by_ccy_dir[key]['by_signal'] = []
        for sid, sig_trades in sorted(sig_in_ccydir.items(), key=lambda x: analyze_trades(x[1])['total_pnl'], reverse=True):
            sig_stats = analyze_trades(sig_trades)
            sig_stats['signal_id'] = sid
            sig_stats['ea'] = signals_data.get(sid, {}).get('ea', get_ea_from_signal(sid))
            by_ccy_dir[key]['by_signal'].append(sig_stats)
    
    day_groups = defaultdict(list)
    for t in filtered:
        tt = parse_trade_time(t.get('Open Time', ''))
        if tt:
            day_groups[tt.strftime('%Y-%m-%d')].append(t)
    for day, trades in sorted(day_groups.items()):
        daily[day] = analyze_trades(trades)
    
    signal_comp = [{'signal_id': s, 'ea': v['ea'], 'count': v['count'], 'win_rate': v['win_rate'],
                    'total_pnl': v['total_pnl'], 'total_pips': v['total_pips'], 'profit_factor': v['profit_factor']}
                   for s, v in sorted(by_signal.items(), key=lambda x: x[1]['total_pnl'], reverse=True)]
    
    return {
        'meta': {'generated_at': datetime.now().isoformat(), 'start_date': start_date.strftime('%Y-%m-%d'),
                 'end_date': end_date.strftime('%Y-%m-%d'), 'signal_filter': signal_id,
                 'total_signals': len(by_signal), 'total_trades': len(filtered)},
        'overall': overall, 'by_signal': by_signal, 'by_ccy': by_ccy, 'by_direction': by_direction,
        'by_ccy_direction': by_ccy_dir, 'by_ccy_signal': by_ccy_signal,
        'by_direction_ccy': by_direction_ccy, 'daily': daily, 'signal_comparison': signal_comp,
    }


def get_ea_style(ea: str) -> str:
    """Get CSS style for EA badge."""
    bg, fg = EA_COLORS.get(ea.split('/')[0], EA_COLORS['UNK'])
    return f'background:{bg};color:{fg}'


def get_signal_link(signal_id: str) -> str:
    """Generate link to Signal report if exists."""
    import os
    base_path = Path(__file__).parent.parent  # workspace root
    reports_dir = base_path / 'docs' / 'reports'
    # Check Signal_Deep_Analysis first
    deep_path = reports_dir / f'Signal_Deep_Analysis_{signal_id}.html'
    if deep_path.exists():
        return f'<a href="../reports/Signal_Deep_Analysis_{signal_id}.html" class="signal-link">{signal_id}</a>'
    # Check martin_v4 report
    martin_path = reports_dir / f'martin_v4_{signal_id}.html'
    if martin_path.exists():
        return f'<a href="../reports/martin_v4_{signal_id}.html" class="signal-link">{signal_id}</a>'
    # No report exists, return plain text
    return signal_id


def generate_html(report: dict, output_path: Path) -> None:
    """Generate HTML report with TSA style."""
    meta, overall = report['meta'], report['overall']
    
    # Calculate sidebar path depth based on output location
    # reviews/monthly/*.html -> ../../sidebar.js
    # reviews/weekly/*.html -> ../../sidebar.js
    # reviews/daily/*.html -> ../../sidebar.js
    # reviews/index.html -> ../sidebar.js
    rel_path = output_path.relative_to(Path(__file__).parent.parent / 'docs')
    path_parts = rel_path.parts
    if len(path_parts) > 1:
        # In subdirectory: need to go up two levels (e.g., monthly -> reviews -> docs)
        sidebar_depth = '../../'
    else:
        # In reviews/ root: need to go up one level
        sidebar_depth = '../'
    
    # Build HTML using string concatenation
    lines = []
    lines.append('<!DOCTYPE html>')
    lines.append('<html lang="zh-Hant">')
    lines.append('<head>')
    lines.append('<meta charset="UTF-8">')
    lines.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    lines.append(f'<title>日期覆盤 | {meta["start_date"]} - {meta["end_date"]}</title>')
    lines.append(f'<link rel="stylesheet" href="{sidebar_depth}sidebar.css">')
    lines.append(f'<script src="{sidebar_depth}sidebar.js"></script>')
    lines.append('<style>')
    lines.append('*{margin:0;padding:0;box-sizing:border-box}')
    lines.append('body{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9}')
    lines.append('body.has-sidebar{padding-left:240px}')
    lines.append('.container{max-width:1200px;margin:auto;padding:20px}')
    lines.append('h1{color:#58a6ff;font-size:1.5em;margin-bottom:8px}')
    lines.append('.meta-info{color:#8b949e;font-size:0.85em;margin-bottom:20px}')
    lines.append('.section{background:#161b22;border-radius:8px;padding:16px;margin-bottom:16px;border:1px solid #21262d}')
    lines.append('h2{color:#58a6ff;border-bottom:1px solid #21262d;padding-bottom:6px;margin-bottom:10px;font-size:1em}')
    lines.append('.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}')
    lines.append('.stat-card{background:#0d1117;border-radius:6px;padding:10px;text-align:center}')
    lines.append('.stat-label{color:#8b949e;font-size:0.75em}')
    lines.append('.stat-value{font-size:1.2em;font-weight:600}')
    lines.append('.positive{color:#3fb950}')
    lines.append('.negative{color:#f85149}')
    lines.append('table{width:100%;border-collapse:collapse;font-size:0.8em;margin-top:6px}')
    lines.append('th{background:#21262d;color:#8b949e;padding:6px;text-align:left;border-bottom:1px solid #30363d}')
    lines.append('td{padding:5px;border-bottom:1px solid #21262d}')
    lines.append('tr:hover{background:#1a2332}')
    lines.append('.ea-badge{display:inline-block;padding:2px 6px;border-radius:4px;font-size:0.7em;font-weight:600}')
    lines.append('.tabs{display:flex;gap:6px;margin-bottom:12px;flex-wrap:wrap}')
    lines.append('.tab{padding:6px 14px;background:#21262d;border:1px solid #30363d;border-radius:6px;cursor:pointer;font-size:0.8em}')
    lines.append('.tab:hover{background:#30363d}')
    lines.append('.tab.active{background:#58a6ff;color:#0d1117;border-color:#58a6ff}')
    lines.append('.tab-content{display:none}')
    lines.append('.tab-content.active{display:block}')
    lines.append('footer{text-align:center;margin-top:24px;color:#484f58;font-size:0.7em}')
    # Signal link styles
    lines.append('.signal-link{color:#58a6ff;text-decoration:none;font-weight:500}')
    lines.append('.signal-link:hover{color:#79c0ff;text-decoration:underline}')
    # Accordion styles
    lines.append('.accordion-row{cursor:pointer;user-select:none}')
    lines.append('.accordion-row:hover{background:#1a2332}')
    lines.append('.accordion-toggle{display:inline-block;width:20px;text-align:center;transition:transform 0.2s}')
    lines.append('.accordion-toggle.open{transform:rotate(90deg)}')
    lines.append('.accordion-detail{display:none}')
    lines.append('.accordion-detail.show{display:table-row}')
    lines.append('.accordion-inner{padding:0}')
    lines.append('.accordion-table{margin:4px 0 4px 24px;width:calc(100% - 24px);font-size:0.9em}')
    lines.append('.accordion-table th{background:#161b22;font-size:0.85em}')
    lines.append('.accordion-table td{padding:4px 6px;border-bottom:1px solid #1c2128}')
    lines.append('.accordion-table tr:hover{background:#1a2332}')
    lines.append('.ea-badge-sm{display:inline-block;padding:1px 4px;border-radius:3px;font-size:0.65em;font-weight:600}')
    lines.append('.sub-dir{font-size:0.8em;padding:1px 5px;border-radius:3px;font-weight:600}')
    lines.append('.sub-buy{background:#0d47a1;color:#90caf9}')
    lines.append('.sub-sell{background:#b71c1c;color:#ef9a9a}')
    lines.append('</style>')
    lines.append('</head>')
    lines.append('<body>')
    lines.append('<div class="container">')
    lines.append('<h1>日期覆盤報告</h1>')
    lines.append(f'<div class="meta-info">期間: {meta["start_date"]} 至 {meta["end_date"]} | Signals: {meta["total_signals"]} | Trades: {meta["total_trades"]}</div>')
    
    # Overall stats
    wr_class = 'positive' if overall['win_rate'] >= 50 else 'negative'
    pnl_class = 'positive' if overall['total_pnl'] >= 0 else 'negative'
    pf_str = f"{overall['profit_factor']:.2f}" if isinstance(overall['profit_factor'], float) else str(overall['profit_factor'])
    
    lines.append('<div class="section">')
    lines.append('<h2>總體表現</h2>')
    lines.append('<div class="stats-grid">')
    lines.append(f'<div class="stat-card"><div class="stat-label">總交易</div><div class="stat-value">{overall["count"]:,}</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">勝率</div><div class="stat-value {wr_class}">{overall["win_rate"]:.1f}%</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">總盈虧</div><div class="stat-value {pnl_class}">${overall["total_pnl"]:,.2f}</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">總Pips</div><div class="stat-value">{overall["total_pips"]:,.1f}</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">盈利因子</div><div class="stat-value">{pf_str}</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">平均持倉</div><div class="stat-value">{overall["avg_hold_hours"]:.1f}h</div></div>')
    lines.append('</div>')
    lines.append('<div class="stats-grid" style="margin-top:10px">')
    lines.append(f'<div class="stat-card"><div class="stat-label">勝場</div><div class="stat-value positive">{overall["win_count"]:,}</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">敗場</div><div class="stat-value negative">{overall["loss_count"]:,}</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">平均勝</div><div class="stat-value positive">${overall["avg_win"]:,.2f}</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">平均敗</div><div class="stat-value negative">-${overall["avg_loss"]:,.2f}</div></div>')
    lines.append('</div>')
    lines.append('</div>')
    
    # Tabs
    lines.append('<div class="tabs">')
    lines.append('<div class="tab active" onclick="showTab(\'signal\')">按Signal</div>')
    lines.append('<div class="tab" onclick="showTab(\'ccy\')">按CCY</div>')
    lines.append('<div class="tab" onclick="showTab(\'dir\')">按方向</div>')
    lines.append('<div class="tab" onclick="showTab(\'ccydir\')">CCY+方向</div>')
    lines.append('<div class="tab" onclick="showTab(\'daily\')">每日</div>')
    lines.append('</div>')
    
    # Signal comparison
    lines.append('<div id="tab-signal" class="tab-content active">')
    lines.append('<div class="section"><h2>Signal對比</h2>')
    lines.append('<table><thead><tr><th>Signal</th><th>EA</th><th>Trades</th><th>WR</th><th>PnL</th><th>Pips</th><th>PF</th><th>Hold</th></tr></thead><tbody>')
    for item in report['signal_comparison']:
        pnl_cls = 'positive' if item['total_pnl'] >= 0 else 'negative'
        pf_s = f"{item['profit_factor']:.2f}" if isinstance(item['profit_factor'], float) else str(item['profit_factor'])
        lines.append(f'<tr><td>{get_signal_link(str(item["signal_id"]))}</td><td><span class="ea-badge" style="{get_ea_style(item["ea"]) }">{item["ea"]}</span></td><td>{item["count"]:,}</td><td>{item["win_rate"]:.1f}%</td><td class="{pnl_cls}">${item["total_pnl"]:,.2f}</td><td>{item["total_pips"]:,.1f}</td><td>{pf_s}</td><td>{item.get("avg_hold_hours",0):.1f}h</td></tr>')
    lines.append('</tbody></table></div></div>')
    
    # CCY with accordion
    lines.append('<div id="tab-ccy" class="tab-content"><div class="section"><h2>按貨幣對</h2>')
    lines.append('<table><thead><tr><th style="width:24px"></th><th>CCY</th><th>Trades</th><th>WR</th><th>PnL</th><th>Pips</th><th>PF</th><th>Hold</th></tr></thead><tbody>')
    for ccy, stats in report['by_ccy'].items():
        pnl_cls = 'positive' if stats['total_pnl'] >= 0 else 'negative'
        pf_s = f"{stats['profit_factor']:.2f}" if isinstance(stats['profit_factor'], float) else str(stats['profit_factor'])
        ccy_id = ccy.replace('-', '')
        lines.append(f'<tr class="accordion-row" onclick="toggleAccordion(\'{ccy_id}\')"><td><span class="accordion-toggle" id="toggle-{ccy_id}">▶</span></td><td>{ccy}</td><td>{stats["count"]:,}</td><td>{stats["win_rate"]:.1f}%</td><td class="{pnl_cls}">${stats["total_pnl"]:,.2f}</td><td>{stats["total_pips"]:,.1f}</td><td>{pf_s}</td><td>{stats.get("avg_hold_hours",0):.1f}h</td></tr>')
        # Accordion detail: Signal breakdown for this CCY
        detail_rows = report.get('by_ccy_signal', {}).get(ccy, [])
        if detail_rows:
            lines.append(f'<tr class="accordion-detail" id="detail-{ccy_id}"><td colspan="8" class="accordion-inner">')
            lines.append('<table class="accordion-table"><thead><tr><th>Signal</th><th>EA</th><th>Dir</th><th>Trades</th><th>WR</th><th>PnL</th><th>Pips</th><th>PF</th><th>Hold</th></tr></thead><tbody>')
            for s in detail_rows:
                ea = s.get('ea', 'UNK')
                ea_style = get_ea_style(ea)
                # Show direction breakdown if available
                dir_bd = s.get('by_direction', {})
                if dir_bd:
                    n_dirs = len(dir_bd)
                    for idx, (d, ds) in enumerate(dir_bd.items()):
                        d_pnl_cls = 'positive' if ds['total_pnl'] >= 0 else 'negative'
                        d_label = 'Buy' if d == 'buy' else 'Sell'
                        d_cls = 'sub-buy' if d == 'buy' else 'sub-sell'
                        d_pf = f"{ds['profit_factor']:.2f}" if isinstance(ds.get('profit_factor'), float) else str(ds.get('profit_factor', '-'))
                        if idx == 0:
                            # First row: include Signal, EA with rowspan
                            lines.append(f'<tr><td rowspan="{n_dirs}">{get_signal_link(str(s["signal_id"]))}</td><td rowspan="{n_dirs}"><span class="ea-badge-sm" style="{ea_style}">{ea}</span></td><td><span class="sub-dir {d_cls}">{d_label}</span></td><td>{ds["count"]:,}</td><td>{ds["win_rate"]:.1f}%</td><td class="{d_pnl_cls}">${ds["total_pnl"]:,.2f}</td><td>{ds.get("total_pips",0):,.1f}</td><td>{d_pf}</td><td>{ds.get("avg_hold_hours",0):.1f}h</td></tr>')
                        else:
                            # Subsequent rows: skip Signal and EA columns
                            lines.append(f'<tr><td><span class="sub-dir {d_cls}">{d_label}</span></td><td>{ds["count"]:,}</td><td>{ds["win_rate"]:.1f}%</td><td class="{d_pnl_cls}">${ds["total_pnl"]:,.2f}</td><td>{ds.get("total_pips",0):,.1f}</td><td>{d_pf}</td><td>{ds.get("avg_hold_hours",0):.1f}h</td></tr>')
                else:
                    s_pf = f"{s['profit_factor']:.2f}" if isinstance(s.get('profit_factor'), float) else str(s.get('profit_factor', '-'))
                    lines.append(f'<tr><td>{get_signal_link(str(s["signal_id"]))}</td><td><span class="ea-badge-sm" style="{ea_style}">{ea}</span></td><td>-</td><td>{s["count"]:,}</td><td>{s["win_rate"]:.1f}%</td><td class="{pnl_cls}">${s["total_pnl"]:,.2f}</td><td>{s.get("total_pips",0):,.1f}</td><td>{s_pf}</td><td>{s.get("avg_hold_hours",0):.1f}h</td></tr>')
            lines.append('</tbody></table></td></tr>')
    lines.append('</tbody></table></div></div>')
    
    # Direction with accordion
    lines.append('<div id="tab-dir" class="tab-content"><div class="section"><h2>按方向</h2>')
    lines.append('<table><thead><tr><th style="width:24px"></th><th>方向</th><th>Trades</th><th>WR</th><th>PnL</th><th>Pips</th><th>PF</th><th>Hold</th></tr></thead><tbody>')
    for dir_key, stats in report['by_direction'].items():
        pnl_cls = 'positive' if stats['total_pnl'] >= 0 else 'negative'
        pf_s = f"{stats['profit_factor']:.2f}" if isinstance(stats['profit_factor'], float) else str(stats['profit_factor'])
        label = 'Buy' if dir_key == 'buy' else 'Sell' if dir_key == 'sell' else dir_key
        dir_id = dir_key
        lines.append(f'<tr class="accordion-row" onclick="toggleAccordion(\'{dir_id}\')"><td><span class="accordion-toggle" id="toggle-{dir_id}">▶</span></td><td>{label}</td><td>{stats["count"]:,}</td><td>{stats["win_rate"]:.1f}%</td><td class="{pnl_cls}">${stats["total_pnl"]:,.2f}</td><td>{stats["total_pips"]:,.1f}</td><td>{pf_s}</td><td>{stats.get("avg_hold_hours",0):.1f}h</td></tr>')
        # Accordion detail: CCY breakdown for this direction
        detail_rows = report.get('by_direction_ccy', {}).get(dir_key, [])
        if detail_rows:
            lines.append(f'<tr class="accordion-detail" id="detail-{dir_id}"><td colspan="8" class="accordion-inner">')
            lines.append('<table class="accordion-table"><thead><tr><th>CCY</th><th>Signal</th><th>EA</th><th>Trades</th><th>WR</th><th>PnL</th><th>Pips</th><th>PF</th><th>Hold</th></tr></thead><tbody>')
            for c in detail_rows:
                sig_rows = c.get('by_signal', [])
                n_sigs = max(len(sig_rows), 1)
                for i, s in enumerate(sig_rows):
                    ea = s.get('ea', 'UNK')
                    ea_style = get_ea_style(ea)
                    s_pnl_cls = 'positive' if s['total_pnl'] >= 0 else 'negative'
                    s_pf = f"{s['profit_factor']:.2f}" if isinstance(s.get('profit_factor'), float) else str(s.get('profit_factor', '-'))
                    if i == 0:
                        # First row: CCY with rowspan
                        rowspan_attr = f' rowspan="{n_sigs}"' if n_sigs > 1 else ''
                        lines.append(f'<tr><td{rowspan_attr}>{c["ccy"]}</td><td>{get_signal_link(str(s["signal_id"]))}</td><td><span class="ea-badge-sm" style="{ea_style}">{ea}</span></td><td>{s["count"]:,}</td><td>{s["win_rate"]:.1f}%</td><td class="{s_pnl_cls}">${s["total_pnl"]:,.2f}</td><td>{s.get("total_pips",0):,.1f}</td><td>{s_pf}</td><td>{s.get("avg_hold_hours",0):.1f}h</td></tr>')
                    else:
                        # Subsequent rows: no CCY cell (covered by rowspan)
                        lines.append(f'<tr><td>{get_signal_link(str(s["signal_id"]))}</td><td><span class="ea-badge-sm" style="{ea_style}">{ea}</span></td><td>{s["count"]:,}</td><td>{s["win_rate"]:.1f}%</td><td class="{s_pnl_cls}">${s["total_pnl"]:,.2f}</td><td>{s.get("total_pips",0):,.1f}</td><td>{s_pf}</td><td>{s.get("avg_hold_hours",0):.1f}h</td></tr>')
                if not sig_rows:
                    ccy_pnl_cls = 'positive' if c['total_pnl'] >= 0 else 'negative'
                    ccy_pf = f"{c['profit_factor']:.2f}" if isinstance(c.get('profit_factor'), float) else str(c.get('profit_factor', '-'))
                    lines.append(f'<tr><td>{c["ccy"]}</td><td>-</td><td>-</td><td>{c["count"]:,}</td><td>{c["win_rate"]:.1f}%</td><td class="{ccy_pnl_cls}">${c["total_pnl"]:,.2f}</td><td>{c.get("total_pips",0):,.1f}</td><td>{ccy_pf}</td><td>{c.get("avg_hold_hours",0):.1f}h</td></tr>')
            lines.append('</tbody></table></td></tr>')
    lines.append('</tbody></table></div></div>')
    
    # CCY+Direction with accordion
    lines.append('<div id="tab-ccydir" class="tab-content"><div class="section"><h2>CCY+方向</h2>')
    lines.append('<table><thead><tr><th style="width:24px"></th><th>CCY</th><th>Dir</th><th>Trades</th><th>WR</th><th>PnL</th><th>Pips</th><th>PF</th><th>Hold</th></tr></thead><tbody>')
    for key, stats in list(report['by_ccy_direction'].items())[:50]:
        pnl_cls = 'positive' if stats['total_pnl'] >= 0 else 'negative'
        pf_s = f"{stats['profit_factor']:.2f}" if isinstance(stats['profit_factor'], float) else str(stats['profit_factor'])
        parts = key.rsplit('_', 1)
        ccy, d = parts[0] if len(parts) > 1 else key, parts[1] if len(parts) > 1 else ''
        dl = 'Buy' if d == 'buy' else 'Sell' if d == 'sell' else d
        ccydir_id = key.replace('-', '')
        lines.append(f'<tr class="accordion-row" onclick="toggleAccordion(\'{ccydir_id}\')"><td><span class="accordion-toggle" id="toggle-{ccydir_id}">▶</span></td><td>{ccy}</td><td>{dl}</td><td>{stats["count"]:,}</td><td>{stats["win_rate"]:.1f}%</td><td class="{pnl_cls}">${stats["total_pnl"]:,.2f}</td><td>{stats["total_pips"]:,.1f}</td><td>{pf_s}</td><td>{stats.get("avg_hold_hours",0):.1f}h</td></tr>')
        # Accordion detail: Signal breakdown
        sig_rows = stats.get('by_signal', [])
        if sig_rows:
            lines.append(f'<tr class="accordion-detail" id="detail-{ccydir_id}"><td colspan="9" class="accordion-inner">')
            lines.append('<table class="accordion-table"><thead><tr><th>Signal</th><th>EA</th><th>Trades</th><th>WR</th><th>PnL</th><th>Pips</th><th>PF</th><th>Hold</th></tr></thead><tbody>')
            for s in sig_rows:
                ea = s.get('ea', 'UNK')
                ea_style = get_ea_style(ea)
                s_pnl_cls = 'positive' if s['total_pnl'] >= 0 else 'negative'
                s_pf = f"{s['profit_factor']:.2f}" if isinstance(s.get('profit_factor'), float) else str(s.get('profit_factor', '-'))
                lines.append(f'<tr><td>{get_signal_link(str(s["signal_id"]))}</td><td><span class="ea-badge-sm" style="{ea_style}">{ea}</span></td><td>{s["count"]:,}</td><td>{s["win_rate"]:.1f}%</td><td class="{s_pnl_cls}">${s["total_pnl"]:,.2f}</td><td>{s.get("total_pips",0):,.1f}</td><td>{s_pf}</td><td>{s.get("avg_hold_hours",0):.1f}h</td></tr>')
            lines.append('</tbody></table></td></tr>')
    lines.append('</tbody></table></div></div>')
    
    # Daily
    lines.append('<div id="tab-daily" class="tab-content"><div class="section"><h2>每日明細</h2>')
    lines.append('<table><thead><tr><th>Date</th><th>Trades</th><th>WR</th><th>PnL</th><th>Pips</th></tr></thead><tbody>')
    for day, stats in report['daily'].items():
        pnl_cls = 'positive' if stats['total_pnl'] >= 0 else 'negative'
        lines.append(f'<tr><td>{day}</td><td>{stats["count"]:,}</td><td>{stats["win_rate"]:.1f}%</td><td class="{pnl_cls}">${stats["total_pnl"]:,.2f}</td><td>{stats["total_pips"]:,.1f}</td></tr>')
    lines.append('</tbody></table></div></div>')
    
    lines.append(f'<footer>Generated by TSA | {meta["generated_at"]}</footer>')
    lines.append('</div>')
    lines.append('<script>')
    lines.append('function showTab(id){')
    lines.append('  document.querySelectorAll(".tab-content").forEach(function(e){e.classList.remove("active")});')
    lines.append('  document.querySelectorAll(".tab").forEach(function(e){e.classList.remove("active")});')
    lines.append('  document.getElementById("tab-"+id).classList.add("active");')
    lines.append('  event.target.classList.add("active");')
    lines.append('}')
    lines.append('function toggleAccordion(id){')
    lines.append('  var detail=document.getElementById("detail-"+id);')
    lines.append('  var toggle=document.getElementById("toggle-"+id);')
    lines.append('  if(!detail||!toggle)return;')
    lines.append('  var isOpen=detail.classList.contains("show");')
    lines.append('  detail.classList.toggle("show");')
    lines.append('  toggle.classList.toggle("open");')
    lines.append('  toggle.textContent=isOpen?"▶":"▼";')
    lines.append('}')
    lines.append('</script>')
    lines.append('</body>')
    lines.append('</html>')
    
    html = '\n'.join(lines)
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f"HTML saved: {output_path}")


def main():
    ap = argparse.ArgumentParser(description='Date Range Review - TSA整合版')
    ap.add_argument('--start-date', required=True)
    ap.add_argument('--end-date', required=True)
    ap.add_argument('--signal-id')
    ap.add_argument('--output', default=str(DEFAULT_OUTPUT))
    ap.add_argument('--data-dir', default=str(DATA_DIR))
    ap.add_argument('--use-close-time', action='store_true')
    ap.add_argument('--json-only', action='store_true')
    ap.add_argument('--html-only', action='store_true')
    ap.add_argument('--period', choices=['daily', 'weekly', 'monthly'], help='Output to period subfolder')
    args = ap.parse_args()
    
    start = datetime.strptime(args.start_date, '%Y-%m-%d')
    end = datetime.strptime(args.end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
    
    if start > end:
        print("Error: start must <= end", file=sys.stderr)
        sys.exit(1)
    
    data_dir = Path(args.data_dir)
    if not data_dir.exists():
        print(f"Error: data dir not found: {data_dir}", file=sys.stderr)
        sys.exit(1)
    
    print(f"Loading from: {data_dir}")
    signals = load_all_signal_data(data_dir)
    print(f"Loaded {len(signals)} signals")
    
    print(f"Analyzing: {args.start_date} to {args.end_date}")
    report = generate_report(signals, start, end, args.signal_id)
    
    output = Path(args.output)
    if args.period:
        output = output / args.period
    
    base = f"review_{args.start_date}_{args.end_date}"
    if args.signal_id:
        base += f"_signal_{args.signal_id}"
    
    if not args.html_only:
        json_path = output / f"{base}.json"
        json_path.parent.mkdir(parents=True, exist_ok=True)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"JSON saved: {json_path}")
    
    if not args.json_only:
        html_path = output / f"{base}.html"
        generate_html(report, html_path)
    
    # Update index.json for the period
    if args.period:
        update_index_json(output, args.period, {
            'start_date': args.start_date,
            'end_date': args.end_date,
            'filename': f"{base}.html",
            'signals': report['meta']['total_signals'],
            'trades': report['meta']['total_trades'],
            'win_rate': report['overall']['win_rate'],
            'total_pnl': report['overall']['total_pnl'],
        })
    
    print(f"\n{'='*50}")
    print(f"Period: {args.start_date} to {args.end_date}")
    print(f"Trades: {report['overall']['count']:,}")
    print(f"Win Rate: {report['overall']['win_rate']:.1f}%")
    print(f"PnL: ${report['overall']['total_pnl']:,.2f}")
    print(f"Signals: {report['meta']['total_signals']}")
    print(f"{'='*50}")


def update_index_json(output_dir: Path, period: str, report_info: dict) -> None:
    """Update the index.json file for a period."""
    import json
    index_path = output_dir / 'index.json'
    
    # Load existing index
    if index_path.exists():
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        except:
            index_data = {'period': period, 'reports': []}
    else:
        index_data = {'period': period, 'reports': []}
    
    # Check if report already exists
    reports = index_data.get('reports', [])
    key = f"{report_info['start_date']}_{report_info['end_date']}"
    existing = [i for i, r in enumerate(reports) if f"{r.get('start_date','')}_{r.get('end_date','')}" == key]
    
    if existing:
        # Update existing
        reports[existing[0]] = report_info
    else:
        # Add new
        reports.append(report_info)
    
    # Sort by start_date descending
    reports.sort(key=lambda x: x.get('start_date', ''), reverse=True)
    
    # Keep only latest 20 reports
    index_data['reports'] = reports[:20]
    
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, ensure_ascii=False, indent=2)
    print(f"Index updated: {index_path}")


if __name__ == '__main__':
    main()