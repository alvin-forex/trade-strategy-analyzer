#!/usr/bin/env python3
"""universe / core / series 手算例測試（CP-BT1 階段 A）。"""

import pytest

from ccy_backtest import core, series, universe


def test_universe_36_instruments_9_currencies():
    """36 instruments＝28 法幣對＋8 XAU 交叉；9 幣；每幣 8 夥伴（36=9×8÷2×… 對帳）。"""
    universe.validate_universe()
    assert len(universe.INSTRUMENTS_36) == 36
    assert len(universe.CURRENCIES_9) == 9
    # 對帳：Σ partners = 2×36 = 72；9 幣 × 8 夥伴 = 72 ✓
    total = sum(len(universe.partners(c)) for c in universe.CURRENCIES_9)
    assert total == 72


def test_parse_and_sign():
    assert universe.parse_instrument("EURUSD") == ("EUR", "USD")
    assert universe.parse_instrument("XAUJPY") == ("XAU", "JPY")
    assert universe.sign_of("EUR", "EURUSD") == 1
    assert universe.sign_of("USD", "EURUSD") == -1
    assert universe.sign_of("XAU", "XAUJPY") == 1
    with pytest.raises(ValueError):
        universe.parse_instrument("FRA40")


def test_aggregate_currency_zero_guard():
    """den=0 或 n=0 → None（防除零）。"""
    assert core.aggregate_currency(10.0, 0.0, 2) is None
    assert core.aggregate_currency(10.0, 2.0, 0) is None
    assert core.aggregate_currency(100.0, 2.0, 2) == pytest.approx(50.0)


def test_engine_hand_calc_two_pairs():
    """合成兩對手算（raw 由 RSI(period=1) 釘死，兩對同價格 → 同 w）：

    A=EURUSD：c=[100,101] 升 → index1 RSI=100 → raw=+50
    B=USDJPY：c=[100,101] 升 → index1 RSI=100 → raw=+50
    h=c+0.5、l=c−0.5 → TR1=max(101.5,100)−min(100.5,100)=1.0 → ATR=1.0
    w=1.0/101×100=0.990099（兩對相同）
    分解（index1）：
      EUR = +50w/w = +50
      USD = (−50+50)w/(2w) = 0
      JPY = −50
      其餘 6 幣無在場對 → None
      avg = (50+0−50)/3 = 0
      n_partners：EUR=1 USD=2 JPY=1
    index0（warmup）：coverage=0，全部 None。
    """
    n = 2
    d = [f"d{i}" for i in range(n)]
    mk = lambda c: {"d": d, "o": c, "h": [x + 0.5 for x in c],
                    "l": [x - 0.5 for x in c], "c": c}
    data = {"EURUSD": mk([100.0, 101.0]), "USDJPY": mk([100.0, 101.0])}
    rows = core.compute_power_history(data, "D1", rsi_period=1, atr_period=1)
    assert len(rows) == 2
    w0 = rows[0]
    assert w0["coverage"] == 0
    assert w0["power"]["EUR"] is None and w0["avg"] is None
    r1 = rows[1]
    assert r1["coverage"] == 2
    assert r1["power"]["EUR"] == pytest.approx(50.0)
    assert r1["power"]["USD"] == pytest.approx(0.0, abs=1e-12)
    assert r1["power"]["JPY"] == pytest.approx(-50.0)
    assert r1["power"]["GBP"] is None
    assert r1["avg"] == pytest.approx(0.0, abs=1e-12)
    assert r1["n_partners"]["EUR"] == 1 and r1["n_partners"]["USD"] == 2


def test_engine_missing_instrument_excluded():
    """A-6：缺料 instrument（XAU 交叉只有 4 條）退出聚合，N_c 按在場計。"""
    d = ["d0", "d1"]
    data = {"XAUUSD": {"d": d, "o": [2000.0, 2001.0],
                       "h": [2000.5, 2001.5], "l": [1999.5, 2000.5],
                       "c": [2000.0, 2001.0]}}
    rows = core.compute_power_history(data, "D1", rsi_period=1, atr_period=1)
    r1 = rows[1]
    assert r1["n_partners"]["XAU"] == 1
    assert r1["n_partners"]["USD"] == 1
    assert r1["power"]["GBP"] is None


def test_series_roundtrip(tmp_path):
    """writer→reader roundtrip：欄序 timestamp,tf,9幣,avg；None↔空字串。"""
    rows = [{"ts": "2026-04-17", "tf": "D1",
             "power": {"EUR": -3.123456, "USD": 1.0, "JPY": None, "GBP": 0.5,
                       "CHF": 0.25, "AUD": -0.125, "CAD": 0.0625, "NZD": 0.03125,
                       "XAU": 2.5},
             "avg": 0.11640625, "n_partners": {}, "coverage": 36}]
    out = str(tmp_path / "cp.csv")
    series.write_cp_power_history(rows, out)
    back = series.read_cp_power_history(out)
    assert back[0]["ts"] == "2026-04-17" and back[0]["tf"] == "D1"
    assert back[0]["power"]["EUR"] == pytest.approx(-3.123456)
    assert back[0]["power"]["JPY"] is None
    assert back[0]["avg"] == pytest.approx(0.116406, abs=1e-6)  # writer %.6f 格式
    with open(out, encoding="utf-8") as f:
        header = f.readline().strip()
    assert header == series.HEADER_CSV
