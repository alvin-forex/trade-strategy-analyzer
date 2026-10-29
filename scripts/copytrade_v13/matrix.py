# -*- coding: utf-8 -*-
"""COPYTRADE v1.3 §11.4–11.9——矩陣跑批、指標集、排名、MFE 風險報告、落庫。

D3 補完（2026-10-29）：§11.6 補齊唔使 L0 嘅六指標——avg_win/avg_loss、
max_concurrent（層級區間重疊掃描）、max_float_loss（MAE 疊加保守口徑）、
recovery_days（月度曲線，月首對月首日曆日）、layers_filtered（被層檔截走層數）、
monthly_pnl（每月 P/L compact 串）。margin 系指標仍等 L0（README 待辦）。
"""
import sqlite3
from collections import defaultdict
from datetime import datetime

from ingest import _pt  # D/M/YYYY 唯一口徑（同 analyzer TIME_FMT）
from sim_engine import (LAYER_POLICIES, COPY_METHODS, ACCOUNTS, SCENARIOS,
                        N_GATE, BUFFER, WEIGHTS, SLIPPAGE_PIPS, cap_layers,
                        sim_cycle, percentile_inc, month_key)


def _max_concurrent(cycles):
    """§11.6 最大同時持倉（層級區間重疊掃描；同刻先 close 後 open 防假重疊）。"""
    events = []
    for c in cycles:
        for L in c["layers"]:
            ot = _pt(L["open_time"])
            ct = _pt(L.get("close_time") or c["close_time"])
            if ot is None or ct is None or ct < ot:
                continue
            events.append((ot, 1))
            events.append((ct, -1))
    if not events:
        return None
    events.sort(key=lambda e: (e[0], e[1]))  # -1 同刻先行（close 先於 open）
    cur = mx = 0
    for _, d in events:
        cur += d
        mx = max(mx, cur)
    return mx


def _recovery_days(months_pnl):
    """§11.6 回撤修復時間（月度曲線粒度）：最長一段 DD 嘅 peak 月→恢復月日曆日差。

    未恢復嘅尾部 DD 唔計（censor）；冇已恢復段 → None。口徑註明喺 README。
    """
    if not months_pnl:
        return None
    cum = peak = 0.0
    peak_k = None
    dd_start = None
    best = None
    for k in sorted(months_pnl):
        cum += months_pnl[k]
        if cum >= peak:
            if dd_start is not None:  # 恢復
                d = (datetime.strptime(k + "-01", "%Y-%m-%d") - dd_start).days
                best = d if best is None else max(best, d)
                dd_start = None
            peak = cum
            peak_k = k
        elif dd_start is None and peak_k is not None:
            dd_start = datetime.strptime(peak_k + "-01", "%Y-%m-%d")
    return best


def _monthly_pnl_str(months_pnl):
    """§11.6 每月 P/L compact 串（"YYYY-MM:val|..."）。"""
    return "|".join(f"{k}:{round(v, 2)}" for k, v in sorted(months_pnl.items())) if months_pnl else None


