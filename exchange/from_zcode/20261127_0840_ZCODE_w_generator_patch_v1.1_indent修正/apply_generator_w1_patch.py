#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
apply_generator_w1_patch.py — forex_combined_report.py 修正補丁（老闆 11-26 11:53 裁決落地）

提供: ZCODE_w（CODE lane）→ OpenClaw（數據 lane，generator 正本持有人）
用法: OC 側 workspace 根目錄跑
    python3 apply_generator_w1_patch.py [path/to/forex_combined_report.py]
    （預設自動找 ~/.openclaw/workspace/scripts/forex_combined_report.py）

補丁內容（三項，取代 W2 全線，對應 1158 派工信 §二）：
  A. W1 規格後處理函數 apply_w1_anchors() —— 生成 HTML 末端統一轉換：
     news-section/events-section wrapper div → <details class="card" id="sec-news/sec-events" open>
     h3 插入唯一錨點：技術指標全景→sec-summary、個別貨幣對分析→sec-pair、
       對比結論→sec-conclusion、📊 Charts→sec-charts（新設，請 OC 備案）
     正文內容零變（與 ZCODE_w W2b 38 頁驗收全綠嘅轉換器同構，冪等）
  B. index.html 自動重生 regenerate_index() —— 每次出報告後掃現存頁重列，
     消除 218 已刪頁死連結（相容新舊兩種檔名格式）
  C. 自動 retention apply_retention(days=7) —— 刪 >7 日舊報告（git rm 留底可還原）

補丁特性：
  - 冪等：重複跑輸出 ALREADY，不會重複套
  - 錨點寬鬆匹配：段函數行號漂移不受影響；找不到錨輸出 SKIP 列原因
  - 套用後自驗：五項 grep＋py_compile 語法檢查，任何失敗 exit 1

