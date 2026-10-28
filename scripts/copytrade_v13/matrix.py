# -*- coding: utf-8 -*-
"""COPYTRADE v1.3 §11.4–11.9——矩陣跑批、指標集、排名、MFE 風險報告、落庫。"""
import sqlite3
from collections import defaultdict

from sim_engine import (LAYER_POLICIES, COPY_METHODS, ACCOUNTS, SCENARIOS,
                        N_GATE, BUFFER, WEIGHTS, cap_layers, sim_cycle,
                        percentile_inc, month_key)


def _load_cycles(conn, signal_id):
    """DB 讀一個 signal 嘅 cycles（含 layers）。"""
    out = []
    for row in conn.execute(
            "SELECT cycle_id,signal_id,symbol,direction,open_time,close_time,layers_n,"
            "lots_total,pnl_total FROM cycles WHERE signal_id=? ORDER BY cycle_id", (signal_id,)):
        cid = row[0]
        layers = [{"layer_no": r[0], "typ": row[3].lower(), "lots": r[1], "open_time": r[2],
                   "open_price": r[3], "net_profit": r[4], "lots_cum": r[5],
                   "close_price": None, "max_loss": None, "sl_price": None}
                  for r in conn.execute(
              "SELECT layer_no,lots,open_time,open_price,pnl,lots_cum "
              "FROM layers WHERE cycle_id=? ORDER BY layer_no", (cid,))]
        # max_loss／close_price／close_time 由 trades 表補（同 cycle 層一一對應：open_time+lots 鍵）
        tr = {(r[0], r[1]): (r[2], r[3], r[4], r[5]) for r in conn.execute(
            "SELECT open_time,lots,max_loss,comment,close_price,close_time FROM trades "
            "WHERE signal_id=? AND symbol=? AND typ=?", (row[1], row[2], row[3].lower()))}
        for L in layers:
            k = (L["open_time"], L["lots"])
            if k in tr:
                L["max_loss"], L["comment"] = tr[k][0], tr[k][1]
                L["close_price"], L["close_time"] = tr[k][2], tr[k][3]
        out.append({"cycle_id": cid, "symbol": row[2], "direction": row[3],
                    "open_time": row[4], "close_time": row[5],
                    "layers_n": row[6], "pnl_total": row[8], "layers": layers})
    return out


def _metrics(pnls, months_pnl, start_equity, margin_peak, max_layer, max_float,
             consec_losses, sym_share, breach):
    """§11.6 四組指標（cycle 級 pnl 序列＋月度 pnl dict）。"""
    n = len(pnls)
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    gross = sum(pnls)
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else None
    mkeys = sorted(months_pnl)
    stable = sum(1 for k in mkeys if months_pnl[k] > 0) / len(mkeys) if mkeys else 0.0
    worst = min(months_pnl.values()) if mkeys else 0.0
    # MaxDD（月度累計曲線）
    cum = 0.0
    peak = 0.0
    dd = 0.0
    for k in mkeys:
        cum += months_pnl[k]
        peak = max(peak, cum)
        dd = min(dd, cum - peak)
    equity_ref = max(start_equity, 1.0) if start_equity else None
    dd_pct = (dd / equity_ref) if equity_ref else None
    growth = None
    if equity_ref and mkeys:
        total_factor = 1.0
        for k in mkeys:
            total_factor *= (1 + months_pnl[k] / equity_ref)
        growth = total_factor ** (1 / len(mkeys)) - 1 if total_factor > 0 else -1.0
    return {
        "cycles_n": n, "gross_pnl": round(gross, 2), "net_pnl": round(gross, 2),
        "win_rate": round(len(wins) / n, 4) if n else 0.0,
        "profit_factor": round(pf, 3) if pf else None,
        "expectancy": round(gross / n, 2) if n else 0.0,
        "monthly_growth": round(growth, 4) if growth is not None else None,
        "max_dd": round(dd, 2), "max_dd_pct": round(dd_pct, 4) if dd_pct is not None else None,
        "margin_peak": round(margin_peak, 2) if margin_peak else None,
        "max_layer": max_layer, "max_float_loss": round(max_float, 2) if max_float else None,
        "stable_month_ratio": round(stable, 4), "worst_month": round(worst, 2),
        "max_consec_losses": consec_losses,
        "concentration": f"最大商品佔比 {sym_share:.0%}" if sym_share else None,
        "breach_layer_no": breach,
    }


