#!/bin/bash
# 批1 四頁 NAV 統一——browser 閘（http server 版）＋8 截圖解鎖態
# Job 505164 / 2100 批示 / 2026-11-07 晚
# 升級：改用 python http.server（file:// 協定 CORS 封鎖 fetch——上次 projection
#       「TypeError＋空表」實錐係量測假象；live 200/200 已實證生產環境正常）
set -u
DOCS=/home/z/my-project/exchange-repo/docs
SHOTS=/home/z/my-project/scripts/scan_out/shots
RAW=/home/z/my-project/scripts/scan_out/batch1r2_browser_raw.txt
PORT=8899
mkdir -p "$SHOTS"; : > "$RAW"

# 解密版暫存原位（signal_ranking 解鎖態；round-trip 已證=現密文內容）
cp /tmp/sr_work/verify_plain.html "$DOCS/_zscan_signal_ranking.html"

python3 -m http.server $PORT --directory "$DOCS" --bind 127.0.0.1 >/dev/null 2>&1 &
SRV=$!
sleep 1.2

agent-browser set viewport 1440 900 >/dev/null 2>&1

MEASURE='var q=encodeURIComponent,d=document,b=d.querySelector(".nav"),dr=d.getElementById("navDrawer"),bg=d.getElementById("burgerBtn"),cur=d.querySelector(".nav>a[aria-current=\"page\"]"),sb=d.getElementById("sidebar-container"),tg=d.getElementById("theme-toggle"),tbl=d.querySelector("table tbody"),err=d.getElementById("err");[q(getComputedStyle(d.documentElement).backgroundColor),q(getComputedStyle(d.body).backgroundColor),q(getComputedStyle(d.documentElement).getPropertyValue("--card2").trim()),q(String(!!b)),q(String(b?b.querySelectorAll("a").length:0)),q(cur?cur.getAttribute("href"):""),q(String(dr&&dr.hidden)),q(String(bg?getComputedStyle(bg).display:"none")),q(String(!!sb)),q(String(tg&&getComputedStyle(tg).display!=="none")),q(String(tbl?tbl.children.length:-1)),q(err?err.textContent:"")].join("|")'

declare -a PAGES=(
  "forex_news.html|P1_forex_news"
  "ccy_power/index.html|P2_ccy_power"
  "projection.html|P3_projection"
  "_zscan_signal_ranking.html|P4_signal_ranking"
)
for entry in "${PAGES[@]}"; do
  pg="${entry%%|*}"; name="${entry##*|}"
  agent-browser open "http://127.0.0.1:$PORT/$pg" >/dev/null 2>&1
  sleep 1.5
  line=$(agent-browser eval "$MEASURE" 2>/dev/null)
  line="${line#\"}"; line="${line%\"}"
  echo "$name|$line" >> "$RAW"
  echo "MEASURE $name"
done

# ---------- 8 截圖（1440×900 頁首＋頁中 45%）----------
shot() {
  agent-browser open "http://127.0.0.1:$PORT/$1" >/dev/null 2>&1
  sleep 2.2
  agent-browser screenshot "$SHOTS/batch1r2_$2_top.png" >/dev/null 2>&1
  agent-browser eval "window.scrollTo(0, Math.floor(document.body.scrollHeight*0.45))" >/dev/null 2>&1
  sleep 0.6
  agent-browser screenshot "$SHOTS/batch1r2_$2_mid.png" >/dev/null 2>&1
  echo "SHOT $2"
}
shot "forex_news.html"               "P1_forex_news"
shot "ccy_power/index.html"          "P2_ccy_power"
shot "projection.html"               "P3_projection"
shot "_zscan_signal_ranking.html"    "P4_signal_ranking"

agent-browser close >/dev/null 2>&1
kill $SRV 2>/dev/null
rm -f "$DOCS/_zscan_signal_ranking.html"

echo "=== BROWSER RAW ==="
cat "$RAW"
echo "=== SHOTS ==="
ls -la "$SHOTS" | grep batch1r2
