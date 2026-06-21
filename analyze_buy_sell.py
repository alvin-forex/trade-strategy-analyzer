#!/usr/bin/env python3
"""CCY RANKING Buy/Sell Direction Analysis"""

import sqlite3
import os
import glob
from collections import defaultdict

DB_PATH = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/data/tsa.db"
SET_DIR = "/home/alvin/.openclaw/workspace/trade_strategy_analyzer/downloads/set_files/"

def check_set_file(signal_id, symbol, ea):
    """Check if a SET file exists for this combo."""
    si = str(signal_id)
    sym = symbol.upper()
    
    # Search both in root and subdirectories
    for root, dirs, files in os.walk(SET_DIR):
        for f in files:
            if not f.endswith('.set'):
                continue
            # Check signal_id and symbol match
            if f'({si})' in f and sym in f.upper():
                # Return relative path from SET_DIR
                rel = os.path.relpath(os.path.join(root, f), SET_DIR)
                return rel
    return None

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # =========================================================================
    # PART 1: Buy vs Sell performance per signal_id + symbol
    # =========================================================================
    print("=" * 100)
    print("# 📊 CCY RANKING BUY/SELL 方向分析報告")
    print("=" * 100)
    print()

    # Get all buy records
    cur.execute("""
        SELECT signal_id, symbol, ea, type, win_rate, profit_factor, trades, 
               total_net_pips, buy_pct, sell_pct, bias, best_day, worst_day,
               max_dd_pips, dde_score
        FROM dde_scores 
        WHERE type = 'buy'
        ORDER BY signal_id, symbol
    """)
    buy_rows = {f"{r['signal_id']}|{r['symbol']}": r for r in cur.fetchall()}

    # Get all sell records
    cur.execute("""
        SELECT signal_id, symbol, ea, type, win_rate, profit_factor, trades, 
               total_net_pips, buy_pct, sell_pct, bias, best_day, worst_day,
               max_dd_pips, dde_score
        FROM dde_scores 
        WHERE type = 'sell'
        ORDER BY signal_id, symbol
    """)
    sell_rows = {f"{r['signal_id']}|{r['symbol']}": r for r in cur.fetchall()}

    all_keys = sorted(set(list(buy_rows.keys()) + list(sell_rows.keys())))

    # Build comparison data
    comparisons = []
    for key in all_keys:
        b = buy_rows.get(key)
        s = sell_rows.get(key)
        sid, sym = key.split("|", 1)
        ea = (b['ea'] if b else s['ea']) if (b or s) else ''
        
        b_wr = b['win_rate'] if b else None
        s_wr = s['win_rate'] if s else None
        b_pf = b['profit_factor'] if b else None
        s_pf = s['profit_factor'] if s else None
        b_trades = b['trades'] if b else 0
        s_trades = s['trades'] if s else 0
        b_pips = b['total_net_pips'] if b else 0
        s_pips = s['total_net_pips'] if s else 0
        
        wr_diff = abs((b_wr or 0) - (s_wr or 0)) if b_wr is not None and s_wr is not None else None
        pf_diff = abs((b_pf or 0) - (s_pf or 0)) if b_pf is not None and s_pf is not None else None
        
        comparisons.append({
            'signal_id': sid,
            'symbol': sym,
            'ea': ea,
            'buy_wr': b_wr,
            'sell_wr': s_wr,
            'buy_pf': b_pf,
            'sell_pf': s_pf,
            'buy_trades': b_trades,
            'sell_trades': s_trades,
            'buy_pips': b_pips,
            'sell_pips': s_pips,
            'wr_diff': wr_diff,
            'pf_diff': pf_diff,
            'buy_row': b,
            'sell_row': s,
        })

    # =========================================================================
    # PART 1a: Table - Buy vs Sell comparison for combos with both directions
    # =========================================================================
    both_dir = [c for c in comparisons if c['buy_wr'] is not None and c['sell_wr'] is not None]
    both_dir_sorted = sorted(both_dir, key=lambda x: x['wr_diff'] or 0, reverse=True)

    print("## 1️⃣ BUY vs SELL 表現對比（按 WR 差異排序，只顯示差異最大的 30 個）")
    print()
    print("| # | Signal ID | Symbol | EA | BUY Trades | BUY WR% | BUY PF | BUY Pips | SELL Trades | SELL WR% | SELL PF | SELL Pips | WR Diff | PF Diff | 優勢方向 |")
    print("|---|-----------|--------|----|-----------|---------|--------|----------|------------|----------|---------|----------|---------|---------|---------|")

    for i, c in enumerate(both_dir_sorted[:30], 1):
        advantage = ""
        if c['wr_diff'] and c['wr_diff'] >= 20:
            if c['buy_wr'] > c['sell_wr']:
                advantage = "🟢 BUY"
            else:
                advantage = "🔴 SELL"
        
        print(f"| {i} | {c['signal_id']} | {c['symbol']} | {c['ea']} | "
              f"{c['buy_trades']} | {c['buy_wr']:.1f} | {c['buy_pf']:.2f} | {c['buy_pips']:.1f} | "
              f"{c['sell_trades']} | {c['sell_wr']:.1f} | {c['sell_pf']:.2f} | {c['sell_pips']:.1f} | "
              f"{c['wr_diff']:.1f} | {c['pf_diff']:.2f} | {advantage} |")

    print()
    print(f"> 總共 {len(both_dir)} 個 combo 同時有 BUY + SELL 數據")
    print()

    # =========================================================================
    # PART 1b: Extreme direction bias combos (WR diff > 30%)
    # =========================================================================
    extreme = [c for c in both_dir if c['wr_diff'] and c['wr_diff'] >= 30]
    print(f"## ⚠️ 方向差異極大嘅 Combo（WR 差異 ≥ 30%，共 {len(extreme)} 個）")
    print()
    if extreme:
        print("| Signal ID | Symbol | EA | BUY WR% | SELL WR% | WR Diff | 建議 |")
        print("|-----------|--------|----|---------|----------|---------|------|")
        for c in sorted(extreme, key=lambda x: x['wr_diff'], reverse=True)[:20]:
            advice = "只做 BUY" if c['buy_wr'] > c['sell_wr'] else "只做 SELL"
            print(f"| {c['signal_id']} | {c['symbol']} | {c['ea']} | {c['buy_wr']:.1f} | {c['sell_wr']:.1f} | {c['wr_diff']:.1f} | {advice} |")
    print()

    # =========================================================================
    # PART 2: buy_pct / sell_pct bias analysis
    # =========================================================================
    print("## 2️⃣ Buy%/Sell% 方向傾向分析")
    print()

    cur.execute("""
        SELECT signal_id, symbol, ea, type, buy_pct, sell_pct, bias, 
               win_rate, profit_factor, trades, total_net_pips
        FROM dde_scores
        WHERE trades >= 5
        ORDER BY signal_id, symbol
    """)
    bias_rows = cur.fetchall()

    strong_buy = []
    strong_sell = []
    mixed = []
    for r in bias_rows:
        if r['buy_pct'] >= 80 and r['sell_pct'] <= 20:
            strong_buy.append(r)
        elif r['sell_pct'] >= 80 and r['buy_pct'] <= 20:
            strong_sell.append(r)
        else:
            mixed.append(r)

    print(f"- **強 BUY 傾向** (buy_pct ≥ 80%): {len(strong_buy)} 筆記錄")
    print(f"- **強 SELL 傾向** (sell_pct ≥ 80%): {len(strong_sell)} 筆記錄")
    print(f"- **混合方向** (20%-80%): {len(mixed)} 筆記錄")
    print()

    # Direction bias summary by EA
    print("### 按 EA 統計方向傾向")
    print()
    print("| EA | 強BUY | 強SELL | 混合 | 總計 |")
    print("|----|-------|--------|------|------|")
    
    ea_bias = defaultdict(lambda: {'buy': 0, 'sell': 0, 'mix': 0})
    for r in strong_buy:
        ea_bias[r['ea']]['buy'] += 1
    for r in strong_sell:
        ea_bias[r['ea']]['sell'] += 1
    for r in mixed:
        ea_bias[r['ea']]['mix'] += 1
    
    for ea in sorted(ea_bias.keys()):
        b = ea_bias[ea]
        total = b['buy'] + b['sell'] + b['mix']
        print(f"| {ea} | {b['buy']} | {b['sell']} | {b['mix']} | {total} |")
    print()

    # =========================================================================
    # PART 3: Top 20 unidirectional combos
    # =========================================================================
    print("## 3️⃣ Top 20 最佳單方向操作 Combo")
    print()
    print("**篩選條件：** WR > 80%, PF > 1.5, Trades ≥ 10, 有 SET 檔")
    print()

    # Get qualifying records - separate buy and sell
    candidates = []
    
    # Buy candidates
    cur.execute("""
        SELECT signal_id, symbol, ea, type, win_rate, profit_factor, trades, 
               total_net_pips, buy_pct, sell_pct, bias, best_day, worst_day,
               max_dd_pips, dde_score, red_card
        FROM dde_scores 
        WHERE type = 'buy' 
          AND win_rate > 80 
          AND profit_factor > 1.5 
          AND trades >= 10
          AND red_card = 0
        ORDER BY profit_factor DESC
    """)
    for r in cur.fetchall():
        set_file = check_set_file(r['signal_id'], r['symbol'], r['ea'])
        if set_file:
            candidates.append({**dict(r), 'set_file': set_file, 'direction': 'BUY'})

    # Sell candidates
    cur.execute("""
        SELECT signal_id, symbol, ea, type, win_rate, profit_factor, trades, 
               total_net_pips, buy_pct, sell_pct, bias, best_day, worst_day,
               max_dd_pips, dde_score, red_card
        FROM dde_scores 
        WHERE type = 'sell' 
          AND win_rate > 80 
          AND profit_factor > 1.5 
          AND trades >= 10
          AND red_card = 0
        ORDER BY profit_factor DESC
    """)
    for r in cur.fetchall():
        set_file = check_set_file(r['signal_id'], r['symbol'], r['ea'])
        if set_file:
            candidates.append({**dict(r), 'set_file': set_file, 'direction': 'SELL'})

    # Also check "Both" type that could qualify as unidirectional
    # Some type=buy records have buy_pct=100, meaning pure buy
    
    # Sort by PF * WR as a composite score
    candidates.sort(key=lambda x: x['profit_factor'] * x['win_rate'], reverse=True)

    # Deduplicate - if same signal_id+symbol appears in both BUY and SELL, keep the better one
    seen = {}
    for c in candidates:
        key = f"{c['signal_id']}|{c['symbol']}|{c['direction']}"
        if key not in seen:
            seen[key] = c
    candidates = list(seen.values())
    candidates.sort(key=lambda x: x['profit_factor'] * x['win_rate'], reverse=True)

    print("### 完整 Top 20 表格")
    print()
    print("| # | Signal ID | Symbol | EA | Direction | Trades | WR% | PF | Net Pips | Buy% | Sell% | Bias | DD Pips | DDE Score | SET File |")
    print("|---|-----------|--------|----|-----------|--------|-----|----|----------|------|-------|------|---------|-----------|----------|")

    for i, c in enumerate(candidates[:20], 1):
        print(f"| {i} | {c['signal_id']} | {c['symbol']} | {c['ea']} | "
              f"{'🟢 '+c['direction']} | {c['trades']} | {c['win_rate']:.1f} | {c['profit_factor']:.2f} | "
              f"{c['total_net_pips']:.1f} | {c['buy_pct']:.0f} | {c['sell_pct']:.0f} | "
              f"{c['bias']} | {c['max_dd_pips']:.1f} | {c['dde_score']:.1f} | "
              f"`{c['set_file']}` |")

    print()
    print(f"> 符合條件且有 SET 檔的 combo 共 {len(candidates)} 個")
    print()

    # =========================================================================
    # PART 3b: Candidates without SET files (for reference)
    # =========================================================================
    no_set_buy = 0
    no_set_sell = 0
    cur.execute("""
        SELECT signal_id, symbol, ea, type FROM dde_scores 
        WHERE type = 'buy' AND win_rate > 80 AND profit_factor > 1.5 AND trades >= 10 AND red_card = 0
    """)
    for r in cur.fetchall():
        if not check_set_file(r['signal_id'], r['symbol'], r['ea']):
            no_set_buy += 1
    cur.execute("""
        SELECT signal_id, symbol, ea, type FROM dde_scores 
        WHERE type = 'sell' AND win_rate > 80 AND profit_factor > 1.5 AND trades >= 10 AND red_card = 0
    """)
    for r in cur.fetchall():
        if not check_set_file(r['signal_id'], r['symbol'], r['ea']):
            no_set_sell += 1
    
    print(f"> 另有 {no_set_buy} 個 BUY 及 {no_set_sell} 個 SELL 符合條件但無 SET 檔")
    print()

    # =========================================================================
    # PART 4: Already output above in Part 3 table
    # =========================================================================

    # =========================================================================
    # PART 5: Best/Worst Day analysis
    # =========================================================================
    print("## 5️⃣ Best Day / Worst Day 星期分析")
    print()

    cur.execute("""
        SELECT type, best_day, worst_day, COUNT(*) as cnt,
               AVG(win_rate) as avg_wr,
               AVG(profit_factor) as avg_pf,
               AVG(total_net_pips) as avg_pips,
               AVG(trades) as avg_trades
        FROM dde_scores
        WHERE best_day != '' AND worst_day != ''
        GROUP BY type, best_day, worst_day
        ORDER BY type, cnt DESC
    """)
    day_rows = cur.fetchall()

    # Aggregate by day
    best_day_stats = defaultdict(lambda: {'count': 0, 'wr_sum': 0, 'pf_sum': 0, 'pips_sum': 0})
    worst_day_stats = defaultdict(lambda: {'count': 0, 'wr_sum': 0, 'pf_sum': 0, 'pips_sum': 0})
    
    cur.execute("""
        SELECT best_day, worst_day, win_rate, profit_factor, total_net_pips, trades, type
        FROM dde_scores
        WHERE best_day != '' AND worst_day != '' AND trades >= 5
    """)
    for r in cur.fetchall():
        bd = r['best_day']
        wd = r['worst_day']
        best_day_stats[bd]['count'] += 1
        best_day_stats[bd]['wr_sum'] += r['win_rate']
        best_day_stats[bd]['pf_sum'] += r['profit_factor']
        best_day_stats[bd]['pips_sum'] += r['total_net_pips']
        
        worst_day_stats[wd]['count'] += 1
        worst_day_stats[wd]['wr_sum'] += r['win_rate']
        worst_day_stats[wd]['pf_sum'] += r['profit_factor']
        worst_day_stats[wd]['pips_sum'] += r['total_net_pips']

    print("### Best Day 分佈（所有 combo 平均）")
    print()
    print("| 星期 | 出現次數 | 平均 WR% | 平均 PF | 平均 Pips |")
    print("|------|---------|---------|---------|-----------|")
    day_order = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']
    for d in day_order:
        s = best_day_stats[d]
        if s['count'] > 0:
            print(f"| {d} | {s['count']} | {s['wr_sum']/s['count']:.1f} | {s['pf_sum']/s['count']:.2f} | {s['pips_sum']/s['count']:.1f} |")
    print()

    print("### Worst Day 分佈（所有 combo 平均）")
    print()
    print("| 星期 | 出現次數 | 平均 WR% | 平均 PF | 平均 Pips |")
    print("|------|---------|---------|---------|-----------|")
    for d in day_order:
        s = worst_day_stats[d]
        if s['count'] > 0:
            print(f"| {d} | {s['count']} | {s['wr_sum']/s['count']:.1f} | {s['pf_sum']/s['count']:.2f} | {s['pips_sum']/s['count']:.1f} |")
    print()

    # Best/Worst day combos for top performers
    print("### Top Combo 的 Best/Worst Day")
    print()
    cur.execute("""
        SELECT signal_id, symbol, ea, type, win_rate, profit_factor, trades,
               total_net_pips, best_day, worst_day
        FROM dde_scores
        WHERE win_rate > 80 AND profit_factor > 1.5 AND trades >= 10 AND red_card = 0
        ORDER BY profit_factor DESC
        LIMIT 20
    """)
    top_day_rows = cur.fetchall()
    print("| Signal ID | Symbol | EA | Dir | WR% | PF | Best Day | Worst Day |")
    print("|-----------|--------|----|-----|-----|----|---------|-----------|")
    for r in top_day_rows:
        print(f"| {r['signal_id']} | {r['symbol']} | {r['ea']} | {r['type'].upper()} | "
              f"{r['win_rate']:.1f} | {r['profit_factor']:.2f} | {r['best_day']} | {r['worst_day']} |")
    print()

    # Best/Worst day pair analysis
    print("### Best Day + Worst Day 配對分析（出現次數最多的配對）")
    print()
    pair_stats = defaultdict(int)
    cur.execute("""
        SELECT best_day, worst_day FROM dde_scores
        WHERE best_day != '' AND worst_day != '' AND trades >= 5
    """)
    for r in cur.fetchall():
        pair_stats[f"{r['best_day']} → {r['worst_day']}"] += 1
    
    print("| Best Day → Worst Day | 出現次數 |")
    print("|---------------------|---------|")
    for pair, cnt in sorted(pair_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"| {pair} | {cnt} |")
    print()

    # =========================================================================
    # Summary Stats
    # =========================================================================
    print("## 📋 總結統計")
    print()
    
    cur.execute("SELECT COUNT(*) FROM dde_scores WHERE type='buy'")
    total_buy = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM dde_scores WHERE type='sell'")
    total_sell = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM dde_scores WHERE type='buy' AND win_rate > 80 AND profit_factor > 1.5 AND trades >= 10 AND red_card = 0")
    qual_buy = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM dde_scores WHERE type='sell' AND win_rate > 80 AND profit_factor > 1.5 AND trades >= 10 AND red_card = 0")
    qual_sell = cur.fetchone()[0]
    
    print(f"- 總 BUY 記錄：{total_buy}")
    print(f"- 總 SELL 記錄：{total_sell}")
    print(f"- 合格 BUY (WR>80%, PF>1.5, T≥10)：{qual_buy}")
    print(f"- 合格 SELL (WR>80%, PF>1.5, T≥10)：{qual_sell}")
    print(f"- 有 SET 檔的合格 combo：{len(candidates)}")
    print()

    conn.close()

if __name__ == "__main__":
    main()
