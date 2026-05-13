// ============================================================
// Martin Autopsy V3 — 馬丁剖析法 V3
// Absolute data analysis: EV$, Odds$, MFE/MAE, TP/SL hybrid, Danger Score, Recovery
// ============================================================

function calcMartinV3(trades) {
  if (!trades || !trades.length) return null;

  // 1. Group trades by (Symbol, Direction, Lots)
  const layerMap = {};
  trades.forEach(t => {
    const key = `${t.Symbol}|${t._direction}|${t._lots}`;
    if (!layerMap[key]) layerMap[key] = [];
    layerMap[key].push(t);
  });

  // 2. Compute per-layer stats
  const layerStats = {};
  for (const [key, tlist] of Object.entries(layerMap)) {
    const [sym, dir, lots] = key.split('|');
    const count = tlist.length;
    const wins = tlist.filter(t => t._netProfit > 0);
    const losses = tlist.filter(t => t._netProfit <= 0);
    const winCount = wins.length;
    const lossCount = losses.length;
    const wr = count > 0 ? (winCount / count * 100) : 0;
    const totalPnl = tlist.reduce((s, t) => s + t._netProfit, 0);
    const avgWinPnl = winCount > 0 ? wins.reduce((s, t) => s + t._netProfit, 0) / winCount : 0;
    const avgLossPnl = lossCount > 0 ? Math.abs(losses.reduce((s, t) => s + t._netProfit, 0) / lossCount) : 0;
    const avgWinPips = winCount > 0 ? wins.reduce((s, t) => s + t._netPips, 0) / winCount : 0;
    const avgLossPips = lossCount > 0 ? Math.abs(losses.reduce((s, t) => s + t._netPips, 0) / lossCount) : 0;
    const evDollar = (wr / 100 * avgWinPnl) - ((1 - wr / 100) * avgLossPnl);
    const oddsDollar = avgLossPnl > 0 ? avgWinPnl / avgLossPnl : 999;
    const oddsPips = avgLossPips > 0 ? avgWinPips / avgLossPips : 999;
    const avgHold = count > 0 ? tlist.reduce((s, t) => s + t._holdingHours, 0) / count : 0;

    // MFE/MAE
    const mfeVals = tlist.map(t => t._maxPips);
    const maeVals = tlist.map(t => Math.abs(t._maxLossPips));
    const avgMFE = mfeVals.length ? mfeVals.reduce((s, v) => s + v, 0) / mfeVals.length : 0;
    const maxMFE = mfeVals.length ? Math.max(...mfeVals) : 0;
    const avgMAE = maeVals.length ? maeVals.reduce((s, v) => s + v, 0) / maeVals.length : 0;
    const maxMAE = maeVals.length ? Math.max(...maeVals) : 0;

    // Rating (V3 auto-rating)
    let rating = 'E';
    if (count >= 2) {
      if (evDollar > 50 && oddsDollar > 2 && wr > 70) rating = 'S+';
      else if (evDollar > 20 && oddsDollar > 1.5 && wr > 65) rating = 'S';
      else if (evDollar > 0 && oddsDollar > 1 && wr > 55) rating = 'A';
      else if (evDollar > -20) rating = 'B';
      else if (evDollar > -50) rating = 'C';
      else rating = 'D';
    }

    layerStats[key] = {
      symbol: sym, direction: dir, lots: parseFloat(lots),
      count, winCount, lossCount, winRate: wr,
      totalPnl, avgWinPnl, avgLossPnl,
      avgWinPips, avgLossPips,
      evDollar, oddsDollar, oddsPips, avgHold,
      avgMFE, maxMFE, avgMAE, maxMAE,
      rating, trades: tlist
    };
  }

  // 3. Aggregate CCY×Direction
  const ccyDirMap = {};
  for (const [key, ls] of Object.entries(layerStats)) {
    const ccyKey = `${ls.symbol}|${ls.direction}`;
    if (!ccyDirMap[ccyKey]) ccyDirMap[ccyKey] = { layers: [], lotSet: new Set() };
    ccyDirMap[ccyKey].layers.push(ls);
    ccyDirMap[ccyKey].lotSet.add(ls.lots);
  }

  const ccyDirStats = [];
  for (const [ccyKey, cd] of Object.entries(ccyDirMap)) {
    const [sym, dir] = ccyKey.split('|');
    const layers = cd.layers;
    const totalTrades = layers.reduce((s, l) => s + l.count, 0);
    const totalWins = layers.reduce((s, l) => s + l.winCount, 0);
    const totalPnl = layers.reduce((s, l) => s + l.totalPnl, 0);
    const numLayers = layers.length;
    const maxDepth = cd.lotSet.size;
    const wr = totalTrades > 0 ? totalWins / totalTrades * 100 : 0;
    const evPerLayer = layers.length ? layers.reduce((s, l) => s + l.evDollar, 0) / layers.length : 0;
    const avgWinPip = layers.length ? layers.reduce((s, l) => s + l.avgWinPips, 0) / layers.length : 0;
    const avgLossPip = layers.length ? layers.reduce((s, l) => s + l.avgLossPips, 0) / layers.length : 0;
    const avgOddsD = layers.length ? layers.reduce((s, l) => s + l.oddsDollar, 0) / layers.length : 0;
    const avgOddsP = layers.length ? layers.reduce((s, l) => s + l.oddsPips, 0) / layers.length : 0;
    const avgMFE = layers.length ? layers.reduce((s, l) => s + l.avgMFE, 0) / layers.length : 0;
    const avgMAE = layers.length ? layers.reduce((s, l) => s + l.avgMAE, 0) / layers.length : 0;
    const pairMaxMAE = layers.length ? Math.max(...layers.map(l => l.maxMAE)) : 0;

    ccyDirStats.push({
      symbol: sym, direction: dir, trades: totalTrades,
      numLayers, maxDepth, totalPnl, winRate: wr,
      evPerLayer, avgWinPip, avgLossPip,
      oddsDollar: avgOddsD, oddsPips: avgOddsP,
      avgMFE, avgMAE, pairMaxMAE,
      layers: layers.sort((a, b) => a.lots - b.lots)
    });
  }
  ccyDirStats.sort((a, b) => b.totalPnl - a.totalPnl);

  // 4. TP/SL for A-grade+ layers
  const aGradeLayers = Object.values(layerStats)
    .filter(l => ['S+', 'S', 'A'].includes(l.rating) && l.count >= 2)
    .map(l => {
      const pairKey = `${l.symbol}|${l.direction}`;
      const pairMaxMAE = ccyDirStats.find(c => c.symbol === l.symbol && c.direction === l.direction)?.pairMaxMAE || l.maxMAE;
      const tp = l.avgMFE;
      const softSL = l.avgMAE * 1.2;
      const hardSL = pairMaxMAE * 1.3;
      const rr = softSL > 0 ? tp / softSL : 0;
      return { ...l, tp, softSL, hardSL, rr, pairMaxMAE };
    });

  const ratingOrder = { 'S+': 0, 'S': 1, 'A': 2 };
  aGradeLayers.sort((a, b) => (ratingOrder[a.rating] || 9) - (ratingOrder[b.rating] || 9) || b.evDollar - a.evDollar);

  // 5. Blacklist
  const blacklist = [];
  for (const cd of ccyDirStats) {
    let danger = 0;
    if (cd.totalPnl < 0) danger += Math.abs(cd.totalPnl) / 1000;
    if (cd.oddsDollar < 1.0) danger += 3;
    if (cd.winRate < 50) danger += 2;
    if (cd.evPerLayer < 0) danger += Math.abs(cd.evPerLayer) / 10;
    const worstEv = Math.min(...cd.layers.map(l => l.evDollar));
    if (worstEv < -50) danger += 2;
    if (danger > 0) {
      const worstLayer = cd.layers.reduce((worst, l) => l.evDollar < worst.evDollar ? l : worst, cd.layers[0]);
      blacklist.push({
        symbol: cd.symbol, direction: cd.direction,
        dangerScore: danger,
        level: danger > 5 ? '💀 DEADLY' : '⚠️ WARNING',
        totalPnl: cd.totalPnl, winRate: cd.winRate,
        oddsDollar: cd.oddsDollar,
        worstLayerLots: worstLayer.lots,
        worstEv: worstLayer.evDollar
      });
    }
  }
  blacklist.sort((a, b) => b.dangerScore - a.dangerScore);

  // 6. Recovery
  const recovery = [];
  for (const cd of ccyDirStats) {
    const deepest = cd.layers[cd.layers.length - 1];
    const worstLoss = deepest && deepest.lossCount > 0 ? deepest.avgLossPnl : 0;
    const bestLayer = cd.layers.reduce((best, l) => l.evDollar > best.evDollar ? l : best, cd.layers[0]);
    const bestEv = bestLayer ? bestLayer.evDollar : 0;
    const recoveryTrades = (bestEv > 0 && worstLoss > 0) ? worstLoss / bestEv : 999;
    let status, statusEmoji;
    if (recoveryTrades > 20 || bestEv <= 0) { status = '🔴 無法恢復'; statusEmoji = '🔴'; }
    else if (recoveryTrades > 5) { status = '🟡 需時'; statusEmoji = '🟡'; }
    else { status = '🟢 安全'; statusEmoji = '🟢'; }
    recovery.push({
      symbol: cd.symbol, direction: cd.direction,
      worstLoss, bestEv, bestLayerLots: bestLayer ? bestLayer.lots : 0,
      recoveryTrades, status, statusEmoji
    });
  }
  recovery.sort((a, b) => a.recoveryTrades - b.recoveryTrades);

  // Summary counts
  const posEvCount = Object.values(layerStats).filter(l => l.evDollar > 0).length;
  const negEvCount = Object.values(layerStats).filter(l => l.evDollar <= 0).length;
  const totalPnl = ccyDirStats.reduce((s, c) => s + c.totalPnl, 0);
  const unrecoverableCount = recovery.filter(r => r.recoveryTrades > 20 || r.recoveryTrades === 999).length;

  return {
    layerStats: Object.values(layerStats),
    ccyDirStats,
    aGradeLayers,
    blacklist,
    recovery,
    summary: {
      totalLayers: Object.keys(layerStats).length,
      totalCcyDir: ccyDirStats.length,
      posEvCount, negEvCount,
      totalPnl,
      blacklistCount: blacklist.length,
      aGradeCount: aGradeLayers.length,
      unrecoverableCount
    }
  };
}

