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
import sys
from typing import Dict, Tuple

SCRIPT_NAME = "sidebar.js"
STYLE_NAME = "sidebar.css"
_SIDEBAR_REF = re.compile(r"""<script\b[^>]*src\s*=\s*["'][^"']*sidebar\.js["']""", re.I)
_STYLE_REF = re.compile(r"""<link\b[^>]*href\s*=\s*["'][^"']*sidebar\.css["']""", re.I)
# sidebar 實體持有人（`docs/shell.html` 例外）：自己就係導航本身，唔應該再載 sidebar.js。
# 實測 shell.html 明寫「本頁唔載 sidebar.js（佢本身就係 sidebar 持有人）——QA EXPECTED_PAGES 例外項」。
_SIDEBAR_HOST = re.compile(r"""<nav\b[^>]*id\s*=\s*["']tsa-sidebar["']""", re.I)
# `</body>` 唔一定獨立一行（實測 `docs/admin/bt/index.html` 係 `</body></html>`）；
# 取**最後一個** `</body>` 之前插，令 script 一定喺 body 內。
_BODY_CLOSE = re.compile(r"</body\s*>", re.I)
_HEAD_CLOSE = re.compile(r"</head\s*>", re.I)
_ENCRYPTED = ("staticrypt", "stati-crypt")

# 已確認「加密頁而真係唔應該插 sidebar」嘅白名單。唔在名單嘅 REFUSED 會令 --check exit 1，
# 否則「有頁真缺但係加密」同「已 OK」永遠分唔開（review 2026-11-27 I-2）。
KNOWN_REFUSED = {"docs/admin/tasks_board.html"}


def relative_sidebar_path(page_path: str, sidebar_dir: str) -> str:
    """算出由 `page_path` 指去 `<sidebar_dir>/sidebar.js` 的相對路徑（永遠用 `/`）。"""
    rel_dir = os.path.relpath(sidebar_dir, os.path.dirname(page_path))
    if rel_dir == ".":
        return SCRIPT_NAME
    return rel_dir.replace(os.sep, "/") + "/" + SCRIPT_NAME


def relative_style_path(page_path: str, sidebar_dir: str) -> str:
    """算出由 `page_path` 指去 `<sidebar_dir>/sidebar.css` 的相對路徑。"""
    rel_dir = os.path.relpath(sidebar_dir, os.path.dirname(page_path))
    if rel_dir == ".":
        return STYLE_NAME
    return rel_dir.replace(os.sep, "/") + "/" + STYLE_NAME


def is_encrypted(html: str) -> bool:
    """StatiCrypt 判斷。掃**全文**而唔止頭 3000 字——實測 `docs/shell.html` 的
    `staticrypt` 字樣在第 7420 字元（其餘 9 個加密頁都在 2000 以內）。今日靠
    `_SIDEBAR_HOST` 先命中冇出事，但呢個係隱性耦合：若 shell.html 結構改，
    就會錯插 sidebar.js 落 shell 造成雙 sidebar。10 頁成本可忽略。"""
    return any(tok in html.lower() for tok in _ENCRYPTED)


def inject_sidebar(html: str, page_path: str, sidebar_dir: str,
                   add_static_css: bool = True) -> Tuple[str, Dict]:
    """把 sidebar script 標籤插入頁尾（可選同時補靜態 `<link sidebar.css>`）。

    report 鍵：status / changed / src / style / reason
    status: ALREADY | INSERTED | REFUSED | PARTIAL

    **為何要補靜態 CSS（review 2026-11-27 I-3）**：`sidebar.js` 第 31-36 行會
    動態 append `<link sidebar.css>`，但 CSS 到手之前 `<nav class="sidebar">` 係
    未樣式化的普通 nav（`position:static`、寬 1264px、透明底）壓在正文上。
    實測慢網（CSS 延遲 1.5s）會見到「一整頁寬的導航清單閃一下」再縮成 200px。
    全站 710 頁都有靜態 `<link>`；呢 6 頁冇，所以補齊同全站一致。
    """
    src = relative_sidebar_path(page_path, sidebar_dir)
    style = relative_style_path(page_path, sidebar_dir)
    report: Dict = {"status": "ALREADY", "changed": False,
                    "src": src, "style": style, "reason": ""}

    if not html.strip():
        report.update(status="REFUSED", reason="空檔")
        return html, report
    # 先判「已有」再判「加密」：加密頁多數已經喺明文側注入過（實測 9/10 有），
    # 報 REFUSED 會誤導成「缺 sidebar」。
    has_script = bool(_SIDEBAR_REF.search(html))
    has_style = bool(_STYLE_REF.search(html))
    encrypted = is_encrypted(html)

    if has_script:
        report["reason"] = "已有 sidebar.js"
        if has_style or not add_static_css or encrypted:
            # 加密頁有 script 就唔再動（密文殼唔可以改結構）
            return html, report
        # 有 script 冇靜態 CSS → 補 CSS（真係改了東西）
        new_html, css_rep = _insert_style_link(html, style)
        if css_rep["changed"]:
            report.update(status="INSERTED", changed=True,
                          reason="已補靜態 sidebar.css（原本只有 JS 動態注入）")
            return new_html, report
        report["reason"] = "已有 sidebar.js；補 CSS 失敗：" + css_rep["reason"]
        return html, report
    if _SIDEBAR_HOST.search(html):
        report["reason"] = "本頁係 sidebar 實體持有人（<nav id=tsa-sidebar>），唔需要載 sidebar.js"
        return html, report
    if encrypted:
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

    # 同步補靜態 `<link sidebar.css>`：唔補會 FOUC（見 docstring）
    if add_static_css:
        new_html, css_rep = _insert_style_link(new_html, style)
        if not css_rep["changed"]:
            report["reason"] = "已插 script；補 CSS 失敗：" + css_rep["reason"]

    report.update(status="INSERTED", changed=True,
                  reason=report["reason"] or "已插入 {0}".format(src))
    return new_html, report


