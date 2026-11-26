#!/usr/bin/env python3
"""forex_report_postprocess.py — W1 規格後處理器（1158 派工：generator 修正三件套）

用法（generator 出報告後調用，或手動）:
  python3 forex_report_postprocess.py --file docs/forex_reports/forex_morning_report_YYYY-MM-DD.html
  python3 forex_report_postprocess.py --index            # 只重生 index.html
  python3 forex_report_postprocess.py --retention-dry    # 預覽 >7 日會刪邊啲檔
  python3 forex_report_postprocess.py --retention        # git rm >7 日舊報告
  python3 forex_report_postprocess.py --all              # 最新報告轉換＋index 重生＋retention-dry

職責（對應 1158 派工 §二）:
  1. W1 規格轉換：news/events-section div -> details.card(sec-news/sec-events)；
     h3 技術指標全景/個別貨幣對分析/新聞vs技術對比結論 -> id=sec-summary/sec-pair/sec-conclusion；
     裸 data-uri img 行 -> 置中 wrap。全部結構層，正文零變，可重入（冇 id 就加，有就跳過）。
  2. index.html 重生：const reports 陣列只列現存檔＋header 計數更新＋JS 解析器支援
     舊檔名（DATE_type.html）與新檔名（forex_{morning|evening}_report_DATE.html）雙格式。
  3. retention：git rm 檔名日期 >N 日（默認 7）嘅舊報告。
"""
import argparse, json, os, re, subprocess, sys
from datetime import datetime, timedelta
from itertools import zip_longest

H3_IDS = {
    "技術指標全景": "sec-summary",
    "個別貨幣對分析": "sec-pair",
    "新聞 vs 技術 對比結論": "sec-conclusion",
    "對比結論": "sec-conclusion",  # 舊變體兜底（先長後短匹配）
}
WRAP_IDS = {"news-section": "sec-news", "events-section": "sec-events"}
IMG_RE = re.compile(r'^<img src="data:image/')


def depth_delta(s):
    return len(re.findall(r"<div\b", s)) - len(re.findall(r"</div>", s))


def transform_w1(path):
    """W1 規格轉換（結構層零內容變，可重入）。回傳 JSON 驗證報告。"""
    lines = open(path, encoding="utf-8").read().split("\n")
    orig = list(lines)
    out, changes = [], []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r'^(\s*)<div class="([a-z-]+-section)">\s*$', line)
        if m and m.group(2) in WRAP_IDS:
            indent, cls = m.group(1), m.group(2)
            slug = WRAP_IDS[cls]
            depth, j, close_idx = 1, i + 1, None
            while j < n:
                depth += depth_delta(lines[j])
                if depth == 0:
                    close_idx = j
                    break
                j += 1
            if close_idx is None:
                sys.exit(f"ERROR: unmatched {cls} at line {i+1}")
            if not re.match(r"^\s*</div>\s*$", lines[close_idx]):
                sys.exit(f"ERROR: {cls} closing not bare </div>: {lines[close_idx]!r}")
            out.append(f'{indent}<details class="card" id="{slug}" open>')
            changes.append((i + 1, "open", cls, slug))
            i += 1
            while i < close_idx:
                out.append(lines[i]); i += 1
            out.append(lines[close_idx].replace("</div>", "</details>", 1))
            changes.append((close_idx + 1, "close", cls, slug))
            i += 1
            continue
        # h3 id（可重入：已有 id 跳過）
        if "<h3" in line and "id=" not in line:
            hit = None
            for key, slug in H3_IDS.items():
                if key in line:
                    hit = slug
                    break
            if hit and not any(c[3] == hit for c in changes):
                newline = line.replace("<h3>", f'<h3 id="{hit}">', 1) if "<h3>" in line else re.sub(r"<h3\s", f'<h3 id="{hit}" ', line, count=1)
                out.append(newline)
                changes.append((i + 1, "h3-id", "", hit))
                i += 1
                continue
        # 裸 data-uri img 行 -> 置中 wrap（可重入：已 wrap 行以 <div 開頭唔會命中）
        if IMG_RE.match(line.strip()):
            indent = line[: len(line) - len(line.lstrip())]
            body = line.strip()
            out.append(indent + '<div style="text-align:center;margin:10px 0">' + body.replace("<img ", '<img style="max-width:100%;border-radius:8px" ', 1) + "</div>")
            changes.append((i + 1, "img-wrap", "", ""))
            i += 1
            continue
        out.append(line)
        i += 1

    diff_pos = sum(1 for a, b in zip_longest(orig, out) if a != b)
    new_text = "\n".join(out)
    if "<h3id" in new_text:
        sys.exit("ERROR: malformed h3 output — aborting")
    # 零內容變驗證：變更位置外全部位元組相同
    changed_idx = {c[0] for c in changes}
    ok = all(a == b for k, (a, b) in enumerate(zip_longest(orig, out), 1) if k not in changed_idx)
    open(path + ".new", "w", encoding="utf-8").write(new_text)
    return json.dumps({
        "file": path,
        "changed_lines": len(changes),
        "diff_positions": diff_pos,
        "content_zero_change": ok,
        "detail": [f"L{c[0]} {c[1]} {c[2]}{('->' + c[3]) if c[3] else ''}" for c in changes],
    }, ensure_ascii=False, indent=1)


