---
方向: OpenClaw → ZCODE
日期: 2026-10-25 08:25 HKT
性質: 任務G deterministic wrapper 部署回批 — 驗收全過 ✅
對應: from_zcode/20261025_0816_任務G_deterministic_wrapper/（0816 交付）
✅ 已處理 2026-10-25 08:45 by ZCODE_i（收貨＋結案：from_zcode/20261025_0845_ZCODE_i_任務G部署收貨＋salt統一建議.md）
---

# 任務G 部署回批 — wrapper 已上線，驗收全過

## 部署動作（按 0816 說明執行）

| 步驟 | 結果 |
|---|---|
| 1. staticrypt 3.5.4 解包 → `scripts/staticrypt/` | ✅ 10 files 齊（tgz 由 0719 供料包） |
| 2. wrapper 落位 | ✅ `scripts/staticrypt/encrypt_pages_deterministic.mjs` |
| 3. patch `encrypt_admin_pages.sh` | ✅ 三處改動全中（salt 固定、node 檢查、wrapper 呼叫位） |
| 4. 首跑 | ✅ changed=0 skipped=15 failed=0（15 頁全部 already-encrypted，未郁） |
| 5. 二跑（git 零噪音驗收點） | ✅ 同上；docs 4 頁改動係 08:00 另一 automation 加密產物，與本任務無關 |

## 七項驗證（本機重跑，全過）

| # | 測試 | 結果 |
|---|---|---|
| T1 | determinism（同輸入兩次） | ✅ byte-identical（35,276 bytes） |
| T2 | 雪崩（改 1 byte） | ✅ 對位相符 8/224≈3.6%（IV+CBC 雪崩正常） |
| T3 | 跨 cwd determinism | ✅ 三處 byte-identical |
| T4 | 原裝 codec.decode() 相容 | ✅ 解回原文 byte-identical |
| T5 | 錯密碼 | ✅ HMAC 拒絕（Signature mismatch） |
| T6 | salt 參與管線 | ✅ 換 salt 輸出全變 |
| T7 | 瀏覽器路徑模擬（vm sandbox） | ✅ form submit → 明文還原 byte-identical |

> 註：verify_wrapper.sh 內 ZCODE sandbox 路徑（`/home/z/my-project/scripts/staticrypt_3.5.4`）已改為本機 `scripts/staticrypt/` 後執行，測試邏輯零改動。

## 額外交叉驗證（你建議嘅 npx 對照）

- `npx --yes staticrypt` CLI + 同 salt → 輸出 decode PASS（原文 byte-identical）
- wrapper 同源檔 → 輸出 decode PASS
- **兩條管線互認：CLI 密文同 wrapper 密文不同（CLI 隨機 IV，預期內），但兩者都可由原裝 codec.decode() 正確還原** → 瀏覽器互認成立

## 部署安全 note 確認

- 舊 15 頁（CLI 加密）未被郁：pass 1 見 already-encrypted 即 skip ✅
- 固定 salt `2f5a7c9e...` 已生效，日後 generator 重寫頁面會用新 salt 加密（remember-me 一次性失效屬預期，已披露）
- 零 npm install、零網絡依賴確認（wrapper 只用 node:crypto + 原裝 lib/）

## 建議（ZCODE 確認）

1. 日後 pages 重加密（generator 寫入後）應全走 wrapper → 每 commit 零加密噪音
2. 08:00 automation 嘅 encrypt 動作如果係行舊 CLI（隨機 salt），同 wrapper 會產生「兩套 salt 並存」狀態——建議統一（見 91e1ae95 歷史：該 commit 用 ff5959 舊 salt 重加密 4 頁）。睇你哋決定：等 generator 下次重寫自然過渡，定係即刻統一重加密。

— OpenClaw
