#!/usr/bin/env python3
"""
Forex Combined Report v3 — 綜合外匯分析報告生成器
Features:
  1. CCY Power 字母排序 + 可點擊 anchor 跳轉
  2. 個別貨幣對分析卡片（S/R, Fib, RSI, MACD, BB, ATR）
  3. 重要事件日程
  4. 按 CCY 分組 + anchor 跳轉
  5. 全球市場速覽（DXY, VIX, Oil, Gold, 10Y, 2Y, S&P500）
"""

import csv
import sys
import argparse
from datetime import datetime
from collections import defaultdict, OrderedDict

# ─── 常量 ────────────────────────────────────────────────────────────────────

DEFAULT_CSV = (
    "/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/"
    "A06E6395D71C5597BD3D45E90C51C549/MQL4/Files/forex_data.csv"
)

# 字母排序
DISPLAY_CURRENCIES = sorted(["AUD", "CAD", "CHF", "EUR", "GBP", "JPY", "NZD", "USD", "XAU"])

ALL_PAIRS = [
    "AUDUSD", "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD",
    "CADCHF", "CADJPY", "CHFJPY",
    "EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD",
    "GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD",
    "NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD",
    "USDCAD", "USDCHF", "USDJPY", "XAUUSD",
]

# 按 CCY 分組（只列出第一個 CCY 為 key 的 pairs，避免重複）
CCY_GROUPS = OrderedDict([
    ("AUD", ["AUDUSD", "AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD"]),
    ("CAD", ["CADCHF", "CADJPY"]),
    ("CHF", ["CHFJPY"]),
    ("EUR", ["EURAUD", "EURCAD", "EURCHF", "EURGBP", "EURJPY", "EURNZD", "EURUSD"]),
    ("GBP", ["GBPAUD", "GBPCAD", "GBPCHF", "GBPJPY", "GBPNZD", "GBPUSD"]),
    ("JPY", []),  # JPY pairs already covered as xxxJPY above
    ("NZD", ["NZDCAD", "NZDCHF", "NZDJPY", "NZDUSD"]),
    ("USD", ["USDCAD", "USDCHF", "USDJPY"]),
    ("XAU", ["XAUUSD"]),
])

PAIR_LABELS = {
    "AUDUSD": "澳元/美元", "AUDCAD": "澳元/加元", "AUDCHF": "澳元/瑞郎",
    "AUDJPY": "澳元/日圓", "AUDNZD": "澳元/紐元",
    "CADCHF": "加元/瑞郎", "CADJPY": "加元/日圓",
    "CHFJPY": "瑞郎/日圓",
    "EURAUD": "歐元/澳元", "EURCAD": "歐元/加元", "EURCHF": "歐元/瑞郎",
    "EURGBP": "歐元/英鎊", "EURJPY": "歐元/日圓", "EURNZD": "歐元/紐元",
    "EURUSD": "歐元/美元",
    "GBPAUD": "英鎊/澳元", "GBPCAD": "英鎊/加元", "GBPCHF": "英鎊/瑞郎",
    "GBPJPY": "英鎊/日圓", "GBPNZD": "英鎊/紐元", "GBPUSD": "英鎊/美元",
    "NZDCAD": "紐元/加元", "NZDCHF": "紐元/瑞郎", "NZDJPY": "紐元/日圓",
    "NZDUSD": "紐元/美元",
    "USDCAD": "美元/加元", "USDCHF": "美元/瑞郎", "USDJPY": "美元/日圓",
    "XAUUSD": "黃金/美元",
}

PAIR_FUNDAMENTAL = {
    "AUDUSD": "鐵礦砂 · RBA vs Fed", "AUDCAD": "鐵礦砂 vs 油價 · RBA vs BoC",
    "AUDCHF": "鐵礦砂 · RBA vs SNB", "AUDJPY": "鐵礦砂 · RBA vs BoJ",
    "AUDNZD": "澳洲 vs 紐西蘭 GDP",
    "CADCHF": "油價 · BoC vs SNB", "CADJPY": "油價 · BoC vs BoJ",
    "CHFJPY": "避險交叉 · SNB vs BoJ",
    "EURAUD": "歐洲 vs 澳洲經濟", "EURCAD": "ECB vs BoC · 歐洲數據",
    "EURCHF": "ECB vs SNB · 歐瑞避險", "EURGBP": "ECB vs BoE · 脫歐遺留",
    "EURJPY": "ECB vs BoJ · 歐日息差", "EURNZD": "ECB vs RBNZ",
    "EURUSD": "ECB vs Fed · 全球核心",
    "GBPAUD": "BoE vs RBA", "GBPCAD": "BoE vs BoC · 油價",
    "GBPCHF": "BoE vs SNB", "GBPJPY": "BoE vs BoJ · 英日息差",
    "GBPNZD": "BoE vs RBNZ", "GBPUSD": "BoE vs Fed · 英美息差",
    "NZDCAD": "乳製品 vs 油價", "NZDCHF": "RBNZ vs SNB",
    "NZDJPY": "RBNZ vs BoJ · 套息", "NZDUSD": "RBNZ vs Fed",
    "USDCAD": "Fed vs BoC · 油價", "USDCHF": "Fed vs SNB · 避險",
    "USDJPY": "Fed vs BoJ · 美日息差", "XAUUSD": "避險 · 通脹 · 美元",
}

