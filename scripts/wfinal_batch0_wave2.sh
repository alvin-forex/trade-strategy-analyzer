#!/bin/bash
# W-FINAL 批 0 第二波：forex_reports / ccy / portfolios / reviews / admin 特徵抽取
# 照 wfinal_batch0_root_v3.sh 同工序（全欄位 percent-encode，python 端 decode）
DOCS=/home/z/my-project/exchange-repo/docs
S=/home/z/my-project/exchange-repo/exchange/from_zcode/wfinal_batch0_shots_20261107
RAW=$S/batch0_wave2_raw.txt
: > "$RAW"
agent-browser set viewport 1440 900 >/dev/null 2>&1
total=0
for dir in forex_reports ccy portfolios reviews admin; do
  n=0
  for f in "$DOCS/$dir"/*.html; do
    [ -e "$f" ] || continue
    n=$((n+1)); total=$((total+1))
    agent-browser open "file://$f" >/dev/null 2>&1
    sleep 0.25
    line=$(agent-browser eval "var dh=getComputedStyle(document.documentElement),db=getComputedStyle(document.body),q=encodeURIComponent;[q(dh.backgroundColor),q(db.backgroundColor),q((dh.getPropertyValue('--card2')||'').trim()),q((dh.getPropertyValue('--accent')||'').trim()),q((dh.getPropertyValue('--accent2')||dh.getPropertyValue('--accent-2')||'').trim()),q(document.body.className),q(String(!!document.querySelector('nav,.nav,header.nav'))),q(String(document.body.classList.contains('has-sidebar'))),q((document.querySelector('h1')||{textContent:''}).textContent.slice(0,40))].join('|')" 2>/dev/null)
    line="${line#\"}"; line="${line%\"}"
    echo "$dir/$(basename "$f")|$line" >> "$RAW"
  done
  echo "FAMILY $dir DONE $n"
done
echo "BATCH0_WAVE2_DONE $total"
