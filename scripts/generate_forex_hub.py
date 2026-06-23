#!/usr/bin/env python3
"""Generate Forex Intelligence Hub index page.

Combines 4H market analysis reports and daily forex reports into a single
TSA admin timeline page.
"""
from __future__ import annotations

import html
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ADMIN = DOCS / "admin"
FOUR_H_DIR = ADMIN / "4h_reports"
DAILY_DIR = ADMIN / "forex_reports"
OUT_DIR = ADMIN / "forex_hub"
OUT_FILE = OUT_DIR / "index.html"


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""


def strip_tags(s: str) -> str:
    s = re.sub(r"<script[\s\S]*?</script>", " ", s, flags=re.I)
    s = re.sub(r"<style[\s\S]*?</style>", " ", s, flags=re.I)
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def title_from_html(text: str, fallback: str) -> str:
    m = re.search(r"<title>(.*?)</title>", text, re.I | re.S)
    if m:
        return strip_tags(m.group(1))
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.I | re.S)
    if h1:
        return strip_tags(h1.group(1))
    return fallback


def extract_first(patterns: list[str], text: str, default: str = "") -> str:
    plain = strip_tags(text)
    for pat in patterns:
        m = re.search(pat, plain, re.I)
        if m:
            return m.group(0).strip()
    return default


def classify_daily(path: Path, title: str) -> str:
    name = path.stem.lower()
    if "morning" in name or "早" in title:
        return "早盤外匯報告"
    if "evening" in name or "晚" in title:
        return "晚盤外匯報告"
    return "每日外匯報告"


def parse_daily_datetime(path: Path) -> tuple[str, str, datetime]:
    name = path.stem
    m = re.search(r"(\d{4}-\d{2}-\d{2})_(morning|evening)", name)
    if m:
        date = m.group(1)
        typ = m.group(2)
        tm = "07:00" if typ == "morning" else "18:00"
        return date, tm, datetime.fromisoformat(f"{date}T{tm}:00")
    m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    date = m.group(1) if m else datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    dt = datetime.fromtimestamp(path.stat().st_mtime)
    return date, dt.strftime("%H:%M"), dt


def parse_4h_datetime(path: Path) -> tuple[str, str, datetime]:
    m = re.search(r"(\d{4}-\d{2}-\d{2})", path.stem)
    date = m.group(1) if m else datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
    text = read_text(path)
    plain = strip_tags(text)
    tm = "16:00"
    t = re.search(r"(\d{1,2}:\d{2})\s*HKT", plain)
    if t:
        tm = t.group(1).zfill(5)
    else:
        dt = datetime.fromtimestamp(path.stat().st_mtime)
        tm = dt.strftime("%H:%M")
    return date, tm, datetime.fromisoformat(f"{date}T{tm}:00")


def build_items() -> list[dict]:
    items: list[dict] = []

    for path in sorted(FOUR_H_DIR.glob("*.html")):
        if path.name == "index.html":
            continue
        text = read_text(path)
        date, tm, dt = parse_4h_datetime(path)
        plain = strip_tags(text)
        market = extract_first([
            r"DXY[^。|\n]{0,80}",
            r"Market Glance[^。\n]{0,140}",
        ], text, "Market Glance / CCY Power / 配對信號")
        ccy = extract_first([
            r"CCY Power[^。\n]{0,160}",
            r"H1 最強[^。\n]{0,120}",
        ], text, "CCY Power 強弱排行")
        signals = extract_first([
            r"AUDCAD[^。\n]{0,100}EURCHF[^。\n]{0,100}XAUUSD[^。\n]{0,100}",
            r"配對信號[^。\n]{0,160}",
        ], text, "AUDCAD / EURCHF / XAUUSD")
        items.append({
            "type": "4h",
            "icon": "🦀",
            "date": date,
            "time": tm,
            "dt": dt,
            "title": "4H 市場綜合分析",
            "url": f"../4h_reports/{path.name}",
            "summary": [market, ccy, signals],
        })

    for path in sorted(DAILY_DIR.glob("*.html")):
        text = read_text(path)
        title = title_from_html(text, path.stem)
        date, tm, dt = parse_daily_datetime(path)
        daily_type = classify_daily(path, title)
        tech = extract_first([
            r"技術指標全景[^。\n]{0,120}",
            r"AUDCAD[^。\n]{0,90}EURCHF[^。\n]{0,90}XAUUSD[^。\n]{0,90}",
        ], text, "技術全景 / 新聞 / 事件 / 配對信號")
        market = extract_first([
            r"DXY[^。|\n]{0,80}",
            r"標普500[^。\n]{0,100}",
            r"Market Glance[^。\n]{0,140}",
        ], text, "Market Glance + 技術分析")
        items.append({
            "type": "daily",
            "icon": "📰",
            "date": date,
            "time": tm,
            "dt": dt,
            "title": daily_type,
            "url": f"../forex_reports/{path.name}",
            "summary": [market, tech],
        })

    return sorted(items, key=lambda x: x["dt"], reverse=True)


