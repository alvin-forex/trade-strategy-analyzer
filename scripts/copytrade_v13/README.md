# COPYTRADE v1.3 §11 跟單模擬器（ZCODE 實作）

照 `COPY_TRADE_SYSTEM_SPEC_v1.3.md` 第十一章＋§6 核心計算定義落地。

## 模組

| 檔 | 職責 |
|---|---|
| `schema.py` | §5.1 九張表 DDL（唯一 schema 來源） |
| `pipcalc.py` | §6.1–6.5 唯一計錢層：pip_value（tick_value 權威＋按日 fx 修正＋sanity band）、兩式交叉驗證、margin、爆倉警戒 |
| `ingest.py` | CSV 逐筆入庫＋馬丁週期（cycle）分組（時間重疊法＋24h gap 保護） |
| `sim_engine.py` | §11.2 五法 M1–M5×三情境×三帳戶單 cycle 模擬 |
| `matrix.py` | §11.4 排名（N=18 閘門＋risk_adj_score 扣分制）＋§11.5 起始資金（夾倉×3）＋§11.6 指標集 |
| `run_sim.py` | CLI＋§11.9 四份產出 |

## 用法

```bash
cd scripts/copytrade_v13
python3 run_sim.py --signals 10344,106,5117 --db-reset   # 指定 signal
python3 run_sim.py --all --db-reset                       # 全量 145
```

產出：`data/copytrade.db`（SQLite 九表）＋ `data/copytrade/` 四份 CSV
（detailed_analysis／decision_ranking／layer_win_freq_matrix／mfe_risk_report）。

## 可信度與解鎖狀態（§11.7）

- 數據源 CSV 逐筆齊全 → `data_grade='A'`。
- **M2／M3 為比例重放**（broker 真實美元 × ratio，線性，零重算）——無 L0 亦可出
  Ideal／USD/demo 全量；**重放對帳已過**（M2 ratio=1.0 逐商品＝原倉 PnL，閘門 0.01 USD）。
- **M1／M4／M5／cent／Realistic／Stress 需要 L0**（`symbols` 表：tick_value／contract_size／
  pip_size／tick_size，MT5 `SymbolInfoDouble` 導出）——缺列時組合標
  `BLOCKED: 需 L0 symbols 導出`，**零估算**（§6.7 鐵律 2）。
- **M4 冇 SL → `RISK_ESTIMATE_UNAVAILABLE`**（沙盒合成 L0 驗證 45/45 行正確標注）。
- L0 導出後重跑同一命令即全解鎖，schema 不變。

## 已驗證（沙盒＋實數）

| 項 | 證據 |
|---|---|
| 逐筆入庫 | 10344=238／106=3,330／5117=31,365（無 20k 上限） |
| 馬丁週期分組 | 5117：13,432 cycles，1→8 層金字塔遞減 |
| 組合數 | 106：9 商品×5 層檔×5 法×3 帳戶×3 情境=2,025 ✓ |
| 重放對帳 | 106 九商品 M2 ratio=1.0 逐商品＝原倉，9/9 過 |
| N=18 閘門 | 12733 深層檔 20 行「樣本不足」不入排名 |
| 起始資金 ×3 | 27226 L1：4,874.65→14,623.94；12733 多層夾倉累加 |
| M4 零估算 | 合成 L0 下 45/45 行 RISK_ESTIMATE_UNAVAILABLE |
| M1 sanity | 價差 1.94 USD 手算＝引擎輸出 |
| D/M/YYYY 口徑 | 照 algoforest_analyzer TIME_FMT（先試 M/D 會日月顛倒六個月） |

## 待辦（L0 到位後）

- M1/M4/M5/cent/Realistic/Stress 全解鎖重跑；
- margin_req 表逐層累積（§6.4/6.5 margin peak、爆倉層級）；
- 兩式交叉驗證每筆跑（§6.3）；
- 與 v1.2 `copy_trade_sim.py` merge（v1.2 源碼在 OpenClaw workspace，待取得）。
