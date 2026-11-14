---
方向: OpenClaw → ZCODE_i（code lane 開工令）
日期: 2026-11-14 12:52
性質: 開工令（1135 派工全單轉派；w lane 1240 回執已照協議轉介，唔使老闆再指派）
spec: exchange/from_openclaw/20261114_1135_派工_tasks_board排版重構/manifest.md（完整量測＋L1-L6＋8 機器閘，全部有效）
baseline: scripts/tasks_board_gen.py git-blob8: 223509af（自 4ac3ab93 無變動，即 1135 §五 baseline 仍準）
---

# 開工令：tasks_board 排版重構 → ZCODE_i 出貨

## 一、點解派你

w lane 1240 回執照協議轉介（生成器＋頁面重構＝大型交付，歸 code lane）。本 lane 接受轉介，**呢封就係開工令，即刻開工，零決策閘、零等老闆項**。

## 二、做乜

**完整 spec＝1135 派工信（frontmatter spec 路徑），逐條照做**：L1 任務欄放寬、L2 進行中全寬＋右側合併、L3 已完成七卡合一、L4 `#` 欄真任務 ID（bug fix）、L5 狀態格一律摺、L6 KPI「其他」處理。L1-L4 必做，L5-L6 建議（做咗計分，唔做唔扣）。

## 三、邊界（照 1135 §四，重申）

- 只改 `scripts/tasks_board_gen.py`＋其生成輸出。**TASKS.md 係我 DATA LANE，唔准動。**
- 唔准改 `scripts/encrypt_admin_pages.sh`／`tests/encryption_check.py`。

## 四、錨點更新（1135 §五兩個數已漂，以此為準）

- 現頁 `docs/admin/tasks_board.html`：**174,683B／14 sections**（12:47 #31 收項後重生成，65f67bad）——唔係 1135 寫嘅 173,531B/13
- 截圖仍然有效：`/home/alvin/.openclaw/workspace/main/tmp_shots/board_{desk,tab,mob}.png`（11-25 拍）＋`board_now.png`（11-32）
- baseline git-blob8 `223509af`（frontmatter已標演算法＋對象）

## 五、驗收（8 機器閘照 1135 §三逐條重測，唔接受自述）

出貨後本 lane 於 **30 分鐘內**回批（notify watcher 每 3 分鐘掃，已提速）。任何一條 FAIL 即退修；全綠即收項＋board 再生出版。

## 六、收項後跟進

OpenClaw 跑 `tasks_board_publish.sh` 四關＋live 部署＋TASKS.md workable 表收項，全程本 lane 做，你只出 patch。
