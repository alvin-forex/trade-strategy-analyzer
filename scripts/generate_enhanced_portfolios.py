#!/usr/bin/env python3
"""Generate enhanced portfolio HTML files (P2-P10) with detailed TP/SL analysis."""
import json, os
from datetime import datetime

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "portfolios")
TIMESTAMP = "2026-06-21 16:55:00"

# Common CSS (from P1 enhanced)
CSS = """*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,'Segoe UI',sans-serif;background:#0d1117;color:#c9d1d9;padding:20px}
.container{max-width:1100px;margin:auto}
h1{color:#58a6ff;font-size:1.4em;margin-bottom:6px}
h2{color:#58a6ff;font-size:1.05em;border-bottom:1px solid #21262d;padding-bottom:6px;margin-bottom:10px}
h3{color:#8b949e;font-size:0.9em;margin:14px 0 6px}
.meta{color:#8b949e;font-size:0.8em;margin-bottom:16px}
.section{background:#161b22;border-radius:8px;padding:16px;margin-bottom:14px;border:1px solid #21262d}
table{width:100%;border-collapse:collapse;margin-top:8px}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid #21262d;font-size:0.85em}
th{color:#8b949e;font-weight:600;text-transform:uppercase;font-size:0.75em;letter-spacing:0.5px}
tr:hover{background:#1c2128}
.positive{color:#3fb950}
.negative{color:#f85149}
.signal-link{color:#58a6ff;text-decoration:none;font-weight:500}
.signal-link:hover{text-decoration:underline}
.ea-badge{display:inline-block;padding:2px 7px;border-radius:4px;font-size:0.7em;font-weight:600}
.stat-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(130px,1fr));gap:8px;margin-top:8px}
.stat-card{background:#21262d;border-radius:6px;padding:10px}
.stat-label{color:#8b949e;font-size:0.7em;margin-bottom:3px;text-transform:uppercase;letter-spacing:0.3px}
.stat-value{font-size:1.15em;font-weight:600}
.calc-box{background:#21262d;border-radius:6px;padding:12px;margin:6px 0;font-family:'Fira Code','Consolas',monospace;font-size:0.85em;line-height:1.6}
.calc-step{color:#8b949e}
.calc-formula{color:#d29922;font-weight:500}
.calc-result{color:#3fb950;font-size:1.1em;font-weight:600;margin-top:4px}
.risk-low{color:#3fb950}
.risk-medium{color:#d29922}
.risk-high{color:#f85149}
ul{margin-left:18px;margin-top:6px}
li{margin:3px 0;font-size:0.85em;line-height:1.5}
.dir-buy{color:#3fb950}
.dir-sell{color:#f85149}
.pct-bar{display:inline-block;width:60px;height:6px;background:#21262d;border-radius:3px;overflow:hidden;vertical-align:middle;margin-left:4px}
.pct-fill{height:100%;border-radius:3px}
.footer{color:#484f58;font-size:0.75em;text-align:center;margin-top:20px;padding:10px}
.tpsl-table{margin-top:10px}
.tpsl-table th{background:#21262d}
.tpsl-highlight{background:#1c2128;border-left:3px solid #58a6ff}
.rr-good{color:#3fb950;font-weight:600}
.rr-medium{color:#d29922;font-weight:600}
.rr-bad{color:#f85149;font-weight:600}"""

EA_BADGES = {
    "DW": '<span class="ea-badge" style="background:#4a148c;color:#ce93d8">DW</span>',
    "MKD": '<span class="ea-badge" style="background:#b71c1c;color:#ef9a9a">MKD</span>',
    "SMA": '<span class="ea-badge" style="background:#0d47a1;color:#90caf9">SMA</span>',
    "Flash": '<span class="ea-badge" style="background:#4a148c;color:#b39ddb">Flash</span>',
    "UNK": '<span class="ea-badge" style="background:#424242;color:#9e9e9e">UNK</span>',
}

def rr_class(sl_pips, tp_pips):
    """Return RR class based on ratio."""
    ratio = tp_pips / sl_pips if sl_pips > 0 else 0
    if ratio >= 2.0:
        return "rr-good"
    elif ratio >= 1.5:
        return "rr-medium"
    else:
        return "rr-bad"

def rr_str(sl_pips, tp_pips):
    ratio = tp_pips / sl_pips if sl_pips > 0 else 0
    return f"1:{ratio:.1f}"

