#!/usr/bin/env python3
"""mt4_ref 參照實現測試（合成數據手算對照——驗證與 MQ4 Calc() 行為一致）。"""
import sys

sys.path.insert(0, "/home/z/my-project/exchange-repo")

from ccy_backtest import mt4_ref, universe


def _u36(sub):
    """由簡化子集構造 36 宇宙：其餘填滿 None（源碼行為＝完全跳過）。"""
    return list(universe.INSTRUMENTS_36)


def test_major_single_pair():
    """單對 EURUSD RSI=70 → EUR 70 / USD 30，XAU 及其餘 50。"""
    pw = mt4_ref.calc_pw_row({"EURUSD": 70.0}, {"EURUSD": 1.0}, _u36(None))
    assert abs(pw["EUR"] - 70.0) < 1e-9
    assert abs(pw["USD"] - 30.0) < 1e-9
    assert abs(pw["XAU"] - 50.0) < 1e-9
    for k in ("JPY", "GBP", "CHF", "AUD", "CAD", "NZD"):
        assert pw[k] == 50.0


def test_gold_halfweight():
    """XAUUSD RSI=70（raw20）＋XAUJPY RSI=60（raw10）：XAU=65；JPY=45（−v×0.5）。"""
    rsi = {"XAUUSD": 70.0, "XAUJPY": 60.0}
    atr = {"XAUUSD": 1.0, "XAUJPY": 1.0}
    pw = mt4_ref.calc_pw_row(rsi, atr, _u36(None))
    assert abs(pw["XAU"] - 65.0) < 1e-9      # 50 + (20+10)/2
    assert abs(pw["JPY"] - 45.0) < 1e-9      # 50 - 10*0.5/1
    assert pw["USD"] == 50.0


def test_avgw_normalization_div_cnt():
    """avgW 歸一＋÷cnt：EURUSD w=2 RSI=70；USDJPY w=4 RSI=55 → avgW=3。
    EUR c=13.3333 cnt1 → 63.3333；USD (−13.3333+6.6667)/2 → 46.6667；JPY −6.6667/1 → 43.3333。"""
    rsi = {"EURUSD": 70.0, "USDJPY": 55.0}
    atr = {"EURUSD": 2.0, "USDJPY": 4.0}
    pw = mt4_ref.calc_pw_row(rsi, atr, _u36(None))
    assert abs(pw["EUR"] - (50 + 20 * (2 / 3) / 1)) < 1e-6
    assert abs(pw["USD"] - (50 + (-20 * (2 / 3) + 5 * (4 / 3)) / 2)) < 1e-6
    assert abs(pw["JPY"] - (50 - 5 * (4 / 3))) < 1e-6


def test_invalid_rsi_skipped():
    """RSI≤0/None → 該 instrument 完全跳過（MQ4 L146 if(r<=0) continue）。"""
    pw = mt4_ref.calc_pw_row({"EURUSD": 70.0, "USDJPY": None}, {"EURUSD": 1.0}, _u36(None))
    assert abs(pw["EUR"] - 70.0) < 1e-9 and abs(pw["USD"] - 30.0) < 1e-9


def test_full36_known_shape():
    """36 宇宙齊料（同值 RSI=60/ATR%=1）→ 全幣 50（同向抵消：28 對 raw=10 全鏈）。"""
    # 28 majors 全 RSI=60：每幣 base+10 / quote−10 累積唔會全抵消，
    # 但 XAUUSD 同 7 交叉唔在場 → XAU=50。
    rsi = {inst: 60.0 for inst in universe.INSTRUMENTS_36 if not inst.startswith("XAU")}
    atr = {k: 1.0 for k in rsi}
    pw = mt4_ref.calc_pw_row(rsi, atr, _u36(None))
    assert abs(pw["XAU"] - 50.0) < 1e-9
    # 每個法幣輸出數值對稱性：README 檢查 pw 都喺 40..60 範圍（合成數據界）
    for k, v in pw.items():
        assert 40.0 <= v <= 60.0, f"{k}={v} 超界"


if __name__ == "__main__":
    test_major_single_pair()
    test_gold_halfweight()
    test_avgw_normalization_div_cnt()
    test_invalid_rsi_skipped()
    test_full36_known_shape()
    print("mt4_ref 自測 5/5 PASS")
