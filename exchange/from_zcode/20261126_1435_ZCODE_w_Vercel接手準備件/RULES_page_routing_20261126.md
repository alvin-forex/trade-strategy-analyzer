# TSA 發佈分流清單 rules（0412 流水線定案 §2「清單寫死喺 rules 檔」）

日期: 2026-11-26
維護: ZCODE_w（template lane，OC 驗）
性質: 分流 rules v1——雙通道（GitHub Pages 公開網／Vercel 私有站）

## 一、私有站（Vercel，密碼保護必須）——含倉位／帳號／訊號明細

| 路徑 | 內容 | 註 |
|------|------|-----|
| `docs/reports/**` | 全量信號報告（497MB，481 index＋martin_v4 等） | 核心主體 |
| `docs/admin/**` | 管理頁（tasks_board 加密頁等） | 加密頁一併私站 |
| `docs/data/**` | signal JSON.enc／ranking.enc 加密數據 | 頁面 fetch 依賴 |
| `docs/ccy/**`、`docs/ccy_power/**`、`docs/ccy_ranking.html` | CCY 分析鏈 | 詳情頁含明文數據 |
| `docs/portfolios/**` | 組合頁 | 倉位明細 |
| `docs/analyzer.html`、`docs/bot2bot-check.html` | 分析工具頁 | |
| `docs/detailed_comparison_*.html`、`docs/index_*.html`（根層） | 信號詳比／深析頁 | |
| `docs/campaign/**`、`docs/js/**`、`docs/common.js`、`docs/sidebar.*` | 站務資產 | 兩邊共用，私站副本一併 |
| `docs/*.md`、`docs/_render_*.py` | 運營文檔 | 內部用 |

## 二、公開網（GitHub Pages）——非核心／已脫敏

| 路徑 | 內容 |
|------|------|
| `docs/index.html`（首頁殼） | 公開入口（fetch 加密數據，無明文） |
| `docs/forex_reports/**` | 早晚報（已過私隱審，倉位唔入） |
| `docs/reviews/**` | 每日／週覆盤 |
| `docs/home/**` | 首頁資產 |

## 三、唔上網（兩邊都唔發）

| 路徑 | 原因 |
|------|------|
| `docs/downloads/**`（201 CSV，63MB） | AlgoForest 真實交易原始數據，頁面唔直接引用，數據治理面唔上網 |
| `docs/BACKUP_RUNBOOK.md` 等 VPS 運維文檔 | 基建敏感 |

## 四、防漏三條（照 0412）

1. 任何新報告類型出廠前，必須加落本清單先算驗收（新類型默認＝私有，除非明確脫敏）
2. 分流以**目錄前綴**為準（唔逐檔判斷）；例外單頁喺 §二列名
3. 本清單改動＝rules 改動，要 OC 驗＋板面登記

## 五、Vercel 部署範圍（照 §一＋§三）

- 部署 root＝`docs/`（排除 `downloads/`；Vercel `excludeFiles` 或部署前 `rsync` 白名單複製，見 RUNBOOK）
- 全站 `X-Robots-Tag: noindex`（vercel.json 已配）＋Deployment Protection（RUNBOOK 步驟 3）
