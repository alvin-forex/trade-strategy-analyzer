/* TSA Supabase 即時數據客戶端（卡 #4 第一版，ZCODE_w 2026-11-27）
   數據源：Supabase REST（匿名 publishable key，RLS 只讀）
   寫入側：OpenClaw service_role（每 15 分鐘 delta-only，唔經呢個檔）
   鐵律：只准 publishable／anon key 入前端；service_role／secret key 絕不入 repo。
   接口：rankings（已用）／signals／positions（已留接口，等正式數據） */
'use strict';
(function () {
  var SUPA_URL = 'https://qbodlutvtkerogwrmcqv.supabase.co';
  /* publishable key（公開只讀，issue #4 明示可放前端） */
  var SUPA_ANON_KEY = 'sb_publishable_j1QloKbZA0NVWg1EnJ1bxA_FRAnxw53';
  var TIMEOUT_MS = 6000;

  /* 帶超時嘅 REST GET；成功回 JSON 陣列，任何失敗 throw（由頁面接住做 fallback） */
  function restGet(table, query) {
    var ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null;
    var timer = ctrl ? setTimeout(function () { ctrl.abort(); }, TIMEOUT_MS) : null;
    var opts = {
      headers: {
        'apikey': SUPA_ANON_KEY,
        'Authorization': 'Bearer ' + SUPA_ANON_KEY
      }
    };
    if (ctrl) opts.signal = ctrl.signal;
    return fetch(SUPA_URL + '/rest/v1/' + table + (query || ''), opts)
      .then(function (r) {
        if (!r.ok) throw new Error('Supabase HTTP ' + r.status + '（' + table + '）');
        return r.json();
      })
      .then(function (data) {
        if (timer) clearTimeout(timer);
        if (!Array.isArray(data)) throw new Error('Supabase 回應非陣列（' + table + '）');
        return data;
      })
      .catch(function (e) {
        if (timer) clearTimeout(timer);
        throw (e && e.name === 'AbortError') ? new Error('Supabase 超時（' + TIMEOUT_MS + 'ms）') : e;
      });
  }

  /* 最新一批 = as_of 最大的嗰組（組合內 rank 升序）；回 { asOf, rows } */
  function latestGroup(rows) {
    if (!rows.length) return { asOf: null, rows: [] };
    var maxAsOf = '';
    rows.forEach(function (r) { if (String(r.as_of) > maxAsOf) maxAsOf = String(r.as_of); });
    var group = rows.filter(function (r) { return String(r.as_of) === maxAsOf; });
    group.sort(function (a, b) {
      var pa = a.payload || {}, pb = b.payload || {};
      return String(pa.portfolio_id || '').localeCompare(String(pb.portfolio_id || ''), 'en') ||
        (a.rank || 0) - (b.rank || 0);
    });
    return { asOf: maxAsOf, rows: group };
  }

  window.TSA = window.TSA || {};
  window.TSA.supa = {
    URL: SUPA_URL,
    ANON_KEY: SUPA_ANON_KEY,
    TIMEOUT_MS: TIMEOUT_MS,
    restGet: restGet,

    /* rankings：portfolio 排名（payload 含 portfolio_id／name／grade／win_rate_3mo／recent_3mo_pnl 等） */
    fetchRankings: function (limit) {
      var q = '?select=as_of,timeframe,symbol,score,rank,payload' +
        '&order=as_of.desc,rank.asc&limit=' + (limit || 200);
      return restGet('rankings', q).then(latestGroup);
    },

    /* signals：即時信號（接口已留；正式數據接入後前端可直接用） */
    fetchSignals: function (limit) {
      var q = '?select=as_of,symbol,action,confidence,payload' +
        '&order=as_of.desc&limit=' + (limit || 200);
      return restGet('signals', q).then(latestGroup);
    },

    /* positions：即時持倉（接口已留；TD EA 匯出接入後前端可直接用） */
    fetchPositions: function (limit) {
      var q = '?select=as_of,account,symbol,lots,pnl,payload' +
        '&order=as_of.desc&limit=' + (limit || 200);
      return restGet('positions', q).then(latestGroup);
    },

    /* health：寫入側心跳（health 表，source=status） */
    fetchHealth: function (limit) {
      var q = '?select=as_of,source,status,payload&order=as_of.desc&limit=' + (limit || 20);
      return restGet('health', q);
    }
  };
})();
