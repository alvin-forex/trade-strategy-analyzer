#!/usr/bin/env python3
"""Portfolio Unified Generator — 合併 Enhanced (TP/SL) + V2 (月度回測/相關性)

Usage:
    python3 scripts/portfolio_unified.py --portfolio P1 --csv-dir samples --output-dir docs/admin/portfolios
"""

import csv, json, os, math, argparse, logging
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from pathlib import Path

# ── Constants ──────────────────────────────────────────────
BALANCE_KEYWORDS = {"balance", "transfer", "credit"}
NOTIONAL_CAPITAL = 10000.0
PIP_VALUE = 10.0  # $10/pip per standard lot

PORTFOLIO_DEFS = [
    {"id": "P1", "name": "DW 保守組", "capital": 1500, "risk_pct": 2.0,
     "target_monthly": 0.5, "signals": ["31593", "17547", "30359"],
     "ea_types": "DW", "risk_level": "Medium", "layers": "L1-L3"},
    {"id": "P2", "name": "SMA 日內組", "capital": 1500, "risk_pct": 1.5,
     "target_monthly": 0.5, "signals": ["16698", "32278", "5001"],
     "ea_types": "SMA", "risk_level": "Low", "layers": "L1-L3"},
    {"id": "P3", "name": "DW SMA 混合穩健組", "capital": 2000, "risk_pct": 1.5,
     "target_monthly": 0.4, "signals": ["23617", "10843"],
     "ea_types": "DW, SMA", "risk_level": "Low", "layers": "L1-L3"},
    {"id": "P4", "name": "DW 高頻組", "capital": 1000, "risk_pct": 2.0,
     "target_monthly": 0.6, "signals": ["20805", "31593", "3291", "16698"],
     "ea_types": "DW", "risk_level": "Medium", "layers": "L1-L3"},
    {"id": "P5", "name": "高利潤單組", "capital": 800, "risk_pct": 2.0,
     "target_monthly": 0.8, "signals": ["5117", "27226"],
     "ea_types": "UNK", "risk_level": "High", "layers": "L1-L2"},
    {"id": "P6", "name": "亞洲時段組", "capital": 1000, "risk_pct": 1.5,
     "target_monthly": 0.4, "signals": ["30359", "33101", "17547"],
     "ea_types": "DW, Flash", "risk_level": "Medium", "layers": "L1-L3"},
    {"id": "P7", "name": "頂級信號組", "capital": 1200, "risk_pct": 2.0,
     "target_monthly": 0.6, "signals": ["5117", "11598", "17547", "27226", "20805", "21698", "22200", "31593", "4022", "3291"],
     "ea_types": "DW, SMA, UNK", "risk_level": "High", "layers": "L1-L3"},
    {"id": "P8", "name": "London 時段組", "capital": 1200, "risk_pct": 2.0,
     "target_monthly": 0.5, "signals": ["33101", "19849", "32541", "10843"],
     "ea_types": "DW, Flash, SMA, UNK", "risk_level": "High", "layers": "L1-L2"},
    {"id": "P9", "name": "NY 時段組", "capital": 1500, "risk_pct": 2.0,
     "target_monthly": 0.5, "signals": ["32719", "36511", "27226", "31781"],
     "ea_types": "DW, UNK", "risk_level": "High", "layers": "L1-L3"},
    {"id": "P10", "name": "混合策略組", "capital": 1800, "risk_pct": 2.0,
     "target_monthly": 0.5, "signals": ["17547", "21698", "22200", "31593", "3291", "5001", "14158", "32278", "16596", "16698"],
     "ea_types": "DW, SMA", "risk_level": "High", "layers": "L1-L3"},
]

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ── 1. CSV Loading ─────────────────────────────────────────
def load_signal_csv(signal_id: str, csv_dir: str = "samples") -> list[dict]:
    path = Path(csv_dir) / f"forex-forest-signals-page-{signal_id}.csv"
    if not path.exists():
        log.warning(f"CSV not found: {path}")
        return []
    trades = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                ttype = row.get("Type", "").strip().lower()
                if ttype in BALANCE_KEYWORDS:
                    continue
                symbol = row.get("Symbol", "").strip()
                if not symbol:
                    continue
                t = {
                    "open_time": row.get("Open Time", ""),
                    "close_time": row.get("Close Time", ""),
                    "type": ttype,
                    "lots": float(row.get("Lots", 0) or 0),
                    "net_pips": float(row.get("Net Pips", 0) or 0),
                    "net_profit": float(row.get("Net Profit", 0) or 0),
                    "symbol": symbol,
                    "holding_hrs": float(row.get("Holding Time (Hours)", 0) or 0),
                    "comment": row.get("Comment", ""),
                }
                trades.append(t)
            except (ValueError, TypeError):
                continue
    return trades