def render(items: list[dict]) -> str:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for item in items:
        grouped[item["date"]].append(item)

    dates = sorted(grouped.keys(), reverse=True)
    latest_dt = items[0]["dt"].strftime("%Y-%m-%d %H:%M") if items else "N/A"

    cards = []
    for idx, date in enumerate(dates):
        day_items = grouped[date]
        count_4h = sum(1 for i in day_items if i["type"] == "4h")
        count_daily = sum(1 for i in day_items if i["type"] == "daily")
        open_attr = " open" if idx == 0 else ""
        rows = []
        for item in day_items:
            latest_badge = '<span class="badge latest">最新</span>' if item is items[0] else ""
            typ = '<span class="badge type4h">4H</span>' if item["type"] == "4h" else '<span class="badge typedaily">每日</span>'
            summary_html = "".join(f"<div class=\"line\">{html.escape(s)}</div>" for s in item["summary"] if s)
            rows.append(f"""
            <article class="report-card" id="{'4h' if item['type']=='4h' else 'daily'}">
              <div class="card-head">
                <div><span class="time">{item['time']}</span> <span class="icon">{item['icon']}</span> <strong>{html.escape(item['title'])}</strong> {typ} {latest_badge}</div>
                <a class="open-link" href="{item['url']}">查看完整報告 →</a>
              </div>
              <div class="summary">{summary_html}</div>
            </article>
            """)
        cards.append(f"""
        <details class="day"{open_attr}>
          <summary><span>📋 {date}{'（今日）' if idx == 0 else ''}</span><span class="counts">🦀 {count_4h} | 📰 {count_daily}</span></summary>
          <div class="day-body">{''.join(rows)}</div>
        </details>
        """)

    return f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>外匯分析中心 - TSA</title>
<link rel="stylesheet" href="../../sidebar.css">
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#0d1117;color:#c9d1d9;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;padding:18px;max-width:980px}} a{{color:#58a6ff;text-decoration:none}}
.hero{{background:linear-gradient(135deg,#161b22,#0f172a);border:1px solid #21262d;border-radius:14px;padding:20px;margin-bottom:16px}} h1{{margin:0;color:#fff;font-size:24px}} .sub{{color:#8b949e;margin-top:6px}} .stats{{display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}} .stat{{background:#0d1117;border:1px solid #21262d;border-radius:10px;padding:10px 14px}} .stat b{{color:#fff}}
.tabs{{display:flex;gap:8px;margin:14px 0;flex-wrap:wrap}} .tab{{background:#161b22;border:1px solid #30363d;border-radius:999px;padding:8px 12px;color:#c9d1d9}}
.day{{background:#161b22;border:1px solid #21262d;border-radius:12px;margin-bottom:12px;overflow:hidden}} summary{{cursor:pointer;padding:14px 16px;font-weight:700;color:#e6edf3;display:flex;justify-content:space-between;align-items:center}} .counts{{color:#8b949e;font-size:12px;font-weight:500}} .day-body{{padding:0 12px 12px}}
.report-card{{background:#0d1117;border:1px solid #21262d;border-radius:10px;margin:10px 0;padding:12px}} .card-head{{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}} .time{{font-family:monospace;color:#f0b429;font-weight:700}} .icon{{margin:0 4px}} .open-link{{font-size:12px;white-space:nowrap}} .summary{{margin-top:8px;color:#8b949e;font-size:13px;line-height:1.55}} .line{{margin-top:3px}}
.badge{{font-size:10px;border-radius:999px;padding:2px 7px;margin-left:5px;vertical-align:middle}} .latest{{background:#f8514922;color:#f85149}} .type4h{{background:#3fb95022;color:#3fb950}} .typedaily{{background:#58a6ff22;color:#58a6ff}}
.footer{{text-align:center;color:#484f58;font-size:11px;margin:18px 0}}
@media(max-width:768px){{body{{padding:64px 10px 12px}} .card-head{{display:block}} .open-link{{display:inline-block;margin-top:8px}}}}
</style>
</head>
<body class="has-sidebar">
<script src="../../sidebar.js"></script>
<main>
  <section class="hero">
    <h1>📊 外匯分析中心</h1>
    <div class="sub">Forex Intelligence Hub｜4H 市場分析 + 每日外匯報告</div>
    <div class="stats">
      <div class="stat">總報告 <b>{len(items)}</b></div>
      <div class="stat">4H 分析 <b>{sum(1 for i in items if i['type']=='4h')}</b></div>
      <div class="stat">每日報告 <b>{sum(1 for i in items if i['type']=='daily')}</b></div>
      <div class="stat">最新更新 <b>{latest_dt}</b></div>
    </div>
  </section>
  <nav class="tabs">
    <a class="tab" href="#4h">🦀 4H 市場分析</a>
    <a class="tab" href="#daily">📰 每日報告</a>
  </nav>
  {''.join(cards)}
  <div class="footer">Generated by generate_forex_hub.py</div>
</main>
</body>
</html>
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    items = build_items()
    OUT_FILE.write_text(render(items), encoding="utf-8")
    print(f"Generated {OUT_FILE} with {len(items)} reports")


if __name__ == "__main__":
    main()
