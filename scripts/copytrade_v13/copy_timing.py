# -*- coding: utf-8 -*-
"""COPYTRADE v1.3 D2——Copy 時機模擬（v1.2 copy_trade_sim.py 改造移植）。

來源：src/copy_trade_sim.py v1.2（449 行，OpenClaw 2026-10-29 05:29 交付副本
`exchange/from_openclaw/20261029_0529_…/copy_trade_sim_v1.2.py`）。
「改造唔重寫」（老闆已批，SPEC §9 決策 4）：邏輯函數全保留，pip 計算換權威鏈。

改造對照表（v1.2 → 本檔）：
| v1.2 原函數 | 處置 | SPEC 依據 |
|---|---|---|
| `_get_pip_size()`（JPY/XAU/XAG/IDX 硬編碼表） | **整個刪除，改 `pipcalc.pip_size()`** | §6.1：pip_size 由 L0 導出，程式內零常數表 |
| `_estimate_pip_value()`（endswith('USD')→10.0——BTCUSD 1000 倍錯誤來源） | **整個刪除，改 `pipcalc.pip_value_usd()`** | §6.2 改造注意（原文命令刪除）；§6.7 鐵律 1 |
| `_calc_pips(entry, exit, direction, pip_size)` | 保留（純數學，pip_size 參數化） | — |
| `_simulate_delayed_entry()` M5 bar 掃描 | 保留語義（MISSED 記錄唔當 0 利潤；出口＝cycle close） | §5.2 copy_sims.outcome |
| `simulate_copy_trade()` 網格 [5,10,15,20]/[10,15,20,25]＋24h 窗口 | 保留 | — |
| pandas m5_data 依賴 | 改 list[dict]（OHLC v2 新契約 bar） | 模組零第三方依賴 |

PnL 口徑（FILLED 時）＝式 A＋滑點（§6.3/§11.8）：
    sim_pnl_usd = (cycle_close − sim_entry) × direction × lots × contract_size
                  − slip_pips × pip_value_usd × lots
MISSED → sim_pnl_usd = None（§5.2：MISSED 必須記錄，不能當 0 利潤）。

鐵律（§6.7）：
- 缺 L0 specs → BLOCKED 標注，零估算（鐵律 2）。
- 缺 M5 bars → NO_M5_DATA 標注（export_hst.py v2 --tf 5 導出後解鎖）。
"""
import json
import os
from datetime import datetime, timedelta

from pipcalc import pip_size, pip_value_usd, MissingSpec, MissingFx

# v1.2 原網格（保留）
DEFAULT_PROFIT_PIPS = [5, 10, 15, 20]
DEFAULT_LOSE_PIPS = [10, 15, 20, 25]
# §11.8 滑點（pip）——同 sim_engine.SLIPPAGE_PIPS 口徑
SLIPPAGE_PIPS = {"Ideal": 0.0, "Realistic": 0.5, "Stress": 2.0}


_TS_FMTS = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
            "%Y.%m.%d %H:%M", "%Y.%m.%d %H:%M:%S",
            "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S")


def parse_ts(s):
    """多格式時間解析（照 ingest._pt 口徑——D/M/YYYY 為 broker CSV 唯一先驗）。

    真 CSV cycle 嘅 open_time 係原始字串（ingest 只標準化 close_time）。
    """
    s = (s or "").strip()
    for fmt in _TS_FMTS:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return datetime.fromisoformat(s[:16])


def _iso_date(s):
    """任一格式時間字串 → YYYY-MM-DD（pip_value_usd 按日 fx 鍵）。"""
    return parse_ts(s).strftime("%Y-%m-%d")


def load_m5_json(path):
    """讀 export_hst.py v2 新契約 M5 JSON → [bar dict]（timestamp 升序）。

    契約：{updated, symbol, timeframe, source, start, end, count,
           bars: [{timestamp, open, high, low, close, volume, spread}]}
    timestamp＝ISO `YYYY-MM-DDTHH:MM`（MT4 server time）。
    """
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    bars = data.get("bars", [])
    bars.sort(key=lambda b: b["timestamp"])
    return bars


def _bar_ts(bar):
    return datetime.fromisoformat(bar["timestamp"])


def _cycle_close_price(cycle):
    """cycle 出口價＝最後一筆層平倉價（v1.2 語義：跟原 cycle 平倉動作）。"""
    closed = [L for L in cycle["layers"] if L.get("close_price")]
    if not closed:
        return None
    last = max(closed, key=lambda L: L.get("close_time") or "")
    return last["close_price"]


