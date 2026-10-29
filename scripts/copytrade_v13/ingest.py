# -*- coding: utf-8 -*-
"""COPYTRADE v1.3 數據基座——CSV 逐筆入庫＋馬丁週期（cycle）分組。

數據源：docs/downloads/forex-forest-signals-page-*.csv（逐筆，A 級可信度：
entry/exit/lot/price/symbol/magic/層（comment+階梯）/時間齊全——§11.7 A 條件）。

cycle 分組規則（馬丁週期＝一次完整開倉→全層平倉）：
- 同 signal × symbol × direction 內，按 open_time 排序
- 新 cycle 條件：open_time > 該群前筆 close_time（無時間重疊）
- gap 保護：與前 cycle 尾筆 close_time 相隔 > 24h 亦強制開新 cycle
- cycle 內按 open_time 編層 1..N；lots_cum 照 §5.2 累積
"""
import csv
import glob
import os
import sqlite3
from collections import defaultdict
from datetime import datetime, timedelta


def _pt(s: str):
    """時間解析——D/M/YYYY 為 broker CSV 唯一口徑（同 algoforest_analyzer TIME_FMT 一致）。

    ⚠️ 唔准先試 M/D：『12/06/2026』係 12 June 唔係 6 Dec，先試 M/D 會日月顛倒六個月。
    """
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M",
                "%Y.%m.%d %H:%M", "%Y.%m.%d %H:%M:%S",
                "%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except (ValueError, AttributeError):
            continue
    return None


def load_signal_csv(path: str):
    """讀一份 signal CSV → [trade dict]（含溯源 source_file/source_row）。"""
    out = []
    with open(path, encoding="utf-8-sig", newline="") as f:
        for i, r in enumerate(csv.DictReader(f), start=2):  # header 之後由 2 計（溯源對 Excel 行）
            typ = (r.get("Type") or "").strip().lower()
            if typ not in ("buy", "sell"):
                continue
            ct = _pt(r.get("Close Time", ""))
            if ct is None:
                continue  # 持倉中——不入庫（照 analyzer S0）
            magic = (r.get("Magic Number") or "").strip()
            out.append({
                "signal_id": os.path.basename(path).split("-")[-1].replace(".csv", ""),
                "symbol": (r.get("Symbol") or "").strip(),
                "typ": typ,
                "lots": float(r.get("Lots") or 0),
                "open_time": (r.get("Open Time") or "").strip(),
                "close_time": ct.strftime("%Y-%m-%d %H:%M"),
                "open_price": float(r.get("Open Price") or 0),
                "close_price": float(r.get("Close Price") or 0),
                "net_pips": float(r.get("Net Pips") or 0),
                "net_profit": float(r.get("Net Profit") or 0),
                "max_profit": float(r.get("Max Profit") or 0),
                "max_loss": float(r.get("Max Loss") or 0),
                "magic": magic,
                "comment": (r.get("Comment") or "").strip(),
                "source_file": os.path.basename(path),
                "source_row": i,
                "_ot": _pt(r.get("Open Time", "")) or ct,
                "_ct": ct,
            })
    out.sort(key=lambda t: t["_ct"])
    return out


def group_cycles(trades):
    """同 signal×symbol×direction → 馬丁週期群。回傳 [cycle dict]（內含 layers）。"""
    by_key = defaultdict(list)
    for t in trades:
        by_key[(t["signal_id"], t["symbol"], t["typ"])].append(t)
    cycles = []
    GAP = timedelta(hours=24)
    for (sid, sym, typ), g in sorted(by_key.items()):
        g.sort(key=lambda t: t["_ot"])
        cur = []
        for t in g:
            if cur:
                last_ct = max(x["_ct"] for x in cur)
                if t["_ot"] > last_ct or (t["_ot"] - last_ct) > GAP:
                    cycles.append(_mk_cycle(sid, sym, typ, cur))
                    cur = []
            cur.append(t)
        if cur:
            cycles.append(_mk_cycle(sid, sym, typ, cur))
    return cycles


