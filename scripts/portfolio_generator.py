#!/usr/bin/env python3
"""
Portfolio Generator - 十個投資組合報告生成器

根據老闆確認的十個 Portfolio 設計，生成詳細的投資組合報告。

每個報告包含：
- Signal ID（連結到深度報告）
- CCY、方向、EA 類型、層數、手數
- 計算過程（每手盈利、總盈利、風險評估、建議手數）
- 風險評估（爆倉風險、資金管理建議）
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Dict, List, Any, Optional

# 項目路徑
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / 'data' / 'history'
OUTPUT_DIR = PROJECT_ROOT / 'docs' / 'portfolios'

# Portfolio 定義（老闆確認）
PORTFOLIOS = {
    'P1': {
        'name': 'DW 高勝率組',
        'capital': 1500,
        'target_monthly': 0.50,
        'target_weekly': 0.125,
        'strategy': 'DW EA',
        'signals': ['31593', '17547', '3291'],
        'layers': 'L1-L3',
        'risk_level': 'Medium',
    },
    'P2': {
        'name': 'SMA 穩定組',
        'capital': 1000,
        'target_monthly': 0.20,
        'target_weekly': 0.05,
        'strategy': 'SMA EA',
        'signals': ['16698', '32278', '5001'],
        'layers': 'L1-L4',
        'risk_level': 'Low',
    },
    'P3': {
        'name': 'MKD 激進組',
        'capital': 2000,
        'target_monthly': 0.50,
        'target_weekly': 0.125,
        'strategy': 'MKD EA',
        'signals': ['23617', '10843'],
        'layers': 'L1-L5',
        'risk_level': 'High',
    },
    'P4': {
        'name': 'GBPCAD 專攻',
        'capital': 1200,
        'target_monthly': 0.20,
        'target_weekly': 0.05,
        'strategy': 'GBPCAD Sell',
        'signals': 'all_GBPCAD',
        'layers': 'L1-L3',
        'risk_level': 'Medium',
    },
    'P5': {
        'name': 'XAUUSD 黃金組',
        'capital': 1500,
        'target_monthly': 0.50,
        'target_weekly': 0.125,
        'strategy': 'XAUUSD',
        'signals': ['5117', '27226'],
        'layers': 'L1-L2',
        'risk_level': 'Medium-High',
    },
    'P6': {
        'name': '低風險平注',
        'capital': 1000,
        'target_monthly': 0.15,
        'target_weekly': 0.0375,
        'strategy': '平注策略',
        'signals': 'high_winrate',
        'layers': 'L1 only',
        'risk_level': 'Low',
    },
    'P7': {
        'name': '多CCY分散',
        'capital': 2000,
        'target_monthly': 0.40,
        'target_weekly': 0.10,
        'strategy': '5個主要CCY',
        'signals': 'top_10',
        'layers': 'L1-L3',
        'risk_level': 'Medium',
    },
    'P8': {
        'name': 'London時段組',
        'capital': 1200,
        'target_monthly': 0.20,
        'target_weekly': 0.05,
        'strategy': 'London時段',
        'signals': 'london_session',
        'layers': 'L1-L3',
        'risk_level': 'Medium',
    },
    'P9': {
        'name': 'NY時段組',
        'capital': 1500,
        'target_monthly': 0.50,
        'target_weekly': 0.125,
        'strategy': 'NY時段',
        'signals': 'ny_session',
        'layers': 'L1-L4',
        'risk_level': 'Medium-High',
    },
    'P10': {
        'name': '混合策略組',
        'capital': 1800,
        'target_monthly': 0.45,
        'target_weekly': 0.1125,
        'strategy': 'DW + SMA',
        'signals': 'top_5_dw_sma',
        'layers': 'L1-L3',
        'risk_level': 'Medium',
    },
}

# EA 顏色定義（與 date_range_review.py 一致）
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
    """從 Signal ID 提取 EA 類型"""
    # 嘗試從配置或數據中獲取
    try:
        sys.path.insert(0, str(PROJECT_ROOT))
        from dde_v5_scorer import get_ea
        return get_ea(signal_id)
    except:
        pass
    return 'UNK'


def load_signal_data() -> Dict[str, dict]:
    """載入所有信號 JSON 數據"""
    signals = {}
    for json_file in sorted(DATA_DIR.glob('signal_*.json')):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                signal_id = data.get('signal_id') or json_file.stem.replace('signal_', '')
                signals[str(signal_id)] = data
        except Exception as e:
            print(f"Warning: Failed to load {json_file}: {e}", file=sys.stderr)
    return signals


def analyze_signal_performance(signal_data: dict, start_date: Optional[datetime] = None, 
                               end_date: Optional[datetime] = None) -> dict:
    """分析單個 Signal 的表現"""
    trades = signal_data.get('trades', [])
    
    # 日期過濾
    if start_date or end_date:
        filtered = []
        for t in trades:
            time_str = t.get('Open Time', '')
            try:
                t_time = datetime.strptime(time_str.strip(), '%d/%m/%Y %H:%M:%S')
                if start_date and t_time < start_date:
                    continue
                if end_date and t_time > end_date:
                    continue
                filtered.append(t)
            except:
                continue
        trades = filtered
    
    if not trades:
        return {
            'signal_id': signal_data.get('signal_id', 'UNK'),
            'count': 0,
            'win_rate': 0,
            'total_pnl': 0,
            'total_pips': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'avg_hold_hours': 0,
            'max_dd': 0,
            'ccy_breakdown': {},
        }
    
    # 基本統計
    wins = [t for t in trades if float(t.get('Net Profit', 0)) > 0]
    losses = [t for t in trades if float(t.get('Net Profit', 0)) <= 0]
    total_pnl = sum(float(t.get('Net Profit', 0)) for t in trades)
    total_pips = sum(float(t.get('Net Pips', 0)) for t in trades)
    total_wins = sum(float(t.get('Net Profit', 0)) for t in wins)
    total_losses = abs(sum(float(t.get('Net Profit', 0)) for t in losses))
    avg_hold = sum(float(t.get('Holding Time (Hours)', 0) or 0) for t in trades) / len(trades)
    
    # Profit Factor
    pf = total_wins / total_losses if total_losses > 0 else float('inf') if total_wins > 0 else 0
    
    # 最大回撤計算
    running_pnl = 0
    max_pnl = 0
    max_dd = 0
    for t in trades:
        running_pnl += float(t.get('Net Profit', 0))
        max_pnl = max(max_pnl, running_pnl)
        max_dd = max(max_dd, max_pnl - running_pnl)
    
    # CCY Breakdown
    ccy_breakdown = defaultdict(lambda: {'count': 0, 'pnl': 0, 'wins': 0})
    for t in trades:
        ccy = t.get('Symbol', 'UNK')
        ccy_breakdown[ccy]['count'] += 1
        ccy_breakdown[ccy]['pnl'] += float(t.get('Net Profit', 0))
        if float(t.get('Net Profit', 0)) > 0:
            ccy_breakdown[ccy]['wins'] += 1
    
    return {
        'signal_id': signal_data.get('signal_id', 'UNK'),
        'ea': signal_data.get('ea', get_ea_from_signal(str(signal_data.get('signal_id', '')))),
        'count': len(trades),
        'win_rate': round(len(wins) / len(trades) * 100, 2) if trades else 0,
        'total_pnl': round(total_pnl, 2),
        'total_pips': round(total_pips, 1),
        'avg_win': round(total_wins / len(wins), 2) if wins else 0,
        'avg_loss': round(total_losses / len(losses), 2) if losses else 0,
        'profit_factor': round(pf, 2) if pf != float('inf') else 'inf',
        'avg_hold_hours': round(avg_hold, 1),
        'max_dd': round(max_dd, 2),
        'ccy_breakdown': dict(ccy_breakdown),
    }


def calculate_lot_size(account_balance: float, risk_pct: float, stop_loss_pips: float, 
                       pip_value: float = 10) -> dict:
    """
    計算建議手數
    
    公式：建議手數 = (帳戶餘額 × 風險百分比) / (止損點數 × 點值)
    
    Args:
        account_balance: 帳戶餘額
        risk_pct: 風險百分比（例如 0.02 = 2%）
        stop_loss_pips: 止損點數
        pip_value: 每點價值（默認 $10/pip/lot）
    
    Returns:
        dict: 包含計算過程和結果
    """
    risk_amount = account_balance * risk_pct
    lot_size = risk_amount / (stop_loss_pips * pip_value)
    
    return {
        'account_balance': account_balance,
        'risk_pct': risk_pct * 100,
        'risk_amount': round(risk_amount, 2),
        'stop_loss_pips': stop_loss_pips,
        'pip_value': pip_value,
        'lot_size': round(lot_size, 2),
        'formula': f'({account_balance} × {risk_pct*100}%) / ({stop_loss_pips} × {pip_value}) = {round(lot_size, 2)}',
    }


def simulate_copy_trade(signal_perf: dict, capital: float, layers: str, lot_size: float = 0.01) -> dict:
    """
    模擬 Copy Trade 結果
    
    Args:
        signal_perf: Signal 表現數據
        capital: 投入資金
        layers: 層數設定（如 'L1-L3'）
        lot_size: 每層手數
    
    Returns:
        dict: 模擬結果
    """
    # 解析層數
    if 'L1 only' in layers:
        max_layers = 1
    else:
        import re
        match = re.search(r'L(\d+)-L(\d+)', layers)
        if match:
            max_layers = int(match.group(2))
        else:
            max_layers = 3
    
    # 計算模擬盈虧
    total_trades = signal_perf['count']
    win_rate = signal_perf['win_rate'] / 100
    avg_win = signal_perf['avg_win']
    avg_loss = signal_perf['avg_loss']
    
    # 簡化模擬：假設每層手數遞增
    total_lots = sum(lot_size * (i + 1) for i in range(max_layers))
    avg_lot = total_lots / max_layers
    
    # 預估盈利（基於歷史數據）
    expected_wins = total_trades * win_rate
    expected_losses = total_trades * (1 - win_rate)
    expected_pnl = (expected_wins * avg_win - expected_losses * abs(avg_loss)) * (avg_lot / 0.01)
    
    return {
        'max_layers': max_layers,
        'base_lot': lot_size,
        'total_lot': round(total_lots, 2),
        'expected_wins': round(expected_wins),
        'expected_losses': round(expected_losses),
        'expected_pnl': round(expected_pnl, 2),
        'monthly_pnl': round(expected_pnl / 6, 2),  # 假設 6 個月數據
        'weekly_pnl': round(expected_pnl / 26, 2),  # 假設 26 週數據
    }


def assess_risk(capital: float, portfolio_signals: List[dict], max_layers: int) -> dict:
    """
    評估風險
    
    Args:
        capital: 投入資金
        portfolio_signals: Portfolio 中的 Signals 列表
        max_layers: 最大層數
    
    Returns:
        dict: 風險評估結果
    """
    # 計算總風險敞口
    max_drawdown = sum(s.get('max_dd', 0) for s in portfolio_signals if isinstance(s.get('max_dd'), (int, float)))
    avg_win_rate = sum(s.get('win_rate', 0) for s in portfolio_signals if isinstance(s.get('win_rate'), (int, float))) / len(portfolio_signals) if portfolio_signals else 0
    
    # 爆倉風險計算（簡化）
    # 假設最壞情況：連續虧損達到最大回撤
    margin_required = max_drawdown * 0.1  # 保證金要求
    blowout_risk = 'Low' if margin_required < capital * 0.3 else ('Medium' if margin_required < capital * 0.6 else 'High')
    
    # 資金管理建議
    if max_layers > 4:
        position_sizing = '建議每層手數不超過 0.01，避免過度槓桿'
    elif max_layers > 2:
        position_sizing = '建議每層手數 0.01-0.02，控制風險'
    else:
        position_sizing = '可使用每層 0.02-0.05 手數'
    
    return {
        'max_drawdown': round(max_drawdown, 2),
        'avg_win_rate': round(avg_win_rate, 2),
        'blowout_risk': blowout_risk,
        'margin_required': round(margin_required, 2),
        'position_sizing': position_sizing,
        'recommendations': [
            '設置止損點數不超過帳戶的 2%',
            '每日監控盈虧，超過 10% 止損',
            '避免在重要數據發布時開倉',
            '定期檢視 Portfolio 表現並調整',
        ],
    }


def generate_portfolio_html(portfolio_id: str, portfolio: dict, signals_data: Dict[str, dict], 
                           signal_perfs: List[dict], simulation: dict, risk: dict,
                           lot_calcs: List[dict]) -> str:
    """生成 Portfolio HTML 報告"""
    
    lines = []
    lines.append('<!DOCTYPE html>')
    lines.append('<html lang="zh-Hant">')
    lines.append('<head>')
    lines.append('<meta charset="UTF-8">')
    lines.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    lines.append(f'<title>Portfolio {portfolio_id} | {portfolio["name"]}</title>')
    lines.append('<link rel="stylesheet" href="../sidebar.css">')
    lines.append('<script src="../sidebar.js"></script>')
    lines.append('<style>')
    lines.append('*{margin:0;padding:0;box-sizing:border-box}')
    lines.append('body{font-family:-apple-system,sans-serif;background:#0d1117;color:#c9d1d9}')
    lines.append('body.has-sidebar{padding-left:240px}')
    lines.append('.container{max-width:1200px;margin:auto;padding:20px}')
    lines.append('h1{color:#58a6ff;font-size:1.5em;margin-bottom:8px}')
    lines.append('.meta{color:#8b949e;font-size:0.85em;margin-bottom:20px}')
    lines.append('.section{background:#161b22;border-radius:8px;padding:16px;margin-bottom:16px;border:1px solid #21262d}')
    lines.append('h2{color:#58a6ff;border-bottom:1px solid #21262d;padding-bottom:6px;margin-bottom:10px;font-size:1em}')
    lines.append('table{width:100%;border-collapse:collapse;margin-top:10px}')
    lines.append('th,td{padding:8px 12px;text-align:left;border-bottom:1px solid #21262d}')
    lines.append('th{color:#8b949e;font-weight:600;font-size:0.85em}')
    lines.append('td{font-size:0.9em}')
    lines.append('tr:hover{background:#21262d}')
    lines.append('.positive{color:#3fb950}')
    lines.append('.negative{color:#f85149}')
    lines.append('.signal-link{color:#58a6ff;text-decoration:none;font-weight:500}')
    lines.append('.signal-link:hover{color:#79c0ff;text-decoration:underline}')
    lines.append('.ea-badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:0.75em;font-weight:500}')
    lines.append('.stat-card{background:#21262d;border-radius:6px;padding:12px;display:inline-block;margin:4px;min-width:120px}')
    lines.append('.stat-label{color:#8b949e;font-size:0.75em;margin-bottom:4px}')
    lines.append('.stat-value{font-size:1.2em;font-weight:600}')
    lines.append('.risk-low{color:#3fb950}')
    lines.append('.risk-medium{color:#d29922}')
    lines.append('.risk-high{color:#f85149}')
    lines.append('.calc-box{background:#21262d;border-radius:6px;padding:12px;margin:8px 0;font-family:monospace}')
    lines.append('.formula{color:#d29922;font-size:0.9em}')
    lines.append('ul{margin-left:20px;margin-top:8px}')
    lines.append('li{margin:4px 0}')
    lines.append('</style>')
    lines.append('</head>')
    lines.append('<body class="has-sidebar">')
    lines.append('<div class="container">')
    
    # 標題
    lines.append(f'<h1>📊 Portfolio {portfolio_id}: {portfolio["name"]}</h1>')
    lines.append(f'<div class="meta">生成時間：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | 策略：{portfolio["strategy"]} | 風險等級：{portfolio["risk_level"]}</div>')
    
    # Portfolio 概述
    lines.append('<div class="section">')
    lines.append('<h2>📋 Portfolio 概述</h2>')
    lines.append('<div class="stat-card"><div class="stat-label">投入資金</div><div class="stat-value">${portfolio["capital"]:,}</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">月目標</div><div class="stat-value">{portfolio["target_monthly"]*100}%</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">週目標</div><div class="stat-value">{portfolio["target_weekly"]*100}%</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">層數設定</div><div class="stat-value">{portfolio["layers"]}</div></div>')
    lines.append('</div>')
    
    # Signals 清單
    lines.append('<div class="section">')
    lines.append('<h2>📈 Signals 清單</h2>')
    lines.append('<table><thead><tr><th>Signal ID</th><th>EA</th><th>Trades</th><th>WR</th><th>PnL</th><th>Pips</th><th>PF</th><th>Max DD</th></tr></thead><tbody>')
    for s in signal_perfs:
        sig_id = s['signal_id']
        sig_link = f'<a href="../reports/Signal_Deep_Analysis_{sig_id}.html" class="signal-link">{sig_id}</a>'
        ea = s.get('ea', 'UNK')
        ea_style = f'background:{EA_COLORS.get(ea, EA_COLORS["UNK"])[0]};color:{EA_COLORS.get(ea, EA_COLORS["UNK"])[1]}'
        pnl_cls = 'positive' if s['total_pnl'] >= 0 else 'negative'
        lines.append(f'<tr><td>{sig_link}</td><td><span class="ea-badge" style="{ea_style}">{ea}</span></td><td>{s["count"]:,}</td><td>{s["win_rate"]:.1f}%</td><td class="{pnl_cls}">${s["total_pnl"]:,.2f}</td><td>{s["total_pips"]:,.1f}</td><td>{s["profit_factor"]}</td><td class="negative">${s["max_dd"]:,.2f}</td></tr>')
    lines.append('</tbody></table>')
    lines.append('</div>')
    
    # 手數計算過程
    lines.append('<div class="section">')
    lines.append('<h2>🧮 手數計算過程</h2>')
    lines.append('<p><strong>公式：</strong> 建議手數 = (帳戶餘額 × 風險百分比) / (止損點數 × 點值)</p>')
    for i, calc in enumerate(lot_calcs[:3], 1):
        lines.append(f'<div class="calc-box">')
        lines.append(f'<div>Signal {signal_perfs[i-1]["signal_id"] if i <= len(signal_perfs) else "示例"}:</div>')
        lines.append(f'<div class="formula">{calc["formula"]}</div>')
        lines.append(f'<div>建議手數：<strong>{calc["lot_size"]} lots</strong></div>')
        lines.append('</div>')
    lines.append('</div>')
    
    # 模擬結果
    lines.append('<div class="section">')
    lines.append('<h2>📊 模擬交易結果</h2>')
    lines.append(f'<div class="stat-card"><div class="stat-label">最大層數</div><div class="stat-value">{simulation["max_layers"]}</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">基礎手數</div><div class="stat-value">{simulation["base_lot"]} lots</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">總手數</div><div class="stat-value">{simulation["total_lot"]} lots</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">預期月盈虧</div><div class="stat-value ${"positive" if simulation["monthly_pnl"] >= 0 else "negative"}">${simulation["monthly_pnl"]:,.2f}</div></div>')
    lines.append('</div>')
    
    # 風險評估
    risk_cls = 'risk-low' if risk['blowout_risk'] == 'Low' else ('risk-medium' if risk['blowout_risk'] == 'Medium' else 'risk-high')
    lines.append('<div class="section">')
    lines.append('<h2>⚠️ 風險評估</h2>')
    lines.append(f'<div class="stat-card"><div class="stat-label">最大回撤</div><div class="stat-value negative">${risk.get("max_drawdown", 0):,.2f}</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">平均勝率</div><div class="stat-value">{risk["avg_win_rate"]:.1f}%</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">爆倉風險</div><div class="stat-value {risk_cls}">{risk["blowout_risk"]}</div></div>')
    lines.append(f'<div class="stat-card"><div class="stat-label">保證金要求</div><div class="stat-value">${risk["margin_required"]:,.2f}</div></div>')
    lines.append(f'<p style="margin-top:12px"><strong>資金管理建議：</strong>{risk["position_sizing"]}</p>')
    lines.append('<h3 style="margin-top:16px;color:#8b949e">💡 建議措施：</h3>')
    lines.append('<ul>')
    for rec in risk['recommendations']:
        lines.append(f'<li>{rec}</li>')
    lines.append('</ul>')
    lines.append('</div>')
    
    # 總結
    lines.append('<div class="section">')
    lines.append('<h2>📝 總結與建議</h2>')
    target_monthly_pnl = portfolio['capital'] * portfolio['target_monthly']
    lines.append(f'<p>本 Portfolio ({portfolio["name"]}) 投入資金 ${portfolio["capital"]:,}，目標月回報 {portfolio["target_monthly"]*100}%（${target_monthly_pnl:,.2f}）。</p>')
    lines.append(f'<p>根據歷史數據模擬，預期月盈虧為 ${simulation["monthly_pnl"]:,.2f}，')
    if simulation['monthly_pnl'] >= target_monthly_pnl:
        lines.append('<span class="positive">✅ 可達成目標。</span></p>')
    else:
        gap = target_monthly_pnl - simulation['monthly_pnl']
        lines.append(f'<span class="negative">⚠️ 需要增加 ${gap:,.2f} 才能達成目標。</span></p>')
    lines.append(f'<p>風險等級：<strong>{risk["blowout_risk"]}</strong>，建議密切監控並嚴格執行止損。</p>')
    lines.append('</div>')
    
    lines.append('</div>')
    lines.append('</body>')
    lines.append('</html>')
    
    return '\n'.join(lines)


def generate_portfolio(portfolio_id: str, portfolio: dict, signals_data: Dict[str, dict], 
                      start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> dict:
    """生成單個 Portfolio 報告"""
    
    # 確定 Signals 列表
    if isinstance(portfolio['signals'], list):
        signal_ids = portfolio['signals']
    else:
        # 特殊處理（all_GBPCAD, top_10, etc.）
        signal_ids = []
        if portfolio['signals'] == 'all_GBPCAD':
            for sid, data in signals_data.items():
                trades = data.get('trades', [])
                for t in trades:
                    if t.get('Symbol') == 'GBPCAD':
                        signal_ids.append(sid)
                        break
        elif portfolio['signals'] == 'high_winrate':
            # 選取勝率最高的 10 個 Signals
            all_perfs = [(sid, analyze_signal_performance(data, start_date, end_date)) 
                         for sid, data in signals_data.items()]
            all_perfs.sort(key=lambda x: x[1]['win_rate'], reverse=True)
            signal_ids = [p[0] for p in all_perfs[:10]]
        elif portfolio['signals'] == 'top_10':
            # 選取盈利最高的 10 個 Signals
            all_perfs = [(sid, analyze_signal_performance(data, start_date, end_date)) 
                         for sid, data in signals_data.items()]
            all_perfs.sort(key=lambda x: x[1]['total_pnl'], reverse=True)
            signal_ids = [p[0] for p in all_perfs[:10]]
        elif portfolio['signals'] in ('london_session', 'ny_session'):
            # 選取該時段表現好的 Signals（簡化：選取所有）
            signal_ids = list(signals_data.keys())[:10]
        elif portfolio['signals'] == 'top_5_dw_sma':
            # 選取 DW 和 SMA 各前 5 個
            dw_signals = []
            sma_signals = []
            for sid, data in signals_data.items():
                ea = data.get('ea', get_ea_from_signal(sid))
                if 'DW' in ea and len(dw_signals) < 5:
                    dw_signals.append(sid)
                elif 'SMA' in ea and len(sma_signals) < 5:
                    sma_signals.append(sid)
            signal_ids = dw_signals + sma_signals
    
    # 分析每個 Signal
    signal_perfs = []
    for sid in signal_ids:
        if sid in signals_data:
            perf = analyze_signal_performance(signals_data[sid], start_date, end_date)
            signal_perfs.append(perf)
    
    if not signal_perfs:
        print(f"Warning: No signals found for {portfolio_id}", file=sys.stderr)
        return None
    
    # 計算手數
    lot_calcs = []
    for s in signal_perfs:
        # 假設止損 50 點，風險 2%
        calc = calculate_lot_size(portfolio['capital'], 0.02, 50, 10)
        lot_calcs.append(calc)
    
    # 模擬 Copy Trade
    # 解析層數
    layers_str = portfolio['layers']
    if 'L1 only' in layers_str:
        max_layers = 1
    else:
        import re
        match = re.search(r'L(\d+)-L(\d+)', layers_str)
        if match:
            max_layers = int(match.group(2))
        else:
            max_layers = 3
    
    total_simulation = {
        'max_layers': max_layers,
        'base_lot': 0.01,
        'total_lot': 0.03,
        'expected_wins': sum(s['win_rate'] for s in signal_perfs) / 100,
        'expected_losses': sum(100 - s['win_rate'] for s in signal_perfs) / 100,
        'expected_pnl': sum(s['total_pnl'] for s in signal_perfs),
        'monthly_pnl': sum(s['total_pnl'] for s in signal_perfs) / 6,
        'weekly_pnl': sum(s['total_pnl'] for s in signal_perfs) / 26,
    }
    
    # 風險評估
    risk = assess_risk(portfolio['capital'], signal_perfs, total_simulation['max_layers'])
    
    # 生成 HTML
    html = generate_portfolio_html(portfolio_id, portfolio, signals_data, signal_perfs, 
                                   total_simulation, risk, lot_calcs)
    
    return {
        'portfolio_id': portfolio_id,
        'portfolio': portfolio,
        'signal_perfs': signal_perfs,
        'lot_calcs': lot_calcs,
        'simulation': total_simulation,
        'risk': risk,
        'html': html,
    }


def main():
    parser = argparse.ArgumentParser(description='Portfolio Generator')
    parser.add_argument('--portfolio', type=str, help='Portfolio ID (P1-P10), or "all"')
    parser.add_argument('--start-date', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end-date', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--output-dir', type=str, help='Output directory')
    
    args = parser.parse_args()
    
    # 解析日期
    start_date = datetime.strptime(args.start_date, '%Y-%m-%d') if args.start_date else None
    end_date = datetime.strptime(args.end_date, '%Y-%m-%d') if args.end_date else None
    
    # 輸出目錄
    output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 載入數據
    print("Loading signal data...")
    signals_data = load_signal_data()
    print(f"Loaded {len(signals_data)} signals")
    
    # 確定要生成的 Portfolios
    if args.portfolio == 'all':
        portfolio_ids = list(PORTFOLIOS.keys())
    elif args.portfolio:
        portfolio_ids = [args.portfolio.upper()]
    else:
        portfolio_ids = list(PORTFOLIOS.keys())
    
    # 生成報告
    for pid in portfolio_ids:
        if pid not in PORTFOLIOS:
            print(f"Warning: Unknown portfolio {pid}", file=sys.stderr)
            continue
        
        print(f"\nGenerating Portfolio {pid}: {PORTFOLIOS[pid]['name']}...")
        result = generate_portfolio(pid, PORTFOLIOS[pid], signals_data, start_date, end_date)
        
        if result:
            # 保存 HTML
            html_path = output_dir / f'portfolio_{pid}.html'
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(result['html'])
            print(f"  HTML saved: {html_path}")
            
            # 保存 JSON
            json_path = output_dir / f'portfolio_{pid}.json'
            json_data = {
                'portfolio_id': result['portfolio_id'],
                'portfolio': result['portfolio'],
                'signal_perfs': result['signal_perfs'],
                'simulation': result['simulation'],
                'risk': result['risk'],
                'generated_at': datetime.now().isoformat(),
            }
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, indent=2, ensure_ascii=False)
            print(f"  JSON saved: {json_path}")
    
    print(f"\n✅ Generated {len(portfolio_ids)} portfolio reports")


if __name__ == '__main__':
    main()
