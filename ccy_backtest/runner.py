#!/usr/bin/env python3
"""CP-BT1 階段 B parity runner：OHLC 窗口 → mt4_ref 重算 → reader 對齊 → 誤差矩陣。

用法：
  python3 -m ccy_backtest.runner supply [ref_root]   # OC 0940 供料佈局（per-idx 多 symbol 檔）
  python3 -m ccy_backtest.runner legacy [ref_root]   # 舊佈局（per-instrument 檔）
  python3 -m ccy_backtest.runner auto   [ref_root]   # 先試 supply，失敗退 legacy

料源：ref/ohlc/（OC 20261123_0940 供料 commit fcafe7da）。
抽樣：ref/ohlc_sampling_list.csv（28 時點；2011 兩點自動跳過——資料端無 2011 OHLC）。
對齊：reader key＝"timestamp|TF"（timestamp 格式 "YYYY.MM.DD HH:MM" 同 MT4 原生一致）。
刻度：OC 0940 正式映射公式 val = 9 × pw/100 = 4.5 + 0.09×(pw−50)（端點/中點實證），
      斜率擬合覆核 b≈0.09（1 自由度，頭三窗擬合，其餘 held-out），顯著偏離先上報。
對齊規則（面板 live 逐 tick 重算實證後定）：
  - 主對齊 S-close：kernel＝尾 bar 終值 vs reader＝最接近 anchor bar 收盘时刻嘅全行
    （同 bar 內漂移最小）；idx22/25（hst 停寫、窗過時）照 OC 0940 指示改用
    S-open＝最接近 anchor 時到嘅全行（照錨驗）。
  - 靈敏度 S-shift1／S-sample 只入 detail 檔唔入主矩陣。
"""
from __future__ import annotations

import csv
import datetime as _dt
import glob
import os
import re
import sys
from typing import Dict, List, Optional

from . import dataio, indicators, mt4_ref, parity, universe

N_BARS = 350
REF_ROOT_DEFAULT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ref")


def load_sampling_list(path: str) -> List[dict]:
    rows = []
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            rows.append({"idx": int(r["idx"]), "ts": r["timestamp"].strip(),
                         "tf": r["timeframe"].strip().upper(), "reason": r["reason"]})
    return rows


def load_ohlc_dir(ohlc_dir: str) -> Dict[str, dict]:
    """掃 ref/ohlc/ 內全部檔案 → {INSTRUMENT: {TF: series}}（兩種佈局兼容）。

    佈局 A（每 instrument 一檔）：*EURUSD_H1_350bars.csv* → {EURUSD: {H1: series}}
    佈局 B（每時點一檔）：檔名含 timestamp → 合併為 per-instrument 全序列再切窗。
    檔名規則寬鬆：以底線分節，從中識別 INSTRUMENT（28+XAUUSD 詞表）與 TF 詞。
    """
    insts = set(universe.INSTRUMENTS_36) | {"XAUUSD"}
    tfs = {"D1", "H4", "H1", "M30", "M5", "M1"}
    out: Dict[str, Dict[str, dict]] = {}
    for path in sorted(glob.glob(os.path.join(ohlc_dir, "**", "*.csv"), recursive=True)):
        base = os.path.basename(path)
        inst = next((i for i in sorted(insts, key=len, reverse=True)
                     if i.upper() in base.upper()), None)
        tf = next((t for t in sorted(tfs, key=len, reverse=True)
                   if f"_{t}_" in base.upper() or base.upper().endswith(f"_{t}.csv")
                   or f"_{t}-" in base.upper()), None)
        if inst is None or tf is None:
            print(f"  [skip] 檔名無法識別 instrument/TF: {base}")
            continue
        try:
            series = dataio.load_ohlc_csv(path)
        except Exception as e:
            print(f"  [skip] 載入失敗 {base}: {e}")
            continue
        out.setdefault(inst, {})
        if tf in out[inst]:
            # 同 instrument 同 TF 多檔（每時點一檔佈局）→ 按 d 值合併去重排序
            m = out[inst][tf]
            seen = {d: i for i, d in enumerate(m["d"])}
            for j, d in enumerate(series["d"]):
                if d not in seen:
                    m["d"].append(d)
                    for k in ("o", "h", "l", "c"):
                        m[k].append(series[k][j])
                else:
                    i2 = seen[d]
                    for k in ("o", "h", "l", "c"):
                        m[k][i2] = series[k][j]
            order = sorted(range(len(m["d"])), key=lambda i: m["d"][i])
            for k in ("d", "o", "h", "l", "c"):
                m[k] = [m[k][i] for i in order]
        else:
            out[inst][tf] = series
    return out