NEWS_ITEMS = [
    {"title": "🔥 中東局勢升級：伊朗襲擊科威特", "tags": ["美元利多↑", "原油利多↑", "AUD利空↓", "CHF利多↑", "XAU利空↓"]},
    {"title": "🛢️ 油價飆升：Brent +2.8% 至 $95.12", "tags": ["CAD利多↑", "AUDCAD利空↓"]},
    {"title": "🇦🇺 澳洲CPI降至4.2%，RBA加息預期降溫", "tags": ["AUD利空↓", "AUDCAD利空↓"]},
    {"title": "🇺🇸 美國PCE通脹預期升至3.7-3.8%", "tags": ["美元利多↑", "XAU利空↓", "AUD利空↓"]},
    {"title": "🇨🇭 瑞郎避險需求：SNB利率維持0%", "tags": ["CHF利多↑", "EURCHF利空↓"]},
    {"title": "📉 黃金跌破200日均線 $4,406", "tags": ["XAU利空↓", "貴金屬利空↓"]},
]

EVENTS = [
    {"time": "20:30 ET", "event": "美國4月PCE物價指數", "importance": "🔴🔴🔴", "forecast": "3.7%", "previous": "3.5%"},
    {"time": "20:30 ET", "event": "美國Q1 GDP修正值", "importance": "🔴🔴🔴", "forecast": "1.5%", "previous": "1.6%"},
    {"time": "20:30 ET", "event": "美國耐用品訂單", "importance": "🔴🔴", "forecast": "-0.5%", "previous": "2.6%"},
    {"time": "22:00 ET", "event": "美國成屋銷售", "importance": "🔴🔴", "forecast": "—", "previous": "—"},
]

MARKET_GLANCE = OrderedDict([
    ("DXY 美元指數", {"value": "104.82", "change": "+0.35%", "direction": "up"}),
    ("VIX 恐慌指數", {"value": "18.5", "change": "+5.2%", "direction": "up"}),
    ("Brent 原油", {"value": "$95.12", "change": "+2.8%", "direction": "up"}),
    ("XAU 黃金", {"value": "$4,385", "change": "-1.2%", "direction": "down"}),
    ("US 10Y", {"value": "4.511%", "change": "+3bp", "direction": "up"}),
    ("US 2Y", {"value": "4.068%", "change": "+2bp", "direction": "up"}),
    ("標普500", {"value": "5,480", "change": "-0.8%", "direction": "down"}),
])

INDICATORS = ["EMA", "RSI", "MACD", "STC", "BB", "River"]
TIMEFRAMES = ["D1", "H4", "H1"]

CCY_COLORS = {
    "AUD": "#2196F3", "CAD": "#4CAF50", "CHF": "#FF9800", "EUR": "#9C27B0",
    "GBP": "#F44336", "JPY": "#FFEB3B", "NZD": "#E91E63", "USD": "#FF5722",
    "XAU": "#FFD700",
}

# ─── 工具函數 ────────────────────────────────────────────────────────────────

def pf(val, default=0.0):
    """Safe float parse, rejecting MT4 sentinel values."""
    try:
        v = float(val)
        return default if v > 2147483640 else v
    except Exception:
        return default


