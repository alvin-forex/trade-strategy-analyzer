#!/usr/bin/env python3
"""
OpenClaw Session Backup Script

備份所有 agent 嘅 session 對話紀錄到指定目錄。
支援：
1. 備份 sessions.json metadata
2. 備份 trajectory.jsonl 實際對話
3. 自動清理 30 日以外嘅備份

Usage:
    python3 backup_sessions.py [--backup-dir DIR] [--retention-days N] [--dry-run]
"""

import argparse
import json
import os
import shutil
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path


def get_agents_dir():
    """Find the OpenClaw agents directory."""
    return Path.home() / ".openclaw" / "agents"


def discover_agents(agents_dir):
    """Discover all agents that have session data."""
    agents = []
    if not agents_dir.exists():
        return agents
    for entry in sorted(agents_dir.iterdir()):
        if entry.is_dir() and (entry / "sessions" / "sessions.json").exists():
            agents.append(entry.name)
    return agents


def get_active_sessions(agents_dir, agent_id, min_age_days=None):
    """
    Read sessions.json and return active sessions.
    If min_age_days is set, only return sessions updated within that many days.
    """
    sessions_file = agents_dir / agent_id / "sessions" / "sessions.json"
    if not sessions_file.exists():
        return {}

    with open(sessions_file) as f:
        data = json.load(f)

    # sessions.json can be either a dict keyed by session key,
    # or a dict with "sessions" array
    if isinstance(data, dict) and "sessions" in data:
        # Array format from CLI --json
        sessions = {}
        for s in data.get("sessions", []):
            key = s.get("key")
            if key:
                sessions[key] = s
    else:
        sessions = data

    if min_age_days is not None:
        cutoff = time.time() - (min_age_days * 86400)
        cutoff_ms = cutoff * 1000
        filtered = {}
        for key, info in sessions.items():
            updated = info.get("updatedAt", 0)
            if updated >= cutoff_ms:
                filtered[key] = info
        return filtered

    return sessions


def find_trajectory_file(sessions_dir, session_info):
    """
    Find the trajectory JSONL file for a session.
    Tries multiple possible naming patterns:
    1. {sessionId}.trajectory.jsonl
    2. {sessionId}.jsonl
    3. Read {sessionId}.trajectory-path.json pointer
    """
    session_id = session_info.get("sessionId")
    if not session_id:
        return None

    # Try {sessionId}.trajectory.jsonl
    trajectory = sessions_dir / f"{session_id}.trajectory.jsonl"
    if trajectory.exists():
        return trajectory

    # Try {sessionId}.jsonl (newer format)
    trajectory = sessions_dir / f"{session_id}.jsonl"
    if trajectory.exists():
        return trajectory

    # Try trajectory-path.json pointer
    path_file = sessions_dir / f"{session_id}.trajectory-path.json"
    if path_file.exists():
        try:
            with open(path_file) as f:
                ptr = json.load(f)
            runtime = ptr.get("runtimeFile")
            if runtime and Path(runtime).exists():
                return Path(runtime)
        except (json.JSONDecodeError, KeyError):
            pass

    return None


def backup_session(backup_dir, agent_id, session_key, session_info, sessions_dir, dry_run=False):
    """
    Backup a single session's trajectory data.
    Returns (success, file_path_or_error).
    """
    # Sanitize session key for filename
    safe_key = session_key.replace(":", "_").replace("/", "_").replace("@", "_")
    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")

    session_backup_dir = backup_dir / agent_id / safe_key
    session_backup_dir.mkdir(parents=True, exist_ok=True)

    trajectory = find_trajectory_file(sessions_dir, session_info)
    if not trajectory or not trajectory.exists():
        return False, "No trajectory file found"

    # Copy trajectory file with timestamp
    dest = session_backup_dir / f"{ts}_trajectory.jsonl"
    if not dry_run:
        shutil.copy2(trajectory, dest)
    return True, str(dest)


def backup_metadata(backup_dir, agent_id, agents_dir, dry_run=False):
    """Backup the sessions.json metadata for an agent."""
    source = agents_dir / agent_id / "sessions" / "sessions.json"
    if not source.exists():
        return False, "No sessions.json found"

    ts = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    dest = backup_dir / agent_id / f"{ts}_sessions.json"
    if not dry_run:
        (backup_dir / agent_id).mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
    return True, str(dest)


