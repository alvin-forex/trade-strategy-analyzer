# ccy_backtest — CP-BT1 CurrencyPower v3.10 Python 移植＋parity

派工單：`exchange/from_openclaw/20261116_1235_派工_CP-BT1_CurrencyPower移植_parity.md`
重發（平台接單）：`exchange/from_openclaw/20261119_1325_派工_ZCODE平台_CPBT1_CurrencyPower移植.md`

- 執行 lane：平台 ZCODE（判準 1–4 全中：純 Python＋白皮書公式＋無編譯／無終端依賴＋機器可驗收）
- 階段 A（本目錄）：目錄骨架＋計算核心移植＋自測 —— 死線 2026-11-21 18:00 HKT
- 階段 B：parity 誤差表＋cp_power_history 序列檔（等 OC 供料）—— 死線 2026-11-23 18:00 HKT

## 目錄結構

```
ccy_backtest/
  __init__.py     版本標記
  indicators.py   Wilder RSI / Wilder ATR（對齊 MT4 iRSI / iATR 語義）
  universe.py     9 貨幣 × 36 instruments 預設宇宙＋帶符號方向
  core.py         raw=RSI−50、w=ATR%、9 貨幣分解引擎（聚合熱點隔離）
  dataio.py       docs/data/*_TF.json loader＋通用 OHLC CSV loader
  series.py       cp_power_history writer／reader（CSV）
  parity.py       階段 B 誤差矩陣（≥10 ts × 9 幣＋AVG，料未到拋 ParityPendingError）
  cli.py          run / parity / selftest
  tests/          18 條手算例單元測試（期望值逐步展開算術，非實現重跑）
  out/            run 產出（樣本序列檔）
  ref/            （空）白皮書 PDF＋已知缺陷清單落位處，等 OC 供料
```

## 公式鏈（派工信原文）

```
iRSI(PairTF, RSI_Period) → raw = RSI − 50
iATR(PairTF)             → w = ATR%（波動加權）
9 貨幣分解引擎（36 instruments）
```

指標語義照 MetaQuotes 官方 RSI.mq4／ATR.mq4：
- RSI：首值喺 index=period（頭 period 個變化簡單平均），之後 Wilder 平滑
  `(prev×(N−1)+x)/N`；`avg_loss==0 → 100`（含全平盤；唔拋 nan）
- ATR：`TR=max(h,c_prev)−min(l,c_prev)`；首值=SMA(頭 period 個 TR)，之後 Wilder 平滑

## 假設登記表（白皮書未到手，parity 到料即校——每條都要 OC 確認或白皮書推翻）

| # | 假設 | 落點 | 影響 |
|---|---|---|---|
| A-1 | 宇宙＝28 法幣對＋8 條 XAU 交叉＝36；原作 Alpari 金交叉 G=5 | universe.py `GOLD_CROSSES` | 若白皮書 G≠8，改一個 list 即可 |
| A-2 | ATR%＝iATR/close×100 | core.py `pair_weight_series` | 替代定義（如 ATR/ATR均線）parity 校 |
| A-3 | **聚合＝帶符號 ATR% 加權平均**（base 記 +raw×w、quote 記 −raw×w） | core.py `aggregate_currency` | **最大假設熱點**；白皮書真聚合公式到料只改呢個函數 |
| A-4 | AVG＝9 幣 power 簡單平均（只計有值幣） | core.py `compute_power_history` | 白皮書確認 |
| A-5 | RSI_Period＝ATR_Period＝14（MT4 預設） | cli 預設參數 | 白皮書確認 |
| A-6 | 缺料 instrument 自動退出聚合（N_c 按在場計） | core.py | docs/data 現只有 4 條 XAU 交叉；終端全量到料自動補齊 |
| A-7 | 顯示刻度映射：暫恒等（RSI 空間 ±50）；原作面板 0..9（中點 4.5）映射待白皮書 | core.py `to_display_scale` | parity 前必須落實 |
| A-8 | 已知缺陷清單未到手——「缺陷照抄」暫無從執行 | indicators.py 預留 DEFEAT_* 位 | 白皮書到料後逐條重現 |

## 已知缺口（等 OC data lane 11-20 12:00 供料，notify 通知）

1. 白皮書 `CurrencyPower_v3_WhitePaper_v310.pdf`（audit-grade：公式＋已知缺陷清單）——唔喺 repo
2. 源碼參考 `CurrencyPower_v3.audit_package.zip` 內 .mq5（v3.10 為準）——唔喺 repo
3. D1／H4 歷史 OHLC 樣本（終端 history 匯出）＋ A06E `ccy_power_reader.csv` 同 timestamp 抽樣
4. docs/data/ 只有 D1（2018-11→2026-04）34 對中 32 對在場、H4 全缺——樣本自測可以，parity 唔夠

建議落位：`ccy_backtest/ref/`（白皮書＋缺陷清單＋audit zip）。

## 跑法

```bash
# 自測（合成數據方向檢查）
python3 -m ccy_backtest.cli selftest

# 單元測試（18 條手算例）
python3 -m pytest ccy_backtest/tests/ -q

# 用 repo 內建 D1 數據出樣本序列（唔係 parity 源）
python3 -m ccy_backtest.cli run --tf D1 --out ccy_backtest/out/cp_power_history_sample_D1.csv

# 階段 B parity（料到先跑，唔會静默扮成功）
python3 -m ccy_backtest.cli parity --series <重建序列csv> --reader <reader抽樣csv> --out ccy_backtest/out/parity_report.csv
```

## 序列檔格式（cp_power_history）

每 bar 一行 × 9 貨幣＋AVG，帶 timestamp/TF（派工信規格）：

```
timestamp,tf,eur,usd,jpy,gbp,chf,aud,cad,nzd,xau,avg
2026-04-17,D1,0.405032,-7.096695,-6.593616,0.498790,1.490118,10.039152,-1.075998,-0.019204,1.887481,-0.051568
```

None（warmup／缺料期）寫空字串。數值係 RSI 空間（±50，0＝中性），
0..9 面板刻度映射（A-7）白皮書到料後接入。

## 階段 A 自測結果（2026-11-20）

- pytest：18/18 PASS（手算例：RSI period1/2 逐步展開、全平盤=100 MT4 語義、
  ATR period2/3 逐步展開、分解引擎兩對手算（EUR=+50/USD=0/JPY=−50）、
  缺料退出、序列檔 roundtrip）
- cli selftest：4/4 PASS
- repo D1 實跑：32 instruments 聯集 1937 row（warmup 14 行），
  全覆蓋（≥30 instrument）1905 行，尾段全覆蓋 row 2026-04-17
  九幣齊（AUD +10.04 最強／USD −7.10 最弱，XAU N=4 因只有 4 條交叉有料）