# ── 2. Signal Stats ────────────────────────────────────────
def calc_signal_stats(trades: list[dict]) -> dict:
    if not trades:
        return {}
    wins = [t for t in trades if t["net_profit"] > 0]
    losses = [t for t in trades if t["net_profit"] <= 0]
    total_pnl = sum(t["net_profit"] for t in trades)
    total_pips = sum(t["net_pips"] for t in trades)
    avg_win = sum(t["net_profit"] for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t["net_profit"] for t in losses) / len(losses)) if losses else 0
    total_win_pnl = sum(t["net_profit"] for t in wins)
    total_loss_pnl = abs(sum(t["net_profit"] for t in losses))
    pf = total_win_pnl / total_loss_pnl if total_loss_pnl > 0 else 99.0
    # Max DD (dollar-based on raw PnL sequence)
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in sorted(trades, key=lambda x: x["close_time"] or x["open_time"]):
        equity += t["net_profit"]
        if equity > peak:
            peak = equity
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
    avg_hold = sum(t["holding_hrs"] for t in trades) / len(trades)
    # Top CCY
    ccy_counts = defaultdict(lambda: {"count": 0, "wins": 0, "pnl": 0.0})
    for t in trades:
        s = t["symbol"]
        ccy_counts[s]["count"] += 1
        ccy_counts[s]["pnl"] += t["net_profit"]
        if t["net_profit"] > 0:
            ccy_counts[s]["wins"] += 1
    top_ccy = sorted(ccy_counts.items(), key=lambda x: x[1]["count"], reverse=True)[:5]
    return {
        "count": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 2),
        "total_pnl": round(total_pnl, 2),
        "total_pips": round(total_pips, 1),
        "avg_win": round(avg_win, 2),
        "avg_loss": round(avg_loss, 2),
        "profit_factor": round(pf, 2),
        "max_dd": round(max_dd, 2),
        "avg_hold_hours": round(avg_hold, 1),
        "top_ccy": top_ccy,
    }


# ── 3. Month Parsing ───────────────────────────────────────
def parse_month(ts: str) -> Optional[str]:
    if not ts:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            dt = datetime.strptime(ts.strip(), fmt)
            return dt.strftime("%Y-%m")
        except ValueError:
            continue
    # Try just YYYY-MM
    parts = ts.strip()[:7]
    if len(parts) == 7 and parts[4] == "-":
        return parts
    return None


# ── 4. Monthly Analysis ────────────────────────────────────
def monthly_analysis(trades: list[dict], min_trades: int = 2) -> dict:
    monthly_pnl = defaultdict(float)
    monthly_wins = defaultdict(int)
    monthly_losses = defaultdict(int)
    monthly_trades = defaultdict(int)
    monthly_pips = defaultdict(float)
    monthly_lots = defaultdict(list)

    for t in trades:
        m = parse_month(t.get("close_time") or t.get("open_time"))
        if not m:
            continue
        original_lot = max(t["lots"], 0.01)
        pnl_001 = t["net_profit"] / original_lot * 0.01
        pips_001 = t["net_pips"] / original_lot * 0.01
        monthly_pnl[m] += pnl_001
        monthly_pips[m] += pips_001
        monthly_trades[m] += 1
        monthly_lots[m].append(original_lot)
        if pnl_001 > 0:
            monthly_wins[m] += 1
        else:
            monthly_losses[m] += 1

    months = sorted(monthly_pnl.keys())
    result = {}
    for m in months:
        if monthly_trades[m] < min_trades:
            continue
        wr = monthly_wins[m] / monthly_trades[m] * 100 if monthly_trades[m] else 0
        wins_pnl = sum(v for k, v in monthly_pnl.items() if k == m and monthly_pnl[m] > 0)
        # Simplified PF for the month
        pos = monthly_pnl[m] if monthly_pnl[m] > 0 else 0
        neg = abs(monthly_pnl[m]) if monthly_pnl[m] < 0 else 0
        pf = pos / neg if neg > 0 else 99.0
        avg_lot = sum(monthly_lots[m]) / len(monthly_lots[m]) if monthly_lots[m] else 0
        result[m] = {
            "trades": monthly_trades[m],
            "win_rate": round(wr, 1),
            "net_pnl_001": round(monthly_pnl[m], 2),
            "pips_001": round(monthly_pips[m], 1),
            "pf": round(pf, 2),
            "avg_lot": round(avg_lot, 3),
        }
    return result


# ── 5. Sequential Simulation ───────────────────────────────
def sequential_simulation(trades: list[dict]) -> dict:
    raw = [t for t in trades if isinstance(t.get("net_profit"), (int, float)) and t.get("symbol")]
    if not raw:
        return {"error": "no valid trades"}

    monthly_pnl_001 = defaultdict(float)
    monthly_wins = defaultdict(int)
    monthly_losses = defaultdict(int)
    monthly_trade_count = defaultdict(int)

    for t in raw:
        original_lot = max(t["lots"], 0.01)
        pnl_001 = t["net_profit"] / original_lot * 0.01
        m = parse_month(t.get("close_time") or t.get("open_time"))
        if m:
            monthly_pnl_001[m] += pnl_001
            monthly_trade_count[m] += 1
            if pnl_001 > 0:
                monthly_wins[m] += 1
            else:
                monthly_losses[m] += 1

    if not monthly_pnl_001:
        return {"error": "no months with valid data"}

    months_sorted = sorted(monthly_pnl_001.keys())
    equity = NOTIONAL_CAPITAL
    peak = NOTIONAL_CAPITAL
    equity_curve = [("start", round(NOTIONAL_CAPITAL, 2))]
    max_dd_pct = 0.0
    max_dd_dollars = 0.0
    max_consec_loss_months = 0
    cur_consec_loss = 0
    total_win_001 = 0.0
    total_loss_001 = 0.0
    win_months = 0
    loss_months = 0

    for m in months_sorted:
        pnl = monthly_pnl_001[m]
        equity += pnl
        if pnl > 0:
            win_months += 1
            total_win_001 += pnl
            cur_consec_loss = 0
        else:
            loss_months += 1
            total_loss_001 += abs(pnl)
            cur_consec_loss += 1
            max_consec_loss_months = max(max_consec_loss_months, cur_consec_loss)
        if equity > peak:
            peak = equity
        dd_pct = ((peak - equity) / peak * 100) if peak > 0 else 0.0
        max_dd_pct = max(max_dd_pct, dd_pct)
        drawdown = peak - equity
        if drawdown > max_dd_dollars:
            max_dd_dollars = drawdown
        equity_curve.append((m, round(equity, 2)))

    total_months = len(months_sorted)
    pf = total_win_001 / total_loss_001 if total_loss_001 > 0 else 99.0
    avg_monthly_pnl = round(sum(monthly_pnl_001[m] for m in months_sorted) / total_months, 2)

    return {
        "total_trades": sum(monthly_trade_count.values()),
        "total_months": total_months,
        "avg_monthly_pnl_001": avg_monthly_pnl,
        "monthly_win_rate": round(win_months / total_months * 100, 1) if total_months else 0,
        "win_months": win_months,
        "loss_months": loss_months,
        "profit_factor_001": round(pf, 2),
        "max_dd": round(max_dd_dollars, 2),
        "max_dd_pct_001": round(max_dd_pct, 2),
        "max_consec_loss_months": max_consec_loss_months,
        "avg_monthly_trades": round(sum(monthly_trade_count.values()) / total_months, 1) if total_months else 0,
        "equity_curve_001": equity_curve,
        "monthly": {m: {"trades": monthly_trade_count[m], "wins": monthly_wins[m], "losses": monthly_losses[m], "pnl_001": round(monthly_pnl_001[m], 2)} for m in months_sorted},
    }


