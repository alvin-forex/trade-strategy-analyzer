#!/usr/bin/env python3
"""
Portfolio HTML Report Generator
Generates 10 portfolio reports with signal analysis, lot calculations, and risk assessment.

Usage:
    python3 scripts/generate_portfolios.py
"""

import json
import os
import glob
from datetime import datetime
from pathlib import Path

# ─── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
HISTORY_DIR = BASE_DIR / "data" / "history"
REPORTS_DIR = BASE_DIR / "docs" / "reports"
OUTPUT_DIR = BASE_DIR / "docs" / "portfolios"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


# ─── Data Loading ───────────────────────────────────────────────────────────
def load_all_signals():
    """Load and compute aggregate statistics for every signal."""
    signals = {}
    for f in sorted(HISTORY_DIR.glob("signal_*.json")):
        sid = f.stem.replace("signal_", "")
        with open(f) as fh:
            raw = json.load(fh)

        trades = raw.get("trades", [])
        if not trades:
            continue

        # Per-symbol aggregation
        sym_map = {}
        for t in trades:
            sym = t.get("Symbol", "")
            if not sym or sym == "profit":
                continue
            if sym not in sym_map:
                sym_map[sym] = {"count": 0, "pnl": 0.0, "wins": 0, "pips": 0.0}
            sym_map[sym]["count"] += 1
            sym_map[sym]["pnl"] += float(t.get("Net Profit", 0))
            sym_map[sym]["pips"] += float(t.get("Net Pips", 0))
            if float(t.get("Net Profit", 0)) > 0:
                sym_map[sym]["wins"] += 1

        top_syms = sorted(sym_map.items(), key=lambda x: x[1]["count"], reverse=True)

        buys = len([t for t in trades if t.get("Type") == "buy"])
        sells = len([t for t in trades if t.get("Type") == "sell"])

        # Max drawdown
        run = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in trades:
            run += float(t.get("Net Profit", 0))
            peak = max(peak, run)
            max_dd = max(max_dd, peak - run)

        lots_list = [float(t.get("Lots", 0)) for t in trades if t.get("Lots")]
        avg_lot = sum(lots_list) / len(lots_list) if lots_list else 0.01

        gp = sum(float(t.get("Net Profit", 0)) for t in trades if float(t.get("Net Profit", 0)) > 0)
        gl = abs(sum(float(t.get("Net Profit", 0)) for t in trades if float(t.get("Net Profit", 0)) < 0))
        pf = gp / gl if gl > 0 else 0.0

        # Session breakdown (approximate from open hour)
        london_n = ny_n = asia_n = 0
        for t in trades:
            ot = t.get("Open Time", "")
            try:
                h = int(ot.split(" ")[1].split(":")[0])
                if 7 <= h <= 13:
                    london_n += 1
                elif 14 <= h <= 21:
                    ny_n += 1
                else:
                    asia_n += 1
            except (IndexError, ValueError):
                pass
        tot = len(trades) or 1

        signals[sid] = {
            "signal_id": sid,
            "ea": raw.get("ea", "UNK"),
            "trade_count": raw.get("trade_count", len(trades)),
            "total_pnl": round(raw.get("summary", {}).get("total_pnl", 0), 2),
            "total_pips": round(raw.get("summary", {}).get("total_pips", 0), 1),
            "win_rate": round(raw.get("summary", {}).get("win_rate", 0), 1),
            "avg_hold_hours": round(raw.get("summary", {}).get("avg_hold_hours", 0), 1),
            "buy_count": buys,
            "sell_count": sells,
            "max_dd": round(max_dd, 2),
            "avg_lot": round(avg_lot, 3),
            "profit_factor": round(pf, 2),
            "symbol_count": len(sym_map),
            "top_symbols": [
                (s, v["count"], round(v["pnl"], 0), round(v["wins"] / v["count"] * 100, 1) if v["count"] else 0)
                for s, v in top_syms[:8]
            ],
            "london_pct": round(london_n / tot * 100, 1),
            "ny_pct": round(ny_n / tot * 100, 1),
            "asia_pct": round(asia_n / tot * 100, 1),
            "has_report": (REPORTS_DIR / f"Signal_Deep_Analysis_{sid}.html").exists(),
        }

    return signals


