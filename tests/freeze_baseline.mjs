#!/usr/bin/env node
/**
 * Step 0 — Baseline 凍結腳本(白皮書 v1.3 §8.2 Task B)
 *
 * 規則(白皮書裁定):
 *  - baseline 凍結必須先於一切引擎公式改動(L15 修復、danger 重構)
 *  - 快照 metadata 必須含 git_commit / engine_sha256 / frozen_at / thresholds
 *  - 現行門檻為百分制殘留(L15),此快照標記 pre-fix,Task D 修復後以
 *    受控流程(freeze --update + 人工審 diff 摘要)產生 post-fix baseline
 *
 * 用法:
 *   node tests/freeze_baseline.mjs                 # 用已凍結 inputs 重跑
 *   node tests/freeze_baseline.mjs --ids ids.txt   # 首次凍結(ID 清單,每行一個)
 *
 * 輸出:
 *   tests/inputs/signals_input.json           # 信號清單 + CSV 檔名 + sha256(凍結輸入)
 *   tests/baseline/baseline.json              # 金標準快照(每信號每層 score/rating/danger)
 *   tests/baseline/rating_distribution.json   # 評級分佈報告
 */

import { createRequire } from 'module';
import { createHash } from 'crypto';
import { readFileSync, writeFileSync, existsSync, mkdirSync } from 'fs';
import { execSync } from 'child_process';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');

const require = createRequire(import.meta.url);
const eng = require(path.join(ROOT, 'martin_v4_engine.js'));

const INPUTS_DIR = path.join(ROOT, 'tests', 'inputs');
const BASELINE_DIR = path.join(ROOT, 'tests', 'baseline');
const INPUTS_JSON = path.join(INPUTS_DIR, 'signals_input.json');
const BASELINE_JSON = path.join(BASELINE_DIR, 'baseline.json');
const DIST_JSON = path.join(BASELINE_DIR, 'rating_distribution.json');

// 現行(未修復)門檻 — 與 martin_v4_engine.js computeRating 一致,凍結時點標記
const CURRENT_THRESHOLDS = { 'S+': 85, S: 70, A: 55, B: 40, C: 25, D: 15, E: 0 };
const THRESHOLDS_STATE = 'pre-L15-fix (85/70/55/40/25/15, score cap 70 — known defect L15)';

function sha256(buf) { return createHash('sha256').update(buf).digest('hex'); }

function gitCommit() {
    try { return execSync('git rev-parse HEAD', { cwd: ROOT }).toString().trim(); }
    catch { return 'unknown'; }
}

function csvPathFor(id) {
    return path.join(ROOT, 'downloads', `forex-forest-signals-page-${id}.csv`);
}

function r2(v) { return Math.round(v * 100) / 100; }

// ── 現行 danger 公式快照(與引擎 computeBlacklist 一致,含 (100-score) 缺陷) ──
function dangerCurrent(s) {
    const score = eng.computeScore(s);
    const lossPart = s.total_pnl > 0 ? 0 : Math.abs(s.total_pnl) / 10;
    return r2((100 - score) + lossPart);
}

function snapshotSignal(id) {
    const csvPath = csvPathFor(id);
    const relCsv = `downloads/forex-forest-signals-page-${id}.csv`;
    if (!existsSync(csvPath)) {
        return { id, csv: relCsv, status: 'no_csv' };
    }
    const buf = readFileSync(csvPath);
    const text = buf.toString('utf-8');
    const trades = eng.parseCSV(text);
    const layerStats = eng.computeLayerStats(trades);
    const summary = eng.computeSummary(trades);

    const layers = {};
    for (const [key, s] of Object.entries(layerStats)) {
        layers[key] = {
            count: s.count,
            wr: s.wr,
            total_pnl: s.total_pnl,
            total_pips: s.total_pips,
            odds_pips: s.odds_pips,
            avg_hold: s.avg_hold,
            score: eng.computeScore(s),
            rating: eng.computeRating(s),
            danger_current: dangerCurrent(s),
        };
    }
    // 與引擎同序:danger 降序(用現行公式)
    const blacklist = eng.computeBlacklist(layerStats).map(b => ({
        key: b.key, rating: b.rating, score: b.score, danger_score: b.danger_score,
        count: b.count, total_pnl: b.total_pnl, reason: b.reason,
    }));
    const ccySummary = eng.buildCCYDirectionSummary(layerStats);

    return {
        id, csv: relCsv, csv_sha256: sha256(buf), status: 'frozen',
        trade_count: trades.length,
        summary,
        layer_count: Object.keys(layers).length,
        layers,
        blacklist,
        ccy_summary: ccySummary,
    };
}

// ESM export — golden.test.mjs 必須與本腳本共用同一 snapshotSignal(單一事實源)
export { snapshotSignal, dangerCurrent, CURRENT_THRESHOLDS, THRESHOLDS_STATE };