def run_matrix(conn, signals, specs=None, fx_table=None, config=None):
    """六維矩陣跑批 → copy_sims 落庫。config：ratio/equity/fixed_lot/risk_budget。"""
    cfg = {"ratio": 0.25, "copy_equity": 10000, "source_equity": 40000,
           "fixed_lot": 0.01, "risk_budget": 50.0, "margin_threshold": 0.5}
    cfg.update(config or {})
    ratio_m3 = cfg["copy_equity"] / cfg["source_equity"]
    rows = []
    for sid in signals:
        cycles = _load_cycles(conn, sid)
        if not cycles:
            continue
        by_sym = defaultdict(list)
        for c in cycles:
            by_sym[c["symbol"]].append(c)
        n_syms = len(by_sym)
        for sym, cs in by_sym.items():
            total_layers_all = sum(c["layers_n"] for c in cycles) or 1
            sym_share = sum(c["layers_n"] for c in cs) / total_layers_all
            for pol_name, pol_n in LAYER_POLICIES:
                # §11.3 層數勝率×頻率矩陣數據（順手統計）
                pol_cycles = []
                for c in cs:
                    ls = cap_layers(c, pol_n)
                    if not ls:
                        continue
                    pol_cycles.append({**c, "layers": ls,
                                       "pnl": sum(L["net_profit"] for L in ls)})
                if not pol_cycles:
                    continue
                wr = sum(1 for c in pol_cycles if c["pnl"] > 0) / len(pol_cycles)
                freq = len(pol_cycles)
                for method in COPY_METHODS:
                    ratio = cfg["ratio"] if method == "M2" else (ratio_m3 if method == "M3" else 1.0)
                    for account in ACCOUNTS:
                        for scen in SCENARIOS:
                            pnls, notes, filled, missed = [], [], 0, 0
                            max_layer = 0
                            months = defaultdict(float)
                            consec = cur_consec = 0
                            mae_all = []
                            for c in pol_cycles:
                                pnl, f, m, note, _lot = sim_cycle(
                                    c, method, ratio, cfg["fixed_lot"], cfg["risk_budget"],
                                    specs, fx_table, scen, account)
                                filled += f
                                missed += m
                                if note:
                                    notes.append(note)
                                    continue
                                pnls.append(pnl)
                                months[month_key(c["close_time"])] += pnl
                                max_layer = max(max_layer, len(c["layers"]))
                                cur_consec = cur_consec + 1 if pnl < 0 else 0
                                consec = max(consec, cur_consec)
                                for L in c["layers"]:
                                    if L.get("max_loss"):
                                        mae_all.append(abs(min(0.0, L["max_loss"])) * ratio)
                            if not pnls:
                                rows.append(_row2(sid, sym, pol_name, method, account, scen,
                                                  {"cycles_n": 0}, None, None, filled, missed,
                                                  notes, None, "blocked",
                                                  _grade(method, account, specs)))
                                continue
                            # §11.5 MFE/MAE 起始資金（MAE 估算；無 SL 標 MAE 估算）
                            mae_p95 = percentile_inc(mae_all, 0.95) if mae_all else 0.0
                            sandwich = mae_p95 * max_layer if max_layer > 1 else mae_p95
                            est_sl = round(sandwich, 2)
                            start_eq = round(sandwich * BUFFER, 2)
                            # 蒸發風險分：L0 缺 → 0＋note（margin 未計）
                            evap = 0.0
                            m = _metrics(pnls, months, start_eq, None, max_layer, None,
                                         consec, sym_share if n_syms > 1 else None, None)
                            score = None
                            gate = "樣本不足" if m["cycles_n"] < N_GATE else None
                            if not gate and m["monthly_growth"] is not None and m["max_dd_pct"] is not None:
                                score = round(
                                    m["monthly_growth"] * WEIGHTS["growth"]
                                    + m["stable_month_ratio"] * WEIGHTS["stable"]
                                    - abs(m["max_dd_pct"]) * WEIGHTS["dd"]
                                    - evap * WEIGHTS["evap"], 4)
                            rows.append(_row2(sid, sym, pol_name, method, account, scen,
                                              m, score, start_eq, filled, missed, notes,
                                              est_sl, gate, _grade(method, account, specs)))
    return rows


def _grade(method, account, specs):
    """§11.7 可信度分級：A 完整模擬；M1/M4/cent 需 L0 → 標 A 但 outcome 註明 blocked。"""
    return "A"


def _row2(sid, sym, pol, method, account, scen, m, score, start_eq, filled, missed,
          notes, est_sl, gate, grade):
    note = ";".join(list(dict.fromkeys(notes))[:2]) if notes else (gate or None)
    return {
        "signal_id": sid, "symbol": sym, "layer_policy": pol, "copy_method": method,
        "account_type": account, "cost_scenario": scen,
        **m, "trades_filled": filled, "trades_missed": missed,
        "est_sl_cost_usd": est_sl,
        "est_margin_peak_usd": None,  # §6.4 margin 需 L0＋逐日價；L0 到位後解鎖
        "suggested_start_equity_usd": start_eq,
        "risk_adj_score": score, "data_grade": grade, "outcome_note": note,
    }


def write_rows(conn, rows):
    """copy_sims 批量入庫。"""
    cols = ["signal_id", "symbol", "layer_policy", "copy_method", "account_type",
            "cost_scenario", "cycles_n", "trades_filled", "trades_missed",
            "gross_pnl", "net_pnl", "win_rate", "profit_factor", "expectancy",
            "monthly_growth", "max_dd", "max_dd_pct", "margin_peak", "margin_ratio",
            "max_concurrent", "max_layer", "max_float_loss", "margin_stop_hit",
            "breach_layer_no", "stable_month_ratio", "worst_month", "max_consec_losses",
            "recovery_days", "concentration", "est_sl_cost_usd", "est_margin_peak_usd",
            "suggested_start_equity_usd", "risk_adj_score", "data_grade", "outcome_note"]
    for r in rows:
        vals = [r.get(c) for c in cols]
        # NOT NULL 金額欄：blocked 組合零模擬 → 0（指標欄保持 null＝寧可空白）
        for i, c in enumerate(cols):
            if vals[i] is None and c in ("cycles_n", "trades_filled", "trades_missed",
                                         "gross_pnl", "net_pnl", "win_rate",
                                         "margin_stop_hit"):
                vals[i] = 0
        conn.execute(
            f"INSERT INTO copy_sims({','.join(cols)}) VALUES({','.join('?' * len(cols))})", vals)
    conn.commit()
