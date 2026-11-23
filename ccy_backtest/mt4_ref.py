#!/usr/bin/env python3
"""MT4 v3.07-MQ4 參照實現（逐行移植自 CurrencyPower_v3_MQ4.mq4 Calc()／OnCalculate()）。

依據：audit zip MT4/CurrencyPower_v3_MQ4.mq4（395 行，v3.07 2026-09-26）＋
白皮書 §3.1–3.4（內容與源碼一致）。行為基準：已知缺陷照抄唔准修正（parity 優先）。

與 ccy_backtest.core（階段 A 假設版）的差異（以本檔為準）：
  - 聚合唔係 ÷Σw，係 ÷cnt（簡單平均，MQ4 L158/L165/L181）
  - 權重歸一 w/avgW（avgW=全宇宙有效 ATR% 平均，MQ4 L150-153）
  - RSI≤0 → 該 instrument 該 bar 完全跳過（MQ4 L146）
  - ATR%≤0（a<=0 或 px<=0 → 0）→ 跳過（MQ4 L138-142）
  - majors 段每對 += / -= 後即時更新 pw[k]=50+c[k]/cnt[k]（僅 k=1..8）
  - XAUUSD：gx += raw×w'；gn++（w>0）
  - 7 條 gold 交叉：gx += raw×w'；gn++；c[Q] -= v×0.5；cnt[Q]++；
    pw[Q] 即時重算（半權重 A2 缺陷——照抄）
  - pw[XAU] = 50 + gx/gn（gn>0；否則 50）
  - 該 bar 起始 pw 全部初始化 50.0（MQ4 L350 ArrayInitialize(pw,50.0)）
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence

from . import universe

CCY9_MQ4 = ["XAU", "USD", "EUR", "JPY", "GBP", "AUD", "CAD", "CHF", "NZD"]
MAJOR_PAIRS = [(b, q) for b, q in (
    ("EUR", "USD"), ("GBP", "USD"), ("AUD", "USD"), ("NZD", "USD"),
    ("USD", "JPY"), ("USD", "CHF"), ("USD", "CAD"),
    ("EUR", "GBP"), ("EUR", "JPY"), ("EUR", "CHF"), ("EUR", "AUD"), ("EUR", "CAD"), ("EUR", "NZD"),
    ("GBP", "JPY"), ("GBP", "CHF"), ("GBP", "AUD"), ("GBP", "CAD"), ("GBP", "NZD"),
    ("AUD", "JPY"), ("AUD", "CHF"), ("AUD", "CAD"), ("AUD", "NZD"),
    ("NZD", "JPY"), ("NZD", "CHF"), ("NZD", "CAD"),
    ("CAD", "JPY"), ("CAD", "CHF"), ("CHF", "JPY"))]
GOLD_Q = ["EUR", "GBP", "AUD", "JPY", "CHF", "CAD", "NZD"]


def calc_pw_row(rsi: Dict[str, Optional[float]],
                atrpct: Dict[str, Optional[float]],
                universe_36: Sequence[str] = None) -> Dict[str, float]:
    """單 bar pw 計算（照 MQ4 Calc(int sh, double &pw[]) 逐行）。

    rsi：{instrument: RSI 值或 None}（MT4 iRSI(...,sh) 對應；≤0/None=無效）
    atrpct：{instrument: ATR% 值或 None}（iATR/close×100；≤0/None=無效）
    回傳 {幣: pw（50 中心）}——9 幣全有（無效則 50.0，照 ArrayInitialize）。
    """
    if universe_36 is None:
        universe_36 = list(universe.INSTRUMENTS_36)

    # MQ4 L141-155：全 36 instrument 計 raw/w
    raw: Dict[str, float] = {}
    w: Dict[str, float] = {}
    sum_w = 0.0
    n_w = 0
    for inst in universe_36:
        raw[inst] = 0.0
        w[inst] = 0.0
        r = rsi.get(inst)
        if r is None or r <= 0:
            continue
        raw[inst] = r - 50.0
        wp = atrpct.get(inst)
        if wp is None or wp <= 0:
            continue
        w[inst] = wp
        sum_w += wp
        n_w += 1

    avg_w = sum_w / n_w if n_w > 0 else 1.0
    if avg_w <= 0:
        avg_w = 1.0

    # c[9]/cnt[9] 初始化（照 ArrayInitialize）
    c = {k: 0.0 for k in CCY9_MQ4}
    cnt = {k: 0 for k in CCY9_MQ4}
    pw = {k: 50.0 for k in CCY9_MQ4}

    # MQ4 L157-166：28 majors
    def ok(inst):
        return inst in universe_36 and w.get(inst, 0.0) > 0

    for base, quote in MAJOR_PAIRS:
        inst = f"{base}{quote}"
        if not ok(inst):
            continue
        v = raw[inst] * (w[inst] / avg_w)
        if base in c:
            c[base] += v
            cnt[base] += 1
        if quote in c:
            c[quote] -= v
            cnt[quote] += 1
        # pw[k] 即時更新（最終與 batch 一致；k 不含 XAU）
        pw[base] = 50.0 + (c[base] / cnt[base] if cnt[base] > 0 else 0.0)
        pw[quote] = 50.0 + (c[quote] / cnt[quote] if cnt[quote] > 0 else 0.0)

    # MQ4 L168-181：XAUUSD ＋ 7 gold 交叉
    gx = 0.0
    gn = 0
    xu = "XAUUSD"
    if ok(xu):
        gx += raw[xu] * (w[xu] / avg_w)
        gn += 1
    for q in GOLD_Q:
        inst = f"XAU{q}"
        if not ok(inst):
            continue
        v = raw[inst] * (w[inst] / avg_w)
        gx += v
        gn += 1
        if q in c:
            c[q] -= v * 0.5
            cnt[q] += 1
            pw[q] = 50.0 + c[q] / cnt[q]

    pw["XAU"] = 50.0 + gx / gn if gn > 0 else 50.0
    return pw
