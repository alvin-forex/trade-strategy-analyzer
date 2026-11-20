#!/usr/bin/env python3
"""dataio 測試：repo JSON loader＋通用 OHLC CSV loader＋parity 前置檢查。"""

import pytest

from ccy_backtest import dataio, parity


def test_load_repo_json_eurusd():
    bars = dataio.load_repo_json("EURUSD", "D1")
    assert len(bars["d"]) == len(bars["c"]) > 1000
    assert bars["d"][0] == "2018-11-08"
    assert bars["c"][-1] > 0


def test_load_repo_json_missing():
    with pytest.raises(FileNotFoundError):
        dataio.load_repo_json("XAUGBP", "D1")  # docs/data 未有呢條交叉


def test_load_ohlc_csv(tmp_path):
    p = tmp_path / "ohlc.csv"
    p.write_text(
        "timestamp,open,high,low,close\n"
        "2026-01-02 00:00,100.0,101.0,99.0,100.5\n"
        "2026-01-03 00:00,100.5,102.0,100.0,101.5\n",
        encoding="utf-8")
    b = dataio.load_ohlc_csv(str(p))
    assert b["d"] == ["2026-01-02 00:00", "2026-01-03 00:00"]
    assert b["c"] == [100.5, 101.5]


def test_load_ohlc_csv_three_col(tmp_path):
    """只有 timestamp,high,low,close（冇 open）→ open=close 填充。"""
    p = tmp_path / "ohlc3.csv"
    p.write_text("date,high,low,close\n2026-01-02,101.0,99.0,100.5\n",
                 encoding="utf-8")
    b = dataio.load_ohlc_csv(str(p))
    assert b["o"] == [100.5] and b["c"] == [100.5]


def test_parity_pending_when_no_reader(tmp_path):
    with pytest.raises(parity.ParityPendingError):
        parity.load_reader_csv(str(tmp_path / "not_exist.csv"))
