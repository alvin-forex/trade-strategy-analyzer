#!/usr/bin/env python3
"""
generate_report_v2.py - TSA v2 Deep Analysis Report Generator
Reads a signal CSV and produces a 5-panel dark-theme HTML report.

Usage:
  python3 generate_report_v2.py downloads/36912.csv --signal-id 36912 --output docs/reports/index_36912.html
"""
import argparse, csv, math, os, sys
from datetime import datetime
from collections import Counter, defaultdict

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_dt(s):
    s = s.strip()
    for fmt in ('%d/%m/%Y %H:%M:%S', '%Y-%m-%d %H:%M:%S', '%d/%m/%Y %H:%M'):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None

def safe_float(v, default=0.0):
    try:
        return float(v)
    except (ValueError, TypeError):
        return default

def fmt_money(v):
    sign = '+' if v >= 0 else ''
    return f"{sign}${v:,.0f}"

def fmt_money2(v):
    sign = '+' if v >= 0 else ''
    return f"{sign}${v:,.2f}"

def fmt_pct(v):
    return f"{v:.1f}%"

def fmt_hours(h):
    if h < 1:
        return f"{h*60:.0f}min"
    if h < 24:
        return f"{h:.2f}h"
    return f"{h/24:.1f}d"

# ---------------------------------------------------------------------------
# CSV Loader
# ---------------------------------------------------------------------------

