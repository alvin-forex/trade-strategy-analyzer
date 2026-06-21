#!/usr/bin/env python3
"""
Generate Portfolio V2 Reports
=============================
方案 B + D 綜合報告：
- P1-P10 Portfolio V2 個別報告
- Portfolio Master Report V2 總報告

Depends on: scripts/portfolio_v2_analyzer.py
"""

import os
import json
from datetime import datetime
from html import escape

from portfolio_v2_analyzer import PORTFOLIO_DEFS, analyze_portfolio

OUT_DIR = "docs/portfolios"
DATA_OUT = "data/portfolio_v2_results.json"


def cls_num(v):
    try:
        return "positive" if float(v) >= 0 else "negative"
    except Exception:
        return ""


def fmt_money(v):
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "$0.00"


def fmt_pct(v):
    try:
        vf = float(v)
        if vf > 100:
            return f"{vf:.0f}%（異常）"
        return f"{vf:.1f}%"
    except Exception:
        return "0.0%"


def judgment(score, avg_trades, prof_pct, dd_pct, corr_pairs):
    """Portfolio level judgment"""
    flags = []
    if avg_trades < 20:
        flags.append("月度交易機會不足")
    if prof_pct < 60:
        flags.append("盈利月份比例偏低")
    if dd_pct > 50:
        flags.append("回撤偏高")
    if len(corr_pairs) >= 2:
        flags.append("信號相關性偏高")

    if score >= 75 and not flags:
        return "✅ 可考慮跟", "good", "月度交易充足、盈利月份比例高、回撤及相關性可控。"
    if score >= 60 and len(flags) <= 1:
        return "✅ 偏正面", "good", "整體條件合格，但仍需留意：" + ("、".join(flags) if flags else "風險管理")
    if score >= 40:
        return "⚠️ 觀察", "warn", "需要觀察：" + "、".join(flags or ["數據穩定性一般"])
    return "❌ 不建議", "bad", "未符合基本跟單條件：" + "、".join(flags or ["機會評分偏低"])


def base_css():
    return """
<style>
:root{--bg:#0d1117;--card:#161b22;--muted:#8b949e;--border:#30363d;--fg:#e6edf3;--accent:#58a6ff;--green:#3fb950;--red:#f85149;--yellow:#d29922;--purple:#bc8cff}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Noto Sans TC','Helvetica Neue',Arial,sans-serif;line-height:1.55}.container{max-width:1280px;margin:0 auto;padding:24px}.hero{padding:28px;background:linear-gradient(135deg,#1f6feb33,#bc8cff22);border:1px solid var(--border);border-radius:18px;margin-bottom:20px}h1{margin:0 0 8px;font-size:34px}h2{margin:28px 0 12px;border-left:4px solid var(--accent);padding-left:12px}h3{margin:20px 0 10px}.meta{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px}.label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}.value{font-size:24px;font-weight:700;margin-top:4px}.positive{color:var(--green)}.negative{color:var(--red)}.warn{color:var(--yellow)}.good{color:var(--green)}.bad{color:var(--red)}.pill{display:inline-block;padding:4px 9px;border-radius:999px;border:1px solid var(--border);background:#21262d;margin:2px;font-size:12px}.pill.good{border-color:#238636;color:#3fb950}.pill.warn{border-color:#9e6a03;color:#d29922}.pill.bad{border-color:#da3633;color:#f85149}table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin:12px 0}th,td{border-bottom:1px solid var(--border);padding:10px;text-align:left;font-size:14px}th{background:#21262d;color:#c9d1d9;position:sticky;top:0}tr:hover{background:#1c2128}.small{font-size:12px;color:var(--muted)}.section{background:rgba(22,27,34,.55);border:1px solid var(--border);border-radius:16px;padding:18px;margin:18px 0}.bar{height:8px;background:#30363d;border-radius:999px;overflow:hidden}.bar>span{display:block;height:100%;background:linear-gradient(90deg,#3fb950,#58a6ff)}.corr-high{background:#f8514922}.corr-low{background:#3fb95022}.nav{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}.nav a{color:#58a6ff;text-decoration:none;border:1px solid var(--border);padding:6px 10px;border-radius:8px;background:#161b22}.note{border-left:4px solid var(--yellow);background:#d2992211;padding:12px;border-radius:8px}.footer{margin-top:40px;color:var(--muted);font-size:12px}.chart{width:100%;height:180px;background:#0b1220;border:1px solid var(--border);border-radius:12px;margin-top:8px}@media(max-width:720px){.container{padding:12px}h1{font-size:26px}th,td{font-size:12px;padding:7px}.value{font-size:20px}}
</style>
"""