# Portfolio data extracted from HTML files
portfolios = [
    # P2
    {
        "id": "P2", "name": "SMA 穩定增長組", "capital": 1000, "target": "週 20%",
        "risk_pct": 2.0, "strategy": "SMA EA 穩定策略，選擇長期穩定盈利的 Smart Moving Average 信號",
        "ea_types": "SMA", "risk_level": "High",
        "signals": [
            {"id": "16698", "ea": "SMA", "ccy": "GBPCAD", "win_rate": 64.63, "trades": 967,
             "pnl": 49300, "pips": 21081, "pf": 2.34, "max_dd": 3806, "avg_hold": 223.1,
             "avg_win": 137.77, "avg_loss": 107.61, "sl_pips": 39},
            {"id": "32278", "ea": "SMA", "ccy": "AUDCHF", "win_rate": 72.06, "trades": 408,
             "pnl": 75732, "pips": 2742, "pf": 77.84, "max_dd": 406, "avg_hold": 45.5,
             "avg_win": 260.94, "avg_loss": 8.65, "sl_pips": 25},
            {"id": "5001", "ea": "SMA", "ccy": "USDJPY", "win_rate": 69.14, "trades": 3545,
             "pnl": 90090, "pips": 55836, "pf": 2.98, "max_dd": 12867, "avg_hold": 141.3,
             "avg_win": 55.32, "avg_loss": 41.59, "sl_pips": 36},
        ],
        "max_dd_total": 17079, "monthly_pnl": 874, "monthly_ret": 87.4,
        "total_lot": 0.19, "total_trades": 4920,
    },
    # P3
    {
        "id": "P3", "name": "MKD 激進增長組", "capital": 2000, "target": "月 50%",
        "risk_pct": 3.0, "strategy": "MKD EA 激進策略，高風險高報酬的 Macdee 信號組合",
        "ea_types": "MKD, UNK", "risk_level": "High",
        "signals": [
            {"id": "23617", "ea": "MKD", "ccy": "XAUUSD", "win_rate": 64.23, "trades": 3545,
             "pnl": 39349, "pips": 17865, "pf": 2.18, "max_dd": 4067, "avg_hold": 24.0,
             "avg_win": 31.90, "avg_loss": 26.25, "sl_pips": 25},
            {"id": "10843", "ea": "UNK", "ccy": "XAUUSD", "win_rate": 80.48, "trades": 210,
             "pnl": 45735, "pips": 3200, "pf": 1.84, "max_dd": 5589, "avg_hold": 0.5,
             "avg_win": 591.09, "avg_loss": 1320.94, "sl_pips": 200},
        ],
        "max_dd_total": 9656, "monthly_pnl": 906, "monthly_ret": 45.3,
        "total_lot": 0.27, "total_trades": 3755,
    },
    # P4
    {
        "id": "P4", "name": "GBPCAD 專攻組", "capital": 1200, "target": "週 20%",
        "risk_pct": 2.0, "strategy": "GBPCAD 貨幣對專注策略，選擇 GBPCAD 交易佔比最高的信號",
        "ea_types": "DW, MKD, SMA", "risk_level": "High",
        "signals": [
            {"id": "20805", "ea": "MKD", "ccy": "GBPCAD", "win_rate": 63.1, "trades": 2734,
             "pnl": 127763, "pips": 594, "pf": 6.17, "max_dd": 681, "avg_hold": 20.0,
             "avg_win": 77.80, "avg_loss": 12.60, "sl_pips": 25},
            {"id": "31593", "ea": "DW", "ccy": "AUDNZD", "win_rate": 79.4, "trades": 1762,
             "pnl": 117771, "pips": 52815, "pf": 40.74, "max_dd": 378, "avg_hold": 38.0,
             "avg_win": 87.62, "avg_loss": 7.72, "sl_pips": 25},
            {"id": "3291", "ea": "DW", "ccy": "XAUUSD", "win_rate": 72.2, "trades": 6407,
             "pnl": 106784, "pips": 71606, "pf": 1.76, "max_dd": 48893, "avg_hold": 45.1,
             "avg_win": 53.61, "avg_loss": 78.10, "sl_pips": 76},
            {"id": "16698", "ea": "SMA", "ccy": "GBPCAD", "win_rate": 65.7, "trades": 967,
             "pnl": 49300, "pips": 21081, "pf": 2.34, "max_dd": 3806, "avg_hold": 223.1,
             "avg_win": 137.77, "avg_loss": 107.61, "sl_pips": 39},
        ],
        "max_dd_total": 53758, "monthly_pnl": 812, "monthly_ret": 67.7,
        "total_lot": 0.29, "total_trades": 11870,
    },
    # P5
    {
        "id": "P5", "name": "XAUUSD 黃金組", "capital": 1500, "target": "月 50%",
        "risk_pct": 2.0, "strategy": "XAUUSD 黃金交易專攻，捕捉黃金大波動的信號組合",
        "ea_types": "UNK", "risk_level": "High",
        "signals": [
            {"id": "5117", "ea": "UNK", "ccy": "XAUUSD", "win_rate": 62.7, "trades": 30216,
             "pnl": 557897, "pips": -16705, "pf": 1.93, "max_dd": 65215, "avg_hold": 0.4,
             "avg_win": 61.22, "avg_loss": 53.40, "sl_pips": 25},
            {"id": "27226", "ea": "UNK", "ccy": "XAUUSD", "win_rate": 89.29, "trades": 28,
             "pnl": 168974, "pips": 645, "pf": 4.83, "max_dd": 18922, "avg_hold": 0.1,
             "avg_win": 8523.24, "avg_loss": 14702.18, "sl_pips": 200},
        ],
        "max_dd_total": 84137, "monthly_pnl": 721, "monthly_ret": 48.1,
        "total_lot": 0.13, "total_trades": 30244,
    },
    # P6
    {
        "id": "P6", "name": "低風險平注組", "capital": 1000, "target": "週 15%",
        "risk_pct": 1.5, "strategy": "低風險均注策略，每筆固定 1.5% 風險，選擇高勝率信號",
        "ea_types": "DW", "risk_level": "High",
        "signals": [
            {"id": "30359", "ea": "DW", "ccy": "GBPCAD", "win_rate": 80.7, "trades": 140,
             "pnl": 19408, "pips": 5580, "pf": 20.81, "max_dd": 494, "avg_hold": 92.3,
             "avg_win": 168.76, "avg_loss": 8.12, "sl_pips": 35},
            {"id": "33101", "ea": "DW", "ccy": "GBPCAD", "win_rate": 90.1, "trades": 81,
             "pnl": 15362, "pips": 5048, "pf": 82.16, "max_dd": 63, "avg_hold": 38.8,
             "avg_win": 210.35, "avg_loss": 2.56, "sl_pips": 25},
            {"id": "17547", "ea": "DW", "ccy": "EURNZD", "win_rate": 82.6, "trades": 1383,
             "pnl": 173023, "pips": 62860, "pf": 12.09, "max_dd": 2744, "avg_hold": 166.9,
             "avg_win": 167.82, "avg_loss": 60.24, "sl_pips": 25},
        ],
        "max_dd_total": 3301, "monthly_pnl": 2591, "monthly_ret": 259.1,
        "total_lot": 0.16, "total_trades": 1604,
    },
    # P7
    {
        "id": "P7", "name": "多CCY分散組", "capital": 2000, "target": "月 40%",
        "risk_pct": 2.0, "strategy": "多貨幣對分散策略，Top 10 信號跨 EA 類型組合",
        "ea_types": "DW, MKD, UNK", "risk_level": "High",
        "signals": [
            {"id": "5117", "ea": "UNK", "ccy": "XAUUSD", "win_rate": 63.9, "trades": 30216,
             "pnl": 557897, "pips": -16705, "pf": 1.93, "max_dd": 65215, "avg_hold": 0.4,
             "avg_win": 61.22, "avg_loss": 53.40, "sl_pips": 25},
            {"id": "11598", "ea": "UNK", "ccy": "GBPJPY", "win_rate": 68.2, "trades": 5278,
             "pnl": 194715, "pips": 29984, "pf": 3.18, "max_dd": 6647, "avg_hold": 116.1,
             "avg_win": 104.50, "avg_loss": 32.84, "sl_pips": 25},
            {"id": "17547", "ea": "DW", "ccy": "EURNZD", "win_rate": 82.6, "trades": 1383,
             "pnl": 173023, "pips": 62860, "pf": 12.09, "max_dd": 2744, "avg_hold": 166.9,
             "avg_win": 167.82, "avg_loss": 60.24, "sl_pips": 25},
            {"id": "27226", "ea": "UNK", "ccy": "XAUUSD", "win_rate": 85.7, "trades": 28,
             "pnl": 168974, "pips": 645, "pf": 4.83, "max_dd": 18922, "avg_hold": 0.1,
             "avg_win": 8523.24, "avg_loss": 14702.18, "sl_pips": 200},
            {"id": "20805", "ea": "MKD", "ccy": "GBPCAD", "win_rate": 63.1, "trades": 2734,
             "pnl": 127763, "pips": 594, "pf": 6.17, "max_dd": 681, "avg_hold": 20.0,
             "avg_win": 77.80, "avg_loss": 12.60, "sl_pips": 25},
            {"id": "21698", "ea": "DW", "ccy": "GBPCHF", "win_rate": 72.0, "trades": 13570,
             "pnl": 127550, "pips": 107082, "pf": 5.30, "max_dd": 876, "avg_hold": 86.8,
             "avg_win": 24.18, "avg_loss": 4.56, "sl_pips": 25},
            {"id": "22200", "ea": "DW", "ccy": "USDCAD", "win_rate": 75.8, "trades": 132,
             "pnl": 127470, "pips": 4146, "pf": 10.50, "max_dd": 2255, "avg_hold": 228.2,
             "avg_win": 1300.70, "avg_loss": 124.06, "sl_pips": 170},
            {"id": "31593", "ea": "DW", "ccy": "AUDNZD", "win_rate": 79.4, "trades": 1762,
             "pnl": 117771, "pips": 52815, "pf": 40.74, "max_dd": 378, "avg_hold": 38.0,
             "avg_win": 87.62, "avg_loss": 7.72, "sl_pips": 25},
            {"id": "4022", "ea": "UNK", "ccy": "EURCAD", "win_rate": 76.7, "trades": 1332,
             "pnl": 106933, "pips": 2349, "pf": 12.84, "max_dd": 1934, "avg_hold": 70.4,
             "avg_win": 142.80, "avg_loss": 11.12, "sl_pips": 25},
            {"id": "3291", "ea": "DW", "ccy": "XAUUSD", "win_rate": 72.2, "trades": 6407,
             "pnl": 106784, "pips": 71606, "pf": 1.76, "max_dd": 48893, "avg_hold": 45.1,
             "avg_win": 53.61, "avg_loss": 78.10, "sl_pips": 76},
        ],
        "max_dd_total": 148545, "monthly_pnl": 1151, "monthly_ret": 57.6,
        "total_lot": 1.21, "total_trades": 62842,
    },
    # P8
    {
        "id": "P8", "name": "London 時段組", "capital": 1200, "target": "週 20%",
        "risk_pct": 2.0, "strategy": "倫敦交易時段專攻，選擇 London session 活躍度最高的信號",
        "ea_types": "DW, Flash, SMA, UNK", "risk_level": "High",
        "signals": [
            {"id": "33101", "ea": "DW", "ccy": "GBPCAD", "win_rate": 90.1, "trades": 81,
             "pnl": 15362, "pips": 5048, "pf": 82.16, "max_dd": 63, "avg_hold": 38.8,
             "avg_win": 210.35, "avg_loss": 2.56, "sl_pips": 25},
            {"id": "19849", "ea": "Flash", "ccy": "XAUUSD", "win_rate": 86.1, "trades": 36,
             "pnl": 5004, "pips": 1139, "pf": 1.57, "max_dd": 4737, "avg_hold": 0.3,
             "avg_win": 276.00, "avg_loss": 175.50, "sl_pips": 200},
            {"id": "32541", "ea": "SMA", "ccy": "XAUUSD", "win_rate": 86.0, "trades": 136,
             "pnl": 14088, "pips": 7234, "pf": 8.34, "max_dd": 812, "avg_hold": 5.8,
             "avg_win": 123.58, "avg_loss": 14.82, "sl_pips": 59},
            {"id": "10843", "ea": "UNK", "ccy": "XAUUSD", "win_rate": 80.0, "trades": 210,
             "pnl": 45735, "pips": 3200, "pf": 1.84, "max_dd": 5589, "avg_hold": 0.5,
             "avg_win": 591.09, "avg_loss": 1320.94, "sl_pips": 200},
        ],
        "max_dd_total": 11201, "monthly_pnl": 4157, "monthly_ret": 346.4,
        "total_lot": 0.16, "total_trades": 463,
    },
    # P9
    {
        "id": "P9", "name": "NY 時段組", "capital": 1500, "target": "月 50%",
        "risk_pct": 2.0, "strategy": "紐約交易時段專攻，選擇 NY session 活躍度最高的信號",
        "ea_types": "DW, UNK", "risk_level": "High",
        "signals": [
            {"id": "32719", "ea": "DW", "ccy": "AUDJPY", "win_rate": 82.7, "trades": 248,
             "pnl": 9582, "pips": 9573, "pf": 8.85, "max_dd": 977, "avg_hold": 58.0,
             "avg_win": 54.20, "avg_loss": 6.12, "sl_pips": 39},
            {"id": "36511", "ea": "DW", "ccy": "EURJPY", "win_rate": 84.7, "trades": 137,
             "pnl": 10989, "pips": 5339, "pf": 53.01, "max_dd": 23, "avg_hold": 129.9,
             "avg_win": 95.20, "avg_loss": 1.79, "sl_pips": 25},
            {"id": "27226", "ea": "UNK", "ccy": "XAUUSD", "win_rate": 85.7, "trades": 28,
             "pnl": 168974, "pips": 645, "pf": 4.83, "max_dd": 18922, "avg_hold": 0.1,
             "avg_win": 8523.24, "avg_loss": 14702.18, "sl_pips": 200},
            {"id": "31781", "ea": "DW", "ccy": "NZDUSD", "win_rate": 56.1, "trades": 442,
             "pnl": 15842, "pips": 2211, "pf": 3.26, "max_dd": 3764, "avg_hold": 70.7,
             "avg_win": 103.50, "avg_loss": 31.76, "sl_pips": 85},
        ],
        "max_dd_total": 23686, "monthly_pnl": 7207, "monthly_ret": 480.4,
        "total_lot": 0.25, "total_trades": 855,
    },
    # P10
    {
        "id": "P10", "name": "混合策略組", "capital": 1800, "target": "月 45%",
        "risk_pct": 2.0, "strategy": "混合策略組合，Top 5 DW + Top 5 SMA 跨 EA 分散",
        "ea_types": "DW, SMA", "risk_level": "High",
        "signals": [
            {"id": "17547", "ea": "DW", "ccy": "EURNZD", "win_rate": 82.6, "trades": 1383,
             "pnl": 173023, "pips": 62860, "pf": 12.09, "max_dd": 2744, "avg_hold": 166.9,
             "avg_win": 167.82, "avg_loss": 60.24, "sl_pips": 25},
            {"id": "21698", "ea": "DW", "ccy": "GBPCHF", "win_rate": 72.0, "trades": 13570,
             "pnl": 127550, "pips": 107082, "pf": 5.30, "max_dd": 876, "avg_hold": 86.8,
             "avg_win": 24.18, "avg_loss": 4.56, "sl_pips": 25},
            {"id": "22200", "ea": "DW", "ccy": "USDCAD", "win_rate": 75.8, "trades": 132,
             "pnl": 127470, "pips": 4146, "pf": 10.50, "max_dd": 2255, "avg_hold": 228.2,
             "avg_win": 1300.70, "avg_loss": 124.06, "sl_pips": 170},
            {"id": "31593", "ea": "DW", "ccy": "AUDNZD", "win_rate": 79.4, "trades": 1762,
             "pnl": 117771, "pips": 52815, "pf": 40.74, "max_dd": 378, "avg_hold": 38.0,
             "avg_win": 87.62, "avg_loss": 7.72, "sl_pips": 25},
            {"id": "3291", "ea": "DW", "ccy": "XAUUSD", "win_rate": 72.2, "trades": 6407,
             "pnl": 106784, "pips": 71606, "pf": 1.76, "max_dd": 48893, "avg_hold": 45.1,
             "avg_win": 53.61, "avg_loss": 78.10, "sl_pips": 76},
            {"id": "5001", "ea": "SMA", "ccy": "USDJPY", "win_rate": 70.5, "trades": 3545,
             "pnl": 90090, "pips": 55836, "pf": 2.98, "max_dd": 12867, "avg_hold": 141.3,
             "avg_win": 55.32, "avg_loss": 41.59, "sl_pips": 36},
            {"id": "14158", "ea": "SMA", "ccy": "CADJPY", "win_rate": 59.0, "trades": 1191,
             "pnl": 85612, "pips": 13737, "pf": 2.67, "max_dd": 15067, "avg_hold": 85.5,
             "avg_win": 128.30, "avg_loss": 48.14, "sl_pips": 126},
            {"id": "32278", "ea": "SMA", "ccy": "AUDCHF", "win_rate": 72.1, "trades": 408,
             "pnl": 75732, "pips": 2742, "pf": 77.84, "max_dd": 406, "avg_hold": 45.5,
             "avg_win": 260.94, "avg_loss": 8.65, "sl_pips": 25},
            {"id": "16596", "ea": "SMA", "ccy": "GBPJPY", "win_rate": 99.3, "trades": 7688,
             "pnl": 60054, "pips": 135139, "pf": 67.85, "max_dd": 351, "avg_hold": 36.1,
             "avg_win": 10.95, "avg_loss": 0.52, "sl_pips": 25},
            {"id": "16698", "ea": "SMA", "ccy": "GBPCAD", "win_rate": 65.7, "trades": 967,
             "pnl": 49300, "pips": 21081, "pf": 2.34, "max_dd": 3806, "avg_hold": 223.1,
             "avg_win": 137.77, "avg_loss": 107.61, "sl_pips": 39},
        ],
        "max_dd_total": 87643, "monthly_pnl": 985, "monthly_ret": 54.7,
        "total_lot": 0.99, "total_trades": 37053,
    },
]


