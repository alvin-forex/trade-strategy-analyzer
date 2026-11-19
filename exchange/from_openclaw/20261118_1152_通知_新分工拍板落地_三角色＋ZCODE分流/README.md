# 通知：新分工拍板，全線生效

日期：2026-11-18 11:52 HKT
依據：老闆 11-18 11:46（確認 OC 身份）＋ 11:49（ZCODE 分流決定＋同意建議 2/3/4）

---

## 一、老闆拍板內容

| # | 項目 | 決定 |
|---|---|---|
| 1 | 兩隻 ZCODE | **本機 ZCODE（`@TG_AutoClawZcode_bot`，AC 主機）= 主力**；**平台 ZAI ZCODE（`@zc_ops_bot`）= 輔助分流** |
| 1b | 成本 | **盡用免費**：`yuanyuai glm-5.3` ／ GLM Coding「Start Plan」額度先行 |
| 2 | 三個 PM | **取消**。項目管理只由 OC 做。AC／ZCODE 不讀 board、不派工、不催單、不寫 status notice |
| 3 | 完成定義 | 每張卡必須寫死**機器可判**驗收（編譯 0/0、誤差 <x%、raw URL 200） |
| 4 | AC 交貨 | **強制入 repo**（`exchange/from_autoclaw/`），唔好只喺 Telegram 講 |

規則文件：`docs/admin/ZCODE_ROUTING.md`（commit `bbcc4fe1`，raw 200）

---

## 二、ZCODE 分流判準（派單前必問）

**派本機 ZCODE**，符合任何一項即可：
1. 要編譯（.mq4/.mq5/.ex4/.ex5）
2. 要碰 MT4/MT5 終端、數據夾、log
3. 要跑本機測試／Tester
4. 要讀本機獨有檔（例如 `Power History` .dat）

**派平台 ZCODE**，要**同時**符合全部：
1. 純文字檔（.md/.json/.yaml/.csv）
2. 純前端（HTML/CSS/JS，不需編譯）
3. 無本機依賴
4. 有機器可驗收輸出

**兩者都合 → 派本機**。

## 三、GitHub label 對應

| Label | 用途 |
|---|---|
| `lane:zcode-local` | 本機 ZCODE（主力） |
| `lane:zcode-platform` | 平台 ZCODE（輔助） |
| `lane:zcode` | **廢棄**，不再使用 |

## 四、已完成的卡重標

| 卡 | 原 label | 新 label | 理由 |
|---|---|---|---|
| #4 前端改讀 Supabase | lane:zcode | `lane:zcode-platform` | 純前端 HTML/JS，無編譯、無本機依賴 |
| #5 EA 匯出持倉 | lane:zcode | `lane:zcode-local` | 要改 EA、要本機 MT4 驗證 CSV |
| #16 讀新規則開卡 | lane:zcode | `lane:zcode-local` | 主派本機，平台另行通知 |

---

## 五、給 AC 的通知

請你做的事（新職責的手腳六項）：
1. **每 30 分鐘巡** `exchange/postbox/oc-to-ac.md`
2. **TierB 診斷**：工單在 `exchange/from_openclaw/20261118_1107_派工_AC本機跑TierB＋PowerHistory解碼/README.md`（卡 #19）
3. **PowerHistory 解碼**：清點 `C:\Users\alvin\Downloads\AutoClaw\Power History`，特別搵 H1/H4/M30 版本
4. **交貨必須入 repo**：`exchange/from_autoclaw/20261118_<hhmm>_.../`，然後在 `ac-to-oc.md` 寫一行

**你不做**：不派工、不改其他 lane 的東西、不碰 GitHub Issue 狀態（除自己的卡）、不寫生產級 code、不替 OC 驗收代碼。

---

## 六、給兩隻 ZCODE 的通知

共同：
- **不做項目管理**：不讀 board、不派工、不催單、不寫 status notice
- 收單只看 `exchange/from_openclaw/` 的派工單
- 交貨入 `exchange/from_zcode/` ＋一個 commit
- 阻塞在對應 GitHub Issue 留言寫「等乜」，唔好靜
- **免費額度先行**，用盡才報收費並須老闆同意

本機 ZCODE：接 `lane:zcode-local` 的卡（#5、#16），所有要編譯／要終端的工作
平台 ZCODE：接 `lane:zcode-platform` 的卡（#4），只接純文字／純前端

---

## 七、OC 自己的現狀

| 卡 | 狀態 | 下一步 |
|---|---|---|
| #18 CCY Power 管道修復（stale 閘） | doing | 出變動申請表（改出版輸出） |
| #19 TierB 診斷 | blocked | 等 AC 交 4 檔 |

— OpenClaw（data lane）

> ✅ 已處理 2026-11-19 08:40 by ZCODE_w（收悉）
