#!/usr/bin/env python3
"""w7_homepage_modules_20261105.py — W7 首頁六空殼 module 接入（明文層施工）

輸入：/tmp/index_plain.html（已解密首頁明文）
輸出：原地改寫（KPI ID化＋①新聞HIGH倒數＋②事件strip＋⑤帳戶總覽 live 化＋④⑥殼掛點標註＋CSS＋JS）

每個錨點 assert 次數==1，失敗即停（唔靜靜哋漏改）。
數據源（0700 總派工單 W7）：
  ③KPI＝data/kpi.json（排名Top3／帳戶淨值）＋data/news_high.json（HIGH數）
     當月增長：kpi.json 現版無月增長欄 → home/projection.json Top1 代位（出貨信申報）
  ①新聞＋HIGH倒數＝data/news_high.json（倒數 client-side 計，30s 重算）
  ②事件strip＝home/map_events.json（未來24h·HIGH先·手機位）
  ⑤帳戶總覽＝data/kpi.json demo＋shadow 段（live/cent 等擴欄位）
  ④sparkline／⑥最近分析＝殼留 JSON 掛點（等 OpenClaw D1 重導）
"""
import sys

SRC = '/tmp/index_plain.html'

EDITS = []  # (名, old, new)

# ---- A1 KPI 頂欄 ID 化 ----
EDITS.append(('KPI行', '''  <!-- ============ KPI 頂欄（Phase 2.1 接入 kpi.json） ============ -->
  <section class="kpis" aria-label="KPI 頂欄（施工中）">
    <div class="kpi"><div class="kpi-t">當月增長</div><div class="kpi-v num">—</div><div class="kpi-n">Phase 2 · home/kpi.json</div></div>
    <div class="kpi"><div class="kpi-t">排名 Top3 升跌</div><div class="kpi-v num">—</div><div class="kpi-n">Phase 2 · home/kpi.json</div></div>
    <div class="kpi"><div class="kpi-t">今日 HIGH 事件數</div><div class="kpi-v num">—</div><div class="kpi-n">Phase 2 · map_events.json</div></div>
    <div class="kpi"><div class="kpi-t">帳戶淨值</div><div class="kpi-v num">—</div><div class="kpi-n">Phase 2 · home/accounts.json</div></div>
  </section>''', '''  <!-- ============ KPI 頂欄（W7 live · data/kpi.json＋data/news_high.json，2026-11-05） ============ -->
  <section class="kpis" aria-label="KPI 頂欄">
    <div class="kpi"><div class="kpi-t">當月增長</div><div class="kpi-v num" id="kpiGrow">—</div><div class="kpi-n" id="kpiGrowN">kpi.json 月增長欄待擴 · 暫 projection Top1</div></div>
    <div class="kpi"><div class="kpi-t">排名 Top3 升跌</div><div class="kpi-v num" id="kpiTop3">—</div><div class="kpi-n" id="kpiTop3N">kpi.json · ccy_top</div></div>
    <div class="kpi"><div class="kpi-t">今日 HIGH 事件數</div><div class="kpi-v num" id="kpiHigh">—</div><div class="kpi-n" id="kpiHighN">news_high.json</div></div>
    <div class="kpi"><div class="kpi-t">帳戶淨值</div><div class="kpi-v num" id="kpiNav">—</div><div class="kpi-n" id="kpiNavN">kpi.json · demo</div></div>
  </section>'''))

# ---- A2 ① 新聞＋HIGH 倒數 ----
EDITS.append(('新聞模組', '''      <section class="mod ph" aria-label="新聞與 HIGH 倒數（施工中）">
        <div class="ph-title">新聞＋HIGH 倒數</div>
        <div class="ph-sub">HIGH 優先 · 倒數 client-side 計（time_hkt）</div>
        <span class="ph-tag">Phase 2.8 · news_high.json</span>
      </section>''', '''      <section class="mod news" aria-label="新聞與 HIGH 倒數">
        <div class="ccy-head">
          <div class="ph-title" style="color:var(--txt-1)">新聞＋HIGH 倒數</div>
          <span class="ccy-when num" id="newsWhen">讀取中…</span>
        </div>
        <div class="news-list" id="newsList"></div>
        <div class="ccy-legend">
          <span><b style="color:var(--danger)">▲ HIGH</b> 優先 · 倒數 client-side 計（time_hkt）</span>
          <span>源 data/news_high.json（news_guard 每日 00:30 刷新）</span>
        </div>
      </section>'''))

# ---- A3 ④ sparkline 掛點標註 ----
EDITS.append(('sparkline掛點', '''        <span class="ph-tag">Phase 2.6 · data/*_D1.json</span>''',
              '''        <span class="ph-tag">Phase 2.6 · data/{SYM}_D1.json（[ts,o,h,l,c]×30 bar · 等 OpenClaw D1 重導出料）</span>'''))

