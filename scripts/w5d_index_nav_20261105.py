#!/usr/bin/env python3
"""w5d_index_nav_20261105.py — W5-D（index_* 154 頁）：NAV 注入＋:root canonical remap（Q1(a) 裁決）

派工鏈：0700 總派工單 W5 → 0836 Q1 裁決(a)（index_* 四件注入含 sidebar.js，
零 JS 純度讓位全站導航統一）→ 0913 回批「W5 剩餘照排：index_* 151 → …」。

人口普查（2026-11-05 10:10，154/154 覆蓋）：
  - 151 頁 Template A v2 暗殼族（rebuild_index_deep_v2.py 5373a0b 產物）：
    :root 區塊 151/151 byte 一致（md5 5ab054fb）——整塊精準替換零誤傷。
    殼 token 舊值（#0a0e17/#111520/#1a1f2e/:root 內/#151b28/#1e2433/#d0d0d0/#777）
    :root 外出現數＝0 → 替換後全站殼殘留歸零。
  - 3 頁 light var 族（index_36512/36655/5117，c9e7e18「reports index 187 重建」遺留，
    root index.html 模板 :root --primary:#0f3460/--bg:#f5f7fa）——照 W5-C v3.9 先例：
    三件注入（css＋container＋js），tokens 豁免（dark default 下會接管 var 翻黑破版）。

做法（151 暗殼頁，錨點 20 頁抽檢 ×1 全一）：
  ① :root 整塊替換→P0 canonical（#0F1520 族＋--pri 金→#5CA8FF 降級＋狀態色
     #22C55E/#EF4444/#EAB308/#F97316）＋緊接補 [data-theme="light"] 塊（martin W5-A 同款）
  ② </head> 前注入 ../sidebar.css＋../tsa_tokens.css（殼已 canonical，tokens 同值 inert）
  ③ <body> 後 #sidebar-container ④ </body> 前 ../sidebar.js
保留域（照 W5-C 語義/數據先例，全部不動）：
  - 圖表系列色 #FFC107×127,714／#fd7e14×72,957（harvested SVG 數據色，2b 波域）
  - 金 #FFD700×1,084（:root 外；S+ 徽記／數據值——金降級只收 --pri 主題位）
  - hero 漸變 #16213e→#0f1729×151＋.hero h1 #fff＋.chart-plate #fff×151（2b 裝飾域）
  - 內容層 inline #1a1f2e×36＋#64b5f6×24（harvested panels 裝飾 chip）
  - #fff×45,091／#333×11,276（SVG fill／數據字色）
用法：python3 w5d_index_nav_20261105.py [--dry|--verify]
"""
import re
import sys
from pathlib import Path

BASE = Path('/home/z/my-project/exchange-repo')
PAGES = sorted((BASE / 'docs/reports').glob('index_*.html'))

# --- :root 整塊替換（151/151 byte 一致實證） ---
ROOT_OLD = (':root{--bg:#0a0e17;--card:#111520;--card2:#1a1f2e;--zebra:#151b28;--brd:#1e2433;--th:#111520;\n'
            '--text:#d0d0d0;--text2:#777;--pri:#FFD700;--acc:#64b5f6;--grn:#4CAF50;--red:#FF5722;--yel:#FFC107;\n'
            '--green:var(--grn);--yellow:var(--yel);--orange:#fd7e14;--primary:var(--pri);--accent:var(--acc);\n'
            '--grade-a:#4CAF50;--grade-b:#FFC107;--grade-c:#fd7e14;--grade-d:#FF5722;\n'
            '--radius:12px;--shadow:0 4px 16px rgba(0,0,0,.4)}')
ROOT_NEW = (':root{--bg:#0F1520;--card:#161E2E;--card2:#1C2638;--zebra:#131C2E;--brd:#2A3650;--th:#161E2E;\n'
            '--text:#E6EDF5;--text2:#A8B4C4;--pri:#5CA8FF;--acc:#38BDF8;--grn:#22C55E;--red:#EF4444;--yel:#EAB308;\n'
            '--green:var(--grn);--yellow:var(--yel);--orange:#F97316;--primary:var(--pri);--accent:var(--acc);\n'
            '--grade-a:#22C55E;--grade-b:#EAB308;--grade-c:#F97316;--grade-d:#EF4444;\n'
            '--radius:12px;--shadow:0 4px 16px rgba(0,0,0,.4)}\n'
            '[data-theme="light"]{--bg:#F1F5F9;--card:#FFFFFF;--card2:#E2E8F0;--zebra:#F8FAFC;--brd:#CBD5E1;--th:#E2E8F0;\n'
            '--text:#1E293B;--text2:#64748B;--pri:#2563EB;--acc:#0EA5E9;--grn:#16A34A;--red:#DC2626;--yel:#CA8A04}')

