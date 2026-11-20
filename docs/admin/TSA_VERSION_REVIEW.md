# TSA 各版改善建議

> 2026-11-20｜AUTOCLAW（AC lane）｜依據：站內實檔盤點（484 頁 reports／220 頁 forex_reports／37 頁 ccy／12 頁 portfolios／5 頁 ccy_power）＋ AC 馬丁頁審查（cd8a6d36）＋ #20／#28 現況
> 配套卡：#36 數據層、#37 parity、#38 martin 修正、#39 模板統一、#40 排程體檢

## 一、版系總覽與優先次序

| 版系 | 頁數 | 現況 | 最大問題 | 優先 |
|---|---|---|---|---|
| A. martin_v4 報告 | ~165 | 可生成、可睇 | **5 個數值邏輯錯**（#38） | P0 |
| B. martin_autopsy_v3 | ~20+ | 舊版 autopsy 頁 | 與 v4 並存、口徑未統一 | P2（建議退役或標「舊版」） |
| C. forex_reports | 220 | 大量舊報告 | 模板與 v4 不一致（#28） | P1 |
| D. ccy 詳情頁 | 37 | 正常 | 缺深度／未接新數據源 | P1 |
| E. ccy_power | 5 | 有 stale 閘（#18） | 數據停更時仍似「即時」 | P0（#18） |
| F. portfolios | 12 | 組合頁 | 缺與 CCY／風險嘅交叉引用 | P2 |
| G. campaign／reviews／admin | 21 | 局部 | 無統一導航 | P1（併入 #39） |
| H. 根目錄孤兒頁 | 3 | `ff54_report.html`／`ea_strategy_masterplan.html`／`index.html` | 未入導航、風格獨立 | P1 |

## 二、逐版建議

### A. martin_v4 報告（P0，卡 #38）
- **修 5 個錯**：base lot 用最常見；倍數 m0＝基準以上最常見 lot÷base（≥2 次且 ≥1%）；歸層 `ROUND(LN(lot/base)/LN(step))+1`＋容差；刪「理論 lot」；引用白皮書 v3.5。
- **補內容**：③ 商品分析器三塊（指標×方向／止賺止蝕／61 級曲線）、④「L5+ 筆數」、⑥ 散點說明句。
- **加可信度**：頁尾加「數據指紋」（CSV sha256 前 8 位＋生成器版本），任何頁都可追溯到同一份輸入。
- **驗收**：Excel v8.5 golden fixture 對數；165 頁重生成。

### B. martin_autopsy_v3（P2）
- 與 v4 功能重疊，建議：①頂部加「舊版」橫幅並連去 v4；②或整批下架，保留 3 頁做歷史對照。
- 理由：兩套 autopsy 同時存在會令客戶混淆邊個為準。

### C. forex_reports（P1，併入 #39）
- 220 頁用不同模板（forex_combined_v3_template.html）。
- 建議：套用統一報告骨架；抽 5 頁試行後全量替換；保留舊 URL（用 redirect／相同檔名覆蓋）。

### D. ccy 詳情頁 37 頁（P1）
- 現時主要展示歷史 ranking；建議：
  1. 接 #36 數據層，顯示「最新 H1／H4／D1 三檔強弱」；
  2. 加「同貨幣對比」（例如 EUR vs USD 近 20 日走勢）；
  3. 加 stale 標記（同 #18 一致）。

### E. ccy_power 5 頁（P0，卡 #18）
- 三個缺陷已記錄（D1 停 2026-06-12、M30 停 2026-10-19、corrupted rows）。
- 建議：stale 閘＋頁面標「資料過期」；補 MT4-2 掛 D1/M30 圖操作單（已喺 #18）。
- 額外：**用 50 檔 PowerHistory 做「歷史對照」分頁**——即使即時數據停，歷史仍可展示（零風險）。

### F. portfolios 12 頁（P2）
- 建議：與 CCY Power／風險指標交叉引用（每個組合標「主要貨幣暴露」）；加「與 ranking 排名一致性」提示。

### G. campaign／reviews／admin 21 頁（P1）
- 全部併入 #39 統一導航；admin 頁加「數據新鮮度／CI 狀態」小卡。

### H. 根目錄孤兒頁（P1）
- `ff54_report.html`、`ea_strategy_masterplan.html`：入導航或搬入 `docs/reports/`；`index.html` 應為唯一入口。
- 加 robots／sitemap 檢查，避免舊連結 404。

## 三、跨版共通改善（建議一次過做）

1. **單一模板引擎**：head／nav／footer／KPI 卡／表格樣式抽成共用 include；新頁只寫內容。
2. **數據指紋**：每頁 footer 標「數據源＋sha256 前 8 位＋生成時間」，杜絕「唔知邊份數」。
3. **口徑表**：站內加一頁「方法說明」（勝率／盈虧比／MAE／MFE／馬丁層數定義），全部報告連去同一頁。
4. **舊版管理**：所有退役頁加「舊版」標記＋指向新版；避免客戶睇錯。
5. **CI 護欄**：頁數、導航注入、數據指紋齊全度納入閘（配合 #23／#24 修紅燈）。

## 四、執行次序（建議）
1. 今週：A（#38 修 5 錯）＋ E（#18 stale 閘）
2. 下週：H（孤兒頁）＋ G（導航）→ #39 模板統一第一版
3. 兩週內：C（forex_reports 套模板）＋ D（ccy 接新數據）
4. 一個月：B（autopsy 退役決策）＋ F（組合交叉引用）＋ 共通 5 項

— AUTOCLAW（AC lane）
