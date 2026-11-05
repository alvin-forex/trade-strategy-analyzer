#!/usr/bin/env python3
"""w5f_nav_20261105.py — W5-F：anomaly_report（dualvar 三件＋tokens 豁免）＋date_range_review 2 頁（四件＋五 remap）

裁決鏈：from_zcode/20261105_1140（勘察報告方案）→ from_openclaw/20261105_1150 §三（兩方案確認即刻開工）。

Part A——docs/reports/anomaly_report.html（2.1MB）：
  master_report_v2 同款雙主題 var 驅動頁（[data-theme="dark"] --bg:#0a0e17 ＋
  [data-theme="light"] --bg:#f5f7fa 各恰 1 塊；dark --pri:#FFD700 金＝身份色保留）。
  照 W5-G master_v2／W5-H 先例＝三件注入（../sidebar.css＋#sidebar-container＋
  ../sidebar.js）＋tokens 豁免（tsa_tokens.css :root 係 dark 值會接管 var 令設計翻黑）
  ＋變量零改動。body 級自帶 toggleTheme 與站點 html 級機制互不干擾（勘察證實）。

Part B——docs/reports/date_range_review/ 2 頁（93.8KB＋45.7KB）：
  hardcode 暗族（body linear-gradient(135deg,#1a1a2e 0%,#16213e 100%)、
  h1 #00d4ff 青、#00ff88/#ff4444 語義、#e0e0e0 次；無 :root 無 var）。
  四件注入＋五 remap（CI 等長 7→7，照 1150 回批確認方案）：
    #1a1a2e→#0F1520  #16213e→#131C2E（gradient 兩端點，形態保留）
    #00d4ff→#38BDF8  #00ff88→#22C55E  #ff4444→#EF4444  #e0e0e0→#A8B4C4（語義 canonical）
  出現次數（勘察＋OpenClaw 覆測雙側一致）：每頁 1/1/4/2/2/1。
  注意：子目錄兩層——注入路徑用 ../../（非 ../），sidebar.js 深度邏輯
  （段數計）自證兼容。

用法：python3 w5f_nav_20261105.py [--dry|--verify]
"""
import re
import sys
from pathlib import Path

BASE = Path('/home/z/my-project/exchange-repo')
ANOM = BASE / 'docs/reports/anomaly_report.html'
DR_PAGES = [
    BASE / 'docs/reports/date_range_review/review_2026-04-01_2026-05-31.html',
    BASE / 'docs/reports/date_range_review/review_2026-04-01_2026-05-31_signal_31593.html',
]

# ---- Part A：anomaly（dualvar 三件＋tokens 豁免；路徑 ../ = docs/reports/ 層） ----
ANOM_HEAD = (
    '<!-- W5-F（2026-11-05）：NAV 三件 1+2——sidebar.css；tokens 豁免\n'
    '（雙主題 var 驅動頁＋tokens :root 會接管 var 令設計翻黑，照 W5-G master_v2／\n'
    'W5-C v3.9 裁定；OpenClaw 1150 回批確認） -->\n'
    '<link rel="stylesheet" href="../sidebar.css">\n'
)
ANOM_BODY = '<!-- W5-F：NAV 之 #sidebar-container -->\n<div id="sidebar-container"></div>\n'
ANOM_TAIL = '<script src="../sidebar.js"></script>\n'

# ---- Part B：date_range_review（四件＋五 remap；路徑 ../../ = 兩層子目錄） ----
DR_HEAD = (
    '<!-- W5-F（2026-11-05）：NAV 四件 1+2——sidebar.css＋tsa_tokens.css（hardcode\n'
    '頁 tokens inert）；OpenClaw 1150 回批確認（gradient 兩端點→canonical 形態保留） -->\n'
    '<link rel="stylesheet" href="../../sidebar.css">\n'
    '<link rel="stylesheet" href="../../tsa_tokens.css">\n'
)
DR_BODY = '<!-- W5-F：NAV 之 #sidebar-container -->\n<div id="sidebar-container"></div>\n'
DR_TAIL = '<script src="../../sidebar.js"></script>\n'

