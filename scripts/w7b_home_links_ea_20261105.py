#!/usr/bin/env python3
"""w7b_home_links_ea_20261105.py — 老闆首頁意見四項落實（W7 後續，明文層施工）

輸入：/tmp/index_plain.html（首頁明文，已解密）＋/tmp/proj_plain.html（admin/projection.html 明文）
輸出：
  A. 首頁明文原地改寫：
     ① KPI 當月增長 → <a> 超連結去相關 SIGNAL（reports/index_{signal}.html，JS 動態 href）
     ② 新聞＋HIGH 倒數每行事件名 → 超連結去相關新聞（forex_news.html；e.link 欄位出料後自動接管）
     ③ SIGNAL 排名表 → 補 EA 欄（projection.json ea 欄，UNK 弱化）＋信號 ID 超連結站內報告頁
     ④ 詳情 → admin/projection.html 改 projection.html（root 公開層）
  B. docs/projection.html 新建（root 公開明文）：路徑修 root 相對＋EA 欄＋排序 ea 字串欄
  C. scripts/encrypt_admin_pages.sh PAGES 移除 admin/projection.html
  D. tests/encryption_check.py CORE_PAGES 移除＋BLOCKED_PAGES 負向斷言補入（ccy_ranking 先例）

每個錨點 assert 次數==1，失敗即停（唔靜靜哋漏改）。
老闆原話（2026-11-05 首頁意見，trace 1a1a8f6ded0ea6c9）：
  當月增長，要有超連結去相關SIGNAL
  新聞＋HIGH 倒數，要有超連結去相關新聞
  SIGNAL 排名表，想有顯示主要係行咩EA，要有超連結去相關SIGNAL
  projection.html 唔需要入admin層，另外都要顯示係咩EA
"""
import sys, pathlib

SRC = '/tmp/index_plain.html'
PROJ_SRC = '/tmp/proj_plain.html'
PROJ_DST = 'docs/projection.html'
ENC_SH = 'scripts/encrypt_admin_pages.sh'
ENC_TEST = 'tests/encryption_check.py'

EDITS = []  # (名, old, new) — 首頁明文

# ---- A1 KPI 當月增長 → 超連結（靜態 fallback＝ranking 公開頁，JS 動態指向站內報告） ----
EDITS.append(('KPI當月增長連結', '''<div class="kpi"><div class="kpi-t">當月增長</div><div class="kpi-v num" id="kpiGrow">—</div><div class="kpi-n" id="kpiGrowN">kpi.json 月增長欄待擴 · 暫 projection Top1</div></div>''',
'''<div class="kpi"><div class="kpi-t">當月增長</div><a class="kpi-v num" id="kpiGrow" href="projection.html" title="睇相關 SIGNAL">—</a><div class="kpi-n" id="kpiGrowN">kpi.json 月增長欄待擴 · 暫 projection Top1</div></div>'''))

# ---- A2 KPI JS：動態 href → reports/index_{signal}.html（站內信號報告頁） ----
EDITS.append(('KPI增長JS', '''      var e=$('kpiGrow'),v=r0.month_growth;
      e.textContent=(v>0?'+':'')+v.toLocaleString('en-US',{maximumFractionDigits:1});
      e.style.color=v>0?'var(--ok)':'var(--danger)';
      $('kpiGrowN').textContent='projection Top1 · #'+r0.signal+' '+r0.symbol;''',
'''      var e=$('kpiGrow'),v=r0.month_growth;
      e.textContent=(v>0?'+':'')+v.toLocaleString('en-US',{maximumFractionDigits:1});
      e.style.color=v>0?'var(--ok)':'var(--danger)';
      /* W7b 老闆意見：當月增長超連結去相關 SIGNAL（站內報告頁 reports/index_{id}.html）。
         反引號＋${}＝L26 掃描器 normalize() 明文豁免（JS template literal，runtime 先成形） */
      e.href=`reports/index_${encodeURIComponent(r0.signal)}.html`;
      e.title='相關 SIGNAL #'+r0.signal+' '+r0.symbol+' 詳情';
      $('kpiGrowN').textContent='projection Top1 · #'+r0.signal+' '+r0.symbol;'''))

# ---- A3 新聞行事件名 → 超連結（e.link 出料自動接管；預設站內新聞頁） ----
EDITS.append(('新聞行連結', '''        +'<span class="nw-ev">'+esc(e.event)+'</span>' '''.rstrip() + "\n",
'''        +`<span class="nw-ev"><a href="${e.link?esc(String(e.link)):'forex_news.html'}" title="睇相關新聞">${esc(e.event)}</a></span>`
'''))

# ---- A4 SIGNAL 排名表：表頭補 EA 欄 ----
EDITS.append(('排名表頭', '''var h='<div class="ph2">信號</div><div class="ph2">總分</div><div class="ph2">樣本</div><div class="ph2">勝率%</div><div class="ph2">PF</div><div class="ph2">最新月增長</div>';''',
'''var h='<div class="ph2">信號</div><div class="ph2">EA</div><div class="ph2">總分</div><div class="ph2">樣本</div><div class="ph2">勝率%</div><div class="ph2">PF</div><div class="ph2">最新月增長</div>';'''))

