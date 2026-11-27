"""CSS 自訂變數（custom property）掃描與修補

用途：#39 全站模板統一嘅前置——確保每頁引用嘅 `var(--x)` 都有定義，
否則瀏覽器靜默 fallback 成透明／繼承，視覺壞但冇任何錯誤訊息。

呢個問題喺本專案真實發生（2026-11-27 實測）：
    `docs/reports/index_*.html` 共 151 頁評級徽章寫
    `background:var(--grade-a22)`，但 `--grade-a22` 全站零定義
    ⇒ 徽章背景透明（Chrome 實測 `rgba(0,0,0,0)`），只有文字顏色正常。
    根因：`scripts/tsa_w/rebuild_index_deep_v2.py:367` 把 hex 的 alpha 位
    誤寫成變數名一部分（`--grade-{x}` + `22` 應為 hex 後綴，唔係變數名後綴）。

同類第二宗（同日實測，未修）：23 頁 `var(--bg-hover)` 無定義且無 link
`tsa_tokens.css` ⇒ 背景透明。

## 關鍵設計（review 2026-11-27 修訂）

1. **只計頁面真正 link 到嘅外部 CSS**。預設把 `<dir>/tsa_tokens.css` 嘅定義
   算落每一頁係錯嘅——冇 `<link>` 嘅頁 runtime 根本冇嗰個變數。
   `resolve_page_tokens()` 逐頁解析 `<link rel=stylesheet>`；頁面引用
   `sidebar.js` 時亦計入 `sidebar.css`（該 JS 會自動注入）。
2. **遮罩（mask）而非刪除**。`mask_noise()` 用**等長**空白取代 `<script>`
   內容同 HTML 註解，令所有 offset 仍然對應原文。咁 `:root` 定位、括號計數、
   anchor 掃描全部唔會被 JS 字串／註解內嘅 `:root{...}`／`}` 呃到。
   先遮 `<script>` 再遮註解（否則 script 內嘅 `/*` 會跨語境吞掉 CSS）。
3. **`--apply` 只補真正缺嘅**。`decls ∩ undefined`；任何宣告都唔會撒落
   唔相關嘅頁。離開碼以「套用後重掃」為準，唔係「有冇動手」。
"""
import re
from typing import Dict, Iterable, List, Optional, Set, Tuple

# `var(--name)` 或 `var(--name, fallback)`。CSS 函數名大小寫不敏感 ⇒ IGNORECASE。
# 用 `,` 或 `)` 終止，避免貪婪食到下一個 token（`var(--x)22` 只算 `--x`）。
_USE = re.compile(r"var\(\s*(--[a-zA-Z0-9_-]+)\s*[,)]", re.I)
# 宣告 `--name:`。變數名大小寫**敏感**，所以呢個唔加 IGNORECASE。
_DEF = re.compile(r"(--[a-zA-Z0-9_-]+)\s*:")
_ROOT = re.compile(r":root\s*\{")
_SCRIPT_BLOCK = re.compile(r"<script\b.*?</script>", re.S | re.I)
_HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
_CSS_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_STYLE_BLOCK = re.compile(r"<style\b[^>]*>(.*?)</style>", re.S | re.I)
_LINK_CSS = re.compile(r"""<link\b[^>]*?href\s*=\s*["']([^"']+\.css)[^"']*["']""", re.I)
_SCRIPT_SRC = re.compile(r"""<script\b[^>]*?src\s*=\s*["']([^"']+)["']""", re.I)


def _blank(text: str) -> str:
    """把一段文字換成等長空白（保留換行，令 line/offset 不變）。"""
    return "".join("\n" if ch == "\n" else " " for ch in text)


def mask_noise(text: str) -> str:
    """等長遮罩：`<script>` 內容 → 空白；HTML 註解 → 空白；CSS 註解 → 空白。

    先遮 `<script>`（連標籤一齊遮，長度不變），再遮 HTML 註解，最後遮 CSS 註解。
    因為 script 已被遮成空白，script 內嘅 `/*` 唔會再觸發 CSS 註解配對，
    所以唔會出現「跨 script 吞掉中間 CSS」。
    """
    out = _SCRIPT_BLOCK.sub(lambda m: _blank(m.group(0)), text)
    out = _HTML_COMMENT.sub(lambda m: _blank(m.group(0)), out)
    out = _CSS_COMMENT.sub(lambda m: _blank(m.group(0)), out)
    return out


def defined_vars(*texts: str) -> Set[str]:
    """把所有來源（頁面自身＋頁面真正 link 到嘅外部 CSS）嘅宣告名收集成集合。"""
    out: Set[str] = set()
    for t in texts:
        if t:
            out |= set(_DEF.findall(mask_noise(t)))
    return out


def used_vars(html: str) -> Set[str]:
    """頁面用到嘅變數名（`<script>` 同註解內嘅唔計）。"""
    return set(_USE.findall(mask_noise(html)))


