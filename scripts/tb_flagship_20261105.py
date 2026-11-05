#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tb_flagship_20261105.py — P-1b TB 旗艦金調：頁層施工工具（解密 plaintext 態）

規格：from_openclaw/20261105_1255（插隊令 P-1b：TB 全 treatment 旗艦級——
NAV＋token＋金調＋深藍黑底）＋ W5-I 套路（生成器層＋頁層同步＋deterministic 重加密）。

改動面（嚴格兩處，其餘 byte 不動）：
  1. <style>...</style> 塊內容：舊 CSS+NAV_CSS → 新 CSS+NAV_CSS
     （**由 tasks_board_gen.py v3.2 直接 import 常量**——與生成器輸出 byte 一致，
     TASKS.md 重生成唔會沖走旗艦樣式）
  2. footer GEN 串：v3（…P3…） → v3.2（…P-1b 旗艦金調…）

設計內容（P-1b 旗艦金調，全部 CSS 層）：
  - :root 擴 --gold/--gold2 canonical（board 零變量依賴慣例，主題 toggle 免疫）
  - h1 金漸層（@supports background-clip:text guard，fallback 實色金）
  - active KPI 金數字＋金 glow＋金左邊條
  - body 頂部金 radial 微光（深藍黑底 --l0 維持）
  - KPI/卡片漸層底＋深影；卡 hover 微升（hover:hover＋reduced-motion 雙守衛）
  - 列 hover 掃讀底色；::selection/::focus-visible/scrollbar/footer 金點
  - NAV 方案 C＋W5-I 三件＋A10 零 script 範圍全保留

用法：
  python3 tb_flagship_20261105.py <plaintext.html>            # 實跑（原地改）
  python3 tb_flagship_20261105.py <plaintext.html> --dry      # 預演
  python3 tb_flagship_20261105.py <plaintext.html> --verify   # 後態覆核
"""
import importlib.util
import re
import sys
from pathlib import Path

GEN_PATH = Path('/home/z/my-project/exchange-repo/scripts/tasks_board_gen.py')

_spec = importlib.util.spec_from_file_location('tasks_board_gen', GEN_PATH)
_gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gen)

NEW_CSS_BLOCK = _gen.CSS + _gen.NAV_CSS          # v3.2 旗艦（byte 同生成器輸出）
NEW_GEN = _gen.GEN

GEN_RE = re.compile(r'ZCODE tasks_board_gen v3\.2（2026-11-05 P-1b[^）]*）')
OLD_GEN_RE = re.compile(r'ZCODE tasks_board_gen v3（2026-11-04 P3[^）]*）')


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else 'run'
    if not src.exists():
        print(f'[FAIL] 檔案不存在: {src}')
        return 1
    t = src.read_text(encoding='utf-8')

    # ---- 錨點斷言（fail-close） ----
    n_style = t.count('<style>')
    if n_style != 1:
        print(f'[FAIL] <style> ×{n_style}（須恰 1）')
        return 1
    i0 = t.find('<style>') + len('<style>')
    i1 = t.find('</style>')
    old_css_block = t[i0:i1]
    m_old = OLD_GEN_RE.search(t)
    if not m_old:
        # 冪等：可能已係新 GEN
        if GEN_RE.search(t):
            print('[SKIP] GEN 已係 v3.2（冪等）')
        else:
            print('[FAIL] 搵唔到舊 GEN 串（v3 P3）——形態不符 fail-close')
            return 1

    if mode == '--verify':
        ok_css = old_css_block == NEW_CSS_BLOCK
        ok_gen = bool(GEN_RE.search(t))
        three = (t.count('<link rel="stylesheet" href="../sidebar.css">') == 1
                 and t.count('<div id="sidebar-container"></div>') == 1
                 and t.count('<script src="../sidebar.js"></script>') == 1)
        n_sec = t.count('<section class="card') + t.count('details class="card')
        print(f'  css_block=v3.2 {"PASS" if ok_css else "FAIL"} | GEN v3.2 {"PASS" if ok_gen else "FAIL"} '
              f'| NAV 三件 {"PASS" if three else "FAIL"} | cards={n_sec}')
        print(f'=== verify：{"PASS" if ok_css and ok_gen and three else "FAIL"} ===')
        return 0 if ok_css and ok_gen and three else 1

    # ---- 施工：兩處替換（GEN 先——style 塊重算避位偏移） ----
    t2 = t
    if m_old:
        t2 = t2[:m_old.start()] + NEW_GEN + t2[m_old.end():]
    i0b = t2.find('<style>') + len('<style>')
    i1b = t2.find('</style>')
    t2 = t2[:i0b] + NEW_CSS_BLOCK + t2[i1b:]

    # ---- 純度自證：除兩個 span 外 byte 不動（逆操作還原==原檔） ----
    back = t2[:i0b] + old_css_block + t2[i0b + len(NEW_CSS_BLOCK):]
    if m_old:
        back = back.replace(NEW_GEN, m_old.group(0), 1)
    if back != t:
        print('[FAIL] 逆操作還原唔等於原檔（純度斷言 fail-close 唔寫檔）')
        return 1

    # ---- 結構不變自證：卡片/列數目一致 ----
    for pat in (r'<section class="card', r'<details class="card', r'class="row row-2"',
                r'class="kpi ', r'<h2>'):
        if len(re.findall(pat, t)) != len(re.findall(pat, t2)):
            print(f'[FAIL] 結構計數變化：{pat}')
            return 1

    delta = len(t2) - len(t)
    if mode == '--dry':
        print(f'[DRY] {src.name}：style 塊 {len(old_css_block)}→{len(NEW_CSS_BLOCK)}B＋'
              f'GEN 串 {len(m_old.group(0)) if m_old else 0}→{len(NEW_GEN)}B；'
              f'總 byte_delta={delta:+d}；其餘 byte 不動（純度斷言過）')
        return 0

    src.write_text(t2, encoding='utf-8')
    print(f'[OK] {src.name} 旗艦金調落地：style 塊＋GEN 串兩處；byte_delta={delta:+d}；'
          f'cards/rows/kpi 計數不變；NAV 三件保留')
    return 0


if __name__ == '__main__':
    sys.exit(main())
