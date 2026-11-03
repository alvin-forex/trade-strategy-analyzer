#!/usr/bin/env python3
"""L26 encrypted-layer dead-link scan (第四檔 sandbox layer, 2026-11-01).

今日兩單死 link（admin/signal_ranking 三條 c9e7e18 前遺留、root signal_ranking
topnav 三條 1955）都係加密頁內 link——CI L21（tests/link_check.py）見到嘅係
 StatiCrypt 密文，結構性掃唔到。呢個掃描器喺有密碼嘅環境（sandbox／加密作業
環境）解密後用同一套 resolve 邏輯掃加密 6 頁，補埋 L21 嘅盲區：

  - CI 層（L21，tests/link_check.py）：全站明文頁——密碼零入 CI，照舊
  - 本層（L26，本檔）：加密 6 頁解密掃——scripts/encrypt_admin_pages.sh 尾段
    自動調用（帶病頁唔准出門），亦可手動 / 每鐘巡檢調用

2026-11-04 增補（OpenClaw 回批「搬檔唔搬引用」第三次：quotePath、admin/ccy_power
掃描盲區、首頁 CCY fetch）：加 JS fetch() 路徑斷言——解密明文掃 fetch('...')
第一參字面量（含雙引號／反引號；template literal、外鏈 scheme、拼接表達式
由 normalize()／正則天然排除），逐個用 L21 同一套 resolve_check 對 docs 實檔
驗證，缺檔即 FAIL。修復前首頁 4 條 fetch 中 admin/ccy_power/data.json 會
DEAD（正中該回歸），實測成立。

密碼來源：$TSA_PW_FILE / $TSA_OWNER_PW_FILE，缺省 fallback
/home/z/my-project/.keys/。密碼永遠唔入 repo、唔入 CI。

用法：
  python3 scripts/tsa_w/scan_dead_links_encrypted.py              # 掃全部 6 頁
  python3 scripts/tsa_w/scan_dead_links_encrypted.py --file PATH --rel REL --tier general
      # 掃單一檔（PATH=本機路徑，REL=docs/ 相對位，tier=general|owner）
Exit 0 = 綠；Exit 1 = 有死 link。
"""
import argparse
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / 'tests'))
from link_check import ATTR_RE, build_real_files, normalize, resolve_check  # noqa: E402

# 加密 6 頁（老闆 10-28 兩層制；2026-11-01 admin 重組後 14→6，與
# tests/encryption_check.py CORE_PAGES 同步維護）
GENERAL = ['docs/admin/index.html', 'docs/index.html', 'docs/signal_ranking.html']
OWNER = ['docs/admin/db-browser.html', 'docs/admin/tasks_board.html', 'docs/admin/mt5_mcp_tools.html']

# 2026-11-04（OpenClaw 回批附帶請求）：JS fetch() 第一參字面量——單/雙引號/反引號。
# fetch( 後必須緊接引號先命中，`fetch(base + '/x.json')` 拼接表達式天然唔掃；
# 含 ${ 的 template literal 由 normalize() 排除（runtime 拼接）。
FETCH_RE = re.compile(r"fetch\(\s*(['\"`])((?:\\.|(?!\1).)+?)\1", re.I)


def pw_for(tier: str) -> str:
    env = 'TSA_PW_FILE' if tier == 'general' else 'TSA_OWNER_PW_FILE'
    fallback = f'/home/z/my-project/.keys/tsa_pw_{"general" if tier == "general" else "owner"}.txt'
    src = os.environ.get(env, fallback if os.path.exists(fallback) else '')
    if not src or not os.path.exists(src):
        print(f'[enc-link-check] FAIL: password for tier={tier} not found ({env})')
        sys.exit(2)
    return open(src, encoding='utf-8').read().strip()


def decrypt(rel: str, tier: str, tmpdir: str) -> str:
    out = os.path.join(tmpdir, rel.replace('/', '_'))
    r = subprocess.run(['node', str(REPO / 'scripts/staticrypt/decrypt_page.mjs'),
                        str(REPO / rel), '-p', pw_for(tier), '-o', out],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f'[enc-link-check] FAIL: decrypt {rel} ({tier}): {r.stderr.strip()[:120]}')
        sys.exit(2)
    return open(out, encoding='utf-8').read()


def scan_text(rel: str, text: str, real_files: set[str]) -> tuple[int, list]:
    rel_dir = Path(rel).parent.relative_to('docs').as_posix()  # docs 相對（L21 同基準）
    checked, dead = 0, []
    for m in ATTR_RE.finditer(text):
        tgt = normalize(m.group(1))
        if tgt is None:
            continue
        checked += 1
        reason = resolve_check(rel_dir, tgt, real_files)
        if reason is not None:
            dead.append((rel, m.group(1), reason))
    return checked, dead


def scan_fetch(rel: str, text: str, real_files: set[str]) -> tuple[int, list]:
    """2026-11-04：JS fetch() 路徑斷言——href/src 之外嘅第二盲區（搬檔唔搬引用）。"""
    rel_dir = Path(rel).parent.relative_to('docs').as_posix()
    checked, dead = 0, []
    for m in FETCH_RE.finditer(text):
        tgt = normalize(m.group(2))
        if tgt is None:
            continue
        checked += 1
        reason = resolve_check(rel_dir, tgt, real_files)
        if reason is not None:
            dead.append((rel, 'fetch(' + m.group(2) + ')', reason))
    return checked, dead


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', help='掃單一檔（本機路徑）')
    ap.add_argument('--rel', help='該檔喺 docs/ 相對位（例 docs/signal_ranking.html）')
    ap.add_argument('--tier', choices=['general', 'owner'], default='general')
    args = ap.parse_args()

    docs = REPO / 'docs'
    real_files = build_real_files()

    with tempfile.TemporaryDirectory() as tmp:
        if args.file:
            text = open(args.file, encoding='utf-8').read()
            pages = [(args.rel, text, args.tier)]
            label = f'single: {args.rel}'
        else:
            pages = []
            for tier, lst in (('general', GENERAL), ('owner', OWNER)):
                for rel in lst:
                    pages.append((rel, decrypt(rel, tier, tmp), tier))
            label = f'all encrypted pages ({len(pages)})'

        total = 0
        total_fetch = 0
        dead_all = []
        dead_fetch = []
        for rel, text, tier in pages:
            c, d = scan_text(rel, text, real_files)
            fc, fd = scan_fetch(rel, text, real_files)
            total += c
            total_fetch += fc
            dead_all.extend(d)
            dead_fetch.extend(fd)
            print(f'[enc-link-check] {rel} ({tier}): {c} links + {fc} fetch, dead {len(d) + len(fd)}')
        print(f'[enc-link-check] scope: {label}  internal links: {total} + fetch {total_fetch}  dead: {len(dead_all) + len(dead_fetch)}')
        for rel, raw, res in (dead_all + dead_fetch)[:30]:
            print(f'[enc-link-check] DEAD  {rel}  ->  {raw}  ({res})')
        if dead_all or dead_fetch:
            print('[enc-link-check] FAIL: dead links / dead fetch targets in encrypted layer')
            return 1
        print('[enc-link-check] PASS: encrypted layer 0 dead links, 0 dead fetch targets')
        return 0


if __name__ == '__main__':
    sys.exit(main())
