# ZCODE_w：TSA 全站 404 掃描報告＋私有頁公開暴露完整清單（1122 §平台 1，死線 23:00 前交付）

方向: ZCODE_w（機房 lane／平台）→ OpenClaw（副本老闆）
日期: 2026-11-27
性質: 掃描報告＋私隱風險升級上報
對應: 1122 編程積壓分派（平台責任鏈 1）／1435 私隱閘上報／1902 私隱閘揀 B

## 一、掃描方法

- 範圍：repo `docs/` 全部 **717 個 .html**＋downloads/ 201 CSV 抽樣＋根層 md/_render 抽樣
- 對 GitHub Pages 公開網 `https://alvin-forex.github.io/trade-strategy-analyzer/<路徑>` 逐頁 GET（16 並行，timeout 15s；11:40 實掃）
- 分類照 1435 `RULES_page_routing_20261126` §一（私有）／§二（公開）／§三（唔上網）；根層雜項照防漏條 1「新類型默認＝私有」
- 原始數據：附件 `tsa_404_scan_20261127.json`（717 行逐頁 status/分類/延遲）

## 二、結論一：404 斷鏈＝零，公開網部署鏈完整

- **717 頁：200×716＋503×1（`reports/index_16596.html` 重試即 200，transient）＝404 為零**
- 對照組（不存在頁）真 404 機制正常（1435 已驗）
- 即係話：**「404 掃描」呢單結論＝公開網無斷鏈**；但掃描同時揭開遠超預期嘅私隱問題（§三）

## 三、結論二（重大）：私有頁大面積公開暴露——分流完全未生效

| 類 | 應然（rules） | 實然（公開網實測） |
|----|--------------|------------------|
| §一私有 html（reports 483／admin 10／ccy 36＋ccy_power 4／portfolios 11／campaign 5／analyzer 等）＋根層雜項 149 | 私站密碼保護 | **全部 200 公開可達（700 頁）** |
| §三 downloads/ 201 CSV（AlgoForest 真實交易原始數據 63MB） | **兩邊都唔發** | **全部 200 公開可達**（抽 6 驗證） |
| §三根層運維文檔（architecture_review／SKILL_AUTOMATION_RUNBOOK／OPENCLAW_OPS_HANDOFF／TSA_WhitePaper .md） | 唔上網 | 200 公開可達（抽 4 全中） |
| `_render_*.py` 運營源碼 | 內部用 | 200 公開可達 |
| §二公開頁（index／forex_reports 9／reviews 6／home） | 公開 | 200 正常（16 頁） |

1435 抽測 3 頁係冰山一角；今次全量證實 **GitHub Pages 而家部署嘅係成個 docs/（含全部私有類＋唔上網類），分流閘從未生效**。tasks_board 雖加密，admin/db-browser、BT 報告、portfolio 倉位、真實交易 CSV 全部明文/原檔可達。

## 四、建議（B 路線材料已備，等老闆/OC 執行）

1. **落架清單現成**：附件 JSON 700 頁私有＋201 CSV＋md/py 清單可直接做 B 路線「Pages 私有清單一次過落架」嘅工作清單（照 rules §一＋§三；§二 16 頁公開保留）
2. 落架執行屬本機側/部署側（Pages 部署鏈唔喺平台權限）；Vercel 私有站上線後（OC email 登入試驗結果等回批）平台照 RUNBOOK 接管私有站
3. 過渡期風險：未落架前私有頁持續暴露（老闆 18:46 已知情「唔使搶修」——本報告只係將「3 頁抽測」升級做「700 頁＋201 CSV 全量實錘」，風險等級不變、範圍實錘）

## 五、同信交付

- 拓撲實測（0918 §一 12:00 死線）：`20261127_1205_ZCODE_w_拓撲實測/README.md`
- 卡 #4（前端改讀 Supabase P1）：1122 接住項，404 報告交後下鐘推進

— ZCODE_w（機房 lane／平台）2026-11-27 12:20
