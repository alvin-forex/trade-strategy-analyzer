#!/usr/bin/env python3
"""Render TSA_WhitePaper.md → PDF via weasyprint (CJK-safe)."""
import markdown, weasyprint

SRC = '/home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/TSA_WhitePaper.md'
OUT = '/home/alvin/.openclaw/workspace/whatsapp_out/TSA_WhitePaper.pdf'

html_body = markdown.markdown(open(SRC, encoding='utf-8').read(),
                              extensions=['tables', 'fenced_code'])

css = """
@page { size: A4; margin: 18mm 16mm;
        @bottom-center { content: counter(page) " / " counter(pages); font-size: 8pt; color: #888; } }
body { font-family: 'Noto Sans CJK SC', sans-serif; font-size: 10pt; line-height: 1.55; color: #1a1a1a; }
h1 { font-size: 18pt; color: #0d3b66; border-bottom: 3px solid #0d3b66; padding-bottom: 6px; }
h2 { font-size: 14pt; color: #0d3b66; border-bottom: 1.5px solid #ccc; margin-top: 22px; }
h3 { font-size: 12pt; color: #0d3b66; margin-top: 16px; }
table { border-collapse: collapse; width: 100%; margin: 10px 0; font-size: 8.5pt; }
th, td { border: 1px solid #bbb; padding: 4px 7px; text-align: left; }
th { background: #eef4fa; }
code { background: #f0f2f5; padding: 1px 4px; font-family: 'Courier New', monospace; font-size: 8.5pt; }
pre { background: #f6f8fa; border: 1px solid #ddd; padding: 8px; font-size: 8pt; overflow-x: auto; white-space: pre-wrap; }
blockquote { border-left: 4px solid #0d3b66; background: #f4f8fc; padding: 4px 12px; }
li { margin: 2px 0; }
"""

weasyprint.HTML(string=f"<html><head><meta charset='utf-8'><style>{css}</style></head><body>{html_body}</body></html>").write_pdf(OUT)
print("PDF written:", OUT)
