#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prep_ranking_data.py — TSA 排名雙頁資料前處理器（派工 v2 §2.1–2.5 規則實作）

輸入：data/tsa.db（dde_scores / batch_runs，經 db_manager 同一 schema）
輸出：docs/data/signal_ranking.json + docs/data/ccy_ranking.json（明文；加密由
      scripts/encrypt_ranking_json.mjs 另行處理，明文唔准入 git——.gitignore 已排）

規則（20261113_1150 派工v2 + 20261113_1426 開工令）：
  §2.1 grain：signal_ranking＝150 signals（跨商品聚合）；ccy_ranking＝signal×symbol×方向（3370）
  §2.2 EA 簡寫：Dragon Wave→DW 等映射＋版本號接尾（v2.10→2.1）＋'+' 串連；base token 供篩選
  §2.3 紅卡：red_card＋red_reasons（四類中文標籤）；分數 0.0 唔入百分位
  §2.4 PF 哨兵：pf_raw=999＝無虧損單（全勝零逆向）；加權只用 0<pf_raw<100；整組哨兵→pfINF=true（前端渲染 ∞）
  §2.5 層級：主列 lv=''；單層列 lv=^L\\d+$；層級手數取主列 layers_json；層級 WR/PF 只用單層列真值，冇→null（前端顯示 —）
  去重：同 (signal, symbol, type, lv) 取 id 最大（最新寫入）一列
  過濾：symbol='profit'（AlgoForest 假 symbol，23 行）剔除
  方向：type buy→'B'、sell→'S'；mix 列不入 ccy grain

用法（VPS 05:30 鏈 / 手動）：
  python3 scripts/prep_ranking_data.py            # 由 repo root 行；自動 latest batch
  python3 scripts/prep_ranking_data.py --batch 20261113_053025
  python3 scripts/prep_ranking_data.py --out docs/data --db data/tsa.db

