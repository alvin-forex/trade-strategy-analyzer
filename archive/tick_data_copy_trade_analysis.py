#!/usr/bin/env python3
"""
Copy Trade Analysis: Copy on Profit / Copy on Lose
Uses AlgoForest CSV with MFE (Max Pips) and MAE (Max Loss Pips) data.

Logic:
- Copy on Profit @ trigger X: eligible if Max Pips >= X
  → Copy entry = original open + X pips
  → Copy PnL = Net Pips - X
  → Win if Net Pips > X

- Copy on Lose @ trigger X: eligible if Max Loss Pips >= X (MAE >= X)
  → Copy entry = original open - X pips (worse price, hoping reversal)
  → Copy PnL = Net Pips + X
  → Win if Net Pips > -X (i.e., trade eventually recovers)

Note: .bfc files are encrypted (Tick Data Suite proprietary format).
We use MFE/MAE from CSV which is standard approach for this analysis.
"""

import csv
import sys
from datetime import datetime
from collections import defaultdict
from pathlib import Path

CSV_PATH = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer/downloads/forex-forest-signals-page-8325.csv")
TRIGGER_LEVELS = [5, 10, 15, 20, 25, 30]


def parse_csv(path: str) -> list[dict]:
    trades = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                trade = {
                    "open_time": row["Open Time"].strip(),
                    "type": row["Type"].strip().lower(),
                    "lots": float(row["Lots"].strip()),
                    "symbol": row["Symbol"].strip(),
                    "open_price": float(row["Open Price"].strip()),
                    "close_time": row["Close Time"].strip(),
                    "close_price": float(row["Close Price"].strip()),
                    "net_pips": float(row["Net Pips"].strip()),
                    "net_profit": float(row["Net Profit"].strip()),
                    "max_profit": float(row["Max Profit"].strip()),
                    "max_pips": float(row["Max Pips"].strip()),
                    "max_loss": float(row["Max Loss"].strip()),
                    "max_loss_pips": float(row["Max Loss Pips"].strip()),
                    "holding_hours": float(row.get("Holding Time (Hours)", "0").strip()),
                }
                trades.append(trade)
            except (ValueError, KeyError) as e:
                print(f"⚠️  Skipping row: {e}", file=sys.stderr)
    return trades


def analyze_copy_on_profit(trades: list[dict], triggers: list[int]) -> dict:
    """Copy on Profit: enter when original trade is +X pips in profit."""
    results = {}
    for trigger in triggers:
        eligible = []
        for t in trades:
            if t["max_pips"] >= trigger:
                copy_pnl = t["net_pips"] - trigger
                copy_pnl_usd = t["net_profit"] - (trigger / t["max_pips"] * t["max_profit"]) if t["max_profit"] != 0 else 0
                # Better USD estimate: scale by pips ratio
                if t["max_pips"] != 0:
                    pip_value_per_lot = t["max_profit"] / t["max_pips"]
                else:
                    pip_value_per_lot = t["net_profit"] / t["net_pips"] if t["net_pips"] != 0 else 0
                copy_pnl_usd = copy_pnl * pip_value_per_lot * t["lots"] / 0.11  # normalize to 0.11 lot
                
                eligible.append({
                    "symbol": t["symbol"],
                    "type": t["type"],
                    "net_pips": t["net_pips"],
                    "max_pips": t["max_pips"],
                    "copy_pnl": copy_pnl,
                    "copy_pnl_usd": copy_pnl * pip_value_per_lot * t["lots"] if pip_value_per_lot else 0,
                })
        
        if not eligible:
            results[trigger] = None
            continue
        
        wins = [e for e in eligible if e["copy_pnl"] > 0]
        losses = [e for e in eligible if e["copy_pnl"] <= 0]
        
        total_pnl = sum(e["copy_pnl"] for e in eligible)
        
        results[trigger] = {
            "total_trades": len(trades),
            "eligible": len(eligible),
            "eligibility_rate": len(eligible) / len(trades) * 100,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(eligible) * 100 if eligible else 0,
            "avg_pnl": total_pnl / len(eligible),
            "total_pnl": total_pnl,
            "avg_win": sum(e["copy_pnl"] for e in wins) / len(wins) if wins else 0,
            "avg_loss": sum(e["copy_pnl"] for e in losses) / len(losses) if losses else 0,
            "max_win": max(e["copy_pnl"] for e in eligible),
            "max_loss": min(e["copy_pnl"] for e in eligible),
            "profit_factor": abs(sum(e["copy_pnl"] for e in wins) / sum(e["copy_pnl"] for e in losses)) if losses and sum(e["copy_pnl"] for e in losses) != 0 else float("inf"),
        }
    
    return results


