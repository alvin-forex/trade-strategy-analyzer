#!/usr/bin/env python3
"""Scan forex_reports/ folder and update forex_news.html REPORT_REGISTRY block."""
import os, re, sys
from pathlib import Path

REPORTS_DIR = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/forex_reports")
NEWS_FILE = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/forex_news.html")

def scan_reports():
    reports = []
    if not REPORTS_DIR.exists():
        return reports
    for f in sorted(REPORTS_DIR.iterdir()):
        if not f.name.endswith('.html') or f.name == 'index.html':
            continue
        m = re.match(r'(\d{4}-\d{2}-\d{2})_(morning|evening|daily)\.html', f.name)
        if m:
            date, typ = m.group(1), m.group(2)
            label = {'morning': '早盤報告', 'evening': '晚盤報告', 'daily': '日報'}[typ]
            reports.append((date, typ, f.name, label))
        elif f.name.startswith('4h'):
            m2 = re.match(r'4h(?:_analysis)?_(\d{4}-\d{2}-\d{2})(?:_\d+)?\.html', f.name)
            if m2:
                reports.append((m2.group(1), '4h', f.name, '4H 分析'))
    reports.sort(key=lambda x: x[0], reverse=True)
    return reports

def update_registry():
    reports = scan_reports()
    if not reports:
        print("No reports found", file=sys.stderr)
        return

    content = NEWS_FILE.read_text(encoding="utf-8")

    lines = ["  /* REPORT_REGISTRY_START */"]
    for date, typ, file, label in reports:
        lines.append(f"  {{date:'{date}',type:'{typ}',file:'{file}',label:'{label}'}},")
    lines.append("  /* REPORT_REGISTRY_END */")
    new_block = "\n".join(lines)

    # Replace only the registry body; do not use re.escape on replacement
    # because that writes literal backslashes into JavaScript.
    pattern = r'(/\* REPORT_REGISTRY_START \*/)(.*?)(/\* REPORT_REGISTRY_END \*/)'
    replacement = lambda m: m.group(1) + '\n' + '\n'.join(
        f"  {{date:'{d}',type:'{t}',file:'{f}',label:'{l}'}},"
        for d, t, f, l in reports
    ) + '\n  ' + m.group(3)
    content, n = re.subn(pattern, replacement, content, flags=re.DOTALL)
    if n == 0:
        raise RuntimeError('REPORT_REGISTRY markers not found in forex_news.html')

    NEWS_FILE.write_text(content, encoding="utf-8")
    print(f"✅ Updated forex_news.html registry: {len(reports)} reports")

if __name__ == "__main__":
    update_registry()