def equity_svg(curve):
    if not curve or len(curve) < 2:
        return '<div class="small">No equity curve</div>'
    vals = [float(v[1]) for v in curve]
    mn, mx = min(vals), max(vals)
    if mx == mn:
        mx = mn + 1
    width, height = 900, 180
    pts = []
    for i, (_, y) in enumerate(curve):
        x = i / max(1, len(curve)-1) * width
        yy = height - ((float(y) - mn) / (mx - mn) * (height - 20) + 10)
        pts.append(f"{x:.1f},{yy:.1f}")
    color = "#3fb950" if vals[-1] >= vals[0] else "#f85149"
    return f'''<svg class="chart" viewBox="0 0 {width} {height}" preserveAspectRatio="none">
<polyline points="{' '.join(pts)}" fill="none" stroke="{color}" stroke-width="3"/>
<text x="8" y="18" fill="#8b949e" font-size="12">Peak {fmt_money(mx)} / Low {fmt_money(mn)}</text>
</svg>'''


def render_signal_table(signals):
    rows = []
    for s in signals:
        if "error" in s:
            rows.append(f"<tr><td>{escape(s.get('signal_id','?'))}</td><td colspan='10' class='negative'>{escape(s['error'])}</td></tr>")
            continue
        sim = s.get("simulation") or {}
        score = s.get("opportunity_score", {})
        rows.append(f"""
<tr>
<td><a href="../reports/martin_final_{escape(s['signal_id'])}.html">{escape(s['signal_id'])}</a></td>
<td>{s.get('total_trades',0):,}</td>
<td>{s.get('active_months',0)}</td>
<td>{s.get('avg_monthly_trades',0)}</td>
<td>{s.get('recent_3mo_avg_trades',0)}</td>
<td class="{cls_num(s.get('recent_3mo_pnl',0))}">{fmt_money(s.get('recent_3mo_pnl',0))}</td>
<td>{fmt_pct(s.get('recent_3mo_win_rate',0))}</td>
<td>{fmt_pct(s.get('profitable_month_pct',0))}</td>
<td class="negative">{fmt_pct(sim.get('max_dd_pct_001',0))}</td>
<td>{sim.get('max_consec_loss_months',0)}</td>
<td><span class="pill {'good' if score.get('score',0)>=70 else 'warn' if score.get('score',0)>=40 else 'bad'}">{score.get('score',0)} / {score.get('grade','?')}</span></td>
</tr>
""")
    return """
<table>
<thead><tr>
<th>Signal</th><th>總交易</th><th>活躍月</th><th>平均/月</th><th>近3月/月</th><th>近3月PnL</th><th>近3月勝率</th><th>盈利月份</th><th>月度DD(0.01lot)</th><th>連虧月</th><th>機會分</th>
</tr></thead><tbody>
""" + "\n".join(rows) + "</tbody></table>"