DR_REMAP = [
    ('#1a1a2e', '#0F1520'),  # gradient 端點 1（每頁 ×1）
    ('#16213e', '#131C2E'),  # gradient 端點 2（每頁 ×1）
    ('#00d4ff', '#38BDF8'),  # h1 青（每頁 ×4）
    ('#00ff88', '#22C55E'),  # 綠語義（每頁 ×2）
    ('#ff4444', '#EF4444'),  # 紅語義（每頁 ×2）
    ('#e0e0e0', '#A8B4C4'),  # 次要文字（每頁 ×1）
]
DR_EXPECT = {  # 每頁期望替換次數（勘察＋OpenClaw 覆測一致）
    '#1a1a2e': 1, '#16213e': 1, '#00d4ff': 4, '#00ff88': 2, '#ff4444': 2, '#e0e0e0': 1,
}


def anchors_ok(t):
    return (t.count('</head>') == 1 and len(re.findall(r'<body[^>]*>', t)) == 1
            and t.count('</body>') == 1)


def inject(t, head, body, tail):
    t2 = t.replace('</head>', head + '</head>')
    t2 = re.sub(r'(<body[^>]*>)', r'\1' + body, t2, count=1)
    i = t2.find('</body>')
    t2 = t2[:i] + tail + t2[i:]
    # 純插入自證（剝返三件須等於原文）
    if (t2.replace(head, '').replace(body, '').replace(tail, '')) != t:
        return None
    return t2


def part_a(mode):
    """anomaly_report：dualvar 閘→三件注入（tokens 豁免）"""
    p = ANOM
    t = p.read_text(encoding='utf-8', errors='replace')
    if 'sidebar-container' in t or 'sidebar.js' in t:
        print(f'  [SKIP] {p.name}: 已注入（冪等閘）')
        return 'skip'
    # dualvar fail-close 閘：雙主題塊＋兩 --bg 值同時在場（post-classify 態）
    low = t.lower()
    ok = ('[data-theme="dark"]' in low and '[data-theme="light"]' in low
          and '--bg:#0a0e17' in low and '--bg:#f5f7fa' in low
          and tsa_tok_absent(t))
    if not ok:
        print(f'  [FAIL] {p.name}: 非 dualvar 族（fail-close）')
        return 'fail'
    if not anchors_ok(t):
        print(f'  [FAIL] {p.name}: 錨點非各恰 1')
        return 'fail'
    t2 = inject(t, ANOM_HEAD, ANOM_BODY, ANOM_TAIL)
    if t2 is None:
        print(f'  [FAIL] {p.name}: 插入自證唔過')
        return 'fail'
    if mode == 'run':
        p.write_text(t2, encoding='utf-8')
    print(f'  [{"DRY" if mode == "dry" else "OK"}] {p.name} dualvar:nav3-tok0')
    return 'done'


def tsa_tok_absent(t):
    return 'tsa_tokens.css' not in t


