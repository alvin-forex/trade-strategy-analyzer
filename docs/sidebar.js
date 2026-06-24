/* TSA Sidebar Navigation JS - 統一導航 + 主題切換 */
(function(){
  // === 主題初始化（必須最先執行，避免閃屏）===
  var savedTheme = localStorage.getItem('tsa-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);

  // === 計算相對路徑深度 ===
  var path = window.location.pathname;
  var depth = '';
  if(path.includes('/admin/ccy_power/') || path.includes('/admin/forex_reports/') || path.includes('/admin/forex_hub/') || path.includes('/reviews/') || path.includes('/reports/') || path.includes('/portfolios/')) depth='../../';
  else if(path.includes('/admin/')) depth='../';
  else if(path.includes('/admin/') === false && (path.includes('/data/') || path.includes('/downloads/'))) depth='../';

  // === 建立 Sidebar HTML ===
  var sidebar = document.createElement('nav');
  sidebar.className = 'sidebar';
  sidebar.id = 'tsa-sidebar';
  sidebar.innerHTML = `
    <div class="sidebar-logo">
      <a href="${depth}index.html">🦀 TSA</a>
      <div class="sub">Trade Strategy Analyzer</div>
    </div>
    <div class="sidebar-links">
      <a href="${depth}index.html" class="sidebar-link" data-page="index"><span class="icon">🏠</span>首頁</a>
      <a href="${depth}admin/signal_ranking.html" class="sidebar-link" data-page="signal_ranking"><span class="icon">🏆</span>Signal 排名</a>
      <a href="${depth}admin/ccy_ranking.html" class="sidebar-link" data-page="ccy_ranking"><span class="icon">💱</span>CCY 排名</a>
      <a href="${depth}admin/volatility.html" class="sidebar-link" data-page="volatility"><span class="icon">📊</span>波幅表</a>
      <a href="${depth}portfolios/portfolio_master_report_v2.html" class="sidebar-link" data-page="portfolios"><span class="icon">💼</span>Portfolio V2</a>
      <a href="${depth}review_filter.html" class="sidebar-link" data-page="review_filter"><span class="icon">🔍</span>覆盤報告 Filter</a>
      <div class="sidebar-sep"></div>
      <a href="${depth}reviews/" class="sidebar-link" data-page="reviews"><span class="icon">📅</span>覆盤報告</a>
      <a href="${depth}admin/ccy_power/index.html" class="sidebar-link" data-page="ccy_power"><span class="icon">⚡</span>CCY Power</a>
      <a href="${depth}admin/forex_news.html" class="sidebar-link" data-page="forex_news"><span class="icon">📄</span>外匯新聞</a>
      <div class="sidebar-sep"></div>
      <div class="sidebar-section-title"><span class="icon">📊</span>外匯分析</div>
      <a href="${depth}admin/forex_hub/index.html#4h" class="sidebar-link sub-link" data-page="forex_hub_4h"><span class="icon">🦀</span>4H 市場分析</a>
      <a href="${depth}admin/forex_hub/index.html#daily" class="sidebar-link sub-link" data-page="forex_hub_daily"><span class="icon">📰</span>每日報告</a>
    </div>
    <!-- 主題切換按鈕（底部）-->
    <div class="sidebar-footer">
      <button class="sidebar-theme-toggle" id="tsa-theme-btn" title="切換亮/暗模式">
        <span class="theme-icon">🌙</span>
        <span class="theme-label">深色模式</span>
      </button>
    </div>
  `;

  // === Mobile 漢堡按鈕 ===
  var toggle = document.createElement('button');
  toggle.className = 'sidebar-toggle';
  toggle.id = 'tsa-sidebar-toggle';
  toggle.innerHTML = '☰';
  toggle.setAttribute('aria-label', '開啟選單');
  toggle.onclick = function(){
    sidebar.classList.toggle('open');
    var ov = document.getElementById('tsa-overlay');
    if(ov) ov.classList.toggle('show');
  };

  // === Mobile 遮罩 ===
  var overlay = document.createElement('div');
  overlay.className = 'sidebar-overlay';
  overlay.id = 'tsa-overlay';
  overlay.onclick = function(){
    sidebar.classList.remove('open');
    overlay.classList.remove('show');
  };

  // === 插入 DOM ===
  document.body.appendChild(sidebar);
  document.body.appendChild(toggle);
  document.body.appendChild(overlay);
  document.body.classList.add('has-sidebar');

  // === 主題切換功能 ===
  var themeBtn = document.getElementById('tsa-theme-btn');
  var themeIcon = sidebar.querySelector('.theme-icon');
  var themeLabel = sidebar.querySelector('.theme-label');

  function updateThemeUI(theme){
    if(theme === 'dark'){
      themeIcon.textContent = '☀️';
      themeLabel.textContent = '淺色模式';
    } else {
      themeIcon.textContent = '🌙';
      themeLabel.textContent = '深色模式';
    }
  }

  // 初始化按鈕 UI
  updateThemeUI(savedTheme);

  // 主題切換事件
  if(themeBtn){
    themeBtn.onclick = function(){
      var current = document.documentElement.getAttribute('data-theme');
      var next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      localStorage.setItem('tsa-theme', next);
      updateThemeUI(next);
      // 觸發自訂事件，等頁面內容可選擇性更新
      window.dispatchEvent(new CustomEvent('tsa-theme-change', {detail:{theme:next}}));
    };
  }

  // === 高亮當前頁面 ===
  var filename = path.split('/').pop().replace('.html','');
  var links = sidebar.querySelectorAll('.sidebar-link');
  links.forEach(function(link){
    var dp = link.getAttribute('data-page');
    if(dp==='index' && (filename==='index' || filename==='dashboard')) link.classList.add('active');
    else if(dp==='signal_ranking' && (filename==='signal_ranking' || filename==='signal_ranking_dde_v5')) link.classList.add('active');
    else if(dp==='ccy_ranking' && filename==='ccy_ranking') link.classList.add('active');
    else if(dp==='volatility' && (filename==='volatility' || filename==='ccy_timeframe_volatility')) link.classList.add('active');
    else if(dp==='ccy_power' && (path.includes('/admin/ccy_power/') || filename==='ccy_power')) link.classList.add('active');
    else if(dp==='forex_news' && (filename==='forex_news' || path.includes('/admin/forex_reports/'))) link.classList.add('active');
    else if(dp==='portfolios' && path.includes('/portfolios/')) link.classList.add('active');
    else if(dp==='reviews' && path.includes('/reviews/')) link.classList.add('active');
    else if(dp==='review_filter' && filename==='review_filter') link.classList.add('active');
    else if(dp==='forex_hub_4h' && (path.includes('/admin/forex_hub/') || path.includes('/admin/4h_reports/') || path.includes('/reports/'))) link.classList.add('active');
    else if(dp==='forex_hub_daily' && path.includes('/admin/forex_hub/') && window.location.hash==='#daily') link.classList.add('active');
    else if(dp!=='index' && filename.includes(dp)) link.classList.add('active');
  });
})();