def render_monthly_table(signal):
    stats = signal.get("monthly_stats", [])[-12:]
    if not stats:
        return "<p class='small'>No monthly data</p>"
    rows = []
    for m in stats:
        rows.append(f"""
<tr><td>{m['month']}</td><td>{m['trades']}</td><td>{fmt_pct(m['win_rate'])}</td><td class="{cls_num(m['total_pnl'])}">{fmt_money(m['total_pnl'])}</td><td>{m['profit_factor']}</td><td>{m['avg_lots']}</td></tr>
""")
    return """
<table><thead><tr><th>月份</th><th>交易數</th><th>勝率</th><th>Net PnL</th><th>PF</th><th>平均Lots</th></tr></thead><tbody>
""" + "\n".join(rows) + "</tbody></table>"


def render_corr(corr):
    pairs = corr.get("high_correlation_pairs", [])
    if not pairs:
        return "<p class='small'>未發現絕對相關性 > 0.6 的 Signal pair。</p>"
    rows = []
    for p in pairs[:12]:
        cls = "corr-high" if p["correlation"] > 0 else "corr-low"
        rows.append(f"<tr class='{cls}'><td>{p['signal_1']}</td><td>{p['signal_2']}</td><td>{p['correlation']}</td><td>{p['direction']}</td></tr>")
    return """
<table><thead><tr><th>Signal A</th><th>Signal B</th><th>相關性</th><th>方向</th></tr></thead><tbody>
""" + "\n".join(rows) + "</tbody></table>"


def portfolio_level_metrics(result):
    valid = [s for s in result["signals"] if "error" not in s]
    if not valid:
        return {"max_dd_pct_001": 0, "avg_score": 0}
    max_dd_pct_001 = max((s.get("simulation") or {}).get("max_dd_pct_001", 0) for s in valid)
    avg_score = sum(s.get("opportunity_score",{}).get("score",0) for s in valid) / len(valid)
    min_recent_trades = min(s.get("recent_3mo_avg_trades",0) for s in valid)
    total_recent_pnl = sum(s.get("recent_3mo_pnl",0) for s in valid)
    return {
        "max_dd_pct_001": round(max_dd_pct_001, 1),
        "avg_score": round(avg_score, 1),
        "min_recent_trades": round(min_recent_trades, 1),
        "total_recent_pnl": round(total_recent_pnl, 2),
    }


def render_portfolio_report(pdef, result):
    metrics = portfolio_level_metrics(result)
    corr_pairs = result.get("correlation", {}).get("high_correlation_pairs", [])
    title, title_cls, reason = judgment(metrics["avg_score"], result["avg_monthly_trades"], result["avg_profitable_month_pct"], metrics["max_dd_pct_001"], corr_pairs)
    generated = datetime.now().strftime("%Y-%m-%d %H:%M HKT")

    best_signal = max([s for s in result["signals"] if "error" not in s], key=lambda s: s.get("opportunity_score",{}).get("score",0), default=None)

    html = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{pdef['id']} Portfolio V2</title><link rel="stylesheet" href="../sidebar.css">{base_css()}</head><body><div class="container">
<div class="hero">
<h1>{pdef['id']} — {escape(pdef['name'])} <span class="pill {title_cls}">{title}</span></h1>
<div class="meta">Portfolio V2 Simulation｜方案 B：月度順序回測 + 方案 D：相關性分析｜Generated: {generated}</div>
<div class="nav"><a href="portfolio_master_report_v2.html">← 總報告</a><a href="portfolio_{pdef['id']}_enhanced.html">舊 Enhanced 版</a></div>
</div>

<div class="note"><strong>判斷：</strong>{reason}<br><span class="small">注意：此 V2 用本地 AlgoForest CSV 交易紀錄，PnL 以 source CSV + 0.01lot 標準化作相對質素比較；不等於實盤保證收益，仍不是 MT4 Bar-by-Bar backtest。</span></div>

