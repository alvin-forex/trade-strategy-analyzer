# PRD: MT4 多帳戶實時監控系統 (MT4 Multi-Account Monitor)

> **版本**: v1.0  
> **日期**: 2026-05-29  
> **作者**: 丁蟹 (OpenClaw AI)  
> **狀態**: 🟡 待批核  

---

## 1. 背景與動機

老闆運行多個 MT4 帳戶（至少 2 個 Terminal），目前無法即時掌握所有帳戶的整體狀況。需要一個系統可以：

- 即時監控多個 MT4 帳戶的餘額、淨值、持倉
- 追蹤開倉/平倉/修改等交易事件
- 通過 Telegram 推送重要通知
- 提供網頁 Dashboard 總覽

### 現有基礎設施

| 組件 | 現況 |
|---|---|
| MT4 Terminal 1 | `A06E6395` — Vantage Live 11, River+Power profile |
| MT4 Terminal 2 | `F1BBCAACD` — 另一個 Vantage 帳戶 |
| ForexDataExporter EA | v3.00 — 已導出 29 pairs 技術數據到 CSV |
| OpenClaw | 運行中，支援 Telegram 推送 |
| Python 環境 | WSL2 Ubuntu, yfinance, pandas 等已安裝 |
| GitHub Pages | `alvin-forex.github.io/trade-strategy-analyzer` |

---

## 2. 系統架構

```
┌──────────────┐    ┌──────────────┐
│  MT4 Terminal │    │  MT4 Terminal │
│  (Account 1)  │    │  (Account 2)  │
│               │    │               │
│ AccountMonitor│    │ AccountMonitor│
│     EA        │    │     EA        │
└──────┬───────┘    └──────┬───────┘
       │ CSV/HTTP          │ CSV/HTTP
       ▼                   ▼
┌─────────────────────────────────┐
│   Python Monitor Service        │
│   (WSL2 Background Process)     │
│                                 │
│  ┌──────────┐  ┌──────────────┐ │
│  │ CSV Watcher│  │ Account State│ │
│  │ (watchdog) │  │  Aggregator  │ │
│  └──────────┘  └──────────────┘ │
│  ┌──────────┐  ┌──────────────┐ │
│  │ Event     │  │ Telegram     │ │
│  │ Detector  │  │ Notifier     │ │
│  └──────────┘  └──────────────┘ │
│  ┌──────────┐  ┌──────────────┐ │
│  │ History   │  │ Web Dashboard│ │
│  │ DB(SQLite)│  │ (FastAPI)    │ │
│  └──────────┘  └──────────────┘ │
└─────────────────────────────────┘
       │                    │
       ▼                    ▼
┌──────────────┐   ┌──────────────┐
│  Telegram    │   │  Web UI      │
│  Push Notify │   │  Dashboard   │
└──────────────┘   └──────────────┘
```

---

## 3. 功能需求

### 3.1 MT4 EA 端：AccountMonitor.mq4

**職責**：在每個 MT4 Terminal 上運行，定期導出帳戶數據。

#### 導出數據（account_state.csv）

| 欄位 | 類型 | 說明 |
|---|---|---|
| `timestamp` | datetime | 導出時間 |
| `account_id` | string | 帳戶標識（自定義名稱） |
| `login` | int | MT4 登入帳號 |
| `broker` | string | Broker 名稱 |
| `balance` | double | 帳戶餘額 |
| `equity` | double | 淨值 |
| `margin` | double | 已用保證金 |
| `free_margin` | double | 可用保證金 |
| `margin_level` | double | 保證金比率 (%) |
| `profit` | double | 浮動盈虧 |
| `currency` | string | 帳戶貨幣 (USD/EUR等) |
| `leverage` | int | 槓桿比例 |
| `open_positions` | int | 持倉數量 |
| `pending_orders` | int | 掛單數量 |

#### 導出數據（account_positions.csv）

| 欄位 | 類型 | 說明 |
|---|---|---|
| `timestamp` | datetime | 導出時間 |
| `ticket` | int | 訂單編號 |
| `symbol` | string | 貨幣對 |
| `type` | string | BUY/SELL |
| `lots` | double | 手數 |
| `open_price` | double | 開倉價 |
| `current_price` | double | 現價 |
| `sl` | double | 止損 |
| `tp` | double | 止盈 |
| `profit` | double | 浮動盈虧 |
| `swap` | double | 隔夜利息 |
| `commission` | double | 手續費 |
| `open_time` | datetime | 開倉時間 |
| `magic_number` | int | EA Magic Number |
| `comment` | string | 訂單備註 |
| `pips` | double | 浮動點數 |