# ─── Lot Calculation ────────────────────────────────────────────────────────
def calc_lots(capital, risk_pct, stop_pips, pip_value=10.0):
    """
    Lot = (capital × risk%) / (stop_pips × pip_value)
    Returns (lots, risk_amount).
    """
    risk_amount = capital * risk_pct / 100
    lots = risk_amount / (stop_pips * pip_value)
    return round(lots, 2), round(risk_amount, 2)


def risk_tier(capital, max_dd, total_lots):
    """Classify risk level."""
    dd_ratio = max_dd / capital if capital else 1
    if dd_ratio < 0.3 and total_lots <= 0.05:
        return "Low", "risk-low"
    elif dd_ratio < 0.7:
        return "Medium", "risk-medium"
    else:
        return "High", "risk-high"


# ─── EA Colors ──────────────────────────────────────────────────────────────
EA_COLORS = {
    "DW":   ("#4a148c", "#ce93d8"),
    "SMA":  ("#0d47a1", "#90caf9"),
    "MKD":  ("#b71c1c", "#ef9a9a"),
    "GEM":  ("#1b5e20", "#a5d6a7"),
    "S10":  ("#e65100", "#ffcc80"),
    "Flash":("#4a148c", "#b39ddb"),
    "MAN":  ("#263238", "#90a4ae"),
    "UNK":  ("#424242", "#9e9e9e"),
}

def ea_badge(ea):
    bg, fg = EA_COLORS.get(ea, EA_COLORS["UNK"])
    return f'<span class="ea-badge" style="background:{bg};color:{fg}">{ea}</span>'


# ─── HTML Template ─────────────────────────────────────────────────────────
CSS = """
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,'Segoe UI',sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}
.container{max-width:1100px;margin:auto}
h1{color:#58a6ff;font-size:1.4em;margin-bottom:6px}
h2{color:#58a6ff;font-size:1.05em;border-bottom:1px solid #21262d;padding-bottom:6px;margin-bottom:10px}
h3{color:#8b949e;font-size:0.9em;margin:14px 0 6px}
.meta{color:#8b949e;font-size:0.8em;margin-bottom:16px}
.section{background:#161b22;border-radius:8px;padding:16px;margin-bottom:14px;border:1px solid #21262d}
table{width:100%;border-collapse:collapse;margin-top:8px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid #21262d;font-size:0.85em}
th{color:#8b949e;font-weight:600;text-transform:uppercase;font-size:0.75em;letter-spacing:0.5px}
tr:hover{background:#1c2128}
.positive{color:#3fb950}
.negative{color:#f85149}
.signal-link{color:#58a6ff;text-decoration:none;font-weight:500}
.signal-link:hover{text-decoration:underline}
.ea-badge{display:inline-block;padding:2px 7px;border-radius:4px;font-size:0.7em;font-weight:600}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;margin-top:8px}
.stat-card{background:#21262d;border-radius:6px;padding:10px}
.stat-label{color:#8b949e;font-size:0.7em;margin-bottom:3px;text-transform:uppercase;letter-spacing:0.3px}
.stat-value{font-size:1.15em;font-weight:600}
.calc-box{background:#21262d;border-radius:6px;padding:12px;margin:6px 0;font-family:'Fira Code','Consolas',monospace;font-size:0.85em;line-height:1.6}
.calc-step{color:#8b949e}
.calc-formula{color:#d29922;font-weight:500}
.calc-result{color:#3fb950;font-size:1.1em;font-weight:600;margin-top:4px}
.risk-low{color:#3fb950}
.risk-medium{color:#d29922}
.risk-high{color:#f85149}
ul{margin-left:18px;margin-top:6px}
li{margin:3px 0;font-size:0.85em;line-height:1.5}
.dir-buy{color:#3fb950}
.dir-sell{color:#f85149}
.pct-bar{display:inline-block;width:60px;height:6px;background:#21262d;border-radius:3px;overflow:hidden;vertical-align:middle;margin-left:4px}
.pct-fill{height:100%;border-radius:3px}
.footer{color:#484f58;font-size:0.75em;text-align:center;margin-top:20px;padding:10px}
"""