def _mk_cycle(sid, sym, typ, members):
    members = sorted(members, key=lambda t: t["_ot"])
    layers = []
    lots_cum = 0.0
    for no, t in enumerate(members, 1):
        lots_cum += t["lots"]
        layers.append({"layer_no": no, **t, "lots_cum": round(lots_cum, 2)})
    return {
        "signal_id": sid, "symbol": sym, "direction": typ.upper(),
        "open_time": members[0]["open_time"], "close_time": max(x["close_time"] for x in members),
        "layers_n": len(members), "lots_total": round(sum(x["lots"] for x in members), 2),
        "pnl_total": round(sum(x["net_profit"] for x in members), 2),
        "data_grade": "A",
        "layers": layers,
    }


def _qc_flag(t, verify_fn):
    """兩式交叉驗證 qc_flag（§6.3）——except 收口同原版（MISSING_SPEC）。"""
    if not verify_fn:
        return None
    try:
        return verify_fn(t)[1]
    except Exception:
        return "MISSING_SPEC"


def ingest(conn: sqlite3.Connection, paths, verify_fn=None):
    """CSV→trades/cycles/layers 三表入庫；verify_fn 做兩式交叉驗證（§6.3，有 specs 先跑）。

    D4 性能：trades／layers 改 executemany 批次（26 萬筆全量逐句 INSERT 係瓶頸）。
    """
    n_tr = n_cy = n_ly = 0
    for pi, p in enumerate(paths, 1):
        trades = load_signal_csv(p)
        cycles = group_cycles(trades)
        conn.executemany(
            "INSERT INTO trades(signal_id,symbol,typ,lots,open_time,close_time,open_price,"
            "close_price,net_pips,net_profit,max_profit,max_loss,magic,comment,source_file,"
            "source_row,qc_flag) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(t["signal_id"], t["symbol"], t["typ"], t["lots"], t["open_time"], t["close_time"],
              t["open_price"], t["close_price"], t["net_pips"], t["net_profit"], t["max_profit"],
              t["max_loss"], t["magic"], t["comment"], t["source_file"], t["source_row"],
              _qc_flag(t, verify_fn)) for t in trades])
        n_tr += len(trades)
        for c in cycles:
            cur = conn.execute(
                "INSERT INTO cycles(signal_id,symbol,direction,open_time,close_time,layers_n,"
                "lots_total,pnl_total,data_grade) VALUES(?,?,?,?,?,?,?,?,?)",
                (c["signal_id"], c["symbol"], c["direction"], c["open_time"], c["close_time"],
                 c["layers_n"], c["lots_total"], c["pnl_total"], c["data_grade"]))
            cid = cur.lastrowid
            conn.executemany(
                "INSERT INTO layers(cycle_id,layer_no,lots,open_time,open_price,pnl,lots_cum)"
                " VALUES(?,?,?,?,?,?,?)",
                [(cid, L["layer_no"], L["lots"], L["open_time"], L["open_price"],
                  L["net_profit"], L["lots_cum"]) for L in c["layers"]])
            n_ly += len(c["layers"])
            n_cy += 1
        if pi % 20 == 0 or pi == len(paths):
            print(f"   …ingest {pi}/{len(paths)} 份（累計 {n_tr:,} 筆）", flush=True)
    conn.commit()
    return n_tr, n_cy, n_ly


def signal_csvs(dl_dir: str, signals=None):
    """downloads 目錄 → signal CSV 路徑清單（可指定 signal 子集）。"""
    files = sorted(glob.glob(os.path.join(dl_dir, "forex-forest-signals-page-*.csv")))
    if signals:
        want = {str(s) for s in signals}
        files = [f for f in files if os.path.basename(f).split("-")[-1].replace(".csv", "") in want]
    return files
