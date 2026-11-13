/* TSA CCY 排名 —— 渲染（資料來自 data/ccy_ranking.json）
   Grain：signal × 商品 × 方向（逐個 signal 分開，唔綜合） */
'use strict';
(function () {
  var app = document.querySelector('.tw');
  var st = {
    f: TSA.store.get('ccy_f', 'all'),
    ea: TSA.store.get('ccy_ea', ''),
    sym: TSA.store.get('ccy_sym', ''),
    q: TSA.store.get('ccy_q', ''),
    showRed: TSA.store.get('ccy_red', false),
    sort: TSA.store.get('ccy_sort', { k: 'dde', dir: 'desc' }),
    rows: [], view: [], page: 0, open: null
  };
  var PAGE = 100;
  var EA_ORDER = ['UNK', 'DW', 'FL', 'MKD', 'MKDP', 'SMA', 'SMAP', 'GC', 'GS', 'S10', 'GEM'];
  var NAMES = { UNK: '未識別', DW: 'Dragon Wave', FL: 'Flash', MKD: 'MKD', MKDP: 'MKD Pro',
    SMA: 'SMA', SMAP: 'SMA Pro', GC: 'Gemini Client', GS: 'Gemini Server',
    S10: 'S10', GEM: 'GEM' };

  TSA.initNav();

  TSA.load('data/ccy_ranking.json').then(function (d) {
    st.rows = d.rows;
    renderMeta(d.meta);
    buildSelects();
    bind();
    apply();
  }).catch(function (e) { TSA.fail(app, e); });

  function renderMeta(m) {
    document.getElementById('asof').innerHTML = '<span class="dot"></span>數據截至 ' + m.as_of;
    document.getElementById('kpis').innerHTML = [
      kpi('Signal × 商品 × 方向', TSA.n(m.combos), '每行 = 一個 signal 喺一個商品一個方向'),
      kpi('已評分', TSA.n(m.scored), '<span style="color:var(--red)">紅卡 ' + TSA.n(m.red) + '</span>'),
      kpi('Signal', m.signals, '全部拆細'),
      kpi('商品', m.pairs, '含指數 / 金屬'),
      kpi('BUY / SELL', TSA.n(m.buys) + '<small>/</small>' + TSA.n(m.sells), '方向分佈')
    ].join('');
    document.getElementById('fAsOf').textContent = m.as_of;
    document.getElementById('fBatch').textContent = m.batch;
    document.getElementById('redN').textContent = '（' + TSA.n(m.red) + '）';
  }

  function kpi(t, v, n) {
    return '<div class="kpi"><div class="kpi-t">' + t + '</div><div class="kpi-v">' + v +
      '</div><div class="kpi-n">' + n + '</div></div>';
  }

  function buildSelects() {
    var seenEa = {}, seenSym = {};
    st.rows.forEach(function (r) {
      String(r.ea || '').split('+').forEach(function (t) { if (t) seenEa[t] = 1; });
      seenSym[r.p] = 1;
    });
    var toks = Object.keys(seenEa).sort(function (a, b) {
      var ia = EA_ORDER.indexOf(a), ib = EA_ORDER.indexOf(b);
      if (ia < 0) ia = 99; if (ib < 0) ib = 99;
      return ia - ib || a.localeCompare(b);
    });
    var ea = document.getElementById('ea');
    ea.innerHTML = '<option value="">全部 EA</option>' + toks.map(function (t) {
      return '<option value="' + t + '">' + t + ' — ' + (NAMES[t] || t) + '</option>';
    }).join('');
    ea.value = st.ea;

    var sym = document.getElementById('sym');
    sym.innerHTML = '<option value="">全部商品</option>' +
      Object.keys(seenSym).sort().map(function (s) {
        return '<option value="' + s + '">' + s + '</option>';
      }).join('');
    sym.value = st.sym;
  }

  function bind() {
    document.querySelectorAll('.chip').forEach(function (c) {
      c.setAttribute('aria-pressed', String(c.getAttribute('data-f') === st.f));
      c.addEventListener('click', function () {
        document.querySelectorAll('.chip').forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        c.setAttribute('aria-pressed', 'true');
        st.f = c.getAttribute('data-f'); st.page = 0; st.open = null;
        TSA.store.set('ccy_f', st.f); apply();
      });
    });
    var q = document.getElementById('q'); q.value = st.q;
    q.addEventListener('input', function () {
      st.q = q.value.toLowerCase().trim(); st.page = 0; st.open = null;
      TSA.store.set('ccy_q', st.q); apply();
    });
    var ea = document.getElementById('ea');
    ea.addEventListener('change', function () {
      st.ea = ea.value; st.page = 0; st.open = null;
      TSA.store.set('ccy_ea', st.ea); apply();
    });
    var sym = document.getElementById('sym');
    sym.addEventListener('change', function () {
      st.sym = sym.value; st.page = 0; st.open = null;
      TSA.store.set('ccy_sym', st.sym); apply();
    });
    var sr = document.getElementById('showRed');
    sr.checked = st.showRed;
    sr.addEventListener('change', function () {
      st.showRed = sr.checked; st.page = 0; st.open = null;
      TSA.store.set('ccy_red', st.showRed); apply();
    });
    document.querySelectorAll('#tbl th[data-k]').forEach(function (th) {
      th.addEventListener('click', function () {
        var k = th.getAttribute('data-k');
        st.sort = { k: k, dir: (st.sort.k === k && st.sort.dir === 'desc') ? 'asc' : 'desc' };
        TSA.store.set('ccy_sort', st.sort); paintSort(); apply();
      });
    });
    document.getElementById('tb').addEventListener('click', function (ev) {
      var tr = ev.target.closest('tr.dr'); if (!tr) return;
      if (ev.target.closest('a')) return;   /* 點連結唔展收 */
      toggleRow(tr);
    });
    paintSort();
  }

  function paintSort() {
    document.querySelectorAll('#tbl th').forEach(function (th) {
      th.removeAttribute('data-dir');
      var a = th.querySelector('.ar'); if (a) a.textContent = '▾';
    });
    var th = document.querySelector('#tbl th[data-k="' + st.sort.k + '"]');
    if (th) {
      th.setAttribute('data-dir', st.sort.dir);
      th.querySelector('.ar').textContent = st.sort.dir === 'desc' ? '▼' : '▲';
    }
  }

  function key(r) { return r.s + '|' + r.p + '|' + r.d; }

  function toggleRow(tr) {
    var k = tr.getAttribute('data-key');
    var nx = tr.nextElementSibling;
    var wasOpen = st.open === k;
    // 收起所有展開行
    document.querySelectorAll('tr.expansion').forEach(function (e) { e.remove(); });
    document.querySelectorAll('tr.dr .caret').forEach(function (c) { c.textContent = '▸'; });
    if (wasOpen) { st.open = null; return; }
    st.open = k;
    tr.querySelector('.caret').textContent = '▾';
    var r = st.rows.find(function (x) { return key(x) === k; });
    if (!r) return;
    var cards = r.lv.map(function (a) {
      var L = a[0], t = a[1], wr = a[2], pf = a[3];
      return '<div class="lvc"><div class="lvc-t">' + L + '</div>' +
        '<div class="lvc-v">' + (wr === null ? '—' : wr + '%') + '</div>' +
        '<div class="lvc-n">PF ' + (pf === null ? '—' : pf) + ' · ' + TSA.n(t) + ' 手</div></div>';
    }).join('');
    var er = document.createElement('tr');
    er.className = 'expansion';
    er.innerHTML = '<td colspan="14"><div class="lvbox"><div class="lvhead">' +
      r.s + ' · ' + r.p + ' · ' + (r.d === 'B' ? 'BUY' : 'SELL') +
      ' — 馬汀層級逐層表現（' + r.lv.length + ' 層）' +
      (r.rr && r.rr.length ? '　' + TSA.rr(r.rr) : '') + '</div>' +
      '<div class="lvgrid">' + cards + '</div></div></td>';
    tr.after(er);
  }

  function apply() {
    st.view = st.rows.filter(function (r) {
      if (st.f === 'buy' && r.d !== 'B') return false;
      if (st.f === 'sell' && r.d !== 'S') return false;
      if (!st.showRed && r.rc) return false;
      if (st.ea) {
        var toks = String(r.ea || '').split('+');
        if (toks.indexOf(st.ea) < 0) return false;
      }
      if (st.sym && r.p !== st.sym) return false;
      if (st.q) {
        var s = (r.s + ' ' + r.p + ' ' + r.e + ' ' + r.E).toLowerCase();
        if (s.indexOf(st.q) < 0) return false;
      }
      return true;
    });
    sortView();
    st.page = Math.min(st.page, Math.max(0, Math.ceil(st.view.length / PAGE) - 1));
    draw();
  }

  function sortView() {
    var k = st.sort.k, dir = st.sort.dir === 'desc' ? -1 : 1;
    var num = ['dde', 't', 'wr', 'pf', 'pp', 'dd', 'ht', 'rc', 'lyn'];
    st.view.sort(function (a, b) {
      if (k === 'i') return 0;
      var av, bv;
      if (k === 'lyn') { av = a.lv.length; bv = b.lv.length; }
      else { av = a[k]; bv = b[k]; }
      if (num.indexOf(k) >= 0) {
        av = (av === null || av === undefined) ? -Infinity : av;
        bv = (bv === null || bv === undefined) ? -Infinity : bv;
        return (av - bv) * dir;
      }
      return String(av).localeCompare(String(bv), 'en') * dir;
    });
  }

  /* 原 signal 連結 ＋ 兩份報告（馬丁 v4 ＋ 深度分析） */
  function linkCell(id) {
    return '<a href="https://signals.algoforest.com/signals/' + id + '" target="_blank" ' +
      'rel="noopener" title="AlgoForest 原始 signal">' + id + '</a>' +
      ' <a href="reports/index_' + id + '.html" title="深度分析報告">🔍</a>' +
      ' <a href="reports/martin_v4_' + id + '.html" title="馬丁剖析 V4">📊</a>';
  }

  function draw() {
    var tb = document.getElementById('tb');
    var start = st.page * PAGE, slice = st.view.slice(start, start + PAGE);
    st.open = null;
    tb.innerHTML = slice.map(function (r, i) {
      var rk = start + i + 1;
      var dir = r.d === 'B' ? '<span class="badge b-buy">▲ BUY</span>'
        : '<span class="badge b-sell">▼ SELL</span>';
      var redCell = r.rc ? TSA.rr(r.rr) : '<span class="dim">—</span>';
      return '<tr class="dr' + (r.rc ? ' redrow' : '') + '" data-key="' +
        TSA.esc(key(r)) + '">' +
        '<td class="l rk"><span class="caret">▸</span>' + rk + '</td>' +
        '<td class="l sid mono">' + linkCell(r.s) + '</td>' +
        '<td class="l mono">' + r.p + '</td>' +
        '<td class="l">' + dir + '</td>' +
        '<td class="l ea" title="' + TSA.esc(r.E) + '">' + TSA.esc(r.e) + '</td>' +
        '<td class="mono">' + TSA.dde(r.dde) + '</td>' +
        '<td class="mono">' + TSA.n(r.t) + '</td>' +
        '<td class="mono">' + (r.wr === null ? '—' : r.wr) + '%</td>' +
        '<td class="mono">' + (r.pfINF ? '<span class="inf">∞</span>' :
          (r.pf === null ? '—' : r.pf)) + '</td>' +
        '<td class="mono ' + TSA.cls(r.pp) + '">' + TSA.n(r.pp) + 'p</td>' +
        '<td class="mono dim">' + TSA.n(r.dd) + 'p</td>' +
        '<td class="mono dim hide-sm">' + (r.ht === null ? '—' : r.ht) + '</td>' +
        '<td class="l rr-cell">' + redCell + '</td>' +
        '<td class="mono dim">' + r.lv.length + '</td>' +
        '</tr>';
    }).join('') || '<tr><td colspan="14" class="l dim" style="padding:26px;text-align:center">' +
      '冇符合條件嘅組合（開「顯示紅卡」可看全部 3,370 行）</td></tr>';

    document.getElementById('cnt').textContent =
      TSA.n(st.view.length) + ' / ' + TSA.n(st.rows.length) + ' 組合';
    pager();
  }

  function pager() {
    var el = document.getElementById('pager');
    var pages = Math.max(1, Math.ceil(st.view.length / PAGE));
    if (pages <= 1) { el.innerHTML = ''; return; }
    var b = ['<button ' + (st.page === 0 ? 'disabled' : '') + ' data-p="prev">← 上頁</button>'];
    var lo = Math.max(0, st.page - 2), hi = Math.min(pages - 1, st.page + 2);
    if (lo > 0) b.push('<button data-p="0">1</button>' + (lo > 1 ? '<span class="info">…</span>' : ''));
    for (var i = lo; i <= hi; i++) {
      b.push('<button data-p="' + i + '" aria-current="' + (i === st.page) + '">' + (i + 1) + '</button>');
    }
    if (hi < pages - 1) b.push((hi < pages - 2 ? '<span class="info">…</span>' : '') +
      '<button data-p="' + (pages - 1) + '">' + pages + '</button>');
    b.push('<button ' + (st.page >= pages - 1 ? 'disabled' : '') + ' data-p="next">下頁 →</button>');
    el.innerHTML = b.join('') + '<span class="info">' + TSA.n(st.view.length) +
      ' 行 · 第 ' + (st.page + 1) + '/' + pages + ' 頁</span>';
    el.querySelectorAll('button[data-p]').forEach(function (bt) {
      bt.addEventListener('click', function () {
        var p = bt.getAttribute('data-p');
        if (p === 'prev') st.page = Math.max(0, st.page - 1);
        else if (p === 'next') st.page = Math.min(pages - 1, st.page + 1);
        else st.page = +p;
        draw(); window.scrollTo(0, 0);
      });
    });
  }
})();
