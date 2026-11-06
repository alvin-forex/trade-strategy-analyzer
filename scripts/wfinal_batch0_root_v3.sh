#!/bin/bash
# W-FINAL 批 0 v3：root 族特徵抽取（全欄位 percent-encode，python 端 decode）
DOCS=/home/z/my-project/exchange-repo/docs
S=/home/z/my-project/exchange-repo/exchange/from_zcode/wfinal_batch0_shots_20261107
RAW=$S/batch0_root_raw.txt
: > "$RAW"
cd "$DOCS"
agent-browser set viewport 1440 900 >/dev/null 2>&1
n=0
for f in *.html; do
  n=$((n+1))
  agent-browser open "file://$DOCS/$f" >/dev/null 2>&1
  sleep 0.3
  line=$(agent-browser eval "var dh=getComputedStyle(document.documentElement),db=getComputedStyle(document.body),q=encodeURIComponent;[q(dh.backgroundColor),q(db.backgroundColor),q((dh.getPropertyValue('--card2')||'').trim()),q((dh.getPropertyValue('--accent')||'').trim()),q((dh.getPropertyValue('--accent2')||dh.getPropertyValue('--accent-2')||'').trim()),q(document.body.className),q(String(!!document.querySelector('nav,.nav,header.nav'))),q(String(document.body.classList.contains('has-sidebar'))),q((document.querySelector('h1')||{textContent:''}).textContent.slice(0,40))].join('|')" 2>/dev/null)
  line="${line#\"}"; line="${line%\"}"
  echo "$f|$line" >> "$RAW"
  if [ $((n % 30)) -eq 0 ]; then echo "PROGRESS $n/148"; fi
done
echo "BATCH0_V3_DONE $n"
