# -*- coding: utf-8 -*-
"""COPYTRADE v1.3 §6 核心計算定義——唯一計錢層（L1）。

鐵律（§6.7）：
1. 本模組係全系統唯一計 pip_value／margin 嘅地方，下游不准重算。
2. 寧可空白，不可估算——缺 symbols 列 raise MissingSpec，缺當日 fx raise MissingFx。
3. SQLite 先行：全部產出落 §5.1 九張表。
"""
import sqlite3
from typing import Dict, Optional


class MissingSpec(Exception):
    """L0 symbols 缺列——不准估算（§6.1 歷史教訓 #1/#2）。"""


class MissingFx(Exception):
    """缺當日 fx——不准用最近值頂（§6.2）。"""


def pip_size(sym: str, specs: Dict) -> float:
    """§6.1：pip_size 由 L0 導出，程式判斷即缺陷；全系統禁止 pip 常數表。"""
    sp = specs.get(sym)
    if sp is None:
        raise MissingSpec(f"symbols 缺列: {sym}（不准估算）")
    if sp["pip_size"] <= 0:
        raise MissingSpec(f"{sym} pip_size 非正數，L0 導出有錯")
    return sp["pip_size"]


def fx_at(sym: str, date: str, specs: Dict, fx_table: Optional[Dict]) -> float:
    """§6.2 方向鎖死：fx ≡ 1 單位報價幣兌 X USD（fx(JPY)≈0.00667）。USD 報價恆 1。"""
    sp = specs.get(sym)
    if sp is None:
        raise MissingSpec(f"symbols 缺列: {sym}")
    if sp["quote_currency"] == "USD":
        return 1.0
    if not fx_table:
        raise MissingFx(f"{sym} 非 USD 報價但無 fx 表（§6.2 不准用最近值頂）")
    rec = fx_table.get((sym, date))
    if rec is None:
        raise MissingFx(f"缺 {sym} 於 {date} 之 fx——raise 不估算")
    return rec


def pip_value_usd(sym: str, date: str, specs: Dict, fx_table: Optional[Dict] = None) -> float:
    """§6.2 權威式：tick_value × (pip_size / tick_size)，非 USD 報價按日修正匯率成分。

    sanity band 0.5–2.0：真漂移最惡 38%/月，2 倍即方向反轉（§6.2）。
    """
    sp = specs.get(sym)
    if sp is None:
        raise MissingSpec(f"symbols 缺列: {sym}（不准估算）")
    pv_ref = sp["tick_value"] * (sp["pip_size"] / sp["tick_size"])
    if sp["quote_currency"] == "USD":
        return pv_ref  # USD 報價恆定不修正（實測漂移 0–6% 屬噪音）
    r_ref = sp.get("fx_at_export")
    if not r_ref:
        raise MissingFx(f"{sym} L0 缺 fx_at_export（導出當日匯率）")
    r_now = fx_at(sym, date, specs, fx_table)
    pv = pv_ref * (r_now / r_ref)
    if not (0.5 <= pv / pv_ref <= 2.0):
        raise MissingFx(f"{sym} {date} fx 修正超出 sanity band（0.5–2.0），方向可能反轉")
    return pv


def verify_trade(t: dict, specs: Dict, fx_table: Optional[Dict] = None) -> tuple:
    """§6.3 兩式交叉驗證——全鏈品質閘門，每筆都跑不抽樣。

    式 A（價差式，對 pip 慣例免疫）：
        profit_usd = (close − open) × direction × lots × contract_size
    式 B（pips 式，依賴 6.1＋6.2 全鏈）：
        profit_usd = net_pips × pip_value_usd × lots
    兩式偏差 > 0.01 USD → qc_flag='SUSPECT'，不參與統計。
    回傳 (profit_usd_式A, qc_flag)。
    """
    sp = specs.get(t["symbol"])
    if sp is None:
        raise MissingSpec(f"symbols 缺列: {t['symbol']}")
    direction = 1.0 if t["typ"].lower() == "buy" else -1.0
    a = (t["close_price"] - t["open_price"]) * direction * t["lots"] * sp["contract_size"]
    b = t["net_pips"] * pip_value_usd(t["symbol"], t["close_time"][:10], specs, fx_table) * t["lots"]
    flag = "SUSPECT" if abs(a - b) > 0.01 else None
    return a, flag


def margin_usd(sym: str, date: str, lots: float, specs: Dict, fx_table: Optional[Dict] = None,
               price: Optional[float] = None, leverage: int = 500) -> float:
    """§6.4：lots × contract_size × price × fx(quote) ÷ leverage；leverage 可配置預設 500。

    JPY 交叉盤漏乘 fx 係 ~150 倍級錯誤——本函數一律乘 fx。
    """
    sp = specs.get(sym)
    if sp is None:
        raise MissingSpec(f"symbols 缺列: {sym}")
    if price is None:
        raise MissingSpec(f"{sym} 缺 price（§6.4 不准用最近值頂）")
    fx = fx_at(sym, date, specs, fx_table)
    return lots * sp["contract_size"] * price * fx / leverage


def breach_layer(layers: list, equity: float, specs: Dict, fx_table=None,
                 price_fn=None, maintain_ratio: float = 0.5, leverage: int = 500):
    """§6.5 爆倉層級警戒線。浮虧以正數表示蝕錢（符號鎖死）。

    layers: [{open_time, open_price, lots, direction}]（時間序）
    回傳第 N 層觸發（1-based）或 None。
    """
    margin_cum = 0.0
    for N, layer in enumerate(layers, start=1):
        sym = layers[0]["symbol"]
        date = layer["open_time"][:10]
        margin_cum += margin_usd(sym, date, layer["lots"], specs, fx_table,
                                 price=layer["open_price"], leverage=leverage)
        price_n = price_fn(layers[0]["symbol"], layer["open_time"]) if price_fn else layer["open_price"]
        float_loss = sum(
            (li["open_price"] - price_n) * (1.0 if li["direction"].lower() == "buy" else -1.0)
            * li["lots"] * specs[sym]["contract_size"] * fx_at(sym, li["open_time"][:10], specs, fx_table)
            for li in layers[:N]
        )
        if equity - float_loss < margin_cum * maintain_ratio:
            return N
    return None
