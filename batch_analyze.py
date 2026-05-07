#!/usr/bin/env python3
"""
Batch Signal Analysis — Process all AlgoForest Signals with CSV data
Generates comprehensive ranking report in HTML format.
"""

import os
import sys
import json
import logging
import traceback
from pathlib import Path
from datetime import datetime
from collections import defaultdict

import numpy as np
import pandas as pd

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from src.csv_parser import parse_csv
from src.position_builder import build_positions
from src.entry_quality import evaluate_positions
from src.statistics import (
    calculate_overall_stats, calculate_symbol_stats,
    calculate_layer_stats, calculate_time_stats,
    calculate_direction_stats
)

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

SIGNAL_DIR = '/mnt/c/Users/Alvin/Downloads/Set File From Signal Page'
OUTPUT_DIR = BASE_DIR / 'output'


def find_csv_for_signal(signal_id: str) -> str:
    """Find CSV file for a given signal ID."""
    signal_dir = os.path.join(SIGNAL_DIR, signal_id)
    if not os.path.isdir(signal_dir):
        return None
    
    for f in os.listdir(signal_dir):
        if f.endswith('.csv'):
            return os.path.join(signal_dir, f)
    return None


def analyze_signal(csv_path: str) -> dict:
    """Run lightweight analysis on a single signal CSV (no market data download)."""
    try:
        trades = parse_csv(csv_path)
        if trades.empty:
            return None
        
        positions = build_positions(trades)
        if not positions:
            return None
        
        positions = evaluate_positions(positions)
        
        # Core stats
        overall = calculate_overall_stats(positions)
        layer_stats = calculate_layer_stats(positions)
        symbol_stats = calculate_symbol_stats(positions)
        
        # Win/Loss
        wins = [p for p in positions if p['net_profit'] > 0]
        losses = [p for p in positions if p['net_profit'] <= 0]
        
        # L1-only and L4+ analysis
        l1_only = [p for p in positions if p['max_layer'] == 1]
        l4_plus = [p for p in positions if p['max_layer'] >= 4]
        l4_plus_wins = [p for p in l4_plus if p['net_profit'] > 0]
        
        # Entry scores
        entry_scores = [p.get('entry_quality', {}).get('score', 0) for p in positions]
        avg_entry_score = np.mean(entry_scores) if entry_scores else 0
        
        # Strategy scores
        strategy_scores = [p.get('strategy_quality', {}).get('score', 0) for p in positions]
        avg_strategy_score = np.mean(strategy_scores) if strategy_scores else 0
        
        # L4+ recovery rate
        l4_recovery_rate = (len(l4_plus_wins) / len(l4_plus) * 100) if l4_plus else 0
        
        # Symbols
        symbols = list(set(p['symbol'] for p in positions if p.get('symbol')))
        
        # Date range
        open_times = [p['open_time'] for p in positions if p.get('open_time')]
        close_times = [p['close_time'] for p in positions if p.get('close_time')]
        date_from = min(open_times).strftime('%Y-%m-%d') if open_times else '?'
        date_to = max(close_times).strftime('%Y-%m-%d') if close_times else '?'
        
        # Layer distribution
        layer_dist = defaultdict(int)
        for p in positions:
            layer_dist[int(p['max_layer'])] += 1
        
        # Avg win / avg loss
        avg_win = np.mean([p['net_profit'] for p in wins]) if wins else 0
        avg_loss = np.mean([p['net_profit'] for p in losses]) if losses else 0
        win_loss_ratio = abs(avg_win / avg_loss) if avg_loss != 0 else 0
        
        # Detect timeframe from comment/pattern
        timeframe = detect_timeframe(positions)
        
        # Detect trade type from comments
        trade_type = detect_trade_type(positions)
        
        # Max consecutive losses
        max_consec_loss = 0
        current_streak = 0
        for p in positions:
            if p['net_profit'] <= 0:
                current_streak += 1
                max_consec_loss = max(max_consec_loss, current_streak)
            else:
                current_streak = 0
        
        # Profit factor (Pips-based)
        pips_wins = [p for p in positions if p.get('net_pips', 0) > 0]
        pips_losses = [p for p in positions if p.get('net_pips', 0) <= 0]
        gross_pips_win = sum(p.get('net_pips', 0) for p in pips_wins)
        gross_pips_loss = abs(sum(p.get('net_pips', 0) for p in pips_losses))
        profit_factor_pips = gross_pips_win / gross_pips_loss if gross_pips_loss > 0 else float('inf')
        
        # Composite score for ranking
        # Weighted: Entry Score 30% + Win Rate 20% + Profit Factor 20% + L4 Recovery 15% + Risk (inverse DD) 15%
        risk_score = max(0, 100 - abs(overall.get('max_dd_pips', 0)) / 50) if overall.get('max_dd_pips', 0) != 0 else 100
        composite = (
            avg_entry_score * 0.30 +
            min(overall.get('win_rate', 0), 100) * 0.20 +
            min(profit_factor_pips * 10, 100) * 0.20 +
            l4_recovery_rate * 0.15 +
            risk_score * 0.15
        )
        
        return {
            'signal_id': os.path.basename(os.path.dirname(csv_path)).split()[0],
            'csv_file': os.path.basename(csv_path),
            'total_cycles': len(positions),
            'total_trades': len(trades),
            'win_rate': round(overall.get('win_rate', 0), 2),
            'avg_win': round(avg_win, 2),
            'avg_loss': round(avg_loss, 2),
            'win_loss_ratio': round(win_loss_ratio, 2),
            'total_profit': round(overall.get('total_profit_pips', 0), 2),
            'profit_factor': round(profit_factor_pips, 2),
            'max_dd': round(overall.get('max_dd_pips', 0), 2),
            'avg_layers': round(overall.get('avg_layers', 0), 2),
            'avg_hold_hours': round(overall.get('avg_holding_time_hours', 0), 2),
            'l1_only_count': len(l1_only),
            'l1_only_pct': round(len(l1_only) / len(positions) * 100, 2),
            'l4_plus_count': len(l4_plus),
            'l4_plus_pct': round(len(l4_plus) / len(positions) * 100, 2),
            'l4_recovery_rate': round(l4_recovery_rate, 2),
            'avg_entry_score': round(avg_entry_score, 2),
            'avg_strategy_score': round(avg_strategy_score, 2),
            'composite_score': round(composite, 2),
            'max_consec_loss': max_consec_loss,
            'symbols': symbols,
            'date_from': date_from,
            'date_to': date_to,
            'layer_dist': dict(layer_dist),
            'timeframe': timeframe,
            'trade_type': trade_type,
            'sharpe': round(overall.get('sharpe_ratio', 0), 2),
            'sortino': round(overall.get('sortino_ratio', 0), 2),
            'exposure_pct': round(overall.get('exposure_time_percent', 0), 2),
            'total_swap': round(overall.get('total_swap', 0), 2),
            'total_commission': round(overall.get('total_commission', 0), 2),
        }
    except Exception as e:
        return {'signal_id': os.path.basename(os.path.dirname(csv_path)).split()[0], 'error': str(e)}


