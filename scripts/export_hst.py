#!/usr/bin/env python3
"""
MT4 .hst History Exporter — converts MT4 .hst files to JSON for web frontend.

v2 (2026-10-29): multi-timeframe + intraday support
  - TF labels: 1->M1, 5->M5, 15->M15, 30->M30, 60->H1, 240->H4, 1440->D1 ...
  - Intraday TFs output the new contract: {updated, count, timeframe, source,
    bars:[{timestamp, open, high, low, close, volume, spread}]} where timestamp
    is an ISO datetime ("2026-10-29T14:15") in MT4 server time.
  - D1 keeps the legacy contract ({symbol, timeframe, start, end, count,
    bars:[{d,o,h,l,c,v}], indicators?}) so existing report pages keep working.
  - --format new|legacy|auto overrides (default auto = intraday new / D1 legacy).
  - --limit N keeps only the most recent N bars (controls M15 file size).
  - spread is read from the v401 record (offset 48, int32); 0 if absent.
  - manifest.json: legacy keys unchanged; intraday runs append tf-level entries.

Usage:
    python export_hst.py [--src DIR] [--out DIR] [--pairs EURUSD,XAUUSD,...]
                         [--tf 1440] [--limit N] [--format auto|new|legacy]
                         [--indicators] [--compact]

Defaults:
    --src   Auto-detect MT4 history directory (VantageInternational-Live 11)
    --out   ../docs/data/
    --tf    1440 (D1)
    --pairs All available pairs
"""

import struct, datetime, json, os, sys, argparse, glob

# MT4 .hst v401 record: 60 bytes
# time(4) + padding(4) + open(8) + high(8) + low(8) + close(8) + vol(8)
# + spread(4) + trailing(8)
RECORD_SIZE = 60
HEADER_SIZE = 148
SPREAD_OFFSET = 48

# Timeframe (minutes) -> label
TF_LABELS = {
    1: 'M1', 5: 'M5', 15: 'M15', 30: 'M30', 60: 'H1',
    240: 'H4', 1440: 'D1', 10080: 'W1', 43200: 'MN1',
}


def tf_label(minutes):
    """Map timeframe minutes to a label (60->H1, 15->M15, 1440->D1)."""
    return TF_LABELS.get(minutes, f'M{minutes}')


def find_mt4_history():
    """Auto-detect MT4 history directory."""
    base = "/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal"
    if not os.path.exists(base):
        return None

    for term in os.listdir(base):
        hist = os.path.join(base, term, "history")
        if not os.path.isdir(hist):
            continue
        for broker in os.listdir(hist):
            broker_path = os.path.join(hist, broker)
            if os.path.isdir(broker_path):
                # Check if it has .hst files
                hst_files = glob.glob(os.path.join(broker_path, "*.hst"))
                if hst_files:
                    return broker_path
    return None


def read_hst(filepath, intraday=False):
    """Read MT4 .hst v401 file, return list of OHLC bars.

    intraday=False (D1 legacy): bars carry 'd' = date string 'YYYY-MM-DD'.
    intraday=True: bars carry 'timestamp' = ISO datetime 'YYYY-MM-DDTHH:MM'
                   plus 'spread' from the v401 record.
    """
    bars = []
    file_size = os.path.getsize(filepath)
    n_bars = (file_size - HEADER_SIZE) // RECORD_SIZE

    if n_bars <= 0:
        return bars

    with open(filepath, 'rb') as f:
        # Skip header
        f.seek(HEADER_SIZE)

        for _ in range(n_bars):
            record = f.read(RECORD_SIZE)
            if len(record) < RECORD_SIZE:
                break

            time_val = struct.unpack('<i', record[0:4])[0]
            # bytes 4-7: padding/unknown (skip)
            open_val = struct.unpack('<d', record[8:16])[0]
            high_val = struct.unpack('<d', record[16:24])[0]
            low_val = struct.unpack('<d', record[24:32])[0]
            close_val = struct.unpack('<d', record[32:40])[0]
            vol = struct.unpack('<q', record[40:48])[0]
            spread = struct.unpack('<i', record[SPREAD_OFFSET:SPREAD_OFFSET + 4])[0]

            # Sanity check: skip zero-price bars
            if open_val == 0 and close_val == 0:
                continue

            dt = datetime.datetime.fromtimestamp(time_val)

            if intraday:
                bars.append({
                    'timestamp': dt.strftime('%Y-%m-%dT%H:%M'),
                    'open': round(open_val, 8),
                    'high': round(high_val, 8),
                    'low': round(low_val, 8),
                    'close': round(close_val, 8),
                    'volume': vol,
                    'spread': max(spread, 0)
                })
            else:
                bars.append({
                    'd': dt.strftime('%Y-%m-%d'),
                    'o': round(open_val, 8),
                    'h': round(high_val, 8),
                    'l': round(low_val, 8),
                    'c': round(close_val, 8),
                    'v': vol
                })

    return bars