def load_csv(path):
    with open(path, encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    deposits = []
    trades = []
    for r in rows:
        t = r.get('Type', '').lower().strip()
        if t == 'balance':
            dep = safe_float(r.get('Net Profit', 0))
            if dep != 0:
                deposits.append(dep)
            continue
        if t not in ('buy', 'sell'):
            continue
        tr = {
            'open_time': parse_dt(r.get('Open Time', '')),
            'close_time': parse_dt(r.get('Close Time', '')),
            'type': t,
            'lots': safe_float(r.get('Lots', 0)),
            'symbol': r.get('Symbol', ''),
            'open_price': safe_float(r.get('Open Price', 0)),
            'close_price': safe_float(r.get('Close Price', 0)),
            'commission': safe_float(r.get('Commission', 0)),
            'swap': safe_float(r.get('Swap', 0)),
            'pips': safe_float(r.get('Net Pips', 0)),
            'net_profit': safe_float(r.get('Net Profit', 0)),
            'max_profit': safe_float(r.get('Max Profit', 0)),
            'max_pips': safe_float(r.get('Max Pips', 0)),
            'max_loss': safe_float(r.get('Max Loss', 0)),
            'max_loss_pips': safe_float(r.get('Max Loss Pips', 0)),
            'magic': r.get('Magic Number', '0').strip(),
            'comment': r.get('Comment', '').strip(),
            'holding_hours': safe_float(r.get('Holding Time (Hours)', 0)),
        }
        trades.append(tr)
    
    trades.sort(key=lambda x: x['close_time'] or datetime.min)
    initial_deposit = sum(deposits) if deposits else 5000.0
    return trades, initial_deposit

# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

def compute_stats(trades, initial_deposit):
    n = len(trades)
    if n == 0:
        return {}
    
    total_profit = sum(t['net_profit'] for t in trades)
    wins = [t for t in trades if t['net_profit'] > 0]
    losses = [t for t in trades if t['net_profit'] <= 0]
    win_rate = len(wins) / n * 100
    
    gross_profit = sum(t['net_profit'] for t in wins)
    gross_loss = abs(sum(t['net_profit'] for t in losses))
    pf = gross_profit / gross_loss if gross_loss > 0 else 999.0
    
    avg_win = sum(t['net_profit'] for t in wins) / len(wins) if wins else 0
    avg_loss = sum(t['net_profit'] for t in losses) / len(losses) if losses else 0
    
    max_win = max((t['net_profit'] for t in trades), default=0)
    max_loss_trade = min((t['net_profit'] for t in trades), default=0)
    
    avg_hold = sum(t['holding_hours'] for t in trades) / n
    avg_hold_win = sum(t['holding_hours'] for t in wins) / len(wins) if wins else 0
    avg_hold_loss = sum(t['holding_hours'] for t in losses) / len(losses) if losses else 0
    
    equity = [initial_deposit]
    for t in trades:
        equity.append(equity[-1] + t['net_profit'])
    final_equity = equity[-1]
    
    peak = equity[0]
    max_dd_pct = 0
    for e in equity:
        if e > peak:
            peak = e
        dd_pct = (peak - e) / peak * 100 if peak > 0 else 0
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct
    
    growth_rate = (final_equity - initial_deposit) / initial_deposit * 100 if initial_deposit > 0 else 0
    
    first_dt = trades[0]['close_time']
    last_dt = trades[-1]['close_time']
    total_days = (last_dt - first_dt).days if first_dt and last_dt else 1
    total_weeks = max(1, total_days / 7)
    
    symbols = sorted(set(t['symbol'] for t in trades if t['symbol']))
    magics = sorted(set(t['magic'] for t in trades if t['magic'] and t['magic'] != '0'))
    
    strategy_names = set()
    for t in trades:
        c = t['comment']
        if c and not c.startswith('so:') and not c.startswith('Deposit'):
            parts = c.split('_')
            if len(parts) >= 2:
                strategy_names.add(parts[0] + ' ' + parts[1])
            else:
                strategy_names.add(c)
    
    buy_trades = [t for t in trades if t['type'] == 'buy']
    sell_trades = [t for t in trades if t['type'] == 'sell']
    
    def dir_stats(dir_trades):
        if not dir_trades:
            return {'n': 0, 'win_rate': 0, 'profit': 0, 'avg': 0}
        w = [t for t in dir_trades if t['net_profit'] > 0]
        p = sum(t['net_profit'] for t in dir_trades)
        return {
            'n': len(dir_trades),
            'win_rate': len(w)/len(dir_trades)*100,
            'profit': p,
            'avg': p/len(dir_trades),
        }
    
    buy_s = dir_stats(buy_trades)
    sell_s = dir_stats(sell_trades)
    
    hold_bins = {'<15min': 0, '15-60min': 0, '1-4hr': 0, '4-12hr': 0, '12hr+': 0}
    for t in trades:
        h = t['holding_hours']
        if h < 0.25:
            hold_bins['<15min'] += 1
        elif h < 1:
            hold_bins['15-60min'] += 1
        elif h < 4:
            hold_bins['1-4hr'] += 1
        elif h < 12:
            hold_bins['4-12hr'] += 1
        else:
            hold_bins['12hr+'] += 1
    
    layer_map = defaultdict(list)
    for t in trades:
        c = t['comment']
        if '_H1_' in c:
            layer_map['H1'].append(t)
        elif '_M30_' in c:
            layer_map['M30'].append(t)
        elif '_M15_' in c:
            layer_map['M15'].append(t)
        elif '_H4_' in c:
            layer_map['H4'].append(t)
        else:
            layer_map['Other'].append(t)
    
    layers = []
    for tf, tf_trades in layer_map.items():
        w = [t for t in tf_trades if t['net_profit'] > 0]
        p = sum(t['net_profit'] for t in tf_trades)
        layers.append({
            'tf': tf,
            'n': len(tf_trades),
            'win_rate': len(w)/len(tf_trades)*100 if tf_trades else 0,
            'profit': p,
        })
    layers.sort(key=lambda x: -x['n'])
    max_layers = len(layers)
    
    hourly = defaultdict(lambda: {'n': 0, 'profit': 0})
    for t in trades:
        if t['close_time']:
            h = t['close_time'].hour
            hourly[h]['n'] += 1
            hourly[h]['profit'] += t['net_profit']
    
    worst_trades = sorted(trades, key=lambda x: x['net_profit'])[:10]
    recent_trades = list(reversed(trades[-20:]))
    
    win_pips = [t['pips'] for t in wins if t['pips'] > 0]
    loss_pips = [abs(t['pips']) for t in losses if t['pips'] < 0]
    avg_win_pips = sum(win_pips)/len(win_pips) if win_pips else 25
    avg_loss_pips = sum(loss_pips)/len(loss_pips) if loss_pips else 50
    
    if max_dd_pct < 20 and max_layers <= 2:
        risk_level, risk_class, risk_emoji = '低風險', 'low', '🟢'
    elif max_dd_pct < 40 and max_layers <= 3:
        risk_level, risk_class, risk_emoji = '中等風險', 'med', '⚠️'
    else:
        risk_level, risk_class, risk_emoji = '高風險', 'high', '🔴'
    
    score = 0
    score += min(25, win_rate / 100 * 25)
    score += min(30, pf / 3 * 30) if pf < 999 else 30
    rr = abs(avg_win / avg_loss) if avg_loss != 0 else 0
    score += min(20, rr / 1.5 * 20)
    score += min(15, min(n, 500) / 500 * 15)
    hold_eff = 1.0 if avg_hold < 4 else max(0, 8 - avg_hold) / 4
    score += min(10, hold_eff * 10)
    
    # Penalty for blown accounts or negative growth
    if total_profit < 0:
        score *= 0.3  # Heavy penalty
    if growth_rate < -50:
        score *= 0.5
    
    # PF < 1 means net negative
    if pf < 1:
        score *= 0.5
    
    if score >= 75:
        grade, grade_stars, grade_label, grade_color = 'AAA', '⭐⭐⭐', '首選 COPY', 'var(--green)'
    elif score >= 55:
        grade, grade_stars, grade_label, grade_color = 'AA', '⭐⭐', '推薦 COPY', 'var(--acc)'
    elif score >= 35:
        grade, grade_stars, grade_label, grade_color = 'A', '⭐', '可考慮 COPY', 'var(--yellow)'
    else:
        grade, grade_stars, grade_label, grade_color = 'B', '—', '不建議 COPY', 'var(--red)'
    
    return {
        'n': n, 'wins': len(wins), 'losses': len(losses),
        'win_rate': win_rate, 'total_profit': total_profit,
        'pf': pf, 'gross_profit': gross_profit, 'gross_loss': gross_loss,
        'avg_win': avg_win, 'avg_loss': avg_loss,
        'max_win': max_win, 'max_loss': max_loss_trade,
        'avg_hold': avg_hold, 'avg_hold_win': avg_hold_win, 'avg_hold_loss': avg_hold_loss,
        'equity': equity, 'final_equity': final_equity,
        'max_dd_pct': max_dd_pct,
        'growth_rate': growth_rate,
        'initial_deposit': initial_deposit,
        'first_dt': first_dt, 'last_dt': last_dt,
        'total_days': total_days, 'total_weeks': total_weeks,
        'symbols': symbols, 'magics': magics,
        'strategy_names': sorted(strategy_names),
        'buy_s': buy_s, 'sell_s': sell_s,
        'hold_bins': hold_bins,
        'layers': layers, 'max_layers': max_layers,
        'hourly': dict(hourly),
        'worst_trades': worst_trades,
        'recent_trades': recent_trades,
        'avg_win_pips': avg_win_pips, 'avg_loss_pips': avg_loss_pips,
        'rr': rr, 'score': score,
        'risk_level': risk_level, 'risk_class': risk_class, 'risk_emoji': risk_emoji,
        'grade': grade, 'grade_stars': grade_stars, 'grade_label': grade_label,
        'grade_color': grade_color,
    }

# ---------------------------------------------------------------------------
# SVG Equity Curve Path
# ---------------------------------------------------------------------------

def equity_svg_paths(equity, width, height):
    n = len(equity)
    if n < 2:
        return '', ''
    min_v = min(equity)
    max_v = max(equity)
    vrange = max_v - min_v if max_v != min_v else 1
    pts = []
    for i, v in enumerate(equity):
        x = (i / (n - 1)) * width
        y = height - ((v - min_v) / vrange) * height
        pts.append(f"{x:.1f},{y:.1f}")
    line_path = 'M' + ' L'.join(pts)
    area_path = line_path + f' L{width:.1f},{height:.1f} L0,{height:.1f} Z'
    return line_path, area_path

def equity_y_labels(equity, n_labels=5):
    min_v = min(equity)
    max_v = max(equity)
    labels = []
    for i in range(n_labels):
        t = 1 - i / (n_labels - 1)
        val = min_v + t * (max_v - min_v)
        if val >= 1000:
            labels.append(f"${val/1000:.1f}K")
        else:
            labels.append(f"${val:.0f}")
    return labels

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = """:root{
  --bg:#0a0e17;--bg2:#0f1320;--card:#111520;--card-h:#161b2d;
  --border:#1e2433;--border2:#2a3040;
  --text:#e0e0e0;--text2:#8892a6;--text3:#5a6478;--white:#fff;
  --pri:#FFD700;--acc:#64b5f6;--acc-dim:rgba(100,181,246,.12);
  --green:#4CAF50;--green-bg:rgba(76,175,80,.12);
  --red:#FF5252;--red-bg:rgba(255,82,82,.12);
  --yellow:#FFC107;--yellow-bg:rgba(255,193,7,.12);
  --orange:#FF9800;--orange-bg:rgba(255,152,0,.12);
  --radius:12px;--radius-sm:8px;
  --shadow:0 4px 24px rgba(0,0,0,.4);
  --font:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang TC','Microsoft JhengHei',sans-serif;
  --mono:'SF Mono','Fira Code',Consolas,monospace;
}
[data-theme="light"]{
  --bg:#f0f2f5;--bg2:#e4e7ec;--card:#ffffff;--card-h:#f0f2f5;
  --border:#c4c9d0;--border2:#a8afb8;
  --text:#0d1117;--text2:#3d4452;--text3:#6b7280;--white:#ffffff;
  --pri:#1a3a6b;--acc:#c81e4a;--acc-dim:rgba(200,30,74,.1);
  --green:#1a7d32;--green-bg:rgba(26,125,50,.1);
  --red:#c41e3a;--red-bg:rgba(196,30,58,.1);
  --yellow:#8a6d00;--yellow-bg:rgba(138,109,0,.12);
  --orange:#fd7e14;--orange-bg:rgba(253,126,20,.08);
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--font);background:var(--bg);color:var(--text);line-height:1.6;font-size:14px}
a{color:var(--acc);text-decoration:none}
.report-header{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:20px 24px;margin-bottom:16px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
.report-header h1{font-size:1.4em;color:var(--pri);font-weight:800}
.report-header .sub{color:var(--text2);font-size:.85em;margin-top:2px}
.report-header .meta{display:flex;gap:12px;flex-wrap:wrap}
.report-header .meta span{background:var(--bg2);border:1px solid var(--border);border-radius:6px;padding:4px 10px;font-size:.78em;color:var(--text2)}
.report-header .meta span b{color:var(--text)}
.main-nav{display:flex;gap:4px;background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:6px;margin-bottom:16px;position:sticky;top:8px;z-index:100;overflow-x:auto;-webkit-overflow-scrolling:touch;box-shadow:var(--shadow)}
.main-nav::-webkit-scrollbar{height:0}
.nav-tab{flex:1;min-width:90px;padding:10px 14px;border:none;background:transparent;color:var(--text2);font-size:14px;font-weight:600;border-radius:var(--radius-sm);cursor:pointer;transition:all .2s;display:flex;align-items:center;justify-content:center;gap:6px;white-space:nowrap}
.nav-tab:hover{background:var(--bg2);color:var(--text)}
.nav-tab.active{background:var(--acc-dim);color:var(--acc);box-shadow:inset 0 0 0 1px rgba(100,181,246,.3)}
.sub-nav{display:flex;gap:2px;border-bottom:1px solid var(--border);margin-bottom:16px;overflow-x:auto;-webkit-overflow-scrolling:touch;align-items:center}
.sub-nav::-webkit-scrollbar{height:0}
.sub-tab{padding:8px 14px;border:none;background:transparent;color:var(--text2);font-size:13px;font-weight:500;cursor:pointer;transition:all .15s;white-space:nowrap;border-bottom:2px solid transparent}
.sub-tab:hover{color:var(--text);background:var(--bg2)}
.sub-tab.active{color:var(--acc);border-bottom-color:var(--acc)}
.panel{display:none}
.panel.active{display:block}
.card{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:20px 24px;margin-bottom:16px;box-shadow:0 2px 8px rgba(0,0,0,.3)}
.card h2{font-size:1.05em;color:var(--white);margin-bottom:12px;display:flex;align-items:center;gap:8px;font-weight:700}
.card h2 .icon{font-size:1.15em}
.card h3{font-size:.95em;color:var(--text);margin-bottom:8px;font-weight:600}
.hero-row{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
.hero-stat{background:var(--card);border:1px solid var(--border);border-radius:var(--radius);padding:20px 16px;text-align:center;position:relative;overflow:hidden}
.hero-stat::before{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,transparent,var(--acc),transparent);opacity:.5}
.hero-stat .val{font-size:28px;font-weight:800;letter-spacing:-1px}
.hero-stat .val.pos{color:var(--green)}.hero-stat .val.neg{color:var(--red)}.hero-stat .val.gold{color:var(--pri)}
.hero-stat .lbl{font-size:11px;color:var(--text2);margin-top:4px;text-transform:uppercase;letter-spacing:1px}
.stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px}
.stat-box{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px 10px;text-align:center;transition:all .2s}
.stat-box:hover{border-color:var(--border2);background:var(--card-h)}
.stat-box .v{font-size:18px;font-weight:700;color:var(--white)}
.stat-box .v.pos{color:var(--green)}.stat-box .v.neg{color:var(--red)}.stat-box .v.gold{color:var(--pri)}
.stat-box .l{font-size:11px;color:var(--text2);margin-top:2px}
.risk-status{border-radius:var(--radius);padding:14px 20px;display:flex;align-items:center;gap:14px;border-left:4px solid;margin-bottom:16px}
.risk-status.low{background:var(--green-bg);border-left-color:var(--green)}
.risk-status.med{background:var(--yellow-bg);border-left-color:var(--yellow)}
.risk-status.high{background:var(--red-bg);border-left-color:var(--red)}
.risk-status .ri{font-size:22px}
.risk-status .rt{font-size:16px;font-weight:700}
.risk-status.low .rt{color:var(--green)}
.risk-status.med .rt{color:var(--yellow)}
.risk-status.high .rt{color:var(--red)}
.risk-status .rd{color:var(--text2);font-size:.85em}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.tbl{width:100%;border-collapse:collapse;font-size:.85em}
.tbl th{background:var(--bg2);color:var(--text2);padding:10px 12px;text-align:left;font-weight:600;border-bottom:1px solid var(--border);font-size:.8em;text-transform:uppercase;letter-spacing:.5px;white-space:nowrap}
.tbl td{padding:10px 12px;border-bottom:1px solid var(--border);color:var(--text)}
.tbl tr:hover td{background:var(--card-h)}
.tbl .pos{color:var(--green);font-weight:600}
.tbl .neg{color:var(--red);font-weight:600}
.tbl .gold{color:var(--pri);font-weight:600}
.badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.75em;font-weight:700;letter-spacing:.5px}
.badge.green{background:var(--green-bg);color:var(--green)}
.badge.red{background:var(--red-bg);color:var(--red)}
.badge.yellow{background:var(--yellow-bg);color:var(--yellow)}
.badge.blue{background:var(--acc-dim);color:var(--acc)}
.chart-box{background:var(--bg2);border:1px solid var(--border);border-radius:var(--radius-sm);padding:16px;margin-bottom:12px;position:relative}
.equity-chart{width:100%;height:200px;display:block}
.bar-chart{display:flex;align-items:flex-end;gap:4px;height:160px;padding:8px 0}
.bar{flex:1;border-radius:3px 3px 0 0;min-height:4px;transition:opacity .2s;position:relative;cursor:default}
.bar:hover{opacity:.8}
.bar.green{background:linear-gradient(180deg,var(--green),rgba(76,175,80,.4))}
.bar.red{background:linear-gradient(180deg,var(--red),rgba(255,82,82,.4))}
.bar.blue{background:linear-gradient(180deg,var(--acc),rgba(100,181,246,.4))}
.bar.gold{background:linear-gradient(180deg,var(--pri),rgba(255,215,0,.4))}
.bar.yellow{background:linear-gradient(180deg,var(--yellow),rgba(255,193,7,.4))}
.divider{border:none;border-top:1px solid var(--border);margin:20px 0}
@media(max-width:768px){
  .hero-row{grid-template-columns:1fr}
  .stat-grid{grid-template-columns:repeat(2,1fr)}
  .two-col{grid-template-columns:1fr}
  .nav-tab{min-width:70px;font-size:12px;padding:8px 10px}
  .nav-tab .nav-text{display:none}
  .report-header{flex-direction:column;align-items:flex-start}
}
.grade-display{text-align:center;padding:20px}
.grade-stars{font-size:36px;letter-spacing:4px}
.grade-label{font-size:14px;font-weight:700;margin-top:8px;text-transform:uppercase;letter-spacing:2px}
.grade-desc{font-size:.85em;color:var(--text2);margin-top:4px}
.mini-stat{display:flex;align-items:center;gap:8px;padding:8px 12px;background:var(--bg2);border-radius:var(--radius-sm);border:1px solid var(--border)}
.mini-stat .ms-v{font-weight:700;color:var(--white)}
.mini-stat .ms-l{font-size:.75em;color:var(--text2)}"""

JS = """<script>
function switchPanel(btn,id){
  document.querySelectorAll('.panel').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t=>t.classList.remove('active'));
  document.getElementById('panel-'+id).classList.add('active');
  btn.classList.add('active');
}
function switchSub(btn,id){
  var parent=btn.closest('.panel');
  var prefix=parent.id.replace('panel-','')+'-';
  parent.querySelectorAll('.sub-tab').forEach(t=>t.classList.remove('active'));
  btn.classList.add('active');
  parent.querySelectorAll('[id]').forEach(function(el){
    if(el.id.startsWith(prefix)) el.style.display='none';
  });
  document.getElementById(id).style.display='block';
}
</script>"""

# ---------------------------------------------------------------------------
# HTML Section Builders (using .format() to avoid f-string quote issues)
# ---------------------------------------------------------------------------

def esc(s):
    """HTML escape"""
    return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def cls_for(v):
    return 'pos' if v >= 0 else 'neg'

def build_header(signal_id, s, strategy_name):
    syms = '/'.join(s['symbols']) if s['symbols'] else 'N/A'
    strat = ', '.join(s['strategy_names']) if s['strategy_names'] else (strategy_name or 'Unknown')
    first = s['first_dt'].strftime('%Y.%m.%d') if s['first_dt'] else 'N/A'
    last = s['last_dt'].strftime('%Y.%m.%d') if s['last_dt'] else 'N/A'
    return """<div class="report-header">
  <div>
    <h1>📊 Signal {sid} \u6df1\u5ea6\u5206\u6790</h1>
    <div class="sub">{strat} \u00b7 {syms}</div>
  </div>
  <div class="meta">
    <span>📅 <b>{first} \u2013 {last}</b></span>
    <span>🔄 <b>{n} \u7b46\u4ea4\u6613</b></span>
    <span>\u23f1 <b>{weeks:.0f} \u9031</b></span>
  </div>
</div>""".format(sid=signal_id, strat=strat, syms=syms, first=first, last=last, n=s['n'], weeks=s['total_weeks'])

def build_nav():
    return """<div class="main-nav">
  <button class="nav-tab active" onclick="switchPanel(this,'dash')">📊 <span class="nav-text">\u5100\u8868\u677f</span></button>
  <button class="nav-tab" onclick="switchPanel(this,'perf')">📈 <span class="nav-text">\u8868\u73fe\u5206\u6790</span></button>
  <button class="nav-tab" onclick="switchPanel(this,'risk')">\u26a0\ufe0f <span class="nav-text">\u98a8\u96aa\u8a55\u4f30</span></button>
  <button class="nav-tab" onclick="switchPanel(this,'copy')">💡 <span class="nav-text">Copy \u6c7a\u7b56</span></button>
  <button class="nav-tab" onclick="switchPanel(this,'data')">📌 <span class="nav-text">\u6578\u64da\u660e\u7d30</span></button>
</div>"""

def build_dashboard(signal_id, s):
    NL = '\n'
    
    # Hero
    profit_cls = cls_for(s['total_profit'])
    hero = """<div class="hero-row">
    <div class="hero-stat">
      <div class="val gold">{stars}</div>
      <div class="lbl">Copy \u8a55\u7d1a \u00b7 {label}</div>
    </div>
    <div class="hero-stat">
      <div class="val pos">{wr}</div>
      <div class="lbl">\u52dd\u7387\uff08{w}W / {l}L\uff09</div>
    </div>
    <div class="hero-stat">
      <div class="val {pcls}">{tp}</div>
      <div class="lbl">\u7e3d\u76c8\u5229 USD</div>
    </div>
  </div>""".format(stars=s['grade_stars'], label=s['grade_label'], wr=fmt_pct(s['win_rate']), w=s['wins'], l=s['losses'], pcls=profit_cls, tp=fmt_money(s['total_profit']))
    
    # Mini equity
    lp, ap = equity_svg_paths(s['equity'], 800, 200)
    mini_eq = """  <div class="card">
    <h2><span class="icon">📈</span> \u6536\u76ca\u66f2\u7dda</h2>
    <div class="chart-box">
      <svg class="equity-chart" viewBox="0 0 800 200" preserveAspectRatio="xMidYMid meet">
        <defs>
          <linearGradient id="eqFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#64b5f6" stop-opacity="0.3"/>
            <stop offset="100%" stop-color="#64b5f6" stop-opacity="0"/>
          </linearGradient>
        </defs>
        <line x1="0" y1="50" x2="800" y2="50" stroke="#1a1f2e" stroke-width="1"/>
        <line x1="0" y1="100" x2="800" y2="100" stroke="#1a1f2e" stroke-width="1"/>
        <line x1="0" y1="150" x2="800" y2="150" stroke="#1a1f2e" stroke-width="1"/>
        <path d="{lp}" fill="none" stroke="#64b5f6" stroke-width="2"/>
        <path d="{ap}" fill="url(#eqFill)"/>
      </svg>
    </div>
  </div>""".format(lp=lp, ap=ap)
    
    # Stat grid
    stat_grid = """  <div class="stat-grid">
    <div class="stat-box"><div class="v gold">{pf}</div><div class="l">\u76c8\u8667\u6bd4 (PF)</div></div>
    <div class="stat-box"><div class="v neg">{dd}</div><div class="l">\u6700\u5927\u56de\u64a4</div></div>
    <div class="stat-box"><div class="v">{mw}</div><div class="l">\u6700\u5927\u55ae\u7b46\u76c8\u5229</div></div>
    <div class="stat-box"><div class="v neg">{ml}</div><div class="l">\u6700\u5927\u55ae\u7b46\u8667\u640d</div></div>
    <div class="stat-box"><div class="v">{gr}</div><div class="l">\u7e3d\u589e\u9577\u7387</div></div>
    <div class="stat-box"><div class="v">{ah}</div><div class="l">\u5e73\u5747\u6301\u5009\u6642\u9593</div></div>
    <div class="stat-box"><div class="v gold">{ml2}</div><div class="l">\u4ea4\u6613\u5c64\u6578</div></div>
    <div class="stat-box"><div class="v">{fe}</div><div class="l">\u6700\u7d42\u6b0a\u76ca</div></div>
  </div>""".format(pf="{:.2f}".format(s['pf']), dd=fmt_pct(s['max_dd_pct']), mw=fmt_money(s['max_win']), ml=fmt_money(s['max_loss']), gr=fmt_pct(s['growth_rate']), ah=fmt_hours(s['avg_hold']), ml2=s['max_layers'], fe="${:,.0f}".format(s['final_equity']))
    
    # Risk
    martin_link = "martin_v4_{}.html".format(signal_id)
    risk = """  <div class="risk-status {rcls}">
    <div class="ri">{re}</div>
    <div>
      <div class="rt">{rl} \u00b7 {ru}</div>
      <div class="rd">\u6700\u5927\u56de\u64a4 {dd} \u00b7 \u6700\u5927\u5c64\u6578 L{ml} \u00b7 \u55ae\u7b46\u6700\u5927\u8667\u640d {ml2}</div>
    </div>
    <a href="{mlink}" style="margin-left:auto;background:var(--acc-dim);color:var(--acc);padding:8px 16px;border-radius:8px;font-weight:700;font-size:.85em;white-space:nowrap;border:1px solid var(--acc)">🔍 \u99ac\u4e01\u5256\u6790\u6cd5 V4 \u2192</a>
  </div>""".format(rcls=s['risk_class'], re=s['risk_emoji'], rl=s['risk_level'], ru=s['risk_level'].upper(), dd=fmt_pct(s['max_dd_pct']), ml=s['max_layers'], ml2=fmt_money(s['max_loss']), mlink=martin_link)
    
    # Direction table
    buy_pcls = cls_for(s['buy_s']['profit'])
    sell_pcls = cls_for(s['sell_s']['profit'])
    dir_html = """  <div class="two-col">
    <div class="card">
      <h2><span class="icon">💰</span> \u65b9\u5411\u8868\u73fe</h2>
      <table class="tbl">
        <thead><tr><th>\u65b9\u5411</th><th>\u7b46\u6578</th><th>\u52dd\u7387</th><th>\u76c8\u8667</th></tr></thead>
        <tbody>
          <tr><td>🟢 BUY</td><td>{bn}</td><td class="pos">{bwr}</td><td class="{bpc}">{bp}</td></tr>
          <tr><td>🔴 SELL</td><td>{sn}</td><td class="pos">{swr}</td><td class="{spc}">{sp}</td></tr>
        </tbody>
      </table>
    </div>
    <div class="card">
      <h2><span class="icon">📚</span> \u5c64\u6578\u5206\u6790</h2>
      <table class="tbl">
        <thead><tr><th>\u5c64</th><th>\u7b46\u6578</th><th>\u52dd\u7387</th><th>\u76c8\u8667</th></tr></thead>
        <tbody>
          {layer_rows}
        </tbody>
      </table>
    </div>
  </div>""".format(bn=s['buy_s']['n'], bwr=fmt_pct(s['buy_s']['win_rate']), bpc=buy_pcls, bp=fmt_money(s['buy_s']['profit']),
                   sn=s['sell_s']['n'], swr=fmt_pct(s['sell_s']['win_rate']), spc=sell_pcls, sp=fmt_money(s['sell_s']['profit']),
                   layer_rows=_layer_rows_html(s['layers']))
    
    # Holding time
    hb = s['hold_bins']
    total_h = sum(hb.values()) or 1
    bin_colors = {'<15min': 'green', '15-60min': 'blue', '1-4hr': 'gold', '4-12hr': 'yellow', '12hr+': 'red'}
    bars = []
    for label in ['<15min', '15-60min', '1-4hr', '4-12hr', '12hr+']:
        count = hb[label]
        pct = count / total_h * 100
        height = max(4, pct)
        bars.append('<div class="bar {}" style="height:{:.0f}%" title="{}: {}\u7b46 ({:.0f}%)"></div>'.format(bin_colors[label], height, label, count, pct))
    bars_html = NL.join(bars)
    
    labels_parts = []
    for label in ['<15min', '15-60min', '1-4hr', '4-12hr', '12hr+']:
        pct = hb[label] / total_h * 100
        labels_parts.append("<span>{} ({:.0f}%)</span>".format(label, pct))
    labels_html = NL.join(labels_parts)
    
    hold_html = """  <div class="card">
    <h2><span class="icon">\u23f1\ufe0f</span> \u6301\u5009\u6642\u9593\u5206\u4f48</h2>
    <div class="bar-chart">
{bars}
    </div>
    <div style="display:flex;justify-content:space-between;font-size:.75em;color:var(--text2);margin-top:6px">
      {labels}
    </div>
  </div>""".format(bars=bars_html, labels=labels_html)
    
    return '<div class="panel active" id="panel-dash">' + NL + hero + NL + mini_eq + NL + stat_grid + NL + risk + NL + dir_html + NL + hold_html + NL + '</div>'

def _layer_rows_html(layers):
    NL = '\n'
    rows = []
    for l in layers:
        cls = cls_for(l['profit'])
        rows.append('<tr><td><span class="badge blue">{}</span></td><td>{}</td><td class="pos">{}</td><td class="{}">{}</td></tr>'.format(
            l['tf'], l['n'], fmt_pct(l['win_rate']), cls, fmt_money(l['profit'])))
    return NL.join(rows)

def build_performance(signal_id, s):
    NL = '\n'
    
    # Large equity
    lp, ap = equity_svg_paths(s['equity'], 800, 380)
    y_labels = equity_y_labels(s['equity'], 5)
    y_positions = [16, 111, 206, 301, 376]
    y_labels_parts = []
    for i, y in enumerate(y_positions):
        y_labels_parts.append('<text x="8" y="{}" fill="#8892a6" font-size="12" font-family="-apple-system,sans-serif" font-weight="600" text-rendering="optimizeLegibility">{}</text>'.format(y, y_labels[i]))
    y_labels_html = NL.join(y_labels_parts)
    
    grid_parts = []
    for y in [0, 95, 190, 285, 380]:
        grid_parts.append('<line x1="0" y1="{}" x2="800" y2="{}" stroke="#1a1f2e" stroke-width="1"/>'.format(y, y))
    grid_html = NL.join(grid_parts)
    
    equity_tab = """    <div class="card">
      <h2><span class="icon">📈</span> \u5b8c\u6574\u6536\u76ca\u66f2\u7dda</h2>
      <div class="chart-box" style="height:400px">
        <svg style="display:block" width="100%" height="380" viewBox="0 0 800 380" preserveAspectRatio="none">
          <defs>
            <linearGradient id="eqFill2" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stop-color="#64b5f6" stop-opacity="0.25"/>
              <stop offset="100%" stop-color="#64b5f6" stop-opacity="0"/>
            </linearGradient>
          </defs>
          <g stroke="#1a1f2e" stroke-width="1">
            {grid}
          </g>
          <g fill="#8892a6" font-size="12" font-family="-apple-system,sans-serif" font-weight="600" text-rendering="optimizeLegibility">
            {ylabels}
          </g>
          <path d="{lp}" fill="none" stroke="#64b5f6" stroke-width="2"/>
          <path d="{ap}" fill="url(#eqFill2)"/>
        </svg>
      </div>
    </div>""".format(grid=grid_html, ylabels=y_labels_html, lp=lp, ap=ap)
    
    # Hourly
    hourly_rows_parts = []
    for h in range(24):
        if h in s['hourly']:
            d = s['hourly'][h]
            cls = cls_for(d['profit'])
            hourly_rows_parts.append('<tr><td>{:02d}:00-{:02d}:00</td><td>{}</td><td class="{}">{}</td></tr>'.format(h, h+1, d['n'], cls, fmt_money(d['profit'])))
    hourly_rows = NL.join(hourly_rows_parts)
    
    time_tab = """    <div class="card">
      <h2><span class="icon">🕐</span> \u4ea4\u6613\u6642\u6bb5\u5206\u6790</h2>
      <table class="tbl">
        <thead><tr><th>\u6642\u6bb5 (UTC)</th><th>\u7b46\u6578</th><th>\u76c8\u8667</th></tr></thead>
        <tbody>{hr}</tbody>
      </table>
    </div>""".format(hr=hourly_rows)
    
    # Holding bars
    hb = s['hold_bins']
    total_h = sum(hb.values()) or 1
    bin_colors = {'<15min': 'green', '15-60min': 'blue', '1-4hr': 'gold', '4-12hr': 'yellow', '12hr+': 'red'}
    bars_parts = []
    for label in ['<15min', '15-60min', '1-4hr', '4-12hr', '12hr+']:
        count = hb[label]
        pct = count / total_h * 100
        height = max(4, pct)
        bars_parts.append('<div class="bar {}" style="height:{:.0f}%"><span style="position:absolute;bottom:-20px;left:50%;transform:translateX(-50%);font-size:10px;color:var(--text2)">{}</span></div>'.format(bin_colors[label], height, count))
    bars_html = NL.join(bars_parts)
    
    hold_tab = """    <div class="card">
      <h2><span class="icon">\u23f1\ufe0f</span> \u6301\u5009\u6642\u9593\u5206\u4f48</h2>
      <div class="bar-chart" style="height:240px">
{bars}
      </div>
    </div>""".format(bars=bars_html)
    
    # Direction
    bs = s['buy_s']
    ss = s['sell_s']
    dir_tab = """    <div class="two-col">
      <div class="card">
        <h2>🟢 BUY \u8868\u73fe</h2>
        <div class="stat-grid" style="grid-template-columns:1fr 1fr">
          <div class="stat-box"><div class="v">{bn}</div><div class="l">\u7b46\u6578</div></div>
          <div class="stat-box"><div class="v pos">{bwr}</div><div class="l">\u52dd\u7387</div></div>
          <div class="stat-box"><div class="v {bpc}">{bp}</div><div class="l">\u7e3d\u76c8\u8667</div></div>
          <div class="stat-box"><div class="v">${bavg:.2f}</div><div class="l">\u5e73\u5747/\u7b46</div></div>
        </div>
      </div>
      <div class="card">
        <h2>🔴 SELL \u8868\u73fe</h2>
        <div class="stat-grid" style="grid-template-columns:1fr 1fr">
          <div class="stat-box"><div class="v">{sn}</div><div class="l">\u7b46\u6578</div></div>
          <div class="stat-box"><div class="v pos">{swr}</div><div class="l">\u52dd\u7387</div></div>
          <div class="stat-box"><div class="v {spc}">{sp}</div><div class="l">\u7e3d\u76c8\u8667</div></div>
          <div class="stat-box"><div class="v">${savg:.2f}</div><div class="l">\u5e73\u5747/\u7b46</div></div>
        </div>
      </div>
    </div>""".format(bn=bs['n'], bwr=fmt_pct(bs['win_rate']), bpc=cls_for(bs['profit']), bp=fmt_money(bs['profit']), bavg=bs['avg'],
                     sn=ss['n'], swr=fmt_pct(ss['win_rate']), spc=cls_for(ss['profit']), sp=fmt_money(ss['profit']), savg=ss['avg'])
    
    return """<div class="panel" id="panel-perf">
  <div class="sub-nav">
    <button class="sub-tab active" onclick="switchSub(this,'perf-equity')">📈 \u6536\u76ca\u66f2\u7dda</button>
    <button class="sub-tab" onclick="switchSub(this,'perf-time')">🕐 \u6642\u6bb5\u5206\u6790</button>
    <button class="sub-tab" onclick="switchSub(this,'perf-hold')">\u23f1\ufe0f \u6301\u5009\u6642\u9593</button>
    <button class="sub-tab" onclick="switchSub(this,'perf-dir')">\u2194\ufe0f \u65b9\u5411\u5206\u6790</button>
  </div>
  <div id="perf-equity">{eq}</div>
  <div id="perf-time" style="display:none">{tm}</div>
  <div id="perf-hold" style="display:none">{hd}</div>
  <div id="perf-dir" style="display:none">{dr}</div>
</div>""".format(eq=equity_tab, tm=time_tab, hd=hold_tab, dr=dir_tab)

def build_risk(signal_id, s):
    NL = '\n'
    martin_link = "martin_v4_{}.html".format(signal_id)
    
    layer_tfs = ', '.join(l['tf'] for l in s['layers'])
    risk_emoji_cls = 'pos' if s['risk_class'] == 'low' else ('gold' if s['risk_class'] == 'med' else 'neg')
    martin_desc = '\u5c6c\u65bc\u4f4e\u99ac\u4e01\u98a8\u96aa\u3002\u5927\u90e8\u5206\u8667\u640d\u53ef\u4ee5\u5feb\u901f\u6062\u5fa9\u3002' if s['max_layers'] <= 2 else '\u9700\u8981\u95dc\u6ce8\u591a\u5c64\u53e0\u52a0\u98a8\u96aa\u3002'
    
    martin_summary = """    <div class="card">
      <h2><span class="icon">🎲</span> \u99ac\u4e01\u98a8\u96aa\u6458\u8981</h2>
      <div class="stat-grid">
        <div class="stat-box"><div class="v gold">{ml}</div><div class="l">\u6700\u5927\u5c64\u6578</div></div>
        <div class="stat-box"><div class="v neg">{mloss}</div><div class="l">\u6700\u5927\u55ae\u7b46\u8667\u640d</div></div>
        <div class="stat-box"><div class="v">{tfs}</div><div class="l">\u7b56\u7565\u985e\u578b</div></div>
        <div class="stat-box"><div class="v {rcls}">{re}</div><div class="l">\u7834\u7522\u98a8\u96aa</div></div>
      </div>
      <p style="color:var(--text2);font-size:.85em;margin-top:8px">\u6b64\u7b56\u7565\u4e3b\u8981\u4f7f\u7528 {ml} \u5c64\uff08{tfs}\uff09\uff0c{desc}</p>
    </div>""".format(ml=s['max_layers'], mloss=fmt_money(abs(s['max_loss'])), tfs=layer_tfs, rcls=risk_emoji_cls, re=s['risk_emoji'], desc=martin_desc)
    
    # Blacklist rows
    bl_parts = []
    for t in s['worst_trades'][:5]:
        dt = t['close_time'].strftime('%m.%d %H:%M') if t['close_time'] else 'N/A'
        tp = t['type'].upper()
        lots = t['lots']
        loss = fmt_money2(t['net_profit'])
        hold = fmt_hours(t['holding_hours'])
        if t['lots'] >= 0.5:
            tag, tag_cls = '\u5927\u624b\u6578\u8667\u640d', 'red'
        elif t['holding_hours'] >= 12:
            tag, tag_cls = '\u9577\u6301\u5009\u8667\u640d', 'yellow'
        else:
            tag, tag_cls = '\u4e00\u822c\u8667\u640d', 'red'
        bl_parts.append('<tr><td>{}</td><td>{}</td><td>{:.2f}</td><td class="neg">{}</td><td>{}</td><td><span class="badge {}">{}</span></td></tr>'.format(dt, tp, lots, loss, hold, tag_cls, tag))
    bl_rows = NL.join(bl_parts)
    
    blacklist = """    <div class="card">
      <h2><span class="icon">\u26a0\ufe0f</span> \u9ed1\u540d\u55ae / \u9ad8\u98a8\u96aa\u4ea4\u6613</h2>
      <table class="tbl">
        <thead><tr><th>\u6642\u9593</th><th>\u65b9\u5411</th><th>\u624b\u6578</th><th>\u76c8\u8667</th><th>\u6301\u5009</th><th>\u5099\u8a3b</th></tr></thead>
        <tbody>{bl}</tbody>
      </table>
    </div>""".format(bl=bl_rows)
    
    # Layer analysis rows
    lr_parts = []
    for i, l in enumerate(s['layers']):
        grade = 'A' if l['win_rate'] >= 80 else ('B' if l['win_rate'] >= 60 else 'C')
        grade_cls = 'green' if grade == 'A' else ('yellow' if grade == 'B' else 'red')
        cls = cls_for(l['profit'])
        lr_parts.append('<tr><td>L{}</td><td>{}</td><td>{}</td><td class="pos">{}</td><td class="{}">{}</td><td><span class="badge {}">{}</span></td></tr>'.format(
            i+1, l['tf'], l['n'], fmt_pct(l['win_rate']), cls, fmt_money(l['profit']), grade_cls, grade))
    layer_rows = NL.join(lr_parts)
    
    layer_tab = """    <div class="card">
      <h2><span class="icon">📚</span> \u5c64\u6578\u5206\u6790</h2>
      <table class="tbl">
        <thead><tr><th>\u5c64</th><th>\u7b56\u7565</th><th>\u7b46\u6578</th><th>\u52dd\u7387</th><th>\u76c8\u8667</th><th>\u8a55\u7d1a</th></tr></thead>
        <tbody>{lr}</tbody>
      </table>
    </div>""".format(lr=layer_rows)
    
    vol_tab = """    <div class="card">
      <h2><span class="icon">📏</span> \u6ce2\u5e45\u5206\u6790</h2>
      <div class="stat-grid">
        <div class="stat-box"><div class="v">${awp:.1f}</div><div class="l">\u5e73\u5747\u76c8\u5229 Pips</div></div>
        <div class="stat-box"><div class="v neg">${alp:.1f}</div><div class="l">\u5e73\u5747\u8667\u640d Pips</div></div>
        <div class="stat-box"><div class="v">{rr:.2f}</div><div class="l">\u76c8\u8667\u6bd4</div></div>
        <div class="stat-box"><div class="v">{ahw}</div><div class="l">\u76c8\u5229\u5e73\u5747\u6301\u5009</div></div>
        <div class="stat-box"><div class="v">{ahl}</div><div class="l">\u8667\u640d\u5e73\u5747\u6301\u5009</div></div>
        <div class="stat-box"><div class="v">${gp:,.0f}</div><div class="l">\u7e3d\u76c8\u5229</div></div>
        <div class="stat-box"><div class="v neg">-${gl:,.0f}</div><div class="l">\u7e3d\u8667\u640d</div></div>
        <div class="stat-box"><div class="v">{dd}</div><div class="l">\u6700\u5927\u56de\u64a4</div></div>
      </div>
    </div>""".format(awp=s['avg_win_pips'], alp=s['avg_loss_pips'], rr=s['rr'], ahw=fmt_hours(s['avg_hold_win']), ahl=fmt_hours(s['avg_hold_loss']), gp=s['gross_profit'], gl=s['gross_loss'], dd=fmt_pct(s['max_dd_pct']))
    
    return """<div class="panel" id="panel-risk">
  <div class="risk-status {rcls}" style="margin-top:0">
    <div class="ri">{re}</div>
    <div>
      <div class="rt">{rl} \u00b7 {ru}</div>
      <div class="rd">\u6700\u5927\u56de\u64a4 {dd} \u00b7 \u55ae\u7b46\u6700\u5927\u8667\u640d {ml} \u00b7 \u5efa\u8b70\u95dc\u6ce8 L3+ \u5c64\u7d1a\u98a8\u96aa</div>
    </div>
  </div>
  <div class="sub-nav">
    <button class="sub-tab active" onclick="switchSub(this,'risk-martin')">🎲 \u99ac\u4e01\u98a8\u96aa</button>
    <button class="sub-tab" onclick="switchSub(this,'risk-layer')">📚 \u5c64\u6578</button>
    <button class="sub-tab" onclick="switchSub(this,'risk-vol')">📏 \u6ce2\u5e45</button>
    <a href="{mlink}" style="margin-left:auto;color:var(--acc);font-size:13px;font-weight:600;padding:8px 14px;white-space:nowrap">🔍 \u5b8c\u6574\u99ac\u4e01\u5256\u6790\u6cd5 V4 \u2192</a>
  </div>
  <div id="risk-martin">{ms}{bl}</div>
  <div id="risk-layer" style="display:none">{lt}</div>
  <div id="risk-vol" style="display:none">{vt}</div>
</div>""".format(rcls=s['risk_class'], re=s['risk_emoji'], rl=s['risk_level'], ru=s['risk_level'].upper(), dd=fmt_pct(s['max_dd_pct']), ml=fmt_money(s['max_loss']),
                mlink=martin_link, ms=martin_summary, bl=blacklist, lt=layer_tab, vt=vol_tab)

def build_copy_decision(signal_id, s):
    NL = '\n'
    
    grade_card = """  <div class="card grade-display">
    <div class="grade-stars">{stars}</div>
    <div class="grade-label" style="color:{gcolor}">{label}</div>
    <div class="grade-desc">\u9ad8\u52dd\u7387\uff08{wr}\uff09+ PF\uff08{pf:.2f}\uff09+ {ml}\u5c64 + {syms}</div>
  </div>""".format(stars=s['grade_stars'], gcolor=s['grade_color'], label=s['grade_label'], wr=fmt_pct(s['win_rate']), pf=s['pf'], ml=s['max_layers'], syms=' / '.join(s['symbols']))
    
    tp_low = int(s['avg_win_pips'] * 0.8)
    tp_high = int(s['avg_win_pips'] * 1.2)
    sl_soft_low = int(s['avg_loss_pips'] * 0.8)
    sl_soft_high = int(s['avg_loss_pips'] * 1.2)
    sl_hard_low = int(s['avg_loss_pips'] * 1.5)
    sl_hard_high = int(s['avg_loss_pips'] * 2.0)
    monthly_growth = s['growth_rate'] / max(1, s['total_weeks']) * 4.3
    
    tpsl_tab = """  <div class="two-col">
    <div class="card">
      <h2><span class="icon">📐</span> TP/SL \u5efa\u8b70</h2>
      <table class="tbl">
        <tbody>
          <tr><td>🎯 \u5efa\u8b70\u6b62\u8cfa (TP)</td><td class="gold">{}-{} pips</td></tr>
          <tr><td>🛡\ufe0f \u8edf\u6b62\u875d (Soft SL)</td><td class="neg">{}-{} pips</td></tr>
          <tr><td>🛡\ufe0f \u786c\u6b62\u875d (Hard SL)</td><td class="neg">{}-{} pips</td></tr>
          <tr><td>📊 \u5e73\u5747\u76c8\u5229</td><td class="pos">{}/\u7b46</td></tr>
          <tr><td>📊 \u5e73\u5747\u8667\u640d</td><td class="neg">{}/\u7b46</td></tr>
          <tr><td>\u2696\ufe0f \u76c8\u8667\u6bd4</td><td>1 : {:.2f}</td></tr>
        </tbody>
      </table>
    </div>
    <div class="card">
      <h2><span class="icon">💰</span> \u5009\u4f4d\u5efa\u8b70</h2>
      <table class="tbl">
        <tbody>
          <tr><td>💵 \u5efa\u8b70\u672c\u91d1</td><td>${:,.0f}+</td></tr>
          <tr><td>📊 \u624b\u6578</td><td>0.01 \u6a19\u6e96</td></tr>
          <tr><td>\u26a1 \u6700\u5927\u540c\u6642\u6301\u5009</td><td>{} \u500b</td></tr>
          <tr><td>🔮 \u9810\u671f\u6708\u589e\u9577</td><td class="pos">{:.2f}%</td></tr>
          <tr><td>📉 \u9810\u671f\u6700\u5927\u56de\u64a4</td><td class="neg">{:.0f}-{:.0f}%</td></tr>
          <tr><td>\u23f1\ufe0f \u5efa\u8b70\u6301\u5009\u6642\u9593</td><td>&lt; {} \u5c0f\u6642</td></tr>
        </tbody>
      </table>
    </div>
  </div>""".format(
        tp_low, tp_high, sl_soft_low, sl_soft_high, sl_hard_low, sl_hard_high,
        fmt_money2(s['avg_win']), fmt_money2(s['avg_loss']), s['rr'],
        s['initial_deposit'], min(4, s['max_layers']+2), monthly_growth,
        max(10, s['max_dd_pct']*0.5), s['max_dd_pct'], max(1, int(s['avg_hold']*2)))
    
    # Score
    wr_score = min(25, s['win_rate'] / 100 * 25)
    pf_score = min(30, s['pf'] / 3 * 30)
    rr_score = min(20, s['rr'] / 1.5 * 20)
    sample_score = min(15, min(s['n'], 500) / 500 * 15)
    hold_eff_val = 1.0 if s['avg_hold'] < 4 else max(0, 8 - s['avg_hold']) / 4
    hold_score = min(10, hold_eff_val * 10)
    
    def grade_badge(sc):
        if sc >= 22: return '<span class="badge green">S</span>'
        if sc >= 16: return '<span class="badge green">A</span>'
        if sc >= 10: return '<span class="badge yellow">B</span>'
        return '<span class="badge red">C</span>'
    
    score_tab = """    <div class="card">
      <h2><span class="icon">🎯</span> \u8cea\u91cf\u8a55\u5206\uff085\u7ef4\u5ea6\uff09\u00b7 \u7e3d\u5206 {:.1f}/100</h2>
      <table class="tbl">
        <thead><tr><th>\u7ef4\u5ea6</th><th>\u8a55\u5206</th><th>\u52a0\u6b0a</th><th>\u5f97\u5206</th><th>\u8a55\u7d1a</th></tr></thead>
        <tbody>
          <tr><td>\u52dd\u7387</td><td>{}</td><td>25%</td><td class="pos">{:.1f}</td><td>{}</td></tr>
          <tr><td>\u76c8\u8667\u6bd4 (PF)</td><td>{:.2f}</td><td>30%</td><td class="pos">{:.1f}</td><td>{}</td></tr>
          <tr><td>Risk/Reward</td><td>1 : {:.2f}</td><td>20%</td><td>{:.1f}</td><td>{}</td></tr>
          <tr><td>\u6a23\u672c\u91cf</td><td>{}</td><td>15%</td><td class="pos">{:.1f}</td><td>{}</td></tr>
          <tr><td>\u6301\u5009\u6548\u7387</td><td>{}</td><td>10%</td><td class="pos">{:.1f}</td><td>{}</td></tr>
        </tbody>
      </table>
    </div>""".format(
        s['score'],
        fmt_pct(s['win_rate']), wr_score, grade_badge(wr_score),
        s['pf'], pf_score, grade_badge(pf_score),
        s['rr'], rr_score, grade_badge(rr_score),
        s['n'], sample_score, grade_badge(sample_score),
        fmt_hours(s['avg_hold']), hold_score, grade_badge(hold_score))
    
    sim_tab = """    <div class="card">
      <h2><span class="icon">💰</span> Copy \u6a21\u64ec</h2>
      <div class="stat-grid">
        <div class="stat-box"><div class="v">$1,000</div><div class="l">\u5efa\u8b70\u672c\u91d1</div></div>
        <div class="stat-box"><div class="v pos">+{:.1f}%</div><div class="l">\u9810\u671f\u6708\u589e\u9577</div></div>
        <div class="stat-box"><div class="v">${:.0f}</div><div class="l">1\u500b\u6708\u5f8c</div></div>
        <div class="stat-box"><div class="v">${:.0f}</div><div class="l">3\u500b\u6708\u5f8c</div></div>
        <div class="stat-box"><div class="v">${:.0f}</div><div class="l">6\u500b\u6708\u5f8c</div></div>
        <div class="stat-box"><div class="v">${:.0f}</div><div class="l">12\u500b\u6708\u5f8c</div></div>
      </div>
    </div>""".format(
        monthly_growth,
        1000 * (1 + monthly_growth/100),
        1000 * (1 + monthly_growth/100)**3,
        1000 * (1 + monthly_growth/100)**6,
        1000 * (1 + monthly_growth/100)**12)
    
    return """<div class="panel" id="panel-copy">
{gc}
  <div class="sub-nav">
    <button class="sub-tab active" onclick="switchSub(this,'copy-tpsl')">📐 TP/SL \u5efa\u8b70</button>
    <button class="sub-tab" onclick="switchSub(this,'copy-score')">🎯 \u8a55\u5206\u8a73\u60c5</button>
    <button class="sub-tab" onclick="switchSub(this,'copy-sim')">💰 \u6a21\u64ec</button>
  </div>
  <div id="copy-tpsl">{tp}</div>
  <div id="copy-score" style="display:none">{sc}</div>
  <div id="copy-sim" style="display:none">{sm}</div>
</div>""".format(gc=grade_card, tp=tpsl_tab, sc=score_tab, sm=sim_tab)

def build_data_details(signal_id, s):
    NL = '\n'
    
    # Recent trades
    tr_parts = []
    for t in s['recent_trades']:
        dt = t['close_time'].strftime('%m.%d %H:%M') if t['close_time'] else 'N/A'
        tp = t['type'].upper()
        cls_p = cls_for(t['net_profit'])
        cls_pip = cls_for(t['pips'])
        tr_parts.append('<tr><td>{}</td><td>{}</td><td>{:.2f}</td><td>{:.5f}</td><td>{:.5f}</td><td class="{}">{:+.1f}</td><td class="{}">{}</td><td>{}</td><td>{}</td></tr>'.format(
            dt, tp, t['lots'], t['open_price'], t['close_price'], cls_pip, t['pips'], cls_p, fmt_money2(t['net_profit']), fmt_hours(t['holding_hours']), t['magic']))
    trade_rows = NL.join(tr_parts)
    
    pos_tab = """    <div class="card">
      <h2><span class="icon">📌</span> \u6700\u8fd1 {} \u7b46\u4ea4\u6613</h2>
      <div style="overflow-x:auto">
      <table class="tbl">
        <thead><tr><th>\u5e73\u5009\u6642\u9593</th><th>\u65b9\u5411</th><th>\u624b\u6578</th><th>\u958b\u5009\u50f9</th><th>\u5e73\u5009\u50f9</th><th>Pips</th><th>\u76c8\u8667</th><th>\u6301\u5009</th><th>Magic</th></tr></thead>
        <tbody>{}</tbody>
      </table>
      </div>
    </div>""".format(len(s['recent_trades']), trade_rows)
    
    magic_str = ' / '.join(s['magics']) if s['magics'] else 'N/A'
    strat_str = ', '.join(s['strategy_names']) if s['strategy_names'] else 'Unknown'
    set_tab = """    <div class="card">
      <h2><span class="icon">\u2699\ufe0f</span> SET \u53c3\u6578</h2>
      <table class="tbl">
        <tbody>
          <tr><td>Magic Number</td><td class="gold">{}</td></tr>
          <tr><td>\u7b56\u7565\u985e\u578b</td><td>{}</td></tr>
          <tr><td>\u6642\u9593\u6846\u67b6</td><td>{}</td></tr>
          <tr><td>\u4ea4\u6613\u54c1\u7a2e</td><td>{}</td></tr>
          <tr><td>\u521d\u59cb\u672c\u91d1</td><td>${:,.0f}</td></tr>
          <tr><td>\u7e3d\u4ea4\u6613\u6578</td><td>{} \u7b46</td></tr>
        </tbody>
      </table>
      <p style="color:var(--text2);font-size:.85em;margin-top:8px">\u26a0\ufe0f \u5b8c\u6574 SET \u53c3\u6578\u9700\u5f9e AlgoForest Settings tab \u4e0b\u8f09</p>
    </div>""".format(magic_str, strat_str, ', '.join(l['tf'] for l in s['layers']), ' / '.join(s['symbols']), s['initial_deposit'], s['n'])
    
    raw_tab = """    <div class="card">
      <h2><span class="icon">📄</span> \u539f\u59cb\u6578\u64da</h2>
      <p style="color:var(--text2);padding:20px 0;text-align:center">📥 <a href="../downloads/{}.csv">\u4e0b\u8f09\u5b8c\u6574 CSV\uff08{} \u7b46\uff09</a></p>
    </div>""".format(signal_id, s['n'])
    
    return """<div class="panel" id="panel-data">
  <div class="sub-nav">
    <button class="sub-tab active" onclick="switchSub(this,'data-pos')">📌 \u5009\u4f4d\u660e\u7d30</button>
    <button class="sub-tab" onclick="switchSub(this,'data-set')">\u2699\ufe0f SET \u53c3\u6578</button>
    <button class="sub-tab" onclick="switchSub(this,'data-raw')">📄 \u539f\u59cb\u6578\u64da</button>
  </div>
  <div id="data-pos">{}</div>
  <div id="data-set" style="display:none">{}</div>
  <div id="data-raw" style="display:none">{}</div>
</div>""".format(pos_tab, set_tab, raw_tab)

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate_html(signal_id, stats, strategy_name=None):
    NL = '\n'
    parts = [
        '<!DOCTYPE html>',
        '<html lang="zh-HK">',
        '<head>',
        '<meta charset="UTF-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>TSA v2 \u2014 Signal {} \u6df1\u5ea6\u5206\u6790</title>'.format(signal_id),
        '<style>{}</style>'.format(CSS),
        '</head>',
        '<body>',
        build_header(signal_id, stats, strategy_name),
        build_nav(),
        build_dashboard(signal_id, stats),
        build_performance(signal_id, stats),
        build_risk(signal_id, stats),
        build_copy_decision(signal_id, stats),
        build_data_details(signal_id, stats),
        JS,
        '</body>',
        '</html>',
    ]
    return NL.join(parts)

def main():
    parser = argparse.ArgumentParser(description='Generate TSA v2 deep analysis report')
    parser.add_argument('csv_path', help='Path to signal CSV file')
    parser.add_argument('--signal-id', required=True, help='Signal ID')
    parser.add_argument('--strategy-name', default=None, help='Strategy name (auto-detected from CSV if omitted)')
    parser.add_argument('--output', '-o', required=True, help='Output HTML path')
    
    args = parser.parse_args()
    
    trades, initial_deposit = load_csv(args.csv_path)
    if not trades:
        print("ERROR: No trades found in {}".format(args.csv_path), file=sys.stderr)
        sys.exit(1)
    
    stats = compute_stats(trades, initial_deposit)
    
    strategy_name = args.strategy_name
    if not strategy_name and stats['strategy_names']:
        strategy_name = ', '.join(stats['strategy_names'])
    
    html = generate_html(args.signal_id, stats, strategy_name)
    
    os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(html)
    
    size_kb = os.path.getsize(args.output) / 1024
    print("Generated {}".format(args.output))
    print("   Signal {}: {} trades, {} win rate, PF {:.2f}".format(args.signal_id, stats['n'], fmt_pct(stats['win_rate']), stats['pf']))
    print("   Final equity: ${:,.0f}, Growth: {}".format(stats['final_equity'], fmt_pct(stats['growth_rate'])))
    print("   Grade: {} {}, Risk: {}".format(stats['grade_stars'], stats['grade_label'], stats['risk_level']))
    print("   File size: {:.1f} KB".format(size_kb))

if __name__ == '__main__':
    main()
