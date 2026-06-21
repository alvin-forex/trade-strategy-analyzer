#!/usr/bin/env python3
"""
Portfolio V2 Analyzer
=====================
方案 B + D 混合分析引擎：
  B → 順序保留回測 (Walk-Forward Sequential Simulation)
  D → 組合內信號相關性分析

Output: 月度統計、順序回測資金曲線、組合相關性矩陣、機會評分
"""

import csv
import os
import json
import math
from datetime import datetime, date
from collections import defaultdict

# ──────────────────────────────────────────
# 1. CSV 讀取
# ──────────────────────────────────────────

BALANCE_KEYWORDS = frozenset(("balance", "deposit", "withdrawal", "transfer", "bonus"))

def load_signal_csv(signal_id: str, csv_dir: str = "downloads") -> list[dict]:
    """讀取單一 signal 嘅 CSV，回傳 list of trades（排除 balance/transfer 類交易）"""
    path = f"{csv_dir}/forex-forest-signals-page-{signal_id}.csv"
    if not os.path.exists(path):
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


# ──────────────────────────────────────────
# 2. 月度統計
# ──────────────────────────────────────────

def parse_month(ts: str) -> str:
    """抽出月份，支援 'YYYY-MM-DD' 及 AlgoForest CSV 嘅 'DD/MM/YYYY HH:MM:SS'"""
    if not ts:
        return None
    ts = ts.strip()
    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
    ]
    for fmt in formats:
        try:
            probe = ts[:10] if fmt in ("%Y-%m-%d", "%d/%m/%Y") else ts
            dt = datetime.strptime(probe, fmt)
            return dt.strftime("%Y-%m")
        except ValueError:
            continue
    return None