def calc_lot(capital, risk_pct, sl_pips):
    """Calculate lot size."""
    risk_amount = capital * risk_pct / 100
    raw_lot = risk_amount / (sl_pips * 10)
    return raw_lot


def safe_lot(raw_lot):
    """Round down to safe lot."""
    if raw_lot >= 0.10:
        return round(raw_lot * 0.4, 2)
    elif raw_lot >= 0.05:
        return round(raw_lot * 0.5, 2)
    else:
        return max(0.01, round(raw_lot * 0.6, 2))


def generate_signal_tpsl_html(sig, capital, risk_pct):
    """Generate TP/SL section HTML for a single signal."""
    sid = sig["id"]
    ea = sig["ea"]
    ccy = sig["ccy"]
    sl_base = sig["sl_pips"]
    avg_win = sig["avg_win"]
    avg_loss = sig["avg_loss"]
    
    # Calculate L1/L2/L3 SL
    sl_l1 = sl_base
    sl_l2 = int(sl_base * 1.2)
    sl_l3 = int(sl_base * 1.4)
    
    # Determine RR ratio target
    win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 99
    
    # TP based on achieving at least 1:2 RR (or 1:1.5 if avg_loss > avg_win)
    if avg_win >= avg_loss:
        target_rr = 2.0
    else:
        target_rr = 1.5
    
    tp1_l1 = int(sl_l1 * target_rr * 0.6)
    tp2_l1 = int(sl_l1 * target_rr)
    tp3_l1 = int(sl_l1 * target_rr * 1.5)
    
    tp1_l2 = int(sl_l2 * target_rr * 0.6)
    tp2_l2 = int(sl_l2 * target_rr)
    tp3_l2 = int(sl_l2 * target_rr * 1.5)
    
    tp1_l3 = int(sl_l3 * target_rr * 0.6)
    tp2_l3 = int(sl_l3 * target_rr)
    tp3_l3 = int(sl_l3 * target_rr * 1.5)
    
    # Lot calculations
    risk_amount = capital * risk_pct / 100
    raw_l1 = calc_lot(capital, risk_pct, sl_l1)
    safe_l1 = safe_lot(raw_l1)
    safe_l2 = round(safe_l1 * 1.5, 2)
    safe_l3 = round(safe_l2 * 1.5, 2)
    
    # High risk warning
    high_risk = avg_loss > avg_win
    risk_warning = ""
    if high_risk:
        risk_warning = " ⚠️"
    
    # RR classes
    rr_c = rr_class(sl_l1, tp2_l1)
    rr_str_val = rr_str(sl_l1, tp2_l1)
    
    badge = EA_BADGES.get(ea, EA_BADGES["UNK"])
    
    # Profit factor ratio
    pf_ratio = avg_win / avg_loss if avg_loss > 0 else 99
    pf_str = f"{pf_ratio:.1f}倍" if pf_ratio < 100 else "∞"
    
    html = f'''
<h3>{badge} Signal {sid} — {ccy} 主要交易對{risk_warning}</h3>
<div class="stat-grid">
<div class="stat-card"><div class="stat-label">歷史勝率</div><div class="stat-value {"positive" if sig["win_rate"] >= 70 else ""}">{sig["win_rate"]:.1f}%</div></div>
<div class="stat-card"><div class="stat-label">平均盈利</div><div class="stat-value positive">${avg_win:.2f}</div></div>
<div class="stat-card"><div class="stat-label">平均虧損</div><div class="stat-value negative">${avg_loss:.2f}</div></div>
<div class="stat-card"><div class="stat-label">平均持倉</div><div class="stat-value">{sig["avg_hold"]:.1f}h</div></div>
<div class="stat-card"><div class="stat-label">Profit Factor</div><div class="stat-value positive">{sig["pf"]:.2f}</div></div>
<div class="stat-card"><div class="stat-label">最大回撤</div><div class="stat-value negative">${sig["max_dd"]:,.0f}</div></div>
</div>

<table class="tpsl-table">
<thead>
<tr><th>層數</th><th>建議手數</th><th>止損 (SL)</th><th>止盈 1 (TP1)</th><th>止盈 2 (TP2)</th><th>止盈 3 (TP3)</th><th>風險回報比</th></tr>
</thead>
<tbody>
<tr class="tpsl-highlight">
<td><strong>L1</strong></td>
<td>{safe_l1} lots</td>
<td class="negative">{sl_l1} pips</td>
<td class="positive">{tp1_l1} pips (50%)</td>
<td class="positive">{tp2_l1} pips (30%)</td>
<td class="positive">{tp3_l1} pips (20%)</td>
<td class="{rr_c}">{rr_str_val}</td>
</tr>
<tr>
<td><strong>L2</strong></td>
<td>{safe_l2} lots</td>
<td class="negative">{sl_l2} pips</td>
<td class="positive">{tp1_l2} pips (50%)</td>
<td class="positive">{tp2_l2} pips (30%)</td>
<td class="positive">{tp3_l2} pips (20%)</td>
<td class="{rr_class(sl_l2, tp2_l2)}">{rr_str(sl_l2, tp2_l2)}</td>
</tr>
<tr>
<td><strong>L3</strong></td>
<td>{safe_l3} lots</td>
<td class="negative">{sl_l3} pips</td>
<td class="positive">{tp1_l3} pips (50%)</td>
<td class="positive">{tp2_l3} pips (30%)</td>
<td class="positive">{tp3_l3} pips (20%)</td>
<td class="{rr_class(sl_l3, tp2_l3)}">{rr_str(sl_l3, tp2_l3)}</td>
</tr>
</tbody>
</table>

<div class="calc-box">
<div class="calc-step">📌 TP/SL 設定邏輯：</div>
<div class="calc-step">  • 止損基於歷史平均虧損 ${avg_loss:.2f}，換算約 {sl_l1}-{sl_l3} pips</div>
<div class="calc-step">  • 止盈基於平均盈利 ${avg_win:.2f}，目標 {tp1_l1}-{tp3_l3} pips（約 1:{target_rr:.1f} 風險回報比）</div>
<div class="calc-step">  • 分批止盈：50% @ TP1, 30% @ TP2, 20% @ TP3</div>
<div class="calc-formula">  → 平均盈利/平均虧損 = ${avg_win:.2f}/${avg_loss:.2f} = {pf_str}</div>
'''
    
    if high_risk:
        html += f'<div class="calc-result" style="color:#f85149">  ⚠️ 平均虧損 > 平均盈利！需高勝率補償，建議縮減手數至 {safe_l1} lots</div>\n'
    elif pf_ratio >= 5:
        html += f'<div class="calc-result">  ✅ 極佳嘅盈利因子，可承受較寬止損</div>\n'
    elif pf_ratio >= 2:
        html += f'<div class="calc-result">  ✅ 良好嘅風險回報比，適合穩定操作</div>\n'
    else:
        html += f'<div class="calc-result" style="color:#d29922">  ⚡ 一般嘅盈利因子，注意倉位控制</div>\n'
    
    html += '</div>\n'
    
    # Return lot info for later use
    return html, safe_l1, safe_l2, safe_l3, sl_l1


