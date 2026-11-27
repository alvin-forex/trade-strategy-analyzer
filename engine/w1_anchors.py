"""W1 模板錨點轉換器（forex_reports C 族頁面）

把舊模板頁面轉成範本 A 骨架：
  - `<div class="news-section">`  → `<details class="card" id="sec-news" open>`
  - `<div class="events-section">` → `<details class="card" id="sec-events" open>`
  - 四個 h3 加唯一錨點：sec-charts / sec-pair / sec-conclusion / sec-summary
  - 插入 `details.card` CSS 兩行

**正文 byte 級零變**：只改 wrapper 開標籤行、對應 `</div>` 收口行、h3 開標籤行、CSS 插入行。
唔重生成、唔格式化、唔改內文、唔改 EOL。

規格來源：exchange/from_openclaw/20261127_1120_加急_W1剩餘頁今下午完成/
參考實作：exchange/from_zcode/20261127_0840_ZCODE_w_generator_patch_v1.1_indent修正/
          apply_generator_w1_patch.py 之 apply_w1_anchors()／patch_css()
參考產物：commit 534074b6c（11-26 晚報，2 details＋5 錨點零正文變）

設計取捨（比 generator patch 版嚴格）：
  1. 冪等判斷逐項做——generator 版靠「兩個錨點都在就 return」，只有一個時會漏另一個。
  2. **配唔上就完全唔動**：wrapper 收口行必須係獨立一行且只有一個 `</div>`，
     否則整個 wrapper 原樣保留，**連 `<details>` 開標籤都唔寫**（開咗就必然唔閉合）。
  3. div 深度計數有下界檢查（depth < 0 即刻放棄），唔靠撞 depth == 0。
  4. 深度計數前先把 HTML 註解遮掉，避免 `<!-- </div> -->` 之類殘留搞亂。
  5. h3 錨點去重：同一個 slug 全頁只准出現一次（SPEC §1.3）。
  6. CSS 只插喺 `<style>` 開標籤之後（唔猜 `.news-section` 規則位置——
     該規則跨行時會把宣告塊劈開）；`<style>` 與 `</style>` 同一行則拒改並報警。
  7. `details.card` 已存在時用容許空白的 regex 判斷（`details.card{` 亦算）。
  8. status 同 warnings 唔准矛盾：仍有未轉換 wrapper ⇒ REFUSED（未改）／PARTIAL（改了一部分），
     唔會扮 ALREADY。
"""
import re
from typing import Dict, List, Tuple

# 四個 h3 錨點（sec-news／sec-events 由 wrapper 轉換而來，唔喺此表）
H3_ANCHORS: Tuple[Tuple[str, str], ...] = (
    ("技術指標全景", "sec-summary"),
    ("個別貨幣對分析", "sec-pair"),
    ("對比結論", "sec-conclusion"),
    ("\U0001F4CA Charts", "sec-charts"),
)

# 所有 W1 錨點 id（供驗證用）
SEC_IDS: Tuple[str, ...] = ("sec-news", "sec-events") + tuple(
    slug for _, slug in H3_ANCHORS
)

WRAP_IDS: Dict[str, str] = {
    "news-section": "sec-news",
    "events-section": "sec-events",
}

CSS_SNIPPET = (
    "details.card { background: #161b22; border-radius: 8px; padding: 12px; "
    "margin-bottom: 14px; }\n"
    "details.card > summary { cursor: pointer; }"
)

# 只認整行 wrapper 開標籤（行首可縮排，可帶額外屬性）
_WRAP_OPEN = re.compile(r'^(\s*)<div class="([a-z][a-z0-9-]*-section)"([^>]*)>\s*$')
# 收口行必須係獨立一行、只得一個 </div>
_CLOSE_ONLY = re.compile(r'^\s*</div>\s*$')
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_OPEN_DIV = re.compile(r"<div\b")
_CLOSE_DIV = re.compile(r"</div>")
_STYLE_OPEN = re.compile(r"^\s*<style\b", re.I)


def _mask_comments(text: str) -> str:
    """把 HTML 註解換成等量換行，令行號不變但註解內的標籤唔會被計入深度。"""
    def repl(m):
        return "\n" * m.group(0).count("\n")
    return _COMMENT.sub(repl, text)


def _depth_delta(line: str) -> int:
    return len(_OPEN_DIV.findall(line)) - len(_CLOSE_DIV.findall(line))