def detect_pair_from_filename(filename):
    """Extract pair name from .hst filename."""
    # Examples: EURUSD1440.hst, XAUUSD.1440.hst, EURUSD15.hst, EURUSD.60.hst
    name = filename.replace('.hst', '')
    # Remove timeframe suffix (43200, 10080, 1440, 240, 60, 30, 15, 5, 1)
    # Longest first so '15' doesn't strip from '1440' etc.
    for tf in ['43200', '10080', '1440', '240', '60', '30', '15', '5', '1']:
        if name.endswith('.' + tf):
            return name[:-len(tf)-1]  # remove .TF
        if name.endswith(tf):
            return name[:-len(tf)]
    return name


def get_all_pairs(hist_dir, timeframe=1440):
    """Get all available pairs for a given timeframe."""
    pairs = {}
    tf_str = str(timeframe)

    for f in sorted(os.listdir(hist_dir)):
        if not f.endswith('.hst'):
            continue

        # Check if it matches the timeframe
        # Format: PAIR{TF}.hst or PAIR.{TF}.hst
        # Match on the dot-suffix first; for bare suffix require a non-digit
        # boundary so EURUSD15.hst doesn't also match tf=1 or tf=5.
        bare = f.endswith(tf_str + '.hst') and not f.endswith(tf_str + tf_str + '.hst')
        dotted = f.endswith('.' + tf_str + '.hst')
        if not (bare or dotted):
            continue
        # Guard: PAIR{TF}.hst bare match must not be the tail of a longer tf
        # (e.g. tf=5 matching 'EURUSD15.hst').
        if bare:
            stem = f[:-len('.hst')]
            prefix = stem[:-len(tf_str)]
            if prefix and prefix[-1].isdigit():
                continue

        pair = detect_pair_from_filename(f)
        filepath = os.path.join(hist_dir, f)
        file_size = os.path.getsize(filepath)
        n_bars = (file_size - HEADER_SIZE) // RECORD_SIZE

        pairs[pair] = {
            'file': f,
            'path': filepath,
            'bars': n_bars
        }

    return pairs


def export_pair(filepath, pair_name, timeframe=1440, fmt='auto', limit=None,
                src_dir=''):
    """Export a single pair to JSON payload dict."""
    intraday = (timeframe != 1440)
    fmt = fmt or 'auto'
    if fmt == 'legacy':
        intraday = False
    elif fmt == 'new':
        intraday = True

    bars = read_hst(filepath, intraday=intraday)
    if not bars:
        return None

    if limit and limit > 0 and len(bars) > limit:
        bars = bars[-limit:]

    label = tf_label(timeframe)

    if intraday:
        return {
            'updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': pair_name,
            'timeframe': label,
            'source': src_dir,
            'start': bars[0]['timestamp'],
            'end': bars[-1]['timestamp'],
            'count': len(bars),
            'bars': bars
        }
    return {
        'symbol': pair_name,
        'timeframe': 'D1' if timeframe == 1440 else label,
        'start': bars[0]['d'],
        'end': bars[-1]['d'],
        'count': len(bars),
        'bars': bars
    }


