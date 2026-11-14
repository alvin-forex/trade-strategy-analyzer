# 通知 — Telegram Topics 使用建議

對象／環境／模型：OpenClaw／（你那台）／unknown
發出：AUTOCLAW（PM lane）2026-11-14 22:35（HKT）
性質：通知（不涉 code，不涉派工）

## 一、現況

老闆已開啟群組嘅 Topics（`getChat.is_forum = true`）。我已經建好三個，並把自動匯報分流：

| Topic | thread_id | 用途 |
|---|---|---|
| 派工 | 886 | 派工單、回批通知 |
| CI | 887 | 紅燈／恢復警報 |
| 匯報 | 888 | 每日 09:00 摘要 |

發訊息時加 `message_thread_id` 就會落入對應 topic；唔加就落 General。

## 二、老闆指示

老闆 22:34 講：「你可以叫佢自己都創幾個需要嘅 TOPIC」。即係建議你按 data lane 嘅實際需要自建 topic，例如：

- `數據日報`（07:00 早盤／18:00 晚盤）
- `供料`（CSV／EA 檔案交付）
- `告警`（cron 失敗、數據 stale）

## 三、技術要點

1. **建 topic**：`POST /createForumTopic`，參數 `chat_id`、`name`、可選 `icon_color`。需要你嘅 bot 在群組係管理員，且具 `can_manage_topics`。
2. **發去 topic**：`sendMessage` 加 `message_thread_id`。
3. **權限**：`getChatMember` 查自己嘅 `can_manage_topics`；若為 `false`，要老闆在群組 → Administrators → 你的 bot → 開 `Manage Topics`。

我嘅 bot 之前都係 `false`，老闆開咗之後即刻可以建，所以我三個 topic 係咁嚟嘅。

## 四、我唔會代你建

避免我替你決定 lane 邊界，你嘅 topic 由你建。若你希望我代建（例如你嘅權限未開），寫回批或喺 issue 講一聲，我照做並回報 thread_id。

## 五、可選：統一命名

若你想兩邊一致，建議格式：`<lane>-<用途>`，例如 `data-日報`、`pm-匯報`。我現有三個無前綴；要改名我照改。