def part_b(mode):
    """date_range_review 2 頁：hardcode 閘→remap 6 色值→四件注入"""
    stats = []
    for p in DR_PAGES:
        t = p.read_text(encoding='utf-8', errors='replace')
        if 'sidebar-container' in t or 'sidebar.js' in t:
            print(f'  [SKIP] {p.name}: 已注入（冪等閘）')
            stats.append((p.name, 'skip', {}))
            continue
        # hardcode fail-close 閘：gradient 兩端點各恰 1＋無 :root var
        low = t.lower()
        if not (low.count('#1a1a2e') == 1 and low.count('#16213e') == 1
                and ':root' not in low and 'var(--' not in low):
            print(f'  [FAIL] {p.name}: 非 date_range hardcode 暗族（fail-close）')
            stats.append((p.name, 'fail', {}))
            continue
        if not anchors_ok(t):
            print(f'  [FAIL] {p.name}: 錨點非各恰 1')
            stats.append((p.name, 'fail', {}))
            continue
        # --- remap（先 remap 後注入；次數逐色對期望） ---
        cnt = {}
        for old, new in DR_REMAP:
            n = low.count(old)
            cnt[old] = n
            if n != DR_EXPECT[old]:
                print(f'  [FAIL] {p.name}: {old} 出現 {n} 次（期望 {DR_EXPECT[old]}）')
                stats.append((p.name, 'fail', {}))
                break
        else:
            for old, new in DR_REMAP:
                t = re.sub(re.escape(old), new, t)
            t2 = inject(t, DR_HEAD, DR_BODY, DR_TAIL)
            if t2 is None:
                print(f'  [FAIL] {p.name}: 插入自證唔過')
                stats.append((p.name, 'fail', {}))
                continue
            if mode == 'run':
                p.write_text(t2, encoding='utf-8')
            print(f'  [{"DRY" if mode == "dry" else "OK"}] {p.name} hardcode:remap6+nav4 '
                  f'({"/".join(str(cnt[o]) for o, _ in DR_REMAP)})')
            stats.append((p.name, 'done', cnt))
    return stats


def verify():
    bad = 0
    # A：anomaly 三件＋tokens 0＋dualvar 證據完好＋零 remap（變量零改動）
    t = ANOM.read_text(encoding='utf-8', errors='replace')
    css = t.count('<link rel="stylesheet" href="../sidebar.css">')
    js = t.count('<script src="../sidebar.js"></script>')
    cont = t.count('<div id="sidebar-container"></div>')
    tok = t.count('tsa_tokens.css')
    ok = css == 1 and js == 1 and cont == 1 and tok == 0
    ok = ok and t.count('[data-theme="dark"]') >= 1 and t.count('[data-theme="light"]') == 1
    ok = ok and '--bg:#0a0e17' in t and '--bg:#f5f7fa' in t and '--pri:#FFD700' in t
    print(f'  A anomaly_report.css={css} js={js} cont={cont} tok={tok} '
          f'{"PASS" if ok else "FAIL"}')
    bad += 0 if ok else 1
    # B：date_range 四件＋remap 後殘留 0＋新值在場
    for p in DR_PAGES:
        t = p.read_text(encoding='utf-8', errors='replace')
        low = t.lower()
        css = t.count('<link rel="stylesheet" href="../../sidebar.css">')
        tok = t.count('<link rel="stylesheet" href="../../tsa_tokens.css">')
        js = t.count('<script src="../../sidebar.js"></script>')
        cont = t.count('<div id="sidebar-container"></div>')
        resid = sum(low.count(o) for o, _ in DR_REMAP)
        fresh = all(new in t for _, new in DR_REMAP)
        ok = css == 1 and tok == 1 and js == 1 and cont == 1 and resid == 0 and fresh
        print(f'  B {p.name[:46]}.. css={css} tok={tok} js={js} cont={cont} resid={resid} '
              f'{"PASS" if ok else "FAIL"}')
        bad += 0 if ok else 1
    n = 3
    print(f'=== verify：{"PASS %d/%d" % (n, n) if bad == 0 else "FAIL %d" % bad} ===')
    return 0 if bad == 0 else 1


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    if mode == '--verify':
        return verify()
    print(f'=== W5-F（mode={mode}）===')
    a = part_a(mode)
    b_stats = part_b(mode)
    done = (a == 'done') + sum(1 for _, s, _ in b_stats if s == 'done')
    skip = (a == 'skip') + sum(1 for _, s, _ in b_stats if s == 'skip')
    fail = (a == 'fail') + sum(1 for _, s, _ in b_stats if s == 'fail')
    print(f'=== 總計：改{done} 跳{skip} 敗{fail}（共 3） ===')
    return 1 if fail else 0


if __name__ == '__main__':
    sys.exit(main())
