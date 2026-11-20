#!/usr/bin/env python3
"""CCY Power v3.10 計算核心 Python 移植（CP-BT1，平台 ZCODE）。

模組：
  indicators  — Wilder RSI / Wilder ATR（對齊 MT4 iRSI / iATR 語義）
  universe    — 9 貨幣 × 36 instruments 預設宇宙＋帶符號方向
  core        — raw=RSI−50、w=ATR%、9 貨幣分解引擎
  dataio      — docs/data/*_TF.json loader＋通用 OHLC CSV loader
  series      — cp_power_history 序列檔 writer
  parity      — 對照 ccy_power_reader.csv 誤差表（階段 B，等 OC 供料）
  cli         — run / parity / selftest

公式來源與假設登記表見 README.md（白皮書未到手前，聚合層屬假設版，
已隔離在 core.aggregate_currency，parity 到料即校準）。
"""

__version__ = "0.1.0-stageA"