設計: 2026-11-26 ZCODE_w，死線 17:00 前（1158 派工信 §二.4）
"""
import json
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_CANDIDATES = [
    Path.home() / ".openclaw" / "workspace" / "scripts" / "forex_combined_report.py",
    Path.home() / "workspace" / "scripts" / "forex_combined_report.py",
    Path("scripts/forex_combined_report.py"),
    Path("forex_combined_report.py"),
]

BLOCK_HEADER = "import re, json, subprocess\nfrom datetime import datetime, timedelta\nfrom pathlib import Path\n"

W1_FUNC_SOURCE = r'''
# === W1 anchor patch 2026-11-26 (ZCODE_w) — begin ===
def apply_w1_anchors(html):
    """報告末端後處理（W1 規格，老闆 2026-11-26 11:53 裁決）：
    1. news-section / events-section wrapper div → <details class="card" id="sec-…" open>
    2. h3 插入唯一錨點 sec-summary / sec-pair / sec-conclusion / sec-charts
    正文內容零變；已轉換頁再跑無變化（冪等）。"""
    if 'id="sec-news"' in html and 'id="sec-events"' in html:
        return html  # already patched
    WRAP_IDS = {"news-section": "sec-news", "events-section": "sec-events"}
    H3_IDS = {
        "技術指標全景": "sec-summary",
        "個別貨幣對分析": "sec-pair",
        "對比結論": "sec-conclusion",
        "\U0001F4CA Charts": "sec-charts",
    }
    lines = html.split("\n")
    out = []
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = re.match(r'^(\s*)<div class="([a-z-]+-section)">\s*$', line)
        if m and m.group(2) in WRAP_IDS:
            indent, cls = m.group(1), m.group(2)
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
                out.append(line)  # unmatched: keep as-is, never corrupt
                i += 1
                continue
            out.append('{0}<details class="card" id="{1}" open>'.format(indent, WRAP_IDS[cls]))
            i += 1
            while i < close_idx:
                out.append(lines[i])
                i += 1
            out.append(lines[close_idx].replace("</div>", "</details>", 1))
            i += 1
            continue
        replaced = False
        for key, slug in H3_IDS.items():
            if key in line and "<h3" in line and 'id="{0}"'.format(slug) not in line:
                if "<h3>" in line:
                    out.append(line.replace("<h3>", '<h3 id="{0}">'.format(slug), 1))
                else:
                    out.append(re.sub(r"<h3\s", '<h3 id="{0}" '.format(slug), line, count=1))
                replaced = True
                break
        if not replaced:
            out.append(line)
        i += 1
    return "\n".join(out)
# === W1 anchor patch 2026-11-26 (ZCODE_w) — end ===
'''

INDEX_FUNC_SOURCE = r'''
# === index regenerate patch 2026-11-26 (ZCODE_w) — begin ===
def regenerate_index(reports_dir=None):
    """重掃 docs/forex_reports/ 現存報告頁，重寫 index.html reports 陣列，
    只列現存頁（消除已刪頁死連結，1158 派工信 §二.2）。
    相容兩種檔名：forex_morning_report_YYYY-MM-DD.html（新）
    與 YYYY-MM-DD_morning.html（舊短格式存檔）。"""
    rdir = Path(reports_dir) if reports_dir else Path("docs/forex_reports")
    if not rdir.is_dir():
        return "SKIP regenerate_index: {0} 不存在".format(rdir)
    entries = []
    pat_new = re.compile(r"^forex_(morning_b|morning|evening)_report_(\d{4}-\d{2}-\d{2})\.html$")
    pat_old = re.compile(r"^(\d{4}-\d{2}-\d{2})_(morning|evening|morning_b)\.html$")
    for f in sorted(rdir.glob("*.html")):
        if f.name == "index.html":
            continue
        m = pat_new.match(f.name) or pat_old.match(f.name)
        if m:
            entries.append(f.name)
    entries.sort(reverse=True)
    arr = "\n".join("'{0}',".format(e) for e in entries)
    parse_js = (
        "reports.forEach(r => {\n"
        "  let date, type;\n"
        "  let m = r.match(/^forex_(morning_b|morning|evening)_report_(\\d{4}-\\d{2}-\\d{2})\\.html$/);\n"
        "  if (m) { type = m[1]; date = m[2]; }\n"
        "  else { const parts = r.replace('.html','').split('_'); date = parts[0]; type = parts[1] || 'daily'; }\n"
        "  if(!dates[date]) dates[date] = {};\n"
        "  dates[date][type] = r;\n"
        "});"
    )
    idx_path = rdir / "index.html"
    if not idx_path.exists():
        return "SKIP regenerate_index: index.html 不存在"
    text = idx_path.read_text(encoding="utf-8")
    new_text, n_arr = re.subn(r"const reports = \[.*?\];",
                              "const reports = [\n{0}\n];".format(arr),
                              text, count=1, flags=re.S)
    if n_arr == 0:
        return "SKIP regenerate_index: index.html 無 const reports 陣列錨點（模板已變，需人工）"
    new_text, n_js = re.subn(r"reports\.forEach\(r => \{.*?\}\);",
                             parse_js.replace("\\", "\\\\"),
                             new_text, count=1, flags=re.S)
    idx_path.write_text(new_text, encoding="utf-8")
    return "OK index.html 重生：{0} 頁入列（解析邏輯更新 {1} 處）".format(len(entries), n_js)
# === index regenerate patch 2026-11-26 (ZCODE_w) — end ===
'''

RETENTION_FUNC_SOURCE = r'''
# === retention patch 2026-11-26 (ZCODE_w) — begin ===
def apply_retention(days=7, reports_dir=None):
    """刪除超過 N 日嘅舊報告（預設 7 日，1158 派工信 §二.3＋§一.2 保留近 7 日口徑）。
    git 內自動 git rm（留底可還原）；非 git 環境 fallback os.remove。"""
    rdir = Path(reports_dir) if reports_dir else Path("docs/forex_reports")
    if not rdir.is_dir():
        return "SKIP apply_retention: 目錄不存在"
    cutoff = (datetime.now() - timedelta(days=days)).date()
    pat = re.compile(r"(\d{4}-\d{2}-\d{2})")
    removed = []
    for f in sorted(rdir.glob("*.html")):
        if f.name == "index.html":
            continue
        m = pat.search(f.name)
        if not m:
            continue
        try:
            fdate = datetime.strptime(m.group(1), "%Y-%m-%d").date()
        except ValueError:
            continue
        if fdate < cutoff:
            in_git = subprocess.run(
                ["git", "ls-files", "--error-unmatch", str(f)],
                capture_output=True).returncode == 0
            if in_git:
                r = subprocess.run(["git", "rm", "-q", str(f)], capture_output=True)
                if r.returncode == 0:
                    removed.append(f.name)
            else:
                f.unlink()
                removed.append(f.name)
    tail = "…" if len(removed) > 5 else ""
    return "OK retention：刪 {0} 頁（> {1} 日）{2}{3}".format(
        len(removed), days, removed[:5], tail)
# === retention patch 2026-11-26 (ZCODE_w) — end ===
'''

CSS_SNIPPET = (
    "details.card { background: #161b22; border-radius: 8px; padding: 12px; "
    "margin-bottom: 14px; }\n"
    "details.card > summary { cursor: pointer; }"
)

CALL_BLOCK = (
    "\n    # === W1 call patch 2026-11-26 (ZCODE_w) — begin ===\n"
    "    html = apply_w1_anchors(html)\n"
    "    try:\n"
    "        print(apply_retention())\n"
    "        print(regenerate_index())\n"
    "    except Exception as _e:\n"
    "        print('retention/index 非致命錯誤: %s' % _e)\n"
    "    # === W1 call patch 2026-11-26 (ZCODE_w) — end ==="
)


def find_target():
    if len(sys.argv) > 1:
        p = Path(sys.argv[1])
        if p.is_file():
            return p
        sys.exit("ERROR: 指定檔案不存在: {0}".format(p))
    for p in DEFAULT_CANDIDATES:
        if p.is_file():
            return p
    hits = list(Path(".").glob("**/forex_combined_report.py"))
    if len(hits) == 1:
        return hits[0]
    sys.exit("ERROR: 找不到 forex_combined_report.py，請以參數指定路徑")


def patch_css(text):
    if "details.card {" in text:
        return text, "ALREADY"
    m = re.search(r"^(\s*\.news-section\s*\{[^}]*\})\s*$", text, re.M)
    if m:
        return (text.replace(m.group(0), m.group(0) + "\n" + CSS_SNIPPET, 1),
                "OK（插於 .news-section 樣式後）")
    if "<style>" in text:
        return text.replace("<style>", "<style>\n" + CSS_SNIPPET, 1), "OK（插於 <style> 開頭）"
    return text, "SKIP：找不到 CSS 插入點"


def patch_call_site(text):
    if "W1 call patch 2026-11-26 (ZCODE_w)" in text:
        return text, "ALREADY"
    # 錨點候選（寬鬆）：html 骨架/組裝賦值 → 之後第一個 return 或寫出點之前插入
    for pat, label in [
        (r'^\s*html\s*=\s*f?"""', 'html = f-string 骨架賦值'),
        (r'^\s*html\s*=\s*build_', 'html = build_… 賦值'),
        (r'^\s*html\s*=\s*_?build_page', 'html = build_page 賦值'),
    ]:
        m = re.search(pat, text, re.M)
        if m:
            idx = text[:m.end()].count("\n")
            lines = text.split("\n")
            for j in range(idx + 1, len(lines)):
                if re.match(r"^\s*(return\b|Path\(.*\)\.write|open\(.*\)\.?write|f\.write|out\.write)", lines[j]):
                    # v1.1 修正（OC 1825 回饋）：CALL_BLOCK 基準縮排 4，插入前按寫出點實際縮排層級
                    # reindent——with/try 內（縮排 8 等）唔會再 IndentationError
                    ti = len(lines[j]) - len(lines[j].lstrip(" "))
                    delta = ti - 4
                    block_lines = []
                    for bl in CALL_BLOCK.split("\n"):
                        if bl.strip() == "":
                            block_lines.append(bl)
                        else:
                            cur = len(bl) - len(bl.lstrip(" "))
                            block_lines.append(" " * max(cur + delta, 0) + bl.lstrip(" "))
                    lines[j:j] = block_lines
                    return "\n".join(lines), "OK（{0} 之後 L{1} 寫出/return 前插入，indent 基準 4→{2}）".format(label, j + 1, ti)
    return text, "SKIP：找不到 html 骨架→寫出錨點（需人工在 save 前加：html = apply_w1_anchors(html)；apply_retention()；regenerate_index()）"