def find_undefined_vars(html: str, token_texts: Iterable[str] = ()) -> List[str]:
    """回傳「用到但冇定義」嘅變數名（排序）。

    `token_texts` 只應該包含**該頁真正載入**嘅外部 CSS 內容。
    用 `resolve_page_tokens()` 由 `<link>` 自動求。
    """
    have = defined_vars(html, *token_texts)
    return sorted(used_vars(html) - have)


def resolve_page_tokens(html: str, page_path: str, css_root: str) -> List[str]:
    """求出該頁 runtime 真正載入嘅 `.css` 檔案內容。

    規則：
      - `<link rel=stylesheet href=...>` 指向嘅 `.css`（相對 `page_path`）
      - 若頁面引用 `sidebar.js`，一併計入同目錄 `sidebar.css`
        （`sidebar.js` 會自動 `createElement('link')` 注入）

    檔案唔存在就跳過（唔會假設存在）。
    """
    import os

    base = os.path.dirname(page_path)
    wanted: List[str] = []

    for href in _LINK_CSS.findall(html):
        if href.startswith(("http://", "https://", "//", "data:")):
            continue
        wanted.append(os.path.normpath(os.path.join(base, href)))

    for src in _SCRIPT_SRC.findall(html):
        if os.path.basename(src).lower() != "sidebar.js":
            continue
        candidate = os.path.normpath(os.path.join(css_root, "sidebar.css"))
        wanted.append(candidate)

    seen, texts = set(), []
    for path in wanted:
        if path in seen or not os.path.isfile(path):
            continue
        seen.add(path)
        with open(path, encoding="utf-8", errors="replace") as fh:
            texts.append(fh.read())
    return texts


