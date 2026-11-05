#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""W5-I（2026-11-05）：admin 加密 4 頁 NAV 三件注入工具（機房 lane ZCODE_w）。

範圍：docs/admin/{db-browser,mt5_mcp_tools,tasks_board,index}.html（解密態 plaintext）。
形態裁定（勘察 2026-11-05 11:4x）——四頁**零色彩改動**，統一三件＋tokens 豁免：
  db-browser     light var 真簽名（--bg:#f5f7fa）→ W5-E signal 族同款豁免
  mt5_mcp_tools  hardcode Apple light 頁（零 var 引用）→ tokens inert 無意義
  tasks_board    自帶 --l0:#0F1520 canonical 族 → W5-H ccy_power 同款豁免
  admin/index    雙主題 var 頁（dark --pri:#FFD700＋light override）→ master_v2
                 同款豁免；**sidebar.js 原已在位（114 行）——補 css＋container 唔重插 js**

注入形態（照 W5-E 出貨 byte 形態，6+/1-）：
  </head> 前      ：<!-- W5-I head 註釋 -->＋<link rel="stylesheet" href="../sidebar.css">
  <body...> 行內 ：追加 <!-- W5-I：NAV 之 #sidebar-container -->；後插
                   <div id="sidebar-container"></div>＋空行
  </body> 前      ：<script src="../sidebar.js"></script>（已在位即跳過）

工序次序：冪等閘先行（href="../sidebar.css" 在場即 skip）→ 錨點唯一性斷言 →
注入 → strip 純插入斷言（逆操作還原==原 bytes）。--dry 只報唔寫；--verify 收
後態覆核。

用法：
  python3 w5i_admin_nav_20261105.py --src-dir /tmp/w5i            # 實跑（原地改）
  python3 w5i_admin_nav_20261105.py --src-dir /tmp/w5i --dry
  python3 w5i_admin_nav_20261105.py --src-dir /tmp/w5i --verify
