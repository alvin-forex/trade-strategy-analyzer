/**
 * Martin Autopsy V4 — Core Computation Engine
 * 純 JavaScript 計算邏輯，唔加公式，只用 CSV 真實數據
 */

// ═══════════════════════════════════════════════════════
// CSV Parser
// ═══════════════════════════════════════════════════════

function parseCSV(text) {
    const lines = text.trim().split('\n');
    if (lines.length < 2) return [];
    
    const headers = lines[0].split(',').map(h => h.trim());
    const trades = [];
    
    for (let i = 1; i < lines.length; i++) {
        const values = parseCSVLine(lines[i]);
        if (values.length < headers.length) continue;
        
        const row = {};
        headers.forEach((h, idx) => row[h] = values[idx]);
        
        const type = (row['Type'] || '').trim().toLowerCase();
        if (type !== 'buy' && type !== 'sell') continue;
        
        const symbol = (row['Symbol'] || '').trim();
        if (!symbol) continue;
        
        const trade = {
            symbol,
            direction: type,
            lots: Math.abs(parseFloat(row['Lots']) || 0),
            net_profit: parseFloat(row['Net Profit']) || 0,
            net_pips: parseFloat(row['Net Pips']) || 0,
            max_profit: parseFloat(row['Max Profit']) || 0,
            max_loss: parseFloat(row['Max Loss']) || 0,
            mfe: parseFloat(row['Max Pips']) || 0,
            mae: Math.abs(parseFloat(row['Max Loss Pips']) || 0),
            holding_hours: parseFloat(row['Holding Time (Hours)']) || 0,
            commission: parseFloat(row['Commission']) || 0,
            swap: parseFloat(row['Swap']) || 0,
            comment: (row['Comment'] || '').trim(),
            open_time: (row['Open Time'] || '').trim(),
            close_time: (row['Close Time'] || '').trim(),
            _openDate: null,  // parsed Date object
        };
        
        // Parse date
        try {
            const parts = trade.open_time.split(/[/\s:]+/);
            if (parts.length >= 6) {
                trade._openDate = new Date(
                    parseInt(parts[2]), parseInt(parts[1]) - 1, parseInt(parts[0]),
                    parseInt(parts[3]), parseInt(parts[4]), parseInt(parts[5])
                );
            }
        } catch (e) {}
        
        trades.push(trade);
    }
    
    return trades;
}

function parseCSVLine(line) {
    const result = [];
    let current = '';
    let inQuotes = false;
    
    for (let i = 0; i < line.length; i++) {
        const ch = line[i];
        if (ch === '"') {
            inQuotes = !inQuotes;
        } else if (ch === ',' && !inQuotes) {
            result.push(current.trim());
            current = '';
        } else {
            current += ch;
        }
    }
    result.push(current.trim());
    return result;
}

// ═══════════════════════════════════════════════════════
// Date Filtering
// ═══════════════════════════════════════════════════════

function filterByDateRange(trades, fromDate, toDate) {
    if (!fromDate && !toDate) return trades;
    
    return trades.filter(t => {
        if (!t._openDate) return false;
        if (fromDate && t._openDate < fromDate) return false;
        if (toDate && t._openDate > toDate) return false;
        return true;
    });
}

function getDateRange(trades) {
    const dates = trades.filter(t => t._openDate).map(t => t._openDate.getTime());
    if (dates.length === 0) return { min: null, max: null };
    return {
        min: new Date(Math.min(...dates)),
        max: new Date(Math.max(...dates)),
    };
}

// ═══════════════════════════════════════════════════════
// Layer Assignment
// ═══════════════════════════════════════════════════════

function assignLayerIndex(lotsList) {
    const unique = [...new Set(lotsList)].sort((a, b) => a - b);
    const map = {};
    unique.forEach((lot, idx) => map[lot] = idx + 1);
    return map;
}

// ═══════════════════════════════════════════════════════
// Core Stats Computation
// ═══════════════════════════════════════════════════════