def _calc_pips(entry, exit_, direction, ps):
    """v1.2 原函數保留（pip_size 由 pipcalc.pip_size 傳入——L0 權威）。"""
    if str(direction).upper() == "BUY":
        return (exit_ - entry) / ps
    return (entry - exit_) / ps


def _scan_trigger(bars, target_price, is_buy, wait_pips, from_ts, window_h=24):
    """v1.2 `_simulate_delayed_entry` 掃描段——保留語義。

    BUY＋wait>0（等升到 target）：bar High >= target → FILLED
    BUY＋wait<0（等跌到 target）：bar Low  <= target → FILLED
    SELL 對稱反轉。窗口：entry 後 24h（v1.2 原行為）。
    回傳 (trigger_ts|None, bar_idx|None)。
    """
    end_ts = from_ts + timedelta(hours=window_h)
    for i, b in enumerate(bars):
        ts = _bar_ts(b)
        if ts < from_ts or ts > end_ts:
            continue
        if is_buy:
            if wait_pips > 0:
                if b["high"] >= target_price:
                    return ts, i
            else:
                if b["low"] <= target_price:
                    return ts, i
        else:
            if wait_pips > 0:
                if b["low"] <= target_price:
                    return ts, i
            else:
                if b["high"] >= target_price:
                    return ts, i
    return None, None


def simulate_copy_timing(cycle, m5_bars, specs, fx_table=None,
                         profit_pips=None, lose_pips=None, scenario="Ideal"):
    """v1.2 `simulate_copy_trade` 改造版——一個 cycle × wait 網格 → [result dict]。

    cycle：ingest.group_cycles / matrix._load_cycles 出嘅 dict（layers[0]＝L1）。
    m5_bars：`load_m5_json()` 出嘅 bar list；None／[] → 全行 NO_M5_DATA。
    specs／fx_table：L0 `symbols` 表（pipcalc 權威鏈）；缺 → 全行 BLOCKED（零估算）。

    每行：{sim_type, wait_pips, outcome(FILLED/MISSED/…), trigger_time,
           sim_entry_price, sim_exit_price, sim_pips, sim_pnl_usd,
           lots, holding_hours}
    """
    if profit_pips is None:
        profit_pips = DEFAULT_PROFIT_PIPS
    if lose_pips is None:
        lose_pips = DEFAULT_LOSE_PIPS
    specs = specs or {}  # None → {}：缺 L0 統一行 MissingSpec→BLOCKED（零估算）

    sym = cycle["symbol"]
    layers = cycle.get("layers") or []
    if not layers:
        return []
    l1 = layers[0]
    direction = cycle.get("direction") or l1.get("typ", "").upper()
    is_buy = str(direction).upper() == "BUY"
    entry_price = l1.get("open_price") or 0
    entry_time = l1.get("open_time")
    lots = l1.get("lots") or 0.0
    exit_price = _cycle_close_price(cycle)
    if not entry_price or not entry_time or exit_price is None:
        return []

    slip = SLIPPAGE_PIPS.get(scenario, 0.0)

    # —— L0 權威鏈（v1.2 違規函數至此退役）——
    try:
        ps = pip_size(sym, specs)                       # §6.1 讀表
        pv = pip_value_usd(sym, _iso_date(entry_time), specs, fx_table)  # §6.2 tick_value 權威
        sp = specs[sym]
        contract_size = sp["contract_size"]
    except (MissingSpec, MissingFx) as e:
        base = {"symbol": sym, "direction": direction, "entry_time": entry_time,
                "entry_price": entry_price, "exit_price": exit_price, "lots": lots,
                "trigger_time": None, "sim_entry_price": None,
                "sim_exit_price": None, "sim_pips": None, "sim_pnl_usd": None,
                "holding_hours": None}
        rows = [dict(base, sim_type="ACTUAL", wait_pips=0, outcome="BLOCKED",
                     sim_entry_price=None, sim_exit_price=None,
                     note=f"BLOCKED: {e}")]
        for w in profit_pips:
            rows.append(dict(base, sim_type="COPY_PROFIT", wait_pips=w,
                             outcome="BLOCKED",
                             note=f"BLOCKED: {e}"))
        for w in lose_pips:
            rows.append(dict(base, sim_type="COPY_LOSE", wait_pips=-w,
                             outcome="BLOCKED",
                             note=f"BLOCKED: {e}"))
        return rows

    from_ts = parse_ts(entry_time)

    def _one(sim_type, wait_pips):
        row = {"symbol": sym, "direction": direction, "entry_time": entry_time,
               "entry_price": entry_price, "exit_price": exit_price, "lots": lots,
               "sim_type": sim_type, "wait_pips": wait_pips, "note": None}
        if wait_pips == 0:
            # ACTUAL 基線：即刻跟 L1 入場（v1.2 baseline 語義）
            sim_entry = entry_price
            trigger_ts = from_ts
        else:
            if is_buy:
                target = entry_price + wait_pips * ps
            else:
                target = entry_price - wait_pips * ps
            sim_entry = target
            if not m5_bars:
                row.update(outcome="NO_M5_DATA", trigger_time=None,
                           sim_entry_price=None, sim_exit_price=None,
                           sim_pips=None, sim_pnl_usd=None, holding_hours=None,
                           note="NO_M5_DATA: wait 掃描需 M5 bars（export_hst.py --tf 5 導出）")
                return row
            trigger_ts, _ = _scan_trigger(m5_bars, target, is_buy, wait_pips, from_ts)
        if wait_pips != 0 and trigger_ts is None:
            # §5.2：MISSED 必須記錄，不能當 0 利潤
            row.update(outcome="MISSED", trigger_time=None,
                       sim_entry_price=None, sim_exit_price=None,
                       sim_pips=None, sim_pnl_usd=None, holding_hours=None)
            return row
        # FILLED——式 A（§6.3 價差式）＋滑點（§11.8）
        d = 1.0 if is_buy else -1.0
        pnl = (exit_price - sim_entry) * d * lots * contract_size
        if slip:
            pnl -= slip * pv * lots
        hold_h = None
        close_time = cycle.get("close_time")
        if trigger_ts and close_time:
            ct = parse_ts(close_time)
            hold_h = round((ct - trigger_ts).total_seconds() / 3600.0, 2)
        row.update(outcome="FILLED", trigger_time=trigger_ts.isoformat()[:16] if trigger_ts else None,
                   sim_entry_price=round(sim_entry, 6), sim_exit_price=exit_price,
                   sim_pips=round(_calc_pips(sim_entry, exit_price, direction, ps), 2),
                   sim_pnl_usd=round(pnl, 2), holding_hours=hold_h)
        return row

    rows = [_one("ACTUAL", 0)]
    for w in profit_pips:
        rows.append(_one("COPY_PROFIT", w))
    for w in lose_pips:
        rows.append(_one("COPY_LOSE", -w))
    return rows