# ── 6. Correlation ─────────────────────────────────────────
def portfolio_correlation(signal_monthly: list[dict]) -> list[dict]:
    """Calculate Pearson correlation between signals based on monthly PnL."""
    # Collect all months
    all_months = set()
    for s in signal_monthly:
        all_months.update(s["monthly"].keys())
    all_months = sorted(all_months)

    # Build PnL vectors
    vectors = {}
    for s in signal_monthly:
        sid = s["signal_id"]
        vectors[sid] = [s["monthly"].get(m, {}).get("pnl_001", 0) for m in all_months]

    results = []
    sids = list(vectors.keys())
    for i, a in enumerate(sids):
        for b in sids[i+1:]:
            va, vb = vectors[a], vectors[b]
            n = len(va)
            if n < 3:
                continue
            mean_a = sum(va) / n
            mean_b = sum(vb) / n
            cov = sum((va[j] - mean_a) * (vb[j] - mean_b) for j in range(n))
            std_a = math.sqrt(sum((x - mean_a) ** 2 for x in va))
            std_b = math.sqrt(sum((x - mean_b) ** 2 for x in vb))
            corr = cov / (std_a * std_b) if std_a > 0 and std_b > 0 else 0
            corr = round(corr, 3)
            direction = "positive" if corr > 0 else "negative" if corr < 0 else "none"
            results.append({"a": a, "b": b, "corr": corr, "direction": direction})
    return results


# ── 7. TP/SL Calculator ────────────────────────────────────
def calculate_tpsl(stats: dict, capital: float, risk_pct: float, signal_id: str) -> dict:
    avg_win = stats.get("avg_win", 50)
    avg_loss = stats.get("avg_loss", 30)
    max_dd = stats.get("max_dd", 500)

    # SL based on avg_loss, expressed in pips (assume $10/pip per standard lot → $0.10/pip per 0.01 lot)
    # But avg_loss is in dollars at the signal's actual lot sizes. We use avg_loss to derive a pip-based SL.
    # Simplified: SL_pips ≈ avg_loss / 10 (assuming avg_loss at ~0.01-0.03 lot, scale factor)
    # More robust: use max_dd per trade as proxy
    if avg_loss > 0:
        sl_pips_l1 = max(15, round(avg_loss / 3))  # pips
    else:
        sl_pips_l1 = 25

    # Adjust for high-risk signals
    risk_factor = 1.0
    if stats.get("profit_factor", 0) < 2.0:
        risk_factor = 0.5  # Halve exposure for low PF

    # RR ratio target
    if avg_win > 0 and avg_loss > 0:
        natural_rr = avg_win / avg_loss
        target_rr = min(max(natural_rr, 1.5), 3.0)
    else:
        target_rr = 2.0

    sl_l1 = sl_pips_l1
    sl_l2 = round(sl_l1 * 1.3)
    sl_l3 = round(sl_l1 * 1.6)

    tp1_l1 = round(sl_l1 * target_rr)
    tp2_l1 = round(sl_l1 * target_rr * 1.6)
    tp3_l1 = round(sl_l1 * target_rr * 2.2)

    tp1_l2 = round(sl_l2 * target_rr)
    tp2_l2 = round(sl_l2 * target_rr * 1.6)
    tp3_l2 = round(sl_l2 * target_rr * 2.2)

    tp1_l3 = round(sl_l3 * target_rr)
    tp2_l3 = round(sl_l3 * target_rr * 1.6)
    tp3_l3 = round(sl_l3 * target_rr * 2.2)

    # Lot sizes
    risk_amount = capital * (risk_pct / 100) * risk_factor
    lot_l1_raw = risk_amount / (sl_l1 * PIP_VALUE)
    lot_l1 = max(0.01, round(lot_l1_raw * 0.4, 2))  # Safety margin
    lot_l2 = round(lot_l1 * 1.5, 2)
    lot_l3 = round(lot_l2 * 1.5, 2)

    return {
        "signal_id": signal_id,
        "sl_l1": sl_l1, "sl_l2": sl_l2, "sl_l3": sl_l3,
        "tp1_l1": tp1_l1, "tp2_l1": tp2_l1, "tp3_l1": tp3_l1,
        "tp1_l2": tp1_l2, "tp2_l2": tp2_l2, "tp3_l2": tp3_l2,
        "tp1_l3": tp1_l3, "tp2_l3": tp2_l3, "tp3_l3": tp3_l3,
        "lot_l1": lot_l1, "lot_l2": lot_l2, "lot_l3": lot_l3,
        "total_lot": round(lot_l1 + lot_l2 + lot_l3, 2),
        "rr": target_rr,
        "risk_amount": round(risk_amount, 2),
        "formula": f"(${capital} × {risk_pct}% × {risk_factor}) / ({sl_l1}p × ${PIP_VALUE}) = {lot_l1_raw:.4f} → {lot_l1}",
    }


