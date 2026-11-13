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
  /* ── 載入加密 JSON（派工v2 §三 方案A：明文唔上 public Pages） ─────────────
     .enc 格式＝hex(HMAC-SHA256)[64] + hex(iv)[32] + hex(AES-CBC cipher)
     key 源＝localStorage「staticrypt_passphrase_general」（staticrypt remember-me
     同一 hashedPassword——頁面解鎖後零二次輸入）；冇記住 → 一次輸入密碼 fallback，
     瀏覽器三輪 PBKDF2（1k SHA-1→14k→585k SHA-256，同 staticrypt 制式）派 key。 */
  PBKDF_SALT: '2f5a7c9e1b3d4f6a8c0e2b4d6f8a1c3e',   // 與全站 staticrypt 同 salt（非秘密）
  PASSPHRASE_KEY: 'staticrypt_passphrase_general',  // /admin/ 頁係 _owner，本雙頁係一般層 _general
  _hex2buf: function (h) {
    var b = new Uint8Array(h.length / 2);
    for (var i = 0; i < b.length; i++) b[i] = parseInt(h.substr(i * 2, 2), 16);
    return b;
  },
  _buf2hex: function (b) {
    return Array.prototype.map.call(new Uint8Array(b), function (x) { return ('0' + x.toString(16)).slice(-2); }).join('');
  },
  _pbkdf2: function (password, salt, iter, hash) {
    return crypto.subtle.importKey('raw', new TextEncoder().encode(password), 'PBKDF2', false, ['deriveBits'])
      .then(function (k) {
        return crypto.subtle.deriveBits({ name: 'PBKDF2', hash: hash, iterations: iter, salt: new TextEncoder().encode(salt) }, k, 256);
      })
      .then(function (bits) { return window.TSA._buf2hex(bits); });
  },
  deriveKey: function (password) {
    var S = window.TSA.PBKDF_SALT, h = window.TSA._pbkdf2;
    return h(password, S, 1000, 'SHA-1')
      .then(function (x) { return h(x, S, 14000, 'SHA-256'); })
      .then(function (x) { return h(x, S, 585000, 'SHA-256'); });
  },
  decryptEnc: function (signed, hashedPasswordHex) {
    var T = window.TSA;
    var hmac = signed.substring(0, 64), iv = T._hex2buf(signed.substring(64, 96)),
        data = T._hex2buf(signed.substring(96));
    var kp = crypto.subtle.importKey('raw', T._hex2buf(hashedPasswordHex), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
      .then(function (hk) { return crypto.subtle.sign('HMAC', hk, new TextEncoder().encode(signed.substring(64))); })
      .then(function (sig) {
        if (T._buf2hex(sig) !== hmac) throw new Error('密碼唔對（HMAC 驗簽失敗）');
      });
    return kp.then(function () {
      return crypto.subtle.importKey('raw', T._hex2buf(hashedPasswordHex), 'AES-CBC', false, ['decrypt'])
        .then(function (k) { return crypto.subtle.decrypt({ name: 'AES-CBC', iv: iv }, k, data); })
        .then(function (pt) { return new TextDecoder().decode(pt); });
    });
  },
  promptFallback: function () {
    var pw = window.prompt('TSA 排名數據已加密——請輸入密碼（與解鎖頁面同一密碼）');
    if (!pw) throw new Error('未輸入密碼');
    return window.TSA.deriveKey(pw);
  },
  load: function (url) {
    var T = window.TSA, encUrl = url + '.enc';
    return fetch(encUrl).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status + ' — ' + encUrl);
      return r.text();
    }).then(function (signed) {
      var hp = null;
      try { hp = localStorage.getItem(T.PASSPHRASE_KEY) || null; } catch (e) { }
      var p = hp ? Promise.resolve(hp) : T.promptFallback();
      return p.then(function (key) {
        return T.decryptEnc(signed, key).then(function (json) {
          try { return JSON.parse(json); }
          catch (e) { throw new Error('解密後 JSON 解析失敗（密文可能損壞）'); }
        }, function (e2) {
          if (hp) { try { localStorage.removeItem(T.PASSPHRASE_KEY); } catch (e) { } }
          throw e2;
        });
      });
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
