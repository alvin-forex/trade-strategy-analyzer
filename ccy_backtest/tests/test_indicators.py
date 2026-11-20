#!/usr/bin/env python3
"""indicators 手算例測試——期望值全部展開算術逐步驗證（唔係實現重跑）。

MT4 語義錨點：
  RSI: avg_loss==0 → 100；否則 100 − 100/(1+g/l)（等價 100g/(g+l)）
  首值喺 index=period（頭 period 個變化簡單平均），之後 Wilder (prev*(N-1)+x)/N
  ATR: TR[i]=max(h,c[i-1])−min(l,c[i-1])；首值=SMA(頭 period 個 TR)，之後 Wilder
"""

import pytest

from ccy_backtest.indicators import atr_wilder, rsi_wilder


def test_rsi_period1_direction():
    """period=1：每 bar 即時值——升 bar RSI=100、跌 bar RSI=0（hand: g=ch, l=0→100；g=0→0）。"""
    closes = [10.0, 11.0, 10.0, 12.0]
    r = rsi_wilder(closes, 1)
    assert r[0] is None
    # ch1=+1 → g=1,l=0 → 100
    assert r[1] == pytest.approx(100.0)
    # ch2=−1 → Wilder(period1): g=(1*0+0)/1=0, l=(0*0+1)/1=1 → 100−100/(1+0)=0
    assert r[2] == pytest.approx(0.0)
    # ch3=+2 → g=2,l=0 → 100
    assert r[3] == pytest.approx(100.0)


def test_rsi_period2_hand_unrolled():
    """closes=[10,11,9.5,10.5]，period=2，期望逐步手算：

    ch1=+1（g=1,l=0）；ch2=−1.5（g=0,l=1.5）
    index2（首值）：g=(1+0)/2=0.5，l=(0+1.5)/2=0.75
      RSI=100−100/(1+0.5/0.75)=100−100/(1.666667)=100−60=40
    index3（Wilder）：g=(0.5×1+1)/2=0.75，l=(0.75×1+0)/2=0.375
      RSI=100−100/(1+0.75/0.375)=100−100/3=66.666667
    """
    closes = [10.0, 11.0, 9.5, 10.5]
    r = rsi_wilder(closes, 2)
    assert r[0] is None and r[1] is None
    assert r[2] == pytest.approx(40.0)
    assert r[3] == pytest.approx(66.6666667, abs=1e-6)


def test_rsi_all_flat_is_100_mt4_semantics():
    """全平盤：g=l=0 → MT4 negative==0 → 100（唔係 nan，照抄行為）。"""
    r = rsi_wilder([5.0, 5.0, 5.0, 5.0], 2)
    assert r[2] == 100.0 and r[3] == 100.0


def test_rsi_all_up_is_100():
    r = rsi_wilder([1.0, 2.0, 3.0, 4.0], 2)
    assert r[2] == 100.0 and r[3] == 100.0


def test_rsi_short_series_returns_all_none():
    assert rsi_wilder([1.0, 2.0], 3) == [None, None]


def test_atr_period2_hand_unrolled():
    """h=[10,11,12], l=[9,10,11], c=[10.5,10.5,11.5]，period=2：

    TR1 = max(11,10.5)−min(10,10.5) = 11−10 = 1.0
    TR2 = max(12,10.5)−min(11,10.5) = 12−10.5 = 1.5
    ATR[2] = (1.0+1.5)/2 = 1.25
    """
    a = atr_wilder([10, 11, 12], [9, 10, 11], [10.5, 10.5, 11.5], 2)
    assert a[0] is None and a[1] is None
    assert a[2] == pytest.approx(1.25)


def test_atr_period3_hand_unrolled():
    """period=3，6 bars：

    TR1=1.0（idx1: max(11,10.5)−min(10,10.5)）
    TR2=1.5（idx2: max(12,10.5)−min(11,10.5)）
    TR3=1.5（idx3: max(11,11.5)−min(10,11.5)）
    ATR[3] = (1.0+1.5+1.5)/3 = 4/3
    TR4 = 1.2（idx4: max(12,10.8)−min(11,10.8)＝前收10.8）
    ATR[4] = (4/3×2+1.2)/3 = 58/45 = 1.2888889
    TR5 = 1.3（idx5: max(12.5,11.2)−min(11.3,11.2)=12.5−11.2，min 取前收 11.2）
    ATR[5] = (58/45×2+1.3)/3 = 349/270 = 1.2925926
    """
    a = atr_wilder([10, 11, 12, 11, 12, 12.5], [9, 10, 11, 10, 11, 11.3],
                   [10.5, 10.5, 11.5, 10.8, 11.2, 11.9], 3)
    assert a[3] == pytest.approx(4.0 / 3.0, abs=1e-12)
    assert a[4] == pytest.approx(58.0 / 45.0, abs=1e-12)
    assert a[5] == pytest.approx(349.0 / 270.0, abs=1e-12)