"""
import argparse
import os
import re
import sys

STAMP = "W5-I"
BODY_CMT = "<!-- W5-I：NAV 之 #sidebar-container -->"
CONTAINER = '<div id="sidebar-container"></div>'
JS_TAG = '<script src="../sidebar.js"></script>'
LINK_TAG = '<link rel="stylesheet" href="../sidebar.css">'

# 每頁 head 註釋（家族＋豁免理由）
HEAD_CMT = {
    "db-browser": "<!-- W5-I（2026-11-05）：NAV 三件 1+2——sidebar.css；tokens 豁免"
                  "（var 驅動 light 設計＋全站 dark default 會翻黑，照 W5-C v3.9 裁定——W5-E signal 族同款） -->",
    "mt5_mcp_tools": "<!-- W5-I（2026-11-05）：NAV 三件 1+2——sidebar.css；tokens 豁免"
                     "（hardcode Apple light 頁零 var 引用，tokens inert 無意義；零色彩改動） -->",
    "tasks_board": "<!-- W5-I（2026-11-05）：NAV 三件 1+2——sidebar.css；tokens 豁免"
                   "（自帶 --l0 canonical 族照 W5-H 先例；tasks_board_gen.py 模板層同步） -->",
    "index": "<!-- W5-I（2026-11-05）：NAV 三件 1+2——sidebar.css＋#sidebar-container 補齊"
             "（sidebar.js 原已在位）；tokens 豁免（雙主題 var 頁照 master_v2 先例） -->",
}
PAGES = ["db-browser", "mt5_mcp_tools", "tasks_board", "index"]

BODY_RE = re.compile(r"<body[^>]*>")


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def write(p, s):
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(s)


def inject(content, name):
    """返回 (patched, log)。冪等閘＋錨點斷言＋三件注入。"""
    if LINK_TAG in content:
        return content, ["冪等閘：sidebar.css 已在場 → skip"]
    assert content.count("</head>") == 1, f"{name}: </head> 錨點唔係恰 1"
    assert content.count("</body>") == 1, f"{name}: </body> 錨點唔係恰 1"
    mb = BODY_RE.findall(content)
    assert len(mb) == 1, f"{name}: <body> 錨點唔係恰 1（{len(mb)}）"

    log = []
    # 1) </head> 前：head 註釋＋css link
    head_snip = HEAD_CMT[name] + "\n" + LINK_TAG + "\n"
    content = content.replace("</head>", head_snip + "</head>", 1)
    log.append("head：註釋＋sidebar.css link 已插 </head> 前")
    # 2) <body...> 行內註釋＋container＋空行
    body_tag = mb[0]
    body_snip = body_tag + BODY_CMT + "\n" + CONTAINER + "\n\n"
    content = content.replace(body_tag, body_snip, 1)
    log.append("body：<body> 行內註釋＋#sidebar-container 已插")
    # 3) </body> 前：sidebar.js（已在位即跳——admin/index 先例）
    if 'src="../sidebar.js"' not in content:
        content = content.replace("</body>", JS_TAG + "\n</body>", 1)
        log.append("tail：sidebar.js 已插 </body> 前")
    else:
        log.append("tail：sidebar.js 原已在位 → 跳過（防重複）")
    return content, log


def strip(content, name):
    """逆操作——還原注入前 bytes（strip 純插入斷言用）。"""
    head_snip = HEAD_CMT[name] + "\n" + LINK_TAG + "\n"
    content = content.replace(head_snip, "", 1)
    mb = BODY_RE.findall(content)
    body_tag = mb[0]
    content = content.replace(
        body_tag + BODY_CMT + "\n" + CONTAINER + "\n\n", body_tag, 1)
    if JS_TAG + "\n</body>" in content:
        content = content.replace(JS_TAG + "\n</body>", "</body>", 1)
    return content


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src-dir", default="/tmp/w5i")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()

    if args.verify:
        ok = fail = 0
        for name in PAGES:
            p = os.path.join(args.src_dir, name + ".html")
            if not os.path.exists(p):
                print(f"MISS  {name}")
                fail += 1
                continue
            c = read(p)
            n_css = c.count('href="../sidebar.css"')
            n_cont = c.count('id="sidebar-container"')
            n_js = c.count('src="../sidebar.js"')
            n_tok = c.count("tsa_tokens.css")
            n_body_cmt = c.count(BODY_CMT)
            # strip 還原對 .orig
            orig_p = os.path.join(args.src_dir, name + ".orig.html")
            strip_ok = ""
            if os.path.exists(orig_p):
                strip_ok = " strip=OK" if strip(c, name) == read(orig_p) else " strip=FAIL"
            good = (n_css == 1 and n_cont == 1 and n_js == 1
                    and n_tok == 0 and n_body_cmt == 1 and "FAIL" not in strip_ok)
            print(f"{'PASS' if good else 'FAIL'}  {name}: css={n_css} cont={n_cont} "
                  f"js={n_js} tok={n_tok} body_cmt={n_body_cmt}{strip_ok}")
            ok += 1 if good else 0
            fail += 0 if good else 1
        print(f"VERIFY_DONE ok={ok} fail={fail}")
        sys.exit(1 if fail else 0)

    changed = skipped = 0
    for name in PAGES:
        p = os.path.join(args.src_dir, name + ".html")
        if not os.path.exists(p):
            print(f"MISS  {p}")
            continue
        c = read(p)
        if LINK_TAG in c:
            print(f"SKIP  {name}（冪等閘：已注入）")
            skipped += 1
            continue
        patched, log = inject(c, name)
        assert strip(patched, name) == c, f"{name}: strip 純插入斷言失敗"
        if args.dry:
            print(f"DRY   {name}: 會注入（{len(log)} 步）")
            for l in log:
                print(f"      - {l}")
        else:
            orig_p = os.path.join(args.src_dir, name + ".orig.html")
            if not os.path.exists(orig_p):
                write(orig_p, c)
            write(p, patched)
            print(f"ENC   {name}: 已注入＋strip 斷言 PASS")
            for l in log:
                print(f"      - {l}")
            changed += 1
    print(f"{'DRY' if args.dry else 'APPLY'}_DONE changed={changed} skipped={skipped}")
    sys.exit(0)


if __name__ == "__main__":
    main()