def cleanup_old_backups(backup_dir, retention_days=30, dry_run=False):
    """Remove backups older than retention_days."""
    if not backup_dir.exists():
        return 0

    cutoff = time.time() - (retention_days * 86400)
    removed = 0

    for root, dirs, files in os.walk(backup_dir):
        for fname in files:
            fpath = Path(root) / fname
            try:
                mtime = fpath.stat().st_mtime
                if mtime < cutoff:
                    if not dry_run:
                        fpath.unlink()
                    removed += 1
            except OSError:
                pass

    # Remove empty directories
    if not dry_run:
        for root, dirs, files in os.walk(backup_dir, topdown=False):
            if root != str(backup_dir) and not os.listdir(root):
                os.rmdir(root)

    return removed


def run_backup(backup_dir=None, retention_days=30, max_age_days=None, dry_run=False):
    """Main backup routine."""
    agents_dir = get_agents_dir()
    if backup_dir is None:
        backup_dir = Path.home() / ".openclaw" / "backups" / "sessions"
    else:
        backup_dir = Path(backup_dir)

    backup_dir.mkdir(parents=True, exist_ok=True)

    agents = discover_agents(agents_dir)
    if not agents:
        print("No agents with session data found.")
        return {"agents": 0, "sessions": 0, "ok": 0, "fail": 0, "cleanup": 0}

    stats = {"agents": len(agents), "sessions": 0, "ok": 0, "fail": 0, "cleanup": 0, "details": []}

    print(f"[{datetime.now().isoformat()}] Starting session backup...")
    print(f"  Backup dir: {backup_dir}")
    print(f"  Retention: {retention_days} days")
    print(f"  Agents found: {', '.join(agents)}")
    if dry_run:
        print("  *** DRY RUN - no files will be written ***")

    for agent_id in agents:
        sessions_dir = agents_dir / agent_id / "sessions"

        # Backup metadata
        ok, result = backup_metadata(backup_dir, agent_id, agents_dir, dry_run)
        stats["details"].append({
            "agent": agent_id,
            "metadata": "ok" if ok else result,
            "metadata_path": result if ok else None
        })
        print(f"  [{agent_id}] Metadata: {'OK' if ok else result}")

        # Get active sessions
        sessions = get_active_sessions(agents_dir, agent_id, min_age_days=max_age_days)
        stats["sessions"] += len(sessions)

        for session_key, info in sessions.items():
            ok, result = backup_session(backup_dir, agent_id, session_key, info, sessions_dir, dry_run)
            if ok:
                stats["ok"] += 1
            else:
                stats["fail"] += 1
                if args.verbose or stats["fail"] <= 10:  # Print first 10 failures by default
                    print(f"    [{agent_id}] {session_key}: FAILED - {result}")
                stats["details"].append({
                    "agent": agent_id,
                    "session": session_key,
                    "status": "ok" if ok else result,
                    "path": result if ok else None
                })

    # Cleanup old backups
    removed = cleanup_old_backups(backup_dir, retention_days, dry_run)
    stats["cleanup"] = removed

    print(f"\nBackup complete:")
    print(f"  Agents: {stats['agents']}")
    print(f"  Sessions scanned: {stats['sessions']}")
    print(f"  Backed up OK: {stats['ok']}")
    print(f"  Failed: {stats['fail']}")
    print(f"  Old backups removed: {stats['cleanup']}")

    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenClaw Session Backup")
    parser.add_argument("--backup-dir", default=None,
                        help="Backup directory (default: ~/.openclaw/backups/sessions)")
    parser.add_argument("--retention-days", type=int, default=30,
                        help="Keep backups for this many days (default: 30)")
    parser.add_argument("--max-age-days", type=int, default=None,
                        help="Only backup sessions active within N days")
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without writing")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show detailed failure reasons")
    args = parser.parse_args()

    stats = run_backup(
        backup_dir=args.backup_dir,
        retention_days=args.retention_days,
        max_age_days=args.max_age_days,
        dry_run=args.dry_run
    )

    sys.exit(1 if stats["fail"] > 0 and stats["ok"] == 0 else 0)
