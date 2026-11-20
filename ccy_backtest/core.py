#!/usr/bin/env python3
"""CP-BT1 分解引擎：raw=RSI−50、w=ATR%、9 貨幣分解。

派工信公式鏈（20261119_1325 派工_ZCODE平台_CPBT1，原文）：
  iRSI(PairTF, RSI_Period) → raw = RSI − 50
  iATR(PairTF)             → w = ATR%（波動加權）
  9 貨幣分解引擎（36 instruments）

假設登記（白皮書 CurrencyPower_v3_WhitePaper_v310.pdf 未到手，到料即校）：
  A-1 宇宙：28 法幣對＋8 條 XAU 交叉＝36（universe.py，GOLD_CROSSES 可調）
  A-2 ATR% 定義：w = iATR / close × 100（相對波動；替代定義 ATR/ATR均值 等 parity 校）
  A-3 聚合：Power_c = Σ(±raw×w) / Σw（帶符號 ATR% 加權平均，±按 base/quote）
      ——本函數係唯一假設熱點，隔離喺 aggregate_currency()，parity 逐 TBAR 校準後只改呢度
  A-4 AVG = 9 幣 power 嘅簡單平均
  A-5 RSI_Period / ATR_Period 預設 14（MT4 預設值；白皮書到料後確認）
  A-6 缺料 instrument（例如 docs/data 只有 4 條 XAU 交叉）自動退出聚合，
      N_c 按該幣在場 instrument 計；全量終端數據到料後自然補齊

輸出 row 格式（dict）：
  {"ts": "2026-04-17", "tf": "D1",
   "power": {"EUR": -3.21, ...9 幣..., "XAU": 1.23}, "avg": 0.45,
   "n_partners": {"EUR": 8, ..., "XAU": 4}, "coverage": 32}
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Sequence

from . import indicators, universe


def pair_raw_series(closes: Sequence[float], rsi_period: int = 14) -> List[Optional[float]]:
    """raw = RSI − 50（index<period 為 None）。"""
    return [None if v is None else v - 50.0
            for v in indicators.rsi_wilder(closes, rsi_period)]


def pair_weight_series(highs: Sequence[float], lows: Sequence[float],
                       closes: Sequence[float],
                       atr_period: int = 14) -> List[Optional[float]]:
    """w = ATR% = iATR / close × 100（assumption A-2）。close==0 防護 → None。"""
    atr = indicators.atr_wilder(highs, lows, closes, atr_period)
    out: List[Optional[float]] = []
    for i, a in enumerate(atr):
        if a is None or closes[i] == 0:
            out.append(None)
        else:
            out.append(a / float(closes[i]) * 100.0)
    return out


def aggregate_currency(signed_weighted_sum: float, weight_sum: float,
                       n_partners: int) -> Optional[float]:
    """假設熱點 A-3：帶符號 ATR% 加權平均。

    白皮書到料後，若真實聚合唔係加權平均（例如先按對內排名再計 up 計數、
    或者正交歸一），只改呢個函數（簽名可能跟住擴）。
    """
    if weight_sum == 0.0 or n_partners == 0:
        return None
    return signed_weighted_sum / weight_sum


def compute_power_history(
    data: Dict[str, dict],
    tf: str,
    rsi_period: int = 14,
    atr_period: int = 14,
    instruments: List[str] = None,
    currencies: List[str] = None,
) -> List[dict]:
    """主入口。

    data：{instrument: {"d": [...], "o": [...], "h": [...], "l": [...], "c": [...]}}
          每個 instrument 自己嘅 bars（可以唔齊口）。
    tf：  標籤字串（例如 "D1"／"H4"），寫入 row。
    回傳 row 列表（按時間序），row 見模組 docstring。

    對齊規則（階段 A 簡版，parity 到料後按終端 timestamp 對齊升級）：
    以全部 instrument 日期嘅聯集為軸；某 instrument 喺某日無 bar → 該日退出該 instrument。
    """
    if instruments is None:
        instruments = list(universe.INSTRUMENTS_36)
    if currencies is None:
        currencies = list(universe.CURRENCIES_9)

    # 每 instrument 預計算 raw/w 序列，並建 日期→index 映射
    pre = {}
    all_dates = set()
    for inst in instruments:
        if inst not in data:
            continue  # A-6：缺料 instrument 整隻退出
        bars = data[inst]
        dates = list(bars["d"])
        raw = pair_raw_series(bars["c"], rsi_period)
        w = pair_weight_series(bars["h"], bars["l"], bars["c"], atr_period)
        pre[inst] = {"idx": {d: i for i, d in enumerate(dates)},
                     "raw": raw, "w": w}
        all_dates.update(dates)

    rows: List[dict] = []
    for ts in sorted(all_dates):
        num = {c: 0.0 for c in currencies}
        den = {c: 0.0 for c in currencies}
        cnt = {c: 0 for c in currencies}
        coverage = 0
        for inst, p in pre.items():
            i = p["idx"].get(ts)
            if i is None:
                continue
            r = p["raw"][i]
            w = p["w"][i]
            if r is None or w is None:
                continue
            coverage += 1
            base, quote = universe.parse_instrument(inst)
            if base in num:
                num[base] += r * w
                den[base] += w
                cnt[base] += 1
            if quote in num:
                num[quote] += -r * w
                den[quote] += w
                cnt[quote] += 1
        power = {}
        for c in currencies:
            power[c] = aggregate_currency(num[c], den[c], cnt[c])
        vals = [power[c] for c in currencies if power[c] is not None]
        avg = sum(vals) / len(vals) if vals else None  # assumption A-4
        rows.append({"ts": ts, "tf": tf, "power": power, "avg": avg,
                     "n_partners": dict(cnt), "coverage": coverage})
    return rows


def to_display_scale(value: Optional[float]) -> Optional[float]:
    """顯示刻度映射（assumption A-7，佔位）。

    原作 FF 面板刻度 0..9（中點 4.5，1545 信）；v3.10 呢個移植版喺
    RSI 空間輸出（raw±50、聚合後理論範圍 ±50）。白皮書到料後若要求
    映射到 0..9 面板刻度做 parity，喺呢度加公式；未到料前恒等返回。
    """
    return value
