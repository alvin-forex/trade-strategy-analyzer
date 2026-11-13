/* TSA 排名雙頁 —— 共用工具（v2 資料分離版） */
'use strict';

window.TSA = {
  /* 數字格式：1234 → 1,234 */
  n: function (v) {
    if (v === null || v === undefined) return '—';
    return Number(v).toLocaleString('en-US');
  },
  /* 正負著色 */
  cls: function (v) { return v > 0 ? 'pos' : (v < 0 ? 'neg' : ''); },
  /* 安全 HTML 轉義 */
  esc: function (s) {
    return String(s === null || s === undefined ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  },
  /* DDE 進度條 */
  dde: function (v) {
    if (v === null || v === undefined) return '<span class="dim">未評</span>';
    return '<span class="ddebar"><i style="width:' + Math.min(100, v) + '%"></i></span>' +
      '<span class="dcommono">' + v + '</span>';
  },
  /* 紅卡原因 pill */
  rr: function (arr) {
    if (!arr || !arr.length) return '';
    return arr.map(function (t, i) {
      return '<span class="rr' + (i === 1 && arr[0].indexOf('樣本') === 0 ? ' rr-w' : '') + '">' +
        window.TSA.esc(t) + '</span>';
    }).join('');
  },
  /* 摺疊／展開持久化（架構 ③：記住上次篩選） */
  store: {
    get: function (k, d) {
      try { var v = sessionStorage.getItem('tsa_rk_' + k); return v === null ? d : JSON.parse(v); }
      catch (e) { return d; }
    },
    set: function (k, v) {
      try { sessionStorage.setItem('tsa_rk_' + k, JSON.stringify(v)); } catch (e) { }
    }
  },
  /* 手機抽屜 nav */
  initNav: function () {
    var d = document.getElementById('navDrawer'), b = document.getElementById('burgerBtn'),
      x = document.getElementById('navDrawerClose');
    if (!d || !b || !x) return;
    function open() { d.hidden = false; b.setAttribute('aria-expanded', 'true'); x.focus(); }
    function close() { d.hidden = true; b.setAttribute('aria-expanded', 'false'); b.focus(); }
    b.addEventListener('click', open);
    x.addEventListener('click', close);
    d.addEventListener('click', function (e) { if (e.target === d) close(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !d.hidden) close(); });
  },
  /* 讀 JSON */
  load: function (url) {
    return fetch(url).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status + ' — ' + url);
      return r.json();
    });
  },
  /* 錯誤畫面 */
  fail: function (box, err) {
    box.innerHTML = '<div class="err"><b>數據載入失敗</b><br>' +
      window.TSA.esc(err.message || err) +
      '<br><span style="color:var(--text2);font-size:12px">' +
      '若用 <code>file://</code> 直接開檔，瀏覽器會封鎖 JSON 讀取。' +
      '請改用 HTTP（本機 <code>python3 -m http.server</code> 或 GitHub Pages）。</span></div>';
  }
};
