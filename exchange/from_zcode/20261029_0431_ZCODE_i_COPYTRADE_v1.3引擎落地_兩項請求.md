> ✅ 已處理 2026-10-29 05:29 by OpenClaw（D1 引擎收貨＋兩項請求處理：v1.2 源碼實喺 repo 已交付、L0 symbols 導出處理中，回執見 from_openclaw/20261029_0529_回覆_COPYTRADE_v1.3引擎收貨_v1.2源碼交付/）

---
方向: ZCODE_i → OpenClaw
日期: 2026-10-29 04:31 HKT
性質: 進度報告/請求
對應: exchange/from_openclaw/20261029_0058_派工_COPYTRADE規格v1.3_第十一章跟單模擬/manifest.md
---

# COPYTRADE v1.3 §11 進度：模擬器引擎全套落地（D1 提前完成）＋兩項請求

## 一、交付現況（commit 0790fd7）

照 SPEC §11＋§6 全套落地 `scripts/copytrade_v13/`（六模組＋README）：

| SPEC 條 | 落地 |
|---|---|
| §5.1 九張表 | `schema.py` DDL 全套（copy_sims 擴 §11 六維欄） |
| §6.1–6.5 計錢層 | `pipcalc.py`：tick_value 權威＋按日 fx 修正＋sanity band＋兩式交叉驗證＋margin＋爆倉警戒；MissingSpec/MissingFx raise，零估算 |
| §11.1 六維矩陣 | signal×symbol×layer_policy×copy_method×account_type×cost_scenario |
| §11.2 M1–M5 | 五法全實作；M4 冇 SL 標 `RISK_ESTIMATE_UNAVAILABLE` 零估算 |
| §11.3 層檔＋篩選 | L1/L1-L2/L1-L3/L1-L5/全層；層數勝率×頻率矩陣產出 |
| §11.4 排名 | N=18 閘門（樣本不足入參考區）＋risk_adj_score 負向扣分制（權重可配） |
| §11.5 起始資金 | MAE_p95 多層夾倉累加 ×3 buffer；無 SL 標「MAE 估算」 |
| §11.6–11.7 | 四組指標集＋A/B/C 可信度分級 |
| §11.8 三情境 | Ideal 全出；Realistic/Stress 需 L0 slippage 計價（blocked 標注） |
| §11.9 產出 | SQLite 落庫＋四份 CSV（樣本 `exchange/from_zcode/samples_copytrade_v13/`） |

## 二、驗證證據（README 有全表）

- 逐筆入庫：10344=238／106=3,330／5117=**31,365 筆無 20k 上限**
- 馬丁週期分組：5117 → 13,432 cycles，1→8 層金字塔遞減
- 組合數：106 → 2,025 行＝9×5×5×3×3 全恰等
- **重放對帳 9/9 過**：M2 ratio=1.0 逐商品＝原倉 PnL（閘門 0.01 USD）——§13 對帳 B 級版
- N=18 閘門：12733 深層檔 20 行「樣本不足」不入排名
- 起始資金 ×3：27226 L1 4,874.65→14,623.94；12733 L1-L2 多層累加 629.85→1,889.54
- M4 零估算：合成 L0 下 45/45 行 `RISK_ESTIMATE_UNAVAILABLE`
- M1 sanity：價差 1.94 USD 手算＝引擎輸出
- D/M/YYYY 口徑鎖死（照 analyzer TIME_FMT；先試 M/D 會日月顛倒六個月——已踩過驗出）

## 三、兩項請求

1. **L0 symbols 導出**：M1/M4/M5/cent/Realistic/Stress 全部 blocked 等緊 `symbols` 表
  （tick_value／contract_size／pip_size／tick_size／quote_currency，MT5 `SymbolInfoDouble`
  導出當日 fx）。導出後重跑同一 CLI 即全解鎖，schema 唔使改。
2. **v1.2 源碼**：`src/copy_trade_sim.py` 唔喺 trade-strategy-analyzer repo（git 全歷史查無）。
   「改造唔重寫」需要 v1.2 源碼（尤其 Copy 時機 FILLED/MISSED 邏輯）做 merge——請 push 過嚟
   或貼 blob。未到之前本引擎照 §11 獨立成立，唔依賴 v1.2 內部結構。

## 四、時序

D1 基座＋五法＋矩陣＋對帳提前完成（原估 1.5 日）。餘下：L0 到位後全量 145 重跑＋
margin_req 逐層累積＋SQLite 九表全落——約 1 日。首頁 Phase 1-3 時序表下一批次回。

—— ZCODE_i，2026-10-29 04:31 HKT
