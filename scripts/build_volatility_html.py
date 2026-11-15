#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
波幅表網頁生成器（R1 Excel 版）
================================
由老闆 2026-11-15 提供嘅 Volatility TableR1.xlsx 生成 docs/volatility.html。

Excel 結構（實測）：
  - A 欄：負責人（每個貨幣組首行出現一次，其餘空）
  - B 欄：CCY (band)——同一貨幣三行：(80%) / (15%) / (5%) 三檔區間
  - C 欄起：40 欄「年份(時段)」區間值（例如 "1-35"，pips）
  - 已知髒數據照錄（trim 空白）：例如 "395=632"、"52+152"、"83103"、"331--1123"、"146-286."

用法：
  python scripts/build_volatility_html.py --xlsx "uploads/Volatility TableR1.xlsx"
  python scripts/build_volatility_html.py --xlsx <path> --out docs/volatility.html

輸出：docs/volatility.html（跟 docs/volatility.html 原有 chrome：sidebar＋主題切換＋波幅表配色）
只讀 Excel 寫 HTML，唔掂任何評分／排名代碼。
"""

import argparse
import html
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

HKT = timezone(timedelta(hours=8))


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def load_rows(xlsx_path: str):
    """讀 Excel，回傳 (headers, groups)；groups = [{'owner':str|None,'sym':str,'band':str,'values':[...40]}]。"""
    import openpyxl
    wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb.active
    headers = [str(ws.cell(row=1, column=c).value or "").strip() for c in range(2, ws.max_column + 1)]
    headers = headers[1:]  # B 欄係 'CCY'，真正數據欄由 C 起
    n_cols = len(headers)

    groups, pending_owner = [], None
    for r in range(2, ws.max_row + 1):
        a = ws.cell(row=r, column=1).value
        b = ws.cell(row=r, column=2).value
        a_txt = str(a).strip() if a is not None else ""
        b_txt = str(b).strip() if b is not None else ""
        if a_txt:
            pending_owner = a_txt
        if not b_txt:
            continue
        m = re.match(r"^(.*?)\s*\((\d+%)\)$", b_txt)
        sym, band = (m.group(1), m.group(2)) if m else (b_txt, "")
        values = []
        for c in range(3, 3 + n_cols):
            v = ws.cell(row=r, column=c).value
            values.append("" if v is None else str(v).strip())
        groups.append({"owner": pending_owner, "sym": sym, "band": band, "values": values})
    return headers, groups


def column_thresholds(groups: list, n_cols: int) -> list:
    """逐欄計上限值嘅 1/3、2/3 分位，做綠黃紅熱度色（跟波幅表傳統）。"""
    uppers = [[] for _ in range(n_cols)]
    num_re = re.compile(r"\d+(?:\.\d+)?")
    for g in groups:
        for i, v in enumerate(g["values"]):
            nums = num_re.findall(v)
            if nums:
                uppers[i].append(float(nums[-1]))
    out = []
    for arr in uppers:
        if not arr:
            out.append((None, None))
            continue
        arr.sort()
        q1, q2 = arr[len(arr) // 3], arr[2 * len(arr) // 3]
        out.append((q1, q2))
    return out


def heat_class(v: str, th) -> str:
    if not th or th[0] is None:
        return ""
    nums = re.findall(r"\d+(?:\.\d+)?", v)
    if not nums:
        return ""
    upper = float(nums[-1])
    if upper <= th[0]:
        return "g"
    if upper <= th[1]:
        return "w"
    return "r"


PAGE_TEMPLATE = """<!DOCTYPE html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>📊 波幅表</title>
<style>
:root{--font-main:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Microsoft JhengHei',sans-serif;--radius:8px}
[data-theme="dark"]{--bg:#0F1520;--bg-card:#161E2E;--bg-hover:#1C2638;--text:#E6EDF5;--text2:#A8B4C4;--primary:#5CA8FF;--accent:#38BDF8;--green:#22C55E;--red:#EF4444;--yellow:#EAB308;--border:#2A3650}
[data-theme="light"]{--bg:#F1F5F9;--bg-card:#ffffff;--bg-hover:#E2E8F0;--text:#1E293B;--text2:#64748B;--primary:#2563EB;--accent:#0EA5E9;--green:#16A34A;--red:#DC2626;--yellow:#CA8A04;--border:#CBD5E1}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--font-main);background:var(--bg);color:var(--text);padding:12px;font-size:13px}
h1{font-size:1.3em;margin-bottom:4px;color:var(--primary)}
.sub{color:var(--text2);font-size:0.85em;margin-bottom:12px}
.info-tip:hover .info-tip-text{display:block}
.legend{display:flex;gap:14px;flex-wrap:wrap;margin-bottom:12px;font-size:0.78em;color:var(--text2)}
.legend span{display:flex;align-items:center;gap:4px}
.legend .dot{width:8px;height:8px;border-radius:50%}
table{border-collapse:collapse}
th{background:var(--bg-card);padding:5px 6px;text-align:center;border-bottom:2px solid var(--primary);color:var(--primary);font-size:0.72em;white-space:nowrap}
td{padding:3px 5px;text-align:center;border-bottom:1px solid var(--border);font-size:0.8em;white-space:nowrap}
tr:hover{background:var(--bg-card)}
tr.grp-end td{border-bottom:2px solid var(--primary)}
.own{font-weight:bold;color:var(--accent);text-align:left!important;padding-left:10px;white-space:nowrap;vertical-align:top;border-right:1px solid var(--border)}
.sym{text-align:left!important;white-space:nowrap;font-family:'SF Mono',Consolas,monospace}
.b15 .sym,.b5 .sym{color:var(--text2)}
.b5 td{opacity:.85}
.g{color:var(--green)}.r{color:var(--red)}.w{color:var(--yellow)}.m{font-family:'SF Mono',Consolas,monospace}
.footer{text-align:center;color:var(--text2);font-size:0.7em;margin-top:20px;padding-top:10px;border-top:1px solid var(--bg-card)}
@media(max-width:700px){table{font-size:0.6em}td,th{padding:2px 2px}}
</style>
<script>
(function(){
  const saved=localStorage.getItem('tsa-theme');
  const t=saved||'dark';
  document.documentElement.setAttribute('data-theme',t);
  document.addEventListener('DOMContentLoaded',function(){
    const btn=document.getElementById('theme-toggle');
    if(btn)btn.textContent=t==='dark'?'☀️':'🌙';
  });
})();
function toggleTheme(){
  const cur=document.documentElement.getAttribute('data-theme');
  const next=cur==='dark'?'light':'dark';
  document.documentElement.setAttribute('data-theme',next);
  localStorage.setItem('tsa-theme',next);
  const btn=document.getElementById('theme-toggle');
  if(btn)btn.textContent=next==='dark'?'☀️':'🌙';
}
</script>
<link rel="stylesheet" href="sidebar.css">
<link rel="stylesheet" href="tsa_tokens.css">
</head><body>
<div id="sidebar-container"></div>
<h1>📊 波幅表</h1>
<p class="sub">R1 版｜每個貨幣三檔區間（80% / 15% / 5%）× 年份(時段)｜Range = pips｜數據來源：__SOURCE_NAME__（負責人標記）</p>
<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;font-size:0.82em;color:var(--text2)"><span>__GEN_TIME__</span><span class="info-tip" style="position:relative;display:inline-flex;cursor:pointer"><span style="width:18px;height:18px;border-radius:50%;background:var(--bg-hover);border:1px solid var(--border);display:inline-flex;align-items:center;justify-content:center;font-size:12px;font-style:italic;color:var(--text2)">i</span><span class="info-tip-text" style="display:none;position:absolute;top:24px;left:0;background:var(--bg-card);border:1px solid var(--border);border-radius:8px;padding:10px 14px;font-size:0.82em;line-height:1.6;z-index:50;box-shadow:0 4px 16px rgba(0,0,0,0.3);color:var(--text);max-width:640px;white-space:normal">每個貨幣三行：80% 檔＝大多數交易嘅波幅區間；15%／5% 檔＝漸大波幅。<br>顏色＝每欄上限值三分位熱度：__LEGEND_COLORS__<br>髒數據照錄（如 395=632、52+152、83103、331--1123、146-286.），未經修改。重跑：python scripts/build_volatility_html.py --xlsx "uploads/__SOURCE_NAME__"</span></span></div>
<div class="legend">
<span><span class="dot" style="background:var(--green)"></span>該欄細波幅</span>
<span><span class="dot" style="background:var(--yellow)"></span>中等</span>
<span><span class="dot" style="background:var(--red)"></span>該欄大波幅</span>
<span class="m">三行一組：80% → 15% → 5%</span></div>
<div style="overflow-x:auto">
<table>
<thead><tr><th>負責人</th><th>CCY</th>__HEADER_CELLS__</tr></thead>
<tbody>
__BODY_ROWS__
</tbody>
</table>
</div>
<div class="footer">🦀 丁蟹分析 | 波幅表 R1｜生成自 __SOURCE_NAME__｜__GEN_TIME__｜python scripts/build_volatility_html.py</div>
<script src="sidebar.js"></script>
</body></html>
"""


def build_html(headers: list, groups: list, source_name: str) -> str:
    ths = column_thresholds(groups, len(headers))
    header_cells = "".join(f"<th>{esc(h)}</th>" for h in headers)

    rows, group_idx = [], 0
    n = len(groups)
    for gi, g in enumerate(groups):
        is_group_start = (gi % 3 == 0) or (g["owner"] is not None)
        is_group_end = (gi % 3 == 2) or (gi == n - 1)
        band_cls = {"80%": "b80", "15%": "b15", "5%": "b5"}.get(g["band"], "")
        cls = []
        if band_cls:
            cls.append(band_cls)
        if is_group_end:
            cls.append("grp-end")
        row_cls = f' class="{" ".join(cls)}"' if cls else ""
        if is_group_start and g["owner"]:
            rows.append(f'<tr{row_cls}><td class="own" rowspan="3">{esc(g["owner"])}</td>')
        else:
            rows.append(f"<tr{row_cls}><td></td>")
        rows.append(f'<td class="sym">{esc(g["sym"])}{" (" + esc(g["band"]) + ")" if g["band"] else ""}</td>')
        for i, v in enumerate(g["values"]):
            if not v:
                rows.append("<td></td>")
            else:
                c = heat_class(v, ths[i])
                rows.append(f'<td class="m {c}">{esc(v)}</td>')
        rows.append("</tr>")
        group_idx += 1

    now = datetime.now(HKT).strftime("%Y-%m-%d %H:%M HKT")
    page = PAGE_TEMPLATE
    page = page.replace("__SOURCE_NAME__", esc(source_name))
    page = page.replace("__GEN_TIME__", esc(now))
    page = page.replace("__HEADER_CELLS__", header_cells)
    page = page.replace("__BODY_ROWS__", "\n".join(rows))
    page = page.replace("__LEGEND_COLORS__", '<span style="color:var(--green)">●</span> 細 <span style="color:var(--yellow)">●</span> 中 <span style="color:var(--red)">●</span> 大')
    return page


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="由 Volatility Excel 生成波幅表網頁（R1 版）")
    ap.add_argument("--xlsx", default=os.path.join("uploads", "Volatility TableR1.xlsx"),
                    help="來源 Excel（預設 uploads/Volatility TableR1.xlsx）")
    ap.add_argument("--out", default=os.path.join("docs", "volatility.html"), help="輸出 HTML")
    args = ap.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    xlsx_path = args.xlsx if os.path.isabs(args.xlsx) else os.path.join(repo_root, args.xlsx)
    out_html = args.out if os.path.isabs(args.out) else os.path.join(repo_root, args.out)

    headers, groups = load_rows(xlsx_path)
    print(f"[讀取] {args.xlsx}｜欄 {len(headers)}｜組 {len(groups)}（即 {len(groups) // 3} 個貨幣 × 3 檔）")

    source_name = os.path.basename(xlsx_path)
    html_text = build_html(headers, groups, source_name)
    os.makedirs(os.path.dirname(out_html), exist_ok=True)
    with open(out_html, "w", encoding="utf-8", newline="\n") as f:
        f.write(html_text)

    owners = sorted({g["owner"] for g in groups if g["owner"]})
    syms = sorted(dict.fromkeys(g["sym"] for g in groups))
    print(f"[輸出] {os.path.relpath(out_html, repo_root)}｜負責人 {len(owners)} 位：{', '.join(owners)}")
    print(f"[貨幣] {len(syms)} 個：{', '.join(syms)}")
    print("✓ 完成")
    return 0


if __name__ == "__main__":
    sys.exit(main())
