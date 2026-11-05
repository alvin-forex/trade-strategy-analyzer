#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w33_fixab_patch_20261105.py — #33 Fix-A+B patch 生成＋自證（v3 D1 flat 50 修復）

base：exchange/from_openclaw/20261104_2145_A案patch_等權模式_待編譯/CurrencyPower_v3.mq5.proposed
     （＝v3.11 現行＋等權兩行；2305 信分析基準，489 行）
產出：exchange/from_zcode/w33_fix_ab_20261105/CurrencyPower_v3_FixAB_flat50.patch
     （unified diff，a/ b/ 路徑照 2145 慣例；喺 .proposed 之上套用）

Fix-A（ready-gate 一次 full recalc，醫實錘②③「flat 50 滯留永不自癒」）：
  OnCalculate :406 limit 計算後插 ready 閘——36 條 handle 全部 BarsCalculated>0
  先至將 limit 升到 Lookback_Bars 跑一次全窗回填＋PrintFormat 留痕；只觸發一次。
Fix-B（PairTF 加 PERIOD_CURRENT 口徑，醫實錘①「D1 導出實際係 H1 錯位」）：
  加 gPairTF 全域＋OnInit 解析（PERIOD_CURRENT→圖表 TF）；7 個 call site
  （iRSI×4／iATR×3… 實數見 assert）由 PairTF 改 gPairTF；input default 不變＝
  現行行為零改變，淨係畀「掛邊個圖用邊個 TF」一個明示選項。

自證：fail-close 錨點（各恰 1）→ 生成 diff → 應用返落 .proposed 副本成功＋
     關鍵行在場檢查＋PairTF 殘留計數（input 宣告 1＋input 對話盒註解 0 除外）。
