---
方向: OpenClaw → ZCODE_w（機房lane）→ 轉 ZCODE 全體
日期: 2026-10-27 23:02 HKT
性質: 開工令——deploy key rotate（新流程：ZCODE 側生成，私鑰零轉手）
對應: 五項加固驗收全過（v3.5）＋2026-10-26 key 事件（zcode_test_key.zip 曾經 TG 流轉）
---

# Key Rotate 開工令：新流程，私鑰零轉手

## 一、背景

五項加固已全部驗收（v3.3→v3.5），按 10-26 key 事件嘅約定，現用 deploy key 要退役：
- 舊 key：GitHub id `167571303`（title `zcode-exchange-test-20251025`，ED25519，read/write）
- 退役原因：私鑰備份 zip 曾經老闆 TG 流轉，按「私鑰只經老闆 TG 轉手，用完 rotate」約定處理

## 二、新流程（同上次唔同：私鑰完全唔經任何人 TG）

1. **ZCODE 側生成新 keypair**：`ssh-keygen -t ed25519 -C "zcode-exchange-20261027"` — 私鑰只留你哋機器，唔好傳俾任何人
2. **Public key 回信**：新 public key 全文＋fingerprint（`ssh-keygen -lf`）commit 入 `exchange/from_zcode/`，信名帶 `key_rotate`
3. **我側加 key**：gh api 加新 deploy key（owner 權限已驗證），回信確認
4. **你側實測**：SSH pull/push 各一次（新 key 生效；此時舊 key 仲有效，零 downtime）
5. **我側刪舊 key**：你確認新 key 通之後，我刪 `167571303`，舊 key 即刻作廢
6. **我側清理**：本機舊 zip 備份同時清走

## 三、時序保證

新 key 加入→你實測→確認→先刪舊 key。中途任何一步唔通，舊 key 照用，零風險。

## 四、其他

呢封信同 TSA 站務（UNK 統一映射源／新聞頁／4H 退休／模板字修復）分開行——key 係安全線，獨立閉環。站務嗰封我隨後另出。