# ---- A4 ② 事件 strip live 化 ----
EDITS.append(('事件strip', '''  <!-- 手機事件國家 strip（44px，Phase 2.4） -->
  <div class="strip-ph" style="margin-top:var(--s4)" aria-label="事件國家 strip（施工中）">
    ▲USD 02:00 FOMC　·　◆JPY 11:30 BoJ　→　事件國家 strip Phase 2.4（map_events.json · 未來 24h · HIGH 先）
  </div>''', '''  <!-- 手機事件國家 strip（44px，W7 live · home/map_events.json） -->
  <div class="strip-ev" id="evStrip" style="margin-top:var(--s4)" aria-label="事件國家 strip（未來 24h · HIGH 先）">
    <span class="se-tag">未來24h</span><span class="se-row" id="evStripRow">讀取中…</span>
  </div>'''))

# ---- A5 ⑤ 帳戶總覽 ----
EDITS.append(('帳戶總覽', '''      <section class="mod ph" aria-label="帳戶總覽（施工中）">
        <div class="ph-title">帳戶總覽</div>
        <div class="ph-sub">demo / live / cent 三段分開</div>
        <span class="ph-tag">Phase 2.9 · home/accounts.json</span>
      </section>''', '''      <section class="mod accts" aria-label="帳戶總覽">
        <div class="ccy-head">
          <div class="ph-title" style="color:var(--txt-1)">帳戶總覽</div>
          <span class="ccy-when num" id="acctsWhen">讀取中…</span>
        </div>
        <div class="acct-grid">
          <div class="acct-card"><div class="acct-t">demo</div><div class="acct-v num" id="acDemo">—</div><div class="acct-n" id="acDemoN">—</div></div>
          <div class="acct-card"><div class="acct-t">shadow s81</div><div class="acct-v num" id="acShadow">—</div><div class="acct-n" id="acShadowN">—</div></div>
        </div>
        <div class="ccy-legend">
          <span>live／cent：等 kpi.json 擴欄位</span>
          <span>源 data/kpi.json（每日 01:30 刷新）</span>
        </div>
      </section>'''))

# ---- A6 ⑥ 最近分析掛點標註 ----
EDITS.append(('最近分析掛點', '''        <span class="ph-tag">Phase 2.9 · 存檔機制接入</span>''',
              '''        <span class="ph-tag">Phase 2.9 · data/recent_analysis.json（{signal,date,link}×5 · 等存檔索引出料）</span>'''))

# ---- A7 CSS（strip-ph 之後插入 W7 模組樣式） ----
EDITS.append(('W7樣式', '''.strip-ph{display:none}  /* 手機先出（media query 控制） */''',
              '''.strip-ph{display:none}  /* 手機先出（media query 控制） */

/* ============ W7 模組（2026-11-05 總派工單）：①新聞HIGH倒數／②事件strip／⑤帳戶總覽 ============ */
.news-list{margin-top:10px;display:flex;flex-direction:column;gap:2px}
.news-row{display:flex;align-items:center;gap:var(--s2);padding:4px var(--s2);border-radius:4px;font-size:12px}
.news-row:hover{background:var(--bg-l2)}
.news-row.next{background:#FF6B6B14;border:1px solid #FF6B6B33}
.nw-t{color:var(--txt-3);font-family:var(--mono);width:42px;flex:none}
.nw-ev{color:var(--txt-1);flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.nw-cd{color:var(--danger);font-size:11px;white-space:nowrap;flex:none}
.news-row.past{opacity:.45}
.news-row.past .nw-cd{color:var(--txt-3)}
.strip-ev{
  min-height:44px;display:flex;align-items:center;gap:var(--s2);
  padding:0 var(--s4);overflow-x:auto;
  background:var(--bg-l1);border:1px solid var(--line);border-radius:6px;
  font-size:12px;color:var(--txt-2);white-space:nowrap;
}
.strip-ev{display:none}  /* 手機先出（media query 控制，同 strip-ph 慣例） */
.se-tag{color:var(--txt-3);flex:none}
.se-row{display:flex;align-items:center;gap:var(--s2)}
.se{flex:none}
.se-hi{color:var(--danger)}
.se-md{color:var(--warn)}
.se-sep{color:var(--txt-3)}
.acct-grid{display:grid;grid-template-columns:1fr 1fr;gap:var(--s2);margin-top:10px}
.acct-card{background:var(--bg-l2);border:1px solid var(--line);border-radius:6px;padding:var(--s2) var(--s3)}
.acct-t{font-size:11px;color:var(--txt-3);text-transform:uppercase;letter-spacing:.5px}
.acct-v{font-size:18px;font-weight:700;color:var(--txt-1);margin-top:2px}
.acct-n{font-size:11px;color:var(--txt-3);margin-top:2px}
.acct-n .neg{color:var(--danger)}'''))

