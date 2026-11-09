> ✅ 已處理 2026-11-09 by OpenClaw（補章——not-fixed 127 清單入帳；跟進按 2100 批示＋0725 補章，見 from_openclaw 對應檔）

# TSA 未改好 127 頁點名清單（終版）

**掃描時間**：2026-11-07 20:15 HKT｜**方法**：機器掃 v3（閘門＝批0 browser 閘靜態等價：--card2 var #1C2638＋html/body bg rgb(15,21,32)）＋6 加密殼解密先掃＋agent-browser 17 頁實測覆核＋批0 405 頁 CSV 對賬（402/405 一致，3 差異全部查清）

全站 **892 頁＝過閘 765＋未達標 127**。分組：
- B・半程缺 token var（深底新殼，補 tsa_tokens.css 即達標）：**4 頁**
- C1・bg 透明（html/body 無背景→白底渲染，輕修：補 bg #0F1520）：**6 頁**
- C2・bg 舊深藍系（#0A0E1A 等，輕修：統一 #0F1520）：**4 頁**
- C3・bg #0F172A 微差（輕修：統一 #0F1520）：**2 頁**
- D・W5-C v3.9 light 豁免族（NAV 三件已注入・tokens 豁免・淺色 var 設計——W-FINAL 深頁標準下未達標，請裁）：**98 頁**
- E・自帶 palette 異系（非標準 token 制，browser 實測深色自帶底）：**5 頁**
- F・舊工具頁（淺色舊殼）：**2 頁**
- G・admin 內部工具／加密殼（批0 建議裁定豁免）：**5 頁**
- H・待刪（G4 裁決中）：**1 頁**

## B・半程缺 token var（深底新殼，補 tsa_tokens.css 即達標）（4 頁）
### 批0 已測 root 補漏（docs/ 根層）（4 頁）
- ff54_report.html
- index.html｜加密殼
- merged_report_11141.html
- symbol_ranking.html

## C1・bg 透明（html/body 無背景→白底渲染，輕修：補 bg #0F1520）（6 頁）
### 批2（docs/reports/）（2 頁）
- reports/date_range_review/review_2026-04-01_2026-05-31.html
- reports/date_range_review/review_2026-04-01_2026-05-31_signal_31593.html

### 批3（docs/forex_reports/）（4 頁）
- forex_reports/2026-05-24_morning.html
- forex_reports/2026-05-25_evening.html
- forex_reports/2026-05-26_morning.html
- forex_reports/2026-06-12_morning_b.html

## C2・bg 舊深藍系（#0A0E1A 等，輕修：統一 #0F1520）（4 頁）
### 批3（docs/forex_reports/）（4 頁）
- forex_reports/2026-05-23_morning.html
- forex_reports/2026-05-24_evening.html
- forex_reports/2026-05-26_evening.html
- forex_reports/2026-05-28_morning.html

## C3・bg #0F172A 微差（輕修：統一 #0F1520）（2 頁）
### 批1（老闆點名四頁）（1 頁）
- ccy_power/index.html

### 批3（docs/forex_reports/）（1 頁）
- forex_reports/index.html