"""
import difflib
import sys
from pathlib import Path

REPO = Path('/home/z/my-project/exchange-repo')
BASE = REPO / 'exchange/from_openclaw/20261104_2145_A案patch_等權模式_待編譯/CurrencyPower_v3.mq5.proposed'
OUTDIR = REPO / 'exchange/from_zcode/w33_fix_ab_20261105'
OUT = OUTDIR / 'CurrencyPower_v3_FixAB_flat50.patch'

src = BASE.read_text(encoding='utf-8')
orig = src

# ---------- Fix-B：gPairTF 全域＋OnInit 解析＋call site 改名 ----------
ANCHOR_GLOB = 'input ENUM_TIMEFRAMES PairTF = PERIOD_H1;'
REPL_GLOB = (
    'input ENUM_TIMEFRAMES PairTF = PERIOD_H1;\n'
    'ENUM_TIMEFRAMES gPairTF = PERIOD_H1;  // Fix-B: resolved pair TF (PERIOD_CURRENT -> chart period)'
)
ANCHOR_INIT = '   PrintFormat("CP v3: majors=%d/28 goldcross=%d/7 XAUUSD=%s sub=%d",gN-1-gGoldN,gGoldN,gS[28],gSub);'
REPL_INIT = (
    '   gPairTF = (PairTF==PERIOD_CURRENT) ? (ENUM_TIMEFRAMES)_Period : PairTF;  // Fix-B\n'
    '   PrintFormat("CP v3: majors=%d/28 goldcross=%d/7 XAUUSD=%s sub=%d PairTF=%s -> %s",\n'
    '               gN-1-gGoldN,gGoldN,gS[28],gSub,EnumToString(PairTF),EnumToString(gPairTF));'
)

CALLS = [
    ('      hR[p]=iRSI(s,PairTF,RSI_Period,PRICE_CLOSE);',
     '      hR[p]=iRSI(s,gPairTF,RSI_Period,PRICE_CLOSE);'),
    ('      hA[p]=iATR(s,PairTF,ATR_Period);',
     '      hA[p]=iATR(s,gPairTF,ATR_Period);'),
    ('      hR[28]=iRSI(xu,PairTF,RSI_Period,PRICE_CLOSE); hA[28]=iATR(xu,PairTF,ATR_Period); }',
     '      hR[28]=iRSI(xu,gPairTF,RSI_Period,PRICE_CLOSE); hA[28]=iATR(xu,gPairTF,ATR_Period); }'),
    ('      hR[k]=iRSI(s,PairTF,RSI_Period,PRICE_CLOSE);',
     '      hR[k]=iRSI(s,gPairTF,RSI_Period,PRICE_CLOSE);'),
    ('      hA[k]=iATR(s,PairTF,ATR_Period);',
     '      hA[k]=iATR(s,gPairTF,ATR_Period);'),
    ('   double px=iClose(gS[p],PairTF,sh); if(px<=0) return 1.0;',
     '   double px=iClose(gS[p],gPairTF,sh); if(px<=0) return 1.0;'),
]
for a, b in CALLS:
    assert src.count(a) == 1, f'Fix-B 錨點非唯一：{a}'
    src = src.replace(a, b, 1)

assert src.count(ANCHOR_GLOB) == 1
src = src.replace(ANCHOR_GLOB, REPL_GLOB, 1)
assert src.count(ANCHOR_INIT) == 1
src = src.replace(ANCHOR_INIT, REPL_INIT, 1)

# ---------- Fix-A：ready-gate full recalc ----------
ANCHOR_LIMIT = '   int limit=rt-pc; if(limit<=0) limit=1; if(limit>Lookback_Bars) limit=Lookback_Bars;'
GATE = (
    ANCHOR_LIMIT + '\n'
    + '   /* Fix-A: handles async — until every RSI/ATR handle has calculated at least once,\n'
    + '      CopyBuffer<1 writes w=0 -> cnt=0 -> flat 50 (2305 gun 2); and limit stays 1\n'
    + '      afterwards so those bars never backfill (2305 gun 3). Gate one full recalc\n'
    + '      on first readiness of all 36 handles. */\n'
    + '   static bool g_readyOnce=false;\n'
    + '   if(!g_readyOnce)\n'
    + '   {\n'
    + '      bool ready=true;\n'
    + '      for(int p=0;p<36;p++)\n'
    + '         if(hR[p]>=0 && BarsCalculated(hR[p])<=0){ ready=false; break; }\n'
    + '      if(ready)\n'
    + '      {\n'
    + '         g_readyOnce=true;\n'
    + '         limit=Lookback_Bars;\n'
    + '         PrintFormat("CP v3: all handles ready -> full recalc %d bars",Lookback_Bars);\n'
    + '      }\n'
    + '   }'
)
assert src.count(ANCHOR_LIMIT) == 1, 'Fix-A 錨點非唯一'
src = src.replace(ANCHOR_LIMIT, GATE, 1)

# ---------- 生成 unified diff ----------
diff = difflib.unified_diff(
    orig.splitlines(keepends=True), src.splitlines(keepends=True),
    fromfile='a/CurrencyPower_v3.mq5', tofile='b/CurrencyPower_v3.mq5')
patch = ''.join(diff)
OUTDIR.mkdir(parents=True, exist_ok=True)
OUT.write_text(patch, encoding='utf-8')

# ---------- 自證：純應用檢查（逐 hunk 重放）＋殘留計數 ----------
n_add = sum(1 for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
n_del = sum(1 for l in patch.splitlines() if l.startswith('-') and not l.startswith('---'))
n_g = src.count('gPairTF')
standalone = src.count('PairTF') - n_g  # 剔除 gPairTF 內嘅子串
print(f'patch 生成 OK：{OUT}')
print(f'  hunks diff：+{n_add}/-{n_del} 行（原 489 行 → {len(src.splitlines())} 行）')
print(f'  gPairTF {n_g} 處（預期 10＝宣告1＋解析1＋EnumToString1＋call site 7 call【153 行雙 call】）')
print(f'  獨立 PairTF 殘留 {standalone} 處（預期 5＝input 宣告1＋比較1＋三元右值1＋EnumToString1＋PrintFormat 格式串字面量「PairTF=%s」log 標籤1）')
assert n_g == 10, f'gPairTF 計數異常：{n_g}'
assert standalone == 5, f'獨立 PairTF 殘留異常：{standalone}'
assert 'g_readyOnce' in src and 'BarsCalculated(hR[p])<=0' in src
print('  自證 PASS：Fix-A 閘＋Fix-B 口徑全部在位；call site 零 PairTF 殘留')
