# 報告節結構規範（REPORT SECTION SPEC，卡 #28 第三份）

- 日期：2026-11-19
- 效力範圍：`docs/reports/` 全族（新頁強制；存量頁按 TEMPLATE_UNIFICATION 遷移表補齊）
- 對應：`TSA_ARCHITECTURE_AUDIT.md` §3 模板清單＋`REPORT_TEMPLATE_UNIFICATION.md` §4 遷移路線

## 0. 現況數字 → 目標數字

| # | 指標 | 現況 | 目標 | 重跑命令 |
|---|---|---|---|---|
| 1 | index_ 具 sec-* 錨點頁 | 147/159 | 159/159 | `c=0; n=0; for f in docs/reports/index_*.html; do n=$((n+1)); grep -q 'id="sec-raw"' "$f" && c=$((c+1)); done; echo "$c/$n"` |
| 2 | index_ 具 #sec-raw 頁 | 147/159 | 159/159 | 同上 |
| 3 | martin_v4 具 sec-* id 頁 | 0/169 | 169/169（生成器側落地） | `grep -l 'id="sec-' docs/reports/martin_v*.html \| wc -l` |
| 4 | 錨點 id 衝突（同頁重複 id） | 0 | 0 | `for f in docs/reports/index_10344.html; do grep -o 'id="sec-[a-z-]*"' $f \| sort \| uniq -d \| wc -l; done` |

## 1. 錨點命名規則（硬規矩）

1. 格式：`sec-<slug>`，slug 用 kebab-case 小寫英數（`sec-raw`、`sec-equity`、`sec-mae-mfe`）；**唔准**中文／空格／底線／駝峰。
2. 掛點：每節標題 `<h2 id="sec-<slug>">`；摺疊卡形態則掛 `<details class="card" id="sec-<slug>">`（index_ 現行實測形態）。
3. 唯一性：同一頁每個 `sec-*` id 只可出現一次（驗收命令 §0 第 4 行）。
4. **`#sec-raw` 係保留錨點**：一律指向「🗃️ 原始數據」節（倉位明細／raw evidence 表）——老闆示範 URL `index_10344.html#sec-raw` 即此節；任何報告族有 raw 數據表必須提供 `#sec-raw`，冇 raw 數據嘅頁唔准虚掛。
5. 摺疊卡內小節用 `<h3>`（無需 id）；如需直達可加 `sec-<slug>-<subslug>`，例 `sec-raw-positions`。

## 2. 每類報告必須有嘅節（固定 id）

### 2.1 範本 A「分析報告版」——`index_*.html`（現行 159 頁基準）

| 順序 | 固定 id | 節名（現行實測） | 必載 |
|---|---|---|---|
| 1 | `sec-equity` | 📈 收益曲線 | 權益曲線圖＋盈/虧倉位圖例 |
| 2 | `sec-score` | 🎯 質量評分 | v5 評分明細 |
| 3 | `sec-layers` | 📚 層數分析（含馬丁風險） | 層數分佈＋風險標記 |
| 4 | `sec-symbol` | 💱 貨幣對×方向 | 分貨幣對統計 |
| 5 | `sec-time` | 🕐 時間行為（時段・持倉・波幅） | 時段／持倉時長 |
| 6 | `sec-advanced` | 🔧 進階參考 | TP/SL、Max Profit 分佈等（6 小節） |
| 7 | `sec-raw` | 🗃️ 原始數據 | 倉位明細全表（3 小節） |

- 驗收：7 個 id 齊全＋§0 命令全過。缺任一＝不合規。

### 2.2 範本 B「馬丁深挖版」——`martin_v4_*.html`（現行 ①-⑥ 文字節固化為 id）