## D・W5-C v3.9 light 豁免族（NAV 三件已注入・tokens 豁免・淺色 var 設計——W-FINAL 深頁標準下未達標，請裁）（98 頁）
### 批2（docs/reports/）（98 頁）
- reports/Signal_Deep_Analysis_10344.html｜W5C
- reports/Signal_Deep_Analysis_10843.html｜W5C
- reports/Signal_Deep_Analysis_11598.html｜W5C
- reports/Signal_Deep_Analysis_12733.html｜W5C
- reports/Signal_Deep_Analysis_13798.html｜W5C
- reports/Signal_Deep_Analysis_16266.html｜W5C
- reports/Signal_Deep_Analysis_16596.html｜W5C
- reports/Signal_Deep_Analysis_16777.html｜W5C
- reports/Signal_Deep_Analysis_19625.html｜W5C
- reports/Signal_Deep_Analysis_19849.html｜W5C
- reports/Signal_Deep_Analysis_25260.html｜W5C
- reports/Signal_Deep_Analysis_27226.html｜W5C
- reports/Signal_Deep_Analysis_2739.html｜W5C
- reports/Signal_Deep_Analysis_32541.html｜W5C
- reports/Signal_Deep_Analysis_35362.html｜W5C
- reports/Signal_Deep_Analysis_35434.html｜W5C
- reports/Signal_Deep_Analysis_35436.html｜W5C
- reports/Signal_Deep_Analysis_38678.html｜W5C
- reports/Signal_Deep_Analysis_3894.html｜W5C
- reports/Signal_Deep_Analysis_4022.html｜W5C
- reports/Signal_Deep_Analysis_4734.html｜W5C
- reports/Signal_Deep_Analysis_5117.html｜W5C
- reports/Signal_Deep_Analysis_7919.html｜W5C
- reports/Signal_Deep_Analysis_7999.html｜W5C
- reports/index_36512.html｜W5D｜TemplateA族
- reports/index_36655.html｜W5D｜TemplateA族
- reports/index_5117.html｜W5D｜TemplateA族
- reports/signal_10344.html｜W5E
- reports/signal_10437.html｜W5E
- reports/signal_106.html｜W5E
- reports/signal_10843.html｜W5E
- reports/signal_10864.html｜W5E
- reports/signal_11889.html｜W5E
- reports/signal_11984.html｜W5E
- reports/signal_12173.html｜W5E
- reports/signal_12733.html｜W5E
- reports/signal_12962.html｜W5E
- reports/signal_13461.html｜W5E
- reports/signal_13790.html｜W5E
- reports/signal_13798.html｜W5E
- reports/signal_13863.html｜W5E
- reports/signal_14158.html｜W5E
- reports/signal_14341.html｜W5E
- reports/signal_14581.html｜W5E
- reports/signal_14592.html｜W5E
- reports/signal_1470.html｜W5E
- reports/signal_14724.html｜W5E
- reports/signal_16266.html｜W5E
- reports/signal_16538.html｜W5E
- reports/signal_16596.html｜W5E
- reports/signal_16698.html｜W5E
- reports/signal_16706.html｜W5E
- reports/signal_16777.html｜W5E
- reports/signal_17547.html｜W5E
- reports/signal_17611.html｜W5E
- reports/signal_17823.html｜W5E
- reports/signal_17962.html｜W5E
- reports/signal_19625.html｜W5E
- reports/signal_1980.html｜W5E
- reports/signal_19849.html｜W5E
- reports/signal_20805.html｜W5E
- reports/signal_20846.html｜W5E
- reports/signal_21698.html｜W5E
- reports/signal_22200.html｜W5E
- reports/signal_22278.html｜W5E
- reports/signal_2351.html｜W5E
- reports/signal_23617.html｜W5E
- reports/signal_25260.html｜W5E
- reports/signal_25668.html｜W5E
- reports/signal_25830.html｜W5E
- reports/signal_27226.html｜W5E
- reports/signal_2739.html｜W5E
- reports/signal_30359.html｜W5E
- reports/signal_31593.html｜W5E
- reports/signal_31781.html｜W5E
- reports/signal_32278.html｜W5E
- reports/signal_32541.html｜W5E
- reports/signal_32719.html｜W5E
- reports/signal_3291.html｜W5E
- reports/signal_33101.html｜W5E
- reports/signal_34259.html｜W5E
- reports/signal_34574.html｜W5E
- reports/signal_35362.html｜W5E
- reports/signal_35434.html｜W5E
- reports/signal_35436.html｜W5E
- reports/signal_36338.html｜W5E
- reports/signal_36397.html｜W5E
- reports/signal_36511.html｜W5E
- reports/signal_38561.html｜W5E
- reports/signal_3894.html｜W5E
- reports/signal_4734.html｜W5E
- reports/signal_5001.html｜W5E
- reports/signal_5275.html｜W5E
- reports/signal_537.html｜W5E
- reports/signal_5566.html｜W5E
- reports/signal_5636.html｜W5E
- reports/signal_7919.html｜W5E
- reports/signal_8325.html｜W5E

## E・自帶 palette 異系（非標準 token 制，browser 實測深色自帶底）（5 頁）
### 批2（docs/reports/）（1 頁）
- reports/anomaly_report.html

### 批5（portfolios＋admin＋ccy_power）（4 頁）
- ccy_power/copy_trade_portfolio.html｜W5H
- ccy_power/copy_trade_v2.html｜W5H
- ccy_power/portfolio_recommendation.html｜W5H
- portfolios/portfolio_master_report_v2.html｜W5G

## F・舊工具頁（淺色舊殼）（2 頁）
### 批0 已測 root 補漏（docs/ 根層）（2 頁）
- analyzer.html
- tug_of_war_calculator.html

## G・admin 內部工具／加密殼（批0 建議裁定豁免）（5 頁）
### 批5（portfolios＋admin＋ccy_power）（5 頁）
- admin/ccy_auto_trader/index.html
- admin/db-browser.html｜加密殼
- admin/index.html｜加密殼
- admin/mt5_mcp_tools.html｜加密殼
- admin/tasks_board.html｜加密殼

## H・待刪（G4 裁決中）（1 頁）
### 批2（docs/reports/）（1 頁）
- reports/sample_redesign_36912.html

## 批次對照總表

| 批 | 總頁 | 過閘 | 未達標 |
|---|---|---|---|
| 批1 | 4 | 3 | 1 |
| 批2 | 475 | 373 | 102 |
| 批3 | 205 | 196 | 9 |
| 批4 | 44 | 44 | 0 |
| 批5 | 19 | 10 | 9 |
| 批0root補漏 | 145 | 139 | 6 |
| **全站** | **892** | **765** | **127** |

## 註
- D 族 98 頁有 W5 注入註釋（`tokens 豁免`）為憑——v3.9 豁免原意＝防止 dark tokens 接管 var 令 light 設計翻黑破版（W5C 信技術理由），唔等於 W-FINAL 深頁視覺達標，故列未達標＋請裁。
- B 組 root index.html 為加密殼（general 鎖），解密後掃描＋browser 實測＝bg 新但缺 token var＋sidebar container（中間態，同 signal_ranking 0825 修復前同款）。
- C1 組 date_range 2 頁 tokens 已鏈（card2/accent var 齊）但 html/body 無背景→白底渲染（browser 實測 transparent×2）。
- 對賬：批0 405 頁 381 過→而家 382 過（signal_ranking 0825 修復 +1）；24 唔跟→23 全數對上＋signal_ranking 已修＝閉環。新發現 103 頁全部喺批0 從未 browser 覆蓋範圍。