#!/usr/bin/env python3
"""
TSA 信號分析一鍵入口（「分析 signal {ID}」自動化鏈·純標準庫）

對應 PRD 待辦③ SKILL 自動化分析流程。本檔案係最細可行駁通：
    下載 CSV → 倉位重構分析 → 存入 data/analysis_history.db → 寫 TG 通知檔 → 印出摘要

設計原則：
- 只用 Python 標準庫（本機 AutoClaw vendor Python 冇 pandas/fastapi 亦可行到）
- 指標口徑跟隨 src/position_builder.py + src/statistics.py + archive/batch_analyze.py：
  * 倉位 = Symbol + 方向 + 平倉時間（截斷至分鐘）分組
  * 層數 = 全信號唯一手數值排序後嘅排名（1 起）
  * win_rate / profit_factor / max_dd 用倉位級 USD 盈虧（同 api_server 通知口徑）
  * l4_recovery_rate = L4+ 倉位中獲利倉位佔比（archive/batch_analyze.py:86 同一定義）
- 入口/出口與既有組件對齊：
  * 下載 URL／UA／'Open Time' 內容檢查同 scripts/batch_csv_downloader.py
  * 存檔經 scripts/history_manager.py save_analysis()（csv_hash 去重＋自動版本化）
  * 通知檔格式同 scripts/api_server.py notify_telegram()：一行一個 JSON {"ts":…,"msg":…}

用法（Windows PowerShell，repo 根目錄）：
    python scripts\\analyze_signal_entry.py 11984            # 有現成 downloads\\11984.csv 就用，否則下載
    python scripts\\analyze_signal_entry.py 11984 --refresh  # 強制重新下載
    python scripts\\analyze_signal_entry.py 11984 --full     # 有 pandas 時改行 archive 完整管線（產 HTML 報告）

通知檔輸出位置：logs/trade-analyzer-notify.jsonl（repo 相對；Windows 冇 /tmp，
由消費方（AutoClaw）以 file_tail 監看後轉發 Telegram）。
"""

import argparse
import csv as csv_mod
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOWNLOADS_DIR = os.path.join(REPO_ROOT, 'downloads')
LOGS_DIR = os.path.join(REPO_ROOT, 'logs')
NOTIFY_FILE = os.path.join(LOGS_DIR, 'trade-analyzer-notify.jsonl')
API_URL = 'https://analytics-api.gemsai.com/signals/{}/trading-order-histories/export'

sys.path.insert(0, os.path.join(REPO_ROOT, 'scripts'))
from history_manager import save_analysis, get_db  # noqa: E402


# ---------------------------------------------------------------- schema

SCHEMA_SQL = '''
CREATE TABLE IF NOT EXISTS analyses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_id TEXT,
    ea_name TEXT,
    pair TEXT,
    csv_filename TEXT,
    set_filename TEXT,
    csv_hash TEXT,
    analysis_date TEXT,
    total_positions INTEGER,
    total_trades INTEGER,
    win_rate REAL,
    profit_factor REAL,
    total_profit REAL,
    max_dd REAL,
    max_dd_percent REAL,
    avg_layers REAL,
    avg_holding_minutes REAL,
    sharpe REAL,
    l1_only_ratio REAL,
    l4_plus_ratio REAL,
    l4_recovery_rate REAL,
    entry_score_avg REAL,
    strategy_score_avg REAL,
    final_score_avg REAL,
    grade_a_count INTEGER,
    grade_b_count INTEGER,
    grade_c_count INTEGER,
    grade_d_count INTEGER,
    symbols_summary TEXT,
    report_path TEXT,
    raw_stats TEXT,
    created_at TEXT DEFAULT (datetime('now', 'localtime'))
);
CREATE TABLE IF NOT EXISTS versions (
    signal_id TEXT,
    version INTEGER,
    analysis_id INTEGER,
    PRIMARY KEY (signal_id, version)
);
CREATE TABLE IF NOT EXISTS symbol_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    analysis_id INTEGER,
    symbol TEXT,
    positions INTEGER,
    win_rate REAL,
    avg_profit REAL,
    profit_factor REAL,
    max_dd REAL
);
'''