def analyze_copy_on_lose(trades: list[dict], triggers: list[int]) -> dict:
    """Copy on Lose: enter when original trade is -X pips (hoping for reversal)."""
    results = {}
    for trigger in triggers:
        eligible = []
        for t in trades:
            if abs(t["max_loss_pips"]) >= trigger:
                # We enter at a worse price (X pips against original direction)
                # If original recovers, we make more. If it doesn't, we lose less initially but...
                # Actually: we copy the SAME direction but enter X pips worse
                # Our PnL = (Close - (Open ± X)) = Net Pips ± X
                # For buy: we buy X pips higher if trade went down first... wait
                
                # Copy on Lose = original trade goes -X pips, we enter SAME direction
                # Buy trade: price drops X pips, we buy at Open - X
                # Our PnL = Close - (Open - X) = (Close - Open) + X = Net Pips + X
                # Sell trade: price rises X pips, we sell at Open + X  
                # Our PnL = (Open + X) - Close = (Open - Close) + X = Net Pips + X
                
                copy_pnl = t["net_pips"] + trigger
                
                # Estimate max drawdown from our entry
                # Our entry is X pips worse than original
                # Original max drawdown from entry = Max Loss Pips
                # Our max drawdown from our entry = Max Loss Pips - X (we entered after X pips already moved)
                # But if it continued going against after we entered: we'd lose more
                # Conservative estimate: remaining drawdown after we enter
                # If Max Loss Pips > trigger, there's additional downside
                remaining_adverse = abs(t["max_loss_pips"]) - trigger
                
                eligible.append({
                    "symbol": t["symbol"],
                    "type": t["type"],
                    "net_pips": t["net_pips"],
                    "max_loss_pips": t["max_loss_pips"],
                    "copy_pnl": copy_pnl,
                    "remaining_adverse": remaining_adverse,
                })
        
        if not eligible:
            results[trigger] = None
            continue
        
        wins = [e for e in eligible if e["copy_pnl"] > 0]
        losses = [e for e in eligible if e["copy_pnl"] <= 0]
        
        # Reversal = trade eventually profitable despite initial -X drawdown
        reversals = [e for e in eligible if e["copy_pnl"] > 0]
        
        total_pnl = sum(e["copy_pnl"] for e in eligible)
        
        results[trigger] = {
            "total_trades": len(trades),
            "eligible": len(eligible),
            "eligibility_rate": len(eligible) / len(trades) * 100,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": len(wins) / len(eligible) * 100 if eligible else 0,
            "reversal_rate": len(reversals) / len(eligible) * 100 if eligible else 0,
            "avg_pnl": total_pnl / len(eligible),
            "total_pnl": total_pnl,
            "avg_win": sum(e["copy_pnl"] for e in wins) / len(wins) if wins else 0,
            "avg_loss": sum(e["copy_pnl"] for e in losses) / len(losses) if losses else 0,
            "max_win": max(e["copy_pnl"] for e in eligible),
            "max_loss": min(e["copy_pnl"] for e in eligible),
            "profit_factor": abs(sum(e["copy_pnl"] for e in wins) / sum(e["copy_pnl"] for e in losses)) if losses and sum(e["copy_pnl"] for e in losses) != 0 else float("inf"),
            "avg_remaining_adverse": sum(e["remaining_adverse"] for e in eligible) / len(eligible),
        }
    
    return results