def detect_timeframe(positions: list) -> str:
    """Try to detect timeframe from trade comments or holding patterns."""
    comments = set()
    for p in positions:
        for t in p.get('trades', []):
            comment = t.get('Comment', '')
            if comment:
                comments.add(comment)
    
    comment_str = ' '.join(comments).upper()
    
    if 'M5' in comment_str or 'M05' in comment_str:
        return 'M5'
    elif 'M15' in comment_str:
        return 'M15'
    elif 'M30' in comment_str:
        return 'M30'
    elif 'H1' in comment_str:
        return 'H1'
    elif 'H4' in comment_str:
        return 'H4'
    elif 'D1' in comment_str:
        return 'D1'
    
    # Infer from holding time
    avg_hold = np.mean([p['holding_time_hours'] for p in positions])
    if avg_hold < 8:
        return 'M5'
    elif avg_hold < 24:
        return 'M15'
    elif avg_hold < 72:
        return 'M30'
    elif avg_hold < 168:
        return 'H1'
    elif avg_hold < 336:
        return 'H4'
    else:
        return 'D1+'


def detect_trade_type(positions: list) -> str:
    """Detect trade type from comments."""
    comments = set()
    for p in positions:
        for t in p.get('trades', []):
            comment = t.get('Comment', '')
            if comment:
                comments.add(comment.upper())
    
    comment_str = ' '.join(comments)
    
    if 'SMA' in comment_str:
        return 'SMA'
    elif 'RSI' in comment_str:
        return 'RSI'
    elif 'MACD' in comment_str:
        return 'MACD'
    elif 'BB' in comment_str or 'BOLL' in comment_str:
        return 'Bollinger'
    elif 'SCALP' in comment_str:
        return 'Scalp'
    elif 'TREND' in comment_str:
        return 'Trend'
    else:
        return 'Mixed/Other'


