# 派工：跨頁密碼 remember 分層修復（P6 B 案落地版）

> 老闆 2026-11-04 11:38 裁定：「由一般頁去 ADMIN 頁又要再打密碼，這問題要修正」
> 分工：ZCODE（CODE LANE：staticrypt template＋加密閘）／OpenClaw（獨立驗收＋上線）

## 根因（OpenClaw 已實證）
- 全部加密頁 staticrypt wrapper 用**同一個** localStorage key 記密碼：
  \`setItem(rememberPassphraseKey, hashedPassword)\`（docs/index.html 實測）
- general 層（TSA_PW）與 owner 層（TSA_OWNER_PW）密碼不同，但「記住」只有一個位
- 登入 admin（owner pw）→ 覆蓋 general 記住的 pw → 返回一般頁要重打；來回每次都要

## 修復規格
1. \`scripts/staticrypt/password_template_zh.html\` ＋ \`password_template_dark.html\`：
   - rememberPassphraseKey／rememberExpirationKey 加層別後綴
   - 判定：\`location.pathname.indexOf('/admin/') >= 0 ? '_owner' : '_general'\`（Pages 下 admin 頁全在 /trade-strategy-analyzer/admin/）
   - 全部 getItem/setItem/removeItem 一致套用
2. \`scripts/encrypt_admin_pages.sh\`：行為不變（remember 30 日），驗證段加一項——產出頁按 OWNER_PAGES 名單含對應 \`_owner\`/\`_general\` 後綴
3. 重加密全部 15 核心頁＋commit

## 驗收（OpenClaw 獨立跑）
- 同一 browser：general 頁登入（記住）→ admin 頁登入（記住）→ 返回 general 頁**零重打**
- localStorage 同時存在兩條 key（_general／_owner）
- CI encryption_check 6/6 照過；remember 天數 30 不變

## 紅線
- 唔統一密碼（兩層制保留）；唔改 remember 天數；唔改加密演算法