// ============================================================
// Render Martin V3
// ============================================================

function renderMartinV3(data) {
  if (!data) { $('martinV3Analysis').innerHTML = '<p style="color:#999">數據不足，需要馬丁策略交易數據</p>'; return; }

  const s = data.summary;
  let html = '';

  // Summary cards
  html += '<div class="stats-grid" style="margin-bottom:20px">';
  html += statBox(s.totalLayers, '層級組合', '');
  html += statBox(s.totalCcyDir, 'CCY×Dir', '');
  html += statBox(s.posEvCount, '正 EV 層', 'positive');
  html += statBox(s.negEvCount, '負 EV 層', 'negative');
  html += statBox('$' + fmt(s.totalPnl, 0), '總 P&L', s.totalPnl >= 0 ? 'positive' : 'negative');
  html += statBox(s.blacklistCount, '黑名單', s.blacklistCount > 0 ? 'negative' : '');
  html += statBox(s.aGradeCount, 'A級+ 層', 'positive');
  html += statBox(s.unrecoverableCount, '無法恢復', s.unrecoverableCount > 0 ? 'negative' : '');
  html += '</div>';

  // === Part 1: CCY×Direction Table ===
  html += '<h3 style="color:var(--primary);margin:20px 0 12px;border-bottom:2px solid var(--primary);padding-bottom:6px">📊 Part 1：CCY × Direction 詳細分析表</h3>';
  html += '<p style="color:var(--text2);font-size:0.82em;margin-bottom:10px">按 Total$ 降序 | EV$ = (WR×AvgWin$) − ((1−WR)×AvgLoss$) | Odds$ = AvgWin$ / AvgLoss$</p>';
  html += '<div class="table-wrap"><table class="data-table">';
  html += '<tr><th>#</th><th>CCY</th><th>Dir</th><th>Trades</th><th>Layers</th><th>MaxD</th><th>Total$</th><th>WR%</th><th>EV$/L</th><th>Win Pip</th><th>Loss Pip</th><th>Odds$</th><th>OddsPip</th><th>AvgMFE</th><th>AvgMAE</th><th>MaxMAE</th></tr>';

  data.ccyDirStats.forEach((cd, i) => {
    const bg = cd.totalPnl > 500 ? '#d4edda' : cd.totalPnl > 0 ? '#fff3cd' : '#f8d7da';
    const evColor = cd.evPerLayer > 0 ? 'var(--green)' : 'var(--red)';
    const oddsColor = cd.oddsDollar > 1 ? 'var(--green)' : cd.oddsDollar > 0.5 ? 'var(--yellow)' : 'var(--red)';
    html += `<tr style="background:${bg}">
      <td><strong>${i + 1}</strong></td>
      <td><strong>${cd.symbol}</strong></td><td>${cd.direction}</td>
      <td>${cd.trades}</td><td>${cd.numLayers}</td><td>${cd.maxDepth}</td>
      <td style="font-weight:700">$${fmt(cd.totalPnl)}</td>
      <td>${pct(cd.winRate)}</td>
      <td style="color:${evColor};font-weight:700">$${fmt(cd.evPerLayer)}</td>
      <td>${fmt(cd.avgWinPip, 1)}</td><td>${fmt(cd.avgLossPip, 1)}</td>
      <td style="color:${oddsColor}">${fmt(cd.oddsDollar)}x</td>
      <td>${fmt(cd.oddsPips)}x</td>
      <td style="color:var(--green)">${fmt(cd.avgMFE, 1)}</td>
      <td style="color:var(--orange)">${fmt(cd.avgMAE, 1)}</td>
      <td style="color:var(--red);font-weight:700">${fmt(cd.pairMaxMAE, 1)}</td>
    </tr>`;
  });
  html += '</table></div>';

  // === Part 2: MFE/MAE Scatter (simplified bar charts per CCY×Dir) ===
  html += '<h3 style="color:var(--primary);margin:20px 0 12px;border-bottom:2px solid var(--primary);padding-bottom:6px">🔬 Part 2：MFE/MAE 層級分析</h3>';
  html += '<p style="color:var(--text2);font-size:0.82em;margin-bottom:10px">每個 CCY×Dir 各層級嘅 MFE（最大有利偏移）同 MAE（最大不利偏移）對比</p>';

  data.ccyDirStats.forEach(cd => {
    html += '<div style="margin-bottom:16px;padding:12px;background:#f8f9fb;border-radius:8px;border:1px solid #e8ecf0">';
    html += `<h4 style="margin:0 0 8px;color:var(--primary)">${cd.symbol} ${cd.direction} (${cd.numLayers} layers)</h4>`;
    html += '<div class="table-wrap"><table class="data-table" style="font-size:0.8em">';
    html += '<tr><th>Layer</th><th>Lots</th><th>Trades</th><th>WR%</th><th>EV$</th><th>Odds$</th><th>AvgMFE</th><th>AvgMAE</th><th>MaxMAE</th></tr>';
    cd.layers.forEach(l => {
      const evColor = l.evDollar > 0 ? 'var(--green)' : 'var(--red)';
      html += `<tr>
        <td>L${l.lots.toFixed(2)}</td><td>${l.lots.toFixed(2)}</td>
        <td>${l.count}</td><td>${pct(l.winRate)}</td>
        <td style="color:${evColor};font-weight:600">$${fmt(l.evDollar)}</td>
        <td>${fmt(l.oddsDollar)}x</td>
        <td style="color:var(--green)">${fmt(l.avgMFE, 1)}</td>
        <td style="color:var(--orange)">${fmt(l.avgMAE, 1)}</td>
        <td style="color:var(--red)">${fmt(l.maxMAE, 1)}</td>
      </tr>`;
    });
    html += '</table></div></div>';
  });

  // === Part 3: TP/SL Hybrid Scheme ===
  html += '<h3 style="color:var(--primary);margin:20px 0 12px;border-bottom:2px solid var(--primary);padding-bottom:6px">🎯 Part 3：A級以上 TP/SL 混合方案</h3>';
  html += '<div style="padding:12px;background:#f0f4ff;border-radius:8px;margin-bottom:12px;font-size:0.82em;color:var(--text2)">';
  html += '<strong style="color:var(--text)">SL 設計原理：</strong><br>';
  html += '🟠 <strong>Soft SL</strong> = Avg MAE × 1.2（正常波動止損）<br>';
  html += '🔴 <strong>Hard SL</strong> = Pair Max MAE × 1.3（極端情況防爆倉）<br>';
  html += '🟢 <strong>TP</strong> = Avg MFE | <strong>R:R</strong> = TP / Soft SL</div>';

  if (data.aGradeLayers.length > 0) {
    html += '<div class="table-wrap"><table class="data-table">';
    html += '<tr><th>Rating</th><th>CCY</th><th>Dir</th><th>Layer</th><th>Trades</th><th>WR%</th><th>EV$</th><th>Odds$</th><th>TP(pip)</th><th>Soft SL</th><th>Hard SL</th><th>R:R</th></tr>';
    data.aGradeLayers.forEach(l => {
      const ratingColor = { 'S+': '#FFD700', 'S': '#28a745', 'A': '#3498db' }[l.rating] || '#666';
      const rrColor = l.rr > 3 ? 'var(--green)' : l.rr > 1.5 ? 'var(--yellow)' : 'var(--red)';
      html += `<tr>
        <td><span style="display:inline-block;padding:2px 8px;border-radius:10px;font-weight:700;font-size:0.85em;color:#000;background:${ratingColor}">${l.rating}</span></td>
        <td><strong>${l.symbol}</strong></td><td>${l.direction}</td>
        <td>L${l.lots.toFixed(2)}</td><td>${l.count}</td><td>${pct(l.winRate)}</td>
        <td style="font-weight:700;color:var(--green)">$${fmt(l.evDollar)}</td>
        <td>${fmt(l.oddsDollar)}x</td>
        <td style="color:var(--green)">${fmt(l.tp, 1)}</td>
        <td style="color:var(--orange)">${fmt(l.softSL, 1)}</td>
        <td style="color:var(--red)">${fmt(l.hardSL, 1)}</td>
        <td style="color:${rrColor};font-weight:700">${fmt(l.rr)}x</td>
      </tr>`;
    });
    html += '</table></div>';
  } else {
    html += '<p style="color:#999">無 A 級以上層級</p>';
  }

  // === Part 4: Ranking ===
  html += '<h3 style="color:var(--primary);margin:20px 0 12px;border-bottom:2px solid var(--primary);padding-bottom:6px">🏅 Part 4：A級以上排行榜</h3>';
  html += '<p style="color:var(--text2);font-size:0.82em;margin-bottom:10px">排序：Rating 降序 → EV$ 降序</p>';

  if (data.aGradeLayers.length > 0) {
    html += '<div class="table-wrap"><table class="data-table">';
    html += '<tr><th>#</th><th>Rating</th><th>CCY</th><th>Dir</th><th>Layer</th><th>Trades</th><th>WR%</th><th>EV$</th><th>Odds$</th><th>OddsPip</th><th>Total$</th><th>AvgHold</th></tr>';
    data.aGradeLayers.forEach((l, i) => {
      const ratingColor = { 'S+': '#FFD700', 'S': '#28a745', 'A': '#3498db' }[l.rating] || '#666';
      const pnlColor = l.totalPnl >= 0 ? 'var(--green)' : 'var(--red)';
      html += `<tr>
        <td><strong>#${i + 1}</strong></td>
        <td><span style="display:inline-block;padding:2px 8px;border-radius:10px;font-weight:700;font-size:0.85em;color:#000;background:${ratingColor}">${l.rating}</span></td>
        <td>${l.symbol}</td><td>${l.direction}</td>
        <td>L${l.lots.toFixed(2)}</td><td>${l.count}</td><td>${pct(l.winRate)}</td>
        <td style="font-weight:700;color:var(--green)">$${fmt(l.evDollar)}</td>
        <td>${fmt(l.oddsDollar)}x</td><td>${fmt(l.oddsPips)}x</td>
        <td style="color:${pnlColor}">$${fmt(l.totalPnl)}</td>
        <td>${fmt(l.avgHold, 1)}h</td>
      </tr>`;
    });
    html += '</table></div>';
  } else {
    html += '<p style="color:#999">無 A 級以上層級</p>';
  }

  // === Part 5: Blacklist ===
  html += '<h3 style="color:var(--primary);margin:20px 0 12px;border-bottom:2px solid var(--primary);padding-bottom:6px">💀 Part 5：黑名單（Danger Score）</h3>';
  html += '<div style="padding:12px;background:#fff0f0;border-radius:8px;margin-bottom:12px;font-size:0.82em;color:var(--text2)">';
  html += '<strong style="color:var(--text)">Danger Score：</strong>';
  html += '① 總虧損/1000 &nbsp; ② Odds$&lt;1 → +3 &nbsp; ③ WR&lt;50% → +2 &nbsp; ④ Avg EV 為負 → |EV|/10 &nbsp; ⑤ 最差層 EV&lt;-$50 → +2<br>';
  html += '💀 DEADLY &gt; 5 | ⚠️ WARNING 1-5</div>';

  if (data.blacklist.length > 0) {
    html += '<div class="table-wrap"><table class="data-table">';
    html += '<tr><th>級別</th><th>CCY</th><th>Dir</th><th>Danger</th><th>Total$</th><th>WR%</th><th>Odds$</th><th>最差層</th></tr>';
    data.blacklist.forEach(bl => {
      html += `<tr>
        <td>${bl.level}</td>
        <td><strong>${bl.symbol}</strong></td><td>${bl.direction}</td>
        <td style="color:var(--red);font-weight:700;font-size:1.1em">${fmt(bl.dangerScore, 1)}</td>
        <td style="font-weight:700">$${fmt(bl.totalPnl)}</td>
        <td>${pct(bl.winRate)}</td><td>${fmt(bl.oddsDollar)}x</td>
        <td>L${bl.worstLayerLots.toFixed(2)} $${fmt(bl.worstEv)}</td>
      </tr>`;
    });
    html += '</table></div>';
  } else {
    html += '<p style="color:var(--green)">✅ 無黑名單組合，所有 CCY×Dir 均為正面</p>';
  }

  // === Part 6: Recovery ===
  html += '<h3 style="color:var(--primary);margin:20px 0 12px;border-bottom:2px solid var(--primary);padding-bottom:6px">🔄 Part 6：恢復力分析</h3>';
  html += '<p style="color:var(--text2);font-size:0.82em;margin-bottom:10px">場景：最深層被 Hard SL 止損，要用最佳 EV 層級贏幾多次先追得返？</p>';

  html += '<div class="table-wrap"><table class="data-table">';
  html += '<tr><th>狀態</th><th>CCY</th><th>Dir</th><th>最深層虧損</th><th>最佳 EV$</th><th>最佳層</th><th>恢復次數</th></tr>';
  data.recovery.forEach(r => {
    const rtDisplay = r.recoveryTrades < 999 ? fmt(r.recoveryTrades, 1) : '∞';
    html += `<tr>
      <td>${r.status}</td>
      <td><strong>${r.symbol}</strong></td><td>${r.direction}</td>
      <td style="color:var(--red)">$${fmt(r.worstLoss)}</td>
      <td style="color:var(--green);font-weight:600">$${fmt(r.bestEv)}</td>
      <td>L${r.bestLayerLots.toFixed(2)}</td>
      <td style="font-weight:700">${rtDisplay}</td>
    </tr>`;
  });
  html += '</table></div>';

  // Conclusion
  const totalPnl = s.totalPnl;
  const topCcy = data.ccyDirStats[0];
  const worstCcy = data.ccyDirStats[data.ccyDirStats.length - 1];
  html += '<div style="margin-top:20px;padding:14px;background:#f8f9fa;border-radius:var(--radius);border-left:4px solid var(--primary)">';
  html += '<strong>📋 馬丁剖析法 V3 結論：</strong><br>';
  html += `共 ${s.totalLayers} 個層級組合，${s.totalCcyDir} 個 CCY×Dir。`;
  html += `正 EV 層 ${s.posEvCount} vs 負 EV 層 ${s.negEvCount}。`;
  if (topCcy) html += `最佳：${topCcy.symbol} ${topCcy.direction}（$${fmt(topCcy.totalPnl)}）。`;
  if (worstCcy && worstCcy.totalPnl < 0) html += `最差：${worstCcy.symbol} ${worstCcy.direction}（$${fmt(worstCcy.totalPnl)}）。`;
  if (s.blacklistCount > 0) html += `<br>⚠️ ${s.blacklistCount} 個黑名單組合需要避開。`;
  if (s.unrecoverableCount > 0) html += `<br>🔴 ${s.unrecoverableCount} 個組合一旦爆 deepest layer 無法恢復。`;
  html += '</div>';

  $('martinV3Analysis').innerHTML = html;
}