def generate_batch_html(results: list, output_path: str):
    """Generate comprehensive HTML report for all signals."""
    
    # Separate successful and failed
    successful = [r for r in results if 'error' not in r]
    failed = [r for r in results if 'error' in r]
    
    # Sort by composite score
    successful.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
    
    # Various rankings
    by_entry = sorted(successful, key=lambda x: x.get('avg_entry_score', 0), reverse=True)
    by_l4_recovery = sorted(successful, key=lambda x: x.get('l4_recovery_rate', 0), reverse=True)
    by_win_rate = sorted(successful, key=lambda x: x.get('win_rate', 0), reverse=True)
    by_profit = sorted(successful, key=lambda x: x.get('total_profit', 0), reverse=True)
    by_risk = sorted(successful, key=lambda x: x.get('max_dd', 0), reverse=True)  # least negative first
    
    # Group by timeframe
    by_timeframe = defaultdict(list)
    for r in successful:
        by_timeframe[r.get('timeframe', 'Unknown')].append(r)
    
    # Group by trade type
    by_type = defaultdict(list)
    for r in successful:
        by_type[r.get('trade_type', 'Unknown')].append(r)
    
    # Aggregate stats
    total_signals = len(successful)
    avg_win_rate = np.mean([r['win_rate'] for r in successful])
    avg_profit = sum(r['total_profit'] for r in successful)
    avg_entry = np.mean([r['avg_entry_score'] for r in successful])
    
    now = datetime.now().strftime('%Y-%m-%d %H:%M HKT')
    
    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>🦀 AlgoForest Signal 批量分析報告</title>
