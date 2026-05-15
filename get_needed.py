#!/usr/bin/env python3
"""
Batch generate index reports using OpenClaw browser tool.
Outputs signal IDs for the caller to process one by one.
"""
import glob, os, json

downloads = 'downloads'
reports = 'docs/reports'
csvs = glob.glob(f'{downloads}/forex-forest-signals-page-*.csv')
needed = []
for c in csvs:
    sid = os.path.basename(c).replace('forex-forest-signals-page-','').replace('.csv','')
    if not os.path.exists(f'{reports}/index_{sid}.html'):
        needed.append(sid)

needed.sort(key=int)
print(json.dumps(needed))
