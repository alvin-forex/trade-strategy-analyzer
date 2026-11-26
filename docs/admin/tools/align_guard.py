# -*- coding: utf-8 -*-
"""align_guard.py — P0-1 對齊檢查器
用途：任何「命中率」在上報前必須過此檢查。它會同時計三種對齊，並判定是否為假命中。

三種對齊
  A. strict    預測 t  → 實際 bar = t 之後一根（唯一可接受）
  B. overlap   預測 t  → 實際 bar = t 所屬那一根（多數情況含前視，命中率會虛高）
  C. best-shift 掃描偏移，取最佳；只作診斷，不准當結果

用法（程式內呼叫）：
    from align_guard import hit_rates
    res = hit_rates(preds, prices, bar=3600)
    print(res); # res["verdict"]

preds  : dict {bar_start_ts: +1/-1}
prices : dict {bar_start_ts: close}
bar    : 秒（3600=H1, 14400=H4, 86400=D1）
"""

def _hit(preds, prices, bar, mode):
    keys = sorted(set(preds) & set(prices))
    hits = tot = 0
    for t in keys:
        p = preds[t]
        if p == 0: continue
        if mode == "strict":
            a = prices.get(t + bar); b = prices.get(t)
        else:  # overlap：用 t 自己那根（bar 起點=t）
            a = prices.get(t); b = prices.get(t - bar)
        if a is None or b is None or a == b: continue
        actual = 1 if a > b else -1
        hits += (1 if (p > 0) == (actual > 0) else 0)
        tot += 1
    return (hits, tot)

def hit_rates(preds, prices, bar=3600, shift_scan=(-2,-1,0,1,2)):
    out = {}
    h, n = _hit(preds, prices, bar, "strict")
    out["strict"] = {"hits": h, "n": n, "rate": (h/n if n else None)}
    h, n = _hit(preds, prices, bar, "overlap")
    out["overlap"] = {"hits": h, "n": n, "rate": (h/n if n else None)}
    best = None
    for s in shift_scan:
        p2 = {t + s*bar: v for t, v in preds.items()}
        h, n = _hit(p2, prices, bar, "strict")
        r = (h/n if n else 0)
        if best is None or r > best[0]: best = (r, s, h, n)
    out["best_shift"] = {"shift": best[1], "rate": best[0], "hits": best[2], "n": best[3]}

    # 判定
    st = out["strict"]["rate"] or 0
    ov = out["overlap"]["rate"] or 0
    bs = out["best_shift"]["rate"] or 0
    flags = []
    if ov - st > 0.10:
        flags.append("重疊對齊比嚴格高 %.1f 個百分點 → 該數字含前視，作廢" % ((ov-st)*100))
    if out["best_shift"]["shift"] != 0 and bs - st > 0.10:
        flags.append("最佳偏移在 %+d 根 → 對齊不確定，非零偏移的結果不准採用" % out["best_shift"]["shift"])
    if st > 0.65:
        flags.append("嚴格模式下命中率 %.1f%% 異常高，需檢查是否用了未來價格或樣本重疊" % (st*100))
    if st < 0.52:
        flags.append("嚴格模式下命中率 %.1f%% 接近隨機（50%%）→ 無預測力" % (st*100))
    verdict = "；".join(flags) if flags else "通過（嚴格模式 %.1f%%，無重疊證據）" % (st*100)
    out["verdict"] = verdict
    out["accept"] = (len(flags) == 0)
    return out


def report(res, title=""):
    lines = []
    if title: lines.append("【%s】" % title)
    for k in ("strict", "overlap", "best_shift"):
        d = res[k]
        if k == "best_shift":
            lines.append("  診斷 最佳偏移：%+d 根 → %.1f%% (n=%d)" % (d["shift"], (d["rate"] or 0)*100, d["n"]))
        else:
            lines.append("  %-8s %.1f%% (%d/%d)" % (k, (d["rate"] or 0)*100, d["hits"], d["n"]))
    lines.append("  判定：%s" % res["verdict"])
    lines.append("  可採用：%s" % ("是" if res["accept"] else "否"))
    return "\n".join(lines)


if __name__ == "__main__":
    # 自檢：重現 Power Diff 案（用 timeline.json + 本機 H1）
    import json, os, sys, base64, subprocess, csv, datetime
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    REPO="alvin-forex/trade-strategy-analyzer"
    H1DIR=r"C:\Users\alvin\AutoClaw\Inbox\Telegram-10\mt5_h1"
    DEN={"EUR":8,"USD":8,"AUD":8,"GBP":7,"JPY":7,"CHF":7,"CAD":7,"NZD":7,"XAU":4}
    PAIRS=["EURUSD","GBPUSD","USDJPY","USDCHF","USDCAD","AUDUSD","NZDUSD","EURGBP","EURJPY","EURCHF",
           "EURCAD","EURAUD","EURNZD","GBPJPY","GBPCHF","GBPCAD","GBPAUD","GBPNZD","AUDJPY","AUDCHF",
           "AUDCAD","AUDNZD","NZDJPY","NZDCHF","NZDCAD","CADJPY","CADCHF","CHFJPY"]
    out=subprocess.check_output(["gh","api","repos/%s/contents/docs/ccy_power/timeline.json"%REPO]).decode("utf-8")
    tl=json.loads(base64.b64decode(json.loads(out)["content"]).decode("utf-8"))
    def ts(s):
        y,mo,d=s.split(" ")[0].split("."); hh,mi=s.split(" ")[1].split(":")
        return int(datetime.datetime(int(y),int(mo),int(d),int(hh),int(mi),tzinfo=datetime.timezone.utc).timestamp())
    px={}
    for p in PAIRS:
        f=os.path.join(H1DIR,"%s_h1.csv"%p)
        if os.path.exists(f):
            px[p]={int(r["time"]):float(r["close"]) for r in csv.DictReader(open(f,encoding="utf-8"))}
    arr=tl["timeline"]["H1"]
    pts=[(ts(a["timestamp"]), a["currencies"]) for a in arr]
    preds={}
    for i in range(1,len(pts)):
        t0,c0=pts[i-1]; t1,c1=pts[i]
        d={cc:(c1[cc]-c0[cc])*DEN[cc] for cc in c0 if cc in c1 and cc in DEN}
        if "EUR" in d and "USD" in d:
            preds[t1- (t1%3600)] = 1 if d["EUR"]-d["USD"] > 0 else -1
    res=hit_rates(preds, px["EURUSD"], bar=3600)
    print(report(res, "自檢：Power Diff × EURUSD"))