def ensure_schema():
    """補倉內缺口：analyses/versions/symbol_stats 三表冇任何 CREATE TABLE（schema 原本喺倉外建）。
    欄位沿用 history_manager.py INSERT/SELECT 實際使用嘅欄位。"""
    conn = get_db()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------- download

def download_csv(signal_id: str) -> str:
    """同 batch_csv_downloader.py 同源下載，輸出採用 downloads/ 現行 bare-id 命名。"""
    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    filepath = os.path.join(DOWNLOADS_DIR, f'{signal_id}.csv')
    url = API_URL.format(signal_id)
    req = urllib.request.Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode('utf-8')
    if 'Open Time' not in content:
        raise RuntimeError(f'信號 {signal_id} 下載內容冇交易表頭（可能已下架或無交易紀錄）')
    with open(filepath, 'w', newline='', encoding='utf-8') as f:
        f.write(content)
    return filepath


# ---------------------------------------------------------------- parse & build positions

NON_TRADE_RE = re.compile(r'Transfer|Deposit|Withdraw|Balance', re.IGNORECASE)
DATE_FMT = '%d/%m/%Y %H:%M:%S'


def _parse_date(s: str):
    try:
        return datetime.strptime(s.strip(), DATE_FMT)
    except ValueError:
        return None


def parse_trades(csv_path: str):
    """std 版 src/csv_parser.py：讀檔、過濾非交易／零手數／無 Symbol 記錄。"""
    trades = []
    with open(csv_path, newline='', encoding='utf-8-sig') as f:
        for row in csv_mod.DictReader(f):
            def _clean(s):
                return (s or '').replace('\ufeff', '').strip()
            row = { _clean(k): _clean(v) for k, v in row.items() }
            comment = row.get('Comment', '')
            if NON_TRADE_RE.search(comment):
                continue
            try:
                lots = float(row.get('Lots') or 0)
            except ValueError:
                continue
            if lots <= 0:
                continue
            symbol = row.get('Symbol', '')
            if not symbol:
                continue
            close_dt = _parse_date(row.get('Close Time', ''))
            open_dt = _parse_date(row.get('Open Time', ''))
            if close_dt is None or open_dt is None:
                continue
            def _num(key):
                try:
                    return float(row.get(key) or 0)
                except ValueError:
                    return 0.0
            trades.append({
                'symbol': symbol,
                'direction': row.get('Type', '').upper(),
                'open_time': open_dt,
                'close_time': close_dt,
                'lots': lots,
                'net_profit': _num('Net Profit'),
                'net_pips': _num('Net Pips'),
                'max_loss': _num('Max Loss'),
                'swap': _num('Swap'),
                'commission': _num('Commission'),
            })
    return trades


def build_positions(trades):
    """std 版 src/position_builder.py：Symbol+方向+平倉分鐘 分組；層數=唯一手數排名。"""
    if not trades:
        return []
    unique_lots = sorted({round(t['lots'], 4) for t in trades})
    layer_of = {lot: i + 1 for i, lot in enumerate(unique_lots)}

    groups = defaultdict(list)
    for t in trades:
        key = (t['symbol'], t['direction'], t['close_time'].replace(second=0, microsecond=0))
        groups[key].append(t)

    positions = []
    for (symbol, direction, close_min), members in groups.items():
        profits = [m['net_profit'] for m in members]
        positions.append({
            'symbol': symbol,
            'direction': direction,
            'open_time': min(m['open_time'] for m in members),
            'close_time': close_min,
            'holding_hours': (close_min - min(m['open_time'] for m in members)).total_seconds() / 3600,
            'net_profit': sum(profits),
            'net_pips': sum(m['net_pips'] for m in members),
            'max_layer': max(layer_of[round(m['lots'], 4)] for m in members),
            'n_trades': len(members),
            'total_swap': sum(m['swap'] for m in members),
            'total_commission': sum(m['commission'] for m in members),
        })
    positions.sort(key=lambda p: p['close_time'])
    return positions


# ---------------------------------------------------------------- stats（口徑同 src/statistics.py）

def calculate_max_drawdown(profits):
    cum, peak, dd = 0.0, [], []
    for p in profits:
        cum += p
        peak.append(cum if not peak or cum > peak[-1] else peak[-1])
        dd.append(cum - peak[-1])
    max_dd = min(dd) if dd else 0.0
    max_peak = max(peak) if peak else 0.0
    max_dd_percent = (max_dd / max_peak) * 100 if max_peak > 0 else 0.0
    return max_dd, max_dd_percent