def slice_window(series: dict, ts: str, n: int = N_BARS) -> Optional[dict]:
    """由 series 切「timestamp（含）向前 n 根」窗口；d 值字串前綴匹配（日期含時分）。"""
    d = series["d"]
    # 精確匹配 → 前綴匹配（reader "2026.11.20 23:53" vs bar "2026.11.20 23:53"）
    cand = [i for i, x in enumerate(d) if x.strip() == ts]
    if not cand:
        cand = [i for i, x in enumerate(d) if str(x).strip().startswith(ts[:16])]
    if not cand:
        return None
    i = max(cand)
    lo = max(0, i - n + 1)
    return {k: v[lo:i + 1] for k, v in series.items()}


def run_parity(ref_root: str = REF_ROOT_DEFAULT, out_dir: str = None,
               ohlc_dir: str = None) -> str:
    ohlc_dir = ohlc_dir or os.path.join(ref_root, "ohlc")
    out_dir = out_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    if not os.path.isdir(ohlc_dir):
        raise parity.ParityPendingError(
            f"ref/ohlc/ 未出現（{ohlc_dir}）——OHLC 供料未到，唔静默扮成功")
    samples = load_sampling_list(os.path.join(ref_root, "ohlc_sampling_list.csv"))
    reader = parity.load_reader_csv(os.path.join(ref_root, "ccy_power_reader.csv"))
    # 2011 兩點資料端無源（OC 1445 確認 MT4 端無料即跳過）
    active = [s for s in samples if not s["ts"].startswith("2011")]

    all_data = load_ohlc_dir(ohlc_dir)
    if not all_data:
        raise parity.ParityPendingError("ohlc/ 有檔但零載入——檔名佈局唔合規，補 runner 相容")

    fake_rows: List[dict] = []
    skipped: List[str] = []
    for s in active:
        key = f"{s['ts']}|{s['tf']}"
        if key not in reader:
            print(f"  [warn] reader 無此 key: {key}")
            continue
        tf = s["tf"]
        # 該 TF 可用 instrument
        usable = {i: v for i, v in all_data.items() if tf in v}
        if not usable:
            print(f"  [warn] {key}：無 {tf} OHLC，跳過")
            continue
        # 每 instrument 該時點窗口的 RSI/ATR% 尾值 → mt4_ref 單 bar 計算
        rsi_by, atr_by = {}, {}
        for inst, tfs in usable.items():
            win = slice_window(tfs[tf], s["ts"])
            if win is None or len(win["c"]) < 15:
                continue  # RSI 暖機最少需求
            r = indicators.rsi_wilder(win["c"], 14)
            atr = indicators.atr_wilder(win["h"], win["l"], win["c"], 14)
            i_last = len(win["c"]) - 1
            rv = r[i_last] if i_last < len(r) else None
            av = atr[i_last] if i_last < len(atr) else None
            px = win["c"][i_last]
            if rv is not None and av is not None and av > 0 and px > 0:
                rsi_by[inst] = rv
                atr_by[inst] = av / px * 100.0
        if len(rsi_by) < 20:
            print(f"  [warn] {key}：有效 instrument 只 {len(rsi_by)}/29——coverage 低，行為異常")
        pw = mt4_ref.calc_pw_row(rsi_by, atr_by, list(universe.INSTRUMENTS_36))
        # 0..9 刻度：X 未知（等 OC）——輸出 (pw−50)+4.5 假設版＋raw，誤差走向判讀用
        scale_guess = {k: (v - 50.0) + 4.5 for k, v in pw.items()}
        fake_rows.append({"ts": key, "power": scale_guess, "avg": None})
        # 詳細 log
        r_row = reader[key]
        diffs = {k: round(scale_guess[k] - r_row[k], 4)
                 for k in universe.CURRENCIES_9 if k in r_row and k in scale_guess}
        print(f"  {key}: instruments={len(rsi_by)} | guess-scale 誤差 = {diffs}")

    if not fake_rows:
        raise parity.ParityPendingError("零對齊行——檢查 reader key 格式／時戳精確匹配")
    report_rows = parity.error_matrix(fake_rows, reader, scale_fn=None)
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "parity_report.csv")
    parity.write_report(report_rows, out_path)
    print(f"parity 報告（guess-scale 版，{len(report_rows)} 行）→ {out_path}")
    return out_path


