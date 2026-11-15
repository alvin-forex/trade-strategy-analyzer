#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
訊號級 Walk-Forward 分析（PRD 14.5.1）
====================================
填補 PRD 14.5.1 真缺口：而家倉庫只有組合級順序回測（scripts/portfolio_v2_analyzer.py:185），
呢個腳本做「訊號級」——將單一信號歷史按月切成 K 個時期，相鄰期做 train/test 對比：

  - Period N 訓練（以第 N 期表現做「選擇依據」）→ Period N+1 測試（第 N+1 期實際經歷）
  - 模擬「投資者根據過往窗口揀信號、下一窗口實際體驗」嘅真實環境
  - 量度 PF 保留率、勝率滑落、期望值變號、樣本外 DD 擴張 → 六維過擬合風險評分（0-100）

數據真相來源（每次執行自行核實並寫入報告）：
  1. data/history/signal_*.json —— 動態核實：本倉庫 .gitignore 咗呢個目錄（commit 646c52a7，
     本地保留）。佢係「派生備份」——每個 JSON 嘅 source_file 欄位都指返 downloads/ 嘅
     AlgoForest CSV，由隊友並行 pipeline 持續刷新。存在時只用作交叉核對，不作分析基準；
  2. downloads/*.csv —— 一手來源（兩種命名：{id}.csv 同 forex-forest-signals-page-{id}.csv），
     全部現有分析器（portfolio_v2_analyzer.py 等）嘅既定輸入，作為分析基準；
     同一 ID 兩份都有時，取月份覆蓋較長者（平手取交易數較多；再平手取長名，
     與 portfolio_v2_analyzer.py 讀取慣例一致）。
  兩者皆無 → 報錯退出。

用法：
  python scripts/signal_walk_forward.py                              # 預設 5 個代表性信號、6 期
  python scripts/signal_walk_forward.py --signals 165,537 --periods 12
  python scripts/signal_walk_forward.py --signals all                # 全部覆蓋足夠嘅信號（較慢）

輸出：
  docs/signal_walk_forward.html            TSA dark theme 報告（每期 train/test 對比表）
  data/signal_walk_forward_results.json    機讀結果

取捨說明（PRD 原文係 12 期）：預設 6 期。所選信號歷史 21-39 個月，切 12 期每期只剩
1.75-3.25 個月，低頻信號單期交易數太少、窗口統計不穩；6 期每期 3.5-6.5 個月，單期樣本
足夠，代價係對比期數由 11 對減到 5 對。要 12 期加 --periods 12。

只做分析，唔改任何評分／排名代碼（dde_v5_scorer.py、排名腳本一律不掂）。
市場狀態偵測（PRD 14.5.2）已在 src/indicators.py:153（ADX regime）落地於深度分析管線，
唔屬本腳本範圍。
"""

import argparse
import csv
import glob
import html
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median

HKT = timezone(timedelta(hours=8))

# 與 portfolio_v2_analyzer.py:20 相同嘅非交易列關鍵字
BALANCE_KEYWORDS = frozenset(("balance", "deposit", "withdrawal", "transfer", "bonus"))

CSV_NAME_RE = re.compile(r"^(?:forex-forest-signals-page-)?(\d+)\.csv$", re.IGNORECASE)

NOTIONAL_CAPITAL = 10000.0   # 與 portfolio_v2_analyzer.py 順序回測相同嘅名義資本（令 DD% 有意義）
PF_CAP = 99.0                # PF 顯示上限（無虧損月慣例 99）

DEFAULT_SIGNALS = ["165", "537", "3291", "1165", "5117"]


# ──────────────────────────────────────────
# 1. CSV 讀取（欄位／過濾慣例跟 portfolio_v2_analyzer.py）
# ──────────────────────────────────────────

def parse_month(ts: str):
    """抽出 'YYYY-MM'；支援 AlgoForest 'DD/MM/YYYY HH:MM:SS' 及 ISO 格式。"""
    if not ts:
        return None
    ts = ts.strip()
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(ts, fmt).strftime("%Y-%m")
        except ValueError:
            continue
    return None


def load_signal_csv(path: str) -> list:
    """讀單一信號 CSV，回傳交易 list（剔除 balance 類同空 Symbol 列）。"""
    trades = []
    try:
        with open(path, newline="", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                try:
                    ttype = (row.get("Type") or "").strip().lower()
                    if ttype in BALANCE_KEYWORDS:
                        continue
                    symbol = (row.get("Symbol") or "").strip()
                    if not symbol:
                        continue
                    trades.append({
                        "open_time": row.get("Open Time", ""),
                        "close_time": row.get("Close Time", ""),
                        "lots": float(row.get("Lots", 0) or 0),
                        "net_pips": float(row.get("Net Pips", 0) or 0),
                        # 每筆折算 per-0.01-lot PnL，令唔同 lot 規模嘅窗口可比（V2 慣例）
                        "pnl_001": float(row.get("Net Profit", 0) or 0) / max(float(row.get("Lots", 0) or 0), 0.01) * 0.01,
                        "symbol": symbol,
                    })
                except (ValueError, TypeError):
                    continue
    except OSError:
        return []
    return trades


def trades_by_month(trades: list) -> dict:
    """按月份分組（close_time 優先，冇就 open_time）。"""
    monthly = defaultdict(list)
    for t in trades:
        m = parse_month(t.get("close_time") or t.get("open_time"))
        if m:
            monthly[m].append(t)
    return dict(monthly)


def month_axis(first: str, last: str) -> list:
    """由 first 到 last 嘅連續月份軸（中間空檔月補 0 交易——休眠期都係真實樣本外風險）。"""
    fy, fm = int(first[:4]), int(first[5:7])
    ly, lm = int(last[:4]), int(last[5:7])
    axis, y, m = [], fy, fm
    while (y, m) <= (ly, lm):
        axis.append(f"{y:04d}-{m:02d}")
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return axis


# ──────────────────────────────────────────
# 2. 數據真相來源核實（每次執行都做，結論寫入報告）
# ──────────────────────────────────────────

def probe_data_sources(repo_root: str) -> dict:
    """核實 PRD 簡報提出嘅兩個候選來源，回傳可寫入報告嘅核實結果。

    判定規則（講明喺報告）：
    - data/history/signal_*.json 係派生備份（source_file 指返 downloads/ CSV，且由隊友
      pipeline 持續刷新）——就算存在都只作交叉核對，不作分析基準；
    - downloads/ CSV 係一手來源＋現有分析器既定輸入 → 分析基準；
    - 兩者皆無 → source=none，報錯退出。
    """
    hist_glob = os.path.join(repo_root, "data", "history", "signal_*.json")
    hist_files = sorted(glob.glob(hist_glob))

    dl_dir = os.path.join(repo_root, "downloads")
    long_csvs, short_csvs, ids = [], [], set()
    if os.path.isdir(dl_dir):
        for fn in os.listdir(dl_dir):
            m = CSV_NAME_RE.match(fn)
            if not m:
                continue
            ids.add(m.group(1))
            (long_csvs if "forex-forest" in fn.lower() else short_csvs).append(fn)

    n_hist, n_csv = len(hist_files), len(long_csvs) + len(short_csvs)
    if n_csv:
        if n_hist:
            decision = (
                f"兩者並存：data/history/signal_*.json 有 {n_hist} 個（派生備份：source_file 指返 downloads/ CSV、"
                f"由並行 pipeline 持續刷新、經 .gitignore 不入庫）；downloads/ 有 {n_csv} 個信號 CSV"
                f"（長名 {len(long_csvs)}、短名 {len(short_csvs)}、去重後 {len(ids)} 個 ID，一手來源）。"
                f"分析基準採用 downloads/ CSV（一手、覆蓋較廣、與 portfolio_v2_analyzer.py 同源）；"
                f"JSON 只作逐信號 trade_count 交叉核對。"
            )
        else:
            decision = (
                f"data/history/signal_*.json 經 glob 核實為 0 個檔案（不採用）；"
                f"downloads/ 實際存在 {n_csv} 個信號 CSV"
                f"（長名 {len(long_csvs)}、短名 {len(short_csvs)}、去重後 {len(ids)} 個信號 ID），採用 downloads/ CSV。"
            )
        source = "csv"
    elif n_hist:
        decision = (
            f"data/history/signal_*.json 有 {n_hist} 個，但 downloads/ 搵唔到信號 CSV。"
            "JSON 屬派生備份（本腳本不作分析基準），請先回復 downloads/ CSV 來源。"
        )
        source = "none"
    else:
        decision = "兩個候選來源都冇數據：data/history/signal_*.json 0 個檔案；downloads/ 搵唔到信號 CSV。"
        source = "none"

    return {
        "checked_at": datetime.now(HKT).strftime("%Y-%m-%d %H:%M HKT"),
        "json_history_count": n_hist,
        "csv_total": n_csv,
        "csv_long_named": len(long_csvs),
        "csv_short_named": len(short_csvs),
        "csv_unique_ids": len(ids),
        "source": source,
        "decision": decision,
    }


def cross_check_json_backup(repo_root: str, signal_id: str, csv_file: str, csv_trades: int) -> dict:
    """逐信號交叉核對 JSON 備份（best-effort：pipeline 可能正在寫入，讀失敗就記錄原因唔中斷）。"""
    path = os.path.join(repo_root, "data", "history", f"signal_{signal_id}.json")
    if not os.path.isfile(path):
        return {"json_exists": False}
    try:
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        src = (d.get("source_file") or "").strip()
        jt = d.get("trade_count")
        return {
            "json_exists": True,
            "json_trade_count": jt,
            "json_source_file": src,
            "json_backup_date": d.get("backup_date"),
            "same_source_file": src.lower() == os.path.basename(csv_file).lower(),
            "trade_count_diff": (jt - csv_trades) if isinstance(jt, int) else None,
        }
    except (OSError, ValueError) as e:
        return {"json_exists": True, "json_error": f"讀取失敗（可能正在寫入）：{e}"}


def resolve_signal_csv(repo_root: str, signal_id: str, csv_dir_name: str = "downloads"):
    """同一 ID 有短名／長名兩份 CSV 時，逐份探測覆蓋後擇優。

    規則（講明喺報告）：月份覆蓋長者勝 → 平手交易數多者勝 → 再平手長名勝
    （長名係 portfolio_v2_analyzer.py 嘅讀取慣例）。
    """
    dl = os.path.join(repo_root, csv_dir_name)
    candidates = []
    for fn in (f"{signal_id}.csv", f"forex-forest-signals-page-{signal_id}.csv"):
        p = os.path.join(dl, fn)
        if os.path.isfile(p):
            months = trades_by_month(load_signal_csv(p))
            n_months = len(month_axis(min(months), max(months))) if months else 0
            candidates.append({
                "path": p, "file": fn,
                "n_months": n_months, "n_trades": sum(len(v) for v in months.values()),
            })
    if not candidates:
        return None, None
    candidates.sort(key=lambda c: (c["n_months"], c["n_trades"], "forex-forest" in c["file"].lower()), reverse=True)
    best = candidates[0]
    return best, candidates


# ──────────────────────────────────────────
# 3. Walk-Forward 核心（PRD 14.5.1：Period N 訓練 / N+1 測試）
# ──────────────────────────────────────────

def split_periods(n_months: int, k: int) -> list:
    """將 n_months 個月切成 k 個接近等長嘅時期，回傳 [(start_idx, end_idx)]（含端點）。"""
    base, rem = divmod(n_months, k)
    periods, start = [], 0
    for i in range(k):
        size = base + (1 if i < rem else 0)
        periods.append((start, start + size - 1))
        start += size
    return periods


def window_metrics(axis_slice: list, trades_in: dict, min_trades: int) -> dict:
    """單一時期指標：per-0.01-lot PnL、勝率、PF、期望值、窗口內月度權益 max DD%。"""
    pnls, wins, losses, n_trades = [], 0, 0, 0
    for m in axis_slice:
        for t in trades_in.get(m, []):
            pnls.append(t["pnl_001"])
            n_trades += 1
            if t["pnl_001"] > 0:
                wins += 1
            else:
                losses += 1

    total = sum(pnls)
    gross_win = sum(p for p in pnls if p > 0)
    gross_loss = abs(sum(p for p in pnls if p <= 0))

    # 窗口內逐月權益 DD（名義資本 $10,000，同組合級 WF 口徑）
    equity, peak, max_dd_pct = NOTIONAL_CAPITAL, NOTIONAL_CAPITAL, 0.0
    for m in axis_slice:
        equity += sum(t["pnl_001"] for t in trades_in.get(m, []))
        peak = max(peak, equity)
        if peak > 0:
            max_dd_pct = max(max_dd_pct, (peak - equity) / peak * 100)

    return {
        "months": f"{axis_slice[0]} ~ {axis_slice[-1]}",
        "n_months": len(axis_slice),
        "trades": n_trades,
        "sufficient": n_trades >= min_trades,
        "win_rate": round(wins / n_trades * 100, 1) if n_trades else None,
        "profit_factor": round(min(gross_win / gross_loss, PF_CAP), 2) if gross_loss > 0 else (PF_CAP if gross_win > 0 else (0.0 if n_trades else None)),
        "expectancy": round(total / n_trades, 2) if n_trades else None,
        "pnl_001": round(total, 2),
        "max_dd_pct": round(max_dd_pct, 2),
    }


def analyze_signal(signal_id: str, trades: list, k: int, min_trades: int) -> dict:
    """單信號 K 期 walk-forward：相鄰期對比＋六維過擬合評分。"""
    trades_in = trades_by_month(trades)
    if not trades_in:
        return {"signal_id": signal_id, "error": "CSV 冇有效交易數據"}
    all_months = month_axis(min(trades_in), max(trades_in))
    if len(all_months) < k:
        return {"signal_id": signal_id, "error": f"月份覆蓋（{len(all_months)} 個月）不足以切 {k} 期"}

    periods = split_periods(len(all_months), k)
    pairs = []
    for i in range(k - 1):
        tr_slice = all_months[periods[i][0]:periods[i][1] + 1]
        te_slice = all_months[periods[i + 1][0]:periods[i + 1][1] + 1]
        train, test = window_metrics(tr_slice, trades_in, min_trades), window_metrics(te_slice, trades_in, min_trades)

        valid = train["sufficient"] and test["sufficient"]
        pf_retention = None
        if valid and train["profit_factor"] is not None and train["profit_factor"] >= 1.0 and test["profit_factor"] is not None:
            pf_retention = round(test["profit_factor"] / train["profit_factor"], 3)

        pair_verdict = "insufficient"
        if valid:
            if test["pnl_001"] > 0 and (train["profit_factor"] < 1.0 or (pf_retention or 0) >= 0.6):
                pair_verdict = "hold"
            elif test["pnl_001"] > 0:
                pair_verdict = "fade_profit"
            else:
                pair_verdict = "flip"

        pairs.append({
            "pair": f"P{i + 1}→P{i + 2}",
            "train": train, "test": test,
            "valid": valid,
            "pf_retention": pf_retention,
            "wr_delta": round(test["win_rate"] - train["win_rate"], 1) if (valid and train["win_rate"] is not None and test["win_rate"] is not None) else None,
            "dd_ratio": round(test["max_dd_pct"] / train["max_dd_pct"], 2) if (valid and train["max_dd_pct"] > 0) else None,
            "verdict": pair_verdict,
        })

    result = {
        "signal_id": signal_id,
        "months_span": f"{all_months[0]} ~ {all_months[-1]}",
        "n_months": len(all_months),
        "total_trades": len(trades),
        "symbols": sorted({t["symbol"] for t in trades})[:8],
        "period_map": [{"period": f"P{i + 1}", "months": all_months[s:e + 1][0] + " ~ " + all_months[s:e + 1][-1], "n_months": e - s + 1} for i, (s, e) in enumerate(periods)],
        "pairs": pairs,
    }
    result.update(rubric(pairs))
    return result


def rubric(pairs: list) -> dict:
    """六維過擬合風險評分（0-100，分數越高＝train 表現越難延續到 test）。

    C1 PF 保留率中位（僅計 train PF≥1 嘅有效期對）……滿分 30
    C2 樣本外盈利期比例（test PnL>0）…………………………滿分 20
    C3 勝率滑落中位（pp）…………………………………………滿分 16
    C4 期望值變號比例 ≥40% ………………………………………滿分 12
    C5 有效期對比例 …………………………………………………滿分 12
    C6 樣本外 DD 擴張中位（test DD/train DD）………………滿分 10
    判定：0-25 低｜26-55 中｜56-100 高
    """
    valid = [p for p in pairs if p["valid"]]
    total_pairs = len(pairs)
    detail, notes = {}, []

    if not valid:
        return {"score": None, "rating": "數據不足", "rubric": {}, "conclusion": "有效 train/test 期對不足，無法判定過擬合風險。"}

    # C1：PF 保留率（train 本身虧損嘅期對唔計入——佢唔係「好成績點解唔延續」嘅問題）
    rets = [p["pf_retention"] for p in valid if p["pf_retention"] is not None]
    if rets:
        med_ret = median(rets)
        detail["C1_pf_retention_median"] = round(med_ret, 3)
        c1 = 0 if med_ret >= 0.85 else 10 if med_ret >= 0.6 else 20 if med_ret >= 0.35 else 30
    else:
        med_ret = None
        c1 = 15
        notes.append("C1：冇 train PF≥1 嘅有效期對，計中間分 15")

    # C2：樣本外盈利期比例
    pos_rate = sum(1 for p in valid if p["test"]["pnl_001"] > 0) / len(valid)
    detail["C2_oos_positive_rate"] = round(pos_rate, 3)
    c2 = 0 if pos_rate >= 0.667 else 10 if pos_rate >= 0.5 else 20

    # C3：勝率滑落
    wr_deltas = [p["wr_delta"] for p in valid if p["wr_delta"] is not None]
    med_wr = median(wr_deltas) if wr_deltas else None
    detail["C3_wr_delta_median_pp"] = med_wr
    c3 = 0 if med_wr is None or med_wr >= -3 else 8 if med_wr >= -8 else 16

    # C4：期望值變號比例
    flips = sum(1 for p in valid
                if p["train"]["expectancy"] is not None and p["test"]["expectancy"] is not None
                and (p["train"]["expectancy"] > 0) != (p["test"]["expectancy"] > 0))
    flip_rate = flips / len(valid)
    detail["C4_expectancy_flip_rate"] = round(flip_rate, 3)
    c4 = 0 if flip_rate < 0.4 else 12

    # C5：樣本充足度
    valid_rate = len(valid) / total_pairs if total_pairs else 0
    detail["C5_valid_pair_rate"] = round(valid_rate, 3)
    c5 = 0 if valid_rate >= 0.8 else 6 if valid_rate >= 0.5 else 12

    # C6：DD 擴張
    dd_ratios = [p["dd_ratio"] for p in valid if p["dd_ratio"] is not None]
    med_dd = median(dd_ratios) if dd_ratios else None
    detail["C6_dd_ratio_median"] = med_dd
    c6 = 0 if med_dd is None or med_dd <= 1.0 else 4 if med_dd <= 1.5 else 10

    score = c1 + c2 + c3 + c4 + c5 + c6
    rating = "低" if score <= 25 else "中" if score <= 55 else "高"
    detail.update({"weights": {"C1": c1, "C2": c2, "C3": c3, "C4": c4, "C5": c5, "C6": c6}})

    ret_txt = f"{med_ret:.0%}" if med_ret is not None else "N/A"
    wr_txt = f"{med_wr:+.1f}pp" if med_wr is not None else "N/A"
    if rating == "低":
        conclusion = (f"各期 train 表現穩定延續到 test（PF 保留率中位 {ret_txt}、樣本外盈利期 {pos_rate:.0%}、"
                      f"勝率變化 {wr_txt}）—— 過擬合風險低。")
    elif rating == "中":
        conclusion = (f"部分期數出現衰減（PF 保留率中位 {ret_txt}、樣本外盈利期 {pos_rate:.0%}、"
                      f"勝率變化 {wr_txt}）—— 過擬合風險中等。")
    else:
        conclusion = (f"train 期表現明顯未能延續（PF 保留率中位 {ret_txt}、樣本外盈利期只有 {pos_rate:.0%}、"
                      f"勝率變化 {wr_txt}）—— 過擬合風險高。")
    if notes:
        conclusion += "（" + "；".join(notes) + "）"
    return {"score": score, "rating": rating, "rubric": detail, "conclusion": conclusion}


# ──────────────────────────────────────────
# 4. EA 名（可選裝飾，只讀 signal_lot_mapping.json）
# ──────────────────────────────────────────

def load_ea_names(repo_root: str) -> dict:
    try:
        with open(os.path.join(repo_root, "signal_lot_mapping.json"), encoding="utf-8") as f:
            data = json.load(f)
        out = {}
        for sid, info in (data.get("signals") or {}).items():
            eas = [e.get("ea_id", "?") for e in (info.get("eas") or [])]
            out[str(sid)] = ", ".join(dict.fromkeys(eas))[:48] if eas else "-"
        return out
    except (OSError, ValueError):
        return {}


# ──────────────────────────────────────────
# 5. HTML 報告（TSA dark theme，觀感跟 portfolio_master_report_v2）
# ──────────────────────────────────────────

CSS = """:root{--bg:#0d1117;--card:#161b22;--muted:#8b949e;--border:#30363d;--fg:#e6edf3;--accent:#58a6ff;--green:#3fb950;--red:#f85149;--yellow:#d29922;--purple:#bc8cff}
[data-theme="light"]{--bg:#f5f7fa;--card:#ffffff;--muted:#666;--border:#ddd;--fg:#333;--accent:#0f3460;--green:#28a745;--red:#dc3545;--yellow:#ffc107;--purple:#6c5ce7}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Noto Sans TC','Helvetica Neue',Arial,sans-serif;line-height:1.55}.container{max-width:1280px;margin:0 auto;padding:24px}.hero{padding:28px;background:linear-gradient(135deg,#1f6feb33,#bc8cff22);border:1px solid var(--border);border-radius:18px;margin-bottom:20px}h1{margin:0 0 8px;font-size:34px}h2{margin:28px 0 12px;border-left:4px solid var(--accent);padding-left:12px}h3{margin:20px 0 10px}.meta{color:var(--muted)}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}.card{background:var(--card);border:1px solid var(--border);border-radius:14px;padding:16px}.label{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}.value{font-size:24px;font-weight:700;margin-top:4px}.positive{color:var(--green)}.negative{color:var(--red)}.warn{color:var(--yellow)}.pill{display:inline-block;padding:4px 9px;border-radius:999px;border:1px solid var(--border);background:var(--card);margin:2px;font-size:12px}.pill.good{border-color:var(--green);color:var(--green)}.pill.warn{border-color:var(--yellow);color:var(--yellow)}.pill.bad{border-color:var(--red);color:var(--red)}.pill.muted{border-color:var(--muted);color:var(--muted)}table{width:100%;border-collapse:collapse;background:var(--card);border:1px solid var(--border);border-radius:12px;overflow:hidden;margin:12px 0}th,td{border-bottom:1px solid var(--border);padding:10px;text-align:left;font-size:14px;vertical-align:top}th{background:var(--card);color:var(--fg);position:sticky;top:0}tr:hover{background:rgba(128,128,128,0.06)}.small{font-size:12px;color:var(--muted)}.section{background:rgba(128,128,128,0.06);border:1px solid var(--border);border-radius:16px;padding:18px;margin:18px 0}.note{border-left:4px solid var(--yellow);background:rgba(210,153,34,0.08);padding:12px;border-radius:8px}.footer{margin-top:40px;color:var(--muted);font-size:12px}.num{text-align:right;font-variant-numeric:tabular-nums}@media(max-width:720px){.container{padding:12px}h1{font-size:26px}th,td{font-size:12px;padding:7px}.value{font-size:20px}}"""

THEME_BOOT = """<script>
(function(){
  const saved=localStorage.getItem('tsa-theme');
  const t=saved||'dark';
  document.documentElement.setAttribute('data-theme',t);
})();
</script>"""


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def cls_for_rating(rating: str) -> str:
    return {"低": "good", "中": "warn", "高": "bad"}.get(rating, "muted")


def money(v, signed=True) -> str:
    if v is None:
        return "—"
    sign = "+" if signed and v > 0 else ""
    return f"{sign}${v:,.2f}"


def num(v, nd=2, suffix="") -> str:
    return "—" if v is None else f"{v:.{nd}f}{suffix}"


def pct(v) -> str:
    return "—" if v is None else f"{v:.1f}%"


def pair_verdict_pill(v: str) -> str:
    m = {
        "hold": ("good", "✓ 延續"),
        "fade_profit": ("warn", "衰減但盈利"),
        "flip": ("bad", "✗ 反轉"),
        "insufficient": ("muted", "數據不足"),
    }.get(v, ("muted", v))
    return f'<span class="pill {m[0]}">{esc(m[1])}</span>'


def build_html(results: list, meta: dict) -> str:
    ts = meta["generated_at"]
    k = meta["periods"]
    ok = [r for r in results if "error" not in r]
    n_low = sum(1 for r in ok if r.get("rating") == "低")
    n_mid = sum(1 for r in ok if r.get("rating") == "中")
    n_high = sum(1 for r in ok if r.get("rating") == "高")

    parts = []
    parts.append(f'<!doctype html><html lang="zh-Hant"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>訊號級 Walk-Forward 分析</title>')
    parts.append(THEME_BOOT)
    parts.append(f"<style>{CSS}</style>")
    parts.append('<link rel="stylesheet" href="sidebar.css">')
    parts.append('</head><body>')
    parts.append('<div id="sidebar-container"></div>')
    parts.append('<div class="container">')

    # hero
    parts.append(
        '<div class="hero">'
        f'<h1>訊號級 Walk-Forward 分析</h1>'
        f'<div class="meta">PRD 14.5.1｜{k} 期 train/test（Period N 訓練 → N+1 測試）｜{len(ok)} 個信號｜Generated: {esc(ts)}</div>'
        '</div>'
    )

    # 數據真相來源核實
    probe = meta["data_source"]
    parts.append(
        '<div class="note"><strong>數據真相來源核實（每次執行自動重做）：</strong>'
        f'{esc(probe["decision"])}'
        '<br>同一信號 ID 有兩份 CSV（短名／長名快照）時，取<span class="warn">月份覆蓋較長</span>者，'
        '平手取交易數較多者，再平手取長名（portfolio_v2_analyzer.py 慣例）。'
        f'<span class="small">核實時間：{esc(probe["checked_at"])}</span></div>'
    )

    # JSON 備份交叉核對摘要（僅當 JSON 存在時顯示）
    xchecks = [r.get("json_cross_check", {}) for r in results if "error" not in r]
    have_json = [x for x in xchecks if x.get("json_exists") and x.get("json_trade_count") is not None]
    if probe.get("json_history_count") and have_json:
        diffs = [x["trade_count_diff"] for x in have_json if x["trade_count_diff"] is not None]
        diff_txt = f"{min(diffs):+d} ～ {max(diffs):+d}" if diffs else "—"
        diff_src = sum(1 for x in have_json if not x.get("same_source_file"))
        parts.append(
            '<div class="note"><strong>JSON 備份交叉核對：</strong>'
            f'{len(have_json)}/{len(xchecks)} 個選中信號有 JSON 備份，trade_count 差異（JSON−CSV）{esc(diff_txt)}。'
            '差異嚟自兩邊過濾口徑／快照時間點唔同（JSON 屬派生備份、由並行 pipeline 持續刷新；'
            f'{diff_src} 個備份源自另一份同名 ID 嘅 CSV 快照）——呢啲差異唔影響本分析：基準一律係揀優後嘅 CSV。逐信號明細喺下面各節。</div>'
        )

    # summary cards
    parts.append('<div class="grid">')
    parts.append(f'<div class="card"><div class="label">分析信號</div><div class="value">{len(ok)}</div></div>')
    parts.append(f'<div class="card"><div class="label">切分時期</div><div class="value">{k} 期</div></div>')
    parts.append(f'<div class="card"><div class="label">過擬合風險 低</div><div class="value positive">{n_low}</div></div>')
    parts.append(f'<div class="card"><div class="label">過擬合風險 中</div><div class="value warn">{n_mid}</div></div>')
    parts.append(f'<div class="card"><div class="label">過擬合風險 高</div><div class="value negative">{n_high}</div></div>')
    parts.append(f'<div class="card"><div class="label">數據來源</div><div class="value" style="font-size:16px">downloads/ CSV</div></div>')
    parts.append('</div>')

    # 總覽表
    parts.append('<h2>信號總覽（每個一行結論）</h2>')
    parts.append('<table><thead><tr><th>Signal</th><th>EA</th><th>數據期</th><th>有效對比</th>'
                 '<th class="num">PF 保留率(中位)</th><th class="num">樣本外盈利期</th><th class="num">勝率變化(中位)</th>'
                 '<th class="num">評分</th><th>過擬合風險</th><th>一行結論</th></tr></thead><tbody>')
    for r in ok:
        rb = r.get("rubric", {})
        valid_n = sum(1 for p in r["pairs"] if p["valid"])
        ret = rb.get("C1_pf_retention_median")
        pos = rb.get("C2_oos_positive_rate")
        wrd = rb.get("C3_wr_delta_median_pp")
        rating = r.get("rating", "數據不足")
        c = cls_for_rating(rating)
        parts.append(
            f'<tr><td><strong>{esc(r["signal_id"])}</strong></td>'
            f'<td class="small">{esc(r.get("ea_name", "-"))}</td>'
            f'<td class="small">{esc(r["months_span"])}<br><span class="small">{r["n_months"]} 個月・{r["total_trades"]:,} 筆</span></td>'
            f'<td class="num">{valid_n}/{len(r["pairs"])}</td>'
            f'<td class="num">{num(ret * 100, 0, "%") if ret is not None else "—"}</td>'
            f'<td class="num">{num(pos * 100, 0, "%") if pos is not None else "—"}</td>'
            f'<td class="num">{f"{wrd:+.1f}pp" if wrd is not None else "—"}</td>'
            f'<td class="num">{r.get("score") if r.get("score") is not None else "—"}/100</td>'
            f'<td><span class="pill {c}">{esc(rating)}</span></td>'
            f'<td class="small">{esc(r.get("conclusion", "—"))}</td></tr>'
        )
    for r in results:
        if "error" in r:
            parts.append(f'<tr><td><strong>{esc(r["signal_id"])}</strong></td><td colspan="9" class="small">⚠ {esc(r["error"])}</td></tr>')
    parts.append('</tbody></table>')

    # 方法論
    parts.append('<h2>方法論</h2><div class="section">')
    parts.append(
        '<p>按 <strong>PRD 14.5.1</strong>：將信號全部歷史（按月、含休眠空檔月）切成 <strong>K 個等長時期</strong>，'
        f'對每對相鄰時期做 <strong>Period N 訓練 / Period N+1 測試</strong>（今次 K={k}，即 {k - 1} 個對比）。'
        '「訓練」＝以第 N 期表現做選擇依據（投資者睇過往窗口決定跟唔跟）；「測試」＝第 N+1 期實際經歷。'
        '所有金額按 <strong>per-0.01-lot</strong> 折算（與組合級 WF 同口徑），DD 用名義資本 $10,000 逐月權益計。</p>'
        '<p>單期交易數 &lt; min_trades（預設 10）視為<strong>數據不足</strong>，該期對唔計入統計。過擬合風險評分（0-100，越高越危險）：</p>'
        '<table><thead><tr><th>維度</th><th>量度</th><th class="num">滿分</th></tr></thead><tbody>'
        '<tr><td>C1 PF 保留率</td><td class="small">test PF / train PF 中位（僅計 train PF≥1 嘅有效期對）</td><td class="num">30</td></tr>'
        '<tr><td>C2 樣本外盈利</td><td class="small">test 窗口 PnL&gt;0 嘅期對比例</td><td class="num">20</td></tr>'
        '<tr><td>C3 勝率滑落</td><td class="small">test WR − train WR 中位（pp）</td><td class="num">16</td></tr>'
        '<tr><td>C4 期望值變號</td><td class="small">train/test 期望值正負變號比例 ≥40%</td><td class="num">12</td></tr>'
        '<tr><td>C5 樣本充足</td><td class="small">有效期對 / 全部期對</td><td class="num">12</td></tr>'
        '<tr><td>C6 DD 擴張</td><td class="small">test DD% / train DD% 中位</td><td class="num">10</td></tr>'
        '</tbody></table>'
        '<p class="small">判定：0-25 低｜26-55 中｜56-100 高。呢個係「表現持續性」量度，唔係盈利能力量度——低風險只代表 past window 表現可信地延續，唔代表信號一定賺錢。</p>'
        '</div>'
    )

    # 期數取捨
    parts.append(
        '<div class="note"><strong>期數取捨（PRD 原文 12 期，本次預設 6 期）：</strong>'
        '所選信號歷史 21-39 個月；切 12 期每期僅 1.75-3.25 個月，低頻信號單期交易數跌穿統計可用水平，'
        '窗口指標（WR/PF/DD）會被個別月份支配；6 期每期 3.5-6.5 個月，單期樣本足夠，代價係對比期數由 11 對減到 5 對、'
        '趨勢轉變偵測較粗。歷史 ≥36 個月嘅信號（如 165）用 <code>--periods 12</code> 仍然可行。後續全部 67+ 信號跑齊時，'
        '可按各信號月份數自動選 6 或 12 期。</div>'
    )

    # per-signal sections
    for r in ok:
        sid = r["signal_id"]
        parts.append(f'<h2 id="s{sid}">Signal {esc(sid)} — {esc(r.get("ea_name", "-"))}</h2>')
        parts.append('<div class="section">')
        pm = "・".join(f'{p["period"]}: {p["months"]}' for p in r["period_map"])
        parts.append(f'<p class="small">時期切分（{r["n_months"]} 個月 → {len(r["period_map"])} 期）：{esc(pm)}</p>')
        xc = r.get("json_cross_check", {})
        if xc.get("json_exists") and xc.get("json_trade_count") is not None:
            src_note = "" if xc.get("same_source_file") else "（備份源自另一份同名 ID CSV 快照）"
            parts.append(
                f'<p class="small">📋 數據核對：分析基準 <code>{esc(r["csv_used"])}</code>（{r["total_trades"]:,} 筆）｜'
                f'JSON 備份 trade_count {xc["json_trade_count"]:,}（差 {xc["trade_count_diff"]:+d}）{esc(src_note)}｜備份時間 {esc(xc.get("json_backup_date", "—"))}</p>'
            )
        elif xc.get("json_exists"):
            parts.append(f'<p class="small">📋 數據核對：JSON 備份讀取失敗（{esc(xc.get("json_error", "未知"))}），基準 <code>{esc(r["csv_used"])}</code></p>')
        else:
            parts.append(f'<p class="small">📋 數據核對：無 JSON 備份，基準 <code>{esc(r["csv_used"])}</code>（{r["total_trades"]:,} 筆）</p>')
        parts.append(f'<p><span class="pill {cls_for_rating(r.get("rating", ""))}">過擬合風險：{esc(r.get("rating", "—"))}'
                     f'（{r.get("score") if r.get("score") is not None else "—"}/100）</span> '
                     f'<span class="small">主要交易品種：{esc(", ".join(r["symbols"]))}</span></p>')
        # 每期 train/test 對比表
        parts.append('<table><thead><tr><th>期對</th>'
                     '<th>Train 窗口</th><th class="num">交易</th><th class="num">勝率</th><th class="num">PF</th><th class="num">期望值</th><th class="num">PnL</th><th class="num">DD%</th>'
                     '<th>Test 窗口</th><th class="num">交易</th><th class="num">勝率</th><th class="num">PF</th><th class="num">期望值</th><th class="num">PnL</th><th class="num">DD%</th>'
                     '<th class="num">PF保留率</th><th class="num">WRΔ</th><th>判定</th></tr></thead><tbody>')
        for p in r["pairs"]:
            tr, te = p["train"], p["test"]
            dim = ' style="opacity:.45"' if not p["valid"] else ""
            ret_txt = f"{p['pf_retention'] * 100:.0f}%" if p["pf_retention"] is not None else "—"
            wr_txt = f"{p['wr_delta']:+.1f}" if p["wr_delta"] is not None else "—"
            parts.append(
                f'<tr{dim}><td><strong>{esc(p["pair"])}</strong></td>'
                f'<td class="small">{esc(tr["months"])}</td><td class="num">{tr["trades"]}</td>'
                f'<td class="num">{pct(tr["win_rate"])}</td><td class="num">{num(tr["profit_factor"])}</td>'
                f'<td class="num">{money(tr["expectancy"], signed=False)}</td>'
                f'<td class="num {"positive" if tr["pnl_001"] > 0 else "negative"}">{money(tr["pnl_001"])}</td>'
                f'<td class="num negative">{num(tr["max_dd_pct"])}%</td>'
                f'<td class="small">{esc(te["months"])}</td><td class="num">{te["trades"]}</td>'
                f'<td class="num">{pct(te["win_rate"])}</td><td class="num">{num(te["profit_factor"])}</td>'
                f'<td class="num">{money(te["expectancy"], signed=False)}</td>'
                f'<td class="num {"positive" if te["pnl_001"] > 0 else "negative"}">{money(te["pnl_001"])}</td>'
                f'<td class="num negative">{num(te["max_dd_pct"])}%</td>'
                f'<td class="num">{ret_txt}</td>'
                f'<td class="num">{wr_txt}</td>'
                f'<td>{pair_verdict_pill(p["verdict"])}</td></tr>'
            )
        parts.append('</tbody></table>')
        parts.append(f'<p class="small">結論：{esc(r.get("conclusion", "—"))}</p>')
        parts.append('</div>')

    # footer
    parts.append(
        '<div class="footer">Generated by <code>scripts/signal_walk_forward.py</code>｜PRD 14.5.1 訊號級 Walk-Forward｜'
        f'{esc(ts)}｜重跑：<code>python scripts/signal_walk_forward.py --signals {",".join(r["signal_id"] for r in ok if "error" not in r) or "165,537,3291,1165,5117"} --periods {k}</code><br>'
        '市場狀態偵測（PRD 14.5.2）已另於 src/indicators.py:153（ADX regime）落地於深度分析管線，唔在本報告範圍。本分析為新增內容，不影響任何評分／排名。</div>'
    )
    parts.append('</div><script src="sidebar.js"></script>')
    parts.append('</body></html>')
    return "\n".join(parts)


# ──────────────────────────────────────────
# 6. 主流程
# ──────────────────────────────────────────

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="訊號級 Walk-Forward 分析（PRD 14.5.1）")
    ap.add_argument("--signals", default=",".join(DEFAULT_SIGNALS),
                    help="逗號分隔信號 ID，或 all（全部數據足夠嘅信號）")
    ap.add_argument("--periods", type=int, default=6, help="切分時期數（PRD 原文 12；預設 6，講明取捨見報告）")
    ap.add_argument("--min-trades", type=int, default=10, help="單期最低交易數，低於視為數據不足（預設 10）")
    ap.add_argument("--csv-dir", default=None, help="downloads 目錄（預設 auto：<repo>/downloads）")
    ap.add_argument("--out-html", default=None, help="輸出 HTML（預設 <repo>/docs/signal_walk_forward.html）")
    ap.add_argument("--out-json", default=None, help="輸出 JSON（預設 <repo>/data/signal_walk_forward_results.json）")
    args = ap.parse_args(argv)

    if not (3 <= args.periods <= 24):
        print(f"✗ --periods 必須 3-24，收到 {args.periods}", file=sys.stderr)
        return 2

    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_dir = args.csv_dir or os.path.join(repo_root, "downloads")
    out_html = args.out_html or os.path.join(repo_root, "docs", "signal_walk_forward.html")
    out_json = args.out_json or os.path.join(repo_root, "data", "signal_walk_forward_results.json")

    # ① 數據真相來源核實（每次執行都做）
    probe = probe_data_sources(repo_root)
    print(f"[數據來源] {probe['decision']}")
    if probe["source"] == "none":
        print("✗ 兩個候選數據來源都冇數據，無法分析。", file=sys.stderr)
        return 1

    # ② 揀信號
    if args.signals.strip().lower() == "all":
        ids = sorted({CSV_NAME_RE.match(fn).group(1) for fn in os.listdir(csv_dir) if CSV_NAME_RE.match(fn)},
                     key=lambda s: int(s))
        print(f"[信號] all 模式：{len(ids)} 個信號 ID（歷史不足者會自動跳過並記錄原因）")
    else:
        ids = [s.strip() for s in args.signals.split(",") if s.strip()]

    ea_names = load_ea_names(repo_root)
    results = []
    for sid in ids:
        best, cands = resolve_signal_csv(repo_root, sid, os.path.relpath(csv_dir, repo_root) if csv_dir.startswith(repo_root) else "downloads")
        if not best:
            results.append({"signal_id": sid, "error": f"downloads/ 搵唔到 {sid}.csv 或 forex-forest-signals-page-{sid}.csv"})
            continue
        trades = load_signal_csv(best["path"])
        r = analyze_signal(sid, trades, args.periods, args.min_trades)
        r["csv_used"] = best["file"]
        r["csv_candidates"] = cands
        r["ea_name"] = ea_names.get(sid, "-")
        r["json_cross_check"] = cross_check_json_backup(repo_root, sid, best["file"], len(trades))
        results.append(r)
        if "error" in r:
            print(f"[{sid}] ✗ {r['error']}（用咗 {best['file']}）")
        else:
            xc = r["json_cross_check"]
            xc_txt = ""
            if xc.get("json_exists") and xc.get("json_trade_count") is not None:
                xc_txt = f"｜JSON 備份核對 trade_count {xc['json_trade_count']} vs CSV {len(trades)}（{xc['trade_count_diff']:+d}）"
                if not xc.get("same_source_file"):
                    xc_txt += "・備份源自另一份同名 CSV 快照"
            elif xc.get("json_exists"):
                xc_txt = f"｜JSON 備份核對失敗：{xc.get('json_error', '未知')}"
            print(f"[{sid}] {r['months_span']}｜{r['n_months']} 個月｜{r['total_trades']:,} 筆｜用 {best['file']}"
                  + (f"（同 ID 有 {len(cands)} 份 CSV，擇優）" if len(cands) > 1 else "") + xc_txt)

    meta = {
        "generated_at": datetime.now(HKT).strftime("%Y-%m-%d %H:%M HKT"),
        "periods": args.periods,
        "min_trades": args.min_trades,
        "prd_ref": "PRD 14.5.1",
        "data_source": probe,
        "signals_requested": ids,
        "rerun": f"python scripts/signal_walk_forward.py --signals {','.join(ids)} --periods {args.periods}",
    }

    os.makedirs(os.path.dirname(out_html), exist_ok=True)
    os.makedirs(os.path.dirname(out_json), exist_ok=True)
    with open(out_html, "w", encoding="utf-8", newline="\n") as f:
        f.write(build_html(results, meta))
    with open(out_json, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"meta": meta, "signals": results}, f, ensure_ascii=False, indent=1)

    # ③ 驗收要求：列出跑咗邊幾個信號＋每個一行結論
    print("\n===== 每個信號一行結論 =====")
    for r in results:
        if "error" in r:
            print(f"Signal {r['signal_id']}: ⚠ {r['error']}")
        else:
            print(f"Signal {r['signal_id']}（{r.get('ea_name', '-')}）: 過擬合風險{r['rating']}（{r['score']}/100）— {r['conclusion']}")
    ok_n = sum(1 for r in results if "error" not in r)
    print(f"\n✓ 完成：{ok_n}/{len(results)} 個信號｜HTML → {os.path.relpath(out_html, repo_root)}｜JSON → {os.path.relpath(out_json, repo_root)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