def calculate_technical_indicators(data):
    """Calculate SMA, EMA, RSI from OHLC data."""
    closes = [b['c'] for b in data['bars']]
    n = len(closes)

    indicators = {}

    # SMA 20, 50, 200
    for period in [20, 50, 200]:
        if n < period:
            continue
        sma = []
        for i in range(period - 1, n):
            val = sum(closes[i - period + 1:i + 1]) / period
            sma.append({'d': data['bars'][i]['d'], 'v': round(val, 8)})
        indicators[f'sma_{period}'] = sma

    # EMA 12, 26
    for period in [12, 26]:
        if n < period:
            continue
        multiplier = 2 / (period + 1)
        ema_val = sum(closes[:period]) / period
        ema = [{'d': data['bars'][period - 1]['d'], 'v': round(ema_val, 8)}]
        for i in range(period, n):
            ema_val = (closes[i] - ema_val) * multiplier + ema_val
            ema.append({'d': data['bars'][i]['d'], 'v': round(ema_val, 8)})
        indicators[f'ema_{period}'] = ema

    # RSI 14
    if n >= 15:
        gains, losses = [], []
        for i in range(1, min(15, n)):
            diff = closes[i] - closes[i - 1]
            gains.append(max(diff, 0))
            losses.append(max(-diff, 0))

        avg_gain = sum(gains) / 14
        avg_loss = sum(losses) / 14

        rsi = []
        if avg_loss == 0:
            rsi.append({'d': data['bars'][14]['d'], 'v': 100.0})
        else:
            rs = avg_gain / avg_loss
            rsi.append({'d': data['bars'][14]['d'], 'v': round(100 - 100 / (1 + rs), 2)})

        for i in range(15, n):
            diff = closes[i] - closes[i - 1]
            gain = max(diff, 0)
            loss = max(-diff, 0)
            avg_gain = (avg_gain * 13 + gain) / 14
            avg_loss = (avg_loss * 13 + loss) / 14
            if avg_loss == 0:
                rsi.append({'d': data['bars'][i]['d'], 'v': 100.0})
            else:
                rs = avg_gain / avg_loss
                rsi.append({'d': data['bars'][i]['d'], 'v': round(100 - 100 / (1 + rs), 2)})

        indicators['rsi_14'] = rsi

    # ATR 14
    if n >= 15:
        trs = []
        for i in range(1, n):
            h = data['bars'][i]['h']
            l = data['bars'][i]['l']
            pc = data['bars'][i - 1]['c']
            tr = max(h - l, abs(h - pc), abs(l - pc))
            trs.append(tr)

        atr_val = sum(trs[:14]) / 14
        atr = [{'d': data['bars'][14]['d'], 'v': round(atr_val, 8)}]
        for i in range(14, len(trs)):
            atr_val = (atr_val * 13 + trs[i]) / 14
            atr.append({'d': data['bars'][i + 1]['d'], 'v': round(atr_val, 8)})
        indicators['atr_14'] = atr

    # MACD (12, 26, 9)
    if n >= 35:
        # Calculate EMA 12 and EMA 26
        mult12 = 2 / 13
        mult26 = 2 / 27

        ema12 = sum(closes[:12]) / 12
        ema26 = sum(closes[:26]) / 26

        macd_line = []
        for i in range(26, n):
            ema12 = (closes[i] - ema12) * mult12 + ema12
            ema26 = (closes[i] - ema26) * mult26 + ema26
            macd_line.append({'d': data['bars'][i]['d'], 'v': round(ema12 - ema26, 8)})

        # Signal line (EMA 9 of MACD)
        if len(macd_line) >= 9:
            mult9 = 2 / 10
            signal_val = sum(m['v'] for m in macd_line[:9]) / 9
            macd_result = []
            for i in range(9, len(macd_line)):
                hist_val = macd_line[i - 1]['v'] - signal_val
                macd_result.append({
                    'd': macd_line[i]['d'],
                    'macd': macd_line[i]['v'],
                    'signal': round(signal_val, 8),
                    'histogram': round(hist_val, 8)
                })
                signal_val = (macd_line[i]['v'] - signal_val) * mult9 + signal_val

            indicators['macd'] = macd_result

    return indicators


