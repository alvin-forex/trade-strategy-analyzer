#!/usr/bin/env python3
"""
Generate Martin Autopsy V4 interactive HTML pages for all Signals.
Creates one HTML per signal that loads CSV and renders client-side.
"""
import os
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'scripts'))
from set_parser import get_set_configs_for_signal

BASE_DIR = Path(__file__).parent
DOWNLOADS_DIR = BASE_DIR / 'downloads'
DOCS_DIR = BASE_DIR / 'docs'
REPORTS_DIR = BASE_DIR / 'reports'
OUTPUT_DIR = BASE_DIR / 'output'

EA_MAP = {
    'DW': ['10437','11984','13790','17547','21698','22200','22278','25830','30359','31781','32719','3291','33101','31593','34574','36338','36397','36511','34259','20846','16538','19625','35434','35436'],
    'SMA': ['106','1980','2351','32278','32541','5001','5275','537','5566','11889','13863','14724','16596','16698','16706','17611','17823','10864','14158','5636','2739','16777','35362'],
    'MKD': ['12962','13461','14341','14592','1470','17962','20805','23617','25668','25260','8325','7919','16266'],
    'S10': ['13798','16596'],
    'Flash': ['19849'],
    'GEM': ['14581'],
    'MAN': ['12173'],
}

def get_ea_tag(signal_id):
    s = str(signal_id)
    for ea, ids in EA_MAP.items():
        if s in ids: return ea
    return 'UNK'


def generate_signal_page(signal_id, ea_tag, csv_filename):
    """Generate one HTML page for a signal."""
    template_path = BASE_DIR / 'martin_v4_template.html'
    engine_path = BASE_DIR / 'martin_v4_engine.js'
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    with open(engine_path, 'r', encoding='utf-8') as f:
        engine_js = f.read()
    
    # CSV URL relative from docs/reports/ -> ../../downloads/ or via symlink docs/downloads/
    csv_url = f'../downloads/{csv_filename}'
    
    # Get SET file configurations for this signal
    set_dir = str(BASE_DIR / 'downloads' / 'set_files')
    set_data = get_set_configs_for_signal(signal_id, set_dir)
    set_json = json.dumps(set_data, ensure_ascii=False)
    
    # Replace placeholders
    html = template.replace('%%SIGNAL_ID%%', signal_id)
    html = html.replace('%%EA%%', ea_tag)
    html = html.replace('%%CSV_URL%%', csv_url)
    html = html.replace('%%SET_DATA%%', set_json)
    
    # Inline the engine JS (GitHub Pages friendly)
    html = html.replace('<script src="martin_v4_engine.js"></script>', f'<script>\n{engine_js}\n</script>')
    
    return html


def main():
    print("🔄 Generating Martin Autopsy V4 pages...")
    
    for d in [DOCS_DIR / 'reports', REPORTS_DIR, OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    
    count = 0
    for f in sorted(DOWNLOADS_DIR.glob('*.csv')):
        fname = f.stem
        sid = fname.replace('forex-forest-signals-page-', '').replace('signal_', '')
        try:
            int(sid)
        except ValueError:
            continue
        
        ea = get_ea_tag(sid)
        html = generate_signal_page(sid, ea, f.name)
        
        for out_dir in [DOCS_DIR / 'reports', REPORTS_DIR, OUTPUT_DIR]:
            out_path = out_dir / f'martin_v4_{sid}.html'
            with open(out_path, 'w', encoding='utf-8') as fh:
                fh.write(html)
        
        count += 1
        if count % 10 == 0:
            print(f"  📊 Generated {count} pages...")
    
    print(f"  ✅ Total: {count} Martin V4 pages generated")
    
    # Copy engine.js to docs for direct reference
    engine_src = BASE_DIR / 'martin_v4_engine.js'
    if engine_src.exists():
        import shutil
        shutil.copy2(engine_src, DOCS_DIR / 'martin_v4_engine.js')
        print(f"  ✅ Engine JS copied to docs/")


if __name__ == '__main__':
    main()
