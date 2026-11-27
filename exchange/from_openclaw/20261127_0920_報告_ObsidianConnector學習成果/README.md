# [本機] Obsidian Connector 學習報告（老闆 11-27 09:17 指示）

## 係乜
Obsidian 官方 11-25 剛發佈 **Connectors**：一組 MIT 開源 skill（github.com/obsidianmd/obsidian-skills），俾 AI agent 讀寫 vault，支援 Claude／ChatGPT／Cursor／Copilot／Grok／Hermes 等。教你 agent：
- 用 Obsidian 格式寫筆記（wikilinks／embeds／properties）
- 整 Bases 同 Canvas 檔
- 用 **Obsidian CLI** 搜尋／讀寫運行中 app 入面嘅筆記
- 用 **Obsidian Headless**（冇 desktop app 都同步／發佈 vault）

## 我哋點用（改善現有記憶／知識管理）
1. **OC（即刻）**：已有 obsidian-vault-maintainer skill＋obsidian-sync cron（知識庫/工作日誌已鏡像）。升級：裝 obsidian-skills 學官方格式（wikilinks／frontmatter／Bases），令 vault 由「鏡像」升級做「真正 Obsidian 結構」（可內鏈跳轉）
2. **AC／ZCODE／DA-Review**：照官方 connector 各自裝 skill，共用同一個 vault（知識庫），實現「一個知識庫多 agent 共寫」——就係老闆「知識先行」嘅理想形態
3. **Headless**：之後 VPS／雲端 agent 都可以直接接 vault，唔使搬檔案

## 派工
- OC：今晚研究 obsidian-skills repo，出導入腳本（vault 升級 Wikilinks／frontmatter）
- AC／ZCODE：收到 OC 導入指引後各自裝 skill（每個 marketplace 搜 "Obsidian"）
- 老闆：你個 Obsidian app 升級到最新版就有 Connectors 支援
