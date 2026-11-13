#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
prep_ranking_data.py — TSA 排名雙頁資料前處理器（派工 v2 §2.1–2.5 規則實作，1815信§四修正）

輸入：data/tsa.db（dde_scores / batch_runs，經 db_manager 同一 schema）
輸出：docs/data/signal_ranking.json + docs/data/ccy_ranking.json（明文；加密由
      scripts/encrypt_ranking_json.mjs 另行處理，明文唔准入 git——.gitignore 已排）

規則（20261113_1150 派工v2 + 20261113_1815 驗收信§四修正）：
  §2.1 grain：signal_ranking＝150 signals（跨商品聚合）；ccy_ranking＝signal×symbol×方向（3370）
      DB 列係「EA實例列」：scorer Step1 按 (comment_prefix+magic) 分組，一實例一行，
      lv＝該實例摸過嘅層（'L1' 純單層／'L1+L2' 多層／'-' 無層），同一 triple 可多行。
      【唔做 lv 級 dedup、唔做 lv 過濾】——全部行按 (signal, symbol, type) triple 聚合。
  §2.2 EA 簡寫：Dragon Wave→DW 等映射＋版本號接尾（v2.10→2.1）＋'+' 串連；base token 供篩選；
      組內 EA 全名取最常見非 UNK（多實例聯合）
  §2.3 紅卡：全行 red_card==1 且 dde≤0 → 紅卡；原因四類中文標籤（全行聯集，id 序）；
      分數 0.0 唔入百分位
  §2.4 PF 哨兵：pf_raw=999＝無虧損單（全勝零逆向）；加權只用 0<pf_raw<100 嘅行；
      全組都冇非哨兵行＋有哨兵行 → pfINF=true（前端渲染 ∞）；哨兵＋實值並存 → 用實值（43024 型）
  §2.5 層級：手數＝各行 layers_json 逐層加總；某層有 lv 恰為該層名（L1/L2/…/L9+）嘅列
      → 用該列真值 WR/PF（多列則手數加權），冇 → null（前端顯示 —）；
      層序照 scorer 慣例 L1<L2<…<L9+（數字序，L9+ 掃尾）
  聚合（1815信§四）：t/pp 總和；dd/dde 最大；wr/ht 手數加權；dde 最大（唔係平均）
  過濾：symbol='profit'（AlgoForest 假 symbol）剔除；type mix 剔除（唔入 ccy grain）
  方向：type buy→'B'、sell→'S'

用法（VPS 05:30 鏈 / 手動）：
  python3 scripts/prep_ranking_data.py            # 由 repo root 行；自動 latest batch
  python3 scripts/prep_ranking_data.py --batch 20261113_053025
  python3 scripts/prep_ranking_data.py --out docs/data --db data/tsa.db

自檢：輸出後印 meta 摘要；--verify 對實測常數（3370/1831/1539/150/pf10/PF1.09）比對
      （真值驗收由有 data/tsa.db 嘅機器行——OpenClaw 側）。
