#!/usr/bin/env python3
"""
conflict_marker_check.py — L24 衝突標記門禁（2026-10-31 a0826fb3 事故防再犯）

事故：OpenClaw clone 帶舊 stash，pull 後 stash pop 撞衝突未解決就 commit+push，
將 git merge 衝突標記（<<<<<<< Updated upstream / >>>>>>> Stashed changes）推入
4 頁加密頁＋雙 staticryptConfig，線上密碼閘不可靠約 2.3 小時。

檢測：全樹掃描行首 git 衝突 START/END 標記（含空格版與無空格版）：
  ^<<<<<<<   ^>>>>>>>   ^<<<<<<< HEAD 等
唔掃中間 ^======= —— markdown setext 標題底線會誤報。
Base64 字母表唔含 < >，加密頁單行 base64 唔會誤報。

Usage: python3 tests/conflict_marker_check.py
Exit: 0=clean, 1=found markers
"""
import os
import sys

START_PREFIXES = ("<<<<<<<", ">>>>>>>")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".staticrypt-tmp"}
MAX_FILE = 64 * 1024 * 1024  # 64MB 上限（最大加密頁 ~28MB 在場）

def main() -> int:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    hits = []
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                if os.path.getsize(path) > MAX_FILE or os.path.getsize(path) == 0:
                    continue
                with open(path, "rb") as fh:
                    data = fh.read()
            except OSError:
                continue
            scanned += 1
            # 二進制粗判：含 NUL 跳過（衝突標記事故只會發生在文本檔）
            if b"\x00" in data:
                continue
            text = data.decode("utf-8", errors="ignore")
            for lineno, line in enumerate(text.splitlines(), 1):
                s = line.lstrip("\ufeff").rstrip()
                if s.startswith(START_PREFIXES):
                    rel = os.path.relpath(path, root)
                    hits.append(f"{rel}:{lineno}: {s[:80]}")
    if hits:
        print(f"[conflict-check] FAIL: {len(hits)} 衝突標記行（{scanned} 檔掃描）")
        for h in hits[:50]:
            print("  " + h)
        if len(hits) > 50:
            print(f"  ...共 {len(hits)} 行")
        return 1
    print(f"[conflict-check] PASS: 0 衝突標記（{scanned} 檔掃描）")
    return 0

if __name__ == "__main__":
    sys.exit(main())
