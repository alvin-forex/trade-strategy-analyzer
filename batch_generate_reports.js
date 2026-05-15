/**
 * Batch Generate Index Reports using Playwright
 * 
 * Usage:
 *   npx playwright install chromium  (first time only)
 *   node batch_generate_reports.js
 * 
 * Prerequisites:
 *   - Node.js 18+
 *   - npm install playwright
 *   - Local server running: cd docs && python3 -m http.server 8765
 */

const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

const DOCS_DIR = path.join(__dirname, 'docs');
const DOWNLOADS_DIR = path.join(__dirname, 'downloads');
const REPORTS_DIR = path.join(DOCS_DIR, 'reports');
const SERVER_URL = 'http://localhost:8765';

// Ensure reports directory exists
if (!fs.existsSync(REPORTS_DIR)) fs.mkdirSync(REPORTS_DIR, { recursive: true });

// Get all CSV signal IDs
const csvFiles = fs.readdirSync(DOWNLOADS_DIR).filter(f => f.match(/^forex-forest-signals-page-(\d+)\.csv$/));
const csvIds = csvFiles.map(f => f.match(/page-(\d+)\.csv$/)[1]).sort((a, b) => parseInt(a) - parseInt(b));

// Filter out existing reports
const needed = csvIds.filter(id => !fs.existsSync(path.join(REPORTS_DIR, `index_${id}.html`)));

console.log(`Total CSVs: ${csvIds.length} | Already generated: ${csvIds.length - needed.length} | To generate: ${needed.length}`);

if (needed.length === 0) {
  console.log('✅ All reports up to date!');
  process.exit(0);
}

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  let success = 0, fail = 0;

  for (let i = 0; i < needed.length; i++) {
    const sid = needed[i];
    const csvFile = `forex-forest-signals-page-${sid}.csv`;
    const outFile = path.join(REPORTS_DIR, `index_${sid}.html`);

    try {
      console.log(`[${i + 1}/${needed.length}] Signal #${sid} ...`);

      // Navigate to index.html
      await page.goto(SERVER_URL + '/index.html', { waitUntil: 'networkidle' });

      // Inject CSV via fetch
      const result = await page.evaluate(async (csvName) => {
        const input = document.getElementById('csvInput');
        input.value = '';
        input.files = new DataTransfer().files;

        const resp = await fetch('/downloads/' + csvName);
        if (!resp.ok) return { error: 'fetch failed', status: resp.status };
        const blob = await resp.blob();
        const file = new File([blob], csvName, { type: 'text/csv' });
        const dt = new DataTransfer();
        dt.items.add(file);
        input.files = dt.files;
        input.dispatchEvent(new Event('change', { bubbles: true }));
        return { ok: true, size: blob.size };
      }, csvFile);

      if (result.error) {
        console.log(`  ❌ CSV inject failed: ${result.error}`);
        fail++;
        continue;
      }

      // Click analyze button
      await page.click('#analyzeBtn');

      // Wait for results to appear
      await page.waitForSelector('#results', { timeout: 15000 });
      await page.waitForTimeout(3000); // Extra time for full render

      // Generate and save report
      const html = await page.evaluate(() => {
        if (typeof downloadReport === 'function') downloadReport();
        return window._reportHTML;
      });

      if (!html) {
        console.log(`  ❌ Report generation failed (no HTML)`);
        fail++;
        continue;
      }

      fs.writeFileSync(outFile, html);
      const sizeKB = (Buffer.byteLength(html) / 1024).toFixed(1);
      console.log(`  ✅ ${sizeKB} KB`);
      success++;

    } catch (err) {
      console.log(`  ❌ Error: ${err.message}`);
      fail++;
    }
  }

  await browser.close();
  console.log(`\n========================================`);
  console.log(`Batch Complete: ${success} ✅ | ${fail} ❌ | Total: ${needed.length}`);
  console.log(`========================================`);
})();
