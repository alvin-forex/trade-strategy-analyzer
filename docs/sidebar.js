/* TSA Sidebar Navigation JS */
(function(){
  // Determine depth for relative links
  var path = window.location.pathname;
  var depth = '';
  if(path.includes('/admin/ccy/') || path.includes('/admin/ccy_power/')) depth='../../';
  else if(path.includes('/admin/forex_reports/') || path.includes('/admin/forex_reports')) depth='../../';
  else if(path.includes('/admin/') || path.includes('/reports/')) depth='../';

  // Build sidebar HTML
  var sidebar = document.createElement('nav');
  sidebar.className = 'sidebar';
  sidebar.id = 'tsa-sidebar';
  sidebar.innerHTML = `
    <div class="sidebar-logo"><a href="${depth}index.html">🦀 TSA</a><div class="sub">Trade Strategy Analyzer</div></div>
    <div class="sidebar-links">
      <a href="${depth}index.html" class="sidebar-link" data-page="index"><span class="icon">🏠</span>首頁</a>
      <a href="${depth}admin/signal_ranking.html" class="sidebar-link" data-page="signal_ranking"><span class="icon">🏆</span>Signal 排名</a>
      <a href="${depth}admin/ccy_ranking.html" class="sidebar-link" data-page="ccy_ranking"><span class="icon">💱</span>CCY 排名</a>
      <div class="sidebar-sep"></div>
      <a href="${depth}admin/forex_news.html" class="sidebar-link" data-page="forex_news"><span class="icon">📰</span>外匯新聞</a>
      <a href="${depth}admin/ccy_power/index.html" class="sidebar-link" data-page="ccy_power"><span class="icon">⚡</span>CCY Power</a>
      <a href="${depth}admin/volatility.html" class="sidebar-link" data-page="volatility"><span class="icon">📊</span>波幅表</a>
    </div>
  `;

  // Mobile toggle button
  var toggle = document.createElement('button');
  toggle.className='sidebar-toggle';
  toggle.id='tsa-sidebar-toggle';
  toggle.innerHTML='☰';
  toggle.onclick=function(){
    sidebar.classList.toggle('open');
    var ov=document.getElementById('tsa-overlay');
    if(ov) ov.classList.toggle('show');
  };

  // Overlay for mobile
  var overlay = document.createElement('div');
  overlay.className='sidebar-overlay';
  overlay.id='tsa-overlay';
  overlay.onclick=function(){
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
  };

  // Insert sidebar
  document.body.appendChild(sidebar);
  document.body.appendChild(toggle);
  document.body.appendChild(overlay);
  document.body.classList.add('has-sidebar');

  // Highlight active page
  var filename = path.split('/').pop().replace('.html','');
  var links = sidebar.querySelectorAll('.sidebar-link');
  links.forEach(function(link){
    var dp = link.getAttribute('data-page');
    if(dp==='index' && (filename==='index' || filename==='dashboard') && !path.includes('ccy_power')) link.classList.add('active');
    else if(dp==='signal_ranking' && (filename==='signal_ranking' || filename==='signal_ranking_dde_v4')) link.classList.add('active');
    else if(dp==='ccy_ranking' && filename==='ccy_ranking') link.classList.add('active');
    else if(dp==='ccy_power' && (filename==='index' && path.includes('ccy_power'))) link.classList.add('active');
    else if(dp==='volatility' && (filename==='volatility' || filename==='ccy_timeframe_volatility')) link.classList.add('active');
    else if(dp==='deep' && (path.includes('/reports/signal_') || path.includes('Signal_Deep_Analysis'))) link.classList.add('active');
    else if(dp==='forex_news' && filename==='forex_news') link.classList.add('active');
    else if(dp!=='index' && dp!=='deep' && filename.includes(dp)) link.classList.add('active');
  });
})();