# ── 8. HTML Generator ──────────────────────────────────────
def generate_unified_html(pdef: dict, signal_analyses: list[dict], portfolio_sim: dict,
                          correlations: list[dict], tpsl_list: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    pid = pdef["id"]
    signals = pdef["signals"]
    capital = pdef["capital"]
    risk = pdef["risk_pct"]
    total_trades = sum(s["stats"]["count"] for s in signal_analyses if s.get("stats"))
    avg_wr = sum(s["stats"]["win_rate"] for s in signal_analyses if s.get("stats")) / len(signal_analyses) if signal_analyses else 0
    total_pnl = sum(s["stats"]["total_pnl"] for s in signal_analyses if s.get("stats"))

    h = []
    h.append('<!DOCTYPE html>')
    h.append('<html lang="zh-Hant">')
    h.append('<head>')
    h.append('<meta charset="UTF-8">')
    h.append('<meta name="viewport" content="width=device-width, initial-scale=1.0">')
    h.append(f'<title>Portfolio {pid} 統一版 | {pdef["name"]}</title>')
    h.append('<link rel="stylesheet" href="../sidebar.css">')
    h.append('<script src="../sidebar.js"></script>')
    h.append('''<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0d1117;color:#c9d1d9}
body.has-sidebar{padding-left:240px}
.container{max-width:1200px;margin:auto;padding:20px}
h1{color:#58a6ff;font-size:1.4em;margin-bottom:6px}
h2{color:#58a6ff;font-size:1.05em;border-bottom:1px solid #21262d;padding-bottom:6px;margin-bottom:10px}
.meta{color:#8b949e;font-size:0.8em;margin-bottom:16px}
.section{background:#161b22;border-radius:8px;padding:16px;margin-bottom:14px;border:1px solid #21262d}
.stat-grid{display:flex;flex-wrap:wrap;gap:8px;margin-top:8px}
.stat-card{background:#21262d;border-radius:6px;padding:10px 14px;min-width:110px}
.stat-label{color:#8b949e;font-size:0.72em;margin-bottom:3px;text-transform:uppercase;letter-spacing:0.5px}
.stat-value{font-size:1.1em;font-weight:600}
.positive{color:#3fb950}.negative{color:#f85149}.warning{color:#d29922}
table{width:100%;border-collapse:collapse;margin-top:8px;font-size:0.85em}
th,td{padding:6px 10px;text-align:left;border-bottom:1px solid #21262d}
th{color:#8b949e;font-weight:600;font-size:0.8em}
tr:hover{background:#1c2128}
.signal-link{color:#58a6ff;text-decoration:none}.signal-link:hover{text-decoration:underline}
.ea-badge{display:inline-block;padding:2px 6px;border-radius:4px;font-size:0.72em;font-weight:600}
.calc-box{background:#21262d;border-radius:6px;padding:10px;margin:6px 0;font-family:monospace;font-size:0.82em}
.formula{color:#d29922}
.risk-low{color:#3fb950}.risk-medium{color:#d29922}.risk-high{color:#f85149}
ul{margin-left:18px;margin-top:6px}li{margin:3px 0}
.footer{margin-top:20px;padding:12px;text-align:center;color:#8b949e;font-size:0.78em;border-top:1px solid #21262d}
.footer a{color:#58a6ff;text-decoration:none;margin:0 6px}
.note{background:#1c2128;border-left:3px solid #58a6ff;padding:8px 12px;margin:8px 0;border-radius:0 4px 4px 0;font-size:0.82em;color:#8b949e}
</style>''')
    h.append('</head>')
    h.append('<body class="has-sidebar">')
    h.append('<div class="container">')

    # Title
    h.append(f'<h1>📊 Portfolio {pid} 統一版: {pdef["name"]}</h1>')
    h.append(f'<div class="meta">生成時間：{now} | 策略：{pdef["ea_types"]} | 風險等級：{pdef["risk_level"]} | 層數：{pdef["layers"]}</div>')

    # ── Section 1: Overview ──
    h.append('<div class="section">')
    h.append('<h2>📋 Portfolio 概述</h2>')
    h.append('<div class="stat-grid">')
    h.append(f'<div class="stat-card"><div class="stat-label">投入資金</div><div class="stat-value">${capital:,}</div></div>')
    h.append(f'<div class="stat-card"><div class="stat-label">目標月報酬</div><div class="stat-value">{pdef["target_monthly"]*100}%</div></div>')
    h.append(f'<div class="stat-card"><div class="stat-label">每筆風險</div><div class="stat-value">{risk}%</div></div>')
    h.append(f'<div class="stat-card"><div class="stat-label">信號數量</div><div class="stat-value">{len(signals)}</div></div>')
    h.append(f'<div class="stat-card"><div class="stat-label">平均勝率</div><div class="stat-value">{avg_wr:.1f}%</div></div>')
    h.append(f'<div class="stat-card"><div class="stat-label">總交易數</div><div class="stat-value">{total_trades:,}</div></div>')
    h.append(f'<div class="stat-card"><div class="stat-label">歷史總盈虧</div><div class="stat-value positive">${total_pnl:,.0f}</div></div>')
    total_lot = sum(t["total_lot"] for t in tpsl_list)
    h.append(f'<div class="stat-card"><div class="stat-label">總手數 (L1-L3)</div><div class="stat-value">{total_lot:.2f}</div></div>')
    h.append('</div>')

    # Signal summary table
    h.append('<table><thead><tr><th>Signal</th><th>EA</th><th>主要貨幣對</th><th>勝率</th><th>交易數</th><th>PF</th><th>總盈虧</th><th>Max DD</th><th>平均持倉</th></tr></thead><tbody>')
    for sa in signal_analyses:
        s = sa["stats"]
        sid = sa["signal_id"]
        top_ccy_str = ", ".join(f"{c}" for c, _ in s["top_ccy"][:2])
        deep_link = f'<a class="signal-link" href="../reports/Signal_Deep_Analysis_{sid}.html">{sid}</a>'
        martin_link = f'<a class="signal-link" href="../reports/martin_v4_{sid}.html">🔍</a>'
        pnl_cls = "positive" if s["total_pnl"] >= 0 else "negative"
        dd_cls = "negative" if s["max_dd"] > 5000 else "warning" if s["max_dd"] > 1000 else ""
        h.append(f'<tr><td>{deep_link} {martin_link}</td><td><span class="ea-badge" style="background:#1f3a5f;color:#58a6ff">DW</span></td><td>{top_ccy_str}</td><td>{s["win_rate"]}%</td><td>{s["count"]:,}</td><td>{s["profit_factor"]}</td><td class="{pnl_cls}">${s["total_pnl"]:,.0f}</td><td class="{dd_cls}">${s["max_dd"]:,.0f}</td><td>{s["avg_hold_hours"]:.0f}h</td></tr>')
    h.append('</tbody></table>')
    h.append('</div>')

    # ── Section 2: Monthly Backtest Summary ──
    if portfolio_sim and "error" not in portfolio_sim:
        h.append('<div class="section">')
        h.append('<h2>📈 月度順序回測摘要（0.01 lot 標準化）</h2>')
        h.append('<div class="note">📊 以 0.01 lot 標準化各 Signal PnL，notional capital $10,000，順序計算 equity curve 和 drawdown</div>')
        h.append('<div class="stat-grid">')
        h.append(f'<div class="stat-card"><div class="stat-label">活躍月份</div><div class="stat-value">{portfolio_sim["total_months"]}</div></div>')
        h.append(f'<div class="stat-card"><div class="stat-label">平均月交易</div><div class="stat-value">{portfolio_sim["avg_monthly_trades"]}</div></div>')
        h.append(f'<div class="stat-card"><div class="stat-label">盈利月份</div><div class="stat-value positive">{portfolio_sim["monthly_win_rate"]}%</div></div>')
        h.append(f'<div class="stat-card"><div class="stat-label">連虧月</div><div class="stat-value {"warning" if portfolio_sim["max_consec_loss_months"] > 0 else ""}">{portfolio_sim["max_consec_loss_months"]}</div></div>')
        h.append(f'<div class="stat-card"><div class="stat-label">最大回撤</div><div class="stat-value negative">{portfolio_sim["max_dd_pct_001"]}%</div></div>')
        h.append(f'<div class="stat-card"><div class="stat-label">PF (0.01lot)</div><div class="stat-value">{portfolio_sim["profit_factor_001"]}</div></div>')
        h.append(f'<div class="stat-card"><div class="stat-label">平均月盈虧</div><div class="stat-value positive">${portfolio_sim["avg_monthly_pnl_001"]:,.2f}</div></div>')
        h.append('</div>')
        h.append('</div>')

    # ── Section 3: TP/SL Detailed ──
    h.append('<div class="section">')
    h.append('<h2>🎯 詳細 TP/SL 建議（按 Signal 分析）</h2>')
    for sa, tpsl in zip(signal_analyses, tpsl_list):
        s = sa["stats"]
        sid = sa["signal_id"]
        rr = tpsl["rr"]
        high_risk = s["profit_factor"] < 2.0 or s["max_dd"] > 10000
        risk_icon = "⚠️" if high_risk else "✅"
        h.append(f'<h3 style="margin-top:12px;color:#e6edf3">{risk_icon} Signal {sid} — {s["top_ccy"][0][0] if s["top_ccy"] else "?"} 主要交易對</h3>')
        h.append(f'<div class="stat-grid">')
        h.append(f'<div class="stat-card"><div class="stat-label">歷史勝率</div><div class="stat-value">{s["win_rate"]}%</div></div>')
        h.append(f'<div class="stat-card"><div class="stat-label">平均盈利</div><div class="stat-value positive">${s["avg_win"]}</div></div>')
        h.append(f'<div class="stat-card"><div class="stat-label">平均虧損</div><div class="stat-value negative">${s["avg_loss"]}</div></div>')
        h.append(f'<div class="stat-card"><div class="stat-label">PF</div><div class="stat-value">{s["profit_factor"]}</div></div>')
        h.append(f'<div class="stat-card"><div class="stat-label">最大回撤</div><div class="stat-value {"negative" if s["max_dd"]>5000 else ""}">${s["max_dd"]:,.0f}</div></div>')
        h.append(f'<div class="stat-card"><div class="stat-label">平均持倉</div><div class="stat-value">{s["avg_hold_hours"]:.0f}h</div></div>')
        h.append(f'</div>')
        # TP/SL table
        h.append('<table><thead><tr><th>層數</th><th>建議手數</th><th>止損 (SL)</th><th>止盈 1 (50%)</th><th>止盈 2 (30%)</th><th>止盈 3 (20%)</th><th>風險回報比</th></tr></thead><tbody>')
        layers_data = [
            ("L1", tpsl["lot_l1"], tpsl["sl_l1"], tpsl["tp1_l1"], tpsl["tp2_l1"], tpsl["tp3_l1"]),
            ("L2", tpsl["lot_l2"], tpsl["sl_l2"], tpsl["tp1_l2"], tpsl["tp2_l2"], tpsl["tp3_l2"]),
            ("L3", tpsl["lot_l3"], tpsl["sl_l3"], tpsl["tp1_l3"], tpsl["tp2_l3"], tpsl["tp3_l3"]),
        ]
        for label, lot, sl, tp1, tp2, tp3 in layers_data:
            h.append(f'<tr><td><strong>{label}</strong></td><td>{lot:.2f} lots</td><td class="negative">{sl} pips</td><td class="positive">{tp1} pips</td><td class="positive">{tp2} pips</td><td class="positive">{tp3} pips</td><td>1:{rr:.1f}</td></tr>')
        h.append('</tbody></table>')
        # Logic note
        avg_ratio = s["avg_win"] / s["avg_loss"] if s["avg_loss"] > 0 else 0
        if high_risk:
            h.append(f'<div class="note">⚠️ <strong>高風險信號</strong>：PF={s["profit_factor"]} (&lt;2.0) 或 Max DD=${s["max_dd"]:,.0f}，建議降低手數。盈虧比={avg_ratio:.1f}倍</div>')
        else:
            h.append(f'<div class="note">✅ 盈利/虧損 = ${s["avg_win"]}/${s["avg_loss"]} = {avg_ratio:.1f}倍。PF={s["profit_factor"]} 表現穩健。分批止盈：50%@TP1, 30%@TP2, 20%@TP3</div>')
    h.append('</div>')

    # ── Section 4: Monthly Data Per Signal ──
    h.append('<div class="section">')
    h.append('<h2>📋 Signal 月度數據（最近 12 個月）</h2>')
    for sa in signal_analyses:
        sid = sa["signal_id"]
        monthly = sa.get("monthly", {})
        if not monthly:
            continue
        months = sorted(monthly.keys())[-12:]
        score = sa.get("opportunity", {}).get("score", "?")
        grade = sa.get("opportunity", {}).get("grade", "?")
        h.append(f'<h3 style="margin-top:10px;color:#e6edf3">Signal {sid} — Score {score} / {grade}</h3>')
        h.append('<table><thead><tr><th>月份</th><th>交易數</th><th>勝率</th><th>Net PnL (0.01lot)</th><th>PF</th><th>平均手數</th></tr></thead><tbody>')
        for m in months:
            d = monthly[m]
            pnl_cls = "positive" if d["net_pnl_001"] >= 0 else "negative"
            h.append(f'<tr><td>{m}</td><td>{d["trades"]}</td><td>{d["win_rate"]}%</td><td class="{pnl_cls}">${d["net_pnl_001"]:,.2f}</td><td>{d["pf"]}</td><td>{d["avg_lot"]}</td></tr>')
        h.append('</tbody></table>')
    h.append('</div>')

    # ── Section 5: Unified Settings Table ──
    h.append('<div class="section">')
    h.append('<h2>⚙️ 統一設定建議</h2>')
    h.append('<table><thead><tr><th>參數</th>')
    for tpsl in tpsl_list:
        h.append(f'<th>Signal {tpsl["signal_id"]}</th>')
    h.append('</tr></thead><tbody>')
    # Base lot
    h.append('<tr><td><strong>基礎手數 (L1)</strong></td>')
    for tpsl in tpsl_list:
        h.append(f'<td>{tpsl["lot_l1"]:.2f} lots</td>')
    h.append('</tr>')
    # Multiplier
    h.append('<tr><td><strong>加倉倍數</strong></td>')
    for _ in tpsl_list:
        h.append('<td>1.5x</td>')
    h.append('</tr>')
    # SL L1
    h.append('<tr><td><strong>止損 L1</strong></td>')
    for tpsl in tpsl_list:
        h.append(f'<td class="negative">{tpsl["sl_l1"]} pips</td>')
    h.append('</tr>')
    # TP1
    h.append('<tr><td><strong>止盈 1</strong></td>')
    for tpsl in tpsl_list:
        h.append(f'<td class="positive">{tpsl["tp1_l1"]} pips (50%)</td>')
    h.append('</tr>')
    # TP2
    h.append('<tr><td><strong>止盈 2</strong></td>')
    for tpsl in tpsl_list:
        h.append(f'<td class="positive">{tpsl["tp2_l1"]} pips (30%)</td>')
    h.append('</tr>')
    # TP3
    h.append('<tr><td><strong>止盈 3</strong></td>')
    for tpsl in tpsl_list:
        h.append(f'<td class="positive">{tpsl["tp3_l1"]} pips (20%)</td>')
    h.append('</tr>')
    # RR
    h.append('<tr><td><strong>風險回報比</strong></td>')
    for tpsl in tpsl_list:
        h.append(f'<td>1:{tpsl["rr"]:.1f}</td>')
    h.append('</tr>')
    # Trailing stop
    h.append('<tr><td><strong>追蹤止損</strong></td>')
    for tpsl in tpsl_list:
        h.append(f'<td>盈利 {tpsl["sl_l1"]}p 後移至保本</td>')
    h.append('</tr>')
    # Risk amount
    h.append('<tr><td><strong>每筆風險</strong></td>')
    for tpsl in tpsl_list:
        h.append(f'<td>${tpsl["risk_amount"]}</td>')
    h.append('</tr>')
    h.append('</tbody></table>')
    h.append('</div>')

    # ── Section 6: Correlation ──
    if correlations:
        h.append('<div class="section">')
        h.append('<h2>🔗 信號相關性分析</h2>')
        h.append('<div class="note">以每月 0.01lot PnL 做 Pearson correlation；&gt;0.6 代表可能同時好/同時差，分散效果較低</div>')
        h.append('<table><thead><tr><th>Signal A</th><th>Signal B</th><th>相關係數</th><th>方向</th><th>風險</th></tr></thead><tbody>')
        for c in correlations:
            risk_label = "⚠️ 高" if abs(c["corr"]) > 0.6 else "✅ 低" if abs(c["corr"]) < 0.3 else "🟡 中"
            corr_cls = "warning" if abs(c["corr"]) > 0.6 else ""
            h.append(f'<tr><td>{c["a"]}</td><td>{c["b"]}</td><td class="{corr_cls}">{c["corr"]}</td><td>{c["direction"]}</td><td>{risk_label}</td></tr>')
        h.append('</tbody></table>')
        h.append('</div>')

    # ── Section 7: Lot Calculation ──
    h.append('<div class="section">')
    h.append('<h2>🧮 手數計算過程</h2>')
    h.append('<p style="color:#8b949e;font-size:0.85em"><strong>公式：</strong> 建議手數 = (帳戶餘額 × 風險% × 風險因子) / (止損點數 × $10/pip) × 0.4 安全係數</p>')
    for tpsl in tpsl_list:
        h.append(f'<div class="calc-box">')
        h.append(f'<div style="color:#58a6ff">📌 Signal {tpsl["signal_id"]}</div>')
        h.append(f'<div class="formula">{tpsl["formula"]}</div>')
        h.append(f'<div>建議 L1: <strong>{tpsl["lot_l1"]:.2f}</strong> | L2: <strong>{tpsl["lot_l2"]:.2f}</strong> | L3: <strong>{tpsl["lot_l3"]:.2f}</strong> lots（總 {tpsl["total_lot"]:.2f}）</div>')
        h.append('</div>')
    h.append('</div>')

    # ── Section 8: Risk Assessment ──
    combined_dd = sum(s["stats"]["max_dd"] for s in signal_analyses)
    dd_ratio = combined_dd / capital * 100 if capital > 0 else 0
    risk_cls = "risk-high" if dd_ratio > 500 else "risk-medium" if dd_ratio > 100 else "risk-low"
    monthly_est = sum(tpsl["total_lot"] for tpsl in tpsl_list) * avg_wr / 100 * 50  # rough estimate
    h.append('<div class="section">')
    h.append('<h2>⚠️ 風險評估與建議</h2>')
    h.append('<div class="stat-grid">')
    h.append(f'<div class="stat-card"><div class="stat-label">合計最大回撤</div><div class="stat-value negative">${combined_dd:,.0f}</div></div>')
    h.append(f'<div class="stat-card"><div class="stat-label">回撤/資金比</div><div class="stat-value {risk_cls}">{dd_ratio:.0f}%</div></div>')
    h.append(f'<div class="stat-card"><div class="stat-label">爆倉風險</div><div class="stat-value {risk_cls}">{pdef["risk_level"]}</div></div>')
    suggested_capital = max(int(combined_dd * 0.3), capital)
    h.append(f'<div class="stat-card"><div class="stat-label">建議最低資金</div><div class="stat-value">${suggested_capital:,.0f}</div></div>')
    h.append(f'<div class="stat-card"><div class="stat-label">預期月盈虧</div><div class="stat-value positive">${monthly_est:,.0f}</div></div>')
    h.append(f'<div class="stat-card"><div class="stat-label">月報酬率</div><div class="stat-value positive">{monthly_est/capital*100:.0f}%</div></div>')
    h.append('</div>')
    h.append('<h3 style="margin-top:14px;color:#8b949e">💡 風險管理建議</h3>')
    h.append('<ul>')
    h.append('<li><strong>每層風險控制：</strong>單筆交易風險不超過帳戶的 2%（$30）</li>')
    h.append('<li><strong>每日止損：</strong>日虧損超過 $75（5%）即停止交易</li>')
    h.append(f'<li><strong>層數控制：</strong>L1-L3 分層進場，總手持倉不超過 {total_lot:.2f} lots</li>')
    h.append('<li><strong>重要數據迴避：</strong>NFP、CPI、FOMC 前 30 分鐘暫停開倉</li>')
    h.append('<li><strong>定期檢視：</strong>每週五收盤後檢視 Portfolio 表現並調整權重</li>')
    # High-risk signal warnings
    for sa in signal_analyses:
        s = sa["stats"]
        if s["profit_factor"] < 2.0:
            h.append(f'<li class="warning"><strong>⚠️ Signal {sa["signal_id"]} 高風險：</strong>PF={s["profit_factor"]} (&lt;2.0)，建議降低手數</li>')
        if s["max_dd"] > 10000:
            h.append(f'<li class="warning"><strong>⚠️ Signal {sa["signal_id"]} 高回撤：</strong>Max DD=${s["max_dd"]:,.0f}，建議增加資金或降低手數</li>')
    h.append('</ul>')
    h.append('</div>')

    # ── Footer ──
    h.append(f'<div class="footer">')
    h.append(f'Generated by Trade Strategy Analyzer | {now}<br>')
    h.append(f'<a href="https://alvin-forex.github.io/trade-strategy-analyzer/index.html">🦀 TSA</a>')
    h.append(f'<a href="../index.html">🏠首頁</a>')
    h.append(f'<a href="../signal_ranking.html">🏆Signal 排名</a>')
    h.append(f'<a href="../ccy_ranking.html">💱CCY 排名</a>')
    h.append(f'<a href="portfolio_master_report_v2.html">💼Portfolio 總覽</a>')
    h.append(f'</div>')

    h.append('</div>')  # container
    h.append('</body>')
    h.append('</html>')

    return '\n'.join(h)


# ── Opportunity Score ──────────────────────────────────────
def opportunity_score(monthly: dict, sim: dict) -> dict:
    if not monthly:
        return {"score": 0, "grade": "F", "reason": "insufficient data"}
    avg_trades = sum(d["trades"] for d in monthly.values()) / len(monthly)
    min_trades = min(d["trades"] for d in monthly.values())
    profitable = sum(1 for d in monthly.values() if d["net_pnl_001"] > 0) / len(monthly)
    dd = sim.get("max_dd_pct_001", 0)

    score = 0
    score += min(avg_trades / 100, 1) * 30   # 30% trade frequency
    score += profitable * 30                   # 30% profitable months
    score += max(0, (5 - dd) / 5) * 25         # 25% low DD
    score += min(min_trades / 20, 1) * 15       # 15% consistency
    score = round(score * 10) / 10

    if score >= 80:
        grade = "A"
    elif score >= 60:
        grade = "B"
    elif score >= 40:
        grade = "C"
    else:
        grade = "D"
    return {"score": score, "grade": grade}


# ── Main ───────────────────────────────────────────────────
def main(args):
    cd = Path(__file__).parent.parent  # trade_strategy_analyzer/
    csv_dir = cd / args.csv_dir
    out_dir = cd / args.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    pdef = None
    for p in PORTFOLIO_DEFS:
        if p["id"] == args.portfolio:
            pdef = p
            break
    if not pdef:
        log.error(f"Portfolio {args.portfolio} not found")
        return

    log.info(f"Generating Portfolio {pdef['id']} ({pdef['name']}) with signals: {pdef['signals']}")

    # Load and analyze each signal
    signal_analyses = []
    all_trades_combined = []
    signal_monthly_list = []

    for sid in pdef["signals"]:
        trades = load_signal_csv(sid, str(csv_dir))
        if not trades:
            log.warning(f"No CSV data for Signal {sid}, skipping")
            continue
        stats = calc_signal_stats(trades)
        monthly = monthly_analysis(trades)
        sim = sequential_simulation(trades)
        opp = opportunity_score(monthly, sim)

        signal_analyses.append({
            "signal_id": sid,
            "stats": stats,
            "monthly": monthly,
            "simulation": sim,
            "opportunity": opp,
        })
        all_trades_combined.extend(
            {"**signal_id**": sid, **t} for t in trades
        )
        signal_monthly_list.append({"signal_id": sid, "monthly": monthly})
        log.info(f"  Signal {sid}: {stats['count']} trades, WR={stats['win_rate']}%, PF={stats['profit_factor']}")

    if not signal_analyses:
        log.error("No signal data found")
        return

    # Portfolio-level sequential sim (combined)
    portfolio_sim = sequential_simulation(all_trades_combined)

    # Correlation
    correlations = portfolio_correlation(signal_monthly_list)

    # TP/SL for each signal
    tpsl_list = []
    for sa in signal_analyses:
        tpsl = calculate_tpsl(sa["stats"], pdef["capital"], pdef["risk_pct"], sa["signal_id"])
        tpsl_list.append(tpsl)

    # Generate HTML
    html = generate_unified_html(pdef, signal_analyses, portfolio_sim, correlations, tpsl_list)

    # Write output
    out_path = out_dir / f"portfolio_{pdef['id']}.html"
    out_path.write_text(html, encoding="utf-8")
    size = out_path.stat().st_size
    log.info(f"✅ Generated: {out_path} ({size:,} bytes)")
    print(f"Output: {out_path} ({size:,} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Portfolio Unified Generator")
    parser.add_argument("--portfolio", default="P1", help="Portfolio ID (e.g. P1)")
    parser.add_argument("--csv-dir", default="samples", help="CSV directory")
    parser.add_argument("--output-dir", default="docs/admin/portfolios", help="Output directory")
    args = parser.parse_args()
    main(args)