def analyze_by_symbol(trades: list[dict], trigger: int, mode: str) -> dict:
    """Breakdown by symbol for a specific trigger level."""
    by_symbol = defaultdict(list)
    for t in trades:
        by_symbol[t["symbol"]].append(t)
    
    results = {}
    for symbol, symbol_trades in by_symbol.items():
        if mode == "profit":
            eligible = [t for t in symbol_trades if t["max_pips"] >= trigger]
            pnls = [t["net_pips"] - trigger for t in eligible]
        else:
            eligible = [t for t in symbol_trades if abs(t["max_loss_pips"]) >= trigger]
            pnls = [t["net_pips"] + trigger for t in eligible]
        
        if not eligible:
            continue
        
        wins = [p for p in pnls if p > 0]
        results[symbol] = {
            "total": len(symbol_trades),
            "eligible": len(eligible),
            "win_rate": len(wins) / len(pnls) * 100 if pnls else 0,
            "avg_pnl": sum(pnls) / len(pnls),
        }
    
    return dict(sorted(results.items(), key=lambda x: x[1]["avg_pnl"], reverse=True))


def generate_report(trades: list[dict], profit_results: dict, lose_results: dict):
    """Generate formatted report."""
    
    # Overall stats
    total = len(trades)
    wins = [t for t in trades if t["net_pips"] > 0]
    avg_pips = sum(t["net_pips"] for t in trades) / total
    avg_max_pips = sum(t["max_pips"] for t in trades) / total
    avg_max_loss = sum(t["max_loss_pips"] for t in trades) / total
    
    print("=" * 80)
    print("📊 COPY TRADE 回測分析報告")
    print("=" * 80)
    print(f"\n📋 數據概覽")
    print(f"   總交易數: {total}")
    print(f"   整體勝率: {len(wins)/total*100:.1f}%")
    print(f"   平均 Net Pips: {avg_pips:.1f}")
    print(f"   平均 Max Pips (MFE): {avg_max_pips:.1f}")
    print(f"   平均 Max Loss Pips (MAE): {avg_max_loss:.1f}")
    print(f"   貨幣對: {', '.join(sorted(set(t['symbol'] for t in trades)))}")
    
    # ============ COPY ON PROFIT ============
    print(f"\n{'='*80}")
    print("📈 COPY ON PROFIT 分析")
    print(f"   邏輯: 當原交易浮盈達 X pips 時跟入，計算跟入後嘅最終 PnL")
    print(f"   跟入 PnL = Net Pips - Trigger Pips")
    print(f"{'='*80}")
    
    print(f"\n   {'Trigger':>8} {'合资格':>6} {'资格率':>8} {'勝率':>8} {'平均PnL':>10} {'總PnL':>10} {'平均贏':>10} {'平均輸':>10} {'PF':>8}")
    print(f"   {'-'*8} {'-'*6} {'-'*8} {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
    
    for trigger in TRIGGER_LEVELS:
        r = profit_results.get(trigger)
        if r is None:
            print(f"   {trigger:>5} pips   N/A")
            continue
        pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] != float('inf') else "∞"
        print(f"   {trigger:>5} pips {r['eligible']:>5} {r['eligibility_rate']:>7.1f}% {r['win_rate']:>7.1f}% {r['avg_pnl']:>9.1f} {r['total_pnl']:>9.1f} {r['avg_win']:>9.1f} {r['avg_loss']:>9.1f} {pf_str:>8}")
    
    # Best trigger for profit
    valid_profit = {k: v for k, v in profit_results.items() if v is not None}
    if valid_profit:
        best_by_wr = max(valid_profit.items(), key=lambda x: x[1]["win_rate"])
        best_by_pnl = max(valid_profit.items(), key=lambda x: x[1]["avg_pnl"])
        best_by_pf = max(valid_profit.items(), key=lambda x: x[1]["profit_factor"] if x[1]["profit_factor"] != float("inf") else 0)
        
        print(f"\n   🏆 最佳 Trigger:")
        print(f"      最高勝率: {best_by_wr[0]} pips ({best_by_wr[1]['win_rate']:.1f}%)")
        print(f"      最高平均PnL: {best_by_pnl[0]} pips ({best_by_pnl[1]['avg_pnl']:.1f})")
        if best_by_pf[1]["profit_factor"] != float("inf"):
            print(f"      最高Profit Factor: {best_by_pf[0]} pips ({best_by_pf[1]['profit_factor']:.2f})")
    
    # ============ COPY ON LOSE ============
    print(f"\n{'='*80}")
    print("📉 COPY ON LOSE 分析")
    print(f"   邏輯: 當原交易浮虧達 X pips 時跟入（同方向），計算跟入後嘅最終 PnL")
    print(f"   跟入 PnL = Net Pips + Trigger Pips（入場價更好，但風險仍在）")
    print(f"{'='*80}")
    
    print(f"\n   {'Trigger':>8} {'合资格':>6} {'资格率':>8} {'勝率':>8} {'回歸率':>8} {'平均PnL':>10} {'總PnL':>10} {'平均贏':>10} {'平均輸':>10} {'PF':>8}")
    print(f"   {'-'*8} {'-'*6} {'-'*8} {'-'*8} {'-'*8} {'-'*10} {'-'*10} {'-'*10} {'-'*10} {'-'*8}")
    
    for trigger in TRIGGER_LEVELS:
        r = lose_results.get(trigger)
        if r is None:
            print(f"   {trigger:>5} pips   N/A")
            continue
        pf_str = f"{r['profit_factor']:.2f}" if r['profit_factor'] != float('inf') else "∞"
        print(f"   {trigger:>5} pips {r['eligible']:>5} {r['eligibility_rate']:>7.1f}% {r['win_rate']:>7.1f}% {r['reversal_rate']:>7.1f}% {r['avg_pnl']:>9.1f} {r['total_pnl']:>9.1f} {r['avg_win']:>9.1f} {r['avg_loss']:>9.1f} {pf_str:>8}")
    
    valid_lose = {k: v for k, v in lose_results.items() if v is not None}
    if valid_lose:
        best_by_wr = max(valid_lose.items(), key=lambda x: x[1]["win_rate"])
        best_by_pnl = max(valid_lose.items(), key=lambda x: x[1]["avg_pnl"])
        best_by_pf = max(valid_lose.items(), key=lambda x: x[1]["profit_factor"] if x[1]["profit_factor"] != float("inf") else 0)
        
        print(f"\n   🏆 最佳 Trigger:")
        print(f"      最高勝率: {best_by_wr[0]} pips ({best_by_wr[1]['win_rate']:.1f}%)")
        print(f"      最高平均PnL: {best_by_pnl[0]} pips ({best_by_pnl[1]['avg_pnl']:.1f})")
        if best_by_pf[1]["profit_factor"] != float("inf"):
            print(f"      最高Profit Factor: {best_by_pf[0]} pips ({best_by_pf[1]['profit_factor']:.2f})")
    
    # ============ BY SYMBOL BREAKDOWN ============
    print(f"\n{'='*80}")
    print("📊 按貨幣對分類 (Trigger = 10 pips)")
    print(f"{'='*80}")
    
    print(f"\n   --- Copy on Profit @ 10 pips ---")
    sym_profit = analyze_by_symbol(trades, 10, "profit")
    print(f"   {'貨幣對':>10} {'交易數':>6} {'合资格':>6} {'勝率':>8} {'平均PnL':>10}")
    print(f"   {'-'*10} {'-'*6} {'-'*6} {'-'*8} {'-'*10}")
    for sym, r in sym_profit.items():
        print(f"   {sym:>10} {r['total']:>6} {r['eligible']:>6} {r['win_rate']:>7.1f}% {r['avg_pnl']:>9.1f}")
    
    print(f"\n   --- Copy on Lose @ 10 pips ---")
    sym_lose = analyze_by_symbol(trades, 10, "lose")
    print(f"   {'貨幣對':>10} {'交易數':>6} {'合资格':>6} {'勝率':>8} {'平均PnL':>10}")
    print(f"   {'-'*10} {'-'*6} {'-'*6} {'-'*8} {'-'*10}")
    for sym, r in sym_lose.items():
        print(f"   {sym:>10} {r['total']:>6} {r['eligible']:>6} {r['win_rate']:>7.1f}% {r['avg_pnl']:>9.1f}")
    
    # ============ RECOMMENDATION ============
    print(f"\n{'='*80}")
    print("💡 建議總結")
    print(f"{'='*80}")
    
    # Find best overall strategy
    all_strategies = []
    for trigger, r in valid_profit.items():
        all_strategies.append(("Copy on Profit", trigger, r["win_rate"], r["avg_pnl"], r["profit_factor"]))
    for trigger, r in valid_lose.items():
        all_strategies.append(("Copy on Lose", trigger, r["win_rate"], r["avg_pnl"], r["profit_factor"]))
    
    best = max(all_strategies, key=lambda x: (x[3], x[2]))  # prioritize avg_pnl, then win_rate
    
    print(f"\n   最佳策略: {best[0]} @ {best[1]} pips")
    print(f"   勝率: {best[2]:.1f}% | 平均 PnL: {best[3]:.1f} pips | PF: {best[4]:.2f}")
    
    # Also show if there's a high-WR strategy
    high_wr = max(all_strategies, key=lambda x: x[2])
    if high_wr != best:
        print(f"\n   最高勝率策略: {high_wr[0]} @ {high_wr[1]} pips")
        print(f"   勝率: {high_wr[2]:.1f}% | 平均 PnL: {high_wr[3]:.1f} pips | PF: {high_wr[4]:.2f}")
    
    print(f"\n{'='*80}")
    print("⚠️  注意事項:")
    print("   1. .bfc tick data 係加密格式，無法直接解析")
    print("   2. 此分析基於 CSV 中嘅 MFE/MAE 數據，屬於靜態分析")
    print("   3. 實際跟入時需要考慮滑點、延遲、流動性等因素")
    print("   4. Copy on Lose 嘅回歸率受持倉時間影響較大")
    print("   5. 建議結合實盤小倉位驗證後再加大規模")
    print(f"{'='*80}")


def main():
    print(f"📂 讀取 CSV: {CSV_PATH}")
    trades = parse_csv(CSV_PATH)
    print(f"✅ 讀取 {len(trades)} 筆交易\n")
    
    # Date range
    dates = []
    for t in trades:
        try:
            dt = datetime.strptime(t["open_time"], "%d/%m/%Y %H:%M:%S")
            dates.append(dt)
        except ValueError:
            pass
    if dates:
        print(f"   時間範圍: {min(dates).strftime('%Y-%m-%d')} ~ {max(dates).strftime('%Y-%m-%d')}")
    
    print(f"\n🔍 分析 Copy on Profit...")
    profit_results = analyze_copy_on_profit(trades, TRIGGER_LEVELS)
    
    print(f"🔍 分析 Copy on Lose...")
    lose_results = analyze_copy_on_lose(trades, TRIGGER_LEVELS)
    
    print(f"\n📊 生成報告...\n")
    generate_report(trades, profit_results, lose_results)


if __name__ == "__main__":
    main()