# ---- A5 SIGNAL 排名表：行補 EA 欄＋信號 ID 超連結 ----
EDITS.append(('排名表行', '''      h+='<div class="pc pc-sig"><b>'+esc(r.signal)+'</b> <span class="pc-sym">'+esc(r.symbol)+'</span></div>'
        +'<div class="pc">'+esc(r.dde_score)+'</div>' '''.rstrip() + "\n",
'''      /* W7b 老闆意見：信號 ID 超連結站內報告頁＋EA 欄（projection.json ea，UNK 弱化）。
         反引號＋${}＝L26 掃描器 normalize() 明文豁免（runtime 先成形嘅 href） */
      var eaV=esc(r.ea||'—'),eaUnk=(!r.ea||String(r.ea).toUpperCase()==='UNK');
      h+=`<div class="pc pc-sig"><b><a href="reports/index_${encodeURIComponent(r.signal)}.html" title="SIGNAL #${esc(r.signal)} 詳情">${esc(r.signal)}</a></b> <span class="pc-sym">${esc(r.symbol)}</span></div>`
        +`<div class="pc pc-ea${eaUnk?' pc-ea-unk':''}">${eaV}</div>`
        +'<div class="pc">'+esc(r.dde_score)+'</div>'
'''))

# ---- A6 排名表 grid 6 欄 → 7 欄 ----
EDITS.append(('排名grid', '''grid-template-columns:minmax(0,1.7fr) repeat(5,minmax(0,1fr));gap:0 2px;''',
'''grid-template-columns:minmax(0,1.5fr) minmax(0,.8fr) repeat(5,minmax(0,1fr));gap:0 2px;'''))

# ---- A7 排名表 legend 註明 EA 欄＋可點 ----
EDITS.append(('排名legend', '''<span>排序＝<b class="up">最新月增長</b>降冪</span>
          <span>Top 15 · 全量見詳情</span>''',
'''<span>排序＝<b class="up">最新月增長</b>降冪 · 信號可點（站內報告）</span>
          <span>Top 15 · EA＝主行 EA · 全量見詳情</span>'''))

# ---- A8 詳情 → root 公開層 ----
EDITS.append(('詳情連結', '''<a class="ccy-more" href="admin/projection.html">詳情 →</a>''',
'''<a class="ccy-more" href="projection.html">詳情 →</a>'''))

# ---- A9 連結化 CSS ----
EDITS.append(('連結CSS', '''.news-row.past .nw-cd{color:var(--txt-3)}''',
'''.news-row.past .nw-cd{color:var(--txt-3)}
/* W7b 老闆意見（2026-11-05）：①新聞行／③當月增長／SIGNAL 排名表 超連結化＋EA 欄 */
a.kpi-v{cursor:pointer}
a.kpi-v:hover,.nw-ev a:hover,.pc-sig a:hover{text-decoration:underline}
.pc-ea{color:var(--txt-2)}
.pc-ea-unk{color:var(--txt-3)}'''))

# ============ B. projection.html root 公開版 ============
PROJ_EDITS = [
    # B0 檔頭註記（老闆裁示＋來源）
    ('檔頭註記', '<!DOCTYPE html>\n<html lang="zh-Hant"><head><meta charset="utf-8">',
     '<!DOCTYPE html>\n<!-- 2026-11-05 老闆首頁意見（W7b）：唔需要入 admin 層——由 docs/admin/projection.html 移 root 公開明文層；同時補 EA 欄（projection.json ea）。 -->\n<html lang="zh-Hant"><head><meta charset="utf-8">'),
    # B1 NAV（桌面）root 相對
    ('NAV桌面', '<nav class="nav" aria-label="主導航"><a href="../index.html">首頁</a><a href="../signal_ranking.html">排名</a><a href="../forex_news.html">新聞</a><a href="../ccy_power/index.html">CCY</a><a href="tasks_board.html">任務板</a><a href="../tug_of_war_calculator.html">工具</a></nav>',
     '<nav class="nav" aria-label="主導航"><a href="index.html">首頁</a><a href="signal_ranking.html">排名</a><a href="forex_news.html">新聞</a><a href="ccy_power/index.html">CCY</a><a href="admin/tasks_board.html">任務板</a><a href="tug_of_war_calculator.html">工具</a></nav>'),
    # B2 NAV（手機 drawer）
    ('NAV手機', '<nav aria-label="主導清單（手機）"><a href="../index.html">首頁</a><a href="../signal_ranking.html">排名</a><a href="../forex_news.html">新聞</a><a href="../ccy_power/index.html">CCY</a><a href="tasks_board.html">任務板</a><a href="../tug_of_war_calculator.html">工具</a></nav>',
     '<nav aria-label="主導清單（手機）"><a href="index.html">首頁</a><a href="signal_ranking.html">排名</a><a href="forex_news.html">新聞</a><a href="ccy_power/index.html">CCY</a><a href="admin/tasks_board.html">任務板</a><a href="tug_of_war_calculator.html">工具</a></nav>'),
    # B3 fetch 路徑 root 相對
    ('fetch投影', "fetch('../home/projection.json')", "fetch('home/projection.json')"),
    ('fetch帳戶', "fetch('../home/accounts.json')", "fetch('home/accounts.json')"),
    # B4 EA 欄表頭（商品之後）
    ('EA欄表頭', '<th class="sortable" data-k="symbol">商品 <span class="arr"></span></th>',
     '<th class="sortable" data-k="symbol">商品 <span class="arr"></span></th>\n<th class="sortable" data-k="ea">EA <span class="arr"></span></th>'),
    # B5 EA 資料格（商品之後；UNK 弱化）
    ('EA資料格', "'</a></b></td><td>'+esc(r.symbol)+'</td>'",
     "'</a></b></td><td>'+esc(r.symbol)+'</td><td style=\"color:'+((r.ea&&r.ea!=='UNK')?'var(--t1)':'var(--t3)')+'\">'+esc(r.ea||'—')+'</td>'"),
    # B6 ea 加入字串排序欄集合
    ('ea排序欄', "state.dir=(k==='signal'||k==='symbol'||k==='month_key')?1:-1;",
     "state.dir=(k==='signal'||k==='symbol'||k==='ea'||k==='month_key')?1:-1;"),
]