def _find_root_block(masked: str) -> Optional[Tuple[int, int]]:
    """回傳第一個 `:root {...}` 的 (開放括號位置, 結尾括號位置)。用遮罩文字定位。

    括號計數只在遮罩文字上做，所以字串／註解內嘅 `}` 唔會誤導。
    """
    m = _ROOT.search(masked)
    if not m:
        return None
    open_idx = masked.find("{", m.end() - 1)
    if open_idx < 0:
        return None
    depth, i, n = 0, open_idx, len(masked)
    while i < n:
        ch = masked[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return open_idx, i
        i += 1
    return None


def insert_root_vars(html: str, decls: Dict[str, str]) -> Tuple[str, Dict]:
    """把 `decls` 插入頁面**第一個** `:root{}` 區塊（已存在嘅唔覆蓋）。

    decls 例：`{"--grade-a22": "#22C55E22"}`

    回 (新 html, report)。report 鍵：inserted / already / reason
    """
    report: Dict = {"inserted": [], "already": [], "reason": ""}
    if not decls:
        report["reason"] = "無需插入"
        return html, report

    have = defined_vars(html)
    todo = {k: v for k, v in decls.items() if k not in have}
    report["already"] = sorted(k for k in decls if k in have)
    if not todo:
        report["reason"] = "全部已定義"
        return html, report

    masked = mask_noise(html)
    span = _find_root_block(masked)
    if span is None:
        report["reason"] = "頁面無平衡嘅 :root 區塊，拒絕插入（避免改動結構）"
        return html, report
    open_idx, close_idx = span

    payload = "".join("{0}:{1};".format(k, v) for k, v in sorted(todo.items()))

    # 插入點：同 prefix 群組尾優先（補 --grade-*22 就插在最後一條 --grade-* 之後）
    prefixes = {k.rsplit("-", 1)[0] + "-" for k in todo if "-" in k[2:]}
    anchor = -1
    for pref in prefixes:
        for m2 in re.finditer(
                r"({0}[a-zA-Z0-9_-]+\s*:\s*[^;{{}}]+;)".format(re.escape(pref)),
                masked[open_idx:close_idx]):
            anchor = max(anchor, open_idx + m2.end())
    if anchor > 0:
        out = html[:anchor] + payload + html[anchor:]
        report["inserted"] = sorted(todo)
        report["reason"] = "已插入 {0} 個定義（接在同組宣告後）".format(len(todo))
        return out, report

    # 區塊尾可能冇分號（`...rgba(0,0,0,.4)}`），唔補就變成
    # `rgba(0,0,0,.4)--grade-a22:…` —— 兩條宣告串埋一齊，全部失效。
    j = close_idx - 1
    while j > open_idx and masked[j] in " \t\r\n":
        j -= 1
    if masked[j] not in ";{":
        payload = ";" + payload

    # 多行 :root（每條宣告一行）要跟隨其縮排／換行，唔好壓成一行
    line_start = html.rfind("\n", 0, close_idx) + 1
    multiline = "\n" in html[open_idx:close_idx]
    if multiline:
        indent_m = re.search(r"[ \t]*$", html[line_start:j + 1])
        indent = indent_m.group(0) if indent_m else ""
        if not indent:
            # 用最後一條宣告的縮排
            last_decl_m = list(re.finditer(r"\n([ \t]+)--", html[open_idx:close_idx]))
            indent = last_decl_m[-1].group(1) if last_decl_m else "  "
        body = "".join("\n{0}{1}:{2};".format(indent, k, v)
                       for k, v in sorted(todo.items()))
        out = html[:j + 1] + body + html[j + 1:]
    else:
        out = html[:close_idx] + payload + html[close_idx:]
    report["inserted"] = sorted(todo)
    report["reason"] = "已插入 {0} 個定義（接在 :root 尾）".format(len(todo))
    return out, report


def scan(html: str, token_texts: Iterable[str] = ()) -> Dict:
    """一頁掃描報表：用到／已定義／未定義。

    `token_texts` 只應該包含該頁真正載入嘅外部 CSS（見 `resolve_page_tokens`）。
    """
    toks = list(token_texts)
    used = used_vars(html)
    have = defined_vars(html, *toks)
    return {
        "used": len(used),
        "defined": len(have),
        "undefined": sorted(used - have),
    }


def main(argv=None) -> int:
    """CLI。

        python -m engine.css_vars --check --dir docs
        python -m engine.css_vars --apply --dir docs --add grade-a22=#22C55E22

    離開碼：0 = 掃描後無未定義變數；1 = 仍有（不論係原本有定修唔到）。
    """
    import argparse
    import glob
    import json
    import os

    ap = argparse.ArgumentParser(description="CSS 自訂變數掃描（#39 前置閘）")
    ap.add_argument("--dir", default="docs")
    ap.add_argument("--token-file", action="append", default=[],
                    help="**強制**額外計入嘅 CSS，可重複（預設唔用，改由每頁 <link> 自動判斷）")
    ap.add_argument("--apply", action="store_true", help="就地修補")
    ap.add_argument("--check", action="store_true", help="只檢查")
    ap.add_argument("--add", action="append", default=[], metavar="NAME=VALUE",
                    help="要補嘅定義，可重複；name 唔使寫開頭兩個 dash，"
                         "例如 --add grade-a22=#22C55E22")
    ap.add_argument("--only", default=None, help="只處理路徑含此字串嘅頁")
    ap.add_argument("--skip", default=None, help="跳過路徑含此字串嘅頁")
    args = ap.parse_args(argv)

    if not args.apply and not args.check:
        ap.error("要指定 --check 或 --apply")

    decls: Dict[str, str] = {}
    for item in args.add:
        if "=" not in item:
            ap.error("--add 格式要 name=value：{0}".format(item))
        k, v = item.split("=", 1)
        k = k.strip()
        if not k.startswith("--"):
            k = "--" + k
        decls[k] = v.strip()

    forced: List[str] = []
    for tf in args.token_file:
        if os.path.exists(tf):
            with open(tf, encoding="utf-8") as fh:
                forced.append(fh.read())

    rows = []
    problem = 0
    applied = 0
    for path in sorted(glob.glob(os.path.join(args.dir, "**", "*.html"), recursive=True)):
        norm = path.replace("\\", "/")
        if args.only and args.only not in norm:
            continue
        if args.skip and args.skip in norm:
            continue
        with open(path, encoding="utf-8", newline="") as fh:
            raw = fh.read()
        eol = "\r\n" if "\r\n" in raw else "\n"
        html = raw.replace("\r\n", "\n")

        # 只計該頁真正 link 到嘅 CSS（+ 使用者強制指定）
        tokens = resolve_page_tokens(html, path, args.dir) + forced
        info = scan(html, tokens)
        rec = {"page": norm, "undefined": info["undefined"]}
        if info["undefined"]:
            problem += 1
            # 只補「這頁真的缺」且「使用者有提供值」嘅，唔會撒無關宣告
            todo = {k: v for k, v in decls.items() if k in info["undefined"]}
            if args.apply and todo:
                new_html, rep = insert_root_vars(html, todo)
                rec["patch"] = rep
                if rep["inserted"]:
                    with open(path, "w", encoding="utf-8", newline="") as fh:
                        fh.write(new_html.replace("\n", eol))
                    applied += 1
                    # 套用後重掃，用真實剩餘為準
                    rec["undefined"] = scan(new_html, tokens)["undefined"]
        rows.append(rec)

    remaining = [r for r in rows if r["undefined"]]
    print(json.dumps({"dir": args.dir,
                      "pages_scanned": len(rows),
                      "pages_with_undefined": len(remaining),
                      "applied": applied,
                      "rows": [r for r in rows if r["undefined"] or r.get("patch")]},
                     ensure_ascii=False, indent=1))
    return 0 if not remaining else 1


if __name__ == "__main__":
    raise SystemExit(main())