def score_one(row):
    """Score 6 indicators, each returns (bull_score, bear_score)."""
    c = pf(row.get("close", 0))
    ema20, ema50, ema200 = pf(row.get("ema20", 0)), pf(row.get("ema50", 0)), pf(row.get("ema200", 0))
    rsi = pf(row.get("rsi14", 50))
    macd_hist = pf(row.get("macd_hist", 0))
    stc_main = pf(row.get("stc_main", 50))
    bb_upper, bb_lower = pf(row.get("bb_upper", 0)), pf(row.get("bb_lower", 0))
    river_upper, river_lower = pf(row.get("river_upper", 0)), pf(row.get("river_lower", 0))

    ind = {}

    # EMA
    sb = se = 0
    if ema20 > 0 and ema50 > 0 and ema200 > 0:
        if c > ema20 > ema50 > ema200:
            sb = 2
        elif c > ema20 > ema50:
            sb = 2
        elif c > ema20:
            sb = 1
        elif c < ema20 < ema50 < ema200:
            se = 2
        elif c < ema20 < ema50:
            se = 2
        elif c < ema20:
            se = 1
    ind["EMA"] = (sb, se)

    # RSI
    sb = se = 0
    if rsi > 60:
        sb = 1
    elif rsi > 55:
        sb = 0.5
    elif rsi < 40:
        se = 1
    elif rsi < 45:
        se = 0.5
    ind["RSI"] = (sb, se)

    # MACD
    sb = 1 if macd_hist > 0 else 0
    se = 0 if macd_hist > 0 else 1
    ind["MACD"] = (sb, se)

    # STC
    sb = se = 0
    if stc_main > 60:
        sb = 1
    elif stc_main > 50:
        sb = 0.5
    elif stc_main < 40:
        se = 1
    elif stc_main < 50:
        se = 0.5
    ind["STC"] = (sb, se)

    # BB
    sb = se = 0
    if bb_upper > 0 and bb_lower > 0:
        rng = bb_upper - bb_lower
        if rng > 0:
            pct = (c - bb_lower) / rng * 100
            if pct > 80:
                sb = 1
            elif pct > 60:
                sb = 0.5
            elif pct < 20:
                se = 1
            elif pct < 40:
                se = 0.5
    ind["BB"] = (sb, se)

    # River
    sb = se = 0
    if river_upper > 0 and river_lower > 0:
        rng = river_upper - river_lower
        if rng > 0:
            rpct = (c - river_lower) / rng * 100
            if rpct > 75:
                sb = 1
            elif rpct > 55:
                sb = 0.5
            elif rpct < 25:
                se = 1
            elif rpct < 45:
                se = 0.5
    ind["River"] = (sb, se)

    return ind


def arrow_cell(sb, se):
    net = sb - se
    if net >= 1.5:
        return '<div class="tf sb" title="強多">⬆</div>'
    if net >= 0.8:
        return '<div class="tf b" title="偏多">↑</div>'
    if net > 0:
        return '<div class="tf mb" title="微多">↑</div>'
    if net <= -1.5:
        return '<div class="tf ss" title="強空">⬇</div>'
    if net <= -0.8:
        return '<div class="tf s" title="偏空">↓</div>'
    if net < 0:
        return '<div class="tf ms" title="微空">↓</div>'
    return '<div class="tf n" title="中性">—</div>'


def calc_support_resistance(close, atr):
    """ATR-based S/R levels."""
    pp = close
    levels = {
        "R3": pp + 1.0 * atr,
        "R2": pp + 0.618 * atr,
        "R1": pp + 0.382 * atr,
        "PP": pp,
        "S1": pp - 0.382 * atr,
        "S2": pp - 0.618 * atr,
        "S3": pp - 1.0 * atr,
    }
    return levels


def calc_fib(close, atr):
    """Fibonacci retracement using ATR-derived H/L."""
    h = close + atr / 2
    l = close - atr / 2
    diff = h - l
    return {
        "23.6%": h - 0.236 * diff,
        "38.2%": h - 0.382 * diff,
        "50.0%": h - 0.500 * diff,
        "61.8%": h - 0.618 * diff,
        "78.6%": h - 0.786 * diff,
    }


def format_price(val, symbol):
    """Format price with appropriate decimal places."""
    if "JPY" in symbol:
        return f"{val:.3f}"
    if symbol == "XAUUSD":
        return f"${val:.2f}"
    return f"{val:.5f}"


def calc_atr_pct(atr, close):
    """ATR as percentage of price."""
    if close <= 0:
        return 0, 0
    pct = atr / close * 100
    return pct, min(100, pct / 0.02)  # 2% = 100%


def bias_label(net_score):
    if net_score >= 5:
        return ("強多 ↑↑", "#3fb950")
    if net_score >= 3:
        return ("偏多 ↑", "#56d364")
    if net_score >= 1:
        return ("微多 ↗", "#56d364aa")
    if net_score <= -5:
        return ("強空 ↓↓", "#f85149")
    if net_score <= -3:
        return ("偏空 ↓", "#f85149")
    if net_score <= -1:
        return ("微空 ↘", "#f85149aa")
    return ("中性 —", "#484f58")


def rsi_status(rsi):
    if rsi >= 70:
        return "超買 ⚠️", "#f85149"
    if rsi >= 60:
        return "偏強", "#3fb950"
    if rsi <= 30:
        return "超賣 ⚠️", "#3fb950"
    if rsi <= 40:
        return "接近超賣 ↓", "#f85149"
    if rsi <= 45:
        return "偏弱", "#f85149aa"
    return "中性", "#484f58"


def macd_status(hist):
    if hist > 0:
        return "金叉 動能偏多 ↑", "#3fb950"
    return "死叉 動能偏空 ↓", "#f85149"


def bb_status(close, bb_upper, bb_lower):
    if bb_upper <= 0 or bb_lower <= 0:
        return "—", "#484f58"
    rng = bb_upper - bb_lower
    if rng <= 0:
        return "—", "#484f58"
    pct = (close - bb_lower) / rng * 100
    if pct >= 90:
        return "上軌 超買區 ⚠️", "#f85149"
    if pct >= 70:
        return "偏上軌", "#3fb950"
    if pct <= 10:
        return "下軌 超賣區 ⚠️", "#3fb950"
    if pct <= 30:
        return "接近下軌 ↓", "#f85149"
    return "中軌附近", "#484f58"


