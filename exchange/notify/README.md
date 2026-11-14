# exchange/notify — 完成即通知（雙向觸發）

> 老闆 2026-11-14 11:47 指示：兩邊設「完成工作就通知對方」機制，收到通知即行下一步，唔等下一個整點。

## 與 exchange/from_* 嘅分別

| 目錄 | 用途 | 大小 | 誰讀 |
|---|---|---|---|
| `exchange/from_zcode/` `from_openclaw/` | 正式信件、patch、供料、回批 | 可大 | 人手／巡檢 job |
| `exchange/notify/` | **只放一行指標**：邊個完成咗乜、對應邊封信 | < 1 KB | 自動 watcher（每 3 分鐘） |

## 規則

1. **完成即寫**：交付／驗收／回批一 push 完，喺自己嘅 notify 目錄加一個檔：
   `exchange/notify/from_zcode/20261114_1231_tasks_board排版_L1-L6交付.md`
2. 檔內容只要三行：
   ```
   完成：tasks_board 排版重構 L1-L6
   信件：exchange/from_zcode/20261114_1231_tasks_board排版交付/
   commit：<sha>
   ```
3. 同一個 commit 內 push（唔好分兩次）。
4. **只寫自己目錄**，唔准動對方 notify 檔。
5. 收到對方 notify 後，收貨方喺自己 notify 目錄寫 `ack` 檔，講「已收，下一步 X」。

## 自動監看

- OpenClaw 側：automation `exchange-notify-watch`，每 3 分鐘對 `origin/main` 做 diff，見到 `exchange/notify/from_zcode/` 有新檔即喚醒，即刻 pull、讀信、驗收、回批。
- ZCODE 側：喺 `:31` 巡檢時，先掃 `exchange/notify/from_openclaw/`；有未讀即優先處理該項，唔需要等下一輪。

## 為何唔用 GitHub webhook

Gateway 冇公開 HTTPS 入口，webhook 收唔到；改用 git 輪詢（3 分鐘）＋`git fetch` 增量 diff，成本極低（每次一個 fetch ref，唔拉 blob）。
