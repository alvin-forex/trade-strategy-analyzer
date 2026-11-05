#!/usr/bin/env python3
"""w8_dark_fix_shots_20261105.py — 暗調殘白修復活體截圖（暗／亮兩態）
頁：index_38900（多圖大頁）／index_1165（fill=#999 rect 較多頁）
"""
import shutil
import subprocess
from pathlib import Path

REPO = Path('/home/z/my-project/exchange-repo/docs')
TMP = Path('/tmp/w8shot')
if TMP.exists():
    shutil.rmtree(TMP)
(TMP / 'reports').mkdir(parents=True)
for f in ['sidebar.css', 'tsa_tokens.css', 'sidebar.js']:
    shutil.copy(REPO / f, TMP / f)
for sid in ['38900', '1165']:
    shutil.copy(REPO / 'reports' / f'index_{sid}.html', TMP / 'reports' / f'index_{sid}.html')

NODE = r'''
const { chromium } = require('playwright');
(async () => {
  const b = await chromium.launch();
  const pg = await b.newPage({ viewport: { width: 1360, height: 900 } });
  for (const sid of ['38900', '1165']) {
    await pg.goto(`file:///tmp/w8shot/reports/index_${sid}.html`, { waitUntil: 'networkidle' });
    await pg.waitForTimeout(400);
    // 暗色 default（root 值）
    await pg.screenshot({ path: `/tmp/w8shot/${sid}_dark.png` });
    // 亮色態
    await pg.evaluate(() => document.documentElement.setAttribute('data-theme', 'light'));
    await pg.waitForTimeout(250);
    await pg.screenshot({ path: `/tmp/w8shot/${sid}_light.png` });
    await pg.evaluate(() => document.documentElement.removeAttribute('data-theme'));
  }
  await b.close();
})();
'''
import os

env = dict(os.environ, NODE_PATH='/home/z/.npm-global/lib/node_modules')
r = subprocess.run(['node', '-e', NODE], capture_output=True, text=True, cwd='/tmp/w8shot', env=env)
print(r.stdout, r.stderr)
for p in sorted(TMP.glob('*.png')):
    print(p, p.stat().st_size)
