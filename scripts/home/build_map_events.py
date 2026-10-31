#!/usr/bin/env python3
"""build_map_events.py — 事件地理層數據生成器（Phase 2.2 數據契約）

源：docs/admin/news_guard.csv（OpenClaw news_guard cron 產物，ForexFactory 抓取）
出：docs/home/map_events.json

契約（設計基準 v1.1 §⑥ + 地圖模組裁決 2026-10-28）：
  events[]:   currency(3) / country(ISO3166-1 alpha-2, EU 為 pseudo-code) /
              impact(HIGH|MED) / event / time_hkt(ISO8601+08:00) / source
  countries[]: currency / country / event_count_24h / max_impact(HIGH|MED|none)   ← 未來 24h 口徑
  generated_at: ISO8601+08:00

窗口：滾動 48h（過去 24h ＋ 未來 24h）。
  - 地圖 L1/L2/L3／strip／popover：前端 filter 未來 24h（裁決 ③修正1／④）
  - KPI「今日 HIGH 事件數」：前端 filter HKT 當日曆日（含已發生）
同源鐵律：map_events.json 與 news_high.json 將來必須同一支 generator——
  本腳本暫以 news_guard.csv 為唯一事實源；news_high.json 落地時合併至此腳本，
  唔准另開程式各自算（老闆喺地圖同倒數見到唔同數會質疑全部數據）。

用法：python3 scripts/home/build_map_events.py [--dry-run]
"""
import csv
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]  # scripts/home/ → repo root
CSV = REPO / "docs" / "admin" / "news_guard.csv"
OUT = REPO / "docs" / "home" / "map_events.json"

HKT = timezone(timedelta(hours=8))
CCY2COUNTRY = {
    "USD": "US", "EUR": "EU", "JPY": "JP", "GBP": "GB", "CHF": "CH",
    "CAD": "CA", "AUD": "AU", "NZD": "NZ",
}
IMPACT_RANK = {"HIGH": 2, "MED": 1, "none": 0}


def parse_row(row, now):
    """'2026.10.30 20:30' + tz HKT → aware datetime；壞行返回 None。"""
    raw = (row.get("time") or "").strip()
    parts = raw.replace(".", "-").split()
    if len(parts) != 2:
        return None
    try:
        dt = datetime.strptime(parts[0] + " " + parts[1], "%Y-%m-%d %H:%M")
    except ValueError:
        return None
    return dt.replace(tzinfo=HKT)


def main():
    dry = "--dry-run" in sys.argv
    now = datetime.now(HKT)
    lo, hi = now - timedelta(hours=24), now + timedelta(hours=24)
    fwd = now + timedelta(hours=24)

    events = []
    with CSV.open(encoding="utf-8-sig", newline="") as f:
        # 檔案格式：time,ccy,event,impact（無 header row）
        for rec in csv.reader(f):
            if not rec or len(rec) < 4:
                continue
            t, ccy, name, impact = (c.strip() for c in rec[:4])
            ccy, impact = ccy.upper(), impact.upper()
            if ccy not in CCY2COUNTRY or impact not in ("HIGH", "MED"):
                continue
            dt = parse_row({"time": t}, now)
            if dt is None or not (lo <= dt <= hi):
                continue
            events.append({
                "currency": ccy,
                "country": CCY2COUNTRY[ccy],
                "impact": impact,
                "event": name,
                "time_hkt": dt.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                "source": "forexfactory",
            })
    events.sort(key=lambda e: (e["time_hkt"], e["currency"]))

    # 未來 24h 国家 rollup（地圖 L1/L2 顯示口徑）
    agg = {}
    for e in events:
        dt = datetime.strptime(e["time_hkt"], "%Y-%m-%dT%H:%M:%S+08:00").replace(tzinfo=HKT)
        if dt <= now:
            continue
        k = e["currency"]
        a = agg.setdefault(k, {"currency": k, "country": e["country"],
                               "event_count_24h": 0, "max_impact": "none"})
        a["event_count_24h"] += 1
        if IMPACT_RANK[e["impact"]] > IMPACT_RANK[a["max_impact"]]:
            a["max_impact"] = e["impact"]
    countries = sorted(agg.values(),
                       key=lambda c: (-IMPACT_RANK[c["max_impact"]], -c["event_count_24h"], c["currency"]))

    doc = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "window": {"past_hours": 24, "future_hours": 24},
        "events": events,
        "countries": countries,
    }
    payload = json.dumps(doc, ensure_ascii=False, indent=1) + "\n"

    if dry:
        print(payload)
        return
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(payload, encoding="utf-8")
    fwd_n = sum(1 for e in events
                if datetime.strptime(e["time_hkt"], "%Y-%m-%dT%H:%M:%S+08:00")
                .replace(tzinfo=HKT) > now)
    print(f"map_events.json 寫入 {OUT}：48h 窗口 {len(events)} 事件"
          f"（未來 24h {fwd_n}，活躍國家 {len(countries)}）")


if __name__ == "__main__":
    main()