#### 導出數據（account_history.csv）

| 欄位 | 類型 | 說明 |
|---|---|---|
| `ticket` | int | 訂單編號 |
| `symbol` | string | 貨幣對 |
| `type` | string | BUY/SELL |
| `lots` | double | 手數 |
| `open_price` | double | 開倉價 |
| `close_price` | double | 平倉價 |
| `open_time` | datetime | 開倉時間 |
| `close_time` | datetime | 平倉時間 |
| `profit` | double | 盈虧 |
| `swap` | double | 隔夜利息 |
| `commission` | double | 手續費 |
| `magic_number` | int | EA Magic Number |
| `comment` | string | 訂單備註 |

#### EA 參數

| 參數 | 預設值 | 說明 |
|---|---|---|
| `ExportIntervalSeconds` | 30 | 導出頻率（秒） |
| `AccountLabel` | "" | 帳戶自定義名稱 |
| `ExportPath` | "MQL4/Files/" | 導出路徑 |
| `EnableTelegram` | true | 是否通過 HTTP 發送到 Python |

#### 導出頻率
- **account_state**: 每 30 秒
- **account_positions**: 每 30 秒（同 state）
- **account_history**: 每 60 秒（只導出今日新增的平倉記錄）

### 3.2 Python 監控服務

#### 3.2.1 CSV 監控器 (File Watcher)
- 使用 `watchdog` 監聽 MT4 MQL4/Files/ 目錄
- 偵測 CSV 文件變更時即時讀取
- 支援多個 Terminal 路徑同時監聽

#### 3.2.2 帳戶狀態聚合器
- 合併多個帳戶的數據
- 計算總餘額、總淨值、總浮動盈虧
- 計算每個帳戶的日盈虧、週盈虧、月盈虧

#### 3.2.3 事件偵測器
偵測以下事件並觸發通知：

| 事件 | 觸發條件 | 優先級 |
|---|---|---|
| 🟢 **新開倉** | positions CSV 出現新 ticket | Normal |
| 🔴 **平倉** | position 消失 + history 出現新記錄 | Normal |
| 🟡 **掛單觸發** | pending → open | Normal |
| ⚠️ **保證金警告** | margin_level < 150% | High |
| 🚨 **保證金危險** | margin_level < 120% | Critical |
| 📊 **大額浮動** | 單筆 profit 變化 > $100 | Normal |
| 💰 **餘額變動** | balance 改變（平倉結算） | Normal |
| 🔌 **斷線** | CSV 超過 5 分鐘未更新 | Critical |

#### 3.2.4 Telegram 推送

**推送格式**（參考 Telegram HTML）：

```
🟢 新開倉 - Account 1
━━━━━━━━━━━━━━━
📊 EURUSD | BUY 0.10 lot
💰 開倉價: 1.16461
🛡️ SL: 1.16000 | TP: 1.17000
🤖 EA: #12345 (CCY Power)
⏰ 2026-05-29 14:30:00
```

```
📊 每日總結 - 2026-05-29
━━━━━━━━━━━━━━━
🏦 Account 1: $10,250.00 (+$250.00)
🏦 Account 2: $5,120.00 (+$120.00)
━━━━━━━━━━━━━━━
💰 總資產: $15,370.00
📈 今日盈虧: +$370.00
📊 持倉數: 5 | 勝率: 60%
```

**通知頻道**：
- 即時事件 → Telegram 私人聊天
- 每日總結 → 每天 23:00 HKT 自動推送
- 保證金警告 → 即時推送 + 重複提醒（每 5 分鐘直到恢復）

### 3.3 Web Dashboard

#### 頁面結構

| 頁面 | 路徑 | 功能 |
|---|---|---|
| **總覽** | `/admin/account_monitor.html` | 所有帳戶總覽 |
| **帳戶詳情** | `/admin/account_detail.html?id=1` | 單個帳戶詳情 |
| **持倉列表** | 內嵌 | 所有帳戶持倉 |
| **歷史記錄** | 內嵌 | 平倉歷史 |
| **圖表分析** | 內嵌 | 盈虧曲線、持倉分佈 |

#### 總覽 Dashboard 內容