# ─── HTML 生成 ───────────────────────────────────────────────────────────────

def build_css():
    return """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
       background: #0d1117; color: #c9d1d9; padding: 10px; max-width: 860px;
       margin: 0 auto; font-size: 12px; line-height: 1.5; }
a { color: #58a6ff; text-decoration: none; }

/* Topnav - left sidebar like TSA */
.topnav { position: fixed; left: 0; top: 0; bottom: 0; width: 180px; background: #161b22;
  border-right: 1px solid #21262d; padding: 12px 0; display: flex; flex-direction: column;
  z-index: 100; overflow-y: auto; }
.topnav-logo { font-weight: 700; font-size: 1em; color: #FFD700; text-decoration: none;
  padding: 8px 14px; margin-bottom: 12px; border-bottom: 1px solid #21262d; }
.topnav-links { display: flex; flex-direction: column; gap: 2px; padding: 0 6px; }
.topnav-link { color: #888; text-decoration: none; font-size: .85em; font-weight: 600; padding: 8px 10px;
  border-radius: 6px; transition: all .2s; border-left: 3px solid transparent; white-space: nowrap; }
.topnav-link:hover { color: #FFD700; background: #1a1f2e; }
.topnav-link.active { color: #FFD700; background: #1a1f2e; border-left-color: #FFD700; }
body { padding-left: 180px; }

h1 { font-size: 17px; color: #fff; text-align: center; margin-bottom: 2px; }
h2 { font-size: 12px; color: #666; text-align: center; margin-bottom: 14px; font-weight: normal; }
h3 { font-size: 13px; color: #58a6ff; margin: 18px 0 8px 0; padding: 6px 10px;
     background: #161b22; border-radius: 6px; border-left: 3px solid #58a6ff; }

/* CCY Power */
.ccy-power { background: #161b22; border-radius: 8px; padding: 10px; margin-bottom: 14px; }
.ccy-grid { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; }
.ccy-item { text-align: center; min-width: 54px; padding: 6px 8px; border-radius: 6px;
            cursor: pointer; transition: transform .15s; }
.ccy-item:hover { transform: scale(1.08); }
.ccy-name { font-size: 10px; font-weight: bold; }
.ccy-val { font-size: 14px; font-weight: bold; margin-top: 1px; }
.ccy-bar { height: 4px; border-radius: 2px; margin-top: 3px; }

/* Market Glance */
.market-glance { background: #161b22; border-radius: 8px; padding: 10px; margin-bottom: 14px; }
.mg-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(110px, 1fr)); gap: 6px; }
.mg-card { background: #0d1117; border-radius: 6px; padding: 6px 8px; text-align: center; }
.mg-label { font-size: 9px; color: #8b949e; }
.mg-value { font-size: 14px; font-weight: bold; color: #e6edf3; }
.mg-change { font-size: 10px; }
.mg-up { color: #3fb950; }
.mg-down { color: #f85149; }

/* Technical table */
table { width: 100%; border-collapse: collapse; font-size: 11px; }
th { background: #161b22; color: #484f58; padding: 4px 2px; text-align: center;
     font-size: 9px; font-weight: bold; border-bottom: 1px solid #21262d; }
td { padding: 3px 1px; text-align: center; border-bottom: 1px solid #161b22; }
tr:nth-child(even) { background: rgba(255,255,255,0.02); }
tr:hover { background: #161b22; }
.sym { font-weight: bold; color: #e6edf3; text-align: left !important; font-size: 11px;
       white-space: nowrap; padding-left: 4px !important; }
.ind-cell { display: inline-flex; flex-direction: column; line-height: 1; }
.tf { font-size: 10px; line-height: 13px; }
.sb { color: #3fb950; font-weight: bold; }
.b  { color: #3fb950; }
.mb { color: #56d364; opacity: 0.7; }
.ss { color: #f85149; font-weight: bold; }
.s  { color: #f85149; }
.ms { color: #f85149; opacity: 0.6; }
.n  { color: #484f58; }
.score { font-size: 10px; font-weight: bold; }

/* News */
.news-section { background: #161b22; border-radius: 8px; padding: 12px; margin-bottom: 14px; }
.news-item { padding: 8px 0; border-bottom: 1px solid #21262d; font-size: 12px; line-height: 1.6; }
.news-item:last-child { border-bottom: none; }
.news-tag { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; margin: 1px 2px; }
.tag-bull { background: #3fb95022; color: #3fb950; }
.tag-bear { background: #f8514922; color: #f85149; }

/* Events */
.events-section { background: #161b22; border-radius: 8px; padding: 12px; margin-bottom: 14px; }
.event-row { display: flex; align-items: center; gap: 8px; padding: 7px 0;
             border-bottom: 1px solid #21262d; font-size: 12px; }
.event-row:last-child { border-bottom: none; }
.event-time { min-width: 65px; color: #8b949e; font-size: 11px; }
.event-imp { min-width: 55px; }
.event-name { flex: 1; font-weight: 500; }
.event-fc { color: #58a6ff; font-size: 11px; }
.event-pv { color: #484f58; font-size: 11px; }

/* Pair cards */
.pairs-section { margin-bottom: 14px; }
.ccy-group-anchor { display: block; position: relative; top: -10px; visibility: hidden; }
.pair-card { background: #161b22; border-radius: 8px; padding: 12px; margin-bottom: 10px;
             border: 1px solid #21262d; }
.pair-header { display: flex; align-items: baseline; justify-content: space-between; margin-bottom: 4px; }
.pair-name { font-size: 15px; font-weight: bold; color: #e6edf3; }
.pair-label { font-size: 11px; color: #8b949e; margin-left: 6px; }
.pair-price { font-size: 14px; font-weight: bold; }
.pair-fund { font-size: 10px; color: #8b949e; margin-bottom: 6px; }
.pair-indicators { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
.pi { font-size: 11px; padding: 2px 6px; border-radius: 4px; background: #0d1117; }
.sr-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 2px 16px; font-size: 11px;
           background: #0d1117; border-radius: 6px; padding: 8px; margin-bottom: 6px; }
.sr-grid .label { color: #8b949e; }
.sr-grid .val { text-align: right; font-family: monospace; color: #e6edf3; }
.sr-grid .resist .val { color: #3fb950; }
.sr-grid .support .val { color: #f85149; }
.fib-grid { display: flex; flex-wrap: wrap; gap: 4px 10px; font-size: 10px; color: #8b949e;
            margin-bottom: 6px; }
.fib-item { }
.pair-bias { display: flex; align-items: center; gap: 8px; font-size: 12px; font-weight: bold;
             padding: 4px 0; }
.atr-bar { height: 6px; border-radius: 3px; background: #21262d; flex: 1; max-width: 80px;
           overflow: hidden; }
.atr-fill { height: 100%; border-radius: 3px; }

/* Verdict */
.verdict { background: #161b22; border-radius: 8px; padding: 12px; margin-bottom: 14px; }
.verdict-item { padding: 6px 0; border-bottom: 1px solid #21262d; display: flex;
                align-items: center; gap: 8px; }
.verdict-item:last-child { border-bottom: none; }
.verdict-pair { font-weight: bold; min-width: 60px; }
.verdict-bar { flex: 1; height: 8px; border-radius: 4px; background: #21262d;
               position: relative; overflow: hidden; }
.verdict-fill { position: absolute; top: 0; height: 100%; border-radius: 4px; }

.legend { text-align: center; font-size: 9px; color: #484f58; margin: 4px 0 10px;
          padding: 6px; background: #161b22; border-radius: 4px; }
.footer { text-align: center; font-size: 9px; color: #30363d; margin-top: 14px; padding: 6px; }
@media (max-width: 768px) {
  .topnav { position: fixed; left: -200px; transition: left .3s; z-index: 200; }
  .topnav.open { left: 0; }
  body { padding-left: 0; }
  .menu-btn { display: block !important; }
}
.menu-btn { display: none; position: fixed; top: 8px; left: 8px; z-index: 150; background: #161b22;
  border: 1px solid #21262d; color: #FFD700; padding: 6px 10px; border-radius: 6px; font-size: 18px; cursor: pointer; }
"""


