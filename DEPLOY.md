# TSA 部署機制 — 必須遵守

## ⚠️ 關鍵事實（2026-10-21 實測更正）

**GitHub Pages 實際上係讀取 `main` 分支嘅 `docs/` 文件夾，唔係 ROOT。**

實測依據（`gh api repos/alvin-forex/trade-strategy-analyzer/pages`）：
```
source: main//docs
url:    https://alvin-forex.github.io/trade-strategy-analyzer/
status: built
```

> 歷史記錄：本文件 2026-06-05 曾寫「Pages 讀 ROOT，唔係 docs」——**該結論係錯的**，已於 2026-10-21 用 GitHub API 實測推翻並更正。
> 今後一切以 Pages API 回傳嘅 `source` 為準，唔好靠記憶。

### 快速自檢（每次部署前 5 秒做完）

```bash
gh api repos/alvin-forex/trade-strategy-analyzer/pages \
  --jq '"source=\(.source.branch)/\(.source.path) status=\(.status)"'
```

## 文件對應表（全部喺 `docs/` 之下）

| 你想改嘅嘢 | 改邊個文件 | 喺邊改 |
|---|---|---|
| TSA 分析工具（上載 CSV、所有 tabs） | `index.html` | `docs/index.html` |
| Dashboard landing page | `dashboard.html` | `docs/dashboard.html` |
| Signal 排名頁面 | `signal_ranking.html` | `docs/signal_ranking.html` |
| CCY 排名頁面 | `admin/ccy_ranking.html` | `docs/admin/ccy_ranking.html` |
| 波幅排名頁面 | `admin/symbol_ranking.html` | `docs/admin/symbol_ranking.html` |
| 後台管理 | `admin/index.html` | `docs/admin/index.html` |
| Signal 分析報告 | `reports/index_{ID}.html` | `docs/reports/index_{ID}.html` |
| Martin V4 報告 | `reports/martin_v4_{ID}.html` | `docs/reports/martin_v4_{ID}.html` |

**Root 底下嘅 `index.html` / `*.html` 唔會上線**，只係舊版殘留，改咗都冇效果。

## 部署流程（每次改動）

```
1. 改 docs/ 入面嘅對應文件
2. git add + commit + git push origin main
3. 等 1-2 分鐘 GitHub Pages build
4. curl 確認 CDN 上線（HTTP 200 + 內容已更新）
5. 通知用戶
```

## ❌ 常見錯誤（不要再犯）

1. ❌ 改 root `index.html` 而唔係 `docs/index.html`（root 唔會上線）
2. ❌ 改 `gh-pages` branch（GitHub Pages 唔讀呢個 branch）
3. ❌ push 到 main 但冇更新 `docs/` 入面嘅文件
4. ❌ 以為 CDN 即時更新（要等 1-2 分鐘）
5. ❌ 憑記憶判斷 Pages 路徑，而唔係查 Pages API

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