"""
import argparse
import json
import re
import sys
import sqlite3
from collections import Counter, defaultdict
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
REASON_ZH_ORDER = ['樣本不足（<10 手）', '淨點數 ≤0', '勝率未達標', '單筆巨虧']

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


def weighted(pairs) -> float | None:
    """手數加權平均：[(value, weight), ...]；value None 剔除；weight 全 0 → 簡單平均；空 → None"""
    vals = [(float(v), float(w)) for v, w in pairs if v is not None]
    if not vals:
        return None
    tw = sum(w for _, w in vals)
    if tw > 0:
        return sum(v * w for v, w in vals) / tw
    return sum(v for v, _ in vals) / len(vals)


def layer_sort_key(ln: str):
    """L1<L2<…<L9<L9+（照 scorer 慣例：L9+／非數字尾掃尾）"""
    n = ln[1:] if ln[:1] in ('L', 'l') else ln
    return (99 if n == '9+' or not n.isdigit() else int(n), ln)


def parse_json(s, default):
    try:
        v = json.loads(s) if s else default
    except Exception:
        return default
    return v if isinstance(v, type(default)) else default


def load_batch(db_path: Path, batch: str | None) -> tuple[str, list]:
    """讀 tsa.db：latest v5 batch → 全部列（profit 過濾前）。回 (batch_id, rows)"""
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


def prep(rows_raw: list, batch: str) -> tuple[dict, dict, dict]:
    """① profit 假 symbol／mix 剔除；② 按 (signal, symbol, type) triple 分組全行聚合（1815信§四）"""
    rows_raw = sorted(rows_raw, key=lambda r: r['id'])   # 穩定序：id 升序
    groups = defaultdict(list)
    dropped_profit = 0
    for r in rows_raw:
        if (r['symbol'] or '').strip().lower() == 'profit':
            dropped_profit += 1
            continue
        typ = (r['type'] or '').strip().lower()
        if typ not in ('buy', 'sell'):
            continue                     # mix 不入 ccy grain
        groups[(r['signal_id'], r['symbol'], typ)].append(r)

    # ③ ccy_ranking rows（grain＝signal×symbol×方向；一行＝一 EA 實例，全行聚合）
    crows = []
    for (sid, sym, typ), rs in groups.items():
        # §四聚合：t/pp 總和；dd/dde 最大；wr/ht 手數加權
        t = sum(int(r[T] or 0) for r in rs)
        pp = sum(float(r[PP] or 0) for r in rs)
        dd = max(float(r[DD] or 0) for r in rs)
        wr = weighted([(r[WR], int(r[T] or 0)) for r in rs])
        ht = weighted([(r[HT], int(r[T] or 0)) for r in rs])
        # PF：加權只用 0<pf_raw<100（哨兵排除）；全組冇實值＋有哨兵 → pfINF
        ok = [(float(r['pf_raw']), int(r[T] or 0)) for r in rs
              if r['pf_raw'] is not None and 0 < float(r['pf_raw']) < 100]
        pf = weighted(ok)
        pf_inf = pf is None and any(float(r['pf_raw'] or 0) >= 100 for r in rs)
        dde = max(float(r[DDE] or 0) for r in rs)
        red = all(int(r['red_card'] or 0) == 1 for r in rs) and dde <= 0   # 全行紅卡
        # EA：最常見非 UNK 全名（多實例聯合）
        cnt = Counter((r['ea'] or '').strip() for r in rs
                      if (r['ea'] or '').strip() and (r['ea'] or '').strip().upper() != 'UNK')
        ea_full = cnt.most_common(1)[0][0] if cnt else 'UNK'
        short = ea_short(ea_full)
        # 紅卡原因：全行聯集（id 序）
        reasons = []
        if red:
            raw = []
            for r in rs:
                raw += [str(x) for x in parse_json(r.get('red_reasons'), [])]
            reasons = zh_reasons(raw)
        # §2.5 lv 陣列：手數＝各行 layers_json 逐層加總；
        # 某層有 lv 恰為該層名（L1/…/L9+）嘅列 → 該層 WR/PF 真值（多列手數加權），冇 → null
        hands = defaultdict(int)
        for r in rs:
            for ln, n in parse_json(r.get('layers_json'), {}).items():
                hands[str(ln)] += int(n or 0)
        lv_arr = []
        for ln in sorted(hands, key=layer_sort_key):
            lrs = [r for r in rs if (r['lv'] or '').strip() == ln]
            lwr = weighted([(r[WR], int(r[T] or 0)) for r in lrs]) if lrs else None
            lok = [(float(r['pf_raw']), int(r[T] or 0)) for r in lrs
                   if r['pf_raw'] is not None and 0 < float(r['pf_raw']) < 100]
            lpf = weighted(lok) if lok else None
            lv_arr.append([ln, hands[ln],
                           round(lwr, 1) if lwr is not None else None,
                           round(lpf, 2) if lpf is not None else None])
        rc = 1 if red else 0
        crows.append({
            's': sid, 'p': sym, 'd': 'B' if typ == 'buy' else 'S',
            'e': short, 'ea': ea_base(short), 'E': ea_full,
            'eaN': len(short.split('+')),
            'dde': round(dde, 1) if not rc else 0.0,
            't': t, 'wr': round(wr, 1) if wr is not None else 0.0,
            'pf': None if (pf_inf or pf is None) else round(pf, 2),
            'pfINF': bool(pf_inf),
            'pp': round(pp, 1), 'dd': round(dd, 1),
            'ht': round(ht, 1) if ht is not None else 0.0,
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
            'rr': sorted({z for c in reds for z in c['rr']}, key=REASON_ZH_ORDER.index),
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
            {'dropped_profit': dropped_profit,
             'multi_row_groups': sum(1 for rs in groups.values() if len(rs) > 1)})


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument('--db', default=str(REPO / 'data' / 'tsa.db'))
    ap.add_argument('--out', default=str(REPO / 'docs' / 'data'))
    ap.add_argument('--batch', default=None)
    ap.add_argument('--verify', action='store_true',
                   help='對派工v2實測常數驗收（3370/1831/1539/150/pf10/PF1.09）——真值由有 DB 嘅機器跑出')
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
    print(f"   profit 假 symbol 剔除 {stat['dropped_profit']} 列；"
          f"多行 triple（EA實例聯合）{stat['multi_row_groups']} 組加權聚合")
    print(f"   輸出：{out_dir}/signal_ranking.json（{len(sig_j['rows'])} rows）"
          f" + {out_dir}/ccy_ranking.json（{len(ccy_j['rows'])} rows）——明文，緊接跑 encrypt_ranking_json.mjs，唔准就咁 commit")

    if args.verify:
        checks = [('combos==3370', m['combos'] == 3370), ('scored==1831', m['scored'] == 1831),
                  ('red==1539', m['red'] == 1539), ('signals==150', m['signals'] == 150),
                  ('pf_fixed==10', m['pf_fixed'] == 10)]
        tgt = next((c for c in ccy_j['rows'] if c['s'] == '43024' and c['p'] == 'AUDCAD' and c['d'] == 'S'), None)
        checks.append(('43024 AUDCAD S PF==1.09', bool(tgt and tgt['pf'] == 1.09)))
        bad = [n for n, okk in checks if not okk]
        print('   驗收：' + (' '.join(n for n, okk in checks if okk) if not bad else f'❌ 未中：{bad}'))
        sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