def generate_lot_calc_html(sig, capital, risk_pct, safe_l1, safe_l2, safe_l3, sl_l1):
    """Generate lot calculation box HTML."""
    risk_amount = capital * risk_pct / 100
    raw_lot = calc_lot(capital, risk_pct, sl_l1)
    
    high_risk = sig["avg_loss"] > sig["avg_win"]
    used_risk = risk_pct if not high_risk else risk_pct * 0.5
    used_amount = capital * used_risk / 100
    
    html = f'''
<div class="calc-box">
<div class="calc-step">📌 Signal {sig["id"]} ({sig["ea"]} / {sig["ccy"]}){" ⚠️ 高風險" if high_risk else ""}</div>
<div class="calc-step">  帳戶餘額 = ${capital:,}</div>
<div class="calc-step">  風險百分比 = {used_risk:.1f}% → 風險金額 = ${used_amount:.1f}</div>
<div class="calc-step">  L1 止損 = {sl_l1} pips | 點值 = $10/pip（標準手）</div>
<div class="calc-formula">  → L1: (${capital:,} × {used_risk:.1f}%) / ({sl_l1} × $10) = {raw_lot:.3f} lots → 建議 {safe_l1} lots</div>
<div class="calc-formula">  → L2: {safe_l1} × 1.5 = {safe_l2} lots</div>
<div class="calc-formula">  → L3: {safe_l2} × 1.5 = {safe_l3} lots</div>
'''
    total = safe_l1 + safe_l2 + safe_l3
    if high_risk:
        html += f'<div class="calc-result" style="color:#d29922">  ⚠️ 建議 L1: {safe_l1} | L2: {safe_l2} | L3: {safe_l3} lots（總 {total:.2f} lots）— 降低風險至 {used_risk:.1f}%</div>'
    else:
        html += f'<div class="calc-result">  ✅ 建議 L1: {safe_l1} | L2: {safe_l2} | L3: {safe_l3} lots（總 {total:.2f} lots）</div>'
    html += '</div>\n'
    return html


