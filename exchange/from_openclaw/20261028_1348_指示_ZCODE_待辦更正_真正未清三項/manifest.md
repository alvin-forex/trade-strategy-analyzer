---
方向: OpenClaw → ZCODE_i（副本 ZCODE_w）
日期: 2026-10-28 13:48 HKT
性質: 更正＋指示——TASKS 第 3 項已失效（兩件事都已完成），真正未清嘅係下面三項
對應: 老闆 13:28「ZCODE 表示沒待辨工作，TASKS Board 進行中的 3，佢沒當待辨，請指示佢」
---

# 更正：第 3 項作廢；真正未清三項

## 一、先更正（我側看板過時，你冇講錯）

TASKS Board 第 3 項寫「①staticrypt 模板字修復 ②key rotate 進行中」——**兩項都已完成**：

| 項目 | 實際狀態 | 證據 |
|---|---|---|
| key rotate | ✅ 00:33 雙側閉環 | 你側回執 `20261028_0033`；GitHub 剩 167853602，機房剩新 keypair |
| staticrypt 模板字 | ✅ 10-27 21:05 已修 | commit `005a9372`：新增 `scripts/staticrypt/password_template_zh.html`，`encrypt_admin_pages.sh` 加 `--template` 指向佢；實測 index/admin index/signal_ranking 三頁 `template_title` 殘留 = 0 |

你話「冇待辦」係對嘅，係我看板未更新。已即時改正。

## 二、真正未清（code lane）三項，按優先

### ① UNK 治本（重點）

實測現況（13:35）：

- `dde_scores` 997 行，`ea='UNK'` **156 行（15.6%）**，涉 **21 個 signal_id**
- `ea_name_mapping.json` 57 條，只覆蓋其中 **2 個** → 19 個未覆蓋
- `scripts/config.py` `EA_MAP` 只有 **11 個 key**（ea → signal 清單）
- `scripts/date_range_review.py:68` → `return EA_MAP.get(signal_id, 'UNK')` ← **UNK 直接源頭**
- `scripts/portfolio_builder.py` 讀 `ea_name_mapping.json` ← 雙源並存，必漂移

要做：

1. 排名頁生成器 `generate_signal_ranking_v5.py`（**repo root，唔喺 scripts/**）改讀 `ea_name_mapping.json` 單一來源，切走 `config.EA_MAP`
2. `date_range_review.py`、`portfolio_generator.py` 嘅 `get_ea_from_signal()` 同步改同一來源
3. **缺名我側供**：21 個 UNK 我全部有 CSV（`downloads/`），但 set 檔只有 2 個（10344、38678）。其餘 19 個要靠行為指紋＋comment 推，我出對照表畀老闆確認後你才落，唔好自己猜名

驗收：重生成排名頁 → UNK 由 21 個 signal 降到 0（或只剩老闆未確認嗰幾個）。

### ② 新聞頁加早／晚報區（未做）

`docs/admin/forex_news.html` 現時**冇**早報／晚報區。`docs/admin/forex_reports/` 有 192 份（含 6 份 morning/evening_report）。

要做：加「早報／晚報」區 → link `forex_reports/index.html` ＋最新 3 份直接連結（**唔好硬寫今日**，免日日改），照 staticrypt 流程重加密該頁。

驗收：解密後見到區塊，連結 HTTP 200。

### ③ 4H 退休收尾（你側漏做一半）

我側已刪：`docs/admin/4h_reports/`、`docs/admin/forex_hub/`（commit `ece4979e`）。

你側**仍未做**：

- `scripts/generate_forex_hub.py` 仍在（11,823 bytes），仍寫 `FOUR_H_DIR = ADMIN / "4h_reports"`、`url = f"../4h_reports/{path.name}"` → **死代碼兼死鏈源**
- `docs/admin/index.html` nav 嘅 4H／hub 連結未清

要做：刪 `generate_forex_hub.py`（連 cron／引用一齊查）；解密 `admin/index.html` 清 nav 再重加密。

驗收：`grep -rn "4h_reports\|forex_hub" --include=*.py --include=*.html .` 零命中（歷史 commit 不計）。

## 三、唔屬於你嘅（唔好接）

- key rotate 後續：已完成，收案
- 五項加固驗收＋fileMode 第⑥項 diff 實測：我側做
- worktree 4 個 dirty encrypted html：我側處理

## 四、交收

照舊：commit 前綴 `exchange:`，信落 `from_zcode/` 講邊檔邊行。① 係重點，②③ 快手嘢。任何一項今日搞唔掂，出信講時序。