def generate_portfolio_html(pid, config, signals):
    """Generate a single portfolio HTML page."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    capital = config["capital"]
    target = config["target"]
    strategy = config["strategy"]
    sig_ids = config["signals"]

    # Collect signal data
    sig_data = []
    for sid in sig_ids:
        s = signals.get(str(sid))
        if s:
            sig_data.append(s)

    if not sig_data:
        return f"<!-- No data for Portfolio {pid} -->"

    # Aggregate stats
    avg_wr = sum(s["win_rate"] for s in sig_data) / len(sig_data)
    total_pnl = sum(s["total_pnl"] for s in sig_data)
    total_trades = sum(s["trade_count"] for s in sig_data)
    total_max_dd = sum(s["max_dd"] for s in sig_data)

    # Determine risk per trade based on strategy
    if "低風險" in strategy or "Low" in strategy:
        risk_per_trade = 1.5
    elif "激進" in strategy or "Aggressive" in strategy:
        risk_per_trade = 3.0
    else:
        risk_per_trade = 2.0

    # Lot calculations
    lot_calcs = []
    for s in sig_data:
        stop_pips = max(s["avg_lot"] * 100, 30)  # Estimate stop from avg lot data
        # Use max_dd-based estimate for stop loss
        if s["trade_count"] > 0:
            est_sl_pips = max(int(s["max_dd"] / s["trade_count"] * 10), 25)
        else:
            est_sl_pips = 50
        est_sl_pips = min(est_sl_pips, 200)  # Cap at 200 pips

        lots, risk_amt = calc_lots(capital, risk_per_trade, est_sl_pips)
        lot_calcs.append({
            "signal_id": s["signal_id"],
            "ea": s["ea"],
            "stop_pips": est_sl_pips,
            "risk_amount": risk_amt,
            "lots": lots,
            "ccy": s["top_symbols"][0][0] if s["top_symbols"] else "N/A",
        })

    total_lots = sum(lc["lots"] for lc in lot_calcs)
    risk_level, risk_class = risk_tier(capital, total_max_dd, total_lots)

    # Expected monthly PnL (project from historical avg)
    # Simple projection: avg monthly pnl per signal * lot adjustment factor
    lot_factor = total_lots / max(sig_data[0]["avg_lot"], 0.01) if sig_data else 1
    months_in_data = max(total_trades / 200, 1)  # rough estimate
    historical_monthly = total_pnl / months_in_data
    projected_monthly = historical_monthly * (capital / 10000)  # scale to capital

    # ── Build HTML ──────────────────────────────────────────────────────────
    html_parts = [
        f'<!DOCTYPE html>',
        f'<html lang="zh-Hant">',
        f'<head>',
        f'<meta charset="UTF-8">',
        f'<meta name="viewport" content="width=device-width, initial-scale=1.0">',
        f'<title>Portfolio {pid} | {config["name"]}</title>',
        f'<style>{CSS}</style>',
        f'</head>',
        f'<body>',
        f'<div class="container">',
        # Header
        f'<h1>📊 Portfolio {pid}: {config["name"]}</h1>',
        f'<div class="meta">生成時間：{ts} | 策略：{strategy} | EA 類型：{", ".join(sorted(set(s["ea"] for s in sig_data)))} | 風險等級：<span class="{risk_class}">{risk_level}</span></div>',
    ]

    # ── Overview ────────────────────────────────────────────────────────────
    html_parts.append(f'<div class="section">')
    html_parts.append(f'<h2>📋 Portfolio 概述</h2>')
    html_parts.append(f'<div class="stat-grid">')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">投入資金</div><div class="stat-value">${capital:,}</div></div>')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">目標報酬</div><div class="stat-value">{target}</div></div>')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">信號數量</div><div class="stat-value">{len(sig_data)}</div></div>')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">平均勝率</div><div class="stat-value {"positive" if avg_wr > 65 else "negative"}">{avg_wr:.1f}%</div></div>')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">總交易數</div><div class="stat-value">{total_trades:,}</div></div>')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">歷史總盈虧</div><div class="stat-value positive">${total_pnl:,.0f}</div></div>')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">每筆風險</div><div class="stat-value">{risk_per_trade}%</div></div>')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">總手數</div><div class="stat-value">{total_lots:.2f} lots</div></div>')
    html_parts.append(f'</div>')
    html_parts.append(f'</div>')

    # ── Signal Details Table ────────────────────────────────────────────────
    html_parts.append(f'<div class="section">')
    html_parts.append(f'<h2>📈 信號明細</h2>')
    html_parts.append(f'<table><thead><tr>'
                      f'<th>Signal ID</th><th>EA</th><th>主要CCY</th><th>方向</th>'
                      f'<th>Trades</th><th>Win Rate</th><th>PnL</th><th>Pips</th>'
                      f'<th>PF</th><th>Max DD</th><th>符號數</th>'
                      f'</tr></thead><tbody>')

    for s in sig_data:
        # Primary symbol
        primary_sym = s["top_symbols"][0][0] if s["top_symbols"] else "N/A"
        # Direction
        if s["buy_count"] > s["sell_count"] * 1.2:
            direction = '<span class="dir-buy">▲ Buy偏多</span>'
        elif s["sell_count"] > s["buy_count"] * 1.2:
            direction = '<span class="dir-sell">▼ Sell偏多</span>'
        else:
            direction = '<span style="color:#8b949e">◆ 雙向</span>'

        # Signal link
        if s["has_report"]:
            sig_link = f'<a href="../reports/Signal_Deep_Analysis_{s["signal_id"]}.html" class="signal-link">{s["signal_id"]}</a>'
        else:
            sig_link = f'<span class="signal-link">{s["signal_id"]}</span>'

        wr_class = "positive" if s["win_rate"] >= 70 else ("risk-medium" if s["win_rate"] >= 60 else "negative")
        dd_val = f'${s["max_dd"]:,.0f}'

        html_parts.append(
            f'<tr>'
            f'<td>{sig_link}</td>'
            f'<td>{ea_badge(s["ea"])}</td>'
            f'<td>{primary_sym}</td>'
            f'<td>{direction}</td>'
            f'<td>{s["trade_count"]:,}</td>'
            f'<td class="{wr_class}">{s["win_rate"]:.1f}%</td>'
            f'<td class="positive">${s["total_pnl"]:,.0f}</td>'
            f'<td>{s["total_pips"]:,.0f}</td>'
            f'<td>{s["profit_factor"]:.2f}</td>'
            f'<td class="negative">{dd_val}</td>'
            f'<td>{s["symbol_count"]}</td>'
            f'</tr>'
        )

    html_parts.append(f'</tbody></table>')
    html_parts.append(f'</div>')

    # ── Per-Signal Detail Cards ─────────────────────────────────────────────
    html_parts.append(f'<div class="section">')
    html_parts.append(f'<h2>🔍 信號深度分析</h2>')
    for s in sig_data:
        primary_sym = s["top_symbols"][0][0] if s["top_symbols"] else "N/A"
        top3 = s["top_symbols"][:4]
        direction = "Buy" if s["buy_count"] > s["sell_count"] else "Sell"

        html_parts.append(f'<h3>{ea_badge(s["ea"])} Signal {s["signal_id"]} — {primary_sym} ({direction})</h3>')
        html_parts.append(f'<table><thead><tr><th>貨幣對</th><th>交易次數</th><th>盈虧</th><th>勝率</th><th>佔比</th></tr></thead><tbody>')
        total_sym_trades = sum(v[1] for v in top3) or 1
        for sym, cnt, pnl, wr in top3:
            pct = cnt / total_sym_trades * 100
            bar_color = "#3fb950" if pnl >= 0 else "#f85149"
            html_parts.append(
                f'<tr><td>{sym}</td><td>{cnt}</td>'
                f'<td class="{"positive" if pnl >= 0 else "negative"}">${pnl:,.0f}</td>'
                f'<td>{wr:.1f}%</td>'
                f'<td>{pct:.1f}%<span class="pct-bar"><span class="pct-fill" style="width:{min(pct,100):.0f}%;background:{bar_color}"></span></span></td>'
                f'</tr>'
            )
        html_parts.append(f'</tbody></table>')

        # Session info
        html_parts.append(
            f'<div style="margin:6px 0;font-size:0.8em;color:#8b949e">'
            f'📊 持倉時間: {s["avg_hold_hours"]:.1f}h | '
            f'🌍 London: {s["london_pct"]:.0f}% | NY: {s["ny_pct"]:.0f}% | Asia: {s["asia_pct"]:.0f}% | '
            f'📏 平均手數: {s["avg_lot"]}'
            f'</div>'
        )
    html_parts.append(f'</div>')

    # ── Lot Calculation ─────────────────────────────────────────────────────
    html_parts.append(f'<div class="section">')
    html_parts.append(f'<h2>🧮 手數計算過程</h2>')
    html_parts.append(f'<p style="font-size:0.85em;color:#8b949e;margin-bottom:8px">')
    html_parts.append(f'<strong>公式：</strong> 建議手數 = (帳戶餘額 × 風險百分比) / (止損點數 × 點值)')
    html_parts.append(f'</p>')

    for lc, s in zip(lot_calcs, sig_data):
        html_parts.append(f'<div class="calc-box">')
        html_parts.append(f'<div class="calc-step">📌 Signal {lc["signal_id"]} ({lc["ea"]} / {lc["ccy"]})</div>')
        html_parts.append(f'<div class="calc-step">  帳戶餘額 = ${capital:,}</div>')
        html_parts.append(f'<div class="calc-step">  風險百分比 = {risk_per_trade}% → 風險金額 = ${lc["risk_amount"]}</div>')
        html_parts.append(f'<div class="calc-step">  止損點數 = {lc["stop_pips"]} pips（基於歷史 Max DD 推算）</div>')
        html_parts.append(f'<div class="calc-step">  點值 (pip value) = $10/pip（標準手）</div>')
        html_parts.append(f'<div class="calc-formula">  → (${capital:,} × {risk_per_trade}%) / ({lc["stop_pips"]} × $10) = {lc["lots"]:.2f} lots</div>')
        html_parts.append(f'<div class="calc-result">  ✅ 建議手數：{lc["lots"]:.2f} lots</div>')
        html_parts.append(f'</div>')

    html_parts.append(f'</div>')

    # ── Risk Assessment ─────────────────────────────────────────────────────
    html_parts.append(f'<div class="section">')
    html_parts.append(f'<h2>⚠️ 風險評估</h2>')
    html_parts.append(f'<div class="stat-grid">')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">最大回撤（合計）</div><div class="stat-value negative">${total_max_dd:,.0f}</div></div>')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">回撤/資金比</div><div class="stat-value {risk_class}">{total_max_dd/capital*100:.1f}%</div></div>')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">爆倉風險</div><div class="stat-value {risk_class}">{risk_level}</div></div>')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">保證金需求</div><div class="stat-value">${total_lots*1000:,.0f}</div></div>')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">預期月盈虧</div><div class="stat-value positive">${projected_monthly:,.0f}</div></div>')
    html_parts.append(f'<div class="stat-card"><div class="stat-label">月報酬率</div><div class="stat-value {"positive" if projected_monthly/capital*100 > 10 else "risk-medium"}">{projected_monthly/capital*100:.1f}%</div></div>')
    html_parts.append(f'</div>')

    html_parts.append(f'<h3>💡 風險管理建議</h3>')
    html_parts.append(f'<ul>')
    html_parts.append(f'<li><strong>每層風險控制：</strong>單筆交易風險不超過帳戶的 {risk_per_trade}%（${capital*risk_per_trade/100:,.0f}）</li>')
    html_parts.append(f'<li><strong>每日止損：</strong>日虧損超過 ${capital*0.05:,.0f}（5%）即停止交易</li>')
    html_parts.append(f'<li><strong>層數控制：</strong>建議 L1-L3 分層進場，總手持倉不超過 {total_lots:.2f} lots</li>')
    if risk_level == "High":
        html_parts.append(f'<li style="color:#f85149"><strong>高風險警告：</strong>歷史回撤較大，建議降低手數或增加資金至 ${total_max_dd*0.3:,.0f}</li>')
    elif risk_level == "Medium":
        html_parts.append(f'<li style="color:#d29922"><strong>中風險提示：</strong>注意分批進場，避免同時開啟所有信號</li>')
    else:
        html_parts.append(f'<li style="color:#3fb950"><strong>低風險：</strong>倉位控制得宜，可適度放寬手數</li>')
    html_parts.append(f'<li><strong>重要數據迴避：</strong>NFP、CPI、FOMC 前 30 分鐘暫停開倉</li>')
    html_parts.append(f'<li><strong>定期檢視：</strong>每週五收盤後檢視 Portfolio 表現並調整權重</li>')
    html_parts.append(f'</ul>')
    html_parts.append(f'</div>')

    # ── Recommended Settings ────────────────────────────────────────────────
    html_parts.append(f'<div class="section">')
    html_parts.append(f'<h2>⚙️ 建議設定</h2>')
    html_parts.append(f'<table><thead><tr><th>參數</th><th>設定值</th><th>說明</th></tr></thead><tbody>')
    html_parts.append(f'<tr><td>資金</td><td>${capital:,}</td><td>起始帳戶餘額</td></tr>')
    html_parts.append(f'<tr><td>基礎手數</td><td>{min(lot_calcs[0]["lots"], 0.05):.2f} lots</td><td>L1 首層進場手數</td></tr>')
    html_parts.append(f'<tr><td>加倉倍數</td><td>1.5x</td><td>L2 = L1 × 1.5, L3 = L2 × 1.5</td></tr>')
    html_parts.append(f'<tr><td>止損模式</td><td>追蹤止損</td><td>盈利 30 pips 後移至保本</td></tr>')
    html_parts.append(f'<tr><td>止盈模式</td><td>分批止盈</td><td>50% @ TP1, 30% @ TP2, 20% @ TP3</td></tr>')
    html_parts.append(f'<tr><td>最大持倉</td><td>{len(sig_data)} 個</td><td>同時持有的最大信號數</td></tr>')
    html_parts.append(f'<tr><td>風險限制</td><td>{risk_per_trade}% / 筆</td><td>單筆最大風險</td></tr>')
    html_parts.append(f'<tr><td>日止損</td><td>${capital*0.05:,.0f} (5%)</td><td>單日最大虧損</td></tr>')
    html_parts.append(f'<tr><td>週止損</td><td>${capital*0.10:,.0f} (10%)</td><td>單週最大虧損</td></tr>')
    html_parts.append(f'</tbody></table>')
    html_parts.append(f'</div>')

    # ── Footer ──────────────────────────────────────────────────────────────
    html_parts.append(f'<div class="footer">')
    html_parts.append(f'Generated by Trade Strategy Analyzer | {ts}')
    html_parts.append(f'<br>Model: ZAI GLM-5.2 | Data source: Forex Forest Signals')
    html_parts.append(f'</div>')

    html_parts.append(f'</div></body></html>')

    return "\n".join(html_parts)


# ─── Portfolio Configurations ───────────────────────────────────────────────
def get_portfolio_configs(signals):
    """Define all 10 portfolio configurations."""

    # Get top DW signals
    dw_sigs = sorted(
        [(sid, s) for sid, s in signals.items() if s["ea"] == "DW"],
        key=lambda x: x[1]["total_pnl"],
        reverse=True
    )
    # Get top SMA signals
    sma_sigs = sorted(
        [(sid, s) for sid, s in signals.items() if s["ea"] == "SMA"],
        key=lambda x: x[1]["total_pnl"],
        reverse=True
    )
    # Get MKD signals
    mkd_sigs = sorted(
        [(sid, s) for sid, s in signals.items() if s["ea"] == "MKD"],
        key=lambda x: x[1]["total_pnl"],
        reverse=True
    )
    # GBPCAD-heavy signals
    gbpcad_sigs = sorted(
        [(sid, s) for sid, s in signals.items()
         if any(sym[0] == "GBPCAD" for sym in s["top_symbols"][:3])],
        key=lambda x: x[1]["total_pnl"],
        reverse=True
    )[:4]
    # London-heavy signals
    london_sigs = sorted(
        [(sid, s) for sid, s in signals.items() if s["london_pct"] > 35],
        key=lambda x: x[1]["london_pct"],
        reverse=True
    )[:4]
    # NY-heavy signals
    ny_sigs = sorted(
        [(sid, s) for sid, s in signals.items() if s["ny_pct"] > 38],
        key=lambda x: x[1]["ny_pct"],
        reverse=True
    )[:4]

    # Top 10 by PnL overall
    top10 = sorted(signals.items(), key=lambda x: x[1]["total_pnl"], reverse=True)[:10]
    top10_ids = [s[0] for s in top10]

    # Top 5 DW + Top 5 SMA
    top5_dw = [s[0] for s in dw_sigs[:5]]
    top5_sma = [s[0] for s in sma_sigs[:5]]

    return {
        "P1": {
            "name": "DW 高勝率組",
            "capital": 1500,
            "target": "月 50%",
            "strategy": "DW EA 高勝率策略，選擇歷史勝率 > 72% 的 Dragon Wave 信號",
            "signals": ["31593", "17547", "3291"],
        },
        "P2": {
            "name": "SMA 穩定增長組",
            "capital": 1000,
            "target": "週 20%",
            "strategy": "SMA EA 穩定策略，選擇長期穩定盈利的 Smart Moving Average 信號",
            "signals": ["16698", "32278", "5001"],
        },
        "P3": {
            "name": "MKD 激進增長組",
            "capital": 2000,
            "target": "月 50%",
            "strategy": "MKD EA 激進策略，高風險高報酬的 Macdee 信號組合",
            "signals": ["23617", "10843"] if "10843" in signals else [s[0] for s in mkd_sigs[:2]],
        },
        "P4": {
            "name": "GBPCAD 專攻組",
            "capital": 1200,
            "target": "週 20%",
            "strategy": "GBPCAD 貨幣對專注策略，選擇 GBPCAD 交易佔比最高的信號",
            "signals": [s[0] for s in gbpcad_sigs[:4]],
        },
        "P5": {
            "name": "XAUUSD 黃金組",
            "capital": 1500,
            "target": "月 50%",
            "strategy": "XAUUSD 黃金交易專攻，捕捉黃金大波動的信號組合",
            "signals": ["5117", "27226"] if "27226" in signals else ["5117", "32541"],
        },
        "P6": {
            "name": "低風險平注組",
            "capital": 1000,
            "target": "週 15%",
            "strategy": "低風險均注策略，每筆固定 1.5% 風險，選擇高勝率信號",
            "signals": ["30359", "33101", "17547"],
        },
        "P7": {
            "name": "多CCY分散組",
            "capital": 2000,
            "target": "月 40%",
            "strategy": "多貨幣對分散策略，Top 10 信號跨 EA 類型組合",
            "signals": top10_ids[:10],
        },
        "P8": {
            "name": "London 時段組",
            "capital": 1200,
            "target": "週 20%",
            "strategy": "倫敦交易時段專攻，選擇 London session 活躍度最高的信號",
            "signals": [s[0] for s in london_sigs[:4]],
        },
        "P9": {
            "name": "NY 時段組",
            "capital": 1500,
            "target": "月 50%",
            "strategy": "紐約交易時段專攻，選擇 NY session 活躍度最高的信號",
            "signals": [s[0] for s in ny_sigs[:4]],
        },
        "P10": {
            "name": "混合策略組",
            "capital": 1800,
            "target": "月 45%",
            "strategy": "混合策略組合，Top 5 DW + Top 5 SMA 跨 EA 分散",
            "signals": top5_dw + top5_sma,
        },
    }


# ─── Main ───────────────────────────────────────────────────────────────────
def main():
    print("Loading signal data...")
    signals = load_all_signals()
    print(f"  → {len(signals)} signals loaded")

    configs = get_portfolio_configs(signals)

    for pid, cfg in configs.items():
        print(f"Generating Portfolio {pid}: {cfg['name']}...")
        html = generate_portfolio_html(pid, cfg, signals)
        out_path = OUTPUT_DIR / f"portfolio_{pid}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"  → {out_path.name} ({len(html):,} bytes)")

    print(f"\n✅ All 10 portfolios generated in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