<div class="grid">
<div class="card"><div class="label">Capital</div><div class="value">{fmt_money(pdef['capital'])}</div></div>
<div class="card"><div class="label">Risk %</div><div class="value">{pdef['risk_pct']}%</div></div>
<div class="card"><div class="label">Signal Count</div><div class="value">{result['valid_signal_count']} / {result['signal_count']}</div></div>
<div class="card"><div class="label">Avg Monthly Trades</div><div class="value">{result['avg_monthly_trades']}</div></div>
<div class="card"><div class="label">Profitable Month Avg</div><div class="value positive">{fmt_pct(result['avg_profitable_month_pct'])}</div></div>
<div class="card"><div class="label">Worst Sequential DD</div><div class="value negative">{fmt_pct(metrics['max_dd_pct_001'])}</div></div>
<div class="card"><div class="label">Avg Opportunity Score</div><div class="value">{metrics['avg_score']}</div></div>
<div class="card"><div class="label">Recent 3M PnL Sum</div><div class="value {cls_num(metrics['total_recent_pnl'])}">{fmt_money(metrics['total_recent_pnl'])}</div></div>
</div>

<h2>Signal 月度可行性 + 順序回測摘要</h2>
{render_signal_table(result['signals'])}

<h2>Portfolio 相關性風險</h2>
<p class="small">以每月 PnL 做 Pearson correlation；>0.6 代表可能同時好/同時差，組合分散效果較低。</p>
{render_corr(result['correlation'])}

<h2>Signal 詳細月度分佈（最近 12 個月）</h2>
"""
    for s in result["signals"]:
        if "error" in s:
            continue
        score = s.get("opportunity_score", {})
        sim = s.get("simulation") or {}
        html += f"""
<div class="section">
<h3>Signal {escape(s['signal_id'])} <span class="pill {'good' if score.get('score',0)>=70 else 'warn' if score.get('score',0)>=40 else 'bad'}">Score {score.get('score',0)} / {score.get('grade','?')}</span></h3>
<div class="grid">
<div class="card"><div class="label">平均每月交易</div><div class="value">{s.get('avg_monthly_trades',0)}</div></div>
<div class="card"><div class="label">最低月交易</div><div class="value">{s.get('min_monthly_trades',0)}</div></div>
<div class="card"><div class="label">盈利月份</div><div class="value positive">{fmt_pct(s.get('profitable_month_pct',0))}</div></div>
<div class="card"><div class="label">近3月平均/月</div><div class="value">{s.get('recent_3mo_avg_trades',0)}</div></div>
<div class="card"><div class="label">月度 Max DD</div><div class="value negative">{fmt_pct(sim.get('max_dd_pct_001',0))}</div></div>
<div class="card"><div class="label">連虧月</div><div class="value warn">{sim.get('max_consec_loss_months',0)}</div></div>
</div>
{equity_svg(sim.get('equity_curve_001', []))}
{render_monthly_table(s)}
</div>
"""

    html += f"""
<div class="footer">Trade Strategy Analyzer / Portfolio V2 ｜Generated {generated}</div>
</div><script src="../sidebar.js"></script></body></html>
"""
    return html


def render_master(results):
    generated = datetime.now().strftime("%Y-%m-%d %H:%M HKT")
    rows = []
    ranked = []
    for r in results:
        metrics = portfolio_level_metrics(r)
        corr_pairs = r.get("correlation", {}).get("high_correlation_pairs", [])
        title, title_cls, reason = judgment(metrics["avg_score"], r["avg_monthly_trades"], r["avg_profitable_month_pct"], metrics["max_dd_pct_001"], corr_pairs)
        ranked.append((metrics["avg_score"], r, metrics, title, title_cls, reason))
    ranked.sort(key=lambda x: x[0], reverse=True)

    for rank, (score, r, m, title, title_cls, reason) in enumerate(ranked, 1):
        rows.append(f"""
