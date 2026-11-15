#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
run_scheduled_reviews.py — 按日期覆盤每日／每週自動化 wrapper（PRD 15.6，待辦⑧）

觸發點（VPS crontab，同 L16 備份 04:00 cron 同一宿主；詳見 docs/REVIEWS_AUTOMATION.md）：

    # TSA 覆盤：每日 06:05 昨日日報（排喺 AlgoForest 同步 ~04:40＋ranking 05:30 之後，
    # 等昨日數據齊先生成；PRD 15.6 原文 00:05 因早過數據同步，改排 06:05，原因見文檔）
    5 6 * * *   cd /home/alvin/.openclaw/workspace/trade_strategy_analyzer \
                 && python3 scripts/run_scheduled_reviews.py daily >> "$HOME/tsa_backups/reviews.log" 2>&1
    # TSA 覆盤：每週一 06:10 上週週報（週一至週日）
    10 6 * * 1  cd /home/alvin/.openclaw/workspace/trade_strategy_analyzer \
                 && python3 scripts/run_scheduled_reviews.py weekly >> "$HOME/tsa_backups/reviews.log" 2>&1

流程（每步都係用返倉庫既有輪，唔新發明）：
  1. generate_history_backup.backup_all_signals()：由 downloads/*.csv（AlgoForest 每日同步）
     刷新 data/history/signal_*.json（.gitignore 局部真實交易數據，唔入 repo）
  2. scripts/date_range_review.py：生成 docs/reviews/{daily,weekly}/review_*.{html,json}
     ＋自動更新各 period 嘅 index.json（docs/reviews/index.html 係動態 fetch index.json，唔使改）
  3. 保留策略（PRD 15.6）：日報 30 日、週報 12 週——按檔名 start_date 剪枝，
     signal 級變體一齊刪，index.json 同步剪
  4. git add docs/reviews/{daily,weekly} ＋ git commit（預設唔 push；--push 交 job 層決定）

用法：
    python3 scripts/run_scheduled_reviews.py daily            # 昨日日報
    python3 scripts/run_scheduled_reviews.py weekly           # 上週週報（最近一個完整週，週一至週日）
    python3 scripts/run_scheduled_reviews.py all              # 兩者（補跑用）
    python3 scripts/run_scheduled_reviews.py daily --date 2026-11-13   # 指定日期補跑
    python3 scripts/run_scheduled_reviews.py daily --no-commit         # 只生成唔 commit（驗證用）

對應關係：
    tsa-ranking-daily（05:30 ranking 重生成，commit 123ce7b1 模式）: 排程生 data 產物＋自動 commit
    本 wrapper（06:05/06:10）                                : 同一模式，產物係覆盤報告
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))  # 同 date_range_review.py 頂部嘅 bootstrap 慣例

# PRD 15.6 保留策略
RETENTION = {'daily': 30, 'weekly': 12 * 7}   # 日報 30 日；週報 12 週（12×7 日）
PERIODS = ('daily', 'weekly')
REVIEW_TOOL = REPO / 'scripts' / 'date_range_review.py'


def yesterday(target: date = None) -> date:
    """每日模式嘅覆盤日：預設昨日。"""
    return (target or date.today()) - timedelta(days=1)


def last_week_bounds(today: date = None) -> tuple:
    """上週週報範圍（週一至週日）。

    最近一個「以週日收尾」嘅週：每週一 00:10 cron 跑時即係啱啱完結嘅完整一週；
    週日當日跑會涵蓋以當日收尾嘅一週（補跑場景）。
    """
    today = today or date.today()
    end = today - timedelta(days=(today.weekday() + 1) % 7)
    return end - timedelta(days=6), end


def refresh_history() -> int:
    """Step 1：downloads/*.csv → data/history/signal_*.json（用返既有生成器）。"""
    from generate_history_backup import backup_all_signals
    n = len(backup_all_signals())
    print(f"[1/4] data/history 已刷新：{n} 個 signal JSON")
    return n


def run_review(start: date, end: date, period: str) -> None:
    """Step 2：subprocess 行 scripts/date_range_review.py（同 PRD 15.4 CLI 一致）。"""
    cmd = [sys.executable, str(REVIEW_TOOL),
           '--start-date', start.isoformat(), '--end-date', end.isoformat(),
           '--period', period]
    print(f"[2/4] {' '.join(cmd)}")
    subprocess.run(cmd, cwd=str(REPO), check=True)


def prune_period(period: str, keep_days: int, today: date = None) -> list:
    """Step 3：保留策略剪枝——刪 start_date 早於 cutoff 嘅 review_* 檔案（含 signal 級變體），
    index.json 同步剪。回傳被刪檔名（commit 訊息用）。"""
    today = today or date.today()
    cutoff = today - timedelta(days=keep_days)
    out_dir = REPO / 'docs' / 'reviews' / period
    if not out_dir.exists():
        return []
    pat = re.compile(r'^review_(\d{4}-\d{2}-\d{2})_')
    deleted = []
    for f in sorted(out_dir.iterdir()):
        m = pat.match(f.name)
        if m and date.fromisoformat(m.group(1)) < cutoff:
            f.unlink()
            deleted.append(f.name)
    index_path = out_dir / 'index.json'
    if index_path.exists() and deleted:
        data = json.loads(index_path.read_text(encoding='utf-8'))
        before = len(data.get('reports', []))
        data['reports'] = [r for r in data.get('reports', [])
                           if date.fromisoformat(str(r.get('start_date', '9999-12-31'))) >= cutoff]
        index_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"[3/4] {period} index.json：{before} → {len(data['reports'])} 條")
    return deleted


def git_commit(parts: list, deleted: list, push: bool) -> None:
    """Step 4：commit 本次 docs/reviews 產物（含剪枝刪檔）；預設唔 push。"""
    paths = ['--'] + [f'docs/reviews/{p}' for p in PERIODS]
    subprocess.run(['git', 'add'] + paths, cwd=str(REPO), check=True)
    if subprocess.run(['git', 'diff', '--cached', '--quiet'], cwd=str(REPO)).returncode == 0:
        print('[4/4] 無變動，毋須 commit')
        return
    msg = 'data: 覆盤自動生成（' + '、'.join(parts) + '）'
    if deleted:
        msg += f'；保留策略清理刪 {len(deleted)} 舊檔'
    subprocess.run(['git', 'commit', '-m', msg], cwd=str(REPO), check=True)
    print(f'[4/4] committed：{msg}')
    if push:
        subprocess.run(['git', 'push'], cwd=str(REPO), check=True)
        print('[4/4] pushed')


def main():
    ap = argparse.ArgumentParser(description='按日期覆盤自動化 wrapper（PRD 15.6）')
    ap.add_argument('mode', choices=['daily', 'weekly', 'all'])
    ap.add_argument('--date', help='daily 補跑用：指定覆盤日 YYYY-MM-DD（預設昨日）')
    ap.add_argument('--no-commit', action='store_true', help='只生成，唔 git commit')
    ap.add_argument('--push', action='store_true', help='commit 後 push（預設唔 push，交 job 層决定）')
    args = ap.parse_args()

    jobs = []
    if args.mode in ('daily', 'all'):
        d = date.fromisoformat(args.date) if args.date else yesterday()
        jobs.append(('daily', d, d))
    if args.mode in ('weekly', 'all'):
        jobs.append(('weekly', *last_week_bounds()))

    refresh_history()
    parts, deleted_all = [], []
    for period, start, end in jobs:
        run_review(start, end, period)
        parts.append(f'{period} {start.isoformat()}' + (f'~{end.isoformat()}' if end != start else ''))
    print('[3/4] 保留策略：日報 30 日／週報 12 週（PRD 15.6）')
    for period in PERIODS:
        deleted_all += prune_period(period, RETENTION[period])
    if deleted_all:
        print(f"[3/4] 已刪：{', '.join(deleted_all)}")

    if args.no_commit:
        print('[4/4] --no-commit：略過 git 步驟')
    else:
        git_commit(parts, deleted_all, args.push)


if __name__ == '__main__':
    main()