function main() {
    mkdirSync(INPUTS_DIR, { recursive: true });
    mkdirSync(BASELINE_DIR, { recursive: true });

    // 1. 決定信號清單
    let ids;
    if (existsSync(INPUTS_JSON)) {
        const prev = JSON.parse(readFileSync(INPUTS_JSON, 'utf-8'));
        ids = prev.signals.map(s => s.id);
        console.log(`使用已凍結輸入清單: ${ids.length} 信號 (${INPUTS_JSON})`);
    } else {
        const idsArg = process.argv.indexOf('--ids');
        if (idsArg === -1 || !process.argv[idsArg + 1]) {
            console.error('首次凍結必須提供 --ids <id 清單檔>(每行一個信號 ID)');
            process.exit(1);
        }
        ids = readFileSync(process.argv[idsArg + 1], 'utf-8').split('\n').map(s => s.trim()).filter(Boolean);
        console.log(`首次凍結: ${ids.length} 信號`);
    }

    // 2. 凍結輸入清單(首次)或驗證(重跑)
    let inputs;
    if (existsSync(INPUTS_JSON)) {
        inputs = JSON.parse(readFileSync(INPUTS_JSON, 'utf-8'));
    } else {
        inputs = {
            frozen_at: new Date().toISOString(),
            git_commit: gitCommit(),
            source: 'signal_ranking_dde_v5.html 內嵌信號清單(martin_v4_*.html 連結提取)',
            signal_count: ids.length,
            signals: ids.map(id => {
                const p = csvPathFor(id);
                const rel = `downloads/forex-forest-signals-page-${id}.csv`;
                return existsSync(p)
                    ? { id, csv: rel, csv_sha256: sha256(readFileSync(p)) }
                    : { id, csv: rel, status: 'no_csv' };
            }),
        };
        writeFileSync(INPUTS_JSON, JSON.stringify(inputs, null, 2) + '\n');
        console.log(`已寫出 ${INPUTS_JSON}`);
    }

    // 3. 對每信號產生快照
    const results = {};
    const dist = {};
    let okCount = 0, skipCount = 0;
    for (const s of inputs.signals) {
        process.stdout.write(`  ${s.id} ... `);
        const snap = snapshotSignal(s.id);
        results[s.id] = snap;
        if (snap.status === 'no_csv') { console.log('SKIP (no csv)'); skipCount++; continue; }
        okCount++;
        for (const l of Object.values(snap.layers)) dist[l.rating] = (dist[l.rating] || 0) + 1;
        console.log(`OK (${snap.layer_count} layers, ${snap.trade_count} trades)`);
    }

    // 4. 寫 baseline
    const baseline = {
        frozen_at: new Date().toISOString(),
        git_commit: gitCommit(),
        engine_file: 'martin_v4_engine.js',
        engine_sha256: sha256(readFileSync(path.join(ROOT, 'martin_v4_engine.js'))),
        engine_version: 'Martin Autopsy V4.1 (as in source header)',
        thresholds: CURRENT_THRESHOLDS,
        thresholds_state: THRESHOLDS_STATE,
        input_ref: 'tests/inputs/signals_input.json',
        signals_frozen: okCount,
        signals_skipped_no_csv: skipCount,
        notes: [
            'Step 0 快照 — 凍結於任何 L15/danger 修復之前。',
            'danger_current 含已知 (100-score) 百分制殘留缺陷(L15 同源),按現行公式原樣凍結。',
            'Task D 修復後必須以受控流程更新本檔案,並人工審閱 diff 摘要(白皮書 v1.3 §8.2)。',
        ],
        signals: results,
    };
    writeFileSync(BASELINE_JSON, JSON.stringify(baseline, null, 2) + '\n');
    console.log(`已寫出 ${BASELINE_JSON}`);

    const distOut = {
        frozen_at: baseline.frozen_at,
        thresholds: CURRENT_THRESHOLDS,
        thresholds_state: THRESHOLDS_STATE,
        signals_frozen: okCount,
        total_layers: Object.values(dist).reduce((a, b) => a + b, 0),
        rating_distribution: Object.fromEntries(
            ['S+', 'S', 'A', 'B', 'C', 'D', 'E'].map(r => [r, dist[r] || 0])
        ),
    };
    writeFileSync(DIST_JSON, JSON.stringify(distOut, null, 2) + '\n');
    console.log(`已寫出 ${DIST_JSON}`);
    console.log(`\n凍結完成: ${okCount} 信號 / ${skipCount} 跳過 / ${distOut.total_layers} 層`);
}

// 僅作為 CLI 直接執行時才跑 main()
import { pathToFileURL } from 'url';
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
    main();
}