def main():
    parser = argparse.ArgumentParser(description='Export MT4 .hst history to JSON')
    parser.add_argument('--src', help='MT4 history directory (auto-detect if omitted)')
    parser.add_argument('--out', default='../docs/data/', help='Output directory')
    parser.add_argument('--pairs', help='Comma-separated pairs (default: all)')
    parser.add_argument('--tf', type=int, default=1440,
                        help='Timeframe minutes: 1,5,15,30,60,240,1440 (default: 1440=D1)')
    parser.add_argument('--limit', type=int, default=None,
                        help='Keep only the most recent N bars (recommended for M15/M30)')
    parser.add_argument('--format', choices=['auto', 'new', 'legacy'], default='auto',
                        help='JSON contract: auto=intraday new/D1 legacy (default), '
                             'new={timestamp,open,...}, legacy={d,o,h,l,c,v}')
    parser.add_argument('--indicators', action='store_true', help='Include technical indicators (D1 legacy only)')
    parser.add_argument('--compact', action='store_true', help='Compact JSON (no indentation)')
    args = parser.parse_args()

    # Find source directory
    hist_dir = args.src
    if not hist_dir:
        hist_dir = find_mt4_history()
        if not hist_dir:
            print("❌ Cannot find MT4 history directory. Use --src to specify.")
            sys.exit(1)

    print(f"📂 MT4 History: {hist_dir}")

    # Get available pairs
    available = get_all_pairs(hist_dir, args.tf)
    if not available:
        print(f"❌ No .hst files found for timeframe {args.tf}")
        sys.exit(1)

    # Filter pairs
    target_pairs = None
    if args.pairs:
        target_pairs = set(p.strip().upper() for p in args.pairs.split(','))

    # Output directory
    out_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), args.out))
    os.makedirs(out_dir, exist_ok=True)

    # Export
    label = tf_label(args.tf)
    intraday = (args.tf != 1440)
    exported = 0
    skipped = 0
    manifest = []

    for pair, info in sorted(available.items()):
        if target_pairs and pair not in target_pairs:
            continue

        print(f"  📊 {pair}: {info['bars']} bars ... ", end='', flush=True)

        data = export_pair(info['path'], pair, args.tf, fmt=args.format,
                           limit=args.limit, src_dir=hist_dir)
        if not data:
            print("❌ (no data)")
            skipped += 1
            continue

        # Add indicators if requested (legacy D1 contract only)
        if args.indicators and not intraday and args.format != 'new':
            indicators = calculate_technical_indicators(data)
            if indicators:
                data['indicators'] = indicators

        # Write JSON
        out_file = os.path.join(out_dir, f"{pair}_{label}.json")

        with open(out_file, 'w') as f:
            if args.compact:
                json.dump(data, f, separators=(',', ':'))
            else:
                json.dump(data, f, indent=1)

        manifest.append({
            'symbol': pair,
            'tf': label,
            'start': data['start'],
            'end': data['end'],
            'bars': data['count'],
            'file': f"{pair}_{label}.json"
        })

        print(f"✅ {data['start']} → {data['end']} ({data['count']} bars)")
        exported += 1

    # Write manifest (per-TF file so runs of different TFs don't clobber
    # each other; legacy D1 manifest name kept for backwards compatibility)
    if intraday:
        manifest_file = os.path.join(out_dir, f'manifest_{label}.json')
    else:
        manifest_file = os.path.join(out_dir, 'manifest.json')

    manifest_payload = {
        'generated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'source': hist_dir,
        'timeframe': label,
        'pairs': manifest,
        'total_pairs': len(manifest),
        'total_bars': sum(m['bars'] for m in manifest)
    }
    if args.limit:
        manifest_payload['limit'] = args.limit

    with open(manifest_file, 'w') as f:
        json.dump(manifest_payload, f, indent=1)

    print(f"\n✅ Exported {exported} pairs, skipped {skipped} (TF={label}, format={args.format})")
    print(f"📁 Output: {out_dir}")
    print(f"📋 Manifest: {manifest_file}")


if __name__ == '__main__':
    main()
