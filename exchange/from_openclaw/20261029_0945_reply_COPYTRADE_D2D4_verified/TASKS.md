# 📋 任務看板 TASKS Board
<!-- project: path:/home/alvin/.openclaw/workspace/main -->
> 老闆同我共用嘅 single source of truth，開工／完工即更新。
> 最後更新：2026-10-29 08:20 HKT

## 🔄 進行中
| # | 任務 | 狀態 | ETA |
|---|---|---|---|
| 1 | Track 1：Excel 工作簿（Copilot 線 v7→v8） | **v8 老闆實機驗 OK 已收案（10-29 05:28）**：v8＋白皮書 v3.1 已存檔，ImportCSV 按鈕 `_xludf` 缺陷已修（`分析工作簿_v8_修正按鈕.xlsm`）；獨立重算 1,381/81.245%/+73,022.98/−2,713.33 全對 | 收案 |
| 3 | ZCODE 待辦 | **真正未清**：①UNK 治本（名稱部分已完成：57→75 鍵、21 id 覆蓋 20；3894 裁示 SMA 不加名）②新聞頁早晚報 ③`forex_hub` 死碼。四項 patch 已出＋v2 deploy key 已加（id 167924058） | 等 ZCODE push |
| 5 | Copytrade 規格書第六節重寫 | **已派 ZCODE（16:15）**：派工包 exchange/1615（6.2 tick_value 權威・已批 4 參數零矛盾・pseudo-code 級精確），commit `a2361d14`。**v1.3 已於 10-29 00:58 派工，D1 引擎提前完成** | 等 ZCODE 交稿 |
| 6 | TASKS Board 重構 | **設計簽核已出（Muse 08:10，459 行＋prototype v2＋量測腳本）**：手機頁高 4,344→2,417px（−44%）、任務欄 49px→336px（2 字→34 字/行）、一列 15 行→4 行、已完成卡 1,871px→246px。待派 ZCODE 落地 | Muse 已簽核→派工中 |
| 7 | MT4 TradeDashboard v1.48 | **老闆 07:50 三項**：①H/D 空白（零單 bucket 被跳過，要顯示 0 單行）②DDGuard 頁加 runtime 開關掣（Acc/Sym/總，GV 持久化＋確認）③版本確認（實為 v1.47，面板刻意唔顯示版本） | 開工中 |

## 📅 已排程（cron 自動行）
- gold-plan-watcher-v2（一至五 07–23 每 10 分鐘）／ff-signal-scraper／xau-session-settle-v3
- tsa-ranking-daily／news-guard-daily／早晚盤報告（07:00／18:00）
- db_snapshot 03:13／VPS 備份 pull 03:05 push 03:35（留 7/8 版）
- heartbeat 6 jobs

## ✅ 已完成（10-29）
| 任務 | 證據 |
|---|---|
| **TSA 站務四項全收案**（模板字／UNK 治本／早晚報區／4H 退休） | ZCODE 落地 `5d33985c`＋我側加密頁 `b1a03da6`，round-trip 全過（10-28 15:24） |
| **db_snapshot 修復實證** | 03:13 實跑通過（tsa_20261028.db.gz）收案；10-29 亦見 ok |
| **deprecated 兩頁裁決**：symbol_ranking／mfe_mae 先保留、待改造完成再確認 | `111c0ab5`（老闆 05:28 拍板） |
| **密碼旋轉**：一般頁 `TSA-ffisthebest`／owner 三頁 `FF48@Alvin` | `86e8a3ad`｜15/15 解密→重加密→新舊密碼驗證（舊全失效） |
| **COPYTRADE v1.3 D1 引擎提前完成**：六模組＋9/9 重放對帳＋N=18 閘門＋M4 零估算 | ZCODE_i `0790fd7`｜v1.2 源碼交付 `1528947d` |
| **OHLC exporter v2 收貨結案**：31 項等價覆蓋全 PASS | ZCODE_w `20261029_0545`／`0631` |
| **tsa-ranking-daily 補 commit/push**（每日 dirty 根因根治） | job `bb79dd50` 已改｜10-29 05:30 首跑成功 `0a9464ec` |

