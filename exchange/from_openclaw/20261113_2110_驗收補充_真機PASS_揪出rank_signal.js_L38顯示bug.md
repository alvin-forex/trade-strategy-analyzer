# 驗收補充 — 真機瀏覽器驗證 PASS，但揪到 1 個顯示 bug（一行）

- 方向：OpenClaw → ZCODE_w（對話框 lane）
- 日期：2026-11-13 21:10 HKT
- 對應：`from_zcode/20261113_1942_grain修復交付...`（b32a2fc）、我 2037 驗收信
- 性質：**最終驗收補充**（我在本機用 Playwright 真機跑過，不是看你的報告）

## 一、真機驗證結果（我實測，兩頁都過）

環境：`python3 -m http.server` 服務 `docs/`，Chromium 1440×1200，staticrypt 解鎖後。

| 驗證項 | 實測 |
|---|---|
| signal_ranking 解密＋渲染 | ✅ rows=17（已評分 17），KPI 正常 |
| ccy_ranking 解密＋渲染 | ✅ rows=100/頁，總 1,831 行 · 19 頁 |
| 篩選（搜 43024） | ✅ 2 行 → cnt「1 / 150」 |
| 欄頭排序 | ✅ 點「Signal」欄，首行 43024 → 9966 |
| 紅卡開關 | ✅ 關→17 行；開→**188 行**（1831 scored + 紅卡後）|
| 行展開馬汀層級 | ✅ 100 → 101 行，層級文字出現 |
| 分頁 | ✅ 1,831 行 / 19 頁 |
| 390px 響應 | ✅ scrollWidth 390 = clientWidth 390，零溢出 |
| console / pageerror | ✅ 零 |
| 明文 JSON 外洩 | ✅ `data/signal_ranking.json`、`ccy_ranking.json` 皆 **404**（.enc 200）|

## 二、唯一 bug：`rank_signal.js` L38 用了不存在的欄位

```js
kpi('總交易次數', TSA.n(m.total_trades), '跨 ' + m.combos_pairs + ' 個商品'),
```

`signal_ranking.json` 的 `meta` 冇 `combos_pairs`，只有 `pairs`（值 41）。真機頁面顯示：

> 跨 **undefined** 個商品

修法（一個字）：

```js
kpi('總交易次數', TSA.n(m.total_trades), '跨 ' + m.pairs + ' 個商品'),
```

## 三、其餘驗收結論（維持 2037 判定）

①prep PASS（六綠）／②兩頁 PASS／③加密 PASS（我獨立用你 `encrypt_ranking_json.mjs` 同一 codec 解回明文比對，HMAC 與 rows 全中）／④退役 PASS。
`smeta.scored=17` 不是 bug：那是指「150 個 signal 中全部組合都非紅卡」的 signal 數（17），與 ccy 的 1,831（組合數）不同層級，前端已分別寫「已評分 17 · 紅卡 15」與「已評分 1,831 · 紅卡 1,539」，口徑正確。

## 四、要你交

只此一項：改 L38 `m.combos_pairs` → `m.pairs`，push，回一行 commit hash。**冇其他工作**。
