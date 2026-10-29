import json
from playwright.sync_api import sync_playwright

JS = r"""
() => {
  const d = document.documentElement;
  const vis = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  let mf = 99, mfw = '';
  document.querySelectorAll('body *').forEach(e => {
    if (!e.children.length && e.textContent.trim()) {
      const f = parseFloat(getComputedStyle(e).fontSize);
      if (f < mf) { mf = f; mfw = (e.className || e.tagName); }
    }
  });
  const ovf = [...document.querySelectorAll('*')]
    .filter(e => e.clientWidth > 0 && e.scrollWidth - e.clientWidth > 2)
    .map(e => [e.className || e.tagName, e.scrollWidth - e.clientWidth]);
  // text blocks chars-per-line
  const blocks = [...document.querySelectorAll('td, li, p, .concl, .t, .ev')]
    .filter(e => e.textContent.trim().length > 8 && vis(e));
  const cpl = blocks.map(e => {
    const cs = getComputedStyle(e);
    const lh = parseFloat(cs.lineHeight) || 20;
    const lines = Math.max(1, Math.round(e.getBoundingClientRect().height / lh));
    const chars = e.textContent.trim().length;
    return { chars, lines, cpl: Math.round(chars / lines) };
  });
  const sortc = cpl.map(o => o.cpl).sort((a, b) => a - b);
  const rows = [...document.querySelectorAll('tbody tr, .row:not(.row-hd)')].map(r => Math.round(r.getBoundingClientRect().height));
  const containers = [...document.querySelectorAll('.card, .board > *')];
  const tops = containers.map(c => Math.round(c.getBoundingClientRect().top));
  return {
    vw: d.clientWidth, sw: d.scrollWidth, pageH: Math.round(document.body.getBoundingClientRect().height),
    minFont: mf, minFontWho: mfw,
    overflowCount: ovf.length, overflowSample: ovf.slice(0, 3),
    cpl: { n: cpl.length, min: sortc[0], median: sortc[Math.floor(sortc.length / 2)], max: sortc[sortc.length - 1],
           maxLines: Math.max(...cpl.map(o => o.lines)) },
    rowH: { n: rows.length, max: Math.max(...rows), avg: Math.round(rows.reduce((a, b) => a + b, 0) / rows.length) },
    cardsFirstScreen: tops.filter(t => t < window.innerHeight).length,
    cardCount: containers.length
  };
}
"""

URLS = {"before": "file:///tmp/tasks_board_probe.html", "after": "file:///tmp/tasks_board_v2.html"}
res = {}
with sync_playwright() as p:
    br = p.chromium.launch()
    for name, url in URLS.items():
        for w, h in ((390, 844), (1280, 800)):
            pg = br.new_page(viewport={"width": w, "height": h}, device_scale_factor=2)
            pg.goto(url)
            pg.wait_for_timeout(250)
            r = pg.evaluate(JS)
            r["minTap"] = pg.evaluate(
                "()=>{const t=[...document.querySelectorAll('a,button,summary,[role=button]')].map(e=>Math.round(e.getBoundingClientRect().height)).filter(x=>x>0);return t.length?Math.min(...t):null}")
            res[f"{name}_{w}"] = r
            print(f"{name} {w}x{h}:", json.dumps(r, ensure_ascii=False))
            pg.close()
    br.close()
open("/tmp/ab_measure.json", "w").write(json.dumps(res, ensure_ascii=False, indent=1))
