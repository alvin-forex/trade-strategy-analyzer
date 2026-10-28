# 派工：COPYTRADE 規格 v1.3——第十一章「跟單模擬」實作

> 方向: OpenClaw → ZCODE_i
> 日期: 2026-10-29 00:58 HKT
> 性質: 派工——規格書已升級 v1.3（新增第十一章「跟單模擬」），請 ZCODE_i 照章實作
> 對應: 老闆 2026-10-29 00:39（確認 M1–M5／層數政策／四維排名＋MFE 風險計量）＋00:53（拍板 N=18／buffer 3×／併主 SPEC 做 v1.3 再交 ZCODE）

---

## 一、背景

老闆要求：**「各 SIGNAL × SYMBOL × 層數 × 不同跟單方法」的跟單交易模擬結果**，目的係選出值博率最高／最有優勢嘅組合，以較多數據印證。

已傾好（老闆批核，全部落鎖入 SPEC §11.0）：

| 參數 | 值 |
|---|---|
| 樣本數閘門 N | **18**（組合 cycle < 18 → 「樣本不足」不入排名） |
| 起始資金 buffer | **3×**（＝當作連續承受 3 次 SL） |
| 跟單方法 | **M1–M5** 五種並跑 |
| 層數政策 | **L1／L1–L2／L1–L3／L1–L5／全層** 五檔 |
| 排名規則 | 四維（月增長＋Max DD＋Margin 回報率＋穩定性）＋**風險調整扣分制** |
| 成本情境 | Ideal／Realistic／Stress 三套獨立跑 |

**老闆篩選邏輯（§11.3，不可省略）**：先篩勝率偏高層數 → 再看頻率（勝率極高但頻繁太少參考價值也低）→ 勝率＋頻率雙高先計單層回報 → 考慮連續複製多層 → 有時兩種複製方法並行 A/B → 較多數據印證。

**MFE/MAE 風險計量（§11.5，老闆重點）**：用歷史 MAE 分佈計「開始 COPY 時真實夾倉／單層或多層 SL 成本」→ 反推起始資金（建議起始資金 = 多層夾倉成本 × 3）。每組合輸出 `est_sl_cost_usd`／`est_margin_peak_usd`／`suggested_start_equity_usd`。

## 二、附件（git-blob8 已標）

| 檔名 | git-blob8 | size | 說明 |
|---|---|---|---|
| COPY_TRADE_SYSTEM_SPEC_v1.3.md | `4c5b676f` | 39,379 | 主規格 v1.3（第十一章 11.0–11.9 全） |
| COPY_TRADE_SYSTEM_SPEC_v1.3.pdf | `cb21d8b4` | 834,732 | 同內容 PDF（render 產物） |

> 注意：主檔檔名仍係 `COPY_TRADE_SYSTEM_SPEC_v1.0.md`（git 歷史慣例），**檔內版本頭已係 v1.3**；本派工包內副本改名 `_v1.3.md` 方便辨識。OpenClaw 側 master 版本喺 `/home/alvin/.openclaw/workspace/main/docs/spec_copy_trade/`。

## 三、請 ZCODE_i 實作（照 SPEC 第十一章）

1. **跟單模擬器**：改造現有 `src/copy_trade_sim.py`（v1.2 已批：改造唔重寫）→ 支援六維模擬矩陣
   - `signal_id × symbol × layer_policy × copy_method × account_type × cost_scenario`
   - tick_value 唯一權威（§6.2）；margin 可配置預設 500（§6.4）；爆倉層級警戒線（§6.5）
   - cent/USD/demo 分開：cent 用 broker 真實 contract_size／tick_value 重算，**唔可以 USD lot 直接除 100**
2. **五種跟單方法 M1–M5**（§11.2 定義）：M1 固定手數／M2 原始手數比例／M3 資金比例／M4 固定金額風險（冇 SL 標 `RISK_ESTIMATE_UNAVAILABLE`，唔准估）／M5 層數＋margin cap
3. **層數政策**（§11.3）：L1／L1–L2／L1–L3／L1–L5／全層；每個 layer_policy 輸出勝率＋頻率（cycle 數）兩欄
4. **排名規則**（§11.4）：樣本數閘門 N=18；risk_adj_score 扣分制（月增長×0.4＋穩定月×0.2 − MaxDD%×0.25 − 蒸發風險×0.15，權重可配）；輸出詳細分析表＋決策排名表（建議欄：優先／可研究／不建議）
5. **MFE/MAE 起始資金計量**（§11.5）：MAE_p95 × 每點值 × 手數 → 多層夾倉成本（按馬丁倍數累加）→ ×3 buffer；冇 SL 用 MAE_p95 估算，標「MAE 估算」
6. **指標集**（§11.6 四組）+ **資料可信度分級**（§11.7：A 完整模擬／B TRADE-RECORD REPLAY／C PARTIAL_SIMULATION，唔准過度聲稱）+ **三套成本情境**（§11.8）
7. **產出**（§11.9）：詳細分析表／決策排名表／層數勝率×頻率矩陣／MFE 風險報告
8. **落庫**：SQLite 先行（v1.2 §9 已批）；輸出形式照 §7.4

## 四、驗收標準（ZCODE_i 交付時附證據）

- [ ] 模擬結果同 v1.2 §6.3 兩式交叉驗證一致（tick_value 權威鏈）
- [ ] M4 冇 SL 交易正確標 `RISK_ESTIMATE_UNAVAILABLE`，零估算
- [ ] 樣本閘門 N=18 生效：<18 cycle 標「樣本不足」入參考區
- [ ] 起始資金 = 夾倉成本 × 3 落鎖
- [ ] cent/USD/demo 三帳結果分開，cent 唔係簡單 ÷100
- [ ] 資料可信度分級標籤正確（A/B/C）
- [ ] 三套成本情境獨立輸出
- [ ] SQLite schema 符合 §5.1 九張表（如有增表須列明）

## 五、優先級同其他工單關係

- 本工單**唔阻塞**首頁 v1.1 Phase 1–3（兩線獨立）
- 與 CP v3.11 MTF、七問同一張 i lane 工單排隊，但**建議優先**：老闆 00:39–00:53 連環批核，屬 hot line
- 若同首頁 Phase 1 撞資源，請喺回信講明排法，等我同老闆確認

## 六、回覆要求

1. 收到蓋 `> ✅ 已處理`（照慣例）
2. 報實作時序（估時）
3. 交付：patch（diff）＋測試證據＋SQLite 產出樣本
4. commit 前綴 `exchange:`；唔 force push；唔提交 credentials

—— OpenClaw（main agent），2026-10-29 00:58 HKT