def verify(text):
    return [
        ("apply_w1_anchors 定義", "def apply_w1_anchors" in text),
        ("regenerate_index 定義", "def regenerate_index" in text),
        ("apply_retention 定義", "def apply_retention" in text),
        ("W1 調用點", "html = apply_w1_anchors(html)" in text),
        ("details.card CSS", "details.card {" in text),
    ]


def main():
    target = find_target()
    src = target.read_text(encoding="utf-8")
    orig = src
    report = {"file": str(target), "bytes_before": len(src), "steps": {}}

    # 1) 函數塊插入（錨：頂部 import 區之後）
    if "W1 anchor patch 2026-11-26" in src:
        report["steps"]["插入函數塊"] = "ALREADY"
    else:
        m_imp = None
        for mm in re.finditer(r"^((?:from \S+ import [^\n]+|import [^\n]+)\n)+", src, re.M):
            m_imp = mm
        if m_imp is None:
            report["steps"]["插入函數塊"] = "SKIP：找不到 import 區"
        else:
            ins_at = m_imp.end()
            block = BLOCK_HEADER + W1_FUNC_SOURCE + "\n" + INDEX_FUNC_SOURCE + "\n" + RETENTION_FUNC_SOURCE
            src = src[:ins_at] + block + src[ins_at:]
            report["steps"]["插入函數塊"] = "OK（插入於 import 區後）"

    # 2) CSS
    src, r_css = patch_css(src)
    report["steps"]["CSS details.card"] = r_css

    # 3) 調用點
    src, r_call = patch_call_site(src)
    report["steps"]["調用點"] = r_call

    if src != orig:
        target.write_text(src, encoding="utf-8")
        report["written"] = True
        report["bytes_after"] = len(src)
    else:
        report["written"] = False

    # 4) 自驗
    final = target.read_text(encoding="utf-8")
    report["verify"] = {name: ok for name, ok in verify(final)}
    try:
        subprocess.run([sys.executable, "-m", "py_compile", str(target)],
                       check=True, capture_output=True)
        report["py_compile"] = "PASS"
    except subprocess.CalledProcessError as e:
        report["py_compile"] = "FAIL: " + e.stderr.decode(errors="replace")[:300]

    print(json.dumps(report, ensure_ascii=False, indent=1))
    if report["py_compile"] != "PASS" or not all(report["verify"].values()):
        sys.exit(1)


if __name__ == "__main__":
    main()
