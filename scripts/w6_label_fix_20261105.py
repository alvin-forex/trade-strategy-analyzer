#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""w6_label_fix_20261105.py — P-1a/W6 v2.1：地圖標籤撞色修復（老闆 11-05「地圖與文字撞色」直令）

問題（live 四幀＋老闆回報對上）：
  1. 國名標籤 .map-lbl fill #D9BC55（暗金）疊喺 12 貨幣國亮金粒子上（op .42-.85＋#FFE566）＝金撞金；
  2. 事件標記 .ev-high-txt（HIGH #FFD700）／.ev-marker（◆ #EAB308）疊喺金光環＋粒子上冇分離。

修法（金色粒子規格不動——粒子/光環/弧線全保留，只掂三條 CSS 文字規則）：
  1. .map-lbl fill #D9BC55 → 象牙白 #F2EAD3（註記層同數據層分色）；
  2. 三條文字規則同加深黑 halo：paint-order:stroke;stroke:rgba(5,7,12,.9);
     stroke-width:.1em;stroke-linejoin:round（em 制隨字號縮放；getBBox 不含
     stroke＝防碰撞邏輯零影響；唔支援 paint-order 瀏覽器退化為淨填色仍可讀）。

設計：fail-close（三錨各恰 1 否則停）＋純度斷言（只三行替換、其餘 byte 不動、
無 halo 前 old fill/marker 必須在場）＋冪等（v2.1 態複跑 skip）＋--verify。

用法：python3 w6_label_fix_20261105.py <home_plaintext.html> [--dry|--verify]
"""
import re
import sys
from pathlib import Path

OLD_LBL = '.map-lbl{fill:#D9BC55;font-weight:700;pointer-events:none;letter-spacing:.5px}'
NEW_LBL = ('.map-lbl{fill:#F2EAD3;font-weight:700;pointer-events:none;letter-spacing:.5px;'
           'paint-order:stroke;stroke:rgba(5,7,12,.9);stroke-width:.1em;stroke-linejoin:round}')
OLD_MARK = '.ev-marker{font-size:44px;font-weight:700;text-anchor:middle;pointer-events:none}'
NEW_MARK = ('.ev-marker{font-size:44px;font-weight:700;text-anchor:middle;pointer-events:none;'
            'paint-order:stroke;stroke:rgba(5,7,12,.9);stroke-width:.1em;stroke-linejoin:round}')
OLD_HIGH = '.ev-high-txt{font-size:52px;font-weight:700;text-anchor:middle;pointer-events:none}'
NEW_HIGH = ('.ev-high-txt{font-size:52px;font-weight:700;text-anchor:middle;pointer-events:none;'
            'paint-order:stroke;stroke:rgba(5,7,12,.9);stroke-width:.1em;stroke-linejoin:round}')

PAIRS = [(OLD_LBL, NEW_LBL), (OLD_MARK, NEW_MARK), (OLD_HIGH, NEW_HIGH)]
HALO_MARK = 'paint-order:stroke'


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    path = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else 'apply'
    html = path.read_text(encoding='utf-8')
    orig = html

    n_old = sum(html.count(o) for o, _ in PAIRS)
    n_new = sum(html.count(n) for _, n in PAIRS)
    if n_new == 3 and n_old == 0:
        print('IDEMPOTENT_SKIP 已係 v2.1 態（三條 halo 在場，零動作）')
        sys.exit(0)
    if n_old != 3:
        print(f'FAIL_CLOSE v2 態錨點異常：old 三條應恰各 1，實得 {n_old}（new {n_new}）——停手')
        sys.exit(1)

    if mode == '--dry':
        for o, n in PAIRS:
            assert html.count(o) == 1, f'錨點非唯一：{o[:40]}'
            print(f'DRY  byte_delta {len(n.encode()) - len(o.encode()):+d}  {o.split("{")[0]}')
        print('DRY 三錨各恰 1，總 delta = %+d' % sum(len(n) - len(o) for o, n in PAIRS))
        sys.exit(0)

    for o, n in PAIRS:
        assert html.count(o) == 1, f'錨點非唯一：{o[:40]}'
        html = html.replace(o, n, 1)

    # 純度斷言：除三行外 byte 不動
    assert len(PAIRS) == 3
    rebuilt = orig
    for o, n in PAIRS:
        rebuilt = rebuilt.replace(o, n, 1)
    assert rebuilt == html, '重建不對齊——有非預期改動'
    for o, _ in PAIRS:
        assert o not in html, f'舊規則殘留：{o[:40]}'
    assert html.count(HALO_MARK) == 3, f'halo 應恰 3 處，實 {html.count(HALO_MARK)}'

    if mode == '--verify':
        print(f'VERIFY PASS  三錨已換＋halo x3＋舊值零殘留  bytes {len(orig.encode())}→{len(html.encode())}')
        sys.exit(0)

    path.write_text(html, encoding='utf-8')
    print(f'OK v2.1 三條 CSS 替換完成  bytes {len(orig.encode())}→{len(html.encode())}'
          f'（delta {len(html.encode()) - len(orig.encode()):+d}）')
    print('修復內容：.map-lbl 象牙白 #F2EAD3＋三條文字規則深黑 halo（粒子/光環/弧線零改動）')


if __name__ == '__main__':
    main()
