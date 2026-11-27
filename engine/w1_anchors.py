"""W1 模板錨點轉換器（forex_reports C 族頁面）

把舊模板頁面轉成範本 A 骨架：
  - `<div class="news-section">`  → `<details class="card" id="sec-news" open>`
  - `<div class="events-section">` → `<details class="card" id="sec-events" open>`
  - 四個 h3 加唯一錨點：sec-charts / sec-pair / sec-conclusion / sec-summary
  - 插入 `details.card` CSS 兩行

**正文 byte 級零變**：只改 wrapper 開標籤行、對應 `</div>` 收口行、h3 開標籤行、CSS 插入行。
唔重生成、唔格式化、唔改內文。

規格來源：exchange/from_openclaw/20261127_1120_加急_W1剩餘頁今下午完成/
參考實作：exchange/from_zcode/20261127_0840_ZCODE_w_generator_patch_v1.1_indent修正/
          apply_generator_w1_patch.py 之 apply_w1_anchors()／patch_css()
參考產物：commit 534074b6c（11-26 晚報，2 details＋5 錨點零正文變）

設計取捨（比 generator patch 版嚴格）：
  1. generator 版靠 `if 'id="sec-news"' in html and 'id="sec-events"' in html: return html`
     做冪等判斷——但 11-26 晚報只有 sec-news 一個時會喺第二輪被當成已套而漏 sec-events。
     本版改為逐項檢查，任何一項未套都會補。
  2. 找不到任何 wrapper 時回 `changed=False` ＋ warning，唔扮成功（避免靜默無操作被當交付）。
  3. wrapper 收口靠 div 深度計數；配唔上就原樣保留 ＋ warning，絕不亂改。
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

# 只認整行 wrapper 開標籤（行首可縮排），避免誤中 CSS 或單行寫法
_WRAP_OPEN = re.compile(r'^(\s*)<div class="([a-z-]+-section)">\s*$')


def _convert_wrappers(lines: List[str], report: Dict) -> List[str]:
    out: List[str] = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = _WRAP_OPEN.match(line)
        if m and m.group(2) in WRAP_IDS:
            indent, cls = m.group(1), m.group(2)
            slug = WRAP_IDS[cls]
            if 'id="{0}"'.format(slug) in line:
                out.append(line)
                i += 1
                continue
            depth = len(re.findall(r"<div\b", line)) - len(re.findall(r"</div>", line))
            j, close_idx = i + 1, None
            while j < n:
                depth += (len(re.findall(r"<div\b", lines[j]))
                          - len(re.findall(r"</div>", lines[j])))
                if depth == 0:
                    close_idx = j
                    break
                j += 1
            if close_idx is None:
                out.append(line)
                report["warnings"].append(
                    "unmatched wrapper: {0} 冇對應 </div>，原樣保留".format(cls))
                i += 1
                continue
            out.append('{0}<details class="card" id="{1}" open>'.format(indent, slug))
            i += 1
            while i < close_idx:
                out.append(lines[i])
                i += 1
            out.append(lines[close_idx].replace("</div>", "</details>", 1))
            report["wrappers"].append({"from": cls, "to": slug})
            i += 1
            continue
        out.append(line)
        i += 1
    return out


def _convert_headings(lines: List[str], report: Dict) -> List[str]:
    out: List[str] = []
    for line in lines:
        new_line = line
        if "<h3" in line:
            for key, slug in H3_ANCHORS:
                if key not in line:
                    continue
                if 'id="{0}"'.format(slug) in line:
                    break                      # 已掛，原樣保留
                if "<h3>" in line:
                    new_line = line.replace("<h3>", '<h3 id="{0}">'.format(slug), 1)
                else:
                    new_line = re.sub(r"<h3\s", '<h3 id="{0}" '.format(slug), line, count=1)
                report["headings"].append({"key": key, "to": slug})
                break
        out.append(new_line)
    return out


def _insert_css(lines: List[str], report: Dict) -> List[str]:
    joined = "\n".join(lines)
    if "details.card {" in joined:
        report["css"] = "ALREADY"
        return lines
    for idx, line in enumerate(lines):
        if re.match(r"^\s*\.news-section\s*\{", line):
            lines = lines[:idx + 1] + CSS_SNIPPET.split("\n") + lines[idx + 1:]
            report["css"] = "OK（插於 .news-section 樣式後）"
            return lines
    for idx, line in enumerate(lines):
        if "<style>" in line:
            lines = lines[:idx + 1] + CSS_SNIPPET.split("\n") + lines[idx + 1:]
            report["css"] = "OK（插於 <style> 開頭）"
            return lines
    report["css"] = "SKIP：找不到 CSS 插入點"
    report["warnings"].append("css: 找不到插入點，頁面無 details.card 樣式")
    return lines


def apply_w1_anchors(html: str) -> Tuple[str, Dict]:
    """對一頁 HTML 套 W1 錨點。回 (新 HTML, report)。

    report 鍵：status / changed / wrappers / headings / css / warnings
    status: "ALREADY" | "APPLIED" | "NOOP"
    """
    report: Dict = {
        "status": "ALREADY",
        "changed": False,
        "wrappers": [],
        "headings": [],
        "css": "ALREADY",
        "warnings": [],
    }
    if not html:
        report["status"] = "NOOP"
        return html, report

    lines = html.split("\n")
    # C 族頁型必須兩個 wrapper 齊（原始或已轉換），否則拒改，唔准只改一半
    missing = []
    for cls, slug in WRAP_IDS.items():
        if ('<div class="{0}">'.format(cls) not in html
                and 'id="{0}"'.format(slug) not in html):
            missing.append(cls)
    if missing:
        report["warnings"].append(
            "缺 {0}：呢頁唔屬 C 族 W1 頁型（或 wrapper 唔喺獨立行），整頁拒改".format(
                "／".join(missing)))
        report["status"] = "NOOP"
        report["changed"] = False
        report["css"] = "SKIP：頁型唔合，唔插 CSS"
        return html, report

    # 先 wrapper（會改變行數），再 heading，最後 CSS（再插兩行）
    lines = _convert_wrappers(lines, report)
    lines = _convert_headings(lines, report)
    lines = _insert_css(lines, report)

    out = "\n".join(lines)
    if out == html:
        report["status"] = "ALREADY"
        if not report["wrappers"] and not report["headings"]:
            report["warnings"].append("no-op：此頁已套齊 W1 錨點")
        report["changed"] = False
        return html, report

    report["changed"] = True
    # 只補 CSS（wrappers/headings 都係空）＝錨點已齊但缺 details.card 樣式
    report["status"] = "CSS_ONLY" if not report["wrappers"] and not report["headings"] else "APPLIED"
    for cls in WRAP_IDS:
        if ('<div class="{0}">'.format(cls) in out
                and not any(w["from"] == cls for w in report["wrappers"])):
            report["warnings"].append(
                "{0}: 仍有未轉換嘅 wrapper（可能唔止一個或多行寫法）".format(cls))
    return out, report


def _iter_pages(reports_dir: str) -> List[str]:
    import glob
    import os
    return sorted(p for p in glob.glob(os.path.join(reports_dir, "*.html"))
                  if not p.endswith("index.html"))


def main(argv=None) -> int:
    """CLI：對 docs/forex_reports/*.html 套 W1 錨點。

    用法：
        python -m engine.w1_anchors --check     # 只報狀態，唔寫檔
        python -m engine.w1_anchors --apply     # 就地套用
        python -m engine.w1_anchors --apply --dir docs/forex_reports
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
    changed = 0
    for path in _iter_pages(args.dir):
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        out, rep = apply_w1_anchors(src)
        if args.apply and rep["changed"]:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(out)
            changed += 1
        rows.append({
            "page": path.replace("\\", "/").rsplit("/", 1)[-1],
            "status": rep["status"],
            "wrappers": len(rep["wrappers"]),
            "headings": [h["to"] for h in rep["headings"]],
            "css": rep["css"],
            "warnings": rep["warnings"],
        })
    print(json.dumps({"dir": args.dir, "applied": changed, "rows": rows},
                     ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
