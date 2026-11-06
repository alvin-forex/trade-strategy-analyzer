#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tasks_board_gen.py v3——TASKS Board 生成器（Muse 規格 2026-10-29 版＋P3 NAV 方案 C 2026-11-04）。

老闆 07:43 落令：「個BOARD手機同電腦都唔能夠清晰顯示，你同MUSE執執要求，
叫ZCODE重構啦」→ Muse 設計已簽核（A1-A10 驗收）→ 本檔照 §六 checklist 落地。

Lane 分界（§6.1）：
- TASKS.md 內容＝DATA LANE（OpenClaw）——本檔零改動任務文字；
- 本檔＝CODE LANE（ZCODE）——解析＋渲染＋inline CSS＋可及性；
- 產出 docs/admin/tasks_board.html（plaintext）→ staticrypt owner 層（3.1）。

解析契約（§6.1，版本化——任何一邊改要通知另一邊）：
- `## <emoji> <標題>` 一個 section 一張卡；emoji 係狀態唯一來源（🔄👀⏸📅✅）；
  未知 emoji → fallback「其他」卡（§6.1 新增狀態規則）。
- 首個 `|` 表格：4 欄＝`#|任務|狀態|ETA`；2 欄＝`任務|證據`；欄數唔符 →
  降級兩欄（任務｜其餘串接）唔爆版（§1.2）。
- `- `／`1. ` 列表：無表格時用；有序保留編號（§6.1）。
- `> ` 首段＝頁面說明；`> 最後更新：…` 抽去 meta 列（§6.1）。
- 狀態格結論抽取（§1.3）：先 `**粗體**`；冇 → 第一個 `。`／`；` 前 ≤48 字；
  剩餘入 <details>（>70 字先摺，≤70 直接出）。

checklist 落點：1.1 emoji 配狀態｜1.2 降級｜1.3 fallback 25/25｜1.4 固定次序
active>owner>todo>sched>done｜2.1-2.10 照 prototype CSS＋minmax(0,…)／:not(.row-2)
中段斷點／code 12.5px／--neutral 標籤／reduced-motion fade 保留｜3.1 plaintext 出檔。
W5-I（2026-11-05）：站點 sidebar NAV 三件（../sidebar.css＋#sidebar-container＋
../sidebar.js，tokens 豁免——自帶 --l0 canonical 族）入本檔模板層——TASKS.md
重生成唔會沖走站點 NAV。
TBNAV A 案（2026-11-06 0922 老闆拍板「除 sidebar 留頂部 NAV」）：v3.3 起 W5-I
sidebar 三件自模板層移除（本檔即權威記錄）；方案 C 頂部 NAV（P3 拍板產物）
保留不動。sidebar.css/sidebar.js 站點全局唔掂——只係 board 呢頁唔再疊加。
P-1b（2026-11-05 1255 插隊令）：旗艦級金調 treatment——:root 擴 --gold/--gold2
canonical（board 零變量依賴慣例，主題 toggle 免疫）；h1 金漸層（@supports guard）；
active KPI 金＋金 glow；body 頂部金 radial 微光＋深藍黑底維持；卡影/hover 微升
（reduced-motion 守衛）；::selection/::focus-visible/scrollbar/footer 金點。
純 CSS 層改動——render_html 結構零改（A10 零 script 範圍照守）。

用法：
  python3 scripts/tasks_board_gen.py --tasks TASKS.md \
      --out docs/admin/tasks_board.html