def build_ccy_power_html(ccy_power):
    max_power = max(ccy_power.values()) if ccy_power else 10
    html = '<div class="ccy-power"><div class="ccy-grid">\n'
    for ccy in DISPLAY_CURRENCIES:
        val = ccy_power.get(ccy, 0)
        color = CCY_COLORS.get(ccy, "#666")
        bar_w = int(val / max(max_power, 1) * 100) if max_power > 0 else 0
        html += (
            f'<a href="#group-{ccy}" class="ccy-item" style="background:{color}18">'
            f'<div class="ccy-name" style="color:{color}">{ccy}</div>'
            f'<div class="ccy-val" style="color:{color}">{val:.1f}</div>'
            f'<div class="ccy-bar" style="background:{color};width:{bar_w}%"></div>'
            f'</a>\n'
        )
    html += '</div>\n</div>\n'
    return html


def build_market_glance_html():
    html = '<div class="market-glance"><div class="mg-grid">\n'
    for name, info in MARKET_GLANCE.items():
        cls = "mg-up" if info["direction"] == "up" else "mg-down"
        html += (
            f'<div class="mg-card">'
            f'<div class="mg-label">{name}</div>'
            f'<div class="mg-value">{info["value"]}</div>'
            f'<div class="mg-change {cls}">{info["change"]}</div>'
            f'</div>\n'
        )
    html += '</div>\n</div>\n'
    return html