def simulate_timing_all(cycles, specs, fx_table=None, m5_loader=None, scenario="Ideal"):
    """v1.2 `simulate_all_cycles` 對應——m5_loader(sym) → bar list|None。

    無 M5 數據嘅 symbol 照跑（wait=0 ACTUAL 行出，wait≠0 行標 NO_M5_DATA）——
    等 export_hst --tf 5 導出後重跑即解鎖（§6.7 鐵律 2：唔用最近值頂）。
    """
    out = []
    for cyc in cycles:
        bars = m5_loader(cyc["symbol"]) if m5_loader else None
        out.extend(simulate_copy_timing(cyc, bars or [], specs, fx_table,
                                        scenario=scenario))
    return out


def summarize_timing(rows):
    """v1.2 `generate_copy_trade_summary` 對應——wait 檔聚合（§5.2 fill_rate 必出）。"""
    by = {}
    for r in rows:
        if r.get("sim_type") == "ACTUAL" and r.get("wait_pips") == 0:
            continue  # 基線唔入掃描聚合（照 v1.2 只聚合 wait 檔）
        k = (r.get("symbol"), r.get("sim_type"), r.get("wait_pips"))
        by.setdefault(k, []).append(r)
    out = []
    for (sym, sim_type, w), rs in sorted(by.items(), key=lambda kv: (str(kv[0]))):
        total = len(rs)
        filled = [r for r in rs if r.get("outcome") == "FILLED"]
        missed = [r for r in rs if r.get("outcome") == "MISSED"]
        blocked = [r for r in rs if r.get("outcome") in ("BLOCKED", "NO_M5_DATA")]
        pnls = [r["sim_pnl_usd"] for r in filled if r.get("sim_pnl_usd") is not None]
        wins = [p for p in pnls if p > 0]
        out.append({
            "symbol": sym, "sim_type": sim_type, "wait_pips": w,
            "cycles": total, "filled": len(filled), "missed": len(missed),
            "blocked": len(blocked),
            "fill_rate": round(len(filled) / total, 4) if total else 0.0,
            "total_pnl_usd": round(sum(pnls), 2) if pnls else None,
            "avg_pnl_usd": round(sum(pnls) / len(pnls), 2) if pnls else None,
            "win_rate": round(len(wins) / len(pnls), 4) if pnls else None,
            "avg_pips": round(sum(r["sim_pips"] for r in filled
                                  if r.get("sim_pips") is not None) / len(filled), 2)
                        if filled else None,
        })
    return out
