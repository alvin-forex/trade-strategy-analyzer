import json
from playwright.sync_api import sync_playwright
URL="file:///home/alvin/.openclaw/workspace/trade_strategy_analyzer/exchange/from_zcode/20261029_1435_ZCODE_w_交付_TASKS_Board六截圖/tasks_board_preview.html"
JS=r"""()=>{
  const d=document.documentElement;
  const leaf=[...document.querySelectorAll('body *')].filter(e=>!e.children.length&&e.textContent.trim());
  const ovf=[...document.querySelectorAll('*')].filter(e=>e.clientWidth>0&&e.scrollWidth-e.clientWidth>2).map(e=>[e.className||e.tagName,e.scrollWidth-e.clientWidth]);
  const blocks=[...document.querySelectorAll('td,li,p,.concl,.t,.ev')].filter(e=>e.textContent.trim().length>8);
  const cpl=blocks.map(e=>{const cs=getComputedStyle(e);const lh=parseFloat(cs.lineHeight)||20;const lines=Math.max(1,Math.round(e.getBoundingClientRect().height/lh));return Math.round(e.textContent.trim().length/lines)}).sort((a,b)=>a-b);
  const rows=[...document.querySelectorAll('.row:not(.row-hd)')].map(r=>Math.round(r.getBoundingClientRect().height));
  const taps=[...document.querySelectorAll('a,button,summary,[role=button]')].map(e=>Math.round(e.getBoundingClientRect().height)).filter(x=>x>0);
  const cards=[...document.querySelectorAll('.card')].map(c=>({cls:c.className,h:Math.round(c.getBoundingClientRect().height)}));
  return {vw:d.clientWidth,sw:d.scrollWidth,pageH:Math.round(document.body.getBoundingClientRect().height),
    minFont:Math.min(...leaf.map(e=>parseFloat(getComputedStyle(e).fontSize))),
    below12:leaf.filter(e=>parseFloat(getComputedStyle(e).fontSize)<12).length,
    overflow:ovf.length, overflowSample:ovf.slice(0,3),
    cplMedian:cpl[Math.floor(cpl.length/2)], cplMin:cpl[0],
    rowMax:Math.max(...rows), rowAvg:Math.round(rows.reduce((a,b)=>a+b,0)/rows.length), rowN:rows.length,
    minTap:taps.length?Math.min(...taps):null,
    cards, taskColW:Math.round((document.querySelector('.c-task')||{getBoundingClientRect:()=>({width:0})}).getBoundingClientRect().width),
    doneCardsH:cards.filter(c=>/done/.test(c.cls)).reduce((a,c)=>a+c.h,0)};
}"""
out={}
with sync_playwright() as p:
    br=p.chromium.launch()
    for w,h in ((320,700),(390,844),(1280,800),(1920,1080)):
        pg=br.new_page(viewport={"width":w,"height":h}); pg.goto(URL); pg.wait_for_timeout(250)
        out[str(w)]=pg.evaluate(JS); pg.close()
    # grayscale-independent: check no script
    br.close()
open('/tmp/tasks_board_measure_20261029.json','w').write(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=1)[:2500])