def _convert_wrappers(lines: List[str], masked: List[str],
                      report: Dict, seen_ids: set) -> Tuple[List[str], List[str]]:
    """回 (新 lines, 新 masked)。配唔上就整段唔動。"""
    out: List[str] = []
    out_masked: List[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = _WRAP_OPEN.match(line)
        if not m or m.group(2) not in WRAP_IDS:
            out.append(line)
            out_masked.append(masked[i])
            i += 1
            continue

        indent, cls, attrs = m.group(1), m.group(2), m.group(3)
        slug = WRAP_IDS[cls]
        if 'id="{0}"'.format(slug) in attrs:
            # 生成器舊寫法 `<div class="news-section" id="sec-news">`：已帶錨點但未轉卡
            report["warnings"].append(
                "{0}: 已帶 id=\"%s\" 但仍是 div，未轉 details（需人手確認）".format(cls, )
                % slug)
            report["leftovers"].append(cls)
            seen_ids.add(slug)
            out.append(line)
            out_masked.append(masked[i])
            i += 1
            continue

        depth = _depth_delta(masked[i])       # 開標籤行本身
        j, close_idx = i + 1, None
        while j < n:
            depth += _depth_delta(masked[j])
            if depth < 0:                     # 收口過多／註解殘留：即刻放棄
                break
            if depth == 0:
                close_idx = j
                break
            j += 1

        bad = None
        if close_idx is None:
            bad = "搵唔到對應 </div>（或中途收口數目異常）"
        elif not _CLOSE_ONLY.match(lines[close_idx]):
            bad = "收口行唔係獨立 </div>：{0!r}".format(lines[close_idx][:60])
        elif lines[close_idx].count("</div>") != 1:
            bad = "收口行有多個 </div>"
        if bad:
            report["warnings"].append("unmatched wrapper: {0} — {1}；整段原樣保留".format(cls, bad))
            report["leftovers"].append(cls)
            out.append(line)
            out_masked.append(masked[i])
            i += 1
            continue

        if slug in seen_ids:
            # 頁內已有同名錨點（例如舊代 <section id="sec-news">）→ 會產生重複 id
            report["warnings"].append(
                "{0}: 頁內已有 id=\"{1}\"，再轉會產生重複 id（SPEC §1.3）；整段原樣保留".format(
                    cls, slug))
            report["leftovers"].append(cls)
            out.append(line)
            out_masked.append(masked[i])
            i += 1
            continue

        out.append('{0}<details class="card" id="{1}" open>'.format(indent, slug))
        out_masked.append("")                  # 淨開標籤，深度 delta = 0
        i += 1
        while i < close_idx:
            out.append(lines[i])
            out_masked.append(masked[i])
            i += 1
        out.append(indent + "</details>")
        out_masked.append("")
        seen_ids.add(slug)
        report["wrappers"].append({"from": cls, "to": slug})
        i += 1
    return out, out_masked


def _convert_headings(lines: List[str], report: Dict, seen_ids: set) -> List[str]:
    out: List[str] = []
    for line in lines:
        new_line = line
        if "<h3" in line:
            for key, slug in H3_ANCHORS:
                if key not in line:
                    continue
                if 'id="{0}"'.format(slug) in line:
                    seen_ids.add(slug)         # 本行已有，記住唔好再掛
                    break
                if slug in seen_ids:
                    report["warnings"].append(
                        "{0}: 頁內已有 id=\"{1}\"，唔再重複掛（SPEC §1.3 一頁一次）".format(
                            key, slug))
                    break
                if "<h3>" in line:
                    new_line = line.replace("<h3>", '<h3 id="{0}">'.format(slug), 1)
                else:
                    new_line = re.sub(r"<h3\s", '<h3 id="{0}" '.format(slug), line, count=1)
                seen_ids.add(slug)
                report["headings"].append({"key": key, "to": slug})
                break
        out.append(new_line)
    return out


def _insert_css(lines: List[str], report: Dict) -> List[str]:
    joined = "\n".join(lines)
    if re.search(r"details\.card\s*\{", joined):
        report["css"] = "ALREADY"
        return lines
    for idx, line in enumerate(lines):
        if not _STYLE_OPEN.match(line):
            continue
        if "</style>" in line:
            report["css"] = "SKIP：<style> 與 </style> 同行，唔敢猜插入點"
            report["warnings"].append("css: 單行 <style>，需人手處理")
            return lines
        lines = lines[:idx + 1] + CSS_SNIPPET.split("\n") + lines[idx + 1:]
        report["css"] = "OK（插於 <style> 開標籤後）"
        return lines
    report["css"] = "SKIP：找不到 <style>"
    report["warnings"].append("css: 頁面無 <style> 區塊，細節卡會無樣式")
    return lines


def _count_leftovers(masked_text: str) -> List[str]:
    """仍以 div 形式存在嘅 wrapper。"""
    found = []
    for cls in WRAP_IDS:
        if re.search(r'<div class="{0}"'.format(cls), masked_text):
            found.append(cls)
    return found


def _has_w1_type(masked_text: str) -> bool:
    for cls, slug in WRAP_IDS.items():
        if re.search(r'<div class="{0}"'.format(cls), masked_text):
            return True
        if re.search(r'<details[^>]*id="{0}"'.format(slug), masked_text):
            return True
    return False


def apply_w1_anchors(html: str) -> Tuple[str, Dict]:
    """對一頁 HTML 套 W1 錨點。回 (新 HTML, report)。

    report 鍵：status / changed / wrappers / headings / css / warnings / leftovers
    status:
      ALREADY    已套齊，無改動、無殘留
      APPLIED    有改動，兩個 wrapper 都轉齊
      CSS_ONLY   只補了 CSS（錨點本來已齊）
      PARTIAL    有改動，但仍有 wrapper 未轉
      REFUSED    wrapper 未轉齊且完全冇改動（有嘢要做但做唔到）
      NOOP       唔屬 C 族 W1 頁型（無 wrapper、無已轉換 details）
    """
    report: Dict = {
        "status": "ALREADY",
        "changed": False,
        "wrappers": [],
        "headings": [],
        "css": "ALREADY",
        "warnings": [],
        "leftovers": [],
    }
    if not html:
        report["status"] = "NOOP"
        return html, report

    masked_text = _mask_comments(html)
    if not _has_w1_type(masked_text):
        report["status"] = "NOOP"
        report["css"] = "SKIP：非 W1 頁型，唔插 CSS"
        report["warnings"].append("無 news/events wrapper：呢頁唔屬 C 族 W1 範圍")
        return html, report

    seen_ids = set(re.findall(r'id="(sec-[a-z0-9-]+)"', masked_text))

    lines = html.split("\n")
    masked = masked_text.split("\n")
    lines, masked = _convert_wrappers(lines, masked, report, seen_ids)
    lines = _convert_headings(lines, report, seen_ids)
    if report["wrappers"] or report["headings"]:
        lines = _insert_css(lines, report)
    else:
        lines = _insert_css(lines, report)     # 可能只缺 CSS（CSS_ONLY 情境）

    out = "\n".join(lines)
    leftover = _count_leftovers(_mask_comments(out))
    report["leftovers"] = sorted(set(report["leftovers"]) | set(leftover))

    if out == html:
        report["changed"] = False
        # 已套齊且無殘留 = 正常 no-op，唔算 warning
        report["status"] = "REFUSED" if report["leftovers"] else "ALREADY"
        return html, report

    report["changed"] = True
    if report["leftovers"]:
        report["status"] = "PARTIAL"
    elif not report["wrappers"] and not report["headings"]:
        report["status"] = "CSS_ONLY"
    else:
        report["status"] = "APPLIED"
    return out, report


def _detect_eol(text: str) -> str:
    return "\r\n" if "\r\n" in text else "\n"


def _iter_pages(reports_dir: str) -> List[str]:
    import glob
    import os
    return sorted(p for p in glob.glob(os.path.join(reports_dir, "*.html"))
                  if os.path.basename(p) != "index.html")


def main(argv=None) -> int:
    """CLI：對 docs/forex_reports/*.html 套 W1 錨點。

    用法：
        python -m engine.w1_anchors --check     # 只報狀態，唔寫檔
        python -m engine.w1_anchors --apply     # 就地套用
        python -m engine.w1_anchors --apply --dir docs/forex_reports

    離開碼：0 = 全部 OK；1 = 有 REFUSED／PARTIAL／warnings。
    """
    import argparse
    import json

    ap = argparse.ArgumentParser(description="W1 模板錨點轉換器（C 族 forex_reports）")
    ap.add_argument("--dir", default="docs/forex_reports")
    ap.add_argument("--apply", action="store_true", help="就地寫回")
    ap.add_argument("--check", action="store_true", help="只檢查唔寫")
    args = ap.parse_args(argv)

    if not args.apply and not args.check:
        ap.error("要指定 --check 或 --apply")

    rows = []
    applied = 0
    groups: Dict[str, int] = {}
    problems = 0
    for path in _iter_pages(args.dir):
        with open(path, encoding="utf-8", newline="") as fh:
            raw = fh.read()
        eol = _detect_eol(raw)
        src = raw.replace("\r\n", "\n")
        out, rep = apply_w1_anchors(src)
        groups[rep["status"]] = groups.get(rep["status"], 0) + 1
        if rep["status"] in ("REFUSED", "PARTIAL") or rep["warnings"]:
            problems += 1
        if args.apply and rep["changed"]:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(out.replace("\n", eol))
            applied += 1
        rows.append({
            "page": path.replace("\\", "/").rsplit("/", 1)[-1],
            "status": rep["status"],
            "wrappers": [w["to"] for w in rep["wrappers"]],
            "headings": [h["to"] for h in rep["headings"]],
            "leftovers": rep["leftovers"],
            "css": rep["css"],
            "warnings": rep["warnings"],
        })
    print(json.dumps({"dir": args.dir, "applied": applied,
                      "by_status": groups, "problem_rows": problems,
                      "rows": rows}, ensure_ascii=False, indent=1))
    return 0 if problems == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