```
┌─────────────────────────────────────────────────┐
│ 📊 MT4 多帳戶監控總覽          Last Update: 14:30│
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ 總資產    │  │ 今日盈虧  │  │ 總持倉數  │      │
│  │ $15,370  │  │ +$370    │  │ 5 個     │      │
│  │ ↑2.5%    │  │ ↑1.0%   │  │          │      │
│  └──────────┘  └──────────┘  └──────────┘      │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │ 帳戶狀態卡片                              │   │
│  │ ┌──────────────┐ ┌──────────────┐        │   │
│  │ │ Account 1     │ │ Account 2     │        │   │
│  │ │ $10,250      │ │ $5,120       │        │   │
│  │ │ Equity: $10,300│ │ Equity: $5,140│       │   │
│  │ │ Margin: 35%  │ │ Margin: 22%  │        │   │
│  │ │ Positions: 3 │ │ Positions: 2 │        │   │
│  │ │ Today: +$250 │ │ Today: +$120 │        │   │
│  │ └──────────────┘ └──────────────┘        │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │ 活躍持倉                                  │   │
│  │ Symbol  Type  Lots  Price   P/L   Acct   │   │
│  │ EURUSD  BUY   0.10  1.164  +$25  Acc1   │   │
│  │ GBPUSD  SELL  0.05  1.344  -$10  Acc1   │   │
│  │ XAUUSD  BUY   0.01  4502   +$50  Acc2   │   │
│  └──────────────────────────────────────────┘   │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │ 今日盈虧曲線 (折線圖)                      │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

#### UI 風格
- 深色主題（與現有 TSA admin 頁面一致）
- 響應式設計（手機優先）
- 自動刷新（每 30 秒）
- 紅綠色表示盈虧

### 3.4 數據存儲

使用 SQLite 存儲歷史數據：

```
data/
├── account_monitor.db
│   ├── tables:
│   │   ├── account_states     (每 30s 快照)
│   │   ├── positions          (持倉快照)
│   │   ├── trade_history      (平倉記錄)
│   │   ├── events             (事件日誌)
│   │   └── daily_summaries    (每日統計)
```

#### 數據保留策略
- **即時數據**: 保留 7 天（每 30 秒）
- **小時聚合**: 保留 90 天
- **日聚合**: 永久保留
- **事件日誌**: 永久保留
- **平倉歷史**: 永久保留

---

## 4. 技術規格

### 4.1 MT4 EA

```
語言: MQL4
檔案: AccountMonitor.mq4
大小估計: ~20KB
依賴: 無外部依賴
兼容: MT4 Build 1240+

導出方式：HTTP POST（主）+ CSV 輪替寫入（fallback）
- 主通道：WebRequest() POST JSON 到 localhost:8788/api/account
- Fallback：account_state_01.csv → 寫完 → rename → account_state.csv
- history 匯出範圍：可配置（預設今日，首跑同步 30 日）
- 定時器：EventSetTimer(30) 唔用 OnTick()
```

### 4.2 Python 服務

```
語言: Python 3.12+
框架: FastAPI (Web) + HTTP API + 記憶體快取
數據庫: SQLite 3 (WAL 模式)
依賴:
  - fastapi
  - uvicorn
  - httpx (Telegram API)
  - jinja2 (HTML templates)
  - （不使用 pandas，改用 csv.DictReader）