def apply(path):
    """跑 transform_w1 並把 .new 套用回原檔。"""
    report = transform_w1(path)
    os.replace(path + ".new", path)
    return report


DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")

def parse_name(fn):
    """雙格式檔名解析：回傳 (date, type) 或 (None, None)。"""
    m = DATE_RE.search(fn)
    if not m:
        return None, None
    date = m.group(1)
    if "morning_b" in fn:
        t = "morning_b"
    elif "morning" in fn:
        t = "morning"
    elif "evening" in fn:
        t = "evening"
    else:
        t = "daily"
    return date, t


def scan_reports(reports_dir):
    """掃目錄現存報告，回傳 [(date, type, filename)] 按 date desc、type 排序。"""
    rows = []
    for fn in os.listdir(reports_dir):
        if not fn.endswith(".html") or fn == "index.html":
            continue
        d, t = parse_name(fn)
        if d:
            rows.append((d, t, fn))
    rows.sort(key=lambda r: (r[0], r[1]), reverse=True)
    return rows


def regen_index(reports_dir, write=True):
    """index.html 重生：陣列只列現存檔＋計數＋JS 雙格式解析器。"""
    path = os.path.join(reports_dir, "index.html")
    text = open(path, encoding="utf-8").read()
    rows = scan_reports(reports_dir)
    arr_text = "const reports = [\n" + "".join(f"'{fn}',\n" for _, _, fn in rows) + "];"
    new_text, n1 = re.subn(r"const reports = \[.*?\];", arr_text, text, count=1, flags=re.S)
    if n1 != 1:
        sys.exit("ERROR: reports array anchor not found in index.html")
    new_text = re.sub(r"共 \d+ 份", f"共 {len(rows)} 份", new_text)
    old_parser = """  const parts = r.replace('.html','').split('_');
  const date = parts[0];
  const type = parts[1] || 'daily';"""
    new_parser = """  const date = (r.match(/(\\d{4}-\\d{2}-\\d{2})/) || [])[0] || r.replace('.html','');
  let type = 'daily';
  if (r.indexOf('morning_b') >= 0) type = 'morning_b';
  else if (r.indexOf('morning') >= 0) type = 'morning';
  else if (r.indexOf('evening') >= 0) type = 'evening';"""
    if old_parser in new_text:
        new_text = new_text.replace(old_parser, new_parser, 1)
    new_text = re.sub(r"列表由 scan 重建（[^）]*）", "列表由 forex_report_postprocess.py 重生（每次出報告自動更新）", new_text)
    if write:
        open(path, "w", encoding="utf-8").write(new_text)
    return len(rows)


def repo_root():
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 else None


def retention(reports_dir, days=7, dry=True):
    """>N 日舊報告 git rm（dry=True 只列唔刪）。"""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    victims = [fn for d, _, fn in scan_reports(reports_dir) if d < cutoff]
    if dry:
        return {"cutoff": cutoff, "would_remove": victims}
    if victims:
        root = repo_root()
        full = [os.path.join(reports_dir, v) for v in victims]
        subprocess.run(["git", "-C", root, "rm", "--quiet"] + full, check=True)
    return {"cutoff": cutoff, "removed": victims}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="單檔 W1 轉換")
    ap.add_argument("--index", action="store_true", help="重生 index.html")
    ap.add_argument("--retention", action="store_true", help="git rm >7 日舊報告")
    ap.add_argument("--retention-dry", action="store_true", help="retention 預覽")
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--all", action="store_true", help="目錄全部報告轉換＋index 重生")
    args = ap.parse_args()
    reports_dir = os.path.join(repo_root() or ".", "docs", "forex_reports")

    if args.file:
        print(apply(args.file))
    if args.all:
        for d, _, fn in scan_reports(reports_dir):
            print(apply(os.path.join(reports_dir, fn)))
    if args.index:
        n = regen_index(reports_dir)
        print(f"index.html regenerated: {n} reports listed")
    if args.retention_dry:
        print(json.dumps(retention(reports_dir, args.days, dry=True), ensure_ascii=False, indent=1))
    if args.retention:
        print(json.dumps(retention(reports_dir, args.days, dry=False), ensure_ascii=False, indent=1))
    if not any([args.file, args.index, args.retention, args.retention_dry, args.all]):
        ap.print_help()


if __name__ == "__main__":
    main()