HEAD_DARK = ('<!-- W5-D（2026-11-05）：NAV 四件 1+2——sidebar.css＋tsa_tokens.css'
             '（:root 已 remap P0 canonical，tokens 同值 inert） -->\n'
             '<link rel="stylesheet" href="../sidebar.css">\n'
             '<link rel="stylesheet" href="../tsa_tokens.css">\n')
HEAD_LIGHT = ('<!-- W5-D（2026-11-05）：NAV 三件 1+2——sidebar.css；tokens 豁免'
              '（var 驅動 light 設計＋全站 dark default 會翻黑，照 W5-C v3.9 先例） -->\n'
              '<link rel="stylesheet" href="../sidebar.css">\n')
BODY_INJ = '<!-- W5-D：NAV 之 #sidebar-container -->\n<div id="sidebar-container"></div>\n'
TAIL_INJ = '<script src="../sidebar.js"></script>\n'

# 殼 token 舊值（:root 外＝0 實證；驗收殘留必須＝0）
SHELL_LEGACY = ['0a0e17', '111520', '151b28', '1e2433', 'd0d0d0']


def classify(t: str) -> str:
    # 全文判定（注入後 head 變長，窗口式判唔到）：舊塊=未轉換／新塊=已轉換／light=var 族
    if ROOT_OLD in t:
        return 'ta'
    if ROOT_NEW in t:
        return 'ta'
    if '#0f3460' in t:
        return 'light'
    return '?'


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    dry, verify = mode == '--dry', mode == '--verify'
    done = skip = fail = 0
    fails = []
    fmts = {'ta': 0, 'light': 0, '?': 0}
    for p in PAGES:
        t = p.read_text(encoding='utf-8', errors='replace')
        fmt = classify(t)
        fmts[fmt] += 1
        if fmt == '?':
            fail += 1; fails.append(f'{p.name}: 格式不明（fail-close）'); continue
        if 'sidebar-container' in t or 'sidebar.js' in t:
            skip += 1        # 冪等閘
            continue
        # --- 錨點全一先至動 ---
        if t.count('</head>') != 1 or t.count('</body>') != 1 or len(re.findall(r'<body[^>]*>', t)) != 1:
            fail += 1; fails.append(f'{p.name}: 錨點非全一'); continue
        t2 = t
        root_ok = None
        if fmt == 'ta':
            if t.count(ROOT_OLD) != 1:
                fail += 1; fails.append(f'{p.name}: :root 舊塊非全一'); continue
            t2 = t.replace(ROOT_OLD, ROOT_NEW)
            root_ok = True
        head_inj = HEAD_DARK if fmt == 'ta' else HEAD_LIGHT
        t2 = t2.replace('</head>', head_inj + '</head>')
        t2 = re.sub(r'(<body[^>]*>)', r'\1' + BODY_INJ, t2, count=1)
        i = t2.find('</body>')
        t2 = t2[:i] + TAIL_INJ + t2[i:]
        # --- 純插入自證：還原後必須等同原文 ---
        strip = t2.replace(head_inj, '').replace(BODY_INJ, '').replace(TAIL_INJ, '')
        if fmt == 'ta':
            strip = strip.replace(ROOT_NEW, ROOT_OLD)
        if strip != t:
            fail += 1; fails.append(f'{p.name}: 還原不對齊（唔應該發生）'); continue
        if not dry and not verify:
            p.write_text(t2, encoding='utf-8')
        done += 1
        tag = 'root+nav' if fmt == 'ta' else 'nav(light)'
        if done <= 3 or dry:
            print(f'  [{"DRY" if dry else "OK"}] {p.name} [{tag}]')
    print(f'\n=== {mode or "run"}：改{done} 跳{skip} 敗{fail}（共{len(PAGES)}；族計 {fmts}） ===')
    for f in fails[:10]:
        print('  FAIL:', f)

    if verify:
        bad = 0
        for p in PAGES:
            t = p.read_text(encoding='utf-8', errors='replace')
            fmt = classify(t)
            css = t.count('<link rel="stylesheet" href="../sidebar.css">')
            js = t.count('<script src="../sidebar.js"></script>')
            cont = t.count('<div id="sidebar-container"></div>')
            tok = t.count('<link rel="stylesheet" href="../tsa_tokens.css">')
            if fmt == 'ta':
                legacy = sum(t.lower().count('#' + k) for k in SHELL_LEGACY)
                ok = (css == 1 and js == 1 and cont >= 1 and tok == 1 and legacy == 0
                      and ROOT_NEW in t and '--text2:#777' not in t)
            elif fmt == 'light':
                ok = css == 1 and js == 1 and cont >= 1 and tok == 0 and '#0f3460' in t
            else:
                ok = False
            if not ok:
                bad += 1
                print(f'  [VERIFY-FAIL] {p.name} fmt={fmt} css={css} js={js} cont={cont} tok={tok}')
        n_expect = len(PAGES)
        print(f'=== verify：{"PASS %d/%d" % (n_expect - bad, n_expect) if bad == 0 else "FAIL %d" % bad} ===')
        return 0 if bad == 0 else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
