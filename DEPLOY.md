# TSA 部署機制 — 必須遵守

## ⚠️ 關鍵事實（2026-06-05 更正）

**GitHub Pages 讀取 `main` 分支嘅 ROOT 文件夾（`/`），唔係 `docs/`！**

之前 DEPLOY.md 講錯咗，已於 2026-06-05 更正。

## 文件對應表

| 你想改嘅嘢 | 改邊個文件 | 喺邊改 |
|---|---|---|
| TSA 分析工具（上載 CSV、所有 tabs） | `index.html` | `main` branch root |
| Dashboard landing page | `dashboard.html` | `main` branch root |
| Signal 排名頁面 | `signal_ranking.html` | `main` branch root |
| CCY 排名頁面 | `admin/ccy_ranking.html` | `main` branch root |
| 波幅排名頁面 | `admin/symbol_ranking.html` | `main` branch root |
| 後台管理 | `admin/index.html` | `main` branch root |
| Signal 分析報告 | `reports/index_{ID}.html` | `main` branch root |
| Martin V4 報告 | `reports/martin_v4_{ID}.html` | `main` branch root |

## 部署流程（每次改動）

```
1. 改 main branch 嘅 docs/xxx.html
2. git add + commit + git push origin main
3. 等 1-2 分鐘 GitHub Pages build
4. curl 確認 CDN 上線
5. 通知用戶
```

## ❌ 常見錯誤（不要再犯）

1. ❌ 改 root `index.html` 但唔同步到 `docs/index.html`
2. ❌ 改 `gh-pages` branch（GitHub Pages 唔讀呢個 branch）
3. ❌ push 到 main 但冇更新 `docs/` 入面嘅文件
4. ❌ 以為 CDN 即時更新（要等 1-2 分鐘）

## 驗證指令

```bash
# 確認線上版本
curl -s "https://alvin-forex.github.io/trade-strategy-analyzer/" | grep "APP_VERSION"
curl -s "https://alvin-forex.github.io/trade-strategy-analyzer/" | grep "tab-news"

# 確認 git 狀態
cd ~/.openclaw/workspace/trade_strategy_analyzer
git log --oneline -3 main
```

## Git Branch 說明

- `main` — **唯一嘅 production branch**，GitHub Pages 從呢度嘅 `docs/` 讀取
- `gh-pages` — 已過時，唔好再用，可以安全忽略
- `uat/dde-v5-optimization` — UAT branch，唔影響 production

---
*建立日期：2026-05-29 by 丁蟹 🦀*
*原因：避免再次出現改錯 branch / 改錯路徑嘅問題*
