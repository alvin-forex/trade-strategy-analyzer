#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_health_json.py — TSA 新首頁「系統健康燈」數據生成器（設計基準 v1.0 §六數據契約）
2026-10-28 老闆批示開工（w lane）：health.json 五項狀態偵測——零新採集，全部用現成來源。

契約欄位（home/health.json）：
  ranking_fresh : bool|null — 排名 pipeline（每日 05:30 隨排名重生成）最後產物 ≤ 48h
  newsguard_ok  : bool|null — news_guard.csv（每日 06:00 掃描）最後更新 ≤ 24h
  mt5_connected : bool|null — MT5 lane 新鮮度（scripts/forex_data_freshness.py --lane mt5 退出碼）
  backup_ok     : bool|null — 每日備份（BACKUP_RUNBOOK：04:00 VACUUM INTO）最新快照 ≤ 24h
  ea_heartbeat  : bool|null — EA 心跳（CCY Power 每鐘 pipeline 最新 commit ≤ 2h）
  checked_at    : string    — HKT ISO8601 檢查時點

null = 燈轉 N/A（灰）——來源喺本機唔存在／唔適用（例如非生產環境），唔當 false 誤報。

五燈來源（2026-10-28 ZCODE_w 掃描實證）：
  ranking_fresh ← git log -1 docs/admin/signal_ranking.html（05:30 automation；48h 容錯已蓋周末）
  newsguard_ok  ← git log -1 docs/admin/news_guard.csv（06:10 掃描；24h 閾值）
  mt5_connected ← 子進程跑 scripts/forex_data_freshness.py --lane mt5（exit 0=True/1=False；
                   腳本缺/WSL /mnt/c 缺 → null）。休市豁免窗口 exit 0 = 燈照綠（豁免=唔檢查）
  backup_ok     ← $TSA_BACKUP_ROOT（預設 ~/tsa_backups）/daily/ 最新 *.db mtime ≤ 24h
  ea_heartbeat  ← git log --grep="CCY Power" -1（每鐘；2h 容錯）

用法：
  python3 scripts/generate_health_json.py [--repo ROOT] [--out PATH] [--stdout]
      [--backup-root DIR] [--skip-mt5]
  cron（生產，每小時）：
  30 * * * * cd <repo> && python3 scripts/generate_health_json.py --repo . \
      --out docs/home/health.json >> $HOME/tsa_backups/health.log 2>&1
