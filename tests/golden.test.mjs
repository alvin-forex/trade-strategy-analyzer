#!/usr/bin/env node
/**
 * Task C — Golden 回歸測試 + 門檻一致性 + 性質測試(白皮書 v1.3 §8.2,L17 測試金字塔)
 *
 * 紅燈 = 禁止 merge main(.github/workflows/regression.yml 門禁)
 *
 * 覆蓋:
 *  [L1] 輸入完整性 — CSV sha256 對照 tests/inputs/signals_input.json(漂移 → 指引受控重凍)
 *  [L1] Golden diff — 當前引擎輸出 vs tests/baseline/baseline.json 全等
 *  [L1] 門檻一致性 — 每層 rating 與 baseline 門檻表對應區間一致
 *  [L2] 性質 — score ∈ [0,70]、評級封閉集合、評級單調、滿分構造、blacklist 降序
 *
 * 執行:node --test tests/golden.test.mjs
 *
 * ⚠️ snapshotSignal 由 tests/freeze_baseline.mjs 導出(單一事實源)。
 *    修改快照邏輯必須改 freeze_baseline.mjs,並以受控流程重凍 baseline。
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'fs';
import { createHash } from 'crypto';
import path from 'path';
import { fileURLToPath } from 'url';
import { createRequire } from 'module';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const require = createRequire(import.meta.url);

const eng = require(path.join(ROOT, 'martin_v4_engine.js'));
const { snapshotSignal } = await import(path.join(ROOT, 'tests', 'freeze_baseline.mjs'));

const baseline = JSON.parse(readFileSync(path.join(ROOT, 'tests', 'baseline', 'baseline.json'), 'utf-8'));
const inputs = JSON.parse(readFileSync(path.join(ROOT, 'tests', 'inputs', 'signals_input.json'), 'utf-8'));

const CLOSED_SET = ['S+', 'S', 'A', 'B', 'C', 'D', 'E'];
const SCORE_CAP = 70; // L15:設計上限 30+20+15+5

// 由門檻表推導評級(門檻驅動,Task D 更新 thresholds 後自動跟隨)
function ratingFromScore(score, th) {
    const rows = Object.entries(th)
        .map(([r, t]) => ({ r, t }))
        .sort((a, b) => b.t - a.t);
    for (const { r, t } of rows) if (score >= t) return r;
    return 'E';
}

// ─────────────────────────────────────────────────────────
// [L1] 輸入完整性 — CSV 漂移偵測
// ─────────────────────────────────────────────────────────
test('[L1] 輸入完整性:CSV sha256 與凍結清單一致', () => {
    const drifted = [];
    for (const sig of inputs.signals) {
        if (sig.status === 'no_csv') continue;
        const p = path.join(ROOT, sig.csv);
        if (!existsSync(p)) { drifted.push(`${sig.id}: CSV 檔案消失`); continue; }
        const h = createHash('sha256').update(readFileSync(p)).digest('hex');
        if (h !== sig.csv_sha256) drifted.push(`${sig.id}: sha256 不一致(輸入已漂移)`);
    }
    if (drifted.length) {
        console.error('\n=== 輸入漂移(非引擎缺陷,輸入數據被更新)===');
        for (const d of drifted.slice(0, 20)) console.error('  ' + d);
        console.error('  → 這不是引擎回歸。請走受控重凍:node tests/freeze_baseline.mjs');
        console.error('    + 人工審閱 diff 摘要 + 更新 inputs(白皮書 v1.3 §8.2 七步流程)');
    }
    assert.equal(drifted.length, 0, `輸入漂移 ${drifted.length} 個信號(需受控重凍,非代碼回歸)`);
});

// ─────────────────────────────────────────────────────────
// [L1] Golden diff — 91 信號全量逐欄比對
// ─────────────────────────────────────────────────────────
test('[L1] golden:當前引擎輸出與 baseline 完全一致', () => {
    const diffs = [];
    let checked = 0;

    for (const sig of inputs.signals) {
        if (sig.status === 'no_csv') continue;
        const base = baseline.signals[sig.id];
        assert.ok(base, `baseline 缺少信號 ${sig.id}`);

        const snap = snapshotSignal(sig.id);
        checked++;

        if (snap.trade_count !== base.trade_count) diffs.push(`${sig.id}: trade_count ${base.trade_count} → ${snap.trade_count}`);
        if (snap.layer_count !== base.layer_count) diffs.push(`${sig.id}: layer_count ${base.layer_count} → ${snap.layer_count}`);
        if (JSON.stringify(snap.summary) !== JSON.stringify(base.summary)) {
            diffs.push(`${sig.id}: summary ${JSON.stringify(base.summary)} → ${JSON.stringify(snap.summary)}`);
        }

        for (const [key, l] of Object.entries(snap.layers)) {
            const b = base.layers[key];
            if (!b) { diffs.push(`${sig.id}/${key}: baseline 無此層(新增)`); continue; }
            for (const f of ['count', 'wr', 'total_pnl', 'total_pips', 'odds_pips', 'avg_hold', 'score', 'rating', 'danger_current']) {
                if (String(b[f]) !== String(l[f])) diffs.push(`${sig.id}/${key}.${f}: ${b[f]} → ${l[f]}`);
            }
        }
        for (const key of Object.keys(base.layers)) {
            if (!snap.layers[key]) diffs.push(`${sig.id}/${key}: 層消失`);
        }

        const bBl = JSON.stringify(base.blacklist.map(x => [x.key, x.danger_score]));
        const nBl = JSON.stringify(snap.blacklist.map(x => [x.key, x.danger_score]));
        if (bBl !== nBl) diffs.push(`${sig.id}: blacklist 順序/內容變化`);

        if (JSON.stringify(base.ccy_summary) !== JSON.stringify(snap.ccy_summary)) {
            diffs.push(`${sig.id}: ccy_summary 變化`);
        }
    }

    if (diffs.length) {
        console.error(`\n=== GOLDEN DIFF 摘要:共 ${diffs.length} 條(前 40 條)===`);
        for (const d of diffs.slice(0, 40)) console.error('  ' + d);
        if (diffs.length > 40) console.error(`  ...另有 ${diffs.length - 40} 條`);
        console.error('  若屬預期公式改動:受控更新 baseline(七步流程)後綠燈。');
    }
    assert.equal(diffs.length, 0, `golden diff 共 ${diffs.length} 條(已凍結 ${checked} 信號)`);
});

// ─────────────────────────────────────────────────────────
// [L1] 門檻一致性 — baseline 每層 rating 對應門檻表區間
// ─────────────────────────────────────────────────────────
test('[L1] 門檻一致性:每層 score/rating 與 baseline 門檻表吻合', () => {
    const th = baseline.thresholds;
    const bad = [];
    for (const [id, sig] of Object.entries(baseline.signals)) {
        if (sig.status === 'no_csv') continue;
        for (const [key, l] of Object.entries(sig.layers)) {
            const expect = ratingFromScore(l.score, th);
            if (expect !== l.rating) bad.push(`${id}/${key}: score ${l.score} → 門檻表應為 ${expect},記錄 ${l.rating}`);
        }
    }
    if (bad.length) {
        console.error('\n=== 門檻不一致(門檻被改而 baseline 未受控更新)===');
        for (const b of bad.slice(0, 20)) console.error('  ' + b);
    }
    assert.equal(bad.length, 0, `${bad.length} 層與門檻表不一致`);
});

// ─────────────────────────────────────────────────────────
// [L2] 性質測試
// ─────────────────────────────────────────────────────────
test('[L2] 性質:score ∈ [0,70] 且評級屬封閉集合', () => {
    const bad = [];
    for (const [id, sig] of Object.entries(baseline.signals)) {
        if (sig.status === 'no_csv') continue;
        for (const [key, l] of Object.entries(sig.layers)) {
            if (typeof l.score !== 'number' || l.score < 0 || l.score > SCORE_CAP) {
                bad.push(`${id}/${key}: score ${l.score} 超界 [0,${SCORE_CAP}]`);
            }
            if (!CLOSED_SET.includes(l.rating)) bad.push(`${id}/${key}: 非法評級 ${l.rating}`);
        }
    }
    assert.equal(bad.length, 0, bad.slice(0, 10).join('; '));
});

test('[L2] 性質:評級單調(同門檻表下,分數越高評級不會更低)', () => {
    const th = baseline.thresholds;
    const rows = Object.entries(th).map(([r, t]) => ({ r, t: Number(t) })).sort((a, b) => b.t - a.t);
    for (let i = 0; i < rows.length; i++) {
        for (let j = 0; j < i; j++) {
            assert.ok(rows[j].t > rows[i].t, `門檻表必須嚴格遞減:${rows[j].r}(${rows[j].t}) vs ${rows[i].r}(${rows[i].t})`);
        }
    }
    // 實例單調:每層 rating == ratingFromScore(score)
    const bad = [];
    for (const [id, sig] of Object.entries(baseline.signals)) {
        if (sig.status === 'no_csv') continue;
        for (const [key, l] of Object.entries(sig.layers)) {
            if (ratingFromScore(l.score, th) !== l.rating) bad.push(`${id}/${key}`);
        }
    }
    assert.equal(bad.length, 0, `單調性違反 ${bad.length} 層`);
});

test('[L2] 性質:滿分構造 score == 70(設計上限鎖定,公式改動即刻紅)', () => {
    const best = {
        symbol: 'TEST', direction: 'buy', layer_label: 'L1', lots: 0.01,
        count: 10, win_count: 10, loss_count: 0,
        wr: 100, odds_pips: 999, avg_hold: 1, total_pnl: 100, total_pips: 100,
    };
    const score = eng.computeScore(best);
    assert.equal(score, SCORE_CAP, `最優層應得 ${SCORE_CAP}(若公式改動,此測試紅 → baseline 需受控重凍)`);
});

test('[L2] 性質:computeBlacklist 只含 D/E 且 danger 降序', () => {
    for (const [id, sig] of Object.entries(baseline.signals)) {
        if (sig.status === 'no_csv' || !sig.blacklist) continue;
        sig.blacklist.forEach((b, i) => {
            assert.ok(['D', 'E'].includes(b.rating), `${id}: blacklist 評級 ${b.rating} 不屬 D/E`);
            if (i > 0) {
                assert.ok(sig.blacklist[i - 1].danger_score >= b.danger_score,
                    `${id}: blacklist danger 非降序(idx ${i})`);
            }
        });
    }
});

test('[L2] 性質:L15 缺陷存在性標記(滿分不可達 S+,防「靜默修復」)', () => {
    // pre-fix 狀態:S+ 門檻 85 > 上限 70 → 構造最優層應為 S(70≥70)而非 S+
    // Task D 修復 + 受控重凍後,thresholds_state 變更,本測試自動失效(條件跳過)
    if (!baseline.thresholds_state.includes('pre-L15-fix')) {
        t_skip();
        return;
    }
    function t_skip() { /* node:test 內以 assert 訊息代替 skip */ }
    const best = {
        symbol: 'TEST', direction: 'buy', layer_label: 'L1', lots: 0.01,
        count: 10, win_count: 10, loss_count: 0,
        wr: 100, odds_pips: 999, avg_hold: 1, total_pnl: 100, total_pips: 100,
    };
    const r = eng.computeRating(best);
    assert.ok(r !== 'S+', `pre-fix 狀態下 S+ 不可達,現得 ${r} — 若非預期請核查門檻`);
    assert.equal(baseline.rating_distribution?.['S+'] ?? 0, 0, 'pre-fix baseline 中 S+ 數應為 0');
});