def calculate_overall(positions):
    n = len(positions)
    profits = [p['net_profit'] for p in positions]
    wins = [x for x in profits if x > 0]
    losses = [x for x in profits if x <= 0]
    gross_win = sum(wins)
    gross_loss = abs(sum(losses))
    pf = (gross_win / gross_loss) if gross_loss > 0 else (999.99 if gross_win > 0 else 0.0)

    max_dd, max_dd_percent = calculate_max_drawdown(profits)

    trading_days = 1.0
    if n >= 1:
        span_days = (positions[-1]['close_time'] - positions[0]['open_time']).total_seconds() / 86400
        trading_days = max(span_days, 1.0)
    annual_factor = (252 / trading_days) ** 0.5

    sharpe = 0.0
    if n >= 2:
        mean_p = sum(profits) / n
        var_p = sum((x - mean_p) ** 2 for x in profits) / n  # np.std 母體標準差
        std_p = var_p ** 0.5
        if std_p > 0:
            sharpe = mean_p / std_p * annual_factor

    l1_only = [p for p in positions if p['max_layer'] == 1]
    l4_plus = [p for p in positions if p['max_layer'] >= 4]
    l4_plus_wins = [p for p in l4_plus if p['net_profit'] > 0]

    return {
        'total_positions': n,
        'total_trades': sum(p['n_trades'] for p in positions),
        'win_rate': round(len(wins) / n * 100, 2) if n else 0.0,
        'profit_factor': round(pf, 2),
        'total_profit': round(sum(profits), 2),
        'max_dd': round(max_dd, 2),
        'max_dd_percent': round(max_dd_percent, 2),
        'avg_layers': round(sum(p['max_layer'] for p in positions) / n, 2) if n else 0.0,
        'avg_holding_hours': round(sum(p['holding_hours'] for p in positions) / n, 2) if n else 0.0,
        'sharpe': round(sharpe, 2),
        'l1_only_ratio': round(len(l1_only) / n * 100, 2) if n else 0.0,
        'l4_plus_ratio': round(len(l4_plus) / n * 100, 2) if n else 0.0,
        'l4_recovery_rate': round(len(l4_plus_wins) / len(l4_plus) * 100, 2) if l4_plus else 0.0,
        'trading_days': round(trading_days, 1),
    }


def calculate_symbol_stats(positions):
    by_symbol = defaultdict(list)
    for p in positions:
        by_symbol[p['symbol']].append(p)
    out = []
    for symbol, plist in sorted(by_symbol.items()):
        profits = [p['net_profit'] for p in plist]
        wins = [x for x in profits if x > 0]
        gross_loss = abs(sum(x for x in profits if x <= 0))
        pf = (sum(wins) / gross_loss) if gross_loss > 0 else (999.99 if wins else 0.0)
        max_dd, _ = calculate_max_drawdown(profits)
        out.append({
            'symbol': symbol,
            'positions': len(plist),
            'win_rate': round(len(wins) / len(plist) * 100, 2),
            'avg_profit': round(sum(profits) / len(plist), 2),
            'profit_factor': round(pf, 2),
            'max_dd': round(max_dd, 2),
        })
    return out


# ---------------------------------------------------------------- notify

def notify(msg: str):
    """同 api_server.notify_telegram 同格式；Windows 冇 /tmp，改落 repo 內 logs/ 俾 agent 撿。"""
    os.makedirs(LOGS_DIR, exist_ok=True)
    with open(NOTIFY_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps({'ts': time.time(), 'msg': msg}, ensure_ascii=False) + '\n')


# ---------------------------------------------------------------- main

def load_ea_name(signal_id: str) -> str:
    try:
        with open(os.path.join(REPO_ROOT, 'ea_name_mapping.json'), encoding='utf-8') as f:
            mapping = json.load(f)
        return ', '.join(mapping.get(str(signal_id), []))
    except Exception:
        return ''