## ✅ 已完成（10-27）
| 任務 | 證據 |
|---|---|
| **PlanExecutor v3.10 資訊面板**（LIVE/SHADOW 徽章・節尾倒數・三部署狀態色碼・Δ距離・風控行） | 編譯 0 err＋MCP 重掛＋截圖 #40295 |
| **17547 完整分析四連發**：PPT 示範版（15頁 #40318）→ 詳析版（18頁 #40325）→ 三維矩陣版（24頁 #40330＋CSV #40331）→ Excel 工作簿（32頁 #40337） | 十三法實測：最優 ≤2.0 帽 98% 利潤 |
| p13489 示範 PPT（15頁，存款幻象＋164 強平發現） | #40286 |
| Track 1 工序 v2.1（S0-S8 十閘門，四輪反饋打磨） | S0-S3 已行 |
| MAIN AGENT 轉 yuanyuai/glm-5.3 | pin＋validate＋snapshot 同步 |
| TSA 保護動作：83 檔真實交易數據 untrack（origin 404 已驗證，歷史不清洗） | 646c52a7/2fbc2ab6 |
| ZCODE：靜默誤會澄清＋五項加固 v3.3 驗收全過＋fileMode 第⑥項開工令 | 734ae039/6c9f140e |
| db_snapshot 連敗三日修復（cron PATH 加 linuxbrew） | env -i 驗證 exit 0 |
| 晨報 6d247f17／晚報 80c480bf＋來源簡寫改革（USER.md directive） | 報告頁 origin 0 全路徑 |
| EA 名 mapping：53 個 UNK 拆解（set 檔線索 28 個即刻有名＋12 家族名） | 對照表 #40308 |
| 報告來源簡寫（生成器 patch＋今日報告手術修） | 7cc9108d |
| **補推 05:30 ranking 產物**（4 頁重加密，live 滯後一日修正）＋**根因：`tsa-ranking-daily` 冇 commit/push 步驟** | `205ad2ab` |
| **任務看板修溢出**（卡片長英數 token 撐爆 445px>388px，右邊字被鄰卡遮） | `c30ed0b6` 已上線 |

## ✅ 已完成（10-26）
| 任務 | 證據 |
|---|---|
| TD5 v1.48（SyncTradesFromHistory 冪等修）＋v1.49（reset 鍵固定位置）＋v1.50 診斷（snap.bin 時間倒退毒記錄） | 編譯 0 err×2＋五行數字一致 |
| ZCODE key 事件收案（備份 key 找回→push 首通 c0577cf） | 指紋 SHA256:/HG5… |
| exchange_cycle 五項加固派工（bb45c430）＋quotePath 增補（fae7c12c） | ZCODE 已收貨 |
| MT4 A06E 恢復＋晚報補跑成功 | 群 -5211779365 |
| Copytrade 規格書/工作流/篩選 PPT＋PDF 三件套交付 | whatsapp_out |

## ✅ 已完成（10-20 精選）
| 任務 | 證據 |
|---|---|
| S10 EA 全筆記＋Apple 風格 PPT／CCY 白皮書 v3.10／TSA 白皮書 | TG msg 396xx 系列 |
| MT5 MCP 打通（67 tools）／VPS 備份架構／工作管理介面上線 | probe 全綠／cron 03:05 |

## ⏸ 待做（未排程）
- MT4/MT5 同步 Round 1+2（方案已交，等拍板）／Round 3（A4/A2）
- CCY 原版對比（方案已批，等「開工」）
- Node 手機 app（等 LAN/Tailscale）
- secrets 遷 SecretRefs／MT4 monitor 轉 systemd

## 👀 等老闆動作
1. **EA 名對照表 25 行**（#40308 已發，第 4 欄填官方名＋版本）→ 填完 15 分鐘入晒＋派 ZCODE 信
2. **Track 1 三個決定**：規格書 4 參數 default／S4 方法庫加減／**17547 開 S6 對帳回測（≤2.0 帽基準）**
3. **Key rotate 轉手**（五項加固已全過，ZCODE 備妥）
4. 短名單時限（S0+S1 隨時開跑）
5. 舊數：CCY 對比開工／MT4-MT5 同步拍板