function computeLayerStats(trades) {
    // Group by (CCY, Direction)
    const ccyDirMap = {};
    for (const t of trades) {
        const key = `${t.symbol}_${t.direction}`;
        if (!ccyDirMap[key]) ccyDirMap[key] = [];
        ccyDirMap[key].push(t);
    }
    
    const results = {};
    
    for (const [ccyDirKey, ccyTrades] of Object.entries(ccyDirMap)) {
        // Compute layer index
        const lotsInGroup = [...new Set(ccyTrades.map(t => t.lots))].sort((a, b) => a - b);
        const lotToIdx = {};
        lotsInGroup.forEach((lot, idx) => lotToIdx[lot] = idx + 1);
        const maxDepth = lotsInGroup.length;
        
        // Group by layer
        const layerMap = {};
        for (const t of ccyTrades) {
            const label = `L${t.lots}`;
            if (!layerMap[label]) layerMap[label] = [];
            layerMap[label].push(t);
        }
        
        for (const [layerLabel, lt] of Object.entries(layerMap)) {
            const n = lt.length;
            if (n === 0) continue;
            
            const wins = lt.filter(t => t.net_profit > 0);
            const losses = lt.filter(t => t.net_profit <= 0);
            const winCount = wins.length;
            const lossCount = losses.length;
            
            const wr = n > 0 ? (winCount / n * 100) : 0;
            const totalPnl = lt.reduce((s, t) => s + t.net_profit, 0);
            const avgWin = winCount > 0 ? wins.reduce((s, t) => s + t.net_profit, 0) / winCount : 0;
            const avgLoss = lossCount > 0 ? Math.abs(losses.reduce((s, t) => s + t.net_profit, 0) / lossCount) : 0;
            
            // Expected Value
            const ev = (wr / 100 * avgWin) - ((1 - wr / 100) * avgLoss);
            
            const avgWinPips = winCount > 0 ? wins.reduce((s, t) => s + t.net_pips, 0) / winCount : 0;
            const avgLossPips = lossCount > 0 ? Math.abs(losses.reduce((s, t) => s + t.net_pips, 0) / lossCount) : 0;
            
            const oddsDollar = avgLoss > 0 ? avgWin / avgLoss : 999;
            const oddsPips = avgLossPips > 0 ? avgWinPips / avgLossPips : 999;
            
            const avgHold = lt.reduce((s, t) => s + t.holding_hours, 0) / n;
            
            // MFE/MAE
            const mfeValues = lt.map(t => t.mfe);
            const maeValues = lt.map(t => t.mae);
            const sortedMfe = [...mfeValues].sort((a, b) => a - b);
            const sortedMae = [...maeValues].sort((a, b) => a - b);
            
            const avgMfe = mfeValues.reduce((s, v) => s + v, 0) / n;
            const maxMfe = Math.max(...mfeValues);
            const medMfe = sortedMfe[Math.floor(n / 2)];
            
            const avgMae = maeValues.reduce((s, v) => s + v, 0) / n;
            const maxMae = Math.max(...maeValues);
            const medMae = sortedMae[Math.floor(n / 2)];
            
            const sampleLots = lt[0].lots;
            const layerIdx = lotToIdx[sampleLots] || 1;
            
            const key = `${ccyDirKey}_${layerLabel}`;
            results[key] = {
                symbol: ccyDirKey.split('_')[0],
                direction: ccyDirKey.split('_')[1],
                layer_label: layerLabel,
                lots: sampleLots,
                layer_idx: layerIdx,
                max_depth: maxDepth,
                count: n,
                win_count: winCount,
                loss_count: lossCount,
                wr: round2(wr),
                total_pnl: round2(totalPnl),
                ev: round2(ev),
                avg_win: round2(avgWin),
                avg_loss: round2(avgLoss),
                avg_win_pips: round2(avgWinPips),
                avg_loss_pips: round2(avgLossPips),
                odds_dollar: oddsDollar < 100 ? round2(oddsDollar) : 999,
                odds_pips: oddsPips < 100 ? round2(oddsPips) : 999,
                avg_hold: round2(avgHold),
                avg_mfe: round2(avgMfe),
                max_mfe: round2(maxMfe),
                med_mfe: round2(medMfe),
                avg_mae: round2(avgMae),
                max_mae: round2(maxMae),
                med_mae: round2(medMae),
                // Trade details for scatter plots
                trade_details: lt.map(t => ({
                    net_pips: t.net_pips,
                    mfe: t.mfe,
                    mae: t.mae,
                    net_profit: t.net_profit,
                    is_win: t.net_profit > 0,
                    lots: t.lots,
                    holding_hours: t.holding_hours,
                })),
            };
        }
    }
    
    return results;
}

// ═══════════════════════════════════════════════════════
// Rating System
// ═══════════════════════════════════════════════════════