def run_full_pipeline(csv_path: str, signal_id: str):
    """有 pandas 時行 archive 完整管線（深入分析＋HTML 報告）。本機未裝 pandas，屬選項。"""
    cmd = [sys.executable, os.path.join('archive', 'run_analysis.py'), '--csv', csv_path]
    print(f"[full] 行完整管線: {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=REPO_ROOT)


def main():
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description='分析 signal {ID} 一鍵鏈（下載→分析→存檔→通知）')
    parser.add_argument('signal_id', help='信號 ID（純數字），例如 11984')
    parser.add_argument('--refresh', action='store_true', help='強制重新下載 CSV（預設：有現成檔就用現成檔）')
    parser.add_argument('--full', action='store_true', help='改行 archive/run_analysis.py 完整管線（需 pandas）')
    args = parser.parse_args()

    sid = args.signal_id.strip()
    if not sid.isdigit():
        parser.error(f'信號 ID 必須係純數字，收到: {sid!r}')

    # ① 落載
    csv_path = os.path.join(DOWNLOADS_DIR, f'{sid}.csv')
    if args.refresh or not os.path.exists(csv_path):
        print(f'[1/4] 下載信號 {sid} CSV ...')
        csv_path = download_csv(sid)
        print(f'      已存 {csv_path}')
    else:
        print(f'[1/4] 用現成 {csv_path}（--refresh 可強制重新下載）')

    if args.full:
        sys.exit(run_full_pipeline(csv_path, sid))

    # ② 分析
    print('[2/4] 倉位重構分析（std lite 口徑，同 position_builder/statistics 對齊）...')
    trades = parse_trades(csv_path)
    if not trades:
        print('❌ CSV 冇有效交易記錄'); sys.exit(1)
    positions = build_positions(trades)
    overall = calculate_overall(positions)
    symbol_stats = calculate_symbol_stats(positions)
    pair = Counter(p['symbol'] for p in positions).most_common(1)[0][0]
    print(f"      {overall['total_positions']} 倉位 / {overall['total_trades']} 交易 | 主貨幣對 {pair}")

    # ③ 存檔
    print('[3/4] 存入 data/analysis_history.db ...')
    ensure_schema()
    with open(csv_path, encoding='utf-8-sig') as f:
        csv_content = f.read()
    data = {
        'signal_id': sid,
        'csv_filename': os.path.basename(csv_path),
        'csv_content': csv_content,
        'csv_hash': hashlib.md5(csv_content.encode()).hexdigest()[:12],
        'ea_name': load_ea_name(sid),
        'pair': pair if len(symbol_stats) == 1 else '',
        'analysis_date': datetime.now().strftime('%Y-%m-%d'),
        **overall,
        'avg_holding_minutes': round(overall['avg_holding_hours'] * 60, 1),
        'symbol_stats': symbol_stats,
        'raw_stats': {'lite_analyzer': True, 'symbols': {s['symbol']: s for s in symbol_stats}},
    }
    aid = save_analysis(data)
    print(f'      已存 analysis #{aid}')

    # ④ 通知（格式同 api_server /api/save）
    profit = overall['total_profit']
    emoji = '🟢' if profit >= 0 else '🔴'
    msg = (
        f"✅ 新分析已存檔\n"
        f"{emoji} Signal {sid} | {data['ea_name'] or '?'} | {overall['total_positions']} 倉位\n"
        f"WR {overall['win_rate']:.1f}% | PF {overall['profit_factor']:.2f} | {emoji} ${profit:+.2f}"
    )
    notify(msg)
    print(f'[4/4] 通知已寫 {NOTIFY_FILE}')

    print('\n===== 摘要 =====')
    print(f"Signal {sid} | EA: {data['ea_name'] or '—'}")
    print(f"總盈虧 ${profit:+.2f} | WR {overall['win_rate']:.1f}% | PF {overall['profit_factor']:.2f}")
    print(f"倉位 {overall['total_positions']} | 交易 {overall['total_trades']} | MaxDD ${overall['max_dd']:.2f} ({overall['max_dd_percent']:.1f}%)")
    print(f"L1-only {overall['l1_only_ratio']:.0f}% | L4+ {overall['l4_plus_ratio']:.0f}% | L4回歸 {overall['l4_recovery_rate']:.0f}%")
    print(f"詳情: python scripts\\history_manager.py summary {aid}")


if __name__ == '__main__':
    main()