def monthly_analysis(trades: list[dict], min_trades: int = 2) -> dict:
    """
    按月份統計交易頻率 / 勝率 / 盈虧 / Profit Factor
    """
    if not trades:
        return {"error": "no trades"}

    # 剔除 header row（如有 Net Profit 標題列）
    raw = [t for t in trades if isinstance(t.get("net_profit"), (int, float))]
    if not raw:
        return {"error": "no numeric trades"}

    # 按月份分組
    monthly = defaultdict(list)
    for t in raw:
        m = parse_month(t.get("close_time") or t.get("open_time"))
        if m:
            monthly[m].append(t)

    if not monthly:
        return {"error": "no valid dates"}

    months_sorted = sorted(monthly.keys())
    monthly_stats = []
    for m in months_sorted:
        mtrades = monthly[m]
        if len(mtrades) < min_trades:
            continue
        wins = [t for t in mtrades if t["net_profit"] > 0]
        losses = [t for t in mtrades if t["net_profit"] <= 0]
        total_pnl = sum(t["net_profit"] for t in mtrades)
        total_pips = sum(t["net_pips"] for t in mtrades)
        win_rate = len(wins) / len(mtrades) if mtrades else 0
        avg_win = sum(t["net_profit"] for t in wins) / len(wins) if wins else 0
        avg_loss = sum(t["net_profit"] for t in losses) / len(losses) if losses else abs(sum(t["net_profit"] for t in losses)) / len(losses) if losses else 0
        pf = sum(t["net_profit"] for t in wins) / abs(sum(t["net_profit"] for t in losses)) if losses and sum(t["net_profit"] for t in losses) != 0 else (99 if wins else 0)
        
        monthly_stats.append({
            "month": m,
            "trades": len(mtrades),
            "win_rate": round(win_rate * 100, 1),
            "total_pnl": round(total_pnl, 2),
            "total_pips": round(total_pips, 1),
            "avg_pnl": round(total_pnl / len(mtrades), 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "profit_factor": round(pf, 2),
            "avg_lots": round(sum(t["lots"] for t in mtrades) / len(mtrades), 3),
            "wins": len(wins),
            "losses": len(losses),
        })

    # 近 3 個月
    recent3 = monthly_stats[-3:] if len(monthly_stats) >= 3 else monthly_stats
    recent3_trades = sum(m["trades"] for m in recent3)
    recent3_pnl = sum(m["total_pnl"] for m in recent3)
    recent3_win_trades = sum(m["wins"] for m in recent3)
    recent3_total = sum(m["trades"] for m in recent3)
    recent3_win_rate = (recent3_win_trades / recent3_total * 100) if recent3_total > 0 else 0

    # 連續虧損月份
    max_consec_loss_months = 0
    cur = 0
    for m in monthly_stats:
        if m["total_pnl"] < 0:
            cur += 1
            max_consec_loss_months = max(max_consec_loss_months, cur)
        else:
            cur = 0

    profitable_months = sum(1 for m in monthly_stats if m["total_pnl"] > 0)
    
    total_trades = sum(m["trades"] for m in monthly_stats)

    return {
        "signal_id": "",  # caller fills
        "total_trades": total_trades,
        "total_months": len(months_sorted),
        "active_months": len(monthly_stats),
        "profitable_months": profitable_months,
        "profitable_month_pct": round(profitable_months / len(monthly_stats) * 100, 1) if monthly_stats else 0,
        "max_consec_loss_months": max_consec_loss_months,
        "avg_monthly_trades": round(total_trades / len(monthly_stats), 1) if monthly_stats else 0,
        "median_monthly_trades": round(sorted([m["trades"] for m in monthly_stats])[len(monthly_stats)//2], 1) if monthly_stats else 0,
        "min_monthly_trades": min(m["trades"] for m in monthly_stats) if monthly_stats else 0,
        "last_month_trades": monthly_stats[-1]["trades"] if monthly_stats else 0,
        "last_month_pnl": monthly_stats[-1]["total_pnl"] if monthly_stats else 0,
        "last_month_win_rate": monthly_stats[-1]["win_rate"] if monthly_stats else 0,
        "best_month_pnl": max(m["total_pnl"] for m in monthly_stats) if monthly_stats else 0,
        "worst_month_pnl": min(m["total_pnl"] for m in monthly_stats) if monthly_stats else 0,
        "avg_monthly_pnl": round(sum(m["total_pnl"] for m in monthly_stats) / len(monthly_stats), 2) if monthly_stats else 0,
        "median_monthly_pnl": round(sorted([m["total_pnl"] for m in monthly_stats])[len(monthly_stats)//2], 2) if monthly_stats else 0,
        "recent_3mo_trades": recent3_trades,
        "recent_3mo_pnl": round(recent3_pnl, 2),
        "recent_3mo_avg_trades": round(recent3_trades / len(recent3), 1) if recent3 else 0,
        "recent_3mo_avg_pnl": round(recent3_pnl / len(recent3), 2) if recent3 else 0,
        "recent_3mo_win_rate": round(recent3_win_rate, 1),
        "monthly_stats": monthly_stats,
    }


# ──────────────────────────────────────────
# 3. 順序保留回測 (Walk-Forward)
# ──────────────────────────────────────────

def sequential_simulation(
    trades: list[dict],
    capital: float = None,
    risk_pct: float = 2.0,
    sl_pips: float = 25,
    use_layers: bool = True,
    max_layers: int = 3,
) -> dict:
    """
    按月順序回測（Outcome-based，V2 修正版）：
    - 逐月匯總原始 Signal 交易結果
    - 轉換為 per-001 lot PnL（可 scale）
    - 計算月度勝率/DD/連續虧損月份
    - 不乘以 portfolio 手數（留俾用戶按自己 lot 決定資本需求）
    """
    raw = [t for t in trades if isinstance(t.get("net_profit"), (int, float)) and t.get("symbol")]
    if not raw:
        return {"error": "no valid trades"}

    from collections import defaultdict
    monthly_pnl_001 = defaultdict(float)
    monthly_wins = defaultdict(int)
    monthly_losses = defaultdict(int)
    monthly_pips = defaultdict(float)
    monthly_trade_count = defaultdict(int)

    for t in raw:
        original_lot = max(t["lots"], 0.01)
        pnl_per_001 = t["net_profit"] / original_lot * 0.01
        pips_per_001 = t["net_pips"] / original_lot * 0.01
        m = parse_month(t.get("close_time") or t.get("open_time"))
        if m:
            monthly_pnl_001[m] += pnl_per_001
            monthly_pips[m] += pips_per_001
            monthly_trade_count[m] += 1
            if pnl_per_001 > 0:
                monthly_wins[m] += 1
            else:
                monthly_losses[m] += 1

    if not monthly_pnl_001:
        return {"error": "no months with valid data"}

    months_sorted = sorted(monthly_pnl_001.keys())

    # Equity curve per-001 lot base + notional capital $10,000
    # 用 notional capital 令 DD% 有意義（否則由 0 開始 peak 太細會誇大百分比）
    notional_capital = 10000.0
    equity = notional_capital
    peak = notional_capital
    equity_curve = [("start", round(notional_capital, 2))]
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
    monthly_win_rate = round(win_months / total_months * 100, 1) if total_months > 0 else 0
    pf = total_win_001 / total_loss_001 if total_loss_001 > 0 else (99 if total_win_001 > 0 else 0)

    # Summary stats per-001 lot
    avg_monthly_pnl = round(sum(monthly_pnl_001[m] for m in months_sorted) / total_months, 2) if total_months else 0
    all_monthly_pnls = sorted([monthly_pnl_001[m] for m in months_sorted])
    median_monthly_pnl = round(all_monthly_pnls[len(all_monthly_pnls)//2], 2) if all_monthly_pnls else 0

    return {
        "total_trades": sum(monthly_trade_count.values()),
        "total_months": total_months,
        "avg_monthly_pnl_001": avg_monthly_pnl,
        "median_monthly_pnl_001": median_monthly_pnl,
        "monthly_win_rate": monthly_win_rate,
        "win_months": win_months,
        "loss_months": loss_months,
        "profit_factor_001": round(pf, 2),
        "max_dd": round(max_dd_dollars, 2),
        "max_dd_pct_001": round(max_dd_pct, 2),
        "max_consec_loss_months": max_consec_loss_months,
        "avg_monthly_trades": round(sum(monthly_trade_count.values())/total_months, 1) if total_months else 0,
        "equity_curve_001": equity_curve,
        "monthly_performance": {m: {"trades": monthly_trade_count[m], "wins": monthly_wins[m], "losses": monthly_losses[m], "pnl_001": round(monthly_pnl_001[m], 2), "pips_001": round(monthly_pips[m], 1)} for m in months_sorted},
    }
# ──────────────────────────────────────────
# 4. 組合相關性 (方案 D)
# ──────────────────────────────────────────

def portfolio_correlation(monthly_results: list[dict]) -> dict:
    """
    計算 Portfolio 內 signal 之間嘅每月盈利相關性
    monthly_results: [{"signal_id": "xxx", "monthly": [{"month":..., "total_pnl":...}, ...]}, ...]
    """
    if len(monthly_results) < 2:
        return {"correlation_matrix": [], "high_correlation_pairs": [], "note": "need at least 2 signals"}

    # Build aligned monthly PnL matrix
    all_months = set()
    signal_monthly = {}
    for sr in monthly_results:
        sid = sr.get("signal_id", "?")
        signal_monthly[sid] = {}
        for m in sr.get("monthly_stats", []):
            if m.get("month"):
                all_months.add(m["month"])
                signal_monthly[sid][m["month"]] = m.get("total_pnl", 0)

    months_sorted = sorted(all_months)

    # Build PnL arrays
    signal_ids = list(signal_monthly.keys())
    pnl_arrays = {}
    for sid in signal_ids:
        arr = [signal_monthly[sid].get(m, 0) for m in months_sorted]
        pnl_arrays[sid] = arr

    # Correlation
    def pearsonr(a, b):
        n = len(a)
        if n < 2:
            return 0
        mean_a = sum(a) / n
        mean_b = sum(b) / n
        num = sum((ai - mean_a) * (bi - mean_b) for ai, bi in zip(a, b))
        den = math.sqrt(sum((ai - mean_a)**2 for ai in a)) * math.sqrt(sum((bi - mean_b)**2 for bi in b))
        return num / den if den != 0 else 0

    high_pairs = []
    matrix = {}
    for i, sid1 in enumerate(signal_ids):
        matrix[sid1] = {}
        for j, sid2 in enumerate(signal_ids):
            if i == j:
                matrix[sid1][sid2] = 1.0
            else:
                corr = pearsonr(pnl_arrays[sid1], pnl_arrays[sid2])
                matrix[sid1][sid2] = round(corr, 3)
                if abs(corr) > 0.6 and sid1 < sid2:
                    high_pairs.append({
                        "signal_1": sid1,
                        "signal_2": sid2,
                        "correlation": round(corr, 3),
                        "direction": "positive" if corr > 0 else "negative",
                    })

    high_pairs.sort(key=lambda x: abs(x["correlation"]), reverse=True)

    return {
        "signal_count": len(signal_ids),
        "month_count": len(months_sorted),
        "month_range": f"{months_sorted[0] if months_sorted else '-'} ~ {months_sorted[-1] if months_sorted else '-'}",
        "correlation_matrix": matrix,
        "high_correlation_pairs": high_pairs,
    }


# ──────────────────────────────────────────
# 5. 機會評分
# ──────────────────────────────────────────

def opportunity_score(ma: dict) -> dict:
    """
    計算 Signal 嘅 Monthly Opportunity Score。
    V2 修正版：盈利能力係硬門檻，不能因為交易頻率高就評 A。
    """
    score = 0
    details = []

    sim = ma.get("simulation") or {}
    avg_pnl_001 = sim.get("avg_monthly_pnl_001", 0)
    median_pnl_001 = sim.get("median_monthly_pnl_001", 0)
    monthly_win_rate = sim.get("monthly_win_rate", ma.get("profitable_month_pct", 0))
    max_dd_pct = sim.get("max_dd_pct_001", ma.get("estimate_max_dd_pct", 50))
    recent_pnl = ma.get("recent_3mo_avg_pnl", 0)

    # 1. 每月交易次數 (20%)
    avg_trades = ma.get("avg_monthly_trades", 0)
    freq_pts = 0
    if avg_trades >= 100:
        freq_pts = 20
        freq_text = "≥100/月，充足"
    elif avg_trades >= 50:
        freq_pts = 15
        freq_text = f"{avg_trades:.0f}/月，一般"
    elif avg_trades >= 20:
        freq_pts = 10
        freq_text = f"{avg_trades:.0f}/月，偏少"
    else:
        freq_pts = 3
        freq_text = f"{avg_trades:.0f}/月，不足"
    score += freq_pts
    details.append(("交易頻率", freq_pts, freq_text))

    # 2. 盈利月份比例 / 月度勝率 (25%)
    if monthly_win_rate >= 80:
        pts = 25
    elif monthly_win_rate >= 65:
        pts = 18
    elif monthly_win_rate >= 50:
        pts = 10
    else:
        pts = 3
    score += pts
    details.append(("盈利月份比例", pts, f"{monthly_win_rate:.0f}%"))

    # 3. 0.01 lot 標準化月均/中位 PnL (25%) — 核心盈利能力
    pnl_pts = 0
    if avg_pnl_001 > 0 and median_pnl_001 > 0:
        if avg_pnl_001 >= 100 and median_pnl_001 >= 30:
            pnl_pts = 25
        elif avg_pnl_001 >= 30 and median_pnl_001 >= 10:
            pnl_pts = 18
        else:
            pnl_pts = 10
    elif avg_pnl_001 > 0:
        pnl_pts = 6
    else:
        pnl_pts = 0
    score += pnl_pts
    details.append(("標準化月均PnL", pnl_pts, f"avg001=${avg_pnl_001:.0f}, median001=${median_pnl_001:.0f}"))

    # 4. 近 3 個月趨勢 (15%)
    recent_trades = ma.get("recent_3mo_avg_trades", 0)
    recent_win_rate = ma.get("recent_3mo_win_rate", 0)
    recent_pts = 0
    if recent_trades >= 10:
        recent_pts += 5
    if recent_pnl > 0:
        recent_pts += 5
    if recent_win_rate >= 60:
        recent_pts += 5
    score += recent_pts
    details.append(("近 3 月趨勢", recent_pts, f"trades={recent_trades:.0f}, src_pnl=${recent_pnl:.0f}, wr={recent_win_rate:.0f}%"))

    # 5. 月度回撤 (15%)
    dd_pts = 0
    if max_dd_pct <= 15:
        dd_pts = 15
    elif max_dd_pct <= 30:
        dd_pts = 10
    elif max_dd_pct <= 50:
        dd_pts = 5
    score += dd_pts
    details.append(("月度回撤", dd_pts, f"{max_dd_pct:.0f}%"))

    # 硬門檻：平均或中位 PnL 為負，最高 C；最近三月同時轉負，最高 D
    if avg_pnl_001 <= 0 or median_pnl_001 <= 0:
        score = min(score, 49)
    if avg_pnl_001 <= 0 and recent_pnl <= 0:
        score = min(score, 35)

    score = min(100, max(0, round(score)))

    if score >= 80:
        grade = "A"
        label = "✅ 優良"
    elif score >= 60:
        grade = "B"
        label = "✅ 良好"
    elif score >= 40:
        grade = "C"
        label = "⚠️ 一般"
    elif score >= 20:
        grade = "D"
        label = "⚠️ 偏低"
    else:
        grade = "E"
        label = "❌ 不足"

    return {
        "score": score,
        "grade": grade,
        "label": label,
        "details": details,
    }


# ──────────────────────────────────────────
# 6. Full Signal Analysis Pipeline
# ──────────────────────────────────────────

def full_signal_analysis(
    signal_id: str,
    capital: float = 10000,
    risk_pct: float = 2.0,
    sl_pips: float = 25,
    csv_dir: str = "downloads",
) -> dict:
    """完整運行一條 signal 嘅分析 pipeline"""
    trades = load_signal_csv(signal_id, csv_dir)
    if not trades:
        return {"signal_id": signal_id, "error": "no data"}

    monthly = monthly_analysis(trades)
    if "error" in monthly:
        return {"signal_id": signal_id, "error": monthly["error"]}

    monthly["signal_id"] = signal_id

    sim = sequential_simulation(trades, capital, risk_pct, sl_pips)

    # 估計回撤百分比（如無模擬層數）
    if "error" not in sim:
        monthly["simulation"] = sim
        monthly["estimate_max_dd_pct"] = sim.get("max_dd_pct_001", 0)
    else:
        monthly["simulation"] = None
        monthly["estimate_max_dd_pct"] = 50

    # 近 3 月平均 PF
    if monthly["monthly_stats"] and len(monthly["monthly_stats"]) >= 3:
        monthly["recent_3mo_pf"] = sum(m["profit_factor"] for m in monthly["monthly_stats"][-3:]) / 3
    elif monthly["monthly_stats"]:
        monthly["recent_3mo_pf"] = monthly["monthly_stats"][-1]["profit_factor"]
    else:
        monthly["recent_3mo_pf"] = 0

    score = opportunity_score(monthly)
    monthly["opportunity_score"] = score

    return monthly


# ──────────────────────────────────────────
# 7. Portfolio Analysis Pipeline
# ──────────────────────────────────────────

def analyze_portfolio(
    portfolio_id: str,
    portfolio_name: str,
    signal_ids: list[str],
    capital: float,
    risk_pct: float = 2.0,
    csv_dir: str = "downloads",
) -> dict:
    """完整運行一個 Portfolio 嘅分析"""
    signal_analyses = []
    for sid in signal_ids:
        print(f"  Analyzing Signal {sid}...")
        analysis = full_signal_analysis(sid, capital, risk_pct, csv_dir=csv_dir)
        analysis["signal_id"] = sid
        signal_analyses.append(analysis)

    # 組合相關性
    corr = portfolio_correlation([
        sr for sr in signal_analyses if "error" not in sr and sr.get("monthly_stats")
    ])

    # Portfolio 級統計
    valid = [sa for sa in signal_analyses if "error" not in sa]
    total_trades = sum(sa.get("total_trades", 0) for sa in valid)
    avg_monthly_trades = sum(sa.get("avg_monthly_trades", 0) for sa in valid) / len(valid) if valid else 0
    avg_profitable_pct = sum(sa.get("profitable_month_pct", 0) for sa in valid) / len(valid) if valid else 0
    avg_recent_3mo_pnl = sum(sa.get("recent_3mo_pnl", 0) for sa in valid) if valid else 0  # source-account PnL, only for trend direction
    avg_score = sum(sa.get("opportunity_score", {}).get("score", 0) for sa in valid) / len(valid) if valid else 0

    # 風險集中度
    ea_types = defaultdict(int)
    symbols = defaultdict(int)
    for sa in valid:
        sid = sa.get("signal_id", "")
        # 由 signal_id 約略推 EA type（實際上要由 metadata 拿，暫存簡化）
        pass

    return {
        "portfolio_id": portfolio_id,
        "portfolio_name": portfolio_name,
        "capital": capital,
        "risk_pct": risk_pct,
        "signal_count": len(signal_ids),
        "valid_signal_count": len(valid),
        "total_trades": total_trades,
        "avg_monthly_trades": round(avg_monthly_trades, 1),
        "avg_profitable_month_pct": round(avg_profitable_pct, 1),
        "avg_recent_3mo_pnl": round(avg_recent_3mo_pnl, 2),
        "avg_opportunity_score": round(avg_score, 1),
        "signals": signal_analyses,
        "correlation": corr,
    }


# ──────────────────────────────────────────
# Portfolio Definitions
# ──────────────────────────────────────────

PORTFOLIO_DEFS = [
    {"id": "P1", "name": "DW 保守組", "capital": 1000, "risk_pct": 1.5,
     "signals": ["31593", "30359", "17547"], "ea_types": "DW", "risk_level": "Low"},
    {"id": "P2", "name": "SMA 日內組", "capital": 1500, "risk_pct": 1.5,
     "signals": ["16698", "32278", "5001"], "ea_types": "SMA", "risk_level": "Low"},
    {"id": "P3", "name": "DW SMA 混合穩健組", "capital": 2000, "risk_pct": 1.5,
     "signals": ["23617", "10843"], "ea_types": "DW, SMA", "risk_level": "Low"},
    {"id": "P4", "name": "DW 高頻組", "capital": 1000, "risk_pct": 2.0,
     "signals": ["20805", "31593", "3291", "16698"], "ea_types": "DW", "risk_level": "Medium"},
    {"id": "P5", "name": "高利潤單組", "capital": 800, "risk_pct": 2.0,
     "signals": ["5117", "27226"], "ea_types": "UNK", "risk_level": "High"},
    {"id": "P6", "name": "亞洲時段組", "capital": 1000, "risk_pct": 1.5,
     "signals": ["30359", "33101", "17547"], "ea_types": "DW, Flash", "risk_level": "Medium"},
    {"id": "P7", "name": "頂級信號組", "capital": 1200, "risk_pct": 2.0,
     "signals": ["5117", "11598", "17547", "27226", "20805", "21698", "22200", "31593", "4022", "3291"],
     "ea_types": "DW, SMA, UNK", "risk_level": "High"},
    {"id": "P8", "name": "London 時段組", "capital": 1200, "risk_pct": 2.0,
     "signals": ["33101", "19849", "32541", "10843"], "ea_types": "DW, Flash, SMA, UNK", "risk_level": "High"},
    {"id": "P9", "name": "NY 時段組", "capital": 1500, "risk_pct": 2.0,
     "signals": ["32719", "36511", "27226", "31781"], "ea_types": "DW, UNK", "risk_level": "High"},
    {"id": "P10", "name": "混合策略組", "capital": 1800, "risk_pct": 2.0,
     "signals": ["17547", "21698", "22200", "31593", "3291", "5001", "14158", "32278", "16596", "16698"],
     "ea_types": "DW, SMA", "risk_level": "High"},
]


def get_portfolio_def(pid: str) -> dict:
    for p in PORTFOLIO_DEFS:
        if p["id"] == pid:
            return p
    return None


if __name__ == "__main__":
    # 測試
    r = full_signal_analysis("17547", capital=10000)
    print(f"Signal 17547:")
    print(f"  Trades: {r.get('total_trades')}")
    print(f"  Avg Monthly: {r.get('avg_monthly_trades')}")
    print(f"  Profitable Months: {r.get('profitable_month_pct')}%")
    print(f"  Recent 3mo PnL: ${r.get('recent_3mo_pnl')}")
    print(f"  Recent 3mo Trades: {r.get('recent_3mo_trades')}")
    print(f"  Opportunity Score: {r.get('opportunity_score', {}).get('score')} ({r.get('opportunity_score', {}).get('grade')})")
    if r.get("simulation"):
        sim = r["simulation"]
        print(f"  Avg Monthly PnL / 0.01 lot: ${sim.get('avg_monthly_pnl_001')}")
        print(f"  Max DD / 0.01 lot: {sim.get('max_dd_pct_001')}%")
        print(f"  Max Consec Loss Months: {sim.get('max_consec_loss_months')}")