#!/usr/bin/env python3
"""Generate Martin Autopsy V4 interactive HTML pages for all Signals.

Creates one HTML per signal that loads CSV and renders client-side.
Uses pre-built templates with inlined JavaScript engine.
"""
import os
import sys
import json
import shutil
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from set_parser import get_set_configs_for_signal

# Import EA configuration from centralized config
from config import EA_MAP, get_ea_type as get_ea_tag

BASE_DIR: Path = Path(__file__).parent
DOCS_DIR: Path = BASE_DIR / 'docs'
REPORTS_DIR: Path = BASE_DIR / 'reports'
OUTPUT_DIR: Path = BASE_DIR / 'output'
DOWNLOADS_DIR: Path = BASE_DIR / 'downloads'


def generate_signal_page(signal_id: str, ea_tag: str, csv_filename: str) -> str:
    """Generate one HTML page for a signal.

    Args:
        signal_id: Signal ID string.
        ea_tag: EA type tag (e.g. 'SMA', 'DW').
        csv_filename: CSV filename for data reference.

    Returns:
        Full HTML string with inlined JS engine.
    """
    template_path: Path = BASE_DIR / 'martin_v4_template.html'
    engine_path: Path = BASE_DIR / 'martin_v4_engine.js'

    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template: str = f.read()
    except FileNotFoundError:
        print(f"  ✗ Template not found: {template_path}")
        return ""

    try:
        with open(engine_path, 'r', encoding='utf-8') as f:
            engine_js: str = f.read()
    except FileNotFoundError:
        print(f"  ✗ Engine JS not found: {engine_path}")
        return ""

    # CSV URL relative from docs/reports/ -> ../../downloads/ or via symlink docs/downloads/
    csv_url: str = f'../downloads/{csv_filename}'

    # Get SET file configurations for this signal
    set_dir: str = str(BASE_DIR / 'downloads' / 'set_files')
    set_data = get_set_configs_for_signal(signal_id, set_dir)
    set_json: str = json.dumps(set_data, ensure_ascii=False)

    # Replace placeholders
    html: str = template.replace('%%SIGNAL_ID%%', signal_id)
    html = html.replace('%%EA%%', ea_tag)
    html = html.replace('%%CSV_URL%%', csv_url)
    html = html.replace('%%SET_DATA%%', set_json)

    # Inline the engine JS (GitHub Pages friendly)
    html = html.replace('<script src="martin_v4_engine.js"></script>', f'<script>\n{engine_js}\n</script>')

    return html


def main() -> None:
    """Main entry point: batch-generate Martin V4 pages for all CSVs."""
    print("🔄 Generating Martin Autopsy V4 pages...")

    for d in [DOCS_DIR / 'reports', REPORTS_DIR, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    count: int = 0
    csv_files: List[Path] = sorted(DOWNLOADS_DIR.glob('*.csv'))
    if not csv_files:
        print("  ⚠ No CSV files found in downloads/")
        return

    for f in csv_files:
        fname: str = f.stem
        sid: str = fname.replace('forex-forest-signals-page-', '').replace('signal_', '')
        try:
            int(sid)
        except ValueError:
            continue

        ea: str = get_ea_tag(sid)
        html: str = generate_signal_page(sid, ea, f.name)
        if not html:
            continue

        for out_dir in [DOCS_DIR / 'reports', REPORTS_DIR, OUTPUT_DIR]:
            out_path: Path = out_dir / f'martin_v4_{sid}.html'
            with open(out_path, 'w', encoding='utf-8') as fh:
                fh.write(html)

        count += 1
        if count % 10 == 0:
            print(f"  📊 Generated {count} pages...")

    print(f"  ✅ Total: {count} Martin V4 pages generated")

    # Copy engine.js to docs for direct reference
    engine_src: Path = BASE_DIR / 'martin_v4_engine.js'
    if engine_src.exists():
        shutil.copy2(engine_src, DOCS_DIR / 'martin_v4_engine.js')
        print(f"  ✅ Engine JS copied to docs/")


if __name__ == '__main__':
    main()