def generate_unified_settings_table(signals_data, capital, risk_pct):
    """Generate unified settings comparison table."""
    html = '''
<table>
<thead><tr><th>參數</th>'''
    for sd in signals_data:
        html += f'<th>Signal {sd["sig"]["id"]}</th>'
    html += '</tr></thead>\n<tbody>\n'
    
    # Base lot row
    html += '<tr><td><strong>基礎手數 (L1)</strong></td>'
    for sd in signals_data:
        warning = " ⚠️" if sd["high_risk"] else ""
        html += f'<td>{sd["safe_l1"]} lots{warning}</td>'
    html += '</tr>\n'
    
    # Multiplier
    html += '<tr><td><strong>加倉倍數</strong></td>'
    for _ in signals_data:
        html += '<td>1.5x</td>'
    html += '</tr>\n'
    
    # SL
    html += '<tr><td><strong>止損 (L1)</strong></td>'
    for sd in signals_data:
        html += f'<td>{sd["sl_l1"]} pips</td>'
    html += '</tr>\n'
    
    # TP1
    html += '<tr><td><strong>止盈 1</strong></td>'
    for sd in signals_data:
        tp1 = int(sd["sl_l1"] * (2.0 if not sd["high_risk"] else 1.5) * 0.6)
        html += f'<td class="positive">{tp1} pips (50%)</td>'
    html += '</tr>\n'
    
    # TP2
    html += '<tr><td><strong>止盈 2</strong></td>'
    for sd in signals_data:
        tp2 = int(sd["sl_l1"] * (2.0 if not sd["high_risk"] else 1.5))
        html += f'<td class="positive">{tp2} pips (30%)</td>'
    html += '</tr>\n'
    
    # TP3
    html += '<tr><td><strong>止盈 3</strong></td>'
    for sd in signals_data:
        tp3 = int(sd["sl_l1"] * (2.0 if not sd["high_risk"] else 1.5) * 1.5)
        html += f'<td class="positive">{tp3} pips (20%)</td>'
    html += '</tr>\n'
    
    # RR
    html += '<tr><td><strong>風險回報比</strong></td>'
    for sd in signals_data:
        target_rr = 2.0 if not sd["high_risk"] else 1.5
        rr_c = "rr-good" if target_rr >= 2.0 else "rr-medium"
        html += f'<td class="{rr_c}">1:{target_rr:.1f}</td>'
    html += '</tr>\n'
    
    # Trailing stop
    html += '<tr><td><strong>追蹤止損</strong></td>'
    for sd in signals_data:
        html += f'<td>盈利 {sd["sl_l1"]}p 後移至保本</td>'
    html += '</tr>\n'
    
    # Per trade risk
    html += '<tr><td><strong>每筆風險</strong></td>'
    for sd in signals_data:
        risk_used = risk_pct * 0.5 if sd["high_risk"] else risk_pct
        risk_amt = capital * risk_used / 100
        html += f'<td>${risk_amt:.0f} ({risk_used:.1f}%)</td>'
    html += '</tr>\n'
    
    html += '</tbody>\n</table>'
    return html


