"""HTML report for one signal, with a date-range selector.

Two constraints shaped this file:

**No external assets.** The page must open from a file:// path and render with
no network, because it is delivered as a single artifact and reviewed offline.
So the CSS is inline and there is no CDN, no font fetch, no chart library.

**The date selector must not need a server.** Every segment is rendered into the
page with its data attributes, and the selector only toggles visibility. That
keeps "show me 2026-01 onward" a client-side filter rather than a re-render,
which matters because the numbers the reader is comparing must not shift
under them while they click.

Text follows the house rule for shipped pages: English or Traditional Chinese
only. Section headings here are English so the file can be diffed and grepped
alongside the other engine output; the labels a person actually reads on screen
are Traditional Chinese.
"""

from __future__ import annotations

import html
import os
from typing import Any, Dict, List, Optional, Sequence

from .scan import SignalRecord

CSS = """
:root{--ink:#1c2530;--muted:#667686;--line:#dde5ec;--bg:#f7f9fb;--card:#fff;
--ok:#1f7a45;--warn:#9a6400;--bad:#ad2323;--accent:#245e8f}
*{box-sizing:border-box}
body{margin:0;padding:24px;background:var(--bg);color:var(--ink);
font:15px/1.55 -apple-system,"Segoe UI","Noto Sans TC","Microsoft JhengHei",sans-serif}
h1{font-size:22px;margin:0 0 4px}
h2{font-size:17px;margin:28px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
.sub{color:var(--muted);font-size:13px;margin-bottom:20px}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;
padding:16px 18px;margin-bottom:16px}
.kpis{display:flex;flex-wrap:wrap;gap:10px}
.kpi{flex:1 1 128px;background:var(--card);border:1px solid var(--line);
border-radius:8px;padding:12px 14px}
.kpi .k{color:var(--muted);font-size:12px;letter-spacing:.02em}
.kpi .v{font-size:20px;font-weight:600;font-variant-numeric:tabular-nums;margin-top:2px}
table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:14px}
th,td{padding:7px 10px;text-align:right;border-bottom:1px solid var(--line)}
th:first-child,td:first-child{text-align:left}
th{background:#eef3f7;font-weight:600;font-size:13px;color:#39485a}
tbody tr:hover{background:#f3f7fa}
tr.thin td{color:var(--muted);font-style:italic}
.controls{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-bottom:12px}
.controls label{font-size:13px;color:var(--muted)}
select,input[type=month]{padding:5px 8px;border:1px solid var(--line);border-radius:5px;
background:#fff;font-size:13px;color:var(--ink)}
.pill{display:inline-block;padding:2px 9px;border-radius:999px;font-size:12px;
font-weight:600;border:1px solid transparent}
.p-ok{background:#e6f4ec;color:var(--ok);border-color:#bfe0cc}
.p-warn{background:#fdf3e0;color:var(--warn);border-color:#f0dcb4}
.p-bad{background:#fbe9e9;color:var(--bad);border-color:#f0c9c9}
ul.issues{margin:8px 0 0;padding-left:20px}
ul.issues li{margin:3px 0}
code{background:#eef3f7;padding:1px 5px;border-radius:4px;font-size:13px}
footer{color:var(--muted);font-size:12px;margin-top:28px}
"""

SCRIPT = """
(function(){
  var from=document.getElementById('from'),to=document.getElementById('to'),
      rows=document.querySelectorAll('#segbody tr'),shown=document.getElementById('shown');
  function apply(){
    var a=from.value||'0000-00',b=to.value||'9999-99',n=0;
    rows.forEach(function(r){
      var m=r.getAttribute('data-month')||'';
      var ok=(!a||m>=a)&&(!b||m<=b);
      r.style.display=ok?'':'none';
      if(ok)n++;
    });
    if(shown)shown.textContent=n;
  }
  if(from)from.addEventListener('change',apply);
  if(to)to.addEventListener('change',apply);
  if(from)from.addEventListener('input',apply);
  if(to)to.addEventListener('input',apply);
  apply();
})();
"""


def _e(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _money(v: float) -> str:
    return f"{v:,.2f}"


def _pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def _quality_badge(rec: SignalRecord) -> str:
    if not rec.quality:
        return '<span class="pill p-warn">未檢查</span>'
    if rec.quality.get("ok"):
        return '<span class="pill p-ok">通過</span>'
    sev = {i.get("severity") for i in rec.quality.get("issues", [])}
    if "error" in sev:
        return '<span class="pill p-bad">有錯誤</span>'
    return '<span class="pill p-warn">有警告</span>'


def _segment_rows(rec: SignalRecord) -> str:
    out: List[str] = []
    for s in rec.segments:
        cls = ' class="thin"' if s.get("thin") else ""
        out.append(
            f'<tr{cls} data-month="{_e(s["label"])}">'
            f'<td>{_e(s["label"])}</td>'
            f'<td>{s["trades"]}</td>'
            f'<td>{_pct(s["win_rate"])}</td>'
            f'<td>{_money(s["net_profit"])}</td>'
            f'<td>{s["net_pips"]:.1f}</td>'
            f'<td>{s["worst_mae_pips"]:.1f}</td>'
            f'<td>{s["symbols"]}</td>'
            f'<td>{s["max_layer"]}</td>'
            f"</tr>"
        )
    return "\n".join(out)


def _issue_items(rec: SignalRecord) -> str:
    issues = (rec.quality or {}).get("issues") or []
    if not issues:
        return "<li>無發現問題。</li>"
    return "\n".join(
        f'<li><code>{_e(i.get("code"))}</code> {_e(i.get("message"))}</li>'
        for i in issues
    )


def _layer_rows(model: Dict[str, Any]) -> str:
    counts = model.get("counts") or {}
    if not counts:
        return '<tr><td colspan="2">無分層數據</td></tr>'
    return "\n".join(
        f'<tr><td>L{k}</td><td>{v}</td></tr>' for k, v in counts.items()
    )


def render(rec: SignalRecord, title: Optional[str] = None) -> str:
    """Render one :class:`SignalRecord` to a standalone HTML document."""
    name = title or f"Signal {rec.signal_id}"
    span = f"{_e(rec.first_trade)} → {_e(rec.last_trade)}" if rec.first_trade else "—"

    drift = rec.drift or {}
    drift_html = (
        f'<div class="card"><strong>漂移</strong>：由 <code>{_e(drift.get("from"))}</code> '
        f'到 <code>{_e(drift.get("to"))}</code>，勝率變化 '
        f'{drift.get("win_rate_delta", 0) * 100:+.1f} 個百分點，'
        f'每筆平均利潤變化 {drift.get("profit_per_trade_delta", 0):+.2f}。</div>'
        if drift else
        '<div class="card">未夠兩個足量月份，無法計算漂移。</div>'
    )

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(name)} — 馬丁掃描報告</title>
<style>{CSS}</style>
</head>
<body>
<h1>{_e(name)}</h1>
<div class="sub">來源 <code>{_e(os.path.basename(rec.path))}</code>　·　交易期間 {span}　·　
共 {rec.trades} 筆交易　·　{len(rec.symbols)} 個品種</div>