def build_news_html():
    html = '<div class="news-section">\n<h3>📰 新聞摘要</h3>\n'
    for item in NEWS_ITEMS:
        html += f'<div class="news-item"><div>{item["title"]}</div><div>'
        for tag in item["tags"]:
            cls = "tag-bull" if "利多" in tag else "tag-bear" if "利空" in tag else "tag-bull"
            html += f'<span class="news-tag {cls}">{tag}</span>'
        html += '</div></div>\n'
    html += '</div>\n'
    return html


def build_events_html():
    html = '<div class="events-section">\n<h3>📅 重要事件日程</h3>\n'
    for ev in EVENTS:
        html += (
            f'<div class="event-row">'
            f'<div class="event-time">{ev["time"]}</div>'
            f'<div class="event-imp">{ev["importance"]}</div>'
            f'<div class="event-name">{ev["event"]}</div>'
            f'<div class="event-fc">預期 {ev["forecast"]}</div>'
            f'<div class="event-pv">前值 {ev["previous"]}</div>'
            f'</div>\n'
        )
    html += '</div>\n'
    return html


def build_technical_table_html(symbol_data, pair_signals):
    html = '<div class="legend">\n'
    html += '<span class="sb">⬆ 強多</span> | <span class="b">↑ 偏多</span> | '
    html += '<span class="mb">↑ 微多</span> | <span class="n">— 中性</span> | '
    html += '<span class="ms">↓ 微空</span> | <span class="s">↓ 偏空</span> | '
    html += '<span class="ss">⬇ 強空</span>\n</div>\n'

    html += '<h3>📈 技術指標全景（MT4 EA 數據）</h3>\n'
    html += '<table>\n<thead>\n<tr>\n<th style="width:56px">Pair</th>\n<th style="width:30px">分</th>\n'
    for ind in INDICATORS:
        html += f'<th>{ind}<br><span style="font-weight:normal;color:#30363d">D1|H4|H1</span></th>\n'
    html += '</tr>\n</thead>\n<tbody>\n'

    sorted_pairs = sorted(symbol_data.keys(), key=lambda s: pair_signals.get(s, 0))
    for sym in sorted_pairs:
        html += f'<tr><td class="sym"><a href="#card-{sym}" style="color:inherit;text-decoration:none">{sym}</a></td>'
        net = pair_signals.get(sym, 0)
        if net >= 5:
            sc = f'<td class="score" style="color:#3fb950">{net:+.0f}</td>'
        elif net >= 2:
            sc = f'<td class="score" style="color:#56d364">{net:+.0f}</td>'
        elif net <= -5:
            sc = f'<td class="score" style="color:#f85149">{net:+.0f}</td>'
        elif net <= -2:
            sc = f'<td class="score" style="color:#f85149;opacity:.8">{net:+.0f}</td>'
        else:
            sc = f'<td class="score" style="color:#484f58">{net:+.0f}</td>'
        html += sc
        for ind in INDICATORS:
            html += '<td><div class="ind-cell">'
            for tf in TIMEFRAMES:
                if tf in symbol_data[sym]:
                    scores = score_one(symbol_data[sym][tf])
                    sb, se = scores[ind]
                    html += arrow_cell(sb, se)
                else:
                    html += '<div class="tf n">—</div>'
            html += '</div></td>'
        html += '</tr>\n'

    html += '</tbody>\n</table>\n'
    return html


