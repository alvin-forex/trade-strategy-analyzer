"""Sidebar 注入工具（#39 W4：全站 sidebar 零缺）

AGENTS.md 定「新頁面要加入 `docs/sidebar.js` 導航」「一律要 sidebar 無豁免」。
本模組負責把 `<script src="…/sidebar.js"></script>` 安全插入頁尾。

設計約束（每條都係實測踩過或會踩）：
  1. **相對路徑要對**：`docs/sidebar.js` 相對 `docs/tha/v52.html` 係 `../sidebar.js`，
     相對 `docs/admin/tha/index.html` 係 `../../sidebar.js`。計錯 = 404 = 冇導航。
  2. **冪等**：已有 `sidebar.js` 唔加第二次。
     只認**真嘅 script 標籤**（`<script … src="…sidebar.js"`），唔認註解或文字提及——
     實測 `docs/shell.html` 有 4 處文字提到 sidebar.js 但冇一個係 script 標籤，
     而佢本身就係 sidebar 實體持有人（唔應該加）。
  3. **`</body>` 之前插**：`</body>` 與其他內容同一行時（實測
     `docs/admin/bt/index.html` 係 `</body></html>`）直接喺之前插，唔會插到 `<html>` 外。
  4. **加密頁拒改**：StatiCrypt 頁係密文殼，插 script 會令解密流程失效
     （AGENTS.md：6 個核心頁加密，生成器重跑會寫返明文，commit 前要重新加密）。
     判斷次序係「先 ALREADY 再加密」——實測 10 個加密頁中 9 個明文側已有 sidebar。
  5. **EOL 保留**：寫回時唔可以翻新全檔（CRLF/LF 各自保持）。
"""
import os
import re
from typing import Dict, Tuple

SCRIPT_NAME = "sidebar.js"
_SIDEBAR_REF = re.compile(r"""<script\b[^>]*src\s*=\s*["'][^"']*sidebar\.js["']""", re.I)
# sidebar 實體持有人（`docs/shell.html` 例外）：自己就係導航本身，唔應該再載 sidebar.js。
# 實測 shell.html 明寫「本頁唔載 sidebar.js（佢本身就係 sidebar 持有人）——QA EXPECTED_PAGES 例外項」。
_SIDEBAR_HOST = re.compile(r"""<nav\b[^>]*id\s*=\s*["']tsa-sidebar["']""", re.I)
# `</body>` 唔一定獨立一行（實測 `docs/admin/bt/index.html` 係 `</body></html>`）；
# 取**最後一個** `</body>` 之前插，令 script 一定喺 body 內。
_BODY_CLOSE = re.compile(r"</body\s*>", re.I)
_ENCRYPTED = ("staticrypt", "stati-crypt")


def relative_sidebar_path(page_path: str, sidebar_dir: str) -> str:
    """算出由 `page_path` 指去 `<sidebar_dir>/sidebar.js` 的相對路徑（永遠用 `/`）。"""
    rel_dir = os.path.relpath(sidebar_dir, os.path.dirname(page_path))
    if rel_dir == ".":
        return SCRIPT_NAME
    return rel_dir.replace(os.sep, "/") + "/" + SCRIPT_NAME


def is_encrypted(html: str) -> bool:
    head = html[:3000].lower()
    return any(tok in head for tok in _ENCRYPTED)


def inject_sidebar(html: str, page_path: str, sidebar_dir: str) -> Tuple[str, Dict]:
    """把 sidebar script 標籤插入頁尾。回 (新 html, report)。

    report 鍵：status / changed / src / reason
    status: ALREADY | INSERTED | REFUSED
    """
    src = relative_sidebar_path(page_path, sidebar_dir)
    report: Dict = {"status": "ALREADY", "changed": False, "src": src, "reason": ""}

    if not html.strip():
        report.update(status="REFUSED", reason="空檔")
        return html, report
    # 先判「已有」再判「加密」：加密頁多數已經喺明文側注入過（實測 9/10 有），
    # 報 REFUSED 會誤導成「缺 sidebar」。
    if _SIDEBAR_REF.search(html):
        report["reason"] = "已有 sidebar.js"
        return html, report
    if _SIDEBAR_HOST.search(html):
        report["reason"] = "本頁係 sidebar 實體持有人（<nav id=tsa-sidebar>），唔需要載 sidebar.js"
        return html, report
    if is_encrypted(html):
        report.update(status="REFUSED", reason="StatiCrypt 加密頁，唔可以插 script")
        return html, report

    # 插在**最後一個** `</body>` 之前（script 必須在 body 內）；冇就插檔尾。
    # 縮排跟 `</body>` 所在行一致。
    last = None
    for m in _BODY_CLOSE.finditer(html):
        last = m
    if last is not None:
        line_start = html.rfind("\n", 0, last.start()) + 1
        prefix = html[line_start:last.start()]
        if prefix.strip() == "":
            # `</body>` 獨立一行（只有縮排）→ 前面插一行，用同一縮排
            line = '{0}<script src="{1}"></script>\n'.format(prefix, src)
            new_html = html[:line_start] + line + html[line_start:]
        else:
            # `...內容</body></html>` 同一行 → 直接在 </body> 前插，唔加縮排
            line = '<script src="{0}"></script>\n'.format(src)
            new_html = html[:last.start()] + line + html[last.start():]
    else:
        tail = "" if html.endswith("\n") else "\n"
        new_html = html + tail + '<script src="{0}"></script>'.format(src) + "\n"

    report.update(status="INSERTED", changed=True,
                  reason="已插入 {0}".format(src))
    return new_html, report


def main(argv=None) -> int:
    """CLI：全站掃描／注入 sidebar。離開碼 0 = 零缺（或全部已套），1 = 仍有缺。

        python -m engine.sidebar_inject --check --dir docs
        python -m engine.sidebar_inject --apply --dir docs
    """
    import argparse
    import glob
    import json
    import os

    ap = argparse.ArgumentParser(description="Sidebar 注入（#39 W4：全站零缺）")
    ap.add_argument("--dir", default="docs")
    ap.add_argument("--apply", action="store_true", help="就地注入")
    ap.add_argument("--check", action="store_true", help="只檢查")
    args = ap.parse_args(argv)

    if not args.apply and not args.check:
        ap.error("要指定 --check 或 --apply")

    sidebar_dir = os.path.abspath(args.dir)
    rows = []
    inserted = refused = 0
    for path in sorted(glob.glob(os.path.join(args.dir, "**", "*.html"), recursive=True)):
        with open(path, encoding="utf-8", newline="") as fh:
            raw = fh.read()
        eol = "\r\n" if "\r\n" in raw else "\n"
        html = raw.replace("\r\n", "\n")
        out, rep = inject_sidebar(html, path, sidebar_dir)
        norm = path.replace("\\", "/")
        if rep["status"] == "REFUSED":
            refused += 1
        if rep["changed"]:
            if args.apply:
                with open(path, "w", encoding="utf-8", newline="") as fh:
                    fh.write(out.replace("\n", eol))
                inserted += 1
        if rep["status"] != "ALREADY":
            rows.append({"page": norm, "status": rep["status"],
                         "src": rep["src"], "reason": rep["reason"]})

    remaining = [r for r in rows if r["status"] != "REFUSED"]
    print(json.dumps({"dir": args.dir, "applied": inserted,
                      "refused": refused, "rows": rows},
                     ensure_ascii=False, indent=1))
    if args.apply:
        return 0
    return 0 if not remaining else 1


if __name__ == "__main__":
    raise SystemExit(main())
