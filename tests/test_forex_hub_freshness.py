#!/usr/bin/env python3
"""
L22 數據新鮮度門禁（白皮書 v1.3 P1-fast 裁定，2026-10-22 實施）

驗證 scripts/generate_forex_hub.py 嘅數據新鮮度行為：
  1. 「數據截至」時間戳必須存在（唔可以得「最新更新」舊語義）
  2. 「今日」標籤必須基於系統日期——舊日期絕不可標「今日」（缺陷本體）
  3. 過期升級警示三級：fresh(≤24h) / stale(>24h) / severe(>7天)
  4. stale/severe 必須有醒目 banner（靜默偽裝新鮮 = 缺陷）

用法: python3 tests/test_forex_hub_freshness.py（exit 0=過 / 非0=敗）
"""
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import generate_forex_hub as hub  # noqa: E402

FAILURES = []


def check(name, cond, detail=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not cond:
        FAILURES.append(name)


def make_item(dt, type_="4h"):
    return {
        "type": type_,
        "icon": "🦀" if type_ == "4h" else "📰",
        "date": dt.strftime("%Y-%m-%d"),
        "time": dt.strftime("%H:%M"),
        "dt": dt,
        "title": "4H 市場綜合分析" if type_ == "4h" else "每日外匯報告",
        "url": f"../{'4h_reports' if type_ == '4h' else 'forex_reports'}/x.html",
        "summary": ["樣本摘要一行"],
    }


now = datetime.now()

# --- 1. fresh：1 小時前數據 ---
r = hub.render([make_item(now - timedelta(hours=1))])
check("fresh: 有「數據截至」時間戳", "數據截至" in r)
check("fresh: 綠色徽章 class=freshness fresh", 'class="freshness fresh"' in r)
check("fresh: 無警示 banner", 'class="banner' not in r)
check("fresh: 無過期字眼", "可能過期" not in r and "嚴重過期" not in r)

# --- 2. 「今日」標籤基於真實日期（缺陷本體：舊 idx==0 硬標）---
today_dt = now.replace(hour=0, minute=1, second=0, microsecond=0)  # 今日零點後
old_dt = now - timedelta(days=30)
r_today_first = hub.render([make_item(today_dt), make_item(old_dt)])
r_old_first = hub.render([make_item(old_dt), make_item(today_dt)])
day_today = today_dt.strftime("%Y-%m-%d")
day_old = old_dt.strftime("%Y-%m-%d")
check("今日日期條目標（今日）", f"📋 {day_today}（今日）" in r_today_first)
check("舊日期條目（哪怕排第一）唔准標（今日）",
      f"📋 {day_old}（今日）" not in r_old_first,
      f"今日={day_today} 舊={day_old}")
check("今日條目在後，舊日期排第一都唔標（今日）",
      f"📋 {day_old}（今日）" not in r_today_first and f"📋 {day_today}（今日）" in r_today_first)

# --- 3. stale：48 小時前 ---
r = hub.render([make_item(now - timedelta(hours=48))])
check("stale: 黃色徽章 class=freshness stale", 'class="freshness stale"' in r)
check("stale: 有醒目 banner", 'class="banner stale"' in r)
check("stale: 提示可能過期", "可能過期" in r)
check("stale: 唔好升級到嚴重字眼", "嚴重過期" not in r)

# --- 4. severe：30 天前（L22 實況：數據停滯近 4 個月仍標今日）---
r = hub.render([make_item(now - timedelta(days=30))])
check("severe: 紅色徽章 class=freshness severe", 'class="freshness severe"' in r)
check("severe: 紅色 banner", 'class="banner severe"' in r)
check("severe: 嚴重過期＋落單核實提示", "嚴重過期" in r and "落單前請核實市況" in r)
check("severe: 舊日期唔標（今日）", "（今日）" not in r)

# --- 5. 邊界：23h=fresh、25h=stale ---
r23 = hub.render([make_item(now - timedelta(hours=23))])
r25 = hub.render([make_item(now - timedelta(hours=25))])
check("邊界 23h=fresh / 25h=stale",
      'freshness fresh' in r23 and 'freshness stale' in r25)

# --- 6. 空清單唔炸 ---
r = hub.render([])
check("空清單渲染唔炸＋N/A 標示", "N/A" in r and "DOCTYPE" in r)

print("=" * 50)
if FAILURES:
    print(f"❌ L22 新鮮度測試失敗 {len(FAILURES)} 項: {FAILURES}")
    sys.exit(1)
print("✅ L22 新鮮度測試全綠（17/17）")