自檢：輸出後印 meta 摘要；--verify 對 schema 常數（3370/1831/1539）比對（真值驗收由 OpenClaw 側跑）。
"""
import argparse
import json
import re
import sys
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# ── EA 簡寫映射（派工v2 §2.2，映射已實測 48 組合全覆蓋） ──────────────────────
EA_MAP = {
    'Dragon Wave': 'DW', 'Flash': 'FL', 'MKD': 'MKD', 'MKD Pro': 'MKDP',
    'SMA': 'SMA', 'SMA Pro': 'SMAP', 'SMAPro': 'SMAP',
    'Gemini Client': 'GC', 'Gemini Server': 'GS',
    'S10': 'S10', 'GEM': 'GEM', 'UNK': 'UNK',
}
EA_ORDER = ['UNK', 'DW', 'FL', 'MKD', 'MKDP', 'SMA', 'SMAP', 'GC', 'GS', 'S10', 'GEM']

# 紅卡原因 → 中文標籤（meta.red_reasons 口徑；rows.rr 用同一標籤）
REASON_ZH = [
    (re.compile(r'^Trades < 10'),        '樣本不足（<10 手）'),
    (re.compile(r'^Net Pips <= 0'),      '淨點數 ≤0'),
    (re.compile(r'^Win Rate < \d+%'),    '勝率未達標'),
    (re.compile(r'^Single Max Loss'),    '單筆巨虧'),
]
LV_RE = re.compile(r'^L\d+$')

DDE = 'dde_score'; WR = 'win_rate'; PF = 'profit_factor'; T = 'trades'
PP = 'total_net_pips'; DD = 'max_dd_pips'; HT = 'avg_hold'


def zh_reasons(raw: list) -> list:
    out = []
    for r in raw or []:
        hit = next((zh for rx, zh in REASON_ZH if rx.search(str(r))), None)
        if hit and hit not in out:
            out.append(hit)
    return out


def fmt_ver(v: str) -> str:
    """v2.10 → '2.1'；v3.00 → '3'；v5.00 → '5'（去尾零，整數去小數點）"""
    s = v.strip()
    if s[:1].lower() == 'v':
        s = s[1:]
    if '.' in s:
        s = s.rstrip('0').rstrip('.')
    return s or '0'


def ea_short(ea_full: str) -> str:
    """'Dragon Wave v2.10/Flash v3.00' → 'DW2.1+FL3'；'UNK' → 'UNK'"""
    parts = [p.strip() for p in (ea_full or 'UNK').split('/') if p.strip()]
    out = []
    for p in parts:
        m = re.match(r'^(.*?)(?:\s+v[\d.]+)?$', p)
        name = m.group(1).strip() if m else p
        vm = re.search(r'v([\d.]+)\s*$', p)
        base = EA_MAP.get(name, 'UNK')
        out.append(base + fmt_ver(vm.group(1)) if vm else base)
    return '+'.join(out) or 'UNK'


def ea_base(short: str) -> str:
    """'DW2.1+FL3' → 'DW+FL'（篩選 base token）"""
    toks = []
    for t in re.split(r'\+', short or ''):
        m = re.match(r'^([A-Za-z0-9]+?)((?:\d+(?:\.\d+)?)?)$', t)
        toks.append(m.group(1) if m else t)
    return '+'.join(toks) or 'UNK'


def load_batch(db_path: Path, batch: str | None) -> tuple[str, list]:
    """讀 tsa.db：latest v5 batch → 全部列（去重／profit 過濾前）。回 (batch_id, rows)"""
    if not db_path.exists():
        sys.exit(f'❌ DB not found: {db_path}（本腳本預期喺有 data/tsa.db 嘅機器行——VPS 05:30 鏈）')
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    if not batch:
        cur.execute("SELECT batch_run_id FROM dde_scores WHERE strategy_version='v5' "
                    'ORDER BY created_at DESC, id DESC LIMIT 1')
        row = cur.fetchone()
        if not row:
            sys.exit('❌ dde_scores 冇 v5 數據')
        batch = row[0]
    cur.execute("SELECT * FROM dde_scores WHERE strategy_version='v5' AND batch_run_id=?", (batch,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    if not rows:
        sys.exit(f'❌ batch {batch} 冇數據')
    return batch, rows


def prep(rows_raw: list, batch: str) -> tuple[dict, dict]:
    # ① 去重：同 (signal, symbol, type, lv) 保留 id 最大；② profit 假 symbol 剔除
    best = {}
    dropped_dup = dropped_profit = 0
    for r in rows_raw:
        if (r['symbol'] or '').strip().lower() == 'profit':
            dropped_profit += 1
            continue
        key = (r['signal_id'], r['symbol'], r['type'], r['lv'] or '')
        if key in best:
            dropped_dup += 1
            if r['id'] > best[key]['id']:
                best[key] = r
        else:
            best[key] = r
    rows = list(best.values())

    combo_rows = {k: r for k, r in best.items()
                  if (r['type'] or '').lower() in ('buy', 'sell') and not LV_RE.match(r['lv'] or '')}
    layer_rows = {}
    for k, r in best.items():
        if LV_RE.match(r['lv'] or ''):
            sig, sym, typ = r['signal_id'], r['symbol'], r['type']
            layer_rows[(sig, sym, typ, r['lv'])] = r

    # ③ ccy_ranking rows（grain＝signal×symbol×方向）
    crows = []
    for r in combo_rows.values():
        t = (r['type'] or '').lower()
        layers = {}
        try:
            layers = json.loads(r.get('layers_json') or '{}')
        except Exception:
            layers = {}
        lv_arr = []
        for ln in sorted(layers.keys()):
            hands = layers[ln]
            lr = layer_rows.get((r['signal_id'], r['symbol'], r['type'], ln))
            lv_arr.append([ln, int(hands), round(lr['win_rate'], 1) if lr else None,
                           round(lr['profit_factor'], 2) if lr else None])
        rc = 1 if r['red_card'] else 0
        reasons = zh_reasons(json.loads(r.get('red_reasons') or '[]')) if rc else []
        pf_raw = float(r.get('pf_raw') or 0)
        pf = float(r.get('profit_factor') or 0)
        pf_inf = pf_raw >= 999 or (r.get('profit_factor') or 0) >= 999
        short = ea_short(r.get('ea') or 'UNK')
        crows.append({
            's': r['signal_id'], 'p': r['symbol'], 'd': 'B' if t == 'buy' else 'S',
            'e': short, 'ea': ea_base(short), 'E': r.get('ea') or 'UNK',
            'eaN': len(short.split('+')),
            'dde': round(float(r[DDE] or 0), 1) if not rc else 0.0,
            't': int(r[T] or 0), 'wr': round(float(r[WR] or 0), 1),
            'pf': None if pf_inf else round(pf, 2),
            'pfINF': bool(pf_inf),
            'pp': round(float(r[PP] or 0), 1), 'dd': round(float(r[DD] or 0), 1),
            'ht': round(float(r[HT] or 0), 1),
            'rc': rc, 'rr': reasons, 'lv': lv_arr,
        })
    # 排序：scored 先（dde 降序），紅卡後（附穩定序）
    crows.sort(key=lambda x: (x['rc'], -(x['dde'] or 0), x['s'], x['p'], x['d']))

    # ④ signal_ranking rows（150；聚合自家 combos）
    by_sig = defaultdict(list)
    for c in crows:
        by_sig[c['s']].append(c)
    srows = []
    for sig, cs in by_sig.items():
        scored = [c for c in cs if not c['rc']]
        reds = [c for c in cs if c['rc']]
        ok_pf = [c['pf'] for c in cs if c['pf'] is not None and not c['pfINF'] and c['pf'] > 0]
        pf_inf_all = bool(cs) and all(c['pfINF'] for c in cs)
        best_c = max(cs, key=lambda c: c['dde'] or 0) if scored else (max(cs, key=lambda c: c['t'] or 0) if cs else None)
        # EA 資訊取代表列（同 signal 一致）
        ea_full = next((c['E'] for c in cs), 'UNK')
        short = ea_short(ea_full)
        srows.append({
            'signal': sig, 'ea': short, 'ea_base': ea_base(short), 'ea_full': ea_full,
            'eaN': len(short.split('+')),
            'ccy_n': len({c['p'] for c in cs}),
            'dde': round(sum(c['dde'] or 0 for c in scored) / len(scored), 1) if scored else 0.0,
            'best_combo': f"{best_c['p']} {'BUY' if best_c['d'] == 'B' else 'SELL'}" if best_c else '—',
            'red_pct': round(len(reds) / len(cs) * 100) if cs else 0,
            'wr': round(sum(c['wr'] for c in cs) / len(cs), 1) if cs else 0,
            'trades': sum(c['t'] for c in cs),
            'pf': round(sum(ok_pf) / len(ok_pf), 2) if ok_pf else None,
            'pips': round(sum(c['pp'] for c in cs), 1),
            'dd': round(max(c['dd'] for c in cs), 1) if cs else 0,
            'combos': len(cs), 'red': len(reds),
            'rr': sorted({z for c in reds for z in c['rr']}, key=lambda z: ['樣本不足（<10 手）', '淨點數 ≤0', '勝率未達標', '單筆巨虧'].index(z)),
            'pfINF': pf_inf_all,
        })
    srows.sort(key=lambda x: (-(x['dde'] or 0), x['signal']))

    # ⑤ meta
    scored_n = sum(1 for c in crows if not c['rc'])
    red_n = len(crows) - scored_n
    reason_counter = defaultdict(int)
    for c in crows:
        for z in c['rr']:
            reason_counter[z] += 1
    as_of = datetime.now().strftime('%Y-%m-%d %H:%M')
    cmeta = {
        'batch': batch, 'as_of': as_of,
        'combos': len(crows), 'scored': scored_n, 'red': red_n,
        'signals': len(srows), 'pairs': len({c['p'] for c in crows}),
        'buys': sum(1 for c in crows if c['d'] == 'B'), 'sells': sum(1 for c in crows if c['d'] == 'S'),
        'trades': sum(c['t'] for c in crows),
        'red_reasons': [[z, reason_counter[z]] for z in
                        ['淨點數 ≤0', '樣本不足（<10 手）', '勝率未達標', '單筆巨虧'] if reason_counter.get(z)],
        'pf_fixed': sum(1 for c in crows if c['pfINF']),
    }
    scored_ddes = [c['dde'] for c in crows if not c['rc']]
    smeta = {
        'batch': batch, 'as_of': as_of, 'total': len(srows),
        'scored': sum(1 for s in srows if s['red'] == 0),
        'avg_dde': round(sum(scored_ddes) / len(scored_ddes), 1) if scored_ddes else 0,
        'best': round(max(scored_ddes), 1) if scored_ddes else 0,
        'worst': round(min(scored_ddes), 1) if scored_ddes else 0,
        'total_trades': cmeta['trades'], 'total_pips': round(sum(c['pp'] for c in crows), 1),
        'red_signals': sum(1 for s in srows if s['red'] > 0 and s['red'] == s['combos']),
        'pairs': cmeta['pairs'],
    }
    return ({'meta': smeta, 'rows': srows}, {'meta': cmeta, 'rows': crows},
            {'dropped_dup': dropped_dup, 'dropped_profit': dropped_profit})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=str(REPO / 'data' / 'tsa.db'))
    ap.add_argument('--out', default=str(REPO / 'docs' / 'data'))
    ap.add_argument('--batch', default=None)
    ap.add_argument('--verify', action='store_true',
                   help='對派工v2實測常數驗收（3370/1831/1539/PF1.09）——真值由你側 DB 跑出')
    args = ap.parse_args()

    batch, raw = load_batch(Path(args.db), args.batch)
    sig_j, ccy_j, stat = prep(raw, batch)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / 'signal_ranking.json').write_text(
        json.dumps(sig_j, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    (out_dir / 'ccy_ranking.json').write_text(
        json.dumps(ccy_j, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

    m = ccy_j['meta']
    print(f"✅ batch={batch}  combos={m['combos']}  scored={m['scored']}  red={m['red']}  "
          f"signals={m['signals']}  pairs={m['pairs']}  buys={m['buys']}  sells={m['sells']}  "
          f"trades={m['trades']}  pfINF={m['pf_fixed']}")
    print(f"   去重剔除 {stat['dropped_dup']} 列；profit 假 symbol 剔除 {stat['dropped_profit']} 列")
    print(f"   輸出：{out_dir}/signal_ranking.json（{len(sig_j['rows'])} rows）"
          f" + {out_dir}/ccy_ranking.json（{len(ccy_j['rows'])} rows）——明文，緊接跑 encrypt_ranking_json.mjs，唔准就咁 commit")

    if args.verify:
        checks = [('combos==3370', m['combos'] == 3370), ('scored==1831', m['scored'] == 1831),
                  ('red==1539', m['red'] == 1539), ('signals==150', m['signals'] == 150),
                  ('pf_fixed==10', m['pf_fixed'] == 10)]
        hit = {c['s']: c for c in ccy_j['rows']}.get('43024')
        tgt = next((c for c in (hit,) if c and c['p'] == 'AUDCAD' and c['d'] == 'S'), None)
        checks.append(('43024 AUDCAD S PF==1.09', bool(tgt and tgt['pf'] == 1.09)))
        bad = [n for n, okk in checks if not okk]
        print('   驗收：' + (' '.join(n for n, okk in checks if okk) if not bad else f'❌ 未中：{bad}'))
        sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