function computeRating(stats) {
    const score = computeScore(stats);
    if (score >= 85) return 'S+';
    if (score >= 70) return 'S';
    if (score >= 55) return 'A';
    if (score >= 40) return 'B';
    if (score >= 25) return 'C';
    if (score >= 15) return 'D';
    return 'E';
}

function computeScore(stats) {
    const wr = stats.wr;
    const ev = stats.ev;
    const odds = Math.min(stats.odds_pips, stats.odds_dollar);
    const count = stats.count;
    const hold = stats.avg_hold;
    
    let score = 0;
    
    // WR (0-30)
    score += wr >= 80 ? 30 : wr >= 70 ? 25 : wr >= 60 ? 18 : wr >= 50 ? 10 : Math.max(0, wr / 5);
    // EV (0-30)
    score += ev >= 20 ? 30 : ev >= 10 ? 25 : ev >= 5 ? 18 : ev >= 0 ? 10 : Math.max(0, 10 + ev / 2);
    // Odds (0-20)
    score += odds >= 2.0 ? 20 : odds >= 1.5 ? 15 : odds >= 1.0 ? 10 : Math.max(0, odds * 10);
    // Count (0-15)
    score += count >= 10 ? 15 : count >= 5 ? 12 : count >= 3 ? 8 : Math.max(0, count * 2);
    // Hold (0-5)
    score += hold <= 24 ? 5 : hold <= 72 ? 4 : hold <= 168 ? 3 : hold <= 360 ? 2 : 1;
    
    return Math.round(score * 10) / 10;
}

// ═══════════════════════════════════════════════════════
// Summary Stats
// ═══════════════════════════════════════════════════════

function computeSummary(trades) {
    const n = trades.length;
    if (n === 0) return { count: 0, win_pct: 0, total_pnl: 0, symbols: 0, layers: 0, best_ccy: '', best_pnl: 0 };
    
    const wins = trades.filter(t => t.net_profit > 0).length;
    const totalPnl = trades.reduce((s, t) => s + t.net_profit, 0);
    const symbols = new Set(trades.map(t => t.symbol)).size;
    const lots = new Set(trades.map(t => t.lots)).size;
    
    // Best CCY
    const ccyPnl = {};
    for (const t of trades) {
        ccyPnl[t.symbol] = (ccyPnl[t.symbol] || 0) + t.net_profit;
    }
    let bestCcy = '';
    let bestPnl = -Infinity;
    for (const [ccy, pnl] of Object.entries(ccyPnl)) {
        if (pnl > bestPnl) { bestPnl = pnl; bestCcy = ccy; }
    }
    
    return {
        count: n,
        win_pct: round2(wins / n * 100),
        total_pnl: round2(totalPnl),
        symbols,
        layers: lots,
        best_ccy: bestCcy,
        best_pnl: round2(bestPnl),
    };
}

// ═══════════════════════════════════════════════════════
// TP/SL Suggestions
// ═══════════════════════════════════════════════════════

function computeTPSL(layerStats) {
    const suggestions = [];
    for (const [key, s] of Object.entries(layerStats)) {
        const rating = computeRating(s);
        if (['S+', 'S', 'A'].includes(rating) && s.count >= 3) {
            suggestions.push({
                key,
                symbol: s.symbol,
                direction: s.direction,
                layer: s.layer_label,
                lots: s.lots,
                rating,
                score: computeScore(s),
                wr: s.wr,
                count: s.count,
                // TP = 80% of avg MFE pips
                suggest_tp: round2(s.avg_mfe * 0.8),
                // SL = 120% of avg MAE pips  
                suggest_sl: round2(s.avg_mae * 1.2),
                avg_mfe: s.avg_mfe,
                avg_mae: s.avg_mae,
                max_mae: s.max_mae,
            });
        }
    }
    return suggestions.sort((a, b) => b.score - a.score);
}

// ═══════════════════════════════════════════════════════
// Blacklist
// ═══════════════════════════════════════════════════════

function computeBlacklist(layerStats) {
    const blacklist = [];
    for (const [key, s] of Object.entries(layerStats)) {
        const rating = computeRating(s);
        if (['D', 'E'].includes(rating) && s.count >= 2) {
            const dangerScore = (100 - computeScore(s)) + Math.abs(s.ev);
            blacklist.push({
                key,
                symbol: s.symbol,
                direction: s.direction,
                layer: s.layer_label,
                lots: s.lots,
                rating,
                score: computeScore(s),
                danger_score: round2(dangerScore),
                wr: s.wr,
                ev: s.ev,
                count: s.count,
                total_pnl: s.total_pnl,
                reason: getDangerReason(s),
            });
        }
    }
    return blacklist.sort((a, b) => b.danger_score - a.danger_score);
}

