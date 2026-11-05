#!/usr/bin/env python3
"""w5e_signal_light_20261105.py — W5-E（signal_* 71 頁）：NAV 三件注入＋tokens 豁免

背景：0700 總派工單 W5「signal_* 76」口徑對賬（1040 回執）——
  signal_*.html 71 頁＝light var 驅動族（:root --bg:#f5f7fa／--primary:#0f3460 navy；
  #0f3460×905；#0d1117/#1976d2/#667eea/gold 全 0；signal_* 無生成器簽名）。
  anomaly_report.html 勘察後**剔出本批**（browser 實測捉出）：暗畫布混種頁
  （body var(--bg)→#0a0e17＋金 h1 #FFD700；單處 #f5f7fa 係局部塊）——歸 W5-F 暗殼 remap 批。
  餘 4 頁另族同樣唔入本批：date_range_review/×2（無 :root hardcode）／
  sample_redesign_36912.html（v2 舊殼 #0a0e17 樣版）／docs/signal_ranking.html（🔐 門戶）。

做法（照 W5-C v3.9 24 頁裁定同款＋tug light 規範族先例）：
  三件注入——../sidebar.css＋#sidebar-container＋../sidebar.js；
  豁免 tsa_tokens.css：tokens :root 係 dark 值，全站 dark default（sidebar.js 強制
  data-theme=localStorage['tsa-theme']||'dark'）下會接管 var(--bg/--text/--primary)
  令 var 驅動 light 設計翻黑破版。內容／變量零改動。
語義色／漸變／數據色全不動（純插入批次）。
分類 fail-close：頁面必須同時具備 :root 與 #f5f7fa 先至算 light var 族，否則唔動。
用法：python3 w5e_signal_light_20261105.py [--dry|--verify]
"""
import re
import sys
from pathlib import Path

BASE = Path('/home/z/my-project/exchange-repo')
PAGES = sorted((BASE / 'docs/reports').glob('signal_*.html'))

HEAD_INJ = ('<!-- W5-E（2026-11-05）：NAV 三件 1+2——sidebar.css；tokens 豁免'
            '（var 驅動 light 設計＋全站 dark default 會翻黑，照 W5-C v3.9 裁定） -->\n'
            '<link rel="stylesheet" href="../sidebar.css">\n')
BODY_INJ = ('<!-- W5-E：NAV 之 #sidebar-container -->\n<div id="sidebar-container"></div>\n')
TAIL_INJ = '<script src="../sidebar.js"></script>\n'


def is_light_var(t: str) -> bool:
    """收緊準則（v2）：必須 --bg:#f5f7fa 真簽名＋零暗畫布殘留。
    v1（':root'+ '#f5f7fa' 同頁即過）被 anomaly_report 混種頁繞過
    （暗畫布 #0a0e17 附掛局部 light 塊）——browser 實測捉出後收緊。"""
    low = t.lower()
    if '#0a0e17' in low or '#0d1117' in low:      # 暗畫布標記 → 非 light 族
        return False
    return '--bg:#f5f7fa' in low.replace(' ', '')  # 真 light var 簽名


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    dry, verify = mode == '--dry', mode == '--verify'
    done = skip = fail = 0
    fails = []
    for p in PAGES:
        t = p.read_text(encoding='utf-8', errors='replace')
        if not is_light_var(t):
            fail += 1; fails.append(f'{p.name}: 非 light var 族（fail-close）'); continue
        already_nav = 'sidebar-container' in t or 'sidebar.js' in t
        if already_nav:
            skip += 1  # 已注入（冪等閘）
            continue
        # --- 三錨點（全一先至動） ---
        if t.count('</head>') != 1:
            fail += 1; fails.append(f'{p.name}: </head> ×{t.count("</head>")}'); continue
        mb = re.findall(r'<body[^>]*>', t)
        if len(mb) != 1:
            fail += 1; fails.append(f'{p.name}: <body> ×{len(mb)}'); continue
        if t.count('</body>') != 1:
            fail += 1; fails.append(f'{p.name}: </body> ×{t.count("</body>")}'); continue
        t2 = t.replace('</head>', HEAD_INJ + '</head>')
        t2 = re.sub(r'(<body[^>]*>)', r'\1' + BODY_INJ, t2, count=1)
        i = t2.find('</body>')
        t2 = t2[:i] + TAIL_INJ + t2[i:]
        # --- 純插入自證：除注入位外零改動 ---
        strip = lambda s: s.replace(HEAD_INJ, '').replace(BODY_INJ, '').replace(TAIL_INJ, '')
        if strip(t2) != t:
            fail += 1; fails.append(f'{p.name}: 插入後原文不對齊（唔應該發生）'); continue
        if not dry and not verify:
            p.write_text(t2, encoding='utf-8')
        done += 1
        if done <= 3 or dry:
            print(f'  [{"DRY" if dry else "OK"}] {p.name} light_var:nav3')
    print(f'\n=== {mode or "run"}：改{done} 跳{skip} 敗{fail}（共{len(PAGES)}） ===')
    for f in fails[:10]:
        print('  FAIL:', f)

    if verify:
        bad = 0
        for p in PAGES:
            t = p.read_text(encoding='utf-8', errors='replace')
            css = t.count('<link rel="stylesheet" href="../sidebar.css">')
            js = t.count('<script src="../sidebar.js"></script>')
            cont = t.count('<div id="sidebar-container"></div>')
            tok = t.count('<link rel="stylesheet" href="../tsa_tokens.css">')
            ok = css == 1 and js == 1 and cont >= 1 and tok == 0 and '#0f3460' in t
            if not ok:
                bad += 1
                print(f'  [VERIFY-FAIL] {p.name} css={css} js={js} cont={cont} tok={tok}')
        n = len(PAGES)
        print(f'=== verify：{"PASS %d/%d" % (n, n) if bad == 0 else f"FAIL {bad}"} ===')
        return 0 if bad == 0 else 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