def _insert_style_link(html: str, style_href: str) -> Tuple[str, Dict]:
    """把 `<link rel="stylesheet" href=...sidebar.css>` 插在 `</head>` 之前。

    全站 710 頁都係靜態 link；`<head>` 唔存在時返回 changed=False（唔會亂插到 body）。
    """
    rep: Dict = {"changed": False, "reason": ""}
    if _STYLE_REF.search(html):
        rep["reason"] = "已有 sidebar.css"
        return html, rep
    m = _HEAD_CLOSE.search(html)
    if m is None:
        rep["reason"] = "頁面無 </head>，拒絕插入（避免 CSS 落到 body）"
        return html, rep
    line_start = html.rfind("\n", 0, m.start()) + 1
    prefix = html[line_start:m.start()]
    tag = '<link rel="stylesheet" href="{0}">'.format(style_href)
    if prefix.strip() == "":
        line = "{0}{1}\n".format(prefix, tag)
        out = html[:line_start] + line + html[line_start:]
    else:
        # `...內容</head>` 同一行 → 直接插，唔加換行（維持 1 行改 1 行，diff 最乾淨）
        out = html[:m.start()] + tag + html[m.start():]
    rep.update(changed=True, reason="已插入 sidebar.css")
    return out, rep


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
        if rep["changed"] and args.apply:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(out.replace("\n", eol))
            inserted += 1
            # 離開碼要反映**動作之後**的狀態：用寫回的內容重跑一次，令
            # `unexplained` 只計「套完之後仍然唔 OK」的頁（review 2026-11-27 I-4）。
            # 舊版用注入前的 report ⇒ INSERTED 全數落入 unexplained ⇒ 成功都 exit 1。
            _, rep = inject_sidebar(out, path, sidebar_dir)
        if rep["status"] == "REFUSED":
            refused += 1
        if rep["status"] != "ALREADY":
            rows.append({"page": norm, "status": rep["status"],
                         "src": rep["src"], "style": rep["style"],
                         "reason": rep["reason"]})

    # 離開碼：任何「未 ALREADY」而唔在白名單嘅頁都要令閘紅。
    # 舊版把 REFUSED 一律當 OK ⇒ 全站仍有 1 頁真缺都報 0（review 2026-11-27 I-2）。
    unexplained = []
    for r in rows:
        if r["status"] == "ALREADY":
            continue
        norm = r["page"].replace("\\", "/")
        if r["status"] == "REFUSED" and any(norm.endswith(k) for k in KNOWN_REFUSED):
            continue
        unexplained.append(r["page"])

    payload = {"dir": args.dir, "applied": inserted, "refused": refused,
               "rows": rows, "unexplained": unexplained}
    # Windows cp1252 stdout 會 crash（review M-3）——統一經 utf-8 bytes 過濾
    text = json.dumps(payload, ensure_ascii=False, indent=1)
    sys.stdout.write(text.encode("utf-8", "replace").decode("utf-8", "replace") + "\n")
    if args.apply:
        return 0 if not unexplained else 1
    return 0 if not unexplained else 1


if __name__ == "__main__":
    raise SystemExit(main())
