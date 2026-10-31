#!/usr/bin/env python3
"""build_phase31_projection.py — Phase 3.1 投影六欄數據層（老闆 22:17 拍板接手開工）
六欄：信號／總分(dde_score)／樣本(trades)／勝率／PF／爆倉(red_card)
當月增長排序鍵：decision_ranking.monthly_pnl 最新月值（單一事實源，唔使 period_stats JOIN）
accounts.json：N/A 灰燈殼（信道復活後切 (a) A06E 帳戶 JSON——2018 信拍板）
"""
import csv, json, sqlite3
from datetime import datetime
from pathlib import Path

REPO = Path("/home/alvin/.openclaw/workspace/trade_strategy_analyzer")
HOME = REPO / "docs" / "home"
NOW = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00")

# 1) dde_scores（997 行：signal×symbol）
db = sqlite3.connect(REPO / "docs/data/tsa.db")
db.row_factory = sqlite3.Row
dde = [dict(r) for r in db.execute(
    "SELECT signal_id, symbol, dde_score, trades, win_rate, profit_factor, red_card, red_reasons, ea "
    "FROM dde_scores")]

# 2) decision_ranking：per signal 最優行 → monthly_pnl 最新月
best = {}
with open(REPO / "data/copytrade/decision_ranking.csv") as f:
    for row in csv.DictReader(f):
        sid = row["signal_id"]
        if sid not in best or int(row["rank"]) < int(best[sid]["rank"]):
            best[sid] = row

def latest_month(mp):
    if not mp: return None, None
    months = {}
    for seg in mp.split("|"):
        if ":" in seg:
            k, v = seg.rsplit(":", 1)
            try: months[k] = float(v)
            except ValueError: pass
    if not months: return None, None
    k = max(months)
    return k, months[k]

# 3) JOIN＋排序
rows = []
for d in dde:
    sid = d["signal_id"]
    b = best.get(sid)
    mk, mv = (latest_month(b["monthly_pnl"]) if b else (None, None))
    rr = d["red_reasons"] or "[]"
    try: reasons = json.loads(rr)
    except Exception: reasons = [rr] if rr else []
    rows.append({
        "signal": sid, "symbol": d["symbol"], "dde_score": d["dde_score"],
        "trades": d["trades"], "win_rate": d["win_rate"],
        "pf": d["profit_factor"], "red_card": d["red_card"],
        "red_reasons": reasons, "ea": d["ea"],
        "month_key": mk, "month_growth": mv,
    })
rows.sort(key=lambda r: (r["month_growth"] is None, -(r["month_growth"] or 0)))

# 4) 產物
(HOME).mkdir(exist_ok=True)
proj = {"generated_at": NOW, "source": "tsa.db dde_scores × copytrade decision_ranking(monthly_pnl)",
        "sort_key": "當月增長(month_growth) desc", "columns":
        ["信號", "總分 dde_score", "樣本 trades", "勝率%", "PF", "爆倉 red_card", "當月增長"],
        "accounts": {"status": "N/A", "note": "MT5 帳戶信道未通——accounts.json N/A 灰燈（2018 信拍板 (c) 對沖）"},
        "rows": rows}
(HOME / "projection.json").write_text(json.dumps(proj, ensure_ascii=False, indent=1))
(HOME / "accounts.json").write_text(json.dumps(
    {"generated_at": NOW, "accounts": None, "status": "N/A",
     "note": "灰燈殼：L0/帳戶信道復活後切 (a) A06E 帳戶 JSON"}, ensure_ascii=False, indent=1))

n_red = sum(1 for r in rows if r["red_card"])
n_growth = sum(1 for r in rows if r["month_growth"] is not None)
print(f"projection.json: {len(rows)} 行（dde 997 級）｜red_card {n_red}｜有當月增長 {n_growth}｜accounts.json N/A 殼 ✅")
print("TOP 5（當月增長）:")
for r in rows[:5]:
    print(f"  {r['signal']:<6} {r['symbol']:<7} 分{r['dde_score']:>5} 勝率{r['win_rate']:>5.1f}% PF{r['pf']:>5} 紅卡{r['red_card']} 當月[{r['month_key']}] {r['month_growth']}")
