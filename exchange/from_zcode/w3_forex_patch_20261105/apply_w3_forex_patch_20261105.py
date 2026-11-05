#!/usr/bin/env python3
"""apply_w3_forex_patch_20261105.py — W3 patch：forex_combined_report.py 生成器模板層套用工具

規格來源：from_openclaw/20261105_0846（方案 A：照 P0/W1 同構出模板 patch——
tsa_tokens.css link＋NAV 四件補齊＋token remap 三條→exchange 回 diff→OpenClaw 側
套用生成器＋重生成 live 頁驗收）＋0700 總派工單 W3 行（生成器模板層改，禁逐頁手改）。

patch 內容（三步，全部等長/純插入——byte 可控）：
  1. head：sidebar.css 行後插 tsa_tokens.css link（四件之第 2 件；hardcode 殼頁
     tokens inert，照 W1/W5-G dark10 同構）
  2. body：`<body ...>` 行後插 #sidebar-container div（四件之第 3 件；W5 全批次
     掛點慣例）
  3. 全域 remap 三條（CI 等長 7→7 hex，照 W5-G dark10 殾 remap 規格）：
       #0d1117 → #0F1520（暗畫布）
       #58a6ff → #5CA8FF（連結/標題藍）
       #8b949e → #A8B4C4（次要文字）
     語義域保留：#3fb950/#f85149/#56d364 勝負、#161b22/#21262d/#30363d/#e6edf3/
     #c9d1d9/#484f58/#1f2937/#666 組件色、inline verdict bar 色——全不動。

適用對象：OpenClaw 側 ~/.openclaw/workspace/scripts/forex_combined_report.py
（1204 行；錨點＝頁面骨架 L1092-1135＋build_css L475；工具按字串錨點操作，
唔依賴行號——生成器版本演進安全）。

用法（OpenClaw 側）：
  python3 apply_w3_forex_patch_20261105.py <生成器.py>            # 實套（自動 .bak 備份）
  python3 apply_w3_forex_patch_20261105.py <生成器.py> --dry      # 預演（只報告唔寫）
  python3 apply_w3_forex_patch_20261105.py <生成器.py> --verify   # 套用後驗證
  python3 apply_w3_forex_patch_20261105.py <生成器.py> --restore  # 由 .bak 回滾

鐵律：fail-close——錨點唔齊（sidebar.css link 恰 1＋sidebar.js 恰 1＋<body 恰 1）
即停唔寫；冪等——已有 tsa_tokens 即跳過注入步（remap 照跑至殘留 0）。
"""
import sys
import shutil
from pathlib import Path

REMAP = [  # (old, new, 釋義)
    ('#0d1117', '#0F1520', '暗畫布'),
    ('#58a6ff', '#5CA8FF', '連結/標題藍'),
    ('#8b949e', '#A8B4C4', '次要文字'),
]

CSS_LINE = '<link rel="stylesheet" href="../sidebar.css">'
TOK_LINE = '<link rel="stylesheet" href="../tsa_tokens.css">'
JS_LINE = '<script src="../sidebar.js"></script>'
CONT_INJ = ('<!-- W3（2026-11-05）：NAV 四件之 #sidebar-container（ZCODE_w patch，'
            '照 P0/W1 同構） -->\n<div id="sidebar-container"></div>\n')


