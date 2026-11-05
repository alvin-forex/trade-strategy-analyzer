/* TSA Sidebar Navigation JS - 統一導航 + 主題切換 + 自動注入 CSS */
(function(){
  // 如果喺 iframe 內，唔注入 sidebar（外層 shell 已有）
  if(window !== window.top) return;
  // === 自動注入 sidebar.css（新頁面只需加 <script src="sidebar.js">）===
  var path = window.location.pathname;
  var cssDepth = '';
  /* 2026-11-04 P5：深度邏輯升級 root 層感知——11-01 重組（34b49ae0）後大多數
     子站已落 root 層（ccy_power/portfolios/reviews/reports/4h_reports/
     forex_reports/forex_hub/ccy/downloads/data/home/prd），舊清單只識 admin
     舊路徑 → root 子目錄頁 depth='' 全部 link 死。改：admin/=../，
     root 一層子目錄=../，其餘（root 頁）=''。 */
  /* 2026-11-05 W4：深度通用化——rootSub 白名單只識一層子目錄，reviews/monthly｜
     weekly 兩層頁會出 ../ 死鏈（sidebar nav 半數 404）。改按路徑段數計：
     admin=../；root 內以 path 段數（減檔名）推深度，N 段目錄=N-1 個 ../；
     root 頁=''。對現有 0/1 層頁行為逐頁等價（admin 舊路徑分支照顧）。 */
  if(path.indexOf('/admin/') >= 0) cssDepth='../';
  else {
    var segN = path.split('/').length - 2; /* ['',a,b,file]→2；['',file]→0；['',a,file]→1 */
    cssDepth = segN > 0 ? new Array(segN + 1).join('../') : '';
  }

  // Check if sidebar.css already loaded
  var cssLoaded = false;
  var links = document.querySelectorAll('link[rel="stylesheet"]');
  for(var i=0; i<links.length; i++){
    if(links[i].href.indexOf('sidebar.css') >= 0) { cssLoaded = true; break; }
  }
  if(!cssLoaded){
    var cssLink = document.createElement('link');
    cssLink.rel = 'stylesheet';
    cssLink.href = cssDepth + 'sidebar.css';
    document.head.appendChild(cssLink);
  }

  // === 主題初始化（必須最先執行，避免閃屏）===
  var savedTheme = localStorage.getItem('tsa-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', savedTheme);

  // === 計算相對路徑深度 ===
  var depth = cssDepth; // reuse computed depth

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
      <a href="${depth}admin/index.html" class="sidebar-link" data-page="index"><span class="icon">🏠</span>首頁</a>
      <a href="${depth}signal_ranking.html" class="sidebar-link" data-page="signal_ranking"><span class="icon">🏆</span>Signal 排名</a>
      <!-- #26 (a) 11-04：CCY 排名改指 root 公開層（老闆裁定公開，admin 副本已刪）；
           43/45/46 行同源死 link 一併修——11-01 重組（34b49ae0）搬走 admin 版後
           sidebar 未同步，實檔均在 root 公開層 -->
      <a href="${depth}ccy_ranking.html" class="sidebar-link" data-page="ccy_ranking"><span class="icon">💱</span>CCY 排名</a>
      <a href="${depth}volatility.html" class="sidebar-link" data-page="volatility"><span class="icon">📊</span>波幅表</a>
      <a href="${depth}portfolios/portfolio_master_report_v2.html" class="sidebar-link" data-page="portfolios"><span class="icon">💼</span>Portfolio 統一版</a>
      <div class="sidebar-sep"></div>
      <a href="${depth}reviews/" class="sidebar-link" data-page="reviews"><span class="icon">📅</span>覆盤報告</a>
      <a href="${depth}ccy_power/index.html" class="sidebar-link" data-page="ccy_power"><span class="icon">⚡</span>CCY Power</a>
      <div class="sidebar-sep"></div>
      <div class="sidebar-section-title"><span class="icon">📊</span>外匯分析</div>
      <!-- 2026-11-04 P5：forex_hub 兩條移除——實檔全 repo 不存在（純死 link，實測 404），
           如日後復建請重加。forex_news 改指 root 實檔。 -->
      <a href="${depth}forex_news.html" class="sidebar-link sub-link" data-page="forex_news"><span class="icon">📄</span>外匯新聞</a>
      <div class="sidebar-sep"></div>
      <div class="sidebar-section-title"><span class="icon">🧮</span>工具</div>
      <a href="${depth}tug_of_war_calculator.html" class="sidebar-link sub-link" data-page="tug_of_war"><span class="icon">⚔️</span>拔河計算機</a>
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
    if(dp==='index' && (filename==='index' || filename==='dashboard') && !path.includes('/ccy_power/')) link.classList.add('active');
    else if(dp==='signal_ranking' && filename==='signal_ranking') link.classList.add('active');
    else if(dp==='ccy_ranking' && filename==='ccy_ranking') link.classList.add('active');
    else if(dp==='volatility' && (filename==='volatility' || filename==='ccy_timeframe_volatility')) link.classList.add('active');
    else if(dp==='ccy_power' && (path.includes('/ccy_power/') || filename==='ccy_power')) link.classList.add('active');
    else if(dp==='portfolios' && path.includes('/admin/portfolios/')) link.classList.add('active');
    else if(dp==='reviews' && path.includes('/admin/reviews/')) link.classList.add('active');
    else if(dp==='review_filter' && filename==='review_filter') link.classList.add('active');
    else if(dp==='forex_hub_4h' && (path.includes('/admin/forex_hub/') || path.includes('/admin/4h_reports/') || path.includes('/reports/'))) link.classList.add('active');
    else if(dp==='forex_hub_daily' && path.includes('/admin/forex_hub/') && window.location.hash==='#daily') link.classList.add('active');
    else if(dp!=='index' && filename.includes(dp)) link.classList.add('active');
  });

  // === 通用 Tab 切換邏輯 ===
  document.addEventListener('DOMContentLoaded', function(){
    var tabBtns = document.querySelectorAll('.tab[data-tab], .tab[onclick]');
    tabBtns.forEach(function(btn){
      // Skip if already has onclick handler
      if(btn.getAttribute('onclick')) return;
      btn.addEventListener('click', function(){
        var target = btn.getAttribute('data-tab');
        if(!target) return;
        // Find closest tabs container
        var tabsContainer = btn.closest('.tabs') || btn.parentElement;
        var contentArea = tabsContainer ? tabsContainer.nextElementSibling : null;
        if(!contentArea) {
          // Try finding content as sibling of parent .tabs-layout
          var layout = btn.closest('.tabs-layout');
          if(layout) contentArea = layout.querySelector('.tabs-content');
        }
        if(!contentArea) return;
        // Deactivate all tabs in same container
        tabsContainer.querySelectorAll('.tab').forEach(function(t){ t.classList.remove('active'); });
        btn.classList.add('active');
        // Hide all panels in content area
        contentArea.querySelectorAll('.tab-panel').forEach(function(p){ p.classList.remove('active'); });
        // Show target panel
        var panel = contentArea.querySelector('#' + target);
        if(panel) panel.classList.add('active');
      });
    });
  });
})();
