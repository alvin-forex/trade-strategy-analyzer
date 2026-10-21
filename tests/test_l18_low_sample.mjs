#!/usr/bin/env node
/**
 * [L18] 低樣本暫緩定級 — 邊界 golden 測試(白皮書 v1.3 §3.3 裁決,v1.4 留後 Step 2,2026-10-22 實施)
 *
 * 範圍:index.html calcStrategyScore(主分析頁倉位評分,唔係 martin_v4_engine.js)
 *   ① np=0 除零 guard — 核實結論(2026-10-22):guard 已存在,np=0 → ddRatio=1.0(白皮書 v1.1「待核實」→ 已核實)
 *   ② |淨利| < $30 → low_sample=true:exitEff(np/maxP)與 ddRatio(maxL/|np|)對微小金額變化極度敏感,
 *      評級唔穩定 → 標記暫緩,唔參與評級聚合(renderScoreSection/history payload 三處 gradeDist 剔除)
 *   四邊界 np=0/1/29/30(白皮書裁定)+ 對稱負值 -29/-30 + 大額對照組
 *
 * 口徑依據:11,616 層 baseline 統計 count<30 佔 89.2%(median=4)——「樣本筆數」口徑會令九成層
 * 失去評級,唔可能係裁決意圖;L18 原始缺陷語境(ddRatio 分母 |np|)指向 net_profit 金額口徑。
 * 口徑再改動必須走受控流程(七步)+ 同步修訂本測試 + 白皮書入冊。
 *
 * 執行:node --test tests/test_l18_low_sample.mjs
 * 紅燈 = 禁止 merge main(.github/workflows/regression.yml golden job 門禁)
 */

import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(__dirname, '..');
const html = readFileSync(path.join(ROOT, 'index.html'), 'utf-8');

// ── 由 index.html 抽取內嵌函數(測嘅就係上線代碼,byte 級同源)──
function extractFn(name) {
    const marker = `function ${name}(`;
    const start = html.indexOf(marker);
    assert.notEqual(start, -1, `index.html 搵唔到 ${marker}`);
    let i = html.indexOf('{', start), depth = 0, end = -1;
    for (; i < html.length; i++) {
        if (html[i] === '{') depth++;
        else if (html[i] === '}') { depth--; if (depth === 0) { end = i + 1; break; } }
    }
    assert.notEqual(end, -1, `function ${name} brace 解析失敗`);
    return html.slice(start, end);
}

// 抽出後評估;calcStrategyScore 內部引用 gradeOf,以參數注入保持同源
const gradeOfSrc = extractFn('gradeOf');
const gradeOf = new Function(`return (${gradeOfSrc});`)();
const calcStrategyScore = new Function('gradeOf', `return (${extractFn('calcStrategyScore')});`)(gradeOf);

// 標準測試倉位:max_profit=100/max_loss=-150/3 層,只變 net_profit
function mkPos(np) {
    return {
        net_profit: np, max_profit: 100, max_loss: -150, max_layer: 3,
        holding_time_hours: 12, total_commission: -5, total_swap: -2,
        l1_max_pips: 30, l1_max_loss_pips: -10, symbol: 'TEST', direction: 'BUY'
    };
}

test('[L18] np=0 除零 guard:唔拋錯 + risk 有界(ddRatio=1.0 分支生效)', () => {
    const r = calcStrategyScore(mkPos(0));
    assert.ok(r.score >= 0 && r.score <= 100, `score 應有界,實得 ${r.score}`);
    assert.ok(r.risk >= 0 && r.risk <= 1, `risk 應有界,實得 ${r.risk}`);
    assert.equal(r.low_sample, true, 'np=0 屬低樣本(暫緩定級)');
});

test('[L18] 白皮書四邊界 np=0/1/29/30:|np|<30 暫緩,np=30 正常', () => {
    assert.equal(calcStrategyScore(mkPos(0)).low_sample, true);
    assert.equal(calcStrategyScore(mkPos(1)).low_sample, true);
    assert.equal(calcStrategyScore(mkPos(29)).low_sample, true);
    assert.equal(calcStrategyScore(mkPos(30)).low_sample, false);
});

test('[L18] 對稱負值:-29 暫緩 / -30 正常(ddRatio 分母同用 |np|,口徑對稱)', () => {
    assert.equal(calcStrategyScore(mkPos(-29)).low_sample, true);
    assert.equal(calcStrategyScore(mkPos(-30)).low_sample, false);
});

test('[L18] 對照組:大額倉位正常定級,grade 停留封閉集 A/B/C/D', () => {
    const r = calcStrategyScore(mkPos(300));
    assert.equal(r.low_sample, false);
    assert.ok(['A', 'B', 'C', 'D'].includes(r.grade), `grade 實得 ${r.grade}`);
});

test('[L18] 透明度:low_sample 唔改變 score/grade 計算(照計,只係聚合剔除)', () => {
    const r29 = calcStrategyScore(mkPos(29));
    const r30 = calcStrategyScore(mkPos(30));
    assert.ok(typeof r29.score === 'number' && isFinite(r29.score));
    assert.ok(['A', 'B', 'C', 'D'].includes(r29.grade), 'grade 照計,唔會變壞字串');
    assert.ok(typeof r30.score === 'number' && isFinite(r30.score));
});

test('[L18] 靈敏度論證鎖定:np 愈細 ddRatio 愈易觸底(缺陷根因唔會被靜默改走)', () => {
    // 同一 max_loss=-150:np=29 時 maxL/|np|/5 > 1 → ddRatio clamp 0;
    // np=300 時 = 1-(150/300)/5 = 0.9 —— 兩者差異正係 np<30 要暫緩嘅原因
    const r29 = calcStrategyScore(mkPos(29));
    const r300 = calcStrategyScore(mkPos(300));
    assert.ok(r29.risk < r300.risk, `細額倉 risk(${r29.risk}) 應顯著低於大額倉(${r300.risk})`);
});