def generate_portfolio_html(p):
    """Generate enhanced HTML for a portfolio."""
    pid = p["id"]
    capital = p["capital"]
    risk_pct = p["risk_pct"]
    
    # Generate signal TP/SL sections and collect lot data
    signals_data = []
    tpsl_sections = ""
    for sig in p["signals"]:
        html, l1, l2, l3, sl1 = generate_signal_tpsl_html(sig, capital, risk_pct)
        tpsl_sections += html
        signals_data.append({
            "sig": sig, "safe_l1": l1, "safe_l2": l2, "safe_l3": l3,
            "sl_l1": sl1, "high_risk": sig["avg_loss"] > sig["avg_win"],
        })
    
    # Generate lot calculation sections
    lot_sections = ""
    for sd in signals_data:
        lot_sections += generate_lot_calc_html(sd["sig"], capital, risk_pct,
                                                sd["safe_l1"], sd["safe_l2"], sd["safe_l3"], sd["sl_l1"])
    
    # Generate unified settings table
    unified_table = generate_unified_settings_table(signals_data, capital, risk_pct)
    
    # Risk assessment
    dd_ratio = p["max_dd_total"] / capital * 100
    suggested_capital = int(p["max_dd_total"] / 0.3)  # 30% of capital = max DD
    daily_stop = capital * 0.05
    weekly_stop = capital * 0.10
    
    # Check for high-risk signals
    high_risk_signals = [sd for sd in signals_data if sd["high_risk"]]
    
    html = f'''<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Portfolio {pid} 增強版 | {p["name"]}</title>
<style>
{CSS}
</style>
</head>
<body>
<div class="container">
<h1>📊 Portfolio {pid} 增強版: {p["name"]}</h1>
<div class="meta">生成時間：{TIMESTAMP} | 策略：{p["strategy"]} | EA 類型：{p["ea_types"]} | 風險等級：<span class="risk-high">{p["risk_level"]}</span></div>

<div class="section">
<h2>📋 Portfolio 概述</h2>
<div class="stat-grid">
<div class="stat-card"><div class="stat-label">投入資金</div><div class="stat-value">${capital:,}</div></div>
<div class="stat-card"><div class="stat-label">目標報酬</div><div class="stat-value">{p["target"]}</div></div>
<div class="stat-card"><div class="stat-label">信號數量</div><div class="stat-value">{len(p["signals"])}</div></div>
<div class="stat-card"><div class="stat-label">平均勝率</div><div class="stat-value positive">{sum(s["win_rate"] for s in p["signals"])/len(p["signals"]):.1f}%</div></div>
<div class="stat-card"><div class="stat-label">總交易數</div><div class="stat-value">{p["total_trades"]:,}</div></div>
<div class="stat-card"><div class="stat-label">歷史總盈虧</div><div class="stat-value positive">${sum(s["pnl"] for s in p["signals"]):,.0f}</div></div>
<div class="stat-card"><div class="stat-label">每筆風險</div><div class="stat-value">{risk_pct:.1f}%</div></div>
<div class="stat-card"><div class="stat-label">總手數</div><div class="stat-value">{p["total_lot"]:.2f} lots</div></div>
</div>
</div>

<div class="section">
<h2>🎯 詳細 TP/SL 建議（按 Signal 分析）</h2>
{tpsl_sections}
</div>

<div class="section">
<h2>🧮 手數計算過程（更新版）</h2>
{lot_sections}
</div>

<div class="section">
<h2>⚙️ 統一設定建議</h2>
{unified_table}
</div>

<div class="section">
<h2>⚠️ 風險評估</h2>
<div class="stat-grid">
<div class="stat-card"><div class="stat-label">最大回撤（合計）</div><div class="stat-value negative">${p["max_dd_total"]:,.0f}</div></div>
<div class="stat-card"><div class="stat-label">回撤/資金比</div><div class="stat-value risk-high">{dd_ratio:.1f}%</div></div>
<div class="stat-card"><div class="stat-label">爆倉風險</div><div class="stat-value risk-high">{p["risk_level"]}</div></div>
<div class="stat-card"><div class="stat-label">建議最低資金</div><div class="stat-value">${suggested_capital:,}</div></div>
<div class="stat-card"><div class="stat-label">預期月盈虧</div><div class="stat-value positive">${p["monthly_pnl"]:,}</div></div>
<div class="stat-card"><div class="stat-label">月報酬率</div><div class="stat-value positive">{p["monthly_ret"]:.1f}%</div></div>
</div>
<h3>💡 風險管理建議</h3>
<ul>
'''
    
    # High risk signal warnings
    for sd in high_risk_signals:
        sig = sd["sig"]
        html += f'<li><strong>Signal {sig["id"]} ({sig["ccy"]}) 高風險警告：</strong>平均虧損 ${sig["avg_loss"]:.2f} > 平均盈利 ${sig["avg_win"]:.2f}，建議降低手數至 {sd["safe_l1"]} lots</li>\n'
    
    html += f'''<li><strong>每層風險控制：</strong>單筆交易風險不超過帳戶的 {risk_pct:.1f}%（${capital * risk_pct / 100:.0f}）</li>
<li><strong>每日止損：</strong>日虧損超過 ${daily_stop:.0f}（5%）即停止交易</li>
<li><strong>層數控制：</strong>建議 L1-L3 分層進場，總手持倉不超過 {p["total_lot"]:.2f} lots</li>
<li style="color:#f85149"><strong>極高風險警告：</strong>歷史回撤 ${p["max_dd_total"]:,.0f}，建議增加資金至 ${suggested_capital:,} 或降低手數</li>
<li><strong>重要數據迴避：</strong>NFP、CPI、FOMC 前 30 分鐘暫停開倉</li>
<li><strong>定期檢視：</strong>每週五收盤後檢視 Portfolio 表現並調整權重</li>
</ul>
</div>

<div class="footer">
Generated by Trade Strategy Analyzer | {TIMESTAMP}
<br>Model: ZAI GLM-5.2 | Data source: Forex Forest Signals
<br>增強版：包含詳細 TP/SL 建議及風險回報比分析
</div>
</div></body></html>'''
    
    return html


def main():
    for p in portfolios:
        html = generate_portfolio_html(p)
        output_path = os.path.join(OUTPUT_DIR, f"portfolio_{p['id']}_enhanced.html")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"✅ Generated {output_path}")
    
    print(f"\n🎉 All {len(portfolios)} enhanced portfolio files generated!")


if __name__ == "__main__":
    main()