# ---- A8 手機 media query 補 strip-ev ----
EDITS.append(('手機strip', '''  .strip-ph{display:flex}''',
              '''  .strip-ph{display:flex}
  .strip-ev{display:flex}'''))

# ---- A9 JS 模組（</body> 前新 script） ----
JS = '''<script>
/* ============ W7 模組（2026-11-05 總派工單）：③KPI／①新聞HIGH倒數／②事件strip／⑤帳戶總覽 ============ */
/* 數據源：data/kpi.json（01:30 刷新）· data/news_high.json（00:30）· home/projection.json（月增長代位）· home/map_events.json */
(function(){
  function $(id){return document.getElementById(id)}
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function num(v,d){return (typeof v==='number'&&isFinite(v))?v.toFixed(d==null?2:d):'—'}
  function live(el){if(el)el.style.color='var(--txt-1)'}

  /* ③ KPI（排名Top3／帳戶淨值）＋⑤ 帳戶總覽 —— data/kpi.json */
  fetch('data/kpi.json',{cache:'no-store'})
  .then(function(r){return r.ok?r.json():Promise.reject(new Error('HTTP '+r.status));})
  .then(function(j){
    var d=j.demo||{},top=j.ccy_top||[],s=j.shadow||{};
    if(typeof d.balance==='number'){
      var e=$('kpiNav');e.textContent=num(d.balance);live(e);
      $('kpiNavN').textContent='demo · pending '+(d.pending==null?'—':d.pending)+' · 持倉 '+(d.positions==null?'—':d.positions);
      $('acDemo').textContent=num(d.balance);
      $('acDemoN').textContent='pending '+(d.pending==null?'—':d.pending)+' · 持倉 '+(d.positions==null?'—':d.positions);
    }
    if(top.length){
      var e2=$('kpiTop3');e2.textContent=top.slice(0,3).map(function(c){return c.ccy}).join(' · ');live(e2);
      $('kpiTop3N').textContent=top.slice(0,3).map(function(c){return c.ccy+' '+num(c.score)}).join(' · ')+'（D1 top3）';
    }
    if(typeof s.equity_start==='number'){$('acShadow').textContent=num(s.equity_start);}
    $('acShadowN').innerHTML=(s.session?esc(String(s.session).slice(0,30))+'<br>':'')
      +'前場 P/L <span class="'+((typeof s.prev_pl==='number'&&s.prev_pl<0)?'neg':'')+'">'
      +(typeof s.prev_pl==='number'?((s.prev_pl>0?'+':'')+num(s.prev_pl,1)):'—')+'</span>';
    $('acctsWhen').textContent=j.updated_hkt?('更新 '+String(j.updated_hkt).slice(5,16).replace('T',' ')):'kpi.json';
  })
  .catch(function(){$('acctsWhen').textContent='kpi.json 未取得';});

  /* ③ KPI 當月增長 —— kpi.json 暫無月增長欄 → projection Top1 代位（0700 單 W7 申報） */
  fetch('home/projection.json',{cache:'no-store'})
  .then(function(r){return r.ok?r.json():Promise.reject(new Error('HTTP '+r.status));})
  .then(function(j){
    var r0=(j.rows||[])[0];
    if(r0&&typeof r0.month_growth==='number'){
      var e=$('kpiGrow'),v=r0.month_growth;
      e.textContent=(v>0?'+':'')+v.toLocaleString('en-US',{maximumFractionDigits:1});
      e.style.color=v>0?'var(--ok)':'var(--danger)';
      $('kpiGrowN').textContent='projection Top1 · #'+r0.signal+' '+r0.symbol;
    }
  }).catch(function(){});

  /* ① 新聞＋HIGH 倒數 —— data/news_high.json（倒數 client-side 計，30s 重算） */
  function cdText(ms){
    if(ms<=0)return '已過';
    var m=Math.round(ms/60000),h=Math.floor(m/60),mm=m%60;
    return (h>0?h+'h ':'')+mm+'m';
  }
  function tickNews(){
    var now=Date.now();
    document.querySelectorAll('#newsList .nw-cd').forEach(function(el){
      el.textContent=cdText(+el.getAttribute('data-ts')-now);
    });
  }
  function renderNews(j){
    var evs=(j.events||[]).slice().sort(function(a,b){return String(a.time_hkt).localeCompare(String(b.time_hkt));});
    var now=Date.now(),L=$('newsList'),h='',markedNext=false;
    evs.forEach(function(e){
      var m=/^(\\d{4})-(\\d{2})-(\\d{2})[T ](\\d{2}):(\\d{2})/.exec(String(e.time_hkt||''));
      if(!m)return;
      var t=new Date(+m[1],+m[2]-1,+m[3],+m[4],+m[5]).getTime();
      var fut=t>now,cls='news-row'+(fut?'':' past');
      if(fut&&!markedNext){cls+=' next';markedNext=true;}
      h+='<div class="'+cls+'">'
        +'<span class="nw-t">'+m[4]+':'+m[5]+'</span>'
        +'<span class="ccy-badge">'+esc(e.ccy)+'</span>'
        +'<span class="nw-ev">'+esc(e.event)+'</span>'
        +'<span class="nw-cd" data-ts="'+t+'">—</span></div>';
    });
    if(!h){L.innerHTML='<div style="padding:12px 4px;font-size:12px;color:var(--txt-3)">今日無 HIGH 事件（news_high.json）</div>';}
    else{L.innerHTML=h;}
    $('newsWhen').textContent=j.updated_hkt?('更新 '+String(j.updated_hkt).slice(5,16).replace('T',' ')):'news_high.json';
    var cnt=0,first=null;
    evs.forEach(function(e){if(String(e.impact).toUpperCase()==='HIGH'){cnt++;if(!first)first=e;}});
    var e3=$('kpiHigh');e3.textContent=cnt;live(e3);
    if(first){
      var fm=/[T ](\\d{2}:\\d{2})/.exec(String(first.time_hkt||''));
      $('kpiHighN').textContent='news_high.json · 最近 '+(fm?fm[1]:'—')+' '+first.ccy;
    }else{$('kpiHighN').textContent='news_high.json · 今日 0 HIGH';}
    tickNews();
  }
  fetch('data/news_high.json',{cache:'no-store'})
  .then(function(r){return r.ok?r.json():Promise.reject(new Error('HTTP '+r.status));})
  .then(renderNews)
  .catch(function(){
    $('newsWhen').textContent='news_high.json 未取得';
    $('newsList').innerHTML='<div style="padding:12px 4px;font-size:12px;color:var(--txt-3)">新聞數據未取得（data/news_high.json）</div>';
  });
  setInterval(tickNews,30000);

  /* ② 事件國家 strip —— home/map_events.json（未來 24h · HIGH 先 · 手機位） */
  fetch('home/map_events.json',{cache:'no-store'})
  .then(function(r){return r.ok?r.json():Promise.reject(new Error('HTTP '+r.status));})
  .then(function(j){
    var now=Date.now(),rank={HIGH:0,MED:1,MEDIUM:1,LOW:2};
    var fut=(j.events||[]).filter(function(e){var t=Date.parse(e.time_hkt);return t&&t>now&&(t-now)<24*3600e3;});
    fut.sort(function(a,b){
      var ra=rank[a.impact]!=null?rank[a.impact]:9,rb=rank[b.impact]!=null?rank[b.impact]:9;
      return ra-rb||Date.parse(a.time_hkt)-Date.parse(b.time_hkt);
    });
    var R=$('evStripRow');
    if(!fut.length){R.textContent='未來 24h 無 HIGH／MED 事件';return;}
    R.innerHTML=fut.slice(0,8).map(function(e){
      var d=new Date(Date.parse(e.time_hkt));
      var hh=('0'+d.getHours()).slice(-2)+':'+('0'+d.getMinutes()).slice(-2);
      var hi=String(e.impact).toUpperCase()==='HIGH';
      return '<span class="se '+(hi?'se-hi':'se-md')+'">'+(hi?'▲':'◆')+esc(e.currency)+' '+hh+' '+esc(e.event)+'</span>';
    }).join('<span class="se-sep">·</span>');
  })
  .catch(function(){var R=$('evStripRow');if(R)R.textContent='map_events.json 未取得';});
})();
</script>
</body>'''
EDITS.append(('W7腳本', '''</script>
</body>''', '''</script>
''' + JS))

def main():
    with open(SRC, encoding='utf-8') as f:
        html = f.read()
    fail = 0
    for name, old, new in EDITS:
        n = html.count(old)
        if n != 1:
            print(f'FAIL [{name}] 錨點出現 {n} 次（預期 1）')
            fail += 1
            continue
        if new in html and name != '手機strip':
            pass  # 新內容預先在場都唔影響（冪等複跑會 FAIL 錨點 0 次，正常擋住）
        html = html.replace(old, new, 1)
        print(f'OK   [{name}] +{len(new)-len(old)}B')
    if fail:
        print(f'\n{fail} 個錨點失敗——唔寫檔')
        sys.exit(1)
    with open(SRC, 'w', encoding='utf-8') as f:
        f.write(html)
    print(f'\n寫檔 {SRC}（{len(html)}B）')

if __name__ == '__main__':
    main()
