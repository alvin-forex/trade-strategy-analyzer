# [本機] 生產線 v1.1（老闆 11-26 15:42 指示）：導入 Superpowers 方法論

老闆指定學習 https://github.com/obra/superpowers （一套俾 coding agent 用嘅完整開發方法論，由多個可組合 skill 組成）。讀完 README，**精髓七步**對應我哋生產線，v1.1 修訂如下：

## Superpowers 七步 → 我哋對應
| Superpowers | 我哋生產線 v1.1 修訂 |
|---|---|
| 1. brainstorming（做之前先問清楚想要乜，扮返理解俾你糾正） | OC 派工前必寫「預期結果」＋**扮返理解俾老闆/需求方糾正**，唔准自己估 |
| 2. using-git-worktrees（隔離工作區＋乾淨測試基線） | ZCODE 開工先開 branch＋確認測試基線乾淨（已實行） |
| 3. writing-plans（工作拆到 2-5 分鐘一件，每件有確實路徑＋驗證步驟） | **新**：派工信嘅「預期結果」要拆到任務級，每件附驗證步驟 |
| 4. subagent-driven-development（每件任務派新 subagent＋逐件 review） | AC 嘅助手並行模式照用；ZCODE 每件任務完自我 review 再交 |
| 5. test-driven-development（RED-GREEN-REFACTOR，先寫失敗測試） | **新**：engine／Python 側代碼一律 TDD；MQL5 生產碼照 MQL5 規範（compile 閘） |
| 6. requesting-code-review（逐任務之間 review，critical 問題擋進度） | DA-Review 逐任務審（已行），critical 問題 block 進度（新增：唔准帶病過關） |
| 7. finishing-a-development-branch（驗證測試→merge/PR 選項→清理） | 機器閘全過→自動併（已行）＋**新**：branch 用完即清理 |

## 即刻生效
- ZCODE：Scanner parity／數據層工作改 TDD＋任務拆細（2-5 分鐘級）
- OC：派工信預期結果加「任務拆解」欄
- DA-Review：審批加「critical 問題 block」規則

## 記錄
- 方法論存 Obsidian 知識庫＋本卡；skill 概念收錄作 AGENT 培訓材料