進程管理: systemd
資源限制: CPU 50%, Memory 256MB
```

### 4.3 部署架構

```
Process Manager: systemd 或 supervisord
端口: FastAPI → localhost:8788
數據目錄: /home/alvin/.openclaw/workspace/trade_strategy_analyzer/data/
Web 目錄: /home/alvin/.openclaw/workspace/trade_strategy_analyzer/docs/admin/
```

### 4.4 與現有系統整合

| 整合點 | 方式 |
|---|---|
| OpenClaw | 通過 session_send / cron 觸發每日總結 |
| Telegram | 直接使用 OpenClaw message 工具推送 |
| TSA Dashboard | 新增 sidebar 項目「帳戶監控」 |
| GitHub Pages | Dashboard HTML 推送到 repo |
| MT4 ForexDataExporter | 共用 MQL4/Files/ 目錄 |

---

## 5. 實施計劃

### Phase 1: MVP（預計 4-5 天）

| 步驟 | 工作內容 | 時間 |
|---|---|---|
| 1.1 | 開發 AccountMonitor.mq4 EA（HTTP POST + OnTimer） | 4h |
| 1.2 | 開發 FastAPI 接收 HTTP POST | 2h |
| 1.3 | CSV Fallback（輪替寫入） | 2h |
| 1.4 | SQLite 設計 + WAL 模式 + 記憶體快取 | 3h |
| 1.5 | Telegram 推送 + PriorityQueue 排隊 | 4h |
| 1.6 | 靜音時段 + 通知分級 | 3h |
| 1.7 | systemd 配置 + 基本測試 | 2h |

**MVP 交付物**：
- EA 安裝到兩個 Terminal（HTTP POST）
- Python 服務 systemd 運行
- Telegram 推送：開倉/平倉/保證金警告/斷線
- 靜音時段功能

### Phase 2: Web Dashboard（預計 3 天）

| 步驟 | 工作內容 | 時間 |
|---|---|---|
| 2.1 | FastAPI 後端 API + 記憶體快取 | 3h |
| 2.2 | Web Dashboard 前端（桌面優先） | 4h |
| 2.3 | 手機端優化（卡片佈局） | 2h |
| 2.4 | 整合到 TSA sidebar | 1h |

**Phase 2 交付物**：
- 網頁總覽 Dashboard（localhost:8788）
- 持倉列表頁
- 歷史記錄頁
- 手機端響應式 UI

### Phase 3: 進階功能（預計 2 天）

| 步驟 | 工作內容 | 時間 |
|---|---|---|
| 3.1 | 盈虧曲線圖表 | 3h |
| 3.2 | 保證金監控 + 斷線偵測（HTTP 超時 5 分鐘） | 2h |
| 3.3 | 遠端 Dashboard 訪問方案 | 3h |
| 3.4 | 效能優化 + 日誌 | 1h |

**Phase 3 交付物**：
- 盈虧曲線圖表
- 斷線即時通知
- 遠端 Dashboard（Tailscale/Cloudflare Tunnel）

---

## 6. 安全考量

| 項目 | 措施 |
|---|---|
| Telegram 推送 | 只發送到老闆私人聊天 (920593269) |
| Telegram bot token | 存儲在環境變數（`TELEGRAM_BOT_TOKEN`），唔寫入 config |
| Web Dashboard | 部署在 localhost:8788（不公開），敏感數據唔通過前端 JS |
| MT4 帳號 | CSV 只存 login ID，可選用別名（ACCT_001/002） |
| 數據庫 | SQLite 本地存儲，WAL 模式，權限 600 |
| API | FastAPI 只監聽 localhost |
| config 檔 | `openclaw.json` 權限 600，確保密碼唔洩漏 |

---

## 7. 風險評估

| 風險 | 機率 | 影響 | 緩解措施 |
|---|---|---|---|
| MT4 WebRequest 白名單 | 中 | HTTP POST 失敗 | EA 需配置 `Allow WebRequest`，CSV fallback |
| CSV 文件鎖定 | 中 | Python 讀取失敗 | HTTP POST 做主通道，CSV 用輪替寫入 |
| Telegram 1 msg/sec 限制 | 中 | 通知延遲 | PriorityQueue 排隊 + 合併 Normal 事件 |
| 推送過吵 | 中 | 用戶體驗差 | 靜音時段 + 可配置門檻 + 每小時摘要 |
| Dashboard 手機無法訪問 | 高 | 無法遠端查看 | Phase 3 提供 Tailscale/Cloudflare Tunnel 方案 |
| 數據庫膨脹 | 低 | 磁碟空間 | 自動清理策略，positions 只存變更 |
| MT4 斷線 | 中 | 數據中斷 | HTTP 超過 5 分鐘未收到 → Telegram 通知 |
| WSL2 權限問題 | 低 | 讀取失敗 | 確保 `chmod 700` 數據目錄 |
| History 導出只限今日 | 中 | 丟失歷史 | 首跑全量同步 30 日，之後增量更新 |

---

## 8. 成功指標

| 指標 | 目標 |
|---|---|
| 數據延遲 | < 5 秒（HTTP POST 主通道） |
| 通知延遲 | < 30 秒（事件到 Telegram，Critical 級別優先） |
| 系統可用性 | > 99%（MT4 運行時） |
| 斷線偵測 | < 5 分鐘（HTTP 超過 5 分鐘未收到） |
| Dashboard 響應時間 | < 1 秒（記憶體快取） |

---

## 9. 已確認事項

1. **帳戶數量**：未確定，需要支援動態新增多個不同 broker 的 MT4 帳戶
2. **帳戶標籤**：預設使用 `Broker Server + 帳戶號碼`，支援自定義名稱；可用別名（ACCT_001/002）避免暴露真實 login
3. **通知頻率**：Telegram 限制為同一聊天 1 msg/sec, 20 msg/min；系統需做好排隊機制
4. **歷史數據**：需要匯入 MT4 登入後可見的交易歷史記錄（可配置範圍；首跑同步 30 日）
5. **帳戶識別**：每個帳戶用 Broker Server + Login ID 作唯一識別
6. **推送噪音控制**：需要靜音時段功能 + 可配置門檻
7. **數據傳輸**：HTTP POST 做主通道（低延遲），CSV 做 fallback（離線可用）

---

## 附錄：參考系統

| 系統 | 特色 | 我們的對應 |
|---|---|---|
| **Signalator Autotrader** | 多帳戶 + Telegram 推送 | ✅ 整合 |
| **Copygram** | Telegram → MT4 trade copy | ❌ 不需要 |
| **forexbook.com** | 網頁帳戶追蹤 | ✅ 自己建 |
| **EFX Dashboard** | EA performance tracker | ✅ 整合 |

---

*PRD v1.1 — 已整合 3 個 AI 專家審查意見 — 待老闆批核後開始實施*

---

## 附錄 A：AI 專家審查總結

### MQL4 專家意見
- ✅ CSV 導出方式合理，30 秒間隔對 MT4 效能影響極小
- ❌ **CSV 係最大弱點**，WSL2 watchdog 不可靠
- 💡 **改用 HTTP POST** 做主通道（WebRequest → FastAPI），CSV 做 fallback
- ⚠️ EA 必須用 `OnTimer()` 而非 `OnTick()`
- ⚠️ history 只導出今日唔夠，需要初始化同步（首跑 30 日）
- ⚠️ MT4 `OrdersHistoryTotal()` 依賴 Account History tab 顯示設定

### Python 架構師意見
- ❌ watchdog 在 WSL2 監聽 Windows 文件系統不可靠
- 💡 改用 **polling 每 5 秒**（延遲 < 35 秒）或直接用 HTTP POST
- ✅ SQLite WAL 模式足夠，不需要 Redis
- 💡 不要用 pandas 解析 CSV（用 csv.DictReader）
- 💡 Telegram 排隊用 PriorityQueue + 合併邏輯
- ✅ 推薦 systemd 而唔係 supervisord
- 💡 加入記憶體快取，避免每次查 SQLite

### Security & UX 專家意見
- 🔐 Telegram bot token 唔好寫入 config，用環境變數
- 🔐 Dashboard 手機遠端訪問方案未解決（localhost 無法從外網訪問）
- 🎨 需要靜音時段功能（00:00-07:00）
- 🎨 大額平倉（>$100）應提升為 High 級別
- 🎨 大額浮動門檻應可配置
- 🎨 推送會唔會太吵？高頻交易場景可能每小時 100+ 條訊息

---

## 附錄 B：系統配置模板

### 環境變數
```bash
TELEGRAM_BOT_TOKEN=bot_xxx:xxx
TELEGRAM_USER_ID=920593269
MT4_MONITOR_API_PORT=8788
MT4_MONITOR_QUIET_HOURS_START=00:00
MT4_MONITOR_QUIET_HOURS_END=07:00
MT4_MONITOR_LARGE_MOVE_THRESHOLD=100
MT4_MONITOR_LARGE_PNL_THRESHOLD=100
MT4_MONITOR_HTTP_TIMEOUT=300  # 5 分鐘無更新視為斷線
```

### systemd service
```ini
[Unit]
Description=MT4 Multi-Account Monitor
After=network.target

[Service]
Type=simple
User=alvin
WorkingDirectory=/home/alvin/.openclaw/workspace/trade_strategy_analyzer
ExecStart=/usr/bin/python3 -m mt4_monitor.main
Restart=on-failure
RestartSec=10
Environment=PYTHONUNBUFFERED=1
Environment=TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
MemoryMax=256M
CPUQuota=50%
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### MT4 EA 配置（需用戶手動設定）
```
MT4 → Tools → Options → Expert Advisors
☑ Allow WebRequest for listed URL
添加: http://localhost:8788
```

---

*PRD v1.1 — 已整合 3 個 AI 專家審查意見 — 待老闆批核後開始實施*