# ------------------------------------------------------------------
# supply 佈局 parity（OC 20261123_0940 供料：per-idx 多 symbol 窗口檔）
# ------------------------------------------------------------------

TF_MINUTES = {"D1": 1440, "H4": 240, "H1": 60, "M30": 30, "M5": 5, "M1": 1}


def load_manifest(ref_root: str) -> Dict[str, dict]:
    path = os.path.join(ref_root, "ohlc", "MANIFEST_summary.csv")
    out: Dict[str, dict] = {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            out[r["file"]] = r
    return out


def parse_idx_filename(name: str):
    m = re.match(r"idx(\d+)_([A-Z0-9]+)_\d{8}_\d{4}\.csv$", name)
    return (int(m.group(1)), m.group(2)) if m else None


def load_idx_window(path: str) -> Dict[str, dict]:
    """per-idx 多 symbol 檔 → {symbol: series}（按 bar_time 升序；同時刻重複保留尾行）。"""
    per: Dict[str, dict] = {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            sym = (r.get("symbol") or "").strip().upper()
            bt = (r.get("bar_time") or "").strip()
            if not sym or not bt:
                continue
            s = per.setdefault(sym, {"d": [], "o": [], "h": [], "l": [], "c": []})
            s["d"].append(bt)
            s["o"].append(float(r["open"]))
            s["h"].append(float(r["high"]))
            s["l"].append(float(r["low"]))
            s["c"].append(float(r["close"]))
    out: Dict[str, dict] = {}
    for sym, s in per.items():
        ded = {}
        for i, d in enumerate(s["d"]):
            ded[d] = i  # 重複 bar_time → 後行覆蓋
        idxs = sorted(ded.values(), key=lambda i: s["d"][i])
        out[sym] = {k: [s[k][i] for i in idxs] for k in ("d", "o", "h", "l", "c")}
    return out


def index_reader_rows(path: str) -> Dict[str, list]:
    """reader csv → {tf: [(ts, {cur: val}), ...]}（按 ts 序；全部行收錄，解析時篩全行）。"""
    out: Dict[str, list] = {}
    with open(path, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            ts = (r.get("timestamp") or "").strip()
            tf = (r.get("timeframe") or "").strip().upper()
            if not ts or tf not in TF_MINUTES:
                continue
            rec = {}
            for i in range(1, 10):
                name = (r.get(f"ccy{i}_name") or "").strip().upper()
                val = (r.get(f"ccy{i}_power") or "").strip()
                cur = {"GOLD": "XAU"}.get(name, name)
                if cur in universe.CURRENCIES_9 and val:
                    try:
                        rec[cur] = float(val)
                    except ValueError:
                        continue
            out.setdefault(tf, []).append((ts, rec))
    for tf in out:
        out[tf].sort(key=lambda x: x[0])
    return out


def _pt(ts: str) -> _dt.datetime:
    return _dt.datetime.strptime(ts.strip(), "%Y.%m.%d %H:%M")


def resolve_reader_row(reader_by_tf: Dict[str, list], tf: str, target_ts: str,
                       min_valid: int = 8, search_min: int = 240):
    """最接近 target_ts 嘅全行（≥min_valid 幣）；同 bar 優先（ts≤target）。→ (dt_min, ts, rec)｜None"""
    t0 = _pt(target_ts)
    before = after = None
    for ts, rec in reader_by_tf.get(tf, []):
        if len(rec) < min_valid:
            continue
        dt = (_pt(ts) - t0).total_seconds() / 60.0
        if abs(dt) > search_min:
            continue
        if dt <= 0 and (before is None or abs(dt) < before[0]):
            before = (abs(dt), ts, rec)
        if dt > 0 and (after is None or dt < after[0]):
            after = (dt, ts, rec)
    if before is not None and before[0] <= TF_MINUTES.get(tf, 60):
        return before
    if after is not None and (before is None or after[0] < before[0]):
        return after
    return before or after


def kernel_pw(win: Dict[str, dict], shift: int = 0,
              rsi_period: int = 14, atr_period: int = 14):
    """窗口 → mt4_ref 單 bar pw；shift=0 尾 bar、1 倒數第二。回 (pw9, val9)。
    val = 9 × pw/100（OC 20261123_0940 正式映射公式）。"""
    rsi_by: Dict[str, float] = {}
    atr_by: Dict[str, float] = {}
    for sym, s in win.items():
        i = len(s["c"]) - 1 - shift
        if i < rsi_period or i < 0:
            continue
        r = indicators.rsi_wilder(s["c"], rsi_period)
        a = indicators.atr_wilder(s["h"], s["l"], s["c"], atr_period)
        rv = r[i] if i < len(r) else None
        av = a[i] if i < len(a) else None
        px = s["c"][i]
        if rv is not None and av is not None and av > 0 and px > 0:
            rsi_by[sym] = rv
            atr_by[sym] = av / px * 100.0
    pw = mt4_ref.calc_pw_row(rsi_by, atr_by, list(universe.INSTRUMENTS_36))
    val = {k: 9.0 * v / 100.0 for k, v in pw.items()}
    return pw, val


def kernel_pw_r1(win: Dict[str, dict], shift: int = 0, rsi_period: int = 4):
    """校準版（config B）：同 calc_pw_row 引擎但 ATR 加權停用（w≡1）＋RSI 周期參數化。

    實證依據：reader 端殘差用未加權 mean-raw＋RSI≈4 擬合 b≈0.092（≈0.09），
    R²=0.743（RSI14/ATR14 版僅 0.27）——符合 FF 原版 v1/v2 無 ATR 加權特征。
    XAU 分母照 calc_pw_row 原樣 gx/gn（gn=5，供料終端 5 條 gold instrument）。"""
    rsi_by: Dict[str, float] = {}
    for sym, s in win.items():
        i = len(s["c"]) - 1 - shift
        if i < rsi_period or i < 0:
            continue
        r = indicators.rsi_wilder(s["c"], rsi_period)
        rv = r[i] if i < len(r) else None
        if rv is not None and rv > 0:
            rsi_by[sym] = rv
    atr_one = {sym: 1.0 for sym in rsi_by}
    pw = mt4_ref.calc_pw_row(rsi_by, atr_one, list(universe.INSTRUMENTS_36))
    val = {k: 9.0 * v / 100.0 for k, v in pw.items()}
    return pw, val


def _fit_slope(pairs):
    """1 自由度：b = Σ(v−4.5)(pw−50) / Σ(pw−50)²；附自由擬合 (a,b)。"""
    num = den = 0.0
    for pw, v in pairs:
        num += (v - 4.5) * (pw - 50.0)
        den += (pw - 50.0) ** 2
    b1 = num / den if den else None
    n = len(pairs)
    sx = sum(p for p, _ in pairs)
    sy = sum(v for _, v in pairs)
    sxx = sum(p * p for p, _ in pairs)
    sxy = sum(p * v for p, v in pairs)
    d = n * sxx - sx * sx
    b_free = (n * sxy - sx * sy) / d if d else None
    a_free = (sy - b_free * sx) / n if b_free is not None else None
    return b1, a_free, b_free


def run_supply_parity(ref_root: str = REF_ROOT_DEFAULT, out_dir: str = None,
                      config: str = "oc0940") -> str:
    """OC 0940 供料佈局主入口：全額窗口逐檔 kernel 重算 → reader 對齊 → 誤差矩陣。

    config="oc0940"（預設，主報告）：RSI14/ATR14＋calc_pw_row＋val=9×pw/100（OC 0940 字面配置）。
    config="calibrated"（校準版附件）：同引擎＋ATR 加權停用＋RSI=4（reader 端實證校準）。

    輸出：out/parity_report_H1_main[_calibrated].csv（主矩陣，S-close 對齊）
          out/parity_report_H4_compare[_calibrated].csv（H4 對照）
          out/parity_supply_detail[_calibrated].csv（逐窗明細）
          out/parity_slope_fit[_calibrated].txt（斜率擬合）
    """
    suffix = "_calibrated" if config == "calibrated" else ""

    def kfn(win, shift=0):
        if config == "calibrated":
            return kernel_pw_r1(win, shift=shift)
        return kernel_pw(win, shift=shift)

    out_dir = out_dir or os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
    man = load_manifest(ref_root)
    samples = {int(s["idx"]): s
               for s in load_sampling_list(os.path.join(ref_root, "ohlc_sampling_list.csv"))}
    reader_by_tf = index_reader_rows(os.path.join(ref_root, "ccy_power_reader.csv"))

    jobs = []
    for fname, m in man.items():
        pi = parse_idx_filename(fname)
        if pi is None:
            continue
        idx, tf = pi
        if idx not in samples:
            continue
        full = (m.get("symbols_full") == "33"
                and m.get("symbols_partial_or_zero", "") in ("", "0"))
        if not full:
            continue
        jobs.append((m.get("anchor_last_EURUSD_bar") or "", idx, tf, fname, m))
    jobs.sort()
    if not jobs:
        raise parity.ParityPendingError("MANIFEST 無全額窗口——供料唔齊，唔静默扮成功")

    detail = []
    main_rows, h4_rows = [], []
    fit_pairs, hold_pairs = [], []
    fit_keys, hold_keys = [], []
    h1_jobs = [j for j in jobs if j[2] == "H1"]
    for k, (_, idx, tf, fname, m) in enumerate(h1_jobs):
        anchor = m["anchor_last_EURUSD_bar"]
        sampled = samples[idx]["ts"]
        stale = (_pt(sampled) - _pt(anchor)).total_seconds() > 24 * 3600
        target = anchor if stale else _dt.datetime.strftime(
            _pt(anchor) + _dt.timedelta(minutes=TF_MINUTES[tf]), "%Y.%m.%d %H:%M")
        win = load_idx_window(os.path.join(ref_root, "ohlc", fname))
        pw, val = kfn(win, 0)
        pw1, val1 = kfn(win, 1)
        res_close = resolve_reader_row(reader_by_tf, tf, target)
        res_sample = resolve_reader_row(reader_by_tf, tf, sampled)
        res_open = resolve_reader_row(reader_by_tf, tf, anchor)
        rec_close = res_close[2] if res_close else {}
        rec_sample = res_sample[2] if res_sample else {}
        rec_open = res_open[2] if res_open else {}
        if k < 3:
            for cur in universe.CURRENCIES_9:
                if cur in pw and cur in rec_close:
                    fit_pairs.append((pw[cur], rec_close[cur]))
                    fit_keys.append(f"idx{idx}")
        else:
            for cur in universe.CURRENCIES_9:
                if cur in pw and cur in rec_close:
                    hold_pairs.append((pw[cur], rec_close[cur]))
                    hold_keys.append(f"idx{idx}")

        def _errs(v9, rec):
            return {c: v9[c] - rec[c] for c in universe.CURRENCIES_9
                    if c in v9 and rec and c in rec}

        errs = _errs(val, rec_close)
        errs_open_v1 = _errs(val, rec_open)
        errs_s = _errs(val, rec_sample)
        errs_shift1 = _errs(val1, rec_open)
        avg_e = sum(errs.values()) / len(errs) if errs else None
        mx = max((abs(v) for v in errs.values()), default=None)
        row = {"timestamp": res_close[1] if res_close else target}
        row.update({c: errs.get(c) for c in universe.CURRENCIES_9})
        row["avg"] = avg_e
        row["max_abs"] = mx
        main_rows.append(row)
        for tag, res, e, pwsrc in (("S-close", res_close, errs, pw),
                                   ("S-open", res_open, errs_open_v1, pw),
                                   ("S-sample", res_sample, errs_s, pw),
                                   ("S-shift1", res_open, errs_shift1, pw1)):
            detail.append({
                "idx": idx, "tf": tf, "file": fname, "anchor": anchor,
                "sampled": sampled, "stale": int(stale), "align": tag,
                "reader_ts": res[1] if res else "", "delta_min":
                    round(res[0], 1) if res else "",
                "kernel_pw": ";".join(f"{c}={pwsrc[c]:.4f}"
                                      for c in universe.CURRENCIES_9),
                "err": ";".join(f"{c}={e[c]:+.4f}" for c in universe.CURRENCIES_9 if c in e),
                "mean_abs": round(sum(abs(v) for v in e.values()) / len(e), 4) if e else "",
            })

    h4_jobs = [j for j in jobs if j[2] == "H4"]
    for _, idx, tf, fname, m in h4_jobs:
        anchor = m["anchor_last_EURUSD_bar"]
        sampled = samples[idx]["ts"]
        stale = (_pt(sampled) - _pt(anchor)).total_seconds() > 24 * 3600
        target = anchor if stale else _dt.datetime.strftime(
            _pt(anchor) + _dt.timedelta(minutes=TF_MINUTES[tf]), "%Y.%m.%d %H:%M")
        win = load_idx_window(os.path.join(ref_root, "ohlc", fname))
        pw, val = kfn(win, 0)
        res = resolve_reader_row(reader_by_tf, tf, target)
        if not res:
            continue
        rec = res[2]
        errs = {c: val[c] - rec[c] for c in universe.CURRENCIES_9 if c in val and c in rec}
        row = {"timestamp": res[1]}
        row.update({c: errs.get(c) for c in universe.CURRENCIES_9})
        row["avg"] = sum(errs.values()) / len(errs) if errs else None
        row["max_abs"] = max((abs(v) for v in errs.values()), default=None)
        h4_rows.append(row)
        detail.append({"idx": idx, "tf": tf, "file": fname, "anchor": anchor,
                       "sampled": sampled, "stale": int(stale), "align": "S-close",
                       "reader_ts": res[1], "delta_min": round(res[0], 1),
                       "kernel_pw": ";".join(f"{c}={pw[c]:.4f}" for c in universe.CURRENCIES_9),
                       "err": ";".join(f"{c}={errs[c]:+.4f}" for c in universe.CURRENCIES_9 if c in errs),
                       "mean_abs": round(sum(abs(v) for v in errs.values()) / len(errs), 4) if errs else ""})

    if len(main_rows) < 10:
        raise parity.ParityPendingError(
            f"H1 主矩陣只得 {len(main_rows)} 行（<10）——對齊規則要覆查")
    os.makedirs(out_dir, exist_ok=True)
    main_path = parity.write_report(main_rows, os.path.join(out_dir, f"parity_report_H1_main{suffix}.csv"))
    if h4_rows:
        parity.write_report(h4_rows, os.path.join(out_dir, f"parity_report_H4_compare{suffix}.csv"))
    dpath = os.path.join(out_dir, f"parity_supply_detail{suffix}.csv")
    with open(dpath, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["idx", "tf", "file", "anchor", "sampled",
                                          "stale", "align", "reader_ts", "delta_min",
                                          "kernel_pw", "err", "mean_abs"])
        w.writeheader()
        w.writerows(detail)
    b1, a_free, b_free = _fit_slope(fit_pairs)
    hold_max = max(abs(v - (4.5 + 0.09 * (p - 50.0))) for p, v in hold_pairs) if hold_pairs else None
    with open(os.path.join(out_dir, f"parity_slope_fit{suffix}.txt"), "w", encoding="utf-8") as f:
        f.write(f"fit_windows = {sorted(set(fit_keys))}\n")
        f.write(f"n_fit_points = {len(fit_pairs)}\n")
        f.write(f"slope_1dof_b = {b1:.6f}\n")
        f.write(f"free_fit_a = {a_free:.6f}\n")
        f.write(f"free_fit_b = {b_free:.6f}\n")
        f.write(f"held_out_points = {len(hold_pairs)}\n")
        f.write(f"held_out_max_abs_resid_vs_0.09 = {hold_max:.6f}\n" if hold_max is not None
                else "held_out = none\n")
    print(f"supply parity：H1 主矩陣 {len(main_rows)} 行（S-close 對齊）→ {main_path}")
    print(f"  H4 對照 {len(h4_rows)} 行｜斜率 1dof b={b1:.4f}（0.09 假設），held-out max resid={hold_max}")
    print(f"  明細 {len(detail)} 行 → {dpath}")
    return main_path


if __name__ == "__main__":
    argv = sys.argv[1:]
    cmd = argv[0] if argv and argv[0] in ("supply", "legacy", "auto") else "auto"
    rest = argv[1:] if cmd != "auto" else argv
    ref_root = rest[0] if rest else REF_ROOT_DEFAULT
    try:
        if cmd == "supply":
            run_supply_parity(ref_root, config="oc0940")
            run_supply_parity(ref_root, config="calibrated")
        elif cmd == "legacy":
            run_parity(ref_root)
        else:
            try:
                run_supply_parity(ref_root, config="oc0940")
                run_supply_parity(ref_root, config="calibrated")
            except parity.ParityPendingError:
                run_parity(ref_root)
    except parity.ParityPendingError as e:
        print(f"PENDING: {e}")
        sys.exit(2)
