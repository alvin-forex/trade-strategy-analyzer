> **本單零阻塞，即刻開工。** 內文出現嘅卡片名一律係版面元素，唔係等你或等老闆嘅標記。

# 派工：tasks_board 排版重構（老闆 2026-11-14 11:13「排版很難看」）

## 一、問題陳述（全部係本機 Playwright 1440×1100 實測數字，唔係感覺）

| 量測項 | 現值 | 問題 |
|---|---|---|
| board 總寬 | 1240px（12 欄 grid） | — |
| 進行中卡 | span 7 = **717px 寬，1327px 高** | 17 行全部堆一張卡，佔全頁 30% |
| 進行中 行 grid | `26px \| 205px \| 1fr(330px) \| 82px` | **任務欄 205px 窄過狀態欄 330px**——任務名係主內容卻最窄，`排名雙頁 KPI（原 Phase 3.1 投影 6 欄）｜OpenClaw＋ZCODE（#2）` 一行斷成 3 行 |
| 單行高 | 66–89px | 17 行×66 ≈ 1.1 屏 |
| 右側欄 | owner 待覆卡 507×480、待做卡 507×212 | 兩卡相加 708px，**對比左側 1327px 留下約 600px 空白洞** |
| 已完成卡 | **7 張獨立卡，每張 82px** | 7 個碎片，每張只有標題＋計數，資訊密度近零 |
| 全頁高度 | **4468px** | 要碌 4.5 屏 |
| KPI 六格 | 進行中17／等你7／待做3／已排程6／已完成60／其他21 | 「其他 21」冇對應卡，語義不明 |
| `#` 欄 | 1,2,3…17 順序號 | 同任務真 ID（#2/#6/#14/#16/#18/#27…）**完全唔對應**，睇板會搵錯行 |

## 二、要改嘅六項（按優先次序）

### L1（必做）任務欄放寬、狀態欄收窄
`.row` grid 由 `26px minmax(0,205px) minmax(0,1fr) 82px` 改為
`34px minmax(0,1fr) minmax(0,300px) 92px`。
理由：任務名係掃讀主軸，狀態已有 `_concl_split` 抽結論＋`<details>` 摺內文，唔需要 330px 常駐。

### L2（必做）進行中卡改全寬、右側兩卡合併
- `.card--active` span 7 → **span 12**
- owner 待覆卡(span5) ＋ 待做卡(span5) 合併成一張「⏸ 待覆／待做」span 6，放喺 進行中 之下
- `已排程` span 7 → span 6，與上卡並排
效果：消滅右側 600px 空洞。

### L3（必做）已完成七卡合一
`.card--done` 七張 → 一張「✅ 已完成（按日期分組）」，組內每組用 `<details><summary>11-13／11-14 收項（6）</summary>`。
理由：預設收合，7×82px 碎片變 1 張 ~90px 卡，展開才見詳情。

### L4（必做）`#` 欄顯示真任務 ID
生成器 `for i, r in enumerate(data, 1)` 改為讀第一格真值：`idx_text = r[0]`，渲染 `r[0]`（`2`／`16`／`FIX-TD`）。
理由：`enumerate` 假號同真 ID 並存會令「#4 係 XAU timing」嘅口頭溝通全部對錯行。**本項係 bug fix，不只美觀。**

### L5（建議）狀態格預設只顯示結論
`_render_state_cell` 已有 concl/fdb 分離，但 `total <= 70` 時唔摺。改成**一律摺**（concl 一行＋details），令行高由 66-89px 降到 ~44px 穩定。
量測目標：進行中 17 行高度 ≤ 850px（現 1327px）。

### L6（建議）KPI 補「其他」定義或移除
「其他 21」冇對應卡片。要麼歸入已完成，要麼移除該格改為 5 格 grid。

## 三、驗收標準（我會逐條機器量測，唔接受自述）

1. `.row` computed `grid-template-columns` 第一欄 ≥ 320px（1440px viewport）
2. 進行中卡 `gridColumn` == `span 12`
3. 已完成卡数量 == 1
4. 進行中表 `#` 欄文字 == TASKS.md 第一格原值（抽 3 行對：16／27／FIX-TD）
5. 進行中 17 行總高 ≤ 900px
6. `document.documentElement.scrollHeight` ≤ 3200px（現 4468px）
7. 390px viewport：`scrollWidth - innerWidth` == 0（零橫向溢出）
8. 解密閘：`bash scripts/tasks_board_publish.sh` 四關全 PASS、0 dead links

## 四、邊界

- 只改 `scripts/tasks_board_gen.py`（CODE LANE 屬你）。**TASKS.md 係我 DATA LANE，唔准動。**
- 唔准改 `encrypt_admin_pages.sh`／`tests/encryption_check.py`。
- 出貨後我會跑上面 8 條機器閘，任何一條 FAIL 即退。

## 五、參考

- baseline：`scripts/tasks_board_gen.py` @ `4ac3ab93`
- 現頁：`docs/admin/tasks_board.html`（173,531B，13 sections）
- 截圖：`/home/alvin/.openclaw/workspace/main/tmp_shots/board_desk.png`（1440）、`board_tab.png`（900）、`board_mob.png`（390）

> ⏳ 進行中 2026-11-14 12:40 by ZCODE_w（收執——本單 tasks_board_gen.py 生成器重構＋頁面重構屬大型交付，照協議歸 ZCODE_i 出貨；w lane 轉介不搶工，已匯報老闆＋記 worklog，等 i lane 接單）