<div class="kpis">
  <div class="kpi"><div class="k">淨利</div><div class="v">{_money(rec.net_profit)}</div></div>
  <div class="kpi"><div class="k">淨點數</div><div class="v">{rec.net_pips:.1f}</div></div>
  <div class="kpi"><div class="k">勝率</div><div class="v">{_pct(rec.win_rate)}</div></div>
  <div class="kpi"><div class="k">持倉組數</div><div class="v">{rec.cycles}</div></div>
  <div class="kpi"><div class="k">最深層數</div><div class="v">{rec.deepest_layers}</div></div>
  <div class="kpi"><div class="k">資料質量</div><div class="v">{_quality_badge(rec)}</div></div>
</div>

<h2>資料質量</h2>
<div class="card"><ul class="issues">{_issue_items(rec)}</ul></div>

<h2>按日期段分拆</h2>
<div class="controls">
  <label>由 <input type="month" id="from"></label>
  <label>至 <input type="month" id="to"></label>
  <span class="sub" style="margin:0">顯示 <strong id="shown">0</strong> 段</span>
</div>
<div class="card" style="padding:0">
<table>
<thead><tr>
<th>日期段</th><th>交易</th><th>勝率</th><th>淨利</th><th>淨點數</th>
<th>最大不利</th><th>品種</th><th>最深層</th>
</tr></thead>
<tbody id="segbody">
{_segment_rows(rec)}
</tbody>
</table>
</div>
{drift_html}

<h2>分層（Excel 法 vs 線性法）</h2>
<div class="card">
<p>Excel 法：基準手數 <code>{rec.layers_excel.get("base")}</code>，
倍率 <code>{rec.layers_excel.get("step")}</code>，
最深 <strong>{rec.layers_excel.get("max_layer")}</strong> 層，
分類率 {_pct(rec.layers_excel.get("classification_rate", 0))}。</p>
<p>線性法：基準手數 <code>{rec.layers_linear.get("base")}</code>，
最深 <strong>{rec.layers_linear.get("max_layer")}</strong> 層。</p>
{'<p><span class="pill p-warn">兩法結論不同</span> 頁面排名用邊個方法會改變結果，需先定案。</p>' if rec.methods_disagree else ''}
<table><thead><tr><th>Excel 層</th><th>交易數</th></tr></thead>
<tbody>{_layer_rows(rec.layers_excel)}</tbody></table>
</div>

<footer>由 TSA Extra Martingale Scanner 產生。本頁只描述數據，不構成策略建議。</footer>
<script>{SCRIPT}</script>
</body>
</html>
"""


def write(rec: SignalRecord, path: str, title: Optional[str] = None) -> str:
    """Render and write; returns the path written. LF endings, UTF-8."""
    doc = render(rec, title=title)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(doc)
    return path


def render_index(records: Sequence[SignalRecord], title: str = "馬丁掃描總覽") -> str:
    """One page listing every scanned signal, sortable by the columns shown."""
    rows: List[str] = []
    for r in records:
        badge = _quality_badge(r)
        rows.append(
            f'<tr><td>{_e(r.signal_id)}</td><td>{r.trades}</td>'
            f'<td>{_pct(r.win_rate)}</td><td>{_money(r.net_profit)}</td>'
            f'<td>{r.cycles}</td><td>{r.deepest_layers}</td>'
            f'<td>{r.layers_excel.get("max_layer", 0)}</td>'
            f'<td>{badge}</td></tr>'
        )
    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{_e(title)}</title><style>{CSS}</style></head>
<body>
<h1>{_e(title)}</h1>
<div class="sub">共 {len(records)} 個信號</div>
<div class="card" style="padding:0">
<table><thead><tr>
<th>信號</th><th>交易</th><th>勝率</th><th>淨利</th><th>組數</th>
<th>最深層</th><th>Excel 層</th><th>質量</th>
</tr></thead><tbody>
{chr(10).join(rows)}
</tbody></table></div>
<footer>由 TSA Extra Martingale Scanner 產生。</footer>
</body></html>
"""
