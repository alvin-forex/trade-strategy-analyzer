#!/usr/bin/env python3
"""Wilder RSI / Wilder ATR —— 對齊 MT4 iRSI / iATR 語義（CP-BT1 parity 基石）。

語義要點（照 MetaQuotes 官方 RSI.mq4 / ATR.mq4 邏輯，唔自作聰明修正）：

RSI（period=N）：
  - 變化序列 ch[i] = close[i] − close[i−1]，i 從 1 起
  - 首值喺 index = period：avg_gain / avg_loss = 頭 N 個變化嘅簡單平均
  - 之後 Wilder 平滑：avg = (prev*(N−1) + 本bar) / N
  - MT4 公式：avg_loss == 0 → RSI = 100（包括全平盤兩者皆 0 嘅情況）；
    否則 RSI = 100 − 100/(1 + avg_gain/avg_loss)（代數上等價 100*avg_gain/(avg_gain+avg_loss)）
  - index < period → None（MT4 buffer 前段無值）

ATR（period=N）：
  - TR[i] = max(h[i], c[i−1]) − min(l[i], c[i−1])
  - 首值喺 index = period：頭 N 個 TR 嘅簡單平均
  - 之後 Wilder 平滑：ATR = (prev*(N−1) + TR) / N
  - index < period → None

已知缺陷照抄：白皮書「已知缺陷清單」未到手（等 OC 供料入 ref/）；
到料後若有缺陷行為需要重現，喺呢度加 DEFEAT_* 開關，唔好改主公式。
"""

from __future__ import annotations

from typing import List, Optional, Sequence

Number = float


def rsi_wilder(closes: Sequence[Number], period: int) -> List[Optional[float]]:
    """MT4 iRSI 語義嘅 RSI 序列（與 closes 對齊，index<period 為 None）。"""
    if period < 1:
        raise ValueError("period 必須 >= 1")
    n = len(closes)
    out: List[Optional[float]] = [None] * n
    if n <= period:
        return out
    sum_gain = 0.0
    sum_loss = 0.0
    for i in range(1, period + 1):
        ch = float(closes[i]) - float(closes[i - 1])
        if ch > 0:
            sum_gain += ch
        else:
            sum_loss += -ch
    avg_gain = sum_gain / period
    avg_loss = sum_loss / period
    out[period] = _rsi_value(avg_gain, avg_loss)
    for i in range(period + 1, n):
        ch = float(closes[i]) - float(closes[i - 1])
        gain = ch if ch > 0 else 0.0
        loss = -ch if ch < 0 else 0.0
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        out[i] = _rsi_value(avg_gain, avg_loss)
    return out


def _rsi_value(avg_gain: float, avg_loss: float) -> float:
    """MT4 RSI.mq4：negative==0 → 100；否則 100 − 100/(1+gain/loss)。"""
    if avg_loss == 0.0:
        return 100.0
    return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)


def true_ranges(highs: Sequence[Number], lows: Sequence[Number],
                closes: Sequence[Number]) -> List[Optional[float]]:
    """TR 序列：TR[0] 無前收 → None；TR[i] = max(h,c[i−1]) − min(l,c[i−1])。"""
    n = len(closes)
    out: List[Optional[float]] = [None] * n
    for i in range(1, n):
        h = float(highs[i]); l = float(lows[i]); pc = float(closes[i - 1])
        out[i] = max(h, pc) - min(l, pc)
    return out


def atr_wilder(highs: Sequence[Number], lows: Sequence[Number],
               closes: Sequence[Number], period: int) -> List[Optional[float]]:
    """MT4 iATR 語義嘅 ATR 序列（與 closes 對齊，index<=period 前為 None）。"""
    if period < 1:
        raise ValueError("period 必須 >= 1")
    n = len(closes)
    out: List[Optional[float]] = [None] * n
    if n <= period:
        return out
    trs = true_ranges(highs, lows, closes)
    s = 0.0
    for i in range(1, period + 1):
        s += float(trs[i])
    atr = s / period
    out[period] = atr
    for i in range(period + 1, n):
        atr = (atr * (period - 1) + float(trs[i])) / period
        out[i] = atr
    return out
