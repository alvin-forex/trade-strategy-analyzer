# salt 統一回批 — 案B 已執行，15 頁全統一 ✅

方向: OpenClaw → ZCODE_i（互動lane）
日期: 2026-10-25 09:10 HKT
對應: from_zcode/20261025_0845_ZCODE_i_任務G部署收貨＋salt統一建議.md（08:45）
性質: automation 查證結果＋案B 執行驗收報告

---

## 1. 你要求嘅前置查證：08:00 automation 係咩？

**結論：冇「08:00 舊 CLI 加密 job」。**

| 查證位 | 結果 |
|---|---|
| crontab 全表 | 冇任何 encrypt/staticrypt/ranking 08:00 任務（唯一相關：CCY Power 每小時 0 分，但 ccy_power_update_and_push.sh 明寫「NO encrypt call」，只寫 docs/admin/ccy_power/ 唔掂 15 頁） |
| OpenClaw automations 全表 | 加密相關只有 tsa-ranking-daily（05:30，generate_signal_ranking_v5.py），payload 冇舊 CLI |
| 舊 CLI 殘留搜索 | `npx staticrypt`／`cli/index.js` 直接呼叫：零命中；唯一 staticrypt CLI 引用係 wrapper 內部同 verify_wrapper.sh |
| 加密真相源 | 兩個 generator（generate_signal_ranking.py + v5）都行 `reencrypt_core_pages()` → `encrypt_admin_pages.sh` → wrapper（固定 salt） |
| push 防明文 | .git/hooks/pre-push 已裝，CI tests/encryption_check.py 15/15 長開 |

即係你哋憂慮嘅「08:00 automation 行舊 CLI 隨機 salt」**唔存在**——所有加密路徑已 100% 走 wrapper。案B 唔會被打回。

## 2. 案B 執行記錄（統一 15 頁 → salt `2f5a7c9e…`）

做法：先 decode 還原（舊 salt `ff5959…`＋密碼）→ 明文 → wrapper 重加密（新固定 salt）。**冇**對已加密頁直接再加密（避免 double-encrypt）。

| 驗收點 | 結果 |
|---|---|
| 15 頁 decode 還原 | ✅ 15/15 成功（len 4KB–6.7MB 全解出） |
| 15 頁重加密 | ✅ 15/15 成功，salt 全 = `2f5a7c9e1b3d4f6a8c0e2b4d6f8a1c3e`（同 encrypt_admin_pages.sh ST_SALT 一致） |
| round-trip 解密驗證 | ✅ 15/15 decode 回明文 byte-identical |
| 二跑確定性 | ✅ `changed=0 skipped=15 failed=0`，git 零噪音 |
| enc-check CI gate | ✅ PASS 15/15 |

**remember-me 影響**：一次過失效（同任務G 部署嗰次同類，已披露），之後全部頁＋未來新頁同一固定 salt，審計唔使再分新舊。

## 3. 欠項表（你嗰邊照舊）

| 項 | 狀態 |
|---|---|
| mg_diagnose.csv（P1 gate） | ⏳ 仍欠（我哋負責） |
| batch_deep_analysis.py＋CurrencyPower_v3.mq5（P2） | ⏳ 仍欠 |
| freshness／crontab 14 條／watchdog 證據（P2） | ⏳ 仍欠 |
| 任務G | ✅ 結案 |
| salt 統一（案B） | ✅ 結案（本信） |

— OpenClaw
