#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w6_map_v2_20261105.py — P-1a/W6：首頁事件地圖 v2 金色粒子（插隊令 1255 首項）

規格（from_openclaw/20261105_1255 P-1a＋老闆 11-04 14:27 參考圖方向）：
  深黑底、金色粒子化大陸／區域、事件點金光、弧線靜態；
  關 1 bundle 實測 <300KB（粒子 canvas 生成，禁嵌圖）；
  關 2 禁 loop 動畫（靜態粒子＋光點；hover/tooltip 可以）→ L2 呼吸/L3 pulse/⏸ 掣全拆；
  關 3 screenshot 送簽核（本工具出貨信附四幀）。
  數據源 docs/home/map_events.json（契約不變）。

施工面（首頁 plaintext 四個 span，其餘 byte 不動）：
  1. CSS：事件地理層整段（.map-mod … prefers-reduced-motion 地圖規則）→ v2 金調版
  2. HTML：map-mod 節（world-g8 12 國 SVG＋mapTgl 掣）→ canvas＋world-map 全量 185 國
     （menelabs_original.svg 同源注入，15 path 加 data-ccy；fill 隱形＝幾何源）
  3. JS：Phase 2.2 地圖動效 IIFE → W6 v2 IIFE（canvas 粒子繪製＋靜態弧線＋金光事件；
     placeLabels/tooltip/數據接入/KPI 沿用 P7 邏輯，色板轉金）
  4. 國名標籤 IIFE：getElementById('world-g8') → 'world-map'

粒子設計：基礎陸地 spacing 19（暗金 .20-.46 op）＋12 貨幣國 spacing 11（亮金 .42-.85，
夾 #FFE566 亮點）；弧線 11 條主要貨幣對（二次貝茲，端點金點）；全部一次靜態繪製。

