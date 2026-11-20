#!/usr/bin/env python3
"""9 貨幣 × 36 instruments 預設宇宙＋帶符號方向（CP-BT1）。

宇宙定義（assumption A-1，白皮書未到手前按派工信「9 貨幣分解引擎（36 instruments）」重建）：
  8 條法幣：EUR USD JPY GBP CHF AUD CAD NZD → C(8,2)=28 對
  黃金：XAU 對 8 條法幣 → 8 對（XAUUSD XAUEUR XAUGBP XAUJPY XAUCHF XAUAUD XAUCAD XAUNZD）
  合計 36。

注意：原作 FF 面板（Alpari）黃金交叉 G=5；v3.10 若白皮書定 G≠8，
到料後只改 GOLD_CROSSES（引擎不變）。docs/data/ 現只有 4 條 XAU 交叉
（XAUUSD XAUEUR XAUAUD XAUJPY），缺 4 條——引擎對缺料 instrument 自動
退出聚合（N_c 按在場 instrument 計），終端全量數據到料後自動補齊。

每個 instrument 有 base／quote；raw_p = RSI−50 以 base 為正方向：
  raw > 0 → base 強於 quote
  分解時 base 記 +raw*w，quote 記 −raw*w
"""

from __future__ import annotations

FIAT = ["EUR", "USD", "JPY", "GBP", "CHF", "AUD", "CAD", "NZD"]

# 28 條法幣對（字母序，與 docs/data/ 檔名一致）
FIAT_PAIRS = [
    "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD", "AUDUSD",
    "CADCHF", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD",
    "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD",
    "USDCAD", "USDCHF", "USDJPY",
]

# 8 條黃金交叉（assumption A-1；原作 Alpari G=5，白皮書到料後可調）
GOLD_CROSSES = ["XAUAUD", "XAUCAD", "XAUCHF", "XAUEUR", "XAUGBP",
                "XAUJPY", "XAUNZD", "XAUUSD"]

INSTRUMENTS_36 = FIAT_PAIRS + GOLD_CROSSES

CURRENCIES_9 = FIAT + ["XAU"]


def parse_instrument(name: str) -> tuple[str, str]:
    """拆 base/quote；XAU 開頭 → base=XAU。6 字母以外拋錯。"""
    n = name.strip().upper()
    if len(n) != 6:
        raise ValueError(f"非 6 字母 instrument：{name}")
    if n.startswith("XAU"):
        return "XAU", n[3:]
    base, quote = n[:3], n[3:]
    if base not in FIAT or quote not in FIAT:
        raise ValueError(f"宇宙外 instrument：{name}")
    return base, quote


def partners(currency: str, instruments=INSTRUMENTS_36) -> list[str]:
    """某貨幣嘅夥伴 instrument 列表（該幣有份嘅全部對）。"""
    c = currency.upper()
    out = []
    for inst in instruments:
        base, quote = parse_instrument(inst)
        if c == base or c == quote:
            out.append(inst)
    return out


def sign_of(currency: str, instrument: str) -> int:
    """currency 喺 instrument 入面嘅方向：base=+1，quote=−1，唔相干拋錯。"""
    base, quote = parse_instrument(instrument)
    c = currency.upper()
    if c == base:
        return +1
    if c == quote:
        return -1
    raise ValueError(f"{currency} 唔屬 {instrument}")


def validate_universe() -> None:
    """36 個 instrument、9 條幣、每條法幣 8 夥伴、XAU 8 夥伴；唔合格拋錯。"""
    if len(INSTRUMENTS_36) != 36:
        raise AssertionError(f"instruments 數 {len(INSTRUMENTS_36)} ≠ 36")
    seen = set()
    for inst in INSTRUMENTS_36:
        if inst in seen:
            raise AssertionError(f"重複 instrument：{inst}")
        seen.add(inst)
        parse_instrument(inst)
    for c in FIAT:
        ps = partners(c)
        if len(ps) != 8:
            raise AssertionError(f"{c} 夥伴數 {len(ps)} ≠ 8")
    if len(partners("XAU")) != 8:
        raise AssertionError("XAU 夥伴數 ≠ 8")
