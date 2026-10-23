#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
forex_data_freshness.py — 數據新鮮度檢查 v3（雙 lane 版）
2026-10-23 phase 2 改造（項 7，老闆修訂版）：
  Lane A — MT5 自家 EA（725B GoldSupporter）：
      gold_tick.csv 90min（每分鐘產出）／forex_data.csv 150min（每小時產出）
  Lane B — MT4 第三方 CCY Power（F1BBCAA*）：
      forex_data.csv 180min（暫定閾值；F1B 10-23 18:17 復活，穩定性驗證中，驗證後可收緊）
  - 老闆裁定：A06E 唔做優先源（仍死）；報告數據一律 MT4/MT5 本地源，嚴禁 yfinance
  - 兩 lane 獨立判定獨立報告：MT5 綠燈唔代表 CCY lane 存活
  - 用法：python3 forex_data_freshness.py --lane mt5   （cron 標籤 freshness）
          python3 forex_data_freshness.py --lane ccy   （cron 標籤 freshness_ccy）
  - 豁免（唔檢查直接 exit 0）：週六/週日全日、週一 08:00 前、每日 05:00–07:59
    （紐約收市維護，夏令 05:00–06:00／冬令 06:00–07:00 都覆蓋；外匯市場同窗口適用兩 lane）
  - 退出碼：0=新鮮/豁免；1=過期/缺失/目錄異常；2=參數錯誤
"""
import os, sys, glob, argparse
from datetime import datetime

LANES = {
    'mt5': {
        'dir': ['/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/725B*/MQL5/Files'],
        'checks': [('gold_tick.csv', 90), ('forex_data.csv', 150)],
    },
    'ccy': {
        'dir': ['/mnt/c/Users/Alvin/AppData/Roaming/MetaQuotes/Terminal/F1BBCAA*/MQL4/Files'],
        'checks': [('forex_data.csv', 180)],
    },
}


def resolve_dir(patterns):
    override = os.environ.get('FRESHNESS_DIR_OVERRIDE')
    if override:
        return override
    for p in patterns:
        hits = sorted(glob.glob(p))
        if hits:
            return hits[0]
    return None


def market_closed(now):
    wd = now.weekday()                       # Mon=0 ... Sun=6
    if wd in (5, 6):
        return True                          # 週六/週日全日
    if wd == 0 and now.hour < 8:
        return True                          # 週一 08:00 前（開市銜接緩衝）
    if 5 <= now.hour < 8:
        return True                          # 每日維護 05:00–07:59
    return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lane', choices=['mt5', 'ccy'], default='mt5')
    args = parser.parse_args()
    cfg = LANES[args.lane]
    now = datetime.now()
    stamp = now.strftime('%Y-%m-%d %H:%M:%S')
    if market_closed(now):
        print(f"[{stamp}] freshness({args.lane}): 休市豁免（週末/維護時段），skip")
        return 0
    d = resolve_dir(cfg['dir'])
    if not d or not os.path.isdir(d):
        print(f"[{stamp}] freshness({args.lane}): ❌ 目錄搵唔到（{cfg['dir'][0]}）")
        return 1
    bad, ok = [], []
    for name, threshold in cfg['checks']:
        path = os.path.join(d, name)
        if not os.path.isfile(path):
            bad.append(name)
            print(f"[{stamp}] freshness({args.lane}): ❌ {name} 缺失（{path}）")
            continue
        age = (now.timestamp() - os.path.getmtime(path)) / 60.0
        last = datetime.fromtimestamp(os.path.getmtime(path)).strftime('%m-%d %H:%M')
        if age > threshold:
            bad.append(name)
            print(f"[{stamp}] freshness({args.lane}): ❌ {name} 過期 {age:.0f}min（閾值 {threshold}min），最後更新 {last}")
        else:
            ok.append(name)
            print(f"[{stamp}] freshness({args.lane}): ✅ {name} 新鮮（{age:.0f}min 前，{last}）")
    if bad:
        print(f"[{stamp}] freshness({args.lane}): 異常 {len(bad)} 檔：{','.join(bad)}")
        return 1
    print(f"[{stamp}] freshness({args.lane}): 全部 {len(ok)} 檔新鮮")
    return 0


if __name__ == '__main__':
    sys.exit(main())