def build_pair_card_html(sym, d1_row, h4_row, net_score):
    """Build a single pair analysis card."""
    close = pf(d1_row.get("close", 0))
    atr = pf(d1_row.get("atr14", 0))
    rsi = pf(d1_row.get("rsi14", 50))
    macd_hist = pf(d1_row.get("macd_hist", 0))
    bb_upper = pf(d1_row.get("bb_upper", 0))
    bb_lower = pf(d1_row.get("bb_lower", 0))
    bb_mid = pf(d1_row.get("bb_middle", pf(d1_row.get("bb_mid", 0))))

    label = PAIR_LABELS.get(sym, "")
    fund = PAIR_FUNDAMENTAL.get(sym, "")
    bias_text, bias_color = bias_label(net_score)

    # S/R
    sr = calc_support_resistance(close, atr)
    # Fib
    fib = calc_fib(close, atr)
    # ATR %
    atr_pct, atr_bar_pct = calc_atr_pct(atr, close)
    atr_pips = atr * 10000 if "JPY" not in sym and sym != "XAUUSD" else atr * 100 if "JPY" in sym else atr
    pip_unit = "pips" if sym != "XAUUSD" else "pts"
    if "JPY" in sym:
        atr_pips = atr * 100
        pip_unit = "pips"
    elif sym == "XAUUSD":
        atr_pips = atr
        pip_unit = "$"
    else:
        atr_pips = atr * 10000
        pip_unit = "pips"

    rsi_txt, rsi_clr = rsi_status(rsi)
    macd_txt, macd_clr = macd_status(macd_hist)
    bb_txt, bb_clr = bb_status(close, bb_upper, bb_lower)

    h = f'<div class="pair-card">\n'

    # Header
    h += (f'<div class="pair-header">'
          f'<div><span class="pair-name">{sym}</span>'
          f'<span class="pair-label">{label}</span></div>'
          f'<div class="pair-price" style="color:{bias_color}">{format_price(close, sym)}</div>'
          f'</div>\n')
    h += f'<div class="pair-fund">{fund}</div>\n'

    # Indicators row
    h += '<div class="pair-indicators">\n'
    h += f'<div class="pi" style="color:{rsi_clr}">RSI {rsi:.1f} {rsi_txt}</div>\n'
    h += f'<div class="pi" style="color:{macd_clr}">MACD {macd_txt}</div>\n'
    h += f'<div class="pi" style="color:{bb_clr}">BB {bb_txt}</div>\n'
    h += f'<div class="pi">ATR {atr_pct:.2f}%</div>\n'
    h += '</div>\n'

    # S/R grid
    h += '<div class="sr-grid">\n'
    for key in ["R3", "R2", "R1"]:
        h += f'<div class="resist"><span class="label">{key}:</span></div><div class="resist val">{format_price(sr[key], sym)}</div>\n'
    h += f'<div><span class="label">PP:</span></div><div class="val">{format_price(sr["PP"], sym)}</div>\n'
    for key in ["S1", "S2", "S3"]:
        h += f'<div class="support"><span class="label">{key}:</span></div><div class="support val">{format_price(sr[key], sym)}</div>\n'
    h += '</div>\n'

    # Fib
    h += '<div class="fib-grid">\n'
    h += '<span style="color:#58a6ff;margin-right:4px">Fib:</span>\n'
    for lvl, val in fib.items():
        h += f'<span class="fib-item">{lvl} {format_price(val, sym)}</span>\n'
    h += '</div>\n'

    # Bias bar
    h += (f'<div class="pair-bias">'
          f'<span style="color:{bias_color}">[ {bias_text} ]</span>'
          f'<span style="font-size:10px;color:#8b949e">技術 {net_score:+.0f}</span>'
          f'<div class="atr-bar"><div class="atr-fill" style="width:{atr_bar_pct:.0f}%;background:{bias_color}"></div></div>'
          f'<span style="font-size:10px;color:#8b949e">ATR {atr_pips:.1f} {pip_unit}</span>'
          f'</div>\n')

    h += '</div>\n'
    return h


def build_pairs_section_html(symbol_data, pair_signals):
    html = '<h3>🔍 個別貨幣對分析</h3>\n<div class="pairs-section">\n'
    for ccy, pairs in CCY_GROUPS.items():
        # Filter to pairs that actually have data
        available = [p for p in pairs if p in symbol_data]
        if not available:
            continue
        html += f'<div class="ccy-group-anchor" id="group-{ccy}"></div>\n'
        for sym in available:
            d1 = symbol_data[sym].get("D1", {})
            h4 = symbol_data[sym].get("H4", {})
            if not d1:
                continue
            net = pair_signals.get(sym, 0)
            html += build_pair_card_html(sym, d1, h4, net)
    html += '</div>\n'
    return html


def build_verdict_html(pair_signals):
    verdicts = {
        "AUDCAD": {"news": "利空", "reason": "AUD弱(CPI↓+失業↑) + CAD強(油價↑)"},
        "EURCHF": {"news": "偏空", "reason": "CHF避險需求↑ + ECB偏鴿"},
        "XAUUSD": {"news": "利空", "reason": "跌破200MA + 美元強 + 避險轉原油"},
        "AUDUSD": {"news": "利空", "reason": "RBA暫停 + 美元強"},
        "USDCAD": {"news": "偏多", "reason": "美元強 但油價支撐CAD"},
        "EURUSD": {"news": "偏空", "reason": "美元強 + ECB偏鴿"},
        "USDJPY": {"news": "偏多", "reason": "美元強 + 日央行寬鬆"},
        "GBPUSD": {"news": "偏空", "reason": "美元強 + 避險情緒"},
    }

    html = '<h3>🔍 新聞 vs 技術 對比結論</h3>\n<div class="verdict">\n'
    for pair, v in verdicts.items():
        tech = pair_signals.get(pair, 0)
        news_bull = "利多" in v["news"]
        news_bear = "利空" in v["news"]

        if news_bear and tech <= -3:
            align = "🟢 一致看空"
        elif news_bull and tech >= 3:
            align = "🟢 一致看多"
        elif news_bear and tech >= 3:
            align = "⚠️ 分歧：新聞空 技術多"
        elif news_bull and tech <= -3:
            align = "⚠️ 分歧：新聞多 技術空"
        else:
            align = "🟡 部分一致"

        max_score = 18
        pct = (tech + max_score) / (2 * max_score) * 100
        pct = max(5, min(95, pct))
        fill_color = "#3fb950" if tech > 0 else "#f85149" if tech < 0 else "#484f58"

        tag_cls = "tag-bear" if news_bear else "tag-bull" if news_bull else "tag-bull"
        html += (
            f'<div class="verdict-item">'
            f'<div class="verdict-pair">{pair}</div>'
            f'<div><span class="news-tag {tag_cls}">{v["news"]}</span></div>'
            f'<div class="verdict-bar"><div class="verdict-fill" style="width:{pct}%;background:{fill_color};left:0"></div></div>'
            f'<div style="min-width:30px;font-weight:bold;color:{fill_color}">{tech:+.0f}</div>'
            f'<div style="font-size:10px">{align}</div>'
            f'</div>\n'
            f'<div style="padding:0 0 6px 68px;font-size:10px;color:#666">{v["reason"]}</div>\n'
        )
    html += '</div>\n'
    return html