"""
import argparse
import glob as globmod
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone

HKT = timezone(timedelta(hours=8))

THRESH_RANKING_MIN = 48 * 60   # 每日 05:30 產物，48h 容錯（覆蓋周末兩日斷更）
THRESH_NEWSGUARD_MIN = 24 * 60 # 每日 06:00 掃描
THRESH_HEARTBEAT_MIN = 2 * 60  # 每鐘 CCY Power commit，2h 容錯
THRESH_BACKUP_MIN = 24 * 60    # 每日 04:00 備份

RANKING_PAGE = "docs/admin/signal_ranking.html"
NEWSGUARD_CSV = "docs/admin/news_guard.csv"
FRESHNESS_SCRIPT = "scripts/forex_data_freshness.py"


def now_hkt():
    return datetime.now(HKT)


def iso_hkt(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S+08:00")


def git_ct(repo, pathspec, grep=None):
    """git log 最後 commit epoch（本地時區）；無紀錄回 None。"""
    cmd = ["git", "-C", repo, "log", "-1", "--format=%ct"]
    if grep:
        cmd += ["--grep=" + grep]
    cmd += ["--", pathspec]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if out.returncode != 0 or not out.stdout.strip():
            return None
        return int(out.stdout.strip())
    except Exception:
        return None


def age_min(ct):
    if ct is None:
        return None
    return (datetime.now().timestamp() - ct) / 60.0


def check_git_source(repo, pathspec, thresh_min, label, detail):
    ct = git_ct(repo, pathspec)
    a = age_min(ct)
    if a is None:
        return None, detail
    ok = a <= thresh_min
    last = datetime.fromtimestamp(ct).astimezone(HKT)
    detail[label] = {"last_commit": iso_hkt(last), "age_min": round(a, 1)}
    return ok, detail


def check_heartbeat(repo, detail):
    """CCY Power 每鐘 pipeline：commit message grep。"""
    cmd = ["git", "-C", repo, "log", "-1", "--format=%ct", "--grep=CCY Power"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if out.returncode != 0 or not out.stdout.strip():
            return None, detail
        ct = int(out.stdout.strip())
    except Exception:
        return None, detail
    a = age_min(ct)
    last = datetime.fromtimestamp(ct).astimezone(HKT)
    detail["ea_heartbeat"] = {
        "last_ccy_power_commit": iso_hkt(last),
        "age_min": round(a, 1),
        "threshold_min": THRESH_HEARTBEAT_MIN,
    }
    return a <= THRESH_HEARTBEAT_MIN, detail


def check_backup(backup_root, detail):
    """BACKUP_RUNBOOK：$TSA_BACKUP_ROOT/daily/ 最新 .db ≤ 24h。"""
    if not backup_root or not os.path.isdir(backup_root):
        return None, detail
    daily = os.path.join(backup_root, "daily")
    if not os.path.isdir(daily):
        return None, detail
    snaps = globmod.glob(os.path.join(daily, "*.db"))
    if not snaps:
        return None, detail
    latest = max(snaps, key=os.path.getmtime)
    a = (datetime.now().timestamp() - os.path.getmtime(latest)) / 60.0
    last = datetime.fromtimestamp(os.path.getmtime(latest)).astimezone(HKT)
    detail["backup_ok"] = {
        "latest_snapshot": os.path.basename(latest),
        "last_run": iso_hkt(last),
        "age_min": round(a, 1),
        "threshold_min": THRESH_BACKUP_MIN,
    }
    return a <= THRESH_BACKUP_MIN, detail


def check_mt5(repo, skip, detail):
    """forex_data_freshness.py --lane mt5：exit 0=新鮮/休市豁免 → True；1=過期 → False；
    環境唔啱（腳本缺/非 WSL 生產機）→ null 灰燈。
    環境探針：無 FRESHNESS_DIR_OVERRIDE 時要求 /mnt/c 存在（生產 WSL 先有 MT5 terminal；
    機房/CI 等外來環境冇 /mnt/c，跑親必 1，會長期紅燈誤導 → 轉灰燈 N/A）。"""
    if skip:
        return None, detail
    script = os.path.join(repo, FRESHNESS_SCRIPT)
    if not os.path.isfile(script):
        return None, detail
    if not os.environ.get("FRESHNESS_DIR_OVERRIDE") and not os.path.isdir("/mnt/c"):
        detail["mt5_connected"] = {
            "probe": FRESHNESS_SCRIPT + " --lane mt5",
            "env": "非生產機（無 /mnt/c）→ N/A",
        }
        return None, detail
    try:
        r = subprocess.run(
            [sys.executable, script, "--lane", "mt5"],
            capture_output=True, text=True, timeout=120,
            cwd=repo,
        )
        lines = (r.stdout or "").strip().splitlines()
        msg = lines[-1] if lines else (r.stderr or "").strip().splitlines()[-1:]
        detail["mt5_connected"] = {
            "exit_code": r.returncode,
            "probe": FRESHNESS_SCRIPT + " --lane mt5",
            "last_line": (msg if isinstance(msg, str) else (msg[0] if msg else ""))[:160],
        }
        if r.returncode == 0:
            return True, detail
        if r.returncode == 1:
            return False, detail
        return None, detail  # 2=參數錯誤等 → 當環境異常，灰燈
    except Exception as e:
        detail["mt5_connected"] = {"error": str(e)[:160]}
        return None, detail


def build_health(repo, backup_root, skip_mt5):
    detail = {}
    ranking_fresh, detail = check_git_source(
        repo, RANKING_PAGE, THRESH_RANKING_MIN, "ranking_fresh", detail)
    newsguard_ok, detail = check_git_source(
        repo, NEWSGUARD_CSV, THRESH_NEWSGUARD_MIN, "newsguard_ok", detail)
    mt5_connected, detail = check_mt5(repo, skip_mt5, detail)
    backup_ok, detail = check_backup(backup_root, detail)
    ea_heartbeat, detail = check_heartbeat(repo, detail)

    payload = {
        "ranking_fresh": ranking_fresh,
        "newsguard_ok": newsguard_ok,
        "mt5_connected": mt5_connected,
        "backup_ok": backup_ok,
        "ea_heartbeat": ea_heartbeat,
        "checked_at": iso_hkt(now_hkt()),
    }
    payload["_meta"] = {
        "thresholds_min": {
            "ranking_fresh": THRESH_RANKING_MIN,
            "newsguard_ok": THRESH_NEWSGUARD_MIN,
            "ea_heartbeat": THRESH_HEARTBEAT_MIN,
            "backup_ok": THRESH_BACKUP_MIN,
        },
        "null_semantics": "N/A（來源唔存在於本機/唔適用）",
        "detail": detail,
    }
    return payload


def main():
    ap = argparse.ArgumentParser(description="TSA health.json generator（五燈）")
    ap.add_argument("--repo", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                    help="repo 根（預設：腳本上上一層）")
    ap.add_argument("--out", default=None,
                    help="輸出 JSON 路徑（預設：stdout）")
    ap.add_argument("--stdout", action="store_true", help="強制印 JSON 唔寫檔")
    ap.add_argument("--backup-root", default=os.environ.get(
        "TSA_BACKUP_ROOT", os.path.join(os.path.expanduser("~"), "tsa_backups")),
        help="備份根目錄（預設 $TSA_BACKUP_ROOT 或 ~/tsa_backups）")
    ap.add_argument("--skip-mt5", action="store_true",
                    help="跳過 MT5 探探測（輸出 null；非 WSL 環境用）")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    if not os.path.isdir(os.path.join(repo, ".git")):
        print(f"[health] ❌ 唔係 git repo：{repo}", file=sys.stderr)
        return 1

    payload = build_health(repo, args.backup_root, args.skip_mt5)

    blob = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out and not args.stdout:
        out = os.path.abspath(args.out)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            f.write(blob + "\n")
        flags = {k: payload[k] for k in
                 ("ranking_fresh", "newsguard_ok", "mt5_connected", "backup_ok", "ea_heartbeat")}
        print(f"[health] ✅ 寫入 {out}")
        print(f"[health] 燈：{json.dumps(flags, ensure_ascii=False)}")
    else:
        print(blob)
    return 0


if __name__ == "__main__":
    sys.exit(main())
