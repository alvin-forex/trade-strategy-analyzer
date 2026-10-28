#!/usr/bin/env python3
"""
Sandbox test for export_hst.py v2 — synthesizes MT4 v401 .hst files and
verifies the exported JSON contracts. (機房無 /mnt/c，照健康燈沙盒模式)

Builds a synthetic history dir with:
  EURUSD15.hst  (M15, intraday -> new contract)
  EURUSD60.hst  (H1,  intraday -> new contract)
  EURUSD1440.hst(D1,  legacy contract)
  EURUSD5.hst   (M5,  guards: tf=5 must NOT steal EURUSD15.hst)
  XAUUSD15.hst  (M15, guards: pair detection with different symbol)
  XAUUSD60.hst  (H1,  guards: pair detection at tf=60)

Run:  python3 scripts/tsa_redo/ohlc_sandbox_test.py
Output: scripts/tsa_redo/ohlc_sandbox/ (auto-recreated, safe to delete)
"""
import struct, os, shutil, subprocess, json, sys, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
SANDBOX = os.path.join(HERE, 'ohlc_sandbox', 'hist')
OUTDIR = os.path.join(HERE, 'ohlc_sandbox', 'out')
EXPORTER = os.path.join(HERE, '..', 'export_hst.py')

HEADER = struct.pack('<i64s12siiii13i', 401, b'TestBroker', b' ', 0, 5,
                     0, 0, *([0] * 13))


def make_hst(path, period, bars):
    """bars: list of (epoch, o, h, l, c, vol, spread)"""
    with open(path, 'wb') as f:
        f.write(HEADER)
        for t, o, h, l, c, v, sp in bars:
            f.write(struct.pack('<i4xddddqi8x', t, o, h, l, c, v, sp))
            assert struct.calcsize('<i4xddddqi8x') == 60


