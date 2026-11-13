/* TSA SIGNAL 排行榜 —— 渲染（資料來自 data/signal_ranking.json）
   欄數 12：# Signal EA CCY數 DDE 紅卡% 勝率 交易 PF 淨點數 MaxDD 組合 */
'use strict';
(function () {
  var tb = document.getElementById('tb');
  var st = {
    f: TSA.store.get('sig_f', 'all'),
    ea: TSA.store.get('sig_ea', ''),
    q: TSA.store.get('sig_q', ''),
    showRed: TSA.store.get('sig_red', false),
    sort: TSA.store.get('sig_sort', { k: 'dde', dir: 'desc' }),
    rows: [], view: [], page: 0
  };
  var PAGE = 100;
  var EA_ORDER = ['UNK', 'DW', 'FL', 'MKD', 'MKDP', 'SMA', 'SMAP', 'GC', 'GS', 'S10', 'GEM'];
  var NAMES = { UNK: '未識別', DW: 'Dragon Wave', FL: 'Flash', MKD: 'MKD', MKDP: 'MKD Pro',
    SMA: 'SMA', SMAP: 'SMA Pro', GC: 'Gemini Client', GS: 'Gemini Server',
    S10: 'S10', GEM: 'GEM' };

  TSA.initNav();

  TSA.load('data/signal_ranking.json').then(function (d) {
    st.rows = d.rows;
    renderMeta(d.meta);
    buildEaSelect();
    bind();
    apply();
  }).catch(function (e) { TSA.fail(document.querySelector('.tw'), e); });

  function renderMeta(m) {
    document.getElementById('asof').innerHTML = '<span class="dot"></span>數據截至 ' + m.as_of;
    var red = m.red_signals || 0;
    document.getElementById('kpis').innerHTML = [
      kpi('Signal 總數', m.total, '已評分 ' + m.scored + ' · 紅卡 ' + red),
      kpi('平均 DDE v5', m.avg_dde === null ? '—' : m.avg_dde, '滿分 100'),
      kpi('最高分', '<span class="gold">' + (m.best === null ? '—' : m.best) + '</span>',
        '最低 ' + (m.worst === null ? '—' : m.worst)),
      kpi('總交易次數', TSA.n(m.total_trades), '跨 ' + m.pairs + ' 個商品'),
      kpi('總淨點數', TSA.n(m.total_pips), 'pips 累計')
    ].join('');
    document.getElementById('fAsOf').textContent = m.as_of;
    document.getElementById('fBatch').textContent = m.batch;
    document.getElementById('redN').textContent = '（' + red + '）';
  }

  function kpi(t, v, n) {
    return '<div class="kpi"><div class="kpi-t">' + t + '</div><div class="kpi-v">' + v +
      '</div><div class="kpi-n">' + n + '</div></div>';
  }

  function buildEaSelect() {
    var seen = {};
    st.rows.forEach(function (r) {
      String(r.ea_base || '').split('+').forEach(function (t) { if (t) seen[t] = 1; });
    });
    var toks = Object.keys(seen).sort(function (a, b) {
      var ia = EA_ORDER.indexOf(a), ib = EA_ORDER.indexOf(b);
      if (ia < 0) ia = 99; if (ib < 0) ib = 99;
      return ia - ib || a.localeCompare(b);
    });
    var sel = document.getElementById('ea');
    sel.innerHTML = '<option value="">全部 EA</option>' + toks.map(function (t) {
      return '<option value="' + t + '">' + t + ' — ' + (NAMES[t] || t) + '</option>';
    }).join('');
    sel.value = st.ea;
  }

  function bind() {
    document.querySelectorAll('.chip').forEach(function (c) {
      c.setAttribute('aria-pressed', String(c.getAttribute('data-f') === st.f));
      c.addEventListener('click', function () {
        document.querySelectorAll('.chip').forEach(function (x) { x.setAttribute('aria-pressed', 'false'); });
        c.setAttribute('aria-pressed', 'true');
        st.f = c.getAttribute('data-f'); st.page = 0;
        TSA.store.set('sig_f', st.f); apply();
      });
    });
    var q = document.getElementById('q');
    q.value = st.q;
    q.addEventListener('input', function () {
      st.q = q.value.toLowerCase().trim(); st.page = 0;
      TSA.store.set('sig_q', st.q); apply();
    });
    var ea = document.getElementById('ea');
    ea.addEventListener('change', function () {
      st.ea = ea.value; st.page = 0; TSA.store.set('sig_ea', st.ea); apply();
    });
    var sr = document.getElementById('showRed');
    sr.checked = st.showRed;
    sr.addEventListener('change', function () {
      st.showRed = sr.checked; st.page = 0;
      TSA.store.set('sig_red', st.showRed); apply();
    });
    document.querySelectorAll('#tbl th[data-k]').forEach(function (th) {
      th.addEventListener('click', function () {
        var k = th.getAttribute('data-k');
        st.sort = { k: k, dir: (st.sort.k === k && st.sort.dir === 'desc') ? 'asc' : 'desc' };
        TSA.store.set('sig_sort', st.sort); paintSort(); apply();
      });
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
      var a = th.querySelector('.ar'); if (a) a.textContent = st.sort.dir === 'desc' ? '▼' : '▲';
    }
  }

  function apply() {
    st.view = st.rows.filter(function (r) {
      if (st.f === 'scored' && r.dde === null) return false;
      if (!st.showRed && st.f !== 'red' && r.red) return false;
      if (st.ea) {
        var toks = String(r.ea_base || '').split('+');
        if (toks.indexOf(st.ea) < 0) return false;
      }
      if (st.q) {
        var s = (r.signal + ' ' + r.ea + ' ' + r.ea_full).toLowerCase();
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
    var num = ['ccy_n', 'dde', 'red_pct', 'wr', 'trades', 'pf', 'pips', 'dd', 'combos', 'eaN'];
    st.view.sort(function (a, b) {
      if (k === 'i') return 0;
      var av = a[k], bv = b[k];
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
    var medals = ['🥇', '🥈', '🥉'];
    var start = st.page * PAGE, slice = st.view.slice(start, start + PAGE);
    tb.innerHTML = slice.map(function (r, i) {
      var rk = start + i + 1;
      var isRed = !!r.red;
      var pfCell = r.pfINF ? '<span class="inf">∞</span>' : (r.pf === null ? '—' : r.pf);
      var main = '<tr class="' + (isRed ? 'redrow' : '') + '">' +
        '<td class="l rk">' + rk + '<span class="medal">' +
        (!isRed && rk <= 3 ? medals[rk - 1] : '') + '</span></td>' +
        '<td class="l sid mono">' + linkCell(r.signal) + '</td>' +
        '<td class="l ea" title="' + TSA.esc(r.ea_full) + '">' + TSA.esc(r.ea) + '</td>' +
        '<td class="mono">' + r.ccy_n + '</td>' +
        '<td class="mono">' + TSA.dde(r.dde) + '</td>' +
        '<td class="mono">' + r.red_pct + '%</td>' +
        '<td class="mono">' + (r.wr === null ? '—' : r.wr) + '%</td>' +
        '<td class="mono">' + TSA.n(r.trades) + '</td>' +
        '<td class="mono">' + pfCell + '</td>' +
        '<td class="mono ' + TSA.cls(r.pips) + '">' + TSA.n(r.pips) + 'p</td>' +
        '<td class="mono dim">' + TSA.n(r.dd) + 'p</td>' +
        '<td class="mono dim">' + r.combos + '</td>' +
        '</tr>';
      if (isRed && r.rr && r.rr.length) {
        main += '<tr class="redrow sub"><td></td><td colspan="11" class="l rr-cell">' +
          TSA.rr(r.rr) + '<span class="dim" style="font-size:11px;margin-left:6px">' +
          '全部 ' + r.combos + ' 個組合均為紅卡</span></td></tr>';
      }
      return main;
    }).join('') || '<tr><td colspan="12" class="l dim" style="padding:26px;text-align:center">' +
      '冇符合條件嘅 signal（開「顯示紅卡」可看全部）</td></tr>';

    document.getElementById('cnt').textContent =
      st.view.length + ' / ' + st.rows.length + ' 個 signal';
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
    el.innerHTML = b.join('') + '<span class="info">' + st.view.length + ' 行 · 第 ' +
      (st.page + 1) + '/' + pages + ' 頁</span>';
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
