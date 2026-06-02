/**
 * Martin Autopsy V4.1 — Core Computation Engine
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
            symbol, direction: type,
            lots: Math.abs(parseFloat(row['Lots']) || 0),
            open_price: parseFloat(row['Open Price']) || 0,
            close_price: parseFloat(row['Close Price']) || 0,
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
            magic: parseInt(row['Magic Number']) || 0,
            _openDate: null,
        };
        try {
            const parts = trade.open_time.split(/[/\s:]+/);
            if (parts.length >= 6) {
                trade._openDate = new Date(parseInt(parts[2]), parseInt(parts[1]) - 1, parseInt(parts[0]), parseInt(parts[3]), parseInt(parts[4]), parseInt(parts[5]));
            }
        } catch (e) {}
        trades.push(trade);
    }
    return trades;
}

function parseCSVLine(line) {
    const result = []; let current = ''; let inQ = false;
    for (let i = 0; i < line.length; i++) {
        const c = line[i];
        if (c === '"') inQ = !inQ;
        else if (c === ',' && !inQ) { result.push(current.trim()); current = ''; }
        else current += c;
    }
    result.push(current.trim());
    return result;
}

// ═══════════════════════════════════════════════════════
// Date Filtering
// ═══════════════════════════════════════════════════════

function filterByDateRange(trades, from, to) {
    if (!from && !to) return trades;
    return trades.filter(t => {
        if (!t._openDate) return false;
        if (from && t._openDate < from) return false;
        if (to && t._openDate > to) return false;
        return true;
    });
}

function getDateRange(trades) {
    const dates = trades.filter(t => t._openDate).map(t => t._openDate.getTime());
    if (!dates.length) return { min: null, max: null };
    return { min: new Date(Math.min(...dates)), max: new Date(Math.max(...dates)) };
}

// ═══════════════════════════════════════════════════════
// Core Stats
// ═══════════════════════════════════════════════════════

function computeLayerStats(trades) {
    const ccyDirMap = {};
    for (const t of trades) {
        const key = `${t.symbol}_${t.direction}`;
        if (!ccyDirMap[key]) ccyDirMap[key] = [];
        ccyDirMap[key].push(t);
    }
    const results = {};
    for (const [ccyDirKey, ccyTrades] of Object.entries(ccyDirMap)) {
        const lotsInGroup = [...new Set(ccyTrades.map(t => t.lots))].sort((a, b) => a - b);
        const lotToIdx = {};
        lotsInGroup.forEach((lot, idx) => lotToIdx[lot] = idx + 1);
        const maxDepth = lotsInGroup.length;
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
            const totalPips = lt.reduce((s, t) => s + t.net_pips, 0);
            const avgWinPips = winCount > 0 ? wins.reduce((s, t) => s + t.net_pips, 0) / winCount : 0;
            const avgLossPips = lossCount > 0 ? Math.abs(losses.reduce((s, t) => s + t.net_pips, 0) / lossCount) : 0;
            const oddsPips = avgLossPips > 0 ? avgWinPips / avgLossPips : 999;
            const avgHold = lt.reduce((s, t) => s + t.holding_hours, 0) / n;
            const mfeVals = lt.map(t => t.mfe);
            const maeVals = lt.map(t => t.mae);
            const avgMfe = mfeVals.reduce((s, v) => s + v, 0) / n;
            const maxMfe = Math.max(...mfeVals);
            const avgMae = maeVals.reduce((s, v) => s + v, 0) / n;
            const maxMae = Math.max(...maeVals);
            const sampleLots = lt[0].lots;
            const layerIdx = lotToIdx[sampleLots] || 1;
            const key = `${ccyDirKey}_${layerLabel}`;
            results[key] = {
                symbol: ccyDirKey.split('_')[0], direction: ccyDirKey.split('_')[1],
                layer_label: layerLabel, lots: sampleLots, layer_idx: layerIdx, max_depth: maxDepth,
                count: n, win_count: winCount, loss_count: lossCount,
                wr: r2(wr), total_pnl: r2(totalPnl), total_pips: r2(totalPips),
                avg_win_pips: r2(avgWinPips), avg_loss_pips: r2(avgLossPips),
                odds_pips: oddsPips < 100 ? r2(oddsPips) : 999,
                avg_hold: r2(avgHold),
                avg_mfe: r2(avgMfe), max_mfe: r2(maxMfe),
                avg_mae: r2(avgMae), max_mae: r2(maxMae),
                trades: lt, // keep full trades for expand
            };
        }
    }
    return results;
}

// ═══════════════════════════════════════════════════════
// Rating
// ═══════════════════════════════════════════════════════

function computeRating(s) {
    const sc = computeScore(s);
    if (sc >= 85) return 'S+'; if (sc >= 70) return 'S'; if (sc >= 55) return 'A';
    if (sc >= 40) return 'B'; if (sc >= 25) return 'C'; if (sc >= 15) return 'D'; return 'E';
}

function computeScore(s) {
    const wr = s.wr; const odds = Math.min(s.odds_pips, 999); const cnt = s.count; const hold = s.avg_hold;
    let score = 0;
    score += wr >= 80 ? 30 : wr >= 70 ? 25 : wr >= 60 ? 18 : wr >= 50 ? 10 : Math.max(0, wr / 5);
    score += odds >= 2.0 ? 20 : odds >= 1.5 ? 15 : odds >= 1.0 ? 10 : Math.max(0, odds * 10);
    score += cnt >= 10 ? 15 : cnt >= 5 ? 12 : cnt >= 3 ? 8 : Math.max(0, cnt * 2);
    score += hold <= 24 ? 5 : hold <= 72 ? 4 : hold <= 168 ? 3 : hold <= 360 ? 2 : 1;
    return Math.round(score * 10) / 10;
}

// ═══════════════════════════════════════════════════════
// Summary / TP/SL / Blacklist / Recovery / CCY Summary
// ═══════════════════════════════════════════════════════

function computeSummary(trades) {
    const n = trades.length;
    if (n === 0) return { count: 0, win_pct: 0, total_pnl: 0, total_pips: 0, symbols: 0, layers: 0, best_ccy: '', best_pnl: 0 };
    const wins = trades.filter(t => t.net_profit > 0).length;
    const totalPnl = trades.reduce((s, t) => s + t.net_profit, 0);
    const totalPips = trades.reduce((s, t) => s + t.net_pips, 0);
    const symbols = new Set(trades.map(t => t.symbol)).size;
    const lots = new Set(trades.map(t => t.lots)).size;
    const ccyPnl = {};
    for (const t of trades) ccyPnl[t.symbol] = (ccyPnl[t.symbol] || 0) + t.net_profit;
    let bestCcy = '', bestPnl = -Infinity;
    for (const [c, p] of Object.entries(ccyPnl)) { if (p > bestPnl) { bestPnl = p; bestCcy = c; } }
    return { count: n, win_pct: r2(wins / n * 100), total_pnl: r2(totalPnl), total_pips: r2(totalPips), symbols, layers: lots, best_ccy: bestCcy, best_pnl: r2(bestPnl) };
}

function computeBlacklist(layerStats) {
    const bl = [];
    for (const [key, s] of Object.entries(layerStats)) {
        const r = computeRating(s);
        if (['D', 'E'].includes(r) && s.count >= 2) {
            const danger = (100 - computeScore(s)) + Math.abs(s.total_pnl > 0 ? 0 : Math.abs(s.total_pnl) / 10);
            bl.push({ key, symbol: s.symbol, direction: s.direction, layer: s.layer_label, lots: s.lots, rating: r, score: computeScore(s), danger_score: r2(danger), wr: s.wr, count: s.count, total_pnl: s.total_pnl, reason: getDangerReason(s) });
        }
    }
    return bl.sort((a, b) => b.danger_score - a.danger_score);
}

function getDangerReason(s) {
    const reasons = [];
    if (s.wr < 40) reasons.push('WR<40%');
    if (s.total_pnl < -50) reasons.push('P&L<-$50');
    if (s.odds_pips < 0.5) reasons.push('RR<0.5');
    if (s.avg_hold > 360) reasons.push('Hold>15d');
    return reasons.join(', ') || 'Underperforming';
}

function buildCCYDirectionSummary(layerStats) {
    const map = {};
    for (const [key, s] of Object.entries(layerStats)) {
        const cd = `${s.symbol}_${s.direction}`;
        if (!map[cd]) map[cd] = [];
        map[cd].push(s);
    }
    const summary = [];
    for (const [cd, layers] of Object.entries(map)) {
        const totalPnl = layers.reduce((s, l) => s + l.total_pnl, 0);
        const totalPips = layers.reduce((s, l) => s + (l.total_pips||0), 0);
        const totalCount = layers.reduce((s, l) => s + l.count, 0);
        const totalWins = layers.reduce((s, l) => s + l.win_count, 0);
        const avgWr = totalCount > 0 ? totalWins / totalCount * 100 : 0;
        const ratings = layers.map(l => computeRating(l));
        const best = ratings.includes('S+') ? 'S+' : ratings.includes('S') ? 'S' : ratings.includes('A') ? 'A' : ratings.includes('B') ? 'B' : 'C';
        summary.push({ symbol: layers[0].symbol, direction: layers[0].direction, layers: layers.length, total_pnl: r2(totalPnl), total_pips: r2(totalPips), total_count: totalCount, avg_wr: r2(avgWr), best_rating: best });
    }
    return summary.sort((a, b) => b.total_pnl - a.total_pnl);
}

// ═══════════════════════════════════════════════════════
// Helpers
// ═══════════════════════════════════════════════════════
function r2(v) { return Math.round(v * 100) / 100; }
function fmtPnl(v) { return v >= 0 ? `+${v.toLocaleString('en', {minimumFractionDigits: 1, maximumFractionDigits: 1})}` : v.toLocaleString('en', {minimumFractionDigits: 1, maximumFractionDigits: 1}); }
function ratingClass(r) { return ({ 'S+': 'r-sp', 'S': 'r-s', 'A': 'r-a', 'B': 'r-b', 'C': 'r-c', 'D': 'r-d', 'E': 'r-e' })[r] || 'r-e'; }
function fmtDate(d) { if (!d) return '—'; return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
function fmtTime(h) {
    if (h < 1) return `${r2(h*60)}m`;
    if (h < 24) return `${r2(h)}h`;
    if (h < 168) return `${r2(h/24)}d`;
    return `${r2(h/168)}w`;
}

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { parseCSV, filterByDateRange, computeLayerStats, computeRating, computeScore, computeSummary, computeBlacklist, buildCCYDirectionSummary };
}