def counts(t: str):
    return {
        'css': t.count(CSS_LINE),
        'js': t.count(JS_LINE),
        'tok': t.count(TOK_LINE),
        'body': t.count('<body'),
        'cont': t.count('<div id="sidebar-container">'),
        **{old: t.count(old) for old, _, _ in REMAP},
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    src = Path(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else 'run'
    dry = mode == '--dry'
    verify = mode == '--verify'
    restore = mode == '--restore'
    bak = src.with_suffix(src.suffix + '.bak_w3')

    if restore:
        if not bak.exists():
            print(f'[restore-FAIL] 無備份 {bak}')
            return 1
        shutil.copy2(bak, src)
        print(f'[restore-OK] {src.name} 已由 {bak.name} 回滾')
        return 0

    if not src.exists():
        print(f'[FAIL] 檔案不存在: {src}')
        return 1
    t = src.read_text(encoding='utf-8', errors='replace')
    c0 = counts(t)

    # ---- fail-close 錨點閘（先行；對 HTML 測試副本同樣生效） ----
    problems = []
    if c0['css'] != 1:
        problems.append(f'sidebar.css link ×{c0["css"]}（須恰 1）')
    if c0['js'] != 1:
        problems.append(f'sidebar.js script ×{c0["js"]}（須恰 1）')
    if c0['body'] != 1:
        problems.append(f'<body ×{c0["body"]}（須恰 1）')
    if problems:
        print('[FAIL] 錨點閘不過（fail-close，唔寫檔）：')
        for p in problems:
            print('   -', p)
        return 1

    if verify:
        ok = (c0['tok'] == 1 and c0['cont'] == 1
              and all(c0[old] == 0 for old, _, _ in REMAP)
              and c0['css'] == 1 and c0['js'] == 1)
        print(f"[verify] css={c0['css']} tok={c0['tok']} cont={c0['cont']} js={c0['js']} "
              f"resid(#0d1117/#58a6ff/#8b949e)={c0['#0d1117']}/{c0['#58a6ff']}/{c0['#8b949e']}")
        print(f'=== verify：{"PASS" if ok else "FAIL"} ===')
        return 0 if ok else 1

    t2 = t
    injected_tok = injected_cont = False

    # ---- 步 1：tsa_tokens.css（冪等閘） ----
    if c0['tok'] == 0:
        t2 = t2.replace(CSS_LINE,
                        CSS_LINE + '\n'
                        '<!-- W3（2026-11-05）：tsa_tokens.css（ZCODE_w patch，照 P0/W1 同構；'
                        'hardcode 殼頁 inert） -->\n' + TOK_LINE, 1)
        injected_tok = True
    else:
        print(f'[SKIP] tsa_tokens 已在場（×{c0["tok"]}）')

    # ---- 步 2：#sidebar-container（冪等閘） ----
    if c0['cont'] == 0:
        i = t2.find('<body')
        j = t2.find('>', i)
        if i == -1 or j == -1:
            print('[FAIL] <body 標籤不完整（fail-close，唔寫檔）')
            return 1
        t2 = t2[:j + 1] + '\n' + CONT_INJ + t2[j + 1:]
        injected_cont = True
    else:
        print(f'[SKIP] #sidebar-container 已在場（×{c0["cont"]}）')

    # ---- 步 3：remap 三條（全域等長；冪等——殘留 0 時零動作） ----
    rep = {}
    for old, new, note in REMAP:
        up = old.upper()
        if t2.count(up):  # 大寫變體在場＝非預期形態，fail-close 手動確認
            print(f'[FAIL] {up} 大寫變體在場 {t2.count(up)} 處（fail-close，'
                  f'請人工確認後手動 remap 為 {new}）')
            return 1
        n = t2.count(old)
        if n:
            t2 = t2.replace(old, new)
            rep[old] = n
        else:
            rep[old] = 0

    # ---- 自證：等長 remap＋純插入 → byte 增量可控 ----
    delta = len(t2) - len(t)
    exp_delta = ((len(TOK_LINE) + 1 + len('<!-- W3（2026-11-05）：tsa_tokens.css（ZCODE_w patch，照 P0/W1 同構；hardcode 殼頁 inert） -->\n')) if injected_tok else 0) \
        + ((len(CONT_INJ) + 1) if injected_cont else 0) \
        + sum(rep[old] * (len(new) - len(old)) for old, new, _ in REMAP)
    if delta != exp_delta:
        print(f'[FAIL] byte 對賬不符：實際 {delta} ≠ 期望 {exp_delta}（fail-close 唔寫檔）')
        return 1

    if dry:
        print(f'[DRY] {src.name}：tokens={"+" if injected_tok else "skip"} '
              f'container={"+" if injected_cont else "skip"} '
              f'remap={rep["#0d1117"]}/{rep["#58a6ff"]}/{rep["#8b949e"]} '
              f'（#0d1117/#58a6ff/#8b949e） byte_delta={delta}')
        return 0

    if t2 != t:
        shutil.copy2(src, bak)
        src.write_text(t2, encoding='utf-8')
        print(f'[OK] {src.name} 已套用（備份 {bak.name}）：'
              f'tokens={"+" if injected_tok else "skip"} '
              f'container={"+" if injected_cont else "skip"} '
              f'remap={rep["#0d1117"]}/{rep["#58a6ff"]}/{rep["#8b949e"]} '
              f'byte_delta={delta}')
        print('下一步：重生成 live 頁（晨報 07:00／晚報 18:00 cron 或手動）→ '
              '本工具 --verify → exchange 驗收信。')
    else:
        print(f'[SKIP] {src.name}：零動作（patch 已全數在場＝冪等）')
    return 0


if __name__ == '__main__':
    sys.exit(main())