def _load_cycles(conn, signal_id):
    """DB 讀一個 signal 嘅 cycles（含 layers）。

    D4 性能：原版 per-cycle 兩條 SELECT（N+1，5117 一個 signal 13k cycles）→
    三條大 query（cycles／layers JOIN／trades）Python 組裝——語義零變。
    """
    cyc = conn.execute(
        "SELECT cycle_id,symbol,direction,open_time,close_time,layers_n,lots_total,pnl_total "
        "FROM cycles WHERE signal_id=? ORDER BY cycle_id", (signal_id,)).fetchall()
    if not cyc:
        return []
    lay = defaultdict(list)
    for r in conn.execute(
            "SELECT l.cycle_id,l.layer_no,l.lots,l.open_time,l.open_price,l.pnl,l.lots_cum "
            "FROM layers l JOIN cycles c ON l.cycle_id=c.cycle_id "
            "WHERE c.signal_id=? ORDER BY l.cycle_id,l.layer_no", (signal_id,)):
        lay[r[0]].append(r)
    tr_by = defaultdict(dict)  # (symbol, typ) → {(open_time, lots): (max_loss, comment, close_price, close_time)}
    for r in conn.execute(
            "SELECT symbol,typ,open_time,lots,max_loss,comment,close_price,close_time "
            "FROM trades WHERE signal_id=?", (signal_id,)):
        tr_by[(r[0], r[1])][(r[2], r[3])] = (r[4], r[5], r[6], r[7])
    out = []
    for row in cyc:
        cid, sym, dr = row[0], row[1], row[2]
        tr = tr_by.get((sym, dr.lower()), {})
        layers = []
        for r in lay.get(cid, []):
            k = (r[3], r[2])  # (open_time, lots)——同原版一一同鍵配對
            e = tr.get(k)
            layers.append({"layer_no": r[1], "typ": dr.lower(), "lots": r[2],
                           "open_time": r[3], "open_price": r[4],
                           "net_profit": r[5], "lots_cum": r[6],
                           "max_loss": e[0] if e else None,
                           "comment": e[1] if e else None,
                           "close_price": e[2] if e else None,
                           "close_time": e[3] if e else None,
                           "sl_price": None})
        out.append({"cycle_id": cid, "symbol": sym, "direction": dr,
                    "open_time": row[3], "close_time": row[4],
                    "layers_n": row[5], "pnl_total": row[7], "layers": layers})
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
        "avg_win": round(sum(wins) / len(wins), 2) if wins else None,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else None,
        "monthly_growth": round(growth, 4) if growth is not None else None,
        "monthly_pnl": _monthly_pnl_str(months_pnl),
        "max_dd": round(dd, 2), "max_dd_pct": round(dd_pct, 4) if dd_pct is not None else None,
        "margin_peak": round(margin_peak, 2) if margin_peak else None,
        "max_layer": max_layer, "max_float_loss": round(max_float, 2) if max_float else None,
        "stable_month_ratio": round(stable, 4), "worst_month": round(worst, 2),
        "max_consec_losses": consec_losses,
        "recovery_days": _recovery_days(months_pnl),
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
    for si, sid in enumerate(signals, 1):
        if si % 10 == 0 or si == len(signals):
            print(f"   …matrix {si}/{len(signals)} signals（rows {len(rows):,}）", flush=True)
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
                # D3 補完（§11.6，唔使 L0）：同 (sym, pol) 計一次——最大同時持倉＋被截層數
                max_conc = _max_concurrent(pol_cycles)
                layers_filt = (sum(c["layers_n"] for c in cs)
                               - sum(len(c["layers"]) for c in pol_cycles))
                for method in COPY_METHODS:
                    ratio = cfg["ratio"] if method == "M2" else (ratio_m3 if method == "M3" else 1.0)
                    for account in ACCOUNTS:
                        for scen in SCENARIOS:
                            # D4 性能短路（零行為變）：sp=None 係組合級常量——對應
                            # sim_cycle 頭兩個 BLOCKED return（need_l0／slip 計價）。
                            # RISK_ESTIMATE／MissingFx 係 per-cycle 語義，照行原路。
                            sp = specs.get(sym) if specs else None
                            slip = SLIPPAGE_PIPS.get(scen, 0.0)
                            if sp is None and (method in ("M1", "M4", "M5")
                                               or account == "cent" or slip > 0):
                                note_b = ("BLOCKED: 需 L0 symbols 導出（§6.7 鐵律 2 零估算）"
                                          if (method in ("M1", "M4", "M5") or account == "cent")
                                          else "BLOCKED: 需 L0（slippage 計價）")
                                missed_total = sum(len(c["layers"]) for c in pol_cycles)
                                rows.append(_row2(sid, sym, pol_name, method, account, scen,
                                                  {"cycles_n": 0}, None, None, 0, missed_total,
                                                  [note_b], None, "blocked",
                                                  _grade(method, account, specs),
                                                  max_conc=None, layers_filt=None))
                                continue
                            pnls, notes, filled, missed = [], [], 0, 0
                            max_layer = 0
                            months = defaultdict(float)
                            consec = cur_consec = 0
                            mae_all = []
                            float_losses = []  # §11.6 最大浮動虧損（cycle 級 MAE 疊加，保守口徑）
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
                                cyc_float = 0.0
                                for L in c["layers"]:
                                    if L.get("max_loss"):
                                        mae_all.append(abs(min(0.0, L["max_loss"])) * ratio)
                                        cyc_float += min(0.0, L["max_loss"]) * ratio
                                float_losses.append(cyc_float)
                            if not pnls:
                                rows.append(_row2(sid, sym, pol_name, method, account, scen,
                                                  {"cycles_n": 0}, None, None, filled, missed,
                                                  notes, None, "blocked",
                                                  _grade(method, account, specs),
                                                  max_conc=None, layers_filt=None))
                                continue
                            # §11.5 MFE/MAE 起始資金（MAE 估算；無 SL 標 MAE 估算）
                            mae_p95 = percentile_inc(mae_all, 0.95) if mae_all else 0.0
                            sandwich = mae_p95 * max_layer if max_layer > 1 else mae_p95
                            est_sl = round(sandwich, 2)
                            start_eq = round(sandwich * BUFFER, 2)
                            # 蒸發風險分：L0 缺 → 0＋note（margin 未計）
                            evap = 0.0
                            max_float = min(float_losses) if float_losses else None
                            m = _metrics(pnls, months, start_eq, None, max_layer, max_float,
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
                                              est_sl, gate, _grade(method, account, specs),
                                              max_conc=max_conc, layers_filt=layers_filt))
    return rows


def _grade(method, account, specs):
    """§11.7 可信度分級：A 完整模擬；M1/M4/cent 需 L0 → 標 A 但 outcome 註明 blocked。"""
    return "A"


def _row2(sid, sym, pol, method, account, scen, m, score, start_eq, filled, missed,
          notes, est_sl, gate, grade, max_conc=None, layers_filt=None):
    note = ";".join(list(dict.fromkeys(notes))[:2]) if notes else (gate or None)
    return {
        "signal_id": sid, "symbol": sym, "layer_policy": pol, "copy_method": method,
        "account_type": account, "cost_scenario": scen,
        **m, "trades_filled": filled, "trades_missed": missed,
        "max_concurrent": max_conc, "layers_filtered": layers_filt,
        "est_sl_cost_usd": est_sl,
        "est_margin_peak_usd": None,  # §6.4 margin 需 L0＋逐日價；L0 到位後解鎖
        "suggested_start_equity_usd": start_eq,
        "risk_adj_score": score, "data_grade": grade, "outcome_note": note,
    }


def write_rows(conn, rows):
    """copy_sims 批量入庫。"""
    cols = ["signal_id", "symbol", "layer_policy", "copy_method", "account_type",
            "cost_scenario", "cycles_n", "trades_filled", "trades_missed",
            "layers_filtered",
            "gross_pnl", "net_pnl", "win_rate", "profit_factor", "expectancy",
            "avg_win", "avg_loss", "monthly_growth", "monthly_pnl",
            "max_dd", "max_dd_pct", "margin_peak", "margin_ratio",
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
