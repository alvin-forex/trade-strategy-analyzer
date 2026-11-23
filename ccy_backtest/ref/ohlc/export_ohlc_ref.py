#!/usr/bin/env python3
"""OC data-lane exporter — CP-BT1 parity OHLC reference windows (2026-11-23 09:15 HKT).

Input : ccy_backtest/ref/ohlc_sampling_list.csv (ZCODE 20261122_1440, seed=20261122)
Source: A06E MT4 terminal .hst history (server Alpari-Pro.ECN-Demo first; other
        A06E server dirs as fallback) — server-time domain, same clock as reader csv.
Output: ccy_backtest/ref/ohlc/idx{NN}_{TF}_{YYYYMMDD_HHMM}.csv
        Columns: idx,timestamp,tf,symbol,bar_time,open,high,low,close
        One file per (timepoint, window-TF); all instruments in one file,
        aligned by construction (bars with bar_time <= timestamp, last N=350).
Also  : MANIFEST_summary.csv (per-file symbol/bar counts + shortfalls)

Rules per ZCODE spec 20261122_1440:
  - every timepoint gets an H1 main window (PairTF = H1);
  - idx with TF != H1 additionally get that TF's window (multi-TF controls);
  - idx 1/23 (2011 isolated reader row) skipped if hst lacks 2011 data;
  - M5 hst exists only for XAUUSD on A06E -> other symbols recorded as shortfall.
Re-run: python3 ccy_backtest/ref/ohlc/export_ohlc_ref.py   (idempotent overwrite)
"""
import csv, os, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'engine', 'research'))
import hst_lib

TF_MIN = {'H1': 60, 'H4': 240, 'M30': 30, 'M15': 15, 'M5': 5, 'M1': 1}
hst_lib.TF_FILE['M5'] = '5'
hst_lib.TF_FILE['M1'] = '1'

SYMS = ['AUDCAD','AUDCHF','AUDJPY','AUDNZD','AUDUSD','CADCHF','CADJPY','CHFJPY',
        'EURAUD','EURCAD','EURCHF','EURGBP','EURJPY','EURNZD','EURUSD',
        'GBPAUD','GBPCAD','GBPCHF','GBPJPY','GBPNZD','GBPUSD',
        'NZDCAD','NZDCHF','NZDJPY','NZDUSD','USDCAD','USDCHF','USDJPY',
        'XAUAUD','XAUEUR','XAUGBP','XAUJPY','XAUUSD']

_cache = {}
_ALPARI = '/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/A06E6395D71C5597BD3D45E90C51C549/history/Alpari-Pro.ECN-Demo'

def bars_for(sym, tf):
    # CP-BT1 parity MUST stay in the reader's broker domain: Alpari-Pro.ECN-Demo
    # only (reader csv + these hst share one server clock and one price feed).
    key = (sym, tf)
    if key not in _cache:
        p = os.path.join(_ALPARI, f"{sym}{hst_lib.TF_FILE[tf]}.hst")
        _cache[key] = hst_lib.read_hst(p) if os.path.exists(p) else []
    return _cache[key]

def epoch(s):
    return int(datetime.datetime.strptime(s, '%Y.%m.%d %H:%M')
               .replace(tzinfo=datetime.timezone.utc).timestamp())

def fmt_time(t):
    return (datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
            + datetime.timedelta(seconds=t)).strftime('%Y.%m.%d %H:%M')

def main():
    rows = list(csv.DictReader(open(os.path.join(HERE, '..', 'ohlc_sampling_list.csv'))))
    summary = []
    for r in rows:
        idx = int(r['idx']); ts_s = r['timestamp']; tf = r['timeframe']; N = int(r['window_bars_N'])
        if idx in (1, 23):
            continue  # 2011 isolated reader row — no 2011 hst; ZCODE 1440 marks these optional
        ts_e = epoch(ts_s)
        windows = [('H1', ts_e)] if tf == 'H1' else [('H1', ts_e), (tf, ts_e)]
        for wtf, wts_e in windows:
            stamp = ts_s.replace('.', '').replace(':', '').replace(' ', '_')
            fn = f'idx{idx:02d}_{wtf}_{stamp}.csv'
            path = os.path.join(HERE, fn)
            counts, short, anchor = {}, [], ''
            with open(path, 'w', newline='') as f:
                w = csv.writer(f)
                w.writerow(['idx', 'timestamp', 'tf', 'symbol', 'bar_time', 'open', 'high', 'low', 'close'])
                for sym in SYMS:
                    bars = [b for b in bars_for(sym, wtf) if b[0] <= wts_e][-N:]
                    counts[sym] = len(bars)
                    if len(bars) < N:
                        short.append(f'{sym}:{len(bars)}')
                    if sym == 'EURUSD' and bars:
                        anchor = fmt_time(bars[-1][0])
                    for b in bars:
                        w.writerow([idx, ts_s, wtf, sym, fmt_time(b[0]),
                                    f'{b[1]:.5f}', f'{b[2]:.5f}', f'{b[3]:.5f}', f'{b[4]:.5f}'])
            total = sum(counts.values())
            summary.append({'file': fn, 'idx': idx, 'window_tf': wtf, 'symbols_full': sum(1 for c in counts.values() if c == N),
                            'symbols_partial_or_zero': len(short), 'total_rows': total, 'anchor_last_EURUSD_bar': anchor,
                            'shortfalls': ';'.join(short) if short else ''})
            print(f'{fn}: rows={total} full={summary[-1]["symbols_full"]}/33 short={len(short)}')
    with open(os.path.join(HERE, 'MANIFEST_summary.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['file', 'idx', 'window_tf', 'symbols_full', 'symbols_partial_or_zero', 'total_rows', 'anchor_last_EURUSD_bar', 'shortfalls'])
        w.writeheader(); w.writerows(summary)
    print('DONE', len(summary), 'files')

if __name__ == '__main__':
    main()
