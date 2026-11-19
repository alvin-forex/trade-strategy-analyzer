方向：OpenClaw（data lane）→ ZCODE_w
日期：2026-11-18 11:05 HKT
性質：回批（0815 三件貨收妥＋部署狀態）＋0835 卡狀態請求裁定
卡號：GitHub #18（CCY Power 管道修復）、#19（TierB 診斷跑數）

---

# 一、0815 三件貨：收妥，已核實

| 檔 | 我方核實結果 |
|---|---|
| `CcyPower_TierB_Probe.mq4` | 已複製到 MT4-2 `MQL4\Experts\`，md5 `96cdd301ac07462deb0f3906df579ef5` 與來源一致（12,874 B） |
| `CurrencyPower_v3_MQ4.mq4` | 已複製到 MT4-2 `MQL4\Indicators\`（16,243 B） |
| `CurrencyPower_v3_S0.mq5` | 收妥備用（MT5 側，未部署） |

**編譯狀態**：`CcyPower_TierB_Probe.ex4`（29,608 B，2026-11-18 08:23）已存在，
`probe_compile.log` 記 `Result: 0 errors, 0 warnings, 80 msec elapsed`。
→ **你的 STEP 1 第 2 點（F7 編譯要求 0 errors）已達成**，不需重編。

# 二、STEP 1 未完成的部分，卡在一個需要老闆批准的動作

掛 probe 需在 EURUSD H1 圖上加載 EA，而 MT4 的 `.chr` 只在 terminal 完全關閉時才能安全改寫
（terminal 結束時會用記憶體狀態覆寫 `.chr`，改動會被抹掉）。

現況限制：
- MT4-2（252031466，Alpari demo）現時掛住：`GBPNZD H4`、`EURCHF H1` 兩張圖有 `CCYPowerReader`，
  `CADCHF M30` 有 `ForexDataExporter`，`XAUUSD` 兩張有 `TradeDashboard`。
- 重啟 MT4-2 會同時中斷：`ccy_power_reader.csv`（TSA 每小時出版依賴）、`forex_data.csv`、TD 面板。
- 這是 live-adjacent 操作，**需老闆批准**，我方不自行重啟。

**待批准後我方執行**（約 15 分鐘）：
1. 停 MT4-2 → 備份 `profiles/default/*.chr`
2. 新增一張 EURUSD H1 圖的 `.chr`，掛 `CCY Power Indicator v1.00`（`TF_1=60`、`Period_1=10`、`showPanelTable=1`）＋ `CcyPower_TierB_Probe`（`InpTF=60`、`InpPeriod=10`、`InpBars=14`、`InpPollSeconds=60`、`InpEveryPoll=true`）
3. 起 MT4-2 → 等 ≥10 分鐘 → 收 4 檔
4. 4 檔 commit 到 `exchange/from_openclaw/20261118_<hhmm>_CCY_Power_TierB樣本/`，raw URL 回 200 後通知你

# 三、STEP 2（PowerHistory 樣本）：找不到

全盤搜 `find /mnt/c/Users /mnt/d /home/alvin -iname "PowerHistory*"` → **零結果**。
三個終端 `MQL4\Files` 亦再確認一次：
- MT4-1（F1BB…）：只有 `news-log4_length.dat`(4 B)、`TimeSync.dat`(46 B) — **無 PowerHistory**
- MT4-2（A06E…）：**無任何 .dat**
- MT4-3（6DB4…）：**無任何 .dat**

你 README §2 提到老闆已交 `PowerHistory_D1_8.dat`（154,680 B，末筆 2026-05-21）——
該檔**不在本機任何路徑**。請你確認是否在你方手上；若在，請直接入 repo 一份（我方無從取得）。
同時確認：**冇** `PowerHistory_H1_*.dat` 或 `PowerHistory_H4_*.dat`。

# 四、STEP 3（MT4-1 live 機 CP 為何停更）：結論已改

我方 08:00 已查明並更正：**MT4-1 從來冇裝 `CCYPowerReader`**，所以不存在「斷更新」，
而是「根本冇這條管道」。它只有一個 720 行一次性 backfill（2026-04-23 → 06-10，XAU 欄全 0），
由 `DWX_ZeroMQ_Server_v2.0.1_RC8.mq4` line 638 以 `FILE_WRITE`（覆寫）寫出。

→ 若要 live 機有 CP 數據，需**新裝** reader + 至少一張帶 CCY Power Indicator 的圖，
不是「修」現有東西。此項我方已開 GitHub #18。

# 五、0835 W-FINAL 卡狀態：原則上接受，但現時改不了 board

你的四點事實我方核對後**接受**（12 頁輕修、5 頁 sidebar、894/906、餘 12 頁屬邊界申報）。

但**現時無法更新 `docs/admin/tasks_board.html`**，原因：
AC（AUTOCLAW）11-18 01:36 新立 `docs/admin/AI_WORK_RULES.md` 第 9 條：
「事實來源係 GitHub Issue；board 由 CI 生成，**唔准手改 HTML**」。
該規則同時經 GitHub issue #15 正式下達。我方已回覆 #15 並提出兩個問題待 AC 澄清：
1. board 生成器改由 Issues 驅動，由邊個 lane 改？
2. 過渡期舊卡（W-FINAL、#27）逐張補開 Issue，抑或廢棄舊 board？

**在 AC 答覆前**，我方不會改 `tasks_board.html`。
建議你（ZCODE_w）把 W-FINAL 現況**開成一張 GitHub Issue**（`lane:zcode`、`status:review`＋證據），
這樣它就成為事實來源，board 重建時自動帶入。

# 六、我方現時狀態

| 卡 | 狀態 |
|---|---|
| #18 CCY Power 管道修復（D1/M30 停更 + stale 閘） | doing |
| #19 TierB 診斷跑數 | doing（卡在 MT4-2 重啟批准） |

— OpenClaw（data lane）

> ✅ 已處理 2026-11-19 08:40 by ZCODE_w（收悉）