"""
import argparse
import html
import re
import sys
from datetime import datetime

# ---- 契約常量（§6.1＋§1.4） --------------------------------------------
STATUS = {  # emoji → (status key, badge 符號, KPI 標籤)
    "🔄": ("active", "▶", "進行中"),
    "👀": ("owner", "!", "等你"),
    "⏸": ("todo", "◆", "待做"),
    "📅": ("sched", "↻", "已排程"),
    "✅": ("done", "✓", "已完成"),
}
ORDER = ["active", "owner", "todo", "sched", "done"]
OTHER = ("other", "◇", "其他")  # 未知 emoji fallback（§6.1）
GEN = "ZCODE tasks_board_gen v3.3（2026-11-06 TBNAV A 案：W5-I sidebar 三件除（老闆 0922 拍板除 sidebar 留頂部 NAV）；方案 C 頂部 NAV 保留；v3.2 旗艦金調＋A10 零 script 範圍照守）"

# ---- NAV BAR 方案 C（2026-11-04 P3 派工）----------------------------------
# 沿用首頁 docs/index.html 方案 C：sticky 48px、手機漢堡 drawer、aria-current。
# admin 層相對路徑重算：../index.html 等；admin 互連 tasks_board.html。
# 硬色值（零變量依賴）：board --l1/--line/--t2/--info 對應 #161E2E/#2A3650/#A8B4C4/#5CA8FF。
NAV_CSS = """
/* ==== NAV BAR 方案 C（2026-11-04 P3，ZCODE；沿用首頁）==== */
.nav{position:sticky;top:0;z-index:50;display:flex;align-items:stretch;height:48px;background:#161E2E;border-bottom:1px solid #2A3650;padding:0 16px;overflow-x:auto;overflow-y:hidden}
.nav a{display:inline-flex;align-items:center;padding:0 12px;color:#A8B4C4;font-size:14px;font-weight:500;white-space:nowrap;border-bottom:2px solid transparent;transition:color .15s,border-color .15s;text-decoration:none}
.nav a:hover{color:#E6EDF5}
.nav a[aria-current="page"]{color:#5CA8FF;font-weight:700;border-bottom-color:#5CA8FF}
.navdrawer{position:fixed;inset:0;z-index:220;background:rgba(10,14,20,.88);display:flex;flex-direction:column;align-items:stretch;justify-content:center;padding:32px}
.navdrawer[hidden]{display:none}
.navdrawer nav{display:flex;flex-direction:column;gap:8px;max-width:420px;margin:0 auto;width:100%}
.navdrawer a{display:flex;align-items:center;height:56px;padding:0 16px;background:#161E2E;border:1px solid #2A3650;border-radius:6px;color:#E6EDF5;font-size:16px;font-weight:500;text-decoration:none}
.navdrawer a[aria-current="page"]{color:#5CA8FF;font-weight:700;border-color:#5CA8FF}
.navdrawer-x{position:absolute;top:16px;right:16px;width:44px;height:44px;border:1px solid #2A3650;border-radius:6px;background:#161E2E;color:#E6EDF5;font-size:18px;cursor:pointer}
.burger{display:none}
@media(max-width:640px){
 .nav{display:none}
 .burger{display:block;position:fixed;top:8px;right:10px;z-index:60;width:40px;height:40px;border:1px solid #2A3650;border-radius:8px;background:#161E2E;color:#E6EDF5;font-size:18px;cursor:pointer}
}
"""

# NAV 清單：ADMIN_CUR=本頁高亮任務板（board 用）；projection 等無對應項時用 NAV_HTML 零 aria-current
_NAV_ITEMS = [
    ("../index.html", "首頁"),
    ("../signal_ranking.html", "排名"),
    ("../forex_news.html", "新聞"),
    ("../ccy_power/index.html", "CCY"),
    ("tasks_board.html", "任務板"),
    ("../tug_of_war_calculator.html", "工具"),
]

def _nav_html(current_href=None):
    a = lambda h, t: ('<a href="%s"%s>%s</a>' % (h, ' aria-current="page"' if h == current_href else '', t))
    items = "".join(a(h, t) for h, t in _NAV_ITEMS)
    return ('<nav class="nav" aria-label="主導航">%s</nav>'
            '<div id="navDrawer" class="navdrawer" hidden role="dialog" aria-modal="true" aria-label="導航選單">'
            '<button id="navDrawerClose" class="navdrawer-x" aria-label="關閉導航">✕</button>'
            '<nav aria-label="主導清單（手機）">%s</nav></div>'
            '<button id="burgerBtn" class="burger" aria-label="開啟導航" aria-expanded="false">☰</button>'
            % (items, items))

NAV_HTML_BOARD = _nav_html("tasks_board.html")   # 任務板頁：任務板項高亮
NAV_HTML_PLAIN = _nav_html(None)                 # 其他 admin 頁：無對應項不設 aria-current

NAV_JS = ("(function(){"
          "var d=document.getElementById('navDrawer'),b=document.getElementById('burgerBtn'),x=document.getElementById('navDrawerClose');"
          "if(!d||!b||!x)return;"
          "var bar=[].map.call(document.querySelectorAll('.nav>a'),function(a){return a.getAttribute('href')});"
          "var dr=[].map.call(document.querySelectorAll('.navdrawer nav>a'),function(a){return a.getAttribute('href')});"
          "if(JSON.stringify(bar)!==JSON.stringify(dr))console.error('[nav] bar/drawer 清單唔一致',bar,dr);"
          "function open(){d.hidden=false;b.setAttribute('aria-expanded','true');x.focus()}"
          "function close(){d.hidden=true;b.setAttribute('aria-expanded','false');b.focus()}"
          "b.addEventListener('click',open);x.addEventListener('click',close);"
          "d.addEventListener('click',function(e){if(e.target===d)close()});"
          "document.addEventListener('keydown',function(e){if(e.key==='Escape'&&!d.hidden)close()});"
          "})();")


# ---- 解析層 ------------------------------------------------------------
def parse_tasks_md(text):
    """TASKS.md → page dict（desc/updated/sections）。零內容改動。"""
    parts = re.split(r"\n## ", text)  # §1.1 保留現有 split 行為
    intro = parts[0]
    desc, updated = "", ""
    for line in intro.splitlines():
        line = line.strip()
        if line.startswith(">"):
            inner = line[1:].strip()
            m = re.match(r"最後更新[：:]\s*(.+)", inner)
            if m:
                updated = m.group(1).strip()
            elif inner and not desc:
                desc = inner
    sections = []
    for part in parts[1:]:
        part = part.strip()
        if not part:
            continue
        lines = part.splitlines()
        head = lines[0].strip()
        m = re.match(r"^(\S+)\s*(.*)$", head)
        emoji, title = (m.group(1), m.group(2).strip()) if m else ("", head)
        info = STATUS.get(emoji, OTHER)
        body = lines[1:]
        sections.append({"emoji": emoji, "title": title, "status": info[0],
                         "sym": info[1], "kpi": info[2], "body": body})
    return {"desc": desc, "updated": updated, "sections": sections}


def _inline_md(s):
    """**粗體**→strong；`code`→code。先 HTML escape（安全第一）。"""
    s = html.escape(s, quote=False)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
    s = re.sub(r"`([^`]+)`", r"<code>\1</code>", s)
    return s


def _concl_split(cell):
    """§1.3 狀態格結論抽取：先 **粗體**；冇 → 第一個 。／； 前 ≤48 字。

    回傳 (concl_html, fdb_html or None)。fallback 全覆蓋——冇粗體冇句讀 →
    頭 48 字；總長 ≤70 字唔摺（checklist 2.5）。
    """
    raw = cell.strip()
    if not raw:
        return "", None
    mb = re.match(r"^\*\*([^*]+)\*\*(.*)$", raw)
    if mb:
        concl = mb.group(1).strip()
        rest = mb.group(2).strip().lstrip("，,").strip()
    else:
        m = re.match(r"^([^。；]{1,48})[。；]?(.*)$", raw)
        concl = m.group(1).strip() if m else raw[:48]
        rest = (m.group(2).strip() if m else raw[48:]).strip()
    concl_len = len(concl)
    total = len(raw)
    fold = total > 70 or bool(rest)
    return _inline_md(concl), (_inline_md(rest) if rest else None) if fold else None


def _table_rows(body):
    """表格行 → [cells]。剝 |---|---| 分隔線（§1.2）。"""
    rows = []
    for ln in body:
        ln = ln.strip()
        if not ln.startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip("|").split("|")]
        if all(re.fullmatch(r":?-{3,}:?", c) for c in cells if c):
            continue
        rows.append(cells)
    return rows


def _list_items(body):
    """- ／1. 列表 → [(text, num or None)]。有序保留原編號（§6.1）。"""
    out = []
    for ln in body:
        ln = ln.strip()
        m = re.match(r"^(\d+)[.、]\s*(.+)$", ln)
        if m:
            out.append((m.group(2), m.group(1)))
            continue
        m = re.match(r"^[-*]\s+(.+)$", ln)
        if m:
            out.append((m.group(1), None))
    return out


# ---- 渲染層 ------------------------------------------------------------
CSS = """
:root{
 --l0:#0F1520;--l1:#161E2E;--l2:#1C2638;--line:#2A3650;--line2:#3A4760;
 --t1:#E6EDF5;--t2:#A8B4C4;--t3:#7A8698;
 --ok:#3DDC84;--warn:#FFB454;--danger:#FF6B6B;--info:#5CA8FF;--neutral:#8B95A5;
 --gold:#FFD700;--gold2:#EAB308;
 --r:14px;
}
*{box-sizing:border-box}
body{margin:0;padding:24px 16px 48px;color:var(--t1);
 background:radial-gradient(1100px 420px at 50% -120px,rgba(255,215,0,.05),transparent 62%),var(--l0);
 font:15px/1.65 -apple-system,"PingFang TC","Noto Sans CJK TC","Microsoft JhengHei",sans-serif;
 -webkit-text-size-adjust:100%}
.wrap{max-width:1240px;margin:0 auto}
h1{font-size:28px;line-height:1.3;margin:0 0 8px;font-weight:800;letter-spacing:-.3px;color:var(--gold)}
@supports ((-webkit-background-clip:text) or (background-clip:text)){
 h1{background:linear-gradient(115deg,#FFE566 0%,#FFD700 45%,#EAB308 100%);
   -webkit-background-clip:text;background-clip:text;color:transparent}
}
.meta{color:var(--t2);font-size:13px;line-height:1.7;margin:0 0 18px;padding-bottom:12px;
 border-bottom:1px solid rgba(255,215,0,.22)}
.kpis{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:8px;margin-bottom:20px}
.kpi{background:linear-gradient(180deg,var(--l2) 0%,var(--l1) 58%);border:1px solid var(--line);
 border-radius:12px;padding:10px 12px;
 display:flex;flex-direction:column;gap:2px;border-left-width:3px;min-width:0;
 box-shadow:0 6px 18px rgba(3,7,15,.35)}
.kpi-n{font-size:23px;font-weight:700;line-height:1.1;font-variant-numeric:tabular-nums}
.kpi-l{font-size:12px;color:var(--t2);white-space:nowrap}
.kpi--active{border-left-color:var(--gold)}
.kpi--active .kpi-n{color:var(--gold);text-shadow:0 0 16px rgba(255,215,0,.32)}
.kpi--owner{border-left-color:var(--warn)}.kpi--owner .kpi-n{color:var(--warn)}
.kpi--todo{border-left-color:var(--neutral)}.kpi--todo .kpi-n{color:var(--t1)}
.kpi--sched{border-left-color:var(--line2)}.kpi--sched .kpi-n{color:var(--t2)}
.kpi--done{border-left-color:var(--ok)}.kpi--done .kpi-n{color:var(--t3)}
.kpi--other{border-left-color:var(--line2)}.kpi--other .kpi-n{color:var(--t2)}

.board{display:grid;grid-template-columns:repeat(12,minmax(0,1fr));gap:16px;align-items:start}
.card{background:var(--l1);border:1px solid var(--line);border-radius:var(--r);
 padding:16px 18px 18px;min-width:0;border-top-width:3px;
 box-shadow:0 10px 28px rgba(3,7,15,.42)}
@media(hover:hover) and (prefers-reduced-motion:no-preference){
 .card{transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease}
 .card:hover{transform:translateY(-2px);border-color:var(--line2);
  box-shadow:0 14px 34px rgba(3,7,15,.50)}
}
.card--active{grid-column:span 7;border-top-color:var(--info)}
.card--owner{grid-column:span 5;border-top-color:var(--warn)}
.card--todo{grid-column:span 5;border-top-color:var(--neutral)}
.card--sched{grid-column:span 7;border-top-color:var(--line2)}
.card--done{grid-column:span 12;border-top-color:rgba(61,220,132,.45)}
.card--other{grid-column:span 12;border-top-color:var(--line2)}
/* P-1b 旗艦金調：active 卡計數徽章金色點綴（數據強調） */
.card--active .cnt{color:var(--gold);border-color:rgba(255,215,0,.38)}

.card-hd{display:flex;align-items:center;gap:10px;margin-bottom:12px;flex-wrap:wrap}
.card-hd h2{font-size:17px;font-weight:700;margin:0;line-height:1.4;letter-spacing:-.1px}
.cnt{margin-left:auto;font-size:12px;color:var(--t2);background:var(--l2);
 border:1px solid var(--line);border-radius:999px;padding:1px 9px;font-variant-numeric:tabular-nums;
 white-space:nowrap}
.badge{display:inline-flex;align-items:center;gap:5px;font-size:12px;font-weight:700;
 padding:2px 9px 2px 7px;border-radius:6px;white-space:nowrap;letter-spacing:.3px}
.badge i{font-style:normal;font-size:12px;line-height:1}
.badge--active{background:rgba(92,168,255,.16);color:#9CCBFF;border:1px solid rgba(92,168,255,.5)}
.badge--owner{background:rgba(255,180,84,.16);color:#FFD79A;border:1px solid rgba(255,180,84,.55)}
.badge--todo{background:transparent;color:var(--t2);border:1px dashed var(--line2)}
.badge--sched{background:transparent;color:var(--t2);border:1px solid var(--line2)}
.badge--done{background:transparent;color:var(--neutral);border:1px solid var(--line)}
.badge--other{background:transparent;color:var(--t2);border:1px solid var(--line2)}

.rows{display:block;min-width:0}
.row{display:grid;grid-template-columns:26px minmax(0,205px) minmax(0,1fr) 82px;
 gap:12px;padding:10px 0;border-bottom:1px solid rgba(42,54,80,.75);align-items:start}
.row:last-child{border-bottom:0;padding-bottom:2px}
/* P-1b：列 hover 掃讀底色（懸停裝置限定） */
@media(hover:hover){.row:not(.row-hd):hover{background:rgba(28,38,56,.32)}}
/* 1945 notes②：表頭 meta neutral(#8B95A5)≈5.5:1 偏淺→t2(#A8B4C4)≈8.7:1；
   「偏密」→padding 6→8px＋letter-spacing .4→.5px */
.row-hd{font-size:12px;color:var(--t2);padding:0 0 8px;border-bottom:1px solid var(--line);
 letter-spacing:.5px}
.row-hd .c{font-size:12px}
/* P4（11-04 派工 330a0094）：任務卡證據偏向一邊浪費空間——比例 task:ev
   1.15:1 → 1:1.6（ev 欄佔比 46.5%→61.5%）；760px 以下單欄由既有
   @media(max-width:767px) 斷點涵蓋，唔新增斷點 */
.row-2{grid-template-columns:minmax(0,1fr) minmax(0,1.6fr)}
.c{min-width:0;overflow-wrap:anywhere;padding-right:10px}
.c p{margin:0}
.t{font-size:15px;font-weight:600;line-height:1.5;overflow-wrap:anywhere;word-break:break-word;padding-right:2px}
/* 16:40 量測回批 (1)：390px 長任務名（中英＋全角＋混合）scrollWidth 329>326 差 3px——
   曾照 OpenClaw 建議用 break-all；1945 notes① 實測副作用＝英文單字「Copilot」被斷
   「Co／pilot」。改 anywhere：min-content 計算同樣可斷（防溢出等效、3px 問題不回頭），
   但只喺必要時先斷——英文單字完整、CJK 照常斷 */
/* 10-31 上線同步：OpenClaw 0130 建議 (2) letter-spacing:-.2px（Chrome 全形「＋」cluster
   3px artifact 兜底）——preview 軌 1355 出貨已實測歸零，生成器跟上防重生成走回頭 */
.c-task .t{overflow-wrap:anywhere;word-break:normal;letter-spacing:-.2px}
.concl{font-size:14px;line-height:1.6;color:var(--t1);overflow-wrap:anywhere}
.chip{display:inline-block;font-size:12px;color:var(--t2);background:var(--l2);
 border:1px solid var(--line);border-radius:6px;padding:1px 7px;white-space:normal}
/* 1945 notes② 同批：序號同表頭同級 12px 灰字——neutral→t2 保持一致 */
.c-idx{font-size:12px;color:var(--t2);font-variant-numeric:tabular-nums;padding-top:3px}
.ev{font-size:13px;color:var(--t2)}
code{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px;
 background:var(--l2);border:1px solid var(--line);border-radius:4px;padding:0 3px;
 overflow-wrap:anywhere}
details.fd{margin:0}
details.fd>summary{list-style:none;cursor:pointer;position:relative;padding:10px 20px 10px 0;min-height:44px;display:flex;align-items:center}
details.fd>summary::-webkit-details-marker{display:none}
details.fd>summary::after{content:"＋";position:absolute;right:0;top:50%;transform:translateY(-50%);color:var(--info);font-size:12px}
details.fd[open]>summary::after{content:"－"}
.fdb{margin:6px 0 0;font-size:13px;line-height:1.7;color:var(--t2);overflow-wrap:anywhere}
.bul{margin:0;padding:0;list-style:none}
.bul li{position:relative;padding:7px 0 7px 16px;border-bottom:1px solid rgba(42,54,80,.75);
 font-size:14px;line-height:1.65;min-width:0;overflow-wrap:anywhere}
.bul li:last-child{border-bottom:0}
.bul li::before{content:"·";position:absolute;left:3px;color:var(--t3);font-weight:700}
.bul li .num{color:var(--warn);font-weight:700;margin-right:2px}
.card--owner .bul li::before{content:"▸";color:var(--warn);font-size:12px;left:0;top:9px}
.fold-sum{list-style:none;cursor:pointer;display:flex;align-items:center;gap:10px;flex-wrap:wrap;min-height:44px;padding:4px 0}
.fold-sum::-webkit-details-marker{display:none}
.fold-sum .card-hd{margin:0;flex:1;min-width:0}
.fold-hint{font-size:12px;color:var(--info);margin-left:auto;white-space:nowrap}
.fold-hint::after{content:" ▾"}
details.card--done[open] .fold-hint::after{content:" ▴"}
details.card--done[open] .rows{margin-top:14px}
details.card--done .rows{margin-top:0}
/* 1945 notes③：footer 12px t3(#7A8698)≈4.95:1 偏細偏淺→13px t2≈8.7:1 */
.foot{text-align:center;color:var(--t2);font-size:13px;margin-top:24px;line-height:1.7}
/* P-1b 旗艦金調：選取色／焦點環／滾動條／footer 金點 */
::selection{background:rgba(255,215,0,.30);color:var(--t1)}
details.fd>summary:focus-visible{outline:2px solid var(--gold);outline-offset:2px;border-radius:4px}
.fold-sum:focus-visible{outline:2px solid var(--gold);outline-offset:2px}
@media(pointer:fine){
 ::-webkit-scrollbar{width:10px;height:10px}
 ::-webkit-scrollbar-thumb{background:var(--l2);border-radius:6px;border:2px solid var(--l0)}
 ::-webkit-scrollbar-thumb:hover{background:var(--line2)}
 ::-webkit-scrollbar-track{background:transparent}
}
.foot::before{content:"◆";color:var(--gold);font-size:9px;margin-right:7px;vertical-align:1px}

@media (min-width:768px) and (max-width:1199px){
 .row:not(.row-2){grid-template-columns:24px minmax(0,180px) minmax(0,1fr) 76px;gap:10px}
}
@media (max-width:1023px){
 .board{grid-template-columns:minmax(0,1fr)}
 .card--active,.card--owner,.card--todo,.card--sched,.card--done,.card--other{grid-column:span 1}
}
@media (max-width:767px){
 body{padding:16px 12px 40px;font-size:15px}
 h1{font-size:22px}
 .kpis{grid-template-columns:repeat(5,minmax(0,1fr));gap:5px}
 .kpi{padding:8px 6px;border-radius:10px}
 .kpi-n{font-size:18px}
 .kpi-l{font-size:12px;letter-spacing:-.3px;line-height:1.25}
 .card{padding:14px 14px 16px;border-radius:12px}
 .card-hd{gap:8px;margin-bottom:12px}
 .card-hd h2{font-size:16px}
 .row-hd{display:none}
 .row{grid-template-columns:minmax(0,1fr);gap:6px;padding:10px 0}
 .row-2{grid-template-columns:minmax(0,1fr);gap:4px}
 details.fd>summary{padding:6px 20px 6px 0}
 .c-idx{display:none}
 .c-state::before,.c-ev::before,.c-eta::before{content:attr(data-l);display:block;
  font-size:12px;color:var(--t2);letter-spacing:.5px;margin-bottom:2px}
 .c-state{padding-left:10px;border-left:2px solid var(--line2)}
 .c-task::before{display:none}
 .t{font-size:15px}
 .concl{font-size:14px}
 .chip{font-size:12.5px;padding:2px 8px}
 .ev{font-size:13.5px}
 .fold-hint{font-size:12.5px}
}
@media (max-width:359px){
 .kpis{grid-template-columns:repeat(3,minmax(0,1fr))}
 .kpi-l{font-size:12px}
}
@media (prefers-reduced-motion:no-preference){details.fd[open] .fdb{animation:fi .16s ease-out}}
@keyframes fi{from{opacity:.4}to{opacity:1}}
"""


def _render_state_cell(cell):
    """狀態格：concl＋（長內文）details（§1.3／checklist 2.5）。"""
    concl, fdb = _concl_split(cell)
    if fdb is None:
        return '<p class="concl">%s</p>' % concl
    return ('<details class="fd"><summary><span class="concl">%s</span></summary>'
            '<div class="fdb">%s</div></details>' % (concl, fdb))


def _render_section(sec, idx_total):
    """一個 section → 一張卡 HTML。"""
    st, sym, kpi = sec["status"], sec["sym"], sec["kpi"]
    title = _inline_md(sec["title"]) or kpi
    rows = _table_rows(sec["body"])
    items = _list_items(sec["body"])
    n = 0
    body_html = ""
    if rows:
        header, data = rows[0], rows[1:]
        if len(header) == 4:  # #|任務|狀態|ETA
            body_html = ('<div class="rows" role="table" aria-label="%s">'
                         '<div class="row row-hd" role="row">'
                         '<div class="c c-0" role="columnheader">#</div>'
                         '<div class="c c-1" role="columnheader">任務</div>'
                         '<div class="c c-2" role="columnheader">狀態</div>'
                         '<div class="c c-3" role="columnheader">ETA</div></div>'
                         % html.escape(sec["title"] or kpi, quote=False))
            for i, r in enumerate(data, 1):
                task = _inline_md(r[1]) if len(r) > 1 else ""
                state = r[2] if len(r) > 2 else ""
                eta = _inline_md(r[3]) if len(r) > 3 else ""
                body_html += ('<div class="row" role="row">'
                              '<div class="c c-idx" role="cell">%d</div>'
                              '<div class="c c-task" role="cell" data-l="任務"><p class="t">%s</p></div>'
                              '<div class="c c-state" role="cell" data-l="狀態">%s</div>'
                              '<div class="c c-eta" role="cell" data-l="ETA"><span class="chip">%s</span></div></div>'
                              % (i, task, _render_state_cell(state), eta))
            n = len(data)
        else:  # 2 欄 任務|證據；欄數唔符 → 降級（任務｜其餘串接）§1.2
            body_html = ('<div class="rows" role="table" aria-label="%s">'
                         '<div class="row row-hd" role="row">'
                         '<div class="c c-0" role="columnheader">任務</div>'
                         '<div class="c c-1" role="columnheader">證據</div></div>'
                         % html.escape(sec["title"] or kpi, quote=False))
            for r in data:
                task = _inline_md(r[0]) if r else ""
                ev = _inline_md(" ｜ ".join(r[1:])) if len(r) > 1 else ""
                body_html += ('<div class="row row-2" role="row">'
                              '<div class="c c-task" role="cell" data-l="任務"><p class="t">%s</p></div>'
                              '<div class="c c-ev" role="cell" data-l="證據"><span class="ev">%s</span></div></div>'
                              % (task, ev))
            n = len(data)
        body_html += "</div>"
    elif items:
        body_html = '<ul class="bul">'
        for text, num in items:
            nnum = '<b class="num">%s</b> ' % html.escape(num) if num else ""
            body_html += "<li>%s%s</li>" % (nnum, _inline_md(text))
        body_html += "</ul>"
        n = len(items)
    hd = ('<div class="card-hd"><span class="badge badge--%s"><i>%s</i>%s</span>'
          '<h2>%s</h2><span class="cnt">%d</span></div>' % (st, sym, kpi, title, n))
    if st == "done":  # checklist 2.4 完成卡摺疊
        return ('<details class="card card--done"><summary class="fold-sum">%s'
                '<span class="fold-hint">展開</span></summary>%s</details>'
                % (hd, body_html))
    return '<section class="card card--%s">%s%s</section>' % (st, hd, body_html)


def render_html(page, now_str):
    """page dict → 完整 HTML（零 script——A10）。"""
    secs = sorted(page["sections"],
                  key=lambda s: ORDER.index(s["status"]) if s["status"] in ORDER else len(ORDER))
    kpi_counts = {}
    for s in page["sections"]:
        k = s["status"]
        if rows_of := _table_rows(s["body"]):
            cnt = len(rows_of) - 1
        else:
            cnt = len(_list_items(s["body"]))
        kpi_counts[k] = kpi_counts.get(k, 0) + max(cnt, 0)
    kpi_html = ""
    order_all = ORDER + (["other"] if "other" in kpi_counts else [])
    for k in order_all:
        if k not in kpi_counts:
            continue
        sym = next((s["sym"] for s in page["sections"] if s["status"] == k), OTHER[1])
        lab = next((s["kpi"] for s in page["sections"] if s["status"] == k), OTHER[2])
        kpi_html += ('<div class="kpi kpi--%s"><span class="kpi-n">%d</span>'
                     '<span class="kpi-l">%s %s</span></div>' % (k, kpi_counts[k], sym, lab))
    meta_bits = []
    if page["desc"]:
        meta_bits.append(html.escape(page["desc"], quote=False))
    if page["updated"]:
        meta_bits.append("最後更新：" + html.escape(page["updated"], quote=False))
    cards = "\n".join(_render_section(s, i) for i, s in enumerate(secs))
    return ("<!DOCTYPE html><html lang=\"zh-Hant\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            "<title>📋 任務看板 TASKS Board</title><style>%s%s</style>"
            "<!-- TBNAV A 案（2026-11-06 老闆拍板）：W5-I sidebar.css 三件已除，方案 C 頂部 NAV 唯一導航 -->\n"
            "</head><body>\n\n"
            "%s"
            "<div class=\"wrap\"><h1>📋 任務看板 TASKS Board</h1>"
            "<div class=\"meta\">%s</div>"
            "<div class=\"kpis\">%s</div>"
            "<div class=\"board\">%s</div>"
            "<div class=\"foot\">auto-generated from TASKS.md · %s · %s</div>"
            "</div>"
            "<script>%s</script>\n</body></html>"
            % (CSS, NAV_CSS, NAV_HTML_BOARD, " · ".join(meta_bits), kpi_html, cards, now_str, GEN, NAV_JS))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tasks", required=True, help="TASKS.md 路徑（DATA lane 產物）")
    ap.add_argument("--out", default="docs/admin/tasks_board.html",
                    help="plaintext HTML 輸出（staticrypt 前一步，§3.1）")
    args = ap.parse_args()
    with open(args.tasks, encoding="utf-8") as f:
        text = f.read()
    page = parse_tasks_md(text)
    if not page["sections"]:
        print("❌ TASKS.md 無 `## <emoji> <標題>` section——解析契約見規格 §6.1", file=sys.stderr)
        sys.exit(1)
    out = render_html(page, datetime.now().strftime("%Y-%m-%d %H:%M HKT"))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(out)
    fb = sum(1 for s in page["sections"]
             for r in _table_rows(s["body"])[1:] if len(r) > 2
             for c in [r[2]] if "**" not in c)
    print("✅ %s（%d sections｜狀態格 fallback 粗體缺失 %d 行——§1.3 覆蓋率驗收用）"
          % (args.out, len(page["sections"]), fb))


if __name__ == "__main__":
    main()
