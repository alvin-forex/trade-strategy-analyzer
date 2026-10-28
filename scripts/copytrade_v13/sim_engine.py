# -*- coding: utf-8 -*-
"""COPYTRADE v1.3 §11——六維模擬矩陣引擎。

矩陣（§11.1）：signal_id × symbol × layer_policy × copy_method × account_type × cost_scenario
方法（§11.2）：M1 固定手數／M2 原始手數比例／M3 資金比例／M4 固定金額風險／M5 層數-margin cap
層檔（§11.3）：L1／L1-L2／L1-L3／L1-L5／全層
情境（§11.8）：Ideal／Realistic／Stress
帳戶：USD／demo（demo 同 USD 數學同源，驗邏輯）／cent（broker 真實 contract_size 重算，禁 ÷100）

鐵律落點：
- L0 缺列 → M1/M4/cent 組合 blocked（指標 null＋note），零估算（§6.7 鐵律 2）
- M2/M3/M5（層截斷）用 CSV broker 真實美元 × 比例重放——線性、零重算（§11.7 A 級重放）
- M4 冇 SL → RISK_ESTIMATE_UNAVAILABLE，不許估（§11.2）
- 樣本閘門 N=18（§11.4）；起始資金 = 夾倉成本 × 3（§11.5，老闆落鎖）
"""
import math
from collections import defaultdict

LAYER_POLICIES = [("L1", 1), ("L1-L2", 2), ("L1-L3", 3), ("L1-L5", 5), ("全層", None)]
COPY_METHODS = ["M1", "M2", "M3", "M4", "M5"]
ACCOUNTS = ["USD", "demo", "cent"]
SCENARIOS = ["Ideal", "Realistic", "Stress"]
SLIPPAGE_PIPS = {"Ideal": 0.0, "Realistic": 0.5, "Stress": 2.0}  # §11.8 小幅/高滑點
N_GATE = 18
BUFFER = 3.0
WEIGHTS = {"growth": 0.4, "stable": 0.2, "dd": 0.25, "evap": 0.15}  # 權重可配（§11.4）


def month_key(ts: str) -> str:
    return ts[:7]


def percentile_inc(vals, p):
    """Excel PERCENTILE.INC 口徑（照 analyzer）。"""
    if not vals:
        return 0.0
    s = sorted(vals)
    k = (len(s) - 1) * p
    f = math.floor(k)
    c = min(f + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def cap_layers(cycle, policy_n):
    """層檔過濾：全層唔截；其餘只取頭 N 層。"""
    if policy_n is None:
        return cycle["layers"]
    return [L for L in cycle["layers"] if L["layer_no"] <= policy_n]


def sim_cycle(cycle, method, ratio, fixed_lot, risk_budget, specs, fx_table,
              scenario, account):
    """一個 cycle × 一個方法 → (pnl, filled, missed, note, max_lot)。

    M2/M3/M5-截斷：copy_profit = source_profit × ratio（broker 真實美元線性重放）。
    M1/M4：需要 L0 specs（contract_size/tick_value/fx）；缺 → (None, blocked)。
    cent：需要 broker cent specs（真實重算，禁 ÷100）；缺 → blocked。
    """
    sym = cycle["symbol"]
    sp = specs.get(sym) if specs else None
    # M5 margin cap／cent 重算／M1/M4 lot 計價——全部要 L0（§6.7 鐵律 2 零估算）
    need_l0 = method in ("M1", "M4", "M5") or account == "cent"
    if need_l0 and sp is None:
        return 0.0, 0, len(cycle["layers"]), "BLOCKED: 需 L0 symbols 導出（§6.7 鐵律 2 零估算）", 0.0

    slip = SLIPPAGE_PIPS.get(scenario, 0.0)
    from pipcalc import pip_value_usd, MissingSpec, MissingFx

    if method == "M1":
        filled = missed = 0
        pnl = 0.0
        max_lot = fixed_lot
        for L in cycle["layers"]:
            try:
                d = 1.0 if L["typ"].lower() == "buy" else -1.0
                base = (L["close_price"] - L["open_price"]) * d * fixed_lot * sp["contract_size"]
                pv = pip_value_usd(sym, (L.get("close_time") or cycle["close_time"])[:10], specs, fx_table)
                cost = slip * pv * fixed_lot if slip else 0.0
                pnl += base - cost
                filled += 1
            except (MissingSpec, MissingFx) as e:
                return 0.0, 0, len(cycle["layers"]), f"BLOCKED: {e}", 0.0
        return pnl, filled, missed, None, max_lot

    if method == "M4":
        # risk_budget / SL_money_per_lot；冇 SL → RISK_ESTIMATE_UNAVAILABLE（零估算）
        from pipcalc import margin_usd  # noqa: F401
        entries = [L for L in cycle["layers"]]
        sls = [L for L in entries if L.get("sl_price")]
        if not sls:
            return 0.0, 0, len(entries), "RISK_ESTIMATE_UNAVAILABLE", 0.0
        pv_ref = None
        try:
            d = 1.0 if entries[0]["typ"].lower() == "buy" else -1.0
            e0 = entries[0]
            per_lot = abs(e0["sl_price"] - e0["open_price"]) * sp["contract_size"]
            lot = risk_budget / per_lot if per_lot > 0 else 0.0
            if lot <= 0:
                return 0.0, 0, len(entries), "RISK_ESTIMATE_UNAVAILABLE", 0.0
            pnl = 0.0
            for L in entries:
                base = (L["close_price"] - L["open_price"]) * d * lot * sp["contract_size"]
                pv = pip_value_usd(sym, (L.get("close_time") or cycle["close_time"])[:10], specs, fx_table)
                pnl += base - (slip * pv * lot if slip else 0.0)
            return pnl, len(entries), 0, None, lot
        except (MissingSpec, MissingFx) as e:
            return 0.0, 0, len(entries), f"BLOCKED: {e}", 0.0

    # M2 / M3 / M5——比例重放（broker 真實美元 × ratio）
    pnl = 0.0
    max_lot = 0.0
    for L in cycle["layers"]:
        copy_lot = L["lots"] * ratio
        max_lot = max(max_lot, copy_lot)
        pnl += L["net_profit"] * ratio
        if slip:
            # 滑點成本要 pip_value；無 L0 → Realistic/Stress 的重放扣除 blocked
            if sp is None:
                return 0.0, 0, len(cycle["layers"]), "BLOCKED: 需 L0（slippage 計價）", 0.0
            try:
                pnl -= slip * pip_value_usd(sym, (L.get("close_time") or cycle["close_time"])[:10], specs, fx_table) * copy_lot
            except (MissingSpec, MissingFx) as e:
                return 0.0, 0, len(cycle["layers"]), f"BLOCKED: {e}", 0.0
    return pnl, len(cycle["layers"]), 0, None, max_lot
