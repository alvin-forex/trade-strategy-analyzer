#!/usr/bin/env python3
"""Pre-push plaintext audit (L22c v2): every commit about to be pushed.

scripts/hooks/pre-push feeds us the standard pre-push stdin lines:

    <local_ref> <local_sha> <remote_ref> <remote_sha>

For each ref being updated we audit every commit new to that ref
(remote_sha..local_sha) — not just HEAD, so plaintext side branches and
plaintext intermediate commits are caught too (v1 gap reported by OpenClaw
live test 2026-10-21). For brand-new refs (remote tip all-zero) we audit the
commits that are new to the whole repo (local tip --not --remotes), so
ancient already-public history never triggers false positives. Ref deletions
are skipped.

Blob checks mirror tests/encryption_check.py (first 4KB must contain the
StatiCrypt marker) with one difference: MISSING is tolerated during history
walking — a historical commit predating a page's creation is not a leak.

Usage:
  python3 tests/push_audit.py            # pre-push mode (reads stdin)
  python3 tests/push_audit.py A..B C..D  # ad-hoc ranges
Exit 0 = clean; exit 1 = at least one plaintext core page in the push.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from encryption_check import CORE_PAGES  # noqa: E402

MAX_COMMITS_PER_REF = 200  # safety cap for pathological pushes


def git_out(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=False).stdout


def is_all_zero(sha: str) -> bool:
    return set(sha) == {"0"}


def commit_exists(sha: str) -> bool:
    r = subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"], capture_output=True, check=False)
    return r.returncode == 0


def commits_for_ref(local_sha: str, remote_sha: str) -> list[str]:
    """Commits that this ref update would make visible on the remote."""
    if not is_all_zero(remote_sha) and commit_exists(remote_sha):
        return git_out("rev-list", f"{remote_sha}..{local_sha}").split()
    # New ref (or remote tip unknown locally): audit commits new to the whole
    # repo; if that yields nothing (e.g. stale remote-tracking refs), audit
    # the tip commit alone.
    commits = git_out("rev-list", local_sha, "--not", "--remotes").split()
    if not commits and commit_exists(local_sha):
        return [local_sha]
    return commits


def audit_commit(sha: str, problems: list[tuple[str, str, str]]) -> None:
    for rel in CORE_PAGES:
        r = subprocess.run(["git", "show", f"{sha}:{rel}"], capture_output=True, check=False)
        if r.returncode != 0:
            continue  # MISSING tolerated in history (page did not exist yet)
        if b"staticrypt" not in r.stdout[:4096].lower():
            problems.append((sha[:8], "PLAINTEXT", rel))


def main() -> int:
    problems: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    capped = False

    def add_commits(commits: list[str]) -> None:
        nonlocal capped
        if len(commits) >= MAX_COMMITS_PER_REF:
            capped = True
        for sha in commits[:MAX_COMMITS_PER_REF]:
            if sha not in seen:
                seen.add(sha)
                audit_commit(sha, problems)

    if len(sys.argv) > 1:
        for spec in sys.argv[1:]:
            add_commits(git_out("rev-list", spec).split())
    else:
        for line in sys.stdin:
            parts = line.split()
            if len(parts) != 4:
                continue
            local_sha, remote_sha = parts[1], parts[3]
            if is_all_zero(local_sha) or not commit_exists(local_sha):
                continue  # ref deletion / unresolvable
            add_commits(commits_for_ref(local_sha, remote_sha))

    if problems:
        print(f"[push-audit] FAIL: {len(problems)} plaintext page hit(s) in the commits being pushed:")
        shown: set[tuple[str, str]] = set()
        for short, why, rel in problems:
            if (short, rel) in shown:
                continue
            shown.add((short, rel))
            print(f"[push-audit]   {short}  {why:9s} {rel}")
        print("[push-audit] fix: bash scripts/encrypt_admin_pages.sh BEFORE committing, then re-push")
        return 1
    note = f" (capped at {MAX_COMMITS_PER_REF}/ref)" if capped else ""
    print(f"[push-audit] PASS: no plaintext core pages in {len(seen)} audited commit(s){note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