| 順序 | 固定 id（新增） | 現行節名（①-⑥） | 必載 |
|---|---|---|---|
| 1 | `sec-overview` | ① 整倉總覽 | 全倉統計 |
| 2 | `sec-detect` | ② 馬丁偵測 | 偵測結論 |
| 3 | `sec-pair` | ③ 商品分析器 | 逐商品分析 |
| 4 | `sec-table` | ④ 商品方向總表 | 方向總表 |
| 5 | `sec-monthly` | ⑤ 月度樞紐 | 月度樞紐表 |
| 6 | `sec-raw` | ⑥ MAE/MFE 散點→**改編**：①-⑥ 保留，`sec-raw` 另掛倉位明細節 | MAE/MFE 散點＋raw 表 |

- 落地點：本機側生成鏈（另開卡）；存量 169 頁唔回改（成本陷阱 32MB 級）。
- 驗收（新頁）：`grep -o 'id="sec-[a-z-]*"' <新頁> | sort -u | wc -l` ≥ 6。

### 2.3 覆盤報告——`date_range_review.py` 產物（daily/weekly/monthly）

| 順序 | 固定 id（新增） | 節名 |
|---|---|---|
| 1 | `sec-summary` | 期間統計（Trades／Win Rate／PnL） |
| 2 | `sec-detail` | 明細節（逐日／逐信號） |
| 3 | `sec-raw`（有 raw 表時） | 原始明細 |

- 落地點：`scripts/date_range_review.py` 生成器（repo 側，改動需老闆批——本卡零 code 改動，此為 spec 預告）。

### 2.4 存檔族（signal_／SDA 舊 24／anomaly）

- 唔套用本 spec（零改動）；索引層標 `archived` 即可（見 TEMPLATE_UNIFICATION P4）。

### 2.5 C 族「每日外匯報告」——`docs/forex_reports/*.html`（#39 W1–W2；2026-11-25 W1 試行補節，1258 §四.2）

| 固定 id | 節名（兩代實測映射） | 必載 |
|---|---|---|
| `sec-summary` | 舊代「市場總結」／新代「技術指標全景」 | 市場概括或指標全景 |
| `sec-news` | 舊代「SCOUT 資訊快遞」／新代「新聞摘要」 | 新聞節 |
| `sec-pair`（逐對卡加 `sec-pair-<slug>` 子錨，例 `sec-pair-audcad`） | 逐貨幣對分析（新代有 `group-<CCY>` 錨點並存，唔改佢） | 逐對分析 |
| `sec-week` | 舊代「下週重點關注」／新代併入結論節（無則免掛，唔准虛掛） | 前瞻節 |
| `sec-opps` | 舊代「潛在交易機會」／新代併入結論節（無則免掛，唔准虛掛） | 機會清單 |
| `sec-raw`（有 raw 表時） | 原始數據表 | 照 §1.4 保留錨點規則 |

- 形態：摺疊卡 `<details class="card" id="sec-<slug>" open>`（W1 頁 1 實測形態）；token link 已由 W3/REG-187 批次注入殼頁（inert），統一轉換後同頁生效。
- 兩代結構：舊代（2026-05 批次）h2 節＋`*-card` div；新代（2026-06 起）h3 節＋`.news-section`/`.events-section`/`.pairs-section` div＋`group-<CCY>` 錨點。轉換僅動結構層（wrapper 行），正文 byte 級零變。
- 驗收（照 §3）：逐頁 diff 正文零變＋headless console 零 error＋tsa_qa_check PASS＋錨點 id 無重複。

## 3. 合規驗收包（任何報告頁交付前必跑）

```
# 1) 錨點齊全（範本 A 例：7 id）
grep -o 'id="sec-[a-z-]*"' <頁> | sort -u
# 2) 無重複 id
grep -o 'id="sec-[a-z-]*"' <頁> | sort | uniq -d | wc -l   # → 0
# 3) token 引用
grep -c 'tsa_tokens.css' <頁>                              # 範本 A/B ≥1
# 4) 全站閘
python scripts/tsa_qa_check.py                             # PASS
python tests/language_check.py                             # 0 violations
```