function getDangerReason(s) {
    const reasons = [];
    if (s.wr < 40) reasons.push('WR<40%');
    if (s.ev < 0) reasons.push('EV<0');
    if (s.total_pnl < -50) reasons.push('P&L<-50');
    if (s.odds_dollar < 0.5) reasons.push('RR<0.5');
    if (s.avg_hold > 360) reasons.push('Hold>15d');
    return reasons.join(', ') || 'Underperforming';
}

// ═══════════════════════════════════════════════════════
// Recovery Plan
// ═══════════════════════════════════════════════════════

function computeRecovery(layerStats) {
    const recovery = [];
    for (const [key, s] of Object.entries(layerStats)) {
        const rating = computeRating(s);
        if (['C', 'D', 'E'].includes(rating) && s.count >= 2) {
            const topLayers = Object.values(layerStats)
                .filter(x => x.symbol === s.symbol && x.direction === s.direction && ['S+', 'S', 'A', 'B'].includes(computeRating(x)))
                .sort((a, b) => b.wr - a.wr);
            
            recovery.push({
                key,
                symbol: s.symbol,
                direction: s.direction,
                layer: s.layer_label,
                rating,
                wr: s.wr,
                ev: s.ev,
                count: s.count,
                suggestion: topLayers.length > 0 
                    ? `Reduce ${s.layer_label} (${s.lots} lots), reallocate to ${topLayers[0].layer_label} (${topLayers[0].lots} lots, WR ${topLayers[0].wr}%)`
                    : `Consider disabling ${s.symbol} ${s.direction} at ${s.layer_label}`,
            });
        }
    }
    return recovery;
}

// ═══════════════════════════════════════════════════════
// CCY×Direction Summary
// ═══════════════════════════════════════════════════════

function buildCCYDirectionSummary(layerStats) {
    const ccyDirMap = {};
    for (const [key, s] of Object.entries(layerStats)) {
        const ccyDir = `${s.symbol}_${s.direction}`;
        if (!ccyDirMap[ccyDir]) ccyDirMap[ccyDir] = [];
        ccyDirMap[ccyDir].push(s);
    }
    
    const summary = [];
    for (const [ccyDir, layers] of Object.entries(ccyDirMap)) {
        const totalPnl = layers.reduce((s, l) => s + l.total_pnl, 0);
        const totalCount = layers.reduce((s, l) => s + l.count, 0);
        const totalWins = layers.reduce((s, l) => s + l.win_count, 0);
        const avgWr = totalCount > 0 ? totalWins / totalCount * 100 : 0;
        
        const ratings = layers.map(l => computeRating(l));
        const bestRating = ratings.includes('S+') ? 'S+' : ratings.includes('S') ? 'S' : ratings.includes('A') ? 'A' : ratings.includes('B') ? 'B' : 'C';
        
        summary.push({
            symbol: layers[0].symbol,
            direction: layers[0].direction,
            layers: layers.length,
            total_pnl: round2(totalPnl),
            total_count: totalCount,
            avg_wr: round2(avgWr),
            best_rating: bestRating,
        });
    }
    
    return summary.sort((a, b) => b.total_pnl - a.total_pnl);
}

// ═══════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════

function round2(v) {
    return Math.round(v * 100) / 100;
}

function fmtPnl(v) {
    return v >= 0 ? `+${v.toLocaleString('en', {minimumFractionDigits: 1, maximumFractionDigits: 1})}` 
                  : v.toLocaleString('en', {minimumFractionDigits: 1, maximumFractionDigits: 1});
}

function ratingClass(r) {
    const map = { 'S+': 'rating-sp', 'S': 'rating-s', 'A': 'rating-a', 'B': 'rating-b', 'C': 'rating-c', 'D': 'rating-d', 'E': 'rating-e' };
    return map[r] || 'rating-e';
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { parseCSV, filterByDateRange, computeLayerStats, computeRating, computeScore, computeSummary, computeTPSL, computeBlacklist, computeRecovery, buildCCYDirectionSummary };
}