# ─── 主函數 ──────────────────────────────────────────────────────────────────

def generate_report(data, ccy_power, output_path):
    # Index data by symbol -> timeframe
    symbol_data = defaultdict(dict)
    for row in data:
        sym = row.get("symbol", "")
        tf = row.get("timeframe", "")
        if sym and tf:
            symbol_data[sym][tf] = row

    # Calculate pair signals
    pair_signals = {}
    for sym in ALL_PAIRS:
        if sym not in symbol_data:
            continue
        total_bull = total_bear = 0
        for tf in TIMEFRAMES:
            if tf in symbol_data[sym]:
                scores = score_one(symbol_data[sym][tf])
                for ind in INDICATORS:
                    sb, se = scores[ind]
                    total_bull += sb
                    total_bear += se
        pair_signals[sym] = total_bull - total_bear

    now = datetime.now().strftime("%Y-%m-%d %H:%M HKT")

    html = f"""<!DOCTYPE html>
<html lang="zh-HK">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>外匯綜合分析報告 - {now}</title>
<style>
{build_css()}
</style>
</head>
<body>
<button class="menu-btn" onclick="document.querySelector('.topnav').classList.toggle('open')">☰</button>
<div class="topnav">
<a href="https://alvin-forex.github.io/trade-strategy-analyzer/" class="topnav-logo">🦀 TSA</a>
<div class="topnav-links">
<a href="https://alvin-forex.github.io/trade-strategy-analyzer/signal_ranking.html" class="topnav-link">🏆 Signal 排名</a>
<a href="https://alvin-forex.github.io/trade-strategy-analyzer/admin/ccy_ranking.html" class="topnav-link">💱 CCY 排名</a>
<a href="https://alvin-forex.github.io/trade-strategy-analyzer/admin/symbol_ranking.html" class="topnav-link">📊 波幅波</a>
<a href="https://alvin-forex.github.io/trade-strategy-analyzer/" class="topnav-link active">📰 外匯新聞</a>
</div>
</div>
<h1>📊 外匯綜合分析報告</h1>
<h2>Combined Forex Analysis | {now}</h2>

{build_ccy_power_html(ccy_power)}

{build_market_glance_html()}

{build_technical_table_html(symbol_data, pair_signals)}

{build_news_html()}

{build_events_html()}

{build_pairs_section_html(symbol_data, pair_signals)}

{build_verdict_html(pair_signals)}

<div class="footer">
新聞 vs 技術對比 | 綠色=一致 | ⚠️=分歧 | 分=技術信號總分<br>
Generated by OpenClaw Forex Combined Report v3.0
</div>
</body>
</html>
"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Forex Combined Report v3")
    parser.add_argument("--input", default=DEFAULT_CSV, help="Path to forex_data.csv")
    parser.add_argument("--output", default=None, help="Output HTML path")
    args = parser.parse_args()

    data = []
    with open(args.input, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)

    if not data:
        print("ERROR: No data rows found.", file=sys.stderr)
        sys.exit(1)

    # Extract CCY power from first row
    ccy_power = {}
    for i in range(1, 10):
        name = data[0].get(f"ccy_{i}_name", "")
        power = pf(data[0].get(f"ccy_{i}_power", 0))
        if name:
            ccy_power[name] = power

    output_path = args.output or f"/tmp/forex_combined_{datetime.now().strftime('%Y%m%d_%H%M')}.html"
    result = generate_report(data, ccy_power, output_path)

    # Stats
    import os
    size = os.path.getsize(result)
    with open(result, "r") as f:
        lines = sum(1 for _ in f)
    print(f"✅ Report generated: {result}")
    print(f"   Lines: {lines} | Size: {size:,} bytes ({size/1024:.1f} KB)")
    return result


if __name__ == "__main__":
    main()