def main():
    shutil.rmtree(os.path.dirname(SANDBOX), ignore_errors=True)
    os.makedirs(SANDBOX, exist_ok=True)
    os.makedirs(OUTDIR, exist_ok=True)

    base = int(datetime.datetime(2026, 10, 28, 0, 0).timestamp())
    fails = []

    # --- M15: 8 bars covering 2 half-hours 2026-10-28 00:00..01:45
    m15 = [(base + i * 900, 1.08000 + i * 0.00010, 1.08020 + i * 0.00010,
            1.07990, 1.08010 + i * 0.00010, 100 + i, 12 + i) for i in range(8)]
    make_hst(os.path.join(SANDBOX, 'EURUSD15.hst'), 15, m15)

    # --- H1: 5 bars 2026-10-28 00:00..04:00
    h1 = [(base + i * 3600, 1.0800 + i * 0.0002, 1.0805 + i * 0.0002,
           1.0798, 1.0802 + i * 0.0002, 500 + i, 15) for i in range(5)]
    make_hst(os.path.join(SANDBOX, 'EURUSD60.hst'), 60, h1)

    # --- D1: 40 bars (>=15 so RSI/ATR indicators can be computed)
    d1 = [(base + i * 86400, 1.08 + i * 0.001, 1.085 + i * 0.001,
           1.078 + i * 0.001, 1.083 + i * 0.001, 10000 + i, 20)
          for i in range(40)]
    make_hst(os.path.join(SANDBOX, 'EURUSD1440.hst'), 1440, d1)

    # --- XAUUSD H1: 4 bars (pair detection at tf=60)
    x60 = [(base + i * 3600, 2750.0 + i, 2751.0 + i, 2749.5, 2750.5 + i,
            300 + i, 25) for i in range(4)]
    make_hst(os.path.join(SANDBOX, 'XAUUSD60.hst'), 60, x60)

    # --- M5: 3 bars (must not be matched when tf=15)
    m5 = [(base + i * 300, 1.0800, 1.0801, 1.0799, 1.0800, 50, 10)
          for i in range(3)]
    make_hst(os.path.join(SANDBOX, 'EURUSD5.hst'), 5, m5)

    # --- XAUUSD M15 (pair detection)
    x15 = [(base + i * 900, 2750.0 + i, 2751.0 + i, 2749.5, 2750.5 + i,
            80 + i, 25) for i in range(6)]
    make_hst(os.path.join(SANDBOX, 'XAUUSD15.hst'), 15, x15)

    def run(args):
        return subprocess.run([sys.executable, EXPORTER] + args,
                              capture_output=True, text=True)

    def check(cond, msg):
        print(('  ✅ ' if cond else '  ❌ ') + msg)
        if not cond:
            fails.append(msg)

    # ================= T1: M15 export =================
    print('T1: --tf 15 (M15, new contract)')
    r = run(['--src', SANDBOX, '--out', OUTDIR, '--tf', '15', '--pairs', 'EURUSD'])
    check(r.returncode == 0, f'exit=0 (stderr={r.stderr.strip()[:80]})')
    p = os.path.join(OUTDIR, 'EURUSD_M15.json')
    check(os.path.exists(p), 'EURUSD_M15.json created')
    d = json.load(open(p))
    check(list(d.keys())[:5] == ['updated', 'symbol', 'timeframe', 'source', 'start'],
          f"top keys updated/symbol/timeframe/source/start (got {list(d.keys())[:5]})")
    check(d['timeframe'] == 'M15', f"timeframe==M15 (got {d['timeframe']})")
    check(d['count'] == 8, f"count==8 (got {d['count']})")
    b0 = d['bars'][0]
    check(set(b0.keys()) == {'timestamp', 'open', 'high', 'low', 'close', 'volume', 'spread'},
          f"bar keys == new contract (got {sorted(b0.keys())})")
    exp_ts = datetime.datetime.fromtimestamp(base).strftime('%Y-%m-%dT%H:%M')
    check(b0['timestamp'] == exp_ts, f"timestamp ISO with time (got {b0['timestamp']}, want {exp_ts})")
    check(b0['spread'] == 12, f"spread==12 (got {b0['spread']})")
    check('T' in d['start'] and 'T' in d['end'], 'start/end carry intraday time')

    # ================= T2: H1 export =================
    print('T2: --tf 60 (H1 label mapping 60->H1, not M60)')
    r = run(['--src', SANDBOX, '--out', OUTDIR, '--tf', '60'])
    check(r.returncode == 0, f'exit=0')
    check(os.path.exists(os.path.join(OUTDIR, 'EURUSD_H1.json')), 'EURUSD_H1.json (label H1)')
    check(os.path.exists(os.path.join(OUTDIR, 'XAUUSD_H1.json')), 'XAUUSD_H1.json (pair detect, H1)')
    check(os.path.exists(os.path.join(OUTDIR, 'manifest_H1.json')), 'manifest_H1.json (per-TF manifest)')
    d = json.load(open(os.path.join(OUTDIR, 'EURUSD_H1.json')))
    check(d['timeframe'] == 'H1', f"timeframe==H1 (got {d['timeframe']})")
    check(d['count'] == 5, f"count==5 (got {d['count']})")
    m = json.load(open(os.path.join(OUTDIR, 'manifest_H1.json')))
    check(m['timeframe'] == 'H1' and m['total_pairs'] == 2, f"manifest tf/total_pairs==2 (got {m['timeframe']}/{m['total_pairs']})")
    check('pairs' in m and 'total_bars' in m, 'manifest legacy keys kept')

    # ================= T3: D1 legacy unchanged =================
    print('T3: --tf 1440 (D1 legacy contract preserved)')
    r = run(['--src', SANDBOX, '--out', OUTDIR, '--tf', '1440', '--indicators'])
    check(r.returncode == 0, f'exit=0')
    d = json.load(open(os.path.join(OUTDIR, 'EURUSD_D1.json')))
    check(d['timeframe'] == 'D1' and 'start' in d and 'end' in d, 'D1 top keys legacy')
    check(d['count'] == 40, f"D1 count==40 (got {d['count']})")
    check(set(d['bars'][0].keys()) == {'d', 'o', 'h', 'l', 'c', 'v'},
          f"D1 bar keys == legacy d/o/h/l/c/v (got {sorted(d['bars'][0].keys())})")
    check('indicators' in d, 'D1 indicators still attached')
    check(os.path.exists(os.path.join(OUTDIR, 'manifest.json')), 'manifest.json legacy name for D1')

    # ================= T4: --limit =================
    print('T4: --limit 3 (keep most recent N bars)')
    r = run(['--src', SANDBOX, '--out', OUTDIR, '--tf', '15', '--pairs', 'EURUSD', '--limit', '3'])
    check(r.returncode == 0, f'exit=0')
    d = json.load(open(os.path.join(OUTDIR, 'EURUSD_M15.json')))
    check(d['count'] == 3, f"count==3 (got {d['count']})")
    check(d['bars'][0]['timestamp'] > '2026-10-28T01:00', 'kept the MOST RECENT bars')
    m = json.load(open(os.path.join(OUTDIR, 'manifest_M15.json')))
    check(m.get('limit') == 3, 'manifest records limit')

    # ================= T5: filename traps =================
    print('T5: filename detection traps')
    r = run(['--src', SANDBOX, '--out', OUTDIR, '--tf', '15', '--pairs', 'EURUSD,XAUUSD'])
    d = json.load(open(os.path.join(OUTDIR, 'EURUSD_M15.json')))
    check(d['count'] == 8, f"tf=15 sees 8 M15 bars (M5 file not stolen; got {d['count']})")
    check(d['symbol'] == 'EURUSD', f"pair name clean 'EURUSD' (got {d['symbol']})")
    d = json.load(open(os.path.join(OUTDIR, 'XAUUSD_M15.json')))
    check(d['symbol'] == 'XAUUSD', f"XAUUSD pair detect (got {d['symbol']})")

    print()
    if fails:
        print(f'❌ {len(fails)} FAILURES:')
        for f_ in fails:
            print('   -', f_)
        sys.exit(1)
    print('✅ ALL SANDBOX TESTS PASSED')


if __name__ == '__main__':
    main()
