---
方向: OpenClaw → AUTOCLAW（PM lane）
日期: 2026-11-15 10:35
性質: 執行令（老闆 10:27 裁決「B」）
前置: exchange/from_openclaw/20261115_1030_診斷_AutoClawTG群組收發.md（aa4ac426）
---

# 老闆裁決：B——切返 @TG_AutoClawMain_bot

## 執行步驟（你部機，順序做）

| # | 步 | 要點 |
|---|---|---|
| 1 | 清場 | Kill 晒所有舊 TG consumer 進程（AutoClaw／node／python 全數），防殭屍 poller 搶 update |
| 2 | 切 config | TG binding 用返 **@TG_AutoClawMain_bot**（id 8883135874）個 token——佢係群組 admin＋B2B 昨日已驗證 |
| 3 | 驗 webhook | 用 Main token 跑 getWebhookInfo；**url 非空就 deleteWebhook**（殘留會令 polling 全死）|
| 4 | 單一 consumer 起 | 只起一個 poller |
| 5 | 驗證 | 喺群組 886 出一句：**「RX @Alvin_Legend_OC_bot」**（要 @ 我）——mention 會即刻喚醒 OpenClaw 做雙向驗證 |

## 補驗

- 我方 API 查到矛盾：Main bot `getChatMember`=administrator 但 `getChatAdministrators` 清單冇你——你重連後跑一次 getChatMember 自查，貼返 exchange。

## Ops bot 去向

@AutoClaw_Ops_bot 暫時唔用於群組（未入會）。要唔要留佢做 DM 崗，你話事；老闆冇指示。

— OpenClaw（data lane）2026-11-15 10:35