用法：python3 w6_map_v2_20261105.py <home_plaintext.html> [--dry|--verify]
"""
import re
import sys
from pathlib import Path

MENELABS = Path('/home/z/my-project/exchange-repo/exchange/from_zcode/'
                 '20261029_0935_ZCODE_w_交付_開源地圖素材六項證據/assets/menelabs_original.svg')
CCY_OF = {'us': 'USD', 'ca': 'CAD', 'jp': 'JPY', 'gb': 'GBP', 'ch': 'CHF',
          'au': 'AUD', 'nz': 'NZD', 'de': 'EUR-DE', 'fr': 'EUR-FR', 'it': 'EUR-IT',
          'es': 'EUR-ES', 'cn': 'CNY', 'in': 'INR', 'kr': 'KRW', 'mx': 'MXN'}

CSS_START = '/* ============ 事件地理層（地圖模組，240px 上限） ============ */'
CSS_END = '/* ============ 雙欄 ============ */'
HTML_START = '<!-- ============ 事件地理層（地圖模組 240px；動效 Phase 2.2） ============ -->'
JS_START = '/* ============ Phase 2.2 地圖動效（L1/L2/L3＋⏸；數據 home/map_events.json） ============ */'
JS_END = '/* ============ 地圖標籤（getBBox 動態置位＋自適應字號防重疊） ============ */'
OLD_LBL_LINE = "var svg=document.getElementById('world-g8');\n  if(!svg)return;"
NEW_LBL_LINE = "var svg=document.getElementById('world-map');\n  if(!svg)return;"


def build_world_svg():
    svg = MENELABS.read_text(encoding='utf-8')
    m = re.search(r'<svg[^>]*>(.*)</svg>', svg, re.S)
    inner = m.group(1)
    n = 0
    for pid, ccy in CCY_OF.items():
        pat = f'<path id="{pid}" '
        if pat in inner:
            inner = inner.replace(pat, f'<path id="{pid}" data-ccy="{ccy}" ', 1)
            n += 1
    assert n == len(CCY_OF), f'data-ccy 注入 {n}/{len(CCY_OF)}'
    head = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2000 1001" id="world-map">\n'
        '  <!-- Source: Menelabs.VectorAtlas dist/world.svg (Natural Earth public domain data)\n'
        '       License: CC BY 4.0 - https://creativecommons.org/licenses/by/4.0/\n'
        '       Attribution: Menelabs VectorAtlas https://github.com/melenaos/Menelabs.VectorAtlas\n'
        '       W6 v2（2026-11-05）：全量 185 國 path＝canvas 粒子採樣幾何源（CSS fill 隱形）；\n'
        '       15 path 加 data-ccy（12 貨幣國＋EUR 四國）行事件錨點（P7 座標零改動） -->\n'
    )
    tail = (
        '  <defs>\n'
        '    <radialGradient id="evGlowH"><stop offset="0%" stop-color="#FFD700" stop-opacity=".55"/>'
        '<stop offset="65%" stop-color="#FFD700" stop-opacity=".18"/>'
        '<stop offset="100%" stop-color="#FFD700" stop-opacity="0"/></radialGradient>\n'
        '    <radialGradient id="evGlowM"><stop offset="0%" stop-color="#EAB308" stop-opacity=".48"/>'
        '<stop offset="65%" stop-color="#EAB308" stop-opacity=".15"/>'
        '<stop offset="100%" stop-color="#EAB308" stop-opacity="0"/></radialGradient>\n'
        '  </defs>\n'
        '  <g id="evLayer"></g><!-- W6 v2：金光環＋hit 熱區＋標籤（互動層；零 loop） -->\n'
        '</svg>'
    )
    return head + inner.rstrip() + '\n' + tail


NEW_CSS = """/* ============ 事件地理層（W6 v2 金色粒子：深黑底＋canvas 粒子＋金光事件點＋靜態弧線；零 loop） ============ */
.map-mod{
  background:var(--bg-l1);border:1px solid var(--line);border-radius:6px;
  padding:var(--s3) var(--s4);margin-bottom:var(--s4);
  display:flex;flex-direction:column;gap:var(--s2);
}
.map-head{display:flex;align-items:baseline;gap:var(--s2)}
.map-head h2{font-size:16px;font-weight:700}
.map-phase{font-size:12px;color:var(--txt-2);margin-left:auto;white-space:nowrap}
.map-svg-wrap{
  position:relative;height:240px;display:flex;align-items:center;justify-content:center;
  background:radial-gradient(ellipse at 50% 38%,#0A0E17 0%,#05070C 78%);
  border:1px solid #131C2E;border-radius:6px;overflow:hidden;
}
.map-svg-wrap svg{height:100%;width:auto;max-width:100%;position:relative;z-index:1}
#mapCanvas{position:absolute;z-index:0;pointer-events:none}
/* W6 v2：path 只做幾何源（粒子喺 canvas）；fill 隱形唔攔互動 */
#world-map path{fill:none;stroke:none;pointer-events:none}
.map-lbl{fill:#F2EAD3;font-weight:700;pointer-events:none;letter-spacing:.5px;paint-order:stroke;stroke:rgba(5,7,12,.9);stroke-width:.1em;stroke-linejoin:round}
.map-cap{
  display:flex;align-items:center;gap:var(--s2);flex-wrap:wrap;
  font-size:12px;color:var(--txt-2);
}
.map-legend{display:flex;gap:var(--s1);flex-wrap:wrap}
.map-legend .ccy-badge{
  font-family:var(--mono);font-size:11px;color:var(--txt-2);
  border:1px solid var(--line);border-radius:4px;padding:1px 6px;background:var(--bg-l2);
}
.map-attr{margin-left:auto;white-space:nowrap}
.map-attr a{color:var(--txt-3)}
.map-attr a:hover{color:var(--txt-2)}
.map-cap .ev-lg{font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:.2px}
/* W6 v2：事件點金光（HIGH 亮金 #FFD700／MED 琥珀金 #EAB308）；hover 環加粗＝非 loop 回饋 */
.ev-ring{pointer-events:none}
.ev-ring .ev-hit{pointer-events:stroke;cursor:pointer}
.ev-ring:hover .ev-line{stroke-width:9}
.ev-marker{font-size:44px;font-weight:700;text-anchor:middle;pointer-events:none;paint-order:stroke;stroke:rgba(5,7,12,.9);stroke-width:.1em;stroke-linejoin:round}
.ev-high-txt{font-size:52px;font-weight:700;text-anchor:middle;pointer-events:none;paint-order:stroke;stroke:rgba(5,7,12,.9);stroke-width:.1em;stroke-linejoin:round}
.ev-tip{
  position:fixed;z-index:9;max-width:300px;pointer-events:none;display:none;
  background:rgba(22,30,46,.95);border:1px solid #2A3650;border-radius:8px;
  padding:10px 12px;font-size:12px;color:var(--txt-1);line-height:1.5;
  box-shadow:0 4px 16px rgba(0,0,0,.4);
}
.ev-tip .tip-ccy{font-weight:700;font-size:13px}
.ev-tip .tip-imp{font-weight:700;padding:0 6px;border-radius:4px;margin-left:6px}
.ev-tip .tip-imp.h{color:#FFD700;border:1px solid #FFD70066}
.ev-tip .tip-imp.m{color:#EAB308;border:1px solid #EAB30866}
.ev-tip .tip-ev{margin-top:4px}
.ev-tip .tip-t{color:var(--txt-3);font-variant-numeric:tabular-nums}
.ev-tip .tip-link{pointer-events:auto;display:inline-block;margin-top:6px;color:var(--info);text-decoration:underline;cursor:pointer}

"""

NEW_HTML_TMPL = """<!-- ============ 事件地理層（W6 v2 金色粒子：canvas 粒子世界＋12 貨幣國高亮＋金光事件點＋靜態弧線；零 loop 動畫） ============ -->
  <section class="map-mod" aria-label="事件地理層">
    <div class="map-head">
      <h2>事件地理層</h2>
      <div class="map-phase">金色粒子世界 · 12 貨幣國高亮 · 事件點金光 · 靜態弧線 · W6 v2</div>
    </div>
    <div class="map-svg-wrap" id="mapWrap">
      <canvas id="mapCanvas" aria-hidden="true"></canvas>
{WORLD_SVG}
    </div>
    <div class="map-cap">
      <span class="map-legend" aria-label="貨幣國清單">
        <span class="ccy-badge">USD</span><span class="ccy-badge">EUR</span><span class="ccy-badge">JPY</span><span class="ccy-badge">GBP</span><span class="ccy-badge">CHF</span><span class="ccy-badge">CAD</span><span class="ccy-badge">AUD</span><span class="ccy-badge">NZD</span><span class="ccy-badge">CNY</span><span class="ccy-badge">INR</span><span class="ccy-badge">KRW</span><span class="ccy-badge">MXN</span>
      </span>
      <span class="ev-lg" style="color:#FFD700">▲ HIGH</span><span class="ev-lg" style="color:#EAB308">◆ MED</span>
      <span class="map-attr">地圖 <a href="https://github.com/melenaos/Menelabs.VectorAtlas" target="_blank" rel="noopener">Menelabs VectorAtlas</a> · <a href="https://creativecommons.org/licenses/by/4.0/" target="_blank" rel="noopener">CC BY 4.0</a>（Natural Earth PD）</span>
    </div>
  </section>"""

NEW_JS = """/* ============ W6 地圖 v2 金色粒子（canvas 粒子世界＋金光事件點＋靜態弧線；零 loop——L2/L3/⏸ 全拆） ============ */
(function(){
  var svg=document.getElementById('world-map');
  var mod=svg?svg.closest('.map-mod'):null;
  if(!svg||!mod)return;
  var NS='http://www.w3.org/2000/svg';
  var layer=document.getElementById('evLayer');
  var cv=document.getElementById('mapCanvas');
  /* W6 v2 金調色板：HIGH 亮金／MED 琥珀金（紅／琥珀退役——「事件點金光」規格） */
  var COLORS={HIGH:{stroke:'#FFD700',glow:'url(#evGlowH)',txt:'HIGH',mark:'\\u25B2'},
              MED:{stroke:'#EAB308',glow:'url(#evGlowM)',txt:'',mark:'\\u25C6'}};
  /* 靜態弧線：11 條主要貨幣對（viewBox 座標二次貝茲；永久靜態） */
  var ARCS=[['USD','EUR'],['USD','JPY'],['GBP','USD'],['CHF','EUR'],['CAD','USD'],
            ['MXN','USD'],['AUD','USD'],['NZD','AUD'],['CNY','JPY'],['KRW','JPY'],['INR','CNY']];

  /* ---- 錨點：bbox 聯集中心＋isPointInFill 試位（P7 邏輯沿用） ---- */
  var pathsByCcy={};
  [].forEach.call(svg.querySelectorAll('path[data-ccy]'),function(p){
    var c=p.getAttribute('data-ccy').split('-')[0];
    (pathsByCcy[c]=pathsByCcy[c]||[]).push(p);
  });
  function unionBBox(ps){
    var u=null;ps.forEach(function(p){try{var b=p.getBBox();
      if(!u)u={x:b.x,y:b.y,width:b.width,height:b.height};
      else{var nx=Math.min(u.x,b.x),ny=Math.min(u.y,b.y);
        u.width=Math.max(u.x+u.width,b.x+b.width)-nx;
        u.height=Math.max(u.y+u.height,b.y+b.height)-ny;u.x=nx;u.y=ny;}
    }catch(e){}});
    return u;
  }
  function inAny(ccy,x,y){
    var pt;try{pt=new DOMPoint(x,y)}catch(e){return true}
    return (pathsByCcy[ccy]||[]).some(function(p){
      try{return p.isPointInFill(pt)}catch(e){return true}});
  }
  var OFF=[[0,0],[0,-.25],[0,.25],[-.25,0],[.25,0],[0,-.45],[0,.45],[-.25,-.25],[.25,.25]];
  function anchor(ccy,b){
    var cx=b.x+b.width/2,cy=b.y+b.height/2;
    for(var i=0;i<OFF.length;i++){
      var x=cx+OFF[i][0]*b.width,y=cy+OFF[i][1]*b.height;
      if(inAny(ccy,x,y))return{x:x,y:y};
    }
    return{x:cx,y:cy};
  }
  function radius(b){
    var m=Math.min(b.width,b.height);
    return Math.max(78,Math.min(146,Math.round(m*0.55*1.4)));
  }
  var NAMES={'USD':'美國','CAD':'加拿大','JPY':'日本','GBP':'英國','CHF':'瑞士',
             'AUD':'澳洲','NZD':'紐西蘭','EUR':'歐元區','CNY':'中國','INR':'印度',
             'KRW':'韓國','MXN':'墨西哥'};

  /* ---- tooltip（P7-2 沿用：fixed 跟滑鼠＋邊緣翻轉；金調 imp 徽章） ---- */
  var tip=null;
  function escEv(s){return String(s||'').replace(/[&<>"]/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  function fmtHKT(iso){
    var m=/^(\\d{4})-(\\d{2})-(\\d{2})T(\\d{2}):(\\d{2})/.exec(String(iso||''));
    return m?(m[2]+'-'+m[3]+' '+m[4]+':'+m[5]):'時間—';
  }
  function showTip(n,x,y){
    if(!tip){tip=document.createElement('div');tip.className='ev-tip';
      tip.setAttribute('role','status');document.body.appendChild(tip);}
    var imp=n.high?'<span class="tip-imp h">HIGH</span>':'<span class="tip-imp m">MED</span>';
    var h='<div class="tip-ccy">'+escEv(NAMES[n.ccy]||n.ccy)+'（'+n.ccy+'）· '+imp+'</div>';
    (n.evs||[]).slice(0,3).forEach(function(e){
      h+='<div class="tip-ev">'+escEv(e.event)+'<br><span class="tip-t">'
        +fmtHKT(e.time_hkt)+' HKT</span></div>';
    });
    if(!(n.evs||[]).length)h+='<div class="tip-ev">未來 24h 無排程事件</div>';
    if(n.url)h+='<a class="tip-link" href="'+n.url+'" target="_blank" rel="noopener">ForexFactory 日曆 ↗</a>';
    tip.innerHTML=h;tip.style.display='block';
    var w=tip.offsetWidth,ht=tip.offsetHeight,vw=window.innerWidth,vh=window.innerHeight;
    var lx=x+16,ly=y+16;
    if(lx+w>vw-8)lx=x-w-16;
    if(ly+ht>vh-8)ly=y-ht-16;
    tip.style.left=Math.max(8,lx)+'px';tip.style.top=Math.max(8,ly)+'px';
  }
  function hideTip(){if(tip)tip.style.display='none'}
  function bindEvHit(hit,node){
    hit.addEventListener('mouseenter',function(e){showTip(node,e.clientX,e.clientY)});
    hit.addEventListener('mousemove',function(e){showTip(node,e.clientX,e.clientY)});
    hit.addEventListener('mouseleave',hideTip);
    hit.addEventListener('click',function(){
      if(node.url)window.open(node.url,'_blank','noopener');
    });
  }

  /* ---- 標籤防碰撞＋邊界 clamp（P7-2 placeLabels 沿用，色板轉金） ---- */
  function placeLabels(nodes){
    var VB=(svg.getAttribute('viewBox')||'0 0 2000 1001').split(/\\s+/).map(Number);
    var PAD=8,placed=[];
    function inter(a,b){return a.x<b.x+b.w&&b.x<a.x+a.w&&a.y<b.y+b.h&&b.y<a.y+a.h}
    function fits(b){return b.x>=PAD&&b.y>=PAD&&b.x+b.w<=VB[2]-PAD&&b.y+b.h<=VB[3]-PAD
      &&!placed.some(function(q){return inter(b,q)})}
    var order=Object.keys(nodes).sort(function(a,b){
      var na=nodes[a],nb=nodes[b];
      return (nb.high-na.high)||(nb.count-na.count)||(a<b?-1:1);
    });
    order.forEach(function(k){
      var n=nodes[k];
      var seq=n.c.txt?[{cls:'ev-high-txt',txt:n.c.txt,fs:52},
                       {cls:'ev-marker',txt:n.c.mark,fs:44}]
                     :[{cls:'ev-marker',txt:n.c.mark,fs:44}];
      var cands=[[0,-n.r],[0,n.r],[n.r,0],[-n.r,0],[0,0]];
      for(var ci=0;ci<cands.length;ci++){
        var ox=cands[ci][0],oy=cands[ci][1];
        var totalH=0;seq.forEach(function(s){totalH+=s.fs});
        var ycur=n.y+oy-totalH/2,ok=true,els=[];
        for(var si=0;si<seq.length;si++){
          var s=seq[si];
          var t=document.createElementNS(NS,'text');
          t.setAttribute('x',(n.x+ox).toFixed(1));
          t.setAttribute('y',(ycur+s.fs*0.72).toFixed(1));
          t.setAttribute('fill',n.c.stroke);t.setAttribute('class',s.cls);
          t.textContent=s.txt;
          svg.appendChild(t);
          var bb;try{bb=t.getBBox()}catch(e){svg.removeChild(t);ok=false;break}
          els.push({el:t,b:{x:bb.x,y:bb.y,w:bb.width,h:bb.height}});
          ycur+=s.fs;
        }
        if(!ok){
          els.forEach(function(q){if(q.el.parentNode)q.el.parentNode.removeChild(q.el)});
          return;
        }
        var ux=Math.min.apply(null,els.map(function(q){return q.b.x}));
        var uy=Math.min.apply(null,els.map(function(q){return q.b.y}));
        var bx=Math.max.apply(null,els.map(function(q){return q.b.x+q.b.w}));
        var by=Math.max.apply(null,els.map(function(q){return q.b.y+q.b.h}));
        var blk={x:ux,y:uy,w:bx-ux,h:by-uy};
        if(!fits(blk)){
          els.forEach(function(q){if(q.el.parentNode)q.el.parentNode.removeChild(q.el)});
          continue;
        }
        placed.push(blk);
        els.forEach(function(q){if(q.el.parentNode)q.el.parentNode.removeChild(q.el)});
        els.forEach(function(q){q.el.removeAttribute('transform');layer.appendChild(q.el)});
        return;
      }
      var t=document.createElementNS(NS,'text');
      t.setAttribute('x',n.x.toFixed(1));t.setAttribute('y',(n.y+15).toFixed(1));
      t.setAttribute('fill',n.c.stroke);t.setAttribute('class','ev-marker');
      t.textContent=n.c.mark;
      layer.appendChild(t);
      try{var b=t.getBBox();placed.push({x:b.x,y:b.y,w:b.width,h:b.height})}catch(e){}
    });
  }

  /* ---- W6 v2 核心：canvas 金色粒子世界（一次靜態繪製，零 loop；禁嵌圖達標） ---- */
  function rnd(x,y){var h=Math.sin(x*12.9898+y*78.233)*43758.5453;return h-Math.floor(h)}
  var arcCache={};
  function arcAnchor(ccy){
    if(arcCache[ccy])return arcCache[ccy];
    var ps=pathsByCcy[ccy];if(!ps||!ps.length)return null;
    var u=unionBBox(ps);var a=u?anchor(ccy,u):null;
    arcCache[ccy]=a;return a;
  }
  function drawMap(){
    if(!cv)return;
    var wrap=svg.parentNode;
    var dpr=Math.min(window.devicePixelRatio||1,2);
    var w=svg.clientWidth||wrap.clientWidth||480;
    var h=svg.clientHeight||wrap.clientHeight||240;
    cv.style.left=svg.offsetLeft+'px';cv.style.top=svg.offsetTop+'px';
    cv.style.width=w+'px';cv.style.height=h+'px';
    cv.width=Math.max(2,Math.round(w*dpr));cv.height=Math.max(2,Math.round(h*dpr));
    var k=cv.width/2000,ctx=cv.getContext('2d');
    ctx.clearRect(0,0,cv.width,cv.height);
    /* 0) 陸地剪影底層（VLM 審圖 r2）：全量 path 極暗金實心 fill＋邊線——
       一次過解決輪廓辨識＋南美非洲黑洞；粒子降暗都認得到陸地 */
    ctx.save();ctx.scale(k,k);
    ctx.fillStyle='rgba(212,175,55,0.07)';
    ctx.strokeStyle='rgba(212,175,55,0.16)';
    ctx.lineWidth=1.2;
    [].forEach.call(svg.querySelectorAll('path'),function(p){
      var d=p.getAttribute('d');if(!d)return;
      try{var path=new Path2D(d);ctx.fill(path);ctx.stroke(path)}catch(e){}
    });
    ctx.restore();
    /* A) 基礎陸地粒子：全量國家（data-ccy 國除外）——疏＋暗金（VLM 審圖 v2：
       0.13-0.22 op＋spacing 22——剪影上嘅顆粒質感） */
    var SP=22;
    [].forEach.call(svg.querySelectorAll('path'),function(p){
      if(p.hasAttribute('data-ccy'))return;
      var b;try{b=p.getBBox()}catch(e){return}
      if(b.width*b.height<20)return;
      for(var x=b.x+SP*.5;x<b.x+b.width;x+=SP)
        for(var y=b.y+SP*.5;y<b.y+b.height;y+=SP){
          var ok=false;try{ok=p.isPointInFill(new DOMPoint(x,y))}catch(e){}
          if(!ok)continue;
          var r1=rnd(x,y);
          ctx.fillStyle='rgba(255,215,0,'+(0.13+r1*0.09).toFixed(2)+')';
          ctx.beginPath();ctx.arc(x*k,y*k,(4.0+r1*2.0)*k,0,6.28318);ctx.fill();
        }
    });
    /* B) 12 貨幣國粒子：密＋亮金（VLM 審圖 v2：0.72-1.0 op——與基底拉開 4-5 倍
       對比；夾 #FFE566 亮點比例升） */
    var SP2=12;
    [].forEach.call(svg.querySelectorAll('path[data-ccy]'),function(p){
      var b;try{b=p.getBBox()}catch(e){return}
      if(b.width*b.height<10)return;
      for(var x=b.x+SP2*.5;x<b.x+b.width;x+=SP2)
        for(var y=b.y+SP2*.5;y<b.y+b.height;y+=SP2){
          var ok=false;try{ok=p.isPointInFill(new DOMPoint(x,y))}catch(e){}
          if(!ok)continue;
          var r2=rnd(x*1.7,y*2.3);
          ctx.fillStyle=r2>.75?'rgba(255,229,102,'+(0.78+r2*.22).toFixed(2)+')'
                              :'rgba(255,215,0,'+(0.60+r2*.30).toFixed(2)+')';
          ctx.beginPath();ctx.arc(x*k,y*k,(5.8+r2*3.4)*k,0,6.28318);ctx.fill();
        }
    });
    /* C) 靜態弧線：11 條主要貨幣對（VLM 審圖 r3：雙描＝寬 halo＋窄主線漸層——
       「事件流向」做第二視覺層） */
    ctx.lineCap='round';
    ARCS.forEach(function(pair){
      var a1=arcAnchor(pair[0]),a2=arcAnchor(pair[1]);
      if(!a1||!a2)return;
      var dx=a2.x-a1.x,dy=a2.y-a1.y,L=Math.sqrt(dx*dx+dy*dy)||1;
      var bend=Math.min(140,L*.22);
      var cx2=(a1.x+a2.x)/2-dy/L*bend,cy2=(a1.y+a2.y)/2+dx/L*bend;
      var gr=ctx.createLinearGradient(a1.x*k,a1.y*k,a2.x*k,a2.y*k);
      gr.addColorStop(0,'rgba(255,215,0,.58)');
      gr.addColorStop(1,'rgba(255,215,0,.26)');
      ctx.beginPath();ctx.moveTo(a1.x*k,a1.y*k);
      ctx.quadraticCurveTo(cx2*k,cy2*k,a2.x*k,a2.y*k);
      ctx.strokeStyle='rgba(255,215,0,.16)';
      ctx.lineWidth=Math.max(2,6.0*k);
      ctx.stroke();
      ctx.strokeStyle=gr;
      ctx.lineWidth=Math.max(1,3.2*k);
      ctx.stroke();
      ctx.fillStyle='rgba(255,229,102,.85)';
      ctx.beginPath();ctx.arc(a1.x*k,a1.y*k,3.8*k,0,6.28318);ctx.fill();
      ctx.beginPath();ctx.arc(a2.x*k,a2.y*k,3.8*k,0,6.28318);ctx.fill();
    });
  }
  var rzT=null;
  window.addEventListener('resize',function(){
    clearTimeout(rzT);rzT=setTimeout(drawMap,250);  /* resize 重繪＝事件驅動，非 loop */
  });
  drawMap();

  /* ---- 數據接入：map_events.json；404／欠料 → 粒子地圖維持靜態零錯 ---- */
  function el(tag,attrs){var n=document.createElementNS(NS,tag);
    for(var k in attrs)n.setAttribute(k,attrs[k]);return n}
  var kpiCard=null;
  [].forEach.call(document.querySelectorAll('.kpi'),function(k){
    var t=k.querySelector('.kpi-t');
    if(!kpiCard&&t&&/今日\\s*HIGH\\s*事件數/.test(t.textContent))kpiCard=k;
  });
  function kpiSet(n){
    if(!kpiCard)return;
    var v=kpiCard.querySelector('.kpi-v');
    if(v)v.textContent=String(n);
  }
  fetch('home/map_events.json',{cache:'no-store'}).then(function(r){
    if(!r.ok)throw new Error('http '+r.status);
    return r.json();
  }).then(function(j){
    var evs=Array.isArray(j)?j:(j&&j.events)||[];
    if(!evs.length)return;
    var gen=j&&j.generated_at||(evs[0]&&evs[0].generated_at)||'';
    var list;
    var countries=(j&&Array.isArray(j.countries))?j.countries:null;
    if(countries){
      list=countries.filter(function(c){
        return c&&c.currency&&pathsByCcy[c.currency]&&c.max_impact&&c.max_impact!=='none';
      }).map(function(c){
        return{ccy:c.currency,high:c.max_impact==='HIGH',count:c.event_count_24h||0};
      });
    }else{
      var nowMs=Date.now(),agg={};
      evs.forEach(function(e){
        if(!e||!e.currency)return;
        var t=Date.parse(e.time_hkt||'');
        if(!isFinite(t)||t<=nowMs||t>nowMs+24*3600e3)return;
        var a=agg[e.currency]||(agg[e.currency]={ccy:e.currency,high:false,count:0});
        a.count++;
        if(e.impact==='HIGH')a.high=true;
      });
      list=Object.keys(agg).map(function(k){return agg[k]})
        .filter(function(a){return pathsByCcy[a.ccy]});
    }
    function pickAnchor(ccy){
      var ps=pathsByCcy[ccy].slice().sort(function(p1,p2){
        var b1,b2;try{b1=p1.getBBox();b2=p2.getBBox()}catch(e){return 0}
        return (b2.width*b2.height)-(b1.width*b1.height);
      });
      for(var i=0;i<ps.length;i++){
        var bb;try{bb=ps[i].getBBox()}catch(e){continue}
        if(bb.width*bb.height<4)continue;
        var cand=anchor(ccy,bb);
        try{if(ps[i].isPointInFill(new DOMPoint(cand.x,cand.y)))return cand}catch(e){}
      }
      var ub=unionBBox(ps);return ub?anchor(ccy,ub):null;
    }
    /* 12 國底層淡金圈：地點存在感（P7 抽象熱點層金調化；fill 唔攔互動） */
    var active={};list.forEach(function(a){active[a.ccy]=true});
    Object.keys(pathsByCcy).forEach(function(ccy){
      if(active[ccy])return;
      var pt=pickAnchor(ccy);if(!pt)return;
      var u=unionBBox(pathsByCcy[ccy])||{width:120,height:120};
      var r2=Math.max(30,Math.min(56,Math.round(Math.min(u.width,u.height)*0.3)));
      var g2=el('g',{'class':'ev-ring ev-idle','role':'img','aria-label':NAMES[ccy]?NAMES[ccy]+'（'+ccy+'）無未來 24h 高／中事件':ccy+' 無事件'});
      g2.appendChild(el('circle',{cx:pt.x.toFixed(1),cy:pt.y.toFixed(1),r:String(r2),fill:'#FFD700',opacity:'0.05'}));
      g2.appendChild(el('circle',{cx:pt.x.toFixed(1),cy:pt.y.toFixed(1),r:String(r2),fill:'none',stroke:'#FFD700','stroke-width':'2',opacity:'0.22'}));
      layer.appendChild(g2);
    });
    /* L1（金光版）：有事件國靜態金環＋光暈（HIGH 亮金／MED 琥珀金）＋hit 熱區 */
    var nodes={};
    list.forEach(function(a){
      var ps=pathsByCcy[a.ccy].slice().sort(function(p1,p2){
        var b1,b2;try{b1=p1.getBBox();b2=p2.getBBox()}catch(e){return 0}
        return (b2.width*b2.height)-(b1.width*b1.height);
      });
      var pt=null;
      for(var i=0;i<ps.length&&!pt;i++){
        var bb;try{bb=ps[i].getBBox()}catch(e){continue}
        if(bb.width*bb.height<4)continue;
        var cand=anchor(a.ccy,bb);
        try{if(ps[i].isPointInFill(new DOMPoint(cand.x,cand.y)))pt=cand}catch(e){}
      }
      if(!pt){var ub=unionBBox(ps);pt=ub?anchor(a.ccy,ub):null}
      if(!pt)return;
      var r=radius((function(){
        var u=null;ps.forEach(function(p){try{var q=p.getBBox();
          if(!u)u={x:q.x,y:q.y,width:q.width,height:q.height};
          else{var nx=Math.min(u.x,q.x),ny=Math.min(u.y,q.y);
            u.width=Math.max(u.x+u.width,q.x+q.width)-nx;
            u.height=Math.max(u.y+q.height,q.y+q.height)-ny;u.x=nx;u.y=ny;}
        }catch(e){}});return u||{width:120,height:120}})());
      var c=a.high?COLORS.HIGH:COLORS.MED;
      var g=el('g',{'class':'ev-ring','role':'img','aria-label':(NAMES[a.ccy]||a.ccy)+(a.high?' 高影響 ':' 中度影響 ')+a.count+' 事件，點擊查看日曆'});
      g.appendChild(el('circle',{cx:pt.x.toFixed(1),cy:pt.y.toFixed(1),r:String(r),fill:c.stroke,opacity:'0.10'}));
      g.appendChild(el('circle',{cx:pt.x.toFixed(1),cy:pt.y.toFixed(1),r:String(Math.round(r*1.25)),fill:c.glow}));
      g.appendChild(el('circle',{cx:pt.x.toFixed(1),cy:pt.y.toFixed(1),r:String(r),fill:'none',stroke:c.stroke,'stroke-width':'6','class':'ev-line'}));
      var hit=el('circle',{cx:pt.x.toFixed(1),cy:pt.y.toFixed(1),r:String(r),fill:'none',stroke:'#000','stroke-opacity':'0','stroke-width':'30','class':'ev-hit'});
      g.appendChild(hit);
      layer.appendChild(g);
      var ccyEvs=evs.filter(function(e){
        if(!e||e.currency!==a.ccy)return false;
        var t=Date.parse(e.time_hkt||'');
        return isFinite(t)&&t>Date.now()&&t<=Date.now()+24*3600e3;
      }).sort(function(e1,e2){return e1.time_hkt<e2.time_hkt?-1:1});
      var node={x:pt.x,y:pt.y,r:r,c:c,g:g,high:a.high,count:a.count,ccy:a.ccy,
                evs:ccyEvs,url:(ccyEvs[0]&&ccyEvs[0].url)||''};
      nodes[a.ccy]=node;
      bindEvHit(hit,node);
    });
    placeLabels(nodes);
    /* KPI：今日 HIGH 事件數（time_hkt 日期＝HKT 今日） */
    var today='';
    try{today=new Date(Date.now()+8*3600e3).toISOString().slice(0,10)}catch(e){}
    var hi=evs.filter(function(e){return e&&e.impact==='HIGH'&&String(e.time_hkt||'').slice(0,10)===today}).length;
    kpiSet(hi);
    /* W6 v2：零 loop——L2 呼吸／L3 pulse 已全拆（1255 關 2）；gen 串留待下版刷新指示 */
    if(gen){try{localStorage.setItem('tsa_map_gen',gen)}catch(e){}}
  }).catch(function(){/* 無數據：粒子地圖維持靜態，零錯誤 */});
})();

"""


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else 'run'
    if not src.exists():
        print(f'[FAIL] 檔案不存在: {src}')
        return 1
    t = src.read_text(encoding='utf-8')

    if mode == '--verify':
        ok = True
        checks = [
            ('canvas 元件', t.count('<canvas id="mapCanvas"') == 1),
            ('world-map SVG', t.count('id="world-map"') == 1),
            ('world-g8 退役', t.count('world-g8') == 0),
            ('mapTgl 退役', t.count('mapTgl') == 0),
            ('data-ccy 15', len(re.findall(r'<path id="[a-z]{2}" data-ccy="', t)) == 15),
            ('金環色板', t.count("stroke:'#FFD700'") >= 1 and t.count("stroke:'#EAB308'") >= 1),
            ('弧線', t.count('quadraticCurveTo') >= 1),
            ('零 loop：ev-halo', t.count('ev-halo') == 0),
            ('零 loop：map-pulse', t.count('map-pulse') == 0),
            ('零 loop：keyframes', t.count('evBreath') == 0 and t.count('evPulse') == 0),
            ('粒子繪製', t.count('drawMap') >= 2),
            ('tooltip 保留', t.count('showTip') >= 1),
            ('KPI 接入保留', t.count('kpiSet') >= 2),
            ('標籤 IIFE 已改 world-map',
             t.count("getElementById('world-map')") == 2),
        ]
        for name, good in checks:
            print(f'  {"PASS" if good else "FAIL"}  {name}')
            ok = ok and good
        print(f'=== verify：{"PASS" if ok else "FAIL"} ===')
        return 0 if ok else 1

    # ---- 四 span 抽取（fail-close：每個 marker 恰一出現） ----
    spans = {}
    for key, (start_m, end_m, incl_end) in {
        'css': (CSS_START, CSS_END, False),
        'html': (HTML_START, '</section>', True),
        'js': (JS_START, JS_END, False),
    }.items():
        if t.count(start_m) != 1:
            print(f'[FAIL] {key} start marker ×{t.count(start_m)}（須恰 1）')
            return 1
        i = t.find(start_m)
        if incl_end:
            j = t.find('</section>', i)
            if j == -1:
                print(f'[FAIL] {key} end 找不到')
                return 1
            j += len('</section>')
        else:
            if t.count(end_m) != 1:
                print(f'[FAIL] {key} end marker ×{t.count(end_m)}')
                return 1
            j = t.find(end_m)
        spans[key] = (i, j, t[i:j])

    # ---- 新內容 ----
    new_html = NEW_HTML_TMPL.replace('{WORLD_SVG}', build_world_svg())
    repl = {
        'css': (spans['css'][2], NEW_CSS.rstrip('\n') + '\n\n'),
        'html': (spans['html'][2], new_html),
        'js': (spans['js'][2], NEW_JS.rstrip('\n') + '\n'),
    }

    # ---- 純度自證：逐 span 順序替換＋逆操作還原==原檔 ----
    t2, undos = t, []
    for key in ('css', 'html', 'js'):
        i, j, old = spans[key]
        old_txt, new_txt = repl[key]
        i2 = t2.find(old_txt) if t2.count(old_txt) == 1 else -1
        if i2 < 0:
            print(f'[FAIL] {key} span 內容搵唔到（位置漂移）')
            return 1
        t2 = t2[:i2] + new_txt + t2[i2 + len(old_txt):]
        undos.append((new_txt, old_txt))
    n_lbl = t2.count(OLD_LBL_LINE)
    if n_lbl != 1:
        print(f'[FAIL] 標籤 IIFE world-g8 行 ×{n_lbl}（JS 替換後須恰 1）')
        return 1
    t2 = t2.replace(OLD_LBL_LINE, NEW_LBL_LINE, 1)
    undos.append((NEW_LBL_LINE, OLD_LBL_LINE))

    back = t2
    for new_txt, old_txt in reversed(undos):
        back = back.replace(new_txt, old_txt, 1)
    if back != t:
        print('[FAIL] 逆操作還原唔等於原檔（純度 fail-close 唔寫檔）')
        return 1

    # ---- 結構計數自證 ----
    for pat, name in [(r'<section\b', 'section'), (r'<script\b', 'script'),
                      (r'</head>', '</head>'), (r'<body\b', '<body'),
                      (r'\.kpi\b', 'kpi CSS 類')]:
        if len(re.findall(pat, t)) != len(re.findall(pat, t2)):
            print(f'[FAIL] 結構計數變化：{name}')
            return 1

    delta = len(t2) - len(t)
    mod_new = (len(repl['css'][1].encode('utf-8')) + len(repl['html'][1].encode('utf-8'))
               + len(repl['js'][1].encode('utf-8')))
    mod_old = (len(spans['css'][2].encode('utf-8')) + len(spans['html'][2].encode('utf-8'))
               + len(spans['js'][2].encode('utf-8')))
    if mode == '--dry':
        print(f'[DRY] {src.name}：四 span 替換（CSS {len(spans["css"][2])}→{len(repl["css"][1])}B｜'
              f'HTML {len(spans["html"][2])}→{len(repl["html"][1])}B｜JS {len(spans["js"][2])}→{len(repl["js"][1])}B｜'
              f'標籤行×1）；char_delta={delta:+d}')
        print(f'      地圖模組 byte：old={mod_old:,}B → new={mod_new:,}B'
              f'（<300KB 關 1：{"PASS" if mod_new < 300 * 1024 else "FAIL"}）')
        return 0

    src.write_text(t2, encoding='utf-8')
    print(f'[OK] {src.name} W6 v2 金色粒子落地：四 span；char_delta={delta:+d}；'
          f'地圖模組 {mod_old:,}→{mod_new:,}B（{"PASS" if mod_new < 300 * 1024 else "FAIL"} <300KB）；'
          f'section/script 計數不變')
    return 0


if __name__ == '__main__':
    sys.exit(main())