# ============ C. encrypt_admin_pages.sh：PAGES 移除 projection ============
ENC_SH_EDITS = [
    ('PAGES清單', 'PAGES=(\n  "docs/admin/index.html"\n  "docs/admin/projection.html"\n  "docs/index.html"\n  "docs/signal_ranking.html"\n)',
     'PAGES=(\n  "docs/admin/index.html"\n  "docs/index.html"\n  "docs/signal_ranking.html"\n)\n# 2026-11-05 老闆首頁意見（W7b）：projection.html 唔需要入 admin 層——移 docs/projection.html root 公開明文，此行刪除。'),
]

# ============ D. tests/encryption_check.py：CORE 出＋BLOCKED 入 ============
ENC_TEST_EDITS = [
    ('CORE除名', '    "docs/admin/mt5_mcp_tools.html",\n    "docs/admin/projection.html",\n    "docs/admin/tasks_board.html",\n    "docs/index.html",',
     '    "docs/admin/mt5_mcp_tools.html",\n    "docs/admin/tasks_board.html",\n    "docs/index.html",'),
    ('裁示註解', '# 2026-11-04 七頁：projection.html 補入（OpenClaw 0435 ③ 批准）——owner 加密頁\n# （P1/P3 修復主場）原唔在名單＝正閘脫網，明文復活閘攔唔住。',
     '# 2026-11-05 老闆首頁意見（W7b）：projection.html 唔需要入 admin 層——移 docs/projection.html\n# root 公開明文（同 34b49ae0 七頁先例），CORE_PAGES 除名＋負向斷言禁 admin 副本復活。'),
    ('BLOCKED補入', 'BLOCKED_PAGES = [\n    ("docs/admin/ccy_ranking.html",',
     'BLOCKED_PAGES = [\n    ("docs/admin/projection.html",\n     "SIGNAL 排名表已裁定 root 公開（老闆 11-05 首頁意見），admin 副本禁止復活"),\n    ("docs/admin/ccy_ranking.html",'),
]


def apply_edits(path, edits, must=True):
    txt = pathlib.Path(path).read_text(encoding='utf-8')
    for name, old, new in edits:
        n = txt.count(old)
        assert n == 1, f'[FAIL] 錨點「{name}」喺 {path} 出現 {n} 次（要求==1）'
        txt = txt.replace(old, new)
        print(f'  [OK] {name}')
    pathlib.Path(path).write_text(txt, encoding='utf-8')
    return txt


def main():
    print(f'== A. 首頁明文層施工：{SRC} ==')
    apply_edits(SRC, EDITS)

    print(f'== B. root 公開版：{PROJ_SRC} -> {PROJ_DST} ==')
    txt = pathlib.Path(PROJ_SRC).read_text(encoding='utf-8')
    for name, old, new in PROJ_EDITS:
        n = txt.count(old)
        assert n == 1, f'[FAIL] 錨點「{name}」出現 {n} 次（要求==1）'
        txt = txt.replace(old, new)
        print(f'  [OK] {name}')
    pathlib.Path(PROJ_DST).write_text(txt, encoding='utf-8')
    print(f'  寫出 {PROJ_DST}（{len(txt)} bytes）')

    print(f'== C. {ENC_SH} ==')
    apply_edits(ENC_SH, ENC_SH_EDITS)

    print(f'== D. {ENC_TEST} ==')
    apply_edits(ENC_TEST, ENC_TEST_EDITS)

    print('全部錨點通過。')


if __name__ == '__main__':
    sys.exit(main())