<style>
  :root {{
    --bg: #0a0e17;
    --card: #111827;
    --card2: #1a2332;
    --border: #1e2d3d;
    --text: #e2e8f0;
    --dim: #8899aa;
    --accent: #10b981;
    --accent2: #06b6d4;
    --warn: #f59e0b;
    --danger: #ef4444;
    --good: #22c55e;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 12px;
    max-width: 100%;
  }}
  .header {{
    text-align: center;
    padding: 20px 0;
    border-bottom: 2px solid var(--accent);
    margin-bottom: 16px;
  }}
  .header h1 {{ font-size: 1.4em; color: var(--accent); }}
  .header .sub {{ color: var(--dim); font-size: 0.85em; }}
  .stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px;
    margin-bottom: 16px;
  }}
  .stat-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 14px;
    text-align: center;
  }}
  .stat-card .val {{
    font-size: 1.6em;
    font-weight: 700;
    color: var(--accent);
  }}
  .stat-card .val.warn {{ color: var(--warn); }}
  .stat-card .val.danger {{ color: var(--danger); }}
  .stat-card .val.good {{ color: var(--good); }}
  .stat-card .label {{ font-size: 0.75em; color: var(--dim); margin-top: 4px; }}
  .section {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 16px;
  }}
  .section h2 {{
    font-size: 1.1em;
    color: var(--accent2);
    margin-bottom: 12px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
  }}
  .section h3 {{
    font-size: 0.95em;
    color: var(--accent);
    margin: 12px 0 8px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
    font-size: 0.78em;
  }}
  th {{
    background: var(--card2);
    padding: 8px 6px;
    text-align: center;
    color: var(--accent2);
    font-weight: 600;
    position: sticky;
    top: 0;
    white-space: nowrap;
  }}
  td {{
    padding: 6px;
    text-align: center;
    border-bottom: 1px solid var(--border);
  }}
  tr:hover {{ background: var(--card2); }}
  .rank {{ font-weight: 700; color: var(--accent); }}
  .rank-top {{ color: #fbbf24; }}
  .positive {{ color: var(--good); }}
  .negative {{ color: var(--danger); }}
  .tag {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7em;
    font-weight: 600;
  }}
  .tag-a {{ background: #065f46; color: #6ee7b7; }}
  .tag-b {{ background: #1e3a5f; color: #93c5fd; }}
  .tag-c {{ background: #713f12; color: #fde68a; }}
  .tag-d {{ background: #7f1d1d; color: #fca5a5; }}
  .top10 {{ background: #0c2a1a !important; }}
  .badge {{
    display: inline-block;
    padding: 1px 6px;
    border-radius: 3px;
    font-size: 0.65em;
    font-weight: 700;
    margin-left: 3px;
  }}
  .badge-gold {{ background: #92400e; color: #fde68a; }}
  .badge-silver {{ background: #374151; color: #d1d5db; }}
  .badge-bronze {{ background: #7c2d12; color: #fed7aa; }}
  .copy-badge {{ background: #064e3b; color: #6ee7b7; }}
  .warn-badge {{ background: #713f12; color: #fde68a; }}
  .summary-text {{ font-size: 0.85em; color: var(--dim); line-height: 1.8; }}
  .summary-text strong {{ color: var(--text); }}
  .footer {{
    text-align: center;
    padding: 16px;
    color: var(--dim);
    font-size: 0.75em;
    border-top: 1px solid var(--border);
    margin-top: 16px;
  }}
  .overflow-x {{ overflow-x: auto; }}
  .mini-bar {{
    height: 4px;
    border-radius: 2px;
    background: var(--border);
    margin-top: 3px;
  }}
  .mini-bar-fill {{
    height: 100%;
    border-radius: 2px;
  }}
</style>
</head>
<body>

<div class="header">
  <h1>🦀 AlgoForest Signal 批量分析報告</h1>
  <div class="sub">共分析 {total_signals} 個 Signal · 生成時間：{now}</div>
</div>

<!-- Summary Stats -->
<div class="stats-grid">
  <div class="stat-card">
    <div class="val">{total_signals}</div>
    <div class="label">有效 Signal 數</div>
  </div>
  <div class="stat-card">
    <div class="val">{avg_win_rate:.1f}%</div>
    <div class="label">平均勝率</div>
  </div>
  <div class="stat-card">
    <div class="val {'positive' if avg_profit > 0 else 'negative'}">${avg_profit:,.2f}</div>
    <div class="label">總盈虧</div>
  </div>
  <div class="stat-card">
    <div class="val">{avg_entry:.1f}</div>
    <div class="label">平均入場分數</div>
  </div>
  <div class="stat-card">
    <div class="val">{len(failed)}</div>
    <div class="label">分析失敗</div>
  </div>
</div>
"""
    
    # ── Top 10 Recommendations ──
    top10 = successful[:10]
    html += """
<div class="section">
  <h2>🏆 Top 10 推薦 Signal（綜合評分排名）</h2>
  <p class="summary-text">
    綜合評分 = 入場分數×30% + 勝率×20% + 盈虧因子×20% + L4+回復率×15% + 風險控制×15%
  </p>
  <div class="overflow-x">
  <table>
    <tr>
      <th>#</th>
      <th>Signal ID</th>
      <th>綜合分</th>
      <th>入場分</th>
      <th>勝率</th>
      <th>盈虧因子</th>
      <th>L4+回復率</th>
      <th>總盈虧</th>
      <th>週期</th>
      <th>類型</th>
      <th>Cycles</th>
    </tr>
"""
    medals = ['🥇', '🥈', '🥉'] + [''] * 7
    for i, r in enumerate(top10):
        grade = get_grade(r['composite_score'])
        pf_display = f"{r['profit_factor']:.2f}" if r['profit_factor'] < 100 else "∞"
        html += f"""
    <tr class="top10">
      <td class="rank">{medals[i]}{i+1}</td>
      <td><strong>#{r['signal_id']}</strong></td>
      <td><span class="tag {grade[1]}">{r['composite_score']:.1f}</span></td>
      <td>{r['avg_entry_score']:.1f}</td>
      <td>{r['win_rate']:.1f}%</td>
      <td>{pf_display}</td>
      <td>{r['l4_recovery_rate']:.1f}%</td>
      <td class="{'positive' if r['total_profit'] > 0 else 'negative'}">{r['total_profit']:.1f} pips</td>
      <td>{r['timeframe']}</td>
      <td>{r['trade_type']}</td>
      <td>{r['total_cycles']}</td>
    </tr>"""
    
    html += """
  </table>
  </div>
</div>
"""
    
    # ── Full Ranking Table ──
    html += """
<div class="section">
  <h2>📊 全部 Signal 完整排名</h2>
  <div class="overflow-x">
  <table>
    <tr>
      <th>#</th>
      <th>Signal ID</th>
      <th>綜合分</th>
      <th>入場分</th>
      <th>策略分</th>
      <th>勝率</th>
      <th>盈虧因子</th>
      <th>盈虧比</th>
      <th>總盈虧</th>
      <th>最大回撤</th>
      <th>均層</th>
      <th>L1%</th>
      <th>L4+%</th>
      <th>L4+回復</th>
      <th>連虧</th>
      <th>週期</th>
      <th>類型</th>
      <th>Cycles</th>
      <th>日期範圍</th>
    </tr>
"""
    for i, r in enumerate(successful):
        grade = get_grade(r['composite_score'])
        pf_display = f"{r['profit_factor']:.2f}" if r['profit_factor'] < 100 else "∞"
        profit_cls = 'positive' if r['total_profit'] > 0 else 'negative'
        dd_cls = 'negative' if r['max_dd'] < -50 else ('warn' if r['max_dd'] < -20 else '')
        top_marker = ' class="top10"' if i < 10 else ''
        
        html += f"""
    <tr{top_marker}>
      <td class="rank">{i+1}</td>
      <td><strong>#{r['signal_id']}</strong></td>
      <td><span class="tag {grade[1]}">{r['composite_score']:.1f}</span></td>
      <td>{r['avg_entry_score']:.1f}</td>
      <td>{r['avg_strategy_score']:.1f}</td>
      <td>{r['win_rate']:.1f}%</td>
      <td>{pf_display}</td>
      <td>{r['win_loss_ratio']:.2f}</td>
      <td class="{profit_cls}">{r['total_profit']:.1f} pips</td>
      <td class="{dd_cls}">{r['max_dd']:.1f} pips</td>
      <td>{r['avg_layers']:.1f}</td>
      <td>{r['l1_only_pct']:.0f}%</td>
      <td>{r['l4_plus_pct']:.0f}%</td>
      <td>{r['l4_recovery_rate']:.0f}%</td>
      <td>{r['max_consec_loss']}</td>
      <td>{r['timeframe']}</td>
      <td>{r['trade_type']}</td>
      <td>{r['total_cycles']}</td>
      <td style="font-size:0.65em">{r['date_from']} ~ {r['date_to']}</td>
    </tr>"""
    
    html += """
  </table>
  </div>
</div>
"""
    
    # ── Entry Score Ranking ──
    html += """
<div class="section">
  <h2>🎯 按入場準確度排名（Entry Score）</h2>
  <p class="summary-text">入場分數越高 = 第一層入市質量越好，適合直接跟單</p>
  <div class="overflow-x">
  <table>
    <tr><th>#</th><th>Signal ID</th><th>入場分</th><th>勝率</th><th>L1%</th><th>盈虧因子</th><th>週期</th><th>類型</th></tr>
"""
    for i, r in enumerate(by_entry[:20]):
        html += f"""
    <tr>
      <td>{i+1}</td>
      <td><strong>#{r['signal_id']}</strong></td>
      <td>{r['avg_entry_score']:.1f}</td>
      <td>{r['win_rate']:.1f}%</td>
      <td>{r['l1_only_pct']:.0f}%</td>
      <td>{r['profit_factor']:.2f}</td>
      <td>{r['timeframe']}</td>
      <td>{r['trade_type']}</td>
    </tr>"""
    html += """
  </table>
  </div>
</div>
"""
    
    # ── L4+ Recovery Ranking (Copy on Lose suitability) ──
    l4_signals = [r for r in by_l4_recovery if r['l4_plus_count'] > 0]
    html += f"""
<div class="section">
  <h2>🔄 按 L4+ 回復率排名（Copy on Lose 適合性）</h2>
  <p class="summary-text">
    L4+ 回復率越高 = 高層數倉位最終獲利的比例越高，越適合「輸了加碼」的跟單策略<br>
    共 {len(l4_signals)} 個 Signal 有 L4+ 倉位
  </p>
  <div class="overflow-x">
  <table>
    <tr><th>#</th><th>Signal ID</th><th>L4+回復率</th><th>L4+佔比</th><th>L4+次數</th><th>均層</th><th>勝率</th><th>總盈虧</th></tr>
"""
    for i, r in enumerate(l4_signals[:20]):
        html += f"""
    <tr>
      <td>{i+1}</td>
      <td><strong>#{r['signal_id']}</strong></td>
      <td>{r['l4_recovery_rate']:.1f}%</td>
      <td>{r['l4_plus_pct']:.1f}%</td>
      <td>{r['l4_plus_count']}</td>
      <td>{r['avg_layers']:.1f}</td>
      <td>{r['win_rate']:.1f}%</td>
      <td class="{'positive' if r['total_profit'] > 0 else 'negative'}">{r['total_profit']:.1f} pips</td>
    </tr>"""
    html += """
  </table>
  </div>
</div>
"""
    
    # ── Risk Ranking (least drawdown first) ──
    html += """
<div class="section">
  <h2>⚠️ 按風險回撤排名（最安全 → 最危險）</h2>
  <div class="overflow-x">
  <table>
    <tr><th>#</th><th>Signal ID</th><th>最大回撤</th><th>連虧</th><th>均層</th><th>盈虧因子</th><th>Sharpe</th><th>勝率</th></tr>
"""
    for i, r in enumerate(by_risk[:20]):
        dd_cls = 'negative' if r['max_dd'] < -50 else ('warn' if r['max_dd'] < -20 else '')
        html += f"""
    <tr>
      <td>{i+1}</td>
      <td><strong>#{r['signal_id']}</strong></td>
      <td class="{dd_cls}">{r['max_dd']:.1f} pips</td>
      <td>{r['max_consec_loss']}</td>
      <td>{r['avg_layers']:.1f}</td>
      <td>{r['profit_factor']:.2f}</td>
      <td>{r['sharpe']:.2f}</td>
      <td>{r['win_rate']:.1f}%</td>
    </tr>"""
    html += """
  </table>
  </div>
</div>
"""
    
    # ── By Timeframe ──
    html += """
<div class="section">
  <h2>⏱️ 按時間週期分類</h2>
"""
    for tf in ['M5', 'M15', 'M30', 'H1', 'H4', 'D1+', 'Unknown']:
        tf_list = by_timeframe.get(tf, [])
        if not tf_list:
            continue
        avg_wr = np.mean([r['win_rate'] for r in tf_list])
        avg_pf = np.mean([r['profit_factor'] for r in tf_list if r['profit_factor'] < 100])
        avg_entry_tf = np.mean([r['avg_entry_score'] for r in tf_list])
        total_pl = sum(r['total_profit'] for r in tf_list)
        
        html += f"""
    <h3>{tf} 週期（{len(tf_list)} 個 Signal）</h3>
    <p class="summary-text">
      平均勝率: <strong>{avg_wr:.1f}%</strong> · 
      平均盈虧因子: <strong>{avg_pf:.2f}</strong> · 
      平均入場分: <strong>{avg_entry_tf:.1f}</strong> · 
      總盈虧: <strong class="{'positive' if total_pl > 0 else 'negative'}">{total_pl:.1f} pips</strong>
    </p>
    <div class="overflow-x">
    <table>
      <tr><th>Signal ID</th><th>綜合分</th><th>勝率</th><th>盈虧因子</th><th>L4+回復</th><th>總盈虧</th><th>Cycles</th></tr>
"""
        tf_sorted = sorted(tf_list, key=lambda x: x.get('composite_score', 0), reverse=True)
        for r in tf_sorted:
            html += f"""
      <tr>
        <td><strong>#{r['signal_id']}</strong></td>
        <td>{r['composite_score']:.1f}</td>
        <td>{r['win_rate']:.1f}%</td>
        <td>{r['profit_factor']:.2f}</td>
        <td>{r['l4_recovery_rate']:.0f}%</td>
        <td class="{'positive' if r['total_profit'] > 0 else 'negative'}">{r['total_profit']:.1f} pips</td>
        <td>{r['total_cycles']}</td>
      </tr>"""
        html += """
    </table>
    </div>
"""
    html += "</div>\n"
    
    # ── By Trade Type ──
    html += """
<div class="section">
  <h2>📈 按交易類型分類</h2>
"""
    for tt in sorted(by_type.keys()):
        tt_list = by_type[tt]
        avg_wr = np.mean([r['win_rate'] for r in tt_list])
        avg_pf = np.mean([r['profit_factor'] for r in tt_list if r['profit_factor'] < 100])
        total_pl = sum(r['total_profit'] for r in tt_list)
        
        html += f"""
    <h3>{tt}（{len(tt_list)} 個 Signal）</h3>
    <p class="summary-text">
      平均勝率: <strong>{avg_wr:.1f}%</strong> · 
      平均盈虧因子: <strong>{avg_pf:.2f}</strong> · 
      總盈虧: <strong class="{'positive' if total_pl > 0 else 'negative'}">{total_pl:.1f} pips</strong>
    </p>
    <div class="overflow-x">
    <table>
      <tr><th>Signal ID</th><th>綜合分</th><th>勝率</th><th>盈虧因子</th><th>入場分</th><th>L4+回復</th><th>總盈虧</th><th>週期</th></tr>
"""
        tt_sorted = sorted(tt_list, key=lambda x: x.get('composite_score', 0), reverse=True)
        for r in tt_sorted:
            html += f"""
      <tr>
        <td><strong>#{r['signal_id']}</strong></td>
        <td>{r['composite_score']:.1f}</td>
        <td>{r['win_rate']:.1f}%</td>
        <td>{r['profit_factor']:.2f}</td>
        <td>{r['avg_entry_score']:.1f}</td>
        <td>{r['l4_recovery_rate']:.0f}%</td>
        <td class="{'positive' if r['total_profit'] > 0 else 'negative'}">{r['total_profit']:.1f} pips</td>
        <td>{r['timeframe']}</td>
      </tr>"""
        html += """
    </table>
    </div>
"""
    html += "</div>\n"
    
    # ── Copy Trade Recommendations ──
    # Find signals best for copy trading: high entry score + high L4 recovery + decent win rate
    copy_candidates = [r for r in successful if r['avg_entry_score'] >= 50 and r['win_rate'] >= 60]
    copy_candidates.sort(key=lambda x: x['composite_score'], reverse=True)
    
    html += f"""
<div class="section">
  <h2>📋 跟單建議（Copy Trade Recommendations）</h2>
  <p class="summary-text">
    篩選條件：入場分數 ≥ 50 + 勝率 ≥ 60%<br>
    符合條件的 Signal：{len(copy_candidates)} 個
  </p>
  <div class="overflow-x">
  <table>
    <tr><th>#</th><th>Signal ID</th><th>綜合分</th><th>入場分</th><th>勝率</th><th>L4+回復</th><th>盈虧因子</th><th>回撤</th><th>建議</th></tr>
"""
    for i, r in enumerate(copy_candidates[:15]):
        rec = get_copy_recommendation(r)
        html += f"""
    <tr>
      <td>{i+1}</td>
      <td><strong>#{r['signal_id']}</strong></td>
      <td>{r['composite_score']:.1f}</td>
      <td>{r['avg_entry_score']:.1f}</td>
      <td>{r['win_rate']:.1f}%</td>
      <td>{r['l4_recovery_rate']:.0f}%</td>
      <td>{r['profit_factor']:.2f}</td>
      <td>{r['max_dd']:.1f} pips</td>
      <td>{rec}</td>
    </tr>"""
    html += """
  </table>
  </div>
</div>
"""
    
    # ── Failed Signals ──
    if failed:
        html += """
<div class="section">
  <h2>❌ 分析失敗的 Signal</h2>
  <div class="overflow-x">
  <table>
    <tr><th>Signal ID</th><th>錯誤信息</th></tr>
"""
        for r in failed:
            html += f"""
    <tr>
      <td>#{r['signal_id']}</td>
      <td class="negative">{r['error']}</td>
    </tr>"""
        html += """
  </table>
  </div>
</div>
"""
    
    # ── Footer ──
    html += f"""
<div class="footer">
  🦀 丁蟹分析系統 · AlgoForest Signal Batch Analysis<br>
  生成時間：{now} · 共分析 {len(results)} 個 Signal
</div>

</body>
</html>"""
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    return output_path


def get_grade(score: float) -> tuple:
    if score >= 70:
        return ('A', 'tag-a')
    elif score >= 55:
        return ('B', 'tag-b')
    elif score >= 40:
        return ('C', 'tag-c')
    else:
        return ('D', 'tag-d')


def get_copy_recommendation(r: dict) -> str:
    if r['composite_score'] >= 70 and r['avg_entry_score'] >= 65:
        return '⭐ 強烈推薦跟單'
    elif r['composite_score'] >= 60 and r['avg_entry_score'] >= 55:
        return '✅ 推薦跟單'
    elif r['l4_recovery_rate'] >= 80:
        return '🔄 適合 Copy on Lose'
    elif r['composite_score'] >= 50:
        return '⚡ 可嘗試，注意風控'
    else:
        return '⚠️ 需謹慎評估'


def main():
    print("🦀 AlgoForest Signal 批量分析啟動")
    print("=" * 50)
    
    # Find all signal directories
    signal_dirs = []
    for name in os.listdir(SIGNAL_DIR):
        full_path = os.path.join(SIGNAL_DIR, name)
        if os.path.isdir(full_path):
            signal_id = name.split()[0]
            csv_path = find_csv_for_signal(signal_id)
            if csv_path:
                signal_dirs.append((signal_id, csv_path))
    
    print(f"找到 {len(signal_dirs)} 個有 CSV 的 Signal")
    
    # Analyze each signal
    results = []
    for i, (signal_id, csv_path) in enumerate(signal_dirs):
        print(f"\r[{i+1}/{len(signal_dirs)}] 分析 #{signal_id}...", end='', flush=True)
        result = analyze_signal(csv_path)
        if result:
            results.append(result)
        else:
            results.append({'signal_id': signal_id, 'error': 'No valid trades found'})
    
    print(f"\n\n✅ 分析完成：{len([r for r in results if 'error' not in r])} 成功, {len([r for r in results if 'error' in r])} 失敗")
    
    # Save JSON
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    json_path = OUTPUT_DIR / 'batch_analysis_results.json'
    # Convert numpy types for JSON serialization
    def sanitize(obj):
        import numpy as np
        if isinstance(obj, (np.integer,)):
            return int(obj)
        elif isinstance(obj, (np.floating,)):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        raise TypeError(f"Not serializable: {type(obj)}")
    
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=sanitize)
    print(f"📄 JSON: {json_path}")
    
    # Generate HTML
    html_path = OUTPUT_DIR / 'batch_signal_report_20260501.html'
    generate_batch_html(results, str(html_path))
    print(f"📄 HTML: {html_path}")
    
    # Print top 10
    successful = [r for r in results if 'error' not in r]
    successful.sort(key=lambda x: x.get('composite_score', 0), reverse=True)
    
    print(f"\n🏆 Top 10 Signal:")
    for i, r in enumerate(successful[:10]):
        print(f"  {i+1}. #{r['signal_id']} - 綜合分:{r['composite_score']:.1f} "
              f"入場:{r['avg_entry_score']:.1f} 勝率:{r['win_rate']:.1f}% "
              f"PF:{r['profit_factor']:.2f} L4+回復:{r['l4_recovery_rate']:.0f}% "
              f"盈虧:{r['total_profit']:.1f} pips [{r['timeframe']}]")
    
    return results


if __name__ == '__main__':
    results = main()