<tr>
<td>{rank}</td><td><a href="portfolio_{r['portfolio_id']}_v2.html">{r['portfolio_id']} — {escape(r['portfolio_name'])}</a></td>
<td><span class="pill {title_cls}">{title}</span></td>
<td>{r['valid_signal_count']}</td>
<td>{r['avg_monthly_trades']}</td>
<td>{fmt_pct(r['avg_profitable_month_pct'])}</td>
<td class="{cls_num(m['total_recent_pnl'])}">{fmt_money(m['total_recent_pnl'])}</td>
<td class="negative">{fmt_pct(m['max_dd_pct_001'])}</td>
<td>{len(r.get('correlation',{}).get('high_correlation_pairs',[]))}</td>
<td>{m['avg_score']}</td>
<td class="small">{escape(reason)}</td>
</tr>
""")

    top = ranked[0] if ranked else None
    html = f"""<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Portfolio Master Report V2</title><link rel="stylesheet" href="../sidebar.css">{base_css()}</head><body><div class="container">
<div class="hero">
<h1>Portfolio Master Report V2</h1>
<div class="meta">10 個 Portfolio 橫向比較｜方案 B 月度順序回測 + 方案 D 相關性分析｜Generated: {generated}</div>
</div>

<div class="note"><strong>總結：</strong>此總報告用作比較 P1-P10 邊個最有「每月交易機會 + 盈利穩定性 + 分散風險」。Portfolio V2 不再自成一角，應整合入 TSA 報告入口、ranking、signal deep analysis 連結。</div>

<div class="grid">
<div class="card"><div class="label">Portfolios</div><div class="value">{len(results)}</div></div>
<div class="card"><div class="label">Best Candidate</div><div class="value positive">{top[1]['portfolio_id'] if top else '-'}</div></div>
<div class="card"><div class="label">Best Score</div><div class="value">{top[2]['avg_score'] if top else '-'}</div></div>
<div class="card"><div class="label">Generated</div><div class="value" style="font-size:16px">{generated}</div></div>
</div>

<h2>Portfolio 排名比較</h2>
<table>
<thead><tr><th>#</th><th>Portfolio</th><th>判斷</th><th>Signals</th><th>平均/月交易</th><th>盈利月份</th><th>近3月PnL合計</th><th>最差DD</th><th>高相關Pairs</th><th>Score</th><th>原因</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table>

<h2>建議整合方向</h2>
<ul>
<li>Portfolio V2 應納入 TSA 主 sidebar / report registry，而非獨立 html 孤島。</li>
<li>Signal links 應連去 Deep Analysis / Martin Autopsy，Portfolio 只作組合層決策。</li>
<li>日後 ranking 應加入「Monthly Opportunity Score」及「Portfolio Fit Score」。</li>
<li>QA gate 要檢查 Portfolio V2 連結、CSV 數據時效、報告生成日期。</li>
</ul>

<div class="nav">
"""
    for r in results:
        html += f"<a href='portfolio_{r['portfolio_id']}_v2.html'>{r['portfolio_id']} V2</a>"
    html += f"""
</div>
<div class="footer">Trade Strategy Analyzer / Portfolio Master Report V2 ｜Generated {generated}</div>
</div><script src="../sidebar.js"></script></body></html>"""
    return html


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    results = []
    for p in PORTFOLIO_DEFS:
        print(f"=== Generating {p['id']} {p['name']} ===")
        r = analyze_portfolio(p["id"], p["name"], p["signals"], p["capital"], p["risk_pct"])
        r["ea_types"] = p.get("ea_types", "")
        r["risk_level"] = p.get("risk_level", "")
        results.append(r)
        html = render_portfolio_report(p, r)
        out = os.path.join(OUT_DIR, f"portfolio_{p['id']}_v2.html")
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  Wrote {out}")

    master = render_master(results)
    master_out = os.path.join(OUT_DIR, "portfolio_master_report_v2.html")
    with open(master_out, "w", encoding="utf-8") as f:
        f.write(master)
    print(f"Wrote {master_out}")

    # JSON artifact for future integration
    with open(DATA_OUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"Wrote {DATA_OUT}")


if __name__ == "__main__":
    main()
